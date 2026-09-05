from enum import StrEnum


class UserRole(StrEnum):
    ADMIN = "Admin"
    SUPPORT_AGENT = "Support Agent"
    CUSTOMER = "Customer"


class CustomerStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"
