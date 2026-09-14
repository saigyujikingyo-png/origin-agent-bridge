"""Independent JSON Schema checks for native verification scripts, without extra tool calls."""

import json

from jsonschema import Draft202012Validator
from mcp import Client

from origin_agent.output_contracts import OUTPUT_CONTRACT_VERSION, output_schema


class ContractClient(Client):
    async def list_tools(self, *args, **kwargs):
        response = await super().list_tools(*args, **kwargs)
        for tool in response.tools:
            assert tool.output_schema == output_schema(tool.name), tool.name
            Draft202012Validator.check_schema(tool.output_schema)
        return response

    async def call_tool(self, name, arguments=None, **kwargs):
        result = await super().call_tool(name, arguments, **kwargs)
        assert result.structured_content is not None, name
        Draft202012Validator(output_schema(name)).validate(result.structured_content)
        if name == "origin_call":
            Draft202012Validator(output_schema(arguments["operation"])).validate(result.structured_content)
        assert result.meta["origin_output_contract_version"] == OUTPUT_CONTRACT_VERSION
        assert json.loads(result.content[0].text) == result.structured_content
        return result
