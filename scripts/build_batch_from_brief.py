#!/usr/bin/env python3
"""Expand a simple per-product brief CSV into a ready-to-run google_flow_rest.py batch CSV.

Usage:
    python build_batch_from_brief.py brief.csv reviewed.csv

Each row of brief.csv describes ONE product in plain fields (mostly Thai).
The script fills a 3-segment master template (pick one via the `genre` column)
and writes out one row per segment (segment_a/b/c) per product, in the exact
column format google_flow_rest.py's `batch` command expects.

Genres (brief.csv column `genre`, default "hook_feature_cta"):
  hook_feature_cta - the original TikTok Shop / Shopee Video structure:
                      Hook (pain point) -> Feature callouts -> CTA banner
  asmr             - satisfying, mostly wordless product-handling ASMR
  pov              - first-person point-of-view, hands-only, "you" framing
  minimal          - clean minimalist aesthetic, negative space, no pop graphics

Optional: brief.csv column `genres` (plural, comma-separated, e.g.
"hook_feature_cta,asmr") generates a full 3-segment set for EACH listed
genre from the same product/brief in one pass. Segment ids become
<product_id>_<genre>_a/b/c to keep them distinct. Takes precedence over
the singular `genre` column when both are present; leave it blank to keep
the original single-genre behavior.
"""
from __future__ import annotations
import csv
import sys
from pathlib import Path

BATCH_FIELDS = ["id", "status", "prompt", "model", "aspect_ratio", "resolution",
                "duration", "count", "email", "start_image", "reference_images",
                "job_id", "error", "genre"]

DEFAULT_PRESENTER = ("a young Asian man with short black hair and thick "
                      "black-framed glasses, seated at a gaming desk setup")

# ---------------------------------------------------------------------------
# Genre: hook_feature_cta (original) - talking presenter, pop-style graphics
# ---------------------------------------------------------------------------
HFC_A = (
    'Vertical 9:16 short-form product ad, {duration} seconds. '
    'Shot 1: {presenter}. '
    'They frown slightly, expressing a common problem, static medium close-up camera. '
    'Bold pop-style Thai text overlay bursts in: "{hook_line_1}" then "{hook_line_2}" '
    'with colorful lightning-bolt and arrow graphics. '
    'Shot 2: Hard cut to an extreme close-up product shot against a pure black background - '
    '{product_visual_desc}, dramatic high-contrast lighting, static camera. '
    'Shot 3: Extreme close-up on a key feature detail of the product, softly blurred background, '
    'subtle rack focus. '
    'Shot 4: Cut back to the same presenter now holding or using the product, smiling warmly, '
    'giving a thumbs-up, same lighting and setting as shot 1.'
)

HFC_B = (
    'Vertical 9:16 short-form product ad, {duration} seconds, continuing the same {product_name} '
    'against a pure black background. '
    'Shot 1: Extreme close-up 3/4 angle of the product floating against black, a glowing graphic '
    'streaks behind it, bold comic-style Thai text pops in: "{feature_tag_1}" with star/sparkle icons. '
    'Shot 2: Extreme close-up on a texture/material detail of the product, text overlay "{feature_tag_2}". '
    'Shot 3: Close-up revealing the product branding/logo clearly. '
    'Shot 4: Wider hero shot of the full product, comic sparkle and smoke-burst graphics around it. '
    'Shot 5: Hard cut to {presenter} using the product in a moody, ambient-lit setting; '
    'animated Thai text builds in "{feature_tag_3}", then a close smiling reaction shot, then a final '
    'clean product beauty shot with three stacked lines of Thai text: "{feature_tag_1}" / '
    '"{feature_tag_2}" / "{feature_tag_3}".'
)

HFC_C = (
    'Vertical 9:16 short-form product ad, {duration} seconds. '
    'Shot 1: {presenter}, warm ambient room lighting. Bold Thai text pops in top-left: '
    '"{upgrade_hook_1}" then "{upgrade_hook_2}" with a small sparkle icon. '
    'Shot 2: Closer medium shot, same setting, they smile and continue speaking. '
    'Shot 3: They smile broadly and point both index fingers downward toward the bottom of frame; '
    'a red circular cursor/arrow icon graphic appears at the bottom center, mimicking a shopping-cart '
    'click prompt. '
    'Shot 4: Cut to a close-up product shot of {product_visual_desc} against a black background with '
    'diagonal glowing neon light streaks, large bold Thai CTA text at the bottom of frame reading '
    '"{cta_text}", text remains on screen through the end of the clip.'
)

# ---------------------------------------------------------------------------
# Genre: asmr - no talking head, satisfying macro handling, minimal captions
# ---------------------------------------------------------------------------
ASMR_A = (
    'Vertical 9:16 ASMR product video, {duration} seconds, no talking, no music, only crisp '
    'satisfying ambient sound. Shot 1: extreme macro close-up of hands slowly unboxing/unwrapping '
    '{product_name} on a soft neutral fabric surface, soft diffused studio lighting, shallow depth '
    'of field, very slow deliberate hand movements. Shot 2: fingers gently tapping and rotating '
    '{product_visual_desc}, capturing crisp tactile sound cues (tapping, light clicks). Shot 3: '
    'extreme close-up as the product surface or cap is opened/pressed, satisfying micro-movement. '
    'Shot 4: hands hold the product steady in soft top-down lighting, tiny minimal Thai caption '
    'fades in at the bottom in a thin elegant font: "{hook_line_1}", no other graphics, no burst '
    'shapes, no comic style.'
)

ASMR_B = (
    'Vertical 9:16 ASMR product video, {duration} seconds, continuing the same {product_name}, no '
    'talking, only crisp ambient sound. Shot 1: slow macro pan across the product surface revealing '
    'texture and material detail, tiny minimal Thai caption fades in: "{feature_tag_1}", thin '
    'elegant font, no icons. Shot 2: extreme close-up of the product being used exactly as intended '
    '(e.g. liquid pouring, cushion pressing, button clicking) with a satisfying sound cue, caption '
    '"{feature_tag_2}" fades in the same minimal style. Shot 3: soft rack-focus reveal of the '
    'product branding/logo. Shot 4: slow 360-degree macro rotation of the full product on a turntable '
    'under soft studio light, caption "{feature_tag_3}" fades in, then fades out cleanly, no sparkle '
    'or burst graphics anywhere.'
)

ASMR_C = (
    'Vertical 9:16 ASMR product video, {duration} seconds, no talking, only crisp ambient sound. '
    'Shot 1: hands neatly repacking or placing {product_name} back into its box/packaging in soft '
    'top-down lighting, deliberate slow motion. Shot 2: a final satisfying close-up sound moment '
    '(box closing, lid clicking shut). Shot 3: static top-down shot of the product centered on a '
    'clean neutral background with soft shadow. Shot 4: small, thin, elegant Thai CTA caption fades '
    'in at the bottom center only: "{cta_text}", no neon, no comic graphics, text remains until the '
    'end of the clip.'
)

# ---------------------------------------------------------------------------
# Genre: pov - first-person point of view, hands-only, "you" framing
# ---------------------------------------------------------------------------
POV_A = (
    'Vertical 9:16 first-person POV product video, {duration} seconds, filmed as if the viewer is '
    'looking through their own eyes - camera framed as the viewer\'s own point of view, handheld, '
    'natural slight motion, no visible presenter face. Shot 1: POV of the viewer\'s own hand '
    'reaching toward {product_visual_desc} sitting on a table/shelf, everyday room in soft focus '
    'behind it. Bold Thai text overlay appears as if addressing the viewer directly: "{hook_line_1}" '
    'then "{hook_line_2}", simple bold sans-serif style, minimal graphics. Shot 2: POV close-up as '
    'the viewer\'s own hands pick up and turn {product_name} to inspect it. Shot 3: POV extreme '
    'close-up on a key feature detail as the viewer\'s fingers interact with it. Shot 4: POV of the '
    'viewer\'s own hands now using the product naturally, a satisfied exhale/reaction implied by '
    'context, same room setting as shot 1.'
)

POV_B = (
    'Vertical 9:16 first-person POV product video, {duration} seconds, continuing the same '
    '{product_name}, handheld POV camera the whole time, no visible presenter face. Shot 1: POV of '
    'the viewer\'s own hands holding the product up close to inspect a feature, bold text overlay '
    '"{feature_tag_1}" pops in near the product. Shot 2: POV close-up as fingers demonstrate a '
    'second feature, text overlay "{feature_tag_2}". Shot 3: POV glance down at the product logo/ '
    'branding held in the viewer\'s own hand. Shot 4: POV of the viewer\'s hands actively using the '
    'product in a real-life moment (at a desk, on a couch, etc.), text builds in "{feature_tag_3}", '
    'then a final POV shot looking down at the product resting in the viewer\'s open palm with all '
    'three tags stacked on screen: "{feature_tag_1}" / "{feature_tag_2}" / "{feature_tag_3}".'
)

POV_C = (
    'Vertical 9:16 first-person POV product video, {duration} seconds, handheld POV camera, no '
    'visible presenter face. Shot 1: POV of the viewer sitting comfortably, product visible in '
    'their own hands/lap, bold Thai text pops in: "{upgrade_hook_1}" then "{upgrade_hook_2}". '
    'Shot 2: POV of the viewer\'s own hand picking up a phone, thumb scrolling naturally. Shot 3: '
    'POV of the viewer\'s own thumb tapping toward the bottom of the screen, a red circular cursor/ '
    'arrow icon appears at the bottom center mimicking a shopping-cart click. Shot 4: POV close-up '
    'of {product_visual_desc} held steady in the viewer\'s own hand, large bold Thai CTA text at '
    'the bottom reading "{cta_text}", text remains on screen through the end of the clip.'
)

# ---------------------------------------------------------------------------
# Genre: minimal - clean aesthetic, negative space, no pop/comic graphics
# ---------------------------------------------------------------------------
MIN_A = (
    'Vertical 9:16 minimalist product ad, {duration} seconds, clean editorial aesthetic, generous '
    'negative space, soft neutral color palette, slow deliberate camera moves, no comic graphics, '
    'no lightning bolts, no clutter. Shot 1: {presenter}, positioned off-center with lots of empty '
    'space in frame, calm neutral expression, soft even studio lighting, static camera. Small, thin, '
    'elegant Thai text fades in gently at the bottom third: "{hook_line_1}" then "{hook_line_2}", '
    'simple sans-serif font, no icons or bursts. Shot 2: slow, deliberate pan across {product_visual_desc} '
    'placed on a clean neutral-toned surface with soft natural shadow. Shot 3: extreme close-up on '
    'a key feature detail, extremely shallow depth of field, quiet and refined. Shot 4: cut back to '
    '{presenter} holding the product with a subtle, calm smile, same minimal lighting as shot 1.'
)

MIN_B = (
    'Vertical 9:16 minimalist product ad, {duration} seconds, continuing the same {product_name}, '
    'clean editorial aesthetic, soft neutral tones, no comic graphics, no sparkle icons. Shot 1: '
    'slow push-in on the product resting on a clean minimal surface, small elegant Thai caption '
    'fades in: "{feature_tag_1}". Shot 2: close-up on a texture/material detail, caption fades to '
    '"{feature_tag_2}", same thin sans-serif style, no icons. Shot 3: quiet, well-lit reveal of the '
    'product branding/logo, held steady. Shot 4: wide, airy hero shot of the full product centered '
    'with abundant negative space, caption builds to "{feature_tag_3}", then a final clean shot with '
    'all three captions arranged simply in a single thin line: "{feature_tag_1}" · "{feature_tag_2}" '
    '· "{feature_tag_3}", no decorative graphics anywhere in the clip.'
)

MIN_C = (
    'Vertical 9:16 minimalist product ad, {duration} seconds, clean editorial aesthetic, soft '
    'neutral tones, no comic graphics. Shot 1: {presenter}, calm and composed, generous negative '
    'space, small elegant Thai text fades in: "{upgrade_hook_1}" then "{upgrade_hook_2}". Shot 2: '
    'closer, quiet medium shot, same calm setting. Shot 3: a simple, understated cursor/arrow icon '
    'fades in near the bottom of frame, no bright colors, minimal style. Shot 4: clean, centered '
    'close-up of {product_visual_desc} against a soft neutral background, small refined Thai CTA '
    'text at the bottom reading "{cta_text}", text remains on screen through the end of the clip, '
    'no neon, no clutter.'
)

GENRES = {
    "hook_feature_cta": (HFC_A, HFC_B, HFC_C),
    "asmr": (ASMR_A, ASMR_B, ASMR_C),
    "pov": (POV_A, POV_B, POV_C),
    "minimal": (MIN_A, MIN_B, MIN_C),
}


def csv_field(row: dict, key: str, default: str = "") -> str:
    value = (row.get(key) or "").strip()
    return value if value else default


def build_rows(brief_row: dict) -> list[dict]:
    duration = csv_field(brief_row, "duration", "10")
    model = csv_field(brief_row, "model", "omni-flash")
    aspect_ratio = csv_field(brief_row, "aspect_ratio", "portrait")
    resolution = csv_field(brief_row, "resolution", "720p")
    presenter = csv_field(brief_row, "presenter_desc", DEFAULT_PRESENTER)

    # `genres` (plural, comma-separated) is optional: pick multiple styles for the
    # same product in one go, e.g. "hook_feature_cta,asmr". Falls back to the
    # single `genre` field (unchanged default behavior) when not given.
    genres_field = csv_field(brief_row, "genres")
    if genres_field:
        genre_list = [g.strip().lower() for g in genres_field.split(",") if g.strip()]
    else:
        genre_list = [csv_field(brief_row, "genre", "hook_feature_cta").strip().lower()]
    for g in genre_list:
        if g not in GENRES:
            raise ValueError(
                f"Unknown genre '{g}'. Choose one of: {', '.join(GENRES)}")
    multi_genre = len(genre_list) > 1

    fmt_args = dict(
        duration=duration,
        presenter=presenter,
        product_name=csv_field(brief_row, "product_name"),
        product_visual_desc=csv_field(brief_row, "product_visual_desc"),
        hook_line_1=csv_field(brief_row, "hook_line_1"),
        hook_line_2=csv_field(brief_row, "hook_line_2"),
        feature_tag_1=csv_field(brief_row, "feature_tag_1"),
        feature_tag_2=csv_field(brief_row, "feature_tag_2"),
        feature_tag_3=csv_field(brief_row, "feature_tag_3"),
        upgrade_hook_1=csv_field(brief_row, "upgrade_hook_1"),
        upgrade_hook_2=csv_field(brief_row, "upgrade_hook_2"),
        cta_text=csv_field(brief_row, "cta_text"),
    )

    product_id = csv_field(brief_row, "product_id", "product")
    reference_image = csv_field(brief_row, "reference_image")
    visual_style = csv_field(brief_row, "visual_style_desc")
    style_override = (
        f' Overall visual style, background, and on-screen text styling: {visual_style}. '
        'Follow this style instead of any conflicting background/graphic style described above; '
        'keep on-screen text bold and legible but recolor/restyle it to match this brand style.'
        if visual_style else ''
    )
    rows = []
    for genre in genre_list:
        template_a, template_b, template_c = GENRES[genre]
        prefix = f"{product_id}_{genre}" if multi_genre else product_id
        segments = [
            (f"{prefix}_a", template_a.format(**fmt_args) + style_override),
            (f"{prefix}_b", template_b.format(**fmt_args) + style_override),
            (f"{prefix}_c", template_c.format(**fmt_args) + style_override),
        ]
        for seg_id, prompt in segments:
            rows.append({
                "id": seg_id, "status": "Ready", "prompt": prompt,
                "model": model, "aspect_ratio": aspect_ratio, "resolution": resolution,
                "duration": duration, "count": "1", "email": "", "start_image": "",
                "reference_images": reference_image, "job_id": "", "error": "",
                "genre": genre,
            })
    return rows


def main():
    if len(sys.argv) != 3:
        raise SystemExit("Usage: python build_batch_from_brief.py brief.csv reviewed.csv")
    brief_path, out_path = Path(sys.argv[1]), Path(sys.argv[2])

    with brief_path.open(encoding="utf-8-sig", newline="") as handle:
        brief_rows = list(csv.DictReader(handle))

    out_rows = []
    for brief_row in brief_rows:
        out_rows.extend(build_rows(brief_row))

    with out_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=BATCH_FIELDS)
        writer.writeheader()
        writer.writerows(out_rows)

    print(f"Wrote {len(out_rows)} rows ({len(brief_rows)} products x 3 segments) to {out_path}")


if __name__ == "__main__":
    main()
