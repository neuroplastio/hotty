---
group: Reference
order: 25
nav: Host design
description: what a host provides beyond the protocol, so that hosts agree
path: host-design
---

# hotty hosts

    Version:  0.9, with SPEC.md 0.9
    Status:   Draft. Guidance for hosts, not part of the protocol.
    Licence:  CC BY 4.0

## Abstract

A **host** draws a program's surfaces (SPEC.md §1). SPEC.md says what a
host must do on the wire. This document says what a host should provide
beyond it, so that a document looks the same on every host that follows
it, and a user finds the same gestures: the font a host ships, and the
gestures it makes a context menu's, and how it numbers and takes a mouse's
other buttons.

Nothing here is on the wire. A host doesn't report it, and a program can't
ask for it. A document may use what it describes, but it can't count on it
(§2.5), and a host that doesn't follow this document is still a host.

## Contents

1. Introduction
2. Fonts
3. Buttons
4. Reduced motion
5. Speaking 0.8 as well
6. Implementations

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

## 3. Buttons

### 3.1 The context menu

SPEC.md §9 defines `contextmenu` and the gestures that make it. Which
gesture a user makes for one is the platform's, and a host takes the ones
its platform calls so. Nothing here is on the wire: a program hears a
`contextmenu`, and can't tell which gesture made it.

| gesture | where it makes `contextmenu` |
| --- | --- |
| the mouse's secondary button | everywhere, unless an element with `rightbutton` takes the button (SPEC.md §9) |
| the primary button with Control held | macOS, where AppKit makes it a context click; `ctrl` is then left out of `mods`, so that it reads as the secondary button's does, and no `press` or `click` comes of it |
| a pen's barrel button | where the platform reports one |
| a touch held past the long-press time | everywhere, over an element that takes it (SPEC.md §9.1) |
| the menu key, `context_menu` or `shift+f10` | only where the host reports it (below) |

**When** is the platform's too: on the press on Linux and macOS, and on
the release on Windows, where native menus and browsers open theirs then.
A host on Windows finds the element at the press, the nearest with
`contextmenu` or `rightbutton`, where that one has `contextmenu` and not
`rightbutton` (SPEC.md §9), holds the pointer and hover from then, as for a press it
takes, and reports for that element at the release, with the release's
cell. A browser host records the element at the secondary `pointerdown`,
calls `setPointerCapture`, and reports the browser's later `contextmenu`
for it, wherever the browser aims that event.

How a toolkit reports them:
- **GTK:** a `GtkGestureClick` with button 3 (`GDK_BUTTON_SECONDARY`) for the
  mouse and the pen's barrel, and a `GtkGestureLongPress` for the touch.
- **AppKit:** `rightMouseDown`, and `menu(for:)` for a context click, which
  covers Control with the primary button. A pen's barrel button comes with
  `rightMouseDown` too.
- **A browser:** the `contextmenu` event itself, which the browser sends
  at its platform's time for each gesture: the secondary button, Control
  with the primary on macOS, a pen's barrel and a touch's long press. The
  host reports it there and cancels it, so the browser's menu does not
  open, and cancels the secondary button's `pointerdown` too, for focus
  and selection. It reports a `contextmenu` the browser makes from a key
  only where its tests tell one from a pointer's, and otherwise not.
  Where an element with `rightbutton` takes the secondary button, it cancels the
  `contextmenu` that button makes and reports none, as a page does that
  keeps the button: the browser sends it on the press on Linux and
  macOS, and after the release on Windows. A `contextmenu` from Control
  with the primary, a pen's barrel or a long press is still reported
  there; the host tells them apart by the press it saw before
  (`pointerdown` with `button` 2 and `pointerType` `mouse`).

Shift and Alt come first (SPEC.md §9.2). With either held, the host
handles the gesture as one on the cells beneath the surface: the
terminal's own menu with Shift, and the program's mouse report with Alt.

**The menu key** is optional (SPEC.md §9). A host that reads keys before
it passes them on, as a terminal host does, can report `context_menu` and
`shift+f10` where SPEC.md says. One that does not leaves them keys, which
reach the program (SPEC.md §10.2), and a program offers its menu from
them too.

### 3.2 Other buttons

SPEC.md §9 reports a mouse's other buttons by the DOM's numbers, on an
element with `aux` in its `data-on`, as an `auxclick` at the release, or a
drag where the element has `drag` too. The secondary button is reported
the same way on an element with `rightbutton`, as `button` 2: GDK's 3,
AppKit's `rightMouseDown` (`buttonNumber` 1), and a browser's 2, the same
on every engine. A host maps its
platform's other buttons to them:

| platform | middle (1) | back (3), forward (4) | later (6 and up) |
| --- | --- | --- | --- |
| GTK (GDK button numbers) | 2 | 8 and 11; 9 and 10 | 12 → 6, 13 → 7, and on |
| AppKit (`NSEvent.buttonNumber`) | 2 | 3, 4 | 5 → 6, 6 → 7, and on |
| a browser (`MouseEvent.button`) | 1, with bit 4 in `buttons` (below) | 3, 4 | none: browsers report no more |

- **GDK's 10 and 11** are libinput's `BTN_FORWARD` and `BTN_BACK`, which
  some mice send for their thumb buttons. Chromium folds them into
  forward and back, and a host does the same, so that one mouse has the
  same numbers in a browser host and in a terminal host.
- **Not the wheel.** GDK's buttons 4 to 7 are X11's wheel, which GTK 4
  sends as scrolls. A host never reports them as buttons.
- **Later buttons** are numbered from 6 in the platform's order, so the
  same physical button may have different numbers on different platforms.
  A program can't count on one anyway (SPEC.md §9). A host reports only
  those its toolkit names: Ghostty's buttons end at its eleventh, which is
  GDK 11 and AppKit's `buttonNumber` 10, so hottyterm has no later button
  on GTK, and six on macOS.
- **What the platform makes a button** is a button. On Linux, libinput
  makes the middle button from a touchpad's three-finger tap, and from the
  primary and secondary pressed together. A host can't tell them from a
  mouse's, and doesn't try.
- **Drivers that send no button.** Many mouse drivers on macOS send back
  and forward as key presses, which reach the program as keys (SPEC.md
  §10.2). On Windows, some send them as an app command instead of a
  button, which no page can cancel: one more reason a browser host checks
  each engine (below).

**A host reports a button only where it can keep the platform's own action
from it** (SPEC.md §9): autoscroll, the terminal's or the browser's paste,
history navigation, a link opened in a new tab. A button it can't take
whole stays the platform's or the terminal's, and is never half-taken: a
program that heard an `auxclick` while the page went back would be worse
off than one that heard nothing.

**A browser host** applies that rule per engine, decided up front, because
it can't find out at run time: a navigation that wasn't cancelled has
already happened.
- **What it cancels,** for a press it takes:
  - `pointerdown`, for focus, selection (or in Firefox the caret's move)
    and autoscroll. Cancelling it also keeps the page from seeing the
    compatibility `mousedown` and `mouseup` (Chromium doesn't send them;
    Firefox sends them only to itself, already cancelled), so the page
    can't cancel `mouseup`. In Firefox it is also what stops the history
    navigation for buttons 3 and 4;
  - `pointerup`, whose result Chromium merges with `mouseup`'s, for
    Chromium's history navigation on buttons 3 and 4 and its middle paste
    on Linux. Firefox doesn't merge it, and its cancel does nothing there;
  - `auxclick`, for a link's new tab in both engines. It does not stop
    Chromium's navigation;
  - the `paste` a middle press makes, which stops the paste in both
    engines. Firefox pastes from a listener of its own on `auxclick`,
    which honours a cancelled `auxclick` but not the pointer and mouse
    cancels.

  It tests each of these in each engine.
- **Which buttons:** it reports buttons 3 and 4 only on the engines its
  tests have checked, Chromium first. Firefox 162 (likely 2026-12-08)
  sends `mousedown`, `mouseup` and `auxclick` with buttons 3 and 4, and
  lets a page that cancels the press stop the navigation; 160 and 161
  send none. No engine has been checked from inside a sandboxed frame,
  and a test that synthesises input does not go the browser's real way to
  back and forward, so the check is made with real input.
- **The buttons bits.** It takes `button` 1 as the middle button only
  when `buttons` has bit 4. With 8 or 16 it is back or forward, which it
  reports as 3 or 4 only where the engine is checked, and otherwise not at
  all. Safari before the fix of WebKit bug 280755 (likely Safari 26.4)
  reported both side buttons as `button` 1 on macOS, with `buttons` 8 or
  16, and as 0 on iPadOS.
- **The pointer, until the release.** It calls `setPointerCapture` on
  the press it takes, so that the moves and the release reach it wherever
  the pointer goes, outside the surface's frame included, as for a
  primary drag. Its moves go to a drag once they pass its slop, where the
  element has `drag` as well (SPEC.md §9.1), and nowhere otherwise; its
  `pointerup` there is the `auxclick` or the `dragend`.
- **Over an element without `aux`,** it passes the press to the program's
  mouse reporting, as it passes a press with Alt (SPEC.md §9.2), and
  cancels its `pointerdown`, as for any press it passes on over a surface,
  since the surface hears nothing of it: no focus, and no autoscroll on
  Windows. The terminal's own paste does not happen there: a browser
  pastes the primary selection only on a press it made itself, into an
  editable element, and a page reads it only in the `paste` event of such
  a press.
- **A text field.** On Linux, where a browser's middle press pastes, a
  middle press on a text field (SPEC.md §9) is left to the browser, which
  focuses the field on `mousedown`, as it does for any button, and pastes
  the selection into it. The host does not cancel it. With Shift held it
  cancels it as for a press it takes, and passes it on. Elsewhere the
  field is like any element without `aux`: the press is passed on, and
  its `pointerdown` cancelled, so the field takes no focus.
- **The terminal's paste into a field** (SPEC.md §11) is not made over a
  surface (above), and on the cells xterm.js moves its own text area under
  the pointer for a middle press on Linux, so the browser pastes there, to
  the program, and the field loses the keyboard. A browser host that can
  route that paste, by cancelling the text area's `paste` and typing its
  `clipboardData` into the field, does; one that can't leaves §11's
  **SHOULD** unmet for a middle press, and skips the vectors marked
  `"paste-field"`.

**On GTK, a second button cancels the first.** A `GtkGestureClick` for
every button (`button` 0), as Ghostty's is, resets itself when a button
other than the held one is pressed (GTK 4.24's `gtkgesturesingle.c`): it
emits `cancel`, the second press never comes as `pressed`, and the first
button's release never comes as `released`, its point being gone. Both
releases still come, as `unpaired-release` with their buttons
(`gtkgestureclick.c`), which Ghostty does not connect. A host that holds
a button, for a surface or for the terminal, and listens only to
`released`, would hold it for good. It takes presses and releases where
every one arrives, a `GtkEventControllerLegacy` beside the gesture, or
keeps every hold through the `cancel` and ends it from
`unpaired-release`. Ending a hold at the `cancel` would end a drag at the
second press, against one button at a time (SPEC.md §9).

**A terminal host** (hottyterm) asks the surface before the terminal does
anything with a press: before its paste, its mouse report, and any return
its toolkit's code makes first. A press the surface took has its moves and
its release taken too, the moves going to a drag where the element drags
with the button (SPEC.md §9.1), and so does any press while a surface
holds a button (SPEC.md §9, *One button at a time*). A middle press on a field is taken, as a
press the surface took: the host focuses the field and puts its caret at
the pointer, then starts the terminal's read of what its middle press
pastes itself, and the terminal's paste types it into the focused field
(SPEC.md §11). It does not fall through to the terminal's middle press,
which mouse reporting or the toolkit would stop first. The terminal's
middle press pastes (SPEC.md §9, *A text field pastes*) only where its
setting makes it paste and the platform can: not where the setting is to
ignore it, nor on GTK with `gtk-enable-primary-paste` off, nor with the
primary selection on a platform that has none (macOS).

## 4. Reduced motion

Where a host reads the setting that `prefers-reduced-motion` follows
(SPEC.md §8):

- **GTK:** `gtk-enable-animations` in GtkSettings; false is `reduce`.
  Watch `notify::gtk-enable-animations` for changes.
- **macOS:** `NSWorkspace.shared.accessibilityDisplayShouldReduceMotion`,
  and `NSWorkspace.accessibilityDisplayOptionsDidChangeNotification` for
  changes.
- **A browser** (the xterm.js addon): the page's own
  `matchMedia('(prefers-reduced-motion: reduce)')`. The browser already
  applies it to the surfaces' CSS, so the addon does nothing.

## 5. Speaking 0.8 as well

hotty's own stack, hosts and SDKs, speaks 0.8 along with 0.9. SPEC.md §15
lets a host speak several versions, and the rest is what the stack does
with it. A host that does not speak a program's version answers it with
`EVERSION` (SPEC.md §4), and the program falls back: a 0.7 program meets
a 0.9 host so. Each version is the session's, but only in its wire
shapes: a host switches how it reads keymaps (§5.1) and reports buttons
(§5.2) by the version it answered in, and nothing else.

- **A host that speaks 0.8 as well** answers a program that lists 0.8 and
  not 0.9 in 0.8, and speaks 0.8 to it from then on (SPEC.md §4). A query
  that lists both is answered in 0.9, the highest the two share.
- **The rest is 0.9's in every session,** an 0.8 one included (the
  maintainer): focus fixup (SPEC.md §10.1), a wheel at a surface's edge
  (SPEC.md §5.3), a key the keymap gives the program that is a command it
  took (SPEC.md §10.6), an identical resend (SPEC.md §7.1), and
  `prefers-reduced-motion` (SPEC.md §8). 0.8 left each of them open or to
  the host, so no 0.8 reading is kept.

### 5.1 Keymaps in an 0.8 session

From 0.9 a keymap is written in two attributes, an element's own
`data-keys` and the `data-keys-inner` that holds for what is inside it
(SPEC.md §10.2, *Keymaps*). An 0.8 document wrote one, `data-keys`, which
held for everything inside its element. A host that speaks 0.8 as well
reads an 0.8 document's keymaps with the same resolver, from other
attributes:
- **Each `data-keys` is read as both its element's own `data-keys` and
  its `data-keys-inner`.** The keymap is then 0.8's: every ancestor's
  `data-keys` from the root down, then the focused element's. With
  nothing focused, and for a selection, the root's and the body's hold as
  inner, and the body's as its own, so an 0.8 body's `mod+c=copy` or
  `default` still holds. An 0.8 wrapper's editing keys and leader reach
  the fields and buttons inside it, as 0.8 had them. `data-keys-inner`,
  which 0.8 had not, is not read.
- **Each reader takes what 0.9 has it take,** so what still differs is
  what 0.9 changed: an inner `program` or `prefix` no longer takes a key
  the element uses (a field types its characters, a button keeps
  `space`); `default` holds where the focused element writes it, not
  above it; a selection reads the root's and the body's keymaps, not those
  around its text; and with nothing focused the body's keymap holds.
- **No second reading:** one resolver, with the bindings taken from where
  0.8 put them.

### 5.2 Buttons in an 0.8 session

From 0.9 a context menu's gesture is `contextmenu`, asked for with
`contextmenu` in `data-on`, and another button is `aux`'s `auxclick`
(SPEC.md §9). 0.8 had a `press` with `button` 2, asked for with
`secondary`, and no other button. A host that speaks 0.8 as well keeps
that in an 0.8 session:
- **`secondary` is read, and `contextmenu`, `aux` and `rightbutton` are
  not.** The gesture is reported as a `press` with `button` 2, its `area`,
  and `c` and `r`, at the press on every platform, as 0.8 had it, and never
  from the menu key.
- **No other button is the surface's:** each is the terminal's, as over
  the cells, and no drag carries a `button`.
- **Shift and Alt** are as 0.8 had them for the secondary press.

## 6. Implementations

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
