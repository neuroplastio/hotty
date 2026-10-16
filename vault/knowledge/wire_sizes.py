"""Bytes on the wire for typical HOTTY messages, with the reference client.

    python3 -I vault/knowledge/wire_sizes.py [path/to/kit.css]

The 0.3 column of wire-sizes.md comes from this, the client speaking 0.3.
The 0.2 column was measured the same way on 2026-10-14, before the fold.
kit.css is hotty-a2ui's rendition/html/kit.css.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "clients", "python"))
import hotty as h  # noqa: E402

ENVELOPE = 9  # ESC ] 7279 ; … ESC \


def b64(n):
    return (n + 2) // 3 * 4


def event(control, detail):
    """An event's bytes: its control and its detail, as a host sends it."""
    return ENVELOPE + len(control) + 1 + b64(len(h.pack(detail)))


def main():
    print("one var delta  ", len(h.set_var("dash", "cpu", "p", "42")))
    print("one text delta ", len(h.set_text("dash", "clock", "12:00:01")))
    for n in (1, 2, 5, 15, 50):
        frame = h.delta("dash", *(h.var(f"cpu{i}", "p", str(40 + i)) for i in range(n)))
        print(f"{n:3d} var ops, one delta  {len(frame):5d}")
    p = h.Placement(cols=60, rows=20, z=5, hover=True)
    print("place_at, hover, first", len(h.place_at("tool", 12, 30, p)))
    p.hover = None  # the flag holds (SPEC §5.2): later frames leave it out
    print("place_at, again       ", len(h.place_at("tool", 12, 30, p)))

    area = {"c": 3, "r": 7, "w": 12, "h": 1}
    print("click event    ", event("a=ev:s=card:e=click:t=go", {"area": area}))
    print("drag event     ", event("a=ev:s=grid:e=drag:t=cell-4-10", {"c": 10, "r": 4, "x": 7}))
    view = {"in": {f"sec-{i:02d}": {"c": 0, "r": i * 3 - 5, "w": 60, "h": 3} for i in range(20)}, "end": False}
    print("view, 20 in    ", event("a=ev:s=doc:e=view", view))

    corpus = os.path.join(os.path.dirname(__file__), "..", "..", "corpus", "04-table.html")
    doc = open(corpus, "rb").read()
    changed = doc.replace(b"</td>", b" </td>", 1).decode()
    print("04-table.html  ", len(doc), "B; morphed whole:", len(h.morph_to("t", "", changed)))

    # A leader with four groups of six actions, and ten actions no key
    # reaches: the tree once, then a few bytes a key of a sequence.
    groups = [("f", "File"), ("b", "Buffer"), ("g", "Git"), ("w", "Window")]
    tree = h.MenuTree("Editor", [h.MenuItem("Space", "Leader", items=[
        h.MenuItem(k, l, items=[h.MenuItem(c, f"{l} action {c}", f"{l.lower()}-{c}") for c in "abcdef"])
        for k, l in groups])] + [h.MenuItem(label=f"Action {i}", name=f"action-{i}") for i in range(10)])
    print("menu tree      ", len(h.menu(tree)))
    seq = len(h.menu_show(["Space"])) + len(h.menu_show(["Space", "g"])) + len(h.menu_hide())
    print("Space g a      ", seq, "B: show, show, hide")

    if len(sys.argv) > 1:
        css = open(sys.argv[1], "rb").read()
        print("kit.css        ", len(css), "B; as a resource:", len(h.res("kit", "text/css", css)))


if __name__ == "__main__":
    main()
