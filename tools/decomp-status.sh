#!/bin/sh
# Print the state of the local cttr decomp clone and the upstream HEAD.
# Read-only. Run from anywhere; paths are relative to this project.
set -eu
cd "$(dirname "$0")/../research/cttr"

echo "== upstream =="
git ls-remote https://github.com/bluisblu/cttr.git HEAD | awk '{print "HEAD " substr($1,1,10)}'
echo "== local clone =="
git log -1 --format='last commit %h %cs %s'
echo "== decompiled source (the numbers that gate the port) =="
printf 'src/CTTR game files:  %s\n' "$(find src/CTTR -name '*.cpp' -o -name '*.c' | wc -l)"
printf 'src/dolphin SDK files: %s\n' "$(find src/dolphin -name '*.cpp' -o -name '*.c' | wc -l)"
printf 'src/auto files:        %s\n' "$(find src/auto -name '*.cpp' -o -name '*.c' | wc -l)"
printf 'symbols named:         %s\n' "$(wc -l < config/G9RE7D/symbols.txt)"
echo "Port-ready = fully linked decomp with the game/engine code decompiled,"
echo "not just the SDK. See docs/DECOMP-WATCH.md."
