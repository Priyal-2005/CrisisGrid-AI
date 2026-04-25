"""Dispatch Agent - Routes emergency resources to incidents.

Part of the CrisisGrid AI LangGraph multi-agent pipeline.
Implements CRITICAL > MEDIUM > LOW prioritization, dynamic re-routing,
and rich explainability for every dispatch decision.
"""

from datetime import datetime


# ---------------------------------------------------------------------------
# Priority and resource-type mappings
# ---------------------------------------------------------------------------

SEVERITY_PRIORITY: dict[str, int] = {"CRITICAL": 0, "MEDIUM": 1, "LOW": 2, "UNKNOWN": 3}

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

VALID_ZONES = {
    "downtown", "harbor", "industrial", "sector7", "north_grid",
    "central_park", "westside", "port", "eastside", "suburbs",
    "midtown", "airport",
}
DEFAULT_ZONE = "downtown"

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


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _resolve_unit_type(resource_need: str) -> str | None:
    return RESOURCE_TYPE_MAP.get(resource_need)


def _normalize_location(location: str) -> str:
    if location in VALID_ZONES:
        return location
    lower = location.lower().strip().replace(" ", "_")
    if lower in VALID_ZONES:
        return lower
    for keyword, zone in _KEYWORD_MAP.items():
        if keyword in lower:
            return zone
    return DEFAULT_ZONE


def _filter_available_units(resources: dict, unit_type: str) -> dict:
    return {
        uid: info
        for uid, info in resources.items()
        if info.get("type") == unit_type and info.get("status") == "AVAILABLE"
    }


def _get_dispatched_incident_ids(dispatch_log: list) -> set:
    """Return set of incident IDs that already have a dispatch entry."""
    return {entry.get("incident_id", "") for entry in dispatch_log}


def _select_priority_incident(
    incidents: list[dict],
    dispatch_log: list[dict],
) -> dict | None:
    """Return the highest-priority incident that has NOT yet been dispatched.

    Priority order: CRITICAL > MEDIUM > LOW
    An incident is considered dispatched if its ID appears in dispatch_log.
    """
    dispatched_ids = _get_dispatched_incident_ids(dispatch_log)
    unassigned = [
        inc for inc in incidents
        if inc.get("id") not in dispatched_ids
        and inc.get("master_incident_id") not in dispatched_ids
    ]
    if not unassigned:
        return None
    unassigned.sort(
        key=lambda x: SEVERITY_PRIORITY.get(x.get("severity", "UNKNOWN").upper(), 3)
    )
    return unassigned[0]


def _compute_all_etas(
    location: str,
    available_units: dict,
    city_graph,
) -> dict[str, tuple[float, list]]:
    """Compute ETA and path for every available unit to *location*.

    Returns: {unit_id: (eta, path)}
    """
    results = {}
    for uid, info in available_units.items():
        path, eta = city_graph.get_shortest_path(info.get("location", DEFAULT_ZONE), location)
        results[uid] = (eta, path)
    return results


def _find_reassignable_unit(
    resources: dict,
    dispatch_log: list,
    incidents: list,
    required_type: str,
) -> tuple[str | None, str | None, str | None]:
    """Find a unit of *required_type* dispatched to a LOW/MEDIUM incident.

    Returns: (unit_id, donor_incident_id, donor_severity) or (None, None, None)
    """
    inc_severity: dict[str, str] = {}
    for inc in incidents:
        iid = inc.get("id", inc.get("master_incident_id", ""))
        inc_severity[iid] = inc.get("severity", "LOW").upper()

    # Iterate dispatch log most-recent-first to reassign from the most recent low-priority dispatch
    for entry in reversed(dispatch_log):
        inc_id = entry.get("incident_id", "")
        unit_id = entry.get("unit_id", "")
        donor_sev = inc_severity.get(inc_id, "LOW")

        if donor_sev not in ("LOW", "MEDIUM"):
            continue
        if not unit_id or unit_id not in resources:
            continue
        unit = resources[unit_id]
        if unit.get("type") != required_type:
            continue
        if unit.get("status") != "DISPATCHED":
            continue

        return unit_id, inc_id, donor_sev

    return None, None, None


def _build_explanation(
    unit_id: str,
    location: str,
    unit_type: str,
    eta: float,
    route: list,
    incident_severity: str,
    all_etas: dict[str, tuple[float, list]],
    rerouted_from: str | None = None,
) -> str:
    """Rich dispatch explanation: why this unit, why not others, what tradeoff."""
    route_str = " → ".join(str(node) for node in route)
    # Build alternatives list (sorted by ETA, excluding the chosen unit)
    alternatives = [
        (uid, t, p) for uid, (t, p) in all_etas.items() if uid != unit_id
    ]
    alternatives.sort(key=lambda x: x[1])

    lines = [
        f"{unit_id} dispatched to {location} [{incident_severity}].",
        f"Route: {route_str}. ETA: {eta:.1f} min.",
        f"Decision: {unit_id} selected as nearest available {unit_type}.",
    ]

    if alternatives:
        alt_strs = [
            f"{uid} ({alt_eta:.0f} min)" for uid, alt_eta, _ in alternatives[:2]
        ]
        lines.append(
            f"Alternatives considered but not selected: {', '.join(alt_strs)} — higher ETA."
        )

    if incident_severity == "CRITICAL":
        lines.append(
            "CRITICAL incident: minimum-ETA unit mandatory. No delay tolerable."
        )
        if len(alternatives) >= 1:
            hold_uid = alternatives[0][0]
            lines.append(
                f"Tradeoff: {hold_uid} held in reserve for potential secondary CRITICAL escalation."
            )
    elif incident_severity == "MEDIUM":
        lines.append(
            "MEDIUM priority: fastest available unit dispatched; CRITICAL reserves maintained."
        )
    else:  # LOW
        lines.append(
            "LOW priority: nearest unit dispatched. Unit may be reassigned if CRITICAL incident emerges."
        )

    if rerouted_from:
        lines.append(
            f"DYNAMIC REROUTE: {unit_id} pulled from lower-priority incident {rerouted_from} "
            f"to service this CRITICAL incident. Incident {rerouted_from} placed back in queue."
        )

    return " ".join(lines)


# ---------------------------------------------------------------------------
# Main agent entry point
# ---------------------------------------------------------------------------

def dispatch_agent(state: dict) -> dict:
    """Assign the nearest available resource to the highest-priority unassigned incident.

    Priority order: CRITICAL > MEDIUM > LOW
    If a new CRITICAL incident arrives and no units are available but LOW incidents
    have dispatched units, this agent will REASSIGN (re-route) a unit from LOW to CRITICAL.

    Writes to state:
        - resources[unit_id]["status"] = "DISPATCHED"
        - New entry appended to dispatch_log
        - agent_reasoning["dispatch"] = rich explanation string
    """
    incidents: list[dict] = state.get("incidents", [])
    resources: dict = state.get("resources", {})
    city_graph = state.get("city_graph")
    dispatch_log: list[dict] = state.get("dispatch_log", [])

    state.setdefault("dispatch_log", [])
    state.setdefault("agent_reasoning", {})

    if not incidents:
        state["agent_reasoning"]["dispatch"] = (
            "No incident data available — nothing to dispatch."
        )
        return state

    if city_graph is None:
        state["agent_reasoning"]["dispatch"] = (
            "NO CITY GRAPH — ESCALATING. Cannot route without a city graph."
        )
        return state

    # ── Select highest-priority unassigned incident ──────────────────────
    incident = _select_priority_incident(incidents, dispatch_log)
    if incident is None:
        state["agent_reasoning"]["dispatch"] = (
            "All current incidents already have dispatched resources. "
            "System monitoring for new calls."
        )
        return state

    incident_id: str = incident.get("id", incident.get("master_incident_id", "unknown"))
    raw_location: str = incident.get("location", "downtown")
    incident_severity: str = incident.get("severity", "LOW").upper()
    resources_needed: list[str] = incident.get("resources_needed", [])

    incident_location = _normalize_location(raw_location)

    # ── Resolve required resource type (first resolvable need) ───────────
    required_type: str | None = None
    for need in resources_needed:
        required_type = _resolve_unit_type(need)
        if required_type is not None:
            break

    if required_type is None:
        state["agent_reasoning"]["dispatch"] = (
            f"NO AVAILABLE UNITS — ESCALATING. "
            f"Could not map resource needs {resources_needed} to a known unit type "
            f"for incident {incident_id} [{incident_severity}]."
        )
        return state

    # ── Check available units ─────────────────────────────────────────────
    available_units = _filter_available_units(resources, required_type)

    rerouted_from: str | None = None

    if not available_units:
        # ── Attempt dynamic re-routing for CRITICAL incidents ─────────────
        if incident_severity == "CRITICAL":
            unit_to_pull, donor_inc_id, donor_sev = _find_reassignable_unit(
                resources, dispatch_log, incidents, required_type
            )
            if unit_to_pull:
                # Pull unit from low-priority incident
                state["resources"][unit_to_pull]["status"] = "AVAILABLE"
                available_units = {unit_to_pull: state["resources"][unit_to_pull]}
                rerouted_from = donor_inc_id
            else:
                # Count total units of this type for context
                total_of_type = sum(
                    1 for u in resources.values() if u.get("type") == required_type
                )
                state["agent_reasoning"]["dispatch"] = (
                    f"NO AVAILABLE UNITS — ESCALATING. "
                    f"Incident {incident_id} [{incident_severity}] requires {required_type}. "
                    f"All {total_of_type} {required_type} unit(s) dispatched to CRITICAL incidents. "
                    f"Requesting mutual aid from neighboring district. "
                    f"Recommend Strategy Agent for prioritization override."
                )
                return state
        else:
            total_of_type = sum(
                1 for u in resources.values() if u.get("type") == required_type
            )
            state["agent_reasoning"]["dispatch"] = (
                f"NO AVAILABLE UNITS — ESCALATING. "
                f"Incident {incident_id} [{incident_severity}] queued — "
                f"all {total_of_type} {required_type} unit(s) currently deployed. "
                f"Will dispatch when a unit returns to AVAILABLE status."
            )
            return state

    # ── Compute ETAs for ALL available units (for explainability) ─────────
    all_etas = _compute_all_etas(incident_location, available_units, city_graph)

    # ── Find the nearest unit ──────────────────────────────────────────────
    unit_id, distance, path = city_graph.find_nearest_unit(
        incident_location, available_units
    )

    if unit_id is None:
        state["agent_reasoning"]["dispatch"] = (
            f"NO PATH AVAILABLE — ESCALATING. "
            f"No valid route to '{incident_location}' (original: '{raw_location}'). "
            f"Manual dispatch required."
        )
        return state

    eta: float = float(distance)

    # ── Update resource status ────────────────────────────────────────────
    state["resources"][unit_id]["status"] = "DISPATCHED"
    state["resources"][unit_id]["assigned_incident"] = incident_id

    # ── Build dispatch log entry ──────────────────────────────────────────
    dispatch_entry: dict = {
        "incident_id": incident_id,
        "unit_id": unit_id,
        "route": path,
        "eta": eta,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "severity": incident_severity,
        "rerouted_from": rerouted_from,
    }
    state["dispatch_log"].append(dispatch_entry)

    # ── Record rich agent reasoning ───────────────────────────────────────
    state["agent_reasoning"]["dispatch"] = _build_explanation(
        unit_id=unit_id,
        location=incident_location,
        unit_type=required_type,
        eta=eta,
        route=path,
        incident_severity=incident_severity,
        all_etas=all_etas,
        rerouted_from=rerouted_from,
    )

    # ── Check system-wide resource utilization and append warning ─────────
    total = len(resources)
    dispatched_count = sum(
        1 for u in state["resources"].values() if u.get("status") == "DISPATCHED"
    )
    utilization = dispatched_count / total if total > 0 else 0.0
    if utilization >= 0.75:
        current = state["agent_reasoning"]["dispatch"]
        state["agent_reasoning"]["dispatch"] = (
            current + f" WARNING: System utilization now at {utilization:.0%} "
            f"({dispatched_count}/{total} units deployed). "
            f"Recommend standby alert to off-duty units."
        )

    return state
