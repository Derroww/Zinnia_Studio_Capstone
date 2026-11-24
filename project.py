import re
from datetime import datetime, date

STATUSES = ["Inquiry", "Quoted", "In Progress", "Completed", "Delivered"]
SERVICE_TYPES = ["Interior Design", "Graphics & Branding", "3D Rendering", "Space Consultation"]

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
        project_id: int = None,
    ):
        self.project_id = project_id
        self.client_name = client_name.strip() if client_name else ""
        self.phone = phone.strip() if phone else ""
        self.service_type = service_type
        self.project_title = project_title.strip() if project_title else ""
        self.quoted_amount = float(quoted_amount) if quoted_amount is not None else 0.0
        self.amount_paid = float(amount_paid) if amount_paid is not None else 0.0
        self.deadline = deadline
        self.status = status

    def is_valid(self) -> str:
        """Validate fields and return a friendly error message, or empty string if valid."""
        if not self.client_name:
            return "Client name is required."
        if not re.fullmatch(r"0[17]\d{8}", self.phone):
            return "Invalid Kenyan phone number. Use 10 digits starting with 07 or 01 (e.g., 0712345678)."
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
        """Job Method 1: Calculate remaining balance owed by the client."""
        return round(self.quoted_amount - self.amount_paid, 2)

    def is_overdue(self) -> bool:
        """Job Method 2: Check if an active project has passed its deadline."""
        if self.status in ["Completed", "Delivered"]:
            return False
        try:
            due = datetime.strptime(self.deadline, "%Y-%m-%d").date()
            return due < date.today()
        except ValueError:
            return False

    def move_to(self, new_status: str):
        """Job Method 3: Safely transition the project stage."""
        if new_status not in STATUSES:
            raise ValueError(f"Unknown status: {new_status}")
        self.status = new_status
