import pandas as pd
"""
DATA LAYER – Spools

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


def load_spools(path: str):
    df = pd.read_excel(path)

    # -----------------------------
    # NORMALIZE – BASIC
    # -----------------------------
    df["archived"] = df["archived"].fillna(False)
    df["state"] = df["state"].fillna("").str.lower()

    df["class_Station"] = (
        df["class_Station"]
        .fillna("Unknown")
        .astype(str)
        .str.replace("\u00a0", " ", regex=False)
        .str.strip()
    )

    # -----------------------------
    # NORMALIZE – ISO WORKBOOK ID
    # -----------------------------
    df["var_ISOworkbookId"] = (
        df["var_ISOworkbookId"]
        .astype(str)
        .str.split(".")
        .str[0]
    )

    # -----------------------------
    # NORMALIZE – SPOOL TYPE
    # -----------------------------
    df["var_workBookType"] = (
        df["var_workBookType"]
        .astype(str)
        .str.strip()
        .str.strip("()")
    )

    # -----------------------------
    # INSPECTION – MAP MES FIELDS
    # -----------------------------
    df["quality_class"] = (
        df["class_Quality class"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    df["pressure_risk"] = (
        df["class_Pressure Risk Category"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    # -----------------------------
    # RED LABEL
    # -----------------------------
    df["label_type"] = df["name"].fillna("").apply(
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
    # CHECK 1 – ARCHIVE CONFLICTS
    # -----------------------------
    archive_conflicts = archived_completed[
        archived_completed["var_ISOworkbookId"].isin(
            active_df["var_ISOworkbookId"]
        )
    ][["var_ISOworkbookId"]].drop_duplicates()

    # -----------------------------
    # CHECK 2 – DUPLICATES (ACTIVE)
    # -----------------------------
    dup_rows = active_df[
        active_df.duplicated("var_ISOworkbookId", keep=False)
    ]

    duplicates = (
        dup_rows.groupby("var_ISOworkbookId")["class_Station"]
        .apply(list)
        .reset_index()
        .rename(columns={"class_Station": "stations"})
    )

    return active_df, duplicates, archive_conflicts
