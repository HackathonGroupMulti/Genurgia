import numpy as np
import pytest

from analysis.reconstruction_quality import evaluate_structure_agreement


def test_identical_structure_masks_have_perfect_agreement() -> None:
    mask = np.zeros((5, 5, 5), dtype=bool)
    mask[1:4, 1:4, 1:4] = True
    result = evaluate_structure_agreement(mask, mask, (0.5, 0.5, 1.0))
    assert result.dice_coefficient == 1
    assert result.average_symmetric_surface_distance_mm == 0
    assert result.hausdorff_95_mm == 0


def test_shifted_masks_report_distances_in_physical_millimetres() -> None:
    candidate = np.zeros((4, 4, 4), dtype=bool)
    reference = np.zeros_like(candidate)
    candidate[1, 1, 1] = True
    reference[2, 1, 1] = True
    result = evaluate_structure_agreement(candidate, reference, (2.0, 1.0, 1.0))
    assert result.dice_coefficient == 0
    assert result.average_symmetric_surface_distance_mm == 2
    assert result.hausdorff_95_mm == 2


def test_missing_or_mismatched_masks_are_not_invented() -> None:
    empty = np.zeros((2, 2, 2), dtype=bool)
    with pytest.raises(ValueError, match="contain"):
        evaluate_structure_agreement(empty, empty, (1, 1, 1))
    with pytest.raises(ValueError, match="shape"):
        evaluate_structure_agreement(empty, np.zeros((3, 3, 3)), (1, 1, 1))
