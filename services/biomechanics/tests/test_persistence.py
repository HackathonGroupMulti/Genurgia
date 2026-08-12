from pathlib import Path
from uuid import UUID, uuid4

import pytest

from app.migrations import MIGRATIONS
from app.persistence import SessionNotFound, SQLiteSessionRepository
from app.schemas.pose import CoordinateConvention, PoseSequenceSummary, Recording


def extraction_metadata(index: int = 1) -> tuple[Recording, PoseSequenceSummary]:
    recording_id = uuid4()
    sequence_id = uuid4()
    recording = Recording(
        id=recording_id,
        original_filename=f"squat-{index}.mp4",
        content_type="video/mp4",
        size_bytes=100,
        duration_ms=2000,
        fps=30,
        width=640,
        height=480,
        storage_reference=f"/artifacts/{sequence_id}/recording.mp4",
    )
    sequence = PoseSequenceSummary(
        id=sequence_id,
        recording_id=recording_id,
        pose_model="test-model",
        pose_model_version="v1",
        coordinate_convention=CoordinateConvention(),
        frame_count=60,
        detected_frame_count=58,
        raw_landmarks_reference=f"/artifacts/{sequence_id}/pose_sequence.json",
        annotated_video_reference=f"/artifacts/{sequence_id}/annotated.mp4",
    )
    return recording, sequence


def repository(tmp_path: Path) -> SQLiteSessionRepository:
    return SQLiteSessionRepository(tmp_path / "sessions.sqlite3")


def test_persists_session_graph_analysis_versions_and_metrics(tmp_path: Path) -> None:
    sessions = repository(tmp_path)
    recording, sequence = extraction_metadata()

    session_id = sessions.record_pose_extraction(recording, sequence)
    sessions.record_analysis(
        sequence.id,
        "knee_flexion",
        "knee-flexion-analysis-v1",
        f"/artifacts/{sequence.id}/knee_flexion.json",
        "knee_flexion_complete",
    )
    sessions.record_analysis(
        sequence.id,
        "squat_repetitions",
        "squat-repetition-analysis-v1",
        f"/artifacts/{sequence.id}/squat_repetitions.json",
        "complete",
        metrics=[
            ("repetition_count", 2, "count"),
            ("mean_rom_degrees", 70.5, "degree"),
        ],
    )

    stored = sessions.get_session(session_id)

    assert stored.status == "complete"
    assert stored.recording.id == recording.id
    assert stored.pose_sequence.id == sequence.id
    assert [analysis.analysis_version for analysis in stored.analyses] == [
        "knee-flexion-analysis-v1",
        "squat-repetition-analysis-v1",
    ]
    assert {metric.name: metric.value for metric in stored.metrics} == {
        "mean_rom_degrees": 70.5,
        "repetition_count": 2,
    }


def test_comparison_reports_change_from_previous_completed_session(tmp_path: Path) -> None:
    sessions = repository(tmp_path)
    for index, mean_rom in enumerate((60.0, 67.5), start=1):
        recording, sequence = extraction_metadata(index)
        sessions.record_pose_extraction(recording, sequence)
        sessions.record_analysis(
            sequence.id,
            "squat_repetitions",
            "squat-repetition-analysis-v1",
            f"/artifacts/{sequence.id}/squat_repetitions.json",
            "complete",
            metrics=[
                ("repetition_count", 2, "count"),
                ("mean_rom_degrees", mean_rom, "degree"),
            ],
        )

    comparison = sessions.compare_sessions()

    assert [entry.mean_rom_degrees for entry in comparison] == [67.5, 60.0]
    assert comparison[0].mean_rom_change_from_previous_degrees == 7.5
    assert comparison[1].mean_rom_change_from_previous_degrees is None


def test_missing_session_is_explicit(tmp_path: Path) -> None:
    with pytest.raises(SessionNotFound):
        repository(tmp_path).get_session(UUID(int=0))


def test_reanalysis_replaces_metrics_without_regressing_complete_status(tmp_path: Path) -> None:
    sessions = repository(tmp_path)
    recording, sequence = extraction_metadata()
    session_id = sessions.record_pose_extraction(recording, sequence)
    sessions.record_analysis(
        sequence.id,
        "squat_repetitions",
        "squat-repetition-analysis-v1",
        "repetitions.json",
        "complete",
        metrics=[
            ("repetition_count", 2, "count"),
            ("mean_rom_degrees", 70, "degree"),
        ],
    )
    sessions.record_analysis(
        sequence.id,
        "squat_repetitions",
        "squat-repetition-analysis-v1",
        "repetitions.json",
        "complete",
        metrics=[("repetition_count", 0, "count")],
    )
    sessions.record_analysis(
        sequence.id,
        "knee_flexion",
        "knee-flexion-analysis-v1",
        "knee.json",
        "knee_flexion_complete",
    )

    stored = sessions.get_session(session_id)

    assert stored.status == "complete"
    assert [(metric.name, metric.value) for metric in stored.metrics] == [
        ("repetition_count", 0)
    ]


def test_repository_releases_database_file_after_each_operation(tmp_path: Path) -> None:
    database_path = tmp_path / "sessions.sqlite3"
    sessions = SQLiteSessionRepository(database_path)

    sessions.list_sessions()
    moved_path = tmp_path / "released.sqlite3"
    database_path.rename(moved_path)

    assert moved_path.is_file()


def test_repository_migrates_existing_v1_database_without_losing_sessions(
    tmp_path: Path,
) -> None:
    import sqlite3

    database_path = tmp_path / "legacy.sqlite3"
    with sqlite3.connect(database_path) as connection:
        for statement in MIGRATIONS[0].statements:
            connection.execute(statement)

    sessions = SQLiteSessionRepository(database_path)
    recording, sequence = extraction_metadata()
    session_id = sessions.record_pose_extraction(recording, sequence)

    stored = sessions.get_session(session_id)
    assert stored.recording.protocol == "squat"
    assert stored.recording.laterality_context == "bilateral"
    with sqlite3.connect(database_path) as connection:
        versions = [row[0] for row in connection.execute(
            "SELECT version FROM schema_migrations ORDER BY version"
        )]
    assert versions == [1, 2]


def test_selected_comparison_enforces_capture_and_analysis_compatibility(
    tmp_path: Path,
) -> None:
    sessions = repository(tmp_path)
    ids = []
    for index, mean_rom in enumerate((60.0, 65.0), start=1):
        recording, sequence = extraction_metadata(index)
        recording = recording.model_copy(
            update={
                "camera_view": "left_side",
                "orientation": "landscape",
                "laterality_context": "bilateral",
            }
        )
        ids.append(sessions.record_pose_extraction(recording, sequence))
        sessions.record_analysis(
            sequence.id,
            "squat_repetitions",
            "squat-repetition-analysis-v2",
            f"/artifacts/{sequence.id}/squat_repetitions_v2.json",
            "complete",
            metrics=[("mean_rom_degrees", mean_rom, "degree")],
        )

    comparison = sessions.compare_selected_sessions(ids[0], ids[1])

    assert comparison.compatible is True
    assert comparison.analysis_version == "squat-repetition-analysis-v2"
    assert comparison.metrics[0].name == "mean_rom_degrees"
    assert comparison.metrics[0].change == 5

    same_session = sessions.compare_selected_sessions(ids[0], ids[0])
    assert same_session.compatible is False
    assert same_session.metrics == []


def test_selected_comparison_rejects_unknown_capture_context(tmp_path: Path) -> None:
    sessions = repository(tmp_path)
    recording, sequence = extraction_metadata()
    first_id = sessions.record_pose_extraction(recording, sequence)
    sessions.record_analysis(
        sequence.id,
        "squat_repetitions",
        "squat-repetition-analysis-v2",
        "repetitions-v2.json",
        "complete",
    )
    recording2, sequence2 = extraction_metadata(2)
    second_id = sessions.record_pose_extraction(recording2, sequence2)
    sessions.record_analysis(
        sequence2.id,
        "squat_repetitions",
        "squat-repetition-analysis-v2",
        "repetitions-v2.json",
        "complete",
    )

    comparison = sessions.compare_selected_sessions(first_id, second_id)

    assert comparison.compatible is False
    assert "Camera view is unknown." in comparison.incompatibilities
