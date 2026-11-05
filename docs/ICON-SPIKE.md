# Spike plan: Switch button icons for CTTR prompts

Written Oct 30, 2026. Goal: prove whether moderngekko-run honors texture
replacement for Crash Tag Team Racing's button prompts, and swap one
GameCube prompt glyph for a Switch one. One visible swap is success; the
full prompt pass is later work.

## Why this looks possible

Brandon's own listing of the moderngekko user directory
(%LOCALAPPDATA%\moderngekko) shows the Dolphin-family texture
folders already present: Dump\Textures, Load\Textures, and
Load\DynamicInputTextures. The last of those is Dolphin's purpose-built
system for swapping button prompt textures per connected controller. The
folders existing is not proof the frontend uses them; the spike exists to
find out.

## Unknowns the spike answers, in order

1. How texture dumping and loading are switched on in this fork. Stock
   Dolphin uses graphics settings; this fork's config.ini [Video] section
   has no such keys, so the toggles may be always-on, inherited from a
   Dolphin.ini, or missing entirely.
2. Whether CTTR's prompts are standalone textures, regions of larger UI
   sheets, or font-drawn text (only the first two are swappable).
3. Whether the static Load\Textures path works, the DynamicInputTextures
   path works, both, or neither.

## Method

1. Baseline run of the game, then inspect Dump\Textures in the user dir.
   If it is empty, grep the ModernGekko source in the LOQ template clone
   for the texture settings (DumpTextures, LoadTextures, DynamicInput) to
   find what this frontend actually reads.
2. From the dump, pick one small prompt texture (menu or tutorial glyph).
3. Make the Switch replacement at identical dimensions. Art source is
   already local and licence-clean: Kenney Input Prompts 1.5A (CC0) at
   ~/workspace/spm-switch-scout/NewSuperPaperBros/tools/button-art, with
   the generator script make-button-icons.py beside it (same pipeline the
   Paper Mario port used). Mapping is label-true, matching the pad config:
   GC A to Switch A, B to B, X to X, Y to Y, Z to ZR, L to ZL, R to ZR,
   Start to Plus.
4. Place the replacement in Load\Textures under the dumped texture's exact
   filename, relaunch, and view the same prompt in game.
5. If the static path works, evaluate a DynamicInputTextures pack as the
   cleaner long-term form. If only the dynamic path works, adapt to its
   per-device JSON format instead.

## Success and failure

- Success: one prompt in game visibly shows a Switch glyph where a
  GameCube glyph was. That proves the pipeline and unlocks a full pass,
  and the result carries forward to the Switch build, where Switch icons
  are the correct end state anyway.
- Failure is also a result: if neither load path is honored, icon swaps
  move to the Horizon phase (where we control the runtime) and the PC
  build keeps its GameCube prompts. No time is spent repainting textures
  before the one-texture proof lands.

Sequencing: after the gamepad fix, so the prompts being swapped match the
controller actually in use.

## Desk pre-check (Nov 2, 2026, RecompCore source)

Partially answers unknown 1 without a LOQ session. In RecompCore
(branch moderngekko-vendor, the runtime source behind the session logs),
texture dumping is config-gated exactly as in Dolphin: the key is
GFX system, "Settings" / "DumpTextures", default false
(Source/Core/Core/Config/GraphicsSettings.cpp), read into
VideoConfig.bDumpTextures (Source/Core/VideoCommon/VideoConfig.cpp).
In stock Dolphin terms that is a GFX.ini containing
[Settings] DumpTextures = True.

What is NOT established: whether moderngekko-port's startup loads a
Dolphin-style GFX.ini from its user directory at all. Its config.ini is
a custom format, UICommon::Init in the Qt path forces DumpTextures off
at base layer during init, and the ModernGekko GitHub repo's current
layout (vendor/dolphin_legacy) differs from the template's pinned
submodules, so GitHub HEAD is not ground truth for Brandon's build.

Practical step order when the spike runs:
1. Baseline run, check Dump\Textures (the build may dump always-on).
2. If empty, create Config\GFX.ini in the moderngekko user dir with
   [Settings] DumpTextures = True and LoadCustomTextures = True,
   rerun, check again.
3. If still empty, grep the pinned source in the LOQ template clone
   (lib/ModernGekko) for DumpTextures and follow what its frontend
   actually reads. That clone, not any GitHub HEAD, is the authority.
