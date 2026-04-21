import pandas as pd

STATUS_GROUPS = {
    "cancelled": "cancelled",
    "done": "closed",
    "completed": "closed",
    "in-progress": "open",
    "in-edit": "open",
    "not-started": "open",
    "scheduled": "open",
    "paused": "open",
    "problem": "open",
}

OPEN_GROUPS = {"open", "unknown"}


def normalize_status_group(status: str) -> str:
    value = "" if pd.isna(status) else str(status).strip().lower()
    if not value:
        return "unknown"
    return STATUS_GROUPS.get(value, "unknown")


def add_operations1_columns(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()

    result["state_group"] = result["state"].apply(normalize_status_group)
    result["is_real_spool"] = result["var_ISOworkbookId"].fillna("").astype(str).str.strip().ne("")

    today = pd.Timestamp.today().normalize()
    start_dates = pd.to_datetime(result["start_date"], errors="coerce")
    result["age_days"] = (today - start_dates.dt.normalize()).dt.days
    result.loc[result["age_days"].lt(0), "age_days"] = pd.NA
    result["age_days"] = result["age_days"].astype("Int64")

    return result


def build_operations1_checks(df: pd.DataFrame) -> pd.DataFrame:
    normalized = add_operations1_columns(df)
    rows = []

    missing_sheet = normalized[~normalized["is_real_spool"]]
    if not missing_sheet.empty:
        rows.append(_check_row(
            severity="High",
            category="Identity",
            check="Missing sheet number",
            sheet_no="",
            revisions="",
            statuses=_format_values(missing_sheet["state"]),
            stations=_format_values(missing_sheet["class_Station"]),
            row_count=len(missing_sheet),
            message="Rows without ISO/sheet number cannot be tracked as spools.",
        ))

    unknown_status = normalized[normalized["state_group"].eq("unknown")]
    if not unknown_status.empty:
        rows.append(_check_row(
            severity="Medium",
            category="Status",
            check="Unknown status value",
            sheet_no="",
            revisions="",
            statuses=_format_values(unknown_status["state"]),
            stations="",
            row_count=len(unknown_status),
            message="Status is not in the normalized Operations1 status list.",
        ))

    spool_rows = normalized[normalized["is_real_spool"]].copy()

    for (sheet_no, revision), group in spool_rows.groupby(
        ["var_ISOworkbookId", "var_ex_internal_rev"], dropna=False
    ):
        open_rows = group[group["state_group"].isin(OPEN_GROUPS)]
        if len(open_rows) > 1:
            rows.append(_check_row(
                severity="High",
                category="Duplicate",
                check="Same revision open more than once",
                sheet_no=sheet_no,
                revisions=revision,
                statuses=_format_values(open_rows["state"]),
                stations=_format_values(open_rows["class_Station"]),
                row_count=len(open_rows),
                message="Same sheet number and internal revision has multiple non-closed/non-cancelled rows.",
            ))

    for sheet_no, group in spool_rows.groupby("var_ISOworkbookId", dropna=False):
        open_rows = group[group["state_group"].isin(OPEN_GROUPS)]
        open_revisions = sorted(
            rev for rev in open_rows["var_ex_internal_rev"].dropna().astype(str).unique() if rev
        )
        if len(open_revisions) > 1:
            rows.append(_check_row(
                severity="High",
                category="Revision",
                check="Multiple open revisions",
                sheet_no=sheet_no,
                revisions=", ".join(open_revisions),
                statuses=_format_values(open_rows["state"]),
                stations=_format_values(open_rows["class_Station"]),
                row_count=len(open_rows),
                message="Same sheet number has more than one internal revision still open.",
            ))

        if len(group) > 1 and open_rows.empty:
            rows.append(_check_row(
                severity="Info",
                category="Duplicate",
                check="Duplicate only in closed/cancelled rows",
                sheet_no=sheet_no,
                revisions=_format_values(group["var_ex_internal_rev"]),
                statuses=_format_values(group["state"]),
                stations=_format_values(group["class_Station"]),
                row_count=len(group),
                message="Repeated sheet number exists only in closed or cancelled rows.",
            ))
        elif len(group) > 1:
            cancelled_or_closed = group[group["state_group"].isin({"cancelled", "closed"})]
            if not cancelled_or_closed.empty:
                rows.append(_check_row(
                    severity="Info",
                    category="Duplicate",
                    check="Open row with closed/cancelled history",
                    sheet_no=sheet_no,
                    revisions=_format_values(group["var_ex_internal_rev"]),
                    statuses=_format_values(group["state"]),
                    stations=_format_values(group["class_Station"]),
                    row_count=len(group),
                    message="Sheet number repeats, but at least one row is closed or cancelled. Review only if unexpected.",
                ))

    if not rows:
        return pd.DataFrame(columns=[
            "severity",
            "category",
            "check",
            "sheet_no",
            "revisions",
            "statuses",
            "stations",
            "row_count",
            "message",
        ])

    return pd.DataFrame(rows)


def filter_checks_for_spools(checks: pd.DataFrame, df_view: pd.DataFrame) -> pd.DataFrame:
    if checks.empty:
        return checks

    sheet_nos = set(df_view["var_ISOworkbookId"].fillna("").astype(str))
    return checks[
        checks["sheet_no"].eq("") | checks["sheet_no"].astype(str).isin(sheet_nos)
    ].copy()


def _check_row(severity, category, check, sheet_no, revisions, statuses, stations, row_count, message):
    return {
        "severity": severity,
        "category": category,
        "check": check,
        "sheet_no": sheet_no,
        "revisions": revisions,
        "statuses": statuses,
        "stations": stations,
        "row_count": row_count,
        "message": message,
    }


def _format_values(series: pd.Series) -> str:
    values = sorted(
        value for value in series.dropna().astype(str).str.strip().unique() if value
    )
    return ", ".join(values)
