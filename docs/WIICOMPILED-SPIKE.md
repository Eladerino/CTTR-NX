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

## BATCH 109 (Nov 4 late): COMMAND-LEVEL DVD HLE -- THE STALL IS BROKEN

dvd.cpp now carries CTTR command issuers that bypass the DI-less
state machine: DVDReadAbsAsyncPrio (0x8034F5B0), DVDSeekAbsAsyncPrio
(0x8034F68C), DVDReadDiskID (0x8034F828), DVDInquiryAsync
(0x8034F9B8), DVDLowInquiry (0x8034CA04), DVDLowReadDiskID
(0x8034C848) -- block setup in CTTR SDK layout, synchronous reads
via ResolveAbsRead, state=END + transferredSize, guest callbacks
through QueueDvdCallback. DVDInit additionally invokes CTTR's
__DVDFSInit (0x8034CDC8); the runtime already published the FST
pointer at BootInfo+0x38 (0x80000038).
Run 121 (60 s): the boot inquiry completed (cb 0x80342C3C =
InquiryCallback), then real file reads flowed -- three GOD file
objects doing Seek+Read chunk streams at disc offsets 0x4BF5678,
0x2B55D428, 0x1ADB882C into staging buffer 0x80B93C60. Identity
object X now shows "game:[R8PE] company:[01] disc:[1]
version[0]" -- NOTE: CurrentDiscGameCode() returns MKWii's R8PE
for this build (product-identity plumbing bug, shared with the
rebrand work; the game accepted it and proceeded). Run 122
(180 s): 76 DVD ops total; frame time now dominated by GX
"worker wait" (57-171 ms) -- the bottleneck moved to callback
drain pacing / GX worker throughput. Batch 110 (next): drain the
pending-callback queue at the end of each CTTR command native so
chunk chains complete iteratively in one call.

## BATCH 110 + RUNS 122-123 (Nov 4 late): LOADING WORKS; FRAME TIME IS NOW PURE GUEST CPU

Batch 110 drains DvdProcessPendingCallbacks at the end of each
CTTR command native. Counting caveat: PowerShell Select-String
undercounts the witness file (findstr is right: run 122 = 76 DVD
ops in 180 s pre-110). Post-109 boots deterministically issue the
inquiry + GOD archive header/TOC streams for three files, then
load on demand. Frame profile in the logo stage is now ~260-320
ms of pure guest execution per frame (gx ~0.3 ms, worker wait 0,
guest idle 0) -- the game is computing, not waiting: next step is
main-thread PC sampling to find the hog (poll loop vs real work).
Still owed: (a) proof the strap textures now hold real pixels
(tex83 sampler recheck or eyes on the window), (b) the logo stage
never yet observed transitioning to title, (c) CurrentDiscGame
Code() returning R8PE -- product identity should be G9RE for
CTTR (coordinate with the rebrand pass), (d) diagnostics cleanup
of batches 50-110 witnesses once stable. Tree state: batch 109 +
110 LIVE (real fixes, keep), drain stub still ON (safe), all
other witnesses dormant.

## BATCHES 114-120 + RUNS 127-134 (Nov 5): BOOT FILES NAMED; IDENTITY FIXED; RETRACE STARVATION MEASURED

Batch 114 ([dvd114] read-path log in dvd.cpp): every boot read comes from
TWO archives -- files\adefault\default.rcf (64 B header; 4096 B chunks at
128/16512/32896/49280; 1856 B at 65664; a 64 B header at fileOff
132001356) and files\movies.rcf (64 B + 1088 B). The file layer is done;
strap textures are produced by the game's own extraction, demand-driven.
Batch 115 (system_bridge.cpp seed table) + batch 116 (DVDInit's header
rewrite made product-aware): the seed table AND DVDInit both hardcoded
SPM/MKWii identity ("R8PE", maker "01", disc 1). CTTR's real boot.bin is
"G9RE7D", maker "7D", disc 0, version 0. Run 128 VERIFIED: the identity
object now reads "game:[G9RE] company:[7D] disc:[0] version[0]".
Frame cost hunt: batch 117 host RIP sampler + batch 118 (gx_worker
witness) + batch 119 (vi.cpp retrace witness). Findings: the GX worker is
PERMANENTLY OFF in this product (GxWorker::RequestMode has no callers
outside tests, so all GX runs inline on the guest thread); VI display
lock is invalid at Brandon's 144 Hz (game keeps its own clock); retraces
advance ONLY from poll points, and run 133 measured 32 retraces taking
~7.2-7.6 s (~230 ms each) -- frames are retrace-paced, so the retrace
supply rate WAS the frame rate. Batch 111's alarm sampler had already
shown ProcessAlarmQueue runs < 8192 times in 75 s (the scheduler idle
loop is not spinning at its designed ~1 kHz). Batch 120 (idle-loop step
timing, os_scheduler.cpp): run 134 -- every idle step is fast (only two
"vi" steps >= 5 ms all run). The idle loop is not where the time goes.

## BATCHES 121-122 + RUNS 135-138 (Nov 5): THE FRAME COST WAS MY OWN DIAGNOSTIC

Run 135 used the runtime's built-in sampling profiler (NSMBW_PROFILE=
45:25, guest_profiler.cpp): 24,659 samples of the presenting thread --
98.7% inside ntdll. profile_stacks.txt + disassembly resolved the wait
to HleFifoWrite +0x4fd/+0x520/+0x530 = fopen/fputc/fclose: BATCH 78's
per-write FIFO stream capture (fopen + fwrite-per-byte + fclose on EVERY
HleFifoWrite call until 8 MiB). At tens of thousands of writes per frame
that is the entire ~230 ms frame; the starved retraces were a symptom.
Batch 121 removes the capture. Run 136: slow frames 154 -> 44 -> 21 ms,
retraces ~60 Hz -- then a NEW crash at the 90th GXCopyDisp: read at
0x2A2929B000C inside batch 104's job dump (unguarded double dereference
rd32(rd32(item+8)+12); the boot jobs recycle before frame 90 at speed).
Batch 122 guards it (+ batch 91's dumpInst range). Run 137: NO crash,
1,149 frames by 12 s, 3,309 by 30 s (~120 fps), retraces at 120 Hz,
scheduler idle healthy. Run 138 = 137 + batch 123.

## BATCHES 123-124 + RUNS 139-140 (Nov 5): CONTENT STILL WHITE; THE DRAIN WAKES AND DEADLOCKS

Runs 137/138 still render a SOLID WHITE frame (screenshot taken of the
live window): the strap TexObj source buffers checksum as uniform-zero
at GXInitTexObj, and after the boot census the game NEVER issues another
DVD read -- the payload reads that would fill the textures are never
asked for. Batch 123 bound CTTR's PAD surface to the existing pad.cpp
HLE (PADInit 0x803538A0, PADRead 0x803539F0, PADReset 0x8035367C,
PADRecalibrate 0x8035378C, PADControlMotor 0x80353CF0 -- all were
#if 0'd for NSMBW/SPM; CTTR's translated PADRead polls unemulated SI
registers). Run 138: no observable change (the gate is earlier than PAD).
Batch 124 removed the batch-43 GOD drain STUB override (os_init.cpp) --
batch 85's own note: "the stub froze the game's file-load finalization
and every texture buffer stayed zeroed." The stub was a shield against
the pre-batch-95 r31 clobber, and batches 85/90/105 retried the real
drain before the DVD HLE existed. Run 139: the drain now RUNS (10,451
god86 witness lines) for 173 frames, then FREEZES inside
fn_8024F278 -> fn_8024FA00 -> fn_8024FA94. FA94 is a GOD-library fiber
switch: when fn_8024F758's ring check (manager+24) first reports work,
FA94 calls fn_8024C870, which does OSDisableInterrupts +
OSSaveFPUContext + OSSaveContext(current) + OSLoadContext(target) --
a hand-rolled cooperative context switch into the manager's saved
context. That switch never comes back (main thread parked; loaders idle
on their semaphores; run 140 frozen live for host sampling). NEXT:
resolve the frozen host stacks (nm124) to learn whether the main thread
sits in the runtime's fiber manager (a scheduler-level block) or in
translated code (a guest-level lost wakeup), then fix accordingly --
likely candidates: OSSaveContext/OSLoadContext need the same HLE
treatment the batch-26 engine fiber switch got, or the manager's saved
context was never initialized because its initializer also routes
through a stubbed/unemulated path.
Tree state: batches 109, 110, 115, 116, 121, 122, 123, 124 LIVE (121 =
diagnostic removal; 122 = diagnostic guard; 123/124 = real direction,
124 currently freezes at frame ~173 -- the build on the LOQ right now
is the batch-124 build; restore os_init.cpp.bak-pre124 + emit + build
to return to the run-138 state).

## BATCHES 125-126 + RUNS 140-142 (Nov 5): THE "FREEZE" IS A FATAL POPUP; RING POPS ARE INNOCENT

Correction to the batch 124 entry above: runs 139/140 do NOT deadlock.
Host sampling of the frozen run 140 (sampler117) showed the guest main
thread parked in ShowRuntimeFatalPopup <- RuntimeCrash::
FatalMissingGuestTarget <- InvokeIndirectCpu <- fn_800A7B90+0x88: an
indirect call to target 0x0 with r3 = NULL, and the runtime's modal
fatal dialog is what "froze" the game (frames stop at 173-353,
varying). Console-140's own dump: TWO unmapped guest touches precede
the fatal -- reads at 0x64657371 ("desq") while comparing the path
"DVD:\design\startup..." inside the manager fiber, and at 0x4739529D
("G9R"+0x9D) inside fn_800A7B90. The runtime zero-fills those pages and
continues, so the fatal is downstream fallout.
Anatomy now fully mapped: the drain (fn_800A86A0) calls fn_8024F278 ->
fn_8024FA00; when fn_8024F758's ring check (manager+24, 8-byte entries)
first reports work, FA00 calls fn_8024FA94 -> fn_8024C870 = the batch-26
HLE GameFiberSwitch_CTTR (os_context.cpp), which models the GOD
library's cooperative fibers as host fibers. Switch-ins go through the
trampoline fn_8024C8E4 (OSEnableInterrupts; C6C0() -> current block;
call block[0](block[1])). Batch 125's witness (os_context.cpp) shows
the switch ping-pong is healthy: cur 0x8044E718 <-> fiber block
0x80450058, job fn=0x8024F8E0 arg=0x809434D8 every entry, only ~3 fiber
visits before the crash. fn_8024F8E0 is a thunk to fn_8024F5A0, the
completion dispatcher. Batch 126's ring-pop witness (func_8024F5A0.cpp,
post-translate; caps w59-61 in os_init.cpp) proves the pops innocent:
exactly TWO pops all run, same sane item 0x807120C0 (vtable 0x803E3FDC,
type word [item+20] = 1, [item+8] = 0x6C3 then 0x16C0).
So the corruption is in the GOD FILE TABLE the dispatched item's method
walks (call chain fn_8021C4B8 -> fn_80238628 -> fn_8023BA20 -> compare
fn_80251894 / fn_8024E9EC) while opening "DVD:\design\startup...": an
entry field that should hold a pointer holds string bytes instead --
the shape of a table whose offset->pointer relocation pass never ran,
plausibly because the pass belongs to the very drain/fiber path that
was stubbed while the boot-time mount happened. NEXT: read
fn_8021C4B8's walk (base + stride + which field is the name pointer)
and find where the table is built/relocated.
Build/emit note (proven run 142): the build compiles generated/cttr/
build_shards, NOT generated/cttr/functions -- a post-translate edit to
a generated function needs emit-build-shards before the build or it
silently does not ship. Tree state: batches 125 (witness) + 126
(witness) LIVE on top of 124. Run 138 state = restore
os_init.cpp.bak-pre124 + emit + build.
Addendum (run 142 + code reads): the stack "code refs" in the runtime
dumps are a raw stack scan, not a true backchain -- several refs are
stale. fn_80238628 never calls the compare. The live chain runs through
fn_8024E9EC (0x68 bytes): a refcounted string-symbol release -- it
hashes [obj+640] (rotl 4) into a bucket inside the manager, reads the
bucket's {begin,end} at +136/+140, computes a string pointer by
arithmetic ((end + begin) - [handle+20]) and calls fn_80251750
(compare/remove), then decrements [obj+640]. Both crash reads are in
the game's string/symbol system, not the DVD/FST path: some symbol
entry's pointer field holds string bytes. NEXT (batch 127): entry
witness on fn_8024E9EC (obj, [obj+640], [obj+644]) + fn_80251750's
args, last-calls-before-crash, to identify the corrupt entry and its
producer.

## BATCHES 127-137 + RUNS 143-153 (Nov 5): THE FIBER DEATH IS A CLOBBERED REGISTER-RESTORE SLOT

The chain, all witnessed: dispatcher fn_8024F5A0 pops the stream item
(0x807120C0) a second time and calls fn_800A7B90(mgr, item+0x20, item)
(batch 128: exactly one call, from F5A0+0x128). 7B90 calls
fn_8023BA20 -> fn_8023BF3C(out, key=item+0x20) (batch 130: key found at
index 0 in the static table at 0x80447CEC, 284-byte records; the
record's object is X, the cnDVDDrive identity object; its vtable[16] =
fn_8023F6DC returns 0x26 fine, batch 133). BF3C then allocates the
360-byte wrapper (fn_8023AC38 returns 0x80B93600 OK, batch 132) and
calls the constructor fn_8023ACEC. Inside ACEC, the saved-r25 stack
slot ([frame+20], holding BF3C's out-pointer 0x80949EE4) is overwritten
with 0x80070578 -- the return address inside fn_80070264 for a call
into the GOD drain -- during the fn_8023A0AC call window (batch 136
slot watch: intact after prologue and after calls at sites 2-5,
poisoned after site 6 = fn_8023A0AC -> fn_8023A700, the job poster that
writes the loader queue and signals its semaphore via fn_8024C95C).
ACEC's epilogue restores the poisoned r25, BF3C writes the out value
(3-6) into the .text at 0x80070578 instead of 7B90's slot, 7B90 reads
its slot as 0 and calls [0]->vtable[22] -> FatalMissingGuestTarget.
Batch 129 (defer ReadAbs callbacks) and batch 137 (defer ALL DVD
callbacks to the scheduler poll) changed nothing: the poisoning is
not the batch-110 immediate drains. The run-153 watchdog dump shows
the main thread (0x8047DF30, stack 0x804C22xx) parked inside
drain -> F278 -> FA00 -> FA94 when the fatal fires, i.e. the drain and
the fiber interleave around the switch. Leading model: some guest
execution (drain chain from fn_80070264) runs with an SP that lands
its frame saves inside the fiber's live frames. Same bug CLASS as
batch 95 (fn_8024FA00's r31 leak), one level deeper.
NEXT (batch 138): batch-95-style protection for fn_8023ACEC -- stash
r25/r26 host-side at entry, rewrite the save slots just before the
epilogue restore leaf at loc_8023AE30 -- plus a drain-entry SP
witness (w74) in fn_800A86A0 to catch the concurrent executor's SP.

## BATCHES 138-150 + RUNS 154-166 (Nov 5): THE FIBER CRASH IS A CROSS-SWITCH-SYSTEM CONTEXT HIJACK; BATCH 150 FIXES IT

Batch 138/139 (batch-95-style protection of fn_8023ACEC, then widened
to r27-r31+LR+this): the out-write finally landed (run 154/155 witness
w71: wrapper 0x80B93600 written to the correct slot), yet 7B90 still
crashed at loc_800A7C04 reading [r1+36]=0. Batch 140/141 witnesses
(w74/w75) found why: after BF3C returns, ctx->gpr[1] is 0x804C2440 --
the MAIN thread's stack -- while 7B90's frame base is 0x80949EA8 (the
fiber stack) and its slot there holds the correct wrapper. w86/w87
(batch 145, readable only after batch 146) showed the whole register
set after BF3C is a stale OTHER context (r25 = a saved-SP slot value,
r26 = SP-8): the context object itself was swapped mid-call, not
clobbered register by register.

Root cause (established by direct reads of the runtime): there is ONE
global CpuContext (GetPersistentCpuContext, abi_bridge.cpp) shared by
every host thread and fiber. Two independent switch systems drive it
on the same host thread: the game's own cooperative fibers
(GameFiberSwitch_CTTR / fn_8024C870's replacement) and the OS-thread
scheduler (GuestFiberManager::SwitchToThread from SelectThread). The
main game block's host handle IS the GOD OS thread's scheduler fiber.
Inside the dispatcher's BF3C -> ACEC -> A0AC -> A700 chain, A700's
semaphore signal (fn_8024C95C -> OSSignalSemaphore HLE) wakes loader
thread 0x80B957D8; the reschedule runs SelectThread ->
SwitchToThread FROM INSIDE the fiber's execution; the composed
round-trip restores snapshots over the shared context: a parked
GameFiberSwitch frame resumes mid-window with the fiber's SP (drain
frames land on the fiber stack, poisoning ACEC's saved-r25 slot with
drain LR 0x80070578), and 7B90 finally resumes with the main thread's
context. Batch 142's switch witness saw the orphan resume (a
GameFiberSwitch exit pair with no matching entry).

Batch 144 (gate foreign-thread ARQ delivery once the game fiber is
claimed) REGRESSED the boot (run 160: 2 frames, DVD census collapsed
to the 1 Inquiry): foreign-thread ARQ completion delivery is
load-bearing for boot progress. Fully reverted.

Batch 146 (FIX, diagnostics): batch 143's caps-widen edit had inserted
a `//` comment before the first nine values of the s_caps initializer
in os_init.cpp, so the compiler swallowed s_caps[0..8] and every cap
since batch 143 was shifted by -9 (w79/w84-w87 silently dead). Batch
146 restored the line. Any future caps edit must parse the initializer
semantically, not by eye.

Batch 147 (OSLoadContext snapshot/restore) was ineffective: run 163's
console proved OS__LoadContext fires exactly once per boot (the fiber
materialization). Kept in tree, harmless; decide in cleanup.

Batch 148 (gate SwitchToThread while a non-home game fiber is
resident) caught the fatal switch exactly once (w89: target
0x80B957D8, caller SP on the fiber stack) and the crash DIED (run
164) -- but the boot then idled at frame 349: SelectThreadSwitch had
already popped the loader, set it RUNNING and current before the
gate, so the deferred wake was never re-picked. Batch 149 (deliver
deferred switches at the GameFiberSwitch resume point) brought the
crash BACK (run 165): a foreign OS-thread round-trip inside the
fiber-switch tail still composes both systems over the shared
context.

Batch 150 (FIX, current build): the gate moved to the very top of
SelectThread_801a9c08, before any queue/mask/state access, keyed on
CttrInDispatcherFiber() (resident block non-home AND its job fn ==
0x8024F8E0, the completion dispatcher specifically -- loader fibers
are also non-home blocks and must NOT be gated). When gated it
returns the function's designed no-switch result (gpr[3]=0); the
woken thread stays QUEUED and a later SelectThread with the home
block resident picks it up via the normal path. Batch 149's delivery
block removed (its statics are dead code, cleanup owed); batch 148's
SwitchToThread backstop narrowed to the same predicate.

Run 166 (batch 150): NO fatal, no "not translated" anywhere. w91
fired once: caller SP 0x80949CC0 (dispatcher fiber), LR
OSSignalSemaphore+0x38 -- the gate catches the reschedule from inside
the signal itself. Frames 1,191 @12s, 3,348 @30s, still climbing
minutes later (every run 139-165 froze at ~frame 346). The guest
profile shows a real loop (top: fn_8008C44C+0x1C draw submit). THE
GOD FIBER CRASH THAT BLOCKED THE CAMPAIGN SINCE BATCH 124 IS FIXED.

## RUNS 166-168 (Nov 5): STABLE AT FULL RATE, PICTURE STILL WHITE; PAD IS NOT THE GATE

Run 166 screenshots: 1536x864, 3 unique colors (white 83.4%, black
16.5%, gray 0.1%) -- byte-identical to the run-137 shot. DVD census
unchanged (15 ops: Inquiry x1, SeekAbs x5, ReadAbs x9; only
default.rcf/movies.rcf header+index reads, biggest 4,096 B, no
payload reads ever). Both loaders idle in OSWaitSemaphore; the two
batch-103 job objects (0x80B921D0, 0x80B920B8) rest in their saved
contexts. Host input experiments (SendKeys Enter/Space, center
click) changed nothing; F10 proves the host window/overlay path
works but "Gamepad: (none)" and the keyboard checkbox was off.

Run 167 (NSMBW_PROFILE=15:20): 20,000 samples, 94.6% in ntdll waits.
The dominant chain (91.1%) bottoms in fn_80296EE0+0x130 -- float math
(matrix work via fn_80298714), i.e. the "wait" is presentation pacing
(Aurora dequeue hitches of ~110 ms recur in the console), not a game
wait. fn_801DB25C (the profiler's outer label) is a GX/VI display
setup function -- read in full; the label is the profiler's
SPM-shaped scan misattributing. The [vi] "(logo)" tag is likewise
meaningless for CTTR: vi.cpp:618 kSeqNames is SPM's sequence table
fed by SPM's global (constant/garbage in CTTR).

Batch 151 + run 168 (PAD witness + env-gated pulse): PAD__Read_HLE
IS polled ~61x/s. Port 0 reports preErr=-1 (PAD_ERR_NO_CONTROLLER)
and preBtn=0 on every call -- no SDL gamepad on the LOQ and
InputBindings::Apply contributes nothing. With CTTR_PAD_PULSE=1 the
HLE delivered A (err forced 0) for t in [8s,14s) and Start for
[16s,22s): shot168.png is BYTE-IDENTICAL to shot166 (md5
ec9369c83af7...). PAD input on port 0 is NOT the gate. Config.toml
holds no PAD section at all.

OPEN: the game loops its frame code forever drawing the same white
frame; no new GOD jobs are posted after the boot phase; no payload
data is ever read from the archives whose indexes were scanned.
NEXT: mine run 167's profile_stacks.txt raw stacks for the per-frame
execution mix (fn_80318348 took 1.6% -- the hottest real function),
and identify what the frame loop waits on / who should post the next
job after the identity+index phase.


## White-screen stage 2: DVD extent units (batch 154) + deferred-reschedule starvation (batch 155)

Run 169/170 (batch 152 memsnap + batch 153 name witness): all three cement
archives ARE mounted in order (fn_8023C330 -> fn_8023BB18 normalize ->
fn_802369EC -> fn_8023ACEC ctor): default.rcf obj 0x80B938D0, movies.rcf
0x80B93768, common.rcf 0x80B93600, owner disc object 0x80B93A44. Batch 153
also deleted batch 113's [prof113] FIFO histogram (witness 353k -> 22k
lines/run).

ROOT CAUSE #2 (run 170 analysis): the runtime's published DVD extents are
inflated 4x. CTTR's real FST stores byte offsets (guest FST at 0x97DC0000
parses clean: default.rcf loc 0x04BF5678 len 352,902,100; common.rcf loc
0x1ADB882C len 589,079; movies.rcf loc 0x2B55D428). dvd.cpp's FST parse
computes startBytes = fileOffset x4; BuildAndPublishRuntimeFst stores
discOffsetWords = start/4 (guest-visible FST correct) but builds
g_publishedExtents with startBytes = discOffsetWords x4 -- inflated.
default.rcf's extent [318,593,504, 671,495,604) swallows common.rcf's true
offset 450,594,860, so common's header read resolved into default.rcf at
fileOffset 132,001,356 (exactly the observed wrong read). Cement magic
failed, the common archive object was released (its memory reused by the
startup.god wrapper -- the "only two archives" misread), startup.god
unresolvable, white screen. Batch 154 (patch-dvd-extent-units.py, one line:
published extents in guest byte-offset units) -- run 171 confirms: TOC
pages now at correct offsets, common.rcf 64@0 + 832@32 (full TOC),
startup.god wrapper constructed at 0x80B93498 and dispatched. But NO
payload read followed. [dvd100] count 0 in all runs: the GOD stream path
never calls DVDLowRead_CTTR; all reads are batch-109 command-level.

ROOT CAUSE #3a (run 173 census + run 172 snapshots): A700 posts 28, w40
signals 28, w43 dequeues only 27, w91 gate exactly 1. The dispatcher popped
the startup.god stream item; fn_8023ACEC's tail posted the wrapper's load
job; the post's semaphore signal hit batch 150's dispatcher-fiber gate;
the dispatcher finished cleanly -- and the 28th job was never dequeued.
Snapshot proof: loader 0x80B957D8 READY in the run queue, pendingFlag
0x804AEA78 = 0x20000000 (prio-2 bit), reschedCounter 0x804AEA7C = 1,
identical at t=25 and t=40. Batch 150's gate defers correctly, but CTTR's
steady state has NO later scheduler entry on a live context:
RunDeferredReschedule's only caller is ProcessAlarmQueue's tail after a
handled completion (none occur), and the per-frame pumps use deferred
private-context variants that suppress SelectThread. Batch 155
(patch-deferred-reschedule-flush.py): CttrFlushDeferredReschedule() in
os_alarm.cpp (no-op under DetClock or hint==0) called at the end of
GX__CopyDisp after VI_HLE_PresentFrame (once per presented frame, live
guest context, home block resident); s_caps extended to exactly 96
(idx95=120 feeds the w95 witness). Run 174: w95 fired 3x, posts ==
dequeues 33/33, pops 3, common.rcf PAYLOAD reads landed (startup.god
fileOff 6144 len 30464; controllers.god fileOff 36864 len 19424). Screen
still byte-identical white -- blocker moved downstream again.

## White-screen stage 3: the paused boot ScriptPlayer (batches 156-162)

Run 175 (batch 156: memsnap retimed to 30/90/180s): memB->memC diff = the
whole GOD/script/scheduler complex frozen; only timers churn. Scheduler
clean (no pending) -- the stall is ABOVE the job machinery. The StartUp
master script is Lua (source resident ~0x80718000): language check ->
MemoryCardManager LoadIconAsync + wait -> LoadObjects of the permanent
.god files -> main loop. Batch 157 (icon witnesses on fn_80187904 /
fn_80187978, ids w1-w5; also added CttrPairWitness to os_init.cpp): run 176
-- ZERO hits. LoadIconAsync/IsIconLoaded are never called; the script
never reaches its first wait. (Side note: the runtime has ZERO CARD
bindings; all ~80 CARD SDK functions run translated against unemulated
EXI registers. Not the current blocker.)

Batch 158 (ScriptPlayer lifecycle witnesses w6-w12): run 177 -- two pooled
players cycle SetScript->PlaySync->SetScript(NULL) via fn_8019134C (the
LoadSet-completion driver) around each load completion. The BOOT player
0x80C0CE58 (script obj 0x80C04528, class ScriptManagerGameFlowClient):
SetScript + PlayAsync exactly once from fn_8018BB98 (main's boot fn),
then Pause exactly once from fn_80191AF4 -- and never resumes. Resume
(fn_80193D30) has zero direct callers. ScriptPlayer state [player+16]:
0 stop, 1 pause, 2 async, 3 sync. ScriptManager::Update (fn_801923CC)
ticks with gate byte [mgr+46]==1 but ScriptPlayer::Update (fn_80193D3C)
only runs state==2 players.

Batch 159 EXPERIMENT (Pause writes state 2 instead of 1): run 178 CRASHED
-- guest jump to 0x3A4C6F61 (":Loa") via fn_80243BF4 (script-native
dispatch on an unpopulated table). The pause is load-bearing: the script
must not run before its world exists. Batch 159 reverted in full.

Batch 160 (runner + handler witnesses w13-w16): run 179 -- the runner
fn_8019342C entered the boot script EXACTLY ONCE (LR 0x80193D8C, from
ScriptPlayer::Update): segment 1 ran and called LoadObjects (native
fn_80191A78, sig "void f(const char* pFileName, const char* loadSetName,
const char* pCategory)") via fn_80191ACC (LoadObjectsUsing chain) ->
fn_80191AF4, which builds a WAITER RECORD (class 0x803CCEFC: flag byte
+4 = 1, player at +8, loadset name at +12 = "Controllers"), stores it at
[fileObj+140] (fileObj = the controllers.god GOD file object, class
0x803ABFA8, name embedded at +16), starts the load via fn_800A8BA4, and
Pauses the active player. LoadObjects semantics = "block the calling
script until the named LoadSet completes."

The resume method is fn_80191F54 (record vtable +8): flag==1 path resumes
([player+16] = 2) when [fileObj+8]==1, clears [fileObj+140], calls
fn_80192044 (record release). Batch 161 (w17/w18/w19 + CttrPairWitness
caps 16->24): run 180 -- fn_80191F54 NEVER called (w17=0), fn_80192044
never called, fn_800A8BA4 fired x2 (boot flow + AF4). Snapshots showed
every precondition satisfied: [fileObj+8]==1, [fileObj+140]==record,
record intact. The caller is fn_800A86A0's registry rescan: fn_800A8CC8
(file-state setter) registers waiter-bearing files into the handler's
190-slot registry array ([handler+4136] -> 0x809514D0) on every state
call (2 at initiation from fn_800A8BA4, 1 at completion from the drain,
3 from fn_800A8C84); the rescan drains entries and calls
[[waiter]+8](waiter, fileObj), then Releases the entry. Registration
self-heals (the state=1 call re-registers), so an early drain is harmless.

ROOT CAUSE #3b: batch 90's `goto loc_800A8854` in fn_800A86A0.cpp ("skip
the registry scan (garbage entries)") -- a crash-campaign workaround from
the shared-CpuContext corruption era -- amputated the rescan, so no waiter
was ever notified after batch 150 fixed the underlying corruption.

Batch 162 (FIX, patch-restore-registry-scan.py): removed the batch-90
skip (scan's indirect calls are batch-42 range-guarded, batch-95
r31-protected) + w20 witness on fn_800A8CC8. Run 181 VERIFIED: w20 shows
state flow 2 -> 1 for both the inner object 0x80951420 and fileObj
0x80951388 (completion calls from fn_800A86A0, LR 0x800A86FC);
fn_80191F54 fired x2 from the rescan (LR 0x800A8810) -- first a no-op
(state still 2), second the resume: fn_80192044 fired (LR 0x80191FE0),
the boot script ran segment 2, paused again for its NEXT LoadObjects,
and the boot advanced to requesting 'DVD:\art/fmv/vug.bik' (the VUG
intro FMV). GOD dequeues went 33 -> 3000+ (cap). No fatals in
console-181.log. THE WHITE-SCREEN STALL IS BROKEN; the boot chain now
walks the StartUp script's load sequence like real hardware.

## White-screen stage 4: the FMV probe and the FST unit trap (batch 163)

Run 182 (batch 162 build, 240 s soak): the StartUp script resumed,
ran segment 2, requested 'DVD:\art\fmv\vug.bik' (the VUG intro movie),
and paused from a NEW site (LR 0x800B9E54, inside fn_800B9E20 -- a
"find the active player via fn_800BA4C0 and pause it" helper called by
fn_800B9C18). The FMV never started: the main thread looped
SeekAbs(0x04BF5678) + ReadAbs(64 -> stack) 29,366 times. The read
offset (visible only in console-182.log's deduped [dvd] ERROR) was
0x4442BC28, length 64, "absolute DVD read offset is not mapped to a
host file". 0x4442BC28 = movies.rcf base 0x2B55D428 + 0x18ECE800, and
the host movies.rcf at +0x18ECE800 holds a real "BIKi" Bink header --
the guest's FMV offset math (via movies.rcf's Cement TOC, which maps
art\fmv\*.bik names) was exactly right; the runtime resolver failed.
Note: vug.bik is NOT a loose FST file -- the real fst.bin (42 entries,
almost all .rcf) has no fmv entries at all; the movies live inside
movies.rcf.

ROOT CAUSE #4: dvd.cpp's ParseDvdFst multiplied the real FST's byte
offsets by 4 (SPM-era word assumption) into FstFileEntry.start/end, and
BuildAndPublishRuntimeFst divided by 4 when publishing -- the pair
cancelled for the guest FST but poisoned everything else:
  * Entries whose inflated start exceeded 32 bits (every real file
    past 1 GB: onfoot*.rcf, solar*.rcf) were silently dropped from
    g_fstFiles and later treated as runtime-added files.
  * nextFreeBytes for synthetic extents was seeded from the inflated
    fstFile.end (max ~= 0xC4247D30), so the first synthetic extent
    landed at discOffsetWords ~= 0x31091F4C -- inside movies.rcf's
    true span [0x2B55D428, 0x4622D438). FindPublishedExtentForByteOffset
    uses upper_bound, so any read past 0x31091F4C inside movies.rcf
    selected the synthetic extent, failed containment, and reported
    unmapped. (Header/TOC reads at movies+0/+32 sit below the poison
    point, which is why mounts kept working.)

Batch 163 (patch-fst-unit-units.py): byte units end to end in dvd.cpp
-- FST parse stores fileOffset unscaled; publish mapping stores
fstFile.start unscaled (guest FST values unchanged); synthetic seeding
uses discOffsetWords + size (no *4); synthetic assignment stores
nextFreeBytes unscaled with the range check on bytes. Synthetic files
now park past the real disc end (0x57057EE4, 32-aligned), and the
dropped >1 GB files get their real mappings back. dvd.cpp only;
backups .bak-pre154 (extent fix) and .bak-pre163.

Run 183 VERIFIED (build copy167, ~176 s): the FMV probe resolves --
[dvd114] movies.rcf fileOff=418179072 (0x18ECE800) len=64, header
reads at +32, then sequential 16,384-byte streaming reads marching
through the movie (418,180,768 -> 418,557,600+ and counting at stop).
dvd109 total collapsed 58,755 -> 57 (retry loop gone); zero DVD read
ERRORs in console-183.log (its 8 "unmapped" hits are scheduler stack
annotations, not read failures); witness 19,556 lines vs run 182's
100,906. The Bink movie streams; the script stays paused for playback
(the fn_800B9E20 pause is the movie wait).

Run 184 (batch 163 build, 300 s soak): the intro sequence advances
like real hardware. The VUG movie finished, the boot script ran
segment 3 (runner hits for 0x80C04528: 3), paused a third time
(w12 = 3, LR 0x800B9E54 -- the movie wait), and the game requested
'DVD:\art\fmv\radical_intro_splash.bik' -- the second intro movie --
whose Bink data streamed from movies.rcf at its own TOC offset
([dvd114] tail at fileOff ~410,095,072+, 16 KB chunks). dvd114 total
265, dvd109 total 286, zero DVD read errors, zero fatals, process
alive at 300 s (CPU 22.2 s). The screenshot route failed a third time
(no snap184.log at all): the snap task's working directory is not the
tree root, so the relative -File path never resolved; from run 185
the snap .bat cds to the tree root and passes an ABSOLUTE -File path.

Run 185 (batch 163 build, 480 s soak): FATAL during vug.bik
playback -- non-deterministic (run 184 played vug through and into
the second movie; run 185 died inside vug at t <= ~400 s).
InvokeIndirectCpu target 0, caller LR 0x802D85B0 = GotoFrame +0xF0,
via BinkNextFrame +0x190; active game target fn_800B9558 (movie
glue). GotoFrame (0x802D84C0) decoded: when [handle+264] != 0 it
calls the function pointer at [handle+276] -- the BINKIO struct at
handle+272, slot +4 (r3 = handle+272, r4 = frame, r5/r7 = frame
offset/size from the table at [handle+268]) -- and that pointer was
0. CTTR streams movies from inside movies.rcf, so the IO callbacks
are game-supplied, not Bink's DVD file IO. Batch 164 (diagnostic,
patch-bink-witness.py): CttrBinkWitness in os_init.cpp -- w1 on
BinkNextFrame entry (prints only when io slot +4 == 0), w2 on
GotoFrame entry (always), dumping [handle+264/+268/+272/+276].
Also: the screenshot route was fixed in run 185 (the snap .bat now
cds to the tree root and passes an absolute -File path) -- shot185
captured the fatal-error dialog itself, which is how the crash was
first spotted (window title "WiiCompiled - Fatal Error", CPU flat).
Pre-existing noise, not the crash cause: tens of thousands of
"[memory] WARNING unmapped guest touch" demand-commit lines in
every long run (garbage-address writes the memory layer papers
over), including Bink "Ready" writes ascending 0x77A10000+.

Run 186 (batch 164 build, ~420 s): FATAL again, but at a DIFFERENT
site -- fn_802D5488 (a C++ virtual dispatcher in the Bink-adjacent
cluster) calling [[obj]+28] == 0, LR 0x802D5594, reached from the
game's movie glue fn_800B9558 via thunks fn_802D68B0 -> fn_802D5784
on the 500 ms timer chain (fn_80070264). Batch 164's witness
acquits the Bink IO: the only GotoFrame of the run was BinkOpen's
priming call, with io0=0x802D432C / io4=0x802D47AC valid and
[handle+264]=0; no BinkNextFrame entry ever saw io4==0. So the two
crashes (run 185's GotoFrame blrl, run 186's vtable bctrl) are one
wandering symptom: some object the movie path dispatches on has
zeroed function slots, timing-dependent. Batch 165 (diagnostic,
patch-obj-witness.py): CttrObjWitness at fn_802D5488 entry --
resolves obj=[cell], vt=[obj], dumps [vt-4] (RTTI) and [vt+0..28]
to identify the sick class and whether the vtable is partially
zero or the object recycled.

Run 187 (batch 165 build, 420 s): SURVIVED -- no crash; boot
progress matched run 184 exactly (vug done, segment 3, splash
streaming, [dvd114] 265). But the [o165] witness saturated: all
3,000 capped lines are one static data object (obj=0x803F26B8,
vt=0x804AD0D0 -- a function-table struct in the Bink-adjacent C++
cluster; DOL bytes confirm [obj]=vtable, [obj+8..] = 0x802Dxxxx
function pointers) on a per-frame dispatch path, so the cap died
long before the movie window and the crash instance was never
sampled. Batch 166 (patch-obj-witness-filter.py, os_init.cpp only):
CttrObjWitness now skips that singleton while it is healthy (all
method slots nonzero) and logs everything else.

Run 188 (batch 166 build, 660 s): SURVIVED again, and the reads
were still advancing at stop ([dvd114] 265, last at line 29,786 of
29,800) -- the splash movie plays at a trickle (16 KB demand-paced
reads) and 660 s does not finish it. Two new facts: (1) GotoFrame
fired 381 times in the tail window -- Bink is frame-skipping
constantly, i.e. playback thinks it is perpetually behind (pacing
suspect: VI runs at the 144 Hz monitor's rate, 2 retraces per
frame = 72 Hz against the game's 60 Hz assumptions, or guest time
otherwise skewed). (2) The filtered [o165] still saturated, because
the singleton's descriptor (0x804AD0D0) LEGITIMATELY contains null
slots (m3/m5) -- my anyZero filter never filtered. But it proved
the healthy movie dispatch: cell 0x80C0D1A8 -> static obj
0x803F26B8 -> descriptor 0x804AD0D0 with slot +28 = 0x803F27A8
(DOL-initial value), LR 0x802D57A0 (thunk fn_802D5784). Batch 167
(diagnostic, pad.cpp): CTTR_PAD_SKIP -- Start held 1.5 s every 15 s
from t=100 s, to skip the FMVs like a player would and reach the
frontend this session.

Run 189 (batch 167 build, CTTR_PAD_SKIP=1, ~420 s): SURVIVED, but
the skip pulses left NO trace -- the witness holds only the three
initial [pad151] stage-0 lines, no stage-7 edge ever printed, and
the boot state at stop was identical to runs 184/187/188 (vug done,
splash streaming, [dvd114] 265 ending at fileOff 410,176,992). So
either CTTR_PAD_SKIP never reached the process or stage 7 never
engaged despite polling. Run 190 is the isolation run: one bat with
CTTR_PAD_PULSE=1 (batch 151's known-printing one-shot pulse) +
CTTR_MEMSNAP=1 ([snap152] prints prove env delivery AND that
PAD__Read_HLE still polls at t=30/90/180) + CTTR_PAD_SKIP=1.

Run 190 (isolation run): TWO findings. (1) PAD: [pad151] shows
exactly 3 calls, all at t=0.0, and [snap152] never fired despite
CTTR_MEMSNAP=1 in the verified bat -- PAD__Read_HLE is entered a
handful of times at boot and never again in the current build, so
the batch-167 skip plan has no input path during movies (in the
white-screen era the frontend-wait polled it ~61x/s, and memsnap
fired at 30/90/180 s through run 182; the poll died somewhere in
the batch 163+ era or the movie path simply never polls). The
skip-via-PAD plan is parked. (2) Run 190 CRASHED during vug with a
THIRD distinct signature: InvokeIndirectCpu target 0x80D9E040 (a
MEM2 heap data pointer in a function slot), caller LR 0x802DDA2C
in fn_802DD5F8 (Bink plane/copy code). That call loads its target
from the global at [0x804562BC] (0x80450000 + 25276) -- the slot
held a heap buffer address instead of code. Three crashes, three
different function-pointer slots (Bink IO +276, descriptor +28,
global 0x804562BC), all in the movie path, all "pointer field
holds zero or data": the movie-era pointer state is being
stomped or consumed inconsistently, timing-dependent (~50% of
long runs). AX's tolerance-ring HLE (which Bink's sound driver
registers callbacks into) is a standing suspect. Run 191: a
1,200 s soak with screenshots at ~600 s and ~1,150 s to see what
is actually presented and whether the boot reaches the frontend
in a lucky run.

Run 191 (batch-167 build, CTTR_COVER_LIFT=1 only, 1,200 s soak;
PID 26356, started 06:05:29 NST Nov 5): a FOURTH distinct outcome
at the same fragile point -- no crash, no frontend, a silent
stall. Orchestration note: the original snap/stop sequence died
in a runtime restart at ~t+185 s; the run itself was unharmed on
the LOQ and the sequence was re-armed (snap A taken manually at
~t+520 s, snap B at ~t+1,150 s, stop at ~t+1,210 s). Final CPU
1,123.5 s over ~1,210 s elapsed (~0.93 cores). console-191.log:
zero InvokeIndirectCpu/Fatal, zero DVD ERROR lines; its only
artifact is one early [runtime] stack dump whose backchain runs
through fn_8024F8E0 (the dispatcher thunk) into OSExitThread on
the fiber-block stack -- a guest thread exit, flagged as an
observation, not a conclusion. Witness preserved as
cttr-witness-191.txt (22,147 lines; the file stopped growing
early -- every witness that fires in the stall state is capped,
[o165] saturated at 3,000).

Witness timeline is identical to runs 182+ through the movie
wait: mounts, startup.god, controllers.god resume (w17 x2, w20
x4), 'DVD:\art\fmv\vug.bik' requested, BinkOpen's priming
GotoFrame (w2, line 18493, LR 0x802D92C8) with handle 0x80C0D480
io0=0x802D432C io4=0x802D47AC both healthy, the initial burst of
42 [dvd114] reads ending at movies.rcf fileOff=418557600 (the
same endpoint as runs 183/185), boot player paused by the movie
path (w12, line 19143, LR 0x800B9E54). Then exactly ONE real
BinkNextFrame -> GotoFrame (w2, line 19147, LR 0x802DA724 =
BinkNextFrame+0x190) with io pointers STILL healthy -- and Bink
is never called again. (Side note, corrected after reading the
batch-164 source again: w1 is a conditional tripwire by design
-- it logs only when io4==0 at BinkNextFrame entry -- so its
silence in runs 186-191 means io4 was never 0 at an entry, not
that the site is broken. BinkNextFrame entries are otherwise
visible only via w2's caller LR; batch 168 adds an always-log
entry witness so the calls can be counted directly.)

What is presented: shot191a.png and shot191b.png are
byte-identical (md5 91c0a376...), 1536x864, a single colour --
100% black (0,0,0). Not the white-screen era's white frame, not
movie content: in the stall state the game presents a solid
black frame, unchanged for at least the last ~630 s of the soak.

Where the CPU goes: sampler117 (150 rounds x 20 ms, 7,650
samples, ctxFail=0) found exactly ONE hot host thread (tid 3824,
150/150 samples inside WiiCompiled.exe); every other thread is
parked in ntdll waits. The hot thread's RIPs spread over 123
distinct sites -- a broad guest-loop free-run, not a tight spin.
An nm124 bisect (offsets drift vs the batch-167 exe, so treat
guest-fn names as neighbourhoods) puts repeated samples in the
OS HLE deferred-alarm path (OS_HLE_ProcessAlarmsDeferred, ~9
samples), scheduler list code (UnlinkGuestListNode, ~4) and
InvokeIndirectCpu, alongside translated guest code. So the main
thread keeps executing the frame loop and scheduler/alarm
machinery at full speed while the movie starves: the movie glue
stops driving Bink after the first frame call, the boot script
stays paused on the movie wait, and nothing paces or blocks the
loop the way healthy playback did (run 188: 21.7 s CPU over
660 s).

Movie-era tally, runs 183-191: played through 183, 184, 187,
188, 189; crashed 185, 186, 190 (three distinct stomped
function-pointer slots); stalled silent 191. Every failure sits
at the same point: immediately after vug's initial read burst
and the first BinkNextFrame. Batch 168 (next): witness the
movie glue fn_800B9558 (entry: inner object + state bytes
[inner+69]/[inner+73]/[inner+24]) and the BINKIO functions
fn_802D432C / fn_802D47AC across the burst boundary, plus an
always-log BinkNextFrame entry witness, to catch which side
stops first. Tooling note: scp over
the SSH route works and is now the preferred fetch for
screenshots/logs/witness files (exact bytes, no base64 chunking).

Run 192 (batch-168 build copy172, CTTR_COVER_LIFT=1, PID 11632,
1,200 s soak, stopped alive, CPU 1,200.3 s -- full-core free-run
again): THE BOOT GETS THROUGH THE MOVIES AND THE WHOLE STARTUP
SCRIPT. BinkNextFrame entered 773 times (new w23 always-log
witness; last at witness line 35833, exactly where frontend
loading begins), GotoFrame >= 600 (b164 w2 cap), BINKIO io4
>= 400 calls (w22 cap), io0 10 (w21) -- vug.bik AND
radical_intro_splash.bik both played to completion with no
crash and no stall at the fragile post-burst point. The batch
168 glue witness watched a quiet object (player 0x80BDAA08,
inner state bytes +69/+73 and word +24 never changed across
>= 500 calls), so the movie evidence came from w21-w23.

For the first time in any run, the memcard icon natives fired:
LoadIconAsync x2, IsIconLoaded x5 (batch 157's w1-w5) -- the
StartUp script's icon branch executed and its wait completed
without any CARD bindings (icons resolve through GOD loads).
The boot script ran 32 runner segments (w13 for 0x80C04528,
vs 1-3 in every earlier run) and the ENTIRE permanent-load
chain executed in order: art/frontend/loading.p3d, the sound
assets (crash.p3d, reverb/pause scripts, a shower of .rsd
files), opening.bnr + crash.ico, then permanent_objects,
collectible_states, onfootminigames, objectives,
genericobjectives, all six missionobjectives, four tutorial
objectives, niscommon, skins.god. [dvd114] = 499 reads
(movies 432, common 59, default 6, opening.bnr 1, crash.ico 1).

NEW STALL at the frontend threshold, fully characterized:
skins.god's final block read is common.rcf fileOff=577536
len=11552, but common.rcf is 589,079 bytes -- the request
overruns EOF by exactly 9 bytes. Verified on disk: the
skins.god script text ("BeginObject Skin CrashDefault ...")
starts at 577,536 and runs to the archive's last byte. The GOD
stream reader issues fixed-size block reads whose final block
is not clamped to the archive end; on hardware the drive just
transfers the count from the continuous disc image.
ResolveAbsRead already clamps readLength to the available
bytes, but DVDReadAbsAsyncPrio_CTTR treated any clamp as fatal
("requested range extends beyond the indexed DVD file",
console-192.log line 833, deduplicated) and completed -1, so
the loader retried the identical block forever -- the last
~29.5k witness lines are the SeekAbs(0x04BF5678) +
ReadAbs(11552 -> 0x80712320) pair. Presentation stayed solid
black at both snaps (md5-identical to run 191's black frames)
even while the game progressed: the video-out path produces no
visible output in this phase yet -- its own thread, separate
from boot progress.

Batch 169 (patch-dvd-eof-overrun.py; FIX): in
DVDReadAbsAsyncPrio_CTTR only (the proven live path), an
EOF-overrun read is served, not failed: available bytes copied,
slack zero-filled, completion reports the full requested
length, with a [dvd169] witness per overrun. The same latent
pattern in DVDLowRead_CTTR and the NSMBW-shaped HLEs is left
alone (never called by CTTR). Run 193 verifies: expect exactly
one [dvd169] line (fileOff=577536 req=11552 served=11543
zeroed=9), then the boot moving past skins.god -- english.rcf /
frontend loads are the next names to watch for.

Run 193 (batch-169 build copy173, CTTR_COVER_LIFT=1, PID 20264):
CRASH #4 in the movie family -- a new signature, and batch 169
was never exercised. The run died within ~a minute of launch
(crash artifact base_1793874230_pid20264 at 06:54:20, witness
mtime 06:54:05) and sat at the fatal dialog for the remaining
~19 minutes (both snaps byte-identical: the dialog over black;
final CPU only 22.75 s). Progress before death: vug played,
splash started (w23 BinkNextFrame = 408, [dvd114] = 265 -- the
same census as the old splash-trickle runs), names end at
radical_intro_splash.bik, [dvd169] = 0 (the boot never reached
skins.god this run, so the EOF fix is still unverified).

The crash: [runtime] Structured exception 0xC0000005 while
executing func_80005240 (the root frame); fault = host READ at
0x100100000000. Active translated target fn_802DFA40, called
from fn_802DD5F8+0x3AC, in the chain movie glue fn_800B9558 ->
fn_802D5488 dispatcher -> BinkCopyToBufferRect+0x3A4 ->
fn_802DD5F8 -> fn_802DFB74 -> fn_802DFA40. Just before the
fault, the memory layer logged unmapped guest touches from the
same target: reads at 0xF8F60268, 0xFF660058, 0xFF65FFF0
(demand-committed zero-fill), i.e. fn_802DFA40 was already
dereferencing garbage pointers before one went too far out to
paper over.

fn_802DFA40 read in full: it is a Bink YUV->RGB converter. At
entry it builds table bases in 0x803Fxxxx/0x8040xxxx static
space (conversion tables r26/r27/r28 = 0x80400100/0x803FFD00/
0x80400500, r29 = 0x803F6B40) and a plane struct pointer
r12 = 0x803FF8C0; its row loop reads THREE PLANE POINTERS from
that static struct -- [r12+8], [r12+16], [r12+20] -- and
dereferences them as byte sources. The garbage values it read
(0xFF660058 et al.) look like packed pixel bytes: the static
plane struct at 0x803FF8C0 had been overwritten with image-like
data (or filled from a torn stream), the same "movie-path
pointer state holds data" pattern as crashes 185/186/190, in a
fourth distinct field set.

Movie-era tally, runs 183-193: completed both movies 192
(then the EOF stall, fixed by 169); played through 183, 184,
187, 188, 189; crashed 185, 186, 190, 193 (four distinct
stomped pointer sets, all in Bink structures); silent stall
191. Batch 170 (next): a Bink-statics witness at fn_802DFA40
entry logging the 0x803FF8C0 plane pointers (+8/+16/+20) and
the run-190 global slot [0x804562BC] on any change or whenever
a field leaves its valid range -- to catch the first moment
the statics go bad and what the rest of the system was doing
at that moment.

Run 194 (batch-170 build copy174, CTTR_COVER_LIFT=1, PID
41684): CRASH #5 -- a repeat of run 190's signature, and the
run-193 "stall" reading is corrected: the stop stats' counters
missed the guest-fatal string, but shot194a shows the Fatal
Error dialog and the crash artifact (base_1793875624_pid41684,
~07:17:34, about 90 s after launch) confirms it. The game
stopped calling 0x80D9E040, Caller LR 0x802DDA2C =
fn_802DD5F8+0x434 -- the SAME stomped slot ([0x804562BC]) with
the SAME wrong value as run 190. The process then sat at the
dialog (final CPU 9.84 s). Witness (19,618 lines): the boot
phase is deterministic-identical to run 192 (SetScript 63,
PlaySync 31, dispatcher pops 3, BinkOpen priming GotoFrame
healthy), the burst reads end at the usual 418,557,600, the
boot player pauses for the movie, the movie glue fn_800B9558
is called exactly once, the dispatcher fn_802D5488 dispatches
once with a fully healthy descriptor (m7 = 0x803F27A8, the
DOL value) -- and the witness ends: the crash is inside that
first movie-frame copy pass. [pl170] never fired (fn_802DFA40
was never reached; the +0x434 call precedes it), [dvd169] = 0
again (skins.god never approached).

fn_802DD5F8 / fn_802DD05C read in full. fn_802DD5F8 calls the
pointer at [0x804562BC] from two sites (loc_802DD858 in its
row loop, loc_802DDA14 after it), r3/r4 = plane-ish args --
it is Bink's selected YUV conversion proc. fn_802DD05C (the
setup fn immediately before it) does NOT pick the proc from a
table: it COPIES the globals block at 0x80450000+252xx from an
input struct (r31, >= 116 bytes): [0x804562BC] := [r31+108]
(path A) or [r31+100] (path B), alongside code constants
0x802DCEEC / 0x802DCFA8 written to +25260/+25264 and plane
fields from [r31+32..+48] / [r31+104..+112]. So in crash runs
the SOURCE STRUCT's proc field already held the heap buffer
0x80D9E040 -- the corruption sits one level up, in whatever
builds/fills that struct (Bink frame setup), consistently
with the whole family: guest structures that should hold
pointers hold data, found by whichever consumer runs first.

Movie-era tally, runs 183-194: completed both movies only in
192 (then the EOF stall, fixed by batch 169, still unverified
because no later run reached skins.god); played through 183,
184, 187, 188, 189; crashed 185, 186, 190, 193, 194 (five
crashes, four distinct pointer-field sets, two sharing the
[0x804562BC] slot and value); stalled 191. Batch 171 (next):
witness fn_802DD05C entry (the source struct's proc fields
+r31 + the slot) and fn_802DD5F8 entry (the slot), to learn
whether the struct is born bad or goes bad.

Run 195 (batch-171 build copy175, CTTR_COVER_LIFT=1, PID
2932): CRASH #6 -- an exact repeat of run 186's signature:
InvokeIndirectCpu target 0, Caller LR 0x802D5594 =
fn_802D5488+0x10C, active target the movie glue fn_800B9558,
dead within ~a minute (final CPU 9.375 s, dialog at both
snaps). Witness tail is the same final heartbeat as 194:
deterministic boot census, burst reads ending 418,557,600,
movie Pause, glue call #1, dispatcher entry #1 with a FULLY
HEALTHY descriptor (o165: cell 0x80C0D1A8 -> obj 0x803F26B8,
m7 = 0x803F27A8) -- then the crash inside that same dispatch.

fn_802D5488's +0x10C call site (loc_802D5578) read in full:
it does NOT dispatch on the entry object. r3 = [r31+20] (a
nested object pointer), r12 = [r3], ctr = [[r3]+28]. At the
crash, r3 = 0x90010004 -- a MEM2-arena address (console:
"MEM2 defaults active -> arena 0x90000800 - 0x97DC0000";
zero unmapped-touch warnings, so the read was legitimately
mapped and the descriptor's +28 slot genuinely contained 0).
So the nested object at [r31+20] was a MEM2 heap object whose
slot +28 was never installed -- while the entry descriptor
the o165 witness samples was healthy. The batch 165 witness
has been sampling the wrong (outer) object for this crash
pair; the inner one is the patient.

Batch 171's own yield, with one self-correction: stage 2
caught fn_802DD5F8's first entry with slot [0x804562BC] = 0
and zeroed planes -- and that call returned harmlessly
(geometry zero skips both guarded calls), so a zero slot at
first DD5F8 entry is NORMAL, not the 190/194 mechanism (there
the slot held 0x80D9E040 at a later, real copy). Stage 1 read
the wrong register: fn_802DD05C's prologue sets r31 = r7, so
the struct arg is gpr[7], not gpr[31]; the stage-1 line
(stru=0x1E0, instruction bytes as "fields") is garbage and is
disregarded. Batch 172: witness inside fn_802D5488 at
loc_802D5578 (r31, [r31+20], [[obj]], [[obj]+28]) and fix
bs171 stage 1 to gpr[7].

Movie-era tally, runs 183-195: full pass only 192; played
through 183, 184, 187, 188, 189; stalled 191; crashed 185,
186, 190, 193, 194, 195 -- six crashes, but now grouped:
the dispatcher pair (186, 195: nested [r31+20] object, slot
+28 = 0), the conversion-slot pair (190, 194: [0x804562BC] =
0x80D9E040), 185 (Bink IO io4 = 0), 193 (plane ptrs = pixel
garbage). All die in the first movie-frame decode/copy pass
after the deterministic boot phase.

Run 196 (batch-172 build copy176, CTTR_COVER_LIFT=1, PID
22660): CRASH #7 -- a seventh distinct signature, plus two
corrections to earlier records. (1) The Logs base_<ts>_pid
directories are created at LAUNCH for every run (their
timestamps are start times: run 191's dir is stamped 06:05:29,
run 192's 06:29:35); only their content distinguishes a
crash. Run 194's crash stands on its dialog + console, not on
the directory timestamp cited there. (2) Run 196's own death:
the orchestration background sequence was killed by a runtime
restart at ~13 min; the run itself had already died in its
first minute (witness frozen at 887,600 bytes, memory dropped
to 187 MB at the parked dialog).

The fatal (console-196.log): [memory] FATAL MMIO read blocked
(non-GPU), guest address 0xCC509EE5, active func the movie
glue fn_800B9558, guest lr 0x802DDBA4 = fn_802DDA48+0x15C
(the fn_802DD05C call site). Stack code refs chain: glue ->
fn_802D68B0 -> fn_802D5784 -> fn_802D5488+0xE8 ->
BinkCopyToBufferRect+0x5B8 -> fn_802DDA48 -> fn_802DD05C.
Guest stack words at the fatal are full of Bink decode floats
(0x45C7E120, 0xC5698125, ...). No InvokeIndirectCpu, no SEH:
translated code in the Bink frame path formed a read at
0xCC509EE5 (the 0xCC000000 MMIO alias + 0x509EE5) and the
memory layer refused it. [dw172] never fired (loc_802D5578
not reached this run).

Batch 171's stage 1, fixed by batch 172 to gpr[7], paid off:
fn_802DD05C's struct is the STATIC descriptor at 0x80400960,
its proc fields are all healthy code (f100=0x802DF5DC,
f104=0x802DF6FC, f108=0x802DF004, f112=0x802DF080), and it
ran twice in run 196, the second entry showing the slot
already installed as 0x802DF948 (code). So the DD05C install
mechanism is HEALTHY: in the 190/194 crashes the slot at
[0x804562BC] must have been overwritten AFTER installation
with the heap value 0x80D9E040. The corruption is a WRITE to
movie-path state after setup, from a writer not yet seen.

Seven crashes (185, 186, 190, 193, 194, 195, 196), one
stall (191), one full pass (192) across runs 183-196 -- all
deaths inside the first movie-frame decode/copy pass, each
touching a different field. Batch 173 (next): a host watcher
thread sampling ~16 hot addresses (the conversion globals
block, the plane struct, the static descriptor's slot, the
Bink handle's IO/frame fields, the dispatcher cell) every
2 ms and logging every change to the witness file -- to catch
the corrupting write's moment and value, whoever makes it.

Run 197 (batch-173 build copy177, CTTR_COVER_LIFT=1, PID
21820): CRASH #8 -- the run-193 SEH repeated exactly (host
0xC0000005, read at 0x100100000000, active fn_802DFA40 from
fn_802DD5F8+0x3AC, identical unmapped-read warnings and
region counters 14108-14111 -- the splash path is
deterministic up to the fault). Final CPU 35.3 s; vug played
(w23 = 389 BinkNextFrame), splash started, [dvd114] = 265.
shot197b (122,789 B) is much larger than the dialog shots —
not yet inspected.

THE WATCHER CAUGHT THE MECHANISM. Batch 173's [bw173] log
(2,052 change lines over its 13.9 s window):

- The conversion slot a1 = [0x804562BC] was NEVER corrupted:
  0 before install, 0x802DF948 after, stable to the end.
  The 190/194 slot value 0x80D9E040 remains unexplained by
  this run (that pair may be a different manifestation).
- a0/a2 = 0x802EB9C4 / 0x802DFA40 (code), a8/a9 = the
  DD05C descriptor's proc fields (code), a12-a15 = handle
  frame table / io0 / io4 / dispatcher cell -- all stable
  and healthy for the whole window.
- The plane fields a4/a5/a6 = [0x803FF8C0+8/+16/+20]: during
  the vug they ALTERNATE between buffer bases (0x80C61460 /
  0x80CD1C60 / 0x80C29F60 sets -- triple buffering, healthy).
  In the splash they instead ADVANCE MONOTONICALLY: a4 sweeps
  0x80C61460 -> 0x9D1DAFBE (~29 MB, no reset, ~14 s), a5/a6
  sweep slower into 0x8EFxxxxx. The decoder's plane cursors
  run away instead of recycling per frame.
- The descriptor slot a7 = [0x803F26D4] held 0x802D5064
  (code) until t=12,381 ms, then was written 0x00009A00 (a
  small count-like value), 0, 0xD6000000, 0, and finally
  0xF8F60000 in the last samples before the fault -- the
  statics region takes stray writes only in the end phase,
  once the cursors have run far out of range (a4 past the
  MEM2 arena end 0x97DC0000 into demand-committed space).

So the splash decode's plane addressing never recycles:
frame buffers registered for the vug are not re-registered
(or not registered at all) for the second open, and the
working pointers free-run until the converter dereferences
them out of range. Next: read BinkOpen (fn_802D8858) /
BinkDoFrame (fn_802D9F60) for where the handle's plane
buffers are installed, extend the watcher with those fields,
and compare the vug open against the splash open.

Run 198 (batch-174 build copy178, CTTR_COVER_LIFT=1, PID
46868): CRASH #9 -- the conversion-slot signature again
(InvokeIndirectCpu target 0x80D9E040, caller
fn_802DD5F8+0x434), this time in the VUG's first dispatch
(w23 = 0, witness 20,723 lines, final CPU 17 s). AND THE
INSTALLER IS CAUGHT. Final witness sequence: [g168] glue
call 1 -> [o165] dispatcher entry (healthy) -> [p157 w24]
BinkDoFrame entered from fn_802D5488+0x74 (the dispatcher's
own call, handle 0x80C0D480) -> [bs171 w2] harmless first
DD5F8 entry -> [bs171 w1] fn_802DD05C entered from
fn_802DD5F8+0x14C with stru = 0x80C0F400 -- a HEAP struct,
not the static descriptor 0x80400960 of run 196. Its fields:
f100=0, f104=0x10000, f108=0xAC44 (44100!), f112=0x10.
[bw173] t=2 ms then shows the globals block rewritten as
a0=0x802D7C28 (code), a1=0x80D9E040 (heap), a2=0x80D96240
(heap), a3=0x802D7B94 (code) -- and DD5F8's post-loop call
read a1 = 0x80D9E040 and died.

So fn_802DD05C installs into the SHARED conversion globals
block from whatever descriptor struct it is handed, and it
serves (at least) two masters: the static video descriptor
(graphics procs 0x802DF948/0x802DFA40, runs 196/197) and a
heap descriptor whose shape -- code, buffer, buffer, code,
plus a 44100 field -- is a Bink SOUND driver registration.
The sound install overwrote the video conversion proc slot
[0x804562BC] with its buffer pointer 0x80D9E040 (the same
deterministic heap address as runs 190/194). Whether the
sound install is legitimate game behaviour that hardware
survives by ordering (video install re-runs after it inside
the frame pass), or itself a symptom of a clobbered r7 in
fn_802DD5F8 (its caller chain runs through the dispatcher
fiber), is the open question. Next: a healthy run under the
current build to census [bs171 w1] descriptor pointers --
if healthy runs also interleave the heap-descriptor install
non-fatally, it is ordering; if they never see it after the
video install, it is the anomaly.

Run 199 (batch-174 build copy178, CTTR_COVER_LIFT=1, PID
21972): CRASH #10 -- the conversion-slot pair again
(0x80D9E040 from 0x802DDA2C), witnessed live by Brandon at
his PC (he screenshotted the dialog; the process was gone
from tasklist by the read-back, consistent with him
dismissing it). The witness tail is run 198's sequence
verbatim: [o165] -> [p157 w24] DoFrame from the dispatcher
-> [bs171 w1] stru=0x80C0F400 -> [bw173] t=2 a1=0x80D9E040.

THE CENSUS SETTLES THE OPEN QUESTION. Run 197 (survived the
vug): [bs171 w1] stru = 0x80400960 (static video descriptor)
20 times out of 20 -- the heap descriptor never appears.
Runs 198 and 199 (crashed): stru = 0x80C0F400 (heap) exactly
once -- the only install of the run, fatal within 2 ms. So
the heap-descriptor install is NOT legitimate interleaving:
it is the anomaly itself. fn_802DD5F8 is entered with the
wrong descriptor in r7 on the runs that die, and every dying
run took the dispatcher's BinkDoFrame route (fn_802D5488
+0x74) for the first frame, while run 197's vug was driven
by BinkNextFrame. The wrong descriptor is real data (a Bink
sound-driver object: callbacks at +32..+48, 44100 at +108),
so the call's arguments were assembled from the wrong
object -- the shared-context family again, this time on the
dispatcher-fiber DoFrame path that batch 150's gate does
not cover. Next: witness fn_802DFB74's arguments and the
dispatcher's DoFrame call site to pin where r7 is set.

Run 200 (batch-175 build copy179, CTTR_COVER_LIFT=1, PID
46668): THE BREAKTHROUGH RUN -- and a new death in new
territory. Brandon watched it live: the window presented
actual frames for the first time in the campaign (white
field with black movie/frontend geometry, vs the uniform
white/black of every earlier run). Census: witness 43,535
lines; [dvd114] = 520; BinkNextFrame = 759, BinkDoFrame
= 400 (cap) -- BOTH movies played through; the arq-pump
fiber-switch servicing counter reached 17,369,938 calls
(the game fully alive in its frame loop).

BATCH 169 VERIFIED, byte for byte as predicted in run 192:
[dvd169] eof-overrun fileOff=577536 req=11552 served=11543
zeroed=9 -- the skins.god final chunk served its 11,543
real bytes plus 9 zero-filled and returned full length.
The waiter resumed, the ENTIRE permanent LoadObjects chain
completed, and the boot went on to the frontend for the
first time ever: frontend.rcf mounted, design/levels/
common/frontend.god loaded, art/frontend/frontend.p3d
requested.

Batch 175 outcome: the poison descriptor 0x80C0F400 never
appeared; all 21 fn_802DD05C installs used the static video
descriptor 0x80400960. The w25 guard also revealed that
fn_802DD5F8 is legitimately entered with plane-buffer
pointers in gpr[7] on other call paths (0x80C86C60 x29,
0x80C16460 x28; logged, not rewritten, harmless -- those
paths do not reach the DD05C install with that value). The
guard stays in as a logged safety net; whether it is the
reason run 200's installs stayed clean or the run simply
took the healthy route is not separable from one run.

The new death: in the frontend phase, fn_8023B188 (GOD
cluster), executing on the dispatcher fiber (pc
0x8024C8E4), read address 0xFE67CD06 -- a garbage pointer
value (float-like bytes). The memory layer absorbed the
first touch with a zero-filled commit (the run's ONLY
unmapped touch), but a follow-on OS__LoadContext hit the
same address as a hard memory error and the process
aborted (the "fatal internal error / called abort" dialog
Brandon screenshotted at 09:32). New family, new phase:
frontend GOD/script work with a bad pointer. Next: read
fn_8023B188 and its callers in the frontend phase; check
the witness tail for the frontend-phase GOD activity that
precedes the read.

Run 201 (batch-176 build copy180, PID 6692): took the slot
route and died in the vug -- target 0x80D9E040, LR
0x802DDA2C, witness 20,817 lines. The batch-176 mutex
watcher showed the GOD static mutex at 0x804478A8 all-zero
(words +0..+16) with +20 = 0x80B9547C throughout the short
run; it never got near the frontend, so run 200's mutex
question stays open.

BATCH 175 VERDICT: the guard never saw its target.
Run 201's only w25 line logged an entry gpr[7] of
0x80C86C60 (a plane buffer); the fatal install (bs171 w1,
stru=0x80C0F400, LR 0x802DD744) came from a fn_802DD5F8
call whose ENTRY gpr[7] was the plane pointer.

CORRECTED PROVENANCE (source + shard reads, Nov 5): the
DD05C descriptor does NOT travel in gpr[7] at all. Entry
gpr[7] is a plane/frame struct pointer (DD5F8 copies it to
r27 and dereferences it). The descriptor is reloaded at
loc_802DD62C from [r1+108] -- a slot in the CALLER's stack
argument block ([callerSP+28]). The caller, fn_802DFB74,
COMPUTES THAT SLOT AS A CONSTANT: r11 = 0x80400000 + 2400
= 0x80400960, stored via a WriteResolvedPair32 at range
offset 28 (fallback: individual WriteResolved32). The
compiled shard is byte-identical in logic to the
functions/ copy on both sides. So on hardware the install
descriptor is always 0x80400960; in poisoned runs
(190/194/198/199/201) DD5F8 nevertheless reads 0x80C0F400
from that slot, and the sibling argument fields come up
garbage too (plane bases 0x12121720 / 0x766481D0 in the
bw173 lines) -- while healthy runs read the constant and
real planes. The failure is therefore in the host memory
path between fn_802DFB74's resolved-range stores and
fn_802DD5F8's flat reads (or in what those addresses map
to), NOT in guest data flow. Batch 175's guard is
superseded as designed; it stays in as a harmless log.

Next (batch 177): read the slot back inside fn_802DFB74
immediately after the store block, log (readback, r11, lr)
as pair-witness w26. Readback == constant but DD05C still
poisoned => the divergence is in the call/read side;
readback == 0x80C0F400 => the resolved-range store path
(WriteResolvedPair32 / ResolveRangeHost) is the bug, and
it would affect every guest function using paired stores.

Run 202 (batch-177 build copy181, PID 6312): slot route
again (target 0x80D9E040, LR 0x802DDA2C, died in the vug),
but the readback witness SPLIT THE BUG: w26 census =
{0x80400960: 1} -- fn_802DFB74's flat-path readback of the
descriptor slot, taken immediately after its store, holds
the CORRECT constant -- while the same run's bs171 w1
census = {0x80C0F400: 1}: fn_802DD5F8's reload of the same
guest address, moments later in the same call chain,
yields the sound object. No guest code runs between the
two reads. So either (a) fn_802DD5F8's r1 differs from
fn_802DFB74's r1 (the static-call path corrupting the
stack pointer, so the reload reads a different address),
or (b) another host thread executing guest code with the
shared CpuContext writes the sound pointer into that stack
slot concurrently (root-cause-#1's family, via a host
thread vector batch 150's SelectThread gate does not
cover -- the audio/Bink sound path is the standing
suspect, since the poison value is always its registration
object). Batch 178 discriminates: w26 now also logs
fn_802DFB74's r1, and a new w27 logs fn_802DD5F8's
reloaded value with its r1 at loc_802DD62C. Equal r1 +
different value => concurrent writer. Different r1 =>
call-path SP corruption.

Run 203 (batch-178 build copy182, PID 36888; died in the
vug, slot signature; the orchestration was killed by a
runtime restart mid-soak and the run was recovered
manually -- it had parked at the fatal dialog with the
witness frozen):

THE STACK POINTERS MATCH EXACTLY. w26 (fn_802DFB74):
a = readback 0x80400960, b = stored 0x80400960, c = frame
r1 0x804C2108 -> its slot = 0x804C2108 + 28 = 0x804C2124.
w27 (fn_802DD5F8): a = reloaded 0x80C0F400, b = frame r1
0x804C20B8 (= 0x804C2108 - 80, the callee's own frame
adjustment) -> its read = 0x804C20B8 + 108 = 0x804C2124.
SAME guest address, call path innocent. The value at
0x804C2124 (in the MAIN thread's stack region,
0x804Cxxxx) changed from the correct constant to the Bink
sound object between two adjacent flat reads with no
guest code in between on this thread. The writer is
another host thread executing guest code against the
shared CpuContext -- root-cause-#1's family through a
host-thread vector (the audio/Bink sound path is the
standing suspect: the poison value is always its
registration object, and the flip also happened in
witness-free builds 185-196, so the writer runs
continuously, not in the witness window).

Batch 179: the watcher gains the slot and its neighbours
(a22..a26 = 0x804C2110, 0x804C2118, 0x804C2120,
0x804C2124, 0x804C212C; the priming call depth -- and so
the slot address -- has been identical across runs
201-203). The change log will timestamp the flip against
the other watched fields and show whether the whole
argument block flips or just the one slot.

Run 204 (batch-179 build copy183, PID 27696): the slot was
FINE this time -- w26 readback 0x80400960, w27 reload
0x80400960, bs171 installed the video descriptor, bw173
t=2 shows the healthy plane set and fn_802DFA40 installed
as a proc -- and the run STILL died in priming, on a
different face of the family: InvokeIndirectCpu target 0
at LR 0x802D8410, inside checksound (0x802D81C4, Bink's
sound-poll helper), right after the first BinkNextFrame.
So the family is bigger than the descriptor slot: Bink-
adjacent pointer fields (handle callbacks, the conversion
descriptor object, the sound poll target) come up wrong in
varying combinations run to run, while runs 192/200 prove
the same code completes when they line up. Working model:
initialization/priming state is being raced by a
concurrent guest-code executor on the shared CpuContext
(the stack-slot flip in run 203 is the proven instance).
Next step is source-level: read how the runtime enters
guest code from its host threads (ARQ pump servicing,
alarm queue, audio callbacks) and whether those entries
synchronize with the main guest thread at all.

ROOT-CAUSE CANDIDATE FOR THE WHOLE MOVIE-CRASH FAMILY
(source read, Nov 5): VI_HLE_ProcessRetracesDeferred
(vi.cpp) is "a wall-clock pump (GX work, host frame
waits)" that delivers retrace callbacks -- and, in the
same call, ARQ completions -- from HOST threads (its
callers: main.cpp's host frame loop and gx_vertex.cpp's
GX timing service). The callbacks run on a
GuestInterruptCallbackContext: a PRIVATE COPY of the
interrupted function's register file -- including gpr[1],
the live stack pointer of whatever guest code the main
thread is executing -- but with FULL access to shared
guest memory, concurrently with that execution. The
retrace chain reaches the alarm-driven 500 ms timer, the
movie glue, fn_802D5488 and Bink code, whose frames land
on the main thread's live stack and stomp in-flight
argument blocks (run 203's flipped slot) and Bink state
(run 204's checksound null, run 197's late descriptor
flip). os_alarm.cpp's deferred pump has the identical
design ("a wall-clock pump... in deterministic mode
alarms fire only from the scheduler"). Console logs
confirm the pumps are ACTIVE in our runs: "[arq-pump] VI
deferred boundary first entry: detClock=0 interrupts=1".

Both pumps refuse to run when DetClock::Enabled(), and
DetClock is switched by the environment variable
NSMBW_DETERMINISTIC=1 (main.cpp), under which retraces,
alarms and audio deliver only from the scheduler's
DeterministicIdleStep, on the guest thread. Run 205 tests
it with no code change: if the crash family vanishes, the
concurrent-pump model is confirmed and the permanent fix
is a CTTR-side determinism/gating decision.

Run 205 (batch-179 build + NSMBW_DETERMINISTIC=1, PID
27140): DetClock engaged ("deterministic timing on",
detClock=1), ZERO fatals -- and ZERO progress: witness
327 lines, no file names, no DVD reads, the process burned
a full core busy-waiting for the whole 1,200 s. Full
deterministic mode stalls CTTR's boot outright: with the
wall-clock pumps off, the events the boot waits on are
never delivered (DeterministicIdleStep only runs inside
the scheduler's idle wait, which this game's fiber/
semaphore boot flow never enters). The pumps are
load-bearing; DetClock is not viable for CTTR as-is.

The servicing bundle's host entry is
ServiceGuestTimingDuringAuroraFrameWait (main.cpp),
registered as Aurora's frame-worker wait callback: it
runs VI retraces, alarms, audio and ARQ servicing while
Aurora's frame worker blocks in FIFO drains -- i.e. on
Aurora's thread, concurrent with the guest thread. The
same services also have guest-thread boundaries (the GX
timing service in gx_vertex.cpp, the scheduler,
ProcessAlarmQueue's tail, the batch-36 fiber-switch tail,
and per-presented-frame GX__CopyDisp). Batch 180
(experiment): env-gate (CTTR_NO_AURORA_PUMP=1) the Aurora
wait callback's servicing, leaving every guest-thread
boundary in place. If the crash family vanishes while
the boot still flows, the permanent fix is to make that
gate CTTR's default.

Run 206 (batch-180 build copy184, CTTR_NO_AURORA_PUMP=1,
PID 12816): the slot crash AGAIN (stru/w27 = 0x80C0F400,
target 0x80D9E040, LR 0x802DDA2C). The Aurora wait
callback is NOT the (only) writer. The remaining
GuestInterruptCallbackContext fabricator is
ServiceDeferredTimingDuringGxWork (gx_vertex.cpp): during
GX work, throttled to 1 ms, it calls
VI_HLE_ProcessRetracesDeferred + OS_HLE_ProcessAlarms
Deferred reentrantly inside the guest's own GX calls.
guest_interrupt_context.h confirms the mechanism: the
deferred chains run on a full copy of the interrupted
thread's CpuContext -- its live stack pointer included --
so the chain (retrace -> alarm -> movie glue -> Bink)
executes on the interrupted thread's stack; when the
interruption lands inside the priming chain itself, the
callback chain's frames coincide with the live frames and
overwrite them (the sound object at the descriptor slot
is one such overwrite). Batch 181: env-gate this service
with the same CTTR_NO_AURORA_PUMP flag (the name now
covers both wall-clock deferred pumps). Scheduler, alarm
tail, fiber tail and present-path servicing remain.

Run 207 (both pumps gated): identical slot crash. Run 208
(batch-182 entry probe): w28 reads the slot ALREADY
poisoned at DD5F8's first statement -- FB74's readback
(0x80400960) and DD5F8's entry read (0x80C0F400) of the
same address straddle only FB74's ctx writes and the
(static, ModHooks-inert) call macro. The watcher baseline
at priming shows FB74's frame area holding a coherent
Bink sound-callback record ({+24: 0x80C0F478, +28:
0x80C0F400, +36: left_callback_first+0x64}) in place of
three of FB74's writes (+24/+28/+36), while its +8/+16
writes survive -- a selective revert of specific stack
addresses to an earlier sound-chain state, writer still
unnamed after five falsified candidates (watcher thread,
Aurora pump, GX timing pump, DetClock stall, call macro).
Batch 183 (targeted correctness patch): at DD5F8's
loc_802DD62C reload, substitute the compile-time constant
0x80400960 whenever the reloaded descriptor differs --
that is the only value FB74 ever stores there on
hardware. w27 keeps logging the pre-guard value, so the
flip stays visible while the boot proceeds.

Run 209 (batch-183 build copy187, PID 9856): THE MOVIES
PLAY. w23=763 BinkNextFrame, w24=400 (cap), dvd114=517,
[dvd169]=1, and the w27 pre-guard census is {0x80400960:
57} -- the descriptor flip DID NOT OCCUR this run; every
install was clean (the guard stood as insurance only).
Names ran the full chain to the frontend (frontend.rcf,
frontend.god, frontend.p3d). Zero InvokeIndirectCpu /
SEH / MMIO fatals.

Death is run 200's frontend death, byte-for-byte in
kind: OS__LoadContext memory error at 0xFE67CD06 (the
identical value as run 200). The batch-176 mutex watcher
shows the static mutex at 0x804478A8 locking/unlocking
plausibly all run (owner 0x8047DF30, count 1), until the
final samples, where its +8 field holds 0xFE67CA0E --
float-like bytes, same 0xFE67xxxx family as the fatal
context value. Verdict: in the frontend phase, animated
3D float data is bulk-written over guest statics (the
mutex, and at least one OSContext the scheduler then
tried to load). One unnamed data-overrun writer remains;
whether it is the same actor as the (intermittent) stack
descriptor flip is unknown. Next instrument: a guard
page on the mutex's host page logging the faulting host
PC + backtrace for any access outside the OS mutex
functions (batch 184).

Run 210 (batch-184 build copy188, PID 10124): priming was
fully clean (w26/w28/w27 all 0x80400960, healthy
descriptor fields, proc installed) -- then the dispatcher
member of the family fired: fn_802D5488 called with a
STATIC instance (r31=0x80356CC8) whose nested object at
+20 was 0x90010004 (zeroed MEM2), target [[obj]+28]=0,
LR 0x802D5594. In healthy run 209 the same witness fires
20x with r31=0x80C0D1A8 (Bink handle) and a valid target.
The mutex watch never armed (the run died in the vug).

New prime suspect, never previously gated:
ArqCompletionPollerMain (audio.cpp, batch 38) -- a
detached host thread that every 50 ms calls
ARQ_HLE_ProcessDeferredInterruptsDeferred(), fabricating
an interrupt context from the live guest registers and
running guest callback chains concurrently with the
guest thread, ~20x/second, from the first ARQ transfer
onward. ARQ serves the sound cluster -- the poison
values' home neighborhood. Batch 185: env-gate the
poller's dispatch with CTTR_NO_AURORA_PUMP (guest-thread
boundaries keep delivering ARQ completions).

Run 211 (batch-185 build copy189, PID 17848, pump flag
on so the ARQ poller was gated too): STALLED AT THE
FIRST ARQ DMA. Witness froze at 18,942 B (~25 s in);
only 2 frames ever presented; console shows the fiber
tail servicing call 1 handled=0, AIInit, the boot ARQ
DMA (0x800 B), the poller start line -- then nothing
for 11.5 min while the main thread burned exactly one
full core (697 s CPU). Loader worker parked in
OSWaitSemaphore as usual. Brandon saw the frozen window
live and flagged it; run stopped early and cleaned.
VERDICT: the poller thread's foreign-thread dispatch is
LOAD-BEARING for boot (batch 144's lesson, strongest
form) -- guest-thread boundaries alone do not deliver
the boot ARQ completion. The poller cannot be switched
off; it must be made safe. It remains the standing
suspect for the pointer flips: it is the one concurrent
guest-code executor left, fabricating callback contexts
seeded from the live thread's registers AND stack
pointer ~20x/second, and the descriptor-flip victim was
a stack slot found holding a sound chain's frame
content. Batch 186 direction: private guest stack for
the deferred-callback fabricated context, so its chains
cannot stomp live frames.

Run 212 (batch-186 build copy190, PID 6564, default
config -- poller and pumps live, no env gates):
BATCH 186 WORKS for the movie phase. w27 pre-guard
census {0x80400960: 57} (the flip never occurred),
dw172 targets {0x802D5E00: 20} all healthy, w23=767,
[dvd169]=1, frontend reached; [w186] hit its 60 cap
(private stacks in constant use). The frontend death
is unchanged: OS__LoadContext memory error at
0xFE67CD06. Batch 184's watch armed and logged only
legit native mutex ops at +0x34..+0x40 -- the
corrupting write never crossed the guest view.

Unification (runs 200/209/212): the GOD mutex owner
field held 0xFE67CA0E with count 1 for ~40 ms in the
frontend phase (bw173 samples, runs 209+212 identical),
then released cleanly. 0xFE67CD06 = 0xFE67CA0E + 0x2F8:
the LoadContext death is the scheduler dereferencing
the same bogus pointer as a thread. The runtime reads
the current thread from guest [0x800000E4]
(__OSCurrentThread; fiber_manager.cpp kOSRunning-
ContextAddr), and OSLockMutex records it as owner --
so [0x800000E4] itself contains 0xFE67CA0E during the
frontend phase. The value exists in game data
(frontend.rcf offset 0x1AE60; also default.rcf and
every onfoot archive -- possibly a shared Cement TOC
hash). Batch 187: second page watch on the low page,
single-word window at 0x800000E4, logging only writes
whose post-step value is not a RAM pointer -- that
names the poisoner directly.

Run 213 (batch-187 build copy191, PID 22864): BATCH 187
NAMED THE POISONER. Priming clean again (w27 57/57,
dw172 20/20, w23=762, batch 186 holding). The page
watch caught [0x800000E4] being overwritten BYTE BY
BYTE: 0x8047DF30 -> 0xFE47DF30 -> 0xFE67DF30 ->
0xFE67CA30 -> 0xFE67CA0E, four single-byte stores from
one host RIP, active guest fn_8020935C, ~435 ms after
the watch armed, immediately after frontend.rcf reads
at fileOff 108544/141312 (the poison bytes sit at
archive offset 0x1AE60, inside the first read's
buffer). Host disassembly of the faulting instruction
(base from the console's own image+ pairs):
movb %bl,(%r13,%rax) inside func_8000519C -- the
game's runtime-library memcpy (.init:0x8000519C), in
its byte-copy loop. A guest memcpy is spraying stream
data across low memory with a near-zero destination;
__OSCurrentThread is just the byte range that kills
the scheduler later. The poller never logged a
recovery: [0x800000E4] stayed poisoned. Batch 188:
witness at memcpy entry for dest < 0x80010000, logging
(dest, src, len, lr) -- the exact bad call.

Run 214 (batch-188 build copy192, PID 19908): the
[w188] log's last line is the poison call itself:
memcpy dest=0x80000000 src=0x80722E32 len=512
lr=0x80251938. (The rest of the log is legit traffic
the filter also catches: boot-time exception-stub
installs at lr 0x80342E00 and ARQ FAKE_VMEM staging
copies to 0x7E00xxxx.) Priming clean again (w27
57/57, dw172 20/20, w23=753); loadctx-err=1, final
CPU 61 s.

Caller chain, from the generated sources:
fn_802518DC is a stream buffer fill (fread-shaped):
r31 = size*count; short path copies from
[stream+40]+[stream+44] (buffer base + cursor) via
fn_80251A04 (the memcpy thunk) with dest = its r4
argument, then advances [stream+44] and [stream+20].
It is reached through fn_80251894 (a guard predicate
on [obj+12]/[obj+14]) from fn_8020935C, a virtual-
dispatch helper in the frontend load path. For the
poison call the destination argument arriving at
fn_802518DC was exactly 0x80000000 (MEM1 base) and
len 512 = size*count. Batch 189: witness at
fn_802518DC entry for dest < 0x80100000, logging the
stream fields [40]/[44]/[48]/[60], all args, and the
up-chain caller read from fn_80251894's saved lr.

Run 215 (batch-189 build copy193, PID 24224, short
soak): [w189] caught the fill red-handed:
stream=0x80712308 dest=0x80000000 size=512 count=1
caller=0x802093F8 (fn_8020935C's first fn_80251894
call), stream fields healthy (buffer base
0x80722400, cursor 0xA32 -> src 0x80722E32 exactly
as the memcpy showed; limit 0x10000; consumed 226).
Process died before the snaps (shots missing);
loadctx-err=1 again.

Source archaeology: fn_802092EC (called at
fn_8020935C entry) reads a 28-byte record from the
stream into fn_8020935C's frame via the same fill
(size 7, count 4). fn_8020935C then calls vtable
methods on its object arg with record fields
[+8]/[+12]/[+16] as arguments, then issues the 512-
byte fill with size = record[+20]. The fill's dest
argument is never explicitly set in fn_8020935C
before that call -- it is whatever ctx->gpr[4]
holds after the preceding virtual calls (last
written from record[+8] for the first vtable call).
Whether record[+8] itself is 0x80000000 (data-driven)
or the value is call residue is the open question.
Batch 190: witness fn_8020935C's entry args and the
record words + passed gpr[4] just before that call.

Run 216 (batch-190 build copy194, PID 40248; its
orchestration was killed by a runtime restart at
~3 min, recovered manually -- the run was unharmed):
[w190] SPLITS THE BUG AGAIN. fn_8020935C was
entered ONCE (r3=0x80B04500, r4=0x80712308 the
stream, r5=0x80949D78 the object, lr=0x801EC518).
The record it read: word0 0x49443350 ("ID3P" -- the
P3D chunk magic), [+8]=0x20, [+12]=0x20, [+16]=8,
[+20]=512 (the fill size), [+24]=1024. And the dest
register actually passed to fn_80251894 was
gpr[4]=0x20 -- NOT 0x80000000. But fn_802518DC
received dest=0x80000000 (w189, identical line).
fn_80251A04 (read from source) is a read/write
dispatcher: with r7==1 it forwards (r4,r5,r6)
straight to memcpy; the dest it used was 8DC's r4.
So gpr[4] mutates 0x20 -> 0x80000000 somewhere
inside fn_80251894's invocation -- whose own code
never writes gpr[4] (it only reads two stream flag
bytes and forwards). The mutation lives in the
call/dispatch boundary or in servicing that runs
inside it. Batch 191: log gpr[4] at fn_80251894
entry and just before its fn_802518DC invoke,
filtered to the frontend stream 0x80712308.

Run 217 (batch-191 build copy195, PID 30784):
[w191] logged ~200 stream fills -- in EVERY one,
gpr[4] at fn_80251894 entry equals gpr[4] just
before its fn_802518DC invoke: no in-body mutation
in any ordinary call. But the shared 200 cap burned
on the stream's constant small reads before
fn_8020935C's fill ever fired ([w189]/[w187]
confirm the poison still happened, t=433), so the
one call that matters is not in the log. Batch 192:
tighten the w191 filter to the poison signature
(frontend stream AND (caller is fn_8020935C's fill
sites OR size >= 0x200)).

Run 218 (batch-192 build copy196, PID 8760): the
filtered [w191] caught the poison pair: at
fn_80251894 entry for lr=0x802093F8, r4 is ALREADY
0x80000000 (and unchanged pre-call) -- while
[w190 w2] read 0x20 in fn_8020935C just before.
The gap closed by reading the COMPILED SHARD
(shard_7a5a406c...): its loc_802093E4 block writes
ctx->gpr[4] = r4 -- a line the functions/ view
hides (the shard emits the full register write-back
set at every call block; the functions/ copies are
a reduced view). The local r4 there is
(r3 | r3) on the RETURN VALUE of the preceding
[[r31]+28] virtual call. Protocol decoded:
fn_8020935C calls vtable method [+28] -> returns a
destination buffer, freads record[+20]=512 bytes
into it; then [+24] -> returns a buffer, freads
record[+24]=1024 bytes. For [+24] the return was
0x80C5D1A0 (healthy heap). For [+28] it returned
0x80000000. Both look like 0x80000000 + a stored
offset; the [+28] object's offset field is 0 --
never assigned. Batch 193: extend the w190 site to
log the object's vtable and its [+8]/[+24]/[+28]/
[+48] targets plus the [+28] return value.

Run 219 (batch-193 build copy197, PID 38576):
[w190 w3] names the methods -- object 0x80949D78,
vtable 0x803D8DB0: [+28] = fn_801EBB34 returned
0x80000000 live; [+24] = fn_801EBB2C; [+8] =
fn_801EB488; [+48] = fn_801EBAA4. Sources:
fn_801EBB2C = return [this+20];
fn_801EBB34 = return [[this+12]+84].
fn_801EB488 (the [+8] setup, a Pure3D image/texture
chunk loader) creates the sub-object P at [obj+12]
via fn_801EC8AC, then seeds obj+20 = [P+80],
obj+16 = [P+72] (pitch, negated for bottom-up),
obj+24 = 0, obj+8 = an arg. So [P+80] = 0x80C5D1A0
(the healthy 1024-byte read dest) while [P+84] =
0x80000000 (the 512-byte read dest -- palette-sized:
256 x 2 bytes). Batch 194: log P and its fields
+72/+80/+84/+88 plus the object's fields at the
same site to pin which of P's fields is bogus.

Run 220 (batch-194 build copy198, PID 37816):
P identified -- [w190 w4] P = 0x8042E2A8 (a static
in the 0x8042xxxx data/bss region), [P+72] = 0x20
(pitch), [P+80] = 0x80C5D1A0 (pixel buffer, set),
[P+84] = 0x80000000 (the bad field), [P+88] = 0.
[w190 w5] obj fields: +16 = 0x20, +20 = 0x80C5D1A0,
+32 = 8, +40 = 0x12 (format). fn_801EC8AC is a
thunk: P = [[ [arg+16] ]+60]([arg+16]). Since P is
at a fixed static address, batch 195 adds a third
VEH page watch (guest 0x8042E000 page, word
0x8042E32C) armed at the same frontend.rcf trigger,
logging every stepped store overlapping [P+84]
with post-store value, host RIP and active fn --
the same technique that named memcpy for
[0x800000E4]. Risk: if the write predates the
frontend trigger the watch misses it; the frontend
phase is when P is used, so odds are good.

Run 221 (batch-195 build copy199, PID 24100): the
[w195] watch armed at the frontend trigger but
logged ZERO writes to [P+84] while the value still
read 0x80000000 -- the write predates the frontend
phase (or bypasses the guest view). DOL section
check: P (0x8042E2A8) lies in .bss
(0x8040B200 + 0xA7288), zero-initialized, so a real
runtime write of 0x80000000 exists. Batch 196
splits the arm: CttrWatchArmP84Page() arms ONLY
watch-3, triggered from CttrNameWitness at the
first ".rcf" name (startup.god era, far earlier);
watches 1/2 keep the frontend trigger.

Run 222 (batch-196 build copy200, PID 3432):
watch-3 armed at the first .rcf name AND at
frontend -- still zero guest-view writes to
[P+84], value still 0x80000000 at the fill. So the
write either predates all GOD file activity (DOL
ctors / early init) or goes through the host view
(native code). Batch 197 discriminates cheaply:
log [P+80]/[P+84] at both arm points (first .rcf
and frontend). Already-bad at first .rcf = pre-GOD
write; good-then-bad with a silent watch = host
view write in between.

Run 223 (batch-197 build copy201, PID 14296) --
the bracket verdict: [w197] p80/p84 are BOTH ZERO
at the first-.rcf arm AND at the frontend arm,
yet [P+80] = 0x80C5D1A0 and [P+84] = 0x80000000
at the fill, with watch-3 armed and silent the
whole frontend phase. Memory::Config::WiiDefaults
(memory.cpp) explains it: the flat map carries
THREE MEM1 views over one backing section --
MEM1_PHYS 0x00000000, MEM1 cached 0x80000000,
MEM1_UNCACHED 0xC0000000. Watch-3 protected only
the cached page; the writer uses an alias page
(phys or uncached VA), invisible to the watch.
Batch 198 extends watch-3 to protect and step all
three alias pages of 0x8042E000, logging which
alias each write came through.

Run 224 (batch-198 build copy201->copy202,
PID 18416): all three alias pages protected --
STILL zero writes logged, [P+84] still becomes
0x80000000 between the frontend arm and the fill.
The only remaining channel is the HOST view: the
unprotected host alias native code writes through
(memory.cpp: "GetPointer still hands out the
unprotected host alias, so native code (image
loading, DVD reads, HLE) is unaffected by the
guest view's protections"). Batch 199 adds the
host-alias page of [P+84] (via HostPointer) as a
fourth watched page in watch-3, with a host flag
on the log line.

Run 225 (batch-199 build copy203, PID 7928): the
host-alias page protected too -- STILL zero
writes caught on any of the four mappings, and
[P+84] still becomes 0x80000000 in the frontend
window. No store instruction explains it. Next
hypothesis: the guest and host VIEWS of P's page
have diverged (a remap / on-demand-commit split),
so the "write" is an artifact of which view reads.
Batch 200: at the w190 w4 site, also log the
host-view reads of [P+72/+80/+84/+88] via
::Memory::Read32 alongside the guest-view values
already logged -- a mismatch proves divergence.

Run 226 (batch-200 build copy204, PID 19064):
[w200] host-view reads MATCH the guest view
exactly (p80=0x80C5D1A0, p84=0x80000000) -- no
divergence; the value is real in the shared
backing, yet no store faulted on any mapping
while armed from the first .rcf name. Remaining
timing hole: P's fields may be set before that
arm (e.g. during DOL load / static init). Batch
201 arms watch-3 at the end of GuestFlat::
Initialize itself -- before the guest executes a
single instruction -- closing all timing doubt.

Run 227 (batch-201 build copy205, PID 18884):
watch armed at Initialize caught exactly TWO
writes to the [P+84] word -- both value 0, at
[P+80]/[P+84], from guest 0x80005240 (the bss
zero-init, host=0). After that, NO store on any
watched view ever touched it, yet it reads
0x80000000 at the fill. THE MISSING VIEW FOUND
in guest_flat_memory.cpp: SectionOffsetFor maps
every Mem1-backed region at (base & 0x1FFFFFF)
into one 32 MiB section -- so FAKE_VMEM
(0x7E000000, size 0x2000000), the ARQ staging
window, aliases the ENTIRE MEM1 backing from
offset 0. A write to guest 0x7E42E32C lands on
[P+84]'s backing. The watch never covered the
0x7E42E000 page. Batch 202 adds it as a fifth
watched page (aliasBase 0x7E42E000).

Run 228 (batch-202 build copy206, PID 12668):
still only the two zero-init writes caught.
CORRECTION on batch 202's premise: ClassifyBacking
(memory.cpp) puts FAKE_VMEM in none of the MEM1/
MEM2 ranges -- it is Backing::Owned, a separate
store, exactly as its config comment intends.
The FAKE_VMEM page watch was a dud. Also verified:
all three MEM1 regions share ONE section, so
HostPointer returns the identical host VA for
0x0042E32C / 0x8042E32C / 0xC042E32C -- the single
protected host page covers every native alias.
Every view is watched, from Initialize, and the
value still appears. Batch 203 changes tactic:
a 100 us poller (started at first name witness)
samples [P+80]/[P+84] through BOTH the host view
(Memory::Read32) and the guest view (raw flat
pointer) and logs the first nonzero transition
with its timestamp -- narrowing the writer's
window to sub-ms and testing view agreement
continuously.

Run 229 (batch-203 build copy207, PID 35440):
ZERO [w203] lines -- the poller never logged a
transition, not even an initial one, although
[w200] at the fill reads the poisoned values
through the same ::Memory::Read32. Either the
poller thread died at start (an uncaught
Memory::Read32 exception would do it silently)
or it read zeros forever. Batch 204 hardens the
poller: a start line with the first read values,
try/catch around the reads with an exception
line, and a 30 s heartbeat logging current
values, so its liveness and readings are proven
in the log itself.

Run 230 (batch-204 build copy208, PID 47356):
THE POLLER READS ZEROS FOREVER (start + 13
heartbeats over 390 s) while [w200] at the fill
reads the real values through the same function.
ROOT CAUSE OF THE WHOLE HUNT FOUND -- an
off-by-interpretation error of mine: the
generated code's field offsets are DECIMAL.
fn_801EBB34 reads [[this+12]+84] = P + 84 decimal
= 0x8042E2FC, NOT 0x8042E32C (P + 0x84 hex).
Batches 195-204 watched the wrong WORD
(0x8042E32C) in the right PAGE (0x8042E000):
the page watch stepped the writer's stores all
along and silently discarded them at the overlap
test. Correct fields: [P+72]=0x8042E2F0,
[P+80]=0x8042E2F8, [P+84]=0x8042E2FC,
[P+88]=0x8042E300. Batch 205 corrects the
overlap test + readback word in watch-3 and the
[w197]/poller read addresses in os_init.cpp.

Run 231 (batch-205 build copy209, PID 41208):
THE WRITER IS NAMED. [w195] (121 lines, cap hit):
guest fn_801E6F44 writes value 0x80000000 to
BOTH [P+84] (rip ...EE95) and [P+80] (rip
...F00B), ~59 times, from poller t=19 ms on.
The corrected poller: p84 = 0x80000000 in every
sample after t=19 ms (one heap value 0x80BFA6A0
at start); p80 cycles through heap buffers as
the descriptor is recycled per image.
fn_801E6F44 source read (func_801E6F44.cpp):
it IS the (+60) factory -- r3 = 0x80430000-7512
= P itself; it calls fn_801E7090(P, src) -> r31,
then initializes P from the SOURCE image object
r29: [P+80] = fn_801E67B0 result / later
[[r29+idx]+100] values; [P+72] = +/-[r29+72];
and [P+84] = 0x80000000 + (rotl([r29+52], 5) &
0x4000000) -- a single bit of source field +52
decides between 0x80000000 and 0x84000000; the
bit is 0 for every conversion in our runtime.
Batch 206 instruments fn_801E6F44: entry fields
[r29+48..+104] + the computed [r31+84], to see
whether [src+52] ever differs (esp. frontend vs
working boot images) and whether r31 is always P.

Run 232 (batch-206 build copy210, PID 29984):
[w206] hit its 300 cap = 150 conversions.
CENSUS: dest is ALWAYS P (0x8042E2A8); computed
[P+84] is ALWAYS 0x80000000; [src+52] is 0 in
ALL 150 source objects (also [src+48]=0;
[src+100] = live pixel pointer, so conversion
always proceeds). On hardware [src+52]'s bit 21
must be set for paletted images (else the game
itself would stream palette data onto 0x80000000)
-- so field +52 of the source image is populated
on hardware from a source our runtime misses.
[src+52] writer/class unknown. Batch 207 swaps
the w1 witness's (always-zero) arg4 field for
[src+0], the source's vtable, to identify the
class and find its +52 writer.

Run 233 (batch-207 build copy211, PID 31304):
source vtable = 0x803D8184 in all 150
conversions. DOL dump of that vtable: [+60] =
0x801E6F44 (the factory -- alignment confirmed),
neighbours 0x801E6E80/6F14/6F1C/6F24/6F2C/
6F3C/6F34/750C/7534/7684/70D8/7C74 and
0x8020079C/7AC/7FC. No generated function names
the vtable VA literally. NOTE: the w206 cap
(150 conversions) burns in the first ~20 s --
the FRONTEND image's own conversion was never
witnessed; P is a singleton, so the frontend
conversion either also computed 0x80000000 or
did not run. Batch 208 raises the w206 cap to
5000; stats will read the conversions nearest
the [w190] fill.

Run 234 (batch-208 build copy212, PID 34284):
4,479 [w206] lines (~2,239 conversions,
including the frontend image's own, nearest the
[w190] fill at witness line 51358): ZERO with
[src+52] != 0, ZERO with computed [P+84] !=
0x80000000. The bit-21 theory is dead: [src+52]
is 0 for every image in the game as we run it,
so the conversion ALWAYS yields 0x80000000.
Batch 209 (EXPERIMENT, same class as batch
183's guard): in fn_801EBB34 (the [+28] getter,
12 bytes), substitute a scratch MEM2 buffer
(0x97F00000) when [P+84] == 0x80000000. If the
frontend survives and reaches title, the
palette fill was the only victim and any later
getter-based palette read stays consistent.

Run 235 (batch-209 build copy213, PID 32996):
BREAKTHROUGH -- THE FRONTEND DEATH IS GONE.
loadctx-err = 0. The batch-209 palette guard
(getter returns scratch 0x97F00000 when [P+84]
== 0x80000000) let the whole frontend.p3d
texture set load: dozens of fn_8020935C image
chunks (0x10..0x200 px, format 0x12), dvd169
fired twice, final CPU 408 s (full soak, vs
~57 s death runs), shots 11,560 / 7,787 bytes
(NOT the 12,383-byte dialog). The game ran its
frame loop (~109 ms frames in the late phase).
NEW ISSUES late in the run: [0x800000E4] was
poisoned AGAIN at t=261 s, this time with
0x00100010 (not the palette bytes), and the
console shows OSSleepThread warnings (wait queue
0x804AEB6C unsatisfiable from a non-switchable
deferred-callback region). Bink activity resumes
at the witness tail. Next: inspect shot235a/b,
find the 0x00100010 writer ([w187] page-watch /
[w188] memcpy lines near the end of witness-235).

Run 235 visuals + tail analysis: shot235a
(+3 min) = the movie viewport geometry (black
rectangle on white, same as run 200) during a
movie phase; shot235b (+5.5 min) = all-white
frame (fade/transition). The frontend itself
LOADED DEEP: names end at car frontend models
(art/cars/neochev/neochev_frontend.p3d,
art/cars/bonecar/bonecar_frontend.p3d). The
t=261 s curthread events look benign: 0 -> the
legit 0x8047DF30 restored 2 ms later (a switch
transient the poller caught), then 0x00100010
as the run was stopping, with Bink frames still
cycling. Textured frontend rendering is not
visible yet (flat black/white frames), PAD is
still dead (run 190), and the frontend phase
runs ~109 ms frames with OSSleepThread retry
warnings from a deferred-callback scope.
Run 236: long soak (18 min, snaps every ~3 min)
on the batch-209 build to confirm the frontend
settles into a stable attract/title loop.

Run 236 (batch-209 build copy213, PID 35592,
18-min long soak): STABLE. Final CPU 1080.8 s
(~98% of one core for the whole soak), ZERO
fatals of any class, one OSSleepThread warning
total. shot236a (+3 min) shows the movie
viewport with the bottom-left shape shifted vs
run 235 (real Bink frames playing); shots b-f
are the all-white frame. Guest file/movie
activity ends at poller t~261 s (the same point
as run 235): [0x800000E4] settles to 0x00100010
-- the PHYSICAL form of thread 0x80100010 (the
OSSleepThread warning in run 235 names "thread
0x100010"), i.e. some path publishes the current
thread phys-masked; harmless across 13 min of
idle but a latent mutex-owner compare risk.
After that the game sits in a stable frame loop
presenting white at ~109 ms/frame -- the
frontend/title idle state. THE BOOT CAMPAIGN'S
BLOCKING CHAIN IS CLOSED (batches 150, 154,
155, 162, 163, 169, 183, 186, 209). Remaining
frontier: visible textured rendering, PAD
input revival (dead since run 190), frame
pacing (~109 ms), the phys/cached curthread
inconsistency, and the palette guard's root
cause ([src+52] always 0 -- guard 209 is a
bypass in the same class as guard 183).

Run 236 witness re-analysis (correction): the
witness going quiet at poller t~261 s is
substantially a CAP artifact ([o165] hit its
3000 cap exactly, [bw173] 3919/4000, [dvd109]
1000) -- guest inactivity is NOT proven by it.
The reliable channels (console frames, CPU,
shots) show the game running a loop to the end.
BUT the movie glue [g168] froze at n=776 in BOTH
runs 235 and 236 (identical), the last script
witness shows the boot player paused at the
movie gate (lr 0x800B9E54), and the last reads
are movies.rcf streaming. So the stable state
is most likely PARKED at the frontend movie
gate -- assets loaded, menu never took over --
not a title idle. Next: the movie-end condition
in the glue fn_800B9558.

Bik headers parsed from the host movies.rcf:
vug (offset 8192) = 500 frames @ 30 fps = 16.7 s
-- matches its observed 17.5 s life, so Bink
pacing is real-time in our runtime. Attract
(offset 5265408) = 2,026 frames @ 29.97 fps =
67.6 s, 1 audio track. But witness-237's
[dvd114] lines (794, below cap -- genuine) END
at movies.rcf fileOff 5,699,552 = only ~434 KB
(~1.4 s of movie) into the attract, and the
batch-210 poller saw zero flag transitions for
~7 min while the glue never returned from the
attract's first call. Bink streaming STARVES
~1.4 s into the attract. Batch 211: a poller on
the attract's Bink handle (0x8138B080, stable
across runs) sampling Frames/FrameNum/rate and
the IO fields every 250 ms.

Run 238 (batch 211, copy215): zero fatals.
Boot handle plays both movies at real-time pace
(framenum tracks ~30-46/s). ATTRACT handle
0x8138B080: frames=2026 confirmed, framenum
reaches 2 at t=250 ms and NEVER changes again
in ~5.5 min of polling; IO slots healthy. After
the attract start, [o165] (dispatcher entry)
never fires again in the witness (cap-blind
after line 21,461, so inconclusive alone), one
lone dispatcher-route BinkNextFrame for the
attract, then no more reads. Leading model: the
glue spins inside the attract's first call and
the completion-dispatcher fiber -- which pumps
BinkDoFrame/BinkNextFrame for playing movies --
is starved of scheduler entries, so Bink starves
at frame 2 and the movie never ends. Batch 212
tests it: heartbeat counters in fn_8024F5A0
(dispatcher) and at the glue loop's present
site, sampled by a 5 s poller.

Run 239 (batch 212, copy216): zero fatals. The
[w212] heartbeats kill the starvation model and
invert the picture. Dispatcher entries: 1 all
run (fn_8024F5A0 loops internally per
activation -- entry count is not a rate). Glue
loop iterations: ~3.8M in the first ~25 s
(~240k/s -- the VUG's own glue call is the spin;
the busy pump is normal and the vug plays
inside it), then exactly +1 iteration in the
next 290 s. The splash and frontend eras run
with the glue returning immediately per call.
For the attract, the glue reaches its present
site ONCE and then PARKS inside one loop
iteration -- blocked in a wait inside
fn_8027D34C, fn_802D68B0->fn_802D5784, or
fn_800B9EB0's advance path -- while Bink's
FrameNum sits at 2. (shot239b is a screen-rect
capture of Brandon's Discord, not the game
window -- the snap method captures screen
content at the window rect; discard it.)
Next: read fn_802D5784 and fn_8027D34C for the
blocking wait.

Run 240 (batch 213, copy217): zero fatals.
Rates settle it: dispatcher items trickle all
run (~2/s in the frontend era, NOT frozen);
glue frozen after the vug; BinkNextFrame frozen
at 773 from t=25 s (+1 for the attract).
Console: the [arq-pump] fiber-switch tail ran
21.19M times (the cooperative system switches
constantly), frames present ~9/s with game
~109 ms, and the run carries the OSSleepThread
wedge pair: thread 0x100010 (the phys-form
current thread the [w187] poller caught being
written at the attract start) tries to block on
wait queue 0x804AEB6C from a non-switchable
(deferred-callback) region and retries forever
-- the runtime's own comment in os_sleep.cpp
flags exactly this failure mode. Next: sampler
stack snapshot of a live attract-era process to
name the parked callback and each thread's
state before choosing a fix.

## CAMPAIGN SINCE NOV 5, 2026: MOVIE, WEDGE, FRONTEND

This section condenses the campaign from run 241 through run 346.
The full working record for the corruption hunt is docs/WRITER-HUNT.md;
the full record for the frontend crash is
docs/FRONTEND-CRASH-2026-11-09.md. Entries below keep only what is
proven, with retracted readings marked as retracted.

### Runs 241-255 (Nov 5): the movie plays; the "pure" crash dies

The frame-2 park from runs 236-240 broke: by runs 248/249 the attract
movie advances at real time (29.97 fps) instead of freezing on frame
2, with a guardian restoring a corrupted OS thread row within ~150 ms
when the load-era damage lands. The next gate sat ~57-60 s into the
movie: a callback calling through a pure3d::Geometry class descriptor
address, the same Pure3D chunk-loader gap then blamed for the
frontend's black untextured quads.

That attribution was then proven wrong as a root cause. Runs 253/254
resolved the fatal host stack: the invoker is the native
ProcessAlarmQueue, reached through the presenter's VIWaitForRetrace
sleep. The alarm-queue anchor was computed with an SPM-derived r13
offset (0x73F0) that, in CTTR's memory map, lands inside Pure3D
registry data holding the "pure3d::Geometry" descriptor pointer, so
the queue walk read the descriptor itself as an OSAlarm and called
its text as a handler. Batch 227 gates the native alarm dispatch on
the handler being a real translated function. Run 255 completed its
full soak with zero fatal errors, the gate catching the bogus
dispatch every time it would have fired.

With the crash gone, the failure underneath it became visible: a
silent stall at the attract handoff. The completion dispatcher
finishes its 161 items, the movie freezes about halfway (frame
~1036 of 2026), and the guest threads park with nothing waking them.
That stall, in two layers, is the rest of this section.

### Nov 6-7: CTTR-only configuration partition

Brandon's scope rule (Nov 6, 2026): anything not related to CTTR is
excluded from the CTTR build/recomp configuration, not merely
runtime-gated. The partition ran in phases (foreign source units
dropped, foreign native registrations stripped, foreign unity units
dropped) and was verified exact: 105 PPC native overrides remain,
103 CTTR plus the batch 265 HLE mutex pair, with zero foreign and
zero missing registrations against the packed CTTR function set
(25,174 functions in the CTTR paths re-emit). Generic WiiCompiled
and Aurora infrastructure stays only where CTTR uses it.

### Batches 254-282, runs 288-317 (Nov 7): the drip, the storm, layer 1

The corruption family behind the stall was chased with watch and
shield instruments (batches 254-261: watch-4 page shield logging
writer RIP plus guest active/pc/lr; batch 261 built the six-word
watch from the drip-caller study). Three manifestations were proven
separately before they were unified:

- The drip (load era, every run): thread owned-mutex lists and mutex
  link fields come to hold data dwords from a static character and
  gradient buffer (MEM1 0x80072F8C-0x80103C1C). Exercised by the file
  layer's lock cycle; byte-identical values and order across runs.
  The posting thread's owned-list tail holds data at post time; the
  only drip words the shield ever catches are the message-queue prev
  word and the GOD mutex prev word, always written from 0 inside
  OSLockMutex. Batch 265 moved the lock pair into HLE; batch 266
  quarantines an implausible entry owner; a drip-fed list can still
  fault a deeper walk node, an exposure never observed as the storm
  site.
- The module-walk storm (runs 301/302): LogGuestModulesOnce walks a
  "REL module list" from 0x800030C8 on every retrace. CTTR is a
  single-DOL game; the word there is 0x10101010 in every run, not a
  module pointer. The walk faults once per retrace on data behind
  that word and prints a ~129-line dump each time: ~120k dumps,
  1.7-1.9 GB consoles. Batch 272 latches the walk settled on first
  failure or completion and retired the amplifier. There is no real
  structure to protect; the list is fake.
- The rampage (runs 288/292): a Lua-region container helper called
  once with a garbage object fills elements monotonically to the
  MMIO boundary; the runtime's absorption policy commits ~2.78 GiB
  of host blocks, which is what kills the process. Not a drip
  escalation (293 had the identical drip and no rampage); caller
  never identified; onset sits inside the storm endgame.

Batch 274's HLE-entry validation then caught the engine of the
remaining damage: the lock pair's currentThread, read from the
running-context word 0x800000E4, is sometimes a data dword
(0x00100010, 0x00790078, and the doubled-u16 family). The phantom
thread's fields resolve through the physical alias into the static
buffer, so lock and unlock surgery runs against the buffer and sets
mutex owners to data values. Batch 275 resolves an implausible word
against the fiber manager and aborts when no plausible fiber thread
exists; run 307 showed the drip contained on it ([w256]=0,
quarantine=0, 299 resolutions, 0 aborts).

The wedge itself was separated next (runs 307/308): OSSleepThread
trusts the same poisonable context word, links the phantom into a
real wait queue, and the wake side faults on it in alternation, a
fault-retry livelock. Batch 276 resolves the context word in
OSSleepThread and makes WakeupThreadQueue clear and log a queue
with an implausible head. Batch 277's pick-loop guard and batch
278's reconcile-walk and insert guards followed; UPDATE 3's
instruction-level attribution to the pick loop was then corrected
by disassembly (the faulting reader is the batch 252 reconcile walk
inside its try/catch, per-switch noise, not the wedge). Batch 280
extended the page shield to the context words 0x800000D4/DC/E0/E4
and armed page 0.

Runs 312/313 proved layer 1 (UPDATE 7 of the brief): a frozen run
ends with the saved current-thread word sane and the running word a
stuck spray value; SelectThread's gate returns "no switch" when the
two disagree, and SelectThreadSwitch, the running word's only
routine rewriter, sits behind that gate. A stuck poison is a
deadlocked fixed point, the lost wakeup unified across 311/312/313.
Batch 282 heals the gate itself: an implausible nonzero context
word trusts the plausible side, else the batch 275 fiber resolver,
writes back, logs [w282]. Runs 314-316 soaked on it with clean
books (50/104/133 heals). Layer 1 is fixed. The writer behind the
spray was still unnamed, and a second layer killed 314/315/316
identically at guest ~330-340 s.

### Runs 314-341 (Nov 7-9): layer 2, from a frozen dispatcher to one flipped field

Batch 283 cleared the switch layer for layer 2 ([w283]=0). Batch
284's spin witness named the visible loop: the movie glue polling a
flag byte through a lock, read, unlock helper on the manager mutex;
batch 285 resolved that helper completely, and batch 286's poller
(f84, mutex, queue, dispatcher state every 250 ms on change) showed
the healthy machine and the break order. The dispatcher
(fn_8024F5A0) drains a ring of completion items; its count freezes
at exactly 161 in every layer-2 death. Batch 287 captured the
dispatcher object for the poller; batch 288 named the stuck current
item (0x807121D0, the same object in every death).

Anatomy rounds on the dispatcher rewrote the worker picture: the
empty-ring path performs the engine's own hand-rolled context
switch to a peer context; the dispatcher has no guest thread of its
own and executes inline on the main thread, driven by pump calls
from the main loop. Batch 291's stage breadcrumbs put the fatal
item at stage 2, frozen inside its completion handler's virtual
calls, and named the file class: sound/scripts/sfx/frontend.p3d.
Two park sites were then separated (runs 322/323): the fighttree
handler fn_800A7798's readiness wait loop (poll a device object at
vtable+88, pump the peer queue on gated iterations, no timeout),
and the .p3d handler fn_80250C24's own stream loop. Run 322's fatal
file was pasadenaFrontEnd.fighttree, not frontend.p3d: the defect
is not file-specific.

Batches 292-295 bracketed both handlers with counters. The wait
counters read zero in runs where the handler demonstrably ran
(324), and the stream counters stopped at deterministic totals
(6,484) in run after run: the parks are inside single nested calls,
not in the loops. Batch 296's freeze watchdog (guest fiber dumps)
first fired only in healthy boot, but its baseline was gold: five
guest threads, the dispatcher inline on the main thread, and the
frozen dispatcher's state readable only from a freeze-time dump.
Batch 297 retuned the trigger; batch 298 replaced the dump walk
with a bounded visitor after the watchdog appeared to hang, a
reading UPDATE 22 then retracted on source evidence: the poller
had retired on its own 500-line print budget, by design, just
before every freeze. Batch 299 was pure budget surgery so the
instruments survive into the frozen phase.

Run 331 rewrote the end-state: the .p3d park released (all handler
counters drained and balanced), the dispatcher emptied and
stopped, no thread was parked anywhere the fiber table could see,
and the wedge was live: the guest CPU thread cycling GOD loader and
mutex work that never produces the one completion the movie flag
waits on. Batch 300 captured the fatal wait object (0x80B93060);
its readiness method (fn_8023B744, vtable+88) returns whether the
object's +24 word is zero. The constructor writes +24 = 0; no class
method writes it after that; the word is owned by an external
completion path. Run 333's trajectory: +24 = 1 during the wait, 0
when the wait completed (the handler exited clean), then 4,
frozen: four more units of work registered against the shared
device object and never drained.

Batch 302's pump counters answered their pre-registered
trichotomy with branch 1: after the wedge the peer pump is never
entered again. Host stacks put the main thread asleep in
VIWaitForRetrace. UPDATE 28's circular-wait model (retraces only
advance on presents) was retracted in UPDATE 29: a wall-clock
retrace path advances ~61 retraces per second deep into the
freeze, thousands of wakes fire into the VI queue, and the
presenter never leaves its wait, with the suspend branch
eliminated by [w233] (susp=0 in every sample). UPDATE 30 unified
the layers on mined evidence: the only [w276] lines in runs
332-334 are a single burst at the attract-to-frontend transition,
with the running-context word holding spray values while the
presenter tried to sleep on the VI queue; both layers are one root
event, a guest bulk write during the frontend reload streaming
data values across low OS structures.

Run 336 (batch 303) corrected the frozen presenter's state (its
TCB reads RUNNING and current while the host sleeps in the idle
loop) and named the writer. The page shield's [w256] catches log
the spray in the act: guest active = the movie glue fn_800B9558,
lr inside BinkCopyToBufferRect. The values written are frame
pixels. Every manifestation in the brief is downstream of the
movie frame copy.

Desk work closed the mechanism (UPDATEs 32-35). Rect contains no
pixel loop: it clips, applies the standard negative-pitch fixup,
and dispatches to a copier; the trampoline and the direct caller
fn_802D5488 are faithful to the original bytes (the caller's
pre-adjust and Rect's fixup cancel by design). Batch 304 (run 337)
caught the offending call: dest = 0x00000020, every other argument
identical to the sane calls (dest 0x80DA4640, pitch 2560, 640x480).
Guest addresses resolve through a 32 MiB MEM1 window mask, so a
destination of 0x20 is offset 0x20 in that window, the same backing
bytes as 0x80000020: the faithful copy writes ~1.2 MB of frame
pixels over physical offsets 0x20..0x12C020, the context words,
the fake module-list head at 0x30C8, thread-list links and low OS
structures. Batch 305 (run 338) showed bad-destination calls are
not rare (the 60-print cap filled, all dest=0x20 through the same
wrapper object). The destination is not read from the wrapper's
object: a virtual provider method, fn_802D5D18, fills the buffer
from a surface object reached through two virtual hops, dest =
[surface+80], pitch = [surface+72]. Batch 307 (run 340) dumped the
surface: a shared static GX descriptor at guest 0x8042E2A8 (width
640, height 480, depth 32, pitch 2560 at +72, pixel pointer at
+80). Both states captured: good calls read +80 = the framebuffer,
with +88/+92/+96 = 0/0/0; from call ~775 onward +80 = 0x00000020
(the descriptor's own +8 value) and +88/+92/+96 = 0xA0/0x78/8. The
descriptor is reconfigured in place mid-run with a small-surface
field set while the movie code keeps reading +80 as its frame
destination.

Two shield attempts failed on mechanism, not on diagnosis. Batch
308 (run 341) added watch entries for the descriptor words, but
the shield check runs only as the completion of a page-guard write
fault and the descriptor's page was never armed. Batch 309 (run
342) armed the page (8 to 9 pages); all 220 catches were the same
boot-init transient and the flip was never caught, while bad
destinations still reached the wrapper: the flip is written
through a mapping the page guard does not cover. Batches 308/309
reverted.

Batch 310 corrects the value at the point of use, the batch 282
family: in fn_802D5D18, the read of [surface+80] passes through
host helper CttrFixDest310, which tracks the last in-window
destination ([0x80000000, 0x81800000)) and substitutes it whenever
the read falls outside the window, logging [w310] per correction
(cap 40).

### Runs 343/344 (Nov 9): layer 2 closed

Run 343 (batch 310) completed the full 1800 s soak: MAX BINK
25,912 (wedged runs: ~1,000), counters still advancing at harvest,
[w256] shield catches 0 and [w282] gate heals 0 for the entire run
(no spray reached any monitored word), [w310] at its 40-print cap,
each correction 0x00000020 to the run's real framebuffer
(0x80DB1340 this run, confirming the last-good design over a
hardcoded address). Handlers balanced end to end. Run 344 (same
exe, no rebuild) passed again and overshot to ~3,108 s guest time:
MAX BINK 27,958 and climbing, zero catches, zero heals. Two
consecutive full passes on one build: the stability bar is met
and layer 2 is closed.

Two readings corrected for the record. First, disp = 161 alone is
not a death signature: with the pump trickling and the movie
playing to the end, 161 is the attract loop's steady state after
loading drains. The death signature was the combination (161 plus
frozen pump plus frozen bink plus spray). Second, the visual
baseline: wedged runs showed white with black bars top and bottom
after the rotating squares; in 343/344 the picture area between
the bars filled with static. The static is the attract movie
playing into the visible buffer without colour conversion, a
separate later problem; the white was the wedge.

The descriptor flip's writer remains unidentified. It is parked:
harmless since batch 310, off the critical path. Page-guard
shielding cannot intercept it (run 342), so identifying it needs
a different instrument if it is ever reopened.

### Runs 345/346 (Nov 9): first input; the frontend Sprite crash

Direction picked Nov 9: menus and gameplay past the attract loop
via input, ahead of movie colour conversion. Run 345 was the first
input run (batch-310 exe; CTTR_PAD_SKIP=1 presses A then Start at
boot, CTTR_PAD_PULSE=1 pulses Start every 15 s). The attract phase
ran normally to ~330 s, the frontend then rendered for ~100 s, and
the run crashed on a frontend Menu draw. The first report (access
violation at 0xFFFFFFFF) was wrong: the fatal is a missing_target,
InvokeIndirectCpu tried to execute guest address 0. The chain:
Menu draw (fn_801C9FCC) to Text draw (fn_801CE4D0), block
loc_801CE568, which loads the Text's selected element from
[Text+132], reads its vtable, takes slot +96 into CTR and calls
it. CTR was 0 because the element's first word was pixel data
(0x11111111). The crash Text is 0x80FA4CF0, child index 1 of Menu
0x80FA4BA8; its +132 held 0x80E5CE38.

The first model (45 of 226 Texts carrying a raw image pointer at
+132 where a Sprite belongs) was tested with batch 311, a
three-stage witness with no behaviour change: [w311a] at the
loader append (fn_801CE840, right after the inventory Find),
[w311r] at the resolver store (fn_801CE5C8), [w311d] at the Draw
block head for non-Sprite elements. Run 346 crashed identically
(same Text, same element address, same LR) and the witness settled
it:

- Appends: 536, covering 226 Texts and 174 distinct Sprites.
  Every Find result was a genuine Sprite (vtable 0x803DF7A4). The
  loader is clean; there is no raw append.
- Resolves: 127, every one a genuine Sprite. SetIndex never copied
  a raw pointer.
- Poisoned draws: exactly 1, the crash. At draw time the Text's
  vector and +132 still held the correct pointer; the pointee's
  first word had become pixel data.
- The crash Sprite's paper trail is two consecutive witness lines:
  appended once (n=251) and resolved once (n=36), vtable correct
  both times. Alive at load, alive at resolve, dead at draw.

Census of run 346's snapshot over the 174 appended Sprites: 96
alive, 78 dead. The dead form a contiguous span, 0x80E0A478 to
0x80EDCF98 (every appended Sprite in the range dead, ~0x2270
stride, the frontend package's in-place object layout; alive again
from 0x80EDD828), plus a second contiguous run at
0x80DC39D8-0x80DF9FE8. Run 345's 18 "raw buffers" are the same dead
Sprites (0x80E1F1F8 resolved alive in 346). Current best mechanism
statement: during the frontend phase, texture data is written
across a ~1.4 MB contiguous span of the frontend package's object
region, destroying every Sprite object in the span in place.
Texts keep correct pointers to dead objects; the first Draw
through one dies. The writer is one of: a Pure3D texture
conversion landing on a wrong destination, the package spool
being reused for textures while its objects are still referenced,
or a host GX-bridge upload computing a wrong guest destination.

### What remains, in order

1. Catch the frontend writer (batch 312 candidate): a flip-watch
   poller on the deterministic victim span (the same addresses
   died in 345 and 346), sampling the crash Sprite and span
   neighbours each tick and dumping guest fiber stacks on the
   vtable-to-pixel transition. If guest stacks show nothing, the
   writer is host-side: a range watch in the GX bridge upload path
   on the victim span.
2. Fix at the source once the writer is named (wrong destination,
   arena bound, or spool lifetime), proven by a pulse run that
   survives the frontend plus a soak. Fallback, only if the writer
   stays elusive and only on Brandon's call: a batch-310-style
   point-of-use guard in Text Draw/SetIndex that skips elements
   whose vtable is not the Sprite vtable. Menus would render with
   the dead Sprites' images missing but stop crashing.
3. After the frontend survives: Bink colour conversion, then
   input-driven menu navigation testing and gameplay entry.
4. Parked: the descriptor-flip writer (harmless since batch 310);
   Phase 5 disposal of the generated/ leftovers; the diagnostic
   cleanup decision (the witness batches' permanent form, flood
   caps, mock-tree trashing). The last two are Brandon's calls.
