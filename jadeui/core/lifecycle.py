"""
JadeUI Lifecycle Manager

Handles application initialization, cleanup, and signal handling.
"""

from __future__ import annotations

import atexit
import logging
import signal
from typing import Callable

logger = logging.getLogger(__name__)


class LifecycleManager:
    """Manages application lifecycle events and cleanup"""

    def __init__(self):
        self._initialized = False
        self._cleanup_callbacks: list[Callable[[], None]] = []
        self._signal_handlers_registered = False

    def initialize(self) -> None:
        """Initialize the lifecycle manager"""
        if self._initialized:
            return

        # Register cleanup on exit
        atexit.register(self._cleanup)

        # Register signal handlers for graceful shutdown
        self._register_signal_handlers()

        self._initialized = True
        logger.info("Lifecycle manager initialized")

    def _register_signal_handlers(self) -> None:
        """Register signal handlers for graceful shutdown"""
        if self._signal_handlers_registered:
            return

        try:
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)
            self._signal_handlers_registered = True
            logger.info("Signal handlers registered")
        except (OSError, ValueError) as e:
            logger.warning(f"Could not register signal handlers: {e}")

    def _signal_handler(self, signum: int, frame) -> None:
        """Handle termination signals"""
        logger.info(f"Received signal {signum}, initiating cleanup")
        self._cleanup()
        exit(0)

    def add_cleanup_callback(self, callback: Callable[[], None]) -> None:
        """Add a callback to be executed during cleanup"""
        self._cleanup_callbacks.append(callback)

    def _cleanup(self) -> None:
        """Execute cleanup callbacks"""
        logger.info("Executing cleanup callbacks")
        for callback in reversed(self._cleanup_callbacks):
            try:
                callback()
            except Exception as e:
                logger.error(f"Error in cleanup callback: {e}")

    def __enter__(self):
        """Context manager entry"""
        self.initialize()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self._cleanup()
