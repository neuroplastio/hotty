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

Each vector starts on a fresh host. Its steps come in two kinds.

**Send** `{ "send": {control}, "payload": text?, "reply": … }`: the command
goes to the host as the program would send it. It is base64-encoded and
chunked as needed, and the payload is UTF-8.
- `"reply"` absent: replies are not checked.
- `"reply": null`: the command must produce no reply.
- `"reply": {…}`: the first reply must match. Every key but `code` and
  `detail` is compared with the reply's control; `code` and `detail` with
  the JSON body of an `a=err`.

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

**Wire vectors** check the envelope alone. The `stream` (JSON-escaped bytes)
must decode into `commands`: listed control keys equal, `m` and `o` never
present, and the payload is UTF-8 text. It must also report `invalid`
malformed or interrupted commands.

The vectors check the document and the wire, not pixels (§9: pixels may
differ between hosts).
