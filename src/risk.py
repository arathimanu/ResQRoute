"""Transparent Scenario-Based Risk Estimation Engine for ResQRoute.

Calculates a location's probability of being affected during a disaster scenario.

LABEL: Scenario-Based Risk Estimate
This score is an explainable simulation estimate based on static geographic exposure,
disaster severity, population density, and infrastructure vulnerability parameters.
It is NOT a real-time predictive machine learning model or sensor reading.

Formula:
  risk_probability = clamp(
      w_exposure * hazard_exposure
    + w_severity * disaster_severity
    + w_population * population_factor
    + w_vulnerability * vulnerability_score,
    0.0, 1.0
  )
"""

import math
from dataclasses import dataclass, asdict
from typing import Dict, Any, List


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance in kilometers between two lat/lon coordinates."""
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


@dataclass
class RiskBreakdown:
    label: str
    hazard_exposure: float
    disaster_severity: float
    population_factor: float
    vulnerability_score: float
    hazard_exposure_weighted: float
    disaster_severity_weighted: float
    population_factor_weighted: float
    vulnerability_score_weighted: float
    weights: Dict[str, float]
    raw_score: float
    probability: float
    risk_level: str
    distance_to_hazard_km: float


def calculate_location_risk(
    loc_lat: float,
    loc_lon: float,
    population_served: int,
    vulnerability_score: float,
    scenario: Dict[str, Any],
    max_population: int = 8000,
) -> RiskBreakdown:
    """Calculate transparent scenario-based risk probability and breakdown for a location.

    Args:
        loc_lat: Latitude of location
        loc_lon: Longitude of location
        population_served: Number of people served by the facility
        vulnerability_score: Structural/location vulnerability (0.0 to 1.0)
        scenario: Scenario dict from scenario.json
        max_population: Reference max population for normalization

    Returns:
        RiskBreakdown containing raw values, weighted terms, final probability, and risk level.
    """
    hazard_lat, hazard_lon = scenario.get("hazard_centre", [13.0100, 80.2483])
    hazard_radius_km = scenario.get("hazard_radius_km", 6.5)
    severity = scenario.get("disaster_severity", 0.8)
    weights = scenario.get("risk_weights", {
        "hazard_exposure": 0.40,
        "disaster_severity": 0.25,
        "population_factor": 0.20,
        "vulnerability_score": 0.15
    })
    thresholds = scenario.get("risk_thresholds", {"high": 0.75, "medium": 0.50})

    # 1. Geographic Hazard Exposure Factor (1.0 at hazard centre, 0.0 at/beyond hazard_radius)
    dist_km = haversine_km(loc_lat, loc_lon, hazard_lat, hazard_lon)
    hazard_exposure = max(0.0, 1.0 - (dist_km / max(0.1, hazard_radius_km)))

    # 2. Disaster Severity Factor (0.0 to 1.0)
    disaster_severity = max(0.0, min(1.0, float(severity)))

    # 3. Population Factor (normalized relative to max_population)
    population_factor = max(0.0, min(1.0, population_served / max(1.0, float(max_population))))

    # 4. Vulnerability Score (0.0 to 1.0)
    vulnerability = max(0.0, min(1.0, float(vulnerability_score)))

    # Weighted terms
    w_exp = weights.get("hazard_exposure", 0.40) * hazard_exposure
    w_sev = weights.get("disaster_severity", 0.25) * disaster_severity
    w_pop = weights.get("population_factor", 0.20) * population_factor
    w_vul = weights.get("vulnerability_score", 0.15) * vulnerability

    raw_score = w_exp + w_sev + w_pop + w_vul
    probability = round(max(0.0, min(1.0, raw_score)), 4)

    # Risk level classification
    if probability >= thresholds.get("high", 0.75):
        risk_level = "HIGH"
    elif probability >= thresholds.get("medium", 0.50):
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"

    return RiskBreakdown(
        label="Scenario-Based Risk Estimate",
        hazard_exposure=round(hazard_exposure, 4),
        disaster_severity=round(disaster_severity, 4),
        population_factor=round(population_factor, 4),
        vulnerability_score=round(vulnerability, 4),
        hazard_exposure_weighted=round(w_exp, 4),
        disaster_severity_weighted=round(w_sev, 4),
        population_factor_weighted=round(w_pop, 4),
        vulnerability_score_weighted=round(w_vul, 4),
        weights=weights,
        raw_score=round(raw_score, 4),
        probability=probability,
        risk_level=risk_level,
        distance_to_hazard_km=round(dist_km, 2),
    )
