import streamlit as st
import pandas as pd

from data.loader import load_spools
from data.loader_tasks import load_tasks
from data.loader_piping_manager import load_piping_manager_checks
from layout.shopfloor import draw_shopfloor
from ui.spool_detail import render_spool_detail
from views.inspection import render_inspection


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


def get_week_options(df):
    week_rows = (
        df[df["start_year_week"] != "No start date"]
        [["start_year", "start_week", "start_year_week"]]
        .dropna(subset=["start_year", "start_week"])
        .drop_duplicates()
        .sort_values(["start_year", "start_week"], ascending=False)
    )

    options = ["All weeks"] + week_rows["start_year_week"].tolist()

    if (df["start_year_week"] == "No start date").any():
        options.append("No start date")

    return options


def render_data_source_sidebar():
    st.sidebar.header("Data files")
    st.sidebar.caption("Upload files for web use. Leave empty to use local files on this PC.")

    spools_file = st.sidebar.file_uploader(
        "Operations1 spools export",
        type=["xlsx"],
        key="spools_upload",
    )
    tasks_file = st.sidebar.file_uploader(
        "Operations1 tasks export",
        type=["xlsx"],
        key="tasks_upload",
    )
    piping_manager_file = st.sidebar.file_uploader(
        "Piping Manager export",
        type=["xlsx"],
        key="pm_upload",
    )

    return spools_file, tasks_file, piping_manager_file


def get_data_sources():
    spools_file, tasks_file, piping_manager_file = render_data_source_sidebar()

    return {
        "spools": spools_file if spools_file is not None else "spools.xlsx",
        "tasks": tasks_file if tasks_file is not None else "operations1_tasks.xlsx",
        "piping_manager": (
            piping_manager_file
            if piping_manager_file is not None
            else "Piping manager-SCM_Weekly_Reporting.xlsx"
        ),
    }

def render_duplicate_metric(title, value, detail):
    st.metric(title, value, detail)


def render_duplicate_issue_rows(df, duplicate_cases, severity, issue, expanded=False):
    issue_cases = duplicate_cases[duplicate_cases["issue"] == issue]
    workbook_ids = set(issue_cases["var_ISOworkbookId"].astype(str))
    issue_rows = df[df["var_ISOworkbookId"].astype(str).isin(workbook_ids)].copy()

    duplicate_info = issue_cases.set_index("var_ISOworkbookId")
    issue_rows["issue"] = issue_rows["var_ISOworkbookId"].map(duplicate_info["issue"])
    issue_rows["action"] = issue_rows["var_ISOworkbookId"].map(duplicate_info["action"])

    issue_rows = issue_rows.sort_values(
        ["var_ISOworkbookId", "var_ex_internal_rev", "state"],
        kind="mergesort",
    )

    table_cols = [
        "var_ISOworkbookId",
        "var_ex_internal_rev",
        "var_workBookType",
        "label_type",
        "state",
        "class_Station",
        "start_year_week",
        "issue",
        "action",
        "task_count",
    ]

    title = f"{issue} ({len(issue_cases)} workbooks, {len(issue_rows)} rows)"
    with st.expander(title, expanded=expanded):
        st.dataframe(issue_rows[table_cols], use_container_width=True, hide_index=True)


def render_duplicate_severity(df, duplicates, severity, expanded=False):
    severity_cases = duplicates[duplicates["severity"] == severity]
    if severity_cases.empty:
        return

    workbook_ids = set(severity_cases["var_ISOworkbookId"].astype(str))
    severity_rows = df[df["var_ISOworkbookId"].astype(str).isin(workbook_ids)]
    title = f"{severity} severity duplicate issues ({len(severity_cases)} workbooks, {len(severity_rows)} rows)"

    with st.expander(title, expanded=expanded):
        for issue in severity_cases["issue"].dropna().unique():
            render_duplicate_issue_rows(
                df,
                severity_cases,
                severity,
                issue,
                expanded=severity == "High",
            )


def render_duplicate_review(df, duplicates):
    if duplicates.empty:
        return

    severity_counts = duplicates["severity"].value_counts().to_dict()
    high_count = severity_counts.get("High", 0)
    medium_count = severity_counts.get("Medium", 0)
    low_count = severity_counts.get("Low", 0)
    duplicate_count = duplicates["var_ISOworkbookId"].nunique()
    affected_rows = df[df["var_ISOworkbookId"].astype(str).isin(set(duplicates["var_ISOworkbookId"].astype(str)))]
    affected_stations = affected_rows["class_Station"].nunique()

    st.warning(f"Duplicate active spools detected: {duplicate_count} workbooks require your attention.")

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        render_duplicate_metric("High severity", high_count, "Problem")
    with col2:
        render_duplicate_metric("Medium severity", medium_count, "Review")
    with col3:
        render_duplicate_metric("Low severity", low_count, "History")
    with col4:
        render_duplicate_metric("Duplicate workbooks", duplicate_count, "Workbook IDs")
    with col5:
        render_duplicate_metric("Affected stations", affected_stations, "Stations")

    render_duplicate_severity(df, duplicates, "High", expanded=True)
    render_duplicate_severity(df, duplicates, "Medium", expanded=False)
    render_duplicate_severity(df, duplicates, "Low", expanded=False)

def add_piping_manager_columns(df, pm_df):
    result = df.copy()
    pm_lookup = pm_df.set_index("var_ISOworkbookId")

    result["pm_part_list_state"] = result["var_ISOworkbookId"].map(pm_lookup["pm_part_list_state"]).fillna("")
    result["pm_av_ready_week"] = result["var_ISOworkbookId"].map(pm_lookup["pm_av_ready_week"]).fillna("")
    result["pm_match_status"] = result["pm_part_list_state"].apply(
        lambda value: "Matched" if value else "Missing in Piping Manager"
    )

    pm_checks = result.apply(evaluate_piping_manager_row, axis=1, result_type="expand")
    result["pm_check_severity"] = pm_checks[0]
    result["pm_check_category"] = pm_checks[1]
    result["pm_check"] = pm_checks[2]
    result["pm_action"] = pm_checks[3]

    return result


def evaluate_piping_manager_row(row):
    state = str(row.get("pm_part_list_state", "")).strip()
    station = str(row.get("class_Station", "")).strip()
    mes_week = str(row.get("start_year_week", "")).strip()
    pm_week = str(row.get("pm_av_ready_week", "")).strip()

    if not state:
        return (
            "High",
            "Missing in PM",
            "Missing in Piping Manager",
            "Workbook from Operations1 was not found in Piping Manager.",
        )

    if state == "5":
        return (
            "Medium",
            "PM Hold",
            "Part list on hold",
            "Review hold status in Piping Manager.",
        )

    if state in {"15", "16"}:
        if not pm_week:
            return (
                "High",
                "AV Week Missing",
                "Missing AV READY KW",
                "Material tested/reserved, but Piping Manager AV READY KW is empty.",
            )
        if mes_week and mes_week != "No start date" and mes_week == pm_week:
            return (
                "OK",
                "OK",
                "Material tested/reserved - AV week OK",
                "No action.",
            )
        return (
            "Medium",
            "AV Week Mismatch",
            "AV week mismatch",
            "Operations1 start week does not match Piping Manager AV READY KW.",
        )

    if state == "2":
        if station == "Work Preparation":
            return (
                "Medium",
                "Status/Station",
                "Fully planned but still in Work Preparation",
                "State 2 should be at PPS or past PPS, not Work Preparation.",
            )
        return (
            "OK",
            "OK",
            "Fully planned - station OK",
            "No action.",
        )

    return (
        "OK",
        "OK",
        "No PM rule for this state",
        "No action.",
    )


def render_pm_issue_rows(df, severity_rows, category, check, expanded=False):
    issue_rows = severity_rows[
        (severity_rows["pm_check_category"] == category)
        & (severity_rows["pm_check"] == check)
    ].copy()

    pm_cols = [
        "var_ISOworkbookId",
        "var_ex_internal_rev",
        "var_workBookType",
        "state",
        "class_Station",
        "start_year_week",
        "pm_part_list_state",
        "pm_av_ready_week",
        "pm_check_category",
        "pm_check",
        "pm_action",
    ]

    title = f"{category} - {check} ({len(issue_rows)} rows)"
    with st.expander(title, expanded=expanded):
        st.dataframe(issue_rows[pm_cols], use_container_width=True, hide_index=True)


def render_pm_severity(df, severity, expanded=False):
    severity_rows = df[df["pm_check_severity"] == severity].copy()
    if severity_rows.empty:
        return

    title = f"{severity} severity Piping Manager issues ({len(severity_rows)} rows)"
    with st.expander(title, expanded=expanded):
        issue_groups = (
            severity_rows[["pm_check_category", "pm_check"]]
            .drop_duplicates()
            .sort_values(["pm_check_category", "pm_check"])
        )
        for _, issue in issue_groups.iterrows():
            render_pm_issue_rows(
                df,
                severity_rows,
                issue["pm_check_category"],
                issue["pm_check"],
                expanded=severity == "High",
            )


def render_piping_manager_check(df):
    pm_issue_rows = df[df["pm_check_severity"].isin(["High", "Medium"])]
    matched_count = int(df["pm_match_status"].eq("Matched").sum())
    missing_count = int(df["pm_match_status"].ne("Matched").sum())
    high_count = int(df["pm_check_severity"].eq("High").sum())
    medium_count = int(df["pm_check_severity"].eq("Medium").sum())
    ok_count = int(df["pm_check_severity"].eq("OK").sum())

    if pm_issue_rows.empty:
        st.success("Piping Manager check: no high or medium issues detected.")
    else:
        st.warning(f"Piping Manager check: {len(pm_issue_rows)} rows need review.")

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Matched", matched_count)
    col2.metric("Missing in PM", missing_count)
    col3.metric("High", high_count)
    col4.metric("Medium", medium_count)
    col5.metric("OK", ok_count)

    category_summary = (
        df.groupby(["pm_check_severity", "pm_check_category", "pm_check"])
        .size()
        .reset_index(name="rows")
        .sort_values(["pm_check_severity", "rows"], ascending=[True, False])
    )
    st.dataframe(category_summary, use_container_width=True, hide_index=True)

    render_pm_severity(df, "High", expanded=True)
    render_pm_severity(df, "Medium", expanded=False)
# --------------------------------------------------
# WORK PREPARATION VIEW
# --------------------------------------------------
def render_work_preparation(data_sources):
    st.markdown("### Stainless Steel - Work Preparation")

    # LOAD DATA
    df, duplicates, archive_conflicts = load_spools(data_sources["spools"])
    tasks_df = load_tasks(data_sources["tasks"])
    pm_df = load_piping_manager_checks(data_sources["piping_manager"])

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
    df = add_piping_manager_columns(df, pm_df)

    # WARNINGS
    render_duplicate_review(df, duplicates)
    render_piping_manager_check(df)

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

    # WEEK FILTER
    week_filter = st.selectbox(
        "Production week",
        get_week_options(df),
        key="week_wp",
    )

    if week_filter != "All weeks":
        df = df[df["start_year_week"] == week_filter].copy()

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
    with st.expander("Sort options"):
        sort_primary = st.selectbox(
            "Primary sort",
            ["None", "start_year_week", "label_type", "class_Station", "state", "task_count"]
        )

        sort_secondary = st.selectbox(
            "Secondary sort",
            ["None", "start_year_week", "class_Station", "label_type", "state", "task_count"]
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
        "start_year_week",
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
    "Carbon Steel",
    "Stainless Steel"
])

data_sources = get_data_sources()

try:
    inspection_df, _, _ = load_spools(data_sources["spools"])
except FileNotFoundError:
    st.error(
        "Data files are missing. Upload the Operations1 spools export in the sidebar, "
        "or place spools.xlsx in the app folder."
    )
    st.stop()


with plant_tabs[0]:
    st.info("Carbon Steel views not enabled yet.")

with plant_tabs[1]:
    dept_tabs = st.tabs([
        "Work Preparation",
        "Inspection"
    ])

    with dept_tabs[0]:
        render_work_preparation(data_sources)

    with dept_tabs[1]:
        render_inspection(inspection_df)







