from datetime import datetime
from enum import Enum
from uuid import UUID


class PlanType(str, Enum):
    FREE = "free"
    PRO = "pro"
    PARTNER = "partner"


class IdentityProvider(str, Enum):
    GOOGLE = "google"
    PASSWORD = "password"
    TELEGRAM = "telegram"

