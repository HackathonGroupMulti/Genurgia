"""Derive versioned knee-flexion series from preserved pose observations."""

from dataclasses import dataclass, replace
from typing import Literal

from analysis.angles import InvalidGeometryError, Point3D, knee_flexion_degrees
from analysis.confidence import conservative_joint_confidence, landmark_confidence
from analysis.filtering import centered_moving_average
from analysis.pose import LandmarkObservation, PoseFrameObservation

KNEE_FLEXION_CALCULATION_VERSION = "knee-flexion-world-3d-v1"
MINIMUM_MEASUREMENT_CONFIDENCE = 0.5
FILTER_NAME = "centered-moving-average-v1"
FILTER_WINDOW_SIZE = 5
FILTER_MINIMUM_VALID_VALUES = 3

Side = Literal["left", "right"]
MeasurementQuality = Literal[
    "valid",
    "low_confidence",
    "missing_pose",
    "missing_landmark",
    "invalid_coordinate",
    "degenerate_geometry",
]

LANDMARK_INDEXES: dict[Side, tuple[int, int, int]] = {
    "left": (23, 25, 27),
    "right": (24, 26, 28),
}


@dataclass(frozen=True, slots=True)
class KneeFlexionSample:
    timestamp_ms: int
    value_degrees: float | None
    filtered_value_degrees: float | None
    confidence: float | None
    quality: MeasurementQuality


@dataclass(frozen=True, slots=True)
class KneeFlexionSeries:
    side: Side
    samples: tuple[KneeFlexionSample, ...]


def derive_knee_flexion_series(
    frames: tuple[PoseFrameObservation, ...],
    side: Side,
) -> KneeFlexionSeries:
    samples = tuple(_sample_for_frame(frame, side) for frame in frames)
    filter_inputs = tuple(
        sample.value_degrees if sample.quality == "valid" else None for sample in samples
    )
    filtered_values = centered_moving_average(
        filter_inputs,
        window_size=FILTER_WINDOW_SIZE,
        minimum_valid_values=FILTER_MINIMUM_VALID_VALUES,
    )
    return KneeFlexionSeries(
        side=side,
        samples=tuple(
            replace(sample, filtered_value_degrees=filtered)
            for sample, filtered in zip(samples, filtered_values, strict=True)
        ),
    )


def _sample_for_frame(frame: PoseFrameObservation, side: Side) -> KneeFlexionSample:
    pose = next((item for item in frame.poses if item.pose_index == 0), None)
    if pose is None:
        return _unavailable_sample(frame.timestamp_ms, "missing_pose")

    landmarks_by_index = {landmark.index: landmark for landmark in pose.world_landmarks}
    required = tuple(landmarks_by_index.get(index) for index in LANDMARK_INDEXES[side])
    if any(landmark is None for landmark in required):
        return _unavailable_sample(frame.timestamp_ms, "missing_landmark")

    landmarks = tuple(landmark for landmark in required if landmark is not None)
    coordinates = tuple(_coordinates(landmark) for landmark in landmarks)
    if any(point is None for point in coordinates):
        return _unavailable_sample(frame.timestamp_ms, "invalid_coordinate")

    points = tuple(point for point in coordinates if point is not None)
    confidence = conservative_joint_confidence(
        landmark_confidence(landmark.visibility, landmark.presence) for landmark in landmarks
    )
    try:
        value = knee_flexion_degrees(points[0], points[1], points[2])
    except InvalidGeometryError:
        return KneeFlexionSample(
            timestamp_ms=frame.timestamp_ms,
            value_degrees=None,
            filtered_value_degrees=None,
            confidence=confidence,
            quality="degenerate_geometry",
        )

    quality: MeasurementQuality = (
        "valid"
        if confidence is not None and confidence >= MINIMUM_MEASUREMENT_CONFIDENCE
        else "low_confidence"
    )
    return KneeFlexionSample(
        timestamp_ms=frame.timestamp_ms,
        value_degrees=value,
        filtered_value_degrees=None,
        confidence=confidence,
        quality=quality,
    )


def _coordinates(landmark: LandmarkObservation) -> Point3D | None:
    if landmark.x is None or landmark.y is None or landmark.z is None:
        return None
    return (landmark.x, landmark.y, landmark.z)


def _unavailable_sample(timestamp_ms: int, quality: MeasurementQuality) -> KneeFlexionSample:
    return KneeFlexionSample(
        timestamp_ms=timestamp_ms,
        value_degrees=None,
        filtered_value_degrees=None,
        confidence=None,
        quality=quality,
    )
