"""
JadeUI Window

Window management for JadeUI applications.
"""

import ctypes
import logging
from typing import Optional, Union, Callable, Any, Tuple

from .core import DLLManager
from .core.types import (
    WebViewWindowOptions,
    WebViewSettings,
    RGBA,
    WindowEventCallback,
    PageLoadCallback,
    FileDropCallback,
)
from .events import EventEmitter
from .exceptions import WindowCreationError

logger = logging.getLogger(__name__)


# Theme constants
class Theme:
    """Window theme constants"""
    
    LIGHT = "Light"
    DARK = "Dark"
    SYSTEM = "System"


# Backdrop material constants (Windows 11)
class Backdrop:
    """Window backdrop material constants for Windows 11
    
    Note: Window must have transparent=True for backdrop effects to work.
    """
    
    MICA = "mica"           # Mica 效果，Windows 11 默认背景材料
    MICA_ALT = "micaAlt"    # Mica Alt 效果，Mica 的替代版本
    ACRYLIC = "acrylic"     # Acrylic 效果，半透明模糊背景


class Window(EventEmitter):
    """A WebView window in JadeUI

    Represents a single window containing a WebView. Windows can be created,
    configured, and controlled through this class.

    Example:
        window = Window(title="My App", width=1024, height=768)
        window.load_url("https://example.com")
        window.show()

    Events:
        - 'close': Fired when window is about to close
        - 'closed': Fired when window is closed
        - 'focus': Fired when window gains focus
        - 'blur': Fired when window loses focus
        - 'resize': Fired when window is resized
        - 'move': Fired when window is moved
        - 'page-loaded': Fired when page finishes loading
        - 'file-drop': Fired when files are dropped on window
    """

    # Class-level window registry
    _windows: dict[int, "Window"] = {}

    def __init__(
        self,
        title: str = "Window",
        width: int = 800,
        height: int = 600,
        url: Optional[str] = None,
        dll_manager: Optional[DLLManager] = None,
        **options,
    ):
        """Create a new window

        Args:
            title: Window title
            width: Window width in pixels
            height: Window height in pixels
            url: URL to load (optional, can be set later)
            dll_manager: DLL manager instance (uses global if None)
            **options: Additional window options:
                - resizable (bool): Allow window resizing (default: True)
                - remove_titlebar (bool): Remove native title bar (default: False)
                - transparent (bool): Enable window transparency (default: False)
                - background_color (RGBA): Window background color
                - always_on_top (bool): Keep window always on top (default: False)
                - theme (str): Window theme ('Light', 'Dark', 'System')
                - maximized (bool): Start maximized (default: False)
                - maximizable (bool): Allow maximize (default: True)
                - minimizable (bool): Allow minimize (default: True)
                - x (int): Window X position (-1 for center)
                - y (int): Window Y position (-1 for center)
                - min_width (int): Minimum window width
                - min_height (int): Minimum window height
                - max_width (int): Maximum window width (0 for no limit)
                - max_height (int): Maximum window height (0 for no limit)
                - fullscreen (bool): Start in fullscreen (default: False)
                - focus (bool): Focus window on creation (default: True)
                - hide_window (bool): Create hidden (default: False)
                - use_page_icon (bool): Use page favicon as window icon (default: True)
                - autoplay (bool): Allow media autoplay (default: False)
                - disable_right_click (bool): Disable right-click menu (default: False)
                - user_agent (str): Custom user agent string
                - preload_js (str): JavaScript to run before page load
        """
        super().__init__()
        
        self.dll_manager = dll_manager or DLLManager()
        if not self.dll_manager.is_loaded():
            self.dll_manager.load()

        self.id: Optional[int] = None
        self._title = title
        self._width = width
        self._height = height
        self._url = url

        # Store options for later use
        self._options = options.copy()
        self._options.setdefault("resizable", True)
        self._options.setdefault("remove_titlebar", False)
        self._options.setdefault("transparent", False)
        self._options.setdefault("background_color", RGBA(255, 255, 255, 255))
        self._options.setdefault("always_on_top", False)
        self._options.setdefault("theme", Theme.SYSTEM)
        self._options.setdefault("maximized", False)
        self._options.setdefault("maximizable", True)
        self._options.setdefault("minimizable", True)
        self._options.setdefault("x", -1)
        self._options.setdefault("y", -1)
        self._options.setdefault("min_width", 0)
        self._options.setdefault("min_height", 0)
        self._options.setdefault("max_width", 0)
        self._options.setdefault("max_height", 0)
        self._options.setdefault("fullscreen", False)
        self._options.setdefault("focus", True)
        self._options.setdefault("hide_window", False)
        self._options.setdefault("use_page_icon", True)

        # WebView settings
        self._options.setdefault("autoplay", False)
        self._options.setdefault("background_throttling", False)
        self._options.setdefault("disable_right_click", False)
        self._options.setdefault("user_agent", None)
        self._options.setdefault("preload_js", None)

        # Callback references to prevent garbage collection
        self._callbacks: list = []

    # ==================== Window Lifecycle ====================

    def show(self, url: Optional[str] = None) -> "Window":
        """Show the window

        Args:
            url: Optional URL to load

        Returns:
            Self for chaining
        """
        if url:
            self._url = url

        if self.id is None:
            self._create_window()
        else:
            self.set_visible(True)

        return self

    def hide(self) -> "Window":
        """Hide the window

        Returns:
            Self for chaining
        """
        if self.id is not None:
            self.set_visible(False)
        return self

    def close(self) -> None:
        """Close the window"""
        if self.id is not None:
            result = self.dll_manager.close_window(self.id)
            if result == 1:
                logger.info(f"Window {self.id} closed")
                self._on_closed()
            else:
                logger.error(f"Failed to close window {self.id}")

    def destroy(self) -> None:
        """Force destroy the window (alias for close)"""
        self.close()

    def focus(self) -> "Window":
        """Focus the window

        Returns:
            Self for chaining
        """
        if self.id is not None:
            self.dll_manager.focus_window(self.id)
        return self

    # ==================== Window State ====================

    def minimize(self) -> "Window":
        """Minimize the window

        Returns:
            Self for chaining
        """
        if self.id is not None:
            self.dll_manager.minimize_window(self.id)
        return self

    def maximize(self) -> "Window":
        """Toggle maximize/restore for the window

        Returns:
            Self for chaining
        """
        if self.id is not None:
            self.dll_manager.toggle_maximize_window(self.id)
        return self

    def restore(self) -> "Window":
        """Restore the window from minimized/maximized state

        Returns:
            Self for chaining
        """
        # If maximized, toggle to restore
        if self.is_maximized:
            self.dll_manager.toggle_maximize_window(self.id)
        return self

    def set_fullscreen(self, fullscreen: bool) -> "Window":
        """Set fullscreen mode

        Args:
            fullscreen: Whether to enable fullscreen

        Returns:
            Self for chaining
        """
        if self.id is not None:
            self.dll_manager.set_window_fullscreen(self.id, 1 if fullscreen else 0)
        return self

    def toggle_fullscreen(self) -> "Window":
        """Toggle fullscreen mode

        Returns:
            Self for chaining
        """
        return self.set_fullscreen(not self.is_fullscreen)

    # ==================== Window Properties ====================

    @property
    def title(self) -> str:
        """Get window title"""
        return self._title

    @title.setter
    def title(self, value: str) -> None:
        """Set window title"""
        self.set_title(value)

    def set_title(self, title: str) -> "Window":
        """Set the window title

        Args:
            title: New window title

        Returns:
            Self for chaining
        """
        self._title = title
        if self.id is not None:
            self.dll_manager.set_window_title(self.id, title.encode("utf-8"))
        return self

    @property
    def size(self) -> Tuple[int, int]:
        """Get window size as (width, height)"""
        return (self._width, self._height)

    def set_size(self, width: int, height: int) -> "Window":
        """Set the window size

        Args:
            width: New width in pixels
            height: New height in pixels

        Returns:
            Self for chaining
        """
        self._width = width
        self._height = height
        if self.id is not None:
            self.dll_manager.set_window_size(self.id, width, height)
        return self

    def set_min_size(self, width: int, height: int) -> "Window":
        """Set minimum window size

        Args:
            width: Minimum width
            height: Minimum height

        Returns:
            Self for chaining
        """
        if self.id is not None:
            self.dll_manager.set_window_min_size(self.id, width, height)
        return self

    def set_max_size(self, width: int, height: int) -> "Window":
        """Set maximum window size

        Args:
            width: Maximum width (0 for no limit)
            height: Maximum height (0 for no limit)

        Returns:
            Self for chaining
        """
        if self.id is not None:
            self.dll_manager.set_window_max_size(self.id, width, height)
        return self

    @property
    def position(self) -> Tuple[int, int]:
        """Get window position as (x, y)"""
        return (self._options.get("x", -1), self._options.get("y", -1))

    def set_position(self, x: int, y: int) -> "Window":
        """Set the window position

        Args:
            x: X position
            y: Y position

        Returns:
            Self for chaining
        """
        self._options["x"] = x
        self._options["y"] = y
        if self.id is not None:
            self.dll_manager.set_window_position(self.id, x, y)
        return self

    def center(self) -> "Window":
        """Center the window on screen

        Returns:
            Self for chaining
        """
        return self.set_position(-1, -1)

    def set_visible(self, visible: bool) -> "Window":
        """Set window visibility

        Args:
            visible: Whether window should be visible

        Returns:
            Self for chaining
        """
        if self.id is not None:
            self.dll_manager.set_window_visible(self.id, 1 if visible else 0)
        return self

    def set_always_on_top(self, on_top: bool) -> "Window":
        """Set always on top

        Args:
            on_top: Whether window should stay on top

        Returns:
            Self for chaining
        """
        if self.id is not None:
            self.dll_manager.set_window_always_on_top(self.id, 1 if on_top else 0)
        return self

    def set_resizable(self, resizable: bool) -> "Window":
        """Set whether window is resizable

        Args:
            resizable: Whether window can be resized

        Returns:
            Self for chaining
        """
        if self.id is not None:
            self.dll_manager.set_window_resizable(self.id, 1 if resizable else 0)
        return self

    # ==================== Theme & Appearance ====================

    def set_theme(self, theme: str) -> "Window":
        """Set window theme

        Args:
            theme: Theme name ('Light', 'Dark', 'System')

        Returns:
            Self for chaining
        """
        if self.id is not None:
            self.dll_manager.set_window_theme(self.id, theme.encode("utf-8"))
        return self

    def get_theme(self) -> str:
        """Get current window theme

        Returns:
            Current theme name
        """
        if self.id is not None:
            buffer = ctypes.create_string_buffer(32)
            result = self.dll_manager.get_window_theme(
                self.id, buffer, ctypes.sizeof(buffer)
            )
            if result == 1:
                return buffer.value.decode("utf-8")
        return Theme.SYSTEM

    def set_backdrop(self, backdrop: str) -> "Window":
        """Set window backdrop material (Windows 11)

        Args:
            backdrop: Backdrop type ('mica', 'micaalt', 'acrylic')

        Returns:
            Self for chaining
        """
        if self.id is not None:
            self.dll_manager.set_window_backdrop(self.id, backdrop.encode("utf-8"))
        return self

    # ==================== WebView Operations ====================

    def load_url(self, url: str) -> "Window":
        """Navigate to a URL

        Args:
            url: URL to load

        Returns:
            Self for chaining
        """
        self._url = url
        if self.id is not None:
            self.dll_manager.navigate_to_url(self.id, url.encode("utf-8"))
        return self

    def navigate(self, url: str) -> "Window":
        """Navigate to a URL (alias for load_url)

        Args:
            url: URL to load

        Returns:
            Self for chaining
        """
        return self.load_url(url)

    def execute_js(self, script: str) -> "Window":
        """Execute JavaScript in the window

        Args:
            script: JavaScript code to execute

        Returns:
            Self for chaining
        """
        if self.id is not None:
            self.dll_manager.execute_javascript(self.id, script.encode("utf-8"))
        return self

    def eval(self, script: str) -> "Window":
        """Execute JavaScript (alias for execute_js)

        Args:
            script: JavaScript code to execute

        Returns:
            Self for chaining
        """
        return self.execute_js(script)

    # ==================== State Queries ====================

    @property
    def is_visible(self) -> bool:
        """Check if window is visible"""
        if self.id is not None:
            return self.dll_manager.is_window_visible(self.id) == 1
        return False

    @property
    def is_maximized(self) -> bool:
        """Check if window is maximized"""
        if self.id is not None:
            return self.dll_manager.is_window_maximized(self.id) == 1
        return False

    @property
    def is_minimized(self) -> bool:
        """Check if window is minimized"""
        if self.id is not None:
            return self.dll_manager.is_window_minimized(self.id) == 1
        return False

    @property
    def is_focused(self) -> bool:
        """Check if window is focused"""
        if self.id is not None:
            return self.dll_manager.is_window_focused(self.id) == 1
        return False

    @property
    def is_fullscreen(self) -> bool:
        """Check if window is in fullscreen mode"""
        # Note: DLL might not provide this query, track locally
        return self._options.get("fullscreen", False)

    # ==================== Window Creation ====================

    def _create_window(self) -> None:
        """Create the actual window using the DLL"""
        # Prepare background color
        background_color = self._options.get("background_color")
        if isinstance(background_color, dict):
            background_color = RGBA(
                background_color.get("r", 255),
                background_color.get("g", 255),
                background_color.get("b", 255),
                background_color.get("a", 255),
            )
        elif background_color is None:
            background_color = RGBA(255, 255, 255, 255)

        # Prepare theme
        theme = self._options.get("theme", Theme.SYSTEM)
        if isinstance(theme, str):
            theme = theme.encode("utf-8")

        # Create window options
        window_options = WebViewWindowOptions(
            title=self._title.encode("utf-8"),
            width=self._width,
            height=self._height,
            resizable=self._options.get("resizable", True),
            remove_titlebar=self._options.get("remove_titlebar", False),
            transparent=self._options.get("transparent", False),
            background_color=background_color,
            always_on_top=self._options.get("always_on_top", False),
            no_center=self._options.get("x", -1) != -1 or self._options.get("y", -1) != -1,
            theme=theme,
            maximized=self._options.get("maximized", False),
            maximizable=self._options.get("maximizable", True),
            minimizable=self._options.get("minimizable", True),
            x=self._options.get("x", -1),
            y=self._options.get("y", -1),
            min_width=self._options.get("min_width", 0),
            min_height=self._options.get("min_height", 0),
            max_width=self._options.get("max_width", 0),
            max_height=self._options.get("max_height", 0),
            fullscreen=self._options.get("fullscreen", False),
            focus=self._options.get("focus", True),
            hide_window=self._options.get("hide_window", False),
            use_page_icon=self._options.get("use_page_icon", True),
        )

        # Prepare WebView settings
        user_agent = self._options.get("user_agent")
        preload_js = self._options.get("preload_js")

        settings = WebViewSettings(
            autoplay=self._options.get("autoplay", False),
            background_throttling=self._options.get("background_throttling", False),
            disable_right_click=self._options.get("disable_right_click", False),
            ua=user_agent.encode("utf-8") if user_agent else None,
            preload_js=preload_js.encode("utf-8") if preload_js else None,
        )

        # Prepare URL
        url_bytes = self._url.encode("utf-8") if self._url else b""

        # Create window
        try:
            self.id = self.dll_manager.create_webview_window(
                url_bytes,
                0,  # parent window ID
                ctypes.byref(window_options),
                ctypes.byref(settings),
            )

            if self.id == 0:
                raise WindowCreationError("Failed to create window")

            logger.info(f"Window created with ID: {self.id}")

            # Register in window registry
            Window._windows[self.id] = self

            # Apply theme and backdrop after creation
            if theme:
                self.dll_manager.set_window_theme(self.id, theme)

            backdrop = self._options.get("backdrop")
            if backdrop:
                self.dll_manager.set_window_backdrop(self.id, backdrop.encode("utf-8"))

            # Set up event handlers
            self._setup_event_handlers()

            # Emit created event
            self.emit("created", self)

        except Exception as e:
            raise WindowCreationError(f"Failed to create window: {e}")

    def _setup_event_handlers(self) -> None:
        """Set up event handlers for the window"""
        if self.id is None:
            return

        # Create callback functions
        @WindowEventCallback
        def window_event_callback(window_id, event_type, event_data):
            return self._on_window_event(window_id, event_type, event_data)

        @PageLoadCallback
        def page_load_callback(window_id, url, status):
            self._on_page_load(window_id, url, status)

        @FileDropCallback
        def file_drop_callback(window_id, file_path, mime_type, x, y):
            self._on_file_drop(window_id, file_path, mime_type, x, y)

        # Store references to prevent garbage collection
        self._callbacks.extend(
            [window_event_callback, page_load_callback, file_drop_callback]
        )

        # Register with DLL (use 0 for global event handlers)
        self.dll_manager.set_window_event_handlers(
            0,
            ctypes.cast(window_event_callback, ctypes.c_void_p),
            ctypes.cast(page_load_callback, ctypes.c_void_p),
            ctypes.cast(file_drop_callback, ctypes.c_void_p),
        )

    def _on_window_event(
        self, window_id: int, event_type: bytes, event_data: bytes
    ) -> int:
        """Handle window events"""
        event_type_str = event_type.decode("utf-8") if event_type else ""
        event_data_str = event_data.decode("utf-8") if event_data else ""

        logger.debug(f"Window event: {window_id}, {event_type_str}, {event_data_str}")

        # Emit event
        self.emit(event_type_str, event_data_str)

        # Handle window closed
        if event_type_str in ["window-closed", "close", "closed"]:
            self._on_closed()

        return 0

    def _on_closed(self) -> None:
        """Handle window closed"""
        if self.id is not None:
            if self.id in Window._windows:
                del Window._windows[self.id]
            self.emit("closed")
            self.id = None

    def _on_page_load(self, window_id: int, url: bytes, status: bytes) -> None:
        """Handle page load events"""
        url_str = url.decode("utf-8") if url else ""
        status_str = status.decode("utf-8") if status else ""

        logger.debug(f"Page load: {window_id}, {url_str}, {status_str}")
        self.emit("page-loaded", url_str, status_str)

    def _on_file_drop(
        self, window_id: int, file_path: bytes, mime_type: bytes, x: float, y: float
    ) -> None:
        """Handle file drop events"""
        file_path_str = file_path.decode("utf-8") if file_path else ""
        mime_type_str = mime_type.decode("utf-8") if mime_type else ""

        logger.debug(
            f"File drop: {window_id}, {file_path_str}, {mime_type_str}, {x}, {y}"
        )
        self.emit("file-drop", file_path_str, mime_type_str, x, y)

    # ==================== Static Methods ====================

    @staticmethod
    def get_window_count() -> int:
        """Get the number of active windows

        Returns:
            Number of active windows
        """
        dll = DLLManager()
        if dll.is_loaded():
            return dll.get_window_count()
        return 0

    @staticmethod
    def get_window_by_id(window_id: int) -> Optional["Window"]:
        """Get a window by its ID

        Args:
            window_id: Window ID

        Returns:
            Window instance or None
        """
        return Window._windows.get(window_id)

    @staticmethod
    def get_all_windows() -> list["Window"]:
        """Get all active windows

        Returns:
            List of active Window instances
        """
        return list(Window._windows.values())

    # ==================== Dunder Methods ====================

    def __repr__(self) -> str:
        return f"Window(id={self.id}, title='{self._title}', size={self._width}x{self._height})"

    def __enter__(self) -> "Window":
        """Context manager entry"""
        if self.id is None:
            self._create_window()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit"""
        self.close()
