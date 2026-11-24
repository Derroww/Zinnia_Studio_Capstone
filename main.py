import os
from datetime import date, datetime
from collections import Counter
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

import database
from project import ClientProject, STATUSES, SERVICE_TYPES

load_dotenv()
APP_TITLE = os.getenv("APP_TITLE", "Zinnia Studio — Client Project & Quote Tracker")

st.set_page_config(page_title=APP_TITLE, page_icon="🌸", layout="wide")

# Initialize database safely
try:
    database.create_table()
    database.seed_sample_data()
except Exception as e:
    st.error(f"Startup Error: {e}")
    st.stop()

st.title(f"🌸 {APP_TITLE}")
st.caption("Zinnia Interiors & Zinnia Graphics — Track client briefs, deposits, deadlines, and project stages in one place.")

tab_list, tab_add, tab_update, tab_delete, tab_summary = st.tabs([
    "📋 Projects (Read)",
    "➕ New Project (Create)",
    "✏️ Update Stage & Payment",
    "🗑️ Delete Project",
    "📊 Summary & Export"
])

# --- TAB 1: LIST & SEARCH (READ) ---
with tab_list:
    col1, col2 = st.columns([2, 1])
    with col1:
        search_query = st.text_input("Search by client name, project title, or service", placeholder="e.g., Westlands, Logo, Amina...")
    with col2:
        status_choice = st.selectbox("Filter by Status", ["All"] + STATUSES)

    try:
        rows = database.get_projects(search_query, status_choice)
    except Exception as e:
        st.error(str(e))
        rows = []

    if not rows:
        st.info("No projects found matching your filter.")
    else:
        enriched = []
        for r in rows:
            proj = ClientProject(
                r["client_name"], r["phone"], r["service_type"],
                r["project_title"], r["quoted_amount"], r["amount_paid"],
                r["deadline"], r["status"], r["id"]
            )
            enriched.append({
                "ID": r["id"],
                "Client": r["client_name"],
                "Phone": r["phone"],
                "Division / Service": r["service_type"],
                "Project Title": r["project_title"],
                "Status": r["status"],
                "Quoted (KES)": f"{r['quoted_amount']:,.0f}",
                "Paid (KES)": f"{r['amount_paid']:,.0f}",
                "Balance Due (KES)": f"{proj.balance_due():,.0f}",
                "Deadline": r["deadline"],
                "Alert": "⚠️ OVERDUE" if proj.is_overdue() else "✅ On Track"
            })
        st.dataframe(pd.DataFrame(enriched), use_container_width=True, hide_index=True)

# --- TAB 2: ADD PROJECT (CREATE) ---
with tab_add:
    st.subheader("Register a New Zinnia Client Project")
    with st.form("add_project_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            client_name = st.text_input("Client Name *")
            phone = st.text_input("Kenyan Phone Number * (e.g., 0712345678)")
            service_type = st.selectbox("Zinnia Division / Service *", SERVICE_TYPES)
            status = st.selectbox("Initial Stage", STATUSES, index=0)
        with c2:
            project_title = st.text_input("Project Title / Scope *")
            quoted_amount = st.number_input("Quoted Amount (KES) *", min_value=0.0, step=1000.0, value=50000.0)
            amount_paid = st.number_input("Deposit / Amount Paid (KES)", min_value=0.0, step=1000.0, value=0.0)
            deadline = st.date_input("Target Deadline *", value=date.today())

        submitted = st.form_submit_button("Save Project")
        if submitted:
            new_proj = ClientProject(
                client_name=client_name,
                phone=phone,
                service_type=service_type,
                project_title=project_title,
                quoted_amount=quoted_amount,
                amount_paid=amount_paid,
                deadline=deadline.strftime("%Y-%m-%d"),
                status=status
            )
            error_msg = new_proj.is_valid()
            if error_msg:
                st.error(error_msg)
            else:
                try:
                    database.add_project(new_proj)
                    st.success(f"Saved project '{new_proj.project_title}' for {new_proj.client_name}!")
                except Exception as e:
                    st.error(str(e))

# --- TAB 3: UPDATE PROJECT (UPDATE) ---
with tab_update:
    st.subheader("Move Project Stage or Record Deposit Payment")
    all_projects = database.get_projects()
    if not all_projects:
        st.info("No projects available to update.")
    else:
        options = {f"#{p['id']} — {p['client_name']} ({p['project_title']})": p for p in all_projects}
        selected_label = st.selectbox("Select Project to Update", list(options.keys()))
        selected = options[selected_label]

        with st.form("update_project_form"):
            new_status = st.selectbox("Project Stage", STATUSES, index=STATUSES.index(selected["status"]))
            new_paid = st.number_input(
                f"Total Amount Paid (Quoted: KES {selected['quoted_amount']:,.0f})",
                min_value=0.0,
                value=float(selected["amount_paid"]),
                step=1000.0
            )
            current_due = datetime.strptime(selected["deadline"], "%Y-%m-%d").date()
            new_deadline = st.date_input("Target Deadline", value=current_due)

            if st.form_submit_button("Update Project"):
                updated_proj = ClientProject(
                    selected["client_name"], selected["phone"], selected["service_type"],
                    selected["project_title"], selected["quoted_amount"], new_paid,
                    new_deadline.strftime("%Y-%m-%d"), new_status, selected["id"]
                )
                error_msg = updated_proj.is_valid()
                if error_msg:
                    st.error(error_msg)
                else:
                    try:
                        database.update_project(
                            selected["id"], new_status, new_paid, new_deadline.strftime("%Y-%m-%d")
                        )
                        st.success("Project updated successfully! Refreshing view...")
                        st.rerun()
                    except Exception as e:
                        st.error(str(e))

# --- TAB 4: DELETE PROJECT (DELETE) ---
with tab_delete:
    st.subheader("Remove Duplicate or Cancelled Project")
    all_projects = database.get_projects()
    if not all_projects:
        st.info("No projects in database.")
    else:
        del_options = {f"#{p['id']} — {p['client_name']}: {p['project_title']} [{p['status']}]": p["id"] for p in all_projects}
        del_label = st.selectbox("Choose Project to Delete", list(del_options.keys()))
        confirm = st.checkbox("I confirm I want to permanently delete this project record.")
        if st.button("Delete Project", type="primary"):
            if not confirm:
                st.warning("Please check the confirmation box first.")
            else:
                try:
                    database.delete_project(del_options[del_label])
                    st.success("Project deleted.")
                    st.rerun()
                except Exception as e:
                    st.error(str(e))

# --- TAB 5: SUMMARY & CSV EXPORT (SMART FEATURE + EXTRA SKILL) ---
with tab_summary:
    st.subheader("Zinnia Studio Financial & Pipeline Overview")
    all_projects = database.get_projects()
    if not all_projects:
        st.info("Add projects to see summary metrics.")
    else:
        total_quoted = sum(p["quoted_amount"] for p in all_projects)
        total_collected = sum(p["amount_paid"] for p in all_projects)
        total_balance = total_quoted - total_collected

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Projects", len(all_projects))
        m2.metric("Total Quoted (KES)", f"{total_quoted:,.0f}")
        m3.metric("Total Collected (KES)", f"{total_collected:,.0f}")
        m4.metric("Pending Balances (KES)", f"{total_balance:,.0f}")

        st.markdown("---")
        c_left, c_right = st.columns(2)

        with c_left:
            st.markdown("**Projects by Stage**")
            stage_counts = Counter(p["status"] for p in all_projects)
            stage_df = pd.DataFrame(
                [{"Stage": s, "Count": stage_counts.get(s, 0)} for s in STATUSES]
            )
            st.bar_chart(stage_df.set_index("Stage"))

        with c_right:
            st.markdown("**⚠️ Overdue Active Projects**")
            overdue_list = []
            for p in all_projects:
                obj = ClientProject(
                    p["client_name"], p["phone"], p["service_type"],
                    p["project_title"], p["quoted_amount"], p["amount_paid"],
                    p["deadline"], p["status"]
                )
                if obj.is_overdue():
                    overdue_list.append({
                        "Client": p["client_name"],
                        "Project": p["project_title"],
                        "Deadline": p["deadline"],
                        "Balance (KES)": f"{obj.balance_due():,.0f}"
                    })
            if overdue_list:
                st.dataframe(pd.DataFrame(overdue_list), use_container_width=True, hide_index=True)
            else:
                st.success("No overdue projects! Everything is on schedule.")

        st.markdown("---")
        st.markdown("**Export Client Report**")
        export_df = pd.DataFrame(all_projects)
        export_df["balance_due"] = export_df["quoted_amount"] - export_df["amount_paid"]
        csv_data = export_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Download Zinnia Projects Report (CSV)",
            data=csv_data,
            file_name=f"zinnia_projects_{date.today()}.csv",
            mime="text/csv"
        )
