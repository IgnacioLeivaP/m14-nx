# How the build fits together

`install/install.py` runs these steps for you. This page is the explanation, for when a step fails or when you want to
run them by hand.

```
install/install.py
  |-- 1  herramientas      python, cmake, ninja, clang, devkitPro, Pillow, numpy, xxhash
  |-- 2  SHA256            default.xex, default.xexp, los WAD del juego y del Title Update, el TU y los DLC
  |-- 3  arbol             <work>/assets/game_root  +  <work>/app  +  <work>/tools  (+ out/icon.jpg)
  |-- 4  iconos            tools/mtg14_iconos.py        -> mtg14_buttons_{ps,switch}.bin
  |-- 5  lua               install/mtg14_lua.py         -> out/lua/<modulo>.lua|.luac
  |-- 6  shaders           tools/shaders_wad.py, XenosRecomp, tools/deko3d_*.py
  |-- 7  pack              tools/build_asset_pack.py    -> game_root.nxpack/.nxidx
  |-- 8  codegen           rexglue codegen              -> app/generated/
  |-- 9  NRO               cmake + Ninja (devkitA64)    -> mtg14.nro
  `-- 10 carpeta final     <out>/switch/mtg14-nx/ + SHA256_mtg14-nx.txt
```

The work folder mirrors the layout the CMake files expect (`app/`, `tools/`, `assets/`, `out/` side by side), which is
why the relative paths inside `app/CMakeLists.txt` and `app/cmake/*.cmake` need no changes.

## What you have to supply

### The SDK (`sdk/`, or `--sdk <carpeta>`)

The ReXGlue fork this port builds against. It contains the code generator (`rexglue codegen`), the Xbox 360 kernel and
runtime, the Horizon (Switch) layer, and the third-party sources the runtime links (FFmpeg for XMA audio, glslang,
SPIRV-Tools, fmt, spdlog, xxHash, toml++…). Its own source and CMake are in `sdk/`; the **large** third parties are
not copied there — fetch them once with `py -3 install/fetch_thirdparty.py` (`--help` explains it; `--source` uses a
local checkout and touches no network).

`--sdk` exists for a tree kept somewhere else; when it is left out, `sdk/` of this repository is used. Build the
generator once with (the installer does this when `<work>/out/host/rexglue.exe` is missing):

```bat
cmake -S <sdk> -B <work>\out\host -G Ninja -DCMAKE_BUILD_TYPE=Release ^
      -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++ ^
      -DCMAKE_C_FLAGS=-march=x86-64-v2 -DCMAKE_CXX_FLAGS=-march=x86-64-v2
cmake --build <work>\out\host --target rexglue
```

`-march=x86-64-v2` is required (the SDK uses SSSE3 intrinsics).

### `--thirdparty <carpeta>`

A folder with the four trees `app/thirdparty/` needs: `plume` (MIT), `uam` (zlib/MIT), `imgui` (MIT) and
`reblue-XenosRecomp` (MIT, Renut's version). The installer junction/copies it into `<work>/app/thirdparty`.

### The NRO icon (`--icon <imagen>`)

A 256x256 JPEG or PNG of yours. The installer copies it to `<work>/out/icon.jpg`, which is where `app/CMakeLists.txt`
looks for it before configuring the NRO. Without `--icon` (and with no `app/icon.jpg` in the tree) the NRO is built
with no icon. It is never distributed with this repository.

### The PC-side shader tools (step 6)

Translating the game's shaders for the console needs three host programs, built once:

| Program | Where it goes | How |
|---|---|---|
| `spirv-cross.exe` | `<work>/out/deko3d_tools/spirv-cross-build/` | `bash tools/deko3d_build_tools.sh` (SPIRV-Cross sources, Apache-2.0) |
| `uam.exe` | `<work>/out/deko3d_tools/uam-build/` | same script (uam, zlib/MIT) |
| `XenosRecomp.exe` | `<work>/out/pc/xenos_recomp/build/XenosRecomp/` | built by a PC configure of `app/` (`thirdparty/reblue-XenosRecomp` is an ExternalProject) |

`--skip-shaders` leaves them out. The NRO then has no translated game shaders, `deko3d_glsl.bin` is not created and
the renderer logs a warning; the game will not draw correctly, so this is only for checking the rest of the pipeline.

## Step details

**Icons (4).** `mtg14_iconos.py` reads the two 64x64 button textures `XBOX_A.TDX` / `XBOX_B.TDX` of
`DATA_CORE.WAD` and the two 1024x1024 symbol sheets `SYMBOLS.TDX` / `SYMBOLS_FE.TDX` (DXT5, 11 mip levels) with
`tools/wad.py`, draws the PlayStation and Switch glyphs itself (plain geometry and Pillow's built-in bitmap font — no
external art and no font file from the system), and writes `Update_Data_Core.wad` once per style with those four
textures replaced: your own Title Update entries stay byte for byte as they are. The two resulting WADs go into the
game folder, because the port redirects `Update_Data_Core.wad` to the one `update_wad_variant` selects.

**Lua (5).** Seven files, all built from *your* copy of the game — no script text and no bytecode of the game is
distributed with this repository. Magic 2014 keeps its menus as Lua **5.1 bytecode** (`.LOB`) inside its WADs, so this
port patches the bytecode (or wraps it in its own Lua text) at install time. Each entry of `lua` in
`install/games/mtg14.toml` names its WAD, its entry inside the WAD, the operation of `install/mtg14_lua.py` and the
output file:

- `main_menu` hides the rows that need Xbox Live, achievements and the store, the four rows at the bottom and the
  promotion banner; `main_menu_layout` takes three leftover Xbox texts off screen.
- `extras_menu` hides the promotions and unlock rows of *Additional content*.
- `press_start` makes one press enough on the title screen and disables the promotion trail.
- `content_enumeration` shows only the spinning ring while the DLC is enumerated, and closes it as soon as it ends.
- `settings` + `layout_helper` add the port's own Lua (language, button icons, DLC state) and its rows to the Settings
  menu, moving the rows it already had so everything fits.

Each operation checks the structures it expects (prototype counts, constants) and stops with the name of what did not
match rather than leaving half a menu. The installer also compares the SHA256 of what it produced with the file that
was tested on the console, and warns when it differs.

**Shaders (6).** `shaders_wad.py` pulls the shader containers (magic `0x102A11xx`) out of the game's WADs into
`out/renut_shader_dump`, named by XXH3 of the container, which is how the renderer looks them up. Then XenosRecomp
translates them to SPIR-V, `deko3d_shaders.py` turns each into uam GLSL and a DKSH, `deko3d_glsl_opt.py` optimises it,
`deko3d_shader_package.py` makes the package, `renut_switch_shader_cache.py` writes the Switch shader table, and
`renut_release_shaders.py` assembles `out/renut_switch_release/` — the file `sd/deko3d_glsl.bin` from there is what
goes on the SD card.

**Code generation (8).** `rexglue codegen mtg14_manifest.toml` runs inside `<work>/app` with
`REX_MAX_JUMP_TABLE_ENTRIES=4096` and `REXGLUE_DUMP_IMAGE=<work>/out/default_image.bin`; it writes `app/generated/`
(the game translated to C++, never committed) and the CMake glue. `app/generated/codegen_profile.txt` records which
profile was used.

**NRO (9).** `cmake -S app -B out/nx -G Ninja` with `tools/switch/cmake/switch-devkitA64.cmake` as the toolchain file,
`-DREXSDK_DIR=<sdk>`, `-DMTG14_NATIVE_RENDERER=OFF`, `-DMTG14_RENUT_RENDERER=ON`, `-DMTG14_RENUT_PORT_SHADERS=OFF`.
`--lto` adds `-DMTG14_SWITCH_LTO=ON` for the release link (much slower). The output is `out/nx/mtg14.nro`. The native
PM4-ring Vulkan renderer of the author's other ports (`src/me/masseffect`, `mtg14_api_*`, `mtg14_port_shaders`) is
**not** part of this repository: this port draws with Renut.

**Package (10).** `mtg14.nro`, `game_root.nxpack` + `.nxidx`, `deko3d_glsl.bin`, `lua/` and (optionally) `dlc/` in
`<out>/switch/mtg14-nx/`, plus `SHA256_mtg14-nx.txt` beside it. The game writes its own `mtg14.toml` there on the
first start; there is no settings file to ship.

## Adding another game of the saga

Copy `install/games/mtg14.toml`, change the id, the file names, the SHA256 tables, the manifest name and the `lua`
entries (their WAD, entry and operation); add the CMake tree of that game under a folder of its own. `install.py`
takes `--game <id>` and reads everything game-specific from that file.
