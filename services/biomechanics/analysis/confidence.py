"""Conservative confidence propagation for derived measurements."""

from collections.abc import Iterable


def landmark_confidence(visibility: float | None, presence: float | None) -> float | None:
    """Use the least favorable confidence signal exposed for one landmark."""

    available = [value for value in (visibility, presence) if value is not None]
    if not available:
        return None
    if any(value < 0 or value > 1 for value in available):
        raise ValueError("Landmark confidence values must be between 0 and 1.")
    return min(available)


def conservative_joint_confidence(
    landmark_confidences: Iterable[float | None],
) -> float | None:
    """Return the minimum confidence only when every required landmark has one."""

    values = tuple(landmark_confidences)
    if not values or any(value is None for value in values):
        return None
    numeric_values = tuple(value for value in values if value is not None)
    if any(value < 0 or value > 1 for value in numeric_values):
        raise ValueError("Landmark confidence values must be between 0 and 1.")
    return min(numeric_values)
