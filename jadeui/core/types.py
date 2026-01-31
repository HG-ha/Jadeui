"""
JadeUI Type Definitions

ctypes structures and callback type definitions for JadeView DLL interface.

JadeView 1.0+ 重要变更:
回调函数返回 const char* 类型，需使用 jade_text_create 创建安全指针。
- 返回 NULL (None): 允许操作
- 返回 "1": 阻止操作
- 返回其他文本: IPC 响应数据
"""

import ctypes

# ==================== Callback Function Types ====================
# JadeView: 回调类型定义
# 使用 WINFUNCTYPE (stdcall) - JadeView DLL 使用 stdcall 调用约定
import sys
from typing import Callable, Optional

if sys.platform == "win32":
    _FUNCTYPE = ctypes.WINFUNCTYPE
else:
    _FUNCTYPE = ctypes.CFUNCTYPE

# 事件回调: window_id, event_data -> void
# 用于通过 jade_on 注册的所有事件 (app-ready, load, file-drop 等)
GenericWindowEventCallback = _FUNCTYPE(
    None,  # 返回 void
    ctypes.c_uint,
    ctypes.c_char_p,
)

# IPC 回调 (jade.invoke): window_id, message -> void*
# 返回 jade_text_create 创建的指针，或 0/NULL 表示无返回
IpcCallback = _FUNCTYPE(
    ctypes.c_void_p,  # 返回 void*
    ctypes.c_uint,
    ctypes.c_char_p,
)

# 应用就绪回调: 与通用事件回调相同
AppReadyCallback = GenericWindowEventCallback

# 所有窗口关闭回调: 与通用事件回调相同
WindowAllClosedCallback = GenericWindowEventCallback

# file-drop 事件回调: 与通用事件回调相同
FileDropCallback = GenericWindowEventCallback

# ==================== Legacy Callback Types ====================

WindowEventCallback = ctypes.CFUNCTYPE(
    ctypes.c_int, ctypes.c_uint32, ctypes.c_char_p, ctypes.c_char_p
)
PageLoadCallback = ctypes.CFUNCTYPE(None, ctypes.c_uint32, ctypes.c_char_p, ctypes.c_char_p)


# Data structures
class RGBA(ctypes.Structure):
    """RGBA color structure"""

    _fields_ = [
        ("r", ctypes.c_int),
        ("g", ctypes.c_int),
        ("b", ctypes.c_int),
        ("a", ctypes.c_int),
    ]

    def __init__(self, r: int = 255, g: int = 255, b: int = 255, a: int = 255):
        super().__init__(r, g, b, a)

    def __repr__(self) -> str:
        return f"RGBA(r={self.r}, g={self.g}, b={self.b}, a={self.a})"


class WebViewWindowOptions(ctypes.Structure):
    """WebView window configuration options

    根据 JadeView 1.2.0 文档更新:
    https://jade.run/guides/window-api#webviewwindowoptions-结构体
    """

    _fields_ = [
        ("title", ctypes.c_char_p),
        ("width", ctypes.c_int),
        ("height", ctypes.c_int),
        ("resizable", ctypes.c_int),
        ("remove_titlebar", ctypes.c_int),
        ("transparent", ctypes.c_int),
        ("background_color", RGBA),
        ("always_on_top", ctypes.c_int),
        ("no_center", ctypes.c_int),
        ("theme", ctypes.c_char_p),
        ("maximized", ctypes.c_int),
        ("maximizable", ctypes.c_int),
        ("minimizable", ctypes.c_int),
        ("x", ctypes.c_int),
        ("y", ctypes.c_int),
        ("min_width", ctypes.c_int),
        ("min_height", ctypes.c_int),
        ("max_width", ctypes.c_int),
        ("max_height", ctypes.c_int),
        ("fullscreen", ctypes.c_int),
        ("focus", ctypes.c_int),
        ("hide_window", ctypes.c_int),
        ("use_page_icon", ctypes.c_int),
        ("borderless", ctypes.c_int),  # JadeView 0.2.1+: 无边框模式
        ("content_protection", ctypes.c_int),  # JadeView 1.1+: 内容保护（禁止截图）
    ]

    def __init__(
        self,
        title: bytes = b"Window",
        width: int = 800,
        height: int = 600,
        resizable: bool = True,
        remove_titlebar: bool = False,
        transparent: bool = False,
        background_color: Optional[RGBA] = None,
        always_on_top: bool = False,
        no_center: bool = False,
        theme: bytes = b"System",
        maximized: bool = False,
        maximizable: bool = True,
        minimizable: bool = True,
        x: int = -1,
        y: int = -1,
        min_width: int = 0,
        min_height: int = 0,
        max_width: int = 0,
        max_height: int = 0,
        fullscreen: bool = False,
        focus: bool = True,
        hide_window: bool = False,
        use_page_icon: bool = True,
        borderless: bool = False,
        content_protection: bool = False,
    ):
        if background_color is None:
            background_color = RGBA(255, 255, 255, 255)

        super().__init__(
            title,
            width,
            height,
            int(resizable),
            int(remove_titlebar),
            int(transparent),
            background_color,
            int(always_on_top),
            int(no_center),
            theme,
            int(maximized),
            int(maximizable),
            int(minimizable),
            x,
            y,
            min_width,
            min_height,
            max_width,
            max_height,
            int(fullscreen),
            int(focus),
            int(hide_window),
            int(use_page_icon),
            int(borderless),
            int(content_protection),
        )


class WebViewSettings(ctypes.Structure):
    """WebView behavior settings

    根据 JadeView 文档更新:
    https://jade.run/guides/window-api#webviewsettings-结构体
    """

    _fields_ = [
        ("autoplay", ctypes.c_int),
        ("background_throttling", ctypes.c_int),
        ("disable_right_click", ctypes.c_int),
        ("ua", ctypes.c_char_p),
        ("preload_js", ctypes.c_char_p),
        ("allow_fullscreen", ctypes.c_int),  # JadeView 0.2.1+: 控制是否允许页面全屏
        ("postmessage_whitelist", ctypes.c_char_p),  # JadeView 1.0.2+: PostMessage 白名单
    ]

    def __init__(
        self,
        autoplay: bool = False,
        background_throttling: bool = False,
        disable_right_click: bool = False,
        ua: Optional[bytes] = None,
        preload_js: Optional[bytes] = None,
        allow_fullscreen: bool = True,  # 默认允许全屏
        postmessage_whitelist: Optional[bytes] = None,  # PostMessage 白名单
    ):
        super().__init__(
            int(autoplay),
            int(background_throttling),
            int(disable_right_click),
            ua,
            preload_js,
            int(allow_fullscreen),
            postmessage_whitelist,
        )


# ==================== Dialog Params (v1.3.0+) ====================
# 根据官方文档: https://jade.run/guides/dialog-api#结构体定义

# 对话框回调函数类型: void (*callback)(const char*)
DialogCallback = _FUNCTYPE(None, ctypes.c_char_p)


class OpenDialogParams(ctypes.Structure):
    """打开文件对话框参数结构体

    用于 jade_dialog_show_open_dialog 函数。
    类似 Electron 的 dialog.showOpenDialog API。

    JadeView 1.3.0+
    参考: https://jade.run/guides/dialog-api#jade_dialog_show_open_dialog
    """

    _fields_ = [
        ("window_id", ctypes.c_uint32),  # 窗口 ID
        ("title", ctypes.c_char_p),  # 对话框标题
        ("default_path", ctypes.c_char_p),  # 默认打开路径
        ("button_label", ctypes.c_char_p),  # 确认按钮的自定义标签
        ("filters", ctypes.c_char_p),  # 文件过滤器（JSON格式）
        (
            "properties",
            ctypes.c_char_p,
        ),  # 对话框特性（逗号分隔）: openFile,openDirectory,multiSelections,showHiddenFiles
        ("blocking", ctypes.c_int),  # 是否阻塞进程
        ("callback", ctypes.c_void_p),  # 回调函数: void (*callback)(const char*)
    ]

    def __init__(
        self,
        window_id: int = 0,
        title: Optional[bytes] = None,
        default_path: Optional[bytes] = None,
        button_label: Optional[bytes] = None,
        filters: Optional[bytes] = None,
        properties: Optional[bytes] = None,
        blocking: int = 1,
        callback: Optional[ctypes.c_void_p] = None,
    ):
        super().__init__(
            window_id,
            title,
            default_path,
            button_label,
            filters,
            properties,
            blocking,
            callback,
        )


class SaveDialogParams(ctypes.Structure):
    """保存文件对话框参数结构体

    用于 jade_dialog_show_save_dialog 函数。
    类似 Electron 的 dialog.showSaveDialog API。

    JadeView 1.3.0+
    参考: https://jade.run/guides/dialog-api#jade_dialog_show_save_dialog
    """

    _fields_ = [
        ("window_id", ctypes.c_uint32),  # 窗口 ID
        ("title", ctypes.c_char_p),  # 对话框标题
        ("default_path", ctypes.c_char_p),  # 默认保存路径
        ("button_label", ctypes.c_char_p),  # 确认按钮的自定义标签
        ("filters", ctypes.c_char_p),  # 文件过滤器（JSON格式）
        ("blocking", ctypes.c_int),  # 是否阻塞进程
        ("callback", ctypes.c_void_p),  # 回调函数: void (*callback)(const char*)
    ]

    def __init__(
        self,
        window_id: int = 0,
        title: Optional[bytes] = None,
        default_path: Optional[bytes] = None,
        button_label: Optional[bytes] = None,
        filters: Optional[bytes] = None,
        blocking: int = 1,
        callback: Optional[ctypes.c_void_p] = None,
    ):
        super().__init__(
            window_id,
            title,
            default_path,
            button_label,
            filters,
            blocking,
            callback,
        )


class MessageBoxParams(ctypes.Structure):
    """消息框参数结构体

    用于 jade_dialog_show_message_box 函数。
    类似 Electron 的 dialog.showMessageBox API。

    JadeView 1.3.0+
    参考: https://jade.run/guides/dialog-api#jade_dialog_show_message_box
    """

    _fields_ = [
        ("window_id", ctypes.c_uint32),  # 窗口 ID
        ("title", ctypes.c_char_p),  # 消息框标题
        ("message", ctypes.c_char_p),  # 消息框内容
        ("detail", ctypes.c_char_p),  # 详细信息
        ("buttons", ctypes.c_char_p),  # 按钮列表（使用|分隔，如"确定|取消"）
        ("default_id", ctypes.c_int),  # 默认选中的按钮索引
        ("cancel_id", ctypes.c_int),  # 取消按钮的索引
        ("type_", ctypes.c_char_p),  # 消息框类型: "none", "info", "error", "warning", "question"
        ("blocking", ctypes.c_int),  # 是否阻塞进程
        ("callback", ctypes.c_void_p),  # 回调函数: void (*callback)(const char*)
    ]

    def __init__(
        self,
        window_id: int = 0,
        title: Optional[bytes] = None,
        message: Optional[bytes] = None,
        detail: Optional[bytes] = None,
        buttons: Optional[bytes] = None,
        default_id: int = 0,
        cancel_id: int = -1,
        type_: Optional[bytes] = None,
        blocking: int = 1,
        callback: Optional[ctypes.c_void_p] = None,
    ):
        super().__init__(
            window_id,
            title,
            message,
            detail,
            buttons,
            default_id,
            cancel_id,
            type_,
            blocking,
            callback,
        )


# ==================== Notification Params (v1.3.0+) ====================
# 根据官方文档: https://jade.run/guides/notification


class NotificationParams(ctypes.Structure):
    """通知参数结构体

    用于 show_notification 函数。
    支持 Windows 桌面通知。

    JadeView 1.3.0+
    参考: https://jade.run/guides/notification#数据结构
    """

    _fields_ = [
        ("summary", ctypes.c_char_p),  # 通知标题（必填字段，不能为空）
        ("body", ctypes.c_char_p),  # 通知内容（可选）
        ("icon", ctypes.c_char_p),  # 图标路径（绝对路径，可选）
        ("timeout", ctypes.c_int),  # 超时时间（毫秒，<= 0 时使用默认超时）
        ("button1", ctypes.c_char_p),  # 第一个按钮文本（可选）
        ("button2", ctypes.c_char_p),  # 第二个按钮文本（可选）
        ("text3", ctypes.c_char_p),  # 第三行文本（可选）
        ("action", ctypes.c_char_p),  # 动作参数（可选，会以 arguments 传参）
    ]

    def __init__(
        self,
        summary: Optional[bytes] = None,
        body: Optional[bytes] = None,
        icon: Optional[bytes] = None,
        timeout: int = 0,
        button1: Optional[bytes] = None,
        button2: Optional[bytes] = None,
        text3: Optional[bytes] = None,
        action: Optional[bytes] = None,
    ):
        super().__init__(
            summary,
            body,
            icon,
            timeout,
            button1,
            button2,
            text3,
            action,
        )


# Python callback types for user code
WindowEventHandler = Callable[[int, str, str], int]
PageLoadHandler = Callable[[int, str, str], None]
FileDropHandler = Callable[[int, str, str, float, float], None]
AppReadyHandler = Callable[[int, str], int]
IPCHandler = Callable[[int, str], int]
WindowAllClosedHandler = Callable[[], int]
