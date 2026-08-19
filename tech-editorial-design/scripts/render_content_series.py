#!/usr/bin/env python3
"""Render a consistent cover-to-content series for each reference direction.

The reference catalog is a one-to-one preview.  This renderer turns one of
those directions into an eight-page, editable SVG series while keeping each
preset's visual tokens stable across cover, section, body, quote, steps, data,
illustration, and ending pages.
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence, Tuple

import render_poster as rp
import render_reference_catalog as rc


DESIGN_W = 1080
DESIGN_H = 1440
PAGE_TYPES: Tuple[str, ...] = (
    "cover",
    "section",
    "body",
    "quote",
    "steps",
    "data",
    "illustration",
    "ending",
)


@dataclass(frozen=True)
class PresetSpec:
    ref_id: str
    alias: str
    chinese: str
    group: str
    motif: str
    tokens: Dict[str, object]


def _token_set(
    background: str,
    paper: str,
    ink: str,
    primary: str,
    secondary: str,
    grid: str,
    texture: str,
    title_position: str,
    motif: str,
    font_family: str = "Arial, 'Microsoft YaHei', 'Noto Sans CJK SC', sans-serif",
) -> Dict[str, object]:
    return {
        "background": background,
        "paper": paper,
        "ink": ink,
        "primary": primary,
        "secondary": secondary,
        "grid": grid,
        "texture": texture,
        "line_width": 3,
        "radius": 14,
        "font_family": font_family,
        "title_position": title_position,
        "motif": motif,
    }


def _make_spec(
    number: int,
    alias: str,
    chinese: str,
    group: str,
    motif: str,
    background: str,
    paper: str,
    ink: str,
    primary: str,
    secondary: str,
    grid: str,
    texture: str,
    title_position: str,
) -> PresetSpec:
    ref_id = f"ref-{number:02d}"
    return PresetSpec(
        ref_id=ref_id,
        alias=alias,
        chinese=chinese,
        group=group,
        motif=motif,
        tokens=_token_set(
            background,
            paper,
            ink,
            primary,
            secondary,
            grid,
            texture,
            title_position,
            motif,
        ),
    )


SPECS: Tuple[PresetSpec, ...] = (
    _make_spec(1, "neon-card-wall", "荧光卡片墙", "A 荧光硬件实验室", "cards", "#050606", "#FAFAF2", "#050606", "#C9FF58", "#A7E1FF", "#2E3830", "dots", "top-left"),
    _make_spec(2, "xray-device-lab", "透明设备实验室", "A 荧光硬件实验室", "device", "#050907", "#F0F6EE", "#050907", "#B8FF4A", "#70816D", "#263726", "grid", "top-left"),
    _make_spec(3, "blue-node-network", "蓝色节点网络", "B 数字蓝图与机械", "network", "#1736D2", "#F4F7FF", "#0E1C73", "#8EE8FF", "#B5D4FF", "#6D8CFF", "grid", "center"),
    _make_spec(4, "engineering-bulb-archive", "工程灯泡档案", "C 工业档案与极简", "bulb", "#EEECE4", "#171918", "#171918", "#F2D83D", "#777A78", "#B9BAB4", "halftone", "top-left"),
    _make_spec(5, "soft-puzzle", "柔彩拼图", "D 轻质彩色与符号", "puzzle", "#F4F1EA", "#24262C", "#24262C", "#80CDB4", "#F39A7C", "#D4D0C4", "paper", "top-center"),
    _make_spec(6, "industrial-showcase", "工业设备橱窗", "C 工业档案与极简", "showcase", "#15191C", "#F4F5F2", "#15191C", "#FF8D57", "#73A9FF", "#56616A", "grid", "top-left"),
    _make_spec(7, "content-direction-board", "内容方向板", "E 信息组织与规则", "board", "#101011", "#EDE6D8", "#101011", "#64E17C", "#D3AA79", "#3C3D3E", "perforated", "top-left"),
    _make_spec(8, "color-geometry", "彩色几何圆", "D 轻质彩色与符号", "geometry", "#F1EFE7", "#232529", "#232529", "#F04B64", "#656761", "#CFCBC0", "dots", "center"),
    _make_spec(9, "warm-award-list", "暖黑荣誉清单", "E 信息组织与规则", "award", "#1F211F", "#F4F0E8", "#1F211F", "#E9E24D", "#C69C79", "#5F5E55", "grid", "top-left"),
    _make_spec(10, "minimal-red-orbit", "极简红弧", "C 工业档案与极简", "orbit", "#030304", "#F4F4F2", "#030304", "#F3264D", "#9A9A9E", "#25252B", "plain", "center"),
    _make_spec(11, "color-symbol-language", "彩色符号语言", "D 轻质彩色与符号", "symbols", "#F5F2E9", "#1B1C20", "#1B1C20", "#1B1C20", "#696A6D", "#C7C4BB", "dots", "top-left"),
    _make_spec(12, "terminal-schedule", "终端时间表", "E 信息组织与规则", "terminal", "#020403", "#F4F7EF", "#020403", "#00C84F", "#FFB916", "#234129", "terminal", "top-left"),
    _make_spec(13, "lavender-requirement", "浅紫需求矩阵", "E 信息组织与规则", "requirement", "#F4EEFA", "#21182E", "#21182E", "#7B25F3", "#5E8AFF", "#D5C9E7", "paper", "top-left"),
    _make_spec(14, "editorial-tech-collage", "白底科技拼贴", "F 白底编辑器与纸张叙事", "collage", "#F8F7F2", "#211D2B", "#211D2B", "#7028DE", "#E64AA8", "#DAD4E5", "paper", "top-left"),
    _make_spec(15, "three-step-guide", "三步指南", "F 白底编辑器与纸张叙事", "steps", "#F6F5EF", "#17151D", "#17151D", "#6B29DB", "#B92A9D", "#D6D1DA", "dots", "top-left"),
    _make_spec(16, "progression-task-wall", "进阶任务墙", "F 白底编辑器与纸张叙事", "tasks", "#F8F7F2", "#141319", "#141319", "#6425D7", "#B82BAA", "#DDD6E8", "grid", "top-left"),
    _make_spec(17, "bionic-arm", "仿生机械臂", "B 数字蓝图与机械", "arm", "#07143D", "#F1F5FF", "#02050D", "#2C61DD", "#73E0A2", "#4663A4", "grid", "top-left"),
    _make_spec(18, "pixel-activity-card", "像素活动卡", "B 数字蓝图与机械", "pixel", "#0C1B43", "#F1F6FF", "#0C1B43", "#3C6DE0", "#35D879", "#28467C", "dots", "top-left"),
    _make_spec(19, "indigo-public-build", "靛蓝公开构建", "B 数字蓝图与机械", "public", "#22256D", "#F6F0D6", "#22256D", "#F36A43", "#F2EB83", "#5158A0", "grid", "top-left"),
    _make_spec(20, "cream-rulebook", "奶油规则页", "F 白底编辑器与纸张叙事", "rules", "#F4EFDF", "#242977", "#242977", "#FF7653", "#FF7653", "#5058A0", "grid", "top-right"),
    _make_spec(21, "warm-quote-collage", "暖纸引用拼贴", "F 白底编辑器与纸张叙事", "quote", "#F3E6D0", "#252A7A", "#252A7A", "#FC7551", "#FC7551", "#555DA7", "grid", "top-right"),
)

BY_ID: Dict[str, PresetSpec] = {spec.ref_id: spec for spec in SPECS}
BY_ALIAS: Dict[str, PresetSpec] = {spec.alias: spec for spec in SPECS}
BY_CHINESE: Dict[str, PresetSpec] = {spec.chinese: spec for spec in SPECS}


def resolve_preset(value: str) -> PresetSpec:
    normalized = value.strip().lower()
    if normalized in BY_ID:
        return BY_ID[normalized]
    if normalized in BY_ALIAS:
        return BY_ALIAS[normalized]
    if value.strip() in BY_CHINESE:
        return BY_CHINESE[value.strip()]
    raise ValueError(f"未知 preset：{value}；请使用 ref-01..ref-21、固定英文别名或中文名")


def _text(
    spec: PresetSpec,
    x: float,
    y: float,
    value: object,
    size: float,
    fill: Optional[str] = None,
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
    t = spec.tokens
    return rp.text_block(
        x,
        y,
        value,
        size=size,
        fill=fill or str(t["ink"]),
        max_units=max_units,
        max_lines=max_lines,
        weight=weight,
        family=str(t["font_family"]),
        line_height=line_height,
        anchor=anchor,
        letter_spacing=letter_spacing,
        opacity=opacity,
        transform=transform,
    )


def _label(spec: PresetSpec, x: float, y: float, value: object, fill: Optional[str] = None, size: float = 18, **kwargs: object) -> str:
    return _text(spec, x, y, value, size, fill, max_units=36, max_lines=1, weight=600, **kwargs)


def _luminance(color: str) -> float:
    """Return a small sRGB luminance estimate for contrast decisions."""
    value = color.strip().lstrip("#")
    if len(value) != 6:
        return 0.5
    try:
        channels = [int(value[index:index + 2], 16) / 255.0 for index in (0, 2, 4)]
    except ValueError:
        return 0.5
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


def _is_light_background(spec: PresetSpec) -> bool:
    return _luminance(str(spec.tokens["background"])) >= 0.55


def _on_background(spec: PresetSpec) -> str:
    """Choose readable title/body text on the preset background."""
    t = spec.tokens
    return str(t["ink"] if _is_light_background(spec) else t["paper"])


def _on_panel(spec: PresetSpec) -> str:
    """Choose readable text on the dark information panels."""
    t = spec.tokens
    return str(t["background"] if _is_light_background(spec) else t["paper"])


def _on_primary(spec: PresetSpec) -> str:
    """Choose readable text inside the primary accent pill or tag."""
    t = spec.tokens
    background = str(t["background"])
    primary = str(t["primary"])
    if _is_light_background(spec):
        return str(t["ink"] if _luminance(primary) >= 0.68 else background)
    return str(t["ink"] if _luminance(primary) >= 0.60 else t["paper"])


def _surface(spec: PresetSpec, *, include_frame: bool = True) -> str:
    t = spec.tokens
    bg = str(t["background"])
    grid = str(t["grid"])
    texture = str(t["texture"])
    parts: List[str] = [rp.rect(0, 0, DESIGN_W, DESIGN_H, fill=bg)]
    if texture == "grid":
        parts.append(rc._grid(40, 40, 1040, 1400, 82, grid, 0.18))
    elif texture == "dots":
        parts.append(rc._dots(38, 42, 1042, 1398, 48, grid, 2, 0.48))
    elif texture == "halftone":
        parts.append(rc._dots(42, 46, 1038, 1394, 26, grid, 2, 0.42))
        parts.append(rc._grid(58, 58, 1022, 1382, 90, grid, 0.16))
    elif texture == "perforated":
        parts.append(rc._dots(38, 44, 1042, 1398, 43, "#060606", 5, 0.72))
    elif texture == "terminal":
        parts.append(rc._grid(32, 42, 1048, 1398, 54, grid, 0.2))
    elif texture == "paper":
        parts.append(rc._dots(44, 44, 1036, 1390, 56, grid, 2, 0.36))
    elif texture == "plain":
        parts.append(rp.rect(58, 54, 964, 1332, fill="none", stroke=grid, stroke_width=2))
    if include_frame:
        parts.append(rc._corner_frame(str(t["primary"]), margin=48, size=24, width=float(t["line_width"])))
    return "".join(parts)


def _doc(spec: PresetSpec, args: argparse.Namespace, body: str, desc: str) -> str:
    local_args = copy.copy(args)
    local_args.style = "reference-catalog"
    local_args.width = DESIGN_W
    local_args.height = DESIGN_H
    return rp.base_svg(local_args, body, str(args.title), desc)


def _header(spec: PresetSpec, args: argparse.Namespace, page_label: str, *, title_y: float = 240, title_size: float = 82) -> str:
    t = spec.tokens
    primary, secondary = str(t["primary"]), str(t["secondary"])
    on_background = _on_background(spec)
    title_pos = str(t["title_position"])
    if title_pos == "center":
        title_x, anchor = 540, "middle"
    elif title_pos == "top-right":
        title_x, anchor = 1000, "end"
    else:
        title_x, anchor = 76, "start"
    return "".join(
        [
            _label(spec, 76, 108, f"{spec.ref_id} / {page_label.upper()}", primary, 18),
            _text(spec, title_x, title_y, args.title, title_size, on_background, max_units=16, max_lines=2, weight=900, line_height=title_size * 1.1, anchor=anchor),
            _text(spec, title_x, title_y + 138, args.subtitle, 26, secondary, max_units=32, max_lines=2, weight=600, line_height=36, anchor=anchor),
        ]
    )


def _footer(spec: PresetSpec, args: argparse.Namespace, y: float = 1320) -> str:
    t = spec.tokens
    return rc._pill(700, y, 270, 54, args.footer, str(t["primary"]), _on_primary(spec))


def _frame_panel(spec: PresetSpec, x: float, y: float, w: float, h: float, *, fill: Optional[str] = None, stroke: Optional[str] = None, radius: Optional[float] = None) -> str:
    t = spec.tokens
    return rp.rect(
        x,
        y,
        w,
        h,
        fill=fill or str(t["paper"]),
        stroke=stroke or str(t["primary"]),
        stroke_width=float(t["line_width"]),
        rx=radius if radius is not None else float(t["radius"]),
    )


def _normalized_points(x: float, y: float, w: float, h: float, points: Sequence[Tuple[float, float]]) -> List[Tuple[float, float]]:
    return [(x + px * w / 900, y + py * h / 500) for px, py in points]


def _token_box(spec: PresetSpec, x: float, y: float, w: float, h: float, value: object, fill: Optional[str] = None, text_fill: Optional[str] = None, stroke: Optional[str] = None) -> str:
    t = spec.tokens
    box_fill = fill or str(t["primary"])
    return rp.group(
        rp.rect(x, y, w, h, fill=box_fill, stroke=stroke or "none", stroke_width=float(t["line_width"]) if stroke else None, rx=float(t["radius"]) * 0.35),
        _text(spec, x + w / 2, y + h * 0.68, value, min(25, h * 0.43), text_fill or str(t["background"]), max_units=max(6, w / 23), max_lines=1, weight=800, anchor="middle"),
    )


def _motif(spec: PresetSpec, x: float, y: float, w: float, h: float, *, opacity: float = 1.0) -> str:
    """Return the preset's recurring subject language in a bounded area."""
    t = spec.tokens
    p, s, paper, bg, grid = str(t["primary"]), str(t["secondary"]), str(t["paper"]), str(t["background"]), str(t["grid"])
    sx, sy = w / 900, h / 500
    def px(value: float) -> float:
        return x + value * sx
    def py(value: float) -> float:
        return y + value * sy

    kind = spec.motif
    if kind == "cards":
        parts: List[str] = []
        accents = [p, s, "#FFBF7A", "#D39BFF", "#FF6F91", "#80FFD3"]
        for index in range(6):
            col, row = index % 3, index // 3
            cx, cy = px(70 + col * 300), py(40 + row * 230)
            parts.append(rp.rect(cx, cy, 230 * sx, 188 * sy, fill=bg, stroke=accents[index], stroke_width=3, rx=12))
            parts.append(rc._avatar(cx + 115 * sx, cy + 76 * sy, 48 * min(sx, sy), accents[index], "#17201B"))
            parts.append(rp.rect(cx, cy + 132 * sy, 230 * sx, 56 * sy, fill=accents[index]))
        return rp.group(*parts, opacity=opacity)
    if kind == "device":
        return rp.group(
            rc._device(px(450), py(242), min(sx, sy) * 1.75, p, "#122015"),
            rp.circle(px(450), py(142), 100 * min(sx, sy), fill="#DFFFB4", opacity=0.18),
            rp.path(f"M {px(80)} {py(430)} L {px(200)} {py(80)} L {px(700)} {py(80)} L {px(820)} {py(430)}", fill="none", stroke=p, stroke_width=2, stroke_dasharray="7 10"),
            opacity=opacity,
        )
    if kind == "network":
        points = _normalized_points(x, y, w, h, [(90, 300), (260, 120), (460, 180), (690, 80), (820, 300), (650, 450), (420, 480), (190, 430)])
        body = [rp.path("M " + " L ".join(f"{a} {b}" for a, b in points) + " Z", fill=s, opacity=0.22, stroke=paper, stroke_width=4)]
        for a, b in [(0, 2), (1, 5), (2, 4), (3, 6), (4, 6), (0, 7), (2, 7), (5, 7)]:
            body.append(rp.line(points[a][0], points[a][1], points[b][0], points[b][1], paper, stroke_width=2, opacity=0.84))
        for point in points:
            body.append(rp.circle(point[0], point[1], 13 * min(sx, sy), fill=p))
        return rp.group(*body, opacity=opacity)
    if kind == "bulb":
        return rp.group(
            rc._bulb(px(450), py(240), min(sx, sy) * 1.2, "#333333", paper),
            rc._dots(px(20), py(30), px(880), py(470), 25 * min(sx, sy), grid, 2, 0.4),
            opacity=opacity,
        )
    if kind == "puzzle":
        return rp.group(
            rc._soft_blob(px(258), py(206), 150 * sx, 90 * sy, s, -12),
            rc._soft_blob(px(650), py(250), 170 * sx, 108 * sy, p, 15),
            rc._soft_blob(px(470), py(390), 190 * sx, 90 * sy, "#F39A7C", -5),
            rc._puzzle_piece(px(212), py(100), 180 * sx, 124 * sy, "#F6D778", -12),
            rc._puzzle_piece(px(548), py(100), 190 * sx, 124 * sy, "#80CDB4", 15),
            opacity=opacity,
        )
    if kind == "showcase":
        return rp.group(
            rp.rect(px(80), py(55), 740 * sx, 380 * sy, fill="#20252A", stroke=s, stroke_width=4, rx=18),
            rc._device(px(450), py(230), min(sx, sy) * 1.55, paper, "#36414A"),
            rp.rect(px(180), py(400), 540 * sx, 40 * sy, fill="#0F1215", stroke=p, stroke_width=3, rx=8),
            opacity=opacity,
        )
    if kind == "board":
        return rp.group(
            rp.rect(px(45), py(55), 810 * sx, 390 * sy, fill="#3C3D3E", stroke=s, stroke_width=2, rx=18),
            rc._dots(px(65), py(75), px(835), py(420), 43 * min(sx, sy), "#050505", 4, 0.85),
            rp.rect(px(105), py(140), 660 * sx, 64 * sy, fill="#1D1D1E", stroke=p, stroke_width=2),
            rp.rect(px(105), py(244), 660 * sx, 64 * sy, fill="#1D1D1E", stroke=s, stroke_width=2),
            opacity=opacity,
        )
    if kind == "geometry":
        return rp.group(
            rp.circle(px(180), py(190), 132 * min(sx, sy), fill="#4C88FF"),
            rp.circle(px(720), py(170), 154 * min(sx, sy), fill="#F4E52F"),
            rp.circle(px(480), py(380), 172 * min(sx, sy), fill="#F04B64"),
            rc._soft_blob(px(470), py(220), 170 * sx, 108 * sy, "#6ED9C3", -18),
            opacity=opacity,
        )
    if kind == "award":
        parts = []
        for index, accent in enumerate((s, p, "#A5BD86", "#D28DAA")):
            cy = py(80 + index * 106)
            parts.extend([rp.rect(px(50), cy, 800 * sx, 78 * sy, fill="#080908", stroke=s, stroke_width=2, rx=18), rp.circle(px(112), cy + 39 * sy, 15 * min(sx, sy), fill=accent), rp.line(px(190), cy + 52 * sy, px(670), cy + 52 * sy, accent, stroke_width=3)])
        return rp.group(*parts, opacity=opacity)
    if kind == "orbit":
        return rp.group(
            rp.path(f"M {px(30)} {py(370)} C {px(260)} {py(80)} {px(700)} {py(80)} {px(870)} {py(380)}", fill="none", stroke=p, stroke_width=32 * min(sx, sy), opacity=0.26),
            rp.path(f"M {px(30)} {py(370)} C {px(260)} {py(80)} {px(700)} {py(80)} {px(870)} {py(380)}", fill="none", stroke=p, stroke_width=8 * min(sx, sy)),
            opacity=opacity,
        )
    if kind == "symbols":
        symbols = ["+", "○", "◆", "✦", "×", "●", "◇", "◼", "✚", "△", "✶", "□", "◒", "✧", "╳", "◈"]
        parts = []
        for index, symbol in enumerate(symbols):
            col, row = index % 8, index // 8
            accent = (p, s, "#FFB914", "#5B75FF", "#B74DFF", "#F75B2A", "#21D7D1")[index % 7]
            parts.append(_text(spec, px(55 + col * 112), py(200 + row * 120), symbol, 62 * min(sx, sy), accent, max_units=3, max_lines=1, weight=900))
        return rp.group(*parts, opacity=opacity)
    if kind == "terminal":
        return rp.group(
            rp.rect(px(55), py(46), 790 * sx, 400 * sy, fill="#020403", stroke=s, stroke_width=3),
            rp.rect(px(55), py(46), 790 * sx, 54 * sy, fill=p),
            _text(spec, px(86), py(86), "REWARD / DATA / SCHEDULE", 20 * min(sx, sy), bg, max_units=20, max_lines=1, weight=900),
            *[rp.line(px(75), py(148 + index * 76), px(820), py(148 + index * 76), s, stroke_width=2) for index in range(4)],
            opacity=opacity,
        )
    if kind == "requirement":
        return rp.group(
            rp.rect(px(50), py(45), 800 * sx, 400 * sy, fill="#1D0E40", stroke=p, stroke_width=3),
            *[_token_box(spec, px(76), py(90 + index * 104), 190 * sx, 54 * sy, label, p, bg, s) for index, label in enumerate(("PROMPT", "SKILL", "MODEL"))],
            *[rp.rect(px(320), py(90 + index * 104), 480 * sx, 54 * sy, fill="#2D165A", stroke=s, stroke_width=2) for index in range(3)],
            opacity=opacity,
        )
    if kind == "collage":
        return rp.group(
            rp.rect(px(55), py(46), 360 * sx, 390 * sy, fill=paper, stroke=p, stroke_width=4),
            rp.rect(px(445), py(36), 360 * sx, 260 * sy, fill="#F4EDFF", stroke=s, stroke_width=4),
            rp.rect(px(424), py(320), 406 * sx, 120 * sy, fill=paper, stroke=s, stroke_width=4),
            rc._device(px(235), py(240), min(sx, sy) * 1.0, p, "#EEE8FF"),
            rp.circle(px(625), py(165), 80 * min(sx, sy), fill="none", stroke=p, stroke_width=6),
            opacity=opacity,
        )
    if kind == "steps":
        return rp.group(
            *[rp.rect(px(55), py(56 + index * 140), 790 * sx, 94 * sy, fill=paper, stroke=p, stroke_width=3) for index in range(3)],
            *[_token_box(spec, px(76), py(76 + index * 140), 180 * sx, 52 * sy, f"STEP {index + 1}", p, bg) for index in range(3)],
            *[rc._arrow(px(710), py(104 + index * 140), px(800), py(104 + index * 140), s, 3) for index in range(3)],
            opacity=opacity,
        )
    if kind == "tasks":
        return rp.group(
            *[rp.rect(px(50), py(38 + index * 140), 800 * sx, 100 * sy, fill=paper, stroke=(p, s, "#F07C50")[index], stroke_width=3) for index in range(3)],
            *[_token_box(spec, px(70), py(58 + index * 140), 180 * sx, 58 * sy, label, (p, s, "#F07C50")[index], bg) for index, label in enumerate(("基础版", "进阶版", "特别版"))],
            opacity=opacity,
        )
    if kind == "arm":
        return rp.group(
            rp.path(f"M {px(120)} {py(410)} L {px(270)} {py(300)} L {px(420)} {py(330)} L {px(575)} {py(170)} L {px(700)} {py(190)} L {px(820)} {py(70)}", fill="none", stroke=p, stroke_width=54 * min(sx, sy), stroke_linecap="round", stroke_linejoin="round"),
            rp.path(f"M {px(120)} {py(410)} L {px(270)} {py(300)} L {px(420)} {py(330)} L {px(575)} {py(170)} L {px(700)} {py(190)} L {px(820)} {py(70)}", fill="none", stroke=paper, stroke_width=7 * min(sx, sy), stroke_linecap="round", stroke_linejoin="round"),
            *[rp.circle(px(a), py(b), 28 * min(sx, sy), fill=bg, stroke=s, stroke_width=5) for a, b in ((270, 300), (575, 170), (700, 190))],
            opacity=opacity,
        )
    if kind == "pixel":
        return rp.group(
            *[rp.rect(px(82 + index * 260), py(70), 190 * sx, 174 * sy, fill="#162B61", stroke=accent, stroke_width=3) for index, accent in enumerate((s, "#FFB832", "#F45E97"))],
            *[_text(spec, px(177 + index * 260), py(176), symbol, 88 * min(sx, sy), accent, max_units=3, max_lines=1, weight=900, anchor="middle") for index, (symbol, accent) in enumerate((("✦", s), ("◆", "#FFB832"), ("●", "#F45E97")))],
            opacity=opacity,
        )
    if kind == "public":
        return rp.group(
            rp.circle(px(160), py(166), 90 * min(sx, sy), fill=p),
            rp.circle(px(710), py(270), 144 * min(sx, sy), fill="#4249A5", stroke=s, stroke_width=4),
            rc._soft_blob(px(450), py(270), 170 * sx, 90 * sy, p, -8),
            rp.path(f"M {px(0)} {py(80)} C {px(240)} {py(0)} {px(650)} {py(0)} {px(900)} {py(80)}", fill="none", stroke=s, stroke_width=3, stroke_dasharray="10 12"),
            opacity=opacity,
        )
    if kind == "rules":
        return rp.group(
            rp.line(px(140), py(50), px(140), py(430), p, stroke_width=4),
            *[rp.circle(px(140), py(90 + index * 112), 14 * min(sx, sy), fill=s) for index in range(4)],
            rp.rect(px(260), py(44), 520 * sx, 300 * sy, fill="#151A59", stroke=p, stroke_width=3),
            opacity=opacity,
        )
    # quote-collage fallback and dedicated warm quote motif.
    return rp.group(
        rp.rect(px(50), py(45), 800 * sx, 390 * sy, fill=paper, stroke=p, stroke_width=4),
        _text(spec, px(104), py(164), "“", 100 * min(sx, sy), p, max_units=3, max_lines=1, weight=900),
        rp.rect(px(110), py(292), 430 * sx, 40 * sy, fill=s),
        rp.rect(px(580), py(292), 210 * sx, 40 * sy, fill=p),
        opacity=opacity,
    )


def render_cover(spec: PresetSpec, args: argparse.Namespace) -> str:
    t = spec.tokens
    primary, secondary = str(t["primary"]), str(t["secondary"])
    on_background = _on_background(spec)
    body = [_surface(spec), _header(spec, args, "cover", title_y=244, title_size=82)]
    if spec.ref_id == "ref-02" and getattr(args, "hero_data_uri", ""):
        hero_args = copy.copy(args)
        hero_args.hero_remove_light = bool(getattr(args, "hero_remove_light", False))
        body += [
            rp.hero_image(hero_args, 110, 540, 860, 500, opacity=0.88),
            rp.rect(110, 540, 860, 500, fill="none", stroke=primary, stroke_width=float(t["line_width"])),
        ]
    else:
        body.append(_motif(spec, 110, 540, 860, 500))
    body += [
        _label(spec, 78, 1120, f"{spec.chinese} / VISUAL DIRECTION", secondary, 18),
        _text(spec, 78, 1194, "封面与正文共享同一套视觉语言。", 30, on_background, max_units=24, max_lines=2, weight=750, line_height=40),
        _footer(spec, args, 1304),
    ]
    return _doc(spec, args, "".join(body), f"{spec.ref_id} {spec.chinese} cover")


def render_section(spec: PresetSpec, args: argparse.Namespace) -> str:
    t = spec.tokens
    primary, secondary = str(t["primary"]), str(t["secondary"])
    on_background = _on_background(spec)
    body = [
        _surface(spec),
        _label(spec, 78, 112, f"{spec.ref_id} / SECTION 01", primary, 18),
        _text(spec, 78, 300, "章节\n分界", 104, on_background, max_units=8, max_lines=2, weight=900, line_height=118),
        _text(spec, 82, 582, args.title, 28, secondary, max_units=28, max_lines=2, weight=650, line_height=38),
        rp.line(80, 640, 430, 640, primary, stroke_width=float(t["line_width"])),
        _motif(spec, 438, 690, 540, 360, opacity=0.9),
        _text(spec, 82, 1130, "01", 90, primary, max_units=4, max_lines=1, weight=900),
        _label(spec, 218, 1110, "从观察开始", secondary, 22),
        _label(spec, 218, 1152, "把素材变成可继续阅读的结构。", on_background, 18),
        _footer(spec, args),
    ]
    return _doc(spec, args, "".join(body), f"{spec.ref_id} section divider")


def render_body(spec: PresetSpec, args: argparse.Namespace) -> str:
    t = spec.tokens
    primary, secondary = str(t["primary"]), str(t["secondary"])
    on_background, panel_text = _on_background(spec), _on_panel(spec)
    panel_fill = str(t["paper"]) if _is_light_background(spec) else "#11151A"
    body = [
        _surface(spec),
        _label(spec, 78, 112, f"{spec.ref_id} / BODY 02", primary, 18),
        _text(spec, 78, 236, args.title, 68, on_background, max_units=17, max_lines=2, weight=900, line_height=78),
        _text(spec, 82, 370, args.subtitle, 25, secondary, max_units=32, max_lines=2, weight=600),
        _frame_panel(spec, 74, 494, 430, 552, fill=panel_fill, stroke=primary),
        _text(spec, 110, 580, "核心观点", 34, panel_text, max_units=10, max_lines=1, weight=850),
        _text(spec, 110, 676, "把一个复杂问题拆成\n可以被复用的步骤。", 34, panel_text, max_units=14, max_lines=2, weight=800, line_height=46),
        _label(spec, 110, 842, "01 / CONTEXT", secondary, 16),
        _label(spec, 110, 890, "02 / METHOD", secondary, 16),
        _label(spec, 110, 938, "03 / RESULT", secondary, 16),
        _motif(spec, 548, 500, 440, 540),
        _text(spec, 78, 1140, "正文页只保留必要信息，\n让主体和层级负责阅读节奏。", 32, on_background, max_units=19, max_lines=2, weight=700, line_height=42),
        _footer(spec, args),
    ]
    return _doc(spec, args, "".join(body), f"{spec.ref_id} body page")


def render_quote(spec: PresetSpec, args: argparse.Namespace) -> str:
    t = spec.tokens
    primary, secondary = str(t["primary"]), str(t["secondary"])
    on_background, panel_text = _on_background(spec), _on_panel(spec)
    panel_fill = str(t["paper"]) if _is_light_background(spec) else "#0C1015"
    body = [
        _surface(spec),
        _label(spec, 78, 112, f"{spec.ref_id} / QUOTE 03", primary, 18),
        _frame_panel(spec, 92, 292, 896, 640, fill=panel_fill, stroke=primary, radius=float(t["radius"]) * 1.4),
        _text(spec, 136, 454, "“", 136, primary, max_units=3, max_lines=1, weight=900),
        _text(spec, 216, 516, "真正重要的不是\n一次完成，而是\n下一次还能继续。", 54, panel_text, max_units=13, max_lines=3, weight=850, line_height=66),
        _label(spec, 220, 786, "ORIGINAL NOTE / 2026", secondary, 17),
        _motif(spec, 560, 792, 360, 190, opacity=0.44),
        _text(spec, 84, 1100, args.subtitle, 27, on_background, max_units=34, max_lines=2, weight=600),
        _footer(spec, args),
    ]
    return _doc(spec, args, "".join(body), f"{spec.ref_id} quote page")


def render_steps(spec: PresetSpec, args: argparse.Namespace) -> str:
    t = spec.tokens
    primary, secondary = str(t["primary"]), str(t["secondary"])
    on_background, panel_text = _on_background(spec), _on_panel(spec)
    card_fill = str(t["paper"]) if _is_light_background(spec) else "#11151A"
    body = [_surface(spec), _label(spec, 78, 112, f"{spec.ref_id} / STEPS 04", primary, 18), _text(spec, 78, 242, args.title, 70, on_background, max_units=16, max_lines=2, weight=900, line_height=80)]
    names = ("观察", "拆解", "复用")
    for index, name in enumerate(names):
        y = 410 + index * 220
        body += [
            _label(spec, 92, y, f"STEP {index + 1}", secondary, 18),
            _frame_panel(spec, 92, y + 30, 866, 138, fill=card_fill, stroke=primary),
            _token_box(spec, 118, y + 70, 184, 54, name, primary, str(t["background"])),
            _text(spec, 352, y + 106, ("先记录真实场景。", "再把信息拆成模块。", "最后沉淀成模板。")[index], 24, panel_text, max_units=23, max_lines=1, weight=720),
            rc._arrow(826, y + 100, 920, y + 100, secondary, 3),
        ]
    body += [_text(spec, 84, 1240, args.subtitle, 28, on_background, max_units=32, max_lines=2, weight=650), _footer(spec, args)]
    return _doc(spec, args, "".join(body), f"{spec.ref_id} steps page")


def render_data(spec: PresetSpec, args: argparse.Namespace) -> str:
    t = spec.tokens
    primary, secondary = str(t["primary"]), str(t["secondary"])
    on_background, panel_text = _on_background(spec), _on_panel(spec)
    panel_fill = str(t["paper"]) if _is_light_background(spec) else "#080B0B"
    body = [
        _surface(spec),
        _label(spec, 78, 112, f"{spec.ref_id} / DATA 05", primary, 18),
        _text(spec, 78, 246, "数据与\n证据", 80, on_background, max_units=8, max_lines=2, weight=900, line_height=92),
        _text(spec, 82, 478, args.subtitle, 25, secondary, max_units=32, max_lines=2, weight=600),
        _frame_panel(spec, 80, 594, 920, 536, fill=panel_fill, stroke=primary),
        _label(spec, 116, 654, "METRIC / 01", secondary, 16),
        _label(spec, 456, 654, "METRIC / 02", secondary, 16),
        _label(spec, 796, 654, "METRIC / 03", secondary, 16),
    ]
    values = (0.82, 0.58, 0.68)
    for index, ratio in enumerate(values):
        x = 118 + index * 340
        body += [
            _text(spec, x, 756, f"{int(ratio * 100):02d}", 72, panel_text, max_units=5, max_lines=1, weight=850),
            rp.rect(x, 818, 250, 16, fill=secondary, rx=8),
            rp.rect(x, 818, 250 * ratio, 16, fill=primary, rx=8),
            _label(spec, x, 884, ("结构清晰度", "信息密度", "复用潜力")[index], panel_text, 18),
        ]
    body += [_motif(spec, 190, 958, 700, 126, opacity=0.32), _footer(spec, args)]
    return _doc(spec, args, "".join(body), f"{spec.ref_id} data page")


def render_illustration(spec: PresetSpec, args: argparse.Namespace) -> str:
    t = spec.tokens
    primary, secondary = str(t["primary"]), str(t["secondary"])
    on_background = _on_background(spec)
    body = [
        _surface(spec),
        _label(spec, 78, 112, f"{spec.ref_id} / ILLUSTRATION 06", primary, 18),
        _text(spec, 78, 270, args.title, 52, on_background, max_units=19, max_lines=1, weight=800),
        _motif(spec, 84, 420, 912, 650, opacity=0.98),
        _label(spec, 84, 1170, "SUBJECT / MOTIF / ORIGINAL", secondary, 17),
        _footer(spec, args),
    ]
    return _doc(spec, args, "".join(body), f"{spec.ref_id} illustration page")


def render_ending(spec: PresetSpec, args: argparse.Namespace) -> str:
    t = spec.tokens
    primary, secondary = str(t["primary"]), str(t["secondary"])
    on_background = _on_background(spec)
    body = [
        _surface(spec),
        _label(spec, 78, 112, f"{spec.ref_id} / ENDING 07", primary, 18),
        _text(spec, 78, 330, "继续\n创造", 112, on_background, max_units=7, max_lines=2, weight=900, line_height=124),
        _text(spec, 82, 628, args.subtitle, 30, secondary, max_units=30, max_lines=2, weight=650, line_height=40),
        _motif(spec, 320, 730, 640, 360, opacity=0.68),
        _text(spec, 84, 1180, "把这一页带到下一次工作里。", 32, on_background, max_units=20, max_lines=1, weight=750),
        _label(spec, 84, 1240, "SERIES COMPLETE / NEXT ITERATION", secondary, 17),
        _footer(spec, args, 1304),
    ]
    return _doc(spec, args, "".join(body), f"{spec.ref_id} ending page")


PAGE_RENDERERS: Dict[str, Callable[[PresetSpec, argparse.Namespace], str]] = {
    "cover": render_cover,
    "section": render_section,
    "body": render_body,
    "quote": render_quote,
    "steps": render_steps,
    "data": render_data,
    "illustration": render_illustration,
    "ending": render_ending,
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate a consistent cover-to-content SVG series for a reference direction.")
    parser.add_argument("--preset", default="ref-01", help="ref-01..ref-21, fixed English alias, or Chinese preset name")
    parser.add_argument("--all-presets", action="store_true", help="render every preset; combine with --all-pages for all series")
    parser.add_argument("--all-pages", action="store_true", help="render cover, section, body, quote, steps, data, illustration, ending")
    parser.add_argument("--page-type", choices=PAGE_TYPES, default="cover", help="render one page type when --all-pages is not used")
    parser.add_argument("--title", default="原创视觉方向", help="main title; use \\n for explicit line breaks")
    parser.add_argument("--subtitle", default="把内容整理成可以被看见的结构", help="subtitle")
    parser.add_argument("--footer", default="ORIGINAL STUDY", help="footer label")
    parser.add_argument("--output-dir", type=Path, default=Path("content-series"), help="root output directory")
    parser.add_argument("--hero-image", type=Path, help="optional local PNG/JPG; cover ref-02 only")
    parser.add_argument("--hero-remove-light", action="store_true", help="apply the existing near-white hero treatment on ref-02 cover")
    parser.add_argument("--png", action="store_true", help="also export PNG beside every SVG")
    parser.add_argument("--force", action="store_true", help="allow replacing existing SVG/PNG/JSON outputs")
    return parser


def _page_filename(index: int, page_type: str) -> str:
    return f"{index:02d}-{page_type}"


def _preset_output_dir(root: Path, spec: PresetSpec) -> Path:
    return root / spec.ref_id


def _sidecar(spec: PresetSpec, args: argparse.Namespace, page_types: Sequence[str]) -> Dict[str, object]:
    return {
        "preset": spec.ref_id,
        "alias": spec.alias,
        "chinese_name": spec.chinese,
        "group": spec.group,
        "tokens": spec.tokens,
        "page_types": list(page_types),
        "title": args.title,
        "subtitle": args.subtitle,
        "footer": args.footer,
        "canvas": {"width": DESIGN_W, "height": DESIGN_H},
        "svg_source_of_truth": True,
        "hero_image": {
            "embedded_on": ["cover"] if spec.ref_id == "ref-02" and getattr(args, "hero_data_uri", "") else [],
            "read_only_data_uri": bool(spec.ref_id == "ref-02" and getattr(args, "hero_data_uri", "")),
        },
    }


def _validate_hero(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    if not args.hero_image:
        args.hero_data_uri = ""
        return
    if not args.hero_image.exists() or not args.hero_image.is_file():
        parser.error(f"找不到 --hero-image 文件：{args.hero_image}")
    if args.hero_image.suffix.lower() not in {".png", ".jpg", ".jpeg"}:
        parser.error("--hero-image 只接受 PNG/JPG/JPEG")
    args.hero_data_uri = rp.image_data_uri(args.hero_image)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        specs = SPECS if args.all_presets else (resolve_preset(args.preset),)
    except ValueError as exc:
        parser.error(str(exc))
        return 2
    if args.all_pages and args.page_type != "cover":
        parser.error("--all-pages 与 --page-type 不能同时指定")
    page_types = PAGE_TYPES if args.all_pages else (args.page_type,)
    _validate_hero(parser, args)
    args.hero_remove_light = bool(args.hero_remove_light)
    args.width = DESIGN_W
    args.height = DESIGN_H
    args.style = "reference-catalog"

    jobs: List[Tuple[PresetSpec, Path, Sequence[str]]] = []
    targets: List[Path] = []
    for spec in specs:
        preset_dir = _preset_output_dir(args.output_dir, spec)
        jobs.append((spec, preset_dir, page_types))
        targets.append(preset_dir / "series.json")
        for index, page_type in enumerate(page_types, start=1):
            base = preset_dir / f"{_page_filename(index, page_type)}.svg"
            targets.append(base)
            if args.png:
                targets.append(preset_dir / f"{_page_filename(index, page_type)}.png")
    if not args.force:
        existing = [path for path in targets if path.exists()]
        if existing:
            parser.error(
                "输出文件已存在，为保护旧稿未覆盖："
                + ", ".join(str(path) for path in existing[:6])
                + (" ..." if len(existing) > 6 else "")
                + "；如需替换请显式使用 --force"
            )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    png_failed = False
    for spec, preset_dir, selected_pages in jobs:
        preset_dir.mkdir(parents=True, exist_ok=True)
        local_args = copy.copy(args)
        # Only the matching ref-02 cover receives an external hero image.
        if spec.ref_id != "ref-02":
            local_args.hero_data_uri = ""
        for index, page_type in enumerate(selected_pages, start=1):
            svg_path = preset_dir / f"{_page_filename(index, page_type)}.svg"
            svg = PAGE_RENDERERS[page_type](spec, local_args)
            svg_path.write_text(svg, encoding="utf-8", newline="\n")
            print(f"SVG 已生成：{svg_path}")
            if args.png:
                png_path = preset_dir / f"{_page_filename(index, page_type)}.png"
                ok, message = rp.export_png(svg_path, png_path, DESIGN_W, DESIGN_H)
                print(message, file=sys.stdout if ok else sys.stderr)
                if not ok:
                    png_failed = True
        sidecar_path = preset_dir / "series.json"
        sidecar_path.write_text(
            json.dumps(_sidecar(spec, local_args, selected_pages), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        print(f"JSON 已生成：{sidecar_path}")
    if args.hero_image and (args.all_presets or args.preset not in {"ref-02", "xray-device-lab", "黑绿透明机器人设备"}):
        print("提示：--hero-image 仅嵌入 ref-02 的 cover 页面，其余 preset 或页面使用原创 SVG 主体。")
    return 2 if png_failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
