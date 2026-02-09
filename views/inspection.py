from logic.shopfloor_rules import STATIONS, calculate_inspection_load
from logic.inspection_graph import build_graph_for_route

from ui.inspection_cytoscape import render_inspection_cytoscape

import streamlit as st


def render_inspection(spools_df):
    st.subheader("🔍 Inspection – Flow Overview")
    st.success("Inspection view loaded")
    inspection_load = calculate_inspection_load(spools_df)

    graph = build_graph_for_route(
        stations=STATIONS,
        inspection_load=inspection_load,
    )

    render_inspection_cytoscape(graph)
