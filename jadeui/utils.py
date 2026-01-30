"""
JadeUI Utilities

Helper functions and utilities for JadeUI.
"""

import os
import sys
from pathlib import Path
from typing import Optional


def get_resource_path(relative_path: str) -> str:
    """Get the absolute path to a resource file

    Compatible with development environment and packaged applications.

    Args:
        relative_path: Relative path to the resource

    Returns:
        Absolute path to the resource
    """
    try:
        # PyInstaller/Nuitka packaged environment
        base_path = sys._MEIPASS  # type: ignore
    except AttributeError:
        # Development environment
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    return os.path.join(base_path, relative_path)


def show_error(title: str, message: str) -> None:
    """Display an error message to the user

    Shows error in console and attempts to show Windows message box.

    Args:
        title: Error title
        message: Error message
    """
    # Log to file
    try:
        log_dir = os.path.expanduser("~")
        log_file = os.path.join(log_dir, "JadeUI_error.log")
        with open(log_file, "a", encoding="utf-8") as f:
            import datetime

            f.write(f"\n[{datetime.datetime.now()}] {title}\n{message}\n")
    except Exception:
        pass

    # Try Windows message box
    try:
        import ctypes

        ctypes.windll.user32.MessageBoxW(0, message, title, 0x10)  # MB_ICONERROR
    except Exception:
        print(f"{title}: {message}")


def ensure_directory(path: str) -> None:
    """Ensure a directory exists, creating it if necessary

    Args:
        path: Directory path
    """
    Path(path).mkdir(parents=True, exist_ok=True)


# ==================== 内存管理工具 (v1.0+) ====================


def jade_text_create(text: str) -> Optional[bytes]:
    """创建安全文本指针

    JadeView 1.0+ 支持 IPC 回调直接返回文本响应。
    此函数使用 DLL 的 jade_text_create 函数创建安全的文本指针，
    适用于需要向前端发送复杂文本响应的场景。

    注意：对于普通事件处理（阻止/允许），直接返回 True/False 或 1/0 即可，
    SDK 会自动处理。此函数主要用于高级 IPC 文本响应场景。

    Args:
        text: 要转换的文本

    Returns:
        安全的文本指针 (bytes)，或 None 如果 DLL 未加载

    Example:
        # 用于需要直接返回文本的 IPC 场景
        result_ptr = jade_text_create("响应数据")
    """
    try:
        from .core import DLLManager

        dll = DLLManager()
        if dll.is_loaded() and dll.has_function("jade_text_create"):
            return dll.jade_text_create(text.encode("utf-8"))
    except Exception:
        pass
    # 降级处理：直接返回 bytes
    return text.encode("utf-8")


def jade_text_free(ptr: bytes) -> None:
    """释放由 jade_text_create 创建的文本指针

    注意：通常不需要手动调用此函数，DLL 会自动管理内存。
    只有在特殊情况下需要手动释放内存时才使用。

    Args:
        ptr: jade_text_create 返回的指针
    """
    try:
        from .core import DLLManager

        dll = DLLManager()
        if dll.is_loaded() and dll.has_function("jade_text_free"):
            dll.jade_text_free(ptr)
    except Exception:
        pass


# ==================== 缓存清理工具 ====================


def clean_cache() -> None:
    """清理 jadeui 包的 __pycache__ 缓存

    当遇到奇怪的崩溃问题时，可以运行此命令清理缓存：
        jadeui-clean

    或在 Python 中调用：
        from jadeui.utils import clean_cache
        clean_cache()
    """
    import shutil

    # 获取 jadeui 包的路径
    package_dir = Path(__file__).parent

    # 清理 jadeui 目录下的所有 __pycache__
    count = 0
    for cache_dir in package_dir.rglob("__pycache__"):
        if cache_dir.is_dir():
            try:
                shutil.rmtree(cache_dir)
                count += 1
                print(f"已清理: {cache_dir}")
            except Exception as e:
                print(f"清理失败: {cache_dir} - {e}")

    if count > 0:
        print(f"\n✅ 共清理 {count} 个缓存目录")
    else:
        print("没有找到需要清理的缓存")
