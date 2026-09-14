"""Validated configuration models and loaders."""

from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field


class DatasetConfig(BaseModel):
    """Configuration shared by dataset adapters."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    dataset: str = Field(min_length=1)
    stage: str = Field(min_length=1)
    enabled: bool = False
    source_url: str | None = None
    version: str = Field(min_length=1)


def parse_dataset_config(content: bytes) -> DatasetConfig:
    """Validate one already-read YAML dataset configuration."""
    raw: object = yaml.safe_load(content)
    return DatasetConfig.model_validate(raw)


def load_dataset_config(path: Path) -> DatasetConfig:
    """Load and validate a YAML dataset configuration."""
    return parse_dataset_config(path.read_bytes())
