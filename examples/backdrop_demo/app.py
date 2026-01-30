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

from jadeui import Backdrop, Events, IPCManager, JadeUIApp, LocalServer, Theme, Window

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

    # 自动解析相对路径
    url = server.start("backdrop_demo")

    window = Window(
        title="背景材料演示",
        width=860,
        height=680,
        url=f"{url}/index.html",
        remove_titlebar=True,
        transparent=True,  # 必须启用透明才能看到材料效果
        theme=Theme.SYSTEM,
    )

    # 监听文件拖放事件
    @window.on(Events.FILE_DROP)
    def on_file_drop(files, x, y):
        """处理文件拖放事件

        Args:
            files: 拖放的文件路径列表
            x: 拖放位置 X 坐标
            y: 拖放位置 Y 坐标
        """
        file_count = len([f for f in files if os.path.isfile(f)])
        folder_count = len([f for f in files if os.path.isdir(f)])

        print(f"📁 文件拖放: {file_count} 个文件, {folder_count} 个文件夹 at ({x:.0f}, {y:.0f})")
        for file_path in files:
            icon = "📂" if os.path.isdir(file_path) else "📄"
            print(f"   {icon} {file_path}")

        # 发送文件信息到前端
        file_info = {
            "files": [
                {"path": f, "name": os.path.basename(f), "isDir": os.path.isdir(f)} for f in files
            ],
            "x": x,
            "y": y,
        }
        ipc.send(window.id, "fileDrop", json.dumps(file_info))

    window.show()
    window.set_backdrop(Backdrop.MICA)


if __name__ == "__main__":
    app.initialize()
    app.run()
