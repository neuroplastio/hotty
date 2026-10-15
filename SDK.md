# HOTTY SDKs

    Version:  0.3, with SPEC.md 0.3
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
- **It depends on the language's standard library only**, and on base64,
  zlib and msgpack where that library lacks them. msgpack writes a
  program's deltas and menus and reads what a host sends (SPEC.md §3.3).
  zlib is needed only to compress what a program sends, which is optional
  (§3.3); a host never compresses what it sends (SPEC.md §3.3).
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
- **Data takes the language's form**: what a message or a control holds
  (§3.2, §3.9) is a field or an accessor, and a question about it
  (`Has`) a method or a function. hotty-go's are plain structs with
  no methods but what its codec generates: a field (`ev.Value`), and a
  function beside the type (`hotty.Light(caps)`).

### 2.3 Shared defaults

The defaults in this document (quiet levels, timeouts, limits, the keymap
of §3.10) are the same in every SDK, so a program behaves the same in every language. An SDK
**MUST NOT** choose other defaults; it **MAY** let the program change them.

### 2.4 Protocol only

An SDK's contract is SPEC.md. Everything a program does with the protocol
that the protocol does not define, such as rendering Markdown, highlighting
code, drawing charts, or building forms from a schema, is presentation, and
outside this document. An SDK **MAY** ship such helpers beside it. They
depend on the SDK; the SDK never depends on them, and nothing in §3 or §4
needs them.

What a text field does with a key is the protocol's (SPEC.md §10.2), so
keymaps (§3.10) and editing a field in cells as a host edits it (§4.6) are
in this document.

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
- fields it does not know, in the capabilities or a detail, are ignored.
  Reading a message **MUST NOT** fail because of its body: a body that
  does not decode leaves absent what it would have filled (§3.9).

### 2.8 Environments

Some environments already do part of what the SDK layer does. A UI
framework's input parser may hand over complete OSC sequences; an editor may
own the terminal's output and hand its input over as events (§4.2). There,
the SDK layer uses what the environment provides: it feeds complete
sequences to the Decoder (§3.6) and writes through the environment's
output. The wire layer is the same everywhere.

### 2.9 Updates cost what they change

A program that redraws a surface's tree, itself or through a framework,
diffs the new tree against the last one it sent and sends what changed as
the ops of one delta (SPEC.md §6.1): a `text` op where a cell's text
changed, 56 bytes, where morphing the whole tree of a small table sends 930.
A whole-tree `morph` without a target stays the fallback, and keeps what the
user was doing. A stylesheet that several documents share goes once, as a
resource (SPEC.md §7.1), not in each document. An SDK's helpers that build
documents (§2.4) do both.

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
| keys (§3.10) | key names, keymaps, the SDK's keymap | `ParseKey`, `DecodeKeys`, `Keymap`, `TerminalKeys` | `keys`, `keymap` |

### 3.1 Constants and named sets

| name | value |
| --- | --- |
| `Number` | `"7279"`, the OSC number |
| `Chunk` | 4096, the most base64 bytes in one sequence |
| `MaxSize` | 1000, the most columns or rows of a surface |
| `MaxName` | 64, the longest surface name |
| `Version` | `"0.3"`, the protocol version the SDK speaks, which its query lists (SPEC.md §4) |
| `DefaultMax` | 16777216 (16 MiB), the most bytes a Decoder decodes one message to unless its `Max` says otherwise (§3.6) |

And these sets, each value under its canonical name:
- **event kinds**: `click`, `change`, `input`, `submit`, `press`, `focus`,
  `blur`, `fit`, `hover`, `view`, `dragstart`, `drag`, `dragend`,
  `command`, `caps` (SPEC.md §9);
- **features**: `passthrough`, `hover`, `count`, `menu` (SPEC.md §4);
- **modifier bits**: `ModShift` 1, `ModAlt` 2, `ModControl` 4, `ModMeta` 8
  (SPEC.md §9);
- **error codes**: `EINVAL`, `ENOENT`, `ENOTARGET`, `EDETACHED`, `EQUOTA`,
  `EBUDGET`, `EVERSION` (SPEC.md §3.6);
- **delta ops**: `morph`, `inner`, `replace`, `append`, `prepend`, `before`,
  `after`, `remove`, `attr`, `unattr`, `text`, `var`, `reveal` (SPEC.md
  §6.1);
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
  and only when compressing makes it smaller. It compresses at zlib's
  default level, 6: a stylesheet of 20 KB comes out a third smaller than at
  level 1, for about a millisecond. `o=z` follows the other keys.
- **`o` and `m` are Encode's.** A control given with either goes out
  without it, and Encode sets them as this section says.
- **Chunks.** A payload whose base64 is longer than 4096 bytes is split
  into chunks of exactly 4096, the last one excepted. Nothing of 4096 or
  less is chunked.
  - The first chunk carries the whole control, then `m=1`.
  - Every further chunk carries only `m`: `1`, or `0` on the last.
- **Every sequence ends with ST** (`ESC \`).

### 3.4 Commands

A builder for each action returns the command's sequences, ready to write.
Each takes the reply options of §3.4.2 and has the default quiet level shown,
which SPEC.md leaves to the program; these are the levels every SDK uses.

| builder | sends | parameters | default `q` |
| --- | --- | --- | --- |
| `Query` | `a=q:n=<n>:v=<Version>`, `late=1` with the `Late` option, then DA1 (`ESC [ c`) | n | 0 |
| `Doc` | `a=doc:s` and the HTML; `d=1` with the `Detached` option, `scroll` with `Scroll` | surface, html | 1 |
| `Place` | `a=place` (§3.4.1) | surface, placement | 1 |
| `PlaceAt` | `ESC 7`, `ESC [ <y+1> ; <x+1> H`, `Place` with `C=1`, `ESC 8` | surface, x, y, placement | 1 |
| `Hide` | `a=hide:s` | surface | 2 |
| `Delta` | `a=delta:s` and its ops as msgpack (§3.4.3) | surface, ops | 2 |
| `SetText` | `Delta` with one op, `Text` | surface, target, text | 2 |
| `SetVar` | `Delta` with one op, `Var` | surface, target, name, value | 2 |
| `SetAttr` | `Delta` with one op, `Attr` | surface, target, name, value | 2 |
| `RemoveAttr` | `Delta` with one op, `Unattr` | surface, target, name | 2 |
| `MorphTo` | `Delta` with one op, `Morph` | surface, target, html | 2 |
| `Reveal` | `Delta` with one op, `RevealOp`: `where` is `start`, `end`, or empty for the nearest (SPEC.md §6.1) | surface, target, where | 2 |
| `Res` | `a=res:id:type` and the data | id, mime, data | 2 |
| `DelRes` | `a=del:id` | id | 2 |
| `Del` | `a=del:s` | surface | 2 |
| `DelAll` | `a=del` | — | 2 |
| `Detach` | `a=detach:s` | surface | 2 |
| `Focus` | `a=focus:s[:t]`; `t` only when given | surface, target | 2 |
| `Blur` | `a=blur:s` | surface | 2 |
| `Sync` | `CSI ? 2026 h`, the commands, `CSI ? 2026 l` (SPEC.md §6.3) | commands | — |
| `WithdrawLate` | `a=q:q=2`: withdraws a query that asked for a late answer (SPEC.md §4) | — | — |
| `Edit` | `a=edit:take=<names>`, the names joined by `,`, in the order given; `take=` empty takes none (SPEC.md §10.6) | names | 2 |
| `Menu` | `a=menu` and the menu as msgpack (below); with no menu, no payload, which hides it (SPEC.md §10.5) | menu | 2 |

- **`Doc` and `Place` answer errors**, since a refused document or placement
  (`EQUOTA`, `ENOENT`) is something a program must hear. Everything else
  answers nothing unless asked: a program that sends deltas every frame would
  otherwise fill its input with replies.
- **`PlaceAt`** places a surface at screen cell (x, y), counted from 0, and
  leaves the cursor where it was: for a full-screen program, which places
  surfaces where it draws them. The coordinates have no leading zeros.
- **`Sync`** takes commands already built, and brackets them.
- **`Menu`** takes a `MenuLevel`: `Seq`, `Label` and `Items`, each item a
  `MenuItem` with `Key`, `Label`, `Group` and `Enabled`. It writes one
  msgpack map, each value in the smallest of its type's forms: `seq`,
  `label` unless it is empty, `items`; each item `key`, `label` unless it
  is empty, `group` only when true, `enabled`. These are myelin's names
  and order, so a program on myelin hands its menu over as it is.

#### 3.4.1 Placement

A `Placement` says where and how a surface is shown (SPEC.md §5.2):

| field | key | default | sent |
| --- | --- | --- | --- |
| `Cols` | `c` | — | always |
| `Rows` | `r` | 0, which is `auto` | always: the number, or `auto` |
| `Window` | `x`, `y`, `w`, `h` | none | all four, or none: none when absent, when all are 0, or when it shows the whole surface (rows given, and the window is 0, 0, cols, rows) |
| `Z` | `z` | 0 | when not 0 |
| `Press` | `p` | absent | `p=1` when on, `p=0` when off, nothing when absent |
| `Fit` | `f` | absent | as `Press` |
| `Hover` | `v` | absent | as `Press` |
| `KeepCursor` | `C=1` | false | when true |

`Press`, `Fit` and `Hover` belong to the surface (SPEC.md §5.2), so each is
absent, on or off: a placement that leaves them absent leaves them as they
were. Go spells them `hotty.On` and `hotty.Off`, with the zero value
absent.

#### 3.4.2 Reply options

Every builder but `Query`, `Sync` and `WithdrawLate` takes two options:
- **`N(n)`** numbers the command and asks for its reply: `n=<n>`, and
  quiet level 0 unless the program gives `Q`.
- **`Q(q)`** sets the quiet level. A `Q` given wins over the level `N`
  implies, whatever the order in which the program gives them.

**`q` goes out only when the wire does not imply it** (SPEC.md §3.5): it is
left out where it would be 0 with `n`, or 1 without, and for the query. So
`Doc` and `Place` carry no `q`, a delta carries `q=2`, and `Doc` with `N(4)`
carries `n=4` alone.

`Query` takes one option of its own, **`Late`** (`late=1`): the program
asks for a late answer (SPEC.md §4).

Each key goes out once. `Doc` also takes **`Detached`** (`d=1`) and
**`Scroll(axes)`** (`scroll=<axes>`, SPEC.md §5.1): a bitmask of
`ScrollVertical` (1) and `ScrollHorizontal` (2). `0`, the default, sends
no key; any other value goes out as given, for the host to judge.

#### 3.4.3 Ops

`Delta(surface, ops…)` sends one delta of the ops given, in order (SPEC.md
§6.1). An **`Op`** has `Op`, `Target`, `Key` and `Value`, and a builder for
each op makes one:

| builder | op | parameters |
| --- | --- | --- |
| `Morph` | `morph` | target (empty: the whole tree), html |
| `Inner`, `Replace`, `Append`, `Prepend`, `Before`, `After` | the same, in lower case | target, html |
| `Remove` | `remove` | target |
| `Attr` | `attr` | target, name, value |
| `Unattr` | `unattr` | target, name |
| `Text` | `text` | target, text |
| `Var` | `var` | target, name, value |
| `RevealOp` | `reveal` | target, where |

The body is one msgpack map, `{"ops": [op, …]}`, each value in the smallest
of its type's forms, and each op a map with its keys in this order:
- `op`;
- `t`, unless the target is empty;
- `k`, for `attr`, `unattr` and `var`;
- `v`: for an op that takes one (SPEC.md §6.1), always, even empty; for
  `reveal`, only when `where` is `start` or `end`.

Targets and values are not cleaned (§3.3): they travel in the body, as the
document has them. A `Delta` of no ops is still sent, and the host answers
it `EINVAL` (SPEC.md §6.1).

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
  - A control with only `m` continues the message in progress; with none
    in progress, it is malformed.
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
- **`Max`** is the most bytes one message decodes to, after base64 and
  zlib; 0 is `DefaultMax`. Past it the message is `invalid`, counted once
  (SPEC.md §3.4, §3.7): a chunked one holds no more base64 than `Max` bytes
  could take, zlib's overhead included, and its further chunks are dropped
  up to its last, which reports `invalid` without counting again. Zlib
  stops inflating past `Max`. A host that decodes with a Decoder reports
  its `Max` as `limits.message` (SPEC.md §13).

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
- **`Holding()`** returns what it holds, and **`InSequence()`** whether
  that is a HOTTY sequence in progress (or one too long, being dropped),
  which the next `Feed` goes on with, rather than the start of a segment,
  which a program reading keys may flush after a moment as typing.
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
  program chooses another, with `Late` when the program asks for a late
  answer (SPEC.md §4).
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
| a reply that answers the query (`re=q`, the query's `n`): `a=ok`, its capabilities decoding (§3.9), their `V` the SDK's `Version` | the terminal is a host: `native`, decided, with its capabilities. Done when the DA1 behind it arrives, or 300 ms after the reply, or at 1500 ms, whichever comes first |
| any other reply that answers the query: an error (`EVERSION`, or another), or capabilities that do not decode or name another version | the terminal is no host the program can use (SPEC.md §4): `text`, decided. Done as for a host's reply |
| a DA1 before any reply | it may answer a question asked before the query (SPEC.md §4). It opens a grace of 150 ms: a reply within it still answers the query |
| the grace ends with no reply | `text`: not a host. Decided and done |
| 1500 ms with no answer at all | `text`. Decided and done |
| the input ends | `text` if nothing was decided. Done |
| with `Late`, a reply that answers the query once the state is `text`, and makes the terminal a host (the first rule) | a late answer: `native`, with its capabilities. Still decided and done |

- **Which inputs are detection's.** Every DA1 from the start until done is
  detection's, and the SDK layer swallows it: it answers the query's fence or
  an earlier question, and is no key. After done, a DA1 is not
  detection's. A reply that answers the query, `a=ok` or `a=err`, is
  detection's whenever it arrives, even after the state is `text`; a late
  one changes nothing, unless the query asked for it (`Late`), and then
  only the first that makes the terminal a host. Replies with another `n`,
  and everything else, are not.
- **Decided and done** differ only when the terminal answers the query:
  whether it is a host the program can use is known when its reply
  arrives, and the detection is over when nothing more of it will arrive. A program that must not wait, such as a framework's adapter
  (§4.3), acts when decided; one that hands the terminal on, when done.

### 3.9 Messages

A decoded **`Message`** has its control (a map of keys to values) and its
payload (bytes). It reads as a reply or as an event.

**The body** (SPEC.md §3.3) is decoded when the reply or event is read, each
field as its type.
- Fields the SDK does not know are ignored (§2.7), whatever their type.
- A body nested more than 32 levels deep does not decode. An SDK stops
  reading there, so that no body can exhaust its stack: TinyGo's is 64 KB,
  and a few hundred levels crash it.
- Nor does a body that holds, anywhere in it, a field the SDK knows or
  not, what SPEC.md §3.3 has no host send: a nil, a map key that is not a
  string, a key given twice in one map (keys compared as the strings they
  are, whatever their form), a string that is not UTF-8, an int further than 2^53 − 1 from
  zero, or a timestamp of another size, with a second's nanoseconds or
  more, or with seconds further than 2^53 − 1 from 1970. Each is checked
  as the body is read, in every SDK alike, so a body decodes in all of
  them or in none: an int past 2^53 − 1 is not rounded where numbers are
  doubles, nor kept where they are not.
- A body that does not decode leaves absent everything it would have
  filled, and the rest of the message stands. That is a body that is not
  one msgpack map, one that breaks a rule above, or one with a field the
  SDK knows holding another type. What it fills is the capabilities, an
  error's code and detail, or what an event's detail carries.

**`Reply`** (SPEC.md §3.6), when the action is `ok` or `err`:

| name | from |
| --- | --- |
| `OK` | `a=ok` |
| `Re` | `re`: the action answered |
| `N` | `n`, as a number; absent when the command had none |
| `Surface` | `s`; absent when the command named none |
| `Cols`, `Rows` | `c` and `r`, as numbers, in a reply to `place` |
| `Code`, `Detail` | the error's body, when not OK |
| `Op` | `i`, as a number, in an error answering a delta: the op at fault (SPEC.md §6.1); absent otherwise |
| `Caps` | the capabilities, the body of an ok reply to `q` |
| `Err` | the reply as an error, carrying `Code` and `Detail`; none when OK |

**`Event`** (SPEC.md §9), when the action is `ev`: `Surface` (absent for
`command` and `caps`, which belong to no surface), `Kind` (as it came,
known or not), `Target` (`t`, empty when absent), and what the detail
carries, each absent when the event does not carry it:

| name | holds | for |
| --- | --- | --- |
| `Value` | `value`, a string | `click`, `change`, `input` |
| `Checked` | `checked`, a boolean | `change` |
| `Fields` | `fields`: the pairs of a name and a value, in order (SPEC.md §9) | `submit` |
| `Mods` | `mods`: the modifier bits (§3.1), 0 when absent | `click`, `press`, `dragstart`, `drag`, `dragend` |
| `Link` | `href`, and `url` if present | `click` on a link |
| `FitRows` | `r` | `fit` |
| `Drag` | `c` and `r`; the steps `x` and `y` in the element dragged, and `tx` and `ty` in a `t` with `drop` (as `TX` and `TY` where the language capitalises), each absent when the detail has none (SPEC.md §9.1) | `dragstart`, `drag`, `dragend` |
| `Hover` | `c` and `r`, or `out` | `hover` |
| `Area` | `area`: `c`, `r`, `w` and `h`, the element's cells | `click`, `press` |
| `Count` | `count`: the click's place in its run of clicks (SPEC.md §9), 2 for the second click of a double click; 1 for a click whose detail has none | `click` |
| `View` | `Areas`, from `in`: each id in view to its cells as `Area` holds them, leaving out one whose area lacks a field, and none when `in` is absent; and `AtEnd`, from `end`, false when absent (SPEC.md §9.5) | `view` |
| `Command` | `Name`, `Key` and `Text`, from `name`, `key` and `text`, each empty when absent, and `HasText`, whether `text` is there (SPEC.md §10.6); absent when the detail has no `name` | `command` |
| `Changed` | the capabilities that changed, a `Caps` with only the fields the detail has (SPEC.md §4) | `caps` |

The detail is read by the event's kind, so a form field named `value` is in
`Fields` and nowhere else. An event of a kind the SDK does not know carries
none of these, and its payload is in its message.

**`Caps`** (SPEC.md §4) has every field SPEC.md lists: `V`, `CellCSS`
(`w`, `h`, from `cellcss`), `Scale`, `Scheme`, `Mod`, `Features`,
`Limits`, `Net`, `Edit`, `Host`, `Version`. It also answers:
- `Has(feature)`: whether `feature` is in `features` (SPEC.md §4);
- `Light`: the scheme is `light`;
- `Merge(changed)`: the capabilities with the fields of a `caps` event's
  `Changed` in place of their own, and without those it empties (`{}`,
  `[]` or `""`: absent now, SPEC.md §9).

**An error** carries `Code` and `Detail`, and its message names both.

### 3.10 Keys

What a text field does with a key (SPEC.md §10.2, §10.4), as data: so that a
program that draws its fields in cells edits them as a host edits them on a
surface, and the keymap it gives a surface is the one it uses in cells. And
which keys any other element gives the program, or scrolls with, for a
host.

- **`ParseKey(name)`** reads a key's name in any of the forms SPEC.md §10.4
  allows (`Shift+Control+a`, `Control+ `) and returns it in the canonical
  one (`Control+A`, `Control+Space`): modifiers in the order `Mod`,
  `Control`, `Alt`, `Meta`, `Shift`, Shift shown in a character where the
  character can show it, `Space` for a space. `Mod` is kept as written: a
  keymap reads it (below). A name that does not parse (empty, an unknown
  modifier, `Control+` with no key) is absent.
- **`Platform`** is how a host reads bindings: `Mod`, `Control` or `Meta`
  (SPEC.md §10.4), and `Edit`, its edit shortcuts, from each action to its
  keys (SPEC.md §10.2). The zero Platform is `Control` with the default
  edit shortcuts. `PlatformOf(caps)` takes both from the capabilities,
  each the zero Platform's when absent. `DefaultEdit(mod)` returns the
  default edit shortcuts for a `Mod`, in SPEC.md §10.2's order, the keys
  canonical with `Mod` read: `Control+Z` and `Control+y` for `redo` where
  it is Control.
- **`DecodeKeys(input)`** reads input from the terminal, the bytes a
  program reads, as SPEC.md §10.4 names it: a list with one entry for each
  key, the key's canonical name, or absent for input that is no key it
  names (a mouse report, a sequence it does not know). It is pure: an `ESC`
  at the end of the input is `Escape`, and the caller passes each read
  whole (a framework's parser has already cut the input into keys).
- **`Keymap`** is a set of bindings, key to action, read on a Platform.
  `ParseKeymap(platform, value)` reads a `data-keys` value as SPEC.md
  §10.2 has hosts read it, dropping the bindings a host ignores, and `Mod`
  as the Platform's: on Control, `Mod+a` and `Control+a` are one key, the
  later binding's. `Format()` writes one back: each key once, where it was
  first bound, as its last binding wrote it (`Mod` kept), with its last
  action, as `key=action`, separated by a space.
- **`Resolve(platform, multiline, values…)`** builds a field's keymap:
  SPEC.md's default keymap for the Platform's `Mod`, with its `Edit`, for
  an `input` or for a multi-line field, then each `data-keys` value in
  turn, the root's first. A binding to a scroll action is left out where
  it stands, in its own value too: it neither acts nor overrides an
  earlier binding of its key (SPEC.md §10.2).
- **`Lookup(key)`** on a resolved keymap returns what the field does with
  the key: an action; `insert` for a character it types; or absent when the
  key is not the field's (it reaches the program, or Tab moves focus). Tab,
  Shift+Tab and Escape are never the field's, nor a key bound to `program`
  or `prefix`, or to an action the field does not have.
- **`Selects(key)`** says whether the field selects with the key (SPEC.md
  §10.2, Shift selects): `Lookup` returns a move for it, and its canonical
  name has `Shift` (`Shift+ArrowLeft`, `Control+Shift+End`, not `Alt+<`).
  A field then does the move with `Extend` (§4.6).
- **`Program(key)`** says whether a keymap gives the key to the program: it
  binds the key to `program` or `prefix`, or, for a key with Shift it does
  not bind, the key without Shift. On an element that is not a text field, a host asks it
  of the element's keymap, `ParseKeymap` of its `data-keys` values joined
  with a space, the root's first, on the host's Platform, with no default
  keymap; a key it gives
  reaches the program before the element or a scroll uses it (SPEC.md
  §10.2, keys for the program).
- **`Prefix(key)`** says whether a keymap binds the key to `prefix`, with
  the same fallback without Shift. A host asks it of a key `Program` gives
  the program, and from then on gives the program every key (SPEC.md
  §10.5).
- **`Scroll(key)`** returns the scroll action a keymap binds the key to,
  with the same fallback without Shift, or absent. A host asks it of the
  keymap it asks `Program` of, for a key the element does not use (SPEC.md
  §10.2, scrolling keys).
- **`TerminalKeys`** is the SDK's keymap, the same in every SDK (§2.3): the
  keys of Bubble Tea's text input and text area (bubbles), which a program
  that edits fields in cells is likely to share, but for Mod+a, which
  selects all, as in a GUI field and SPEC.md's default keymap: Control+a
  on Linux, while on macOS Control+a stays the line's start. A program puts it in the
  `data-keys` of an element that holds its fields, and gives its cells
  rendition the same keymap, `Resolve(platform, multiline, TerminalKeys)`.

  | action | keys |
  | --- | --- |
  | `char-backward`, `char-forward` | ArrowLeft, Control+b; ArrowRight, Control+f |
  | `word-backward` | Alt+ArrowLeft, Control+ArrowLeft, Alt+b |
  | `word-forward` | Alt+ArrowRight, Control+ArrowRight, Alt+f |
  | `line-start`, `line-end` | Home; End, Control+e |
  | `delete-char-backward` | Backspace, Control+h |
  | `delete-char-forward` | Delete, Control+d |
  | `delete-word-backward` | Alt+Backspace, Control+w, Control+Backspace |
  | `delete-word-forward` | Alt+Delete, Alt+d, Control+Delete |
  | `delete-to-line-start`, `delete-to-line-end` | Control+u; Control+k |
  | `line-previous`, `line-next` | ArrowUp, Control+p; ArrowDown, Control+n |
  | `page-up`, `page-down` | PageUp; PageDown |
  | `input-start`, `input-end` | Alt+<, Control+Home; Alt+>, Control+End |
  | `select-all` | Mod+a |
  | `newline` | Control+m |

  It leaves Enter to SPEC.md's default (`submit` in an `input`, `newline`
  in a multi-line field). In the order of this table, it is the value
  vectors call `terminal_keys`.

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
- **A late answer.** A terminal opened with `Late` asks for one (SPEC.md
  §4). If it comes, it goes to the event stream as the host's capabilities,
  and `Detect()` answers with it from then on. Until it comes, the
  terminal stays in raw mode, or the answer would be echoed, and `Close()`
  withdraws the query (`WithdrawLate`), so that no answer reaches whatever
  reads the terminal next.
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
  file). It sends nothing but a withdrawal of a late query (above): what is
  left on the screen, and the replies not read, are the program's to
  settle first (§2.6).
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
- **A late answer is the environment's**, since detection is: one query
  asks for it for every session, and it is withdrawn while a shell has the
  terminal (on exit and suspension).
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
- **A late answer.** A Session made with `Late` asks for one (SPEC.md §4),
  through its terminal when the terminal detects. If it comes while the
  mode is `Text`, the mode becomes `Native`, ready is sent again, and then
  the program is asked for a layout: a program that asks for a late answer
  draws either rendition whenever the mode says. Until it comes, `Close()`
  withdraws the query (`WithdrawLate`).
- **Layout.** With each frame, the program says which surfaces it wants
  where: name, rectangle on the screen, an optional clip (the part of the
  screen the surface shows in, such as a scrolling region), `Keep`, `Z`,
  `Press`, `Fit`, `Hover`, `Scroll` (the axes the host scrolls the document
  along, §3.4.2), and a function that returns the document. The Session
  sends only what changed:
  - a document once, attached, with its `Scroll`, and again only when the
    host has lost it or its `Scroll` changed;
  - a placement (`PlaceAt`) when its rectangle, window or options changed,
    with `Press`, `Fit` and `Hover` only when they differ from what the
    surface has (SPEC.md §5.2), on or off; a surface clipped to nothing is
    as good as not wanted;
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
  terminal that is not a host, it answers no HOTTY command, until the test
  makes it a host, as a multiplexer's terminal attaching does: then it
  answers a query that asked for a late answer and was not answered
  (SPEC.md §4), and every command after.
- **The host.** It keeps every surface's document with the delta operations
  and the morph of SPEC.md §6, answers as SPEC.md §3.6 has hosts do, and
  passes the host vectors' `send`, `inspect` and `key` steps. It speaks
  the SDK's `Version` only: it answers a query that lists it with its
  capabilities, and any other with `EVERSION` (SPEC.md §4). It lays
  nothing out: `r=auto` gets an estimate the test may replace, nothing in
  it scrolls, so a key bound to a scroll action goes on as if its keymap
  did not bind it (SPEC.md §10.2), and it sends no `view`. Nor can it
  measure where in an element the pointer is: a drag of an element with
  `data-steps` carries the steps the test gives, in it and in `t` (SPEC.md
  §9.1). A drag goes to the element the test names, which may be one with
  `drop` in its `data-on`. So it skips the vectors marked `scroll`,
  `steps`, `drop` and `view` (conformance/README.md), which every other
  host passes.
- **Strict by default.** A malformed message, an `EINVAL`, or a HOTTY
  command other than the query sent to a terminal that is not a host fails
  the test. A lenient host records them instead.
- **The user.** It plays the user: typing, pressing a key as SPEC.md §10.2
  has a host take it, clicking, filling a field, checking a box, choosing
  an option, submitting, pressing, dragging, and any event the test makes
  up.
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

### 4.6 Field

A text field's value, caret and selection, edited as SPEC.md §10.2's actions
edit them, for a program that draws its fields in cells (the second
rendition, §2.5). Go: `hottyedit.Field`, a module of its own for its
grapheme segmentation.

- **The field.** `Value`, `Caret` (a count of characters, grapheme
  clusters, from the start), `Anchor`, `Multiline`, `Password`, and
  `Rows`, the rows it shows (1 when absent), for `page-up` and
  `page-down`.
- **The selection** runs from `Anchor`, the end where it began, to the
  caret (SPEC.md §10.2). Nothing is selected when `Anchor` is absent or at
  the caret. `Selection()` returns its start and end, equal when nothing
  is selected, for the rendition to draw. `Select(anchor, caret)` sets
  both, for a selection the user makes with the pointer, and
  `Select(p, p)` puts the caret at `p` with nothing selected. Go keeps the
  anchor behind `Anchor()` and `Select`, since a `Field` literal's zero
  anchor would select.
- **Rows are lines.** A field in cells does not wrap: each line is a row,
  and the place along it is a count of characters. A rendition that wraps
  moves the caret between its rows itself.
- **`Do(action)`** does an action, and reports whether the value changed,
  so the program knows when to report an `input`. A selection comes first,
  as SPEC.md §10.2 says: a delete deletes it, a move starts from its start
  or its end and ends it, and `select-all` selects the whole value.
  `submit` and `program` are the program's, and change nothing, as are
  `copy`, `cut`, `paste`, `undo` and `redo`: a Field holds no clipboard
  and no history, which a program that keeps them adds around it.
- **`Extend(action)`** does a move as Shift does it (SPEC.md §10.2): the
  anchor stays, or is set where the caret is, and the caret moves from
  where it is. An action that is not a move is `Do`'s.
- **A run of row moves,** `line-previous`, `line-next`, `page-up` and
  `page-down`, with `Do` or `Extend`, keeps the place along the row it
  started from; any other action, typing, or `Select` ends it.
- **`Type(text)`** types text at the caret, in place of the selection.
- **`Key(keymap, key)`**, where an SDK has it, does what the keymap says
  of the key: types it, does its action, or, when `Selects(key)`, extends
  with it.

An SDK whose language has no grapheme segmentation **MAY** count code
points instead, CR LF still one, and says so (§5.3); it then skips the
vectors that require `graphemes`. So does its `DecodeKeys`, for a character
of more than one code point.

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
| `keys` | key names and `DecodeKeys` (§3.10, SPEC.md §10.4) | hosts and SDKs |
| `keymap` | `ParseKeymap`, `Resolve`, `Lookup`, `Program`, `Scroll` and `TerminalKeys` (§3.10, SPEC.md §10.2) | hosts and SDKs |
| `edit` | the actions on a value: a Field (§4.6) | hosts, and SDKs with a Field |

An SDK conforms when it meets every **MUST** of this document and passes
every SDK section, `edit` where it provides a Field.

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
| [hotty-go](https://github.com/neuroplastio/hotty-go) | Go | the reference; complete, with what a relay writes as a host (replies, events, `Message.Placement`, `CursorBelow`) | `hottyterm`, `hottytea`, `hottytest`, `hottyedit` (§4.6) |
| `clients/python` (this repository) | Python | complete | `Hotty`, for the examples |
| [hotty-lua](https://github.com/neuroplastio/hotty-lua) | Lua | complete for 0.2, under LuaJIT, Lua 5.1, Neovim and gopher-lua (plx's); 0.3 to come | `hotty.nvim` (§4.2) |

hotty-go's runners (`vectors_test.go`, and `hottyedit`'s for `edit`) run
every SDK section and skip nothing. hotty-lua's (`tests/vectors.lua`, under
each of its runtimes) and the Python client's count code points (§4.6) and
skip only the vectors that require `graphemes`. plx's `sdk/hotty` (Go) is a
relay's codec, to be replaced by hotty-go's, which has all that plexos
listed it uses. hotty-blitz's `hotty-wire` (Rust) is a host's; its tests
run the `keys`, `keymap` and `edit` sections.

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
| `Op` and its fields | `hotty.Op{Op, Target, Key, Value}` | `Op(op, target, key, value)` | a table with those keys | `Op { op, target, key, value }` | `{ op, target, key, value }` |
| `Morph`, `Inner`, `Replace`, `Append`, `Prepend`, `Before`, `After`, `Remove`, `Attr`, `Unattr`, `Text`, `Var`, `RevealOp` | `hotty.OpMorph`, `hotty.OpInner`, …, `hotty.OpText`, `hotty.OpVar`, `hotty.OpReveal` (`hotty.Text` is a detector's state) | `morph`, `inner`, …, `text`, `var`, `reveal_op` | as Python | as Python | `morph`, `inner`, …, `text`, `varOp`, `revealOp` |
| `SetText`, `SetVar`, `SetAttr`, `RemoveAttr`, `MorphTo`, `Reveal` | the same | `set_text`, `set_var`, `set_attr`, `remove_attr`, `morph_to`, `reveal` | as Python | as Python | `setText`, `setVar`, `setAttr`, `removeAttr`, `morphTo`, `reveal` |
| `Res`, `DelRes` | `Res`, `DelRes` | `res`, `del_res` | `res`, `del_res` | `res`, `del_res` | `res`, `delRes` |
| `Del`, `DelAll` | `Del`, `DelAll` | `delete`, `del_all` | `del`, `del_all` | `del`, `del_all` | `del`, `delAll` |
| `Detach`, `Focus`, `Blur`, `Sync` | the same | `detach`, `focus`, `blur`, `sync` | as Python | as Python | `detach`, `focus`, `blur`, `sync` |
| `WithdrawLate` | `hotty.WithdrawLate` | `withdraw_late` | `withdraw_late` | `withdraw_late` | `withdrawLate` |
| `Edit`, `Menu` | `hotty.Edit`, `hotty.Menu` | `edit`, `menu` | as Python | as Python | `edit`, `menu` |
| `MenuLevel`, `MenuItem` and their fields | `hotty.MenuLevel{Seq, Label, Items}`, `hotty.MenuItem{Key, Label, Group, Enabled}` | `MenuLevel(seq, label, items)`, `MenuItem(key, label, group, enabled)` | tables with those keys | `MenuLevel { seq, … }` | `{ seq, label, items }` |
| `Placement` and its fields | `Placement{Cols, Rows, Window, Z, Press, Fit, Hover, KeepCursor}` | `Placement(cols, rows, window, z, press, fit, hover, keep_cursor)` | a table with those keys | `Placement { cols, rows, … }` | `{ cols, rows, window, z, press, fit, hover, keepCursor }` |
| a flag on, off or absent (`Press`, `Fit`, `Hover`) | `hotty.On`, `hotty.Off`, the zero value | `True`, `False`, `None` | `true`, `false`, `nil` | `Option<bool>` | `true`, `false`, `undefined` |
| `N`, `Q`, `Detached`, `Scroll`, `Late` | `hotty.N(n)`, `hotty.Q(q)`, `hotty.Detached()`, `hotty.Scroll(axes)`, `hotty.Late()` | `n=`, `q=`, `detached=`, `scroll=`, `late=` | `{ n = …, q = …, detached = …, scroll = …, late = … }` | builder methods | `{ n, q, detached, scroll, late }` |
| `ScrollVertical`, `ScrollHorizontal` | `hotty.ScrollVertical`, `hotty.ScrollHorizontal` | `SCROLL_VERTICAL`, `SCROLL_HORIZONTAL` | `SCROLL_VERTICAL`, `SCROLL_HORIZONTAL` | `SCROLL_VERTICAL`, `SCROLL_HORIZONTAL` | `SCROLL_VERTICAL`, `SCROLL_HORIZONTAL` |
| `Decoder.Feed`, `Invalid`, `Max` | `(*Decoder).Feed`, `.Invalid`, `.Max` | `Decoder.feed`, `.invalid`, `.max` | `decoder:feed`, `.invalid`, `hotty.decoder({ max = … })` | `Decoder::feed`, `.invalid`, `.max` | `Decoder.feed`, `.invalid`, `.max` |
| `DefaultMax` | `hotty.DefaultMax` | `DEFAULT_MAX` | `DEFAULT_MAX` | `DEFAULT_MAX` | `DEFAULT_MAX` |
| `Scanner`, `Detector` | `Scanner`, `Detector` | `Scanner`, `Detector` | `scanner`, `detector` | `Scanner`, `Detector` | `Scanner`, `Detector` |
| `Holding`, `InSequence` | `(*Scanner).Holding`, `.InSequence` | `Scanner.holding`, `.in_sequence` | `scanner:holding`, `:in_sequence` | `Scanner::holding`, `::in_sequence` | `Scanner.holding`, `.inSequence` |
| `Reply`, `Event`, `Caps` | `Reply`, `Event`, `Caps` | the same | tables with the fields in snake case | the same | the same |
| `FitRows`, `Mods`, `CellCSS` | `FitRows`, `Mods`, `CellCSS` | `fit_rows`, `mods`, `cell_css` | as Python | as Python | `fitRows`, `mods`, `cellCss` |
| `ModShift`, `ModAlt`, `ModControl`, `ModMeta` | `hotty.ModShift`, … | `MOD_SHIFT`, … | `MOD_SHIFT`, … | `MOD_SHIFT`, … | `MOD_SHIFT`, … |
| a message as a `Reply` or an `Event`, `Err` | `hotty.ReplyOf(m)`, `hotty.EventOf(m)`, `hotty.Err(r)` | `m.reply()`, `m.event()`, `r.err()` | `m:reply()`, `m:event()`, `r:err()` | methods | `m.reply()`, `m.event()`, `r.err()` |
| `Has`, `Light`, `Merge` | `hotty.HasFeature(c, feature)` (`hotty.Has` asks a control), `hotty.Light(c)`, `hotty.Merge(c, changed)` | `c.has(feature)`, `c.light()`, `c.merge(changed)` | `c:has(feature)`, … | methods | `c.has(feature)`, … |
| `Command`, `Changed` | `Event.Command`, `Event.Changed` | `e.command`, `e.changed` | as Python | methods | `e.command`, `e.changed` |
| a control's `get` and `with` | `hotty.Get(ctl, k)`, `hotty.With(ctl, k, v)` | the SDK's own | the SDK's own | the SDK's own | the SDK's own |
| `ParseKey`, `DecodeKeys` | `hotty.ParseKey`, `hotty.DecodeKeys` | `parse_key`, `decode_keys` | as Python | as Python | `parseKey`, `decodeKeys` |
| `Keymap`, `ParseKeymap`, `Resolve`, `Lookup`, `Program`, `Prefix`, `Scroll`, `Format` | `hotty.Keymap`, `hotty.ParseKeymap`, `hotty.Resolve`, `(Keymap).Lookup`, `.Program`, `.Prefix`, `.Scroll`, `.Format` | `Keymap`, `parse_keymap`, `resolve`, `Keymap.lookup`, `.program`, `.prefix`, `.scroll`, `.format` | `parse_keymap`, `resolve`, `keymap:lookup`, `:program`, `:prefix`, `:scroll`, `:format` | as Python | `Keymap`, `parseKeymap`, `resolve`, `.lookup`, `.program`, `.prefix`, `.scroll`, `.format` |
| `TerminalKeys` | `hotty.TerminalKeys` | `TERMINAL_KEYS` | `TERMINAL_KEYS` | `TERMINAL_KEYS` | `TERMINAL_KEYS` |
| `Platform`, `PlatformOf`, `DefaultEdit` | `hotty.Platform{Mod, Edit}`, `hotty.PlatformOf`, `hotty.DefaultEdit` | `Platform(mod, edit)`, `platform_of`, `default_edit` | a table `{ mod = …, edit = … }`, `platform_of`, `default_edit` | as Python | `{ mod, edit }`, `platformOf`, `defaultEdit` |
| `Field`, `Do`, `Type` | `hottyedit.Field`, `(*Field).Do`, `.Type` | `Field`, `.do`, `.type` | `field`, `:do_action` (`do` is a keyword), `:type` | `Field`, `do_action`, `type_text` | `Field`, `.do`, `.type` |

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
- **Why the SDK has a keymap of its own.** SPEC.md's default keymap is
  small, so that a program that names no keys loses none. A program that
  edits fields in cells, though, has a keymap already, usually its
  framework's, and wants its surfaces' fields to edit the same. Bubble
  Tea's is the one the reference SDK's programs have; one keymap shared by
  every SDK keeps a program the same in every language (§2.3).
- **Why a body decodes whole or not at all.** A codec generated from the
  types (Go's msgp, Rust's serde) stops at the first field of the wrong
  type. A rule every SDK can keep is the one such a codec keeps, and a
  host that sends a wrong type fails the vectors instead.
- **Why presentation is out.** HOTTY carries any HTML. How one program
  presents its content is that program's choice, and an SDK that builds
  documents would make it for every program, in each language differently.

## Appendix C. Moving from 0.2

Informative. HOTTY 0.3 breaks 0.2 (SPEC.md §15), as a fold of what 0.2
grew. A program and its SDK move together, and its tests' fake hosts with
them. These are the places a port goes wrong:

- **A delta is a list of ops.** `Delta(surface, op, target, key,
  payload)` became `Delta(surface, ops…)`, the ops built by `Text`,
  `Attr` and the rest (§3.4.3; in Go `OpText`, `OpAttr`, …). A frame's changes to one surface go in one
  delta, which the host applies as one; the one-op shorthands (`SetText`,
  …) are still there for a single change.
- **The flags stay on the surface.** `p`, `f` and `v` hold until the
  program turns them off (SPEC.md §5.2). A program that placed a surface
  without `Press` to stop its presses now sends `Press: Off`. A Session
  (§4.3) sends them when they change.
- **Ask by feature.** `Supports`, `Sends`, `Drags`, `Hovers`, `Views` and
  the capabilities' `Passthrough`, `Scroll`, `Steps`, `Drop`, `Count` and
  `Menu` are gone: everything a 0.3 host does, it does, and `HasFeature(c,
  feature)` answers for `passthrough`, `hover`, `count` and `menu`.
- **The cell is in CSS pixels.** `Cell`, in device pixels, is gone, and
  `CellCSS` is the host's own field. There is no `resize`: a new font is a
  `caps` event with the new `CellCSS`, which `Merge` folds in.
- **A submit's fields are pairs**, in order: two fields of one name are
  two pairs. Code that looked a name up in a map looks it up in the pairs.
- **Modifiers are bits.** A drag's `Keys` list is `Mods`, and clicks and
  presses carry it too: `Mods & ModShift` for Shift.
- **An empty target is absent.** `Target` reads the same, empty, but a
  host's `t=` with nothing after it is gone from the wire, and a fake host
  that sends one is out of date.
- **No key sequences in the host.** `data-key` and the capabilities'
  `Keys` are gone. A program binds its leader to `prefix` (SPEC.md §10.5),
  reads the keys after it, and sends `a=focus` when the sequence ends. Its
  menu goes to `Menu`, as in the cells.
- **Errors only, unless asked.** A builder sends no `q` where the wire
  implies it, and `N(n)` alone asks for the reply. A fake host must answer
  a command without `q` only with an error.
