import streamlit as st

# --------------------------------------------------
# STATION IMAGES
# --------------------------------------------------
STATION_IMAGES = {
    "Work Prep": "assets/work_preparation.png",
    "PPS": "assets/pps.png",
    "Fitting Prep": "assets/fitting_material_preparation.png",
    "Pipe Prep": "assets/pipe_material_preparation.png",
    "Cutting": "assets/cutting.png",
    "Cold Bending": "assets/cold_bending.png",
    "Mech Fab": "assets/mechanical_fabrication.png",
    "Fitup": "assets/fitup.png",
    "Welding": "assets/welding.png",
    "NDT": "assets/ndt.png",
    "TK": "assets/technical_control.png",
}

STATION_LABELS = {
    "Work Preparation": "Work Prep",
    "PPS": "PPS",
    "Fitting Material Preparation": "Fitting Prep",
    "Pipe Material Preparation": "Pipe Prep",
    "Cutting": "Cutting",
    "Cold Bending": "Cold Bending",
    "Mechanical Fabrication": "Mech Fab",
    "Fitup": "Fitup",
    "Welding": "Welding",
    "NDT": "NDT",
    "Technical Control": "TK",
}

STATIONS_ORDER = list(STATION_LABELS.keys())

# --------------------------------------------------
# SINGLE STATION BLOCK
# --------------------------------------------------
def draw_station(internal_name, spool_counts, red_label_counts):
    # CSS injected every rerun (safe)
    st.markdown(
        """
        <style>
        /* station button */
        div.stButton > button {
            background-color: #1e1e1e !important;
            color: #e0e0e0 !important;
            border-radius: 12px;
            height: 30px;
            padding: 0 10px;
            font-size: 12px;
            font-weight: 600;
            border: 1px solid #333;
            margin-top: 6px;
            white-space: nowrap;
        }
        div.stButton > button:hover {
            background-color: #2a2a2a !important;
            border-color: #444;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    label = STATION_LABELS[internal_name]
    total = spool_counts.get(internal_name, 0)
    red = red_label_counts.get(internal_name, 0)
    image_path = STATION_IMAGES[label]

    # IMAGE
    st.image(image_path, use_container_width=True)

    # CLICKABLE STATION BADGE
    if st.button(label, key=f"station_{internal_name}", use_container_width=True):
        st.session_state.selected_station = internal_name

    # SPACING
    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

    # STACKED METRIC BADGES (NO WRAP, CENTERED)
    st.markdown(
        f"""
        <div style="
            background:#2b3a55;
            color:#e6f0ff;
            border-radius:10px;
            height:28px;
            padding:0 10px;
            font-size:13px;
            font-weight:600;
            display:flex;
            align-items:center;
            justify-content:center;
            white-space:nowrap;
            margin-bottom:4px;
        ">
            Total spools: {total}
        </div>

        <div style="
            background:#5a1f24;
            color:#ffecec;
            border-radius:10px;
            height:26px;
            padding:0 10px;
            font-size:12px;
            font-weight:600;
            display:flex;
            align-items:center;
            justify-content:center;
            white-space:nowrap;
        ">
            Red label: {red}
        </div>
        """,
        unsafe_allow_html=True
    )

# --------------------------------------------------
# SHOPFLOOR LAYOUT (ONE ROW)
# --------------------------------------------------
def draw_shopfloor(spool_counts, red_label_counts):
    st.subheader("🏭 Shopfloor layout")

    cols = st.columns(len(STATIONS_ORDER))

    for col, station in zip(cols, STATIONS_ORDER):
        with col:
            draw_station(station, spool_counts, red_label_counts)
