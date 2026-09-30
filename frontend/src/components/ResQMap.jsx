import React from "react";
import { MapContainer, TileLayer, Marker, Popup, Polyline, Tooltip } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

// Fix standard Leaflet default marker asset paths in Webpack/Vite
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
});

// Custom Leaflet DivIcons
const createCustomIcon = (bgColor, iconText, badgeText = "") => {
  return L.divIcon({
    className: "custom-map-icon",
    html: `
      <div style="
        background-color: ${bgColor};
        width: 32px;
        height: 32px;
        border-radius: 50%;
        border: 2px solid #ffffff;
        box-shadow: 0 3px 8px rgba(0,0,0,0.35);
        display: flex;
        align-items: center;
        justify-content: center;
        color: #ffffff;
        font-weight: bold;
        font-size: 13px;
        position: relative;
      ">
        ${iconText}
        ${badgeText ? `
          <div style="
            position: absolute;
            top: -6px;
            right: -8px;
            background: #0f172a;
            color: #f8fafc;
            border: 1px solid ${bgColor};
            font-size: 9px;
            padding: 1px 4px;
            border-radius: 6px;
            font-weight: 700;
          ">${badgeText}</div>
        ` : ""}
      </div>
    `,
    iconSize: [32, 32],
    iconAnchor: [16, 16],
    popupAnchor: [0, -16],
  });
};

const depotIcon = createCustomIcon("#2563eb", "🏢", "DEPOT");
const vehicleIcon = createCustomIcon("#eab308", "🚛", "TRUCK");

const getRiskIcon = (riskLevel, probPct) => {
  if (riskLevel === "HIGH") return createCustomIcon("#ef4444", "🚨", `${probPct}%`);
  if (riskLevel === "MEDIUM") return createCustomIcon("#f97316", "⚠️", `${probPct}%`);
  return createCustomIcon("#22c55e", "🟢", `${probPct}%`);
};

export default function ResQMap({
  depots = [],
  locations = [],
  vehicles = [],
  activeRouteCoords = [],
  previousRouteCoords = [],
  roads = [],
  onSelectRoad,
  center = [13.0450, 80.2450], // Chennai Central
  zoom = 13,
}) {
  return (
    <MapContainer
      center={center}
      zoom={zoom}
      style={{ width: "100%", height: "100%", borderRadius: "12px" }}
      scrollWheelZoom={true}
    >
      {/* OpenStreetMap Tile Layer */}
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors | ResQRoute'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />

      {/* Render Roads (Damaged/Blocked status highlights) */}
      {roads.map((road, idx) => {
        if (!road.u_coords || !road.v_coords || !road.u_coords[0] || !road.v_coords[0]) return null;

        let color = "#94a3b8"; // CLEAR default
        let dashArray = null;
        let weight = 3;

        if (road.status === "BLOCKED") {
          color = "#ef4444";
          dashArray = "6, 6";
          weight = 4;
        } else if (road.status === "DAMAGED") {
          color = "#f97316";
          weight = 4;
        }

        const edgeCoords = road.geometry && road.geometry.length > 0
          ? road.geometry
          : [road.u_coords, road.v_coords];

        return (
          <Polyline
            key={`road-${idx}`}
            positions={edgeCoords}
            pathOptions={{ color, weight, dashArray, opacity: 0.8 }}
            eventHandlers={{
              click: () => onSelectRoad && onSelectRoad(road),
            }}
          >
            <Tooltip sticky>
              <div>
                <strong>Road Segment:</strong> {road.u} &harr; {road.v}<br />
                <strong>Distance:</strong> {road.distance_km} km<br />
                <strong>Status:</strong> <span style={{
                  color: road.status === "BLOCKED" ? "#ef4444" : (road.status === "DAMAGED" ? "#f97316" : "#22c55e"),
                  fontWeight: "bold"
                }}>{road.status}</span>
              </div>
            </Tooltip>
          </Polyline>
        );
      })}

      {/* Render Previous Planned Route (if rerouted) */}
      {previousRouteCoords && previousRouteCoords.length > 1 && (
        <Polyline
          positions={previousRouteCoords}
          pathOptions={{ color: "#94a3b8", weight: 4, dashArray: "5, 10", opacity: 0.6 }}
        />
      )}

      {/* Render Active Planned Route Polyline */}
      {activeRouteCoords && activeRouteCoords.length > 1 && (
        <Polyline
          positions={activeRouteCoords}
          pathOptions={{ color: "#2563eb", weight: 6, opacity: 0.95 }}
        />
      )}

      {/* Render Depots */}
      {depots.map((depot) => (
        <Marker key={`depot-${depot.id}`} position={[depot.lat, depot.lon]} icon={depotIcon}>
          <Popup>
            <div style={{ padding: "4px" }}>
              <h4 style={{ margin: "0 0 4px 0", color: "#1e293b" }}>{depot.name}</h4>
              <p style={{ margin: 0, fontSize: "0.85rem" }}>
                <strong>Relief Stock:</strong> {depot.available_supplies} units
              </p>
            </div>
          </Popup>
        </Marker>
      ))}

      {/* Render Affected Locations */}
      {locations.map((loc) => {
        const probPct = Math.round((loc.risk_probability || 0) * 100);
        const icon = getRiskIcon(loc.risk_level, probPct);
        return (
          <Marker key={`loc-${loc.id}`} position={[loc.lat, loc.lon]} icon={icon}>
            <Popup>
              <div style={{ padding: "4px", minWidth: "220px" }}>
                <h4 style={{ margin: "0 0 4px 0", color: "#0f172a" }}>{loc.name}</h4>
                <div style={{ fontSize: "0.8rem", color: "#334155", display: "grid", gap: "2px" }}>
                  <div><strong>Scenario-Based Risk:</strong> <span style={{
                    color: loc.risk_level === "HIGH" ? "#ef4444" : (loc.risk_level === "MEDIUM" ? "#f97316" : "#22c55e"),
                    fontWeight: "bold"
                  }}>{loc.risk_level} ({probPct}%)</span></div>
                  <div><strong>Remaining Demand:</strong> {loc.remaining_demand} / {loc.demand} units</div>
                  <div><strong>Urgency:</strong> P{loc.urgency} | <strong>Deadline:</strong> {loc.deadline} min</div>
                  <div><strong>Priority Score:</strong> {loc.priority_score}</div>
                  <div><strong>Status:</strong> {loc.status}</div>
                </div>
              </div>
            </Popup>
          </Marker>
        );
      })}

      {/* Render Vehicles */}
      {vehicles.map((v) => (
        <Marker key={`vehicle-${v.id}`} position={[v.lat, v.lon]} icon={vehicleIcon}>
          <Popup>
            <div style={{ padding: "4px" }}>
              <h4 style={{ margin: "0 0 4px 0", color: "#0f172a" }}>🚛 {v.id}</h4>
              <p style={{ margin: 0, fontSize: "0.85rem" }}>
                <strong>Cargo:</strong> {v.current_load} / {v.capacity} units<br />
                <strong>Clock:</strong> {v.current_time.toFixed(1)} min
              </p>
            </div>
          </Popup>
        </Marker>
      ))}
    </MapContainer>
  );
}
