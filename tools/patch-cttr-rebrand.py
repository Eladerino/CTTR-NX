import sys, os

root = sys.argv[1] if len(sys.argv) > 1 else r"C:\dev\cttr-wiicompiled"
failures = []

def patch(relpath, replaces):
    path = os.path.join(root, relpath)
    src = open(path, encoding="utf-8").read()
    orig = src
    for old, new, minimum in replaces:
        n = src.count(old)
        status = "ok" if n >= minimum else "MISS"
        if n < minimum:
            failures.append((relpath, old, n, minimum))
        print(f"  [{status}] {relpath}: {n}x {old[:60]!r}")
        if n:
            src = src.replace(old, new)
    if src != orig:
        open(path, "w", encoding="utf-8", newline="").write(src)
        print(f"  wrote {relpath}")

print("== settings_overlay.cpp (splash + overlay text) ==")
patch(r"runtime\src\settings_overlay.cpp", [
    ('"Made by JosiahG"', '"Crash Tag Team Racing"', 2),
    ('"A Super Paper Mario PC recomp. Built on WiiCompiled\'s code."',
     '"Port by Eladerino. Built on WiiCompiled by patchzyy and contributors."', 1),
    ("aims Tippi's pointer, and a click presses A.",
     "moves the pointer, and a click presses A.", 1),
    ("Tippis Zeiger", "den Zeiger", 0),
    ("le pointeur de Tippi", "le pointeur", 0),
    ("el puntero de Tippi", "el puntero", 0),
    ("il puntatore di Tippi", "il puntatore", 0),
    ('"Use a Pixl / Cancel"', '"Action / Cancel"', 0),
])

print("== frontend_runtime.cpp ==")
patch(r"runtime\src\frontend_runtime.cpp", [
    ('aurora.appName = "Super Paper Mario"', 'aurora.appName = "Crash Tag Team Racing"', 1),
    ('"not a Super Paper Mario state"', '"not a Crash Tag Team Racing state"', 1),
])

print("== main.cpp (Discord presence) ==")
patch(r"runtime\src\main.cpp", [
    ('"Super Paper Mario"', '"Crash Tag Team Racing"', 1),
])

print("== game_folder.cpp ==")
patch(r"runtime\src\game_folder.cpp", [
    ('L"Super Paper Mario"', 'L"Crash Tag Team Racing"', 1),
    ("Super Paper Mario (USA, R8PE01, revision 0, or Europe, R8PP01)",
     "Crash Tag Team Racing (GameCube USA, G9RE7D, revision 0)", 1),
    ('L"Choose your Super Paper Mario disc image"', 'L"Choose your Crash Tag Team Racing disc image"', 1),
    ('L"Wii disc images (*.iso, *.ciso, *.wbfs)"', 'L"GameCube disc images (*.iso, *.ciso, *.wbfs)"', 1),
    ('"Super Paper Mario", text.c_str()', '"Crash Tag Team Racing", text.c_str()', 1),
    ('info.id != "R8PE01" && info.id != "R8PP01"', 'info.id != "G9RE7D"', 1),
    ('"), not Super Paper Mario for the USA (R8PE01) or Europe (R8PP01)."',
     '"), not Crash Tag Team Racing (USA, G9RE7D)."', 1),
    ('info.id == "R8PE01" && info.revision != 0', 'info.id == "G9RE7D" && info.revision != 0', 1),
    ('"That is Super Paper Mario USA revision "', '"That is Crash Tag Team Racing USA revision "', 1),
    ('"), not Super Paper Mario " + kGameId', '"), not Crash Tag Team Racing " + kGameId', 0),
    ('", not Super Paper Mario " + kGameId', '", not Crash Tag Team Racing " + kGameId', 0),
    ('"That is Super Paper Mario revision "', '"That is Crash Tag Team Racing revision "', 0),
    ("Put your Super Paper Mario disc image", "Put your Crash Tag Team Racing disc image", 1),
    ("MarioWiiSaveData", "CTTRSaveData", 0),
])

print("== runtime_config.h (user data dir + config template) ==")
patch(r"runtime\include\runtime_config.h", [
    ("MarioWiiSaveData", "CTTRSaveData", 4),
    ("// New Super Paper Bros. defaults:", "// Crash Tag Team Racing defaults:", 1),
    ('"# New Super Paper Bros. user configuration\\n"', '"# Crash Tag Team Racing user configuration\\n"', 1),
    ("# paths.dvd_root is your Super Paper Mario (USA, R8PE01) extracted to a DATA folder; the",
     "# paths.dvd_root is your Crash Tag Team Racing (USA, G9RE7D) extracted to a DATA folder; the", 1),
    ("SuperPaperMario", "CrashTagTeamRacing", 0),
])

print("== os_reset.cpp (panic text) ==")
patch(r"runtime\src\hle\os\os_reset.cpp", [
    ("Super Paper Mario", "Crash Tag Team Racing", 3),
])

print("== dvd.cpp (config help text) ==")
patch(r"runtime\src\hle\storage\dvd.cpp", [
    ("Super Paper Mario", "Crash Tag Team Racing", 2),
])

print("== PublicProducts.cmake (app icon) ==")
patch(r"runtime\cmake\PublicProducts.cmake", [
    ("assets/icon/nsmbw.ico", "assets/icon/cttr.ico", 1),
])

if failures:
    print("FAILURES:", failures)
    sys.exit(1)
print("rebrand patch complete")


# --- Pass 3 (same night, after exe string audit) ---------------------------
# The first passes missed every "New Super Paper Bros" variant (the searches
# were run for "Super Paper Mario" only). Pass 3 fixed: the settings bar
# title, the boot-screen rewrite text + its log line, the Gecko cheats help
# (R8PE01.ini -> G9RE7D.ini), the updater's relaunch script (New Super Paper
# Bros.exe -> WiiCompiled.exe), the dvd.cpp error text (R8PE01 -> G9RE7D),
# and removed game_folder.cpp's SPM other-region restart branch (single-disc
# product; wrong-disc folders now fall through to the Problem message).
# Attribution correction (Brandon): WiiCompiled is by patchzyy and
# contributors; JosiahG authored the NewSuperPaperBros product/launcher
# layer. The kCredit line above carries the corrected credit.
