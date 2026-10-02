"""The reference client: speak HOTTY (SPEC.md) from a Python program.

No dependencies. It has the two layers SDK.md describes:

- The wire layer does no I/O: `encode` and the command builders (`doc`,
  `place`, `set_text`, …) return escape sequences as strings, a `Decoder`
  turns the OSC sequences a program reads back into messages, a `Scanner`
  cuts them out of a byte stream, a `Detector` decides whether the terminal
  is a host, and `Reply`, `Event` and `Caps` read what the host said.
- `Hotty` does the I/O for the examples: it writes commands to stdout and
  reads replies and events from stdin, which must be in raw mode (use
  `Hotty.raw()`).
"""

import base64
import binascii
import contextlib
import dataclasses
import json
import os
import re
import select
import sys
import termios
import time
import tty
import zlib
from dataclasses import dataclass, field

# --- constants (SDK.md §3.1) ------------------------------------------------

NUMBER = "7279"
OSC_NUMBER = NUMBER  # the name this client had first
CHUNK = 4096
MAX_SIZE = 1000
MAX_NAME = 64
VERSION = "0.1"
COMPRESS_FROM = 256
SCAN_MAX = 64 << 10

EVENT_CLICK = "click"
EVENT_CHANGE = "change"
EVENT_INPUT = "input"
EVENT_SUBMIT = "submit"
EVENT_PRESS = "press"
EVENT_FOCUS = "focus"
EVENT_BLUR = "blur"
EVENT_RESIZE = "resize"
EVENT_FIT = "fit"
EVENT_HOVER = "hover"
EVENT_DRAG_START = "dragstart"
EVENT_DRAG = "drag"
EVENT_DRAG_END = "dragend"

EINVAL = "EINVAL"
ENOENT = "ENOENT"
ENOTARGET = "ENOTARGET"
EDETACHED = "EDETACHED"
EQUOTA = "EQUOTA"
EBUDGET = "EBUDGET"

OPS = ("morph", "inner", "replace", "append", "prepend", "before", "after", "remove", "attr", "unattr", "text", "var")

REPLY_ALWAYS = 0
REPLY_ON_ERROR = 1
NO_REPLY = 2

_PREFIX = b"\x1b]" + NUMBER.encode() + b";"
_ST = "\x1b\\"

# --- values and names (SDK.md §3.3, §3.5) ------------------------------------


def _value_char(c):
    return 0x20 <= ord(c) <= 0x7E and c not in ":;="


def clean_value(v):
    """A control value as it may be sent: each character a value may not hold
    (`:`, `;`, `=`, a control character, anything outside ASCII) becomes one
    `_` (SPEC §3.2). Bytes are read as UTF-8, each byte that is not UTF-8
    counting as one character."""
    if isinstance(v, bytes):
        v = v.decode("utf-8", "surrogateescape")
    elif not isinstance(v, str):
        v = str(v)
    return "".join(c if _value_char(c) else "_" for c in v)


_NAME = re.compile(r"[A-Za-z0-9_-]{1,64}\Z")


def valid_name(s):
    """Whether s is a valid surface name: 1 to 64 of A-Z, a-z, 0-9, '_', '-'."""
    return bool(_NAME.match(s))


def surface_name(s):
    """s made a valid surface name: each other character becomes `_`, it is
    cut to 64, and an empty name is `_`."""
    if valid_name(s):
        return s
    out = "".join(c if (c.isascii() and (c.isalnum() or c in "_-")) else "_" for c in s)[:MAX_NAME]
    return out or "_"


# --- encoding (SDK.md §3.3) --------------------------------------------------


def encode(control, payload=b"", compress=True):
    """One command as OSC sequences. `control` is a dict, or a list of
    (key, value) pairs, in the order they are sent. Values are cleaned
    (`clean_value`); a payload of 256 bytes or more is compressed when that
    makes it smaller; a base64 payload longer than 4096 is chunked at exactly
    4096."""
    if isinstance(payload, str):
        payload = payload.encode()
    pairs = list(control.items()) if isinstance(control, dict) else list(control)
    body, zipped = payload, False
    if compress and len(payload) >= COMPRESS_FROM:
        z = zlib.compress(payload, 1)
        if len(z) < len(payload):
            body, zipped = z, True
    b64 = base64.b64encode(body).decode()
    quiet = None
    parts = []
    for k, v in pairs:
        v = clean_value(v)
        parts.append(f"{k}={v}")
        if k == "q":
            quiet = v
    if zipped:
        parts.append("o=z")
    ctl = ":".join(parts)
    head = "\x1b]" + NUMBER + ";"
    if len(b64) <= CHUNK:
        return head + ctl + (";" + b64 if b64 else "") + _ST
    out = []
    for i in range(0, len(b64), CHUNK):
        piece = b64[i : i + CHUNK]
        if i == 0:
            out.append(f"{head}{ctl}:m=1;{piece}{_ST}")
            continue
        more = "0" if i + CHUNK >= len(b64) else "1"
        out.append(f"{head}m={more}" + (f":q={quiet}" if quiet is not None else "") + f";{piece}{_ST}")
    return "".join(out)


# --- commands (SDK.md §3.4) --------------------------------------------------


def _set(pairs, k, v):
    for i, (key, _) in enumerate(pairs):
        if key == k:
            pairs[i] = (k, str(v))
            return
    pairs.append((k, str(v)))


def _command(pairs, payload, default_q, n=None, q=None):
    """Reply options (SDK.md §3.4): `n` numbers the command and asks for its
    reply, `q` sets the quiet level, and a `q` given wins over the one `n`
    implies, whatever the order."""
    _set(pairs, "q", default_q)
    if n is not None:
        _set(pairs, "n", n)
        _set(pairs, "q", REPLY_ALWAYS)
    if q is not None:
        _set(pairs, "q", q)
    return encode(pairs, payload)


def query(n=1):
    """Asks whether the terminal is a host, fenced with DA1 (SPEC §4)."""
    return encode([("a", "q"), ("n", n)]) + "\x1b[c"


def doc(surface, html, detached=False, n=None, q=None):
    """Sends a surface's document (SPEC §5.1); `detached` creates it detached."""
    pairs = [("a", "doc"), ("s", surface)]
    if detached:
        pairs.append(("d", "1"))
    return _command(pairs, html, REPLY_ON_ERROR, n, q)


@dataclass
class Window:
    """The part of a surface a placement shows, in cells (SPEC §5.2)."""

    x: int = 0
    y: int = 0
    w: int = 0
    h: int = 0


@dataclass
class Placement:
    """Where and how a surface is shown (SPEC §5.2). rows 0 is auto."""

    cols: int
    rows: int = 0
    window: Window = None
    z: int = 0
    press: bool = False
    fit: bool = False
    hover: bool = False
    keep_cursor: bool = False

    def control(self, surface):
        pairs = [("a", "place"), ("s", surface), ("c", str(self.cols)), ("r", str(self.rows) if self.rows > 0 else "auto")]
        w = self.window
        if w is not None and (w.x, w.y, w.w, w.h) != (0, 0, 0, 0):
            if self.rows <= 0 or (w.x, w.y, w.w, w.h) != (0, 0, self.cols, self.rows):
                pairs += [("x", str(w.x)), ("y", str(w.y)), ("w", str(w.w)), ("h", str(w.h))]
        if self.z:
            pairs.append(("z", str(self.z)))
        if self.press:
            pairs.append(("p", "1"))
        if self.fit:
            pairs.append(("f", "1"))
        if self.hover:
            pairs.append(("v", "1"))
        if self.keep_cursor:
            pairs.append(("C", "1"))
        return pairs


def place(surface, placement, n=None, q=None):
    """Places a surface at the cursor (SPEC §5.2)."""
    return _command(placement.control(surface), b"", REPLY_ON_ERROR, n, q)


def place_at(surface, x, y, placement, n=None, q=None):
    """Places a surface with its top left at screen cell (x, y), from 0, and
    leaves the cursor where it was."""
    p = dataclasses.replace(placement, keep_cursor=True)
    return f"\x1b7\x1b[{y + 1};{x + 1}H" + place(surface, p, n, q) + "\x1b8"


def hide(surface, n=None, q=None):
    return _command([("a", "hide"), ("s", surface)], b"", NO_REPLY, n, q)


def delta(surface, op, target="", key="", payload=b"", n=None, q=None):
    """Changes a surface's document (SPEC §6.1)."""
    pairs = [("a", "delta"), ("s", surface), ("op", op)]
    if target:
        pairs.append(("t", target))
    if key:
        pairs.append(("k", key))
    return _command(pairs, payload, NO_REPLY, n, q)


def set_text(surface, target, text, n=None, q=None):
    return delta(surface, "text", target, "", text, n, q)


def set_var(surface, target, name, value, n=None, q=None):
    return delta(surface, "var", target, name, str(value), n, q)


def set_attr(surface, target, name, value, n=None, q=None):
    return delta(surface, "attr", target, name, str(value), n, q)


def remove_attr(surface, target, name, n=None, q=None):
    return delta(surface, "unattr", target, name, b"", n, q)


def morph_to(surface, target, html, n=None, q=None):
    return delta(surface, "morph", target, "", html, n, q)


def res(id, mime, data, n=None, q=None):
    """Sends a resource that documents refer to as cid:<id> (SPEC §7.1)."""
    return _command([("a", "res"), ("id", id), ("type", mime)], data, NO_REPLY, n, q)


def del_res(id, n=None, q=None):
    return _command([("a", "del"), ("id", id)], b"", NO_REPLY, n, q)


def delete(surface, n=None, q=None):
    """`del` (a keyword in Python): deletes a surface."""
    return _command([("a", "del"), ("s", surface)], b"", NO_REPLY, n, q)


def del_all(n=None, q=None):
    return _command([("a", "del")], b"", NO_REPLY, n, q)


def detach(surface, n=None, q=None):
    return _command([("a", "detach"), ("s", surface)], b"", NO_REPLY, n, q)


def focus(surface, target="", n=None, q=None):
    pairs = [("a", "focus"), ("s", surface)]
    if target:
        pairs.append(("t", target))
    return _command(pairs, b"", NO_REPLY, n, q)


def blur(surface, n=None, q=None):
    return _command([("a", "blur"), ("s", surface)], b"", NO_REPLY, n, q)


def sync(*cmds):
    """Commands the host applies as one batch (SPEC §6.3)."""
    return "\x1b[?2026h" + "".join(cmds) + "\x1b[?2026l"


# --- messages (SDK.md §3.6, §3.9) --------------------------------------------


class HottyError(Exception):
    """A command the host refused: its code (EINVAL, ENOENT, …) and detail."""

    def __init__(self, code, detail=None):
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code
        self.detail = detail


class Message:
    """One HOTTY message: a reply or an event from the host, or a command
    from a program. `control` has no `m` or `o`."""

    def __init__(self, control, payload):
        self.control = control
        self.payload = payload

    def __getitem__(self, k):
        return self.control.get(k)

    def get(self, k, default=None):
        return self.control.get(k, default)

    @property
    def json(self):
        if not self.payload:
            return None
        try:
            return json.loads(self.payload)
        except ValueError:
            return None

    def reply(self):
        """The message as a reply, or None if it is not one."""
        return Reply(self) if self.control.get("a") in ("ok", "err") else None

    def event(self):
        """The message as an event, or None if it is not one."""
        return Event(self) if self.control.get("a") == "ev" else None

    def __repr__(self):
        return f"Message({self.control}, {self.payload[:80]!r})"


def _int(s):
    if s is None or not re.fullmatch(r"-?[0-9]+", s):
        return None
    return int(s)


class Reply:
    """The host's answer to a command (SPEC §3.6)."""

    def __init__(self, m):
        self.message = m
        self.ok = m["a"] == "ok"
        self.re = m["re"]
        self.n = _int(m["n"])
        self.surface = m["s"]
        self.cols = _int(m["c"])
        self.rows = _int(m["r"])
        self.code = self.detail = None
        if not self.ok:
            body = m.json if isinstance(m.json, dict) else {}
            self.code = body.get("code") if isinstance(body.get("code"), str) else None
            self.detail = body.get("detail") if isinstance(body.get("detail"), str) else None

    def caps(self):
        """The capabilities a reply to a query carries, or None."""
        if not self.ok or self.re != "q":
            return None
        return Caps(self.message.json if isinstance(self.message.json, dict) else {})

    def err(self):
        """The reply as an error: None when ok."""
        return None if self.ok else HottyError(self.code or "", self.detail)


@dataclass
class Drag:
    c: int
    r: int
    keys: list = field(default_factory=list)


@dataclass
class Hover:
    c: int = None
    r: int = None
    out: bool = False


def _is_int(v):
    return isinstance(v, int) and not isinstance(v, bool)


def _is_num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


class Event:
    """What the user did in a surface (SPEC §9). The detail's accessors
    return None where the event does not carry it."""

    def __init__(self, m):
        self.message = m
        self.surface = m["s"]
        self.kind = m["e"]
        self.target = m["t"] or ""
        d = m.json
        self._d = d if isinstance(d, dict) else {}

    def value(self):
        v = self._d.get("value")
        return v if isinstance(v, str) else None

    def checked(self):
        v = self._d.get("checked")
        return v if isinstance(v, bool) else None

    def fields(self):
        """A submit's fields by name: a value that is not a string as its
        JSON, a null left out."""
        if self.kind != EVENT_SUBMIT:
            return None
        return {
            k: v if isinstance(v, str) else json.dumps(v, separators=(",", ":"))
            for k, v in self._d.items()
            if v is not None
        }

    def link(self):
        """(href, url) of a link's click; url is None when there is none."""
        href = self._d.get("href")
        if self.kind != EVENT_CLICK or not isinstance(href, str):
            return None
        url = self._d.get("url")
        return href, url if isinstance(url, str) else None

    def size(self):
        w, h = self._d.get("w"), self._d.get("h")
        if self.kind != EVENT_RESIZE or not (_is_num(w) and _is_num(h)):
            return None
        return w, h

    def fit_rows(self):
        r = self._d.get("r")
        return r if self.kind == EVENT_FIT and _is_int(r) else None

    def drag(self):
        if self.kind not in (EVENT_DRAG_START, EVENT_DRAG, EVENT_DRAG_END):
            return None
        c, r, keys = self._d.get("c"), self._d.get("r"), self._d.get("keys", [])
        if not (_is_int(c) and _is_int(r)):
            return None
        return Drag(c, r, [k for k in keys if isinstance(k, str)] if isinstance(keys, list) else [])

    def hover(self):
        if self.kind != EVENT_HOVER:
            return None
        if self._d.get("out") is True:
            return Hover(out=True)
        c, r = self._d.get("c"), self._d.get("r")
        if not (_is_int(c) and _is_int(r)):
            return None
        return Hover(c, r)


class Caps:
    """What a host says about itself (SPEC §4). A field of an unexpected type
    is ignored, as one the program does not know would be."""

    def __init__(self, d):
        self.raw = d

        def get(k, ok, default=None):
            v = d.get(k)
            return v if ok(v) else default

        self.v = get("v", lambda v: isinstance(v, str), "")
        self.ops = [o for o in get("ops", lambda v: isinstance(v, list), []) if isinstance(o, str)]
        self.events = [e for e in get("events", lambda v: isinstance(v, list), []) if isinstance(e, str)]
        cell = get("cell", lambda v: isinstance(v, dict), {})
        self.cell = (cell["w"], cell["h"]) if _is_num(cell.get("w")) and _is_num(cell.get("h")) else None
        self.scale = get("scale", _is_num)
        self.scheme = get("scheme", lambda v: isinstance(v, str), "")
        limits = get("limits", lambda v: isinstance(v, dict), {})
        self.limits = {k: v for k, v in limits.items() if _is_int(v)}
        net = get("net", lambda v: isinstance(v, dict), {})
        self.net = {k: [s for s in v if isinstance(s, str)] for k, v in net.items() if isinstance(v, list)}
        self.passthrough = get("passthrough", lambda v: isinstance(v, bool), False)
        self.host = get("host", lambda v: isinstance(v, str))
        self.version = get("version", lambda v: isinstance(v, str))

    def supports(self, op):
        """Whether the host supports a delta op; one that lists none, all."""
        return not self.ops or op in self.ops

    def sends(self, kind):
        """Whether the host sends an event kind; one that lists none, all."""
        if kind in (EVENT_DRAG_START, EVENT_DRAG_END):
            kind = EVENT_DRAG
        return not self.events or kind in self.events

    def drags(self):
        """Whether the host lists drag: a host that lists no kinds does not."""
        return EVENT_DRAG in self.events

    def hovers(self):
        """Whether the host lists hover: a host that lists no kinds does not."""
        return EVENT_HOVER in self.events

    def light(self):
        return self.scheme == "light"

    def cell_css(self):
        """A cell's size in CSS pixels: a usual 9x18 when the host did not
        say."""
        s = self.scale if self.scale and self.scale > 0 else 1
        if self.cell is None or self.cell[0] <= 0 or self.cell[1] <= 0:
            return 9, 18
        return self.cell[0] / s, self.cell[1] / s


# --- decoding (SDK.md §3.6) --------------------------------------------------

NOT_HOTTY = "not_hotty"
PARTIAL = "partial"
COMPLETE = "complete"
INVALID = "invalid"

_KEY = re.compile(r"[A-Za-z][A-Za-z0-9_-]*\Z")
_VALUE = re.compile(r"[\x20-\x39\x3c\x3e-\x7e]*\Z")
_B64 = re.compile(r"[A-Za-z0-9+/]*={0,2}\Z")


def _parse_control(s):
    if not s:
        return None
    out = {}
    for part in s.split(":"):
        k, eq, v = part.partition("=")
        if not eq or not _KEY.match(k) or not _VALUE.match(v) or k in out:
            return None
        out[k] = v
    return out


def _b64decode(s):
    s = re.sub(r"\s+", "", s)
    if not _B64.match(s) or len(s.rstrip("=")) % 4 == 1:
        return None
    try:
        return base64.b64decode(s + "=" * (-len(s) % 4))
    except binascii.Error:
        return None


class Decoder:
    """Turns OSC sequences into messages, joining chunked ones (SPEC §3.4).
    `invalid` counts the malformed messages dropped (SPEC §3.7)."""

    def __init__(self):
        self.invalid = 0
        self._pending = None  # (control, [base64 pieces])

    def feed(self, seq):
        """Takes one OSC sequence, ESC ] … with or without its terminator.
        Returns (result, message): message is set when result is COMPLETE."""
        if isinstance(seq, str):
            seq = seq.encode("utf-8", "surrogateescape")
        head = _PREFIX[:-1]  # ESC ] 7279
        if not seq.startswith(head) or seq[len(head) : len(head) + 1].isdigit():
            return NOT_HOTTY, None
        body = seq[len(head) :]
        if body.endswith(b"\x1b\\"):
            body = body[:-2]
        elif body.endswith(b"\x07"):
            body = body[:-1]
        if not body.startswith(b";"):
            return self._bad()
        try:
            text = body[1:].decode("ascii")
        except UnicodeDecodeError:
            return self._bad()
        ctl_s, _, b64 = text.partition(";")
        ctl = _parse_control(ctl_s)
        if ctl is None:
            return self._bad()
        if "m" in ctl and set(ctl) <= {"m", "q"}:
            if self._pending is None or ctl["m"] not in ("0", "1"):
                return self._bad()
            self._pending[1].append(b64)
            if ctl["m"] == "1":
                return PARTIAL, None
            ctl, pieces = self._pending
            self._pending = None
            return self._finish(ctl, "".join(pieces))
        if self._pending is not None:
            self._pending = None
            self.invalid += 1
        if ctl.get("m") == "1":
            self._pending = (ctl, [b64])
            return PARTIAL, None
        if "m" in ctl and ctl["m"] != "0":
            return self._bad()
        return self._finish(ctl, b64)

    def _bad(self):
        if self._pending is not None:
            self._pending = None
            self.invalid += 1
        self.invalid += 1
        return INVALID, None

    def _finish(self, ctl, b64):
        payload = _b64decode(b64)
        if payload is None:
            self.invalid += 1
            return INVALID, None
        if ctl.get("o") == "z":
            try:
                payload = zlib.decompress(payload)
            except zlib.error:
                self.invalid += 1
                return INVALID, None
        ctl = {k: v for k, v in ctl.items() if k not in ("m", "o")}
        return COMPLETE, Message(ctl, payload)


# --- scanning (SDK.md §3.7) --------------------------------------------------

_DA1_PREFIX = b"\x1b[?"


class Scanner:
    """Cuts HOTTY messages out of a byte stream, however its reads split it
    (SDK.md §3.7). `feed` returns segments in order: ("pass", bytes) for
    everything else, unchanged; ("osc", bytes) for one complete HOTTY
    sequence; and with da1=True, ("da1", bytes) for a Primary Device
    Attributes answer. It holds only what may still become one of those."""

    _GROUND, _OSC, _DISCARD = range(3)

    def __init__(self, da1=False):
        self.da1 = da1
        self.invalid = 0
        self._mode = self._GROUND
        self._held = b""  # a prefix of a sequence, or the HOTTY sequence in progress
        self._esc = False  # the last byte inside a HOTTY sequence was ESC

    @property
    def holding(self):
        """The bytes held for the next feed."""
        return self._held

    def feed(self, data):
        out = []
        for b in data:
            self._byte(bytes([b]), out)
        return _merge(out)

    def flush(self):
        """Ends the stream: a held prefix goes out as pass, and a HOTTY
        sequence in progress is dropped as malformed."""
        out = []
        if self._mode == self._OSC:
            self.invalid += 1
        elif self._held:
            out.append(("pass", self._held))
        self._mode, self._held, self._esc = self._GROUND, b"", False
        return _merge(out)

    def _byte(self, c, out):
        if self._mode == self._DISCARD:
            # Dropping a HOTTY sequence longer than SCAN_MAX, up to its end.
            if self._esc:
                self._esc = False
                self._mode = self._GROUND
                if c != b"\\":
                    self._held = b"\x1b"  # an ESC that is not ST begins a new sequence
                    self._ground(c, out)
            elif c == b"\x07":
                self._mode = self._GROUND
            elif c == b"\x1b":
                self._esc = True
            return
        if self._mode == self._OSC:
            if self._esc:
                self._esc = False
                if c == b"\\":
                    out.append(("osc", self._held + c))
                    self._mode, self._held = self._GROUND, b""
                    return
                # ESC without \ ends the sequence unfinished: it is dropped,
                # and the ESC begins whatever comes next.
                self.invalid += 1
                self._mode, self._held = self._GROUND, b"\x1b"
                self._ground(c, out)
                return
            if c == b"\x07":
                out.append(("osc", self._held + c))
                self._mode, self._held = self._GROUND, b""
                return
            if len(self._held) >= SCAN_MAX:
                self.invalid += 1
                self._mode, self._held = self._DISCARD, b""
                self._esc = c == b"\x1b"
                return
            self._esc = c == b"\x1b"
            self._held += c
            return
        self._ground(c, out)

    def _ground(self, c, out):
        if self._held:
            cand = self._held + c
            if _PREFIX.startswith(cand):
                self._held = cand
                if cand == _PREFIX:
                    self._mode = self._OSC
                return
            if self.da1 and self._da1_step(cand, out):
                return
            out.append(("pass", self._held))
            self._held = b""
        if c == b"\x1b":
            self._held = c
            return
        out.append(("pass", c))

    def _da1_step(self, cand, out):
        if _DA1_PREFIX.startswith(cand):
            self._held = cand
            return True
        if cand.startswith(_DA1_PREFIX):
            last = cand[-1:]
            if last == b"c":
                out.append(("da1", cand))
                self._held = b""
                return True
            if last.isdigit() or last == b";":
                self._held = cand
                return True
        return False


def _merge(segs):
    out = []
    for kind, b in segs:
        if out and kind == "pass" and out[-1][0] == "pass":
            out[-1] = ("pass", out[-1][1] + b)
        else:
            out.append((kind, b))
    return out


# --- detection (SDK.md §3.8) -------------------------------------------------

DETECTING = "detecting"
NATIVE = "native"
TEXT = "text"

DETECT_TIMEOUT = 1500  # ms: no answer at all
DETECT_AFTER_DA1 = 150  # ms: a DA1 before any reply may answer an earlier question
DETECT_AFTER_REPLY = 300  # ms: the DA1 behind the reply


class Detector:
    """Decides whether the terminal is a HOTTY host (SPEC §4), with time
    passed in as milliseconds. `decided` is set when the state is known,
    `done` when nothing more of the detection will arrive; `deadline` is
    when to call `tick` next (None once done)."""

    def __init__(self, n=1):
        self.n = n
        self.state = DETECTING
        self.caps = None
        self.decided = False
        self.done = False
        self._timeout = self._grace = self._after = None

    @property
    def deadline(self):
        if self.done or self._timeout is None:
            return None
        if self.state == DETECTING:
            return min(t for t in (self._timeout, self._grace) if t is not None)
        return self._after

    def start(self, now):
        """Returns the query to send (with its DA1 fence)."""
        self._timeout = now + DETECT_TIMEOUT
        return query(self.n)

    def _fire(self, now):
        if self.done or self._timeout is None:
            return
        if self.state == DETECTING:
            if now >= self._timeout or (self._grace is not None and now >= self._grace):
                self.state, self.decided, self.done = TEXT, True, True
        elif now >= self._after:
            self.done = True

    def tick(self, now):
        self._fire(now)

    def da1(self, now):
        """A DA1 answer arrived. Returns whether it was detection's."""
        self._fire(now)
        if self.done:
            return False
        if self.state == DETECTING:
            if self._grace is None:
                self._grace = now + DETECT_AFTER_DA1
            return True
        self.done = True
        return True

    def reply(self, r, now):
        """A reply arrived. Returns whether it answers the query."""
        self._fire(now)
        if not (r.ok and r.re == "q" and r.n == self.n):
            return False
        if self.state == DETECTING:
            self.state, self.decided = NATIVE, True
            self.caps = r.caps()
            self._after = min(now + DETECT_AFTER_REPLY, self._timeout)
        return True

    def end(self, now):
        """The input ended, or the caller gave up."""
        self._fire(now)
        if not self.decided:
            self.state, self.decided = TEXT, True
        self.done = True


# --- I/O for the examples ----------------------------------------------------


class Hotty:
    def __init__(self, out=None, inp=None):
        self.out = out or sys.stdout.buffer
        self.inp_fd = (inp or sys.stdin).fileno()
        self.buffer = b""
        self.caps = None
        self._decoder = Decoder()

    # --- sending ---------------------------------------------------------

    def send(self, payload=b"", **control):
        self.out.write(encode(control, payload).encode())
        self.out.flush()

    def write(self, text):
        self.out.write(text.encode() if isinstance(text, str) else text)
        self.out.flush()

    def doc(self, surface, html, quiet=REPLY_ON_ERROR, detached=False):
        self.write(doc(surface, html, detached=detached, q=quiet))

    def place(self, surface, cols, rows="auto", move_cursor=True, quiet=REPLY_ON_ERROR, window=None, z=0, press=False, fit=False, hover=False):
        """Places a surface at the cursor. `window` is (x, y, w, h): the part
        of the surface to show (SPEC §5.2), or None for all of it; `z` puts
        the placement above (greater) or below overlapping ones; `press`
        asks for a `press` event on every press in it (SPEC §9); `fit` asks
        for a `fit` event whenever the rows its document needs change;
        `hover` asks for a `hover` event whenever the element under the
        pointer changes, or the pointer leaves (SPEC §9.4)."""
        p = Placement(
            cols=int(cols),
            rows=0 if rows == "auto" else int(rows),
            window=Window(*window) if window is not None else None,
            z=z,
            press=press,
            fit=fit,
            hover=hover,
            keep_cursor=not move_cursor,
        )
        self.write(place(surface, p, q=quiet))

    def hide(self, surface, quiet=NO_REPLY):
        """Removes the placement and keeps the surface (SPEC §5.4)."""
        self.write(hide(surface, q=quiet))

    def delta(self, surface, op, target=None, payload="", key=None, quiet=NO_REPLY):
        self.write(delta(surface, op, target or "", key or "", payload, q=quiet))

    def text(self, surface, target, text):
        self.write(set_text(surface, target, text))

    def var(self, surface, target, name, value):
        self.write(set_var(surface, target, name, value))

    def attr(self, surface, target, name, value):
        self.write(set_attr(surface, target, name, value))

    def res(self, name, mime, data, quiet=NO_REPLY):
        self.write(res(name, mime, data, q=quiet))

    def delete(self, surface, quiet=NO_REPLY):
        self.write(delete(surface, q=quiet))

    def detach(self, surface, quiet=NO_REPLY):
        self.write(detach(surface, q=quiet))

    def focus(self, surface, target=None, quiet=NO_REPLY):
        self.write(focus(surface, target or "", q=quiet))

    def blur(self, surface, quiet=NO_REPLY):
        self.write(blur(surface, q=quiet))

    @contextlib.contextmanager
    def sync(self):
        """Synchronized output: the host shows the whole batch or none of it."""
        self.write("\x1b[?2026h")
        try:
            yield
        finally:
            self.write("\x1b[?2026l")

    # --- receiving -------------------------------------------------------

    @staticmethod
    @contextlib.contextmanager
    def raw(fd=None):
        fd = sys.stdin.fileno() if fd is None else fd
        old = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            yield
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)

    def read(self, timeout):
        """Reads what is available within `timeout` seconds into the buffer."""
        r, _, _ = select.select([self.inp_fd], [], [], timeout)
        if r:
            data = os.read(self.inp_fd, 65536)
            if not data:
                raise EOFError
            self.buffer += data
            return True
        return False

    def take(self):
        """Splits the buffer into (messages, other input bytes). A HOTTY
        message still arriving stays in the buffer; a lone ESC is the
        Escape key, and goes out at once."""
        sc = Scanner()
        segs = sc.feed(self.buffer)
        if sc.holding == b"\x1b":
            segs += sc.flush()
            self.buffer = b""
        else:
            self.buffer = sc.holding
        messages, other = [], b""
        for kind, b in segs:
            if kind == "pass":
                other += b
                continue
            result, m = self._decoder.feed(b)
            if result == COMPLETE:
                messages.append(m)
        return messages, other

    def query(self, timeout=None):
        """Is there a HOTTY host? Returns its capabilities (the JSON object),
        or None. Reads until detection is done (SDK.md §3.8), and leaves
        everything that is not detection's in the buffer, for take()."""
        now = lambda: time.monotonic() * 1000  # noqa: E731
        det = Detector(1)
        self.write(det.start(now()))
        if timeout is not None:
            det._timeout = now() + timeout * 1000
        sc = Scanner(da1=True)
        dec = Decoder()
        rest = b""
        pending = self.buffer
        self.buffer = b""
        while True:
            for kind, b in sc.feed(pending):
                if kind == "da1":
                    if not det.da1(now()):
                        rest += b
                elif kind == "osc":
                    result, m = dec.feed(b)
                    r = m.reply() if result == COMPLETE else None
                    if r is None or not det.reply(r, now()):
                        rest += b
                else:
                    rest += b
            pending = b""
            det.tick(now())
            if det.done:
                break
            try:
                if not self.read(max(0.0, (det.deadline - now()) / 1000)):
                    det.tick(now())
            except EOFError:
                det.end(now())
            pending, self.buffer = self.buffer, b""
            if det.done and not pending:
                break
        self.buffer = rest + sc.holding + pending + self.buffer
        if det.state != NATIVE:
            return None
        r = det.caps
        self.caps = r
        return r.raw if r is not None else {}
