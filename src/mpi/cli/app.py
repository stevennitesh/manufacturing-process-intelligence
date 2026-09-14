"""Top-level MPI command line interface."""

from pathlib import Path
from typing import Annotated

import typer

from mpi import __version__
from mpi.core.config import load_dataset_config
from mpi.core.logging import configure_logging
from mpi.datasets.injection_molding import (
    DEFAULT_RAW_ROOT,
    AcquisitionError,
    acquire_injection_molding,
)
from mpi.datasets.injection_molding_canonicalization import CanonicalizationError
from mpi.datasets.injection_molding_persistence import (
    DEFAULT_OUTPUT,
    PersistenceError,
)
from mpi.datasets.injection_molding_persistence import prepare as prepare_injection_molding
from mpi.datasets.injection_molding_validation import (
    RawValidationError,
    validate_injection_molding,
)

app = typer.Typer(
    name="mpi",
    help="Manufacturing Process & Quality Intelligence.",
    no_args_is_help=True,
)
config_app = typer.Typer(help="Validate and inspect project configuration.")
data_app = typer.Typer(help="Acquire, validate and prepare manufacturing dataset sources.")
app.add_typer(config_app, name="config")
app.add_typer(data_app, name="data")


def version_callback(value: bool) -> None:
    """Print the installed version and exit."""
    if value:
        typer.echo(__version__)
        raise typer.Exit


@app.callback()
def main(
    version: Annotated[
        bool | None,
        typer.Option("--version", callback=version_callback, is_eager=True, help="Show version."),
    ] = None,
    log_level: Annotated[
        str,
        typer.Option(help="Application log level."),
    ] = "INFO",
) -> None:
    """Initialize the command line application."""
    del version
    configure_logging(log_level)


@config_app.command("validate")
def validate_config(
    path: Annotated[Path, typer.Argument(exists=True, dir_okay=False, readable=True)],
) -> None:
    """Validate a dataset configuration file."""
    config = load_dataset_config(path)
    typer.echo(f"valid dataset config: {config.dataset} ({config.stage})")


@data_app.command("acquire")
def acquire_data(
    dataset: Annotated[str, typer.Argument(help="Dataset identifier.")],
    raw_root: Annotated[
        Path,
        typer.Option(help="Root directory for immutable raw source evidence."),
    ] = DEFAULT_RAW_ROOT,
) -> None:
    """Acquire and byte-verify a pinned dataset source."""
    if dataset != "injection_molding":
        typer.echo(f"Error: unsupported acquisition dataset: {dataset}", err=True)
        raise typer.Exit(code=1)
    try:
        result = acquire_injection_molding(raw_root=raw_root)
    except AcquisitionError as error:
        typer.echo(f"Error: {error}", err=True)
        raise typer.Exit(code=1) from error
    typer.echo(f"dataset: {result.dataset}")
    typer.echo(f"candidate: {result.candidate}")
    typer.echo(f"source version: {result.source_version}")
    typer.echo(f"archive: {result.archive_path}")
    typer.echo(f"size: {result.size}")
    typer.echo(f"sha256: {result.sha256}")
    typer.echo(f"receipt: {result.receipt_path}")
    typer.echo(f"disposition: {result.disposition}")
    typer.echo("verification: byte-verified; schema validation and preparation not performed")


@data_app.command("validate")
def validate_data(
    dataset: Annotated[str, typer.Argument(help="Dataset identifier.")],
    raw_root: Annotated[
        Path,
        typer.Option(help="Root directory containing immutable raw source evidence."),
    ] = DEFAULT_RAW_ROOT,
) -> None:
    """Validate an acquired source archive without network access."""
    if dataset != "injection_molding":
        typer.echo(f"Error: unsupported validation dataset: {dataset}", err=True)
        raise typer.Exit(code=1)
    try:
        result = validate_injection_molding(raw_root=raw_root)
    except (AcquisitionError, RawValidationError) as error:
        typer.echo(f"Error: {error}", err=True)
        if isinstance(error, RawValidationError) and error.check_id == "archive.present":
            typer.echo(
                "Acquire the pinned source with `mpi data acquire injection_molding`.",
                err=True,
            )
        raise typer.Exit(code=1) from error
    typer.echo(f"dataset: {result.dataset}")
    typer.echo(f"candidate: {result.candidate}")
    typer.echo(f"source version: {result.source_version}")
    typer.echo(f"archive: {result.archive_path}")
    typer.echo(f"checks passed: {len(result.checks)}")
    typer.echo(
        "membership: "
        f"{len(result.matched_cycle_ids)} matched / "
        f"{len(result.labeled_only_cycle_ids)} labeled-only / "
        f"{len(result.signal_only_cycle_ids)} signal-only"
    )
    typer.echo(f"receipt: {result.receipt_path if result.receipt_path else 'absent'}")
    typer.echo("limitations:")
    for limitation in result.limitations:
        typer.echo(f"- {limitation}")


@data_app.command("prepare")
def prepare_data(
    dataset: Annotated[str, typer.Argument(help="Dataset identifier.")],
    raw_root: Annotated[
        Path,
        typer.Option(help="Root directory containing immutable raw source evidence."),
    ] = DEFAULT_RAW_ROOT,
    output: Annotated[
        Path,
        typer.Option(help="Complete destination directory for the prepared bundle."),
    ] = DEFAULT_OUTPUT,
) -> None:
    """Prepare or reuse local canonical tables without network access."""
    if dataset != "injection_molding":
        typer.echo(f"Error: unsupported preparation dataset: {dataset}", err=True)
        raise typer.Exit(code=1)
    try:
        result = prepare_injection_molding(raw_root=raw_root, output=output)
    except (AcquisitionError, RawValidationError, CanonicalizationError, PersistenceError) as error:
        typer.echo(f"Error: {error}", err=True)
        if isinstance(error, RawValidationError) and error.check_id == "archive.present":
            typer.echo(
                "Acquire the pinned source with `mpi data acquire injection_molding`.",
                err=True,
            )
        raise typer.Exit(code=1) from error
    typer.echo(f"output: {result.output_path}")
    typer.echo(f"disposition: {result.disposition}")
    typer.echo(f"source version: {result.source_version}")
    typer.echo(f"source manifest sha256: {result.source_manifest_sha256}")
    typer.echo("counts:")
    for table in ("units", "operations", "process_features", "signals", "quality", "context"):
        typer.echo(f"- {table}: {getattr(result.bundle, table).height}")
    typer.echo("limitations:")
    for limitation in result.bundle.metadata.limitations:
        typer.echo(f"- {limitation}")
