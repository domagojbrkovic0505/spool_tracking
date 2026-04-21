import re

import pandas as pd


PM_PATH = (
    r"C:\Users\domag\spool_tracking_backup_20260421_212416"
    r"\Piping manager-SCM_Weekly_Reporting.xlsx"
)


def _clean_text(series: pd.Series) -> pd.Series:
    return (
        series.fillna("")
        .astype(str)
        .str.replace("\u00a0", " ", regex=False)
        .str.strip()
        .str.replace(r"\.0$", "", regex=True)
    )


def _normalize_week(value) -> str:
    text = "" if pd.isna(value) else str(value).strip()
    if not text or text.lower() == "nan":
        return ""

    match = re.match(r"^(\d{4})[-_/ ]?W?(\d{1,2})$", text, flags=re.IGNORECASE)
    if not match:
        return text

    year, week = match.groups()
    return f"{int(year)}-W{int(week):02d}"


def load_piping_manager_checks(path: str = PM_PATH) -> pd.DataFrame:
    df = pd.read_excel(
        path,
        sheet_name="SCM_Weekly_Reporting",
        header=1,
        dtype=str,
        usecols=lambda column: column
        in {
            "SHEET NO",
            "PART LIST STATE",
            "AV READY KW",
        },
    )

    result = pd.DataFrame()
    result["var_ISOworkbookId"] = _clean_text(df["SHEET NO"])
    result["pm_part_list_state"] = _clean_text(df["PART LIST STATE"])
    result["pm_av_ready_week"] = df["AV READY KW"].apply(_normalize_week)

    result = result[result["var_ISOworkbookId"].ne("")]
    result = result.drop_duplicates("var_ISOworkbookId", keep="first")

    return result

