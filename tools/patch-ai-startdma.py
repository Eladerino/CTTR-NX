import sys
from pathlib import Path

# Batch 29: AIStartDMA override did not take effect.
# Forensics (mem1_9, byte-identical to mem1_8): the console-32 fault is a
# read of 0xCC005036 = __DSPRegs[27] (DSP_DMA_CONTROL_LEN). In the
# __AXOutInit tail (mode 0, DspReady already stored, r3=__AXOutBuffer,
# r4=0x280 in the stale dispatch ctx), AIInitDMA cannot be the fault:
# its guest body reads __DSPRegs[24] at 0xCC005030 first and would have
# faulted there. AIStartDMA is the only other reader of [27] in that
# tail, its ONLY register touch is that read, and it has exactly one
# caller in the whole DOL (__AXOutInit+0x388). So batch 27's binding of
# 0x80354818 to the external impl AIStartDMA_80124048 was silently not
# applied (the VOID no-arg macro form itself is proven good by batch
# 19's GXDrawDone binding). Fix: rebind to a local CTTR stub in the
# batch-27 style (mirrors AIStopDMA_CTTR), whose symbol is defined in
# this same file and cannot be missing at link/scan time.
# The script first prints every AIStartDMA reference under runtime/src
# so the run log shows whether AIStartDMA_80124048 exists anywhere.

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

if "AIStartDMA_CTTR" in src:
    print("already patched:", path)
    sys.exit(0)

old = "PPC_NATIVE_OVERRIDE_VOID(80354818, AIStartDMA_80124048, (), ());"
if src.count(old) != 1:
    print("ANCHOR PROBLEM: batch-27 AIStartDMA binding count =", src.count(old))
    sys.exit(1)

new = r"""extern "C" void AIStartDMA_CTTR() {
    std::lock_guard<std::mutex> lock(g_ai.mutex);
    g_ai.enabled = true;
}
PPC_NATIVE_OVERRIDE_VOID(80354818, AIStartDMA_CTTR, (), ());"""
src = src.replace(old, new)
path.write_text(src, encoding="utf-8")
print("patched:", path)
