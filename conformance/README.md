# HOTTY conformance vectors

`vectors.json` is what a host must do, as data. Two implementations that share
no code run it:
- hotty-blitz: `crates/hotty-blitz/tests/conformance.rs`;
- xterm-addon-hotty: `tests/e2e/conformance.spec.ts` and
  `tests/unit/conformance.test.ts`.

A disagreement is either a bug or a line of `SPEC.md` that says too
little.

## Format

```
{ "version": "0.1",
  "vectors": [ { "name": …, "steps": [ step, … ] } ],
  "wire":    [ { "name": …, "stream": …, "commands": [ … ], "invalid": n } ] }
```

Each vector starts on a fresh host. A vector with `"requires":
"passthrough"` applies only to a host that reports `passthrough` (SPEC §4,
§9.3); others skip it. Its steps come in three kinds.

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

**Pointer** `{ "pointer": "move" | "down" | "up", "s": surface, "at": …,
"keys": [ … ], "events": [ … ] }`: a mouse, as the user would move it (SPEC
§9.1, §16).
- `"move"` puts the pointer on surface `s` at `at`: an element's id, for
  the centre of its box, or `[c, r]`, for the centre of that cell of the
  surface, counted from its top left cell (§9.1). A cell can lie outside
  the window, outside the surface, and over another surface.
- `"down"` and `"up"` press and release the primary button where the
  pointer is.
- `"keys"`: the modifier keys held during the step (`shift`, `ctrl`, `alt`,
  `meta`); none when absent.
- `"through"`: `true` if the step passes through the surface (SPEC §9.3),
  `false` if the surface gets it. Absent: not checked.
- `"events"`: every event (`a=ev`) the step makes the host send, in order,
  and nothing more. Each is compared as a reply is: every key but `detail`
  with the event's control, and `detail`, when present, with its JSON body
  (equal as JSON values). Absent: events are not checked.

The documents of pointer steps size their elements in cells
(`--hotty-cell-w`, `--hotty-cell-h`, SPEC §8), and point at centres that lie
well inside a cell, so the cell reported is the same on every host.

**Wire vectors** check the envelope alone. The `stream` (JSON-escaped bytes)
must decode into `commands`: listed control keys equal, `m` and `o` never
present, and the payload is UTF-8 text. It must also report `invalid`
malformed or interrupted commands.

The vectors check the document, the events and the wire, not pixels (§5.3:
pixels may differ between hosts).
