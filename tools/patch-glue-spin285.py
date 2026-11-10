# Batch 285 (CTTR diagnostic): extend the glue spin
# witness with the helper object's internals.
#
# Run 317's [w284] named the spinning call: the glue
# loop's virtual target fn_80242B9C thunks to
# fn_80239F04 on sub = [obj+12]. That function makes two
# vtable calls on the embedded helper at sub+12 (slots
# +8 and +12, this = sub+12) and returns the flag byte
# at [sub+84]; the glue loops while it is 0. In the
# wedge the calls return instantly (spin burst), then
# one blocks forever in OSWaitSemaphore.
#
# Host-side only: CttrGlueSpin284 already receives obj.
# This patch widen its log line to [w285], adding sub,
# the helper's vtable word hw = [sub+12], the two call
# targets v8 = [hw+8] / v12 = [hw+12], the flag byte
# f84 = [sub+84], and the GOD semaphore Q's count and
# pending words (Q = 0x80B954A8; count at +1612,
# pending at +1664) sampled at spin detection, which
# separates "waits consume real posts" from "waits
# never engage Q".
#
# One file: os_init.cpp. Anchor is the batch 284 block
# verbatim; aborts unless it appears exactly once.
# Idempotent via the "Batch 285" marker; backup
# .bak-pre285. Honours CTTR_ROOT.

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled"))
MARKER = "Batch 285"
OSI = ROOT / "runtime" / "src" / "hle" / "os" / "os_init.cpp"

ANCHOR = '''    uint32_t vt = 0, slot = 0;
    try {
        vt = ::Memory::Read32(obj);
        slot = ::Memory::Read32(vt + 120u);
    } catch (...) {}
    FILE* f = fopen("cttr-witness.txt", "a");
    if (f) {
        fprintf(f, "[w284] spin obj=0x%08X target=0x%08X ret=%u vt=0x%08X slot=0x%08X calls=%llu win=%llu\\n",
                obj, target, ret, vt, slot,
                s_calls284.load(), wc);
        fclose(f);
    }
'''

REPL = '''    uint32_t vt = 0, slot = 0;
    // Batch 285: also read the helper object's internals
    // (fn_80239F04's two vtable calls and its exit flag)
    // and Q's count/pending at spin detection time.
    uint32_t sub = 0, hw = 0, v8 = 0, v12 = 0;
    uint32_t f84 = 0xFFFFFFFFu, qcnt = 0xFFFFFFFFu, qpend = 0xFFFFFFFFu;
    try {
        vt = ::Memory::Read32(obj);
        slot = ::Memory::Read32(vt + 120u);
        sub = ::Memory::Read32(obj + 12u);
        hw = ::Memory::Read32(sub + 12u);
        v8 = ::Memory::Read32(hw + 8u);
        v12 = ::Memory::Read32(hw + 12u);
        f84 = ::Memory::Read8(sub + 84u);
        qcnt = ::Memory::Read32(0x80B95AF4u);
        qpend = ::Memory::Read32(0x80B95B28u);
    } catch (...) {}
    FILE* f = fopen("cttr-witness.txt", "a");
    if (f) {
        fprintf(f, "[w285] spin obj=0x%08X target=0x%08X ret=%u vt=0x%08X slot=0x%08X sub=0x%08X hw=0x%08X v8=0x%08X v12=0x%08X f84=%u qcnt=%u qpend=%u calls=%llu win=%llu\\n",
                obj, target, ret, vt, slot, sub, hw, v8, v12, f84, qcnt, qpend,
                s_calls284.load(), wc);
        fclose(f);
    }
'''


def main() -> int:
    if not OSI.is_file():
        print(f"ABORT missing file: {OSI}")
        return 1
    text = OSI.read_text(encoding="utf-8", errors="strict")
    if MARKER in text:
        print("ALREADY: batch 285 present")
        return 0
    n = text.count(ANCHOR)
    if n != 1:
        print(f"ABORT anchor count {n} (need 1)")
        return 1
    bak = OSI.with_name(OSI.name + ".bak-pre285")
    if not bak.exists():
        shutil.copy2(OSI, bak)
    OSI.write_text(text.replace(ANCHOR, REPL), encoding="utf-8")
    print(f"patched {OSI.name} (backup {bak.name})")
    print("OK batch 285 applied")
    return 0


if __name__ == "__main__":
    sys.exit(main())
