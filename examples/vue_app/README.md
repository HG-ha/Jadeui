# JadeUI + Vue 示例

这是一个使用 Vue 3 + JadeUI 开发桌面应用的示例。

## 项目结构

```
vue_app/
├── app.py              # JadeUI 后端
├── frontend/           # Vue 前端项目
│   ├── src/
│   │   ├── App.vue
│   │   ├── main.js
│   │   └── views/
│   ├── package.json
│   └── vite.config.js
└── web/                # 构建输出 (自动生成)
```

## 使用方法

### 1. 安装前端依赖

```bash
cd frontend
npm install
```

### 2. 构建前端

```bash
npm run build
```

这会将 Vue 应用构建到 `../web` 目录。

### 3. 运行应用

```bash
cd ..
python app.py
```

### 4. 打包

首先安装开发依赖（包含 nuitka）：

```bash
pip install jadeui[dev]
```

然后在 `examples/vue_app` 目录下执行：

```bash
python ../../scripts/build.py app.py -o vueapp
```

## 开发模式

如果需要热重载开发：

```bash
# 终端 1: 运行 Vite 开发服务器
cd frontend
npm run dev

# 终端 2: 直接用浏览器打开 http://localhost:5173 进行开发
```

开发完成后再构建并运行 JadeUI。

## IPC 通信

Vue 中调用 Python 后端：

```javascript
// 发送请求
window.jade.ipcSend('api:getUser', '')

// 监听响应
window.jade.ipcMain('api:getUser:response', (data) => {
  const user = JSON.parse(data)
  console.log(user)
})
```

Python 后端处理：

```python
@router.ipc.on("api:getUser")
def get_user(window_id, data):
    user = {"id": 1, "name": "张三"}
    router.ipc.send(window_id, "api:getUser:response", json.dumps(user))
    return 1
```

