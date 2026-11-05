# Tooling references from the recomp guide channel

Collected Nov 1, 2026 from the recomp guide Discord channel and assessed the
same day. Each entry: what it is, and where it slots into this project.
Two of these were already settled earlier the same day in the spm-nx and
JSRF threads; their verdicts are recorded here so they are not re-litigated.

## Sampling profiler pattern: NFSMW-NX `perfil_pilas.flag` (StevensND)

- An empty file named `perfil_pilas.flag` in `<NRO folder>/logs/rex/` turns
  on a sampling profiler. No rebuild needed; absence means off.
- Every 1 ms it briefly pauses each game thread and records the current
  function and caller. Every 10 s it writes the most frequent stacks per
  thread, with percentages, to the log. It also records the stacks active
  during frames longer than 45 ms (stutters).
- Discipline that comes with it: FPS from a profiled session do not count
  (the sampler costs performance); only the percentages are evidence.
  Functions appear as `image+0x...` addresses, resolved afterwards with
  `aarch64-none-elf-addr2line -f -C -e <ELF>` using the ELF from the same
  build, so the ELF is kept.
- Stevens' companion advice: an ImGui overlay for live bottleneck reading,
  with the data recorded to a .log file. The screenshots show frame-time
  graphs and per-section timings (Update, Draw, GPU Frame, Present) over
  lm-nx and NFSMW-NX.
- Slots in: this is the profiler design to copy in the Horizon phase (the
  same instrument class as SwitchWakerHD's main sampler and as the
  sampling profiler already at the top of spm-nx's steal list). On PC the
  equivalent question (where does CPU time go) is what the perf CSV logger
  in `tools/cttr-perf-log.ps1` starts on; the stack sampler is the console
  answer to the same question.

## SwitchWakerHD debug server (centollOS)

- Doc: https://github.com/centollOS/SwitchWakerHD/blob/main/docs/debug-server.md
- A TCP server in the game (port 6543, local network only, no password),
  off unless a settings toggle enables it. Plain-text protocol, one command
  per line, with a Python client (`wwhd_debug.py`).
- Commands cover: live log streaming, build deploy with CRC check and
  restart without touching the console, injected button/stick input at the
  point the game reads the controller, screenshots, SD card file transfer,
  crash report fetch, memory peek/poke, scripted warps, and a perf-test
  channel (portable bench states, a freezable clock, per-frame recording)
  driven by a `perf_test.py` companion.
- The server itself is a game-agnostic pair (`debug_server.{h,cpp}`) that
  builds on Switch and POSIX hosts, designed to be lifted into other
  runtimes. Developer variables live in a `[dev]` section of settings.ini,
  read at boot and echoed to the log.
- Already assessed Nov 1, 2026 for spm-nx and JSRF NX: a dev-tooling win
  (scripted repeatable runs make perf comparisons trustworthy), provided
  it stays default-off behind a dev toggle and out of release builds.
- Slots in: the Horizon phase dev-loop blueprint (H2/H4). Deploy, warp,
  screenshot and streamed logs are the console version of the
  log-don't-relay rule.

## sys-agent (leolovenet) — SETTLED, parked

- https://github.com/leolovenet/sys-agent — a maintained sys-botbase fork:
  Atmosphère-compatible process memory access, on-console memory search,
  hardware watchpoints and an execution tracer, transactional code
  patching, process inspection, SD FTP while a game stays open, verified
  one-shot Hekate emuMMC reboot.
- Already settled Nov 1, 2026 at Brandon's direction: it replaced
  sys-botbase as the external stopgap in both ports' perf scope docs, and
  then all sys-agent work was parked until later. Cautions recorded with
  it: the command socket on port 6000 is unauthenticated (trusted LAN and
  emuMMC only), back up `atmosphere/contents/43000000000000A6` before
  installing, and keep it off during quoted perf runs.
- Slots in: nothing to do now. When CTTR reaches the hardware phase, the
  same stopgap slot applies; setup steps are not to be pushed unprompted.

## Switch Frame Tap (TomasUribe)

- https://github.com/TomasUribe/switch-frame-tap — despite the name, a
  capture/streaming sysmodule, not a frame-time logger. A `vi:u` mitm
  watches the game's presents, reads finished frames with
  `svcReadDebugProcessMemory`, and the Tegra VIC + NVENC turn them into
  H.264 at up to 1080p60 over USB-C or network. Records MP4, takes
  native-resolution screenshots, and has viewers for Windows, Linux,
  macOS and Android. GPL-2.0, actively released, firmware 21 to 23,
  works on Switch Lite.
- Slots in: the capture-card replacement for hardware test sessions
  (Brandon tests on a Switch Lite): record runs for review instead of
  pointing a phone at the screen. It records what was presented, not
  timings, so it complements the loggers rather than replacing them, and
  it does real VIC/NVENC work on the console, so it stays out of quoted
  perf measurements. Its README research section (routes to another
  process's frames, driving the Tegra engines from a sysmodule) is also
  useful Horizon systems reading.

## SA2 deko3d renderer guide (ChanseyIsTheBest)

- https://github.com/ChanseyIsTheBest/sa2-nx/blob/main/docs/deko3d-renderer-guide.md
- How sa2-nx (an Xbox 360 ReXGlue port) moved from Vulkan on NVK to a
  deko3d renderer, following banjo-nx's route: the game's Direct3D calls
  are hooked into Renut's renderer, replayed by one render thread on
  plume's deko3d back end, with shaders compiled to DKSH by uam.
- The game-specific census (XDK Direct3D layouts, Xenos shader chain)
  does not transfer to a GameCube GX runtime. These parts do:
  - The priced case against NVK on the A57: banjo-nx measured roughly
    3 µs per pipeline bind, 2.4 to 2.9 µs per draw, 1.3 to 1.6 µs per
    descriptor or uniform update. deko3d has no driver layer doing that
    work, and dropping NVK also shrank the NRO from 58.2 MB to 43.8 MB.
    Direct evidence for this project's H3 renderer decision, and it
    strengthens the deko3d lean: on Switch the CPU is also paying for
    the recompiled game and any interpreted code, so per-call driver
    tax is the wrong place to spend it.
  - The staged method: build the new renderer on PC first with the old
    one still in the build and a boot key to A/B them; lockstep frame
    captures to compare pictures; first light in Ryujinx (RenderDoc
    works) before the console; console render-thread work measured
    separately (SA2 City Escape at 1020 MHz: render thread 17.6 to
    11.1 ms and game thread 19.2 to 15.5 ms after that work).
  - Pacing rule: never decouple the game from its frame rate when the
    game's speed follows it.
  - Shader cache discipline: a console run writes its pipeline list;
    a PC tool builds the DKSH cache from that list; list and cache are
    fsynced to the card. The same harvest-on-console, compile-on-PC
    pattern as spm-nx's PC-side Prepare work.
  - Licensing discipline: a table of every borrowed part with source,
    licence and how it was taken; third-party changes kept as diffs in
    `patches/`; `THIRD_PARTY_NOTICES.md` and a release `LICENSES.txt`.
    Caution noted in the guide itself: Renut has no licence file; its
    author permits reuse by these ports.

## Console overlays: SaltyNX / NX-FPS / ReverseNX-RT (StevensND, nfsmw-nx)

- https://github.com/StevensND/nfsmw-nx/blob/main/docs/console-overlays.md
- How a homebrew NRO feeds Status Monitor Overlay / Horizon OC Monitor
  and ReverseNX-RT. SaltyNX cannot inject its NX-FPS plugin into
  homebrew (it loads plugins by debugging the process, which homebrew
  refuses, and forwarder title IDs are treated as homebrew on purpose),
  so the NRO does the plugin's job itself: it asks SaltyNX for its
  shared page once at startup, then writes the NX-FPS block (174 bytes,
  magic 0x465053) itself.
- The write pattern: on every present, a heartbeat (pluginActive, the
  API id, the frame time into a 10-entry FPSticks ring on the 19.2 MHz
  tick, frame number, resolution) at a cost of about 25 bytes to mapped
  memory with no system calls; once per second, the FPS and FPSavg
  fields. The ReverseNX-RT block (magic "NXRT") is created the same
  way, after which the overlay's fake docked/handheld choice and clocks
  are obeyed by the game.
- A ready template ships in the repo (`extras/saltynx-template`, two
  files, libnx only, four calls: Init, Heartbeat, Update, IsDocked),
  with a failure table (SaltyNX missing, the one-session resource limit
  and its `sm:` release workaround, the reserve-once page rule).
- Slots in: an H4 checklist item. Two files at the present point give
  live FPS, resolution and clocks in the overlays Brandon already uses
  on the console, no ImGui build required. Overlays are for eyes during
  the run; the logs are for numbers after it.

## renut-nx docs folder (ChanseyIsTheBest)

- https://github.com/ChanseyIsTheBest/renut-nx/tree/master/docs — 28
  docs for the Xbox 360 recomp family. Already checked Nov 1, 2026 for
  spm-nx; nothing was adopted from it there.
- For this project the transferable reads, when the Horizon phase
  starts, are `deko3d-native-renderer-kit.md` (the kit the SA2 guide
  builds on), `deko3d-port-faq.md`, `deko3d-shader-optimisations.md`
  (each pass with its measured reason) and `pgo-lto.md` (PGO is already
  on spm-nx's take list). The rest is XDK/Xenos-specific.
