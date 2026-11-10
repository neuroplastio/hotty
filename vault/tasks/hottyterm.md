# hottyterm: the terminal's own work

Features of hottyterm, and its bugs against the spec, that change no spec
item. Each is done on hottyterm's main when the maintainer dispatches it.

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

- [ ] **HT-02** hottyterm updates itself
      status: recorded, not dispatched | added: 2026-10-31
      problem: a new hottyterm reaches the user only when they run their
      package manager. plx updates in place, and the maintainer, after
      trying Rex (gov R-25), listed "hottyterm autoupdate feature" among
      the things needed for a better experience.
      shape:
      - hottyterm checks for a newer release of its channel (dev or
        stable), and says so in a notice that stays until the user acts.
      - It updates the way it was installed: Homebrew and the AUR own
        their files, so there it runs or offers their upgrade; a
        hottyterm installed from a release archive replaces itself.
      - A relaunch restores what plx holds: panes under plx survive it,
        a bare shell does not, and the notice says which.
      open:
      - whether it checks by default, and how often;
      - whether the package-manager route runs the upgrade or only
        names the command;
      - the notice: GTK's, or a surface of hottyterm's own.

- [x] **HT-03** `--hotty-bg` keeps the configured background after a program sets OSC 11
      status: fixed for a program's OSC 4, 10 and 11 (hottyterm patch 0055, 2026-11-10, local until hottyterm's next commit); a theme change in the config is not covered | added: 2026-11-07
      found: by plx (plx-look, 2026-11-07).
      - A program sets the terminal's background with OSC 11 (#191919
        there). hottyterm draws the cells on the new background.
      - A surface keeps `--hotty-bg` at the configured one (#282C34).
      - So a document that fills with `var(--hotty-bg)` shows two
        backgrounds side by side.
      - plx works around it on its side.
      spec: §8 lists `--hotty-bg` as "the terminal's background", and says
      "When the terminal's theme or font changes, the host updates the
      stylesheet and draws every surface again". It doesn't name OSC 10,
      11 or 4. But once a program sets OSC 11, the terminal draws its cells
      on that colour, so that colour is the terminal's background. Read as
      written, this is a bug in hottyterm against 0.7, not a spec question.
      A sentence naming the colours a program sets is a wording to weigh
      for 0.8 (`tasks/0.8.md`, To consider).
      cause (read from the code at hottyterm 07080c8, not reproduced here):
      - hotty.zig's `config()` reads the terminal's current colours
        (`t.colors.background.get()`, where OSC 11's value wins over the
        configured one).
      - But hotty.zig calls `hotty_host_configure` only when the host
        starts (`ensureHost`) and on a resize of the window or the cells
        (`resized`).
      - The stream handler's `colorOperation` (OSC 4, 10 and 11, set and
        reset) and Termio's `changeConfig` (a new theme in the config)
        change the colours without telling hotty. So the host keeps its
        stylesheet until the next resize.
      - hotty-blitz is right as it is: `hotty_host_configure` restyles
        every surface, the open menu included, and sends `caps` when
        `scheme` changed.
      scope: everything §8 derives from the colours goes stale the same
      way, after a program's colour change and after a theme change in
      the config:
      - `--hotty-fg`, the 16 `--hotty-ansi-*` and `--hotty-accent`;
      - `color-scheme` and `prefers-color-scheme`;
      - `caps`' `scheme`.
      done 2026-11-10 (the maintainer took it, via margin-surf's report):
      - `Hotty.recolored` in hotty.zig, called at the top of `flush`: when
        the foreground, background or palette differ from the ones the
        host was last configured with, it runs `resized` (configure,
        rewindow, repaint). Same colours again cost nothing; it is
        coalesced by the batch of output. No upstream lines.
      - Checked with `scripts/osc11-check.py` on a private display: after
        a second OSC 11 the old build's surface stayed #191919 beside
        cells at #2A1A1A, and the new one's surface was #2A1A1A. No
        automated test (the host is a C ABI; the check is the script).
      - Left: a theme change in the config (`Termio.changeConfig`) with no
        output after it still waits for the next batch of output.
      the plan was:
      - In hotty.zig: after each of those changes, a hook gives the host
        the current colours (`hotty_host_configure`, which does nothing
        when nothing changed) and the surfaces are drawn again. It is
        coalesced, so a program that sets colours often doesn't restyle
        every surface on each one.
      - A test: OSC 11, then the host stylesheet's `--hotty-bg`.
      - hotty-blitz needs no change. The xterm addon is not checked.
