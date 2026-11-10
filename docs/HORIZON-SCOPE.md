# Horizon scope: porting the ModernGekko runtime to Switch

Written Oct 30, 2026. This is a scoping document, not a schedule. It defines
the first milestones and the cheap kill-gates for the Switch phase of the
CTTR recomp project. The PC spike it builds on is recorded in
~/workspace/cttr-switch-scout/SCOUT-BRIEF.md (spike result, Oct 29 late).

## Where we start (established facts)

- The game side is solved in principle: DolRecomp translated CTTR's G9RE7D
  main.dol with 0 unknown instructions, and the C backend emits portable C,
  so the game module can be recompiled for the Switch's ARM64 chip with no
  new translation work.
- The runtime side is the project. On PC, the game runs inside
  moderngekko-run, a Dolphin-derived host (GX, audio, input, DVD, CARD,
  timing) using SDL3 for window/input and Cubeb for audio, with the module
  compiled to a native DLL and loaded at entry 0x80005240.
- The runtime already has an interpreter fallback for code it cannot trust:
  on PC it runs CTTR's self-modifying chunk [0x80369860, 0x8036D860) through
  the interpreter while everything else runs native. That fallback is a
  feature we will rely on, not a bug to design around.
- Encouraging precedent found Oct 30: this same runtime family already runs
  on iPhone, iPad, Apple Silicon Mac and tvOS (the SunPad project, Super
  Mario Sunshine), as ahead-of-time native ARM64 with interpreter fallback
  and no PowerPC JIT, rendering through a Metal GX backend. So the runtime
  has already survived one port to a locked-down ARM64 platform, its GX
  layer already has more than one backend implementation, and the no-JIT
  design Horizon homebrew needs is already its normal mode on iOS.

## What has to be audited (on the LOQ clone, no code changes)

Milestone H0 is a reading exercise over lib/ModernGekko in the template
clone. For each subsystem, record: what the desktop build uses, what a
Horizon build would use instead, and the size of the gap.

- Host shell: how moderngekko-run creates its window and main loop, and how
  much of it is SDL versus direct OS calls.
- GX backend selection: which graphics backend the PC run actually uses,
  how backends are registered, and how big the backend interface is (the
  SunPad Metal backend is the reference for what a new backend costs).
- Audio: Cubeb sits behind which internal interface, and what an audout
  (libnx) backend would have to satisfy.
- Input: the GCPadNew.ini path (no in-app config UI exists; a hand-authored
  ini is required even on PC), and where pad state enters the core.
- Disc and card: both are file-backed on PC (extracted game directory,
  memory card image). Confirm the exact file APIs used; Horizon fs should
  map cleanly if the calls are ordinary stdio.
- OS services: threading, timers, filesystem paths, and any socket or
  process APIs in the linked subset of the Dolphin core. This is where
  Dolphin-derived code usually hides its platform assumptions.
- Build graph: which vendored libraries the moderngekko targets actually
  link (the PC configure pulls in a large Dolphin dependency tree; the
  Horizon build needs the smallest honest subset).

## Milestones

- H0, audit and dependency map. Deliverable: the table above, filled in
  from the actual source. Exit condition: we can name the smallest
  separable compile target for a Horizon probe.
- H1, cross-compile probe. Using the pinned devkitPro Docker image pattern
  (already proven on the LOQ during the Strikers spike), try to compile
  that target for aarch64 with libnx. No game, no graphics. Deliverable: a
  blocker list with each blocker's size and shape. Exit condition: either a
  linkable static library, or a blocker list concrete enough to price.
- H2, null-backend boot on hardware. An NRO that loads the CTTR module
  (recompiled for ARM64 via the C backend) with null video and null audio,
  logging over stdout/nxlink, game logic ticking, SMC chunk on the
  interpreter. Exit condition: core init and module load on a real Switch,
  stable for minutes. This is the cheap kill-gate for the whole Switch
  phase: if the runtime cannot stand up here, the renderer debate is moot.
- H3, renderer decision gate. Decide with H0's measured backend interface,
  not by preference: (a) a deko3d GX backend (the Super Paper Mario work
  already proved a deko3d backend inside a GX-shaped runtime is viable),
  (b) Vulkan over Mesa NVK (the nvk-switch-builder repo and its arm64 CI
  artifact pipeline already exist from the Strikers spike), or (c) another
  backend modelled on SunPad's Metal one if its seam turns out smallest.
  Evidence for (a), added Nov 4, 2026 (Brandon's pointer, verified):
  two GameCube games already ship on Switch drawn through Aurora with a
  deko3d backend. centollOS/SwitchWaker (GameCube Wind Waker, from the
  decompilation) replaced its OpenGL renderer with deko3d (roughly 90%
  less CPU per frame; shaders prebuilt). The Dusklight Switch port
  (Twilight Princess, Twilit Realm's decomp-based reimplementation;
  Alek's Ultimate NX Edition) defaults to deko3d on Switch and its
  renderer is Aurora's lib/deko, built from SwitchWaker's. So option (a)
  has a named, reusable starting artifact (Aurora lib/deko, via
  SwitchWaker) proven on the same graphics layer this runtime uses,
  not just a design direction.
- H4, platform layer and packaging. libnx input mapped through the pad
  config, audout audio backend, sdmc paths for the extracted game data and
  memory card file, title-takeover NRO packaging, own-dump data only.

## Known risks, stated plainly

- SDL3 on Horizon: SDL2 exists in devkitPro portlibs; SDL3's state there
  is an H0 question. If the host shell leans hard on SDL3, replacing that
  surface with direct libnx calls is part of the port, not a surprise.
- The interpreter-run SMC chunk will cost more on the Switch's Cortex-A57
  than on the LOQ. Whether it matters depends on how hot that code is in
  races, which the pending PC soak checks partially answer.
- Dolphin-derived code carries desktop assumptions in inconvenient places.
  H1 exists to enumerate them before anyone commits to the full port.
- Scale: even with the Apple precedent, this is months-scale work. H2 is
  designed so the project can be killed cheaply if the answer is no.

## Reference: mkdd-nx v1.8.2 release notes (passed along by Brandon, Nov 2, 2026)

https://github.com/digdat0/mkdd-nx/releases/tag/v1.8.2

- v1.8.2 is a multiplayer fix: with 3 or 4 players, MKDD Plus courses no
  longer draw black or navy in Versus and Grand Prix (regression from
  v1.8.0/v1.8.1).
- Known issue carried in the notes: 4 players on MKDD Plus can run slowly,
  30 fps or less at stock clocks with AUTO resolution and HD textures, and
  50+ fps with an overclock. The notes recommend OC for large games on
  complex tracks.
- Why it matters here: this is the shipped deko3d chassis (see
  CHASSIS-DEEP-DIVE-2026-11-02.md) stating its own stock-clock envelope in
  public. Even an optimised, shipped GC recomp port lands at or under
  30 fps in its heaviest multiplayer content at stock clocks, and its
  authors steer heavy-case players to overclock. Calibrate CTTR Horizon
  expectations and public wording accordingly: near-60 in light content
  does not generalise to the heavy end at stock.
- Packaging shape also worth noting: release assets are the NRO, the
  MKDD-NX-Tools companion apps, and an update.txt consumed by an in-game
  updater.

## Reference: digdat0's port guides (passed along by Brandon, Nov 4, 2026)

Four guides from the mkdd-nx and Animal Crossing (gcNX) projects, read
the night they were posted. They are the closest written playbooks to
this phase: a GameCube recomp port that shipped on deko3d, and a
GameCube decomp port's Switch platform lessons.

- RECOMP_PORT_GUIDE.md (mkdd-nx):
  https://github.com/digdat0/mkdd-nx/blob/main/docs/RECOMP_PORT_GUIDE.md
- DEKO3D_MIGRATION.md (mkdd-nx):
  https://github.com/digdat0/mkdd-nx/blob/main/docs/DEKO3D_MIGRATION.md
- OPTIMIZATION.md (mkdd-nx):
  https://github.com/digdat0/mkdd-nx/blob/main/docs/OPTIMIZATION.md
- SWITCH_PORT_GUIDE.md (ACGC-Switch-Port):
  https://github.com/digdat0/ACGC-Switch-Port/blob/main/docs/SWITCH_PORT_GUIDE.md

What transfers to CTTR:

- The GX decoder seam is the pivotal design decision: mkdd-nx decodes
  GX on its own core into a backend-neutral Frame, which is what made
  its GL-to-deko3d move a renderer-only swap. On the WiiCompiled side,
  Aurora's lib/deko (via SwitchWaker, per the H3 evidence above) is
  that same swap. Keep the seam clean whichever chassis wins.
- Their deko3d migration was run as an experiment with a written exit
  (at least 10% less GPU time at the same settings, no visual
  regressions, or GL stays). A template for the H3 gate. Measured
  result: about 42 to 59.9 fps handheld at 1.5x, render CPU cost
  5-9 ms down to about 2.5 ms.
- EFB copies dominated their GPU time (15 copies, 9.35 ms of a 17 ms
  frame) and skipping the final copy (present from the EFB when
  nothing draws after it) was the single biggest gain at 4x. Expect
  CTTR's GX copy patterns to behave the same; profile copies before
  tuning anything else.
- Measurement traps: if a figure does not change when the workload
  changes, it is timing waits, not work (their GPU total sat near
  15 ms at 137 draws and at 825). Count game frames, not screen
  updates. Emulator and PC harness prove correctness, never speed.
- Regenerate everything after changing native/HLE bind lists, and
  verify the regen landed (timestamps plus grep). The PC campaign
  learned the same rule with emit-build-shards.
- The MMIO census: instrument hardware accesses once, then drop the
  address check everywhere the census found no hardware access. A
  named optimisation candidate for translated code on the A57.
- Platform traps from the AC guide: a game that replaces global
  operator new will capture a linked-in driver's allocations on
  Switch (rename the game's symbols with objcopy); pointers handed
  to audio/DMA/GPU may be written through later, so copy on hand-off;
  SDL2's Switch pad mapping is positional (A/B and X/Y swapped);
  ApmCpuBoostMode_FastLoad drops the GPU to 76.8 MHz, so end boost
  at the first presented frame; clocks stay opt-in and dynamic
  resolution is the performance answer.
- End state in both projects is CPU-bound with a flat profile, which
  matches the PC campaign's findings and the stock-clock calibration
  in the mkdd reference above.
