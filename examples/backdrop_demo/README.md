# Backdrop Demo

Windows 11 背景材料效果演示。

## 功能

- Mica 效果
- Mica Alt 效果
- Acrylic 效果
- 主题切换

## 运行

```bash
python app.py
```

## 打包

```bash
python ..\..\scripts\build.py app.py --output backdrop_demo
```

## 背景材料

| 类型 | 说明 |
|------|------|
| `mica` | 从桌面壁纸采样颜色，性能最佳 |
| `micaAlt` | Mica 的替代版本，效果更明显 |
| `acrylic` | 半透明模糊效果 |

## 注意

- 需要 Windows 11
- 窗口必须设置 `transparent=True`

