"""ResQRoute - Streamlit Interactive Demo.

Adaptive Disaster Relief Routing — an offline-first routing system for
planning and adapting relief deliveries in changing disaster conditions.
"""

from typing import Dict, List, Optional, Tuple
import matplotlib.pyplot as plt
import networkx as nx
import streamlit as st

from src.graph import RoadGraph, RoadStatus
from src.dijkstra import dijkstra
from src.models import Depot, Vehicle, AffectedLocation, RequestStatus
from src.greedy import select_next_location, GreedyDecision, DEFAULT_AVERAGE_SPEED
from src.simulation import simulate_delivery, DeliveryResult
from src.mission import run_mission


# =====================================================================
# Fixed Layout Coordinates for Deterministic Visualization
# =====================================================================
NODE_POSITIONS: Dict[str, Tuple[float, float]] = {
    "Central Depot": (0.0, 1.0),
    "Junction A": (2.2, 2.0),
    "Junction B": (2.2, 0.0),
    "Junction C": (4.8, 0.0),
    "Field Hospital": (5.2, 2.0),
    "Shelter East": (7.4, 1.0),
}


# =====================================================================
# Scenario Initialization
# =====================================================================
def create_initial_scenario() -> Tuple[RoadGraph, Depot, Vehicle, List[AffectedLocation]]:
    """Create a fixed, realistic disaster scenario with clear alternative paths."""
    graph = RoadGraph()

    # Roads topology:
    # Upper Corridor: Central Depot -> Junction A -> Field Hospital (4 + 5 = 9 km)
    # Lower Corridor: Central Depot -> Junction B -> Junction C -> Shelter East (3 + 4 + 4 = 11 km)
    # Cross Links: Junction A <-> Junction C (2 km), Field Hospital <-> Shelter East (3 km)
    graph.add_edge("Central Depot", "Junction A", distance=4.0, status=RoadStatus.CLEAR)
    graph.add_edge("Central Depot", "Junction B", distance=3.0, status=RoadStatus.CLEAR)
    graph.add_edge("Junction A", "Field Hospital", distance=5.0, status=RoadStatus.CLEAR)
    graph.add_edge("Junction A", "Junction C", distance=2.0, status=RoadStatus.CLEAR)
    graph.add_edge("Junction B", "Junction C", distance=4.0, status=RoadStatus.CLEAR)
    graph.add_edge("Junction C", "Shelter East", distance=4.0, status=RoadStatus.CLEAR)
    graph.add_edge("Field Hospital", "Shelter East", distance=3.0, status=RoadStatus.CLEAR)

    depot = Depot(
        id="Central Depot",
        name="Main Logistics Warehouse",
        available_supplies=250,
    )

    vehicle = Vehicle(
        id="Relief-Truck-1",
        capacity=100,
        current_load=90,
        base_depot="Central Depot",
        current_location="Central Depot",
        current_time=0.0,
    )

    locations = [
        AffectedLocation(
            id="Field Hospital",
            name="Emergency Field Hospital",
            demand=50,
            urgency=1,       # Priority 1: Critical
            deadline=60.0,   # Arrive within 60 mins
        ),
        AffectedLocation(
            id="Shelter East",
            name="Displaced Persons Shelter East",
            demand=40,
            urgency=2,       # Priority 2: High
            deadline=85.0,   # Arrive within 85 mins
        ),
        AffectedLocation(
            id="Junction C",
            name="Relief Camp Junction C",
            demand=25,
            urgency=3,       # Priority 3: Moderate
            deadline=100.0,  # Arrive within 100 mins
        ),
    ]

    return graph, depot, vehicle, locations


def initialize_session_state(force_reset: bool = False) -> None:
    """Initialize or reset the Streamlit session state variables."""
    if force_reset or "graph" not in st.session_state:
        graph, depot, vehicle, locations = create_initial_scenario()
        st.session_state.graph = graph
        st.session_state.depot = depot
        st.session_state.vehicle = vehicle
        st.session_state.locations = locations
        st.session_state.delivery_history: List[DeliveryResult] = []
        st.session_state.last_decision: Optional[GreedyDecision] = None
        st.session_state.active_route: Optional[List[str]] = None
        st.session_state.previous_route: Optional[List[str]] = None
        st.session_state.reroute_flag: Optional[bool] = None
        st.session_state.reroute_count: int = 0
        st.session_state.update_message: Optional[str] = None


# =====================================================================
# Graph Visualization (NetworkX + Matplotlib)
# =====================================================================
def get_unique_edges(graph: RoadGraph) -> List[Tuple[str, str, Dict[str, any]]]:
    """Return an undirected list of unique road segments with their attributes."""
    seen = set()
    edges = []
    for u in graph.adj:
        for v, attrs in graph.adj[u].items():
            pair = tuple(sorted([u, v]))
            if pair not in seen:
                seen.add(pair)
                edges.append((pair[0], pair[1], attrs))
    return edges


def plot_network(
    graph: RoadGraph,
    locations: List[AffectedLocation],
    vehicle: Vehicle,
    active_route: Optional[List[str]] = None,
) -> plt.Figure:
    """Render a clean, publication-quality road network plot with hazards and active routes."""
    fig, ax = plt.subplots(figsize=(9.5, 5.2), dpi=120)
    G = nx.Graph()

    # Build networkx graph
    for u in graph.adj:
        G.add_node(u)
        for v, attrs in graph.adj[u].items():
            G.add_edge(u, v, weight=attrs["distance"], status=attrs["status"])

    pos = NODE_POSITIONS

    # Locations lookup map
    loc_map = {loc.id: loc for loc in locations}

    # Determine node colors
    node_colors = []
    node_sizes = []
    node_labels = {}

    for node in G.nodes():
        if node == "Central Depot":
            node_colors.append("#2980B9")  # Blue
            node_sizes.append(1500)
            node_labels[node] = f"DEPOT\n({node})"
        elif node in loc_map:
            loc = loc_map[node]
            if loc.status == RequestStatus.SERVED:
                node_colors.append("#27AE60")  # Green
            elif loc.status == RequestStatus.PARTIALLY_SERVED:
                node_colors.append("#F39C12")  # Orange
            else:
                node_colors.append("#E74C3C")  # Red (Unserved)
            node_sizes.append(1800)
            node_labels[node] = f"{node}\n[Req: {loc.remaining_demand} | P{loc.urgency}]"
        else:
            node_colors.append("#95A5A6")  # Gray (Transit Junction)
            node_sizes.append(1300)
            node_labels[node] = f"{node}\n(Junction)"

    # Draw nodes
    nx.draw_networkx_nodes(
        G,
        pos,
        ax=ax,
        node_color=node_colors,
        node_size=node_sizes,
        edgecolors="#2C3E50",
        linewidths=2.0,
    )

    # Highlight current vehicle location
    if vehicle.current_location in pos:
        v_pos = pos[vehicle.current_location]
        ax.scatter(
            [v_pos[0]],
            [v_pos[1] + 0.28],
            s=450,
            marker="v",
            color="#F1C40F",
            edgecolors="#D68910",
            linewidths=2.0,
            zorder=6,
            label=f"Vehicle: {vehicle.id}",
        )

    # Identify route edges
    route_edge_set = set()
    if active_route and len(active_route) > 1:
        for i in range(len(active_route) - 1):
            pair = tuple(sorted([active_route[i], active_route[i + 1]]))
            route_edge_set.add(pair)

    # Draw edges by category
    unique_edges = get_unique_edges(graph)
    edge_labels = {}

    for u, v, attrs in unique_edges:
        dist = attrs["distance"]
        status = attrs["status"]
        pair = tuple(sorted([u, v]))
        is_in_route = pair in route_edge_set

        # Text label on edge
        if status == RoadStatus.BLOCKED:
            edge_labels[(u, v)] = f"{dist}k [BLOCKED]"
        elif status == RoadStatus.DAMAGED:
            edge_labels[(u, v)] = f"{dist}k (DAMAGED)"
        else:
            edge_labels[(u, v)] = f"{dist} km"

        # Edge rendering styles
        if is_in_route:
            # Active planned path (Cyan/Royal Blue outline)
            nx.draw_networkx_edges(
                G,
                pos,
                edgelist=[(u, v)],
                ax=ax,
                width=5.5,
                edge_color="#00A8FF",
                alpha=0.9,
            )
        elif status == RoadStatus.BLOCKED:
            # Blocked Road (Red Dashed)
            nx.draw_networkx_edges(
                G,
                pos,
                edgelist=[(u, v)],
                ax=ax,
                width=3.0,
                edge_color="#E74C3C",
                style="dashed",
                alpha=0.85,
            )
        elif status == RoadStatus.DAMAGED:
            # Damaged Road (Orange Solid)
            nx.draw_networkx_edges(
                G,
                pos,
                edgelist=[(u, v)],
                ax=ax,
                width=3.0,
                edge_color="#E67E22",
                style="solid",
                alpha=0.85,
            )
        else:
            # Clear Road (Slate Gray Solid)
            nx.draw_networkx_edges(
                G,
                pos,
                edgelist=[(u, v)],
                ax=ax,
                width=2.2,
                edge_color="#7F8C8D",
                style="solid",
                alpha=0.7,
            )

    # Draw labels
    nx.draw_networkx_labels(G, pos, labels=node_labels, ax=ax, font_size=8.5, font_weight="bold")
    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, ax=ax, font_size=8, font_color="#2C3E50")

    ax.set_title("Road Network", fontsize=13, fontweight="bold", pad=12)
    ax.axis("off")
    plt.tight_layout()
    return fig


# =====================================================================
# Main Streamlit Application
# =====================================================================
def main() -> None:
    st.set_page_config(
        page_title="ResQRoute - Adaptive Disaster Relief Routing",
        page_icon="🚑",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    initialize_session_state()

    # --- Header ---
    st.title("🚑 ResQRoute")
    st.markdown("#### Adaptive Disaster Relief Routing")
    st.caption(
        "An offline-first routing system for planning and adapting relief deliveries "
        "in changing disaster conditions."
    )

    st.info(
        "**Offline-First** — all routing and scheduling runs locally on your machine. "
        "No internet connection, GPS, or external data sources are required.",
        icon="📡",
    )
    st.divider()

    # --- Sidebar Overview & Mission Stats ---
    with st.sidebar:
        st.header("Mission Control")
        if st.button("↺ Reset Scenario", use_container_width=True):
            initialize_session_state(force_reset=True)
            st.rerun()

        st.subheader("Vehicle Status")
        veh = st.session_state.vehicle
        st.write(f"**ID:** `{veh.id}`")
        st.write(f"**Location:** `{veh.current_location}`")
        st.write(f"**Mission Clock:** `{veh.current_time:.1f} min`")
        st.write(f"**Supplies:** `{veh.current_load} / {veh.capacity} units`")
        st.progress(veh.current_load / max(1, veh.capacity))

        st.subheader("Affected Locations")
        for loc in st.session_state.locations:
            status_emoji = "🟢" if loc.status == RequestStatus.SERVED else ("🟠" if loc.status == RequestStatus.PARTIALLY_SERVED else "🔴")
            st.write(
                f"{status_emoji} **{loc.name}**\n"
                f"- Remaining: **{loc.remaining_demand}** / {loc.demand} units\n"
                f"- Urgency: **P{loc.urgency}** | Deadline: **{loc.deadline:.0f} min**"
            )

        st.divider()
        st.caption("**Map Legend**")
        st.markdown(
            "- 🟦 Depot · 🔴 Unserved · 🟢 Served · ⚪ Junction\n"
            "- ─── Clear road\n"
            "- ─── Damaged road (1.5× cost)\n"
            "- - - Blocked road (impassable)\n"
            "- ━━━ Active planned route\n"
            "- 🟡 Vehicle position"
        )

    # --- Layout Columns ---
    col_map, col_ops = st.columns([1.2, 1.0], gap="medium")

    # =================================================================
    # Column 1: Road Network Visualization
    # =================================================================
    with col_map:
        st.subheader("🗺️ Road Network Topology")
        fig = plot_network(
            graph=st.session_state.graph,
            locations=st.session_state.locations,
            vehicle=st.session_state.vehicle,
            active_route=st.session_state.active_route,
        )
        st.pyplot(fig, use_container_width=True)
        plt.close(fig)

        # Reroute alert banner if status changed
        if st.session_state.reroute_flag is not None:
            if st.session_state.reroute_flag:
                st.error("🚨 **Adaptive Reroute Triggered!** A road blockage/hazard forced an alternate detour.")
            else:
                st.info("ℹ️ **Route Stable:** Current best route remains unchanged.")

    # =================================================================
    # Column 2: Mission Actions & Road Condition Updates
    # =================================================================
    with col_ops:
        st.subheader("🚀 Mission Actions")

        btn_step, btn_full = st.columns(2)
        with btn_step:
            step_clicked = st.button("▶ Execute Next Delivery", use_container_width=True)
        with btn_full:
            full_clicked = st.button("⏩ Run Full Mission", use_container_width=True)

        # Single Delivery Step Execution
        if step_clicked:
            if st.session_state.vehicle.current_load <= 0:
                st.warning("⚠️ Vehicle has 0 supplies remaining. Cannot execute delivery.")
            else:
                # 1. Greedy choice of next feasible location
                decision = select_next_location(
                    graph=st.session_state.graph,
                    vehicle=st.session_state.vehicle,
                    locations=st.session_state.locations,
                    average_speed=DEFAULT_AVERAGE_SPEED,
                    use_effective_cost=True,
                )

                if decision is None:
                    st.warning("⚠️ No feasible target location found under current road conditions and constraints.")
                else:
                    # Check reroute against previous planned route
                    if st.session_state.previous_route and st.session_state.previous_route != decision.path:
                        st.session_state.reroute_flag = True
                        st.session_state.reroute_count += 1
                    else:
                        st.session_state.reroute_flag = False

                    # Simulate delivery
                    result = simulate_delivery(
                        vehicle=st.session_state.vehicle,
                        decision=decision,
                        average_speed=DEFAULT_AVERAGE_SPEED,
                    )
                    st.session_state.delivery_history.append(result)
                    st.session_state.last_decision = decision
                    st.session_state.active_route = decision.path
                    st.session_state.previous_route = list(decision.path)
                    st.rerun()

        # Full Mission Execution
        if full_clicked:
            if st.session_state.vehicle.current_load <= 0:
                st.warning("⚠️ Vehicle has 0 supplies remaining.")
            else:
                initial_step_count = len(st.session_state.delivery_history)
                summary = run_mission(
                    graph=st.session_state.graph,
                    vehicle=st.session_state.vehicle,
                    locations=st.session_state.locations,
                    average_speed=DEFAULT_AVERAGE_SPEED,
                    use_effective_cost=True,
                )
                for res in summary.delivery_results:
                    st.session_state.delivery_history.append(res)
                if summary.delivery_results:
                    st.session_state.active_route = summary.delivery_results[-1].route
                st.success(
                    f"Mission execution completed! Processed {len(summary.delivery_results)} delivery legs."
                )
                st.rerun()

        # Display latest delivery outcome
        if st.session_state.delivery_history:
            latest = st.session_state.delivery_history[-1]
            st.success(f"✅ **Delivery Complete** — {latest.message}")
            c1, c2, c3 = st.columns(3)
            c1.metric("Destination", latest.location_id)
            c2.metric("Delivered", f"{latest.delivered_amount} units")
            c3.metric("Arrival Time", f"{latest.arrival_time:.1f} min")
            st.write(f"**Route:** `{' -> '.join(latest.route)}` ({latest.distance:.1f} km)")

        st.divider()

        # =============================================================
        # Manual Road Condition Update (Core Demo Requirement)
        # =============================================================
        st.subheader("Road Condition Update")
        st.caption("Demonstration Scenario — simulate a road hazard (flood, debris, landslide) and observe adaptive rerouting:")

        # Extract available unique edges for dropdown
        unique_edges = get_unique_edges(st.session_state.graph)
        edge_options = [f"{u} <-> {v} (Current: {attrs['status']})" for u, v, attrs in unique_edges]

        selected_edge_str = st.selectbox("Select Road Segment:", edge_options)
        new_status = st.selectbox("Assign Road Status:", [RoadStatus.CLEAR, RoadStatus.DAMAGED, RoadStatus.BLOCKED])

        if st.button("🚨 Update Road Condition", use_container_width=True):
            # Parse selected road
            idx = edge_options.index(selected_edge_str)
            u, v, old_attrs = unique_edges[idx]

            # Record route before update for comparison
            prev_decision = select_next_location(
                graph=st.session_state.graph,
                vehicle=st.session_state.vehicle,
                locations=st.session_state.locations,
            )
            old_path = prev_decision.path if prev_decision else None

            # Mutate road status in RoadGraph
            st.session_state.graph.set_road_status(u, v, new_status, bidirectional=True)

            # Re-evaluate route after update
            new_decision = select_next_location(
                graph=st.session_state.graph,
                vehicle=st.session_state.vehicle,
                locations=st.session_state.locations,
            )
            new_path = new_decision.path if new_decision else None

            # Determine whether rerouting occurred
            rerouted = False
            if old_path and new_path:
                rerouted = (old_path != new_path)
            elif old_path and not new_path:
                rerouted = True

            st.session_state.reroute_flag = rerouted
            if rerouted:
                st.session_state.reroute_count += 1
            if new_path:
                st.session_state.active_route = new_path
                st.session_state.previous_route = new_path

            st.session_state.update_message = {
                "road": f"{u} <-> {v}",
                "new_status": new_status,
                "old_path": old_path,
                "new_path": new_path,
                "rerouted": rerouted,
            }
            st.rerun()

        if st.session_state.update_message:
            msg = st.session_state.update_message
            # Show structured reroute result card
            rerouted = msg["rerouted"]
            reroute_label = "✅ Route Recalculated" if rerouted else "ℹ️ Route Unchanged"
            box = st.container(border=True)
            box.markdown(f"**Road updated:** `{msg['road']}` → **{msg['new_status']}**")
            box.markdown(
                f"**Previous Route:** `{' -> '.join(msg['old_path']) if msg['old_path'] else 'None'}`"
            )
            box.markdown(
                f"**Updated Route:** `{' -> '.join(msg['new_path']) if msg['new_path'] else 'No feasible route'}`"
            )
            if rerouted:
                box.error(f"**Rerouted: YES** — {reroute_label}")
            else:
                box.info(f"**Rerouted: NO** — {reroute_label}")

    st.divider()

    # =================================================================
    # Section 3: Mission Statistics & Delivery History
    # =================================================================
    st.subheader("📊 Mission Statistics")
    m1, m2, m3, m4, m5, m6 = st.columns(6)

    served_count = sum(1 for loc in st.session_state.locations if loc.status == RequestStatus.SERVED)
    partially_count = sum(1 for loc in st.session_state.locations if loc.status == RequestStatus.PARTIALLY_SERVED)
    total_delivered = sum(r.delivered_amount for r in st.session_state.delivery_history if r.success)
    total_dist = sum(r.distance for r in st.session_state.delivery_history if r.success)
    total_time = sum(r.travel_time for r in st.session_state.delivery_history if r.success)

    m1.metric("Fully Served", f"{served_count} / {len(st.session_state.locations)}")
    m2.metric("Partially Served", partially_count)
    m3.metric("Supplies Delivered", f"{total_delivered} units")
    m4.metric("Total Distance", f"{total_dist:.1f} km")
    m5.metric("Total Travel Time", f"{total_time:.1f} min")
    m6.metric("Reroutes Triggered", st.session_state.reroute_count)

    # Delivery history log
    if st.session_state.delivery_history:
        with st.expander("📋 View Delivery History", expanded=False):
            log_data = []
            for i, res in enumerate(st.session_state.delivery_history, start=1):
                log_data.append({
                    "Step": i,
                    "Destination": res.location_id,
                    "Route": " -> ".join(res.route),
                    "Distance (km)": res.distance,
                    "Travel Time (min)": res.travel_time,
                    "Arrival Clock (min)": res.arrival_time,
                    "Delivered (units)": res.delivered_amount,
                    "Vehicle Load Remaining": res.remaining_vehicle_load,
                    "Status": res.location_status,
                })
            st.dataframe(log_data, use_container_width=True)


if __name__ == "__main__":
    main()
