# Batch 243 (fix candidate, diagnostic-grade exit): intercept
# OSResetSystem at CTTR's own address.
#
# Evidence (runs 269/270 + generated-code decode): at the attract
# transition the frontend calls OSResetSystem (guest 0x80348F18)
# via fn_801944D8 -> fn_801946D8. The generated SDK implementation
# loops on __OSCallResetFunctions until every registered reset
# callback reports done AND the SRAM sync word at 0x8047DB0C is
# nonzero; that word is 0 in every surveyed era of this port, so
# the reset never completes and the executor thread (which runs
# every guest thread) spins inside the reset forever -- the
# "frontend freeze". The runtime's OSResetSystem HLE stub is
# registered at 0x80273B38 (an SPM address, os_reset.cpp is
# inherited from that project) and never fires here.
#
# This batch registers a CTTR override at 0x80348F18 following the
# OS__Panic CpuContext pattern in the same file: log + witness the
# request (mode/args), then take the existing clean-exit path
# (the port has no in-process guest reboot). If a run now EXITS
# at the transition instead of freezing, the mechanism is proven
# end to end and a true reboot becomes the follow-up.
#
# Pure ASCII. Anchor verified count==1; .bak-pre243; idempotent.

import os
import shutil
import sys

ROOT = os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled")
MARKER = "Batch 243"
REL = r"runtime\src\hle\os\os_reset.cpp"

ANCHOR = "PPC_NATIVE_OVERRIDE(80349244, OSSetResetCallback_CTTR, uint32_t, (uint32_t callback), (callback));"

ADD = (
    "\n"
    "\n"
    "// Batch 243 (CTTR): OSResetSystem is at 0x80348F18 in this game, not at\n"
    "// the SPM address 0x80273B38 registered above, so guest reset calls ran\n"
    "// the SDK implementation, which waits forever for its reset callbacks\n"
    "// and the SRAM sync word (0x8047DB0C, always 0 in this port). Log and\n"
    "// witness the request, then take the clean-exit path until an\n"
    "// in-process guest reboot exists.\n"
    "extern \"C\" void OSResetSystem_CTTR(CpuContext* ctx)\n"
    "{\n"
    "    const uint32_t mode243 = ctx ? ctx->gpr[3] : 0;\n"
    "    const uint32_t arg4_243 = ctx ? ctx->gpr[4] : 0;\n"
    "    const uint32_t arg5_243 = ctx ? ctx->gpr[5] : 0;\n"
    "    RT_LOGF(RT_TAG_OS, \"OSResetSystem_CTTR: mode=%u arg4=%u arg5=%u\\n\", mode243, arg4_243, arg5_243);\n"
    "    std::fflush(stderr);\n"
    "    if (FILE* wf243 = std::fopen(\"cttr-witness.txt\", \"a\")) {\n"
    "        std::fprintf(wf243, \"[w243] OSResetSystem called mode=%u arg4=%u arg5=%u\\n\", mode243, arg4_243, arg5_243);\n"
    "        std::fclose(wf243);\n"
    "    }\n"
    "    if (RuntimeFrontend::Active()) RuntimeFrontend::Fail(\"Guest requested reset\");\n"
    "    AxDspHle::ShutdownMixWorker();\n"
    "    Memory::Reset();\n"
    "    SetRuntimeExitCode(0);\n"
    "    ExitForAuroraWindowClose();\n"
    "}\n"
    "\n"
    "PPC_NATIVE_OVERRIDE_VOID(80348F18, OSResetSystem_CTTR, (CpuContext* ctx), (ctx));"
)


def main():
    path = os.path.join(ROOT, REL)
    with open(path, "r", encoding="utf-8", errors="strict") as fh:
        text = fh.read()
    if MARKER in text:
        print("SKIP (already patched):", REL)
        return
    n = text.count(ANCHOR)
    if n != 1:
        print("ABORT: anchor count %d != 1" % n)
        sys.exit(1)
    shutil.copyfile(path, path + ".bak-pre243")
    text = text.replace(ANCHOR, ANCHOR + ADD, 1)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)
    print("PATCHED:", REL)
    print("batch 243 applied")


if __name__ == "__main__":
    main()
