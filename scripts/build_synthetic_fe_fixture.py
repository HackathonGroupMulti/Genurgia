"""Build a deterministic CC0 FE package against an existing reconstruction."""

import argparse
import json
import zipfile
from pathlib import Path
from uuid import UUID

from app.synthetic_fixture import synthetic_fe_manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reconstruction-id", required=True, type=UUID)
    parser.add_argument("--laterality", required=True, choices=("left", "right"))
    parser.add_argument("--coordinate-system", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    manifest = synthetic_fe_manifest(
        args.reconstruction_id,
        args.laterality,
        args.coordinate_system,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(args.output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        _write_member(
            archive,
            "finite_element_model_manifest_v1.json",
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        )
        _write_member(
            archive,
            "README.txt",
            "Synthetic Knee Twin topology fixture. CC0-1.0. Not anatomical evidence.\n",
        )
    print(f"Wrote {args.output}")


def _write_member(archive: zipfile.ZipFile, name: str, text: str) -> None:
    member = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
    member.compress_type = zipfile.ZIP_DEFLATED
    archive.writestr(member, text.encode())


if __name__ == "__main__":
    main()
