import math

import pytest

from analysis.angles import (
    InvalidGeometryError,
    included_angle_degrees,
    knee_flexion_degrees,
    vector_between,
)


def test_vector_between_uses_point_minus_origin() -> None:
    assert vector_between((1, 2, 3), (4, 6, 8)) == (3.0, 4.0, 5.0)


def test_included_angle_for_perpendicular_vectors_is_90_degrees() -> None:
    assert included_angle_degrees((1, 0, 0), (0, 1, 0)) == pytest.approx(90.0)


def test_straight_modeled_leg_is_zero_flexion() -> None:
    assert knee_flexion_degrees(
        hip=(0, 1, 0),
        knee=(0, 0, 0),
        ankle=(0, -1, 0),
    ) == pytest.approx(0.0)


def test_right_angle_geometry_is_90_degrees_flexion() -> None:
    assert knee_flexion_degrees(
        hip=(0, 1, 0),
        knee=(0, 0, 0),
        ankle=(1, 0, 0),
    ) == pytest.approx(90.0)


@pytest.mark.parametrize(
    ("first", "second"),
    [
        ((0, 0, 0), (1, 0, 0)),
        ((math.nan, 0, 0), (1, 0, 0)),
    ],
)
def test_invalid_vectors_raise_explicit_error(first, second) -> None:
    with pytest.raises(InvalidGeometryError):
        included_angle_degrees(first, second)
