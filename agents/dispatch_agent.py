"""Dispatch Agent - Routes emergency resources to incidents.

Part of the CrisisGrid AI LangGraph multi-agent pipeline.
Receives a master incident object from the Fusion Agent, locates the
nearest available resource unit, and dispatches it via the city graph.
"""

from datetime import datetime


# ---------------------------------------------------------------------------
# Resource-type mapping
# ---------------------------------------------------------------------------
# Maps incident resource need keywords to the exact unit type strings
# stored in state.resources.  Only explicit matches are used — no fuzzy
# inference.
RESOURCE_TYPE_MAP: dict[str, str] = {
    "Fire": "fire_truck",
    "Medical": "ambulance",
    "Police": "police",
    "Ambulance": "ambulance",
    "Fire Truck": "fire_truck",
    "fire": "fire_truck",
    "medical": "ambulance",
    "police": "police",
    "ambulance": "ambulance",
    "fire_truck": "fire_truck",
}


def _resolve_unit_type(resource_need: str) -> str | None:
    """Map an incident resource-need string to an exact unit type.

    Args:
        resource_need: A value from incident["resources_needed"],
                       e.g. "Fire", "Medical", "Police".

    Returns:
        The canonical unit type string (e.g. "fire_truck", "ambulance",
        "police"), or ``None`` if no exact mapping exists.
    """
    return RESOURCE_TYPE_MAP.get(resource_need)


def _filter_available_units(
    resources: dict,
    unit_type: str,
) -> dict:
    """Return the subset of *resources* matching *unit_type* and AVAILABLE.

    Args:
        resources: ``state.resources`` — a dict of
                   ``{unit_id: {type, status, location, ...}}``.
        unit_type: The canonical unit type to filter for.

    Returns:
        A dict ``{unit_id: unit_info}`` containing only units whose
        ``type`` matches *unit_type* and whose ``status`` is
        ``"AVAILABLE"``.
    """
    return {
        uid: info
        for uid, info in resources.items()
        if info.get("type") == unit_type and info.get("status") == "AVAILABLE"
    }


def _build_explanation(
    unit_id: str,
    location: str,
    unit_type: str,
    eta: float,
    route: list,
) -> str:
    """Build a plain-English dispatch explanation string.

    Args:
        unit_id:   ID of the dispatched unit.
        location:  Incident location (zone/node name).
        unit_type: Canonical unit type string.
        eta:       Estimated time of arrival in minutes.
        route:     Ordered list of zone nodes forming the route.

    Returns:
        Human-readable explanation of the dispatch decision.
    """
    route_str = " → ".join(str(node) for node in route)
    return (
        f"Selected {unit_id} for deployment to {location}.\n"
        f"• Closest available {unit_type} — {eta:.1f} min travel time\n"
        f"• Route: {route_str}\n"
        f"• Other {unit_type} units reserved for higher-priority scenarios\n"
        f"• ETA: {eta:.1f} min"
    )


# ---------------------------------------------------------------------------
# Main agent entry point
# ---------------------------------------------------------------------------

VALID_ZONES = {
    "downtown", "harbor", "industrial", "sector7", "north_grid",
    "central_park", "westside", "port", "eastside", "suburbs",
    "midtown", "airport",
}

DEFAULT_ZONE = "downtown"


def _normalize_location(location: str) -> str:
    """Map an incident location string to a valid city-graph zone.

    If the location is already a valid zone name, return it as-is.
    Otherwise try a case-insensitive match, then fall back to
    ``DEFAULT_ZONE`` so the dispatch can still proceed.
    """
    if location in VALID_ZONES:
        return location

    lower = location.lower().strip().replace(" ", "_")
    if lower in VALID_ZONES:
        return lower

    # Keyword heuristics for common Hindi/English terms
    _KEYWORD_MAP = {
        "hawa": "airport",  "airport": "airport",
        "bandargah": "harbor", "harbor": "harbor", "harbour": "harbor",
        "port": "port",
        "park": "central_park",
        "factory": "industrial", "industrial": "industrial",
        "north": "north_grid",
        "west": "westside",
        "east": "eastside",
        "suburb": "suburbs",
        "mid": "midtown",
        "centre": "downtown", "center": "downtown", "central": "central_park",
        "sector": "sector7",
    }
    for keyword, zone in _KEYWORD_MAP.items():
        if keyword in lower:
            return zone

    return DEFAULT_ZONE


def dispatch_agent(state: dict) -> dict:
    """Assign the nearest available resource to an incident.

    This function is designed to be called as a LangGraph node.  It reads
    the shared state produced by upstream agents (primarily the Fusion
    Agent), performs resource selection and routing, then writes dispatch
    results back to state.

    **MVP constraint:** only ONE resource is dispatched per invocation,
    even if the incident requires multiple resource types.

    Args:
        state: LangGraph state object containing at minimum:
            - ``incidents``  – list of incident dicts from the Fusion Agent.
            - ``incident``   – single dict (legacy / fallback).
            - ``resources``  – dict of all units keyed by unit ID.
            - ``city_graph`` – a CityGraph object exposing
              ``find_nearest_unit(location, units_dict)`` and
              ``get_shortest_path(start, end)``.

    Returns:
        The mutated *state* dict with:
            - ``resources[unit_id]["status"]`` set to ``"DISPATCHED"``.
            - A new entry appended to ``dispatch_log``.
            - ``agent_reasoning["dispatch"]`` set to an explanation string.
    """
    # ── Extract incident details ──────────────────────────────────────
    if "incidents" in state and state["incidents"]:
        incident: dict = state["incidents"][-1]
    elif "incident" in state and state.get("incident"):
        incident = state["incident"]
    else:
        state.setdefault("agent_reasoning", {})["dispatch"] = (
            "No incident data available — nothing to dispatch."
        )
        return state

    incident_id: str = incident.get("id", incident.get("master_incident_id", "unknown"))
    raw_location: str = incident.get("location", "downtown")
    resources_needed: list[str] = incident.get("resources_needed", [])

    resources: dict = state.get("resources", {})
    city_graph = state.get("city_graph")

    # Ensure mutable containers exist on state
    if "dispatch_log" not in state:
        state["dispatch_log"] = []
    if "agent_reasoning" not in state:
        state["agent_reasoning"] = {}

    if city_graph is None:
        state["agent_reasoning"]["dispatch"] = (
            "NO CITY GRAPH - ESCALATION REQUIRED. "
            "Cannot route without a city graph."
        )
        return state

    # ── Validate / normalise location against graph zones ─────────────
    incident_location = _normalize_location(raw_location)

    # ── Resolve the first resource need to a unit type ────────────────
    required_type: str | None = None
    for need in resources_needed:
        required_type = _resolve_unit_type(need)
        if required_type is not None:
            break

    if required_type is None:
        # None of the listed needs mapped to a known unit type.
        state["agent_reasoning"]["dispatch"] = (
            "NO AVAILABLE UNITS - ESCALATION REQUIRED. "
            f"Could not map any resource need {resources_needed} to a "
            "known unit type."
        )
        return state

    # ── Filter for available units of the required type ───────────────
    available_units: dict = _filter_available_units(resources, required_type)

    if not available_units:
        state["agent_reasoning"]["dispatch"] = (
            "NO AVAILABLE UNITS - ESCALATION REQUIRED"
        )
        return state

    # ── Find the nearest available unit via the city graph ────────────
    unit_id, distance, path = city_graph.find_nearest_unit(
        incident_location,
        available_units,
    )

    if unit_id is None:
        state["agent_reasoning"]["dispatch"] = (
            "NO PATH AVAILABLE - ESCALATION REQUIRED. "
            f"Could not find a valid route to location '{incident_location}' "
            f"(original: '{raw_location}')."
        )
        return state

    # ── Calculate ETA (distance already represents travel_time in min) ─
    eta: float = float(distance)

    # ── Update unit status ────────────────────────────────────────────
    state["resources"][unit_id]["status"] = "DISPATCHED"

    # ── Build & append dispatch log entry ─────────────────────────────
    dispatch_entry: dict = {
        "incident_id": incident_id,
        "unit_id": unit_id,
        "route": path,
        "eta": eta,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    state["dispatch_log"].append(dispatch_entry)

    # ── Record agent reasoning ────────────────────────────────────────
    state["agent_reasoning"]["dispatch"] = _build_explanation(
        unit_id=unit_id,
        location=incident_location,
        unit_type=required_type,
        eta=eta,
        route=path,
    )

    return state
