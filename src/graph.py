"""Graph representation for the ResQRoute disaster relief road network.

This module models road intersections/locations as nodes and road segments as weighted edges.
Each edge maintains a physical distance and a dynamic road status:
  - CLEAR: Normal condition, passable at standard cost.
  - DAMAGED: Degraded condition (e.g. minor flooding or debris), passable with penalty.
  - BLOCKED: Impassable road (e.g. severe flooding, landslide, collapsed bridge).
"""

from typing import Dict, List, Optional, Tuple


class RoadStatus:
    CLEAR = "CLEAR"
    DAMAGED = "DAMAGED"
    BLOCKED = "BLOCKED"
    VALID_STATUSES = {CLEAR, DAMAGED, BLOCKED}


class RoadGraph:
    """Road network graph using an adjacency list representation.
    
    Adjacency Structure:
        self.adj[u][v] = {
            'distance': float,   # Physical distance in km or meters
            'status': str        # RoadStatus (CLEAR, DAMAGED, BLOCKED)
        }
    """

    def __init__(self) -> None:
        self.adj: Dict[str, Dict[str, Dict[str, any]]] = {}

    def add_node(self, node: str) -> None:
        """Add a location/intersection node to the graph if it doesn't already exist."""
        if node not in self.adj:
            self.adj[node] = {}

    def add_edge(
        self,
        u: str,
        v: str,
        distance: float,
        status: str = RoadStatus.CLEAR,
        bidirectional: bool = True,
    ) -> None:
        """Add a road connection between two nodes with a physical distance and status.
        
        Args:
            u: Starting node ID
            v: Ending node ID
            distance: Physical distance (> 0)
            status: Road status ('CLEAR', 'DAMAGED', or 'BLOCKED')
            bidirectional: If True, adds an edge in both directions (u <-> v)
        """
        if status not in RoadStatus.VALID_STATUSES:
            raise ValueError(f"Invalid status '{status}'. Must be one of {RoadStatus.VALID_STATUSES}")
        if distance <= 0:
            raise ValueError("Distance must be a positive number.")

        self.add_node(u)
        self.add_node(v)

        self.adj[u][v] = {"distance": float(distance), "status": status}
        if bidirectional:
            self.adj[v][u] = {"distance": float(distance), "status": status}

    def set_road_status(
        self,
        u: str,
        v: str,
        status: str,
        bidirectional: bool = True,
    ) -> None:
        """Dynamically update the condition of an existing road segment."""
        if status not in RoadStatus.VALID_STATUSES:
            raise ValueError(f"Invalid status '{status}'. Must be one of {RoadStatus.VALID_STATUSES}")
        if u not in self.adj or v not in self.adj[u]:
            raise KeyError(f"Road segment between '{u}' and '{v}' does not exist.")

        self.adj[u][v]["status"] = status
        if bidirectional and v in self.adj and u in self.adj[v]:
            self.adj[v][u]["status"] = status

    def get_edge(self, u: str, v: str) -> Optional[Dict[str, any]]:
        """Return edge attributes between u and v, or None if no edge exists."""
        return self.adj.get(u, {}).get(v)

    def get_effective_weight(self, u: str, v: str, damaged_penalty: float = 1.5) -> float:
        """Calculate the traversal weight for routing algorithms.
        
        - CLEAR: returns base physical distance
        - DAMAGED: returns distance * damaged_penalty (simulates delays/slower transit)
        - BLOCKED: returns infinity (impassable)
        """
        edge = self.get_edge(u, v)
        if edge is None:
            return float("inf")

        status = edge["status"]
        if status == RoadStatus.BLOCKED:
            return float("inf")
        elif status == RoadStatus.DAMAGED:
            return edge["distance"] * damaged_penalty
        return edge["distance"]

    def get_neighbors(self, node: str, include_blocked: bool = False) -> Dict[str, Dict[str, any]]:
        """Return adjacent neighbors of a node.
        
        Args:
            node: The node ID to inspect
            include_blocked: If False, omits neighbors connected via BLOCKED roads
        """
        if node not in self.adj:
            return {}
        if include_blocked:
            return self.adj[node]
        return {
            neighbor: attrs
            for neighbor, attrs in self.adj[node].items()
            if attrs["status"] != RoadStatus.BLOCKED
        }

    def nodes(self) -> List[str]:
        """Return all node IDs in the graph."""
        return list(self.adj.keys())

    def display(self) -> None:
        """Print a human-readable representation of the road network."""
        print("=== Disaster Road Network Topology ===")
        for u in sorted(self.adj.keys()):
            neighbors = self.adj[u]
            if not neighbors:
                print(f"  {u} -> (no connections)")
                continue
            edges_str = ", ".join(
                f"{v} ({attrs['distance']}km, {attrs['status']})"
                for v, attrs in neighbors.items()
            )
            print(f"  {u} -> {edges_str}")
        print("=======================================")
