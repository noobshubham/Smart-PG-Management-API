class AuthError(Exception):
    """Base auth-domain error."""


class OwnerAlreadyExistsError(AuthError):
    def __init__(self, phone_number: str) -> None:
        super().__init__(f"Owner with phone {phone_number} already exists")
        self.phone_number = phone_number


class InvalidCredentialsError(AuthError):
    def __init__(self) -> None:
        super().__init__("Invalid phone number or password")
