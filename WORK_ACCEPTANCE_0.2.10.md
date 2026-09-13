# Origin Companion 0.2.10 acceptance

Date: 13 September 2026. **Preview.** This maintenance release addresses the
user-supplied WorkBuddy feedback. It retains one plugin identity, one execution
core, five economy tools and the existing runtime dependencies.

## Changes

- Help requests accidentally wrapped in `origin_call` now succeed through validated
  read-only dispatch. Recursive dispatch is rejected; unknown operations return
  structured discovery guidance. The skill distinguishes direct entrypoints from
  full-mode operations. `origin_recipe` is a valid full-mode operation too.
- The MCP host requirement is separate from optional model advice. Terra max is
  a benchmark preference with `required: false`; the plugin does not select or
  detect the host model, and model-quality verification remains false.
- Unknown-concentration results retain the legacy string and add
  `unknown_uncertainty_result` with a status, null value, reason and null method.
  The reason accurately states that inverse-calibration uncertainty is unsupported
  by this workflow; there is no measurement-uncertainty input that silently enables it.
- Per-axis `auto`/`decimal`/`scientific` styles shorten very small/large tick labels.
  Formatting is checked again after native OPJU reopen. Data, units, linear scales
  and global Origin preferences remain unchanged.

## Current checks

| Layer | Evidence | Boundary |
| --- | --- | --- |
| Portable suite | 185 passed, one receiver test initially skipped; the receiver then passed with Node/PowerShell available | 186 distinct tests passed across the two runs; no model benchmark |
| Packaging | Skill/plugin validators and official MCPB 2.1.2 manifest validation passed; self-contained ZIP/MCPB about 31.57 MiB | Checksums are integrity checks, not a publisher code signature |
| Source native regression | Three graph pages, noisy nonzero-intercept calibration, unit conversion, 2 cm path, interpolation/extrapolation, error bars, notation overrides; 14 files downloaded and hashed | Origin 2026b SR2, standard Origin, x64 only |
| Frozen release regression | Same numerical/format/download checks passed with development Python paths removed; 18.797 s client-to-file completion, 15.5 s native execution | This scripted client timing is not a general-agent benchmark |
| Visual review | Two source PNGs, all three source PDFs/SVGs, and the registered-connector PNG inspected | Renderers can differ; Poppler font warnings were checked against actual rendered figures |
| Installation | Native self-test passed; version pointer, WorkBuddy and Claude commands use 0.2.10; both actual configured MCP commands returned five tools and the new version | These command checks are not a fresh WorkBuddy/Claude model session |
| Registered OpenAI connector | Actual calls in the current Codex task returned 0.2.10, recovered wrapped help, ran the native recipe and returned its preview | Does not certify a separate Chat, cloud Work or local Work task |
| Registered file receipt | PNG, PDF, SVG and OPJU saved using the bundled receiver; every local file was read back and matched size/SHA256 | Current host-file route only; not every browser automatic-download policy |

The noisy fixture returned slope **2993.428571428571**, intercept **0.01246** and
molar absorptivity **1496.7142857142856 L mol^-1 cm^-1** at 2 cm. The independent
Python standard-library regression agreed. Expressing the same concentrations in
mmol/L changed the slope by 1000 while preserving molar absorptivity.

The installed registered-connector fixture had a known nonzero intercept of 0.012
and slope 1500. It returned **1499.9999999999998**, **0.011999999999999997**, and an
unknown concentration of **5.0e-5 mol/L** for absorbance 0.087. These are synthetic
acceptance values, not experimental conclusions or a claim of 16-digit precision.

Economy tool definitions remain **5129 UTF-8 bytes**, unchanged from the measured
0.2.9 baseline; full mode is 22555 bytes. Added guidance lives in the skill or
on-demand responses. These figures exclude conversation, images and reasoning;
billed tokens, actual model/effort and provider charges were not measured.

## Upgrade and scope

The maintainer installation was upgraded with the existing account connection and
encrypted credentials. The WorkBuddy and Codex skills were refreshed, and 0.2.9
was retained for rollback. Existing host conversations/processes may need a
reconnect or a new conversation to load changed instructions.

The earlier WorkBuddy report establishes bounded **0.2.9** core-workflow evidence;
it does not become a 0.2.10 model pass by inheritance. This release does not retest
2026 SR1, every Origin function, general GUI transactions or every agent/model.
Panels remain separate graph pages. Error bars do not imply weighted regression.
Inverse-calibration confidence intervals and automatic fit-equation annotations
remain unsupported in the fixed recipe. The user-confirmed local Work project-sync
frontend issue was not investigated or patched.

See [machine-readable evidence](origin-agent/verification/release-0.2.10.json),
[repair design](origin-agent/docs/WORKBUDDY_FIX_PLAN.md), and
[installation instructions](origin-agent/docs/INSTALL.md).
