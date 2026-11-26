from datetime import date
import pandas as pd
import streamlit as st

import database
from auth import hash_password, validate_password_strength, verify_password
from project import ClientProject, SERVICE_TYPES, STATUSES

st.set_page_config(
    page_title="Zinnia Studio — Project & Quote Tracker",
    page_icon="🌸",
    layout="wide",
)

database.create_tables()
database.ensure_initial_admin()

if "user" not in st.session_state:
    st.session_state.user = None

st.title("🌸 Zinnia Studio — Client Project & Quote Tracker")
st.caption("Zinnia Interiors & Graphics — Track client briefs, deposits, deadlines, and project stages in one place.")


def show_auth_screen() -> None:
    st.subheader("Sign In or Register")
    login_tab, register_tab = st.tabs(["🔐 Login", "📝 Register"])

    with login_tab:
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Log In")

        if submitted:
            user = database.get_user_by_username(username)
            if user and verify_password(password, user["password_hash"]):
                st.session_state.user = {
                    "id": user["id"],
                    "username": user["username"],
                    "full_name": user["full_name"],
                    "role": user["role"],
                }
                st.rerun()
            else:
                st.error("Invalid username or password.")

    with register_tab:
        with st.form("register_form"):
            full_name = st.text_input("Full Name")
            new_username = st.text_input("Choose a Username")
            # Label reflects strong password requirement
            new_password = st.text_input(
                "Create Strong Password (8+ chars, upper/lower/digit/symbol)",
                type="password",
            )
            confirm_password = st.text_input("Confirm Password", type="password")
            reg_submitted = st.form_submit_button("Create Account")

        if reg_submitted:
            # Password strength check applied during registration 
            strength_error = validate_password_strength(new_password)
            if strength_error:
                st.warning(strength_error)
            elif new_password != confirm_password:
                st.warning("Passwords do not match.")
            else:
                pw_hash = hash_password(new_password)
                ok, msg = database.register_user(new_username, full_name, pw_hash, role="staff")
                if ok:
                    st.success(msg)
                else:
                    st.error(msg)


if st.session_state.user is None:
    show_auth_screen()
    st.stop()

current_user = st.session_state.user
is_admin = current_user.get("role") == "admin"

with st.sidebar:
    st.markdown(f"### 👤 {current_user['full_name']}")
    st.caption(f"Username: `{current_user['username']}` | Role: **`{current_user['role'].upper()}`**")
    if st.button("🚪 Log Out", use_container_width=True):
        st.session_state.user = None
        st.rerun()

tab_labels = [
    "📋 Projects (Read)",
    "➕ New Project (Create)",
    "✏️ Update Stage & Payment",
    "🗑️ Delete Project",
    "📊 Summary & Export",
]
if is_admin:
    tab_labels.append("🛡️ Admin: Team Roles")

tabs = st.tabs(tab_labels)

# --- TAB 1: READ & FILTER ---
with tabs[0]:
    col1, col2 = st.columns([3, 1])
    with col1:
        search_query = st.text_input(
            "Search by client name, project title, or service",
            placeholder="e.g., Westlands, Logo, Amina...",
        )
    with col2:
        status_choice = st.selectbox("Filter by Status", ["All"] + STATUSES)

    projects = database.fetch_projects(search_query, status_choice)
    if projects:
        df = pd.DataFrame(projects)
        df = df.rename(
            columns={
                "id": "ID",
                "client_name": "Client Name",
                "phone": "Phone",
                "service_type": "Service Type",
                "project_title": "Project Title",
                "quoted_amount": "Quoted (KES)",
                "amount_paid": "Paid (KES)",
                "balance_due": "Balance Due (KES)",
                "status": "Status",
                "deadline": "Deadline",
                "overdue": "Overdue",
            }
        )
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No matching projects found. Add a project in the 'New Project (Create)' tab.")

# --- TAB 2: CREATE ---
with tabs[1]:
    st.subheader("Log a New Client Brief")
    with st.form("create_project_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            client_name = st.text_input("Client Name *")
            phone = st.text_input("Kenyan Phone Number *", placeholder="0712345678")
            service_type = st.selectbox("Service Category *", SERVICE_TYPES)
            status = st.selectbox("Initial Stage *", STATUSES, index=0)
        with c2:
            project_title = st.text_input("Project Title *", placeholder="e.g., Westlands Café Interior & Branding")
            quoted_amount = st.number_input("Quoted Amount (KES) *", min_value=0.0, step=500.0)
            amount_paid = st.number_input("Amount Paid (KES)", min_value=0.0, step=500.0)
            deadline = st.date_input("Target Deadline *", value=date.today())

        create_btn = st.form_submit_button("Save Project")

    if create_btn:
        new_proj = ClientProject(
            client_name=client_name,
            phone=phone,
            service_type=service_type,
            project_title=project_title,
            quoted_amount=quoted_amount,
            amount_paid=amount_paid,
            deadline=deadline.isoformat(),
            status=status,
        )
        validation_msg = new_proj.is_valid()
        if validation_msg:
            st.error(validation_msg)
        else:
            try:
                new_id = database.add_project(new_proj)
                st.success(f"Project #{new_id} ('{new_proj.project_title}') saved successfully!")
            except ValueError as err:
                st.error(str(err))

# --- TAB 3: UPDATE ---
with tabs[2]:
    st.subheader("Update Project Stage & Payment")
    all_projects = database.fetch_projects()
    if not all_projects:
        st.info("No projects available to update.")
    else:
        options = {
            f"#{p['id']} — {p['client_name']} ({p['project_title']})": p
            for p in all_projects
        }
        selected_label = st.selectbox("Select Project", list(options.keys()))
        selected_proj = options[selected_label]

        with st.form("update_project_form"):
            current_idx = STATUSES.index(selected_proj["status"]) if selected_proj["status"] in STATUSES else 0
            updated_status = st.selectbox("Stage", STATUSES, index=current_idx)
            updated_paid = st.number_input(
                f"Amount Paid (KES) — Quoted: {selected_proj['quoted_amount']:,.2f}",
                min_value=0.0,
                max_value=float(selected_proj["quoted_amount"]),
                value=float(selected_proj["amount_paid"]),
                step=500.0,
            )
            update_btn = st.form_submit_button("Update Project")

        if update_btn:
            try:
                database.update_project_stage_and_payment(
                    selected_proj["id"], updated_status, float(updated_paid)
                )
                st.success("Project updated!")
                st.rerun()
            except ValueError as err:
                st.error(str(err))

# --- TAB 4: DELETE (ADMIN ONLY) ---
with tabs[3]:
    st.subheader("Delete a Project Record")
    if not is_admin:
        st.warning("🔒 Admin access required. Only administrators can delete project records.")
    else:
        all_projects = database.fetch_projects()
        if not all_projects:
            st.info("No projects available to delete.")
        else:
            del_options = {
                f"#{p['id']} — {p['client_name']} | {p['project_title']}": p["id"]
                for p in all_projects
            }
            chosen = st.selectbox("Select Project to Delete", list(del_options.keys()))
            confirm_del = st.checkbox("I confirm I want to permanently delete this project.")
            if st.button("Delete Selected Project", type="primary", disabled=not confirm_del):
                database.delete_project(del_options[chosen])
                st.success("Project deleted.")
                st.rerun()

# --- TAB 5: SUMMARY & EXPORT ---
with tabs[4]:
    st.subheader("Studio Financial & Workflow Summary")
    all_projects = database.fetch_projects()
    if not all_projects:
        st.info("No project records yet to summarize.")
    else:
        df_summary = pd.DataFrame(all_projects)
        total_quoted = df_summary["quoted_amount"].sum()
        total_paid = df_summary["amount_paid"].sum()
        total_balance = df_summary["balance_due"].sum()
        overdue_count = (df_summary["overdue"] == "Yes").sum()

        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Total Projects", len(df_summary))
        m2.metric("Quoted (KES)", f"{total_quoted:,.2f}")
        m3.metric("Paid (KES)", f"{total_paid:,.2f}")
        m4.metric("Balance Due (KES)", f"{total_balance:,.2f}")
        m5.metric("Overdue Active", int(overdue_count))

        st.markdown("#### Projects by Stage")
        stage_counts = df_summary["status"].value_counts().reset_index()
        stage_counts.columns = ["Stage", "Count"]
        st.dataframe(stage_counts, use_container_width=True, hide_index=True)

        csv_bytes = df_summary.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Download Projects Report (CSV)",
            data=csv_bytes,
            file_name="zinnia_studio_projects.csv",
            mime="text/csv",
        )

# --- TAB 6: ADMIN USER MANAGEMENT ---
if is_admin:
    with tabs[5]:
        st.subheader("Manage Team Accounts & Roles")
        users = database.list_users()
        st.dataframe(pd.DataFrame(users), use_container_width=True, hide_index=True)

        user_map = {f"{u['full_name']} (@{u['username']}) — [{u['role']}]": u for u in users}
        target_label = st.selectbox("Select User", list(user_map.keys()))
        target_user = user_map[target_label]
        new_role = st.selectbox("Assign Role", ["staff", "admin"], index=0 if target_user["role"] == "staff" else 1)

        if st.button("Save Role Change"):
            if target_user["id"] == current_user["id"] and new_role != "admin":
                st.error("You cannot remove your own admin role while logged in.")
            else:
                database.update_user_role(target_user["id"], new_role)
                st.success(f"Updated {target_user['username']} to '{new_role}'.")
                st.rerun()