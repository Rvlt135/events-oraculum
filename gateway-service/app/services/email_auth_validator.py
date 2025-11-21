from urllib.parse import urlparse

from app.services.exceptions import ValidationError

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
        
        raise ValidationError(
            name="invalid return_to",
            message="return_to is not allowed",
        )


email_auth_validator = EmailAuthValidator()