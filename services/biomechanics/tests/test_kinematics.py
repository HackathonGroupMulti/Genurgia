from analysis.kinematics import derive_knee_flexion_series
from analysis.pose import (
    LandmarkObservation,
    PoseFrameObservation,
    PoseObservation,
)


def landmark(
    index: int,
    x: float | None,
    y: float | None,
    z: float | None = 0.0,
    confidence: float | None = 0.9,
) -> LandmarkObservation:
    return LandmarkObservation(
        index=index,
        name=str(index),
        x=x,
        y=y,
        z=z,
        visibility=confidence,
        presence=confidence,
    )


def frame(
    frame_index: int,
    *,
    left_ankle: tuple[float, float, float] = (0, -1, 0),
    confidence: float | None = 0.9,
) -> PoseFrameObservation:
    world_landmarks = (
        landmark(23, 0, 1, confidence=confidence),
        landmark(25, 0, 0, confidence=confidence),
        landmark(27, *left_ankle, confidence=confidence),
        landmark(24, 2, 1, confidence=confidence),
        landmark(26, 2, 0, confidence=confidence),
        landmark(28, 2, -1, confidence=confidence),
    )
    return PoseFrameObservation(
        frame_index=frame_index,
        timestamp_ms=frame_index * 100,
        poses=(
            PoseObservation(
                pose_index=0,
                image_landmarks=(),
                world_landmarks=world_landmarks,
            ),
        ),
    )


def test_series_derives_left_and_right_flexion_with_timestamps() -> None:
    frames = tuple(frame(index, left_ankle=(1, 0, 0)) for index in range(5))

    left = derive_knee_flexion_series(frames, "left")
    right = derive_knee_flexion_series(frames, "right")

    assert [sample.timestamp_ms for sample in left.samples] == [0, 100, 200, 300, 400]
    assert all(sample.value_degrees == 90.0 for sample in left.samples)
    assert all(sample.value_degrees == 0.0 for sample in right.samples)
    assert all(sample.filtered_value_degrees == 90.0 for sample in left.samples)


def test_low_confidence_value_is_labeled_and_excluded_from_filter() -> None:
    frames = tuple(frame(index, confidence=0.2 if index == 2 else 0.9) for index in range(5))

    sample = derive_knee_flexion_series(frames, "left").samples[2]

    assert sample.value_degrees == 0.0
    assert sample.confidence == 0.2
    assert sample.quality == "low_confidence"
    assert sample.filtered_value_degrees is None


def test_missing_pose_is_explicitly_unavailable() -> None:
    missing_frame = PoseFrameObservation(frame_index=0, timestamp_ms=0, poses=())

    sample = derive_knee_flexion_series((missing_frame,), "left").samples[0]

    assert sample.value_degrees is None
    assert sample.confidence is None
    assert sample.quality == "missing_pose"
