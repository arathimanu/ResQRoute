"""OSM Road Graph Loader for ResQRoute.

Converts the downloaded OpenStreetMap graph JSON into the project's native `RoadGraph` instance.
Binds real OSM road distances (in km) and geometries for visualization.
"""

import json
import os
from typing import Dict, Tuple, Any, List

from src.graph import RoadGraph, RoadStatus
from config import GRAPH_PATH


def load_osm_road_graph(graph_json_path: str = str(GRAPH_PATH)) -> Tuple[RoadGraph, Dict[str, Dict[str, Any]], Dict[str, Any]]:
    """Load cached OSM road graph and return (RoadGraph, node_coordinates_map, raw_json_data).

    Returns:
        graph: Native RoadGraph populated with nodes and edges
        node_positions: Dict mapping node_id -> {"lat": float, "lon": float, "label": str}
        raw_data: Complete dict loaded from json
    """
    if not os.path.exists(graph_json_path):
        raise FileNotFoundError(
            f"OSM graph data file '{graph_json_path}' not found.\n"
            "Please run `python data/fetch_network.py` first to download the Chennai road network."
        )

    with open(graph_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    graph = RoadGraph()
    node_positions: Dict[str, Dict[str, Any]] = {}

    # 1. Add nodes
    for node_id, attrs in data.get("nodes", {}).items():
        graph.add_node(node_id)
        node_positions[node_id] = {
            "lat": attrs["lat"],
            "lon": attrs["lon"],
            "label": attrs.get("label", node_id),
        }

    # 2. Add edges
    for edge in data.get("edges", []):
        u = edge["u"]
        v = edge["v"]
        distance_km = edge["distance_km"]
        status = edge.get("status", RoadStatus.CLEAR)

        if distance_km > 0:
            graph.add_edge(u, v, distance=distance_km, status=status, bidirectional=True)
            # Store rich metadata on internal edge dictionary for frontend display
            if u in graph.adj and v in graph.adj[u]:
                graph.adj[u][v]["name"] = edge.get("name", "")
                graph.adj[u][v]["geometry"] = edge.get("geometry", [])
            if v in graph.adj and u in graph.adj[v]:
                graph.adj[v][u]["name"] = edge.get("name", "")
                # Reversed geometry for opposite direction
                rev_geom = list(reversed(edge.get("geometry", [])))
                graph.adj[v][u]["geometry"] = rev_geom

    return graph, node_positions, data
