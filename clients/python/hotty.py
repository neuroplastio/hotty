"""The reference client: speak HOTTY (SPEC.md) from a Python program.

No dependencies. The program writes commands to its stdout like any other escape
sequence, and reads replies and events from its stdin, which must be in raw mode
(use `Hotty.raw()`).
"""

import base64
import contextlib
import json
import os
import re
import select
import sys
import termios
import tty
import zlib

OSC_NUMBER = "7279"
CHUNK = 4096


def encode(control, payload=b""):
    """One command as OSC chunks. `control` is an ordered dict of str -> str."""
    if isinstance(payload, str):
        payload = payload.encode()
    control = dict(control)
    body = payload
    if len(payload) > 256:
        z = zlib.compress(payload, 1)
        if len(z) < len(payload):
            control["o"] = "z"
            body = z
    b64 = base64.b64encode(body).decode()
    ctl = ":".join(f"{k}={v}" for k, v in control.items())
    if len(b64) <= CHUNK:
        return f"\x1b]{OSC_NUMBER};{ctl}" + (f";{b64}" if b64 else "") + "\x1b\\"
    parts = []
    chunks = [b64[i : i + CHUNK] for i in range(0, len(b64), CHUNK)]
    for i, c in enumerate(chunks):
        last = i == len(chunks) - 1
        if i == 0:
            parts.append(f"\x1b]{OSC_NUMBER};{ctl}:m=1;{c}\x1b\\")
        else:
            parts.append(f"\x1b]{OSC_NUMBER};m={0 if last else 1};{c}\x1b\\")
    return "".join(parts)


_OSC = re.compile(rb"\x1b\]" + OSC_NUMBER.encode() + rb";([^;\x07\x1b]*)(?:;([^\x07\x1b]*))?(?:\x07|\x1b\\)")


class Message:
    """A reply or event from the host."""

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

    def __repr__(self):
        return f"Message({self.control}, {self.payload[:80]!r})"


def _decode(control_bytes, payload_bytes):
    control = {}
    for part in control_bytes.decode("ascii", "replace").split(":"):
        if "=" in part:
            k, v = part.split("=", 1)
            control[k] = v
    payload = b""
    if payload_bytes:
        payload = base64.b64decode(payload_bytes + b"=" * (-len(payload_bytes) % 4))
        if control.get("o") == "z":
            payload = zlib.decompress(payload)
    return Message(control, payload)


class Hotty:
    def __init__(self, out=None, inp=None):
        self.out = out or sys.stdout.buffer
        self.inp_fd = (inp or sys.stdin).fileno()
        self.buffer = b""
        self._n = 0

    # --- sending ---------------------------------------------------------

    def send(self, payload=b"", **control):
        self.out.write(encode(control, payload).encode())
        self.out.flush()

    def write(self, text):
        self.out.write(text.encode() if isinstance(text, str) else text)
        self.out.flush()

    def doc(self, surface, html, quiet=1):
        self.send(html, a="doc", s=surface, q=quiet)

    def place(self, surface, cols, rows="auto", move_cursor=True, quiet=1, window=None, z=0, press=False, fit=False):
        """Places a surface at the cursor. `window` is (x, y, w, h): the part
        of the surface to show (SPEC §5.2), or None for all of it; `z` puts
        the placement above (greater) or below overlapping ones; `press`
        asks for a `press` event on every press in it (SPEC §9); `fit` asks
        for a `fit` event whenever the rows its document needs change."""
        control = dict(a="place", s=surface, c=cols, r=rows, q=quiet)
        if window is not None:
            control.update(zip("xywh", window))
        if z:
            control["z"] = z
        if press:
            control["p"] = 1
        if fit:
            control["f"] = 1
        if not move_cursor:
            control["C"] = 1
        self.send(**control)

    def hide(self, surface, quiet=1):
        """Removes the placement and keeps the surface (SPEC §5.4)."""
        self.send(a="hide", s=surface, q=quiet)

    def patch(self, surface, op, target=None, payload="", key=None, quiet=1):
        control = dict(a="patch", s=surface, op=op, q=quiet)
        if target:
            control["t"] = target
        if key:
            control["k"] = key
        self.send(payload, **control)

    def text(self, surface, target, text):
        self.patch(surface, "text", target, text)

    def var(self, surface, target, name, value):
        self.patch(surface, "var", target, str(value), key=name)

    def attr(self, surface, target, name, value):
        self.patch(surface, "attr", target, str(value), key=name)

    def res(self, name, mime, data, quiet=1):
        self.send(data, a="res", id=name, type=mime, q=quiet)

    def delete(self, surface):
        self.send(a="del", s=surface, q=1)

    def focus(self, surface, target=None):
        control = dict(a="focus", s=surface, q=1)
        if target:
            control["t"] = target
        self.send(**control)

    def blur(self, surface):
        self.send(a="blur", s=surface, q=1)

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
        """Splits the buffer into (messages, other input bytes)."""
        messages = []
        other = b""
        pos = 0
        for m in _OSC.finditer(self.buffer):
            other += self.buffer[pos : m.start()]
            messages.append(_decode(m.group(1), m.group(2) or b""))
            pos = m.end()
        rest = self.buffer[pos:]
        # Keep an unfinished HOTTY message (ESC ] …) for the next read. A lone
        # ESC is the Escape key: it goes to the program now.
        cut = rest.rfind(b"\x1b]")
        if cut != -1 and not re.search(rb"\x07|\x1b\\", rest[cut + 2 :]) and len(rest) - cut < (64 << 20):
            other += rest[:cut]
            self.buffer = rest[cut:]
            return messages, other
        other += rest
        self.buffer = b""
        return messages, other

    def query(self, timeout=0.5):
        """Is there a HOTTY host? Returns its capabilities, or None.

        Sends the query and then DA1: a terminal that is not a host answers only DA1.
        """
        self.write(f"\x1b]{OSC_NUMBER};a=q:n=1\x1b\\\x1b[c")
        caps = None
        import time

        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if not self.read(max(0.0, deadline - time.monotonic())):
                break
            msgs, _ = self.take()
            for m in msgs:
                if m["a"] == "ok" and m["re"] == "q":
                    caps = m.json or {}
            if re.search(rb"\x1b\[\?[\d;]*c", self.buffer) or caps is not None:
                # DA1 arrived (or we have our answer): drain DA1 and stop.
                self.read(0.05)
                self.buffer = re.sub(rb"\x1b\[\?[\d;]*c", b"", self.buffer)
                break
        return caps
