// Videos (WMV/XMV) de Magic 2012.
//
// Con el renderer de Renut, el primer video (el logo de WotC, ~fotograma 58) hace perder el
// dispositivo Vulkan ("device lost") y no se dibuja nada mas (2026-11-08, sin resolver: ver
// BITACORA "Renut dibuja Magic en PC"). Mientras tanto, con Renut los videos se saltan: el
// juego los pide desde Lua con playMovie (tabla de funciones Lua en 0x82CAAB60:
// playMovie -> sub_82B8C620, isMoviePlaying -> sub_82B849E8, stopMovie -> sub_82B849C0).
// playMovie lee el nombre, llama a sub_82B8C428 (arma la ruta y arranca el video con
// sub_823685E0) y devuelve a Lua su true/false. Se intercepta sub_82B8C428 para que
// responda false ("no se pudo"): la parte Lua queda intacta. (Interceptar playMovie entero
// y no devolver nada terminaba en un DbgBreak del kernel.)
// Con la GPU emulada los videos funcionan y se reproducen siempre.

#include <cstdint>
#include <string>
#include <cstring>

#include <rex/cvar.h>
#include <rex/hook.h>
#include <rex/logging.h>
#include <rex/system/kernel_state.h>

#include "mtg14_opciones.h"

#if MTG14_RENUT_RENDERER
#include "renut_engine/gpu/banjo_renut_select.h"
#endif

REXCVAR_DEFINE_BOOL(mtg14_movies_renut, false, "Mtg14",
                    "Renut's renderer: play the game's videos (false = skip them; they lose the Vulkan "
                    "device for now). The emulated GPU always plays them");

namespace {
// An MSVC std::string of the game (32-bit): the text in place when its capacity (+0x14) is under 16, else a pointer at
// +0; its size at +0x10.
std::string GuestString(uint32_t address) {
  auto* memory = rex::system::kernel_state()->memory();
  const char* text = address ? memory->TranslateVirtual<const char*>(address) : nullptr;
  return text ? std::string(text, strnlen(text, 256)) : std::string();
}

std::string GuestMsvcString(uint32_t address) {
  auto* memory = rex::system::kernel_state()->memory();
  const auto* object = address ? memory->TranslateVirtual<const uint8_t*>(address) : nullptr;
  if (!object) return {};
  const auto word = [](const uint8_t* p) {
    return uint32_t(p[0]) << 24 | uint32_t(p[1]) << 16 | uint32_t(p[2]) << 8 | p[3];
  };
  const uint32_t size = word(object + 16), capacity = word(object + 20);
  if (size > 256) return {};
  const char* text = capacity < 16 ? reinterpret_cast<const char*>(object)
                                  : memory->TranslateVirtual<const char*>(word(object));
  return text ? std::string(text, size) : std::string();
}

bool SaltarVideos() {
#if MTG14_RENUT_RENDERER
  return ::banjo::renut_gpu::Active() && !REXCVAR_GET(mtg14_movies_renut);
#else
  return false;
#endif
}
}  // namespace

// playMovie's string overload resolves the filename (82D66348) before it
// calls 82AE1930. Port messages are not files: consume them before that check.
extern "C" REX_FUNC(__imp__sub_82D68E90);
REX_HOOK_RAW(sub_82D68E90) {
  if (mtg14::opciones::HandleMessage(GuestMsvcString(ctx.r3.u32))) {
    ctx.r3.u64 = 0;
    return;
  }
  __imp__sub_82D68E90(ctx, base);
}

extern "C" REX_FUNC(__imp__sub_82AE1930);
REX_HOOK_RAW(sub_82AE1930) {  // bool (const std::string* nombre)
  static uint32_t requests_logged = 0;
  if (requests_logged++ < 24)
    REXLOG_INFO("[movies-request] '{}'", GuestString(ctx.r3.u32));
  // Our Settings menu's messages (mtg14_opciones.h): game:playMovie("mtg14:estilo=ps").
  if (mtg14::opciones::HandleMessage(GuestString(ctx.r3.u32))) {
    ctx.r3.u64 = 0;
    return;
  }
  if (SaltarVideos()) {
    static bool avisado = false;
    if (!avisado) {
      avisado = true;
      REXLOG_INFO("[movies] Renut: los videos se saltan (mtg14_movies_renut = false)");
    }
    ctx.r3.u64 = 0;  // false: el video no arranco
    return;
  }
  __imp__sub_82AE1930(ctx, base);
}
