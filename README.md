# Pragati: Urban Flood Forecasting & Reliability-Aware Decision Support

> **Predict → Trust → Act**

PRAGATI is an M.Tech research project developing a Physics-Guided Spatio-Temporal Graph Neural Network (PG-STGNN) paired with an active reliability gating mechanism (AETHER) for multi-horizon urban flood inundation depth forecasting and constrained emergency-resource decision support.

---

## 1. Frozen Scientific Baseline

- **Domain:** Urban Flooding & Waterlogging
- **Spatial Resolution:** Uber H3 Discrete Global Grid Resolution 9 (~0.1 km²/cell)
- **Timestep ($\Delta t$):** 15 minutes
- **Lookback Window ($T_{in}$):** 6.0 hours (24 discrete timesteps)
- **Forecast Horizons ($H$):** 2, 4, and 6 hours (8, 16, and 24 discrete future timesteps)
- **Primary Target:** Inundation depth in metres above local ground level
- **Neural Model:** PG-STGNN (GraphSAGE spatial encoder + GRU temporal encoder)
- **Ensemble:** 3 independently seeded models to generate ensemble disagreement
- **Physics Guidance:** Continuity-inspired volume-conservation regularization
- **Reliability Gate:** AETHER Gate (Mahalanobis latent OOD, ensemble disagreement, sensor quality, physics residual $\to$ Release / Refine / Abstain)
- **Simulator:** Rapid Terrain-Driven Surface-Flow Simulator (synthetic events & selective refinement)

For detailed architectural notes, see [`docs/PRAGATI_CONTEXT.md`](docs/PRAGATI_CONTEXT.md) and [`PRAGATI_MASTER_PROPOSAL_FINAL.md`](PRAGATI_MASTER_PROPOSAL_FINAL.md).

---

## 2. Repository Layout

```text
D:\Pragati/
├── configs/                  # Declarative experiment and baseline YAML files
│   └── baseline_config.yaml  # Frozen baseline configuration
├── data/                     # Data stores (strictly gitignored)
│   ├── raw/                  # Raw sensor telemetry and external GIS data
│   ├── interim/              # Cleaned and aligned temporal slices
│   ├── processed/            # H3 graph datasets and normalized features
│   └── synthetic/            # Synthetic events from surface-flow simulator
├── docs/                     # Research specifications and context
│   └── PRAGATI_CONTEXT.md    # Summary of frozen scientific baseline
├── notebooks/                # Jupyter exploration and visualization notebooks
├── scripts/                  # Reproducible CLI scripts for training and evaluation
├── src/
│   └── pragati/              # Core library
│       ├── config.py         # Pydantic configuration schemas & timestep calculations
│       ├── aether/           # Reliability gate & failure detection
│       ├── baselines/        # Comparative baselines (Persistence, GRU, ST-GNN)
│       ├── data/             # Ingestion, validation, quality metrics
│       ├── evaluation/       # Point, spatial, reliability, and latency metrics
│       ├── graph/            # H3 graph & D8 terrain edge attributes
│       ├── models/           # PG-STGNN architecture (GraphSAGE + GRU)
│       ├── simulation/       # Rapid terrain-driven surface-flow simulator
│       └── utils/            # Seeding, I/O, logging utilities
├── tests/                    # Pytest test suite
│   └── test_config.py        # Config validations & horizon-to-timestep tests
├── AGENTS.md                 # Assistant rules for research integrity & strict typing
├── pyproject.toml            # Project metadata and pinned dependencies
└── README.md                 # Project introduction and quickstart guide
```

---

## 3. Setup and Installation

### Prerequisites
- Python 3.11+ (recommended: Python 3.11 virtual environment)
- Git

### Recommended Environment Setup

Using `venv`:
```bash
# Create and activate a clean virtual environment
python -m venv .venv
# On Windows (PowerShell):
.venv\Scripts\Activate.ps1
# On Linux/macOS:
source .venv/bin/activate

# Upgrade pip
python -m pip install --upgrade pip
```

### Install Core & PyTorch Dependencies

```bash
# Install PyTorch & Torch-Geometric (adjust CUDA version if applicable)
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
pip install torch-geometric

# Install PRAGATI in editable development mode with core dependencies
pip install -e .
```

---

## 4. Running Tests

To run the unit test suite:

```bash
pytest
```

To run with coverage and verbose logging:

```bash
pytest -v --cov=src/pragati
```

---

## 5. Development Principles

- **No Hardcoded Absolute Paths:** Dynamic resolution via `pathlib.Path`.
- **Seed Everything:** Deterministic seeding for torch, numpy, and random.
- **Strict Typing:** All modules strictly annotated and checked with `mypy`.
- **Reproducibility:** Zero claims without accompanying run logs.
