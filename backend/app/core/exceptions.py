class DristikException(Exception):
    """Base exception for all Dristik 2.0 system errors."""
    def __init__(self, message: str, status_code: int = 500):
        super().__init__(message)
        self.message = message
        self.status_code = status_code

class EntityNotFoundException(DristikException):
    def __init__(self, entity: str, identifier: str):
        super().__init__(f"{entity} '{identifier}' not found.", status_code=404)

class CrawlerException(DristikException):
    def __init__(self, message: str):
        super().__init__(message, status_code=502)

class AuthenticationException(DristikException):
    def __init__(self, message: str = "Invalid credentials"):
        super().__init__(message, status_code=401)
