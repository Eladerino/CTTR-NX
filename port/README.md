# Port

This directory holds the WiiCompiled spike project for Crash Tag Team
Racing:

- `wiicompiled-spike/projects/cttr/recomp.yml` The translator project:
  24 MB MEM1 configuration with the game's real SDA bases, reading the
  DOL path from the `RECOMP_CTTR_DOL` environment variable.
- `wiicompiled-spike/projects/cttr/MAP.txt` The function map for the
  translator, converted from the upstream decompilation's symbol table
  (bluisblu/cttr, CC0-1.0), plus a handful of splits added during the
  boot campaign.

The runtime working tree itself lives outside this repository. The
translation results, the HLE binding campaign, and the current boot
state are recorded in docs/WIICOMPILED-SPIKE.md. The earlier plan for
this directory (a decomp-source layout following the Strikers port) was
set aside with the decomp route on Oct 29, 2026; see
docs/CHASSIS-DEEP-DIVE-2026-11-02.md for how the chassis choice was made.
