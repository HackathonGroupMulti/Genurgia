# Processing and Reliability Evidence

Last measured: 2026-08-12

## Current execution decision

Squat extraction remains synchronous on the offline single-user workstation. Every successful extraction reports its input bytes, processed frames, wall-clock processing duration, average processing throughput, and operation identifier. SQLite records operation start, completion/failure stage, error class, sanitized detail, and duration.

The first measured MediaPipe run on the repository's attributed `squat-real.webm` fixture produced:

| Input | Evidence |
| --- | --- |
| File size | 527,508 bytes |
| Source duration | 7,100 ms |
| Decoded/processed frames | 213 |
| Processing duration | 4,318 ms |
| Average processing throughput | 49.3 frames/s |

This is one local Windows developer-workstation measurement, not a capacity guarantee. It supports retaining the simple synchronous boundary for the current short single-user protocol. Reassess when supported resolution/duration grows, multiple operations must overlap, or measured processing prevents safe interaction.

## Failure and cleanup behavior

* Request data streams in 1 MiB chunks to a hidden temporary file and fails at the configured byte limit.
* Empty, oversized, extension/content mismatches, and extraction failures do not publish a session bundle.
* Extraction writes into a hidden staging directory. One atomic rename exposes the bundle only after source, overlay, raw observations, and a SHA-256 manifest exist.
* Derived JSON uses temporary-file replacement and atomically refreshes the durable manifest.
* Request `finally` cleanup removes temporary uploads. Processing exceptions remove staging or a just-published bundle before metadata becomes visible.
* Startup marks leftover running operations as interrupted and removes abandoned upload/staging work from the single-worker workstation.

There is no user-facing mid-extraction cancellation because there is no job boundary. Terminating the workstation process can interrupt extraction; startup reconciliation makes that failure explicit and removes unpublished work. Milestone 13 introduces cancellable durable jobs for anatomical replay and later long-running work.
