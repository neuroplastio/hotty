---
group: Concepts
order: 20
nav: Surfaces
description: a named document on a rectangle of cells, from its size to its removal
---

# Surfaces

A surface is one HTML document with a name, shown on at most one rectangle
of cells. The document and the rectangle are sent apart: `a=doc` gives the
surface its document, and `a=place` gives it a **placement**. This page
says what each part is for; the [protocol](../../SPEC.md#5-surfaces) has
the rules (§5).

```text
program → ESC ] 7279 ; a=doc:s=card ; <h1>Deploy</h1><p id=status>Waiting</p> ST
program → ESC ] 7279 ; a=place:s=card:c=40:r=auto:n=1 ST
host    → ESC ] 7279 ; a=ok:n=1:s=card:re=place:c=40:r=3 ST
```

(Payloads are shown decoded here; on the wire they are base64.)

## A name and a document

The name is how your program refers to the surface from then on: 1 to 64
letters, digits, `_` and `-` ([§3.5](../../SPEC.md#35-common-keys)). Two
runs of a program in one terminal could pick the same one. So an SDK's
`Surface(name)` prefixes the name with the program's name and process id,
or with the prefix its environment gives
([SDK design](../../SDK.md#41-terminal)).

`a=doc` creates the surface, or replaces its whole document
([§5.1](../../SPEC.md#51-documents-adoc)). The payload is a document or a
fragment, parsed as a browser parses HTML. A new document keeps the
surface's placement and size, so a card can show something else without
being placed again.

Two keys of `a=doc` belong to the document: `d=1` creates the surface
detached ([Detaching](#detaching)), and `scroll` lets it scroll
([Scrolling inside a document](#scrolling-inside-a-document)). A new
document sent without them has neither, whatever the one before it had.

To change part of a document, send a delta rather than the whole document
again ([Updates](updates.md)).

## A size in cells

A placement's size is in cells: `c` columns and `r` rows, each from 1 to
1000 ([§5.2](../../SPEC.md#52-placement-aplace)). The host lays the
document out at that size, in CSS pixels
([§5.3](../../SPEC.md#53-geometry)). Media queries and viewport units refer
to it, so `100vw` is the surface's width, not the terminal's.

`r=auto` asks for as many rows as the content needs, up to 1000, and a
placement with no `r` means the same. Number the placement with `n`, as
above, and the reply says how many rows the host chose.

The pixels inside the rectangle may differ between hosts, as text differs
between fonts. The cells it covers may not: they are exactly what the
program asked for (§5.3). So the terminal's grid stays a grid, whatever a
host draws inside it.

## When the content changes height

A document can need more rows, or fewer, after it is placed. An image
arrives, a font loads, a delta adds a line, or the terminal's font changes
the size of a cell (§5.2). The host keeps the placement's size anyway,
since the cells below it are your program's.

With `f=1` on a placement, the program hears `fit` whenever the rows the
content needs change. Its detail is the rows `r=auto` would choose now:

```text
program → ESC ] 7279 ; a=place:s=log:c=60:r=auto:f=1:n=2 ST
host    → ESC ] 7279 ; a=ok:n=2:s=log:re=place:c=60:r=4 ST
program → ESC ] 7279 ; a=delta:s=log:q=2 ; {"ops": [{"op": "append", "t": "lines", "v": "<li>tests passed</li>"}]} ST
host    → ESC ] 7279 ; a=ev:s=log:e=fit ; {"r": 5} ST
```

The program then places the surface again with 5 rows, where it has room
for them. `fit` is opt-in, so a program that never sizes a surface by its
content hears nothing new ([Appendix B](../../SPEC.md#appendix-b-rationale)).

## Windows

A placement can show part of its surface, a **window** (§5.2). `x` and `y`
say where the window starts in the surface, in columns and rows, and `w`
and `h` how many of each it shows. Without them, the window is the whole
surface.

The whole surface is still laid out at `c` by `r`. Only the window is
drawn, and only the window takes the pointer (§5.3). A new window of the
same surface lays nothing out again, and a host should make it cheap.

Windows are for full-screen programs that scroll content holding surfaces,
such as a transcript. A surface at the edge of a scrolling region shows
the part in view, as a kitty graphics placement shows part of an image:

```text
program → ESC ] 7279 ; a=place:s=diff:c=60:r=10:y=4:h=6 ST
```

The diff is ten rows tall, and its top four have scrolled out of view. The
placement shows the six below them.

## Stacking

`z` orders placements that overlap, as CSS `z-index` orders boxes (§5.2).
It runs from -1000 to 1000, and a placement without it has 0. Of two with
the same `z`, the surface created later is above.

- `z` belongs to the placement: placing the surface again without it puts
  it back at 0.
- Every placement is above the terminal's cells, whatever its `z`.
- Where placements overlap, the pointer goes to the topmost one under it.

## Where a placement goes

A placement's top-left corner is the cell the cursor is in (§5.2). The
host then moves the cursor to the start of the line below the placement,
scrolling if it must. So a command that prints a card places it at the
cursor, and its next output follows below, as it would after text.

A full-screen program places its surfaces where it draws them instead. It
moves the cursor there, places with `C=1`, which leaves the cursor where it
is, and puts the cursor back:

```text
program → ESC 7  ESC [ 3 ; 5 H  ESC ] 7279 ; a=place:s=chart:c=40:r=12:C=1 ST  ESC 8
```

`ESC 7` saves the cursor, `ESC [ 3 ; 5 H` moves it to row 3, column 5, and
`ESC 8` restores it. The SDKs call this `PlaceAt`.

Placing a surface that is already placed moves it: the old placement goes.
A full-screen program places its surfaces again whenever its frame moves
them, as it redraws its cells.

A placement also carries what the program wants to hear: `p` for presses,
`f` for `fit` and `v` for hover. Each belongs to the surface and holds until
the program changes it, so a program that places a surface every frame
sends them once ([Input](input.md#what-asks-for-each-event)).

## Scrolling inside a document

By default, nothing in a surface scrolls (§5.3). What doesn't fit is
clipped, there are no scrollbars, and every scroll offset stays at zero. A
wheel over it acts as it would over the cells: it scrolls the scrollback,
or on the alternate screen, reaches the program.

So a program can scroll content as it scrolls its cells. It hears the
wheel, and places its surfaces again, through windows where they are
partly in view. The whole screen scrolls, with its surfaces in it.

Some content can't be laid out to fit, such as a long log beside a form.
Paging it through windows costs a round trip for each step of the wheel. A
document that asks, with `scroll` on its `a=doc`, scrolls in the host
instead:

```text
program → ESC ] 7279 ; a=doc:s=log:scroll=1 ; <pre>…</pre> ST
```

`scroll` names the axes: `1` vertically, `2` horizontally, `3` both. Along
them the document scrolls as a page does in a browser:

- its root, and every element whose `overflow` is `auto` or `scroll`,
  scroll what overflows them, with the host's scrollbars;
- the user scrolls it with a wheel, a touchpad or a finger, and with keys
  while the surface has the keyboard ([Keyboard and focus](keyboard.md));
- a gesture scrolls the innermost element that can still move that way.
  At its end it goes outward, and past the root to the terminal, unless
  `overscroll-behavior` stops it.

Scrollbars take pixels inside the rectangle, never cells, so the cells a
surface covers stay what the program chose. `scrollbar-width`,
`scrollbar-color` and `scrollbar-gutter` style them.

Scrolling is local: the program hears of it only where elements ask to be
told when they are in view ([§9.5](../../SPEC.md#95-view)). It moves the
scroll only by moving focus, or with `reveal`
([Updates](updates.md#the-ops)). A delta keeps the offsets, and a new
document starts at the top left.

## Lifetime

A placement lives as a kitty graphics placement does: on the line it was
placed on ([§5.4](../../SPEC.md#54-lifetime)). It scrolls up with that
line, and goes when the line leaves the scrollback. The document stays, and
your program can place it again.

- **The alternate screen.** A placement made there belongs to that screen,
  and goes when the terminal leaves it. The host should delete the surface
  too.
- **A full reset** (RIS) deletes every surface.
- **A multiplexer** that passes hotty through should delete what a pane's
  program left when it ends, as a reset in that pane would. Where it keeps
  the pane's text on the screen, it keeps the detached surfaces with it.

Your program can remove a placement itself, and keep the surface or not:

| command | removes |
| --- | --- |
| `a=hide:s=<name>` | the placement; the document stays, with what the user did in it |
| `a=del:s=<name>` | the surface and its placement |
| `a=del:id=<id>` | a resource ([Images and the network](resources.md)) |
| `a=del` | every surface |

Hide what you will show again soon, such as a card scrolled out of view,
and delete the rest. A hidden document still takes deltas, and placing it
again shows it as it is then, with nothing sent again. Hidden surfaces
count against the host's limits ([§13](../../SPEC.md#13-limits)).

Hiding a surface that has the keyboard gives the keyboard back to the
terminal, as `a=blur` does. A placement answered with `ENOENT` means the
host has no surface of that name, after a reset for instance: send the
document again.

## Detaching

A surface belongs to the program that sent its document
([§5.5](../../SPEC.md#55-ownership-adetach)). Its events go to that
program's input, and it takes the keyboard on that program's behalf. The
host can't tell when that program has gone.

Events arrive on whatever reads the terminal's input. After a command
exits, that is usually a shell, which would read a click as typed text. So
a program that leaves surfaces on the screen **detaches** them before it
exits, or creates them detached:

```text
program → ESC ] 7279 ; a=doc:s=report:d=1 ; <table>…</table> ST
program → ESC ] 7279 ; a=place:s=report:c=60 ST
```

`d=1` suits a document the program will never hear from, even one it keeps
changing with deltas. `a=detach:s=<name>` does the same later, once the
program is done listening. Either holds until an `a=doc` without `d=1`
replaces the document.

A detached surface stays on the screen as text does. It is placed, hidden,
changed and deleted as before, and moves with its line. Nothing in it
reaches the program:

- it sends no events of any kind;
- it never has the keyboard, and `a=focus` on it is `EDETACHED`;
- its form controls act as if `disabled`, and match `:disabled`, while
  what the user typed in them stays;
- what is local still works: hover, selecting text, toggling a
  `<details>`, and hyperlinks, which belong to the terminal.

Detaching a field the user is typing in sends no `change`. To keep what
they typed, send `a=blur` first: the field commits its value, with a
`change` if it changed, and `blur` follows. Detach once `blur` arrives.

A program that crashes can't detach. What ran it, such as a shell, may
detach its surfaces if it knows their names. Otherwise they keep reporting
until they are deleted or leave the scrollback, as a crashed program can
leave mouse reporting on ([Appendix B](../../SPEC.md#appendix-b-rationale)).
