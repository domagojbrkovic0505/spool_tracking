import streamlit as st
from pathlib import Path
import re
import streamlit.components.v1 as components


def render_inspection_flow(inspection_load: dict):
    base_dir = Path(__file__).resolve().parent.parent
    svg_path = base_dir / "assets" / "inspection_main_flow.svg"

    if not svg_path.exists():
        st.warning(f"Inspection flow diagram not found: {svg_path}")
        return

    with open(svg_path, "r", encoding="utf-8") as f:
        svg = f.read()

    # --- SAFE LABEL REPLACEMENT ---
    for station, values in inspection_load.items():
        w = values.get("WITNESS", 0)
        h = values.get("HOLD", 0)

        new_label = (
            f"{station}"
            f"<div>W: {w}</div>"
            f"<div>H: {h}</div>"
        )

        # replace ONLY the label text inside foreignObject
        svg = re.sub(
            rf">(\\s*{re.escape(station)}\\s*)<",
            f">{new_label}<",
            svg,
            count=1
        )

    components.html(
        f"""
        <div style="
            background:#0e1117;
            padding:16px;
            border-radius:12px;
            overflow-x:auto;
        ">
            {svg}
        </div>
        """,
        height=450,
        scrolling=True
    )
