const API_BASE = "http://localhost:8000/api";

export async function fetchScenario() {
  const res = await fetch(`${API_BASE}/scenario`);
  if (!res.ok) throw new Error("Failed to fetch scenario details");
  return res.json();
}

export async function fetchLocations() {
  const res = await fetch(`${API_BASE}/locations`);
  if (!res.ok) throw new Error("Failed to fetch locations");
  return res.json();
}

export async function fetchDepots() {
  const res = await fetch(`${API_BASE}/depots`);
  if (!res.ok) throw new Error("Failed to fetch depots");
  return res.json();
}

export async function fetchVehicles() {
  const res = await fetch(`${API_BASE}/vehicles`);
  if (!res.ok) throw new Error("Failed to fetch vehicles");
  return res.json();
}

export async function fetchRoads() {
  const res = await fetch(`${API_BASE}/roads`);
  if (!res.ok) throw new Error("Failed to fetch roads");
  return res.json();
}

export async function computeRoute(startNode, targetNode, useEffectiveCost = true) {
  const res = await fetch(`${API_BASE}/route`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      start_node: startNode,
      target_node: targetNode,
      use_effective_cost: useEffectiveCost,
    }),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Failed to compute route");
  }
  return res.json();
}

export async function updateRoadCondition(u, v, status) {
  const res = await fetch(`${API_BASE}/road-condition`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ u, v, status }),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Failed to update road condition");
  }
  return res.json();
}

export async function executeMissionStep() {
  const res = await fetch(`${API_BASE}/mission/step`, {
    method: "POST",
  });
  if (!res.ok) throw new Error("Failed to execute mission step");
  return res.json();
}

export async function resetMission() {
  const res = await fetch(`${API_BASE}/mission/reset`, {
    method: "POST",
  });
  if (!res.ok) throw new Error("Failed to reset mission");
  return res.json();
}

export async function fetchMissionHistory() {
  const res = await fetch(`${API_BASE}/missions`);
  if (!res.ok) throw new Error("Failed to fetch mission history");
  return res.json();
}
