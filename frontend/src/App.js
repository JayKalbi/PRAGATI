import React, { useState, useEffect, useRef } from 'react';
import { MapContainer, TileLayer, Polygon, Tooltip } from 'react-leaflet';
import { RadialBarChart, RadialBar, ResponsiveContainer, PolarAngleAxis } from 'recharts';

const BACKEND_HTTP = 'http://localhost:8000';
const BACKEND_WS = 'ws://localhost:8000/ws';

export default function App() {
  const [data, setData] = useState(null);
  const [connected, setConnected] = useState(false);
  const [rainfallInput, setRainfallInput] = useState(15);
  const wsRef = useRef(null);

  useEffect(() => {
    let reconnectTimer = null;

    const connectWebSocket = () => {
      const ws = new WebSocket(BACKEND_WS);
      wsRef.current = ws;

      ws.onopen = () => {
        setConnected(true);
      };

      ws.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);
          setData(payload);
          setRainfallInput(payload.rainfall_rate);
        } catch (e) {
          console.error("WS Parse Error:", e);
        }
      };

      ws.onclose = () => {
        setConnected(false);
        reconnectTimer = setTimeout(connectWebSocket, 2000);
      };

      ws.onerror = () => {
        ws.close();
      };
    };

    connectWebSocket();

    return () => {
      if (wsRef.current) wsRef.current.close();
      if (reconnectTimer) clearTimeout(reconnectTimer);
    };
  }, []);

  // Handlers for REST Controls
  const toggleAnomaly = async () => {
    try {
      await fetch(`${BACKEND_HTTP}/toggle-anomaly`, { method: 'POST' });
    } catch (e) {
      console.error(e);
    }
  };

  const handleRainfallChange = async (e) => {
    const val = parseFloat(e.target.value);
    setRainfallInput(val);
    try {
      await fetch(`${BACKEND_HTTP}/set-rainfall/${val}`, { method: 'POST' });
    } catch (err) {
      console.error(err);
    }
  };

  const toggleApproval = async () => {
    try {
      await fetch(`${BACKEND_HTTP}/toggle-human-approval`, { method: 'POST' });
    } catch (e) {
      console.error(e);
    }
  };

  const deployPump = async () => {
    try {
      await fetch(`${BACKEND_HTTP}/deploy-pump`, { method: 'POST' });
    } catch (e) {
      console.error(e);
    }
  };

  const deployBoat = async () => {
    try {
      await fetch(`${BACKEND_HTTP}/deploy-boat`, { method: 'POST' });
    } catch (e) {
      console.error(e);
    }
  };

  // Hexagon styling based on water depth
  const getHexStyle = (depth) => {
    let fillColor = '#10b981'; // green fallback
    let color = '#34d399';
    if (depth < 0.1) {
      fillColor = '#0284c7'; // Blue (0 - 0.1m)
      color = '#38bdf8';
    } else if (depth <= 0.4) {
      fillColor = '#eab308'; // Yellow (0.1 - 0.4m)
      color = '#fde047';
    } else {
      fillColor = '#dc2626'; // Red (> 0.4m)
      color = '#f87171';
    }

    return {
      fillColor,
      weight: 1.5,
      opacity: 0.9,
      color,
      fillOpacity: 0.65
    };
  };

  const aether = data?.aether || {
    status: 'RELEASE',
    score: 0.92,
    action: 'Initializing...',
    metrics: { ood_score: 0.2, ensemble_disagreement: 0.05, sensor_quality: 0.98, physics_residual: 0.04 }
  };

  const gaugeData = [
    {
      name: 'Trust',
      value: Math.round(aether.score * 100),
      fill: aether.status === 'RELEASE' ? '#10b981' : aether.status === 'REFINE' ? '#f59e0b' : '#ef4444'
    }
  ];

  return (
    <div className="app-container">
      {/* Top Navigation Bar */}
      <header className="app-header">
        <div className="header-left">
          <span className="logo-badge">PRAGATI</span>
          <span className="header-title">Command & Control Center</span>
          <span className="header-subtitle">Predict → Trust → Act (Disaster Intelligence)</span>
        </div>
        <div className="header-right">
          <div className={`connection-indicator ${connected ? '' : 'disconnected'}`}>
            <span className="indicator-dot"></span>
            {connected ? 'LIVE TELEMETRY (1Hz)' : 'CONNECTING TO BACKEND...'}
          </div>
        </div>
      </header>

      {/* Main Split Layout */}
      <div className="app-body">
        {/* Left 60%: Interactive Map with H3 Hex Grid */}
        <div className="map-pane">
          <MapContainer
            center={[19.0760, 72.8777]}
            zoom={14}
            zoomControl={false}
            attributionControl={false}
          >
            <TileLayer
              url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
            />

            {data?.hex_grid?.map((hex) => (
              <Polygon
                key={hex.id}
                positions={hex.coordinates}
                pathOptions={getHexStyle(hex.depth)}
              >
                <Tooltip direction="top" opacity={0.9} sticky>
                  <div style={{ fontSize: '11px', lineHeight: '1.4' }}>
                    <strong>{hex.id}</strong><br />
                    Depth: <span style={{ color: '#38bdf8' }}>{hex.depth.toFixed(2)} m</span><br />
                    Risk: <strong>{hex.risk_level}</strong><br />
                    Elevation Bias: {hex.elevation_factor}x
                  </div>
                </Tooltip>
              </Polygon>
            ))}
          </MapContainer>

          {/* Map Overlay Legend */}
          <div className="map-overlay-legend">
            <div className="legend-title">Inundation Risk (Depth)</div>
            <div className="legend-item">
              <span className="legend-color" style={{ background: '#0284c7' }}></span>
              <span>Nominal &lt; 0.10m</span>
            </div>
            <div className="legend-item">
              <span className="legend-color" style={{ background: '#eab308' }}></span>
              <span>Warning 0.10m – 0.40m</span>
            </div>
            <div className="legend-item">
              <span className="legend-color" style={{ background: '#dc2626' }}></span>
              <span>Critical &gt; 0.40m</span>
            </div>
          </div>
        </div>

        {/* Right 40%: Command Sidebar */}
        <div className="sidebar-pane">
          {/* Top: AETHER Reliability Gate Card */}
          <div className="card">
            <div className="card-title">
              <span>AETHER Trust Gate</span>
              <span style={{ fontSize: '11px', color: '#64748b' }}>Latent Penultimate OOD</span>
            </div>

            <div className={`aether-banner ${aether.status}`}>
              <div>
                <div style={{ fontSize: '11px', textTransform: 'uppercase', opacity: 0.8 }}>Gate Decision</div>
                <div className="aether-status-text">{aether.status}</div>
              </div>
              <div className="aether-score-badge">
                Trust: {(aether.score * 100).toFixed(0)}%
              </div>
            </div>

            <div className="aether-action-text">
              {aether.action}
            </div>

            <div style={{ height: 110, width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <ResponsiveContainer width="100%" height="100%">
                <RadialBarChart
                  cx="50%"
                  cy="70%"
                  innerRadius="65%"
                  outerRadius="100%"
                  barSize={12}
                  data={gaugeData}
                  startAngle={180}
                  endAngle={0}
                >
                  <PolarAngleAxis type="number" domain={[0, 100]} angleAxisId={0} tick={false} />
                  <RadialBar background={{ fill: '#1e293b' }} dataKey="value" cornerRadius={6} />
                </RadialBarChart>
              </ResponsiveContainer>
            </div>

            <div className="metrics-grid">
              <div className="metric-box">
                <div className="metric-label">Latent OOD</div>
                <div className="metric-value">{aether.metrics?.ood_score}</div>
              </div>
              <div className="metric-box">
                <div className="metric-label">Disagreement</div>
                <div className="metric-value">{aether.metrics?.ensemble_disagreement}</div>
              </div>
              <div className="metric-box">
                <div className="metric-label">Sensor Q</div>
                <div className="metric-value" style={{ color: aether.metrics?.sensor_quality > 0.8 ? '#10b981' : '#ef4444' }}>
                  {aether.metrics?.sensor_quality}
                </div>
              </div>
              <div className="metric-box">
                <div className="metric-label">Physics Res</div>
                <div className="metric-value">{aether.metrics?.physics_residual}</div>
              </div>
            </div>
          </div>

          {/* Middle: Controls Card */}
          <div className="card">
            <div className="card-title">Demo Controls & Forcing</div>
            
            <div className="control-row slider-container">
              <div className="slider-header">
                <span>Rainfall Intensity (Forcing)</span>
                <strong>{rainfallInput} mm/hr</strong>
              </div>
              <input
                type="range"
                min="0"
                max="100"
                step="1"
                value={rainfallInput}
                onChange={handleRainfallChange}
              />
            </div>

            <div className="control-row">
              <button
                className={`btn-anomaly ${data?.anomaly_active ? 'active' : 'inactive'}`}
                onClick={toggleAnomaly}
              >
                {data?.anomaly_active ? '✓ Anomaly Active (Click to Clear)' : '🚨 Inject Sensor Anomaly / OOD'}
              </button>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: '#94a3b8' }}>
              <span>Live Sensor Depth:</span>
              <strong style={{ color: '#38bdf8' }}>{data?.water_depth?.toFixed(2) || '0.00'} m</strong>
            </div>
          </div>

          {/* Bottom: Resource Optimization & Human Approval Panel */}
          <div className="card">
            <div className="card-title">
              <span>Operational Resource Deployment</span>
              <span style={{ fontSize: '10px', color: '#64748b' }}>OR-Tools MILP</span>
            </div>

            <div className="approval-box">
              <div>
                <div style={{ fontSize: '12px', fontWeight: 600, color: '#f8fafc' }}>Human Dispatch Authority</div>
                <div style={{ fontSize: '10px', color: '#94a3b8' }}>Mandatory human-in-the-loop gate</div>
              </div>
              <label className="toggle-switch">
                <input
                  type="checkbox"
                  checked={data?.human_approval || false}
                  onChange={toggleApproval}
                />
                <span className="slider-toggle"></span>
              </label>
            </div>

            <div className="resource-action-grid">
              <div className="resource-card">
                <div>
                  <div className="resource-title">Dewatering Pumps</div>
                  <div className="resource-meta">
                    Available: {data?.pumps ? (data.pumps.available - data.pumps.active) : 4} | Active: {data?.pumps?.active || 0}
                  </div>
                </div>
                <button
                  className="btn-action"
                  onClick={deployPump}
                  disabled={!data?.human_approval || data?.pumps?.active >= data?.pumps?.available}
                >
                  Deploy Pump (-0.07m)
                </button>
              </div>

              <div className="resource-card">
                <div>
                  <div className="resource-title">Rescue Boats</div>
                  <div className="resource-meta">
                    Available: {data?.boats ? (data.boats.available - data.boats.deployed) : 2} | Deployed: {data?.boats?.deployed || 0}
                  </div>
                </div>
                <button
                  className="btn-action"
                  onClick={deployBoat}
                  disabled={!data?.human_approval || data?.boats?.deployed >= data?.boats?.available}
                >
                  Deploy Boat (+Reach)
                </button>
              </div>
            </div>
          </div>

          {/* System Ticker / Audit Log */}
          <div className="system-ticker">
            <strong>System Log:</strong> {data?.last_action_msg || 'Connecting...'}
          </div>
        </div>
      </div>
    </div>
  );
}
