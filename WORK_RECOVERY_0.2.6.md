# Origin Companion 0.2.6: cloud workflow recovery

Historical report, 2026-09-11. The repaired version was installed and passed a real cloud Work synthetic calibration; it remained a preview. For current status see [0.2.8 acceptance](WORK_ACCEPTANCE_0.2.8.md).

## Confirmed problems

The deleted Work conversation's complete tool history could not be recovered. Two local Beer–Lambert program failures remained: an import of unbundled NumPy, followed by an unavailable `GLayer.set_label` call. Neither produced a deliverable figure or OPJU. They were consistent with the screenshot's task, but did not explain all 13 minutes 40 seconds or establish time spent searching Drive.

A separate reproducible defect returned `poll_after_seconds=3` for failed jobs while progress still said executing. During diagnosis, Origin Companion existed in ChatGPT's personally created directory but was not installed/connected. The same app was restored and its tools refreshed. Runtime version and registered cloud metadata are separate checks.

## Changes

- `origin_import_table` accepts retrieved CSV/TSV text, validates it and creates an immutable snapshot; identical input reuses the dataset without repeated code embedding or guessed local paths.
- A Beer–Lambert recipe reuses native fitting, independent numerical checks, OPJU reopen and export verification. Intercept, weighting and actual units remain explicit.
- Failed/cancelled/interrupted jobs return `terminal=true`, stop polling, preserve the last execution stage and provide recovery guidance without automatically repeating writes.
- Tool/skill guidance prioritises fixed workflows and documents runtime dependencies and verified axis-label APIs.

## Recorded checks

| Check | Result |
| --- | --- |
| Windows unit/protocol tests | 125 passed; Ruff lint/format passed |
| Independent package | Without development-runtime PATH, cloud text import, native calibration and artifact checks passed in 13.657 seconds |
| Deliberate missing module | Terminal failure after 16.420 seconds, with stop-polling and recovery guidance |
| Actual cloud Work | GPT-5.6 Sol, light effort; synthetic table to final response in 111.831 seconds |
| Cloud job | Queue/execution 39.371 seconds; native execution/verification 34.313 seconds |
| Artifacts | PNG/PDF/SVG/OPJU, fit JSON and residual CSV generated; all six sizes/hashes matched; PNG visually reviewed; OPJU data/label reopen checks passed |
| Installation/connection | Local 0.2.6; same private app reconnected, background task on 0.2.6; other plugins preserved |

Six synthetic points, free-intercept unweighted OLS: slope 4800.95890410959, intercept 0.01973424657534234, R² 0.9999022836181513. With a 1 cm path and concentration in mol/dm³, absorptivity was 4800.9589 L·mol⁻¹·cm⁻¹; A=0.366 gave 7.212429×10⁻⁵ mol/dm³. These are engineering test data, not the user's experimental conclusion.

Economy retained five tools; full operations increased from 13 to 14. Tool-definition JSON was 21,837 bytes full versus 4,908 economy, 77.52% smaller; this is not billed-token or model-success evidence. The package was about 31.54 MiB with no added third-party runtime dependency.

A real Work failure-feedback check read an existing failed job once. It returned `failed`, `terminal=true`, no `poll_after_seconds`, and API recovery guidance. Work reported the failure and stopped after about 24.7 seconds without resubmission or further polling. No output was recovered from that old failed job.

## Limits

This verified the workflow after table input, without rereading Drive. The deleted task's complete waiting causes remain unknown. It does not guarantee all models, data sizes, network states or Origin features can never stall. Other computers, models, hosts and actual cloud download buttons needed separate acceptance at this stage. Local figures/OPJU were generated and available through MCP preview/resources; resource existence was not proof that every host could download them.

[Reproduction script](origin-agent/scripts/verify_cloud_workflow.py) · [Machine-readable record](origin-agent/verification/release-0.2.6.json) · [Earlier Work coverage](WORK_ACCEPTANCE_2026-09-11.md)
