#!/usr/bin/env python3
"""files.py — a file list whose rows have their own menu (V7-01, SDK.md §4.7).

    hotty run -- python3 examples/files.py [--log events.jsonl]

Right-click a row (or focus it and press Shift+F10 or the Menu key): the
program opens a menu of its own, a second surface at a higher z with its top
left at the pointer, flipped left or up at the screen's edge. The rows say
`secondary` in their data-on, so the terminal opens none; elsewhere a
right-click is the terminal's own menu.

The menu's document is sent once, unplaced, and each open only places it and
updates its items. It has the keyboard: Enter or a click does an item;
Escape, a click elsewhere or a second secondary press closes it. Tab and
Shift+Tab move between items, and so do Up and Down: its data-keys bind the
arrows to `program` (SPEC §10.2) and the program turns them into a focus.
A left click selects a row; q quits. --log appends every event as JSON lines.
"""
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "clients", "python"))
import hotty  # noqa: E402
from hotty import Hotty, Placement  # noqa: E402

FILES = ["README.md", "build.zig", "notes.md", "LICENSE", "main.py", "todo.txt"]
LIST_X, LIST_Y, LIST_COLS = 2, 1, 50  # the list's cell on the screen
MENU_COLS, MENU_ROWS, ROW_ROWS = 22, 6, 2
ITEMS = [("open", "Open"), ("rename", "Rename"), ("copy", "Copy path"), ("delete", "Delete")]

LIST = """
<style>
  body { font: 14px var(--hotty-font); margin: 0; }
  .title, .row, #status { height: calc(2 * var(--hotty-cell-h)); line-height: calc(2 * var(--hotty-cell-h)); padding: 0 12px; outline: none; }
  .title { font: 600 14px sans-serif; }
  .row:hover { background: color-mix(in srgb, var(--hotty-fg) 8%, transparent); }
  .row.sel { background: color-mix(in srgb, var(--hotty-accent) 25%, transparent); }
  .row:focus { box-shadow: inset 2px 0 var(--hotty-accent); }
  #status { opacity: .7; }
</style>
<div class=title>Files</div>
@ROWS@
<div id=status>Right-click a row for its menu</div>
""".replace("@ROWS@", "\n".join(f'<div class=row id="{f}" tabindex=0 data-on="secondary click">{f}</div>' for f in FILES))

MENU = """
<style>
  body { margin: 0; font: 13px sans-serif; }
  #card { box-sizing: border-box; width: calc(100% - 8px); padding: 4px 3px; border: 1px solid var(--hotty-ansi-8); border-radius: 6px;
          background: color-mix(in srgb, var(--hotty-bg) 90%, white); color: var(--hotty-fg); box-shadow: 0 2px 6px rgba(0,0,0,.5); }
  .item { display: block; box-sizing: border-box; width: 100%; height: var(--hotty-cell-h); padding: 0 10px; border: 0; border-radius: 3px;
          background: none; color: inherit; font: inherit; text-align: left; outline: none; }
  .item:hover, .item:focus { background: var(--hotty-accent); color: var(--hotty-bg); }
  .item.danger { color: var(--hotty-ansi-9); }
  .item.danger:hover, .item.danger:focus { background: var(--hotty-ansi-9); color: var(--hotty-bg); }
  .item:disabled { opacity: .4; background: none; }
  hr { margin: calc(var(--hotty-cell-h) / 2 - 1px) 3px; border: 0; border-top: 1px solid var(--hotty-ansi-8); }
</style>
<div id=card data-keys="arrow_up=program arrow_down=program">
  <button class=item id=open data-on=click>Open</button>
  <button class=item id=rename data-on=click>Rename</button>
  <button class=item id=copy data-on=click>Copy path</button>
  <hr>
  <button class="item danger" id=delete data-on=click>Delete</button>
</div>
"""


def main():
    args = sys.argv[1:]
    log = open(args[args.index("--log") + 1], "a") if "--log" in args else None

    def record(kind, **fields):
        if log:
            log.write(json.dumps({"kind": kind, **fields}) + "\n")
            log.flush()

    lam = Hotty()
    size = shutil.get_terminal_size()
    with Hotty.raw():
        if lam.query() is None:
            print("files.py needs a hotty host: run it under `hotty run`.")
            return
        lam.write("\x1b[?1049h\x1b[?25l\x1b[2J\x1b[1;1H")
        lam.doc("list", LIST)
        lam.write(hotty.place_at("list", LIST_X, LIST_Y, Placement(cols=LIST_COLS)))
        lam.doc("menu", MENU)  # kept ready, unplaced (not detached: that is inert)
        record("ready", cols=size.columns, lines=size.lines)

        areas = {}  # a row's cells, as its events reported them
        row = menu_for = item = None  # the last row, the open menu's row, its focused item

        def say(text):
            lam.text("list", "status", text)

        def close(refocus=True):
            nonlocal menu_for
            if menu_for is None:
                return
            f, menu_for = menu_for, None
            lam.hide("menu")
            if refocus:
                lam.focus("list", f)

        def open_menu(f, x, y, below=0):
            """Opens f's menu with its top left at screen cell (x, y), flipped
            left or up where it would pass the edge (`below`: the height to
            clear when flipping up, so it opens above the element)."""
            nonlocal menu_for, item
            if x + MENU_COLS > size.columns:
                x = max(0, x - MENU_COLS)
            if y + MENU_ROWS > size.lines:
                y = max(0, y - MENU_ROWS - below)
            ops = [hotty.attr(i, "title", f"{label} {f}") for i, label in ITEMS]
            ops.append(hotty.attr("delete", "disabled", "") if f == "LICENSE" else hotty.unattr("delete", "disabled"))
            lam.delta("menu", *ops)
            lam.write(hotty.place_at("menu", x, y, Placement(cols=MENU_COLS, rows=MENU_ROWS, z=10)))
            menu_for, item = f, "open"
            lam.focus("menu", "open")
            record("menu", file=f, x=x, y=y)

        def pick(name):
            f = menu_for
            close()
            label = dict(ITEMS)[name]
            say(f"{label}: {f}")
            record("action", action=name, file=f)

        def move(step):
            nonlocal item
            ids = [i for i, _ in ITEMS if (i, menu_for) != ("delete", "LICENSE")]
            item = ids[(ids.index(item) + step) % len(ids)]
            lam.focus("menu", item)

        try:
            while True:
                lam.read(1.0)
                msgs, keys = lam.take()
                for m in msgs:
                    if m["a"] != "ev":
                        continue
                    ev, t = m.event(), m["t"] or ""
                    record("event", s=m["s"], e=m["e"], t=m["t"], detail=m.body)
                    if m["s"] == "menu":
                        if ev.kind == "click" and t in dict(ITEMS):
                            pick(t)
                        elif ev.kind == "focus" and t in dict(ITEMS):
                            item = t
                        elif ev.kind == "blur":
                            close(refocus=False)
                    elif ev.kind == "press" and ev.button() == 2 and t in FILES:
                        row, areas[t] = t, ev.area()
                        # c, r are the list's cell: add its place on the screen.
                        open_menu(t, LIST_X + ev.c(), LIST_Y + ev.r(), below=1)
                    elif ev.kind == "click" and t in FILES:
                        row, areas[t] = t, ev.area()
                        for f in FILES:
                            lam.attr("list", f, "class", "row sel" if f == t else "row")
                        say(f"Selected: {t}")
                    elif ev.kind == "focus" and t in FILES:
                        row = t
                for key in hotty.decode_keys(keys):
                    if menu_for:
                        if key == "arrow_down":
                            move(1)
                        elif key == "arrow_up":
                            move(-1)
                        elif key == "enter":
                            pick(item)
                        elif key == "escape":
                            close()
                    elif key in ("shift+f10", "context_menu") and row:
                        a = areas.get(row) or hotty.Area(0, 2 + ROW_ROWS * FILES.index(row), LIST_COLS, ROW_ROWS)
                        open_menu(row, LIST_X + a.c, LIST_Y + a.r + a.h, below=a.h)
                    elif key == "q":
                        raise KeyboardInterrupt
                    record("key", key=key)
        except (KeyboardInterrupt, EOFError):
            pass
        record("exit")
        lam.delete("menu")
        lam.delete("list")
        lam.write("\x1b[?25h\x1b[?1049l")


if __name__ == "__main__":
    main()
