import sys

path = sys.argv[1] if len(sys.argv) > 1 else r"runtime\src\hle\os\os_internal.h"
src = open(path, encoding="utf-8").read()

old = 'extern "C" [[noreturn]] void OS__LoadContext_801a1f58(CpuContext* ctx);'
new = 'extern "C" void OS__LoadContext_801a1f58(CpuContext* ctx);'

if new in src and old not in src:
    print("already patched:", path)
    sys.exit(0)
if src.count(old) != 1:
    print("ANCHOR PROBLEM: count =", src.count(old), "in", path)
    sys.exit(1)
open(path, "w", encoding="utf-8").write(src.replace(old, new))
print("patched:", path)
