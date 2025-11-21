import random
import string


def generate_referral_code(length: int = 8) -> str:
    """Generates a random alphanumeric referral code."""
    characters = string.ascii_uppercase + string.digits
    return ''.join(random.choice(characters) for i in range(length))
