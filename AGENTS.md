# Agent Rules for PRAGATI Research Repository

These guidelines govern all AI-assisted engineering and research tasks in the PRAGATI repository.

## 1. Environment & Language Specification
- **Python Version:** Python 3.11+ (targeting standard Python 3.11 features; ensure backward/forward compatibility across 3.11–3.12).
- **Strict Typing:** All new functions, methods, and classes must have complete type annotations (`typing` / built-in generics). Use `mypy`-compatible signatures.
- **Testing Standard:** All functional modules must include corresponding unit tests written for `pytest`. Tests must run fast, be isolated, and avoid network dependencies.

## 2. Path Handling & Configuration
- **No Hardcoded Absolute Paths:** Never hardcode absolute system paths (such as `D:\...` or `C:\Users\...`). Always resolve paths dynamically using `pathlib.Path` relative to project roots or configuration anchors.
- **Declarative Configuration:** All hyperparameters, spatial resolutions, lookback windows, horizon steps, model architectures, and operational thresholds must be defined in YAML config files (in `configs/`) and parsed into validated Pydantic models (`src/pragati/config.py`).
- **Data Directory Discipline:** Raw, interim, processed, and synthetic data directories must remain gitignored. Code must gracefully check for data presence or create output directories automatically.

## 3. Scientific Reproducibility & Research Integrity
- **Seed Everything:** Every script or model training routine must strictly seed all RNGs (`torch.manual_seed`, `torch.cuda.manual_seed_all`, `numpy.random.seed`, `random.seed`) and enable deterministic backend flags when applicable.
- **Zero Unsubstantiated Claims:** Never claim accuracy numbers, performance metrics, deployment readiness, or benchmark superiority without an accompanying, verifiable experiment run log or artifact.
- **Baseline Rigor:** Every proposed model innovation (e.g., PG-STGNN, AETHER gates, physics regularizers) must be compared against established baselines (persistence, GRU/temporal-only, non-physics ST-GNN) under identical holdout splits.

## 4. Development & Workflow Hygiene
- **Small, Focused Commits:** Keep code changes minimal, modular, and testable. Do not combine disparate architectural changes into monolithic edits.
- **Clean Interface Boundaries:** Maintain strict separation of concerns across subpackages:
  - `pragati.data`: Ingestion, schema validation, quality scoring, spatial indexing.
  - `pragati.graph`: H3 spatial graph construction, D8 terrain attributes, edge calculations.
  - `pragati.simulation`: Rapid terrain-driven surface-flow simulator for synthetic data & refinement.
  - `pragati.models`: PG-STGNN architecture (GraphSAGE + GRU), multi-horizon heads.
  - `pragati.baselines`: Persistence, standard GRU/LSTM, ST-GNN baselines.
  - `pragati.aether`: Reliability gate (Mahalanobis OOD, ensemble disagreement, sensor quality, physics residual).
  - `pragati.evaluation`: Hydrological, spatial, reliability (selective risk, AUROC), and operational metrics.
  - `pragati.utils`: Seeding, I/O helpers, logging, timing.
