# CTTR NX (working title)

An unofficial, non-commercial fan project: a native Nintendo Switch port of
Crash Tag Team Racing (GameCube, 2005), built downstream of the community
matching decompilation at github.com/bluisblu/cttr.

## Status: preparation phase

There is no playable build and no game code in this project yet. The upstream
decompilation is early (see docs/DECOMP-WATCH.md), and a source port can only
begin once the decompiled code reaches a fully linked, shiftable state.
What exists now is the groundwork: a studied reference chassis (the Super
Mario Strikers Switch port), an architecture map, and the project skeleton
the game code will land in when the decomp is ready.

## Legal and provenance

- This project is not affiliated with, endorsed by, or connected to Radical
  Entertainment, Vivendi, Sierra, Activision, or Nintendo. Crash Bandicoot
  and Crash Tag Team Racing are trademarks of their respective rights
  holders; all game IP belongs to them, all rights reserved.
- No game data is distributed here. Running any future build will require a
  disc image dumped from your own copy of the North American GameCube
  release (G9RE7D, Rev 0).
- The upstream decompilation (bluisblu/cttr) is CC0-1.0. This port is a
  separate downstream project. Per the upstream project's stated policy,
  nothing from this project is contributed back upstream, and no AI-assisted
  work is submitted there. AI assistance used in this project is disclosed
  here, in this repository, where it belongs.
- Any licence granted here covers this project's own code only, never game
  data or third-party material.

## Layout

- `research/` Local reference clones (Strikers port, cttr decomp). Not part
  of the project source; never committed anywhere.
- `docs/CHASSIS-MAP.md` What the Strikers Switch chassis is made of, which
  pieces transfer to CTTR, and which problems are CTTR-specific.
- `docs/DECOMP-WATCH.md` Snapshot of upstream decomp state and the concrete
  conditions that make the port phase startable.
- `port/` Where the port source will live when Phase 2 opens. Mirrors the
  Strikers layout: game source, platform layer, Switch packaging.
- `tools/decomp-status.sh` Prints the state of the local cttr clone and the
  upstream HEAD, for a quick progress check.
