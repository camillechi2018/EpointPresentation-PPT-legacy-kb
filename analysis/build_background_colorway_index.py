"""Tag existing theme-gallery backgrounds by approximate hue and lightness."""
from __future__ import annotations

import json
from pathlib import Path

from extract_theme_system import ROOT, image_tags


def main():
    catalog = json.loads((ROOT / "image-catalog.json").read_text(encoding="utf-8-sig"))
    assets = []
    for item in catalog["backgrounds"]:
        path = ROOT / item["file"]
        assets.append({"asset_id": item["id"], "family_id": item["family_id"], "role": item["role"], "paired_layout_id": item["paired_layout_id"], "source_page": item["source_slide"], "file": item["file"], "sha256": item["sha256"], "theme_binding": "template-v2-original", "selection_status": "machine_tagged_pending_visual_review", **image_tags(path.read_bytes())})
    out = ROOT / "theme-assets/background-colorway-index.json"
    out.write_text(json.dumps({"schema_version": "1.0", "assets": assets, "note": "Hue tags are approximate; paired layout and text safe area remain mandatory."}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"backgrounds": len(assets), "out": str(out)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
