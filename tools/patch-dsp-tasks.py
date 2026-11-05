import sys

path = sys.argv[1] if len(sys.argv) > 1 else r"runtime\src\hle\audio\audio.cpp"
src = open(path, encoding="utf-8").read()

if "8035C0FC" in src:
    print("already patched:", path)
    sys.exit(0)

impl = r'''

// ---- CTTR DSP task family (batch 28) ----
// Guest DSPAddTask reads the DSP control register while queueing the AX
// task; the runtime's AxDspHle owns the task model instead.
PPC_NATIVE_OVERRIDE(8035C0FC, DSPAddTask_8015d50c, uint32_t, (uint32_t task_ptr), (task_ptr));
PPC_NATIVE_OVERRIDE(8035C1AC, DSPAssertTask_8015d57c, uint32_t, (uint32_t taskPtr), (taskPtr));
PPC_NATIVE_OVERRIDE_VOID(8035C888, __DSP_boot_task_8015dc60, (uint32_t task_ptr), (task_ptr));
'''
src += impl
open(path, "w", encoding="utf-8").write(src)
print("patched:", path)
