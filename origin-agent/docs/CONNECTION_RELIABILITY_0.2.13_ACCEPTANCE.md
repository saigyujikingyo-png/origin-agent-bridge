# Connection reliability 0.2.13 candidate acceptance

Date: 2026-09-28. Status: locally installed candidate; selected Codex plugin route verified. This is a bounded product-owned repair receipt, not universal host or lifecycle acceptance.

## Problem and resulting behavior

A configured plugin could become unreachable after short connection failures. Accounts shared the vendor registry with other plugins, transient status errors caused immediate cleanup, and the controller eventually exhausted its retry budget. Failed cleanup could replace the original cause in diagnostics.

The candidate bundles official tunnel-client 0.0.15, pins both archive and executable hashes, and assigns each account a validated private state root. A proven live connection survives transient observation/network failures; longer outages use capped recovery intervals. Authentication and uncertain ownership stop safely. Manual stop intent and installer transaction fences remain authoritative. Scientific jobs are not replayed by reconnection.

Actual Windows Go-client fixtures also reproduced a cleanup error: psutil's thread-state heuristic can report running after a successful synchronous Windows process suspension. The controller now uses the successful Windows suspend operation as its quiescence barrier while retaining process identity checks and resuming preserved owners after refusal.

Vendor registration time is not process creation time. The candidate reads the isolated persisted process identity because the vendor status projection omits it, cross-checks alias/profile/PID, and compares OS creation time and executable before adoption.

## Evidence

| Layer | Result | Boundary |
| --- | --- | --- |
| Source regression | 361 passed, 2 skipped, 165.62 seconds; Ruff checks and formatting passed; lock checked offline | Windows source tests, including optional real-client fixtures; not every OS or native feature |
| Real vendor client | SHA-verified 0.0.15; concurrent isolated accounts; exact process identity; cleanup of one leaves the other live; refusal resumes preserved processes | Loopback control plane and synthetic MCP; no real-account failure injection |
| Recovery regressions | Transient timeout preserves live owner, delayed registration, missing daemon recovery, long network outage, stale status, mixed primary/cleanup errors and manual-stop/fence behavior | Controlled fixtures, not a workstation sleep or real WAN outage test |
| Package | 323 file hashes and 42 source/dependency fingerprints matched; ZIP and MCPB are identical, 58.55 MiB | Local candidate, not a published GitHub release |
| Native installer gate | Origin 2026b SR2 (10.350243), x64, activated standard edition; synthetic native read-back passed | Installation self-check only; no user mini-project work |
| Installed migration | 0.2.12 to 0.2.13 committed through the existing installation transaction; both existing account tasks retain enabled intent | Other products and old installed versions remain outside this upgrade |
| Account preservation | Existing tunnel identifiers and encrypted credential files preserved; normalized profile fingerprint matches after accounting for new health/log paths and the upgraded MCP command | Expected runtime locations changed; byte-for-byte profile equality is not claimed |
| Local connection | Both account supervisors and daemons live, fresh and locally ready after controlled start | Local readiness does not certify a remote account route |
| Actual plugin route | Two consecutive read-only `origin_status` calls from this Codex conversation returned 0.2.13 on the intended computer | One host-selected route; no claim for the other account or every host |
| User materials | All 23 pre-existing mini-project files retain their SHA-256 values | No fresh mini-project scientific run was submitted |

Candidate ZIP/MCPB SHA-256:

`41ad1ec289f7103afbd7be4943bd5d74044f4e9167fecd83cb9dc8d27162527a`

Official dependency archive SHA-256:

`3b53133a1e24d43f63088d843860cb1701a4c3ed6390de2e19f69089e43bddc1`

Official dependency executable SHA-256:

`1946de55a038313a9b9b2458d05fe1719fa9cf1f20a94dd5f38fc26a98bfdd42`

## Remaining acceptance

The shared legacy whole-map lost-update mechanism is supported by upstream code and the incident's competing state observations, but its exact historic interleaving was not reproduced. The previous unexplained supervisor exit remains unresolved. Neither is silently converted into a confirmed universal cause.

The earlier design's complete acceptance matrix remains a target. Long-duration operation, actual network interruption, logon/logoff, sleep/wake, reboot, additional account/host routes, and a fresh scientific workflow plus artifact delivery still need separate evidence. The confirmed external local Work project-sync issue remains out of scope. No Terra max benchmark or model-quality claim is made by these diagnostics.

## Routine use and recovery

For the already configured computer, select or mention Origin Companion and request work. The managed connection runs independently of the development checkout while the user is logged in and the computer is online. No terminal or manual reconnect is required for the verified route's ordinary use. Initial account linking, device availability and native licensing remain prerequisites.

Rollback uses the installation's existing receipt and preserves stop intent. It restores a previous runtime/configuration but does not certify connectivity and does not remove the earlier shared-state reliability risk. Private installation IDs, account details and full local evidence stay outside this public document.

## Primary implementation references

- [Repair design and proposed acceptance matrix](CONNECTION_RELIABILITY_0.2.13_DESIGN.md)
- [Runtime lifecycle](RUNTIME_LIFECYCLE.md)
- [Official client 0.0.15](https://github.com/openai/tunnel-client/releases/tag/v0.0.15)
- [Official state transaction lock](https://github.com/openai/tunnel-client/blob/v0.0.15/pkg/codexplugin/state/lock.go)
- [psutil Windows process suspension implementation](https://github.com/giampaolo/psutil/blob/release-7.2.2/psutil/arch/windows/proc.c)
