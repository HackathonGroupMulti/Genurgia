from pathlib import Path

import pytest

from analysis.kinematics import (
    KneeFlexionSample,
    KneeFlexionSeries,
    derive_knee_flexion_series,
)
from analysis.mediapipe_pose import MediaPipePoseProvider
from analysis.reps import SquatRepetitionConfig, detect_squat_repetitions

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
MODEL_PATH = REPOSITORY_ROOT / "data" / "models" / "pose_landmarker_full.task"
REAL_SQUAT_FIXTURE = REPOSITORY_ROOT / "data" / "fixtures" / "squat-real.webm"


def series(side: str, values: list[float | None], confidences: list[float] | None = None):
    samples = tuple(
        KneeFlexionSample(
            timestamp_ms=index * 200,
            value_degrees=value,
            filtered_value_degrees=value,
            confidence=(confidences[index] if confidences else 0.9) if value is not None else None,
            quality="valid" if value is not None else "missing_pose",
        )
        for index, value in enumerate(values)
    )
    return KneeFlexionSeries(side=side, samples=samples)


def test_detects_two_complete_repetitions_and_exact_boundaries() -> None:
    left_values = [10, 10, 40, 75, 90, 55, 20, 15, 40, 80, 100, 50, 20]
    right_values = [12, 12, 42, 77, 94, 57, 22, 17, 42, 82, 96, 52, 22]

    repetitions = detect_squat_repetitions(
        series("left", left_values),
        series("right", right_values),
    )

    assert len(repetitions) == 2
    assert (
        repetitions[0].start_timestamp_ms,
        repetitions[0].bottom_timestamp_ms,
        repetitions[0].end_timestamp_ms,
    ) == (200, 800, 1200)
    assert repetitions[0].left_rom_degrees == 80
    assert repetitions[0].right_rom_degrees == 82
    assert repetitions[0].mean_rom_degrees == 81
    assert repetitions[0].signed_rom_difference_degrees == -2
    assert repetitions[0].absolute_rom_difference_degrees == 2
    assert repetitions[0].signed_max_flexion_difference_degrees == -4
    assert repetitions[0].absolute_max_flexion_difference_degrees == 4
    assert repetitions[1].repetition_index == 2


def test_uses_peak_bilateral_flexion_as_bottom_and_propagates_minimum_confidence() -> None:
    values = [10, 10, 40, 75, 85, 95, 58, 20]
    confidences = [0.9, 0.9, 0.85, 0.8, 0.7, 0.6, 0.75, 0.9]

    repetition = detect_squat_repetitions(
        series("left", values, confidences),
        series("right", values, confidences),
    )[0]

    assert repetition.bottom_timestamp_ms == 1000
    assert repetition.confidence == 0.6


def test_rejects_shallow_incomplete_and_too_fast_cycles() -> None:
    shallow = [10, 10, 40, 60, 45, 20, 15]
    incomplete = [10, 10, 40, 75, 90, 80]
    too_fast = [10, 40, 75, 55, 20]

    assert detect_squat_repetitions(series("left", shallow), series("right", shallow)) == ()
    assert detect_squat_repetitions(series("left", incomplete), series("right", incomplete)) == ()
    assert (
        detect_squat_repetitions(
            series("left", too_fast),
            series("right", too_fast),
            SquatRepetitionConfig(minimum_duration_ms=1000),
        )
        == ()
    )


def test_excessive_bilateral_gap_discards_active_cycle() -> None:
    values = [10, 10, 40, None, None, None, 80, 55, 20]

    assert detect_squat_repetitions(series("left", values), series("right", values)) == ()


def test_allows_a_bounded_gap_without_filling_missing_measurements() -> None:
    values = [10, 10, 40, None, 75, 90, 55, 20]
    config = SquatRepetitionConfig(maximum_gap_ms=500)

    repetitions = detect_squat_repetitions(
        series("left", values),
        series("right", values),
        config,
    )

    assert len(repetitions) == 1
    assert repetitions[0].duration_ms == 1200


def test_completes_when_ascent_returns_directly_to_standing_at_sample_resolution() -> None:
    values = [10, 10, 40, 75, 90, 20]

    repetitions = detect_squat_repetitions(series("left", values), series("right", values))

    assert len(repetitions) == 1
    assert repetitions[0].end_timestamp_ms == 1000


def test_requires_aligned_bilateral_series() -> None:
    left = series("left", [10, 20])
    right = series("right", [10])

    try:
        detect_squat_repetitions(left, right)
    except ValueError as error:
        assert "equal sample counts" in str(error)
    else:
        raise AssertionError("Expected mismatched bilateral samples to be rejected.")


@pytest.mark.skipif(not MODEL_PATH.is_file(), reason="MediaPipe model has not been downloaded")
def test_real_squat_fixture_contains_two_complete_repetitions(tmp_path: Path) -> None:
    extraction = MediaPipePoseProvider(MODEL_PATH).extract(
        REAL_SQUAT_FIXTURE,
        tmp_path / "annotated.mp4",
    )

    repetitions = detect_squat_repetitions(
        derive_knee_flexion_series(extraction.frames, "left"),
        derive_knee_flexion_series(extraction.frames, "right"),
    )

    assert len(repetitions) == 2
    assert [repetition.bottom_timestamp_ms for repetition in repetitions] == pytest.approx(
        [2167, 5333], abs=100
    )
    assert all(repetition.mean_rom_degrees >= 60 for repetition in repetitions)
