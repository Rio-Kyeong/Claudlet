# Repository Guidelines

This project keeps one set of guidelines, in **[CONTRIBUTING.md](CONTRIBUTING.md)**
(Korean: [CONTRIBUTING.ko.md](CONTRIBUTING.ko.md)) — dev setup, running tests,
code style, branch model, and commit conventions. Read that before changing
anything.

This file exists because coding agents look for `AGENTS.md` by convention. It is
deliberately a pointer rather than a copy: two documents describing the same
rules drift apart, and then contributors get contradictory guidance.

Two things worth knowing before you touch the code, both expanded in
CONTRIBUTING.md:

- **Test behavior, not interaction.** Push logic into pure functions and test
  input→output; drive the pet through its socket harness and `snapshot()`.
  Asserting that a particular private method was called breaks on renames that
  change nothing.
- **Platform code can't run here.** KWin/D-Bus, Win32, and Quartz paths are
  verified on real hardware, so keep them thin wrappers over tested pure logic
  rather than mocking them into a green suite.
