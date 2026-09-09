import asyncio
import math
import time
from typing import List, Dict, Any
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="PRAGATI Disaster Intelligence API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# CHANGED: GET route at root "/" returning required status
@app.get("/")
def root():
    return {"status": "PRAGATI API Running", "version": "1.0"}

# -------------------------------------------------------------
# Global State
# -------------------------------------------------------------
class SystemState:
    def __init__(self):
        self.base_depth: float = 0.05
        self.current_depth: float = 0.05
        self.rainfall_rate: float = 15.0  # mm/hr
        self.anomaly_active: bool = False
        self.human_approval: bool = False
        self.pump_count: int = 4
        self.boat_count: int = 2
        self.active_pumps: int = 0
        self.deployed_boats: int = 0
        self.last_action_msg: str = "System initialized. Monitoring sensor telemetry."
        self.step_counter: int = 0
        self.hex_grid: List[Dict[str, Any]] = []
        self.init_hex_grid()

    def init_hex_grid(self):
        # 5x5 hexagon-like city grid centered at Mumbai (approx lat 19.0760, lon 72.8777)
        base_lat = 19.0760
        base_lon = 72.8777
        grid = []
        r = 0.006  # hexagon radius in degrees approx

        for row in range(5):
            for col in range(5):
                hex_id = f"HEX-{row}-{col}"
                # stagger rows for honeycomb arrangement
                lat_offset = (row - 2) * (r * 1.5)
                lon_offset = (col - 2) * (r * math.sqrt(3)) + ((row % 2) * (r * math.sqrt(3) / 2))
                center_lat = base_lat + lat_offset
                center_lon = base_lon + lon_offset

                # 6 vertices of hexagon
                points = []
                for i in range(6):
                    angle_deg = 60 * i - 30
                    angle_rad = math.radians(angle_deg)
                    p_lat = center_lat + r * math.sin(angle_rad) * 0.85
                    p_lon = center_lon + r * math.cos(angle_rad)
                    points.append([p_lat, p_lon])
                points.append(points[0])  # close ring

                # terrain factor for spatial diversity
                elevation_factor = 0.8 + 0.4 * math.sin(row * 1.2 + col * 1.5)

                grid.append({
                    "id": hex_id,
                    "row": row,
                    "col": col,
                    "center": [center_lat, center_lon],
                    "coordinates": points,
                    "elevation_factor": round(elevation_factor, 2),
                    "depth": 0.05,
                    "risk_level": "LOW"
                })
        self.hex_grid = grid

    def update_physics(self):
        self.step_counter += 1
        t = self.step_counter * 0.15

        # Natural slow water oscillation between 0.0 and 0.8m
        oscillation = 0.18 * math.sin(t) + 0.08 * math.cos(t * 0.6)
        rain_effect = (self.rainfall_rate / 100.0) * 0.45
        pump_reduction = self.active_pumps * 0.07

        # Inundation depth calculation with natural damping
        raw_depth = self.base_depth + oscillation + rain_effect - pump_reduction
        if raw_depth < 0.0:
            raw_depth = 0.01

        # If anomaly is injected, add erratic corrupted spikes
        if self.anomaly_active:
            raw_depth = max(raw_depth, 0.68 + 0.15 * math.sin(t * 3.0))

        self.current_depth = round(min(raw_depth, 0.95), 3)

        # Update each hexagon depth in the grid based on elevation factor
        for cell in self.hex_grid:
            cell_depth = round(self.current_depth * cell["elevation_factor"], 3)
            cell["depth"] = cell_depth
            if cell_depth < 0.1:
                cell["risk_level"] = "LOW"
            elif cell_depth <= 0.4:
                cell["risk_level"] = "MEDIUM"
            else:
                cell["risk_level"] = "HIGH"

    def get_aether_status(self) -> Dict[str, Any]:
        # AETHER decision gate logic matching PRD rules
        if self.current_depth > 0.5 or self.anomaly_active:
            status = "ABSTAIN"
            score = 0.15
            action = "HALT AUTOMATION: Requesting Operator Manual Review"
            reason = "Critical inundation threshold exceeded or sensor corruption detected"
        elif 0.2 <= self.current_depth <= 0.5:
            status = "REFINE"
            score = 0.55
            action = "INVOKE SURROGATE: Running Rapid Surface-Flow Simulation"
            reason = "Moderate risk with physical uncertainty; running secondary verification"
        else:
            status = "RELEASE"
            score = 0.92
            action = "AUTONOMOUS PASS: Dispatched to Resource Optimization Engine"
            reason = "High confidence, low residual error, physical bounds verified"

        ood_score = round(3.8 if self.anomaly_active else (0.4 + self.current_depth * 1.5), 2)
        disagreement = round(0.42 if self.anomaly_active else (0.05 + self.current_depth * 0.18), 2)
        sensor_quality = round(0.25 if self.anomaly_active else 0.98, 2)
        physics_residual = round(0.35 if self.anomaly_active else 0.06, 2)

        return {
            "status": status,
            "score": score,
            "action": action,
            "reason": reason,
            "metrics": {
                "ood_score": ood_score,
                "ensemble_disagreement": disagreement,
                "sensor_quality": sensor_quality,
                "physics_residual": physics_residual
            }
        }

    def get_full_telemetry(self) -> Dict[str, Any]:
        aether = self.get_aether_status()
        return {
            "timestamp": time.strftime("%H:%M:%S"),
            "water_depth": self.current_depth,
            "rainfall_rate": self.rainfall_rate,
            "anomaly_active": self.anomaly_active,
            "human_approval": self.human_approval,
            "pumps": {
                "available": self.pump_count,
                "active": self.active_pumps
            },
            "boats": {
                "available": self.boat_count,
                "deployed": self.deployed_boats
            },
            "last_action_msg": self.last_action_msg,
            "aether": aether,
            "hex_grid": self.hex_grid
        }

state = SystemState()

# -------------------------------------------------------------
# Background Physics Simulation Task
# -------------------------------------------------------------
@app.on_event("startup")
async def startup_event():
    async def physics_loop():
        while True:
            state.update_physics()
            await asyncio.sleep(1.0)
    asyncio.create_task(physics_loop())

# -------------------------------------------------------------
# REST Control Endpoints
# -------------------------------------------------------------
class RainfallUpdate(BaseModel):
    value: float

@app.post("/toggle-anomaly")
async def toggle_anomaly():
    state.anomaly_active = not state.anomaly_active
    state.last_action_msg = (
        "ANOMALY INJECTED: Sensor reading corrupted / out-of-distribution event triggered."
        if state.anomaly_active else
        "ANOMALY CLEARED: Telemetry restored to nominal calibrated state."
    )
    return {"status": "ok", "anomaly_active": state.anomaly_active, "message": state.last_action_msg}

@app.post("/set-rainfall/{value}")
async def set_rainfall(value: float):
    state.rainfall_rate = max(0.0, min(100.0, value))
    state.last_action_msg = f"Rainfall forcing adjusted to {state.rainfall_rate:.1f} mm/hr."
    return {"status": "ok", "rainfall_rate": state.rainfall_rate}

@app.post("/toggle-human-approval")
async def toggle_human_approval():
    state.human_approval = not state.human_approval
    state.last_action_msg = f"Human Dispatch Authority: {'ENABLED (Authorized)' if state.human_approval else 'DISABLED (Locked)'}."
    return {"status": "ok", "human_approval": state.human_approval}

@app.post("/deploy-pump")
async def deploy_pump():
    if not state.human_approval:
        return {"status": "rejected", "message": "ACTION BLOCKED: Human Approval is OFF. Authorization required."}
    
    if state.active_pumps < state.pump_count:
        state.active_pumps += 1
        state.last_action_msg = f"PUMP DISPATCHED: Pump #{state.active_pumps} active. Water depth reduced by -0.07m."
        return {"status": "success", "active_pumps": state.active_pumps, "message": state.last_action_msg}
    else:
        return {"status": "limit_reached", "message": "All available pumps (4) are already actively pumping."}

@app.post("/deploy-boat")
async def deploy_boat():
    if not state.human_approval:
        return {"status": "rejected", "message": "ACTION BLOCKED: Human Approval is OFF. Authorization required."}
    
    if state.deployed_boats < state.boat_count:
        state.deployed_boats += 1
        state.last_action_msg = f"RESCUE BOAT DISPATCHED: Unit #{state.deployed_boats} deployed. Reachability to cutoff sector +45%."
        return {"status": "success", "deployed_boats": state.deployed_boats, "message": state.last_action_msg}
    else:
        return {"status": "limit_reached", "message": "All emergency rescue boats (2) are actively deployed."}

@app.post("/reset-resources")
async def reset_resources():
    state.active_pumps = 0
    state.deployed_boats = 0
    state.last_action_msg = "Resources recalled to depots."
    return {"status": "ok", "message": state.last_action_msg}

# -------------------------------------------------------------
# WebSocket Stream
# -------------------------------------------------------------
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            payload = state.get_full_telemetry()
            await websocket.send_json(payload)
            await asyncio.sleep(1.0)
    except WebSocketDisconnect:
        pass
    except Exception:
        await websocket.close()
