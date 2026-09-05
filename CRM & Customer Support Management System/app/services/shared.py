VALID_TRANSITIONS: dict[str, set[str]] = {
    "open": {"in_progress", "resolved", "cancelled"},
    "in_progress": {"waiting_for_customer", "resolved", "cancelled"},
    "waiting_for_customer": {"in_progress", "cancelled"},
    "resolved": {"closed", "open"},
    "closed": set(),
    "cancelled": set(),
}
TERMINAL_STATUSES = {"closed", "cancelled"}
ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".doc", ".docx", ".txt"}
ALLOWED_MIME_TYPES: dict[str, set[str]] = {
    ".pdf": {"application/pdf"},
    ".jpg": {"image/jpeg"},
    ".jpeg": {"image/jpeg"},
    ".png": {"image/png"},
    ".doc": {"application/msword"},
    ".docx": {"application/vnd.openxmlformats-officedocument.wordprocessingml.document"},
    ".txt": {"text/plain"},
}


