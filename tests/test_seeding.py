"""Unit tests for deterministic seeding utility."""

import random
import numpy as np
from pragati.utils.seeding import get_rng, set_global_seed


def test_set_global_seed_numpy_reproducibility() -> None:
    """Verify that same seed produces identical numpy random outputs."""
    set_global_seed(42)
    val1 = np.random.rand(10)

    set_global_seed(42)
    val2 = np.random.rand(10)

    np.testing.assert_array_equal(val1, val2)


def test_set_global_seed_different_seeds() -> None:
    """Verify that different seeds produce different outputs."""
    set_global_seed(42)
    val1 = np.random.rand(10)

    set_global_seed(99)
    val2 = np.random.rand(10)

    assert not np.array_equal(val1, val2)


def test_set_global_seed_python_random() -> None:
    """Verify that standard library random module is seeded."""
    set_global_seed(1234)
    r1 = [random.random() for _ in range(5)]

    set_global_seed(1234)
    r2 = [random.random() for _ in range(5)]

    assert r1 == r2


def test_get_rng_isolated() -> None:
    """Verify get_rng returns an isolated generator that reproduces across instances."""
    rng1 = get_rng(2026)
    arr1 = rng1.standard_normal(size=5)

    rng2 = get_rng(2026)
    arr2 = rng2.standard_normal(size=5)

    np.testing.assert_array_equal(arr1, arr2)

    rng3 = get_rng(9999)
    arr3 = rng3.standard_normal(size=5)
    assert not np.array_equal(arr1, arr3)


def test_torch_seed_if_available() -> None:
    """Verify torch seeding executes without error and produces deterministic tensors."""
    try:
        import torch

        set_global_seed(42)
        t1 = torch.randn(5)

        set_global_seed(42)
        t2 = torch.randn(5)

        assert torch.equal(t1, t2)
    except ImportError:
        pass
