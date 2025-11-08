
class GoogleOAuthValidator:
    def __init__(self) -> None:
        pass

    def validate_and_parse_return_path(self, data: str) -> str:
        if data is None:
            data = "/dashboard"
        else:
            # TO DO parsing and validation
            pass
        return data


google_oauth_validator = GoogleOAuthValidator()