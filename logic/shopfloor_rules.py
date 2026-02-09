import pandas as pd

STATIONS = [
    "Work Preparation",
    "PPS",
    "Fitting Material Preparation",
    "Pipe Material Preparation",
    "Cutting",
    "Mechanical Fabrication",
    "Fitup",
    "Welding",
    "Cold Bending",
    "Induction Bending",
    "NDT",
    "RT",
    "Technical Control",
    "Documentation",
]

WITNESS_STATIONS = {
    "Cutting",
    "Mechanical Fabrication",
    "Fitup",
    "Welding",
    "Cold Bending",
    "Induction Bending",
    "NDT",
    "RT",
    "Technical Control",
}

HOLD_STATIONS = {
    "Technical Control",
}

ROUTES_BY_SPOOL_TYPE = {
    "TK": [
        "Work Preparation",
        "PPS",
        "Pipe Material Preparation",
        "Mechanical Fabrication",
        "Fitup",
        "Technical Control",
        "Documentation",
    ],
    "SW": [
        "Work Preparation",
        "PPS",
        "Fitting Material Preparation",
        "Pipe Material Preparation",
        "Cutting",
        "Mechanical Fabrication",
        "Fitup",
        "Welding",
        "NDT",
        "RT",
        "Technical Control",
        "Documentation",
    ],
    "KRB o.": [
        "Work Preparation",
        "PPS",
        "Pipe Material Preparation",
        "Cutting",
        "Cold Bending",
        "Fitup",
        "NDT",
        "Technical Control",
        "Documentation",
    ],
    "KRB m.": [
        "Work Preparation",
        "PPS",
        "Fitting Material Preparation",
        "Pipe Material Preparation",
        "Cutting",
        "Cold Bending",
        "Mechanical Fabrication",
        "Fitup",
        "Welding",
        "NDT",
        "RT",
        "Technical Control",
        "Documentation",
    ],
}


def evaluate_heat_map(quality, pressure):
    red_label = False
    hold_possible = False

    if quality in {"Q1", "Q2", "Q3"} and pressure in {"I", "II", "III"}:
        red_label = True

    if quality in {"Q2", "Q3"} and pressure in {"II", "III"}:
        hold_possible = True

    return red_label, hold_possible


def calculate_inspection_load(spools_df: pd.DataFrame):
    inspection_load = {
        station: {"WITNESS": 0, "HOLD": 0}
        for station in STATIONS
    }

    for _, spool in spools_df.iterrows():
        spool_type = spool.get("var_workBookType")
        quality = spool.get("quality_class")
        pressure = spool.get("pressure_risk")

        if spool_type not in ROUTES_BY_SPOOL_TYPE:
            continue

        red_label, hold_possible = evaluate_heat_map(quality, pressure)
        if not red_label:
            continue

        for station in ROUTES_BY_SPOOL_TYPE[spool_type]:
            if hold_possible and station in HOLD_STATIONS:
                inspection_load[station]["HOLD"] += 1
            elif station in WITNESS_STATIONS:
                inspection_load[station]["WITNESS"] += 1

    return inspection_load
