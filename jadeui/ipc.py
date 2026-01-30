"""
JadeUI IPC Manager

Inter-process communication between Python backend and web frontend.
"""

from __future__ import annotations

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

        # Create ctypes callback (返回 void* - jade_text_create 指针)
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

        This method is safe to call from within IPC handlers.

        Args:
            window_id: Target window ID
            channel: IPC channel name
            message: Message content

        Raises:
            IPCError: If message sending fails
        """
        import ctypes

        # 使用 jade_text_create 创建 DLL 管理的安全指针
        # 这解决了在 IPC 回调中调用 send() 时的内存管理问题
        message_bytes = message.encode("utf-8")
        message_ptr = self.dll_manager.jade_text_create(message_bytes)

        if message_ptr:
            # 将 void* 转换为 c_char_p
            message_char_p = ctypes.cast(message_ptr, ctypes.c_char_p)
            result = self.dll_manager.send_ipc_message(
                window_id, channel.encode("utf-8"), message_char_p
            )
        else:
            # 回退到直接传递
            result = self.dll_manager.send_ipc_message(
                window_id, channel.encode("utf-8"), message_bytes
            )

        if result != 1:
            raise IPCError(f"Failed to send IPC message on channel '{channel}'")

        logger.debug(f"Sent IPC message to window {window_id} on channel '{channel}': {message}")

    def broadcast(self, channel: str, message: str) -> None:
        """Broadcast an IPC message to all windows (not implemented)"""
        logger.warning("broadcast() not implemented - would need window enumeration")

    def _handle_message(self, window_id: int, channel: str, message: bytes):
        """Internal message handler dispatcher

        IPC 回调返回 void* (jade_text_create 创建的指针，或 0 表示无返回)
        """
        try:
            message_str = message.decode("utf-8") if message else ""
            logger.debug(
                f"IPC message received: channel={channel}, window_id={window_id}, message={message_str}"
            )

            if channel in self._handlers:
                handler = self._handlers[channel]
                result = handler(window_id, message_str)
                logger.debug(f"IPC handler for '{channel}' returned: {result}")

                # 如果有返回值，使用 jade_text_create 创建文本
                if result is not None:
                    response = str(result)
                    response_bytes = response.encode("utf-8")

                    # jade_text_create 现在返回 c_void_p，可以直接返回
                    ptr = self.dll_manager.jade_text_create(response_bytes)
                    if ptr:
                        return ptr

                return 0  # 无返回数据

            else:
                logger.warning(f"No handler registered for IPC channel: {channel}")
                return 0

        except Exception as e:
            logger.error(f"Error in IPC handler for channel '{channel}': {e}")
            import traceback

            traceback.print_exc()
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
