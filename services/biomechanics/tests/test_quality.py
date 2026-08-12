from pathlib import Path

import pytest

from analysis.kinematics import (
    KneeFlexionSample,
    KneeFlexionSeries,
    derive_knee_flexion_series,
)
from analysis.mediapipe_pose import MediaPipePoseProvider
from analysis.pose import LandmarkObservation, PoseFrameObservation, PoseObservation
from analysis.quality import assess_capture_quality
from analysis.reps import detect_squat_repetitions

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
MODEL_PATH = REPOSITORY_ROOT / "data" / "models" / "pose_landmarker_full.task"
REAL_SQUAT_FIXTURE = REPOSITORY_ROOT / "data" / "fixtures" / "squat-real.webm"


def _landmark(index: int, x: float = 0.5, y: float = 0.5) -> LandmarkObservation:
    return LandmarkObservation(index, str(index), x, y, 0.0, 0.9, 0.9)


def _frames(count: int, missing: set[int] | None = None) -> tuple[PoseFrameObservation, ...]:
    missing = missing or set()
    landmarks = tuple(_landmark(index) for index in (23, 24, 25, 26, 27, 28))
    return tuple(
        PoseFrameObservation(
            frame_index=index,
            timestamp_ms=index * 100,
            poses=()
            if index in missing
            else (PoseObservation(0, landmarks, landmarks),),
        )
        for index in range(count)
    )


def _series(side: str, count: int, unavailable: set[int] | None = None) -> KneeFlexionSeries:
    unavailable = unavailable or set()
    return KneeFlexionSeries(
        side=side,
        samples=tuple(
            KneeFlexionSample(
                timestamp_ms=index * 100,
                value_degrees=None if index in unavailable else 50.0,
                filtered_value_degrees=None if index in unavailable else 50.0,
                confidence=None if index in unavailable else 0.9,
                quality="missing_pose" if index in unavailable else "valid",
            )
            for index in range(count)
        ),
    )


def test_capture_quality_passes_complete_well_framed_capture() -> None:
    frames = _frames(20)

    result = assess_capture_quality(frames, _series("left", 20), _series("right", 20), 2)

    assert result.status == "pass"
    assert result.guidance == ()
    assert all(signal.status == "pass" for signal in result.signals)


def test_capture_quality_reports_gaps_missing_pose_and_incomplete_cycle() -> None:
    frames = _frames(20, missing=set(range(10)))
    unavailable = set(range(8))

    result = assess_capture_quality(
        frames,
        _series("left", 20, unavailable),
        _series("right", 20, unavailable),
        0,
    )

    statuses = {signal.name: signal.status for signal in result.signals}
    assert result.status == "fail"
    assert statuses["pose_detection_coverage"] == "fail"
    assert statuses["maximum_unavailable_bilateral_interval"] == "fail"
    assert statuses["complete_squat_cycle"] == "fail"
    assert result.guidance


@pytest.mark.skipif(not MODEL_PATH.is_file(), reason="MediaPipe model has not been downloaded")
def test_real_fixture_reports_framing_failure_without_hiding_valid_signals(
    tmp_path: Path,
) -> None:
    extraction = MediaPipePoseProvider(MODEL_PATH).extract(
        REAL_SQUAT_FIXTURE,
        tmp_path / "annotated.mp4",
    )
    left = derive_knee_flexion_series(extraction.frames, "left")
    right = derive_knee_flexion_series(extraction.frames, "right")
    repetitions = detect_squat_repetitions(left, right)

    report = assess_capture_quality(extraction.frames, left, right, len(repetitions))
    signals = {signal.name: signal for signal in report.signals}

    assert report.status == "fail"
    assert signals["pose_detection_coverage"].status == "pass"
    assert signals["bilateral_valid_knee_coverage"].status == "pass"
    assert signals["maximum_unavailable_bilateral_interval"].status == "pass"
    assert signals["complete_squat_cycle"].status == "pass"
    assert signals["required_landmark_framing_coverage"].status == "fail"
