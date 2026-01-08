"""
JadeUI 背景材料演示

展示 Windows 11 的三种背景材料效果：
- Mica: Windows 11 默认背景材料
- Mica Alt: Mica 的替代版本
- Acrylic: 半透明模糊背景

同时演示文件拖放功能。

注意：背景材料需要 transparent=True 才能生效
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from jadeui import JadeUIApp, Window
from jadeui.window import Backdrop, Theme
from jadeui.ipc import IPCManager
from jadeui.server import LocalServer

app = JadeUIApp()
ipc = IPCManager()
server = LocalServer()
window = None


@ipc.on("setBackdrop")
def handle_set_backdrop(window_id: int, backdrop: str) -> int:
    """设置背景材料"""
    global window
    if window and window.id is not None:
        window.set_backdrop(backdrop)
    return 1


@ipc.on("setTheme")
def handle_set_theme(window_id: int, theme: str) -> int:
    """设置主题"""
    global window
    if window:
        theme_map = {
            "light": Theme.LIGHT,
            "dark": Theme.DARK,
            "system": Theme.SYSTEM,
        }
        t = theme_map.get(theme.lower(), Theme.SYSTEM)
        window.set_theme(t)
    return 1


@ipc.on("windowAction")
def handle_window_action(window_id: int, action: str) -> int:
    global window
    if window:
        if action == "close":
            window.close()
        elif action == "minimize":
            window.minimize()
        elif action == "maximize":
            window.maximize()
    return 1


@app.on_ready
def on_ready():
    global window
    print("背景材料演示启动")

    web_dir = os.path.join(os.path.dirname(__file__), "web")
    url = server.start(web_dir, "backdrop_demo")

    window = Window(
        title="背景材料演示",
        width=850,
        height=620,
        url=f"{url}/index.html",
        remove_titlebar=True,
        transparent=True,  # 必须启用透明才能看到材料效果
        theme=Theme.SYSTEM,
    )
    
    # 监听文件拖放事件
    @window.on("file-drop")
    def on_file_drop(file_path, mime_type, x, y):
        print(f"📁 文件拖放: {file_path} ({mime_type}) at ({x:.0f}, {y:.0f})")
        # 发送文件信息到前端
        file_info = {
            "path": file_path,
            "name": os.path.basename(file_path),
            "mime": mime_type,
            "x": x,
            "y": y
        }
        ipc.send(window.id, "fileDrop", json.dumps(file_info))
    
    window.show()
    window.set_backdrop(Backdrop.MICA)


if __name__ == "__main__":
    app.initialize()
    app.run()

