# Batch 241 (diagnostic): make the batch 237 host-stack sampler
# repeat inside one stall episode.
#
# Batch 237 samples once per stall episode; the two samples per
# run land mostly in dispatch glue and may catch different eras
# (run 268: sample 1 storm era, sample 2 frozen era). A histogram
# needs volume: sample on every stall poll once the survey has
# been identical for 10 polls, up to 40 samples per episode. The
# counter resets with the episode (counters-moved branch), like
# the bool did.
#
# Pure ASCII. Anchors verified count==1; .bak-pre241; idempotent.

import os
import shutil
import sys

ROOT = os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled")
MARKER = "Batch 241"
REL = r"runtime\src\hle\os\os_init.cpp"

EDITS = [
    (
        "    bool sampled237 = false;  // Batch 237",
        "    int sampled237 = 0;  // Batch 237, repeat counter since Batch 241",
    ),
    (
        "            sampled237 = false;  // Batch 237",
        "            sampled237 = 0;  // Batch 237/241",
    ),
    (
        "            if (hashStill229 >= 10 && !sampled237) { sampled237 = true; CttrSampleHostStacks237(); }  // Batch 237",
        "            if (hashStill229 >= 10 && sampled237 < 40) { ++sampled237; CttrSampleHostStacks237(); }  // Batch 241",
    ),
]


def main():
    path = os.path.join(ROOT, REL)
    with open(path, "r", encoding="utf-8", errors="strict") as fh:
        text = fh.read()
    if MARKER in text:
        print("SKIP (already patched):", REL)
        return
    for old, _new in EDITS:
        n = text.count(old)
        if n != 1:
            print("ABORT: anchor count %d != 1 for: %s" % (n, old[:60]))
            sys.exit(1)
    shutil.copyfile(path, path + ".bak-pre241")
    for old, new in EDITS:
        text = text.replace(old, new, 1)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)
    print("PATCHED:", REL)
    print("batch 241 applied")


if __name__ == "__main__":
    main()
