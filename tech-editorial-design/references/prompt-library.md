# 无字主体提示词库

## 使用原则

提示词只生成“无字主体素材”：物体、人物姿态（仅在有肖像授权时）、材质、光线、背景和构图。不要让模型生成中文、数字、Logo、品牌名、二维码、按钮或完整海报。文字和可识别标志留给 `render_poster.py` 的 SVG 图层。

通用负面约束：

> no readable text, no letters, no numbers, no logos, no trademarks, no watermark, no QR code, no UI copy, no brand identity, no celebrity likeness, no copied poster layout, no copyrighted character

生成后先人工检查主体是否含有意外字母、商标、平台水印或可识别人物，再嵌入 SVG。

## neon-grid：透明科技主体

```text
无字的 [主体对象]，中心偏右构图，黑色背景，荧光黄绿色边缘光，半透明外壳和精细线框，局部电路节点、低对比点阵和几何网格，冷静的产品展示视角，真实材质与清晰轮廓，周围保留大块黑色留白，适合竖版 3:4 科技编辑海报，high detail, crisp edges, subtle glow
```

可替换：`[主体对象]` 用“便携机器人 / 模块化硬件 / 抽象数据核心”等通用描述，不填具体品牌型号。

## blue-digital：蓝色数字主体

```text
无字的 [智能设备/抽象几何装置]，饱和钴蓝背景，透明或半透明白蓝 3D 材质，体积光和像素化边缘，周围有稀疏坐标数字、虚线框和微小几何标记，中心主体完整并保留大块安全留白，数字展会海报视觉，blue digital editorial, crisp translucent object, no text, no logo
```

## industrial-mono：工程结构主体

```text
无字的 [工业对象]，黑色工作台背景，黑白银灰单色工业摄影与工程制图混合，金属、玻璃、机械关节或爆炸结构，硬朗侧光，细微颗粒和坐标虚线，少量黄色高亮零件，中心主体完整、轮廓清楚、周围留白，竖版技术目录构图，monochrome industrial design, technical drawing, high contrast
```

## modern-dark：活动信息图背景

```text
无字的深灰现代活动信息图背景，黑色半透明圆角卡片、克制的米色标题线、少量黄色圆点和低亮度光晕，留出大块干净的文字安全区，秩序优先、现代无衬线编辑设计，dark modern event editorial background, no text, no logos
```

## editor-ui：留白产品模型

```text
无字的 [产品/概念物体]，浅灰白背景，干净的产品渲染，柔和阴影，轻微紫色环境光，主体位于画布中部并留出四周空白，平面设计编辑器展示感，清晰轮廓，适合叠加可编辑信息卡，no interface text, clean editorial product shot
```

## public-blueprint：蓝图与原型

```text
无字的 [原型/装置]，深蓝蓝图纸背景，细密纸张颗粒，白色结构线、虚线坐标、橙色定位标记和淡黄色辅助线，轻微等距或正面视角，像公共项目的原型蓝图，主体可读、留出大块文字安全区，vertical editorial blueprint, no text, no logos
```

## minimal-orb：红色弧面

```text
无字的抽象 [产品/概念形体]，近黑色背景，极简构图，单一红色发光弧面或半透明球体，柔和渐变、低噪点、精致边缘光，主体只占画面中下部，顶部和两侧保留大量空白，高端科技品牌视觉，minimal abstract editorial object, no text, no logo
```

## 生成后处理

1. 把素材裁成适合的主体比例，不改变原文件；在 SVG 中用 `preserveAspectRatio="xMidYMid slice"` 控制展示裁切。
2. 先用 SVG 加入准确文案，再导出 PNG；不要把文字重新交给图像模型修复。
3. 若素材带有水印、品牌标志、名人脸或现成角色，停止使用并换素材；不要用提示词“去水印”绕过权利边界。
