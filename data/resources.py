"""Mock resource database for CrisisGrid AI.

Provides a pre-configured set of emergency response units spread
across the city zones.
"""


def load_resources() -> dict:
    """Return the initial resource database.

    Each unit has a unique ID and a dict of:
        - type:     ``"ambulance"`` | ``"fire_truck"`` | ``"police"``
        - status:   ``"AVAILABLE"`` | ``"DISPATCHED"``
        - location: Zone node name from the city graph.

    Returns:
        ``{unit_id: {type, status, location}}`` dict.
    """
    return {
        "AMB-01": {
            "type": "ambulance",
            "status": "AVAILABLE",
            "location": "Zone-A",
        },
        "AMB-02": {
            "type": "ambulance",
            "status": "AVAILABLE",
            "location": "Zone-E",
        },
        "AMB-03": {
            "type": "ambulance",
            "status": "AVAILABLE",
            "location": "Zone-I",
        },
        "FT-01": {
            "type": "fire_truck",
            "status": "AVAILABLE",
            "location": "Zone-B",
        },
        "FT-02": {
            "type": "fire_truck",
            "status": "AVAILABLE",
            "location": "Zone-G",
        },
        "POL-01": {
            "type": "police",
            "status": "AVAILABLE",
            "location": "Zone-C",
        },
        "POL-02": {
            "type": "police",
            "status": "AVAILABLE",
            "location": "Zone-D",
        },
        "POL-03": {
            "type": "police",
            "status": "AVAILABLE",
            "location": "Zone-H",
        },
    }
