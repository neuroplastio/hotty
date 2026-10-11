# Changes

## 0.2

A draft, as every 0.x is. It breaks 0.1 (SPEC.md §15): programs and hosts
move to it together. It ships with hottyterm's release that pins hotty-blitz
a70065f and with xterm-addon-hotty 0.1.0-next.8.

### What changed

- **A host's bodies are msgpack** (SPEC.md §3.3): the capabilities, an
  error's body, and every event's detail are one msgpack map, with nothing
  after it, nested at most 32 deep. What a program sends is unchanged: text
  and bytes.
- **Each field has a type**, and keeps it from 0.2 on: `int`, `float`, `str`,
  `bool`, arrays and maps of them. A float is sent as a float even when
  whole. A known field of another type fails the body; unknown fields are
  skipped.
- **A body holds nothing a host does not send**, anywhere in it: no nil,
  keys that are strings and each given once, UTF-8 strings, ints within
  2^53 − 1 of zero, and timestamps msgpack defines. A body that breaks one
  does not decode, and the message stands without it (SDK.md §3.9).
- **A query lists the versions the program speaks** (SPEC.md §4):
  `a=q:n=1:v=0.2`. A host answers in the highest it shares, or with the new
  error `EVERSION`, its detail the versions it speaks. A program takes as a
  host only an answer whose capabilities decode and name a version it
  speaks. A 0.1 program on a 0.2 host, and a 0.2 program on a 0.1 host,
  each find no host and draw in cells.

### Added within 0.2

What follows came after the first 0.2 hosts, and keeps the version: a host
that lacks it says so in its capabilities.

- **`reveal`** (SPEC.md §6.1), a delta that scrolls an element into view:
  its top to the top with `start`, its bottom to the bottom with `end`,
  and by as little as it takes with neither. It moves no focus. A program
  asks `Supports(c, "reveal")`.
- **`view`** (SPEC.md §9.5), an event: the elements with `data-on~=view`
  and an id that are in view, each with its area, and whether the
  document shows its end. A host sends it once the document is laid out,
  then on each change, once a scroll comes to rest. A program asks
  `Views(c)`.

Each SDK has the builder `Reveal`, the event's `View` (`Areas` and `AtEnd`,
from `in` and `end`), and `Views`.

### Porting

A port that compiles can still be wrong. SDK.md Appendix C lists what ports
got wrong; the two that cost most:

- **A clicked link is `Link`, not a field.** 0.1's hotty-go read any detail
  through `Event.Fields()`, so programs found a link's href as
  `Fields()["href"]`. In 0.2 `Fields` holds a submit's fields only, and a
  link click carries `Link` (`Href`, `URL`). After a mechanical port, link
  clicks silently go nowhere.
- **Read the event's fields, never its detail.** Code that unmarshals
  `ev.Detail` as JSON reads zero values from msgpack: a checkbox that is
  always unchecked. Use `Checked`, `Value` and the rest.

And a test that plays the host answers with msgpack capabilities naming
0.2 (hotty-go: `hottytest.Body`, or `hottytest.Host`), or the program under
test falls back to text.

### In each SDK

- **hotty-go** (Go): the wire types are data, with functions beside them.
  `m.Reply()` is `hotty.ReplyOf(m)`, `m.Event()` is `hotty.EventOf(m)`,
  `r.Caps()` is the field `r.Caps` (nil when none) or `hotty.CapsOf(body)`,
  `r.Err()` is `hotty.Err(r)`, `c.Supports(op)` is `hotty.Supports(c, op)`,
  and an event's accessors (`Value()`, `Checked()`, `Link()`, `Size()`,
  `FitRows()`, `Drag()`, `Hover()`, `Area()`, `Fields()`) are its fields.
  A host or relay answers a query with `hotty.ReplyQuery`.
- **hotty-ts** (TypeScript) and the **Python client**: the reader keeps an
  int apart from a float; `query()` sends `v`.
- **hotty-lua**: `hotty.msgpack.decode(s)` returns `value, kinds`, where
  `kinds[t][k]` tells a float, bin, array, time or extension apart from
  what Lua alone cannot.
- **hotty-blitz** and **xterm-addon-hotty**, the hosts: they send msgpack
  and answer queries by version.
