"""Vehicle movement and relief delivery simulation for ResQRoute.

Phase 3 implements:
  - Movement of a vehicle along a planned shortest path.
  - Tracking of vehicle clock (current_time) and position (current_location).
  - Material drop-off at affected disaster sites (full and partial deliveries).
  - Safe validation against already served locations and unreachable routes.
"""

from dataclasses import dataclass
from typing import List, Optional

try:
    from src.graph import RoadGraph, RoadStatus
    from src.dijkstra import dijkstra, build_sample_disaster_network
    from src.models import Depot, Vehicle, AffectedLocation, RequestStatus
    from src.greedy import select_next_location, GreedyDecision, DEFAULT_AVERAGE_SPEED
except ImportError:
    from graph import RoadGraph, RoadStatus
    from dijkstra import dijkstra, build_sample_disaster_network
    from models import Depot, Vehicle, AffectedLocation, RequestStatus
    from greedy import select_next_location, GreedyDecision, DEFAULT_AVERAGE_SPEED


@dataclass
class DeliveryResult:
    """Detailed summary report of a simulated delivery execution.

    Attributes:
        success: Whether the delivery mission was successfully executed.
        vehicle_id: ID of the executing vehicle.
        location_id: Target location ID.
        route: Sequence of nodes traversed from start to target.
        distance: Total road distance traveled (km).
        travel_time: Time taken for transit (minutes/hours).
        arrival_time: Vehicle's updated mission clock after arrival.
        delivered_amount: Relief units delivered in this trip.
        remaining_vehicle_load: Units remaining onboard the vehicle.
        location_status: Post-delivery service status of the target location.
        message: Informative status or error explanation.
    """
    success: bool
    vehicle_id: str
    location_id: str
    route: List[str]
    distance: float
    travel_time: float
    arrival_time: float
    delivered_amount: int
    remaining_vehicle_load: int
    location_status: str
    message: str


def simulate_delivery(
    vehicle: Vehicle,
    decision: Optional[GreedyDecision],
    average_speed: float = DEFAULT_AVERAGE_SPEED,
) -> DeliveryResult:
    """Simulate moving a vehicle to a selected location and delivering relief goods.

    Execution Steps:
      1. Validate decision existence, route validity, location status, and vehicle load.
      2. Advance vehicle time: `travel_time = distance / average_speed`.
      3. Update vehicle location: `vehicle.current_location = location.id`.
      4. Deliver supplies: `delivered_amount = min(vehicle.current_load, location.remaining_demand)`.
      5. Deduct vehicle payload: `vehicle.current_load -= delivered_amount`.
      6. Update location demand & status: `location.receive_delivery(delivered_amount)`.
      7. Return structured DeliveryResult.

    Args:
        vehicle: Vehicle instance executing the delivery.
        decision: The GreedyDecision providing target location and planned path.
        average_speed: Speed in distance/time units (default 1.0 km/min = 60 km/h).

    Returns:
        DeliveryResult containing comprehensive mission metrics and status.
    """
    # Safety Check 1: Null decision
    if decision is None or decision.location is None:
        return DeliveryResult(
            success=False,
            vehicle_id=vehicle.id,
            location_id="",
            route=[],
            distance=0.0,
            travel_time=0.0,
            arrival_time=vehicle.current_time,
            delivered_amount=0,
            remaining_vehicle_load=vehicle.current_load,
            location_status="",
            message="Rejected: Decision or target location is None.",
        )

    loc = decision.location

    # Safety Check 2: Unreachable or invalid route
    if not decision.path or decision.distance == float("inf"):
        return DeliveryResult(
            success=False,
            vehicle_id=vehicle.id,
            location_id=loc.id,
            route=decision.path or [],
            distance=decision.distance,
            travel_time=0.0,
            arrival_time=vehicle.current_time,
            delivered_amount=0,
            remaining_vehicle_load=vehicle.current_load,
            location_status=loc.status,
            message=f"Rejected: No valid path exists to location '{loc.id}'.",
        )

    # Safety Check 3: Target already fully served
    if loc.status == RequestStatus.SERVED or loc.remaining_demand <= 0:
        return DeliveryResult(
            success=False,
            vehicle_id=vehicle.id,
            location_id=loc.id,
            route=decision.path,
            distance=decision.distance,
            travel_time=0.0,
            arrival_time=vehicle.current_time,
            delivered_amount=0,
            remaining_vehicle_load=vehicle.current_load,
            location_status=loc.status,
            message=f"Rejected: Location '{loc.id}' is already fully served.",
        )

    # Safety Check 4: Vehicle has no inventory
    if vehicle.current_load <= 0:
        return DeliveryResult(
            success=False,
            vehicle_id=vehicle.id,
            location_id=loc.id,
            route=decision.path,
            distance=decision.distance,
            travel_time=0.0,
            arrival_time=vehicle.current_time,
            delivered_amount=0,
            remaining_vehicle_load=0,
            location_status=loc.status,
            message=f"Rejected: Vehicle '{vehicle.id}' has zero load onboard.",
        )

    # --- Execution Phase ---
    # 1. Calculate transit metrics
    travel_time = decision.distance / average_speed
    vehicle.current_time += travel_time
    vehicle.current_location = loc.id

    # 2. Determine delivery amount: smaller of vehicle load and unmet demand
    deliverable = min(vehicle.current_load, loc.remaining_demand)
    vehicle.current_load -= deliverable

    # 3. Update location state
    actual_delivered = loc.receive_delivery(deliverable)

    return DeliveryResult(
        success=True,
        vehicle_id=vehicle.id,
        location_id=loc.id,
        route=decision.path,
        distance=decision.distance,
        travel_time=round(travel_time, 2),
        arrival_time=round(vehicle.current_time, 2),
        delivered_amount=actual_delivered,
        remaining_vehicle_load=vehicle.current_load,
        location_status=loc.status,
        message=f"Delivered {actual_delivered} units to '{loc.id}'. Status: {loc.status}.",
    )


# =====================================================================
# Verification and Self-Test Scenarios
# =====================================================================
if __name__ == "__main__":
    print("====================================================================")
    print("   ResQRoute Phase 3: Vehicle Movement & Delivery Simulation Demo   ")
    print("====================================================================\n")

    # 1. Setup Network and Vehicle
    network = build_sample_disaster_network()

    truck = Vehicle(
        id="Truck-Alpha",
        capacity=100,
        current_load=80,
        base_depot="Central Depot",
        current_location="Central Depot",
        current_time=0.0,
    )

    hospital = AffectedLocation(
        id="Field Hospital",
        name="Field Hospital",
        demand=50,
        urgency=1,
        deadline=60.0,
    )

    shelter = AffectedLocation(
        id="Shelter East",
        name="Shelter East",
        demand=40,
        urgency=2,
        deadline=80.0,
    )

    # --- Case 1: Normal Delivery (Complete fulfillment) ---
    print("[Case 1] Normal Delivery (Vehicle Load >= Location Demand):")
    print(f"  Starting Vehicle: Location='{truck.current_location}', Time={truck.current_time}m, Load={truck.current_load}")
    print(f"  Target Location:  Demand={hospital.demand}, Remaining={hospital.remaining_demand}, Status={hospital.status}")

    decision_1 = select_next_location(network, truck, [hospital, shelter])
    assert decision_1 is not None and decision_1.location.id == "Field Hospital"

    result_1 = simulate_delivery(truck, decision_1)
    print(f"  -> Execution Result: Success={result_1.success}")
    print(f"     Vehicle ID:         {result_1.vehicle_id}")
    print(f"     Location ID:        {result_1.location_id}")
    print(f"     Traversed Route:    {' -> '.join(result_1.route)}")
    print(f"     Distance Traveled:  {result_1.distance} km")
    print(f"     Travel Time:        {result_1.travel_time} min")
    print(f"     Arrival Time:       {result_1.arrival_time} min")
    print(f"     Delivered Amount:   {result_1.delivered_amount} units")
    print(f"     Remaining Load:     {result_1.remaining_vehicle_load} units")
    print(f"     Location Status:    {result_1.location_status}")

    assert result_1.success is True
    assert result_1.delivered_amount == 50
    assert result_1.remaining_vehicle_load == 30
    assert truck.current_location == "Field Hospital"
    assert truck.current_time == 10.0
    assert hospital.status == RequestStatus.SERVED
    assert hospital.remaining_demand == 0
    print("  [PASS] Case 1 passed (Full demand delivered, vehicle state updated).\n")

    # --- Case 2: Partial Delivery (Vehicle Load < Location Demand) ---
    print("[Case 2] Partial Delivery (Vehicle Load < Remaining Demand):")
    # Truck is now at Field Hospital with 30 units load. Shelter East demands 40 units.
    print(f"  Current Vehicle:  Location='{truck.current_location}', Time={truck.current_time}m, Load={truck.current_load}")
    print(f"  Target Location:  Demand={shelter.demand}, Remaining={shelter.remaining_demand}, Status={shelter.status}")

    # Directly build decision from Field Hospital to Shelter East (3.0 km directly connected)
    path_2, dist_2, _ = dijkstra(network, truck.current_location, shelter.id)
    decision_2 = GreedyDecision(
        location=shelter,
        path=path_2,
        distance=dist_2,
        estimated_arrival_time=truck.current_time + dist_2,
        priority=10.0,
    )

    result_2 = simulate_delivery(truck, decision_2)
    print(f"  -> Execution Result: Success={result_2.success}")
    print(f"     Vehicle ID:         {result_2.vehicle_id}")
    print(f"     Location ID:        {result_2.location_id}")
    print(f"     Traversed Route:    {' -> '.join(result_2.route)}")
    print(f"     Distance Traveled:  {result_2.distance} km")
    print(f"     Travel Time:        {result_2.travel_time} min")
    print(f"     Arrival Time:       {result_2.arrival_time} min")
    print(f"     Delivered Amount:   {result_2.delivered_amount} units")
    print(f"     Remaining Load:     {result_2.remaining_vehicle_load} units")
    print(f"     Location Status:    {result_2.location_status}")
    print(f"     Remaining Demand:   {shelter.remaining_demand} units")

    assert result_2.success is True
    assert result_2.delivered_amount == 30  # Delivered all remaining 30 units
    assert result_2.remaining_vehicle_load == 0  # Truck is now empty
    assert truck.current_location == "Shelter East"
    assert truck.current_time == 13.0
    assert shelter.status == RequestStatus.PARTIALLY_SERVED
    assert shelter.remaining_demand == 10
    print("  [PASS] Case 2 passed (Partial delivery safely processed, truck empty).\n")

    # --- Case 3: Rejection of Already Served Location ---
    print("[Case 3] Safety Validation: Attempting delivery to already SERVED location:")
    already_served_decision = GreedyDecision(
        location=hospital,  # Already SERVED in Case 1
        path=["Shelter East", "Field Hospital"],
        distance=3.0,
        estimated_arrival_time=16.0,
        priority=1.0,
    )
    result_3 = simulate_delivery(truck, already_served_decision)
    print(f"  -> Rejection Result: Success={result_3.success}, Message='{result_3.message}'")
    assert result_3.success is False
    assert "already fully served" in result_3.message.lower()
    print("  [PASS] Case 3 passed (Already served location safely rejected).\n")

    # --- Case 4: Rejection of Unreachable/Invalid Route ---
    print("[Case 4] Safety Validation: Attempting delivery with unreachable route:")
    unreachable_loc = AffectedLocation(
        id="Isolated Island",
        name="Isolated Island",
        demand=20,
        urgency=1,
        deadline=100.0,
    )
    unreachable_decision = GreedyDecision(
        location=unreachable_loc,
        path=[],
        distance=float("inf"),
        estimated_arrival_time=float("inf"),
        priority=0.0,
    )
    result_4 = simulate_delivery(truck, unreachable_decision)
    print(f"  -> Rejection Result: Success={result_4.success}, Message='{result_4.message}'")
    assert result_4.success is False
    assert "no valid path" in result_4.message.lower()
    print("  [PASS] Case 4 passed (Unreachable decision safely rejected).\n")

    print("====================================================================")
    print("   All Phase 3 Delivery Simulation tests passed successfully!       ")
    print("====================================================================\n")
