# HOTTY — HTML Over The TTY

    Version:  0.2
    Status:   Draft. Versions 0.x may change incompatibly (§15).
    Licence:  CC BY 4.0 (this document); the conformance vectors are
              Apache-2.0.

## Abstract

HOTTY lets a program running in a terminal show **surfaces**: small HTML
documents drawn by the terminal into rectangles of cells, the way the kitty
graphics protocol places images. The program sends markup and deltas
in-band, as escape sequences in its ordinary output, so it works over a pty,
over SSH and through anything else that carries a terminal's bytes. The
terminal lays the markup out, draws it, and handles focus, typing and hover
itself. What the user does comes back to the program as events on its input.

There is no script and no network. The program is the application: it holds
the state and decides what every event means. The terminal is the view. A
surface can do nothing the program did not send it, and can learn nothing
the program did not give it.

![hotty-demo full screen in xterm.js: the web shell runs `sh deploy.sh`, whose
askhot questions — a choice, a text field, a confirmation, a form — are
surfaces the program hears; a chart streams from a pipe; a metrics chart is
hovered for its values, a moment pinned and a heatmap shown; a document
scrolls a row at a time, with a table, code and an SVG diagram in it; cards,
images and charts scroll in a feed; and an agent's transcript, diff, approval
and load test follow.](demo.gif)

*The HOTTY website, [hotty.neuroplast.io](https://hotty.neuroplast.io),
running in xterm.js with
[xterm-addon-hotty](https://github.com/neuroplastio/xterm-addon-hotty), one of
the two hosts that share no code and pass the conformance vectors. Every
surface — the askhot questions, the charts, the table, the diagram, the cards,
the diff, the approval — is HTML the program sent in-band, in the terminal's
own output; the cells around them are the program's too.*

## Contents

1. Introduction
2. Conventions
3. The envelope
4. Detection and capabilities
5. Surfaces
6. Deltas
7. Resources
8. The host stylesheet
9. Events
10. Keyboard and focus
11. Text
12. Security
13. Limits
14. Degradation
15. Versioning and extensions
16. Conformance

Appendices: A. Examples · B. Rationale · C. Prior art

---

## 1. Introduction

A terminal program has cells: monospace characters with a few
attributes. HOTTY adds a second kind of output: a **surface**, one HTML
document, placed on a rectangle of cells. Inside it the host lays out and draws
the document at the terminal's own resolution, with proportional type,
tables, form controls, SVG and images. Outside it, everything stays a
terminal.

HOTTY is designed around four constraints:

- **In-band.** Everything a surface needs travels in the program's output
  stream. Nothing is loaded from files or the network, so a program behaves
  the same locally, over SSH and inside a container.
- **The program is the application.** Surfaces have no script. The program
  changes the document with deltas and hears about events. It never runs
  code in the terminal.
- **Degradable.** A program asks whether the terminal is a HOTTY host before
  using it, and paints ordinary text when it is not. Terminals that are not
  hosts ignore HOTTY sequences.
- **Cheap to update.** Changes are deltas addressed by element id, so a
  program changing one number sends a few bytes, and a host repaints what
  changed.

### Non-goals

HOTTY is not a web browser in a terminal:
- it has no URLs to visit;
- it loads nothing remotely;
- it runs no JavaScript or WebAssembly;
- it has no cookies or storage.

It is also not a replacement for cell-based TUIs: surfaces sit beside
terminal text, and a program can use both.

## 2. Conventions

The key words **MUST**, **MUST NOT**, **SHOULD**, **SHOULD NOT** and **MAY**
are to be interpreted as described in RFC 2119 and RFC 8174 when, and only
when, they appear in bold.

- **Program**: the process whose output the terminal displays.
- **Host**: whatever renders HOTTY for that program. Usually the terminal
  emulator itself. It can also be a pty shim between the program and a
  terminal (a *polyfill*; §14). A multiplexer between a program and a
  terminal either is a host itself, or passes HOTTY through and keeps
  placements consistent with its own screen and scrollback.
- **Session**: a program's connection to a host, from the first HOTTY command
  until a full reset or the end of the program's output.
- **Surface**, **resource**, **delta**, **event**: §5, §7, §6 and §9.
- `ESC` is 0x1B, `BEL` 0x07, `ST` the two bytes `ESC \`. `CSI` is `ESC [`.
- **CSS pixel**: CSS's reference pixel. A host's **scale** is device pixels
  per CSS pixel.

## 3. The envelope

### 3.1 Sequences

Every HOTTY message, in both directions, is an operating system command:

```
ESC ] 7279 ; <control> [ ; <payload> ] ST
```

- **7279** is the ASCII codes of `H` and `O`.
- A host **MUST** also accept `BEL` as the terminator. Hosts send `ST`.
- A terminal that is not a HOTTY host ignores the sequence, as it ignores any
  OSC it does not know. That is what makes HOTTY safe to try (§4).

### 3.2 Control

`<control>` is a list of `key=value` pairs separated by `:`.

```
control = pair *( ":" pair )
pair    = key "=" value
key     = ALPHA *( ALPHA / DIGIT / "-" / "_" )
value   = *( %x20-39 / %x3C / %x3E-7E )    ; printable ASCII except ":" ";" "="
```

- A key appears at most once.
- A host **MUST** ignore keys it does not know (§15).
- **A value is printable ASCII.** Whoever sends one, a host or a program,
  **MUST** replace each character a value may not hold with `_`: `:`, `;`,
  `=`, a control character, and any character outside ASCII. It replaces
  each Unicode code point with one `_`, and each byte that is not UTF-8 with
  one `_`. An element whose id is `café` is reported as `t=caf_`, so a
  program that needs its ids back gives them in ASCII.

### 3.3 Payload

`<payload>` is the command's body, **base64** encoded (RFC 4648, standard
alphabet).
- Hosts **MUST** accept base64 with or without padding, and ignore
  whitespace in it.
- A program **MAY** compress a body with zlib (RFC 1950) before encoding
  it, and mark it `o=z`. A host **MUST NOT** compress what it sends (replies
  and events), so a program needs no zlib to read them.
- An empty body is sent as nothing, and the `;` before it may then be
  omitted.
- Text bodies (markup, delta values) are UTF-8.
- **A host's bodies are msgpack**
  ([MessagePack](https://github.com/msgpack/msgpack/blob/master/spec.md)).
  The body of a reply (§3.6, §4) or an event (§9) is one msgpack map, with
  nothing after it. What a program sends is not msgpack, but
  for a menu (§10.6): documents, deltas and resources are text or bytes.
- **Each field has a type.** This document shows a body as JSON with types
  in place of values: `{"c": int, "keys": [str]}` is a map with an int
  `c` and an array of strings `keys`, and `{str: int}` a map from strings
  to ints. The types are `int`, `float`, `str` and `bool`.
  - A host **MUST** send each field as its type. A field it has nothing
    for is left out, not sent as nil.
  - An int is at most 2^53 − 1 from zero either way, so that a reader
    whose numbers are doubles (JavaScript, Lua 5.1) holds it exactly.
  - A body holds no nil, and its maps are keyed by strings, each given
    once. A string is UTF-8.
  - Any of msgpack's forms of a type is that type: an int of any size,
    signed or not, a float of 32 or 64 bits, a string, an array or a map
    of any length.
  - A time, in a field that carries one, is msgpack's timestamp
    (extension type −1): 4, 8 or 12 bytes, its seconds at most 2^53 − 1
    from 1970 and its nanoseconds under a second. No field of this version
    carries one.
  - A body that breaks any of these, anywhere in it, in a field a reader
    knows or not, does not decode (SDK.md §3.9).

### 3.4 Chunks

A message whose encoded payload is longer than 4096 bytes **MUST** be split
into chunks of at most 4096 payload bytes each:

- The first chunk carries the whole control plus `m=1`.
- Every further chunk carries only `m` and, if the message has one, `q`.
  Every chunk but the last has `m=1`; the last has `m=0`.
- The chunks of one message are contiguous. A HOTTY message with any other key
  arriving before the last chunk aborts the message in progress. The host
  **MUST** discard that message and process the new one normally.
- Other output (terminal text, other escape sequences) may appear between
  chunks.
- A host **MAY** limit the size of a reassembled message, decoded: what
  base64 and zlib leave. It reports a limit it enforces as
  `limits.message` (§13). It **SHOULD** accept at least 1 MiB decoded.
  Past its limit, it drops the message and its further chunks, up to the
  last.
- A program **MAY** limit the messages it decodes from its host the same
  way.

### 3.5 Common keys

| key | meaning |
| --- | --- |
| `a` | the action: `q`, `doc`, `place`, `hide`, `delta`, `res`, `del`, `detach`, `focus`, `blur`, `edit`, `menu` from the program (§4–§10); `ok`, `err`, `ev` from the host |
| `s` | a surface name: `[A-Za-z0-9_-]{1,64}` |
| `n` | a request number chosen by the program, echoed in the reply |
| `q` | quiet: `0` (default) reply always, `1` reply only on error, `2` never reply |
| `o` | `z`: the payload is zlib-compressed |
| `m` | `1`: more chunks follow; `0`: last chunk |

### 3.6 Replies

The host answers each command, unless `q` says not to, with:

```
ESC ] 7279 ; a=ok|err [:n=<n>] [:s=<s>] :re=<action> [:<more>] [; <payload>] ST
```

- `n` and `s` are echoed when the command had them, and `re` names the action
  answered.
- `a=ok` replies to `place` carry `c` and `r` (§5.2); the reply to `q`
  carries the capabilities (§4).
- `a=err` carries the body `{"code": str, "detail": str}`. The codes:

| code | when |
| --- | --- |
| `EINVAL` | an unknown action or op; a bad surface name; a missing `s`, `t`, `k`, `c` or `id`; `c` or `r` out of range |
| `ENOENT` | no surface of that name |
| `ENOTARGET` | no element with that id. The detail is the id, or the missing ids comma-separated (§6.2) |
| `EDETACHED` | the surface is detached (§5.5) |
| `EQUOTA` | over one of the host's limits (§13) |
| `EBUDGET` | the host gave up on work that exceeded its time budget (§13) |
| `EVERSION` | a query (§4) lists no version the host speaks, or none at all. The detail is the versions the host speaks, comma-separated |

Replies travel on the program's input, interleaved with whatever the user
types. A program that does not want them sends `q=2`.

### 3.7 Malformed messages

A malformed message:
- a control that does not parse;
- a payload that is not valid base64 or zlib;
- a message past the host's limit (§3.4, §13);
- an aborted chunked message.

Each counts once: a malformed message that arrives before the last chunk of
another aborts it (§3.4), and makes two, the aborted message and itself.

The host **MUST NOT** act on it. It sends no reply, since it cannot know what
the program meant. It **MAY** log it.

## 4. Detection and capabilities

A program finds out whether it has a host by sending a query, then Primary
Device Attributes as a fence:

```
ESC ] 7279 ; a=q:n=1:v=0.2 ST   CSI c
```

Every terminal answers DA1. A host answers the query first:

```
ESC ] 7279 ; a=ok:n=1:re=q ; <base64 msgpack> ST
```

If the DA1 answer arrives with no HOTTY reply before it, there is no host. The
program **SHOULD** then fall back (§14).

**Versions.** `v` lists the HOTTY versions the program speaks,
comma-separated: `v=0.2` for this document, and one day perhaps
`v=0.2,0.3`. A version is `major.minor`, two numbers written without
leading zeros, and versions compare as those numbers, the major first.
- A host answers in the highest version it shares with the program: `a=ok`,
  with that version's capabilities, whose `v` names it. It speaks that
  version from then on.
- A host that shares none, or gets a query with no `v`, answers `a=err`
  with `EVERSION` (§3.6), the versions it speaks, comma-separated, as the
  detail.
- A program **MUST** take as no host a terminal that answers its query with
  an error, or with capabilities that do not decode (§3.3) or whose `v` it
  did not list, and fall back (§14). A program and a host of different
  versions, which may read each other's messages differently, then never
  meet.

A DA1 answer may belong to a question asked earlier, by the program or by
whatever ran before it. A program **MAY** wait a little after a DA1 that
arrives before any reply, for the reply and the DA1 behind it. A host answers
the query before that DA1, so the wait costs a terminal that is not a host
only that little. SDK.md sets how long.

**A late answer.** What stands between the program and the terminal may not
know yet whether there will be a host: a multiplexer running a pane with no
terminal attached. A program that can start using HOTTY after it has fallen
back asks for a late answer with `late=1`:

```
ESC ] 7279 ; a=q:n=1:v=0.2:late=1 ST   CSI c
```

- A host answers it as any query, at once.
- What passes HOTTY through and cannot answer it yet **MAY** hold it, and
  answer it once, with the reply a host would send, as soon as there is a
  host. It holds one query at a time: any other `a=q` takes its place. It
  forgets the query when the program it runs ends and on a full reset
  (RIS).
- The program takes such a reply, whenever it arrives, as detection finding
  a host, if it is one the program can use (Versions, above), and may use
  HOTTY from then on (§14). Without `late=1`, a reply that arrives once the
  program has fallen back changes nothing.
- A program that will no longer take a late answer, such as one about to
  exit, withdraws its query with `a=q:q=2`: a query that wants no answer,
  which takes the held one's place, so that no reply reaches whatever reads
  the terminal after it. A host answers it with nothing, as `q=2` says.

The capabilities, the body of that reply, are a map of these fields (§3.3):

| field | type | meaning |
| --- | --- | --- |
| `v` | str | the HOTTY version the host answers in (Versions, above): `"0.2"` for this document |
| `ops` | [str] | the delta ops it supports (§6) |
| `events` | [str] | the event kinds it can send (§9). `drag` stands for `dragstart`, `drag` and `dragend` (§9.1) |
| `cell` | `{"w": int, "h": int}` | the cell size in device pixels |
| `scale` | float | device pixels per CSS pixel |
| `scheme` | str | `"dark"` or `"light"`: the terminal's colour scheme |
| `limits` | `{str: int}` | the host's limits (§13), such as `{"resources": <bytes>, "surfaces": <count>, "message": <bytes>}` |
| `net` | `{str: [str]}` | the host's network policy (§7.2), from directive to sources, such as `{"img-src": ["https://example.com"]}`. Absent or empty: the host fetches nothing from the network |
| `passthrough` | bool | `true` when the pointer passes through the parts of a surface that take no pointer (§9.3). Absent: every window takes the pointer wherever it is |
| `scroll` | bool | `true` when a document can ask to scroll (`scroll`, §5.1, §5.3). Absent: nothing in a surface scrolls |
| `steps` | bool | `true` when a drag of an element with `data-steps` says where in the element the pointer is (§9.1). Absent: a drag's detail has no `x` or `y` |
| `drop` | bool | `true` when an element with `drop` in its `data-on` can be where a drag goes without being dragged, and a drag says where in it the pointer is when it has `data-steps` (§9.1). Absent: only an element that opts in to drags is ever `t`, and a drag's detail has no `tx` or `ty` |
| `count` | bool | `true` when a repeated click carries its `count` (§9). Absent: every click reads as the first of its run, and a program offers another way to do what a double click would |
| `mod` | str | `"Control"` or `"Meta"`: the modifier `Mod` stands for in bindings (§10.4) |
| `edit` | `{str: [str]}` | the host's edit shortcuts (§10.2), from each action to its keys as §10.4 names them: `{"copy": ["Control+c"], …}`. A host that reports them takes edit commands from a program in the cells (§10.6) |
| `keys` | `{"leader": str, "timeout": int}` | the user's leader, a key sequence, and how long a sequence waits for its next key, in milliseconds (§10.5). Absent: the host reads no key sequences |
| `menu` | bool | `true` when the host shows a program's which-key menus (§10.6) |
| `host` | str | optional: a name for the implementation |
| `version` | str | optional, with `host`: the implementation's version, as dot-separated numbers compared one by one (`"0.0.10"` is after `"0.0.9"`) |

Programs **MUST** ignore fields they do not know.

The capabilities describe the host when it answers. `cell` and `scale`
change during a session, with the terminal's zoom, its font, or the
display it is on (§5.3). A cell's size in CSS pixels, `cell` over `scale`,
changes only with the font, and the host then sends `resize` (§9). A
program that keeps it asks again (`a=q`) then. `mod`, `edit` and `keys`
are the user's, and may change too: the host then sends `caps` (§9).

## 5. Surfaces

A **surface** is one HTML document, named by the program, and at most one
**placement**: a rectangle of cells showing it.

### 5.1 Documents: `a=doc`

```
ESC ] 7279 ; a=doc:s=<name>[:d=1][:scroll=<axes>] ; <HTML> ST
```

- The payload is an HTML document or a fragment, parsed with the HTML parsing
  algorithm. It creates the surface, or replaces its whole document.
- Replacing a document keeps the surface's placement and size.
- `d=1` creates the surface detached (§5.5), so a program that will hear
  nothing from a document, even one it keeps changing with deltas, gives it
  up in the same command. A document sent without `d=1` makes the surface
  the program's, whether it was detached or not.
- `scroll` lets the document scroll (§5.3) along the axes it names, a
  bitmask: `1` vertically, `2` horizontally, `3` both. Absent or anything
  else, it does not scroll. Like `d`, it belongs to the document: a new
  document sent without it does not scroll. A host without `scroll` in its
  capabilities ignores it (§15).
- The document's `<base href>` sets its base URL (§7.3), and its
  `<meta name="hotty-network">` asks for network access (§7.2).
- The host applies its stylesheet (§8) and the security rules (§12) before
  the document is shown.

### 5.2 Placement: `a=place`

```
ESC ] 7279 ; a=place:s=<name>:c=<cols>[:r=<rows>|auto][:x=<col>][:y=<row>][:w=<cols>][:h=<rows>][:z=<n>][:p=1][:f=1][:v=1][:C=1] ST
```

- **Size:** the surface is `c` columns wide and `r` rows tall, and its
  document is laid out at that size (§5.3). Both range from 1 to 1000; a
  missing `r` is `auto`.
- **`r=auto`:** the host lays the document out `c` columns wide and uses the
  smallest number of rows that holds its content, up to 1000. The reply
  reports the rows chosen: `a=ok:…:c=<c>:r=<r>`.
- **The window:** `x`, `y`, `w` and `h` choose the part of the surface the
  placement shows: `w` columns and `h` rows, starting `x` columns and `y`
  rows into the surface. By default `x` and `y` are 0, and `w` and `h` reach
  the surface's right and bottom edges, so a placement with none of them
  shows the whole surface. A window that does not lie inside the surface, or
  that has no cells, is `EINVAL`. The rest of the surface is laid out as
  usual and not shown.
- **Position:** the placement covers the window's `w` × `h` cells, with its
  top-left corner at the cursor's cell.
- **Stacking:** `z` orders placements that overlap, as CSS `z-index` orders
  boxes: a placement with a greater `z` is above one with a smaller, and of
  two with the same `z`, the surface created later (by the `a=doc` that
  created it) is above. `z` is an integer from -1000 to 1000, else `EINVAL`;
  a placement without it has 0. It belongs to the placement: placing the
  surface again without `z` puts it back at 0. Every placement is above the
  cells, whatever its `z`. Where placements overlap, the topmost one under
  the pointer receives it (§5.3).
- **Presses:** with `p=1`, the program hears of every press in the window,
  whatever it lands on, as `press` (§9). Like `z`, it belongs to the
  placement: placing the surface again without it stops them.
- **Fit:** with `f=1`, the program hears `fit` (§9) whenever the number of
  rows the document needs at the placement's width — the rows `r=auto` would
  choose — differs from the rows it last heard. The first it hears are the
  placement's own: `r`, or for `r=auto` the rows chosen, whether or not a
  reply carries them (§3.5). `f` other than `1` is as if absent. A
  document's height changes after it is placed when a resource it refers to
  arrives or is replaced (§7.1), an image or font it fetched loads (§7.2), a
  delta changes it (§6), or a cell's size in CSS pixels changes (§5.3).
  - The placement keeps its size: the footprint is the program's (§11), and
    placing the surface again with the new rows is the program's to do.
  - A host sends at most one `fit` per surface per frame it draws, with the
    rows of the layout drawn in it. A placement the host does not draw,
    scrolled out of view (§5.4), hears of a change once it is drawn again.
    Its order with other events the same change causes, such as `resize`
    (§5.3), is not set.
  - A detached surface sends none (§5.5), and the rows the program last
    heard stay as they were: once a document makes it the program's again,
    it hears how they differ.
  - Like `z`, it belongs to the placement: placing the surface again without
    it stops them, and placing it again with it starts again from the new
    placement's rows.
- **Hover:** with `v=1`, the program hears `hover` (§9.4) each time the
  element the pointer is over in the window changes, and when the pointer
  leaves the window. (`h` is taken: it is the window's rows.) `v` other
  than `1` is as if absent. Like `z`, it belongs to the placement: placing
  the surface again without it stops them.
- **Moving and removing:** placing a surface that is already placed moves
  it, or shows another window of it: the old placement is removed. A program
  scrolling a region of the screen that holds a surface places it again with
  the part in view. A change of window alone does not change the document's
  layout, and a host **SHOULD** make it cheap. `a=del` removes a placement
  (§5.4).
- **The cursor:** unless the command has `C=1`, the host then moves the
  cursor as if by `h` times IND (index) followed by CR. It ends at the start
  of the line below the placement, scrolling if necessary. With `C=1` it does
  not move.

### 5.3 Geometry

- The surface's viewport is its size, `c` × `r` cells, in CSS pixels,
  whatever window of it is shown (§5.2). Media queries and viewport units
  refer to it. The document is laid out at that width, and at that height
  for anything sized by the viewport.
- Only the window is shown, and only the window receives the pointer: where
  windows overlap, the topmost (§5.2, `z`). A press with Alt held is the
  exception: it passes every surface (§9.2). On a host with `passthrough`,
  so does the pointer over the parts of a window that take none (§9.3).
- **What does not fit is clipped, and a surface scrolls only where its
  document asks** (`scroll`, §5.1). Along an axis it did not ask for:
  - The host **MUST** clip overflow as `overflow: hidden` does: the
    document's root, and any element whose `overflow` is `auto` or
    `scroll`.
  - It shows no scrollbars, and keeps every scroll offset at zero,
    whatever the document's CSS or script-free defaults would do (such as
    scrolling a focused element into view).
  - The one exception is a text field's own text, which follows its caret.
  - **A program that needs to scroll** does it the way it scrolls cells:
    it hears the terminal's wheel input (below) and moves its surfaces.
    A surface partly out of view shows its visible part through a window
    (§5.2). So the whole screen scrolls, with its surfaces in it.
- **A scrolling document** scrolls along the axes it asked for as a page
  does in a browser:
  - Its root, and any element whose `overflow` is `auto` or `scroll`,
    scroll their overflow, with the host's scrollbars. CSS
    `scrollbar-width`, `scrollbar-color` and `scrollbar-gutter` apply, and
    a scrollbar takes pixels inside the rectangle, never cells: the
    footprint stays the program's.
  - The user scrolls it with a wheel, a touchpad or a touch drag over its
    window that drags no element (§9.1), and, while the surface has the
    keyboard (§10), with the keys a browser scrolls with and those the
    focused element's keymap binds to a scroll action, but not those it
    gives the program (§10.2). A key a browser scrolls with that can move
    nothing goes on to the program, as every key the surface does not use
    does. Focus scrolls an element into view.
  - A gesture scrolls the innermost element under the pointer that can
    still move that way. Where none can, it goes on outward, and past the
    root to the terminal, as if over the cells beneath (§9), unless CSS
    `overscroll-behavior` stops it there.
  - Scrolling is local: the program hears of it only where it asks, which
    elements are in view (§9.5), and moves it only by focus (§10.1) or by
    bringing an element into view (`reveal`, §6.1). A delta keeps the
    offsets (§6.2), and a new document starts at the top left.
- When the cell size changes, the rectangle keeps its cells and changes
  its pixels:
  - **A zoom**, the user enlarging or shrinking the terminal for the
    moment, or **a display** with another pixel density, changes how many
    device pixels a CSS pixel is. `scale` (§4) follows, so a cell and the
    root font keep their size in CSS pixels, and the document keeps its
    layout, as a page in a frame does under a browser's zoom. The host
    draws it again at the new scale, and the program hears nothing.
  - **The terminal's font**, a new family or size in its settings,
    changes a cell's size in CSS pixels. The host lays the document out
    again, with no involvement from the program, and **SHOULD** send
    `resize` (§9).
- Pixels inside the rectangle **MAY** differ between hosts, as text does
  between fonts. The cell footprint **MUST NOT**.

### 5.4 Lifetime

A placement behaves like a kitty graphics placement:

- It is anchored to the line it was placed on, and moves with it as the
  screen scrolls.
- It is removed when that line leaves the scrollback. The surface's document
  remains, and the program may place it again.
- A placement made on the alternate screen belongs to that screen. It is
  removed when the terminal leaves the alternate screen, and the host
  **SHOULD** delete the surface as well.
- A full reset (RIS) deletes every surface.
- A multiplexer that passes HOTTY through, when the program a pane runs
  ends or it starts another in its place, **SHOULD** delete the surfaces
  and resources that program left, and no other pane's, as a full reset in
  that pane would. Where it keeps the pane's text on the screen, it keeps
  the detached surfaces with it (§5.5). The next program starts a session
  of its own, and cannot know their names.

A program removes a placement and keeps its surface with `a=hide`:

```
ESC ] 7279 ; a=hide:s=<name> ST
```

- The document stays as it is, with what the user did in it, and deltas
  still apply to it. Placing the surface again shows it as it is then,
  without sending it again.
- A program hides the surfaces it expects to show again soon, such as a card
  scrolled out of view, and deletes the rest.
- Hiding a surface that has the keyboard gives the keyboard back to the
  terminal, as `a=blur` does (§10.1).
- `ENOENT` if there is no such surface. Hiding a surface that is not placed
  does nothing.

`a=del` deletes explicitly:

| command | effect |
| --- | --- |
| `a=del:s=<name>` | delete the surface and its placement (`ENOENT` if there is none) |
| `a=del:id=<id>` | delete a resource (§7) |
| `a=del` | delete every surface |

### 5.5 Ownership: `a=detach`

A surface belongs to the program that sent its document: it reports to that
program (§9), and takes the keyboard on its behalf (§10). Once the program
has nothing more to hear from a surface, it **detaches** it:

```
ESC ] 7279 ; a=detach:s=<name> ST
```

or creates it detached, with `d=1` on the `a=doc` that sends its document
(§5.1).

- **A program that leaves surfaces on the screen when it exits**, such as
  the documents a command prints among its output, **SHOULD** detach them
  before it exits, or create them detached. Whatever reads the terminal's
  input after it, a shell for instance, knows nothing of them.
- **What runs a program**, such as a shell, **MAY** detach the surfaces the
  program named once it exits, if it knows their names.
- **A detached surface stays on the screen as text does.** It is placed,
  hidden, changed by deltas and deleted as before, and moves with its line
  (§5.4).
  Nothing in it reaches the program any more:
  - **It sends no events** (§9), of any kind, `press`, `hover` and drags
    included, whatever its placement's `p` and `v` and its `data-on`. A
    drag under way when it is detached ends with nothing more reported
    (§9.1).
  - **It never has the keyboard.** A surface that has the keyboard when it
    is detached gives it back to the terminal, and sends neither `change`
    nor `blur`. A click in it takes nothing, and `a=focus` is `EDETACHED`.
    A program that wants what the user typed in a focused field sends
    `a=blur` first, and detaches once `blur` arrives (§10.1).
  - **Its form controls are disabled**: every `input`, `select`, `textarea`
    and `button`, including those deltas add later, acts as if it had the
    `disabled` attribute. They match `:disabled`, and the user can neither
    focus, edit, toggle nor activate them. What the user had typed into
    them stays. The document itself is unchanged: its elements report the
    program's attributes (§16).
  - **What is local stays** (§9): hover, selecting text, toggling a
    `<details>`, and hyperlinks, which belong to the terminal and open as
    before. Over anything else, the host **SHOULD NOT** show a pointer that
    promises a click (a link's hand), whatever the document's `cursor`
    asks for.
- **Until its next document.** A surface stays detached until an `a=doc`
  without `d=1` replaces its document.
- `ENOENT` if there is no such surface. Detaching a detached surface does
  nothing.

## 6. Deltas

### 6.1 `a=delta`

```
ESC ] 7279 ; a=delta:s=<name>:op=<op>[:t=<element id>][:k=<name>] ; <payload> ST
```

Deltas change one surface's document, addressing elements by id.

| `op` | payload | effect |
| --- | --- | --- |
| `morph` (the default) | HTML | morph the target into the payload (§6.2) |
| `inner` | HTML | morph the target's children into the payload's nodes |
| `replace` | HTML | replace the target with the payload's nodes, without morphing |
| `append`, `prepend` | HTML | insert the payload's nodes as the target's last or first children. A payload element whose id is already a child of the target is morphed where it is, not added again |
| `before`, `after` | HTML | insert the payload's nodes before or after the target |
| `remove` | none | remove the target |
| `attr` | a value | set the target's attribute `k` |
| `unattr` | none | remove the target's attribute `k` |
| `text` | UTF-8 text | replace the target's children with one text node |
| `var` | a value | set the custom property `--k` on the target (a `k` that already starts with `--` is used as is) |
| `reveal` | `start`, `end`, or none | scroll the target into view (below) |

- **Missing arguments:** `t` is required except for `morph`, and `k` for
  `attr`, `unattr` and `var`. A missing one is `EINVAL`, and an unknown op is
  `EINVAL`.
- **A missing target** is `ENOTARGET`, with the id as the detail.
- **Context:** a payload is parsed as a fragment in the context of the
  element it will become a child of, so table rows, cells and list items
  parse as they would in place.
- **The cheap path:** `var` and `text` are the deltas that change every
  frame (a bar's width, a clock). A host **SHOULD** make them cheap.
- **Reveal** changes no node. It scrolls each box that holds the target,
  the innermost first and the document's root last, so that the target's
  border box is in view: its top at the top of each box with `start`, its
  bottom at the bottom with `end`, and with no payload, by as little as
  brings it into view, as a browser's `scrollIntoView` does with
  `block: "nearest"`. Across, it always scrolls as little as it can. It
  scrolls only what scrolls (§5.3): in a document that asked for no
  scrolling, it moves nothing. It moves neither focus nor the keyboard
  (§10), and sends no event of its own: elements that report whether they
  are in view report it as after any scroll (§9.5). Another payload is
  `EINVAL`.

### 6.2 Morph

Morphing keeps the identity of elements that stay: their focus, the text a
user is typing, their scroll position, and whether a `<details>` is open.
Morphing a live node *old* into a parsed node *new*:

1. **Two text nodes:** if the data differs, set old's data to new's. Two
   comments: leave old as it is.
2. **Two elements match** when their tag name and namespace are equal and
   their `id`s are equal or absent on either side. Then:
   - make old's attributes equal to new's: add the missing ones, change the
     different ones, and remove the extra ones;
   - if old is the focused element, leave its `value` as it is;
   - morph old's children into new's (step 4).
3. **Otherwise**, replace old with new.
4. **Children.** For each of new's children, in order, find an old child:
   - A new child with an `id` takes the old child with that id, if any.
   - A new child without an `id` takes the first old child after the last
     match that is the same kind of node: an element with the same tag and no
     id, a text node, or a comment. Old children whose id the new list still
     wants are skipped.

   Then:
   - Old children not taken are removed.
   - Taken children are morphed and put in the new order, moved rather than
     recreated.
   - New children with no match are inserted.

**Controls whose values the program sets.** When an attribute that
sets a control's default changes (`value` on inputs, textareas and selects;
`checked` on checkboxes and radio buttons; `selected` on options), the host
**MUST** also set the control's current state to it, unless the control is
focused. The program's value wins, except while the user is editing.

**`morph` without `t`** matches each top-level element of the payload to the
document element with the same id, and morphs it. Elements whose id is not in
the document are skipped and reported in one `ENOTARGET`, their ids
comma-separated in the detail. The others are still applied. This lets a
program that redraws its whole tree every frame keep the terminal-side state
of what did not change.

**A payload with other than one top-level element**, given to `morph` with a
`t`, replaces the target with all of its nodes.

### 6.3 Order and transactions

- The host applies commands in the order they arrive. It **SHOULD** render
  at most once per display frame.
- For atomicity, a program brackets a batch in synchronized output (DEC
  private mode 2026: `CSI ? 2026 h` … `CSI ? 2026 l`). The host **MUST NOT**
  show a state from inside the batch. It may hold commands until the batch
  ends, or apply them without drawing.
- A host that gives up waiting for the end of a batch (terminals time these
  out) **MAY** apply what it holds.

## 7. Resources

A surface loads what the program sent it (§7.1), and from the network only
what the network policy allows (§7.2).

### 7.1 In-band resources

```
ESC ] 7279 ; a=res:id=<id>:type=<MIME type> ; <bytes> ST
```

A **resource** is named bytes with a MIME type, stored per session: a
stylesheet shared by several surfaces, an image, a font.

- **References:** documents refer to a resource as `cid:<id>` (RFC 2392's
  scheme, as HTML e-mail refers to its attachments). A host **MUST** resolve
  `cid:` in URL-valued attributes (`src`, `srcset`, `href` of
  `<link rel=stylesheet>`, `poster`, SVG `href`) and in CSS `url()` and
  `@import`. Those include inline `style` attributes, `<style>` elements and
  stylesheet resources.
- **Updates:** sending a resource again replaces it, and every surface that
  refers to it is drawn again. `a=del:id=<id>` deletes it, after which
  references to it fail as if missing.
- **Late arrival:** a reference to a resource that does not exist yet is
  resolved when it arrives. A placement made with `f=1` hears whether that
  changed the document's height (§5.2).
- **Quota:** the host reports its quota under `limits.resources`. A resource
  that would exceed it is refused with `EQUOTA`. A resource is one message,
  so `limits.message` (§13) also caps the largest resource the host takes.
- **The program's values stand:** a host that rewrites references in order
  to load them (to `blob:` URLs, say) **MUST** still treat the attribute as
  having the program's value: in morphs, in `inspect` (§16), and in event
  details.

### 7.2 The network

The **network policy** decides what a surface may fetch from the network. It
has two halves, and a URL may be fetched only when both allow it.

**The host's half** is what the host allows. Its user sets it, or the page
that embeds it. It lists **sources** per **directive**:

| directive | covers |
| --- | --- |
| `img-src` | images: `<img>`, `srcset`, `<picture>`, `poster`, images in SVG, and images in CSS |
| `media-src` | `<audio>` and `<video>` |
| `font-src` | `@font-face` |
| `style-src` | stylesheets: `<link rel=stylesheet>` and `@import` |

- A source is an origin, `http` or `https` with an optional port
  (`https://example.com`, `http://localhost:8080`), or `https:`, which
  matches every HTTPS origin.
- A host's policy is empty unless its user or embedder grants something.
  The host reports it in its capabilities (`net`, §4).
- A host run by a person (a terminal) **SHOULD** start with an empty policy.
  Every fetch tells a server that the document is being shown, and where
  from; that is the user's decision.

**The document's half** says what it needs:

```html
<meta name="hotty-network" content="img-src https://example.com; font-src https:">
```

- The syntax is CSP's: directives separated by `;`, each followed by its
  sources separated by spaces.
- A document with no such element asks for nothing, and fetches nothing
  from the network.

**Fetching:**
- A host **MUST NOT** fetch a URL unless a source in each half matches it,
  for the directive that covers it.
- It **SHOULD** send no referrer and no credentials (cookies,
  authorization) with what it fetches.
- A reference the policy does not allow fails as a missing resource does.
- What is fetched arrives after the document is laid out, as a late
  resource does (§7.1), and changes its height the same way: a program that
  sizes a surface by its content places it with `f=1` (§5.2).
  The program's value still stands (§7.1).

### 7.3 The base URL

- A document's base URL is the `href` of its first `<base>` element when
  that is an absolute `http` or `https` URL, and `https://hotty.invalid/`
  otherwise. Relative references resolve against it: for fetching, still
  subject to §7.2, and for links (§9). A form's empty `action` resolves
  too, and goes nowhere (§9).
- The base URL grants nothing by itself: a fetch needs the network policy,
  and nothing navigates.

## 8. The host stylesheet

Every surface gets a stylesheet from the host that hands it the terminal's
look. Its rules **MUST** lose to any rule in the document, as a user-agent
stylesheet's do; a cascade layer below all author styles achieves this. It
contains at least:

```css
:root {
  color-scheme: dark;              /* or light: the terminal's */
  --hotty-fg: …;                   /* the terminal's foreground */
  --hotty-bg: …;                   /* and background */
  --hotty-ansi-0: …;               /* … the 16 ANSI colours … */
  --hotty-ansi-15: …;
  --hotty-accent: var(--hotty-ansi-12);  /* dark; ansi-4 when light */
  --hotty-cell-w: …px;             /* one cell, in CSS pixels */
  --hotty-cell-h: …px;
  --hotty-font: <the terminal's font family>, monospace;
  font-family: var(--hotty-font);
  font-size: <the terminal's font size>;
  line-height: var(--hotty-cell-h);  /* so 1rlh is one row */
  color: var(--hotty-fg);
  background: var(--hotty-bg);
  overflow: hidden;                /* §5.3 */
  accent-color: var(--hotty-accent);
}
body { margin: 0; }

/* Controls in the terminal's colours. :where() keeps this rule below the
   state rules after it, such as :disabled. */
:where(input:not([type=checkbox], [type=radio], [type=range]), textarea,
       select, button) {
  color: var(--hotty-fg);
  background: var(--hotty-bg);
  border: 1px solid var(--hotty-ansi-8);
}
button:enabled, input:is([type=button], [type=submit], [type=reset]):enabled {
  background: var(--hotty-ansi-8);
}
::placeholder, :disabled { color: var(--hotty-ansi-8); }
:focus-visible { outline: 1px solid var(--hotty-accent); }
:any-link { color: var(--hotty-accent); }
::selection { color: var(--hotty-bg); background: var(--hotty-accent); }
```

- `prefers-color-scheme` follows the terminal's scheme.
- **The palette dresses the controls.** Fields, buttons, checks, focus,
  links and selected text take the terminal's colours, not the engine's,
  so they look the same on every host and like the terminal around them.
  A document that styles its own controls wins, as with every rule here.
  - `--hotty-accent` is the terminal's blue: `--hotty-ansi-12` when the
    scheme is dark, `--hotty-ansi-4` when it is light, as plain blue is
    hard to read on most dark backgrounds. A document may use it as the
    terminal's accent.
  - `ansi-8` (bright black) is the dim grey themes give for secondary
    text: borders, buttons, placeholders and what is disabled. A disabled
    button keeps the background, so its text stays legible.
- When the terminal's theme or font changes, the host updates the
  stylesheet and draws every surface again. A zoom changes neither
  `--hotty-cell-*` nor `font-size`: the host draws every surface again at
  the new scale (§5.3).

The custom-property prefix `--hotty-` and the attribute prefix `data-hotty-`
are reserved for this specification.

## 9. Events

```
ESC ] 7279 ; a=ev:s=<name>:e=<kind>:t=<element id> [; <base64 msgpack detail>] ST
```

The host reports what the user did. Events are not replies: they are sent
whatever the value of `q`. Like replies (§3.6), they arrive on the program's
input, interleaved with the user's keys, so a program that places surfaces
reads HOTTY messages from its input. A detached surface sends none (§5.5).

| `e` | when | detail |
| --- | --- | --- |
| `click` | activating a `button`; an `a` or `summary`; an `input` of type `button`, `submit` or `reset`; or any element with `data-on~=click` | `{"area": area}`, the element's cells (below); with `"href": str` and `"url": str` for links (below), `"value": str` when the element has a `value` attribute, and `"count": int` for a repeated click (below) |
| `change` | a checkbox or radio button toggled, or an option of a `select` picked (§10.2), at once; a text control or `textarea` whose value changed, when the change is committed (focus leaves it, including when the surface loses the keyboard) | `{"checked": bool, "value": str}` for checkboxes and radio buttons, `{"value": str}` otherwise |
| `input` | every edit of a control with `data-on~=input` | `{"value": str}` |
| `submit` | a form submitted (a submit button, or Enter in a text field) | the form's fields, `{str: str}` from names to values, the submitter's included |
| `press` | the primary button pressed, a tap, or a touch that becomes a drag (§9.1), anywhere in the window of a surface placed with `p=1` (§5.2), except a mouse's or a pen's press with Alt held (§9.2) and where the pointer passes through (§9.3) | `{"area": area}`, the cells of the element `t` names (below); none when `t` is empty |
| `dragstart` | a mouse's or a pen's primary button pressed, or a touch that drags (§9.1), on an element with `data-on~=drag`, without Alt (§9.2) | `{"c": int, "r": int, "keys": [str]}`: the pointer's cell and the keys held, with `"x": int` and `"y": int`, its step, on an element with `data-steps` (§9.1) |
| `drag` | during a drag, the element under the pointer changed, or the pointer's step in the dragged element or in `t` (§9.1) | the same, with `"tx": int` and `"ty": int`, the step in `t`, where `t` has `drop` in its `data-on` and `data-steps` (§9.1) |
| `dragend` | the drag ended: the button released or the finger lifted, wherever the pointer is (§9.1) | as for `drag` |
| `focus` | the user focuses an element: the surface gains the keyboard, or its focus moves to another of its elements (§10.1); `t` names the element focused | none |
| `blur` | the surface loses the keyboard (§10); `t` is empty | none |
| `resize` | the surface's size in CSS pixels changed without its cells changing: the terminal's font changed (§5.3); `t` is empty | `{"w": float, "h": float}` in CSS pixels |
| `fit` | on a placement made with `f=1` (§5.2), the rows the document needs at the placement's width changed; `t` is empty | `{"r": int}`: the rows `r=auto` would choose now |
| `hover` | on a placement made with `v=1` (§5.2), the element the pointer is over changed, or the pointer left the window (§9.4) | `{"c": int, "r": int}`: the pointer's cell (§9.1); `{"out": bool}`, `true`, when it left, with `t` empty |
| `view` | which elements with `data-on~=view` are in view, or where they are, changed, or whether the document shows its end (§9.5); `t` is empty | `{"in": {str: area}, "end": bool}`: each element in view by its id, with its cells (below) |
| `command` | a key of an edit command the program takes, or a menu of the terminal (§10.6) | `{"name": str, "key": str}`, with `"text": str` for a paste |
| `caps` | `mod`, `edit` or `keys` changed (§4) | the fields that changed, as the capabilities have them. One that became absent comes as its type's empty value: `"edit": {}`, the host takes no edit commands now (§10.6), and `"keys": {}`, it reads no key sequences (§10.5). `mod` is never absent |

- **Events of the terminal,** `command` and `caps`, belong to no surface,
  and have neither `s` nor `t`.
- **The element that reports** a `click` is the nearest one, from the target
  of the click outward, that is one of those kinds. If it has no `id`,
  nothing is reported: the id is the program's handle. A link is the
  exception: its `href` is the handle, and `t` is then empty.
- **Where the element is.** A `click`'s and a `press`'s `area`, and each
  of a `view`'s, is `{"c": int, "r": int, "w": int, "h": int}`: the cells
  the element's border box covers as the user sees it, scrolled (§5.3)
  included. `c` and `r` are the first column and row it touches, counted
  from 0 at the surface's top left cell as a drag's are (§9.1), and `w` and
  `h` the columns and rows it spans. An element partly clipped or scrolled
  away reports its whole area, so `c` and `r` may be negative or past the
  surface. A click from the keyboard carries it too. A program places what
  belongs next to the element by it, as a browser places a select's list
  or a menu by its control.
- **Repeated clicks.** A click that quickly follows another on the same
  element carries `count`: its place in that run of clicks, 2 for the
  second click of a double click, 3 for the third of a triple click. The
  host counts as its platform does, by the user's own settings for how
  quickly and how close together the clicks come, and not by a time of
  its own. Every click of a run is reported: a double click is a `click`,
  then a `click` with `"count": 2`. A click on another element, or on
  another surface, starts a new run. A click without `count` is the first
  of its run, and so is every click from the keyboard. A host that counts
  clicks reports `count` (§4).
- **A press** is reported whatever it lands on: a control, an element with
  a handler, plain text, or empty space. `t` is the id of the nearest
  element that has one, from the pressed element outward, and empty if
  none has. It comes before every other event the press causes, on this
  surface or another (`change`, `blur`, `focus`), and so before the `click`
  its release may make. A press the host takes for a hyperlink's own
  gesture (below) is the terminal's, and is not reported, and neither is
  a press with Alt held (§9.2), which is the program's.
- **Links.** A link's detail carries `href`, the program's value, and `url`,
  the `href` resolved against the document's base URL (§7.3). `url` is
  absent when it would be under `https://hotty.invalid/`.
- **A surface never navigates.** A click on a link is an event, and the
  program decides what it means: it may show another page, or ask its
  platform to open the link. The host never opens a link itself, whatever
  the gesture, except a hyperlink (below). Forms never submit anywhere:
  `submit` is all that happens.
- **Hyperlinks.** A link with `target="_blank"` is a hyperlink, as OSC 8
  makes one of text in cells. It belongs to the terminal, not the program.
  The host **MUST** treat it exactly as it treats an OSC 8 hyperlink:
  - the same gesture opens it;
  - hovering it gives the same feedback, such as the pointer and the
    address;
  - the same policies apply, such as the schemes it opens, a confirmation,
    and a setting that turns hyperlinks off.

  Its address is its `url`: a link without one is not a hyperlink. A click
  on a hyperlink is not reported.
- **Local behaviour stays local.** HTML's own default actions happen in the
  host without a round trip:
  - focus, the caret and typing in text fields;
  - toggling checkboxes, radio buttons and `<details>`;
  - hover, and the pointer's shape: `:hover` needs no program (a
    placement may still ask to hear where the pointer is, §9.4). Over a
    surface, a host that shows a pointer shows the one the document asks
    for (CSS `cursor`, and as in a browser, a pointer over a link and a
    text cursor over text). Over a hyperlink it shows what it shows over
    an OSC 8 hyperlink;
  - selecting text, where CSS `user-select` allows it (§11).
- **Gestures that scroll are the terminal's,** except over a document that
  scrolls (§5.3), which takes them while it can move that way. A wheel, a
  touchpad's scroll, or a touch drag over any other surface, unless it
  drags an element (§9.1), does what it would do over the cells beneath
  it. That is scrollback, or on the alternate screen, the program's wheel
  input. The host **MUST** pass them on, with the position of the pointer
  or the finger. Taps and long presses, and clicks and drags (§9.1) that
  do not begin with Alt held (§9.2), stay the surface's.
- **The detail** is a msgpack map (§3.3), base64-encoded. Values are the
  program's (§7): an `href` is reported as the document has it.
- **Unknown kinds.** A program **MUST** ignore an event whose kind it does
  not know: later versions add kinds (§15). The capabilities list the kinds
  a host sends (`events`, §4).

### 9.1 Drags

An element opts in to drags with `drag` in its `data-on`, as it opts in to
clicks with `click`. A **drag** is a press of a mouse's or a pen's primary
button on such an element, the moves of the pointer while the button is down,
and its release; or a touch on such an element that does not pan (below), the
finger's moves, and its lift. A program hears through drags what a click
cannot carry: a range dragged across a grid, a handle dragged to where it is
let go. An element that is only a place to drop on opts in with `drop`
(below): a drag can go to it, and it is never dragged itself.

- **Three events:**
  - `dragstart`, on the press (a touch's once it drags, below). `t` is
    the element that opted in: the nearest one, from the pressed element
    outward, with `drag` in its `data-on`. If it has no `id`, there is no
    drag.
  - `drag`, each time the element under the pointer changes. `t` is the
    nearest element with an `id` and `drag` or `drop` in its `data-on`,
    from the one under the pointer outward, and empty where there is none,
    outside the window included. While `t` is empty, a `drag` is sent each
    time the cell under the pointer changes instead. A `drag` is also sent
    each time a step (below) changes: `x` or `y` in the element dragged,
    `tx` or `ty` in `t`. A move that changes several of these, the element
    or the cell included, sends one.
  - `dragend`, once, on the release, wherever the pointer is. `t` is as
    for `drag`.

  A drag therefore costs a few events for each element it crosses, and one
  for each step, not one for every move.
- **The detail** of each is `{"c": int, "r": int, "keys": [str]}`, with
  `"x": int` and `"y": int` on an element with steps, and in `drag` and
  `dragend`, `"tx": int` and `"ty": int` where `t` is a drop target with
  steps (below):
  - `c` and `r` are the column and the row of the surface under the
    pointer, counted from 0 at the surface's top left cell, not its
    window's (§5.2). They go on counting outside the surface: negative
    above it and to its left, its size or more below it and to its right.
    A program that scrolls while the pointer is past an edge knows how far
    past it the pointer is.
  - `keys` are the modifier keys held: a list of `"shift"`, `"ctrl"`,
    `"alt"` and `"meta"`, in that order, empty when none is. `"alt"` is
    never in `dragstart`'s: a press with Alt held starts no drag (§9.2).
    Alt pressed later is reported, and the drag goes on.
- **Where in the element: steps.** An element that opts in to drags, or to
  drops, may say how many steps its width and its height are divided into, with
  `data-steps="<x>"` or `data-steps="<x> <y>"`: whole numbers from 0 to
  2^53 − 1 (§3.3), `0` for none along that axis. A slider from 0 to 20
  has `data-steps="20"`, a vertical one `data-steps="0 20"`. Each event of a drag of it then says where in
  it the pointer is:
  - `x`, when the first count is not 0: the pointer's distance from the
    left edge of the element's border box, over the box's width, times
    the count, rounded to the nearest whole number (a half up), and
    clamped to 0 and the count. A box with no width gives 0.
  - `y`, when the second count is not 0: the same, from the top edge, over
    its height.

  The element is the one `dragstart` names, whatever `t` says later, and
  its box is where the user sees it at the time, scrolled (§5.3)
  included. The step is measured against it wherever the pointer is: over
  another element, outside the surface, or outside the window. So a
  slider follows a finger that slips off its track until it lifts, as a
  browser's range input does. Its counts are the ones it has when the
  drag starts. A value that is not one or two whole numbers in that range
  gives no steps. If the element leaves the document during the drag, `x`
  and `y` stay as they last were, as they do in a `dragend` that ends a drag
  early (below). `steps` in the capabilities (§4) says a host does this.
- **Where in the target.** When `t` has `drop` in its `data-on` (below)
  and steps, `drag` and `dragend` also say where in `t` the pointer is:
  `tx` and `ty`, measured against `t`'s border box as `x` and `y` are
  against the dragged element's, by the counts `t` has at that moment. So
  a list splits a row with `data-on="drag drop"` and `data-steps="0 1"`
  into halves, for an item to land before or after it, and a tree splits a
  folder with `data-steps="0 2"` into before, into and after: a quarter, a
  half and a quarter. Where `t` is empty, has no `drop` or has no steps,
  there is no `tx` or `ty`, so a slider's drag over itself carries only
  `x`; a `dragend` that ends a drag early (below) has none either. `drop`
  in the capabilities (§4) says a host does this.
- **A place to drop on.** An element with `drop` in its `data-on` and an
  `id` can be `t` without being dragged. A press on it starts no drag of it
  (one of an element around it that opts in to drags starts as before), and
  its text can be selected as any other's (§11). An element with both is
  dragged and dropped on. `drop` in the capabilities (§4) says a host does
  this; where it is absent, only an element that opts in to drags is ever
  `t`, and a program offers another way to do what a drop would.
- **The pointer is the surface's until the release,** or the finger until
  it lifts, as a page's `setPointerCapture` makes it an element's. Every
  move goes to the drag, wherever the pointer is: over the cells, over
  another surface, or outside the terminal's window where the platform
  allows it. None of it reaches anything else: no other surface, no
  `hover` (§9.4), and no mouse reporting to the program.
- **A drag selects no text.** A press on an element that opts in starts no
  text selection, whatever its CSS, as if it had `user-select: none` (§11).
- **A touch drags only an element that opts out of panning.** A touch on an
  element that opts in is a drag, rather than a scroll, when the
  `touch-action` that Pointer Events determine for the touched element
  allows no pan along the touch's first move. That value is the touched
  element's own, with its ancestors', up to and including the nearest
  element that scrolls (§5.3), as the document's CSS sets them: what a host
  sets for its own handling of touch does not count. The host takes the
  first move once the touch has gone past its tap slop, along the larger of
  the two deltas, a tie counting as a pan. `pan-x` allows a horizontal pan,
  `pan-y` a vertical one, and `auto` and `manipulation` both; `pan-left`
  and `pan-right`, or `pan-up` and `pan-down`, count as their axis where
  the host's CSS engine parses them, which not every engine does. Any
  other value, `none` and `pinch-zoom` included, allows neither. Elsewhere
  `touch-action` changes nothing: a touch that does not drag pans as §5.3
  and §9 say.
  - Where the value allows both pans, as the initial `auto` does, nothing
    changes: a touch drag scrolls (§9), and a tap is a click, which only
    `click` reports.
  - **A touch presses when it becomes a drag,** and at that moment is a
    press as a mouse's is (Order, below): `press`, if the placement asked
    for it, then `dragstart`, both for where the touch began (its cell,
    and its step), then everything else the press causes. If the finger
    is by then over another element than the one `dragstart` names (or,
    where that names none, another cell), or at another step, a `drag`
    for where it is follows.
  - **A touch the host takes as a pan** presses nothing, and stays a pan to
    its end.
  - **A touch that lifts before going past the slop** is a tap, or a long
    press if held past the host's long-press time. Each is what it is on
    any other element (§9): a tap presses at its lift. A long press never
    becomes a drag.
  - **Alt.** A touch that begins with Alt held is never a drag. `keys` are
    the modifier keys held on a keyboard when the finger touched, and as
    for a mouse after.
- **Order.** The press that starts a drag is a press like any other
  (§10.1). `press`, if the placement asked for it, comes first, then
  `dragstart`, then everything else the press causes (`change`, `blur`,
  `focus`). On the release, `dragend` comes before any `click`.
- **A drag is a click only where it began.** When it ends on the element
  it started on (the nearest element with an `id` and `drag` in its
  `data-on`, from the one under the pointer outward, is `dragstart`'s `t`;
  without `drop`, that is `dragend`'s `t`), its release is the click it
  would have been without the drag: an element with `click` in its
  `data-on` as well reports `click`, after `dragend`. A drag that ends
  anywhere else reports no `click`. So does a touch's: one that lifts on
  the element it began on reports `click` after `dragend`.
- **What ends a drag early.** The host sends `dragend` at once, with `t`
  empty and the last cell the pointer was on, when before the release:
  - the surface's placement goes away (`a=hide`, or its line leaving the
    screen);
  - a new document replaces the surface's (`a=doc`);
  - the host loses the pointer;
  - or, in a touch's drag, a second finger touches. The surface hears
    nothing more of the gesture until every finger lifts, and what the
    host does with it is its own. A second finger before a touch drags
    makes it no drag.

  A surface that is detached or deleted during a drag reports nothing more
  (§5.5). Nothing else ends a drag: neither a delta nor a new placement
  (moving the surface, or showing another window of it).
- **Detection.** `drag` in `events` (§4) stands for the three kinds. Where
  it is absent, a program offers another way to do what its drags do, such
  as keys or clicks.

### 9.2 Presses with Alt

A press of the primary button with Alt held is the program's, never a
surface's. Wherever it lands, in any window and whatever its `z`, the host
handles it as a press on the cells beneath the surface.

- **With mouse reporting on,** the program hears it as it hears a press on
  the cells, Alt included: in the SGR encoding, `CSI < 8 ; <col> ; <row> M`.
  With mouse reporting off, the terminal does what it does with such a
  press on the cells, such as starting a rectangular selection.
- **The surface hears nothing of it.** No `press`, whatever `p` asked for,
  no `dragstart`, and no `click` on its release. It takes no focus, starts
  no selection, and opens no hyperlink. The surface under the pointer is no
  longer hovered: the pointer has left its window (§9.4).
- **The keyboard** goes back to the terminal, as on a click on the cells
  (§10.1): a surface that had it sends `blur`.
- **The gesture is the program's until the release.** Every move and the
  release go where those of a press on the cells go, over any surface, and
  none of them reaches a surface.
- **The press decides,** and the keys held later change nothing. A drag
  that a press without Alt began stays the surface's when Alt is pressed
  during it (its `keys` then list `"alt"`, §9.1). A gesture that a press
  with Alt began stays the program's when Alt is let go.
- **On macOS, Alt is Option**, whether or not the terminal makes Option
  type as Alt for keys (Ghostty's `macos-option-as-alt`, say). That setting
  is about text, and a press has none.
- **Mouse and pen only.** A tap is a click whatever the keys held, and a
  touch with Alt held scrolls (§9.1).

### 9.3 Where the pointer passes through

A surface that only shows something, such as a frame drawn around cells,
should not keep the pointer from them. On a host that reports
`passthrough` (§4), a surface takes the pointer only where an element is
there for it: where CSS hit testing finds an element at the point, as a
browser's does. Hit testing skips every box whose `pointer-events` is
`none`; the property inherits, so `html { pointer-events: none }` makes a
surface take no pointer, and an element in it with `pointer-events: auto`
takes it back over its own box.

Where a window takes no pointer, the pointer **passes through** it, as if
the window were not there:

- **To what is below:** the topmost other window at that point that takes
  the pointer there, or else the cells. Over the cells, the terminal does
  what it does with the pointer over cells: with mouse reporting on, the
  program hears presses, releases and motion as it hears them over cells
  (the SGR encoding, say), and the pointer has the shape the terminal
  gives the cells (the one the program set with OSC 22, for instance).
- **The press decides,** as in §9.2: a gesture whose press passed through
  is not the surface's until its release, wherever the pointer goes, and a
  gesture whose press a surface took (a drag, §9.1) stays that surface's
  over the parts that take no pointer.
- **The surface hears nothing of it:** no `press`, whatever `p` asked for,
  no `dragstart` and no `click`; it takes no focus and starts no selection.
  A press passing through takes the keyboard back as a click on the cells
  does (§10.1). The pointer there hovers nothing in the surface, and
  `:hover` matches nothing under it: it is out of the window (§9.4).
- **Gestures that scroll** reach the cells as everywhere (§9).

A host without `passthrough` gives a window the pointer wherever it is
(§5.3). A program that relies on the cells under a surface hearing the
pointer checks for `passthrough`, and otherwise keeps its surfaces off the
cells whose pointer it needs.

### 9.4 Hover

Hover stays local (§9): `:hover` and the pointer's shape need no program.
A program that asks, with `v=1` on a placement (§5.2), also hears where the
pointer is over the window, element by element: to show a hint of its own
for what is under it, or to know that the pointer has gone from what the
program draws itself, such as cells it lit while the pointer was over them.

- **Over the window.** `hover` is sent each time the element the pointer
  is over changes. `t` is the nearest element with an `id`, from the one
  under the pointer outward (the innermost one `:hover` matches), and
  empty where none has an id. The detail is `{"c": int, "r": int}`, the cell
  of the surface under the pointer, counted as for drags (§9.1): from the
  surface's top left cell, not its window's.
- **Out.** `hover` with `t` empty and the detail `{"out": true}` is sent
  when the window loses the pointer. A window has the pointer while it
  receives it (§5.3): the pointer is in it, it is the topmost window there,
  and on a host with `passthrough` it takes the pointer at that point
  (§9.3). It loses the pointer when the pointer:
  - moves onto the cells, or onto another window;
  - moves onto a part of it that lets the pointer through (§9.3);
  - leaves the terminal's window, or the host loses it otherwise;
  - is pressed with Alt (§9.2): the gesture is the program's, and hovers
    nothing until its release.

  The pointer is in at most one window at a time. Moving from one window
  to another, the first one's out comes before the second one's `hover`.
- **Only changes.** A `hover` is sent when `t`, or whether the window has
  the pointer, differs from what the program last heard: neither a move
  within an element nor a new cell sends one. A placement made with `v=1`
  starts from out. A host **MAY** send only the last of the changes
  between two frames it draws, so at most one per surface per frame.
- **A held button holds hover.** From a press a surface takes to its
  release, no surface sends `hover`: the pointer is the gesture's, and a
  drag reports its own targets (§9.1). At the release, the surface reports
  where the pointer is now, if that differs from what the program last
  heard, after every other event of the release (`dragend`, `click`,
  `change`, `focus`, `blur`). A window the pointer is then in, another one
  included, reports it at the pointer's next move. A press itself sends no
  `hover`.
- **Mouse and pen.** A touch's moves scroll (§9), or drag (§9.1), and
  hover nothing. At a tap's release, or the lift that ends a touch's drag,
  a host **MAY** report what the finger was on, as browsers leave `:hover`
  on what a tap touched.
- **Not the keyboard's.** Focus moving, to the surface or away from it,
  changes nothing: a window reports the pointer whether or not it has the
  keyboard (§10).
- **Under a pointer that does not move.** When a delta, a new document, a
  resource, or a new placement changes what lies under a pointer that has
  not moved, a host **MAY** report it only at the pointer's next move.
- **Lifetime.** Like `p`, it belongs to the placement: placing the surface
  again without `v=1` stops it, and so does hiding it. Placing it again
  with `v=1` goes on from what the program last heard, or from out if the
  placement before did not ask. A new document keeps it, and what the
  program last heard: an element with the same id under the pointer is
  not reported again. A detached surface sends none (§5.5); once a document
  makes it the program's again, it hears how the pointer differs from what
  it heard last.
- **Detection.** `hover` in `events` (§4). Where it is absent, a program
  never hears that the pointer has left for a surface, and does not keep a
  state of its own that waits for it: it clears it on the next thing it
  hears instead, a key or a press.

### 9.5 View

Scrolling is local (§5.3). A program that marks elements with
`data-on~=view` hears which of them are in view, as a browser's
`IntersectionObserver` tells a page: to mark the section a reader is in, as
a table of contents does, or to fetch what comes into view.

- **In view.** An element with `view` in its `data-on` and an `id` is in
  view while some of its border box is shown: inside the window (§5.2), and
  neither scrolled away nor clipped by a box that holds it (§5.3). One that
  is not rendered (`display: none`, `visibility: hidden`) is not in view,
  and one without an `id` is never reported.
- **The event.** `view`, with `t` empty, carries `{"in": {str: area},
  "end": bool}`: each element in view, by its id, with its area as a
  click's (§9), the whole of it however little is shown; and `end`,
  `true` when the document's root is scrolled as far down as it goes, as
  a root that does not scroll down always is. It names every element in
  view, not what changed.
- **When.** A host sends `view` once the document is laid out in a
  placement, and then each time what it would carry changes: an element
  comes into view or leaves it, an area changes, or `end` does. A scroll
  changes the areas as it moves, so while one moves, a gesture with its
  momentum or a smooth scroll, the host waits for it to come to rest and
  sends one `view` then. Otherwise it sends at most one per surface per
  frame it draws, with the layout drawn in it. A document with no element
  that asks sends none.
- **Lifetime.** It belongs to the placement, as `fit` does (§5.2): a
  placement the host does not draw, scrolled out of view (§5.4), hears of
  a change once it is drawn again; hiding the surface stops it; placing it
  again sends one as the first. A new document sends one once it is laid
  out. A detached surface sends none (§5.5).
- **Detection.** `view` in `events` (§4). Where it is absent, a program
  that needs to know what is shown draws that part in cells, or takes the
  element it last brought into view (`reveal`, §6.1) as the one shown.

## 10. Keyboard and focus

### 10.1 Who has the keyboard

A surface **has the keyboard** when the user clicks an element in it that
takes focus, or the program gives it with:

```
ESC ] 7279 ; a=focus:s=<name>[:t=<element id>] ST
```

- **With `t`:** the element is focused (`ENOTARGET` if there is none).
- **Without `t`:** the surface's focused element keeps focus, or else the
  first focusable element receives it.
- **Echo:** no `focus` event is sent for focus the program gave.
- **The host says where the user puts focus.** Each time the user focuses
  an element of a surface, by a click or with Tab (§10.2), whether the
  surface had the keyboard or not, the host sends `focus`. Its `t` is the
  id of the nearest element that has one, from the focused element
  outward, and empty if none has. So a program knows which element the
  keys it is given come from (§10.2, *Keys for the program*). The `change`
  that focus leaving a text control commits comes first, and a click's
  `press` before both (§9).
- **A click** is a press of the primary button without Alt (§9.2), a
  tap, or a touch that becomes a drag (§9.1).
- **Elements that take focus** on a click, unless they are disabled:
  - `input`, `select`, `textarea` and `button`;
  - links with an `href`, except hyperlinks (§9), which are the terminal's
    whatever their `tabindex`;
  - the first `summary` of a `details`;
  - editing hosts (`contenteditable`);
  - any element with a `tabindex` of 0 or more.

  A click on a `label` is a click on its control.
- **A click on anything else takes nothing.** On a surface with no such
  element a click never takes the keyboard, and no `focus` is sent: every
  key would reach the program anyway (§10.2). A program that needs to know
  the user went to the surface all the same places it with `p=1`, and
  hears `press` (§9).
- **A click elsewhere gives the keyboard back** to the terminal: on the
  cells, on another surface, or inside this one on an element that does not
  take focus. The host sends `blur`.
- **A detached surface** (§5.5) never has the keyboard: `a=focus` is
  `EDETACHED`, whatever its `t`, and `a=blur` does nothing.

The program takes the keyboard back with `a=blur:s=<name>`. The focused
control commits its value first (a `change` may follow), and then `blur` is
sent.

### 10.2 Keys

While a surface has the keyboard, each key either goes to its focused element
or reaches the program. The surface is offered the key as the user pressed
it, before the terminal's own shortcuts, and then, if it does not use it,
as the program would read it (§10.4). A key the terminal turns into
other input, such as a binding that sends text or a key the user remapped,
is offered the second time as the key that input reads as.

| focused element | keys it uses |
| --- | --- |
| text field: an `input` of type `text`, `search`, `url`, `tel`, `email`, `password` or `number` (or a type the host does not know, which is `text`), a `textarea`, an editing host (`contenteditable`) | the keys its keymap binds, and printable characters (below) |
| an `input` of a date or time type | printable characters, Space, Backspace, Delete, the arrows, Home, End, Page Up, Page Down, Enter, unmodified or with Shift only |
| `select` | printable characters, Space, Up, Down, Home, End, Page Up, Page Down, Enter, unmodified or with Shift only |
| `button`, `a`, `summary`, checkbox, radio button | Space and Enter, unmodified or with Shift only |

- **Tab and Shift+Tab** move between the surface's focusable elements, and
  the host sends `focus` for the one they move to (§10.1). Past the last
  one, or before the first, the surface loses the keyboard: the host sends
  `blur` and the terminal has the keyboard again.
- **Escape** is never used by the surface, except by a select's open list
  (below) and a key sequence that waits (§10.5). It reaches the program,
  which decides, for instance by sending `a=blur`.
- **A key sequence that waits** (§10.5) takes every key first.
- **A key the element gives the program** reaches it, whatever the element
  or the scrolling (§5.3) would do with it (below, *Keys for the program*).
- **A key that starts a key sequence** (§10.5), and that the element does
  not use, starts it.
- **A key the element binds to a scroll action**, and does not use, scrolls
  the surface's document (below, *Scrolling keys*).
- **Every other key** reaches the program as ordinary terminal input, in the
  keyboard encoding the program has enabled, or as an edit command it takes
  (§10.6). A program's own keymap therefore keeps working while a surface
  holds the keyboard.

#### Selects

A focused `select` picks an option with its keys, as a browser's closed
select does on Linux and Windows. Each pick is heard at once (§9): `input`,
with `data-on~=input`, then `change`.
- **Up and Down** pick the option before or after the picked one; **Home**
  and **End** the first and the last.
- **A character** picks the next option after the picked one whose label
  starts with it, ignoring case, going round to the first. A host **MAY**
  match several characters typed in quick succession, as browsers do.
- **Page Up and Page Down** move further, by as much as the host likes.
- Disabled options are passed over, and a key with no option to go to picks
  nothing.

**The list** is the host's to show or not:
- A host **MAY** show no list. The select then works by its keys alone, and
  Space and Enter do nothing. A program that wants a list on every host
  draws its own: a button, and a surface at a higher z (§5.2) placed by the
  `area` its click reports (§9).
- A list a host shows opens as a browser's does, on a click or a key, and
  may be drawn past the surface's rectangle, over the cells and other
  surfaces, as a browser draws one past the page. While it is open it has
  every key, Escape and those the keymap gives the program included, and
  it closes on a pick, on Escape, and when the select loses focus.

#### Text fields

A text field's **keymap** binds keys to editing actions. It is the default
keymap, then the `data-keys` attribute of each element from the document's
root down to the field, the field's own last. Its bindings to scroll
actions are left out, each where it stands, as if it were not there (below,
*Scrolling keys*). Each `data-keys` overrides what
came before it key by key: a binding replaces the earlier binding of its key,
and leaves the others as they were. A program sets its keymap once, on an
element that holds its fields, and a field that needs one key otherwise says
only that.

`data-keys` is a list of bindings separated by ASCII white space (space,
tab, line feed, form feed, carriage return), as HTML's space-separated
tokens are. A binding is
`key=action`, split at its last `=`: the key is named as §10.4 has it
(`Control+a`, `Mod+s`, `Alt+ArrowLeft`, `Alt+==line-start` binds `Alt+=`), and the
action is one of the table below or a scroll action (*Scrolling keys*). A
host **MUST** ignore a binding whose key does not parse or whose action it
does not know, and bindings of Tab,
Shift+Tab and Escape, which keep their meaning above.

The default keymap is the keys every host binds, then those of the host's
platform modifier, `Mod` (§10.4), then the host's edit shortcuts. Every
host binds:

| key | action |
| --- | --- |
| ArrowLeft, ArrowRight | `char-backward`, `char-forward` |
| Alt+ArrowLeft, Alt+ArrowRight | `word-backward`, `word-forward` |
| Home, End | `line-start`, `line-end` |
| Backspace, Delete | `delete-char-backward`, `delete-char-forward` |
| Alt+Backspace, Alt+Delete | `delete-word-backward`, `delete-word-forward` |
| ArrowUp, ArrowDown | `line-previous`, `line-next` |
| PageUp, PageDown | `page-up`, `page-down` |
| Enter | `submit` in an `input`, `newline` in a multi-line field |

Where `Mod` is Control:

| key | action |
| --- | --- |
| Control+ArrowLeft, Control+ArrowRight | `word-backward`, `word-forward` |
| Control+Home, Control+End | `input-start`, `input-end` |
| Control+Backspace, Control+Delete | `delete-word-backward`, `delete-word-forward` |

Where `Mod` is Meta:

| key | action |
| --- | --- |
| Meta+ArrowLeft, Meta+ArrowRight | `line-start`, `line-end` |
| Meta+ArrowUp, Meta+ArrowDown | `input-start`, `input-end` |
| Meta+Backspace | `delete-to-line-start` |
| Control+a, Control+e | `line-start`, `line-end` |
| Control+b, Control+f | `char-backward`, `char-forward` |
| Control+p, Control+n | `line-previous`, `line-next` |
| Control+h, Control+d | `delete-char-backward`, `delete-char-forward` |
| Control+k | `delete-to-line-end` |

The **edit shortcuts** are the host's, and the user's to change; a host
reports them as `edit` (§4). The same keys send a program in the cells the
edit commands it takes (§10.6). Unless the user changes them, they are:

| key | action |
| --- | --- |
| Mod+a | `select-all` |
| Mod+c | `copy` |
| Mod+x | `cut` |
| Mod+v | `paste` |
| Mod+z | `undo` |
| Mod+Z; Control+y where `Mod` is Control | `redo` |

These are a text field's keys in a browser on Linux and Windows, where
`Mod` is Control, and on macOS, where it is Meta: the Command key is Meta,
the Option key Alt (§10.4), and Control+a and the keys after it are
Cocoa's. Mod+Z is Mod+Shift+z (§10.4). Shift selects with each move
(below). A program that wants one of them binds it to `program`. A host
that sees only what the program would read (§10.4) can offer a key only as
that: in the legacy encoding a terminal may send Control+Backspace as
`0x08`, which is Control+h, and a macOS terminal sends Command+ArrowLeft as
`0x01`, which is Control+a.

A key goes to the field's keymap:
- **Bound:** the field does the action. A key bound to `program`, or to an
  action the field does not have (a multi-line one in an `input`, or
  `copy`, `cut` and `paste` where they have nothing to do, below), reaches
  the program.
- **Not bound, with Shift:** the key is looked up again without Shift, so
  Shift+ArrowLeft does what ArrowLeft does, and selects (below). A
  character shows Shift in itself (`A`, §10.4), so this concerns the other
  keys.
- **Not bound, a printable character** without Control, Alt and Meta: the
  field types it at the caret.
- **Otherwise** the key reaches the program.

So a field uses only the keys its keymap names, and the characters it types:
a key the program did not give the field stays the program's.

The actions:

| action | what it does |
| --- | --- |
| `char-backward`, `char-forward` | moves the caret one character back, or forward |
| `word-backward` | moves the caret back over spaces, then over the word before them, to its start |
| `word-forward` | moves the caret forward over spaces, then over the word after them, to its end |
| `line-start`, `line-end` | moves the caret to the start, or the end, of its line |
| `delete-char-backward`, `delete-char-forward` | deletes the character before the caret, or after it |
| `delete-word-backward`, `delete-word-forward` | deletes from the caret to where `word-backward`, or `word-forward`, would move it |
| `delete-to-line-start`, `delete-to-line-end` | deletes from the start of the caret's line to the caret, or from the caret to the end of its line |
| `line-previous`, `line-next` † | moves the caret to the row above, or below, as near as it can to the place along the row where a run of these moves began; from the first row to the start of the value, from the last to its end |
| `page-up`, `page-down` † | moves the caret as many rows up, or down, as the field shows, the same way |
| `input-start`, `input-end` | moves the caret to the start, or the end, of the value |
| `select-all` | selects the whole value: the anchor at its start, the caret at its end |
| `copy` | puts the selected text on the clipboard, and leaves it selected |
| `cut` | puts the selected text on the clipboard and deletes it |
| `paste` | types the clipboard's text in place of the selection |
| `undo`, `redo` | undoes the field's last edit, or redoes the last one undone (below) |
| `newline` † | types a line break |
| `submit` | submits the field's form, as Enter does in a text `input` (§9 `submit`) |
| `program` | nothing: the key reaches the program |

† Multi-line fields only: a `textarea` and an editing host.

- **Characters** are grapheme clusters (Unicode UAX #29, extended), and a
  line break (CR LF, LF or CR) is one. The caret stops at the value's ends.
- **A space** is a character whose first code point has the Unicode
  `White_Space` property; a line break is one. **A word** is a run of
  characters that are not spaces.
- **A line** is the text between line breaks; an `input`'s value is one
  line. A **row** is a line as the field lays it out: a line that wraps is
  several rows.
- **A password field** (`type=password`) is one word: the word actions move
  to, or delete to, the start or the end of the value.
- **A selection** runs from its anchor, the end where it began, to the
  caret. The user makes one with the pointer, with Shift (below) or with
  `select-all`. It comes first: typing replaces it, and a delete action
  deletes it and nothing else. A move without Shift starts from its start
  when it goes back or up, and from its end otherwise, and the selection
  goes; `char-backward` and `char-forward` stop there.
- **Shift selects.** The moves are `char-backward`, `char-forward`,
  `word-backward`, `word-forward`, `line-start`, `line-end`,
  `line-previous`, `line-next`, `page-up`, `page-down`, `input-start` and
  `input-end`. A move done by a key whose name has Shift (§10.4), bound
  with Shift or looked up without it, moves the caret from where it is and
  keeps the anchor, which is where the caret was if nothing was selected.
  Shift+ArrowLeft selects the character before the caret.
  Control+Shift+ArrowRight, Shift+End and, in a `textarea`,
  Shift+ArrowDown go on by a word, to the line's end and by a row. When the
  caret comes back to the anchor, nothing is selected.
- **Every edit** is an edit for the `input` and `change` events (§9).
- **The clipboard** is the host's: the platform's, where there is one. A
  field has no `copy` or `cut` with nothing selected, nor in a password
  field, and no `paste` on a host that cannot read the clipboard: the key
  reaches the program, so Control+c on Linux still interrupts it. An `input` drops the
  line breaks from what it pastes, as HTML's does.
- **Undo.** Each text field keeps a history of its edits, as a browser's
  does, for as long as it is in the document:
  - Typing characters one after another is one edit, and so is deleting
    them one at a time, with `delete-char-backward` or
    `delete-char-forward`. The run ends with any other action, and when
    the pointer moves the caret. Every other edit, a cut and a paste among
    them, is one of its own.
  - `undo` puts back the value and the selection from before the last
    edit, and `redo` those from after the edit last undone. A new edit
    drops the edits undone.
  - With nothing to undo, or to redo, the key is still the field's, and
    does nothing.
  - A value the program sets (§6.2, *Controls whose values the program
    sets*) clears the history.

#### Keys for the program

A key that the focused element's keymap binds to `program` reaches the
program, before the element uses it and before the surface scrolls with it
(§5.3), whatever the element. It reaches it as terminal input, which names
no element: the last `focus` does (§10.1), or the program's own `a=focus`.
- **Every focused element has a keymap**, read as a text field's is, but
  with its scroll actions: the `data-keys` of each element from the
  document's root down to it, the element's own last, each overriding what
  came before it key by key. A
  key with Shift that is not bound is looked up again without it. Only a
  text field starts from the default keymap.
- **Outside a text field,** a keymap gives only `program` and the scroll
  actions (below). Its other bindings still override farther ones key by
  key, but do nothing there: the element uses those keys as the table
  above says.
- **With no element focused** there is no keymap. A program that wants
  keys in a surface with nothing to focus gives an element a `tabindex`
  and focuses it.

So a program that works a list, a menu or a table with the arrows keeps
them on the element that holds it. On a button in a scrolling surface,
`data-keys="ArrowUp=program ArrowDown=program"` sends the arrows to the
program, where they would otherwise scroll the surface.

#### Scrolling keys

A focused element's keymap may bind keys to scroll actions, so that the keys
a program scrolls its cells with, such as a pager's `j` and `k`, scroll its
surfaces where the host scrolls them (§5.3):

| action | scrolls |
| --- | --- |
| `scroll-up`, `scroll-down` | up, or down, as far as the host scrolls with ArrowUp and ArrowDown |
| `scroll-left`, `scroll-right` | left, or right, as far as with ArrowLeft and ArrowRight |
| `scroll-page-up`, `scroll-page-down` | up, or down, as far as with Page Up and Page Down |
| `scroll-half-page-up`, `scroll-half-page-down` | up, or down, by half the height of the box it scrolls (its scrollport) |
| `scroll-start`, `scroll-end` | to the top, or the bottom, as Home and End |

- **What scrolls** is the nearest element that scrolls (the root, or an
  element whose `overflow` is `auto` or `scroll`), from the focused element
  outward, itself included. Where it cannot move that way, the key goes
  outward as a gesture does (§5.3), as far as `overscroll-behavior` lets
  it, and never past the root: a key never scrolls the terminal. Where
  nothing it may reach can move, the key is used, and does nothing, unlike
  a key a browser scrolls with, which then goes on to the program (§5.3).
- **Order.** A key bound to `program` is the program's (above). Any other
  key the focused element uses (the table at the start of §10.2) stays the
  element's: Space on a button presses it, and a character on a select
  picks. A key the element does not use and its keymap binds to a scroll
  action scrolls, before the surface's own scrolling keys (§5.3), and does
  not reach the program.
- **Along an axis the document does not scroll** (§5.1 `scroll`), a scroll
  action does nothing, and the key goes on as if its keymap did not bind
  it. On a host without `scroll`, and on one older than these actions,
  which ignores them, the program hears these keys as before.
- **A text field's keymap leaves scroll actions out.** A binding to one
  neither acts nor overrides the bindings before it, so a field inside an
  element that scrolls with `j` still types `j`, and a `textarea` keeps
  `page-down` on Page Down. A farther binding of the key still holds: under
  `j=program` on the root, `j` in that field reaches the program. A field's
  own text follows its caret (§5.3).

So a program that pages its cells with `j`, `k`, `g`, `G`, Space and `b`
binds the same keys on the element that scrolls on a surface:
`data-keys="j=scroll-down k=scroll-up g=scroll-start G=scroll-end
Space=scroll-page-down Shift+Space=scroll-page-up b=scroll-page-up"`
(Shift+Space, or it would page down as Space does). Its buttons keep Space,
and its fields type every letter.

### 10.3 Key releases

HOTTY has no key events of its own. A program that needs to know when a key is
released (a game, say) enables the kitty keyboard protocol with *report event
types*. That is an ordinary terminal feature, and works the same with or
without HOTTY.
- The alternate screen keeps its own stack of keyboard flags, so a
  full-screen program enables them after switching to it.
- A surface that does not have the keyboard does not affect the keys at all.

### 10.4 Key names

A key is named by its W3C UI Events key value, after the modifier keys held,
each followed by `+`: `a`, `A`, `Enter`, `ArrowLeft`, `Control+a`,
`Alt+Backspace`, `Control+Shift+ArrowRight`.
- **Modifiers** are `Control`, `Alt`, `Meta` and `Shift`, written in that
  order. A name read from a document may have them in any order.
- **A character** is the one the key types. Shift shows in the character
  (`A`, `!`), and is written only where it does not: `Shift+Enter`,
  `Shift+Tab`. With Control, Alt or Meta, a letter with Shift is its capital
  (`Control+A`), and `Shift` with a small letter is the capital
  (`Control+Shift+a` reads as `Control+A`).
- **`Space`** is the space bar's key value, a space, written so that it can
  stand in a list (`Control+Space`). `+` is the plus key (`Control++`).
- **`Mod`**, in a binding (§10.2, §10.5), is the platform's modifier for
  commands: Meta on macOS, whose Command key is Meta, and Control
  elsewhere, unless the user sets it otherwise. A host reports it as `mod`
  (§4), and reads `Mod` as that modifier wherever it reads a binding, so
  `Mod+c` is `Meta+c` on macOS and `Control+c` on Linux. It is written
  before the other modifiers (`Mod+Shift+ArrowLeft`), and no key pressed
  is named with it.

A host offers a surface that has the keyboard each key at most twice
(§10.2). The surface uses a key that its focused element uses, Tab and
Shift+Tab, which move focus, a key of a key sequence (§10.5), and a key it
scrolls with (§5.3):
- **As pressed, first.** A host that sees the key the user pressed (a
  terminal emulator, a browser) offers it before the terminal's own
  shortcuts and before the bindings that translate keys, named from the key
  itself: the modifiers held, with the platform's command key (Command on
  macOS, Super or the Windows key elsewhere) as Meta, and the key's value.
  It does so for the keys that type no text: a key that is not a character
  (`ArrowLeft`, `Home`, `Backspace`, `Enter`), and a character with Control
  or Meta. Typing goes only the second way, through the platform's input
  methods. If the surface uses the key, it is the surface's, and the
  terminal does nothing with it, not even a shortcut bound to it. A host
  **MAY** keep keys it reserves for itself, as a browser keeps Control+t.
- **As the program would read it, otherwise.** A key the surface does not
  use goes on as it would with no surface: the terminal's shortcuts take
  the keys they bind, and the rest is what the terminal would send the
  program, the bytes of the keyboard encoding the program has set (legacy,
  xterm's `modifyOtherKeys`, or the kitty keyboard protocol) after the
  terminal's own bindings. The host names it from those bytes, read as
  this table says, and offers it. Input that is several keys (a binding
  that sends text) is each of them in turn. A host that has only those
  bytes, such as one that runs as a program in a terminal, offers keys
  this way alone.

| input | key |
| --- | --- |
| a printable character: one grapheme cluster, in UTF-8 | that character; `Space` for `0x20` |
| `0x00` | `Control+Space` |
| `0x01`–`0x1a`, but those below | `Control+a` … `Control+z` |
| `0x08` | `Control+h` |
| `0x09`, `0x0d`, `0x1b`, `0x7f` | `Tab`, `Enter`, `Escape`, `Backspace` |
| `0x1c`–`0x1f` | `Control+\`, `Control+]`, `Control+^`, `Control+_` |
| `ESC` before one of the above | that key, with Alt: `ESC b` is `Alt+b`, `ESC 0x7f` is `Alt+Backspace` |
| `CSI A`, `B`, `C`, `D`; `SS3 A` … `D` | `ArrowUp`, `ArrowDown`, `ArrowRight`, `ArrowLeft` |
| `CSI H`, `SS3 H`, `CSI 1 ~`, `CSI 7 ~` | `Home` |
| `CSI F`, `SS3 F`, `CSI 4 ~`, `CSI 8 ~` | `End` |
| `CSI 2 ~`, `CSI 3 ~`, `CSI 5 ~`, `CSI 6 ~` | `Insert`, `Delete`, `PageUp`, `PageDown` |
| `CSI Z` | `Shift+Tab` |
| `CSI 1 ; m X`, for each `X` above; `CSI n ; m ~` | the key above, with the modifiers in `m` |
| `CSI 27 ; m ; c ~` (`modifyOtherKeys`) | the key whose code is `c`, with the modifiers in `m` |
| `CSI c [: s [: b]] [; m [: e] [; t]] u`, and the kitty protocol's `CSI 1 ; m : e X` and `CSI n ; m : e ~` | the key whose code is `c`, with the modifiers in `m`; a release (`e` = 3) is no key |

- **Modifiers `m`:** absent, empty or below 2, no modifier. Otherwise `m` − 1
  is a sum of bits: 1 Shift, 2 Alt, 4 Control, 8 Meta (the kitty protocol's
  Super) and 32 Meta. Other bits (Hyper, Caps Lock, Num Lock) name no
  modifier.
- **Codes `c`:** 9 is Tab, 13 Enter, 27 Escape, 8 and 127 Backspace; another
  code below 57344 is the character with that code point, and the kitty
  protocol's codes from 57344 are the keys it gives them. A character key
  with Shift is the shifted key `s` when given, else the text `t` when
  given, else the capital of `c`; Shift is written only when that is `c`
  itself (`Shift+1`).
- **`ESC [` and `ESC O`** begin CSI and SS3. Alone, they are `Alt+[` and
  `Alt+O`.
- **Anything else,** such as a sequence this table does not name, is no key
  a field uses: it reaches the program.

### 10.5 Key sequences

A document gives an element a key sequence that activates it, as an access
key does in a browser, and while a sequence waits for its next key the host
shows which keys can follow, as a which-key menu:

```html
<menu data-key="<leader> f" aria-label="File">
  <button id=new data-key="n">New file</button>
  <button id=open data-key="o">Open…</button>
</menu>
<button id=top data-key="g g" hidden>Top</button>
```

- **`data-key`** is a sequence: keys named as §10.4 names them, `Mod`
  included, separated by ASCII white space, as myelin writes them. `g g` is
  `g` twice. `<leader>` stands for the user's leader, a sequence the host
  reports as `keys.leader` (§4). A host **MUST** ignore a `data-key` with a
  key that does not parse, with Tab, Shift+Tab or Escape, or with any other
  name in angle brackets.
- **Groups.** A sequence goes on from the one of the nearest element around
  it that has a `data-key`: above, the button's `n` is `<leader> f n`. An
  element with such elements inside it is a group: its sequence leads to
  theirs, and does nothing itself.
- **What a sequence does.** The host activates its element as a browser
  does an access key. It clicks an element a click activates (a `button`,
  a link, a `summary`, a checkbox or radio button, an `input` of type
  `button`, `submit` or `reset`, an element with `data-on~=click`), which
  does and reports what a click from the keyboard does (§9), and focuses
  any other element that takes focus (§10.1). A disabled element's
  sequence does nothing. A hidden element's works, so a hidden button is a
  command with nothing on the screen; its click's `area` is all zeros.
- **Which element.** Sequences work while the surface has the keyboard
  (§10.1). Where several elements have the same sequence, the one nearest
  the focused element wins: the one whose nearest common ancestor with it
  is deepest, and of those the last in tree order.
- **Starting.** A key that starts a sequence starts it when the focused
  element does not use it and its keymap does not give it to the program
  (§10.2): Space on a button presses the button, and a character in a text
  field types.
- **Waiting.** While a sequence waits, the next key the host offers, as
  pressed or as the program would read it (§10.4), is the sequence's:
  - a key that finishes a sequence runs it, unless a longer one, at least
    as near the focus, goes on from it: then it waits again, as it does on
    a key that only goes on;
  - **Escape** ends the wait, and does nothing more;
  - **any other key** ends the wait, and the keys typed, that one included,
    go on in order as if no element had a `data-key`: to the element, the
    scroll actions and the program (§10.2);
  - after `keys.timeout` milliseconds (§4) with no key, the sequence typed
    runs if it finishes one, and its keys go on otherwise.

  The wait also ends, and its keys do nothing, when the surface loses the
  keyboard. These are myelin's rules, so a program that reads the same
  keymap in its cells does there what the host does here (§10.6).
- **The menu.** While a sequence waits, the host **SHOULD** show the keys
  that can follow it, each with its label: a group's `aria-label`, an
  element's `aria-label`, or else its text, with its white space collapsed.
  A disabled element's key shows as disabled. The host draws the menu
  itself, as it may a select's list (§10.2), and **MAY** wait a moment
  first, so that a sequence typed quickly shows none.
- A host that reads sequences reports `keys` (§4). Others ignore
  `data-key`.

### 10.6 Commands in the cells

A program in the cells reads keys as bytes, and to it an edit shortcut
(§10.2) is a key like any other: Control+c interrupts, Control+v quotes the
next key. A program that selects, edits or undoes in its cells, as a text
field does on a surface, takes the edit commands instead:

```
ESC ] 7279 ; a=edit:take=copy,paste,undo,redo ST
```

- **`take`** names the commands, the actions of the edit shortcuts
  (`select-all`, `copy`, `cut`, `paste`, `undo`, `redo`), comma-separated.
  Each `a=edit` replaces what the last took, and one with an empty `take`,
  or none, takes nothing. A host **MUST** ignore a name it does not know.
- **Per screen.** The main screen and the alternate screen each keep their
  own, as the kitty keyboard protocol keeps its flags (§10.3): a
  full-screen program takes its commands after switching to the alternate
  screen, and leaving it drops them. A full reset (RIS) drops both.
- **A key of a command taken,** one of the host's edit shortcuts (`edit`,
  §4), reaches the program as the event `command`, in place of its bytes,
  and so does each of its repeats. Its release sends nothing (§10.3).

  ```
  ESC ] 7279 ; a=ev:e=command ; <base64 msgpack detail> ST
  ```

  The detail is `{"name": str, "key": str}`: the command, and its key as
  §10.4 names it. A `paste` also has `"text": str`, the text on the
  clipboard, and none when the clipboard holds no text or the host cannot
  read it.
- **The program decides** what the command means. It copies what it has
  selected, and with nothing selected takes the command as its key, as a
  text field does (§10.2): Control+c still interrupts.
- **The terminal's selection comes first.** While the user has text
  selected in the cells, a key of `copy` copies it, as the terminal's own
  copy does, and is not sent. A surface's selection is copied as §11 says.
- **A surface that has the keyboard** is offered the key first (§10.2). A
  key it does not use reaches the program as the command.
- **The terminal's menus,** such as an Edit menu or a context menu, send
  the command they name, with no `key`, where its key would send one. Their
  copy copies the terminal's selection first, as above.
- **In order.** A command reaches the program on its input, among the keys
  typed around it, as every event does (§9): a paste never overtakes what
  was typed before it. The terminal's own paste, by a key that is no edit
  shortcut, still sends the clipboard as it would without HOTTY, as a
  bracketed paste where the program asked for one.
- **A host that takes `a=edit`** reports its edit shortcuts as `edit`
  (§4). When they change, or `mod` does (§10.4), as when a multiplexer's
  viewer changes to one on another platform, it sends `caps` (§9).

**Menus.** A program that reads key sequences in its cells, as one built on
myelin does, shows which keys can follow one while it waits by sending the
host its menu:

```
ESC ] 7279 ; a=menu ; <base64 msgpack menu> ST
```

- **The menu** is one msgpack map (§3.3), myelin's which-key level:
  `{"seq": [str], "label": str, "items": [item]}`. `seq` is the keys typed
  so far, as §10.4 names them, and `label` their group's label. Each item
  is a key that can follow them, `{"key": str, "label": str, "group":
  bool, "enabled": bool}`: the key, what it does, whether more keys follow
  it, and whether it does anything now. A host **MAY** show only as many
  items as fit.
- **The host shows it** as it shows a surface's (§10.5), until the program
  sends another, or `a=menu` with no body, which hides it. It also hides
  it on Escape, on a key the menu does not list, when the screen changes
  and on a full reset (RIS), so that a program that ends while it waits
  leaves none behind. The keys still reach the program.
- A host that shows menus reports `menu` (§4).

## 11. Text

A surface is drawn as pixels, but it is never only pixels: the host holds its
document, and therefore its text.

- **Selecting** in a surface selects the text of its document, as in a
  browser: from a press, by dragging; a word, with a double click; a
  block, with a triple click. A text field selects with its keys too
  (§10.2). Where the platform has a primary selection, as X11 and Wayland
  do, a host **SHOULD** put the text there once it is selected, as
  browsers do.
- **There is one selection,** the terminal's on its cells or a surface's.
  A press anywhere else, on the cells or on another surface, drops a
  surface's, and a press on a surface drops the terminal's.
- **Copying** is the `copy` action (§10.2), by the keymap, as cutting and
  pasting are. A focused text field's selection is copied by a key its
  keymap binds to `copy`, and a password field's never is.
- **A selection in a document,** outside a text field, is copied by a key
  that the keymap of the element whose text it starts in, in tree order,
  binds to `copy`, read as a text field's keymap is: the default keymap,
  then the `data-keys` of each element from the root down to it. The host
  offers it each key first, before the surface that has the keyboard and
  the terminal's own shortcuts, whether or not the surface has the
  keyboard. A key it does not bind to `copy`, `program` included, goes on
  as if nothing were selected: under `Mod+c=program`, Control+c on Linux
  interrupts the program while text is selected.
- **The terminal's own copy** and paste, from its own keys or its menu,
  are the user's whatever the keymaps say. Its copy **SHOULD** copy a
  surface's selection, so that no document makes its text uncopyable, and
  while a text field has the keyboard its paste **SHOULD** type into the
  field as `paste` does, and not reach the program. Its own selection on
  its cells it copies as it would without HOTTY.
- **`user-select: none`** is the document's to set, as in a browser. A host
  **MUST NOT** start a selection on an element whose `user-select` is
  `none` (its used value, CSS UI 4: the elements inside one with `auto`
  included), or on one that opts in to drags (§9.1). It **SHOULD** leave
  their text out of a selection that crosses them.
- **Wherever the host extracts the screen as text** (scrollback search, "copy
  all", a serialised buffer), it **SHOULD** use for each row a surface covers
  the text of the elements laid out on that row. `data-hotty-text` on an
  element replaces its text there: a chart can say what it shows.
- **The footprint** is the program's choice (`c` and `r`, or `r=auto`), so
  the terminal's grid stays a grid whatever the host draws inside it.

## 12. Security

A surface's markup comes from the program's side of the pty, which may be a
remote machine, or a file someone `cat`s. Hosts treat it as untrusted.

A host **MUST** ensure that:

- **no script runs:** no `<script>`, event-handler attributes, `javascript:`
  URLs, or script inside SVG;
- **nothing is fetched** except `cid:` resources, `data:` URLs, and what the
  network policy allows (§7.2). This covers references from attributes and
  from CSS (`url()`, `@import`, `@font-face`, `image-set()`). Prefetch and
  preconnect hints and nested documents (`<iframe>`, `<object>`, `<embed>`)
  are never fetched;
- **nothing navigates:** links, forms and `<meta http-equiv=refresh>` have no
  effect beyond the events of §9, and a host that opens a link (§9) opens it
  outside the surface. `<base>` only sets the base URL (§7.3);
- **nothing opens a window, dialog or popup;**
- **a surface cannot take the keyboard** from the terminal on its own
  (`autofocus`): only the user or the program gives it the keyboard (§10);
- **a surface cannot draw outside its rectangle**, `position: fixed`
  included;
- **a surface cannot read** the screen, the clipboard, other surfaces, or
  anything about the terminal beyond what §8 gives it. Events carry only the
  program's own ids and what the user entered into the program's own
  surface.

**Defence in depth:**
- Two independent layers are recommended: a sanitizer that removes what can
  run, navigate or load before markup reaches a live document, and an engine
  or policy that cannot fetch beyond the network policy even if the
  sanitizer misses something.
- The second layer must hold on its own: a sanitizer working on attributes
  misses requests carried by CSS (`url()`, `@import`, `@font-face`).
- A host built on a web engine inherits the policies of the page that embeds
  it. Its documentation must say what that page has to allow.

## 13. Limits

- A host reports its limits under `limits` (§4) and refuses commands that
  would exceed them with `EQUOTA`. Hidden surfaces (§5.4) count: a program
  that keeps many deletes the ones it needs least.
- A host reports a message-size limit as `limits.message`: the most bytes it
  accepts for one reassembled message, decoded (§3.4). A host that reports
  none enforces none; one with a limit **SHOULD** accept at least 1 MiB. A
  message past the limit is malformed (§3.7), not `EQUOTA`. A resource is
  one message (§7.1), so this limit also caps how large a resource the host
  takes.
- Rendering must not stall the terminal. A host **MAY** abandon a render
  that exceeds its time budget and report `EBUDGET`: pathological CSS such
  as huge blurs, deep nesting, or enormous documents.

## 14. Degradation

A program **SHOULD** work without a host.
- When detection (§4) finds none it can use, it paints its interface as
  terminal text (until a late answer finds one, §4), and should not send
  HOTTY commands to a terminal that is not a host.
- The same program can use HOTTY where it is available and text where it is
  not, with no change to how it runs.

Between the two, a **polyfill** host can serve terminals that show images:
- It sits on the pty between the program and the terminal, and passes every
  byte through except HOTTY messages.
- It renders surfaces itself and sends them as pixels: kitty graphics
  placements anchored where the cursor was, updated as frames change. A
  window is a placement of part of the image.
- It answers `a=q` on the terminal's behalf.

Because it runs next to the terminal, a program on the far side of SSH needs
no change. Pixels lose what a native host keeps: sharpness under zoom, and
the text of §11.

## 15. Versioning and extensions

- `v` in the capabilities is the protocol version, a string `major.minor`.
  From 1.0 on, a change that breaks existing programs or hosts gets a new
  major version, and additions that old hosts and programs can ignore get a
  new minor version. **Until 1.0, any minor version may break the previous
  one**: versions 0.x are drafts.
- **A program and a host agree on a version** before either reads the
  other (§4): the program's query lists the versions it speaks, and the host
  answers in the highest it speaks too, or with `EVERSION`. With none in
  common, the program falls back (§14). A host or a program **MAY** speak
  several versions.
- **A field keeps its type,** from 0.2 on: a version that needs another type
  for it adds a field under a new name. A reader then never meets a field
  it knows with a type it does not.
- A host **MUST** ignore control keys it does not know. An unknown action or
  delta op is `EINVAL`. A program **MUST** ignore event kinds (§9) and
  capability fields (§4) it does not know.
- `host` and `version` (§4) only name an implementation. A program **MAY**
  use them to avoid a known bug of some of its versions, and falls back as
  if the bug were there when either is absent. What a capability field
  says, a program learns from the field, never from the name.
- **Extensions** by an implementation use a vendor prefix:
  - control keys `x-<vendor>-<name>`;
  - attributes `data-<vendor>-<name>`;
  - custom properties `--<vendor>-<name>`.

  An extension **MUST NOT** be required for a document or program to work on
  another host.
- `--hotty-*`, `data-hotty-*` and unprefixed control keys belong to this
  specification.

## 16. Conformance

A host conforms to HOTTY version 0.2 when:
- it meets every **MUST** of this document;
- it passes `conformance/vectors.json` (`conformance/README.md`).

The vectors check replies, error codes, every delta op, morph, context
parsing, resources, drags and their steps, presses with Alt, `fit`, hover,
`area`, scrolling, `reveal` and `view`, key sequences, edit commands,
keymaps and the envelope, and their
`keys`, `keymap` and `edit` sections a host's key names (§10.4), keymaps
and actions (§10.2).
They inspect documents and events, not pixels.
The vectors marked `"passthrough"` apply to a host that reports it (§9.3),
those marked `"hover"` to a host whose `events` list it (§9.4), those
marked `"scroll"` to a host that reports it (§5.3), those marked
`"steps"`, `"drop"` or `"count"` to a host that reports it (§9.1, §9),
those marked `"view"` to a host whose `events` list it (§9.5), those
marked `"keys"` to a host that reports it (§10.5), and those marked
`"commands"` to a host with a terminal that takes edit commands (§10.6).

To be tested, a host exposes a way to *inspect* an element, reporting:
- its tag;
- its attributes with the program's values (§7);
- its text;
- its child elements as `[tag, id, text]`.

It also lets a test move a mouse's pointer to the centre of an element, or
of a cell of a surface, press and release its primary button there, with
modifier keys held, turn its wheel there, take the pointer out of the
terminal's window, and press keys where the keyboard is. A host that takes
touch also lets a test touch a cell of a surface with one finger, move it,
and lift it, and tells it whether a touch went on to the terminal. A host
with `passthrough` also tells the test whether each of those reached the
surface or passed through it, and a host with `scroll` whether a wheel or
a key went on to the terminal.

This is a test interface, not part of the wire protocol.

A library that speaks HOTTY for programs, an SDK, conforms when it meets
[SDK.md](SDK.md) and passes the vectors' SDK sections: `build`, `encode`,
`decode`, `scan`, `detect`, `keys` and `keymap`, and `edit` where it edits
fields (SDK.md §4.6).

---

## Appendix A. Examples

Detection (payload shortened):

```
program → ESC ] 7279 ; a=q:n=1:v=0.2 ST  CSI c
host    → ESC ] 7279 ; a=ok:n=1:re=q ; hqF2ozAuMqNvcHOcpW1vcnBo… ST  CSI ? 62 ; 22 c
```

A card placed below the prompt, then a delta and an event:

```
program → ESC ] 7279 ; a=doc:s=card:q=2 ; PGJ1dHRvbiBpZD1nbz5HbzwvYnV0dG9uPg== ST
          (<button id=go>Go</button>)
program → ESC ] 7279 ; a=place:s=card:c=40:r=auto ST
host    → ESC ] 7279 ; a=ok:s=card:re=place:c=40:r=2 ST
program → ESC ] 7279 ; a=delta:s=card:op=text:t=go:q=2 ; U3RhcnQ= ST
          (the button now reads "Start")
host    → ESC ] 7279 ; a=ev:s=card:e=click:t=go ST
          (the user clicked it)
```

A page that asks for images from its own site, on a host whose policy grants
that origin (`"net": {"img-src": ["https://example.com"]}` in its
capabilities):

```
program → ESC ] 7279 ; a=doc:s=post:q=2 ; … ST
          (<base href="https://example.com/blog/">
           <meta name="hotty-network" content="img-src https://example.com">
           <img src="cover.png"> <a href="../about">About</a>)
          (the host fetches https://example.com/blog/cover.png)
host    → ESC ] 7279 ; a=ev:s=post:e=click:t= ; eyJocmVmIjoiLi4vYWJvdXQiLCJ1cmwiOiJodHRwczovL2V4YW1wbGUuY29tL2Fib3V0In0= ST
          ({"href":"../about","url":"https://example.com/about"}: the user
           clicked the link, and the program decides where it goes)
```

A value that changes every frame, cheaply:

```
program → CSI ? 2026 h
program → ESC ] 7279 ; a=delta:s=dash:op=var:t=cpu:k=p:q=2 ; NDI= ST        (--p: 42)
program → ESC ] 7279 ; a=delta:s=dash:op=text:t=clock:q=2 ; MTI6MDA6MDE= ST  (12:00:01)
program → CSI ? 2026 l
```

## Appendix B. Rationale

- **Why an OSC.** Terminals parse OSC sequences and ignore the ones they do
  not know, which makes probing safe. An APC or DCS would serve as well on
  the wire, but more of the software between a program and a terminal drops
  or mangles them.
- **Why `:` between keys**, not `;`: some terminals limit the number of
  `;`-separated OSC fields.
- **Why base64 always.**
  - Many terminals drop C0 bytes inside an OSC, so a `<pre>` would lose its
    newlines.
  - Raw bytes are at the mercy of every parser on the way.
  - zlib on markup more than pays for base64's third.
- **Why 4096-byte chunks:** some terminals ignore longer strings, and some
  multiplexers discard a string that takes too long to arrive.
- **Why values are ASCII.** A byte of UTF-8 may be 0x9C, which a parser that
  reads 8-bit controls takes for ST, and ends the sequence there. Neovim's
  input parser is one. An id cut to `_` is a smaller loss than an event cut
  in two.
- **Why msgpack, inside the base64.** A host's bodies were JSON until 0.2.
  - JSON has one kind of number, so a count of cells written `2.0` had to
    be read as `2`, and every SDK carried that rule. msgpack keeps ints
    and floats apart, and has a type for time.
  - Where a language has a codec generated from types (Go's msgp, Rust's
    serde), it reads a body, and no one writes a reader by hand. Where it
    has none, a decoder is under 200 lines.
  - Its maps are keyed by name, as JSON's are, so a version adds a field
    that an older reader ignores (§15).
  - It stays inside the base64, since its bytes include ST and BEL.
  - What a program sends stays text: a document is HTML.
- **Why hosts do not compress.** Replies and events are small, and zlib
  would be a second dependency a program needs only to read them.
  Programs keep it for what they send, where documents are large.
- **Why ids and deltas.**
  - Addressing by id keeps a delta's effect predictable, and makes an update
    cost what it changes.
  - `morph` without a target also serves programs that redraw their whole
    tree (immediate mode) while keeping what the user was doing.
- **Why no script:** it keeps the sandbox small enough to defend, and the
  program in charge.
- **Why `fit` tells, and the host does not resize.** A document's height can
  change after its placement is answered: an image arrives, a font loads, a
  stylesheet is replaced. A host that grew the placement on its own would
  cover the cells below it, which are the program's (§11). `fit` tells the
  program the rows the content needs now; the program decides where they
  come from. It is opt-in so a program that never sizes by content hears
  nothing new.
- **Why a zoom keeps the layout.** A zoom is the user's, for the moment:
  the terminal's text grows, and a surface over it should grow with it,
  as a kitty image placed over cells does, but drawn again so it stays
  sharp. Growing the CSS cell instead would grow only what is sized in
  cells or rem, and leave images, borders and gaps at their old size in
  a bigger box. It would also lay the document out again, send `fit` and
  `resize`, and make a cell size the program read stale. Viewers of one
  pane in a multiplexer, each at its own zoom, would each lay it out
  differently. A browser zooms a page in a frame the same way: the frame
  keeps its size in CSS pixels, and its document its layout. A new font
  is different: the cell changes in CSS pixels, and the document is laid
  out for it.
- **Why the host grants and the document asks.** Markup can come from
  anywhere, a file someone `cat`s included, and every fetch tells a server
  who looked and where. So only the host (its user, or the page that embeds
  it) can allow the network. A document names what it needs, can only get
  less than the host allows, and fetches nothing unless it asks.
- **Why a link click is an event.** The program is the application: a click
  may mean another page in the program, not a URL to load. Hosts still give
  links the gestures users expect of links, the way terminals open OSC 8
  hyperlinks.
- **Why synchronized output for transactions:** it is the terminal's
  existing mechanism for showing a batch of output at once, and programs use
  it for flicker-free text.
- **Why windows:** full-screen programs scroll content that holds surfaces:
  a transcript, a document. Without a window, a surface at the edge of the
  scrolling region can only disappear or cover the program's frame. With
  one, the program shows the part in view, as a kitty placement shows part
  of an image, and the document is not laid out again as it scrolls.
- **Why detach.** Events arrive on whatever reads the terminal's input, and
  a host cannot tell when the program that drew a surface has gone: after it
  exits, a shell would read them as typed text. Only the program knows when
  it is done with a surface, and printing a document is the common case,
  hence `d=1`. A program that crashes cannot detach. What ran it can, if it
  knows the surfaces' names, and a multiplexer deletes those of the
  program a pane runs when it ends (§5.4); otherwise they keep reporting
  until they are deleted or leave the scrollback, as a crashed program can
  leave mouse reporting on.
- **Why a late answer.** A multiplexer can run a pane with no terminal
  attached: restored after a reboot, or started from a script. Detection
  then finds no host, and a program that settled on text at its start
  would stay text after a terminal that is a host attaches. The late
  answer is asked for, so a program that expects no reply after its fence
  never gets one, and it comes once, so it is not a stream of changes.
  Terminals report what changes later in the same way, such as the colour
  scheme (mode 2031) and the window's size (mode 2048): the program asks,
  and hears when there is something to say.
- **Why the query names versions.** Until 1.0 a version may change how
  bodies are read, as 0.2 did (§3.3), and a program that took a reply in a
  version it does not speak for a host would read nothing right. The
  capabilities alone cannot tell it, since a program may not be able to
  read them. The host, which reads the query whatever its version, decides,
  and an error is the one answer every version takes as no host.
- **Why `press`.** A program that shows several surfaces moves its own
  selection to the one the user goes to: a dashboard selects the card
  pressed, and a multiplexer that draws its panes and tools as surfaces
  focuses the one pressed, as it does for a press on cells through mouse
  reporting. A surface takes every press, and `focus` and `click` cover only
  what takes focus or has a handler, so a press on text or empty space
  told the program nothing. `data-on~=click` on a document's root would
  cover the program's own documents, but only on the release, and not a
  multiplexer relaying another program's documents, which it would have to
  rewrite.
  - **Asked for, not always sent**, because events reach whatever reads the
    input: a document printed by a program that exits without detaching
    (§5.5) would otherwise type an event into the shell on every click on
    its text. The programs that ask are those that read events.
  - **On the placement**, because the pointer belongs to the window that
    receives it (§5.3), and a program that composes surfaces places them
    every frame anyway. A multiplexer asks for every surface it relays, and
    passes a `press` on only to a program whose own placement asked.
  - **First**, as a browser's `pointerdown` comes before the focus moves: a
    program hears where the user went before it hears what that did.
- **Why drags.** A spreadsheet selects a range by dragging across it, and
  fills by dragging its handle. Clicks cannot stand in for either. The
  terminal's mouse reporting can, but it does not reach over a surface,
  where the pointer is the surface's.
  - **Opted in, element by element,** because elsewhere a mouse's drag
    selects text, which the reader of a document expects of it.
  - **Elements, not pixels.** An event for each element crossed is a few
    for each cell of a grid, which a round trip over SSH can carry; one for
    every move would not be.
  - **The cell in the detail** says what elements cannot: where the
    pointer is past the surface's edge, which a program that scrolls during
    a drag needs. Cells are the one unit that the program and every host
    share (§5.3). They are counted from the surface, not the screen, so a
    multiplexer relaying a surface passes its events on unchanged.
  - **The pointer is held,** as a browser's `setPointerCapture` holds it,
    so a drag that leaves the window still ends, and the program hears
    where.
  - **Steps say where in an element.** A slider, a splitter or a scrubber
    needs the pointer's place along one element, finer than a cell, and
    still after the pointer has left it, as a browser's range input keeps
    following. A cell cannot say it: the program does not know where the
    element is, since the layout is the host's. Pixels would cost an event
    for every move, so the program names the steps it can use instead. It
    hears one event for each, and the step is already the slider's value.
    They are measured against the element the drag started on, as
    `offsetX` is against the element that captured the pointer, and
    clamped, as a range input's value is.
  - **Touch only where an element opts out of panning,** because a touch
    drag scrolls (below): a surface that took every touch drag would trap
    the finger. `touch-action` is the web's switch for it, which maps,
    sliders and canvases already use, so the trap is per element and only
    over its area, a swipe the element still allows scrolls, and a second
    finger always gives the gesture back to the host. A tap is still a
    click.
  - **No text selection,** because one gesture cannot select both text and
    cells.
  - **In a browser's order:** the press is reported before the focus moves,
    as `pointerdown` comes before it, and the release before the click, as
    `pointerup` does. A browser clicks only where a press and its release
    meet, so a drag that ends elsewhere is no click.
  - **Not HTML's drag and drop** (`draggable`, `DataTransfer`). It moves
    data between pages and applications, through script, which a surface
    does not have. The program already holds the data.
- **Why hover is reported.** A multiplexer draws its own controls in cells
  next to the surfaces it relays, and lights them while the pointer is over
  them, from mouse reporting. When the pointer goes from such a control
  straight onto a surface, mouse reporting stops, and the control stays lit.
  A program that shows hints of its own for what is under the pointer, in
  a box that may reach past the surface, needs to know what that is.
  `:hover` alone can do neither.
  - **Asked for**, like `press` and for the same reason: events reach
    whatever reads the input. A multiplexer asks for the surfaces it
    relays, and passes `hover` on only to a program whose own placement
    asked.
  - **Elements, not moves,** as for drags: an event for each element
    crossed, which a round trip over SSH can carry. The id is the
    program's handle; the program wrote the document, and knows what its
    elements mean without being told their attributes.
  - **Out is said,** not left to the next event: going onto the cells, a
    program with mouse reporting hears motion there, but going onto
    another program's surface, or out of the terminal, it hears nothing.
  - **Not while a button is held,** because the gesture has the pointer
    (§9.1), and a drag already reports what it crosses.
  - **`v`,** because `h` is the window's rows.
- **Why a press with Alt passes a surface.** A surface takes every press
  in its window (§5.3), so a program could not start a gesture of its own
  over one. A multiplexer that draws its panes and tools as surfaces moves
  them with Alt and a drag, as a window manager moves windows, and a pane
  or a tool is mostly surface. Terminals already pass a layer this way:
  Shift takes a press past a program's mouse reporting, to the terminal's
  selection. Alt takes it past a surface, to the program.
  - **Alt,** because the other keys are taken. Ctrl, or Cmd on macOS, is
    the hyperlink gesture (§9). Shift is the terminal's way past mouse
    reporting, and Super is often the window manager's. A browser does
    little with an Alt-click (some save a link), and a surface has no
    downloads.
  - **As on the cells,** so the program hears it as it hears every other
    press: a report at a cell, with Alt set, then the moves and the
    release. A program that reads no mouse loses nothing a surface would
    have told it.
  - **No `press`,** whatever `p` asked for: the press is not the surface's,
    and the program hears it already, through its mouse reporting. Hearing
    it twice, it would act on it twice, such as focusing a pane and then
    moving it.
  - **The press decides,** because a gesture has one owner from its press
    to its release, as a drag holds the pointer (§9.1). A gesture that
    changed hands when a key did would leave each side half of it.
  - **Option on macOS,** because it is the key a Mac user holds for Alt.
    Ghostty reports it as Alt to mouse reporting whatever
    `macos-option-as-alt` says. That setting chooses what Option types,
    and a press types nothing.
- **Why hide:** sending a document and laying it out costs far more than
  placing it. A program scrolling through many surfaces keeps the ones that
  will come back, and only it knows which those are.
- **Why nothing scrolls unless it asks:** a surface is a rectangle of the
  program's choosing, as an image is.
  - A scroll inside a surface competes with the terminal's for the same
    wheel or drag, and on a touch screen a surface that takes drags traps
    the finger. So the terminal owns scrolling by default, and a surface's
    content is whatever the program lays out.
  - Some content cannot be laid out to fit: a select's list longer than
    the screen, a log beside a form. Paging it by placing windows (§5.2)
    on every wheel step costs a round trip per step. A document that asks
    scrolls locally, as a page's element does, and hands a gesture back
    to the terminal at its end, as a browser chains it to the page.
  - **Per axis,** because a list scrolls down and a wide table across, and
    an axis a document did not ask for keeps the default.
  - **On the document,** because whether content scrolls is the content's
    nature, as `overflow` is, while the placement only chooses where it
    shows.
  - **Scrollbars take pixels, not cells,** so a scrollbar's width, which
    differs between hosts, changes no footprint (§5.3).
- **Why controls take the palette:** a field drawn in an engine's own
  colours looks like a web page pasted into the terminal, and differs
  between hosts (Chromium's and Blitz's greys are not the same). The 16
  colours are the one palette every terminal theme designs for contrast,
  so the host stylesheet draws controls with them and nothing else.
- **Why `area`:** a program that shows something next to an element (a
  select's list in a surface of its own, a menu) needs to know where the
  element is, and only the host lays the document out. Terminals call a
  rectangle of cells an area (DEC's rectangular-area operations).
- **Why a field's keys are the program's.** A program that draws a field
  in cells reads its keys from the terminal and edits the field as its own
  keymap says. On a surface the same field is drawn by the host, and should
  edit the same: the same keys, the same moves. The host cannot know which
  keys the program binds, so the program says, in `data-keys`, and what it
  does not give the field stays its own.
  - **Offered as pressed first, then as the program reads them.** A
    focused field on a surface is a GUI control, and gets the keys a GUI
    field gets, before the terminal's shortcuts, as a page gets them
    before a browser's. The terminal's translations exist for programs in
    cells: a macOS terminal sends Control+a for Command+ArrowLeft, which a
    field would read as select all. What the field does not use goes on as
    before, so the terminal's shortcuts keep their keys elsewhere, and the
    user's remapping still reaches the program and the field as bytes. In
    cells a program reads only bytes, and Command+ArrowLeft stays
    Control+a there.
  - **Inherited,** because a program has one keymap and many fields: it is
    set once, and overridden where a field differs.
  - **A default with a GUI field's keys,** Shift selecting included:
    people's hands know them from every text field, whatever draws it. The
    default takes few of the program's keys: those of a terminal's line
    editor are mostly Control and Alt with a letter, and the one it does
    take, Control+a, readline's line start, is also Home. A program that
    needs one binds it to `program`.
  - **Readline's actions,** with the words and lines of Bubble Tea's text
    input and text area. Terminal programs share them, more or less, so a
    program's cells and its surfaces can share one implementation
    (SDK.md).
  - **Selection by Shift and `select-all`, from the anchor,** as GUI fields
    select. A program that draws a field in cells shows a selection as it
    shows a selected row, and an SDK's field keeps one (SDK.md §4.6).
  - **Copying, cutting, pasting and undo are the keymap's,** with a
    browser's keys: Control+c, Control+x, Control+v and Control+z edit in
    every GUI, and where nothing is selected, or outside a text field,
    they keep their terminal meanings (interrupting, nano's exit, quoting
    the next key, suspending). A program that needs one binds it to
    `program`, as a REPL that always interrupts with Control+c. The
    terminal's own copy and paste stay the user's, so no document makes
    its text uncopyable.
  - **One key per platform, `Mod`,** because binding both Control+c and
    Command+c takes a key from the program on each platform for nothing.
    The rows around it follow the platform too: Control+a is a line's
    start on macOS and Command+a selects all.
- **Why edit commands in the cells.** A program that selects and edits in
  its cells needs the same keys as a field, and those keys mean something
  in a terminal. Neither side can decide alone: the terminal does not know
  whether the program has something selected, and the program cannot read
  the clipboard in order with its keys. So the terminal sends the command
  with its key, the paste with its text, and the program decides, as a
  field decides on a surface. It takes them by name, per screen, as the
  kitty keyboard protocol's flags are taken, so a shell and a full-screen
  editor run in one terminal each get what they asked for.
- **Why key sequences.** Leader keys and which-key menus are how keyboard
  programs grow past the keys they have (Spacemacs, Neovim, Zed, Helix).
  On a surface only the host can wait for the next key without a race,
  so the document declares its sequences on the elements they activate,
  as `accesskey` does, and the host resolves them by myelin's rules.
  - **The element's own keys first,** so a leader never takes Space from a
    button or a letter from a field.
  - **The label is the element's,** its text or `aria-label`, so the menu
    says what the screen says.
  - **In the cells the program resolves them,** since it reads the keys
    anyway, and sends only the menu to draw. One menu, drawn by the host,
    serves both, and a program that builds both from one keymap behaves
    the same in each.
- **Why a host may show no select list.** A select's list opens past its
  control, and a surface is a rectangle of cells: drawn inside, a list
  would force small surfaces to grow, and drawn outside, it is something
  the host places over what the program placed.
  - **Programs draw their own lists anyway,** as web apps wrap or replace
    `<select>` with script. In HOTTY the program plays the script's part: a
    button, and a list in a surface of its own, placed by `area`.
  - **A closed select still works,** with keys as browsers' do, so a
    document that has one loses nothing but the list.
  - **A pick sends `change` at once,** as a browser's select does, rather
    than when focus leaves it: there is nothing more to commit.
- **Why any element can give keys to the program.** A program that works a
  list or a table with the arrows needs them on a focused button too, and
  in a scrolling surface the host would take them to scroll (§5.3). A page
  in a browser stops that with script (`preventDefault`); a surface has
  none, so the document says beforehand, in the `data-keys` it already
  reads for fields.
- **Why `focus` names the element.** Those keys reach the program as
  terminal input, which names no element, and Tab moves focus inside the
  host. A program with a field and a list could not tell which one the
  arrows came from, after a Tab, and acted on the one it last knew. A
  browser's `focusin` names its target in the same way.
  - **The keys stay input,** so the program reads them in the encoding
    it enabled and with its own keymap, as every other key. An event per
    key would carry a second encoding of them.
  - **Every move, not only the first,** because the surface keeps the
    keyboard while focus moves inside it. A program that only wanted to
    know the surface has the keyboard reads the first `focus` after a
    `blur`, as before.
- **Why scrolling keys.** Pagers and viewers in the terminal (less, vim,
  Bubble Tea's viewport, glow) share `j` and `k`, Space and `b`, `g` and
  `G`. A program that scrolls its cells with them should scroll its
  surfaces with the same keys, but only the host scrolls a surface
  (§5.3), and it cannot know which keys the program scrolls with, so the
  program says, as it does for a field's keys.
  - **The element's own keys come first,** so bindings on an element that
    scrolls take neither Space from the buttons in it nor a letter from
    its selects.
  - **A field leaves them out,** or `j` could not be typed in a field
    inside an element that scrolls with it.
  - **Never the terminal:** a key that reached an end and went on to
    scroll the screen would move what the program drew around the
    surface.
- **Why `reveal` and `view`.** Scrolling is local (§5.3), so a program
  could neither follow the reader nor take them somewhere: a table of
  contents beside a document marks the section in view and jumps to one
  on a click, and a long list fetches what comes into view.
  - **Elements opt in,** as they do for clicks: most documents scroll
    with nothing to tell, and a report on every scroll would fill the
    program's input as unasked replies would (§3.5). So the host also
    waits for a scroll to rest.
  - **Every element in view, with its whole area,** so the program keeps
    no state of its own to follow changes, and places what it draws by an
    element as it does by a clicked one (`area`).
  - **`reveal` moves no focus.** Focus already scrolls (§10.1), and taking
    it would move the keyboard from where the user is. Its payload names
    the alignments a reader needs, those of `scrollIntoView`; across,
    where nothing is read in order, as little as it can.

## Appendix C. Prior art

HOTTY takes from:

- **the kitty graphics protocol**: the shape of the envelope (key=value
  controls, chunks, `q`, `C=1`), and placements anchored to cells;
- **Hotwire and Turbo**: HTML over the wire, which the name follows, and
  appending by id;
- **Datastar and idiomorph**: morphing, and matching top-level elements by id;
- **RFC 2392**: the `cid:` scheme.

DomTerm, which renders HTML fragments in a terminal's output, is the closest
related work.
