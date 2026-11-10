# Batch 232b: namespace fix for 232's idle counter -- os_internal.h lives
# inside namespace OsHleInternal, so the counter must live there too.
import os, shutil, sys

ROOT = os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled")
MARKER = "Batch 232b"

def patch(path, pairs):
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        src = f.read()
    if MARKER in src:
        print("already patched:", path)
        return
    for old, new in pairs:
        n = src.count(old)
        if n != 1:
            print("ANCHOR FAIL (%d) in %s: %r" % (n, path, old[:70]))
            sys.exit(1)
        src = src.replace(old, new)
    bak = path + ".bak-pre232b"
    if not os.path.exists(bak):
        shutil.copy2(path, bak)
    with open(path, "w", encoding="utf-8") as f:
        f.write(src)
    print("patched:", path)

sched = os.path.join(ROOT, "runtime", "src", "hle", "os", "os_scheduler.cpp")
patch(sched, [
    ("""std::atomic<uint32_t> g_idleIter232{0};  // Batch 232: scheduler idle-loop iterations (watchdog probe)""",
     """namespace OsHleInternal { std::atomic<uint32_t> g_idleIter232{0}; }  // Batch 232b: idle-loop iterations (watchdog probe)"""),
])

osi = os.path.join(ROOT, "runtime", "src", "hle", "os", "os_init.cpp")
patch(osi, [
    ("""extern std::atomic<uint32_t> g_idleIter232;  // Batch 232 (defined in os_scheduler.cpp)
static void CttrBeatPollMain() {""",
     """static void CttrBeatPollMain() {  // Batch 232b: g_idleIter232 comes via os_internal.h (OsHleInternal)"""),
    ("""p232[2], g_idleIter232.load(), w232); }  // Batch 232""",
     """p232[2], OsHleInternal::g_idleIter232.load(), w232); }  // Batch 232"""),
])
print("batch 232b applied")
