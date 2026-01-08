"""
JadeUI Core Module

Low-level interfaces to the JadeView DLL and type definitions.
"""

from .dll import DLLManager
from .types import (
    RGBA,
    WebViewWindowOptions,
    WebViewSettings,
    WindowEventCallback,
    PageLoadCallback,
    FileDropCallback,
    AppReadyCallback,
    IpcCallback,
    WindowAllClosedCallback,
)
from .lifecycle import LifecycleManager

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
]
