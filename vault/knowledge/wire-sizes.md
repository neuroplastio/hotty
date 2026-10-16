# What HOTTY costs on the wire

Measured with the Python client (`clients/python`) by
[`wire_sizes.py`](wire_sizes.py): 0.2 on 2026-10-14, 0.3 on 2026-10-16
after the fold. Bytes are whole sequences: `ESC ] 7279 ;`, the control,
the base64 payload and `ST`.

| message | 0.2 | 0.3 |
| --- | --- | --- |
| one `var` delta (`--p: 42`) | 49 | 68 |
| one `text` delta (`12:00:01`) | 56 | 76 |
| 5 `var` changes, one frame | 245 | 196 |
| 15 `var` changes, one frame | 755 | 188 |
| 50 `var` changes, one frame | 2,540 | 360 |
| `PlaceAt` with `z` and hover, per surface per frame | 61 | 57 first, 53 after |
| `click` with its `area` | 62 | 62 |
| `drag` | 64 | 56 |
| `view` with 20 elements in view | 582 | 579 |
| `corpus/04-table.html` (1,131 B) morphed whole for one changed cell | 930 | 781 |
| hotty-a2ui's `kit.css` (about 50 KB) as a resource | 26,858 (zlib 1) | 17,704 (zlib 6) |

What the numbers say:
- **The bytes go from the program to the host.** Events come at the user's
  pace and are a few dozen bytes; `view` is the largest, and comes once a
  scroll rests.
- **A frame is one delta.** In 0.2 every change was a message of its own,
  mostly envelope, and zlib could not see across them. In 0.3 a frame's
  changes to a surface are one list of ops: 15 changes cost a quarter of
  what they did, and 50 a seventh. A lone change costs more than it
  did (68 B, not 49), since an op is a map keyed by name (gov P-3).
- **Under 256 bytes nothing is compressed** (SDK.md §3.3): 5 changes (196 B)
  cost more than 15 (188 B), which zlib folds.
- **A whole-tree morph still sends the tree.** One changed cell is a `text`
  op, or 781 B as a morph of the whole table: SDK.md §2.9 says to diff
  first.
- **Compression level matters for large payloads.** At zlib's default
  level `kit.css` is a third smaller than at level 1, for about a
  millisecond.

The fold these led to is [`../tasks/fold-0.3.md`](../tasks/fold-0.3.md).
