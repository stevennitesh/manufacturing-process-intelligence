import hashlib
import json
import sys
import zipfile
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts import inspect_injection_molding_source as source_inspection


def _write_parseable_archives(root: Path) -> None:
    root.mkdir()
    for name in source_inspection.ARCHIVES:
        with zipfile.ZipFile(root / name, "w") as archive:
            archive.writestr("evidence.txt", f"parseable {name}")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_manifest(path: Path, source_root: Path) -> None:
    files: list[dict[str, int | str]] = []
    for name in source_inspection.ARCHIVES:
        archive = source_root / name
        files.append(
            {
                "source_path": name,
                "bytes": archive.stat().st_size,
                "sha256": _sha256(archive),
            }
        )
    path.write_text(json.dumps({"files": files}), encoding="utf-8")


def test_rejects_wrong_hash_before_parsing_parseable_archives(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source_root = tmp_path / "source"
    _write_parseable_archives(source_root)
    manifest = tmp_path / "manifest.json"
    _write_manifest(manifest, source_root)
    contents = json.loads(manifest.read_text(encoding="utf-8"))
    contents["files"][0]["sha256"] = "0" * 64
    manifest.write_text(json.dumps(contents), encoding="utf-8")

    parsing_started = False

    def unexpected_parse(_path: Path, *_args: Any) -> Any:
        nonlocal parsing_started
        parsing_started = True
        raise AssertionError("archive parsing must not begin before identity passes")

    monkeypatch.setattr(source_inspection, "archive_members", unexpected_parse)
    monkeypatch.setattr(source_inspection, "inspect_csv_archive", unexpected_parse)
    monkeypatch.setattr(source_inspection, "inspect_hdf_archive", unexpected_parse)

    with pytest.raises(source_inspection.SourceIdentityError, match=r"dataset1\.zip"):
        source_inspection.inspect(source_root, manifest)

    assert parsing_started is False


def test_matching_identity_reaches_inspection_without_full_source_fixture(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source_root = tmp_path / "source"
    _write_parseable_archives(source_root)
    manifest = tmp_path / "manifest.json"
    _write_manifest(manifest, source_root)
    inspected: list[str] = []

    def inspect_csv(path: Path, dataset_number: int) -> dict[str, int]:
        inspected.append(path.name)
        return {"dataset_number": dataset_number}

    def inspect_hdf(path: Path) -> dict[str, str]:
        inspected.append(path.name)
        return {"archive": path.name}

    monkeypatch.setattr(source_inspection, "inspect_csv_archive", inspect_csv)
    monkeypatch.setattr(source_inspection, "inspect_hdf_archive", inspect_hdf)

    result = source_inspection.inspect(source_root, manifest)

    assert inspected == list(source_inspection.ARCHIVES)
    assert result["datasets"]["dataset2"] == {"archive": "dataset2.zip"}


def test_cli_names_mismatched_file_and_exits_nonzero(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    source_root = tmp_path / "source"
    _write_parseable_archives(source_root)
    manifest = tmp_path / "manifest.json"
    _write_manifest(manifest, source_root)
    contents = json.loads(manifest.read_text(encoding="utf-8"))
    contents["files"][0]["sha256"] = "f" * 64
    manifest.write_text(json.dumps(contents), encoding="utf-8")
    monkeypatch.setattr(
        sys,
        "argv",
        ["inspect-source", str(source_root), "--manifest", str(manifest)],
    )

    with pytest.raises(SystemExit) as exit_info:
        source_inspection.main()

    assert exit_info.value.code == 2
    assert "source identity mismatch for dataset1.zip" in capsys.readouterr().err
