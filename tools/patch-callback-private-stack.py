# Batch 186 (CTTR fix candidate): private guest stacks for
# deferred callback contexts.
#
# GuestInterruptCallbackContext (runtime/include/
# guest_interrupt_context.h) seeds its fabricated context
# with a full copy of the interrupted guest thread's
# registers -- including gpr[1], its LIVE stack pointer.
# The deferred services (VI retraces, alarms, audio ticks,
# ARQ completions) then run unbounded guest callback
# chains on that stack: same-thread at the pump sites,
# CONCURRENTLY on the ARQ poller thread (batch 38, proven
# load-bearing by run 211) and the Aurora/GX worker
# threads. A chain's frames land on whatever stack region
# the interrupted thread later reuses; run 203 proved the
# Bink descriptor slot flipped to a sound chain's frame
# content between two adjacent flat reads at the identical
# guest address, and runs 185-210 show the whole family
# (descriptor slot, dispatcher object, io4 callback,
# checksound target) taking turns as the victim.
#
# Fix: keep the register seed, but replace gpr[1] with a
# private stack. Slots are 8 x 256 KB of backed MEM2
# above the game's arena and the runtime's published FST
# (0x97E00000..0x98000000), handed out round-robin by a
# single shared counter defined in os_init.cpp
# (CttrCallbackStackTop), which also witness-logs the
# first 60 fabrications ([w186], seed SP -> slot top).
# A chain runs to completion synchronously, so a slot is
# only reused after 8 further chains have run.
#
# Two files: guest_interrupt_context.h (declaration +
# gpr[1] override at the seed) and
# runtime/src/hle/os/os_init.cpp (the allocator).
# Idempotent via the "Batch 186" marker; backups
# .bak-pre186. Runtime-only change: no emit needed.
# Honours CTTR_ROOT.

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled"))
MARKER = "Batch 186"
HDR = ROOT / "runtime" / "include" / "guest_interrupt_context.h"
OSI = ROOT / "runtime" / "src" / "hle" / "os" / "os_init.cpp"

HDR_OLD1 = "class GuestInterruptCallbackContext {"
HDR_NEW1 = """// Batch 186: shared private-stack allocator for deferred callback
// contexts; defined in os_init.cpp. Returns the guest stack top a
// fabricated callback context should run on instead of the
// interrupted thread's live stack pointer.
uint32_t CttrCallbackStackTop(uint32_t seedSp);

class GuestInterruptCallbackContext {"""

HDR_OLD2 = """        const CpuContext* interrupted = TryGetCpuContext();
        return interrupted != nullptr ? *interrupted : GetPersistentCpuContext();"""
HDR_NEW2 = """        const CpuContext* interrupted = TryGetCpuContext();
        CpuContext seed = interrupted != nullptr ? *interrupted : GetPersistentCpuContext();
        // Batch 186: keep the interrupted thread's register seed, but
        // NOT its stack pointer. These chains run unbounded guest
        // code (whole GOD completions), at the pump sites mid-frame
        // and concurrently on the poller/worker threads; on the live
        // stack their frames land on regions the interrupted thread
        // later reuses -- the mechanism behind the Bink priming
        // stack-slot flips (runs 185-210). Run each chain on a
        // private stack slot instead.
        seed.gpr[1] = CttrCallbackStackTop(seed.gpr[1]);
        return seed;"""

OSI_OLD = 'extern "C" void CttrNameWitness(int what, uint32_t aux, uint32_t lr, uint32_t strGuest) {'
OSI_NEW = """// Batch 186: private guest stacks for deferred callback contexts
// (GuestInterruptCallbackContext). Slots live in backed MEM2 above
// the game's arena and the runtime's published FST: 8 x 256 KB at
// 0x97E00000..0x98000000, handed out round-robin. A chain runs to
// completion synchronously, so a slot is only reused after 8
// further chains have run.
uint32_t CttrCallbackStackTop(uint32_t seedSp) {
    static std::atomic<uint32_t> s_slot{0};
    static std::atomic<int> s_logged{0};
    const uint32_t slot = s_slot.fetch_add(1, std::memory_order_relaxed) % 8u;
    const uint32_t top = 0x97E00000u + (slot + 1u) * 0x00040000u - 16u;
    if (s_logged.fetch_add(1, std::memory_order_relaxed) < 60) {
        FILE* f = fopen("cttr-witness.txt", "a");
        if (f) {
            fprintf(f, "[w186] cb stack slot=%u top=0x%08X seedSp=0x%08X\\n", slot, top, seedSp);
            fclose(f);
        }
    }
    return top;
}

""" + OSI_OLD


def fail(msg):
    print("FAIL:", msg)
    sys.exit(1)


def patch(path, pairs):
    text = path.read_text()
    if MARKER in text:
        print(f"{path.name}: already applied, skipping")
        return
    for old, _new in pairs:
        c = text.count(old)
        if c != 1:
            fail(f"{path.name}: anchor count {c} != 1 for {old[:60]!r}")
    for old, new in pairs:
        text = text.replace(old, new, 1)
    backup = path.with_name(path.name + ".bak-pre186")
    if not backup.exists():
        shutil.copy2(path, backup)
    path.write_text(text)
    print(f"patched: {path.name}")


def main():
    for p in (HDR, OSI):
        if not p.exists():
            fail(f"missing file: {p}")
    patch(HDR, [(HDR_OLD1, HDR_NEW1), (HDR_OLD2, HDR_NEW2)])
    patch(OSI, [(OSI_OLD, OSI_NEW)])
    print("Batch 186 applied.")


if __name__ == "__main__":
    main()
