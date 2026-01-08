"""
JadeUI Python SDK - Desktop Application Framework

A Python SDK for creating desktop applications using JadeView's WebView technology.
Provides a clean, object-oriented API for window management, IPC communication,
and web frontend integration.

Example:
    from jadeui import JadeUIApp, Window

    app = JadeUIApp()

    @app.on_ready
    def on_ready():
        window = Window(
            title="My App",
            width=1024,
            height=768,
            url="https://example.com"
        )
        window.show()

    app.run()

Example with local server:
    from jadeui import JadeUIApp, Window, LocalServer

    app = JadeUIApp()
    server = LocalServer()

    @app.on_ready
    def on_ready():
        url = server.start("./web", "myapp")
        window = Window(title="My App", url=f"{url}/index.html")
        window.show()

    app.run()

Example with IPC:
    from jadeui import JadeUIApp, Window, IPCManager

    app = JadeUIApp()
    ipc = IPCManager()

    @ipc.on("message")
    def handle_message(window_id, message):
        print(f"Received: {message}")
        ipc.send(window_id, "message", f"Echo: {message}")
        return 1

    @app.on_ready
    def on_ready():
        window = Window(title="IPC Demo", url="...")
        window.show()

    app.run()
"""

from .app import JadeUIApp
from .window import Window, Theme, Backdrop
from .ipc import IPCManager
from .server import LocalServer
from .events import EventEmitter, Events
from .router import Router
from .core.types import RGBA, WebViewWindowOptions, WebViewSettings
from .exceptions import (
    JadeUIError,
    DLLLoadError,
    WindowCreationError,
    IPCError,
    ServerError,
    InitializationError,
)
from .downloader import (
    download_dll,
    ensure_dll,
    find_dll,
    get_architecture,
    VERSION as DLL_VERSION,
)
from . import utils

__version__ = "0.1.1"
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
