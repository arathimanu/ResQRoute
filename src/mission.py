"""Adaptive disaster relief routing mission loop for ResQRoute.

Phase 4 implements:
  - Iterative dispatch loop executing greedy selection and delivery simulation.
  - Safe termination when vehicle supplies are exhausted or no feasible targets remain.
  - Dynamic road-update callback mechanism allowing road network topology/status
    to change adaptively between delivery steps.
  - Comprehensive mission summary tracking total deliveries, transit metrics, and service status.
"""

from dataclasses import dataclass, field
from typing import Callable, List, Optional

try:
    from src.graph import RoadGraph, RoadStatus
    from src.dijkstra import dijkstra, build_sample_disaster_network
    from src.models import Depot, Vehicle, AffectedLocation, RequestStatus
    from src.greedy import select_next_location, GreedyDecision, DEFAULT_AVERAGE_SPEED
    from src.simulation import simulate_delivery, DeliveryResult
except ImportError:
    from graph import RoadGraph, RoadStatus
    from dijkstra import dijkstra, build_sample_disaster_network
    from models import Depot, Vehicle, AffectedLocation, RequestStatus
    from greedy import select_next_location, GreedyDecision, DEFAULT_AVERAGE_SPEED
    from simulation import simulate_delivery, DeliveryResult


# Type alias for road update callback: receives (graph, step_number, vehicle, locations)
RoadUpdateCallback = Callable[[RoadGraph, int, Vehicle, List[AffectedLocation]], None]


@dataclass
class MissionSummary:
    """Comprehensive post-mission audit and performance report.

    Attributes:
        delivery_results: Step-by-step history of all executed deliveries.
        total_locations_served: Number of locations completely fulfilled (SERVED).
        total_locations_partially_served: Number of locations partially fulfilled (PARTIALLY_SERVED).
        total_supplies_delivered: Aggregate relief units delivered across all steps.
        total_distance_travelled: Total distance traversed by the vehicle (km).
        total_travel_time: Total transit duration (minutes/hours).
        final_vehicle_location: Final graph node where the vehicle stopped.
        final_vehicle_load: Remaining relief supplies onboard the vehicle.
        final_mission_time: Final clock timestamp on the mission clock.
    """
    delivery_results: List[DeliveryResult] = field(default_factory=list)
    total_locations_served: int = 0
    total_locations_partially_served: int = 0
    total_supplies_delivered: int = 0
    total_distance_travelled: float = 0.0
    total_travel_time: float = 0.0
    final_vehicle_location: str = ""
    final_vehicle_load: int = 0
    final_mission_time: float = 0.0


def run_mission(
    graph: RoadGraph,
    vehicle: Vehicle,
    locations: List[AffectedLocation],
    average_speed: float = DEFAULT_AVERAGE_SPEED,
    road_update_callback: Optional[RoadUpdateCallback] = None,
    use_effective_cost: bool = True,
    max_steps: int = 100,
) -> MissionSummary:
    """Execute an adaptive relief delivery mission for a single vehicle.

    Loop Workflow:
      1. While the vehicle has supplies and feasible targets remain:
         a. Greedily select the best reachable, feasible affected location.
         b. If no candidate is feasible, terminate the mission cleanly.
         c. Simulate movement, travel time, and relief delivery.
         d. Log the DeliveryResult.
         e. Trigger the road_update_callback (if provided) to simulate real-time road changes.
         f. Subsequent iterations adaptively use the modified graph topology.
      2. Compile and return a complete MissionSummary.

    Args:
        graph: RoadGraph network instance.
        vehicle: Vehicle instance carrying relief goods.
        locations: List of AffectedLocation instances.
        average_speed: Transit speed (default 1.0 km/min = 60 km/h).
        road_update_callback: Optional callback invoked between steps to inject road changes.
        use_effective_cost: If True, uses hazard penalties in Dijkstra routing.
        max_steps: Safeguard limit against infinite loops.

    Returns:
        MissionSummary: Aggregate performance and execution statistics.
    """
    delivery_results: List[DeliveryResult] = []
    step = 0

    while vehicle.current_load > 0 and step < max_steps:
        # 1. Greedy choice of the highest-priority feasible target
        decision = select_next_location(
            graph=graph,
            vehicle=vehicle,
            locations=locations,
            average_speed=average_speed,
            use_effective_cost=use_effective_cost,
        )

        # 2. Clean exit if no feasible targets are found
        if decision is None:
            break

        # 3. Execute delivery
        result = simulate_delivery(
            vehicle=vehicle,
            decision=decision,
            average_speed=average_speed,
        )
        delivery_results.append(result)

        # Stop if an unhandled delivery failure occurs
        if not result.success:
            break

        step += 1

        # 4. Adaptive road updates between delivery steps
        if road_update_callback is not None:
            road_update_callback(graph, step, vehicle, locations)

    # 5. Calculate mission summary metrics
    served_count = sum(1 for loc in locations if loc.status == RequestStatus.SERVED)
    partially_served_count = sum(1 for loc in locations if loc.status == RequestStatus.PARTIALLY_SERVED)
    total_delivered = sum(r.delivered_amount for r in delivery_results if r.success)
    total_dist = sum(r.distance for r in delivery_results if r.success)
    total_time = sum(r.travel_time for r in delivery_results if r.success)

    return MissionSummary(
        delivery_results=delivery_results,
        total_locations_served=served_count,
        total_locations_partially_served=partially_served_count,
        total_supplies_delivered=total_delivered,
        total_distance_travelled=round(total_dist, 2),
        total_travel_time=round(total_time, 2),
        final_vehicle_location=vehicle.current_location,
        final_vehicle_load=vehicle.current_load,
        final_mission_time=round(vehicle.current_time, 2),
    )


# =====================================================================
# Verification and Self-Test Scenarios
# =====================================================================
if __name__ == "__main__":
    print("====================================================================")
    print("   ResQRoute Phase 4: Adaptive Routing Mission Loop Demo            ")
    print("====================================================================\n")

    # 1. Initialize Network
    network = build_sample_disaster_network()

    # 2. Initialize Vehicle with 90 units
    truck = Vehicle(
        id="Truck-1",
        capacity=100,
        current_load=90,
        base_depot="Central Depot",
        current_location="Central Depot",
        current_time=0.0,
    )

    # 3. Initialize Disaster Locations
    hospital = AffectedLocation(
        id="Field Hospital",
        name="Field Hospital",
        demand=50,
        urgency=1,        # Critical
        deadline=60.0,
    )

    shelter = AffectedLocation(
        id="Shelter East",
        name="Shelter East",
        demand=40,
        urgency=2,        # High
        deadline=80.0,
    )

    community_c = AffectedLocation(
        id="Junction C",
        name="Camp Junction C",
        demand=30,
        urgency=3,        # Moderate
        deadline=100.0,
    )

    candidate_locations = [hospital, shelter, community_c]

    print("Initial Disaster State:")
    print(f"  Vehicle: {truck.id} at '{truck.current_location}' with {truck.current_load} units.")
    for loc in candidate_locations:
        print(f"  Target: '{loc.name}' | Demand: {loc.demand} | Urgency: {loc.urgency} | Deadline: {loc.deadline}m")
    print()

    # 4. Define an adaptive road-update callback
    # Between Step 1 and Step 2, a flash flood blocks the direct road between Field Hospital <-> Shelter East
    def disaster_event_callback(
        g: RoadGraph,
        step_num: int,
        veh: Vehicle,
        locs: List[AffectedLocation],
    ) -> None:
        if step_num == 1:
            print("\n  >>> [DISASTER EVENT ALERT] Flash flood reported! Road segment 'Field Hospital' <-> 'Shelter East' is now BLOCKED! <<<")
            g.set_road_status("Field Hospital", "Shelter East", RoadStatus.BLOCKED)

    # 5. Run the adaptive mission loop
    print("Starting Adaptive Mission Loop...\n")
    summary = run_mission(
        graph=network,
        vehicle=truck,
        locations=candidate_locations,
        average_speed=1.0,
        road_update_callback=disaster_event_callback,
    )

    # Print step-by-step results
    for i, res in enumerate(summary.delivery_results, start=1):
        print(f"[Step {i}] Delivery to '{res.location_id}':")
        print(f"  - Route:             {' -> '.join(res.route)}")
        print(f"  - Leg Distance:      {res.distance} km")
        print(f"  - Leg Travel Time:   {res.travel_time} min")
        print(f"  - Arrival Time:      {res.arrival_time} min")
        print(f"  - Delivered Units:   {res.delivered_amount} units")
        print(f"  - Remaining Load:    {res.remaining_vehicle_load} units")
        print(f"  - Target Status:     {res.location_status}")
        print()

    # Print overall summary
    print("====================================================================")
    print("   Final Mission Summary                                            ")
    print("=====================================================================")
    print(f"Total Completed Deliveries:        {len(summary.delivery_results)}")
    print(f"Fully Served Locations:            {summary.total_locations_served}")
    print(f"Partially Served Locations:        {summary.total_locations_partially_served}")
    print(f"Total Supplies Delivered:          {summary.total_supplies_delivered} units")
    print(f"Total Distance Travelled:          {summary.total_distance_travelled} km")
    print(f"Total Travel Time:                 {summary.total_travel_time} min")
    print(f"Final Vehicle Location:            {summary.final_vehicle_location}")
    print(f"Final Vehicle Load:                {summary.final_vehicle_load} units (Truck Empty)")
    print(f"Final Mission Clock:               {summary.final_mission_time} min")
    print("====================================================================\n")

    # Assertions for verification
    assert len(summary.delivery_results) == 2, "Expected exactly 2 delivery steps!"
    assert summary.total_supplies_delivered == 90, "Expected all 90 units to be delivered!"
    assert summary.final_vehicle_load == 0, "Expected vehicle to be completely empty!"
    assert hospital.status == RequestStatus.SERVED, "Field Hospital should be SERVED!"
    assert shelter.status == RequestStatus.SERVED, "Shelter East should be SERVED!"
    assert community_c.status == RequestStatus.UNSERVED, "Camp Junction C should remain UNSERVED (no load left)."

    # Verify that Step 2 detoured around the blocked road (Field Hospital <-> Shelter East)
    step_2_route = summary.delivery_results[1].route
    assert "Junction A" in step_2_route or "Junction C" in step_2_route, "Step 2 should detour around blocked direct link!"
    print("  [PASS] Adaptive detour verified: direct road was safely avoided in Step 2.")
    print("  [PASS] Vehicle supply exhaustion verified: truck stopped when load reached 0.")
    print("  [PASS] All Phase 4 Mission Loop tests passed successfully!\n")
