---
group: Concepts
order: 50
nav: Keyboard and focus
description: who has the keyboard, which keys a surface keeps, and how the rest reach the program
---

# Keyboard and focus

A surface uses only the keys it needs, and every other key reaches the
program as ordinary terminal input. So a program's own keymap keeps
working while one of its surfaces has the keyboard. The program says, in
the document, which keys it wants back.

## Who has the keyboard

The terminal has the keyboard until the user clicks something in a
surface that takes focus, or the program gives it
([§10.1](../../SPEC.md#101-who-has-the-keyboard)). The program gives it
with `a=focus`, naming an element with `t`:

```text
program → ESC ] 7279 ; a=focus:s=login:t=user ST
```

Without `t`, the focused element keeps focus, or else the first element
that can take it does. These take focus on a click, unless disabled:

- `input`, `select`, `textarea` and `button`;
- links with an `href`, except hyperlinks, which are the terminal's;
- the first `summary` of a `details`;
- `contenteditable` elements;
- any element with a `tabindex` of 0 or more.

A click on a `label` is a click on its control. A click on anything else
takes nothing: on a surface with nothing to focus, every key reaches the
program anyway.

The keyboard goes back to the terminal, and the host sends `blur`, when:

- the user clicks the cells, another surface, or an element here that
  takes no focus;
- `tab` moves past the last element, or `shift+tab` before the first;
- the program sends `a=blur`, or hides the surface.

A focused text field commits its value first, so its `change`, if the
value changed, comes before the `blur`. `escape` is never the surface's, except in a select's
open list: it reaches the program, which may send `a=blur`.

A surface cannot take the keyboard on its own: `autofocus` does nothing
([Security](security.md)). A detached surface never has it, and detaching
one that has it gives the keyboard back with no `change` and no `blur`
([§5.5](../../SPEC.md#55-ownership-adetach)).

## Following focus

The host tells the program each time the user moves focus, so the
program knows where the keys come from. A click or a `tab` that focuses an
element sends `focus`, with the nearest id from that element outward.
Here the user typed a name and pressed `tab`:

```text
host → ESC ] 7279 ; a=ev:s=login:e=change:t=user ; {"value": "ada"} ST
host → ESC ] 7279 ; a=ev:s=login:e=focus:t=pass ST
```

Focus that the program gives with `a=focus` sends no `focus` back. A
program that must know the user went to a surface with nothing to focus
places it with `p=1`, and hears `press` ([Input](input.md#presses)).

## The keys a surface uses

While a surface has the keyboard, its focused element takes the keys it
uses, and the rest reach the program ([§10.2](../../SPEC.md#102-keys)):

| focused element | keys it uses |
| --- | --- |
| a text field: an `input` of a text type, a `textarea`, a `contenteditable` | the characters it types, and the keys its keymap binds (below) |
| an `input` of a date or time type | characters, `space`, `backspace`, `delete`, the arrows, `home`, `end`, `page_up`, `page_down`, `enter` |
| a `select` | characters, `space`, `arrow_up`, `arrow_down`, `home`, `end`, `page_up`, `page_down`, `enter` |
| a `button`, a link, a `summary`, a checkbox or a radio button | `space` and `enter` |

Outside a text field, those keys count only on their own or with `shift`.
`tab` and `shift+tab` move focus. In a document that scrolls, the keys it
scrolls with scroll it ([Keymaps](#keymaps), below). Every other key
reaches the program in the keyboard encoding it enabled, as if no surface
were there.

**Selects** pick with their keys, as a closed select does in a browser on
Linux and Windows. Each pick is heard at once: `input` if asked for, then
`change`.

A host may show no list at all, and then `space` and `enter` do nothing.
A program that wants a list everywhere draws its own: a button, and a
surface at a higher `z` placed by the click's `area`.

**Text fields** edit as a text field in a browser does. The arrows,
`home`, `end`, `backspace` and `delete` move and delete, `shift` selects,
and `mod+c`, `mod+v` and `mod+z` copy, paste and undo. `enter` submits an
`input`'s form, and types a line break in a `textarea`.

With nothing selected, `mod+c` has nothing to copy, and the key reaches
the program: on Linux, `ctrl+c` still interrupts it. Each field keeps its
own undo history, which a value the program sets clears.

**Key releases** are not HOTTY's. A program that needs them, such as a
game, enables the kitty keyboard protocol's event types, as it would
without HOTTY ([§10.3](../../SPEC.md#103-key-releases)).

## Keymaps

A keymap says which keys an element uses, and which it gives to the
program. The program writes it in `data-keys`, as bindings of a key to an
action, separated by spaces:

```html
<main data-keys="ctrl+u=delete-to-line-start mod+k=prefix">
  <input id=cmd name=cmd data-keys="ctrl+c=program">
</main>
```

- **Inherited.** An element's keymap is the `data-keys` of each element
  from the root down to it, its own last. Each overrides the ones before
  it key by key. Set yours once on an element that holds the fields, and
  override where one field differs.
- **A text field starts from a default**: the keys every host binds,
  those of the platform's `mod`, and the host's edit shortcuts
  ([text fields](../../SPEC.md#text-fields)). They are a browser field's
  keys, with Cocoa's `ctrl+a`, `ctrl+e` and the like on macOS.
- **`program`** sends the key to the program, whatever the element would
  do with it. A REPL that always interrupts binds `ctrl+c=program`.
- **`prefix`** sends the key, and every key after it (below).
- **Scroll actions**, such as `scroll-down` and `scroll-page-up`, scroll
  the surface where its document scrolls.
- **Ignored:** a binding whose key does not parse, an action the host
  does not know, and bindings of `tab`, `shift+tab` and `escape`.

Outside a text field, a keymap gives only `program`, `prefix` and scroll
actions. A focused button in a scrolling surface would scroll with the
arrows, and `data-keys="arrow_up=program arrow_down=program"` sends them to
the program instead. With no element focused there is no keymap, so give
an element a `tabindex` and focus it.

**Scrolling keys** let a surface scroll with the keys a program pages its
cells with ([scrolling keys](../../SPEC.md#scrolling-keys)). A pager binds
them on what it scrolls:

```html
<article tabindex=0 data-keys="j=scroll-down k=scroll-up g=scroll-start shift+g=scroll-end space=scroll-page-down shift+space=scroll-page-up b=scroll-page-up">…</article>
```

A text field leaves scroll actions out, so a field inside still types `j`,
and a button keeps `space`. A key never scrolls the terminal itself. These
keys need a document that scrolls
([§5.3](../../SPEC.md#53-geometry)).

An SDK has the keymap as data. `TerminalKeys` has the keys of Bubble
Tea's text input and text area, the same in every SDK
([SDK design §3.10](../../SDK.md#310-keys)). Put it in the `data-keys` of
the element that holds your fields, and edit your fields in cells with the
same keymap.

## Key names

HOTTY names keys as
[*myelin key names* 0.1](https://github.com/neuroplastio/myelin/blob/myelinkey/v0.1.0/myelinkey/SPEC.md)
does ([§10.4](../../SPEC.md#104-key-names)), in Ghostty's vocabulary. A
name is its modifiers, each followed by `+`, then one key: a physical key,
a character, or a modifier tapped alone.

| name | the key |
| --- | --- |
| `ctrl+a` | Control with the key that types `a` |
| `ctrl+key_a` | Control with the key where a US keyboard has A, whatever it types |
| `shift+g` | Shift with `g`: the key that types `G` |
| `?` | the key that types `?`, Shift included |
| `alt+arrow_left` | Alt with the left arrow |
| `page_down`, `enter`, `space` | keys that are only physical |
| `mod+s` | `ctrl+s` on Linux and Windows, `super+s` on macOS |
| `shift` | Shift tapped on its own |

- **Modifiers** are `super`, `ctrl`, `alt` and `shift`, in that order.
  `super` is Command on macOS, and Super or the Windows key elsewhere.
- **A physical key** is a place on the keyboard: its W3C code in snake
  case, such as `page_down`, `key_w` or `numpad_enter`.
- **A character** is what the key types. A letter is written small, with
  `shift` as a modifier. Any other character already has Shift in it.
- **`mod`** is the platform's command modifier. The host reports which it
  is as `mod` in its capabilities, and reads `mod+c` as `super+c` on macOS
  and `ctrl+c` elsewhere. Only the keys you write use `mod`; no key
  pressed is named with it.

The host reads the keys you write leniently: modifiers in any order and
case, `cmd`, `opt` and `control`, `PageDown` and `pgdn`. A letter reads
the same in either case, so `G` is `g`: write `shift+g` for Shift with
it. It refuses `meta`, which some programs mean as `super` and others as
`alt`, and `mod` together with `super` or `ctrl`.

Events name modifiers with the same words, as bits of `mods`: 1 `shift`,
2 `alt`, 4 `ctrl` and 8 `super`.

## Two names for one press

A press can have two names, and the host looks its physical one up first.
A host that sees the key itself, as a terminal emulator or a browser
does, offers it as pressed. It does so first, before the terminal's own
shortcuts, for each key that types no text.

A key with `ctrl` or `super` then has two names: on a US layout, Control
with W is `ctrl+key_w` and `ctrl+w`. The surface uses the press if it
uses either name, and where a keymap binds both, the physical binding
wins. A host may keep a few keys for itself, as a browser keeps `ctrl+t`.

A key the surface does not use goes on as if no surface were there. The
terminal's shortcuts take theirs, and the rest become the bytes of the
keyboard encoding the program set. The host offers those bytes to the
surface again, with one name: the character they carry, or a physical key.

Typing comes only this second way, through the platform's input methods.
A host that has only bytes, such as `hotty run` inside another terminal,
offers every key this way. Bytes say what a key types, not where it is,
so:

- **A binding that must hold everywhere names the character**: `ctrl+w`,
  not `ctrl+key_w`.
- **Some keys arrive as others.** In the legacy encoding, `ctrl+backspace`
  may arrive as `ctrl+h`, and a macOS terminal sends Command with the left
  arrow as `ctrl+a`.
- **A press given to the program stays the program's.** A binding of
  either name to `program` holds when its bytes come. `ctrl+key_a=program`
  in a field sends `ctrl+a` on, though the field selects all with `ctrl+a`
  on Linux.
- **A modifier tapped alone** is named on its release, as `shift_left`
  and `shift`, and goes no further. Binding it to `program` does nothing.

## Key sequences and prefixes

The program reads its key sequences itself, with the keymap it uses in
its cells ([§10.5](../../SPEC.md#105-key-sequences)). A leader key, or
`g g`, works on a surface once the host sends the program every key after
the first. That is what `prefix` does:

```html
<main data-keys="mod+k=prefix">
  <ul id=files tabindex=0 data-keys="g=prefix">…</ul>
</main>
```

Here `mod+k` anywhere in `main`, and `g` on the list, hand the program the
keys that follow, `tab` and `escape` included. The program keeps the
sequence's time. Once the sequence ends, by a key, a timeout or `escape`,
it gives the keys back with `a=focus`:

```text
host    → g                        (terminal input: the list's prefix)
program → ESC ] 7279 ; a=menu:show=1 ; {"seq": ["g"]} ST
host    → g                        (the program's, whatever is focused)
program → ESC ] 7279 ; a=menu:show=0 ST
program → ESC ] 7279 ; a=focus:s=browser ST
```

`a=focus` without `t` leaves focus where it was. A prefix also ends when
the program sends `a=blur`, when the surface loses the keyboard, or when
the user focuses an element with a press. The program hears of each it
did not send, as `blur` or `focus`, so it always knows where its keys
come from.

## Edit commands in the cells

A program that edits in its cells can take the edit shortcuts as commands
rather than keys ([§10.6](../../SPEC.md#106-commands-in-the-cells)). To a
program that reads bytes, `ctrl+c` interrupts and `ctrl+v` quotes the
next key. One that selects, copies and undoes in its cells, as a field
does, takes the commands it handles:

```text
program → ESC ] 7279 ; a=edit:take=copy,paste,undo,redo ST
host    → ESC ] 7279 ; a=ev:e=command ; {"name": "paste", "key": "ctrl+v", "text": "hello"} ST
```

- **A key of a command taken** arrives as `command`, in place of its
  bytes. `key` is the one name its bytes have, and a `paste` carries the
  clipboard's text, in order with the keys typed around it.
- **The program decides.** It copies what it has selected. With nothing
  selected, it takes the command as its key, so `ctrl+c` still
  interrupts.
- **The terminal's selection comes first.** While the user has text
  selected in the cells, the copy key copies it, and nothing is sent.
- **A surface that has the keyboard** is offered the key first.
- **The terminal's menus**, such as an Edit menu, send each command the
  program takes, with no `key`.
- **Per screen.** Each `a=edit` replaces the last, and the main and
  alternate screens keep their own. A full-screen program takes its
  commands after switching to the alternate screen.

A host that takes edit commands reports its shortcuts as `edit` in its
capabilities, and sends `caps` when they change. A command belongs to no
surface, so it has no `s` and no `t`.

## The program's menu

A program sends its menu to tell the host what it can do now, with the
keys that reach each action ([§10.7](../../SPEC.md#107-menus)). The host
can show a level of it while a sequence waits for its next key. A
multiplexer may list it in a palette, or give it to an agent that drives
the program.

```text
program → ESC ] 7279 ; a=menu ; {"label": "files", "items": [
            {"key": "g", "label": "go", "enabled": true, "items": [
              {"key": "g", "label": "top", "name": "top", "enabled": true},
              {"key": "shift+g", "label": "bottom", "name": "bottom", "enabled": true}]},
            {"key": "mod+s", "label": "save", "name": "save", "enabled": false},
            {"label": "reload", "name": "reload", "enabled": true}]} ST
```

- **An item** has a `key`, the key that reaches it after its group's,
  and a `label`. Its `name` is the command a pick sends, and its `items`
  make it a group. Items nest at most eight deep.
- **An item without `enabled` is disabled**, so send `"enabled": true` for
  each one that works now. An empty `items` makes no group.
- **The menu lasts** until the program sends another, or `a=menu` with no
  body. Each screen keeps its own, and a program clears its menu when it
  ends.

While a sequence waits, the program shows the level its keys reach.
`a=menu:show=1` with `{"seq": ["g"]}` shows the `go` group: `g` for top,
`shift+g` for bottom. The host may wait a moment first, so a sequence
typed quickly shows nothing.

The level stays until the program shows another, or sends
`a=menu:show=0`. The host also hides it on `escape`, on a key the level
does not list, and when the screen changes. The keys go where they would
without it.

A pick sends `command` with the item's name and no key:

```text
host → ESC ] 7279 ; a=ev:e=command ; {"name": "reload"} ST
```

A disabled item is never sent. An item no key reaches, as `reload` here,
is reached only by a pick. A terminal may list the items in its own
command palette, and one with no palette adds none.

A host that takes menus has the feature `menu`. Without it, `a=menu` is
`EINVAL`, and the program draws its menu itself, in its cells or on a
surface at a higher `z`. An SDK builds these commands with `Menu`,
`MenuShow` and `MenuHide` ([SDK design](../../SDK.md#34-commands)).
