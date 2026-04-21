class HTTPStatusException(Exception):
    """Custom exception for HTTP status errors."""

    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(self._generate_message())

    def _generate_message(self) -> str:
        """Generates a detailed error message."""
        return f"HTTP {self.status_code}: {self.detail}"

    def __str__(self) -> str:
        """Returns a string representation of the exception."""
        return self._generate_message()