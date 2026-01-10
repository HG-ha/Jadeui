# JadeUI Examples

示例程序，展示 JadeUI 的各种用法。

## 快速开始

```python
from jadeui import Window

Window(title="My App", url="https://example.com").run()
```

## 示例列表

| 示例 | 说明 | 复杂度 |
|------|------|--------|
| [simple](./simple/) | **最简示例** - 几行代码创建应用 | ⭐ |
| [calculator](./calculator/) | 简单计算器，演示基础窗口和 IPC | ⭐⭐ |
| [backdrop_demo](./backdrop_demo/) | Windows 11 Mica/Acrylic 背景效果 | ⭐⭐ |
| [router_demo](./router_demo/) | 内置路由系统，多页面应用 | ⭐⭐⭐ |
| [custom_template](./custom_template/) | 自定义 HTML 模板 | ⭐⭐⭐ |
| [vue_app](./vue_app/) | Vue.js 前端框架集成 | ⭐⭐⭐ |

## 运行方式

```bash
# 最简示例
python examples/simple/app.py
```

## 使用模式对比

### 简单模式（推荐新手）

```python
from jadeui import Window

# 自动检测 web 目录
Window(title="My App").run()

# 或指定 URL
Window(title="My App").run(url="https://example.com")
```

### 完整模式（多窗口、复杂应用）

```python
from jadeui import JadeUIApp, Window

app = JadeUIApp()

@app.on_ready
def on_ready():
    Window(title="Window 1", url="...").show()
    Window(title="Window 2", url="...").show()

app.run()
```
