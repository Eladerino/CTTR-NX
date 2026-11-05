# Phase 0: disc, dump, and decomp build check

Goal: prove three things in one sitting, before any port code depends on
them. (1) The disc is the exact build the decomp targets (USA, Rev 0,
G9RE7D). (2) The dump of it is good. (3) The decomp toolchain builds
against that dump on the LOQ.

Everything in this phase happens on Brandon's machines. The dump and
anything generated from it stay there; only build logs come back.

## Step 1: dump the disc

Route: Brandon's modded Wii U, currently at his brother's place, so the
console has to be picked up (or the dump done there) before this step.

CleanRip runs in the Wii U's vWii mode. Confirmed Oct 29, 2026: both
the Wii U side and the vWii side are modded, so this is direct:

- Run CleanRip from the vWii Homebrew Channel, dump to SD or USB.
  Requested format: plain ISO, CleanRip's default full dump, exactly
  1,459,978,240 bytes, untrimmed and unscrubbed (plus a .bca file,
  which is not needed here). 1.46 GB fits a FAT32 card in one piece,
  no splits. The decomp build accepts other formats too (RVZ, GCM,
  WBFS and more), but plain ISO needs no conversion, verifies cleanly
  in Dolphin, and is reusable by every later phase, so it is the one
  to make.
- Fallback if there were no Wii/Wii U: a PC dump needs one of a short
  list of supported desktop DVD drives and Rawdump/Friidump; laptop
  drives (including the LOQ's) generally cannot read GameCube discs.
  Not needed here.
- Keep the ISO somewhere stable on the LOQ, for example
  C:\Games\CTTR\cttr.iso. It will be reused by every later phase.

## Step 2: set up the decomp check (LOQ, native Windows)

The upstream README recommends native Windows tooling (not WSL) for this
repo. One-time setup:

```
py -m pip install ninja
```

Then:

```
cd C:\Games\CTTR
git clone https://github.com/bluisblu/cttr.git
cd cttr
```

This clone is read-only reference for the build check. Per the upstream
project's policy, nothing is ever committed or pushed back to it from
this project.

## Step 3: place the dump and build

Copy the ISO into the version folder so the tree looks like:

```
cttr\orig\G9RE7D\cttr.iso
```

(Any filename works; ISO, GCM, RVZ and the other formats from the
upstream README are all accepted.)

Then:

```
python configure.py
ninja
```

## What success and failure look like

- The build verifies the dump against config/G9RE7D/build.sha1 early.
  A hash mismatch means wrong revision or a bad dump, and it fails
  there, loudly, before wasting time. That check IS the disc-version
  proof; there is no separate step.
- Success: ninja runs to completion and links the matched portion of
  the game. At the decomp's current state most of the binary is still
  the original code being matched against, which is expected and fine.
- Send back: the last screen of ninja output, or the full error if it
  stops. That log decides the next step.

## Result: PASSED, Oct 29, 2026

Ran end to end on the LOQ against Brandon's own dump.

- SPLIT extracted the ISO and analysed the DOL: 25,203 functions,
  448 objects written.
- The verification step passed: CHECK config\G9RE7D\build.sha1
  reported "./build/G9RE7D/main.dol: OK". The disc is exactly the
  target build (USA, Rev 0, G9RE7D) and the dump is good.
- Full build completed (147 steps) and produced the progress report:
  All 6.85% matched, 4.45% linked (88 / 448 files); SDK code 95.72%
  matched; Lua code 88.60% matched. The unmatched mass is the game
  and engine code, as DECOMP-WATCH.md describes.
- The MWCC "return value expected" warnings are the decomp's empty
  stub function bodies; expected and harmless.
- Toolchain lessons from the run: the PATH ninja on the LOQ is
  devkitPro's MSYS2 build, which runs commands through /bin/sh and
  mangles backslash paths; the pip ninja (Python312\Scripts\ninja.exe,
  runs through cmd) is the one to use for decomp work. A one-line
  local edit in the clone's tools/project.py (download_tool.as_posix()
  in the download rule) is also in place.

## After Phase 0 passes

- The CTTR-NX repo gets a Phase 0 results note (disc verified, build
  verified, LOQ toolchain proven).
- The next buildable prep item is the Strikers Switch toolchain spike:
  proving the pinned devkitPro Docker image, Mesa NVK build, and Dawn
  fork compile on the LOQ, so the Phase 2 start is not blocked on
  toolchain archaeology.
- Phase 2 itself (game code in the port) still waits on the decomp
  reaching a fully linked, shiftable state. Phase 0 does not change
  that gate; it removes every other unknown in front of it.
