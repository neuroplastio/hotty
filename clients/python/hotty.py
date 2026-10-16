"""The reference client: speak HOTTY (SPEC.md) from a Python program.

No dependencies. It has the two layers SDK.md describes:

- The wire layer does no I/O: `encode` and the command builders (`doc`,
  `place`, `set_text`, …) return escape sequences as strings, a `Decoder`
  turns the OSC sequences a program reads back into messages, `unpack`
  reads their msgpack bodies, a `Scanner`
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
import datetime
import os
import re
import select
import struct
import sys
import termios
import time
import tty
import zlib
from dataclasses import dataclass, field
from typing import NamedTuple

# --- constants (SDK.md §3.1) ------------------------------------------------

NUMBER = "7279"
OSC_NUMBER = NUMBER  # the name this client had first
CHUNK = 4096
MAX_SIZE = 1000
MAX_NAME = 64
VERSION = "0.3"
COMPRESS_FROM = 256
SCAN_MAX = 64 << 10

EVENT_CLICK = "click"
EVENT_CHANGE = "change"
EVENT_INPUT = "input"
EVENT_SUBMIT = "submit"
EVENT_PRESS = "press"
EVENT_FOCUS = "focus"
EVENT_BLUR = "blur"
EVENT_FIT = "fit"
EVENT_HOVER = "hover"
EVENT_VIEW = "view"
EVENT_DRAG_START = "dragstart"
EVENT_DRAG = "drag"
EVENT_DRAG_END = "dragend"
EVENT_COMMAND = "command"
EVENT_CAPS = "caps"

EINVAL = "EINVAL"
ENOENT = "ENOENT"
ENOTARGET = "ENOTARGET"
EDETACHED = "EDETACHED"
EQUOTA = "EQUOTA"
EBUDGET = "EBUDGET"
EVERSION = "EVERSION"

# The features a host may lack (SPEC §4).
FEATURE_PASSTHROUGH = "passthrough"
FEATURE_HOVER = "hover"
FEATURE_COUNT = "count"
FEATURE_MENU = "menu"

# The modifier bits of an event's `mods` (SPEC §9).
MOD_SHIFT = 1
MOD_ALT = 2
MOD_CONTROL = 4
MOD_META = 8

OPS = ("morph", "inner", "replace", "append", "prepend", "before", "after", "remove", "attr", "unattr", "text", "var", "reveal")

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
    4096. The keys `o` and `m` are Encode's: a control given with them goes
    out without them."""
    if isinstance(payload, str):
        payload = payload.encode()
    pairs = list(control.items()) if isinstance(control, dict) else list(control)
    body, zipped = payload, False
    if compress and len(payload) >= COMPRESS_FROM:
        z = zlib.compress(payload, 6)
        if len(z) < len(payload):
            body, zipped = z, True
    b64 = base64.b64encode(body).decode()
    parts = []
    for k, v in pairs:
        if k in ("o", "m"):
            continue  # Encode's to set
        v = clean_value(v)
        parts.append(f"{k}={v}")
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
        out.append(f"{head}m={more};{piece}{_ST}")
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
    implies, whatever the order. `q` goes out only where the wire does not
    imply it (SPEC §3.5, SDK.md §3.4.2): it is left out where it would be
    0 with `n`, or 1 without."""
    if n is not None:
        _set(pairs, "n", n)
    level = q if q is not None else (REPLY_ALWAYS if n is not None else default_q)
    if level != (REPLY_ALWAYS if n is not None else REPLY_ON_ERROR):
        _set(pairs, "q", level)
    return encode(pairs, payload)


def query(n=1, late=False):
    """Asks whether the terminal is a host that speaks VERSION, fenced
    with DA1 (SPEC §4); with late, a late answer is welcome."""
    pairs = [("a", "q"), ("n", n), ("v", VERSION)]
    if late:
        pairs.append(("late", 1))
    return encode(pairs) + "\x1b[c"


def withdraw_late():
    """Withdraws a query that asked for a late answer (SPEC §4): a query
    that wants no answer, which takes its place."""
    return encode([("a", "q"), ("q", NO_REPLY)])


def edit(names, n=None, q=None):
    """Takes the edit commands named, comma-separated (SPEC §10.6); none
    takes nothing."""
    return _command([("a", "edit"), ("take", ",".join(names))], b"", NO_REPLY, n, q)


@dataclass
class MenuItem:
    """One of a program's actions in its menu (SPEC §10.7): the key that
    reaches it after its group's, what it does, the command a pick sends,
    whether it does anything now, and the items after it."""

    key: str = ""
    label: str = ""
    name: str = ""
    enabled: bool = True
    items: list = field(default_factory=list)


@dataclass
class MenuTree:
    """A program's menu (SPEC §10.7): what it is for, and its items."""

    label: str = ""
    items: list = field(default_factory=list)


def _menu_item(it):
    i = {}
    if it.key:
        i["key"] = it.key
    if it.label:
        i["label"] = it.label
    if it.name:
        i["name"] = it.name
    i["enabled"] = bool(it.enabled)
    if it.items:
        i["items"] = [_menu_item(c) for c in it.items]
    return i


def menu(tree=None, n=None, q=None):
    """Sends a program's menu, what it can do now, or with none leaves it
    none (SPEC §10.7). The map's order is SDK.md §3.4's."""
    if tree is None:
        return _command([("a", "menu")], b"", NO_REPLY, n, q)
    m = {}
    if tree.label:
        m["label"] = tree.label
    m["items"] = [_menu_item(i) for i in tree.items]
    return _command([("a", "menu")], pack(m), NO_REPLY, n, q)


def menu_show(seq=(), n=None, q=None):
    """Shows the level of the menu the keys typed reach; with none, its top
    level (SPEC §10.7)."""
    body = pack({"seq": list(seq)}) if seq else b""
    return _command([("a", "menu"), ("show", "1")], body, NO_REPLY, n, q)


def menu_hide(n=None, q=None):
    """Hides the level of the menu shown (SPEC §10.7)."""
    return _command([("a", "menu"), ("show", "0")], b"", NO_REPLY, n, q)


SCROLL_VERTICAL = 1
SCROLL_HORIZONTAL = 2


def doc(surface, html, detached=False, scroll=0, n=None, q=None):
    """Sends a surface's document (SPEC §5.1); `detached` creates it detached,
    and `scroll` lets it scroll along the axes it names, a bitmask of
    SCROLL_VERTICAL and SCROLL_HORIZONTAL (0: it does not scroll)."""
    pairs = [("a", "doc"), ("s", surface)]
    if detached:
        pairs.append(("d", "1"))
    if scroll:
        pairs.append(("scroll", str(scroll)))
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
    """Where and how a surface is shown (SPEC §5.2). rows 0 is auto. `press`,
    `fit` and `hover` belong to the surface and hold until sent again:
    None leaves the key out, True sends 1 and False sends 0 (SDK.md §3.4.1)."""

    cols: int
    rows: int = 0
    window: Window = None
    z: int = 0
    press: bool = None
    fit: bool = None
    hover: bool = None
    keep_cursor: bool = False

    def control(self, surface):
        pairs = [("a", "place"), ("s", surface), ("c", str(self.cols)), ("r", str(self.rows) if self.rows > 0 else "auto")]
        w = self.window
        if w is not None and (w.x, w.y, w.w, w.h) != (0, 0, 0, 0):
            if self.rows <= 0 or (w.x, w.y, w.w, w.h) != (0, 0, self.cols, self.rows):
                pairs += [("x", str(w.x)), ("y", str(w.y)), ("w", str(w.w)), ("h", str(w.h))]
        if self.z:
            pairs.append(("z", str(self.z)))
        for key, flag in (("p", self.press), ("f", self.fit), ("v", self.hover)):
            if flag is not None:
                pairs.append((key, "1" if flag else "0"))
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


@dataclass
class Op:
    """One op of a delta (SPEC §6.1, SDK.md §3.4.3): the op, its target (empty:
    none), its key for `attr`, `unattr` and `var`, and its value."""

    op: str
    target: str = ""
    key: str = ""
    value: str = ""


# The ops that always carry a value `v`, even an empty one (SPEC §6.1);
# `reveal` carries it only as "start" or "end".
_VALUED = frozenset(("morph", "inner", "replace", "append", "prepend", "before", "after", "attr", "text", "var"))
_KEYED = frozenset(("attr", "unattr", "var"))


def _op_map(o):
    m = {"op": o.op}
    if o.target:
        m["t"] = o.target
    if o.op in _KEYED:
        m["k"] = o.key
    if o.op in _VALUED or (o.op == "reveal" and o.value in ("start", "end")):
        m["v"] = str(o.value)
    return m


def morph(target, html):
    """Morphs the target (empty: the whole tree) to html (SPEC §6.2)."""
    return Op("morph", target, "", html)


def inner(target, html):
    return Op("inner", target, "", html)


def replace(target, html):
    return Op("replace", target, "", html)


def append(target, html):
    return Op("append", target, "", html)


def prepend(target, html):
    return Op("prepend", target, "", html)


def before(target, html):
    return Op("before", target, "", html)


def after(target, html):
    return Op("after", target, "", html)


def remove(target):
    return Op("remove", target)


def attr(target, name, value):
    return Op("attr", target, name, str(value))


def unattr(target, name):
    return Op("unattr", target, name)


def text(target, text):
    return Op("text", target, "", text)


def var(target, name, value):
    return Op("var", target, name, str(value))


def reveal_op(target, where=""):
    """Scrolls the target into view: where is "start" or "end", or empty for
    as little as brings it into view."""
    return Op("reveal", target, "", where)


def delta(surface, *ops, n=None, q=None):
    """Changes a surface's document with the ops given, applied in order and
    shown as one (SPEC §6.1). The body is one msgpack map, `{"ops": [...]}`;
    targets and values travel in it as they are, uncleaned (SDK.md §3.4.3)."""
    body = pack({"ops": [_op_map(o) for o in ops]})
    return _command([("a", "delta"), ("s", surface)], body, NO_REPLY, n, q)


def set_text(surface, target, text, n=None, q=None):
    return delta(surface, Op("text", target, "", text), n=n, q=q)


def set_var(surface, target, name, value, n=None, q=None):
    return delta(surface, var(target, name, value), n=n, q=q)


def set_attr(surface, target, name, value, n=None, q=None):
    return delta(surface, attr(target, name, value), n=n, q=q)


def remove_attr(surface, target, name, n=None, q=None):
    return delta(surface, unattr(target, name), n=n, q=q)


def morph_to(surface, target, html, n=None, q=None):
    return delta(surface, morph(target, html), n=n, q=q)


def reveal(surface, target, where="", n=None, q=None):
    """Scrolls the target into view (SPEC §6.1): where is "start" or "end",
    or empty for as little as brings it into view."""
    return delta(surface, reveal_op(target, where), n=n, q=q)


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
    def body(self):
        """The body, a msgpack map (SPEC §3.3), or None when there is none,
        or it is not one map that decodes."""
        if not self.payload:
            return None
        try:
            v = unpack(self.payload)
        except ValueError:
            return None
        return v if isinstance(v, dict) else None

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
        self.op = _int(m["i"])  # the op of a delta at fault, from 0 (SPEC §3.6, §6.1)
        self.code = self.detail = None
        if not self.ok:
            body = _typed_body(m, _ERROR) or {}
            self.code = body.get("code")
            self.detail = body.get("detail")

    def caps(self):
        """The capabilities a reply to a query carries, or None when it
        carries none, or they do not decode."""
        if not self.ok or self.re != "q":
            return None
        body = _typed_body(self.message, _CAPS)
        return Caps(body) if body is not None else None

    def err(self):
        """The reply as an error: None when ok."""
        return None if self.ok else HottyError(self.code or "", self.detail)


@dataclass
class Drag:
    """A drag's cell, its steps x and y in the element dragged, and tx and
    ty in t, each None where the detail has none (SPEC §9.1)."""

    c: int
    r: int
    x: int = None
    y: int = None
    tx: int = None
    ty: int = None


@dataclass
class Hover:
    c: int = None
    r: int = None
    out: bool = False


@dataclass
class Area:
    """The cells an element covers, counted from the surface's top left
    cell (SPEC §9)."""

    c: int
    r: int
    w: int
    h: int


@dataclass
class Command:
    """An edit command (SPEC §10.6), or a pick from the program's menu
    (§10.7): its name, its key, empty from a menu,
    and a paste's text, has_text telling an empty one from none."""

    name: str
    key: str = ""
    text: str = ""
    has_text: bool = False


@dataclass
class View:
    """The elements in view by id, with their cells, and whether the
    document shows its end (SPEC §9.5)."""

    areas: dict = field(default_factory=dict)
    at_end: bool = False


# The types of a body's fields (SPEC §3.3): a type's name, a list of one
# type (an array of it), or a dict: a map's fields by name, or under "*" the
# type of each value of a map keyed by strings; a tuple is an array of exactly
# those types, in order. A field not named is not
# checked, as one a program does not know is ignored (SDK.md §2.7).
_IS = {
    "int": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "float": lambda v: isinstance(v, float),
    "str": lambda v: isinstance(v, str),
    "bool": lambda v: isinstance(v, bool),
}


def _typed(v, t):
    if isinstance(t, str):
        return _IS[t](v)
    if isinstance(t, tuple):  # an array of exactly these types, in order
        return isinstance(v, list) and len(v) == len(t) and all(_typed(x, f) for x, f in zip(v, t))
    if isinstance(t, list):
        return isinstance(v, list) and all(_typed(x, t[0]) for x in v)
    if not isinstance(v, dict):
        return False
    if "*" in t:
        return all(isinstance(k, str) and _typed(x, t["*"]) for k, x in v.items())
    return all(_typed(v[k], f) for k, f in t.items() if k in v)


def _typed_body(m, t):
    """m's body when each field it has that t names is of its type; None
    when it does not decode (SDK.md §3.9)."""
    b = m.body
    return b if b is not None and _typed(b, t) else None


_ERROR = {"code": "str", "detail": "str"}
_CAPS = {
    "v": "str",
    "cellcss": {"w": "float", "h": "float"},
    "scale": "float",
    "scheme": "str",
    "mod": "str",
    "features": ["str"],
    "limits": {"*": "int"},
    "net": {"*": ["str"]},
    "edit": {"*": ["str"]},
    "host": "str",
    "version": "str",
}
_AREA = {"c": "int", "r": "int", "w": "int", "h": "int"}
_DRAG = {"c": "int", "r": "int", "mods": "int", "x": "int", "y": "int", "tx": "int", "ty": "int"}
# Each kind's detail (SPEC §9); a kind not here carries none a program reads.
_DETAIL = {
    EVENT_CLICK: {"value": "str", "href": "str", "url": "str", "area": _AREA, "mods": "int", "count": "int"},
    EVENT_PRESS: {"area": _AREA, "mods": "int"},
    EVENT_CHANGE: {"checked": "bool", "value": "str"},
    EVENT_INPUT: {"value": "str"},
    EVENT_SUBMIT: {"fields": [("str", "str")]},
    EVENT_FIT: {"r": "int"},
    EVENT_DRAG_START: _DRAG,
    EVENT_DRAG: _DRAG,
    EVENT_DRAG_END: _DRAG,
    EVENT_HOVER: {"c": "int", "r": "int", "out": "bool"},
    EVENT_VIEW: {"in": {"*": _AREA}, "end": "bool"},
    EVENT_COMMAND: {"name": "str", "key": "str", "text": "str"},
    EVENT_CAPS: _CAPS,
}


class Event:
    """What the user did in a surface (SPEC §9). The detail is read by the
    event's kind (SDK.md §3.9), and its accessors return None where the
    event does not carry it, or its detail does not decode."""

    def __init__(self, m):
        self.message = m
        self.surface = m["s"]  # None for command and caps (SPEC §9)
        self.kind = m["e"]
        self.target = m["t"] or ""
        t = _DETAIL.get(self.kind)
        self._body = _typed_body(m, t) if t else None
        self._d = self._body or {}

    def value(self):
        if self.kind not in (EVENT_CLICK, EVENT_CHANGE, EVENT_INPUT):
            return None
        return self._d.get("value")

    def checked(self):
        return self._d.get("checked") if self.kind == EVENT_CHANGE else None

    def fields(self):
        """A submit's fields, a list of (name, value) in order: two fields of
        one name are two pairs (SPEC §9). None when the detail has none."""
        if self.kind != EVENT_SUBMIT or "fields" not in self._d:
            return None
        return [tuple(p) for p in self._d["fields"]]

    def mods(self):
        """The modifier keys held, as bits (MOD_SHIFT, …); 0 when none was
        (SPEC §9)."""
        if self.kind not in (EVENT_CLICK, EVENT_PRESS, EVENT_DRAG_START, EVENT_DRAG, EVENT_DRAG_END):
            return 0
        return self._d.get("mods", 0)

    def link(self):
        """(href, url) of a link's click; url is None when there is none."""
        href = self._d.get("href")
        if self.kind != EVENT_CLICK or href is None:
            return None
        return href, self._d.get("url")

    def fit_rows(self):
        return self._d.get("r") if self.kind == EVENT_FIT else None

    def drag(self):
        if self.kind not in (EVENT_DRAG_START, EVENT_DRAG, EVENT_DRAG_END):
            return None
        c, r = self._d.get("c"), self._d.get("r")
        if c is None or r is None:
            return None
        d = self._d
        return Drag(c, r, d.get("x"), d.get("y"), d.get("tx"), d.get("ty"))

    def count(self):
        """A click's place in its run of clicks (SPEC §9): 2 for the second
        click of a double click; 1 for a click whose detail has none."""
        if self.kind != EVENT_CLICK:
            return None
        return self._d.get("count") or 1

    def area(self):
        """The cells of a click's or a press's element (SPEC §9)."""
        a = self._d.get("area") if self.kind in (EVENT_CLICK, EVENT_PRESS) else None
        if a is None or any(k not in a for k in "crwh"):
            return None
        return Area(a["c"], a["r"], a["w"], a["h"])

    def hover(self):
        if self.kind != EVENT_HOVER:
            return None
        if self._d.get("out") is True:
            return Hover(out=True)
        c, r = self._d.get("c"), self._d.get("r")
        if c is None or r is None:
            return None
        return Hover(c, r)

    def command(self):
        """An edit command (SPEC §10.6), or None."""
        if self.kind != EVENT_COMMAND or "name" not in self._d:
            return None
        d = self._d
        return Command(d["name"], d.get("key", ""), d.get("text", ""), "text" in d)

    def changed(self):
        """The capabilities a caps event says changed (SPEC §4), a Caps with
        only those fields in raw; None when its detail does not decode."""
        if self.kind != EVENT_CAPS or self._body is None:
            return None
        return Caps(self._body)

    def view(self):
        """What a view reports: an element whose area lacks a field is left
        out."""
        if self.kind != EVENT_VIEW or self._body is None:
            return None
        areas = {}
        for id, a in self._d.get("in", {}).items():
            if all(k in a for k in "crwh"):
                areas[id] = Area(a["c"], a["r"], a["w"], a["h"])
        return View(areas, self._d.get("end", False))


class CellCSS(NamedTuple):
    """One cell's size in CSS pixels (SPEC §4, §5.3)."""

    w: float
    h: float


class Caps:
    """What a host says about itself (SPEC §4), from a body whose fields
    have their types (Reply.caps). A field the host did not send is None,
    or empty."""

    def __init__(self, d):
        self.raw = d
        self.v = d.get("v", "")
        cell = d.get("cellcss", {})
        self.cell_css = CellCSS(cell["w"], cell["h"]) if "w" in cell and "h" in cell else None
        self.scale = d.get("scale")
        self.scheme = d.get("scheme", "")
        self.mod = d.get("mod")
        self.features = d.get("features", [])
        self.limits = d.get("limits", {})
        self.net = d.get("net", {})
        self.edit = d.get("edit")
        self.host = d.get("host")
        self.version = d.get("version")

    def has(self, feature):
        """Whether the host has a feature (SPEC §4): passthrough, hover,
        count or menu."""
        return feature in self.features

    def light(self):
        return self.scheme == "light"

    def merge(self, changed):
        """The capabilities with the fields a caps event changed (SPEC §4),
        and without those it empties (`{}`, `[]` or `""`): absent now
        (SPEC §9)."""
        raw = {**self.raw, **changed.raw}
        return Caps({k: v for k, v in raw.items()
                     if not (k in changed.raw and isinstance(v, (dict, list, str)) and not v)})


# --- msgpack (SPEC §3.3, SDK.md §3.9) ----------------------------------------

# How deep a body may nest: its map is the first level.
MAX_DEPTH = 32
MAX_INT = 2**53 - 1

_EPOCH = datetime.datetime(1970, 1, 1, tzinfo=datetime.timezone.utc)


class Timestamp(NamedTuple):
    """A time, as msgpack's timestamp has it (extension -1, SPEC.md §3.3):
    seconds since 1970-01-01T00:00:00Z, and nanoseconds into the second."""

    sec: int
    nsec: int = 0

    def to_datetime(self):
        """As an aware UTC datetime, which keeps microseconds. OverflowError
        outside datetime's years, 1 to 9999."""
        return _EPOCH + datetime.timedelta(seconds=self.sec, microseconds=self.nsec // 1000)


_FIXED = {0xCA: ">f", 0xCB: ">d", 0xCC: ">B", 0xCD: ">H", 0xCE: ">I", 0xCF: ">Q",
          0xD0: ">b", 0xD1: ">h", 0xD2: ">i", 0xD3: ">q"}
_SIZED = {0xC4: ("bin", ">B"), 0xC5: ("bin", ">H"), 0xC6: ("bin", ">I"),
          0xC7: ("ext", ">B"), 0xC8: ("ext", ">H"), 0xC9: ("ext", ">I"),
          0xD9: ("str", ">B"), 0xDA: ("str", ">H"), 0xDB: ("str", ">I"),
          0xDC: ("array", ">H"), 0xDD: ("array", ">I"), 0xDE: ("map", ">H"), 0xDF: ("map", ">I")}
_FIXEXT = {0xD4: 1, 0xD5: 2, 0xD6: 4, 0xD7: 8, 0xD8: 16}


def _len_head(n, fix, fixmax, h8, h16, h32):
    if n <= fixmax:
        return bytes([fix | n])
    if h8 is not None and n < 1 << 8:
        return bytes([h8, n])
    if n < 1 << 16:
        return bytes([h16]) + n.to_bytes(2, "big")
    return bytes([h32]) + n.to_bytes(4, "big")


def pack(v):
    """v as msgpack, each value in the smallest of its type's forms: a dict
    a map in its order, a list an array, str a str, a bool, an int, a float
    64 bits."""
    if isinstance(v, bool):
        return b"\xc3" if v else b"\xc2"
    if isinstance(v, float):
        return b"\xcb" + struct.pack(">d", v)
    if isinstance(v, int):
        if 0 <= v < 128:
            return bytes([v])
        if -32 <= v < 0:
            return (v & 0xFF).to_bytes(1, "big")
        for lo, hi, h, n in ((0, 1 << 8, 0xCC, 1), (0, 1 << 16, 0xCD, 2), (0, 1 << 32, 0xCE, 4),
                             (-(1 << 7), 1 << 7, 0xD0, 1), (-(1 << 15), 1 << 15, 0xD1, 2),
                             (-(1 << 31), 1 << 31, 0xD2, 4), (-(1 << 63), 1 << 64, 0xD3, 8)):
            if lo <= v < hi:
                return bytes([h]) + v.to_bytes(n, "big", signed=v < 0 or h >= 0xD0)
    if isinstance(v, str):
        b = v.encode()
        return _len_head(len(b), 0xA0, 31, 0xD9, 0xDA, 0xDB) + b
    if isinstance(v, list):
        return _len_head(len(v), 0x90, 15, None, 0xDC, 0xDD) + b"".join(pack(x) for x in v)
    if isinstance(v, dict):
        return _len_head(len(v), 0x80, 15, None, 0xDE, 0xDF) + b"".join(pack(k) + pack(x) for k, x in v.items())
    raise TypeError(f"msgpack: cannot pack {type(v).__name__}")


def unpack(data):
    """The one msgpack value in data, as plain values: a map is a dict, an
    array a list, str a str, bin bytes, a timestamp (extension -1) a
    Timestamp, and any other extension None. ValueError when data is not
    one value, or nests more than MAX_DEPTH deep, or holds what no host
    sends (SPEC.md §3.3): a nil, a key that is not a str or is given twice
    in one map, a str that is not UTF-8, an int further than MAX_INT from zero, or a timestamp msgpack
    does not define."""
    data = memoryview(data)
    v, i = _unpack(data, 0, 0)
    if i != len(data):
        raise ValueError("msgpack: bytes after the value")
    return v


def _take(m, i, n):
    if i + n > len(m):
        raise ValueError("msgpack: cut short")
    return m[i : i + n], i + n


def _unpack(m, i, depth):
    b, i = _take(m, i, 1)
    c = b[0]
    if c <= 0x7F:
        return c, i
    if c >= 0xE0:
        return c - 0x100, i
    if c == 0xC0:
        raise ValueError("msgpack: a nil")
    if c in (0xC2, 0xC3):
        return c == 0xC3, i
    if c in _FIXED:
        f = struct.Struct(_FIXED[c])
        b, i = _take(m, i, f.size)
        v = f.unpack(b)[0]
        if isinstance(v, int) and abs(v) > MAX_INT:
            raise ValueError("msgpack: an int further than 2^53 - 1 from zero")
        return v, i
    if c <= 0x8F:
        kind, n = "map", c & 0x0F
    elif c <= 0x9F:
        kind, n = "array", c & 0x0F
    elif c <= 0xBF:
        kind, n = "str", c & 0x1F
    elif c in _SIZED:
        kind, f = _SIZED[c]
        f = struct.Struct(f)
        b, i = _take(m, i, f.size)
        n = f.unpack(b)[0]
    elif c in _FIXEXT:
        kind, n = "ext", _FIXEXT[c]
    else:
        raise ValueError(f"msgpack: no type starts with 0x{c:02x}")
    if kind == "ext":
        b, i = _take(m, i, 1)
        code = b[0] - 0x100 if b[0] > 0x7F else b[0]
        b, i = _take(m, i, n)
        return (_timestamp(bytes(b)) if code == -1 else None), i
    if kind in ("str", "bin"):
        b, i = _take(m, i, n)
        return (str(b, "utf-8") if kind == "str" else bytes(b)), i
    if depth == MAX_DEPTH:
        raise ValueError("msgpack: nested too deep")
    if n > len(m) - i:  # each takes a byte at least
        raise ValueError("msgpack: cut short")
    if kind == "array":
        out = []
        for _ in range(n):
            v, i = _unpack(m, i, depth + 1)
            out.append(v)
        return out, i
    out = {}
    for _ in range(n):
        if i < len(m) and not (0xA0 <= m[i] <= 0xBF or 0xD9 <= m[i] <= 0xDB):
            raise ValueError("msgpack: a map key that is not a str")
        k, i = _unpack(m, i, depth + 1)
        if k in out:
            raise ValueError("msgpack: a key given twice")
        out[k], i = _unpack(m, i, depth + 1)
    return out, i


def _timestamp(b):
    if len(b) == 4:
        s, ns = struct.unpack(">I", b)[0], 0
    elif len(b) == 8:
        x = struct.unpack(">Q", b)[0]
        s, ns = x & 0x3_FFFF_FFFF, x >> 34
    elif len(b) == 12:
        ns, s = struct.unpack(">Iq", b)
        if abs(s) > MAX_INT:
            raise ValueError("msgpack: a timestamp further than 2^53 - 1 seconds from 1970")
    else:
        raise ValueError("msgpack: a timestamp of %d bytes" % len(b))
    if ns > 999_999_999:
        raise ValueError("msgpack: a timestamp's nanoseconds over a second")
    return Timestamp(s, ns)


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


DEFAULT_MAX = 16 << 20


def _encoded_max(n):
    """The most base64 a message of n decoded bytes takes, zlib's overhead
    included."""
    return -(-(n + n // 256 + 64) // 3) * 4


class Decoder:
    """Turns OSC sequences into messages, joining chunked ones (SPEC §3.4).
    `invalid` counts the malformed messages dropped (SPEC §3.7). `max` is the
    most bytes one message decodes to, 0 for DEFAULT_MAX: past it a message
    is malformed, and its further chunks are dropped (SDK.md §3.6)."""

    def __init__(self, max=0):
        self.invalid = 0
        self.max = max
        self._pending = None  # [control, [base64 pieces], size, over]

    def _max(self):
        return self.max if self.max > 0 else DEFAULT_MAX

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
        if set(ctl) == {"m"}:
            if self._pending is None or ctl["m"] not in ("0", "1"):
                return self._bad()
            p = self._add(b64)
            if ctl["m"] == "1":
                return PARTIAL, None
            self._pending = None
            if p[3]:
                return INVALID, None
            return self._finish(p[0], "".join(p[1]))
        self._abort()
        if ctl.get("m") == "1":
            self._pending = [ctl, [], 0, False]
            self._add(b64)
            return PARTIAL, None
        if "m" in ctl and ctl["m"] != "0":
            return self._bad()
        return self._finish(ctl, b64)

    def _add(self, b64):
        """Adds a chunk's base64 to the message in progress: past max, the
        message is over, counted once, and holds nothing more."""
        p = self._pending
        if not p[3]:
            p[2] += len(b64)
            if p[2] > _encoded_max(self._max()):
                p[1], p[3] = [], True
                self.invalid += 1
            else:
                p[1].append(b64)
        return p

    def _abort(self):
        """Drops the message in progress, counted unless it was over."""
        if self._pending is not None:
            if not self._pending[3]:
                self.invalid += 1
            self._pending = None

    def _bad(self):
        self._abort()
        self.invalid += 1
        return INVALID, None

    def _finish(self, ctl, b64):
        n = self._max()
        payload = _b64decode(b64) if len(b64) <= _encoded_max(n) else None
        if payload is None or len(payload) > n and ctl.get("o") != "z":
            self.invalid += 1
            return INVALID, None
        if ctl.get("o") == "z":
            try:
                z = zlib.decompressobj()
                payload = z.decompress(payload, n + 1)
                if len(payload) > n or not z.eof:
                    raise zlib.error("past max, or cut short")
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

    @property
    def in_sequence(self):
        """Whether a HOTTY sequence is in progress, or one too long is being
        dropped: the next feed goes on with it, and flush would drop it.
        Otherwise what is held is the start of a segment, which a program
        reading keys may flush after a moment, as typing (SDK.md §3.7)."""
        return self._mode != self._GROUND

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
    when to call `tick` next (None once done). A reply to the query makes
    the terminal a host when its capabilities decode and name VERSION, and
    any other reply to it, an error included, leaves it TEXT. With `late`,
    the query asks for a late answer, and the first reply after the state
    is TEXT that makes the terminal a host does."""

    def __init__(self, n=1, late=False):
        self.n = n
        self.late = late
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
        return query(self.n, self.late)

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
        if not (r.re == "q" and r.n == self.n):
            return False
        caps = r.caps()
        host = caps is not None and caps.v == VERSION
        if self.state == DETECTING:
            self.state, self.decided = (NATIVE, True) if host else (TEXT, True)
            self.caps = caps if host else None
            self._after = min(now + DETECT_AFTER_REPLY, self._timeout)
        elif self.state == TEXT and self.late and host:
            self.state, self.caps = NATIVE, caps
        return True

    def end(self, now):
        """The input ended, or the caller gave up."""
        self._fire(now)
        if not self.decided:
            self.state, self.decided = TEXT, True
        self.done = True


# --- keys (SDK.md §3.10; SPEC.md §10.2, §10.4) --------------------------------

MODIFIERS = ("Control", "Alt", "Meta", "Shift")
# Mod, in a binding, is the platform's modifier for commands (SPEC.md
# §10.4), written first.
_ALL_MODS = ("Mod",) + MODIFIERS

ACTIONS = (
    "char-backward", "char-forward", "word-backward", "word-forward", "line-start", "line-end",
    "delete-char-backward", "delete-char-forward", "delete-word-backward", "delete-word-forward",
    "delete-to-line-start", "delete-to-line-end", "line-previous", "line-next", "page-up", "page-down",
    "input-start", "input-end", "select-all", "newline", "submit", "program", "prefix",
    "copy", "cut", "paste", "undo", "redo",
) + (
    "scroll-up", "scroll-down", "scroll-left", "scroll-right", "scroll-page-up", "scroll-page-down",
    "scroll-half-page-up", "scroll-half-page-down", "scroll-start", "scroll-end",
)
# The scroll actions, which a text field's keymap leaves out (SPEC.md §10.2).
SCROLL_ACTIONS = frozenset(a for a in ACTIONS if a.startswith("scroll-"))
# The actions only a multi-line field has (SPEC.md §10.2).
MULTILINE_ACTIONS = frozenset(("line-previous", "line-next", "page-up", "page-down", "newline"))
# The moves, which select with Shift (SPEC.md §10.2).
MOVES = frozenset(("char-backward", "char-forward", "word-backward", "word-forward", "line-start", "line-end",
                   "line-previous", "line-next", "page-up", "page-down", "input-start", "input-end"))
# The moves that go back or up, which start from a selection's start.
_BACK = frozenset(("char-backward", "word-backward", "line-start", "line-previous", "page-up", "input-start"))
# What Lookup returns for a character the field types.
INSERT = "insert"

# The SDK's keymap (SDK.md §3.10): Bubble Tea's text input and text area, but
# Mod+a selects all.
TERMINAL_KEYS = " ".join((
    "ArrowLeft=char-backward Control+b=char-backward ArrowRight=char-forward Control+f=char-forward",
    "Alt+ArrowLeft=word-backward Control+ArrowLeft=word-backward Alt+b=word-backward",
    "Alt+ArrowRight=word-forward Control+ArrowRight=word-forward Alt+f=word-forward",
    "Home=line-start End=line-end Control+e=line-end",
    "Backspace=delete-char-backward Control+h=delete-char-backward",
    "Delete=delete-char-forward Control+d=delete-char-forward",
    "Alt+Backspace=delete-word-backward Control+w=delete-word-backward Control+Backspace=delete-word-backward",
    "Alt+Delete=delete-word-forward Alt+d=delete-word-forward Control+Delete=delete-word-forward",
    "Control+u=delete-to-line-start Control+k=delete-to-line-end",
    "ArrowUp=line-previous Control+p=line-previous ArrowDown=line-next Control+n=line-next",
    "PageUp=page-up PageDown=page-down",
    "Alt+<=input-start Control+Home=input-start Alt+>=input-end Control+End=input-end",
    "Mod+a=select-all",
    "Control+m=newline",
))

_NAMED = re.compile(r"[A-Z][A-Za-z0-9]+\Z")


def chars(s):
    """A text's characters. This client counts code points, CR LF one
    (SDK.md §4.6): it has no grapheme segmentation."""
    out, i = [], 0
    while i < len(s):
        n = 2 if s.startswith("\r\n", i) else 1
        out.append(s[i:i + n])
        i += n
    return out


def _is_char(v):
    c = chars(v)
    return len(c) == 1 and ord(v[0]) >= 0x20 and v[0] != "\x7f"


def _split_key(name):
    """A key's name as (modifiers, value), or None when it does not parse."""
    if name.endswith("++") and len(name) > 2:
        head, value = name[:-2], "+"
    elif name == "+":
        head, value = "", "+"
    else:
        i = name.rfind("+")
        head, value = (name[:i], name[i + 1:]) if i >= 0 else ("", name)
    mods = head.split("+") if head else []
    if any(m not in _ALL_MODS for m in mods) or len(set(mods)) != len(mods):
        return None
    if value == "Space":
        value = " "
    if not (_is_char(value) or _NAMED.match(value)):
        return None
    return mods, value


def _key_name(mods, value):
    """The canonical name of a key: modifiers in order, Shift shown in a
    letter where it can be, Space for a space."""
    mods = set(mods)
    if "Shift" in mods and _is_char(value) and len(value) == 1:
        up, low = value.upper(), value.lower()
        if len(up) == 1 and up != value:
            value, mods = up, mods - {"Shift"}
        elif len(low) == 1 and low != value:
            mods = mods - {"Shift"}
    return "+".join([m for m in _ALL_MODS if m in mods] + ["Space" if value == " " else value])


def parse_key(name):
    """A key's name in its canonical form (SDK.md §3.10), or None."""
    k = _split_key(name)
    return None if k is None else _key_name(*k)


_C0 = {0x00: "Control+Space", 0x08: "Control+h", 0x09: "Tab", 0x0D: "Enter", 0x1B: "Escape", 0x7F: "Backspace",
       0x1C: "Control+\\", 0x1D: "Control+]", 0x1E: "Control+^", 0x1F: "Control+_"}
_CSI_FINAL = {"A": "ArrowUp", "B": "ArrowDown", "C": "ArrowRight", "D": "ArrowLeft", "H": "Home", "F": "End"}
_TILDE = {1: "Home", 7: "Home", 4: "End", 8: "End", 2: "Insert", 3: "Delete", 5: "PageUp", 6: "PageDown"}
_CODES = {9: "Tab", 13: "Enter", 27: "Escape", 8: "Backspace", 127: "Backspace"}
# The kitty keyboard protocol's codes from 57344 that name keys.
_KITTY = {57399 + i: str(i) for i in range(10)}
_KITTY.update({57409: ".", 57410: "/", 57411: "*", 57412: "-", 57413: "+", 57414: "Enter", 57415: "=",
               57417: "ArrowLeft", 57418: "ArrowRight", 57419: "ArrowUp", 57420: "ArrowDown",
               57421: "PageUp", 57422: "PageDown", 57423: "Home", 57424: "End", 57425: "Insert", 57426: "Delete",
               57441: "Shift", 57442: "Control", 57443: "Alt", 57444: "Meta", 57447: "Shift", 57448: "Control",
               57449: "Alt", 57450: "Meta"})


def _with(name, add):
    """A key's name with more modifiers."""
    if name is None:
        return None
    mods, value = _split_key(name)
    return _key_name(mods + [m for m in add if m not in mods], value)


def _mods(field):
    """The modifiers in a CSI parameter `m[:e]`, and whether it is a
    release."""
    parts = field.split(":")
    try:
        m = int(parts[0]) if parts[0] else 1
        e = int(parts[1]) if len(parts) > 1 and parts[1] else 1
    except ValueError:
        return None, False
    bits = max(m - 1, 0)
    mods = [n for n, b in (("Shift", 1), ("Alt", 2), ("Control", 4)) if bits & b]
    if bits & (8 | 32):
        mods.append("Meta")
    return mods, e == 3


def _code_key(code, mods, shifted=None, text=None):
    """The key a kitty or modifyOtherKeys code names."""
    if code in _CODES:
        return _key_name(mods, _CODES[code])
    if code >= 57344:
        return _key_name(mods, _KITTY[code]) if code in _KITTY else None
    if code < 0x20 or code == 0x7F:
        return None
    value = chr(code)
    if "Shift" in mods:
        if shifted:
            value = chr(shifted)
        elif text:
            value = text
        elif len(value.upper()) == 1:
            value = value.upper()
        if value != chr(code):
            mods = [m for m in mods if m != "Shift"]
    return "+".join([m for m in MODIFIERS if m in mods] + ["Space" if value == " " else value])


def _csi(params, final):
    """The key a CSI sequence names, or None."""
    if params[:1] in ("<", "=", ">", "?"):
        return None
    fields = params.split(";")
    try:
        if final == "u":
            codes = [int(x) if x else 0 for x in fields[0].split(":")]
            mods, release = _mods(fields[1]) if len(fields) > 1 else ([], False)
            if release or mods is None:
                return None
            text = "".join(chr(int(x)) for x in fields[2].split(":") if x) if len(fields) > 2 else None
            return _code_key(codes[0], mods, codes[1] if len(codes) > 1 else None, text)
        if final == "~":
            n = int(fields[0]) if fields[0] else 0
            if n == 27 and len(fields) >= 3:
                mods, release = _mods(fields[1])
                return None if release or mods is None else _code_key(int(fields[2]), mods)
            if n not in _TILDE:
                return None
            mods, release = _mods(fields[1]) if len(fields) > 1 else ([], False)
            return None if release or mods is None else _key_name(mods, _TILDE[n])
        if final in _CSI_FINAL:
            mods, release = _mods(fields[1]) if len(fields) > 1 else ([], False)
            return None if release or mods is None else _key_name(mods, _CSI_FINAL[final])
        if final == "Z":
            return "Shift+Tab"
    except ValueError:
        return None
    return None


def _one(data, i):
    """The key of a control byte or a character at data[i], and its length."""
    b = data[i]
    if b < 0x20 or b == 0x7F:
        return (_C0[b] if b in _C0 else "Control+" + chr(b + 0x60)), 1
    n = 1 if b < 0x80 else 2 if b >> 5 == 6 else 3 if b >> 4 == 14 else 4 if b >> 3 == 30 else 0
    try:
        c = data[i:i + n].decode() if n else None
    except UnicodeDecodeError:
        c = None
    if c is None or len(c) != 1:
        return None, 1
    return ("Space" if c == " " else c), n


def decode_keys(data):
    """The keys in input from the terminal (SDK.md §3.10, SPEC.md §10.4): a
    canonical name for each, None for input that is no key."""
    if isinstance(data, str):
        data = data.encode()
    out, i = [], 0
    while i < len(data):
        if data[i] != 0x1B:
            k, n = _one(data, i)
            out.append(k)
            i += n
            continue
        if i + 1 == len(data):
            out.append("Escape")
            break
        nxt = data[i + 1]
        if nxt in (0x5B, 0x4F) and i + 2 < len(data):
            if nxt == 0x4F:
                out.append(_CSI_FINAL.get(chr(data[i + 2])) if chr(data[i + 2]) in "ABCDHF" else None)
                i += 3
                continue
            j = i + 2
            while j < len(data) and 0x30 <= data[j] <= 0x3F:
                j += 1
            params = data[i + 2:j].decode()
            while j < len(data) and 0x20 <= data[j] <= 0x2F:
                j += 1
            if j == len(data):
                out.append(None)
                break
            out.append(_csi(params, chr(data[j])) if data[j] >= 0x40 else None)
            i = j + 1
            continue
        k, n = _one(data, i + 1)
        out.append(_with(k, ["Alt"]))
        i += 1 + n
    return out


class Platform:
    """How a host reads bindings (SDK.md §3.10): Mod, Control or Meta, and
    its edit shortcuts, from action to keys; None for the defaults."""

    def __init__(self, mod="Control", edit=None):
        self.mod = mod if mod in ("Control", "Meta") else "Control"
        self.edit = edit


def platform_of(caps):
    """The Platform of a host's capabilities, the defaults where absent."""
    return Platform(caps.mod or "Control", caps.edit)


_EDIT_ACTIONS = ("select-all", "copy", "cut", "paste", "undo", "redo")


def _read_mod(key, mod):
    """A canonical key's name with Mod read as mod."""
    mods, value = _split_key(key)
    return _key_name([mod if m == "Mod" else m for m in mods], value)


def default_edit(mod="Control"):
    """The default edit shortcuts for a Mod (SPEC.md §10.2), Mod read."""
    e = {"select-all": ["Mod+a"], "copy": ["Mod+c"], "cut": ["Mod+x"], "paste": ["Mod+v"], "undo": ["Mod+z"],
         "redo": ["Mod+Z"] + (["Control+y"] if mod == "Control" else [])}
    return {a: [_read_mod(k, mod) for k in ks] for a, ks in e.items()}


class Keymap:
    """Bindings of keys to actions (SPEC.md §10.2), read on a Platform.
    `resolve` makes the one a field uses, whose `lookup` says what the field
    does with a key."""

    def __init__(self, multiline=False, platform=None):
        self.bindings = {}  # key, Mod read, to action
        self.written = {}  # key, Mod read, to its last binding's key
        self.multiline = multiline
        self.platform = platform or Platform()

    def bind(self, key, action):
        k = _read_mod(key, self.platform.mod)
        self.bindings[k] = action
        self.written[k] = key

    def format(self):
        return " ".join(f"{self.written[k]}={a}" for k, a in self.bindings.items())

    def _key(self, key):
        """A key's canonical name with Mod read, or None."""
        k = parse_key(key)
        return None if k is None else _read_mod(k, self.platform.mod)

    def _bound(self, k):
        """The action bound to canonical key k, or to k without Shift when k
        has Shift and is not bound itself."""
        mods, value = _split_key(k)
        a = self.bindings.get(k)
        if a is None and "Shift" in mods:
            a = self.bindings.get(_key_name([m for m in mods if m != "Shift"], value))
        return a

    def program(self, key):
        """Whether the keymap gives the key to the program (SPEC.md §10.2):
        it binds the key to `program` or `prefix`. On an element that is not
        a text field, a host asks it of the element's data-keys alone, before
        the element or a scroll uses it."""
        k = self._key(key)
        return k is not None and self._bound(k) in ("program", "prefix")

    def prefix(self, key):
        """Whether the keymap binds the key to `prefix`, with the same
        fallback without Shift: a host gives the program every key after it
        (SPEC.md §10.5)."""
        k = self._key(key)
        return k is not None and self._bound(k) == "prefix"

    def scroll(self, key):
        """The scroll action the keymap binds the key to, or None (SPEC.md
        §10.2): a host asks it, outside a text field, for a key the element
        does not use."""
        k = self._key(key)
        a = None if k is None else self._bound(k)
        return a if a in SCROLL_ACTIONS else None

    def lookup(self, key):
        """An action, INSERT for a character the field types, or None when
        the key is not the field's."""
        k = self._key(key)
        if k is None or k in ("Tab", "Shift+Tab", "Escape"):
            return None
        mods, value = _split_key(k)
        a = self._bound(k)
        if a is not None:
            return None if a in ("program", "prefix") or (a in MULTILINE_ACTIONS and not self.multiline) else a
        if _is_char(value) and not {"Control", "Alt", "Meta"} & set(mods):
            return INSERT
        return None

    def selects(self, key):
        """Whether the field selects with the key (SPEC.md §10.2): it looks
        up a move, and its name has Shift. The field then extends with it."""
        k = self._key(key)
        return k is not None and self.lookup(k) in MOVES and "Shift" in _split_key(k)[0]


def _bindings(value):
    """A data-keys value's bindings, in order, without those a host ignores."""
    for b in re.split(r"[ \t\n\f\r]+", value):
        i = b.rfind("=")
        if i < 0:
            continue
        k, a = parse_key(b[:i]), b[i + 1:]
        if k is None or a not in ACTIONS or k in ("Tab", "Shift+Tab", "Escape"):
            continue
        yield k, a


def parse_keymap(platform, value):
    """A data-keys value's bindings, without those a host ignores, Mod read
    as the platform's."""
    m = Keymap(platform=platform)
    for k, a in _bindings(value):
        m.bind(k, a)
    return m


# The default keymap (SPEC.md §10.2): every host's keys, then those of its
# Mod; the edit shortcuts come last.
_DEFAULT = (("ArrowLeft", "char-backward"), ("ArrowRight", "char-forward"),
            ("Alt+ArrowLeft", "word-backward"), ("Alt+ArrowRight", "word-forward"),
            ("Home", "line-start"), ("End", "line-end"),
            ("Backspace", "delete-char-backward"), ("Delete", "delete-char-forward"),
            ("Alt+Backspace", "delete-word-backward"), ("Alt+Delete", "delete-word-forward"),
            ("ArrowUp", "line-previous"), ("ArrowDown", "line-next"), ("PageUp", "page-up"), ("PageDown", "page-down"))
_DEFAULT_MOD = {
    "Control": (("Control+ArrowLeft", "word-backward"), ("Control+ArrowRight", "word-forward"),
                ("Control+Home", "input-start"), ("Control+End", "input-end"),
                ("Control+Backspace", "delete-word-backward"), ("Control+Delete", "delete-word-forward")),
    "Meta": (("Meta+ArrowLeft", "line-start"), ("Meta+ArrowRight", "line-end"),
             ("Meta+ArrowUp", "input-start"), ("Meta+ArrowDown", "input-end"),
             ("Meta+Backspace", "delete-to-line-start"),
             ("Control+a", "line-start"), ("Control+e", "line-end"),
             ("Control+b", "char-backward"), ("Control+f", "char-forward"),
             ("Control+p", "line-previous"), ("Control+n", "line-next"),
             ("Control+h", "delete-char-backward"), ("Control+d", "delete-char-forward"),
             ("Control+k", "delete-to-line-end")),
}


def resolve(platform, multiline, *values):
    """A field's keymap: SPEC.md's default for the platform, then each
    data-keys value, the root's first, less their scroll actions."""
    platform = platform or Platform()
    m = Keymap(multiline, platform)
    for k, a in _DEFAULT + (("Enter", "newline" if multiline else "submit"),) + _DEFAULT_MOD[platform.mod]:
        m.bind(k, a)
    edit = platform.edit if platform.edit is not None else default_edit(platform.mod)
    for a, keys in edit.items():
        if a not in _EDIT_ACTIONS:
            continue
        for key in keys:
            k = parse_key(key)
            if k is not None and k not in ("Tab", "Shift+Tab", "Escape"):
                m.bind(k, a)
    for v in values:
        for k, a in _bindings(v):
            if a not in SCROLL_ACTIONS:
                m.bind(k, a)
    return m


# --- a field in cells (SDK.md §4.6) -------------------------------------------

_WHITE_SPACE = frozenset([*range(0x09, 0x0E), 0x20, 0x85, 0xA0, 0x1680, *range(0x2000, 0x200B), 0x2028, 0x2029, 0x202F, 0x205F, 0x3000])


def _space(c):
    return ord(c[0]) in _WHITE_SPACE


def _break(c):
    return c in ("\n", "\r", "\r\n")


class Field:
    """A text field's value, caret and selection, edited by SPEC.md §10.2's
    actions. The caret counts characters (`chars`). The selection runs from
    `anchor` to the caret; nothing is selected when `anchor` is None or at
    the caret."""

    def __init__(self, value="", caret=None, multiline=False, password=False, rows=1, anchor=None):
        self.value = value
        self.caret = len(chars(value)) if caret is None else caret
        self.multiline = multiline
        self.password = password
        self.rows = rows
        self.anchor = anchor
        self._goal = None

    def selection(self):
        """The selection's start and end, equal when nothing is selected."""
        n = len(chars(self.value))
        p = min(max(self.caret, 0), n)
        a = p if self.anchor is None else min(max(self.anchor, 0), n)
        return min(a, p), max(a, p)

    def select(self, anchor, caret):
        """Selects from anchor to caret; select(p, p) puts the caret at p with
        nothing selected. It ends a run of row moves."""
        self._goal = None
        self.caret = caret
        self.anchor = None if anchor == caret else anchor

    def _lines(self, c):
        """The start and end of each line."""
        out, start = [], 0
        for i, ch in enumerate(c):
            if self.multiline and _break(ch):
                out.append((start, i))
                start = i + 1
        out.append((start, len(c)))
        return out

    def _word_back(self, c, p):
        if self.password:
            return 0
        while p > 0 and _space(c[p - 1]):
            p -= 1
        while p > 0 and not _space(c[p - 1]):
            p -= 1
        return p

    def _word_forward(self, c, p):
        if self.password:
            return len(c)
        while p < len(c) and _space(c[p]):
            p += 1
        while p < len(c) and not _space(c[p]):
            p += 1
        return p

    def _rows(self, c, p, by):
        lines = self._lines(c)
        r = next(i for i, (s, e) in enumerate(lines) if s <= p <= e)
        if self._goal is None:
            self._goal = p - lines[r][0]
        t = r + by
        if t < 0:
            return 0
        if t >= len(lines):
            return len(c)
        s, e = lines[t]
        return s + min(self._goal, e - s)

    def _delete(self, c, a, b):
        if a >= b:
            return False
        self.value = "".join(c[:a] + c[b:])
        self.caret = a
        return True

    def do(self, action):
        """Does an action; returns whether the value changed. A selection comes
        first: a delete deletes it, a move starts from its start going back
        and from its end otherwise, and ends it."""
        return self._act(action, False)

    def extend(self, action):
        """Does a move as Shift does it: the anchor stays, or is set at the
        caret, and the caret moves from where it is. An action that is not a
        move is do's."""
        return self._act(action, action in MOVES)

    def _act(self, action, extend):
        c = chars(self.value)
        p = min(max(self.caret, 0), len(c))
        rows = action in ("line-previous", "line-next", "page-up", "page-down")
        if not rows:
            self._goal = None
        if action in MULTILINE_ACTIONS and not self.multiline:
            return False
        lo, hi = self.selection()
        if action == "select-all":
            self.anchor, self.caret = 0, len(c)
            return False
        if action == "newline":
            return self.type("\n")
        if extend:
            if self.anchor is None:
                self.anchor = p
        elif lo < hi and action in MOVES:
            self.anchor = None
            p = lo if action in _BACK else hi
            if action in ("char-backward", "char-forward"):
                self.caret = p
                return False
        elif lo < hi and action.startswith("delete-"):
            self.anchor = None
            return self._delete(c, lo, hi)
        elif lo == hi:
            self.anchor = None
        lines = self._lines(c)
        s, e = next((s, e) for s, e in lines if s <= p <= e)
        move = {
            "char-backward": lambda: max(p - 1, 0),
            "char-forward": lambda: min(p + 1, len(c)),
            "word-backward": lambda: self._word_back(c, p),
            "word-forward": lambda: self._word_forward(c, p),
            "line-start": lambda: s,
            "line-end": lambda: e,
            "line-previous": lambda: self._rows(c, p, -1),
            "line-next": lambda: self._rows(c, p, 1),
            "page-up": lambda: self._rows(c, p, -max(self.rows, 1)),
            "page-down": lambda: self._rows(c, p, max(self.rows, 1)),
            "input-start": lambda: 0,
            "input-end": lambda: len(c),
        }.get(action)
        if move is not None:
            self.caret = move()
            if self.anchor == self.caret:
                self.anchor = None
            return False
        span = {
            "delete-char-backward": (max(p - 1, 0), p),
            "delete-char-forward": (p, min(p + 1, len(c))),
            "delete-word-backward": (self._word_back(c, p), p),
            "delete-word-forward": (p, self._word_forward(c, p)),
            "delete-to-line-start": (s, p),
            "delete-to-line-end": (p, e),
        }.get(action)
        if span is not None:
            self.caret = p
            return self._delete(c, *span)
        return False

    def type(self, text):
        """Types text in place of the selection, or at the caret; returns
        whether the value changed."""
        self._goal = None
        if not text:
            return False
        c = chars(self.value)
        lo, hi = self.selection()
        self.anchor = None
        before = "".join(c[:lo]) + text
        self.value = before + "".join(c[hi:])
        self.caret = len(chars(before))
        return True



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

    def doc(self, surface, html, quiet=None, detached=False, scroll=0):
        self.write(doc(surface, html, detached=detached, scroll=scroll, q=quiet))

    def place(self, surface, cols, rows="auto", move_cursor=True, quiet=None, window=None, z=0, press=None, fit=None, hover=None):
        """Places a surface at the cursor. `window` is (x, y, w, h): the part
        of the surface to show (SPEC §5.2), or None for all of it; `z` puts
        the placement above (greater) or below overlapping ones; `press`
        asks for a `press` event on every press in it (SPEC §9); `fit` asks
        for a `fit` event whenever the rows its document needs change;
        `hover` asks for a `hover` event whenever the element under the
        pointer changes, or the pointer leaves (SPEC §9.4). These three
        belong to the surface: None leaves them as they were, True turns
        them on and False off (SPEC §5.2)."""
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

    def hide(self, surface, quiet=None):
        """Removes the placement and keeps the surface (SPEC §5.4)."""
        self.write(hide(surface, q=quiet))

    def delta(self, surface, *ops, quiet=None):
        """Sends one delta of the ops (`morph`, `text`, … build them): the
        changes of a frame to one surface go in one delta (SDK.md §2.9)."""
        self.write(delta(surface, *ops, q=quiet))

    def text(self, surface, target, text):
        self.write(set_text(surface, target, text))

    def var(self, surface, target, name, value):
        self.write(set_var(surface, target, name, value))

    def attr(self, surface, target, name, value):
        self.write(set_attr(surface, target, name, value))

    def reveal(self, surface, target, where=""):
        self.write(reveal(surface, target, where))

    def res(self, name, mime, data, quiet=None):
        self.write(res(name, mime, data, q=quiet))

    def delete(self, surface, quiet=None):
        self.write(delete(surface, q=quiet))

    def detach(self, surface, quiet=None):
        self.write(detach(surface, q=quiet))

    def focus(self, surface, target=None, quiet=None):
        self.write(focus(surface, target or "", q=quiet))

    def blur(self, surface, quiet=None):
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
        """Is there a HOTTY host that speaks VERSION? Returns its
        capabilities (a Caps), or None. Reads until detection is done (SDK.md §3.8), and leaves
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
        self.caps = det.caps
        return det.caps
