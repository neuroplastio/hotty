# For the SDLC Agent: hotty-surf's pipeline, from the a2ui-exit finish (2026-11-10)

Written by hotty Agent at the maintainer's request, who will adjust the
pipeline from this. It comes from finishing the last two legs of
hotty-surf's a2ui-exit plan (L7 tree, L12 surfmd) and moving the gate's
Blitz from 0.7.0 to 0.7.3. The numbers are from that one session.

## What cost time

- **`make check` is all or nothing.** The L7 merge took about 25 minutes of
  it (fmt, tidy, gen, vet, lint, test, look-test, TinyGo wasm for 13
  packages, stack, gate, legible). For L12 (surfmd: its own module, no CSS,
  no stories) I ran that module's `go vet` and `go test` and the root
  packages' tests, and merged. Nothing was lost.
- **`make gate` is 2,400 cases, about 6 minutes.** One story takes 2
  seconds with `GATE_FLAGS="--only <story>"`, or `node scripts/gate/gate.cjs
  --only <case>` with `--hotty`/`--fonts` set to another Blitz. That is how
  a case was rendered on 0.7.0 and on 0.7.3 side by side.
- **The baseline retake is a second full gate run** (`make gate-baseline`),
  so a gate that needed retaking costs 12 minutes. It was started before
  the maintainer had judged the images, and had to be thrown away.

## What failed or misled

- **An empty `scripts/gate/node_modules` passes the Makefile's prerequisite**
  (a directory exists, so make does not run `npm ci`) and then
  `font-scale.test.cjs` dies on "Cannot find module 'playwright'". Main's
  was empty; the other worktree had it. The target should test for
  `node_modules/playwright`, not the directory.
- **The gate's scores did not show the bug.** Blitz 0.7.2 scrolled a
  content-sized textarea to its end; the 30 `field-rows` cases went from
  about 590 to 5,000–7,000, which "30 to look at" reports as worse, not as
  what is wrong. The maintainer found it by looking at one case before and
  after. The fix restored exactly the old score (585.9).
- **A detached check's only end marker is the `exit N` line** the wrapper
  appends (`sh -c '… ; echo "exit $?" >> log'`). Without it, "no output
  yet" and "finished" look the same. Every long step should write one.
- **The shared check lock is held across a whole `make check`.** Anything
  queued behind it (the gate, a baseline) waits for all of it.
- **Killing a stray run is blocked** for the agent (the classifier refused
  `pkill`), so a wrongly started baseline ran to its end. A `make` target
  or a lock-file-based `cancel` would let an agent stop its own runs.

## What worked, to keep

- Looking at before/after images of one case, chosen by the biggest score
  change, rather than reading the report. The maintainer decides in a few
  seconds; the agent reads no screenshots.
- A per-leg brief and a `ready <branch> <head>` message to the coordinator.
- Rebase of the leg's branch in its own worktree, merge in main
  with `--ff-only` after the check.

## Proposals, for the SDLC Agent to weigh

1. **Choose the checks by what changed.** A change that touches only a
   sub-module's Go (surfmd, surftea) needs that module's tests, vet and
   tidy; one that touches CSS, `vocab.go` or stories needs the gate for
   those stories (`--only`); only a Blitz or font change needs the whole
   gate. `make check` stays the full one, run before a push.
2. **Gate by story, report by story.** Print the changed stories (grouped
   by name, not 30 case lines) and write the before/after pair for the
   worst case of each, so the maintainer's look is one command and the
   agent does not open images.
3. **Render the previous Blitz on demand** (`make gate-compare
   CASE=… OLD=blitz-0.7.0`), so the "before" is not rebuilt by hand.
4. **Retake the baseline only after a look.** `gate-baseline` should refuse
   to run until the report it follows has been seen (a file the look
   writes), and it should reuse that run's results rather than render the
   2,400 cases again.
5. **Check `node_modules/playwright`**, as above.
6. **Cap and cancel.** Give `make` a `stop` target for the runs under
   `check.lock` (they are in a `systemd-run` scope each).
7. **A Blitz bump is its own leg.** It carried a hotty-blitz release
   (0.7.3, mods/blitz 0055) and notes in `vault/knowledge/blitz-gaps.md`,
   `css-subset.md` and the plan. A checklist for it: install the build next
   to the old one, point `make.mk` at it, `--only` the stories that use
   what changed, look, then the full gate.

## State left behind

hotty-surf v0.5.0, surfmd/v0.5.0 and surftea/v0.5.0 and hotty-blitz v0.7.3
are pushed. `~/.config/hotty-surf/make.mk` (per machine) points the gate at
`blitz-0.7.3`. The baseline did not change; `make gate` says "as known".
