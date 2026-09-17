"""
HistorySnooze Universal Network Retry Handler.
Provides exponential backoff decorator for network operations.
Compliant with 01_ARCHITECTURE_CONSTRAINED_AI.md and Rule <= 150 lines.
"""

import asyncio
import functools
import inspect
import logging
import time
from typing import Any, Callable, Optional, Tuple, Type, Union

logger = logging.getLogger("hsnooze.retry")


def retry_network_op(
    func: Optional[Callable[..., Any]] = None,
    *,
    max_retries: int = 3,
    backoff_factor: float = 2.0,
    initial_delay: float = 1.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    log_level: int = logging.WARNING,
) -> Callable[..., Any]:
    """
    Universal retry decorator with exponential backoff for network operations.
    Supports both synchronous and asynchronous functions.

    Usage:
        @retry_network_op(max_retries=3, backoff_factor=2.0, exceptions=(NetworkError,))
        def call_api():
            ...

        @retry_network_op
        def simple_call():
            ...
    """
    if isinstance(exceptions, type) and issubclass(exceptions, Exception):
        exceptions = (exceptions,)

    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        if inspect.iscoroutinefunction(fn):

            @functools.wraps(fn)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                last_exc: Optional[Exception] = None
                for attempt in range(1, max_retries + 1):
                    try:
                        return await fn(*args, **kwargs)
                    except exceptions as exc:
                        last_exc = exc
                        if attempt >= max_retries:
                            logger.log(
                                log_level,
                                f"Network op '{fn.__name__}' failed after {max_retries} attempts: {exc}",
                            )
                            raise
                        delay = initial_delay * (backoff_factor ** (attempt - 1))
                        logger.log(
                            log_level,
                            f"Network op '{fn.__name__}' attempt {attempt}/{max_retries} failed: {exc}. "
                            f"Retrying in {delay:.2f}s...",
                        )
                        await asyncio.sleep(delay)
                if last_exc is not None:
                    raise last_exc

            return async_wrapper
        else:

            @functools.wraps(fn)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                last_exc: Optional[Exception] = None
                for attempt in range(1, max_retries + 1):
                    try:
                        return fn(*args, **kwargs)
                    except exceptions as exc:
                        last_exc = exc
                        if attempt >= max_retries:
                            logger.log(
                                log_level,
                                f"Network op '{fn.__name__}' failed after {max_retries} attempts: {exc}",
                            )
                            raise
                        delay = initial_delay * (backoff_factor ** (attempt - 1))
                        logger.log(
                            log_level,
                            f"Network op '{fn.__name__}' attempt {attempt}/{max_retries} failed: {exc}. "
                            f"Retrying in {delay:.2f}s...",
                        )
                        time.sleep(delay)
                if last_exc is not None:
                    raise last_exc

            return sync_wrapper

    if func is not None and callable(func):
        return decorator(func)
    return decorator
