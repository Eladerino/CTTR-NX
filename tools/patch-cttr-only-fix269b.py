#!/usr/bin/env python3
# Batch 269b: compile repairs for the batch 269 overlay excisions.
#
# The first 269 build (Nov 7 2026) surfaced three over-cuts in
# settings_overlay.cpp that the text-level mock could not see:
#   1. The FlagList/Story span (end anchor "struct MenuPage",
#      keep_end) also ate the MenuTab enum and kTabNames table,
#      which sat between DrawStoryPage and the struct. The kept
#      kPages rows (Settings/Enhancements/Dev) and DrawMainWindow
#      still use them. Restored verbatim from the pre-269 backup.
#   2. ContainsNoCase lived inside the Dev Tools cluster (it was
#      the warp menu's filter helper), but DrawMainWindow's page
#      search also calls it. Restored verbatim.
#   3. Draw() still called DrawDebugHud(), whose definition the
#      Dev Tools excision removed. Call line removed.
#
# Anchored, backed up (.bak-pre269b), idempotent via marker.
import os
import sys

ROOT = os.environ.get("CTTR_ROOT", r"C:\dev\cttr-wiicompiled")
PATH = os.path.join(ROOT, "runtime", "src", "settings_overlay.cpp")
MARKER = "Batch 269b"


def main():
    with open(PATH, "r", errors="replace") as fh:
        text = fh.read()
    if MARKER in text:
        print("SKIP (already patched): batch 269b")
        return 0
    lines = text.split("\n")

    def find1(needle):
        hits = [i for i, l in enumerate(lines) if needle in l]
        if len(hits) != 1:
            print("ABORT: anchor %r found %d times" % (needle, len(hits)))
            sys.exit(1)
        return hits[0]

    # 3 first (line removal does not disturb the insert anchors'
    # uniqueness, and doing it first keeps indices simple to reason
    # about: inserts are located after).
    i = find1("DrawDebugHud();")
    del lines[i]

    # 1: enum + names immediately before struct MenuPage.
    i = find1("struct MenuPage { int tab;")
    lines[i:i] = [
        "enum MenuTab { kTabSettings, kTabEnhancements, kTabNetwork, kTabDev, kTabCount };",
        'constexpr const char* kTabNames[kTabCount] = {"Settings", "Enhancements", "Network", "Dev Tools"};  // Batch 269b: restored; batch 269\'s FlagList span ate it (it sat between DrawStoryPage and struct MenuPage).',
    ]

    # 2: ContainsNoCase immediately before DrawMainWindow.
    i = find1("void DrawMainWindow() {")
    lines[i:i] = [
        "bool ContainsNoCase(const char* hay, const char* needle) {  // Batch 269b: restored; DrawMainWindow's search uses it (it lived in the excised Dev Tools cluster).",
        "    std::string h = hay, n = needle;",
        "    for (char& c : h) c = static_cast<char>(std::tolower(static_cast<unsigned char>(c)));",
        "    for (char& c : n) c = static_cast<char>(std::tolower(static_cast<unsigned char>(c)));",
        "    return h.find(n) != std::string::npos;",
        "}",
        "",
    ]

    out = "\n".join(lines)
    with open(PATH + ".bak-pre269b", "w") as fh:
        fh.write(text)
    with open(PATH, "w") as fh:
        fh.write(out)
    print("PATCHED: runtime\\src\\settings_overlay.cpp (batch 269b)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
