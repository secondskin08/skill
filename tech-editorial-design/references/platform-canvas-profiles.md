# 多平台画布与调用说明

这份说明解决一个常见误解：`ref-01` 至 `ref-21` 是视觉方向，`profile` 是目标平台的画布和专用构图。先选 ref，再选 profile；不要把平台比例当成新的视觉风格。

## 1. 五个 profile

| profile | 中文理解 | 尺寸 | 比例 | 适用场景 | 页面 |
|---|---|---:|---:|---|---|
| `xhs-portrait` | 小红书竖版 | 1080×1440 | 3:4 | 小红书图文、公众号正文页、正文配图、竖版海报 | `cover`、`section`、`body`、`quote`、`steps`、`data`、`illustration`、`ending` |
| `douyin-vertical` | 抖音竖屏 | 1080×1920 | 9:16 | 抖音封面、短视频章节帧、数据帧、结尾帧 | 同上 8 页 |
| `wechat-header` | 公众号头图 | 900×383 | 约 2.35:1 | 公众号文章头图 | 仅 `cover` |
| `social-square` | 方形分享图 | 1080×1080 | 1:1 | 公众号分享卡、社交卡片、方形栏目封面 | 同上 8 页 |
| `landscape-video` | 横版视频 | 1920×1080 | 16:9 | 横版视频、演示封面、电脑端宽屏内容 | 同上 8 页 |

这些尺寸是 Skill 的内置生产画布，不宣称是各平台永久不变的官方标准。平台界面和裁切规则可能更新，正式发布前仍要在目标平台实际预览。

### 为什么公众号头图只有封面

头图的职责是让读者识别文章主题，不是承载完整正文。公众号一篇文章的推荐组合是：

```text
wechat-header（文章头图）
        ↓
xhs-portrait（正文信息页、正文配图、步骤页、引用页等）
        ↓
social-square（转发或社交分享卡）
```

如果需要一张公众号内的横向正文图，应在内容设计中另行确定横图版式；本 v05 不把 `wechat-header` 冒充成完整正文画布。

## 2. 安全区

渲染器会把安全区写入每个 profile 文件夹里的 `series.json`。下面是默认值，单位为像素，表示内容应避开的边距：

| profile | 左 | 上 | 右 | 下 | 额外保留区 |
|---|---:|---:|---:|---:|---|
| `xhs-portrait` | 64 | 72 | 64 | 72 | 无 |
| `douyin-vertical` | 72 | 170 | 72 | 210 | 顶部平台覆盖区 0–170；底部平台覆盖区 1710–1920 |
| `wechat-header` | 42 | 32 | 42 | 32 | 无 |
| `social-square` | 64 | 64 | 64 | 64 | 无 |
| `landscape-video` | 96 | 72 | 96 | 72 | 无 |

抖音上下保留区是为了避开平台界面、标题和互动控件，不要把关键标题、日期、人物脸部或行动按钮放进去。安全区不是建议裁切线；成片仍须在真实平台预览。

## 3. 最小调用方式

脚本位置为 `tech-editorial-design/scripts/render_platform_series.py`。以下示例保持既有 21 个方向和调用名不变，`ref-20` 也可以替换为中文名 `奶油规则页` 或英文别名 `cream-rulebook`。

### Windows PowerShell

```powershell
cd "$HOME\.codex\skills\tech-editorial-design"
$out = Join-Path $PWD "platform-v05"
python scripts\render_platform_series.py --preset ref-20 --profile xhs-portrait --all-pages --title "我的主题" --subtitle "同一套设计语言" --footer "我的栏目" --output-dir $out --png
```

### macOS / Linux

```bash
cd "$HOME/.codex/skills/tech-editorial-design"
out="$PWD/platform-v05"
python3 scripts/render_platform_series.py --preset ref-20 --profile xhs-portrait --all-pages --title "我的主题" --subtitle "同一套设计语言" --footer "我的栏目" --output-dir "$out" --png
```

生成其他平台时只替换 `--profile`：

```text
xhs-portrait       小红书和公众号正文，3:4
douyin-vertical    抖音竖屏，9:16
wechat-header      公众号头图，只用 --page-type cover
social-square      方形分享卡，1:1
landscape-video    横版视频，16:9
```

一次生成一个方向的五种画布：

```powershell
python scripts\render_platform_series.py --preset ref-20 --all-profiles --all-pages --title "我的主题" --subtitle "同一套设计语言" --footer "我的栏目" --output-dir $out --png
```

在 macOS / Linux 中将命令中的 `python` 替换为 `python3`，并使用 `/` 路径。`--all-pages` 会根据 profile 的页面能力执行：`wechat-header` 生成 1 张 cover，其他 profile 各生成 8 张。

一次生成 21 个方向的封面覆盖：

```powershell
python scripts\render_platform_series.py --all-presets --profile xhs-portrait --page-type cover --output-dir $out --png
```

不要把 `--all-profiles` 和一个非 `cover` 的 `--page-type` 混用：`wechat-header` 没有 body、steps 等页面，脚本会为了保护输出而报错。需要所有平台的正文页时使用 `--all-pages`。

## 4. 输出结构

例如 `ref-20` 的五种封面会输出为：

```text
platform-v05/
└─ ref-20/
   ├─ xhs-portrait/
   │  ├─ 01-cover.svg
   │  ├─ 01-cover.png
   │  └─ series.json
   ├─ douyin-vertical/
   ├─ wechat-header/
   ├─ social-square/
   └─ landscape-video/
```

每个 profile 都有自己的 SVG、PNG 和 `series.json`。SVG 是可编辑源文件；PNG 是预览或平台上传候选。sidecar 至少应包含：`preset`、`alias`、`group`、`tokens`、`profile`、`canvas`、`ratio`、`safe_area`、`reserved_zones`、`page_types`、`dedicated_layout: true`、`stretched_from_3_4: false`。

## 5. 人工审核总览

先生成 PNG，再用总览脚本：

```powershell
python scripts\build_platform_contact_sheet.py --input-root $out --preset ref-20 --page 01-cover.png --output (Join-Path $out "ref-20-five-profiles.png")
```

这会把同一个 ref 的五种画布放在一起，适合检查“同一视觉系统、不同构图”。要检查某个平台是否仍然保留 21 个方向：

```powershell
python scripts\build_platform_contact_sheet.py --input-root $out --profile douyin-vertical --page 01-cover.png --output (Join-Path $out "douyin-21-directions.png")
```

总览脚本按等比缩略展示并标注 profile 或 ref，不把总览当作最终平台素材。

## 6. 验收规则

逐项确认：

- 画布像素尺寸和 SVG `viewBox` 与 profile 完全一致；
- 同一 ref 的五张封面使用相同 `tokens`、主 motif、色板、字体层级、纹理和边框语法；
- 五张图的构图和安全区适配目标比例，没有拉伸、黑边、上下留白或硬裁切伪装；
- 抖音关键内容没有进入顶部 170 px 或底部 210 px 保留区；
- 公众号组合使用头图、正文图和分享卡各自对应的 profile；
- `wechat-header` 只生成 `cover`，没有把正文硬塞进头图；
- 文案、数字、日期、二维码、品牌和主体图片经过人工核对并具有使用权限；
- SVG 文字、表格、边框、标签和线条仍可编辑；
- 在手机和实际目标平台预览后，标题、主体、行动信息均可读；
- 旧输出没有被覆盖；需要替换时必须显式使用 `--force` 并新建版本记录。

“保持一致”不等于每个平台的坐标完全相同：允许改变的是构图、主体大小、留白和安全区；不允许改变的是视觉令牌和设计语言。任何实质改变都应递增版本并重新人工审核。
