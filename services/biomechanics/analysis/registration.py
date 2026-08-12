from dataclasses import dataclass

import cv2
import numpy as np


@dataclass(frozen=True, slots=True)
class RigidRegistrationResult:
    transform: np.ndarray
    residuals_mm: np.ndarray
    rms_error_mm: float


@dataclass(frozen=True, slots=True)
class ArthroscopyPoseResult:
    anatomy_from_camera_transform: np.ndarray
    reprojection_errors_px: np.ndarray
    rms_reprojection_error_px: float


@dataclass(frozen=True, slots=True)
class RegistrationUncertaintyResult:
    translation_95_mm: float
    rotation_95_degrees: float


def triangulate_point_linear(
    projection_matrices: list[np.ndarray],
    image_points_px: list[tuple[float, float]],
) -> np.ndarray:
    if len(projection_matrices) != len(image_points_px) or len(image_points_px) < 2:
        raise ValueError("Triangulation requires matching observations from at least two views.")
    rows = []
    for projection, (u, v) in zip(projection_matrices, image_points_px, strict=True):
        matrix = np.asarray(projection, dtype=float)
        if matrix.shape != (3, 4) or not np.isfinite(matrix).all():
            raise ValueError("Each projection matrix must be finite and 3x4.")
        rows.extend((u * matrix[2] - matrix[0], v * matrix[2] - matrix[1]))
    system = np.asarray(rows)
    _u, singular_values, vh = np.linalg.svd(system)
    homogeneous = vh[-1]
    if singular_values[-2] <= 1e-12 or abs(homogeneous[3]) <= 1e-12:
        raise ValueError("Camera geometry is degenerate for this triangulation.")
    point = homogeneous[:3] / homogeneous[3]
    if not np.isfinite(point).all():
        raise ValueError("Triangulation produced a non-finite point.")
    return point


def estimate_rigid_transform(
    source_mm: np.ndarray, target_mm: np.ndarray
) -> RigidRegistrationResult:
    source = np.asarray(source_mm, dtype=float)
    target = np.asarray(target_mm, dtype=float)
    if source.shape != target.shape or source.ndim != 2 or source.shape[1] != 3:
        raise ValueError("Source and target landmarks must share an N×3 shape.")
    if source.shape[0] < 3 or not np.isfinite(source).all() or not np.isfinite(target).all():
        raise ValueError("Rigid registration requires at least three finite landmark pairs.")
    if np.linalg.matrix_rank(source - source.mean(axis=0)) < 2:
        raise ValueError("Rigid registration landmarks are geometrically degenerate.")
    source_center = source.mean(axis=0)
    target_center = target.mean(axis=0)
    covariance = (source - source_center).T @ (target - target_center)
    u, _singular, vh = np.linalg.svd(covariance)
    rotation = vh.T @ u.T
    if np.linalg.det(rotation) < 0:
        vh[-1] *= -1
        rotation = vh.T @ u.T
    translation = target_center - rotation @ source_center
    transform = np.eye(4)
    transform[:3, :3] = rotation
    transform[:3, 3] = translation
    transformed = (rotation @ source.T).T + translation
    residuals = np.linalg.norm(transformed - target, axis=1)
    return RigidRegistrationResult(
        transform=transform,
        residuals_mm=residuals,
        rms_error_mm=float(np.sqrt(np.mean(residuals**2))),
    )


def perturbation_uncertainty(
    source_mm: np.ndarray,
    target_mm: np.ndarray,
    landmark_standard_deviation_mm: float,
    *,
    samples: int = 200,
    seed: int = 0,
) -> RegistrationUncertaintyResult:
    if landmark_standard_deviation_mm < 0 or samples < 20:
        raise ValueError("Uncertainty requires non-negative noise and at least 20 samples.")
    nominal = estimate_rigid_transform(source_mm, target_mm).transform
    generator = np.random.default_rng(seed)
    translations = []
    rotations = []
    for _ in range(samples):
        perturbed_source = np.asarray(source_mm) + generator.normal(
            0, landmark_standard_deviation_mm, np.asarray(source_mm).shape
        )
        perturbed_target = np.asarray(target_mm) + generator.normal(
            0, landmark_standard_deviation_mm, np.asarray(target_mm).shape
        )
        transform = estimate_rigid_transform(perturbed_source, perturbed_target).transform
        delta = transform @ np.linalg.inv(nominal)
        translations.append(np.linalg.norm(delta[:3, 3]))
        cosine = np.clip((np.trace(delta[:3, :3]) - 1) / 2, -1, 1)
        rotations.append(np.rad2deg(np.arccos(cosine)))
    return RegistrationUncertaintyResult(
        translation_95_mm=float(np.percentile(translations, 95)),
        rotation_95_degrees=float(np.percentile(rotations, 95)),
    )


def solve_arthroscopy_pose(
    anatomy_points_mm: np.ndarray,
    image_points_px: np.ndarray,
    camera_matrix: np.ndarray,
    distortion_coefficients: np.ndarray,
) -> ArthroscopyPoseResult:
    anatomy = np.asarray(anatomy_points_mm, dtype=np.float64)
    image = np.asarray(image_points_px, dtype=np.float64)
    intrinsic = np.asarray(camera_matrix, dtype=np.float64)
    distortion = np.asarray(distortion_coefficients, dtype=np.float64)
    if anatomy.ndim != 2 or anatomy.shape[1] != 3 or image.shape != (len(anatomy), 2):
        raise ValueError("Arthroscopy pose requires aligned N×3 anatomy and N×2 image points.")
    if len(anatomy) < 4 or intrinsic.shape != (3, 3):
        raise ValueError("At least four correspondences and a 3x3 intrinsic matrix are required.")
    if not all(np.isfinite(value).all() for value in (anatomy, image, intrinsic, distortion)):
        raise ValueError("Arthroscopy pose inputs must be finite.")
    ok, rotation_vector, translation_vector = cv2.solvePnP(
        anatomy,
        image,
        intrinsic,
        distortion,
        flags=cv2.SOLVEPNP_EPNP,
    )
    if not ok:
        raise ValueError("Arthroscopy pose optimization failed.")
    rotation, _ = cv2.Rodrigues(rotation_vector)
    camera_from_anatomy = np.eye(4)
    camera_from_anatomy[:3, :3] = rotation
    camera_from_anatomy[:3, 3] = translation_vector[:, 0]
    projected, _ = cv2.projectPoints(
        anatomy, rotation_vector, translation_vector, intrinsic, distortion
    )
    errors = np.linalg.norm(projected[:, 0, :] - image, axis=1)
    return ArthroscopyPoseResult(
        anatomy_from_camera_transform=np.linalg.inv(camera_from_anatomy),
        reprojection_errors_px=errors,
        rms_reprojection_error_px=float(np.sqrt(np.mean(errors**2))),
    )
