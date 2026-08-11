"""Pure, unit-tested joint-angle calculations."""

import math
from collections.abc import Sequence

Point3D = tuple[float, float, float]
Vector3D = tuple[float, float, float]


class InvalidGeometryError(ValueError):
    """Raised when an angle cannot be calculated from the supplied geometry."""


def vector_between(origin: Sequence[float], point: Sequence[float]) -> Vector3D:
    if len(origin) != 3 or len(point) != 3:
        raise InvalidGeometryError("Three-dimensional coordinates are required.")

    vector = tuple(float(point[index]) - float(origin[index]) for index in range(3))
    if not all(math.isfinite(component) for component in vector):
        raise InvalidGeometryError("Coordinates must contain only finite values.")
    return vector  # type: ignore[return-value]


def included_angle_degrees(first: Sequence[float], second: Sequence[float]) -> float:
    if len(first) != 3 or len(second) != 3:
        raise InvalidGeometryError("Three-dimensional vectors are required.")

    first_vector = tuple(float(component) for component in first)
    second_vector = tuple(float(component) for component in second)
    if not all(math.isfinite(component) for component in (*first_vector, *second_vector)):
        raise InvalidGeometryError("Vectors must contain only finite values.")

    first_norm = math.sqrt(sum(component * component for component in first_vector))
    second_norm = math.sqrt(sum(component * component for component in second_vector))
    if first_norm == 0 or second_norm == 0:
        raise InvalidGeometryError("Cannot calculate an angle from a zero-length vector.")

    dot_product = sum(a * b for a, b in zip(first_vector, second_vector, strict=True))
    cosine = dot_product / (first_norm * second_norm)
    clamped_cosine = max(-1.0, min(1.0, cosine))
    return math.degrees(math.acos(clamped_cosine))


def knee_flexion_degrees(hip: Point3D, knee: Point3D, ankle: Point3D) -> float:
    """Return modeled knee flexion where 0° is straight modeled extension."""

    femur_vector = vector_between(knee, hip)
    tibia_vector = vector_between(knee, ankle)
    included_angle = included_angle_degrees(femur_vector, tibia_vector)
    return 180.0 - included_angle
