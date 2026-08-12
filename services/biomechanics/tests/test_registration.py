import cv2
import numpy as np
import pytest
from pydantic import ValidationError

from analysis.registration import (
    estimate_rigid_transform,
    perturbation_uncertainty,
    solve_arthroscopy_pose,
    triangulate_point_linear,
)
from app.schemas.registration import ArthroscopyRefinementGateV1, TissueScoreAnnotationV1


def test_triangulation_recovers_known_capture_point() -> None:
    intrinsic = np.array([[800, 0, 320], [0, 800, 240], [0, 0, 1]], dtype=float)
    cameras = []
    points = []
    expected = np.array([40.0, 25.0, 1000.0])
    for center_x in (-200.0, 200.0, 0.0, 100.0):
        extrinsic = np.column_stack((np.eye(3), np.array([-center_x, 0, 0])))
        projection = intrinsic @ extrinsic
        image = projection @ np.append(expected, 1)
        cameras.append(projection)
        points.append((image[0] / image[2], image[1] / image[2]))
    actual = triangulate_point_linear(cameras, points)
    np.testing.assert_allclose(actual, expected, atol=1e-8)


def test_rigid_registration_recovers_known_transform_and_residuals() -> None:
    source = np.array([[0, 0, 0], [10, 0, 0], [0, 20, 0], [0, 0, 30]], dtype=float)
    angle = np.deg2rad(20)
    rotation = np.array(
        [[np.cos(angle), -np.sin(angle), 0], [np.sin(angle), np.cos(angle), 0], [0, 0, 1]]
    )
    translation = np.array([100, -20, 5])
    target = (rotation @ source.T).T + translation
    result = estimate_rigid_transform(source, target)
    np.testing.assert_allclose(result.transform[:3, :3], rotation, atol=1e-10)
    np.testing.assert_allclose(result.transform[:3, 3], translation, atol=1e-10)
    assert result.rms_error_mm < 1e-10


def test_registration_refuses_insufficient_or_degenerate_evidence() -> None:
    with pytest.raises(ValueError, match="two views"):
        triangulate_point_linear([np.eye(3, 4)], [(1, 2)])
    collinear = np.array([[0, 0, 0], [1, 0, 0], [2, 0, 0]])
    with pytest.raises(ValueError, match="degenerate"):
        estimate_rigid_transform(collinear, collinear)


def test_registration_uncertainty_is_reproducible_and_has_explicit_units() -> None:
    source = np.array([[0, 0, 0], [10, 0, 0], [0, 20, 0], [0, 0, 30]], dtype=float)
    target = source + np.array([10, 20, 30])
    first = perturbation_uncertainty(source, target, 0.5, samples=40, seed=42)
    second = perturbation_uncertainty(source, target, 0.5, samples=40, seed=42)
    assert first == second
    assert first.translation_95_mm > 0
    assert first.rotation_95_degrees > 0


def test_arthroscopy_pose_reports_known_reprojection_error() -> None:
    anatomy = np.array(
        [[0, 0, 0], [20, 0, 0], [0, 20, 0], [0, 0, 20], [20, 20, 10]],
        dtype=np.float64,
    )
    intrinsic = np.array([[900, 0, 320], [0, 900, 240], [0, 0, 1]], dtype=np.float64)
    rotation_vector = np.array([0.1, -0.05, 0.02])
    translation = np.array([10, -5, 500.0])
    image, _ = cv2.projectPoints(anatomy, rotation_vector, translation, intrinsic, np.zeros(5))
    result = solve_arthroscopy_pose(anatomy, image[:, 0, :], intrinsic, np.zeros(5))
    assert result.rms_reprojection_error_px < 0.01
    identity = result.anatomy_from_camera_transform @ np.linalg.inv(
        result.anatomy_from_camera_transform
    )
    np.testing.assert_allclose(identity, np.eye(4), atol=1e-10)


def test_arthroscopy_refinement_and_scoring_are_evidence_gated() -> None:
    with pytest.raises(ValidationError, match="must be refused"):
        ArthroscopyRefinementGateV1(
            overlay_registration_id="registration",
            calibrated=False,
            parallax_sufficient=True,
            coverage_ratio=0.5,
            residual_rms_px=1,
            residual_threshold_px=2,
            output_reconstruction_version="arthroscopy-refined-v1",
            decision="create-new-reconstruction",
        )
    with pytest.raises(ValidationError, match="two expert"):
        TissueScoreAnnotationV1(
            taxonomy_version="research-tissue-v1",
            expert_labels={"expert-a": "label"},
            inter_rater_result={},
        )
