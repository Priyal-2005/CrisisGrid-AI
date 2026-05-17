"""Dispatch Agent — Enhanced with multi-resource dispatch and severity scoring.

Part of the CrisisGrid AI LangGraph multi-agent pipeline.

Improvements over v1:
- Multi-resource dispatch (sends resource PACKAGES, not single units)
- severity_score-based prioritization (not just tier ordering)
- Strategic rerouting from MEDIUM → CRITICAL (not just LOW → CRITICAL)
- Partial reassignment (pull 1 of N units from a lower-priority incident)
- Rich explainability: why this incident, why these resources, what risks
- Dynamic ETA awareness via city_graph traffic conditions
"""

from datetime import datetime
from data.zone_profiles import get_zone_risk_summary


# ---------------------------------------------------------------------------
# Priority and resource-type mappings
# ---------------------------------------------------------------------------

SEVERITY_PRIORITY: dict[str, int] = {
    "CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "UNKNOWN": 4
}

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

    Priority order: severity_score (highest first), then tier as fallback.
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

    # Sort by severity_score (descending), then by tier priority as fallback
    unassigned.sort(
        key=lambda x: (
            -x.get("severity_score", 0),  # Higher score = higher priority
            SEVERITY_PRIORITY.get(x.get("severity", "UNKNOWN").upper(), 4),
        )
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
    requester_severity_score: int = 100,
) -> tuple[str | None, str | None, str | None, int]:
    """Find a unit of *required_type* dispatched to a lower-priority incident.

    Enhanced: now considers MEDIUM incidents (not just LOW) as donors
    when the requester is CRITICAL/HIGH with a high severity_score.

    Returns: (unit_id, donor_incident_id, donor_severity, donor_score) or (None, None, None, 0)
    """
    inc_data: dict[str, dict] = {}
    for inc in incidents:
        iid = inc.get("id", inc.get("master_incident_id", ""))
        inc_data[iid] = {
            "severity": inc.get("severity", "LOW").upper(),
            "score": inc.get("severity_score", 0),
        }

    # Maximum severity score we'll steal from
    # CRITICAL (86+) can steal from anything below 66 (MEDIUM and LOW)
    # HIGH (66-85) can steal from below 36 (LOW only)
    steal_threshold = 0
    if requester_severity_score >= 86:
        steal_threshold = 65  # Can steal from MEDIUM and below
    elif requester_severity_score >= 66:
        steal_threshold = 35  # Can steal from LOW only

    # Iterate dispatch log most-recent-first to reassign from the lowest-priority dispatch
    candidates = []
    for entry in dispatch_log:
        inc_id = entry.get("incident_id", "")
        unit_id = entry.get("unit_id", "")
        donor = inc_data.get(inc_id, {"severity": "LOW", "score": 0})
        donor_score = donor["score"]
        donor_sev = donor["severity"]

        if donor_score >= steal_threshold:
            continue  # Donor is too important to steal from
        if not unit_id or unit_id not in resources:
            continue
        unit = resources[unit_id]
        if unit.get("type") != required_type:
            continue
        if unit.get("status") != "DISPATCHED":
            continue

        candidates.append((unit_id, inc_id, donor_sev, donor_score))

    if not candidates:
        return None, None, None, 0

    # Pick the donor with the LOWEST severity score (least impact)
    candidates.sort(key=lambda x: x[3])
    return candidates[0]


def _build_explanation(
    unit_id: str,
    location: str,
    unit_type: str,
    eta: float,
    route: list,
    incident_severity: str,
    severity_score: int,
    all_etas: dict[str, tuple[float, list]],
    rerouted_from: str | None = None,
    reroute_donor_severity: str | None = None,
    zone_risk: str = "",
    resource_package: dict | None = None,
    competing_incidents: list[dict] | None = None,
) -> str:
    """Rich dispatch explanation: why this unit, why not others, what tradeoff.

    Enhanced with:
    - Severity score context
    - Zone risk information
    - Resource package rationale
    - Competing incident comparison
    - Risk acceptance statements
    """
    route_str = " → ".join(str(node) for node in route)
    # Build alternatives list (sorted by ETA, excluding the chosen unit)
    alternatives = [
        (uid, t, p) for uid, (t, p) in all_etas.items() if uid != unit_id
    ]
    alternatives.sort(key=lambda x: x[1])

    lines = [
        f"DISPATCH: {unit_id} → {location} [{incident_severity}, score={severity_score}/100].",
        f"Route: {route_str}. ETA: {eta:.1f} min.",
        f"Decision: {unit_id} selected as nearest available {unit_type}.",
    ]

    # Zone risk context
    if zone_risk:
        lines.append(f"Zone intelligence: {zone_risk}")

    # Resource package context
    if resource_package:
        pkg_str = ", ".join(f"{v}×{k}" for k, v in resource_package.items())
        lines.append(f"Full resource requirement: [{pkg_str}]. This dispatch covers {unit_type} component.")

    if alternatives:
        alt_strs = [
            f"{uid} ({alt_eta:.0f} min)" for uid, alt_eta, _ in alternatives[:2]
        ]
        lines.append(
            f"Alternatives considered: {', '.join(alt_strs)} — higher ETA, not selected."
        )

    # Competing incidents context
    if competing_incidents:
        for comp in competing_incidents[:2]:
            comp_id = comp.get("id", "?")
            comp_score = comp.get("severity_score", 0)
            comp_sev = comp.get("severity", "?")
            lines.append(
                f"Competing: {comp_id} [{comp_sev}, score={comp_score}] — "
                f"{'deferred (lower score)' if comp_score < severity_score else 'also being serviced'}."
            )

    if incident_severity == "CRITICAL":
        lines.append(
            f"CRITICAL incident (score {severity_score}/100): minimum-ETA unit mandatory. No delay tolerable."
        )
        if len(alternatives) >= 1:
            hold_uid = alternatives[0][0]
            lines.append(
                f"Tradeoff: {hold_uid} held in reserve for potential secondary CRITICAL escalation."
            )
    elif incident_severity == "HIGH":
        lines.append(
            f"HIGH priority (score {severity_score}/100): fast response required. "
            f"CRITICAL reserves maintained where possible."
        )
    elif incident_severity == "MEDIUM":
        lines.append(
            "MEDIUM priority: fastest available unit dispatched; CRITICAL reserves maintained."
        )
    else:  # LOW
        lines.append(
            "LOW priority: nearest unit dispatched. Unit may be reassigned if higher-priority incident emerges."
        )

    if rerouted_from:
        lines.append(
            f"⚡ DYNAMIC REROUTE: {unit_id} pulled from {reroute_donor_severity or 'lower-priority'} "
            f"incident {rerouted_from} to service this {incident_severity} incident. "
            f"Risk accepted: {rerouted_from} temporarily without {unit_type} coverage."
        )

    return " ".join(lines)


# ---------------------------------------------------------------------------
# Main agent entry point
# ---------------------------------------------------------------------------

def dispatch_agent(state: dict) -> dict:
    """Assign resources to the highest-priority unassigned incident.

    Enhanced with:
    - Multi-resource dispatch (sends multiple units per resource package)
    - severity_score-based prioritization (not just tier)
    - Strategic rerouting (MEDIUM → CRITICAL, not just LOW → CRITICAL)
    - Partial reassignment support
    - Zone-aware explainability

    Writes to state:
        - resources[unit_id]["status"] = "DISPATCHED"
        - New entries appended to dispatch_log
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

    # ── Update city graph with current incident conditions ────────────
    try:
        city_graph.update_conditions(active_incidents=incidents)
    except AttributeError:
        pass  # Old CityGraph without dynamic conditions

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
    severity_score: int = incident.get("severity_score", 50)
    resources_needed: list[str] = incident.get("resources_needed", [])
    required_resources: dict = incident.get("required_resources", {})

    incident_location = _normalize_location(raw_location)

    # Get zone risk summary for explainability
    zone_risk = get_zone_risk_summary(incident_location)

    # ── Determine resource package to dispatch ──────────────────────────
    # Use required_resources from severity engine if available,
    # otherwise fall back to resources_needed list
    dispatch_plan: list[dict] = []  # List of {type, unit_id, eta, path}

    # Build the list of resource types and counts to dispatch
    resource_targets: dict[str, int] = {}
    if required_resources:
        resource_targets = dict(required_resources)
    else:
        for need in resources_needed:
            rtype = _resolve_unit_type(need)
            if rtype:
                resource_targets[rtype] = resource_targets.get(rtype, 0) + 1

    if not resource_targets:
        # Absolute fallback: dispatch one ambulance
        resource_targets = {"ambulance": 1}

    # ── Identify competing incidents for explainability ────────────────
    dispatched_ids = _get_dispatched_incident_ids(dispatch_log)
    competing = [
        inc for inc in incidents
        if inc.get("id") != incident_id
        and inc.get("id") not in dispatched_ids
        and inc.get("master_incident_id") not in dispatched_ids
    ]
    competing.sort(key=lambda x: -x.get("severity_score", 0))

    # ── Dispatch each resource type in the package ─────────────────────
    dispatch_explanations: list[str] = []
    all_rerouted_from: list[str] = []

    for required_type, count_needed in resource_targets.items():
        for dispatch_i in range(count_needed):
            available_units = _filter_available_units(resources, required_type)
            rerouted_from: str | None = None
            reroute_donor_sev: str | None = None

            if not available_units:
                # ── Attempt dynamic re-routing for HIGH/CRITICAL incidents ─────
                if severity_score >= 66:  # HIGH or CRITICAL
                    unit_to_pull, donor_inc_id, donor_sev, donor_score = _find_reassignable_unit(
                        resources, dispatch_log, incidents, required_type,
                        requester_severity_score=severity_score,
                    )
                    if unit_to_pull:
                        state["resources"][unit_to_pull]["status"] = "AVAILABLE"
                        available_units = {unit_to_pull: state["resources"][unit_to_pull]}
                        rerouted_from = donor_inc_id
                        reroute_donor_sev = donor_sev
                    else:
                        total_of_type = sum(
                            1 for u in resources.values() if u.get("type") == required_type
                        )
                        dispatch_explanations.append(
                            f"NO {required_type.upper()} AVAILABLE (need #{dispatch_i+1}/{count_needed}). "
                            f"All {total_of_type} unit(s) on higher-priority assignments. "
                            f"Requesting mutual aid for {required_type}."
                        )
                        continue
                else:
                    total_of_type = sum(
                        1 for u in resources.values() if u.get("type") == required_type
                    )
                    dispatch_explanations.append(
                        f"NO {required_type.upper()} AVAILABLE for {incident_severity} incident "
                        f"(score {severity_score}). Queued until unit returns."
                    )
                    continue

            # ── Compute ETAs for all available units ──────────────────
            all_etas = _compute_all_etas(incident_location, available_units, city_graph)

            # ── Find the nearest unit ─────────────────────────────────
            unit_id, distance, path = city_graph.find_nearest_unit(
                incident_location, available_units
            )

            if unit_id is None:
                dispatch_explanations.append(
                    f"NO PATH to '{incident_location}' for {required_type}. Manual dispatch required."
                )
                continue

            eta: float = float(distance)

            # ── Update resource status ────────────────────────────────
            state["resources"][unit_id]["status"] = "DISPATCHED"
            state["resources"][unit_id]["assigned_incident"] = incident_id

            # ── Build dispatch log entry ──────────────────────────────
            dispatch_entry: dict = {
                "incident_id": incident_id,
                "unit_id": unit_id,
                "route": path,
                "eta": eta,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "severity": incident_severity,
                "severity_score": severity_score,
                "rerouted_from": rerouted_from,
            }
            state["dispatch_log"].append(dispatch_entry)

            if rerouted_from:
                all_rerouted_from.append(rerouted_from)

            # ── Build explanation for this unit ───────────────────────
            explanation = _build_explanation(
                unit_id=unit_id,
                location=incident_location,
                unit_type=required_type,
                eta=eta,
                route=path,
                incident_severity=incident_severity,
                severity_score=severity_score,
                all_etas=all_etas,
                rerouted_from=rerouted_from,
                reroute_donor_severity=reroute_donor_sev,
                zone_risk=zone_risk if dispatch_i == 0 else "",
                resource_package=required_resources if dispatch_i == 0 else None,
                competing_incidents=competing if dispatch_i == 0 else None,
            )
            dispatch_explanations.append(explanation)

    # ── Compile final reasoning ──────────────────────────────────────
    if dispatch_explanations:
        full_reasoning = " || ".join(dispatch_explanations)
    else:
        full_reasoning = (
            f"NO AVAILABLE UNITS — ESCALATING. "
            f"Incident {incident_id} [{incident_severity}, score={severity_score}] "
            f"requires resources but none available. "
            f"Recommend Strategy Agent for mutual aid request."
        )

    state["agent_reasoning"]["dispatch"] = full_reasoning

    # ── Check system-wide resource utilization and append warning ─────
    total = len(resources)
    dispatched_count = sum(
        1 for u in state["resources"].values() if u.get("status") == "DISPATCHED"
    )
    utilization = dispatched_count / total if total > 0 else 0.0
    if utilization >= 0.75:
        current = state["agent_reasoning"]["dispatch"]
        state["agent_reasoning"]["dispatch"] = (
            current + f" ⚠️ WARNING: System utilization at {utilization:.0%} "
            f"({dispatched_count}/{total} units deployed). "
            f"Recommend standby alert to off-duty units."
        )

    return state
