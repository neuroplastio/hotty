# A synthetic keymap's characters arrive as Escape under kitty flag 8

Seen while preparing gov R-23's blind pairs, 2026-10-30. Low priority:
upstream behaviour, seen only with synthetic input so far.

## What happens

A program that pushes kitty keyboard flag 8 (report all keys as escape
codes; plx does, for its panes) gets **Escape** for a character typed by
an input tool whose keymap puts characters on keycodes that are physical
keys elsewhere. `wtype` is one: its per-character keymap starts at
keycode 9, which is evdev's Escape, so the first character it types sits
there. Ghostty encodes the key by its physical key under flag 8, finds
Escape, and sends `CSI 27 u` (a pane that asked for no flags, behind a
multiplexer that translates, reads a bare `\x1b`).

Any input with a keymap like wtype's can meet the same: an on-screen
keyboard, remote input, a virtual keyboard that builds its keymap on
the fly. A real keyboard doesn't: shift+r reaches a hotty field as `R`.

## Seen

In a plain pane (a raw-input logger) of a throwaway plx, keys typed with
`wtype` into the window on a headless sway:

| wtype | the pane read |
| --- | --- |
| `A` | `\x1b` |
| `-M shift a -m shift` | `a` (lowercase: unexplained, likely wtype's single-level keymap) |
| `b` | `b` |

The same in hottyterm (26.10.27, on Ghostty 1.4.1-dev) and in stock
Ghostty 1.4.0 run with `--config-default-files=false`. So it is
Ghostty's encoder, not a patch of ours.

## What would tell more

- A virtual keyboard with a real keymap (shift levels, keycodes off the
  physical keys' range) to separate wtype's keymap from Ghostty's
  fallback, and to explain the lowercase `a`.
- Whether Ghostty should prefer the keysym's text over the physical key
  for a non-functional keysym under flag 8. That is upstream's call;
  never raised there by us (hottyterm's AGENTS.md).
- A hottyterm mod could prefer the keysym's text under flag 8, if a
  real (non-synthetic) input ever hits it.

