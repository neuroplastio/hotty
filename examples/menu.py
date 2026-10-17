#!/usr/bin/env python3
"""menu.py — a program's menu, with keys and without (SPEC §10.7).

    hotty run -- python3 examples/menu.py

The program sends what it can do as its menu. Space starts a sequence: the
host shows the level the keys reach, `f` goes into File, and a key ends it.
The actions without keys (Sort, Reload) are reached only by a pick: from
a multiplexer's palette, such as plx's, or from whatever drives the
program, by name. Every action the program runs is printed;
q quits.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "clients", "python"))
import hotty  # noqa: E402
from hotty import Hotty, MenuItem, MenuTree  # noqa: E402

LABELS = {
    "file-new": "New file",
    "file-rename": "Rename",
    "sort-name": "Sort by name",
    "sort-time": "Sort by time",
    "reload": "Reload",
    "quit": "Quit",
}


def tree(sorted_by):
    """The menu: what the program can do now. Sorting by what it is sorted
    by already does nothing, so that item is not enabled."""
    return MenuTree("Files", [
        MenuItem("space", "Leader", items=[
            MenuItem("f", "File", items=[
                MenuItem("n", "New file", "file-new"),
                MenuItem("r", "Rename", "file-rename"),
            ]),
            MenuItem("q", "Quit", "quit"),
        ]),
        MenuItem(label="Sort", items=[
            MenuItem(label="By name", name="sort-name", enabled=sorted_by != "name"),
            MenuItem(label="By time", name="sort-time", enabled=sorted_by != "time"),
        ]),
        MenuItem(label="Reload", name="reload"),
    ])


# The keys that run an action at the end of a sequence.
SEQUENCES = {("space", "f", "n"): "file-new", ("space", "f", "r"): "file-rename", ("space", "q"): "quit"}
GROUPS = {("space",), ("space", "f")}


def main():
    lam = Hotty()
    with Hotty.raw():
        caps = lam.query()
        if caps is None:
            print("menu.py needs a hotty host: run it under `hotty run`.")
            return
        if not caps.has(hotty.FEATURE_MENU):
            print("this host takes no menus (the feature menu, SPEC §4).")
            return
        lam.write("\x1b[?1049h\x1b[2J\x1b[1;1H")
        lam.write("menu.py: Space for the leader, a pick for the rest, q to quit.\r\n")
        sorted_by = "name"
        lam.write(hotty.menu(tree(sorted_by)))
        seq = ()

        def run(name):
            nonlocal sorted_by
            lam.write(f"ran {name}: {LABELS.get(name, name)}\r\n")
            if name in ("sort-name", "sort-time"):
                sorted_by = name[5:]
                lam.write(hotty.menu(tree(sorted_by)))
            return name == "quit"

        try:
            while True:
                lam.read(1.0)
                msgs, keys = lam.take()
                done = False
                for m in msgs:
                    if m["a"] == "ev" and m["e"] == "command":
                        done = run(m.body["name"]) or done
                # The keys as SPEC §10.4 names them: a space is "space".
                for key in hotty.decode_keys(keys):
                    if not seq and key == "q":
                        done = True
                        break
                    if not seq and key != "space":
                        continue
                    seq += (key,)
                    if seq in GROUPS:
                        lam.write(hotty.menu_show(list(seq)))
                        continue
                    lam.write(hotty.menu_hide())
                    name = SEQUENCES.get(seq)
                    seq = ()
                    if name:
                        done = run(name) or done
                if done:
                    break
        finally:
            lam.write(hotty.menu())
            lam.write("\x1b[?1049l")


if __name__ == "__main__":
    main()
