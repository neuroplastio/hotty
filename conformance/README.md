# HOTTY conformance vectors

`vectors.json` is what a host and an SDK must do, as data.

The host sections (`vectors`, `wire`) are run by two hosts that share no
code:
- hotty-blitz: `crates/hotty-blitz/tests/conformance.rs`, which runs the
  `keys`, `keymap` and `edit` sections too, the edits on a real surface;
- xterm-addon-hotty: `tests/e2e/conformance.spec.ts` and
  `tests/unit/conformance.test.ts` (with `keys`, `keymap` and `edit`).

hotty-go's test host runs `vectors` too (`hottytest/conformance_test.go`).

The SDK sections (`wire`, `build`, `encode`, `decode`, `scan`, `detect`,
`keys`, `keymap`, `edit`; SDK.md §5) are run by:
- the Python client: `clients/python/test_vectors.py`, every section;
- hotty-go: `hotty_test.go` (`wire`), `vectors_test.go` (`build`,
  `encode`, `decode`, `scan`, `detect`, `keys`, `keymap`) and
  `hottyedit/field_test.go` (`edit`);
- hotty-lua: `tests/vectors.lua`, every section, under each of its
  runtimes.

The Python client and hotty-lua count code points, not grapheme clusters
(SDK.md §4.6), and skip the vectors that require `graphemes`.

A disagreement is either a bug or a line of `SPEC.md` or `SDK.md` that says
too little.

## Format

```
{ "version": "0.1",
  "vectors": [ { "name": …, "steps": [ step, … ] } ],
  "wire":    [ { "name": …, "stream": …, "commands": [ … ], "invalid": n } ],
  "build":   [ … ], "encode": [ … ], "decode": [ … ], "scan": [ … ],
  "detect":  [ … ] }
```

Each vector starts on a fresh host. A vector with `"requires"` applies only
to a host that has what it names, and others skip it: `"passthrough"`, a
host that reports `passthrough` (SPEC §4, §9.3); `"hover"`, a host that
lists `hover` in `events` (§9.4); `"scroll"`, a host that reports `scroll`
(§4, §5.3); `"touch"`, a host that takes touch (SPEC §9.1, §16). A list
names several, all required. Its steps come in five kinds.

**Send** `{ "send": {control}, "payload": text?, "reply": …, "events": … }`:
the command goes to the host as the program would send it. It is
base64-encoded and chunked as needed, and the payload is UTF-8.
- `"reply"` absent: replies are not checked.
- `"reply": null`: the command must produce no reply.
- `"reply": {…}`: the first reply (`a=ok` or `a=err`) must match. Every key
  but `code` and `detail` is compared with the reply's control; `code` and
  `detail` with the JSON body of an `a=err`.
- `"events"`: the events the command makes the host send, as for a pointer
  step (below). Some follow the command by a frame or a load (`fit`, SPEC
  §5.2), so a runner waits for them, and then a frame or two more to see
  one too many.

**Inspect** `{ "inspect": [surface, id], "expect": … }`: the host reports the
element as the program wrote it:
- `tag`;
- `attrs`: the attributes, with the program's values (a `cid:` URL stays
  `cid:` whatever the host loads);
- `text`: the text content;
- `children`: the child elements as `[tag, id or null, text]`.

`"expect": null` means there is no such element. Otherwise every key of
`expect` must equal the reported value exactly (keys it leaves out are not
checked).

**Pointer** `{ "pointer": "move" | "down" | "up" | "leave", "s": surface,
"at": …, "keys": [ … ], "events": [ … ] }`: a mouse, as the user would move it (SPEC
§9.1, §16).
- `"move"` puts the pointer on surface `s` at `at`: an element's id, for
  the centre of its box, or `[c, r]`, for the centre of that cell of the
  surface, counted from its top left cell (§9.1). A cell can lie outside
  the window, outside the surface, and over another surface. Moving onto
  another surface `s`, with no button down, takes the pointer off the one
  it was on, as a terminal does: that one is left first (SPEC §9.4).
- `"down"` and `"up"` press and release the primary button where the
  pointer is.
- `"wheel"` turns the wheel where the pointer is, by `"by": [c, r]`, columns
  and rows of the surface (positive: right and down), a cell's pixels each.
  It is one gesture: a runner may send it as several wheel events (a
  browser scrolls no more than a page for one), lets what it scrolls come
  to rest before the step's events are read, and lets the gesture end
  before the next step, so each wheel step is a gesture of its own.
- `"leave"` takes the pointer out of the terminal's window.
- `"keys"`: the modifier keys held during the step (`shift`, `ctrl`, `alt`,
  `meta`); none when absent.
- `"through"`: `true` if the step passes through the surface (SPEC §9.3),
  `false` if the surface gets it. Absent: not checked.
- `"terminal"`, for a wheel: `true` if the gesture went on to the terminal,
  as over the cells beneath (SPEC §9), `false` if it did not (the document
  scrolled, or `overscroll-behavior` stopped it, §5.3). Absent: not
  checked.
- `"events"`: every event (`a=ev`) the step makes the host send, in order,
  and nothing more. Each is compared as a reply is: every key but `detail`
  with the event's control, and `detail`, when present, with its JSON body
  (equal as JSON values; `null` when the event has none). Absent: events
  are not checked.

**Touch** `{ "touch": "down" | "move" | "up", "s": surface, "at": …,
"keys": [ … ], "terminal": …, "events": [ … ] }`: one finger, as the user
would touch the terminal (SPEC §9.1, §16). `"down"` touches surface `s` at
`at`, a cell `[c, r]` as for a pointer step; `"move"` moves the finger to
`at`, in moves of a runner's choosing, along the straight line from where
it was, so it passes the host's tap slop in that line's direction (the
vectors move along a row or a column, so where the finger enters an
element does not depend on those moves); `"up"`
lifts it. `"keys"` are the modifier keys held, as for a pointer step.
`"terminal"`, for a move: `true` if the touch went on to the terminal as a
scroll (SPEC §9), `false` if the surface took it; absent, not checked.
`"events"` as for a pointer step: what the step makes the host send.

**Key** `{ "key": name, "keys": [ … ], "terminal": …, "events": [ … ] }`: a
key pressed and released where the keyboard is (SPEC §10): on the surface
that has it, or else on the terminal. `name` is the key as the DOM's
`KeyboardEvent.key` has it (`"Enter"`, `"Tab"`, `"End"`, `"ArrowDown"`,
`"B"`). `"keys"` are the modifier keys held, as for a pointer step. The host
names the key as SPEC §10.4 does: the modifiers before `name`, Shift left
out before a character. A runner that gives the host keys by name uses that
name; one that presses keys on a terminal gets it from the terminal's
encoding, which, for the keys the vectors press, is the same. `"terminal"`:
`true` if the key reached the program as terminal input (§10.2), `false` if
the surface used it; absent, not checked. `"events"` as for a pointer step.

The documents of pointer steps size their elements in cells
(`--hotty-cell-w`, `--hotty-cell-h`, SPEC §8), and point at centres that lie
well inside a cell, so the cell reported is the same on every host. Wheels
and keys scroll a document to an end, or bring an element into view where
any alignment ends at the same offset, never by a distance: how far a
wheel's notch or an arrow key moves differs between hosts.

A host never compresses what it sends (SPEC §3.3): a runner checks that no
reply or event it reads carries `o`.

**Wire vectors** check the envelope alone. The `stream` (JSON-escaped bytes)
must decode into `commands`: listed control keys equal, `m` and `o` never
present, and the payload is UTF-8 text. It must also report `invalid`
malformed or interrupted commands.

The vectors check the document, the events and the wire, not pixels (§5.3:
pixels may differ between hosts).

## The SDK sections

They check an SDK's wire layer (SDK.md §3). Names in them are canonical, in
snake case (SDK.md Appendix A): a runner maps `set_text`, `keep_cursor` and
`fit_rows` to its own. Strings are the UTF-8 of the JSON string. `null`
means absent: Go's zero value, Python's `None`. A vector with `"requires"`
applies to an SDK that implements what it names; a runner declares what it
implements, and skips the rest:

| `requires` | what it names |
| --- | --- |
| `place.hover` | `Placement.Hover` (`v=1`) |
| `event.hover` | `Event.Hover()` |
| `caps.passthrough`, `caps.version`, `caps.scroll` | those fields of `Caps` |
| `doc.scroll` | `Doc`'s `Scroll` option (`scroll=<axes>`) |
| `event.area` | `Event.Area()` |
| `caps.lenient` | a capability field of an unexpected type is ignored (SDK.md §2.7) |
| `caps.drag-kinds` | `Sends` answers for `dragstart` and `dragend` as for `drag` (SPEC §4) |
| `options.unordered` | a `q` given wins over the `q` that `n` implies, whatever their order |
| `decode.abort-count` | a malformed message that aborts a chunked one counts twice (SPEC §3.7) |
| `decode.unterminated` | `Feed` takes a sequence without its terminator |
| `scanner.da1` | the Scanner's `da1` segments |
| `graphemes` | text is split into grapheme clusters (UAX #29), not code points (SDK.md §4.6) |

**Build** `{ "build": builder, "args": {…}, "options": {…}?, "out": [ … ] }`:
the runner calls the builder with `args`, and with the reply options `n`
and `q`, `detached`, `scroll` and `late` from `options`, which have no
order. `sync` takes `args.commands`, each a `{ "build", "args", "options" }`
of its own. The output, split into raw bytes and HOTTY sequences, must be
`out`:
- `{ "raw": text }`: bytes that are not HOTTY's, such as `PlaceAt`'s cursor
  moves, `Query`'s DA1 and `Sync`'s brackets;
- `{ "cmd": { "control": {…}, "payload": text? } }`: one command, decoded.
  Its control has exactly these keys (`m` and `o` never), and its payload is
  this text, empty when absent.

**Encode** `{ "control": [[key, value], …], "payload": text | "payload_b64":
…, "bytes"?: text, "chunks"?: [ { "control": text, "len": n } ] }`: the
runner calls `Encode` with the control in that order. With `bytes`, the
output must be exactly that: these are payloads that cannot be compressed,
under 256 bytes or random. With `chunks`, it is split into sequences, and
each one's control (between `ESC ] 7279 ;` and `;`) and base64 length must
match. Every case must also decode back to the payload, with the control's
keys in order, but `m` and `o`, which are Encode's (SDK.md §3.3).

**Decode** `{ "seqs": [ text, … ], "results": [ … ], "invalid": n,
"messages": [ … ] }`: each sequence goes to one Decoder's `Feed`, in order.
`results` are its results (`not_hotty`, `partial`, `complete`, `invalid`),
and `invalid` its count after the last. `messages` are the complete ones,
in order:
- `control`: exactly these keys and values;
- `reply`: `Reply`'s fields (`ok`, `re`, `n`, `surface`, `cols`, `rows`,
  `code`, `detail`);
- `event`: `Event`'s fields and accessors (`surface`, `kind`, `target`,
  `value`, `checked`, `fields`, `link` with `href` and `url`, `size` with
  `w` and `h`, `fit_rows`, `drag` with `c`, `r` and `keys`, `hover` with
  `c`, `r` and `out`);
- `caps`: `Caps`'s fields, and its answers: `supports` and `sends` map an
  argument to the answer, `drags`, `hovers`, `light`, `cell_css` with `w`
  and `h`.

Only the keys listed are checked. Numbers compare as numbers.

**Scan** `{ "stream": text, "segments": [ … ], "held"?: text, "flush"?: [
… ], "invalid"?: n }`: the stream goes to a Scanner, which looks for DA1
answers only when the vector requires `scanner.da1`. The runner feeds it
whole, cut in two at every offset (or, in a long stream, at every offset
near its ends and at a stride between), and a byte at a time; each time,
the segments must be `segments` (adjacent `pass` segments merged), what it
holds after the stream `held` (none when absent), what `Flush` returns
`flush` (none when absent), and its count of dropped sequences `invalid`
(0 when absent). A segment is `{ "pass": text }`, `{ "osc": text }` or `{
"da1": text }`.

**Keys** checks key names (SPEC §10.4, SDK.md §3.10), in two forms:
- `{ "input": text, "keys": [ … ] }`: `DecodeKeys(input)` must return
  `keys`, one entry for each key, `null` for input that is no key;
- `{ "key": text, "canon": text | null }`: `ParseKey(key)` must return
  `canon`, `null` when the name does not parse.

**Keymap** checks keymaps (SPEC §10.2, SDK.md §3.10), in three forms:
- `{ "parse": text, "format": text }`: `ParseKeymap(parse).Format()` must be
  `format`; with `"terminal_keys": true` and no `parse`, `TerminalKeys`
  formatted must be `format`;
- `{ "multiline": bool, "terminal_keys"?: true, "keys": [ … ], "lookup": {
  key: action | null } }`: `Resolve(multiline, …)` with `TerminalKeys`
  first when `terminal_keys` is true, then each of `keys`. `Lookup` of each
  key of `lookup` must return its value: an action, `"insert"`, or `null`
  when the key is not the field's;
- `{ "keys": [ … ], "program"?: { key: bool }, "scroll"?: { key: action |
  null } }`: an element's keymap outside a text field, with no default
  keymap: `ParseKeymap` of `keys` joined with a space, the root's first.
  `Program` of each key of `program`, and `Scroll` of each key of
  `scroll`, must return its value, `null` for none.

**Edit** `{ "field": { "value", "caret", "multiline"?, "password"?, "rows"?
}, "steps": [ … ] }`: a Field (SDK.md §4.6) made from `field`, absent keys
false, or 1 for `rows`. Each step is `{ "do": action }` or `{ "type": text
}`, and after it every key the step lists must equal the Field's: `value`,
`caret` (in characters), and `changed`, what `Do` or `Type` returned.
`"requires": ["graphemes"]` marks the vectors whose text has a character of
more than one code point, other than CR LF.

**Detect** `{ "n"?: n, "late"?: true, "steps": [ … ], "caps"?: {…} }`: one
Detector, with the query's number `n` (1 when absent), asking for a late
answer when `late` is true. Each step happens at time `at`, in
milliseconds, and is one of `start`, `da1`, `osc` (a sequence, decoded, and
given to `Reply`), `tick` and `end`. After each, every key the step lists
must equal the Detector's: `took` (what `DA1` or `Reply` returned), `state`
(`detecting`, `native`, `text`), `decided`, `done`, and `deadline` (`null`
when there is none). `caps` is checked against the capabilities at the
end.
