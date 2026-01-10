<p align="center">
  <img src="assets/light.svg" alt="JadeUI Logo" width="120">
</p>

<h1 align="center">JadeUI</h1>

<p align="center">
  <strong>Python SDK for JadeView - 使用 Web 技术构建桌面应用</strong>
</p>

<p align="center">
  <a href="https://pypi.org/project/jadeui/"><img src="https://img.shields.io/pypi/v/jadeui.svg" alt="PyPI version"></a>
  <a href="https://pypi.org/project/jadeui/"><img src="https://img.shields.io/pypi/pyversions/jadeui.svg" alt="Python versions"></a>
</p>

---

JadeUI 是 [JadeView](https://jade.run) 的 Python SDK，让你可以使用 Python + Web 技术构建现代桌面应用程序。

## 特性

- **WebView 窗口** - 使用 HTML/CSS/JS 构建 UI
- **现代外观** - 支持 Windows 11 Mica/Acrylic 效果
- **主题切换** - Light/Dark/System 主题
- **IPC 通信** - Python 与前端双向通信
- **打包体积** - 极小的依赖，打包后体积仅有8MB左右

## 安装

```bash
pip install jadeui
```

## 快速开始

### 最简模式

```python
from jadeui import Window

Window(title="Hello JadeUI", url="https://example.com").run()
```

### 本地应用（自动检测 web 目录）

```python
from jadeui import Window

Window(title="My App").run()  # 自动加载 web/index.html
```

### 完整模式（多窗口、全局事件）

```python
from jadeui import JadeUIApp, Window

app = JadeUIApp()

@app.on_ready
def on_ready():
    Window(title="Window 1", url="https://example.com").show()
    Window(title="Window 2", url="https://google.com").show()

app.run()
```

## 示例项目

查看 [examples](./examples) 目录获取完整示例：

| 示例 | 说明 |
|------|------|
| [simple](./examples/simple) | **最简示例** - 几行代码创建应用 |
| [calculator](./examples/calculator) | 基础计算器，展示窗口创建和 IPC 通信 |
| [backdrop_demo](./examples/backdrop_demo) | Windows 11 Mica/Acrylic 背景效果 |
| [router_demo](./examples/router_demo) | 内置路由系统实现多页面应用 |
| [custom_template](./examples/custom_template) | 自定义 HTML 模板和样式 |
| [vue_app](./examples/vue_app) | Vue.js + JadeUI 集成示例 |

### 效果预览

| Simple | Calculator | Backdrop |
|:---:|:---:|:---:|
| ![Simple](assets/simple.png) | ![Calculator](assets/calculator_iiBxCxUko6.png) | ![Backdrop](assets/backdrop_demo.png) |

| Router | Custom Template | Vue App |
|:---:|:---:|:---:|
| ![Router](assets/router_demo.png) | ![Custom](assets/custom_demo.png) | ![Vue](assets/vueapp.png) |

## API 文档

完整文档请访问: https://jade.run/python-sdk

## 打包发布

使用 Nuitka 将应用打包成独立的可执行文件：

```bash
# 安装开发依赖
pip install jadeui[dev]

# 打包为单个exe应用
python scripts/build.py your_app.py -o your_app

# 打包为目录形式，而不是单个exe
python scripts/build.py your_app.py -o your_app --no-onefile
```

打包脚本会自动包含 JadeView DLL 和 web 目录。更多选项：

```bash
python scripts/build.py --help
```

## 系统要求

- **操作系统**: Windows 10/11
- **Python**: 3.7+

## 许可证

MIT License

## 链接

- [Python SDK 文档](https://jade.run/python-sdk)
- [JadeView 官网](https://jade.run)
- [GitHub](https://github.com/HG-ha/Jadeui)
- [PyPI](https://pypi.org/project/jadeui/)

