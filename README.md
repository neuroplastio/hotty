# HOTTY — HTML Over The TTY

HOTTY lets a terminal program show **surfaces**: small HTML documents that the
terminal lays out and draws into a rectangle of cells, the way kitty's
graphics protocol places images. The program sends markup and patches in its
ordinary output. The terminal handles layout, drawing, focus and typing.
Clicks, changes and submits come back as events on the program's input.

- No script and no network: the program is the application, the terminal
  the view.
- It works over a pty and SSH, since everything travels in-band.
- Patches are addressed by element id, so a change costs what it changes.
- Programs can detect a host and fall back to plain text where there is none.

**Status: version 0.1, a draft.** The spec is implemented twice, by programs
that share no code, and both pass the conformance vectors. It will change
before version 1; its open issues are in Appendix D.

## What is here

| path | what |
| --- | --- |
| [`SPEC.md`](SPEC.md) | the protocol |
| [`conformance/`](conformance/) | the conformance vectors: what a host must do, as data |
| [`corpus/`](corpus/) | pages that exercise the HTML and CSS a surface is expected to handle |
| [`examples/`](examples/) | programs that speak HOTTY: a card, a dashboard, a form, a large grid, a game |
| [`clients/python/hotty.py`](clients/python/hotty.py) | a dependency-free reference client, used by the examples and the hosts' tests |

## Implementations

| repository | what |
| --- | --- |
| `neuroplastio/hotty-blitz` | a renderer (Rust, on Blitz) with a C ABI for terminals, and `hotty run`, a polyfill that shows surfaces in any terminal with kitty graphics |
| `neuroplastio/xterm-addon-hotty` | an xterm.js addon: the browser renders each surface in a sandboxed iframe |

## Try it

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
