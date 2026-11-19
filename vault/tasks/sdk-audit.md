# SDK audit

What SDK.md says and an SDK doesn't do yet. The maintainer, 2026-11-19:
SDK.md is kept current as items are added, and every SDK is audited
against it later, in one pass. Nothing here is scheduled.

- **`Plain`, an option of `Doc`** (SDK.md §3.3, §3.4.2, Appendix A;
  2026-11-19). It sends a document uncompressed. plx asked for it for its
  in-process cells documents, which were compressed only to be inflated
  again (about 550 KB and 14% of a draw's CPU, from hotty-surf's
  cells-perf spike).
  - hotty-go: has it (`hotty.Plain()`).
  - hotty-ts, hotty-lua, hotty-rs: not yet. Where an SDK never compresses,
    the option is accepted and does nothing.
