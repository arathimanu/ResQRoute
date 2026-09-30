import React from "react";
import { Navigation, MapPin, Route, ShieldAlert, RotateCcw } from "lucide-react";

export default function Navbar({ activeTab, setActiveTab, onReset, resetting }) {
  const tabs = [
    { id: "dashboard", label: "Dashboard", icon: Navigation },
    { id: "locations", label: "Affected Locations & Risk", icon: MapPin },
    { id: "planner", label: "Route Planner & Hazards", icon: Route },
    { id: "missions", label: "Mission Execution", icon: ShieldAlert },
  ];

  return (
    <header style={{
      background: "linear-gradient(135deg, #1e293b 0%, #0f172a 100%)",
      color: "#ffffff",
      padding: "0.85rem 1.5rem",
      display: "flex",
      alignItems: "center",
      justifyContent: "space-between",
      borderBottom: "1px solid #334155",
      boxShadow: "0 4px 12px rgba(0,0,0,0.15)"
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: "0.85rem" }}>
        <div style={{
          background: "#ef4444",
          width: "38px",
          height: "38px",
          borderRadius: "10px",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: "1.25rem",
          fontWeight: "bold",
          boxShadow: "0 2px 8px rgba(239,68,68,0.4)"
        }}>
          🚑
        </div>
        <div>
          <h1 style={{ margin: 0, fontSize: "1.25rem", fontWeight: "700", letterSpacing: "-0.02em" }}>
            ResQRoute
          </h1>
          <p style={{ margin: 0, fontSize: "0.75rem", color: "#94a3b8" }}>
            Disaster Response Decision Support & Adaptive Routing System
          </p>
        </div>
      </div>

      <nav style={{ display: "flex", gap: "0.5rem" }}>
        {tabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "0.45rem",
                padding: "0.5rem 0.9rem",
                borderRadius: "8px",
                border: "none",
                background: isActive ? "#3b82f6" : "transparent",
                color: isActive ? "#ffffff" : "#cbd5e1",
                fontSize: "0.85rem",
                fontWeight: isActive ? "600" : "500",
                cursor: "pointer",
                transition: "all 0.15s ease"
              }}
            >
              <Icon size={16} />
              {tab.label}
            </button>
          );
        })}
      </nav>

      <button
        onClick={onReset}
        disabled={resetting}
        style={{
          display: "flex",
          alignItems: "center",
          gap: "0.45rem",
          padding: "0.5rem 0.9rem",
          borderRadius: "8px",
          border: "1px solid #475569",
          background: "#1e293b",
          color: "#f8fafc",
          fontSize: "0.825rem",
          fontWeight: "500",
          cursor: resetting ? "not-allowed" : "pointer",
          opacity: resetting ? 0.6 : 1
        }}
        title="Reset scenario state"
      >
        <RotateCcw size={15} />
        {resetting ? "Resetting..." : "Reset Scenario"}
      </button>
    </header>
  );
}
