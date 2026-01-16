"""
JadeUI Python SDK - Desktop Application Framework

A Python SDK for creating desktop applications using JadeView's WebView technology.
Provides a clean, object-oriented API for window management, IPC communication,
and web frontend integration.

Quick Start (simplest):
    from jadeui import Window

    Window(title="My App", url="https://example.com").run()

Local App (auto-detect web folder):
    from jadeui import Window

    Window(title="My App").run()  # Loads web/index.html

Full Mode (multi-window, events):
    from jadeui import JadeUIApp, Window

    app = JadeUIApp()

    @app.on_ready
    def on_ready():
        Window(title="Window 1", url="https://example.com").show()
        Window(title="Window 2", url="https://google.com").show()

    app.run()

With IPC:
    from jadeui import IPCManager, Window

    ipc = IPCManager()

    @ipc.on("message")
    def handle_message(window_id, message):
        print(f"Received: {message}")
        ipc.send(window_id, "message", f"Echo: {message}")
        return 1

    Window(title="IPC Demo").run(web_dir="web")
"""

from . import utils
from .app import JadeUIApp
from .core.types import RGBA, WebViewSettings, WebViewWindowOptions
from .downloader import (
    VERSION as DLL_VERSION,
)
from .downloader import (
    download_dll,
    ensure_dll,
    find_dll,
    get_architecture,
)
from .events import EventEmitter, Events
from .exceptions import (
    DLLLoadError,
    InitializationError,
    IPCError,
    JadeUIError,
    ServerError,
    WindowCreationError,
)
from .ipc import IPCManager
from .router import Router
from .server import LocalServer
from .window import Backdrop, Theme, Window

__version__ = "0.3.3"
__author__ = "JadeView Team"
__license__ = "MIT"

__all__ = [
    # Main classes
    "JadeUIApp",
    "Window",
    "IPCManager",
    "LocalServer",
    "Router",
    # Constants
    "Theme",
    "Backdrop",
    "Events",
    # Types
    "RGBA",
    "WebViewWindowOptions",
    "WebViewSettings",
    # Events
    "EventEmitter",
    # Exceptions
    "JadeUIError",
    "DLLLoadError",
    "WindowCreationError",
    "IPCError",
    "ServerError",
    "InitializationError",
    # DLL Downloader
    "download_dll",
    "ensure_dll",
    "find_dll",
    "get_architecture",
    "DLL_VERSION",
    # Utilities
    "utils",
]


def create_app(
    enable_dev_tools: bool = False,
    user_data_dir: str = None,
    log_file: str = None,
) -> JadeUIApp:
    """Create and initialize a JadeUI application

    Convenience function for quick app creation.

    Args:
        enable_dev_tools: Whether to enable developer tools
        user_data_dir: Directory for user data storage
        log_file: Path to log file

    Returns:
        Initialized JadeUIApp instance

    Example:
        from jadeui import create_app, Window

        app = create_app()

        @app.on_ready
        def setup():
            Window(title="My App", url="https://example.com").show()

        app.run()
    """
    app = JadeUIApp()
    app.initialize(
        enable_dev_tools=enable_dev_tools,
        user_data_dir=user_data_dir,
        log_file=log_file,
    )
    return app
