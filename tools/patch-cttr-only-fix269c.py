#!/usr/bin/env python3
# Batch 269c: link repairs for the CTTR-only partition (batches
# 268+269), found by the first partition build (Nov 7 2026).
#
# Two inventory misses, both structural:
#   1. The unit inventory behind CttrSources.cmake was derived
#      from unity-batch contents, so every SKIP_UNITY_BUILD_
#      INCLUSION unit was invisible to it. Five kept units were
#      left out of the manifest and the link failed on their
#      symbols (PPC_*, KPAD_HLE_SaveState/LoadState,
#      GuestProfiler::OnFramePresented): fpu_helpers.cpp,
#      ppc_helpers.cpp, ppc_quantized.cpp, hle/input/kpad.cpp,
#      guest_profiler.cpp. The pre-partition build's object dir
#      (build-cttr/CMakeFiles/mkw_runtime_common.dir) proves these
#      five -- and only these five -- were standalone objects.
#      They are added back here, in the manifest's alphabetical
#      order. (host_cpu_baseline.cpp, platform/host_platform.cpp
#      and product/*.cpp have no object in mkw_runtime_common;
#      they belong to other targets and stay out.)
#   2. ModHooks (declared in abi_bridge.h, consulted on every
#      indirect call) was defined in mod_runtime.cpp, which batch
#      269 dropped with the mod feature. Nothing else in the kept
#      tree references ModRuntime:: anymore (verified by search),
#      but abi_bridge needs the ModHooks symbols. They are defined
#      here as permanently inert in recomp_mod_loader.cpp -- the
#      kept generic mod machinery: with no mod runtime in the
#      build, no hook can ever register, g_active stays false, and
#      ApplyRuntimeCallOptions never reaches Run.
#
# Anchored, backed up (.bak-pre269c), idempotent via marker.
import os
import sys

ROOT = os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled")
CMAKE_PATH = os.path.join(ROOT, "runtime", "cmake", "CttrSources.cmake")
LOADER_PATH = os.path.join(ROOT, "runtime", "src", "recomp_mod_loader.cpp")
MARKER = "Batch 269c"

ENTRIES = [
    # (new entry, anchor substring of the line it goes before)
    ("fpu_helpers.cpp", "/src/frame_input.cpp\""),
    ("guest_profiler.cpp", "/src/hle/audio/audio.cpp\""),
    ("hle/input/kpad.cpp", "/src/hle/input/pad.cpp\""),
    ("ppc_helpers.cpp", "/src/recomp_mod_loader.cpp\""),
    ("ppc_quantized.cpp", "/src/recomp_mod_loader.cpp\""),
]

STUB = """
// Batch 269c: ModHooks was defined in mod_runtime.cpp, dropped with
// the mod feature in batch 269, but abi_bridge.h declares it and
// consults it on every indirect call. With no mod runtime in the
// CTTR build nothing can register a hook, so the flag is
// permanently false and Run is never reached (ApplyRuntimeCallOptions
// checks the flag first). Defined here with the kept generic mod
// machinery.
namespace ModHooks {
bool g_active = false;
bool Run(uint32_t, CpuContext*) { return false; }
} // namespace ModHooks
"""


def load(path):
    with open(path, "r", errors="replace") as fh:
        return fh.read()


def save(path, text, old):
    with open(path + ".bak-pre269c", "w") as fh:
        fh.write(old)
    with open(path, "w") as fh:
        fh.write(text)


def main():
    cmake = load(CMAKE_PATH)
    loader = load(LOADER_PATH)
    if MARKER in cmake and MARKER in loader:
        print("SKIP (already patched): batch 269c")
        return 0
    if "ModHooks" in loader:
        print("ABORT: recomp_mod_loader.cpp already mentions ModHooks")
        return 1

    lines = cmake.split("\n")
    for entry, anchor in ENTRIES:
        needle = "/src/%s\"" % entry
        if any(needle in l for l in lines):
            print("ABORT: entry already present: %s" % entry)
            return 1
        hits = [i for i, l in enumerate(lines) if anchor in l]
        if len(hits) != 1:
            print("ABORT: anchor %r found %d times" % (anchor, len(hits)))
            return 1
        lines.insert(hits[0], '    "${CMAKE_CURRENT_LIST_DIR}/../src/%s"' % entry)
    lines.append("# Batch 269c: skip-unity units (fpu_helpers, ppc_helpers,")
    lines.append("# ppc_quantized, hle/input/kpad, guest_profiler) restored to the")
    lines.append("# manifest, and the ModHooks stub (see recomp_mod_loader.cpp).")
    new_cmake = "\n".join(lines)

    new_loader = loader.rstrip("\n") + "\n" + STUB

    save(CMAKE_PATH, new_cmake, cmake)
    save(LOADER_PATH, new_loader, loader)
    print("PATCHED: runtime\\cmake\\CttrSources.cmake (+5 units)")
    print("PATCHED: runtime\\src\\recomp_mod_loader.cpp (ModHooks stub)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
