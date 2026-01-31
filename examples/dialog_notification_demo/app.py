"""
JadeUI 对话框与通知示例

展示 JadeView 1.3.0+ 的对话框和通知功能：
- Dialog: 文件选择、消息框
- Notification: 桌面通知

运行方式:
    python examples/dialog_notification_demo/app.py
"""

import os

from jadeui import Dialog, Events, IPCManager, Notification, Window

# IPC 管理器
ipc = IPCManager()

# 配置通知（图标路径），也可以删除这两行代码，不配置图标
ICON = os.path.join(os.path.dirname(__file__), "web", "favicon.png")
Notification.config(app_name="JadeUI Demo", icon=ICON)


# ==================== 通知事件处理 ====================


@Notification.on(Events.NOTIFICATION_ACTION)
def on_action(data):
    """用户点击通知按钮"""
    button = data.get("action")  # "action_0" 或 "action_1"（按钮索引）
    button_text = data.get("title")  # 按钮文本
    action_id = data.get("arguments")  # 你传入的 action 参数

    print(f"[通知] 按钮点击: {button_text}")
    print(f"       按钮索引: {button}，action_id: {action_id}")

    # 根据 action_id 处理不同通知
    if action_id == "download_complete":
        if button == "action_0":
            print("       → 点击了打开下载文件夹")
        else:
            print("       → 点击忽略")
    elif action_id == "new_message":
        if button == "action_0":
            print("       → 打开消息")
        else:
            print("       → 稍后提醒")


@Notification.on(Events.NOTIFICATION_SHOWN)
def on_shown(data):
    """通知显示成功"""
    print(f"[通知] 已显示: {data.get('title')}")


@Notification.on(Events.NOTIFICATION_DISMISSED)
def on_dismissed(data):
    """通知被关闭"""
    print(f"[通知] 已关闭: {data.get('title')}")


# ==================== IPC 处理器 ====================


@ipc.on("openFile")
def open_file(window_id: int, _: str) -> str:
    Dialog.show_open_dialog(window_id, title="选择文件", properties=["openFile"])
    return '{"ok":true}'


@ipc.on("saveFile")
def save_file(window_id: int, _: str) -> str:
    Dialog.show_save_dialog(window_id, title="保存文件", default_path="untitled.txt")
    return '{"ok":true}'


@ipc.on("showMessage")
def show_message(window_id: int, type_: str) -> str:
    if type_ == "info":
        Dialog.alert("这是一条提示消息", title="提示", type_="info", window_id=window_id)
    elif type_ == "confirm":
        Dialog.confirm("确定要继续吗？", window_id=window_id)
    elif type_ == "error":
        Dialog.error("发生了一个错误！", window_id=window_id)
    return '{"ok":true}'


@ipc.on("notify")
def notify(_: int, type_: str) -> str:
    success = False

    if type_ == "simple":
        # 简单通知，无按钮
        success = Notification.show("简单通知", "这是一条简单的通知消息")

    elif type_ == "buttons":
        # 带按钮通知，模拟下载完成场景
        success = Notification.with_buttons(
            "下载完成",
            "video.mp4 已下载完成",
            "打开文件夹",
            "忽略",
            action="download_complete",  # 用于识别这个通知
        )

    elif type_ == "timeout":
        # 定时通知，模拟新消息场景
        success = Notification.with_buttons(
            "新消息",
            "你有一条来自小明的消息",
            "查看",
            "稍后",
            action="new_message",
            timeout=15000,  # 15秒后自动关闭
        )

    print(f"[通知] 显示结果: {success}")
    return f'{{"ok": {"true" if success else "false"}}}'


# 创建窗口
window = Window(title="Dialog & Notification Demo", width=700, height=500)
window.run()
