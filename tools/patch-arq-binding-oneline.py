import re
import sys
from pathlib import Path

# Batch 33: ARStartDMA (0x803550B0) dispatches to the translated guest
# body even though audio.cpp already contains a complete native impl,
# ARQTransfer_CTTR, bound at that address -- the console-35 run faulted
# inside the guest body (read of 0xCC005020, __DSPRegs[16]) and the
# impl's first-transfer log line never appeared.
#
# Established by diagnostics (Nov 4, 2026):
# - The generated call site in __ARQServiceQueueLo is
#   InvokeDirectCpu<0x803550B0u>(ctx), IDENTICAL in form to the working
#   AIInitDMA call site -- codegen is not the differentiator; the
#   runtime dispatch resolved this address to the translated function.
# - The binding is the ONLY multi-line PPC_NATIVE_OVERRIDE in the
#   file (audio.cpp:817-820, spread over four lines); every working
#   binding is a single line. The translator builds each override's
#   ABI thunk from the signature scans in GeneratedMarkers.cs (the
#   full-statement pattern and the void-arguments pattern); a binding
#   those scans cannot read produces no native thunk, and
#   InvokeDirectCpu silently falls back to the translated body.
# - Baseline from cttr-translate-32.log: "Native guest-effect
#   contracts: 374 total, 248 precise, 126 full-context."
#
# Fix: join the binding onto ONE line, macro and arguments unchanged.
# The batch-33 run gates on the contracts count rising (374 -> 375
# total and/or 248 -> 249 precise) after retranslation; if it does
# not move, this theory is wrong and the run stops before building.

path = Path(sys.argv[1] if len(sys.argv) > 1 else r"runtime\src\hle\audio\audio.cpp")
src = path.read_text(encoding="utf-8")

single = ("PPC_NATIVE_OVERRIDE_VOID(803550B0, ARQTransfer_CTTR, "
          "(uint32_t direction, uint32_t mainMemoryAddress, "
          "uint32_t aramAddress, uint32_t byteCount), "
          "(direction, mainMemoryAddress, aramAddress, byteCount));")

if single in src:
    print("already patched:", path)
    sys.exit(0)

pattern = re.compile(
    r"PPC_NATIVE_OVERRIDE_VOID\(803550B0,\s*ARQTransfer_CTTR,.*?byteCount\)\);",
    re.DOTALL)
matches = pattern.findall(src)
if len(matches) != 1:
    print("ANCHOR PROBLEM: multi-line ARQTransfer bindings found =", len(matches))
    sys.exit(1)

src = pattern.sub(single, src, count=1)
path.write_text(src, encoding="utf-8")
print("patched:", path, "(ARQTransfer_CTTR binding joined to one line)")
