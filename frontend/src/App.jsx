import React, { useState, useEffect } from "react";
import Navbar from "./components/Navbar";
import Dashboard from "./pages/Dashboard";
import Locations from "./pages/Locations";
import RoutePlanner from "./pages/RoutePlanner";
import Missions from "./pages/Missions";
import {
  fetchScenario,
  fetchLocations,
  fetchDepots,
  fetchVehicles,
  fetchRoads,
  fetchMissionHistory,
  resetMission,
} from "./api";

export default function App() {
  const [activeTab, setActiveTab] = useState("dashboard");
  const [loading, setLoading] = useState(true);
  const [resetting, setResetting] = useState(false);
  const [error, setError] = useState(null);

  // State data
  const [scenario, setScenario] = useState(null);
  const [locations, setLocations] = useState([]);
  const [depots, setDepots] = useState([]);
  const [vehicles, setVehicles] = useState([]);
  const [roads, setRoads] = useState([]);
  const [missionData, setMissionData] = useState(null);
  const [activeRouteCoords, setActiveRouteCoords] = useState([]);

  // Load state from FastAPI backend
  const loadAllData = async () => {
    try {
      const [sc, locs, dps, vehs, rds, mss] = await Promise.all([
        fetchScenario(),
        fetchLocations(),
        fetchDepots(),
        fetchVehicles(),
        fetchRoads(),
        fetchMissionHistory(),
      ]);

      setScenario(sc);
      setLocations(locs);
      setDepots(dps);
      setVehicles(vehs);
      setRoads(rds);
      setMissionData(mss);
      setError(null);
    } catch (err) {
      console.error("Backend fetch error:", err);
      setError("Cannot connect to FastAPI backend at http://localhost:8000. Please ensure the backend server is running.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAllData();
  }, []);

  const handleReset = async () => {
    setResetting(true);
    try {
      await resetMission();
      setActiveRouteCoords([]);
      await loadAllData();
    } catch (err) {
      alert("Failed to reset scenario: " + err.message);
    } finally {
      setResetting(false);
    }
  };

  if (loading) {
    return (
      <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100vh", fontFamily: "sans-serif", background: "#f8fafc" }}>
        <div style={{ textAlign: "center" }}>
          <h2 style={{ color: "#1e293b" }}>🚑 Loading ResQRoute System...</h2>
          <p style={{ color: "#64748b" }}>Connecting to backend & loading OpenStreetMap Chennai road graph...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ padding: "2rem", maxWidth: "600px", margin: "4rem auto", fontFamily: "sans-serif" }}>
        <div style={{ background: "#fef2f2", border: "1px solid #fca5a5", borderRadius: "10px", padding: "1.5rem" }}>
          <h3 style={{ color: "#991b1b", margin: "0 0 0.5rem 0" }}>⚠️ Backend Server Disconnected</h3>
          <p style={{ color: "#7f1d1d", fontSize: "0.9rem", margin: "0 0 1rem 0" }}>{error}</p>
          <button
            onClick={() => { setLoading(true); loadAllData(); }}
            style={{ padding: "0.5rem 1rem", background: "#ef4444", color: "#fff", border: "none", borderRadius: "6px", cursor: "pointer", fontWeight: "600" }}
          >
            Retry Connection
          </button>
        </div>
      </div>
    );
  }

  return (
    <div style={{ fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, sans-serif", background: "#f8fafc", minHeight: "100vh" }}>
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        onReset={handleReset}
        resetting={resetting}
      />

      <main>
        {activeTab === "dashboard" && (
          <Dashboard
            scenario={scenario}
            locations={locations}
            depots={depots}
            vehicles={vehicles}
            roads={roads}
            activeRouteCoords={activeRouteCoords}
            onSelectRoad={(road) => {
              setActiveTab("planner");
            }}
          />
        )}

        {activeTab === "locations" && (
          <Locations
            locations={locations}
            scenario={scenario}
          />
        )}

        {activeTab === "planner" && (
          <RoutePlanner
            depots={depots}
            locations={locations}
            vehicles={vehicles}
            roads={roads}
            activeRouteCoords={activeRouteCoords}
            setActiveRouteCoords={setActiveRouteCoords}
            onRefreshData={loadAllData}
          />
        )}

        {activeTab === "missions" && (
          <Missions
            vehicles={vehicles}
            locations={locations}
            missionData={missionData}
            onRefreshData={loadAllData}
            setActiveRouteCoords={setActiveRouteCoords}
          />
        )}
      </main>
    </div>
  );
}
