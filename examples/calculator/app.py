"""
JadeUI 计算器示例 - 最小化实现

展示如何使用 JadeUI SDK 创建一个简单的计算器应用

运行方式:
    # 先安装包
    pip install -e .

    # 然后运行
    python examples/calculator/app.py
"""

from jadeui import Backdrop, IPCManager, JadeUIApp, LocalServer, Theme, Window


def main():
    print("🧮 JadeUI 计算器示例")
    print("=" * 40)

    # 创建应用
    app = JadeUIApp()
    app.initialize()

    # 本地服务器
    server = LocalServer()

    # IPC 管理器
    ipc = IPCManager()

    # 计算器逻辑 - 前端已经在本地计算，这里只做日志记录
    @ipc.on("calculate")
    def handle_calculate(window_id: int, expression: str) -> int:
        """记录计算历史"""
        print(f"📝 计算记录: {expression}")
        ipc.send(window_id, "result", "logged")
        return 1

    # 窗口操作
    @ipc.on("windowAction")
    def handle_window_action(window_id: int, action: str) -> int:
        print(f"🪟 窗口操作: window_id={window_id}, action={action}")
        window = Window.get_window_by_id(window_id)
        if window:
            print(f"   找到窗口: {window}")
            if action == "close":
                print("   执行关闭...")
                window.close()
            elif action == "minimize":
                print("   执行最小化...")
                window.minimize()
        else:
            print(f"   ❌ 未找到窗口 {window_id}")
            print(f"   活动窗口: {Window.get_all_windows()}")
        return 1

    # 应用准备就绪
    @app.on_ready
    def on_ready():
        # 启动服务器（自动解析相对路径）
        url = server.start("calculator")
        print(f"✅ 服务器: {url}")

        # 创建窗口
        window = Window(
            title="计算器",
            width=320,
            height=480,
            url=f"{url}/index.html",
            remove_titlebar=True,
            transparent=True,
            resizable=False,
            min_width=320,
            min_height=480,
            theme=Theme.DARK,
        )
        window.show()
        window.set_backdrop(Backdrop.MICA)
        print(f"✅ 窗口创建完成 (ID: {window.id})")

    print("⏳ 启动应用...")
    app.run()
    print("👋 退出")


if __name__ == "__main__":
    main()
