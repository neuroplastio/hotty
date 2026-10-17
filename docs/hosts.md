---
group: Start
order: 10
nav: Choose a host
description: the terminals and browsers that draw HOTTY's surfaces
---

# Choose a host

A host is what draws a program's surfaces, usually the terminal itself. A
program asks the terminal whether it is a host when it starts, and draws in
cells where it is not, so you can run a HOTTY program anywhere. It only
shows its surfaces where there is a host.

| host | where it runs | what you get |
| --- | --- | --- |
| [hottyterm](#hottyterm) | macOS on Apple silicon, Linux on x86_64 | everything, drawn by the terminal at its own resolution |
| [a browser](#a-browser) | any page that runs xterm.js | everything, each surface in a sandboxed iframe |
| [`hotty run`](#any-terminal-with-kitty-graphics) | kitty, Ghostty and other terminals with kitty graphics | surfaces as images: sharp at one zoom, no text to select |

A program of HOTTY 0.4 needs a host of 0.4. A host of another version, 0.2
or later, answers its question with the versions it speaks; a host of 0.1
answers with capabilities the program can't read. Either way the program
draws in cells, as it would without a host.

## hottyterm

[hottyterm](https://github.com/neuroplastio/hottyterm) is
[Ghostty](https://ghostty.org) with HOTTY built in. It draws surfaces as
it draws text: sharp at any zoom, following its theme, with text you can
select and copy. Typing in a field, hovering and scrolling happen in the
terminal, with no round trip to the program.

```sh
brew install --cask neuroplastio/tap/hottyterm   # macOS on Apple silicon
yay -S hottyterm-bin                             # Arch Linux on x86_64
```

Other Linux distributions take the release's archive.
[Installing hottyterm](https://github.com/neuroplastio/hottyterm/blob/main/docs/install.md)
has every way, and what hottyterm adds to Ghostty's settings.

## A browser

[xterm-addon-hotty](https://github.com/neuroplastio/xterm-addon-hotty)
makes [xterm.js](https://xtermjs.org) a host. The browser draws each
surface in a sandboxed iframe over the terminal's cells, so a web page that
runs a terminal program, locally or over a WebSocket, shows its surfaces
too.

```sh
npm install @neuroplastio/xterm-addon-hotty @xterm/xterm
```

[hotty.neuroplast.io](https://hotty.neuroplast.io) runs this way. Its
tour, demo apps and tools are one HOTTY program, in the page with nothing
to install.
[Using the addon](https://github.com/neuroplastio/xterm-addon-hotty/blob/main/docs/usage.md)
shows how to load it and what it lets a page decide.

## Any terminal with kitty graphics

`hotty run`, from [hotty-blitz](https://github.com/neuroplastio/hotty-blitz),
is a host for terminals that show images through the kitty graphics
protocol: kitty, Ghostty, WezTerm and others. It sits between the program
and the terminal, passes everything through except HOTTY, and sends each
surface as an image:

```sh
hotty run -- python3 examples/dash.py
hotty run -- ssh server program   # the host runs here, so the server needs none
```

Images lose what a native host keeps: sharpness when you zoom, and the text
of a surface, which can't be selected. Clicks, keys and scrolling still
reach the surfaces. `hotty run` is built from source for now:
[The polyfill](https://github.com/neuroplastio/hotty-blitz/blob/main/docs/polyfill.md)
says how.

## Without a host

Every other terminal, and a pipe, has no host. A program written with an
SDK finds that out when it starts and draws in cells, as any terminal
program does. [Degrading](concepts/degrading.md) says what a program does
in each case.
