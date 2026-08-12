from analysis.symmetry import exact_bilateral_differences


def test_exact_bilateral_differences_use_left_minus_right() -> None:
    result = exact_bilateral_differences(
        left_rom_degrees=65,
        right_rom_degrees=70,
        left_max_flexion_degrees=100,
        right_max_flexion_degrees=96,
    )

    assert result.signed_rom_difference_degrees == -5
    assert result.absolute_rom_difference_degrees == 5
    assert result.signed_max_flexion_difference_degrees == 4
    assert result.absolute_max_flexion_difference_degrees == 4


def test_exact_bilateral_differences_preserve_zero() -> None:
    result = exact_bilateral_differences(
        left_rom_degrees=70,
        right_rom_degrees=70,
        left_max_flexion_degrees=100,
        right_max_flexion_degrees=100,
    )

    assert result.signed_rom_difference_degrees == 0
    assert result.absolute_max_flexion_difference_degrees == 0
