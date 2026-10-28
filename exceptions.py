class AppException(Exception):
    status_code = 500
    code = "INTERNAL_ERROR"

    def __init__(self, message=None, details=None, status_code=None, code=None):
        super().__init__(message or "An internal error occurred.")
        self.message = message or "An internal error occurred."
        self.details = details or {}
        if status_code is not None:
            self.status_code = status_code
        if code is not None:
            self.code = code

    def to_dict(self):
        rv = {"success": False, "error": self.message, "code": self.code}
        if self.details:
            rv["details"] = self.details
        return rv


class ValidationError(AppException):
    status_code = 400
    code = "VALIDATION_ERROR"


class AuthenticationError(AppException):
    status_code = 401
    code = "AUTHENTICATION_FAILED"


class AuthorizationError(AppException):
    status_code = 403
    code = "FORBIDDEN"


class NotFoundError(AppException):
    status_code = 404
    code = "NOT_FOUND"


class InvalidStateTransitionError(AppException):
    status_code = 400
    code = "INVALID_STATE_TRANSITION"


class ConflictError(AppException):
    status_code = 409
    code = "CONFLICT"

