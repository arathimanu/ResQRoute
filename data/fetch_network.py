"""
data/fetch_network.py
=====================
One-time script to download the Chennai, Tamil Nadu OSM road network
and export it as data/chennai_graph.json for offline use.

Run once (requires internet):
    .venv\\Scripts\\python data/fetch_network.py

Output:
    data/chennai_graph.json   — cached road graph (nodes + edges + geometry)

The downloaded graph is based on publicly available OpenStreetMap data.
All coordinates are real geographic data (lat/lon from OSM).
Disaster scenario parameters (risk, demand, severity) are NOT from this file
and are clearly labelled as simulation inputs in data/scenario.json.
"""

import json
import math
import os
import sys
from datetime import datetime, timezone

try:
    import osmnx as ox
except ImportError:
    print("ERROR: osmnx is not installed.")
    print("Install with: .venv\\Scripts\\python -m pip install osmnx")
    sys.exit(1)

# ── Study Area ─────────────────────────────────────────────────────────────────
# Chennai Central + South, covering Adyar/Cooum flood basin.
# We use a wider west bound to include Koyambedu and the airport approach road.
NORTH = 13.10
SOUTH = 13.00
EAST  = 80.29
WEST  = 80.20

# Only keep major road categories (suitable for disaster relief routing).
# This keeps the graph manageable (~1 000–3 000 edges) while remaining real.
ROAD_FILTER = (
    '["highway"~"motorway|trunk|primary|secondary|tertiary'
    '|motorway_link|trunk_link|primary_link|secondary_link|tertiary_link"]'
)

# ── Key Facility Locations ─────────────────────────────────────────────────────
# Real Chennai facilities; coordinates from public OpenStreetMap data.
# These will be snapped to their nearest OSM drive-network node.
KEY_LOCATIONS: dict[str, tuple[float, float]] = {
    "ripon_building":       (13.0827, 80.2707),   # GCC / disaster command HQ
    "govt_general_hospital":(13.0827, 80.2719),   # Government General Hospital
    "stanley_hospital":     (13.1085, 80.2866),   # Stanley Medical College Hospital
    "rajiv_gandhi_hospital":(12.9957, 80.2157),   # Rajiv Gandhi Govt. General Hospital
    "jn_stadium":           (13.0048, 80.2613),   # Jawaharlal Nehru Stadium (flood camp)
    "ymca_nandanam":        (13.0100, 80.2483),   # YMCA Ground, Nandanam
    "marina_beach":         (13.0500, 80.2824),   # Marina Beach grounds (open shelter)
    "koyambedu_market":     (13.0694, 80.1948),   # Koyambedu Market Complex (supply hub)
    "chennai_airport_road": (12.9941, 80.1789),   # Airport area logistics node
    "anna_nagar":           (13.0868, 80.2101),   # Anna Nagar Tower Park
}


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two points (km)."""
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def main() -> None:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(script_dir, "chennai_graph.json")

    print("=" * 65)
    print("  ResQRoute - Chennai OSM Road Network Fetcher")
    print("=" * 65)
    print(f"  Bbox:  {SOUTH} N to {NORTH} N  |  {WEST} E to {EAST} E")
    print(f"  Area:  ~{haversine_km(SOUTH, WEST, NORTH, WEST):.0f} km x "
          f"{haversine_km(SOUTH, WEST, SOUTH, EAST):.0f} km")
    print("  Filter: major roads (primary, secondary, tertiary + links)")
    print()

    # -- Download ---------------------------------------------------------------
    print("Downloading from OpenStreetMap via Overpass API...")
    print("(This may take 1-3 minutes. Please wait.)")

    # Use a reliable overpass endpoint and settings
    ox.settings.overpass_url = "https://overpass.kumi.systems/api/interpreter"
    ox.settings.requests_kwargs = {"verify": False}  # Bypass local corporate SSL interception if any

    endpoints = [
        "https://overpass.kumi.systems/api/interpreter",
        "https://overpass-api.de/api/interpreter",
        "https://overpass.nchc.org.tw/api/interpreter",
    ]

    G = None
    for ep in endpoints:
        print(f"Trying Overpass endpoint: {ep} ...")
        ox.settings.overpass_url = ep
        try:
            G = ox.graph_from_bbox(
                bbox=(NORTH, SOUTH, EAST, WEST),
                network_type="drive",
                simplify=True,
                custom_filter=ROAD_FILTER,
            )
            if G is not None:
                print(f"Successfully fetched graph from {ep}")
                break
        except Exception as exc:
            print(f"Endpoint {ep} failed: {exc}")

    if G is None:
        print("ERROR: Could not fetch graph from any Overpass server.")
        sys.exit(1)

    raw_nodes = len(G.nodes)
    raw_edges = len(G.edges)
    print(f"Downloaded: {raw_nodes:,} nodes, {raw_edges:,} edges")

    # ── Snap key locations to nearest graph node ───────────────────────────────
    # -- Snap key locations to nearest graph node -------------------------------
    print("\nSnapping key facilities to nearest road-network nodes...")
    key_location_nodes: dict[str, str] = {}
    for loc_id, (lat, lon) in KEY_LOCATIONS.items():
        try:
            node_id = ox.nearest_nodes(G, X=lon, Y=lat)
            key_location_nodes[loc_id] = str(node_id)
            node_lat = G.nodes[node_id].get("y", lat)
            node_lon = G.nodes[node_id].get("x", lon)
            snap_dist = haversine_km(lat, lon, node_lat, node_lon) * 1000
            print(f"  {loc_id:30s} -> OSM node {node_id}  (snap {snap_dist:.0f} m)")
        except Exception as exc:
            print(f"  WARNING: could not snap {loc_id}: {exc}")

    # -- Build nodes dict -------------------------------------------------------
    print("\nBuilding node dictionary...")
    nodes_dict: dict[str, dict] = {}
    for node_id, data in G.nodes(data=True):
        entry: dict = {
            "lat": round(float(data.get("y", 0.0)), 7),
            "lon": round(float(data.get("x", 0.0)), 7),
        }
        nodes_dict[str(node_id)] = entry

    # Attach human-readable labels to key-location nodes
    for loc_id, osm_id_str in key_location_nodes.items():
        if osm_id_str in nodes_dict:
            nodes_dict[osm_id_str]["label"] = loc_id

    # ── Build edges list ───────────────────────────────────────────────────────
    print("Building edge list …")
    edges_list: list[dict] = []
    seen: set[tuple] = set()

    for u, v, data in G.edges(data=True):
        u_str, v_str = str(u), str(v)
        pair = tuple(sorted([u_str, v_str]))
        if pair in seen:
            continue
        seen.add(pair)

        length_m = float(data.get("length", 0))
        distance_km = round(length_m / 1000.0, 5)
        if distance_km <= 0:
            continue

        # Extract actual road geometry (shapely LineString → list of [lat, lon])
        geometry: list[list[float]] = []
        if "geometry" in data:
            try:
                for lon_pt, lat_pt in data["geometry"].coords:
                    geometry.append([round(lat_pt, 7), round(lon_pt, 7)])
            except Exception:
                pass

        if not geometry:
            # Fall back to straight line between endpoints
            u_d = nodes_dict.get(u_str, {})
            v_d = nodes_dict.get(v_str, {})
            if u_d and v_d:
                geometry = [
                    [u_d["lat"], u_d["lon"]],
                    [v_d["lat"], v_d["lon"]],
                ]

        # Road name (may be a list in OSM data)
        raw_name = data.get("name", "")
        if isinstance(raw_name, list):
            raw_name = raw_name[0] if raw_name else ""

        edges_list.append({
            "u": u_str,
            "v": v_str,
            "distance_km": distance_km,
            "status": "CLEAR",
            "name": str(raw_name),
            "geometry": geometry,
        })

    # ── Write output ───────────────────────────────────────────────────────────
    output = {
        "metadata": {
            "source": "OpenStreetMap contributors (ODbL)",
            "area": "Chennai, Tamil Nadu, India",
            "bbox": {"north": NORTH, "south": SOUTH, "east": EAST, "west": WEST},
            "road_types": "primary, secondary, tertiary and link roads",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_nodes": len(nodes_dict),
            "total_edges": len(edges_list),
        },
        "nodes": nodes_dict,
        "edges": edges_list,
        "key_location_nodes": key_location_nodes,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, separators=(",", ":"))

    size_mb = os.path.getsize(output_path) / 1_048_576
    print(f"\n[OK] Saved to {output_path}")
    print(f"   {len(nodes_dict):,} nodes | {len(edges_list):,} unique edges | {size_mb:.1f} MB")
    print(f"   Key location nodes: {key_location_nodes}")
    print("\nDone. Re-run only if you need to refresh the road network.")


if __name__ == "__main__":
    main()
