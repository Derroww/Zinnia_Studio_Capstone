import sqlite3
from project import ClientProject

DB_NAME = "zinnia_projects.db"

def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def create_table():
    try:
        with get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS projects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    client_name TEXT NOT NULL,
                    phone TEXT NOT NULL,
                    service_type TEXT NOT NULL,
                    project_title TEXT NOT NULL,
                    quoted_amount REAL NOT NULL,
                    amount_paid REAL NOT NULL,
                    deadline TEXT NOT NULL,
                    status TEXT NOT NULL
                )
            """)
            conn.commit()
    except sqlite3.Error as e:
        raise RuntimeError(f"Database initialization error: {e}")

def add_project(proj: ClientProject):
    try:
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO projects (client_name, phone, service_type, project_title, quoted_amount, amount_paid, deadline, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    proj.client_name,
                    proj.phone,
                    proj.service_type,
                    proj.project_title,
                    proj.quoted_amount,
                    proj.amount_paid,
                    proj.deadline,
                    proj.status,
                ),
            )
            conn.commit()
    except sqlite3.Error as e:
        raise RuntimeError(f"Failed to save project: {e}")

def get_projects(search_term: str = "", status_filter: str = "All"):
    try:
        with get_connection() as conn:
            query = "SELECT * FROM projects WHERE 1=1"
            params = []
            if search_term.strip():
                query += " AND (client_name LIKE ? OR project_title LIKE ? OR service_type LIKE ?)"
                like_val = f"%{search_term.strip()}%"
                params.extend([like_val, like_val, like_val])
            if status_filter != "All":
                query += " AND status = ?"
                params.append(status_filter)
            query += " ORDER BY deadline ASC"
            cursor = conn.execute(query, tuple(params))
            return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        raise RuntimeError(f"Failed to fetch projects: {e}")

def update_project(project_id: int, status: str, amount_paid: float, deadline: str):
    try:
        with get_connection() as conn:
            conn.execute(
                """
                UPDATE projects
                SET status = ?, amount_paid = ?, deadline = ?
                WHERE id = ?
                """,
                (status, float(amount_paid), deadline, project_id),
            )
            conn.commit()
    except sqlite3.Error as e:
        raise RuntimeError(f"Failed to update project: {e}")

def delete_project(project_id: int):
    try:
        with get_connection() as conn:
            conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
            conn.commit()
    except sqlite3.Error as e:
        raise RuntimeError(f"Failed to delete project: {e}")

def seed_sample_data():
    """Populate initial demo data if database is empty."""
    existing = get_projects()
    if not existing:
        samples = [
            ClientProject("Amina Wanjiku", "0712345678", "Interior Design", "Westlands 3BR Apartment Makeover", 250000, 150000, "2026-11-15", "In Progress"),
            ClientProject("Kileleshwa Bistro", "0722987654", "Graphics & Branding", "Full Menu, Logo & Signage Rebrand", 85000, 85000, "2026-11-28", "Quoted"),
            ClientProject("David Ochieng", "0110456789", "3D Rendering", "Karen Villa Living Room 3D Concept", 60000, 20000, "2026-12-05", "Inquiry"),
            ClientProject("Savannah Spa", "0733112233", "Space Consultation", "Reception & Treatment Room Layout", 45000, 45000, "2026-11-10", "Delivered"),
        ]
        for s in samples:
            add_project(s)
