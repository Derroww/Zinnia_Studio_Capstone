import os
import sqlite3
from dotenv import load_dotenv
from auth import hash_password
from project import ClientProject

load_dotenv()
DB_NAME = os.getenv("DB_NAME", "zinnia_projects.db")

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def create_tables() -> None:
    """Create users and projects tables if they do not exist."""
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                full_name TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'staff'
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_name TEXT NOT NULL,
                phone TEXT NOT NULL,
                service_type TEXT NOT NULL,
                project_title TEXT NOT NULL,
                quoted_amount REAL NOT NULL,
                amount_paid REAL NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'Inquiry',
                deadline TEXT NOT NULL
            )
            """
        )
        conn.commit()

def ensure_initial_admin() -> None:
    """Create an initial admin user from .env if no admin account exists yet."""
    admin_user = os.getenv("ADMIN_USERNAME", "").strip().lower()
    admin_pass = os.getenv("ADMIN_PASSWORD", "").strip()
    admin_name = os.getenv("ADMIN_FULL_NAME", "Studio Admin").strip()

    if not admin_user or not admin_pass:
        return

    with get_connection() as conn:
        existing_admin = conn.execute(
            "SELECT id FROM users WHERE role = 'admin' LIMIT 1"
        ).fetchone()
        if not existing_admin:
            conn.execute(
                """
                INSERT OR IGNORE INTO users (username, full_name, password_hash, role)
                VALUES (?, ?, ?, 'admin')
                """,
                (admin_user, admin_name, hash_password(admin_pass)),
            )
            conn.commit()

# --- Auth & User Functions ---

def register_user(
    username: str,
    full_name: str,
    password_hash: str,
    role: str = "staff",
) -> tuple[bool, str]:
    clean_user = username.strip().lower()
    clean_name = full_name.strip()
    clean_role = role.strip().lower() if role.strip().lower() in {"admin", "staff"} else "staff"

    if not clean_user or not clean_name:
        return False, "Username and full name are required."
    try:
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO users (username, full_name, password_hash, role)
                VALUES (?, ?, ?, ?)
                """,
                (clean_user, clean_name, password_hash, clean_role),
            )
            conn.commit()
        return True, f"Account created ({clean_role}). You can now log in."
    except sqlite3.IntegrityError:
        return False, "That username is already taken."
    except sqlite3.Error as e:
        return False, f"Database error during registration: {e}"


def get_user_by_username(username: str) -> dict | None:
    clean_user = username.strip().lower()
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id, username, full_name, password_hash, role FROM users WHERE username = ?",
            (clean_user,),
        ).fetchone()
        return dict(row) if row else None

def list_users() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, username, full_name, role FROM users ORDER BY id ASC"
        ).fetchall()
        return [dict(r) for r in rows]

def update_user_role(user_id: int, new_role: str) -> None:
    if new_role not in {"admin", "staff"}:
        raise ValueError("Role must be 'admin' or 'staff'.")
    with get_connection() as conn:
        conn.execute("UPDATE users SET role = ? WHERE id = ?", (new_role, user_id))
        conn.commit()

# --- Project CRUD Functions ---

def add_project(project: ClientProject) -> int:
    validation_error = project.is_valid()
    if validation_error:
        raise ValueError(validation_error)

    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO projects (
                client_name, phone, service_type, project_title,
                quoted_amount, amount_paid, status, deadline
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                project.client_name,
                project.phone,
                project.service_type,
                project.project_title,
                project.quoted_amount,
                project.amount_paid,
                project.status,
                project.deadline,
            ),
        )
        conn.commit()
        return cursor.lastrowid


def fetch_projects(search_term: str = "", status_filter: str = "All") -> list[dict]:
    query = "SELECT * FROM projects WHERE 1=1"
    params: list = []

    if search_term.strip():
        like = f"%{search_term.strip()}%"
        query += " AND (client_name LIKE ? OR project_title LIKE ? OR service_type LIKE ?)"
        params.extend([like, like, like])

    if status_filter != "All":
        query += " AND status = ?"
        params.append(status_filter)

    query += " ORDER BY id DESC"

    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
        results = []
        for r in rows:
            item = dict(r)
            proj_obj = ClientProject(
                client_name=item["client_name"],
                phone=item["phone"],
                service_type=item["service_type"],
                project_title=item["project_title"],
                quoted_amount=item["quoted_amount"],
                amount_paid=item["amount_paid"],
                deadline=item["deadline"],
                status=item["status"],
                project_id=item["id"],
            )
            item["balance_due"] = proj_obj.balance_due()
            item["overdue"] = "Yes" if proj_obj.is_overdue() else "No"
            results.append(item)
        return results

def update_project_stage_and_payment(
    project_id: int,
    new_status: str,
    new_amount_paid: float,
) -> None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM projects WHERE id = ?",
            (project_id,),
        ).fetchone()
        if not row:
            raise ValueError(f"Project #{project_id} not found.")

        proj = ClientProject(
            client_name=row["client_name"],
            phone=row["phone"],
            service_type=row["service_type"],
            project_title=row["project_title"],
            quoted_amount=row["quoted_amount"],
            amount_paid=new_amount_paid,
            deadline=row["deadline"],
            status=row["status"],
            project_id=row["id"],
        )
        proj.move_to(new_status)

        validation_error = proj.is_valid()
        if validation_error:
            raise ValueError(validation_error)

        conn.execute(
            """
            UPDATE projects
            SET status = ?, amount_paid = ?
            WHERE id = ?
            """,
            (proj.status, proj.amount_paid, project_id),
        )
        conn.commit()

def delete_project(project_id: int) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
        conn.commit()




