# Next Chembridge plugin: ChemDraw or Mnova

Assessment date: 2026-09-12. Status: preparation and recommendation; native feasibility tests described below have not yet run. Apply [DEVELOPMENT_PRINCIPLES.md](DEVELOPMENT_PRINCIPLES.md) and the [Origin retrospective](ORIGIN_DEVELOPMENT_RETROSPECTIVE.md).

## Recommendation

Prioritise a bounded **ChemDraw native-engine feasibility and quality stage**. If it passes, make a dedicated ChemDraw companion the next product; keep Mnova next in the sequence. This priority addresses the owner's unresolved drawing-quality problem. Mnova has the clearer documented scripting route and is the alternative if the licensed ChemDraw edition or native quality path fails the first gate.

Do not count the existing ChemAIst prototype as completed ChemDraw automation. The owner reports that repeated outputs did not meet the required quality. Its open-format workflows and optional vendor adapters have a different product boundary. Reuse individually verified infrastructure where useful; requalify every drawing and vendor-execution component before reuse. This assessment does not rename, replace or modify the existing ChemAIst installation.

## Evidence available now

| Item | Current observation | What remains unknown |
| --- | --- | --- |
| Local ChemDraw | Windows uninstall registry reports ChemDraw 26.0.0; executable present | Actual edition entitlements, add-in access, supported native operations and a complete automated edit/export/reopen workflow |
| Local Mnova | Registry reports 17.0.41952; Python 3.11 runtime and official Python/JavaScript examples are installed | Current licensed modules, unattended entrypoint behavior, processing/export/reopen acceptance and other university installations |
| Installed ChemAIst | Runtime identity passed; version 0.12.20+codex.20260905161818; 53 discovered tools matched the runtime manifest | This check does not certify output quality or every adapter |
| ChemAIst rendering status | Native/RDKit/open-format backends were available; the configured ChemDraw renderer was unavailable | The status of its Python ChemScript import is not proof about every separately installed .NET/vendor interface |
| Mnova detection in ChemAIst | The adapter reported no detected Mnova although the current per-user installation exists | Detection needs requalification; do not confuse an adapter path failure with absence of the software |

The School of Chemistry's public table lists both ChemDraw and MNova for eligible students and home/non-university computers. It does not establish a uniform installed version or every module/SDK entitlement. Check the applicable school distribution and each execution device before declaring support. [University source](https://chem.ed.ac.uk/cto/student-support/computing-software)

## Native interface assessment

**ChemDraw.** Revvity's official add-in documentation describes access to the active document, CDXML input/output, a document PNG method and selection SVG output. Its guide explicitly describes limited access. `addCDXML` retains supplied coordinates and style: importing a poor layout does not repair it. The add-in repository also states that support depends on the product level. These are documented capabilities, not a successful test on this computer. [Official guide and examples](https://github.com/Revvity/ChemDraw-AddIns) · [API reference PDF, sections on Document and Selection](https://github.com/Revvity/ChemDraw-AddIns/blob/master/Documentation/ChemDraw%20JavaScript%20API%20Reference%20Guide.pdf)

**Mnova.** The vendor documents both Python and JavaScript scripting. Mnova 17's change log includes Python 3.11 and additional phase, multiplet, assignment and integral operations. Local examples use the official MnovaFramework/MnovaNMR interfaces to inspect peaks and process phase settings. Those examples were read, not executed. Existing nmrglue results must retain their independent provenance. [Mnova scripting](https://mestrelab.com/resources/mnova-python-the-holy-grail-of-automation.html) · [Mnova 17 change log](https://support.mestrelab.com/kb/article/567-what-s-new-in-mnova-17-changelog/)

| Decision factor | ChemDraw native companion | Mnova native companion |
| --- | --- | --- |
| Main user benefit | Reliable editable structures, reaction schemes and mechanisms with acceptable final graphics | Repeatable spectral import, processing, peak/integral reporting and editable analysis projects |
| Learning friction removed | Repeated drawing, styling, alignment, corrections and export steps | Repeated processing dialogs, parameter selection, batch handling and reporting |
| Main uncertainty | Native interface coverage, edition support, active-document control and high-quality complete-page layout | Licensed module coverage, script invocation, session isolation and scientifically defensible processing defaults |
| Quality challenge | Chemistry, stereochemistry, electron flow, spacing, labels, arrow geometry and native rendering all need checks | Phase/baseline/reference settings, peak overlap, integrals and interpretation need checks |
| Fit for economical models | High when a small typed scene and native recipes handle repetitive steps; harder for unconstrained mechanisms | High for parameterised reproducible recipes; ambiguous assignment must stay explicit |
| Relative engineering predictability | Lower until the native feasibility gate passes | Higher from the available scripting evidence; still unverified in an agent workflow |
| Recommended order | First feasibility stage, then first product if accepted | Next product, or earlier if the ChemDraw gate fails |

This is a qualitative engineering judgement, not measured comparative performance, a price comparison or a claim that open-source software generally has poor quality.

## First gate: prove the ChemDraw route

1. Identify the licensed edition and supported add-in API from the running vendor application. Establish a bounded bridge to the intended document. Do not assume a COM program identifier or a ChemScript library exists merely because ChemDraw is installed.
2. Prove native document read/write and image production with an isolated document, then save and reopen the editable result. Record the actual producing engine. A native PNG method or selection SVG method is not proof of native PDF/CDX export; validate each requested format separately.
3. Review three representative outputs: a structure sheet with charges/stereochemistry, an ordinary reaction with conditions and aligned components, and a short explicit electron-flow mechanism. Agree the target style and acceptable reference with the owner during this stage.
4. Check chemical semantics, bond and arrow geometry, labels/charges, collisions, readability at final size, editability and source preservation. Native import/export success alone does not pass the quality gate.
5. Prove one continued edit and one failure/recovery path, without modifying the user's existing document. Keep selection and active-document changes bound to a known session/revision.

**Advance** when native execution, acceptable representative graphics and editable round-trip are demonstrated on the licensed baseline. **Stop broad development** if the interface is inaccessible, requires an unconfirmed extra entitlement, or only renders the same rejected layouts. Investigate the missing capability within this bounded stage; if it remains blocked, advance the Mnova candidate instead of expanding an unaccepted drawing engine.

## Proposed ChemDraw implementation boundary

Use a small MCP facade and a supervised native worker. Prefer the supported ChemDraw add-in API for document access and available exports; add other verified official interfaces only for concrete missing operations. The bridge must verify local pairing and the intended document, reject unauthorised origins/requests, and provide a bounded failure when the native application is unavailable. Exact transport and launch behavior are feasibility items.

Prefer official structure generation/cleanup and style operations where the installed edition exposes them. Whole-page arrangement and electron-flow placement require a deterministic scene/layout contract and visual checks; do not assume the vendor will redesign imported coordinates. An independent chemistry library may validate identity, valence or atom mapping, with its actual provenance retained. It must not silently become the primary renderer when native output is requested.

Proposed module separation, to be created only after the feasibility decision:

```text
mcp/             small host-neutral tool surface
jobs/            bounded jobs, revisions, progress and recovery
adapters/        verified vendor API and document binding
scenes/          typed chemistry, layout constraints and style profiles
verification/    semantic, native round-trip and visual checks
artifacts/       editable outputs, manifests and verified delivery
installer/       per-user detection, setup, update and rollback
```

Expose status, on-demand operation help, a typed call, common recipes and artifact retrieval. Keep large schemas and screenshots out of routine calls. The agent supplies chemical intent and reviewed choices; the execution layer handles repeated edits and native operations. Preserve one visible plugin identity across supported hosts, and test each actual host separately.

## Mnova scope if selected next

Start with one declared 1D NMR workflow: identify/import a copied dataset, apply explicit processing/reference choices, produce peak/integral tables, save the native document, export a figure, reopen and compare the recorded results. Record acquired versus processed data, nucleus, solvent, units, referencing, phase/baseline choices and integral normalisation. Automatic processing is not automatic structural proof.

Use installed Mnova Python/JavaScript capabilities and verify their real invocation before promising headless use. Batch work through one bounded session and return compact numerical results. Treat qNMR, prediction, verification, MS/other modules and 2D capabilities as separately licensed and tested features. Preserve original FIDs and distinguish independent validation from native processing.

## Delivery stages after the first gate

| Stage | Exit evidence |
| --- | --- |
| Native vertical workflow | Correct native result, editable save/reopen, selected figure formats and recovery |
| Useful workflow set | Agreed representative cases, difficult and unsupported inputs, continued edits and owner quality acceptance |
| Agent acceptance | Natural-language requests in real hosts, GPT-5.6 Terra max benchmark, actual calls/retries/time/tokens and complete artifact receipt |
| Packaging | Non-developer installation, fresh install and upgrade, paths with spaces/per-user installs, credential reuse, rollback and removal |
| Sharing preview | English GitHub instructions, checksums, one product entry, tested-version/host matrix and explicit remaining gaps |

The first benchmark must include failed first attempts and human corrections. Other models and agents are targets until tested, not inheritances from Origin. Start on the verified Windows baseline; expansion to other versions or operating systems requires separate evidence.

The OpenAI frontend project-sync bug is outside this development scope by the user's instruction. Do not resume attempts to repair it. Keep that host limitation separate from the plugin's native and other-host acceptance.

## Prepared next action

Run the three-case ChemDraw native feasibility gate, then choose the product implementation based on its evidence and owner quality review. The present work prepared this plan, inspected installations and documentation, and read the existing plugin's status. It did not execute ChemDraw/Mnova scientific jobs or establish native feasibility.
