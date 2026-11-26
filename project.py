from datetime import date, datetime
import re

STATUSES = ["Inquiry", "Quoted", "In Progress", "Completed", "Delivered"]
SERVICE_TYPES = [
    "Interior Design",
    "Graphics & Branding",
    "3D Rendering",
    "Space Consultation",
]

PHONE_PATTERN = re.compile(r"^0[17]\d{8}$")


def _clean_text(value) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _normalize_phone(phone) -> str:
    cleaned = _clean_text(phone)
    return re.sub(r"[\s\-]", "", cleaned)


class ClientProject:
    def __init__(
        self,
        client_name: str,
        phone: str,
        service_type: str,
        project_title: str,
        quoted_amount: float,
        amount_paid: float,
        deadline: str,
        status: str = "Inquiry",
        project_id: int | None = None,
    ):
        self.project_id = project_id
        self.client_name = _clean_text(client_name)
        self.phone = _normalize_phone(phone)
        self.service_type = _clean_text(service_type)
        self.project_title = _clean_text(project_title)

        self._numeric_error = ""
        try:
            q_val = 0.0 if quoted_amount in (None, "") else float(quoted_amount)
            p_val = 0.0 if amount_paid in (None, "") else float(amount_paid)
            if not (q_val == q_val and p_val == p_val):  # NaN check
                raise ValueError("NaN value")
            self.quoted_amount = round(q_val, 2)
            self.amount_paid = round(p_val, 2)
        except (TypeError, ValueError):
            self.quoted_amount = 0.0
            self.amount_paid = 0.0
            self._numeric_error = "Quoted amount and amount paid must be valid numbers."

        if isinstance(deadline, (date, datetime)):
            self.deadline = deadline.strftime("%Y-%m-%d")
        else:
            self.deadline = _clean_text(deadline)

        cleaned_status = _clean_text(status)
        self.status = cleaned_status if cleaned_status else "Inquiry"

    def is_valid(self) -> str:
        """Validate fields and return a friendly error message, or empty string if valid."""
        if self._numeric_error:
            return self._numeric_error
        if not self.client_name:
            return "Client name is required."
        if not PHONE_PATTERN.fullmatch(self.phone):
            return (
                "Invalid Kenyan phone number. Use 10 digits starting with 07 or 01 "
                "(e.g., 0712345678)."
            )
        if not self.project_title:
            return "Project title/description is required."
        if self.service_type not in SERVICE_TYPES:
            return f"Service type must be one of: {', '.join(SERVICE_TYPES)}."
        if self.quoted_amount <= 0:
            return "Quoted amount (KES) must be greater than 0."
        if self.amount_paid < 0:
            return "Amount paid cannot be negative."
        if self.amount_paid > self.quoted_amount:
            return "Amount paid cannot exceed the quoted amount."
        if self.status not in STATUSES:
            return f"Status must be one of: {', '.join(STATUSES)}."
        try:
            datetime.strptime(self.deadline, "%Y-%m-%d")
        except ValueError:
            return "Deadline must be a valid date in YYYY-MM-DD format."
        return ""

    def balance_due(self) -> float:
        """Calculate remaining balance owed by the client."""
        return round(self.quoted_amount - self.amount_paid, 2)

    def is_overdue(self) -> bool:
        """Check if an active project has passed its deadline."""
        if self.status in ("Completed", "Delivered"):
            return False
        try:
            due = datetime.strptime(self.deadline, "%Y-%m-%d").date()
            return due < date.today()
        except ValueError:
            return False

    def move_to(self, new_status: str) -> None:
        """Safely transition the project stage."""
        cleaned = _clean_text(new_status)
        if cleaned not in STATUSES:
            raise ValueError(f"Unknown status: {new_status}")
        self.status = cleaned