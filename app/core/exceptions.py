class ToolTimeout(Exception):
    """Simulated network timeout."""


class ToolMalformedResponse(Exception):
    """Simulated bad tool payload."""


class ToolRetriesExhausted(Exception):
    def __init__(self, cause: Exception):
        super().__init__(str(cause))
        self.cause = cause
