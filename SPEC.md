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
- Where a host must send a value that contains `:`, `;`, `=` or a control
  character (an element id, say), it replaces each such character with `_`.

### 3.3 Payload

`<payload>` is the command's body, **base64** encoded (RFC 4648, standard
alphabet).
- Hosts **MUST** accept base64 with or without padding, and ignore
  whitespace in it.
- A body **MAY** be compressed with zlib (RFC 1950) before encoding, and
  marked `o=z`.
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
| `a` | the action: `q`, `doc`, `place`, `hide`, `patch`, `res`, `del`, `focus`, `blur` from the program (§4–§10); `ok`, `err`, `ev` from the host |
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
| `EQUOTA` | over one of the host's limits (§13) |
| `EBUDGET` | the host gave up on work that exceeded its time budget (§13) |

Replies travel on the program's input, interleaved with whatever the user
types. A program that does not want them sends `q=2`.

### 3.7 Malformed messages

A malformed message:
- a control that does not parse;
- a payload that is not valid base64 or zlib;
- an aborted chunked message.

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

The capabilities object:

| field | meaning |
| --- | --- |
| `v` | the HOTTY version the host implements, as a string: `"0.1"` for this document |
| `ops` | the patch ops it supports (§6) |
| `events` | the event kinds it can send (§9) |
| `cell` | `{"w": …, "h": …}`: the cell size in device pixels |
| `scale` | device pixels per CSS pixel |
| `scheme` | `"dark"` or `"light"`: the terminal's colour scheme |
| `limits` | the host's limits (§13), such as `{"resources": <bytes>, "surfaces": <count>}` |
| `net` | the host's network policy (§7.2), from directive to sources, such as `{"img-src": ["https://example.com"]}`. Absent or empty: the host fetches nothing from the network |
| `host` | optional: a name for the implementation |

Programs **MUST** ignore fields they do not know.

## 5. Surfaces

A **surface** is one HTML document, named by the program, and at most one
**placement**: a rectangle of cells showing it.

### 5.1 Documents: `a=doc`

```
ESC ] 7279 ; a=doc:s=<name> ; <HTML> ST
```

- The payload is an HTML document or a fragment, parsed with the HTML parsing
  algorithm. It creates the surface, or replaces its whole document.
- Replacing a document keeps the surface's placement and size.
- The document's `<base href>` sets its base URL (§7.3), and its
  `<meta name="hotty-network">` asks for network access (§7.2).
- The host applies its stylesheet (§8) and the security rules (§12) before
  the document is shown.

### 5.2 Placement: `a=place`

```
ESC ] 7279 ; a=place:s=<name>:c=<cols>[:r=<rows>|auto][:x=<col>][:y=<row>][:w=<cols>][:h=<rows>][:C=1] ST
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
- Only the window is shown, and only the window receives the pointer.
- **What does not fit is clipped.** The document's root does not scroll, and
  the host shows no scrollbar for it. An element whose `overflow` is `auto`
  or `scroll` scrolls within the surface as usual; the host handles that
  scrolling.
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
  resolved when it arrives.
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
reads HOTTY messages from its input.

| `e` | when | detail |
| --- | --- | --- |
| `click` | activating a `button`; an `a` or `summary`; an `input` of type `button`, `submit` or `reset`; or any element with `data-on~=click` | `{"href": …, "url": …}` for links (below); `{"value": …}` when the element has a `value` attribute; otherwise none |
| `change` | a checkbox or radio button toggled; a text control, `textarea` or `select` whose value changed, when the change is committed (focus leaves it, including when the surface loses the keyboard) | `{"checked": …, "value": …}` for checkboxes and radio buttons, `{"value": …}` otherwise |
| `input` | every edit of a control with `data-on~=input` | `{"value": …}` |
| `submit` | a form submitted (a submit button, or Enter in a text field) | the form's fields as an object of names to values, the submitter's included |
| `focus`, `blur` | the surface gains or loses the keyboard (§10); `t` is empty | none |
| `resize` | the surface's pixel size changed without its cells changing (§5.3); `t` is empty | `{"w": …, "h": …}` in CSS pixels |

- **The element that reports** a `click` is the nearest one, from the target
  of the click outward, that is one of those kinds. If it has no `id`,
  nothing is reported: the id is the program's handle. A link is the
  exception: its `href` is the handle, and `t` is then empty.
- **Links.** A link's detail carries `href`, the program's value, and `url`,
  the `href` resolved against the document's base URL (§7.3). `url` is
  absent when it would be under `https://hotty.invalid/`.
- **A surface never navigates.** A click on a link is an event, and the
  program decides what it means: it may show another page, or ask its
  platform to open the link. Forms never submit anywhere: `submit` is all
  that happens.
- **Opening links.** A host **MAY** open a link whose `url` is `http`,
  `https` or `mailto` outside the surface (a new tab or window, or the
  system's handler) when the user asks for that with the gesture that means
  it on the host's platform: a middle click, a Ctrl or Cmd click, a context
  menu. It then sends the `click` with `"opened": true` in the detail, so
  the program does not open it again. A plain click opens nothing.
- **Local behaviour stays local.** HTML's own default actions happen in the
  host without a round trip:
  - focus, the caret and typing in text fields;
  - toggling checkboxes, radio buttons and `<details>`;
  - hover;
  - scrolling of overflowing elements.
- **The detail** is a JSON value, base64-encoded. Values are the program's
  (§7): an `href` is reported as the document has it.

## 10. Keyboard and focus

### 10.1 Who has the keyboard

A surface **has the keyboard** when the user clicks into it or the program
gives it with:

```
ESC ] 7279 ; a=focus:s=<name>[:t=<element id>] ST
```

- **With `t`:** the element is focused (`ENOTARGET` if there is none).
- **Without `t`:** the surface's focused element keeps focus, or else the
  first focusable element receives it.
- **Echo:** no `focus` event is sent for focus the program gave.

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
  patch op is `EINVAL`.
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
parsing, resources and the envelope. They inspect documents, not pixels.

To be tested, a host exposes a way to *inspect* an element, reporting:
- its tag;
- its attributes with the program's values (§7);
- its text;
- its child elements as `[tag, id, text]`.

This is a test interface, not part of the wire protocol.

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
- **Why ids and patches.**
  - Addressing by id keeps a patch's effect predictable, and makes an update
    cost what it changes.
  - `morph` without a target also serves programs that redraw their whole
    tree (immediate mode) while keeping what the user was doing.
- **Why no script:** it keeps the sandbox small enough to defend, and the
  program in charge.
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
- **Why hide:** sending a document and laying it out costs far more than
  placing it. A program scrolling through many surfaces keeps the ones that
  will come back, and only it knows which those are.
- **Why clip rather than scroll the root:** a surface is a rectangle of the
  program's choosing, as an image is. A root scrollbar would also change the
  layout's width from host to host.

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
