"""
JadeUI 全屏功能示例

展示全屏相关的 API 用法：
- set_fullscreen(bool) - 设置全屏状态
- toggle_fullscreen() - 切换全屏
- is_fullscreen - 查询全屏状态

注意：全屏功能需要 JadeView DLL 0.2.1+ 版本

运行方式:
    python examples/fullscreen_demo/app.py
"""

import json

from jadeui import Backdrop, Theme, Window
from jadeui.ipc import IPCManager

# 创建窗口
window = Window(
    title="全屏功能演示",
    width=900,
    height=600,
    remove_titlebar=True,
    transparent=True,
    theme=Theme.SYSTEM,
)

# 设置窗口属性
window.set_backdrop(Backdrop.MICA)

# 创建 IPC 管理器处理前端请求
ipc = IPCManager()


def send_state_update(window_id: int):
    """发送状态更新到前端"""
    win = Window.get_window_by_id(window_id)
    if win:
        state = json.dumps({"isFullscreen": win.is_fullscreen, "isMaximized": win.is_maximized})
        ipc.send(window_id, "fullscreenState", state)


@ipc.on("toggleFullscreen")
def handle_toggle_fullscreen(window_id: int, message: str) -> int:
    """切换全屏状态"""
    print(f"[IPC] toggleFullscreen: window_id={window_id}")
    win = Window.get_window_by_id(window_id)
    if win:
        win.toggle_fullscreen()
        send_state_update(window_id)
        return 1
    return 0


@ipc.on("setFullscreen")
def handle_set_fullscreen(window_id: int, message: str) -> int:
    """设置全屏状态"""
    print(f"[IPC] setFullscreen: window_id={window_id}, message={message}")
    win = Window.get_window_by_id(window_id)
    if win:
        # 解析消息获取 fullscreen 参数
        fullscreen = message.lower() == "true" if message else False
        win.set_fullscreen(fullscreen)
        send_state_update(window_id)
        return 1
    return 0


@ipc.on("getFullscreenState")
def handle_get_state(window_id: int, message: str) -> int:
    """获取当前全屏状态"""
    print(f"[IPC] getFullscreenState: window_id={window_id}")
    send_state_update(window_id)
    return 1


# 运行 - 自动检测 web 目录并启动服务器
window.run()
