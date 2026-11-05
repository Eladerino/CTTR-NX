import sys
from pathlib import Path

# Batch 30: AIStartDMA, second attempt.
# Batch 29 (rebind 0x80354818 to a local VOID stub) ran and the boot
# faulted at the SAME address (console-33, mem1_10: 0xCC005036,
# __DSPRegs[27], LR __AXOutInit+0x388, guest state identical, 41 bytes
# differ in the whole 24 MB snapshot). A full-DOL scan confirms the
# only [27] readers are __OSStopAudioSystem, AIInitDMA (3rd read,
# exonerated by first-touch at 0xCC005030), AIStartDMA and AIStopDMA
# (sole caller __AXOutQuit, not in this stack) -- so guest AIStartDMA
# still ran. Pattern across this file (audio.cpp): VOID+args bindings
# work (AIInit, AIInitDMA, __DSP_boot_task), non-VOID+no-args works
# (DSPCheckInit, batch 21: tiny 8-byte leaf, proven by the absence of
# a second DSPInit log in the __AXOutInitDSP path), VOID+no-args has
# now failed twice for this address with two different impls. Fix:
# match the proven DSPCheckInit form exactly -- PPC_NATIVE_OVERRIDE,
# uint32_t return, no args, local stub returning 0.
# Handles both starting states: batch-29 applied (VOID AIStartDMA_CTTR
# binding present) or not (batch-27 AIStartDMA_80124048 binding).

path = Path(sys.argv[1] if len(sys.argv) > 1 else r"runtime\src\hle\audio\audio.cpp")
src = path.read_text(encoding="utf-8")

# Diagnostic: where does AIStartDMA appear in the runtime sources?
src_root = path.parent
while src_root.name != "src" and src_root.parent != src_root:
    src_root = src_root.parent
print("---- AIStartDMA references under", src_root, "----")
found_any = False
if src_root.is_dir():
    for f in sorted(src_root.rglob("*")):
        if f.suffix not in (".cpp", ".h", ".hpp"):
            continue
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for n, line in enumerate(text.splitlines(), 1):
            if "AIStartDMA" in line:
                print(f"  {f.relative_to(src_root)}:{n}: {line.strip()}")
                found_any = True
if not found_any:
    print("  (none)")
print("----")

if "AIStartDMA_CTTR_R" in src:
    print("already patched:", path)
    sys.exit(0)

old29 = "PPC_NATIVE_OVERRIDE_VOID(80354818, AIStartDMA_CTTR, (), ());"
old27 = "PPC_NATIVE_OVERRIDE_VOID(80354818, AIStartDMA_80124048, (), ());"
count = src.count(old29) + src.count(old27)
if count != 1:
    print("ANCHOR PROBLEM: AIStartDMA VOID bindings found =", count,
          "(batch29:", src.count(old29), "batch27:", src.count(old27), ")")
    sys.exit(1)

state = "batch29" if src.count(old29) == 1 else "batch27"
new_block = r"""extern "C" uint32_t AIStartDMA_CTTR_R() {
    std::lock_guard<std::mutex> lock(g_ai.mutex);
    g_ai.enabled = true;
    return 0;
}
PPC_NATIVE_OVERRIDE(80354818, AIStartDMA_CTTR_R, uint32_t, (), ());"""
src = src.replace(old29, new_block).replace(old27, new_block)
path.write_text(src, encoding="utf-8")
print("patched:", path, "(replaced the", state, "binding)")
