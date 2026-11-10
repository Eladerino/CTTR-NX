# Batch 248 (diagnostics): active-era Bink IO sampling.
#
# The stall surveys only fire once the guest is already still, so
# batches 244-247 only ever saw the frozen state of the Bink IO
# structs. The [w212] heartbeat prints from the same poller every
# 5 s WHILE the counters move -- this batch appends a [w248] line
# there with the live values of the pump's wait state:
#   io+28, io+32 (busy flag), io+84, io+88/+92/+96 (cursor triple)
#     for the IO context struct at 0x8138B190
#   inner+16 (service counter), inner+20/+24/+44
#     for the GOD device object at 0x80B93A44
#   dev76+184 (the fn_8023A700 queue field), dev76 word+84,
#   dev80 word+84 (fn_80239F04's returned flag byte lives there)
#     for the file/device objects at 0x80B93060 / 0x80B92558
#
# Pure ASCII. Anchor verified count==1; .bak-pre248; idempotent.

import os
import shutil
import sys

ROOT = os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled")
MARKER = "Batch 248"
REL = r"runtime\src\hle\os\os_init.cpp"

ANCHOR = 'fprintf(f, "[w212] t=%lldms disp=%llu glue=%llu bink=%llu\\n", ms, d, g, b);  // Batch 213'

INSERT = ANCHOR + (
    '\n            fprintf(f, "[w248] io28=%08X io32=%08X io84=%08X ioCur=%08X/%08X/%08X in16=%08X in20=%08X in24=%08X in44=%08X d76q=%08X d76w84=%08X d80w84=%08X\\n", ::Memory::Read32(0x8138B190u + 28u), ::Memory::Read32(0x8138B190u + 32u), ::Memory::Read32(0x8138B190u + 84u), ::Memory::Read32(0x8138B190u + 88u), ::Memory::Read32(0x8138B190u + 92u), ::Memory::Read32(0x8138B190u + 96u), ::Memory::Read32(0x80B93A44u + 16u), ::Memory::Read32(0x80B93A44u + 20u), ::Memory::Read32(0x80B93A44u + 24u), ::Memory::Read32(0x80B93A44u + 44u), ::Memory::Read32(0x80B93060u + 184u), ::Memory::Read32(0x80B93060u + 84u), ::Memory::Read32(0x80B92558u + 84u));  // Batch 248'
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
    shutil.copyfile(path, path + ".bak-pre248")
    text = text.replace(ANCHOR, INSERT, 1)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)
    print("PATCHED:", REL)
    print("batch 248 applied")


if __name__ == "__main__":
    main()
