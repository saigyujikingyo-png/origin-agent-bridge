# Origin Companion 0.2.11 acceptance

Date: 14 September 2026. Release type: **preview**. This release implements
output contract **1.0.0** without adding runtime dependencies or changing the
single Origin Companion identity.

## What changed

Every public tool declares a meaningful output schema and returns matching
structured results. Strict server validation rejects malformed output, preserves
known operation identifiers and never automatically repeats an action. Economy
mode retains five entrypoints and discovers exact per-operation schemas through
help. Artifact metadata now describe mode and pagination while preserving the
existing text, image and binary content blocks.

[Contract semantics, limits and per-operation coverage](origin-agent/docs/OUTPUT_CONTRACTS.md)
include migration and recovery guidance. The changes also turn unsupported GUI
project-index inspection into a correctable error and sanitize unexpected tool
execution exceptions.

## Current checks

- Full automated suite: **228 passed, 1 skipped** (Windows symlink-creation privilege),
  27.39 seconds. Ruff passes. Auto/legacy stdio and full/economy protocol checks pass.
- 43 focused output-contract cases include all six job states and seven session
  states, direct/dispatch consistency, valid JSON Schema, malformed output rejection,
  retention of identifiers without replay, media blocks and exact text pagination.
- Independent read-only code review found a session-state dispatcher mismatch;
  it was fixed and all seven states were retested. Native testing found a missing
  `total_panels` progress field; it was fixed and covered by queue-reader tests.
- Source calibration: three graph pages, two Beer–Lambert fits, supplied error bars,
  unit conversion, extrapolation flags and unsupported uncertainty semantics pass.
  Coefficients agree with independent standard-library regression. Native data,
  labels, tick formats, reports and OPJU reopen checks pass. All **14 files** were
  transferred through MCP and saved with matching lengths/SHA-256: 22.797 seconds.
- Independent Windows bundle repeats the same calibration and 14-file receipt:
  **17.250 seconds**. The bundle runs without a separate Python install or source
  checkout. These timings include protocol checking and are not billed model usage.
- Source economy workflow: native linear fit, cached-plan/job reuse, exact paginated
  manifest reconstruction and generic Python numerical readback pass (29.359 seconds).
- Persistent sessions: initial creation, continued edits, stale-revision refusal,
  failure rollback with numerical checks, restore, cancellation/recovery, a second
  MCP process, idle suspend/resume and close all pass.
- GUI transaction checks passed observation, stale-target isolation, program/batch
  exclusion, modal-commit refusal, editing and native readback. The later rollback
  scenario encountered a transient missing/ambiguous menu target and stopped with
  the correctable guard. Cleanup rollback and close succeeded. **The complete GUI
  scenario is partial**, not a pass; no uncertain GUI input was automatically replayed.
- Native scripts validate actual result payloads against independent JSON Schema
  validators, check declared schemas where listed, and compare the JSON text fallback.
- A source PNG was visually reviewed: labels, units, scientific x-axis notation,
  data markers and fitted line are visible without clipping. PDF/SVG bytes were
  received and hashed; this release did not repeat their visual review.
- Plugin manifest and official MCPB validation pass. The MCPB validator recommends
  a 512-pixel Claude icon; the current valid shared icon remains unchanged.

The initial source calibration attempt failed on the missing progress field. Its
client closed, leaving an interrupted synthetic job. The formal queue recovery
confirmed interruption; only the process proven to belong to that test was stopped.
The corrected run used a fresh directory. Failed evidence was not relabelled a pass.

## Size and overhead

Tool catalog UTF-8 size (serialized tool metadata): **178,008 bytes full**, **36,317
bytes economy** (20.4% of full). Both are within the documented 200 KB/40 KB budgets.
Repeated status-result validation measured **0.1489 ms median / 0.1782 ms p95** over
500 warm iterations on the development computer. These are a small local
microbenchmark, not an end-to-end performance or model-cost comparison. Output
schemas add metadata compared with 0.2.10. Actual Terra max/model tokens, reasoning
usage, first-attempt model success and charges were not measured in these scripts.

## Installation and host acceptance

The release preserves existing local runtime data, encrypted keys and per-account
private connections. User accounts and private connection identifiers are kept out
of this public record. Installation and account refresh results are recorded after
release deployment; package and protocol passes do not establish account acceptance.

The supported version family remains standard x64 Origin 2026 SR1 and 2026b SR2.
Current native checks above use licensed **2026b SR2 (10.350243)**. The 2026 SR1
baseline and earlier host acceptance remain historical; they were not rerun here.
Full GUI coverage, all Origin functions, all host/model combinations, Terra max
benchmarking and all file-delivery routes remain separate gates. The confirmed
OpenAI local Work project-sync frontend issue was not investigated or patched.

Keep 0.2.10 available for rollback. Use the
[installation guide](origin-agent/docs/INSTALL.md) and verify `origin_status` reports
plugin `0.2.11` and output contract `1.0.0` in each refreshed host/account.
