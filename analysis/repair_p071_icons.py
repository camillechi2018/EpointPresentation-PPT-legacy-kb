"""Replace P071's four filled picture icons with small native line icons."""
from __future__ import annotations

import argparse
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.util import Pt

WHITE = RGBColor(255, 255, 255)
TARGETS = {47: "users", 37: "folder", 31: "monitor", 42: "cloud-upload"}


def repair(source: Path, output: Path) -> dict:
    if source.resolve() == output.resolve() or output.exists():
        raise ValueError("输出必须是新的 PPTX 文件")
    ppt = Presentation(source)
    if len(ppt.slides) != 1:
        raise ValueError("P071 组件应只有一页")
    slide = ppt.slides[0]
    originals = {s.shape_id: s for s in slide.shapes if s.shape_id in TARGETS}
    if set(originals) != set(TARGETS):
        raise ValueError(f"P071 原图标不完整：{sorted(set(TARGETS)-set(originals))}")

    def line(x1, y1, x2, y2, name, width=1.55):
        shape = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, int(x1), int(y1), int(x2), int(y2))
        shape.name = name
        shape.line.color.rgb = WHITE
        shape.line.width = Pt(width)
        return shape

    def outline(kind, x, y, w, h, name, width=1.55):
        shape = slide.shapes.add_shape(kind, int(x), int(y), int(w), int(h))
        shape.name = name
        shape.fill.background()
        shape.line.color.rgb = WHITE
        shape.line.width = Pt(width)
        return shape

    def filled(kind, x, y, w, h, name):
        shape = slide.shapes.add_shape(kind, int(x), int(y), int(w), int(h))
        shape.name = name
        shape.fill.solid()
        shape.fill.fore_color.rgb = WHITE
        shape.line.fill.background()
        return shape

    for sid, kind in TARGETS.items():
        old = originals[sid]
        x, y, w, h = old.left, old.top, old.width, old.height
        old._element.getparent().remove(old._element)
        n = f"native-icon:p071:{kind}"
        if kind == "users":
            filled(MSO_SHAPE.OVAL, x+w*.37, y+h*.18, w*.26, h*.26, n+":head")
            outline(MSO_SHAPE.OVAL, x+w*.23, y+h*.51, w*.54, h*.27, n+":body")
            filled(MSO_SHAPE.OVAL, x+w*.12, y+h*.34, w*.16, h*.16, n+":left-head")
            filled(MSO_SHAPE.OVAL, x+w*.72, y+h*.34, w*.16, h*.16, n+":right-head")
        elif kind == "folder":
            pts=[(.15,.31),(.38,.31),(.49,.42),(.84,.42),(.84,.76),(.15,.76),(.15,.31)]
            for i in range(len(pts)-1):
                a,b=pts[i],pts[i+1]
                line(x+w*a[0],y+h*a[1],x+w*b[0],y+h*b[1],n+f":edge-{i}")
        elif kind == "monitor":
            outline(MSO_SHAPE.RECTANGLE,x+w*.14,y+h*.20,w*.72,h*.51,n+":screen")
            line(x+w*.50,y+h*.71,x+w*.50,y+h*.83,n+":stand")
            line(x+w*.34,y+h*.84,x+w*.66,y+h*.84,n+":base")
            line(x+w*.34,y+h*.47,x+w*.45,y+h*.56,n+":check-a",1.35)
            line(x+w*.45,y+h*.56,x+w*.67,y+h*.35,n+":check-b",1.35)
        else:
            # An outlined cloud keeps its silhouette visible at the source's 22.7 pt size.
            outline(MSO_SHAPE.CLOUD,x+w*.13,y+h*.22,w*.74,h*.57,n+":cloud",1.35)
            line(x+w*.50,y+h*.60,x+w*.50,y+h*.37,n+":up-stem",1.35)
            line(x+w*.50,y+h*.37,x+w*.40,y+h*.47,n+":up-left",1.35)
            line(x+w*.50,y+h*.37,x+w*.60,y+h*.47,n+":up-right",1.35)

    output.parent.mkdir(parents=True, exist_ok=True)
    ppt.save(output)
    return {"source": str(source), "output": str(output), "replaced_picture_ids": sorted(TARGETS), "native_shape_count": sum(s.name.startswith("native-icon:p071:") for s in slide.shapes)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    print(repair(args.input, args.out))
