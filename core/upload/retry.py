"""
VĀSTU Upload Pipeline - Exponential Backoff & Retry Logic
Provides exponential backoff with full jitter to handle transient network drops.
"""

import time
import random
import logging
from typing import Callable, TypeVar, Any, Optional

logger = logging.getLogger("vastu.upload.retry")

T = TypeVar("T")

def calculate_backoff_delay(
    attempt: int,
    base_delay: float = 0.5,
    max_delay: float = 30.0,
    jitter: bool = True
) -> float:
    """
    Computes exponential backoff delay for a given attempt index (0-indexed).
    Uses full jitter by default to prevent thundering herd.
    """
    delay = min(max_delay, base_delay * (2 ** attempt))
    if jitter:
        # Full jitter: uniform random in [0.5 * delay, delay] to ensure some progressive backoff
        return random.uniform(0.5 * delay, delay)
    return delay

def retry_with_backoff(
    func: Callable[[], T],
    max_retries: int = 5,
    base_delay: float = 0.5,
    max_delay: float = 30.0,
    retryable_exceptions: tuple = (Exception,),
    on_retry: Optional[Callable[[int, Exception, float], None]] = None
) -> T:
    """
    Executes func with exponential backoff retries.
    """
    attempt = 0
    while True:
        try:
            return func()
        except retryable_exceptions as e:
            if attempt >= max_retries:
                logger.error(f"Exhausted {max_retries} retries for operation. Error: {e}")
                raise e
            delay = calculate_backoff_delay(attempt, base_delay, max_delay)
            if on_retry:
                on_retry(attempt, e, delay)
            else:
                logger.warning(f"Operation failed (attempt {attempt + 1}/{max_retries + 1}): {e}. Retrying in {delay:.2f}s")
            time.sleep(delay)
            attempt += 1
