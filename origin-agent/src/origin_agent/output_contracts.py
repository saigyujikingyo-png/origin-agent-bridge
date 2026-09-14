"""Versioned, server-enforced MCP results without changing operation response shapes.

Models validate the original payload; they never inject defaults or coerce returned
values. The dispatcher advertises a compact projection and validates its selected
operation before returning it. Large media remain in MCP content blocks.
"""

import copy
import json
import math
import re
from functools import lru_cache
from typing import Literal

from mcp_types import CallToolResult, TextContent
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError, model_validator

from .output_types import (
    OPERATION_OUTPUT_TYPES,
    ErrorOutput,
    JsonObject,
    JsonValue,
    ProfileReport,
    SessionState,
)

OUTPUT_CONTRACT_VERSION = "1.0.0"
MAX_JSON_BYTES = 8 * 1024 * 1024
MAX_JSON_DEPTH = 40
MAX_JSON_ITEMS = 65536
_ID = re.compile(r"^[a-f0-9]{32}$")


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)


class OperationSummary(ContractModel):
    name: str
    summary: str


class HelpRouting(ContractModel):
    direct_tools: list[str] = Field(max_length=16)
    via_origin_call: str
    help: str


class HelpCatalog(ContractModel):
    operations: list[OperationSummary] = Field(max_length=14)
    routing: HelpRouting
    profile: ProfileReport


class HelpCall(ContractModel):
    tool: Literal["origin_call"]
    operation: str
    arguments_json: str


class ArtifactReceiver(ContractModel):
    javascript: str
    usage: str


class HelpDetail(ContractModel):
    operation: str
    instructions: str | None
    input_schema: JsonObject
    output_schema: JsonObject
    output_contract_version: Literal["1.0.0"]
    call: HelpCall
    receiver: ArtifactReceiver | None = None


# This projection deliberately retains flattened operation results for old hosts.
# The full operation validator is applied before results reach this facade.
_DISPATCH_MARKERS = [
    ["plugin_version", "agent_profile"],
    ["dataset_id", "row_count", "columns"],
    ["plan_id", "native_execution"],
    ["job_id", "state", "terminal"],
    ["session_id", "revision"],
    ["artifact_id", "mime_type"],
    ["engine", "workflow", "project_index", "verification"],
    ["installation", "counts"],
    ["baseline", "categories", "full_functionality_verified"],
    ["operations", "routing", "profile"],
    ["operation", "input_schema", "output_schema"],
]


class DispatchedOutput(BaseModel):
    model_config = ConfigDict(
        extra="allow",
        strict=True,
        allow_inf_nan=False,
        json_schema_extra={
            "anyOf": [{"required": keys} for keys in _DISPATCH_MARKERS],
            "description": (
                "Operation-shaped result. Read origin_help(operation=...) for its exact output_schema; "
                "the server validates that operation contract before this compact dispatch projection."
            ),
        },
    )
    __pydantic_extra__: dict[str, JsonValue] = Field(init=False)
    job_id: str | None = Field(default=None, pattern=r"^[a-f0-9]{32}$")
    plan_id: str | None = Field(default=None, pattern=r"^[a-f0-9]{32}$")
    dataset_id: str | None = Field(default=None, pattern=r"^[a-f0-9]{32}$")
    session_id: str | None = Field(default=None, pattern=r"^[a-f0-9]{32}$")
    state: (
        Literal["queued", "running", "succeeded", "failed", "cancelled", "interrupted"] | SessionState | None
    ) = None
    terminal: bool | None = None

    @model_validator(mode="before")
    @classmethod
    def identifiable_operation(cls, value):
        if not isinstance(value, dict) or not any(set(keys) <= value.keys() for keys in _DISPATCH_MARKERS):
            raise ValueError("Missing operation result identity")
        return value


def success_type(operation):
    if operation == "origin_help":
        return HelpCatalog | HelpDetail
    if operation == "origin_call":
        return DispatchedOutput
    return OPERATION_OUTPUT_TYPES[operation]


@lru_cache(maxsize=40)
def output_adapter(operation, error=False):
    return TypeAdapter(ErrorOutput if error else success_type(operation))


def _compact_schema(value, names=False):
    if isinstance(value, dict):
        # Display titles/defaults add no contract information. Keep descriptions,
        # required fields, null alternatives, constraints and reference definitions.
        return {
            key: _compact_schema(item, key in {"properties", "$defs", "definitions", "patternProperties"})
            for key, item in value.items()
            if names or key not in {"title", "default"}
        }
    if isinstance(value, list):
        return [_compact_schema(item) for item in value]
    return value


@lru_cache(maxsize=20)
def _schema(operation):
    schema = TypeAdapter(success_type(operation) | ErrorOutput).json_schema()
    schema = _compact_schema(schema)
    schema["type"] = "object"
    schema["$comment"] = "Origin Companion output contract " + OUTPUT_CONTRACT_VERSION
    # Recursive JSON is reserved for explicitly extensible results and schema
    # documents. Advertise its collection bounds, matching the runtime guard.
    definition = schema.get("$defs", {}).get("JsonValue")
    if definition:
        for option in definition.get("anyOf", []):
            if option.get("type") == "array":
                option["maxItems"] = MAX_JSON_ITEMS
            elif option.get("type") == "object":
                option["maxProperties"] = MAX_JSON_ITEMS
            elif option.get("type") == "string":
                option["maxLength"] = MAX_JSON_BYTES
    return schema


def output_schema(operation):
    return copy.deepcopy(_schema(operation))


def bounded_json(value):
    """Reject non-JSON, non-finite, cyclic/too-deep or excessive structured data."""
    nodes = 0

    def visit(item, depth):
        nonlocal nodes
        nodes += 1
        if depth > MAX_JSON_DEPTH or nodes > MAX_JSON_ITEMS:
            raise ValueError("Structured output exceeds its depth/item limit")
        if isinstance(item, dict):
            if len(item) > MAX_JSON_ITEMS or any(type(key) is not str for key in item):
                raise ValueError("Invalid structured object")
            for child in item.values():
                visit(child, depth + 1)
        elif isinstance(item, list):
            if len(item) > MAX_JSON_ITEMS:
                raise ValueError("Structured array exceeds its item limit")
            for child in item:
                visit(child, depth + 1)
        elif isinstance(item, float):
            if not math.isfinite(item):
                raise ValueError("Non-finite output")
        elif item is not None and type(item) not in (str, int, bool):
            raise ValueError("Non-JSON output type")

    visit(value, 0)
    encoded = json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
    if len(encoded.encode("utf-8")) > MAX_JSON_BYTES:
        raise ValueError("Structured output exceeds 8 MiB; use artifact resources")
    return encoded


def _failure(operation, payload):
    failure = {
        "error": "output_validation",
        "operation": operation,
        "message": (
            "Backend output does not match its declared contract. The operation may already have executed; "
            "inspect retained identifiers before any deliberate retry."
        ),
    }
    if isinstance(payload, dict):
        for name in ("job_id", "plan_id", "dataset_id", "session_id"):
            value = payload.get(name)
            if isinstance(value, str) and _ID.fullmatch(value):
                failure[name] = value
    if "job_id" in failure:
        failure["recovery"] = {"tool": "origin_get_job", "arguments": {"job_id": failure["job_id"]}}
    output_adapter(operation, error=True).validate_python(failure, strict=True)
    return CallToolResult(
        content=[TextContent(text=bounded_json(failure))],
        structured_content=failure,
        is_error=True,
        meta={"origin_output_contract_version": OUTPUT_CONTRACT_VERSION},
    )


def _validate_artifact_content(payload, content):
    """Check metadata/block correspondence without copying or re-encoding media."""
    mode = payload["mode"]
    expected_count = 2 if mode == "info" else 3
    if len(content) != expected_count or content[0].type != "text" or content[1].type != "resource_link":
        raise ValueError("Artifact content layout does not match its metadata")
    link = content[1]
    if (
        str(link.uri) != f"origin://artifacts/{payload['artifact_id']}"
        or link.size != payload["bytes"]
        or link.mime_type != payload["mime_type"]
    ):
        raise ValueError("Artifact link metadata does not match")
    if mode == "info":
        return
    block = content[payload["content_index"]]
    if mode == "preview":
        if block.type != "image" or block.mime_type != payload["mime_type"]:
            raise ValueError("Preview content does not match")
    elif mode == "download":
        if (
            block.type != "resource"
            or not hasattr(block.resource, "blob")
            or str(block.resource.uri) != str(link.uri)
            or block.resource.mime_type != link.mime_type
        ):
            raise ValueError("Download resource does not match")
    else:
        if block.type != "text":
            raise ValueError("Text content does not match")
        page = json.loads(block.text)
        if (
            not isinstance(page, dict)
            or set(page) != {"offset", "next_offset", "total_chars", "text"}
            or not isinstance(page["text"], str)
            or {k: v for k, v in page.items() if k != "text"} != payload["pagination"]
        ):
            raise ValueError("Text page metadata does not match")
        end = page["total_chars"] if page["next_offset"] is None else page["next_offset"]
        if len(page["text"]) != end - page["offset"]:
            raise ValueError("Text page length does not match")


def validate_result(operation, result):
    """Validate every route once it returns; never invoke or repeat an operation."""
    payload = result.structured_content if isinstance(result, CallToolResult) else None
    try:
        if not isinstance(payload, dict):
            raise ValueError("Missing structured object")
        serialized = bounded_json(payload)
        output_adapter(operation, bool(result.is_error)).validate_python(payload, strict=True)
        # Preserve media/page blocks and their positions. The first text block is
        # the matching JSON fallback; binary content is never reserialized here.
        content = list(result.content)
        if not result.is_error and "artifact_id" in payload and "mode" in payload:
            _validate_artifact_content(payload, content)
        text_index = next((i for i, block in enumerate(content) if isinstance(block, TextContent)), None)
        if text_index is None:
            content.insert(0, TextContent(text=serialized))
        else:
            try:
                matches = bounded_json(json.loads(content[text_index].text)) == serialized
            except (ValueError, TypeError, RecursionError, OverflowError):
                matches = False
            if not matches:
                content[text_index] = content[text_index].model_copy(update={"text": serialized})
        return result.model_copy(
            update={
                "content": content,
                "meta": {**(result.meta or {}), "origin_output_contract_version": OUTPUT_CONTRACT_VERSION},
            }
        )
    except (ValidationError, ValueError, TypeError, KeyError, RecursionError, OverflowError):
        return _failure(operation, payload)
