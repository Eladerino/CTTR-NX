#!/usr/bin/env python3
"""Batch 271 -- CTTR-only Phase 4: strip the foreign leftovers inside
KEPT files, now that phases 1-3 removed the foreign sources,
products and registrations.

  settings_overlay.cpp : remove SPM's PatchBootStrings /
      PatchMessageStrings guest-text rewriters and their Draw calls.
  os_init.cpp          : remove the three dead #if 0 StaticR blocks
      (the live 0x80274664 alarm-hook registration stays).
  updater.cpp          : the shared self-updater still pointed at
      SPM's GitHub releases. Neutralize the endpoints (no CTTR
      release repo exists; an empty API URL fails the check
      silently, the updater's offline path) and rename the test
      env vars SPM_UPDATE_TEST_* -> CTTR_UPDATE_TEST_*.
  recomp_mod_loader    : remove the RiivolutionXml registry
      (setters have no callers left; getters only ever return
      empty). riivolution.cpp's two read sites become the empty
      defaults they already always observed.
  main.cpp + consumers : NSMBW_* diagnostic env vars and the
      Android debug.nsmbw.* property bridge renamed to CTTR_ /
      debug.cttr.*; bridge rows with no consumer anywhere
      (lobbytest, tsonly, tapscript, warp, patchreadback,
      sscript) dropped.
  PublicProducts.cmake : stale RetroRewind mention in a comment.
  Orphaned foreign headers deleted after an includer scan:
      include/netplay_start.h, netplay_lobby.h, netplay_session.h,
      netplay_ui.h, spm_map_sweep.h, spm_prepare_graphics.h,
      mod_runtime.h, spm_mod_api.h, src/netplay/*.h,
      spm_warp_rooms.inc (wherever it lives).

Backups: <file>.bak-pre271. Idempotent via marker.
Env: CTTR_ROOT (default live tree).
"""
import os
import re
import shutil
import sys

ROOT = os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled")
RT = os.path.join(ROOT, "runtime")
MARKER = "Batch 271"


def fail(msg):
    print("ABORT:", msg)
    sys.exit(1)


class Edit:
    def __init__(self, relpath):
        # latin-1 gives a 1:1 byte<->char mapping, so untouched
        # regions round-trip byte-identically even for sources
        # that are not valid UTF-8 (settings_overlay.cpp). All
        # anchors used here are pure ASCII.
        self.relpath = relpath
        self.path = os.path.join(RT, relpath)
        if not os.path.exists(self.path):
            fail("missing file: " + relpath)
        self.orig = open(self.path, "rb").read()
        self.text = self.orig.decode("latin-1")
        self.lines = self.text.split("\n")
        self.ops = 0

    def find(self, pred, what, count=1):
        hits = [i for i, l in enumerate(self.lines) if pred(l)]
        if len(hits) != count:
            fail("%s: %s found %d times, expected %d" % (self.relpath, what, len(hits), count))
        return hits

    def rm_span(self, start_pred, end_pred, what, end_skip=0):
        """Delete lines from the start_pred line through the
        (end_skip+1)-th following line matching end_pred."""
        s = self.find(start_pred, what + " (start)")[0]
        seen = -1
        e = None
        for i in range(s, len(self.lines)):
            if end_pred(self.lines[i]):
                seen += 1
                if seen == end_skip:
                    e = i
                    break
        if e is None:
            fail("%s: %s (end) not found" % (self.relpath, what))
        del self.lines[s:e + 1]
        self.ops += 1
        return s

    def rm_fn(self, sig_substr, what, comment_pred=None):
        """Delete a function: optional preceding comment block start
        (comment_pred) through the brace-matched end of the
        function whose signature line contains sig_substr."""
        sig = self.find(lambda l: sig_substr in l, what + " (sig)")[0]
        start = sig
        if comment_pred is not None:
            cands = [i for i in range(sig) if comment_pred(self.lines[i])]
            if not cands:
                fail("%s: %s (comment start) not found" % (self.relpath, what))
            start = cands[-1]
        depth = 0
        begun = False
        end = None
        for i in range(sig, len(self.lines)):
            depth += self.lines[i].count("{") - self.lines[i].count("}")
            if "{" in self.lines[i]:
                begun = True
            if begun and depth == 0:
                end = i
                break
        if end is None:
            fail("%s: %s (fn end) not found" % (self.relpath, what))
        del self.lines[start:end + 1]
        self.ops += 1

    def rm_exact_line(self, exact, what):
        # tolerate CRLF: staged lines may carry a trailing \r
        idx = self.find(lambda l: l.rstrip("\r") == exact, what)[0]
        del self.lines[idx]
        self.ops += 1

    def replace_substr(self, old, new, what, count=None):
        joined = "\n".join(self.lines)
        c = joined.count(old)
        if count is not None and c != count:
            fail("%s: %s found %d times, expected %d" % (self.relpath, what, c, count))
        if c == 0:
            fail("%s: %s not found" % (self.relpath, what))
        joined = joined.replace(old, new)
        self.lines = joined.split("\n")
        self.ops += 1
        return c

    def commit(self):
        if self.ops == 0:
            return False
        bak = self.path + ".bak-pre271"
        if not os.path.exists(bak):
            shutil.copy2(self.path, bak)
        open(self.path, "w", encoding="latin-1", newline="").write("\n".join(self.lines))
        return True


def already_done():
    p = os.path.join(RT, r"src\updater.cpp")
    return os.path.exists(p) and MARKER.encode() in open(p, "rb").read()


def edit_os_init():
    e = Edit(r"src\hle\os\os_init.cpp")
    e.rm_span(lambda l: l.rstrip() == "#if 0  // NSMBW: MKW StaticR.rel prolog",
              lambda l: l.rstrip() == "#endif", "os_init #if0 block A")
    e.rm_span(lambda l: "StaticR.rel prolog wrapper" in l,
              lambda l: l.rstrip() == "#endif", "os_init #if0 block B")
    e.rm_span(lambda l: "StaticRProlog_RecompModInit is not linked" in l,
              lambda l: l.rstrip() == "#endif", "os_init #if0 block C", end_skip=1)
    t = "\n".join(e.lines)
    if "StaticR" in t:
        fail("os_init: StaticR remains")
    if "func_80274664" not in t or "REGISTER_NATIVE_FUNCTION_AS(0x80274664" not in t:
        fail("os_init: live alarm-hook registration lost")
    return e


def edit_overlay():
    e = Edit(r"src\settings_overlay.cpp")
    e.rm_fn("void PatchBootStrings() {", "PatchBootStrings",
            comment_pred=lambda l: "New Super Paper Bros.: the boot screen" in l)
    e.rm_fn("void PatchMessageStrings() {", "PatchMessageStrings",
            comment_pred=lambda l: "The game's own instruction lines still talk" in l)
    e.rm_exact_line("    PatchBootStrings();", "Draw call PatchBootStrings")
    e.rm_exact_line("    PatchMessageStrings();", "Draw call PatchMessageStrings")
    t = "\n".join(e.lines)
    if "PatchBootStrings" in t or "PatchMessageStrings" in t:
        fail("overlay: patch fns remain")
    return e


def edit_updater():
    e = Edit(r"src\updater.cpp")
    e.replace_substr("SPM_UPDATE_TEST_URL", "CTTR_UPDATE_TEST_URL", "test url env", count=2)
    e.replace_substr("SPM_UPDATE_TEST_INSTALL", "CTTR_UPDATE_TEST_INSTALL", "test install env", count=1)
    e.replace_substr("https://api.github.com/repos/josiahg2502-glitch/NewSuperPaperBros/releases/latest",
                     "", "SPM api endpoint", count=1)
    e.replace_substr("https://github.com/josiahg2502-glitch/NewSuperPaperBros/releases/download/",
                     "", "SPM download endpoint", count=1)
    e.replace_substr('"NewSuperPaperBros.zip"', '"WiiCompiled.zip"', "asset name win", count=1)
    e.replace_substr('"NewSuperPaperBros-linux.tar.gz"', '"WiiCompiled-linux.tar.gz"', "asset name linux", count=1)
    e.replace_substr("(NewSuperPaperBros/)", "(WiiCompiled/)", "archive comment", count=1)
    e.replace_substr("const char* const kTestUrl = std::getenv(\"CTTR_UPDATE_TEST_URL\");",
                     "const char* const kTestUrl = std::getenv(\"CTTR_UPDATE_TEST_URL\");  // Batch 271: no CTTR release endpoint; the default API/download URLs are empty and the check fails silent, like offline.",
                     "batch marker", count=1)
    t = "\n".join(e.lines)
    if "NewSuperPaperBros" in t or "SPM_UPDATE" in t:
        fail("updater: SPM refs remain")
    return e


def edit_mod_loader_cpp():
    e = Edit(r"src\recomp_mod_loader.cpp")
    e.rm_fn("std::string& RiivolutionXmlPath() {", "registry storage A")
    e.rm_fn("std::vector<RecompMod::RiivolutionOptionSelection>& RiivolutionSelections() {",
            "registry storage B")
    e.rm_fn("void RegisterRiivolutionXml(const char* packRelativePath) {", "registry cluster",
            comment_pred=None)
    # the cluster continues: RegisterRiivolutionOption + both getters
    for sig in ("void RegisterRiivolutionOption(const char* sectionName",
                "const std::string& RiivolutionXml() {",
                "const std::vector<RiivolutionOptionSelection>& RiivolutionOptionSelections() {"):
        e.rm_fn(sig, "registry fn " + sig[:30])
    t = "\n".join(e.lines)
    if "RiivolutionXml" in t or "RiivolutionOptionSelection" in t or "RiivolutionSelections" in t:
        fail("mod_loader: registry remains")
    return e


def edit_mod_loader_h():
    e = Edit(r"include\recomp_mod_loader.h")
    s = e.find(lambda l: "Riivolution settings pinned by" in l, "header registry comment")[0]
    en = e.find(lambda l: "RiivolutionOptionSelections();" in l, "header registry end")[0]
    del e.lines[s:en + 1]
    e.ops += 1
    t = "\n".join(e.lines)
    if "Riivolution" in t:
        fail("mod_loader.h: Riivolution remains")
    return e


def edit_riivolution():
    e = Edit(r"src\hle\storage\riivolution.cpp")
    e.replace_substr("const std::string& configured = RecompMod::RiivolutionXml();",
                     "const std::string configured;  // Batch 271: no distribution-pinned pack in the CTTR build (registry removed).",
                     "configured site", count=1)
    e.rm_span(lambda l: "for (const auto& selection : RecompMod::RiivolutionOptionSelections())" in l,
              lambda l: l.rstrip() == "    }", "selections loop")
    e.replace_substr("std::vector<RiivolutionContract::OptionSelection> RiivoManifestSelections() {",
                     "std::vector<RiivolutionContract::OptionSelection> RiivoManifestSelections() {\n    // Batch 271: no registered option selections in the CTTR build.",
                     "selections marker", count=1)
    t = "\n".join(e.lines)
    if "RecompMod::Riivolution" in t:
        fail("riivolution: registry refs remain")
    return e


def edit_main():
    e = Edit(r"src\main.cpp")
    e.replace_substr("debug.nsmbw.det=1", "debug.cttr.det=1", "bridge comment det", count=1)
    e.replace_substr("debug.nsmbw.dethash / detdump set NSMBW_DET_HASH / NSMBW_DET_DUMP",
                     "debug.cttr.dethash / detdump set CTTR_DET_HASH / CTTR_DET_DUMP",
                     "bridge comment hash", count=1)
    e.replace_substr("debug.nsmbw.script[2|3] the scripted remote (NSMBW_INPUT_SCRIPT)",
                     "debug.cttr.script[2|3] the scripted remote (CTTR_INPUT_SCRIPT)",
                     "bridge comment script", count=1)
    e.replace_substr('property("debug.nsmbw.det")', 'property("debug.cttr.det")', "det prop", count=1)
    e.replace_substr('setenv("NSMBW_DETERMINISTIC", "1", 1);', 'setenv("CTTR_DETERMINISTIC", "1", 1);',
                     "det setenv", count=1)
    # Bridge table: keep only rows whose env var has a consumer
    # (dethash, detdump, logfps); drop lobbytest/tsonly/tapscript/
    # warp/patchreadback.
    s = e.find(lambda l: 'std::pair{"debug.nsmbw.dethash"' in l, "bridge table start")[0]
    en = e.find(lambda l: '"NSMBW_PATCH_READBACK"}}) {' in l, "bridge table end")[0]
    lead = e.lines[s][:len(e.lines[s]) - len(e.lines[s].lstrip())]
    cont = e.lines[s + 1][:len(e.lines[s + 1]) - len(e.lines[s + 1].lstrip())]
    e.lines[s:en + 1] = [
        lead + 'for (const auto& [prop, env] : {std::pair{"debug.cttr.dethash", "CTTR_DET_HASH"},',
        cont + 'std::pair{"debug.cttr.detdump", "CTTR_DET_DUMP"},',
        cont + 'std::pair{"debug.cttr.logfps", "CTTR_LOG_FPS"}}) {',
    ]
    e.ops += 1
    e.replace_substr('property("debug.nsmbw.script")', 'property("debug.cttr.script")', "script prop", count=1)
    e.replace_substr('property("debug.nsmbw.script2")', 'property("debug.cttr.script2")', "script2 prop", count=1)
    e.replace_substr('property("debug.nsmbw.script3")', 'property("debug.cttr.script3")', "script3 prop", count=1)
    e.replace_substr('setenv("NSMBW_INPUT_SCRIPT", script.c_str(), 1);',
                     'setenv("CTTR_INPUT_SCRIPT", script.c_str(), 1);', "input script setenv", count=1)
    e.rm_span(lambda l: 'property("debug.nsmbw.sscript")' in l,
              lambda l: l.rstrip("\r") == "            }", "sscript block")
    e.replace_substr('std::getenv("NSMBW_DETERMINISTIC")', 'std::getenv("CTTR_DETERMINISTIC")',
                     "det getenv", count=1)
    e.replace_substr("(NSMBW's pipelines", "(inherited pipelines", "cache comment", count=1)
    e.replace_substr("// NSMBW display settings:", "// Display settings:", "display comment", count=1)
    e.replace_substr("debug.nsmbw.gfx", "debug.cttr.gfx", "gfx props")
    t = "\n".join(e.lines)
    if "nsmbw" in t.lower():
        fail("main: nsmbw remains")
    return e


def rename_file(relpath, pairs, label):
    e = Edit(relpath)
    for old, new in pairs:
        e.replace_substr(old, new, label + " " + old)
    return e


def edit_public_products():
    e = Edit(r"cmake\PublicProducts.cmake")
    e.replace_substr("WiiCompiled/RetroRewind only pull", "WiiCompiled only pulls",
                     "stale comment", count=1)
    return e


HEADER_CANDIDATES = [
    r"include\netplay_start.h", r"include\netplay_lobby.h",
    r"include\netplay_session.h", r"include\netplay_ui.h",
    r"include\spm_map_sweep.h", r"include\spm_prepare_graphics.h",
    r"include\mod_runtime.h", r"include\spm_mod_api.h",
]


def header_sweep():
    """Move provably orphaned foreign headers to .bak-pre271.
    A candidate is blocked if any non-candidate kept source
    mentions its basename."""
    candidates = list(HEADER_CANDIDATES)
    npdir = os.path.join(RT, r"src\netplay")
    if os.path.isdir(npdir):
        for f in sorted(os.listdir(npdir)):
            if f.endswith(".h"):
                candidates.append(os.path.join("src", "netplay", f))
    for dp, dn, fn in os.walk(RT):
        for f in fn:
            if f == "spm_warp_rooms.inc":
                candidates.append(os.path.relpath(os.path.join(dp, f), RT))
    cand_paths = {os.path.normpath(os.path.join(RT, c)) for c in candidates}
    kept_texts = []
    for base in ("src", "include"):
        for dp, dn, fn in os.walk(os.path.join(RT, base)):
            for f in fn:
                if f.endswith((".cpp", ".h", ".inc")) and "bak" not in f:
                    p = os.path.normpath(os.path.join(dp, f))
                    if p not in cand_paths:
                        kept_texts.append(open(p, errors="replace").read())
    moved, blocked = [], []
    for c in candidates:
        p = os.path.join(RT, c)
        if not os.path.exists(p):
            continue
        base = os.path.basename(c)
        if any(base in t for t in kept_texts):
            blocked.append(c)
            continue
        os.rename(p, p + ".bak-pre271")
        moved.append(c)
    return moved, blocked


def main():
    if already_done():
        print("batch 271 already applied, skipping")
        return
    editors = [
        edit_os_init(), edit_overlay(), edit_updater(),
        edit_mod_loader_cpp(), edit_mod_loader_h(), edit_riivolution(),
        edit_main(),
        rename_file(r"src\det_hash.cpp",
                    [("NSMBW_DET_HASH", "CTTR_DET_HASH"), ("NSMBW_DET_DUMP", "CTTR_DET_DUMP")], "det_hash.cpp"),
        rename_file(r"include\det_hash.h",
                    [("NSMBW_DET_HASH", "CTTR_DET_HASH"), ("NSMBW_DET_DUMP", "CTTR_DET_DUMP")], "det_hash.h"),
        rename_file(r"src\guest_profiler.cpp", [("NSMBW_PROFILE", "CTTR_PROFILE")], "guest_profiler.cpp"),
        rename_file(r"include\guest_profiler.h", [("NSMBW_PROFILE", "CTTR_PROFILE")], "guest_profiler.h"),
        rename_file(r"src\hle\vi.cpp", [("NSMBW_LOG_FPS", "CTTR_LOG_FPS")], "vi.cpp"),
        rename_file(r"src\wii_remote_input.cpp",
                    [("NSMBW_INPUT_SCRIPT", "CTTR_INPUT_SCRIPT"),
                     ("NSMBW_SCRIPT_REMOTES", "CTTR_SCRIPT_REMOTES")], "wii_remote_input.cpp"),
        edit_public_products(),
    ]
    changed = []
    for e in editors:
        if e.commit():
            changed.append(e.relpath)
    moved, blocked = header_sweep()
    print("batch 271 applied:")
    for c in changed:
        print("  PATCHED", c)
    for m in moved:
        print("  HEADER->BAK", m)
    for b in blocked:
        print("  HEADER BLOCKED (still referenced):", b)


if __name__ == "__main__":
    main()
