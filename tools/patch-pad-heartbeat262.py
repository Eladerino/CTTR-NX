# Batch 262: surface the PAD call count in the heartbeat.
#
# The pad-polling hunt (Nov 6) proved [pad151]=3 is a
# witness artifact: pad.cpp's s_calls increments on every
# PAD__Read_HLE call but only the first 3 calls print (plus
# env-gated pulse edges; soak runs set no pulse env). This
# batch mirrors s_calls to a file-scope counter and prints
# it as pad= in every [w212] heartbeat line, settling
# whether the guest polls PAD during the attract.
#
# Pure ASCII. Anchors verified count==1 per file;
# .bak-pre262 per file; idempotent via the Batch 262
# marker (checked in pad.cpp).

import os
import shutil
import sys

ROOT = os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled")
MARKER = "Batch 262"

PAD = r"runtime\src\hle\input\pad.cpp"
PAD_EDITS = []
A = '''extern "C" uint32_t PAD__Read_HLE(uint32_t statusPtr)'''
PAD_EDITS.append((A, '''// Batch 262: PAD call count mirror for the heartbeat.
uint64_t g_padCalls262 = 0;
extern "C" uint64_t CttrPadCalls262() { return g_padCalls262; }

extern "C" uint32_t PAD__Read_HLE(uint32_t statusPtr)'''))
A = """        ++s_calls;"""
PAD_EDITS.append((A, """        ++s_calls;
        g_padCalls262 = s_calls;  // Batch 262"""))

OSI = r"runtime\src\hle\os\os_init.cpp"
OSI_EDITS = []
A = """static void CttrBeatPollMain() {"""
OSI_EDITS.append((A, """extern "C" uint64_t CttrPadCalls262();  // Batch 262

static void CttrBeatPollMain() {"""))
A = """fprintf(f, "[w212] t=%lldms disp=%llu glue=%llu bink=%llu\\n", ms, d, g, b);  // Batch 213"""
OSI_EDITS.append((A, """fprintf(f, "[w212] t=%lldms disp=%llu glue=%llu bink=%llu pad=%llu\\n", ms, d, g, b, (unsigned long long)CttrPadCalls262());  // Batch 262"""))


def apply(rel, edits):
    path = os.path.join(ROOT, rel)
    with open(path, "r", encoding="utf-8", errors="strict") as fh:
        text = fh.read()
    for anchor, _ in edits:
        n = text.count(anchor)
        if n != 1:
            print("ABORT: anchor count %d != 1 in %s for: %s" % (n, rel, anchor[:60]))
            sys.exit(1)
    shutil.copyfile(path, path + ".bak-pre262")
    for anchor, insert in edits:
        text = text.replace(anchor, insert, 1)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)
    print("PATCHED:", rel)


def main():
    padpath = os.path.join(ROOT, PAD)
    with open(padpath, "r", encoding="utf-8", errors="strict") as fh:
        if MARKER in fh.read():
            print("SKIP (already patched)")
            return
    apply(PAD, PAD_EDITS)
    apply(OSI, OSI_EDITS)
    print("batch 262 applied")


if __name__ == "__main__":
    main()
