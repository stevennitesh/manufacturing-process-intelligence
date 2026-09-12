import random

from mqi.core.seeds import set_global_seed


def test_seed_repeats_standard_library_randomness() -> None:
    set_global_seed(7)
    first = random.random()
    set_global_seed(7)

    assert random.random() == first
