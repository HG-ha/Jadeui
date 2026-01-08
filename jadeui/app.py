"""
JadeUI Application

Main application class for JadeUI desktop applications.
"""

import ctypes
import logging
import signal
import sys
import threading
from typing import Optional, Callable, Any

from .core import DLLManager, LifecycleManager
from .events import EventEmitter, GlobalEventManager, Events
from .exceptions import InitializationError
from .core.types import (
    AppReadyCallback,
    WindowAllClosedCallback,
)

logger = logging.getLogger(__name__)


class JadeUIApp(EventEmitter):
    """Main JadeUI application class

    This is the central class for JadeUI applications. It manages the application
    lifecycle, DLL loading, and global event handling.

    Example:
        app = JadeUIApp()

        @app.on('ready')
        def on_ready():
            # Create windows here
            window = Window("My App")
            window.show()

        app.run()

    Events:
        - 'ready': Fired when app is initialized and ready
        - 'error': Fired when an error occurs
        - 'window-all-closed': Fired when all windows are closed
        - 'before-quit': Fired before app quits

    Attributes:
        dll_manager: The DLL manager instance
        lifecycle_manager: The lifecycle manager instance
    """

    _instance: Optional["JadeUIApp"] = None

    def __new__(cls) -> "JadeUIApp":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, "_initialized") and self._initialized:
            return

        super().__init__()
        self._initialized = False
        self.dll_manager = DLLManager()
        self.lifecycle_manager = LifecycleManager()
        self._dev_tools_enabled = False
        self._log_file: Optional[str] = None
        self._data_directory: Optional[str] = None

        # Callback references to prevent garbage collection
        self._callbacks: list = []
        
        # Global event manager
        self._global_events: Optional[GlobalEventManager] = None

    @classmethod
    def get_instance(cls) -> Optional["JadeUIApp"]:
        """Get the singleton instance of the app

        Returns:
            The app instance or None if not created
        """
        return cls._instance

    def initialize(
        self,
        enable_dev_tools: bool = False,
        log_file: Optional[str] = None,
        data_directory: Optional[str] = None,
    ) -> "JadeUIApp":
        """Initialize the JadeUI application

        Args:
            enable_dev_tools: Whether to enable developer tools (F12)
            log_file: Path to log file (None disables file logging)
            data_directory: WebView data directory (None uses default, current directory)

        Returns:
            Self for chaining

        Raises:
            InitializationError: If initialization fails
        """
        if self._initialized:
            return self

        try:
            # Store configuration
            self._dev_tools_enabled = enable_dev_tools
            self._log_file = log_file
            self._data_directory = data_directory

            # Initialize lifecycle manager
            self.lifecycle_manager.initialize()
            self.lifecycle_manager.add_cleanup_callback(self._cleanup)

            # Load DLL
            self.dll_manager.load()

            # Initialize JadeView DLL
            # API: JadeView_init(enable_devtools, log_path, data_directory)
            result = self.dll_manager.JadeView_init(
                1 if enable_dev_tools else 0,
                log_file.encode("utf-8") if log_file else None,
                data_directory.encode("utf-8") if data_directory else None,
            )

            if result == 0:
                raise InitializationError("JadeView DLL initialization failed")

            # Create global event manager
            self._global_events = GlobalEventManager(self.dll_manager)

            # Register global event handlers
            self._register_global_events()

            self._initialized = True
            logger.info("JadeUI application initialized successfully")
            return self

        except Exception as e:
            raise InitializationError(f"Failed to initialize JadeUI: {e}")

    def _register_global_events(self) -> None:
        """Register global event handlers with the DLL"""
        # Create app-ready callback
        @AppReadyCallback
        def app_ready_callback(success: int, reason: ctypes.c_char_p) -> int:
            reason_str = reason.decode("utf-8") if reason else "unknown"
            return self._on_app_ready(success, reason_str)

        # Create window-all-closed callback
        @WindowAllClosedCallback
        def window_all_closed_callback() -> int:
            return self._on_window_all_closed()

        # Store references to prevent garbage collection
        self._callbacks.append(app_ready_callback)
        self._callbacks.append(window_all_closed_callback)

        # Register with DLL
        self.dll_manager.jade_on(
            b"app-ready",
            ctypes.cast(app_ready_callback, ctypes.c_void_p),
        )
        self.dll_manager.jade_on(
            b"window-all-closed",
            ctypes.cast(window_all_closed_callback, ctypes.c_void_p),
        )

        logger.info("Global event handlers registered")

    def _on_app_ready(self, success: int, reason: str) -> int:
        """Handle app-ready event"""
        try:
            if success == 1 and reason == "success":
                logger.info("JadeUI app ready")
                self.emit("ready")
            else:
                logger.error(f"JadeUI app failed to initialize: {reason}")
                self.emit(
                    "error",
                    InitializationError(f"App initialization failed: {reason}"),
                )
        except Exception as e:
            logger.error(f"Error in app-ready handler: {e}")
        return 0

    def _on_window_all_closed(self) -> int:
        """Handle window-all-closed event"""
        logger.info("All windows closed")
        self.emit("window-all-closed")
        # Default behavior: cleanup when all windows are closed
        self._cleanup()
        return 0

    def run(self) -> None:
        """Start the application message loop

        This method blocks until all windows are closed.
        Call this after setting up event handlers and windows.
        
        Supports Ctrl+C to terminate the application.
        """
        if not self._initialized:
            self.initialize()

        # 设置信号处理器
        self._setup_signal_handlers()

        logger.info("Starting JadeUI message loop")
        try:
            self.dll_manager.run_message_loop()
        except KeyboardInterrupt:
            logger.info("Application interrupted by user (Ctrl+C)")
        finally:
            self._cleanup()

    def _setup_signal_handlers(self) -> None:
        """设置信号处理器以支持 Ctrl+C"""
        self._shutting_down = False
        
        def signal_handler(signum, frame):
            if self._shutting_down:
                return
            self._shutting_down = True
            logger.info(f"Received signal {signum}, shutting down...")
            self._force_quit()

        # 注册 SIGINT (Ctrl+C) 和 SIGTERM
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Windows: 设置控制台控制处理器
        if sys.platform == "win32":
            self._setup_windows_console_handler()

    def _setup_windows_console_handler(self) -> None:
        """设置 Windows 控制台控制处理器"""
        try:
            # 使用 ctypes 直接调用 Windows API
            kernel32 = ctypes.windll.kernel32
            
            # BOOL WINAPI HandlerRoutine(DWORD dwCtrlType)
            HANDLER_ROUTINE = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_ulong)
            
            CTRL_C_EVENT = 0
            CTRL_BREAK_EVENT = 1
            CTRL_CLOSE_EVENT = 2
            
            @HANDLER_ROUTINE
            def console_handler(ctrl_type):
                if ctrl_type in (CTRL_C_EVENT, CTRL_BREAK_EVENT, CTRL_CLOSE_EVENT):
                    if not self._shutting_down:
                        self._shutting_down = True
                        logger.info("Console control event received, shutting down...")
                        # 在新线程中执行清理，避免阻塞
                        threading.Thread(target=self._force_quit, daemon=True).start()
                    return True
                return False
            
            # 保存引用防止垃圾回收
            self._console_handler = console_handler
            kernel32.SetConsoleCtrlHandler(console_handler, True)
            logger.debug("Windows console handler registered")
        except Exception as e:
            logger.warning(f"Could not set Windows console handler: {e}")

    def _force_quit(self) -> None:
        """强制退出应用"""
        try:
            # 清理窗口
            self.dll_manager.cleanup_all_windows()
            
            # Windows: 发送退出消息到消息循环
            if sys.platform == "win32":
                try:
                    user32 = ctypes.windll.user32
                    # PostQuitMessage 会导致 GetMessage 返回 0，从而退出消息循环
                    user32.PostQuitMessage(0)
                except Exception as e:
                    logger.warning(f"PostQuitMessage failed: {e}")
                    
        except Exception as e:
            logger.error(f"Error during force quit: {e}")
        finally:
            # 确保进程退出
            import os
            os._exit(0)

    def quit(self) -> None:
        """Quit the application

        Cleans up all resources and exits the message loop.
        """
        logger.info("Quitting JadeUI application")
        self.emit("before-quit")
        self._cleanup()

    def _cleanup(self) -> None:
        """Clean up application resources"""
        if not self._initialized:
            return
            
        try:
            self.dll_manager.cleanup_all_windows()
            logger.info("Application resources cleaned up")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

    def is_ready(self) -> bool:
        """Check if the application is initialized and ready

        Returns:
            True if app is ready
        """
        return self._initialized

    @property
    def dev_tools_enabled(self) -> bool:
        """Check if developer tools are enabled"""
        return self._dev_tools_enabled

    def on_ready(self, callback: Callable[[], Any]) -> Callable[[], Any]:
        """Decorator for ready event

        Args:
            callback: Function to call when app is ready

        Returns:
            The callback function

        Example:
            @app.on_ready
            def setup():
                window = Window("My App")
                window.show()
        """
        self.on("ready", callback)
        return callback

    def on_window_all_closed(
        self, callback: Callable[[], Any]
    ) -> Callable[[], Any]:
        """Decorator for window-all-closed event

        Args:
            callback: Function to call when all windows are closed

        Returns:
            The callback function
        """
        self.on("window-all-closed", callback)
        return callback

    def __enter__(self) -> "JadeUIApp":
        """Context manager entry"""
        if not self._initialized:
            self.initialize()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit"""
        self._cleanup()

    def __repr__(self) -> str:
        status = "ready" if self._initialized else "not initialized"
        return f"JadeUIApp(status={status}, dev_tools={self._dev_tools_enabled})"
