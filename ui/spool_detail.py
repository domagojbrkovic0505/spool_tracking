import streamlit as st
import pandas as pd


def render_spool_detail(spool_row, tasks_df: pd.DataFrame | None = None):
    """
    Spool Detail + OP1 Tasks
    """

    st.subheader("🧵 Spool Detail")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Identification")
        st.markdown(f"**Spool ID:** {spool_row['var_ISOworkbookId']}")
        st.markdown(f"**Revision:** {spool_row['var_ex_internal_rev']}")
        st.markdown(f"**Spool Type (MES):** {spool_row['var_workBookType']}")

    with col2:
        st.markdown("### Status")
        st.markdown(f"**Station:** {spool_row['class_Station']}")
        st.markdown(f"**State:** {spool_row['state']}")
        st.markdown(f"**Label:** {spool_row['label_type']}")

    # --------------------------------------------------
    # TASKS
    # --------------------------------------------------
    st.markdown("---")
    st.subheader("🧩 OP1 Tasks")

    if tasks_df is None or tasks_df.empty:
        st.info("No tasks found for this spool.")
        return

    task_cols = [
        "task_name",
        "task_description",
        "state",
        "assigned_Groups",
    ]

    st.dataframe(
        tasks_df[task_cols],
        use_container_width=True,
        hide_index=True,
    )
