# HOTTY SDKs

    Version:  0.1, with SPEC.md 0.1
    Status:   Draft. It changes with SPEC.md (§15 there).
    Licence:  CC BY 4.0

## Abstract

An **SDK** is a library through which a program speaks HOTTY in one
language. This document says what every SDK provides, whatever its
language: its components, what each one does, the options each takes and
their defaults, and the names they go by. A program written against one SDK
reads the same against another, once the language's idioms are applied.

An SDK has two layers. The **wire layer** encodes and decodes, and does no
I/O; the conformance vectors check it. The **SDK layer** does the I/O for a
kind of program: one that prints and exits, one built on a UI framework, a
test. It is described here so that SDKs agree where a program would notice,
and follow their language everywhere else.

The reference implementation is
[hotty-go](https://github.com/neuroplastio/hotty-go). Its names are the
canonical ones, and where it falls short of this document, §5.3 says so.

## Contents

1. Introduction
2. Principles
3. The wire layer
4. The SDK layer
5. Conformance

Appendices: A. Names · B. Rationale

---

## 1. Introduction

[SPEC.md](SPEC.md) defines the wire: what a program and a host send each
other. This document defines how a library presents the wire to a program.
Where the two disagree, SPEC.md is right and this document is wrong.

The key words **MUST**, **MUST NOT**, **SHOULD**, **SHOULD NOT** and **MAY**
are to be interpreted as in SPEC.md §2.

- **Program**, **host**, **surface**, **placement**, **reply**, **event**:
  as in SPEC.md.
- **SDK**: a library that speaks HOTTY for programs in one language.
- **Wire layer**: the part of an SDK that builds commands and reads what the
  host sends. It does no I/O (§2.1).
- **SDK layer**: the part that reads and writes a terminal, or works through
  whatever stands for one (§4).
- **Canonical name**: the name this document gives a component, an
  operation, an option or a field. It is hotty-go's, and an SDK spells it in
  its language's case (Appendix A).
- **Environment**: what the program runs in: a process with a terminal, a
  UI framework that owns the screen, an editor, a page.

## 2. Principles

### 2.1 Two layers

- **The wire layer is pure.** It **MUST NOT** do I/O, start threads, or read
  a clock: where it needs the time (the Detector, §3.8), the caller passes
  it in. Given the same input, it returns the same output.
- **It depends on the language's standard library only**, and on base64 and
  zlib where that library lacks them. zlib is needed only to compress what a
  program sends, which is optional (§3.3); a host never compresses what it
  sends (SPEC.md §3.3).
- **The SDK layer is built on the wire layer's public interface**, so a
  program that needs something the SDK layer does not do can do it from the
  same parts.

### 2.2 Canonical concepts, idiomatic surface

- Every component, operation, option and field in §3 has a canonical name.
  An SDK **MUST** provide each under a name a reader maps to it at a glance:
  the canonical name in the language's case (`SetText`, `set_text`,
  `setText`). Where the name is a keyword of the language, the SDK picks the
  nearest word (`del` is `delete` in Python) and says so in its
  documentation.
- **Options take the language's form**: functional options in Go, keyword
  arguments in Python, a table in Lua, a struct or a builder in Rust, an
  object in TypeScript. What an option is called, and its default, are
  canonical.
- **Errors take the language's form**: an error value, an exception, a
  result type. What they carry (a code and a detail, §3.9) is canonical.
- **Absence takes the language's form**: Go's zero value and `ok`, Python's
  `None`, Lua's `nil`, Rust's `Option`. The vectors write it `null`.

### 2.3 Shared defaults

The defaults in this document (quiet levels, timeouts, limits) are the same
in every SDK, so a program behaves the same in every language. An SDK
**MUST NOT** choose other defaults; it **MAY** let the program change them.

### 2.4 Protocol only

An SDK's contract is SPEC.md. Everything a program does with the protocol
that the protocol does not define, such as rendering Markdown, highlighting
code, drawing charts, or building forms from a schema, is presentation, and
outside this document. An SDK **MAY** ship such helpers beside it. They
depend on the SDK; the SDK never depends on them, and nothing in §3 or §4
needs them.

### 2.5 Three renditions

Every program has three renditions (SPEC.md §14): surfaces on a host, cells
on a terminal that is not one, and plain data when there is no terminal. An
SDK makes the three branch points plain:
- **No terminal:** opening the terminal fails (§4.1). The program writes
  plain data.
- **Not a host:** detection says no (§3.8). The program draws in cells, and
  sends nothing of HOTTY but the query.
- **A host:** surfaces.

### 2.6 Leave the terminal clean

Replies and events arrive on the program's input, and whatever reads the
input after the program exits, a shell for instance, reads them as typing.
An SDK makes it easy, and its documentation says how, for a program to:
- read every reply its commands caused before it exits (a fence, §4.1);
- leave no surface that still reports events: create the ones it leaves on
  the screen detached, or detach them (SPEC.md §5.5).

### 2.7 Forward compatibility

As SPEC.md §15 has programs do:
- control keys the SDK does not know are kept in the message, and change
  nothing;
- an event of a kind it does not know is an event all the same: its kind is
  reported as it came;
- capability fields it does not know are ignored, and so is a known field
  of an unexpected type. Reading the capabilities **MUST NOT** fail because
  of one field.

### 2.8 Environments

Some environments already do part of what the SDK layer does. A UI
framework's input parser may hand over complete OSC sequences; an editor may
own the terminal's output and hand its input over as events (§4.2). There,
the SDK layer uses what the environment provides: it feeds complete
sequences to the Decoder (§3.6) and writes through the environment's
output. The wire layer is the same everywhere.

## 3. The wire layer

An SDK **MUST** provide every component of this section.

| component | does | Go | vectors |
| --- | --- | --- | --- |
| constants (§3.1) | the protocol's numbers and named values | `Number`, `Chunk`, … | — |
| Control (§3.2) | an ordered list of keys and values | `Control` | — |
| Encode (§3.3) | one command as OSC sequences | `Encode` | `encode` |
| commands (§3.4) | a builder for each action | `Doc`, `Place`, … | `build` |
| names (§3.5) | surface names | `ValidName`, `SurfaceName` | — |
| Decoder (§3.6) | OSC sequences into messages | `Decoder` | `wire`, `decode` |
| Scanner (§3.7) | HOTTY sequences out of a byte stream | — | `scan` |
| Detector (§3.8) | whether the terminal is a host | `internal/detect` | `detect` |
| messages (§3.9) | replies, events, capabilities, errors | `Reply`, `Event`, `Caps`, `Error` | `decode` |

### 3.1 Constants and named sets

| name | value |
| --- | --- |
| `Number` | `"7279"`, the OSC number |
| `Chunk` | 4096, the most base64 bytes in one sequence |
| `MaxSize` | 1000, the most columns or rows of a surface |
| `MaxName` | 64, the longest surface name |
| `Version` | `"0.1"`, the protocol version the SDK implements |

And these sets, each value under its canonical name:
- **event kinds**: `click`, `change`, `input`, `submit`, `press`, `focus`,
  `blur`, `resize`, `fit`, `hover`, `dragstart`, `drag`, `dragend`
  (SPEC.md §9);
- **error codes**: `EINVAL`, `ENOENT`, `ENOTARGET`, `EDETACHED`, `EQUOTA`,
  `EBUDGET` (SPEC.md §3.6);
- **delta ops**: `morph`, `inner`, `replace`, `append`, `prepend`, `before`,
  `after`, `remove`, `attr`, `unattr`, `text`, `var` (SPEC.md §6.1);
- **quiet levels**: `ReplyAlways` 0, `ReplyOnError` 1, `NoReply` 2
  (SPEC.md §3.5).

### 3.2 Control

A command's control is an **ordered** list of keys and values: keys go out
in the order they were added. It reads a key's value and whether it is
present (`get`), and sets one, in place if present, at the end if not
(`with`).

### 3.3 Encoding

`Encode(control, payload)` returns one command as one or more OSC
sequences. Its output is fixed except where the protocol leaves a choice to
the program (compression), so the `encode` vectors compare bytes.

- **Values are cleaned.** Each character a value may not hold becomes one
  `_`: `:`, `;`, `=`, a control character, and any character outside ASCII,
  one `_` for each Unicode code point, and one for each byte that is not
  UTF-8 (SPEC.md §3.2). Keys are the SDK's own and are not cleaned.
- **Keys go out in order**, as `key=value` joined by `:`.
- **The payload is base64**, the standard alphabet, padded. An empty payload
  is sent as nothing, with no `;` before it.
- **Compression is the program's choice.** An SDK **MAY** compress a payload
  with zlib and mark it `o=z`, and then only a payload of 256 bytes or more,
  and only when compressing makes it smaller. `o=z` follows the other keys.
- **Chunks.** A payload whose base64 is longer than 4096 bytes is split
  into chunks of exactly 4096, the last one excepted. Nothing of 4096 or
  less is chunked.
  - The first chunk carries the whole control, then `m=1`.
  - Every further chunk carries `m` (`1`, or `0` on the last) and, if the
    control has one, `q` with the same value: `m=0:q=2`.
- **Every sequence ends with ST** (`ESC \`).

### 3.4 Commands

A builder for each action returns the command's sequences, ready to write.
Each takes the reply options of §3.4.2 and has the default quiet level shown,
which SPEC.md leaves to the program; these are the levels every SDK uses.

| builder | sends | parameters | default `q` |
| --- | --- | --- | --- |
| `Query` | `a=q:n=<n>`, then DA1 (`ESC [ c`) | n | none |
| `Doc` | `a=doc:s` and the HTML; `d=1` with the `Detached` option, `scroll` with `Scroll` | surface, html | 1 |
| `Place` | `a=place` (§3.4.1) | surface, placement | 1 |
| `PlaceAt` | `ESC 7`, `ESC [ <y+1> ; <x+1> H`, `Place` with `C=1`, `ESC 8` | surface, x, y, placement | 1 |
| `Hide` | `a=hide:s` | surface | 2 |
| `Delta` | `a=delta:s:op[:t][:k]` and the payload; `t` and `k` only when given | surface, op, target, key, payload | 2 |
| `SetText` | `Delta` with `op=text` | surface, target, text | 2 |
| `SetVar` | `Delta` with `op=var`, `k` the name | surface, target, name, value | 2 |
| `SetAttr` | `Delta` with `op=attr`, `k` the name | surface, target, name, value | 2 |
| `RemoveAttr` | `Delta` with `op=unattr`, `k` the name, no payload | surface, target, name | 2 |
| `MorphTo` | `Delta` with `op=morph` | surface, target, html | 2 |
| `Res` | `a=res:id:type` and the data | id, mime, data | 2 |
| `DelRes` | `a=del:id` | id | 2 |
| `Del` | `a=del:s` | surface | 2 |
| `DelAll` | `a=del` | — | 2 |
| `Detach` | `a=detach:s` | surface | 2 |
| `Focus` | `a=focus:s[:t]`; `t` only when given | surface, target | 2 |
| `Blur` | `a=blur:s` | surface | 2 |
| `Sync` | `CSI ? 2026 h`, the commands, `CSI ? 2026 l` (SPEC.md §6.3) | commands | — |

- **`Doc` and `Place` answer errors**, since a refused document or placement
  (`EQUOTA`, `ENOENT`) is something a program must hear. Everything else
  answers nothing unless asked: a program that sends deltas every frame would
  otherwise fill its input with replies.
- **`PlaceAt`** places a surface at screen cell (x, y), counted from 0, and
  leaves the cursor where it was: for a full-screen program, which places
  surfaces where it draws them. The coordinates have no leading zeros.
- **`Sync`** takes commands already built, and brackets them.

#### 3.4.1 Placement

A `Placement` says where and how a surface is shown (SPEC.md §5.2):

| field | key | default | sent |
| --- | --- | --- | --- |
| `Cols` | `c` | — | always |
| `Rows` | `r` | 0, which is `auto` | always: the number, or `auto` |
| `Window` | `x`, `y`, `w`, `h` | none | all four, or none: none when absent, when all are 0, or when it shows the whole surface (rows given, and the window is 0, 0, cols, rows) |
| `Z` | `z` | 0 | when not 0 |
| `Press` | `p=1` | false | when true |
| `Fit` | `f=1` | false | when true |
| `Hover` | `v=1` | false | when true |
| `KeepCursor` | `C=1` | false | when true |

#### 3.4.2 Reply options

Every builder but `Query` and `Sync` takes two options:
- **`N(n)`** numbers the command and asks for its reply: `n=<n>`, and
  `q=0` unless the program gives `Q`.
- **`Q(q)`** sets the quiet level. A `Q` given wins over the level `N`
  implies, whatever the order in which the program gives them.

Each key goes out once. `Doc` also takes **`Detached`** (`d=1`) and
**`Scroll(axes)`** (`scroll=<axes>`, SPEC.md §5.1): a bitmask of
`ScrollVertical` (1) and `ScrollHorizontal` (2). `0`, the default, sends
no key; any other value goes out as given, for the host to judge.

### 3.5 Names

- **`ValidName(s)`**: whether `s` is a surface name: 1 to 64 of `A`–`Z`,
  `a`–`z`, `0`–`9`, `_` and `-`.
- **`SurfaceName(s)`**: `s` made one: each other character becomes `_`, it
  is cut to 64, and an empty name becomes `_`.

### 3.6 Decoder

A Decoder turns OSC sequences into messages, one at a time, joining chunked
ones. A new Decoder is ready to use.

- **`Feed(seq)`** takes one OSC sequence, `ESC ] …`, **with or without its
  terminator** (an environment may strip it, §4.2), and returns a result and,
  when the result is `complete`, the message:

  | result | when |
  | --- | --- |
  | `not_hotty` | the sequence is another OSC, or another number (`ESC ] 72790`). The caller handles it; a chunked message in progress is not affected |
  | `partial` | a chunk of a message that is not complete yet |
  | `complete` | a whole message |
  | `invalid` | a malformed message (SPEC.md §3.7), dropped |

- **The control is strict.** It is SPEC.md §3.2's grammar: a key that does
  not parse, a value outside printable ASCII, a key that appears twice, or
  an empty control is malformed.
- **Chunks** (SPEC.md §3.4):
  - A control with only `m` and `q` continues the message in progress; with
    none in progress, it is malformed.
  - Any other message arriving before the last chunk aborts the one in
    progress, which counts as malformed, and is then decoded as usual. If it
    is malformed itself, that makes two (SPEC.md §3.7).
  - The pieces of base64 are joined before they are decoded, so a chunk may
    end anywhere in a base64 quantum.
- **The payload** is base64, with or without padding, whitespace ignored.
  Any other byte makes the message malformed. A payload marked `o=z` is
  inflated if the SDK has zlib; one that does not reports it `invalid`.
  Hosts never compress (SPEC.md §3.3), so only a relay meets one.
- **The message** has the control without `m` and `o`, and the payload as
  bytes.
- **`Invalid`** counts the malformed messages dropped so far.

### 3.7 Scanner

A Scanner cuts HOTTY sequences out of a byte stream, however the reads split
it. An SDK that reads a raw terminal uses one; so does a relay, on a
program's output. An environment that hands over complete sequences needs
none (§2.8), but the wire layer has one all the same.

- **`Feed(bytes)`** returns segments, in order:
  - `pass`: bytes that are not HOTTY's, unchanged: keys, mouse reports,
    other OSCs, other answers;
  - `osc`: one complete HOTTY sequence, from `ESC ] 7279 ;` to its
    terminator (ST or BEL), ready for the Decoder;
  - `da1`: optionally, an answer to Primary Device Attributes,
    `CSI ? <digits and ;> c`, for an SDK that reads DA1 itself (§4.1). A
    Scanner that does not look for them passes them.
- **It holds only what may still become a segment of its own**: bytes that
  are the start of `ESC ] 7279 ;` (or of a DA1 answer, when it looks for
  them), and a HOTTY sequence in progress. Everything else goes out in the
  same `Feed` that brought it. So the segments do not depend on how the
  stream was split, and a key is never kept waiting for the next read.
- **An ESC inside a HOTTY sequence** that does not begin its ST ends the
  sequence unfinished: the sequence is dropped as malformed, and the ESC
  begins what comes next.
- **A HOTTY sequence longer than 64 KiB** (65536 bytes, its terminator not
  counted) is dropped as malformed, up to its terminator. No host sends one:
  chunks are at most 4096 bytes of base64.
- **`Flush()`** ends the stream: what is held goes out as `pass`, except a
  HOTTY sequence in progress, which is dropped as malformed. A program
  reading keys flushes a lone ESC held at the end of a read, as the Escape
  key; that is the SDK layer's choice (§4.1).
- **`Invalid`** counts the sequences it dropped.

### 3.8 Detector

A Detector decides whether the terminal is a host (SPEC.md §4). It is a
state machine with the time passed in, in milliseconds, so it behaves the
same in every SDK and environment, and the `detect` vectors check it step
by step.

- **`Start(now)`** returns the query to send: `Query(n)`, `n` 1 unless the
  program chooses another.
- **`DA1(now)`**: a DA1 answer arrived. It returns whether the answer was
  detection's. **`Reply(r, now)`**: a reply arrived; it returns whether it
  answers the query. **`Tick(now)`**: the time is now. **`End(now)`**: the
  input ended, or the caller gave up.
- **It exposes** `State` (`detecting`, `native` or `text`), `Caps` (the
  host's, when native), `Decided`, `Done`, and `Deadline`: when to call
  `Tick` next, or none once done.
- **Every input first lets the time pass**: whatever was due at or before
  `now` happens before the input is taken.

The rules, with their times:

| rule | |
| --- | --- |
| a reply that answers the query (`a=ok`, `re=q`, the query's `n`) | the terminal is a host: `native`, decided, with its capabilities. Done when the DA1 behind it arrives, or 300 ms after the reply, or at 1500 ms, whichever comes first |
| a DA1 before any reply | it may answer a question asked before the query (SPEC.md §4). It opens a grace of 150 ms: a reply within it still makes the terminal a host |
| the grace ends with no reply | `text`: not a host. Decided and done |
| 1500 ms with no answer at all | `text`. Decided and done |
| the input ends | `text` if nothing was decided. Done |

- **Which inputs are detection's.** Every DA1 from the start until done is
  detection's, and the SDK layer swallows it: it answers the query's fence or
  an earlier question, and is no key. After done, a DA1 is not
  detection's. A reply that answers the query is detection's whenever it
  arrives, even after the state is `text`; a late one changes nothing.
  Replies with another `n`, error replies, and everything else are not.
- **Decided and done** differ only for a host: it is known to be one when
  its reply arrives, and the detection is over when nothing more of it will
  arrive. A program that must not wait, such as a framework's adapter
  (§4.3), acts when decided; one that hands the terminal on, when done.

### 3.9 Messages

A decoded **`Message`** has its control (a map of keys to values) and its
payload (bytes). It reads as a reply or as an event.

**`Reply`** (SPEC.md §3.6), when the action is `ok` or `err`:

| field | from |
| --- | --- |
| `OK` | `a=ok` |
| `Re` | `re`: the action answered |
| `N` | `n`, as a number; absent when the command had none |
| `Surface` | `s`; absent when the command named none |
| `Cols`, `Rows` | `c` and `r`, as numbers, in a reply to `place` |
| `Code`, `Detail` | the error's JSON body, when not OK |
| `Caps()` | the capabilities, in an ok reply to `q` |
| `Err()` | the reply as an error, carrying `Code` and `Detail`; none when OK |

**`Event`** (SPEC.md §9), when the action is `ev`: `Surface`, `Kind` (as it
came, known or not) and `Target` (`t`, empty when empty), and accessors that
read the detail, each absent when the event does not carry it:

| accessor | returns | for |
| --- | --- | --- |
| `Value()` | the detail's `value`, a string | `click`, `change`, `input` |
| `Checked()` | the detail's `checked`, a boolean | `change` |
| `Fields()` | the detail's values, by name: a string as it is, any other value as its JSON, a null left out | `submit` |
| `Link()` | `href`, and `url` if present | `click` on a link |
| `Size()` | `w` and `h`, in CSS pixels | `resize` |
| `FitRows()` | `r` | `fit` |
| `Drag()` | `c`, `r` and `keys` | `dragstart`, `drag`, `dragend` |
| `Hover()` | `c` and `r`, or out | `hover` |
| `Area()` | `area`: `c`, `r`, `w` and `h`, the element's cells; absent unless all four are whole numbers | `click`, `press` |

**`Caps`** (SPEC.md §4) has every field SPEC.md lists: `V`, `Ops`,
`Events`, `Cell` (`w`, `h`), `Scale`, `Scheme`, `Limits`, `Net`,
`Passthrough`, `Scroll`, `Host`, `Version`. Each field is read on its own (§2.7). It
also answers:
- `Supports(op)`: whether `op` is in `ops`; a host that lists no ops is
  taken to support them all;
- `Sends(kind)`: whether the host sends `kind`; `drag` stands for the three
  drag kinds (SPEC.md §4); a host that lists no events is taken to send
  them all;
- `Drags()` and `Hovers()`: whether `drag` and `hover` are in `events`. A
  host that lists no events is taken to send neither, since both came after
  the first hosts: a program offers another way to do what they do;
- `Light()`: the scheme is `light`;
- `CellCSS()`: a cell's size in CSS pixels, `Cell` divided by `Scale` (1
  when absent), and a usual 9 × 18 when the host gave no cell.

**An error** carries `Code` and `Detail`, and its message names both.

## 4. The SDK layer

What a program does with a terminal depends on the kind of program, and on
what it runs in. This section describes the components an SDK **SHOULD**
provide for the kinds of program its language is used for, by what they do,
then by the shape hotty-go gives them. An SDK follows its language and its
frameworks in everything else.

### 4.1 Terminal

For a program that is not a full-screen framework's: a command that prints
documents and exits, one that asks a question, a chart that streams. Go:
`hottyterm.Term`.

- **Opening.** `Open(name)` uses the process's terminal, whatever its
  standard output is (a pipe, say): `/dev/tty`, or the platform's console.
  With no terminal, it fails, and the program writes plain data.
  `New(in, out, name, size, known)` makes one from streams, for a test or an
  environment with no file (a terminal in a page). `known` tells it the
  terminal is a host, and with what capabilities, without asking.
- **One reader.** Everything the terminal sends is read once, by the
  terminal: keys, the mouse, pastes, replies and events. What a call waits
  for goes to that call (detection's answers, a fence's DA1, a numbered
  reply); everything else goes to one event stream, in the order it
  arrived. Calls that wait and a reader of events may run at once.
- **Detection.** `Detect()` runs the Detector (§3.8), once: later calls
  return the first answer. It returns when the Detector is done, so that
  nothing of the detection is left for whatever reads the terminal next. A
  terminal made with `known` answers at once.
- **Requests.** `Request(build)` sends one command numbered with `N` and
  waits for its reply, 3 s at most. The number is never 1, which is the
  query's. An error reply is a reply, not an error; no reply in time is an
  error.
- **The fence.** `Fence()` waits until the terminal has taken everything
  written before it (it sends DA1, which terminals answer in order), 1 s at
  most, and returns the replies nothing read: the errors of commands sent
  with `q=1`, mostly. A program calls it before it exits.
- **The line.** `LineStart()` moves the cursor to the start of a line, where
  a surface placed at the cursor belongs: it asks where the cursor is (CPR),
  and writes CR LF if it is not at column 0. A terminal that does not
  answer within 1 s is taken to be at one.
- **Printing.** `Print(name, html, placement)` sends a document detached and
  places it at the cursor, in one write, and returns the surface's full
  name: for a document that stays in the scrollback among the program's
  output.
- **Writing.** `Send(commands…)` writes commands in one write, so that
  nothing the program prints lands between them.
- **Names.** `Surface(name)` makes a surface name of the program's own: a
  prefix, a dash and the name, made valid. The prefix is the program's name
  and a number unique on the terminal (its process id), or what the
  environment provides, so that two runs never share a surface. Every name
  is remembered (`Surfaces()`), and `DetachAll()` detaches them all.
- **Closing.** `Close()` gives the terminal back as it was (its mode, its
  file). It sends nothing: what is left on the screen, and the replies not
  read, are the program's to settle first (§2.6).
- **Raw mode.** Calls that wait for the terminal put it in raw mode for
  themselves. A program that reads keys asks for it once.
- **The polyfill.** `KittyGraphics()` **MAY** be provided: whether a
  terminal that is not a host shows kitty graphics, so that a program can
  suggest a polyfill (SPEC.md §14).

### 4.2 Push environments

In some environments the SDK does not read the terminal: the environment
hands it what arrives, and writes for it. Neovim is one: its TUI parses the
input and raises `TermResponse` with each OSC, DCS and APC sequence, without
its terminator; a plugin writes to the terminal with `nvim_ui_send`. There:

- **Input is pushed.** The SDK layer receives sequences in callbacks, and
  feeds the Decoder and the Detector from them. It needs no Scanner.
- **Waiting is asynchronous.** Detection, requests and fences complete
  through callbacks or coroutines, with timers the environment provides.
- **What is detection's is advisory**: the environment may hand the same
  answer to other listeners. Others ask DA1 too, so a stale DA1 is routine,
  and the Detector's grace (§3.8) matters.
- **The terminal can change.** An editor can attach another UI, or come
  back from suspension; the SDK layer detects again, and sends documents
  again, when the environment says so.
- **What the environment lacks, the SDK lacks**: CPR, `LineStart`, `Print`
  and raw mode may not exist. Surface names take a prefix the program
  supplies.
- **Batches do not nest.** Where the environment brackets its own frames in
  synchronized output, the SDK sends its commands within them, and does not
  add brackets of its own.

### 4.3 Session: a framework's adapter

For a full-screen program built on a UI framework, which redraws its frame
as its state changes. Go: `hottytea.Session`, for Bubble Tea. Other
frameworks get their own adapter, with the same responsibilities.

- **Modes.** `Detecting` until the Detector decides, then `Native` (a host)
  or `Text` (not one). In `Text` the Session sends nothing, and the program
  draws everything in cells.
- **Layout.** With each frame, the program says which surfaces it wants
  where: name, rectangle on the screen, an optional clip (the part of the
  screen the surface shows in, such as a scrolling region), `Keep`, `Z`,
  `Press`, `Fit`, `Hover`, and a function that returns the document. The
  Session sends only what changed:
  - a document once, attached, with `q=1`, and again only when the host has
    lost it;
  - a placement (`PlaceAt`) when its rectangle, window or options changed;
    a surface clipped to nothing is as good as not wanted;
  - for a surface no longer wanted, `Hide` if `Keep`, else `Del`.
- **Order.** Its commands go out with the framework's frames, in the same
  stream, so that a placement lands with the cells around it.
- **Relayout.** A framework's renderer erases, scrolls and switches screens
  on its own, and a host drops placements with them (SPEC.md §5.4). The
  Session watches the output on its way out, and asks the program for a new
  layout when it sees: erase in display (2 or 3), scroll up or down, insert
  or delete lines, a new scrolling region, reverse index, leaving the
  alternate screen, or a full reset. An environment that knows its own
  redraws (an editor) uses its events instead.
- **Lost documents.** `ENOENT` in answer to a placement means the host lost
  the document (a reset, the alternate screen); the Session sends it again
  with the next layout.
- **Limits.** At most 48 surfaces by default, fewer when the host's
  `limits.surfaces` says so, or when an `EQUOTA` says so. To make room, it
  deletes the surfaces not wanted, the longest unseen first; under a limit
  the host set, a new surface waits for room.
- **Messages.** What the host sends comes back to the program as the
  framework's messages: ready (the mode is known), an event, an error (a
  command refused), an ack (the ok of a numbered command), relayout, and
  pong (a round trip timed). Everything else passes as it was.
- **Closing.** `Close()` deletes the surfaces the Session sent;
  `DetachAll()` detaches them instead, for a program that leaves them on
  the screen.

### 4.4 Test host

A host that runs inside a test, so that a program's tests need no terminal.
Go: `hottytest.Host`.

- **The terminal around it.** It answers what terminals answer: DA1, the
  cursor's position, the background colour, and, when asked to, the kitty
  graphics query. It tracks the alternate screen and full resets as a host
  does (SPEC.md §5.4), and keeps the cells the program printed. Made as a
  terminal that is not a host, it answers no HOTTY command.
- **The host.** It keeps every surface's document with the delta operations
  and the morph of SPEC.md §6, answers as SPEC.md §3.6 has hosts do, and
  passes the host vectors' `send` and `inspect` steps. It lays nothing out:
  `r=auto` gets an estimate the test may replace.
- **Strict by default.** A malformed message, an `EINVAL`, or a HOTTY
  command other than the query sent to a terminal that is not a host fails
  the test. A lenient host records them instead.
- **The user.** It plays the user: typing, clicking, filling a field,
  checking a box, choosing an option, submitting, pressing, dragging, and
  any event the test makes up.
- **Inspection.** The test reads each surface: its document, an element's
  attributes and text, the focused element, whether it is detached, and
  where it is placed.

An SDK that does not build one **MAY** test its SDK layer against another
implementation's host, over a pipe.

### 4.5 Relay

A relay stands between programs and a host, as a multiplexer does (SPEC.md
§2): it answers the query with the host's capabilities, gives each
program's surfaces names of their own on the host, places them where the
program's pane is, and passes events back to the program whose surface they
came from. plx's `pkg/hottyrelay` is one. This section is reserved: what a
relay does will be specified here, with its own vectors.

## 5. Conformance

### 5.1 Vector sections

`conformance/vectors.json` holds the vectors of hosts and of SDKs
([`conformance/README.md`](conformance/README.md)):

| section | checks | runs it |
| --- | --- | --- |
| `vectors` | a host: replies, documents, events | hosts, test hosts (§4.4) |
| `wire` | decoding a stream of commands | hosts and SDKs |
| `build` | the builders, their defaults and options (§3.4) | SDKs |
| `encode` | `Encode`: cleaning, chunks, compression (§3.3) | SDKs |
| `decode` | the Decoder and the messages (§3.6, §3.9) | SDKs |
| `scan` | the Scanner (§3.7) | SDKs |
| `detect` | the Detector (§3.8) | SDKs |

An SDK conforms when it meets every **MUST** of this document and passes
every SDK section.

### 5.2 Runners

- **Names in the vectors are canonical**, in snake case: a runner maps
  `set_text`, `keep_cursor` and `fit_rows` to its own names. That mapping is
  what keeps SDKs aligned.
- **`requires`.** A vector that needs something an SDK may not have yet
  names it in `requires`. A runner declares what it implements, and skips
  the vectors whose `requires` it lacks, so the list of what an SDK lacks is
  its runner's, not a list kept by hand.
- **A copy, checked.** An SDK keeps a copy of `vectors.json` in its tests,
  and a test that compares it with the spec's when a checkout is at hand
  (hotty-go: `make vectors`, `TestVectorsAreCurrent`). The runner checks
  that the vectors' version is the SDK's.

### 5.3 Implementations

| SDK | language | wire layer | SDK layer |
| --- | --- | --- | --- |
| [hotty-go](https://github.com/neuroplastio/hotty-go) | Go | the reference; lacks the Scanner, the Detector as a public component, `Caps.Passthrough` and `Caps.Version`, lenient capabilities, `Sends` for `dragstart` and `dragend`, unordered reply options, counting a malformed message that aborts a chunked one twice, the `Scroll` option, `Event.Area()` and `Caps.Scroll` | `hottyterm`, `hottytea`, `hottytest` |
| `clients/python` (this repository) | Python | complete | `Hotty`, for the examples |
| hotty.lua | Lua | planned, for Neovim and plx scripts | §4.2 |

hotty-go's runner (`vectors_test.go`) runs the `build`, `encode` and
`decode` sections, and skips the vectors that require what it lacks; `scan`
and `detect` wait for its Scanner and Detector. plx's `sdk/hotty` (Go) is a relay's codec, to be
replaced by hotty-go's. hotty-blitz's `hotty-wire` (Rust) is a host's.

---

## Appendix A. Names

The canonical names, in each language's case. Go's are hotty-go's.

| canonical | Go | Python | Lua | Rust | TypeScript |
| --- | --- | --- | --- | --- | --- |
| `Encode` | `hotty.Encode` | `hotty.encode` | `hotty.encode` | `hotty::encode` | `encode` |
| `Query` | `hotty.Query` | `query` | `query` | `query` | `query` |
| `Doc` | `Doc` | `doc` | `doc` | `doc` | `doc` |
| `Place`, `PlaceAt` | `Place`, `PlaceAt` | `place`, `place_at` | `place`, `place_at` | `place`, `place_at` | `place`, `placeAt` |
| `Hide`, `Delta` | `Hide`, `Delta` | `hide`, `delta` | `hide`, `delta` | `hide`, `delta` | `hide`, `delta` |
| `SetText`, `SetVar`, `SetAttr`, `RemoveAttr`, `MorphTo` | the same | `set_text`, `set_var`, `set_attr`, `remove_attr`, `morph_to` | as Python | as Python | `setText`, `setVar`, `setAttr`, `removeAttr`, `morphTo` |
| `Res`, `DelRes` | `Res`, `DelRes` | `res`, `del_res` | `res`, `del_res` | `res`, `del_res` | `res`, `delRes` |
| `Del`, `DelAll` | `Del`, `DelAll` | `delete`, `del_all` | `del`, `del_all` | `del`, `del_all` | `del`, `delAll` |
| `Detach`, `Focus`, `Blur`, `Sync` | the same | `detach`, `focus`, `blur`, `sync` | as Python | as Python | `detach`, `focus`, `blur`, `sync` |
| `Placement` and its fields | `Placement{Cols, Rows, Window, Z, Press, Fit, Hover, KeepCursor}` | `Placement(cols, rows, window, z, press, fit, hover, keep_cursor)` | a table with those keys | `Placement { cols, rows, … }` | `{ cols, rows, window, z, press, fit, hover, keepCursor }` |
| `N`, `Q`, `Detached`, `Scroll` | `hotty.N(n)`, `hotty.Q(q)`, `hotty.Detached()`, `hotty.Scroll(axes)` | `n=`, `q=`, `detached=`, `scroll=` | `{ n = …, q = …, detached = …, scroll = … }` | builder methods | `{ n, q, detached, scroll }` |
| `ScrollVertical`, `ScrollHorizontal` | `hotty.ScrollVertical`, `hotty.ScrollHorizontal` | `SCROLL_VERTICAL`, `SCROLL_HORIZONTAL` | `scroll_vertical`, `scroll_horizontal` | `SCROLL_VERTICAL`, `SCROLL_HORIZONTAL` | `SCROLL_VERTICAL`, `SCROLL_HORIZONTAL` |
| `Decoder.Feed`, `Invalid` | `(*Decoder).Feed`, `.Invalid` | `Decoder.feed`, `.invalid` | `decoder:feed` | `Decoder::feed` | `Decoder.feed` |
| `Scanner`, `Detector` | — | `Scanner`, `Detector` | `scanner`, `detector` | `Scanner`, `Detector` | `Scanner`, `Detector` |
| `Reply`, `Event`, `Caps` | `Reply`, `Event`, `Caps` | the same | tables with the fields in snake case | the same | the same |
| `FitRows`, `CellCSS` | `FitRows`, `CellCSS` | `fit_rows`, `cell_css` | as Python | as Python | `fitRows`, `cellCss` |

In the vectors, every name is in snake case: `place_at`, `keep_cursor`,
`fit_rows`, `cell_css`.

## Appendix B. Rationale

- **Why two layers.** What goes on the wire is the same in every program;
  how a program reads its terminal is not. A pure wire layer can be checked
  as data, in every language, by the same vectors, and an environment that
  does its own I/O (an editor, a page) still uses all of it.
- **Why shared defaults.** A program ported from one language to another
  should not start filling its input with replies, or wait a different time
  for an answer. Defaults are behaviour, and behaviour is what the program's
  user sees.
- **Why the Scanner and the Detector are in the wire layer.** Both are
  pure: bytes in, segments out; inputs and times in, a decision out. Both
  are where SDKs went wrong first: a reply cut across two reads read as
  keys, a DA1 left for the shell, a terminal that is a host taken for one
  that is not. As state machines with vectors, they are right once, in every
  language.
- **Why `Doc` and `Place` answer errors and nothing else does.** A refused
  document or placement leaves a hole in the program's screen, which the
  program must hear about; a delta that names a missing element is the
  program's bug, which a test finds. Asking for every reply would fill the
  input with them.
- **Why a `Q` given wins over `N`.** Options in most languages have no
  order: keyword arguments, a table, a struct. The rule that needs no order
  is the one every SDK can follow.
- **Why presentation is out.** HOTTY carries any HTML. How one program
  presents its content is that program's choice, and an SDK that builds
  documents would make it for every program, in each language differently.
