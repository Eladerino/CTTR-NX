#!/usr/bin/env python3
"""Batch 123 (CTTR): bind CTTR's GameCube PAD surface to the runtime's
existing PAD HLE implementations in pad.cpp.

pad.cpp carries full HLE impls (PAD__Init_HLE, PAD__Read_HLE, PAD__Reset_HLE,
PAD__Recalibrate_HLE, PAD__ControlMotor_HLE, MKWii heritage) but every
PPC_NATIVE_OVERRIDE is #if 0'd out for NSMBW/SPM, which never link PAD.
CTTR is a GameCube PAD game: its SDK PADRead (0x803539F0) currently runs
translated and polls SI registers the runtime does not emulate, so the game
can never see a controller or a button press -- the likely gate behind the
logo/strap stage never advancing (and all in-game input). Bind the five
CTTR addresses (symbols: PADInit 0x803538A0, PADRead 0x803539F0, PADReset
0x8035367C, PADRecalibrate 0x8035378C, PADControlMotor 0x80353CF0).

REQUIRES emit-build-shards after applying (override toggles), then build.
"""
import pathlib
import shutil
import sys

ROOT = pathlib.Path.cwd()
TARGET = ROOT / "runtime" / "src" / "hle" / "input" / "pad.cpp"

EDITS = [
    (
        """#if 0  // SPM: 0x801af2f0: no NSMBW symbol at this address
PPC_NATIVE_OVERRIDE(801AF2F0, PAD__Init_HLE, uint32_t, (), ());
#endif
#endif""",
        """#if 0  // SPM: 0x801af2f0: no NSMBW symbol at this address
PPC_NATIVE_OVERRIDE(801AF2F0, PAD__Init_HLE, uint32_t, (), ());
#endif
#endif
PPC_NATIVE_OVERRIDE(803538A0, PAD__Init_HLE, uint32_t, (), ());  // Batch 123: CTTR PADInit""",
    ),
    (
        """#if 0  // SPM: 0x801af44c: no NSMBW symbol at this address
PPC_NATIVE_OVERRIDE(801AF44C, PAD__Read_HLE, uint32_t, (uint32_t statusPtr), (statusPtr));
#endif
#endif""",
        """#if 0  // SPM: 0x801af44c: no NSMBW symbol at this address
PPC_NATIVE_OVERRIDE(801AF44C, PAD__Read_HLE, uint32_t, (uint32_t statusPtr), (statusPtr));
#endif
#endif
PPC_NATIVE_OVERRIDE(803539F0, PAD__Read_HLE, uint32_t, (uint32_t statusPtr), (statusPtr));  // Batch 123: CTTR PADRead""",
    ),
    (
        """#if 0  // SPM: 0x801af0dc: no NSMBW symbol at this address
PPC_NATIVE_OVERRIDE(801AF0DC, PAD__Reset_HLE, uint32_t, (uint32_t mask), (mask));
#endif
#endif""",
        """#if 0  // SPM: 0x801af0dc: no NSMBW symbol at this address
PPC_NATIVE_OVERRIDE(801AF0DC, PAD__Reset_HLE, uint32_t, (uint32_t mask), (mask));
#endif
#endif
PPC_NATIVE_OVERRIDE(8035367C, PAD__Reset_HLE, uint32_t, (uint32_t mask), (mask));  // Batch 123: CTTR PADReset""",
    ),
    (
        """#if 0  // SPM: 0x801af1e4: no NSMBW symbol at this address
PPC_NATIVE_OVERRIDE(801AF1E4, PAD__Recalibrate_HLE, uint32_t, (uint32_t mask), (mask));
#endif
#endif""",
        """#if 0  // SPM: 0x801af1e4: no NSMBW symbol at this address
PPC_NATIVE_OVERRIDE(801AF1E4, PAD__Recalibrate_HLE, uint32_t, (uint32_t mask), (mask));
#endif
#endif
PPC_NATIVE_OVERRIDE(8035378C, PAD__Recalibrate_HLE, uint32_t, (uint32_t mask), (mask));  // Batch 123: CTTR PADRecalibrate""",
    ),
    (
        """#if 0  // SPM: 0x801af908: no NSMBW symbol at this address
PPC_NATIVE_OVERRIDE_VOID(801AF908, PAD__ControlMotor_HLE, (int32_t chan, uint32_t command), (chan, command));
#endif
#endif""",
        """#if 0  // SPM: 0x801af908: no NSMBW symbol at this address
PPC_NATIVE_OVERRIDE_VOID(801AF908, PAD__ControlMotor_HLE, (int32_t chan, uint32_t command), (chan, command));
#endif
#endif
PPC_NATIVE_OVERRIDE_VOID(80353CF0, PAD__ControlMotor_HLE, (int32_t chan, uint32_t command), (chan, command));  // Batch 123: CTTR PADControlMotor""",
    ),
]


def main() -> int:
    data = TARGET.read_text(encoding="utf-8")
    if "Batch 123" in data:
        print("batch 123 already applied, skipping")
        return 0
    for old, _new in EDITS:
        if data.count(old) != 1:
            print("ERROR: an anchor count != 1; aborting, no writes")
            return 1
    shutil.copy2(TARGET, TARGET.with_name(TARGET.name + ".bak-pre123"))
    for old, new in EDITS:
        data = data.replace(old, new)
    TARGET.write_text(data, encoding="utf-8")
    print("batch 123 applied OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
