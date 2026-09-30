"""ResQRoute — Disaster Response Decision Support and Adaptive Routing System API.

FastAPI Backend exposing decision-support, risk estimation, and disaster-aware routing endpoints.
Wraps the existing src/ algorithm modules (graph.py, dijkstra.py, greedy.py, simulation.py, mission.py).
"""

from typing import Dict, List, Optional, Any
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config import SYSTEM_TITLE, DAMAGED_PENALTY, DEFAULT_SPEED_KMMIN
from src.graph import RoadStatus
from src.dijkstra import dijkstra
from src.greedy import select_next_location, get_urgency_factor, GreedyDecision
from src.simulation import simulate_delivery
from backend.state import AppState

app = FastAPI(
    title=SYSTEM_TITLE,
    description="Offline-first disaster response decision support and adaptive routing system API.",
    version="2.0.0",
)

# Enable CORS for React frontend (Vite default dev server is http://localhost:5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request Pydantic Schemas ───────────────────────────────────────────────────
class RouteRequest(BaseModel):
    start_node: str
    target_node: str
    use_effective_cost: bool = True


class RoadConditionRequest(BaseModel):
    u: str
    v: str
    status: str  # CLEAR, DAMAGED, BLOCKED


# ── Helper Functions ───────────────────────────────────────────────────────────
def calculate_location_priority_score(loc, start_node: str, state: AppState) -> float:
    """Calculate extended priority score taking risk factor into account.
    
    Priority Formula:
      priority = (remaining_demand * urgency_factor * risk_factor) / (distance + 1)
      where risk_factor = 1.0 + risk_probability
    """
    if loc.status == "SERVED" or loc.remaining_demand <= 0:
        return 0.0

    path, dist, _ = dijkstra(state.graph, start_node, loc.id, use_effective_cost=True)
    if path is None or dist == float("inf"):
        return 0.0

    urgency_factor = get_urgency_factor(loc.urgency)
    risk_factor = 1.0 + loc.risk_probability
    priority = (loc.remaining_demand * urgency_factor * risk_factor) / (dist + 1.0)
    return round(priority, 4)


def get_route_coordinates(path: List[str], state: AppState) -> List[List[float]]:
    """Extract lat/lon polyline coordinates following actual OSM road geometry."""
    coords: List[List[float]] = []
    if not path or len(path) < 1:
        return coords

    for i in range(len(path) - 1):
        u, v = path[i], path[i + 1]
        edge = state.graph.get_edge(u, v)
        if edge and "geometry" in edge and edge["geometry"]:
            edge_coords = edge["geometry"]
            # Avoid duplicate vertex where segments connect
            if coords and edge_coords and coords[-1] == edge_coords[0]:
                coords.extend(edge_coords[1:])
            else:
                coords.extend(edge_coords)
        else:
            # Fallback to straight line between node coordinates
            u_pos = state.node_positions.get(u)
            v_pos = state.node_positions.get(v)
            if u_pos and v_pos:
                if not coords or coords[-1] != [u_pos["lat"], u_pos["lon"]]:
                    coords.append([u_pos["lat"], u_pos["lon"]])
                coords.append([v_pos["lat"], v_pos["lon"]])

    # If single node path
    if not coords and len(path) == 1:
        p = state.node_positions.get(path[0])
        if p:
            coords.append([p["lat"], p["lon"]])

    return coords


# ── API Endpoints ──────────────────────────────────────────────────────────────

@app.get("/api/scenario")
def get_scenario():
    """Return active disaster scenario details, transparent risk weights, and disclaimer."""
    state = AppState.get_instance()
    return {
        "scenario": state.scenario,
        "damaged_road_penalty": DAMAGED_PENALTY,
        "default_speed_kmh": 30.0,
    }


@app.get("/api/locations")
def get_locations():
    """Return all affected locations with risk breakdown, demand, urgency, and computed priority."""
    state = AppState.get_instance()
    start_node = state.vehicles[0].current_location if state.vehicles else "ripon_building"

    result = []
    for loc in state.locations:
        priority_score = calculate_location_priority_score(loc, start_node, state)
        loc_dict = {
            "id": loc.id,
            "name": loc.name,
            "demand": loc.demand,
            "remaining_demand": loc.remaining_demand,
            "urgency": loc.urgency,
            "deadline": loc.deadline,
            "delivered_amount": loc.delivered_amount,
            "status": loc.status,
            "lat": loc.lat,
            "lon": loc.lon,
            "population_served": loc.population_served,
            "vulnerability_score": loc.vulnerability_score,
            "risk_probability": loc.risk_probability,
            "risk_level": loc.risk_level,
            "priority_score": priority_score,
            "risk_breakdown": loc.risk_breakdown,
        }
        result.append(loc_dict)

    # Sort locations by priority score descending
    result.sort(key=lambda x: x["priority_score"], reverse=True)
    return result


@app.get("/api/depots")
def get_depots():
    """Return relief supply depots list."""
    state = AppState.get_instance()
    return [
        {
            "id": d.id,
            "name": d.name,
            "available_supplies": d.available_supplies,
            "lat": d.lat,
            "lon": d.lon,
        }
        for d in state.depots
    ]


@app.get("/api/vehicles")
def get_vehicles():
    """Return relief vehicles status list."""
    state = AppState.get_instance()
    return [
        {
            "id": v.id,
            "capacity": v.capacity,
            "current_load": v.current_load,
            "base_depot": v.base_depot,
            "current_location": v.current_location,
            "current_time": v.current_time,
            "lat": v.lat,
            "lon": v.lon,
        }
        for v in state.vehicles
    ]


@app.get("/api/roads")
def get_roads():
    """Return all unique road segments with distance, status, and OSM geometry."""
    state = AppState.get_instance()
    seen = set()
    edges_out = []

    for u in state.graph.adj:
        for v, attrs in state.graph.adj[u].items():
            pair = tuple(sorted([u, v]))
            if pair not in seen:
                seen.add(pair)
                u_pos = state.node_positions.get(u, {})
                v_pos = state.node_positions.get(v, {})
                edges_out.append({
                    "u": u,
                    "v": v,
                    "distance_km": attrs["distance"],
                    "status": attrs["status"],
                    "name": attrs.get("name", ""),
                    "geometry": attrs.get("geometry", []),
                    "u_coords": [u_pos.get("lat"), u_pos.get("lon")],
                    "v_coords": [v_pos.get("lat"), v_pos.get("lon")],
                })
    return edges_out


@app.post("/api/route")
def compute_route(req: RouteRequest):
    """Compute optimal disaster-aware route using Dijkstra's algorithm on the real road network."""
    state = AppState.get_instance()
    if req.start_node not in state.graph.nodes():
        raise HTTPException(status_code=400, detail=f"Start node '{req.start_node}' not found in graph.")
    if req.target_node not in state.graph.nodes():
        raise HTTPException(status_code=400, detail=f"Target node '{req.target_node}' not found in graph.")

    path, dist, cost = dijkstra(
        graph=state.graph,
        start=req.start_node,
        target=req.target_node,
        use_effective_cost=req.use_effective_cost,
        damaged_penalty=DAMAGED_PENALTY,
    )

    if path is None:
        return {
            "success": False,
            "message": f"Target location '{req.target_node}' is unreachable under current road conditions.",
            "path": None,
            "distance_km": float("inf"),
            "effective_cost": float("inf"),
            "estimated_travel_time_min": float("inf"),
            "geometry": [],
        }

    # travel_time = distance / speed
    travel_time_min = round(dist / DEFAULT_SPEED_KMMIN, 1)
    geometry = get_route_coordinates(path, state)

    state.active_route = path
    state.previous_route = list(path)

    return {
        "success": True,
        "start_node": req.start_node,
        "target_node": req.target_node,
        "path": path,
        "distance_km": dist,
        "effective_cost": cost,
        "estimated_travel_time_min": travel_time_min,
        "geometry": geometry,
    }


@app.post("/api/road-condition")
def update_road_condition(req: RoadConditionRequest):
    """Update a road segment status (CLEAR/DAMAGED/BLOCKED) and evaluate rerouting impact."""
    if req.status not in RoadStatus.VALID_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid status '{req.status}'. Must be CLEAR, DAMAGED, or BLOCKED.")

    state = AppState.get_instance()
    if req.u not in state.graph.adj or req.v not in state.graph.adj[req.u]:
        raise HTTPException(status_code=400, detail=f"Road segment between '{req.u}' and '{req.v}' does not exist.")

    # Record previous route to target location if active
    vehicle = state.vehicles[0] if state.vehicles else None
    target_loc_id = state.locations[0].id if state.locations else None

    old_path = None
    old_dist = 0.0
    if vehicle and target_loc_id:
        prev_decision = select_next_location(state.graph, vehicle, state.locations, average_speed=DEFAULT_SPEED_KMMIN)
        if prev_decision:
            old_path = prev_decision.path
            old_dist = prev_decision.distance

    # Update road status bidirectionally
    state.graph.set_road_status(req.u, req.v, req.status, bidirectional=True)

    # Calculate new route after status update
    new_path = None
    new_dist = 0.0
    new_decision = None
    if vehicle and state.locations:
        new_decision = select_next_location(state.graph, vehicle, state.locations, average_speed=DEFAULT_SPEED_KMMIN)
        if new_decision:
            new_path = new_decision.path
            new_dist = new_decision.distance

    rerouted = False
    if old_path and new_path:
        rerouted = (old_path != new_path)
    elif old_path and not new_path:
        rerouted = True

    if rerouted:
        state.reroute_count += 1
    if new_path:
        state.active_route = new_path

    new_geometry = get_route_coordinates(new_path, state) if new_path else []
    old_geometry = get_route_coordinates(old_path, state) if old_path else []

    return {
        "success": True,
        "updated_road": {"u": req.u, "v": req.v, "new_status": req.status},
        "rerouted": rerouted,
        "reroute_count": state.reroute_count,
        "previous_route": {
            "path": old_path,
            "distance_km": old_dist,
            "geometry": old_geometry,
        },
        "updated_route": {
            "path": new_path,
            "distance_km": new_dist,
            "geometry": new_geometry,
        },
        "message": (
            f"Road segment '{req.u}' <-> '{req.v}' updated to {req.status}. "
            f"{'Rerouted via alternative detour!' if rerouted else 'Route remains unchanged.'}"
        ),
    }


@app.post("/api/mission/step")
def execute_mission_step():
    """Execute next greedy delivery step using vehicle movement and delivery simulation."""
    state = AppState.get_instance()
    if not state.vehicles:
        raise HTTPException(status_code=400, detail="No vehicle available.")

    vehicle = state.vehicles[0]
    if vehicle.current_load <= 0:
        return {
            "success": False,
            "message": "Vehicle has 0 supplies remaining. Mission finished.",
        }

    decision: Optional[GreedyDecision] = select_next_location(
        graph=state.graph,
        vehicle=vehicle,
        locations=state.locations,
        average_speed=DEFAULT_SPEED_KMMIN,
        use_effective_cost=True,
    )

    if decision is None:
        return {
            "success": False,
            "message": "No feasible target location found under current road conditions and constraints.",
        }

    result = simulate_delivery(vehicle=vehicle, decision=decision, average_speed=DEFAULT_SPEED_KMMIN)
    state.delivery_history.append(result)
    state.active_route = decision.path

    # Update vehicle lat/lon to target location lat/lon
    target_loc = next((loc for loc in state.locations if loc.id == decision.location.id), None)
    if target_loc:
        vehicle.lat = target_loc.lat
        vehicle.lon = target_loc.lon

    return {
        "success": result.success,
        "vehicle_id": result.vehicle_id,
        "location_id": result.location_id,
        "route": result.route,
        "distance_km": result.distance,
        "travel_time_min": result.travel_time,
        "arrival_time_min": result.arrival_time,
        "delivered_amount": result.delivered_amount,
        "remaining_vehicle_load": result.remaining_vehicle_load,
        "location_status": result.location_status,
        "message": result.message,
        "geometry": get_route_coordinates(result.route, state),
    }


@app.post("/api/mission/reset")
def reset_mission():
    """Reset scenario, vehicle positions, locations, and road statuses to initial state."""
    state = AppState.get_instance()
    state.reset()
    return {"success": True, "message": "Disaster scenario and road network state reset to initial conditions."}


@app.get("/api/missions")
def get_mission_history():
    """Return delivery history log and mission summary statistics."""
    state = AppState.get_instance()
    history = [
        {
            "vehicle_id": r.vehicle_id,
            "location_id": r.location_id,
            "route": r.route,
            "distance_km": r.distance,
            "travel_time_min": r.travel_time,
            "arrival_time_min": r.arrival_time,
            "delivered_amount": r.delivered_amount,
            "remaining_vehicle_load": r.remaining_vehicle_load,
            "location_status": r.location_status,
            "message": r.message,
        }
        for r in state.delivery_history
    ]

    served_count = sum(1 for loc in state.locations if loc.status == "SERVED")
    partially_count = sum(1 for loc in state.locations if loc.status == "PARTIALLY_SERVED")
    total_delivered = sum(r.delivered_amount for r in state.delivery_history if r.success)
    total_dist = sum(r.distance for r in state.delivery_history if r.success)
    total_time = sum(r.travel_time for r in state.delivery_history if r.success)

    return {
        "history": history,
        "summary": {
            "total_locations": len(state.locations),
            "fully_served": served_count,
            "partially_served": partially_count,
            "total_delivered_units": total_delivered,
            "total_distance_km": round(total_dist, 2),
            "total_travel_time_min": round(total_time, 2),
            "reroutes_triggered": state.reroute_count,
        },
    }
