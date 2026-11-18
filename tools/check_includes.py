#!/usr/bin/env python3
"""Comprueba que cada `#include "..."` del codigo del port apunta a algo que existe.

    py -3 -I tools/check_includes.py [--repo .]

Sirve para lo que no se ve a simple vista al copiar un arbol de codigo: un .cpp que se quedo fuera porque solo lo
usaba un fichero del juego, una cabecera que se perdio por el camino. Los `#include <...>` no se miran.

Un include se da por bueno si esta en el repositorio (por ruta relativa o por nombre en cualquier carpeta de
`app/src`) o si lo genera la compilacion: el codigo del juego (`generated/`), los headers SPIR-V que hace el CMake a
partir de los .hlsl (`host_shaders/`), el fichero de configuracion compilada y lo que llega con `--thirdparty`.
"""
import argparse
import os
import re
import sys

EXT = ('.c', '.cc', '.cpp', '.h', '.hpp', '.inc', '.in')
INCLUDE = re.compile(r'^\s*#\s*include\s*"([^"]+)"')
IGNORADAS = {'.git', '__pycache__'}

# Lo que no esta en el repositorio porque lo produce la compilacion o se aporta aparte.
EXTERNOS = (
    'generated/',            # lo escribe el generador de codigo ReXGlue (el juego traducido)
    'host_shaders/',         # los headers SPIR-V/DXIL que el CMake hace de los .hlsl del renderer
    'mtg14_builtin_config.h',  # configure_file de src/mtg14_builtin_config.h.in
    'imgui', 'xxhash.h', 'shader_common.h', 'renderdoc_app.h', 'lz4.h', 'spirv_cross',
)


def externo(objetivo):
    o = objetivo.replace('\\', '/')
    return any(x in o for x in EXTERNOS)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--repo', default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    ap.add_argument('--quiet', action='store_true', help='solo los problemas')
    a = ap.parse_args()
    repo = os.path.abspath(a.repo)
    src = os.path.join(repo, 'app', 'src')

    # Todo lo que hay en app/: para resolver `#include "shader_cache.h"` aunque este en una subcarpeta.
    presentes = set()
    for base, dirs, files in os.walk(os.path.join(repo, 'app')):
        dirs[:] = [d for d in dirs if d not in IGNORADAS and d != 'thirdparty']
        for nombre in files:
            presentes.add(os.path.join(base, nombre).replace(os.sep, '/'))
            presentes.add(os.path.basename(nombre))

    fuera, externos, revisados, total = [], [], 0, 0
    for base, dirs, files in os.walk(src):
        dirs[:] = sorted(d for d in dirs if d not in IGNORADAS)
        for nombre in sorted(files):
            if not nombre.endswith(EXT):
                continue
            ruta = os.path.join(base, nombre)
            rel = os.path.relpath(ruta, repo).replace(os.sep, '/')
            total += 1
            try:
                with open(ruta, encoding='utf-8') as f:
                    lineas = f.readlines()
            except UnicodeDecodeError:
                fuera.append('%s: no es UTF-8' % rel)
                continue
            for numero, linea in enumerate(lineas, 1):
                m = INCLUDE.match(linea)
                if not m:
                    continue
                objetivo = m.group(1)
                revisados += 1
                candidatos = [os.path.join(base, objetivo).replace(os.sep, '/'),
                              os.path.join(os.path.dirname(ruta), objetivo).replace(os.sep, '/')]
                if any(c in presentes for c in candidatos) or os.path.basename(objetivo) in presentes:
                    continue
                if externo(objetivo):
                    externos.append('%s:%d  %s' % (rel, numero, objetivo))
                else:
                    fuera.append('%s:%d  no esta: %s' % (rel, numero, objetivo))
    if not a.quiet:
        print('check_includes: %d ficheros de codigo, %d #include "..." revisados' % (total, revisados))
        print('  %d son de la compilacion o de --thirdparty (no estan ni deben estar en el repositorio)'
              % len(externos))
    if fuera:
        print('')
        print('%d SIN RESOLVER:' % len(fuera))
        for f in fuera:
            print('  - %s' % f)
        return 1
    if not a.quiet:
        print('  todos los includes propios se resuelven dentro del repositorio')
    return 0


if __name__ == '__main__':
    sys.exit(main())
