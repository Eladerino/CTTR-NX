# Chassis map: what the Strikers Switch port is, and what CTTR reuses

Written Oct 29, 2026 from direct inspection of both clones in research/:
new-coke/strikers (port) and bluisblu/cttr (decomp). File and line counts
below were measured in those clones, not copied from project pages.

## Update, Oct 30, 2026

This map was written for the decomp-based route, which was set aside the
same day it was written. The active route is static recompilation
(DolRecomp + ModernGekko), with the Switch phase scoped in
docs/HORIZON-SCOPE.md. The Strikers material below stays useful as
background for that phase's renderer decision (the Mesa NVK build recipe,
and the NVK builder repo produced during the Strikers spike), but the
game-layer and platform-layer mapping here assumed decompiled source and
no longer describes the plan.

## The Strikers chassis, layer by layer

1. Game layer. The decomp source, reorganised under src/ (Game, NL engine,
   SDK-facing code, PowerPC_EABI_Support runtime). A CTTR port would hold
   the cttr decomp source the same way: src/CTTR game code, the engine, and
   the src/dolphin SDK tree as the interface surface.
2. Aurora (extern/aurora, vendored). Replaces the GameCube SDK's GX, OS,
   PAD, DVD, CARD and VI behaviour with host implementations backed by
   SDL3 and a modern GPU API. The port compiles the game against an
   "aurora-overlay" include directory (port-specific SDK shims) plus
   Aurora's own headers, selected by a CMake flag (STRIKERS_AURORA).
3. Platform layer (src/platform/, ~70 files). The per-game host glue
   Aurora does not provide: disc image reading (disc.c, disc_reader.cpp),
   PAD and input mapping, audio mixing and output, memory card images,
   THP video playback (thp.c), OS services, region and language handling.
   A Switch-specific subdirectory (src/platform/switch/) carries nx_init,
   rumble, and Horizon gap-filling (posix_gaps.c, sqlite_vfs.c).
4. Switch GPU stack. This is the heavy part, and it is pinned end to end in
   tools/switch/:
   - Mesa with NVK (the open Vulkan driver for the Switch's Tegra GPU),
     built from a pinned Mesa commit (tools/switch/build-nvk.sh,
     deps.env MESA_REF) with a Rust toolchain (NVK is written in Rust;
     pinned 1.99.1, plus bindgen/cbindgen) and meson.
   - A fork of Dawn (WebGPU) with Switch changes (new-coke/dawn-switch,
     pinned commit), fetched by tools/fetch-switch-deps.sh and validated
     against the Dawn version Aurora pins.
   - A local patch set against Aurora itself: tools/aurora-local-changes.patch,
     5,391 lines across 63 files. The Switch support is not stock Aurora.
   - The devkitPro toolchain runs from a pinned Docker image
     (devkitpro/devkita64 digest in deps.env), via
     tools/toolchain-switch.cmake. Packaging (tools/switch/package.sh)
     produces a title-takeover style install: NRO plus data read from the
     player's own disc image on the SD card.
5. Settings and UI. A separate settings app (borealis, a Switch UI toolkit,
   sits in extern/ alongside aurora and musyx) and an ini file
   (strikers-switch.ini.example) for graphics, controls and data location.

## What transfers to CTTR directly

- The whole Switch GPU stack recipe: pinned Mesa NVK build, Dawn fork,
  devkitPro Docker toolchain, packaging scripts. Game-agnostic; the pins
  will need refreshing to whatever is current when Phase 2 starts, but the
  shape of the build is proven.
- The Aurora local-changes patch as the starting point for Switch support
  in Aurora, rather than rediscovering those 63 files of fixes.
- The platform-layer pattern: which services needed hand-written glue in
  Strikers (disc, PAD, audio, card, THP, region) is the checklist for
  CTTR's platform layer, even though the implementations differ.
- The distribution model: own-dump data loading, no assets shipped, ini
  driven config, settings kept off the game binary.

## What is CTTR-specific (the real unknowns)

- Engine. Strikers is Next Level Games' engine; CTTR is Radical's Pure3D
  lineage. GX usage patterns, scene graph, and resource formats differ.
  Nothing at the engine layer transfers; this is where the port work lives,
  and it cannot start until the engine code is decompiled (it is not yet:
  see DECOMP-WATCH.md). One concrete detail already visible: the game
  embeds a Lua VM (the upstream repo's most recent commit, Oct 15, 2026,
  matched luaV_execute), so mission and game logic are partly scripted.
- Audio. Strikers carries MusyX (extern/musyx, MIT). CTTR's audio stack is
  Radical's own over the SDK AX layer; NISManager and the Sound headers in
  src/CTTR are the visible surface so far. No transfer assumed.
- FMV. Strikers implements THP playback in its platform layer. CTTR's
  video format on GameCube is unconfirmed; if it is also THP, that piece
  transfers conceptually. To be answered from the dump in Phase 0.
- Single DOL. cttr's config builds sys/main.dol only, with no REL modules
  configured. If that holds for the full game, CTTR avoids the overlay
  problem entirely, which is genuinely good news for port difficulty.
- Content shape. CTTR is a hub-world game (on-foot park exploration plus
  racing), not a single-mode sports game. Streaming, load sets (LoadSet.h
  exists in the decomp headers), and save flow will need their own work.

## Build environment reality check (Oct 29, 2026)

- This VM has cmake 3.28 and Python 3.12 but no devkitPro, no ninja, and
  no Docker, so no Switch compile can happen here (same constraint as the
  Super Paper Mario work). Switch builds run on Brandon's LOQ, which is
  also where his dump and any generated game code stay.
- The decomp's own Phase 0 build (configure.py + ninja on the LOQ, native
  Windows tooling per its README) needs only Python and ninja, and proves
  the disc and toolchain before any port code exists.

## Spike result (Oct 29, 2026, LOQ)

The Strikers Switch build was spiked on the LOQ the same day:

- Docker Desktop installed; the pinned devkitPro image
  (devkitpro/devkita64@sha256:1fc388c3...) pulls and runs on x86_64.
- Inside the container: apt build deps installed, the Dawn fork fetched
  (tools/fetch-switch-deps.sh), and configure ran with working devkitA64
  compilers (GNU 15.2.0) until it stopped at the one predicted wall:
  "extern/nvk-switch/lib/libvulkan.a is missing". The game-compile half
  of the chassis is therefore proven on an x86_64 Windows host.
- The remaining piece is only the NVK static library, whose build script
  checks the Docker host architecture and refuses non-arm64, because
  mesa-switch compiles NVK's Rust code for the host with no target flag.
  The official Switch release offers no shortcut: its zip is the NRO
  plus licences, with the driver statically linked inside.
- Plan: build NVK once on a GitHub Actions arm64 runner
  (ubuntu-24.04-arm) from a small builder repo, download the
  extern/nvk-switch tree as an artifact, drop it into the LOQ clone,
  then re-run configure and tools/switch/rebuild.sh. Not yet started.
