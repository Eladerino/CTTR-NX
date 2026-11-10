# Batch 214 (CTTR diagnostic): extend the batch-187
# __OSCurrentThread watch (watch-2) to every alias
# page of the low word.
#
# The [w187] poller sees [0x800000E4] become
# 0x00100010 at the attract start, but the watch
# never logs the write: watch-2 only protects the
# cached guest page (g_base+0x80000000). The write
# must arrive via the physical (0x000000E4) or
# uncached (0xC00000E4) guest alias, or via the
# host alias that ::Memory::Write32 uses -- the
# same blind spot batch 198/199 closed for the
# [P+84] watch. The native write sites
# (os_scheduler's SelectThread, os_sleep's
# default-thread path) publish whatever thread
# identity they hold; this watch catches the
# store itself, whichever mapping carries it,
# and the completion log gains host=%d.
#
# One file: guest_flat_memory.cpp (runtime-only,
# no emit). Idempotent via the "Batch 214"
# marker; backup .bak-pre214. Honours CTTR_ROOT.

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled"))
MARKER = "Batch 214"
GFM = ROOT / "runtime" / "src" / "guest_flat_memory.cpp"

EDITS = [
    # 1. Alias page statics.
    (
        "uint8_t* s_watch2Page = nullptr;",
        "uint8_t* s_watch2Page = nullptr;\n"
        "uint8_t* s_watch2PagePhys = nullptr;  // Batch 214: physical alias page\n"
        "uint8_t* s_watch2PageUnc = nullptr;  // Batch 214: uncached alias page\n"
        "uint8_t* s_watch2PageHost = nullptr;  // Batch 214: host-alias page\n"
        "thread_local uint8_t* s_watch2OpenPage = nullptr;  // Batch 214\n"
        "thread_local bool s_watch2StepHost = false;  // Batch 214",
        1,
    ),
    # 2. AV fault block: match any alias page.
    (
        "    // Batch 187: __OSCurrentThread page write watch (low page).\n"
        "    if (s_watch2Armed.load() && isWrite && s_watch2Page != nullptr &&\n"
        "        faultAddress >= s_watch2Page &&\n"
        "        faultAddress < s_watch2Page + kHostPageSize) {\n"
        "        const uint32_t guestAddr = 0x80000000u +\n"
        "            static_cast<uint32_t>(static_cast<uint8_t*>(faultAddress) - s_watch2Page);\n"
        "        if (guestAddr < 0x800000E8u && guestAddr + 8u > 0x800000E4u) {\n"
        "            s_watch2StepAddr = guestAddr;\n"
        "            s_watch2StepRip = static_cast<uintptr_t>(info->ContextRecord->Rip);\n"
        "            try { s_watch2StepActive = RecompMod::CurrentTranslatedExecutionAddress(); } catch (...) { s_watch2StepActive = 0; }\n"
        "        } else {\n"
        "            s_watch2StepAddr = 0;\n"
        "        }\n"
        "        ProtectRange(s_watch2Page, kHostPageSize, kProtReadWrite);\n"
        "        info->ContextRecord->EFlags |= 0x100u;\n"
        "        s_watch2StepPending = true;\n"
        "        return EXCEPTION_CONTINUE_EXECUTION;\n"
        "    }",
        "    // Batch 187: __OSCurrentThread page write watch (low page).\n"
        "    // Batch 214: match the physical/uncached alias pages and the\n"
        "    // host-alias page too -- the 0x00100010 write never crossed the\n"
        "    // cached page this watch originally protected.\n"
        "    if (s_watch2Armed.load() && isWrite) {\n"
        "        uint8_t* hitPage = nullptr;\n"
        "        uint32_t aliasBase = 0;\n"
        "        bool hostHit = false;\n"
        "        if (s_watch2Page != nullptr && faultAddress >= s_watch2Page &&\n"
        "            faultAddress < s_watch2Page + kHostPageSize) {\n"
        "            hitPage = s_watch2Page; aliasBase = 0x80000000u;\n"
        "        } else if (s_watch2PagePhys != nullptr && faultAddress >= s_watch2PagePhys &&\n"
        "                   faultAddress < s_watch2PagePhys + kHostPageSize) {\n"
        "            hitPage = s_watch2PagePhys; aliasBase = 0x00000000u;\n"
        "        } else if (s_watch2PageUnc != nullptr && faultAddress >= s_watch2PageUnc &&\n"
        "                   faultAddress < s_watch2PageUnc + kHostPageSize) {\n"
        "            hitPage = s_watch2PageUnc; aliasBase = 0xC0000000u;\n"
        "        } else if (s_watch2PageHost != nullptr && faultAddress >= s_watch2PageHost &&\n"
        "                   faultAddress < s_watch2PageHost + kHostPageSize) {\n"
        "            hitPage = s_watch2PageHost; aliasBase = 0x80000000u; hostHit = true;\n"
        "        }\n"
        "        if (hitPage != nullptr) {\n"
        "            const uint32_t guestAddr = aliasBase +\n"
        "                static_cast<uint32_t>(static_cast<uint8_t*>(faultAddress) - hitPage);\n"
        "            if (guestAddr < 0x800000E8u && guestAddr + 8u > 0x800000E4u) {\n"
        "                s_watch2StepAddr = guestAddr;\n"
        "                s_watch2StepRip = static_cast<uintptr_t>(info->ContextRecord->Rip);\n"
        "                s_watch2StepHost = hostHit;\n"
        "                try { s_watch2StepActive = RecompMod::CurrentTranslatedExecutionAddress(); } catch (...) { s_watch2StepActive = 0; }\n"
        "            } else {\n"
        "                s_watch2StepAddr = 0;\n"
        "            }\n"
        "            s_watch2OpenPage = hitPage;\n"
        "            ProtectRange(hitPage, kHostPageSize, kProtReadWrite);\n"
        "            info->ContextRecord->EFlags |= 0x100u;\n"
        "            s_watch2StepPending = true;\n"
        "            return EXCEPTION_CONTINUE_EXECUTION;\n"
        "        }\n"
        "    }",
        1,
    ),
    # 3. Completion: log host flag; re-protect the opened page.
    (
        '                    fprintf(wf, "[w187] curthread write value=0x%08X rip=0x%llX active=0x%08X\\n",\n'
        "                            value, static_cast<unsigned long long>(s_watch2StepRip),\n"
        "                            s_watch2StepActive);",
        '                    fprintf(wf, "[w187] curthread write value=0x%08X rip=0x%llX active=0x%08X host=%d\\n",  // Batch 214\n'
        "                            value, static_cast<unsigned long long>(s_watch2StepRip),\n"
        "                            s_watch2StepActive, s_watch2StepHost ? 1 : 0);",
        1,
    ),
    (
        "        s_watch2StepAddr = 0;\n"
        "        if (s_watch2Armed.load() && s_watch2Page != nullptr) {\n"
        "            ProtectRange(s_watch2Page, kHostPageSize, kProtRead);\n"
        "        }\n"
        "        return EXCEPTION_CONTINUE_EXECUTION;\n"
        "    }",
        "        s_watch2StepAddr = 0;\n"
        "        s_watch2StepHost = false;\n"
        "        if (s_watch2OpenPage != nullptr) {  // Batch 214: re-protect the opened alias page\n"
        "            ProtectRange(s_watch2OpenPage, kHostPageSize, kProtRead);\n"
        "            s_watch2OpenPage = nullptr;\n"
        "        }\n"
        "        return EXCEPTION_CONTINUE_EXECUTION;\n"
        "    }",
        1,
    ),
    # 4. Arm: set + protect all alias pages.
    (
        "    s_watch2Page = g_base + 0x80000000u;\n"
        "    if (ProtectRange(s_watch2Page, kHostPageSize, kProtRead)) {",
        "    s_watch2Page = g_base + 0x80000000u;\n"
        "    s_watch2PagePhys = g_base + 0x00000000u;  // Batch 214: alias pages\n"
        "    s_watch2PageUnc = g_base + 0xC0000000u;  // Batch 214\n"
        "    s_watch2PageHost = HostPointer(0x800000E4u) - (0x800000E4u & 0xFFFu);  // Batch 214\n"
        "    if (s_watch2PageHost != nullptr) { (void)ProtectRange(s_watch2PageHost, kHostPageSize, kProtRead); }  // Batch 214: lenient\n"
        "    if (ProtectRange(s_watch2Page, kHostPageSize, kProtRead) &&\n"
        "        ProtectRange(s_watch2PagePhys, kHostPageSize, kProtRead) &&  // Batch 214\n"
        "        ProtectRange(s_watch2PageUnc, kHostPageSize, kProtRead)) {  // Batch 214",
        1,
    ),
]


def fail(msg):
    print("FAIL:", msg)
    sys.exit(1)


def main():
    if not GFM.exists():
        fail(f"missing file: {GFM}")
    text = GFM.read_text()
    if MARKER in text:
        print("already applied, skipping")
        return
    for idx, (old, new, want) in enumerate(EDITS):
        got = text.count(old)
        if got != want:
            fail(f"guest_flat_memory.cpp edit {idx}: anchor count {got} != {want}")
        text = text.replace(old, new, 1)
    backup = GFM.with_name(GFM.name + ".bak-pre214")
    if not backup.exists():
        shutil.copy2(GFM, backup)
    GFM.write_text(text)
    print("patched: guest_flat_memory.cpp")
    print("Batch 214 applied (runtime-only, no emit).")


if __name__ == "__main__":
    main()
