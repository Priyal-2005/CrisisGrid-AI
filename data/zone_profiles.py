"""Zone Risk Profiles — Infrastructure-aware intelligence for CrisisGrid AI.

Each city zone has a risk profile capturing:
- Population density (affects casualty potential)
- Hazard level (chemical, industrial, environmental)
- Industrial risk (factory/chemical plant presence)
- Infrastructure importance (critical infrastructure multiplier)
- Congestion score (affects ETA and evacuation)
- Evacuation difficulty (limited exits, security, terrain)
- Special flags (chemical_sites, medical_facilities, schools)

Used by:
- severity_engine.py — zone-adjusted severity scoring
- dispatch_agent.py — dispatch prioritization
- strategy_agent.py — cascade and infrastructure reasoning
- city_graph.py — dynamic traffic conditions
"""

from __future__ import annotations


# ---------------------------------------------------------------------------
# Zone risk profiles (all values normalized 0.0 – 1.0)
# ---------------------------------------------------------------------------

ZONE_PROFILES: dict[str, dict] = {
    "downtown": {
        "population_density": 0.90,
        "hazard_level": 0.35,
        "industrial_risk": 0.10,
        "infrastructure_importance": 0.70,
        "congestion_score": 0.85,
        "evacuation_difficulty": 0.60,
        "chemical_sites": False,
        "medical_facilities": True,
        "schools": True,
        "description": "Dense commercial and residential hub — high population, heavy traffic",
    },
    "harbor": {
        "population_density": 0.40,
        "hazard_level": 0.55,
        "industrial_risk": 0.50,
        "infrastructure_importance": 0.60,
        "congestion_score": 0.45,
        "evacuation_difficulty": 0.65,
        "chemical_sites": False,
        "medical_facilities": False,
        "schools": False,
        "description": "Harbor area — shipping, fuel storage, moderate industrial activity",
    },
    "industrial": {
        "population_density": 0.25,
        "hazard_level": 0.90,
        "industrial_risk": 0.95,
        "infrastructure_importance": 0.55,
        "congestion_score": 0.35,
        "evacuation_difficulty": 0.75,
        "chemical_sites": True,
        "medical_facilities": False,
        "schools": False,
        "description": "Industrial zone — chemical plants, factories, high hazmat risk",
    },
    "sector7": {
        "population_density": 0.65,
        "hazard_level": 0.30,
        "industrial_risk": 0.15,
        "infrastructure_importance": 0.45,
        "congestion_score": 0.55,
        "evacuation_difficulty": 0.40,
        "chemical_sites": False,
        "medical_facilities": True,
        "schools": True,
        "description": "Mixed-use residential sector — schools, clinics, moderate density",
    },
    "north_grid": {
        "population_density": 0.55,
        "hazard_level": 0.25,
        "industrial_risk": 0.10,
        "infrastructure_importance": 0.40,
        "congestion_score": 0.50,
        "evacuation_difficulty": 0.35,
        "chemical_sites": False,
        "medical_facilities": False,
        "schools": True,
        "description": "Northern residential grid — suburban feel, schools nearby",
    },
    "central_park": {
        "population_density": 0.70,
        "hazard_level": 0.20,
        "industrial_risk": 0.05,
        "infrastructure_importance": 0.50,
        "congestion_score": 0.60,
        "evacuation_difficulty": 0.30,
        "chemical_sites": False,
        "medical_facilities": True,
        "schools": True,
        "description": "Central park area — open spaces, high foot traffic, nearby hospitals",
    },
    "westside": {
        "population_density": 0.60,
        "hazard_level": 0.30,
        "industrial_risk": 0.20,
        "infrastructure_importance": 0.45,
        "congestion_score": 0.55,
        "evacuation_difficulty": 0.45,
        "chemical_sites": False,
        "medical_facilities": False,
        "schools": True,
        "description": "Western residential and light commercial area",
    },
    "port": {
        "population_density": 0.30,
        "hazard_level": 0.65,
        "industrial_risk": 0.60,
        "infrastructure_importance": 0.70,
        "congestion_score": 0.40,
        "evacuation_difficulty": 0.70,
        "chemical_sites": True,
        "medical_facilities": False,
        "schools": False,
        "description": "Port — cargo, fuel depots, hazardous material transit, critical logistics",
    },
    "eastside": {
        "population_density": 0.50,
        "hazard_level": 0.35,
        "industrial_risk": 0.25,
        "infrastructure_importance": 0.40,
        "congestion_score": 0.45,
        "evacuation_difficulty": 0.40,
        "chemical_sites": False,
        "medical_facilities": True,
        "schools": False,
        "description": "Eastern mixed area — light industry and residential",
    },
    "suburbs": {
        "population_density": 0.45,
        "hazard_level": 0.15,
        "industrial_risk": 0.05,
        "infrastructure_importance": 0.25,
        "congestion_score": 0.30,
        "evacuation_difficulty": 0.20,
        "chemical_sites": False,
        "medical_facilities": False,
        "schools": True,
        "description": "Suburban residential — low density, easy evacuation",
    },
    "midtown": {
        "population_density": 0.80,
        "hazard_level": 0.30,
        "industrial_risk": 0.10,
        "infrastructure_importance": 0.60,
        "congestion_score": 0.75,
        "evacuation_difficulty": 0.55,
        "chemical_sites": False,
        "medical_facilities": True,
        "schools": True,
        "description": "Midtown — dense commercial, hospitals, high pedestrian traffic",
    },
    "airport": {
        "population_density": 0.70,
        "hazard_level": 0.60,
        "industrial_risk": 0.30,
        "infrastructure_importance": 0.95,
        "congestion_score": 0.80,
        "evacuation_difficulty": 0.90,
        "chemical_sites": False,
        "medical_facilities": True,
        "schools": False,
        "description": "Airport — critical transport hub, fuel storage, security-restricted evacuation",
    },
}

# Default profile for unrecognized zones
DEFAULT_ZONE_PROFILE: dict = {
    "population_density": 0.50,
    "hazard_level": 0.30,
    "industrial_risk": 0.15,
    "infrastructure_importance": 0.40,
    "congestion_score": 0.50,
    "evacuation_difficulty": 0.40,
    "chemical_sites": False,
    "medical_facilities": False,
    "schools": False,
    "description": "Unknown zone — default risk profile applied",
}


def get_zone_profile(zone: str) -> dict:
    """Return the risk profile for a given zone, falling back to defaults."""
    return ZONE_PROFILES.get(zone.lower().strip(), DEFAULT_ZONE_PROFILE)


def get_zone_risk_summary(zone: str) -> str:
    """Return a human-readable risk summary for a zone."""
    p = get_zone_profile(zone)
    flags = []
    if p["population_density"] >= 0.7:
        flags.append("HIGH POPULATION DENSITY")
    if p["hazard_level"] >= 0.6:
        flags.append("HIGH HAZARD ZONE")
    if p["industrial_risk"] >= 0.7:
        flags.append("INDUSTRIAL RISK")
    if p["infrastructure_importance"] >= 0.8:
        flags.append("CRITICAL INFRASTRUCTURE")
    if p["chemical_sites"]:
        flags.append("CHEMICAL SITES PRESENT")
    if p["evacuation_difficulty"] >= 0.7:
        flags.append("DIFFICULT EVACUATION")
    if p["medical_facilities"]:
        flags.append("MEDICAL FACILITIES NEARBY")
    if p["schools"]:
        flags.append("SCHOOLS IN ZONE")

    if not flags:
        return f"{zone}: Standard risk profile. {p['description']}"
    return f"{zone}: {', '.join(flags)}. {p['description']}"
