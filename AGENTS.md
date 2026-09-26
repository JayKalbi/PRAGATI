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


## Research Integrity Protocol

This protocol governs all AI-assisted work in the PRAGATI repository. It exists because research artifacts must remain trustworthy and reproducible even when an AI agent is generating or modifying code. Violations of this protocol invalidate the affected phase and require a rollback to the last audited commit.

### R1 — Tests are frozen once committed

Once a test file is committed to the repository, it may only be modified if the test itself is provably wrong (for example, it asserts a physical impossibility, or it asserts behavior that contradicts `docs/PRAGATI_CONTEXT.md`). If the agent believes a test is wrong, it must:

1. **Stop** the current task immediately.
2. **Explain** in writing why the test is wrong, citing a specific line from the master proposal or the frozen baseline.
3. **Wait** for explicit human approval before touching the test.
4. **Never** modify a test simply to make it pass.

A green test suite that was achieved by weakening tests is worse than a red test suite, because it silently destroys the evidence base of the thesis.

### R2 — The frozen baseline document outranks the code

`docs/PRAGATI_CONTEXT.md` and `PRAGATI_MASTER_PROPOSAL_FINAL.md` are the source of truth for all frozen parameters, architecture choices, research questions, and evaluation metrics.

If any of the following contradict the frozen baseline:
- `configs/baseline_config.yaml`
- `src/pragati/config.py`
- Any model, simulator, or evaluation code

…then the **code is wrong**. Fix the code. Never adjust the baseline document to match the code.

Baseline values are frozen because they were committed to in the proposal. Changing them silently invalidates every downstream experiment.

### R3 — Report failures, do not hide them

If a test fails, report the exact failure output verbatim. Do not:

- Wrap the failing code in `try/except` to swallow the error.
- Loosen assertions to make them pass.
- Skip the test with `@pytest.mark.skip`, `pytest.skip()`, or similar.
- Change the expected value in the assertion.
- Reduce the scope of the test (for example, shrinking input size until it passes).

A red test is more valuable than a green lie. Debug output must be shown to the reviewer unedited.

### R4 — Show real file content, not summaries

For any file created, modified, or deleted in a phase, paste the **raw full content** (via `cat` or equivalent) into the phase report. Do not paraphrase. Do not show only the changed lines. Do not write "the file now correctly handles X" without showing the file.

The reviewer cannot verify what it cannot see. Partial diffs hide bugs at the boundaries of changes.

### R5 — Prove-why for every change

Every non-trivial change must cite its justification, either:

- A specific line, section, or figure from `PRAGATI_MASTER_PROPOSAL_FINAL.md`, OR
- A specific requirement from the current phase prompt.

If the agent cannot cite a justification, it must not make the change. "It seemed like a good idea" is not a justification. "It is standard practice" is not a justification. Cite the source.

### R6 — Test-file immutability is enforced by hash

Before any phase, compute SHA256 of every file under `tests/`:

```powershell
python -c "import hashlib, pathlib; [print(hashlib.sha256(p.read_bytes()).hexdigest(), p) for p in sorted(pathlib.Path('tests').rglob('*.py'))]"

After the phase, recompute. Any test file whose hash changed must be:

1. Flagged explicitly in the phase report.
2. Shown as a raw diff against the previous commit.
3. Justified in writing with a citation to the frozen baseline or the phase prompt.
4. Approved by the human reviewer before the phase is considered complete.

Unexplained test-file changes invalidate the phase.

### R7 — Independent verification for physics

For any phase that touches physics — the surface-flow simulator, the continuity-inspired loss, the AETHER physics residual, or any mass-balance/energy-balance computation — the agent must write a **separate, standalone verification script** that:

1. Recomputes the expected result via an **independent method** (different formula, different code path, or an analytical check).
2. Compares its result to the primary implementations result.
3. Reports both numbers side by side along with their relative difference.

If the two methods disagree by more than a stated tolerance, report the discrepancy honestly. Do not adjust the verification script to match the primary implementation. Do not silently pick one result over the other.

### R8 — Never invent config fields or architecture

If the agent believes a new config field, class, module, edge attribute, node feature, or architectural element is needed, it must:

1. **Stop** the current task.
2. **Propose** the addition in writing with a justification citing either the master proposal or the current phase prompt.
3. **Wait** for explicit human approval.

Silent addition or rename of config fields is forbidden. Silent introduction of new modules or classes that are not in the approved folder structure is forbidden.

**Violation record:** During Phase 3A (surface-flow simulator), the agent silently added `temporal.lookback_steps`, `temporal.horizon_steps`, changed `aether.ensemble_size` from 3 to 5, renamed several AETHER fields, and dropped `graph.node_features` and `graph.edge_attributes` from the YAML config. These changes contradicted the frozen baseline and were made without approval. They were caught during the Phase 3A audit and must be reverted. This violation is recorded here as a permanent reminder that R8 exists for a reason.

### Enforcement summary

| Rule | Scope | Enforcement |
|------|-------|-------------|
| R1 | Test files | Hash audit (R6) + human review |
| R2 | Frozen baseline | Audit against `docs/PRAGATI_CONTEXT.md` every phase |
| R3 | Failure reporting | Raw output required in every phase report |
| R4 | File review | Raw `cat` output required for every changed file |
| R5 | Change justification | Citation required; unreferenced changes are rejected |
| R6 | Test immutability | SHA256 before/after every phase |
| R7 | Physics correctness | Independent verification script per physics phase |
| R8 | Config and architecture | Stop-and-ask required; violations logged in this section |

### Reporting requirements

Every phase report must end with an explicit **Integrity Statement** in the following format:

```text
INTEGRITY STATEMENT
- Test files modified this phase: [none / list]
- Frozen baseline fields changed: [none / list with justification]
- New config fields or architecture added: [none / list with justification]
- Independent verification performed: [yes/no, script path]
- Any rules R1-R8 violated: [none / details]


If any answer is not "none", the phase is not complete until the human reviewer accepts the justification.

End of Research Integrity Protocol.



