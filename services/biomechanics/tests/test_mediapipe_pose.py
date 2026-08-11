from pathlib import Path

import pytest

from analysis.mediapipe_pose import MediaPipePoseProvider

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
MODEL_PATH = REPOSITORY_ROOT / "data" / "models" / "pose_landmarker_full.task"
FIXTURE_VIDEO = REPOSITORY_ROOT / "data" / "fixtures" / "pose-person.mp4"


@pytest.mark.skipif(not MODEL_PATH.is_file(), reason="MediaPipe model has not been downloaded")
def test_mediapipe_extracts_timestamped_landmarks_and_overlay(tmp_path: Path) -> None:
    overlay_path = tmp_path / "annotated.mp4"

    result = MediaPipePoseProvider(MODEL_PATH).extract(FIXTURE_VIDEO, overlay_path)

    assert result.video.decoded_frame_count == 12
    assert result.video.fps == pytest.approx(10.0)
    assert [frame.timestamp_ms for frame in result.frames] == sorted(
        frame.timestamp_ms for frame in result.frames
    )
    detected_frames = [frame for frame in result.frames if frame.poses]
    assert detected_frames
    assert len(detected_frames[0].poses[0].image_landmarks) == 33
    assert overlay_path.stat().st_size > 0
