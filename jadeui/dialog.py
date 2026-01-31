"""
JadeUI Dialog API

对话框 API，提供文件选择、保存和消息框功能。
类似 Electron 的 dialog 模块。

JadeView 1.3.0+
参考文档: https://jade.run/guides/dialog-api

同时支持前端 JavaScript 调用和 Python 后端调用：

Frontend Example (JavaScript):
    // 打开文件对话框
    const result = await jade.dialog.showOpenDialog({
        title: '选择文件',
        filters: [
            { name: '图片', extensions: ['png', 'jpg'] },
            { name: '所有文件', extensions: ['*'] }
        ],
        properties: ['openFile', 'multiSelections']
    });

    // 消息框
    const response = await jade.dialog.showMessageBox({
        title: '确认',
        message: '是否删除？',
        type: 'warning',
        buttons: ['删除', '取消']
    });

Python Example:
    from jadeui import Dialog

    # 打开文件对话框（阻塞模式）
    Dialog.show_open_dialog(
        window_id=1,
        title="选择文件",
        filters=[{"name": "图片", "extensions": ["png", "jpg"]}],
        properties=["openFile", "multiSelections"],
        blocking=True
    )

    # 消息框
    Dialog.show_message_box(
        window_id=1,
        title="确认",
        message="是否删除文件？",
        buttons=["删除", "取消"],
        type_="warning"
    )
"""

from __future__ import annotations

import ctypes
import json
import logging
from typing import Any, Callable, Dict, List, Optional, Union

from .core import DLLManager
from .core.types import (
    DialogCallback,
    MessageBoxParams,
    OpenDialogParams,
    SaveDialogParams,
)

logger = logging.getLogger(__name__)


class Dialog:
    """对话框 API

    提供文件选择、保存和消息框功能。
    所有方法都是静态方法，可以直接调用。

    JadeView 1.3.0+
    参考: https://jade.run/guides/dialog-api
    """

    # 保存回调引用，防止被垃圾回收
    _callbacks: List[Any] = []

    @staticmethod
    def _format_filters_json(filters: Optional[List[Dict[str, Any]]]) -> Optional[bytes]:
        """格式化文件过滤器为 JSON 格式

        Args:
            filters: 过滤器列表，每项为 {"name": "名称", "extensions": ["ext1", "ext2"]}

        Returns:
            JSON 格式的过滤器字符串
        """
        if not filters:
            return None
        return json.dumps(filters, ensure_ascii=False).encode("utf-8")

    @staticmethod
    def _format_properties(properties: Optional[List[str]]) -> Optional[bytes]:
        """格式化对话框属性为逗号分隔字符串

        Args:
            properties: 属性列表，如 ["openFile", "multiSelections"]

        Returns:
            逗号分隔的属性字符串
        """
        if not properties:
            return None
        return ",".join(properties).encode("utf-8")

    @staticmethod
    def show_open_dialog(
        window_id: int = 0,
        title: Optional[str] = None,
        default_path: Optional[str] = None,
        button_label: Optional[str] = None,
        filters: Optional[List[Dict[str, Any]]] = None,
        properties: Optional[List[str]] = None,
        blocking: bool = True,
        callback: Optional[Callable[[str], None]] = None,
    ) -> int:
        """显示打开文件对话框

        Args:
            window_id: 父窗口 ID
            title: 对话框标题
            default_path: 默认打开路径
            button_label: 确认按钮的自定义标签
            filters: 文件过滤器列表，JSON 格式
                    如 [{"name": "图片", "extensions": ["png", "jpg"]}]
            properties: 对话框属性列表
                    可选值: "openFile", "openDirectory", "multiSelections", "showHiddenFiles"
            blocking: 是否阻塞进程（默认 True）
            callback: 回调函数，非阻塞模式下使用

        Returns:
            1 表示成功，0 表示失败

        Example:
            # 阻塞模式
            Dialog.show_open_dialog(
                window_id=1,
                title="选择图片",
                filters=[{"name": "图片", "extensions": ["png", "jpg", "gif"]}],
                properties=["openFile", "multiSelections"]
            )

            # 非阻塞模式 + 回调
            def on_result(result):
                print(f"选中: {result}")

            Dialog.show_open_dialog(
                window_id=1,
                title="选择文件",
                properties=["openFile"],
                blocking=False,
                callback=on_result
            )
        """
        dll = DLLManager()
        if not dll.is_loaded():
            dll.load()

        if not dll.has_function("jade_dialog_show_open_dialog"):
            logger.warning("jade_dialog_show_open_dialog 不可用，需要 JadeView 1.3.0+")
            return 0

        # 处理回调
        cb_ptr = None
        if callback and not blocking:

            @DialogCallback
            def c_callback(result: bytes):
                try:
                    result_str = result.decode("utf-8") if result else ""
                    callback(result_str)
                except Exception as e:
                    logger.error(f"Dialog callback error: {e}")

            Dialog._callbacks.append(c_callback)
            cb_ptr = ctypes.cast(c_callback, ctypes.c_void_p)

        # 创建参数结构体
        params = OpenDialogParams(
            window_id=window_id,
            title=title.encode("utf-8") if title else None,
            default_path=default_path.encode("utf-8") if default_path else None,
            button_label=button_label.encode("utf-8") if button_label else None,
            filters=Dialog._format_filters_json(filters),
            properties=Dialog._format_properties(properties),
            blocking=1 if blocking else 0,
            callback=cb_ptr,
        )

        # 调用 DLL 函数
        result = dll.jade_dialog_show_open_dialog(ctypes.byref(params))
        return result

    @staticmethod
    def show_save_dialog(
        window_id: int = 0,
        title: Optional[str] = None,
        default_path: Optional[str] = None,
        button_label: Optional[str] = None,
        filters: Optional[List[Dict[str, Any]]] = None,
        blocking: bool = True,
        callback: Optional[Callable[[str], None]] = None,
    ) -> int:
        """显示保存文件对话框

        Args:
            window_id: 父窗口 ID
            title: 对话框标题
            default_path: 默认保存路径/文件名
            button_label: 确认按钮的自定义标签
            filters: 文件过滤器列表，JSON 格式
            blocking: 是否阻塞进程（默认 True）
            callback: 回调函数，非阻塞模式下使用

        Returns:
            1 表示成功，0 表示失败

        Example:
            Dialog.show_save_dialog(
                window_id=1,
                title="保存文档",
                default_path="document.txt",
                filters=[{"name": "文本文件", "extensions": ["txt"]}]
            )
        """
        dll = DLLManager()
        if not dll.is_loaded():
            dll.load()

        if not dll.has_function("jade_dialog_show_save_dialog"):
            logger.warning("jade_dialog_show_save_dialog 不可用，需要 JadeView 1.3.0+")
            return 0

        # 处理回调
        cb_ptr = None
        if callback and not blocking:

            @DialogCallback
            def c_callback(result: bytes):
                try:
                    result_str = result.decode("utf-8") if result else ""
                    callback(result_str)
                except Exception as e:
                    logger.error(f"Dialog callback error: {e}")

            Dialog._callbacks.append(c_callback)
            cb_ptr = ctypes.cast(c_callback, ctypes.c_void_p)

        # 创建参数结构体
        params = SaveDialogParams(
            window_id=window_id,
            title=title.encode("utf-8") if title else None,
            default_path=default_path.encode("utf-8") if default_path else None,
            button_label=button_label.encode("utf-8") if button_label else None,
            filters=Dialog._format_filters_json(filters),
            blocking=1 if blocking else 0,
            callback=cb_ptr,
        )

        # 调用 DLL 函数
        result = dll.jade_dialog_show_save_dialog(ctypes.byref(params))
        return result

    @staticmethod
    def show_message_box(
        window_id: int = 0,
        title: Optional[str] = None,
        message: Optional[str] = None,
        detail: Optional[str] = None,
        buttons: Optional[List[str]] = None,
        default_id: int = 0,
        cancel_id: int = -1,
        type_: str = "none",
        blocking: bool = True,
        callback: Optional[Callable[[str], None]] = None,
    ) -> int:
        """显示消息框

        Args:
            window_id: 父窗口 ID
            title: 消息框标题
            message: 消息内容
            detail: 详细信息（可选）
            buttons: 按钮文本列表，如 ["确定", "取消"]
            default_id: 默认选中的按钮索引
            cancel_id: 取消按钮的索引（按 ESC 时触发）
            type_: 消息类型: "none", "info", "error", "warning", "question"
            blocking: 是否阻塞进程（默认 True）
            callback: 回调函数，非阻塞模式下使用

        Returns:
            1 表示成功，0 表示失败

        Example:
            Dialog.show_message_box(
                window_id=1,
                title="确认删除",
                message="确定要删除这个文件吗？",
                detail="此操作不可撤销",
                type_="warning",
                buttons=["删除", "取消"],
                default_id=1,
                cancel_id=1
            )
        """
        dll = DLLManager()
        if not dll.is_loaded():
            dll.load()

        if not dll.has_function("jade_dialog_show_message_box"):
            logger.warning("jade_dialog_show_message_box 不可用，需要 JadeView 1.3.0+")
            return 0

        # 处理回调
        cb_ptr = None
        if callback and not blocking:

            @DialogCallback
            def c_callback(result: bytes):
                try:
                    result_str = result.decode("utf-8") if result else ""
                    callback(result_str)
                except Exception as e:
                    logger.error(f"Dialog callback error: {e}")

            Dialog._callbacks.append(c_callback)
            cb_ptr = ctypes.cast(c_callback, ctypes.c_void_p)

        # 格式化按钮（使用 | 分隔）
        buttons_str = "|".join(buttons) if buttons else "确定"

        # 创建参数结构体
        params = MessageBoxParams(
            window_id=window_id,
            title=title.encode("utf-8") if title else None,
            message=message.encode("utf-8") if message else None,
            detail=detail.encode("utf-8") if detail else None,
            buttons=buttons_str.encode("utf-8"),
            default_id=default_id,
            cancel_id=cancel_id,
            type_=type_.encode("utf-8") if type_ else b"none",
            blocking=1 if blocking else 0,
            callback=cb_ptr,
        )

        # 调用 DLL 函数
        result = dll.jade_dialog_show_message_box(ctypes.byref(params))
        return result

    @staticmethod
    def show_error_box(
        window_id: int = 0,
        title: str = "错误",
        content: str = "",
    ) -> int:
        """显示错误框

        简化的错误消息框，只有标题和内容。

        Args:
            window_id: 父窗口 ID
            title: 错误标题
            content: 错误内容

        Returns:
            1 表示成功，0 表示失败

        Example:
            Dialog.show_error_box(1, "错误", "文件读取失败！")
        """
        dll = DLLManager()
        if not dll.is_loaded():
            dll.load()

        if not dll.has_function("jade_dialog_show_error_box"):
            logger.warning("jade_dialog_show_error_box 不可用，需要 JadeView 1.3.0+")
            return 0

        result = dll.jade_dialog_show_error_box(
            window_id,
            title.encode("utf-8"),
            content.encode("utf-8"),
        )
        return result

    # ==================== 便捷方法 ====================

    @staticmethod
    def confirm(
        message: str,
        title: str = "确认",
        ok_label: str = "确定",
        cancel_label: str = "取消",
        window_id: int = 0,
    ) -> int:
        """显示确认对话框

        Args:
            message: 消息内容
            title: 对话框标题
            ok_label: 确认按钮文本
            cancel_label: 取消按钮文本
            window_id: 父窗口 ID

        Returns:
            1 表示成功调用

        Example:
            Dialog.confirm("确定要退出吗？")
        """
        return Dialog.show_message_box(
            window_id=window_id,
            title=title,
            message=message,
            type_="question",
            buttons=[ok_label, cancel_label],
            default_id=0,
            cancel_id=1,
        )

    @staticmethod
    def alert(
        message: str,
        title: str = "提示",
        type_: str = "info",
        window_id: int = 0,
    ) -> int:
        """显示提示对话框

        Args:
            message: 消息内容
            title: 对话框标题
            type_: 消息类型 ("info", "warning", "error")
            window_id: 父窗口 ID

        Returns:
            1 表示成功调用

        Example:
            Dialog.alert("操作成功！")
            Dialog.alert("请注意！", type_="warning")
        """
        return Dialog.show_message_box(
            window_id=window_id,
            title=title,
            message=message,
            type_=type_,
            buttons=["确定"],
        )

    @staticmethod
    def error(message: str, title: str = "错误", window_id: int = 0) -> int:
        """显示错误对话框

        Args:
            message: 错误消息
            title: 对话框标题
            window_id: 父窗口 ID

        Returns:
            1 表示成功调用

        Example:
            Dialog.error("文件保存失败！")
        """
        return Dialog.show_error_box(window_id, title, message)


# 保留旧的常量以保持向后兼容
class MessageBoxType:
    """消息框类型（已弃用，请使用字符串类型）"""

    NONE = "none"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    QUESTION = "question"


class OpenDialogProperties:
    """打开对话框属性（已弃用，请使用字符串列表）"""

    OPEN_FILE = "openFile"
    OPEN_DIRECTORY = "openDirectory"
    MULTI_SELECTIONS = "multiSelections"
    SHOW_HIDDEN_FILES = "showHiddenFiles"
