import networkx as nx
import plotly.graph_objects as go

def build_city_graph():
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
        G.add_edge(u, v, weight=w)
        
    return G

def get_shortest_path(G, source, target):
    """Calculates the shortest path based on travel time (weight)."""
    try:
        path = nx.shortest_path(G, source=source, target=target, weight="weight")
        travel_time = nx.shortest_path_length(G, source=source, target=target, weight="weight")
        return path, travel_time
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        return [], float('inf')

def find_nearest_unit(G, incident_location, available_units):
    """Finds the nearest available unit to an incident location."""
    best_unit = None
    best_path = []
    min_eta = float('inf')
    
    for unit in available_units:
        if unit.get("status") != "available":
            continue
            
        path, eta = get_shortest_path(G, unit["location"], incident_location)
        if eta < min_eta:
            min_eta = eta
            best_unit = unit
            best_path = path
            
    return best_unit, best_path, min_eta

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
