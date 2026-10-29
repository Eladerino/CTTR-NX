# Port layout (placeholder until Phase 2)

When the upstream decomp reaches a shiftable state, the port source lands
here, following the Strikers port layout:

- Game source: the decompiled CTTR code (CC0 upstream), reorganised the way
  Strikers reorganises its decomp (game, SDK-facing layer, engine/node).
- `platform/`: the host layer that replaces GameCube hardware services:
  disc/DVD, PAD input, OS services, audio out, memory card, FMV playback.
- `platform/switch/`: Horizon-specific init, rumble, and glue.
- Switch packaging: devkitPro toolchain file, NVK/Mesa build, NRO packaging,
  title takeover install layout (game data read from the player's own disc
  image on the SD card, never bundled).

Nothing in this directory is game code yet. See docs/CHASSIS-MAP.md for the
full transfer analysis and docs/DECOMP-WATCH.md for the start conditions.
