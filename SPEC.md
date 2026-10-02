# HOTTY — HTML Over The TTY

    Version:  0.1
    Status:   Draft. Versions 0.x may change incompatibly (§15).
    Licence:  CC BY 4.0 (this document); the conformance vectors are
              Apache-2.0.

## Abstract

HOTTY lets a program running in a terminal show **surfaces**: small HTML
documents drawn by the terminal into rectangles of cells, the way the kitty
graphics protocol places images. The program sends markup and patches
in-band, as escape sequences in its ordinary output, so it works over a pty,
over SSH and through anything else that carries a terminal's bytes. The
terminal lays the markup out, draws it, and handles focus, typing and hover
itself. What the user does comes back to the program as events on its input.

There is no script and no network. The program is the application: it holds
the state and decides what every event means. The terminal is the view. A
surface can do nothing the program did not send it, and can learn nothing
the program did not give it.

## Contents

1. Introduction
2. Conventions
3. The envelope
4. Detection and capabilities
5. Surfaces
6. Patches
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
  patches the document and hears about events. It never runs code in the
  terminal.
- **Degradable.** A program asks whether the terminal is a HOTTY host before
  using it, and paints ordinary text when it is not. Terminals that are not
  hosts ignore HOTTY sequences.
- **Cheap to update.** Changes are patches addressed by element id, so a
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
- **Surface**, **resource**, **patch**, **event**: §5, §7, §6 and §9.
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
- Text bodies (markup, patch values) are UTF-8.

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
- A host **MAY** limit the size of a reassembled message. It **SHOULD** accept
  at least 1 MiB decoded.

### 3.5 Common keys

| key | meaning |
| --- | --- |
| `a` | the action: `q`, `doc`, `place`, `hide`, `patch`, `res`, `del`, `detach`, `focus`, `blur` from the program (§4–§10); `ok`, `err`, `ev` from the host |
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
- `a=err` carries a JSON body `{"code": …, "detail": …}`. The codes:

| code | when |
| --- | --- |
| `EINVAL` | an unknown action or op; a bad surface name; a missing `s`, `t`, `k`, `c` or `id`; `c` or `r` out of range |
| `ENOENT` | no surface of that name |
| `ENOTARGET` | no element with that id. The detail is the id, or the missing ids comma-separated (§6.2) |
| `EDETACHED` | the surface is detached (§5.5) |
| `EQUOTA` | over one of the host's limits (§13) |
| `EBUDGET` | the host gave up on work that exceeded its time budget (§13) |

Replies travel on the program's input, interleaved with whatever the user
types. A program that does not want them sends `q=2`.

### 3.7 Malformed messages

A malformed message:
- a control that does not parse;
- a payload that is not valid base64 or zlib;
- an aborted chunked message.

Each counts once: a malformed message that arrives before the last chunk of
another aborts it (§3.4), and makes two, the aborted message and itself.

The host **MUST NOT** act on it. It sends no reply, since it cannot know what
the program meant. It **MAY** log it.

## 4. Detection and capabilities

A program finds out whether it has a host by sending a query, then Primary
Device Attributes as a fence:

```
ESC ] 7279 ; a=q:n=1 ST   CSI c
```

Every terminal answers DA1. A host answers the query first:

```
ESC ] 7279 ; a=ok:n=1:re=q ; <base64 JSON> ST
```

If the DA1 answer arrives with no HOTTY reply before it, there is no host. The
program **SHOULD** then fall back (§14).

A DA1 answer may belong to a question asked earlier, by the program or by
whatever ran before it. A program **MAY** wait a little after a DA1 that
arrives before any reply, for the reply and the DA1 behind it. A host answers
the query before that DA1, so the wait costs a terminal that is not a host
only that little. SDK.md sets how long.

The capabilities object:

| field | meaning |
| --- | --- |
| `v` | the HOTTY version the host implements, as a string: `"0.1"` for this document |
| `ops` | the patch ops it supports (§6) |
| `events` | the event kinds it can send (§9). `drag` stands for `dragstart`, `drag` and `dragend` (§9.1) |
| `cell` | `{"w": …, "h": …}`: the cell size in device pixels |
| `scale` | device pixels per CSS pixel |
| `scheme` | `"dark"` or `"light"`: the terminal's colour scheme |
| `limits` | the host's limits (§13), such as `{"resources": <bytes>, "surfaces": <count>}` |
| `net` | the host's network policy (§7.2), from directive to sources, such as `{"img-src": ["https://example.com"]}`. Absent or empty: the host fetches nothing from the network |
| `passthrough` | `true` when the pointer passes through the parts of a surface that take no pointer (§9.3). Absent: every window takes the pointer wherever it is |
| `host` | optional: a name for the implementation |
| `version` | optional, with `host`: the implementation's version, as dot-separated numbers compared one by one (`"0.0.10"` is after `"0.0.9"`) |

Programs **MUST** ignore fields they do not know.

## 5. Surfaces

A **surface** is one HTML document, named by the program, and at most one
**placement**: a rectangle of cells showing it.

### 5.1 Documents: `a=doc`

```
ESC ] 7279 ; a=doc:s=<name>[:d=1] ; <HTML> ST
```

- The payload is an HTML document or a fragment, parsed with the HTML parsing
  algorithm. It creates the surface, or replaces its whole document.
- Replacing a document keeps the surface's placement and size.
- `d=1` creates the surface detached (§5.5), so a program that will hear
  nothing from a document, even one it keeps patching, gives it up in the
  same command. A document sent without `d=1`
  makes the surface the program's, whether it was detached or not.
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
  patch changes it (§6), or the cell size changes (§5.3).
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
- **What does not fit is clipped, and nothing in a surface scrolls.**
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
    (§5.2). So the whole screen scrolls, with its surfaces in it. A
    surface never scrolls on its own, however small.
- When the cell size changes (a zoom or a font change), the rectangle keeps
  its cells and changes its pixels. The host lays the document out again,
  with no involvement from the program, and sends `resize` (§9).
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

A program removes a placement and keeps its surface with `a=hide`:

```
ESC ] 7279 ; a=hide:s=<name> ST
```

- The document stays as it is, with what the user did in it, and patches
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
  hidden, patched and deleted as before, and moves with its line (§5.4).
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
    and `button`, including those patches add later, acts as if it had the
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

## 6. Patches

### 6.1 `a=patch`

```
ESC ] 7279 ; a=patch:s=<name>:op=<op>[:t=<element id>][:k=<name>] ; <payload> ST
```

Patches change one surface's document, addressing elements by id.

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

- **Missing arguments:** `t` is required except for `morph`, and `k` for
  `attr`, `unattr` and `var`. A missing one is `EINVAL`, and an unknown op is
  `EINVAL`.
- **A missing target** is `ENOTARGET`, with the id as the detail.
- **Context:** a payload is parsed as a fragment in the context of the
  element it will become a child of, so table rows, cells and list items
  parse as they would in place.
- **The cheap path:** `var` and `text` are the patches that change every
  frame (a bar's width, a clock). A host **SHOULD** make them cheap.

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
  that would exceed it is refused with `EQUOTA`.
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
  --hotty-cell-w: …px;             /* one cell, in CSS pixels */
  --hotty-cell-h: …px;
  --hotty-font: <the terminal's font family>, monospace;
  font-family: var(--hotty-font);
  font-size: <the terminal's font size>;
  line-height: var(--hotty-cell-h);  /* so 1rlh is one row */
  color: var(--hotty-fg);
  background: var(--hotty-bg);
  overflow: hidden;                /* §5.3 */
}
body { margin: 0; }
```

- `prefers-color-scheme` follows the terminal's scheme.
- When the terminal's theme, font or cell size changes, the host updates the
  stylesheet and draws every surface again.

The custom-property prefix `--hotty-` and the attribute prefix `data-hotty-`
are reserved for this specification.

## 9. Events

```
ESC ] 7279 ; a=ev:s=<name>:e=<kind>:t=<element id> [; <base64 JSON detail>] ST
```

The host reports what the user did. Events are not replies: they are sent
whatever the value of `q`. Like replies (§3.6), they arrive on the program's
input, interleaved with the user's keys, so a program that places surfaces
reads HOTTY messages from its input. A detached surface sends none (§5.5).

| `e` | when | detail |
| --- | --- | --- |
| `click` | activating a `button`; an `a` or `summary`; an `input` of type `button`, `submit` or `reset`; or any element with `data-on~=click` | `{"href": …, "url": …}` for links (below); `{"value": …}` when the element has a `value` attribute; otherwise none |
| `change` | a checkbox or radio button toggled; a text control, `textarea` or `select` whose value changed, when the change is committed (focus leaves it, including when the surface loses the keyboard) | `{"checked": …, "value": …}` for checkboxes and radio buttons, `{"value": …}` otherwise |
| `input` | every edit of a control with `data-on~=input` | `{"value": …}` |
| `submit` | a form submitted (a submit button, or Enter in a text field) | the form's fields as an object of names to values, the submitter's included |
| `press` | the primary button pressed, or a tap, anywhere in the window of a surface placed with `p=1` (§5.2), except with Alt held (§9.2) and where the pointer passes through (§9.3) | none |
| `dragstart` | a mouse's or a pen's primary button pressed on an element with `data-on~=drag` (§9.1), without Alt (§9.2) | `{"c": …, "r": …, "keys": […]}`: the pointer's cell and the keys held (§9.1) |
| `drag` | during a drag, the element under the pointer changed (§9.1) | the same |
| `dragend` | the drag ended: the button released, wherever the pointer is (§9.1) | the same |
| `focus`, `blur` | the surface gains or loses the keyboard (§10); `t` is empty | none |
| `resize` | the surface's pixel size changed without its cells changing (§5.3); `t` is empty | `{"w": …, "h": …}` in CSS pixels |
| `fit` | on a placement made with `f=1` (§5.2), the rows the document needs at the placement's width changed; `t` is empty | `{"r": …}`: the rows `r=auto` would choose now |
| `hover` | on a placement made with `v=1` (§5.2), the element the pointer is over changed, or the pointer left the window (§9.4) | `{"c": …, "r": …}`: the pointer's cell (§9.1); `{"out": true}` when it left, with `t` empty |

- **The element that reports** a `click` is the nearest one, from the target
  of the click outward, that is one of those kinds. If it has no `id`,
  nothing is reported: the id is the program's handle. A link is the
  exception: its `href` is the handle, and `t` is then empty.
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
- **Gestures that scroll are the terminal's.** A wheel, a touchpad's
  scroll, or a touch drag over a surface does what it would do over the
  cells beneath it. That is scrollback, or on the alternate screen, the
  program's wheel input. The host **MUST** pass them on, with the position
  of the pointer or the finger. Taps, clicks, long presses, and a mouse's
  or a pen's drags (§9.1) stay the surface's, unless they begin with Alt
  held (§9.2).
- **The detail** is a JSON value, base64-encoded. Values are the program's
  (§7): an `href` is reported as the document has it.
- **Unknown kinds.** A program **MUST** ignore an event whose kind it does
  not know: later versions add kinds (§15). The capabilities list the kinds
  a host sends (`events`, §4).

### 9.1 Drags

An element opts in to drags with `drag` in its `data-on`, as it opts in to
clicks with `click`. A **drag** is a press of a mouse's or a pen's primary
button on such an element, the moves of the pointer while the button is
down, and its release. A program hears through drags what a click cannot
carry: a range dragged across a grid, a handle dragged to where it is let
go.

- **Three events:**
  - `dragstart`, on the press. `t` is the element that opted in: the
    nearest one, from the pressed element outward, with `drag` in its
    `data-on`. If it has no `id`, there is no drag.
  - `drag`, each time the element under the pointer changes. `t` is the
    nearest element with an `id` and `drag` in its `data-on`, from the one
    under the pointer outward, and empty where there is none, outside the
    window included. While `t` is empty, a `drag` is sent each time the
    cell under the pointer changes instead.
  - `dragend`, once, on the release, wherever the pointer is. `t` is as
    for `drag`.

  A drag therefore costs a few events for each element it crosses, not one
  for every move.
- **The detail** of each is `{"c": …, "r": …, "keys": […]}`:
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
- **The pointer is the surface's until the release,** as a page's
  `setPointerCapture` makes it an element's. Every move goes to the drag,
  wherever the pointer is: over the cells, over another surface, or outside
  the terminal's window where the platform allows it. None of it reaches
  anything else: no other surface, no `hover` (§9.4), and no mouse
  reporting to the program.
- **A drag selects no text.** A press on an element that opts in starts no
  text selection, whatever its CSS, as if it had `user-select: none` (§11).
- **Mouse and pen only.** A touch on an element that opts in does what it
  does on any other: a touch drag scrolls (§9), and a tap is a click, which
  only `click` reports.
- **Order.** The press that starts a drag is a press like any other
  (§10.1). `press`, if the placement asked for it, comes first, then
  `dragstart`, then everything else the press causes (`change`, `blur`,
  `focus`). On the release, `dragend` comes before any `click`.
- **A drag is a click only where it began.** When it ends on the element
  it started on (`dragend`'s `t` is `dragstart`'s), its release is the
  click it would have been without the drag: an element with `click` in its
  `data-on` as well reports `click`, after `dragend`. A drag that ends
  anywhere else reports no `click`.
- **What ends a drag early.** The host sends `dragend` at once, with `t`
  empty and the last cell the pointer was on, when before the release:
  - the surface's placement goes away (`a=hide`, or its line leaving the
    screen);
  - a new document replaces the surface's (`a=doc`);
  - or the host loses the pointer.

  A surface that is detached or deleted during a drag reports nothing more
  (§5.5). Nothing else ends a drag: neither a patch nor a new placement
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
- **Mouse and pen only.** A tap is a click whatever the keys held.

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
  empty where none has an id. The detail is `{"c": …, "r": …}`, the cell
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
- **Mouse and pen.** A touch's moves scroll (§9) and hover nothing. A tap
  is a press and a release: at its release, a host **MAY** report what it
  landed on, as browsers leave `:hover` on what a tap touched.
- **Not the keyboard's.** Focus moving, to the surface or away from it,
  changes nothing: a window reports the pointer whether or not it has the
  keyboard (§10).
- **Under a pointer that does not move.** When a patch, a new document, a
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
- **A click** is a press of the primary button without Alt (§9.2), or a
  tap.
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
or reaches the program:

| focused element | keys it uses (unmodified, or with Shift only) |
| --- | --- |
| text-like `input` | printable characters, Space, Backspace, Delete, Left, Right, Home, End, Enter |
| `textarea`, `contenteditable` | the same, plus Up, Down, Page Up and Page Down |
| `select` | printable characters, Space, Up, Down, Home, End, Page Up, Page Down, Enter |
| `button`, `a`, `summary`, checkbox, radio button | Space and Enter |

- **Tab and Shift+Tab** move between the surface's focusable elements. Past
  the last one, or before the first, the surface loses the keyboard: the
  host sends `blur` and the terminal has the keyboard again.
- **Escape** is never used by the surface. It reaches the program, which
  decides, for instance by sending `a=blur`.
- **Every other key** reaches the program as ordinary terminal input, in the
  keyboard encoding the program has enabled. A program's own keymap therefore
  keeps working while a surface holds the keyboard.

### 10.3 Key releases

HOTTY has no key events of its own. A program that needs to know when a key is
released (a game, say) enables the kitty keyboard protocol with *report event
types*. That is an ordinary terminal feature, and works the same with or
without HOTTY.
- The alternate screen keeps its own stack of keyboard flags, so a
  full-screen program enables them after switching to it.
- A surface that does not have the keyboard does not affect the keys at all.

## 11. Text

A surface is drawn as pixels, but it is never only pixels: the host holds its
document, and therefore its text.

- **Selecting and copying** inside a surface **SHOULD** copy the selected
  text of the document.
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
- Rendering must not stall the terminal. A host **MAY** abandon a render
  that exceeds its time budget and report `EBUDGET`: pathological CSS such
  as huge blurs, deep nesting, or enormous documents.

## 14. Degradation

A program **SHOULD** work without a host.
- When detection (§4) finds none, it paints its interface as terminal text,
  and should not send HOTTY commands to a terminal that is not a host.
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
- A host **MUST** ignore control keys it does not know. An unknown action or
  patch op is `EINVAL`. A program **MUST** ignore event kinds (§9) and
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

A host conforms to HOTTY version 0.1 when:
- it meets every **MUST** of this document;
- it passes `conformance/vectors.json` (`conformance/README.md`).

The vectors check replies, error codes, every patch op, morph, context
parsing, resources, drags, presses with Alt, `fit`, hover and the
envelope. They inspect documents and events, not pixels. The vectors marked
`"passthrough"` apply to a host that reports it (§9.3), and those marked
`"hover"` to a host whose `events` list it (§9.4).

To be tested, a host exposes a way to *inspect* an element, reporting:
- its tag;
- its attributes with the program's values (§7);
- its text;
- its child elements as `[tag, id, text]`.

It also lets a test move a mouse's pointer to the centre of an element, or
of a cell of a surface, press and release its primary button there, with
modifier keys held, and take the pointer out of the terminal's window. A
host with `passthrough` also tells the test whether each of those reached
the surface or passed through it.

This is a test interface, not part of the wire protocol.

A library that speaks HOTTY for programs, an SDK, conforms when it meets
[SDK.md](SDK.md) and passes the vectors' SDK sections: `build`, `encode`,
`decode`, `scan` and `detect`.

---

## Appendix A. Examples

Detection (payload shortened):

```
program → ESC ] 7279 ; a=q:n=1 ST  CSI c
host    → ESC ] 7279 ; a=ok:n=1:re=q ; eyJ2IjoiMC4xIiwib3BzIjpb… ST  CSI ? 62 ; 22 c
```

A card placed below the prompt, then a patch and an event:

```
program → ESC ] 7279 ; a=doc:s=card:q=2 ; PGJ1dHRvbiBpZD1nbz5HbzwvYnV0dG9uPg== ST
          (<button id=go>Go</button>)
program → ESC ] 7279 ; a=place:s=card:c=40:r=auto ST
host    → ESC ] 7279 ; a=ok:s=card:re=place:c=40:r=2 ST
program → ESC ] 7279 ; a=patch:s=card:op=text:t=go:q=2 ; U3RhcnQ= ST
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
program → ESC ] 7279 ; a=patch:s=dash:op=var:t=cpu:k=p:q=2 ; NDI= ST        (--p: 42)
program → ESC ] 7279 ; a=patch:s=dash:op=text:t=clock:q=2 ; MTI6MDA6MDE= ST  (12:00:01)
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
- **Why hosts do not compress.** Replies and events are small, and zlib is
  the one dependency a program would need only to read them. Programs keep
  it for what they send, where documents are large.
- **Why ids and patches.**
  - Addressing by id keeps a patch's effect predictable, and makes an update
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
  knows the surfaces' names; otherwise they keep reporting until they are
  deleted or leave the scrollback, as a crashed program can leave mouse
  reporting on.
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
  - **Mouse and pen only,** because a touch drag scrolls (below): a surface
    that took touch drags would trap the finger. A tap is still a click.
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
- **Why nothing scrolls:** a surface is a rectangle of the program's
  choosing, as an image is.
  - A scrollbar would change the layout's width from host to host.
  - A scroll inside a surface would compete with the terminal's for the
    same wheel or drag. The user could not tell which one a gesture
    moves.
  - On a touch screen, a surface that takes drags traps the finger: the
    screen stops scrolling wherever a surface is.

  The terminal owns scrolling, and a surface's content is whatever the
  program lays out.

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
