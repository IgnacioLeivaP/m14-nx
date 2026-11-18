#!/usr/bin/env python3
"""Lee y escribe los .WAD de Magic 2014 (version 0x0201), para armar variantes de Update001.wad.

    py -3 -I tools/wad14.py lista  fichero.wad
    py -3 -I tools/wad14.py rehace fichero.wad salida.wad [carpeta_extra ...]

`rehace` vuelve a escribir el WAD con los mismos ficheros y le agrega (o reemplaza) los de cada carpeta extra: la
ruta dentro de la carpeta es la del WAD (p. ej. UPDATE001/DATA_ALL_PLATFORMS/.../XBOX_A.TDX).

Formato (2026-11-09, mirado en Update001.wad de la TU #3 y en Data_Core.wad):
    u16 0x1234, u16 0x0201, u32 578 (igual en todos)
    u32 largo_nombres, nombres separados por \\0 (sin repetir)
    u32 n, n * (u32 0x01000000 + i, u32 fecha)
    u32 n, u32 numero de carpetas, u32 n, n * u32 posicion de cada fichero
    arbol en preorden, registros de 16 bytes: carpeta (nombre, n_ficheros, n_carpetas, 0) con sus carpetas y luego
    sus ficheros (nombre, 4 + largo comprimido, 0x01000000 + indice, 0); hijos en orden alfabetico DESCENDENTE.
    en cada posicion (alineada a 4): u32 largo sin comprimir + bloque zlib.
"""
import struct
import sys
import zlib


class RawBlock(bytes):
    """Bloque WAD original: preservar tambien parches con size 0xFFFFFFFF."""
    pass


def leer(ruta):
    """{ruta dentro del WAD: contenido}, la fecha de los ficheros y el valor de +4."""
    h = open(ruta, 'rb').read()
    assert struct.unpack_from('<HH', h, 0) == (0x1234, 0x0202), 'no es un WAD 0x0202'
    o = 12 + struct.unpack_from('<I', h, 8)[0]
    largo = struct.unpack_from('<I', h, o)[0]
    tabla = h[o + 4:o + 4 + largo]
    o += 4 + largo
    n = struct.unpack_from('<I', h, o)[0]
    fecha = struct.unpack_from('<I', h, o + 8)[0] if n else 0
    fechas = [struct.unpack_from('<I', h, o + 8 + 8*i)[0] for i in range(n)]
    o += 4 + 8 * n
    _, _, c = struct.unpack_from('<3I', h, o)
    pos = struct.unpack_from('<%dI' % c, h, o + 12)
    o += 12 + 4 * c
    primero = min(pos) if pos else len(h)

    def nombre(x):
        return tabla[x:tabla.index(b'\0', x)].decode('latin1')

    out = {}

    def carpeta(o, padre):
        nm, nf, nc, _ = struct.unpack_from('<4I', h, o)
        aqui = padre + nombre(nm) + '/'
        o += 16
        for _ in range(nc):
            o = carpeta(o, aqui)
        for _ in range(nf):
            nm, tam, ix, _ = struct.unpack_from('<4I', h, o)
            p = pos[ix & 0xFFFFFF]
            block = RawBlock(h[p:p + tam])
            block.fecha = fechas[ix & 0xFFFFFF]
            out[aqui + nombre(nm)] = block
            o += 16
        return o

    while o + 16 <= primero:
        o = carpeta(o, '')
    return out, fecha


def escribir(ficheros, salida, fecha=0x3F099984, xml=b''):
    # Arbol: {nombre: subarbol} para carpetas, {nombre: bytes} para ficheros.
    raiz = {}
    for ruta, datos in ficheros.items():
        partes = ruta.split('/')
        d = raiz
        for p in partes[:-1]:
            d = d.setdefault(p, {})
        d[partes[-1]] = datos
    nombres, off = bytearray(), {}

    def nid(s):
        if s not in off:
            off[s] = len(nombres)
            nombres.extend(s.encode('latin1') + b'\0')
        return off[s]

    registros, datos_en_orden, carpetas = [], [], [0]

    def recorrer(nombre, d):
        subs = sorted((k for k in d if isinstance(d[k], dict)), reverse=True)
        fs = sorted((k for k in d if not isinstance(d[k], dict)), reverse=True)
        carpetas[0] += 1
        registros.append(['c', nid(nombre), len(fs), len(subs)])
        for k in subs:
            recorrer(k, d[k])
        for k in fs:
            if isinstance(d[k], RawBlock):
                u = struct.unpack_from('<I', d[k], 0)[0]
                comp = d[k][4:]
            else:
                u = len(d[k])
                comp = zlib.compress(d[k], 9)
            registros.append(['f', nid(k), len(datos_en_orden), 4 + len(comp)])
            datos_en_orden.append((u, comp, getattr(d[k], 'fecha', fecha)))

    for k in sorted(raiz, reverse=True):
        recorrer(k, raiz[k])
    n = len(datos_en_orden)
    cab = struct.pack('<HHII', 0x1234, 0x0202, 578, len(xml)) + xml + struct.pack('<I', len(nombres)) + bytes(nombres)
    cab += struct.pack('<I', n) + b''.join(struct.pack('<II', 0x01000000 + i, stamp) for i, (_, _, stamp) in enumerate(datos_en_orden))
    largo_pos = 12 + 4 * n
    inicio = len(cab) + largo_pos + 16 * len(registros)
    inicio = (inicio + 3) & ~3
    posiciones, cuerpo = [], bytearray()
    for u, comp, stamp in datos_en_orden:
        posiciones.append(inicio + len(cuerpo))
        cuerpo += struct.pack('<I', u) + comp
        cuerpo += bytes((-len(cuerpo)) % 4)
    cab += struct.pack('<3I', n, carpetas[0], n) + b''.join(struct.pack('<I', p) for p in posiciones)
    for r in registros:
        if r[0] == 'c':
            cab += struct.pack('<4I', r[1], r[2], r[3], 0)
        else:
            cab += struct.pack('<4I', r[1], r[3], 0x01000000 + r[2], 0)
    cab += bytes(inicio - len(cab))
    open(salida, 'wb').write(bytes(cab) + bytes(cuerpo))
    return n


def main():
    orden = sys.argv[1]
    if orden == 'lista':
        fs, _ = leer(sys.argv[2])
        for r in sorted(fs):
            print('%9d  %s' % (len(fs[r]), r))
    elif orden == 'rehace':
        import os
        fs, fecha = leer(sys.argv[2])
        extra = 0
        for carpeta in sys.argv[4:]:
            for base, _, archivos in os.walk(carpeta):
                for a in archivos:
                    p = os.path.join(base, a)
                    r = os.path.relpath(p, carpeta).replace(os.sep, '/').upper()
                    fs[r] = open(p, 'rb').read()
                    extra += 1
        raw = open(sys.argv[2], 'rb').read()
        xml = raw[12:12 + struct.unpack_from('<I', raw, 8)[0]]
        n = escribir(fs, sys.argv[3], fecha or 0x3F099984, xml)
        print('%s: %d ficheros (%d de las carpetas extra)' % (sys.argv[3], n, extra))


if __name__ == '__main__':
    main()
