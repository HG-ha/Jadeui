# Calculator

简单计算器示例，演示基础的窗口创建和 IPC 通信。

## 功能

- 自定义标题栏
- 键盘输入支持
- Python 后端计算
- Mica 透明背景效果
- 应用图标

## 运行

```bash
python examples/calculator/app.py
```

## 打包

首先安装开发依赖（包含 nuitka）：

```bash
pip install jadeui[dev]
```

然后在 `examples/calculator` 目录下执行：

```bash
python ../../scripts/build.py app.py -o calculator
```

脚本会自动包含 `web` 目录和 `web/favicon.png` 图标。

## 文件结构

```
calculator/
├── app.py          # Python 后端
├── README.md       # 说明文档
└── web/
    ├── index.html  # 前端界面
    └── favicon.png # 应用图标
```
