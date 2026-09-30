import React, { useState } from "react";
import { Info, AlertTriangle, ShieldCheck, ChevronDown, ChevronUp } from "lucide-react";

export default function Locations({ locations = [], scenario }) {
  const [expandedId, setExpandedId] = useState(null);

  const weights = scenario?.scenario?.risk_weights || {
    hazard_exposure: 0.40,
    disaster_severity: 0.25,
    population_factor: 0.20,
    vulnerability_score: 0.15,
  };

  const toggleExpand = (id) => {
    setExpandedId(expandedId === id ? null : id);
  };

  return (
    <div style={{ padding: "1.5rem", maxWidth: "1280px", margin: "0 auto" }}>
      {/* Page Header */}
      <div style={{ marginBottom: "1.25rem" }}>
        <h2 style={{ margin: 0, fontSize: "1.4rem", color: "#0f172a", fontWeight: "700" }}>
          Disaster Affected Locations & Risk Assessment
        </h2>
        <p style={{ margin: "4px 0 0 0", fontSize: "0.875rem", color: "#64748b" }}>
          Locations prioritized using transparent <strong>Scenario-Based Risk Estimates</strong>, urgency, and remaining demand.
        </p>
      </div>

      {/* Transparent Risk Formula Explanation Card */}
      <div style={{
        background: "#f8fafc",
        border: "1px solid #cbd5e1",
        borderRadius: "10px",
        padding: "1rem 1.25rem",
        marginBottom: "1.5rem",
        fontSize: "0.85rem",
        color: "#334155"
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", fontWeight: "700", color: "#1e293b", marginBottom: "0.4rem" }}>
          <Info size={18} color="#2563eb" />
          Transparent Risk Probability Calculation Model (Scenario-Based Risk Estimate)
        </div>
        <p style={{ margin: "0 0 0.5rem 0" }}>
          Risk probabilities are calculated transparently using a weighted combination of geographic exposure, disaster severity, population density, and facility vulnerability:
        </p>
        <div style={{
          background: "#ffffff",
          padding: "0.6rem 0.85rem",
          borderRadius: "6px",
          fontFamily: "monospace",
          fontSize: "0.8rem",
          border: "1px solid #e2e8f0",
          color: "#0f172a"
        }}>
          Risk Probability = ({weights.hazard_exposure} × Hazard Exposure) + ({weights.disaster_severity} × Disaster Severity) + ({weights.population_factor} × Population Factor) + ({weights.vulnerability_score} × Vulnerability)
        </div>
        <div style={{ marginTop: "0.5rem", fontSize: "0.775rem", color: "#64748b" }}>
          Note: This score is a simulation parameter for disaster decision support, NOT a real-time ML prediction.
        </div>
      </div>

      {/* Locations Table */}
      <div style={{
        background: "#ffffff",
        borderRadius: "10px",
        border: "1px solid #e2e8f0",
        boxShadow: "0 1px 4px rgba(0,0,0,0.05)",
        overflow: "hidden"
      }}>
        <table style={{ width: "100%", borderCollapse: "collapse", textAlign: "left", fontSize: "0.875rem" }}>
          <thead>
            <tr style={{ background: "#f1f5f9", color: "#475569", textTransform: "uppercase", fontSize: "0.75rem", letterSpacing: "0.03em" }}>
              <th style={thStyle}>Location Name</th>
              <th style={thStyle}>Population</th>
              <th style={thStyle}>Affect Probability</th>
              <th style={thStyle}>Risk Level</th>
              <th style={thStyle}>Demand</th>
              <th style={thStyle}>Urgency</th>
              <th style={thStyle}>Priority Score</th>
              <th style={thStyle}>Status</th>
              <th style={thStyle}>Math Breakdown</th>
            </tr>
          </thead>
          <tbody>
            {locations.map((loc) => {
              const isExpanded = expandedId === loc.id;
              const probPct = Math.round((loc.risk_probability || 0) * 100);
              const breakdown = loc.risk_breakdown || {};

              return (
                <React.Fragment key={loc.id}>
                  <tr style={{ borderBottom: "1px solid #e2e8f0", background: isExpanded ? "#f8fafc" : "#ffffff" }}>
                    <td style={{ ...tdStyle, fontWeight: "600", color: "#0f172a" }}>
                      {loc.name}
                    </td>
                    <td style={tdStyle}>{loc.population_served.toLocaleString()}</td>
                    <td style={{ ...tdStyle, fontWeight: "700" }}>{probPct}%</td>
                    <td style={tdStyle}>
                      <span style={{
                        padding: "3px 8px",
                        borderRadius: "12px",
                        fontSize: "0.75rem",
                        fontWeight: "700",
                        background: loc.risk_level === "HIGH" ? "#fef2f2" : (loc.risk_level === "MEDIUM" ? "#fff7ed" : "#f0fdf4"),
                        color: loc.risk_level === "HIGH" ? "#dc2626" : (loc.risk_level === "MEDIUM" ? "#c2410c" : "#15803d"),
                        border: `1px solid ${loc.risk_level === "HIGH" ? "#fca5a5" : (loc.risk_level === "MEDIUM" ? "#ffedd5" : "#bbf7d0")}`
                      }}>
                        {loc.risk_level}
                      </span>
                    </td>
                    <td style={tdStyle}>
                      {loc.remaining_demand} <span style={{ color: "#94a3b8" }}>/ {loc.demand} units</span>
                    </td>
                    <td style={tdStyle}>
                      <span style={{ fontWeight: "600" }}>P{loc.urgency}</span> <span style={{ fontSize: "0.75rem", color: "#64748b" }}>({loc.deadline}m)</span>
                    </td>
                    <td style={{ ...tdStyle, fontWeight: "700", color: "#2563eb" }}>
                      {loc.priority_score}
                    </td>
                    <td style={tdStyle}>
                      <span style={{
                        padding: "3px 8px",
                        borderRadius: "6px",
                        fontSize: "0.75rem",
                        fontWeight: "600",
                        background: loc.status === "SERVED" ? "#dcfce7" : (loc.status === "PARTIALLY_SERVED" ? "#fef3c7" : "#fee2e2"),
                        color: loc.status === "SERVED" ? "#166534" : (loc.status === "PARTIALLY_SERVED" ? "#92400e" : "#991b1b")
                      }}>
                        {loc.status}
                      </span>
                    </td>
                    <td style={tdStyle}>
                      <button
                        onClick={() => toggleExpand(loc.id)}
                        style={{
                          background: "none",
                          border: "1px solid #cbd5e1",
                          borderRadius: "6px",
                          padding: "2px 8px",
                          cursor: "pointer",
                          display: "flex",
                          alignItems: "center",
                          gap: "4px",
                          fontSize: "0.75rem",
                          color: "#475569"
                        }}
                      >
                        {isExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                        {isExpanded ? "Hide" : "Factors"}
                      </button>
                    </td>
                  </tr>

                  {/* Expandable Factor Breakdown Row */}
                  {isExpanded && (
                    <tr style={{ background: "#f8fafc", borderBottom: "1px solid #e2e8f0" }}>
                      <td colSpan={9} style={{ padding: "1rem 1.25rem" }}>
                        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "1rem", fontSize: "0.8rem" }}>
                          <div style={breakdownBox}>
                            <div style={breakdownLabel}>1. Hazard Exposure ({weights.hazard_exposure * 100}%)</div>
                            <div style={breakdownValue}>{breakdown.hazard_exposure} (dist: {breakdown.distance_to_hazard_km} km)</div>
                            <div style={breakdownContrib}>Contribution: +{breakdown.hazard_exposure_weighted}</div>
                          </div>

                          <div style={breakdownBox}>
                            <div style={breakdownLabel}>2. Disaster Severity ({weights.disaster_severity * 100}%)</div>
                            <div style={breakdownValue}>{breakdown.disaster_severity} (Scenario)</div>
                            <div style={breakdownContrib}>Contribution: +{breakdown.disaster_severity_weighted}</div>
                          </div>

                          <div style={breakdownBox}>
                            <div style={breakdownLabel}>3. Population Factor ({weights.population_factor * 100}%)</div>
                            <div style={breakdownValue}>{breakdown.population_factor} ({loc.population_served} pop)</div>
                            <div style={breakdownContrib}>Contribution: +{breakdown.population_factor_weighted}</div>
                          </div>

                          <div style={breakdownBox}>
                            <div style={breakdownLabel}>4. Vulnerability Score ({weights.vulnerability_score * 100}%)</div>
                            <div style={breakdownValue}>{breakdown.vulnerability_score} (Facility)</div>
                            <div style={breakdownContrib}>Contribution: +{breakdown.vulnerability_score_weighted}</div>
                          </div>
                        </div>

                        <div style={{ marginTop: "0.75rem", fontSize: "0.8rem", color: "#334155", fontWeight: "600" }}>
                          Total Sum = {breakdown.raw_score} &rarr; Scenario Risk Estimate = {probPct}% ({loc.risk_level})
                        </div>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

const thStyle = {
  padding: "0.75rem 1rem",
  fontWeight: "700",
  borderBottom: "2px solid #cbd5e1",
};

const tdStyle = {
  padding: "0.75rem 1rem",
  color: "#334155",
};

const breakdownBox = {
  background: "#ffffff",
  padding: "0.6rem 0.8rem",
  borderRadius: "6px",
  border: "1px solid #e2e8f0",
};

const breakdownLabel = {
  fontSize: "0.7rem",
  color: "#64748b",
  fontWeight: "700",
  textTransform: "uppercase",
};

const breakdownValue = {
  fontSize: "0.85rem",
  fontWeight: "600",
  color: "#0f172a",
  margin: "2px 0",
};

const breakdownContrib = {
  fontSize: "0.75rem",
  color: "#2563eb",
  fontWeight: "700",
};
