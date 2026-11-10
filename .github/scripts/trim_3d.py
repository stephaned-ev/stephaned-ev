"""Post-process the images made by github-profile-3d-contrib.

- removes the language pie chart;
- fits the radar's log scale to the data: rings above the first power of ten
  that covers the largest value are dropped and the rest is enlarged, so the
  ring labels stay true.

Usage: trim_3d.py FILE.svg [FILE.svg ...]
"""
import math
import re
import sys
import xml.etree.ElementTree as ET

SVG = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG)
RINGS = 5  # 1, 10, 100, 1K, 10K
NUM = re.compile(r"-?\d+(?:\.\d+)?")


def tag(el):
    return el.tag.rsplit("}", 1)[-1]


def scale_attr(el, name, k):
    if name in el.attrib:
        el.set(name, NUM.sub(lambda m: f"{float(m.group()) * k:.2f}", el.get(name)))


def is_radar(group):
    return any(tag(e) == "polygon" and e.get("class") == "radar" for e in group.iter())


def fit_radar(group):
    values = [int(t.text) for t in group.iter(f"{{{SVG}}}title") if (t.text or "").isdigit()]
    top = max(values, default=0)
    keep = min(RINGS, max(2, math.ceil(math.log10(top)) + 1 if top > 1 else 2))
    if keep == RINGS:
        return
    k = RINGS / keep
    sides = sum(1 for e in group if tag(e) == "g")  # one axis per metric
    ring_lines = [e for e in group if tag(e) == "line"]
    labels = [e for e in group if tag(e) == "text"]
    for i, line in enumerate(ring_lines):
        if i // sides >= keep:
            group.remove(line)
        else:
            for a in ("x1", "y1", "x2", "y2"):
                scale_attr(line, a, k)
    for i, label in enumerate(labels):
        if i >= keep:
            group.remove(label)
        else:
            scale_attr(label, "y", k)
    for axis in (e for e in group if tag(e) == "g"):
        for line in axis.iter(f"{{{SVG}}}line"):
            scale_attr(line, "x1", k)
            scale_attr(line, "y1", k)
    for poly in group.iter(f"{{{SVG}}}polygon"):
        scale_attr(poly, "points", k)
        for anim in poly.iter(f"{{{SVG}}}animate"):
            scale_attr(anim, "values", k)


def process(path):
    tree = ET.parse(path)
    root = tree.getroot()
    panels = [g for g in root if tag(g) == "g" and g.get("transform")]
    radars = [g for g in panels if is_radar(g)]
    if not radars:  # layout changed upstream: leave the file alone
        print(f"{path}: radar not found, left unchanged")
        return
    for g in panels:
        if g in radars:
            fit_radar(g)
        else:
            root.remove(g)  # the pie chart
    tree.write(path, encoding="utf-8", xml_declaration=False)
    print(f"{path}: done")


if __name__ == "__main__":
    for p in sys.argv[1:]:
        process(p)
