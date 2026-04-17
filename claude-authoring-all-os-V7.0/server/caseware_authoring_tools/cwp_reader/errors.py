"""Error handling for CWP Template Reader MCP Server."""

from __future__ import annotations

import logging
from collections.abc import Callable
from functools import wraps
from typing import ParamSpec, TypeVar

logger = logging.getLogger(__name__)

P = ParamSpec("P")
R = TypeVar("R")


class TemplateReaderError(Exception):
    """Base exception for template reader errors."""

    def __init__(self, message: str, operation: str | None = None) -> None:
        super().__init__(message)
        self.operation = operation


def with_error_handling(func: Callable[P, R]) -> Callable[P, R]:
    """Decorator providing consistent error handling and logging.

    Catches unexpected exceptions and wraps them in TemplateReaderError
    with the function name attached for diagnostics.
    """

    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        try:
            return func(*args, **kwargs)
        except TemplateReaderError:
            raise
        except (FileNotFoundError, ValueError, ImportError):
            # Re-raise known errors without wrapping
            raise
        except Exception as e:
            raise TemplateReaderError(
                f"Unexpected error in {func.__name__}: {e}",
                operation=func.__name__,
            ) from e

    return wrapper
