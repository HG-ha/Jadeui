"""
JadeUI Utilities

Helper functions and utilities for JadeUI.
"""

import os
import sys
from typing import Optional
from pathlib import Path


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
    except:
        pass

    # Try Windows message box
    try:
        import ctypes

        ctypes.windll.user32.MessageBoxW(0, message, title, 0x10)  # MB_ICONERROR
    except:
        print(f"{title}: {message}")


def ensure_directory(path: str) -> None:
    """Ensure a directory exists, creating it if necessary

    Args:
        path: Directory path
    """
    Path(path).mkdir(parents=True, exist_ok=True)
