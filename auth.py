import hashlib
import re
import secrets

# Password strength regex: at least 8 chars, 1 lowercase, 1 uppercase, 1 digit, 1 special char
STRONG_PASSWORD_PATTERN = re.compile(
    r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9]).{8,}$"
)


# Helper function to validate password strength
def validate_password_strength(password: str) -> str:
    """Return a friendly error message if weak, or empty string if strong."""
    if not password or not STRONG_PASSWORD_PATTERN.fullmatch(password):
        return (
            "Password must be at least 8 characters long and include at least "
            "one uppercase letter, one lowercase letter, one number, and one special character."
        )
    return ""


def hash_password(password: str, salt: str | None = None) -> str:
    """Return 'salt$hash' using PBKDF2-HMAC-SHA256."""
    if not salt:
        salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        100_000,
    )
    return f"{salt}${dk.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Verify a plain password against a stored 'salt$hash' string."""
    if not stored_hash or "$" not in stored_hash:
        return False
    salt, expected_hex = stored_hash.split("$", 1)
    computed = hash_password(password, salt=salt)
    _, computed_hex = computed.split("$", 1)
    return secrets.compare_digest(computed_hex, expected_hex)