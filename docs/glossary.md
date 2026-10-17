---
group: Reference
order: 50
nav: Glossary
description: the words hotty uses, each with its section of the protocol
---

# Glossary

Each word below links to the section that defines it, in the
[protocol](../SPEC.md) or the [SDK design](../SDK.md).

- **area**: a rectangle of cells, given as `c`, `r`, `w` and `h`. It is
  where an element is, in an event ([§9](../SPEC.md#9-events)), or where
  a finger drags in the cells ([§9.6](../SPEC.md#96-touch-in-the-cells)).
- **capability**: a field of the host's answer to the query, such as its
  version, its cell size or its features
  ([§4](../SPEC.md#4-detection-and-capabilities)).
- **cell**: one character's place in the terminal's grid. A placement's
  size and position are counted in cells ([§5.3](../SPEC.md#53-geometry)).
- **delta**: a change to a surface's document, a list of ops applied as
  one ([§6.1](../SPEC.md#61-adelta)).
- **document**: the HTML a program sends for a surface, with `a=doc`
  ([§5.1](../SPEC.md#51-documents-adoc)).
- **event**: what the host reports of the user, written to the program's
  input as `a=ev` ([§9](../SPEC.md#9-events)).
- **feature**: something optional a host has, listed in its capabilities:
  `passthrough`, `hover`, `count` or `menu`
  ([§4](../SPEC.md#4-detection-and-capabilities)).
- **host**: what draws a program's surfaces: usually the terminal itself,
  sometimes a polyfill or a multiplexer ([§2](../SPEC.md#2-conventions)).
- **keymap**: the keys an element binds to actions, from the `data-keys`
  of it and the elements around it ([§10.2](../SPEC.md#102-keys)).
- **morph**: changing an element into new HTML while keeping what the user
  was doing in it ([§6.2](../SPEC.md#62-morph)).
- **op**: one change in a delta, such as `text`, `attr` or `morph`, on an
  element found by its id ([§6.1](../SPEC.md#61-adelta)).
- **placement**: the rectangle of cells that shows a surface, made with
  `a=place` ([§5.2](../SPEC.md#52-placement-aplace)).
- **prefix**: a key bound to `prefix`, which sends the program itself and
  every key after it, until the program gives them back with `a=focus` or
  `a=blur`, the surface loses the keyboard, or the user focuses an element
  of it with a press ([§10.5](../SPEC.md#105-key-sequences)).
- **program**: the process whose output the terminal shows; it holds the
  state and decides what each event means ([§2](../SPEC.md#2-conventions)).
- **rendition**: one of the three ways a program shows itself: surfaces,
  cells or plain data ([SDK design §2.5](../SDK.md#25-three-renditions)).
- **resource**: named bytes with a MIME type, such as an image, sent with
  `a=res` and referred to as `cid:<id>`
  ([§7.1](../SPEC.md#71-in-band-resources)).
- **surface**: a named HTML document, and at most one placement showing
  it ([§5](../SPEC.md#5-surfaces)).
- **window**: the part of a surface that its placement shows, chosen with
  `x`, `y`, `w` and `h` ([§5.2](../SPEC.md#52-placement-aplace)).

[How hotty works](concepts/how-it-works.md) shows most of these in one
round trip.
