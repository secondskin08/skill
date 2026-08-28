#!/usr/bin/env python3
"""Build human-review sheets for the dedicated platform canvas outputs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from render_platform_series import PROFILE_BY_ID, PROFILES


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in (
        Path("C:/Windows/Fonts/msyh.ttc"),
        Path("C:/Windows/Fonts/simhei.ttf"),
        Path("/System/Library/Fonts/PingFang.ttc"),
        Path("/System/Library/Fonts/STHeiti Medium.ttc"),
        Path.home() / "Library/Fonts/NotoSansCJK-Regular.ttc",
        Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
        Path("/usr/share/fonts/opentype/noto/NotoSansCJKsc-Regular.otf"),
        Path("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"),
    ):
        if path.exists():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="生成多平台画布人工审核总览。")
    parser.add_argument("--input-root", type=Path, required=True, help="render_platform_series.py 的输出根目录")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preset", help="查看一个 ref 在五种画布上的效果，例如 ref-20")
    mode.add_argument("--profile", choices=tuple(PROFILE_BY_ID), help="查看一种画布上的 21 个视觉方向")
    parser.add_argument("--page", default="01-cover.png", help="要汇总的 PNG 文件名")
    parser.add_argument("--output", type=Path, required=True, help="总览 PNG 输出路径")
    parser.add_argument("--force", action="store_true", help="允许覆盖既有总览")
    return parser


def _entries(args: argparse.Namespace) -> list[tuple[Path, dict[str, object], str]]:
    rows: list[tuple[Path, dict[str, object], str]] = []
    if args.preset:
        for profile in PROFILES:
            folder = args.input_root / args.preset / profile.profile_id
            image_path = folder / args.page
            sidecar_path = folder / "series.json"
            if not image_path.exists() or not sidecar_path.exists():
                raise SystemExit(f"缺少预览或记录：{image_path} / {sidecar_path}")
            sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
            label = f"{profile.profile_id}｜{profile.label}｜{profile.width}×{profile.height}"
            rows.append((image_path, sidecar, label))
        return rows

    profile = PROFILE_BY_ID[args.profile]
    for number in range(1, 22):
        folder = args.input_root / f"ref-{number:02d}" / profile.profile_id
        image_path = folder / args.page
        sidecar_path = folder / "series.json"
        if not image_path.exists() or not sidecar_path.exists():
            raise SystemExit(f"缺少预览或记录：{image_path} / {sidecar_path}")
        sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
        label = f"{sidecar['preset']}｜{sidecar['chinese_name']}"
        rows.append((image_path, sidecar, label))
    return rows


def main() -> int:
    args = build_parser().parse_args()
    if args.output.exists() and not args.force:
        raise SystemExit(f"输出已存在，为保护旧稿未覆盖：{args.output}；如需替换请使用 --force")
    entries = _entries(args)

    preset_mode = bool(args.preset)
    columns = 2 if preset_mode else 3
    card_w, card_h = (500, 390) if preset_mode else (310, 390)
    margin, gap, label_h, header_h = 36, 24, 58, 112
    row_count = (len(entries) + columns - 1) // columns
    width = margin * 2 + columns * card_w + (columns - 1) * gap
    height = header_h + margin + row_count * (card_h + label_h) + max(0, row_count - 1) * gap + margin
    sheet = Image.new("RGB", (width, height), "#E9E9E6")
    draw = ImageDraw.Draw(sheet)
    title_font, meta_font, label_font = _font(32), _font(18), _font(17)
    title = f"{args.preset} 五种平台画布" if preset_mode else f"{args.profile} 21 个视觉方向"
    draw.text((margin, 26), title, font=title_font, fill="#151518")
    draw.text((margin, 72), f"页面：{args.page}｜等比缩略，未拉伸", font=meta_font, fill="#5B5B62")

    for index, (image_path, _sidecar, label) in enumerate(entries):
        col, row = index % columns, index // columns
        x = margin + col * (card_w + gap)
        y = header_h + margin + row * (card_h + label_h + gap)
        draw.rounded_rectangle((x, y, x + card_w, y + card_h), radius=10, fill="#FFFFFF", outline="#B2B2AD", width=2)
        with Image.open(image_path) as source:
            preview = source.convert("RGB")
            preview.thumbnail((card_w - 20, card_h - 20), Image.Resampling.LANCZOS)
        px = x + (card_w - preview.width) // 2
        py = y + (card_h - preview.height) // 2
        sheet.paste(preview, (px, py))
        draw.text((x + 4, y + card_h + 12), label, font=label_font, fill="#1D1D20")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(args.output, format="PNG", optimize=True)
    print(f"多平台总览已生成：{args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
