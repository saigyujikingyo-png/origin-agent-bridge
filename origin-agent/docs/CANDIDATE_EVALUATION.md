# Open-source candidate evaluation on the target Origin build

Date: 2026-09-11. Target: a personal sharing plugin for classmates and staff using the installed standard Origin 2026b SR2 (10.350243), Windows x64. This was not an official university deployment test.

## Candidate and environment

- Upstream: [Ge-Shun/origin-mcp](https://github.com/Ge-Shun/origin-mcp), v0.1.4, commit `fecb7226ed60d7651d921d2586eb9950bf16b618`.
- Isolated Python 3.12.14 environment with originpro 1.1.15, OriginExt 1.2.5 and pandas 3.0.5.
- Upstream dependency ranges initially resolved MCP 2.2.0; importing `mcp.server.fastmcp` failed. Pinning MCP 1.30.0 allowed startup.
- The upstream serial `OriginEmbeddedBridgeServer` ran in a separate Python process and created a test Origin through external originpro. No `attach()`, OPX installation or attachment to the user's active project was tested.
- Each test used synthetic data, temporary port/authentication and separate output. Only test-created Origin was closed; installed plugin configuration was preserved.
- The MCP 2 stdio client's initial new-protocol probe was rejected by the MCP 1 server, followed by successful compatibility negotiation. This was not a Claude, ChatGPT or WorkBuddy model test.

## Results

Strict acceptance completed 17 tool calls and nine checks: eight passed and one failed, so **overall acceptance failed**. An exploratory run that inspected only outer `ok` fields is not a pass.

| Check | Evidence |
| --- | --- |
| CSV import/read-back | 51 rows; first row `0, 2.3, 0.1` matched the synthetic input |
| Native linear fit | Intercept `0.09999999999999964`, slope `0.20000000000000007`; absolute errors below `1e-9` against 0.1/0.2 |
| Structured nonlinear fit | **Failed:** outer `ok: true`, inner `executed: false`, `result: false`, empty parameters |
| Smoothing | Origin reported execution, but output values were not independently checked; not complete algorithm acceptance |
| Continued cell edit | Wrote `0.123` and read it back |
| Matrix round-trip | `[[1,2,3],[4,5,6]]` matched |
| Save/reopen | Nonempty OPJU reopened with the edited value `0.123` intact |
| Figure | PNG decoded; two synthetic curves visually inspected, both the same colour; not publication-quality acceptance |

The failed command was:

```text
nlfit iy:=[Candidate]1!(1, 2) function:="ExpDec1" init_y0:=0.2 init_A1:=1.8 init_t1:=1.0;
```

This does not mean ExpDec1 is unavailable. Origin Companion's `op.NLFit('ExpDec1')` recovered `y0=0.3, A1=2.0, t1=1.4` with numerical assertions on the same Origin. The failure concerns the candidate path and error propagation, not the licence's nonlinear capability.

## Timing and context

The 17 steps totalled 21.687 seconds, excluding Origin cold start. Session cell write/read took about `0.078/0.063` seconds; a label edit 0.094 seconds; first import/plot/export 10.704 seconds. These are one-machine synthetic observations, not cross-device or stability guarantees.

Upstream full mode exposed 237 tools and about 379,300 bytes of serialised descriptions; source default compact mode had 25 tools. Fine-grained tool count can increase context without proving complete coverage. Prefer few entrypoints, on-demand arguments, batches and short summaries.

## Reuse decision and reproduction

The project offers useful knowledge organisation, object adapters and session design, but this test did not establish a ready-made release meeting the complete goal. Correct error propagation and accept analysis adapters before including them. Keep Origin Companion's portable runtime, snapshots, native assertions and host packaging as the foundation.

The route is native APIs → sessions/checkpoints → required GUI → read-back → category acceptance → installation without Python/JSON expertise. The user should state goals and scientific constraints and review results, not write LabTalk or Python.

In an isolated candidate environment, install the pinned commit, `mcp==1.30.0`, `originpro==1.1.15` and `OriginExt==1.2.5`; use this project's development environment as the MCP client:

```text
scripts/verify_candidate.py --candidate-dir <checkout> --candidate-python <candidate-python.exe> --output <new-directory>
```

The script pins the commit, creates its own Origin/authentication session, records each result and exits nonzero on strict failure. GUI, third-party Apps, all statistics, cancellation/crash recovery, embedded OPX, multiple Windows users and actual host models are outside this test. Candidate source is not included in the sharing package.
