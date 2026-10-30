"""Audit what a base-token JSON cannot directly recolor in source components."""
from __future__ import annotations

import csv
import json
import re
from collections import Counter
from pathlib import Path
from zipfile import ZipFile

from lxml import etree

ROOT = Path(__file__).resolve().parents[1]
CATALOG = json.loads((ROOT / "catalog.json").read_text(encoding="utf-8"))
TOKENS = json.loads((ROOT / "epoint-presentation/assets/design-tokens.json").read_text(encoding="utf-8"))
KNOWN_COLORS = {value.removeprefix("#").upper() for value in TOKENS["colors"].values()}


def count(root, local_name: str) -> int:
    return len(root.xpath(f'//*[local-name()="{local_name}"]'))


def scan_layout(item: dict) -> dict:
    with ZipFile(ROOT / item["source"]) as package:
        name = next(n for n in package.namelist() if re.fullmatch(r"ppt/slides/slide\d+\.xml", n))
        slide = etree.fromstring(package.read(name))
        media = Counter(Path(n).suffix.lower() for n in package.namelist() if n.startswith("ppt/media/"))
        support_blips = 0
        for n in package.namelist():
            if n.endswith(".xml") and (n.startswith("ppt/slideLayouts/") or n.startswith("ppt/slideMasters/")):
                support_blips += count(etree.fromstring(package.read(n)), "blip")
        explicit = Counter(e.get("val").upper() for e in slide.xpath('//*[local-name()="srgbClr"]') if e.get("val"))
        font_refs = sum(1 for e in slide.xpath('//*[local-name()="latin" or local-name()="ea" or local-name()="cs"]') if (e.get("typeface") or "").startswith("+"))
        row = {
            "source_page": item["source_page"],
            "layout_id": item["id"],
            "role": item["role"],
            "family_id": item.get("family_id", ""),
            "collection": item["collection"],
            "media_total": sum(media.values()),
            "media_formats": ";".join(f"{ext}:{num}" for ext, num in sorted(media.items())),
            "slide_pictures": count(slide, "pic"),
            "layout_master_image_refs": support_blips,
            "gradients": count(slide, "gradFill"),
            "scheme_color_refs": count(slide, "schemeClr"),
            "font_theme_refs": font_refs,
            "native_charts": count(slide, "chart"),
            "native_tables": count(slide, "tbl"),
            "explicit_color_occurrences_outside_base": sum(num for color, num in explicit.items() if color not in KNOWN_COLORS),
            "explicit_colors_outside_base": ";".join("#" + color for color in sorted(explicit.keys() - KNOWN_COLORS)),
        }
        if row["media_total"]:
            row["control_boundary"] = "含媒体素材，需换图或重制素材"
        elif row["gradients"] or row["native_charts"] or row["native_tables"]:
            row["control_boundary"] = "含渐变或数据对象，需特殊映射"
        else:
            row["control_boundary"] = "仅原生对象，仍需颜色与字体角色映射"
        return row


def ranges(pages: list[int]) -> str:
    if not pages:
        return "无"
    spans = []
    start = prev = pages[0]
    for page in pages[1:]:
        if page == prev + 1:
            prev = page
            continue
        spans.append(f"P{start:03d}" if start == prev else f"P{start:03d}–P{prev:03d}")
        start = prev = page
    spans.append(f"P{start:03d}" if start == prev else f"P{start:03d}–P{prev:03d}")
    return "、".join(spans)


def main() -> None:
    rows = sorted((scan_layout(x) for x in CATALOG["layouts"] if x.get("collection") in ("source-theme", "source-content")), key=lambda x: x["source_page"])
    assert len(rows) == 217 and [x["source_page"] for x in rows] == list(range(1, 218))
    output = ROOT / "analysis/基础变量控制边界.csv"
    with output.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    summary = {
        "all_source_components_not_connected_to_token_recoloring": len(rows),
        "with_media": sum(bool(r["media_total"]) for r in rows),
        "with_gradients": sum(bool(r["gradients"]) for r in rows),
        "with_theme_color_refs": sum(bool(r["scheme_color_refs"]) for r in rows),
        "with_theme_font_refs": sum(bool(r["font_theme_refs"]) for r in rows),
        "with_native_charts": sum(bool(r["native_charts"]) for r in rows),
        "with_native_tables": sum(bool(r["native_tables"]) for r in rows),
        "with_explicit_colors_outside_base": sum(bool(r["explicit_color_occurrences_outside_base"]) for r in rows),
    }
    buckets = Counter(r["control_boundary"] for r in rows)
    lines = [
        "# 基础变量对原稿组件的控制边界",
        "",
        "依据 v0.8 `design-tokens.json` 与217个 `blank.pptx` 组件逐页检查。此处的“不能直接控制”指修改基础变量 JSON 后，现有组件不会自动重染；不代表这些页面永远无法换色。目前 AI 背景提示词脚本能读取变量；新建页可按变量制作，但尚无自动套用脚本。",
        "",
        "## 数量概览",
        "",
        "| 检查项 | 页数 | 说明 |",
        "|---|---:|---|",
        f"| 原稿组件尚未连接自动换肤 | {len(rows)} | 全部需对象角色映射 |",
        f"| 含媒体文件 | {summary['with_media']} | 照片、PNG、SVG、WDP 等须换素材或单独处理 |",
        f"| 含渐变 | {summary['with_gradients']} | 需映射各渐变停靠点与透明度 |",
        f"| 含主题色引用 | {summary['with_theme_color_refs']} | 需处理母版／主题颜色关系 |",
        f"| 含主题字体引用 | {summary['with_theme_font_refs']} | 需处理继承字体及断行 |",
        f"| 含原生图表 | {summary['with_native_charts']} | 系列、坐标轴、标签单独映射 |",
        f"| 含原生表格 | {summary['with_native_tables']} | 单元格、边框、文字单独映射 |",
        f"| 出现基础变量未收录的显式颜色 | {summary['with_explicit_colors_outside_base']} | 需先判定用途，不宜按色值盲替换 |",
        "",
        "以上项目可以重叠，不能相加当作总页数。媒体文件统计来自 PPTX 包；其中可能包含占位图、图标和背景，不能一概视为照片。",
        "",
        "## 按处理难度分组（互斥）",
        "",
        "| 分组 | 页数 | 页码 |",
        "|---|---:|---|",
    ]
    for label in ("含媒体素材，需换图或重制素材", "含渐变或数据对象，需特殊映射", "仅原生对象，仍需颜色与字体角色映射"):
        pages = [r["source_page"] for r in rows if r["control_boundary"] == label]
        lines.append(f"| {label} | {len(pages)} | {ranges(pages)} |")
    lines.extend(["", "## 特殊对象页码", ""])
    for label, key in (("原生图表", "native_charts"), ("原生表格", "native_tables"), ("母版或版式引用图片", "layout_master_image_refs")):
        pages = [r["source_page"] for r in rows if r[key]]
        lines.append(f"- {label}：{ranges(pages)}")
    lines.extend([
        "",
        "## 读取方法与限制",
        "",
        "- 逐个打开 `catalog.json` 登记的217个原稿组件 `blank.pptx`，统计幻灯片 XML、包内媒体和母版／版式图片引用。按页全部结果见 [CSV](基础变量控制边界.csv)。",
        "- `gradFill`、`schemeClr` 和字体引用是 OOXML 对象计数；并不表示它们在画面中都可见。未做逐页渲染、像素分割或业务语义判断。",
        "- 基础变量的10个语义色无法覆盖所有原稿显式色；即使同一色值出现在多页，也可能分别承担正文、图标或装饰用途。",
        "- 对媒体、渐变、图表和字体建立映射后，仍需按页渲染并检查对比度、中文断行、裁切和层级。",
    ])
    (ROOT / "analysis/基础变量控制边界.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (ROOT / "analysis/token-control-summary.json").write_text(json.dumps({"summary": summary, "buckets": dict(buckets)}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"summary": summary, "buckets": dict(buckets)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
