---
group: Concepts
order: 40
nav: Input
description: what a surface reports to the program, and when
---

# Input

A surface reports what the user does as events, and only the events the
program asked for. Most of what the user does stays in the terminal:
typing in a field, ticking a box, hovering, scrolling. The program hears
the result when it needs it, such as a field's value once it is committed.

```text
host → ESC ] 7279 ; a=ev:s=card:e=click:t=go ; {"area": {"c": 0, "r": 0, "w": 4, "h": 1}} ST
```

An event arrives on the program's input, among the keys the user types
([§9](../../SPEC.md#9-events)). `s` names the surface, `e` the kind of
event, and `t` the element, by its `id`. The detail is msgpack, shown
here decoded.

The id is the program's handle, so give one to each element whose events
you want: a button with no id reports no click. Write ids in ASCII, since
a host reports `café` as `caf_` ([§3.2](../../SPEC.md#32-control)).
[Keyboard and focus](keyboard.md) covers the keys, and `focus` and `blur`.

## What asks for each event

An element asks for its own events, and a placement asks for those of its
whole surface. Nothing is sent that nobody asked for:

| event | asked for by | sent |
| --- | --- | --- |
| `click`, `change`, `input`, `submit` | the element: its kind, or `click` or `input` in its `data-on` | each time |
| `caret` | `caret` in a text field's `data-on` | each move of the selection, at most one a frame |
| `press` | `p=1` on the placement | each press |
| `dragstart`, `drag`, `dragend` | `drag` in the element's `data-on`, and `drop` for a target | for each element, cell or step crossed |
| `hover` | `v=1` on the placement | each change, at most one a frame |
| `view` | `view` in the element's `data-on` | once a scroll rests, else at most one a frame |
| `fit` | `f=1` on the placement | at most one a frame |
| `focus`, `blur` | nothing: the keyboard is always told | each time |
| `command` | `a=edit`, and a named item in the program's menu | each key, each pick |
| `caps` | the query | each change |

Events are asked for because they reach whatever reads the terminal's
input. A document left on the screen after its program exits would
otherwise type events into the shell. A program detaches the surfaces it
leaves ([§5.5](../../SPEC.md#55-ownership-adetach)), and a detached
surface sends nothing.

`data-on` is a list of words, as in `data-on="click drag"`. `p`, `f` and
`v` belong to the surface: `1` turns one on and `0` off, and it holds
until the program sends it again
([§5.2](../../SPEC.md#52-placement-aplace)). `fit` says the rows a
document needs have changed, and `caps` that the host's capabilities have.

The pointer's events need a window the host draws. A hidden surface, or
one scrolled out of view, sends no `press`, drag, `hover`, `fit` or
`view`. Drawn again, it reports what changed since the program last heard.

A click, a press and a drag's events carry `mods`, the modifier keys held,
as bits: 1 `shift`, 2 `alt`, 4 `ctrl` and 8 `super`. It is left out when
none is held. Ignore an event whose kind you don't know: later versions
add kinds.

## Clicks

A `click` is sent when the user activates a `button`, a link, a `summary`,
or an `input` of type `button`, `submit` or `reset`. Any other element
asks for clicks with `data-on="click"`. The element that reports is the
nearest of these, from where the user clicked outward.

```html
<button id=save value=draft>Save</button>
<li id=row-7 data-on=click>…</li>
```

```text
host → ESC ] 7279 ; a=ev:s=editor:e=click:t=save ; {"area": {"c": 2, "r": 5, "w": 6, "h": 1}, "value": "draft"} ST
```

- **`area`** is the cells the element covers, counted from 0 at the
  surface's top left cell. Place what belongs next to the element by it,
  as a browser places a menu by its button. An element partly scrolled
  away reports its whole area, so `c` and `r` may be negative.
- **`value`** comes when the element has a `value` attribute.
- **`count`** marks a repeated click: 2 for the second click of a double
  click, 3 for the third of a triple. Every click of a run is reported, so
  a double click is a `click`, then a `click` with `"count": 2`.

A click from the keyboard, `space` or `enter` on a button, carries its
area too, and is always the first of its run. Only a host with the
feature `count` counts clicks, by the user's own settings
([§4](../../SPEC.md#4-detection-and-capabilities)). Without it, offer
another way to do what a double click would.

## Links

A click on a link is an event like any other click: a surface never
navigates. The link's `href` is its handle, so `t` is absent. The detail
carries `href` as the document has it, and `url`, the address it resolves
to against the document's base URL
([§7.3](../../SPEC.md#73-the-base-url)):

```text
host → ESC ] 7279 ; a=ev:s=post:e=click ; {"area": {"c": 12, "r": 3, "w": 5, "h": 1}, "href": "../about", "url": "https://example.com/about"} ST
```

The program decides what the click means: it may show another page, or
ask its platform to open the address. `url` is absent where it would fall
under `https://hotty.invalid/`. That is the base of a document with no
`<base href>`, so a relative link there has only its `href`.

A link with `target="_blank"` is a **hyperlink**, and belongs to the
terminal. The host treats it exactly as an OSC 8 hyperlink in the cells:
the same gesture opens it, with the same feedback and settings.

Its click is not reported, nor a press the host takes for its gesture. A
`target="_blank"` link with no `url` is not a hyperlink.

## Forms

A form's controls work in the terminal, and the program hears their
values as they settle. Toggling a checkbox, picking an option and typing
need no round trip, and each control reports by its kind:

| event | when | detail |
| --- | --- | --- |
| `change` | a checkbox or radio button toggled, or a select's option picked: at once. A text field's value: when focus leaves it, if the user changed it | `{"checked": bool, "value": str, "rev": int}` for a checkbox or radio button, `{"value": str, "rev": int}` otherwise |
| `input` | every edit of a control with `data-on="input"` | `{"value": str, "rev": int}`, and `"sel": [int, int]` with `data-on="input caret"` |
| `caret` | the user moved the selection of a text field with `data-on="caret"`, and no `input` says so | `{"sel": [int, int], "rev": int}` |
| `submit` | a submit button, or `enter` in a text field | `{"fields": [[str, str]]}`: each named field's name and value, in tree order |

A search box that hears every keystroke, as the user types "ad" and
presses `enter`:

```html
<form id=search>
  <input id=q name=q data-on=input>
</form>
```

```text
host → ESC ] 7279 ; a=ev:s=find:e=input:t=q ; {"value": "a", "rev": 1} ST
host → ESC ] 7279 ; a=ev:s=find:e=input:t=q ; {"value": "ad", "rev": 2} ST
host → ESC ] 7279 ; a=ev:s=find:e=submit:t=search ; {"fields": [["q", "ad"]]} ST
```

- **A submit's fields are pairs**, since two controls may share a name,
  as two checkboxes for one setting do. A form with no named field sends
  `[]`. Nothing is sent anywhere else: `submit` is all that happens.
- **A text field commits** when focus leaves it, including when the
  surface loses the keyboard, and sends `change` if its value changed.
  Without `data-on="input"`, that `change` is all the program hears of it.
- **`rev` counts the user's changes** to the control: each edit, toggle,
  check and pick. Moving the caret doesn't count, nor does a value the
  program sets. The program sends it back to change the control
  (below).
- **The program sets a value** by changing the control's `value`,
  `checked` or `selected` attribute with a delta. Its value wins, except
  while the user is editing that control ([Updates](updates.md)).

## Changing what the user is changing

> [!NOTE]
> New in 0.5.

To change a control the user may be changing, a program sends `a=field`
([§6.4](../../SPEC.md#64-afield)). The command carries the `rev` the
program last heard, and the host applies it only if the control still has
that `rev`. A picker completes what the user typed in place: the field
keeps its id, its history and its keys, and the caret goes after the
text.

```text
host    → ESC ] 7279 ; a=ev:s=find:e=input:t=q ; {"value": "sr", "rev": 2} ST
program → ESC ] 7279 ; a=field:s=find:t=q ; {"rev": 2, "from": 0, "to": 2, "text": "src/"} ST
```

- **The body** holds `rev` and one of:
  - `value`;
  - `text`, which replaces the selection or the range `from`..`to`;
  - `checked`, for a checkbox or a radio button.

  `sel` sets the selection after the change: the anchor, then the caret.
  `sel` alone moves the selection.
- **Positions** count bytes of the value's UTF-8, so `é` is 2. A program
  in JavaScript converts from UTF-16.
- **If the user changed the control first**, the host changes nothing and
  answers `ESTALE`, with the control's `rev` as the detail. The program
  waits for the event it hears next and decides again. It doesn't resend:
  that would overwrite what the user did.
- **Nothing is sent back.** `a=field` sends no `input` or `change`. When
  focus leaves a field that only the program changed, the host sends no
  `change` either.
- **Undo** takes the change back as one edit, as it does the user's.
- **A field's caret starts at the end of its value**, and stays where the
  user left it while another element has focus.

## Presses

A placement with `p=1` hears every press in its window, whatever it lands
on: a control, plain text or empty space. A program uses it to follow the
user between surfaces, as a dashboard selects the card pressed.

```text
program → ESC ] 7279 ; a=place:s=cpu:c=40:r=6:p=1 ST
host    → ESC ] 7279 ; a=ev:s=cpu:e=press:t=cpu-card ; {"area": {"c": 0, "r": 0, "w": 40, "h": 6}} ST
```

- **`t`** is the nearest element with an id, from the one pressed
  outward. Where none has one, there is no `t` and no `area`.
- **A press comes first**, before every other event it causes: the
  `change` and `focus` it brings, and the `click` its release may make.
- **A press** is the primary button, a tap, or a touch that becomes a
  drag. It is not reported where the pointer passes through, for a mouse
  or pen press with Alt held, or where the host takes it for a
  hyperlink's gesture.

## Drags

An element opts in to drags with `data-on="drag"`, and then hears the
pointer from the press to the release
([§9.1](../../SPEC.md#91-drags)). Drags carry what a click cannot: a
range dragged across a grid, a handle let go somewhere, a slider.

- **`dragstart`** comes on the press. `t` is the element that opted in,
  and it needs an id, or there is no drag.
- **`drag`** comes each time the element under the pointer changes. Its
  `t` is the nearest element there with an id and `drag` or `drop`. Where
  there is none, a `drag` comes for each cell instead.
- **`dragend`** comes once, on the release, wherever the pointer is.

Each carries `c` and `r`, the pointer's cell counted from the surface's
top left. They go on counting outside it, negative above and to the left.
A drag costs a few events for each element it crosses, not one a move.

**Steps say where in an element.** With `data-steps="20"`, every event of
its drag carries `x`, from 0 to 20 across its width. `data-steps="0 20"`
divides its height instead, for `y`. A `drag` also comes each time the
step changes, as for this volume slider:

```html
<div id=volume data-on=drag data-steps=20 style="touch-action: pan-y">…</div>
```

```text
host → ESC ] 7279 ; a=ev:s=mixer:e=dragstart:t=volume ; {"c": 4, "r": 1, "x": 5} ST
host → ESC ] 7279 ; a=ev:s=mixer:e=drag:t=volume ; {"c": 5, "r": 1, "x": 6} ST
  …
host → ESC ] 7279 ; a=ev:s=mixer:e=dragend:t=volume ; {"c": 7, "r": 1, "x": 9} ST
```

The step is measured against the dragged element wherever the pointer
is, and clamped. So the slider follows a finger that slips off its track,
as a browser's range input does.

**A drop target** has `drop` in its `data-on` and an id, and a drag can
end on it. One with only `drop` is never dragged itself. With steps, a
target also tells where in it the pointer is, as `tx` and `ty`.

A list row with `data-on="drag drop"` and `data-steps="0 1"` is both. It
splits into halves, for an item dropped on it to land before or after it.
A tree's folder with `data-steps="0 2"` splits into before, into and
after.

- **The pointer is held** until the release, as `setPointerCapture`
  holds it in a page. Every move goes to the drag, over the cells, another
  surface, or outside the terminal's window.
- **A drag selects no text** on an element that opts in.
- **A drag is a click only where it began.** Released on the element it
  started on, it also sends `click` after `dragend`, if that element has
  `click` in its `data-on`.
- **It can end early**, with a `dragend` that has no `t`. That happens
  when the placement goes away, a new document replaces this one, or the
  host loses the pointer. A delta or a new placement does not end it.

## Touch on a surface

A tap on a surface is a click, and a touch drag scrolls, as a wheel does
([§9](../../SPEC.md#9-events)). Over a document that scrolls, it scrolls
the document while that can move. Over any other surface, it does what it
would over the cells beneath: scrollback, or on the alternate screen, the
program's wheel input.

A touch drags an element only where the element opts out of panning, so
a surface never traps the finger:

- **`touch-action`** decides, as the document's CSS sets it. On an
  element that opts in to drags, a touch drags when `touch-action` allows
  no pan along its first move.
- **`pan-y`** on a horizontal slider drags it across, and an up or down
  swipe still scrolls. `none` drags it either way. The default, `auto`,
  always scrolls.
- **The touch presses when it becomes a drag**: `press`, if asked for,
  then `dragstart`, both for where the touch began.
- **A tap presses at its lift.** A long press never becomes a drag.
- **A second finger** ends a drag, and the gesture is the host's until
  every finger lifts.

A touch with Alt held never drags, and a touch's moves hover nothing. A
host may report what a tap touched, or what the finger was on at the lift
that ends a drag.

## Presses with Alt

A press with Alt held is the program's, never a surface's
([§9.2](../../SPEC.md#92-presses-with-alt)). Wherever it lands, the host
takes it as a press on the cells beneath. With mouse reporting on, the
program hears it as any press on the cells, with Alt set: in the SGR
encoding, `CSI < 8 ; <col> ; <row> M`.

So a program can start a gesture of its own over its surfaces. A
multiplexer that draws its panes as surfaces moves them with Alt and a
drag, as a window manager moves windows.

- **The surface hears nothing of it**: no `press`, `dragstart` or
  `click`. It takes no focus, and opens no hyperlink. A surface that had
  the keyboard gives it back, and sends `blur`.
- **The press decides.** The gesture stays the program's until its
  release, whether or not Alt stays held. A drag begun without Alt stays
  the surface's when Alt is pressed during it.
- **On macOS, Alt is Option**, whatever the terminal makes Option type.
- **Mouse and pen only.** A tap is a click whatever keys are held.

## Where the pointer passes through

On a host with the feature `passthrough`, a surface takes the pointer only
where an element is there for it
([§9.3](../../SPEC.md#93-where-the-pointer-passes-through)). The host hit
tests as a browser does, and skips every box whose `pointer-events` is
`none`. So a frame drawn around cells can leave the cells the pointer:

```html
<style>
  html { pointer-events: none }
  #close { pointer-events: auto }
</style>
<div class=frame><button id=close>Close</button></div>
```

Where a window takes no pointer, the pointer reaches what is below it:
another window, or the cells. Over the cells, the program hears presses
and motion through its mouse reporting, as it would with no surface
there. The surface hears nothing, and a press there gives the keyboard
back to the terminal.

A gesture belongs to whoever took its press, until its release. Without
`passthrough`, every window takes the pointer wherever it is. A program
that needs the cells under a surface checks for the feature, and
otherwise keeps its surfaces off those cells.

## Hover

`:hover` and the pointer's shape need no program. A placement with `v=1`
also hears which element the pointer is over
([§9.4](../../SPEC.md#94-hover)). A program uses it to show a hint of its
own, or to know that the pointer has left what it lit.

```text
program → ESC ] 7279 ; a=place:s=chart:c=60:r=12:v=1 ST
host    → ESC ] 7279 ; a=ev:s=chart:e=hover:t=bar-7 ; {"c": 31, "r": 4} ST
host    → ESC ] 7279 ; a=ev:s=chart:e=hover ; {"out": true} ST
```

- **Only changes.** A `hover` comes when the element under the pointer
  changes, `t` its nearest id, with the pointer's cell. A move within an
  element sends nothing, and the host sends at most one a frame.
- **Out** comes when the window loses the pointer: to the cells, another
  window, a part that lets it through, or outside the terminal. A press
  with Alt sends it too.
- **A held button holds hover.** From a press to its release, no surface
  sends `hover`: a drag reports its own targets. At the release, the
  surface reports where the pointer is now.
- **Mouse and pen.** A touch's moves hover nothing. At a tap's release,
  or the lift that ends a touch's drag, a host may report what the finger
  was on.

Hover is a feature, `hover`. Where a host lacks it, a program never hears
that the pointer has left. It clears what it lit on the next key or press
instead.

## What is in view

A document that scrolls tells the program which of its marked elements
are in view ([§9.5](../../SPEC.md#95-view)). Mark an element with
`data-on="view"` and an id. A table of contents marks the section being
read this way, and a long list fetches what comes into view.

```text
host → ESC ] 7279 ; a=ev:s=guide:e=view ; {"in": {"install": {"c": 0, "r": -3, "w": 60, "h": 8}, "usage": {"c": 0, "r": 5, "w": 60, "h": 20}}, "end": false} ST
```

- **`in`** names every element in view, each with its whole area, not
  only what changed. So the program keeps no state to follow changes.
- **`end`** is `true` when the document's root is scrolled as far down as
  it goes.
- **When:** once the document is laid out, then each time what it would
  carry changes. While a scroll moves, the host waits for it to rest.

To take the reader to an element, the program sends the `reveal` op
([Updates](updates.md)).

## Touch in the cells

> [!NOTE]
> New in 0.4.

A program that drags with the mouse in its cells can name where a finger
drags too ([§9.6](../../SPEC.md#96-touch-in-the-cells)). Over the cells a
touch drag scrolls, so a slider drawn in cells moves for a mouse but not
for a finger. `a=touch` names the cells where a finger drags, and which
way:

```text
program → ESC ] 7279 ; a=touch ; {"areas": [{"c": 10, "r": 20, "w": 30, "h": 1, "drag": "x"}]} ST
```

Each area has:

- `c` and `r`, its first column and row, counted from 0 at the screen's
  top left, where a mouse report counts from 1;
- `w` and `h`, the columns and rows it spans;
- `drag`, the way a finger drags in it: `"x"` across, `"y"` up and down,
  or `"xy"` either.

In an area, a touch that moves the area's way becomes the mouse's primary
button. It is pressed where the touch began, moves with the finger, and
is released where it lifts. The program reads it as it reads the mouse,
in its own mode and encoding, so there is no new event to parse.

- **A tap** in an area is a press and a release at the lift, so a slider
  jumps to where it was tapped. A swipe the other way still scrolls.
- **Only while the program reads the mouse's buttons**, and the terminal
  shows the screen rather than its scrollback.
- **Areas last** until the program sends others, or `a=touch` with no
  body. The main and alternate screens keep their own.
- **They are cells of the screen**, not of its text: they stay put when
  the lines scroll. Send them again when what you drew moves, and clear
  them when you exit.
- **Surfaces come first.** A touch that begins where a surface's window
  takes the pointer is the surface's.
- **Only a finger.** The mouse and a pen reach the program as they always
  have.

A host that takes no touch accepts `a=touch` all the same, so a program
sends its areas without checking. A multiplexer that relays the mouse
passes its panes' areas on, moved to where each pane is. An SDK builds the
command with `Touch` ([SDK design](../../SDK.md#34-commands)).
