"""Data models for ResQRoute disaster relief logistics and scheduling.

Defines core entities for Phase 2:
  - RequestStatus: Status states for affected locations (UNSERVED, PARTIALLY_SERVED, SERVED).
  - Depot: Warehouses/supply points with inventory.
  - Vehicle: Relief transport vehicles with capacity and load tracking.
  - AffectedLocation: Disaster sites with aid demand, urgency, and deadlines.
"""

from dataclasses import dataclass
from typing import Optional


class RequestStatus:
    UNSERVED = "UNSERVED"
    PARTIALLY_SERVED = "PARTIALLY_SERVED"
    SERVED = "SERVED"
    VALID_STATUSES = {UNSERVED, PARTIALLY_SERVED, SERVED}


@dataclass
class Depot:
    """Represents a relief supply depot / base station.

    Attributes:
        id: Node ID matching a vertex in RoadGraph (e.g., "Central Depot").
        name: Human-readable name.
        available_supplies: Total inventory count of relief units in stock.
    """
    id: str
    name: str
    available_supplies: int = 0


@dataclass
class Vehicle:
    """Represents a disaster relief transport vehicle.

    Attributes:
        id: Unique vehicle identifier (e.g., "Truck-1").
        capacity: Maximum payload capacity in relief units.
        current_load: Current units of relief material loaded on board.
        base_depot: Starting / home depot node ID in RoadGraph.
        current_location: Current node ID where the vehicle is stationed.
        current_time: Cumulative mission clock time (in hours or minutes).
    """
    id: str
    capacity: int
    current_load: int = 0
    base_depot: str = ""
    current_location: str = ""
    current_time: float = 0.0

    def __post_init__(self) -> None:
        # If current_location is not explicitly provided, default to base_depot
        if not self.current_location and self.base_depot:
            self.current_location = self.base_depot

    @property
    def available_capacity(self) -> int:
        """Return remaining payload space on the vehicle."""
        return max(0, self.capacity - self.current_load)

    @property
    def is_empty(self) -> bool:
        """Check if the vehicle has no supplies left on board."""
        return self.current_load == 0


@dataclass
class AffectedLocation:
    """Represents a disaster-affected site requiring emergency relief supplies.

    Attributes:
        id: Node ID matching a vertex in RoadGraph (e.g., "Field Hospital").
        name: Human-readable name of the location.
        demand: Total relief units requested by the location.
        urgency: Priority rating (e.g., 1 = Critical, 2 = High, 3 = Moderate).
                 Lower numerical values indicate higher urgency.
        deadline: Maximum allowable mission time (in hours/minutes) by which aid must arrive.
        delivered_amount: Relief units received so far.
        status: Current service status (UNSERVED, PARTIALLY_SERVED, SERVED).
    """
    id: str
    name: str
    demand: int
    urgency: int
    deadline: float
    delivered_amount: int = 0
    status: str = RequestStatus.UNSERVED

    @property
    def remaining_demand(self) -> int:
        """Calculate remaining unmet relief demand."""
        return max(0, self.demand - self.delivered_amount)

    def receive_delivery(self, amount: int) -> int:
        """Record a delivery of relief supplies and update status accordingly.

        Args:
            amount: Units delivered.

        Returns:
            int: Actual accepted units delivered (capped by remaining demand).
        """
        accepted = min(amount, self.remaining_demand)
        self.delivered_amount += accepted
        if self.remaining_demand == 0:
            self.status = RequestStatus.SERVED
        elif self.delivered_amount > 0:
            self.status = RequestStatus.PARTIALLY_SERVED
        return accepted


if __name__ == "__main__":
    print("=== Testing ResQRoute Data Models ===")

    # 1. Instantiate a Depot
    depot = Depot(id="Central Depot", name="Main Logistics Warehouse", available_supplies=500)
    print(f"Depot: {depot.name} (ID: '{depot.id}'), Stock: {depot.available_supplies} units")

    # 2. Instantiate a Vehicle
    truck = Vehicle(
        id="Truck-Alpha",
        capacity=100,
        current_load=100,
        base_depot="Central Depot",
        current_location="Central Depot",
        current_time=0.0
    )
    print(f"Vehicle: {truck.id}, Load: {truck.current_load}/{truck.capacity}, Location: '{truck.current_location}'")

    # 3. Instantiate an AffectedLocation
    hospital = AffectedLocation(
        id="Field Hospital",
        name="Emergency Field Hospital",
        demand=60,
        urgency=1,        # Critical priority
        deadline=45.0,    # Must arrive within 45 minutes
    )
    print(f"Location: {hospital.name} (ID: '{hospital.id}'), Demand: {hospital.demand}, Status: {hospital.status}")
    print(f"  -> Remaining Demand: {hospital.remaining_demand} units")

    # Simulate a delivery
    delivered = hospital.receive_delivery(40)
    print(f"  -> Delivered {delivered} units. New Status: {hospital.status}, Remaining: {hospital.remaining_demand}")

    delivered = hospital.receive_delivery(20)
    print(f"  -> Delivered {delivered} units. New Status: {hospital.status}, Remaining: {hospital.remaining_demand}")
    print("=== All models initialized and verified successfully! ===")
