# Origin Companion 0.2.7: cloud artifact delivery

Historical report, 2026-09-11. Installed locally and accepted through actual cloud Work as a preview for standard Origin 2026b SR2 (10.350243), Windows x64. See [0.2.8](WORK_ACCEPTANCE_0.2.8.md) for subsequent evidence.

## What changed

Earlier versions generated and verified local files but returned resource references without establishing downloadable cloud artifacts. This version transfers verified binary files over the existing private MCP connection. If Work does not create attachments automatically, the plugin supplies an on-demand fixed receiver to save, verify and expose files in the host output directory. It avoids browser globals and persistent terminal input, two failure modes observed during retesting.

Numeric Unicode superscripts/subscripts in titles and axes are converted to Origin rich text to prevent missing-glyph boxes. Terminal failure, stop-polling and recovery guidance remain in place.

## Evidence

| Check | Result |
| --- | --- |
| Local tests | 132 passed, one skipped for Windows symlink permissions; Ruff lint/format passed |
| Final frozen runtime | Without development-runtime PATH, synthetic import, native fit, independent numbers, reopen and four binary downloads passed; workflow 14.594 seconds |
| Deliberate missing module | Terminal failure in 8.540 seconds with recovery guidance; success/fault suite 23.531 seconds |
| Data retrieval | Authorised original test data and instructions retrieved from Google Drive and independently checked; private sources not published |
| Actual Work model | GPT-5.6 Sol, light effort |
| Native Work execution | Reused the verified dataset; fixed native recipe job 12.386 seconds, execution/verification 10.672 seconds |
| Actual delivery | PNG, PDF, SVG and editable OPJU became real attachments; each size/SHA-256 matched the local artifact |
| Numbers and figures | Common analysis wavelength, free intercept, unweighted OLS; native report matched independent calculations; reopened data/labels passed; PNG and cloud PDF visually opened |
| Installed receiver discovery | Work requested the receiver from installed-plugin help and then downloaded/verified OPJU without user-copied code |
| Host configuration | Actual Claude Desktop, WorkBuddy and Codex cache launch commands returned 0.2.7 and five tools; not three host/model certifications |
| Runtime/package consistency | Existing private tunnel on 0.2.7, refreshed cloud metadata advertised download, all 306 installed files matched |
| Distribution | ZIP/MCPB about 31.55 MiB each; official MCPB manifest passed; no new runtime dependency |

The regenerate-and-deliver turn showed 3 minutes 6 seconds in Work; task timestamps differed by 188.888 seconds. **It reused previously retrieved data and excludes initial Drive retrieval.** This is neither a performance ceiling nor a universal latency claim. Host receiving/orchestration remains part of total Work time.

The displayed path length was a test assumption. No error bars were invented for data without replicates. Public records exclude coursework data, private conversation/Drive identifiers and account information.

## Efficiency and limits

Economy still exposed five tools, full mode 14. Compact tool JSON was 22,327 bytes full versus 5,125 economy, a 77.05% size reduction, not a billed-token, cost or success-rate reduction. The receiver loads only for delivery; binary contents are not printed into the model's text context.

This accepted the reproduced fixes and a real cloud case on the target build. It did not certify all Origin functions, a second physical device, all models, long unattended operation, local Work or other hosts' natural-language workflows. Binary MCP transfer is limited to **32 MiB per file**; the host needs file-saving support or the receiver's execution capability. Each user supplies their own Origin licence.

Installation paths were updated to 0.2.7. Documentation revisions preserved the verified executable bytes; installation integrity and the local native self-test passed again.

[Installation](origin-agent/docs/INSTALL.md) · [File receiver](origin-agent/skills/origin-workflow/references/FILE_DELIVERY.md) · [Reproduction script](origin-agent/scripts/verify_cloud_workflow.py) · [Machine-readable record](origin-agent/verification/release-0.2.7.json) · [Earlier GUI/function coverage](WORK_ACCEPTANCE_2026-09-11.md)
