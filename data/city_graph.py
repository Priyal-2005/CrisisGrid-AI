"""Mock city graph for CrisisGrid AI.

Provides a NetworkX-backed city graph with zones as nodes and
travel-time weighted edges.  Exposes helper methods used by the
Dispatch Agent.
"""

import networkx as nx


class CityGraph:
    """Wrapper around a NetworkX graph with dispatch-friendly methods.

    Nodes represent city zones.  Edges carry a ``travel_time`` weight
    (in minutes) representing average emergency-vehicle travel time.
    """

    def __init__(self, graph: nx.Graph):
        self.graph = graph

    def find_nearest_unit(
        self,
        location: str,
        available_units: dict,
    ) -> tuple[str, float, list[str]]:
        """Find the nearest available unit to *location*.

        Uses Dijkstra shortest-path on ``travel_time`` weights.

        Args:
            location:        Target zone node.
            available_units: ``{unit_id: {type, status, location, ...}}``.

        Returns:
            ``(unit_id, total_travel_time, path)`` for the closest unit.

        Raises:
            ValueError: If no reachable unit exists.
        """
        best_unit = None
        best_distance = float("inf")
        best_path: list[str] = []

        for uid, info in available_units.items():
            unit_loc = info.get("location")
            try:
                path = nx.shortest_path(
                    self.graph, source=unit_loc, target=location,
                    weight="travel_time",
                )
                dist = nx.shortest_path_length(
                    self.graph, source=unit_loc, target=location,
                    weight="travel_time",
                )
                if dist < best_distance:
                    best_distance = dist
                    best_unit = uid
                    best_path = path
            except nx.NetworkXNoPath:
                continue

        if best_unit is None:
            raise ValueError(
                f"No reachable unit found for location '{location}'."
            )
        return best_unit, best_distance, best_path

    def get_shortest_path(
        self,
        start: str,
        end: str,
    ) -> tuple[list[str], float]:
        """Return the shortest path and travel time between two zones.

        Args:
            start: Source zone node.
            end:   Destination zone node.

        Returns:
            ``(path, travel_time)`` tuple.
        """
        path = nx.shortest_path(
            self.graph, source=start, target=end, weight="travel_time",
        )
        dist = nx.shortest_path_length(
            self.graph, source=start, target=end, weight="travel_time",
        )
        return path, dist


def create_city_graph() -> CityGraph:
    """Build a mock city graph with 8 zones and realistic travel times.

    Zone layout (approximate):
        Zone-A ── Zone-B ── Zone-C
          │          │          │
        Zone-D ── Zone-E ── Zone-F
          │          │          │
        Zone-G ── Zone-H ── Zone-I

    Returns:
        A ``CityGraph`` instance ready for dispatch queries.
    """
    G = nx.Graph()

    zones = [
        "Zone-A", "Zone-B", "Zone-C",
        "Zone-D", "Zone-E", "Zone-F",
        "Zone-G", "Zone-H", "Zone-I",
    ]
    G.add_nodes_from(zones)

    edges = [
        ("Zone-A", "Zone-B", 5),
        ("Zone-B", "Zone-C", 7),
        ("Zone-A", "Zone-D", 6),
        ("Zone-B", "Zone-E", 4),
        ("Zone-C", "Zone-F", 8),
        ("Zone-D", "Zone-E", 3),
        ("Zone-E", "Zone-F", 5),
        ("Zone-D", "Zone-G", 7),
        ("Zone-E", "Zone-H", 4),
        ("Zone-F", "Zone-I", 6),
        ("Zone-G", "Zone-H", 5),
        ("Zone-H", "Zone-I", 3),
    ]

    for u, v, t in edges:
        G.add_edge(u, v, travel_time=t)

    return CityGraph(G)
