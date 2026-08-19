#!/usr/bin/env python3
"""Render a 21-direction reference catalog as editable SVG posters.

This companion renderer is intentionally separate from render_poster.py.
Each preset has a different layout skeleton so a reference catalog can be
reviewed as a set of actual directions instead of seven variations of one
template. Exact text remains editable SVG; the optional hero image is used
only by ref-02 and is embedded as a read-only data URI.
"""

from __future__ import annotations

import argparse
import copy
import sys
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence, Tuple

import render_poster as rp


DESIGN_W = 1080
DESIGN_H = 1440
PRESETS: Tuple[str, ...] = tuple(f"ref-{index:02d}" for index in range(1, 22))


def _txt(
    x: float,
    y: float,
    value: object,
    size: float,
    fill: str,
    *,
    max_units: float = 16,
    max_lines: int = 3,
    weight: object = 700,
    line_height: Optional[float] = None,
    anchor: str = "start",
    letter_spacing: Optional[object] = None,
    opacity: Optional[object] = None,
    transform: Optional[str] = None,
) -> str:
    return rp.text_block(
        x,
        y,
        value,
        size=size,
        fill=fill,
        max_units=max_units,
        max_lines=max_lines,
        weight=weight,
        line_height=line_height,
        anchor=anchor,
        letter_spacing=letter_spacing,
        opacity=opacity,
        transform=transform,
    )


def _label(x: float, y: float, value: object, fill: str, size: float = 18, **kwargs: object) -> str:
    return rp.small_label(x, y, value, fill, size=size, **kwargs)


def _doc(args: argparse.Namespace, body: str, desc: str) -> str:
    # base_svg supplies common editable defs and the accessible title.
    # A neutral style name keeps this catalog independent of the seven-family
    # poster renderer while still reusing its export contract.
    local_args = copy.copy(args)
    local_args.style = "reference-catalog"
    return rp.base_svg(local_args, body, str(args.title), desc)


def _corner_frame(color: str, *, margin: float = 44, size: float = 24, width: float = 3) -> str:
    return rp.corner_marks(color, size=size, margin=margin, stroke_width=width)


def _grid(x0: float, y0: float, x1: float, y1: float, step: float, color: str, opacity: float = 0.25) -> str:
    parts: List[str] = []
    x = x0
    while x <= x1:
        parts.append(rp.line(x, y0, x, y1, color, stroke_width=1, opacity=opacity))
        x += step
    y = y0
    while y <= y1:
        parts.append(rp.line(x0, y, x1, y, color, stroke_width=1, opacity=opacity))
        y += step
    return "".join(parts)


def _dots(x0: float, y0: float, x1: float, y1: float, step: float, color: str, radius: float = 3, opacity: float = 0.5) -> str:
    parts: List[str] = []
    y = y0
    row = 0
    while y <= y1:
        x = x0 + (step * 0.5 if row % 2 else 0)
        while x <= x1:
            parts.append(rp.circle(x, y, radius, fill=color, opacity=opacity))
            x += step
        y += step
        row += 1
    return "".join(parts)


def _pill(x: float, y: float, w: float, h: float, text: object, fill: str, text_fill: str, *, stroke: Optional[str] = None) -> str:
    return rp.group(
        rp.rect(x, y, w, h, fill=fill, rx=h / 2, stroke=stroke or "none", stroke_width=2 if stroke else None),
        _txt(x + w / 2, y + h * 0.68, text, min(22, h * 0.42), text_fill, max_units=max(6, w / 24), max_lines=1, weight=800, anchor="middle"),
    )


def _tag_box(x: float, y: float, w: float, h: float, text: object, fill: str, text_fill: str, stroke: Optional[str] = None) -> str:
    return rp.group(
        rp.rect(x, y, w, h, fill=fill, rx=5, stroke=stroke or "none", stroke_width=2 if stroke else None),
        _txt(x + w / 2, y + h * 0.67, text, min(26, h * 0.43), text_fill, max_units=max(7, w / 23), max_lines=1, weight=800, anchor="middle"),
    )


def _arrow(x1: float, y1: float, x2: float, y2: float, color: str, width: float = 4) -> str:
    # A small open arrow keeps the diagrams editable and avoids marker defs.
    dx = x2 - x1
    dy = y2 - y1
    length = max(1.0, (dx * dx + dy * dy) ** 0.5)
    ux, uy = dx / length, dy / length
    px, py = -uy, ux
    head = 16
    ax, ay = x2 - ux * head, y2 - uy * head
    return rp.line(x1, y1, x2, y2, color, stroke_width=width) + rp.path(
        f"M {x2} {y2} L {ax + px * head * 0.55} {ay + py * head * 0.55} M {x2} {y2} L {ax - px * head * 0.55} {ay - py * head * 0.55}",
        fill="none",
        stroke=color,
        stroke_width=width,
        stroke_linecap="round",
    )


def _avatar(cx: float, cy: float, radius: float, accent: str, bg: str) -> str:
    # Abstract geometric avatar placeholder; deliberately not a person photo.
    return rp.group(
        rp.circle(cx, cy, radius, fill=bg, stroke=accent, stroke_width=3),
        rp.circle(cx, cy - radius * 0.24, radius * 0.27, fill=accent, opacity=0.9),
        rp.path(
            f"M {cx - radius * 0.53} {cy + radius * 0.48} Q {cx} {cy - radius * 0.02} {cx + radius * 0.53} {cy + radius * 0.48}",
            fill=accent,
            opacity=0.78,
        ),
        rp.rect(cx - radius * 0.13, cy - radius * 0.65, radius * 0.26, radius * 0.18, fill=bg, rx=3, opacity=0.7),
    )


def _device(cx: float, cy: float, scale: float, stroke: str, fill: str = "none") -> str:
    # Original, non-branded device silhouette for catalog directions.
    w, h = 230 * scale, 150 * scale
    return rp.group(
        rp.rect(cx - w / 2, cy - h / 2, w, h, fill=fill, stroke=stroke, stroke_width=5 * scale, rx=22 * scale),
        rp.rect(cx - w * 0.34, cy - h * 0.30, w * 0.68, h * 0.42, fill="none", stroke=stroke, stroke_width=3 * scale, rx=12 * scale),
        rp.circle(cx - w * 0.23, cy + h * 0.28, 8 * scale, fill=stroke),
        rp.circle(cx + w * 0.23, cy + h * 0.28, 8 * scale, fill=stroke),
        rp.line(cx - w * 0.16, cy + h * 0.15, cx + w * 0.16, cy + h * 0.15, stroke, stroke_width=3 * scale),
        rp.line(cx, cy + h / 2, cx, cy + h / 2 + 34 * scale, stroke, stroke_width=5 * scale),
        rp.line(cx - 42 * scale, cy + h / 2 + 34 * scale, cx + 42 * scale, cy + h / 2 + 34 * scale, stroke, stroke_width=5 * scale),
    )


def _bulb(cx: float, cy: float, scale: float, fill: str, stroke: str) -> str:
    r = 170 * scale
    return rp.group(
        rp.circle(cx, cy - 24 * scale, r, fill=fill, stroke=stroke, stroke_width=5 * scale, opacity=0.96),
        rp.path(f"M {cx - r * 0.58} {cy + r * 0.55} L {cx - 68 * scale} {cy + r * 0.95} L {cx + 68 * scale} {cy + r * 0.95} L {cx + r * 0.58} {cy + r * 0.55}", fill=fill, stroke=stroke, stroke_width=5 * scale),
        rp.rect(cx - 68 * scale, cy + r * 0.91, 136 * scale, 32 * scale, fill=stroke, rx=8 * scale),
        rp.rect(cx - 58 * scale, cy + r * 1.12, 116 * scale, 30 * scale, fill=fill, stroke=stroke, stroke_width=4 * scale, rx=7 * scale),
        rp.line(cx - 34 * scale, cy + r * 1.12, cx + 34 * scale, cy + r * 1.12, stroke, stroke_width=4 * scale),
        rp.path(f"M {cx - r * 0.26} {cy + r * 0.65} L {cx + r * 0.26} {cy + r * 0.65}", fill="none", stroke=stroke, stroke_width=4 * scale),
    )


def _puzzle_piece(x: float, y: float, w: float, h: float, fill: str, rotate: float = 0) -> str:
    d = (
        f"M {x} {y + h * 0.2} L {x + w * 0.28} {y + h * 0.2} "
        f"C {x + w * 0.18} {y - h * 0.1} {x + w * 0.42} {y - h * 0.1} {x + w * 0.38} {y + h * 0.2} "
        f"L {x + w * 0.68} {y + h * 0.2} L {x + w * 0.68} {y + h * 0.48} "
        f"C {x + w * 1.08} {y + h * 0.36} {x + w * 1.08} {y + h * 0.64} {x + w * 0.68} {y + h * 0.52} "
        f"L {x + w * 0.68} {y + h * 0.82} L {x + w * 0.4} {y + h * 0.82} "
        f"C {x + w * 0.52} {y + h * 1.18} {x + w * 0.24} {y + h * 1.18} {x + w * 0.32} {y + h * 0.82} "
        f"L {x} {y + h * 0.82} Z"
    )
    return rp.path(d, fill=fill, stroke="#ffffff", stroke_width=3, opacity=0.95, transform=f"rotate({rotate} {x + w / 2} {y + h / 2})")


def _soft_blob(cx: float, cy: float, rx: float, ry: float, fill: str, rotate: float = 0) -> str:
    d = f"M {cx - rx} {cy} C {cx - rx * 0.82} {cy - ry * 1.10} {cx - rx * 0.18} {cy - ry * 0.92} {cx} {cy - ry} C {cx + rx * 0.92} {cy - ry * 0.75} {cx + rx * 1.08} {cy - ry * 0.16} {cx + rx} {cy} C {cx + rx * 0.75} {cy + ry * 0.94} {cx + rx * 0.14} {cy + ry * 1.03} {cx} {cy + ry} C {cx - rx * 0.92} {cy + ry * 0.78} {cx - rx * 1.12} {cy + ry * 0.14} {cx - rx} {cy} Z"
    return rp.path(d, fill=fill, opacity=0.9, transform=f"rotate({rotate} {cx} {cy})")


def ref_01(args: argparse.Namespace) -> str:
    ink, lime, white, muted = "#050606", "#C9FF58", "#FAFAF2", "#969C96"
    body = [rp.rect(0, 0, DESIGN_W, DESIGN_H, fill=ink), _dots(30, 40, 1050, 1390, 42, "#2E3830", 2, 0.6), _corner_frame(lime, margin=42, size=28, width=2)]
    body += [_label(72, 104, "01 / CARD WALL", lime, 19), _txt(72, 218, args.title, 82, lime, max_units=15, max_lines=2, weight=900, line_height=92), _txt(74, 370, args.subtitle, 27, white, max_units=32, max_lines=2, weight=500, line_height=36), rp.line(72, 430, 1008, 430, lime, stroke_width=3)]
    card_w, card_h = 206, 310
    colors = ["#C9FF58", "#A7E1FF", "#FFBF7A", "#D39BFF", "#FF6F91", "#80FFD3", "#F4EC76", "#B4B8FF"]
    for idx in range(8):
        col, row = idx % 4, idx // 4
        x, y = 74 + col * 232, 500 + row * 350
        accent = colors[idx]
        body.append(rp.group(rp.rect(x, y, card_w, card_h, fill="#101512", stroke=accent, stroke_width=3), rp.rect(x, y, card_w, 204, fill="#0A0C0B"), _avatar(x + card_w / 2, y + 100, 72, accent, "#17201B"), rp.rect(x, y + 204, card_w, 106, fill=accent), _txt(x + 18, y + 244, f"创作者 {idx + 1:02d}", 24, ink, max_units=9, max_lines=1, weight=900), _txt(x + 18, y + 278, "原创方向 / 视觉研究", 16, ink, max_units=13, max_lines=1, weight=600)))
    body += [_pill(370, 1302, 340, 54, args.footer, lime, ink)]
    return _doc(args, "".join(body), "ref-01 人物卡片墙：抽象创作者卡片的四列两行布局")


def ref_02(args: argparse.Namespace) -> str:
    ink, green, white, muted = "#050907", "#B8FF4A", "#F0F6EE", "#70816D"
    body = [rp.rect(0, 0, DESIGN_W, DESIGN_H, fill=ink), rp.rect(0, 0, DESIGN_W, DESIGN_H, fill="url(#neon-grid-pattern)", opacity=0.62), _grid(60, 80, 1020, 1310, 120, green, 0.1), _corner_frame(green, margin=46, size=24, width=2), _label(72, 112, "02 / DEVICE LAB", green, 18), _txt(72, 226, args.title, 82, white, max_units=16, max_lines=2, weight=900, line_height=94), _txt(74, 372, args.subtitle, 27, green, max_units=32, max_lines=2, weight=600), _tag_box(76, 438, 200, 44, "X-RAY / OBJECT", "#132113", green, green)]
    if args.hero_data_uri:
        hero_args = copy.copy(args)
        hero_args.hero_data_uri = args.hero_data_uri
        hero_args.hero_remove_light = False
        body.append(rp.hero_image(hero_args, 100, 548, 880, 490, opacity=0.88))
    else:
        body += [_device(540, 790, 2.15, green, "#122015"), rp.circle(540, 722, 122, fill="#DFFFB4", opacity=0.18), rp.path("M 140 1014 L 290 670 L 770 670 L 940 1014", fill="none", stroke=green, stroke_width=2, stroke_dasharray="7 10", opacity=0.72)]
    body += [rp.rect(100, 548, 880, 490, fill="none", stroke=green, stroke_width=3), _tag_box(110, 1088, 214, 48, "MODULE 01", green, ink), _label(110, 1188, "透明结构 / 可拆解 / 可复用", white, 21), _label(110, 1230, "OBJECT DATA  /  04.21.26", muted, 17), _pill(700, 1190, 270, 54, args.footer, green, ink)]
    return _doc(args, "".join(body), "ref-02 黑绿透明设备海报：可选嵌入只读主体图层")


def ref_03(args: argparse.Namespace) -> str:
    blue, ice, cyan, deep = "#1736D2", "#F4F7FF", "#8EE8FF", "#0E1C73"
    body = [rp.rect(0, 0, DESIGN_W, DESIGN_H, fill=blue), rp.rect(0, 0, DESIGN_W, DESIGN_H, fill="url(#dot-pattern)", opacity=0.22), _grid(30, 60, 1050, 1330, 90, ice, 0.13), _corner_frame(ice, margin=52, size=25, width=3), _label(78, 108, "03 / NETWORK OBJECT", cyan, 18), _txt(68, 256, args.title, 88, ice, max_units=15, max_lines=2, weight=900, line_height=100), _txt(76, 414, args.subtitle, 28, cyan, max_units=31, max_lines=2, weight=650), _tag_box(78, 488, 170, 46, "AGENT", deep, ice, cyan), _tag_box(838, 488, 164, 46, "SKILL", deep, ice, cyan)]
    points = [(190, 760), (354, 630), (542, 698), (744, 590), (906, 770), (742, 958), (520, 1030), (296, 940)]
    body += [rp.path("M " + " L ".join(f"{x} {y}" for x, y in points) + " Z", fill="#B5D4FF", opacity=0.22, stroke=ice, stroke_width=4), rp.path("M " + " L ".join(f"{x} {y}" for x, y in points) + " Z", fill="none", stroke=cyan, stroke_width=3, stroke_dasharray="4 10")]
    for a, b in [(0, 2), (1, 5), (2, 4), (3, 6), (4, 6), (0, 7), (2, 7), (5, 7)]:
        body.append(rp.line(points[a][0], points[a][1], points[b][0], points[b][1], ice, stroke_width=2, opacity=0.82))
    for idx, (x, y) in enumerate(points):
        body += [rp.circle(x, y, 15, fill=cyan), _label(x + 22, y + 7, f"{idx + 1:02d} → {x},{y}", ice, 14)]
    body += [_txt(78, 1182, "把观点连成网络，\n让每个节点都能继续生长", 38, ice, max_units=17, max_lines=2, weight=800, line_height=48), _pill(730, 1220, 240, 54, args.footer, cyan, deep)]
    return _doc(args, "".join(body), "ref-03 饱和蓝色网络 3D 结构：节点、连线和坐标标注")


def ref_04(args: argparse.Namespace) -> str:
    paper, gray, ink, yellow = "#EEECE4", "#777A78", "#171918", "#F2D83D"
    body = [rp.rect(0, 0, DESIGN_W, DESIGN_H, fill=paper), _grid(60, 80, 1020, 1370, 92, ink, 0.11), _dots(70, 520, 1010, 1330, 24, "#B9BAB4", 2, 0.48), _corner_frame(ink, margin=54, size=22, width=2), _pill(76, 104, 220, 52, "04 / IDEA LAB", yellow, ink), _txt(76, 246, args.title, 86, ink, max_units=16, max_lines=2, weight=900, line_height=96), _txt(80, 410, args.subtitle, 25, gray, max_units=34, max_lines=2, weight=500)]
    body += [_bulb(548, 800, 1.35, "#D1D1CB", ink), _label(116, 1136, "LIGHT / SIGNAL / INSIGHT", ink, 19), _txt(116, 1226, "从一个微小的想法，\n点亮一整套方法。", 36, ink, max_units=18, max_lines=2, weight=700, line_height=46), _pill(720, 1250, 250, 54, args.footer, ink, paper)]
    return _doc(args, "".join(body), "ref-04 浅色工程灯泡：档案纸底、技术网格与巨大灯泡主体")


def ref_05(args: argparse.Namespace) -> str:
    paper, ink, coral, mint, lavender, yellow = "#F4F1EA", "#24262C", "#F39A7C", "#80CDB4", "#B3A6E8", "#F6D778"
    body = [rp.rect(0, 0, DESIGN_W, DESIGN_H, fill=paper), _dots(30, 40, 1050, 1390, 38, "#D4D0C4", 2, 0.45), _corner_frame(coral, margin=48, size=22, width=3), _label(78, 108, "05 / SOFT OBJECTS", coral, 18), _txt(76, 244, args.title, 82, ink, max_units=15, max_lines=2, weight=900, line_height=94), _txt(80, 396, args.subtitle, 27, ink, max_units=33, max_lines=2, weight=500)]
    body += [_soft_blob(278, 690, 155, 112, mint, -12), _soft_blob(722, 690, 170, 126, lavender, 16), _soft_blob(506, 900, 220, 120, coral, -6), _puzzle_piece(264, 612, 190, 150, yellow, -12), _puzzle_piece(598, 614, 205, 150, mint, 15), _puzzle_piece(362, 868, 220, 156, lavender, -5), rp.circle(522, 794, 98, fill="#FFFFFF", opacity=0.78, stroke=ink, stroke_width=3), _txt(522, 808, "MAKE", 28, ink, max_units=6, max_lines=1, weight=900, anchor="middle"), _tag_box(82, 1116, 260, 52, "SOFT / ABSTRACT", ink, paper), _txt(88, 1220, "把抽象的灵感，\n变成可以触摸的形状。", 36, ink, max_units=17, max_lines=2, weight=800, line_height=45), _pill(728, 1254, 242, 54, args.footer, coral, paper)]
    return _doc(args, "".join(body), "ref-05 浅色软质拼图：奶油底、软体块与拼图轮廓")


def ref_06(args: argparse.Namespace) -> str:
    charcoal, steel, blue, orange, white = "#15191C", "#B6C0C5", "#73A9FF", "#FF8D57", "#F4F5F2"
    body = [rp.rect(0, 0, DESIGN_W, DESIGN_H, fill=charcoal), rp.rect(42, 56, 996, 1230, fill="#262C31", stroke=steel, stroke_width=6, rx=26), rp.rect(72, 88, 936, 1120, fill="#20252A", stroke="#56616A", stroke_width=2, rx=16), _grid(90, 210, 990, 1160, 78, steel, 0.17), _corner_frame(orange, margin=54, size=26, width=3), _label(88, 146, "06 / INDUSTRIAL SHOWCASE", orange, 18), _txt(86, 280, args.title, 78, white, max_units=16, max_lines=2, weight=900, line_height=90), _txt(92, 416, args.subtitle, 25, steel, max_units=34, max_lines=2, weight=500)]
    body += [_device(540, 740, 2.2, steel, "#36414A"), rp.rect(164, 992, 752, 96, fill="#0F1215", stroke=blue, stroke_width=3, rx=12), _label(198, 1030, "PRODUCT / MATERIAL / PROCESS", blue, 17), _txt(198, 1070, "模块化设备橱窗", 32, white, max_units=10, max_lines=1, weight=800), _tag_box(92, 1138, 188, 48, "01  OBJECT", orange, charcoal), _tag_box(792, 1138, 188, 48, "02  DETAIL", blue, charcoal), _pill(390, 1292, 300, 54, args.footer, orange, charcoal)]
    return _doc(args, "".join(body), "ref-06 工业设备橱窗：厚重外框、金属设备和产品铭牌")


def ref_07(args: argparse.Namespace) -> str:
    black, board, paper, green, tan = "#101011", "#3C3D3E", "#EDE6D8", "#64E17C", "#D3AA79"
    body = [rp.rect(0, 0, DESIGN_W, DESIGN_H, fill=black), _dots(70, 90, 1010, 1330, 43, "#050505", 5, 0.85), _corner_frame(tan, margin=54, size=24, width=2), _label(78, 112, "07 / CONTENT DIRECTION", tan, 18), _txt(78, 258, args.title, 78, paper, max_units=17, max_lines=2, weight=900, line_height=90), _txt(82, 400, args.subtitle, 26, tan, max_units=32, max_lines=2, weight=500)]
    body += [rp.rect(76, 496, 928, 660, fill=board, rx=26, stroke="#606060", stroke_width=2)]
    rows = [("DIRECTION 01", "展示作品，让想法被更多人看见。", green), ("DIRECTION 02", "记录过程，把经验变成可复用的内容。", tan), ("DIRECTION 03", "建立反馈，让下一次创作更清晰。", paper)]
    for idx, (head, detail, accent) in enumerate(rows):
        y = 556 + idx * 178
        body += [rp.rect(112, y, 210, 58, fill=black, stroke=accent, stroke_width=2), _txt(217, y + 39, head, 19, accent, max_units=15, max_lines=1, weight=800, anchor="middle"), rp.rect(360, y - 4, 570, 86, fill="#1D1D1E", rx=4), _txt(392, y + 30, detail, 22, paper, max_units=26, max_lines=2, weight=650, line_height=30), _label(392, y + 68, "EDITORIAL ACTION / 2026", accent, 14)]
    body += [_tag_box(84, 1202, 260, 50, "OPEN / MAKE / SHARE", green, black), _txt(88, 1302, "让内容方向先被看见，\n再被更多人一起完成。", 32, paper, max_units=18, max_lines=2, weight=700, line_height=40), _pill(722, 1310, 246, 54, args.footer, tan, black)]
    return _doc(args, "".join(body), "ref-07 穿孔板内容方向：深色圆孔板上的三条内容路径")


def ref_08(args: argparse.Namespace) -> str:
    bg, ink, red, yellow, blue, cyan = "#F1EFE7", "#232529", "#F04B64", "#F4E52F", "#4C88FF", "#6ED9C3"
    body = [rp.rect(0, 0, DESIGN_W, DESIGN_H, fill=bg), _dots(44, 52, 1036, 1380, 46, "#CFCBC0", 2, 0.58), _label(78, 112, "08 / COLOR GEOMETRY", red, 18), _txt(78, 254, args.title, 82, ink, max_units=15, max_lines=3, weight=900, line_height=92), _txt(82, 472, args.subtitle, 26, "#656761", max_units=32, max_lines=2, weight=500)]
    body += [rp.circle(192, 720, 180, fill=blue, opacity=0.85), rp.circle(816, 706, 216, fill=yellow, opacity=0.9), rp.circle(560, 1000, 242, fill=red, opacity=0.88), _soft_blob(530, 748, 220, 160, cyan, -18), rp.circle(312, 1008, 72, fill="#A977FF"), _tag_box(102, 1180, 250, 54, "ORIGINAL / PLAY", ink, bg), _txt(110, 1284, "用颜色制造节奏，\n用形状保持秩序。", 34, ink, max_units=17, max_lines=2, weight=800, line_height=43), _pill(730, 1308, 238, 54, args.footer, yellow, ink)]
    return _doc(args, "".join(body), "ref-08 浅色彩色几何圆：纸张底上的彩色圆形和软体几何")


def ref_09(args: argparse.Namespace) -> str:
    bg, warm, yellow, white, green = "#1F211F", "#C69C79", "#E9E24D", "#F4F0E8", "#A5BD86"
    body = [rp.rect(0, 0, DESIGN_W, DESIGN_H, fill=bg), _grid(60, 100, 1020, 1320, 96, "#5F5E55", 0.18), _corner_frame(warm, margin=54, size=22, width=2), _label(78, 114, "09 / AWARD LIST", yellow, 18), _txt(78, 264, args.title, 76, warm, max_units=16, max_lines=2, weight=800, line_height=88), _txt(82, 402, args.subtitle, 25, white, max_units=34, max_lines=2, weight=500)]
    entries = [("01", "荣誉与认可", warm), ("02", "创作基金", yellow), ("03", "持续流量", green), ("04", "特别舞台", "#D28DAA")]
    for idx, (num, label, accent) in enumerate(entries):
        y = 520 + idx * 158
        body += [rp.rect(92, y, 900, 112, fill="#080908", stroke=warm, stroke_width=2, rx=22), rp.circle(160, y + 56, 20, fill=accent), rp.circle(160, y + 56, 29, fill="none", stroke=yellow, stroke_width=4), _txt(224, y + 50, f"{num}  {label}", 30, white, max_units=14, max_lines=1, weight=800), rp.line(224, y + 76, 760, y + 76, accent, stroke_width=3), rp.circle(926, y + 56, 31, fill="none", stroke=accent, stroke_width=2, opacity=0.75)]
    body += [_label(96, 1192, "THE LIST CONTINUES", warm, 17), _txt(96, 1286, "把每一次完成，\n都留在下一次机会里。", 34, white, max_units=17, max_lines=2, weight=700, line_height=42), _pill(730, 1310, 238, 54, args.footer, yellow, bg)]
    return _doc(args, "".join(body), "ref-09 暖黑获奖列表：四条奖项式横向清单")


def ref_10(args: argparse.Namespace) -> str:
    black, white, red, muted = "#030304", "#F4F4F2", "#F3264D", "#9A9A9E"
    body = [rp.rect(0, 0, DESIGN_W, DESIGN_H, fill=black), rp.rect(62, 60, 956, 1320, fill="none", stroke="#131317", stroke_width=2), _label(86, 136, "10 / MINIMAL ORB", red, 18), _txt(78, 300, args.title, 108, white, max_units=13, max_lines=2, weight=400, line_height=120, letter_spacing=-3), _txt(84, 472, args.subtitle, 27, muted, max_units=32, max_lines=2, weight=400), rp.line(86, 538, 994, 538, "#25252B", stroke_width=1), rp.path("M 86 916 C 310 640 774 642 1002 920", fill="none", stroke=red, stroke_width=42, opacity=0.25, filter="url(#soft-glow)"), rp.path("M 86 916 C 310 640 774 642 1002 920", fill="none", stroke=red, stroke_width=10), rp.path("M 134 960 C 334 782 756 790 960 972", fill="none", stroke="#5D0C1C", stroke_width=2), _label(92, 688, "A SMALL SIGNAL FOR BIG IDEAS", muted, 16), _txt(92, 1172, "保持留白，\n让重点自己发光。", 42, white, max_units=13, max_lines=2, weight=600, line_height=50), _label(92, 1290, args.footer, red, 20, letter_spacing=1)]
    return _doc(args, "".join(body), "ref-10 极简红弧：黑底、巨大留白和一条发光红弧")


def ref_11(args: argparse.Namespace) -> str:
    black, white = "#1B1C20", "#F5F2E9"
    palette = ["#F62854", "#FFB914", "#37D583", "#5B75FF", "#B74DFF", "#F75B2A", "#21D7D1"]
    body = [rp.rect(0, 0, DESIGN_W, DESIGN_H, fill=white), _dots(34, 50, 1040, 1350, 54, "#C7C4BB", 2, 0.58), _label(78, 112, "11 / SYMBOL TYPE", black, 18), _txt(78, 242, args.title, 82, black, max_units=15, max_lines=2, weight=900, line_height=92), _txt(80, 386, args.subtitle, 25, "#696A6D", max_units=33, max_lines=2, weight=500)]
    symbols = ["+", "○", "◆", "✦", "×", "●", "◇", "◼", "✚", "△", "●", "✶", "□", "◒", "✧", "╳", "◈", "✚", "○", "◆", "✦", "×", "●", "◇"]
    for idx, symbol in enumerate(symbols):
        col, row = idx % 6, idx // 6
        x, y = 124 + col * 150, 586 + row * 110
        accent = palette[idx % len(palette)]
        body += [_txt(x, y, symbol, 62, accent, max_units=3, max_lines=1, weight=900), _label(x + 8, y + 34, "01+", accent, 13)]
    body += [rp.rect(74, 1012, 932, 2, fill="#B7B4AC"), _txt(80, 1138, "让符号自己组成语言，\n让内容拥有一套新字形。", 38, black, max_units=17, max_lines=2, weight=800, line_height=47), _pill(744, 1258, 226, 54, args.footer, "#F62854", white)]
    return _doc(args, "".join(body), "ref-11 浅色彩色符号拼字：彩色几何符号组成的字形海报")


def ref_12(args: argparse.Namespace) -> str:
    black, green, yellow, white, gray = "#020403", "#00C84F", "#FFB916", "#F4F7EF", "#8FA197"
    body = [rp.rect(0, 0, DESIGN_W, DESIGN_H, fill=black), _grid(40, 42, 1040, 1398, 54, "#234129", 0.22), _corner_frame(green, margin=50, size=24, width=2), _label(76, 110, "12 / TERMINAL SCHEDULE", green, 18), _txt(76, 246, args.title, 78, white, max_units=15, max_lines=2, weight=900, line_height=90), _txt(80, 390, args.subtitle, 26, green, max_units=33, max_lines=2, weight=500), _txt(84, 526, ">> TIMELINE", 32, yellow, max_units=15, max_lines=1, weight=900, letter_spacing=1)]
    lines = [("START", "05.08", "OPEN"), ("DEADLINE", "06.08 24:00", "LOCK"), ("RESULT", "07.01", "NEXT")]
    for idx, (label, value, status) in enumerate(lines):
        y = 612 + idx * 120
        body += [_label(92, y, label, gray, 17), _txt(320, y + 8, value, 44, green, max_units=15, max_lines=1, weight=800, letter_spacing=1), _pill(820, y - 34, 160, 46, status, yellow if idx == 1 else "#153421", black if idx == 1 else green)]
    body += [_txt(84, 1018, ">> REWARD", 32, yellow, max_units=15, max_lines=1, weight=900, letter_spacing=1), rp.rect(80, 1070, 920, 242, fill="#020403", stroke=yellow, stroke_width=3), rp.rect(80, 1070, 920, 56, fill=yellow), _txt(112, 1108, "REWARD TABLE", 20, black, max_units=14, max_lines=1, weight=900), _label(116, 1188, "流量激励", yellow, 20), _txt(344, 1188, "把一次参与，变成持续的作品机会。", 24, white, max_units=25, max_lines=2, weight=650), _label(116, 1262, "CALC / 100% ORIGINAL", gray, 15), _pill(736, 1260, 238, 50, args.footer, green, black)]
    return _doc(args, "".join(body), "ref-12 终端时间奖励表：绿色终端时间轴和奖励表格")


def ref_13(args: argparse.Namespace) -> str:
    black, purple, violet, white, blue = "#21182E", "#7B25F3", "#BD69FF", "#F4EEFA", "#5E8AFF"
    body = [rp.rect(0, 0, DESIGN_W, DESIGN_H, fill=white), _grid(48, 50, 1030, 1380, 76, purple, 0.12), _corner_frame(violet, margin=52, size=24, width=3), _label(78, 112, "13 / REQUIREMENT", blue, 18), _txt(78, 256, args.title, 84, black, max_units=15, max_lines=2, weight=900, line_height=96), _txt(82, 414, args.subtitle, 26, purple, max_units=33, max_lines=2, weight=600), _tag_box(82, 488, 250, 52, "REQUIREMENT / 01", purple, white)]
    reqs = [("PROMPT", "用一句话让想法拥有清晰方向。"), ("SKILL", "把工作里的痛点变成可复用能力。"), ("MODEL", "为自己的领域保留独特灵魂。")]
    for idx, (name, detail) in enumerate(reqs):
        y = 606 + idx * 172
        body += [_tag_box(88, y, 188, 52, f">> {name}", black, violet, purple), rp.rect(320, y - 8, 670, 84, fill="#FFFFFF", stroke=purple, stroke_width=2), _txt(354, y + 28, detail, 22, black, max_units=28, max_lines=2, weight=650, line_height=30), rp.line(320, y + 76, 940, y + 76, violet, stroke_width=2)]
    body += [_txt(86, 1170, ">> PROCESS", 32, blue, max_units=14, max_lines=1, weight=900), _txt(88, 1250, "明确要求，\n让创意进入下一步。", 34, black, max_units=16, max_lines=2, weight=800, line_height=43), _pill(746, 1290, 224, 54, args.footer, violet, black)]
    return _doc(args, "".join(body), "ref-13 浅紫需求表：浅色底、紫色边框和三条需求说明")


def ref_14(args: argparse.Namespace) -> str:
    paper, dark, purple, pink, lavender = "#F8F7F2", "#211D2B", "#7028DE", "#E64AA8", "#D4C7F5"
    body = [rp.rect(0, 0, DESIGN_W, DESIGN_H, fill=paper), _grid(36, 50, 1044, 1370, 96, "#DAD4E5", 0.32), _corner_frame(purple, margin=42, size=25, width=3), _label(78, 106, "14 / TECHNOLOGY COLLAGE", purple, 18), _txt(74, 240, args.title, 80, dark, max_units=15, max_lines=2, weight=900, line_height=90), _txt(80, 380, args.subtitle, 26, purple, max_units=31, max_lines=2, weight=600)]
    body += [rp.rect(94, 500, 438, 420, fill="#FFFFFF", stroke=purple, stroke_width=4), _grid(120, 520, 505, 900, 32, lavender, 0.45), _device(304, 720, 1.4, purple, "#EEE8FF"), rp.rect(542, 470, 402, 300, fill="#F4EDFF", stroke=pink, stroke_width=4), rp.circle(746, 620, 112, fill="none", stroke=purple, stroke_width=7), rp.path("M 640 620 L 720 548 L 828 680", fill="none", stroke=pink, stroke_width=5), rp.rect(534, 802, 446, 262, fill="#FFFFFF", stroke=pink, stroke_width=4), _label(568, 846, "SYSTEM NOTES", purple, 17), _txt(566, 918, "把技术、故事和\n细节放在同一张画布。", 31, dark, max_units=14, max_lines=2, weight=800, line_height=40), _tag_box(84, 1012, 260, 52, "PANEL / ORIGINAL", purple, paper), _txt(86, 1126, "白底也可以有\n强烈的科技感。", 38, dark, max_units=14, max_lines=2, weight=800, line_height=47), _pill(736, 1256, 230, 54, args.footer, pink, paper)]
    return _doc(args, "".join(body), "ref-14 白底紫粉科技拼贴：多个窗口和设备块的不对称版式")


def ref_15(args: argparse.Namespace) -> str:
    paper, ink, purple, magenta, gray = "#F6F5EF", "#17151D", "#6B29DB", "#B92A9D", "#C5C1CB"
    body = [rp.rect(0, 0, DESIGN_W, DESIGN_H, fill=paper), _dots(36, 36, 1044, 1400, 58, "#D6D1DA", 2, 0.45), _corner_frame(magenta, margin=56, size=25, width=3), _label(82, 110, "15 / STEP GUIDE", purple, 18), _txt(76, 264, args.title, 82, ink, max_units=15, max_lines=3, weight=900, line_height=92), _txt(82, 482, args.subtitle, 25, purple, max_units=31, max_lines=2, weight=600)]
    steps = [("STEP 1", "定格瞬间", "在一个真实场景里留下观察。"), ("STEP 2", "走心分享", "把过程和判断讲给别人听。"), ("STEP 3", "继续迭代", "带着反馈回到下一轮创作。")]
    for idx, (step, head, detail) in enumerate(steps):
        y = 586 + idx * 220
        body += [_label(100, y, step, magenta, 18), rp.rect(98, y + 28, 882, 142, fill="#FFFFFF", stroke=purple, stroke_width=3), _tag_box(116, y + 52, 208, 52, head, purple, paper), _txt(360, y + 88, detail, 23, ink, max_units=25, max_lines=2, weight=700, line_height=30), _arrow(854, y + 96, 930, y + 96, magenta, 3)]
    body += [_txt(86, 1280, "一页就能说清楚，\n下一步从哪里开始。", 34, ink, max_units=16, max_lines=2, weight=800, line_height=43), _pill(748, 1310, 220, 54, args.footer, magenta, paper)]
    return _doc(args, "".join(body), "ref-15 白底步骤指南：三步纵向流程与箭头指引")


def ref_16(args: argparse.Namespace) -> str:
    paper, ink, purple, pink, orange = "#F8F7F2", "#141319", "#6425D7", "#B82BAA", "#F07C50"
    body = [rp.rect(0, 0, DESIGN_W, DESIGN_H, fill=paper), _grid(40, 40, 1040, 1400, 82, "#DDD6E8", 0.33), _corner_frame(purple, margin=48, size=24, width=3), _label(82, 110, "16 / PROGRESSION MAP", purple, 18), _txt(76, 254, args.title, 78, ink, max_units=16, max_lines=2, weight=900, line_height=90), _txt(84, 410, args.subtitle, 25, purple, max_units=33, max_lines=2, weight=600), _tag_box(704, 148, 250, 54, "ADVANCED / 03", purple, paper)]
    tasks = [("基础版", "把一个想法说清楚。", purple), ("进阶版", "把过程变成可复用方法。", pink), ("特别版", "把反馈变成下一次机会。", orange)]
    for idx, (head, detail, accent) in enumerate(tasks):
        y = 560 + idx * 220
        body += [rp.rect(94, y, 890, 160, fill="#FFFFFF", stroke=accent, stroke_width=3), _tag_box(112, y + 28, 210, 54, head, accent, paper), _txt(366, y + 74, detail, 26, ink, max_units=22, max_lines=1, weight=800), _label(366, y + 116, f"TASK {idx + 1:02d} / MOVE FORWARD", accent, 16), rp.line(886, y + 52, 948, y + 52, accent, stroke_width=4), rp.line(918, y + 78, 948, y + 78, accent, stroke_width=4)]
    body += [_txt(94, 1260, "三个任务，\n让内容逐级长大。", 36, ink, max_units=14, max_lines=2, weight=800, line_height=44), _pill(746, 1310, 222, 54, args.footer, pink, paper)]
    return _doc(args, "".join(body), "ref-16 白底三任务进阶页：三张横向任务卡的升级结构")


def ref_17(args: argparse.Namespace) -> str:
    navy, blue, ice, green, black = "#07143D", "#2C61DD", "#F1F5FF", "#73E0A2", "#02050D"
    body = [rp.rect(0, 0, DESIGN_W, DESIGN_H, fill=navy), rp.rect(0, 0, DESIGN_W, DESIGN_H, fill="url(#dot-pattern)", opacity=0.16), _grid(54, 80, 1026, 1360, 72, ice, 0.13), _corner_frame(ice, margin=50, size=24, width=2), _label(78, 110, "17 / BIO-MECHANIC", green, 18), _txt(76, 246, args.title, 76, ice, max_units=16, max_lines=2, weight=900, line_height=90), _txt(82, 396, args.subtitle, 25, green, max_units=32, max_lines=2, weight=600)]
    # Angular robotic arm, deliberately original and free of logos or people.
    arm = rp.group(
        rp.path("M 228 1048 L 354 888 L 464 908 L 620 704 L 742 724 L 886 514", fill="none", stroke=blue, stroke_width=58, stroke_linecap="round", stroke_linejoin="round"),
        rp.path("M 228 1048 L 354 888 L 464 908 L 620 704 L 742 724 L 886 514", fill="none", stroke=ice, stroke_width=8, stroke_linecap="round", stroke_linejoin="round"),
        rp.circle(354, 888, 40, fill=black, stroke=green, stroke_width=6), rp.circle(620, 704, 42, fill=black, stroke=green, stroke_width=6), rp.circle(742, 724, 38, fill=black, stroke=green, stroke_width=6),
        rp.path("M 886 514 L 946 458 L 930 554 L 876 580 Z", fill=green, stroke=ice, stroke_width=5),
        rp.rect(160, 1030, 140, 74, fill=black, stroke=blue, stroke_width=4), _label(180, 1075, "BASE / 001", ice, 16),
    )
    body += [arm, _tag_box(94, 520, 180, 48, "JOINT / A", blue, ice), _tag_box(808, 458, 180, 48, "END / B", green, black), _label(112, 1168, "MOTION / FORCE / RESPONSE", green, 18), _txt(112, 1250, "把复杂动作，\n拆成可以理解的结构。", 34, ice, max_units=17, max_lines=2, weight=800, line_height=43), _pill(742, 1310, 226, 54, args.footer, blue, ice)]
    return _doc(args, "".join(body), "ref-17 蓝黑仿生机械臂：技术网格与原创机械关节")


def ref_18(args: argparse.Namespace) -> str:
    bg, blue, white, green, orange, pink = "#0C1B43", "#3C6DE0", "#F1F6FF", "#35D879", "#FFB832", "#F45E97"
    body = [rp.rect(0, 0, DESIGN_W, DESIGN_H, fill=bg), rp.rect(0, 0, DESIGN_W, DESIGN_H, fill="url(#dot-pattern)", opacity=0.13), _corner_frame(blue, margin=48, size=25, width=3), _label(78, 112, "18 / PIXEL ACTIVITY CARD", green, 18), _txt(76, 250, args.title, 74, white, max_units=16, max_lines=2, weight=900, line_height=88), _txt(80, 398, args.subtitle, 25, blue, max_units=33, max_lines=2, weight=600)]
    icons = [(178, 590, "✦", green), (540, 590, "◆", orange), (900, 590, "●", pink)]
    for x, y, icon, accent in icons:
        body += [rp.rect(x - 110, y - 100, 220, 200, fill="#162B61", stroke=accent, stroke_width=3), _txt(x, y + 24, icon, 96, accent, max_units=3, max_lines=1, weight=900, anchor="middle"), _label(x, y + 132, "#ORIGINAL", white, 15, anchor="middle")]
    body += [_tag_box(90, 844, 900, 88, "ACTIVITY / PARTICIPATE / SHARE", blue, white), rp.rect(92, 992, 896, 224, fill="#10275A", stroke=green, stroke_width=3, rx=20), _txt(132, 1064, "带着一个主题，\n发布你的原创作品。", 34, white, max_units=16, max_lines=2, weight=800, line_height=44), _label(132, 1158, "PIXEL RULE  /  01 + 01 + 01", orange, 17), _pill(748, 1302, 218, 54, args.footer, pink, white)]
    return _doc(args, "".join(body), "ref-18 像素图标活动卡：三枚像素符号与活动说明块")


def ref_19(args: argparse.Namespace) -> str:
    indigo, orange, cream, yellow = "#22256D", "#F36A43", "#F6F0D6", "#F2EB83"
    body = [rp.rect(0, 0, DESIGN_W, DESIGN_H, fill=indigo), _grid(40, 40, 1040, 1400, 86, cream, 0.12), rp.path("M 0 320 C 300 60 820 60 1080 320", fill="none", stroke=orange, stroke_width=3, stroke_dasharray="10 12", opacity=0.78), rp.path("M 0 1150 C 330 1400 760 1380 1080 1120", fill="none", stroke=yellow, stroke_width=3, stroke_dasharray="10 12", opacity=0.7), _corner_frame(orange, margin=52, size=24, width=3), _label(80, 112, "19 / PUBLIC COVER", yellow, 18), _tag_box(680, 96, 306, 56, "ORIGINAL EDITION", orange, cream), _txt(74, 324, args.title, 112, cream, max_units=12, max_lines=2, weight=900, line_height=124, letter_spacing=-4), _txt(78, 612, args.subtitle, 28, yellow, max_units=31, max_lines=3, weight=650, line_height=38)]
    body += [rp.circle(178, 800, 108, fill=orange, opacity=0.92), rp.circle(850, 900, 164, fill="#4249A5", stroke=yellow, stroke_width=4), _soft_blob(564, 912, 188, 104, orange, -8), rp.rect(130, 1046, 820, 2, fill=cream), _txt(144, 1152, "让创造被更多人看见", 44, cream, max_units=15, max_lines=1, weight=800), _label(144, 1222, "ORIGINAL / CREATIVE / PUBLIC", yellow, 17), _pill(720, 1306, 242, 54, args.footer, orange, cream)]
    return _doc(args, "".join(body), "ref-19 靛蓝橙色大字封面：巨型字块与弧线轨迹")


def ref_20(args: argparse.Namespace) -> str:
    indigo, orange, cream, yellow, purple = "#242977", "#FF7653", "#F4EFDF", "#E7D950", "#8D69D8"
    body = [rp.rect(0, 0, DESIGN_W, DESIGN_H, fill=cream), _grid(42, 42, 1038, 1398, 86, indigo, 0.1), rp.path("M 48 222 C 260 52 820 52 1032 222", fill="none", stroke=orange, stroke_width=3, stroke_dasharray="8 12"), _corner_frame(orange, margin=52, size=24, width=3), _label(80, 110, "20 / RULES & REWARDS", indigo, 18), _tag_box(680, 88, 300, 54, "ORIGINAL RULEBOOK", orange, cream), _txt(78, 266, args.title, 78, indigo, max_units=16, max_lines=2, weight=900, line_height=90), _txt(82, 412, args.subtitle, 25, orange, max_units=33, max_lines=2, weight=600)]
    body += [_tag_box(82, 520, 232, 54, "TIMELINE", orange, cream), _txt(84, 652, "01  START", 32, indigo, max_units=12, max_lines=1, weight=800), _txt(84, 710, "02  PUBLISH", 32, indigo, max_units=12, max_lines=1, weight=800), _txt(84, 768, "03  REVIEW", 32, indigo, max_units=12, max_lines=1, weight=800), rp.line(360, 548, 360, 824, orange, stroke_width=4), rp.circle(360, 596, 14, fill=yellow), rp.circle(360, 708, 14, fill=yellow), rp.circle(360, 820, 14, fill=yellow), rp.rect(430, 544, 530, 304, fill=indigo, stroke=orange, stroke_width=3), _label(466, 598, "REWARD", orange, 18), _txt(466, 678, "内容被看见，\n机会就会继续流动。", 33, cream, max_units=15, max_lines=2, weight=800, line_height=44), _label(466, 788, "ORIGINAL / FAIR / OPEN", yellow, 16), _tag_box(84, 968, 230, 54, "NOTES", purple, cream), rp.rect(86, 1046, 874, 190, fill="#FFFFFF", stroke=purple, stroke_width=3), _txt(120, 1126, "把规则写清楚，\n让参与变得更简单。", 34, indigo, max_units=16, max_lines=2, weight=800, line_height=44), _pill(740, 1304, 220, 54, args.footer, orange, cream)]
    return _doc(args, "".join(body), "ref-20 奶油纸张规则信息页：时间线、奖励块和规则说明")


def ref_21(args: argparse.Namespace) -> str:
    indigo, orange, cream, yellow, purple = "#252A7A", "#FC7551", "#F3E6D0", "#D8C94B", "#7E6BC8"
    body = [rp.rect(0, 0, DESIGN_W, DESIGN_H, fill=cream), _grid(42, 42, 1038, 1398, 90, indigo, 0.1), _corner_frame(indigo, margin=50, size=26, width=3), _label(80, 110, "21 / QUOTE COLLAGE", indigo, 18), _tag_box(700, 92, 260, 52, "ORIGINAL QUOTE", orange, cream), _txt(76, 250, args.title, 76, indigo, max_units=16, max_lines=2, weight=900, line_height=90), _txt(82, 400, args.subtitle, 25, orange, max_units=32, max_lines=2, weight=600)]
    body += [rp.rect(102, 544, 876, 500, fill=indigo, stroke=orange, stroke_width=4), _grid(136, 580, 946, 1010, 42, cream, 0.16), _txt(150, 670, "“", 110, orange, max_units=3, max_lines=1, weight=900), _txt(238, 692, "真正的壁垒在于\n把想法变成下一次行动。", 36, cream, max_units=19, max_lines=2, weight=800, line_height=48), _label(244, 850, "ORIGINAL NOTE / 2026", yellow, 16), _tag_box(692, 900, 222, 50, "SOURCE / OWN", purple, cream), rp.rect(154, 1112, 412, 102, fill=orange), _txt(184, 1172, "截图 / 片段 / 证据", 28, cream, max_units=9, max_lines=1, weight=900), rp.rect(610, 1112, 356, 102, fill="#FFFFFF", stroke=indigo, stroke_width=3), _txt(640, 1154, "把观点留在画面里", 24, indigo, max_units=11, max_lines=2, weight=800, line_height=31), _label(154, 1274, "COLLAGE / PROCESS / INSIGHT", indigo, 17), _pill(742, 1302, 218, 54, args.footer, orange, cream)]
    return _doc(args, "".join(body), "ref-21 暖纸引用拼贴：靛蓝引用窗口、引号与橙色标签")


RENDERERS: Dict[str, Callable[[argparse.Namespace], str]] = {
    "ref-01": ref_01,
    "ref-02": ref_02,
    "ref-03": ref_03,
    "ref-04": ref_04,
    "ref-05": ref_05,
    "ref-06": ref_06,
    "ref-07": ref_07,
    "ref-08": ref_08,
    "ref-09": ref_09,
    "ref-10": ref_10,
    "ref-11": ref_11,
    "ref-12": ref_12,
    "ref-13": ref_13,
    "ref-14": ref_14,
    "ref-15": ref_15,
    "ref-16": ref_16,
    "ref-17": ref_17,
    "ref-18": ref_18,
    "ref-19": ref_19,
    "ref-20": ref_20,
    "ref-21": ref_21,
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate 21 visibly different editable reference directions.")
    selector = parser.add_mutually_exclusive_group()
    selector.add_argument("--preset", choices=PRESETS, default="ref-01", help="render one reference direction")
    selector.add_argument("--all", action="store_true", help="render ref-01 through ref-21")
    parser.add_argument("--title", default="原创视觉方向", help="main title; use \\n for explicit line breaks")
    parser.add_argument("--subtitle", default="把内容整理成可以被看见的结构", help="subtitle")
    parser.add_argument("--footer", default="ORIGINAL STUDY", help="footer label")
    parser.add_argument("--output-dir", type=Path, default=Path("reference-catalog"), help="directory for SVG/PNG outputs")
    parser.add_argument("--hero-image", type=Path, help="optional local PNG/JPG; embedded only by ref-02")
    parser.add_argument("--png", action="store_true", help="also export PNG for a single preset")
    parser.add_argument("--force", action="store_true", help="allow replacing existing outputs")
    return parser


def _targets(presets: Sequence[str], outdir: Path, export_png: bool) -> List[Path]:
    targets: List[Path] = []
    for preset in presets:
        targets.append(outdir / f"{preset}.svg")
        if export_png:
            targets.append(outdir / f"{preset}.png")
    return targets


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    presets = PRESETS if args.all else (args.preset,)
    export_png = bool(args.all or args.png)
    if args.hero_image:
        if not args.hero_image.exists() or not args.hero_image.is_file():
            parser.error(f"找不到 --hero-image 文件：{args.hero_image}")
        if args.hero_image.suffix.lower() not in {".png", ".jpg", ".jpeg"}:
            parser.error("--hero-image 只接受 PNG/JPG/JPEG")
        args.hero_data_uri = rp.image_data_uri(args.hero_image)
    else:
        args.hero_data_uri = ""
    args.width = DESIGN_W
    args.height = DESIGN_H
    args.hero_remove_light = False
    args.style = "reference-catalog"
    outdir = args.output_dir
    targets = _targets(presets, outdir, export_png)
    if not args.force:
        existing = [path for path in targets if path.exists()]
        if existing:
            parser.error("输出文件已存在，为保护旧稿未覆盖：" + ", ".join(str(path) for path in existing[:5]) + (" ..." if len(existing) > 5 else "") + "；如需替换请显式使用 --force")
    outdir.mkdir(parents=True, exist_ok=True)
    any_png_failed = False
    for preset in presets:
        local_args = copy.copy(args)
        # A hero image is intentionally scoped to ref-02; all other references
        # use their own original SVG geometry so the catalog remains varied.
        if preset != "ref-02":
            local_args.hero_data_uri = ""
        svg_path = outdir / f"{preset}.svg"
        svg = RENDERERS[preset](local_args)
        svg_path.write_text(svg, encoding="utf-8", newline="\n")
        print(f"SVG 已生成：{svg_path}")
        if export_png:
            png_path = outdir / f"{preset}.png"
            ok, message = rp.export_png(svg_path, png_path, DESIGN_W, DESIGN_H)
            print(message, file=sys.stdout if ok else sys.stderr)
            if not ok:
                any_png_failed = True
    if args.hero_image and (args.all or args.preset != "ref-02"):
        print("提示：--hero-image 仅嵌入 ref-02，其余预设使用原创 SVG 几何主体。")
    return 2 if any_png_failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
