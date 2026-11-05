# Runbook: wiicompiled spike for CTTR

Written Nov 2, 2026. Purpose and pricing rationale:
docs/CHASSIS-DEEP-DIVE-2026-11-02.md. Prepared files live in
`port/wiicompiled-spike/projects/cttr/` (recomp.yml + MAP.txt, the map
converted from the decomp's CC0 symbols.txt by
`tools/dtk-to-wiicompiled-map.py`: 25,203 functions).

The spike's deliverable is two lists, not a game: what the translator
chokes on, and which HLE functions the runtime link is missing. Stop
when both lists exist. Booting is a separate decision.

## Where it runs

On the LOQ, inside the existing spm-nx clone's WiiCompiled tree
(C:\dev\spm-nx\wiicompiled), in WSL, the same environment that already
builds SPM's generated code. Brandon's verified main.dol stays on his
machine; nothing game-derived is sent anywhere.

## Steps

1. Copy the prepared project in:
   `cp -r port/wiicompiled-spike/projects/cttr /mnt/c/dev/spm-nx/wiicompiled/projects/cttr`
   (adjust the source path to wherever this repo sits relative to the
   shell; the destination is the point).

2. Fill in the two SDA constants in projects/cttr/recomp.yml.
   They are the lis/ori pairs __init_registers (0x8000539C) installs
   into r13 (_SDA_BASE_) and r2 (_SDA2_BASE_). Read them from the DOL
   with the decomp toolchain's objdump, e.g.:
   `powerpc-eabi-objdump -D --start-address=0x8000539C --stop-address=0x80005440 /mnt/c/Games/CTTR/cttr/build/G9RE7D/main.dol`
   and note the two built-up constants. The generic-dol.yml comment
   describes the same procedure. Do not proceed with the placeholders:
   a wrong SDA base poisons every small-data access silently.

3. Point the translator at the DOL:
   `export RECOMP_CTTR_DOL=/mnt/c/Games/CTTR/cttr/build/G9RE7D/main.dol`

4. Build the translator CLI (skip if the SPM flow already built it):
   `dotnet build translator/src/Translator.Cli/Translator.Cli.csproj -c Release`
   and define the same `translator` shell function the framework docs
   use (docs/building-macos.md, step 2).

5. Translate from the entry point (0x80005240, __start):
   ```
   mkdir -p generated/cttr/functions build/cttr/base
   translator translate-recursive 0x80005240 \
     --project projects/cttr/recomp.yml \
     --outdir generated/cttr/functions \
     --output-metadata generated/cttr/base_translation_output.json \
     --no-function-files \
     --prune-stale \
     --threads $(nproc)
   ```
   Save the full console output. Unsupported instructions (allowed by
   config, so they are reported, not fatal), unreachable functions and
   data complaints are all spike data.

6. Emit the manifest and data initializer:
   ```
   translator emit-base-manifest --project projects/cttr/recomp.yml \
     --out build/cttr/base \
     --functions-dir generated/cttr/functions \
     --translation-output-metadata generated/cttr/base_translation_output.json \
     --region E
   translator generate-data-init --project projects/cttr/recomp.yml
   translator emit-build-shards --project projects/cttr/recomp.yml \
     --base-metadata generated/cttr/base_translation_output.json \
     --base-functions-dir generated/cttr/functions \
     --native-source-dir runtime/src \
     --out generated/cttr/build_shards
   ```

7. Attempt the runtime build against the generated shards using the
   same CMake flow the macOS doc uses for mkwii after this point
   (docs/building-macos.md, step 4 onward), substituting the cttr
   paths. Collect every undefined-symbol / missing-function error
   into one list. That list is the runtime gap inventory. Expect the
   CARD family to be on it; anything else on it is new information.

## Send back

- The translator's console output from steps 5 and 6 (or the tail if
  enormous, plus any error summary).
- The missing-functions list from step 7, verbatim.
- The two SDA values used, so the prepared recomp.yml can be
  completed in the repo.

## Stop conditions

- Both lists captured: spike complete, pricing conversation follows.
- Translator refuses the DOL outright (bad header assumptions, Gekko
  encoding it cannot decode even permissively): also a result; send
  the error verbatim and stop.
- Anything asking for game files to leave the LOQ: stop, that is
  outside the project's rules.

## RESULTS (Nov 2, 2026) — spike complete, link closed

Run live with Brandon on the LOQ in one session. Both deliverable lists
were captured, and with Brandon's go-ahead the link was then closed
entirely. Booting the executable was NOT attempted; that remains a
separate decision.

### Translation

- Whole DOL translated in ~20 s: 25,270 functions (map 25,203 + 67 from
  the call-graph walk). SDA bases decoded from __init_registers:
  r13 = 0x804AB980, r2 = 0x804B6F80.
- 3 unsupported instructions, all `bso` (branch if summary overflow):
  0x802D7010 in NGC_SoundInit, 0x802D94A4 in BinkOpen, 0x802E4758 in
  BinkAudioDecompressOpen. Root cause: Translator's PpcLifter.cs plain
  conditional-branch group omitted the `bso`/`bns` case labels (decoder
  and code generator already handled them). Fix: two case labels,
  delivered as tools/patch-lifter-bso.py. Retranslation: clean, zero
  developer output, release-eligible.
- The one translation warning (0x803433FC branches to 0x00000060) is
  __OSDBJump, the SDK debugger trampoline; dead on retail, closed.
- Framework friction: emit-base-manifest hard-requires a configured REL
  (CTTR has none), so that stage is unusable for DOL-only GC projects;
  skipped by design. Shards and data-init do not need it.

### Windows build recipe (what actually works)

- Toolchain: llvm-mingw 20260616 (clang 22.1.8, matches the Launcher's
  clang-22 fingerprint), prefixed drivers x86_64-w64-mingw32-clang(++)
  passed via CC/CXX environment variables (MSYS2-flavoured cmake
  mangles -D compiler paths).
- CMake MUST be the vanilla Kitware build. MSYS2's cmake and its
  pkg-config advertise the clang64 prefix to find_package, which
  "found" ZLIB/BZip2 there; their root include dir then rode into
  aurora_gx as -isystem and shadowed llvm-mingw's libc++ headers.
  Symptom was aurora_gx math.h macro errors (fpclassify/isfinite).
  MSYS2 clang64 also fails earlier on its own: its headers hide the
  WinRT string APIs abseil's cctz needs, and -D_WIN32_WINNT=0x0A00
  does not cure it.
- PATH scrubbed to llvm-mingw\bin + System32 + Windows, Launcher-style;
  cmake/ninja invoked by absolute path. Canonical flags from the
  Launcher's NativeBuildFlags.ps1: AURORA_DAWN_PROVIDER=package,
  AURORA_SDL3_PROVIDER=vendor, CMAKE_SYSTEM_PROCESSOR=x86_64,
  CMP0168 NEW, AWK blanked (libpng uses its prebuilt pnglibconf.h).
- C++/WinRT headers are generated, not shipped: Microsoft.Windows.
  CppWinRT 3.0.260818.1 nupkg, cppwinrt.exe -input local -output
  <dir>, passed as -DMKW_CPPWINRT_INCLUDE_DIR. Needed by the runtime's
  music_attenuation.cpp (Windows.Media.Control) on _WIN32.
- Runtime build consumes root generated/ paths; the project's three
  files (RuntimeConfig.h, data_sections_init.cpp,
  guest_symbol_table.cpp) were staged there, SPM's originals preserved
  in generated/spm-stash. Shards were pointed at the nested cttr lane
  via -DMKW_TRANSLATED_SHARD_MANIFEST.

### Link inventory

The full build (911 targets: runtime, aurora, all 72 CTTR shards)
reached the final link with exactly **3 undefined symbols**:

- func_8026C8E8, referenced by the runtime's alarm queue processing
  and OS__SetPeriodicAlarm
- func_80275A58, referenced by OS__SetPeriodicAlarm
- func_8026DE74, referenced by SelectThread

All three are interior entry points into small unnamed SDK OS
functions (offsets +0x14, +0x28, +0x14 from the mapped starts
0x8026C8D4, 0x80275A30, 0x8026DE60) that the runtime's OS HLE calls
directly. Nothing else was missing: no CARD, DVD, PAD, AX/audio or
Bink symbols. The runtime's HLE covers CTTR's entire SDK surface at
link level with zero new runtime code.

Fix: add the three addresses as function starts in MAP.txt (25,206
entries), retranslate (25,273 functions, 25,265 shared), re-emit
shards, incremental rebuild. **WiiCompiled.exe links clean.**

### What this does and does not prove

Proves: the translator digests CTTR completely; the runtime's HLE
surface covers the game at link level; the per-game bring-up cost to
a linked executable was one 2-line translator patch plus 3 map splits
plus a (now documented) Windows toolchain recipe.

Does not prove: that it boots or runs. Untested risk areas, in
expected order: (1) the 16 KB runtime-loaded code chunk at
0x80369860 — this chassis has no interpreter/JIT, so execution
reaching untranslated code has nowhere to go; (2) CARD save behaviour
at runtime (links != works); (3) the audio library/DSP microcode
identity; (4) GX Flipper-vs-Hollywood deltas under Aurora.

Artifacts on the LOQ: wiicompiled lanes projects\cttr, generated\cttr,
build\cttr, build-cttr, logs cttr-*.log; toolchain at C:\dev\llvm-mingw
and C:\dev\cppwinrt-headers. Cleanup (delete the four lanes, restore
generated\spm-stash) only when the spike is declared parked.

## Postscript (Nov 2, 2026, evening): shared-tree revert + boot-test status

A first boot attempt reached the runtime's disc validation and stopped
there by design: this tree is the SPM product, and both intake paths
(disc-image decrypt and extracted-folder check in game_folder.cpp)
hard-require SPM (kGameId "R8PE01", revision 0). CTTR's ISO was
rejected as "not a plain Wii disc"; an extracted CTTR folder would be
rejected on the ID check. The identity flip is one constant, and the
framework's own PAL variant is produced by rewriting exactly those
constants, but Brandon has live SPM work in the same tree and directed
that CTTR must not mutate it.

Accordingly, the spike's two mutations to SPM-owned state were
reverted the same evening and verified with git status (no tracked
modifications remain):
- translator PpcLifter.cs bso/bns patch: checked out; translator
  rebuilt from pristine source so the compiled CLI matches.
- The three root generated/ files staged for CTTR: SPM's originals
  restored from generated/spm-stash.
Additive lanes (projects/cttr, generated/cttr, build/cttr, build-cttr,
logs) remain on disk; they are untracked/gitignored and inert for SPM
builds. The bso/bns fix, if it is ever kept, should land as its own
considered translator change (it is a genuine upstream bug: decoder
and code generator already handled bso/bns; only the lifter's case
group omitted them), not as spike residue.

Boot test: to run in a SEPARATE copy of the tree (Brandon's call),
with the G9RE7D identity flip applied there only.

## Postscript 2 (Nov 2, 2026, evening): first guest execution

In the separate tree (C:\dev\cttr-wiicompiled), two identity fixes
were needed before guest code ran at all:
- game_folder.cpp kGameId "R8PE01" -> "G9RE7D" (disc validation).
- system_bridge.h kDefaultEntryAddress 0x80006124 -> 0x80005240.
  0x80006124 is SPM's __start, hardcoded; the runtime boots the guest
  at that constant. (The 80006124 map split added earlier was chasing
  this: harmless, not needed. The runtime's clean exit in that run
  was it calling mid-fn_80006110 as the "entry" and returning 0.)

With the entry fixed, the runtime entered func_80005240 (__start)
and CTTR's own startup executed in translation until OSInit's
interrupt init wrote the GameCube PI interrupt-mask register
0xCC003004, which the runtime blocks: "MMIO write blocked (non-GPU)".
The runtime replaces SDK functions with HLE implementations bound
per game by guest address (PPC_NATIVE_OVERRIDE + address-suffixed
extern "C" symbols); raw guest MMIO is blocked by design. None of
CTTR's addresses are bound yet, so its SDK code runs raw until it
pokes hardware. The existing HLE catalog already covers the OS
init/interrupt family; CTTR's counterparts are named in the decomp
symbols (OSInit 0x80342C78, __OSInterruptInit 0x80347C64,
__OSInitMemoryProtection 0x803488E4, ...). Next campaign, when
called: bind the OS-init family at CTTR's addresses in the separate
tree and iterate run-by-run. The shared SPM tree was not touched by
any of this.

## Postscript 3 — HLE bring-up campaign (Nov 2, 2026, evening)

All work in the separate tree C:\dev\cttr-wiicompiled. Method: run,
read the fault, bind the named SDK function at CTTR's address to an
existing HLE impl (or a small CTTR stub), re-emit shards (REQUIRED
after any override add, else duplicate func_ symbols at link),
rebuild, run. Shared-function count ticks down one per binding
(25,266 at campaign start).

Bound so far: batch 1 OS interrupt family + __OSInitMemoryProtection;
batch 2 EXIInit/EXISelect/EXIDeselect + __OSInitSram stub (seeded
SRAM defaults); batch 3 SIInit/SISetSamplingRate; batch 4
__OSInitAudioSystem; batch 5 DVDInit (HLE indexed the extracted
folder: 38 files, FST published); batch 6 ARInit CTTR stub (seeds the
AR allocator globals in .sbss for a stock 16 MB ARAM; no ARAM device
exists in this runtime). Batch 7 (OSSetResetCallback stub)
issued, result pending. OSInit completed; static ctors completed;
the game is inside main()'s own init now.

Two infrastructure findings worth more than the bindings:

1. DATA BLOBS: the generated data_sections_init set (.cpp + blobs +
   .S) is a matched set or it is poison. The spike's three-file swap
   moved the .cpp without its blobs, so the loader memcpy'd another
   game's 2,176-byte _sdata blob with CTTR's 39,936 size, overrunning
   into neighboring blob bytes (PPC code landed at .sdata addresses;
   SwitchThreadCallback read back as an instruction word). Fix was
   regenerating into build/cttr and copying the WHOLE set over.
   Compounding trap: Copy-Item preserves source timestamps, so ninja
   then reported "no work to do" — touch the copied files before
   rebuilding. generate-data-init writes to the project output root
   (build/cttr per recomp.yml), NOT to the root generated/ the build
   consumes.

2. AURORA DIVIDE: a Pure3D static ctor called GXSetDispCopyYScale
   before any display mode existed (vscale 0). The SDK does this math
   in float (harmless /0); aurora's get_num_xfb_lines_internal does
   it in integers with a CHECK that compiles out in Release ->
   SIGFPE (0xC0000094). Patched in the copy's aurora: early return 0
   when efbHeight or iScale is 0. Diagnosis path that worked when
   the runtime's stack walker only named exports: module offsets are
   stable across runs; llvm-symbolizer --relative-address resolved
   them to GXSetDispCopyYScale + its thunk caller exactly. Also:
   the runtime refuses non-Release builds (CMake guard), and its
   own VEH handler swallows first-chance exceptions under lldb.

Process notes: after a crash, kill any lingering WiiCompiled.exe
before linking (locked exe = silent stale-binary rerun). Brandon
pastes whole blocks; the terminal's multi-line paste warning is
noise. Crash artifacts + full transcripts land in
MarioWiiSaveData\Logs\base_* folders (MEM1 snapshots included).

## Postscript 4 (Nov 3, 2026 evening): batches 7-23, the hang, the scheduler war, first light

Tooling: lldb is a DEAD probe for this process (the runtime's VEH
handler eats the faults; three attempts produced nothing). The
replacement is an external ReadProcessMemory sampler
(tools/hang-sample.py -> v4): host RIP histograms + guest OS state
through the flat mapping at 0x100000000000 + guest VA (guest data
is big-endian). v4 enumerates threads from the OS list head at
low-mem 0x800000DC (the current-thread slot can read 0 under the
HLE) and prints saved SRR0 (+0x198 in OSContext; the +0x8C field
earlier samplers called "pc" is XER).

Batches 7-10 (Nov 2 late): OSSetResetCallback stub (PI write);
GXInit CTTR twin in gx_init.cpp (FifoObj 0x804999C0, gxData
0x80499A40, __GXData var 0x804B2360, reg base vars seeded); five VI
bindings + retargeted VI retrace count/queue vars to CTTR
(0x804AEB64 / 0x804AEB6C); VISetPre/PostRetraceCallback bound.
Milestone: OSInit + ctors + main init chain all run; boot then
HUNG after the DVD read cache with both guest threads waiting on
the retrace queue and retraceCount stuck at 0.

The hang (Nov 3): every AdvanceRetrace pump sits downstream of
executor activity (HLE idle loop, GX worker); the guest scheduler
owned the executor, so no retrace ever fired. Sampler v2/v3
showed the executor parked inside guest SelectThread and a
coherent guest state with a missing event.

Batch 11: VIWaitForRetrace 0x80351410 bound to the runtime's HLE
(sleeps via the HLE scheduler; the idle loop pumps retraces).
State transformed but still stuck: the executor spun in a guest
list-walk (func_80265A40).

Batch 12: retargeted the HLE scheduler's queue constants to CTTR
in os_internal.h + fiber_manager.cpp (RunQueue array 0x8047DB18,
RunQueueBits 0x804AEA78, RunQueueHint 0x804AEA7C). Necessary, not
sufficient; state identical.

Batch 13 (the real poison): the HLE called three guest helpers by
HARDCODED SPM ADDRESSES: os_scheduler.cpp's OSSaveContext helper
func_8026DE74, os_alarm.cpp's func_80275A58 (__OSTimeToSystemTime)
and func_8026C8E8 (InsertAlarm). In CTTR those are unrelated game
functions; every HLE schedule/alarm op called wrong code with
scheduler pointers. Redirected to CTTR's real ones: OSSaveContext
0x80344DDC, __OSTimeToSystemTime 0x8034B838, InsertAlarm
0x80343620. DEADLOCK BROKE immediately.

Batch 14: the HLE scheduler resumed the main thread at its
guest-saved SRR0 0x8034A908 (mid-SelectThread) ->
InvokeIndirectJump "not a registered function". Added MAP split
8034A908 (MAP.txt now 4 splits).

Batch 15: the resume landed but OS__LoadContext is [[noreturn]]
and aborts when a resumed function-tail segment returns. Patch
(tools/patch-loadcontext-return.py): drop [[noreturn]], final
abort -> return. Result: an infinite ping-pong: the mid-scheduler
tail segment returns instantly, the thread never progresses.

Batch 16: bound guest SelectThread 0x8034A804 -> HLE
SelectThread_801a9c08 so ALL guest blocking funnels into the HLE
scheduler. Milestone: [place] boot -> logo; retraces fire; window
presents (black). New stuck shape: both threads WAITING on GX
FinishQueue / a stack-local queue; fiber manager and guest
current-thread identity had diverged (A's saved context held B's
stack pointer).

Batch 17: bound the thread family to the HLE (OSCreateThread
0x8034AA98, OSExitThread 0x8034AC80, OSCancelThread 0x8034AD64,
OSJoinThread 0x8034AF20 in os_thread.cpp; OSResumeThread
0x8034B060, OSSuspendThread 0x8034B2E8, OSSleepThread 0x8034B458,
OSWakeupThread 0x8034B544 in os_scheduler.cpp; placement matters:
impls must be declared in the file the override lands in).

Batch 18 (tools/patch-spm-addrs-os.py): retargeted six more SPM
literals in the OS HLE: OSInitContext invoke 0x8026E058 ->
0x80344F90; new-thread LR 0x8027510C -> 0x8034AC80;
__OSErrorTable+0x40 0x804F5270 -> 0x8047D7D0;
__OSFpscrEnableBits 0x8056D278 -> 0x804AD3C0;
__OSUnlockAllMutex invoke 0x802733D0 -> 0x80348BD8;
kSwitchThreadCallbackPtrAddr 0x8056D2A0 -> 0x804AD3E0. (Found
when HLE OSCreateThread jumped to SPM's OSInitContext address.)

Batch 19 (tools/patch-gx-drawdawn.py): A was sleeping in guest
GXDrawDone on FinishQueue (0x804AEDE4); the only waker is the PE
finish interrupt handler, which never runs here. Bound CTTR
GXDrawDone 0x80366B44 -> HLE GX__DrawDone_8016eab0 (aurora wait +
finish handler) and retargeted kGxDrawDoneFlagAddr -> 0x804AEDE0
(DrawDone), kGXDataPtrAddr -> 0x804B2360, kPeThreadQueueAddr ->
0x804AEDE4. Milestone: video init COMPLETED; boot advanced into
the memory-card init chain. Watch items from that run: an absorbed
unmapped write to 0x7E000004 from fn_802393A8 (texture-ish loop,
recurs since batch 5 in another form), and the shell's SPM splash
font/readout noise (cosmetic).

Batch 20: CARDInit -> OSGetFontEncode reads __VIRegs[VI_DTV_STAT]
at 0xCC00206E (DTV status reg; identified from the decomp's
OSFont.c). Bound CTTR OSGetFontEncode 0x80347344 -> the runtime's
existing OSGetFontEncode_HLE_801b00a0 (os_font.cpp).

Batch 21: CARDInit -> DSPInit reads __DSPRegs[5] at 0xCC00500A.
Bound DSPInit 0x8035C030 -> DSPInit_8015d444 and DSPCheckInit
0x8035C0F4 -> DSPCheckInit_8015d504 (audio.cpp). Note the HLE
DSPInit does not set the guest __DSP_init_flag (0x804AED68);
guest-side DSPCheckInit callers now get the HLE's answer.

Batch 22: CARDInit -> EXIProbeEx reads EXI0 CSR at 0xCC006800.
The runtime has NO CARD HLE and no card device; adopted honest
no-card semantics (a normal console state): CTTR stubs in
os_interrupt.cpp: EXIProbe 0x8036E6E4 -> 0, EXIProbeEx
0x8036E764 -> -1, EXIGetID 0x8036F3B0 -> 0 (contracts from the
decomp's EXIBios.c). CARDInit then completes.

CURRENT FAULT (Nov 3, 21:24 NST) — mechanism PROVEN from the
mem1.bin snapshot (base_1793753637_pid33492; forensics scripts
tools/mem1-forensics*.py, capstone PPC disasm of the loaded DOL):
after CARDInit, boot hits a jump to guest 0x0 from
fn_8024FA00+0x58. Call chain proven from thread A's stack:
fn_801608DC+0xA8 -> fn_8024F7B0 (0x8024F878) -> fn_8024FA00(obj)
with obj = the singleton at *(r13+0x2AB0) = 0x804AE430 (snapshot
value 0x809434D8). fn_8024FA00 drains a pointer ring at obj+0x2C
(cursors q[0]=pop, q[1]=push, q[2]=start, q[3]=end), calling
element->vtable[5] then vtable[3] per element. [CORRECTION,
Postscript 5: an early +1-sentinel reading of the count helper
was wrong — the helper returns a plain cursor distance, the
translator's shard code is verified correct, and the completion
ring is legitimately empty; see Postscript 5 for the verdict.]

## Postscript 5 (Nov 3, 2026 late): the drain crash, forensic verdict

Push-side trace completed offline (reliable single-pass BL scan +
capstone): the singleton is the game's async file loader.
Requests (8-byte elements, ring at +0x18) are serviced by
fn_8024F5A0 (sole caller: the loader pump fn_8024F7B0 at
0x8024F8EC); it pops a request, and pushes a completion into the
+0x2C ring (push fn_8025012C, sole caller 0x8024F600) ONLY when
the request element's second word (its completion handle) is
nonzero. The snapshot's one pending request is "dummy.p3d" with
handle 0 — fire-and-forget by design, so the empty completion
ring is CORRECT state. The translator-bug theory (srawi/addze
carry in the count helper) was tested against the actual shard
code and is DEAD: the lifter models the srawi carry correctly
and the translated count returns 0 for the empty ring, matching
hardware. The crash executes on the game's own loader fiber
(block at 0x80450058: entry fn_8024F8E0, arg = the loader,
context r1 = 0x8094A360 — the crash stack), a cooperative fiber
layer the game runs on top of guest OSSaveContext/OSLoadContext
(switch fn_8024C870; per-thread block pointer at OSThread+0x2F8).
The drain's helper fn_8024FA94 itself calls that fiber switch.
Verdict: root-cause CLASS is the guest cooperative fiber switch
vs the HLE fiber scheduler interop — the same seam as batches
13/16, now inside the loader pump; the snapshot's preserved
state is post-switch and self-consistent, so the phantom pop's
exact register state is not recoverable from it. NEXT STEP when
resumed: audit how guest OSSaveContext (0x80344DDC) /
OSLoadContext (0x80344D64) calls interleave with the HLE
scheduler (the HLE already invokes the guest OSSaveContext as a
helper, batch 13); candidate fix is binding CTTR OSLoadContext
to the runtime's OS__LoadContext HLE so both schedulers share
one context model. Do NOT guess-apply it in a late session:
test it as its own batch with the loader pump as the test case.

Shared-function count after batch 22's emit: 25,226 (25,275 base).
Corrected translate command for Windows (no --no-function-files;
see batch 14 notes in the session record). Remaining known
suspects on the board: kInterruptHandlerTablePtrAddr (NSMBW
0x8056db88, CTTR var 0x804AEA28, not retargeted); the alarm HLE's
kAlarmQueueOffsetFromR13 (SPM-derived; CTTR AlarmQueue 0x804AE9F0
= r13 + 0x3090, sign flips) if any HLE alarm path ever runs;
os_interrupt.cpp's kDefaultCallbackAddr 0x80276544 (SPM) in an
interrupt-callback path; the whole AX/DSP task stack beyond
DSPInit; real CARD support (dir-based, like ModernGekko's) as a
later campaign.

## Postscript 6 (Nov 3, 2026, late): the fiber switch works; the drain crash is register clobbering on the unwind

Batches 23-25 landed and are KEEPERS:
- Batch 23: bound CTTR OSLoadContext 0x80344E5C -> OS__LoadContext_801a1f58 (os_context.cpp). Proof it was the right seam: the next run's fatal moved to missing-target 0x8024C8AC, the exact resume point after OSSaveContext inside the guest fiber switch fn_8024C870.
- Batch 24: MAP split 8024C8AC (5 splits now; 25,276 functions). The switch then ran BOTH directions (log: LoadContext ctx=0x80450078 -> trampoline 0x8024C8E4; ctx=0x8044E738 -> resume 0x8024C8AC).
- Batch 25: removed [[noreturn]] from OS__LoadContext_801a1f58's declaration in os_internal.h:160 (batch 15 had only fixed os_context.cpp's definition). The override thunk (CountedAbiRawCpuThunk<0x80344E5C, &OS__LoadContext_801a1f58>::Invoke) was compiling the return path as unreachable and trapping int3 (0x80000003) when the impl returned. Symbolizer offsets: use the runtime stack's printed module+ offset, NOT a hand-computed base subtraction (0x284C3F was right; 0x384C3F wasted a round trip).

Result: the dummy.p3d load now COMPLETES through the fiber (descriptor state 1, sizes filled; ring1 request consumed), the switch round-trips, and boot reaches retrace ~64-69 before the ORIGINAL drain crash (Caller LR 0x8024FA58, target 0) recurs, deterministically, identical across runs (rules out a race).

ROOT CAUSE (verified by elimination; every guest primitive and every translated shard body in the drain path was read and is CORRECT: count fn_802501DC incl. wrap path + ctx store-back, peek fn_8025028C, push fn_8025012C, advance fn_80250224, store helper fn_80250AA8, FA00's loop test loc_8024FA6C): the game's cooperative fiber switch returns THROUGH the nested HLE invocations. On hardware OSLoadContext never returns and a fiber resumes via its saved srr0 (0x8024C8AC); the instruction after the switch's OSLoadContext call (0x8024C8C4) is dead code. In the nested-invocation model that fall-through EXECUTES when the inner invocation returns, running the switch's and FA94's epilogues with the OTHER fiber's register values in the single shared CpuContext. FA00 then reloads r30 from ctx->gpr[30], which holds a fiber-BLOCK pointer (0x8044E718 / 0x80450058) instead of the loader singleton, so the "count" reads block fields as ring cursors, returns garbage nonzero, and the drain pops a null element. Post-crash snapshots therefore show a pristine empty ring2 in both runs — the ring was never the problem.

DESIGNED FIX (batch 26, next session): HLE-own the switch itself. PPC_NATIVE_OVERRIDE for fn_8024C870 with a custom impl built on the runtime's host fiber manager (the same machinery OSCreateThread_HLE uses): keyed by guest block address; fresh fibers enter via the guest trampoline semantics (block[0] = fn 0x8024F8E0, block[1] = arg = loader); a switch yields the current host fiber and resumes the target's, so no guest frame ever executes the dead fall-through and each fiber keeps its own host CpuContext/stack. Audit first: remaining guest callers of OSLoadContext 0x80344E5C besides fn_8024C870 (the batch-23 binding may become unnecessary; the 0x8024C8AC split stays harmless either way). Do NOT keep guessing at the drain; it is exonerated.

## Postscript 7 (Nov 3, 2026, late evening): FIBER SWITCH SOLVED; boot is in audio bring-up

Batch 26 (patch-gamefiber-switch.py, os_context.cpp): HLE-owned the guest fiber
switch fn_8024C870 (GameFiberSwitch_CTTR) on the runtime's HostContext backend.
Each guest fiber block maps to a real host fiber (1 MB host stack) with its own
saved CpuContext; the switch saves *ctx, restores the target's, HostContext::Switch.
Fresh fibers boot by reusing OS__LoadContext on the block's guest OSContext
(srr0 = trampoline 0x8024C8E4). Batch 26b (patch-gamefiber-node.py): the current
block lives in the game's own thread-wrapper registry, NOT the OSThread struct —
fn_8024C65C walks the list headed at *(r13+0x2A78) (CTTR head value 0x8044E710 for
thread A), matching node+0x310 against OSGetCurrentThread(); the block pointer is
node+0x2F8 and the fiber object is embedded at node+8 (so the "home block"
0x8044E718 = node_A+8, a pure save slot with fn=0, never a trampoline target).
GameFiberCurrentNode mirrors that walk; the first version's write to
OSThread+0x2F8 landed where nothing reads it and the trampoline called fn=0.
With 26b the loader pump cycles cleanly: THE DRAIN CRASH IS GONE.

Audio frontier (the boot now dies inside the sound-engine init chain,
fn_8018BB98 -> ... -> fn_8027CC48 (game audio init) -> AX library):
- Batch 27 (patch-ai-family.py, audio.cpp): retargeted the AI HLE's four
  guest-state constants to CTTR's .sbss (same order as decomp ai.c:
  __CallbackStack 0x804AEC00, __AID_Callback 0x804AEBFC, __AI_init_flag
  0x804AEC08, __AID_Active 0x804AEC0C) and bound AIInit 0x80354B60,
  AIInitDMA, AIRegisterDMACallback, AIStartDMA, AIGetDSPSampleRate to the
  runtime impls, plus CTTR stubs for AIStopDMA and AISetDSPSampleRate
  (g_ai-backed). AIInit passed.
- Batch 28 (patch-dsp-tasks.py, audio.cpp): bound DSPAddTask 0x8035C0FC,
  DSPAssertTask 0x8035C1AC, __DSP_boot_task 0x8035C888 to AxDspHle impls.
  DSPAddTask passed.
- CURRENT FAULT (console-32/crash_sigabrt-8, mem1_8): MMIO read 0xCC005036
  (AR register block) inside __AXOutInit+0x388 (guest LR 0x80358758) — the AX
  output init is starting ARAM DMA work. NEXT BATCH (29): the AR/ARAM-DMA
  family — check what AxDspHle/the runtime models for ARStartDMA
  (guest AR functions live near 0x803551A0 ARInit, already stubbed batch 6;
  find ARStartDMA/ARGetDMAStatus in CTTR symbols + the runtime's aram
  handling) and bind/stub accordingly. Watch items carried: HLE DSPInit does
  not set guest __DSP_init_flag (0x804AED68); the AI stream family
  (AISetStreamPlayState etc.) is still translated and will fault on AI
  register writes when reached.
Shared-function count after batch 28's emit: ~25,210 (25,224 after batch 26,
minus 7 AI bindings, minus 3 DSP bindings, minus stream/stub deltas — read the
copy44 emit line to confirm when convenient).

Batch 29 target (identified Nov 3, 23:20 NST, not yet patched): the 0xCC005036
read is NOT in __AXOutInit or __AXNextFrame's own body (no fixed-offset loads
there). Chain: AXInit -> AXInitEx+0x38 -> __AXOutInit -> __AXNextFrame
(0x80357914, called at __AXOutInit+0x324/+0x354). __AXNextFrame's callees:
the __AX command-insert helpers 0x80357524-0x80357660, plus 0x8035880C (once,
early) and 0x803596A0 (once, +0x150). The AR-register read lives in one of
those two (or deeper). First step next session: identify 0x8035880C and
0x803596A0 in symbols.txt, disassemble, then bind the AR family member
responsible (ARGetDMAStatus 0x80355074 / __ARGetInterruptStatus 0x80355304 are
the standing candidates if the call tree reaches them).

Batch 29 forensic verdict (Nov 3, 23:12 NST; mem1_9 is byte-identical to
mem1_8, md5 e146a6c8...): the 23:20 target above is WRONG. 0x8035880C =
__AXGetStudio and 0x803596A0 = __AXGetPBs, both 0xC-byte leaf getters,
innocent, and __AXNextFrame had already returned when the fault hit.
0xCC005036 is __DSPRegs[27] (DSP_DMA_CONTROL_LEN, hw_regs.h), NOT an AR
register. Snapshot state pins the fault to the __AXOutInit tail:
__AXOutputBufferMode (0x804AED08) = 0, __AXOutDspReady (r13+0x3360) = 1
already stored, __AXOutFrame/__AXAiDmaFrame = 0, stale dispatch ctx
r3 = 0x80481CA0 (__AXOutBuffer) / r4 = 0x280. In that tail (decomp
AXOut.c __AXOutInit): mode-0 branch calls AIInitDMA(buf, 0x280) then
AIStartDMA(). AIInitDMA is EXONERATED: its guest body reads
__DSPRegs[24] at 0xCC005030 (lhz at 0x803547B4) before [25] and [27],
so guest execution would have faulted at 0xCC005030, not 0xCC005036 —
batch 27's AIInitDMA binding worked. AIStartDMA (0x80354818) is the
fault: its ONLY register touch is lhz 0x36(r3) at 0x80354820 =
0xCC005036, and a full-DOL BL scan shows it has exactly ONE caller,
__AXOutInit at 0x80358758 (the fault's LR; the fault record's guest
refs are stale at the last dispatch boundary, the AIInitDMA native
call, which is why r3/r4 still hold that call's args). So batch 27's
AIStartDMA binding to the external impl AIStartDMA_80124048 silently
did not take effect, while its sibling bindings in the same append
did. The VOID no-arg macro form is NOT the cause (batch 19's
GXDrawDone VOID no-arg binding in gx_stubs.cpp demonstrably worked);
leading suspect is the external impl name/symbol not resolving in
this runtime. Batch 29 patch (tools/patch-ai-startdma.py, mock-tested,
ISSUED not yet run): prints every AIStartDMA reference under
runtime/src (settles whether AIStartDMA_80124048 exists), then rebinds
0x80354818 to a local AIStartDMA_CTTR stub (g_ai.enabled = true, the
mirror of batch 27's AIStopDMA_CTTR). AIStopDMA is deliberately left
alone: its impl is already a local stub, so if it faults later the
impl-name theory dies and we learn something. Watch items after
AIStartDMA: MIXInit 0x8035AE9C and AISetDSPSampleRate (guest-called at
fn_8027CC48+0x15C; batch-27 stub binding untested from the guest side)
in the game audio-init chain, then the DSP mail leaves
(DSPCheckMailToDSP/DSPSendMailToDSP read __DSPRegs[0..3]) inside
__AXOutNewFrame when the first AX frame callback fires.

Batch 29 RUN (Nov 3, 23:20 NST; console-33 + crash_sigabrt-9 +
mem1_10): SAME fault, byte-near-identical run (41 bytes differ in the
whole 24 MB snapshot; mode/DspReady/counters identical). The local
VOID stub rebind did NOT displace guest AIStartDMA either. Full-DOL
scan for [27] readers: only __OSStopAudioSystem, AIInitDMA,
AIStartDMA, AIStopDMA exist — the identification stands, the binding
mechanism is what is failing. Pattern across audio.cpp bindings:
VOID+args works (AIInit, AIInitDMA, __DSP_boot_task), non-VOID+args
works (DSPAddTask), non-VOID+no-args works (DSPCheckInit, batch 21 —
proven by the absence of a second DSPInit HLE log from the
__AXOutInitDSP path in console-32/33), VOID+no-args has now failed
twice at this address with two different impls. (GXDrawDone's VOID
no-arg binding worked, but that lives in gx_stubs.cpp, a dedicated
stubs file — file context may matter to the emitter.) Batch 30 patch
(tools/patch-ai-startdma-r.py, mock-tested against BOTH starting
states, ISSUED): rebind 0x80354818 in the exact DSPCheckInit form —
PPC_NATIVE_OVERRIDE, uint32_t return, no args, local stub
AIStartDMA_CTTR_R returning 0 — plus post-emit verification greps of
generated/cttr/build_shards for AIStartDMA_CTTR_R, so the next run
log proves whether the emitter emitted the override at all. If the
grep is empty, the emitter is dropping this address/form and the
next route is a dedicated audio stubs file (gx_stubs.cpp pattern).

Batch 30 RUN (Nov 3, 23:35 NST; Brandon's pasted terminal transcript):
patch applied clean ("replaced the batch29 binding"); emit base
25,276 / shared 25,215; build rebuilt only unity_runtime_0 + relink;
run faulted IDENTICALLY (0xCC005036, LR 0x80358758, stale ctx
r3=0x80481CA0/r4=0x280, AIInit and DSPInit HLE lines exactly once
each, mmio=1). Third failed displacement of guest AIStartDMA at
0x80354818, second failed binding FORM (non-VOID uint32_t no-args
this time) — the macro-form theory is now dead too; something about
this ADDRESS (or its registration) resists override, not the form.
Two more facts from the transcript: (1) the patch's pre-patch
reference print settles the batch-29 open question — AIStartDMA_
80124048 DOES exist, defined at audio.cpp:303 in this same file, so
batch 27's binding pointed at a real in-file impl and still did not
take; (2) the post-emit grep for AIStartDMA_CTTR_R over build_shards
*.cpp came back EMPTY. Caveat before acting on (2): that grep was
never calibrated — it is not yet established that ANY override name
appears in shard .cpp files (known-good bindings may register
runtime-side only, with the shard-side signal being the guest
function's EXCLUSION instead). Batch 31 is therefore a no-rebuild
diagnostic first: confirm the _R binding persisted in audio.cpp,
calibrate with known-good names (AIInitDMA_80123fcc, AIStopDMA_CTTR,
DSPCheckInit_8015d504) across ALL of generated/cttr (every file
type), and check whether guest fn/func_80354818 is still present in
the generated tree. Only if the calibration proves shard .cpp is
where overrides land does the dedicated-stubs-file route trigger.

Batch 31 diagnostic RESULTS (Nov 3, 23:47 NST; no rebuild): (1) the
batch-30 binding PERSISTED in audio.cpp — line 797 defines
AIStartDMA_CTTR_R, line 802 is the PPC_NATIVE_OVERRIDE(80354818,
AIStartDMA_CTTR_R, uint32_t, (), ()); the batch-29 void stub at 793
is orphaned but harmless. (2) Section 4: exactly ONE registration
for 80354818 exists under all of runtime/src — no competitor.
(3) CALIBRATION VERDICT: override impl names appear in ZERO files
under generated/cttr for the known-good bindings too (AIInitDMA_
80123fcc, AIStopDMA_CTTR, DSPCheckInit_8015d504 all 0) — override
names NEVER land in the generated tree, so batch 30's empty shard
grep proved nothing; that verification method is retired. (4) Guest
AIStartDMA is still fully generated: functions/func_80354818.cpp
exists, and 80354818 is mentioned in build_shards/base_common/
shard_7ca4da871d8c2c05b3cb3f02.cpp — note BASE_COMMON: this tiny
pure-MMIO leaf (no game-specific addresses in its 0x18 body) is a
shared function, unlike its AI siblings whose bodies reference
game-specific .sbss globals. Working theory: base_common functions
come from the frozen base_common_shard_map.json (emit log: "reused
frozen table"), and per-game native overrides do not displace them.
Still missing the decisive comparison: whether known-good
overridden guests (80354790 AIInitDMA, 80354B60 AIInit, 8035C0F4
DSPCheckInit) are ABSENT from build_shards while 80354818 is
present, plus the shard context lines for 80354818 (definition vs
table entry) and the func-file heads. That is diagnostic #2; batch
32 is designed from it (candidates: force base_common re-emit by
retiring the frozen map, or a dedicated stubs file if the shard
comparison points at file context instead).

Diagnostic #2 RESULTS (Nov 3, 23:49 NST) — ROOT CAUSE FOUND.
Section A killed the frozen-map theory: every probed address,
known-good included, appears in exactly 1 base_common shard file
(presence there is just mentions), and section D shows 80354818 is
not in base_common_shard_map.json at all. Section B is the smoking
gun, shard_7ca4da871d8c2c05b3cb3f02.cpp lines 28622/28628:
"// inline leaf 0x80354818 (6 guest instruction(s))" ...
"// end of inlined leaf 0x80354818". THE TRANSLATOR INLINED
AIStartDMA INTO ITS CALLER (__AXOutInit, same shard). There is no
call and no dispatch in the generated code, so no override
registration of any form can ever intercept it — that is why three
binding forms failed identically while the larger AIInitDMA (real
call, dispatch-checked) worked. Overrides only intercept actual
calls; inlined leaves bypass the mechanism entirely. Fix direction:
find the inlining control (translator source emits the "inline
leaf" comment; recomp.yml may carry thresholds/exclusions — the
batch-23/24 MAP-split precedent shows per-function translator
controls exist in this project) and stop 0x80354818 being inlined,
then the existing batch-30 override should take over with no
further binding work. Diagnostic #3: enumerate ALL inlined leaves
in the shards (blast radius — DSPCheckInit 0x8035C0F4 is 2
instructions and may also be inlined, which would void its
single-DSPInit-log "proof" and revive the __DSP_init_flag watch
item), dump recomp.yml, and locate the "inline leaf" code in
translator/src.

Diagnostic #3 RESULTS (Nov 3, 23:51 NST): the inliner is
translator/src/Translator.Core/Translation/LeafFunctionInliner.cs
(the "inline leaf" comment is its line 157). recomp.yml carries NO
inlining config (translation: only entry_points,
allow_unsupported_instructions, function_map) — the control lives
in translator code/config plumbing, not the project file. The
inlined-leaf census is dominated by CRT helpers (0x8032FB18 x2553,
the 0x803307xx memset/memcpy family, low 0x8000xxxx leaves);
AIStartDMA is inlined exactly x1, far below the top-25 cutoff, and
DSPCheckInit's inline status is still unknown (needs the filtered
8034/8035-range census). KEY LEAD in the inliner's own code:
LeafInlineRejection.BlockedAddress exists (LeafFunctionInliner.cs
line 221, inside TryCreateCandidate) — some address set already
blocks inlining; the open question is what feeds that set (native
override addresses from the marker scan? a config list?) and why
0x80354818 was not in it while (apparently) DSPCheckInit was
protected or rejected on other grounds. Next diagnostic: the
filtered census plus the TryCreateCandidate region (lines ~195-270)
and a translator-wide grep for BlockedAddress / LeafFunctionInliner
callers to find the blocked-set construction.

Diagnostic #4 RESULTS (Nov 3, 23:54 NST): (1) Filtered census:
AIStartDMA 0x80354818 inlined x1 AND AIStopDMA 0x80354830 inlined
x1 — batch 27's AIStopDMA binding is dead for the same reason (it
would fault in __AXOutQuit the same way; it was never a valid
discriminator). DSPCheckInit 0x8035C0F4 is NOT in the inlined list —
its native binding genuinely intercepts, the single-DSPInit-log
proof stands, __DSP_init_flag watch item unchanged. Other notable
inlined SDK leaves (future MMIO-fault candidates if they touch
hardware regs): __ARGetInterruptStatus 0x80355304 x7, 0x803552E4 x7,
0x80354920 x1; the AX command-insert leaves 0x80357524-0x80357660
are inlined but are pure guest-memory work. (2) The blocked set is
real and override-driven: Translator.Cli Program.cs:3885-3893,
BuildLeafInliningBlockedTargets = nativeGuestEffects.Contracts.Keys
∪ translationExclusions ∪ modPatchedAddresses, built lazily at
Program.cs:125-141 and fed through FunctionTranslator options into
LeafInliningPolicy.BlockedTargets; TryCreateCandidate rejects when
the entry point OR ANY instruction address in the body is blocked
(inliner comment: a replacement anywhere in the body counts).
(3) The catch: inlining happens inside FunctionTranslator — i.e.,
at TRANSLATION time — and emit-build-shards assembles shards from
the frozen base translation (base_translation_output.json +
functions/); Brandon's emit outputs never showed Program.cs:468's
"[translator] Leaf inlining: N address(es)..." line. So the splice
in func_803583D0.cpp (__AXOutInit) was baked when the base
translation was generated, before batches 27-30 added the AI
contracts, and no re-emit since could ever remove it. Fix route:
regenerate the base translation (or retranslate the affected
callers) with the current native sources so 0x80354818 lands in the
blocked set — AIStopDMA and every other now-overridden inlined leaf
get de-inlined by the same pass — then emit, rebuild, run.
Diagnostic #5 reads Program.cs wiring (115-150, 3883-3898),
nativeGuestEffects provenance, and which command writes the base
translation, to pin the exact regeneration command.

Diagnostic #5 RESULTS (Nov 3, 23:55 NST): wiring confirmed.
runtimeNativeGuestEffects is a shared Lazy (Program.cs:110);
baseTranslationExclusions (112-116) are the native registrations
flagged ExcludesBaseTranslation; WithProjectFrontEndPolicy
(133-142) injects LeafInliningBlockedTargets into TranslationOptions
with the comment "Leaf inlining is a front-end decision: the splice
happens before SSA... every discovery entry point has to agree on
it." The upstream comment at 117-120 records the SAME bug class hit
with mod patches (mod-patched callees leaf-inlined into base
callers) — this failure mode is known to the framework; CTTR just
hit its native-override variant because the base translation
predates the AI contracts. The translate flow prints the contracts
count (462-465) and writes base_translation_output.json +
mod-awareness atomically (1478-1532); emit-build-shards is a
separate subcommand (168) that only reads them. Regeneration
command is the campaign's own corrected Windows translate-recursive
(spike step 5 minus --no-function-files, per batch 14): it re-runs
in ~20 s and has been run before mid-campaign (batch 13/14 era,
25,273 functions). BATCH 32 ISSUED (Nov 3, 23:56 NST): backup
generated/cttr -> generated/cttr.bak-pre32, retranslate, calibrated
gate (grep ALL function files for "inline leaf 0x80354818" /
"0x80354830" — must be zero hits, else stop before building), then
emit + rebuild (cttr-build-copy47.log) + run. No source patch: the
batch-30 _R override is already in audio.cpp waiting.

Batch 32 RUN (Nov 3, 23:59 NST; console-35 + crash_sigabrt-11 +
mem1_1) — SOLVED. The 0xCC005036 AIStartDMA fatal is GONE: boot
completed __AXOutInit and the whole fn_8027CC48 audio-init chain,
and mem1_1 differs from mem1_0 in 9,501 bytes (vs 41 for the
identical-fault runs), with AX state advanced (0x0009450C at
0x804AED38). The batch-30 _R override fired once the leaf was
de-inlined, exactly as the mechanism predicted. NEW FAULT (next
campaign step, batch 33): FATAL MMIO read 0xCC005020 =
__DSPRegs[16] (AR_DMA_MMADDR_H — the AR DMA registers live in the
DSP register block, indices 16-21) in guest __ARQServiceQueueLo
(0x80356B08, size 0x100) at +0x60, called from ARQPostRequest
+0x138. Call path: the HLE DVD read (DVD__ReadAbsAsyncPrio_HLE)
called back into guest fn_8027D754 -> fn_802448CC -> fn_802446F8 ->
ARQPostRequest (MEM1 buf 0x808CA280, len 0x4000) — the game's file
loading now runs and stages reads through the ARAM queue. ARInit
was stubbed in batch 6 (allocator state only; no ARAM device), so
the ARQ family is unimplemented: batch 33 target is the ARQ service
routines (__ARQServiceQueueLo 0x80356B08, __ARQServiceQueueHi,
__ARQInterruptServiceRoutine 0x80356C0C, ARQInit 0x80356CD8) with
decomp src/dolphin/ar/arq.c as spec — design question is a
synchronous-completion HLE (perform the MEM1<->ARAM copy against a
host backing buffer and fire the request callback) vs stubbing the
service leaves; note AIStopDMA 0x80354830 and __ARGetInterruptStatus
0x80355304 are also de-inlined now, so their overrides are live for
when __AXOutQuit / AR interrupt paths run. Parked at the school-
night cutoff, Nov 4 00:00 NST; batch 33 is the next session's first
job.

Batch 33 investigation (Nov 4, 02:15-02:45 NST; Brandon up again
after sleep, session resumed at his word): the ARQ HLE ALREADY
EXISTS in the runtime and is complete -- audio.cpp:789
ARQTransfer_CTTR does the DMA synchronously through the FAKE_VMEM
window (memory.cpp:540, a real 32 MiB region at 0x7E000000) and
queues a deferred interrupt; audio.cpp:822
ARQ_HLE_ProcessDeferredInterrupts pumps completions into the guest
ISR (InvokeDirectCpu<0x80356C0C>) and IS wired (os_alarm.cpp:253).
Yet console-35 has zero "CTTR ARQ DMA" log lines and the guest body
ran. Call-site comparison killed the codegen theory: the batch-32
__ARQServiceQueueLo calls InvokeDirectCpu<0x803550B0u>(ctx),
IDENTICAL in form to the working AIInitDMA call site in
__AXOutInit -- dispatch resolved 0x803550B0 to the translated
function at runtime. The binding (audio.cpp:817-820) is the ONLY
multi-line PPC_NATIVE_OVERRIDE in the file; every working binding
is one line. GeneratedMarkers.cs builds each override's ABI thunk
from its signature scans (full-statement pattern line 107,
void-arguments pattern line 114); the working theory is those scans
never produced a thunk for the four-line macro, so the dispatch
silently fell back to the translated body. Baseline
(cttr-translate-32.log): contracts 374 total / 248 precise / 126
full-context; leaf-inlining blocked 375. BATCH 33 ISSUED:
tools/patch-arq-binding-oneline.py (mock-tested: apply, idempotent,
anchor-failure) joins the binding to a single line, macro and args
unchanged; the run retranslates and GATES on the contracts count
rising (total >374 or precise >248) before emit/rebuild (copy48)/
run. If the count does not move, the theory is wrong and the next
read is the generated dispatch glue for 803550B0 vs 80354790.

Batch 33 RUN (Nov 4, 02:54 NST; console-36) -- THEORY CONFIRMED,
fault dead, new hang downstream. The gate passed (contracts rose)
and the run logged "[audio] CTTR ARQ DMA: direction=0
main=0x808ca280 aram=0x4000 bytes=0x800" -- ARQTransfer_CTTR fired
with exactly the snapshot's request parameters. The single-line
reformat was the whole fix: multi-line override macros are
invisible to the translator's signature scans and silently fall
back to the translated body. No FATAL in console-36. BUT the boot
then hung: at the 12 s and 30 s watchdogs, 0 frames presented, all
threads parked as before, and NEITHER the pump's dispatch line
("Dispatching CTTR ARQ DMA completion interrupt(s)") NOR its
masked line ("pending while guest interrupts are disabled") ever
appeared -- so ARQ_HLE_ProcessDeferredInterrupts was never called
with a pending interrupt in 30 s. The transfer's completion sits
in g_aramDmaInterruptsPending and the loader waits on its callback
forever. Batch 34 target: the pump's only call site
(os_alarm.cpp:253) -- read its enclosing function and callers, find
which deferred-service points actually run during this boot phase,
and wire the pump into one that does (the change the framework's
own wiring apparently misses for this flow).

Batch 33 follow-up investigation (Nov 4, 03:00-03:11 NST) and
batch 34 ISSUED. The pump call at os_alarm.cpp:253 sits in
ProcessAlarmQueue's completion tail (network/DVD/ARQ/NAND share
it). The function head is innocent: no empty-queue early return,
the depth guard is a thread_local RAII scope, and EnsureSda1Base
repairs r13 before the r13 gate. Its live callers are
SelectThreadSwitch's idle loop (os_scheduler.cpp:113/322) plus
alarm-set HLE entries for other games' addresses. The idle loop
enables interrupts on entry and pumps every wait iteration -- so
if it were ever entered after the transfer, the ARQ interrupt
would have dispatched. It wasn't: CTTR's all-fibers-blocked loader
state is reached through the game's own fiber switch
(GameFiberSwitch_CTTR, os_context.cpp:242 -- always has a target
block, no host wait, no service calls), never through
SelectThread. Self-sealing deadlock: the only event that can wake
the loader is serviced only from a loop the blocked state never
enters. Side datum: CTTR's AlarmQueue is .sbss 0x804AE9F0 =
r13 + 0x3070, while the HLE addresses it as SDA1_BASE minus an
SPM-shaped offset -- the alarm HLE's queue geometry stays on the
suspect list for when guest alarms matter.
Batch 34 (patch-arq-pump-vi.py, mock-tested: clean apply,
idempotent, anchor-fail exits untouched): in
VI_HLE_ProcessRetracesDeferred (vi.cpp) -- the wall-clock deferred
boundary that already invokes guest retrace callbacks on a private
interrupt context (GuestInterruptCallbackContext) from GX work and
the host frame loop -- call ARQ_HLE_ProcessDeferredInterrupts(cpu)
inside the same Begin/End wrapper right after AdvanceDueRetraces,
plus a one-time entry log of the gate state (detClock /
interrupts). Declaration already reaches vi.cpp via
hle_stubs.h:46; log style RT_LOGF(RT_TAG_VI, ...). Native-source
only: no retranslate/emit; build copy49 + run. Readings: if the
"[arq-pump]" line shows detClock=1, the wall-clock path is off by
design and servicing moves to the deterministic path; if
"Dispatching CTTR ARQ DMA completion interrupt(s)" appears and
the boot proceeds, the hang is solved; if dispatch logs but the
hang persists, delivery works and resumption is the next target.

Batch 34 RUN (Nov 4, 03:15 NST; console-37): NEGATIVE, and the
gate log earned its keep. "[arq-pump] VI deferred boundary first
entry: detClock=0 interrupts=1" -- the boundary is entered during
boot, DetClock is off, interrupts were on. The transfer fired
again (line 116), but NO dispatch and NO masked-pending line:
after the stall begins, VI_HLE_ProcessRetracesDeferred is never
called again (its callers are GX work and host frame waits; the
stalled game does neither), so the batch-34 call site starves
exactly like the SelectThread idle loop did. Lesson: every
guest-activity-driven service point starves in an all-blocked
state; the next candidate must be a loop that demonstrably spins
DURING the stall -- the VI-wait idle loop inside vi.cpp (the
" goes idle and calls ProcessTimerEvents again" path near
vi.cpp:637, used by VIWaitForRetrace-style HLE waits) and the
pump's own verbatim body (audio.cpp:819+) are the batch-35
reads, because the pump's gates have so far been paraphrase,
not source.

Batch 35 ISSUED (Nov 4, 03:18 NST). The pump verbatim
(audio.cpp:819-871) has only four gates -- null cpu, pending==0,
interrupts-disabled (one-time log), and a thread_local re-entry
guard -- and invokes the ISR 0x80356C0C directly; no mask or
address reads. So it has simply never been entered with the
interrupt pending. Batch-34's starvation also clarified the
stall: VI retrace count freezes at 6, so nothing guest-side or
VI-side runs at all once blocked. The one path that provably
executes after the transfer completes is the blocking path
itself: the loader's first blocking fiber switch happens with
the interrupt already pending, and every GameFiberSwitch_CTTR
resume re-enables interrupts at its tail before returning to
guest code -- hardware-interrupt timing. patch-arq-pump-fiber.py
(mock-tested: clean apply, idempotent, anchor-fail untouched)
adds extern "C" declarations for the Begin/End deferred-callback
pair above GameFiberSwitch_CTTR (os_context.cpp already includes
hle_stubs.h, which declares the pump at :46) and calls
ARQ_HLE_ProcessDeferredInterrupts(ctx) at the switch tail after
OS__EnableInterrupts_801a65c0(), inside the same Begin/End +
try/catch discipline as the ProcessAlarmQueue tail. Expected
sequence: pump fiber resumes -> tail dispatches the ISR -> ISR
completes the request, callback signals the loader's semaphore
in guest bookkeeping -> pump fiber's scheduler cycle picks the
loader up. Native-only; build copy50 + run. Batch 34's VI call
site stays (harmless, and its gate log is proven useful).

Batch 35 RUN (Nov 4, 03:20 NST; console-38): NEGATIVE --
identical hang, identical watchdog state, no dispatch, no
masked line. Three service points have now failed to produce a
single pump entry with the interrupt pending, which inverts the
suspicion: the interrupt may never be queued at all. If
ARQTransfer_CTTR logs at entry and then hits an early return (or
a swallowed throw) before its fetch_add at audio.cpp:815, every
observation across consoles 36/37/38 is explained by one cause
-- transfer logged, pending stays 0, loader waits forever, and
no service point anywhere can dispatch what was never queued.
Two verifications before batch 36: (1) batch 35 actually
applied and built (patch output + copy50 log showing the
os_context TU recompiled -- the run block does not stop on a
patch failure, and console-38 carries no batch-35 marker); (2)
ARQTransfer_CTTR's body verbatim (audio.cpp ~780-817): order of
log / copy / fetch_add and every early return in between.

Verifications RETURNED (Nov 4, 03:21 NST) -- both surprises.
(1) Batch 35 NEVER APPLIED: os_context.cpp contains no
"Batch 35" text, cttr-build-copy50.log has no os_context TU
line, and the exe timestamp is 03:15:19 (batch 34's build).
Console-38 re-tested the batch-34 binary; batch 35's idea is
still untested. Whether the block wasn't run or the patch
failed silently in it is unknown -- the run block continued
regardless, which is the process defect. Standing fix from
here: every run block carries a post-patch verification gate
(Select-String -Quiet on the marker; build only if present),
generalising batch 33's contracts gate. (2) ARQTransfer_CTTR
is CLEAN (audio.cpp:789-816 verbatim): aligns args, the only
early return is byteCount==0 (not our 0x800), GetPointers are
unchecked but a null would host-crash the memmove (no crash),
log precedes the copy, and the fetch_add(1) at line 815 is
unconditional. The interrupt IS queued; the "never queued"
hypothesis is dead. Batch 35 is therefore RE-DELIVERED as-is
with the gated run block (build copy50) and a request for the
patch output lines. If it lands and still doesn't dispatch,
the remaining unknown is whether post-transfer entries to the
batch-34 VI boundary are interrupts-gated -- the fiber-switch
tail calls the pump after the switch's own Enable, so it is
immune to that too.

Console-39 (Nov 4, 03:24 NST): STILL no dispatch, identical
hang -- but Brandon uploaded only the console log, so whether
the gate passed this time is unknown from the log alone (the
exe ran, which suggests the gate passed OR the exe was run
manually after a gate stop). Asked for the block's terminal
output (patch lines + gate verdict). Batch 36 is designed
either way as a self-reporting consolidation in os_context.cpp:
ensure the batch-35 edits (idempotent), capture the pump's
return value at the tail, and add one-time logs at
GameFiberSwitch entry (first switch ever) and at the tail
(first tail execution) -- one run then settles which code ran,
whether switches and tails execute post-transfer, and what the
pump saw, ending the inference chain.

Batch 36 WRITTEN and mock-tested (Nov 4, 03:25 NST;
patch-arq-pump-fiber36.py). State-aware: pristine file gets
decls + instrumented tail; a file already carrying batch 35
gets its tail block regex-upgraded (end anchor requires the
closing brace, after a first cut matched the catch-block End
line and left a remnant -- caught in mock, fixed, re-verified:
both states converge to functionally identical output, braces
balanced, exactly one pump call); already-patched reports and
exits 0; garbled-anchor exits 1 untouched. Instrumentation:
entry build-stamp log ("servicing build live (batch 36)"),
tail logs for the first three tail calls plus any call with
handled=1, pump return captured. Delivered with the gated run
block (marker "batch 36"; build copy51). Brandon's batch-35
terminal output is now optional context, not a blocker.

Batch-35 gate output RECEIVED (Nov 4, 03:26 NST): the patch
applied cleanly (edit 1/edit 2/written), the gate verified,
the build recompiled unity_guest_system and relinked -- so
console-39 WAS batch 35, and it is a true negative. Combined
with the proven fetch_add, this closes the logic: every switch
delivers exactly one tail execution on the resume side, the
tail calls the pump after the switch's own Enable, and the
pump logs "Dispatching" before invoking the ISR -- so no
dispatch means NO GameFiberSwitch call at all after the
transfer. The whole game fiber system freezes at the post; the
posting thread blocks without switching (and the DVD callback
was therefore serviced inline by the DVD HLE, not from
ProcessAlarmQueue's tail, which would have pumped 10 lines
later). Next target after batch 36's confirmation: the Aurora
frame-worker wait callback -- hle_stubs.h:47-52 calls it (with
the VI retrace pacing loop) a "long host wait that already
services retraces and alarms", and Audio_HLE_PollDeferred
exists to be called from exactly there; its call sites are the
batch-37 evidence.

Frame-worker evidence LANDED (Nov 4, 03:29-03:30 NST):
Audio_HLE_PollDeferred is defined at audio.cpp:697 and called from
exactly two places: main.cpp:121, inside
ServiceGuestTimingDuringAuroraFrameWait (registered as the Aurora
frame-worker wait callback at main.cpp:1711), and vi.cpp:957 (the VI
retrace pacing loop). The callback services three DEFERRED TWINS at
wall-clock cadence while the host waits: VI_HLE_ProcessRetraces-
Deferred(8), OS_HLE_ProcessAlarmsDeferred(8) (def os_alarm.cpp:403;
whether its body reaches ProcessAlarmQueue's tail was left unread --
the batch-37 twin makes it moot for this path), Audio_HLE_Poll-
Deferred(). Audio_HLE_PollDeferred's body (verbatim) is the template:
DetClock gate, OS_HLE_InterruptsEnabled gate, GuestInterruptCallback-
Context, OS_HLE_Begin/EndDeferredGuestCallbacks + try/catch. The ARQ
pump was the only completion service with NO such twin.

BATCH 37 ISSUED (Nov 4, ~03:31 NST): patch-arq-pump-framewait.py
(mock-tested: fresh apply, idempotent re-apply, twin braces balanced
9/9). Four edits: (1) hle_stubs.h declares
ARQ_HLE_ProcessDeferredInterruptsDeferred() beside the pump; (2)
audio.cpp defines the twin right after the pump, mirroring
Audio_HLE_PollDeferred exactly -- DetClock gate, pending==0 silent
return (the twin lives in audio.cpp so it can read the counter),
then a ONE-TIME log "[arq-pump] frame-wait ARQ servicing reached
with pending=N interrupts=I" BEFORE the interrupts gate, then the
isolated context + wrapper + pump call; (3) main.cpp calls the twin
in ServiceGuestTimingDuringAuroraFrameWait after Audio_HLE_Poll-
Deferred(); (4) vi.cpp calls it after its Audio_HLE_PollDeferred()
site. Gated run block (both main.cpp and audio.cpp must contain the
twin name before building), build cttr-build-copy52.log. Reading
console-41: twin reached line + pump Dispatching line + boot
proceeds = SOLVED at the designated host wait. Twin reached line
absent entirely = the Aurora wait callback does not run during the
stall either; last host-side runners are the frontend main loop /
stall watchdog (batch 38 territory, or a dedicated completion
poller). Reached with interrupts=0 = interrupts are the gate.
Run order vs batch 36 is free (disjoint files: 36 os_context.cpp;
37 hle_stubs.h/audio.cpp/main.cpp/vi.cpp).

CONSOLE-40 RAN (Nov 4, 03:37 NST) with batches 36+37 in ONE build
(copy52; the 14-object rebuild covered os_context, audio, main, vi):
- BATCH 36 CONFIRMED DECISIVELY: the entry stamp printed, and
  exactly ONE fiber-switch tail call logged ("call 1 handled=0"),
  BEFORE the "[audio] CTTR ARQ DMA" line (log lines 113/116/118).
  Calls 2-3 never appeared: ZERO GameFiberSwitch calls after the
  transfer. The fiber system freezes at the post, exactly as the
  closing logic predicted.
- BATCH 37 NEGATIVE: no "[arq-pump] frame-wait ARQ servicing
  reached" line anywhere in the full log, and no Dispatching line.
  The twin was never reached with a completion pending, so the
  Aurora frame-worker wait callback does NOT fire during the stall
  (its waits are submission-driven: no frame in flight, no wait,
  no callback). The VI pacing-loop call site is the same story.
- Score: FOUR service-point families proven dead in the all-blocked
  state -- ProcessAlarmQueue tail (scheduler idle), VI deferred
  boundary, fiber-switch tail, Aurora frame-wait callback. All are
  driven by guest or graphics activity; this state has neither.
- The one host mechanism PROVEN alive during the stall is the
  [vi] watchdog itself (it printed its 12 s dump). Batch 38
  candidate: call the batch-37 twin from the watchdog's periodic
  path -- IF its loop ticks well inside the 12 s report threshold,
  the per-tick cost is one atomic load (pending==0 early-out) and
  even ~1 s cadence unblocks the boot, since the loader waits
  indefinitely. Plan B: a dedicated completion-poller thread.
  Evidence needed: the watchdog's file/function and loop cadence.

WATCHDOG VERDICT (Nov 4, 03:39 NST): StartStallWatchdogOnce
(vi.cpp:531) spawns a detached thread that sleep_until()s 12 s,
dumps guest threads, sleep_until()s 30 s, dumps again, and EXITS
(optional SPM_WATCHDOG_AT extra dump). It is a one-shot diagnostic,
not a periodic loop -- no cadence to piggyback on, and it is
skipped entirely when RuntimeFrontend::Active(). Dead end as a
service point (it would deliver the completion at t=12 s at best,
and never in a frontend build). Batch 38 design therefore: a
DEDICATED COMPLETION POLLER owned by audio.cpp -- spawned once via
call_once at the first ARQ transfer, blocks on a condition variable
notified by ARQTransfer_CTTR after its fetch_add (50 ms timeout
backstop), and calls the batch-37 deferred twin, which already
carries the DetClock gate, pending check, interrupts gate and
isolated context. This mirrors the hardware truth the activity-
driven service points violate: ARQ completion is asynchronous and
independent of guest scheduling and graphics activity. Anchors
needed before writing: ARQTransfer_CTTR verbatim incl. the pending
counter's declaration, and audio.cpp's include list.

BATCH 38 ISSUED (Nov 4, ~03:47 NST): patch-arq-poller.py
(mock-tested: fresh apply, idempotent re-apply, braces balanced,
notify lands immediately after the fetch_add). Anchors verified
verbatim first: includes (<mutex> at :21; <atomic>/<chrono>
present, <thread>/<condition_variable> absent), the counter
declaration (audio.cpp:58), and ARQTransfer_CTTR's tail (fetch_add
at :815, memory_order_release). Three edits, all in audio.cpp:
(1) add <condition_variable> + <thread>; (2) after the counter:
g_arqPollerMutex/g_arqPollerCv, ArqCompletionPollerMain (one-time
"[arq-pump] ARQ completion poller thread started (batch 38)" log;
loop: wait_for 50 ms backstop, unlock, call the batch-37 twin,
relock), NotifyArqCompletionPoller (call_once detached spawn +
empty-lock + notify_all); (3) ARQTransfer_CTTR calls
NotifyArqCompletionPoller() right after the fetch_add. DetClock
mode is untouched (the twin gates on DetClock::Enabled()).
Reading console-41: poller-started line at the transfer, then the
twin's reached line, then the pump's Dispatching line, then boot
proceeds past the loader post = the ARQ saga closed. If the ISR
dispatches but the boot still hangs, the problem moves downstream
(the ISR's own bookkeeping / the loader's wake path) and the
watchdog dump from THAT run is the evidence. Gated block, build
cttr-build-copy53.log.

CONSOLE-41 RAN (Nov 4, 03:54 NST) -- **THE ARQ HANG IS SOLVED.**
The full sequence fired in order (log lines 112-115): transfer,
"[arq-pump] ARQ completion poller thread started (batch 38)",
"frame-wait ARQ servicing reached with pending=1 interrupts=1",
"Dispatching CTTR ARQ DMA completion interrupt(s): 1". The guest
ISR ran, the loader woke, and boot proceeded past the post that
froze consoles 36-40. The batch-33..38 chain is complete: single-
line binding (33) + deferred twin (37) + dedicated poller (38);
34/35/36 were the instrumented negatives that cornered it.
Batches 34-37's extra service points are now redundant but
harmless (all gated on the same pending counter).

NEW FATAL, far downstream (same run): FATAL MMIO read 0xCC003001
(PI register byte) inside guest OSGetResetButtonState
(0x803492B8, size 0x298; LR = base+0x24), called from game code
fn_801944D8 <- fn_80194110 <- fn_80070264 <- fn_80238628 <-
fn_80174724 <- fn_8018BB98 (main init chain). Decomp
(OSResetSW.c:50): the function reads __PIRegs[0]; bit 0x00010000
is active-low for the reset button (clear = pressed). With the
button untouched it returns FALSE through its debounce statics;
the only hardware touch is that one register read (plus
__PIRegs[0]=2 writes in the handler/callback setter, unreached).
Honest HLE: return FALSE (0) -- "reset button not pressed".
OSGetResetSwitchState forwards to it (same body via dispatch).
OSGetResetCode (OSReset.c:232) reads only the low-memory reset
code variable -- guest RAM, no HLE needed. Batch 39: bind
0x803492B8 with a SINGLE-LINE override to an HLE impl returning 0,
placed beside the existing OS getters; retranslate + emit with
the contracts gate (bindings/thunks are built at translation
time); build copy54. Evidence needed: the OSGetFontEncode
binding's file + macro idiom, and any existing OSGetReset
mentions in runtime/src.

CORRECTION to the above (same reading session): OSGetResetCode
DOES touch hardware on the cold-boot path -- when
__OSRebootParams.valid is false it returns
(__PIRegs[9] & 0xFFFFFFF8) / 8 (PI register 9, 0xCC003024). It
survived boot only because that path was not taken (or the seeded
reboot params read as valid). Batch 39 therefore binds BOTH
getters: OSGetResetButtonState 0x803492B8 -> FALSE, and
OSGetResetCode 0x80349118 (size 0x38, inline-risk leaf -- the
batch's retranslation de-inlines override-driven) -> 0 (honest
cold-boot code). Watch item: OSSetResetCallback /
__OSResetSWInterruptHandler write __PIRegs[0]=2; a PI WRITE
fault at 0xCC003000 later means the game registered a reset
callback and that setter joins the batch.

BATCH 39 ISSUED (Nov 4, ~04:03 NST): patch-reset-getters.py
(mock-tested: fresh apply, idempotent re-apply, braces balanced,
both bindings verified single-line). Evidence: the authors
already HLE'd OSGetResetCode for NSMBW in os_init.cpp:183-197
(impl OSGetResetCode_801a8a50, one-time log, return 0) bound at
0x80273B08, and os_font.cpp binds one OSGetFontEncode impl at
two addresses -- the exact pattern to copy. Edits (os_init.cpp
only, anchored on the NSMBW binding line): (1) bind CTTR's
OSGetResetCode 0x80349118 to the existing impl; (2) new
OSGetResetButtonState_CTTR impl in the file's style (one-time
RT_LOG, return 0) bound at 0x803492B8. Side facts: CTTR's build
has NO separate OSGetResetSwitchState symbol (folded/absent;
the fault came through OSGetResetButtonState itself);
OSSetResetCallback is 0x80349244 (watch item: writes
__PIRegs[0]=2 if called). Run block: patch gate -> backup
generated\cttr to cttr.bak-pre39 -> translate (cttr-translate-
39.log) -> contracts gate (total must exceed the 374 baseline)
-> emit -> build cttr-build-copy54.log -> run. Reading
console-42: the two new [os] getter lines at the startup chain,
no PI fatal, boot proceeds past fn_80194110's reset check.

CONSOLE-42 RAN (Nov 4, 04:15 NST): BATCH 39 SOLVED the reset
getters -- both bindings fired in boot order: "[os]
OSGetResetCode_801a8a50 called: returning 0 (Cold Boot)" (early
OS init) and, right after the ARQ dispatch, "[os]
OSGetResetButtonState_CTTR called: returning 0 (not pressed)".
Boot advanced one call site further in the master init
(fn_8018BB98 +0x744 -> +0x74C) into a graphics/texture subtree.

NEW FATAL (missing_target): InvokeIndirectCpu target 0x0, caller
LR 0x803688E0 = GXLoadTlut+0x2C, via game fn_801E7494. Decomp
(GXTexture.c:706): GXLoadTlut calls __GXData->tlutRegionCallback
(tlut_name) -- an indirect call through the GX state struct.
GXInit (GXInit.c) installs it via GXSetTlutRegionCallback(
__GXDefaultTlutRegionCallback) in its own body.

MEM1 FORENSICS (mem1_2_g919.bin, from the crash): __GXData
(.sdata2 0x804B2360) = 0x80499A40; the struct's first 0x400
bytes contain NO .text-shaped value at all, and the default
callback addresses (0x80363CDC tlut, 0x80363BE0 tex) appear
NOWHERE in all of MEM1 -- GXInit's callback installs never
executed. The struct is only sparsely written (a few fields:
+0x008=0xF, +0x014=0x2200, +0x01C=0x16009), so some GX activity
happened, but guest GXInit (0x80364034) either never ran or was
diverted. Prime suspect: an HLE GXInit binding at CTTR's address
that seeds host state only (the VIInit "seeding VI state (HLE)"
pattern), leaving the guest struct empty; alternative: the
game's GXInit call site was skipped upstream (e.g. a render-mode
guard after the HLE VIInit). Evidence needed: GXInit/GXLoadTlut
mentions in runtime/src. Batch 40 follows from which it is:
seed the guest callbacks from the HLE, unbind GXInit so the
translated body runs, or bind GXLoadTlut's family.

GXInit evidence LANDED (Nov 4, 04:18 NST): gx_init.cpp:392 --
"GXInit (CTTR): same shape as the NSMBW HLE above, with CTTR
addresses. gxData is zeroed; later GX API calls are thunked to
aurora and keep their own state." CTTR's GXInit IS HLE-bound and
by design does NOT maintain the guest __GXData struct; bound GX
functions keep host state instead. GXLoadTlut is evidently NOT
among the bound functions, so its translated body consults the
guest struct the HLE left empty -- a mixed-model seam, not a
game-order bug. Batch 40 direction: bind the TLUT family for
CTTR as host thunks in gx_texture.cpp, following its existing
GXLoadTexObj pattern (seeding guest callbacks instead would
cascade into the guest region arrays, which the same model
leaves unmaintained). Evidence needed: every "Tlut" mention in
runtime/src + the CTTR GXInit HLE body (gx_init.cpp ~385-410).

TLUT evidence LANDED (Nov 4, 04:18 NST): the host thunks ALREADY
EXIST -- GX__LoadTlut_80170fa8 (gx_texture.cpp:797) and
GX__InitTlutObj_80170f80 (:786) -- bound ONLY at NSMBW addresses
(0x8028eff4 / 0x8028efcc). CTTR's addresses were never added.
The CTTR GXInit HLE (gx_init.cpp:393-414, bound at 0x80364034)
confirmed: host GXInit + zeroed guest gxData (0x80499A40,
0x5B0 bytes) + __GXData pointer written to 0x804B2360 + the
__PIRegs/__CPRegs-style base globals seeded at 0x804AED90+.
CTTR GXTexture family (symbols): GXInitTexObj 0x8036825C,
GXInitTexObjCI 0x803684A8, GXInitTexObjLOD 0x803684F0,
GXInitTexObjWrapMode 0x80368654, GXInitTexObjTlut 0x80368670,
GXLoadTexObjPreLoaded 0x80368698 (uses texRegionCallback --
same crash class), GXLoadTexObj 0x80368814, GXInitTlutObj
0x80368868, GXLoadTlut 0x803688B4, GXInitTexCacheRegion
0x8036894C, GXInitTlutRegion 0x80368A40, GXInvalidateTexAll
0x80368A78, GXSetTexRegionCallback 0x80368AC0,
GXSetTlutRegionCallback 0x80368AD4. Batch 40: add CTTR binding
lines beside the NSMBW ones for every thunk the inventory
shows (two-address pattern), retranslate under the contracts
gate. One open detail: the LoadTlut thunk's tail writes into
guest gxData via kGXDataPtrAddr -- check its definition is
game-relative, not an NSMBW literal.

TEXTURE INVENTORY LANDED (Nov 4, 04:20 NST): gx_texture.cpp
binds thunks for NSMBW only (8028xxxx): GXInitTexObj 8028ea24,
GXInitTexObjCI 8028ec30, GXInitTexObjLOD 8028ec78,
GXInitTexObjWrapMode 8028ed8c, GXInitTexObjTlut 8028eda0,
GXLoadTexObj 8028ef78, GXLoadTexObjPreLoaded 8028ee14,
GXInitTlutObj 8028efcc, GXLoadTlut 8028eff4, GXInvalidateTexAll
8028F198. kGXDataPtrAddr = 0x804B2360 (gx_internal.h:57,
commented NSMBW) -- and CTTR's __GXData pointer lives at the
SAME address (proven from the crash dump), so the thunks'
guest-flag writes (gd+2, gd+0x5FC) land correctly for CTTR
unchanged. Batch 40: add the CTTR binding line beside each
NSMBW one for those ten impls (CTTR: 8036825c, 803684a8,
803684f0, 80368654, 80368670, 80368814, 80368698, 80368868,
803688b4, 80368a78), after a duplicate check that none of
those addresses is already bound elsewhere (the runtime
resolves duplicates "by priority" -- cf. the boot line -- so
a second binding could silently shadow). Retranslate with
the contracts gate at >376 (374 baseline + batch 39's two;
the behavioral proof is console-43 itself).

BATCH 40 ISSUED (Nov 4, ~04:24 NST): patch-gx-texture-cttr-
bindings.py (mock-tested: fresh apply, idempotent re-apply,
each CTTR line verified directly after its NSMBW twin for the
same impl). Ten single-line bindings added in gx_texture.cpp.
Duplicate check returned EMPTY -- none of the ten addresses was
bound anywhere. Run block: patch gate -> backup cttr.bak-pre40
-> translate (cttr-translate-40.log) -> contracts gate >376 ->
emit -> build cttr-build-copy55.log -> run. Reading console-43:
boot proceeds past fn_801E7494's GXLoadTlut (texture loads
visible in [drawdump] lines if enabled, or simply no
missing_target at GXLoadTlut+0x2C), deeper into the master init
-- likely the first presented frames if the texture subtree
completes. Watch: GXInitTexCacheRegion / GXInitTlutRegion have
no thunks anywhere (guest region structs stay guest-side);
if a later fault lands in region handling, that family is next.

CONSOLE-43 RAN (Nov 4, 04:25 NST): BATCH 40 SOLVED the texture
seam -- boot passed GXLoadTlut, the game entered a live graphics
loop (85,439 "[aurora::gx::fifo] Ignoring nested GX_CMD_CALL_DL"
lines: display lists flowing, Aurora declining DL-within-DL
nesting -- a rendering-fidelity gap to revisit, not a blocker),
and the fiber system resumed switching (tail calls 2 and 3
logged with handled=0; in the hang consoles they never came).
No watchdog dump: the crash arrived inside 30 s.

NEW FATAL (missing_target #10): bctrl to 0x0 at
fn_800A86A0+0x184 (game code, size 0x1CC), on a loader thread's
fiber (r4=0x80B957D8), resumed via the LoadContext pad
(pc=0x8024C8E4), called through the game's 0x8023Axxx sync/
message middleware (fn_8023A0AC <- fn_8023ACEC <- fn_8023BF3C
<- fn_8023BA20 <- fn_800A7B90 <- the thread wrapper fn_8024F5A0).
The object in r5/r6 (0x80944248) is ALL ZERO for at least 0x80
bytes in the crash dump -- fn_800A86A0 calls a function pointer
out of a structure that was never initialized. Next evidence:
the generated C++ for fn_800A86A0 (what field it calls, where
the object comes from) + the zero-run extent around 0x80944248.

CONSOLE-43 CRASH IDENTIFIED (Nov 4): fn_800A86A0 is a virtual
of class GODFileHandler (RTTI string at its vtable
0x803ABFE4+16; vt[2]=fn_800A8580, vt[3]=fn_800A86A0). It is the
handler's drain/update: walk the in-flight list (mgr+0x10;
nodes: state @+8, filename @+0x10, type @+0x60, resource
@+0x80), finalize state-2/3 nodes through the resource's
vtable, then scan a 190-entry registry (base @ mgr+0x1028),
clearing each entry and calling entry->vtable[3]
(release/dispose) -- the crash is that call with vtable[3]==0
(LR 0x800A8824, counters r24=3/r30=0xC consistent with slot 3).
Dump state: singleton mgr 0x80942488 (@0x804AD928); ONE list
node (0x80951420) loading "design\startup.gdo" (type "Script"),
state 2, resource 0x807120C0 (a core::IRefCount-derived obj,
vtable 0x803E3FDC, [res+20]=2, [res+24]=0 -- the finalize
branch was SKIPPED for it: leaf 0x802512D4 yields byte 0 from
[res+20]=2, the not-ready path); the 190-table reads EMPTY in
the dump because entries are cleared BEFORE the dispose call.
The r5 buffer 0x80944248 (260 zero bytes, DEADBABE neighbour)
is a load destination buffer referenced x3 by a request
descriptor at 0x80943504 -- not the crash object. The runtime's
crash register dump is the outer fiber ctx (r31=0 cannot be
the pump's), so the bad entry's address is not recoverable
from this dump. Next evidence: func_8023A700.cpp -- the caller
at +0xC4 -- to see whether the pump is invoked directly on the
singleton or indirectly over a registry (a bogus registered
pump would produce exactly this garbage-table crash).

DISPATCH ANATOMY (Nov 4): fn_8023A700 is NOT the drain's
caller -- it is the broker's bucket-insert (hash insert into
obj+0x654 buckets by key*4, lock via vtable[13], notify via
vtable[14], signal sem at obj+0x64C via fn_8024C95C). The
crash backchain runs fn_800A7B90 -> fn_8023BA20 ->
fn_8023BF3C -> fn_8023ACEC -> fn_8023A0AC (a 0x14-byte thunk)
-> fn_800A86A0. MEM1 scans REFUTE the "static vtable with a
null slot 3" theory: NO data-range vtable in the whole image
has code at [0],[1],[2] and 0 at [3] (the two loose-filter
hits were a name-tagged descriptor struct at 0x80944350 --
first field points at a "...:Stats"/"content::SimpleC..."
string, callback at +8 -- and a thread struct at 0x80BA8C20).
The dump's r31=0 / r27=1 fit a different shape: the drain
invoked with this==NULL (or a garbage table base), reading
slot value 1 and calling through two zero reads. Working
theory: the broker dispatcher can reach the drain with a
null/stale handler during a registration transition -- the
class of interleave the host-thread ARQ poller (batch 38) and
HLE fiber yields make observable. Next evidence: the thunk
func_8023A0AC.cpp (0x14 bytes) and the dispatcher
func_8023ACEC.cpp -- how the pair (handler, method) is loaded
decides where a guard can live.

DISPATCH ANATOMY CLOSED (Nov 4, later): fn_8023ACEC is a
handler CONSTRUCTOR (360-byte named objects, vtable
0x803E1E80, name at +30, broker at +12, key at +16; allocates
a 20-byte node via fn_80248178/fn_80248C34 and registers it
through fn_8023A0AC -> broker+184 bucket object ->
fn_8023A700 insert). fn_8023A0AC is just the register shim
(r3 = Read32(broker+184)). NEITHER dispatches the drain.
Bucket object 0x80B954A8 (vtable 0x803E1DE4): vt[13]=
fn_8023A6B8, vt[14]=fn_8023A6DC (the lock/unlock pair),
+4136 = 0, insert count 1. Handler class vtable is full
(vt[3]=fn_8023B094). GODFileHandler (vtable 0x803ABFE4) has
ONLY vt[2]=fn_800A8580 and vt[3]=fn_800A86A0 before its name
string -- so the drain is reached only as GODFileHandler::
vt[3] on some instance, with NO frame on the faulting fiber's
stack (the backchain is an unrelated construction chain):
the invocation arrived on a different guest context (a host-
serviced callback context), which is why the crash dump's
registers/stack describe the wrong fiber. The dispose target
reading 0 fits a heap descriptor at 0x80944350 (first word =
static type descriptor 0x803E3E48 in the "content::Simple..."
string area, +8 = fn_8024FBEC, +12 = 0; ref'd by .bss global
0x804AE434) but its size argues against it being a table
entry (the drain reads entry+0x8C). UNRESOLVED from dumps:
the exact entry and the invoking context. Fix-shape question
is now an API question: can a native override log/sanitize
and then call the base translated body (the statefree
machinery in fn_8023ACEC's generated code hints the runtime
keeps base bodies callable for some functions)? Evidence:
grep runtime/src for BaseTranslated/statefree usage in
overrides + the ARQ pump's guest-ISR invocation lines.
Fallback if no delegation exists: no-op stub experiment for
fn_800A86A0 (vt[3] may be a flush/dispose pass the boot can
survive without; vt[2] fn_800A8580 may be the real update).

BATCH 41 ISSUED (Nov 4): guard the translated body instead of
overriding a vtable-called function. The abi_bridge evidence
showed BaseTranslated vs override priorities but no supported
"override calls the base body" pattern in runtime/src, and a
native override at an indirect-dispatch (vtable) target
carries the stale-winner boot-fatal risk proven on the SPM
side. patch-god-drain-nullguard.py (mock-tested: fresh apply,
idempotent re-apply, decoys untouched, wrong-count fails
clean) rewrites all 7 InvokeIndirectCpu(ctr, ctx) sites in
generated/cttr/functions/func_800A86A0.cpp to
if (ctr != 0) { InvokeIndirectCpu(ctr, ctx); } -- a null
dispose/finalize target is never a legitimate call; the
reload-after-call flow tolerates the skip. POST-TRANSLATE
STEP from now on: retranslation regenerates the file, so the
guard runs after translate-recursive and before emit on every
future retranslation (regen-pass pattern). Run block:
translate (cttr-translate-41.log) -> guard + count gate (==7)
-> emit -> build cttr-build-copy56.log -> run. Reading
console-44: no missing_target at 0x800A8824; boot proceeds
past the GOD drain -- watch whether startup.gdo's load
completes (title/menu progress) or stalls (would mean the
drain's finalize half is load-bearing in a way the guard
disturbed -- it should not be: all non-null calls run as
before).

CONSOLE-44 RAN (Nov 4): batch 41's null-guard WORKED for the
null case and the game ran longer (88,467 lines, 87,611 DL
lines). NEW FATAL at the SAME site (fn_800A86A0+0x184):
target 0x6865656C = "heel" -- the scan read an entry whose
vtable pointer landed in .rodata string data ("flying
wheel" motif string at 0x8039CA6F; V = 0x8039CA64, fn =
[V+12] = the "heel" bytes). A stale registry entry whose
heap block was reused as string data. The singleton's table
is all-zero in the dump again. Pattern across both crashes:
the drain, running on a host-serviced callback context,
meets registry entries in states the game's own main-loop
timing never presents (null dispose, then stale/reused) --
a context/interleave divergence, not a code-path bug.

BATCH 42 ISSUED (Nov 4): patch-god-drain-rangeguard.py widens
the guard from ctr!=0 to a code-image range check at the
same 7 sites: if (ctr >= 0x80000000u && ctr < 0x80390000u).
Both observed bad targets fall outside; every legitimate
target is inside. Skipping = a skipped dispose (small leak);
the drain already cleared the slot, so bad entries do not
return. Mock-tested on clean, batch-41-guarded (upgraded in
place), and re-apply paths. Same post-translate flow;
build cttr-build-copy57.log. Reading console-45: no
missing_target at 0x800A8824 and continued boot (title/
menus), or the next distinct fault.

CONSOLE-45 RAN (Nov 4): NO CRASH -- batch 42's range guard
held. But the boot now SPINS instead: 94,916 lines, watchdog
at 12 s reports 0 guest frames presented, retraces stop at 6,
and 4,378 blocked MMIO writes to 0xCC005000 (DSP register
page, OSSleepThread-attributed) pour out. Anatomy of the
spin: the DL spam stops at line 89,947 amid Aurora FIFO
DESYNC errors ("truncated draw cmd=0xBD fmt=5 vtxCount=24910,
need 124550 bytes, have 6886" -- the FIFO reader lost
alignment; nested-CALL_DL fidelity gap territory), fiber
switches resume (tail calls 2-3), and then the drain
(fn_800A86A0) starts reading WILD addresses (34 unmapped
touches, 33 with active=fn_800A86A0: entries like 0x01800000
-- data words, not pointers). The watchdog's current-thread
dump shows the main thread inside the drain's own semaphore
call (fn_8023BE8C -> OSSignalSemaphore; stack +1C =
0x80942488, the singleton). Unified theory: the drain is
scanning a garbage-fed registry -- plausibly an async
DVD/ARQ completion delivering file data over live structures
(console-44's "heel" target was a pointer into loaded file
data: motif strings live in .gdo content), or a phantom
invocation context; either way the singleton's own table was
empty/pristine in every dump, so the REAL handler has no
drain work at boot. The range guard converted crashes into
an endless garbage churn that starves presentation.

BATCH 43 DIRECTION: stub fn_800A86A0 natively (one-time log +
return) in os_init.cpp beside the batch-39 bindings.
Accepted risk: a native override at a vtable-called
(indirect-dispatch) address may hit the stale-winner boot
fatal -- if so it fails immediately and legibly, and the
fallback is a generated-code edit that makes the drain
validate its table base against the singleton's. If the stub
boots, watch for first presented frames / title progress;
the FIFO desync is the next target either way.

BATCH 43 ISSUED (Nov 4): patch-god-drain-stub.py binds
0x800A86A0 to GODFileHandler_Drain_CTTR (one-time log, return
0) in runtime/src/hle/os/os_init.cpp, anchored verbatim on
the batch-39 line 218 binding, exact PPC_NATIVE_OVERRIDE
shape. Backup written to os_init.cpp.bak-pre43 before edit.
Mock-tested: fresh apply, idempotent, anchor-miss fails
clean with no backup. The batch 41/42 generated-code guards
are RETIRED by this batch (no rangeguard step in the run
block; retranslation regenerates the drain body, dispatch
goes to the override). Run: patch -> gate -> translate
(cttr-translate-43.log) -> emit -> build
cttr-build-copy58.log -> run. Readings: (a) boot fatal
naming 0x800A86A0 / stale indirect winner -> route closed,
restore backup, fallback = generated-code table-base
validation; (b) stub log line + first presented frames /
title progress -> the phantom drain was the presentation
blocker; (c) stub log + same 0-present spin -> the blocker
is elsewhere (FIFO desync / async-DVD stomp widens).
Real runtime paths confirmed Nov 4: os_init.cpp is
runtime/src/hle/os/os_init.cpp; audio.cpp is
runtime/src/hle/audio/audio.cpp.

CONSOLE-46 RAN (Nov 4, console_2_s1ib.log, 175,586 lines --
the longest run yet): batch 43's stub FIRED (line 123) and
the vtable-target override route WORKS (no stale-winner
fatal). The whole GOD symptom family is GONE: zero MMIO
writes, zero unmapped touches. BUT presentation is still
blocked: 0 frames presented at the watchdog, retraces stuck
at 6, and 174,720 of the lines are nested-CALL_DL spam. The
guest NEVER calls GXCopyDisp, VISetNextFrameBuffer, VIFlush
or GXDrawDone (all zero in the log) -- its frame loop never
completes a frame, while Aurora chews plausible DL streams
(hex dumps show real matrix/vertex data) with recurring
desyncs (truncated draws) and 277 "XF: PosMtx sub-copy
unsupported" gaps. Prime suspect now: the GX completion
path. CTTR: GXDrawDone 0x80366B44, GXSetDrawDoneCallback
0x80366DD8, GXCopyDisp 0x80367868, VISetNextFrameBuffer
0x803525A4. If GXDrawDone is translated guest code, it polls
guest gxData flags that the HLE GXInit zeroed by design
(batch 40's disease) and that only a guest GP-interrupt
handler would set. Evidence asked: DrawDone/DrawSync/
CopyDisp/NextFrameBuffer hits in runtime/src, plus existence
of the generated files for those four addresses.

GX EVIDENCE BACK (Nov 4): all four CTTR frame-path functions
(GXDrawDone 80366B44, GXCopyDisp 80367868, VISetNextFrameBuffer
803525A4, GXSetDrawDoneCallback 80366DD8) have generated
bodies -- TRANSLATED, none bound. Meanwhile vi.cpp's design
expects the HLE path: VISetNextFrameBuffer writes pending
values, VIFlush arms them, and "present happens in
GXCopyDisp (gx_copy.cpp)" -- the present is driven by the HLE
GXCopyDisp, keyed on g_vi state the translated CTTR bodies
never touch. So the guest's frame loop runs entirely in
guest-SDK land against a gxData the HLE GXInit zeroed, and
the host present path never engages. Batch 44 shape: bind
the CTTR frame-path family to the existing HLE impls
(batch-40 pattern) + a synchronous-semantics GXDrawDone.
Impl names/bindings for gx_copy.cpp and vi.cpp requested.

CORRECTION + BATCH 44 (Nov 4): the VI family and GXDrawDone
were ALREADY bound at CTTR addresses by the runtime's
authors (vi.cpp:1647-1654 appended CTTR block;
gx_stubs.cpp:250 binds 80366B44). Two of my console-46
inferences were wrong: "generated file exists" does NOT mean
unbound (the batch-32 lesson, relearned -- the translator
emits bodies for the whole closure and overrides win by
priority), and "GXCopyDisp never appears in the log" meant
only that its translated body doesn't log. The actual hole:
gx_copy.cpp binds its family ONLY at NSMBW addresses, and
the present lives in the HLE GXCopyDisp. patch-gx-copy-cttr-
bindings.py appends 9 single-line CTTR bindings at EOF in
gx_copy.cpp (SetDispCopySrc 80367230, SetDispCopyDst
80367328, SetTexCopySrc 803672AC, SetTexCopyDst 8036735C,
SetCopyFilter 8036764C, SetDispCopyGamma 80367854, GXCopyDisp
80367868, GXCopyTex 803679D0, SetDispCopyYScale 80367508),
duplicate-guarded, backup gx_copy.cpp.bak-pre44, mock-tested.
Run: patch -> gate (9) -> translate (cttr-translate-44.log)
-> emit -> build cttr-build-copy59.log -> run. Reading
console-47: first presented frames (watchdog quiet or
"presented" > 0, window shows the game) is the prize.

*** FIRST PRESENTED FRAMES (Nov 4, console-46/batch 44) ***
"[vi] first visible guest frame presented" at line 124;
watchdog reports 9 guest frames presented. The GXCopyDisp
binding was the presentation hole -- CTTR now renders and
presents. The run then sat at 9 frames (startup cover waits
for A or 2; a static title may also present once) and later
died on a NEW fatal: access_violation, 16-bit MMIO write to
0xCC005000 (__DSPRegs[0]) at fn_801616B4+0x4C, called from
fn_8018BB98+0x74C (the master update chain) from main. A
guest audio/DSP path writing the DSP register page directly.
Next: read func_801616B4.cpp to see the write's context.

DSP FATAL ANATOMY (Nov 4): fn_801616B4 is a UI/widget render
function (vtable setters + a 2060-byte-stride item list) --
it writes NO MMIO. The crash LR 0x80161700 is the return
address of its FIRST call: vt[15] of the object at
SDA+10588, target fn_801DB25C (0x148 bytes, preceded by a row
of 8-byte thunks). The 16-bit write to 0xCC005000 happened
inside fn_801DB25C's subtree; decomp dsp.c proves the shape
(DSPSendMailToDSP: __DSPRegs[0] = mail >> 16). Unlike
console-45's logged-and-skipped 32-bit writes, this one
FATALED (access_violation, pc=0 -- a host-invoked context).
Next evidence: func_801DB25C.cpp (what it writes/reads/
returns) + where "MMIO write blocked" is produced in
runtime/src (guard shape: can DSP-page writes be made
log-and-skip, or is a stub for fn_801DB25C the surgical fix?).
STILL OPEN: Brandon's report of what the window showed and
whether he pressed A/2.

PRESENT FUNCTION IDENTIFIED (Nov 4): fn_801DB25C is the
game engine's own frame-present method -- GXDrawDone,
optional VIWaitForRetrace, Y-scale math (480/528 line modes),
then batch-44's GXSetDispCopySrc/Dst/YScale, GXCopyDisp,
and VISetNextFrameBuffer + VIFlush. It writes NO MMIO. The
fatal 16-bit write to 0xCC005000 came from HOST code through
the Memory API (memory.cpp throws AccessViolation; the
guest flat-memory path logs-and-skips instead, cf.
console-45). It fired after 9 clean presents -- consistent
with the game's audio starting (title music / first DSP or
AI interrupt activity) and an HLE interrupt-emulation path
writing the DSP register page through Memory::Write16.
Evidence asked: all CC005 hits in runtime/src.

BATCH 45 ISSUED (Nov 4): the DSP mail HLE impls exist
(audio.cpp:400-434, AxDspHle-backed) bound only at NSMBW
addresses. patch-dsp-mail-cttr-bindings.py adds the four
CTTR bindings after their NSMBW twins, mirroring each macro
form exactly (incl. REGISTER_NATIVE_FUNCTION's 0x form):
DSPSendMailToDSP 8035C01C, DSPCheckMailToDSP 8035BFE4,
DSPCheckMailFromDSP 8035BFF4, DSPReadMailFromDSP 8035C004.
Backup audio.cpp.bak-pre45; mock-tested. Bindings precede
retranslation so the leaf inliner skips these addresses.
Run: patch -> gate (4) -> translate (cttr-translate-45.log)
-> emit -> build cttr-build-copy60.log -> run. Reading the
next console: frames keep presenting past 9 and the title
settles (watch for the cover/input behaviour and any audio
life), or the next distinct fault.

CONSOLE-47 (batch 45): DSP mail fault GONE (audio worker
started). 9 frames presented again, then a NEW fatal whose
log trail is explicit: "[audio] unknown AX command 0x2420 at
word 17; abandoning the command list" -- then an
AccessViolation at 0x24200002 in a GXCopyDisp-active
context. The hexdump shows the guest AX command list
contains the pointer 0x80482420; the HLE's AX parser read
its LOW half (0x2420) as a command opcode -- CTTR's (2005)
AX command-list layout differs from NSMBW's (2009), which
the parser was written against. The abandoned list leaves
state the present path then touches at the mis-composed
address 0x24200002 (= 0x2420 low half + 0x0002 field).
Next: read the parser + abandon path ("unknown AX command"
site in runtime/src) and decide: teach it CTTR's format, or
make abandonment fully quiesce (video continues, AX audio
dropped) for the spike.

PARSER READ (Nov 4): ax_mix.cpp's parser consumes the guest
command list as 16-bit words (ReadAddress = Hilo(hi,lo));
unknown commands abandon the list cleanly and log once.
The fatal address 0x24200002 IS Hilo(0x2420, 0x0002) -- a
later ReadAddress landed exactly on the unknown command
word, so another stage/entry point kept consuming the
misaligned list and composed a wild address whose read
threw through Memory:: (fatal), unlike the guest flat path.
CTTR's full AX decomp (incl. AXCL.c, the list builder) is
in the local research tree, so a grammar-correct parser is
possible LATER; for the spike, batch 46 = tolerance: make a
bad list degrade to silence instead of death (catch the
AccessViolation around the mix step and/or make MixRead*
non-throwing). Evidence asked: MixRead definitions, the
switch function's caller, existing catch sites.

PARSER STRUCTURE (Nov 4): ax_mix.cpp runs TWO passes -- a
bounds-checked scan/validate pass (skip(n) word counts,
returns idx <= size) and ExecuteCommandList (unchecked
ReadAddress + MixRead32 dereferences). An AXCommandLayout
enum (Old vs New) already exists. The containment point for
batch 46 is the MixRead/MixWrite boundary: making those
non-throwing (0 on unmapped reads, dropped writes) turns
every misparse into silence instead of process death,
without touching parser grammar or control flow. Asked for
the MixRead/MixWrite definitions and ExecuteCommandList's
caller.

BATCH 46 ISSUED (Nov 4): ax_internal.h's MixReadBE/MixWrite16
already had the worker-safety rule (on the mix worker:
report + return 0 / drop) but fell through to THROWING
Memory::Read/Write off the worker thread -- and the mix also
runs inline elsewhere (frame-wait servicing), where CTTR's
misaligned list composed 0x24200002 and the throw killed
the process. patch-ax-mix-tolerance.py wraps the two
fallbacks in try/catch (Memory::AccessViolation) that takes
the same report-and-degrade path; happy path byte-identical.
Mock-tested (fresh, idempotent, braces balanced). RUNTIME-
ONLY change: no retranslation; build cttr-build-copy61.log
and run directly. Reading the next console: frames keep
presenting past 9 with the title settling (audio degraded/
silent is acceptable for the spike), or the next fault
outside the mix helpers' reach.

CONSOLE-48 (batch 46): SAME fatal (0x24200002, len 4), one
beat after the unknown-command report, and NO batch-46
"out of range" reports -- the throwing access does NOT go
through MixReadBE/MixWrite16. New hard evidence: the
fault's backchain contains __AXOutNewFrame+0xCC return
addresses -- the guest AX frame callback was executing
(serviced inside GXCopyDisp's frame wait, active=GXCopyDisp)
when the access threw via the checked Memory API. So a
second consumer of the audio state (AxDspHle-side or the
callback's own HLE callees) composes/uses the wild address
outside the mix helpers' protection. Asked for: audio
folder file list, both ExecuteCommandList call sites, and
direct Memory:: reads in the audio folder outside
ax_mix/ax_internal.

CALL-SITE STRUCTURE (Nov 4): the mix entry scans the list,
collects aux-input addresses composed Hilo-style from list
words (addAuxInput(wordAddress(...))), reads them via
ReadGuestS32Buffer, then defers to the worker or executes
inline. If the misaligned scan collected 0x24200002 as an
aux address and ReadGuestS32Buffer reads via Memory::
directly, the throw fires on the servicing thread
(active=GXCopyDisp) -- matching every detail, including the
report order (execute of the previous list first, then the
new list's aux read). Asked for ReadGuestS32Buffer's
definition + all direct Memory:: uses inside ax_mix.cpp.

READ SITES (Nov 4): inside ax_mix.cpp, direct Memory:: uses
are the command-list load (line 316, valid guest address),
and the AX DSP task-struct writes (1459+, structural
addresses). ReadGuestS32Buffer is CALLED at 347 and 1316 but
not defined in ax_mix.cpp -- its definition should be in
ax_memory.cpp (the AX memory layer, home of MixResolveRange).
Asked for that definition to shape batch 47 (route it
through the now-non-throwing MixRead32, or catch at its
boundary).

CONFIRMED (Nov 4): ReadGuestS32Buffer (ax_memory.cpp) has
the identical flaw -- fast resolve path, worker degrade
path, then a THROWING Memory::Read32 loop off the worker.
That is the 0x24200002 detonation point (aux-input read on
the servicing thread). Note: the earlier folder-wide grep
was truncated by Select-Object -First 14 (bak duplicates
crowded it), so ax_memory.cpp/ax_effects.cpp were never
actually cleared. Batch 47 will cover every Memory::
fallback in ax_memory.cpp (+ ax_effects.cpp if any) with
the batch-46 treatment. Sweep asked without truncation.

FULL SWEEP (Nov 4): ax_effects.cpp already wraps guest-state
access in try/catch (AccessViolation) -- the authors'
established pattern, validating batches 46/47. ax_memory.cpp
is otherwise guarded (Contains checks, TryRead/TryWrite),
EXCEPT the two buffer helpers: ReadGuestS32Buffer (line 216,
confirmed) and its write twin at line 201, both with the
throwing off-worker fallback. Batch 47 covers both; asked
for the write helper's verbatim text (ax_memory.cpp
lines ~180-220).

BATCH 47 ISSUED (Nov 4): patch-ax-memory-tolerance.py wraps
both ax_memory.cpp buffer-helper fallbacks (WriteGuestS32Buffer
+ ReadGuestS32Buffer) in try/catch (Memory::AccessViolation)
-> report + degrade (drop writes; zero-fill remaining reads),
mirroring batch 46 and the ax_effects.cpp precedent.
Mock-tested. Runtime-only: build cttr-build-copy62.log, no
retranslation. With 46+47, every guest-address consumer in
the AX mix path is now non-throwing; if the boot proceeds
past the audio start into a settled title, the tolerance
ring is complete for this stretch. The REAL fix (teach the
parser CTTR's AX grammar from the local AXCL.c decomp)
remains a later fidelity project -- audio will be degraded
until then.

*** CONSOLE (batch 47 run, console_6_uizo.log): 517 FRAMES
PRESENTED at the 12 s watchdog *** (prior best: 9). The
game blew past the audio start; the tolerance ring (46+47)
holds -- the unknown-command report fires once and nothing
dies. The log (244,604 lines, longest yet) ends amid ~1,701
NON-FATAL invalid-access dumps: active=GXCopyTex (batch-44
HLE), LR fn_801D68D0+0xE4, addr 0x24200182 len 4 -- the
0x2420xxxx poison now surfacing in the texture path (a
texture descriptor struct sits at r31=0x8042E2A8 with
320x240-ish fields). No crash artifacts were produced. Open:
whether the process was still alive when the log was
grabbed, and ABOVE ALL what the screen shows -- Brandon's
visual report is now the decisive evidence (title visible?
correct? cover lifted with A/2?).

VISUAL REPORT + DUMP CYCLE (Nov 4, batch-47 run continued):
Brandon's visual report finally landed: NOTHING on screen
but the runtime's own WiiCompiled branding -- despite the
517-frames-presented log line, no guest content reaches
the window. The process loops endlessly printing the same
invalid-access dumps (he pasted six; all identical in
structure).

Dump-cycle analysis (Nov 4): every dump is the same call --
active=GXCopyTex (0x803679D0, batch-44 HLE), LR
fn_801D68D0+0xE4, live chain main -> fn_8018BB98 ->
fn_80070264 -> fn_8008D278 -> fn_80089C18 -> fn_801DDA38
-> fn_801DDDB0 -> fn_801DF6A4 -> fn_801D68D0 -> GXCopyTex
(a per-frame renderer path, not one-time init). The fault
address cycles through EXACTLY three values: 0x24200002,
0x24200182, 0x24200302 -- stride 0x180, all unaligned
(+2 mod 4), len 4. The guest texture descriptor at
r31=0x8042E2A8 is CLEAN: 320x240, channel masks at +0x38,
and a VALID data pointer at +0x50 (0x80B30EA0); its twin
at r30=0x80B30E00 carries the same 320x240 fields. So the
poison is NOT in the guest descriptor -- the bad address
is computed inside the HLE copy path (gx_copy.cpp) from
state we cannot see in guest dumps. Real GXCopyTex (decomp
GXFrameBuf.c) never dereferences dest at all (it packs
dest & 0x3FFFFFFF into a BP register); the HLE version
performs a real memory copy, so its address math is the
suspect. 0x2420 remains the low half of guest pointer
0x80482420 (seen in the list at r6=0x804816D4/0x804819D4,
whose entries pair that pointer with 0x0002).

NEXT EVIDENCE (asked Nov 4): gx_copy.cpp itself (the
GXCopyTex + GXSetTexCopyDst impl bodies) and the generated
caller generated\cttr\functions\func_801D68D0.cpp (what
dest the guest actually passes in r3). Batch 48 shapes
itself from those two files. Side note: each dump is
~140 lines of hexdump/stack walking -- the flood itself
is expensive and may be starving real progress.

CALLER + LINE MAP (Nov 4): the generated caller settles the
guest side -- func_801D68D0 sets r3 = FlatRead32(r31 + 80),
i.e. dest = descriptor field +0x50 = 0x80B30EA0 in the
dumps (VALID), and r4 = r26 & 255 (clear flag), then
InvokeDirectCpu<0x803679D0>. So the guest passes a good
dest; the 0x2420xxxx poison is created INSIDE the HLE
wrapper. gx_copy.cpp line map: line 42 comment ties
GXCopyTex destinations to CPU cache ops (SPM offscreen);
the copy impls call Aurora-shaped GXSetTexCopySrc (114,
191, 251), GXSetTexCopyDst (121), and at line 242
GXCopyTex(GuestToHostPtr(da), (GXBool)c) -- GuestToHostPtr
resolving da is the likely dump source. Impl names do NOT
use the addr-suffix pattern (both GXCopyTex_ greps came
back empty). Asked for gx_copy.cpp lines 30-269 verbatim
to find where da is assigned.

CORRECTION (Nov 4, supersedes the two entries above): the
0x2420xxxx poison is NOT computed in the GX copy path.
Log-wide tally of console_6_uizo.log: 1,701 AccessViolation
dumps, ALL at the same three addresses (0x24200002,
0x24200182, 0x24200302), spread across THREE active
functions -- GXCopyTex (1,152), GXCopyDisp (417),
GXDrawDone (132). Their common path is the frame wait:
both copy impls call GXDrawDone() first, and the mix
services inline during those waits. The FIRST fault is at
log line 2413, immediately after line 2412 "[audio]
unknown AX command 0x2420 at word 17; abandoning the
command list" and the mix-worker start at 2411. And
[spmcopy] logging proves every GXCopyTex dest is valid
(640x480 -> 0x80A9FA20 / 0x80B30EA0 / 0x80B43B40, 160x120
-> 0x80BFB220, repeating per frame). The stride 0x180 =
384 bytes = 96 s32 samples = exactly one AX frame buffer:
per mix service, three buffer reads at poisoned base +
n*0x180. Batch 46/47's try/catch stopped the crash but
the memory layer prints its ~140-line dump BEFORE the
throw, so every serviced wait re-dumps -- the flood
(1,701 dumps dominating a 244k-line log) is itself the
slowdown consistent with a screen that never progresses.
BATCH 48 DIRECTION: Contains pre-checks at the AX guest-
buffer read sites so poisoned addresses never reach the
Memory layer at all (degrade silently like the worker
path). Verbatim post-46/47 text of the candidate sites
requested Nov 4.

BATCH 48 ISSUED (Nov 4): patch-ax-contains-precheck.py adds
Memory::Contains pre-checks at all five AX fallback sites
(ax_memory.cpp Write/ReadGuestS32Buffer, ax_internal.h
MixReadBE + MixWrite16, ax_effects.cpp
ResolveGuestThreadRange) so unmapped ranges degrade BEFORE
any Memory:: access -- no access, no dump. Mapped ranges
fall through byte-identically. Mock-tested: fresh apply
(5 inserts, markers 2/2/1, backups .bak-pre48), idempotent
re-apply, brace deltas preserved, corrupted-anchor abort
writes nothing. Runtime-only, build copy63, no
retranslation. Proof of site: the run's one "worker
skipped" line reports 384 bytes at 0x24200002 -- a full
96-sample buffer call through ReadGuestS32Buffer.
Watch the run for: zero DUMPING CPU STATE blocks, frames
climbing past 517, and whether the screen finally moves.

*** CONSOLE-49 (batch 48 run): DUMP FLOOD ELIMINATED ***
AccessViolation dumps: 1,701 -> 0. "worker skipped" fired
exactly once (0x24200002, 384 bytes -- the designed
one-time report). Watchdog: 688 frames presented at 12 s
(was 517), VI black=0. Log shrank 244,604 -> 64,602 lines.
The unknown-AX-command report still fires once (audio
stays degraded; grammar parser remains the fidelity
project). What remains is 63,924 lines of ONE Aurora line:
"Ignoring nested GX_CMD_CALL_DL" -- 99% of the log, ~91
per frame. Aurora drops draws nested inside display
lists; if CTTR renders through nested DLs, that is both
the new flood and the prime suspect for a still-blank
screen. Smaller fry: 186 XF PosMtx sub-copy unsupported,
~125 truncated-draw desyncs, 16 unknown-opcode FIFO stops.
Next verdict is again Brandon's eyes on the batch-48 run:
does the screen show anything now, and does A/2 lift the
cover at full speed?

VISUAL VERDICT (Nov 4, screenshot): the window shows ONLY
the runtime's own startup cover -- black screen, tiny
centered text "Made by JosiahG / A Super Paper Mario PC
recomp. Built on WiiCompiled's code." The game presents
688 frames BEHIND that cover (VI black=0); the cover has
never lifted in any run. The [vi] log line has said it all
along: "waiting for A or 2 to lift the startup cover."
So the open question narrows to the cover's lift condition:
what input does it poll, and does that path exist for a
GameCube PAD-driven game on a Wii-remote-shaped runtime?
Evidence asked: every "cover" mention under runtime/src/hle
plus the vi.cpp cover code with context; and whether
Brandon has pressed anything (keyboard/controller) during
these runs.

COVER LIFT PATH (Nov 4): vi.cpp lives at runtime\src\hle\
vi.cpp (not hle\vi\vi.cpp). Its comment at line 1051ff:
NSMBW lifted the cover at the first visible frame, but
"Mario Kart's ..." (a prior port's change) made it stay up
until the player presses A or 2 -- implemented in
hle/input/kpad.cpp. kpad.cpp:298: "The startup cover
(settings_overlay) waits for A or 2; the press itself never
reaches the game." So the cover polls the KPAD (Wii
Remote) state. Whether that state updates without a guest
KPADRead -- and what host keys/buttons feed it -- is the
remaining question; kpad.cpp 265-350, vi.cpp 1039-1078 and
the settings_overlay source asked Nov 4.

COVER MECHANISM SOLVED (Nov 4): the A/2 check lives in
kpad.cpp's ReadSample(), which runs ONLY from
KPAD__Read_HLE / KPAD__ReadEx_HLE -- i.e. only when the
guest calls KPADRead. CTTR is a GameCube PAD game and
never calls KPAD, so NotifyStrapInputAccepted() can never
fire and g_strapInputAccepted stays false forever: NO
host press can ever lift the cover for CTTR. Not a
"Brandon didn't press" problem -- the watcher is never
executed. StartupScreenVisible() (settings_overlay.cpp)
has further gates beyond acceptance: g_bootShadersReady,
a 60-frame dismiss transition, a 180-frame title-card
minimum hold (688 presented clears it), and
SpmMapSweep::Seq() == 0 -- an SPM-specific sequence read
whose value under CTTR is unknown and could pin the cover
by itself. Batch 49 shape: pump the same ReadKpadSample
A/2 test from a per-frame host path (vi.cpp's present,
beside the "waiting for A or 2" log) and/or auto-accept
for KPAD-less guests, after Seq() and g_bootShadersReady
are checked. Evidence asked Nov 4.

COVER GATES UPDATE (Nov 4): g_bootShadersReady is
host-side and self-resolving -- UpdateBootShaderState()
(settings_overlay.cpp) sets it when Aurora's queued
pipeline count reaches 0, with a 3-minute failsafe. Not
a hard blocker. SpmMapSweep::Seq() is still unknown: the
definition did not surface (only call sites); vi.cpp:644
calls SpmMapSweep::Tick(ctx, presentedFrames) on every
present, so Seq() returns whatever the sweep's SPM-shaped
tracking computes from guest memory -- under CTTR it may
sit at its initial value, and if that is 0 the
StartupScreenVisible() Seq()==0 clause pins the cover
even after an accepted press. Sweep module source asked.
Also noted: the cover Brandon sees is the minimal text
form ("Made by JosiahG...") because the chapter-card form
needs SPM game fonts (gameFonts false under CTTR).

BATCH 49 READY (Nov 4) -- patch-cttr-cover-lift.py,
mock-tested (fresh apply, idempotent re-apply, corrupted
anchor aborts writing nothing). Seq() is SOLVED:
spm_map_sweep.cpp Seq() { TryRead32(kNowSeq=0x8056D0D8)
}, SPM's sequence global; console-49 proves the pin:
"[place] boot -> logo (frame 0)" and no further transition
in 688 frames, so the u32 there is a constant 0 under CTTR
and StartupScreenVisible()'s Seq clause is permanently
true. g_bootShadersReady is host-side/self-resolving
(UpdateBootShaderState: Aurora queue drains to 0, 3-min
failsafe). So the cover had TWO independent permanent pins
for CTTR: the KPAD-only accept watcher AND Seq()==0.
Batch 49 is env-gated (CTTR_COVER_LIFT, the tree's getenv
idiom; unset = zero change for SPM/NSMBW/MKW):
settings_overlay.cpp skips the Seq clause under the gate
(file-local CttrCoverLift helper; <cstdlib> include added
if absent), and gx_copy.cpp's GX__CopyDisp calls
NotifyStrapInputAccepted() under the gate -- restoring
NSMBW's original first-frames lift for opt-in runs. Other
gates (shaders, 180-frame minimum, 60-frame transition)
still apply. Run block sets $env:CTTR_COVER_LIFT="1"
before launch; build copy64. Watch for the "[cttr]
CTTR_COVER_LIFT" log line and the cover lifting after
~frame 240 onto CTTR's own screens.

CONSOLE-50: BATCH 49 VERIFIED (Nov 4). The
"[cttr] CTTR_COVER_LIFT" accept line fired, 677 frames
presented at the 12 s watchdog, VI black=0, AccessViolation
dumps still 0, "worker skipped" still exactly 1. Brandon's
4.2 s clip (127 frames, pixel-analysed): the branding
cover appears in NO frame -- the cover is gone and CTTR
is on screen for the first time. What it shows is sparse,
broken rendering: a dark-teal field (RGB 5,56,78), a black
sub-rectangle (~965x426) at the window's top-left holding
a solid white block (exactly 480x201) that comes and goes
(aliasing in the 30 fps capture of a ~56 fps present
stream prevents a clean blink-period read). The guest
image does not fill the window -- present-scaling geometry
under CTTR's VI config is an open secondary question.
The rendering poverty matches the log: "Ignoring nested
GX_CMD_CALL_DL" x64,451 (~95/frame, first at log line 166,
last at 65,144 -- all run long), plus 53 truncated draws
at the same vtxCount=24964 (one stream position desyncing
identically every frame) and 186 "XF: PosMtx sub-copy
unsupported". CTTR, like most GameCube titles, builds its
scene from display lists called inside display lists;
Aurora's FIFO decoder drops every nested call, which is
most of the scene graph. NEXT: batch 50 targets nested
CALL_DL in Aurora's decoder (aurora-main in Brandon's
tree); decoder source around the message requested.

CALL_DL INVESTIGATION (Nov 4, local reference tree
~/workspace/spm-switch-scout/NewSuperPaperBros/wiicompiled
-- same codebase, may differ in CTTR-specific bindings):
(1) Aurora's command_processor process() CALL_DL case is
an UNCONDITIONAL drop (skip 8 bytes, warn) -- there is no
nesting check; Aurora never follows a call by design.
(2) By design the runtime pre-flattens: gx_dl.cpp
WalkDisplayList + DlFlattenVisitor recurse into nested
lists (depth cap 8) and GX__CallDisplayList_80172f64
submits only flattened or provably call-free streams to
Aurora's GXCallDisplayList -> process_display_list ->
process(). gx_fifo.cpp likewise intercepts CALL_DL in
the guest FIFO and routes it to the same HLE impl.
(3) Console-50 contains ZERO "[spmdl] call" lines -- the
HLE impl's own first-60-calls log never fired -- so in
the CTTR run the flattening path apparently never ran:
CTTR's lists reach Aurora through another route, raw.
(4) Aurora's own hex dumps in console-50 prove stream
DESYNC, not just dropped calls: process() decodes vertex
floats as commands from ~pos 74 (0x43a28000 = 325.0f,
0x3f410000, 0x41c00000 = 24.0f; "unknown opcode 0xFF" =
NaN/0xFFFFFFFF bytes; phantom CALL_DL = 0x40 bytes inside
float data; truncated draw vtxCount=24964 read from data
bytes). So most "nested" warnings are garbage decode
AFTER a desync point -- the primary bug is upstream of
the drop: an unflattened route and/or a vertex-size
model that diverges from CTTR's layouts ~74 bytes into
the stream. Batch 50 reframed accordingly: find the
actual submission route in Brandon's tree first (his
CallDisplayList binding/impl set), then fix that path's
flattening/layout handling. Refined evidence requested.

ROUTE HUNT UPDATE (Nov 4): Brandon's tree matches the
reference (gx_dl.cpp [spmdl] log present at his line 1453;
Aurora CALL_DL case identical at his line 740; the ONLY
GXCallDisplayList binding is NSMBW 0x80291458 -- no CTTR
binding exists). Console-50 deep tally: no "raw draw
vertex-size mismatch" (submit_raw_draw path is clean/not
used); the desynced buffers are genuine GX streams (XF
matrix loads parse cleanly: -1.0/1.0/320.0/-240.0) that
slip framing a few dozen bytes in; draw counts read as
0x6184 = the bytes of the BP-opcode runs (61 84 ...) the
streams are full of; buffer heads show Aurora-extension
commands (50 00 35 = INVALIDATE_TEX_ALL, zero payload --
Aurora's own API encodings, e.g. via the batch-40
GXInvalidateTexAll thunk), and "unknown subcommand
3510/6100" are drift artifacts of slipped framing.
BATCH 50 (DIAGNOSTIC, patch-aurora-stream-fingerprint.py,
mock-tested against the real Aurora sources): rate-limited
[cttr-dbg] fingerprints -- process() entry (size + first
24 bytes, first 32), handle_aurora (subCmd + pos, first
48), fifo drain() (size + head, first 32). One run will
separate drain-fed buffers from process_display_list
submissions and show the framing state at every Aurora
command. Build copy65; console-51's [cttr-dbg] lines are
the evidence. The fix is batch 51, designed from them.

CONSOLE-51: batch 50's diagnostics NEVER FIRED -- zero
[cttr-dbg] lines in 64,212 lines, while the CALL_DL flood
ran unchanged (63,533) and the batch-49 cover accept
fired. process() demonstrably ran (the warnings come from
inside it), so the diagnostic code was not in the binary:
either the patch did not apply (his command_processor.cpp
has ~41 more lines than the reference -- an anchor may
have missed, and this round came with no terminal paste
to confirm the gate), or his build compiles Aurora from a
different directory than tree-root aurora-main (e.g. a
_deps copy), making the edits inert. Two-command check
requested: Batch-50 marker grep on the patched files +
which command_processor.cpp path the build's ninja files
actually compile.

CHECK RESULT (Nov 4): marker grep printed NOTHING -- the
batch-50 patch never landed in his files. The ninja output
proves the build DOES compile tree-root aurora-main
(build-cttr/build.ninja -> aurora-build target from
C:/dev/cttr-wiicompiled/aurora-main/lib/gx/
command_processor.cpp), so the wrong-directory theory is
dead; it was an anchor miss in his ~41-lines-longer
command_processor.cpp, and the script's ANCHOR FAIL line
scrolled past in the pasted block. Lesson banked: future
run blocks carry a hard in-block gate (throw if the marker
grep is empty) so a missed patch stops the block before
the build instead of producing a silent no-op run.
Requested his exact anchor neighbourhoods (process()
head, handle_aurora subCmd lines, drain() head) to write
a line-tolerant v2 against his real text.

BRANDON'S ANCHOR TEXT (Nov 4): his process() and
handle_aurora() heads match v1's anchors VERBATIM (so v1
most likely never executed, or died on the fifo anchor);
his drain() differs -- sAsyncDecode prologue + NSMBW
stage-timer lines the reference lacks. BATCH 50 v2
(patch-aurora-stream-fingerprint-v2.py): line-anchored
inserts (signature line / subCmd read + pos+=2 / drain
guard-block close), mock-tested on the reference shape,
a Brandon-shaped variant (async prologue + his comments)
and a corrupted-guard variant (named abort, no writes).
Run block hard-gates: throws before building if the
script is missing from the tree root or the Batch 50
markers are absent after patching. Build copy66;
console-52's [cttr-dbg] lines drive batch 51.

CONSOLE-52: STILL zero [cttr-dbg] lines in a fresh run
(pid 41944; cover accept fired; CALL_DL flood 63,380;
the aurora::gx::fifo logger demonstrably flows -- other
warns from the same module print). Since "Ignoring
nested" is Log.warn in the SAME file and SAME static Log
as the process() insert, a binary containing the patch
could not stay silent through ~63k process() calls. So
either v2 also failed to land (atomic abort -> gate
throw) or the build never recompiled/relinked Aurora.
Deciding evidence requested: current marker count, the
copy66 build log's aurora/error lines, and exe-vs-source
mtimes. No new patch until this is understood -- two
silent cycles is the limit for guessing.

DECIDING EVIDENCE (Nov 4): marker count 0; exe mtime
11/04 13:05:55 (the batch-49/copy64 binary); source
command_processor.cpp mtime 11/01 00:55:52 -- the file
has not been touched since Nov 1. CONCLUSION: neither
v1 nor v2 ever wrote anything; consoles 51 AND 52 both
ran the copy64 binary, which is why nothing changed
between them. The patch STEP is what keeps failing on
his machine (script delivery or an unseen anchor in his
drain guard -- his paste cut off before the sBufferSize
guard lines, the one site never actually sighted).
Process fix: stop the one-shot block for this patch --
run the patch as its own step, read its output together,
then build. Asked: Test-Path on the v2 script in the
tree root + his exact sBufferSize==0 guard lines.

ROOT CAUSE OF THE BATCH-50 DELIVERY FAILURES (Nov 4):
Test-Path on the v2 script in his tree root = False --
the attachment/Downloads/copy route silently never
delivered v1 or v2. His drain guard text is EXACTLY the
reference shape (if (detail::sBufferSize == 0) { return;
} after note_drain_wait), so the anchors were never the
problem. BATCH 50 v3: same inserts, leaner script,
delivered INLINE -- a PowerShell single-quoted here-string
piped straight into python's stdin (python -), no file,
no Downloads, no copy step. Verified: pure ASCII (safe
for PS 5.1 piping), applies via the exact stdin route on
a Brandon-shaped mock, idempotent. Split flow stands:
patch-only block + marker gate first, build block after
his output confirms. STANDING LESSON: for Brandon's
tree, deliver patch scripts inline via here-string ->
python stdin; the attachment route is unreliable and
fails silently.

BATCH 50 v3 LANDED (Nov 4): the inline here-string route
worked first try -- both files patched, gate shows the 3
markers (command_processor.cpp:629 process, :3268
handle_aurora, fifo.cpp:143 drain). Inline delivery is
now the proven route for his tree. Build copy66 + run
issued; console-53's [cttr-dbg] lines (first 32 process
buffers, first 32 drains, first 48 aurora subcommands)
will separate drain-fed buffers from process_display_list
submissions and expose the framing slip for batch 51.

CONSOLE-53 VERDICT (Nov 4): the batch-50 diagnostics
fired (32 drains / 32 processes / 48 aurora subcommands,
all capped). ROUTE PROVEN: every early drain is followed
by its process() with identical size+head -- the garbage
arrives via Aurora's own FIFO drains, NOT
process_display_list. The recurring offender is one
~164.5 KB encoded stream per frame whose drains start at
ROTATING phases of the same bytes (the BP run
"...61 00 15 61 56 61 00 3d 53 35" into XF load
"10 00 06 10 20 3f 8c cc cd..."): clean starts (61.., 10..,
50 00 35) alternate with mid-command starts (35..,
53 35.., 3d 53 35..). When a buffer starts one byte into
"50 00 35", process() reads subcommand 0x3510, logs
"stopping FIFO decode" and DISCARDS ALL 164,568 BYTES
(16 such events); other misaligned buffers decode as
garbage (63,452 CALL_DL drops = 0x40 payload bytes at
command positions; 193 truncated draws). Clean small
drains (20-byte BP blocks, 15-byte invalidate blocks,
an 82-byte buffer with a well-formed TEXOBJ 0030) decode
perfectly -- encoder and decoder agree whenever phase
holds. The only defect is stream phase at drain
boundaries; process() requires aligned input, has no
resync and no tail carry-over.
BATCH 51 (DIAGNOSTIC, patch-aurora-buffer-dump.py,
mock-tested incl. abort-without-batch-50): drain()
writes the first two >64 KB buffers to
cttr-dbg-buffer1.bin / cttr-dbg-buffer2.bin in the CWD.
Offline byte-level parse of those files will show
whether the break is a cut (split command tails) or an
interleave (foreign commands embedded), which decides
where the batch-52 fix lands. Build copy67; evidence =
the two .bin files + console-54.

BUFFER PARSE VERDICT (Nov 4): buffer1 (159,226 B) ENDS
MID-COMMAND -- its last command is a BP load at 159,222
with only 4 of 5 bytes present (61 00 3d 53 + missing
byte). The recurring stream shows the missing byte is
0x35 (…61 00 3d 53 35 then a clean XF load), so the
stream itself is continuous and well-formed; the DRAIN
BOUNDARY cut it. Combined with console-53 (buffers
starting mid-command die via the 3510 discard or decode
as the CALL_DL flood) and the source fact that process()
returns size (discard-the-rest) on hard errors, the
defect is fully pinned: drains cut commands and nothing
carries the partial tail forward. Walker tools:
tools/walk_gx.py, walk_gx2.py (Aurora-faithful, with
CP->VAT/VCD state tracking).
BATCH 52 (FIX, patch-aurora-tail-carry.py, mock-tested
on reference + Brandon-shaped trees, diffs eyeballed --
the first mock run caught a braceless-if throw that
would have become unconditional; the patcher now
consumes both lines): process() reports a truncated
final command (draw failure -> commandStart; handle_xf
truncation -> pos=size+1 sentinel; lastCmdStart tracker
makes the final return report the truncated command's
start on overshoot). drain(): the count==0&&retried
throw becomes a break, and the sBufferSize=0 reset
becomes a memmove that carries [consumed, size) into
the next drain, with a >16-drain no-progress poison
guard that drops a stuck tail with a log line. Aligned
streams are untouched (leftover 0). Diagnostics from
batches 50/51 stay in as verification. Build copy68;
console-55 + fresh buffer dumps + the screen itself
are the verdict.

CONSOLE-55 (batch 52 run): the fix is LIVE (the poison
guard fires: "dropping N stuck undecoded FIFO bytes
after 17 drains") but it did NOT cure the flood:
CALL_DL 63,478 (was 63,597), unknown subcommand 16,
truncated draws 193, PosMtx 186 -- all unchanged; 685
frames presented. The guard drops ~7.4-9.7 KB stuck
tails constantly (818 lines; six recurring sizes x ~136)
-- roughly one stuck residue per frame. And the giant
drains STILL arrive with rotated heads (35 10.. /
3d 53 35.. / 53 35..), i.e. the buffer at drain time
does NOT start with the tail the previous drain carried.
Conclusion: in Brandon's fifo revision the giant buffers
do not flow through the sync drain's carry path the way
the reference's do -- his async worker/hand-off mechanics
own them, and that code is unseen. Batch 53 must be
designed against his actual fifo.cpp (requested as an
upload). Do not iterate the carry design blind.

HIS REAL FILES READ (Nov 4, cttr-53-sources.zip):
fifo.cpp (694 lines) has a full async decode-thread
design (items/batches/hand_off), BUT sAsyncDecode is
false in these runs (the drain logger fires; drain()
early-returns to finish() when async) -- so batch 52
landed in the right path after all. The buffer mixes
segment kinds: FIFO bytes + copied DL bytes
(queue_display_list appends) + raw-draw vertices
(queue_raw_draw appends), with sDrainMark/insert_at_
drain_point machinery on top. His process() return
sites audited from his real command_processor.cpp:
the ONLY discard path batch 52 cannot see is the
GX_LOAD_AURORA case (his line 771): handle_aurora
opens with if (pos + 2 > size) return false, and the
case turns any false into return size. A drain cutting
right after an Aurora opcode (buffer ends 50 / 50 00)
consumes the partial command; its last byte (35)
starts the next drain -> the 3510 discards + flood,
and pos never overshoots, so batch 52 stays blind.
BATCH 53 (patch-aurora-header-truncation.py, tested
against his real file; diff = 6 lines at the one case):
if size - commandStart < 3, return commandStart
(carry) instead of size; unknown subcommands still
discard. Build copy69; console-56 is the verdict
(3510 -> 0, CALL_DL collapse, guard silent, screen).

CONSOLE-56 (batch 53 run): NOT cured. CALL_DL 64,208
(was 63,478), unknown subcommand STILL exactly 16,
truncated draws STILL exactly 193, PosMtx 188. Only
movement: poison-guard drops 818 -> 145 (the header
carry does fire). The 16/193 counts are now essentially
RUN-INVARIANT across batches 50-53, and the two dumped
buffers are size-identical every run (159,226 /
164,568) -- deterministic. New suspicion: the bulk of
the flood never passes through drain() at all -- guest
display lists submitted via process_display_list()
(which calls process() directly, still discards on the
aurora false path, and is where genuine nested CALL_DL
opcodes from CTTR's own lists would be dropped by
design). Batch 50 fingerprinted drains, not callers.
BATCH 54 = attribution: split the CALL_DL / unknown-
subcommand / truncated-draw counters by caller using
the g_replayingDisplayList flag process_display_list
already sets. That fork decides the fix layer: DL path
(flatten/bind GXCallDisplayList properly) vs drain path.
ACCESS (Nov 4): Brandon asked about direct work on his
PC. Route exists: this VM joins his tailnet (Tailscale
connector; he approves), his LOQ runs Windows OpenSSH
Server with Sudo's ed25519 public key, then Sudo SSHes
in through the tailnet proxy and runs the patch/build/
log loop directly. Setup offered; awaiting his call.

CONSOLE-57 (batch 54 attribution run, driven over SSH
by Sudo; exe run via a one-off interactive scheduled
task in Brandon's session -- session-0 launches stall
after the config line, do not use them): verdict is
total. CALL_DL fifo 63,557 / dl 0. Unknown subcommand
fifo 16 / dl 0. Truncated-draw stops fifo 64 / dl 0.
Guard drops 1,295 lines; 668 frames at the 12 s
watchdog; VI black=0. THE FLOOD IS 100% FIFO-DRAIN
PATH; the display-list hypothesis is DEAD. Next audit:
the runtime pump (his gx_fifo.cpp, unread) and drain()'s
own offset accounting across multi-segment process()
calls (a mid-buffer early return followed by drain
resuming at a segment boundary instead of commandStart
would consume part of a command and rotate the phase,
matching every observation).

CONSOLE-59 / BATCH 56 BYTE VERDICT (Nov 4): the 40
drain windows are contiguous and the stream is
deterministic. Stitched-stream walk dies at a seam
with subcmd 3510. Byte-level: the recurring BP command
61 00 3d 53 35 is SPLIT by the 20-byte present BP
block (61 49 000000 / 61 4a 077e7f / 61 4d 000028 /
61 4e 000100) landing INSIDE it -- split point drifts
1 byte per cycle (4|1, 3|2, 2|3 across cycles). The
block enters the buffer between two chunks of the
scene stream. Batches 52/53/55 proved: process()
reports truncations, drain() carries correctly,
stale-mark inserts never happen. The splice is an
at-end append/insert into a mid-command tail by a
second producer. Batch 57 = producer witness: log
kind/size/head for every queue_display_list /
queue_raw_draw / insert_at_drain_point around the
giants to name the block's producer and the chunk
that ends mid-command. NOTE: RT_LOGF lines ([spmdl]
etc.) do NOT appear in the redirected console logs --
an earlier [spmdl]-absence conclusion was void.

BATCH 57 VERDICT (console-60): the producer witness
on queue_display_list / queue_raw_draw /
insert_at_drain_point NEVER fired in a full run --
the giants do not enter Aurora's buffer through
those three. The Aurora GX API serializes via
fifo.hpp's inline write_data/write_u32 (GXFrameBuffer
copy setup writes BP regs 0x49/0x4A/0x4D/0x4E that
way: the 20-byte seam block is GXSetTexCopySrc/Dst).
Tail trace of the first giant: its last ~230 bytes
are alternating XF/BP loads, no draws; both parsers
agree on every boundary until the tail. The seam
mechanism stays not-fully-convicted; the pragmatic
move is the bigger proven loss first: 63.5k nested
CALL_DLs dropped per run because CTTR's
GXCallDisplayList (0x8036A1C4, translated) writes raw
CALL_DL opcodes into the FIFO and Aurora never
follows them. Batch 58 binds 0x8036A1C4 to the
runtime's GX__CallDisplayList_80172f64 (the SPM
flattener/interpreter) -- retranslate + emit +
rebuild; verdict = CALL_DL count collapse.

BATCHES 58-62 VERDICTS (Nov 4, console-61..65):
Batch 58 bound 0x8036A1C4 -> GX__CallDisplayList_
80172f64; retranslate+emit+rebuild; behaviour
IDENTICAL (CALL_DL 63,558, all fifo-tagged).
Batch 59+61 witnesses (file output; runtime
stderr/RT_LOG-GX never reaches the console logs):
GX__CallDisplayList_80172f64 is NEVER ENTERED in a
35 s boot run -- by the override, by the pump, by
anyone. Batch 60+62: the pump IS fed (FifoStore
Entry -> HleFifoWrite fire; WriteBurst fires,
size=10) and its CALL_DL case never triggers;
discards stay under 20k.
CORRECTION OF THE LONG-STANDING READING: the
"806 CALL_DL per giant" are PHANTOMS. A raw scan
of buffer1 finds ZERO plausible CALL_DL packets
(0x40 + MEM1 addr + sane size) at any offset. The
giants are Aurora's API-serialized stream; both
Aurora's decoder and the offline walker desync at
the frame seam and land on 0x40 bytes inside
vertex data, manufacturing the flood. The real
defect is ONE phase slip per frame at the copy
seam: the last draw before the GXSetTexCopySrc/Dst
block is sized one byte differently by the stream
decoder than by the API writer (writer/decoder
VAT-state timing is the prime suspect; cf. the
NBT 60-vs-36-byte note in gx_fifo.cpp). Loss per
frame is small (the seam draw + the block's echo);
giants decode ~99.99% before the slip. Batch 58's
binding stays (correct; simply unexercised by the
boot/attract path in 35 s windows).
Diagnostics live in tree: batches 50,52-57,59-62
witnesses (log/file only) -- removable as a set.

BATCH 63 WRITE-RING VERDICT (console-66): the seam
"BP" is vertex data. Aurora's GX API serializes
draws component-by-component into the FIFO buffer
(len=1 and len=4 writes). The frame's last draw is
still missing its final byte (35) when drain()
runs; the copy block (4x write_u8(61)+write_u32,
Aurora's GXSetTexCopySrc/Dst serialization) lands
next; the 35 arrives with the next frame's writes.
Cause: TWO LANES. Guest FIFO stores are recorded
by the GX worker and replayed asynchronously;
native HLE calls (gx_copy's GXCopyTex/GXCopyDisp)
execute immediately on the guest thread. Guest
order [draw stores -> GXCopyTex] executes as
[GXCopyTex block -> last draw bytes]. Batch 64:
drain the GX worker queue at the top of the
gx_copy HLE entry points so recorded stores replay
before the copy serializes -- the same sync-point
pattern gx_init documents for GXBeginDisplayList.

BATCH 64 VERDICT (console-67): NO CHANGE (CALL_DL
63,559, subCmd 16, trunc 225, drops 1,304). The GX
worker drain at the copy HLE entry points did not
move the seam -- either those HLE functions are
not the block's lane for CTTR, or the lag is not
the worker queue. (64b repaired a build break my
one-line edit caused: a // comment ate a closing
brace in GX__SetDispCopyDst.) Batch 65: lane
witnesses in both GX__SetTexCopySrc (runtime,
witness file) and Aurora's GXSetTexCopySrc
(Aurora Log channel).

BATCH 65 DECODER TRACE (console-68): the giant's
parse is a perfectly regular state-upload sequence
to the very end -- repeating [BP,BP,XF(33),XF(29)]
groups (72-byte period); the buffer ends mid-BP
one byte before the next group. No interior
desync, no mis-sized draw (last draw len 2883 =
3+120x24 exactly). The stream is well-formed; the
cut is at the drain boundary and the BP's last
byte lands behind the copy block. Batch 64's
worker drain did not cure it, so the byte's lane
is still unproven; the BP was written as five
1-byte writes, a shape no Aurora RAS macro uses
(u8+u32) -- writer identification continues.

BATCH 66 WRITER VERDICT (console-69, return
addresses resolved via llvm-nm against the exe,
control GXSetDispCopySrc landing exact): the
giant's tail is VERTEX DATA. The byte-wise writer
is write_color_attr (GXVert.cpp) -- 61 00 3d 53 is
a vertex color, 35 the next component; the 4-byte
writer is write_numeric_component. The decoder
undercounts the final draw: it stops at 158,956
(120 verts x 24B) while the writer keeps emitting
vertex components ~270 more bytes. The "regular
BP/XF tail" was the decoder misparsing vertex
data (72-byte period = 3 verts x 24B). Seam =
writer/decoder vertex accounting mismatch on the
last draw, not an ordering/lane problem; batches
64's worker-drain theory is dead. Next: verify
against buffer1's last-draw header and the bytes
after it.

BATCH 67/67c: Aurora's GXBegin fires ONCE in the
whole boot (nVerts=0) and GXEnd never -- the GX
API vertex path is not the giants' producer. The
write_color_attr / write_numeric_component symbols
are anonymous-namespace, so they may belong to a
different TU than GXVert.cpp. Producer hunt moves
to finding every TU defining those helpers.

BATCH 68 CENSUS (console-74): the pump's packet
parser sees almost no draws -- 3 draw packets in
a full boot (2 raw-ok triangles, 1 zero-count quad
that is the lone GXBegin witness line). Guest
drawing does NOT flow through HleFifoWrite's
packet loop. Remaining lane: the HLE GX library
bindings in gx_vertex.cpp (guest GXBegin/GXPosition
are native overrides) and/or ApplyFifoPacketsDirect
bursts. Next: read gx_vertex.cpp's begin/vertex
impls and ApplyFifoPacketsDirect.

BATCH 69 HISTOGRAM (console-75): giant #2 is
100% vertex-component writes -- 34,285 numeric
(write_numeric_component) + 4x6,857 color bytes
(write_color_attr) = 6,857 vertices x 24B =
164,568 = the whole giant. The stream reaching
the decoder is a bare vertex stream. GXBegin
fired ~once per boot, so the draws' headers are
missing: the pump's GXBegin call is gated on
!recordOnly while its attribute writes are not
(suspect) -- during GX worker recording the
vertices serialize with no draw framing, and the
decoder parses them as commands (the entire
flood). Next: read the pump vertex loop's
recordOnly handling.

BATCH 70 (console-76): GXPosition3f32's caller is
HleFifoWrite itself (+0xd1a) -- the pump's vertex
loop IS the vertex producer (SubmitAttribute
inlined). So pump conversion runs at scale, but
its GXBegin gate (gx_fifo.cpp ~line 560) fires
~never. Remaining question: how inBegin gets set
for CTTR draws (guest GXBegin HLE binding?) and
why the gate's GXBegin call is skipped while the
vertex loop below it runs.

BATCH 72 FIX VERDICT (console-78): ROOT CAUSE OF
THE WHOLE FIFO FLOOD FOUND AND FIXED. Batch 71's
lifecycle witness proved the pump took exactly
one draw begin all boot -- a GX_QUADS packet with
vtxCount 0 -- and never completed it:
finishVertexIfNeeded only completes a draw from
inside the vertsRemaining > 0 decrement, so a
zero-count draw wedges inBegin forever. Every
later FIFO byte was eaten as vertex components of
the phantom draw; Aurora got a headerless vertex
stream and parsed it as commands -- the phantom
CALL_DL flood (63,559/run), subCmd=3510 garbage,
poison-guard drops, and the nearly empty scene
were all this one wedge. Batch 72: the pump
consumes a zero-count draw packet's header and
skips it (hardware draws nothing for it).
Console-78: CALL_DL 63,559 -> 0, subCmd=3510 -> 0,
stuck drops 1,304 -> 0, process truncations -> 0;
GXBegin/GXEnd witnesses both hit their 40 caps
(draws begin AND complete); frames presented
1,385 by 30 s (~46/s vs ~19/s wedged). Dominant
real draw: QUADS fmt0 count=65 rawSize=24, raw
path ok. NEW VISIBLE DEFECT (was masked): 698
"GX guest pointer: memory error" lines (0xA67C4000,
0x8000041, 0x38000041) -- indexed draws fetching
vertex arrays at unmapped guest addresses; CP
array base translation is the suspect. Next hunt.
Diagnostics batches 50-71 remain in-tree; cleanup
owed once the port is stable.

BATCH 81 FIX VERDICT (console-87): SECOND ROOT
CAUSE FOUND AND FIXED. The pump's FIFO buffer
(gx_internal.h fifoBytes) was a fixed 4096-byte
array, and pushBytes silently RESET it (dropping
all buffered bytes) on overflow. The raw draw
path needs the whole draw packet buffered before
submitting, so any draw over ~4 KB (the strap
screen's 270-330 vertex x 24 B draws = 6.5-8 KB)
filled the buffer, the next store wiped it, and
the parser resumed inside the draw's own vertex
data -- producing the garbage CALL_DL entries
(0xC0000000/255, 0x??000041/0xC0000000) and the
698 GX guest-pointer errors. Proven by offline
parse of a captured guest stream (batch 78):
20,839 packets, ZERO anomalies under SDK rules;
the guest stream was never corrupt. Fix: fifoBytes
4096 -> 4 MiB (covers the theoretical max draw
packet, 65535 verts x ~60 B). Console-87:
big draws buffer whole (7059 B) and submit ok;
guest-pointer errors 698 -> 0; garbage
GX__CallDisplayList entries gone; all Aurora
flood counters stay 0. NEW STATE: frames present
at only ~4/s (116 in 30 s) with everything
parsing clean -- the game now submits complete
frames and the bottleneck moved downstream
(Aurora decode/render throughput; subCmd discards
still appear Aurora-side at the 48-line cap).
Next campaign: frame-rate / Aurora-side stream.

## BATCHES 82-89 (Nov 4 late): WHITE SCREEN = ZEROED TEXTURES = THE BATCH-43 DRAIN STUB

Brandon's screenshot of the batch-81 build: a solid white rectangle -- the
strap screen's textured quads draw whole but sample blank. Batch 82 witness
(gx_texture.cpp -> cttr-witness.txt): GXInitTexObj/GXLoadTexObj for CTTR are
bound and ACCEPTED (zero placeholder binds); every texture's guest image
buffer checksums as zeros at init and at load. Batch 83 timeline sampler
(gx_copy.cpp, frame 90): the two strap buffers (0x00B43B40 320x240 RGBA8,
0x00B30EA0 320x240 I8 -- the I8 sum equals FNV-of-zeros for 76,800 exactly)
are STILL all-zero ~25 s in. Batch 84 MEM1 density scan: no image-like
region exists anywhere in MEM1; the texture heap (0xA00000-0xC00000) is
essentially empty. The image data NEVER ARRIVES.

Prime suspect identified by construction: batch 43 stubbed the game's
per-frame GODFileHandler drain fn_800A86A0 ("load-list finalize + registry
dispose") to a no-op -- queued file loads never finalize into their
destination buffers. Batch 85 un-stubbed it (batch-42 range guards
re-applied; they had been lost in a later re-translation; NOTE: toggling
the stub REQUIRES an emit-build-shards re-run, else duplicate-symbol link
error for func_800A86A0; emit needs RECOMP_CTTR_DOL set). Result: boot runs
8 frames, freezes at 9 presented, process alive, CPU ~8 s/35 s (blocked,
not spinning).

Batches 86-89 bracketed the hang with CttrGodWitness (native helper in
os_init.cpp; POST-TRANSLATE patchers like 41/42 -- re-apply after any
re-translate): the drain enters from LR 0x80070578, this=0x80942488,
returns cleanly for calls 1-8 (call 8 scans garbage, see below). Call 9:
D1 get-ms wrapper (fn_8024CC4C -> OSGetTime) returns; D2 fn_8023BA00 ->
fn_8023BE8C site 11 -> fn_8023BE3C -> fn_8024C9A0 -> OSLockMutex on the
fixed mutex at guest 0x804478D4 -- NEVER RETURNS. The watchdog dump in
console-97 confirms: current thread 0x80505D18 state 4 (waiting),
queue=0x804478D4.

Why the mutex is stuck: call 8's registry scan (190-entry table at
this+4136) walked GARBAGE entries (console-97 lines 361-779: ~34 unmapped
guest touches from pc=0x8024C8E4, lr=0x800A8824/8810 -- string-fragment
pointers). The range guard blocks out-of-range dispose targets, but
0x8024C8E4 is in range, so garbage disposes EXECUTED and corrupted sync
state. Open question: why the registry is garbage (registrations landing
on a different handler instance? ctor clear lost?). NEXT (batch 90):
un-stub the drain but skip ONLY the registry scan (jump loc_800A87C8 ->
epilogue loc_800A8854): the load-list finalize -- the part textures need --
runs, the garbage walker does not. Tree left SAFE Nov 4 late: stub
re-applied (batch-43 patcher), emit+build = copy110, console-98 verified
133 frames/30 s; all batch 82-89 instrumentation dormant in place.

## BATCH 90 VERDICT (Nov 4 late): SCAN-SKIP NOT ENOUGH -- THE DRAIN'S WHOLE ENVIRONMENT IS WRONG

Batch 90 (un-stub + goto epilogue at loc_800A87C8, skipping only the
registry scan): drain survived 10 calls (was 8), froze on call 11 --
inside fn_8024F278 -> fn_8024FA00 this time (run 97 froze in OSLockMutex
0x804478D4 via fn_8023BE3C/fn_8024C9A0; the site MIGRATES run to run).
Console-99 watchdog: only 5 guest threads listed (run 97 had 6) -- the
main thread 0x80505D18 is GONE from the OS thread list, scheduler idling.
So the corruption is not the scan alone: ~10 frames of finalize activity
progressively wreck guest threading/sync state, and the drain's handler
instance (this=0x80942488, sole caller fn_80070264+0x314) reads garbage
from the start (registry = recycled string fragments). Leading theory:
the drain runs on a handler instance whose construction/registration
state never matches the instance the game's loaders actually use
(cf. batch 43's dumps: a second handler with an EMPTY registry).
NEXT AVENUE: in the STUBBED build (game stable), poll both candidate
handler instances' registry tables + load lists across frames 30/90/300
and find which one the game actually registers into; then aim the drain
(or a native finalize) at the right object. Tree parked SAFE Nov 4 late:
stub re-applied, emit+build = copy112, console-100 verified 139/30 s.

## BATCHES 91-96 (Nov 4 late): THE DRAIN IS INNOCENT-ISH -- THE COMPLETION QUEUE IS EMPTY AND THE LOCK LAYER IS THE BATTLEFIELD

Batch 91 census (stubbed build, frame 90): exactly ONE GOD handler
vtable exists (0x803ABFE4, drain at slot 3) and exactly ONE instance
(0x80942488, the drain's this). Its registry array (0x809514D0) is
COMPLETELY EMPTY at frame 90. The two-instance theory is dead.

Batch 92/93 registry snapshots per drain call (entry + pre-scan):
registry empty at every entry. One apparent junk reading (call 8
pre-scan, nz=102) was an artifact: r31 (this) was 0 at that site, so
the snapshot read guest low memory as the "registry".

Batch 94 r31 trace (ctx->gpr[31] after every call site in the drain):
the get-ms wrapper (D1) leaves gpr[31]=1 after EVERY call (benign --
the drain never reloads r31 there). On the first "real work" call,
D3 (fn_8024F278 -> fn_8024FA00) returns with gpr[31]=0, and the drain
DOES reload r31 after D3 -- arriving at the scan with this=0, walking
exception-vector memory as the registry and disposing code addresses
(0x8024C8E4 et al.) into live structures. That fully explains the
batch-85/89 garbage scans and the migrating corruption.

Batch 95 (snapshot this at entry into a function-scope const; restore
r31 + ctx->gpr[31] after all 14 call sites): the scan corruption is
FIXED (call 8's w3 reads the true this again, calls 8 and 9 return
cleanly) -- but the run still freezes, now INSIDE D3/fn_8024FA00 on
the second work call (call 10, run 105; identical in run 106).

Batch 96 (brackets inside fn_8024FA00): fn_8024FA00 processes a
completion queue at manager+44 ([r13+10928] is the manager singleton):
fn_802501DC(queue) returns 0 == DONE/EMPTY (polarity proven from the
CR test at FA78); nonzero -> pop head via fn_80250224, call the
object's vtable[5] then vtable[3], repeat. In run 106 the check
returned 0 on EVERY drain call -- the completion queue is EMPTY
whenever the drain looks. Nothing is ever finalized because nothing
ever arrives, matching batch 84 (image data never lands in MEM1) and
every watchdog dump (the three GOD loader threads, entry 0x8024C55C,
sit in state 4 on their queues forever).

SHARPENED PROBLEM STATEMENT: the freeze and the empty textures are
two faces of one stall. Load requests never reach the loader threads'
queues (or completions never reach the manager+44 queue), so no data
moves; and when the main thread participates in GOD locking at all
(drain un-stubbed), it deadlocks within ~10 frames at whichever GOD
lock it touches next (BE3C mutex 0x804478D4, or inside fn_8024F758 --
first call inside fn_8024FA00 -- on the fatal call). Next avenues:
(a) trace the load REQUEST path -- who posts work to the loader
threads, and does a post ever happen (watch their queue heads /
OSSendMsg calls during boot); (b) trace fn_8024F758 (likely a lock or
state query on the manager) and the manager object's fields over the
first 12 frames; (c) examine whether the runtime's ARQ/DVD completion
callbacks (batch 36/38 fiber servicing) ever fire for GOD file reads.
All batch 91-96 instrumentation is dormant in place. Tree parked SAFE
Nov 4 late (stub on, console-107: 140 frames/30 s).

## BATCHES 97-99 (Nov 4 late): THE GOD WORLD IS FROZEN FROM FRAME ~10 -- THE STALL IS IN THE BOOT WINDOW

Change-detector (gx_copy sampler) over the handler region
(0x80940000+0x12000), SDA region (0x80440000+0x10000) and heap region
(0x80B80000+0x80000), sampled every 10 frames from frame 10 to 370 in
the stubbed build: the ONLY blocks that ever change are two counter/
table blocks (0x80940A00/B00) and two render-working blocks in the
heap (0x80B9E700, 0x80BDA900). The handler object, its registry, all
SDA globals, the loader threads' stacks (0x80BA8F00, 0x80B95700) --
frozen solid the entire run. Console-110: the only ARQ DMA of the
whole boot is one 0x800-byte AUDIO transfer; no file-data DMAs at
all. The "[dvd] read cache: 37 files / 891 MiB" line is a host-side
preload of the extracted dvd_root, not game-issued reads.
CONCLUSION: whatever the game was going to request for the strap
screen was decided before frame ~10 (during boot, before the first
presented frames) or is gated on a boot-time condition that never
completes and is never retried. Next avenue when resumed: boot-window
instrumentation -- log GOD/DVD file opens by name in the runtime's
DVD HLE layer during init, and a frame-1 full dump of the handler
object vs its frame-90 state. Tree remains SAFE (stub on) with the
batch 97-99 detector dormant in gx_copy.cpp (self-caps at 40 samples).

## BATCHES 100-101 (Nov 4 late): DVD GAP FOUND -- BUT THE FUNNEL IS NEVER REACHED; WORKERS WAIT ON A SEMAPHORE NOBODY SIGNALS

Discovery: of CTTR's entire DVD surface, ONLY DVDInit (0x8034D974)
was HLE-bound. DVDLowRead/DVDReadAsyncPrio/etc. run as translated
guest SDK code, and the runtime has NO DI register emulation
anywhere -- so a guest DVD read would wait forever for a DI
interrupt. Batch 100 bound CTTR's DVDLowRead (0x8034C4F0) to a
CTTR-safe copy of the SPM HLE read (same host-read + CopyToGuestAsDma
+ callback path, WITHOUT CompleteDvdCancelState, whose writes to
NSMBW globals 0x8050B690/0x8056DCxx would land in live CTTR heap).
Batch 101 traced it: ZERO calls in 45 s. The binding is correct and
worth keeping (anything that ever reaches DVDLowRead now completes),
but the game's read path never gets there. The apparent behavior
change in runs 111/112 (CPU, "slow frame (logo)" lines) was a
misread: the slow-frame spam is just the stage timer on the known
~4.5 fps pace; frame counts were unchanged.

The loader threads' shape (from generated code): entry trampoline
fn_8024C55C calls the fn ptr at [desc+8]; the worker body fn_8023A1EC
begins by calling fn_8024C93C, a tail-wrapper for OSWaitSemaphore
(0x8034A1B4) -- the workers park on a GOD "work available" semaphore.
Their processing calls no DVD SDK functions directly. The OS
semaphore trio (OSInitSemaphore 0x8034A15C, OSWaitSemaphore
0x8034A1B4, OSSignalSemaphore 0x8034A224) has NO HLE binding in the
runtime's OS layer -- all translated.
NEXT STEP when resumed: read fn_8023A1EC's wait call site (lines
~40-70) to identify the work-semaphore address, then witness
OSSignalSemaphore's generated body during boot: if that semaphore is
never signaled, the poster (game-side load requester) is dead before
posting; if it IS signaled and waits never return, the translated
semaphore/scheduler integration is the bug. Tree state: stub ON,
batch 100 binding live, batches 97-99 detector dormant. Stable
(103 frames/30 s, console-112/113).

## BATCH 102 (Nov 4 late): THE SEMAPHORE WORKS -- A HANDFUL OF BOOT JOBS RUN, THEN POSTING STOPS

Worker body fn_8023A1EC loops on OSWaitSemaphore(sem at loaderObj+1612),
then checks a flag byte at loaderObj+1608 and dequeues via fn_8023A9B8.
Batch 102 witnessed OSSignalSemaphore (w40) / OSWaitSemaphore (w41)
entries system-wide for a full run: 12 signals, 15 waits, ALL from the
GOD semaphore helper pair -- wait wrapper fn_8024C93C, signal wrapper
fn_8024C95C. Three loader objects (semaphores 0x80B95AF4, 0x80BA9254,
0x80450450; a fourth semaphore at 0x80B95B18 = first loader +1636 is
a second semaphore in the same object). Waits and signals interleave
sanely: workers wake, loop, re-wait. The semaphore/scheduler layer is
HEALTHY. A handful of jobs are posted and consumed during boot, then
posting stops entirely -- the strap/title requests are never enqueued.
NEXT STEP when resumed: find the callers of the post helper
fn_8024C95C across the generated tree (the load-request API), and
bracket the worker dequeue fn_8023A9B8 to identify what the ~12 boot
jobs actually were (their item contents). Tree state unchanged and
stable: drain stub ON, batch 100 DVDLowRead binding live (inert until
reached), all witnesses dormant.

## BATCH 103 (Nov 4 late): TWO BOOT JOBS, PURE IN-MEMORY STAGES, WAITING ON A FIELD THAT NEVER CHANGES

Post-helper entries (w42) all come from fn_8023A700 (the GOD enqueue
API, LR 0x8023A7C4) plus reposts signaled from fn_8023A9B8's area
(LR 0x8023A9A8, to the second semaphore of loader object 1).
Dequeued items (w43/w44): exactly TWO job objects ever circulate --
0x80B921D0 and 0x80B920B8. Each carries a vtable that gets swapped as
it advances (seen: 0x803E376C -> 0x803E3B3C, 0x803E3C3C), and the
worker invokes item->vtable[5] then vtable[3] per handoff. The
vtable[5] stage functions are all LEAF code with zero calls:
fn_8024A3F0, fn_80248730 (stage logic), fn_80248B8C (a getter:
return [[item+8]+12]). After ~10 handoffs both jobs stop being
reposted. No stage issues a read; the jobs are waiting on a field in
shared state that some other actor was supposed to update (the same
flavor of stall as everything else in this campaign: an expected
producer never produces). Callers of the post helper exist across
the 0x802B9xxx/0x802BAxxx asset layer (fn_802BA070 x4, fn_802BA664
x4, fn_802B9E7C x2) -- those are presumably the real load-request
sites, never exercised for strap/title.
NEXT STEP when resumed: read the two leaf stage functions
fn_8024A3F0 / fn_80248730 fully -- the exact field(s) they poll or
decrement are named in their bodies; then find who was supposed to
write that field. Tree stable, stub on, all witnesses dormant.

## BATCHES 104-105 (Nov 4 late): THE STALLED RESOURCE IS THE DISC IDENTITY OBJECT ("cnDVDDrive")

Batch 104 dumped the two boot jobs and their shared resource:
BOTH jobs point at ONE resource object X = 0x80B93A44. X contains
the formatted identity string "game:[] company:[] disc:[0]
version[0]" -- empty game (4 chars) and company (2 chars), disc 0,
version 0. X+180 (the state word the workers poll via fn_80239908)
= 1 (not ready); X+188 = back-pointer to loader object 1. On real
hardware the identity fields come from the GameCube disc header /
DiskID. Nothing in our runtime ever issues that read: DVDLowRead
(batch 100 binding) has still never been called, the manager queue
is empty, and batch 105 (drain un-stubbed again on top of the
batch-95 r31 fix) changed nothing -- drain calls 1-9 returned, call
10 hung inside the FA00 chain again (a separate drain-side hang;
the manager queue is NOT the identity path).
The identity format string ("\ncDVDDrive\ngame:[%.4s]
company:[%.2s] disc:[%d] version[%d]\n") lives at VA 0x803E2654
(DOL file off 0x3DF634, section 12); "cnDVDDrive" tag at
0x803E2647. Guest code builds such addresses as base+offset
(0x803E0000 + imm), so full-address greps miss references.
fn_8023F914 (size 0xDC, spans 0x8023F914-0x8023F9F0) is a
constructor in the cnDVDDrive cluster: writes table-derived
pointers (base 0x803E2A54) into a new object at +0/+4/+12/+188/+192
and calls fn_80241208. X's own first words (0x803E2838/284C/2858)
come from a nearby table (0x803E2838).
NEXT STEP when resumed: walk the cnDVDDrive constructor/init
cluster (fn_8023F914, fn_80241208, neighbors 0x8023F12C-0x8023FB14)
and find (a) X's constructor, (b) who was supposed to issue the
disc-header/DiskID read and set X+180 to its ready value, (c) what
guest call or HLE surface that read should have arrived through
(DVDLowReadDiskID 0x8034C848 and DVDReadDiskID 0x8034F828 are the
prime candidates -- neither has ever fired; their callers in the
cluster will show why). Tree state: drain UN-STUBBED after batch
105 (batch 90a) -- freeze-prone on drain call ~10; re-park with
patch-god-drain-stub.py + emit + build before any long run.

## BATCH 106 (Nov 4 late): DISKID PATH NEVER FIRES; X's CONSTRUCTOR ISN'T fn_8023F914

Entry traces (run 119, verified current exe): DVDLowReadDiskID
(w45) 0, DVDReadDiskID (w46) 0, fn_8034E788 (w47) 0, fn_80350778
(w49) 0, fn_8023F914 (w50) 0. Only fn_8034EC18 (w48) fired, once.
So the game never asks the SDK for the disc ID, and X is not built
by the constructor I guessed. X's vtable group at 0x803E2838
(DOL-verified triples {COL 0x804AAAD0, offset, fn}): primary
methods fn_80237778, fn_8023779C (shared base), fn_8023F6F4;
secondary fn_8023F67C; tertiary fn_8023F68C, fn_8023F684. Batch
97-99's detector showed X's heap block (0x80B93A00) already static
by frame 10: X is fully formed, state=1, before frame ~10 and
never touched again. (Run-119 build printed a ninja subcommand
failure AFTER the link; the exe is the batch-106 build -- proven
by w48 existing at all, impossible under the previous caps bound.)

## BATCHES 107-108 (Nov 4 late): ROOT CAUSE OF THE WHOLE STALL -- NO DI EMULATION UNDER THE TRANSLATED DVD STATE MACHINE

Batch 108 traced the public DVD surface for a full boot:
DVDReadAsyncPrio 0, DVDReadPrio 0, DVDReadAbsAsyncPrio 0, seeks 0,
__DVDPushWaitingQueue exactly 1, stateReady exactly 1,
stateCheckID 0. The single queued command in the entire boot is a
DVD INQUIRY (push caller LR 0x8034FA44 inside DVDInquiryAsync,
queue index 2) -- the cnDVDDrive's boot-time drive inquiry, i.e.
the command whose completion was supposed to fill identity object
X (0x80B93A44) and flip its state word at +180 from 1 to ready.
stateReady dispatched once into stateBusy with the current-block
SDA slot reading 0, and no DVDLow* issuer ever ran (DVDLowRead,
DVDLowReadDiskID, DVDLowInquiry all zero for the whole campaign).
CONCLUSION: CTTR uses the full translated GameCube DVD SDK state
machine (stateReady/stateBusy/stateCheckID/cbForStateBusy + the
waiting queues). That machine advances via DI (drive interface)
register pokes and completion interrupts. The runtime emulates
NEITHER (zero DI register handling anywhere in runtime/src or
aurora). The inquiry therefore never issues and never completes;
the drive identity never becomes ready; GOD's three loaders idle
with only their two housekeeping jobs ping-ponging; no read
command is ever even created; textures stay zero forever.
FIX DIRECTION (next campaign step): bypass the state machine --
HLE-bind the SDK command entry points to the runtime's existing
file-backed DVD implementation (the SPM dvd.cpp HLE family):
DVDInquiryAsync, DVDReadAsyncPrio, DVDReadPrio, DVDReadAbsAsyncPrio,
DVDSeek*, DVDReadDiskID, plus whatever GOD calls directly. The
batch-100 DVDLowRead_CTTR binding is the working template (it must
stay for any state-machine stragglers). This is a runtime-code
project in dvd.cpp + binding tables; coordinate with the rebrand
pass currently editing runtime/src (branding only) so the builds
do not interleave.


## Rebrand batch (Nov 4, 2026, late)

The runtime's product identity was rebranded from the Super Paper Mario
product it was adapted from to Crash Tag Team Racing, port by Eladerino
(script: tools/patch-cttr-rebrand.py, applied to the LOQ working tree;
builds cttr-build-rebrand through cttr-build-rebrand5). Splash
title/credit, settings bar title, product descriptor
(runtime/src/product/base_product.cpp), app name, Discord presence,
launcher setup text and disc validation (G9RE7D only; the SPM
other-region restart branch in game_folder.cpp was removed, as this is
a single-disc product), panic text, config help text, the generated
Config.toml template, and the updater's relaunch target now name CTTR.
The runtime/src edits are branding only, apart from that one branch
removal and the G9RE7D string fixes in dvd.cpp (config help and the
dvd_root error text). The user data directory moved from
MarioWiiSaveData to CTTRSaveData; the old folder was copied across and
the original kept. The exe icon is a neutral generated CTTR monogram
(runtime/assets/icon/cttr.ico) instead of the NSMBW icon.
Attribution correction: WiiCompiled is by patchzyy and contributors;
JosiahG authored the NewSuperPaperBros product/launcher layer this
tree adapts, and Aurora is by Luke Street. Verified against the built
exe: zero occurrences of "Super Paper Mario", "New Super Paper Bros",
"MarioWiiSaveData" or "R8PE01/R8PP01" (narrow and wide), and
mkw_runtime_config_tests passes. Known remainder: the SPM debug
tooling internals (SpmMapSweep, the "tippi" action key, debug
identifiers in settings_overlay.cpp) are untouched. The working tree
is free for the batch-100 DVD work.
