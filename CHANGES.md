---
group: Reference
order: 30
nav: Changes
description: what each version changed, and how to upgrade
path: changes
---

# Changes

## 0.4

A draft, as every 0.x is, released 2026-10-18 across the stack. It breaks
0.3 (SPEC.md §15): a 0.4 host answers a 0.3 program with `EVERSION`, and
the program falls back (§4, §14).

### What changed

- **Keys are named by *myelin key names* 0.1** (SPEC.md §10.4), which this
  document cites at the tag `myelinkey/v0.1.0` rather than naming keys
  itself. The modifiers are `super`, `ctrl`, `alt` and `shift`. A physical
  key is its W3C code in snake case (`arrow_left`, `page_down`, `key_w`).
  A character is what the key types, a letter written small with `shift`
  as a modifier (`shift+g`). The W3C key values (`Control+a`, `ArrowLeft`,
  `Meta+Enter`) are gone.
- **`mod` is myelin's command modifier** (its §4.4): a binding writes
  `mod+s`. The capabilities' `mod` is `"ctrl"` or `"super"`, and `edit`
  names its keys the new way (§4).
- **A host reads a key a program writes** with myelin's default reading,
  so `G` is `g`, and `meta` is refused (§10.4).
- **A press can have two names,** its physical key and the character it
  types, and a keymap is looked up by the physical one first (§10.4). A
  host that reads bytes names what they carry.
- **Shift falls back only from a key that is not a character** (§10.2):
  `shift+g` is a key of its own. A field types what a key types, a letter
  with `shift` as its capital.
- **`mods` keeps its bits,** and 8 is `super` (§9).
- **A press given to the program as pressed stays the program's** when it
  comes again as bytes, though the field binds its bytes' name, and a
  `prefix` binding starts its prefix (§10.4): `ctrl+key_a=program` in a
  field sends `ctrl+a` on.
- **A modifier tapped alone** is named on its release (`shift_left`,
  `shift`) and goes no further, so a tap bound to `program` or `prefix`
  does nothing (§10.4).
- **A `command`'s `key` is the one name its bytes have,** `ctrl+c`, never
  `ctrl+key_c` (§10.6).
- **A finger can drag in the cells** (§9.6). `a=touch` names areas of the
  screen, each with the way it drags. There, while the program reads the
  mouse, a touch drag that way and a tap reach the program as the mouse's
  primary button. Elsewhere, and the other way, a touch drag still
  scrolls. It adds to 0.3 and changes nothing a program already does.
- **The name is written hotty,** in lowercase, even at the start of a
  sentence: "hotty 0.4", "a hotty host". Nothing on the wire changes, and
  neither do identifiers, environment variables or task ids. The text of
  0.1 to 0.3 stays as it was released.

### Upgrading from 0.3

**A program:**
- Write keys in the new names: in `data-keys`, in a menu's item keys and
  `seq`, and wherever you compare a `command`'s `key`. `Mod+s` is
  `mod+s`, and `Control+A` is `ctrl+shift+a` (§10.4).
- Read the capabilities' `mod` as `"ctrl"` or `"super"`, and `edit` in the
  new names (§4).
- Bind Shift with a letter as `shift+<letter>`: a host reads `G` as `g`.
- If you read the mouse to drag something in your cells, such as a
  slider, send its cells with `a=touch` so that a finger drags it too, and
  send them again when it moves (§9.6).

**A host:**
- Read a written key with myelin's default reading, `mod` standing for
  your `mod`. Refuse `meta`, and a binding with `mod` and `ctrl` or
  `super` as well (§10.4).
- Name a press seen as pressed by its physical key and by the character
  it types, and look the physical one up first. Name keys from bytes as
  §10.4's table has them.
- Report `mod`, `edit` and a `command`'s `key` in the new names, the
  `key` as its bytes name it (§10.6).
- Keep a press you give the program as pressed, by either name, the
  program's when its bytes come, and start a `prefix` binding's prefix
  then. Offer a modifier tapped alone to the surface, and send it nowhere
  else (§10.4).
- Fall back without `shift` only from a key that is not a character
  (§10.2).
- Take `a=touch`, and keep its areas per screen. In an area, while the
  program reads the mouse, report a touch drag the area's way, and a tap,
  as the mouse's primary button (§9.6).

**A multiplexer** does both lists. A keymap of its own that is myelin's
already speaks these names. One that relays the mouse gives the terminal
the areas of the panes it shows, moved to where each pane is (§9.6).

## 0.3

A draft, as every 0.x is. It breaks 0.2 (SPEC.md §15): it folds what 0.2
grew, for bandwidth and for fewer rules, and programs and hosts move to it
together. The list it folds is `vault/tasks/fold-0.3.md`.

### What changed

- **A delta is one list of ops** (SPEC.md §6.1): `a=delta:s=<name>` and one
  msgpack map, `{"ops": [{"op", "t", "k", "v"}, …]}`, applied in order and
  shown as one. The control keys `op`, `t` and `k`, and the text payload,
  are gone. A frame of fifteen small changes is 184 bytes, not 755. An op
  whose target is missing fails alone, and the reply names it by its index,
  `i`; a malformed op rejects the whole delta. Targets travel as the
  document has them, so an id outside ASCII is addressed as it is.
- **`p`, `f` and `v` belong to the surface** (SPEC.md §5.2): `1` on, `0`
  off, held until the program sends them again. A placement without them
  leaves them as they were. One table in §9 says, for every event, what
  asks for it, how long and how often.
- **Features** (SPEC.md §4): a 0.3 host does every op and event, scrolling,
  steps, drops and `view`. One list, `features`, names what a host may
  lack: `passthrough`, `hover`, `count`, `menu`. The capabilities' `ops`,
  `events`, `passthrough`, `scroll`, `steps`, `drop`, `count`, `keys` and
  `menu` are gone.
- **The cell is in CSS pixels** (SPEC.md §4, §5.3, §8): `cellcss` takes the
  place of `cell`, `resize` is gone, and a new font sends `caps` with the
  new `cellcss`. `--hotty-px` is one device pixel, current through zooms.
  `scale` stays, as a hint for images.
- **`caps` carries any field that changed** (SPEC.md §4, §9), not only
  `mod` and `edit`: a multiplexer whose program moves to another viewer's
  host tells it everything that differs.
- **Event details** (SPEC.md §9): a submit's fields are pairs,
  `{"fields": [[name, value], …]}`; `mods`, one int of modifier bits, goes
  on clicks, presses and drags in place of a drag's `keys`; `t` is absent,
  not empty, where no element is meant; a detail with no field is no
  payload.
- **Errors only, unless asked** (SPEC.md §3.5, §3.6): `q` defaults to 1,
  and to 0 for a query and a command with `n`. Continuation chunks carry
  only `m`.
- **Key sequences are the program's** (SPEC.md §10.5): `data-key`, the
  capabilities' `keys`, and the hosts' sequence engines are gone. A keymap
  action, `prefix`, sends the program every key after it, whatever is
  focused, until it sends `a=focus`.
- **A menu is what a program can do** (SPEC.md §10.7, which takes menus
  out of §10.5): `a=menu` sends the program's actions as a tree, kept per
  screen, each item with a key where one reaches it and a `name`;
  `a=menu:show=1` shows the level the keys typed reach, a few bytes a key,
  and `show=0` hides it. A pick, from a multiplexer's palette or an agent,
  sends `command` with the item's name. A 0.2 menu was one level, shown
  when sent. A host that takes menus has the feature `menu`, for programs
  on surfaces as in the cells.

### Upgrading from 0.2

**A program:**
- Send a frame's changes to a surface as one `a=delta` whose `ops` list
  holds them all (§6.1), not one message per change. Deltas no longer take
  `op`, `t` or `k` in the control.
- Send `p`, `f` and `v` when they change, not with every placement: they
  hold until the program sends them again (§5.2).
- Lay out with `cellcss`, in CSS pixels, and stop handling `resize`: a new
  font sends `caps` with the new `cellcss` (§4). A document that needs a
  device pixel reads `--hotty-px` (§8).
- Ask `features` for `passthrough`, `hover`, `count` and `menu` only, and
  count on every op, every event, scrolling, steps and drops.
- Read a submit's `fields` as pairs, a click's, press's or drag's `mods` as
  bits, and an absent `t` as no element (§9).
- Leave `q` out unless you want more than errors (§3.5).
- Resolve key sequences yourself: bind the keys that start one to `prefix`
  in the keymap, and the keys after it come to you, whatever is focused,
  until you send `a=focus` (§10.5). `data-key` is gone.
- Send what you can do as a menu tree with a `name` per item, show a level
  with `a=menu:show=1` and hide it with `show=0`, and handle `command` with
  a `name` from a pick (§10.7).

**A host:**
- Decode a delta's op list and apply it as one unit. Reply to an op whose
  target is missing with its index `i`, and reject a malformed op's whole
  delta (§6.1).
- Keep `p`, `f` and `v` per surface (§5.2).
- Report `cellcss` and `features`, and send `caps` with every field that
  changed. Send no `resize` (§4).
- Take `q` as 1 when it is absent, and read only `m` on continuation
  chunks (§3.5, §3.6).
- Send event details as §9 has them.
- Route every key after a `prefix` to the program, until it sends
  `a=focus` or the surface loses the keyboard (§10.5).
- Keep a program's menu per screen and show the level its keys reach.
  Report the feature `menu` only if both hold (§10.7). Add no palette for
  it: where you already list commands of your own, you may list its named
  items there, and send a pick as `command` with the item's name.

**A multiplexer** is a host to the programs in its panes and a program to
its terminal, so it does both lists. Besides them:
- Answer a pane's query for the terminal whose keys reach that pane, and
  when that terminal changes, send the pane `caps` with every field that
  differs from what it last heard (§4).
- Replay a surface with its `p`, `f` and `v`: they are the surface's now,
  not a placement's.
- Keep each pane's menu and show its levels, or leave `menu` out of the
  features you report and answer a pane's `a=menu` with `EINVAL` (§10.7).
  You may offer the menu in a palette of your own, or to whatever drives
  the pane, and send picks to the pane as `command`.
- While a surface you relay has the keyboard, give its pane every key you
  read, after your own shortcuts. A prefix asks nothing of you, since the
  keys the surface uses never reach you (§10.5).

## 0.2

A draft, as every 0.x is. It breaks 0.1 (SPEC.md §15): programs and hosts
move to it together. It ships with hottyterm's release that pins hotty-blitz
a70065f and with xterm-addon-hotty 0.1.0-next.8.

### What changed

- **A host's bodies are msgpack** (SPEC.md §3.3): the capabilities, an
  error's body, and every event's detail are one msgpack map, with nothing
  after it, nested at most 32 deep. What a program sends is unchanged: text
  and bytes.
- **Each field has a type**, and keeps it from 0.2 on: `int`, `float`, `str`,
  `bool`, arrays and maps of them. A float is sent as a float even when
  whole. A known field of another type fails the body; unknown fields are
  skipped.
- **A body holds nothing a host does not send**, anywhere in it: no nil,
  keys that are strings and each given once, UTF-8 strings, ints within
  2^53 − 1 of zero, and timestamps msgpack defines. A body that breaks one
  does not decode, and the message stands without it (SDK.md §3.9).
- **A query lists the versions the program speaks** (SPEC.md §4):
  `a=q:n=1:v=0.2`. A host answers in the highest it shares, or with the new
  error `EVERSION`, its detail the versions it speaks. A program takes as a
  host only an answer whose capabilities decode and name a version it
  speaks. A 0.1 program on a 0.2 host, and a 0.2 program on a 0.1 host,
  each find no host and draw in cells.

### Added within 0.2

What follows came after the first 0.2 hosts, and keeps the version: a host
that lacks it says so in its capabilities.

- **`reveal`** (SPEC.md §6.1), a delta that scrolls an element into view:
  its top to the top with `start`, its bottom to the bottom with `end`,
  and by as little as it takes with neither. It moves no focus. A program
  asks `Supports(c, "reveal")`.
- **`view`** (SPEC.md §9.5), an event: the elements with `data-on~=view`
  and an id that are in view, each with its area, and whether the
  document shows its end. A host sends it once the document is laid out,
  then on each change, once a scroll comes to rest. A program asks
  `Views(c)`.
- **`limits.message`** (SPEC.md §13): a host may limit the decoded size of
  one reassembled message and reports it under `limits` (§4). Past it a
  message is malformed (§3.7), not `EQUOTA`, and its further chunks are
  dropped; a host that reports none enforces none, and one with a limit
  should accept at least 1 MiB decoded. A resource is one message, so this
  limit also caps the largest resource. A program may limit what it decodes
  from its host the same way: each SDK's Decoder takes `Max`, 16 MiB by
  default (SDK.md §3.6).

- **A click's `count`** (SPEC.md §9): a click that quickly follows another
  on the same element carries its place in that run, 2 for the second
  click of a double click, as the platform counts them by the user's own
  settings. Every click of a run is reported. A host that counts reports
  `count: true` in its capabilities.
- **Drops** (SPEC.md §9.1): an element with `drop` in its `data-on` can be
  where a drag goes, `t`, without being dragged, and keeps its text
  selection. When such a `t` has `data-steps`, `drag` and `dragend` say
  where in it the pointer is, `tx` and `ty`, and a `drag` goes out when that
  step changes: a row with `"0 1"` splits into halves, a folder with `"0 2"`
  into before, into and after. A host that does both reports `drop: true`.
- **Copying** (SPEC.md §10.2, §11): the new action `copy`, which the
  default keymap binds to Control+c and Meta+c (Command+c). A text field's
  keymap copies its selection; a selection elsewhere in a document is
  copied by the keymap of the element it starts in, which the host offers
  each key first, keyboard or not. With nothing selected, in a password
  field, or under `Control+c=program`, the key goes to the program: Control+c
  still interrupts. The terminal's own copy keys and menu copy whatever
  the keymaps say. A double click selects a word, a triple click a block,
  and Linux hosts put a selection in the primary selection. There is one
  selection across the host. No wire change and no capability.
- **Cutting, pasting and undo** (SPEC.md §10.2, §11): a text field's
  default keymap binds Control+x and Meta+x to the new action `cut`,
  Control+v and Meta+v to `paste`, Control+z and Meta+z to `undo`, and
  Control+Z, Control+y and Meta+Z to `redo`. Each field keeps its own
  history, as a browser's does; a value the program sets clears it. `cut`
  with nothing selected, or in a password field, leaves the key to the
  program. The terminal's own paste types into a field that has the
  keyboard. A host that does not know the actions leaves the keys to the
  program, as before; no capability.
- **`Mod` and the edit shortcuts** (SPEC.md §10.2, §10.4): a binding's
  `Mod` is Meta on macOS and Control elsewhere, reported as `mod`. The
  default keymap now binds each edit action once, to the host's edit
  shortcuts (Mod+a, Mod+c, Mod+x, Mod+v, Mod+z, Mod+Z, and Control+y where
  Mod is Control), which the user may change and the host reports as
  `edit`. Its other rows follow the platform: Control+ArrowLeft moves by a
  word where Mod is Control; Meta+ArrowLeft and Control+a go to the line's
  start where it is Meta. A Linux host no longer binds Meta+c, nor a macOS
  host Control+c. Breaks 0.2 in place.
- **Key sequences** (SPEC.md §10.5): `data-key="<leader> f n"` gives an
  element a sequence that clicks or focuses it, with groups, `<leader>`
  and a timeout reported as `keys`, by myelin's rules. While one waits the
  host shows a which-key menu of the elements' labels.
- **Commands in the cells** (SPEC.md §10.6): `a=edit:take=copy,paste,…`
  makes the edit shortcuts reach a program as the event `command`, with
  their key and, for a paste, the clipboard's text, per screen. The
  terminal's selection is still copied first, and its menus send commands
  without a key. `a=menu` shows a program's which-key menu, a msgpack map
  as myelin's levels are, reported as `menu`. `caps` says when `mod`,
  `edit` or `keys` change, and sends one that became absent empty
  (`"edit": {}`). `command` and `caps` belong to no surface.

Each SDK has the builder `Reveal`, the event's `View` (`Areas` and `AtEnd`,
from `in` and `end`), `Views`, the event's `Count`, the drag's `tx` and
`ty`, and the capabilities' `Count` and `Drop`.

### Porting

A port that compiles can still be wrong. SDK.md Appendix C lists what ports
got wrong; the two that cost most:

- **A clicked link is `Link`, not a field.** 0.1's hotty-go read any detail
  through `Event.Fields()`, so programs found a link's href as
  `Fields()["href"]`. In 0.2 `Fields` holds a submit's fields only, and a
  link click carries `Link` (`Href`, `URL`). After a mechanical port, link
  clicks silently go nowhere.
- **Read the event's fields, never its detail.** Code that unmarshals
  `ev.Detail` as JSON reads zero values from msgpack: a checkbox that is
  always unchecked. Use `Checked`, `Value` and the rest.

And a test that plays the host answers with msgpack capabilities naming
0.2 (hotty-go: `hottytest.Body`, or `hottytest.Host`), or the program under
test falls back to text.

### In each SDK

- **hotty-go** (Go): the wire types are data, with functions beside them.
  `m.Reply()` is `hotty.ReplyOf(m)`, `m.Event()` is `hotty.EventOf(m)`,
  `r.Caps()` is the field `r.Caps` (nil when none) or `hotty.CapsOf(body)`,
  `r.Err()` is `hotty.Err(r)`, `c.Supports(op)` is `hotty.Supports(c, op)`,
  and an event's accessors (`Value()`, `Checked()`, `Link()`, `Size()`,
  `FitRows()`, `Drag()`, `Hover()`, `Area()`, `Fields()`) are its fields.
  A host or relay answers a query with `hotty.ReplyQuery`.
- **hotty-ts** (TypeScript) and the **Python client**: the reader keeps an
  int apart from a float; `query()` sends `v`.
- **hotty-lua**: `hotty.msgpack.decode(s)` returns `value, kinds`, where
  `kinds[t][k]` tells a float, bin, array, time or extension apart from
  what Lua alone cannot.
- **hotty-blitz** and **xterm-addon-hotty**, the hosts: they send msgpack
  and answer queries by version.
