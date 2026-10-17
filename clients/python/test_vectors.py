"""Runs the conformance vectors' SDK sections against this client: wire,
build, encode, decode, scan, detect, keys, keymap and edit
(conformance/README.md).

    python3 clients/python/test_vectors.py [vectors.json]
"""

import base64
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import hotty  # noqa: E402

# What this client implements, for vectors marked "requires".
FEATURES = {
    "options.unordered",
    "decode.abort-count",
    "decode.max",
    "decode.unterminated",
    "scanner.da1",
}

failures = []
counts = {}


def check(section, name, ok, why=""):
    counts.setdefault(section, [0, 0])
    counts[section][0 if ok else 1] += 1
    if not ok:
        failures.append(f"{section}: {name}: {why}")


def runs(v):
    return set(v.get("requires", [])) <= FEATURES


def osc_segments(out):
    """A builder's or encoder's output as [("raw", text) | ("osc", bytes)]."""
    sc = hotty.Scanner()
    segs = sc.feed(out.encode() if isinstance(out, str) else out) + sc.flush()
    return [("raw", b.decode()) if k == "pass" else ("osc", b) for k, b in segs]


# --- wire --------------------------------------------------------------------


def run_wire(v):
    sc, dec = hotty.Scanner(), hotty.Decoder()
    got = []
    for kind, b in sc.feed(v["stream"].encode()) + sc.flush():
        if kind != "osc":
            continue
        result, m = dec.feed(b)
        if result == hotty.COMPLETE:
            got.append(m)
    invalid = sc.invalid + dec.invalid
    if invalid != v["invalid"]:
        return False, f"invalid {invalid}, want {v['invalid']}"
    if len(got) != len(v["commands"]):
        return False, f"{len(got)} commands, want {len(v['commands'])}"
    for m, want in zip(got, v["commands"]):
        if "m" in m.control or "o" in m.control:
            return False, f"m or o left in {m.control}"
        for k, val in want["control"].items():
            if m.control.get(k) != val:
                return False, f"{k}={m.control.get(k)!r}, want {val!r}"
        if m.payload.decode() != want["payload"]:
            return False, f"payload {m.payload[:60]!r}"
    return True, ""


# --- build -------------------------------------------------------------------


def placement(p):
    w = p.get("window")
    return hotty.Placement(
        cols=p["cols"],
        rows=p.get("rows", 0),
        window=hotty.Window(w["x"], w["y"], w["w"], w["h"]) if w else None,
        z=p.get("z", 0),
        press=p.get("press"),
        fit=p.get("fit"),
        hover=p.get("hover"),
        keep_cursor=p.get("keep_cursor", False),
    )


def build(b):
    a, o = b.get("args", {}), b.get("options", {})
    ro = {k: o[k] for k in ("n", "q") if k in o}
    name = b["build"]
    if name == "query":
        return hotty.query(a["n"], late=o.get("late", False))
    if name == "withdraw_late":
        return hotty.withdraw_late()
    if name == "doc":
        return hotty.doc(a["surface"], a["html"], detached=o.get("detached", False), scroll=o.get("scroll", 0), **ro)
    if name == "place":
        return hotty.place(a["surface"], placement(a["placement"]), **ro)
    if name == "place_at":
        return hotty.place_at(a["surface"], a["x"], a["y"], placement(a["placement"]), **ro)
    if name == "delta":
        ops = [hotty.Op(o["op"], o.get("target", ""), o.get("key", ""), o.get("value", "")) for o in a["ops"]]
        return hotty.delta(a["surface"], *ops, **ro)
    if name == "sync":
        return hotty.sync(*(build(c) for c in a["commands"]))
    fn = {
        "hide": lambda: hotty.hide(a["surface"], **ro),
        "set_text": lambda: hotty.set_text(a["surface"], a["target"], a["text"], **ro),
        "set_var": lambda: hotty.set_var(a["surface"], a["target"], a["name"], a["value"], **ro),
        "set_attr": lambda: hotty.set_attr(a["surface"], a["target"], a["name"], a["value"], **ro),
        "remove_attr": lambda: hotty.remove_attr(a["surface"], a["target"], a["name"], **ro),
        "morph_to": lambda: hotty.morph_to(a["surface"], a["target"], a["html"], **ro),
        "reveal": lambda: hotty.reveal(a["surface"], a["target"], a.get("where", ""), **ro),
        "res": lambda: hotty.res(a["id"], a["mime"], a["data"], **ro),
        "del_res": lambda: hotty.del_res(a["id"], **ro),
        "del": lambda: hotty.delete(a["surface"], **ro),
        "del_all": lambda: hotty.del_all(**ro),
        "detach": lambda: hotty.detach(a["surface"], **ro),
        "focus": lambda: hotty.focus(a["surface"], a.get("target", ""), **ro),
        "blur": lambda: hotty.blur(a["surface"], **ro),
        "edit": lambda: hotty.edit(a.get("names", []), **ro),
        "menu": lambda: hotty.menu(menu_tree(a["menu"]) if "menu" in a else None, **ro),
        "menu_show": lambda: hotty.menu_show(a.get("keys", []), **ro),
        "menu_hide": lambda: hotty.menu_hide(**ro),
    }[name]
    return fn()


def menu_item(i):
    return hotty.MenuItem(i.get("key", ""), i.get("label", ""), i.get("name", ""), i.get("enabled", True),
                          [menu_item(c) for c in i.get("items", [])])


def menu_tree(m):
    return hotty.MenuTree(m.get("label", ""), [menu_item(i) for i in m.get("items", [])])


def payload_of(seg):
    """A command's payload as a vector gives it: text, or payload_b64."""
    if "payload_b64" in seg:
        return base64.b64decode(seg["payload_b64"])
    return seg.get("payload", "").encode()


def body_matches(cmd):
    """A build vector's body, as JSON, is what its payload_b64 holds."""
    return hotty.unpack(base64.b64decode(cmd["payload_b64"])) == cmd["body"]


def run_build(v):
    got = []
    dec = hotty.Decoder()
    for kind, b in osc_segments(build(v)):
        if kind == "raw":
            got.append({"raw": b})
            continue
        result, m = dec.feed(b)
        if result != hotty.COMPLETE:
            return False, f"a command did not decode: {result}"
        got.append({"cmd": {"control": m.control, "payload": bytes(m.payload)}})
    want = []
    for seg in v["out"]:
        if "cmd" in seg:
            want.append({"cmd": {"control": seg["cmd"]["control"], "payload": payload_of(seg["cmd"])}})
            if "body" in seg["cmd"] and not body_matches(seg["cmd"]):
                return False, "body and payload_b64 disagree"
        else:
            want.append(seg)
    return got == want, f"got {got}"


# --- encode ------------------------------------------------------------------


def run_encode(v):
    payload = base64.b64decode(v["payload_b64"]) if "payload_b64" in v else v["payload"].encode()
    out = hotty.encode([tuple(p) for p in v["control"]], payload)
    if "bytes" in v and out != v["bytes"]:
        return False, f"bytes {out[:120]!r}"
    seqs = [b for k, b in osc_segments(out) if k == "osc"]
    if "chunks" in v:
        got = []
        for s in seqs:
            inner = s.decode()[len("\x1b]7279;") : -2]
            ctl, _, b64 = inner.partition(";")
            got.append({"control": ctl, "len": len(b64)})
        if got != v["chunks"]:
            return False, f"chunks {got}"
    dec = hotty.Decoder()
    results = [dec.feed(s) for s in seqs]
    if not results or results[-1][0] != hotty.COMPLETE:
        return False, "does not decode"
    m = results[-1][1]
    if m.payload != payload:
        return False, "payload differs after the round trip"
    if list(m.control) != [k for k, _ in v["control"] if k not in ("m", "o")]:
        return False, f"control keys {list(m.control)}"
    return True, ""


# --- decode ------------------------------------------------------------------


def num_eq(a, b):
    return a == b or (isinstance(a, (int, float)) and isinstance(b, (int, float)) and float(a) == float(b))


def reply_view(r):
    return {"ok": r.ok, "re": r.re, "n": r.n, "surface": r.surface, "cols": r.cols, "rows": r.rows, "code": r.code, "detail": r.detail, "op": r.op}


def event_view(e):
    link = e.link()
    drag = e.drag()
    hover = e.hover()
    area = e.area()
    view = e.view()
    cmd = e.command()
    return {
        "command": {"name": cmd.name, "key": cmd.key, "text": cmd.text, "has_text": cmd.has_text} if cmd else None,
        "surface": e.surface,
        "kind": e.kind,
        "target": e.target,
        "value": e.value(),
        "checked": e.checked(),
        "fields": [list(p) for p in e.fields()] if e.fields() is not None else None,
        "mods": e.mods(),
        "link": {"href": link[0], "url": link[1]} if link else None,
        "fit_rows": e.fit_rows(),
        "drag": {"c": drag.c, "r": drag.r, "x": drag.x, "y": drag.y, "tx": drag.tx, "ty": drag.ty} if drag else None,
        "hover": {"c": hover.c, "r": hover.r, "out": hover.out} if hover else None,
        "area": {"c": area.c, "r": area.r, "w": area.w, "h": area.h} if area else None,
        "count": e.count(),
        "view": {
            "areas": {k: {"c": a.c, "r": a.r, "w": a.w, "h": a.h} for k, a in view.areas.items()},
            "at_end": view.at_end,
        }
        if view
        else None,
    }


def caps_view(c, want):
    return {
        "v": c.v,
        "cell_css": {"w": c.cell_css.w, "h": c.cell_css.h} if c.cell_css else None,
        "scale": c.scale,
        "scheme": c.scheme,
        "mod": c.mod,
        "features": c.features,
        "limits": c.limits,
        "net": c.net,
        "edit": c.edit,
        "host": c.host,
        "version": c.version,
        "light": c.light(),
        "has": {f: c.has(f) for f in want.get("has", {})},
    }


def match(got, want, path):
    for k, w in want.items():
        g = got.get(k)
        if k == "areas" and path.endswith(".view"):
            # Compared whole (conformance/README.md, Decode).
            if g != w:
                return False, f"{path}.{k} = {g!r}, want {w!r}"
        elif isinstance(w, dict) and isinstance(g, dict):
            ok, why = match(g, w, f"{path}.{k}")
            if not ok:
                return ok, why
        elif not num_eq(g, w):
            return False, f"{path}.{k} = {g!r}, want {w!r}"
    return True, ""


def run_decode(v):
    dec = hotty.Decoder(v.get("max", 0))
    results, msgs = [], []
    for s in v["seqs"]:
        result, m = dec.feed(s.encode())
        results.append(result)
        if result == hotty.COMPLETE:
            msgs.append(m)
    if results != v["results"]:
        return False, f"results {results}"
    if dec.invalid != v["invalid"]:
        return False, f"invalid {dec.invalid}, want {v['invalid']}"
    if len(msgs) != len(v["messages"]):
        return False, f"{len(msgs)} messages"
    for m, want in zip(msgs, v["messages"]):
        if m.control != want["control"]:
            return False, f"control {m.control}"
        if "reply" in want:
            r = m.reply()
            if r is None:
                return False, "not a reply"
            ok, why = match(reply_view(r), want["reply"], "reply")
            if not ok:
                return ok, why
        if "event" in want:
            e = m.event()
            if e is None:
                return False, "not an event"
            ok, why = match(event_view(e), want["event"], "event")
            if not ok:
                return ok, why
            if "changed" in want:
                ch = e.changed()
                if ch is None:
                    return False, "no changed caps"
                if set(ch.raw) != set(want["changed"]["fields"]):
                    return False, f"changed fields {sorted(ch.raw)}"
                fields = {k: x for k, x in want["changed"].items() if k != "fields"}
                ok, why = match(caps_view(ch, fields), fields, "changed")
                if not ok:
                    return ok, why
        if "caps" in want:
            c = m.reply().caps() if m.reply() else None
            if want["caps"] is None:
                if c is not None:
                    return False, "caps, want none"
                continue
            if c is None:
                return False, "no caps"
            ok, why = match(caps_view(c, want["caps"]), want["caps"], "caps")
            if not ok:
                return ok, why
    return True, ""


# --- scan --------------------------------------------------------------------


def scan_once(v, data, cuts):
    sc = hotty.Scanner(da1="scanner.da1" in v.get("requires", []))
    segs, prev = [], 0
    for c in cuts + [len(data)]:
        segs += sc.feed(data[prev:c])
        prev = c
    held = sc.holding
    # A sequence held is in progress; the start of a segment is not.
    if held and sc.in_sequence != held.startswith(b"\x1b]7279;"):
        held = b"in_sequence is " + str(sc.in_sequence).encode() + b" holding " + held
    flushed = sc.flush()
    return hotty._merge(segs), held, flushed, sc.invalid


def run_scan(v):
    data = v["stream"].encode()
    want = [(list(s)[0], list(s.values())[0].encode()) for s in v["segments"]]
    want_flush = [(list(s)[0], list(s.values())[0].encode()) for s in v.get("flush", [])]
    want_held = v.get("held", "").encode()
    # Every offset, and byte by byte; a long stream is cut at every offset
    # near its ends and at a stride between.
    offsets = range(1, len(data))
    if len(data) > 512:
        offsets = sorted({*range(1, 64), *range(len(data) - 64, len(data)), *range(64, len(data) - 64, 4999)})
    splits = [[]] + [[i] for i in offsets] + [list(range(1, len(data)))]
    for cuts in splits:
        segs, held, flushed, invalid = scan_once(v, data, cuts)
        where = f"cut at {cuts[:3]}{'…' if len(cuts) > 3 else ''}"
        if segs != want:
            return False, f"{where}: segments {segs[:4]}"
        if held != want_held:
            return False, f"{where}: held {held[:40]!r}"
        if flushed != want_flush:
            return False, f"{where}: flush {flushed}"
        if invalid != v.get("invalid", 0):
            return False, f"{where}: invalid {invalid}"
    return True, ""


# --- detect ------------------------------------------------------------------


def run_detect(v):
    det = hotty.Detector(v.get("n", 1), late=v.get("late", False))
    dec = hotty.Decoder()
    for i, st in enumerate(v["steps"]):
        at = st["at"]
        took = None
        if st.get("start"):
            det.start(at)
        elif st.get("da1"):
            took = det.da1(at)
        elif "osc" in st:
            result, m = dec.feed(st["osc"].encode())
            r = m.reply() if result == hotty.COMPLETE else None
            took = det.reply(r, at) if r is not None else False
        elif st.get("tick"):
            det.tick(at)
        elif st.get("end"):
            det.end(at)
        got = {"took": took, "state": det.state, "decided": det.decided, "done": det.done, "deadline": det.deadline}
        for k in ("took", "state", "decided", "done", "deadline"):
            if k in st and got[k] != st[k]:
                return False, f"step {i} (at {at}): {k} = {got[k]!r}, want {st[k]!r}"
    if "caps" in v:
        c = det.caps
        if v["caps"] is None:
            return (True, "") if c is None else (False, f"caps {c!r}, want none")
        if c is None:
            return False, "no caps"
        ok, why = match({"v": c.v}, v["caps"], "caps")
        if not ok:
            return ok, why
    return True, ""


# --- keys, keymap, edit --------------------------------------------------------


def run_keys(v):
    if "input" in v:
        got = hotty.decode_keys(v["input"])
        return got == v["keys"], f"{got!r}, want {v['keys']!r}"
    if "text" in v:
        got = hotty.key_text(v["key"])
        return got == v["text"], f"{got!r}, want {v['text']!r}"
    if "mod" in v:
        got = hotty.read_key(hotty.Platform(v["mod"]), v["key"])
        return got == v["canon"], f"{got!r}, want {v['canon']!r}"
    got = hotty.parse_key(v["key"])
    return got == v["canon"], f"{got!r}, want {v['canon']!r}"


def platform(v):
    p = v.get("platform", {})
    return hotty.Platform(p.get("mod", "ctrl"), p.get("edit"))


def run_keymap(v):
    if "program" in v or "scroll" in v or "prefix" in v:
        m = hotty.parse_keymap(platform(v), " ".join(v["keys"]))
        for key, want in v.get("program", {}).items():
            got = m.program(key)
            if got != want:
                return False, f"{key!r}: program {got!r}, want {want!r}"
        for key, want in v.get("prefix", {}).items():
            got = m.prefix(key)
            if got != want:
                return False, f"{key!r}: prefix {got!r}, want {want!r}"
        for key, want in v.get("scroll", {}).items():
            got = m.scroll(key)
            if got != want:
                return False, f"{key!r}: scroll {got!r}, want {want!r}"
        return True, ""
    if "lookup" not in v:
        got = hotty.parse_keymap(platform(v), v["parse"] if "parse" in v else hotty.TERMINAL_KEYS).format()
        return got == v["format"], f"{got!r}, want {v['format']!r}"
    layers = ([hotty.TERMINAL_KEYS] if v.get("terminal_keys") else []) + v["keys"]
    m = hotty.resolve(platform(v), v["multiline"], *layers)
    for key, want in v["lookup"].items():
        got = m.lookup(key)
        if got != want:
            return False, f"{key!r}: {got!r}, want {want!r}"
    for key, want in v.get("selects", {}).items():
        got = m.selects(key)
        if got != want:
            return False, f"{key!r}: selects {got!r}, want {want!r}"
    for key, want in v.get("binds", {}).items():
        got = m.binds(key)
        if got != want:
            return False, f"{key!r}: binds {got!r}, want {want!r}"
    return True, ""


def run_edit(v):
    f = v["field"]
    fld = hotty.Field(f["value"], f["caret"], f.get("multiline", False), f.get("password", False), f.get("rows", 1),
                      f.get("anchor"))
    for i, st in enumerate(v["steps"]):
        changed = False
        if "do" in st:
            changed = fld.do(st["do"])
        elif "extend" in st:
            changed = fld.extend(st["extend"])
        elif "select" in st:
            fld.select(*st["select"])
        else:
            changed = fld.type(st["type"])
        # Nothing selected is an anchor at the caret (SDK.md §4.6).
        anchor = fld.caret if fld.anchor is None else fld.anchor
        got = {"value": fld.value, "caret": fld.caret, "anchor": anchor, "changed": changed}
        for k in ("value", "caret", "anchor", "changed"):
            if k in st and got[k] != st[k]:
                what = st.get("do", st.get("extend", st.get("select", st.get("type"))))
                return False, f"step {i} ({what!r}): {k} {got[k]!r}, want {st[k]!r}"
    return True, ""


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "..", "..", "conformance", "vectors.json")
    data = json.load(open(path))
    if data["version"] != hotty.VERSION:
        print(f"the vectors are for {data['version']}, this client for {hotty.VERSION}")
        return 1
    skipped = 0
    for section, run in (("wire", run_wire), ("build", run_build), ("encode", run_encode), ("decode", run_decode), ("scan", run_scan), ("detect", run_detect),
                         ("keys", run_keys), ("keymap", run_keymap), ("edit", run_edit)):
        for v in data.get(section, []):
            if not runs(v):
                skipped += 1
                continue
            try:
                ok, why = run(v)
            except Exception as e:  # noqa: BLE001
                ok, why = False, f"{type(e).__name__}: {e}"
            check(section, v["name"], ok, why)
    for section, (ok, bad) in counts.items():
        print(f"{section:7} {ok} passed" + (f", {bad} failed" if bad else ""))
    if skipped:
        print(f"skipped {skipped} (requires)")
    for f in failures:
        print("FAIL", f)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
