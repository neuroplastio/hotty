---
group: Concepts
order: 10
nav: How hotty works
description: one surface, from the program's first byte to the user's click
---

# How hotty works

A hotty program writes HTML to its terminal, and the terminal draws it
among the cells. When the user clicks, the program reads the event from
its input, as it reads keys. Everything travels in the program's own
output and input, so hotty works wherever a terminal does: over SSH, in a
container, in a multiplexer that is a host itself or passes hotty
through.

```text
 program                                   host (the terminal)
   │  is there a host? (a=q)  ───────────▶  │
   │  ◀─────────────  yes, and what it can  │
   │  a document (a=doc)      ───────────▶  │  keeps the HTML
   │  a placement (a=place)   ───────────▶  │  lays it out on cells, draws it
   │  a change (a=delta)      ───────────▶  │  changes those elements
   │  ◀───────────────  an event (a=ev)     │  the user clicked, typed, dragged
```

This page follows one card through that loop. The [protocol](../../SPEC.md)
has the rules; each step below names its section.

## The envelope

Every message, both ways, is one escape sequence (§3):

```text
ESC ] 7279 ; a=doc:s=card ; PGJ1dHRvbiBpZD1nbz5HbzwvYnV0dG9uPg== ST
```

- `ESC ]` starts an operating system command, as setting a window's title
  does, and `ST` ends it. 7279 is `H` and `O` in ASCII.
- The **control**, `a=doc:s=card`, is `key=value` pairs. `a` is the
  action, and `s` names the surface.
- The **payload** is base64: HTML here, and msgpack where a message has
  fields.

A terminal that isn't a host ignores the sequence, as it ignores any
command it doesn't know. That's what makes it safe to ask.

## Is there a host?

A program asks first (§4):

```text
program → ESC ] 7279 ; a=q:n=1:v=0.4 ST  CSI c
host    → ESC ] 7279 ; a=ok:n=1:re=q ; <the capabilities> ST  CSI ? 62 ; 22 c
```

`CSI c` asks the terminal what it is, and every terminal answers it. So a
program that sees that answer with no hotty reply in front of it knows
there is no host. It then draws in cells after a short grace, not a long
timeout.

The reply carries the host's **capabilities**: the version it speaks, the
size of a cell in CSS pixels, its light or dark scheme, and the optional
features it has.

## A document, then a place for it

A **surface** is a named HTML document. The program sends the document,
then places it (§5):

```text
program → ESC ] 7279 ; a=doc:s=card ; <button id=go>Go</button> ST
program → ESC ] 7279 ; a=place:s=card:c=40:r=auto:n=2 ST
host    → ESC ] 7279 ; a=ok:n=2:s=card:re=place:c=40:r=2 ST
```

(Payloads are shown decoded here; on the wire they are base64.)

The placement is a rectangle of cells at the cursor: 40 columns, and as
many rows as the document needs, which the host answers with. The surface
then belongs to that line. It scrolls up with the output around it, and
stays in the scrollback after the program exits. A full-screen program
places its surfaces where it draws, and moves them as its screen changes.

The host lays the document out with real CSS, in the terminal's font and
colours by default ([Styling](styling.md)). Inside the rectangle it is
HTML. Outside it, everything is still a terminal.

## Changes by id

To change what a surface shows, the program sends a **delta**: a list of
operations on elements, each found by its `id` (§6):

```text
program → ESC ] 7279 ; a=delta:s=card:q=2 ; {"ops": [{"op": "text", "t": "go", "v": "Start"}]} ST
```

The button now reads "Start". A change costs what it changes: a live
number is a few dozen bytes, however large the document is.
[Updates](updates.md) has every operation, and the morph that replaces an
element while keeping what the user was doing in it.

## Events come back as input

When the user clicks the button, the host writes an **event** to the
program's input, among the keys the user types (§9):

```text
host → ESC ] 7279 ; a=ev:s=card:e=click:t=go ; {"area": {"c": 0, "r": 0, "w": 4, "h": 1}} ST
```

`s` is the surface, `e` the kind of event, and `t` the element's id. The
program decides what it means.

Much happens without a round trip. Typing in a field, hovering, scrolling a
document and toggling a checkbox all happen in the terminal, and the
program hears only what it asked for: a `change` when the field's value is
committed, a `submit` with the whole form. [Input](input.md) and
[Keyboard and focus](keyboard.md) say what a surface reports, and when.

## What hotty is not

- **Not a browser.** A surface runs no script. The program holds the state
  and decides what every click means. The host only draws and reports.
- **Not the network.** Everything a document needs, images included, comes
  in the program's output. A host fetches from the network only where the
  user lets it, and only what the document asks for
  ([Images and the network](resources.md)).
- **Not all or nothing.** A program can put one card in a shell's output,
  or draw every panel of a full-screen tool as HTML. Wherever there is no
  host, it draws the same thing in cells ([Degrading](degrading.md)).
