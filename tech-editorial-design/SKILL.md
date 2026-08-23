---
name: tech-editorial-design
description: "Extract a visual fingerprint from a reference and create editable Chinese technology covers, matching body layouts, in-article illustrations, posters, and infographics."
---

# Tech Editorial Design

Use this skill when a reference image needs to become a reusable, original visual system for a Chinese technology cover, matching body pages, in-article illustrations, vertical poster, or long infographic.

## Operating rule

Separate the job into two layers:

1. Extract a visual fingerprint: composition, palette, type hierarchy, texture, grid, image treatment, and recurring motifs.
2. Generate the hero asset without words (AI may help) and put all exact Chinese, numbers, brands, borders, grids, labels, and UI marks into editable SVG through `scripts/render_poster.py`.

Do not promise pixel-level copying. Treat “90% similarity” as a visual-direction target and preserve enough originality to avoid copying protected logos, artwork, layouts, or a living creator’s distinctive signature.

The stable content-series renderer uses a 3:4 portrait canvas, defaulting to 1080×1440. For mainstream platform output, use `scripts/render_platform_series.py` and choose a named profile: `xhs-portrait` (1080×1440, 3:4), `douyin-vertical` (1080×1920, 9:16), `wechat-header` (900×383, cover only), `social-square` (1080×1080, 1:1), or `landscape-video` (1920×1080, 16:9). The five profiles use dedicated compositions and safe areas; they do not stretch the 3:4 page or fake another ratio with letterboxing. `series.json` records the profile, dimensions, safe area, fixed design tokens, and `stretched_from_3_4: false`. For公众号, combine `wechat-header` for the article header, `xhs-portrait` for body pages and in-article illustrations, and `social-square` for a share card. `wechat-header` intentionally supports only `cover`; a body page must use `xhs-portrait` or another full-page profile. Read [references/platform-canvas-profiles.md](references/platform-canvas-profiles.md) before cross-platform rendering.

Both renderers support explicit `\n` in text and wrap text to the line limit configured by each layout; overlong text is marked with an ellipsis instead of being allowed to run outside the safe area. Pass a local PNG/JPG with `--hero-image` only when the user has permission to use it; the source is read-only and embedded as a data URI. If a generated hero has a plain near-white background, `--hero-remove-light` can invert it into black-backed ghosted line art at render time. This is a style treatment rather than real transparency, so inspect it before use.

```powershell
python scripts/render_poster.py --style neon-grid --title "主标题" --subtitle "副标题" --eyebrow "科技专题" --footer "你的品牌" --output poster.svg --png poster.png
```

Available style families: `neon-grid`, `blue-digital`, `industrial-mono`, `modern-dark`, `editor-ui`, `public-blueprint`, plus the optional `minimal-orb` variant. Read the relevant sections of [references/style-families.md](references/style-families.md) and [references/prompt-library.md](references/prompt-library.md) before generating a new direction. Use [references/quality-gate.md](references/quality-gate.md) for visual, text, rights, and export checks.

When the user supplies eight or more references, do not collapse them into a small style set before showing coverage. First create a one-to-one preview for every reference, keep the source order and reference ID, then group only after the user can see the differences. Read [references/reference-coverage.md](references/reference-coverage.md) and the 21-direction prompt set in [references/reference-prompts-21.md](references/reference-prompts-21.md). Use `scripts/render_reference_catalog.py --all` for the built-in 21-direction coverage set; use the ordinary renderer only after the user chooses a direction.

## Choose a named preset

The 21 directions are organized into six usage groups without merging the presets. When the user does not know which one to choose, read [references/preset-catalog.md](references/preset-catalog.md). Each direction has three equivalent identifiers: `ref-xx`, a Chinese name, and an English alias.

For novice-friendly invocation wording and copy-ready examples, read [references/invocation-guide.md](references/invocation-guide.md). A usable request should name a specific preset, a page type, a topic, the exact text fields, and whether the whole series must remain locked to that preset.

## Extend a cover into a content series

When the user asks for body layout or in-article illustrations, treat the chosen cover preset as the source of truth. Read [references/series-consistency.md](references/series-consistency.md). Lock the background, palette, typography hierarchy, texture, line/radius rules, title alignment, signature motif, and image treatment for the whole series.

Use `scripts/render_content_series.py` for the built-in series system. It supports `cover`, `section`, `body`, `quote`, `steps`, `data`, `illustration`, and `ending`. Use `--all-pages` to create the full set. The renderer writes a sidecar JSON with the selected preset and design tokens; keep it with the SVG/PNG files so the series can be reproduced.

Use `scripts/render_platform_series.py` when the output must be delivered to more than one platform. It accepts the same `ref-01` to `ref-21`, Chinese names, and fixed English aliases, plus `--profile` or `--all-profiles`. `--all-pages` renders all pages supported by each selected profile; because `wechat-header` supports only `cover`, it produces one page there and eight pages for each of the other profiles. The same preset tokens are reused across every profile; only the composition, available space, and platform safe areas change. Use `scripts/build_platform_contact_sheet.py` to compare five profiles for one preset or all 21 presets within one profile. Copy-ready commands and platform routing are in [references/invocation-guide.md](references/invocation-guide.md) and [references/platform-canvas-profiles.md](references/platform-canvas-profiles.md).

For human review, use `scripts/build_series_contact_sheet.py` on one rendered preset directory. It creates a labeled two-column overview containing all eight pages, making it easier to check that the cover, body layouts, illustration, and ending still belong to the same system.

When validating breadth across many directions, use `scripts/build_preset_catalog_sheet.py` to place the same page type from several presets into one labeled overview. This is the preferred check for confirming that 21 references have not collapsed back into a few dark or blue templates.

Do not make every page identical. Page structure may change to fit its role, but it must not introduce another preset's palette, material, card geometry, texture, or motif. The `illustration` page should contain little text and reuse the chosen preset's subject/material language instead of becoming an unrelated AI image.

The SVG is the source of truth. PNG export uses a locally installed Edge/Chrome headless browser when available; if no browser can be found, keep the SVG and explain the export failure rather than hiding it.

Existing SVG/PNG files are protected by default. Use `--force` only when the user explicitly wants to replace a prior render; otherwise choose a new versioned output path.
