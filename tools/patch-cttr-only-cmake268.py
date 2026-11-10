# Batch 268: CTTR-only build graph (Phases 1+2, build-graph half).
#
# Brandon's ruling (Nov 6, 2026): anything not related to CTTR should
# not be built or recomped with it. This patcher applies the build
# graph half of the CTTR-only partition in the CTTR tree only:
#   1. Writes runtime/cmake/CttrSources.cmake: the explicit list of
#      the 90 runtime units CTTR compiles (103 today minus the 13
#      foreign units: gx_nsmbw, spm_rel_pin, mod_runtime, netplay x8,
#      spm_map_sweep, spm_prepare_graphics). Classification:
#      cttr_manifest_classification.csv; plan:
#      ~/cttr-design/cttr-only-implementation-plan.md
#   2. runtime/CMakeLists.txt: the src/*.cpp glob becomes an include
#      of that manifest. Every line after it (platform REMOVE_ITEMs,
#      appends) is untouched, so platform behaviour is preserved.
#   3. runtime/cmake/PublicProducts.cmake: the spm_libretro product
#      block and the RetroRewind product block are removed (neither
#      was ever built in this tree; WiiCompiled is the only product).
#      mkw_release is kept, depending on WiiCompiled alone.
#
# Pure ASCII. Anchors verified against the live files Nov 6, 2026.
# Backups: .bak-pre268. Idempotent via the marker.

import os
import shutil
import sys

ROOT = os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled")
MARKER = "Batch 268"
CMAKE_REL = r"runtime\CMakeLists.txt"
PRODUCTS_REL = r"runtime\cmake\PublicProducts.cmake"
MANIFEST_REL = r"runtime\cmake\CttrSources.cmake"

GLOB_LINE = 'file(GLOB_RECURSE SOURCES CONFIGURE_DEPENDS "src/*.cpp")'
GLOB_REPLACEMENT = """# CTTR-only (Batch 268): explicit source manifest replaces the glob.
# Anything not related to CTTR is not built with it. Classification
# and plan: ~/cttr-design/cttr-only-implementation-plan.md
include("${CMAKE_CURRENT_LIST_DIR}/cmake/CttrSources.cmake")
set(SOURCES ${CTTR_RUNTIME_SOURCES})"""

UNITS = [
    "src/abi_bridge.cpp",
    "src/android/android_bridge.cpp",
    "src/audio_backend.cpp",
    "src/controller_mapping_wizard.cpp",
    "src/det_clock.cpp",
    "src/det_hash.cpp",
    "src/disc_image.cpp",
    "src/discord_presence.cpp",
    "src/display_settings.cpp",
    "src/dynamic_aspect.cpp",
    "src/external_audio_macos.cpp",
    "src/fiber_manager.cpp",
    "src/frame_input.cpp",
    "src/frontend_runtime.cpp",
    "src/game_folder.cpp",
    "src/guest_flat_memory.cpp",
    "src/hle/audio/audio.cpp",
    "src/hle/audio/ax_effects.cpp",
    "src/hle/audio/ax_memory.cpp",
    "src/hle/audio/ax_mix.cpp",
    "src/hle/c_stdio.cpp",
    "src/hle/egg_decomp.cpp",
    "src/hle/esp.cpp",
    "src/hle/gx/gx_copy.cpp",
    "src/hle/gx/gx_dl.cpp",
    "src/hle/gx/gx_egg.cpp",
    "src/hle/gx/gx_fatal_stubs.cpp",
    "src/hle/gx/gx_fifo.cpp",
    "src/hle/gx/gx_frame.cpp",
    "src/hle/gx/gx_guest_write_hooks.cpp",
    "src/hle/gx/gx_indirect.cpp",
    "src/hle/gx/gx_init.cpp",
    "src/hle/gx/gx_lighting.cpp",
    "src/hle/gx/gx_objects.cpp",
    "src/hle/gx/gx_pixel.cpp",
    "src/hle/gx/gx_stubs.cpp",
    "src/hle/gx/gx_tev.cpp",
    "src/hle/gx/gx_texture.cpp",
    "src/hle/gx/gx_transform.cpp",
    "src/hle/gx/gx_utils.cpp",
    "src/hle/gx/gx_vertex.cpp",
    "src/hle/gx/gx_worker.cpp",
    "src/hle/input/pad.cpp",
    "src/hle/input/wpad.cpp",
    "src/hle/ios.cpp",
    "src/hle/net/network_config.cpp",
    "src/hle/net/network_core.cpp",
    "src/hle/net/network_deferred.cpp",
    "src/hle/net/network_socket.cpp",
    "src/hle/net/network_ssl.cpp",
    "src/hle/os/os_alarm.cpp",
    "src/hle/os/os_cache.cpp",
    "src/hle/os/os_context.cpp",
    "src/hle/os/os_font.cpp",
    "src/hle/os/os_init.cpp",
    "src/hle/os/os_interrupt.cpp",
    "src/hle/os/os_message.cpp",
    "src/hle/os/os_report.cpp",
    "src/hle/os/os_reset.cpp",
    "src/hle/os/os_scheduler.cpp",
    "src/hle/os/os_sleep.cpp",
    "src/hle/os/os_thread.cpp",
    "src/hle/os/os_time.cpp",
    "src/hle/sc.cpp",
    "src/hle/storage/dvd.cpp",
    "src/hle/storage/nand_api.cpp",
    "src/hle/storage/nand_async.cpp",
    "src/hle/storage/nand_fs.cpp",
    "src/hle/storage/nand_isfs.cpp",
    "src/hle/storage/riivolution.cpp",
    "src/hle/strap_scene.cpp",
    "src/hle/task_thread.cpp",
    "src/hle/trk.cpp",
    "src/hle/vi.cpp",
    "src/host_context.cpp",
    "src/input_bindings.cpp",
    "src/input_expr.cpp",
    "src/keybinds.cpp",
    "src/main.cpp",
    "src/memory.cpp",
    "src/mod_install.cpp",
    "src/music_attenuation.cpp",
    "src/native_override_counts.cpp",
    "src/recomp_mod_loader.cpp",
    "src/save_state.cpp",
    "src/settings_overlay.cpp",
    "src/system_bridge.cpp",
    "src/updater.cpp",
    "src/virtual_remote.cpp",
    "src/wii_remote_input.cpp",
]


def manifest_text():
    lines = [
        "# CTTR-only runtime source manifest (Batch 268, Nov 6 2026).",
        "# The runtime units the CTTR build compiles, listed explicitly.",
        "# Anything not related to CTTR is not built with it (Brandon's",
        "# ruling, Nov 6 2026). Source of truth: the classification in",
        "# cttr_manifest_classification.csv; plan and findings in",
        "# ~/cttr-design/cttr-only-implementation-plan.md. Generated",
        "# data-init units are appended by PublicProducts.cmake as",
        "# before and are not listed here.",
        "set(CTTR_RUNTIME_SOURCES",
    ]
    for unit in UNITS:
        lines.append('    "${CMAKE_CURRENT_LIST_DIR}/%s"' % unit)
    lines.append(")")
    return "\n".join(lines) + "\n"


def read_lines(path):
    with open(path, "r", errors="replace", newline="") as fh:
        return fh.read().splitlines()


def write_lines(path, lines):
    with open(path, "w", newline="\n") as fh:
        fh.write("\n".join(lines) + "\n")


def backup(path):
    bak = path + ".bak-pre268"
    if not os.path.exists(bak):
        shutil.copy2(path, bak)
        print("backup:", bak)


def find_block_from(lines, start, label):
    # Depth-counted if/endif matching from a known start line, so
    # nested ifs inside a block cannot end the span early.
    depth = 0
    for j in range(start, len(lines)):
        stripped = lines[j].strip()
        if stripped.startswith("if("):
            depth += 1
        elif stripped == "endif()":
            depth -= 1
            if depth == 0:
                return start, j
    raise SystemExit("FAIL: %s block never closes" % label)


def find_blocks(lines, start_pred, must_contain, label):
    # All blocks whose start line matches and whose span contains the
    # required text. PublicProducts.cmake has two MKW_HAVE_RETRO_REWIND
    # ifs (retro shard libraries ~190, RetroRewind product ~413); the
    # content check is what tells them apart.
    found = []
    i = 0
    while i < len(lines):
        if start_pred(lines[i]):
            start, end = find_block_from(lines, i, label)
            span = "\n".join(lines[start:end + 1])
            if must_contain in span:
                found.append((start, end))
            i = end + 1
        else:
            i += 1
    return found


def main():
    cmake_path = os.path.join(ROOT, CMAKE_REL)
    products_path = os.path.join(ROOT, PRODUCTS_REL)
    manifest_path = os.path.join(ROOT, MANIFEST_REL)

    cmake_lines = read_lines(cmake_path)
    if any(MARKER in line for line in cmake_lines):
        print("SKIP: marker already present in CMakeLists.txt")
        return 0

    if len(UNITS) != 90 or len(set(UNITS)) != 90:
        raise SystemExit("FAIL: manifest unit list is not 90 unique entries")

    # --- CMakeLists.txt: glob -> manifest -------------------------------
    hits = [i for i, line in enumerate(cmake_lines) if line.strip() == GLOB_LINE]
    if len(hits) != 1:
        raise SystemExit("FAIL: glob line found %d times (want 1)" % len(hits))

    products_lines = read_lines(products_path)

    lib_blocks = find_blocks(
        products_lines,
        lambda l: l.strip() == "if(MKW_BUILD_LIBRETRO)",
        "add_library(spm_libretro",
        "spm_libretro")
    if len(lib_blocks) != 1:
        raise SystemExit("FAIL: spm_libretro blocks found: %d" % len(lib_blocks))

    shard_blocks = find_blocks(
        products_lines,
        lambda l: l.strip() == "if(MKW_HAVE_RETRO_REWIND)",
        "add_library(mkw_retro_rewind_functions",
        "retro shard libraries")
    if len(shard_blocks) != 1:
        raise SystemExit("FAIL: retro shard blocks found: %d" % len(shard_blocks))

    retro_blocks = find_blocks(
        products_lines,
        lambda l: l.strip() == "if(MKW_HAVE_RETRO_REWIND)",
        "add_executable(RetroRewind",
        "RetroRewind product")
    if len(retro_blocks) != 1:
        raise SystemExit("FAIL: RetroRewind product blocks found: %d"
                         % len(retro_blocks))
    retro_span = "\n".join(
        products_lines[retro_blocks[0][0]:retro_blocks[0][1] + 1])
    if "mkw_release" not in retro_span:
        raise SystemExit("FAIL: RetroRewind span lacks mkw_release")

    # The arch-flag list spans three lines: set( opener, first names
    # line, continuation ending in "spm_libretro)". Both name lines
    # get rewritten so no removed target is named anywhere.
    targets_hits = []
    for i, line in enumerate(products_lines):
        if line.strip().startswith("set(MKW_ALL_BUILD_TARGETS"):
            if i + 2 < len(products_lines) and "spm_libretro" in products_lines[i + 2]:
                targets_hits.append(i + 1)
    if len(targets_hits) != 1:
        raise SystemExit("FAIL: MKW_ALL_BUILD_TARGETS list lines found: %d"
                         % len(targets_hits))

    backup(cmake_path)
    backup(products_path)

    cmake_lines[hits[0]:hits[0] + 1] = GLOB_REPLACEMENT.splitlines()
    write_lines(cmake_path, cmake_lines)
    print("CMakeLists.txt: glob replaced with manifest include")

    # All spans were located on the unedited line list. Apply edits in
    # strictly descending index order so no span index shifts under a
    # later edit: the arch-flag target list (bottom, a one-line rewrite
    # that changes no line count), the RetroRewind product block, the
    # spm_libretro block, then the retro shard libraries (top).
    ti = targets_hits[0]
    products_lines[ti] = ("    mkw_runtime_common mkw_base_shared "
                          "mkw_base_sensitive")
    products_lines[ti + 1] = "    WiiCompiled)"
    rs, re_ = retro_blocks[0]
    products_lines[rs:re_ + 1] = [
        "add_custom_target(mkw_release DEPENDS WiiCompiled)"]
    ls, le = lib_blocks[0]
    del products_lines[ls:le + 1]
    ss, se = shard_blocks[0]
    del products_lines[ss:se + 1]
    write_lines(products_path, products_lines)
    print("PublicProducts.cmake: retro shard block removed (%d lines), "
          "spm_libretro block removed (%d lines), RetroRewind block "
          "replaced (%d lines), arch-flag list pruned"
          % (se - ss + 1, le - ls + 1, re_ - rs + 1))

    with open(manifest_path, "w", newline="\n") as fh:
        fh.write(manifest_text())
    print("CttrSources.cmake written: %d units" % len(UNITS))
    print("PATCHED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
