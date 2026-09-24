# PRAGATI Architecture v2.0 — Frozen Scientific Baseline

> **Summary Document**: Distilled reference for the PRAGATI research repository, derived directly from `PRAGATI_MASTER_PROPOSAL_FINAL.md`.

---

## 1. Core Paradigm: Predict → Trust → Act

PRAGATI is a disaster-intelligence and decision-support platform for urban flooding and waterlogging. Rather than treating flood management merely as an end-to-end regression problem, PRAGATI enforces a reliability chokepoint before any decision support or automated resource allocation:

```text
SENSE → UNDERSTAND → PREDICT → TRUST (AETHER) → SIMULATE / REFINE → OPTIMIZE → RECOMMEND → HUMAN ACTION → FEEDBACK
```

---

## 2. Frozen Baseline Specifications

| Dimension | Specification | Notes |
| :--- | :--- | :--- |
| **Domain** | Urban Flooding & Waterlogging | Spatially heterogeneous, rapid rainfall-runoff response |
| **Spatial Unit** | **H3 Resolution 9** | Hexagonal indexing (~0.1 km² per cell, ~100m edge length) |
| **Timestep ($\Delta t$)** | **15 minutes** | Aggregated telemetry and rainfall forcing |
| **Lookback Window ($T_{in}$)** | **6 hours (24 timesteps)** | Historical depth and meteorological context sequence |
| **Forecast Horizons ($H$)** | **2, 4, and 6 hours** | Corresponding to **8, 16, and 24 future timesteps** |
| **Primary Target** | Inundation depth ($d$) | Measured in **metres above local ground level** |
| **Core Architecture** | **GraphSAGE + GRU** | GraphSAGE learns spatial embeddings; GRU models temporal dynamics |
| **Ensemble** | **3 independently seeded models** | Provides ensemble disagreement signal for reliability estimation |
| **Physics Guidance** | Continuity-inspired regularizer | Enforces volumetric conservation: $\Delta V \approx P + I - O - F$ |
| **Reliability Gate** | **AETHER Gate** | Actions: **Release / Refine / Abstain** |
| **Simulator** | Rapid Terrain-Driven Surface-Flow Simulator | Synthetic ground truth generation, edge scenarios, and selective refinement |

---

## 3. AETHER Trust Gate Mechanics

AETHER acts as an active decision gate (not just a passive uncertainty estimate) using four distinct signals:

1. **Mahalanobis Latent OOD ($D_M$):** Computed in the 64-dimensional penultimate feature space against the empirical mean $\mu$ and covariance $\Sigma$ of training embeddings.
2. **Ensemble Disagreement:** Variance across the 3 independently trained PG-STGNN models ($\hat{y}_1, \hat{y}_2, \hat{y}_3$).
3. **Sensor Quality Metric ($q$):** Composite metric capturing missingness, stuck values, physical out-of-bounds, rate-of-change anomalies, and communication dropouts.
4. **Physics Residual ($R_i$):** Water-balance continuity residual violation score.

### Decision Actions:
- **Release:** High reliability. Forecast proceeds directly to the risk engine.
- **Refine:** Borderline confidence / physics inconsistency. Invokes the rapid terrain-driven surface-flow simulator to verify and adjust the state.
- **Abstain:** Severe OOD, massive disagreement, or sensor corruption. Downstream automated optimization is halted; alerts request immediate human operator review.

---

## 4. Research Questions (RQ1–RQ6)

- **RQ1:** Does terrain-aware graph structure improve spatial inundation forecasting over temporal-only and flat spatial baselines?
- **RQ2:** Does continuity-inspired physics regularization improve the physical plausibility and conservation consistency of predicted water depths?
- **RQ3:** Can the multi-signal AETHER gate detect forecast failures more effectively than any single uncertainty or confidence metric?
- **RQ4:** Does selective simulation refinement improve forecast accuracy and stability on extreme or difficult hydrological events?
- **RQ5:** Does reliability-aware gating significantly reduce unsafe downstream automated actions and false alarms?
- **RQ6:** Does constrained mixed-integer linear programming (MILP) with separate pump/boat response formulations improve emergency resource deployment efficiency?

---

## 5. Evaluation Metrics Suite

### A. Point Forecasting Accuracy
- **MAE** (Mean Absolute Error)
- **RMSE** (Root Mean Squared Error)
- **$R^2$** (Coefficient of Determination)
- **NSE** (Nash-Sutcliffe Efficiency) & **KGE** (Kling-Gupta Efficiency)
- **Peak Depth Error:** Absolute difference between predicted and observed peak water level
- **Peak Timing Error:** Lead/lag timestep offset between predicted and observed peak inundation

### B. Spatial Extent & Threshold Classification
Evaluated at operational inundation thresholds (e.g., $d \ge 0.15\text{m}$, $d \ge 0.30\text{m}$):
- **IoU** (Intersection over Union / Critical Success Index)
- **Precision, Recall, F1-Score**

### C. Reliability & Selective Prediction
- **Calibration:** Expected Calibration Error (ECE), calibration curves
- **Selective Risk & Coverage:** Risk-coverage curves evaluating forecast error under varying abstention thresholds
- **Failure Detection:** AUROC and AUPRC for identifying high-error / failed predictions

### D. Operational Feasibility
- **Latency:** PG-STGNN inference latency, AETHER gating latency, simulation refinement latency, and MILP solve time
- **Resource Constraints:** Lead time gained for emergency response crews

---

## 6. Scope Boundaries & Technical Discipline

As specified in the PRAGATI master proposal:
- **No Claim of Full Digital Twin:** The architecture is *digital-twin-inspired* connecting sensing, graph representation, prediction, simulation, and feedback; it does not claim full hydrodynamic or complete municipal digital twin fidelity.
- **Surface Flow vs Complete Underground Hydraulics:** The MVP simulator is a *Rapid Terrain-Driven Surface-Flow Simulator* for synthetic ground truth and rapid refinement, avoiding unsubstantiated claims of solving full 2D shallow-water equations or municipal pipe network equations.
- **Graph Topology:** The spatial graph is a relational spatial network with terrain-aware directed/undirected attributes, *not* a DAG.
- **AETHER Gate:** AETHER is an active reliability chokepoint (Release / Refine / Abstain), not merely an uncertainty quantification module.
- **Human Authority:** All consequential resource allocations remain recommendations subject to mandatory human command approval.

