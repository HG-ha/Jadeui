"""
JadeUI Window

Window management for JadeUI applications.
"""

from __future__ import annotations

import ctypes
import logging
from json import loads as _json_loads
from typing import Any, Callable, Dict, List, Optional, Tuple, TypeVar, Union

from .core import DLLManager
from .core.types import (
    RGBA,
    FileDropCallback,
    GenericWindowEventCallback,
    WebViewSettings,
    WebViewWindowOptions,
)
from .events import EventEmitter
from .exceptions import WindowCreationError

# Type variables for callback decorators
F = TypeVar("F", bound=Callable[..., Any])

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

    MICA = "mica"  # Mica 效果，Windows 11 默认背景材料
    MICA_ALT = "micaAlt"  # Mica Alt 效果，Mica 的替代版本
    ACRYLIC = "acrylic"  # Acrylic 效果，半透明模糊背景


# ==================== Event Parameter Extractors ====================
# Pre-compiled extractors for high-performance event argument parsing.
# Format: event_name -> (extractor_func, is_dict_passthrough)
# - extractor_func: lambda that extracts args tuple from parsed JSON dict
# - is_dict_passthrough: if True, pass the entire dict to callback


def _extract_none(d: Dict) -> tuple:
    return ()


def _extract_resize(d: Dict) -> tuple:
    return (d.get("width", 0), d.get("height", 0))


def _extract_move(d: Dict) -> tuple:
    return (d.get("x", 0), d.get("y", 0))


def _extract_state(d: Dict) -> tuple:
    return (d.get("isMaximized", False),)


def _extract_url(d: Dict) -> tuple:
    return (d.get("url", ""),)


def _extract_title(d: Dict) -> tuple:
    return (d.get("title", ""),)


def _extract_new_window(d: Dict) -> tuple:
    return (d.get("url", ""), d.get("frame_name", ""))


def _extract_favicon(d: Dict) -> tuple:
    return (d.get("favicon", ""),)


def _extract_js_result(d: Dict) -> tuple:
    return (d.get("callbackId"), d.get("result"))


# Event extractors mapping: event_name -> (extractor, pass_dict_if_no_extractor)
_EVENT_EXTRACTORS: Dict[str, Callable[[Dict], tuple]] = {
    # Window events
    "window-resized": _extract_resize,
    "window-moved": _extract_move,
    "window-state-changed": _extract_state,
    "window-focused": _extract_none,
    "window-blurred": _extract_none,
    "window-closing": _extract_none,
    "window-created": _extract_none,
    "window-closed": _extract_none,
    "window-destroyed": _extract_none,
    # WebView events
    "webview-will-navigate": _extract_url,
    "webview-did-start-loading": _extract_url,
    "webview-did-finish-load": _extract_url,
    "webview-new-window": _extract_new_window,
    "webview-page-title-updated": _extract_title,
    "favicon-updated": _extract_favicon,
    # Other events
    "javascript-result": _extract_js_result,
}


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
                       Args: (files: List[str], x: float, y: float)
                       Note: 使用此事件会接管 WebView 的拖拽事件处理，
                             导致前端无法收到原生拖拽事件。
    """

    # Class-level window registry
    _windows: dict[int, "Window"] = {}

    # Class-level flag to track if global event handlers are registered
    _global_handlers_registered: bool = False
    # Class-level callback references to prevent garbage collection
    _global_callbacks: list = []

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
                - disable_right_click (bool): Disable right-click menu (default: True)
                - user_agent (str): Custom user agent string
                - preload_js (str): JavaScript to run before page load
                - allow_fullscreen (bool): Allow page to enter fullscreen (default: True)
                    Note: Requires JadeView DLL 0.2.1+
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
        self._options.setdefault("disable_right_click", True)
        self._options.setdefault("user_agent", None)
        self._options.setdefault("preload_js", None)
        self._options.setdefault("allow_fullscreen", True)  # JadeView 0.2.1+

        # Callback references to prevent garbage collection
        self._callbacks: list = []

        # 通过 jade_on 注册的事件标志
        self._registered_jade_events: set[str] = set()

        # 待应用的设置（在窗口创建前设置的属性）
        self._pending_backdrop: Optional[str] = None

        # JavaScript 执行回调注册表: callbackId -> callback
        self._js_callbacks: Dict[int, Callable[[Any], Any]] = {}
        self._js_callback_id_counter: int = 0

    # 需要通过 jade_on 注册到 DLL 的事件列表
    # 参考: https://jade.run/guides/events/event-types
    JADE_ON_EVENTS = {
        # 窗口事件
        "window-resized",  # {"width": 宽度, "height": 高度}
        "window-moved",  # {"x": x坐标, "y": y坐标}
        "window-state-changed",  # {"isMaximized": 布尔值}
        "window-focused",  # {}
        "window-blurred",  # {}
        "window-closing",  # {} - 可返回 1 阻止关闭
        "window-created",  # {}
        "window-closed",  # {}
        "window-destroyed",  # {}
        "resized",  # "宽度,高度" (旧兼容格式)
        # WebView 事件
        "webview-will-navigate",  # {"url": "目标URL", "window_id": 窗口ID}
        "webview-did-start-loading",  # {"url": "加载URL", "window_id": 窗口ID}
        "webview-did-finish-load",  # {"url": "加载URL", "window_id": 窗口ID}
        "webview-new-window",  # {"url": "新窗口URL", "frame_name": "_blank"}
        "webview-page-title-updated",  # {"title": "新标题", "window_id": 窗口ID}
        "webview-page-icon-updated",  # JSON对象
        "favicon-updated",  # {"favicon": "图标URL"}
        # 其他事件
        "theme-changed",  # {}
        "javascript-result",  # {"callbackId": 回调ID, "result": 执行结果}
    }

    def on(self, event: str, callback: Optional[Callable[..., Any]] = None) -> Callable[..., Any]:
        """Register an event listener

        Automatically registers events with DLL via jade_on when needed.
        Supported events: https://jade.run/guides/events/event-types

        Args:
            event: Event name to listen for
            callback: Function to call when event is emitted

        Returns:
            The callback function (for decorator usage)
        """
        # file-drop 有特殊的回调签名，单独处理
        if event == "file-drop":
            if callback is None:

                def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
                    self._register_file_drop_handler(fn)
                    return fn

                return decorator
            else:
                self._register_file_drop_handler(callback)
                return callback

        # 其他需要通过 jade_on 注册的事件
        if event in self.JADE_ON_EVENTS:
            if callback is None:

                def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
                    self._register_jade_on_event(event, fn)
                    return fn

                return decorator
            else:
                self._register_jade_on_event(event, callback)
                return callback

        # 其他事件使用父类的 on 方法
        return super().on(event, callback)

    # ==================== Typed Event Decorators ====================
    # These provide IDE type hints for event callback parameters

    def on_resized(self, callback: Callable[[int, int], Any]) -> Callable[[int, int], Any]:
        """Register a callback for window resize events.

        Args:
            callback: Function to call when window is resized.
                - width (int): New window width in pixels
                - height (int): New window height in pixels

        Example:
            @window.on_resized
            def handle_resize(width: int, height: int):
                print(f"Window resized to {width}x{height}")
        """
        self._register_jade_on_event("window-resized", callback)
        return callback

    def on_moved(self, callback: Callable[[int, int], Any]) -> Callable[[int, int], Any]:
        """Register a callback for window move events.

        Args:
            callback: Function to call when window is moved.
                - x (int): New X position in pixels
                - y (int): New Y position in pixels

        Example:
            @window.on_moved
            def handle_move(x: int, y: int):
                print(f"Window moved to ({x}, {y})")
        """
        self._register_jade_on_event("window-moved", callback)
        return callback

    def on_focused(self, callback: Callable[[], Any]) -> Callable[[], Any]:
        """Register a callback for window focus events.

        Args:
            callback: Function to call when window gains focus (no parameters).

        Example:
            @window.on_focused
            def handle_focus():
                print("Window focused")
        """
        self._register_jade_on_event("window-focused", callback)
        return callback

    def on_blurred(self, callback: Callable[[], Any]) -> Callable[[], Any]:
        """Register a callback for window blur events.

        Args:
            callback: Function to call when window loses focus (no parameters).

        Example:
            @window.on_blurred
            def handle_blur():
                print("Window lost focus")
        """
        self._register_jade_on_event("window-blurred", callback)
        return callback

    def on_closing(
        self, callback: Callable[[], Union[bool, int, None]]
    ) -> Callable[[], Union[bool, int, None]]:
        """Register a callback for window closing events.

        Return True or 1 to prevent the window from closing.

        Args:
            callback: Function to call when window is about to close.
                Returns: True/1 to prevent closing, False/0/None to allow.

        Example:
            @window.on_closing
            def handle_closing():
                if has_unsaved_changes:
                    return True  # Prevent closing
                return False  # Allow closing
        """
        self._register_jade_on_event("window-closing", callback)
        return callback

    def on_state_changed(self, callback: Callable[[bool], Any]) -> Callable[[bool], Any]:
        """Register a callback for window state change events.

        Args:
            callback: Function to call when window state changes.
                - is_maximized (bool): Whether window is maximized

        Example:
            @window.on_state_changed
            def handle_state(is_maximized: bool):
                print(f"Maximized: {is_maximized}")
        """
        self._register_jade_on_event("window-state-changed", callback)
        return callback

    def on_file_dropped(
        self, callback: Callable[[List[str], int, int], Any]
    ) -> Callable[[List[str], int, int], Any]:
        """Register a callback for file drop events.

        Note: Using this event will intercept WebView's drag events,
              preventing the frontend from receiving native drag events.

        Args:
            callback: Function to call when files are dropped.
                - files (List[str]): List of dropped file paths
                - x (int): Drop X position
                - y (int): Drop Y position

        Example:
            @window.on_file_dropped
            def handle_drop(files: list, x: int, y: int):
                print(f"Dropped {len(files)} files at ({x}, {y})")
                for f in files:
                    print(f"  - {f}")
        """
        self._register_file_drop_handler(callback)
        return callback

    def on_navigate(
        self, callback: Callable[[str], Union[bool, int, None]]
    ) -> Callable[[str], Union[bool, int, None]]:
        """Register a callback for navigation events.

        Return True or 1 to prevent navigation.

        Args:
            callback: Function to call before navigation.
                - url (str): Target URL
                Returns: True/1 to prevent navigation, False/0/None to allow.

        Example:
            @window.on_navigate
            def handle_navigate(url: str):
                if "dangerous" in url:
                    return True  # Block navigation
                print(f"Navigating to: {url}")
        """
        self._register_jade_on_event("webview-will-navigate", callback)
        return callback

    def on_page_loaded(self, callback: Callable[[str], Any]) -> Callable[[str], Any]:
        """Register a callback for page load complete events.

        Args:
            callback: Function to call when page finishes loading.
                - url (str): Loaded page URL

        Example:
            @window.on_page_loaded
            def handle_loaded(url: str):
                print(f"Page loaded: {url}")
        """
        self._register_jade_on_event("webview-did-finish-load", callback)
        return callback

    def on_title_updated(self, callback: Callable[[str], Any]) -> Callable[[str], Any]:
        """Register a callback for page title update events.

        Args:
            callback: Function to call when page title changes.
                - title (str): New page title

        Example:
            @window.on_title_updated
            def handle_title(title: str):
                print(f"Title changed to: {title}")
        """
        self._register_jade_on_event("webview-page-title-updated", callback)
        return callback

    def on_new_window(
        self, callback: Callable[[str, str], Union[bool, int, None]]
    ) -> Callable[[str, str], Union[bool, int, None]]:
        """Register a callback for new window request events.

        Return True or 1 to prevent opening new window.

        Args:
            callback: Function to call when new window is requested.
                - url (str): URL for new window
                - frame_name (str): Target frame name (e.g., "_blank")
                Returns: True/1 to prevent, False/0/None to allow.

        Example:
            @window.on_new_window
            def handle_new_window(url: str, frame_name: str):
                print(f"New window requested: {url}")
                # Open in same window instead
                window.navigate(url)
                return True  # Prevent new window
        """
        self._register_jade_on_event("webview-new-window", callback)
        return callback

    def on_js_result(self, callback: Callable[[int, Any], Any]) -> Callable[[int, Any], Any]:
        """Register a callback for JavaScript execution result events.

        This listens to the native javascript-result event from the DLL.
        For simpler usage, consider using execute_js() with a callback parameter.

        Args:
            callback: Function to call when JS execution completes.
                - callback_id (int): The callback ID
                - result (Any): The execution result

        Example:
            @window.on_js_result
            def handle_js_result(callback_id: int, result):
                print(f"JS result [{callback_id}]: {result}")
        """
        self._register_jade_on_event("javascript-result", callback)
        return callback

    # ==================== Internal Event Registration ====================

    def _register_jade_on_event(self, event: str, callback: Callable[..., Any]) -> None:
        """通用的 jade_on 事件注册器

        Uses pre-compiled extractors for high-performance event argument parsing.
        """
        # 添加到本地监听器
        self._listeners[event].append(callback)

        # 只注册一次到 DLL
        if event in self._registered_jade_events:
            return

        # 获取预编译的参数提取器（O(1) 查找）
        extractor = _EVENT_EXTRACTORS.get(event)

        # 创建 ctypes 回调
        @GenericWindowEventCallback
        def event_callback(window_id: int, json_data: bytes) -> int:
            result = 0
            try:
                # 解析 JSON
                data_str = json_data.decode("utf-8") if json_data else "{}"
                data_dict = _json_loads(data_str) if data_str else {}
                logger.debug(f"Event {event}: window={window_id}, data={data_str}")

                # 提取参数
                if extractor is not None:
                    args = extractor(data_dict)
                else:
                    # 未知事件：传递解析后的字典
                    args = (data_dict,)

                # 调用所有监听器，收集返回值（用于阻止事件）
                for cb in list(self._listeners.get(event, [])):
                    try:
                        ret = cb(*args)
                        # 如果任何回调返回 True 或 1，则阻止事件
                        # 适用于: window-closing, webview-new-window
                        if ret is True or ret == 1:
                            result = 1
                    except Exception as e:
                        logger.error(f"Error in {event} callback: {e}")
            except Exception as e:
                logger.error(f"Error in {event} event handler: {e}")
            return result

        # 保存引用防止垃圾回收
        self._callbacks.append(event_callback)

        # 通过 jade_on 注册到 DLL
        self.dll_manager.jade_on(
            event.encode("utf-8"),
            ctypes.cast(event_callback, ctypes.c_void_p),
        )

        self._registered_jade_events.add(event)
        logger.info(f"{event} event handler registered with DLL")

    def _register_file_drop_handler(self, callback: Callable[..., Any]) -> None:
        """注册 file-drop 事件处理器到 DLL"""
        # 添加到本地监听器
        self._listeners["file-drop"].append(callback)

        # 只注册一次到 DLL
        if "file-drop" in self._registered_jade_events:
            return

        # 创建 ctypes 回调
        @FileDropCallback
        def file_drop_callback(window_id: int, json_data: bytes) -> None:
            self._on_file_drop(window_id, json_data)

        # 保存引用防止垃圾回收
        self._callbacks.append(file_drop_callback)

        # 通过 jade_on 注册到 DLL
        self.dll_manager.jade_on(
            b"file-drop",
            ctypes.cast(file_drop_callback, ctypes.c_void_p),
        )

        self._registered_jade_events.add("file-drop")
        logger.info("file-drop event handler registered with DLL")

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

    def run(
        self,
        url: Optional[str] = None,
        web_dir: Optional[str] = None,
        entry: str = "index.html",
        enable_dev_tools: bool = False,
    ) -> None:
        """Run the window with automatic app initialization

        This is a convenience method for simple single-window applications.
        It automatically initializes JadeUIApp if needed, shows the window,
        and runs the message loop.

        Also registers default IPC handlers for window actions (close, minimize, maximize).

        Args:
            url: URL to load (takes precedence over web_dir)
            web_dir: Local web directory path. If provided, automatically starts
                    a local server. Can be:
                    - Absolute path: "C:/myapp/web"
                    - Relative path: "web" (relative to caller's directory)
                    - None: auto-detect "web" folder in caller's directory
            entry: Entry HTML file when using web_dir (default: "index.html")
            enable_dev_tools: Whether to enable developer tools (F12)

        Example:
            # Simplest - auto-detect web folder
            from jadeui import Window
            Window(title="My App").run()

            # With explicit web directory
            Window(title="My App").run(web_dir="web")

            # With remote URL
            Window(title="My App").run(url="https://example.com")
        """
        import inspect
        import os

        from .app import JadeUIApp
        from .ipc import IPCManager
        from .server import LocalServer

        # 获取调用者的目录
        caller_frame = inspect.stack()[1]
        caller_dir = os.path.dirname(os.path.abspath(caller_frame.filename))

        # 处理 web_dir 和 url
        if url:
            self._url = url
        elif web_dir is not None:
            # 使用指定的 web 目录
            if not os.path.isabs(web_dir):
                web_dir = os.path.join(caller_dir, web_dir)
            if not os.path.isdir(web_dir):
                raise ValueError(f"web 目录不存在: {web_dir}")
            server = LocalServer()
            server_url = server.start("app", web_dir)
            self._url = f"{server_url}/{entry}"
        elif self._url is None:
            # 自动检测 web 目录
            auto_web_dir = os.path.join(caller_dir, "web")
            if os.path.isdir(auto_web_dir):
                server = LocalServer()
                server_url = server.start("app", auto_web_dir)
                self._url = f"{server_url}/{entry}"
            else:
                raise ValueError(
                    f"未指定 url 或 web_dir，且未在 {caller_dir} 下找到 web 目录。\n"
                    "请指定 url 或 web_dir 参数，或在脚本同级目录创建 web 文件夹。"
                )

        # Get or create JadeUIApp instance
        app = JadeUIApp.get_instance()
        if app is None:
            app = JadeUIApp()

        # Initialize if not already initialized
        if not app._initialized:
            app.initialize(enable_dev_tools=enable_dev_tools)

        # 注册默认的窗口操作 IPC 处理器
        ipc = IPCManager()

        @ipc.on("windowAction")
        def _handle_window_action(window_id: int, action: str) -> int:
            win = Window.get_window_by_id(window_id)
            if win:
                if action == "close":
                    win.close()
                elif action == "minimize":
                    win.minimize()
                elif action == "maximize":
                    win.maximize()
            return 1

        # 保存 window 引用，在 on_ready 中显示
        window = self

        # 注册 on_ready 回调来显示窗口
        @app.on_ready
        def _show_window():
            window.show()

        # Run message loop
        app.run()

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

        Note:
            Requires JadeView DLL version 0.2.1 or above.

        Args:
            fullscreen: Whether to enable fullscreen

        Returns:
            Self for chaining
        """
        self._options["fullscreen"] = fullscreen
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
            result = self.dll_manager.get_window_theme(self.id, buffer, ctypes.sizeof(buffer))
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
        else:
            # 保存设置，在窗口创建后应用
            self._pending_backdrop = backdrop
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

    def execute_js(
        self,
        script: str,
        callback: Optional[Callable[[Any], Any]] = None,
    ) -> "Window":
        """Execute JavaScript in the window

        Args:
            script: JavaScript code to execute
            callback: Optional callback function to receive the result.
                      Will be called with the JavaScript execution result.
                      Note: Requires registering javascript-result event handler.

        Returns:
            Self for chaining

        Example:
            # Without callback
            window.execute_js("console.log('Hello')")

            # With callback
            def on_result(result):
                print(f"Result: {result}")
            window.execute_js("1 + 1", callback=on_result)
        """
        if self.id is not None:
            if callback is not None:
                # 生成唯一的 callbackId 并注册回调
                self._js_callback_id_counter += 1
                callback_id = self._js_callback_id_counter
                self._js_callbacks[callback_id] = callback

                # 确保已注册 javascript-result 事件处理器
                self._ensure_js_result_handler()

                # 包装脚本以返回 callbackId
                wrapped_script = f"""
(function() {{
    try {{
        var result = eval({repr(script)});
        if (typeof jade !== 'undefined' && jade.ipcSend) {{
            jade.ipcSend('__js_result__', JSON.stringify({{
                callbackId: {callback_id},
                result: result
            }}));
        }}
    }} catch (e) {{
        if (typeof jade !== 'undefined' && jade.ipcSend) {{
            jade.ipcSend('__js_result__', JSON.stringify({{
                callbackId: {callback_id},
                error: e.message
            }}));
        }}
    }}
}})();
"""
                self.dll_manager.execute_javascript(self.id, wrapped_script.encode("utf-8"))
            else:
                self.dll_manager.execute_javascript(self.id, script.encode("utf-8"))
        return self

    def _ensure_js_result_handler(self) -> None:
        """确保已注册 JavaScript 结果处理器"""
        if "__js_result__" in self._registered_jade_events:
            return

        from .ipc import IPCManager

        ipc = IPCManager(self.dll_manager)

        @ipc.on("__js_result__")
        def handle_js_result(window_id: int, message: str) -> int:
            try:
                data = _json_loads(message) if message else {}
                callback_id = data.get("callbackId")
                result = data.get("result")
                error = data.get("error")

                if callback_id and callback_id in self._js_callbacks:
                    callback = self._js_callbacks.pop(callback_id)
                    if error:
                        logger.error(f"JS execution error: {error}")
                        callback(None)
                    else:
                        callback(result)
            except Exception as e:
                logger.error(f"Error handling JS result: {e}")
            return 1

        self._registered_jade_events.add("__js_result__")
        logger.info("JavaScript result handler registered")

    def eval(self, script: str, callback: Optional[Callable[[Any], Any]] = None) -> "Window":
        """Execute JavaScript (alias for execute_js)

        Args:
            script: JavaScript code to execute
            callback: Optional callback function to receive the result

        Returns:
            Self for chaining
        """
        return self.execute_js(script, callback)

    def reload(self) -> "Window":
        """Reload the current page in the WebView

        Reloads the current page content, equivalent to browser's refresh button.

        Note:
            Requires JadeView DLL version 0.2 or above.

        Returns:
            Self for chaining
        """
        if self.id is not None:
            self.dll_manager.reload(self.id)
        return self

    def refresh(self) -> "Window":
        """Refresh the current page (alias for reload)

        Returns:
            Self for chaining
        """
        return self.reload()

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
        """Check if window is in fullscreen mode

        Note:
            Requires JadeView DLL version 0.2.1 or above for accurate query.
            Falls back to local state tracking for older versions.
        """
        if self.id is not None:
            # Try to query DLL first (JadeView 0.2.1+)
            if self.dll_manager.has_function("is_window_fullscreen"):
                return self.dll_manager.is_window_fullscreen(self.id) == 1
        # Fallback to local tracking
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
            allow_fullscreen=self._options.get("allow_fullscreen", True),
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

            # 应用 backdrop（优先使用 set_backdrop 设置的值）
            backdrop = self._pending_backdrop or self._options.get("backdrop")
            if backdrop:
                self.dll_manager.set_window_backdrop(self.id, backdrop.encode("utf-8"))
                self._pending_backdrop = None  # 清除待处理设置

            # Set up event handlers
            self._setup_event_handlers()

            # Emit created event
            self.emit("created", self)

        except Exception as e:
            raise WindowCreationError(f"Failed to create window: {e}")

    def _setup_event_handlers(self) -> None:
        """Set up event handlers for the window

        Uses jade_on to register global event handlers (only once per class).
        This replaces the deprecated set_window_event_handlers API.
        """
        if self.id is None:
            return

        # Register global handlers only once (class-level)
        if not Window._global_handlers_registered:
            self._register_global_event_handlers()
            Window._global_handlers_registered = True

    @classmethod
    def _register_global_event_handlers(cls) -> None:
        """Register global event handlers using jade_on

        This replaces the deprecated set_window_event_handlers API.
        All window events are now handled through jade_on.
        """
        dll = DLLManager()

        # Register window-closed event handler
        @GenericWindowEventCallback
        def window_closed_callback(window_id: int, json_data: bytes) -> int:
            try:
                window = cls._windows.get(window_id)
                if window:
                    window._on_closed()
            except Exception as e:
                logger.error(f"Error in window-closed handler: {e}")
            return 0

        cls._global_callbacks.append(window_closed_callback)
        dll.jade_on(
            b"window-closed",
            ctypes.cast(window_closed_callback, ctypes.c_void_p),
        )

        # Register page load events via jade_on
        # webview-did-finish-load: {"url": "...", "window_id": ...}
        @GenericWindowEventCallback
        def page_load_callback(window_id: int, json_data: bytes) -> int:
            try:
                data_str = json_data.decode("utf-8") if json_data else "{}"
                window = cls._windows.get(window_id)
                if window:
                    data = _json_loads(data_str) if data_str else {}
                    url = data.get("url", "")
                    logger.debug(f"Page load: {window_id}, {url}")
                    window.emit("page-loaded", url, "complete")
            except Exception as e:
                logger.error(f"Error in page-load handler: {e}")
            return 0

        cls._global_callbacks.append(page_load_callback)
        dll.jade_on(
            b"webview-did-finish-load",
            ctypes.cast(page_load_callback, ctypes.c_void_p),
        )

        logger.info("Global event handlers registered via jade_on")

    def _on_closed(self) -> None:
        """Handle window closed"""
        if self.id is not None:
            if self.id in Window._windows:
                del Window._windows[self.id]
            self.emit("closed")
            self.id = None

    def _on_file_drop(self, window_id: int, json_data: bytes) -> None:
        """Handle file drop events

        Args:
            window_id: The window ID
            json_data: JSON data containing files array and position
                      Format: {"files": ["path1", "path2"], "x": x, "y": y}
        """
        try:
            data_str = json_data.decode("utf-8") if json_data else "{}"
            data = _json_loads(data_str) if data_str else {}

            files = data.get("files", [])
            x = data.get("x", 0)
            y = data.get("y", 0)

            logger.debug(f"File drop: window={window_id}, files={files}, x={x}, y={y}")
            self.emit("file-drop", files, x, y)
        except Exception as e:
            logger.error(f"Error parsing file drop data: {e}")
            self.emit("file-drop", [], 0, 0)

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
