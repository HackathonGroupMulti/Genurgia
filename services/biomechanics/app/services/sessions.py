"""Longitudinal session workflows over persisted metadata and immutable artifacts."""

import hashlib
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from app.persistence import SQLiteSessionRepository
from app.schemas.kinematics import KINEMATICS_ANALYSIS_VERSION
from app.schemas.quality import CAPTURE_QUALITY_ANALYSIS_VERSION
from app.schemas.repetitions import REPETITION_ANALYSIS_VERSION
from app.schemas.sessions import (
    ExportArtifact,
    ReanalysisResponse,
    SessionExportManifest,
)
from app.services.kinematics import KinematicsService
from app.storage import LocalArtifactStore


class SessionWorkflowService:
    def __init__(
        self,
        repository: SQLiteSessionRepository,
        artifacts: LocalArtifactStore,
        kinematics: KinematicsService,
    ) -> None:
        self._repository = repository
        self._artifacts = artifacts
        self._kinematics = kinematics

    def reanalyze(self, session_id: UUID, analyses: list[str]) -> ReanalysisResponse:
        session = self._repository.get_session(session_id)
        existing = {
            (analysis.analysis_type, analysis.analysis_version)
            for analysis in session.analyses
        }
        sequence_id = session.pose_sequence.id
        for analysis_type in analyses:
            if analysis_type == "knee_flexion":
                if (analysis_type, KINEMATICS_ANALYSIS_VERSION) not in existing:
                    self._kinematics.analyze_knee_flexion(sequence_id)
            elif analysis_type == "squat_repetitions":
                if (analysis_type, REPETITION_ANALYSIS_VERSION) not in existing:
                    self._kinematics.analyze_squat_repetitions(sequence_id)
            elif analysis_type == "capture_quality":
                if (analysis_type, CAPTURE_QUALITY_ANALYSIS_VERSION) not in existing:
                    self._kinematics.analyze_capture_quality(sequence_id)
            else:
                raise ValueError(f"Unsupported analysis type: {analysis_type}")
        return ReanalysisResponse(
            session=self._repository.get_session(session_id),
            requested_analyses=analyses,
        )

    def export_manifest(self, session_id: UUID) -> SessionExportManifest:
        session = self._repository.get_session(session_id)
        references: list[tuple[str, str, str | None, str | None]] = [
            ("original_recording", session.recording.storage_reference, None, None),
            (
                "raw_pose_observations",
                session.pose_sequence.raw_landmarks_reference,
                None,
                None,
            ),
            (
                "annotated_pose_overlay",
                session.pose_sequence.annotated_video_reference,
                None,
                None,
            ),
        ]
        references.extend(
            (
                "derived_analysis",
                analysis.artifact_reference,
                analysis.analysis_type,
                analysis.analysis_version,
            )
            for analysis in session.analyses
        )
        return SessionExportManifest(
            generated_at=datetime.now(UTC),
            session=session,
            artifacts=[
                self._inspect_reference(
                    session.pose_sequence.id,
                    role,
                    reference,
                    analysis_type,
                    analysis_version,
                )
                for role, reference, analysis_type, analysis_version in references
            ],
        )

    def _inspect_reference(
        self,
        pose_sequence_id: UUID,
        role: str,
        reference: str,
        analysis_type: str | None,
        analysis_version: str | None,
    ) -> ExportArtifact:
        filename = Path(reference).name
        expected_prefix = f"/artifacts/{pose_sequence_id}/"
        path = (
            self._artifacts.path_for(pose_sequence_id, filename)
            if reference.startswith(expected_prefix)
            else None
        )
        exists = path is not None and path.is_file()
        return ExportArtifact(
            role=role,
            artifact_reference=reference,
            analysis_type=analysis_type,
            analysis_version=analysis_version,
            exists=exists,
            size_bytes=path.stat().st_size if exists and path is not None else None,
            sha256=_sha256(path) if exists and path is not None else None,
            integrity="verified" if exists else "missing",
        )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
