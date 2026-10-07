# HOTTY — HTML Over The TTY

HOTTY lets a terminal program show **surfaces**: small HTML documents that the
terminal lays out and draws into a rectangle of cells, the way kitty's
graphics protocol places images. The program sends markup and deltas in its
ordinary output. The terminal handles layout, drawing, focus and typing.
Clicks, changes and submits come back as events on the program's input.

- No script and no network: the program is the application, the terminal
  the view.
- It works over a pty and SSH, since everything travels in-band.
- Deltas are addressed by element id, so a change costs what it changes.
- Programs can detect a host and fall back to plain text where there is none.

The website, [hotty.neuroplast.io](https://hotty.neuroplast.io), is itself a
terminal program: the tour, the demo apps and a toolkit of HOTTY tools, in a
browser through xterm-addon-hotty or natively in hottyterm.

**Status: version 0.1, a draft.** Versions 0.x may change incompatibly. Two
implementations that share no code pass the conformance vectors:
[hotty-blitz](https://github.com/neuroplastio/hotty-blitz), a renderer with a
C ABI and a polyfill for terminals that show images, and
[xterm-addon-hotty](https://github.com/neuroplastio/xterm-addon-hotty), for
xterm.js in a browser.

## What is here

| path | what |
| --- | --- |
| [`SPEC.md`](SPEC.md) | the protocol |
| [`SDK.md`](SDK.md) | what a library that speaks HOTTY for programs provides, in any language: its components, options, defaults and names |
| [`conformance/`](conformance/) | the conformance vectors: what a host and an SDK must do, as data |
| [`corpus/`](corpus/) | pages that exercise the HTML and CSS a surface is expected to handle |
| [`examples/`](examples/) | programs that speak HOTTY: a card, a dashboard, a form, a large grid, a game |
| [`clients/python/hotty.py`](clients/python/hotty.py) | a dependency-free reference client with SDK.md's whole wire layer, used by the examples and the hosts' tests; `test_vectors.py` runs the SDK vectors against it |

## Implementations

| repository | what |
| --- | --- |
| `neuroplastio/hotty-demo` | the website, hotty.neuroplast.io: the tour, the demo apps and the toolkit, as one terminal program (native and WebAssembly) |
| `neuroplastio/hottyterm` | a terminal that speaks HOTTY natively: a fork of Ghostty with hotty-blitz built in, installed as `brew install --cask neuroplastio/tap/hottyterm` (macOS on Apple silicon) or the AUR's `hottyterm-bin` (Arch on x86_64) |
| `neuroplastio/hotty-blitz` | a renderer (Rust, on Blitz) with a C ABI for terminals, and `hotty run`, a polyfill that shows surfaces in any terminal with kitty graphics |
| `neuroplastio/xterm-addon-hotty` | an xterm.js addon: the browser renders each surface in a sandboxed iframe |

## Try it

With hottyterm, a terminal that speaks HOTTY natively (Homebrew:
`brew install --cask neuroplastio/tap/hottyterm`; Arch's AUR:
`yay -S hottyterm-bin`):

```
python3 examples/dash.py
```

With hotty-blitz built, in kitty, Ghostty, or any terminal with kitty
graphics:

```
hotty run -- python3 examples/dash.py
```

With xterm-addon-hotty, in a browser tab:

```
python3 serve.py --examples      # in xterm-addon-hotty, then open /?run=dash
```

`examples/bubbros.py` needs the game first: `scripts/bubbros-fetch.sh`. Its
art is not ours to publish; it is replaced before anything built on it is.

## Changing the protocol

- **A change to the wire** goes into `SPEC.md` and `conformance/vectors.json`
  together, and both implementations run the new vectors. A change that breaks
  existing programs or hosts needs a new version (§15).
- **Extensions** live in implementations under a vendor prefix (§15). They
  come here when a second implementation wants them.

## Licence

- `SPEC.md` and the documentation: [CC BY 4.0](LICENSE-CC-BY-4.0).
- The vectors, corpus, examples and client: [Apache-2.0](LICENSE-APACHE).
