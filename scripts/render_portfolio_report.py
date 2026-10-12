"""Render the public HTML report from the current saved portfolio evidence."""

from __future__ import annotations

import argparse
import os
import tempfile
from pathlib import Path

from mpi.dashboard import load_dashboard_data
from mpi.portfolio import render_report, scalar_comparison_svg


def _write_atomic(output: Path, content: str) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", newline="\n", dir=output.parent, delete=False
        ) as target:
            temporary = Path(target.name)
            target.write(content)
        os.replace(temporary, output)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--template", type=Path, default=Path("docs/report/template.html"))
    parser.add_argument("--output", type=Path, default=Path("docs/report/index.html"))
    parser.add_argument(
        "--figure-output", type=Path, default=Path("docs/images/scalar-comparison.svg")
    )
    args = parser.parse_args()

    # Saved artifact paths follow the repository-root convention of the research scripts.
    data = load_dashboard_data()
    run = data.uncertainty_run
    report = render_report(
        data,
        args.template.read_text(encoding="utf-8"),
        source_version=str(run["source_version"]),
        source_archive_sha256=str(run["source_archive_sha256"]),
        membership_sha256=str(run["membership_sha256"]),
    )
    _write_atomic(args.output, report)
    _write_atomic(args.figure_output, scalar_comparison_svg(data))
    print(f"Rendered aggregate portfolio report: {args.output.resolve()}")
    print(f"Exported scalar comparison: {args.figure_output.resolve()}")


if __name__ == "__main__":
    main()
