# Batch 230: AdvanceRetrace guard hardening (runtime/src/hle/vi.cpp).
#
# Run 257 evidence: during the attract movie, a guest-memory access inside
# AdvanceRetrace faults on every pass (720 AccessViolation dumps in
# console-257.log, addr = streamed pixel data). Host stack of the fault:
# VIWaitForRetrace_HLE -> OSSleepThread_HLE -> SelectThreadSwitch ->
# AdvanceDueRetraces -> AdvanceRetrace -> WriteFloat32Slow -> GetPointer.
# At the freeze (~335 s) retraces stop entirely ([w119] ends) while the
# fault dumps keep repeating: the retrace never completes. The re-entry
# guard s_inAdvanceRetrace is set by exchange at entry and cleared ONLY by
# the store at the bottom of the function, so any exception unwinding out
# of the body latches it true forever and every later retrace no-ops.
#
# This batch:
#  1. Adds an RAII scope guard right after the exchange so the flag clears
#     on EVERY exit path (normal, early return, exception).
#  2. Wraps the body in try/catch: an AccessViolation is logged to the
#     witness as [w230] with the fault address and a phase marker instead
#     of unwinding into the scheduler / VI wait paths.
#  3. Plants phase markers (s_phase230) at the body's stages so the [w230]
#     log names the faulting stage in run 258.
#
# Idempotent via the "Batch 230" marker. Backup: .bak-pre230.
import os
import sys

ROOT = os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled")
PATH = os.path.join(ROOT, "runtime", "src", "hle", "vi.cpp")

with open(PATH, "r", errors="strict") as f:
    orig = f.read()

if "Batch 230" in orig:
    print("batch 230 already applied")
    sys.exit(0)

EDITS = []

# E1: phase counter next to the guard declaration.
EDITS.append((
    "static std::atomic<bool> s_inAdvanceRetrace{false};",
    "static std::atomic<bool> s_inAdvanceRetrace{false};\n"
    "static std::atomic<int> s_phase230{0};  // Batch 230: AdvanceRetrace stage marker for the [w230] fault log",
))

# E2: RAII guard reset + open the try block right after the re-entry guard.
EDITS.append((
    "    if (s_inAdvanceRetrace.exchange(true)) {\n"
    "        return;\n"
    "    }",
    "    if (s_inAdvanceRetrace.exchange(true)) {\n"
    "        return;\n"
    "    }\n"
    "    // Batch 230: clear the re-entry guard on EVERY exit path. Before this\n"
    "    // batch, an exception out of a guest-memory access inside the retrace\n"
    "    // unwound past the store at the bottom and latched the guard true\n"
    "    // forever; every later AdvanceRetrace then no-opped, retraces stopped,\n"
    "    // and the frontend wedged with all guest state frozen (run 257).\n"
    "    struct CttrRetraceGuardReset230 {\n"
    "        ~CttrRetraceGuardReset230() { s_inAdvanceRetrace.store(false); }\n"
    "    } cttrRetraceGuardReset230;\n"
    "    s_phase230.store(1);\n"
    "    try {",
))

# E3: phase 2 before scene logging.
EDITS.append((
    "    LogSceneChanges();",
    "    s_phase230.store(2);  // Batch 230\n"
    "    LogSceneChanges();",
))

# E4: phase 3 before the SPM sweep tick.
EDITS.append((
    "    SpmMapSweep::Tick(ctx, s_presentedXfbFrames);",
    "    s_phase230.store(3);  // Batch 230\n"
    "    SpmMapSweep::Tick(ctx, s_presentedXfbFrames);",
))

# E5: phase 4 after the guest-state lock block (at the Batch 119 print block).
EDITS.append((
    "    {  // Batch 119 (CTTR diagnostic): retrace cadence to the witness file.",
    "    s_phase230.store(4);  // Batch 230\n"
    "    {  // Batch 119 (CTTR diagnostic): retrace cadence to the witness file.",
))

# E6: phase 5 before the retrace-queue wakeup.
EDITS.append((
    "        OSWakeupThread_HLE_801aaaa4(ctx);",
    "        s_phase230.store(5);  // Batch 230\n"
    "        OSWakeupThread_HLE_801aaaa4(ctx);",
))

# E7: phase 6 before the pre/post retrace callbacks.
EDITS.append((
    "        if (preCb) {",
    "        s_phase230.store(6);  // Batch 230\n"
    "        if (preCb) {",
))

# E8: phase 7 before the XFB present.
EDITS.append((
    "            VI_HLE_PresentFrame(shouldPresentXfb, false);",
    "            s_phase230.store(7);  // Batch 230\n"
    "            VI_HLE_PresentFrame(shouldPresentXfb, false);",
))

# E9: close the try with witness-logging catches before the function end.
EDITS.append((
    "    RuntimeFrontend::RequestSuspendAtVI();\n"
    "}",
    "    RuntimeFrontend::RequestSuspendAtVI();\n"
    "    } catch (const ::Memory::AccessViolation& e230) {  // Batch 230\n"
    "        static int s_w230 = 0;\n"
    "        if (++s_w230 <= 60) {\n"
    "            if (FILE* tf = fopen(\"cttr-witness.txt\", \"a\")) { fprintf(tf, \"[w230] retrace AV addr=0x%08X len=%u phase=%d n=%d\\n\", (unsigned)e230.address(), (unsigned)e230.length(), (int)s_phase230.load(), s_w230); fclose(tf); }\n"
    "        }\n"
    "    } catch (...) {  // Batch 230\n"
    "        static int s_w230b = 0;\n"
    "        if (++s_w230b <= 60) {\n"
    "            if (FILE* tf = fopen(\"cttr-witness.txt\", \"a\")) { fprintf(tf, \"[w230] retrace unknown exception phase=%d n=%d\\n\", (int)s_phase230.load(), s_w230b); fclose(tf); }\n"
    "        }\n"
    "    }\n"
    "}",
))

src = orig
for i, (old, new) in enumerate(EDITS, 1):
    n = src.count(old)
    if n != 1:
        print("ANCHOR FAIL edit %d: count=%d" % (i, n))
        sys.exit(1)
    src = src.replace(old, new, 1)

with open(PATH + ".bak-pre230", "w") as f:
    f.write(orig)
with open(PATH, "w") as f:
    f.write(src)
print("batch 230 applied to", PATH)
