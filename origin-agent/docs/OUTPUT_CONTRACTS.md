# Output contracts — 0.2.11

Contract version: **1.0.0**. All public MCP tools declare `outputSchema` and return
matching `structuredContent`. The server validates each result using strict typed
models before delivery. The models and schema generator share the existing
Pydantic dependency; there is no new runtime service or paid model call.

## Discovery and compatibility

Economy mode still advertises five tools: `origin_status`, `origin_help`,
`origin_call`, `origin_recipe`, and `origin_get_artifact`. Use
`origin_help(operation="origin_get_job")` to obtain the operation's `input_schema`
and `output_schema`. Full mode advertises all 14 operations with their exact result
schemas. `origin_call` exposes a compact projection and validates the selected
operation's full contract before returning its unchanged, flattened result.
Do not nest calls; direct help is preferred, though wrapped help remains accepted.

Contracts use JSON Schema 2020-12, local `$defs`/`$ref`, unions and null alternatives.
A provider's model-generation strict-schema subset is not necessarily an MCP
result-schema implementation. Thin host adapters must preserve results and media;
actual provider/model compatibility remains a separate acceptance gate.

Existing field names, numerical meanings, missing fields, nulls and text/resource
block positions are retained. Validation does not coerce strings to numbers or
booleans and does not insert default measurements or verification claims. Added
fields are `origin_status.output_contract`, the output schema/version in help,
and artifact mode/content-index/pagination metadata. The first MCP text block
remains a JSON fallback equal to `structuredContent`; binary data stay separate.
The contract version is also in result/tool `_meta.origin_output_contract_version`.

## Semantics and recovery

Jobs have six states: queued, running, succeeded, failed, cancelled, interrupted.
Pending jobs have `terminal=false` and a polling interval. Terminal failures provide
`next_action`; waiting cannot complete them. A successful submission or cancellation
request can return an already completed job because identical plans are deduplicated.
Session states are separate: opening, executing, ready, gui, suspended, closed,
needs_attention. Session inspection works directly and through `origin_call`.

Numerical values are finite JSON numbers. Counts such as `graphs_reopened` and
`native_reports_reopened` remain counts; a successful program does not turn
`independent_scientific_validation=false` into true. Units remain explicit in field
names, workflow configuration or the source data. An omitted check means no result
was supplied. Null uncertainty is not zero uncertainty. Beer–Lambert's structured
`unknown_uncertainty_result` and its legacy display string retain their meanings.

Correctable errors use stable `error` values: validation, syntax, invalid_request,
tool, execution, output_validation, with MCP `isError=true`. A failed scientific
job is a valid job-status response with `state=failed`; it is not a malformed tool
response. Unhandled execution exceptions return a sanitized structured error.

A malformed backend result becomes `output_validation`, never a valid success.
Valid known job/plan/dataset/session IDs are retained. A retained job ID includes
readback recovery guidance. **The action may already have executed.** Inspect the
known state before any deliberate retry; the validator never repeats an operation.
GUI observation jobs without a stored project index return an explicit
`invalid_request` from `origin_inspect_project`; use their checkpoint/artifacts.

## Artifacts and bounds

Artifact metadata describe ID, local path, MIME type, byte length, SHA-256 and mode.
Block 0 is metadata JSON; block 1 is the original resource link. For preview,
download or text, `content_index=2` identifies the existing image, embedded binary
resource or text-page block. Text metadata include offset, next_offset and
total_chars. Pagination measures characters, not bytes. At EOF next_offset is null.
The server checks that block kinds, link metadata and page lengths match.
Download bytes are hash-verified by the existing artifact transfer path; metadata
alone do not establish host receipt, successful saving or visual correctness.

All structured results must fit 8 MiB of compact UTF-8 JSON, depth 40 and 65,536
visited JSON values (including containers); object keys must be strings. Unknown
fields are rejected outside documented extension points. Extensible JSON is used
for schema documents, recovery arguments and the compact dispatcher; it is subject
to the same global bounds. Images/files are not duplicated into this JSON limit.
Existing transfer limits remain 32 MiB per binary download, 8 MiB PNG preview,
128 KiB text artifact, and 256–32,768 characters per text page.

Generated schemas are cached, with cosmetic titles/defaults omitted; constraints,
field names and descriptions remain intact. Catalog regression budgets are under
200 KB UTF-8 for full mode, under 40 KB for economy, and economy below 25% of full.
Schema bytes are not tokens, billed cost or proof of model success. Output schemas
increase catalog size relative to 0.2.10; on-demand operation discovery keeps that
increase out of the default dispatcher.

## Coverage and verification

All contracts below are implemented. `tests/test_output_contracts.py` checks
independent schema validation, direct/dispatch behavior, malformed outputs,
retained IDs without replay, all job/session states, media block positions, exact
text reassembly and error flags. The existing transport tests cover auto and
legacy MCP modes. Native verification scripts additionally check responses with
an independent JSON Schema validator (`scripts/contract_validation.py`).

| Public operation | Contract branches | Current verification route |
| --- | --- | --- |
| origin_status | discovery, target/profile, errors | unit, stdio, native |
| origin_capabilities | search, detail, coverage, errors | typed contract; coverage unit; native installation discovery |
| origin_import_table | snapshot/column quality, errors | unit, stdio |
| origin_inspect_dataset | snapshot/column quality, errors | unit, stdio, native workflow |
| origin_plan_workflow | bounded plan, errors | unit, stdio, native workflow |
| origin_run_workflow | six job states, cached terminal, errors | lifecycle unit; native workflow |
| origin_recipe | plan or job, errors | existing recipe tests; native workflow |
| origin_get_job | six states; workflow/program/session/GUI evidence | lifecycle unit; native scripts |
| origin_cancel_job | pending or terminal status, errors | lifecycle unit; native session cancellation |
| origin_run_program | standalone/session jobs, errors | native program/session scripts |
| origin_session | jobs or seven inspection states, errors | all inspection states unit; native session script |
| origin_gui | jobs with bounded GUI observations, errors | typed contract; native GUI script |
| origin_inspect_project | workflow/program/session index, unsupported GUI job | native workflow/program; explicit unsupported result |
| origin_get_artifact | info/preview/text/download, errors | all modes unit; exact binary/text checks; native files |
| origin_help (economy) | catalog or exact schemas/receiver, errors | every operation's schema and live help tests |
| origin_call (economy) | compact projection plus selected operation, errors | direct/dispatch tests and native economy scripts |

The table identifies verification routes, not a claim that every possible program,
GUI control, legacy artifact or host/model has passed. Read the version-specific
[acceptance record](https://github.com/saigyujikingyo-png/origin-agent-bridge/blob/codex/origin-companion-release/WORK_ACCEPTANCE_0.2.11.md) for executed checks and remaining
gaps. Schema compliance supplements native reopening, scientific cross-checks,
visual review and actual account/host delivery; it cannot replace them.
