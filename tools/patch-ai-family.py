import sys

path = sys.argv[1] if len(sys.argv) > 1 else r"runtime\src\hle\audio\audio.cpp"
src = open(path, encoding="utf-8").read()

if "80354B60" in src:
    print("already patched:", path)
    sys.exit(0)

retargets = [
    ("constexpr uint32_t kAIInitializedAddr = 0x8056DDD0u;",
     "constexpr uint32_t kAIInitializedAddr = 0x804AEC08u;"),
    ("constexpr uint32_t kAICallbackBusyAddr = 0x8056DDD4u;",
     "constexpr uint32_t kAICallbackBusyAddr = 0x804AEC0Cu;"),
    ("constexpr uint32_t kAICallbackStackSwitchAddr = 0x8056DE04u;",
     "constexpr uint32_t kAICallbackStackSwitchAddr = 0x804AEC00u;"),
    ("constexpr uint32_t kAIDmaCallbackAddr = 0x8056DE08u;",
     "constexpr uint32_t kAIDmaCallbackAddr = 0x804AEBFCu;"),
]
for old, new in retargets:
    if src.count(old) != 1:
        print("RETARGET ANCHOR PROBLEM:", old, "count =", src.count(old))
        sys.exit(1)
    src = src.replace(old, new)

impl = r'''

// ---- CTTR AI family (batch 27) ----
// The four guest-state constants above now hold CTTR's .sbss addresses
// (__CallbackStack 0x804AEC00, __AID_Callback 0x804AEBFC, __AI_init_flag
// 0x804AEC08, __AID_Active 0x804AEC0C — same layout order as the decomp ai.c).
extern "C" void AIStopDMA_CTTR() {
    std::lock_guard<std::mutex> lock(g_ai.mutex);
    g_ai.enabled = false;
}
extern "C" void AISetDSPSampleRate_CTTR(uint32_t rate_flag) {
    // SDK convention: 0 = 32 kHz, 1 = 48 kHz (mirrors AIGetDSPSampleRate).
    std::lock_guard<std::mutex> lock(g_ai.mutex);
    g_ai.sampleRate = rate_flag ? 48000u : 32000u;
}
PPC_NATIVE_OVERRIDE_VOID(80354B60, AIInit_801240b0, (uint32_t callback_stack_switch), (callback_stack_switch));
PPC_NATIVE_OVERRIDE_VOID(80354790, AIInitDMA_80123fcc, (uint32_t start_addr, uint32_t length), (start_addr, length));
PPC_NATIVE_OVERRIDE(8035474C, AIRegisterDMACallback_80123f88, uint32_t, (uint32_t callback), (callback));
PPC_NATIVE_OVERRIDE_VOID(80354818, AIStartDMA_80124048, (), ());
PPC_NATIVE_OVERRIDE_VOID(80354830, AIStopDMA_CTTR, (), ());
PPC_NATIVE_OVERRIDE(80354A10, AIGetDSPSampleRate_8012409c, uint32_t, (), ());
PPC_NATIVE_OVERRIDE_VOID(80354930, AISetDSPSampleRate_CTTR, (uint32_t rate_flag), (rate_flag));
'''
src += impl
open(path, "w", encoding="utf-8").write(src)
print("patched:", path)
