# Origin Companion development retrospective

Date: 2026-09-12. This is a Chembridge handoff for the next specialist-software plugin. Read [DEVELOPMENT_PRINCIPLES.md](DEVELOPMENT_PRINCIPLES.md) for the standing requirements and [NEXT_PLUGIN_ASSESSMENT.md](NEXT_PLUGIN_ASSESSMENT.md) for the product decision.

## What the project established

Origin Companion demonstrated a usable pattern: a general agent plans work, a small MCP interface dispatches jobs to the user's licensed Windows software, and the runtime returns editable native artifacts with verification. The same scientific implementation can serve different hosts. A passing connection check is narrower evidence than a completed scientific workflow.

The [0.2.9 acceptance record](WORK_ACCEPTANCE_0.2.9.md) records the frozen runtime's synthetic regression, independent numerical checks, OPJU reopening, exports, installation and actual Chat/cloud Work/Codex connection checks. Its 174 passing local tests and one permission-related skip are historical results for that release, not tests rerun for this retrospective. Full Origin coverage, every model, and every second-device scenario were not certified.

## Lessons to carry forward

| Observed issue or result | Development rule for the next plugin |
| --- | --- |
| A status call, process exit or openable file did not establish correct scientific output | Build one complete native workflow before broadening the tool catalog: import/create, execute, save, reopen, independently check, deliver |
| Native calculation defaults could alter the requested method, including fit weighting | Encode scientific choices explicitly; verify returned parameters and results against an independent reference |
| General script access and many successful examples did not establish complete feature coverage | Maintain an operation-by-operation matrix: implemented, native-verified, host-verified, unsupported or unverified |
| Long or failing jobs required diagnosis and recovery | Use bounded asynchronous jobs, progress, terminal error states, cancellation, idempotency and safe checkpoints; never retry uncertain writes blindly |
| Different software instances and continued edits could interfere | Identify the target device, document and revision; isolate jobs and preserve originals before editing |
| Retired registrations and stale tool maps produced Unknown tool | Stabilize product identity and tool contracts early; expose version/build/manifest identity and verify a fresh host after a registration change |
| Separate local and cloud entries confused ordinary users | Keep one visible entry per product on supported surfaces, with one execution core and thin adapters |
| MCP icon metadata did not populate ChatGPT's registered listing | Verify the saved listing, not just the manifest. The inspected form accepted a 256 px PNG below 10 KB; retain a separate small asset and recheck host requirements when they change |
| Repeated installation and migration met file locks and existing credentials | Detect per-user and system installations, preserve configuration, provide receipts/rollback, and reuse valid credentials instead of requesting new keys by default |
| An artifact existing on Windows did not prove user receipt | Track native output, attachment transfer, manual download and automatic saving separately; verify the delivered bytes and the chosen result location |
| Cloud-synchronised Git/build data caused storage and file-operation friction | Keep active repositories, runtimes and locks outside sync; use the authorised university cloud for verified cold development archives |
| Host context and corrections dominated some model calls | Benchmark complete workflows with GPT-5.6 Terra max; include failed attempts, cached/input/output/reasoning tokens and actual charges when available |

## Quality before breadth

Use the vendor's engine for the output the product promises. An open-format writer is useful for interchange, and an independent open-source library can check semantics or calculations, but neither establishes vendor execution. A native renderer also cannot correct a chemically wrong input or a poor supplied layout automatically.

Separate four checks: scientific/chemical correctness, native editability, visual quality at the intended use size, and actual host delivery. For figures, agree representative acceptable examples early and inspect fresh outputs, including difficult and negative cases. Do not use a large tool count or a green unit suite as a substitute for those checks.

Keep the ordinary interface small: status, on-demand help, a typed operation call, a common recipe and artifact retrieval. Resolve repetitive steps in deterministic code. Return compact results and paths; send full schemas, logs, images or data only when the task needs them. Record measured resource use; fewer entrypoints alone are not proof of lower billing.

## Scope boundary: OpenAI project synchronisation

The user has confirmed the local Work project-synchronisation problem as an OpenAI frontend bug and explicitly instructed us to stop attempting repairs. Treat it as an external known issue. Do not continue host investigation, change project caches or patch the application for this issue unless the user explicitly reopens it. The affected host check remains separately unverified; it is not an Origin defect to fix or a reason to claim a false pass.

## Reuse and delivery

Reuse the proven patterns for identity, typed jobs, bounded execution, artifact manifests, user-level installation, credential preservation and per-host acceptance. Extract a small shared library only when the second implementation demonstrates actual duplication. Each vendor keeps its own operation contracts and acceptance cases. Do not copy proprietary binaries, licences, private data or university teaching documents into GitHub.

For the next release, retain English GitHub documentation, downloadable packages and checksums, a clear installation path for non-developers, one product identity, update/rollback instructions and an honest tested-host matrix. Software detection, SDK documentation, native execution and user acceptance remain separate facts.
