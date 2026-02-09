import json
import streamlit.components.v1 as components


def render_inspection_cytoscape(graph):
    elements = []

    # MOCK mapping: station -> supported spool types
    STATION_TYPES = {
        "Work Preparation": ["Basic", "Bend", "Weld", "Bend + Weld"],
        "Cutting": ["Basic", "Bend", "Weld", "Bend + Weld"],
        "Bending": ["Bend", "Bend + Weld"],
        "Welding": ["Weld", "Bend + Weld"],
        "NDT": ["Weld", "Bend + Weld"],
        "Technical Control": ["Basic", "Bend", "Weld", "Bend + Weld"],
    }

    x_step = 220
    y_station = 200
    y_badge = 280

    for idx, node in enumerate(graph["nodes"]):
        x = idx * x_step + 140
        station = node["label"]
        types = STATION_TYPES.get(station, [])

        elements.append({
            "data": {
                "id": node["id"],
                "label": station,
                "icon": f"/assets/{station.lower().replace(' ', '_')}.png",
                "type": "station",
                "spool_types": ",".join(types),
            },
            "position": {"x": x, "y": y_station},
        })

        elements.append({
            "data": {
                "id": node["id"] + "_badge",
                "label": f"W:{node.get('witness', 0)}  H:{node.get('hold', 0)}",
                "type": "badge",
                "station_id": node["id"],
            },
            "position": {"x": x, "y": y_badge},
        })

    for edge in graph["edges"]:
        elements.append({"data": edge})

    html = """
<!DOCTYPE html>
<html>
<head>
  <script src='https://unpkg.com/cytoscape@3.26.0/dist/cytoscape.min.js'></script>
  <style>
    body { margin: 0; background-color: #e8f2ff; }
    #toolbar { padding: 6px; background: #e8f2ff; border-bottom: 1px solid #94a3b8; display:flex; flex-wrap:wrap; gap:6px; }
    button { padding: 4px 10px; border-radius: 4px; border: 1px solid #64748b; background: #f8fafc; cursor: pointer; }
    #cy { width: 100%; height: 520px; background-color: #e8f2ff; }
  </style>
</head>

<body>
  <div id='toolbar'>
    <b>View:</b>
    <button onclick="fitView()">Fit</button>
    <button onclick="zoomIn()">Zoom +</button>
    <button onclick="zoomOut()">Zoom -</button>
    <button onclick="togglePan()">Pan</button>
    <button onclick="toggleBadges()">Toggle W/H</button>
    <span style="margin-left:12px"><b>Spool type:</b></span>
    <button onclick="filterType('All')">All</button>
    <button onclick="filterType('Basic')">Basic</button>
    <button onclick="filterType('Bend')">Bend</button>
    <button onclick="filterType('Weld')">Weld</button>
    <button onclick="filterType('Bend + Weld')">Bend + Weld</button>
  </div>
  <div id='cy'></div>

  <script>
    var panEnabled = false;

    var cy = cytoscape({
      container: document.getElementById('cy'),
      elements: __ELEMENTS__,
      layout: { name: 'preset' },
      userZoomingEnabled: false,
      userPanningEnabled: false,
      style: [
        {
          selector: 'node[data(type) = "station"]',
          style: {
            shape: 'round-rectangle',
            width: 160,
            height: 100,
            'background-image': 'data(icon)',
            'background-fit': 'cover',
            'border-width': 2,
            'border-color': '#1e3a8a',
            'label': 'data(label)',
            'text-halign': 'center',
            'text-valign': 'center',
            'font-size': '13px',
            'color': '#ffffff'
          }
        },
        {
          selector: 'node[data(type) = "badge"]',
          style: {
            shape: 'round-rectangle',
            width: 100,
            height: 28,
            'background-color': '#f1f5f9',
            'border-width': 1,
            'border-color': '#64748b',
            'label': 'data(label)',
            'font-size': '11px',
            'color': '#0f172a'
          }
        },
        {
          selector: 'edge',
          style: {
            width: 2,
            'line-color': '#64748b',
            'target-arrow-shape': 'triangle'
          }
        }
      ]
    });

    function fitView() { cy.fit(); }
    function zoomIn() { cy.zoom(cy.zoom() * 1.2); }
    function zoomOut() { cy.zoom(cy.zoom() / 1.2); }

    function togglePan() {
      panEnabled = !panEnabled;
      cy.userPanningEnabled(panEnabled);
    }

    function toggleBadges() {
      var badges = cy.nodes('node[data(type) = "badge"]');
      badges.visible() ? badges.hide() : badges.show();
    }

    function filterType(type) {
      if (type === 'All') {
        cy.nodes().show();
        cy.edges().show();
        cy.fit();
        return;
      }

      cy.nodes('node[data(type) = "station"]').forEach(function(n) {
        var types = n.data('spool_types').split(',');
        types.includes(type) ? n.show() : n.hide();
      });

      cy.nodes('node[data(type) = "badge"]').forEach(function(b) {
        var st = cy.getElementById(b.data('station_id'));
        st.visible() ? b.show() : b.hide();
      });

      cy.edges().forEach(function(e) {
        (e.source().visible() && e.target().visible()) ? e.show() : e.hide();
      });

      cy.fit();
    }

    cy.fit();
  </script>
</body>
</html>
""".replace("__ELEMENTS__", json.dumps(elements))

    components.html(html, height=600)
