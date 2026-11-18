// Controles tactiles: en Bejeweled 3 llamaban a los TouchBegan/Moved/Ended del propio juego
// (direcciones de Bejeweled). Magic 2012 de Xbox no tiene ese camino: por ahora no hacen nada.
// La version original esta en ref/bejeweled3-nx/app/src/mtg14_touch.cpp.

#include "mtg14_touch.h"

namespace mtg14::touch {

void OnWindowMouse(MouseKind, float, float) {}

void Dispatch(PPCContext&, uint8_t*) {}

}  // namespace mtg14::touch
