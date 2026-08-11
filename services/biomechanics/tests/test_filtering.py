import pytest

from analysis.filtering import centered_moving_average


def test_centered_moving_average_smooths_synthetic_signal() -> None:
    filtered = centered_moving_average(
        (0.0, 10.0, 0.0, 10.0, 0.0),
        window_size=3,
        minimum_valid_values=2,
    )

    assert filtered == pytest.approx((5.0, 10 / 3, 20 / 3, 10 / 3, 5.0))


def test_filter_preserves_missing_center_instead_of_interpolating() -> None:
    assert centered_moving_average(
        (1.0, None, 3.0),
        window_size=3,
        minimum_valid_values=2,
    ) == (None, None, None)


@pytest.mark.parametrize("window_size", [0, 2, -1])
def test_filter_rejects_invalid_window(window_size: int) -> None:
    with pytest.raises(ValueError):
        centered_moving_average((1.0,), window_size=window_size)
