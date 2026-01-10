# JadeUI 简单示例

展示 JadeUI 最简洁的使用方式。

## 最简模式 - 自动检测 web 目录

只需几行代码，SDK 会自动：
- 检测当前目录下的 `web` 文件夹
- 启动本地服务器
- 注册窗口操作处理器

```python
from jadeui import Window

window = Window(title="My App", remove_titlebar=True, transparent=True)
window.run()  # 自动加载 web/index.html
```

## 指定 web 目录

```python
from jadeui import Window

window = Window(title="My App")
window.run(web_dir="frontend")  # 加载 frontend/index.html
```

## 远程 URL

```python
from jadeui import Window

window = Window(title="My App")
window.run(url="https://example.com")
```

## 运行示例

```bash
# 最简模式（加载 web/index.html）
python examples/simple/app_local.py

# 远程 URL 模式
python examples/simple/app.py
```

## 目录结构

```
simple/
├── app.py          # 远程 URL 示例
├── app_local.py    # 本地服务器示例
└── web/
    └── index.html  # 前端页面
```

## 对比

| 模式 | 代码 | 适用场景 |
|------|------|----------|
| `window.run()` | 自动检测 web 目录 | 本地开发 |
| `window.run(web_dir="...")` | 指定 web 目录 | 自定义目录 |
| `window.run(url="...")` | 加载远程 URL | 远程服务 |
