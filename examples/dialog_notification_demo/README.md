# Dialog & Notification Demo

演示 JadeView 1.3.0+ 新增的对话框和通知功能。

## 功能演示

### 对话框 (Dialog)

同时支持**前端 JavaScript** 和 **Python 后端**两种调用方式：

- **打开文件对话框** - 选择单个或多个文件
- **保存文件对话框** - 选择保存路径
- **消息框** - 信息/警告/错误/确认

### 通知 (Notification)

仅支持 **Python 后端**调用（Windows 原生通知）：

- **简单通知** - 基本的标题和内容
- **带按钮通知** - 可交互，支持事件回调
- **定时通知** - 指定超时时间

## 运行

```bash
python examples/dialog_notification_demo/app.py
```

## 前端 API (JavaScript)

### Dialog

```javascript
// 打开文件对话框
const result = await jade.dialog.showOpenDialog({
    title: '选择文件',
    filters: [
        { name: '图片', extensions: ['png', 'jpg'] },
        { name: '所有文件', extensions: ['*'] }
    ],
    properties: ['openFile', 'multiSelections']
});

// 保存文件对话框
const savePath = await jade.dialog.showSaveDialog({
    title: '保存文件',
    defaultPath: 'document.txt',
    filters: [{ name: '文本文件', extensions: ['txt'] }]
});

// 消息框
const response = await jade.dialog.showMessageBox({
    title: '确认',
    message: '确定要删除吗？',
    type: 'warning',
    buttons: ['删除', '取消']
});
```

## 后端 API (Python)

### Dialog

```python
from jadeui import Dialog

# 打开文件对话框
Dialog.show_open_dialog(
    window_id=1,
    title="选择文件",
    filters=[{"name": "图片", "extensions": ["png", "jpg"]}],
    properties=["openFile", "multiSelections"]
)

# 消息框
Dialog.show_message_box(
    window_id=1,
    title="确认",
    message="确定要删除吗？",
    type_="warning",
    buttons=["删除", "取消"]
)

# 便捷方法
Dialog.alert("操作成功！")
Dialog.confirm("确定要继续吗？")
Dialog.error("操作失败！")
```

### Notification

```python
from jadeui import Notification, Events

# 配置应用（可选，有默认值）
Notification.config(app_name="我的应用", icon="C:/path/to/icon.ico")

# 监听通知事件
@Notification.on(Events.NOTIFICATION_ACTION)
def on_action(data):
    """用户点击通知按钮"""
    button = data.get("action")       # "action_0" 或 "action_1"
    action_id = data.get("arguments")  # 你传入的 action 参数
    print(f"按钮点击: {button}, action: {action_id}")

@Notification.on(Events.NOTIFICATION_DISMISSED)
def on_dismissed(data):
    """通知被关闭"""
    print(f"通知关闭: {data.get('title')}")

# 简单通知
Notification.show("标题", "内容")

# 带按钮的通知
Notification.with_buttons(
    "下载完成",
    "video.mp4 已下载",
    "打开",       # button1
    "忽略",       # button2
    action="download_123"  # 用于在回调中识别通知
)

# 设置超时
Notification.show("任务", "执行中...", timeout=10000)
```

## 参考文档

- [Dialog API](https://jade.run/guides/dialog-api)
- [Notification API](https://jade.run/guides/notification)
