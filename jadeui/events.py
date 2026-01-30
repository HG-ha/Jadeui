"""
JadeUI Event System

Centralized event system for handling window events, app events, and custom events.
"""

from __future__ import annotations

import ctypes
import logging
from collections import defaultdict
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional

if TYPE_CHECKING:
    from .core import DLLManager

logger = logging.getLogger(__name__)


class EventEmitter:
    """Centralized event emitter for JadeUI

    Provides a flexible event system with support for:
    - Multiple listeners per event
    - One-time listeners (once)
    - Listener removal
    - Event chaining with decorators

    Example:
        emitter = EventEmitter()

        @emitter.on('my-event')
        def handler(data):
            print(f"Received: {data}")

        emitter.emit('my-event', 'Hello!')
    """

    def __init__(self):
        self._listeners: Dict[str, List[Callable[..., Any]]] = defaultdict(list)
        self._once_listeners: set[Callable[..., Any]] = set()

    def on(self, event: str, callback: Optional[Callable[..., Any]] = None) -> Callable[..., Any]:
        """Register an event listener

        Can be used as a method or decorator:

        As method:
            emitter.on('event', callback)

        As decorator:
            @emitter.on('event')
            def callback():
                pass

        Args:
            event: Event name to listen for
            callback: Function to call when event is emitted

        Returns:
            The callback function (for decorator usage)
        """
        if callback is None:
            # Used as decorator
            def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
                self._listeners[event].append(fn)
                logger.debug(f"Registered listener for event: {event}")
                return fn

            return decorator
        else:
            # Used as method
            self._listeners[event].append(callback)
            logger.debug(f"Registered listener for event: {event}")
            return callback

    def off(self, event: str, callback: Optional[Callable[..., Any]] = None) -> None:
        """Remove an event listener

        Args:
            event: Event name
            callback: The callback function to remove.
                     If None, removes all listeners for the event.
        """
        if callback is None:
            # Remove all listeners for this event
            if event in self._listeners:
                self._listeners[event].clear()
                logger.debug(f"Removed all listeners for event: {event}")
        else:
            # Remove specific listener
            if callback in self._listeners[event]:
                self._listeners[event].remove(callback)
                self._once_listeners.discard(callback)
                logger.debug(f"Removed listener for event: {event}")

    def emit(self, event: str, *args: Any, **kwargs: Any) -> bool:
        """Emit an event to all registered listeners

        Args:
            event: Event name
            *args: Positional arguments to pass to listeners
            **kwargs: Keyword arguments to pass to listeners

        Returns:
            True if any listeners were called
        """
        if event not in self._listeners or not self._listeners[event]:
            return False

        listeners_called = False
        # Copy list to avoid modification during iteration
        for callback in list(self._listeners[event]):
            try:
                callback(*args, **kwargs)
                listeners_called = True

                # Remove if it was a once listener
                if callback in self._once_listeners:
                    self._listeners[event].remove(callback)
                    self._once_listeners.discard(callback)
            except Exception as e:
                logger.error(f"Error in {event} callback: {e}")

        return listeners_called

    def once(self, event: str, callback: Optional[Callable[..., Any]] = None) -> Callable[..., Any]:
        """Register a one-time event listener

        The listener will be removed after the first event emission.

        Args:
            event: Event name
            callback: Function to call once when event is emitted

        Returns:
            The callback function (for decorator usage)
        """
        if callback is None:
            # Used as decorator
            def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
                self._listeners[event].append(fn)
                self._once_listeners.add(fn)
                logger.debug(f"Registered one-time listener for event: {event}")
                return fn

            return decorator
        else:
            # Used as method
            self._listeners[event].append(callback)
            self._once_listeners.add(callback)
            logger.debug(f"Registered one-time listener for event: {event}")
            return callback

    def remove_all_listeners(self, event: Optional[str] = None) -> None:
        """Remove all listeners for an event or all events

        Args:
            event: Specific event to clear listeners for, or None for all events
        """
        if event:
            self._listeners[event].clear()
            logger.debug(f"Cleared all listeners for event: {event}")
        else:
            self._listeners.clear()
            self._once_listeners.clear()
            logger.debug("Cleared all event listeners")

    def listener_count(self, event: str) -> int:
        """Get the number of listeners for an event

        Args:
            event: Event name

        Returns:
            Number of registered listeners
        """
        return len(self._listeners[event])

    def event_names(self) -> list[str]:
        """Get all event names with registered listeners

        Returns:
            List of event names
        """
        return [name for name, listeners in self._listeners.items() if listeners]

    def has_listeners(self, event: str) -> bool:
        """Check if an event has any listeners

        Args:
            event: Event name

        Returns:
            True if event has listeners
        """
        return bool(self._listeners[event])


class GlobalEventManager:
    """Manager for DLL-level global events

    Handles registration and management of global events with the JadeView DLL,
    such as 'app-ready', 'window-all-closed', etc.
    """

    def __init__(self, dll_manager: "DLLManager"):
        self.dll_manager = dll_manager
        self._callbacks: Dict[str, Any] = {}  # Store ctypes callbacks

    def register(self, event: str, callback: Callable) -> None:
        """Register a global event handler with the DLL

        Args:
            event: Event name (e.g., 'app-ready', 'window-all-closed')
            callback: ctypes callback function
        """
        # Store reference to prevent garbage collection
        self._callbacks[event] = callback

        # Register with DLL
        self.dll_manager.jade_on(
            event.encode("utf-8"),
            ctypes.cast(callback, ctypes.c_void_p),
        )
        logger.info(f"Registered global event: {event}")

    def unregister(self, event: str) -> None:
        """Unregister a global event handler

        Args:
            event: Event name
        """
        if event in self._callbacks:
            self.dll_manager.jade_off(event.encode("utf-8"))
            del self._callbacks[event]
            logger.info(f"Unregistered global event: {event}")

    def list_events(self) -> list[str]:
        """Get list of registered global events

        Returns:
            List of event names
        """
        return list(self._callbacks.keys())


# Standard event names
# 参考: https://jade.run/guides/events/event-types
class Events:
    """Standard event name constants

    事件注册方式指南:

    1. 应用生命周期事件 - 通过 JadeUIApp 注册:
        ```python
        from jadeui import JadeUIApp
        app = JadeUIApp()

        @app.on_ready
        def handle_ready():
            print("应用已就绪")
        ```

    2. 窗口事件 - 通过 Window.on() 或专用装饰器注册:
        ```python
        from jadeui import Window

        window = Window(title="示例")

        # 使用专用装饰器（推荐，有类型提示）
        @window.on_resized
        def handle_resize(width: int, height: int):
            print(f"大小: {width}x{height}")

        # 或使用通用 on() 方法
        @window.on("window-moved")
        def handle_move(x: int, y: int):
            print(f"位置: ({x}, {y})")
        ```

    3. IPC 事件 - 通过 IPCManager 注册:
        ```python
        from jadeui.ipc import IPCManager

        ipc = IPCManager()

        @ipc.on("myChannel")
        def handle_message(window_id: int, message: str):
            return "收到"
        ```

    Window 专用装饰器列表:
        - @window.on_resized           -> WINDOW_RESIZED
        - @window.on_moved             -> WINDOW_MOVED
        - @window.on_focused           -> WINDOW_FOCUSED
        - @window.on_blurred           -> WINDOW_BLURRED
        - @window.on_closing           -> WINDOW_CLOSING (可阻止关闭)
        - @window.on_state_changed     -> WINDOW_STATE_CHANGED
        - @window.on_fullscreen_changed -> WINDOW_FULLSCREEN (v1.2+)
        - @window.on_navigate          -> WEBVIEW_WILL_NAVIGATE (可阻止导航)
        - @window.on_page_loaded       -> WEBVIEW_DID_FINISH_LOAD
        - @window.on_title_updated     -> WEBVIEW_PAGE_TITLE_UPDATED
        - @window.on_new_window        -> WEBVIEW_NEW_WINDOW (可阻止新窗口)
        - @window.on_download_started  -> WEBVIEW_DOWNLOAD_STARTED (可阻止下载, v0.3.1+)
        - @window.on_file_dropped      -> FILE_DROP
        - @window.on_js_result         -> JAVASCRIPT_RESULT

    回调返回值说明:
        - 返回 1 或 True 阻止操作
        - 返回 0 或 False/None 允许操作
    """

    # ==================== 应用生命周期事件 ====================
    # 注册方式: @app.on_ready, @app.on_all_windows_closed 等
    APP_READY = "app-ready"  # 应用初始化完成
    WINDOW_ALL_CLOSED = "window-all-closed"  # 所有窗口关闭
    BEFORE_QUIT = "before-quit"  # 应用即将退出

    # ==================== 窗口事件 ====================
    # 注册方式: @window.on("事件名") 或专用装饰器
    WINDOW_CREATED = "window-created"  # 窗口创建完成
    APP_WINDOW_CREATED = "app-window-created"  # 同上，别名
    WINDOW_CLOSED = "window-closed"  # 窗口已关闭
    WINDOW_CLOSING = "window-closing"  # 窗口即将关闭，可返回"1"阻止 -> @window.on_closing
    WINDOW_RESIZED = "window-resized"  # 窗口大小改变 -> @window.on_resized
    WINDOW_STATE_CHANGED = "window-state-changed"  # 最大化/还原状态改变 -> @window.on_state_changed
    WINDOW_FULLSCREEN = "window-fullscreen"  # 全屏状态改变 (v1.2+) -> @window.on_fullscreen_changed
    WINDOW_MOVED = "window-moved"  # 窗口位置改变 -> @window.on_moved
    WINDOW_FOCUSED = "window-focused"  # 窗口获得焦点 -> @window.on_focused
    WINDOW_BLURRED = "window-blurred"  # 窗口失去焦点 -> @window.on_blurred
    WINDOW_DESTROYED = "window-destroyed"  # 窗口销毁
    RESIZED = "resized"  # 窗口大小改变（旧格式，兼容用）

    # ==================== WebView 事件 ====================
    # 注册方式: @window.on("事件名") 或专用装饰器
    WEBVIEW_WILL_NAVIGATE = "webview-will-navigate"  # 即将导航，可返回1阻止 -> @window.on_navigate
    WEBVIEW_DID_START_LOADING = "webview-did-start-loading"  # 开始加载
    WEBVIEW_DID_FINISH_LOAD = "webview-did-finish-load"  # 加载完成 -> @window.on_page_loaded
    WEBVIEW_NEW_WINDOW = "webview-new-window"  # 请求新窗口，可返回1阻止 -> @window.on_new_window
    WEBVIEW_PAGE_TITLE_UPDATED = (
        "webview-page-title-updated"  # 标题更新 -> @window.on_title_updated
    )
    WEBVIEW_PAGE_ICON_UPDATED = "webview-page-icon-updated"  # 图标更新
    FAVICON_UPDATED = "favicon-updated"  # 图标更新（别名）
    JAVASCRIPT_RESULT = "javascript-result"  # JS执行结果 -> @window.on_js_result
    WEBVIEW_DOWNLOAD_STARTED = "webview-download-started"  # 下载开始，可返回"1"阻止 -> @window.on_download_started (v0.3.1+)
    POSTMESSAGE_RECEIVED = "postmessage-received"  # 接收 PostMessage 消息 (v1.0.2+)

    # ==================== 文件事件 ====================
    FILE_DROP = "file-drop"  # 文件拖放到窗口 -> @window.on_file_dropped

    # ==================== 主题事件 ====================
    THEME_CHANGED = "theme-changed"  # 系统主题改变

    # ==================== 其他事件 ====================
    UPDATE_WINDOW_ICON = "update-window-icon"  # 更新窗口图标
    IPC_MESSAGE = "ipc-message"  # IPC 消息（通过 IPCManager 注册）
