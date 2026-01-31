"""
JadeUI Notification API

桌面通知 API，支持 Windows 系统通知。

JadeView 1.3.0+
参考文档: https://jade.run/guides/notification

注意：
    - 仅支持 Windows 平台（Windows 10 或更高版本）
    - 首次发送通知时会自动注册应用
    - 最多支持两个按钮
    - 图标路径必须是绝对路径

Example:
    from jadeui import Notification
    from jadeui.events import Events

    # 配置应用信息（可选，有默认值）
    Notification.config(app_name="我的应用", icon="C:/path/to/icon.ico")

    # 监听按钮点击事件（使用 Events 常量）
    @Notification.on(Events.NOTIFICATION_ACTION)
    def on_action(data):
        print(f"用户点击了: {data}")

    @Notification.on(Events.NOTIFICATION_DISMISSED)
    def on_dismissed(data):
        print("通知被关闭")

    # 简单通知
    Notification.show("新消息", "您有一条新的系统通知")

    # 带按钮的通知（action 参数用于识别通知）
    Notification.with_buttons(
        "下载完成",
        "文件已保存到下载目录",
        "打开",
        "忽略",
        action="download_123"
    )
"""

from __future__ import annotations

import ctypes
import json
import logging
from typing import Any, Callable, Dict, List, Optional, TypeVar

from .core import DLLManager
from .core.types import GenericWindowEventCallback, NotificationParams

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


class Notification:
    """桌面通知 API

    提供 Windows 桌面通知功能。
    首次发送通知时会自动注册应用。

    JadeView 1.3.0+
    参考: https://jade.run/guides/notification

    Events:
        - 'action': 用户点击通知按钮时触发（仅带按钮的通知）
        - 'shown': 通知成功显示时触发
        - 'dismissed': 通知被关闭时触发
        - 'failed': 通知显示失败时触发

    Example:
        from jadeui import Notification

        # 简单通知
        Notification.show("标题", "内容")

        # 带按钮的通知
        Notification.with_buttons("标题", "内容", "确定", "取消", action="my_action")
    """

    # 类级别状态
    _registered: bool = False
    _app_name: str = "JadeUI App"
    _app_icon: Optional[str] = None

    # 事件处理（使用完整的 DLL 事件名称）
    _event_handlers: Dict[str, List[Callable]] = {
        "notification-action": [],
        "notification-shown": [],
        "notification-dismissed": [],
        "notification-failed": [],
    }
    _callbacks_registered: bool = False
    _callback_refs: List[Any] = []  # 防止回调被垃圾回收

    # DLL 事件名称列表
    _EVENTS = [
        "notification-action",
        "notification-shown",
        "notification-dismissed",
        "notification-failed",
    ]

    @classmethod
    def config(
        cls,
        app_name: Optional[str] = None,
        icon: Optional[str] = None,
    ) -> None:
        """配置通知应用信息

        可在发送通知前调用此方法配置应用信息。
        如果不调用，将使用默认值。

        Args:
            app_name: 应用显示名称（默认 "JadeUI App"）
            icon: 应用图标路径（绝对路径，可选）

        Example:
            Notification.config(
                app_name="我的应用",
                icon="C:/path/to/icon.ico"
            )
        """
        if app_name:
            cls._app_name = app_name
        if icon:
            cls._app_icon = icon

        # 如果已注册，重新注册以更新信息
        if cls._registered:
            cls._do_register()

    @classmethod
    def on(cls, event: str) -> Callable[[F], F]:
        """注册通知事件监听器

        支持的事件（使用 Events 常量或字符串）:
            - Events.NOTIFICATION_ACTION / 'notification-action': 用户点击通知按钮
            - Events.NOTIFICATION_SHOWN / 'notification-shown': 通知成功显示
            - Events.NOTIFICATION_DISMISSED / 'notification-dismissed': 通知被关闭
            - Events.NOTIFICATION_FAILED / 'notification-failed': 通知显示失败

        Args:
            event: 事件名称

        Returns:
            装饰器函数

        Example:
            from jadeui import Notification, Events

            @Notification.on(Events.NOTIFICATION_ACTION)
            def on_action(data):
                # data = {
                #     "action": "action_0",      # 按钮索引
                #     "title": "确定",           # 按钮文本
                #     "arguments": "my_action"   # 你传入的 action 参数
                # }
                print(f"按钮点击: {data}")

            @Notification.on(Events.NOTIFICATION_DISMISSED)
            def on_dismissed(data):
                print("通知被关闭")
        """
        if event not in cls._event_handlers:
            raise ValueError(f"未知事件: {event}，支持的事件: {cls._EVENTS}")

        def decorator(func: F) -> F:
            cls._event_handlers[event].append(func)
            return func

        return decorator

    @classmethod
    def _ensure_initialized(cls) -> bool:
        """确保通知系统已初始化（自动注册）"""
        dll = DLLManager()
        if not dll.is_loaded():
            dll.load()

        # 注册应用
        if not cls._registered:
            if not cls._do_register():
                return False

        # 注册事件回调
        if not cls._callbacks_registered:
            cls._register_event_callbacks()

        return True

    @classmethod
    def _do_register(cls) -> bool:
        """执行注册"""
        dll = DLLManager()

        if not dll.has_function("set_notification_app_registry"):
            logger.warning("set_notification_app_registry 不可用，需要 JadeView 1.3.0+")
            return False

        result = dll.set_notification_app_registry(
            cls._app_name.encode("utf-8"),
            cls._app_icon.encode("utf-8") if cls._app_icon else None,
        )

        if result == 1:
            cls._registered = True
            logger.debug(f"通知应用已注册: {cls._app_name}")
            return True
        else:
            logger.error(f"通知应用注册失败: {cls._app_name}")
            return False

    @classmethod
    def _register_event_callbacks(cls) -> None:
        """注册 DLL 事件回调"""
        dll = DLLManager()

        if not dll.has_function("jade_on"):
            logger.warning("jade_on 不可用")
            return

        for event_name in cls._EVENTS:
            # 创建闭包捕获 event_name
            def make_callback(name: str):
                @GenericWindowEventCallback
                def callback(window_id: int, data: bytes):
                    cls._dispatch_event(name, data)

                return callback

            cb = make_callback(event_name)
            cls._callback_refs.append(cb)

            dll.jade_on(
                event_name.encode("utf-8"),
                ctypes.cast(cb, ctypes.c_void_p),
            )
            logger.debug(f"已注册通知事件: {event_name}")

        cls._callbacks_registered = True

    @classmethod
    def _dispatch_event(cls, event: str, data: bytes) -> None:
        """分发事件到处理器"""
        handlers = cls._event_handlers.get(event, [])
        if not handlers:
            return

        # 解析数据
        try:
            data_str = data.decode("utf-8") if data else "{}"
            data_dict = json.loads(data_str) if data_str else {}
        except (UnicodeDecodeError, json.JSONDecodeError):
            data_dict = {"raw": data}

        # 调用所有处理器
        for handler in handlers:
            try:
                handler(data_dict)
            except Exception as e:
                logger.error(f"通知事件处理器异常: {e}")

    @classmethod
    def is_registered(cls) -> bool:
        """检查是否已注册通知应用

        Returns:
            已注册返回 True
        """
        return cls._registered

    @classmethod
    def _send(
        cls,
        summary: str,
        body: Optional[str] = None,
        icon: Optional[str] = None,
        timeout: int = 0,
        button1: Optional[str] = None,
        button2: Optional[str] = None,
        text3: Optional[str] = None,
        action: Optional[str] = None,
    ) -> bool:
        """内部方法：发送通知到 DLL"""
        if not summary:
            logger.error("通知标题 (summary) 不能为空")
            return False

        # 确保已初始化
        if not cls._ensure_initialized():
            return False

        dll = DLLManager()

        if not dll.has_function("show_notification"):
            logger.warning("show_notification 不可用，需要 JadeView 1.3.0+")
            return False

        # 使用传入的 icon 或默认 icon
        final_icon = icon or cls._app_icon

        # 创建参数结构体
        params = NotificationParams(
            summary=summary.encode("utf-8"),
            body=body.encode("utf-8") if body else None,
            icon=final_icon.encode("utf-8") if final_icon else None,
            timeout=timeout,
            button1=button1.encode("utf-8") if button1 else None,
            button2=button2.encode("utf-8") if button2 else None,
            text3=text3.encode("utf-8") if text3 else None,
            action=action.encode("utf-8") if action else None,
        )

        logger.debug(
            f"调用 show_notification: summary={summary}, body={body}, "
            f"button1={button1}, button2={button2}, action={action}"
        )

        # 调用 DLL 函数
        try:
            result = dll.show_notification(ctypes.byref(params))
            logger.debug(f"show_notification 返回: {result}")
        except Exception as e:
            logger.error(f"show_notification 异常: {e}")
            return False

        if result == 1:
            logger.debug(f"通知已显示: {summary}")
            return True
        else:
            logger.error(f"通知显示失败: {summary}")
            return False

    # ==================== 公开 API ====================

    @classmethod
    def show(
        cls,
        title: str,
        body: Optional[str] = None,
        icon: Optional[str] = None,
        timeout: int = 0,
    ) -> bool:
        """显示简单通知（无按钮）

        首次调用时会自动注册应用。

        Args:
            title: 通知标题（必填）
            body: 通知内容（可选）
            icon: 图标路径（绝对路径，可选，覆盖 config 设置）
            timeout: 超时时间（毫秒，<= 0 时使用默认超时）

        Returns:
            显示成功返回 True

        Example:
            Notification.show("提示", "操作已完成")
            Notification.show("下载中", "正在下载文件...", timeout=5000)
        """
        return cls._send(
            summary=title,
            body=body,
            icon=icon,
            timeout=timeout,
        )

    @classmethod
    def with_buttons(
        cls,
        title: str,
        body: str,
        button1: str,
        button2: Optional[str] = None,
        icon: Optional[str] = None,
        timeout: int = 0,
        action: Optional[str] = None,
    ) -> bool:
        """显示带按钮的通知

        用户点击按钮时会触发 'action' 事件，需要使用 @Notification.on("action")
        装饰器来监听并处理按钮点击。

        Args:
            title: 通知标题
            body: 通知内容
            button1: 第一个按钮文本（必填）
            button2: 第二个按钮文本（可选）
            icon: 图标路径（绝对路径，可选）
            timeout: 超时时间（毫秒，<= 0 时使用默认超时）
            action: 动作标识符，用于在事件回调中识别此通知。
                    点击按钮后，此值会以 'arguments' 字段返回。

        Returns:
            显示成功返回 True

        事件数据格式:
            用户点击按钮后，@Notification.on("action") 回调会收到以下数据：
            {
                "action": "action_0",      # 按钮索引 (action_0=第1个, action_1=第2个)
                "title": "打开",           # 按钮文本
                "arguments": "download_123" # 你传入的 action 参数值
            }

        Example:
            # 1. 先注册事件监听器
            @Notification.on("action")
            def on_action(data):
                action_id = data.get("arguments")  # 获取你传入的 action
                button = data.get("action")        # 获取按钮索引

                if action_id == "download_123":
                    if button == "action_0":
                        print("用户点击了「打开」")
                    elif button == "action_1":
                        print("用户点击了「忽略」")

            # 2. 发送通知
            Notification.with_buttons(
                "下载完成",
                "video.mp4 已下载",
                "打开",       # → 点击后 action="action_0"
                "忽略",       # → 点击后 action="action_1"
                action="download_123"  # → 返回在 arguments 中
            )
        """
        return cls._send(
            summary=title,
            body=body,
            icon=icon,
            timeout=timeout,
            button1=button1,
            button2=button2,
            action=action,
        )

    # ==================== 便捷方法 ====================

    @classmethod
    def info(cls, title: str, body: str, icon: Optional[str] = None) -> bool:
        """显示信息通知"""
        return cls.show(title, body, icon=icon)

    @classmethod
    def success(cls, title: str, body: str, icon: Optional[str] = None) -> bool:
        """显示成功通知"""
        return cls.show(title, body, icon=icon)

    @classmethod
    def warning(cls, title: str, body: str, icon: Optional[str] = None) -> bool:
        """显示警告通知"""
        return cls.show(title, body, icon=icon)

    @classmethod
    def error(cls, title: str, body: str, icon: Optional[str] = None) -> bool:
        """显示错误通知"""
        return cls.show(title, body, icon=icon)

    # ==================== 兼容性方法 ====================

    @classmethod
    def register(cls, app_name: str, icon_path: Optional[str] = None) -> bool:
        """注册通知应用（兼容旧 API）

        注意：现在推荐使用 config() 方法配置，show() 会自动注册。
        此方法保留用于向后兼容。
        """
        cls._app_name = app_name
        if icon_path:
            cls._app_icon = icon_path
        return cls._do_register()
