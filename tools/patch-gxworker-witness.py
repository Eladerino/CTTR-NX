#!/usr/bin/env python3
# Batch 118: mirror the GX worker's timing truth into cttr-witness.txt.
#
# gx_worker.cpp already computes exactly what we need (per-window records /
# drains / game-thread wait ms in PrintPerfWindow) but prints it with
# fprintf(stderr), which never reaches the redirected console logs for this
# GUI-subsystem build. Batch 118 adds witness-file lines:
#   [w118] window ...   -- PrintPerfWindow aggregates + a host address anchor
#                          (&PrintPerfWindow) for symbol-slide resolution
#   [w118] drainwait .. -- any WaitForWorker call that blocked >= 3 ms, with
#                          published at entry/exit and wait-service call count
#   [w118] replay ..    -- any ReplayRange that took >= 3 ms, with record
#                          count and whether it ran on the worker thread
#                          (few records + long ms = one blocking record)
# All lines capped so the witness stays readable.
#
# Usage: run with CWD = tree root (path is relative, like batches 114/116).
import pathlib, shutil, sys

p = pathlib.Path("runtime/src/hle/gx/gx_worker.cpp")
src = p.read_text(encoding="utf-8", errors="surrogateescape")
if "Batch 118" in src:
    print("batch 118 already applied, skipping")
    sys.exit(0)

# --- Edit A: WaitForWorker instrumentation -------------------------------
old_a = """    Worker& w = *g_worker;
    const auto start = std::chrono::steady_clock::now();
    bool waited = false;
    std::unique_lock lock(w.mutex);
    while (w.consumed != w.published) {
        waited = true;
        if (w.idleCv.wait_for(lock, std::chrono::milliseconds(1), [&w] { return w.consumed == w.published; })) {
            break;
        }
        if (g_waitService != nullptr) {
            lock.unlock();
            g_waitService();
            lock.lock();
        }
    }
    w.consumed = 0;"""
new_a = """    Worker& w = *g_worker;
    const auto start = std::chrono::steady_clock::now();
    bool waited = false;
    std::unique_lock lock(w.mutex);
    const size_t pub118 = w.published;  // Batch 118 (CTTR diagnostic)
    int svc118 = 0;                     // Batch 118
    while (w.consumed != w.published) {
        waited = true;
        if (w.idleCv.wait_for(lock, std::chrono::milliseconds(1), [&w] { return w.consumed == w.published; })) {
            break;
        }
        if (g_waitService != nullptr) {
            ++svc118;  // Batch 118
            lock.unlock();
            g_waitService();
            lock.lock();
        }
    }
    {  // Batch 118 (CTTR diagnostic): long drain waits to the witness file.
        static int s_w118n = 0;
        const long long ms118 = std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now() - start).count();
        if (waited && ms118 >= 3 && s_w118n < 150) {
            ++s_w118n;
            if (FILE* tf = fopen("cttr-witness.txt", "a")) { fprintf(tf, "[w118] drainwait %lld ms pub %zu -> %zu svc %d\\n", ms118, pub118, w.published, svc118); fclose(tf); }
        }
    }
    w.consumed = 0;"""
if src.count(old_a) != 1:
    print(f"ANCHOR A FAIL count={src.count(old_a)}")
    sys.exit(1)
src = src.replace(old_a, new_a, 1)

# --- Edit B: ReplayRange timing ------------------------------------------
old_b = """void ReplayRange(size_t from, size_t to, bool immediate) {
    size_t read = AlignUp(from);  // `from` is a payload end (a published end); the next record is aligned
    while (read < to) {
        RecordHeader* header = HeaderAt(read);
        void* payload = g_ring + read + sizeof(RecordHeader);
        read = AlignUp(read + sizeof(RecordHeader) + header->size);"""
new_b = """void ReplayRange(size_t from, size_t to, bool immediate) {
    const auto t118 = std::chrono::steady_clock::now();  // Batch 118 (CTTR diagnostic)
    size_t recs118 = 0;                                  // Batch 118
    size_t read = AlignUp(from);  // `from` is a payload end (a published end); the next record is aligned
    while (read < to) {
        RecordHeader* header = HeaderAt(read);
        void* payload = g_ring + read + sizeof(RecordHeader);
        read = AlignUp(read + sizeof(RecordHeader) + header->size);
        ++recs118;  // Batch 118"""
if src.count(old_b) != 1:
    print(f"ANCHOR B FAIL count={src.count(old_b)}")
    sys.exit(1)
src = src.replace(old_b, new_b, 1)

old_b2 = """        } catch (...) {
            g_replayErrors.Add();
            std::fprintf(stderr, "[gxworker] a deferred GX call threw\\n");
        }
    }
}"""
new_b2 = """        } catch (...) {
            g_replayErrors.Add();
            std::fprintf(stderr, "[gxworker] a deferred GX call threw\\n");
        }
    }
    {  // Batch 118 (CTTR diagnostic): slow replay ranges to the witness file.
        static int s_r118n = 0;
        const long long ms118 = std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now() - t118).count();
        if (ms118 >= 3 && s_r118n < 150) {
            ++s_r118n;
            if (FILE* tf = fopen("cttr-witness.txt", "a")) { fprintf(tf, "[w118] replay [%zu,%zu) %lld ms recs %zu worker %d imm %d\\n", from, to, ms118, recs118, t_worker ? 1 : 0, immediate ? 1 : 0); fclose(tf); }
        }
    }
}"""
if src.count(old_b2) != 1:
    print(f"ANCHOR B2 FAIL count={src.count(old_b2)}")
    sys.exit(1)
src = src.replace(old_b2, new_b2, 1)

# --- Edit C: PrintPerfWindow witness mirror -------------------------------
old_c = """                     static_cast<double>(waitMicros) / 1000.0 / frames, static_cast<unsigned long long>(unsafeDrains));
    }"""
new_c = """                     static_cast<double>(waitMicros) / 1000.0 / frames, static_cast<unsigned long long>(unsafeDrains));
    }
    {  // Batch 118 (CTTR diagnostic): the same aggregates to the witness file
       // (fprintf(stderr) never reaches the console log for this build), plus
       // a host address anchor for symbol-slide resolution.
        if (FILE* tf = fopen("cttr-witness.txt", "a")) {
            fprintf(tf, "[w118] window frames %llu-%llu mode %u recs/f %.1f drains/f %.1f peakKB %llu full %llu err %llu waitms/f %.2f unsafe %llu anchor %p\\n",
                    static_cast<unsigned long long>(firstFrame), static_cast<unsigned long long>(lastFrame),
                    static_cast<unsigned>(mode), static_cast<double>(records) / frames,
                    static_cast<double>(drains) / frames, static_cast<unsigned long long>(peak / 1024),
                    static_cast<unsigned long long>(full), static_cast<unsigned long long>(errors),
                    static_cast<double>(waitMicros) / 1000.0 / frames,
                    static_cast<unsigned long long>(unsafeDrains),
                    reinterpret_cast<void*>(&PrintPerfWindow));
            fclose(tf);
        }
    }"""
if src.count(old_c) != 1:
    print(f"ANCHOR C FAIL count={src.count(old_c)}")
    sys.exit(1)
src = src.replace(old_c, new_c, 1)

shutil.copy2(p, "gx_worker.cpp.bak-pre118")
p.write_text(src, encoding="utf-8", errors="surrogateescape")
print("batch 118 applied OK")
