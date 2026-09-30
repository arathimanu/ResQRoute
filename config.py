"""Central configuration constants for ResQRoute system."""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

# Data file paths
SCENARIO_PATH = DATA_DIR / "scenario.json"
LOCATIONS_PATH = DATA_DIR / "locations.json"
GRAPH_PATH = DATA_DIR / "chennai_graph.json"

# Routing parameters
DAMAGED_PENALTY: float = 1.5
DEFAULT_SPEED_KMH: float = 30.0  # 30 km/h average relief travel speed in urban flood conditions
DEFAULT_SPEED_KMMIN: float = DEFAULT_SPEED_KMH / 60.0  # 0.5 km/min

# System labelling
SYSTEM_TITLE = "ResQRoute — Disaster Response Decision Support and Adaptive Routing System"
RISK_LABEL = "Scenario-Based Risk Estimate"
