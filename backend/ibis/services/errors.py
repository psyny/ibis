"""Service-level errors. The API maps them to HTTP status codes (see main.py)."""


class DomainError(Exception):
    status_code = 400

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class AuthenticationError(DomainError):
    status_code = 401


class NotFoundError(DomainError):
    status_code = 404


class PermissionDeniedError(DomainError):
    status_code = 403


class ConflictError(DomainError):
    status_code = 409


class ValidationError(DomainError):
    status_code = 422
