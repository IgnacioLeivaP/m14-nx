#!/usr/bin/env python3
"""Saca los shaders Xenos de los WAD del juego para el cache de Renut: Magic los guarda
como archivos .SHA en el WAD (contenedores 0x102A1100 pixel / 0x102A1101 vertex), no en el
ejecutable, que es donde los busca tools/renut_shader_dump.py en otros juegos de la saga.

Mismo nombre que renut_shader_dump.py: <vs|ps>_<xxh3_64 del contenedor>.bin, contenedor =
cabecera (virt) + bloque fisico (phys), como lo recibe D3DDevice_Create*Shader.

    py -3 -I tools/shaders_wad.py <Data_Core.wad> [<Update_Data_Core.wad>] --out <out/renut_shader_dump>
"""
import argparse
import os
import struct
import sys

import xxhash

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wad  # noqa: E402  (lector de WAD de DotP, tools/wad.py)


def contenedor(data):
    """El contenedor valido al inicio de data, o None (las comprobaciones de Renut)."""
    if len(data) < 0x24 or data[:3] != b'\x10\x2a\x11':
        return None
    virt, phys = struct.unpack_from('>II', data, 4)
    ct, dt, so = struct.unpack_from('>III', data, 0x10)
    if not (0x24 <= virt < 0x10000 and 0 < phys < 0x100000 and virt <= len(data)):
        return None
    if ct >= virt or dt >= virt or not (0x24 <= so < virt - 8):
        return None
    poff, psize = struct.unpack_from('>II', data, so)
    if poff + psize != phys or len(data) < virt + phys:
        return None
    return data[:virt + phys]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('wads', nargs='+')
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    n = {'vs': 0, 'ps': 0, 'malos': 0, 'nuevos': 0}
    for ruta in a.wads:
        with open(ruta, 'rb') as source:
            positions = wad.posiciones(source)
        for index, (name, _) in wad.rutas(ruta).items():
            if not name.upper().endswith('.SHA'):
                continue
            datos = wad.contenido(ruta, positions[index])
            if datos[:3] != b'\x10\x2a\x11':
                continue
            blob = contenedor(datos)
            if blob is None:
                n['malos'] += 1
                continue
            tipo = 'vs' if struct.unpack_from('>I', blob, 0)[0] & 1 else 'ps'
            n[tipo] += 1
            p = os.path.join(a.out, f'{tipo}_{xxhash.xxh3_64_hexdigest(blob)}.bin')
            if not os.path.exists(p):
                open(p, 'wb').write(blob)
                n['nuevos'] += 1
    total = len([x for x in os.listdir(a.out) if x.endswith('.bin')])
    print(f"{n['vs']} vertex, {n['ps']} pixel, {n['malos']} invalidos; {n['nuevos']} nuevos; {total} en {a.out}")


if __name__ == '__main__':
    main()
