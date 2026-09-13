# WorkBuddy acceptance follow-up: 0.2.10

## Scope and design

The user supplied a WorkBuddy acceptance report for 0.2.9 on Origin 2026b SR2.
Its three synthetic inputs and four local jobs were independently checked: numeric
results matched, and 20 artifact sizes/hashes matched their manifests. This is
bounded core-workflow evidence; the host model, effort and usage were not supplied.

1. Keep five economy entrypoints. Clarify direct help and operation dispatch in
   tool descriptions, on-demand guidance and the skill. Accept an accidentally
   wrapped read-only help request through normal MCP validation. Reject recursive
   dispatch and return structured discovery guidance for unknown operations.
   Do not replay writes or add a model service.
2. Keep `host_requirement` a string describing MCP capability. Add a separate
   conditional `host_recommendation` and optional Terra max benchmark preference.
   Preserve host-selected models and the unverified model-quality flag.
3. Keep the legacy `unknown_uncertainty` text field and add
   `unknown_uncertainty_result` with status, null value, stable reason and null
   method. Describe the unsupported inverse-calibration calculation accurately;
   do not imply that an unavailable input field would enable it.
4. Add per-axis auto/decimal/scientific tick formatting through the documented
   [Origin axis properties](https://docs.originlab.com/labtalk/ref/layer-axis-label-obj/).
   Auto uses scientific notation below 0.001 or at/above 100000 in absolute axis
   magnitude. Preserve values, units, scale and global preferences. Read formatting
   properties back after OPJU reopen. Explicit overrides use the full workflow
   style schema; common recipes gain auto formatting without extra parameters.

## Verification and delivery

- Portable regression: seven profiles, the actual five-tool discovery/dispatch
  contract, malformed help, recursive/unknown requests, no duplicate writes,
  tick-selection boundaries and explicit overrides.
- Isolated licensed native run: noisy nonzero-intercept calibration, unit/path
  conversion, interpolation/extrapolation, structured uncertainty, missing paired
  parameters, multi-series/error bars, numeric oracle, PNG/PDF/SVG/OPJU output and
  saved tick-property readback. Download bytes through MCP and compare hashes.
- Inspect generated figures. Keep OPJU/result evidence separate from host delivery.
- Measure compact schema bytes before/after; do not call those billed tokens.
- Build the self-contained Windows ZIP/MCPB, validate manifests, install alongside
  the retained previous version, reuse connection credentials, refresh the running
  bridge, and invoke the installed plugin. Publish English notes, checksums and
  sanitised evidence to GitHub as a preview.

No local Work frontend-bug repair, new cloud identity, remote-key replacement,
weighted regression or inverse-calibration interval implementation is in scope.
School 2026 SR1 and actual host/model acceptance require separate evidence.
