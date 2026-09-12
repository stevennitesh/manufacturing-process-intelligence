from pathlib import Path

import pytest
from pydantic import ValidationError

from mqi.core.config import load_dataset_config


def test_load_dataset_config() -> None:
    config = load_dataset_config(Path("configs/datasets/solidair.yaml"))

    assert config.name == "solidair"
    assert config.stage == "mvp"
    assert config.enabled is False


def test_reject_unknown_dataset_config_field(tmp_path: Path) -> None:
    path = tmp_path / "dataset.yaml"
    path.write_text(
        "name: example\nstage: mvp\nenabled: false\nversion: test\nunknown: value\n",
        encoding="utf-8",
    )

    with pytest.raises(ValidationError):
        load_dataset_config(path)
