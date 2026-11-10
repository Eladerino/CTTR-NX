# CTTR NX (working title)

An unofficial, non-commercial fan project: a native Nintendo Switch port of
Crash Tag Team Racing (GameCube, 2005), built by statically recompiling the
game's own code and running it on open source runtimes. Nothing here is
affiliated with or endorsed by the game's rights holders, and no game data
is distributed. Playing requires a disc image dumped from your own copy of
the North American GameCube release (G9RE7D, Rev 0).

## Status

The project's one route is the WiiCompiled-to-Switch pipeline:
statically recompile the game's own code with the WiiCompiled
toolchain, prove the game out on the PC runtime, then carry that
build to Switch through the Horizon phase.

**Where the PC build stands.** The whole game binary translates
cleanly (25,276 functions) and boots through system, disc, video and
audio init. The boot loader stall is long solved: the game streams
its archives, plays the attract movie start to finish, and loads the
frontend, which renders. The campaign's two long-standing failure
layers were root-caused in November 2026. A poisoned scheduler
context word is healed at the selection gate (batch 282). The second
layer was the attract movie's own frame copy: a shared GX
descriptor's pixel pointer flips in place to 0x20 mid-run, and
through the runtime's MEM1 window that destination lands on low
memory, so the copy sprayed frame pixels over the OS block (batch
310 corrects the destination at the point of use; the flip's writer
is still unknown and now harmless). The batch-310 build passed two
consecutive full soaks (30 minutes, then ~52 minutes) with the
movie looping.

The current open problem is one step further in, and it is the
active work. Steered past the attract loop with synthetic input,
the game crashes on a frontend menu draw: Sprite objects in the
frontend package's memory are overwritten in place by texture data
during the frontend phase. The loader is proven innocent (batch 311
witness: every load and resolve correct; the objects die
afterwards). Next step is catching the overwriting writer with a
flip-watch on the affected span, with a point-of-use guard in the
frontend Text draw as the fallback. The full campaign log, batch by
batch, is docs/WIICOMPILED-SPIKE.md; the corruption hunt is
consolidated in docs/WRITER-HUNT.md, and the frontend crash record
is docs/FRONTEND-CRASH-2026-11-09.md.

**The Switch phase** has not started: there is no Switch build yet.
It is scoped in docs/HORIZON-SCOPE.md: source audit, cross-compile
probe, a null-backend boot on real hardware as the kill-gate, then
the renderer decision (Aurora's deko3d backend is the leading
candidate, with two shipped GameCube ports as evidence).

An earlier ModernGekko/DolRecomp PC route also reached playable; it
is not the project's direction and is kept only as history
(docs/HANDOFF-ADDENDUM-2026-11-01.md).

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
  ongoing campaign, batch by batch, through the November wedge hunt
  and the frontend crash diagnosis.
- `docs/WRITER-HUNT.md` The consolidated record of the corruption
  hunt: the drip, the module-walk storm, the two wedge layers, and
  the Bink frame copy named as the writer.
- `docs/FRONTEND-CRASH-2026-11-09.md` The first input run's crash:
  diagnosis, the batch 311 loader witness, and the dead-Sprite
  census.
- `docs/UPDATER-PREP-2026-11-05.md` CTTR-side prep for the shared
  cross-port self-updater: version source, menu placement, release
  assets, and the file set an update may touch.
- `docs/HANDOFF-ADDENDUM-2026-11-01.md` Historical: the earlier
  ModernGekko route's performance session, measurements and the
  shutdown-counter findings.
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
  Dolphin; the WiiCompiled runtime by patchzyy and contributors); their
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
- WiiCompiled (recompiler and runtime): patchzyy and contributors.
- Aurora graphics library: Luke Street and contributors.
- Product and launcher layer: adapted from JosiahG's NewSuperPaperBros,
  his Super Paper Mario port built on WiiCompiled.
- Matching decompilation reference: the bluisblu/cttr project (CC0-1.0).
- Crash Tag Team Racing: Radical Entertainment. Crash Bandicoot is a
  trademark of Activision.

## AI assistance

AI assistance: This project is developed with help from AI coding tools.
All code is reviewed and tested by the maintainer before it is committed.
