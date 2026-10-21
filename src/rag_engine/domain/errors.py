class EngineError(Exception):
    """Public-safe failure; never expose provider bodies or local paths."""

    def __init__(self, code: str, message: str, status: int = 400):
        super().__init__(message)
        self.code, self.message, self.status = code, message, status
