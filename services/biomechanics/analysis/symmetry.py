"""Pure, explicitly named bilateral difference calculations."""

from dataclasses import dataclass

SYMMETRY_ALGORITHM_VERSION = "bilateral-exact-differences-v1"


@dataclass(frozen=True, slots=True)
class BilateralDifferences:
    signed_rom_difference_degrees: float
    absolute_rom_difference_degrees: float
    signed_max_flexion_difference_degrees: float
    absolute_max_flexion_difference_degrees: float


def exact_bilateral_differences(
    *,
    left_rom_degrees: float,
    right_rom_degrees: float,
    left_max_flexion_degrees: float,
    right_max_flexion_degrees: float,
) -> BilateralDifferences:
    """Return left-minus-right differences; positive signed values mean left is greater."""

    signed_rom = left_rom_degrees - right_rom_degrees
    signed_max = left_max_flexion_degrees - right_max_flexion_degrees
    return BilateralDifferences(
        signed_rom_difference_degrees=signed_rom,
        absolute_rom_difference_degrees=abs(signed_rom),
        signed_max_flexion_difference_degrees=signed_max,
        absolute_max_flexion_difference_degrees=abs(signed_max),
    )
