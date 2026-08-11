from uuid import UUID

from analysis.kinematics import (
    FILTER_MINIMUM_VALID_VALUES,
    FILTER_NAME,
    FILTER_WINDOW_SIZE,
    KNEE_FLEXION_CALCULATION_VERSION,
    MINIMUM_MEASUREMENT_CONFIDENCE,
    derive_knee_flexion_series,
)
from analysis.pose import (
    LandmarkObservation,
    PoseFrameObservation,
    PoseObservation,
)
from app.schemas.kinematics import (
    FilterDescription,
    KneeFlexionAnalysis,
    KneeFlexionSample,
    KneeFlexionSeries,
)
from app.schemas.pose import PoseFrame, PoseSequenceArtifact
from app.storage import LocalArtifactStore


class PoseSequenceNotFound(FileNotFoundError):
    pass


class KinematicsService:
    def __init__(self, artifact_store: LocalArtifactStore) -> None:
        self._artifacts = artifact_store

    def analyze_knee_flexion(self, pose_sequence_id: UUID) -> KneeFlexionAnalysis:
        raw_path = self._artifacts.path_for(pose_sequence_id, "pose_sequence.json")
        if not raw_path.is_file():
            raise PoseSequenceNotFound(f"Pose sequence {pose_sequence_id} was not found.")

        artifact = PoseSequenceArtifact.model_validate_json(raw_path.read_text(encoding="utf-8"))
        domain_frames = tuple(
            self._to_domain_frame(frame) for frame in artifact.pose_sequence.frames
        )
        domain_series = [
            derive_knee_flexion_series(domain_frames, "left"),
            derive_knee_flexion_series(domain_frames, "right"),
        ]
        artifact_filename = "knee_flexion.json"
        analysis = KneeFlexionAnalysis(
            calculation_version=KNEE_FLEXION_CALCULATION_VERSION,
            source_pose_sequence_id=pose_sequence_id,
            source_pose_model=artifact.pose_sequence.pose_model,
            source_pose_model_version=artifact.pose_sequence.pose_model_version,
            coordinate_convention=artifact.pose_sequence.coordinate_convention,
            minimum_measurement_confidence=MINIMUM_MEASUREMENT_CONFIDENCE,
            filtering=FilterDescription(
                name=FILTER_NAME,
                window_size=FILTER_WINDOW_SIZE,
                minimum_valid_values=FILTER_MINIMUM_VALID_VALUES,
                behavior=(
                    "Centered offline mean over valid samples; missing or low-confidence "
                    "center samples remain unavailable."
                ),
            ),
            series=[
                KneeFlexionSeries(
                    side=series.side,
                    samples=[
                        KneeFlexionSample.model_validate(sample, from_attributes=True)
                        for sample in series.samples
                    ],
                )
                for series in domain_series
            ],
            artifact_reference=self._artifacts.reference(
                pose_sequence_id,
                artifact_filename,
            ),
        )
        self._artifacts.write_json(
            pose_sequence_id,
            artifact_filename,
            analysis.model_dump(mode="json"),
        )
        return analysis

    @staticmethod
    def _to_domain_frame(frame: PoseFrame) -> PoseFrameObservation:
        return PoseFrameObservation(
            frame_index=frame.frame_index,
            timestamp_ms=frame.timestamp_ms,
            poses=tuple(
                PoseObservation(
                    pose_index=pose.pose_index,
                    image_landmarks=tuple(
                        LandmarkObservation(**landmark.model_dump())
                        for landmark in pose.image_landmarks
                    ),
                    world_landmarks=tuple(
                        LandmarkObservation(**landmark.model_dump())
                        for landmark in pose.world_landmarks
                    ),
                )
                for pose in frame.poses
            ),
        )
