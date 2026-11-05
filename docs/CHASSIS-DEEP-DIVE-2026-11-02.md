# Chassis deep dive: mkdd-nx and wiicompiled, and what they mean for CTTR

Written Nov 2, 2026. Question from Brandon: why not throw CTTR at
wiicompiled the way SPM and JSRF were started, and see what fails?
Method: source-level reads of digdat0/mkdd-nx (cloned into
`research/mkdd-nx`) and of the local WiiCompiled tree
(`~/workspace/spm-switch-scout/NewSuperPaperBros/wiicompiled`, the
framework spm-nx is built on). This document corrects the framing given
in chat on Nov 1-2, 2026 where the source disagrees with it.

## Verdict up front

The purpose-built chassis is a proven route to a shipped GameCube game
on Switch: mkdd-nx did exactly that, at near-60 fps on stock clocks.
And wiicompiled is not the Wii-only, SPM-shaped thing it was described
as in chat: it is a multi-game framework whose own example project
targets GameCube DOLs and whose graphics layer (Aurora) describes
itself as a GameCube and Wii compatibility layer. The runtime question
is real but enumerable, and its first layer surfaces at link time as a
list, not one crash at a time. A bounded translator-plus-link spike on
the LOQ would produce that list in days. None of this displaces
ModernGekko, which plays CTTR today and stays the reference
implementation either way. CTTR also stays behind SPM in the queue.

## What mkdd-nx actually is

A C/deko3d port of MKDD-Recomp (LeftInWalmart, Rust/Bevy, PC), per its
README and docs/ARCHITECTURE.md. The design and analysis artifacts come
from the PC project; the Switch code is a port of that design, not a
from-zero runtime.

Pipeline: the disc image feeds MKDD-Recomp's "sheets" (CSV: p-code per
instruction, function list, memory map, HLE list), and
`tools/gen_c.py` emits one C function per guest function. The generator
does real optimization work: per-function register dataflow (registers
live in C locals, stored back only at calls, returns and slow paths),
ABI liveness (volatile registers the callee never reads are not stored;
returns hand back only r3/r4/f1), paired singles as inline C, an inline
MEM1 fast path for loads/stores, and trampolines for MMIO.

Runtime (`runtime/`, about 21,000 lines of C): hand-written, per game.

- `hle.c` (696 lines): functions on the sheets' HLE list check a hook
  on entry and are routed here; OS, DVD, audio and GX SDK calls.
- `native.c` (7,422 lines): 113 hot engine functions (matrix maths,
  J3D animation, collision, HUD) rewritten by hand in C. A verifier
  mode runs sampled native calls through the recompiled original from
  the same state and compares results and memory.
- `gx.c` (2,797 lines): a GX command-stream decoder (FIFO and display
  lists to batched vertices and pipeline state) on its own thread,
  producing a neutral Frame that the renderer replays.
- `render_dk.c` (about 2,100 lines): the deko3d replay, with an
  emulated EFB and per-material specialised TEV shaders (an uber
  shader draws while they compile). docs/DEKO3D_MIGRATION.md records
  the move from OpenGL ES at stock handheld clocks: race fps about 42
  to 53 on the first deko3d build and 59.9 after GPU work; CPU spent
  rendering per frame 5-9 ms down to about 2.5 ms.
- `dsp.c`: high-level emulation of the JAudio DSP microcode.
- `memcard.c`: memory card at the CARD API level; saves are standard
  .gci files.
- `sched.c`: guest threads as host threads, one running at a time.
- Thread layout on Switch: core 0 renders, core 1 runs the game,
  core 2 runs the GX decoder, timer and a sampling profiler.
- There is no interpreter and no JIT anywhere. Every guest function is
  translated ahead of time, hooked to HLE, or hand-nativised. MKDD's
  code all lives in its DOL, so the design never needs an answer for
  code that appears at runtime.

What it stood on: MKDD-Recomp's existing PC work (sheets pipeline,
runtime design, renderer design; the build fetches its sheets),
doldecomp/mkdd (CC0) for function names and structures, and a
first-party Nintendo title on the standard SDK and the well-documented
J-framework/JAudio stack.

## What wiicompiled actually is

WiiCompiled: a framework with a .NET translator (`translator/`, DOL and
REL inputs handled generically), a C++ runtime (`runtime/`, about
167,000 lines), the Aurora graphics layer, and per-game projects under
`projects/` (spm, mkwii, nsmbw, plus an examples folder).

- `projects/examples/generic-dol.yml` is a template for an arbitrary
  DOL and says, in its own comments, to point it at "a legally obtained
  GameCube/Wii main.dol". Its memory config is 24 MB at 0x80000000.
  It requires the DOL's SDA bases (r13/r2, read from __init_registers;
  the translator does not guess them) and takes an optional function
  map; without one it seeds from the entry point and discovers
  functions through the call graph.
- The framework FAQ (docs/WiiCompiled-README.md) answers Brandon's
  question in its own words: "The translator itself handles DOLs and
  RELs generically... The catch is that a playable port also needs a
  runtime: audio, input, GX, everything the game touches."
- The runtime's HLE is Dolphin-OS lineage and covers most of what a
  GameCube game touches, because the Wii SDK is the GameCube SDK
  evolved and Aurora is a GameCube and Wii layer: OS (thread, alarm,
  message, interrupt, cache, context, time, scheduler), GX (FIFO,
  display lists, TEV, textures, lighting, transform), AX audio
  (a full mixer/effects/memory HLE), DVD (storage/dvd.cpp, 1,274
  lines), PAD (input/pad.cpp; the SI MMIO is stubbed, input is
  handled at the SDK-function level), VI.
- A mature project (projects/spm/recomp.yml) shows the per-game
  artifacts a bring-up produces: pinned DOL hash, SDA bases, a
  function map (MAP.txt), a pre-linked REL input, and data remap
  tables (bindiff, datamap, remap CSVs) recording which data words
  need pointer fixups.
- Verified gaps for a GameCube game: there is no CARD/EXI module at
  all (storage is DVD plus the Wii NAND stack), so CTTR's saves need
  a new CARD backend; the mkdd-nx memcard.c is the working pattern
  (CARD API over .gci files). Wii-only machinery (IOS, ESP, SC, NAND)
  exists but is simply never called by GameCube software; any boot
  assumptions around it are a spike-time check, not a design flaw.

## Where the earlier framing was wrong

Two claims from the Nov 1-2 chat answers do not survive the source:

1. "A purpose-built runtime is the decomp timeline." mkdd-nx shipped
   one, on a modern timeline, by porting an existing PC design and
   standing on a mature decomp's symbol map. CTTR has the symbol map
   (the bluisblu decomp's 44,980 named symbols) though no PC
   predecessor project and a third-party engine (Radical Pure3D)
   instead of Nintendo's J-framework.
2. "Failures would surface one crash at a time, invisibly."
   WiiCompiled replaces SDK functions at link level, so the first
   failure layer of a new game is a linker list of missing HLE
   functions: enumerable on day one. Behavioural gaps still surface
   at runtime, but the unknown is bounded far sooner than claimed.

## What survives

- A playable port needs runtime coverage of everything the game
  touches; the framework's own FAQ says so, and both sibling chassis
  confirm it with their HLE/native inventories.
- ModernGekko remains the only stack where CTTR plays today, and the
  only one that handles CTTR's runtime-loaded code generically
  (chunk verification plus a Jit64 fallback; see
  HANDOFF-ADDENDUM-2026-11-01.md). It stays the reference
  implementation: the PC harness pattern in both sibling projects
  (mkdd-nx verifies natives against the recompiled original;
  WiiCompiled verifies against real hardware behaviour) needs a
  ground truth, and ModernGekko is ours.
- Neither route escapes the performance campaign. mkdd-nx reaches
  near-60 at stock through codegen quality (liveness, fast paths)
  plus 113 hand-written natives, not through chassis choice. CTTR's
  measured position (one emulation thread pegged on a 16-thread LOQ,
  ~19 fps in the heavy stretch) implies serious CPU work on the A57
  under any chassis.

## CTTR-specific hard spots, per chassis

- Runtime-loaded code at 0x80369860 (16 KB, invalidated 16 times in
  one logged session, not a REL): ModernGekko covers it with Jit64
  today (at JIT speed; its cost is the open perf question). Both
  AOT chassis need a bespoke answer: identify the blob (it is loaded
  from game data deterministically) and translate it as an extra
  unit, or hand-write what it is. Solvable, and it is CTTR-only work
  neither sibling ever had to do.
- CARD saves: new backend needed in wiicompiled; present in
  ModernGekko (Dolphin) and in mkdd-nx's runtime.
- Audio: CTTR's audio stack is unverified from current evidence
  (which library and DSP microcode family Radical used here). Both
  HLEs are library-specific (AX in wiicompiled; JAudio microcode in
  mkdd-nx), so this is a spike-time identification, not an assumption.
- GX deltas: Flipper GX vs the Hollywood GX both HLEs were tuned
  against. The command model is shared lineage; per-game quirks are
  expected and are exactly what mkdd-nx's per-draw state caching and
  WiiCompiled's per-game GX files (e.g. gx_nsmbw.cpp) exist to absorb.

## The bounded spike (when Brandon wants the answer)

On the LOQ, with his verified main.dol (game data never leaves his
machine):

1. Create projects/cttr in the local WiiCompiled tree: memory 24 MB,
   SDA bases from the DOL's __init_registers, function map converted
   from the decomp's symbol map, allow_unsupported_instructions on
   (the generic template's setting; SPM's strict setting comes later).
2. Run the translator. Output: whether it digests CTTR whole, and any
   unsupported-instruction or data-remap fallout.
3. Build the runtime against the generated code. Output: the linker
   list of missing HLE functions. That list, plus CARD and the loaded
   chunk, is the true runtime gap for this game.
4. Stop there and price it. Booting to first light is a separate
   decision made with the list in hand.

Expected cost: days of iteration, dominated by step 3's list. The
spike does not commit to the route; it converts the chassis argument
into a priced inventory. The Switch platform layer is not part of the
spike cost: spm-nx already runs this framework on Horizon, so a
viable CTTR project would inherit that work instead of repeating the
H0-H4 platform program ModernGekko needs.

## Recommendation

Keep ModernGekko as the reference and the perf investigation's home.
Keep SPM first in the queue. Run the spike when Brandon wants the
chassis question answered with evidence; if its gap list comes back
short (CARD, the chunk, a handful of functions), wiicompiled becomes
the likely shipping chassis for CTTR-NX, with ModernGekko as its
verification oracle. If the list comes back long, HORIZON-SCOPE's
ModernGekko program stands as written.
