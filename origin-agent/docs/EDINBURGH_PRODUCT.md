# Origin Companion: product scope and reuse decision

Updated: 2026-09-13. Origin Companion is an MIT-licensed open-source project developed and maintained with Codex for sharing with classmates, professors and researchers. The target is one plugin and shared execution core for ChatGPT Chat, local Work, cloud Work, Codex, Claude Desktop, WorkBuddy and other suitable general-purpose agents. The goal is natural-language access to the complete functionality of the specified, legally licensed Edinburgh Origin versions, with straightforward installation and continuous editing.

This is an independent sharing project. Official university distribution, campus SSO and central administration are not prerequisites.

## Development and agent use

- **Development:** Codex handles source changes, builds, tests and releases. Repositories, development terminals and engineering tools belong here.
- **User work:** users connect from their chosen agent, including Codex, provide data, describe research goals and check results. Installation, use and recovery should not require source clones, code projects, development servers or script expertise.
- **Local execution:** the package includes its Python runtime and runs on a Windows computer with activated target Origin. A cloud agent does not move Origin into the cloud. The runtime must be independent of the development task and terminal.
- **Acceptance:** test from the real user entrypoint of each host. CLI/protocol smoke tests, native scripts and CI establish their recorded checks; a complete agent workflow requires actual model calls, native outputs and delivered artifacts in that host.

Codex and other suitable agent integrations are end-user routes as well as development options. If a host asks for a folder, a research folder is sufficient; the plugin does not require Git. If a host requires a code project, record that as user friction rather than claiming the intended work scenario is complete. Cloud Work has real calls recorded; local Work requires separate acceptance.

## Two specified Origin builds

After checking the university download directory and second device on 2026-09-12, the user selected **Origin 2026 SR1 (10.300197)** and **Origin 2026b SR2 (10.350243)**, Windows x64, standard edition. SR1 was the observed university distribution; SR2 retains existing acceptance. Native workers allow these exact builds and check bitness, edition and non-Demo activation. Other builds are not automatically admitted.

Support and acceptance are separate. SR2 tests do not certify SR1. SR1 has passed four native datasets and a Terra max cloud Norris workflow through an independent normal-user runtime. Complete independent cloud artifact receipt details and the original tool-host startup issue remain open. Both builds retain `full_functionality_verified: false`.

The sharing package contains the plugin and required redistributable runtime only. Recipients supply their own activated Origin. Complete functionality is bounded by what that licensed version actually provides, including less common analysis, editing, Apps and GUI interactions; features exclusive to a different licence are not missing plugin features.

## Existing-project evaluation

The public GitHub review covered Origin/OriginPro MCP, natural-language automation, Edinburgh/university deployment, installation and host support. **No existing release was found with public evidence that it fully meets this target.** That is not proof that no related project exists.

| Project | Reusable work | Gap or insufficient evidence in the reviewed version |
| --- | --- | --- |
| Ge-Shun/origin-mcp | Origin 2026/2026b bridge; 25 compact tools/full mode; function knowledge; sheets, matrices, graphs, analysis and templates; Start/Stop OPX; instance/recovery design | Marked Alpha/testing; default dependency resolution failed locally until MCP 1.x was pinned; structured nonlinear fit reported outer success without executing; OPX installation and all host flows unverified |
| garethbeaumo/originlab-mcp | originpro/COM; 66 tools; import, graph editing, nonlinear fits and local configuration panel | A feature list does not prove complete Origin coverage or all target deployments/hosts |
| youngminsw/Origin-Pro-MCP | COM, separate sessions, recovery, MCP/CLI; statistics, signals, matrices and plots | Author reported OriginPro 2020 testing; standard 2026b and broad deployment require verification |
| Yike-Ye/OriginLab-MCP | Windows/VM remote control, actual graph-state read-back and compact tools | Mainly plotting and inspection; author reported Origin 2024, not an Edinburgh full-function release |

Ge-Shun v0.1.4 commit `fecb7226ed60d7651d921d2586eb9950bf16b618` was reviewed and tested in an isolated Python environment through actual MCP calls. With MCP 1.30.0 pinned, import, linear coefficients, matrix read/write, continued edits and OPJU save/reopen passed. Structured ExpDec1 did not, so overall strict acceptance failed. The 17-step test used the upstream serial bridge with a separate external Origin instance, not embedded OPX startup. See [candidate evaluation](CANDIDATE_EVALUATION.md).

## Technical decision

Selectively reuse the candidate's knowledge organisation, verified object adapters and session design. Evidence does not support simply repackaging it as a complete product. Retain Origin Companion's portable runtime, host wrappers, input snapshots and verification. The existing native nonlinear implementation, numerically verified on the same Origin build, addresses the observed fitting gap.

See [implementation design](IMPLEMENTATION_PLAN.md). Persistent sessions/checkpoints and the [GUI channel](GUI.md) have recorded native cases. Extend complex controls, sharing installation and function-category acceptance using real outcomes and correction counts. Retain MIT attribution if incorporating upstream modules. Candidate source currently exists only in ignored test directories and is not included in this release.

## Acceptance for a smooth, complete plugin

| Area | Completion criterion |
| --- | --- |
| Installation | One package, clear host selection, Origin discovery, connection and synthetic self-test; no source checkout, development terminal, manual JSON or separate Python; account authorisation identified separately |
| Functionality | Imports, sheets/matrices, 2D/3D, fitting, statistics, signals, peaks, templates, Apps and project interaction for the specified build; GUI coverage where APIs are insufficient; evidence per category |
| Continuous work | Edit the same project, preserve manual changes, inspect current objects/graphs, and restore explicit checkpoints without silently rebuilding away content |
| Learning effort | Users state research goals; the agent finds operations and supplies arguments; ask only for missing information affecting scientific conclusions, and provide actionable recovery |
| Results | Editable OPJU, traceable parameters/sources/steps, actual visual review and appropriate numerical checks |
| Shared use | Same code/interface, with individual data, settings and agent accounts; no developer-specific paths, keys or accounts |
| Hosts | ChatGPT Chat, local Work, cloud Work, Codex and each advertised other Agent entrypoint accepted independently, with consistent core workflows and without development-process dependencies |
| Performance/quota | On-demand discovery, batching, session reuse, short default summaries, no extra model service, and measured time/calls |
| Distribution | Shareable package/link, checksums, updates and rollback; clean-environment/different-user installation checks; classmate/staff trials inform usability without waiting for official university release |

Complete functionality means the plugin does not arbitrarily restrict the licensed version's scope. It does not mean AI cannot err, and neither tool count nor arbitrary script execution replaces acceptance.

## Host differences and current state

Local MCP generally requires the least account setup and uses each person's own agent account; execution remains on Windows. Cloud ChatGPT needs each recipient's supported connection and workspace permissions. Developer tunnel IDs/keys are not packaged. Campus deployment/SSO is outside the current scope. Mac users need a reachable licensed Windows computer or VM; native macOS Origin execution is not claimed.

Version 0.2 provides general programming, persistent sessions, Win32/UIA and screenshot input, automatic configuration and native installation checks. Broad mechanisms exist, but not every function, App, host/model or device is certified. See [validation history](VALIDATION.md), [coverage](COVERAGE.md) and [current Work evidence](../../WORK_ACCEPTANCE_0.2.8.md).

GitHub Releases remains the distribution route. One Windows package supports both target builds; upgrades reuse personal settings and encrypted credentials. Initial host selection uses text and first-time cloud setup still includes official account steps and scripts, so an entirely graphical one-click flow is not claimed. See [distribution principles](../../PUBLIC_DISTRIBUTION.md).

Sources reviewed: [School of Chemistry software](https://chem.ed.ac.uk/cto/student-support/computing-software), [Ge-Shun](https://github.com/Ge-Shun/origin-mcp), [v0.1.4](https://github.com/Ge-Shun/origin-mcp/releases/tag/v0.1.4), [tool modes](https://github.com/Ge-Shun/origin-mcp/blob/main/docs/tools.md), [native CI](https://github.com/Ge-Shun/origin-mcp/blob/main/.github/workflows/real-origin.yml), [garethbeaumo](https://github.com/garethbeaumo/originlab-mcp), [youngminsw](https://github.com/youngminsw/Origin-Pro-MCP), [Yike-Ye](https://github.com/Yike-Ye/OriginLab-MCP). These are dated evaluation sources, not claims about future upstream releases.
