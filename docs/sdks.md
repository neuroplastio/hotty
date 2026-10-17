---
group: Start
order: 20
nav: Choose an SDK
description: the libraries that speak HOTTY for a program, in Go, TypeScript, Lua and Python
---

# Choose an SDK

An SDK speaks HOTTY for your program. It asks the terminal whether it is a
host, builds the commands that show and change surfaces, and reads the
events that come back. Every SDK follows the same [design](../SDK.md):
the same names, the same defaults, and the same conformance vectors. So
what you learn in one carries over to the others.

| SDK | for | what it has |
| --- | --- | --- |
| [Go](#go) | command-line tools, full-screen programs, their tests | the most: Bubble Tea, charts, forms, fields in cells, a host for tests |
| [TypeScript](#typescript) | Node and Bun programs | the protocol and a terminal to use it in |
| [Lua](#lua) | Neovim plugins, plx scripts | the protocol, and surfaces anchored to a buffer or a tool |
| [Python](#python) | trying HOTTY out, the examples in this repository | the protocol, in one file with no dependencies |

Each speaks HOTTY 0.4 and no other version. A program written with one
draws in cells wherever the terminal is not a host of 0.4.

## Go

[hotty-go](https://github.com/neuroplastio/hotty-go) has the most. Next to
the protocol it has a package for each kind of program:

- `hottyterm`, for a command that prints a card, asks a question or
  streams a chart, and leaves it in the scrollback;
- `hottytea`, for a full-screen [Bubble Tea](https://github.com/charmbracelet/bubbletea)
  program, keeping its surfaces in place as its frame changes;
- `hottyedit`, for a text field drawn in cells that edits as a surface's
  does;
- `hottytest`, a host that runs inside `go test`, so a program's tests
  need no terminal.

```sh
go get github.com/neuroplastio/hotty-go github.com/neuroplastio/hotty-go/hottyterm
```

Start with the [Go quick start](https://github.com/neuroplastio/hotty-go/blob/main/docs/quickstart.md).

## TypeScript

hotty-ts is the SDK for Node and Bun: the protocol, and a terminal that
detects the host, prints documents and reads the host's events. Its
package is `@neuroplastio/hotty`, which isn't published yet.

## Lua

[hotty-lua](https://github.com/neuroplastio/hotty-lua) is written for two
places. `hotty.nvim` anchors surfaces to positions in a Neovim buffer, so
they move with their text. `hotty.plx` places surfaces in a plx script's
tool or rail. Under both, `require("hotty")` is the protocol alone, in Lua
5.1 with nothing else, so it runs under LuaJIT, PUC Lua and gopher-lua.

Start with the [Lua quick start](https://github.com/neuroplastio/hotty-lua/blob/main/docs/quickstart.md).

## Python

[`clients/python/hotty.py`](../clients/python/hotty.py) in this repository
is one file with no dependencies: every command, the decoder, detection,
and a small terminal for the examples. Copy it next to your program to try
HOTTY:

```sh
python3 examples/card.py   # in a host, from a checkout of this repository
```

It passes the SDK sections of the conformance vectors, all but the few
that need grapheme clusters, and is not a package with releases. The
reference implementation is [hotty-go](#go).

## Your own

To speak HOTTY from another language, follow the [SDK design](../SDK.md)
and pass the SDK sections of the [conformance vectors](../conformance/README.md).
The protocol is escape sequences, base64 and msgpack, so any language that
can write to its terminal can speak it.
