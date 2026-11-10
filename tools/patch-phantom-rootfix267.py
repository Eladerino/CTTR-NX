#!/usr/bin/env python3
# Batch 267: phantom root fix, implemented shape (see the design
# doc's Nov 7 implementation note):
#  - fiber_manager: SwitchToThread returns SwitchResult;
#    HasUsableFiber added.
#  - os_scheduler: gate on HasUsableFiber; both switch sites log
#    [w267] on post-commit failure and rescue via LoadContext
#    (except Deferred, which is log-only by batch 148's lesson).
# House rules: pure ASCII, anchors exactly once per file,
# .bak-pre267 backups, idempotent via the "Batch 267" marker.
import os, shutil, sys

ROOT = os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled")
HDR = os.path.join(ROOT, "runtime", "include", "fiber_manager.h")
CPP = os.path.join(ROOT, "runtime", "src", "fiber_manager.cpp")
SCHED = os.path.join(ROOT, "runtime", "src", "hle", "os", "os_scheduler.cpp")
MARKER = "Batch 267"

# ---------------- fiber_manager.h ----------------
H_OLD = ("    // Switch to a specific guest thread's fiber (called from OSLoadContext)\n"
         "    // This saves the current fiber's state and switches to the target\n"
         "    static void SwitchToThread(uint32_t guestThreadAddr, CpuContext* cpu);")
H_NEW = ("    // Batch 267: SwitchToThread reports its outcome so a caller\n"
         "    // that already committed guest bookkeeping can tell a real\n"
         "    // switch from an abandonment (deferred / no fiber / invalid).\n"
         "    enum class SwitchResult { Switched, AlreadyCurrent, Deferred, NoFiber, InvalidFiber, NotInitialized };\n"
         "\n"
         "    // Switch to a specific guest thread's fiber (called from OSLoadContext)\n"
         "    // This saves the current fiber's state and switches to the target\n"
         "    static SwitchResult SwitchToThread(uint32_t guestThreadAddr, CpuContext* cpu);\n"
         "\n"
         "    // Batch 267: record exists, handle non-null, not terminated.\n"
         "    static bool HasUsableFiber(uint32_t guestThreadAddr);")

# ---------------- fiber_manager.cpp ----------------
C_SIG_OLD = "void GuestFiberManager::SwitchToThread(uint32_t guestThreadAddr, CpuContext* cpu) {"
C_SIG_NEW = "GuestFiberManager::SwitchResult GuestFiberManager::SwitchToThread(uint32_t guestThreadAddr, CpuContext* cpu) {"
C_INIT_OLD = ("    if (!s_initialized) {\n"
              "        RT_LOG(RT_TAG_OS) << \"SwitchToThread called before initialization!\" << std::endl;\n"
              "        return;\n"
              "    }")
C_INIT_NEW = ("    if (!s_initialized) {\n"
              "        RT_LOG(RT_TAG_OS) << \"SwitchToThread called before initialization!\" << std::endl;\n"
              "        return SwitchResult::NotInitialized;  // Batch 267\n"
              "    }")
C_DEF_OLD = ("        CttrDeferSwitch(guestThreadAddr);  // Batch 149: deliver when the home block is resident again\n"
             "        return;\n"
             "    }")
C_DEF_NEW = ("        CttrDeferSwitch(guestThreadAddr);  // Batch 149: deliver when the home block is resident again\n"
             "        return SwitchResult::Deferred;  // Batch 267\n"
             "    }")
C_NOFIB_OLD = ("        if (it == s_fibers.end()) {\n"
               "            RT_LOG(RT_TAG_OS) << \"SwitchToThread: no fiber for 0x\"\n"
               "                      << std::hex << guestThreadAddr << std::dec << std::endl;\n"
               "            return;\n"
               "        }")
C_NOFIB_NEW = ("        if (it == s_fibers.end()) {\n"
               "            RT_LOG(RT_TAG_OS) << \"SwitchToThread: no fiber for 0x\"\n"
               "                      << std::hex << guestThreadAddr << std::dec << std::endl;\n"
               "            return SwitchResult::NoFiber;  // Batch 267\n"
               "        }")
C_INV_OLD = ("        if (!fiberHandle || it->second.terminated) {\n"
             "            RT_LOG(RT_TAG_OS) << \"SwitchToThread: invalid fiber for 0x\"\n"
             "                      << std::hex << guestThreadAddr << std::dec << std::endl;\n"
             "            return;\n"
             "        }")
C_INV_NEW = ("        if (!fiberHandle || it->second.terminated) {\n"
             "            RT_LOG(RT_TAG_OS) << \"SwitchToThread: invalid fiber for 0x\"\n"
             "                      << std::hex << guestThreadAddr << std::dec << std::endl;\n"
             "            return SwitchResult::InvalidFiber;  // Batch 267\n"
             "        }")
C_CUR_OLD = ("        // from before the guest thread slept.\n"
             "        return;\n"
             "    }")
C_CUR_NEW = ("        // from before the guest thread slept.\n"
             "        return SwitchResult::AlreadyCurrent;  // Batch 267\n"
             "    }")
C_END_OLD = ("            s_currentGuestThread = 0;\n"
             "        }\n"
             "    }\n"
             "}\n"
             "\n"
             "uint32_t GuestFiberManager::GetCurrentGuestThread() {")
C_END_NEW = ("            s_currentGuestThread = 0;\n"
             "        }\n"
             "    }\n"
             "    return SwitchResult::Switched;  // Batch 267\n"
             "}\n"
             "\n"
             "uint32_t GuestFiberManager::GetCurrentGuestThread() {")
C_HAS_OLD = ("bool GuestFiberManager::HasFiber(uint32_t guestThreadAddr) {\n"
             "    std::lock_guard<std::mutex> lock(s_mutex);\n"
             "    return s_fibers.count(guestThreadAddr) > 0;\n"
             "}")
C_HAS_NEW = (C_HAS_OLD + "\n"
             "\n"
             "// Batch 267: usable means the switch can actually happen:\n"
             "// a record that exists, with a live handle, not terminated.\n"
             "bool GuestFiberManager::HasUsableFiber(uint32_t guestThreadAddr) {\n"
             "    std::lock_guard<std::mutex> lock(s_mutex);\n"
             "    auto it = s_fibers.find(guestThreadAddr);\n"
             "    return it != s_fibers.end() && it->second.fiber != nullptr && !it->second.terminated;\n"
             "}")

# ---------------- os_scheduler.cpp ----------------
S_GATE_OLD = ("        // Check if target thread has a fiber\n"
              "        if (!Fiber::GuestFiberManager::HasFiber(nextThread)) {")
S_GATE_NEW = ("        // Check if target thread has a usable fiber (Batch 267:\n"
              "        // HasFiber alone let terminated / null-handle records\n"
              "        // through to an abandoning switch; unusable targets\n"
              "        // take the LoadContext fallback deterministically.)\n"
              "        if (!Fiber::GuestFiberManager::HasUsableFiber(nextThread)) {")
S_HELPER_ANCHOR = "static void SelectThreadSwitch(CpuContext* cpu, uint32_t runningContext, bool resumeInIdle)\n{"
S_HELPER = ("// Batch 267: report a SwitchToThread outcome that did not\n"
            "// switch after the guest bookkeeping committed. The\n"
            "// dispatcher-deferral exit logged nothing before this,\n"
            "// which kept it an unprovable suspect for the phantoms.\n"
            "static const char* B267ResultName(Fiber::GuestFiberManager::SwitchResult r)\n"
            "{\n"
            "    using SR = Fiber::GuestFiberManager::SwitchResult;\n"
            "    switch (r) {\n"
            "        case SR::Switched: return \"switched\";\n"
            "        case SR::AlreadyCurrent: return \"already-current\";\n"
            "        case SR::Deferred: return \"deferred\";\n"
            "        case SR::NoFiber: return \"no-fiber\";\n"
            "        case SR::InvalidFiber: return \"invalid-fiber\";\n"
            "        case SR::NotInitialized: return \"not-initialized\";\n"
            "    }\n"
            "    return \"?\";\n"
            "}\n"
            "\n"
            "static void B267LogSwitchFailure(uint32_t target, Fiber::GuestFiberManager::SwitchResult r, bool rescued)\n"
            "{\n"
            "    static std::atomic<int> s_b267LogCount{0};\n"
            "    if (s_b267LogCount.fetch_add(1) < 300) {\n"
            "        if (FILE* wf = fopen(\"cttr-witness.txt\", \"a\")) {\n"
            "            fprintf(wf, \"[w267] switch to=0x%08X result=%s rescued=%d\\n\",\n"
            "                    target, B267ResultName(r), rescued ? 1 : 0);\n"
            "            fclose(wf);\n"
            "        }\n"
            "    }\n"
            "}\n"
            "\n")
S_A_OLD = ("        if (currentGuestThread == 0) {\n"
           "            Fiber::GuestFiberManager::SwitchToThread(nextThread, cpu);\n"
           "            return;\n"
           "        }")
S_A_NEW = ("        if (currentGuestThread == 0) {\n"
           "            // Batch 267: a non-switch outcome here used to be\n"
           "            // indistinguishable from a real switch. Rescue the\n"
           "            // fiber-record failures via LoadContext (the host\n"
           "            // never switched, so the load is sound); a deferral\n"
           "            // is logged only (batch 148 forbids switching from\n"
           "            // inside the dispatcher fiber in any form).\n"
           "            using SR = Fiber::GuestFiberManager::SwitchResult;\n"
           "            const SR r267 = Fiber::GuestFiberManager::SwitchToThread(nextThread, cpu);\n"
           "            if (r267 == SR::NoFiber || r267 == SR::InvalidFiber || r267 == SR::NotInitialized) {\n"
           "                B267LogSwitchFailure(nextThread, r267, true);\n"
           "                cpu->gpr[3] = nextThread;\n"
           "                OS__LoadContext_801a1f58(cpu);\n"
           "            } else if (r267 == SR::Deferred) {\n"
           "                B267LogSwitchFailure(nextThread, r267, false);\n"
           "            }\n"
           "            return;\n"
           "        }")
S_B_OLD = ("        // Perform the fiber switch!\n"
           "        Fiber::GuestFiberManager::SwitchToThread(nextThread, cpu);\n"
           "        // When we return here, we've been switched back\n"
           "        return;")
S_B_NEW = ("        // Perform the fiber switch! (Batch 267: same outcome\n"
            "        // handling as the no-current-thread site above.)\n"
            "        {\n"
            "            using SR = Fiber::GuestFiberManager::SwitchResult;\n"
            "            const SR r267 = Fiber::GuestFiberManager::SwitchToThread(nextThread, cpu);\n"
            "            if (r267 == SR::NoFiber || r267 == SR::InvalidFiber || r267 == SR::NotInitialized) {\n"
            "                B267LogSwitchFailure(nextThread, r267, true);\n"
            "                cpu->gpr[3] = nextThread;\n"
            "                OS__LoadContext_801a1f58(cpu);\n"
            "            } else if (r267 == SR::Deferred) {\n"
            "                B267LogSwitchFailure(nextThread, r267, false);\n"
            "            }\n"
            "        }\n"
            "        // When we return here, we've been switched back\n"
            "        return;")


def patch(path, pairs, extra=None):
    raw = open(path, "rb").read()
    text = raw.decode("utf-8", errors="strict").replace("\r\n", "\n")
    if MARKER in text:
        print("SKIP (already applied):", path)
        return False
    anchors = [a for a, _ in pairs] + ([extra] if extra else [])
    for anchor in anchors:
        n = text.count(anchor)
        if n != 1:
            print("FAIL: anchor count %d (want 1) in %s for %r" % (n, os.path.basename(path), anchor[:64]))
            sys.exit(1)
    bak = path + ".bak-pre267"
    if not os.path.exists(bak):
        shutil.copyfile(path, bak)
        print("backup:", bak)
    for old, new in pairs:
        text = text.replace(old, new)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    print("patched:", path)
    return True


def main():
    patch(HDR, [(H_OLD, H_NEW)])
    patch(CPP, [(C_SIG_OLD, C_SIG_NEW), (C_INIT_OLD, C_INIT_NEW), (C_DEF_OLD, C_DEF_NEW),
                (C_NOFIB_OLD, C_NOFIB_NEW), (C_INV_OLD, C_INV_NEW), (C_CUR_OLD, C_CUR_NEW),
                (C_END_OLD, C_END_NEW), (C_HAS_OLD, C_HAS_NEW)])
    changed = patch(SCHED, [(S_GATE_OLD, S_GATE_NEW), (S_A_OLD, S_A_NEW), (S_B_OLD, S_B_NEW)],
                    extra=S_HELPER_ANCHOR)
    if changed:
        t = open(SCHED, encoding="utf-8").read()
        t = t.replace(S_HELPER_ANCHOR, S_HELPER + S_HELPER_ANCHOR, 1)
        with open(SCHED, "w", encoding="utf-8", newline="\n") as f:
            f.write(t)
    h = open(HDR, encoding="utf-8").read()
    c = open(CPP, encoding="utf-8").read()
    s = open(SCHED, encoding="utf-8").read()
    assert "enum class SwitchResult" in h and "HasUsableFiber" in h
    assert c.count("return SwitchResult::") == 6, c.count("return SwitchResult::")
    assert s.count("[w267] switch") == 1 and s.count("HasUsableFiber(nextThread)") == 1
    print("OK: batch 267 applied")
    return 0


if __name__ == "__main__":
    sys.exit(main())
