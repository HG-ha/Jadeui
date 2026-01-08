"""
JadeUI 自定义模板示例

演示如何使用自定义 HTML 模板创建完全不同的布局。
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from jadeui import JadeUIApp, Router

app = JadeUIApp()
router = Router()

# ============ 定义页面路由 ============
# 注意：自定义模板时，icon 参数不会被自动使用
# 你需要在自己的模板中处理导航

router.page("/", "pages/home.html", title="首页")
router.page("/products", "pages/products.html", title="产品")
router.page("/contact", "pages/contact.html", title="联系我们")


# ============ IPC 处理器 ============

@router.ipc.on("get_products")
def get_products(window_id, data):
    products = [
        {"id": 1, "name": "产品 A", "price": 99},
        {"id": 2, "name": "产品 B", "price": 199},
        {"id": 3, "name": "产品 C", "price": 299},
    ]
    router.ipc.send(window_id, "get_products:response", json.dumps(products))
    return 1


# ============ 应用启动 ============

@app.on_ready
def on_ready():
    print("应用已就绪")

    web_dir = os.path.join(os.path.dirname(__file__), "web")

    # 使用自定义模板！
    router.mount(
        title="Custom Template Demo",
        web_dir=web_dir,
        template="index.html",  # ← 使用自定义模板
        width=900,
        height=600,
    )


if __name__ == "__main__":
    app.initialize()
    app.run()

