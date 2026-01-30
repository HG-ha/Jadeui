"""
JadeUI + Vue 示例

前端使用 Vue 3 开发，JadeUI 作为桌面容器。

使用方法：
1. cd examples/vue_app/frontend
2. npm install
3. npm run build
4. cd ..
5. python app.py
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from jadeui import JadeUIApp, Router

app = JadeUIApp()
router = Router()

# Vue 应用使用前端路由，这里只需要定义一个根路径
# Vue Router 会处理所有路由
router.page("/", "index.html", title="Vue App")


# ============ IPC 处理器 ============
# 前端通过 jade.ipcSend 调用这些处理器


@router.ipc.on("api:getUser")
def get_user(window_id, data):
    user = {"id": 1, "name": "张三", "email": "zhang@example.com"}
    router.ipc.send(window_id, "api:getUser:response", json.dumps(user))
    return 1


@router.ipc.on("api:saveData")
def save_data(window_id, data):
    print(f"保存数据: {data}")
    router.ipc.send(window_id, "api:saveData:response", json.dumps({"success": True}))
    return 1


# ============ 应用启动 ============


@app.on_ready
def on_ready():
    print("应用已就绪")

    # 检查是否已构建
    web_dir = os.path.join(os.path.dirname(__file__), "web")
    if not os.path.exists(os.path.join(web_dir, "index.html")):
        print("错误: 请先构建 Vue 前端！")
        print("  cd frontend")
        print("  npm install")
        print("  npm run build")
        return

    # web_dir 自动解析相对路径
    router.mount(
        title="JadeUI + Vue",
        web_dir="web",
        template="index.html",  # Vue 入口
        width=1000,
        height=700,
    )


if __name__ == "__main__":
    app.initialize()
    app.run()
