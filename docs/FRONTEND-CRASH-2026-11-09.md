# Run 345 crash -- dump read (Nov 9, 2026)

Source: the run 345 crash folder (crash_missing_target.txt), console-345.log,
cttr-witness.txt and the mem1.bin snapshot from the same run. Build:
batch-310 exe, same as passes 343/344.
Run config: CTTR_PAD_SKIP=1 (A then Start at boot) + CTTR_PAD_PULSE=1 (Start every 15 s) -- first run with either.

## Correction to the first report

The fatal is NOT an access violation at 0xFFFFFFFF. That value was stack data.
The actual fatal is `missing_target`: InvokeIndirectCpu tried to execute guest
address 0x0, which is not translated/registered. PC=0, LR=0x801CE584, CTR=0.

## The crash, named

Call chain (guest backchain, verified in shards):

main (fn_8018BB98) -> fn_80070264 -> fn_8008D278 -> fn_80162B5C -> fn_80164888
-> fn_801CDF54 (pure3d::frontend::Parent draw) -> fn_801C9FCC
(pure3d::frontend::Menu draw, vtable 0x803D36E8 slot+32) -> virtual child
draw at vtable+32 -> fn_801CE4D0 (pure3d::frontend::Text draw,
vtable 0x803D47DC slot+32) -> CRASH at loc_801CE568.

- Menu object: 0x80FA4BA8 (pure3d::frontend::Menu). Its child array at
  [Menu+112] = 0x80FA4D90: child 0 = 0x80FA4C30 (pure3d::Font), child 1 =
  0x80FA4CF0 (the crash Text), then a 0 terminator. Loop index at crash: r29=1.
- Crash Text: 0x80FA4CF0, pure3d::frontend::Text, type field [this+4]=2,
  dims 64x64 ([this+88]=0x00400040), colours [this+80/84]=0xFFAA70AA,
  [this+136]=0.5f.
- Crash site, loc_801CE568 in func_801CE4D0.cpp (shard_d10804887dbe024e7818206a.cpp):
    r3  = [this+132]          ; = 0x80E5CE38
    r12 = [r3]                ; = 0x11111111 (a pixel word)
    r12 = [r12+96]            ; read via 0x11111171 -> 0 in this memory system
    ctr = r12; InvokeIndirectCpu(ctr)   ; ctr=0 -> missing_target, LR=0x801CE584
  In a healthy Text, [this+132] is a pure3d::Sprite object (vtable
  0x803DF7A4), and vtable+96 = fn_801CEC90 is the intended target.

## What [this+132] held instead

0x80E5CE38 is raw image/pixel data, not an object: words 0x11111111,
0x00110011, 0x10101010, 0x00100010... continuing for kilobytes, in the
0x80E0-0x80E9 image-data zone. The same pointer is also in a global pointer
table at 0x80FC87C8 (a list of image buffers) and at [Text+144] (same field
mirrored). No object header exists at or before it.

## This is not a one-off corruption

Census of all 226 pure3d::frontend::Text instances in mem1.bin at crash:
- 99: [this+132] = 0 (null -- Text draw early-outs, safe)
- 82: [this+132] = a real pure3d::Sprite (29 distinct Sprite objects)
- 45: [this+132] = raw image data (18 distinct buffers, all in the image zone;
  e.g. 0x80E1F1F8 x15, 0x80E2BAA0 x7, 0x80E5F2C8 x6; crash instance is the
  only type-2 among the raw set, the rest are type-1)

So a whole subset of frontend Texts carry an image-data pointer where the
draw path expects a Sprite object. Any of them is a crash waiting for its
Menu to be drawn; the crash one was simply the first raw Text in a Menu
actually drawn.

## Timeline / press stage

- Attract phase ran normally to ~t=330 s: last [w212] t=330347ms, bink=750,
  pad=3205. Bink, glue and the loader pump (frozen at 429,892) all stop
  advancing after ~t=330-341 s -- the movie phase ended and the frontend
  took over. That is the input effect: in passes 343/344 (no input) bink
  climbed past 25,000 and never stopped.
- Frontend then rendered for ~100 s: 180 "[vi] slow frame (frontend)" lines,
  mostly ~53-114 ms frames (a few up to ~477 ms during load).
- Last witness sample t=431340ms (all loader counters frozen, handlers
  balanced 53/53, push=pop=12,467, zero [w282] heals -- no spray, no wedge
  recurrence). Crash followed shortly after, on a frontend draw frame.
- Which individual Start pulse (15 s cadence) opened the crash Menu cannot
  be isolated from the counters: the pad counter is only sampled with the
  movie-phase [w212] poller, which stops at t=330 s. What is proven is the
  stage: movie -> frontend transition at ~330 s, then a Menu draw in the
  frontend phase, child index 1, Text draw, first raw-Sprite virtual call.

## Open question (next hunt, in order)

1. Why do 45 Texts get an image pointer at +132 instead of a Sprite object?
   Candidates: the resource/loader path that resolves a Text's sprite
   returns image data directly for one package/class of images, or the
   Sprite creation step for those images is missing in this build.
2. Are raw Texts ever drawn on real hardware, i.e. is +132=raw an illegal
   state the game itself never produces? The census pattern (shared
   buffers, repeated across identical Texts) suggests a systematic loader
   outcome, not random corruption -- no spray/heal activity in run 345
   supports that.
3. Fix neighbourhoods (decide on evidence from 1): repair the resolution
   path so +132 is a Sprite, or guard the Text draw's virtual call the
   way batch 310 guards the Bink destination -- the guard is the fallback,
   not the first choice.

## Loader hunt findings (Nov 9 evening, from the crash snapshot + shards)

- Text object model decoded: ctor fn_801CE3B0 (only caller: chunk loader
  fn_801CC498); element vector inline at Text+112 {begin,end,cap} with
  elements stored at Text+144 onward; SetIndex fn_801CE5C8 copies
  vector[index] into Text+132 and calls vtable+48; Draw fn_801CE4D0
  resolves +132 via SetIndex when null, then calls [elem] vtable+96/+40
  as a pure3d::Sprite (vtable 0x803DF7A4).
- fn_801CE840 (called only by the chunk loader) appends the inventory
  Find result (fn_801CECCC -> fn_80242FD0 Radical hash -> inventory
  vtable+20) via push_back fn_801CEB84, then UNCONDITIONALLY AddRefs it
  (obj->vtable+8). A raw pointer returned by Find would have died in
  that AddRef at load; run 345's console has exactly one missing_target
  line (the Draw crash). So raw elements most likely entered the
  vectors AFTER append, or through a route other than fn_801CE840.
- Census of the snapshot: 226 Texts; +132 = 99 null / 82 Sprite /
  45 raw; slot+144 = 162 Sprite / 64 raw; 18 distinct raw buffers, all
  in 0x80E0-0x80E9, shared across Texts; zero pure3d::Image objects
  exist in memory. Raw buffers are referenced only from Text vectors
  and one big pointer array at 0x80FC8000+.
- Console: exactly 5 unmapped-touch warnings; three at fn_80163860 /
  lr 0x801638B4 read pixel words as addresses (0x0D010103, 0x0E000000,
  0x22132213 = first word of raw buffer 0x80E1F1F8). fn_80163860 is a
  named-resource resolution helper that reads [obj+132] at entry;
  still unclassified, second suspect after the loader path.

## Batch 311 (applied Nov 9; built and run as run 346)

Witness only, no behaviour change. patch-textprov311.py (mock-tested
first, APPLIED; backups .bak-pre311 on both files):
- os_init.cpp: CttrLog311Append / CttrLog311Resolve / CttrLog311Draw
  writing [w311a] / [w311r] / [w311d] to cttr-witness.txt.
- shard_d10804887dbe024e7818206a.cpp: call in fn_801CE840 right after
  the Find returns (before push_back/AddRef), call in fn_801CE5C8
  right after the Text+132 store, call in fn_801CE4D0 at the head of
  loc_801CE568 (logs only non-Sprite elements, deduped per pair,
  with idx and vector slots).
Discrimination: [w311a] raw at append => Find/inventory is the root.
[w311a] clean but [w311r]/[w311d] raw => the vector is overwritten
between append and draw. The build ran in parallel under the Nov 9
parallel-build ruling; run 346 used the run 345 configuration.

## Desk check while batch 311 waits for a build slot (Nov 9)

- fn_801CE894 (Text vtable+48, called by the resolver right after every
  +132 assignment) is a layout refresh: reads +132, calls the selected
  element's vtable+88 (bounds), rescales the Text rect at +100/+104
  using the +136 factor and +88 dims, calls fn_801C7204. It never
  writes +132 or the vector. It is a consumer: a raw +132 at resolve
  time would crash HERE (vtable+88 call), not in Draw.
- fn_801CE6E0 (Text vtable+40) resolves +132 via fn_801CE5C8 when null,
  then calls [elem] vtable+96 like Draw does. Also a consumer only.
- Run 345 crashed in Draw's own loc_801CE568 call with the resolver
  path already returned, so at that Draw's resolution moment the
  element was valid (or +132 was pre-set nonzero). The raw value
  reached +132 without passing through a live resolver+CE894 pair,
  or the vector slot it was copied from turned raw after an earlier
  clean resolve with the same index (resolver early-outs when the
  index is unchanged and +132 is nonzero, so a slot that turns raw
  later is never re-validated). Batch 311's three logs discriminate.

## Run 346 verdict (Nov 9, batch 311 witness) -- the pointer was never wrong

Run 346 (batch 311 exe, same PAD config) crashed identically:
[w223] missing-target, active=fn_801CE4D0, lr=0x801CE584, ctr=0,
r3=0x80E5CE38, Text 0x80FA4CF0, Menu 0x80FA4BA8, child idx 1.
New crash folder: base_1794272081_pid48524. Witness:
cttr-witness-346.txt (7,670,404 B), kept with the local run evidence.

The three-stage witness settles the loader question:

- [w311a] appends: 536, covering 226 distinct Texts, 174 distinct
  Sprites. EVERY Find result was a genuine Sprite (vt=0x803DF7A4).
  The inventory/Find/loader path is CLEAN. There is no raw-append.
- [w311r] resolves: 127, every one a genuine Sprite. SetIndex never
  copied a raw pointer into Text+132.
- [w311d] poisoned draws: exactly 1, the crash itself.
  text=0x80FA4CF0 idx=0 elem=0x80E5CE38 vt=0x1E151E15 (pixels),
  slots: 0x80E5CE38 0 0 -- vector and +132 still hold the CORRECT
  pointer at draw time.
- The crash Sprite's own paper trail: appended once (n=251,
  text=0x80FA4CF0, obj=0x80E5CE38, vt=0x803DF7A4, w4=1) and resolved
  once (n=36, same address, vt=0x803DF7A4), on consecutive witness
  lines 58008/58009. Alive at load, alive at resolve, dead at draw:
  the Sprite OBJECT AT 0x80E5CE38 was overwritten in place by
  texture data between resolve and draw. The Text, its vector and
  the resolver are all innocent.

Census of run 346's crash snapshot (mem1.bin) over the 174 appended
Sprites: 96 alive, 78 dead (first word now pixel data). The dead
form a CONTIGUOUS span: every appended Sprite from 0x80E0A478 to
0x80EDCF98 is dead (regular ~0x2270 stride, the frontend package's
in-place object layout), alive again from 0x80EDD828. A second
contiguous dead run sits at 0x80DC39D8-0x80DF9FE8. Two scattered
deaths elsewhere look like ordinary heap reuse (one now holds an
"art/..." path string). Re-reads run 345: its 18 "raw buffers" are
the same dead Sprites (0x80E1F1F8 was resolved alive in 346 at
n=29/33, and was pixel data in 345's snapshot).

Mechanism, current best statement: during the frontend phase,
texture data (GX-tiled index data) is written across a ~1.4 MB
contiguous span of the frontend package's object region,
destroying every Sprite object in the span in place. Texts keep
correct pointers to dead objects; the first Draw through one
dies. Open sub-question: is the write (i) a Pure3D texture
conversion landing on a wrong destination (the [P+84] path,
batch-209 country), (ii) the package spool being reused for
textures while its objects are still referenced, or (iii) a host
GX-bridge upload computing a wrong guest destination?

## Remaining work and how it is typically completed

1. Catch the writer (next witness step, batch 312 candidate):
   flip-watch poller on the deterministic victim span (same
   addresses died in 345 and 346). Sample [0x80E5CE38] and a few
   span neighbours each poll tick; on the vtable-to-pixel
   transition, dump guest fiber stacks (batch 296-298 tech) plus
   poller counters. If the writer is guest code, its stack names
   it. If the stacks show nothing, the writer is host-side: add a
   range watch in the GX bridge upload path logging any upload
   whose guest range intersects the victim span.
2. Fix at the source once the writer is named (wrong destination,
   arena bound, or spool lifetime), proven by a pulse run that
   survives the frontend and a soak.
3. Fallback if the writer stays elusive: batch-310-style
   point-of-use guard in Text Draw/SetIndex (skip elements whose
   vtable is not the Sprite vtable). Proven pattern in this tree;
   menus would render with the dead Sprites' images missing but
   stop crashing, unblocking the menus/gameplay milestone while
   the root hunt continues. Decision is Brandon's, after step 1.
4. After the frontend survives: Bink colour conversion (attract
   movie plays as unconverted static), input-driven menu
   navigation, gameplay entry -- the milestone picked Nov 9.
5. Parked: descriptor-flip writer (harmless since batch 310),
   Phase 5 disposal and diagnostic cleanup (Brandon's calls).
