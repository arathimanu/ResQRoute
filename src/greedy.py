"""Greedy selection of affected locations for ResQRoute disaster relief.

DAA Theoretical Concepts:
  - Strategy: Greedy Choice Property with Multi-Criteria Scoring.
  - Evaluation Function:
        Priority = (remaining_demand * urgency_factor) / (shortest_distance + 1)
  - Feasibility Filters:
      1. Location is not already fully served (remaining_demand > 0, status != SERVED).
      2. Location can be reached in the road network via Dijkstra's algorithm.
      3. Location's demand does not exceed the vehicle's available load.
      4. Estimated arrival time satisfies the location's deadline.
  - Optimization Goal: Maximizes relief impact per unit of travel distance while
    respecting vehicle capacity, road network availability, and delivery deadlines.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

try:
    from src.graph import RoadGraph, RoadStatus
    from src.dijkstra import dijkstra, build_sample_disaster_network
    from src.models import Depot, Vehicle, AffectedLocation, RequestStatus
except ImportError:
    from graph import RoadGraph, RoadStatus
    from dijkstra import dijkstra, build_sample_disaster_network
    from models import Depot, Vehicle, AffectedLocation, RequestStatus


@dataclass
class GreedyDecision:
    """Encapsulates the greedy decision output for dispatching a vehicle.

    Attributes:
        location: The selected AffectedLocation object.
        path: Shortest road path from vehicle's current location to the target.
        distance: Physical road distance in km.
        estimated_arrival_time: Mission clock timestamp when the vehicle arrives.
        priority: Computed greedy priority score.
    """
    location: AffectedLocation
    path: List[str]
    distance: float
    estimated_arrival_time: float
    priority: float


def get_urgency_factor(urgency: int) -> float:
    """Map urgency levels to numerical weight multipliers.

    Lower integer values represent higher urgency in disaster relief:
      - Urgency 1 (Critical):  Factor 3.0
      - Urgency 2 (High):      Factor 2.0
      - Urgency 3 (Moderate):  Factor 1.0
      - Urgency >= 4:          1.0 / urgency
    """
    urgency_weights: Dict[int, float] = {
        1: 3.0,  # Critical
        2: 2.0,  # High
        3: 1.0,  # Moderate
    }
    return urgency_weights.get(urgency, max(0.25, 1.0 / max(1, urgency)))


# Assumed Travel-Speed Model:
# Default speed is 1.0 distance-unit per time-unit (e.g., 1.0 km/min = 60 km/h).
# When average_speed = 1.0, travel_time equals distance (1 km -> 1 minute of travel).
DEFAULT_AVERAGE_SPEED: float = 1.0


def select_next_location(
    graph: RoadGraph,
    vehicle: Vehicle,
    locations: List[AffectedLocation],
    average_speed: float = DEFAULT_AVERAGE_SPEED,
    use_effective_cost: bool = True,
) -> Optional[GreedyDecision]:
    """Select the highest-priority feasible affected location for a vehicle.

    Filtering Criteria:
      1. Already fully served (`status == RequestStatus.SERVED` or `remaining_demand <= 0`).
      2. Vehicle load constraint (`remaining_demand > vehicle.current_load`):
         The vehicle must have enough onboard cargo (`current_load`) to satisfy
         the location's unmet demand. Note: `current_load` represents relief goods
         available to deliver (distinct from `available_capacity`, which represents
         empty cargo space for picking up items).
      3. Destination unreachable in road graph (Dijkstra returns no path or infinite cost).
      4. Deadline violated (`estimated_arrival_time > deadline`).

    Travel-Speed Model:
      travel_time = distance / average_speed
      estimated_arrival_time = vehicle.current_time + travel_time
      (By default, average_speed = 1.0, so 1 km distance = 1 minute travel time).

    Greedy Metric:
      priority = (remaining_demand * urgency_factor) / (shortest_distance + 1.0)

    Args:
        graph: Current RoadGraph network (reflecting road damages and blockages).
        vehicle: The vehicle being dispatched.
        locations: List of disaster-affected candidate locations.
        average_speed: Speed in km per time unit (default 1.0 km/min = 60 km/h).
        use_effective_cost: If True, uses hazard penalties in Dijkstra when finding path.

    Returns:
        GreedyDecision if a feasible location exists, else None.
    """
    if vehicle.current_load <= 0:
        return None

    best_decision: Optional[GreedyDecision] = None
    best_priority: float = -1.0

    for loc in locations:
        # Filter 1: Check if already fully served or no remaining demand
        if loc.status == RequestStatus.SERVED or loc.remaining_demand <= 0:
            continue

        # Filter 2: Vehicle-load feasibility check
        # Ensures the vehicle has sufficient onboard supplies (current_load) to fulfill
        # the remaining demand. We check current_load (goods on board to deliver),
        # NOT available_capacity (which is unused space for loading goods at a depot).
        if loc.remaining_demand > vehicle.current_load:
            continue

        # Filter 3: Check reachability via Dijkstra's algorithm
        path, distance, _ = dijkstra(
            graph,
            start=vehicle.current_location,
            target=loc.id,
            use_effective_cost=use_effective_cost,
        )
        if path is None or distance == float("inf"):
            continue

        # Filter 4: Check delivery deadline using the travel-speed model
        # travel_time = distance / average_speed
        travel_time = distance / average_speed
        estimated_arrival = vehicle.current_time + travel_time
        if estimated_arrival > loc.deadline:
            continue

        # Greedy Priority Calculation
        urgency_factor = get_urgency_factor(loc.urgency)
        priority = (loc.remaining_demand * urgency_factor) / (distance + 1.0)

        # Greedy Selection: maximize priority score
        # Tie-breaker: higher priority, earlier deadline, shorter distance
        if priority > best_priority:
            best_priority = priority
            best_decision = GreedyDecision(
                location=loc,
                path=path,
                distance=distance,
                estimated_arrival_time=round(estimated_arrival, 2),
                priority=round(priority, 4),
            )

    return best_decision


# =====================================================================
# Verification and Self-Test Scenarios
# =====================================================================
if __name__ == "__main__":
    print("====================================================================")
    print("   ResQRoute Phase 2: Greedy Selection Self-Test Demo              ")
    print("====================================================================\n")

    # 1. Setup sample network topology
    network = build_sample_disaster_network()
    print("Road network initialized with 6 nodes (Central Depot, Junctions, Hospital, Shelter).")

    # 2. Setup Vehicle
    # Vehicle starts at Central Depot with 80 units of medical/food supplies
    truck = Vehicle(
        id="Truck-1",
        capacity=100,
        current_load=80,
        base_depot="Central Depot",
        current_location="Central Depot",
        current_time=0.0,
    )
    print(f"Vehicle: {truck.id} at '{truck.current_location}' | Load: {truck.current_load}/{truck.capacity} units\n")

    # 3. Setup Candidate Locations
    loc_hospital = AffectedLocation(
        id="Field Hospital",
        name="Field Hospital",
        demand=50,
        urgency=1,       # Critical (Factor = 3.0)
        deadline=60.0,   # Arrive within 60 mins
    )
    loc_shelter = AffectedLocation(
        id="Shelter East",
        name="Shelter East",
        demand=30,
        urgency=2,       # High (Factor = 2.0)
        deadline=50.0,   # Arrive within 50 mins
    )
    loc_served = AffectedLocation(
        id="Junction B",
        name="Relief Camp B",
        demand=20,
        urgency=1,
        deadline=30.0,
        delivered_amount=20,
        status=RequestStatus.SERVED,  # Should be filtered out
    )
    loc_heavy = AffectedLocation(
        id="Junction C",
        name="Community Center C",
        demand=95,       # 95 > truck.current_load (80) -> Should be filtered out
        urgency=1,
        deadline=40.0,
    )
    loc_tight_deadline = AffectedLocation(
        id="Shelter East",
        name="Remote Outpost",
        demand=10,
        urgency=1,
        deadline=5.0,    # Unreachable before 5.0 mins (min dist is 10km) -> Should be filtered out
    )

    all_locations = [loc_hospital, loc_shelter, loc_served, loc_heavy]

    # --- Test 1: Normal Greedy Selection ---
    print("[Test 1] Candidate Selection under Normal Conditions:")
    print(f"  - Candidate 1: {loc_hospital.name} (Demand={loc_hospital.demand}, Urgency={loc_hospital.urgency}, Deadline={loc_hospital.deadline}m)")
    print(f"  - Candidate 2: {loc_shelter.name} (Demand={loc_shelter.demand}, Urgency={loc_shelter.urgency}, Deadline={loc_shelter.deadline}m)")
    print(f"  - Candidate 3: {loc_served.name} (Status={loc_served.status} -> expect filtered)")
    print(f"  - Candidate 4: {loc_heavy.name} (Demand={loc_heavy.demand} > Load={truck.current_load} -> expect filtered)")

    decision = select_next_location(network, truck, all_locations, average_speed=1.0)
    assert decision is not None, "A feasible location should have been selected!"
    print("\n  -> Greedy Decision Result:")
    print(f"     Target Location:       {decision.location.name} ({decision.location.id})")
    print(f"     Planned Route:         {' -> '.join(decision.path)}")
    print(f"     Route Distance:        {decision.distance} km")
    print(f"     Est. Arrival Time:     {decision.estimated_arrival_time} min")
    print(f"     Computed Priority:     {decision.priority}")

    # Field Hospital: (50 * 3.0) / (10.0 + 1) = 150 / 11 ≈ 13.6364
    # Shelter East:   (30 * 2.0) / (10.0 + 1) = 60 / 11 ≈ 5.4545
    assert decision.location.id == "Field Hospital", "Field Hospital should be chosen due to higher priority score!"
    print("  [PASS] Test 1: Field Hospital correctly selected with highest priority score.\n")

    # --- Test 2: Road Blockage forces Rerouting and Score Recalculation ---
    print("[Test 2] Road Blockage Simulation: Bridge to Field Hospital BLOCKED...")
    network.set_road_status("Junction A", "Field Hospital", RoadStatus.BLOCKED)

    # Detour to Field Hospital: Central Depot -> Junction A -> Junction C -> Shelter East -> Field Hospital (13 km)
    # New Field Hospital priority: (50 * 3.0) / (13.0 + 1) = 150 / 14 ≈ 10.7143
    # Shelter East distance is 10 km (Central Depot -> Junction A -> Junction C -> Shelter East)
    # Shelter East priority: (30 * 2.0) / (10.0 + 1) = 60 / 11 ≈ 5.4545
    # Field Hospital is still higher priority (10.7143 > 5.4545) and arrival is 13.0 min <= 60.0 min
    decision_reroute = select_next_location(network, truck, all_locations, average_speed=1.0)
    assert decision_reroute is not None
    print(f"     Selected Target:       {decision_reroute.location.name}")
    print(f"     Detour Route:          {' -> '.join(decision_reroute.path)}")
    print(f"     Detour Distance:       {decision_reroute.distance} km")
    print(f"     Est. Arrival Time:     {decision_reroute.estimated_arrival_time} min")
    print(f"     Detour Priority:       {decision_reroute.priority}")
    assert "Junction C" in decision_reroute.path, "Route should detour through Junction C!"
    print("  [PASS] Test 2: Safely detoured around blocked road and recalculated priority.\n")

    # --- Test 3: Deadline Expiry Filtering ---
    print("[Test 3] Deadline Tightening: Field Hospital deadline reduced to 12.0 min (detour takes 13.0 min)...")
    loc_hospital.deadline = 12.0  # Arrival time (13.0) exceeds deadline (12.0)

    decision_fallback = select_next_location(network, truck, all_locations, average_speed=1.0)
    assert decision_fallback is not None
    print(f"     Selected Target:       {decision_fallback.location.name}")
    print(f"     Route:                 {' -> '.join(decision_fallback.path)}")
    print(f"     Est. Arrival Time:     {decision_fallback.estimated_arrival_time} min <= Deadline ({decision_fallback.location.deadline} min)")
    assert decision_fallback.location.id == "Shelter East", "Should fall back to Shelter East when Field Hospital misses deadline!"
    print("  [PASS] Test 3: Unfeasible deadline correctly filtered, fell back to next viable target.\n")

    # --- Test 4: No Feasible Locations ---
    print("[Test 4] Exhaustion Case: Vehicle has 0 load remaining...")
    empty_truck = Vehicle(id="Empty-Truck", capacity=100, current_load=0, current_location="Central Depot")
    decision_none = select_next_location(network, empty_truck, all_locations)
    assert decision_none is None, "Should return None when vehicle has no load!"
    print("     Result: None")
    print("  [PASS] Test 4: Correctly returned None when no candidate is feasible.\n")

    print("====================================================================")
    print("   All Phase 2 Greedy Selection tests passed successfully!         ")
    print("====================================================================\n")
