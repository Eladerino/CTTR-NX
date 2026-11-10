#!/usr/bin/env python3
# Batch 155 (FIX): deliver OS-thread wakeups that batch 150's gate
# deferred while the GOD completion-dispatcher fiber was resident.
#
# Evidence (runs 172-173): the startup.god wrapper's ctor posts its
# load job from inside the dispatcher fiber and OSSignalSemaphore
# wakes loader thread 0x80B957D8 (priority 2; the running thread is
# priority 15). Batch 150's SelectThread gate returns the designed
# no-switch (w91, exactly once) and the loader stays READY in the
# run queue with the reschedule hint (0x804AEA7C) set -- in both
# t=25 s and t=40 s snapshots, unchanged. Nothing ever picks it up:
# RunDeferredReschedule (ProcessAlarmQueue's tail) only runs when
# the alarm queue handled a completion, CTTR's steady state produces
# no completions, and the per-frame pumps (main.cpp, GX, VI pacing)
# use the deferred private-context variants that suppress switches
# by design. 28 job posts vs 27 dequeues; the 28th job -- the one
# that would read startup.god's payload -- never executes.
#
# Fix: GX__CopyDisp (guest-called once per presented frame, live
# context, home block resident) calls CttrFlushDeferredReschedule,
# a thin exported wrapper over the existing RunDeferredReschedule:
# it no-ops unless the reschedule hint is set, skips deterministic
# mode, and lets SelectThread re-apply its own guards (dispatcher
# gate, scheduler-disable count, priority rules). Also grants the
# w95 god-witness a cap of 120 so flushes are visible in the log.
#
# Idempotent via "Batch 155" marker per file. Backups: .bak-pre155.
# CTTR_ROOT env override for mock testing.
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled"))
MARKER = "Batch 155"


def patch(relpath, edits):
    target = ROOT / relpath
    text = target.read_text(encoding="utf-8", errors="strict")
    if MARKER in text:
        print(f"{relpath}: batch 155 already applied; skipped")
        return
    for anchor, _rep in edits:
        n = text.count(anchor)
        if n != 1:
            print(f"FATAL: {relpath} anchor found {n} times (need exactly 1); no writes made")
            sys.exit(1)
    backup = target.with_name(target.name + ".bak-pre155")
    if not backup.exists():
        shutil.copy2(target, backup)
        print(f"backup written: {backup}")
    for anchor, rep in edits:
        text = text.replace(anchor, rep)
    target.write_text(text, encoding="utf-8")
    print(f"{relpath}: batch 155 applied")


ALARM = Path("runtime") / "src" / "hle" / "os" / "os_alarm.cpp"
A_ALARM = "} // namespace\n\nnamespace OsHleInternal {"
R_ALARM = """} // namespace

// Batch 155: frame-boundary flush for deferred OS reschedules.
// Batch 150's SelectThread gate keeps a wakeup queued when it fires
// while the GOD completion-dispatcher fiber is resident, expecting
// a later SelectThread to pick it up; in CTTR's steady state none
// runs (the alarm tail above only flushes after a completion, and
// the per-frame pumps use the switch-suppressed deferred variants),
// so the woken thread starves with the reschedule hint set forever.
// GX__CopyDisp calls this once per presented frame on the live
// context. RunDeferredReschedule applies the usual guards (no flush
// while a retrace advance is in flight) and SelectThread re-checks
// the dispatcher gate, the scheduler-disable count and priorities.
extern "C" void CttrGodWitness(int what, uint32_t a, uint32_t b);  // Batch 155 (defined in os_init.cpp)

extern "C" void CttrFlushDeferredReschedule()
{
    if (DetClock::Enabled()) {
        return;
    }
    if (::Memory::Read32(kSchedulerReschedCounterAddr) == 0) {
        return;
    }
    CpuContext* cpu = TryGetCpuContext();
    if (!cpu) {
        cpu = &GetPersistentCpuContext();
    }
    CttrGodWitness(95, ::Memory::Read32(kSchedulerReschedCounterAddr),
                   ::Memory::Read32(kSchedulerPendingFlagAddr));  // Batch 155
    RunDeferredReschedule(cpu);
}

namespace OsHleInternal {"""
patch(ALARM, [(A_ALARM, R_ALARM)])

GX = Path("runtime") / "src" / "hle" / "gx" / "gx_copy.cpp"
A_GX1 = 'extern "C" void GX__CopyDisp_8016fc38(uint32_t da, uint32_t c) {'
R_GX1 = """extern "C" void CttrFlushDeferredReschedule();  // Batch 155 (defined in os_alarm.cpp)

extern "C" void GX__CopyDisp_8016fc38(uint32_t da, uint32_t c) {"""
A_GX2 = "    VI_HLE_PresentFrame(/*presentedXfb=*/true, /*paceToRetrace=*/true);\n}"
R_GX2 = """    VI_HLE_PresentFrame(/*presentedXfb=*/true, /*paceToRetrace=*/true);
    // Batch 155: the frame is presented and paced; deliver any OS-thread
    // wakeup deferred while the GOD dispatcher fiber was resident, so
    // queued loader threads run between frames (see os_alarm.cpp).
    CttrFlushDeferredReschedule();
}"""
patch(GX, [(A_GX1, R_GX1), (A_GX2, R_GX2)])

INIT = Path("runtime") / "src" / "hle" / "os" / "os_init.cpp"
A_INIT = "200};  // Batch 150 (adds what 91 SelectThread dispatcher gate)"
R_INIT = ("200, 0, 0, 0, 120};  // Batch 155 (adds what 95 frame-boundary reschedule flush; "
          "ids 92-94 stay capped 0 -- the batch 153 name witness keeps its own table) "
          "+ Batch 150 (adds what 91 SelectThread dispatcher gate)")
patch(INIT, [(A_INIT, R_INIT)])

print("batch 155 done")
