import React from "react";
import ResQMap from "../components/ResQMap";

export default function Dashboard({
  scenario,
  locations = [],
  depots = [],
  vehicles = [],
  roads = [],
  activeRouteCoords = [],
  onSelectRoad,
}) {
  const highRiskCount = locations.filter((l) => l.risk_level === "HIGH").length;
  const medRiskCount = locations.filter((l) => l.risk_level === "MEDIUM").length;
  const totalSupplies = depots.reduce((acc, d) => acc + d.available_supplies, 0);
  const activeVehicle = vehicles[0];

  return (
    <div style={{ padding: "1.25rem", height: "calc(100vh - 70px)", display: "flex", flexDirection: "column", gap: "1rem" }}>
      {/* Top Banner & Stat Cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: "0.85rem" }}>
        <div style={cardStyle}>
          <div style={labelStyle}>Active Scenario</div>
          <div style={{ fontSize: "1rem", fontWeight: "700", color: "#1e293b", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
            {scenario?.scenario?.disaster_name || "Chennai Flood Response"}
          </div>
          <div style={{ fontSize: "0.75rem", color: "#64748b" }}>
            Severity: {((scenario?.scenario?.disaster_severity || 0.8) * 100).toFixed(0)}%
          </div>
        </div>

        <div style={cardStyle}>
          <div style={labelStyle}>Affected Facilities</div>
          <div style={{ fontSize: "1.4rem", fontWeight: "800", color: "#0f172a" }}>
            {locations.length}
          </div>
          <div style={{ fontSize: "0.75rem", color: "#64748b" }}>
            <span style={{ color: "#ef4444", fontWeight: "700" }}>{highRiskCount} High</span> · <span style={{ color: "#f97316", fontWeight: "700" }}>{medRiskCount} Med</span>
          </div>
        </div>

        <div style={cardStyle}>
          <div style={labelStyle}>Relief Depot Inventory</div>
          <div style={{ fontSize: "1.4rem", fontWeight: "800", color: "#2563eb" }}>
            {totalSupplies} <span style={{ fontSize: "0.85rem", fontWeight: "500" }}>units</span>
          </div>
          <div style={{ fontSize: "0.75rem", color: "#64748b" }}>
            {depots[0]?.name || "Main Depot"}
          </div>
        </div>

        <div style={cardStyle}>
          <div style={labelStyle}>Relief Vehicle Payload</div>
          <div style={{ fontSize: "1.4rem", fontWeight: "800", color: "#eab308" }}>
            {activeVehicle?.current_load || 0} / {activeVehicle?.capacity || 0}
          </div>
          <div style={{ fontSize: "0.75rem", color: "#64748b" }}>
            {activeVehicle?.id || "Vehicle Alpha"}
          </div>
        </div>

        <div style={cardStyle}>
          <div style={labelStyle}>Road Network Status</div>
          <div style={{ fontSize: "1.4rem", fontWeight: "800", color: "#10b981" }}>
            {roads.length} <span style={{ fontSize: "0.85rem", fontWeight: "500" }}>segments</span>
          </div>
          <div style={{ fontSize: "0.75rem", color: "#64748b" }}>
            Real OSM Chennai Grid
          </div>
        </div>
      </div>

      {/* Main Content Area: Leaflet Map */}
      <div style={{ flex: 1, position: "relative", minHeight: "400px" }}>
        <ResQMap
          depots={depots}
          locations={locations}
          vehicles={vehicles}
          roads={roads}
          activeRouteCoords={activeRouteCoords}
          onSelectRoad={onSelectRoad}
        />


      </div>
    </div>
  );
}

const cardStyle = {
  background: "#ffffff",
  padding: "0.85rem 1rem",
  borderRadius: "10px",
  border: "1px solid #e2e8f0",
  boxShadow: "0 1px 3px rgba(0,0,0,0.05)",
};

const labelStyle = {
  fontSize: "0.75rem",
  fontWeight: "600",
  color: "#64748b",
  textTransform: "uppercase",
  letterSpacing: "0.03em",
  marginBottom: "4px",
};
