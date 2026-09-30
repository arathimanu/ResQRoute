import React, { useState } from "react";
import ResQMap from "../components/ResQMap";
import { computeRoute, updateRoadCondition } from "../api";
import { AlertCircle, CheckCircle2, ArrowRight, ShieldAlert, Route } from "lucide-react";

export default function RoutePlanner({
  depots = [],
  locations = [],
  vehicles = [],
  roads = [],
  activeRouteCoords = [],
  setActiveRouteCoords,
  onRefreshData,
}) {
  const [selectedDepot, setSelectedDepot] = useState(depots[0]?.id || "ripon_building");
  const [selectedTarget, setSelectedTarget] = useState(locations[0]?.id || "govt_general_hospital");
  const [loadingRoute, setLoadingRoute] = useState(false);
  const [routeResult, setRouteResult] = useState(null);

  // Road condition form state
  const [selectedRoadEdge, setSelectedRoadEdge] = useState("");
  const [newRoadStatus, setNewRoadStatus] = useState("BLOCKED");
  const [roadUpdateResult, setRoadUpdateResult] = useState(null);
  const [updatingRoad, setUpdatingRoad] = useState(false);

  // Handle route computation
  const handleGenerateRoute = async () => {
    setLoadingRoute(true);
    setRoadUpdateResult(null);
    try {
      const res = await computeRoute(selectedDepot, selectedTarget, true);
      setRouteResult(res);
      if (res.success && res.geometry) {
        setActiveRouteCoords(res.geometry);
      }
    } catch (err) {
      alert("Error computing route: " + err.message);
    } finally {
      setLoadingRoute(false);
    }
  };

  // Handle road condition update
  const handleApplyRoadUpdate = async () => {
    if (!selectedRoadEdge) {
      alert("Please select a road segment from the dropdown or map first.");
      return;
    }
    const [u, v] = selectedRoadEdge.split("|");
    setUpdatingRoad(true);
    try {
      const res = await updateRoadCondition(u, v, newRoadStatus);
      setRoadUpdateResult(res);
      if (res.updated_route && res.updated_route.geometry) {
        setActiveRouteCoords(res.updated_route.geometry);
      }
      if (onRefreshData) onRefreshData();
    } catch (err) {
      alert("Error updating road: " + err.message);
    } finally {
      setUpdatingRoad(false);
    }
  };

  return (
    <div style={{ padding: "1.25rem", height: "calc(100vh - 70px)", display: "flex", gap: "1.25rem" }}>
      {/* Left Control Panel */}
      <div style={{ width: "420px", display: "flex", flexDirection: "column", gap: "1rem", overflowY: "auto" }}>
        
        {/* Route Generator Box */}
        <div style={panelBoxStyle}>
          <h3 style={panelTitleStyle}>
            <Route size={18} color="#2563eb" />
            Route Planning (Dijkstra)
          </h3>

          <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
            <div>
              <label style={labelStyle}>Start Relief Depot / Origin:</label>
              <select
                value={selectedDepot}
                onChange={(e) => setSelectedDepot(e.target.value)}
                style={selectStyle}
              >
                {depots.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.name} ({d.available_supplies} units)
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label style={labelStyle}>Target Disaster Location:</label>
              <select
                value={selectedTarget}
                onChange={(e) => setSelectedTarget(e.target.value)}
                style={selectStyle}
              >
                {locations.map((loc) => (
                  <option key={loc.id} value={loc.id}>
                    {loc.name} (Risk: {loc.risk_level}, Rem: {loc.remaining_demand})
                  </option>
                ))}
              </select>
            </div>

            <button
              onClick={handleGenerateRoute}
              disabled={loadingRoute}
              style={btnPrimaryStyle}
            >
              {loadingRoute ? "Computing Dijkstra Route..." : "📍 Generate Route"}
            </button>
          </div>

          {/* Route Result Summary */}
          {routeResult && (
            <div style={{ marginTop: "1rem", padding: "0.85rem", background: routeResult.success ? "#f0fdf4" : "#fef2f2", borderRadius: "8px", border: `1px solid ${routeResult.success ? "#bbf7d0" : "#fca5a5"}` }}>
              {routeResult.success ? (
                <>
                  <div style={{ fontWeight: "700", color: "#166534", fontSize: "0.875rem", marginBottom: "4px" }}>
                    ✅ Optimal Route Generated
                  </div>
                  <div style={{ fontSize: "0.8rem", color: "#334155" }}>
                    <strong>Distance:</strong> {routeResult.distance_km} km | <strong>ETA:</strong> {routeResult.estimated_travel_time_min} min
                  </div>
                  <div style={{ fontSize: "0.75rem", color: "#64748b", marginTop: "4px", wordBreak: "break-word" }}>
                    <strong>Path:</strong> {routeResult.path.join(" → ")}
                  </div>
                </>
              ) : (
                <div style={{ color: "#991b1b", fontSize: "0.85rem", fontWeight: "600" }}>
                  ⚠️ {routeResult.message}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Dynamic Road Condition Update Box */}
        <div style={panelBoxStyle}>
          <h3 style={panelTitleStyle}>
            <ShieldAlert size={18} color="#ef4444" />
            Simulate Road Hazard & Reroute
          </h3>

          <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
            <div>
              <label style={labelStyle}>Select Road Segment (OSM Edge):</label>
              <select
                value={selectedRoadEdge}
                onChange={(e) => setSelectedRoadEdge(e.target.value)}
                style={selectStyle}
              >
                <option value="">-- Choose road segment --</option>
                {roads.map((r, i) => (
                  <option key={i} value={`${r.u}|${r.v}`}>
                    {r.u} &harr; {r.v} ({r.distance_km} km) [{r.status}]
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label style={labelStyle}>Assign Road Status:</label>
              <select
                value={newRoadStatus}
                onChange={(e) => setNewRoadStatus(e.target.value)}
                style={selectStyle}
              >
                <option value="BLOCKED">🔴 BLOCKED (Impassable / Flooded)</option>
                <option value="DAMAGED">🟠 DAMAGED (1.5x Traversal Cost)</option>
                <option value="CLEAR">🟢 CLEAR (Normal traffic)</option>
              </select>
            </div>

            <button
              onClick={handleApplyRoadUpdate}
              disabled={updatingRoad}
              style={{ ...btnPrimaryStyle, background: "#ef4444" }}
            >
              {updatingRoad ? "Updating & Recalculating..." : "🚨 Apply Hazard & Recalculate"}
            </button>
          </div>

          {/* Reroute Before / After Comparison Result Card */}
          {roadUpdateResult && (
            <div style={{
              marginTop: "1rem",
              padding: "0.85rem",
              borderRadius: "8px",
              background: roadUpdateResult.rerouted ? "#fff1f2" : "#f0fdf4",
              border: `1px solid ${roadUpdateResult.rerouted ? "#fecdd3" : "#bbf7d0"}`
            }}>
              <div style={{
                display: "flex",
                alignItems: "center",
                gap: "6px",
                fontWeight: "700",
                fontSize: "0.9rem",
                color: roadUpdateResult.rerouted ? "#9f1239" : "#166534",
                marginBottom: "0.5rem"
              }}>
                {roadUpdateResult.rerouted ? <AlertCircle size={18} /> : <CheckCircle2 size={18} />}
                {roadUpdateResult.rerouted ? "🚨 REROUTED: YES (Alternative Detour Found)" : "ℹ️ REROUTED: NO (Route Unchanged)"}
              </div>

              <div style={{ fontSize: "0.8rem", color: "#334155", display: "grid", gap: "4px" }}>
                <div>
                  <strong>Previous Route:</strong>{" "}
                  <code>{roadUpdateResult.previous_route.path ? roadUpdateResult.previous_route.path.join(" → ") : "None"}</code>{" "}
                  ({roadUpdateResult.previous_route.distance_km} km)
                </div>
                <div>
                  <strong>Updated Route:</strong>{" "}
                  <code>{roadUpdateResult.updated_route.path ? roadUpdateResult.updated_route.path.join(" → ") : "No feasible route"}</code>{" "}
                  ({roadUpdateResult.updated_route.distance_km} km)
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Right Content Area: Map */}
      <div style={{ flex: 1, position: "relative" }}>
        <ResQMap
          depots={depots}
          locations={locations}
          vehicles={vehicles}
          roads={roads}
          activeRouteCoords={activeRouteCoords}
          previousRouteCoords={roadUpdateResult?.previous_route?.geometry}
          onSelectRoad={(road) => setSelectedRoadEdge(`${road.u}|${road.v}`)}
        />
      </div>
    </div>
  );
}

const panelBoxStyle = {
  background: "#ffffff",
  padding: "1.1rem",
  borderRadius: "10px",
  border: "1px solid #e2e8f0",
  boxShadow: "0 1px 3px rgba(0,0,0,0.05)",
};

const panelTitleStyle = {
  margin: "0 0 0.85rem 0",
  fontSize: "1.05rem",
  fontWeight: "700",
  color: "#0f172a",
  display: "flex",
  alignItems: "center",
  gap: "0.5rem",
};

const labelStyle = {
  display: "block",
  fontSize: "0.775rem",
  fontWeight: "600",
  color: "#475569",
  marginBottom: "4px",
};

const selectStyle = {
  width: "100%",
  padding: "0.55rem 0.75rem",
  borderRadius: "6px",
  border: "1px solid #cbd5e1",
  fontSize: "0.85rem",
  color: "#0f172a",
  background: "#f8fafc",
  outline: "none",
};

const btnPrimaryStyle = {
  width: "100%",
  padding: "0.65rem",
  borderRadius: "6px",
  border: "none",
  background: "#2563eb",
  color: "#ffffff",
  fontSize: "0.875rem",
  fontWeight: "600",
  cursor: "pointer",
  boxShadow: "0 2px 4px rgba(37,99,235,0.2)",
};
