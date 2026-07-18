# Color Sense Picker

一个 Windows 桌面取色判断软件，用于帮助摄影爱好者实时识别图片颜色，并判断当前颜色属于某个基础颜色的程度。

## 运行

```powershell
cd C:\Users\26499\Desktop\hobby\color_sense_picker
python app.py
```

也可以双击 `run_color_picker.bat`。

## 功能

- `屏幕取色 F6`：抓取当前桌面，进入全屏取色模式。
- 鼠标移动：查看像素级放大网格、HEX 色值和当前颜色。
- 鼠标单击：确认颜色。
- `Esc`：退出取色模式。
- HSV 色块和色相条：手动调整当前颜色。
- 颜色信息：HEX、RGB、HSV、HSL、CMYK。
- 颜色归属程度：用 CIE Lab 色差计算当前色与基础色卡的匹配度。
- 判断目标：可选择红、橙、黄、绿等基础色，也可以把当前颜色设为自定义目标。

## 算法说明

颜色匹配度基于 CIE Lab 空间的色差：

```text
score = 100 * exp(-(deltaE / 48)^2)
```

这个分数不是物理标准值，而是给交互设计用的直观“属于这个颜色的程度”。后续可以把 `PALETTE` 换成品牌色、服装色卡、工业标准色卡，或把 `similarity_score` 调整成更严格的阈值模型。
