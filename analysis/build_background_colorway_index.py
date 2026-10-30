"""Validate canonical background tags and derive the searchable colorway index.

The 68 image-catalog backgrounds are the only manually edited records. Never
hand-edit theme-assets/background-colorway-index.json: generate it from here.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "image-catalog.json"
INDEX = ROOT / "theme-assets" / "background-colorway-index.json"
HUES = {"blue", "cyan", "green", "violet", "warm", "mixed", "neutral"}
ROLES = {"cover", "agenda", "chapter", "closing"}


def build() -> dict:
    source = json.loads(CATALOG.read_text(encoding="utf-8-sig"))
    entries = source["backgrounds"]
    output = []
    seen = set()
    for item in entries:
        asset_id = item["id"]
        if asset_id in seen:
            raise ValueError(f"重复素材ID: {asset_id}")
        seen.add(asset_id)
        if item["role"] not in ROLES:
            raise ValueError(f"未知页面角色: {asset_id}")
        palette = item.get("color_profile")
        visual = item.get("visual_profile")
        if not isinstance(palette, dict) or not isinstance(visual, dict):
            raise ValueError(f"缺少颜色或视觉标签: {asset_id}")
        if palette.get("accent_hue") not in HUES:
            raise ValueError(f"未知色系: {asset_id}")
        if palette.get("tone") not in {"light", "mid", "dark"}:
            raise ValueError(f"未知明暗标签: {asset_id}")
        ratio = palette.get("accent_coverage")
        if not isinstance(ratio, (float, int)) or not 0 <= ratio <= 1:
            raise ValueError(f"强调色占比无效: {asset_id}")
        score = visual.get("impact_score")
        if not isinstance(score, int) or isinstance(score, bool) or not 1 <= score <= 5:
            raise ValueError(f"视觉冲击力评分无效: {asset_id}")
        if not visual.get("review_status"):
            raise ValueError(f"缺少复核状态: {asset_id}")
        path = ROOT / item["file"]
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != item["sha256"]:
            raise ValueError(f"背景图片缺失或SHA不匹配: {asset_id}")
        paired = ROOT / item["editable_source"]
        if not paired.is_file():
            raise ValueError(f"配套可编辑版式缺失: {asset_id}")
        output.append({
            "asset_id": asset_id,
            "family_id": item["family_id"],
            "role": item["role"],
            "paired_layout_id": item["paired_layout_id"],
            "source_page": item["source_slide"],
            "file": item["file"],
            "preview": item["preview"],
            "sha256": item["sha256"],
            "theme_binding": "template-v2-original",
            "accent_hue": palette["accent_hue"],
            "accent_hex": palette.get("accent_hex"),
            "accent_coverage": ratio,
            "tone": palette["tone"],
            "mean_lightness": palette["mean_lightness"],
            "visual_impact": score,
            "visual_review_status": visual["review_status"],
            "text_safe_areas": item.get("text_safe_areas", []),
        })
    if not output:
        raise ValueError("主题图库没有背景记录")
    return {
        "schema_version": "1.0",
        "source": "image-catalog.json/backgrounds",
        "assets": output,
        "note": "色调和冲击力标签用于候选排序；标题、Logo、安全区和整套家族仍需目视核对。",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="只检查索引是否与主目录一致")
    args = parser.parse_args()
    data = build()
    content = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    if args.check:
        if not INDEX.exists() or INDEX.read_bytes() != content.encode("utf-8"):
            parser.exit(2, "色系索引与 image-catalog.json 不一致；请重建索引。\n")
    else:
        INDEX.write_bytes(content.encode("utf-8"))
    print(json.dumps({"backgrounds": len(data["assets"]), "index": str(INDEX), "mode": "check" if args.check else "build"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
