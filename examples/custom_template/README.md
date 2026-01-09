# Custom Template

自定义 HTML 模板示例，完全控制应用布局。

## 功能

- 自定义导航栏布局
- 自定义主题切换
- 使用 Router 处理页面内容

## 运行

```bash
python app.py
```

## 打包

首先安装开发依赖（包含 nuitka）：

```bash
pip install jadeui[dev]
```

然后在 `examples/custom_template` 目录下执行：

```bash
python ../../scripts/build.py app.py -o custom
```

## 文件结构

```
custom_template/
├── app.py              # Python 后端
└── web/
    ├── index.html      # 自定义模板
    ├── css/
    │   └── custom.css  # 自定义样式
    └── pages/          # 页面内容
```

## 自定义模板要求

1. 包含 `id="page-content"` 的元素用于渲染页面
2. 监听 `router:update` IPC 消息
3. 发送 `router:ready` 通知后端

```javascript
jade.ipcMain('router:update', async function(data) {
    const navData = JSON.parse(data);
    // 加载页面内容到 #page-content
});

jade.ipcSend('router:ready', '');
```

