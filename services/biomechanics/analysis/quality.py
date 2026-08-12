"""Versioned capture-level quality analysis from observable inputs."""

from dataclasses import dataclass
from typing import Literal

from analysis.kinematics import KneeFlexionSeries
from analysis.pose import PoseFrameObservation

CAPTURE_QUALITY_ALGORITHM_VERSION = "capture-quality-v1"
REQUIRED_IMAGE_LANDMARKS = frozenset({23, 24, 25, 26, 27, 28})
QualityStatus = Literal["pass", "warning", "fail", "unavailable"]


@dataclass(frozen=True, slots=True)
class QualitySignal:
    name: str
    value: float | bool | None
    unit: Literal["ratio", "millisecond", "count", "boolean"]
    status: QualityStatus
    criteria: str
    explanation: str


@dataclass(frozen=True, slots=True)
class CaptureQualityReport:
    status: Literal["pass", "warning", "fail"]
    signals: tuple[QualitySignal, ...]
    guidance: tuple[str, ...]


def assess_capture_quality(
    frames: tuple[PoseFrameObservation, ...],
    left: KneeFlexionSeries,
    right: KneeFlexionSeries,
    repetition_count: int,
) -> CaptureQualityReport:
    if not frames:
        raise ValueError("Capture quality requires at least one decoded frame.")
    if len(left.samples) != len(frames) or len(right.samples) != len(frames):
        raise ValueError("Capture quality inputs must have matching frame counts.")

    pose_coverage = sum(bool(frame.poses) for frame in frames) / len(frames)
    bilateral_valid = tuple(
        left_sample.quality == "valid"
        and right_sample.quality == "valid"
        and left_sample.filtered_value_degrees is not None
        and right_sample.filtered_value_degrees is not None
        for left_sample, right_sample in zip(left.samples, right.samples, strict=True)
    )
    bilateral_coverage = sum(bilateral_valid) / len(bilateral_valid)
    maximum_gap_ms = _maximum_unavailable_interval_ms(frames, bilateral_valid)
    framing_value = _framing_coverage(frames)

    signals = (
        QualitySignal(
            name="decode_validity",
            value=True,
            unit="boolean",
            status="pass",
            criteria="At least one frame decoded with positive video metadata.",
            explanation="The pose provider produced decoded frames for analysis.",
        ),
        _ratio_signal(
            "pose_detection_coverage",
            pose_coverage,
            pass_minimum=0.90,
            warning_minimum=0.70,
            explanation="Fraction of decoded frames containing pose index 0.",
        ),
        _ratio_signal(
            "bilateral_valid_knee_coverage",
            bilateral_coverage,
            pass_minimum=0.85,
            warning_minimum=0.60,
            explanation="Fraction of frames with valid filtered measurements for both knees.",
        ),
        _gap_signal(maximum_gap_ms),
        _framing_signal(framing_value),
        QualitySignal(
            name="complete_squat_cycle",
            value=repetition_count > 0,
            unit="boolean",
            status="pass" if repetition_count > 0 else "fail",
            criteria="At least one complete standing-to-bottom-to-standing cycle is detected.",
            explanation=(
                "A complete configured squat cycle was available."
                if repetition_count > 0
                else "No complete configured squat cycle was detected."
            ),
        ),
    )
    status: Literal["pass", "warning", "fail"] = (
        "fail"
        if any(signal.status == "fail" for signal in signals)
        else "warning"
        if any(signal.status in {"warning", "unavailable"} for signal in signals)
        else "pass"
    )
    return CaptureQualityReport(
        status=status,
        signals=signals,
        guidance=_guidance(signals),
    )


def _ratio_signal(
    name: str,
    value: float,
    *,
    pass_minimum: float,
    warning_minimum: float,
    explanation: str,
) -> QualitySignal:
    status: QualityStatus = (
        "pass" if value >= pass_minimum else "warning" if value >= warning_minimum else "fail"
    )
    return QualitySignal(
        name=name,
        value=value,
        unit="ratio",
        status=status,
        criteria=f"pass >= {pass_minimum:.2f}; warning >= {warning_minimum:.2f}; otherwise fail",
        explanation=explanation,
    )


def _gap_signal(value: int) -> QualitySignal:
    status: QualityStatus = "pass" if value <= 250 else "warning" if value <= 500 else "fail"
    return QualitySignal(
        name="maximum_unavailable_bilateral_interval",
        value=float(value),
        unit="millisecond",
        status=status,
        criteria="pass <= 250 ms; warning <= 500 ms; otherwise fail",
        explanation=(
            "Longest consecutive interval without valid filtered measurements for both knees."
        ),
    )


def _framing_signal(value: float | None) -> QualitySignal:
    if value is None:
        return QualitySignal(
            name="required_landmark_framing_coverage",
            value=None,
            unit="ratio",
            status="unavailable",
            criteria="pass >= 0.95; warning >= 0.80; otherwise fail",
            explanation="No detected frame contained all required image-space landmarks.",
        )
    return _ratio_signal(
        "required_landmark_framing_coverage",
        value,
        pass_minimum=0.95,
        warning_minimum=0.80,
        explanation=(
            "Fraction of evaluable detected frames with hips, knees, and ankles inside a 5% margin."
        ),
    )


def _framing_coverage(frames: tuple[PoseFrameObservation, ...]) -> float | None:
    evaluable = 0
    framed = 0
    for frame in frames:
        pose = next((pose for pose in frame.poses if pose.pose_index == 0), None)
        if pose is None:
            continue
        by_index = {landmark.index: landmark for landmark in pose.image_landmarks}
        required = [by_index.get(index) for index in REQUIRED_IMAGE_LANDMARKS]
        if any(
            landmark is None or landmark.x is None or landmark.y is None
            for landmark in required
        ):
            continue
        evaluable += 1
        if all(0.05 <= landmark.x <= 0.95 and 0.05 <= landmark.y <= 0.95 for landmark in required):
            framed += 1
    return framed / evaluable if evaluable else None


def _maximum_unavailable_interval_ms(
    frames: tuple[PoseFrameObservation, ...],
    valid: tuple[bool, ...],
) -> int:
    if all(valid):
        return 0
    timestamps = [frame.timestamp_ms for frame in frames]
    fallback_interval = (
        max(1, round((timestamps[-1] - timestamps[0]) / (len(timestamps) - 1)))
        if len(timestamps) > 1
        else 0
    )
    maximum = 0
    start: int | None = None
    for index, is_valid in enumerate((*valid, True)):
        if not is_valid and start is None:
            start = index
        elif is_valid and start is not None:
            end_timestamp = (
                timestamps[index]
                if index < len(timestamps)
                else timestamps[-1] + fallback_interval
            )
            maximum = max(maximum, end_timestamp - timestamps[start])
            start = None
    return maximum


def _guidance(signals: tuple[QualitySignal, ...]) -> tuple[str, ...]:
    guidance_by_name = {
        "pose_detection_coverage": (
            "Improve lighting and contrast, reduce occlusion, and keep one person visible."
        ),
        "bilateral_valid_knee_coverage": (
            "Keep both hips, knees, and ankles visible throughout the recording."
        ),
        "maximum_unavailable_bilateral_interval": (
            "Avoid camera obstruction and keep the full movement inside the frame."
        ),
        "required_landmark_framing_coverage": (
            "Move the camera back so hips, knees, and ankles stay away from frame edges."
        ),
        "complete_squat_cycle": (
            "Record a complete standing-to-bottom-to-standing squat at a steady pace."
        ),
    }
    return tuple(
        guidance_by_name[signal.name]
        for signal in signals
        if signal.status in {"warning", "fail", "unavailable"}
        and signal.name in guidance_by_name
    )
