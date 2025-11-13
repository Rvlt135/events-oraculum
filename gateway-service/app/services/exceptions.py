class AuthorizationError(Exception):
    pass


class ValidationError(Exception):
    def __init__(self, name: str, message: str):
        self.name = name
        self.message = message
