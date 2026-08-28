#!/usr/bin/env python3
"""Render one visual preset into dedicated mainstream platform canvases.

The existing render_content_series.py remains the stable 3:4 source.  This
companion renderer adds platform-specific compositions instead of stretching
that portrait canvas into unrelated aspect ratios.
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import render_content_series as cs
import render_poster as rp
import render_reference_catalog as rc


@dataclass(frozen=True)
class CanvasProfile:
    profile_id: str
    label: str
    width: int
    height: int
    kind: str
    ratio: str
    safe_area: Dict[str, int]
    reserved_zones: Dict[str, Dict[str, int]]
    allowed_pages: Tuple[str, ...]
    purpose: str


ALL_PAGES = cs.PAGE_TYPES
PROFILES: Tuple[CanvasProfile, ...] = (
    CanvasProfile(
        "xhs-portrait",
        "小红书竖版／通用图文",
        1080,
        1440,
        "portrait",
        "3:4",
        {"left": 64, "top": 72, "right": 64, "bottom": 72},
        {},
        ALL_PAGES,
        "小红书图文、公众号正文配图、3:4 竖版海报",
    ),
    CanvasProfile(
        "douyin-vertical",
        "抖音竖屏",
        1080,
        1920,
        "tall",
        "9:16",
        {"left": 72, "top": 170, "right": 72, "bottom": 210},
        {
            "top_platform_overlay": {"x": 0, "y": 0, "width": 1080, "height": 170},
            "bottom_platform_overlay": {"x": 0, "y": 1710, "width": 1080, "height": 210},
        },
        ALL_PAGES,
        "抖音竖屏封面、短视频章节帧、数据帧与结尾帧",
    ),
    CanvasProfile(
        "wechat-header",
        "公众号横图",
        900,
        383,
        "ultra-wide",
        "900:383",
        {"left": 42, "top": 32, "right": 42, "bottom": 32},
        {},
        ("cover",),
        "公众号文章头图；正文继续使用 xhs-portrait，分享卡使用 social-square",
    ),
    CanvasProfile(
        "social-square",
        "方形分享图",
        1080,
        1080,
        "square",
        "1:1",
        {"left": 64, "top": 64, "right": 64, "bottom": 64},
        {},
        ALL_PAGES,
        "公众号分享图、社交卡片、方形栏目封面",
    ),
    CanvasProfile(
        "landscape-video",
        "横版视频／宽屏封面",
        1920,
        1080,
        "wide",
        "16:9",
        {"left": 96, "top": 72, "right": 96, "bottom": 72},
        {},
        ALL_PAGES,
        "16:9 横版视频、演示封面与电脑端宽屏内容",
    ),
)

PROFILE_BY_ID = {profile.profile_id: profile for profile in PROFILES}


def resolve_profile(value: str) -> CanvasProfile:
    normalized = value.strip().lower()
    if normalized in PROFILE_BY_ID:
        return PROFILE_BY_ID[normalized]
    raise ValueError("未知 profile：" + value + "；请使用 " + "、".join(PROFILE_BY_ID))


def _corner_frame(profile: CanvasProfile, color: str, width: float = 3) -> str:
    m = profile.safe_area
    x1, y1 = float(m["left"]), float(m["top"])
    x2, y2 = float(profile.width - m["right"]), float(profile.height - m["bottom"])
    size = max(16.0, min(profile.width, profile.height) * 0.025)
    return "".join(
        (
            rp.line(x1, y1 + size, x1, y1, color, stroke_width=width),
            rp.line(x1, y1, x1 + size, y1, color, stroke_width=width),
            rp.line(x2, y1 + size, x2, y1, color, stroke_width=width),
            rp.line(x2, y1, x2 - size, y1, color, stroke_width=width),
            rp.line(x1, y2 - size, x1, y2, color, stroke_width=width),
            rp.line(x1, y2, x1 + size, y2, color, stroke_width=width),
            rp.line(x2, y2 - size, x2, y2, color, stroke_width=width),
            rp.line(x2, y2, x2 - size, y2, color, stroke_width=width),
        )
    )


def _surface(spec: cs.PresetSpec, profile: CanvasProfile) -> str:
    t = spec.tokens
    bg, grid = str(t["background"]), str(t["grid"])
    texture = str(t["texture"])
    left, top = profile.safe_area["left"], profile.safe_area["top"]
    right = profile.width - profile.safe_area["right"]
    bottom = profile.height - profile.safe_area["bottom"]
    step = max(26, round(min(profile.width, profile.height) / 13))
    parts: List[str] = [rp.rect(0, 0, profile.width, profile.height, fill=bg)]
    if texture in {"grid", "terminal"}:
        parts.append(rc._grid(left, top, right, bottom, step, grid, 0.20))
    elif texture in {"dots", "paper"}:
        parts.append(rc._dots(left, top, right, bottom, step, grid, 2, 0.38))
    elif texture == "halftone":
        parts.append(rc._dots(left, top, right, bottom, max(20, step // 2), grid, 2, 0.38))
        parts.append(rc._grid(left, top, right, bottom, step * 2, grid, 0.14))
    elif texture == "perforated":
        parts.append(rc._dots(left, top, right, bottom, step, "#060606", max(3, step / 10), 0.70))
    elif texture == "plain":
        parts.append(rp.rect(left, top, right - left, bottom - top, fill="none", stroke=grid, stroke_width=2))
    parts.append(_corner_frame(profile, str(t["primary"]), float(t["line_width"])))
    return "".join(parts)


def _doc(spec: cs.PresetSpec, profile: CanvasProfile, args: argparse.Namespace, body: str, desc: str) -> str:
    accessible_title = str(args.title).replace("\\r\\n", "\n").replace("\\r", "\n").replace("\\n", "\n")
    root_attrs = rp.attrs(
        width=profile.width,
        height=profile.height,
        viewBox=f"0 0 {profile.width} {profile.height}",
        preserve_aspect_ratio="xMidYMid meet",
        role="img",
        aria_label=accessible_title,
    )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" {root_attrs}>'
        + rp.tag("title", rp.esc(accessible_title))
        + rp.tag("desc", rp.esc(desc))
        + rp.defs_block("reference-catalog")
        + body
        + "</svg>"
    )


def _label(spec: cs.PresetSpec, x: float, y: float, value: object, fill: str, size: float) -> str:
    return cs._text(spec, x, y, value, size, fill, max_units=42, max_lines=1, weight=700, letter_spacing=0.6)


def _footer(spec: cs.PresetSpec, profile: CanvasProfile, args: argparse.Namespace) -> str:
    t = spec.tokens
    p = str(t["primary"])
    text_fill = cs._on_primary(spec)
    if profile.kind == "ultra-wide":
        x, y, w, h, size = profile.width - 260, profile.height - 62, 218, 34, 15
    elif profile.kind == "wide":
        x, y, w, h, size = profile.width - 430, profile.height - 112, 320, 50, 20
    else:
        x, y, w, h, size = profile.width - 390, profile.height - 124, 310, 52, 19
    return rp.group(
        rp.rect(x, y, w, h, fill=p, rx=h / 2),
        cs._text(spec, x + w / 2, y + h * 0.67, args.footer, size, text_fill, max_units=18, max_lines=1, weight=800, anchor="middle"),
    )


def _motif_or_hero(
    spec: cs.PresetSpec,
    args: argparse.Namespace,
    x: float,
    y: float,
    w: float,
    h: float,
    *,
    opacity: float = 1.0,
) -> str:
    if spec.ref_id == "ref-02" and getattr(args, "hero_data_uri", ""):
        hero_args = copy.copy(args)
        hero_args.hero_remove_light = bool(getattr(args, "hero_remove_light", False))
        return rp.group(
            rp.hero_image(hero_args, x, y, w, h, opacity=opacity),
            rp.rect(x, y, w, h, fill="none", stroke=str(spec.tokens["primary"]), stroke_width=float(spec.tokens["line_width"])),
        )
    return cs._motif(spec, x, y, w, h, opacity=opacity)


def _cover(spec: cs.PresetSpec, profile: CanvasProfile, args: argparse.Namespace) -> str:
    t = spec.tokens
    p, s, ink = str(t["primary"]), str(t["secondary"]), cs._on_background(spec)
    body: List[str] = [_surface(spec, profile)]
    if profile.kind == "ultra-wide":
        body += [
            _label(spec, 54, 58, f"{spec.ref_id} / WECHAT HEADER", p, 14),
            cs._text(spec, 54, 145, args.title, 52, ink, max_units=9, max_lines=2, weight=900, line_height=54),
            cs._text(spec, 58, 252, args.subtitle, 18, s, max_units=24, max_lines=2, weight=650, line_height=24),
            _motif_or_hero(spec, args, 540, 66, 304, 210),
        ]
    elif profile.kind == "wide":
        body += [
            _label(spec, 104, 126, f"{spec.ref_id} / LANDSCAPE VIDEO", p, 22),
            cs._text(spec, 104, 350, args.title, 112, ink, max_units=7, max_lines=2, weight=900, line_height=120),
            cs._text(spec, 112, 642, args.subtitle, 34, s, max_units=27, max_lines=2, weight=650, line_height=44),
            _motif_or_hero(spec, args, 1000, 154, 800, 650),
            _label(spec, 110, 920, profile.purpose, ink, 20),
        ]
    elif profile.kind == "square":
        body += [
            _label(spec, 72, 108, f"{spec.ref_id} / SOCIAL SQUARE", p, 18),
            cs._text(spec, 540, 236, args.title, 76, ink, max_units=11, max_lines=2, weight=900, line_height=84, anchor="middle"),
            cs._text(spec, 540, 376, args.subtitle, 27, s, max_units=28, max_lines=2, weight=650, line_height=36, anchor="middle"),
            _motif_or_hero(spec, args, 130, 460, 820, 420),
        ]
    else:  # douyin-vertical
        body += [
            _label(spec, 82, 222, f"{spec.ref_id} / DOUYIN VERTICAL", p, 19),
            cs._text(spec, 82, 426, args.title, 94, ink, max_units=9, max_lines=2, weight=900, line_height=104),
            cs._text(spec, 86, 660, args.subtitle, 31, s, max_units=30, max_lines=2, weight=650, line_height=42),
            _motif_or_hero(spec, args, 110, 790, 860, 720),
            _label(spec, 86, 1650, "TITLE / SUBJECT / SUBTITLE 均位于竖屏安全区", ink, 17),
        ]
    body.append(_footer(spec, profile, args))
    return _doc(spec, profile, args, "".join(body), f"{spec.ref_id} {profile.profile_id} cover")


def _section(spec: cs.PresetSpec, profile: CanvasProfile, args: argparse.Namespace) -> str:
    p, s, ink = str(spec.tokens["primary"]), str(spec.tokens["secondary"]), cs._on_background(spec)
    body: List[str] = [_surface(spec, profile)]
    if profile.kind == "wide":
        body += [
            _label(spec, 110, 130, f"{spec.ref_id} / SECTION 01", p, 22),
            cs._text(spec, 110, 430, "章节\n分界", 128, ink, max_units=7, max_lines=2, weight=900, line_height=138),
            cs._text(spec, 118, 770, args.title, 34, s, max_units=28, max_lines=2, weight=700),
            _motif_or_hero(spec, args, 1000, 180, 760, 640, opacity=0.88),
        ]
    elif profile.kind == "square":
        body += [
            _label(spec, 72, 108, f"{spec.ref_id} / SECTION 01", p, 18),
            cs._text(spec, 84, 330, "章节\n分界", 112, ink, max_units=7, max_lines=2, weight=900, line_height=120),
            _motif_or_hero(spec, args, 470, 300, 510, 420, opacity=0.86),
            cs._text(spec, 90, 800, args.title, 30, s, max_units=28, max_lines=2, weight=700),
        ]
    else:
        body += [
            _label(spec, 82, 220, f"{spec.ref_id} / SECTION 01", p, 19),
            cs._text(spec, 82, 560, "章节\n分界", 124, ink, max_units=7, max_lines=2, weight=900, line_height=136),
            cs._text(spec, 88, 890, args.title, 32, s, max_units=28, max_lines=2, weight=700),
            _motif_or_hero(spec, args, 300, 1040, 680, 520, opacity=0.88),
        ]
    body.append(_footer(spec, profile, args))
    return _doc(spec, profile, args, "".join(body), f"{spec.ref_id} {profile.profile_id} section")


def _body_page(spec: cs.PresetSpec, profile: CanvasProfile, args: argparse.Namespace) -> str:
    t = spec.tokens
    p, s, ink, panel_text = str(t["primary"]), str(t["secondary"]), cs._on_background(spec), cs._on_panel(spec)
    panel_fill = str(t["paper"]) if cs._is_light_background(spec) else "#11151A"
    body: List[str] = [_surface(spec, profile)]
    if profile.kind == "wide":
        body += [
            _label(spec, 104, 120, f"{spec.ref_id} / BODY 02", p, 21),
            cs._text(spec, 104, 280, args.title, 74, ink, max_units=17, max_lines=2, weight=900, line_height=82),
            cs._frame_panel(spec, 104, 470, 720, 390, fill=panel_fill, stroke=p),
            cs._text(spec, 150, 560, "核心观点", 38, panel_text, max_units=10, max_lines=1, weight=850),
            cs._text(spec, 150, 670, "把复杂问题拆成\n可以复用的步骤。", 36, panel_text, max_units=17, max_lines=2, weight=780, line_height=48),
            _motif_or_hero(spec, args, 940, 240, 820, 620),
        ]
    elif profile.kind == "square":
        body += [
            _label(spec, 72, 104, f"{spec.ref_id} / BODY 02", p, 18),
            cs._text(spec, 72, 230, args.title, 64, ink, max_units=15, max_lines=2, weight=900, line_height=72),
            cs._frame_panel(spec, 72, 390, 456, 450, fill=panel_fill, stroke=p),
            cs._text(spec, 108, 474, "核心观点", 32, panel_text, max_units=10, max_lines=1, weight=850),
            cs._text(spec, 108, 574, "把复杂问题拆成\n可以复用的步骤。", 30, panel_text, max_units=14, max_lines=2, weight=780, line_height=41),
            _motif_or_hero(spec, args, 568, 410, 430, 410),
        ]
    else:
        body += [
            _label(spec, 82, 218, f"{spec.ref_id} / BODY 02", p, 19),
            cs._text(spec, 82, 390, args.title, 76, ink, max_units=16, max_lines=2, weight=900, line_height=84),
            cs._frame_panel(spec, 82, 620, 916, 500, fill=panel_fill, stroke=p),
            cs._text(spec, 128, 716, "核心观点", 38, panel_text, max_units=10, max_lines=1, weight=850),
            cs._text(spec, 128, 836, "把复杂问题拆成\n可以复用的步骤。", 38, panel_text, max_units=17, max_lines=2, weight=780, line_height=50),
            _motif_or_hero(spec, args, 160, 1190, 760, 420),
        ]
    body.append(_footer(spec, profile, args))
    return _doc(spec, profile, args, "".join(body), f"{spec.ref_id} {profile.profile_id} body")


def _quote(spec: cs.PresetSpec, profile: CanvasProfile, args: argparse.Namespace) -> str:
    t = spec.tokens
    p, s, ink, panel_text = str(t["primary"]), str(t["secondary"]), cs._on_background(spec), cs._on_panel(spec)
    panel_fill = str(t["paper"]) if cs._is_light_background(spec) else "#0C1015"
    body: List[str] = [_surface(spec, profile)]
    if profile.kind == "wide":
        x, y, w, h, quote_x, quote_y, size = 160, 200, 1600, 650, 290, 390, 70
    elif profile.kind == "square":
        x, y, w, h, quote_x, quote_y, size = 90, 220, 900, 650, 180, 410, 54
    else:
        x, y, w, h, quote_x, quote_y, size = 86, 440, 908, 920, 170, 700, 58
    body += [
        _label(spec, profile.safe_area["left"] + 10, profile.safe_area["top"] + 50, f"{spec.ref_id} / QUOTE", p, 19),
        cs._frame_panel(spec, x, y, w, h, fill=panel_fill, stroke=p),
        cs._text(spec, quote_x - 70, quote_y - 50, "“", size * 1.8, p, max_units=2, max_lines=1, weight=900),
        cs._text(spec, quote_x, quote_y, "真正重要的不是一次完成，\n而是下一次还能继续。", size, panel_text, max_units=22, max_lines=3, weight=850, line_height=size * 1.22),
        _label(spec, quote_x, quote_y + size * 3.1, "ORIGINAL NOTE / 2026", s, max(16, size * 0.28)),
        _motif_or_hero(spec, args, x + w * 0.60, y + h * 0.62, w * 0.33, h * 0.24, opacity=0.38),
        _footer(spec, profile, args),
    ]
    return _doc(spec, profile, args, "".join(body), f"{spec.ref_id} {profile.profile_id} quote")


def _steps(spec: cs.PresetSpec, profile: CanvasProfile, args: argparse.Namespace) -> str:
    t = spec.tokens
    p, s, ink, panel_text = str(t["primary"]), str(t["secondary"]), cs._on_background(spec), cs._on_panel(spec)
    card_fill = str(t["paper"]) if cs._is_light_background(spec) else "#11151A"
    body: List[str] = [_surface(spec, profile)]
    names = ("观察", "拆解", "复用")
    notes = ("先记录真实场景。", "再把信息拆成模块。", "最后沉淀成模板。")
    if profile.kind == "wide":
        body += [_label(spec, 104, 120, f"{spec.ref_id} / STEPS", p, 21), cs._text(spec, 104, 280, args.title, 72, ink, max_units=18, max_lines=2, weight=900)]
        for index, name in enumerate(names):
            x = 104 + index * 590
            body += [
                cs._frame_panel(spec, x, 470, 500, 330, fill=card_fill, stroke=p),
                cs._text(spec, x + 44, 560, f"0{index + 1}", 54, p, max_units=4, max_lines=1, weight=900),
                cs._text(spec, x + 44, 650, name, 38, panel_text, max_units=7, max_lines=1, weight=850),
                cs._text(spec, x + 44, 724, notes[index], 24, panel_text, max_units=18, max_lines=2, weight=650),
            ]
    else:
        top = 340 if profile.kind == "square" else 500
        gap = 210 if profile.kind == "square" else 320
        card_h = 150 if profile.kind == "square" else 220
        body += [
            _label(spec, 76, 108 if profile.kind == "square" else 220, f"{spec.ref_id} / STEPS", p, 19),
            cs._text(spec, 76, 248 if profile.kind == "square" else 390, args.title, 66 if profile.kind == "square" else 76, ink, max_units=17, max_lines=2, weight=900),
        ]
        for index, name in enumerate(names):
            y = top + index * gap
            body += [
                cs._frame_panel(spec, 80, y, profile.width - 160, card_h, fill=card_fill, stroke=p),
                cs._text(spec, 120, y + card_h * 0.58, f"0{index + 1}", 42, p, max_units=4, max_lines=1, weight=900),
                cs._text(spec, 250, y + card_h * 0.58, name, 34, panel_text, max_units=7, max_lines=1, weight=850),
                cs._text(spec, 450, y + card_h * 0.58, notes[index], 23, panel_text, max_units=19, max_lines=2, weight=650),
            ]
    body.append(_footer(spec, profile, args))
    return _doc(spec, profile, args, "".join(body), f"{spec.ref_id} {profile.profile_id} steps")


def _data(spec: cs.PresetSpec, profile: CanvasProfile, args: argparse.Namespace) -> str:
    t = spec.tokens
    p, s, ink, panel_text = str(t["primary"]), str(t["secondary"]), cs._on_background(spec), cs._on_panel(spec)
    panel_fill = str(t["paper"]) if cs._is_light_background(spec) else "#080B0B"
    body: List[str] = [_surface(spec, profile)]
    values = ((82, "结构清晰度"), (57, "信息密度"), (68, "复用潜力"))
    if profile.kind == "wide":
        body += [_label(spec, 104, 120, f"{spec.ref_id} / DATA", p, 21), cs._text(spec, 104, 300, "数据与证据", 78, ink, max_units=12, max_lines=1, weight=900)]
        for index, (value, label) in enumerate(values):
            x = 104 + index * 590
            body += [
                cs._frame_panel(spec, x, 470, 500, 320, fill=panel_fill, stroke=p),
                cs._text(spec, x + 44, 600, str(value), 86, panel_text, max_units=5, max_lines=1, weight=900),
                rp.rect(x + 44, 660, 400, 18, fill=s, rx=9),
                rp.rect(x + 44, 660, 400 * value / 100, 18, fill=p, rx=9),
                cs._text(spec, x + 44, 738, label, 25, panel_text, max_units=12, max_lines=1, weight=700),
            ]
    else:
        body += [
            _label(spec, 76, 108 if profile.kind == "square" else 220, f"{spec.ref_id} / DATA", p, 19),
            cs._text(spec, 76, 250 if profile.kind == "square" else 410, "数据与证据", 66 if profile.kind == "square" else 80, ink, max_units=12, max_lines=1, weight=900),
        ]
        top = 350 if profile.kind == "square" else 580
        gap = 190 if profile.kind == "square" else 310
        h = 150 if profile.kind == "square" else 220
        for index, (value, label) in enumerate(values):
            y = top + index * gap
            body += [
                cs._frame_panel(spec, 80, y, profile.width - 160, h, fill=panel_fill, stroke=p),
                cs._text(spec, 124, y + h * 0.60, str(value), 58, panel_text, max_units=5, max_lines=1, weight=900),
                rp.rect(310, y + h * 0.47, 540, 16, fill=s, rx=8),
                rp.rect(310, y + h * 0.47, 540 * value / 100, 16, fill=p, rx=8),
                cs._text(spec, 310, y + h * 0.76, label, 22, panel_text, max_units=12, max_lines=1, weight=700),
            ]
    body.append(_footer(spec, profile, args))
    return _doc(spec, profile, args, "".join(body), f"{spec.ref_id} {profile.profile_id} data")


def _illustration(spec: cs.PresetSpec, profile: CanvasProfile, args: argparse.Namespace) -> str:
    p, s, ink = str(spec.tokens["primary"]), str(spec.tokens["secondary"]), cs._on_background(spec)
    body: List[str] = [_surface(spec, profile)]
    if profile.kind == "wide":
        body += [
            _label(spec, 104, 120, f"{spec.ref_id} / ILLUSTRATION", p, 21),
            cs._text(spec, 104, 300, args.title, 72, ink, max_units=18, max_lines=2, weight=900),
            _motif_or_hero(spec, args, 820, 150, 980, 760),
            _label(spec, 108, 820, "SUBJECT / MOTIF / ORIGINAL", s, 20),
        ]
    elif profile.kind == "square":
        body += [
            _label(spec, 72, 106, f"{spec.ref_id} / ILLUSTRATION", p, 18),
            cs._text(spec, 72, 244, args.title, 62, ink, max_units=17, max_lines=2, weight=900),
            _motif_or_hero(spec, args, 90, 380, 900, 520),
        ]
    else:
        body += [
            _label(spec, 82, 220, f"{spec.ref_id} / ILLUSTRATION", p, 19),
            cs._text(spec, 82, 420, args.title, 74, ink, max_units=17, max_lines=2, weight=900),
            _motif_or_hero(spec, args, 88, 650, 904, 850),
            _label(spec, 88, 1600, "SUBJECT / MOTIF / ORIGINAL", s, 18),
        ]
    body.append(_footer(spec, profile, args))
    return _doc(spec, profile, args, "".join(body), f"{spec.ref_id} {profile.profile_id} illustration")


def _ending(spec: cs.PresetSpec, profile: CanvasProfile, args: argparse.Namespace) -> str:
    p, s, ink = str(spec.tokens["primary"]), str(spec.tokens["secondary"]), cs._on_background(spec)
    body: List[str] = [_surface(spec, profile)]
    if profile.kind == "wide":
        body += [
            _label(spec, 104, 122, f"{spec.ref_id} / ENDING", p, 21),
            cs._text(spec, 104, 430, "继续创造", 126, ink, max_units=8, max_lines=1, weight=900),
            cs._text(spec, 112, 620, args.subtitle, 34, s, max_units=30, max_lines=2, weight=650),
            _motif_or_hero(spec, args, 1120, 180, 650, 620, opacity=0.72),
        ]
    elif profile.kind == "square":
        body += [
            _label(spec, 72, 106, f"{spec.ref_id} / ENDING", p, 18),
            cs._text(spec, 540, 350, "继续\n创造", 104, ink, max_units=7, max_lines=2, weight=900, line_height=112, anchor="middle"),
            _motif_or_hero(spec, args, 260, 530, 560, 310, opacity=0.70),
        ]
    else:
        body += [
            _label(spec, 82, 220, f"{spec.ref_id} / ENDING", p, 19),
            cs._text(spec, 82, 620, "继续\n创造", 132, ink, max_units=7, max_lines=2, weight=900, line_height=142),
            cs._text(spec, 88, 1000, args.subtitle, 32, s, max_units=30, max_lines=2, weight=650),
            _motif_or_hero(spec, args, 300, 1180, 680, 430, opacity=0.70),
        ]
    body.append(_footer(spec, profile, args))
    return _doc(spec, profile, args, "".join(body), f"{spec.ref_id} {profile.profile_id} ending")


PLATFORM_RENDERERS = {
    "cover": _cover,
    "section": _section,
    "body": _body_page,
    "quote": _quote,
    "steps": _steps,
    "data": _data,
    "illustration": _illustration,
    "ending": _ending,
}


def render_page(spec: cs.PresetSpec, profile: CanvasProfile, page_type: str, args: argparse.Namespace) -> str:
    if profile.profile_id == "xhs-portrait":
        return cs.PAGE_RENDERERS[page_type](spec, args)
    return PLATFORM_RENDERERS[page_type](spec, profile, args)


def _sidecar(spec: cs.PresetSpec, profile: CanvasProfile, args: argparse.Namespace, page_types: Sequence[str]) -> Dict[str, object]:
    return {
        "preset": spec.ref_id,
        "alias": spec.alias,
        "chinese_name": spec.chinese,
        "group": spec.group,
        "tokens": spec.tokens,
        "profile": profile.profile_id,
        "platform_profile": profile.profile_id,
        "profile_label": profile.label,
        "purpose": profile.purpose,
        "canvas": {"width": profile.width, "height": profile.height},
        "ratio": profile.ratio,
        "safe_area": profile.safe_area,
        "safe_zones": {"content": profile.safe_area},
        "reserved_zones": profile.reserved_zones,
        "page_types": list(page_types),
        "title": args.title,
        "subtitle": args.subtitle,
        "footer": args.footer,
        "dedicated_layout": True,
        "stretched_from_3_4": False,
        "layout_version": "v05",
        "svg_source_of_truth": True,
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Render one preset into dedicated mainstream platform canvases.")
    parser.add_argument("--preset", default="ref-01", help="ref-01..ref-21, fixed English alias, or Chinese preset name")
    parser.add_argument("--all-presets", action="store_true", help="render every preset")
    profile_selector = parser.add_mutually_exclusive_group()
    profile_selector.add_argument("--profile", choices=tuple(PROFILE_BY_ID), default="xhs-portrait", help="target canvas profile")
    profile_selector.add_argument("--all-profiles", action="store_true", help="render all five canvas profiles")
    page_selector = parser.add_mutually_exclusive_group()
    page_selector.add_argument("--page-type", choices=ALL_PAGES, default="cover", help="render one page type")
    page_selector.add_argument("--all-pages", action="store_true", help="render all page types supported by each profile")
    parser.add_argument("--title", default="原创视觉方向", help="main title; use \\n for explicit line breaks")
    parser.add_argument("--subtitle", default="同一套设计语言，适配不同平台", help="subtitle")
    parser.add_argument("--footer", default="ORIGINAL STUDY", help="footer label")
    parser.add_argument("--output-dir", type=Path, default=Path("platform-series"), help="root output directory")
    parser.add_argument("--hero-image", type=Path, help="optional local PNG/JPG; embedded on ref-02 only")
    parser.add_argument("--hero-remove-light", action="store_true", help="apply near-white hero treatment on ref-02")
    parser.add_argument("--png", action="store_true", help="also export PNG beside every SVG")
    parser.add_argument("--force", action="store_true", help="allow replacing existing SVG/PNG/JSON outputs")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        specs = cs.SPECS if args.all_presets else (cs.resolve_preset(args.preset),)
        profiles = PROFILES if args.all_profiles else (resolve_profile(args.profile),)
    except ValueError as exc:
        parser.error(str(exc))
        return 2
    _validate_hero(parser, args)
    args.hero_remove_light = bool(args.hero_remove_light)
    args.width = cs.DESIGN_W
    args.height = cs.DESIGN_H
    args.style = "reference-catalog"

    jobs: List[Tuple[cs.PresetSpec, CanvasProfile, Path, Tuple[str, ...]]] = []
    targets: List[Path] = []
    for spec in specs:
        for profile in profiles:
            if args.all_pages:
                page_types = profile.allowed_pages
            else:
                if args.page_type not in profile.allowed_pages:
                    parser.error(f"{profile.profile_id} 不支持 {args.page_type}；支持：{', '.join(profile.allowed_pages)}")
                page_types = (args.page_type,)
            output_dir = args.output_dir / spec.ref_id / profile.profile_id
            jobs.append((spec, profile, output_dir, page_types))
            targets.append(output_dir / "series.json")
            for index, page_type in enumerate(page_types, start=1):
                base = output_dir / f"{index:02d}-{page_type}"
                targets.append(base.with_suffix(".svg"))
                if args.png:
                    targets.append(base.with_suffix(".png"))

    if not args.force:
        existing = [path for path in targets if path.exists()]
        if existing:
            parser.error(
                "输出文件已存在，为保护旧稿未覆盖："
                + ", ".join(str(path) for path in existing[:6])
                + (" ..." if len(existing) > 6 else "")
                + "；如需替换请显式使用 --force"
            )

    png_failed = False
    for spec, profile, output_dir, page_types in jobs:
        output_dir.mkdir(parents=True, exist_ok=True)
        local_args = copy.copy(args)
        if spec.ref_id != "ref-02":
            local_args.hero_data_uri = ""
        for index, page_type in enumerate(page_types, start=1):
            svg_path = output_dir / f"{index:02d}-{page_type}.svg"
            svg_path.write_text(render_page(spec, profile, page_type, local_args), encoding="utf-8", newline="\n")
            print(f"SVG 已生成：{svg_path}")
            if args.png:
                png_path = output_dir / f"{index:02d}-{page_type}.png"
                ok, message = rp.export_png(svg_path, png_path, profile.width, profile.height)
                print(message, file=sys.stdout if ok else sys.stderr)
                if not ok:
                    png_failed = True
        sidecar_path = output_dir / "series.json"
        sidecar_path.write_text(
            json.dumps(_sidecar(spec, profile, local_args, page_types), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        print(f"JSON 已生成：{sidecar_path}")
    return 2 if png_failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
