import re

import pandas as pd
"""
DATA LAYER - Spools

Loads and normalizes spool data from MES Excel export.

Responsibilities:
- Read raw spool data from Excel
- Normalize identifiers (ISO, revision, text fields)
- Derive Red label flags
- Split active vs archived spools
- Detect data integrity issues:
    - duplicate active spools
    - archived/completed conflicts

Architectural rules:
- No Streamlit imports
- No UI logic
- No shopfloor or routing logic
- Side-effect free (pure data processing)
"""


CUTOFF_DATE = pd.Timestamp("2026-03-30")

OPEN_STATES = {
    "in-progress",
    "in-edit",
    "not-started",
    "scheduled",
    "paused",
    "problem",
}
CANCELLED_STATES = {"cancelled"}
CLOSED_STATES = {"done", "completed"}

COLUMN_ALIASES = {
    "id": ["id", "order_id", "order id", "orderid"],
    "name": ["name"],
    "archived": ["archived", "archive"],
    "state": ["state", "status"],
    "start_date": ["start_date", "start date", "startdate", "order start date"],
    "class_Station": ["class_Station", "Station", "station", "class station"],
    "var_ISOworkbookId": [
        "var_ISOworkbookId",
        "ISOworkbookId",
        "ISO workbook ID",
        "ISO workbook id",
        "iso_workbook_id",
        "iso workbook",
    ],
    "var_ex_internal_rev": [
        "var_ex_internal_rev",
        "ex_internal_rev",
        "internal_rev",
        "internal revision",
        "revision",
    ],
    "var_workBookType": [
        "var_workBookType",
        "workBookType",
        "workbook type",
        "work_book_type",
        "spool type",
    ],
    "class_Quality class": [
        "class_Quality class",
        "Quality class",
        "quality_class",
        "quality class",
    ],
    "class_Pressure Risk Category": [
        "class_Pressure Risk Category",
        "Pressure Risk Category",
        "pressure_risk",
        "pressure risk",
        "pressure risk category",
    ],
}


def _column_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value).replace("\u00a0", " ").lower())


def _normalize_headers(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(col).replace("\u00a0", " ").strip() for col in df.columns]

    lookup = {_column_key(col): col for col in df.columns}

    for canonical, aliases in COLUMN_ALIASES.items():
        if canonical in df.columns:
            continue

        source = next(
            (lookup[_column_key(alias)] for alias in aliases if _column_key(alias) in lookup),
            None,
        )
        if source is not None:
            df[canonical] = df[source]

    return df


def _ensure_column(df: pd.DataFrame, column: str, default="") -> None:
    if column not in df.columns:
        df[column] = default


def _normalize_archived(series: pd.Series) -> pd.Series:
    if pd.api.types.is_bool_dtype(series):
        return series.fillna(False)

    normalized = series.fillna(False)
    if pd.api.types.is_numeric_dtype(normalized):
        return normalized.astype(bool)

    return (
        normalized.astype(str)
        .str.strip()
        .str.lower()
        .isin({"true", "1", "yes", "y", "archived"})
    )


def _clean_text(series: pd.Series, default="") -> pd.Series:
    return (
        series.fillna(default)
        .astype(str)
        .str.replace("\u00a0", " ", regex=False)
        .str.strip()
    )

def _format_values(series: pd.Series) -> str:
    values = sorted(
        value for value in series.dropna().astype(str).str.strip().unique() if value
    )
    return ", ".join(values)


def _build_duplicate_issues(active_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    spool_rows = active_df[active_df["var_ISOworkbookId"].ne("")]

    for sheet_no, group in spool_rows.groupby("var_ISOworkbookId", dropna=False):
        if len(group) <= 1:
            continue

        open_rows = group[group["state"].isin(OPEN_STATES)]
        cancelled_rows = group[group["state"].isin(CANCELLED_STATES)]
        closed_rows = group[group["state"].isin(CLOSED_STATES)]
        history_rows = pd.concat([cancelled_rows, closed_rows])

        open_revisions = sorted(
            rev for rev in open_rows["var_ex_internal_rev"].dropna().astype(str).unique() if rev
        )

        if len(open_rows) > 1 and len(open_revisions) > 1:
            severity = "High"
            issue = "Multiple open revisions"
            action = "Problem: more than one revision is still active/open."
        elif len(open_rows) > 1:
            severity = "High"
            issue = "Same revision open more than once"
            action = "Problem: duplicate open rows exist for the same revision."
        elif len(open_rows) == 1 and not history_rows.empty:
            severity = "Medium"
            issue = "Open row with cancelled/closed older version"
            action = "Review: usually acceptable when the older revision is cancelled/closed."
        elif len(open_rows) == 1:
            severity = "Medium"
            issue = "Single open row with duplicate history"
            action = "Review duplicate history for this workbook."
        else:
            severity = "Low"
            issue = "Only cancelled/closed duplicate history"
            action = "Usually OK: no open duplicate rows remain."

        rows.append({
            "severity": severity,
            "issue": issue,
            "var_ISOworkbookId": sheet_no,
            "revisions": _format_values(group["var_ex_internal_rev"]),
            "open_revisions": ", ".join(open_revisions),
            "states": _format_values(group["state"]),
            "stations": _format_values(group["class_Station"]),
            "row_count": len(group),
            "open_count": len(open_rows),
            "cancelled_count": len(cancelled_rows),
            "closed_count": len(closed_rows),
            "action": action,
        })

    if not rows:
        return pd.DataFrame(columns=[
            "severity",
            "issue",
            "var_ISOworkbookId",
            "revisions",
            "open_revisions",
            "states",
            "stations",
            "row_count",
            "open_count",
            "cancelled_count",
            "closed_count",
            "action",
        ])

    severity_order = {"High": 0, "Medium": 1, "Low": 2}
    result = pd.DataFrame(rows)
    result["_severity_order"] = result["severity"].map(severity_order).fillna(9)
    return result.sort_values(["_severity_order", "var_ISOworkbookId"]).drop(columns="_severity_order")


def _add_start_week_columns(df: pd.DataFrame) -> pd.DataFrame:
    start_dates = pd.to_datetime(df["start_date"], errors="coerce", utc=True)
    iso_calendar = start_dates.dt.isocalendar()

    df["start_date"] = start_dates.dt.tz_convert(None)
    df["start_year"] = iso_calendar["year"].astype("Int64")
    df["start_week"] = iso_calendar["week"].astype("Int64")
    df["start_year_week"] = "No start date"

    has_week = df["start_year"].notna() & df["start_week"].notna()
    df.loc[has_week, "start_year_week"] = [
        f"{int(year)}-W{int(week):02d}"
        for year, week in zip(df.loc[has_week, "start_year"], df.loc[has_week, "start_week"])
    ]

    return df


def load_spools(path: str):
    df = _normalize_headers(pd.read_excel(path))

    for column in [
        "id",
        "name",
        "archived",
        "state",
        "start_date",
        "class_Station",
        "var_ISOworkbookId",
        "var_ex_internal_rev",
        "var_workBookType",
        "class_Quality class",
        "class_Pressure Risk Category",
    ]:
        _ensure_column(df, column, False if column == "archived" else "")

    # -----------------------------
    # NORMALIZE - BASIC
    # -----------------------------
    df["archived"] = _normalize_archived(df["archived"])
    df["state"] = _clean_text(df["state"]).str.lower()
    df["class_Station"] = _clean_text(df["class_Station"], "Unknown").replace("", "Unknown")
    df = _add_start_week_columns(df)
    df = df[df["start_date"].notna() & (df["start_date"] >= CUTOFF_DATE)].copy()

    # -----------------------------
    # NORMALIZE - IDENTIFIERS
    # -----------------------------
    df["id"] = _clean_text(df["id"])
    df["var_ISOworkbookId"] = _clean_text(df["var_ISOworkbookId"]).str.split(".").str[0]
    df["var_ex_internal_rev"] = _clean_text(df["var_ex_internal_rev"]).str.split(".").str[0]

    # -----------------------------
    # NORMALIZE - SPOOL TYPE
    # -----------------------------
    df["var_workBookType"] = _clean_text(df["var_workBookType"]).str.strip("()")

    # -----------------------------
    # INSPECTION - MAP MES FIELDS
    # -----------------------------
    df["quality_class"] = _clean_text(df["class_Quality class"])
    df["pressure_risk"] = _clean_text(df["class_Pressure Risk Category"])

    # -----------------------------
    # RED LABEL
    # -----------------------------
    df["label_type"] = df["name"].fillna("").astype(str).apply(
        lambda x: "Red label"
        if x.strip().lower().endswith("red label")
        else "Standard"
    )
    df["is_red_label"] = df["label_type"] == "Red label"

    # -----------------------------
    # ACTIVE / ARCHIVED SPLIT
    # -----------------------------
    active_df = df[df["archived"] == False].copy()

    archived_completed = df[
        (df["archived"] == True) & (df["state"] == "completed")
    ]

    # -----------------------------
    # CHECK 1 - ARCHIVE CONFLICTS
    # -----------------------------
    archive_conflicts = archived_completed[
        archived_completed["var_ISOworkbookId"].isin(
            active_df["var_ISOworkbookId"]
        )
    ][["var_ISOworkbookId"]].drop_duplicates()

    # -----------------------------
    # CHECK 2 - DUPLICATES / REVISIONS (ACTIVE)
    # -----------------------------
    duplicates = _build_duplicate_issues(active_df)

    return active_df, duplicates, archive_conflicts

