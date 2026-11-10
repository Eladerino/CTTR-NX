# Batch 249 (diagnostics): sample the fn_8023A700 queue object Q in
# the active era, on the [w212] heartbeat next to batch 248's [w248].
#
# fn_8023A700 (decoded Nov 6) enqueues onto Q = word at [inner+184]
# (inner GOD object 0x80B93A44): per-channel intrusive lists with
# heads at Q+1624+chan*4 and tails at Q+1636+chan*4, a pending
# counter at Q+1664, and a signal word at Q+1612 (fn_8024C95C).
# Batch 248 sampled dev76+184, which is NOT this object. This batch
# prints Q's pointer, signal, channel-0/1 heads, channel-0 tail,
# pending counter, and (when the head is a plausible MEM1 pointer)
# the head node's first two words.
#
# Pure ASCII. Anchor verified count==1; .bak-pre249; idempotent.

import os
import shutil
import sys

ROOT = os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled")
MARKER = "Batch 249"
REL = r"runtime\src\hle\os\os_init.cpp"

ANCHOR = '::Memory::Read32(0x80B92558u + 84u));  // Batch 248'

INSERT = ANCHOR + (
    '\n            { const uint32_t qp249 = ::Memory::Read32(0x80B93A44u + 184u); const bool qok249 = (qp249 >= 0x80000000u && qp249 < 0x81800000u); const uint32_t qh249 = qok249 ? ::Memory::Read32(qp249 + 1624u) : 0u; const bool hok249 = (qh249 >= 0x80000000u && qh249 < 0x81800000u); fprintf(f, "[w249] qp=%08X q1612=%08X q1624=%08X q1628=%08X q1636=%08X q1664=%08X qh0=%08X qhn=%08X\\n", qp249, qok249 ? ::Memory::Read32(qp249 + 1612u) : 0u, qh249, qok249 ? ::Memory::Read32(qp249 + 1628u) : 0u, qok249 ? ::Memory::Read32(qp249 + 1636u) : 0u, qok249 ? ::Memory::Read32(qp249 + 1664u) : 0u, hok249 ? ::Memory::Read32(qh249) : 0u, hok249 ? ::Memory::Read32(qh249 + 4u) : 0u); }  // Batch 249'
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
    shutil.copyfile(path, path + ".bak-pre249")
    text = text.replace(ANCHOR, INSERT, 1)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)
    print("PATCHED:", REL)
    print("batch 249 applied")


if __name__ == "__main__":
    main()
