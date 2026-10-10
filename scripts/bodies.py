#!/usr/bin/env python3
"""Writes the host bodies in conformance/vectors.json from their JSON twins.

A host's bodies are msgpack in base64 (SPEC.md §3.3), which no one reads.
So a decode vector's `bodies`, and a detect step's `body`, show each one as
JSON (conformance/README.md, Numbers), and this writes the base64 in the
sequences from them:

    python3 scripts/bodies.py          # writes the file
    python3 scripts/bodies.py --check  # fails when it would change it

A twin's maps are written in its order, its ints in their smallest form and
its floats in 64 bits. A twin `{"hex": …}` is those bytes as they are.
"""

import base64
import json
import os
import re
import struct
import sys

PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "conformance", "vectors.json")

# A HOTTY sequence: its control, its payload, and its terminator.
SEQ = re.compile(r"^(\x1b\]7279;)([^;\x07\x1b]*);([^\x07\x1b]*)((?:\x07|\x1b\\)?)$")


def pack(v, out):
    """Appends v's msgpack to out."""
    if v is None:
        out.append(0xC0)
    elif v is True or v is False:
        out.append(0xC3 if v else 0xC2)
    elif isinstance(v, int):
        if 0 <= v < 0x80:
            out.append(v)
        elif -32 <= v < 0:
            out.append(v & 0xFF)
        elif v >= 0:
            for tag, fmt, top in ((0xCC, ">B", 1 << 8), (0xCD, ">H", 1 << 16), (0xCE, ">I", 1 << 32), (0xCF, ">Q", 1 << 64)):
                if v < top:
                    out += bytes([tag]) + struct.pack(fmt, v)
                    break
            else:
                raise ValueError(f"int {v} is too large")
        else:
            for tag, fmt, low in ((0xD0, ">b", -(1 << 7)), (0xD1, ">h", -(1 << 15)), (0xD2, ">i", -(1 << 31)), (0xD3, ">q", -(1 << 63))):
                if v >= low:
                    out += bytes([tag]) + struct.pack(fmt, v)
                    break
            else:
                raise ValueError(f"int {v} is too small")
    elif isinstance(v, float):
        out += b"\xcb" + struct.pack(">d", v)
    elif isinstance(v, str):
        b = v.encode()
        n = len(b)
        if n < 32:
            out.append(0xA0 | n)
        elif n < 1 << 8:
            out += bytes([0xD9, n])
        elif n < 1 << 16:
            out += b"\xda" + struct.pack(">H", n)
        else:
            out += b"\xdb" + struct.pack(">I", n)
        out += b
    elif isinstance(v, list):
        header(len(v), 0x90, 0xDC, out)
        for x in v:
            pack(x, out)
    elif isinstance(v, dict):
        header(len(v), 0x80, 0xDE, out)
        for k, x in v.items():
            pack(k, out)
            pack(x, out)
    else:
        raise TypeError(f"no msgpack for {v!r}")


def header(n, fix, tag16, out):
    if n < 16:
        out.append(fix | n)
    elif n < 1 << 16:
        out += bytes([tag16]) + struct.pack(">H", n)
    else:
        out += bytes([tag16 + 1]) + struct.pack(">I", n)


def body_bytes(twin):
    if isinstance(twin, dict) and list(twin) == ["hex"]:
        return bytes.fromhex(twin["hex"])
    out = bytearray()
    pack(twin, out)
    return bytes(out)


def parse(seq):
    m = SEQ.match(seq)
    if not m:
        return None
    pairs = dict(p.split("=", 1) for p in m.group(2).split(":") if "=" in p)
    return m, pairs


def write_seqs(seqs, bodies, name):
    """Writes the base64 of each body in bodies into the sequences that carry it."""
    if len(bodies) != len(seqs):
        raise SystemExit(f"{name}: {len(bodies)} bodies for {len(seqs)} sequences")
    seqs = list(seqs)
    for i, twin in enumerate(bodies):
        if twin is None:
            continue
        p = parse(seqs[i])
        if not p or "a" not in p[1]:
            raise SystemExit(f"{name}: sequence {i} has a body but starts no message")
        # The message's chunks: this sequence, and the continuations after
        # it up to the last (m=0), skipping what is not HOTTY's.
        chunks = [i]
        more = p[1].get("m") == "1"
        j = i + 1
        while more and j < len(seqs):
            q = parse(seqs[j])
            if q and "a" not in q[1]:
                chunks.append(j)
                more = q[1].get("m") == "1"
            elif q or seqs[j].startswith("\x1b]7279"):
                break
            j += 1
        text = base64.b64encode(body_bytes(twin)).decode()
        # Each chunk keeps its length, and the last, when the message ends,
        # takes the rest.
        ends = not more
        at = 0
        for k, c in enumerate(chunks):
            m, _ = parse(seqs[c])
            if k == len(chunks) - 1 and ends:
                part = text[at:]
            else:
                part = text[at : at + len(m.group(3))]
            if k < len(chunks) - 1 and len(part) < len(m.group(3)):
                raise SystemExit(f"{name}: sequence {c}'s chunk is longer than the body")
            at += len(part)
            seqs[c] = m.group(1) + m.group(2) + ";" + part + m.group(4)
    return seqs


def main():
    check = sys.argv[1:] == ["--check"]
    with open(PATH, encoding="utf-8") as f:
        old = f.read()
    v = json.loads(old)
    for d in v["decode"]:
        if "bodies" in d:
            d["seqs"] = write_seqs(d["seqs"], d["bodies"], d["name"])
    for d in v["detect"]:
        for s in d["steps"]:
            if "body" in s:
                (s["osc"],) = write_seqs([s["osc"]], [s["body"]], d["name"])
    new = json.dumps(v, indent=1) + "\n"
    if check:
        if new != old:
            raise SystemExit("conformance/vectors.json: a body is not its twin: run python3 scripts/bodies.py")
        return
    if new != old:
        with open(PATH, "w", encoding="utf-8") as f:
            f.write(new)


if __name__ == "__main__":
    main()
