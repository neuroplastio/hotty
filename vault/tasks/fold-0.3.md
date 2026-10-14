# HOTTY 0.3: the fold

What a pass over SPEC 0.2 found for bandwidth and protocol complexity
(2026-10-14), to fold into the spec. Folding them makes HOTTY 0.3 (the
maintainer, 2026-10-14). The list grows until folding starts; nothing is
folded yet. The measurements behind it are in
[`../knowledge/wire-sizes.md`](../knowledge/wire-sizes.md).

Item template:

```
- [ ] **FOLD-NN** title
      status: proposed | added: YYYY-MM-DD
      problem: …
      proposal: …
      gain: … | cost: …
```

Statuses: `proposed`, `accepted`, `rejected`, `folded`. An item marked
`needs: maintainer` is a scope decision, not the agent's to make.

When folding starts, each item lands in SPEC.md, SDK.md and the vectors
together (AGENTS.md), and the stack moves to 0.3 together: the three SDKs,
the Python client, hotty-blitz, hottyterm, xterm-addon-hotty and their
consumers.

## Wire (0.3)

- [ ] **FOLD-01** Deltas are one list of ops
      status: proposed | added: 2026-10-14
      problem: every delta is a message of its own, with an envelope and a
      control: 49 B to set `--p: 42`. A frame of 15 small deltas is 755 B,
      and zlib cannot see across messages.
      proposal: `a=delta:s=<name>` carries one msgpack map,
      `{"ops": [{"op": str, "t": str, "k": str, "v": str|bin}, …]}`, applied
      as one unit. The control keys `op`, `t` and `k` go.
      gain: 15 ops 755 → 184 B, 50 ops 2,540 → 356 B. One surface's batch
      is atomic without mode 2026. Targets travel as UTF-8, so a delta can
      address `café` (events still report it as `caf_`, §3.2).
      cost: one op is 64 B instead of 49. Every delta builder in the SDKs
      and the Python client; hosts decode a program's msgpack, as they do
      for `a=menu` today; the `build`, `encode` and delta vectors.
      notes: ops are maps keyed by name, as every HOTTY body is. Positional
      tuples would make one op 52 B, but need an exception to gov P-3:
      not proposed. Deltas move to msgpack, so gov hears of it under P-3
      when folding starts.

- [ ] **FOLD-02** Subscriptions stay on the surface
      status: proposed | added: 2026-10-14
      problem: `p`, `f` and `v` end with every new placement, and the spec
      says so for each flag, then again for hover (§9.4) and view (§9.5). A
      program that places its surfaces every frame, as Appendix B expects,
      sends them every frame, and loses them the one time it forgets.
      proposal: they hold until the program sets them to `0`; `z`, the
      window and `C` stay the placement's. `view` takes the same lifetime.
      One table in §9 replaces the scattered rules: for each event, how it
      is opted in (always, `data-on`, or a surface flag), how long that
      lasts, how often it is sent (per change, per frame, at rest), and
      that a detached surface sends none.
      gain: fewer bytes per placement, and an SDK can skip a placement that
      changes nothing. About six lifetime paragraphs become one table.
      notes: the flags could also be named as the events they ask for
      (`ev=press,hover,fit`), which retires "`v`, because `h` is taken".
      Optional.

- [ ] **FOLD-03** What 0.2 added becomes 0.3's baseline
      status: proposed | added: 2026-10-14
      problem: each feature added within 0.2 got a flag of its own
      (`passthrough`, `scroll`, `steps`, `drop`, `count`, `menu`), beside the
      `ops` and `events` lists, whose absence means opposite things: no
      `ops` is every op, no `events` is no drag, hover or view. Every SDK
      carries that split (SDK.md §3.9).
      proposal: a 0.3 host does every op, every event and `scroll`, `steps`
      and `drop`; `ops`, `events` and those flags go. One list,
      `features: [str]`, names what a host may lack, with the names the
      conformance markers use; absent means none. In 0.3 it holds
      `passthrough`, `hover` and `count`, and later additions.
      gain: one mechanism. The SDKs' `Supports`, `Sends`, `Drags`, `Hovers`,
      `Views` and the flags become one `Has(name)`.
      cost: checked 2026-10-14, both hosts already do every op and event
      but `hover`, and `scroll`, `steps` and `drop`. xterm-addon-hotty sends
      no `hover` and reports no `passthrough`; hotty-blitz reports
      `passthrough` and `count` only when its embedder supplies them. Those
      three stay features unless the hosts catch up before the fold.

- [ ] **FOLD-04** Geometry without `resize`
      status: proposed | added: 2026-10-14
      problem: the cell is reported in device pixels, beside `scale`. A new
      font sends `resize` to every surface, and the program asks again
      (`a=q`) for the cell. A zoom changes `scale` and the program hears
      nothing (§5.3), so a program that works out one device pixel from it,
      such as a multiplexer snapping its decorations to device pixels, is
      wrong after every zoom. No consumer checked acts on `resize`.
      proposal: `cell` is in CSS pixels. A new font sends `caps` with the
      new `cell`. The host stylesheet gains `--hotty-px`, one device pixel
      in CSS pixels, kept current through zooms as the stylesheet's other
      properties are. `resize` goes. Whether `scale` stays, as a hint for
      the resolution of images, is decided when folding.
      gain: one event kind and a round trip fewer; device-pixel snapping is
      CSS, and right after a zoom.

- [ ] **FOLD-05** Event details
      status: proposed | added: 2026-10-14
      problem and proposal, three parts:
      - `submit` carries the form's names as the detail's own keys
        (`{str: str}`). Two checkboxes with one name lose a value, since a
        map holds a key once, and SDKs read the detail by kind so that a
        field named `value` stays a field. It becomes
        `{"fields": [[name, value], …]}`.
      - Drags spell the modifiers `"ctrl"`, `"shift"`, …, where key names
        spell `Control`, `Shift` (§10.4). Clicks and presses carry none, so
        Shift+click cannot extend a selection. One int, `mods`, with §10.4's
        bits (1 Shift, 2 Alt, 4 Control, 8 Meta) and left out at 0, goes on
        `click`, `press` and the drags, in place of `keys`.
      - `t` is absent, not empty, where no element is meant (`fit`, `view`,
        `blur`, `hover` when the pointer leaves).

- [ ] **FOLD-06** Envelope trims
      status: proposed | added: 2026-10-14
      - `q` defaults to 1 (errors only), and `n` implies 0. That is the
        rule SDK.md §3.4.2 already follows, moved onto the wire: most
        commands then carry no `q`, and a program that forgets one does not
        fill its input with replies.
      - Continuation chunks carry only `m`. Their `q` does nothing: replies
        are per message.

- [ ] **FOLD-07** Split the document
      status: proposed | added: 2026-10-14
      problem: §10 is 576 of SPEC's 2,482 lines (23%), and most of it is
      how a host behaves (text fields' keymaps and actions, key names from
      a terminal's bytes), not the wire. Appendix B (365 lines) grows an
      entry per feature.
      proposal: SPEC.md keeps the envelope, surfaces, deltas, resources,
      events and security. A normative companion takes keyboard routing,
      text fields and key names. Appendix B keeps one entry per mechanism.
      Prose only; folded last.

## Scope decisions

- [ ] **FOLD-08** The features for programs in the cells leave HOTTY's core
      status: proposed | needs: maintainer | added: 2026-10-14
      problem: `a=edit`, the `command` event, `a=menu` and the `menu`
      capability serve a program drawing in the cells, not a surface: the
      terminal using HOTTY's envelope as a side channel.
      proposal: a companion spec on the same envelope; or drop `a=menu`,
      since a program can already show its which-key menu as a surface at a
      higher `z`, and keep `a=edit` in the companion. `caps` stays in the
      core, for `mod` and `cell` (FOLD-04).
      consumers: `a=edit` only in hotty-a2ui's storybook; `a=menu` none.

- [ ] **FOLD-09** Key sequences are resolved by the program
      status: proposed | needs: maintainer | added: 2026-10-14
      problem: §10.5 puts a sequence engine in the host: `data-key`, groups,
      the nearest-to-focus rule, `<leader>`, a timeout, `keys` in the
      capabilities, and a which-key menu the host draws. Appendix B's main
      reason is a race: after a leader, the next key can reach a focused
      text field before the program can react.
      proposal: one keymap action, `prefix`. The key reaches the program,
      and so does every key after it, whatever is focused, until the
      program sends `a=focus` or the surface loses the keyboard. The program
      resolves sequences with myelin, as it does in its cells, labels them
      from the document it wrote, and shows its menu as a surface.
      gain: `data-key`, `keys`, menus drawn by the host and the vectors'
      `keys` marker go.
      cost: the menu shows a round trip later, which which-key's own pause
      hides; the action it leads to needed the program anyway. It reverses
      what shipped on 2026-10-14 (hottyterm 26.10.14-dev.740d7f8,
      xterm-addon-hotty 0.1.0-next.17). No consumer uses `data-key` yet, so
      it is cheapest now.

## SDKs (any time, not tied to 0.3)

- [ ] **FOLD-10** Compress at zlib's default level
      status: proposed | added: 2026-10-14
      hotty-go compresses at `BestSpeed`, the Python client at level 1.
      hotty-a2ui's `kit.css` is 26,708 B of base64 at level 1 and 17,452 B
      at level 6, 35% less, for about a millisecond. SDK.md §3.3 can name
      the level; the `encode` vectors already leave compression out.

- [ ] **FOLD-11** Diff before morphing
      status: proposed | added: 2026-10-14
      Morphing the whole tree sends the whole tree: 930 B for one changed
      cell of `corpus/04-table.html`, where a `text` delta is 56 B. SDK.md
      says to diff first (hotty-a2ui's `rendition/html/diff.go` does), with
      the whole-tree morph as the fallback that keeps the user's state, and
      to send a stylesheet shared by documents once, as a resource, rather
      than in each document.

## Considered, not proposed

- **One zlib stream across messages:** a dropped or aborted message (§3.4,
  §3.7) would corrupt everything after it.
- **Z85 in place of base64:** 8% smaller, but its alphabet has `:` and `=`,
  and every SDK would need it where base64 is built in.
- **One-letter actions and keys:** FOLD-01 already spreads the control
  over a frame's ops.
- **Resources by hash, cached across sessions:** one program could probe
  what another sent, and a miss costs a round trip. Worth another look for
  slow links (NEIO-12).
- **zlib preset dictionaries:** xterm-addon-hotty inflates with
  `DecompressionStream`, which takes none, and FOLD-11 gets most of the gain.
- **`r=auto`'s rows from `fit` alone:** a placement out of view hears no
  `fit` until it is drawn, and the reply is at once. The reply stays.

## Kept on purpose

Morph's rules, detach, presses with Alt, passthrough, touch drags and the
text fields' actions: each is opted into or local, and is what
multiplexers, touch and two hosts that share no code need. `reveal` is an
odd delta, since it changes no node, but it is cheap.
