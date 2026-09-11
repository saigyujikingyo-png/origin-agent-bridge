---
name: origin-workflow
description: Use local licensed Origin to import scientific datasets, plot, fit, revise, batch and export editable OPJU projects through the Origin Agent MCP tools. Works with any MCP host; use for Origin automation and scientific plotting requests.
---

# Origin workflows

Translate the user's requested outcome into a validated workflow. Do not teach menus or ask the user to write code.

1. Call `origin_status` once per session. It does not launch Origin. An executable is not evidence of completed analysis.
2. Inspect the selected local file with `origin_inspect_dataset`. Use returned column names, row quality and dataset ID. Cloud attachment IDs are not Windows paths: obtain a real local file through the host's file transfer or ask where the Windows copy is. Never invent paths.
3. Resolve only missing scientific inputs: model, intercept, weighting, actual units and requested preprocessing. Reuse the user/lab manual's instructions. Style can use the report preset. Do not silently remove rows, subtract a baseline, force zero intercept or treat replicates as uncertainty.
4. Build one `origin_plan_workflow` containing related panels. Omit `analysis` for plotting. Fits require `kind`, `intercept` and `weighting="none"`. Error bars do not imply weighted fitting. Other weighting and nonlinear models are unsupported in this release.
5. When the task is authorized and scientific inputs clear, call `origin_run_workflow` directly. A plan is not an extra permission gate. Reuse its plan ID on reconnect: duplicate submission does not repeat computation.
6. Call `origin_get_job(wait_seconds=20)` instead of rapid polling. Retain IDs, not full datasets. Read detailed artifacts only when useful.
7. On `succeeded`, inspect relevant graphs with `origin_get_artifact(mode="preview")`. Check units, clipping, readable legends and agreement with the requested analysis. Return editable OPJU and useful images/fit summaries. The manifest records the engine, input hashes, model, checks and project index.
8. For revisions, call `origin_inspect_project`, modify the workflow and create a new plan. Revisions regenerate from immutable input; they do not preserve unrelated manual OPJU edits. Reuse dataset IDs. To intentionally retry after fixing a failed job's environment, set a new descriptive `revision` in the workflow. Do not loop automatic retries.

Failed, cancelled or interrupted jobs are not native success. Do not deliver partial files as verified. Do not use arbitrary Python/LabTalk or GUI clicking to bypass unsupported operations. Every computer needs its own activated Origin.

Computation is local; the host/model can receive requested summaries, previews and files. Cloud-agent use is not entirely offline. Report uncertainty and extrapolation; a good-looking graph or high R-squared does not establish scientific validity.
