#!/usr/bin/env python3
# Batch 270: CTTR-only Phase 3 -- strip every foreign (non-CTTR)
# PPC_NATIVE_OVERRIDE registration from the kept runtime sources.
#
# Data: cttr_native_scope.csv (511 scanner rows: file, line,
# address, handler, in_cttr_map) -- the 408 in_cttr_map=False rows
# are the strip set. 11 of them lived in gx_nsmbw.cpp /
# spm_rel_pin.cpp, already deleted in batch 269; the remaining 397
# sit in 45 kept files. Design: ~/cttr-design/phase3/batch270-design.md
#
# A registration is one source line:
#   PPC_NATIVE_OVERRIDE_VOID(8027322C, OSLockMutex_HLE_801a7ee4, ...);
# A line is removed only when its (address, handler) pair is a
# CSV-foreign pair FOR THAT FILE. Handler functions stay (several
# serve CTTR registrations too). Verification is address-set based
# (the CSV predates batch 265, whose two added CTTR registrations
# must simply never match the foreign set -- they cannot, their
# addresses are CTTR's).
#
# All edits stage in memory; files are written only when every
# selected file verifies: removed multiset == CSV-foreign multiset
# for the file, and the per-file brace delta is unchanged.
# .bak-pre270 backups; marker "Batch 270"; --only G1|G2|G3|G4
# selects a build group (default: all).
import csv
import os
import re
import sys
from collections import Counter

ROOT = os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled")
SCOPE_CSV = os.environ.get("CTTR_SCOPE_CSV", r"C:\Users\glynn\cttr_native_scope.csv")
MARKER = "Batch 270"
DROPPED_FILES = {"hle\\gx\\gx_nsmbw.cpp", "hle\\spm_rel_pin.cpp"}

GROUPS = {
    "G1": ["hle\\gx\\gx_copy.cpp", "hle\\gx\\gx_dl.cpp", "hle\\gx\\gx_egg.cpp",
           "hle\\gx\\gx_indirect.cpp", "hle\\gx\\gx_init.cpp", "hle\\gx\\gx_lighting.cpp",
           "hle\\gx\\gx_pixel.cpp", "hle\\gx\\gx_stubs.cpp", "hle\\gx\\gx_tev.cpp",
           "hle\\gx\\gx_texture.cpp", "hle\\gx\\gx_transform.cpp", "hle\\gx\\gx_vertex.cpp"],
    "G2": ["hle\\os\\os_alarm.cpp", "hle\\os\\os_cache.cpp", "hle\\os\\os_context.cpp",
           "hle\\os\\os_font.cpp", "hle\\os\\os_init.cpp", "hle\\os\\os_interrupt.cpp",
           "hle\\os\\os_message.cpp", "hle\\os\\os_report.cpp", "hle\\os\\os_reset.cpp",
           "hle\\os\\os_scheduler.cpp", "hle\\os\\os_sleep.cpp", "hle\\os\\os_thread.cpp",
           "hle\\os\\os_time.cpp"],
    "G3": ["hle\\storage\\dvd.cpp", "hle\\storage\\nand_api.cpp", "hle\\storage\\nand_async.cpp",
           "hle\\storage\\nand_isfs.cpp", "hle\\ios.cpp", "hle\\sc.cpp", "hle\\esp.cpp",
           "hle\\c_stdio.cpp"],
    "G4": ["hle\\audio\\audio.cpp", "hle\\audio\\ax_effects.cpp", "hle\\input\\pad.cpp",
           "hle\\input\\wpad.cpp", "hle\\input\\kpad.cpp", "hle\\vi.cpp",
           "hle\\egg_decomp.cpp", "hle\\net\\network_config.cpp", "hle\\strap_scene.cpp",
           "hle\\task_thread.cpp", "hle\\trk.cpp"],
}

OVERRIDE_RE = re.compile(
    r"(?:PPC_NATIVE_OVERRIDE[A-Z_0-9]*|REGISTER_NATIVE_FUNCTION(?:_AS)?)"
    r"\s*\(\s*(?:0[xX])?([0-9A-Fa-f]+)\s*,\s*([A-Za-z_][A-Za-z0-9_]*)")


def norm_addr(a):
    a = a.strip().upper()
    if a.startswith("0X"):
        a = a[2:]
    return a.zfill(8)


def main():
    only = None
    if "--only" in sys.argv:
        only = sys.argv[sys.argv.index("--only") + 1].upper()
        if only not in GROUPS:
            print("ABORT: unknown group %r" % only)
            return 1

    foreign = {}
    with open(SCOPE_CSV, newline="") as fh:
        for row in csv.DictReader(fh):
            if row["in_cttr_map"] != "False":
                continue
            rel = row["file"].replace("/", "\\")
            if rel.startswith("runtime\\src\\"):
                rel = rel[len("runtime\\src\\"):]
            foreign.setdefault(rel, Counter())[
                (norm_addr(row["address"]), row["handler"])] += 1

    selected = set(GROUPS[only]) if only else None
    staged = {}
    total_removed = 0
    for rel, want in sorted(foreign.items()):
        if rel in DROPPED_FILES:
            continue
        if selected is not None and rel not in selected:
            continue
        path = os.path.join(ROOT, "runtime", "src", *rel.split("\\"))
        if not os.path.exists(path):
            print("ABORT: expected kept file missing: %s" % rel)
            return 1
        with open(path, "r", errors="replace") as fh:
            text = fh.read()
        if MARKER in text:
            print("SKIP (already patched): %s" % rel)
            continue
        lines = text.split("\n")
        removed = Counter()
        kept_lines = []
        i = 0
        while i < len(lines):
            m = OVERRIDE_RE.search(lines[i])
            if m:
                # A registration may span several lines; it ends at
                # the first line carrying ");".
                j = i
                while j < len(lines) and ");" not in lines[j]:
                    j += 1
                if j >= len(lines):
                    print("ABORT: %s: unterminated registration at line %d"
                          % (rel, i + 1))
                    return 1
                span_text = "\n".join(lines[i:j + 1])
                m2 = OVERRIDE_RE.search(span_text)
                pair = (norm_addr(m2.group(1)), m2.group(2))
                if want.get(pair, 0) > removed.get(pair, 0):
                    removed[pair] += 1
                    i = j + 1
                    continue
                kept_lines.extend(lines[i:j + 1])
                i = j + 1
                continue
            kept_lines.append(lines[i])
            i += 1
        if removed != want:
            print("ABORT: %s: removed %s != CSV foreign %s"
                  % (rel, dict(removed), dict(want)))
            return 1
        new_text = "\n".join(kept_lines)
        if (new_text.count("{") - new_text.count("}")) != (text.count("{") - text.count("}")):
            print("ABORT: %s: brace delta changed" % rel)
            return 1
        new_text = new_text.rstrip("\n") + \
            "\n// Batch 270: foreign registrations stripped (CTTR-only Phase 3).\n"
        staged[path] = (text, new_text)
        total_removed += sum(removed.values())
        print("STAGED %s: -%d registrations" % (rel, sum(removed.values())))

    if not staged:
        print("nothing to do")
        return 0
    for path, (old, new) in staged.items():
        with open(path + ".bak-pre270", "w") as fh:
            fh.write(old)
        with open(path, "w") as fh:
            fh.write(new)
    print("batch 270 applied: %d files, %d registrations stripped"
          % (len(staged), total_removed))
    return 0


if __name__ == "__main__":
    sys.exit(main())
