"""Deterministic random number generation and seeding utilities for PRAGATI."""

import os
import random
import numpy as np


def set_global_seed(seed: int) -> None:
    """Seed python random, numpy, and torch (if installed) deterministically.

    Also sets deterministic backend flags and environment variables where applicable.

    Args:
        seed: The integer seed to set across all RNGs.
    """
    random.seed(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)
    np.random.seed(seed)

    try:
        import torch

        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
            torch.backends.cudnn.deterministic = True
            torch.backends.cudnn.benchmark = False
    except ImportError:
        pass


def get_rng(seed: int) -> np.random.Generator:
    """Return an isolated NumPy random Generator instance for local reproducibility.

    Args:
        seed: Integer seed for Generator initialization.

    Returns:
        np.random.Generator: Isolated pseudo-random number generator.
    """
    return np.random.default_rng(seed)
