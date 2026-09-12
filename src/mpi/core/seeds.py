"""Deterministic random seed conventions."""

import random

DEFAULT_SEED = 42


def set_global_seed(seed: int = DEFAULT_SEED) -> None:
    """Seed standard-library randomness used by foundation code."""
    random.seed(seed)
