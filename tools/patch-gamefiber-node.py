import sys

path = sys.argv[1] if len(sys.argv) > 1 else r"runtime\src\hle\os\os_context.cpp"
src = open(path, encoding="utf-8").read()

if "GameFiberCurrentNode" in src:
    print("already patched:", path)
    sys.exit(0)

# 1. Node resolver, inserted before GameFiberSwitch_CTTR.
anchor_fn = 'extern "C" void GameFiberSwitch_CTTR(CpuContext* ctx) {'
if src.count(anchor_fn) != 1:
    print("FN ANCHOR PROBLEM: count =", src.count(anchor_fn))
    sys.exit(1)
helper = r'''// The game tracks each OS thread's current fiber block in its own thread
// wrapper registry, not in the OSThread struct: fn_8024C65C walks the list
// headed at *(r13+0x2A78), matching node+0x310 against OSGetCurrentThread(),
// and fn_8024C6C0 reads the block from node+0x2F8. Mirror that resolution.
uint32_t GameFiberCurrentNode(CpuContext* ctx) {
    const uint32_t curThread = ::Memory::Read32(0x800000E4u); // __OSCurrentThread
    if (!curThread) {
        return 0;
    }
    uint32_t node = ::Memory::Read32(ctx->gpr[13] + 0x2A78u);
    while (node) {
        if (::Memory::Read32(node + 0x310u) == curThread) {
            return node;
        }
        node = ::Memory::Read32(node);
    }
    return 0;
}

extern "C" void GameFiberSwitch_CTTR(CpuContext* ctx) {'''
src = src.replace(anchor_fn, helper, 1)

# The helper sits inside the anonymous namespace opened for GameFiber; the
# replace above closed it before the extern fn, so drop the now-duplicated
# namespace close that followed the original function signature block.
old_book = '''    const uint32_t curThread = ::Memory::Read32(0x800000E4u); // __OSCurrentThread
    uint32_t curBlock = 0;
    if (curThread) {
        curBlock = ::Memory::Read32(curThread + 0x2F8u);
        // Guest bookkeeping, mirrors fn_8024C870: current block becomes newBlock.
        ::Memory::Write32(curThread + 0x2F8u, newBlock);
    }'''
new_book = '''    const uint32_t curThread = ::Memory::Read32(0x800000E4u); // __OSCurrentThread
    uint32_t curBlock = 0;
    const uint32_t node = GameFiberCurrentNode(ctx);
    if (node) {
        curBlock = ::Memory::Read32(node + 0x2F8u);
        // Guest bookkeeping, mirrors fn_8024C870: current block becomes newBlock.
        ::Memory::Write32(node + 0x2F8u, newBlock);
    } else if (curThread) {
        curBlock = ::Memory::Read32(curThread + 0x2F8u);
        ::Memory::Write32(curThread + 0x2F8u, newBlock);
    }'''
if src.count(old_book) != 1:
    print("BOOKKEEPING ANCHOR PROBLEM: count =", src.count(old_book))
    sys.exit(1)
src = src.replace(old_book, new_book, 1)

open(path, "w", encoding="utf-8").write(src)
print("patched:", path)
