import pandas as pd


def load_tasks(path: str) -> pd.DataFrame:
    """
    Učitava Tasks sheet iz Operations1 exporta.
    Taskovi se NE sortiraju (redoslijed nije definiran).
    """

    df = pd.read_excel(
        path,
        sheet_name="Tasks"
    )

    # Normalizacija ključa (order_id)
    df["order_id"] = (
        df["order_id"]
        .astype(str)
        .str.strip()
    )

    # Sigurnost – popuni prazna polja
    for col in ["task_name", "task_description", "state", "assigned_Groups"]:
        if col in df.columns:
            df[col] = df[col].fillna("")

    return df
