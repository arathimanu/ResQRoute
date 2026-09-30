"""Application State Manager for ResQRoute Backend.

Holds in-memory scenario state, road graph, vehicles, depots, and locations.
Supports reset to initial state for repeatable demonstration flows.
"""

import json
import os
from typing import Dict, List, Optional, Tuple, Any

from config import SCENARIO_PATH, LOCATIONS_PATH, GRAPH_PATH, DEFAULT_SPEED_KMH, DEFAULT_SPEED_KMMIN
from src.graph import RoadGraph, RoadStatus
from src.models import Depot, Vehicle, AffectedLocation, RequestStatus
from src.risk import calculate_location_risk, RiskBreakdown
from backend.osm_loader import load_osm_road_graph


class AppState:
    _instance: Optional["AppState"] = None

    def __init__(self) -> None:
        self.graph: Optional[RoadGraph] = None
        self.node_positions: Dict[str, Dict[str, Any]] = {}
        self.scenario: Dict[str, Any] = {}
        self.depots: List[Depot] = []
        self.vehicles: List[Vehicle] = []
        self.locations: List[AffectedLocation] = []
        self.delivery_history: List[Any] = []
        self.active_route: Optional[List[str]] = None
        self.previous_route: Optional[List[str]] = None
        self.reroute_count: int = 0
        self.key_location_nodes: Dict[str, str] = {}
        self.osm_raw: Dict[str, Any] = {}

    @classmethod
    def get_instance(cls) -> "AppState":
        if cls._instance is None:
            cls._instance = AppState()
            cls._instance.initialize()
        return cls._instance

    def initialize(self, force_reset: bool = False) -> None:
        """Load scenario data, OSM road graph, facilities, and calculate risk scores."""
        # 1. Load scenario configuration
        if not os.path.exists(str(SCENARIO_PATH)):
            raise FileNotFoundError(f"Scenario file '{SCENARIO_PATH}' not found.")
        with open(SCENARIO_PATH, "r", encoding="utf-8") as f:
            self.scenario = json.load(f)

        # 2. Load OSM road graph
        self.graph, self.node_positions, self.osm_raw = load_osm_road_graph(str(GRAPH_PATH))
        self.key_location_nodes = self.osm_raw.get("key_location_nodes", {})

        # 3. Load locations data
        if not os.path.exists(str(LOCATIONS_PATH)):
            raise FileNotFoundError(f"Locations file '{LOCATIONS_PATH}' not found.")
        with open(LOCATIONS_PATH, "r", encoding="utf-8") as f:
            raw_locs = json.load(f)

        self.depots = []
        self.locations = []
        self.vehicles = []
        self.delivery_history = []
        self.active_route = None
        self.previous_route = None
        self.reroute_count = 0

        # Max population reference for normalization
        max_pop = max((item.get("population_served", 1) for item in raw_locs if item["type"] != "depot"), default=8000)

        for item in raw_locs:
            item_id = item["id"]
            # Map location ID to OSM node ID if mapped, else use item_id
            node_id = self.key_location_nodes.get(item_id, item_id)

            if item["type"] == "depot":
                depot = Depot(
                    id=node_id,
                    name=item["name"],
                    available_supplies=item.get("available_supplies", 500),
                    lat=item["lat"],
                    lon=item["lon"],
                )
                self.depots.append(depot)

                # Initialize relief truck stationed at depot
                vehicle = Vehicle(
                    id="Relief-Truck-Alpha",
                    capacity=200,
                    current_load=180,
                    base_depot=node_id,
                    current_location=node_id,
                    current_time=0.0,
                    lat=item["lat"],
                    lon=item["lon"],
                )
                self.vehicles.append(vehicle)

            else:
                # Calculate transparent scenario-based risk probability
                risk_info: RiskBreakdown = calculate_location_risk(
                    loc_lat=item["lat"],
                    loc_lon=item["lon"],
                    population_served=item.get("population_served", 1000),
                    vulnerability_score=item.get("vulnerability_score", 0.5),
                    scenario=self.scenario,
                    max_population=max_pop,
                )

                affected_loc = AffectedLocation(
                    id=node_id,
                    name=item["name"],
                    demand=item.get("demand", 50),
                    urgency=item.get("urgency", 2),
                    deadline=item.get("deadline", 180.0),
                    delivered_amount=0,
                    status=RequestStatus.UNSERVED,
                    lat=item["lat"],
                    lon=item["lon"],
                    population_served=item.get("population_served", 1000),
                    vulnerability_score=item.get("vulnerability_score", 0.5),
                    risk_probability=risk_info.probability,
                    risk_level=risk_info.risk_level,
                    risk_breakdown={
                        "label": risk_info.label,
                        "hazard_exposure": risk_info.hazard_exposure,
                        "disaster_severity": risk_info.disaster_severity,
                        "population_factor": risk_info.population_factor,
                        "vulnerability_score": risk_info.vulnerability_score,
                        "hazard_exposure_weighted": risk_info.hazard_exposure_weighted,
                        "disaster_severity_weighted": risk_info.disaster_severity_weighted,
                        "population_factor_weighted": risk_info.population_factor_weighted,
                        "vulnerability_score_weighted": risk_info.vulnerability_score_weighted,
                        "weights": risk_info.weights,
                        "raw_score": risk_info.raw_score,
                        "distance_to_hazard_km": risk_info.distance_to_hazard_km,
                    },
                )
                self.locations.append(affected_loc)

    def reset(self) -> None:
        """Reset scenario state."""
        self.initialize(force_reset=True)
