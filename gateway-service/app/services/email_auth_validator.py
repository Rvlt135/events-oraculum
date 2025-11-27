from urllib.parse import urlparse

from app.services.exceptions import AuthorizationError

from app.config.settings import settings

# TODO properly think and implement it proper storage
WHITELIST = []


class EmailAuthValidator:
    def __init__(self) -> None:
        pass

    def validate_and_parse_return_path(self, data: str) -> str:
        if data is None:
            data = "/dashboard"

        url = urlparse(data)
        if (url.netloc and url.netloc in WHITELIST) or url.path.startswith('/'):
            return data
        
        raise AuthorizationError("invalid return_to")
    
    def validate_password(self, password: str) -> str:
        if len(password) < 8:
            raise AuthorizationError("week_password")

    def validate_invite_code(self, code: str) -> str:
        if code is None:
            raise AuthorizationError("invite_required")
        if len(code) != settings.invite_code_length:
            raise AuthorizationError("invite_invalid")
        allowed_characters = settings.invite_code_alphabet
        if not all(char in allowed_characters for char in code):
            raise AuthorizationError("invite_invalid")

email_auth_validator = EmailAuthValidator()
