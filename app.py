import streamlit as st
import pandas as pd

from data.loader import load_spools
from data.loader_tasks import load_tasks
from layout.shopfloor import draw_shopfloor
from ui.spool_detail import render_spool_detail
from views.inspection import render_inspection


inspection_df, _, _ = load_spools("spools.xlsx")

"""
Main Streamlit application entry point.

Responsibilities:
- Define page configuration and global layout
- Orchestrate views and tabs
- Connect data layer with UI components

IMPORTANT:
- This file is intentionally kept thin and stable
- No business logic
- No data normalization
- No heavy computations

This file is considered LOCKED.
"""

# --------------------------------------------------
# BASIC APP CONFIG
# --------------------------------------------------
st.set_page_config(
    page_title="Spool Tracking",
    layout="wide"
)

# --------------------------------------------------
# CONSTANTS
# --------------------------------------------------
STATUS_COLORS = {
    "cancelled": "#d32f2f",
    "problem": "#f57c00",
    "in-progress": "#1976d2",
    "in-edit": "#9e9e9e",
    "completed": "#388e3c",
}

# --------------------------------------------------
# HELPERS
# --------------------------------------------------
def style_rows(row):
    color = STATUS_COLORS.get(row["state"])
    if color:
        return [f"color: {color}"] * len(row)
    return [""] * len(row)

def apply_search(df, search_text):
    if not search_text:
        return df

    terms = [
        t.strip().lower()
        for t in search_text.replace(",", " ").split()
        if t.strip()
    ]

    mask = pd.Series(False, index=df.index)

    for term in terms:
        term_mask = pd.Series(False, index=df.index)
        for col in df.columns:
            term_mask |= (
                df[col]
                .fillna("")
                .astype(str)
                .str.lower()
                .str.contains(term, na=False)
            )
        mask |= term_mask

    return df[mask]

def inject_status_radio_colors():
    st.markdown(
        """
        <style>
        div[data-baseweb="radio"] label span { font-weight:600; }
        div[data-baseweb="radio"] label span:contains("cancelled") { color:#d32f2f; }
        div[data-baseweb="radio"] label span:contains("completed") { color:#388e3c; }
        div[data-baseweb="radio"] label span:contains("in-progress") { color:#1976d2; }
        div[data-baseweb="radio"] label span:contains("in-edit") { color:#9e9e9e; }
        div[data-baseweb="radio"] label span:contains("problem") { color:#f57c00; }
        </style>
        """,
        unsafe_allow_html=True
    )

# --------------------------------------------------
# WORK PREPARATION VIEW
# --------------------------------------------------
def render_work_preparation():
    st.markdown("### Stainless Steel · Work Preparation")

    # LOAD DATA
    df, duplicates, archive_conflicts = load_spools("spools.xlsx")
    tasks_df = load_tasks("operations1_tasks.xlsx")

    df = df.copy()
    df["id"] = df["id"].astype(str)
    tasks_df["order_id"] = tasks_df["order_id"].astype(str)

    # FIX REVISION DISPLAY
    df["var_ex_internal_rev"] = (
        df["var_ex_internal_rev"]
        .astype(str)
        .str.split(".")
        .str[0]
        .str.zfill(3)
    )

    # TASK COUNT
    task_counts = tasks_df.groupby("order_id").size().to_dict()
    df["task_count"] = df["id"].map(task_counts).fillna(0).astype(int)

    # WARNINGS
    if not duplicates.empty:
        st.warning("Duplicate active spools detected")
        st.dataframe(duplicates, use_container_width=True)

    if not archive_conflicts.empty:
        st.error("Archived completed spool conflict detected")
        st.dataframe(archive_conflicts, use_container_width=True)

    # SHOPFLOOR COUNTS
    spool_counts = (
        df.groupby("class_Station")["var_ISOworkbookId"]
        .nunique()
        .to_dict()
    )

    red_label_counts = (
        df[df["is_red_label"]]
        .groupby("class_Station")["var_ISOworkbookId"]
        .nunique()
        .to_dict()
    )

    draw_shopfloor(spool_counts, red_label_counts)

    # FILTER BY STATION
    if "selected_station" in st.session_state:
        df_view = df[df["class_Station"] == st.session_state.selected_station]
        st.markdown(f"#### Spools at station: **{st.session_state.selected_station}**")
    else:
        df_view = df.copy()
        st.markdown("#### All active spools")

    # SEARCH
    search_text = st.text_input(
        "Search",
        placeholder="Examples: ISO123, Q2 II, Welding, Red label, in-progress",
        key="search_wp"
    )

    inject_status_radio_colors()

    # STATUS FILTER WITH COUNTS
    status_counts = df_view["state"].value_counts().to_dict()
    statuses = ["All"] + [
        f"{s} ({status_counts.get(s, 0)})"
        for s in sorted(status_counts.keys())
    ]

    status_filter = st.radio(
        "Filter by status",
        statuses,
        horizontal=True,
        key="status_wp"
    )

    df_filtered = apply_search(df_view, search_text)

    if status_filter != "All":
        status_name = status_filter.split(" (")[0]
        df_filtered = df_filtered[df_filtered["state"] == status_name]

    # SORT OPTIONS
    with st.expander("🔃 Sort options"):
        sort_primary = st.selectbox(
            "Primary sort",
            ["None", "label_type", "class_Station", "state", "task_count"]
        )

        sort_secondary = st.selectbox(
            "Secondary sort",
            ["None", "class_Station", "label_type", "state", "task_count"]
        )

        sort_order = st.radio(
            "Order",
            ["Ascending", "Descending"],
            horizontal=True
        )

    sort_cols = []
    ascending = []

    if sort_primary != "None":
        sort_cols.append(sort_primary)
        ascending.append(sort_order == "Ascending")

    if sort_secondary != "None" and sort_secondary != sort_primary:
        sort_cols.append(sort_secondary)
        ascending.append(sort_order == "Ascending")

    if sort_cols:
        df_filtered = df_filtered.sort_values(
            by=sort_cols,
            ascending=ascending,
            kind="mergesort"
        )

    # TABLE
    table_cols = [
        "var_ISOworkbookId",
        "var_ex_internal_rev",
        "var_workBookType",
        "label_type",
        "state",
        "class_Station",
        "task_count",
    ]

    table = st.dataframe(
        df_filtered[table_cols]
        .style
        .apply(style_rows, axis=1),
        use_container_width=True,
        hide_index=True,
        selection_mode="single-row",
        on_select="rerun",
    )

    # DETAIL VIEW
    if table.selection.rows:
        idx = table.selection.rows[0]
        spool_row = df_filtered.iloc[idx]

        selected_id = spool_row["id"]
        spool_tasks = tasks_df[tasks_df["order_id"] == selected_id]

        st.markdown("---")
        render_spool_detail(spool_row, spool_tasks)

# --------------------------------------------------
# TABS
# --------------------------------------------------
plant_tabs = st.tabs([
    "⚙️ Carbon Steel",
    "🧪 Stainless Steel"
])

with plant_tabs[0]:
    st.info("Carbon Steel views not enabled yet.")

with plant_tabs[1]:
    dept_tabs = st.tabs([
        "🛠 Work Preparation",
        "🔍 Inspection"
    ])

    with dept_tabs[0]:
        render_work_preparation()

    with dept_tabs[1]:
        render_inspection(inspection_df)
