# CTTR NX (working title)

An unofficial, non-commercial fan project: a native Nintendo Switch port of
Crash Tag Team Racing (GameCube, 2005), built by statically recompiling the
game's own code and running it on open source runtimes. Nothing here is
affiliated with or endorsed by the game's rights holders, and no game data
is distributed. Playing requires a disc image dumped from your own copy of
the North American GameCube release (G9RE7D, Rev 0).

## Status

Two routes exist, and both are documented in this repo.

**PC playable (ModernGekko route).** The game translated with DolRecomp
runs on a Dolphin-derived runtime: menus, cutscenes, saving, gamepad input,
and races all work at the game's original unlocked frame rate. Performance
in the opening areas is strong; performance in the hub and later areas is
an open investigation (see docs/HANDOFF-ADDENDUM-2026-11-01.md).

**Boot campaign (WiiCompiled route).** The whole game binary translates
cleanly (25,276 functions) and the runtime now boots the game on PC:
system init, disc, video, and audio init all complete, and the game
presents frames behind the runtime's startup cover. The current open
problem is the game's internal file loader, which stalls in the boot
window so level data never streams in. The full campaign log, batch by
batch, is docs/WIICOMPILED-SPIKE.md.

There is no Switch build yet. The Horizon phase is scoped in
docs/HORIZON-SCOPE.md: source audit, cross-compile probe, a null-backend
boot on real hardware as the kill-gate, then the renderer decision.

An earlier plan to build on the community matching decompilation was set
aside on Oct 29, 2026: at 6.85% matched it is years from port-ready. The
decomp remains a reference and a background watch (docs/DECOMP-WATCH.md).

## Layout

- `docs/PHASE-0.md` Disc verification: the G9RE7D dump and the decomp
  build check that proved it (passed Oct 29, 2026).
- `docs/CHASSIS-MAP.md` What the Strikers Switch chassis is made of.
  Written for the earlier decomp route; kept as background.
- `docs/CHASSIS-DEEP-DIVE-2026-11-02.md` Source-level comparison of the
  candidate runtimes (purpose-built AOT, ModernGekko, WiiCompiled).
- `docs/WIICOMPILED-SPIKE.md` The WiiCompiled translation spike and the
  ongoing boot campaign, batch by batch.
- `docs/HANDOFF-ADDENDUM-2026-11-01.md` ModernGekko performance session:
  measurements and the shutdown-counter findings.
- `docs/HORIZON-SCOPE.md` The Switch phase: milestones and kill-gates.
- `docs/ICON-SPIKE.md` Plan for swapping the game's button prompt
  textures for Switch icons via texture replacement.
- `docs/TOOLING-REFERENCES.md` Notes on the tooling this project leans on.
- `docs/DECOMP-WATCH.md` Snapshot of upstream decomp state, kept as a
  background watch.
- `port/` The WiiCompiled spike project: the translator project file and
  the function map converted from the decomp's symbols.
- `tools/` The campaign's own tooling: patch scripts for the runtime
  tree, memory snapshot forensics, a process sampler, and a performance
  logger.
- `research/` Local reference clones (Strikers port, cttr decomp). Not
  part of the project source; never committed anywhere.

## Legal and provenance

- This project is not affiliated with, endorsed by, or connected to Radical
  Entertainment, Vivendi, Sierra, Activision, or Nintendo. Crash Bandicoot
  and Crash Tag Team Racing are trademarks of their respective rights
  holders; all game IP belongs to them, all rights reserved.
- No game data is distributed here. Running any build requires a disc image
  dumped from your own copy of the North American GameCube release
  (G9RE7D, Rev 0).
- The recompilation tools and runtimes are third-party open source projects
  (DolRecomp and ModernGekko by ExpansionPak and contributors, building on
  Dolphin; the WiiCompiled runtime by JosiahG and contributors); their
  licences travel with their code.
- The upstream decompilation (bluisblu/cttr) is CC0-1.0 and is used here as
  reference only. Per that project's stated policy, nothing from this
  project is contributed back upstream, and no AI-assisted work is
  submitted there. AI assistance used in this project is disclosed here, in
  this repository, where it belongs.
- Any licence granted here covers this project's own code only, never game
  data or third-party material.

## Credits

- DolRecomp and ModernGekko: ExpansionPak and contributors, building on
  the Dolphin emulator (Dolphin Team).
- WiiCompiled runtime and the Aurora graphics library: JosiahG and
  contributors.
- Matching decompilation reference: the bluisblu/cttr project (CC0-1.0).
- Crash Tag Team Racing: Radical Entertainment. Crash Bandicoot is a
  trademark of Activision.

## AI assistance

AI assistance: This project is developed with help from AI coding tools.
All code is reviewed and tested by the maintainer before it is committed.
