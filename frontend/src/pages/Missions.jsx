import React, { useState } from "react";
import { executeMissionStep, fetchMissionHistory } from "../api";
import { Play, CheckCircle, Truck, Package, Clock, ShieldAlert } from "lucide-react";

export default function Missions({
  vehicles = [],
  locations = [],
  missionData,
  onRefreshData,
  setActiveRouteCoords,
}) {
  const [executing, setExecuting] = useState(false);
  const [latestResult, setLatestResult] = useState(null);

  const activeVehicle = vehicles[0];

  const handleStep = async () => {
    setExecuting(true);
    try {
      const res = await executeMissionStep();
      setLatestResult(res);
      if (res.geometry) {
        setActiveRouteCoords(res.geometry);
      }
      if (onRefreshData) onRefreshData();
    } catch (err) {
      alert("Error executing delivery step: " + err.message);
    } finally {
      setExecuting(false);
    }
  };

  const summary = missionData?.summary || {
    total_locations: locations.length,
    fully_served: 0,
    partially_served: 0,
    total_delivered_units: 0,
    total_distance_km: 0,
    total_travel_time_min: 0,
    reroutes_triggered: 0,
  };

  const history = missionData?.history || [];

  return (
    <div style={{ padding: "1.5rem", maxWidth: "1280px", margin: "0 auto" }}>
      {/* Page Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1.5rem" }}>
        <div>
          <h2 style={{ margin: 0, fontSize: "1.4rem", color: "#0f172a", fontWeight: "700" }}>
            Disaster Relief Mission Execution
          </h2>
          <p style={{ margin: "4px 0 0 0", fontSize: "0.875rem", color: "#64748b" }}>
            Execute greedy prioritization steps and track real-time delivery progress.
          </p>
        </div>

        <button
          onClick={handleStep}
          disabled={executing || !activeVehicle || activeVehicle.current_load <= 0}
          style={{
            display: "flex",
            alignItems: "center",
            gap: "0.5rem",
            padding: "0.65rem 1.25rem",
            borderRadius: "8px",
            border: "none",
            background: activeVehicle && activeVehicle.current_load > 0 ? "#10b981" : "#94a3b8",
            color: "#ffffff",
            fontSize: "0.9rem",
            fontWeight: "600",
            cursor: activeVehicle && activeVehicle.current_load > 0 ? "pointer" : "not-allowed",
            boxShadow: "0 2px 6px rgba(16,185,129,0.3)"
          }}
        >
          <Play size={18} />
          {executing ? "Dispatching Delivery..." : "▶ Execute Next Delivery Step"}
        </button>
      </div>

      {/* Latest Step Result Alert */}
      {latestResult && (
        <div style={{
          padding: "1rem 1.25rem",
          borderRadius: "10px",
          background: latestResult.success ? "#f0fdf4" : "#fef2f2",
          border: `1px solid ${latestResult.success ? "#bbf7d0" : "#fca5a5"}`,
          marginBottom: "1.5rem"
        }}>
          <div style={{ fontWeight: "700", color: latestResult.success ? "#166534" : "#991b1b", fontSize: "0.95rem", marginBottom: "4px" }}>
            {latestResult.success ? "✅ Delivery Mission Step Completed" : "⚠️ Step Execution Warning"}
          </div>
          <p style={{ margin: "0 0 0.5rem 0", fontSize: "0.85rem", color: "#334155" }}>
            {latestResult.message}
          </p>
          {latestResult.success && (
            <div style={{ fontSize: "0.8rem", color: "#475569", display: "flex", gap: "1.5rem" }}>
              <span><strong>Destination:</strong> {latestResult.location_id}</span>
              <span><strong>Delivered:</strong> {latestResult.delivered_amount} units</span>
              <span><strong>Distance:</strong> {latestResult.distance_km} km</span>
              <span><strong>Arrival Clock:</strong> {latestResult.arrival_time_min} min</span>
              <span><strong>Remaining Load:</strong> {latestResult.remaining_vehicle_load} units</span>
            </div>
          )}
        </div>
      )}

      {/* Mission Statistics Cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "1rem", marginBottom: "1.5rem" }}>
        <div style={cardStyle}>
          <div style={cardLabel}>Locations Fully Served</div>
          <div style={cardValue}>{summary.fully_served} <span style={{ fontSize: "0.9rem", color: "#64748b" }}>/ {summary.total_locations}</span></div>
        </div>

        <div style={cardStyle}>
          <div style={cardLabel}>Total Supplies Delivered</div>
          <div style={{ ...cardValue, color: "#2563eb" }}>{summary.total_delivered_units} <span style={{ fontSize: "0.85rem" }}>units</span></div>
        </div>

        <div style={cardStyle}>
          <div style={cardLabel}>Total Distance Traversed</div>
          <div style={{ ...cardValue, color: "#059669" }}>{summary.total_distance_km} <span style={{ fontSize: "0.85rem" }}>km</span></div>
        </div>

        <div style={cardStyle}>
          <div style={cardLabel}>Reroutes Triggered</div>
          <div style={{ ...cardValue, color: "#d97706" }}>{summary.reroutes_triggered}</div>
        </div>
      </div>

      {/* Delivery History Log Table */}
      <div style={{ background: "#ffffff", borderRadius: "10px", border: "1px solid #e2e8f0", overflow: "hidden" }}>
        <div style={{ padding: "0.85rem 1.25rem", borderBottom: "1px solid #e2e8f0", fontWeight: "700", color: "#0f172a" }}>
          📜 Delivery Execution History Log
        </div>

        {history.length === 0 ? (
          <div style={{ padding: "2rem", textAlign: "center", color: "#94a3b8", fontSize: "0.9rem" }}>
            No deliveries executed yet. Click "Execute Next Delivery Step" to start dispatching relief.
          </div>
        ) : (
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.85rem", textAlign: "left" }}>
            <thead>
              <tr style={{ background: "#f8fafc", color: "#475569", textTransform: "uppercase", fontSize: "0.75rem" }}>
                <th style={thStyle}>Step</th>
                <th style={thStyle}>Vehicle</th>
                <th style={thStyle}>Destination</th>
                <th style={thStyle}>Route</th>
                <th style={thStyle}>Distance (km)</th>
                <th style={thStyle}>Transit Time (min)</th>
                <th style={thStyle}>Arrival Clock</th>
                <th style={thStyle}>Delivered</th>
                <th style={thStyle}>Cargo Left</th>
              </tr>
            </thead>
            <tbody>
              {history.map((row, idx) => (
                <tr key={idx} style={{ borderBottom: "1px solid #e2e8f0" }}>
                  <td style={{ ...tdStyle, fontWeight: "700" }}>#{idx + 1}</td>
                  <td style={tdStyle}>{row.vehicle_id}</td>
                  <td style={{ ...tdStyle, fontWeight: "600", color: "#0f172a" }}>{row.location_id}</td>
                  <td style={{ ...tdStyle, fontFamily: "monospace" }}>{row.route ? row.route.join(" → ") : ""}</td>
                  <td style={tdStyle}>{row.distance_km}</td>
                  <td style={tdStyle}>{row.travel_time_min}</td>
                  <td style={tdStyle}>{row.arrival_time_min} min</td>
                  <td style={{ ...tdStyle, fontWeight: "700", color: "#166534" }}>{row.delivered_amount} units</td>
                  <td style={tdStyle}>{row.remaining_vehicle_load} units</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

const cardStyle = {
  background: "#ffffff",
  padding: "1rem 1.25rem",
  borderRadius: "10px",
  border: "1px solid #e2e8f0",
};

const cardLabel = {
  fontSize: "0.75rem",
  fontWeight: "600",
  color: "#64748b",
  textTransform: "uppercase",
  marginBottom: "4px",
};

const cardValue = {
  fontSize: "1.5rem",
  fontWeight: "800",
  color: "#0f172a",
};

const thStyle = {
  padding: "0.75rem 1rem",
  fontWeight: "700",
  borderBottom: "2px solid #cbd5e1",
};

const tdStyle = {
  padding: "0.75rem 1rem",
  color: "#334155",
};
