#!/usr/bin/env python3
"""Batch 124 (CTTR): un-stub the GOD file handler drain (fn_800A86A0).

The batch-43 no-op stub override in os_init.cpp is still the registered
winner for 0x800A86A0. Batch 85's own note records why the stub is wrong:
"the stub froze the game's file-load finalization and every texture buffer
stayed zeroed." The stub was only ever a shield against pre-fix drain
corruption; batch 95 fixed the actual mechanism (fn_8024FA00's translation
clobbers r31, so the drain reloaded this=0 and scanned exception-vector
memory as its registry). Batches 85/90/105 retried the real drain BEFORE
the DVD command HLE existed (batch 109), so its completion queue could
never drain. Post-109/110, completions flow; retry the real drain now,
with batches 86-96's witnesses (incl. the r31 restore) live in the
generated body. Also deletes the stale triplicated batch-90 comment that
claims the stub is already removed, and the stale batch-85 comment.

REQUIRES emit-build-shards after applying (override toggle), then build.
"""
import pathlib
import shutil
import sys

ROOT = pathlib.Path.cwd()
TARGET = ROOT / "runtime" / "src" / "hle" / "os" / "os_init.cpp"

OLD_STUB = """extern "C" uint32_t GODFileHandler_Drain_CTTR()
{
    static bool logged = false;
    if (!logged) {
        logged = true;
        RT_LOG(RT_TAG_OS) << "GODFileHandler_Drain_CTTR called: stubbed (no-op, batch 43)" << std::endl;
    }
    return 0;
}
PPC_NATIVE_OVERRIDE(800A86A0, GODFileHandler_Drain_CTTR, uint32_t, (), ());"""

NEW_STUB = """// Batch 124: the batch-43 stub override is REMOVED -- the real translated
// fn_800A86A0 runs again (batch 95's r31 restore + batches 86-96 witnesses
// are in its generated body). The stub froze file-load finalization (batch
// 85's note): with it, texture buffers stay zeroed and no payload reads are
// ever issued. GODFileHandler_Drain_CTTR kept nowhere; do not re-stub
// without re-proving the r31 mechanism is back."""

OLD_90 = """// Batch 90: drain stub removed again -- the real fn_800A86A0 runs, with
// its registry scan skipped in the generated body (batch 90b), because the
// scan walks garbage entries and corrupts the handler mutex state.
// Batch 90: drain stub removed again -- the real fn_800A86A0 runs, with
// its registry scan skipped in the generated body (batch 90b), because the
// scan walks garbage entries and corrupts the handler mutex state.
// Batch 90: drain stub removed again -- the real fn_800A86A0 runs, with
// its registry scan skipped in the generated body (batch 90b), because the
// scan walks garbage entries and corrupts the handler mutex state.
"""

OLD_85 = """// Batch 85: the batch-43 GODFileHandler drain stub was removed -- the real
// fn_800A86A0 runs again (batch-42 range guards re-applied to its generated
// body) because the stub froze the game's file-load finalization and every
// texture buffer stayed zeroed.
"""


def main() -> int:
    data = TARGET.read_text(encoding="utf-8")
    if "Batch 124" in data:
        print("batch 124 already applied, skipping")
        return 0
    for anchor in (OLD_STUB, OLD_90, OLD_85):
        if data.count(anchor) != 1:
            print("ERROR: an anchor count != 1; aborting, no writes")
            return 1
    shutil.copy2(TARGET, TARGET.with_name(TARGET.name + ".bak-pre124"))
    data = data.replace(OLD_STUB, NEW_STUB).replace(OLD_90, "").replace(OLD_85, "")
    TARGET.write_text(data, encoding="utf-8")
    print("batch 124 applied OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
