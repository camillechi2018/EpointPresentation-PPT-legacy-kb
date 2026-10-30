"""Extract native gradients, table styles and embedded media from canonical slides."""
from __future__ import annotations

import hashlib
import io
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from zipfile import ZipFile

from lxml import etree
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "theme-assets"
CAT = json.loads((ROOT / "catalog.json").read_text(encoding="utf-8"))
SVG_COLOR = re.compile(r"#[0-9a-fA-F]{3,8}\b")
COMPLEX_SVG = re.compile(r"<(?:\w+:)?(?:linearGradient|radialGradient|style|image|mask|pattern)\b|url\(#")


def local(node):
    return node.tag.rsplit("}", 1)[-1]


def palette_from_theme(root):
    schemes = root.xpath('//*[local-name()="clrScheme"]')
    if not schemes:
        return {}
    result = {}
    for slot in schemes[0]:
        color = next((child.get("lastClr") or child.get("val") for child in slot if child.get("lastClr") or child.get("val")), None)
        if color:
            result[local(slot)] = "#" + color.upper()
    return result


def color_spec(element):
    color = next((child for child in element if local(child) in ("srgbClr", "schemeClr", "sysClr", "prstClr")), None)
    if color is None:
        return None
    return {"kind": local(color), "value": color.get("val"), "transforms": [{"kind": local(t), "value": t.get("val")} for t in color]}


def gradient_spec(element):
    stops = []
    for stop in element.xpath('./*[local-name()="gsLst"]/*[local-name()="gs"]'):
        stops.append({"position": int(stop.get("pos", "0")), "color": color_spec(stop)})
    geometry = next((child for child in element if local(child) in ("lin", "path")), None)
    return {"stops": stops, "geometry": None if geometry is None else {"kind": local(geometry), "attributes": dict(geometry.attrib)}}


def image_tags(raw):
    try:
        with Image.open(io.BytesIO(raw)) as im:
            if im.width * im.height > 40_000_000:
                return {"accent_hue": "unknown", "tone": "unknown", "reason": "large_image_not_sampled"}
            im = im.convert("RGB")
            im.thumbnail((96, 96))
            pixels = list(im.getdata())
        if not pixels:
            return {"accent_hue": "unknown", "tone": "unknown"}
        light = sum(max(p) for p in pixels) / len(pixels) / 255
        chromatic = [p for p in pixels if max(p) - min(p) > 35 and max(p) > 50]
        if len(chromatic) < len(pixels) * 0.05:
            hue = "neutral"
        else:
            red = sum(p[0] for p in chromatic) / len(chromatic)
            green = sum(p[1] for p in chromatic) / len(chromatic)
            blue = sum(p[2] for p in chromatic) / len(chromatic)
            hue = "blue" if blue > red * 1.12 and blue > green * 1.04 else "green" if green > red * 1.12 and green > blue * 0.90 else "warm" if red > green * 1.12 else "mixed"
        return {"accent_hue": hue, "tone": "light" if light > 0.67 else "dark" if light < 0.36 else "mid", "mean_lightness": round(light, 3)}
    except Exception:
        return {"accent_hue": "unknown", "tone": "unknown"}


def main():
    (OUT / "svg").mkdir(parents=True, exist_ok=True)
    (OUT / "raster").mkdir(parents=True, exist_ok=True)
    recipes = {}
    assets = {}
    pages = []
    table_styles = {}
    theme_schemes = Counter()
    native_icon_candidates = []
    svg_color_frequency = Counter()
    for entry in CAT["layouts"]:
        if entry.get("collection") not in ("source-theme", "source-content"):
            continue
        page = entry["source_page"]
        page_record = {"source_page": page, "layout_id": entry["id"], "collection": entry["collection"], "family_id": entry.get("family_id"), "gradient_ids": [], "asset_ids": [], "table_style_ids": []}
        with ZipFile(ROOT / entry["source"]) as package:
            slide_name = next(n for n in package.namelist() if re.fullmatch(r"ppt/slides/slide\d+\.xml", n))
            slide = etree.fromstring(package.read(slide_name))
            ns = {"a": "http://schemas.openxmlformats.org/drawingml/2006/main", "p": "http://schemas.openxmlformats.org/presentationml/2006/main"}
            for shape in slide.xpath("//p:sp", namespaces=ns):
                if shape.xpath(".//a:t", namespaces=ns):
                    continue
                ext = shape.xpath("./p:spPr/a:xfrm/a:ext", namespaces=ns)
                if not ext:
                    continue
                width = int(ext[0].get("cx", "0")) / 12700
                height = int(ext[0].get("cy", "0")) / 12700
                if not (4 <= width <= 80 and 4 <= height <= 80 and 0.25 <= width / height <= 4):
                    continue
                nv = shape.xpath("./p:nvSpPr/p:cNvPr", namespaces=ns)
                paint = [{"kind": local(color), "value": color.get("val")} for color in shape.xpath(".//a:srgbClr|.//a:schemeClr", namespaces=ns)]
                native_icon_candidates.append({"source_page": page, "shape_id": int(nv[0].get("id")) if nv else None, "width_pt": round(width, 2), "height_pt": round(height, 2), "colors": paint, "status": "small_unlabeled_shape_candidate_not_confirmed_icon"})
            theme_name = next((n for n in package.namelist() if re.fullmatch(r"ppt/theme/theme\d+\.xml", n)), None)
            if theme_name:
                scheme = palette_from_theme(etree.fromstring(package.read(theme_name)))
                theme_schemes[json.dumps(scheme, sort_keys=True)] += 1
            for gradient in slide.xpath('//*[local-name()="gradFill"]'):
                spec = gradient_spec(gradient)
                encoded = json.dumps(spec, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
                gid = "gradient-" + hashlib.sha256(encoded.encode()).hexdigest()[:16]
                obj = recipes.setdefault(gid, {"id": gid, **spec, "occurrences": 0, "pages": []})
                obj["occurrences"] += 1
                if page not in obj["pages"]:
                    obj["pages"].append(page)
                page_record["gradient_ids"].append(gid)
            for table in slide.xpath('//*[local-name()="tbl"]'):
                style_nodes = table.xpath('./*[local-name()="tblPr"]/*[local-name()="tableStyleId"]')
                style_id = style_nodes[0].text if style_nodes else "none"
                cells = table.xpath('.//*[local-name()="tc"]')
                fills = Counter()
                for cell in cells:
                    for fill in cell.xpath('./*[local-name()="tcPr"]/*[local-name()="solidFill" or local-name()="gradFill"]'):
                        color = color_spec(fill)
                        fills[json.dumps(color, sort_keys=True)] += 1
                t = table_styles.setdefault(style_id, {"id": style_id, "pages": [], "cell_count": 0, "explicit_cell_fills": Counter(), "table_styles_xml": "ppt/tableStyles.xml"})
                if "sections" not in t and "ppt/tableStyles.xml" in package.namelist():
                    styles_root = etree.fromstring(package.read("ppt/tableStyles.xml"))
                    style = next((node for node in styles_root if node.get("styleId") == style_id), None)
                    if style is not None:
                        t["name"] = style.get("styleName")
                        t["sections"] = {local(section): dict(Counter(color.get("val") for color in section.xpath('.//*[local-name()="schemeClr"]'))) for section in style}
                t["pages"].append(page)
                t["cell_count"] += len(cells)
                t["explicit_cell_fills"].update(fills)
                page_record["table_style_ids"].append(style_id)
            for name in package.namelist():
                if not name.startswith("ppt/media/"):
                    continue
                suffix = Path(name).suffix.lower()
                if suffix not in (".svg", ".png", ".jpg", ".jpeg", ".webp", ".wdp"):
                    continue
                raw = package.read(name)
                digest = hashlib.sha256(raw).hexdigest()
                aid = "asset-" + digest[:16]
                if aid not in assets:
                    kind = "svg" if suffix == ".svg" else "raster"
                    dest = OUT / kind / (digest[:16] + suffix)
                    dest.write_bytes(raw)
                    record = {"id": aid, "sha256": digest, "kind": kind, "format": suffix, "file": dest.relative_to(ROOT).as_posix(), "source_pages": [], "theme_binding": "template-v2-original", "review_status": "machine_classified_pending_visual_review"}
                    if kind == "svg":
                        source = raw.decode("utf-8", "replace")
                        colors = sorted({v.upper() for v in SVG_COLOR.findall(source)})
                        svg_color_frequency.update(colors)
                        has_risky = bool(re.search(r"<(?:\w+:)?(?:style|image|mask|pattern)\b", source))
                        brand_colors = {"#376FFF", "#4096FF"} & set(colors)
                        neutral = set(colors) <= {"#FFFFFF", "#000000", "#262626", "#CCCCCC", "#666666"}
                        control = "brand_svg_candidate" if brand_colors and not has_risky else "neutral_svg_reusable" if neutral and not has_risky else "theme_bound_component"
                        record.update({"colors": colors, "control": control, "has_gradient": bool(re.search(r"<(?:\w+:)?(?:linearGradient|radialGradient)\b", source)), "requires_visual_review": True})
                    else:
                        record.update({"control": "theme_bound_component", **image_tags(raw)})
                    assets[aid] = record
                if page not in assets[aid]["source_pages"]:
                    assets[aid]["source_pages"].append(page)
                page_record["asset_ids"].append(aid)
        pages.append(page_record)
    assert len(pages) == 217 and [p["source_page"] for p in pages] == list(range(1, 218))
    assert len(theme_schemes) == 1, "源组件的主题色板并不一致，需要逐页登记"
    palette = json.loads(next(iter(theme_schemes)))
    for table in table_styles.values():
        table["explicit_cell_fills"] = [{"color": json.loads(k), "count": v} for k, v in table["explicit_cell_fills"].most_common()]
    payload = {"schema_version": "1.0", "source": "完整模版示例v2.pptx", "source_pages": 217, "theme_palette": palette, "gradients": list(recipes.values()), "table_styles": list(table_styles.values()), "svg_color_frequency": dict(svg_color_frequency.most_common()), "native_icon_candidates": native_icon_candidates, "assets": list(assets.values()), "pages": pages, "classification_note": "Small unlabeled shapes are icon candidates, not verified icons. SVG candidates require visual review; raster hue tags are approximate."}
    path = ROOT / "theme-assets/registry.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary = {"pages": len(pages), "gradient_occurrences": sum(v["occurrences"] for v in recipes.values()), "gradient_recipes": len(recipes), "table_styles": len(table_styles), "native_icon_candidates": len(native_icon_candidates), "svg": sum(v["kind"] == "svg" for v in assets.values()), "brand_svg_candidates": sum(v["control"] == "brand_svg_candidate" for v in assets.values()), "neutral_svg_reusable": sum(v["control"] == "neutral_svg_reusable" for v in assets.values()), "theme_bound_assets": sum(v["control"] == "theme_bound_component" for v in assets.values()), "theme_palette": palette}
    (ROOT / "analysis/theme-system-summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
