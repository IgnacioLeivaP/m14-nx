#!/usr/bin/env python3
"""Dibuja las variantes de iconos de botones (PlayStation y Switch) de Magic 2014.

Los iconos de Xbox que trae el juego se sustituyen por dibujos propios de este repositorio: formas geometricas y
letras hechas aqui, sin arte de terceros ni fuentes del sistema (nada que no se pueda redistribuir).

    py -3 -I tools/mtg14_iconos.py --data <carpeta_del_juego> [--out <carpeta_de_salida>]

Entrada: la carpeta del juego preparada por el instalador, con Data_Core.wad y Update_Data_Core.wad (los del
usuario). Salida: <out>/mtg14_buttons_ps.bin y <out>/mtg14_buttons_switch.bin: el Update_Data_Core.wad del Title
Update con las texturas de los botones cambiadas. El SDK lee la variante que el jugador elige en lugar de
Update_Data_Core.wad, por eso van en la carpeta de datos del juego.

TDX (Xbox 360): cabecera de 16 bytes en little endian (u16 0x0200, ancho, alto, niveles, u32 banderas, u32 formato)
y detras los pixeles, en formato 21 (BGRA de 32 bits, lineal). Las hojas SYMBOLS y SYMBOLS_FE de 1024x1024 llevan 11
niveles y, porque sus banderas tienen el bit 0x200, un bloque extra: tras los 16 bytes va su largo y el bloque, y
detras los pixeles. Se conservan los 11 niveles y ese bloque; los niveles de 1024 a 32 se rehacen y la cola
empaquetada menor de 32 se queda como estaba.
"""
import argparse
import os
import struct
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wad  # noqa: E402
import wad14  # noqa: E402

TEX = 'DATA_X360/ART_ASSETS/TEXTURES/ANIMATIONTEXURES'
FONTS = 'DATA_ALL_PLATFORMS/ART_ASSETS/FONTS'
HOJAS = ('SYMBOLS.TDX', 'SYMBOLS_FE.TDX')

# Casillas de los botones de Xbox en SYMBOLS/SYMBOLS_FE (y0, x0, y1, x1), en la hoja de 1024x1024 (rejilla de 84).
CASILLAS = {
    'A': (598, 178, 658, 242), 'B': (598, 262, 658, 326),
    'X': (598, 346, 658, 410), 'Y': (598, 430, 658, 494),
    'LB': (514, 848, 578, 916), 'RB': (514, 932, 578, 1000),
    'LT': (598, 8, 662, 76), 'RT': (598, 92, 662, 160),
    'BACK': (598, 596, 662, 664), 'START': (598, 680, 662, 748),
}

# Colores de los dibujos (formas y letras propias, no una copia de ningun glifo).
AZUL = (58, 106, 200, 255)
ROJO = (206, 60, 60, 255)
ROSA = (216, 96, 176, 255)
VERDE = (66, 172, 96, 255)
GRIS = (86, 92, 104, 255)
CLARO = (240, 242, 246, 255)

BGRA = 21
BLOQUE = 0x200   # la hoja lleva un bloque extra entre la cabecera y los pixeles


def leer_tdx(d):
    """(imagen, niveles, banderas, formato, desplazamiento de los pixeles) de un TDX; la imagen es el nivel mayor."""
    _, w, h, niveles, banderas, fmt = struct.unpack_from('<HHHHII', d, 0)
    offset = 20 + struct.unpack_from('<I', d, 16)[0] if banderas & BLOQUE else 16
    if fmt != BGRA:
        raise SystemExit('formato de TDX no soportado: %d (%dx%d)' % (fmt, w, h))
    im = Image.frombuffer('RGBA', (w, h), d[offset:offset + w * h * 4], 'raw', 'BGRA', 0, 1).copy()
    return im, niveles, banderas, fmt, offset


def releer_niveles(original, im):
    """El TDX original con los niveles de 1024 a 32 rehechos con `im` (BGRA de 32 bits)."""
    datos = bytearray(original)
    _, _, _, _, offset = leer_tdx(original)
    nivel = im
    while nivel.width >= 32:
        pixeles = nivel.tobytes('raw', 'BGRA')
        if offset + len(pixeles) > len(datos):
            raise SystemExit('el TDX no tiene sitio para el nivel de %d px' % nivel.width)
        datos[offset:offset + len(pixeles)] = pixeles
        offset += len(pixeles)
        nivel = nivel.resize((nivel.width // 2, nivel.height // 2), Image.LANCZOS)
    return bytes(datos)


def nuevo_tdx(im, banderas, niveles):
    """Un TDX con la cabecera del original y los `niveles` pixeles de `im` (BGRA)."""
    im = im.convert('RGBA')
    cabecera = bytearray(struct.pack('<HHHHII', 0x0200, im.width, im.height, niveles, banderas, BGRA))
    if banderas & BLOQUE:
        # El bloque extra (6060 bytes en las hojas) se rellena fuera: aqui solo su tamano.
        raise SystemExit('nuevo_tdx no se usa con hojas que llevan bloque extra')
    nivel = im
    for _ in range(niveles):
        cabecera += nivel.tobytes('raw', 'BGRA')
        nivel = nivel.resize((max(1, nivel.width // 2), max(1, nivel.height // 2)), Image.LANCZOS)
    return bytes(cabecera)


def _fuente():
    """La fuente de mapa de bits de Pillow: sin ficheros de fuente del sistema."""
    return ImageFont.load_default()


def texto(txt, ancho, alto, color):
    """El texto, lo mayor que entra en ancho x alto, centrado en un lienzo de ese tamano."""
    f = _fuente()
    lienzo = Image.new('RGBA', (max(1, ancho), max(1, alto)), (0, 0, 0, 0))
    caja = f.getbbox(txt)
    tw, th = caja[2] - caja[0], caja[3] - caja[1]
    if tw <= 0 or th <= 0:
        return lienzo
    base = Image.new('RGBA', (tw + 2, th + 2), (0, 0, 0, 0))
    ImageDraw.Draw(base).text((1 - caja[0], 1 - caja[1]), txt, font=f, fill=color)
    f2 = min(ancho / base.width, alto / base.height)
    nuevo = base.resize((max(1, round(base.width * f2)), max(1, round(base.height * f2))), Image.LANCZOS)
    lienzo.alpha_composite(nuevo, ((ancho - nuevo.width) // 2, (alto - nuevo.height) // 2))
    return lienzo


def forma(tipo, ancho, alto, color):
    """Un dibujo propio de la forma pedida, lo mayor que entra en ancho x alto."""
    esc = 4  # se dibuja grande y se reduce: bordes suaves
    W, H = max(1, ancho) * esc, max(1, alto) * esc
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    g = max(2, min(W, H) // 10)
    if tipo == 'cruz':
        w = max(2, (W - 2 * g) // 3)
        d.rectangle((W // 2 - w // 2, g, W // 2 + w // 2, H - g), fill=color)
        d.rectangle((g, H // 2 - w // 2, W - g, H // 2 + w // 2), fill=color)
    elif tipo == 'circulo':
        d.ellipse((g, g, W - g, H - g), outline=color, width=max(2, (W - 2 * g) // 6))
    elif tipo == 'cuadrado':
        d.rectangle((g, g, W - g, H - g), outline=color, width=max(2, (W - 2 * g) // 6))
    elif tipo == 'triangulo':
        d.polygon([(W // 2, g), (W - g, H - g), (g, H - g)], outline=color, width=max(2, (W - 2 * g) // 6))
    elif tipo == 'redondo':  # el fondo de una tecla: se lee sobre menus claros y oscuros
        d.ellipse((0, 0, W - 1, H - 1), fill=color)
    elif tipo == 'pastilla':
        d.rounded_rectangle((0, 0, W - 1, H - 1), radius=max(2, H // 3), fill=color)
    return im.resize((max(1, ancho), max(1, alto)), Image.LANCZOS)


def tecla(txt, ancho, alto, letra=CLARO, fondo=GRIS, forma_fondo='redondo'):
    im = forma(forma_fondo, ancho, alto, fondo)
    im.alpha_composite(texto(txt, int(ancho * 0.72), int(alto * 0.72), letra),
                       (int(ancho * 0.14), int(alto * 0.14)))
    return im


def tecla_forma(tipo, ancho, alto, color, fondo=GRIS):
    """Una tecla con una forma dentro (la cruz, el circulo, el cuadrado o el triangulo de PlayStation)."""
    im = forma('redondo', ancho, alto, fondo)
    dentro = int(ancho * 0.60)
    im.alpha_composite(forma(tipo, dentro, dentro, color), ((ancho - dentro) // 2, (alto - dentro) // 2))
    return im


def dibujos():
    """{estilo: {boton: imagen}} con las formas y las letras de cada estilo."""
    ps = {
        'A': tecla_forma('cruz', 64, 64, AZUL), 'B': tecla_forma('circulo', 64, 64, ROJO),
        'X': tecla_forma('cuadrado', 64, 64, ROSA), 'Y': tecla_forma('triangulo', 64, 64, VERDE),
        'LB': tecla('L1', 64, 64), 'RB': tecla('R1', 64, 64),
        'LT': tecla('L2', 64, 64, forma_fondo='pastilla'), 'RT': tecla('R2', 64, 64, forma_fondo='pastilla'),
        'BACK': tecla('SEL', 64, 64, forma_fondo='pastilla'), 'START': tecla('STA', 64, 64, forma_fondo='pastilla'),
    }
    switch = {
        'A': tecla('A', 64, 64), 'B': tecla('B', 64, 64),
        'X': tecla('X', 64, 64), 'Y': tecla('Y', 64, 64),
        'LB': tecla('L', 64, 64), 'RB': tecla('R', 64, 64),
        'LT': tecla('ZL', 64, 64, forma_fondo='pastilla'), 'RT': tecla('ZR', 64, 64, forma_fondo='pastilla'),
        'BACK': tecla('-', 64, 64, forma_fondo='pastilla'), 'START': tecla('+', 64, 64, forma_fondo='pastilla'),
    }
    return {'ps': ps, 'switch': switch}


def caja(im):
    """(x0, y0, x1, y1) de lo que no es transparente."""
    a = np.array(im)[:, :, 3]
    ys, xs = np.nonzero(a > 40)
    if not len(xs):
        return (0, 0, im.width, im.height)
    return (int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1)


def encajar(icono, w, h):
    """El icono del mayor tamano que entra en w x h sin deformarse, centrado en un lienzo w x h."""
    f = min(w / icono.width, h / icono.height)
    nuevo = icono.resize((max(1, round(icono.width * f)), max(1, round(icono.height * f))), Image.LANCZOS)
    lienzo = Image.new('RGBA', (max(1, w), max(1, h)), (0, 0, 0, 0))
    lienzo.alpha_composite(nuevo, ((w - nuevo.width) // 2, (h - nuevo.height) // 2))
    return lienzo


def entradas(core):
    """{ruta dentro de DATA_CORE: contenido} de las texturas que se cambian."""
    queridas = {}
    posiciones = None
    with open(core, 'rb') as f:
        posiciones = wad.posiciones(f)
    for i, (nombre, _) in wad.rutas(core).items():
        alto = nombre.upper()
        if alto.startswith('DATA_CORE/'):
            alto = alto[len('DATA_CORE/'):]
        boton = alto.rsplit('/', 1)[-1]
        if (alto.startswith(TEX + '/XBOX_') and alto.endswith('.TDX')) or \
                alto in [FONTS + '/' + h for h in HOJAS] or boton in HOJAS:
            queridas[alto] = wad.contenido(core, posiciones[i])
    return queridas


def cambios_estilo(dib, queridas):
    """{ruta dentro de DATA_CORE: TDX nuevo} para un estilo."""
    cambios = {}
    for ruta, datos in queridas.items():
        nombre = ruta.rsplit('/', 1)[1].upper()
        if nombre.startswith('XBOX_') and nombre[5:-4] in dib:
            boton = nombre[5:-4]
            im, niveles, banderas, _, _ = leer_tdx(datos)
            if im.size != (64, 64):
                continue  # las grises van comprimidas: se quedan como estan
            x0, y0, x1, y1 = caja(im)
            nuevo = Image.new('RGBA', im.size, (0, 0, 0, 0))
            nuevo.alpha_composite(encajar(dib[boton], x1 - x0, y1 - y0), (x0, y0))
            cambios[ruta] = nuevo_tdx(nuevo, banderas, niveles)
        elif nombre in HOJAS:
            im, _, _, _, _ = leer_tdx(datos)
            for boton, (y0, x0, y1, x1) in CASILLAS.items():
                # Se limpia la casilla entera de 84 pixeles (incluye el texto de SELECT/START y los bordes del
                # boton de Xbox) y se pone el dibujo nuevo en la caja que ocupaba el viejo.
                cx, cy = (x0 // 84) * 84, (y0 // 84) * 84
                im.paste((0, 0, 0, 0), (cx, cy, min(cx + 84, im.width), min(cy + 84, im.height)))
                im.alpha_composite(encajar(dib[boton], x1 - x0, y1 - y0), (x0, y0))
            cambios[ruta] = releer_niveles(datos, im)
    return cambios


def variante(estilo, dib, core, update, salida):
    """El Update_Data_Core.wad del usuario con las texturas de ese estilo cambiadas."""
    print('  %s: sacando las texturas de %s' % (estilo, os.path.basename(core)))
    queridas = entradas(core)
    print('  %s: %d texturas del juego' % (estilo, len(queridas)))
    cambios = cambios_estilo(dib, queridas)

    fs, fecha = wad14.leer(update)
    crudo = open(update, 'rb').read(1024)
    xml = crudo[12:12 + struct.unpack_from('<I', crudo, 8)[0]]
    originales = len(fs)
    for ruta, datos in cambios.items():
        fs['UPDATE_DATA_CORE/' + ruta] = datos
    n = wad14.escribir(fs, salida, fecha, xml)
    print('  %s: %s (%d texturas cambiadas de %d; %d en el WAD)' % (estilo, salida, len(cambios), originales, n))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--data', required=True, help='carpeta del juego preparada (Data_Core.wad, Update_Data_Core.wad)')
    ap.add_argument('--out', help='carpeta donde dejar las variantes (por defecto, la misma)')
    a = ap.parse_args()
    core = os.path.join(a.data, 'Data_Core.wad')
    update = os.path.join(a.data, 'Update_Data_Core.wad')
    for p in (core, update):
        if not os.path.exists(p):
            sys.exit('falta %s' % p)
    salida = a.out or a.data
    os.makedirs(salida, exist_ok=True)
    for estilo, dib in dibujos().items():
        variante(estilo, dib, core, update, os.path.join(salida, 'mtg14_buttons_%s.bin' % estilo))
    print('listo: 2 variantes en %s' % salida)
    return 0


if __name__ == '__main__':
    sys.exit(main())
