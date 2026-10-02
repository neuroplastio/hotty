#!/usr/bin/env python3
"""bubbros.py — Bub-n-Bros in a HOTTY surface, the game itself unchanged.

    scripts/bubbros-fetch.sh                        # the game, at ../bubbros
    hotty run -- python3 examples/bubbros.py
    (xterm-addon-hotty) python3 serve.py --examples # then /?run=bubbros

Keys: ← → move, ↑ jump, ↓ or Space fire; a second player on A D, W, S.
      q or Esc quits.

The game server (gamesrv + bubbob from fpiesche/bub-n-bros, MIT) runs in this
process at 40 Hz, as bb_tornado.py runs it for browsers. Its art is Sebastian
Wegner's "Bub & Bob", used with the project's permission and not copied here;
it gets replaced before anything built on it is published.

Each frame the game describes the screen as a list of ~380 sprites (walls
included), of which a handful move. The canvas client repaints all of them.
Here each sprite is an element, and only the ones that changed get a delta
(one `attr style`), inside synchronized output: the host repaints only those.

Key releases come from the kitty keyboard protocol (SPEC §10.3). Where the
terminal does not speak it, a key counts as released when its auto-repeat
stops.
"""
import os
import re
import signal
import struct
import sys
import time
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "clients", "python"))
from hotty import Hotty  # noqa: E402

GAME_DIR = os.path.abspath(os.environ.get("BUBBROS_DIR") or os.path.join(HERE, "..", "..", "bubbros"))
FRAME = 0.025  # the game's own step (bb_tornado.py's periodic callback)

STYLE = """<style>
  html, body { margin: 0; background: #000; overflow: hidden; }
  #board { position: relative; overflow: hidden; background: #000; margin: 0 auto; }
  .s { position: absolute; image-rendering: pixelated; background-repeat: no-repeat; }
</style>"""


def png_rgba(width, height, rows):
    """A PNG of 8-bit RGBA rows (bytes), with zlib from the standard library."""

    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)

    raw = b"".join(b"\x00" + r for r in rows)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw, 6))
        + chunk(b"IEND", b"")
    )


def ppm_to_png(data, colorkey):
    """The game's P6 pixmaps, with its colour key as transparency."""
    if isinstance(data, str):
        data = data.encode("latin-1")
    fields, pos = [], 0
    while len(fields) < 4:
        m = re.compile(rb"\s*(#[^\n]*\n\s*)*(\S+)").match(data, pos)
        fields.append(m.group(2))
        pos = m.end()
    assert fields[0] == b"P6", fields[0]
    w, h = int(fields[1]), int(fields[2])
    pixels = data[pos + 1 : pos + 1 + w * h * 3]
    if isinstance(colorkey, int):
        key = bytes(((colorkey >> 16) & 255, (colorkey >> 8) & 255, colorkey & 255))
    elif colorkey is not None:
        key = bytes(colorkey[:3])
    else:
        key = None
    rows = []
    for y in range(h):
        row = pixels[y * w * 3 : (y + 1) * w * 3]
        out = bytearray()
        for x in range(0, len(row), 3):
            px = row[x : x + 3]
            out += px + (b"\x00" if px == key else b"\xff")
        rows.append(bytes(out))
    return png_rgba(w, h, rows)


def png_size(png):
    return struct.unpack(">II", png[16:24])


class Icon:
    __slots__ = ("res", "x", "y", "w", "h", "bw", "bh", "alpha")


class Screen:
    """What the terminal shows: resources, the board, and a pool of sprite
    elements whose styles follow the game's drawing list slot by slot."""

    def __init__(self, lam, gamesrv, width, height):
        self.lam = lam
        self.gamesrv = gamesrv
        self.width, self.height = width, height
        self.bitmaps = {}  # bitmap object id → (resource id, width, height)
        self.icons = {}  # icon code → Icon
        self.pending = []  # icons defined since the last frame
        self.slots = []  # style last sent per slot ("" = not created)
        self.scale = 1.0
        self.frames = self.changed = 0
        self.bytes = 0

    # The game's client interface (what bb_tornado's socket handler answers).
    def __getattr__(self, name):
        if name.startswith("gs_"):
            return lambda *args, **kwds: None
        raise AttributeError(name)

    def gs_send_definition(self, chunk):
        if hasattr(chunk, "code"):
            self.pending.append(chunk)

    def write_message(self, message):
        pass

    # ------------------------------------------------------------------

    def define(self, icon):
        bitmap = icon.origin[0]
        key = id(bitmap)
        if key not in self.bitmaps:
            png = self._png(bitmap)
            res = f"b{len(self.bitmaps)}"
            self.lam.res(res, "image/png", png)
            self.bitmaps[key] = (res, *png_size(png))
        res, bw, bh = self.bitmaps[key]
        _, x, y = icon.origin
        i = Icon()
        i.res, i.x, i.y, i.w, i.h, i.bw, i.bh, i.alpha = res, x, y, icon.w, icon.h, bw, bh, icon.alpha
        self.icons[icon.code] = i

    def _png(self, bitmap):
        name = bitmap.filename
        if "." in name:
            static = os.path.join(GAME_DIR, "static", name[: name.index(".")] + ".png")
            if os.path.exists(static):
                with open(static, "rb") as f:
                    return f.read()
        return ppm_to_png(bitmap.read(), bitmap.colorkey)

    def fit(self, cols, rows, cell_w, cell_h):
        """The largest scale that fits (pixels stay square: `pixelated`)."""
        k = min(cols * cell_w / self.width, rows * cell_h / self.height)
        self.scale = round(k, 3)

    def board_html(self):
        k = self.scale
        return f"<div id=board style='width:{self.width * k:g}px;height:{self.height * k:g}px'></div>"

    def style(self, sprite):
        x, y, code = ord(sprite[0]) - 701, ord(sprite[1]) - 701, ord(sprite[2])
        i = self.icons.get(code)
        if i is None:
            return "display:none"
        k = self.scale
        s = (
            f"left:{x * k:g}px;top:{y * k:g}px;width:{i.w * k:g}px;height:{i.h * k:g}px;"
            f"background-image:url(cid:{i.res});background-position:{-i.x * k:g}px {-i.y * k:g}px;"
            f"background-size:{i.bw * k:g}px {i.bh * k:g}px"
        )
        if i.alpha != 255:
            s += f";opacity:{i.alpha / 255:.3f}"
        return s

    def frame(self, drawing):
        """Deltas for one frame: new icons, then only the slots that changed."""
        for icon in self.pending:
            self.define(icon)
        self.pending.clear()
        cur = [drawing[i : i + 3] for i in range(0, len(drawing), 3)]
        styles = [self.style(s) for s in cur]
        styles += ["display:none"] * (len(self.slots) - len(styles))
        new = []
        changed = 0
        for n, st in enumerate(styles):
            if n >= len(self.slots):
                new.append(f"<div class=s id=s{n} style='{st}'></div>")
                self.slots.append(st)
            elif self.slots[n] != st:
                self.lam.attr("game", f"s{n}", "style", st)
                self.slots[n] = st
                changed += 1
        if new:
            self.lam.delta("game", "append", "board", "".join(new))
            changed += len(new)
        self.frames += 1
        self.changed += changed

    def restyle(self):
        """After a rescale: every slot again."""
        self.lam.delta("game", "replace", "board", self.board_html())
        self.slots = []


# --- Keys -------------------------------------------------------------------

# (player, action) per key, action being the game's key name.
KEYMAP = {
    "left": (0, "Left"), "right": (0, "Right"), "up": (0, "Jump"), "down": (0, "Fire"), " ": (0, "Fire"),
    "a": (1, "Left"), "d": (1, "Right"), "w": (1, "Jump"), "s": (1, "Fire"),
}
ARROWS = {"A": "up", "B": "down", "C": "right", "D": "left"}
KITTY_EVENT = re.compile(rb"\x1b\[(\d*)(?::[\d:]*)?(?:;(\d*)(?::(\d+))?)?(?:;[\d:]*)?([uABCD~])")
LEGACY = re.compile(rb"\x1b\[([ABCD])|\x1bO([ABCD])|([\x20-\x7e])|(\x1b)")


def kitty_events(data):
    """(key, event) pairs: event 1 press, 2 repeat, 3 release."""
    out = []
    for m in KITTY_EVENT.finditer(data):
        code, event, final = m.group(1), int(m.group(3) or 1), m.group(4).decode()
        if final in ARROWS:
            key = ARROWS[final]
        elif final == "u":
            n = int(code or 0)
            key = "escape" if n == 27 else chr(n).lower() if 32 <= n < 127 else None
        else:
            key = None
        if key:
            out.append((key, event))
    return out


def legacy_keys(data):
    out = []
    for m in LEGACY.finditer(data):
        if m.group(1) or m.group(2):
            out.append(ARROWS[(m.group(1) or m.group(2)).decode()])
        elif m.group(3):
            out.append(m.group(3).decode().lower())
        else:
            out.append("escape")
    return out


def main():
    args = sys.argv[1:]
    level = args[args.index("--level") + 1] if "--level" in args else "CompactLevels.py"
    # --log FILE: every key action the game receives, with its time (tests).
    log = open(args[args.index("--log") + 1], "a", buffering=1) if "--log" in args else None
    if not os.path.isdir(os.path.join(GAME_DIR, "bubbob")):
        print(f"bubbros.py: the game is not at {GAME_DIR}: run scripts/bubbros-fetch.sh")
        return 1

    # The game prints to stdout; the terminal belongs to us.
    out = sys.stdout.buffer
    sys.stdout = open(os.devnull, "w")
    lam = Hotty(out=out)
    real_write = lam.out.write

    os.chdir(GAME_DIR)
    sys.path.insert(0, GAME_DIR)
    saved, sys.argv = sys.argv, [sys.argv[0]]
    import bubbob.bb
    import gamesrv

    sys.argv = saved
    game = bubbob.bb.BubBobGame("levels/" + level)

    with Hotty.raw():
        caps = lam.query()
        if caps is None:
            lam.write("bubbros.py needs a HOTTY host (`hotty run`, a terminal that speaks HOTTY, or xterm-addon-hotty)\r\n")
            return 1
        # Is there a kitty keyboard protocol? Ask, with DA1 as the fence.
        lam.write("\x1b[?u\x1b[c")
        kitty = False
        deadline = time.monotonic() + 0.5
        while time.monotonic() < deadline and not re.search(rb"\x1b\[\?[\d;]*c", lam.buffer):
            lam.read(0.05)
        kitty = re.search(rb"\x1b\[\?\d+u", lam.buffer) is not None
        lam.buffer = b""

        screen = Screen(lam, gamesrv, game.width, game.height)
        gamesrv.clients.append(screen)
        for bitmap in list(gamesrv.bitmaps.values()):
            for icon in list(bitmap.icons.values()):
                screen.pending.append(icon)

        def counting(b):
            screen.bytes += len(b)
            return real_write(b)

        lam.out.write = counting

        def layout():
            cols, lines = os.get_terminal_size(out.fileno())
            cw = caps["cell"]["w"] / caps.get("scale", 1)
            ch = caps["cell"]["h"] / caps.get("scale", 1)
            screen.fit(cols, lines - 1, cw, ch)
            return cols, lines

        cols, lines = layout()
        lam.write("\x1b[?1049h\x1b[?25l\x1b[2J\x1b[1;1H")
        if kitty:
            # After entering the alternate screen: it keeps its own flag stack.
            lam.write("\x1b[>11u")  # disambiguate | report event types | all keys as escapes
        lam.doc("game", STYLE + screen.board_html())
        lam.place("game", cols, lines - 1, move_cursor=False)
        resized = []
        signal.signal(signal.SIGWINCH, lambda *_: resized.append(1))

        players = game.FnPlayers()
        joined = {}

        def join(n):
            if n in joined or n not in players or players[n] is None:
                return joined.get(n)
            p = players[n]
            p._client = screen
            p.playerjoin()
            p.setplayername("")
            game.updateplayers()
            joined[n] = p
            return p

        join(0)
        held = {}  # key → time of the last press or repeat (legacy mode)
        next_tick = time.monotonic()
        stats_at = time.monotonic()
        try:
            while True:
                now = time.monotonic()
                if lam.read(max(0.0, next_tick - now)):
                    msgs, data = lam.take()
                    for m in msgs:
                        if m["a"] == "ev" and m["e"] == "resize":
                            resized.append(1)
                    events = kitty_events(data) if kitty else [(k, 1) for k in legacy_keys(data)]
                    for key, event in events:
                        if key in ("q", "escape") and event == 1:
                            return 0
                        if key not in KEYMAP:
                            continue
                        n, action = KEYMAP[key]
                        p = join(n)
                        if p is None:
                            continue
                        if event == 3:
                            getattr(p, "km" + action)()
                            held.pop(key, None)
                            if log:
                                log.write(f"{time.monotonic():.3f} release {n} {action}\n")
                        elif event == 1 and key not in held:
                            getattr(p, "k" + action)()
                            held[key] = [time.monotonic(), 0]
                            if log:
                                log.write(f"{time.monotonic():.3f} press {n} {action}\n")
                        else:
                            if key in held:
                                held[key][0] = time.monotonic()
                                held[key][1] += 1
                    continue
                if now < next_tick:
                    continue
                next_tick += FRAME
                if now - next_tick > 0.25:  # fell far behind: do not catch up in a burst
                    next_tick = now + FRAME
                if not kitty:
                    # No release events: a key is up once its auto-repeat stops.
                    for key, (seen, repeats) in list(held.items()):
                        if now - seen > (0.12 if repeats else 0.6):
                            n, action = KEYMAP[key]
                            getattr(joined[n], "km" + action)()
                            del held[key]
                            if log:
                                log.write(f"{time.monotonic():.3f} release {n} {action} (repeat stopped)\n")
                if resized:
                    resized.clear()
                    cols, lines = layout()
                    lam.place("game", cols, lines - 1, move_cursor=False)
                    screen.restyle()
                if game.mainstep() > 0:
                    with lam.sync():
                        screen.frame("".join(gamesrv.sprites))
                if now - stats_at >= 1.0 and screen.frames:
                    span = now - stats_at
                    lam.write(
                        f"\x1b[{lines};1H\x1b[2m q quits · {len(screen.slots)} sprites · "
                        f"{screen.changed / screen.frames:.1f} changed/frame · "
                        f"{screen.bytes / screen.frames / 1024:.1f} KiB/frame · {screen.frames / span:.0f} fps · "
                        f"keys: {'kitty' if kitty else 'legacy'}\x1b[0m\x1b[K"
                    )
                    screen.frames = screen.changed = screen.bytes = 0
                    stats_at = now
        except (KeyboardInterrupt, EOFError):
            return 0
        finally:
            lam.out.write = real_write
            if kitty:
                lam.write("\x1b[<u")
            lam.delete("game")
            lam.write("\x1b[?25h\x1b[?1049l")


if __name__ == "__main__":
    sys.exit(main())
