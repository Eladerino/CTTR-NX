# Batch 169 (CTTR FIX): tolerate EOF-overrun reads in DVDReadAbsAsyncPrio_CTTR.
#
# Run 192 stalled at the threshold of the frontend: the GOD stream
# reader's final block read for skins.god (the last file loaded from
# common.rcf) asked for 11,552 bytes at archive offset 577,536, but
# common.rcf is 589,079 bytes -- the request overruns the file end
# by exactly 9 bytes (the skins.god script text runs to the very
# last byte of the archive, verified on disk). ResolveAbsRead
# already clamps readLength to the available bytes, but the CTTR
# ReadAbs native treated any clamp as fatal ("requested range
# extends beyond the indexed DVD file") and completed with -1, so
# the loader retried the same block forever (~29.5k witness lines).
#
# On hardware the drive transfers the full requested count from the
# continuous disc image and the guest's parser stops at the file's
# own internal end. This fix matches that: serve the available
# bytes, zero-fill the slack (inter-file padding), and complete
# with the full requested length. Scope: DVDReadAbsAsyncPrio_CTTR
# only (the proven live path). The same latent pattern in
# DVDLowRead_CTTR and the NSMBW-shaped HLEs is left alone -- none
# of them has ever been called by CTTR.
#
# A [dvd169] witness line records each overrun served.
# Idempotent via the "Batch 169" marker; backup dvd.cpp.bak-pre169.
# Runtime-only change: no emit needed. Honours CTTR_ROOT.

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled"))
MARKER = "Batch 169"
TARGET = ROOT / "runtime" / "src" / "hle" / "storage" / "dvd.cpp"

OLD_BRANCH = """    if (readInfo.readLength != static_cast<uint32_t>(length)) {
        ReportDvdReadError(HostPathText(readInfo.entry->hostPath), readInfo.fileOffset,
                           static_cast<uint32_t>(length),
                           "requested range extends beyond the indexed DVD file");
        return done(-1);
    }
"""

NEW_BRANCH = """    // Batch 169 (CTTR fix): a read that starts inside the file but runs
    // past its end is NOT an error. ResolveAbsRead clamps readLength to
    // the bytes available; on hardware the drive transfers the full
    // requested count from the continuous disc image (the guest's GOD
    // stream reader issues fixed-size block reads whose final block
    // can overrun the archive -- proven by skins.god in common.rcf:
    // fileOff 577536 len 11552 vs size 589079, a 9-byte overrun that
    // hard-failed every retry in run 192). Serve the available bytes,
    // zero-fill the slack, and complete with the full requested
    // length (see the tail of this function).
    const bool eofOverrun = readInfo.readLength < static_cast<uint32_t>(length);
"""

OLD_TAIL = """    CopyToGuestAsDma(buffer, tempBuf.data(), tempBuf.size());
    return done(static_cast<int32_t>(tempBuf.size()));
}
PPC_NATIVE_OVERRIDE(8034F5B0, DVDReadAbsAsyncPrio_CTTR,"""

NEW_TAIL = """    CopyToGuestAsDma(buffer, tempBuf.data(), tempBuf.size());
    if (eofOverrun) {
        // Batch 169: zero-fill the slack past EOF and report the full
        // requested transfer, matching the hardware drive.
        const uint32_t slack = static_cast<uint32_t>(length) - readInfo.readLength;
        std::vector<uint8_t> zeros(slack, 0);
        CopyToGuestAsDma(buffer + readInfo.readLength, zeros.data(), zeros.size());
        FILE* tf = fopen("cttr-witness.txt", "a");
        if (tf) { fprintf(tf, "[dvd169] eof-overrun fileOff=%u req=%u served=%u zeroed=%u\\n", (unsigned)readInfo.fileOffset, (unsigned)length, (unsigned)readInfo.readLength, (unsigned)slack); fclose(tf); }
        return done(static_cast<int32_t>(length));
    }
    return done(static_cast<int32_t>(tempBuf.size()));
}
PPC_NATIVE_OVERRIDE(8034F5B0, DVDReadAbsAsyncPrio_CTTR,"""


def fail(msg):
    print("FAIL:", msg)
    sys.exit(1)


def main():
    if not TARGET.exists():
        fail(f"missing file: {TARGET}")
    text = TARGET.read_text()
    if MARKER in text:
        print("dvd.cpp: already applied, skipping")
        return
    for anchor, label in ((OLD_BRANCH, "overrun branch"), (OLD_TAIL, "completion tail")):
        c = text.count(anchor)
        if c != 1:
            fail(f"{label}: anchor count {c} != 1")
    text = text.replace(OLD_BRANCH, NEW_BRANCH, 1)
    text = text.replace(OLD_TAIL, NEW_TAIL, 1)
    backup = TARGET.with_name(TARGET.name + ".bak-pre169")
    if not backup.exists():
        shutil.copy2(TARGET, backup)
    TARGET.write_text(text)
    print("patched: dvd.cpp")
    print("Batch 169 applied.")


if __name__ == "__main__":
    main()
