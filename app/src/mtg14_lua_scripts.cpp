// The game's Lua scripts (LUBE menus, .LOB in Data_Core.wad), replaced by our own text versions.
//
// sub_823AC9F0 is the game's script loader (2026-11-08): r3 = the script's object, r4 = lua_State*. The object holds
// +0 the chunk name (char*), +8 the data and +0xC its size; the loader hands {data, size} to luaD_protectedparser
// (sub_8225C4B8) through its reader sub_823AC5E0. f_parser (sub_8226BAF8) takes text chunks too (luaY_parser,
// sub_822A2E48), so a replacement can be plain Lua.
//
// A replacement is <exe folder>/lua/<module>.lua (Lua text) or <module>.luac (the game bytecode patched by
// tools/luapatch.py), for any module that has one (the chunk name is the module, "menus.help_options.settings.basic [a] [b]")
// (BASIC.LOB -> lua/menus.help_options.settings.basic.lua). For the call the object's data and size point at a
// copy in guest memory; they are restored afterwards (the object owns its own buffer).
// mtg14_lua_log = true logs every chunk name the loader sees (once each).

#include <algorithm>
#include <csetjmp>
#include <memory>
#include <vector>
#include <cctype>
#include <cstdint>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <mutex>
#include <set>
#include <string>
#include <unordered_map>

#include <fmt/format.h>

#include <rex/cvar.h>
#include <rex/filesystem.h>
#include <rex/hook.h>
#include <rex/logging.h>
#include <rex/ppc/context.h>
#include <rex/ppc/func.h>
#include <rex/system/kernel_state.h>

#include "mtg14_dlc.h"
#include "mtg14_opciones.h"

REXCVAR_DEFINE_BOOL(mtg14_lua_catch_errors, true, "Mtg14",
                    "Lua errors caught as on the console (luaD_rawrunprotected / luaD_throw with setjmp and longjmp) "
                    "instead of ending the game (the runtime cannot unwind the C++ exception the game throws)");
REXCVAR_DEFINE_BOOL(mtg14_lua_log, false, "Mtg14", "Log the name of every Lua script the game loads (once each)");

namespace {

uint8_t* Guest(uint32_t address) {
  return address ? rex::system::kernel_state()->memory()->TranslateVirtual<uint8_t*>(address) : nullptr;
}
uint32_t Be32(const uint8_t* p) { return uint32_t(p[0]) << 24 | uint32_t(p[1]) << 16 | uint32_t(p[2]) << 8 | p[3]; }
void SetBe32(uint8_t* p, uint32_t v) {
  p[0] = uint8_t(v >> 24);
  p[1] = uint8_t(v >> 16);
  p[2] = uint8_t(v >> 8);
  p[3] = uint8_t(v);
}

std::string ChunkName(uint32_t object) {
  const uint8_t* o = Guest(object);
  if (!o) return {};
  const uint32_t size = Be32(o + 24), capacity = Be32(o + 28);
  if (size > 512) return {};
  const char* name = reinterpret_cast<const char*>(capacity < 16 ? o + 8 : Guest(Be32(o + 8)));
  return name ? std::string(name, size) : std::string();
}

// "menus.help_options.settings.basic [407D1848] [421878C0]" -> "menus.help_options.settings.basic": the chunk name is
// the Lua module's, then two addresses.
std::string Module(const std::string& name) {
  std::string m = name.substr(0, name.find(' '));
  for (char& c : m) c = char(std::tolower(uint8_t(c)));
  return m;
}

// What our Settings menu needs from the port, as Lua put before its text: the options in use and the new rows'
// labels in the game's language (the game's text tables have none for them).
std::string SettingsHeader() {
  const std::string current = mtg14::opciones::CurrentLanguage();
  std::string chosen = mtg14::opciones::Get("idioma");
  if (chosen.empty()) chosen = current;
  // Lua text read as Latin-1: accents as \ddd escapes.
  struct Labels {
    const char* lang; const char* idioma; const char* botones; const char* reinicio; const char* dlc; const char* ninguno;
  };
  static const Labels kLabels[] = {
      {"es", "Idioma", "Iconos de botones", "Idioma e iconos cambian al volver a abrir el juego", "Contenido descargable",
       "Ninguno"},
      {"fr", "Langue", "Ic\\244nes des boutons", "Langue et icones au prochain lancement du jeu",
       "Contenu t\\233l\\233chargeable", "Aucun"},
      {"de", "Sprache", "Tastensymbole", "Sprache und Symbole wechseln beim n\\228chsten Spielstart", "Zusatzinhalte",
       "Keine"},
      {"it", "Lingua", "Icone dei pulsanti", "Lingua e icone cambiano al prossimo avvio del gioco", "Contenuti scaricabili",
       "Nessuno"},
      {"en", "Language", "Button icons", "Language and button icons change after restarting the game", "Downloadable content",
       "None"},
  };
  const Labels* l = &kLabels[4];
  for (const Labels& k : kLabels)
    if (current == k.lang) l = &k;
  // DLC check (the user's request, 2026-11-09): "OK" and the packs found in the content store.
  std::string packs;
  for (int n : mtg14::dlc::InstalledPacks()) packs += (packs.empty() ? "" : ", ") + std::to_string(n);
  const std::string dlc = packs.empty() ? std::string(l->ninguno) : "Instalados: " + packs + " (sin verificar)";
  const auto installed = mtg14::dlc::InstalledPacks();
  std::string rows = "{";
  const char* pack_names[] = {"Expansion Pack 1", "Deck Pack 1", "Deck Pack 2", "Deck Pack 3"};
  for (int n = 1; n <= 4; ++n) {
    const bool present = std::find(installed.begin(), installed.end(), n) != installed.end();
    // Installation is evidence of files only; never label unplayed DLC as loaded.
    const char* status = current == "es" ? (present ? "Presente; uso pendiente" : "Falta")
                                         : (present ? "Present; gameplay unverified" : "Missing");
    rows += std::string(n == 1 ? "" : ",") + "'" + pack_names[n - 1] + ": " + status + "'";
  }
  rows += "}";
  return std::string("local MTG14 = { idioma = '") + chosen + "', estilo = '" + mtg14::opciones::ButtonStyle() +
         "', txt_idioma = '" + l->idioma + "', txt_botones = '" + l->botones + "', txt_reinicio = '" + l->reinicio +
         "', txt_dlc = '" + l->dlc + "', dlc = '" + dlc + "', packs = " + rows + " }\n";
}

struct Replacement {
  uint32_t guest = 0;  // the text in guest memory (kept for the whole run)
  uint32_t size = 0;
};

std::mutex g_mutex;
std::set<std::string> g_logged;
std::unordered_map<std::string, Replacement> g_loaded;  // by chunk name; size 0: no file

// The script's replacement, read once.
const Replacement* Find(const std::string& name) {
  const std::string module = Module(name);
  if (module.empty()) return nullptr;
  auto it = g_loaded.find(module);
  if (it == g_loaded.end()) {
    Replacement r;
    // Lua text (.lua) or the game's bytecode patched by tools/luapatch.py (.luac); f_parser takes both.
    const auto folder = rex::filesystem::GetExecutableFolder() / "lua";
    auto path = folder / (module + ".lua");
    std::error_code ec;
    if (!std::filesystem::is_regular_file(path, ec)) path = folder / (module + ".luac");
    std::ifstream in(path, std::ios::binary);
    if (in) {
      std::string text((std::istreambuf_iterator<char>(in)), std::istreambuf_iterator<char>());
      if (module == "menus.frontend.help_options_basic_settings" ||
          module == "menus.frontend.help_options_basic_settings_layout") text = SettingsHeader() + text;
      if (!text.empty()) {
        auto* memory = rex::system::kernel_state()->memory();
        r.guest = memory->SystemHeapAlloc(uint32_t(text.size()), 16);
        if (uint8_t* p = Guest(r.guest)) {
          std::memcpy(p, text.data(), text.size());
          r.size = uint32_t(text.size());
          REXLOG_INFO("[lua] {} replaced by {} ({} bytes)", name, path.string(), text.size());
        }
      }
    }
    it = g_loaded.emplace(module, r).first;
  }
  return it->second.size ? &it->second : nullptr;
}

}  // namespace

extern "C" REX_FUNC(__imp__sub_82AB9158);
REX_HOOK_RAW(sub_82AB9158) {  // int (ScriptObject*, lua_State*)
  const uint32_t object = ctx.r3.u32;
  const std::string name = ChunkName(object);
  const Replacement* replacement = nullptr;
  {
    std::lock_guard<std::mutex> lock(g_mutex);
    if (REXCVAR_GET(mtg14_lua_log) && g_logged.insert(name).second) {
      const uint8_t* o = Guest(object);
      REXLOG_INFO("[lua] load '{}' ({} bytes)", name, o ? Be32(o + 4) : 0);
    }
    if (!name.empty()) replacement = Find(name);
  }
  uint8_t* o = replacement ? Guest(object) : nullptr;
  if (!o) {
    __imp__sub_82AB9158(ctx, base);
    return;
  }
  const uint32_t data = Be32(o), size = Be32(o + 4);
  SetBe32(o, replacement->guest);
  SetBe32(o + 4, replacement->size);
  __imp__sub_82AB9158(ctx, base);
  SetBe32(o, data);
  SetBe32(o + 4, size);
  REXLOG_INFO("[lua] {}: loaded the replacement, result {}", name, int32_t(ctx.r3.u32));
}

// Lua errors (2026-11-09). The game's Lua is built as C++: luaD_rawrunprotected (sub_8226AA90) is
//   lj.previous = L->errorJmp (+0x70); lj.status (+8) = 0; L->errorJmp = &lj; try { f(L, ud); } catch (...) {}
//   L->errorJmp = lj.previous; return lj.status;
// and luaD_throw sets L->errorJmp->status and throws lua_longjmp*. The runtime cannot unwind a guest C++ exception
// (the SDK's HandleCppException stops), so every Lua error ended the game; on the console a pcall catches it and the
// game goes on. Here the pair is done the way Lua built as C does it: luaD_rawrunprotected keeps a host jmp_buf for its
// lua_longjmp (made on the guest stack below the caller's frame) and luaD_throw longjmps to it. The guest frames in
// between are left as they are (their nonvolatile registers are host locals, gone with them); the guest state at the
// call is restored from a copy of the context.
namespace {
struct ProtectedCall {
  uint32_t lj = 0;
  std::jmp_buf buf;
};
thread_local std::vector<ProtectedCall*> g_protected;
uint32_t g_errors_logged = 0;
}  // namespace

extern "C" REX_FUNC(__imp__sub_82353328);
REX_HOOK_RAW(sub_82353328) {  // int luaD_rawrunprotected(lua_State* L, Pfunc f, void* ud)
  if (!REXCVAR_GET(mtg14_lua_catch_errors)) {
    __imp__sub_82353328(ctx, base);
    return;
  }
  const uint32_t L = ctx.r3.u32, f = ctx.r4.u32, ud = ctx.r5.u32, r1 = ctx.r1.u32;
  uint8_t* const l = Guest(L);
  const uint32_t lj = (r1 - 0x40) & ~0xFu;
  uint8_t* const j = Guest(lj);
  PPCFunc* const fn = rex::runtime::ResolveIndirectFunction(f);
  if (!l || !j || !fn) {
    __imp__sub_82353328(ctx, base);
    return;
  }
  SetBe32(j + 0, Be32(l + 0x70));  // lj.previous
  SetBe32(j + 4, 0);
  SetBe32(j + 8, 0);  // lj.status
  SetBe32(l + 0x70, lj);
  const std::unique_ptr<PPCContext> saved = std::make_unique<PPCContext>(ctx);
  ProtectedCall call;
  call.lj = lj;
  g_protected.push_back(&call);
  if (setjmp(call.buf) == 0) {
    ctx.r1.u32 = lj;  // the callee's frame goes below the lua_longjmp
    ctx.r3.u64 = L;
    ctx.r4.u64 = ud;
    fn(ctx, base);
  } else {
    ctx = *saved;  // the guest state at the call (luaD_throw jumped here)
  }
  g_protected.pop_back();
  SetBe32(l + 0x70, Be32(j + 0));
  ctx.r1.u32 = r1;
  ctx.r3.u64 = Be32(j + 8);
}

// luaD_throw (sub_8226A988, 2026-11-09): r3 = lua_State*, r4 = the error code. The game's Lua is built as C++: an
// error is a `throw lua_longjmp*`, which the runtime cannot unwind (the SDK's HandleCppException stops), so every Lua
// error ends the game. The message is logged first: L->top (+8) - 1 is a TValue of 16 bytes (value +0, type +8; a
// string, type 4, is a TString* whose text starts at +16 and whose length is at +12).
extern "C" REX_FUNC(__imp__sub_82353220);
REX_HOOK_RAW(sub_82353220) {
  const uint32_t L = ctx.r3.u32, code = ctx.r4.u32;
  std::string message = "(not a string)";
  if (const uint8_t* l = Guest(L)) {
    const uint32_t top = Be32(l + 8);
    if (const uint8_t* tv = Guest(top - 16)) {
      if (Be32(tv + 8) == 4) {
        if (const uint8_t* ts = Guest(Be32(tv))) {
          const uint32_t len = std::min<uint32_t>(Be32(ts + 12), 400);
          message.assign(reinterpret_cast<const char*>(ts + 16), len);
        }
      }
    }
  }
  const bool log = g_errors_logged < 40;
  if (log) {
    ++g_errors_logged;
    REXLOG_ERROR("[lua] error {} (luaD_throw): {}", code, message);
  }
  // Where (the scripts carry no debug info): the running Lua functions from L->ci (+0x14; CallInfo 0x18 bytes, func
  // at +4) down, each with its first text constants, and the instruction that failed (L->savedpc, +0x18). Lua 5.1:
  // LClosure: isC +6, p +16; Proto: k +8, code +12, sizek +40, sizecode +44; instruction: op 6 bits, A 8, C 9, B 9.
  if (const uint8_t* l = log ? Guest(L) : nullptr) {
    auto string_of = [](const uint8_t* tv) -> std::string {
      if (!tv || Be32(tv + 8) != 4) return {};
      const uint8_t* ts = Guest(Be32(tv));
      return ts ? std::string(reinterpret_cast<const char*>(ts + 16), std::min<uint32_t>(Be32(ts + 12), 60)) : "";
    };
    uint32_t ci = Be32(l + 0x14);
    const uint32_t base_ci = Be32(l + 0x28);
    uint32_t pc = Be32(l + 0x18);
    for (int depth = 0; depth < 6 && ci >= base_ci && ci; ++depth, ci -= 0x18) {
      const uint8_t* c = Guest(ci);
      const uint8_t* func = c ? Guest(Be32(c + 4)) : nullptr;
      const uint8_t* cl = func ? Guest(Be32(func)) : nullptr;
      if (!cl || cl[6]) {
        REXLOG_ERROR("[lua]   #{}: C function", depth);
        if (depth == 0 && c) pc = 0;
        continue;
      }
      const uint8_t* proto = Guest(Be32(cl + 16));
      if (!proto) break;
      const uint32_t k = Be32(proto + 8), code = Be32(proto + 12), sizek = Be32(proto + 40),
                     sizecode = Be32(proto + 44);
      std::string consts;
      for (uint32_t i = 0, shown = 0; i < sizek && i < 400 && shown < 8; ++i) {
        const std::string t = string_of(Guest(k + 16 * i));
        if (!t.empty()) consts += "'" + t + "' ", ++shown;
      }
      if (depth > 0 && c) pc = Be32(c + 12);  // the caller's saved pc
      std::string where;
      if (pc > code && pc <= code + 4 * sizecode) {
        const uint8_t* ip = Guest(pc - 4);
        const uint32_t ins = ip ? Be32(ip) : 0;
        const uint32_t op = ins & 0x3F, a = (ins >> 6) & 0xFF, cc = (ins >> 14) & 0x1FF, b = ins >> 23;
        where = fmt::format("pc {} of {}, op {} A {} B {} C {}", (pc - code) / 4 - 1, sizecode, op, a, b, cc);
        if (cc >= 256) where += " key '" + string_of(Guest(k + 16 * (cc - 256))) + "'";
        if (op == 5) where += " global '" + string_of(Guest(k + 16 * (ins >> 14))) + "'";
      }
      REXLOG_ERROR("[lua]   #{}: {} | constants {}", depth, where, consts);
    }
  }
  // Caught by our luaD_rawrunprotected: back to it, as a pcall on the console.
  if (const uint8_t* l = Guest(L); l && REXCVAR_GET(mtg14_lua_catch_errors)) {
    const uint32_t lj = Be32(l + 0x70);
    for (auto it = g_protected.rbegin(); lj && it != g_protected.rend(); ++it) {
      if ((*it)->lj == lj) {
        if (uint8_t* j = Guest(lj)) SetBe32(j + 8, code);
        if (log) REXLOG_INFO("[lua]   caught (as the console's pcall does); the game goes on");
        std::longjmp((*it)->buf, 1);
      }
    }
  }
  __imp__sub_82353220(ctx, base);
}
