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


def load_dataset_config(path: Path) -> DatasetConfig:
    """Load and validate a YAML dataset configuration."""
    with path.open(encoding="utf-8") as stream:
        raw: object = yaml.safe_load(stream)
    return DatasetConfig.model_validate(raw)
