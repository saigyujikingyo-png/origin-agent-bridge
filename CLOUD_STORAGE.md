# Chembridge development storage

Updated: 2026-09-12. The user selected their private University of Edinburgh OneDrive `Chembridge` folder for large development files across Chembridge. The folder was created through the university sign-in session and its private status was confirmed in the web interface. It is not a university shared site and is not automatically accessible to classmates, professors or public GitHub visitors.

This policy concerns development archives and local disk use. Plugin operation and result delivery do not require university OneDrive. Users may choose local folders, Work/other host attachments or another authorised destination. Record school, organisational or browser restrictions on automated downloads separately, and use an official authorised delivery route. Uploading to OneDrive or removing organisational restrictions is not a universal acceptance prerequisite.

## Where files belong

| Location | Contents |
| --- | --- |
| GitHub | Source, dependency locks, documentation, small public tests, sanitised acceptance records and distributable releases |
| Private OneDrive / Chembridge / datasets / plugin | Large inputs, downloaded public data and private data authorised for storage |
| Private OneDrive / Chembridge / validation / plugin / version | Full images, native projects, videos and larger acceptance materials |
| Private OneDrive / Chembridge / archives / plugin | Retained old builds, migration packages and historical archives |
| Local directory outside sync | Active checkouts, installed runtimes, virtual environments, locks, databases, running jobs and bounded caches |

Create subdirectories as needed. Keep personal cloud URLs and machine-specific paths in local configuration or ignored receipts, not the public repository. Cloud storage does not replace Git history and is not a live working directory for Origin, SQLite or builds.

The current maintainer checkout remains `C:\Projects\origin-companion`; the runtime remains under `%USERPROFILE%\.origin-agent`. The old OneDrive conversation entrypoint stays a compatibility entry, not a build directory.

## Archive and free local space

1. Identify cold project files, excluding the current installation/build, active jobs, credentials and at least one usable rollback version.
2. Archive selected content and record relative paths, sizes and SHA-256 hashes. Verify readability and file equality locally first.
3. Upload to the designated private folder, wait for completion, then download it again and compare byte count and SHA-256. A progress indicator or listed filename is not sufficient.
4. Retain verification receipts and recovery instructions locally; publish only suitable sanitised summaries.
5. Release the corresponding local cold copies after verification. In synced folders use OneDrive's **Free up space**, not **Delete**, which propagates to the cloud. Retain originals and record the reason if retention rules or incomplete verification prevent cleanup.

Retrieve large files on demand and check their hashes before use. Reuse cached content within capacity/recency limits. Restore to a temporary local folder, verify it, then move it into the working directory rather than computing while syncing. No additional resident sync daemon or paid cloud service was installed for this workflow.

## Data and permissions

Private experiments, coursework, restricted software and licences are not published with releases. Keep credentials in the host's credential store, outside archives. Do not change sharing permissions by default; sharing a particular artifact with named recipients is a separate user action.

Retention and storage quota depend on university policy and the actual account. The university page checked for this record distinguished 1 TB for A5 and 100 GB for A1; student status alone does not establish quota. Export materials needed long term before leaving the university, following its rules. [University OneDrive guidance](https://information-services.ed.ac.uk/computing/comms-and-collab/office365/onedrive-for-business)

OneDrive suits personal files. Choose an explicit SharePoint team location if shared maintenance becomes necessary; the current location is the user's requested private folder. [University cloud file storage guidance](https://information-services.ed.ac.uk/computing/desktop-personal/off-site-working/cloud-based-file-storage)

## Recorded observations

On 2026-09-12, the local Origin historical build area contained 26 subdirectories, approximately 3.335 GiB; installed versions totalled approximately 0.641 GiB. This inventory is not a claim of space already freed. Actual migration and reclaimed space are recorded per verified batch.

The first batch archived 482 files from an old 0.1.0 build to private `Chembridge/archives`. The downloaded 100,917,106-byte ZIP matched its original SHA-256, and each archived file matched the source. The old build outside sync and two temporary ZIPs were then removed, freeing 171,823,182 bytes (about 163.9 MiB) of original build content. The current build, runtime and rollback version were preserved. See the [sanitised receipt](origin-agent/verification/cloud-archive-2026-09-12.json).

The private folder now contains `archives`, `datasets` and `validation`; the account page showed 1 TB at that time. Remaining cold data has not been bulk-migrated. An agent completed this archive/upload/read-back/cleanup batch; no automatic reclamation policy has been enabled.

The user selected the university OneDrive Chembridge folder as the main Codex materials workspace. Its `AGENTS.md` and `START_HERE.md` distinguish cloud materials from each device's local source checkout. Archived files showed Windows `Offline` and `RecallOnDataAccess` metadata, consistent with Files On-Demand. This workspace setting does not automatically limit Codex caches, dependencies or working-copy sizes, and is not evidence of global automatic cleanup.
