from pathlib import Path

import pytest
from pydantic import ValidationError

from mpi.core.config import load_dataset_config


def test_load_dataset_config() -> None:
    config = load_dataset_config(Path("configs/datasets/injection_molding.yaml"))

    assert config.dataset == "injection_molding"
    assert config.stage == "mvp"
    assert config.enabled is True


def test_reject_unknown_dataset_config_field(tmp_path: Path) -> None:
    path = tmp_path / "dataset.yaml"
    path.write_text(
        "dataset: example\nstage: mvp\nenabled: false\nversion: test\nunknown: value\n",
        encoding="utf-8",
    )

    with pytest.raises(ValidationError):
        load_dataset_config(path)
