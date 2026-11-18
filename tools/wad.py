"""Lee los .WAD de Duels of the Planeswalkers (2009, 2012, 2013 y 2014).

    python wad.py lista  fichero.WAD            # cuantos ficheros de cada tipo
    python wad.py extrae fichero.WAD carpeta    # los saca todos, por indice y tipo
    python wad.py nombres fichero.WAD [prefijo] # la ruta y el tamano de cada fichero
    python wad.py saca   fichero.WAD texto [carpeta]  # los ficheros cuya ruta contiene el texto

Formato (sacado a mano, 2026-10-02; vale para 2013 PC, 2014 PC y los WAD que
lleva dentro el OBB de Android del 2014):

    u16 0x1234, u16 0x0202, u32 largo_xml, xml <WAD_HEADER>   (carpetas por plataforma)
    u32 largo_nombres, nombres separados por \\0               (carpetas y ficheros)
    u32 n, n * (u32 id 0x01000000+i, u32 fecha)
    u32 n, u32 0x10, u32 n, n * u32 posicion absoluta de cada fichero
    arbol: registros de 16 bytes hasta el primer fichero
    en cada posicion: u32 tamano sin comprimir + bloque zlib (o el fichero tal cual)

El arbol (descifrado el 2026-10-02) va en preorden. Una carpeta es
(u32 nombre, u32 n_ficheros, u32 n_carpetas, u32 0): detras van sus carpetas,
cada una entera, y despues sus ficheros, (u32 nombre, u32 tamano en el WAD,
u32 0x01000000 + indice, u32 0). `nombre` es la posicion en la tabla de
nombres; `indice`, el de la tabla de posiciones. Las carpetas de arriba llevan
ademas un HEADER.XML cada una.
"""
import collections
import os
import struct
import sys
import zlib


def tras_indice(h):
    """Donde empieza la tabla de nombres: detras del <WAD_HEADER>, que solo
    llevan los WAD de version 0x0202 (2013 y 2014). Los 0x0201 (2009 y 2012)
    son iguales sin el."""
    if struct.unpack_from("<H", h, 2)[0] == 0x0201:
        return 8
    return 12 + struct.unpack_from("<I", h, 8)[0]


def posiciones(f):
    h = f.read(0x400000)
    o = tras_indice(h)
    largo_nombres = struct.unpack_from("<I", h, o)[0]
    o += 4 + largo_nombres
    ids = struct.unpack_from("<I", h, o)[0]
    o += 4 + ids * 8
    _, _, cuantos = struct.unpack_from("<3I", h, o)
    if o + 12 + cuantos * 4 > len(h):
        h += f.read(o + 12 + cuantos * 4 - len(h) + 16)
    return struct.unpack_from("<%dI" % cuantos, h, o + 12)


def rutas(ruta):
    """{indice: (ruta dentro del WAD, tamano en el WAD)}, del arbol de carpetas."""
    with open(ruta, "rb") as f:
        primero = min(posiciones(f))
        f.seek(0)
        h = f.read(primero)
    o = tras_indice(h)
    largo_nombres = struct.unpack_from("<I", h, o)[0]
    tabla = h[o + 4:o + 4 + largo_nombres]
    o += 4 + largo_nombres
    o += 4 + struct.unpack_from("<I", h, o)[0] * 8
    o += 12 + struct.unpack_from("<I", h, o + 8)[0] * 4
    salida = {}

    def nombre(x):
        return tabla[x:tabla.index(b"\0", x)].decode("latin1")

    def carpeta(o, padre):
        n, n_ficheros, n_carpetas, _ = struct.unpack_from("<4I", h, o)
        aqui = padre + nombre(n) + "/"
        o += 16
        for _ in range(n_carpetas):
            o = carpeta(o, aqui)
        for _ in range(n_ficheros):
            n, tam, indice, _ = struct.unpack_from("<4I", h, o)
            salida[indice & 0xFFFFFF] = (aqui + nombre(n), tam)
            o += 16
        return o

    while o + 16 <= primero:
        o = carpeta(o, "")
    return salida


def ficheros(ruta, entero=False):
    """(indice, posicion, contenido): el contenido completo con entero=True,
    si no los primeros 4 KB (basta para saber que es)."""
    with open(ruta, "rb") as f:
        for i, x in enumerate(posiciones(f)):
            f.seek(x)
            tam = struct.unpack("<I", f.read(4))[0]
            cabeza = f.read(1)
            f.seek(x + 4)
            if cabeza == b"\x78":
                try:
                    z = zlib.decompressobj()
                    if entero:
                        datos = z.decompress(f.read(tam + tam // 2 + 65536))
                        while len(datos) < tam and not z.eof:
                            datos += z.decompress(f.read(1 << 20))
                    else:
                        datos = z.decompress(f.read(65536), 4096)
                    yield i, x, datos
                    continue
                except zlib.error:
                    f.seek(x + 4)
            yield i, x, f.read(tam if entero else 4096)


def contenido(ruta, posicion):
    """El fichero que empieza en esa posicion del WAD, descomprimido."""
    with open(ruta, "rb") as f:
        f.seek(posicion)
        tam = struct.unpack("<I", f.read(4))[0]
        datos = f.read(tam + tam // 2 + 65536)
    if datos[:1] == b"x":
        try:
            return zlib.decompressobj().decompress(datos)
        except zlib.error:
            pass
    return datos[:tam]


def cabecera(ruta):
    """(el <WAD_HEADER> del WAD -vacio en los 0x0201-, la fecha que llevan sus ficheros)."""
    with open(ruta, "rb") as f:
        h = f.read(0x100000)
    xml = b""
    if struct.unpack_from("<H", h, 2)[0] != 0x0201:
        n = struct.unpack_from("<I", h, 8)[0]
        xml = h[12:12 + n]
    o = tras_indice(h)
    o += 4 + struct.unpack_from("<I", h, o)[0]
    ids = struct.unpack_from("<I", h, o)[0]
    return xml, (struct.unpack_from("<I", h, o + 8)[0] if ids else 0)


def escribir(ficheros, salida, fecha=0, xml=b""):
    """Escribe un WAD 0x0202 con {ruta dentro del WAD: contenido}. Devuelve cuantos ficheros lleva."""
    raiz = {}
    for ruta, datos in ficheros.items():
        partes = ruta.split("/")
        d = raiz
        for p in partes[:-1]:
            d = d.setdefault(p, {})
        d[partes[-1]] = datos
    nombres, off = bytearray(), {}

    def nid(s):
        if s not in off:
            off[s] = len(nombres)
            nombres.extend(s.encode("latin1") + b"\0")
        return off[s]

    registros, datos_en_orden, carpetas = [], [], [0]

    def recorrer(nombre, d):
        subs = sorted((k for k in d if isinstance(d[k], dict)), reverse=True)
        fs = sorted((k for k in d if not isinstance(d[k], dict)), reverse=True)
        carpetas[0] += 1
        registros.append(["c", nid(nombre), len(fs), len(subs)])
        for k in subs:
            recorrer(k, d[k])
        for k in fs:
            comp = zlib.compress(d[k], 9)
            registros.append(["f", nid(k), len(datos_en_orden), 4 + len(comp)])
            datos_en_orden.append((len(d[k]), comp))

    for k in sorted(raiz, reverse=True):
        recorrer(k, raiz[k])
    n = len(datos_en_orden)
    cab = struct.pack("<HHII", 0x1234, 0x0202, 578, len(xml)) + xml + struct.pack("<I", len(nombres)) + bytes(nombres)
    cab += struct.pack("<I", n) + b"".join(struct.pack("<II", 0x01000000 + i, fecha) for i in range(n))
    largo_pos = 12 + 4 * n
    inicio = len(cab) + largo_pos + 16 * len(registros)
    inicio = (inicio + 3) & ~3
    posiciones, cuerpo = [], bytearray()
    for u, comp in datos_en_orden:
        posiciones.append(inicio + len(cuerpo))
        cuerpo += struct.pack("<I", u) + comp
        cuerpo += bytes((-len(cuerpo)) % 4)
    cab += struct.pack("<3I", n, carpetas[0], n) + b"".join(struct.pack("<I", p) for p in posiciones)
    for r in registros:
        if r[0] == "c":
            cab += struct.pack("<4I", r[1], r[2], r[3], 0)
        else:
            cab += struct.pack("<4I", r[1], r[3], 0x01000000 + r[2], 0)
    cab += bytes(inicio - len(cab))
    with open(salida, "wb") as f:
        f.write(bytes(cab) + bytes(cuerpo))
    return n


def tipo(b):
    s = b.lstrip(b"\xef\xbb\xbf")
    if b.startswith(b"\x1bLua"):
        return "lua"
    if s.startswith(b"<"):
        if s.startswith(b"<?xml"):
            s = s.split(b"?>", 1)[-1].lstrip()
        raiz = s[1:40].split(b">")[0].split()[0] if len(s) > 1 else b""
        return "xml_" + raiz.decode("latin1", "replace")
    return "bin_" + b[:4].hex()


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return
    orden, ruta = sys.argv[1], sys.argv[2]
    if orden == "lista":
        k = collections.Counter(tipo(b) for _, _, b in ficheros(ruta))
        print(ruta, sum(k.values()), "ficheros")
        for t, c in k.most_common():
            print("  %6d  %s" % (c, t))
    elif orden == "nombres":
        prefijo = sys.argv[3].upper() if len(sys.argv) > 3 else ""
        for i, (nombre, tam) in sorted(rutas(ruta).items(), key=lambda x: x[1]):
            if nombre.upper().startswith(prefijo):
                print("%6d %10d  %s" % (i, tam, nombre))
    elif orden == "saca":
        texto = sys.argv[3].upper()
        destino = sys.argv[4] if len(sys.argv) > 4 else "."
        with open(ruta, "rb") as f:
            donde = posiciones(f)
        for i, (nombre, _) in sorted(rutas(ruta).items(), key=lambda x: x[1]):
            if texto in nombre.upper():
                salida = os.path.join(destino, nombre)
                os.makedirs(os.path.dirname(salida), exist_ok=True)
                with open(salida, "wb") as out:
                    out.write(contenido(ruta, donde[i]))
                print(salida)
    elif orden == "extrae":
        destino = sys.argv[3]
        os.makedirs(destino, exist_ok=True)
        for i, x, b in ficheros(ruta, entero=True):
            t = tipo(b)
            ext = "luac" if t == "lua" else ("xml" if t.startswith("xml") else "bin")
            with open(os.path.join(destino, "%05d_%s.%s" % (i, t, ext)), "wb") as out:
                out.write(b)
        print("extraidos en", destino)


if __name__ == "__main__":
    main()
