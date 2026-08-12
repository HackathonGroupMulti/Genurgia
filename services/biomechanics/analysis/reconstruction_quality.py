from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True, slots=True)
class StructureAgreement:
    dice_coefficient: float
    average_symmetric_surface_distance_mm: float
    hausdorff_95_mm: float
    reference_voxels: int
    candidate_voxels: int


def evaluate_structure_agreement(
    candidate: np.ndarray,
    reference: np.ndarray,
    spacing_mm: tuple[float, float, float],
) -> StructureAgreement:
    """Compare two binary 3D masks without inventing missing structures."""
    if candidate.shape != reference.shape or candidate.ndim != 3:
        raise ValueError("Candidate and reference label maps must share one 3D shape.")
    if any(value <= 0 or not np.isfinite(value) for value in spacing_mm):
        raise ValueError("Voxel spacing must contain three finite positive millimetre values.")
    candidate_mask = candidate.astype(bool, copy=False)
    reference_mask = reference.astype(bool, copy=False)
    candidate_count = int(candidate_mask.sum())
    reference_count = int(reference_mask.sum())
    if candidate_count == 0 or reference_count == 0:
        raise ValueError("Both masks must contain the evaluated structure.")
    overlap = int(np.logical_and(candidate_mask, reference_mask).sum())
    dice = 2 * overlap / (candidate_count + reference_count)
    candidate_surface = _surface_points(candidate_mask, spacing_mm)
    reference_surface = _surface_points(reference_mask, spacing_mm)
    candidate_distances = _nearest_distances(candidate_surface, reference_surface)
    reference_distances = _nearest_distances(reference_surface, candidate_surface)
    symmetric = np.concatenate((candidate_distances, reference_distances))
    return StructureAgreement(
        dice_coefficient=float(dice),
        average_symmetric_surface_distance_mm=float(symmetric.mean()),
        hausdorff_95_mm=float(np.percentile(symmetric, 95)),
        reference_voxels=reference_count,
        candidate_voxels=candidate_count,
    )


def _surface_points(
    mask: np.ndarray, spacing_mm: tuple[float, float, float]
) -> np.ndarray:
    padded = np.pad(mask, 1, constant_values=False)
    interior = np.ones_like(mask, dtype=bool)
    for axis in range(3):
        lower = [slice(1, -1)] * 3
        upper = [slice(1, -1)] * 3
        lower[axis] = slice(0, -2)
        upper[axis] = slice(2, None)
        interior &= padded[tuple(lower)] & padded[tuple(upper)]
    indices = np.argwhere(mask & ~interior)
    return indices.astype(float) * np.asarray(spacing_mm, dtype=float)


def _nearest_distances(source: np.ndarray, target: np.ndarray) -> np.ndarray:
    result = np.empty(source.shape[0], dtype=float)
    chunk_size = 256
    for start in range(0, source.shape[0], chunk_size):
        chunk = source[start : start + chunk_size]
        squared = ((chunk[:, None, :] - target[None, :, :]) ** 2).sum(axis=2)
        result[start : start + chunk_size] = np.sqrt(squared.min(axis=1))
    return result
