"""
Core exceptions used across the backend.

These are intentionally minimal. Higher-level services may raise more specific
exceptions, but this centralizes the named exceptions previously referenced
through the legacy `app.core.exceptions` package.
"""
from typing import Optional


class LLMError(Exception):
    """Raised when there is an LLM-related issue."""
    def __init__(self, message: str = "LLM call failed") -> None:
        super().__init__(message)
        self.message = message


class RenderError(Exception):
    """Raised when a rendering backend (Graphviz/PlantUML) fails.

    The `detail` attribute can carry a nested exception message.
    """
    def __init__(self, message: str, detail: Optional[str] = None) -> None:
        super().__init__(message)
        self.detail = detail


class ValidationError(Exception):
    """Raised for validation failures (syntax, formats, etc.)"""
    pass


class DiagramGenerationError(Exception):
    """Raised when diagram generation fails end-to-end."""
    def __init__(self, message: str, detail: Optional[str] = None) -> None:
        super().__init__(message)
        self.detail = detail


__all__ = ["LLMError", "RenderError", "ValidationError", "DiagramGenerationError"]
