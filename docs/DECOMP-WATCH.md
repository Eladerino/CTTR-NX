# CTTR decomp watch

Snapshot: Oct 29, 2026, from the cloned upstream repo (bluisblu/cttr) and
decomp.dev figures checked the same day.

## Where upstream stands

- Overall: 6.85% of code matched (about 1.4k of ~25k functions), 4.45%
  linked. Pace over the 30 days before Oct 29: +0.47 points. Last push
  Oct 15, 2026.
- Target binary: a single main DOL (config/G9RE7D/config.yml points at
  sys/main.dol only). No REL/overlay modules are configured, which removes
  the multi-image problem that complicates other GameCube projects.
- Symbols are far ahead of code: config/G9RE7D/symbols.txt names 44,980
  symbols. The map of the binary exists; the C++ reconstruction does not yet.

## The split that matters

Counting decompiled C/C++ files in the clone (355 total):

- src/dolphin: 188 files. The GameCube SDK (GX, AX, DVD, CARD, PAD, OS and
  friends). This is most of what has been matched so far.
- src/CTTR: 7 files. The game itself: Controller, Player, Mode, Skin,
  Wheel, BrakeMotif, Differential, plus headers for more (NISManager,
  GameObject, LoadSet, Sound interfaces).
- src/auto: 13 files of auto-split, not yet hand-matched code.
- src/PowerPC_EABI_Support: the Metrowerks runtime/MSL layer.

Translation: the matched percentage is mostly SDK, and the SDK is the part
a port replaces with Aurora-style implementations anyway. The blocking work
for a port is the game and engine code (Radical's Pure3D lineage), which is
barely started. The headline percentage overstates port readiness.

## What "port-ready" means concretely

Phase 2 (the actual port) can start when all of these are true:

1. The decomp links a complete executable from decompiled source (the
   fully linked figure reaches effectively 100%, or the project declares a
   shiftable state where the whole DOL builds from C/C++).
2. src/CTTR and the engine code are substantively decompiled, not just the
   SDK and runtime layers.
3. The build runs against Brandon's own G9RE7D dump in Phase 0, so the
   toolchain and disc version are proven before port work depends on them.

Until then, progress is measured by src/CTTR file growth and the linked
percentage, not the matched headline. tools/decomp-status.sh prints both
from the local clone.
