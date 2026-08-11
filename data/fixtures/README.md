# Deterministic fixtures

`pose-person.mp4` is a 1.2-second, 480×360, 10 FPS decoder and pose-extraction fixture generated from the MediaPipe example image. It is intentionally small and contains no personal Knee Twin data.

Most tests inject deterministic pose observations so they do not rerun an ML model. The MediaPipe integration test uses this video when the downloaded model is available.

`squat-real.webm` is a 7.1-second real-person weighted-squat fixture used to validate the full pose-to-repetition path. Exact numerical behavior remains covered by synthetic signals because MediaPipe outputs can change with model versions.

See `SOURCE.md` for provenance.
