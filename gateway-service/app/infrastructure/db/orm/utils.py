import random
import string

from app.config.settings import settings


def generate_referral_code(length: int = settings.ref_code_length) -> str:
    """Generates a random alphanumeric referral code."""
    characters = string.ascii_uppercase + string.digits
    return ''.join(random.choice(characters) for _ in range(length))
