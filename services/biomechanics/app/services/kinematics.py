from statistics import fmean
from uuid import UUID

from analysis.kinematics import (
    FILTER_MINIMUM_VALID_VALUES,
    FILTER_NAME,
    FILTER_WINDOW_SIZE,
    KNEE_FLEXION_CALCULATION_VERSION,
    MINIMUM_MEASUREMENT_CONFIDENCE,
    derive_knee_flexion_series,
)
from analysis.kinematics import (
    KneeFlexionSample as DomainKneeFlexionSample,
)
from analysis.kinematics import (
    KneeFlexionSeries as DomainKneeFlexionSeries,
)
from analysis.pose import (
    LandmarkObservation,
    PoseFrameObservation,
    PoseObservation,
)
from analysis.reps import (
    DEFAULT_SQUAT_REPETITION_CONFIG,
    SQUAT_REPETITION_ALGORITHM_VERSION,
    detect_squat_repetitions,
)
from app.persistence import SQLiteSessionRepository
from app.schemas.kinematics import (
    FilterDescription,
    KneeFlexionAnalysis,
    KneeFlexionSample,
    KneeFlexionSeries,
)
from app.schemas.pose import PoseFrame, PoseSequenceArtifact
from app.schemas.repetitions import (
    SquatPhaseModel,
    SquatRepetition,
    SquatRepetitionAnalysis,
)
from app.storage import LocalArtifactStore


class PoseSequenceNotFound(FileNotFoundError):
    pass


class KinematicsService:
    def __init__(
        self,
        artifact_store: LocalArtifactStore,
        session_repository: SQLiteSessionRepository | None = None,
    ) -> None:
        self._artifacts = artifact_store
        self._sessions = session_repository

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
        if self._sessions is not None:
            self._sessions.record_analysis(
                pose_sequence_id=pose_sequence_id,
                analysis_type="knee_flexion",
                analysis_version=analysis.analysis_version,
                artifact_reference=analysis.artifact_reference,
                status="knee_flexion_complete",
            )
        return analysis

    def analyze_squat_repetitions(self, pose_sequence_id: UUID) -> SquatRepetitionAnalysis:
        knee_path = self._artifacts.path_for(pose_sequence_id, "knee_flexion.json")
        if knee_path.is_file():
            knee_analysis = KneeFlexionAnalysis.model_validate_json(
                knee_path.read_text(encoding="utf-8")
            )
        else:
            knee_analysis = self.analyze_knee_flexion(pose_sequence_id)

        domain_series = [
            self._to_domain_series(series) for series in knee_analysis.series
        ]
        by_side = {series.side: series for series in domain_series}
        repetitions = detect_squat_repetitions(by_side["left"], by_side["right"])
        config = DEFAULT_SQUAT_REPETITION_CONFIG
        artifact_filename = "squat_repetitions.json"
        analysis = SquatRepetitionAnalysis(
            source_pose_sequence_id=pose_sequence_id,
            source_knee_flexion_analysis_version=knee_analysis.analysis_version,
            phase_model=SquatPhaseModel(
                algorithm_version=SQUAT_REPETITION_ALGORITHM_VERSION,
                phase_states=["standing", "descending", "bottom", "ascending"],
                standing_max_degrees=config.standing_max_degrees,
                descent_start_min_degrees=config.descent_start_min_degrees,
                bottom_min_degrees=config.bottom_min_degrees,
                bottom_exit_max_degrees=config.bottom_exit_max_degrees,
                minimum_duration_ms=config.minimum_duration_ms,
                maximum_duration_ms=config.maximum_duration_ms,
                maximum_gap_ms=config.maximum_gap_ms,
                minimum_side_rom_degrees=config.minimum_side_rom_degrees,
                behavior=(
                    "Requires aligned valid filtered values from both knees. Incomplete cycles, "
                    "cycles outside duration or ROM limits, and cycles crossing excessive data "
                    "gaps are omitted without interpolation."
                ),
            ),
            repetitions=[
                SquatRepetition.model_validate(repetition, from_attributes=True)
                for repetition in repetitions
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
        if self._sessions is not None:
            metrics: list[tuple[str, float, str]] = [
                ("repetition_count", float(len(repetitions)), "count")
            ]
            if repetitions:
                metrics.extend(
                    [
                        (
                            "mean_left_rom_degrees",
                            fmean(item.left_rom_degrees for item in repetitions),
                            "degree",
                        ),
                        (
                            "mean_right_rom_degrees",
                            fmean(item.right_rom_degrees for item in repetitions),
                            "degree",
                        ),
                        (
                            "mean_rom_degrees",
                            fmean(item.mean_rom_degrees for item in repetitions),
                            "degree",
                        ),
                        (
                            "mean_duration_ms",
                            fmean(item.duration_ms for item in repetitions),
                            "millisecond",
                        ),
                        (
                            "mean_confidence",
                            fmean(item.confidence for item in repetitions),
                            "ratio",
                        ),
                    ]
                )
            self._sessions.record_analysis(
                pose_sequence_id=pose_sequence_id,
                analysis_type="squat_repetitions",
                analysis_version=analysis.analysis_version,
                artifact_reference=analysis.artifact_reference,
                status="complete",
                metrics=metrics,
            )
        return analysis

    @staticmethod
    def _to_domain_series(series: KneeFlexionSeries) -> DomainKneeFlexionSeries:
        return DomainKneeFlexionSeries(
            side=series.side,
            samples=tuple(
                DomainKneeFlexionSample(
                    timestamp_ms=sample.timestamp_ms,
                    value_degrees=sample.value_degrees,
                    filtered_value_degrees=sample.filtered_value_degrees,
                    confidence=sample.confidence,
                    quality=sample.quality,
                )
                for sample in series.samples
            ),
        )

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
