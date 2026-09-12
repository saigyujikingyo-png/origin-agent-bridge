# Capability coverage and delivery limits

Baseline: Origin 2026 SR1 (10.300197) and 2026b SR2 (10.350243), Windows x64, standard edition, activated and non-Demo. **The original cases below are from SR2. SR1 has separate four-dataset NIST and Terra max cloud Norris evidence; complete cloud receipt details remain open. SR1 does not inherit SR2's other pass results.** Native programming and GUI input expose licensed capabilities, but every function, App and dialog has not been accepted. `full_functionality_verified` remains false.

Use `origin_capabilities(query="coverage")` to read packaged categories, then discover local interfaces for the actual task. The machine-readable matrix is `src/origin_agent/data/coverage.json`; interface count is not a coverage percentage.

| Category | Recorded real cases | Further task-level acceptance |
| --- | --- | --- |
| Import and worksheets | CSV/TSV/XLSX, multiple columns, column calculations, names/data read-back; 4×5 matrix creation and saved-value read-back | All connectors and remaining sheet/matrix transformations |
| Plotting and details | 2D scatter/line/multi-Y/error bars, fit curves, axis text, visible/long titles, matrix 3D surface, continued OPJU editing | Other 3D/statistical graphs and complex layouts |
| Fitting | Free/fixed-intercept linear fits, Beer–Lambert, ExpDec1 parameter recovery | Other models, weights and specialist dialogs |
| Statistics, signals and peaks | Totals/regression diagnostics, count/mean/sample SD; native FFT of 32 sine samples, 3 Hz peak and amplitude 1 | Hypothesis tests, ANOVA and remaining signal/peak analyses |
| Templates and Apps | Native default graph templates | User/analysis templates and each third-party App |
| Projects and exports | OPJU save/reopen, PNG/PDF/SVG, sessions, checkpoints, recovery and project switching | Other formats and project combinations |
| GUI mechanisms | Menus/buttons/Edit, UIA selection/toggle/expand/collapse/value, click/drag-select/scroll/shortcuts/Chinese input, transaction read-back | Every custom editor/modal flow, locked or disconnected remote desktops |

Source extended-GUI acceptance completed 43 jobs: 39 successes and four expected refusals, in 111.718 seconds. Synthetic-only raw evidence is retained at the maintainer's `.local/gui-extended-acceptance-03/acceptance-gui.json`. [VALIDATION.md](VALIDATION.md) separately records frozen runtime and installation evidence; source success does not establish installed-package success.

The practical benefit is that the agent discovers functions, prepares native programs, batches work, handles necessary GUI steps and checks results. Scientific models, units and weights still need evidence. Native batches reduce GUI steps; repeated GUI observations take time, and screenshot-driven work requires vision support. No actual account token-saving percentage is established.

Each device's installation generates its local paths; users retain their own Origin licences and agent accounts. Local protocol or alternate-path tests do not certify all other devices or host models. The plugin is MIT-licensed and adds no paid model intermediary. See [current Work acceptance](../../WORK_ACCEPTANCE_0.2.8.md).
