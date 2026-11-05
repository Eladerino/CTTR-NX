import sys

path = sys.argv[1] if len(sys.argv) > 1 else r"runtime\src\hle\os\os_context.cpp"
src = open(path, encoding="utf-8").read()

if "GameFiberSwitch_CTTR" in src:
    print("already patched:", path)
    sys.exit(0)

# 1. Includes (after the os_internal.h include line).
anchor = '#include "os_internal.h"'
if src.count(anchor) != 1:
    print("INCLUDE ANCHOR PROBLEM: count =", src.count(anchor))
    sys.exit(1)
includes = anchor + '\n#include "fiber_manager.h"\n#include "host_context.h"\n#include "isa/ppc_isa_context.h"\n#include <unordered_map>'
src = src.replace(anchor, includes)

# 2. The HLE switch impl + override, appended at end of file.
impl = r'''

// ---- CTTR cooperative game fibers (batch 26) ----
// Radical's loader fibers are cooperative coroutines living INSIDE one OS
// thread, switched by guest fn_8024C870 via guest OSSaveContext/OSLoadContext.
// Modeling that switch with the shared-context OSLoadContext unwinds guest
// frames with the other fiber's registers: the instruction after the switch's
// OSLoadContext call is dead code on hardware (OSLoadContext never returns
// there; a fiber resumes through its saved srr0), but it executes in the
// nested-invocation model and clobbers the caller's saved registers (the
// loader drain then reloads r30 as a fiber-block pointer and pops a null
// completion). So the switch itself is HLE-owned here: each guest fiber block
// maps to a real host fiber with its own saved CpuContext, switched with the
// same save/copy/Switch discipline GuestFiberManager uses for OS threads.
namespace {
struct GameFiber {
    HostContext::Handle handle = nullptr;
    CpuContext saved{};
    bool started = false;
    bool terminated = false;
    uint32_t lastSwitcher = 0;
};
std::unordered_map<uint32_t, GameFiber> g_gameFibers;

void GameFiberProc(void* param) {
    const uint32_t block =
        static_cast<uint32_t>(reinterpret_cast<uintptr_t>(param));
    CpuContext* cpu = &GetPersistentCpuContext();
    CpuContextScope scope(cpu);
    // Fresh fiber: the guest OSContext inside the block (block+0x20) already
    // holds the trampoline entry (srr0 = fn_8024C8E4), the fiber stack and
    // the SDA bases. Reuse OS__LoadContext to materialize it and jump in.
    cpu->gpr[3] = block + 0x20u;
    OS__LoadContext_801a1f58(cpu);
    // The guest fiber proc is not expected to return. If it does, the fiber
    // is finished: hand control back to whoever last switched to it.
    GameFiber& self = g_gameFibers[block];
    self.terminated = true;
    auto it = g_gameFibers.find(self.lastSwitcher);
    if (it != g_gameFibers.end() && it->second.handle) {
        *cpu = it->second.saved;
        HostContext::Switch(it->second.handle);
    }
    // Nowhere to go back to: park rather than return into the host backend.
    for (;;) {
        std::this_thread::sleep_for(std::chrono::hours(24));
    }
}
} // namespace

extern "C" void GameFiberSwitch_CTTR(CpuContext* ctx) {
    const uint32_t newBlock = ctx->gpr[3];
    if (!newBlock) {
        return;
    }
    const uint32_t curThread = ::Memory::Read32(0x800000E4u); // __OSCurrentThread
    uint32_t curBlock = 0;
    if (curThread) {
        curBlock = ::Memory::Read32(curThread + 0x2F8u);
        // Guest bookkeeping, mirrors fn_8024C870: current block becomes newBlock.
        ::Memory::Write32(curThread + 0x2F8u, newBlock);
    }
    OS__DisableInterrupts_801a65ac();
    if (curBlock == newBlock) {
        OS__EnableInterrupts_801a65c0();
        return;
    }
    GameFiber& cur = g_gameFibers[curBlock];
    if (!cur.started) {
        // First switch away from this block: it executes on the OS thread's
        // own host fiber; borrow that handle so switches can return here.
        cur.started = true;
        if (Fiber::GuestFiber* gf = Fiber::GuestFiberManager::GetFiber(curThread)) {
            cur.handle = gf->fiber;
        }
    }
    cur.saved = *ctx;
    GameFiber& tgt = g_gameFibers[newBlock];
    tgt.lastSwitcher = curBlock;
    if (!tgt.started) {
        tgt.started = true;
        tgt.handle = HostContext::Create(
            1024 * 1024, &GameFiberProc,
            reinterpret_cast<void*>(static_cast<uintptr_t>(newBlock)));
        if (!tgt.handle) {
            RT_LOG(RT_TAG_OS) << "GameFiberSwitch: host fiber create failed for block 0x"
                              << std::hex << newBlock << std::dec << std::endl;
            OS__EnableInterrupts_801a65c0();
            return;
        }
        HostContext::Switch(tgt.handle);
    } else if (!tgt.terminated) {
        *ctx = tgt.saved;
        MkwApplyHostNiMode(ctx->fpscr);
        HostContext::Switch(tgt.handle);
    }
    // Resumed (or the target finished instantly): whoever switched back has
    // already restored our saved CpuContext into *ctx, per the same
    // discipline. The guest switch re-enables interrupts on the resume path.
    OS__EnableInterrupts_801a65c0();
}
PPC_NATIVE_OVERRIDE_VOID(8024C870, GameFiberSwitch_CTTR, (CpuContext* ctx), (ctx));
'''
src += impl
open(path, "w", encoding="utf-8").write(src)
print("patched:", path)
