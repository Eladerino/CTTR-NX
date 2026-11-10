# Self-updater: CTTR adoption prep (Nov 5, 2026)

Prepared for the shared cross-port self-updater (SPM chat leads the
shared core, same dev-kit pattern as the SwitchWaker debug server).
This doc answers the four CTTR-side questions: version source, menu
row placement, release asset pattern, and the exact file set an
update may touch. All runtime facts are from the LOQ working tree
(C:\dev\cttr-wiicompiled) as of Nov 5, 2026.

Headline finding: the WiiCompiled runtime already ships a working
updater (runtime/src/updater.cpp, from the NewSuperPaperBros
product). CTTR's PC shell adoption is mostly repointing and
packaging, not new code. The Switch build adopts the shared core
instead; do not port updater.cpp's apply mechanism to Horizon.

## 1. Version source

- The running build reads its own version from `version.txt` beside
  the engine: Updater::Start() reads the first line of
  EngineDir()/version.txt (for example "v1.0.5") into the current
  version string. Absent or empty means a development build: the
  updater stays Off and its menu rows are hidden.
- The comparison target is the GitHub release's `tag_name`, fetched
  from the releases/latest API. Compare is dotted-numeric
  (Parts()/Newer() in updater.cpp): "v1.2.3" parses to {1,2,3}.
  Caveat: suffixes are not parsed, so "v0.1.2-beta" compares as
  0.1.2. Keep release tags plain semver.
- version.txt is written at packaging time from the release tag.
  One source of truth: the tag. Stamp version.txt from it when the
  release zip is built, never by hand.
- Switch (shared core, later): the per-port config's version source
  is the version baked into the NRO at build time (the NACP version
  string, the spm-nx precedent: "0.1.2-beta"). Stamp it from the
  same tag at build time.

## 2. Menu / settings row placement

- PC shell (existing, working): the settings overlay's Game page
  carries two rows, shown only for packaged builds
  (settings_overlay.cpp, the Updater block near the Language row):
  an "Update" action row whose value renders the state
  ("<latest> - install", "Up to date (<current>)", "Checking...",
  "Downloading...", "Couldn't connect - retry", "Off"), and a
  "Check for updates" on/off toggle backed by the CheckUpdates key
  in Config.toml. A paper notice also appears in-game when an
  update is available.
- Placement decision: the commission's generic rule put the row
  on the Developer page, but Brandon refined placement per menu
  on Nov 5, 2026: JSRF's row goes under its About section, and
  SPM's goes under the Game page (its menu has no About; the
  Game tab is short). CTTR's shell is the same JosiahG menu
  family as SPM's, and the existing updater rows already live
  on its Game page, so CTTR placement is the Game page: no move
  needed, and it matches the decision Brandon made for this
  menu. Priority is explicitly not urgent; in-flight port work
  finishes first.
- Behaviour change to make at adoption: today
  InitializeRuntimeSettings() calls Updater::Start(), which checks
  in the background at boot. The locked rules say menu-triggered
  only, never boot-blocking, sockets on demand when tapped. Gate
  Start() down to reading version.txt at boot, and run the check
  from the row tap (Install() already re-runs the check from the
  Failed state; expose the check for the tap).

## 3. Release asset pattern (Eladerino/CTTR-NX)

Repo state, verified Nov 5, 2026: no releases and no tags exist
yet. The pattern is greenfield, shaped to the existing updater's
URL construction (kDownload + tag + "/" + kAsset, asset name
constant across releases):

- Repo: Eladerino/CTTR-NX. Repoint kApi / kDownload in
  updater.cpp from josiahg2502-glitch/NewSuperPaperBros (three
  constants, plus the asset name below).
- Tag: `v<semver>` (v0.1.0, v0.1.1, ...). The tag is also what
  gets stamped into version.txt.
- Windows asset: `CTTR-NX.zip`, one top folder (CTTR-NX/)
  containing a single `engine/` folder (the file set in section
  4). The unpacker finds the top folder by looking for the one
  that contains `engine/`, so that shape is required, not
  cosmetic. Linux twin if ever needed: `CTTR-NX-linux.tar.gz`.
- Switch asset (shared core, later): proposed
  `CTTR-NX-switch.zip` holding the app-folder payload: the NRO
  plus bundled assets (cacert.pem, dsp_coef.bin, licenses/,
  wii_bootstrap/, per the spm-nx staging set). The shared core
  fixes its own pattern; this is CTTR's config entry for it.

## 4. Exact file set an update may touch

PC packaged layout (install root = the folder the player keeps;
engine/ inside it). The update merge (robocopy /E, no /MIR: files
are added and overwritten, never deleted) may touch ONLY:

- engine/WiiCompiled.exe
- engine/version.txt
- engine/SDL3.dll
- engine/webgpu_dawn.dll
- engine/dxcompiler.dll
- engine/dxil.dll
- engine/libc++.dll
- engine/libpng16.dll
- engine/libunwind.dll
- engine/libz.dll
- engine/dsp_coef.bin

That is the full distributable set the build produces (verified
against build-cttr's output; test executables, static libraries
and CMake files are build artifacts and never ship).

Never in reach, by construction (none of it is in the asset):

- The player's game data (the extracted disc folder / game/),
  which sits outside engine/.
- All user data: Documents\CTTRSaveData (Config.toml, Logs, save
  states, saves). It lives outside the install root entirely.
- Mods and texture replacements (player folders, not shipped).
- On Switch: UserData/ (saves, settings, caches) and game/ are
  outside the shared core's merge set for the same reason: the
  asset simply does not contain them.

## 5. How the existing updater applies (for reference)

Check: curl the releases/latest JSON to UserData/update_check.json,
parse tag_name, compare. Download: curl the asset into
<root>/_update/, extract with tar, then hand over to a generated
script (PowerShell on Windows, sh elsewhere) that waits for the
process to exit, robocopies the unpacked folder over the install
root with /E, relaunches WiiCompiled.exe, and deletes _update/.
If the engine folder is not literally named "engine", Download()
refuses: there is nothing safe to copy over. Test hook:
SPM_UPDATE_TEST_URL points the check/download at a local stand-in
(latest.json, <tag>/<asset>); SPM_UPDATE_TEST_INSTALL auto-installs.

## 6. Adoption checklist (CTTR)

1. Repoint kApi, kDownload, kAsset in updater.cpp to
   Eladerino/CTTR-NX and CTTR-NX.zip. (Branding pass follow-up:
   these still name JosiahG's repo; the rebrand did not touch
   them because the updater was dormant on dev builds.)
2. Gate the boot-time check per section 2 (menu-triggered only).
3. Add the packaging step: assemble CTTR-NX/engine/ with the
   section 4 file set, stamp engine/version.txt from the tag,
   zip as CTTR-NX.zip with the single top folder.
4. Cut the first GitHub release (v0.1.0) with that asset so the
   check has something to find.
5. Test end to end with SPM_UPDATE_TEST_URL against a local
   stand-in before the first real release.
6. Switch, when Horizon lands: adopt the shared core with the
   section 1/3 config; the Developer page row; NRO + bundled
   assets only.
