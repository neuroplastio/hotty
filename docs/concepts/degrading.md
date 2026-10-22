---
group: Concepts
order: 90
nav: Degrading
description: how a program finds a host, and what it shows where there is none
---

# Degrading

A hotty program runs wherever a terminal program runs, and shows surfaces
only where it finds a host ([§14](../../SPEC.md#14-degradation)).
Everywhere else it draws in cells, or writes plain data. It finds out
when it starts, and runs the same way in each case.

## Three renditions

Every program has three renditions, and an SDK makes the choice between
them plain ([SDK design §2.5](../../SDK.md#25-three-renditions)):

| where it runs | what it shows | how it knows |
| --- | --- | --- |
| a terminal that is a host | surfaces | detection finds a host it can use |
| a terminal that is not a host | cells | detection says no |
| no terminal: a cron job, a CI log | plain data | opening the terminal fails |

A command that prints a status card shows a surface in a host, and lines
of text in another terminal. With no terminal, it writes the card's facts
as plain data. In the cells, a program sends nothing of hotty but its
query.

An SDK opens the process's terminal itself, `/dev/tty` or the platform's
console, whatever its standard output is
([SDK design §4.1](../../SDK.md#41-terminal)). Only where there is none
does the program fall back to plain data.

## Is there a host?

A program asks with a query, followed by a question every terminal
answers ([§4](../../SPEC.md#4-detection-and-capabilities)):

```text
program → ESC ] 7279 ; a=q:n=1:v=0.5 ST  CSI c
```

`CSI c` asks for the terminal's Primary Device Attributes (DA1). A host
answers the query before it answers DA1, so the order of the answers
decides:

```text
host     → ESC ] 7279 ; a=ok:n=1:re=q ; <the capabilities> ST  CSI ? 62 ; 22 c
terminal → CSI ? 62 ; 22 c
```

The first terminal is a host: its reply comes first, with its
capabilities. The second answers DA1 alone, so it is no host, and the
program knows after a short grace, not a long timeout.

A DA1 answer may belong to a question asked earlier, by the program or by
what ran before it. So a program waits a little after a DA1 that comes
with no reply before it. An SDK's detector waits 150 ms for a reply then,
and gives up after 1500 ms with no answer at all
([SDK design §3.8](../../SDK.md#38-detector)).

The detector tells two moments apart. It has **decided** once it knows
whether the terminal is a host, and is **done** once nothing more of the
detection will arrive. A framework's adapter acts when decided; a program
that hands the terminal on waits until done.

## Versions

The query lists the versions the program speaks, and the host answers in
the highest one it shares. A host that shares none answers `EVERSION`,
with the versions it speaks as the detail:

```text
program → ESC ] 7279 ; a=q:n=1:v=0.5 ST  CSI c
host    → ESC ] 7279 ; a=err:n=1:re=q ; {"code": "EVERSION", "detail": "0.4"} ST  CSI ? 62 ; 22 c
```

The program takes that as no host, and draws in cells. It does the same
with capabilities that do not decode, or that name a version it did not
list. Until 1.0 a version may change how messages are read, so a program
and a host of different versions never meet
([§15](../../SPEC.md#15-versioning-and-extensions)).

Today's SDKs each speak 0.5 alone, so a program written with one draws
in cells on a host of 0.4. The detail lets the program tell its user which
versions the terminal speaks.

## Features

A host of 0.5 does everything 0.5 describes, except the features it may
lack ([§4](../../SPEC.md#4-detection-and-capabilities)). The
capabilities' `features` list those it has, and a program offers another
way where one is missing:

| feature | without it, the program |
| --- | --- |
| `passthrough` | keeps its surfaces off the cells whose pointer it needs |
| `hover` | clears what it lit under the pointer on the next key or press, since it never hears the pointer leave |
| `count` | offers another way to do what a double click would |
| `menu` | shows its menu itself, in its cells or on a surface |

Ignore a feature you don't know: later versions add them. Edit commands in
the cells need `edit` in the capabilities
([Keyboard and focus](keyboard.md#edit-commands-in-the-cells)). Touch
areas need nothing: a host that takes no touch accepts `a=touch` and does
nothing with it.

The capabilities may also name the host and its version. A program uses
them only to avoid a known bug of some version, never to learn what a
field would tell it.

## A late answer

A program can start using hotty after it fell back, when it asked for a
late answer ([§4](../../SPEC.md#4-detection-and-capabilities)). A
multiplexer can run a pane with no terminal attached, such as one
restored after a reboot. Detection then finds no host, though one may
attach later.

```text
program  → ESC ] 7279 ; a=q:n=1:v=0.5:late=1 ST  CSI c
terminal → CSI ? 62 ; 22 c                                    (no host yet: the program draws in cells)
host     → ESC ] 7279 ; a=ok:n=1:re=q ; <the capabilities> ST   (later: a host attached)
```

- **What stands between** the program and the terminal may hold the
  query, and answer it once there is a host. It holds one query at a
  time.
- **The program takes the reply**, whenever it comes, as detection
  finding a host, if it is one it can use. It may show surfaces from
  then on.
- **A program about to exit** withdraws its query with `a=q:q=2`, so that
  no reply reaches whatever reads the terminal after it.

An SDK takes `Late` as an option. A framework's session then switches to
surfaces when the answer comes, and asks the program for a new layout
([SDK design §4.3](../../SDK.md#43-session-a-frameworks-adapter)).

## The polyfill

A polyfill is a host for terminals that show images
([§14](../../SPEC.md#14-degradation)). It sits on the pty between the
program and the terminal, passes every byte through but hotty's, and
answers the query for the terminal. It draws each surface itself, and
sends it as a kitty graphics placement.

The program needs no change, even on the far side of SSH, since the
polyfill runs next to the terminal. Pixels lose what a native host keeps:
sharpness when the user zooms, and the surface's text, which cannot be
selected. `hotty run` is one
([Choose a host](../hosts.md#any-terminal-with-kitty-graphics)).

A polyfill reads keys only as bytes, so it knows what a key types but not
where it is. A binding that must hold there names the character, `ctrl+w`,
not the physical key, `ctrl+key_w`
([Keyboard and focus](keyboard.md#two-names-for-one-press)). An SDK may
tell a program that a terminal shows kitty graphics, so that it can
suggest the polyfill to its user.

## What a program does in each case

- **On a host**, it checks the features, shows its surfaces and reads
  events. Before it exits, it detaches the surfaces it leaves on the
  screen, and reads every reply its commands caused
  ([SDK design §2.6](../../SDK.md#26-leave-the-terminal-clean)).
- **In the cells**, it draws the same interface as text, and sends nothing
  of hotty but the query. An SDK's field edits as a surface's does, with
  the same keymap, so the user's hands need not change
  ([SDK design §4.6](../../SDK.md#46-field)).
- **With no terminal**, it writes plain data.

The program runs the same way in all three. Only what it draws changes.
