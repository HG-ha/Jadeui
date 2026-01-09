"""
JadeUI DLL Manager

Handles loading and function binding for the JadeView DLL.
"""

import ctypes
import logging
import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any, List, Optional

from ..exceptions import DLLLoadError
from .types import (
    WebViewSettings,
    WebViewWindowOptions,
)

if TYPE_CHECKING:
    from ctypes import CDLL

logger = logging.getLogger(__name__)

class DLLManager:
    """Manager for JadeView DLL loading and function binding

    Handles automatic discovery, loading, and function binding for the
    JadeView DLL. Functions that don't exist in the DLL are gracefully
    handled with stub implementations.
    """

    # Singleton instance
    _instance: Optional["DLLManager"] = None

    def __new__(cls, dll_path: Optional[str] = None) -> "DLLManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_instance(dll_path)
        return cls._instance

    def _init_instance(self, dll_path: Optional[str] = None) -> None:
        """Initialize instance attributes"""
        self.dll_path = dll_path or self._find_dll()
        self.dll: Optional["CDLL"] = None
        self._loaded = False
        self._available_functions: set[str] = set()
        self._unavailable_functions: set[str] = set()

    def __init__(self, dll_path: Optional[str] = None):
        # __init__ is called after __new__, but we already initialized in _init_instance
        pass

    def _find_dll(self) -> str:
        """Find the JadeView DLL in common locations

        If DLL is not found, attempts to download it automatically.
        """
        from ..downloader import ensure_dll, find_dll, get_architecture

        # Try to find existing DLL
        dll_path = find_dll()
        if dll_path:
            return str(dll_path)

        # Try legacy paths for backward compatibility
        arch = get_architecture()
        dist_dir = f"JadeView-dist_{arch}"
        dll_name = "JadeView_x64.dll" if arch == "x64" else "JadeView.dll"

        legacy_paths = [
            # Package root (old structure)
            Path(__file__).parent.parent.parent / "JadeView-dist_x64" / "JadeView_x64.dll",
            Path(__file__).parent.parent.parent / dist_dir / dll_name,
            # Current working directory
            Path.cwd() / "JadeView-dist_x64" / "JadeView_x64.dll",
            Path.cwd() / dist_dir / dll_name,
        ]

        # Try PyInstaller/Nuitka paths
        try:
            base_path = sys._MEIPASS  # type: ignore
            legacy_paths.append(Path(base_path) / dist_dir / dll_name)
        except AttributeError:
            pass

        for path in legacy_paths:
            if path.exists():
                return str(path)

        # DLL not found - attempt to download
        try:
            dll_path = ensure_dll()
            return str(dll_path)
        except Exception as e:
            logger.error(f"Failed to ensure DLL: {e}")
            # Return default path (will fail later with better error message)
            return str(Path(__file__).parent.parent / "dll" / dist_dir / dll_name)

    def load(self) -> None:
        """Load the DLL and bind functions"""
        if self._loaded:
            return

        if not os.path.exists(self.dll_path):
            raise DLLLoadError(f"DLL not found at: {self.dll_path}")

        try:
            self.dll = ctypes.CDLL(self.dll_path)
            self._bind_functions()
            self._loaded = True
            logger.info(f"DLL loaded from: {self.dll_path}")
            if self._unavailable_functions:
                logger.debug(
                    f"Unavailable functions: {', '.join(sorted(self._unavailable_functions))}"
                )
        except DLLLoadError:
            raise
        except Exception as e:
            raise DLLLoadError(f"Failed to load DLL: {e}")

    def _try_bind(
        self,
        name: str,
        argtypes: List[Any],
        restype: Any,
        required: bool = False,
    ) -> bool:
        """Try to bind a function from the DLL

        Args:
            name: Function name
            argtypes: Argument types
            restype: Return type
            required: If True, raise error if function not found

        Returns:
            True if function was bound successfully
        """
        assert self.dll is not None

        try:
            func = getattr(self.dll, name)
            func.argtypes = argtypes
            func.restype = restype
            self._available_functions.add(name)
            return True
        except AttributeError:
            if required:
                raise DLLLoadError(f"Required function '{name}' not found in DLL")
            self._unavailable_functions.add(name)
            return False

    def _bind_functions(self) -> None:
        """Bind all DLL functions with proper signatures"""
        dll = self.dll
        assert dll is not None, "DLL must be loaded before binding functions"

        # ==================== Required Functions ====================
        # These must exist for the SDK to work

        # Initialization
        self._try_bind(
            "JadeView_init",
            [ctypes.c_int, ctypes.c_char_p, ctypes.c_char_p],
            ctypes.c_int,
            required=True,
        )

        # Event handling
        self._try_bind(
            "jade_on",
            [ctypes.c_char_p, ctypes.c_void_p],
            None,
            required=True,
        )

        # Message loop
        self._try_bind("run_message_loop", [], None, required=True)

        # Cleanup
        self._try_bind("cleanup_all_windows", [], None, required=True)

        # Window management
        self._try_bind(
            "create_webview_window",
            [
                ctypes.c_char_p,
                ctypes.c_uint32,
                ctypes.POINTER(WebViewWindowOptions),
                ctypes.POINTER(WebViewSettings),
            ],
            ctypes.c_uint32,
            required=True,
        )

        self._try_bind(
            "set_window_event_handlers",
            [ctypes.c_uint32, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p],
            ctypes.c_int,
            required=True,
        )

        self._try_bind("close_window", [ctypes.c_uint32], ctypes.c_int, required=True)

        # ==================== Optional Functions ====================
        # These are optional and the SDK will work without them

        self._try_bind("get_window_count", [], ctypes.c_uint32)

        # Window operations
        self._try_bind("minimize_window", [ctypes.c_uint32], ctypes.c_int)
        self._try_bind("toggle_maximize_window", [ctypes.c_uint32], ctypes.c_int)
        self._try_bind("set_window_theme", [ctypes.c_uint32, ctypes.c_char_p], ctypes.c_int)
        self._try_bind("set_window_backdrop", [ctypes.c_uint32, ctypes.c_char_p], ctypes.c_int)

        # Local server
        self._try_bind(
            "create_local_server",
            [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_size_t],
            ctypes.c_int,
        )

        # IPC
        self._try_bind(
            "register_ipc_handler",
            [ctypes.c_char_p, ctypes.c_void_p],
            ctypes.c_int,
        )
        self._try_bind(
            "send_ipc_message",
            [ctypes.c_uint32, ctypes.c_char_p, ctypes.c_char_p],
            ctypes.c_int,
        )

        # Additional window properties
        self._try_bind(
            "set_window_title",
            [ctypes.c_uint32, ctypes.c_char_p],
            ctypes.c_int,
        )
        self._try_bind(
            "set_window_size",
            [ctypes.c_uint32, ctypes.c_int, ctypes.c_int],
            ctypes.c_int,
        )
        self._try_bind(
            "set_window_position",
            [ctypes.c_uint32, ctypes.c_int, ctypes.c_int],
            ctypes.c_int,
        )
        self._try_bind(
            "set_window_visible",
            [ctypes.c_uint32, ctypes.c_int],
            ctypes.c_int,
        )
        self._try_bind(
            "set_window_always_on_top",
            [ctypes.c_uint32, ctypes.c_int],
            ctypes.c_int,
        )
        self._try_bind(
            "get_window_theme",
            [ctypes.c_uint32, ctypes.c_char_p, ctypes.c_size_t],
            ctypes.c_int,
        )

        # WebView navigation
        self._try_bind(
            "navigate_to_url",
            [ctypes.c_uint32, ctypes.c_char_p],
            ctypes.c_int,
        )
        self._try_bind(
            "execute_javascript",
            [ctypes.c_uint32, ctypes.c_char_p],
            ctypes.c_int,
        )

        # Event system
        self._try_bind("jade_off", [ctypes.c_char_p], None)

        # Window state queries
        self._try_bind("is_window_maximized", [ctypes.c_uint32], ctypes.c_int)
        self._try_bind("is_window_minimized", [ctypes.c_uint32], ctypes.c_int)
        self._try_bind("is_window_visible", [ctypes.c_uint32], ctypes.c_int)
        self._try_bind("is_window_focused", [ctypes.c_uint32], ctypes.c_int)

        # Window focus
        self._try_bind("focus_window", [ctypes.c_uint32], ctypes.c_int)
        self._try_bind(
            "set_window_fullscreen",
            [ctypes.c_uint32, ctypes.c_int],
            ctypes.c_int,
        )
        self._try_bind(
            "set_window_resizable",
            [ctypes.c_uint32, ctypes.c_int],
            ctypes.c_int,
        )
        self._try_bind(
            "set_window_min_size",
            [ctypes.c_uint32, ctypes.c_int, ctypes.c_int],
            ctypes.c_int,
        )
        self._try_bind(
            "set_window_max_size",
            [ctypes.c_uint32, ctypes.c_int, ctypes.c_int],
            ctypes.c_int,
        )

        # WebView info
        self._try_bind(
            "get_webview_version",
            [ctypes.c_char_p, ctypes.c_size_t],
            ctypes.c_int,
        )

    def is_loaded(self) -> bool:
        """Check if DLL is loaded"""
        return self._loaded

    def has_function(self, name: str) -> bool:
        """Check if a function is available in the DLL

        Args:
            name: Function name

        Returns:
            True if function is available
        """
        return name in self._available_functions

    def get_available_functions(self) -> set[str]:
        """Get set of available function names"""
        return self._available_functions.copy()

    def get_unavailable_functions(self) -> set[str]:
        """Get set of unavailable function names"""
        return self._unavailable_functions.copy()

    def __getattr__(self, name: str) -> Any:
        """Delegate attribute access to the DLL

        For unavailable functions, returns a no-op stub that logs a warning.
        """
        if name.startswith("_"):
            raise AttributeError(f"'{type(self).__name__}' has no attribute '{name}'")

        if self.dll is None:
            raise DLLLoadError("DLL not loaded. Call load() first.")

        # Check if function is unavailable
        if name in self._unavailable_functions:
            # Return a stub function
            def stub(*args, **kwargs):
                logger.debug(f"Called unavailable DLL function: {name}")
                return 0  # Return 0 for int functions, harmless for None

            return stub

        return getattr(self.dll, name)
