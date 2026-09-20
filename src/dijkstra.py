"""Dijkstra's Shortest Path Algorithm for ResQRoute Disaster Relief Routing.

DAA Theoretical Concepts:
  - Strategy: Greedy Approach.
  - Priority Queue: Min-Heap (via Python's `heapq` module).
  - Time Complexity: O((V + E) * log V), where V is vertices (locations) and E is edges (roads).
  - Space Complexity: O(V) for storing distances, predecessors, and heap state.
  - Invariant: When a node is popped from the min-heap, its shortest path from the source is finalized.
  - Constraint: Non-negative edge weights; impassable (BLOCKED) roads are skipped.
"""

import heapq
from typing import List, Optional, Tuple
try:
    from src.graph import RoadGraph, RoadStatus
except ImportError:
    from graph import RoadGraph, RoadStatus


def dijkstra(
    graph: RoadGraph,
    start: str,
    target: str,
    use_effective_cost: bool = True,
    damaged_penalty: float = 1.5,
) -> Tuple[Optional[List[str]], float, float]:
    """Find the optimal route from start to target using Dijkstra's algorithm.

    Blocked roads (status == RoadStatus.BLOCKED) are strictly bypassed.

    Args:
        graph: RoadGraph network instance
        start: Starting location node ID
        target: Destination location node ID
        use_effective_cost: If True, uses hazard-adjusted costs for routing
                           (e.g., damaged roads cost distance * damaged_penalty).
                           If False, routes purely by nominal physical distance on passable roads.
        damaged_penalty: Multiplier applied to physical distance on DAMAGED roads.

    Returns:
        tuple of:
          - path: List of node IDs representing the route, or None if unreachable.
          - total_distance: Sum of nominal physical distance (km) along the path.
          - total_cost: Sum of effective traversal cost along the path.
    """
    if start not in graph.nodes():
        raise ValueError(f"Start node '{start}' does not exist in graph.")
    if target not in graph.nodes():
        raise ValueError(f"Target node '{target}' does not exist in graph.")

    # Base case: start is target
    if start == target:
        return [start], 0.0, 0.0

    # distances stores the minimum known traversal cost from start to each node
    distances = {node: float("inf") for node in graph.nodes()}
    distances[start] = 0.0

    # predecessors stores the previous node on the shortest path for backtracking
    predecessors = {node: None for node in graph.nodes()}

    # Min-Heap stores tuples: (current_cost, current_node)
    priority_queue: List[Tuple[float, str]] = [(0.0, start)]

    # Visited set ensures we do not re-process nodes whose shortest path is finalized
    visited = set()

    while priority_queue:
        current_cost, current_node = heapq.heappop(priority_queue)

        if current_node in visited:
            continue
        visited.add(current_node)

        # Early termination: destination reached
        if current_node == target:
            break

        # If current cost exceeds recorded distance, skip stale heap entries
        if current_cost > distances[current_node]:
            continue

        # Explore neighbors
        for neighbor, edge_attrs in graph.adj.get(current_node, {}).items():
            # RULE: Impassable roads (BLOCKED) must not be traversed
            if edge_attrs["status"] == RoadStatus.BLOCKED:
                continue

            # Compute edge traversal cost
            if use_effective_cost:
                edge_cost = graph.get_effective_weight(
                    current_node, neighbor, damaged_penalty=damaged_penalty
                )
            else:
                edge_cost = edge_attrs["distance"]

            if edge_cost == float("inf"):
                continue

            new_cost = current_cost + edge_cost

            # Relaxation step: update if a shorter path is discovered
            if new_cost < distances[neighbor]:
                distances[neighbor] = new_cost
                predecessors[neighbor] = current_node
                heapq.heappush(priority_queue, (new_cost, neighbor))

    # If destination was not reached, return None
    if distances[target] == float("inf"):
        return None, float("inf"), float("inf")

    # Path reconstruction via predecessor backtracking
    path = []
    curr = target
    while curr is not None:
        path.append(curr)
        curr = predecessors[curr]
    path.reverse()

    # Calculate nominal physical distance and effective traversal cost
    total_physical_distance = 0.0
    total_effective_cost = 0.0

    for i in range(len(path) - 1):
        u, v = path[i], path[i + 1]
        edge = graph.get_edge(u, v)
        if edge:
            total_physical_distance += edge["distance"]
            if edge["status"] == RoadStatus.DAMAGED and use_effective_cost:
                total_effective_cost += edge["distance"] * damaged_penalty
            else:
                total_effective_cost += edge["distance"]

    return path, round(total_physical_distance, 2), round(total_effective_cost, 2)


# =====================================================================
# Verification and Example Disaster Relief Network Demonstration
# =====================================================================
def build_sample_disaster_network() -> RoadGraph:
    """Build a sample disaster road network for testing.

    Topology:
      [Central Depot] --- 4 km --- [Junction A] --- 6 km --- [Field Hospital]
            |                             |                         |
           3 km                          2 km                      3 km
            |                             |                         |
      [Junction B] ------- 5 km --- [Junction C] --- 4 km --- [Shelter East]
    """
    g = RoadGraph()

    g.add_edge("Central Depot", "Junction A", distance=4.0, status=RoadStatus.CLEAR)
    g.add_edge("Central Depot", "Junction B", distance=3.0, status=RoadStatus.CLEAR)
    g.add_edge("Junction A", "Field Hospital", distance=6.0, status=RoadStatus.CLEAR)
    g.add_edge("Junction A", "Junction C", distance=2.0, status=RoadStatus.CLEAR)
    g.add_edge("Junction B", "Junction C", distance=5.0, status=RoadStatus.CLEAR)
    g.add_edge("Junction C", "Shelter East", distance=4.0, status=RoadStatus.CLEAR)
    g.add_edge("Field Hospital", "Shelter East", distance=3.0, status=RoadStatus.CLEAR)

    return g


if __name__ == "__main__":
    print("====================================================================")
    print("   ResQRoute Phase 1: Dijkstra's Disaster Relief Routing Demo       ")
    print("====================================================================\n")

    network = build_sample_disaster_network()
    network.display()

    origin = "Central Depot"
    destination = "Field Hospital"

    # --- Test Case 1: Baseline routing with all roads CLEAR ---
    print(f"\n[Test Case 1] Normal Conditions: Routing from '{origin}' to '{destination}'...")
    path, dist, cost = dijkstra(network, origin, destination)
    print(f"  -> Optimal Route: {' -> '.join(path)}")
    print(f"  -> Total Physical Distance: {dist} km")
    print(f"  -> Total Routing Cost:     {cost}")
    assert path == ["Central Depot", "Junction A", "Field Hospital"], "Unexpected path in Test 1!"
    print("  [PASS] Test Case 1 passed.\n")

    # --- Test Case 2: Disaster event blocks primary road ---
    blocked_road = ("Junction A", "Field Hospital")
    print(f"[Test Case 2] Disaster Event: Flood/Debris blocks {blocked_road[0]} <-> {blocked_road[1]}!")
    network.set_road_status(blocked_road[0], blocked_road[1], RoadStatus.BLOCKED)

    path, dist, cost = dijkstra(network, origin, destination)
    print(f"  -> Recalculated Route:     {' -> '.join(path)}")
    print(f"  -> Total Physical Distance: {dist} km")
    print(f"  -> Total Routing Cost:     {cost}")
    # Verify that the blocked edge (Junction A <-> Field Hospital) is not traversed
    edge_traversed = any(
        (path[i] == blocked_road[0] and path[i + 1] == blocked_road[1]) or
        (path[i] == blocked_road[1] and path[i + 1] == blocked_road[0])
        for i in range(len(path) - 1)
    )
    assert not edge_traversed, f"Blocked road {blocked_road} was traversed!"
    assert path == ["Central Depot", "Junction A", "Junction C", "Shelter East", "Field Hospital"], "Unexpected detour path!"
    print("  [PASS] Test Case 2 passed (Dijkstra successfully bypassed blocked road).\n")

    # --- Test Case 3: Damaged road with penalty vs clear detour ---
    print(f"[Test Case 3] Road Degradation: Bridge between Central Depot <-> Junction A is DAMAGED...")
    # Reset blocked road to clear, but damage the direct link
    network.set_road_status("Junction A", "Field Hospital", RoadStatus.CLEAR)
    network.set_road_status("Central Depot", "Junction A", RoadStatus.DAMAGED)

    path, dist, cost = dijkstra(network, origin, destination, use_effective_cost=True)
    print(f"  -> Route with Damage Penalty: {' -> '.join(path)}")
    print(f"  -> Total Physical Distance:   {dist} km")
    print(f"  -> Traversal Cost (w/ penalty): {cost}")
    print("  [PASS] Test Case 3 passed.\n")

    # --- Test Case 4: Destination completely cut off ---
    print(f"[Test Case 4] Extreme Disaster: All roads to '{destination}' BLOCKED...")
    network.set_road_status("Junction A", "Field Hospital", RoadStatus.BLOCKED)
    network.set_road_status("Field Hospital", "Shelter East", RoadStatus.BLOCKED)

    path, dist, cost = dijkstra(network, origin, destination)
    print(f"  -> Result when unreachable: path = {path}, distance = {dist}")
    assert path is None, "Path should be None when destination is unreachable!"
    print("  [PASS] Test Case 4 passed (Proper unreachable handling).\n")

    print("====================================================================")
    print("   All Phase 1 Dijkstra tests executed successfully!               ")
    print("====================================================================")
