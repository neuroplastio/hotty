#!/usr/bin/env python3
"""grid.py — a large document with one cell changing per frame.

    hotty run -- python3 examples/grid.py                   # 32768 cells, groups of 8
    options: --cells N  --fanout F (0: one flat flex grid)  --hz 10  --per-frame K
             --contain (CSS containment on groups and cells, for browser hosts)

The same shapes as hotty-blitz's `hotty bench`: nested flex groups of F fixed-size cells, or
one flat grid. Each frame sends K text patches to cells on screen, so the cost
of a frame should depend on K and on the depth of the tree, not on N. q quits.
"""
import os
import shutil
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "clients", "python"))
from hotty import Hotty  # noqa: E402

STYLE = """<style>
  html, body { margin: 0; overflow: hidden; font: 12px var(--hotty-font); }
  .g { display: flex; flex-wrap: wrap; gap: 1px; }
  .c { width: 44px; height: 16px; overflow: hidden; text-align: center;
       background: color-mix(in srgb, var(--hotty-bg) 85%, white); }
</style>"""


def group(out, first, n, fanout):
    """n cells from index `first`, nested in groups of `fanout` (as bench_tree)."""
    if fanout == 0 or n <= fanout:
        out.append("<div class=g>")
        out.extend(f"<span class=c id=c{i}>{i % 1000}</span>" for i in range(first, first + n))
        out.append("</div>")
        return
    per = -(-n // fanout)
    out.append("<div class=g>")
    start = first
    while start < first + n:
        c = min(per, first + n - start)
        group(out, start, c, fanout)
        start += c
    out.append("</div>")


def main():
    args = sys.argv[1:]

    def opt(name, default, kind=int):
        return kind(args[args.index(name) + 1]) if name in args else default

    cells = opt("--cells", 32768)
    fanout = opt("--fanout", 8)
    hz = opt("--hz", 10.0, float)
    per_frame = opt("--per-frame", 1)
    contain = "--contain" in args
    lam = Hotty()
    size = shutil.get_terminal_size()
    with Hotty.raw():
        if lam.query() is None:
            print("grid.py needs a HOTTY host (`hotty run`, or a terminal that speaks HOTTY)")
            return
        parts = [STYLE]
        if contain:
            parts.append("<style>.g { contain: layout paint; } .c { contain: strict; }</style>")
        group(parts, 0, cells, fanout)
        lam.write("\x1b[?1049h\x1b[?25l\x1b[H\x1b[2J")
        lam.doc("grid", "".join(parts))
        lam.place("grid", size.columns, size.lines - 1, move_cursor=False)
        tick = 0
        try:
            while True:
                if lam.read(1.0 / hz):
                    _, keys = lam.take()
                    if b"q" in keys:
                        break
                tick += 1
                with lam.sync():
                    # The first cells in document order are the ones on screen.
                    for k in range(per_frame):
                        c = (tick * 7 + k * 13) % 64
                        lam.text("grid", f"c{c}", str((c * 7 + tick) % 1000))
                    lam.write(
                        f"\x1b[{size.lines};1H q quits · {cells} cells · fanout {fanout} · {hz:g} Hz\x1b[K"
                    )
        except (KeyboardInterrupt, EOFError):
            pass
        lam.write("\x1b[?25h\x1b[?1049l")


if __name__ == "__main__":
    main()
