# What HOTTY 0.2 costs on the wire

Measured 2026-10-14 with the Python client (`clients/python`), by
[`wire_sizes.py`](wire_sizes.py). Bytes are whole sequences: `ESC ] 7279 ;`,
the control, the base64 payload and `ST`.

| message | bytes |
| --- | --- |
| one `var` delta (`--p: 42`) | 49 |
| one `text` delta (`12:00:01`) | 56 |
| 15 `var` deltas, one frame | 755 |
| 50 `var` deltas, one frame | 2,540 |
| `PlaceAt` with `z` and hover, per surface per frame | 61 |
| `click` with its `area` | 62 |
| `drag` | 64 |
| `view` with 20 elements in view | 582 |
| `corpus/04-table.html` (1,131 B) morphed whole for one changed cell | 930 |
| hotty-a2ui's `kit.css` (50,347 B) as a resource, zlib level 1 | 26,858 |

What the numbers say:
- **The bytes go from the program to the host.** Events come at the user's
  pace and are a few dozen bytes; `view` is the largest, and comes once a
  scroll rests.
- **Small deltas are mostly envelope.** `--p: 42` is 2 bytes of change in 49.
  A frame of many is that many envelopes, and zlib cannot see across them.
- **A whole-tree morph sends the tree.** One changed cell is a 56 B `text`
  delta, or 930 B as a morph of the whole table.
- **Compression level matters for large payloads.** `kit.css` is 26,708 B of
  base64 at level 1, 17,452 B at level 6 and 17,384 B at level 9.

The proposals these lead to are in [`../tasks/fold-0.3.md`](../tasks/fold-0.3.md)
(FOLD-01, FOLD-10, FOLD-11). One list of 15 deltas would be 184 B, and of 50,
356 B; a list of one is 64 B.
