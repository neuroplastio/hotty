# Surface scaling from the terminal font: decision draft

Status: option 2 chosen by the maintainer on 2026-11-08. The kit and plx
size their surfaces relative to the terminal font and cells. The spec and
hosts retain their current model.

## Evidence and limits

An isolated headless sway at 2874×1845 device pixels and scale 1.6 ran
installed hottyterm 26.11.07-dev.07080c8 with plx 26.11.08-dev.58e349a
at 9, 12 and 13 points, with the same nav tool in dark mode. At 9, the nav
switches and tree rows are visibly compressed; at 12 and 13 they have
more vertical room. Terminal monospace text grows with the setting, while
the nav labels change much less. The supplied 13-point monospace samples
show hottyterm and Ghostty looking nearly identical in glyph size and line
spacing, and Zed looking smaller. These are visual comparisons, not
calibrated glyph measurements. The screenshots and terminal log confirm
that the issue is visible without reproducing a populated agents list.

The current contract makes a settings font change resize the CSS cell and
relayout the document, whereas zoom changes scale and keeps layout
(`SPEC.md` §5.3, §8, and rationale at line 2692). Blitz implements this in
`hotty-blitz/crates/hotty-blitz/src/style.rs:12`: cell dimensions are
physical dimensions divided by scale; its root font and cell variables are
CSS pixels (lines 33–42). In `hotty-surf/surfui/surf.css:349–361`, compact
rows follow the cell height but gaps are 4px and type is 14px. The kit
also has fixed icon widths and font sizes (lines 448–460). plx's actual
surface CSS mixes a cell-based tab height with fixed padding and type
(`plx/internal/tui/hotdecor/decor.css:248–261`), and has fixed pane header
icon and label sizes (lines 446–476). Thus these sizes do not all follow
the font setting; the precise contribution to the pictured crowding needs
the controlled shots. This evidence does not establish a separate Blitz
layout defect.

On Linux Ghostty specifies font size in points (`src/config/Config.zig:255`)
and converts points using DPI / 72 (`src/font/face.zig:47–57`); its base
DPI is 96 (line 29) and the surface multiplies it by content scale
(`src/Surface.zig:510–525`). The isolated hottyterm logged scale 1.6 and 154 DPI. At that DPI and no
extra text scaling: 11pt is about 23.53 device px or 14.71 logical px;
13pt is about 27.81 device px or 17.38 logical px. At exact 96 DPI these
are 14.67 and 17.33 logical px. Font rasterization, rounding, text scaling,
and font metrics affect the visible glyphs. This predicts why a point
setting looks larger than a pixel setting, but Zed's units and this
machine's actual text scaling still require verification. The two supplied
terminal images support hottyterm matching Ghostty at 13; they do not
prove exact pixel parity or diagnose 11 against 13. Ghostty's font unit is
not ours to change.

## Options

1. **Host maps configured size to zoom from a reference.** Preserve the
   reference CSS cell and root font; scale all document pixels, including
   fixed images and spacing. This matches the existing zoom model but
   changes the settings-font contract and its rationale, caps/fit/resize
   semantics, family changes and reference-size selection. Both Blitz and
   the xterm.js host (`xterm-addon-hotty/src/hostcss.ts:78–84`) need
   consistent metrics and tests; SDKs and applications relying on cell
   metrics or events need review. A breaking protocol change needs a new
   spec minor and matching implementations (P-5). Existing kit goldens and
   the Blitz gate must be rerun; verify hairlines and cross-host rendering.
2. **Relative dimensions in the kit and plx.** Keep the host/spec model;
   convert typography, gaps, padding, icons and relevant radii to rem, em
   or cells, retaining device-pixel hairlines where intended. Fixed-pixel
   author surfaces outside those projects still do not scale as a unit.
   Requires auditing density semantics, plx's own CSS, kit goldens and the
   Blitz gate; SDKs and other hosts keep their current contract. Reference
   appearance and both light/dark and narrow/wide layouts need review.
3. **Both.** Uniform host scaling covers third-party pixel surfaces, while
   relative kit units retain meaningful adaptation to font metrics. Costs
   and compatibility risks of both apply; avoid double scaling and define
   which changes should cause relayout.

**Choice:** option 2. It
addresses the identified mixed-unit surfaces without changing a protocol
contract for every author and host. Option 1 better satisfies a general
promise that all authored pixels scale, if that is the desired contract.

## Open questions

- Is proportional scaling required for every existing surface, including
  fixed-pixel art? Lean: decide this explicitly before changing the spec.
- Should a new font family relayout even if a size setting acts as zoom?
  Lean: yes, because its cell metrics may change independently.
- What is the reference and how do caps, fit and cell geometry behave?
  Lean: preserve the present contract unless a versioned replacement has
  cross-host tests and a clear migration.
- Which pixel dimensions are deliberate physical hairlines? Lean: keep
  `--hotty-px` for those and check at fractional scale.
- Does the chosen fix preserve legibility and proportions at each size?
  Lean: compare the same nav surface in dark and light at both widths
  before and after implementation, with the maintainer reviewing the look.
