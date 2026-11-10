# Batch 225 (CTTR diagnostic): host stack trace
# in the missing-target fatal handler.
#
# Batch 223 (run 251/252) proved the ambient
# guest context cannot name the caller of the
# fatal InvokeIndirectCpu (target 0x70757265):
# the tracker holds the outermost dispatch
# (VIWaitForRetrace) and ctx->lr is stale. The
# sibling missing-JUMP-target path in
# abi_bridge.h already calls
# DumpHostStackTraceForRuntimeHelper() (defined
# in main.cpp) before exiting; the missing-CALL
# path (RuntimeCrash::FatalMissingGuestTarget)
# does not. Batch 225 adds that one call right
# after the Batch 223 witness block, so the
# console log gains the native host stack of
# the exact call site -- resolvable against a
# symbol dump of the exe (llvm-nm).
#
# Runtime-only (main.cpp), no emit. Idempotent
# via the "Batch 225" marker; backup
# .bak-pre225. Honours CTTR_ROOT.

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled"))
MARKER = "Batch 225"
MAIN = ROOT / "runtime" / "src" / "main.cpp"

EDITS = [
    (
        "    if (RuntimeFrontend::Active()) {\n"
        "        std::ostringstream error;\n"
        "        error << \"Missing guest function 0x\" << std::hex << target << \" (LR 0x\" << (cpu ? cpu->lr : 0) << \")\";\n"
        "        RuntimeFrontend::Fail(error.str().c_str());\n"
        "    }",
        "    DumpHostStackTraceForRuntimeHelper();  // Batch 225: name the native caller of the fatal invoke\n"
        "    if (RuntimeFrontend::Active()) {\n"
        "        std::ostringstream error;\n"
        "        error << \"Missing guest function 0x\" << std::hex << target << \" (LR 0x\" << (cpu ? cpu->lr : 0) << \")\";\n"
        "        RuntimeFrontend::Fail(error.str().c_str());\n"
        "    }",
        1,
    ),
]


def fail(msg):
    print("FAIL:", msg)
    sys.exit(1)


def main():
    if not MAIN.exists():
        fail(f"missing file: {MAIN}")
    text = MAIN.read_text()
    if MARKER in text:
        print("already applied, skipping")
        return
    for idx, (old, new, want) in enumerate(EDITS):
        got = text.count(old)
        if got != want:
            fail(f"main.cpp edit {idx}: anchor count {got} != {want}")
        text = text.replace(old, new, 1)
    backup = MAIN.with_name(MAIN.name + ".bak-pre225")
    if not backup.exists():
        shutil.copy2(MAIN, backup)
    MAIN.write_text(text)
    print("patched: main.cpp")
    print("Batch 225 applied (runtime-only, no emit).")


if __name__ == "__main__":
    main()
