# Addendum to HANDOFF-2026-10-30 — Nov 1, 2026: session A results and the shutdown-counter decode

Supersedes the suspect ranking in Open Problem 1 and the framing of Open
Problem 3 of the original handoff. Read the original handoff first for
setup, paths and commands; this file only carries what Nov 1 changed.

## Session A (pad, as-is) — banked

Files: `cttr-perf-pad-20261101-173329.csv` and `cttr-run-pad.log`, run
Nov 1, 2026 on the LOQ, plugged in. The logger worked end to end: the
window title carries the FPS counter, so the CSV has per-second FPS,
total CPU, and per-thread CPU. The hot emulation thread was 38280.

Segments, by shape (no markers were dropped, so this segmentation is
inference, and which stretch was the standalone race is unconfirmed —
Brandon loaded into the world hub and the session was cut short to
charge the controller):

- Startup ~7 s: a loader thread pegged at ~100% of a core, no title yet.
- Title: ~27-29 FPS, emulation thread pegged at ~99-101%.
- A flat 30.0 FPS plateau for ~25 s with the emulation thread at only
  ~46-63%: paced by something else (likely a menu screen), NOT CPU-bound.
- A heavy stretch of ~40 s at ~19 FPS typical, dips to 9.9-16, thread
  pegged 97-101%.
- A lighter stretch of ~30 s at 41.5-53.4 FPS, thread still pegged.
- A final ~35 s at ~29-40 FPS, thread pegged.

Conclusion: outside the plateau, the session is bound by one emulation
thread at ~100% of one core; total process CPU is essentially that
thread. No graphics/driver thread ever runs hot.

## The shutdown counters, decoded from the runtime source

Source: ExpansionPak/RecompCore, branch `moderngekko-vendor`,
`Source/Core/Core/PowerPC/StaticRecomp/`, read Nov 1, 2026. Session A's
shutdown line:

```
native=2664053959 fallback=0 native_exc=368491 hook_fb=275313796
smc_failed=1 verifications=1653 reverify_events=16 bursts=23420507
cycles=49152935596
```

- `native` = m_native_dispatches: calls into the recompiled module.
- `fallback` = m_fallback_steps: Dolphin-interpreter single steps. That
  path is taken ONLY for forced-fallback ranges (config
  MAIN_STATICRECOMP_FALLBACK_RANGES / env STATICRECOMP_FALLBACK_RANGES;
  neither is set here) or when no fallback JIT exists. A Jit64 IS
  created in StaticRecompCore::Init, and Run's non-dispatchable path
  calls Jit64->Run(), which is not counted anywhere in this line.
  **fallback=0 is structural. It does not measure off-module execution.**
- The failed SMC chunk [0x80369860,0x8036D860) is not dispatchable
  (DispatchableAt requires CHUNK_VERIFIED), so when the game executes
  code there, **Jit64 runs it — JIT speed, not interpreter speed**. The
  log line's word "interpreter" is the runtime's loose wording.
  smc_failed=1 means exactly one chunk fails verification; it was
  invalidated 16 times in this session (reverify_events; the tee'd log
  shows 14 mismatch lines, all flushed at the end of the file because
  stdout was a pipe, so line position in that log means nothing).
- `hook_fb` = m_hook_fallback_instructions: native code hitting
  unmodeled instructions (DMA mtspr, cache ops, ...). dcbf/dcbst/dcbi/
  icbi have a fast path with no round trip; other instructions pay
  SyncOut → interpreter SingleStep → SyncIn. 275M this session; the
  fast/slow split is not observable from the counter.
- `bursts` = SyncIn..SyncOut native runs; ~2,100 charged cycles per
  burst on average, consistent with timeslice exits dominating.
- `cycles` = guest cycles charged by native dispatches only. 49.15e9
  over the ~163 s logged span is ~62% of the 486 MHz real-time budget;
  the remainder is an unseparable mix of JIT execution, plateau
  pacing/waits, and sync overhead.

## Revised suspects for Open Problem 1

1. **JIT-executed code** (the failed SMC chunk plus any other
   non-module code). Unmeasured. Measure with a sampling profiler
   (Very Sleepy class) attached during one race: samples in anonymous
   executable memory = JIT-compiled guest code; samples in
   gG9RE7D_recomp.dll = native recomp; samples in moderngekko-run.exe
   = Dolphin core / GX / Vulkan submission.
2. **The forced-interpreter A/B**: launch with
   `STATICRECOMP_FALLBACK_RANGES=80369860-8036D860` to force that range
   onto the true interpreter. If hub/race FPS craters, the chunk is hot
   under JIT today. If nothing changes, the chunk is cold and suspect 1
   dies for this chunk.
3. **Slow-path hook fallbacks** — only if the profiler shows
   HookInstructionFallback hot; the counter alone cannot convict it.
4. **Pad path** — session B (ini renamed away) is still owed; the
   controller needed charging. Session A shows the bound thread is the
   emulation thread, but the A/B remains the clean control.

## Open questions for Brandon

- Which CSV stretch was the standalone race?
- Was the flat-30 plateau a menu screen?
