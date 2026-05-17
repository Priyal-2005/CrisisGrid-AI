"""Multi-Factor Severity Scoring Engine — CrisisGrid AI.

Replaces the simplistic LOW/MEDIUM/CRITICAL classification with a
dynamic 0-100 severity score computed from multiple weighted factors.

Score mapping:
    0-35   → LOW
    36-65  → MEDIUM
    66-85  → HIGH
    86-100 → CRITICAL

Used by:
- fusion_agent.py   — replaces call-count escalation with multi-factor scoring
- dispatch_agent.py — priority ordering within severity tiers
- strategy_agent.py — cascade risk assessment

This module is pure computation — no LLM calls, no side effects.
"""

from __future__ import annotations

import math
from data.zone_profiles import get_zone_profile


# ---------------------------------------------------------------------------
# Incident type base scores (intrinsic danger of the incident category)
# ---------------------------------------------------------------------------

INCIDENT_TYPE_SCORES: dict[str, int] = {
    # Fires
    "fire": 65,
    "industrial_fire": 85,
    "chemical_fire": 92,
    "building_fire": 70,
    "residential_fire": 60,
    "wildfire": 75,

    # Explosions
    "explosion": 90,
    "chemical_explosion": 96,
    "gas_explosion": 88,
    "industrial_explosion": 94,

    # Hazmat
    "chemical_spill": 80,
    "gas_leak": 72,
    "toxic_release": 88,
    "radiation": 95,

    # Natural disasters
    "earthquake": 78,
    "flood": 55,
    "tsunami": 92,
    "landslide": 70,

    # Transport
    "accident": 55,
    "multi_vehicle_accident": 70,
    "train_derailment": 85,
    "plane_crash": 95,

    # Medical
    "medical": 40,
    "cardiac_arrest": 65,
    "mass_casualty": 90,

    # Other
    "building_collapse": 85,
    "structural_failure": 75,
    "unknown": 45,
}


# ---------------------------------------------------------------------------
# Time sensitivity profiles (minutes until outcome degrades significantly)
# ---------------------------------------------------------------------------

TIME_SENSITIVITY: dict[str, int] = {
    "cardiac_arrest": 100,      # 4 min window
    "explosion": 95,            # Immediate secondary blast risk
    "chemical_explosion": 95,
    "toxic_release": 90,        # Plume exposure grows rapidly
    "building_collapse": 85,    # Golden hour for trapped victims
    "fire": 80,                 # Spread rate doubles every 3-5 min
    "chemical_fire": 90,
    "industrial_fire": 85,
    "gas_leak": 75,
    "earthquake": 70,           # Aftershock risk + trapped persons
    "flood": 45,                # Usually slower onset
    "accident": 60,
    "medical": 50,
    "unknown": 50,
}


# ---------------------------------------------------------------------------
# Resource requirements by incident type (base quantities)
# ---------------------------------------------------------------------------

INCIDENT_RESOURCE_REQUIREMENTS: dict[str, dict[str, int]] = {
    "fire": {"fire_truck": 2, "ambulance": 1, "police": 1},
    "industrial_fire": {"fire_truck": 3, "ambulance": 2, "police": 2},
    "chemical_fire": {"fire_truck": 3, "ambulance": 3, "police": 2},
    "building_fire": {"fire_truck": 2, "ambulance": 2, "police": 1},
    "explosion": {"fire_truck": 3, "ambulance": 3, "police": 2},
    "chemical_explosion": {"fire_truck": 3, "ambulance": 4, "police": 2},
    "industrial_explosion": {"fire_truck": 3, "ambulance": 4, "police": 2},
    "gas_explosion": {"fire_truck": 2, "ambulance": 3, "police": 2},
    "gas_leak": {"fire_truck": 1, "ambulance": 1, "police": 1},
    "chemical_spill": {"fire_truck": 2, "ambulance": 2, "police": 2},
    "toxic_release": {"fire_truck": 2, "ambulance": 3, "police": 2},
    "accident": {"ambulance": 2, "police": 1},
    "multi_vehicle_accident": {"ambulance": 3, "police": 2, "fire_truck": 1},
    "flood": {"police": 2, "ambulance": 1},
    "earthquake": {"fire_truck": 2, "ambulance": 3, "police": 2},
    "building_collapse": {"fire_truck": 2, "ambulance": 3, "police": 2},
    "medical": {"ambulance": 1},
    "cardiac_arrest": {"ambulance": 1},
    "mass_casualty": {"ambulance": 5, "police": 3, "fire_truck": 1},
    "unknown": {"ambulance": 1, "police": 1},
}


# ---------------------------------------------------------------------------
# Spread risk by incident type (probability of expanding/cascading)
# ---------------------------------------------------------------------------

SPREAD_RISK: dict[str, int] = {
    "fire": 70,
    "industrial_fire": 85,
    "chemical_fire": 95,
    "building_fire": 65,
    "explosion": 80,
    "chemical_explosion": 95,
    "industrial_explosion": 90,
    "gas_explosion": 85,
    "gas_leak": 60,
    "chemical_spill": 70,
    "toxic_release": 85,
    "flood": 55,
    "earthquake": 50,
    "building_collapse": 30,
    "accident": 15,
    "medical": 5,
    "unknown": 30,
}


# ---------------------------------------------------------------------------
# Factor weights (must sum to 1.0)
# ---------------------------------------------------------------------------

FACTOR_WEIGHTS: dict[str, float] = {
    "incident_type_base": 0.22,
    "casualty_factor": 0.18,
    "spread_risk": 0.10,
    "hazmat_risk": 0.10,
    "infrastructure_criticality": 0.10,
    "population_density": 0.08,
    "time_sensitivity": 0.07,
    "corroboration_confidence": 0.05,
    "cascade_probability": 0.05,
    "evacuation_difficulty": 0.05,
}


# ---------------------------------------------------------------------------
# Core severity computation
# ---------------------------------------------------------------------------

def _casualty_score(injured_count: int) -> int:
    """Map injured count to a 0-100 factor score."""
    if injured_count <= 0:
        return 10
    if injured_count <= 2:
        return 40
    if injured_count <= 5:
        return 60
    if injured_count <= 10:
        return 75
    if injured_count <= 20:
        return 88
    return 95  # Mass casualty


def _resolve_incident_type(raw_type: str, context: dict | None = None) -> str:
    """Map raw incident type to the most specific known type.

    Uses context clues (summary, zone) to upgrade generic types.
    For example, a "fire" in the "industrial" zone becomes "industrial_fire".

    Generic types (fire, explosion, accident, medical) ALWAYS go through
    context-based upgrading even though they exist in INCIDENT_TYPE_SCORES,
    because context can resolve them to more specific (higher-severity) types.
    """
    t = raw_type.lower().strip().replace(" ", "_")

    # Context-based upgrading
    summary = (context or {}).get("summary", "").lower()
    zone = (context or {}).get("location", "").lower()

    # --- Types that should always attempt context-based upgrade ---

    if t == "fire":
        if any(kw in summary for kw in ["chemical", "hazmat", "toxic"]):
            return "chemical_fire"
        if any(kw in summary for kw in ["factory", "industrial", "plant", "warehouse"]):
            return "industrial_fire"
        if zone in ("industrial", "port"):
            return "industrial_fire"
        if any(kw in summary for kw in ["building", "floor", "trapped", "storey", "manzil"]):
            return "building_fire"
        return "fire"

    if t in ("explosion", "blast"):
        if any(kw in summary for kw in ["chemical", "hazmat", "toxic"]):
            return "chemical_explosion"
        if any(kw in summary for kw in ["factory", "industrial", "plant"]):
            return "industrial_explosion"
        if zone in ("industrial", "port"):
            return "industrial_explosion"
        if any(kw in summary for kw in ["gas", "cylinder", "lpg"]):
            return "gas_explosion"
        return "explosion"

    if t == "accident":
        if any(kw in summary for kw in ["multiple", "multi", "bus", "truck", "pile"]):
            return "multi_vehicle_accident"
        return "accident"

    if t == "medical":
        if any(kw in summary for kw in ["heart", "cardiac", "chest pain"]):
            return "cardiac_arrest"
        if any(kw in summary for kw in ["mass", "multiple casualt"]):
            return "mass_casualty"
        return "medical"

    # --- Already-specific types — return if known ---
    if t in INCIDENT_TYPE_SCORES:
        return t

    # Fallback
    return "unknown"


def _hazmat_score(incident_type: str, zone: str) -> int:
    """Compute hazardous material risk score."""
    zone_profile = get_zone_profile(zone)
    base = 0

    # Incident-type based hazmat
    if "chemical" in incident_type:
        base = 90
    elif "gas" in incident_type or "toxic" in incident_type:
        base = 75
    elif "industrial" in incident_type:
        base = 60
    elif incident_type in ("fire", "building_fire"):
        base = 20  # Smoke inhalation risk
    elif "explosion" in incident_type:
        base = 50
    else:
        base = 5

    # Zone chemical site amplifier
    if zone_profile.get("chemical_sites"):
        base = min(100, int(base * 1.4))

    # Zone industrial risk amplifier
    zone_industrial = zone_profile.get("industrial_risk", 0)
    if zone_industrial >= 0.7:
        base = min(100, int(base * 1.2))

    return min(100, base)


def _cascade_probability(incident_type: str, zone: str, severity_so_far: float) -> int:
    """Estimate probability of secondary/cascading disasters."""
    zone_profile = get_zone_profile(zone)
    base = SPREAD_RISK.get(incident_type, 30)

    # Chemical sites amplify cascade risk
    if zone_profile.get("chemical_sites") and "fire" in incident_type:
        base = min(100, base + 25)

    # High infrastructure importance = more cascade impact
    infra = zone_profile.get("infrastructure_importance", 0.4)
    if infra >= 0.8:
        base = min(100, base + 15)

    # Already-high severity amplifies cascade concern
    if severity_so_far >= 75:
        base = min(100, base + 10)

    return min(100, base)


def compute_severity_score(
    incident_type: str,
    location: str,
    injured_count: int = 0,
    duplicate_count: int = 1,
    confidence_score: int = 50,
    summary: str = "",
) -> dict:
    """Compute a multi-factor severity score for an incident.

    Args:
        incident_type: Raw incident type from triage.
        location: City zone name.
        injured_count: Number of known casualties.
        duplicate_count: Number of corroborating calls.
        confidence_score: Fusion agent confidence (0-100).
        summary: Combined incident summary text.

    Returns:
        dict with:
            - severity_score (int, 0-100)
            - severity_label (str: LOW / MEDIUM / HIGH / CRITICAL)
            - factors (dict of individual factor scores)
            - resolved_type (str: most specific incident type)
            - required_resources (dict of resource type → count)
            - explanation (str: human-readable breakdown)
    """
    context = {"summary": summary, "location": location}
    resolved_type = _resolve_incident_type(incident_type, context)
    zone_profile = get_zone_profile(location)

    # --- Compute individual factors ---

    type_base = INCIDENT_TYPE_SCORES.get(resolved_type, 45)
    casualty = _casualty_score(injured_count)
    spread = SPREAD_RISK.get(resolved_type, 30)
    hazmat = _hazmat_score(resolved_type, location)
    infra = int(zone_profile.get("infrastructure_importance", 0.4) * 100)
    pop_density = int(zone_profile.get("population_density", 0.5) * 100)
    time_sens = TIME_SENSITIVITY.get(resolved_type, 50)
    corroboration = min(100, confidence_score + (duplicate_count - 1) * 12)
    evac_diff = int(zone_profile.get("evacuation_difficulty", 0.4) * 100)

    # Cascade is computed using partial severity for feedback
    partial_severity = (
        type_base * FACTOR_WEIGHTS["incident_type_base"]
        + casualty * FACTOR_WEIGHTS["casualty_factor"]
        + spread * FACTOR_WEIGHTS["spread_risk"]
    )
    cascade = _cascade_probability(resolved_type, location, partial_severity)

    # --- Weighted sum ---

    factors = {
        "incident_type_base": type_base,
        "casualty_factor": casualty,
        "spread_risk": spread,
        "hazmat_risk": hazmat,
        "infrastructure_criticality": infra,
        "population_density": pop_density,
        "time_sensitivity": time_sens,
        "corroboration_confidence": corroboration,
        "cascade_probability": cascade,
        "evacuation_difficulty": evac_diff,
    }

    raw_score = sum(
        factors[f] * FACTOR_WEIGHTS[f] for f in FACTOR_WEIGHTS
    )
    severity_score = max(0, min(100, int(round(raw_score))))

    # --- Map to label ---

    if severity_score >= 86:
        severity_label = "CRITICAL"
    elif severity_score >= 66:
        severity_label = "HIGH"
    elif severity_score >= 36:
        severity_label = "MEDIUM"
    else:
        severity_label = "LOW"

    # --- Resource requirements ---

    base_resources = dict(
        INCIDENT_RESOURCE_REQUIREMENTS.get(resolved_type, {"ambulance": 1, "police": 1})
    )

    # Scale ambulances by casualty count
    if injured_count > 3:
        base_resources["ambulance"] = max(
            base_resources.get("ambulance", 1),
            min(5, math.ceil(injured_count / 3)),
        )

    # Critical incidents get resource multiplier
    if severity_score >= 86:
        for rtype in base_resources:
            base_resources[rtype] = min(5, base_resources[rtype] + 1)

    # --- Explanation ---

    explanation_parts = []
    sorted_factors = sorted(factors.items(), key=lambda x: x[1] * FACTOR_WEIGHTS.get(x[0], 0), reverse=True)
    top_factors = sorted_factors[:3]
    for fname, fval in top_factors:
        weight = FACTOR_WEIGHTS.get(fname, 0)
        contribution = fval * weight
        explanation_parts.append(
            f"{fname.replace('_', ' ').title()}: {fval}/100 (weight {weight:.0%}, contributes {contribution:.1f})"
        )

    zone_flags = []
    if zone_profile.get("chemical_sites"):
        zone_flags.append("CHEMICAL SITES")
    if zone_profile.get("infrastructure_importance", 0) >= 0.8:
        zone_flags.append("CRITICAL INFRASTRUCTURE")
    if zone_profile.get("population_density", 0) >= 0.7:
        zone_flags.append("HIGH POPULATION")

    explanation = (
        f"Severity Score: {severity_score}/100 → {severity_label}. "
        f"Resolved type: {resolved_type}. "
        f"Top factors: {'; '.join(explanation_parts)}. "
    )
    if zone_flags:
        explanation += f"Zone flags: {', '.join(zone_flags)}. "
    if injured_count > 0:
        explanation += f"Casualties reported: {injured_count}. "
    if duplicate_count > 1:
        explanation += f"Corroborated by {duplicate_count} callers (confidence {corroboration}%). "

    return {
        "severity_score": severity_score,
        "severity_label": severity_label,
        "factors": factors,
        "resolved_type": resolved_type,
        "required_resources": base_resources,
        "explanation": explanation,
    }


def compare_incidents(incidents: list[dict]) -> list[dict]:
    """Sort incidents by severity_score descending for dispatch prioritization.

    Each incident dict must have a 'severity_score' key.
    Returns the same list sorted in-place.
    """
    return sorted(incidents, key=lambda x: x.get("severity_score", 0), reverse=True)
