"""
JadeUI 简单示例 - 使用本地服务器

展示最简洁的本地应用开发方式：
- 自动检测 web 目录
- 自动启动本地服务器
- 自动注册窗口操作处理器

运行方式:
    python examples/simple/app_local.py
"""

from jadeui import Backdrop, Theme, Window

# 创建窗口
window = Window(
    title="本地应用示例",
    width=800,
    height=600,
    remove_titlebar=True,
    transparent=True,
    theme=Theme.SYSTEM,
)

# 设置窗口属性
window.set_backdrop(Backdrop.MICA)

# 运行 - 自动检测 web 目录并启动服务器
window.run()
