# mtg14-nx — Magic: The Gathering – Duels of the Planeswalkers 2014 for the Nintendo Switch

A **static recompilation** of the Xbox 360 XBLA game *Magic: The Gathering – Duels of the Planeswalkers 2014*
(title `584112C5`) to the Nintendo Switch, built with [ReXGlue](https://github.com/rexglue/rexglue-sdk): the game's
PowerPC code is translated to C++ ahead of time and compiled into a native Nintendo Switch program (`.nro`). No
emulator is involved and the console does not run any Xbox code.

**This repository does not contain the game.** Not a single byte of its data, art, audio, video, menu bytecode or
translated code is included. You supply your own legally purchased copy; the installer turns it into the folder that
goes on the console's SD card, on your own machine.

## Nintendo Switch hardware test

On November 18, 2026 the maintainer confirmed that the updated build runs on Nintendo Switch hardware and that the dark-screen fix resolved the issue. The fix addresses a battlefield that could stay dark after card zoom or the opening-hand mulligan. The fix is built into the port.

The hardware result applies to the tested local build. The public-source snapshot carries the same fix and has not been rebuilt and tested on hardware separately.

## Requirements

Build on Windows. For playback, use a Nintendo Switch already set up to run homebrew.

| What | Why |
|---|---|
| Your own copy of the game | `default.xex`, `default.xexp`, `DATA_CORE.WAD`, `DATA_DECKS_D14.WAD` and the Title Update WADs (`UPDATE_DATA_*.WAD`). Optional: the DLC packages. |
| Python 3.8 or newer | the installer and the tools, plus `Pillow`, `numpy` and `xxhash` (`py -m pip install Pillow numpy xxhash`) |
| Visual Studio 2022 Build Tools | CMake and Ninja (no MSVC compiler needed) |
| LLVM / clang | to build the ReXGlue code generator |
| [devkitPro](https://devkitpro.org) with the `switch-dev` packages | devkitA64, libnx and deko3d: the console toolchain |
| `git` | to fetch the SDK's large third-party libraries (once) |
| `plume`, `uam`, `imgui`, `reblue-XenosRecomp` | `--thirdparty`; see [THIRD_PARTY.md](THIRD_PARTY.md) |

## Install

1. Put the eight extracted files listed below in a dedicated input folder. The extracted Title Update files are required. The original Title Update package passed with `--tu` is optional and used for verification.
2. Set up the SDK and renderer dependencies and the host shader tools. The shader tools are required for a playable build. [Build instructions](docs/BUILD.md)
3. Open **Command Prompt** in the repository and run the following example. Remove the `--dlc`, `--tu`, or `--icon` line for any option you are skipping. Choose a dedicated build folder outside this repository and separate from your inputs.

```bat
py -3 install\install.py --game mtg14 ^
    --data  "C:\M14\game" ^
    --dlc   "C:\M14\dlc" ^
    --tu    "C:\M14\title-update" ^
    --icon  "C:\M14\icon.jpg" ^
    --thirdparty "C:\M14\thirdparty" ^
    --work  "C:\M14\build" ^
    --out   "C:\M14\output"
```

`--dlc`, `--tu` and `--icon` are optional. The SDK is `sdk/` inside this repository, so nothing has to be pointed at
it. Its large third-party libraries (FFmpeg, SDL3, glslang, Vulkan headers…) are **not** copied here: fetch them once,
before the first build, with

```bat
py -3 install\fetch_thirdparty.py
```

To use an existing local SDK checkout, run `py -3 install\fetch_thirdparty.py --source "C:\M14\rexglue-sdk"`.

`--data` must contain the game files; `--xex`/`--xexp` can point at them individually if they are elsewhere. Add
`--dry-run` to see every step and command without touching anything. `install\install.py --help` lists the rest.

The NRO's **icon is yours**: `--icon <image>` (256x256 JPEG or PNG). Without it the build makes an NRO with no icon;
nothing of the sort is distributed with this repository.

What the installer does, in order:

1. checks Python, CMake, Ninja, clang, devkitPro and the Python modules, and tells you what to install if any is missing;
2. checks the SHA256 of every file you supplied (tables below) and refuses to continue if one does not match;
3. copies the game to a work folder outside the repository;
4. draws the PlayStation and Switch button icon variants from the game's own textures (`tools/mtg14_iconos.py`);
5. builds the menus from *your* copy of the game, on the fly (`install/mtg14_lua.py`): the main menu loses the entries
   that need Xbox Live, achievements and the store, the DLC enumeration shows only its loading ring, one press is
   enough on the title screen, and the Settings menu gains language, button icons and DLC rows. No script text and no
   bytecode of the game is distributed with this repository;
6. translates the game's shaders for the console's GPU (`--skip-shaders` to leave this out);
7. builds the asset pack (`game_root.nxpack` + `.nxidx`);
8. runs the ReXGlue code generator on your `default.xex`;
9. compiles the `.nro` with devkitA64 (with your `--icon`, if given);
10. leaves `switch\mtg14-nx\`, ready for the SD card, next to a `SHA256_mtg14-nx.txt` of everything in it.

Copy the generated `switch/mtg14-nx/` folder so the SD card contains `sd:/switch/mtg14-nx/mtg14.nro`. Keep `game_root.nxpack`, `game_root.nxidx`, `deko3d_glsl.bin`, `lua/`, and any `dlc/` beside the NRO. Use the generated checksum file to verify the copy.

### Files you have to provide

| File | Where | SHA256 | Size |
|---|---|---|---|
| `default.xex` | base game (the `584112C5` folder of your XBLA copy) | `0aab95bec6aee6b82ac92a36b0af17e1a5840bfeec4f9fb9889eb620b17633b7` | 16 166 912 |
| `default.xexp` | Title Update | `0dc3022934e8f7f02ab92c77f94ce4219b43380cb093da07fdb4c9920a1edcc0` | 1 359 872 |
| `DATA_CORE.WAD` | base game | `5b40fa9e4c4fd1b17b05538e6df4ba0b26541b18f43e434c508333d0e6c4d2d0` | 426 830 060 |
| `DATA_DECKS_D14.WAD` | base game | `4cdd4585f2995df374cb1a963db06e0ef261e1e5127830747aad5226f8186f9d` | 181 163 596 |
| `UPDATE_DATA_CORE.WAD` | Title Update | `61c5e11ff0f901ed6ee46ca928f2fb7944ac141ae882425eb45fdffe1708955a` | 1 567 928 |
| `UPDATE_DATA_DECKS_D14.WAD` | Title Update | `ec057ced0933f83057fcc02ff835ae3e2b35f45593f5c97e2d9f498b57ad20c0` | 1 727 102 |
| `UPDATE_DATA_DECKS_E14.WAD` | Title Update (expansion decks) | `b3155823df1b488339f70a0e2e999ad54b3f8742cdd55bdcc5de521c79314340` | 799 399 |
| `UPDATE_DATA_DLC_0001.WAD` | Title Update (DLC list) | `11bfad36a7f8123a5db2aeedcdae46a68e39bbd88dd6ec8a8063ff1f29325644` | 205 520 |

The Title Update package itself (`tu00000002_00000000`) is checked when you pass `--tu`, and the four DLC packages when
you pass `--dlc`: their SHA256 are in [`install/games/mtg14.toml`](install/games/mtg14.toml). Without the DLC the base
campaign still works.

## Launching on the console

Hold **R** while starting any game from the home menu, then open the Homebrew Menu and start `mtg14`. A title takeover
is required: from the Album the applet does not get enough memory.

At its first start the game writes `sdmc:/switch/mtg14-nx/mtg14.toml` with only your options. Everything else is
compiled in.

## What works

- The base game: campaign and tutorial, single duels, the deck manager and the `DATA_DECKS_D14.WAD` decks of your copy.
- The Title Update: its data WADs are mounted on `update:` and the extra cards, decks and fixes they contain are the
  game's own.
- The four DLC packages, once they are in `dlc/` (installed from `dlc/` next to the NRO).
- Languages: the nine the game ships (English, Spanish, French, German, Italian, Japanese, Portuguese, Korean, Russian).
- Button icons: Xbox 360, PlayStation and Nintendo Switch. The installer builds the PlayStation and Switch variants from
  your own textures; the port redirects `Update_Data_Core.wad` to the style `update_wad_variant` selects, so all three
  live side by side.
- Settings menu with three rows the original never had: **Language**, **Button icons** and a read-only **DLC** line that
  lists the packs the port found.
- Renders with Renut's Direct3D-level renderer on deko3d, docked and handheld, touch screen as the game's own input.

## Known limitations

The hardware confirmation covers the dark-screen fix and general operation. These limitations still apply:

- **Videos are skipped** (the intro and the studio logos); the game goes straight to the menu.
- The main menu keeps the local game, the campaign, the deck manager and the settings; leaderboards, online play,
  achievements, downloadable content and the store are hidden, because there is nothing behind them on a Switch.
- The first start enumerates the DLC packages for a few seconds (about six on a PC); only the loading ring is shown.
- The DLC row reports the packs it found, not what the game actually loaded ("sin verificar").
- Changing the button-icon style takes effect on the next start and the game does not say so.
- Hardware test coverage is unconfirmed for the Switch button icons on screen, a full duel against
  the computer, the DLC campaigns and decks, the promotion of the first start and the "Additional content" entry. Treat
  those as untested.
- The port's own extra options (frame rate, logging, renderer) are set in `mtg14.toml`, not in a menu.
- The test runs were made on a PC with the audio muted: sound quality has not been verified.

## What is not in this repository

- `app/thirdparty/` — `plume`, `uam`, `imgui` and `reblue-XenosRecomp`: pass it with `--thirdparty`.
- The **large** third-party libraries of the SDK (`sdk/thirdparty/`): each one has a public repository and its own
  license, so they are fetched instead of copied — `install\fetch_thirdparty.py`. The SDK's own source, its CMake and
  the small dependencies **are** here.
- The native PM4-ring Vulkan renderer (`app/src/me/masseffect`, `mtg14_api_*`, `mtg14_port_shaders`): this port draws
  with Renut, so that tree is not part of this repository.
- Any result of running the build: the generated C++ of your game, the asset pack, the shaders, the `.nro`, the button
  icon variants, the patched menus and the NRO icon.

`docs/BUILD.md` explains what each one is and how to obtain it. Everything else the build needs is here: the port's
own code (`app/`), its configuration (`app/*.toml`), the CMake glue, the toolchain file and the tools.

## Layout

```
app/                the port's own code (C++), its CMake glue and configuration
install/            install.py, mtg14_lua.py (the menus), fetch_thirdparty.py and games/mtg14.toml
sdk/                the ReXGlue fork this port uses (source and CMake; its big libraries are fetched)
tools/              the tools the installer runs (WAD, Lua, shaders, icons, asset pack) + check_clean.py
docs/BUILD.md       how the pieces fit, step by step
THIRD_PARTY.md      every dependency, its origin and its license
LICENSE              GPL-3.0-or-later for project-owned code
```

Another game of the saga is installed by adding `install/games/<game>.toml` with its own hashes, paths and Lua
operations; the installer is not specific to Magic 2014.

## AI usage disclosure

OpenAI Codex helped prepare the source snapshot, update the installation instructions, and check that local game files are excluded. The maintainer reported the Switch hardware result.

## License

Project-owned code is licensed under GPL-3.0-or-later, following the other Magic Switch ports. ReXGlue and its Horizon layer retain BSD-3-Clause. The reNut renderer is included under the author's written redistribution permission for the Magic ports. Other dependencies retain their own terms. [Project license](LICENSE) ? [Third-party notices](THIRD_PARTY.md)

## Credits

This port stands on other people's work: the ReXGlue SDK (Tom Clay, and the Xenia project it derives from), the
Horizon/Switch layer by StevenSND, reNut by masterspike52 and plume by renderbag (the renderer), XenosRecomp by
hedge-dev, uam and deko3d by fincs (devkitPro), and the earlier Magic ports of this saga that share their tools.
See [THIRD_PARTY.md](THIRD_PARTY.md) for the complete list and the licenses.

## Legal notice

This is a **fan project**, made for preservation and personal use on hardware the author owns. It is not affiliated
with, endorsed by or supported by Wizards of the Coast, Hasbro, Stainless Games, Microsoft, Xbox Game Studios or
Nintendo. *Magic: The Gathering* and *Duels of the Planeswalkers* are trademarks of Wizards of the Coast;
*Nintendo Switch* is a trademark of Nintendo; *Xbox 360* is a trademark of Microsoft.

No game data is distributed: you must own the game. Do not redistribute the folder the installer produces, nor any
output of these tools that contains the game's data.
