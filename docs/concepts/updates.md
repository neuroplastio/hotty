---
group: Concepts
order: 30
nav: Updates
description: changing a surface by element id, at the cost of what changed
---

# Updates

A program changes a surface with a **delta**: a list of operations on its
document, each finding its element by `id` ([§6](../../SPEC.md#6-deltas)).
The host applies them to the document it keeps, so a change costs what it
changes, however large the document is.

```text
program → ESC ] 7279 ; a=doc:s=dash ; <style>.bar { width: calc(var(--p) * 1%) }</style> <div id=cpu class=bar style="--p: 0"></div> <span id=clock></span> ST
program → ESC ] 7279 ; a=delta:s=dash:q=2 ; {"ops": [{"op": "var", "t": "cpu", "k": "p", "v": "42"}, {"op": "text", "t": "clock", "v": "12:00:01"}]} ST
```

(Payloads are shown decoded here, and the delta's msgpack as JSON. On the
wire they are base64.)

The bar is 42% wide now, and the clock reads 12:00:01. The document's CSS
does the drawing, and the delta only sets the numbers it reads.

## A delta

A delta is one message: `a=delta`, the surface's name, and its ops in
msgpack ([§6.1](../../SPEC.md#61-adelta)). Each op is a map of up to four
strings:

- `op`, what it does;
- `t`, its target: the id of an element;
- `k`, a name: the attribute for `attr` and `unattr`, the custom property
  for `var`;
- `v`, its value: HTML, text, or a value to set.

The host applies the ops in order, as one unit, and shows none of the
states between them. So the changes of one frame to one surface go in one
delta.

## The ops

| `op` | what it does to the target |
| --- | --- |
| `text` | replaces its children with the text `v` |
| `var` | sets the custom property `--k` on it to `v` (`k` may carry its `--`) |
| `attr` | sets its attribute `k` to `v` |
| `unattr` | removes its attribute `k` |
| `morph` | morphs it into the HTML `v`, keeping what stays ([below](#morph)) |
| `inner` | morphs its children into the nodes of `v` |
| `replace` | replaces it with the nodes of `v`, without morphing |
| `append`, `prepend` | adds the nodes of `v` as its last or first children |
| `before`, `after` | adds the nodes of `v` before or after it |
| `remove` | removes it |
| `reveal` | scrolls it into view: its top with `start`, its bottom with `end`, or as little as it takes |

`text` and `var` are the ops a dashboard sends every frame, and a host
should make them cheap. Most of what changes often fits one of them. A
number is text, and a bar's width or a colour can be a custom property
that the document's CSS reads.

HTML in `v` is parsed where it will go, as a child of the element it
joins. So a `<tr>` added to a table body, or an `<li>` to a list, parses
as it would in place.

`append` and `prepend` don't add an element twice. An element of `v` whose
id is already a child of the target is morphed where it is. So a log can
send its last line again as it changes.

`reveal` changes no node. It scrolls each box that holds the target until
the target is in view, and only in a document that scrolls
([Surfaces](surfaces.md#scrolling-inside-a-document)). It moves neither
focus nor the keyboard.

## Why ids

An id makes a delta's effect predictable: it changes that element, and
nothing else ([Appendix B](../../SPEC.md#appendix-b-rationale)). Your
program wrote the document, so it knows what each id means. Events name
elements by id too, so the id is your handle both ways ([Input](input.md)).

Give ids in ASCII. A delta finds any id as the document has it, but an
event's control replaces each character outside ASCII with `_`
([§3.2](../../SPEC.md#32-control)). An element whose id is `café` is
reported as `caf_`.

**A missing target** changes nothing, and the ops after it still apply.
The host answers `ENOTARGET` with the id, and `i`, the index of the first
op that failed. A delta that is wrong anywhere else, such as an op the
table doesn't have, applies nothing and is `EINVAL`.

Without `q` or `n`, a host answers a delta only with an error
([§3.6](../../SPEC.md#36-replies)). Deltas sent every frame usually carry
`q=2`, which asks for nothing at all, and the SDKs send them that way
([SDK design](../../SDK.md#34-commands)).

## Morph

Morphing turns an element into new HTML while keeping what stays the same
([§6.2](../../SPEC.md#62-morph)). Elements that match are changed in place,
not made again, so they keep:

- focus, and the text the user is typing;
- their scroll positions;
- whether a `<details>` is open.

Two elements match when their tags are the same, and so are their ids
where both have one. Among children, one with an id finds its old self by
id, wherever it was, and the rest match in order, by kind. What matches is
changed in place and moved where the new HTML puts it; what doesn't is
removed or inserted.

**The program's values win, except while the user is editing.** A change
to `value`, `checked` or `selected` also sets the control's current state,
unless the control is focused. A focused control keeps the value the user
is typing. To change a control the user may be changing, the program sends
`a=field`, which changes it only if the user hasn't since
([Input](input.md#changing-what-the-user-is-changing)).

`morph` with no `t` matches each top-level element of `v` to the element
of the document with the same id. A program that redraws its whole tree
every frame, in immediate mode, can send all of it this way:

```text
program → ESC ] 7279 ; a=delta:s=signup:q=2 ; {"ops": [{"op": "morph", "v": "<form id=form><input id=email name=email> <p id=hint>That address is taken</p></form>"}]} ST
```

The hint changes, and the field the user is typing in keeps its text and
its focus. Ids that aren't in the document are reported together, in one
`ENOTARGET`, and the rest still apply.

`replace` is the op that doesn't morph: what it inserts starts fresh. A new
document, sent with `a=doc`, replaces everything, and starts scrolled to
the top left.

## Several commands at once

A delta is one unit already. For a batch of several commands or surfaces,
bracket it in synchronized output, the terminal's way of showing a batch
at once
([§6.3](../../SPEC.md#63-order-and-transactions)):

```text
program → CSI ? 2026 h
program → ESC ] 7279 ; a=delta:s=list:q=2 ; {"ops": [{"op": "attr", "t": "row-4127", "k": "class", "v": "selected"}]} ST
program → ESC ] 7279 ; a=doc:s=detail ; <h2>Build 4127</h2>… ST
program → CSI ? 2026 l
```

Here one surface marks the row picked, and another shows its details. The
host shows no state from inside the batch: it may hold the commands until
the batch ends, or apply them without drawing. Programs already bracket
their cells this way to draw a frame without flicker.

- The host applies commands in the order they arrive, and should draw at
  most once a display frame.
- Terminals time a batch out. A host that gives up waiting for its end may
  apply what it holds.

## What an update costs

A delta costs the bytes of what it changes: its ops in msgpack, then
base64, in one envelope. The deltas of
[Appendix A](../../SPEC.md#appendix-a-examples) show the scale, counted on
the wire, envelope included:

| update | bytes |
| --- | --- |
| one `text`: a button reads "Start" | 68 |
| a `var` and a `text`: a bar and a clock | 104 |

Neither number depends on the size of the document. Until 0.3, each op was
a message of its own, with its own envelope: a frame of fifteen small
changes took 755 bytes. As the ops of one delta, they take 184
([Appendix B](../../SPEC.md#appendix-b-rationale)).

Sending only what changed is the program's side: a program that redraws
its tree diffs it against the last one it sent. A cell's new text is then
a `text` op of 56
bytes, where morphing a small table's whole tree sends 930
([SDK design](../../SDK.md#29-updates-cost-what-they-change)). The `morph`
without a target stays the fallback.

A document is the large message, so it goes once, and deltas follow. A
program may compress it with zlib, marked `o=z`, which more than pays for
base64's third on markup ([§3.3](../../SPEC.md#33-payload)). A stylesheet
that several documents share goes once too, as a resource
([Images and the network](resources.md)).
