#!/usr/bin/env python3
"""dash.py — a live dashboard on the alternate screen (M2).

    hotty run -- python3 examples/dash.py            # targeted patches
    hotty run -- python3 examples/dash.py --morph    # whole tree, morphed, every frame
    options: --hz 10  --seconds N (exit after N s and print the byte count)

q quits. Without a HOTTY host it draws a plain-text version.
"""
import os
import shutil
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "clients", "python"))
from hotty import Hotty  # noqa: E402

STYLE = """
<style>
  /* The dashboard fills its surface, whatever its size: the bottom cards take
     the height that is left and scroll inside if it is not enough. */
  html, body { height: 100%; }
  body { font-family: sans-serif; }
  .app { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr));
         grid-template-rows: auto auto minmax(0, 1fr);
         gap: 1ch; padding: 0.5rlh 1ch; height: 100%; box-sizing: border-box; }
  header { grid-column: 1 / -1; display: flex; align-items: baseline; gap: 2ch; }
  header h1 { margin: 0; font: 600 1.3em sans-serif; }
  header .clock { margin-left: auto; font-family: var(--hotty-font); color: var(--hotty-ansi-6); }
  .card { background: color-mix(in srgb, var(--hotty-bg) 88%, white); border-radius: 8px;
          padding: 0.5rlh 1ch; border: 1px solid color-mix(in srgb, var(--hotty-bg) 70%, white); }
  .card h2 { margin: 0 0 4px; font: 500 0.8em sans-serif; opacity: .7; text-transform: uppercase;
             letter-spacing: .05em; }
  .big { font: 700 1.6em sans-serif; white-space: nowrap; overflow: hidden; }
  .bar { height: 8px; border-radius: 4px; background: rgba(255,255,255,.08); margin-top: 6px; overflow: hidden; }
  .bar > i { display: block; height: 100%; width: calc(var(--p, 0) * 1%);
             background: linear-gradient(90deg, var(--hotty-ansi-2), var(--hotty-ansi-3), var(--hotty-ansi-1)); }
  .cores, .procs { min-height: 0; overflow: auto; }
  .cores { grid-column: 1 / 3; }
  /* As many columns of cores as fit: 24 cores need 12 rows, not 24. */
  #cores { display: grid; grid-template-columns: repeat(auto-fill, minmax(24ch, 1fr)); column-gap: 3ch; }
  .core { display: grid; grid-template-columns: 5ch 1fr 5ch; align-items: center; gap: 1ch;
          font: 0.85em var(--hotty-font); }
  .core .bar { margin: 0; }
  .procs { grid-column: 3 / 5; }
  table { width: 100%; border-collapse: collapse; font: 0.85em var(--hotty-font); }
  th { text-align: left; opacity: .6; font-weight: 500; }
  td.n { text-align: right; }
  tr:nth-child(even) td { background: rgba(255,255,255,.03); }
</style>
"""


def read_cpu():
    with open("/proc/stat") as f:
        lines = [l.split() for l in f if l.startswith("cpu")]
    return [(sum(map(int, l[1:])), int(l[4]) + int(l[5])) for l in lines]


def cpu_percent(prev, cur):
    out = []
    for (t0, i0), (t1, i1) in zip(prev, cur):
        dt = t1 - t0
        out.append(0.0 if dt <= 0 else 100.0 * (1 - (i1 - i0) / dt))
    return out


def meminfo():
    m = {}
    with open("/proc/meminfo") as f:
        for line in f:
            k, v = line.split(":", 1)
            m[k] = int(v.split()[0])
    total, avail = m["MemTotal"], m["MemAvailable"]
    return total, total - avail


def top_procs(n=8):
    rows = []
    page = os.sysconf("SC_PAGE_SIZE") // 1024
    for pid in os.listdir("/proc"):
        if not pid.isdigit():
            continue
        try:
            with open(f"/proc/{pid}/statm") as f:
                rss = int(f.read().split()[1]) * page
            with open(f"/proc/{pid}/comm") as f:
                name = f.read().strip()
        except OSError:
            continue
        rows.append((rss, pid, name))
    rows.sort(reverse=True)
    return rows[:n]


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def procs_rows(procs):
    return "".join(
        f"<tr><td>{p}</td><td>{esc(name)}</td><td class=n>{rss // 1024} MB</td></tr>" for rss, p, name in procs
    )


def core_rows(pcts):
    return "".join(
        f"<div class=core><span>cpu{i}</span><div class=bar><i id=c{i} style='--p:{p:.0f}'></i></div>"
        f"<span id=cv{i}>{p:4.0f}%</span></div>"
        for i, p in enumerate(pcts)
    )


def body(state):
    total, used = state["mem"]
    return f"""<div class=app id=app>
  <header><h1>hotty dash</h1><span id=mode>{state['mode']}</span><span class=clock id=clock>{state['clock']}</span></header>
  <div class=card><h2>cpu</h2><div class=big id=cpu>{state['cpu'][0]:.0f}%</div><div class=bar><i id=cpubar style='--p:{state['cpu'][0]:.0f}'></i></div></div>
  <div class=card><h2>memory</h2><div class=big id=mem>{used / 1048576:.1f} GB</div><div class=bar><i id=membar style='--p:{100 * used / total:.0f}'></i></div></div>
  <div class=card><h2>load</h2><div class=big id=load>{state['load']}</div></div>
  <div class=card><h2>frames</h2><div class=big id=frames>{state['frames']}</div></div>
  <div class="card cores"><h2>cores</h2><div id=cores>{core_rows(state['cpu'][1:])}</div></div>
  <div class="card procs"><h2>top by memory</h2><table><thead><tr><th>pid</th><th>name</th><th class=n>rss</th></tr></thead><tbody id=procs>{procs_rows(state['procs'])}</tbody></table></div>
</div>"""


def main():
    args = sys.argv[1:]
    morph = "--morph" in args
    hz = float(args[args.index("--hz") + 1]) if "--hz" in args else 10.0
    seconds = float(args[args.index("--seconds") + 1]) if "--seconds" in args else None
    # --cores K: update only the clock and K core bars per frame (patch-size experiments).
    only = int(args[args.index("--cores") + 1]) if "--cores" in args else None
    record = args[args.index("--record") + 1] if "--record" in args else None
    if record:
        # Write the command stream for --frames N frames to a file, as fast as
        # possible, for `hotty replay` (hotty-blitz's benchmark).
        return record_stream(record, morph, int(args[args.index("--frames") + 1]) if "--frames" in args else 100)
    lam = Hotty()
    size = shutil.get_terminal_size()
    sent = [0]
    real_write = lam.out.write

    def counting_write(b):
        sent[0] += len(b)
        return real_write(b)

    lam.out.write = counting_write

    with Hotty.raw():
        caps = lam.query()
        lam.write("\x1b[?1049h\x1b[?25l\x1b[H\x1b[2J")
        prev = read_cpu()
        state = {
            "mode": "morph" if morph else "patch",
            "clock": "",
            "cpu": [0.0] * len(prev),
            "mem": meminfo(),
            "load": "",
            "frames": 0,
            "procs": top_procs(),
        }
        if caps is not None:
            lam.doc("dash", STYLE + body(state))
            lam.write("\x1b[1;1H")
            lam.place("dash", size.columns, size.lines - 1, move_cursor=False)
        start = time.monotonic()
        baseline = sent[0]
        last_procs = 0.0
        try:
            while True:
                if lam.read(1.0 / hz):
                    _, keys = lam.take()
                    if b"q" in keys:
                        break
                now = time.monotonic()
                if seconds is not None and now - start > seconds:
                    break
                cur = read_cpu()
                state["cpu"] = cpu_percent(prev, cur)
                prev = cur
                state["mem"] = meminfo()
                state["load"] = " ".join(open("/proc/loadavg").read().split()[:3])
                state["clock"] = time.strftime("%H:%M:%S") + f".{int(now * 1000) % 1000:03d}"
                state["frames"] += 1
                if now - last_procs > 1.0:
                    state["procs"] = top_procs()
                    last_procs = now
                if caps is None:
                    total, used = state["mem"]
                    lam.write(
                        f"\x1b[H hotty dash (no host: text)  {state['clock']}\x1b[K\r\n"
                        f" cpu {state['cpu'][0]:5.1f}%   mem {used / 1048576:5.1f} GB   load {state['load']}\x1b[K"
                    )
                    continue
                with lam.sync():
                    if morph:
                        lam.patch("dash", "morph", "app", body(state))
                    elif only is not None:
                        lam.text("dash", "clock", state["clock"])
                        for i, p in enumerate(state["cpu"][1 : 1 + only]):
                            lam.var("dash", f"c{i}", "p", f"{p:.0f}")
                            lam.text("dash", f"cv{i}", f"{p:4.0f}%")
                    else:
                        total, used = state["mem"]
                        lam.text("dash", "clock", state["clock"])
                        lam.text("dash", "cpu", f"{state['cpu'][0]:.0f}%")
                        lam.var("dash", "cpubar", "p", f"{state['cpu'][0]:.0f}")
                        lam.text("dash", "mem", f"{used / 1048576:.1f} GB")
                        lam.var("dash", "membar", "p", f"{100 * used / total:.0f}")
                        lam.text("dash", "load", state["load"])
                        lam.text("dash", "frames", str(state["frames"]))
                        for i, p in enumerate(state["cpu"][1:]):
                            lam.var("dash", f"c{i}", "p", f"{p:.0f}")
                            lam.text("dash", f"cv{i}", f"{p:4.0f}%")
                        if now - last_procs < 1.0 / hz:
                            lam.patch("dash", "inner", "procs", procs_rows(state["procs"]))
                    lam.write(f"\x1b[{size.lines};1H q quits · {state['mode']} · {hz:g} Hz\x1b[K")
        except (KeyboardInterrupt, EOFError):
            pass
        frames = max(state["frames"], 1)
        per_frame = (sent[0] - baseline) / frames
        if caps is not None:
            lam.delete("dash")
        lam.write("\x1b[?25h\x1b[?1049l")
    line = f"dash: {state['mode']}: {state['frames']} frames, {per_frame:.0f} bytes/frame to the terminal"
    print(line)
    if os.environ.get("DASH_REPORT"):
        with open(os.environ["DASH_REPORT"], "a") as f:
            f.write(line + "\n")


def frame_ops(lam, state, morph, procs_changed):
    if morph:
        lam.patch("dash", "morph", "app", body(state))
        return
    total, used = state["mem"]
    lam.text("dash", "clock", state["clock"])
    lam.text("dash", "cpu", f"{state['cpu'][0]:.0f}%")
    lam.var("dash", "cpubar", "p", f"{state['cpu'][0]:.0f}")
    lam.text("dash", "mem", f"{used / 1048576:.1f} GB")
    lam.var("dash", "membar", "p", f"{100 * used / total:.0f}")
    lam.text("dash", "load", state["load"])
    lam.text("dash", "frames", str(state["frames"]))
    for i, p in enumerate(state["cpu"][1:]):
        lam.var("dash", f"c{i}", "p", f"{p:.0f}")
        lam.text("dash", f"cv{i}", f"{p:4.0f}%")
    if procs_changed:
        lam.patch("dash", "inner", "procs", procs_rows(state["procs"]))


def record_stream(path, morph, frames):
    import random

    rng = random.Random(7)
    with open(path, "wb") as f:
        lam = Hotty(out=f)
        ncores = 24
        state = {
            "mode": "morph" if morph else "patch",
            "clock": "00:00:00.000",
            "cpu": [0.0] * (ncores + 1),
            "mem": (32 << 20, 12 << 20),
            "load": "1.00 1.00 1.00",
            "frames": 0,
            "procs": [(rng.randint(100, 900) << 10, str(1000 + i), f"proc{i}") for i in range(8)],
        }
        lam.doc("dash", STYLE + body(state))
        lam.place("dash", 126, 36, move_cursor=False)
        for n in range(frames):
            state["frames"] = n + 1
            state["clock"] = f"00:00:{n // 10:02d}.{(n % 10) * 100:03d}"
            state["cpu"] = [rng.random() * 100 for _ in range(ncores + 1)]
            state["mem"] = (32 << 20, (12 << 20) + rng.randint(0, 1 << 18))
            state["load"] = " ".join(f"{rng.random() * 4:.2f}" for _ in range(3))
            procs_changed = n % 10 == 0
            if procs_changed:
                state["procs"] = [(rng.randint(100, 900) << 10, str(1000 + i), f"proc{i}") for i in range(8)]
            with lam.sync():
                frame_ops(lam, state, morph, procs_changed)


if __name__ == "__main__":
    main()
