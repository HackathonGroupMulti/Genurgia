import pytest

from analysis.confidence import conservative_joint_confidence, landmark_confidence


def test_landmark_confidence_uses_least_favorable_available_signal() -> None:
    assert landmark_confidence(visibility=0.8, presence=0.6) == 0.6
    assert landmark_confidence(visibility=0.8, presence=None) == 0.8


def test_landmark_confidence_is_unavailable_without_provider_signals() -> None:
    assert landmark_confidence(None, None) is None


def test_joint_confidence_requires_every_landmark_and_uses_minimum() -> None:
    assert conservative_joint_confidence((0.9, 0.7, 0.8)) == 0.7
    assert conservative_joint_confidence((0.9, None, 0.8)) is None


def test_invalid_confidence_is_rejected() -> None:
    with pytest.raises(ValueError):
        landmark_confidence(1.2, 0.8)
