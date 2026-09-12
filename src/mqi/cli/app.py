"""Top-level MQI command line interface."""

from pathlib import Path
from typing import Annotated

import typer

from mqi import __version__
from mqi.core.config import load_dataset_config
from mqi.core.logging import configure_logging

app = typer.Typer(
    name="mqi",
    help="Manufacturing Quality & Process Intelligence.",
    no_args_is_help=True,
)
config_app = typer.Typer(help="Validate and inspect project configuration.")
app.add_typer(config_app, name="config")


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
    typer.echo(f"valid dataset config: {config.name} ({config.stage})")
