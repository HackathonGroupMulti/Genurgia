"""Pure squat-phase segmentation from bilateral knee-flexion series."""

from dataclasses import dataclass
from typing import Literal

from analysis.kinematics import KneeFlexionSample, KneeFlexionSeries

SQUAT_REPETITION_ALGORITHM_VERSION = "bilateral-squat-state-machine-v1"

SquatPhase = Literal["standing", "descending", "bottom", "ascending"]


@dataclass(frozen=True, slots=True)
class SquatRepetitionConfig:
    standing_max_degrees: float = 25.0
    descent_start_min_degrees: float = 35.0
    bottom_min_degrees: float = 70.0
    bottom_exit_max_degrees: float = 60.0
    minimum_duration_ms: int = 800
    maximum_duration_ms: int = 10_000
    maximum_gap_ms: int = 500
    minimum_side_rom_degrees: float = 35.0


DEFAULT_SQUAT_REPETITION_CONFIG = SquatRepetitionConfig()


@dataclass(frozen=True, slots=True)
class SquatRepetition:
    repetition_index: int
    start_timestamp_ms: int
    bottom_timestamp_ms: int
    end_timestamp_ms: int
    duration_ms: int
    left_max_flexion_degrees: float
    right_max_flexion_degrees: float
    left_rom_degrees: float
    right_rom_degrees: float
    mean_rom_degrees: float
    confidence: float


@dataclass(frozen=True, slots=True)
class _BilateralSample:
    timestamp_ms: int
    left_degrees: float | None
    right_degrees: float | None
    confidence: float | None

    @property
    def mean_degrees(self) -> float | None:
        if self.left_degrees is None or self.right_degrees is None:
            return None
        return (self.left_degrees + self.right_degrees) / 2


@dataclass(slots=True)
class _Candidate:
    start_timestamp_ms: int
    last_valid_timestamp_ms: int
    peak_timestamp_ms: int
    peak_mean_degrees: float
    minimum_left_degrees: float
    maximum_left_degrees: float
    minimum_right_degrees: float
    maximum_right_degrees: float
    minimum_confidence: float
    phase: Literal["descending", "bottom", "ascending"] = "descending"

    def include(self, sample: _BilateralSample) -> None:
        assert sample.left_degrees is not None
        assert sample.right_degrees is not None
        assert sample.confidence is not None
        assert sample.mean_degrees is not None
        self.last_valid_timestamp_ms = sample.timestamp_ms
        self.minimum_left_degrees = min(self.minimum_left_degrees, sample.left_degrees)
        self.maximum_left_degrees = max(self.maximum_left_degrees, sample.left_degrees)
        self.minimum_right_degrees = min(self.minimum_right_degrees, sample.right_degrees)
        self.maximum_right_degrees = max(self.maximum_right_degrees, sample.right_degrees)
        self.minimum_confidence = min(self.minimum_confidence, sample.confidence)
        if sample.mean_degrees > self.peak_mean_degrees:
            self.peak_mean_degrees = sample.mean_degrees
            self.peak_timestamp_ms = sample.timestamp_ms


def detect_squat_repetitions(
    left: KneeFlexionSeries,
    right: KneeFlexionSeries,
    config: SquatRepetitionConfig = DEFAULT_SQUAT_REPETITION_CONFIG,
) -> tuple[SquatRepetition, ...]:
    """Return complete bilateral squat cycles; never fill missing measurements."""

    _validate_inputs(left, right, config)
    repetitions: list[SquatRepetition] = []
    last_standing: _BilateralSample | None = None
    candidate: _Candidate | None = None

    for sample in _bilateral_samples(left, right):
        mean_degrees = sample.mean_degrees
        if mean_degrees is None:
            continue

        if (
            candidate is not None
            and sample.timestamp_ms - candidate.last_valid_timestamp_ms > config.maximum_gap_ms
        ):
            candidate = None
            last_standing = None

        if candidate is None:
            if mean_degrees <= config.standing_max_degrees:
                last_standing = sample
            elif (
                last_standing is not None
                and mean_degrees >= config.descent_start_min_degrees
                and sample.timestamp_ms - last_standing.timestamp_ms <= config.maximum_gap_ms
            ):
                candidate = _start_candidate(last_standing, sample)
            continue

        candidate.include(sample)
        if candidate.phase == "descending":
            if mean_degrees >= config.bottom_min_degrees:
                candidate.phase = "bottom"
            elif mean_degrees <= config.standing_max_degrees:
                candidate = None
                last_standing = sample
        elif candidate.phase == "bottom":
            if mean_degrees <= config.bottom_exit_max_degrees:
                candidate.phase = "ascending"
        elif mean_degrees >= config.bottom_min_degrees:
            candidate.phase = "bottom"

        if (
            candidate is not None
            and candidate.phase == "ascending"
            and mean_degrees <= config.standing_max_degrees
        ):
            completed = _complete_candidate(candidate, sample.timestamp_ms, config)
            if completed is not None:
                repetitions.append(
                    SquatRepetition(
                        repetition_index=len(repetitions) + 1,
                        **completed,
                    )
                )
            candidate = None
            last_standing = sample

    return tuple(repetitions)


def _start_candidate(start: _BilateralSample, current: _BilateralSample) -> _Candidate:
    assert start.left_degrees is not None
    assert start.right_degrees is not None
    assert start.confidence is not None
    assert start.mean_degrees is not None
    candidate = _Candidate(
        start_timestamp_ms=start.timestamp_ms,
        last_valid_timestamp_ms=start.timestamp_ms,
        peak_timestamp_ms=start.timestamp_ms,
        peak_mean_degrees=start.mean_degrees,
        minimum_left_degrees=start.left_degrees,
        maximum_left_degrees=start.left_degrees,
        minimum_right_degrees=start.right_degrees,
        maximum_right_degrees=start.right_degrees,
        minimum_confidence=start.confidence,
    )
    candidate.include(current)
    return candidate


def _complete_candidate(
    candidate: _Candidate,
    end_timestamp_ms: int,
    config: SquatRepetitionConfig,
) -> dict[str, int | float] | None:
    duration_ms = end_timestamp_ms - candidate.start_timestamp_ms
    left_rom = candidate.maximum_left_degrees - candidate.minimum_left_degrees
    right_rom = candidate.maximum_right_degrees - candidate.minimum_right_degrees
    if not config.minimum_duration_ms <= duration_ms <= config.maximum_duration_ms:
        return None
    if min(left_rom, right_rom) < config.minimum_side_rom_degrees:
        return None
    return {
        "start_timestamp_ms": candidate.start_timestamp_ms,
        "bottom_timestamp_ms": candidate.peak_timestamp_ms,
        "end_timestamp_ms": end_timestamp_ms,
        "duration_ms": duration_ms,
        "left_max_flexion_degrees": candidate.maximum_left_degrees,
        "right_max_flexion_degrees": candidate.maximum_right_degrees,
        "left_rom_degrees": left_rom,
        "right_rom_degrees": right_rom,
        "mean_rom_degrees": (left_rom + right_rom) / 2,
        "confidence": candidate.minimum_confidence,
    }


def _bilateral_samples(
    left: KneeFlexionSeries,
    right: KneeFlexionSeries,
) -> tuple[_BilateralSample, ...]:
    output: list[_BilateralSample] = []
    for left_sample, right_sample in zip(left.samples, right.samples, strict=True):
        left_value = _valid_filtered_value(left_sample)
        right_value = _valid_filtered_value(right_sample)
        confidences = (left_sample.confidence, right_sample.confidence)
        confidence = (
            min(value for value in confidences if value is not None)
            if left_value is not None
            and right_value is not None
            and all(value is not None for value in confidences)
            else None
        )
        output.append(
            _BilateralSample(
                timestamp_ms=left_sample.timestamp_ms,
                left_degrees=left_value,
                right_degrees=right_value,
                confidence=confidence,
            )
        )
    return tuple(output)


def _valid_filtered_value(sample: KneeFlexionSample) -> float | None:
    if sample.quality != "valid":
        return None
    return sample.filtered_value_degrees


def _validate_inputs(
    left: KneeFlexionSeries,
    right: KneeFlexionSeries,
    config: SquatRepetitionConfig,
) -> None:
    if left.side != "left" or right.side != "right":
        raise ValueError("Repetition detection requires left and right series in that order.")
    if len(left.samples) != len(right.samples):
        raise ValueError("Left and right series must have equal sample counts.")
    if any(
        left_sample.timestamp_ms != right_sample.timestamp_ms
        for left_sample, right_sample in zip(left.samples, right.samples, strict=True)
    ):
        raise ValueError("Left and right sample timestamps must match.")
    if not (
        config.standing_max_degrees
        < config.descent_start_min_degrees
        < config.bottom_min_degrees
    ):
        raise ValueError("Phase thresholds must increase from standing to descent to bottom.")
    if not config.standing_max_degrees < config.bottom_exit_max_degrees < config.bottom_min_degrees:
        raise ValueError("Bottom exit must provide hysteresis between standing and bottom.")
    if config.minimum_duration_ms <= 0 or config.maximum_duration_ms < config.minimum_duration_ms:
        raise ValueError("Duration limits must be positive and ordered.")
    if config.maximum_gap_ms < 0 or config.minimum_side_rom_degrees < 0:
        raise ValueError("Gap and ROM limits cannot be negative.")
