from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError


class PasswordService:
    def __init__(self):
        self.hasher = PasswordHasher()

    def hash_password(self, password: str) -> str:
        return self.hasher.hash(password)

    def verify_password(self, password: str, password_hash: str) -> bool:
        try:
            self.hasher.verify(password_hash, password)
            if self.hasher.check_needs_rehash(password_hash):
                return True
            return True
        except VerifyMismatchError:
            return False

password_service = PasswordService()
