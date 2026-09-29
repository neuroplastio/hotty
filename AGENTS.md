# For agents

This repository is the HOTTY protocol: `SPEC.md`, its conformance vectors, and
the reference material around them. Implementations live elsewhere
(hotty-blitz, xterm-addon-hotty).

- **The spec is normative, and the vectors are the spec as data.** A change
  to one without the other is incomplete. Run both implementations' vector
  runners before calling a change done.
- **Do not grow the wire for one implementation.** Anything only one host
  needs is an extension under a vendor prefix (§15), in that host's
  repository.
- **Breaking changes need a new version** (§15). Say in the commit message
  which sections changed and why.
- **No implementation code here** beyond test tooling: the reference client
  and the example programs.
- The example art from Bub-n-Bros is fetched, never committed.
