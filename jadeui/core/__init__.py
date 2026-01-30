"""
JadeUI Core Module

Low-level interfaces to the JadeView DLL and type definitions.
"""

from typing import Optional

from .dll import DLLManager
from .lifecycle import LifecycleManager
from .types import (
    RGBA,
    AppReadyCallback,
    FileDropCallback,
    GenericWindowEventCallback,
    IpcCallback,
    PageLoadCallback,
    WebViewSettings,
    WebViewWindowOptions,
    WindowAllClosedCallback,
    WindowEventCallback,
)

# ==================== 安全文本指针辅助函数 ====================
# JadeView 1.0+: 回调函数需要返回通过 jade_text_create 创建的安全指针

# 全局 DLL 引用，用于在回调中创建安全文本指针
_dll_instance: Optional[DLLManager] = None


def _get_dll() -> DLLManager:
    """获取 DLL 实例"""
    global _dll_instance
    if _dll_instance is None:
        _dll_instance = DLLManager()
    return _dll_instance


def create_safe_text(text: str) -> Optional[bytes]:
    """使用 jade_text_create 创建安全的文本指针

    JadeView 1.0+ 回调函数需要返回通过此函数创建的指针。

    Args:
        text: 要返回的文本

    Returns:
        安全的文本指针，或 None 如果失败
    """
    dll = _get_dll()
    if dll.is_loaded() and dll.has_function("jade_text_create"):
        return dll.jade_text_create(text.encode("utf-8"))
    return None


def create_block_response() -> Optional[bytes]:
    """创建阻止操作的响应 ("1")"""
    return create_safe_text("1")


def create_allow_response() -> None:
    """创建允许操作的响应 (NULL)"""
    return None


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
    # 安全文本指针辅助函数
    "create_safe_text",
    "create_block_response",
    "create_allow_response",
]
