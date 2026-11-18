#!/usr/bin/env python3
"""Comprueba que este repositorio no lleva nada del juego (ni datos, ni arte, ni codigo generado).

    py -3 tools/check_clean.py [--repo .] [--ref DIR ...] [--quiet]

Falla (codigo 1) si encuentra dentro del repositorio:
  - extensiones de datos del juego o de compilados (.xex, .xexp, .wad, .nxpack, .nro, .bin, .TDX, .lua, ...)
  - cabeceras: XEX2, WAD (0x1234 version 0x0201/0x0202), TDX (0x0200), STFS (LIVE / PNG) o bytecode Lua (\\x1bLua)
  - carpetas `generated` (el codigo del juego traducido a C++)
  - archivos de mas de 5 MB
  - rutas personales (C:\\Users, D:\\Juegos, /home/...), direcciones de correo o cadenas que parezcan claves
  - comentarios que son un listado de instrucciones PowerPC (el desensamblado del juego pegado al lado del codigo)
  - cualquier archivo cuyo SHA256 coincida con uno de las carpetas de referencia (--ref: por defecto ../game,
    ../tu, los paquetes DLC de la raiz del proyecto y ../nx/out/pack)

Magic 2014 guarda sus menus como bytecode Lua compilado (.LOB) dentro de sus WAD, asi que `.lua` y `.luac` tambien
estan prohibidos: los scripts se generan en la instalacion (`install/mtg14_lua.py`), no viajan aqui.

Los SHA256 de los archivos del juego SI pueden publicarse (son punteros de verificacion, no datos del juego): el
instalador los lleva en install/games/<juego>.toml, el README los repite en su tabla y aqui se toleran en esos dos
sitios. Fuera de ellos, una cadena hexadecimal de 64 caracteres solo se acepta si la linea dice que es una huella
(sha256 / hash) de una funcion o de un fichero generado.

`sdk/` es codigo de terceros copiado tal cual (ReXGlue y sus dependencias pequenas): ahi solo se miran las cosas
que no pueden estar nunca -- binarios, datos del juego, tamano y SHA256 --, no las heuristicas de texto (los
ficheros llevan el correo de su autor en la cabecera de licencia, imagenes de su documentacion y datos de prueba
que no son UTF-8). Los logos de documentacion y las pruebas de esas carpetas son suyos, no del juego.
"""
import argparse
import hashlib
import os
import re
import sys

MAX_BYTES = 5 << 20
ZONA_VENDIDA = ('sdk/',)   # codigo de terceros tal cual: solo se comprueban binarios, datos y tamanos

EXT_PROHIBIDAS = {
    '.xex', '.xexp', '.xbe', '.xap', '.wad', '.nxpack', '.nxidx', '.pack', '.nsp', '.xci', '.nro', '.nso', '.nca',
    '.bin', '.tdx', '.dds', '.luac', '.lua', '.lob', '.xma', '.wmv', '.bik', '.ogg', '.wav', '.mp3', '.iso',
    '.stfs', '.elf', '.kip', '.pak', '.zip', '.7z', '.rar', '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.ico',
    '.ttf', '.otf', '.pdb', '.dll', '.exe', '.obj', '.lib', '.a', '.o',
}
# En la zona vendida solo se prohibe lo que es un binario o un dato del juego: sus imagenes de documentacion y sus
# datos de prueba son de sus autores.
EXT_VENDIDA = {
    '.xex', '.xexp', '.xbe', '.xap', '.wad', '.nxpack', '.nxidx', '.pack', '.nsp', '.xci', '.nro', '.nso', '.nca',
    '.bin', '.tdx', '.dds', '.luac', '.lua', '.lob', '.xma', '.wmv', '.bik', '.ogg', '.wav', '.mp3', '.iso',
    '.stfs', '.elf', '.kip', '.pak', '.zip', '.7z', '.rar', '.pdb', '.dll', '.exe', '.obj', '.lib', '.a', '.o',
}
CARPETAS_PROHIBIDAS = {'generated', 'obj', 'bin', 'build', 'out'}
CARPETAS_IGNORADAS = {'.git', '__pycache__'}   # las que deja Python al ejecutar las herramientas
TEXTO = {'.py', '.md', '.toml', '.json', '.txt', '.cmake', '.cpp', '.h', '.hpp', '.inc', '.hlsl', '.hlsli', '.sh',
         '.ps1', '.yml', '.yaml', '.gitignore', '.in'}

CABECERAS_JUEGO = [
    (b'XEX2', 'XEX2 (ejecutable de Xbox 360)'),
    (b'XEX1', 'XEX1 (ejecutable de Xbox 360)'),
    (b'\x1bLua', 'bytecode Lua'),
    (b'LIVE', 'STFS (paquete de Xbox 360)'),
]
CABECERAS_ARTE = [
    (b'\x89PNG', 'PNG (imagen)'),
    (b'DDS ', 'DDS (textura)'),
]

RUTAS_PERSONALES = [
    (re.compile(r'[A-Za-z]:\\\\?Users\\\\?', re.I), 'ruta C:\\Users'),
    (re.compile(r'[A-Za-z]:\\\\?Juegos\\\\?', re.I), 'ruta D:\\Juegos'),
    (re.compile('Programming' + ' projects', re.I), 'ruta de otro proyecto'),
    (re.compile(r'/home/[a-z0-9_.-]+/'), 'ruta /home/...'),
    (re.compile(r'/Users/[a-z0-9_.-]+/'), 'ruta /Users/...'),
]
CORREO = re.compile(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}')
CLAVES = [
    (re.compile(r'-----BEGIN [A-Z ]*PRIVATE KEY-----'), 'clave privada'),
    (re.compile(r'AKIA[0-9A-Z]{16}'), 'clave de AWS'),
    (re.compile(r'(?i)(password|passwd|contrase[ñn]a|secret|api[_-]?key|token|bearer|authorization)\s*[:=]\s*'
                r'["\']?[A-Za-z0-9_\-./+]{12,}'), 'cadena que parece una clave'),
    (re.compile(r'(?i)(ghp|gho|ghs|github_pat)_[A-Za-z0-9_]{20,}'), 'token de GitHub'),
]
HEX_LARGO = re.compile(r'\b[0-9a-fA-F]{64}\b')

# Un comentario que es una instruccion PowerPC: el desensamblado del juego pegado al lado del codigo. Cuenta solo
# si empieza por un mnemotecnico de verdad y detras viene un registro o una direccion, para no caer en prosa que
# empiece por "and", "or" o "not".
PPC_MNEMOS = set('''
b bctr bl blr bctrl blrl bdnz beq bne ble bge bgt blt beqlr bnelr ba bla bclr bdz
mflr mtlr mfctr mtcrf mtctr mfcr mtmsr mfspr mtspr mftb
li lis lwz lwzu lwzx lwzux lhz lha lhzx lbz lbzx lfs lfsx lfd lfdx lwarx lhbrx lwbrx
stw stwu stwux stwx sth sthbrx stwbrx stb stfs stfsx stfd stfdx stwcx std stdu
mr addi addis add ori oris andi andis xori xor clrlwi clrrwi slwi srwi rlwinm rlwimi
extsb extsh extlw cntlzw cmpwi cmplwi cmpw cmplw cmpd cmpl crxor crand cror creqv
fmr fmuls fadds fsubs fadd fsub fmadds fmsubs fnmsubs fmadd fdivs fdiv fneg fabs frsp
fcmpo fcmpu fres fsel fctiwz fctidz fcfid psq_l psq_st
mullw mulhw mulhd mulli divw divwu subf subfc subfic neg nop sync isync subfe adde
and or not slw srw srawi sraw dcbf dcbst dcbt dcbz icbi eieio
xxlor xxlxor xxpermdi xxspltw lvx stvx lvsl lvsr vspltw vmrghw vmrglw vperm vcmpgefp
vaddfp vmaddfp vsubfp vandc vxor vor vcmpeqfp vrefp vcmpgtfp
'''.split())
PPC_LINEA = re.compile(r'^\s*(?://+|#)\s*(?:0x[0-9A-Fa-f]{8}\s+)?([A-Za-z]{1,9})\s*(.*)$')
PPC_OPERANDO = re.compile(r'^(?:[rf]\d{1,2}\b|cr\d\b|0x[0-9A-Fa-f]+)')
PPC_AMBIGUOS = {'and', 'or', 'not'}   # palabras corrientes: solo cuentan con una lista de registros
PPC_SUELTOS = {'bctr', 'blr', 'bctrl', 'blrl', 'nop', 'sync', 'isync', 'beqlr', 'bnelr'}


def listado_powerpc(linea):
    """True si la linea es un comentario que transcribe instrucciones del juego."""
    m = PPC_LINEA.match(linea)
    if not m:
        return False
    mnemotecnico, resto = m.group(1).lower(), m.group(2)
    if mnemotecnico not in PPC_MNEMOS:
        return False
    if mnemotecnico in PPC_SUELTOS and not resto.strip():
        return True
    if mnemotecnico in PPC_AMBIGUOS and ',' not in resto:
        return False
    return bool(PPC_OPERANDO.match(resto))


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        while True:
            piece = f.read(1 << 20)
            if not piece:
                break
            h.update(piece)
    return h.hexdigest()


def cabecera(ruta, solo_juego=False):
    """(nombre, motivo) si el archivo empieza como algo del juego."""
    with open(ruta, 'rb') as f:
        d = f.read(16)
    if len(d) < 4:
        return None
    for magic, motivo in (CABECERAS_JUEGO if solo_juego else CABECERAS_JUEGO + CABECERAS_ARTE):
        if d.startswith(magic):
            # LIVE tambien aparece dentro de textos: solo cuenta al principio y con cabecera de paquete.
            if magic == b'LIVE' and not (len(d) >= 8 and d[4:6] in (b'\x00\x00', b'\x00\x01')):
                continue
            return motivo
    # WAD de la saga: u16 0x1234 y detras la version (0x0201 en 2009/2012, 0x0202 en 2013/2014)
    if d[0:2] == b'\x34\x12' and d[2:4] in (b'\x01\x02', b'\x02\x02'):
        return 'WAD (0x1234)'
    # TDX de Xbox 360: u16 0x0200 y un tamano razonable detras
    if d[0:2] == b'\x00\x02':
        w = int.from_bytes(d[2:4], 'little')
        h = int.from_bytes(d[4:6], 'little')
        if 1 <= w <= 4096 and 1 <= h <= 4096:
            return 'TDX (0x0200)'
    return None


def referencias(raiz):
    """Carpetas cuyos archivos no pueden aparecer en el repositorio (los datos del usuario, en modo lectura)."""
    proyecto = os.path.dirname(os.path.abspath(raiz))
    return [c for c in (os.path.join(proyecto, 'game'), os.path.join(proyecto, 'tu'),
                        os.path.join(proyecto, 'dlc'), os.path.join(proyecto, 'nx', 'out', 'pack'))
            if os.path.isdir(c)]


def sueltos(raiz):
    """Archivos del usuario que estan en la raiz del proyecto (el paquete del Title Update, por ejemplo)."""
    proyecto = os.path.dirname(os.path.abspath(raiz))
    salida = []
    for nombre in sorted(os.listdir(proyecto)):
        ruta = os.path.join(proyecto, nombre)
        if os.path.isfile(ruta) and re.match(r'(?i)tu[0-9a-f_]+$', nombre):
            salida.append(ruta)
    return salida


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--repo', default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    help='carpeta del repositorio a revisar (por defecto, la de este script)')
    ap.add_argument('--ref', action='append', default=[], help='carpeta de referencia con datos del juego '
                                                             '(se puede repetir; por defecto game/, tu/, dlc y el pack)')
    ap.add_argument('--quiet', action='store_true', help='solo los problemas')
    a = ap.parse_args()
    repo = os.path.abspath(a.repo)

    problemas = []
    archivos = []
    for base, dirs, files in os.walk(repo):
        dirs[:] = sorted(d for d in dirs if d not in CARPETAS_IGNORADAS)
        for d in dirs:
            if d.lower() in CARPETAS_PROHIBIDAS:
                problemas.append('carpeta prohibida: %s' % os.path.relpath(os.path.join(base, d), repo))
        for nombre in sorted(files):
            archivos.append(os.path.join(base, nombre))

    hashes = {}
    powerpc = 0
    for ruta in archivos:
        rel = os.path.relpath(ruta, repo).replace(os.sep, '/')
        ext = os.path.splitext(ruta)[1].lower()
        tam = os.path.getsize(ruta)
        vendido = rel.startswith(ZONA_VENDIDA)
        # Un fichero de licencia se llama COPYING.LIB y no es una biblioteca.
        licencia = os.path.basename(ruta).lower().startswith(('copying', 'license', 'licence'))
        if ext in (EXT_VENDIDA if vendido else EXT_PROHIBIDAS) and not licencia:
            problemas.append('extension prohibida %s: %s' % (ext, rel))
        if tam > MAX_BYTES:
            problemas.append('archivo de %d bytes (maximo %d): %s' % (tam, MAX_BYTES, rel))
        motivo = cabecera(ruta, solo_juego=vendido)
        if motivo:
            problemas.append('cabecera de %s: %s' % (motivo, rel))
        if vendido:
            # Codigo de terceros tal cual: sus cabeceras de licencia, sus imagenes y sus datos de prueba no son
            # nuestros, y el desensamblado que traen es de su propio material (el kernel de Xbox, su recompilador).
            hashes[sha256(ruta)] = rel
            continue
        if ext in TEXTO or os.path.basename(ruta).lower().startswith('.git'):
            try:
                with open(ruta, encoding='utf-8') as f:
                    texto = f.read()
            except UnicodeDecodeError:
                problemas.append('archivo de texto que no es UTF-8: %s' % rel)
                texto = ''
            for patron, que in RUTAS_PERSONALES:
                if patron.search(texto):
                    problemas.append('%s: %s' % (que, rel))
            for m in CORREO.finditer(texto):
                if not m.group(0).lower().endswith(('.png', '.jpg', '.wad', '.exe')):
                    problemas.append('correo "%s": %s' % (m.group(0), rel))
            for patron, que in CLAVES:
                if patron.search(texto):
                    problemas.append('%s: %s' % (que, rel))
            for numero, linea in enumerate(texto.splitlines(), 1):
                if listado_powerpc(linea):
                    problemas.append('comentario con listado PowerPC en %s:%d' % (rel, numero))
                    powerpc += 1
            # Los SHA256 de los archivos del juego se publican en install/games/*.toml y en la tabla del README.
            if not rel.endswith('.toml') and rel != 'README.md':
                # Una huella (SHA256 de una funcion del juego, que se cita con su nombre) es aceptable; una cadena
                # hexadecimal larga sin explicacion, no.
                for linea in texto.splitlines():
                    if not HEX_LARGO.search(linea):
                        continue
                    if re.search(r'(?i)sha-?256|hash|huella|fnv|crc', linea):
                        continue
                    problemas.append('cadena hexadecimal larga (%s...) fuera de un JSON: %s'
                                     % (HEX_LARGO.search(linea).group(0)[:12], rel))
        hashes[sha256(ruta)] = rel

    refs = a.ref or referencias(repo)
    comparados = 0
    for carpeta in refs:
        if os.path.abspath(carpeta) == repo:
            continue
        for base, _, files in os.walk(carpeta):
            for nombre in files:
                ruta = os.path.join(base, nombre)
                h = sha256(ruta)
                comparados += 1
                if h in hashes:
                    problemas.append('mismo SHA256 que %s: %s' % (os.path.join(base, nombre), hashes[h]))
    for ruta in sueltos(repo):
        h = sha256(ruta)
        comparados += 1
        if h in hashes:
            problemas.append('mismo SHA256 que %s: %s' % (ruta, hashes[h]))

    total = sum(os.path.getsize(r) for r in archivos)
    if not a.quiet:
        print('check_clean: %s' % repo)
        print('  %d archivos, %.2f MB' % (len(archivos), total / (1 << 20)))
        print('  %d archivos de referencia comparados por SHA256 (%d carpetas)' % (comparados, len(refs)))
        print('  %d comentarios con listado PowerPC en el codigo del port' % powerpc)
    if problemas:
        print('')
        print('%d PROBLEMA(S):' % len(problemas))
        for p in problemas:
            print('  - %s' % p)
        return 1
    print('  limpio: no hay datos del juego, ni codigo generado, ni rutas personales')
    return 0


if __name__ == '__main__':
    sys.exit(main())
