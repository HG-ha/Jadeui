"""
JadeUI 后端主导路由示例
"""

import json

from jadeui import Events, JadeUIApp, Router

app = JadeUIApp()
router = Router()

# ============ 定义页面路由 ============

router.page("/", "pages/home.html", title="首页", icon="🏠")
router.page("/dashboard", "pages/dashboard.html", title="仪表盘", icon="📊")
router.page("/users", "pages/users.html", title="用户管理", icon="👥")
router.page("/user/:id", "pages/user.html", title="用户详情", show_in_nav=False)
router.page("/settings", "pages/settings.html", title="设置", icon="⚙️")
router.page("/about", "pages/about.html", title="关于", icon="😄")


# ============ 模拟数据库 ============

users_db = [
    {"id": 1, "name": "张三", "email": "zhang@example.com", "role": "管理员"},
    {"id": 2, "name": "李四", "email": "li@example.com", "role": "编辑"},
    {"id": 3, "name": "王五", "email": "wang@example.com", "role": "用户"},
    {"id": 4, "name": "赵六", "email": "zhao@example.com", "role": "用户"},
]


# ============ IPC 处理器 ============

@router.ipc.on("get_users")
def get_users(window_id, data):
    """获取用户列表"""
    # 发送响应回前端
    router.ipc.send(window_id, "get_users:response", json.dumps(users_db))
    return 1


@router.ipc.on("get_user")
def get_user(window_id, user_id):
    """获取单个用户"""
    for user in users_db:
        if str(user["id"]) == str(user_id):
            router.ipc.send(window_id, "get_user:response", json.dumps(user))
            return 1
    router.ipc.send(window_id, "get_user:response", json.dumps({"error": "用户不存在"}))
    return 1


@router.ipc.on("get_stats")
def get_stats(window_id, data):
    """获取统计数据"""
    import datetime
    stats = {
        "server_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_users": len(users_db),
        "online_users": 2,
        "today_visits": 1234,
    }
    router.ipc.send(window_id, "get_stats:response", json.dumps(stats))
    return 1


# ============ 窗口事件处理 ============

def on_window_resized(data):
    """窗口大小变化事件处理
    
    事件类型: window-resized
    数据格式: {"width": 宽度, "height": 高度}
    """
    print(f"窗口大小变化: {data}")
    # 可以解析 JSON 获取具体尺寸
    try:
        size = json.loads(data)
        print(f"   宽度: {size.get('width')}, 高度: {size.get('height')}")
    except:
        pass


def on_window_moved(data):
    """窗口移动事件处理
    
    事件类型: window-moved
    数据格式: {"x": x坐标, "y": y坐标}
    """
    print(f"窗口移动: {data}")
    # 可以解析 JSON 获取具体坐标
    try:
        position = json.loads(data)
        print(f"    x: {position.get('x')}, y: {position.get('y')}")
    except:
        pass

# ============ 应用启动 ============

@app.on_ready
def on_ready():
    """应用就绪后"""
    print("应用已就绪")

    # mount 会自动导航到 initial_path (默认 "/")
    # web_dir 自动解析相对路径
    window = router.mount(
        title="JadeUI Demo",
        web_dir="web",
        width=1100,
        height=750,
        sidebar_width=200,
        theme="system",
    )

    # 监听窗口大小变化事件
    window.on(Events.WINDOW_RESIZED, on_window_resized)
    window.on(Events.WINDOW_MOVED, on_window_moved)


if __name__ == "__main__":
    app.initialize()
    app.run()
