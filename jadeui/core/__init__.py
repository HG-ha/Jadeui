"""
JadeUI Core Module

Low-level interfaces to the JadeView DLL and type definitions.
"""

from .dll import DLLManager
from .lifecycle import LifecycleManager
from .types import (
    RGBA,
    AppReadyCallback,
    FileDropCallback,
    IpcCallback,
    PageLoadCallback,
    WebViewSettings,
    WebViewWindowOptions,
    WindowAllClosedCallback,
    WindowEventCallback,
    GenericWindowEventCallback,
)

__all__ = [
    "DLLManager",
    "RGBA",
    "WebViewWindowOptions",
    "WebViewSettings",
    "LifecycleManager",
    "WindowEventCallback",
    "PageLoadCallback",
    "FileDropCallback",
    "AppReadyCallback",
    "IpcCallback",
    "WindowAllClosedCallback",
    "GenericWindowEventCallback",
]
