---
group: Concepts
order: 60
nav: Styling
description: the terminal's colours, font and cells, handed to every document
---

# Styling

Every surface starts with the host's stylesheet, which hands it the
terminal's look: its colours, its font and the size of its cells
([§8](../../SPEC.md#8-the-host-stylesheet)). A document that draws
with it looks like part of the terminal, and follows the terminal when its
theme changes. Any rule of the document's own wins over it.

## The host stylesheet

The host's rules lose to every rule in the document, as a browser's
default styles do. So they set a starting point, and your CSS decides. On
the root they set:

| property | value |
| --- | --- |
| `color`, `background` | the terminal's foreground and background |
| `font-family`, `font-size` | the terminal's font, at its size |
| `line-height` | one cell's height, so `1rlh` is one row |
| `color-scheme` | the terminal's scheme, `dark` or `light` |
| `accent-color` | the terminal's blue |
| `overflow` | `hidden`: nothing scrolls unless the document asks ([Surfaces](surfaces.md#scrolling-inside-a-document)) |

`body` has no margin. The stylesheet also defines custom properties, for a
document to use in its own rules:

| property | holds |
| --- | --- |
| `--hotty-fg`, `--hotty-bg` | the terminal's foreground and background |
| `--hotty-ansi-0` … `--hotty-ansi-15` | the 16 ANSI colours of the terminal's theme |
| `--hotty-accent` | the terminal's blue: `ansi-12` when the scheme is dark, `ansi-4` when light |
| `--hotty-font` | the terminal's font family, then `monospace` |
| `--hotty-cell-w`, `--hotty-cell-h` | one cell, in CSS pixels |
| `--hotty-px` | one device pixel, in CSS pixels |

The prefixes `--hotty-` and, for attributes, `data-hotty-` belong to the
protocol. Name your own properties otherwise.

## The palette

The 16 ANSI colours are the one palette every terminal theme designs for
contrast ([Appendix B](../../SPEC.md#appendix-b-rationale)). A document
that draws with them reads well in whatever theme the user picks:

```css
.ok    { color: var(--hotty-ansi-2); }   /* green */
.fail  { color: var(--hotty-ansi-1); }   /* red */
.muted { color: var(--hotty-ansi-8); }   /* bright black, for secondary text */
.card  { border: 1px solid var(--hotty-ansi-8);
         background: color-mix(in srgb, var(--hotty-bg) 85%, var(--hotty-accent)); }
```

Form controls take the palette too: fields, buttons, checkboxes, focus
rings, links and selected text. They are drawn in the terminal's colours,
not the engine's, so they look the same on every host. `ansi-8` draws
their borders, buttons, placeholders and whatever is disabled.

A document that styles its own controls wins here, as everywhere else.

## Light and dark

The host's capabilities say whether the terminal's scheme is `dark` or
`light`, in `scheme` ([§4](../../SPEC.md#4-detection-and-capabilities)).
The stylesheet sets `color-scheme` to match, and `prefers-color-scheme`
follows it. So a document can keep colours of its own for each:

```css
:root { --line: #3c9; }
@media (prefers-color-scheme: light) { :root { --line: #075; } }
```

When the terminal's theme changes, the host updates the stylesheet and
draws every surface again. A document that draws with the palette follows
on its own, with nothing sent. The program hears `caps` only if the scheme
itself changed, with the new `scheme`.

## Sizes in cells

`--hotty-cell-w` and `--hotty-cell-h` are one cell in CSS pixels, as
`cellcss` is in the capabilities. With them, a document lines up with the
terminal's grid: a label as wide as 12 cells, or a gap of one row.

```css
.label { width: calc(12 * var(--hotty-cell-w)); }
.rows  { display: grid; gap: 1rlh; }   /* the root's line-height is one row */
```

The surface is `c` by `r` cells, and that is its viewport
([§5.3](../../SPEC.md#53-geometry)). Media queries and viewport units see
that size, so a document can lay itself out for the width it is placed at.

When the terminal's font changes, so does the size of a cell in CSS
pixels. The host lays every document out again with the new
`--hotty-cell-*`, and sends `caps` with the new `cellcss`. A placement
keeps its cells, and one that asked hears `fit` if its content now needs
other rows ([Surfaces](surfaces.md#when-the-content-changes-height)).

## Fonts

The root's font is the terminal's, at its size, and `--hotty-font` names
its family. A document can set any other, such as proportional type for
prose. Code and figures that should line up with the cells around it keep
the terminal's font.

```css
body       { font-family: sans-serif; }
code, .num { font-family: var(--hotty-font); }
```

A font of the document's own comes as a resource, which `@font-face`
names with `cid:`. It can also come from the network, where the host and
the document both allow it ([Images and the network](resources.md)).

```css
@font-face { font-family: Inter; src: url(cid:inter); }
```

## One device pixel

`--hotty-px` is one device pixel in CSS pixels: `1px` divided by the host's
`scale` (§8). With it, a rule or a border is exactly one device pixel thick
at every zoom, and a box can snap to the screen's pixels:

```css
hr { border: 0; border-top: var(--hotty-px) solid var(--hotty-ansi-8); }
```

A zoom changes how many device pixels a CSS pixel is, and nothing else
(§5.3). The cell, the root font and the layout stay as they were, as a
page's do in a frame under a browser's zoom. The host draws the document
again, sharp, with `--hotty-px` at its new value.

| what changes | what the host does | the program hears |
| --- | --- | --- |
| a zoom, or a display of another density | draws every surface again at the new scale, layout kept | nothing |
| the terminal's font | lays every document out again for the new cell | `caps` with `cellcss` |
| the terminal's theme | updates the stylesheet, draws every surface again | `caps` with `scheme`, if the scheme changed |

`scale` in the capabilities is a hint for images: device pixels per CSS
pixel when the host answered. An image with that many pixels for each CSS
pixel it covers is sharp then, though a zoom may change it later without
a word.

## CSS the host reads

Some CSS tells the host how to behave, not only how to draw:

| property | what the host does with it |
| --- | --- |
| `overflow` | in a document that scrolls, `auto` and `scroll` make an element scroll ([Surfaces](surfaces.md#scrolling-inside-a-document)) |
| `overscroll-behavior` | stops a gesture going on outward, to the terminal |
| `scrollbar-width`, `scrollbar-color`, `scrollbar-gutter` | style the host's scrollbars |
| `cursor` | sets the pointer over the element, as in a browser |
| `user-select` | `none` keeps the user from starting a selection there |
| `touch-action` | on an element that opts in to drags, decides whether a finger drags it or scrolls ([Input](input.md#touch-on-a-surface)) |

## What CSS a host handles

The [corpus](../../corpus/README.md) holds the HTML and CSS a surface is
expected to handle. Each of its pages tests a part of it, and reads at
80×24 cells:

- cards and typography: flexbox, headings, lists, quotes and `pre`;
- grids and tables: `grid-template-areas`, `fr`, `minmax()`, `colspan`
  and `border-collapse`;
- form controls: text fields, checkboxes, radio buttons, ranges, selects,
  progress and meters;
- effects: shadows, gradients, transforms, `opacity`, `clip-path` and
  `filter`;
- Unicode: CJK, emoji, right-to-left text and combining marks;
- selectors and values: `:has()`, `:is()`, nesting, `@layer`, `calc()`,
  `clamp()`, `aspect-ratio` and container queries;
- overflow: `text-overflow`, `position: sticky` and absolute positioning;
- SVG and images, with icons drawn in `currentColor`.

Not every host is a browser, so hosts judge their rendering of these pages
against a browser's. Pixels inside a surface may differ between hosts, as
text does between fonts. The cells it covers may not (§5.3).

A surface is not a page, and some CSS stops at its edge
([Security](security.md)):

- nothing draws outside the rectangle, `position: fixed` included;
- `url()`, `@import` and `@font-face` load only what the program sent,
  `data:` URLs, and what the network policy allows
  ([Images and the network](resources.md));
- nothing scrolls unless the document asks
  ([Surfaces](surfaces.md#scrolling-inside-a-document)).
