#!/usr/bin/env python3
"""Build a labeled contact sheet for an eight-page visual series."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


PAGE_LABELS = {
    "cover": "封面",
    "section": "章节页",
    "body": "正文页",
    "quote": "引用页",
    "steps": "步骤页",
    "data": "数据页",
    "illustration": "正文配图",
    "ending": "结尾页",
}


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = (
        Path("C:/Windows/Fonts/msyh.ttc"),
        Path("C:/Windows/Fonts/simhei.ttf"),
        Path("C:/Windows/Fonts/arial.ttf"),
        Path("/System/Library/Fonts/PingFang.ttc"),
        Path("/System/Library/Fonts/STHeiti Medium.ttc"),
        Path.home() / "Library/Fonts/NotoSansCJK-Regular.ttc",
        Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
        Path("/usr/share/fonts/opentype/noto/NotoSansCJKsc-Regular.otf"),
        Path("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"),
        Path.home() / ".local/share/fonts/NotoSansCJK-Regular.ttc",
    )
    for candidate in candidates:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size)
    return ImageFont.load_default()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="为 8 页视觉系列生成带标签的审核总览图。")
    parser.add_argument("--input-dir", type=Path, required=True, help="包含 PNG 和 series.json 的 ref 目录")
    parser.add_argument("--output", type=Path, required=True, help="总览 PNG 输出路径")
    parser.add_argument("--force", action="store_true", help="允许覆盖既有总览图")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.output.exists() and not args.force:
        raise SystemExit(f"输出已存在，为保护旧稿未覆盖：{args.output}；如需替换请使用 --force")
    sidecar_path = args.input_dir / "series.json"
    if not sidecar_path.exists():
        raise SystemExit(f"缺少 series.json：{sidecar_path}")
    sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
    pages = sorted(args.input_dir.glob("[0-9][0-9]-*.png"))
    if len(pages) != 8:
        raise SystemExit(f"需要 8 张页面 PNG，实际找到 {len(pages)} 张：{args.input_dir}")

    margin, gap, card_w, card_h, label_h = 34, 24, 360, 480, 48
    header_h = 116
    sheet_w = margin * 2 + card_w * 2 + gap
    sheet_h = header_h + margin + (card_h + label_h) * 4 + gap * 3 + margin
    sheet = Image.new("RGB", (sheet_w, sheet_h), "#ECEBE6")
    draw = ImageDraw.Draw(sheet)
    title_font, label_font = _font(30), _font(20)
    title = f"{sidecar['preset']}  {sidecar['chinese_name']}｜封面到正文一致性总览"
    draw.text((margin, 28), title, font=title_font, fill="#171719")
    draw.text((margin, 72), f"组别：{sidecar['group']}　固定别名：{sidecar['alias']}", font=label_font, fill="#55555C")

    for index, page_path in enumerate(pages):
        col, row = index % 2, index // 2
        x = margin + col * (card_w + gap)
        y = header_h + margin + row * (card_h + label_h + gap)
        with Image.open(page_path) as source:
            preview = source.convert("RGB")
            preview.thumbnail((card_w, card_h), Image.Resampling.LANCZOS)
        px = x + (card_w - preview.width) // 2
        py = y + (card_h - preview.height) // 2
        draw.rounded_rectangle((x - 2, y - 2, x + card_w + 2, y + card_h + 2), radius=9, fill="#FFFFFF", outline="#B8B7B2", width=2)
        sheet.paste(preview, (px, py))
        page_type = page_path.stem.split("-", 1)[1]
        label = f"{index + 1:02d}  {PAGE_LABELS.get(page_type, page_type)} / {page_type}"
        draw.text((x + 8, y + card_h + 12), label, font=label_font, fill="#1D1D20")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(args.output, format="PNG", optimize=True)
    print(f"总览已生成：{args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
