#!/usr/bin/env python3
"""Render editable, text-safe technology posters as SVG.

The script deliberately keeps the hero image and the typography as separate
layers.  An optional local hero image is embedded read-only as a data URI;
all exact words, numbers, labels, grids, and decorative controls remain SVG
elements that can be edited in a vector editor.
"""

from __future__ import annotations

import argparse
import base64
import html
import mimetypes
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Iterable, List, Optional, Sequence, Tuple
import unicodedata


STYLE_NAMES = (
    "neon-grid",
    "blue-digital",
    "industrial-mono",
    "modern-dark",
    "editor-ui",
    "public-blueprint",
    "minimal-orb",
)
DESIGN_W = 1080
DESIGN_H = 1440


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def attrs(**values: object) -> str:
    chunks = []
    for key, value in values.items():
        if value is None:
            continue
        key = key.rstrip("_").replace("_", "-")
        chunks.append(f'{key}="{esc(value)}"')
    return " ".join(chunks)


def tag(name: str, content: str = "", **values: object) -> str:
    attr_text = attrs(**values)
    opening = f"<{name}{(' ' + attr_text) if attr_text else ''}"
    if content == "":
        return opening + " />"
    return opening + f">{content}</{name}>"


def rect(x: object, y: object, w: object, h: object, fill: str = "none", **kwargs: object) -> str:
    return tag("rect", x=x, y=y, width=w, height=h, fill=fill, **kwargs)


def line(x1: object, y1: object, x2: object, y2: object, stroke: str, **kwargs: object) -> str:
    return tag("line", x1=x1, y1=y1, x2=x2, y2=y2, stroke=stroke, **kwargs)


def circle(cx: object, cy: object, r: object, fill: str = "none", **kwargs: object) -> str:
    return tag("circle", cx=cx, cy=cy, r=r, fill=fill, **kwargs)


def path(d: str, fill: str = "none", **kwargs: object) -> str:
    return tag("path", d=d, fill=fill, **kwargs)


def group(*content: str, **kwargs: object) -> str:
    return tag("g", "".join(content), **kwargs)


def _char_width(ch: str) -> float:
    """A small, dependency-free approximation for CJK-aware wrapping."""
    if unicodedata.east_asian_width(ch) in {"W", "F", "A"}:
        return 1.0
    return 0.58


def _hard_wrap(line: str, max_units: float) -> List[str]:
    if not line:
        return [""]
    chunks: List[str] = []
    current: List[str] = []
    used = 0.0
    for ch in line:
        width = _char_width(ch)
        if current and used + width > max_units:
            chunks.append("".join(current))
            current = []
            used = 0.0
        current.append(ch)
        used += width
    if current:
        chunks.append("".join(current))
    return chunks or [""]


def wrap_text(value: object, max_units: float = 16.0, max_lines: int = 3) -> List[str]:
    """Wrap explicit newlines while always returning at most ``max_lines``."""
    text = (
        str(value or "")
        .replace("\r\n", "\n")
        .replace("\r", "\n")
        .replace("\\n", "\n")
    )
    raw_lines = text.split("\n")
    result: List[str] = []
    for raw in raw_lines:
        result.extend(_hard_wrap(raw, max_units))
    if not result:
        result = [""]
    if len(result) > max_lines:
        result = result[:max_lines]
        result[-1] = _clip_line(result[-1], max_units, ellipsis=True)
    return result


def _clip_line(line: str, max_units: float, ellipsis: bool = False) -> str:
    if sum(_char_width(ch) for ch in line) <= max_units:
        return line
    suffix = "…" if ellipsis else ""
    available = max(0.0, max_units - _char_width(suffix))
    out: List[str] = []
    used = 0.0
    for ch in line:
        cw = _char_width(ch)
        if used + cw > available:
            break
        out.append(ch)
        used += cw
    return "".join(out) + suffix


def text_block(
    x: float,
    y: float,
    value: object,
    *,
    size: float,
    fill: str,
    max_units: float = 16.0,
    max_lines: int = 3,
    weight: object = 700,
    family: str = "Arial, 'Microsoft YaHei', 'Noto Sans CJK SC', sans-serif",
    anchor: str = "start",
    line_height: Optional[float] = None,
    letter_spacing: Optional[object] = None,
    opacity: Optional[object] = None,
    transform: Optional[str] = None,
    extra: str = "",
) -> str:
    lines = wrap_text(value, max_units=max_units, max_lines=max_lines)
    lh = line_height or size * 1.16
    tspans: List[str] = []
    for index, one_line in enumerate(lines):
        tspans.append(
            tag(
                "tspan",
                esc(one_line),
                x=x,
                dy=0 if index == 0 else lh,
            )
        )
    extra_attrs = f" {extra.strip()}" if extra.strip() else ""
    body = "".join(tspans)
    text_attrs = attrs(
        x=x,
        y=y,
        fill=fill,
        font_size=size,
        font_family=family,
        font_weight=weight,
        text_anchor=anchor,
        letter_spacing=letter_spacing,
        opacity=opacity,
        transform=transform,
    )
    return f"<text {text_attrs}{extra_attrs}>{body}</text>"


def small_label(x: float, y: float, value: object, fill: str, size: float = 18, **kwargs: object) -> str:
    return text_block(x, y, value, size=size, fill=fill, weight=600, max_units=34, max_lines=1, **kwargs)


def image_data_uri(image_path: Path) -> str:
    mime = mimetypes.guess_type(image_path.name)[0] or "application/octet-stream"
    encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def hero_image(args: argparse.Namespace, x: float, y: float, w: float, h: float, *, opacity: float = 0.96) -> str:
    if not args.hero_data_uri:
        return ""
    image_filter = "url(#remove-light-bg)" if args.hero_remove_light else None
    frame = "" if args.hero_remove_light else rect(
        x - 10, y - 10, w + 20, h + 20, fill="#111318", rx=28, opacity=0.85
    )
    return group(
        frame,
        tag(
            "image",
            href=args.hero_data_uri,
            x=x,
            y=y,
            width=w,
            height=h,
            preserve_aspect_ratio="xMidYMid slice",
            opacity=opacity,
            filter=image_filter,
        ),
    )


def defs_block(style: str) -> str:
    # Reusable patterns and filters are intentionally plain SVG, so a vector
    # editor can inspect and alter them without a plugin or a linked asset.
    common = [
        tag("filter", tag("feGaussianBlur", std_deviation=8, result="blur"), id="soft-glow", x="-50%", y="-50%", width="200%", height="200%"),
        tag(
            "filter",
            '<feComponentTransfer>'
            '<feFuncR type="table" tableValues="1 0"/>'
            '<feFuncG type="table" tableValues="1 0"/>'
            '<feFuncB type="table" tableValues="1 0"/>'
            '</feComponentTransfer>'
            '<feComponentTransfer>'
            '<feFuncR type="gamma" amplitude="1.35" exponent="1.8" offset="0"/>'
            '<feFuncG type="gamma" amplitude="1.35" exponent="1.8" offset="0"/>'
            '<feFuncB type="gamma" amplitude="1.35" exponent="1.8" offset="0"/>'
            '</feComponentTransfer>',
            id="remove-light-bg",
            x="0%",
            y="0%",
            width="100%",
            height="100%",
        ),
        tag(
            "linearGradient",
            tag("stop", offset="0%", stop_color="#ffffff", stop_opacity="0.98")
            + tag("stop", offset="100%", stop_color="#c8ced6", stop_opacity="0.65"),
            id="steel-gradient",
            x1="0%",
            y1="0%",
            x2="100%",
            y2="100%",
        ),
        tag(
            "linearGradient",
            tag("stop", offset="0%", stop_color="#ff294f", stop_opacity="0.95")
            + tag("stop", offset="54%", stop_color="#e90036", stop_opacity="0.72")
            + tag("stop", offset="100%", stop_color="#050509", stop_opacity="0.05"),
            id="orb-gradient",
            x1="0%",
            y1="0%",
            x2="0%",
            y2="100%",
        ),
        tag(
            "pattern",
            path("M 64 0 L 0 0 0 64", stroke="#29312c", stroke_width=1, fill="none")
            + circle(2, 2, 1.4, fill="#516050", opacity="0.58"),
            id="neon-grid-pattern",
            width=64,
            height=64,
            pattern_units="userSpaceOnUse",
        ),
        tag(
            "pattern",
            circle(12, 12, 2.2, fill="#c1c4c9", opacity="0.28"),
            id="dot-pattern",
            width=36,
            height=36,
            pattern_units="userSpaceOnUse",
        ),
        tag(
            "pattern",
            line(0, 10, 0, 0, "#7f7a92", stroke_width=1, opacity="0.5")
            + line(0, 10, 10, 10, "#7f7a92", stroke_width=1, opacity="0.5"),
            id="editor-grid-pattern",
            width=20,
            height=20,
            pattern_units="userSpaceOnUse",
        ),
    ]
    if style == "public-blueprint":
        common.append(
            tag(
                "filter",
                tag("feTurbulence", type="fractalNoise", base_frequency="0.8", num_octaves=2, seed=5, result="noise")
                + tag("feColorMatrix", type="saturate", values="0", result="mono", **{"in": "noise"})
                + tag("feComponentTransfer", tag("feFuncA", type="table", table_values="0 0.05"), result="fade", **{"in": "mono"})
                + tag("feBlend", in2="SourceGraphic", mode="multiply"),
                id="paper-noise",
            )
        )
    return tag("defs", "".join(common))


def base_svg(args: argparse.Namespace, content: str, title: str, desc: str) -> str:
    accessible_title = title.replace("\\r\\n", "\n").replace("\\r", "\n").replace("\\n", "\n")
    root_attrs = attrs(
        width=args.width,
        height=args.height,
        viewBox=f"0 0 {DESIGN_W} {DESIGN_H}",
        preserve_aspect_ratio="xMidYMid meet",
        role="img",
        aria_label=accessible_title,
    )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" {root_attrs}>'
        + tag("title", esc(accessible_title))
        + tag("desc", esc(desc))
        + defs_block(args.style)
        + content
        + "</svg>"
    )


def corner_marks(color: str, size: float = 22, margin: float = 38, stroke_width: float = 3) -> str:
    x2 = DESIGN_W - margin
    y2 = DESIGN_H - margin
    m = margin
    return "".join(
        [
            line(m, m + size, m, m, color, stroke_width=stroke_width),
            line(m, m, m + size, m, color, stroke_width=stroke_width),
            line(x2, m + size, x2, m, color, stroke_width=stroke_width),
            line(x2, m, x2 - size, m, color, stroke_width=stroke_width),
            line(m, y2 - size, m, y2, color, stroke_width=stroke_width),
            line(m, y2, m + size, y2, color, stroke_width=stroke_width),
            line(x2, y2 - size, x2, y2, color, stroke_width=stroke_width),
            line(x2, y2, x2 - size, y2, color, stroke_width=stroke_width),
        ]
    )


def footer_pill(text: object, *, y: float, accent: str, dark: str = "#111111", search_prefix: str = "DESIGN") -> str:
    label = str(text or "TECH EDITORIAL")
    return group(
        rect(332, y, 416, 58, fill=accent, rx=29),
        rect(468, y + 6, 272, 46, fill="#ffffff", rx=23),
        text_block(354, y + 39, search_prefix, size=22, fill="#ffffff", max_units=7, max_lines=1, weight=800, letter_spacing=1),
        circle(496, y + 29, 10, fill="none", stroke=accent, stroke_width=3),
        line(503, y + 36, 512, y + 44, accent, stroke_width=3, stroke_linecap="round"),
        text_block(532, y + 39, label, size=23, fill=dark, max_units=15, max_lines=1, weight=600),
        text_block(390, y + 96, "ORIGINAL VISUAL SYSTEM", size=17, fill="#ffffff", max_units=24, max_lines=1, weight=400, anchor="middle", letter_spacing=1.4),
    )


def neon_grid(args: argparse.Namespace) -> str:
    lime, white, red, ink, muted = "#c9ff58", "#f7f8ee", "#f43651", "#060807", "#9ba59a"
    body: List[str] = [
        rect(0, 0, DESIGN_W, DESIGN_H, fill=ink),
        rect(0, 0, DESIGN_W, DESIGN_H, fill="url(#neon-grid-pattern)", opacity=0.78),
        rect(0, 0, DESIGN_W, 540, fill="#000000", opacity=0.48),
        corner_marks(lime, size=24, margin=42, stroke_width=2),
        small_label(72, 94, args.eyebrow, lime, size=20),
        text_block(72, 210, args.title, size=96, fill=lime, max_units=16, max_lines=3, weight=900, line_height=104, letter_spacing=-2),
        text_block(76, 472, args.subtitle, size=32, fill=white, max_units=30, max_lines=3, weight=500, line_height=41),
        rect(70, 508, 940, 2, fill=lime, opacity=0.7),
        small_label(76, 555, "VISUAL SYSTEM / 01", muted, size=16),
    ]
    if args.hero_data_uri:
        body.append(hero_image(args, 116, 608, 848, 454))
        body.append(rect(116, 608, 848, 454, fill="none", stroke=lime, stroke_width=3, opacity=0.84))
    else:
        body.extend(
            [
                rect(136, 650, 808, 346, fill="#0a100d", stroke=lime, stroke_width=3, opacity=0.92),
                path("M 172 914 L 322 754 L 430 850 L 590 698 L 736 860 L 894 736", fill="none", stroke=lime, stroke_width=3, opacity=0.86),
                path("M 170 946 C 336 774 480 1008 680 790 S 874 818 928 704", fill="none", stroke=white, stroke_width=1, stroke_dasharray="5 10", opacity=0.74),
                circle(322, 754, 12, fill=lime),
                circle(590, 698, 12, fill=lime),
                circle(894, 736, 12, fill=lime),
                rect(208, 702, 118, 34, fill=lime),
                small_label(267, 726, "BUILD", ink, size=15, anchor="middle"),
                small_label(815, 946, "01 / 100", lime, size=18, anchor="end"),
                text_block(180, 860, "把想法做成\n可以被看见的作品", size=48, fill=white, max_units=11, max_lines=2, weight=700, line_height=54),
            ]
        )
    body.extend(
        [
            rect(70, 1102, 940, 2, fill=lime, opacity=0.7),
            group(
                rect(74, 1140, 264, 50, fill=lime, rx=4),
                text_block(94, 1173, "模块 / MODULE", size=21, fill=ink, max_units=15, max_lines=1, weight=800),
            ),
            small_label(76, 1250, "A  让内容有结构", white, size=22),
            small_label(76, 1292, "B  让观点被记住", white, size=22),
            small_label(76, 1334, "C  让灵感持续生长", white, size=22),
            footer_pill(args.footer, y=1360, accent=red),
            circle(946, 1194, 5, fill=red),
            circle(972, 1194, 5, fill=lime),
            circle(998, 1194, 5, fill=white),
        ]
    )
    return base_svg(args, "".join(body), str(args.title), "neon-grid 黑底荧光绿科技编辑海报")


def industrial_mono(args: argparse.Namespace) -> str:
    yellow, white, black, gray, steel = "#ffea18", "#efefea", "#080808", "#818383", "#adb4ba"
    body: List[str] = [
        rect(0, 0, DESIGN_W, DESIGN_H, fill=black),
        rect(0, 0, DESIGN_W, DESIGN_H, fill="url(#dot-pattern)", opacity=0.34),
        corner_marks(steel, size=30, margin=42, stroke_width=2),
        line(62, 152, 1018, 152, gray, stroke_width=1, opacity=0.65),
        small_label(78, 116, args.eyebrow, yellow, size=20),
        text_block(72, 280, args.title, size=90, fill=white, max_units=17, max_lines=3, weight=900, line_height=98, letter_spacing=-1),
        text_block(78, 382, args.subtitle, size=25, fill=steel, max_units=38, max_lines=2, weight=500),
        text_block(78, 486, "01—SYSTEM / 02—PROCESS / 03—OUTPUT", size=18, fill=yellow, max_units=44, max_lines=1, weight=700, letter_spacing=1),
    ]
    if args.hero_data_uri:
        body.append(hero_image(args, 150, 540, 780, 500, opacity=0.92))
        body.append(rect(150, 540, 780, 500, fill="none", stroke=steel, stroke_width=2, opacity=0.75))
    else:
        body.extend(
            [
                rect(132, 564, 816, 464, fill="#141515", stroke=gray, stroke_width=2),
                rect(172, 610, 736, 304, fill="none", stroke=steel, stroke_width=1, stroke_dasharray="2 7", opacity=0.7),
                path("M 210 842 L 292 724 L 394 790 L 494 646 L 612 834 L 764 682 L 872 812", fill="none", stroke=white, stroke_width=5, opacity=0.82),
                path("M 222 876 L 312 764 L 402 842 L 514 714 L 616 874 L 778 742 L 868 852", fill="none", stroke=yellow, stroke_width=2, opacity=0.95),
                circle(292, 724, 9, fill=yellow),
                circle(494, 646, 9, fill=yellow),
                circle(764, 682, 9, fill=yellow),
                text_block(190, 990, "OBJECT / 002", size=19, fill=steel, max_units=22, max_lines=1, weight=700),
            ]
        )
    body.extend(
        [
            line(74, 1094, 1008, 1094, yellow, stroke_width=2),
            text_block(78, 1154, "拆解复杂问题，\n把答案装进系统。", size=40, fill=white, max_units=19, max_lines=2, weight=700, line_height=48),
            group(
                rect(702, 1128, 306, 92, fill=yellow, rx=2),
                text_block(724, 1168, "FIELD NOTE", size=18, fill=black, max_units=20, max_lines=1, weight=800),
                text_block(724, 1202, args.footer, size=24, fill=black, max_units=12, max_lines=1, weight=800),
            ),
            footer_pill("INDUSTRIAL / " + str(args.footer), y=1308, accent="#e8e8e2", dark=black),
            text_block(74, 1278, "NO. 0024   /   2026", size=15, fill=gray, max_units=22, max_lines=1, weight=600, letter_spacing=1),
        ]
    )
    return base_svg(args, "".join(body), str(args.title), "industrial-mono 黑白工业风海报，黄色作为强调色")


def editor_ui(args: argparse.Namespace) -> str:
    purple, magenta, dark, paper, gray = "#5d25d9", "#bd31a8", "#17131d", "#f8f6f0", "#b7b3bf"
    body: List[str] = [
        rect(0, 0, DESIGN_W, DESIGN_H, fill=paper),
        rect(0, 0, DESIGN_W, DESIGN_H, fill="url(#editor-grid-pattern)", opacity=0.32),
        rect(42, 42, 996, 1356, fill="none", stroke=purple, stroke_width=4, rx=32),
        small_label(82, 102, "PANEL  /  TECH EDITORIAL", purple, size=17),
        text_block(74, 242, args.title, size=78, fill=dark, max_units=19, max_lines=3, weight=900, line_height=88, letter_spacing=-2),
        text_block(82, 424, args.subtitle, size=28, fill=purple, max_units=31, max_lines=3, weight=650, line_height=38),
        group(
            rect(78, 486, 922, 4, fill=magenta),
            rect(78, 500, 320, 38, fill=purple, rx=4),
            text_block(94, 526, args.eyebrow, size=18, fill=paper, max_units=24, max_lines=1, weight=800),
        ),
        corner_marks(magenta, size=24, margin=54, stroke_width=3),
    ]
    if args.hero_data_uri:
        body.append(hero_image(args, 110, 574, 860, 412, opacity=0.93))
        body.append(rect(110, 574, 860, 412, fill="none", stroke=purple, stroke_width=4, rx=18))
    else:
        body.extend(
            [
                rect(108, 572, 864, 420, fill="#e8e3ef", stroke=purple, stroke_width=4, rx=18),
                rect(150, 630, 780, 290, fill="#ffffff", stroke=gray, stroke_width=1),
                line(170, 680, 910, 680, gray, stroke_width=1),
                line(170, 730, 910, 730, gray, stroke_width=1),
                line(170, 780, 910, 780, gray, stroke_width=1),
                line(170, 830, 910, 830, gray, stroke_width=1),
                rect(204, 700, 334, 24, fill=purple, opacity=0.8),
                rect(204, 750, 468, 24, fill=magenta, opacity=0.7),
                rect(204, 800, 278, 24, fill=purple, opacity=0.5),
                circle(832, 756, 74, fill="none", stroke=purple, stroke_width=5, stroke_dasharray="10 8"),
                circle(832, 756, 40, fill=magenta, opacity=0.72),
            ]
        )
    body.extend(
        [
            group(
                rect(80, 1036, 920, 200, fill="#ffffff", stroke=purple, stroke_width=3),
                rect(80, 1036, 260, 52, fill=purple),
                text_block(100, 1071, "LAYOUT NOTES", size=20, fill=paper, max_units=17, max_lines=1, weight=800),
                text_block(112, 1144, "把信息拆成\n清晰可编辑的模块", size=34, fill=dark, max_units=16, max_lines=2, weight=800, line_height=44),
                text_block(610, 1140, "01  hierarchy\n02  rhythm\n03  action", size=21, fill=purple, max_units=14, max_lines=3, weight=700, line_height=31),
            ),
            text_block(82, 1294, "PANEL / 01", size=17, fill=purple, max_units=12, max_lines=1, weight=800, letter_spacing=1),
            footer_pill(args.footer, y=1308, accent=magenta, dark=dark),
        ]
    )
    return base_svg(args, "".join(body), str(args.title), "editor-ui 白底紫色编辑器框信息图")


def public_blueprint(args: argparse.Namespace) -> str:
    blue, orange, yellow, white, ink = "#263989", "#ff7050", "#f4ee98", "#fbfaeb", "#142156"
    body: List[str] = [
        rect(0, 0, DESIGN_W, DESIGN_H, fill=blue),
        rect(0, 0, DESIGN_W, DESIGN_H, fill="#ffffff", opacity=0.05, filter="url(#paper-noise)"),
        rect(50, 48, 980, 1344, fill="none", stroke=yellow, stroke_width=2, stroke_dasharray="8 9", opacity=0.72),
        path("M 0 180 C 300 30 760 40 1080 170", fill="none", stroke=yellow, stroke_width=2, stroke_dasharray="8 10", opacity=0.75),
        path("M 0 1220 C 340 1390 760 1380 1080 1200", fill="none", stroke=yellow, stroke_width=2, stroke_dasharray="8 10", opacity=0.75),
        corner_marks(orange, size=26, margin=60, stroke_width=4),
        small_label(76, 112, args.eyebrow, yellow, size=18),
        text_block(74, 258, args.title, size=86, fill=white, max_units=17, max_lines=3, weight=900, line_height=98),
        text_block(78, 448, args.subtitle, size=28, fill=yellow, max_units=31, max_lines=3, weight=650, line_height=38),
        group(
            rect(76, 500, 290, 48, fill=orange),
            text_block(96, 534, "OPEN / BUILD / SHARE", size=17, fill=white, max_units=21, max_lines=1, weight=800, letter_spacing=1),
        ),
    ]
    if args.hero_data_uri:
        body.append(hero_image(args, 132, 596, 816, 390, opacity=0.9))
        body.append(rect(132, 596, 816, 390, fill="none", stroke=orange, stroke_width=3))
    else:
        body.extend(
            [
                rect(112, 590, 856, 412, fill="none", stroke=yellow, stroke_width=2),
                line(112, 796, 968, 796, yellow, stroke_width=1, stroke_dasharray="8 8"),
                line(540, 590, 540, 1002, yellow, stroke_width=1, stroke_dasharray="8 8"),
                path("M 160 920 L 250 710 L 380 860 L 520 680 L 642 884 L 820 700 L 928 918", fill="none", stroke=white, stroke_width=4),
                path("M 160 920 L 250 710 L 380 860 L 520 680 L 642 884 L 820 700 L 928 918", fill="none", stroke=orange, stroke_width=2, stroke_dasharray="2 10"),
                circle(250, 710, 12, fill=orange),
                circle(520, 680, 12, fill=orange),
                circle(820, 700, 12, fill=orange),
                small_label(160, 650, "[ 01 ]", yellow, size=19),
                small_label(800, 964, "[ 02 ]", yellow, size=19),
            ]
        )
    body.extend(
        [
            group(
                rect(76, 1050, 928, 190, fill=ink, stroke=orange, stroke_width=3),
                rect(76, 1050, 928, 50, fill=orange),
                text_block(98, 1084, "参与方式 / HOW TO BUILD", size=20, fill=white, max_units=24, max_lines=1, weight=800),
                text_block(110, 1160, "把一个想法发布出来，\n让更多人一起完善它。", size=34, fill=white, max_units=16, max_lines=2, weight=750, line_height=45),
                text_block(714, 1158, "#buildinpublic\n#techculture", size=20, fill=yellow, max_units=14, max_lines=2, weight=800, line_height=30),
            ),
            text_block(80, 1290, "2026  /  PUBLIC BLUEPRINT", size=16, fill=yellow, max_units=28, max_lines=1, weight=700, letter_spacing=1),
            footer_pill(args.footer, y=1308, accent=orange, dark=ink),
        ]
    )
    return base_svg(args, "".join(body), str(args.title), "public-blueprint 颗粒蓝底橙色公开构建风")


def blue_digital(args: argparse.Namespace) -> str:
    blue, bright, ice, mint, deep = "#1535C9", "#2458FF", "#EEF4FF", "#7DFFB2", "#0A1B69"
    body: List[str] = [
        rect(0, 0, DESIGN_W, DESIGN_H, fill=blue),
        rect(0, 0, DESIGN_W, DESIGN_H, fill="#0E2391", opacity=0.48),
        rect(0, 0, DESIGN_W, DESIGN_H, fill="url(#dot-pattern)", opacity=0.24),
        rect(54, 50, 972, 1340, fill="none", stroke=ice, stroke_width=2, opacity=0.58),
        line(540, 50, 540, 1390, ice, stroke_width=2, stroke_dasharray="8 12", opacity=0.5),
        line(54, 690, 1026, 690, ice, stroke_width=2, stroke_dasharray="8 12", opacity=0.5),
        corner_marks(ice, size=25, margin=62, stroke_width=4),
        small_label(78, 112, args.eyebrow, mint, size=18),
        text_block(70, 264, args.title, size=92, fill=ice, max_units=16, max_lines=3, weight=900, line_height=102, letter_spacing=-2),
        text_block(78, 458, args.subtitle, size=28, fill=mint, max_units=31, max_lines=3, weight=650, line_height=38),
        group(
            rect(78, 514, 250, 42, fill=ice, rx=21),
            text_block(98, 542, "AI STARTER", size=17, fill=deep, max_units=16, max_lines=1, weight=900, letter_spacing=1),
        ),
    ]
    if args.hero_data_uri:
        body.append(hero_image(args, 126, 606, 828, 436, opacity=0.92))
        body.append(rect(126, 606, 828, 436, fill="none", stroke=mint, stroke_width=3, opacity=0.86))
    else:
        body.extend(
            [
                rect(128, 588, 824, 466, fill=bright, opacity=0.35, stroke=ice, stroke_width=2),
                # Abstract translucent device / node cluster: no generated text.
                path("M 212 834 L 318 690 L 510 724 L 668 624 L 864 786 L 766 958 L 526 1008 L 312 950 Z", fill="#D6E4FF", opacity=0.24, stroke=ice, stroke_width=3),
                path("M 212 834 L 318 690 L 510 724 L 668 624 L 864 786 L 766 958 L 526 1008 L 312 950 Z", fill="none", stroke=mint, stroke_width=2, stroke_dasharray="3 9"),
                path("M 318 690 L 526 1008 M 510 724 L 312 950 M 668 624 L 766 958 M 212 834 L 864 786", fill="none", stroke=ice, stroke_width=2, opacity=0.88),
                circle(318, 690, 14, fill=mint),
                circle(668, 624, 14, fill=mint),
                circle(864, 786, 14, fill=mint),
                circle(526, 1008, 14, fill=mint),
                group(
                    rect(164, 662, 132, 44, fill=deep, stroke=ice, stroke_width=2),
                    small_label(230, 690, "agent", ice, size=17, anchor="middle"),
                ),
                group(
                    rect(780, 956, 140, 44, fill=deep, stroke=mint, stroke_width=2),
                    small_label(850, 984, "skill", mint, size=17, anchor="middle"),
                ),
            ]
        )
    body.extend(
        [
            small_label(82, 1114, "01 → 100  /  DIGITAL FIELD NOTES", ice, size=17),
            text_block(82, 1204, "让复杂技术\n变得可理解", size=42, fill=ice, max_units=13, max_lines=2, weight=800, line_height=50),
            group(
                rect(670, 1132, 332, 104, fill=deep, stroke=mint, stroke_width=2),
                small_label(700, 1170, "#build / #skill / #agent", mint, size=17),
                text_block(700, 1206, args.footer, size=24, fill=ice, max_units=13, max_lines=1, weight=800),
            ),
            footer_pill(args.footer, y=1308, accent="#F5F6FF", dark=deep),
        ]
    )
    return base_svg(args, "".join(body), str(args.title), "blue-digital 饱和蓝色数字像素风科技海报")


def modern_dark(args: argparse.Namespace) -> str:
    dark, panel, tan, yellow, white, muted = "#202020", "#0B0B09", "#D8A87C", "#F2E85D", "#F5F4ED", "#8C8A83"
    body: List[str] = [
        rect(0, 0, DESIGN_W, DESIGN_H, fill=dark),
        rect(0, 0, DESIGN_W, DESIGN_H, fill="url(#dot-pattern)", opacity=0.1),
        line(62, 182, 1018, 182, "#484840", stroke_width=1),
        corner_marks(tan, size=20, margin=48, stroke_width=2),
        small_label(78, 112, args.eyebrow, tan, size=18),
        text_block(76, 278, args.title, size=86, fill=white, max_units=17, max_lines=3, weight=800, line_height=96, letter_spacing=-1),
        text_block(80, 442, args.subtitle, size=27, fill=tan, max_units=32, max_lines=3, weight=500, line_height=37),
        group(
            rect(80, 518, 920, 2, fill=yellow),
            small_label(80, 556, "CONTENTS / 01—04", yellow, size=17),
        ),
    ]
    if args.hero_data_uri:
        body.append(hero_image(args, 116, 596, 848, 244, opacity=0.75))
        body.append(rect(116, 596, 848, 244, fill="none", stroke="#67645A", stroke_width=2))
    else:
        body.extend(
            [
                rect(116, 590, 848, 250, fill=panel, stroke="#67645A", stroke_width=2, rx=18),
                circle(290, 716, 78, fill="none", stroke=tan, stroke_width=3, opacity=0.75),
                circle(290, 716, 34, fill=yellow, opacity=0.9),
                path("M 454 778 C 546 636 674 636 772 774", fill="none", stroke=tan, stroke_width=4, opacity=0.75),
                path("M 470 754 C 570 700 680 700 812 650", fill="none", stroke=yellow, stroke_width=2, stroke_dasharray="3 9"),
                small_label(836, 652, "01 / 04", muted, size=16, anchor="end"),
            ]
        )
    card_y = 900
    card_h = 96
    card_data = [
        ("01", "观点与灵感", "从一个问题开始，把背景说清楚。"),
        ("02", "方法与过程", "把过程拆开，让别人可以复用。"),
        ("03", "结果与反馈", "记录真实结果，保留下一次迭代。"),
    ]
    for idx, (num, heading, detail) in enumerate(card_data):
        y = card_y + idx * 118
        body.append(
            group(
                rect(78, y, 924, card_h, fill=panel, stroke="#4A4942", stroke_width=1, rx=14),
                circle(126, y + 48, 15, fill=yellow),
                text_block(126, y + 55, num, size=15, fill=panel, max_units=3, max_lines=1, weight=900, anchor="middle"),
                text_block(172, y + 40, heading, size=25, fill=white, max_units=12, max_lines=1, weight=750),
                text_block(172, y + 70, detail, size=17, fill=muted, max_units=36, max_lines=1, weight=450),
                line(878, y + 38, 960, y + 38, tan, stroke_width=2),
                line(918, y + 56, 960, y + 56, yellow, stroke_width=2),
            )
        )
    body.extend(
        [
            text_block(80, 1300, "把内容做成\n可以继续使用的资产", size=32, fill=white, max_units=17, max_lines=2, weight=700, line_height=39),
            footer_pill(args.footer, y=1340, accent=tan, dark=panel),
        ]
    )
    return base_svg(args, "".join(body), str(args.title), "modern-dark 深灰现代活动信息图")


def minimal_orb(args: argparse.Namespace) -> str:
    red, white, black, muted = "#ff244d", "#f7f7f5", "#030304", "#8e8e93"
    body: List[str] = [
        rect(0, 0, DESIGN_W, DESIGN_H, fill=black),
        rect(62, 58, 956, 1324, fill="none", stroke="#101013", stroke_width=2),
        small_label(78, 118, args.eyebrow, red, size=18),
        text_block(74, 278, args.title, size=108, fill=white, max_units=14, max_lines=3, weight=400, line_height=120, letter_spacing=-3),
        text_block(80, 472, args.subtitle, size=26, fill=muted, max_units=34, max_lines=3, weight=400, line_height=36),
        line(80, 534, 1000, 534, "#25252b", stroke_width=1),
        circle(540, 870, 294, fill="url(#orb-gradient)", opacity=0.15),
        path("M 108 892 C 300 682 770 682 1002 910", fill="none", stroke=red, stroke_width=34, opacity=0.85, filter="url(#soft-glow)"),
        path("M 108 892 C 300 682 770 682 1002 910", fill="none", stroke="#ff244d", stroke_width=8, opacity=0.98),
        path("M 178 942 C 390 780 722 780 930 956", fill="none", stroke="#4d0b18", stroke_width=2),
        small_label(96, 666, "A QUIET SYSTEM FOR LOUD IDEAS", muted, size=16),
        small_label(96, 1094, "2026 / EDITION 01", muted, size=17),
        text_block(96, 1176, "把灵感\n留在视线里", size=42, fill=white, max_units=12, max_lines=2, weight=600, line_height=50),
        text_block(96, 1304, args.footer, size=21, fill=red, max_units=22, max_lines=1, weight=700, letter_spacing=1),
        footer_pill("MINIMAL / " + str(args.footer), y=1342, accent=red, dark=black),
    ]
    if args.hero_data_uri:
        # The hero sits in the negative space between the title and the orb;
        # the source remains untouched and is still an editable image layer.
        body.append(hero_image(args, 710, 580, 250, 220, opacity=0.55))
    return base_svg(args, "".join(body), str(args.title), "minimal-orb 黑底红色弧面极简封面")


RENDERERS = {
    "neon-grid": neon_grid,
    "blue-digital": blue_digital,
    "industrial-mono": industrial_mono,
    "modern-dark": modern_dark,
    "editor-ui": editor_ui,
    "public-blueprint": public_blueprint,
    "minimal-orb": minimal_orb,
}


def find_browser() -> Optional[str]:
    candidates = [
        shutil.which(name)
        for name in ("msedge", "msedge.exe", "chrome", "chrome.exe", "chromium", "chromium.exe")
    ]
    local_app_data = Path(os.environ.get("LOCALAPPDATA", ""))
    program_files = Path(os.environ.get("PROGRAMFILES", r"C:\Program Files"))
    program_files_x86 = Path(os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)"))
    candidates.extend(
        [
            str(local_app_data / "Microsoft/Edge/Application/msedge.exe"),
            str(local_app_data / "Google/Chrome/Application/chrome.exe"),
            str(program_files / "Microsoft/Edge/Application/msedge.exe"),
            str(program_files / "Google/Chrome/Application/chrome.exe"),
            str(program_files_x86 / "Microsoft/Edge/Application/msedge.exe"),
            str(program_files_x86 / "Google/Chrome/Application/chrome.exe"),
        ]
    )
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return str(Path(candidate))
    return None


def export_png(svg_path: Path, png_path: Path, width: int, height: int) -> Tuple[bool, str]:
    browser = find_browser()
    if not browser:
        return False, "未检测到 Microsoft Edge 或 Google Chrome headless，已保留 SVG；请安装浏览器后重试 PNG 导出。"
    png_path.parent.mkdir(parents=True, exist_ok=True)
    uri = svg_path.resolve().as_uri()
    command = [
        browser,
        "--headless=new",
        "--disable-gpu",
        "--hide-scrollbars",
        "--allow-file-access-from-files",
        f"--window-size={width},{height}",
        f"--screenshot={png_path.resolve()}",
        uri,
    ]
    try:
        completed = subprocess.run(command, capture_output=True, text=True, timeout=90, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, f"PNG 导出未完成（{exc}），已保留 SVG。"
    if completed.returncode != 0 or not png_path.exists():
        detail = (completed.stderr or completed.stdout or "浏览器未返回详细错误").strip().replace("\n", " ")
        return False, f"PNG 导出失败：{detail[:320]}；已保留 SVG。"
    return True, f"PNG 已生成：{png_path}"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate editable Chinese technology posters as SVG.")
    parser.add_argument("--style", choices=STYLE_NAMES, default="neon-grid", help="style family")
    parser.add_argument("--title", default="科技，让创意被看见", help="main title; use \\n for explicit line breaks")
    parser.add_argument("--subtitle", default="把复杂信息整理成清晰的视觉系统", help="subtitle")
    parser.add_argument("--eyebrow", default="TECH EDITORIAL / 01", help="small eyebrow label")
    parser.add_argument("--footer", default="TECH EDITORIAL", help="footer label")
    parser.add_argument("--output", required=True, type=Path, help="output SVG path")
    parser.add_argument("--png", type=Path, help="optional PNG path; requires local Edge/Chrome headless")
    parser.add_argument("--hero-image", type=Path, help="optional local PNG/JPG hero image")
    parser.add_argument(
        "--hero-remove-light",
        action="store_true",
        help="invert a near-white hero into black-backed ghosted line art; inspect before use",
    )
    parser.add_argument("--width", type=int, default=DESIGN_W, help="output width in pixels")
    parser.add_argument("--height", type=int, default=DESIGN_H, help="output height in pixels")
    parser.add_argument("--force", action="store_true", help="allow replacing existing SVG/PNG output")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.width <= 0 or args.height <= 0:
        parser.error("--width 和 --height 必须为正整数")
    if args.output.exists() and not args.force:
        parser.error(f"输出文件已存在，为保护旧稿未覆盖：{args.output}；如需替换请显式使用 --force")
    if args.png and args.png.exists() and not args.force:
        parser.error(f"PNG 文件已存在，为保护旧稿未覆盖：{args.png}；如需替换请显式使用 --force")
    if args.hero_image:
        if not args.hero_image.exists() or not args.hero_image.is_file():
            parser.error(f"找不到 --hero-image 文件：{args.hero_image}")
        if args.hero_image.suffix.lower() not in {".png", ".jpg", ".jpeg"}:
            parser.error("--hero-image 只接受 PNG/JPG/JPEG")
        args.hero_data_uri = image_data_uri(args.hero_image)
    else:
        args.hero_data_uri = ""
    args.output.parent.mkdir(parents=True, exist_ok=True)
    try:
        svg = RENDERERS[args.style](args)
        args.output.write_text(svg, encoding="utf-8", newline="\n")
    except (OSError, ValueError) as exc:
        print(f"SVG 生成失败：{exc}", file=sys.stderr)
        return 1
    print(f"SVG 已生成：{args.output}")
    if args.png:
        ok, message = export_png(args.output, args.png, args.width, args.height)
        print(message, file=sys.stdout if ok else sys.stderr)
        return 0 if ok else 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
