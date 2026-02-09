def build_inspection_graph(stations, inspection_load):
    nodes = []
    edges = []

    for station in stations:
        load = inspection_load.get(station, {})
        nodes.append({
            "id": station,
            "label": station,
            "witness": load.get("WITNESS", 0),
            "hold": load.get("HOLD", 0),
        })

    for i in range(len(stations) - 1):
        edges.append({
            "source": stations[i],
            "target": stations[i + 1],
        })

    return {
        "nodes": nodes,
        "edges": edges,
    }
