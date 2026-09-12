# Detailed cloud Work acceptance: Origin Companion

Historical report, **2026-09-11**. Scoped acceptance passed after fixes and retesting; final installed version **0.2.5**. Later evidence is recorded in [0.2.8 acceptance](WORK_ACCEPTANCE_0.2.8.md), not retroactively assigned to these jobs.

The final installation completed **44 successful real Work jobs**: 43 GUI regression jobs and one two-panel batch. The entire run retained 104 queued jobs: 84 succeeded, 19 failed and one was intentionally cancelled. Six failures were deliberate protection/fault tests; the other 13 were pre-fix defects, API corrections or test interference. None were deleted or relabelled. Pre-submission refusals and transport errors are outside the queued-job count. All **266 declared artifacts** from successful jobs matched sizes/hashes, and synthetic input files retained their original hashes.

## Scope and evidence

An actual ChatGPT cloud Work task connected to local licensed Origin, not merely a local MCP client. The browser showed **GPT-5.6 Sol, light reasoning** (original UI label: `轻度`). The `gpt-terra`/economy preset controls interface/context preferences, not proof of Terra execution.

Environment: standard Origin 2026b SR2 (10.350243), Windows x64, non-Demo; originpro 1.1.15 and OriginExt 1.2.5. All inputs were dedicated synthetic CSV/TSV/XLSX/projects. No Drive coursework was read and no Edinburgh course requirements or real experimental conclusions were certified.

Passes required actual jobs, native read-back or relevant artifacts. Independent checks covered source/snapshot hashes, numerical fits, output manifests, sizes/hashes, PNG decoding, PDF/SVG formats and selected visual review. Structural program reopen does not independently validate every internal scientific value.

## Cloud phases

| Phase | Runtime | Result |
| --- | --- | --- |
| A: common workflows | 0.2.2 | CSV/TSV/XLSX, free/zero intercept, multi-Y, errors, Beer–Lambert, deduplication and paginated reads; discovered missing titles and plan-note issues |
| B: general interfaces | 0.2.2 | Nonlinear fit, copied-project editing, LabTalk, Origin C, snapshots, statistics and FFT ultimately passed; matrix output exposed a defect |
| R: regression | 0.2.3 | Exact XLSX sheet names, four visible panel titles, conditional notes, matrices/3D and saved-value read-back passed |
| C: sessions | 0.2.3 | Continued edits, stale refusal, error/checkpoint/cancellation recovery, two-session isolation and close passed |
| D: initial GUI | 0.2.4 | Observation, capture, menus, modal-commit refusal and code isolation passed; minimised hidden-dialog cleanup failed and session was safely closed |
| D-R: GUI regression | 0.2.5 | All 43 jobs succeeded: controls, Chinese text, commit, modal rollback, another begin and close |
| E: final package figures | 0.2.5 | Two-panel PNG/PDF/SVG/OPJU, unweighted fitting, reopened data/text passed |

A/B corrections and intermediate failures remain part of the record. Eventual success is not zero-intervention, first-attempt or cross-model success.

## Numbers and native capabilities

| Case | Independent expectation/read-back | Representative job |
| --- | --- | --- |
| Free-intercept unweighted OLS | slope 0.2004, intercept 0.0992, RSS 0.0002304, R² 0.9994266261 | bb35e9d3060b4d05a7f4a3e27d94a731 |
| Zero-intercept unweighted OLS | slope 0.2334666667, intercept 0 | bb35e9d3060b4d05a7f4a3e27d94a731 |
| Synthetic Beer–Lambert | slope/ε 4800, intercept 0.02; 1 cm and A=0.366 give 7.208333333e-5 mol/L | bb35e9d3060b4d05a7f4a3e27d94a731 |
| ExpDec1 | y0=0.3, A1=2, t1=1.4; 51 rows, native report/curve | 249cd2d6b56c46559c2483536e238ed6 |
| Continued copy editing | Axis/title annotation changed; source project hash preserved; native refit checked parameters | 90fd3e0cbefc41369c0fd2e4093ca8cd |
| LabTalk | Sum of squares 55; repeated submission reused the job | 4b2d7aaa03b04fbfae81a5f1f9fe0db3 |
| Origin C | Local compilation, square(7)=49 | b3a354756b604a879d26bf4374c4037d |
| File snapshot | Original CSV hash preserved; five rows, Absorbance total 2.5 | d9c592f2bbaf41fea6686a08b03f6d75 |
| Descriptive statistics | n=5, mean=3, sample SD=√2.5 | c605ce1790b1484bb0253e878e694023 |
| FFT | 32 samples, dt=1/32, native peak 3 Hz and amplitude 1 | 2249db52e3274ad6b855f7152351f9b5 |
| Matrix/3D | 4×5, first=11, last=54, total=650; native surface and OPJU | e9500a031e314fcdb13064fb4386a3af |
| Reopened matrix | Exact [MBook1]MSheet1! read-back: 11, 54, 650 | c51b1228417a487e94cb6dd81391f270 |

All listed linear fits explicitly used no weighting; displayed SD did not silently become weights. Test unknown concentrations are unrelated to the user's earlier assignment.

Four-panel titles/axes were reread from the saved project, and every corresponding PNG viewed. Long-title PDF/SVG were separately rendered, preserving Chinese text and wrapping. Matrix/3D retained default axis titles, so these were function-test figures, not ready-to-submit laboratory figures. A representative PDF used unembedded Arial and Type3 glyphs; local rendering passed, cross-computer font consistency remained unverified. Some extra B1 graphs contained scatter only; the native fit-result graph is the evidence for the fitted curve.

## Final installed batch

Job `63baa58393f6490b9e4bb9d84b203626`, plan `2abf4608ef897f57dab9a0056ddd3f69`, ran 0.2.5. Two figures, two native reports, two fit JSON/residual CSV sets and OPJU were produced. The manifest recorded 12.406 seconds for execution, not the whole cloud turn.

- Calibration: slope=0.2004, intercept=0.0992, RSS=0.0002304, R²=0.9994266260526787, n=5, weighting=none; SD for display only.
- Beer–Lambert: slope/ε=4800, intercept=0.02, RSS=0.000012, R²=0.9999784274870795, n=7; 1 cm and A=0.366 give 7.208333333333333e-5 mol/L.
- `project_reopened`, `data_roundtrip` and `graph_text_roundtrip` were true; two graphs, titles and native reports were reread.
- The supervising task independently checked numbers/hashes and both PNGs; rendered long-title PDF/SVG showed the complete three-line title, Chinese text, axes and curves.
- Final `project.opju`: 257,236 bytes; SHA-256 `06662a6eba7f3ee616add5bafeae22cad28d926ea6a116280e4f107d97e08f2f`.

Calibration's mmol/L was a synthetic display-test choice, not a source-unit determination from the unitless CSV header. Beer–Lambert explicitly used mol/L and 1 cm. Unknown absorbance uncertainty was not supplied; no unknown-concentration confidence interval was calculated.

## Sessions and recovery

The main session created X=[1,2,3], Y=[2,4,6], then changed Y to [3,6,9] using the same native PID. Stale revisions were rejected. A deliberate write/Save of 100/200/300 followed by an error recovered 3/6/9. Restoring the seed checkpoint recovered 2/4/6; cancelling a confirmed running long program also preserved 2/4/6 on next read.

A second session held X=[10,20], Y=[7,8], isolated from the first during switching. The supervising task independently checked eight vector sets and both sessions ended closed.

- Main close artifact: `7c269450629a4302afe45c55d3570e51/project.opju`.
- Second close artifact: `df1ccfc504b44cdcae6cf1686c72560c/project.opju`.
- Running cancellation: `95805d7e7534487f86e94dab3681d24f`.
- Successful recovery: `52cf4deeb9b343648f68f700fa9623da`.

Recovery covers Origin checkpoints, not external file/network/system effects. Normal Work idle-timeout recovery was not separately tested.

## Final installed GUI regression

All 43 D-R jobs succeeded. One initial wait during modal rollback reported Connection failed; querying the same job returned success without resubmitting a write. The transport cause remained unknown, so successful jobs do not imply every network call succeeded.

Checks included checkbox 0→1→0, Window Title selection Long name then Both, setting Long name to Drag Me, drag-select/delete, full Chinese input, screenshot-bound clicking and CTRL+A replacement. The exact final test string was `Origin Companion 验收成功` ("Origin Companion acceptance successful"); it remains quoted as original evidence.

- Chinese commit `a72fb18bef4843ba8a67d2257c71784e`; native read `a34626b4744845cab5db8f8bda8f30f3` matched the full name and X=[1,2,3].
- Uncommitted `Uncommitted name to discard`: `e052d4542e7d485aa98e5d62a29ec04b`.
- Rollback with modal still open: `c4d205aaa75241fc856c203fe7bbf5d4`; checkpoint reloaded, blocked=false.
- Post-rollback read `3fbea5949efc42c4bf6c951d0b5d9abb` retained committed Chinese text and X=[1,2,3].
- Begin/observe again: `4bcdec68c4bd44778268b2e8d4971042` / `16daa044f01746f7b435b1a3469640b3`.
- Final close `45c339eef8074826bc31e0fec22924a6`; session `8a1bd66a61fa25c8b6fea21b1c46db30`, revision=43, closed, no active transaction/job.
- Nineteen control/state/data checks were independently compared with no differences; the native dialog screenshot was viewed.

Work did not separately test scroll; the local extended-GUI script did. D-R opened Properties by shortcut, leaving no menu, so conditional dismiss was not triggered. Controlled minimisation failure/regression was local; Work 0.2.5 tested normal modal rollback and subsequent use. These scopes do not certify all GUI functionality.

## Defects and corrections retained

1. Missing planned graph titles: create actual text objects, wrap by text height, adjust layer space and compare title/axis text after reopen.
2. Unconditional error-bar/fit notes: generate notes from actual mappings and analysis requests.
3. Wrong XLSX sheet `Data` versus actual `Data 数据`: reject and list exact sheets; corrected call passed.
4. Nonexistent MSheet.rows/cols: use shape/depth and verify saved matrix data.
5. Minimisation hid a Properties dialog from observation; old rollback restored data but retained GUI blocking. Explicit rollback now validates the checkpoint and rebuilds only the owned Origin process. Unit/native fault tests passed; local full GUI took 90.703 seconds and allowed another begin.
6. Private connection ended with its parent and MSIX hid configuration from the background task. Use per-user shared state, preserve identity and supervise the child with bounded retries.
7. Model API corrections covered cumulative versus total sums, temporary fit trees not persisted in OPJU, allocated worksheet rows, explicit stats outputs and FFT table references. Failures and corrected guidance were retained.
8. Initial B5 interference came from the supervising task starting another Origin instance concurrently. Serialising native access resolved it; it is not model-capability evidence.

## Package and engineering quality

Installed Codex, Claude Desktop and WorkBuddy startup configurations were checked with actual MCP clients: 0.2.5 and five economy tools. Only Work had separate model-call evidence.

- Local Windows: 113 tests passed in 22.17 seconds; Ruff lint/format passed.
- Clean Windows/Ubuntu CI: [b8df531 run](https://github.com/saigyujikingyo-png/origin-agent-bridge/actions/runs/34628338565).
- Official MCPB manifest/icon validation passed, with a 512×512 display-size recommendation.
- ZIP/MCPB about 31.72 MiB each; installed size about 65.81 MiB; no external Python requirement or bundled Origin/licence.
- Package SHA-256: `25418ad58e738f33887d154881d4381c6d3cbd923a8bcba7a2a52633c4d1ace6`.
- Installation receipt: `096c75fcc0e74cd080b3550090230680`.
- Fifty third-party lock records matched the original baseline. An accidental pywin32-ctypes metadata change was corrected before publication.

The first 0.2.3 connection-exit test needed manual restart. Direct supervision subsequently recovered in about 31.615 seconds on 0.2.4 and 8.938 seconds on 0.2.5; the background parent was a Windows service, independent of Codex. One initial 0.2.4 launch returned 0xC0000142 and succeeded unchanged on retry; cause unknown. 0.2.5 started first time in this test. Full reboot, logout/login and long-term availability were not tested.

## Learning effort, efficiency and limits

Common imports, fits, export and OPJU use recipes/batches instead of menus. A representative four-panel native phase took about 12.25 seconds, excluding total Work reasoning, calls and review.

Tool JSON shrank from 13 tools/19,514 bytes to five/4,372 bytes, 77.6%; these are UTF-8 bytes, not account tokens, charges or model success rates. Complex programs/GUI still need scientific choices, correct APIs and result checks. Actual corrections and repeated GUI calls preclude a promise of zero learning or first-attempt success. Screenshot input needs an interactive desktop and may require re-observation after minimisation, focus or layout changes.

At this report's date, `full_functionality_verified` remained false: all menus, Apps, dialogs, statistics, OriginPro features and formats were not accepted. A second physical device, other accounts/models and actual Claude/WorkBuddy model workflows remained unverified. This is personal sharing for licensed users, not official university/OriginLab distribution.

Small synthetic inputs do not establish large-data stress or concurrent throughput. Routine import defaults were 25 MiB/file, 250,000 rows, 128 columns and 12 panels/job. Native execution uses a serial device queue; session isolation does not mean concurrent GUI control.

The 43 cloud GUI jobs spanned **25 minutes 52 seconds** from first submission to final close. Their `verification.seconds` total was about **41.1 seconds**, excluding all pre-observation, queueing, cloud reasoning, calls, image reads and test corrections. It cannot be used to allocate each cost component. This demonstrates remaining cloud GUI round-trip friction; prefer recipes and batched native programs.

Editorial correction: the original Work report called Python package originpro 1.1.15 "OriginPro 1.1.15". Actual status/manifests confirm the application was standard Origin. Original reports, failures and corrections are retained in local evidence.
