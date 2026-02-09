
def build_graph_for_route(route):
    """
    Build a simple linear graph from a station route.
    If route is None -> return empty graph placeholder.
    """

    if route is None:
        return {
            "nodes": [],
            "edges": []
        }

    nodes = []
    edges = []

    for station in route:
        nodes.append({
            "id": station,
            "label": station,
            "witness": 0,
            "hold": 0,
        })

    for i in range(len(route) - 1):
        edges.append({
            "source": route[i],
            "target": route[i + 1],
        })

    return {
        "nodes": nodes,
        "edges": edges,
    }
