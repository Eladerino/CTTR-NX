# Writer hunt -- consolidated brief (Nov 7-9, 2026)

Purpose: one page that consolidates everything proven about the corruption
that has driven the CTTR campaign's failure classes, so the hunt resumes
from facts, not from the retracted readings. Sources: god-drip-callers.md,
rampage-anatomy-292.md, batch272-module-walk-latch.md, runs 288-303 records.

## The theme

Guest OS/container structures end up holding **data dwords that are then
dereferenced as pointers**. Three manifestations, all proven at the level
stated; whether they share one writer is NOT proven.

## UPDATE 7 (Nov 7, runs 312/313 + batch 282): the wedge mechanism is PROVEN

313 froze with lastCur=DF30 (sane), lastRun=0x009E009E (spray,
stuck), mismatch=701. SelectThread's gate returns "no switch"
when cur != run, and SelectThreadSwitch -- E4's only routine
rewriter -- sits behind that gate: a stuck poison is a
deadlocked fixed point. THE lost wakeup, unified across
311/312/313. The shield (280) loses the streaming race
(open-page window; 313's E4 stayed poisoned after a logged
restore). Volleys are byte-identical across runs (determin-
istic attract-loop stream). Batch 282 heals the gate itself:
implausible nonzero context word -> trust the plausible side,
else the 275 fiber resolver, write back, log [w282]. Run 314
soaking on it. The writer's name is still open, but with the
gate healed its sprays should be survivable noise.

## UPDATE 6 (Nov 7, run 311 + batch 280): abandonment exonerated; the shield now guards the words

Run 311 (batch 267): stall ~451 s, [w267]=0, [w252]=0 -- the
switch-abandonment exits (deferred / no-fiber / invalid) NEVER
fired. The phantom class is closed with direct evidence.
[w278] fired 25x, all step 0, same stream values -- the list
head is sprayed all run. End state: B957 WAITING on Q, DF30
WAITING with resume inside the GOD lock wrapper (mutex-block
silhouette pointing at the GOD/Bink IO chain).
Batch 280 (run 312 soaking, mappings=40 confirmed): the
watch-4 shield now covers 0x800000D4/DC/E0/E4 (kind 1) and
page 0 is armed. A sprayed write is restored in place AND
logged with the writer's RIP + guest active/pc/lr -- the
writer hunt's missing instrument.

## UPDATE 5 (Nov 7, runs 310/311): guards cleaned the noise; 267 soaking

Run 310 (batch 278): stall ~355 s, lost-wakeup silhouette, AV
dumps ZERO. [w278] reconcile fired 6x -- the thread-list HEAD
word itself held 0x1F401F40 (step 0). Insert guard silent.
Batch 267 implemented in revised shape (design doc has the
note): SwitchResult + HasUsableFiber gate + [w267] post-commit
failure logging with LoadContext rescue; the rollback loop was
not built because batch 150 already guards the scheduler entry
against dispatcher-fiber picks. Run 311 soaking on it; [w267]
and [w252] censuses decide whether abandonment is real.

## UPDATE 4 (Nov 7, run 309 + disassembly): UPDATE 3's site attribution was WRONG

Disassembly of the 309 exe places the Read16Slow call at
SelectThreadSwitch +0xF5 inside the batch 252 RECONCILE's
thread-list walk (s_phantom252 is referenced at +0x116), not
the pick loop. The walk faults on a thread-list node holding a
data dword, inside its try/catch: the 307/308 dump floods were
per-switch noise, not the wedge. Run 309 (batch 277 build,
[w277]=0 -- the pick guard never engaged) stalled at ~356 s
with the lost-wakeup silhouette: B957 asleep on Q, VI balanced.
Batch 278 (run 310 soaking) guards the reconcile walk and
InsertThreadIntoQueueByPriority (os_thread.cpp), whose
unchecked walk can mis-link a sleeper behind a data node --
the standing lost-wakeup candidate. The pick guard stays as
defense. What survives from UPDATE 3: both fault shapes do
enter through OSSleepThread's SelectThread call, and data
dwords do sit in OS lists; the faulting reader is the
reconcile, and the wedge is a wakeup that never lands.

## UPDATE 3 (Nov 7, run 308): Defect B's site PROVEN at instruction level

Both wedge fault shapes resolve (nm308) to SelectThreadSwitch
+0xF9: the pick loop's Read16(nextThread + kThreadStateOffset),
reached from OSSleepThread_HLE +0x660. Fault addr = candidate +
0x2C8 exactly; candidates are data dwords from a deterministic
stream (identical across runs). No catch inside the scheduler
and the read precedes the pop, so the sleep's catch aborts and
the retry re-picks the same head: the livelock. Batch 277
(applied; run 309 soaking) validates the candidate before the
state read and discards implausible heads without dereferencing
them ([w277]). Run 308 also showed batch 276's sleep half
working (297 VI-queue resolutions, 0 aborts) and doubled
survival to ~891 s -- the pick loop was the remaining door.
Still unknown: who inserts data dwords into run queues.

## UPDATE 2 (Nov 7, runs 307/308): two defects, separated

Defect A (the drip) is CONTAINED: run 307 on batch 275 shows zero
lock damage ([w256]=0, quarantine=0, AV 17, [w275] 299 resolutions,
0 aborts). Defect B (the wedge) is independent: 307 still stalled
at ~446 s, damageless. Its mechanism, decoded from 307's 17 dumps:
OSSleepThread_HLE trusts the same poisonable ctx word -- it writes
state at poisoned+0x2C8 (len=2) and links the phantom into a real
wait queue; WakeupThreadQueue then faults on Read16(phantom+0x2C8)
in alternation with the sleep side, a fault-retry livelock.
Batch 276 (applied; run 308 soaking) resolves the ctx word in
OSSleepThread the same way and makes WakeupThreadQueue clear +
log ([w276]) any queue with an implausible head or a capped
cycle. Batch 267's SelectThreadSwitch gate remains the candidate
for stopping the ctx word from being poisoned via a sprayed
run-queue head.

## UPDATE (Nov 7, run 306 + batch 274/275): the drip's engine is the poisoned running-context word

Batch 274's HLE-entry validation caught it: the lock pair's
currentThread, read from the running-context word 0x800000E4, is
sometimes a DATA DWORD (0x00100010, 0x00790078, 0x003C003C,
0x00270027; 299 capped log lines in run 306 alone). The phantom
thread's fields at data+0x2F4 resolve through the physical alias
into the static character buffer, so lock/unlock surgery runs
against the buffer and sets mutex owners to data values. The next
SelectThreadSwitch rewrites the word -- intermittent, self-healing;
survivable (306 passed with bink 30,679) or lethal (304/305)
depending on what the surgery hits. Batch 275 (applied, run 307
soaking) resolves an implausible word against
Fiber::GuestFiberManager::GetCurrentGuestThread() and aborts when
no plausible fiber thread exists. WHO writes data over the ctx
word remains unknown -- a sprayed run-queue head committed by
SelectThreadSwitch is the concrete candidate (batch 267's gate).

## Manifestation 1 -- the drip (deterministic, load era, every run)

- A thread's owned-mutex list (head/tail at TCB+756/+760) or a mutex's link
  fields (+16/+20) come to hold dwords from a static character/gradient
  buffer (MEM1 0x80072F8C-0x80103C1C): 0x41434244 "ABCD", 0x42444345
  "BCDE", even a PPC instruction word 0x7C0802A6.
- Exercised by the file layer's lock cycle (GOD statics mutex 0x804478A8,
  MQ 0x80B9547C) from console line ~17,851 onward; byte-identical values
  and order across runs 288 vs 293. In-range dwords are traversed silently
  and the link stores scribble real mutex pointers into buffer words
  (two-way corruption); out-of-range dwords produce the visible touches.
- Pre-265 this walked inside the guest's own OSLockMutex; since batch 265
  the HLE pair walks it, and batch 266 quarantines only an implausible
  ENTRY owner. A drip-fed list can still fault the HLE walk at a deeper
  node (the walk reads mutex+0 of each node) -- that exposure is real but
  has never been the observed storm site.
- Entry point unknown. The god-drip-callers.md §7 experiment was BUILT as
  batch 261: all six words are in the watch-4 table (s_crit254 in
  guest_flat_memory.cpp), and the checker is a shield -- it restores the
  last good value and logs [w256] with writer RIP + guest active/pc/lr.
- What the shield data from runs 298/303 proves (probe304b/c/d, Nov 7):
  the ONLY drip words that fire are MQ prev (0x80B95490, 243 catches in
  303 / 375 in 298) and GOD mutex prev (0x804478BC, 2 per run). DF30's
  head/tail never fire. MQ prev is always written FROM 0 TO a data dword:
  0x10101010 dominant (108/208), doubled-u16 patterns (0x00170017,
  0x00450045), arbitrary data dwords. Guest context: active =
  fn_8023B314 with lr = 0x8023A734 (the Q post helper fn_8023A700's lock
  return), i.e. the write happens INSIDE OSLockMutex(MQ) -- the HLE lock's
  LinkMutexToThread writing the caller's owned-list TAIL into MQ+0x14.
  Conclusion: **the posting thread's owned-list tail holds data dwords**
  at post time. The poster is the movie glue thread B957 (0x80B957D8);
  its owned head/tail (0x80B95ACC / 0x80B95AD0) are NOT in the watch
  table -- that is the batch 273 gap (design:
  batch273-b957-owned-watch.md). Host RIP resolution from logs is
  blocked by ASLR (no recorded base for the RIP's module); the guest
  lr/active evidence is stronger anyway.
- 0x10101010 is also the fake module-list head value (manifestation 3):
  the same data word feeds both fake structures, suggesting a common
  data source rather than independent sprays.

## Manifestation 2 -- the rampage (runs 288, 292)

- fn_802C4F28 (0x802C4xxx Lua-region container helper) is called once
  (lr 0x802C4ED4, stack 0x804C1F10) with a garbage object (first read at
  0x41C00030) and fills 8-byte elements monotonically from 0x01800000 to
  the MMIO boundary 0xCC000000: 45,575 first-touch warnings, ~2.78 GiB of
  host blocks committed by the runtime's absorption policy, which is what
  actually kills the process.
- The caller at 0x802C4ED4 and the source of the garbage object were never
  identified. Onset sits inside the storm endgame, concurrent with (not
  caused by) the presenter's retrace fault loop (see manifestation 3).
- Not a drip escalation: 293 had the identical drip and no rampage.

## Manifestation 3 -- the module-walk storm (runs 301, 302; likely 292's loop)

- LogGuestModulesOnce (vi.cpp) walks a "REL module list" from the head
  pointer at 0x800030C8 on every AdvanceRetrace. **Its premise is void in
  CTTR**: CTTR is a single-DOL game, and the word at 0x800030C8 is
  0x10101010 in every run checked -- not a module pointer. The walk's only
  output in healthy and storm runs alike is one line: "REL module 0
  (unexpected) linked at image 0x10101010 ... MISMATCH".
- The walk interprets the data behind that word as module structs. When
  the +0x04 "next" word holds an unmapped media-pattern value
  (302: 0x311C321D; 301: 0x6CB66AB4; cf. 292's presenter loop at
  0x19191919/0x18181818, host site never resolved for 292), each retrace's
  walk faults once at module+0x00. Memory::TryRead32 handles the fault,
  but ResolveRegion prints a full ~129-line dump before throwing, and the
  walk's only early-out (module id 1 reported) never fires in CTTR -- so
  the fault repeats every retrace for the rest of the run: ~120k dumps,
  1.7-1.9 GB consoles, heavy host CPU/IO burn on the scheduler path.
- Run 298 (pass) had the same fake walk but a walk-safe +0x04 word:
  7,698 diffuse dumps, top address 376.
- Batch 272 (applied Nov 7) latches the walk settled on first failure or
  completion. Run 303 (soaking, verdict ~08:27 NST Nov 7) discriminates
  whether the flood itself wedges the guest or is a sibling symptom.
- No watch needed for this family: 272 retired the amplifier, and the
  "list" being fake means there is no real structure to protect. The
  varying +0x04 word is data in some buffer the game writes; identifying
  that buffer (phys 0x00101010 area, if the alias reading is right) is a
  curiosity, not a stability lever.

## The wild unlock (runs 303/304, decoded Nov 7 from console-304)

Both consoles end their OS traffic with "[os] OSUnlockMutex: memory
error at 0xE8FF7ED9" (14 mentions in 304). The preceding AV dump header
identifies it exactly: active = 0x80348B10 (OSUnlockMutex), lr =
0x8024C9D0 (the unlock call inside the fn_8024C9A0 wrapper family),
guest r31 = 0x80B93A50 (inner GOD object +0xC), r30 = 0x804478EC (GOD
statics area), r1 = 0x804C20D8 (the presenter-family stack). So a GOD
mutex unlock's list surgery touches 0xE8FF7ED9 -- a deterministic data
value sitting in a link field at surgery time, on a path the watch-4
shield does not intercept first. In 303 the guest ran 18 more healthy
minutes after it; in 304 the stall followed within ~30 s. It is a
member of the drip family (data dword in a mutex link), not a separate
bug, and it is the strongest single marker that the lock lists still
take damage the current shields don't cover.

## What is NOT proven

- One writer vs several. The drip's data source is a static character
  buffer; the storm/rampage values are media-pattern (u16 sample pairs).
  Different data, same shape (data-as-pointer). A single misdirected copy
  class (the batch 209 palette-fread failure shape) could feed both.
- Whether the guest wedge in 301/302 (~370-380 s heartbeat stop) is the
  flood's host burn or a separate spray victim. ANSWERED by runs
  303/304 (Nov 7): the wedge occurs with NO flood (304 stalled at
  ~440 s, console quiet, VI healthy, thread list intact -- a
  lost-wakeup silhouette), and a full pass occurs on the same build
  (303). The flood was an amplifier/sibling, never a necessary cause.

## Next actions (in order)

1. Run 303 verdict: PASS (Nov 7 ~08:29 NST) -- full soak, best bink
   19,895, storm dead. Run 304 confirmation soak in flight.
2. Batch 273 (B957 owned head/tail added to s_crit254) ran in 305 and
   caught ZERO -- the checker samples after a watched-page write lands,
   and the linking lock overwrites the tail with the mutex it just
   linked, so a bad tail is always consumed before any sample. Page
   watches cannot win this race (same reason DF30's tail never fired).
   Superseded by batch 274: log-only validation at HLE lock/unlock
   ENTRY (os_scheduler.cpp B274CheckEntry -- caller head/tail + mutex
   next/prev read before any surgery, [w274] line with guest lr on
   any implausible field). Run 306 (launched Nov 7 ~09:58 NST) is its
   first soak.
3. Batch 267 phantom root fix (design drafted) -- independent hardening.
4. If a future run stalls quiet, read the wedge from its clean console
   first -- that evidence outranks all of the above.

## UPDATE 8 -- runs 314-317: layer 1 fixed, layer 2 localized to one call (Nov 7, 2026)

Layer 1 is the gate deadlock (UPDATE 7): batch 282 heals it ([w282] 50/104/133 heals in 314/315/316, clean books). Layer 2 killed 314/315/316 identically at guest ~330-340 s and batch 283 cleared the switch layer ([w283]=0 -- no LoadContext borrow, no cross-thread AlreadyCurrent; every B957 switch is a real fiber switch).

Run 317 (batch 284 spin witness in the glue loop) named the call: the loop is func_800B9558 at loc_800B9674; its virtual target is fn_80242B9C (vtable 0x803E2BC4 slot +120; host-read slot == guest target, vtable intact). fn_80242B9C thunks to fn_80239F04 on [obj+12]; that makes two vtable calls on the embedded helper at subobj+12 (slots +8/+12) and returns byte [subobj+84] -- the loop's exit flag. Shape: at ~330 s the completion flow breaks (Q ends count=4/pending=4), the flag stays 0, the helper's calls return instantly (spin burst, 10k+/s, ~75k iterations in 5 s), then one call blocks forever in OSWaitSemaphore and the guest freezes (glue counter stops; last heartbeat t=330 s in 317). Disp (fn_8024F5A0 entries) stops at 161 in the same window -- cause or starved effect still open, but the question now has addresses. Next: batch 285 extends [w284] host-side (sub, helper vtable, slot targets, +84 byte) and the hunt moves to whoever writes [subobj+84] and why the posts stop landing.

## UPDATE 9 -- run 318: the spin is the engine's own mutex poll (Nov 7, 2026)

[w285] resolved fn_80239F04 completely: its two vtable calls are this-adjust thunks to fn_8023E7D4/fn_8023E7F8 = fn_8024C9A0 (OSLockMutex) / fn_8024C9C0 (OSUnlockMutex) on the manager mutex at 0x80B9547C. The function is Lock -> read flag byte [0x80B93A98] -> Unlock -> return flag. The glue loop is a designed poll, paced in health by mutex contention and prompt flag sets. At the break the worker side stops: dispatcher entries (fn_8024F5A0) freeze at exactly 161 in all five deaths (314-318), Q reads count=0/pending=0 at spin detection (the 4/4 end state is later accumulation), the flag never sets, the mutex goes quiet, and the movie thread free-polls at 10-30k/s until (in some runs) a final lock blocks forever. Batch 286 polls f84/mutex owner+count/Q every 250 ms on change; run 319 will show the healthy rhythm and the exact break order. The remaining question is the worker side: who sets [0x80B93A98], and what kills its trigger at ~330 s.

## UPDATE 10 -- the dispatcher is a coroutine that never gets switched back (Nov 7, 2026)

Anatomy rounds 1-2 (dispatcher-anatomy-318.md, dispatcher-anatomy2-318.md) rewrote the worker-side picture. fn_8024F5A0 drains a ring buffer (this+24) of 8-byte items, gated at entry by byte [this+1]; its heartbeat ticks per iteration, not at entry. Its empty-ring path fn_8024FA94 performs the engine's hand-rolled context switch (fn_8024C870 = OSSaveContext/OSLoadContext pair) to a peer context (fixed object 0x80450058) when the ring is empty but an item is still marked current at [this+12]. Nothing in the subtree contains an OS wait. So the frozen count at 161 means the dispatcher was switched away (or gated, or simply stopped being called) and the return switch never happened -- a cooperative-scheduling starvation across the engine's own context system, layered over the OS threads. The dispatcher itself never touches the flag, the manager mutex, or Q. Batch 287 captures the dispatcher object at its beat site so the [w286] poller can watch its gate byte, current item, and ring head/tail alongside f84/mutex/Q in run 319.

## UPDATE 11 -- run 319: the break, in order (Nov 7, 2026)

The [w286] timeline (f84 / manager mutex / Q / dispatcher gate+cur+ring) shows a healthy machine until t=320,304 ms: items cycling through the dispatcher (cur changing, head/tail advancing together, Q flickering, DF30 holding the mutex in bursts). At 320,304 ms every sampled field freezes: ring empty (head==tail=0x80943DA0), cur stuck at item 0x807121D0 (never cleared; in health it clears between items). The dispatcher iterates ~5 more times over 17 s (disp 156 -> 161 -- mostly switched away on the empty-ring path, whose switch arm requires exactly cur != 0), the movie thread's poll accelerates without contention, bursts ([w285], 4,826 calls), then blocks forever in OSWaitSemaphore while 4 posts accumulate unconsumed (320-339 s). f84 never rose all run. Layer 2 is now: one item's processing stops the completion flow -- the item is 0x807121D0. Batch 288 adds the current item's header (vtable, type at +20) to the poller so the next run names it.

## UPDATE 12 -- run 320 verdict (Nov 7, 2026)

Seventh consecutive layer-2 death, same shape: MAX BINK 1,020, dispatcher frozen at 161 iterations, the same item object stuck current (0x807121D0, descriptor 0x803E3FDC, state 2, refcount 2, state-3 stamp absent). Campaign paused for the night at Brandon's call; run 321 (stage breadcrumbs + item filename) is staged.

## UPDATE 13 -- run 321: stage 2, frontend.p3d (Nov 8, 2026)

The stage breadcrumbs and filename dump landed. The fatal item (same 0x807121D0) froze at stage=2: the state-2 set and the extension-handler lookup returned, the state-3 set never ran. The park is inside the two virtual calls, with the slot+20 completion call at loc_8024F6A0 the prime suspect. The item is the load completion for **sound/scripts/sfx/frontend.p3d**, the frontend SFX script package. Batch 291 will capture the handler object and its slot+20 target per item; a static hunt for the .p3d handler registration runs in parallel.

## UPDATE 14 -- run 321 verdict; campaign paused (Nov 8, 2026)

Formal counts: witness 11 MB, MAX BINK 1,462, dispatcher frozen at 161, glue count 484,342 and still climbing at the kill, AV 0. Brandon paused CTTR runs Nov 8 21:05. Staged for the resume: batch 291 (stage-6 marker at loc_8024F6A0 entry plus CttrDispHandler291 capturing item/handler/slot+20 target per item) mock-passed against the real shard span, and the run 322 script set. First action on resume: apply 291, build, launch 322, read hdl=/tgt= on the stuck item's [w288] lines.

## UPDATE 15 -- anatomy round 4: the slot+20 handler's wait loop is the park (Nov 8, 2026)

Full report: dispatcher-anatomy4-322.md. fn_800A7798 (the slot+20 completion handler; the frontend fighttree items' target, handler obj 0x809514C0) opens with a readiness wait loop (loc_800A7810/7800/780C): it polls the per-file device object (resolved by filename via fn_8023BA20 into a stack handle) at vtable slot+88; the ONLY exit is that call returning a nonzero low byte -- no counter, no timeout. On iterations where the poll returns 0 AND the byte at [item+300] is 0, it pumps the peer queue: fn_8024F278 -> fn_8024FA00 -> (one branch) fn_8024FA94 -> fn_8024C870, the hand-rolled context switch. If the switched-to peer never switches back, the handler never returns and the dispatcher stays mid-item -- exactly the 319-321 signature. Second sub-mechanism in the same loop: slot+88 never reports ready at all. Other round-4 facts: the handler writes [item+296]=2 at entry and [item+24]=new child via fn_8025130C, writes NOTHING to the handler object, and NEVER writes [item+20] (so a normal return always leaves state 2 for the dispatcher's own state-3 step; frozen state 2 means "never returned", no partial signalling). fn_80339354 = sprintf and fn_800C88B4 = GlobalFightTreeNode_Get (named symbol entries). No filename-content branching anywhere in the handler: per-file divergence is entirely inside the resolved device object's vtable. Open: who writes the [item+300] pump-gate byte; whether frontend.p3d's handler/target match the fighttree items' (run 322's capture answers).

## UPDATE 15 -- run 322: park confirmed inside fn_800A7798; fatal file varies (Nov 8, 2026)

Run 322 froze with stage=6 on the stuck item and hdl=0x809514C0 / tgt=0x800A7798 captured: the dispatcher entered the slot+20 completion handler and never returned. This run's fatal file was pasadenaFrontEnd.fighttree, NOT frontend.p3d (no p3d [w288] line exists in 322) -- so the defect is not file-specific; it is the handler's readiness wait loop (loc_800A7810, anatomy round 4): poll handle+88 forever, pumping fn_8024F278 → fn_8024FA00 → fn_8024FA94 → fn_8024C870 (context switch) on gated iterations. Two sub-variants remain: (a) the pump switches the dispatcher task away and it is never switched back; (b) the device readiness (+88) simply never fires and the loop polls (with the switch as a bystander). Next instrument, when runs resume: discriminate (a) vs (b) -- e.g. capture the stuck item's handle pointer and [item+300] byte in the poller, and/or count fn_8024C870 entries from the dispatcher context. Fix neighborhoods: host fiber/context-switch layer for (a); the GOD device readiness path (what should set +88 ready for a completed local file load) for (b).

## UPDATE 16 -- run 323: nested-wait candidate eliminated; stream loop stands alone (Nov 8, 2026)

Run 323 died on frontend.p3d inside fn_80250C24 (stage 6) with batch 292's wait counters at ZERO for the entire run -- fn_800A7798 was never entered, so round 5's unifying candidate (a per-entry call nesting into the fight-tree wait loop) is eliminated for the .p3d deaths. The .p3d park is fn_80250C24's own stream loop (loc_80250D6C → loc_80250FA4): continuation needs fn_8024E7DC nonzero AND [item+20] != 4; the cursor is stepped by fn_8024E850/fn_8024E9EC. Layer 2 therefore has two independent park sites with one signature: (1) fn_80250C24 stream loop (.p3d class; runs 319-321, 323), (2) fn_800A7798 readiness wait loop (fighttree class; run 322; sub-variant split still open -- 323 never reached a fighttree item). Round 6 is reading the stream helpers and the +28 child constructor to find why the cursor stalls.

## UPDATE 17 -- Run 324: the wait loop never runs, anywhere (Nov 9, 2026)

Run 324 (batch 293) died on pasadenaFrontEnd.fighttree via fn_800A7798 again (twin of 322), disp 161, MAX BINK 1503.

- **[w293] stream counters stopped at push=pop=8,400** -- every .p3d walk in 324 completed (a mid-walk sample showed a healthy frame: dep=3, flen=fown=32912). Round 6's zero-length fixed point did NOT fire; it remains unproven in any run (323's god62/63 caps died too early to confirm it there either).
- **[w292] wait counters were ZERO for the whole of run 324** -- as in 323. But 324's fighttree items demonstrably flowed through fn_800A7798 (captures + advancing stamps) and one froze inside it. The generated entry block gotos the loop head unconditionally; the hook is present in the patched shard, the object rebuilt after the patch, the symbol is in the exe, the registration binds 0x800A7798 -> &func_800A7798, mkw_base_shared is a STATIC lib (no duplicate atomics), and the exe disassembly contains exactly one call to CttrWaitPoll292 inside func_800A7798. Yet the counter never increments. Execution therefore never reaches loc_800A7810 despite entering (and usually leaving) the function.
- Batch 294 (run 325) brackets the whole path: counters at fn_800A7798 entry/exit, fn_8023BA20 entry/exit (BA20 is a thin wrapper: it calls fn_8023BF3C, the real resolver, 888 lines), and fn_8023BF3C entry; [w294] prints every ~10 s while an item is current. The five counts will show exactly which segment execution enters and never leaves -- or whether fn_800A7798 is entered at all.

## UPDATE 18 -- Runs 325 + stacks: no thread is in the handler; the park is off-thread (Nov 9, 2026)

Run 325 (batch 294) died on the .p3d side (~guest t=308 s, neocortex_onfoot_model.p3d last dispatcher item), disp 161, MAX BINK 1503.

- [w294]: e=0/x=0 all run (no fighttree items loaded -- consistent with [w288]); rin=rout=bf balanced 12->61. The resolver pair is a general loader service.
- [w293]: pushes/pops stopped at 6,484 again -- deterministic totals shared with run 324 (6231/6350/6484 across both runs). The stream walk HALTS mid-item; it does not spin. Combined with 324, round 6's fixed-point is now effectively dead for these deaths: the park is inside one nested call in fn_80250C24's per-item path, not in the loop.
- [w237] host stacks from the frozen 325 resolved against nm325: NONE of the 88 threads was inside fn_8024F5A0 / fn_80250C24 / fn_800A7798 at sample time. The dispatcher context is parked off-thread (a suspended fiber's saved context), which live stacks cannot show. One live thread was in the GOD/Bink lock chain (func_8023BA00 -> func_8023BE8C -> fn_8024C9A0 -> OSLockMutex HLE).
- Unifying model, now strong: BOTH traps are the same event -- the dispatcher task parks inside a nested call during a completion handler and the cooperative switch-away is never reversed; the defect lives in the host fiber/context layer, not in either handler's logic. Next instruments: per-callee entry/exit counters in fn_80250C24's path (batch 295), and a fighttree draw under 294 (run 326 in flight).

## UPDATE 19 -- Run 327: the park is inside fn_80250C24's own body (Nov 9, 2026)

Run 327 (batch 295) died on the model-.p3d procession (~guest t=307 s; nina_onfoot last), disp 161, witness 227.7 MB ([w226] flood).

- [w295] final state: h (fn_80250C24) = 11 in / 10 out -- the 11th invocation never returned. EVERY bracketed callee balanced: child ctor 10/10, header read 29,622/29,622, seek 6,229/6,229, fn_8024E940 11/11, fn_80143720 477/477. Push/pop 6,228/6,227 at the last live sample (one chunk frame open, normal mid-walk state), final [w293] total 6,484 with pos=103,211 -- the same deterministic totals/position as runs 324-326.
- So the dispatcher is parked inside fn_80250C24's own body, past every direct callee: in one of its ~14 InvokeIndirectCpu sites (10 inside the walk loop) or an unbracketed direct call. The indirect sites share identical register-flush context, so site-bracketing there is clumsy; the better instrument is host-side.
- Batch 296 (run 328): freeze watchdog in the poller -- dispatcher heartbeat stalled ~10 s with an item current => GuestFiberManager::DumpGuestThreads into the witness (host fiber state + guest OSThread state/suspend/priority/queue + saved registers + guest stack backchain per thread), cap 3. The parked dispatcher's guest thread will show its exact resume chain.

## UPDATE 20 -- Run 328 baseline fiber dumps: the dispatcher runs on the main thread (Nov 9, 2026)

Batch 296's trigger was too naive (healthy loads stall the dispatcher heartbeat >10 s); run 328's 3 dumps all landed in healthy boot -- but as a BASELINE they are gold:

- Only **5 guest threads** exist. Three (0x80BA8F38, 0x80B957D8 = movie glue TCB, 0x80450780) share trampoline entry fn_8024C55C and sit in OSWaitSemaphore (guest state 4 = WAITING, their task semaphores) -- the engine's task model.
- **The dispatcher has NO guest thread of its own.** The current thread is the scheduler/main thread 0x8047DF30, and its live backchain runs: main -> fn_8018BB98 -> fn_80070264 -> fn_800A86A0 -> **fn_8024F278 (peer pump) -> fn_8024FA00 -> fn_8024FA94 (empty-ring path) -> fn_8024C6C0/C65C**. The completion dispatcher fn_8024F5A0 executes inline on the main thread, driven by pump calls from the main loop.
- Consequence for the freeze: when a handler parks mid-item, it strands the MAIN thread's continuation -- the fix hunt is now about what the main thread yielded to / why the guest scheduler never resumes it, readable directly from a freeze-time fiber dump (its saved context + guest TCB state/queue).
- Batch 297 (run 329) retunes the trigger: same item + dispatcher stalled + glue heartbeat climbing >3000 per window (the freeze signature healthy loads lack), plus a 60 s unconditional stall trigger, cap 4.

## UPDATE 21 -- Run 329: the watchdog itself hung in the dump (Nov 9, 2026)

Run 329 (batch 297) froze on the model-.p3d procession again (~guest 307-322 s, disp 161, MAX BINK 1031, witness 232.7 MB). Fiber dumps 2 (t=195 s) and 3 (t=255 s) landed -- both still mid-load (the glue thread spins during heavy loads too, so the signature gate is weaker than designed). No dump exists for the freeze itself, and "DUMP 1" appears nowhere in 232 MB of witness.

- The poller's own unconditional cadence lines stop at the freeze: last [w295]/[w294] at t=301,059 ms, last [w286] at t=308,083 ms, then silence for the remaining ~1,490 s of soak. The poller thread HUNG at the freeze moment -- at exactly the point where the retuned trigger would fire (the fatal fn_80250C24 invocation had already begun by t=301 s: h=11/10).
- The only blocking call the poller makes there is DumpGuestThreads -> SystemBridge::DumpGuestStack. Verdict: that guest-stack walk does not terminate on the parked fiber (the healthy dumps already showed it walking into data addresses). The watchdog became a victim of the freeze it was built to observe.
- Comparative baseline from dumps 2/3 (healthy): thread 0x80450780 cycles READY (on run queue 0x8047DB28) <-> WAITING normally; all other threads parked on their trampoline semaphores; main thread current.
- Batch 298 (run 330): the watchdog no longer uses DumpGuestThreads. It writes a START line first (numbering provable even on a hang), then walks the table via ForEachFiber with its own bounded visitor: fixed fields (host state, guest TCB state/suspend/priority/queue, saved pc/lr/sp) plus a backchain capped at 20 frames that only follows strictly increasing frame pointers.

## UPDATE 22 -- CORRECTION: the poller never hung; it retired on budget (Nov 9, 2026)

UPDATE 21's verdict (poller hung inside DumpGuestThreads) is WRONG. Reading CttrFlagPoll286's loop head in the live source settles it: `for (int i = 0; i < 8000 && lines < 500; ++i)` -- the [w286] change-print budget is 500 lines, and load churn spends ~496 of them by t≈300 s. The loop then exits BY DESIGN, taking the [w294]/[w295] cadence prints and the fiber watchdog with it -- always just before/at the freeze. No hang anywhere; DumpGuestThreads is exonerated (its healthy-fire outputs were complete and correct), and run 329's missing "DUMP 1" header is most plausibly a flood-interleave artifact in a 232 MB witness (run 330, light flood, numbered cleanly 1-2-3).

Run 330's dumps 1-3 (all pre-freeze) add one healthy-baseline datum worth keeping: worker thread 0x80450780 sat READY (state 1, queue = run queue 0x8047DB28) in every sample from t=35 s through t=256 s. Whether that is normal trampoline bookkeeping or a chronic missed run is exactly what a freeze-time dump will disambiguate.

- Batch 299 (run 331): pure budget surgery in the flag poller -- loop lines cap 500 -> 100000, iterations 8000 -> 20000, [w294]/[w295] caps 400 -> 100000, watchdog dump cap 4 -> 6. The watchdog (297 trigger + 298 bounded walk) then survives into the frozen phase and fires there.

## UPDATE 23 -- Runs 328-330 consolidated; batch 299; run 331 launched (Nov 9, 2026)

- **Run 328** (batch 296): froze ~guest t=330 s on the frontend-animation .p3d procession (ngin/crunch/pasadena/vonclutch), disp 161, stage 6, MAX BINK 1,012, witness 233.4 MB. Verdict detail in UPDATE 20 (baseline dumps; dispatcher = main thread inline).
- **Run 329** (batch 297): froze ~guest 307-322 s on the model-.p3d procession (coco last [w288], item 0x807120C0), MAX BINK 1,031, witness 232.7 MB, [w282]=70 heals. Dumps 2 (t=195 s) and 3 (t=255 s) landed mid-load -- the glue thread spins during heavy healthy loads too, so the 297 signature gate is weaker than designed. No freeze dump; cause established in UPDATE 22 (poller budget), NOT the UPDATE 21 hang theory (retracted).
- **Run 330** (batch 298): froze on sound/scripts/sfx/frontend.p3d (item 0x807121D0), MAX BINK 1,500 (the attract loop ran further than usual), witness only 10.7 MB (light [w226] flood), [w282]=282, glue heartbeat reached 575,517 by guest t=341 s -- this run's glue spun far longer than the usual ~55k. The batch-298 bounded walk is PROVEN: dumps 1-3 (t=135/195/256 s, all pre-freeze) each completed START to END cleanly. All five fibers matched the healthy baseline in every dump: 8F38/B957D8 WAITING on trampoline semaphores, DF30 (main) current/RUNNING (dump 2 chain via the pump path fn_8024FA94/fn_8024F278; dump 3 chain via the GOD resolver path fn_8023BE8C/fn_8023BA00), ED40 WAITING, and **0780 READY on run queue 0x8047DB28 in all three samples**. No dump 4 fired -- the poller had already retired on its 500-line budget (UPDATE 22).
- **Batch 299** (poller budget surgery only): loop `i < 20000 && lines < 100000`, [w294]/[w295] caps -> 100000, watchdog dumps296 cap 4 -> 6. First 331 build failed on my own syntax slip -- the patcher's dumps-cap edit inserted a `// Batch 299` comment mid-condition, commenting out the rest of the if. Patcher fixed; live os_init.cpp corrected in place and verified; rebuild linked clean (exe 59,096,064 B, 05:49:24). Standing lesson: never insert a `//` comment mid-expression.
- **Infra**: the SSH route to BRANDON-PC was down ~05:56-09:01 (repeated "Connection closed by UNKNOWN port 65535"; LOQ asleep or Tailscale/proxy dropped), and two VM-side retry timers were lost to runtime restarts in the window. Route recovered on its own; nothing LOQ-side was harmed (run 330 was already harvested at 05:39).
- **Run 331** (batch 299) launched 09:03, harvest331 verified for 09:38, nm331 dumped. Expected payoff: the watchdog now lives past t=300 s, so the freeze-time [w296] dump should finally land. Read it against the healthy baseline -- main thread's guest TCB state/queue at the freeze, and whether 0780 is still READY-stuck or has gone WAITING.

## UPDATE 24 -- Run 331: the park is transient; the wedge is a live loader/glue loop (Nov 9, 2026)

Run 331 (batch 299) verdict: harvest fired 09:38, process gone at verdict, witness-331 9,315,976 B / 90,883 lines, MAX BINK 1,045, console 3,159 lines with 3 AV mentions (all the known benign vectored-handler events: addr 0xFFFFFFFF len 4, ctx null, identical cadence -- not crashes), quarantine 0, [w256]=34, [w252]=2. The batch-299 budget raise worked end to end: the flag poller printed 1,141+ [w286] lines and was still sampling at t=2,092,032 ms when the harvest killed the process; the beat poller printed its usual 16 [w212] and retired.

The full-surviving record rewrites the end-state:

- **The .p3d park released.** [w295] sat at h=11/10 (hdr 29,622, push 6,228 -- the deterministic totals) through t=300.9 s. In the next 10 s window everything drained: h=28/28, hdr 44,546/44,546, seek 9,173/9,173, push=pop=9,171, ctor 27/27, e940 28/28, f3720 3,818/3,818 -- all balanced. The "park inside fn_80250C24's own body" (UPDATE 19) is a long stall, not a terminal one -- at least in 331 the handler's 11th invocation returned and 17 more completions flowed.
- **The fighttree handler finally showed its loop.** In the same window [w294] recorded fn_800A7798 e=2/x=1 with **polls=157** -- the batch-292 wait-loop counter that read zero in every prior run. One invocation entered the readiness wait (loc_800A7810 loop head; pump block fires only when the poll returns 0 AND [item+300]==0) and never exited by the last [w294] print. UPDATE 17's paradox (verified hook, zero polls, fighttree deaths) now has a second data point: the loop DOES run when the handler is reached in this load order -- the earlier deaths parked before the loop head, this one inside/after it.
- **The dispatcher drained and stopped.** [w286]: cur cleared at t=320,208 ms (stage 6 -> 5), ring empty (head==tail==0x80943ED8) from then on, qcnt/qpend settling at 4/4 for the remaining ~29 minutes. disp froze at 161 because an empty ring generates no iterations -- the frozen disp count is a symptom of an empty queue, not of a stuck item.
- **No thread is parked anywhere the fiber table can see.** [w228] stall survey at t=557.6 s: runbits=0 (zero threads on any run queue); main thread DF30 state RUNNING, resume LR fn_801DB25C (presenter VI-wait caller); glue B957D8 state 0x00020000; worker 0x80450780 WAITING on its semaphore (its chronic healthy READY, UPDATE 20/22 baseline, is gone in the wedge). No [w296] freeze dump fired: the watchdog's gate is a stuck CURRENT item, and cur was 0 -- the trigger design misses this wedge shape. (Dumps 1-3 were healthy baselines again.)
- **The wedge is live.** All 49 [w237] host-stack samples resolve (nm331) to a single thread -- the guest CPU thread -- cycling the GOD loader family (fn_8023BA00 -> fn_8023BE8C -> fn_8024C9A0/C0 Bink lock wrappers -> OSLock/UnlockMutex HLE, WakeupThreadQueue inside unlocks) and the movie chain (fn_802D47AC/84C0/DA594 -> fn_800B9558, the glue fn). Zero samples inside fn_800A7798, the dispatcher, or fn_80250C24. The engine is spinning productively-looking loader/mutex work that never produces the one completion the movie flag (f84, never set) waits on.

**Model, revised:** layer 2 is not a park in a handler. The completion machinery stalls transiently inside handlers (tens of seconds), drains, and the system then settles into a live loader/glue loop in which one fighttree completion is lost -- its handler polled readiness 157+ times without the readiness ever being signalled, and whatever should signal it is inside the same loop that keeps cycling. Next hunt, in order: (1) identify the object/vtable behind the wait loop's [sp+20] handle and what sets its +88 readiness -- the god86 entry witness at fn_8023BF3C in existing witnesses is unmined for the fighttree keys; (2) read fn_8023BF3C's completion path for where a resolved file's readiness is published; (3) a watchdog variant gated on disp-stall + cur==0 + qpend>0, since the current gate cannot see this wedge.

## UPDATE 25 -- Run 332: the readiness word identified; the resolver is a heavy-traffic service (Nov 9, 2026)

Run 332 (batch 300) verdict: harvest fired 10:49, witness-332 9,714,668 B / 93,680 lines, MAX BINK 1,135, [w282]=143, console AV mentions 3 (the benign vectored set), quarantine 0. Wedge onset t=325,676 ms (disp 161), identical frozen tail to 331 (cur=0, stage 5, ring empty, qpend=4, f84=0, glue spinning).

Batch 300's instruments, first full read:

- **[w295] balanced end to end**: h=53/53, ctor 52/52, hdr 56,154/56,154, seek 12,469/12,469, push=pop=12,467. The .p3d park is transient -- second consecutive confirmation (331: 28/28). It is not the wedge.
- **[w294] balanced too**: e=8/x=8 for fn_800A7798, rin=rout=bf=116 for the resolver pair, polls frozen at 685, pumps 677. In 332 NO handler invocation is left open anywhere. 331's open invocation (e=2/x=1, polls=157) was a symptom visible in that run's load order, not the mechanism. The wedge is a lost completion with every measured guest-side participant exited cleanly.
- **[w300] froze on the fatal wait's record**: witem=0x807121D0, whdl=0x80B93060, vt=0x803E1E80, r88=0x8023B744, [whdl+300]=128 -- unchanged from probe (t=632 s) to harvest (t=2,066 s).
- **god66 mining (115 rows, whole run -- the batch-300 cap raise works)**: only 8 distinct keys all run. The dominant key 0x807121F0 (-> out 0x80712310) accounts for 59 calls, and calls 91-114 are that SAME key+out pair repeated back-to-back. The two queue-manager contexts (0x8084B3E0/B458) take 15 each, item sibling 0x80712218 12, 0x807120E0 9, engine ctx 0x804C15DC 3, two singletons. Read: the resolver is called constantly with a small rotating key set (per-context file resolution); the keys are item-block fields, not filenames. The repeated identical tail is steady-state loader cycling, not a stuck retry -- BF3C RETURNS every time (rin=rout). Nothing in the god66 stream discriminates the fatal item; the discrimination has to come from the wait object itself.

**The readiness mechanism, decoded from source** (func_8023B744.cpp + func_8023ACEC.cpp, fetched from the tree):

- fn_8023B744 IS the vtable+88 method of the constructed wait object. Body: call the object's vtable+152 method; compute a flag via the cntlzw/rotl boolean idiom -- **the flag is 1 iff [obj+24]==0, else 0**; call vtable+156 with that flag; return the flag. fn_800A7798's loop exits when the returned low byte is nonzero. So the handler's wait is, verbatim: *until [handle+24] == 0*.
- The ctor fn_8023ACEC writes **[obj+24] = 0 at construction** (and [obj+0]=0x803E1E80 -- the same vtable [w300] sees; [obj+4]=0x803E1930, [obj+8]=1, [obj+12]=device ptr, [obj+16]=a parse word, [obj+300..343] a zeroed 44-byte sub-struct, [obj+28]=0, [obj+29]=a parse byte; [obj+300] reads 128 in the wedge only because a later writer put it there -- offset 300 is the sub-struct's first word, NOT the +300 gate byte fn_800A7798 reads at [item+300]).
- Therefore: readiness starts TRUE at construction. Some post-construction step SETS [obj+24] nonzero (work submitted), and that work's completion must CLEAR it. In the wedge the clear never happens. The suspects for the setter, in order: the object's own vtable+152 / vtable+156 methods (called on every poll), the table device's completion path, or the caller between resolve and wait.

**Batch 301** (applied + verified live, build 333 running): [w300] gains **w24=[whdl+24]** printed every ~10 s (the set/clear transitions will be visible across the run, per wait object), plus **v152=[vt+152]** and **v156=[vt+156]** (the service methods' addresses, resolvable against the DOL symbols). God caps 67 (C610 index), 68 (init-flag), 70/71 (device-call bracket + final out value) raised 100 -> 100000 so the resolver's internal path survives to the fatal window; caps parse verified idx-exact (66-72 = 100000, 100000, 100000, 100, 100000, 100000, 100). Run 333's evidence should name: the w24 trajectory of the fatal object (when it was set, by correlation with which loader phase), and the two service functions behind the wait.

## UPDATE 26 -- Run 333: the fighttree wait COMPLETED; the lost completion is upstream of the dispatcher (Nov 9, 2026)

Run 333 (batch 301) verdict: harvest fired 11:44, witness-333 9,396,105 B / 91,706 lines, MAX BINK 1,044, [w212]=15, [w228]=136, [w252]=2, [w256]=35, [w286]=2,262, [w294]=208, [w295]=208, [w300]=177, god66=115. Console-333 3,154 lines, AV mentions 2 (content spot-check: the 0xFFFFFFFF hits in console-333 are ordinary stack words inside the known benign vectored-handler dumps -- same family as 331's verified set). Wedge onset t=320,630 ms. Near-clone of 332 (identical [w295] totals: hdr 56,154, seek 12,469, push=pop=12,467).

**The w24 trajectory (batch 301's payoff)** -- [w300] saw exactly one wait object all run (0x80B93060, the singleton the resolver returns for the dominant key; god71 confirms BF3C writes that same pointer out repeatedly). Its +24 word: **1** at t=310,933 ms (wait in progress, polls=199), **0** at t=320,971 ms (polls stopped at 681 -- the wait COMPLETED and the handler exited; [w294] e=8/x=8 agrees), then **4** at t=331,002 ms, frozen there for the remaining ~29 minutes. So in 333 the fighttree completion was NOT lost at the handler: it arrived, the handler finished its post-wait work, and afterwards four more units of work registered against the same shared device object and never drained. Combined with 331 (wait still open at harvest) and 332 (balanced, polls 685), the handler wait is a sometimes-visible symptom of the stall, never its mechanism.

**Resolver internals (uncapped god witnesses, first full read)**:
- god68 count **0** all run: BF3C's create path was NEVER entered in run 333. Every one of the 116 resolutions hit a populated device-table slot. The "create-skipped / device never created" hypothesis is dead.
- god67 printed 116 rows, all a=0/b=0 -- as built, that witness carries no information (its site arguments are not the C610 index). Dead witness; noted, not chased.
- god70 = 232 (2 per call), god71 = 347 (~3 per call): the device-path bracket fires on every resolution, including the repeated outs of the singleton 0x80B93060 to 0x80712310 (item block), 0x8094A0F4 and 0x804C12E4 (loader contexts).

**Class anatomy, completed from source** (vtable 0x803E1E80 dumped from the DOL; all ~40 slots resolved; the class's function files swept):
- +88 fn_8023B744: mutex-guarded read -- lock fn_8023B188 / unlock fn_8023B1B0 on the GOD statics mutex 0x804478A8; returns ([obj+24]==0). It changes nothing.
- +100 fn_8023B858: returns byte [obj+28] (the operation result byte the handler branches on after the wait).
- +64 fn_8023B5BC (BF3C's per-resolution service call): composite forwarder -- calls +40 fn_8023B1D8 (opens with a size-12 request to fn_80248178) then +92 fn_8023B7A0, which calls the RESOLVED DEVICE's vtable+88 (the table device at [obj+12], a DIFFERENT readiness method from this class's own +88 -- same slot, other class) plus fn_8024C32C. The forward chain is consistent with the healthy runs' host stacks, which rotate through exactly these resolver frames.
- **Writer sweep**: across all 44 fetched class/resolver function files, the ONLY writes to a +24 offset are the ctor fn_8023ACEC (writes 0) and a stack-frame store inside BF3C itself (r11-12, not an object field). No class method writes [obj+24]. **The word is written from outside this class** -- an external agent (the async completion path that services the underlying device) owns it: it set the word to 1 during the fatal wait, cleared it at completion, and set it to 4 for the next batch of work that then never completed.

**Model, current**: after the last dispatcher item (161) completed at ~t=321 s, the producer side stopped: the dispatcher ring stayed empty, 4 posts sat unconsumed in the movie queue (qpend=4), the shared GOD device accumulated 4 pending units ([obj+24]=4 -- the matching count is suggestive, not proven), the presenter parked at the VI-retrace wait, and the movie glue spun polling f84. The external writer/clearer of [obj+24] and the dispatcher producer are the same missing heartbeat. Next: identify the producer -- what enqueues dispatcher items and posts to the movie queue during the attract cycle, and which guest thread/context runs the device completion that clears +24. Host-side candidates already in evidence: the ARQ/DVD async completion path and the peer pump fn_8024F278 (the [item+300] gate byte at fn_800A7798's loop head is written by that same economy -- also still unattributed).

## UPDATE 27 -- The pump's empty path is a context switch; batch 302 pre-registered (Nov 9, 2026)

Desk results since UPDATE 26:

- **fn_8023BA20** is a true thin wrapper (copies the key word to a stack slot, calls BF3C, returns). Nothing else.
- **[w286]'s f84** is byte [0x80B93A98] -- the SAME +84 offset the batch-248 print reads on three sibling objects (0x8138B190 io, 0x80B93060, 0x80B92558), i.e. a class-family state byte, not a bespoke movie flag. In run 333's 15 [w248] prints the value at the SINGLETON 0x80B93060+84 (d76w84) never changed (0). The manager's own +16 word (0x80B93A44+16) ticked 0xA/0xB during health and settled at 0xE (14) at the end; io84 (0x8138B190+84) went 0 -> 0x01365C88 exactly once, late (an accumulated counter/timestamp shape, not a flag).
- **fn_8024FA94** (the dispatcher's empty-ring path, 0x78 bytes) leads with **fn_8024C870** -- the engine's hand-rolled context switch (OSSaveContext/OSLoadContext + FPU). So an empty-ring pump cycle is literally how the engine yields/sleeps its main context. "Pump runs, ring empty" and "main thread parked" are the same observation from two sides: the interesting question is no longer whether the pump runs, but whether anything ever WAKES the context with new work -- i.e. whether the enqueue side and the completion interrupts still fire.
- **fn_80248178** (the GOD service object's +40 target, reached via BF3C -> +64 composite fn_8023B5BC -> +40 fn_8023B1D8): lock mutex 0x8044E6D8, call **[G]->vtable+56** where G = the global peer pointer at SDA [r13+10864], unlock. Another forwarder layer into a global peer object; the chain is consistent with run 331's rotating resolver/GOD host stacks in the frozen phase (the main thread keeps servicing this economy; it is the enqueue/completion machinery's front door).

**Batch 302 (built next; interpretation pre-registered here)**: entry counters CttrPumpCnt302 at fn_8024F278 (pump), fn_8024FA94 (empty-ring), fn_802500BC (pop), printed as totals on the [w300] ~10 s cadence. Reading key:
- pump AND fa94 both frozen after the wedge -> the main loop stopped reaching the pump at all; the stall is inside the loop body upstream of the pump call.
- pump climbing, fa94 climbing, pop frozen at 161 -> the pump cycles and yields normally; the ring is genuinely never refilled; the producer/enqueue side is dead and the hunt moves to the enqueue callers.
- pump climbing, fa94 frozen, pop frozen -> the dispatcher enters but never takes the empty path and never pops: ring/gate state is inconsistent (head/tail or the [this+1] gate) -- a dispatcher-internal defect.

## UPDATE 28 -- Run 334 verdict: the main thread is parked in VIWaitForRetrace; the retrace only advances on presents (Nov 9, 2026)

Run 334 (batch 302) verdict: witness-334 236,962,318 B / 1,263,815 lines ([w226] flood heavy), MAX BINK 1,010, [w212]=14, [w228]=143, [w252]=2, [w256]=33, [w286]=576, [w294]=190, [w295]=207, [w300]=176, god66=116, console-334 3,170 lines, AV 3 (benign family), quarantine 0. Onset in the usual window (disp 130 -> 161 between guest t=326,386 and 331,387 ms).

**Batch 302 answered its trichotomy: branch 1.** The [w300] counter series has exactly two transition prints: t=331,074 ms (pump=368,702, fa94=377,707, pop=81, qpend=1) and t=341,106 ms (pump=369,038, fa94=377,900, pop=81, qpend=0) -- then NOTHING moves for the remaining ~29 minutes. The peer pump is never entered again after the wedge. pop=81 total (fn_802500BC is not called 1:1 per item; its frozenness, not its value, is the signal).

**The fighttree wait completed in 334 too** (polls frozen at 556, e=8/x=8; [w295] 53/53 with the identical deterministic totals). w24 trajectory: 0 in 175 of 176 prints, a single 1 at t=331,074 (polls already final -- a transient submit+clear with no waiter), back to 0. **332/333's w24=4 / qpend=4 frozen endgame does NOT recur (334 ends 0/0): pending-count debris varies by run and is not the mechanism.** god68=0 again (create path never entered, third run), god67 dead again, god70=232, god71=344.

**Host stacks (334): the capture point.** Every resolved [w237] sample's engine thread (tid 38440 in the late samples) sits in the SAME stack: SleepPreciselyUntil <- SelectThreadSwitch <- OSSleepThread_HLE <- **VIWaitForRetrace_HLE** <- fn_801DB25C (the presenter) <- InvokeIndirectCpu <- fn_8008E400 <- fn_8008D278. No sample contains the pump, either handler, or the resolver. The main/scheduler context is properly ASLEEP in the HLE waiting for a retrace.

**The VI economy, from source** (runtime/src/hle/video/vi.cpp + fiber_manager.cpp + os_scheduler.cpp -- heritage code, NSMBW addresses annotated):
- VIWaitForRetrace_HLE (801b99ec): records retraceCount at entry, then loops: OSSleepThread on the VI retrace queue 0x804AEB6C; on each wake, breaks only if `g_vi.retraceCount - entryCount >= FrameStep()`. It is a LEVEL check on a software counter -- nothing else can release it.
- g_vi.retraceCount advances in AdvanceRetrace, which runs on the PRESENT path (the paced frame-present function around vi.cpp:1180 also drives PaceToRetraceBoundary and the Aurora present schedule) and in VI_HLE_ForceRetrace.
- ProcessTimerEvents (fiber_manager.cpp:595) drains g_viRetracePendingCount (max 16/slice) into VI_HLE_ForceRetrace calls; it is invoked from os_scheduler.cpp's yield/idle points (lines 447/496). **No producer of g_viRetracePendingCount exists anywhere under runtime/src** (findstr across the tree: only the definition, the init zero, and ProcessTimerEvents' own remainder re-add). For the CTTR build this path appears to be dead machinery inherited from the SPM side.
- Consequence: in this build, retraces are produced ONLY by presenting frames. The main thread's loop is pump -> render/present -> VIWaitForRetrace. At the attract-movie -> frontend transition (~t=321 s: movie ends, frontend reload completes), the first scene frame cannot be produced until the loader pump runs, the pump runs on the main thread after the wait, and the wait needs a retrace that only a presented frame produces. **A circular wait across the mode transition** -- escaped in earlier loops by present-cadence surplus, lost once at ~5 minutes in every 282+ build. This also re-reads 331: its rotating GOD/Bink stacks were the healthy pre-wedge servicing; the frozen survey ([w228], runbits=0, DF30 resume at the VI-wait caller) already showed the same park.

**Fix candidates (next round; VI code is shared heritage, so scope carefully):**
1. Wall-clock VI heartbeat: feed g_viRetracePendingCount (or AdvanceRetrace directly) from a timer so retraces exist independent of presents -- what real hardware does; lands in the scheduler idle path where ProcessTimerEvents already runs.
2. Pump-while-waiting inside VIWaitForRetrace's loop (mirrors the guest's own fn_800A7798 wait design, which pumps the loader while it waits).
3. Post a pending retrace when a thread queues on the VI queue and the count has not advanced for over one interval (smallest change, same site family as 1).
Before choosing: read AdvanceRetrace + PaceToRetraceBoundary + the present-path callers in full, and confirm how the SPM side produces pending counts (if it does) so a CTTR fix does not fork shared semantics blindly.

## UPDATE 29 -- CORRECTION to UPDATE 28: retraces DO advance in the freeze; the wake is lost at the VI queue (Nov 9, 2026)

UPDATE 28's mechanism is retracted in two places. (1) "Retraces are produced ONLY by presenting frames" is FALSE: VI_HLE_PollRetrace -> AdvanceDueRetraces(ctx, 8, true) is a wall-clock retrace path, called from the scheduler's idle loop (os_scheduler.cpp:445) and from the batch-234 no-runnable fallback (os_scheduler.cpp:494). The pending-count path (ProcessTimerEvents) is indeed producerless, but it is not the only path. (2) The "circular wait" therefore does not hold as stated: the waiter's level condition is satisfiable without any present.

**What run 334 actually proves** ([w232] prints time-correlated against [w300] timestamps in witness-334): the prints at poller t=351,132 / 381,205 / 411,279 / 441,350 / 471,420 / 501,494 / 531,564 / 561,634 ms show due and poll climbing steadily, and due-minus-dueEarly (actual AdvanceRetrace executions) climbing by ~1,830 per 30 s = **~61 retraces/second, deep into the frozen phase**. dueWaitMs stays 1-13 ms (the next boundary is always near). Each AdvanceRetrace calls OSWakeupThread on the VI retrace queue 0x804AEB6C (vi.cpp, wake block) -- thousands of wakes -- while the presenter never leaves VIWaitForRetrace (334 stacks) and the pump never runs again (batch 302 counters). **The wake is lost between OSWakeupThread and the presenter's reschedule, permanently, from the transition onward.**

**Code anatomy of the wake** (os_scheduler.cpp WakeupThreadQueue, os_sleep.cpp OSSleepThread_HLE):
- Sleep side: marks TCB WAITING (state u16 at +0x2C8 = 4), stores queue at +0x2DC, InsertThreadIntoQueueByPriority, SuspendGuestThread, SelectThread. Defense-in-depth: if SelectThread returns without switching and the thread is still WAITING+linked, it unlinks and re-marks RUNNING (batch 235 sites; [w233] unparkable=0 in 333/334).
- Wake side: loop pops queue head ([queue+0]) up to 256 times; terminated threads are unlinked and dropped (ThreadStateIsTerminated(state) OR GuestFiberManager::IsTerminated(thread)); survivors are marked READY, and ONLY if suspend (+0x2CC) < 1 are they linked onto a run queue + fiber-resumed + pending-marked. Immediate reschedule is suppressed while advancing a retrace (by design -- the scheduler's outer loop is expected to pick).
- **[w233] eliminates the suspend branch for the presenter: suspDF30=0 in all 18 samples of run 334 and all 17 of run 333**, idleFlag=0, unparkable=0 throughout.

Remaining candidate failure points inside the wake, in order: (a) the presenter is not the queue head when wakes fire -- its node was never linked, was unlinked by the defense path, or sits behind a stale head the pops never clear; (b) the terminated branch consumes it (guest state reads terminated, or the fiber manager believes the main fiber terminated); (c) it is popped and linked but the pick never selects it (pending/run-queue side). Batch 303 instruments WakeupThreadQueue for the VI queue only (calls / pops / terminated-hits / suspend-skips / links / last popped thread) plus the live queue head on the [w300] cadence; interpretation pre-registered in the batch-303 daily-log entry before launch.

## UPDATE 30 -- Layers 1 and 2 are one root: the transition-era spray orphans the VI waiter (Nov 9, 2026)

Mined from the existing witnesses (no new run needed):

**The burst.** In every run 332/333/334, the ONLY [w276] lines in the file are a single burst at the attract->frontend transition, all of the form:
`[w276] sleep poisoned current=0x009E009E queue=0x804AEB6C fallback=0x8047DF30 lr=0x801DB288`
(334: 43 lines, 333: 77, 332: 143.) The running-context word OSSleepThread read was a SPRAY value (the u16-pair gradient family: 009E009E, 00A300A3, 00AC00AC, 00B200B2, 00B300B2, later 0x00350035) while the presenter (lr 0x801DB288, inside VIWaitForRetrace) tried to sleep on the VI queue. Batch 276's resolver substitutes the fiber manager's current thread (DF30, correct) and the sleep proceeds -- the guard worked; the poison is the story. In 333 the burst spans witness lines 83,772-86,224: AFTER the fighttree wait completed (line 80,702) and BEFORE the w24->4 print (line 88,593); its last lines interleave with `[w282] gate heal cur=0x36263626 run=0x00350035 healed=0x8047DF30 lr=0x801DB288` (BOTH OS context words spray-valued at that instant, healed to DF30) and `[w278] reconcile walk bad node=0x36263626 at step 0` (a thread-list walk hitting spray at its head). The wake-side [w276] queue-clear NEVER fires for the VI queue in any of 332-334 -- the wake path is innocent.

**The frozen presenter.** The burst's tail print `[w251] ms=326358 ... e4=8047DF30 d4=8047DF30 df30=00040001` (fields verified against the batch-251 source: df30 = u32 at DF30+0x2C8) shows the context words healed and consistent while **the presenter's state is WAITING (0x0004 in the high half)** -- and per UPDATE 29 it stays WAITING-and-unreachable while retraces advance at ~61/s and wakes fire into the VI queue forever. The presenter is WAITING but not wakeable: its sleep, executed inside the spray window, left it on no queue (insert into sprayed list pointers, a queue head/tail sprayed to zero, or its link node overwritten mid-insert -- the exact step is the one thing still unobserved).

**Unified model.** Layer 1 (the SelectThread gate deadlock, fixed by batch 282's heal) and layer 2 (this wedge) are the same root event at different addresses: a guest bulk write during the frontend reload streams data values (u16 gradients, ASCII-ish words like 0x36263626, zeros) across the low OS structures -- context words, thread-list links, queue fields. On hardware the same write is harmless (the game's own scratch/ARAM layout); in this build its destination aliases live OS memory -- the FAKE_VMEM / memory-map aliasing family is the prime suspect class. The defenses (276 resolve, 278 reconcile, 282 heal) save the context words but cannot save a sleep that executes mid-burst.

**Next steps.** (1) Slim batch 303 (os_init only): [w300] gains vqh=[0x804AEB6C], vqt=[0x804AEB70], and the presenter's dst=[DF30+0x2C8], dq=[DF30+0x2DC], dnx=[DF30+0x2FC] across the burst, to catch the orphaning step in the act. (2) Reopen the writer hunt with the burst window as the target: guest time ~320-326 s, the frontend reload's bulk transfers; the batch-280 shield trail is the starting point. (3) Fix prongs: kill the write's aliasing at the root if the writer is found; independent HLE hardening candidate -- WakeupThreadQueue rescues a thread whose TCB claims WAITING-on-this-queue but which is not linked (or the VI wait sleeps with a timeout and re-checks). Do NOT ship a rescue hack before the writer is identified; it would mask the root while the spray keeps eating other structures.

## UPDATE 31 -- Run 336 verdict, and THE WRITER IS NAMED: BinkCopyToBufferRect (Nov 9, 2026)

Run 336 (batch 303, build verified before launch): witness-336 237,161,402 B / 1,264,620 lines, MAX BINK 1,013, console-336 3,163 lines, AV 3, quarantine 0, [w256]=34, [w276]=50, [w282]=49. Wedge in the usual window: disp 136 -> 161 between guest t=320,054 and 325,055 ms; handlers balanced; fighttree wait completed (polls 527); pump frozen at 420,979.

**Batch 303's frozen fields -- and a correction to UPDATE 30.** Across the whole transition series the batch-303 fields never change: vqh=0, vqt=0, dq=0, dnx=0x8044ED40, and dst (u32 at DF30+0x2C8) = 0x00020001 -- **the presenter's TCB state is RUNNING (2), not WAITING**. The batch-296 fiber walk agrees: fiber DF30 state=2, cur=1, term=0, susp=0, queue=0. UPDATE 30's "WAITING but on no queue" was built on a single [w251] sample that caught a transient mid-sleep state; the steady frozen state is that every guest-side structure believes the main thread is RUNNING and current, while the host thread sleeps in the scheduler's idle servicing loop (334 stacks) and the pump never runs again. The spray burst at the transition is real ([w276]=50 in 336, same form), but the terminal scheduler step that loses the thread (idle-loop exit condition vs pick vs fiber switch-in) is still unobserved. It may not need observing, because of what follows.

**The writer.** The watch-4 shield's [w256] lines (33 in 334, 34 in 336, identical shape) log the spray in the act:
`[w256] word 0x800000E4 shielded 0x8047DF30 -> 0x00100010 restored rip=0x7FF7...FC03 active=0x800B9558 pc=0x00000000 lr=0x802D9C18`
The rip is a host address at the same module offset (…FC03) in every catch -- the runtime's memory-write helper executing the store, not the culprit. The guest context is the culprit: active = the movie glue fn_800B9558, and lr resolved against the DOL symbol table: **0x802D9C18 is inside BinkCopyToBufferRect (0x802D9874, size 0x6EC)**; a second context (the E0/list-tail catch) has lr inside fn_802DD5F8. The values written are frame pixels (0x00100010, 0x10101010 -- u16 pixel pairs). **The spray is the Bink movie frame copy**: BinkCopyToBufferRect (called via the BinkCopyToBuffer trampoline, 0x802D9834) copies decoded attract-movie frames into a buffer whose span, in this build, sweeps across live OS memory -- the low context block (shielded, restored), thread/queue link fields (unshielded -- the drip, the fake module-list head 0x10101010 at 0x800030C8, the corrupted owned-list tails the HLE's own surgery then propagates). Bink is recompiled guest code; there is no HLE binding for it in runtime/src. Every manifestation in this brief is downstream of this one copy family.

**Next steps.** (1) Read BinkCopyToBufferRect's recompiled shard and its caller chain (glue -> BinkCopyToBuffer -> Rect) with the actual arguments: destination base, pitch, height, plane pointers from the Bink handle -- find which parameter makes the span cover 0x800000D4..0x804AEB6C instead of the movie buffer, and where the guest's movie frame buffer legitimately lives (MEM2/EXRAM aliasing is the prime suspect class). (2) Fix at the copy (or at the memory mapping it exposes), then soak: the stability bar is unchanged (repeat 1800 s passes). (3) The SelectThread idle/pick counters (batch 304 candidate) are shelved unless the copy fix leaves a residual wedge.

## UPDATE 32 -- Inside the copy: Rect dispatches, the trampoline is faithful, the caller algebra cancels (Nov 9, 2026)

Desk pass over func_802D9874's shard (shard_2b818545ce61b8bbb7369a20.cpp), the original DOL bytes, and the caller chain:

- **Rect contains no pixel loop.** It marshals, clips the SOURCE rectangle against handle fields [h+596]/[h+600] (all comparisons unsigned, no underflow paths), applies the standard negative-pitch fixup (`dest += (-pitch)*(destheight - desty - 1); desty = 0`), and dispatches on (flags & 15) to a copier. For type 3 the block is loc_802D9BD0: it calls func_802DFB74 (a 0x5C thunk) with lr=0x802D9C18 -- exactly the [w256] return address -- passing r3=dest (post-fixup), r4=destx, r5=desty, r6=pitch, r7=plane pointer read as `[h+188] + 4*[h+184]` (index unchecked), r8=srcx, r9=srcy, r10=srcw, stack srch/[h+204]/[h+208]/flags. The spraying stores execute inside that copier family.
- **The trampoline suspicion is refuted by the original bytes.** A desk pass flagged BinkCopyToBuffer (0x802D9834) for storing its incoming r9 into the flags slot and never zeroing r7/r8. The DOL's own 16 instructions at 0x802D9834 do exactly the same (stw r9,16(r1) at 0x802D9844; li r9/r10 zero srcx/srcy; r7/r8 untouched): the SDK signature is the 7-arg form (r7=destx, r8=desty, r9=flags) and both the original and the recomp are correct. Nobody in the shards calls the trampoline directly anyway.
- **The direct caller is fn_802D5488** (called by fn_802D5784), a wrapper that passes destx=desty=0, flags=3, srcw/srch from its caller's struct, dest/pitch from the same struct -- and pre-adjusts `dest += (height-1)*pitch` when pitch<0 (cmpwi/bge verified in the DOL bytes at 0x802D5528). That pre-adjust and Rect's fixup are exact inverses for desty=0: **they cancel**, by design. No double-adjust bug.
- **What remains open is the VALUES**: dest/pitch/height the game hands fn_802D5488, the plane pointer from the unchecked [h+184] index, and [h+204]/[h+208] forwarded unclamped to every copier. Batch 304 (next) logs Rect-entry and type-3-dispatch arguments ([w304], sampled plus always-print when the computed row span intersects 0x80000000-0x80510000) so run 337 shows the offending call's full argument set.

## UPDATE 33 -- Mechanism closed: a null-ish destination (0x00000020) + the window mask (Nov 9, 2026)

Run 337 (batch 304) is wedged in the usual window (disp 161 by guest t~336 s, pump frozen 414,154, wait completed). The [w304] witness caught the offending call:

- Normal calls (all sampled): dest=0x80DA4640, pitch=2560, 640x480, flags 3, plane=0x80C86C60, span 0x80DA4640-0x80ED0640. Sane.
- **Call n=998 (site 1, Rect entry): dest=0x00000020**, every other argument identical. The wrapper handed Rect a destination of 0x20.
- File order in witness-337: first [w256] shield catch at line 79,503, the bad-dest print at 82,112, the [w276] burst from 84,766 -- sprays, then the bad call caught in the open, then the transition burst. [w256] count passed 35 (runs 334/336: 33/34) and was still climbing; bad-dest calls that don't land on a sample slot don't print, so n=998 is unlikely to be the only one.

**Why dest=0x20 sprays the OS block** -- confirmed in the memory source (guest_flat_memory.cpp): guest addresses resolve through a 32 MiB MEM1 window (`region.base & 0x01FFFFFFu`, line ~397). Address 0x00000020 is offset 0x20 in that window -- the same backing bytes as 0x80000020. The faithful copy therefore writes 1.2 MB of frame pixels over physical offsets 0x20..0x12C020: the context words at 0xD4-0xE4 (shield-restored), the module-list head at 0x30C8 (the 0x10101010 fake head), thread-list links and low OS structures (unshielded -- the drip the defenses have chased all week), with the HLE's own list surgery propagating the poison. Every manifestation in this brief is now explained by one event type: **an occasional movie-copy call whose destination pointer reads 0x00000020 instead of the frame buffer 0x80DA4640.**

**Still open**: why the pointer is 0x20 (it arrives via fn_802D5488's caller struct -- a lifecycle moment, a misread field, or a host-side allocation artifact), and whether more bad values exist beyond the sampled one. Batch 305: hook fn_802D5488's entry, print in full only when the dest field is outside the MEM windows (with caller lr + all args), so the next run names the provenance. Fix candidates once provenance is known: repair the pointer's source, or guard the copy against out-of-window destinations (defensible, but papers over provenance -- decide on evidence).

## UPDATE 34 (interim) -- Provenance narrows to a parameter-provider method (Nov 9, 2026)

Run 338 (batch 305) wedged as usual (pump frozen 353,807). The [w305] hook fired its full 60-print cap, every print the same shape: dest=0x00000020, pitch=2560, wrapper object 0x8138AD60 (vtable 0x803F26B8; Bink-neighborhood pointers at +16/+20/+28 = 0x8138B008/0x8138AF40/0x8138B080; +32 = float 1.0). So bad-destination calls through the wrapper are not rare -- the cap filled.

Reading fn_802D5488's span showed why: the destination is NOT read from the object. The wrapper passes a pointer to its own frame buffer into a **virtual method -- vtable+24 of the object at [obj+20] (= 0x8138AF40)** -- at loc_802D55B8, and that method FILLS the buffer (dest/pitch/src rect/dims). Pitch and dimensions come back correct; dest comes back 0x20. The wrapper's object comes from a global singleton (fn_802D5784 loads it from SDA [r13+11524]).

Batch 306 (run 339) named the method: **fn_802D5D18** (guest 0x802D5D18, size 0xE8), called on provider object 0x80C0D388 in every sample. Its body, read from the shard: if [this+48] < [this+44] (index < count), it takes entry = this + index*20, calls fn_801EC8AC([entry+52], 0, 0), and fills the buffer from the returned object X: **dest = [X+80], pitch = [X+72]**, src x/y = 0, and width/height from the entry's +56/+60/+64/+68 fields. fn_801EC8AC (size 0x30, no HLE binding) is itself a thunk: it returns obj->[+16]->vtable[60]() -- a "current surface" accessor. So the destination is the +80 field of a surface object reached through two virtual hops, and that field holds 0x20 while its +72 neighbour holds the correct pitch 2560. Batch 307 (run 340) dumps that surface object (address + first 25 words) at the exact read inside fn_802D5D18, to identify the object and the field's true nature.

## UPDATE 35 -- The destination is a field of a shared static GX descriptor; it flips mid-run (Nov 9, 2026)

Run 340's [w307] dump (inside fn_802D5D18, at the dest read) names the surface: a **static image descriptor at guest 0x8042E2A8** (in the game's data region, not heap): +0 width 640, +4 height 480, +8 depth 32, +16 format 0x1B, +56..+68 RGBA masks, **+72 pitch 2560, +80 pixel pointer**. Provider state: count [prov+44] = 1, index [prov+48] = 0.

Both states captured in full:
- GOOD (first calls): +80 = 0x80DA4640 (the known framebuffer), +88/+92/+96 = 0/0/0.
- BAD (from call n=775 onward, 70 of 80 capped prints): **+80 = 0x00000020** (the descriptor's own +8 value), +88 = 0xA0, +92 = 0x78, +96 = 8. Everything else byte-identical.

So the descriptor is reconfigured in place mid-run -- its tail is rewritten with a different field set (0x20 / 160 / 120 / 8 reads like a small-surface config) while fn_802D5D18 keeps reading +80 as the movie frame destination. The wrapper object is the same instance throughout (0x8138AD60, run 338 and 340 alike).

**Batch 308 (run 341) is the causal experiment**: two new watch-4 shield entries in guest_flat_memory.cpp's s_crit254 -- 0x8042E328 (+80) and 0x8042E330 (+88), both kind=1 (plausible iff 0 or a MEM1-window pointer). The flip values (0x20, 0xA0) are implausible, so the shield restores the good pointer on detection and logs [w256] with the active guest context. If run 341 passes the full 1800 s (and repeats), the flip is proven to be the wedge's cause, and the shield log names the flip's writer for the real fix.

## UPDATE 36 -- Run 341: the shield was never armed on the descriptor's page (Nov 9, 2026)

Run 341 wedged on schedule (disp 161 by ~320 s, pump frozen 439,041). The batch-308 shield entries produced 37 catches on 0x8042E328, but all were boot-time descriptor-init transients (0x00000000 -> 0x00000008, active=0x80348A34, lr=0x8024C9B0); **the flip to 0x20 was never caught, and the bad destination still reached the wrapper ([w305] cap filled, 70 bad [w307] reads)**.

Root cause, read in guest_flat_memory.cpp: the shield check (CttrWatch4Check254) runs only as the single-step completion of a **page-guard write fault**, and CttrWatchArmTcbPages arms exactly 8 guest pages (0x80B95000, 0x80B93000, 0x8047D000, 0x8047E000, 0x8138B000, 0x80C0C000, 0x80447000, 0x80000000). The descriptor page 0x8042E000 was never armed, so writes to it never fault and the check effectively never sees the flip. (Side find: a batch-195 watch already guards guest 0x8042E32C, the descriptor's +84 word.)

**Batch 309 (run 342)** adds 0x8042E000 to kPages254 (8 -> 9 pages) and grows the guard arrays 40 -> 45 slots. With the page armed, the flip write faults, the check restores +80 in the fault path before any guest read, and the [w256] log carries the flip writer's active guest address.

## UPDATE 37 -- Shield post-mortem and the point-of-use fix (batch 310, run 343) (Nov 9, 2026)

Run 342 (batch 309, descriptor page armed) still wedged on schedule (disp 161 by ~325 s). Mining: all 220 descriptor catches were the same boot-init transient (0 -> 8, writer active=0x801E6F44, lr=0x801E6FA0); **zero catches carried the flip value 0x20, while [w305]/[w307] still logged a full set of bad destinations**. The flip is written through a mapping the page guard does not cover, so page-guard shielding cannot intercept it. Batches 308/309 reverted (guest_flat_memory.cpp restored from .bak-pre308).

**Batch 310 (run 343) corrects the value at the point of use**, the same family as the batch-282 gate heal: in fn_802D5D18, the read of [surface+80] passes through host helper CttrFixDest310, which tracks the last in-window destination ([0x80000000, 0x81800000)) and substitutes it whenever the read falls outside the window, logging [w310] per correction (cap 40). If run 343 passes 1800 s, the bar becomes repeat passes on this build; the flip's writer stays an open diagnostic thread (its identity is no longer on the critical path).

## UPDATE 38 -- RUN 343 PASSES: the wedge is dead (Nov 9, 2026)

Run 343 (batch 310, point-of-use destination guard) completed the
full 1800 s soak. Final numbers: MAX BINK 25,912 (wedged runs:
~1,000; best historical pass, run 306: 30,679), bink and glue
counters still advancing in the last samples before harvest;
[w256] shield catches 0 and [w282] gate heals 0 for the entire
run -- no spray reached any monitored word, ever; [w310] logged
its 40-print cap of corrections, each 0x00000020 -> the run's
real framebuffer (0x80DB1340 this run, confirming the last-good
design over a hardcoded address). Witness 23.9 MB / 239,642
lines (wedged runs: ~237 MB flood); AV mentions 1, quarantine 0;
handlers balanced end-to-end (push=pop=12,467, hdr 56,154/56,154).

disp stayed 161 the whole run: with the pump trickling (~85
calls/10 s) and the movie playing to the end, 161 is the attract
loop's steady state after loading drains, NOT a death signature
by itself. The death signature was the combination (161 + frozen
pump + frozen bink + spray), and all three companions are gone.

Brandon saw it live: the window showed full-screen static where
every wedged run showed a white letterboxed field. The static is
the attract movie playing into the visible buffer without color
conversion (a separate, later problem); the white was the wedge's
corpse.

Layer 2 is CLOSED by batch 310. Remaining bar: repeat full
passes on this build (run 344 launched on the same exe). The
descriptor flip's writer remains unidentified (open diagnostic
thread, off the critical path).

## UPDATE 39 -- Run 344: second consecutive pass; stability bar met (Nov 9, 2026)

Run 344 (same batch-310 exe, no rebuild) passed and overshot:
the harvest344 task never fired at 18:11 (stayed Ready), so the
run was harvested manually at ~3,108 s guest time. MAX BINK
27,958 and climbing at harvest; [w256] 0, [w252] 0, gate heals 0;
handlers balanced; quarantine 0; AV mentions 2 (console chatter,
same benign class as 343's 1). The transient zeroed [w300]
vtable fields seen at the 18:28 probe read back to the standard
settled values (0x803E1E80 / 0x8023B744) in the final sample -- a
sampling phase, not a state change.

Two consecutive full passes on one build (343: 1800 s, 344:
~3100 s). Layer 2 stays closed. Next is Brandon's call: menu
driving/gameplay past the attract loop, the movie color
conversion, the diagnostic-cleanup decision, or Phase 5.
