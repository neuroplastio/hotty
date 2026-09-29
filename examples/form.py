#!/usr/bin/env python3
"""form.py — a settings form (M3, Q-0005).

    hotty run -- python3 examples/form.py [--log events.jsonl]

The form holds the keyboard from the start. Typing, Tab, Space and clicks stay
in the terminal; the program only hears `change`, `click` and `submit`.
Esc hands the keyboard back to the program; then `f` focuses the form again
and `q` quits.
"""
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "clients", "python"))
from hotty import Hotty  # noqa: E402

HTML = """
<style>
  body { font: 15px/1.2 sans-serif; }
  form { padding: 8px 16px; }
  h1 { margin: 0 0 8px; font: 600 20px/28px sans-serif; height: 28px; }
  .row { display: flex; align-items: center; height: 40px; }
  .row > label:first-child { width: 120px; opacity: .8; }
  input[type=text], input[type=email] { width: 300px; height: 26px; box-sizing: border-box;
      padding: 0 8px; border-radius: 6px; border: 1px solid var(--hotty-ansi-8);
      background: color-mix(in srgb, var(--hotty-bg) 80%, black); color: var(--hotty-fg);
      font: 14px var(--hotty-font); }
  input:focus { border-color: var(--hotty-ansi-4); outline: 2px solid color-mix(in srgb, var(--hotty-ansi-4) 40%, transparent); }
  .opts label { margin-right: 16px; }
  .buttons { display: flex; gap: 12px; height: 44px; align-items: center; margin-left: 120px; }
  button { height: 30px; width: 100px; border-radius: 6px; border: 0; font: 600 14px sans-serif;
           background: var(--hotty-ansi-4); color: var(--hotty-bg); }
  button:hover { filter: brightness(1.15); }
  button:focus { outline: 2px solid var(--hotty-fg); }
  button#cancel { background: color-mix(in srgb, var(--hotty-bg) 70%, white); color: var(--hotty-fg); }
  #status { margin-left: 120px; height: 24px; opacity: .8; font: 13px var(--hotty-font); }
</style>
<form id=settings>
  <h1>Settings</h1>
  <div class=row><label for=name>Name</label><input type=text id=name name=name value=""></div>
  <div class=row><label for=email>Email</label><input type=email id=email name=email value=""></div>
  <div class="row opts"><label>Notify</label><label><input type=checkbox id=notify name=notify value=yes> on build</label></div>
  <div class="row opts"><label>Theme</label>
    <label><input type=radio id=dark name=theme value=dark checked> dark</label>
    <label><input type=radio id=light name=theme value=light> light</label></div>
  <div class=buttons><button type=submit id=save>Save</button><button type=button id=cancel>Cancel</button></div>
  <div id=status>Tab: next field · Esc: keyboard back</div>
</form>
"""


def main():
    args = sys.argv[1:]
    log_path = args[args.index("--log") + 1] if "--log" in args else None
    log = open(log_path, "a") if log_path else None

    def record(kind, **fields):
        if log:
            log.write(json.dumps({"kind": kind, **fields}) + "\n")
            log.flush()

    lam = Hotty()
    size = shutil.get_terminal_size()
    with Hotty.raw():
        caps = lam.query()
        if caps is None:
            print("form.py needs a HOTTY host: run it under `hotty run`.")
            return
        lam.write("\x1b[?1049h\x1b[?25l\x1b[2J\x1b[1;1H")
        lam.doc("form", HTML)
        # r=auto: the host sizes the surface to the form, whatever its cell size.
        lam.place("form", min(size.columns, 60), move_cursor=False)
        lam.focus("form", "name")
        record("ready")
        focused = True

        def status(text):
            lam.text("form", "status", text)

        def footer():
            where = "form has the keyboard (Esc: give it back)" if focused else "program has the keyboard (f: focus form, q: quit)"
            lam.write(f"\x1b[{size.lines};1H {where}\x1b[K")

        footer()
        try:
            while True:
                lam.read(1.0)
                msgs, keys = lam.take()
                for m in msgs:
                    if m["a"] != "ev":
                        continue
                    detail = m.json
                    record("event", e=m["e"], t=m["t"], detail=detail)
                    e = m["e"]
                    if e == "change":
                        status(f"{m['t']} changed: {json.dumps(detail)}")
                    elif e == "click" and m["t"] == "cancel":
                        status("cancelled")
                    elif e == "submit":
                        status("saved: " + ", ".join(f"{k}={v}" for k, v in (detail or {}).items()))
                    elif e == "blur":
                        focused = False
                        footer()
                    elif e == "focus":
                        focused = True
                        footer()
                if keys:
                    record("keys", data=keys.decode("utf-8", "replace"))
                    if keys == b"\x1b":
                        lam.blur("form")
                        focused = False
                        footer()
                    elif b"f" in keys and not focused:
                        lam.focus("form")
                        focused = True
                        footer()
                    elif b"q" in keys and not focused:
                        break
        except (KeyboardInterrupt, EOFError):
            pass
        record("exit")
        lam.delete("form")
        lam.write("\x1b[?25h\x1b[?1049l")


if __name__ == "__main__":
    main()
