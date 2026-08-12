# Offline Workstation Security and Recovery

Last reviewed: 2026-08-12

Knee Twin is currently an offline, single-researcher workstation application. These controls are operating requirements, not optional deployment suggestions. They do not authorize clinical use or identifiable medical-data ingestion.

## Required workstation controls

* Store the repository, SQLite database, artifact directory, temporary files, and backups only on organization-approved encrypted volumes.
* Use full-volume encryption with keys protected by the workstation's approved identity and recovery process.
* Keep the API and web application on loopback interfaces. Do not run Uvicorn or Next.js with `0.0.0.0`, a LAN address, a tunnel, or a public reverse proxy.
* Use a dedicated operating-system account with screen locking, current security updates, endpoint protection, and least-privilege access.
* Import only de-identified, authorized research evidence. Do not place names, medical-record numbers, dates of birth, or uncontrolled free-text identifiers in filenames, subject codes, or capture notes.
* Disable consumer cloud synchronization for research evidence unless the research protocol explicitly approves the provider, encryption, region, access, retention, and incident process. The current OneDrive-hosted development checkout must not hold sensitive cases in `data/local`.

The application rejects non-loopback CORS origins and the Next.js backend URL rejects non-loopback hosts. These are defense-in-depth checks; the operator must still bind both processes to loopback and maintain host firewall controls.

## Retention and deletion

Knee Twin does not silently age out evidence. A session's source recording, raw observations, overlays, derived artifacts, relational metadata, and integrity metadata are retained together until an authorized researcher explicitly deletes the session.

`DELETE /sessions/{id}?confirm=true` is the only application deletion workflow in this milestone. It stages the artifact bundle out of the published namespace, deletes relational metadata, and then removes the staged bundle. A database failure restores the staged bundle. Deletion is permanent in the live workspace and recoverable only from a separately retained backup. Backup retention and destruction follow the approved research protocol, not the application's live-session deletion.

Before deletion, download the session export manifest and confirm the session identifier, source filename, knee context, capture time, and integrity state. Do not delete a corrupt bundle until the discrepancy is investigated and the required evidence is recovered or formally dispositioned.

## Backup procedure

1. Stop the Next.js and FastAPI processes so SQLite and artifact manifests are quiescent.
2. Copy `KNEE_TWIN_DATABASE_PATH` and the entire `KNEE_TWIN_ARTIFACT_DIR` as one dated backup set. Do not select individual bundle files.
3. Encrypt the backup set before it leaves the approved encrypted workstation volume.
4. Record the backup-set identifier, creation time, source workstation, application revision, database migration versions, custodian, encryption method, and retention/disposal date outside the backup itself.
5. Restrict recovery keys separately from the backup media and test restoration on an offline encrypted volume.

## Recovery procedure

1. Keep the damaged workspace unchanged for investigation.
2. Restore the database and complete artifact directory from the same backup set into a new encrypted location.
3. Configure `KNEE_TWIN_DATABASE_PATH` and `KNEE_TWIN_ARTIFACT_DIR` to that location and start the API on `127.0.0.1` only.
4. Open the session export manifest for representative sessions. Every expected artifact must be `verified`; `missing`, `untracked`, or `checksum_mismatch` requires investigation.
5. Confirm session counts, source filenames/codes, analysis versions, and replay behavior before declaring recovery complete.
6. Record the recovery test, discrepancies, reviewer, and disposition.

Automated recovery coverage copies a complete database/artifact set, reopens it through fresh repositories, and verifies every expected session artifact against the durable bundle manifest.

## Integrity and incident handling

Each published bundle contains `artifact_manifest_v1.json`, which records filename, byte size, and SHA-256 for source and derived artifacts. New derived files are atomically replaced and then cause the bundle manifest to be atomically refreshed. Session export reports both the expected and actual hash.

Treat a missing or mismatched artifact, unexpected operation failure, unauthorized file access, lost device, exposed key, non-loopback binding, or uncontrolled synchronization as an incident. Stop processing, preserve logs and the affected workspace, record the known scope and time, notify the responsible research/security owner, and do not resume until disposition is authorized.

## Review boundary

This is a prototype security baseline, not a completed security certification. Before identifiable, medical, connected, multi-user, or clinical use, complete a formal threat model, privacy impact assessment, access-control design, audit design, vulnerability management process, incident exercises, data-processing agreements, and applicable institutional/regulatory review.
