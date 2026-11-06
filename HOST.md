---
group: Reference
order: 25
nav: Host design
description: what a host provides beyond the protocol, so that hosts agree
path: host-design
---

# hotty hosts

    Version:  0.7, with SPEC.md 0.7
    Status:   Draft. Guidance for hosts, not part of the protocol.
    Licence:  CC BY 4.0

## Abstract

A **host** draws a program's surfaces (SPEC.md §1). SPEC.md says what a
host must do on the wire. This document says what a host should provide
beyond it, so that a document looks the same on every host that follows
it, and a user finds the same gestures: the font a host ships, and the
gestures it calls a secondary press.

Nothing here is on the wire. A host doesn't report it, and a program can't
ask for it. A document may use what it describes, but it can't count on it
(§2.5), and a host that doesn't follow this document is still a host.

## Contents

1. Introduction
2. Fonts
3. The secondary press
4. Speaking 0.6 as well
5. Implementations

Appendix: A. Rationale

---

## 1. Introduction

[SPEC.md](SPEC.md) defines the wire, and [SDK.md](SDK.md) how a library
presents it to a program. This document is for whoever writes a host: a
terminal, a browser addon, a renderer. Where it and SPEC.md disagree,
SPEC.md is right and this document is wrong.

The key words **MUST**, **MUST NOT**, **SHOULD**, **SHOULD NOT** and **MAY**
are to be interpreted as in SPEC.md §2. A MUST here binds a host that
follows this document, not every host. Licence terms bind every host
that ships the font.

## 2. Fonts

### 2.1 The font

A host **SHOULD** ship one font: **AdwaitaMono Nerd Font Propo**, from Nerd
Fonts v3.5.1, in its Regular (400), Bold (700), Italic (400) and Bold Italic
(700) faces.

- **Adwaita Mono** is GNOME's monospace typeface, built on Iosevka. It is
  licensed under the SIL Open Font License 1.1, with no reserved font
  names.
- **Nerd Fonts** adds the icon sets that terminal programs draw with:
  - Material Design Icons, Font Awesome, Devicons, Codicons and Octicons;
  - Powerline's symbols and the rest of its sets (§2.4).
- **Propo** is the variant whose icons keep their own width. A host lays out
  text as HTML, not on the terminal's grid, so an icon takes the room it
  needs. The plain variant gives an icon one cell's advance and draws it
  past it, over the next letter. The Mono variant shrinks it into one cell.

The family is named `"AdwaitaMono Nerd Font Propo"`, as Nerd Fonts names it.
A host **MUST NOT** rename it. A document that names the family gets it on
every host that follows this document.

Italic is the font's own, not Regular slanted by the engine, so it matches a
terminal that draws its cells in Adwaita Mono (§2.5). The other weights come
from the engine, which takes the nearest of the two.

### 2.2 Its place in the font lists

The font goes where a document's text reaches it without asking for it:

- **`monospace` and `ui-monospace`:** first. A document in monospace looks
  the same on every system.
- **Every other generic family** (`serif`, `sans-serif`, `system-ui`,
  `cursive`, `fantasy`, `ui-serif`, `ui-sans-serif`, `ui-rounded`): second,
  right after the system's own choice and before the families the system
  lists after it. A document's sans-serif stays the system's. What that
  font lacks, a Nerd Font icon or a symbol such as ⌘, comes from this
  font, and not from whichever font the system lists next (§A.4).
- `emoji`, `math` and `fangsong` keep the system's lists.
- **`--hotty-font`** (SPEC.md §8) is the terminal's font family, then this
  font, then `monospace`:

  ```css
  --hotty-font: "JetBrains Mono", "AdwaitaMono Nerd Font Propo", monospace;
  ```

  A host that already puts the font first in `monospace` **MAY** leave it
  out here, as the two lists then mean the same.

A browser can't change what a generic family means inside a page, so a
browser host does only the last step. There a document that names
`monospace` itself gets the browser's monospace font, and reaches this one
only through `--hotty-font` or by name.

### 2.3 Loading it

The font is about 1.35 MB per face as WOFF2, and about 4 MB per face
uncompressed.

- **A native host** **SHOULD** embed the WOFF2 faces and decode them once
  per process, off the thread that draws, before its first surface needs
  them. Decoding all four takes about 85 ms on four threads. Every surface
  then shares the decoded faces.
- **A browser host** **SHOULD** serve the faces as files, declare them with
  `@font-face` in the host stylesheet, and let the browser fetch each face
  the first time a surface draws text in it. The surface's CSP
  (SPEC.md §7.2) allows the font's URL in `font-src`; that is the host's
  own grant, not the document's. A document's network policy doesn't
  change it.

### 2.4 Licences

A host that ships the font **MUST** ship, beside it:

- **`OFL.txt`**: the font's licence, the SIL Open Font License 1.1, with its
  copyright lines.
- **`NOTICE.txt`**: the icon sets Nerd Fonts adds, each with its version,
  licence and source, followed by each licence's text. The sets carry MIT,
  Apache-2.0, CC BY 4.0, OFL-1.1 and the Unlicense. CC BY 4.0 (Codicons, Font
  Awesome's icons) requires the attribution this file gives.

A host that lists its third-party components **MUST** list the font there
too, with both texts. The OFL allows bundling the font with software that is
sold, but not selling the font on its own.

The icon sets include brand logos: Apple's, Microsoft Windows', and many
others. Their licences cover the drawings, not the trademarks. A host's own
interface, defaults, documentation and screenshots **SHOULD NOT** show a
brand's logo. A user who puts one in their own configuration takes that on
themselves.

### 2.5 What a program can count on

Nothing: a program can't tell from the capabilities (SPEC.md §4) whether
a host ships the font.

- **A document that draws Nerd Font icons** gets them on a host that
  follows this document, and boxes or another font's glyphs elsewhere. A
  program that shows icons **SHOULD** let its user switch them to text.
- **Cells are the terminal's.** The font plays no part in cells: the
  terminal draws them with its own fonts. hottyterm's default font is
  Adwaita Mono, the letters of this font, so until its user picks another,
  cells and surfaces look alike. Whether an icon shows in cells depends on
  the terminal. Ghostty embeds Symbols Nerd Font, and hottyterm with it.
  Elsewhere the user's font decides.

## 3. The secondary press

SPEC.md §9 defines a secondary press and the event it makes. Which gesture
a user makes for one is the platform's, and a host takes the ones its
platform calls so. Nothing here is on the wire: a program hears a `press`
with `button` 2, and can't tell which gesture made it.

| gesture | where it is a secondary press |
| --- | --- |
| the mouse's secondary button | everywhere |
| the primary button with Control held | macOS, where AppKit makes it a context click; `ctrl` is then left out of `mods` |
| a pen's barrel button | where the platform reports one |
| a touch held past the long-press time | everywhere, over an element that takes it (SPEC.md §9.1) |

How a toolkit reports them:
- **GTK:** a `GtkGestureClick` with button 3 (`GDK_BUTTON_SECONDARY`) for the
  mouse and the pen's barrel, and a `GtkGestureLongPress` for the touch.
- **AppKit:** `rightMouseDown`, and `menu(for:)` for a context click, which
  covers Control with the primary button. A pen's barrel button comes with
  `rightMouseDown` too.
- **A browser:** `pointerdown` with `button` 2 for a mouse and a pen's barrel
  button, which is also the DOM's number for `button`. The `contextmenu`
  event covers the rest: Control with the primary button on macOS, and a
  touch's long press. A host that takes the press from `pointerdown` calls
  `preventDefault` on the `contextmenu` that follows, so the browser's
  menu does not open over a press the surface took.

Shift and Alt come first (SPEC.md §9.2). With either held, the host
handles the press as one on the cells beneath the surface: the terminal's
own menu with Shift, and the program's mouse report with Alt.

In a 0.6 session (§4.1) Alt is all a 0.6 program could meet of this: see
there.

The keyboard's way to a menu is not the host's. `shift+f10` and the Menu key
reach the program as keys (SPEC.md §10.2), and a host adds nothing for them.

## 4. Speaking 0.6 as well

hotty's own stack, hosts and SDKs, speaks 0.6 along with 0.7. SPEC.md §15
lets a host speak several versions, and the rest is what the stack does
with it. A host that does not speak 0.6 answers a 0.6 program with
`EVERSION` (SPEC.md §4), and the program falls back.

### 4.1 A 0.6 session

- **A host that speaks 0.6 as well** answers a program that lists 0.6 and
  not 0.7 in 0.6, and speaks 0.6 to it from then on (SPEC.md §4). A query
  that lists both is answered in 0.7, the highest the two share.
- **One behaviour of 0.7 can reach a 0.6 program:** a press of the
  secondary button with Alt held. In 0.7 it is the program's, and with
  mouse reporting on the program hears `CSI < 10 ; <col> ; <row> M`
  (SPEC.md §9.2). In a 0.6 session it stays the terminal's, as 0.6's §9.2
  has it: not reported to the cells as `CSI < 10`.
- **Nothing else of the secondary press reaches a 0.6 session.** A 0.6
  document never asks for `secondary` in its `data-on`, so the host sends it
  no secondary `press`: a secondary press over its elements is the
  terminal's, as it was.
- **A 0.7 program on a 0.6 host** is answered in 0.6 and meets no
  secondary press; SDK.md §3.8 and §4.7 say what an SDK does.

## 5. Implementations

| host | how it ships the font | since |
| --- | --- | --- |
| hotty-blitz (hottyterm, `hotty run`) | embedded, decoded on a thread of its own when a host starts; first in `monospace`, second elsewhere | 0.5.1; Italic and Bold Italic 0.5.2 |
| xterm-addon-hotty | in the package's `fonts/`; the page serves it and passes its URL as the `fonts` option, and the addon adds it to `--hotty-font` and each surface's CSP | 0.5.1; Italic and Bold Italic 0.5.4 |

Both ship `OFL.txt` and `NOTICE.txt` beside the faces. hottyterm lists the
font in its third-party notices.

## Appendix A. Rationale

Informative.

### A.1 Why ship a font

Users rarely install a Nerd Font for an app. A program that draws an icon,
a key's symbol or a file type's logo then shows boxes, or a glyph from
whatever font the system falls back to, at its size and weight. With one
font shipped, a surface looks the same on every system: monospace text
lines up as the author saw it, and icons draw without asking.

### A.2 Why not in the spec

A font in SPEC.md would bind every host to ship it, and let a document
rely on it. The font is new, and how documents use it is still unknown.
It can move into SPEC.md later, as a guarantee or as a capability, once
hosts and programs have used it.

### A.3 Why this font

- **Nerd Fonts,** because terminal programs already draw with it: prompts,
  file trees, status lines. A surface draws the same icons the user's
  terminal does.
- **Adwaita Mono,** out of the families Nerd Fonts patches:
  - its licence: the OFL with no reserved font names, so the patched font
    may be shipped under Nerd Fonts' name;
  - its look: an even, readable monospace, on the GNOME desktop by default;
  - static faces of its own for Regular, Bold, Italic and Bold Italic,
    which is all a host needs, and the faces a terminal draws its cells
    with when it uses Adwaita Mono.

  Fonts whose licences limit where they may be used (Apple's SF fonts and
  SF Symbols, Microsoft's Segoe) were left out, and so was Meslo, which is
  made from Apple's Menlo.
- **One font, not two.** A proportional font for the rest (Inter, say) would
  double the size and add no icons: the system's sans-serif serves text.

### A.4 Why second, and not last

Fontconfig lists many families for each generic one: on a typical Linux
desktop, `sans-serif` names over a hundred, and the user's installed Nerd
Fonts are often among the first. With this font last, an icon in sans-serif
text came from the first of those that had it. A plain Nerd Font gives an
icon one cell's advance and draws it wider, so it covered the next letter.
Second, right after the system's choice, the icon comes from the Propo
faces unless the system's own sans-serif has it.

A side effect: a symbol the system's sans-serif lacks, such as ⌘ ⌥ ⇧ in
Noto Sans, draws from this font, as Adwaita Mono draws it.

### A.5 Why WOFF2

WOFF2 is a third of the size uncompressed faces take in a binary, and it is
what a browser fetches anyway. A native host pays for it with about 85 ms of
decoding, once per process and off the drawing thread.
