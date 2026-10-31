# hottyterm: the terminal's own work

Features of hottyterm that change no spec item. Each is done on hottyterm's
main when the maintainer dispatches it.

Item template: as `tasks/0.4.md`.

- [ ] **HT-01** A document's remote resources ask the user, rather than fail silently
      status: recorded, not dispatched (the maintainer, 2026-10-31: "Just record, do not dispatch") | added: 2026-10-31
      problem: hottyterm's half of the network policy (SPEC §7.2,
      `hotty-net =` in its config) starts empty, as §7.2 says a terminal
      should. A document that asks for a remote image, font or stylesheet
      with `<meta name="hotty-network">` gets nothing, and nothing says
      why. The maintainer: "Currently, it just not renders remote
      resources and the user doesn't have any idea what's going on."
      ask, in the maintainer's words: "when hotty requests loading resource
      from the domain - a confirmation dialog with "allow <domain> for this
      session" - keeps permission in memory, "allow <domain> always" -
      saves to the config, "allow all https resources" - saves to the
      config."
      shape:
      - The three answers are grants to §7.2's host half: the origin in
        memory for the session, the origin in `hotty-net`, or `https:` in
        `hotty-net`.
      - Only a fetch that the document's half allows and the host's half
        refuses asks. A document that asks for nothing asks the user
        nothing.
      - Until the answer, the reference fails as a missing resource does.
        After a grant it arrives late (§7.1), as a fetch after layout does
        now. Programs see the new grant in `net` (SPEC §4).
      open:
      - per directive (`img-src`, `font-src`, ...) or all four at once;
      - one dialog per origin, or one per document that lists them;
      - whether a refusal is remembered for the session;
      - the dialog: GTK's, or a surface of hottyterm's own.
