"""Bytes on the wire for typical HOTTY messages, with the reference client.

    python3 -I vault/knowledge/wire_sizes.py [path/to/kit.css]

The numbers in wire-sizes.md come from this. Run it again once 0.3 is
folded, with the client then speaking 0.3, to check what the fold saved.
kit.css is hotty-a2ui's rendition/html/kit.css.
"""

import os
import sys
import zlib

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "clients", "python"))
import hotty as h  # noqa: E402

ENVELOPE = 9  # ESC ] 7279 ; … ESC \


def b64(n):
    return (n + 2) // 3 * 4


def batched(ops):
    """A delta list as FOLD-01 proposes: one a=delta, one msgpack body,
    compressed at 256 bytes or more as SDK.md §3.3 does today."""
    ctl, body = "a=delta:s=dash", h.pack({"ops": ops})
    z = zlib.compress(body, 6)
    use = z if len(body) >= 256 and len(z) < len(body) else body
    return ENVELOPE + len(ctl) + (4 if use is z else 0) + 1 + b64(len(use))


def var_ops(n):
    return [{"op": "var", "t": f"cpu{i}", "k": "p", "v": str(40 + i)} for i in range(n)]


def main():
    print("one var delta  ", len(h.set_var("dash", "cpu", "p", "42")))
    print("one text delta ", len(h.set_text("dash", "clock", "12:00:01")))
    for n in (1, 2, 5, 15, 50):
        today = sum(len(h.set_var("dash", f"cpu{i}", "p", str(40 + i))) for i in range(n))
        print(f"{n:3d} var deltas  today {today:5d}  as one list {batched(var_ops(n)):5d}")
    print("place_at, hover", len(h.place_at("tool", 12, 30, h.Placement(cols=60, rows=20, z=5, hover=True), q=2)))

    area = {"c": 3, "r": 7, "w": 12, "h": 1}
    click = h.pack({"area": area})
    print("click event    ", ENVELOPE + len("a=ev:s=card:e=click:t=go") + 1 + b64(len(click)))
    drag = h.pack({"c": 10, "r": 4, "keys": [], "x": 7})
    print("drag event     ", ENVELOPE + len("a=ev:s=grid:e=drag:t=cell-4-10") + 1 + b64(len(drag)))
    view = h.pack({"in": {f"sec-{i:02d}": {"c": 0, "r": i * 3 - 5, "w": 60, "h": 3} for i in range(20)}, "end": False})
    print("view, 20 in    ", ENVELOPE + len("a=ev:s=doc:e=view:t=") + 1 + b64(len(view)))

    corpus = os.path.join(os.path.dirname(__file__), "..", "..", "corpus", "04-table.html")
    doc = open(corpus, "rb").read()
    print("04-table.html  ", len(doc), "B; morphed whole:", len(h.morph_to("t", "", doc.replace(b"</td>", b" </td>", 1).decode())))

    if len(sys.argv) > 1:
        css = open(sys.argv[1], "rb").read()
        print("kit.css        ", len(css), "B; on the wire today:", len(h.res("kit", "text/css", css)))
        for level in (1, 6, 9):
            print(f"  zlib level {level}: {b64(len(zlib.compress(css, level)))} B of base64")


if __name__ == "__main__":
    main()
