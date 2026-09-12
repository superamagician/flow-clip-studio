#!/usr/bin/env python3
"""Product-specific ad copy via Claude (optional - falls back to static generic
copy in app.py's autofill() when this isn't configured or a call fails).

Fixes the "every product sounds the same" problem: the old static autofill
filled blank hook/feature/CTA fields with fixed phrases ("คุณภาพดี", "ใช้งานง่าย",
"คุ้มราคาสุดๆ") regardless of what the product actually was. This calls Claude
Haiku with the sales-script-writer skill's principles baked into the system
prompt, so a customer who doesn't type their own copy still gets something
tailored to the specific product instead of interchangeable filler - including
a scene_setting_desc (e.g. "a kitchen countertop" vs "a gym floor") that feeds
into the default presenter_desc so the video's setting varies by product
category too, not just a fixed "bright clean modern room" every time.
"""
from __future__ import annotations
import json
import os
import urllib.error
import urllib.request

API_URL = "https://api.anthropic.com/v1/messages"
MODEL = "claude-haiku-4-5-20251001"

REQUIRED_FIELDS = {
    "hook_line_1", "hook_line_2", "feature_tag_1", "feature_tag_2", "feature_tag_3",
    "upgrade_hook_1", "upgrade_hook_2", "cta_text", "scene_setting_desc",
}

SYSTEM_PROMPT = """You are a professional Thai-language direct-response copywriter for \
short-form TikTok Shop/Shopee product ad videos. For the given product, write copy that \
is SPECIFIC to this exact product - never generic filler that could apply to any \
product. Before writing, silently answer: what does this product actually do, what \
specific problem/pain does it solve, what does the buyer get/become after using it. \
Then write, in Thai (except scene_setting_desc, which is English):
- hook_line_1, hook_line_2: short (under ~8 Thai words each) pain-point or question \
hooks that stop the scroll
- feature_tag_1, feature_tag_2, feature_tag_3: three DIFFERENT angles (spec-driven, \
convenience-driven, emotional/identity-driven), each fusing a specific detail with its \
payoff - never three phrasings of the same idea
- upgrade_hook_1, upgrade_hook_2: short aspirational transformation lines leading into \
a call to action
- cta_text: a short call to action in TikTok Shop/Shopee native vocabulary (references \
"ตะกร้า")
- scene_setting_desc: a short English phrase describing a realistic background/setting \
suited to THIS SPECIFIC product category (e.g. "a kitchen countertop with morning \
light" for a kitchen gadget, "a gym floor with dramatic lighting" for fitness gear, \
"a bathroom vanity with soft light" for skincare) - never a generic room for every \
product

Never invent unverifiable claims (certifications, "#1", medical/health claims, exact \
prices/discounts) beyond what's given. Respond with ONLY a JSON object with exactly \
these keys: hook_line_1, hook_line_2, feature_tag_1, feature_tag_2, feature_tag_3, \
upgrade_hook_1, upgrade_hook_2, cta_text, scene_setting_desc. No other text, no \
markdown code fences."""


def enabled() -> bool:
    return bool(os.getenv("ANTHROPIC_API_KEY"))


def generate_copy(product_name: str, product_visual_desc: str = "") -> dict | None:
    """Returns {hook_line_1, hook_line_2, feature_tag_1..3, upgrade_hook_1..2,
    cta_text, scene_setting_desc}, or None if not configured / the call failed
    or returned something unusable - callers must fall back to static copy."""
    key = os.getenv("ANTHROPIC_API_KEY", "")
    if not key:
        return None

    user_content = f"Product name: {product_name}"
    if product_visual_desc:
        user_content += f"\nVisual description: {product_visual_desc}"

    body = json.dumps({
        "model": MODEL,
        "max_tokens": 600,
        "system": SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": user_content}],
    }).encode("utf-8")
    req = urllib.request.Request(
        API_URL, data=body, method="POST",
        headers={"x-api-key": key, "anthropic-version": "2023-06-01",
                 "content-type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode("utf-8"))
        text = result["content"][0]["text"].strip()
        data = json.loads(text)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError,
            KeyError, IndexError, json.JSONDecodeError, ValueError):
        return None

    if not REQUIRED_FIELDS.issubset(data.keys()):
        return None
    return {k: str(data[k]).strip() for k in REQUIRED_FIELDS}
