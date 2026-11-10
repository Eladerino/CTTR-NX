#!/usr/bin/env python3
# Batch 125: witness every GameFiberSwitch_CTTR switch + GameFiberProc
# materialization in os_context.cpp (first 120 switches): cur/new block,
# the target block's {fn,arg} pair at [0]/[4], its guest OSContext SRR0
# (block+0x20+0x198) and saved SP (block+0x20+4), started flags. Run 140
# died inside a fiber job whose descriptor fields held string bytes as
# pointers; this log shows exactly what the switch handed the fiber.
# Idempotent via "Batch 125" marker. Backup: os_context.cpp.bak-pre125
# beside the source.
import shutil
import sys
from pathlib import Path

ROOT = Path(r"C:\dev\cttr-wiicompiled")
TARGET = ROOT / "runtime" / "src" / "hle" / "os" / "os_context.cpp"

TEXT = TARGET.read_text(encoding="utf-8", errors="strict")
if "Batch 125" in TEXT:
    print("batch 125 already applied; nothing to do")
    sys.exit(0)

A1 = """    CpuContext* cpu = &GetPersistentCpuContext();
    CpuContextScope scope(cpu);
    // Fresh fiber: the guest OSContext inside the block (block+0x20) already"""
R1 = """    CpuContext* cpu = &GetPersistentCpuContext();
    CpuContextScope scope(cpu);
    // Batch 125: witness what a fresh fiber is materialized with.
    try {
        RT_LOG(RT_TAG_OS) << "[w125] GameFiberProc block=0x" << std::hex << block
                          << " fn=0x" << ::Memory::Read32(block)
                          << " arg=0x" << ::Memory::Read32(block + 4u)
                          << " srr0=0x" << ::Memory::Read32(block + 0x20u + 0x198u)
                          << " sp=0x" << ::Memory::Read32(block + 0x20u + 4u)
                          << std::dec << std::endl;
    } catch (...) {
    }
    // Fresh fiber: the guest OSContext inside the block (block+0x20) already"""

A2 = """    GameFiber& cur = g_gameFibers[curBlock];"""
R2 = """    // Batch 125: witness the switch and the target block's job descriptor.
    {
        static int s_w125 = 0;
        if (s_w125 < 120) {
            ++s_w125;
            try {
                auto itT = g_gameFibers.find(newBlock);
                const bool tgtStarted = itT != g_gameFibers.end() && itT->second.started;
                RT_LOG(RT_TAG_OS) << "[w125] switch cur=0x" << std::hex << curBlock
                                  << " new=0x" << newBlock
                                  << " fn=0x" << ::Memory::Read32(newBlock)
                                  << " arg=0x" << ::Memory::Read32(newBlock + 4u)
                                  << " srr0=0x" << ::Memory::Read32(newBlock + 0x20u + 0x198u)
                                  << " sp=0x" << ::Memory::Read32(newBlock + 0x20u + 4u)
                                  << " tgtStarted=" << (tgtStarted ? 1 : 0)
                                  << " callerLR=0x" << ctx->lr
                                  << std::dec << std::endl;
            } catch (...) {
            }
        }
    }
    GameFiber& cur = g_gameFibers[curBlock];"""

for name, a in (("A1 GameFiberProc", A1), ("A2 switch", A2)):
    n = TEXT.count(a)
    if n != 1:
        print(f"FATAL: anchor {name} found {n} times (need exactly 1); no writes made")
        sys.exit(1)

backup = TARGET.with_name(TARGET.name + ".bak-pre125")
if not backup.exists():
    shutil.copy2(TARGET, backup)
    print(f"backup written: {backup}")

TEXT = TEXT.replace(A1, R1).replace(A2, R2)
TARGET.write_text(TEXT, encoding="utf-8")
print("batch 125 applied to os_context.cpp")
