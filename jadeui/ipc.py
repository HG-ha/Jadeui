"""
JadeUI IPC Manager

Inter-process communication between Python backend and web frontend.
"""

import logging
from typing import Any, Callable, Dict, Optional

from .core import DLLManager
from .core.types import IpcCallback, IPCHandler
from .exceptions import IPCError

logger = logging.getLogger(__name__)


class IPCManager:
    """Manager for inter-process communication

    Handles IPC channels for communication between Python backend and web frontend.
    Allows registering handlers for different message types and sending messages to windows.

    Example:
        ipc = IPCManager()

        @ipc.on('chat')
        def handle_chat(message):
            print(f"Received: {message}")
            return f"Echo: {message}"

        ipc.send(window_id, 'chat', 'Hello from Python!')
    """

    def __init__(self, dll_manager: Optional[DLLManager] = None):
        """Initialize IPC manager

        Args:
            dll_manager: DLL manager instance (uses global if None)
        """
        self.dll_manager = dll_manager or DLLManager()
        if not self.dll_manager.is_loaded():
            self.dll_manager.load()

        self._handlers: Dict[str, Callable[[int, str], Any]] = {}
        self._callbacks = []  # Prevent garbage collection

    def register_handler(self, channel: str, handler: IPCHandler) -> None:
        """Register an IPC message handler

        Args:
            channel: IPC channel name
            handler: Function to handle messages on this channel

        Raises:
            IPCError: If handler registration fails
        """
        if channel in self._handlers:
            logger.warning(f"Handler for channel '{channel}' already exists, replacing")

        self._handlers[channel] = handler

        # Create ctypes callback
        @IpcCallback
        def ipc_callback(window_id, message):
            return self._handle_message(window_id, channel, message)

        self._callbacks.append(ipc_callback)

        # Register with DLL
        import ctypes

        result = self.dll_manager.register_ipc_handler(
            channel.encode("utf-8"),
            ctypes.cast(ipc_callback, ctypes.c_void_p),  # type: ignore
        )

        if result != 1:
            raise IPCError(f"Failed to register IPC handler for channel '{channel}'")

        logger.info(f"Registered IPC handler for channel: {channel}")

    def send(self, window_id: int, channel: str, message: str) -> None:
        """Send an IPC message to a window

        Args:
            window_id: Target window ID
            channel: IPC channel name
            message: Message content

        Raises:
            IPCError: If message sending fails
        """
        result = self.dll_manager.send_ipc_message(
            window_id, channel.encode("utf-8"), message.encode("utf-8")
        )

        if result != 1:
            raise IPCError(f"Failed to send IPC message on channel '{channel}'")

        logger.debug(f"Sent IPC message to window {window_id} on channel '{channel}': {message}")

    def broadcast(self, channel: str, message: str) -> None:
        """Broadcast an IPC message to all windows (not implemented)"""
        logger.warning("broadcast() not implemented - would need window enumeration")

    def _handle_message(self, window_id: int, channel: str, message: bytes) -> int:
        """Internal message handler dispatcher"""
        try:
            message_str = message.decode("utf-8") if message else ""

            if channel in self._handlers:
                handler = self._handlers[channel]
                result = handler(window_id, message_str)

                # Log the result if it's meaningful
                if result is not None:
                    logger.debug(f"IPC handler for '{channel}' returned: {result}")

                return 1 if result is not None else 0
            else:
                logger.warning(f"No handler registered for IPC channel: {channel}")
                return 0

        except Exception as e:
            logger.error(f"Error in IPC handler for channel '{channel}': {e}")
            return 0

    def on(self, channel: str) -> Callable[[IPCHandler], IPCHandler]:
        """Decorator to register an IPC handler

        Args:
            channel: IPC channel name

        Returns:
            Decorator function

        Example:
            ipc = IPCManager()

            @ipc.on('chat')
            def handle_chat(window_id, message):
                return f"Echo: {message}"
        """

        def decorator(handler: IPCHandler) -> IPCHandler:
            self.register_handler(channel, handler)
            return handler

        return decorator

    def remove_handler(self, channel: str) -> None:
        """Remove an IPC handler

        Args:
            channel: IPC channel name
        """
        if channel in self._handlers:
            del self._handlers[channel]
            logger.info(f"Removed IPC handler for channel: {channel}")
        else:
            logger.warning(f"No handler found for channel: {channel}")

    def list_handlers(self) -> list[str]:
        """List all registered IPC channels

        Returns:
            List of channel names
        """
        return list(self._handlers.keys())
