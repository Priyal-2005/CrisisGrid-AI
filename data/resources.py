import copy

INITIAL_RESOURCES = {
    # Ambulances (5)
    "AMB-01": {
        "id": "AMB-01",
        "type": "ambulance",
        "status": "AVAILABLE",
        "location": "downtown",
        "eta": None,
        "assigned_incident": None
    },
    "AMB-02": {
        "id": "AMB-02",
        "type": "ambulance",
        "status": "AVAILABLE",
        "location": "central_park",
        "eta": None,
        "assigned_incident": None
    },
    "AMB-03": {
        "id": "AMB-03",
        "type": "ambulance",
        "status": "DISPATCHED",
        "location": "midtown",
        "eta": 4,
        "assigned_incident": "INC-PREV-01"
    },
    "AMB-04": {
        "id": "AMB-04",
        "type": "ambulance",
        "status": "AVAILABLE",
        "location": "suburbs",
        "eta": None,
        "assigned_incident": None
    },
    "AMB-05": {
        "id": "AMB-05",
        "type": "ambulance",
        "status": "AVAILABLE",
        "location": "north_grid",
        "eta": None,
        "assigned_incident": None
    },

    # Fire Trucks (3)
    "FIRE-01": {
        "id": "FIRE-01",
        "type": "fire_truck",
        "status": "AVAILABLE",
        "location": "industrial",
        "eta": None,
        "assigned_incident": None
    },
    "FIRE-02": {
        "id": "FIRE-02",
        "type": "fire_truck",
        "status": "AVAILABLE",
        "location": "harbor",
        "eta": None,
        "assigned_incident": None
    },
    "FIRE-03": {
        "id": "FIRE-03",
        "type": "fire_truck",
        "status": "DISPATCHED",
        "location": "eastside",
        "eta": 7,
        "assigned_incident": "INC-PREV-02"
    },

    # Police Vans (4)
    "POLICE-01": {
        "id": "POLICE-01",
        "type": "police",
        "status": "AVAILABLE",
        "location": "sector7",
        "eta": None,
        "assigned_incident": None
    },
    "POLICE-02": {
        "id": "POLICE-02",
        "type": "police",
        "status": "AVAILABLE",
        "location": "westside",
        "eta": None,
        "assigned_incident": None
    },
    "POLICE-03": {
        "id": "POLICE-03",
        "type": "police",
        "status": "AVAILABLE",
        "location": "port",
        "eta": None,
        "assigned_incident": None
    },
    "POLICE-04": {
        "id": "POLICE-04",
        "type": "police",
        "status": "DISPATCHED",
        "location": "airport",
        "eta": 2,
        "assigned_incident": "INC-PREV-03"
    }
}

def load_resources():
    """Returns the initial state of all emergency resources."""
    return copy.deepcopy(INITIAL_RESOURCES)
