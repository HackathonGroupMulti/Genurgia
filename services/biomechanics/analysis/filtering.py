"""Small, deterministic temporal filters that never replace missing samples."""

from collections.abc import Sequence


def centered_moving_average(
    values: Sequence[float | None],
    *,
    window_size: int = 5,
    minimum_valid_values: int = 3,
) -> tuple[float | None, ...]:
    """Smooth valid centers using nearby values while preserving missing centers."""

    if window_size <= 0 or window_size % 2 == 0:
        raise ValueError("window_size must be a positive odd integer.")
    if minimum_valid_values <= 0 or minimum_valid_values > window_size:
        raise ValueError("minimum_valid_values must be between 1 and window_size.")

    radius = window_size // 2
    filtered: list[float | None] = []
    for index, center in enumerate(values):
        if center is None:
            filtered.append(None)
            continue

        start = max(0, index - radius)
        end = min(len(values), index + radius + 1)
        valid_values = [value for value in values[start:end] if value is not None]
        if len(valid_values) < minimum_valid_values:
            filtered.append(None)
            continue
        filtered.append(sum(valid_values) / len(valid_values))

    return tuple(filtered)
