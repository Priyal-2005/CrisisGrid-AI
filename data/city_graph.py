"""City Graph with Dynamic Traffic Conditions — CrisisGrid AI.

Extends the static NetworkX graph with:
- Dynamic ETA inflation near active incidents
- Zone congestion modeling
- Road blockage simulation
- Disaster traffic multipliers

The base graph structure is PRESERVED — only ETA calculations are enhanced.
"""

import networkx as nx
import plotly.graph_objects as go
from data.zone_profiles import get_zone_profile


class CityGraph:
    def __init__(self):
        self.graph = self._build_graph()
        # Dynamic conditions — updated by dispatch/backend
        self._active_incident_zones: list[str] = []
        self._blocked_roads: set[tuple[str, str]] = set()
        self._flood_zones: set[str] = set()

    def _build_graph(self):
        """Builds and returns an undirected networkx graph representing the smart city."""
        G = nx.Graph()

        # Define nodes with arbitrary (x,y) coordinates for plotting purposes
        nodes = {
            "downtown": (0, 0),
            "harbor": (2, -2),
            "industrial": (4, 1),
            "sector7": (-2, 2),
            "north_grid": (0, 4),
            "central_park": (2, 2),
            "westside": (-4, 0),
            "port": (4, -3),
            "eastside": (5, 0),
            "suburbs": (-3, -3),
            "midtown": (1, -1),
            "airport": (-5, 4)
        }

        for node, pos in nodes.items():
            G.add_node(node, pos=pos)

        # Define edges with weight (travel time in minutes)
        edges = [
            ("downtown", "midtown", 3),
            ("downtown", "central_park", 5),
            ("downtown", "sector7", 6),
            ("downtown", "westside", 8),
            ("midtown", "harbor", 4),
            ("harbor", "port", 5),
            ("central_park", "industrial", 7),
            ("central_park", "north_grid", 6),
            ("sector7", "north_grid", 5),
            ("sector7", "airport", 12),
            ("westside", "suburbs", 10),
            ("westside", "airport", 15),
            ("industrial", "eastside", 4),
            ("port", "eastside", 8),
            ("suburbs", "midtown", 9),
            ("north_grid", "airport", 14),
            ("eastside", "downtown", 11)
        ]

        for u, v, w in edges:
            G.add_edge(u, v, weight=w, base_weight=w)

        return G

    # ------------------------------------------------------------------
    # Dynamic conditions API
    # ------------------------------------------------------------------

    def update_conditions(
        self,
        active_incidents: list[dict] | None = None,
        blocked_roads: list[tuple[str, str]] | None = None,
        flood_zones: list[str] | None = None,
    ) -> None:
        """Update dynamic traffic conditions.

        Called by the backend after each pipeline run to reflect
        current crisis state in routing calculations.
        """
        if active_incidents is not None:
            self._active_incident_zones = [
                inc.get("location", "").lower().strip()
                for inc in active_incidents
                if inc.get("status", "ACTIVE") == "ACTIVE"
            ]

        if blocked_roads is not None:
            self._blocked_roads = set(blocked_roads)

        if flood_zones is not None:
            self._flood_zones = set(flood_zones)

    def _get_dynamic_weight(self, u: str, v: str) -> float:
        """Compute dynamic edge weight accounting for traffic conditions.

        Applies multipliers for:
        - Active incidents near the route (congestion from responders + crowds)
        - Zone congestion profiles
        - Blocked roads (returns infinity)
        - Flood zones (major delay)
        """
        base_weight = self.graph[u][v].get("base_weight", self.graph[u][v].get("weight", 5))
        multiplier = 1.0

        # Blocked road check
        if (u, v) in self._blocked_roads or (v, u) in self._blocked_roads:
            return float("inf")

        # Flood zone penalty
        if u in self._flood_zones or v in self._flood_zones:
            multiplier += 1.5  # 150% slower through flooded areas

        # Active incident congestion (responders, crowds, road closures)
        for zone in self._active_incident_zones:
            if zone == u or zone == v:
                multiplier += 0.4  # 40% slower near active incident
            # Adjacent zone mild congestion
            if zone in self.graph.neighbors(u) or zone in self.graph.neighbors(v):
                multiplier += 0.1

        # Zone congestion from profile (rush hour simulation)
        dest_profile = get_zone_profile(v)
        congestion = dest_profile.get("congestion_score", 0.5)
        multiplier += congestion * 0.25  # Up to +25% for highly congested zones

        return base_weight * multiplier

    # ------------------------------------------------------------------
    # Routing with dynamic conditions
    # ------------------------------------------------------------------

    def get_shortest_path(self, start, end, use_dynamic=True):
        """Calculates the shortest path based on travel time (weight).

        Args:
            start: Source zone.
            end: Destination zone.
            use_dynamic: If True, use dynamic traffic-adjusted weights.

        Returns:
            (path, travel_time) — path is a list of zone names.
        """
        try:
            if use_dynamic and (self._active_incident_zones or
                                self._blocked_roads or
                                self._flood_zones):
                # Create a temporary weight function for dynamic routing
                def weight_fn(u, v, data):
                    return self._get_dynamic_weight(u, v)

                path = nx.shortest_path(
                    self.graph, source=start, target=end, weight=weight_fn
                )
                travel_time = nx.shortest_path_length(
                    self.graph, source=start, target=end, weight=weight_fn
                )
            else:
                path = nx.shortest_path(
                    self.graph, source=start, target=end, weight="weight"
                )
                travel_time = nx.shortest_path_length(
                    self.graph, source=start, target=end, weight="weight"
                )
            return path, travel_time
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return [], float('inf')

    def find_nearest_unit(self, incident_location, available_units_dict):
        """Finds the nearest available unit to an incident location."""
        best_unit_id = None
        best_path = []
        min_eta = float('inf')

        for unit_id, unit_info in available_units_dict.items():
            path, eta = self.get_shortest_path(unit_info["location"], incident_location)
            if eta < min_eta:
                min_eta = eta
                best_unit_id = unit_id
                best_path = path

        return best_unit_id, min_eta, best_path

    def get_traffic_report(self) -> dict:
        """Return a summary of current traffic conditions for explainability."""
        report = {
            "active_incident_zones": list(self._active_incident_zones),
            "blocked_roads": [list(r) for r in self._blocked_roads],
            "flood_zones": list(self._flood_zones),
            "affected_edges": [],
        }
        for u, v in self.graph.edges():
            dynamic_w = self._get_dynamic_weight(u, v)
            base_w = self.graph[u][v].get("base_weight", self.graph[u][v].get("weight", 5))
            if dynamic_w == float("inf"):
                report["affected_edges"].append({
                    "from": u,
                    "to": v,
                    "base_eta": round(base_w, 1),
                    "dynamic_eta": "BLOCKED",
                    "inflation": "BLOCKED",
                })
            elif dynamic_w > base_w * 1.1:  # >10% inflation
                inflation_pct = int((dynamic_w / base_w - 1) * 100)
                report["affected_edges"].append({
                    "from": u,
                    "to": v,
                    "base_eta": round(base_w, 1),
                    "dynamic_eta": round(dynamic_w, 1),
                    "inflation": f"+{inflation_pct}%",
                })
        return report


def create_city_graph():
    return CityGraph()


def get_graph_figure(G, active_routes=None, incident_nodes=None):
    """Generates a Plotly figure of the city graph, optionally highlighting incidents and routes."""
    pos = nx.get_node_attributes(G, 'pos')

    edge_x = []
    edge_y = []
    for edge in G.edges():
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])

    edge_trace = go.Scatter(
        x=edge_x, y=edge_y,
        line=dict(width=2, color='#aaaaaa'),
        hoverinfo='none',
        mode='lines'
    )

    node_x = []
    node_y = []
    node_text = []
    node_color = []

    incident_nodes = incident_nodes or []

    for node in G.nodes():
        x, y = pos[node]
        node_x.append(x)
        node_y.append(y)
        node_text.append(node)
        if node in incident_nodes:
            node_color.append('red')
        else:
            node_color.append('lightblue')

    node_trace = go.Scatter(
        x=node_x, y=node_y,
        mode='markers+text',
        hoverinfo='text',
        text=node_text,
        textposition="top center",
        marker=dict(
            showscale=False,
            color=node_color,
            size=24,
            line_width=2,
            line_color='black'
        )
    )

    traces = [edge_trace, node_trace]

    if active_routes:
        for route in active_routes:
            rx = []
            ry = []
            for node in route:
                x, y = pos[node]
                rx.append(x)
                ry.append(y)

            route_trace = go.Scatter(
                x=rx, y=ry,
                line=dict(width=5, color='orange', dash='dot'),
                hoverinfo='none',
                mode='lines'
            )
            traces.append(route_trace)

    fig = go.Figure(data=traces,
             layout=go.Layout(
                title="CrisisGrid Smart City Map",
                titlefont_size=16,
                showlegend=False,
                hovermode='closest',
                margin=dict(b=20,l=5,r=5,t=40),
                xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                yaxis=dict(showgrid=False, zeroline=False, showticklabels=False))
                )

    return fig
