#!/usr/bin/env python3
# Batch 52 (FIX): preserve stream phase across Aurora fifo
# drains. Proven defect (batch 51 dumps): buffer1 ends
# mid-BP-command (61 00 3d 53 + 1 byte) -- drains cut the
# encoded stream at arbitrary points, process() requires
# command-aligned input, and on hard errors it discards
# the rest of the buffer, so the next drain starts with
# continuation bytes and decodes as garbage (the CALL_DL
# flood / 3510 whole-buffer discards).
#
# Fix, two halves:
#  1. process() reports a TRUNCATED final command instead
#     of pretending the buffer was fully consumed:
#       - handle_draw() failure now returns commandStart
#         (was: return size).
#       - handle_xf() truncation sets pos = size + 1
#         (sentinel); a new lastCmdStart tracker makes the
#         final return yield lastCmdStart when pos > size
#         (covers BP/CP/INDX/CALL_DL tail overruns).
#     Genuine hard errors (unknown Aurora subcommand)
#     still return size (discard), as today.
#  2. drain() keeps the undecoded tail: the count==0 &&
#     retried throw becomes a break, and the final
#     sBufferSize = 0 reset becomes a memmove that carries
#     [consumed, size) to the front for the next drain.
#     A tail that makes zero progress for >16 drains is
#     dropped with a log line (poison guard). Aligned
#     streams are unaffected: leftover is 0, as today.
#
# Structural (brace-tracked) anchoring; every site is
# verified before anything is written; a miss aborts
# with the site name and every file untouched.
# Backups: .bak-pre52. Idempotent via Batch 52 markers.
# Usage: python - [tree-root]   (default root: .)
import os, shutil, sys

ROOT = sys.argv[1] if len(sys.argv) > 1 else "."

def fail(site, why):
    print(f"ANCHOR FAIL ({site}): {why}; aborting, nothing written")
    sys.exit(1)

def depth_delta(line):
    return line.count("{") - line.count("}")

# ---------------- command_processor.cpp ----------------

PROC_SIG = "uint32_t process(const u8* data, u32 size, bool bigEndian) {"
DRAW_RET = "if (!handle_draw(cmd, data, pos, size, bigEndian)) return size;"
XF_SIG = "static void handle_xf(const u8* data, u32& pos, u32 size, bool bigEndian) {"

def patch_cp(text):
    lines = text.split("\n")
    if any("Batch 52" in ln for ln in lines):
        return None
    # locate process() span by brace tracking
    sig = [i for i, ln in enumerate(lines) if PROC_SIG in ln]
    if len(sig) != 1:
        fail("command_processor.cpp:process-sig", f"found {len(sig)} (want 1)")
    start = sig[0]
    depth = 0; end = None; while_i = None; final_ret = None
    base_depth = None; while_depth = None; loop_closed = False
    for i in range(start, len(lines)):
        ln = lines[i]; stripped = ln.strip()
        if i == start:
            depth += depth_delta(ln); base_depth = depth; continue
        if while_i is not None and final_ret is None and loop_closed \
                and depth == while_depth and stripped == "return size;":
            final_ret = i
        if while_i is None and "while (pos < size) {" in ln:
            while_i = i; while_depth = depth
        depth += depth_delta(ln)
        if while_i is not None and not loop_closed and depth == while_depth:
            loop_closed = True
        if depth < base_depth:
            end = i; break
    if while_i is None:
        fail("command_processor.cpp:process-while", "no 'while (pos < size) {' inside process()")
    if final_ret is None:
        fail("command_processor.cpp:process-final-return", "could not locate process()'s final 'return size;'")
    # (b) lastCmdStart declaration: 'u32 pos = 0;' before the while
    decl = [i for i in range(start, while_i) if lines[i].strip() == "u32 pos = 0;"]
    if len(decl) != 1:
        fail("command_processor.cpp:process-decl", f"found {len(decl)} 'u32 pos = 0;' before the loop (want 1)")
    # (c) loop-top: 'const u32 commandStart = pos;'
    top = [i for i in range(while_i, final_ret) if lines[i].strip() == "const u32 commandStart = pos;"]
    if len(top) != 1:
        fail("command_processor.cpp:process-loop-top", f"found {len(top)} commandStart lines (want 1)")
    # (a) handle_draw return
    dr = [i for i in range(start, end if end else len(lines)) if DRAW_RET in lines[i]]
    if len(dr) != 1:
        fail("command_processor.cpp:draw-return", f"found {len(dr)} handle_draw return lines (want 1)")
    # handle_xf sentinel: exactly 2 'pos = size;' in its first 30 lines
    xsig = [i for i, ln in enumerate(lines) if XF_SIG in ln]
    if len(xsig) != 1:
        fail("command_processor.cpp:xf-sig", f"found {len(xsig)} handle_xf definitions (want 1)")
    xf = [i for i in range(xsig[0], min(xsig[0] + 30, len(lines))) if lines[i].strip() == "pos = size;"]
    if len(xf) != 2:
        fail("command_processor.cpp:xf-sentinel", f"found {len(xf)} 'pos = size;' lines in handle_xf head (want 2)")

    # apply edits bottom-up so indices stay valid
    edits = []
    edits.append((final_ret, "final"))
    edits.append((dr[0], "draw"))
    edits.append((top[0], "top"))
    edits.append((decl[0], "decl"))
    for i in xf:
        edits.append((i, "xf"))
    for i, kind in sorted(edits, reverse=True):
        if kind == "final":
            lines[i] = lines[i].replace("return size;",
                "return pos > size ? lastCmdStart : size;  // Batch 52: a truncated final command reports its start so drain() can carry its bytes forward.", 1)
        elif kind == "draw":
            lines[i] = lines[i].replace("return size;", "return commandStart;", 1) + \
                "  // Batch 52: truncated draw -- report the draw's start so drain() carries its bytes forward (was: return size, discarding them)."
        elif kind == "top":
            lines[i] = lines[i] + "\n    lastCmdStart = commandStart;  // Batch 52"
        elif kind == "decl":
            lines[i] = lines[i] + "\n  u32 lastCmdStart = 0;  // Batch 52: start of the most recent command (truncation reporting)."
        elif kind == "xf":
            lines[i] = lines[i].replace("pos = size;",
                "pos = size + 1;  // Batch 52: truncation sentinel -- process() reports this command as incomplete.", 1)
    return "\n".join(lines)

# ---------------- fifo.cpp ----------------

DRAIN_SIG = "void drain() {"
THROW_NEEDLE = "if (count == 0 && retried)"
RESET_LINE = "detail::sBufferSize = 0;"
PRESERVE = [
    "  // Batch 52: carry any undecoded tail (a command cut by the drain",
    "  // boundary) into the next drain instead of dropping it, so the",
    "  // stream's phase survives across drains. A tail that makes no",
    "  // progress for many drains is dropped to avoid a permanent block.",
    "  {",
    "    static int s_cttrStuckDrains = 0;",
    "    const uint32_t leftover = detail::sBufferSize - consumed;",
    "    if (leftover == 0) {",
    "      s_cttrStuckDrains = 0;",
    "      detail::sBufferSize = 0;",
    "    } else if (consumed == 0 && ++s_cttrStuckDrains > 16) {",
    '      Log.warn("[cttr-dbg] dropping {} stuck undecoded FIFO bytes after {} drains", detail::sBufferSize, s_cttrStuckDrains);',
    "      s_cttrStuckDrains = 0;",
    "      detail::sBufferSize = 0;",
    "    } else {",
    "      if (consumed > 0) s_cttrStuckDrains = 0;",
    "      std::memmove(detail::sBufferData, detail::sBufferData + consumed, leftover);",
    "      detail::sBufferSize = leftover;",
    "    }",
    "  }",
]

def patch_fifo(text):
    lines = text.split("\n")
    if any("Batch 52" in ln for ln in lines):
        return None
    sig = [i for i, ln in enumerate(lines) if ln.strip() == DRAIN_SIG]
    if len(sig) != 1:
        fail("fifo.cpp:drain-sig", f"found {len(sig)} (want 1)")
    start = sig[0]
    thr = [i for i in range(start, min(start + 90, len(lines))) if THROW_NEEDLE in lines[i]]
    if len(thr) != 1:
        fail("fifo.cpp:drain-throw", f"found {len(thr)} count==0 throw lines in drain() (want 1)")
    # the throw statement sits on the line after the if (braceless if);
    # it must be consumed too, or it becomes unconditional
    if thr[0] + 1 >= len(lines) or "throw" not in lines[thr[0] + 1]:
        fail("fifo.cpp:drain-throw-body", "no throw statement on the line after the count==0 if")
    rst_all = [i for i in range(thr[0], min(thr[0] + 30, len(lines))) if lines[i].strip() == RESET_LINE]
    if not rst_all:
        fail("fifo.cpp:drain-reset", "no sBufferSize reset after the drain loop (want the first of >=1)")
    rst = [rst_all[0]]  # drain's own reset is the first one after its loop
    if sum(ln.count("{") - ln.count("}") for ln in PRESERVE) != 0:
        fail("fifo.cpp:drain", "internal: preserve block is brace-unbalanced")
    # bottom-up: reset first, then the two throw lines become one break
    lines[rst[0]:rst[0] + 1] = PRESERVE
    lines[thr[0]:thr[0] + 2] = ["    if (count == 0 && retried) break;  // Batch 52: keep the undecoded tail (see below) instead of throwing; the guard there drops a permanently stuck tail."]
    return "\n".join(lines)

FILES = [
    ("aurora-main/lib/gx/command_processor.cpp", patch_cp),
    ("aurora-main/lib/gx/fifo.cpp", patch_fifo),
]

plan = []
for relpath, fn in FILES:
    path = os.path.join(ROOT, relpath)
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        text = f.read()
    new_text = fn(text)
    if new_text is None:
        print(f"batch 52: {relpath} already patched, skipping")
    else:
        plan.append((path, relpath, new_text))

for path, relpath, new_text in plan:
    shutil.copyfile(path, path + ".bak-pre52")
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(new_text)
    print(f"batch 52: tail carry-over added in {relpath} (backup at {path}.bak-pre52)")

print("batch 52: done" if plan else "batch 52: nothing to do (all files already patched)")
