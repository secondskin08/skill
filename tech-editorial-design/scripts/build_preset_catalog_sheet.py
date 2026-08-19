#!/usr/bin/env python3
"""Build a labeled overview for the same page type across multiple presets."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in (
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
    ):
        if path.exists():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="汇总多个预设的同类页面，便于检查 21 个方向是否都能延伸。")
    parser.add_argument("--input-root", type=Path, required=True, help="包含 ref-01、ref-02 等目录的根目录")
    parser.add_argument("--page", default="01-body.png", help="每个 ref 目录中要汇总的 PNG 文件名")
    parser.add_argument("--start", type=int, default=1, help="起始 ref 编号")
    parser.add_argument("--end", type=int, default=21, help="结束 ref 编号")
    parser.add_argument("--title", default="21 预设延伸总览", help="总览标题")
    parser.add_argument("--output", type=Path, required=True, help="总览 PNG 输出路径")
    parser.add_argument("--force", action="store_true", help="允许覆盖既有总览")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.start < 1 or args.end > 21 or args.start > args.end:
        raise SystemExit("编号范围必须在 1—21 内，且 start 不得大于 end")
    if args.output.exists() and not args.force:
        raise SystemExit(f"输出已存在，为保护旧稿未覆盖：{args.output}；如需替换请使用 --force")

    entries: list[tuple[Path, dict[str, object]]] = []
    for number in range(args.start, args.end + 1):
        ref_dir = args.input_root / f"ref-{number:02d}"
        image_path = ref_dir / args.page
        sidecar_path = ref_dir / "series.json"
        if not image_path.exists() or not sidecar_path.exists():
            raise SystemExit(f"缺少预览或记录：{image_path} / {sidecar_path}")
        entries.append((image_path, json.loads(sidecar_path.read_text(encoding="utf-8"))))

    margin, gap, card_w, card_h, label_h = 34, 24, 330, 440, 44
    columns = 2
    rows = (len(entries) + columns - 1) // columns
    header_h = 96
    width = margin * 2 + card_w * columns + gap * (columns - 1)
    height = header_h + margin + rows * (card_h + label_h) + gap * max(0, rows - 1) + margin
    sheet = Image.new("RGB", (width, height), "#ECEBE6")
    draw = ImageDraw.Draw(sheet)
    title_font, label_font = _font(30), _font(18)
    draw.text((margin, 26), args.title, font=title_font, fill="#171719")
    draw.text((margin, 66), f"ref-{args.start:02d} 至 ref-{args.end:02d}｜{args.page}", font=label_font, fill="#5B5B62")

    for index, (image_path, sidecar) in enumerate(entries):
        col, row = index % columns, index // columns
        x = margin + col * (card_w + gap)
        y = header_h + margin + row * (card_h + label_h + gap)
        with Image.open(image_path) as source:
            preview = source.convert("RGB")
            preview.thumbnail((card_w, card_h), Image.Resampling.LANCZOS)
        px = x + (card_w - preview.width) // 2
        py = y + (card_h - preview.height) // 2
        draw.rounded_rectangle((x - 2, y - 2, x + card_w + 2, y + card_h + 2), radius=9, fill="#FFFFFF", outline="#B8B7B2", width=2)
        sheet.paste(preview, (px, py))
        label = f"{sidecar['preset']}  {sidecar['chinese_name']}"
        draw.text((x + 6, y + card_h + 11), label, font=label_font, fill="#1D1D20")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(args.output, format="PNG", optimize=True)
    print(f"总览已生成：{args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
