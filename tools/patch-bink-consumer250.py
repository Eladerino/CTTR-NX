# Batch 250 (diagnostics): identify the Bink IO queue consumer.
#
# Run 280 showed posts to Q (the message queue at [inner+184])
# draining promptly all run, then 4 posts stranding at the freeze
# with the semaphore count (Q+1612) at 4. Q+1612 is an OS semaphore
# (fn_8024C95C -> OSSignalSemaphore). This batch extends the
# heartbeat with the semaphore's wait queue (head Q+1616, tail
# Q+1620) and, when the head is a plausible MEM1 pointer, the
# waiting thread's TCB fields (state +0x2C8, prio +0x2D0, resume
# +0x198, suspend +0x2CC, queue +0x2DC). It also prints the movie
# glue thread 0x80B957D8's state/resume for cross-checking.
#
# Pure ASCII. Anchor verified count==1; .bak-pre250; idempotent.

import os
import shutil
import sys

ROOT = os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled")
MARKER = "Batch 250"
REL = r"runtime\src\hle\os\os_init.cpp"

ANCHOR = 'hok249 ? ::Memory::Read32(qh249 + 4u) : 0u); }  // Batch 249'

INSERT = ANCHOR + (
    '\n            { const uint32_t qp250 = ::Memory::Read32(0x80B93A44u + 184u); const bool qok250 = (qp250 >= 0x80000000u && qp250 < 0x81800000u); const uint32_t sh250 = qok250 ? ::Memory::Read32(qp250 + 1616u) : 0u; const bool sok250 = (sh250 >= 0x80000000u && sh250 < 0x81800000u); fprintf(f, "[w250] sh=%08X st=%08X cstate=%08X cprio=%08X cres=%08X csusp=%08X cqueue=%08X bstate=%08X bres=%08X\\n", sh250, qok250 ? ::Memory::Read32(qp250 + 1620u) : 0u, sok250 ? ::Memory::Read32(sh250 + 712u) : 0u, sok250 ? ::Memory::Read32(sh250 + 720u) : 0u, sok250 ? ::Memory::Read32(sh250 + 408u) : 0u, sok250 ? ::Memory::Read32(sh250 + 716u) : 0u, sok250 ? ::Memory::Read32(sh250 + 732u) : 0u, ::Memory::Read32(0x80B957D8u + 712u), ::Memory::Read32(0x80B957D8u + 408u)); }  // Batch 250'
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
    shutil.copyfile(path, path + ".bak-pre250")
    text = text.replace(ANCHOR, INSERT, 1)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)
    print("PATCHED:", REL)
    print("batch 250 applied")


if __name__ == "__main__":
    main()
