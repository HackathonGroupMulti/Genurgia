from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True, slots=True)
class TetrahedronQuality:
    signed_volume_mm3: float


def signed_tetrahedron_volume_mm3(
    a: tuple[float, float, float],
    b: tuple[float, float, float],
    c: tuple[float, float, float],
    d: tuple[float, float, float],
) -> float:
    """Return oriented tet4 volume in cubic millimetres."""
    points = np.asarray((a, b, c, d), dtype=float)
    if not np.isfinite(points).all():
        raise ValueError("Tetrahedron coordinates must be finite.")
    edges = np.stack(
        (points[1] - points[0], points[2] - points[0], points[3] - points[0])
    )
    return float(np.linalg.det(edges) / 6.0)
