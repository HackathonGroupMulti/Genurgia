import json
from pathlib import Path
from uuid import uuid4

from app.storage import ARTIFACT_MANIFEST_FILENAME, LocalArtifactStore


def test_bundle_is_hidden_until_atomic_publication_and_manifested(tmp_path: Path) -> None:
    store = LocalArtifactStore(tmp_path)
    bundle_id = uuid4()
    staging = store.begin_bundle(bundle_id)
    source = store.create_temporary_upload(".mp4")
    source.write_bytes(b"source-video")

    store.copy_to_staging(staging, "recording.mp4", source)
    store.write_staged_json(staging, "pose_sequence.json", {"frames": []})

    assert not (tmp_path / str(bundle_id)).exists()
    published = store.publish_bundle(bundle_id, staging)
    assert published.is_dir()
    manifest = json.loads((published / ARTIFACT_MANIFEST_FILENAME).read_text(encoding="utf-8"))
    assert [item["filename"] for item in manifest["artifacts"]] == [
        "pose_sequence.json",
        "recording.mp4",
    ]
    assert all(len(item["sha256"]) == 64 for item in manifest["artifacts"])


def test_atomic_derived_write_refreshes_manifest_and_detects_corruption(tmp_path: Path) -> None:
    store = LocalArtifactStore(tmp_path)
    bundle_id = uuid4()
    staging = store.begin_bundle(bundle_id)
    store.write_staged_json(staging, "source.json", {"source": True})
    store.publish_bundle(bundle_id, staging)

    store.write_json(bundle_id, "derived.json", {"derived": True})
    verified = {item["filename"]: item for item in store.verify_bundle(bundle_id)}
    assert verified["source.json"]["integrity"] == "verified"
    assert verified["derived.json"]["integrity"] == "verified"

    store.path_for(bundle_id, "derived.json").write_text("corrupt", encoding="utf-8")
    corrupt = {item["filename"]: item for item in store.verify_bundle(bundle_id)}
    assert corrupt["derived.json"]["integrity"] == "checksum_mismatch"

    store.path_for(bundle_id, "unexpected.txt").write_text("untracked", encoding="utf-8")
    with_untracked = {item["filename"]: item for item in store.verify_bundle(bundle_id)}
    assert with_untracked["unexpected.txt"]["integrity"] == "untracked"


def test_abandoned_upload_and_staging_cleanup_is_bounded_to_work_directories(
    tmp_path: Path,
) -> None:
    store = LocalArtifactStore(tmp_path)
    upload = store.create_temporary_upload()
    upload.write_bytes(b"partial")
    staging = store.begin_bundle(uuid4())
    store.write_staged_json(staging, "partial.json", {})
    preserved = tmp_path / "preserved.txt"
    preserved.write_text("keep", encoding="utf-8")

    assert store.cleanup_abandoned_work() == 2
    assert preserved.read_text(encoding="utf-8") == "keep"


def test_staged_deletion_can_be_restored_before_finalization(tmp_path: Path) -> None:
    store = LocalArtifactStore(tmp_path)
    bundle_id = uuid4()
    staging = store.begin_bundle(bundle_id)
    store.write_staged_json(staging, "source.json", {})
    store.publish_bundle(bundle_id, staging)

    deletion = store.stage_bundle_deletion(bundle_id)
    assert not (tmp_path / str(bundle_id)).exists()
    store.restore_staged_deletion(bundle_id, deletion)
    assert store.path_for(bundle_id, "source.json").is_file()

    deletion = store.stage_bundle_deletion(bundle_id)
    store.finalize_staged_deletion(deletion)
    assert not deletion.exists()
