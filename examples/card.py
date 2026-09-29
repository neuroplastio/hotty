#!/usr/bin/env python3
"""card.py — print an HTML card inline, or its text rendition without a host (M1).

    hotty run -- python3 examples/card.py
    python3 examples/card.py            # no host: plain text
"""
import os
import shutil
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "clients", "python"))
from hotty import Hotty  # noqa: E402

HTML = """
<style>
  .card { margin: 0.5rlh 1ch; padding: 0.5rlh 2ch; border-radius: 10px;
          border: 1px solid var(--hotty-ansi-8);
          background: linear-gradient(135deg, color-mix(in srgb, var(--hotty-bg) 80%, var(--hotty-ansi-4)),
                                              color-mix(in srgb, var(--hotty-bg) 85%, var(--hotty-ansi-5))); }
  h2 { margin: 0; font: 600 1.3em sans-serif; }
  .grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 1ch; margin-top: 0.5rlh; }
  .stat { background: rgba(0,0,0,.18); border-radius: 6px; padding: 4px 1ch; }
  .stat b { display: block; font: 700 1.4em sans-serif; color: var(--hotty-ansi-2); }
  .stat span { font: 0.8em sans-serif; opacity: .8; }
</style>
<div class="card">
  <h2>Build finished · <span style="color: var(--hotty-ansi-2)">passed</span></h2>
  <div class="grid">
    <div class="stat"><b>412</b><span>tests</span></div>
    <div class="stat"><b>0</b><span>failures</span></div>
    <div class="stat"><b>38.2 s</b><span>wall time</span></div>
  </div>
</div>
"""

TEXT = """Build finished · passed
  tests 412   failures 0   wall time 38.2 s
"""


def main():
    lam = Hotty()
    if not sys.stdin.isatty():
        sys.stdout.write(TEXT)
        return
    with Hotty.raw():
        caps = lam.query()
    if caps is None:
        sys.stdout.write(TEXT)
        return
    cols = min(shutil.get_terminal_size().columns, 90)
    lam.doc("card", HTML)
    lam.place("card", cols)  # r=auto; the cursor moves below the card


if __name__ == "__main__":
    main()
