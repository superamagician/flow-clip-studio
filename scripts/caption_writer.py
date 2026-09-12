#!/usr/bin/env python3
"""Template-based caption + hashtag generator, per platform.

Deterministic (no LLM/API call) so it works instantly from a UI button with zero
extra cost or setup — mirrors the style rules from the `post-caption-writer` skill,
built from whatever brief fields are already on hand (product_name, hook lines,
feature tags, upgrade hook, CTA). Not as nuanced as asking Claude directly (no live
hashtag-trend check), but always available and free.
"""
from __future__ import annotations
import re


def tagify(text: str) -> str:
    """Strip whitespace/punctuation so text can follow a '#' safely."""
    return re.sub(r"[\s!?.,()\-\/]+", "", text or "").strip("#")


def field(brief: dict, key: str, default: str = "") -> str:
    return (brief.get(key) or "").strip() or default


def tiktok_captions(brief: dict) -> dict:
    name = field(brief, "product_name", "สินค้านี้")
    hook1, hook2 = field(brief, "hook_line_1"), field(brief, "hook_line_2")
    feat1, feat2, feat3 = (field(brief, "feature_tag_1"), field(brief, "feature_tag_2"),
                            field(brief, "feature_tag_3"))
    up1, up2 = field(brief, "upgrade_hook_1"), field(brief, "upgrade_hook_2")
    cta = field(brief, "cta_text", "กดตะกร้าเลย")

    cap1 = f"{hook1} {hook2} 😔 ลองเซตนี้ดู! {feat1} + {feat2} + {feat3} ครบจบในที่เดียว {cta} 🛒✨".strip()
    tags1 = ["#TikTokShop", "#ของมันต้องมี"] + [f"#{tagify(t)}" for t in (feat1, feat2) if t]

    cap2 = f"{up1} {up2} 💪 {cta} 👇".strip()
    tags2 = ["#TikTokShop", "#รีวิวสินค้า", f"#{tagify(name)}"] if name else ["#TikTokShop", "#รีวิวสินค้า"]

    return {
        "captions": [
            {"text": cap1, "hashtags": tags1},
            {"text": cap2, "hashtags": tags2},
        ]
    }


def facebook_captions(brief: dict) -> dict:
    name = field(brief, "product_name", "สินค้านี้")
    hook1, hook2 = field(brief, "hook_line_1"), field(brief, "hook_line_2")
    feat1, feat2, feat3 = (field(brief, "feature_tag_1"), field(brief, "feature_tag_2"),
                            field(brief, "feature_tag_3"))
    up1, up2 = field(brief, "upgrade_hook_1"), field(brief, "upgrade_hook_2")

    h1 = hook1.rstrip("?")
    h2 = hook2.rstrip("?")
    cap1 = (f"เคยไหม? {h1}... {h2}... 😞\n"
            f"ลองเปลี่ยนมาใช้ {name} ดู — {feat1}, {feat2}, {feat3} ใช้ต่อเนื่องแล้วเห็นความเปลี่ยนแปลง\n"
            f"สนใจทักแชทสอบถามได้").strip()
    cap2 = f"{up1} {up2} ด้วย {name} แท็กเพื่อนที่กำลังมองหาตัวช่วยนี้อยู่เลย 👇".strip()

    return {
        "captions": [
            {"text": cap1, "hashtags": []},
            {"text": cap2, "hashtags": []},
        ]
    }


def shopee_captions(brief: dict) -> dict:
    name = field(brief, "product_name", "สินค้านี้")
    hook1 = field(brief, "hook_line_1")
    feat1, feat2, feat3 = (field(brief, "feature_tag_1"), field(brief, "feature_tag_2"),
                            field(brief, "feature_tag_3"))
    up1, up2 = field(brief, "upgrade_hook_1"), field(brief, "upgrade_hook_2")

    cap1 = f"{name} 🔥 {feat1} + {feat2} + {feat3} กดตะกร้าด้านล่างเลย ของมีจำนวนจำกัด".strip()
    tags1 = ["#shopeeTH"] + ([f"#{tagify(feat1)}"] if feat1 else [])

    cap2 = f"{hook1} {up1} {up2} แอดตะกร้าเลย ลิงก์สินค้าอยู่ด้านล่างคลิป 👇".strip()
    tags2 = ["#shopeeaffiliate"]

    return {
        "captions": [
            {"text": cap1, "hashtags": tags1},
            {"text": cap2, "hashtags": tags2},
        ]
    }


GENERATORS = {
    "tiktok": tiktok_captions,
    "facebook": facebook_captions,
    "shopee": shopee_captions,
}


def generate(brief: dict, platforms: list[str]) -> dict:
    result = {}
    for platform in platforms:
        generator = GENERATORS.get(platform)
        if generator:
            result[platform] = generator(brief)
    return result
