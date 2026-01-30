"""
JadeUI IPC 示例 - 前后端通信

展示前端调用后端并获取返回值：
- jade.invoke() 调用后端
- 后端返回 JSON 数据
- 前端显示返回结果

运行方式:
    python examples/ipc_demo/app.py
"""

import json
import os
import platform
import time

from jadeui import Backdrop, JadeUIApp, Theme, Window
from jadeui.ipc import IPCManager
from jadeui.server import LocalServer

# 获取脚本所在目录
script_dir = os.path.dirname(os.path.abspath(__file__))
web_dir = os.path.join(script_dir, "web")

# 创建应用
app = JadeUIApp()

# 启动本地服务器
server = LocalServer()
server_url = server.start("app", web_dir)

# 创建 IPC 管理器
ipc = IPCManager()


# ========== 注册 IPC 处理器 ==========


@ipc.on("greet")
def handle_greet(window_id: int, message: str) -> str:
    """处理问候请求，返回问候语"""
    name = message if message else "World"
    return json.dumps(
        {
            "greeting": f"Hello, {name}!",
            "from": "Python Backend",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
    )


@ipc.on("calculate")
def handle_calculate(window_id: int, message: str) -> str:
    """处理计算请求，返回计算结果"""
    try:
        data = json.loads(message)
        a = float(data.get("a", 0))
        b = float(data.get("b", 0))
        op = data.get("op", "+")

        if op == "+":
            result = a + b
        elif op == "-":
            result = a - b
        elif op == "*":
            result = a * b
        elif op == "/":
            result = a / b if b != 0 else "Error: Division by zero"
        else:
            result = "Error: Unknown operator"

        return json.dumps({"expression": f"{a} {op} {b}", "result": result, "success": True})
    except Exception as e:
        return json.dumps({"error": str(e), "success": False})


@ipc.on("getSystemInfo")
def handle_system_info(window_id: int, message: str) -> str:
    """获取系统信息"""
    return json.dumps(
        {
            "python_version": platform.python_version(),
            "os": platform.system(),
            "os_version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "cwd": os.getcwd(),
        }
    )


# 创建窗口（设置 URL）
window = Window(
    url=f"{server_url}/index.html",
    title="JadeUI IPC Demo",
    width=800,
    height=600,
    remove_titlebar=True,
    transparent=True,
    theme=Theme.SYSTEM,
)
window.set_backdrop(Backdrop.MICA)


# 注册窗口操作处理器
@ipc.on("windowAction")
def handle_window_action(window_id: int, action: str) -> str:
    """处理窗口操作"""
    if action == "close":
        window.close()
    elif action == "minimize":
        window.minimize()
    elif action == "maximize":
        window.maximize()
    return json.dumps({"success": True})


# 在 app-ready 时显示窗口
@app.on_ready
def on_ready():
    window.show()


# 启动应用
app.run()
