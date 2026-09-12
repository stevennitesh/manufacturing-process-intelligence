import hashlib
import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path("scripts/inspect_solidair_source.py")


def test_inspection_reports_structure_without_row_values(tmp_path: Path) -> None:
    csv_path = tmp_path / "production.csv"
    csv_path.write_text("feature,target\n1.5,2.5\n,3.5\n1.5,2.5\n", encoding="utf-8")
    metadata_path = tmp_path / "metadata.json"
    csv_md5 = hashlib.md5(csv_path.read_bytes()).hexdigest()
    metadata_path.write_text(
        json.dumps(
            {
                "id": 1,
                "doi": "10.0/example",
                "metadata": {
                    "title": "Example",
                    "publication_date": "2026-01-01",
                    "version": None,
                    "license": {"id": "example"},
                    "access_right": "open",
                },
                "files": [
                    {
                        "key": "production.csv",
                        "size": csv_path.stat().st_size,
                        "checksum": f"md5:{csv_md5}",
                        "links": {"self": "https://example.test/production.csv"},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    output_path = tmp_path / "inspection.json"

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--metadata",
            str(metadata_path),
            "--csv",
            f"production={csv_path}",
            "--target",
            "target",
            "--output",
            str(output_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    report = json.loads(output_path.read_text(encoding="utf-8"))
    inspected = report["csv"]["production"]

    assert inspected["row_count"] == 3
    assert inspected["column_count"] == 2
    assert inspected["duplicate_row_digest_occurrences"] == 1
    assert inspected["column_observations"]["feature"]["blank_or_token_missing"] == 1
    assert inspected["trace"]["data_row_number"] == 1
    assert inspected["zenodo_md5_matches"] is True
    assert set(inspected["trace"]) == {"data_row_number", "meaning"}
    assert "rows" not in inspected


def test_inspection_rejects_missing_declared_target(tmp_path: Path) -> None:
    csv_path = tmp_path / "simulation.csv"
    csv_path.write_text("feature,other\n1,2\n", encoding="utf-8")
    metadata_path = tmp_path / "metadata.json"
    metadata_path.write_text(
        json.dumps(
            {
                "id": 1,
                "doi": "10.0/example",
                "metadata": {
                    "title": "Example",
                    "publication_date": "2026-01-01",
                    "version": None,
                    "license": {"id": "example"},
                    "access_right": "open",
                },
                "files": [],
            }
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--metadata",
            str(metadata_path),
            "--csv",
            f"simulation={csv_path}",
            "--target",
            "target",
            "--output",
            str(tmp_path / "inspection.json"),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "missing target columns" in result.stderr
