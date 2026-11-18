#!/usr/bin/env python3
"""Instalador del port de Magic 2014 (Xbox 360 XBLA, titulo 584112C5) para la Nintendo Switch.

Junta TUS archivos del juego (comprados) con el codigo de este repositorio y deja una carpeta lista para copiar a
la SD de la consola. No redistribuye nada del juego: los datos salen de tu copia y solo se usan en tu equipo.

    py -3 install/install.py --game mtg14 --data <carpeta del juego> [--dlc <carpeta>] --out <carpeta>
        [--tu <carpeta del Title Update>] [--icon <imagen.jpg>] [--thirdparty <carpeta>]

    py -3 install/install.py --game mtg14 --data ... --out ... --dry-run    # solo ensena los pasos

Pasos (cada uno imprime lo que hace; --dry-run ensena el comando en vez de ejecutarlo):
    1. comprobar herramientas      python, cmake, ninja, clang, devkitPro, Pillow, numpy, xxhash
    2. comprobar archivos          SHA256 de default.xex/.xexp, los WAD, los mazos, el Title Update y los DLC
    3. preparar el arbol           copia los datos a <work>/assets/game_root (fuera del repositorio)
    4. iconos                      variantes de botones PlayStation y Switch (tools/mtg14_iconos.py)
    5. lua                         los menus: se sacan de los WAD del usuario y se parchean aqui (install/mtg14_lua.py)
    6. shaders                     los contenedores del juego para el cache de Renut y deko3d_glsl.bin
    7. paquete de datos            game_root.nxpack + game_root.nxidx (tools/build_asset_pack.py)
    8. codigo generado             ReXGlue sobre tu default.xex (el generador se compila del SDK)
    9. NRO                         cmake + Ninja con devkitA64 (icono: --icon; sin el, el NRO va sin icono)
   10. carpeta final               <out>/switch/mtg14-nx/, lista para sdmc:/switch/

El SDK de ReXGlue (rama del port) va en sdk/; sus terceros grandes se bajan con install/fetch_thirdparty.py. Las
dependencias de app/thirdparty no estan en este repositorio por tamano: se piden con --thirdparty. Ver README.md y
docs/BUILD.md. El icono del NRO es una imagen tuya: no viaja en el repositorio.
"""
import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # publico/
INSTALL_DIR = os.path.dirname(os.path.abspath(__file__))
GAMES_DIR = os.path.join(INSTALL_DIR, 'games')
SDK_DIR = os.path.join(REPO, 'sdk')

# Los terceros grandes del SDK: cada uno tiene su repositorio y se baja con install/fetch_thirdparty.py.
TERCEROS_GRANDES = ('FFmpeg', 'simde', 'sdl3', 'vulkan-headers', 'glslang', 'spirv-tools', 'tracy', 'vulkan-loader',
                    'catch2', 'imgui', 'xxHash', 'moltenvk', 'tomlplusplus', 'spirv-headers',
                    'vulkan-memory-allocator', 'fmt', 'inja')


class InstallError(Exception):
    pass


def log(msg):
    print(msg, flush=True)


def head(n, total, title):
    log('')
    log('[%d/%d] %s' % (n, total, title))


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        while True:
            piece = f.read(1 << 20)
            if not piece:
                break
            h.update(piece)
    return h.hexdigest()


def human(n):
    for unit in ('B', 'KB', 'MB', 'GB'):
        if n < 1024 or unit == 'GB':
            return ('%d %s' % (n, unit)) if unit == 'B' else ('%.1f %s' % (n, unit))
        n /= 1024.0


def run(cmd, cwd=None, env=None, dry=False, what=None):
    """Ejecuta un comando (o lo ensena, con --dry-run)."""
    texto = ' '.join('"%s"' % c if ' ' in c else c for c in cmd)
    log('    $ %s%s' % (texto, ('   (%s)' % cwd) if cwd else ''))
    if dry:
        return 0
    entorno = dict(os.environ)
    if env:
        entorno.update(env)
    p = subprocess.run(cmd, cwd=cwd, env=entorno)
    if p.returncode != 0 and what:
        raise InstallError('%s fallo (codigo %d); mira la salida de arriba' % (what, p.returncode))
    return p.returncode


def tool(name, extra_paths=()):
    """Ruta de una herramienta del PATH (o de las carpetas indicadas)."""
    p = shutil.which(name)
    if p:
        return p
    for carpeta in extra_paths:
        for ext in ('', '.exe', '.bat'):
            c = os.path.join(carpeta, name + ext)
            if os.path.isfile(c):
                return c
    return None


# ----------------------------------------------------------------------------- leer install/games/<juego>.toml

def _valor(texto, donde):
    """Un valor del TOML reducido que usan estos juegos: cadena, entero o lista de cadenas (en una linea)."""
    t = texto.strip()
    if not t:
        raise InstallError('%s: falta el valor' % donde)
    if t[0] == '"':
        if len(t) < 2 or t[-1] != '"' or '"' in t[1:-1]:
            raise InstallError('%s: cadena mal cerrada: %s' % (donde, t))
        return t[1:-1]
    if t[0] == '[':
        if len(t) < 2 or t[-1] != ']':
            raise InstallError('%s: lista mal cerrada: %s' % (donde, t))
        dentro = t[1:-1].strip()
        if not dentro:
            return []
        salida = []
        for parte in dentro.split(','):
            parte = parte.strip()
            if len(parte) < 2 or parte[0] != '"' or parte[-1] != '"':
                raise InstallError('%s: en la lista solo van cadenas: %s' % (donde, parte))
            salida.append(parte[1:-1])
        return salida
    try:
        return int(t)
    except ValueError:
        raise InstallError('%s: valor no reconocido: %s' % (donde, t))


def cargar_juego(game_id):
    """El <juego>.toml de install/games como diccionario: claves sueltas y tablas [[required]]/[[dlc]]/[[lua]]..."""
    path = os.path.join(GAMES_DIR, game_id + '.toml')
    if not os.path.isfile(path):
        disponibles = [os.path.splitext(f)[0] for f in os.listdir(GAMES_DIR) if f.endswith('.toml')]
        raise InstallError('no conozco el juego "%s"; hay: %s' % (game_id, ', '.join(sorted(disponibles))))
    juego = {}
    tabla = None
    with open(path, encoding='utf-8') as f:
        for numero, linea in enumerate(f, 1):
            limpia = linea.split('#', 1)[0].strip()
            if not limpia:
                continue
            if limpia.startswith('[[') and limpia.endswith(']]'):
                nombre = limpia[2:-2].strip()
                tabla = {}
                juego.setdefault(nombre, []).append(tabla)
                continue
            if limpia.startswith('[') and limpia.endswith(']'):
                raise InstallError('%s:%d: solo se usan tablas [[...]]' % (path, numero))
            if '=' not in limpia:
                raise InstallError('%s:%d: se esperaba clave = valor' % (path, numero))
            clave, valor = limpia.split('=', 1)
            if tabla is None:
                juego[clave.strip()] = _valor(valor, '%s:%d' % (path, numero))
            else:
                tabla[clave.strip()] = _valor(valor, '%s:%d' % (path, numero))
    for obligatoria in ('id', 'nro', 'sd_folder', 'pack_name', 'required', 'lua'):
        if obligatoria not in juego:
            raise InstallError('%s no dice "%s"' % (path, obligatoria))
    return juego


def devkitpro():
    """La raiz de devkitPro en este equipo. El instalador de devkitPro deja DEVKITPRO con la ruta de MSYS
    (/opt/devkitpro), que en Windows no sirve para CMake: se ignora y se usa la carpeta normal."""
    for candidato in (os.environ.get('MTG14_DEVKITPRO'), os.environ.get('DEVKITPRO'), r'C:/devkitPro'):
        if candidato and os.path.isdir(candidato):
            return candidato
    return None


# ----------------------------------------------------------------------------- 1. herramientas

def step_tools(args, juego):
    """Comprueba lo que hace falta. Devuelve {nombre: ruta o None} y la lista de problemas."""
    faltan = []
    hay = {}
    hay['python'] = sys.executable
    extra = []
    vs = os.environ.get('MTG14_VSDIR', r'C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools')
    extra += [os.path.join(vs, 'Common7', 'IDE', 'CommonExtensions', 'Microsoft', 'CMake', 'CMake', 'bin'),
              os.path.join(vs, 'Common7', 'IDE', 'CommonExtensions', 'Microsoft', 'CMake', 'Ninja')]
    devkit = devkitpro()
    for nombre in ('cmake', 'ninja'):
        hay[nombre] = tool(nombre, extra)
        if not hay[nombre]:
            faltan.append('%s: instala los "Visual Studio 2022 Build Tools" (traen CMake y Ninja) y arranca desde '
                          'una consola que los tenga en el PATH' % nombre)
    hay['clang'] = tool('clang', ['C:/Program Files/LLVM/bin'])
    if not hay['clang']:
        faltan.append('clang: el generador de codigo se compila con clang; instala LLVM en el PATH')
    hay['git'] = tool('git')
    # devkitPro (devkitA64 + libnx + deko3d)
    if os.path.isdir(devkit):
        hay['devkitpro'] = devkit
        for sub in ('devkitA64/bin/aarch64-none-elf-g++.exe', 'libnx/lib'):
            if not os.path.exists(os.path.join(devkit, sub.replace('/', os.sep))):
                faltan.append('devkitPro en %s no tiene %s: instala devkitA64 y libnx con devkitProUpdater' %
                              (devkit, sub))
    else:
        hay['devkitpro'] = None
        faltan.append('devkitPro: instalalo de https://devkitpro.org (paquetes switch-dev: devkitA64, libnx, '
                      'deko3d) o dime su ruta con la variable DEVKITPRO')
    # modulos de Python que usan las herramientas
    for modulo, pista in (('PIL', 'Pillow (py -m pip install Pillow)'),
                          ('numpy', 'numpy (py -m pip install numpy)'),
                          ('xxhash', 'xxhash (py -m pip install xxhash)')):
        try:
            __import__(modulo)
            hay[modulo] = True
        except ImportError:
            hay[modulo] = None
            faltan.append('modulo de Python %s: %s' % (modulo, pista))
    if not args.sdk:
        faltan.append('el SDK de ReXGlue: no hay sdk/ en el repositorio; pasalo con --sdk <carpeta> (ver README)')
    elif not os.path.isfile(os.path.join(args.sdk, 'CMakeLists.txt')):
        faltan.append('--sdk %s no parece un arbol del SDK (falta CMakeLists.txt)' % args.sdk)
    else:
        hay['sdk'] = args.sdk
        sin_terceros = [n for n in TERCEROS_GRANDES
                        if not os.path.isdir(os.path.join(args.sdk, 'thirdparty', n))]
        if sin_terceros:
            faltan.append('los terceros del SDK que faltan en %s (%s): bajalos con "py -3 install/fetch_thirdparty.py"'
                          % (os.path.join(args.sdk, 'thirdparty'), ', '.join(sin_terceros)))
    if not args.thirdparty:
        faltan.append('--thirdparty <carpeta con plume, uam, imgui y reblue-XenosRecomp> (ver THIRD_PARTY.md)')
    elif not os.path.isdir(args.thirdparty):
        faltan.append('--thirdparty %s no existe' % args.thirdparty)
    return hay, faltan


# ----------------------------------------------------------------------------- 2. archivos

def step_verify(args, juego):
    """SHA256 de todo lo que hay que aportar. Un archivo distinto o que falta para la instalacion."""
    problemas = []
    vistos = {}
    # --xex / --xexp mandan sobre lo que haya en --data (el usuario puede tenerlos sueltos).
    sueltos = {}
    for nombre, ruta in (('default.xex', args.xex), ('default.xexp', args.xexp)):
        if ruta:
            sueltos[nombre] = os.path.abspath(ruta)

    def comprueba(entrada, carpeta, tipo):
        nombre = entrada['file']
        ruta = sueltos.get(nombre) or os.path.join(carpeta, nombre)
        if not os.path.isfile(ruta):
            problemas.append('falta %s (%s) en %s' % (nombre, entrada.get('info', ''), carpeta))
            return None
        tam = os.path.getsize(ruta)
        if tam != entrada['size']:
            problemas.append('%s: %s bytes, se esperaban %d (%s)' % (nombre, tam, entrada['size'],
                                                                     entrada.get('info', '')))
            return None
        h = sha256(ruta)
        if h != entrada['sha256']:
            problemas.append('%s: SHA256 %s, se esperaba %s (%s). ¿Es la version %s?' %
                             (nombre, h[:16] + '...', entrada['sha256'][:16] + '...', entrada.get('info', ''), tipo))
            return None
        log('    OK  %-58s %s' % (nombre, human(tam)))
        vistos[nombre] = ruta
        return ruta

    log('  datos del juego (--data):')
    for entrada in juego['required']:
        comprueba(entrada, args.data, 'base')
    # --tu puede ser la carpeta o el propio paquete del Title Update.
    carpeta_tu = args.tu
    if carpeta_tu and os.path.isfile(carpeta_tu):
        carpeta_tu = os.path.dirname(os.path.abspath(carpeta_tu))
    if carpeta_tu and os.path.isdir(carpeta_tu):
        log('  Title Update (--tu):')
        for entrada in juego.get('optional', []):
            comprueba(entrada, carpeta_tu, 'Title Update')
    elif juego.get('optional'):
        log('    (sin --tu: no se comprueba el paquete del Title Update que trae default.xexp y los Update_Data_*.WAD)')
    if args.dlc:
        log('  contenido descargable (--dlc):')
        for entrada in juego.get('dlc', []):
            ruta = comprueba(entrada, args.dlc, 'DLC')
            if ruta:
                vistos[entrada['file']] = ruta
    for p in problemas:
        log('    !! ' + p)
    if problemas:
        raise InstallError('%d archivo(s) no coinciden: no se instala nada' % len(problemas))
    return vistos


# ----------------------------------------------------------------------------- 3. arbol de trabajo

def step_stage(args, juego, archivos):
    """Copia los datos a <work>/assets/game_root y el codigo del port a <work>/app y <work>/tools."""
    work = args.work
    if not os.path.isdir(args.data):
        raise InstallError('--data %s no existe' % args.data)
    if args.dry_run:
        log('    $ copiar %s -> %s (sin las variantes mtg14_buttons_*)' % (args.data,
                                                                           os.path.join(work, 'assets',
                                                                                        'game_root')))
        log('    $ copiar %s/app y %s/tools -> %s' % (REPO, REPO, work))
        log('    $ enlazar %s -> %s/app/thirdparty' % (args.thirdparty or '<--thirdparty>', work))
        return work
    for sub in ('assets/game_root', 'app', 'tools', 'out'):
        os.makedirs(os.path.join(work, sub), exist_ok=True)
    go = os.path.join(work, 'assets', 'game_root')
    copiados = 0
    for nombre in sorted(os.listdir(args.data)):
        origen = os.path.join(args.data, nombre)
        if os.path.isfile(origen):
            # Las variantes de iconos se generan aqui: no se copian las de otra instalacion.
            if nombre.startswith('mtg14_buttons_'):
                continue
            shutil.copy2(origen, os.path.join(go, nombre))
            copiados += 1
        elif os.path.isdir(origen):
            if nombre.lower() in ('cache', 'logs'):
                continue
            shutil.copytree(origen, os.path.join(go, nombre), dirs_exist_ok=True)
            copiados += 1
    for nombre, ruta in (('default.xex', args.xex), ('default.xexp', args.xexp)):
        if ruta:
            shutil.copy2(os.path.abspath(ruta), os.path.join(go, nombre))
    log('    %d entradas de %s -> %s (%s)' % (copiados, args.data, go,
                                              human(sum(os.path.getsize(os.path.join(r, f))
                                                        for r, _, fs in os.walk(go) for f in fs))))
    # Codigo del port: la app y las herramientas (rutas relativas de sus cmake: ../assets, ../out).
    for nombre in ('app', 'tools'):
        destino = os.path.join(work, nombre)
        if os.path.isdir(destino):
            shutil.rmtree(destino)
        shutil.copytree(os.path.join(REPO, nombre), destino)
    log('    app/ y tools/ copiados en %s' % work)
    # thirdparty (plume, uam, imgui, reblue-XenosRecomp): se enlaza si se puede y se copia si no.
    tp = os.path.join(work, 'app', 'thirdparty')
    if os.path.isdir(tp):
        shutil.rmtree(tp)
    if not enlaza(args.thirdparty, tp):
        log('    copiando thirdparty (puede tardar: son cientos de MB)')
        shutil.copytree(args.thirdparty, tp)
    # El icono del NRO es del usuario: se deja donde el CMake lo busca (out/icon.jpg) antes de configurar.
    if args.icon:
        if not os.path.isfile(args.icon):
            raise InstallError('--icon %s no existe' % args.icon)
        os.makedirs(os.path.join(work, 'out'), exist_ok=True)
        shutil.copy2(os.path.abspath(args.icon), os.path.join(work, 'out', 'icon.jpg'))
        log('    icono del NRO: %s' % args.icon)
    return work


def enlaza(origen, destino):
    """Un enlace de directorio si el sistema lo permite (Windows: junction). True si quedo hecho."""
    try:
        subprocess.run(['cmd', '/c', 'mklink', '/J', destino, origen], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception:
        try:
            os.symlink(origen, destino, target_is_directory=True)
            return True
        except Exception:
            return False


# ----------------------------------------------------------------------------- 4. iconos

def step_icons(args, juego, work):
    go = os.path.join(work, 'assets', 'game_root')
    if args.skip_icons:
        log('    (saltado por --skip-icons: el juego usara los iconos de Xbox)')
        return
    run([sys.executable, os.path.join('tools', 'mtg14_iconos.py'), '--data', go, '--out', go],
        cwd=work, dry=args.dry_run, what='los iconos')
    for estilo in ('ps', 'switch'):
        p = os.path.join(go, 'mtg14_buttons_%s.bin' % estilo)
        if not args.dry_run and not os.path.isfile(p):
            raise InstallError('no se creo %s' % p)


# ----------------------------------------------------------------------------- 5. lua

def step_lua(args, juego, work):
    """Los menus, generados aqui a partir de los .LOB del WAD del usuario.

    Cada entrada de `lua` en el TOML dice su WAD, la ruta dentro del WAD, la operacion de install/mtg14_lua.py y el
    nombre del fichero de salida. Nada de esto viaja en el repositorio: el bytecode del juego es del usuario y las
    operaciones son nuestras.
    """
    if not juego.get('lua'):
        return
    destino = os.path.join(work, 'out', 'lua')
    base = os.path.join(work, 'assets', 'game_root')
    if args.dry_run:
        for entrada in juego['lua']:
            log('    $ sacar %s de %s y aplicarle "%s" -> out/lua/%s'
                % (entrada['entry'], entrada['wad'], entrada['clase'], entrada['out']))
        return
    sys.path.insert(0, INSTALL_DIR)
    import mtg14_lua  # noqa: E402
    try:
        hechos = mtg14_lua.generar(base, juego['lua'], destino)
    except mtg14_lua.ErrorLua as e:
        raise InstallError('los menus: %s' % e)
    por_nombre = {entrada['out']: entrada for entrada in juego['lua']}
    for nombre, tam in hechos:
        entrada = por_nombre[nombre]
        log('    %-46s %s  %s' % (nombre, human(tam), entrada.get('info', '')))
        if entrada.get('sha256'):
            h = sha256(os.path.join(destino, nombre))
            if h != entrada['sha256']:
                log('    (aviso) el SHA256 no es el del fichero probado en consola (%s... en vez de %s...): tu '
                    'copia del juego puede ser otra version' % (h[:12], entrada['sha256'][:12]))


# ----------------------------------------------------------------------------- 6. shaders

def step_shaders(args, juego, work):
    go = os.path.join(work, 'assets', 'game_root')
    dump = os.path.join(work, 'out', 'renut_shader_dump')
    wads = [os.path.join(go, nombre) for nombre in juego.get('shader_wads', [])]
    run([sys.executable, os.path.join('tools', 'shaders_wad.py')] + wads + ['--out', dump],
        cwd=work, dry=args.dry_run, what='los shaders del juego')
    if args.skip_shaders:
        log('    (--skip-shaders: el NRO se queda sin los shaders del juego y avisa al arrancar)')
        return
    glsl = os.path.join(work, 'out', 'deko3d_shaders', 'glsl_opt')
    xenos = os.path.join(work, 'out', 'pc', 'xenos_recomp', 'build', 'XenosRecomp', 'XenosRecomp.exe')
    if not args.dry_run:
        faltan = [n for n, p in (('XenosRecomp', xenos),
                                 ('spirv-cross', os.path.join(work, 'out', 'deko3d_tools', 'spirv-cross-build',
                                                              'spirv-cross.exe')),
                                 ('uam', os.path.join(work, 'out', 'deko3d_tools', 'uam-build', 'uam.exe')))
                  if not os.path.isfile(p)]
        if faltan:
            raise InstallError(
                'faltan las herramientas de PC para los shaders: %s. Se compilan una vez con '
                'tools/deko3d_build_tools.sh (spirv-cross y uam) y el arbol de PC de Renut (XenosRecomp); '
                'ver docs/BUILD.md, paso 3. Si no las quieres ahora: --skip-shaders.' % ', '.join(faltan))
    run([xenos, dump, os.path.join(work, 'out', 'deko3d_shaders', 'scratch_cache.cpp'),
         os.path.join('app', 'thirdparty', 'reblue-XenosRecomp', 'XenosRecomp', 'shader_common.h')],
        cwd=work, dry=args.dry_run, what='XenosRecomp',
        env={'MTG14_DEKO3D_SPIRV_DIR': os.path.join(work, 'out', 'deko3d_shaders', 'spirv')})
    run([sys.executable, os.path.join('tools', 'deko3d_shaders.py'), '--spirv',
         os.path.join(work, 'out', 'deko3d_shaders', 'spirv'), '--out', os.path.join(work, 'out', 'deko3d_shaders'),
         '--jobs', str(args.jobs)], cwd=work, dry=args.dry_run, what='deko3d_shaders.py')
    run([sys.executable, os.path.join('tools', 'deko3d_glsl_opt.py'), '--in',
         os.path.join(work, 'out', 'deko3d_shaders', 'glsl'), '--out', glsl, '--check'],
        cwd=work, dry=args.dry_run, what='deko3d_glsl_opt.py')
    run([sys.executable, os.path.join('tools', 'deko3d_shader_package.py'), '--glsl', glsl, '--out',
         os.path.join(work, 'out', 'renut_switch')], cwd=work, dry=args.dry_run, what='deko3d_shader_package.py')
    run([sys.executable, os.path.join('tools', 'renut_switch_shader_cache.py'), '--pc',
         os.path.join(work, 'out', 'pc')], cwd=work, dry=args.dry_run, what='renut_switch_shader_cache.py')
    run([sys.executable, os.path.join('tools', 'renut_release_shaders.py'), '--glsl', glsl],
        cwd=work, dry=args.dry_run, what='renut_release_shaders.py')


# ----------------------------------------------------------------------------- 7. paquete

def step_pack(args, juego, work):
    go = os.path.join(work, 'assets', 'game_root')
    run([sys.executable, os.path.join('tools', 'build_asset_pack.py'), go, '--out-dir',
         os.path.join(work, 'out', 'pack'), '--verify'], cwd=work, dry=args.dry_run, what='el paquete de datos')


# ----------------------------------------------------------------------------- 8. codigo generado

def step_codegen(args, juego, work):
    if not args.sdk and not args.dry_run:
        raise InstallError('falta --sdk (arbol del SDK de ReXGlue del port)')
    sdk = os.path.abspath(args.sdk) if args.sdk else '<--sdk>'
    host = os.path.join(work, 'out', 'host')
    rexglue = os.path.join(host, 'rexglue.exe')
    if args.dry_run or not os.path.isfile(rexglue):
        cmake = shutil.which('cmake') or 'cmake'
        run([cmake, '-S', sdk, '-B', host, '-G', 'Ninja', '-DCMAKE_BUILD_TYPE=Release',
             '-DCMAKE_C_COMPILER=clang', '-DCMAKE_CXX_COMPILER=clang++',
             '-DCMAKE_C_FLAGS=-march=x86-64-v2', '-DCMAKE_CXX_FLAGS=-march=x86-64-v2'],
            dry=args.dry_run, what='la configuracion del generador')
        run([cmake, '--build', host, '--target', 'rexglue', '-j', str(args.jobs)],
            dry=args.dry_run, what='la compilacion del generador')
        log('    (el generador se queda en %s)' % host)
    env = {}
    for par in juego.get('codegen_env', []):
        clave, valor = par.split('=', 1)
        env[clave] = valor
    env['REXGLUE_DUMP_IMAGE'] = os.path.join(work, 'out', 'default_image.bin')
    app = os.path.join(work, 'app')
    run([rexglue, 'codegen', juego['codegen_manifest']], cwd=app, env=env, dry=args.dry_run,
        what='el generador de codigo')
    if not args.dry_run:
        perfil = os.path.join(app, 'generated', 'codegen_profile.txt')
        os.makedirs(os.path.dirname(perfil), exist_ok=True)
        with open(perfil, 'w', encoding='ascii') as f:
            f.write(juego['codegen_profile'])


# ----------------------------------------------------------------------------- 9. NRO

def step_build(args, juego, work):
    devkit = devkitpro() or 'C:/devkitPro'
    cmake = shutil.which('cmake') or 'cmake'
    sdk = os.path.abspath(args.sdk) if args.sdk else '<--sdk>'
    toolchain = os.path.join(work, 'tools', 'switch', 'cmake', 'switch-devkitA64.cmake')
    bdir = os.path.join(work, 'out', 'nx')
    cmd = [cmake, '-S', os.path.join(work, 'app'), '-B', bdir, '-G', 'Ninja',
           '-DCMAKE_BUILD_TYPE=Release',
           '-DCMAKE_TOOLCHAIN_FILE=%s' % toolchain,
           '-DREXSDK_DIR=%s' % sdk,
           '-DMTG14_NATIVE_RENDERER=OFF',
           '-DMTG14_RENUT_RENDERER=ON',
           '-DMTG14_RENUT_PORT_SHADERS=OFF',
           '-DMTG14_SWITCH_LTO=%s' % ('ON' if args.lto else 'OFF'),
           '-DPython3_EXECUTABLE=%s' % sys.executable]
    if args.nvk_sdk:
        cmd.append('-DREXGLUE_SWITCH_NVK_SDK=%s' % os.path.abspath(args.nvk_sdk))
    run(cmd, cwd=work, env={'DEVKITPRO': devkit}, dry=args.dry_run, what='la configuracion del NRO')
    run([cmake, '--build', bdir, '-j', str(args.jobs)], cwd=work, env={'DEVKITPRO': devkit}, dry=args.dry_run,
        what='la compilacion del NRO')


# ----------------------------------------------------------------------------- 10. carpeta final

def step_package(args, juego, work):
    final = os.path.join(args.out, 'switch', juego['sd_folder'])
    if not args.dry_run:
        os.makedirs(os.path.join(final, 'lua'), exist_ok=True)
    copiado = []

    def pon(origen, nombre, obligatorio=True):
        if args.dry_run:
            log('    $ %s -> %s' % (origen, nombre))
            return
        if not os.path.isfile(origen):
            if obligatorio:
                raise InstallError('no existe %s (paso anterior sin terminar)' % origen)
            log('    (aviso) falta %s: no se copia %s' % (origen, nombre))
            return
        shutil.copy2(origen, os.path.join(final, nombre))
        copiado.append((nombre, os.path.getsize(origen)))

    pon(os.path.join(work, 'out', 'nx', juego['nro']), juego['nro'])
    pon(os.path.join(work, 'out', 'pack', juego['pack_name'] + '.nxpack'), juego['pack_name'] + '.nxpack')
    pon(os.path.join(work, 'out', 'pack', juego['pack_name'] + '.nxidx'), juego['pack_name'] + '.nxidx')
    pon(os.path.join(work, 'out', 'renut_switch_release', 'sd', 'deko3d_glsl.bin'), 'deko3d_glsl.bin',
        obligatorio=not args.skip_shaders)
    lua_out = os.path.join(work, 'out', 'lua')
    if os.path.isdir(lua_out):
        for nombre in sorted(os.listdir(lua_out)):
            if nombre.endswith(('.lua', '.luac')):
                if not args.dry_run:
                    shutil.copy2(os.path.join(lua_out, nombre), os.path.join(final, 'lua', nombre))
                    copiado.append(('lua/' + nombre, os.path.getsize(os.path.join(lua_out, nombre))))
    if args.dlc:
        os.makedirs(os.path.join(final, 'dlc'), exist_ok=True)
        for entrada in juego.get('dlc', []):
            origen = os.path.join(args.dlc, entrada['file'])
            if args.dry_run:
                log('    $ %s -> dlc/%s' % (origen, entrada['file']))
            elif os.path.isfile(origen):
                shutil.copy2(origen, os.path.join(final, 'dlc', entrada['file']))
                copiado.append(('dlc/' + entrada['file'], os.path.getsize(origen)))
    log('')
    log('  carpeta para la SD: %s' % final)
    for nombre, tam in copiado:
        log('    %-64s %s' % (nombre, human(tam)))
    if not args.dry_run:
        # La tabla de SHA256, para comprobar la copia a la consola sin volver a calcularla.
        tabla = os.path.join(args.out, 'switch', 'SHA256_%s.txt' % juego['sd_folder'])
        with open(tabla, 'w', encoding='ascii', newline='\n') as f:
            for base, _, ficheros in os.walk(final):
                for nombre in sorted(ficheros):
                    ruta = os.path.join(base, nombre)
                    rel = './' + os.path.relpath(ruta, final).replace(os.sep, '/')
                    f.write('%s *%s\n' % (sha256(ruta), rel))
        log('')
        log('  SHA256 de la carpeta: %s' % tabla)
    log('')
    log('  Copia ESA carpeta a sdmc:/switch/ de la consola (arrastrando desde el PC, o con Hekate/MTP),')
    log('  y en la consola arranca el NRO con takeover (manten R al abrir un juego, luego el Homebrew Menu):')
    log('  desde el Album no tiene memoria suficiente. La primera vez el juego escribe sus ajustes')
    log('  (%s.toml) al lado del NRO.' % juego['id'])
    return final


# ----------------------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--game', default='mtg14', help='juego a instalar (install/games/<juego>.toml); por defecto mtg14')
    ap.add_argument('--xex', help='default.xex de tu copia (normalmente ya esta en --data)')
    ap.add_argument('--xexp', help='default.xexp del Title Update (normalmente ya esta en --data)')
    ap.add_argument('--data', required=True, help='carpeta con los datos del juego (default.xex, *.WAD)')
    ap.add_argument('--dlc', help='carpeta con los paquetes DLC comprados (opcional)')
    ap.add_argument('--tu', help='carpeta (o el propio paquete) del Title Update; opcional, solo para comprobar su SHA256')
    ap.add_argument('--icon', help='imagen del NRO (256x256 JPEG/PNG tuya); sin ella el NRO va sin icono')
    ap.add_argument('--out', required=True, help='carpeta donde dejar switch/<juego>-nx/')
    ap.add_argument('--work', help='carpeta de trabajo (por defecto <out>/../<juego>_build); fuera del repositorio')
    ap.add_argument('--sdk', help='arbol del SDK de ReXGlue (por defecto, sdk/ del repositorio)')
    ap.add_argument('--thirdparty', help='carpeta con plume, uam, imgui y reblue-XenosRecomp')
    ap.add_argument('--nvk-sdk', help='portlibs/switch de la Mesa (solo si se enlaza NVK; no hace falta)')
    ap.add_argument('--jobs', type=int, default=os.cpu_count() or 8, help='trabajos en paralelo (por defecto: CPUs)')
    ap.add_argument('--lto', action='store_true', help='enlace con LTO (mas lento; el NRO definitivo lo usa)')
    ap.add_argument('--skip-icons', action='store_true', help='no crear las variantes de iconos')
    ap.add_argument('--skip-shaders', action='store_true', help='no traducir los shaders del juego')
    ap.add_argument('--dry-run', action='store_true', help='ensenar los pasos sin ejecutar nada')
    args = ap.parse_args()

    args.data = os.path.abspath(args.data)
    args.out = os.path.abspath(args.out)
    args.work = os.path.abspath(args.work or os.path.join(os.path.dirname(args.out), args.game + '_build'))
    args.sdk = os.path.abspath(args.sdk) if args.sdk else (SDK_DIR if os.path.isdir(SDK_DIR) else None)
    args.thirdparty = os.path.abspath(args.thirdparty) if args.thirdparty else None
    t0 = time.time()
    log('instalador de %s (%s)' % (args.game, 'simulacion, nada se ejecuta' if args.dry_run else 'en serio'))
    log('  datos:  %s' % args.data)
    log('  salida: %s' % args.out)
    log('  trabajo: %s' % args.work)

    try:
        juego = cargar_juego(args.game)
        total = 10
        head(1, total, 'herramientas')
        hay, faltan = step_tools(args, juego)
        for nombre, p in sorted(hay.items()):
            if p:
                log('    OK  %s' % nombre)
        if faltan:
            log('')
            log('  Falta esto para poder instalar:')
            for f in faltan:
                log('    - %s' % f)
            if not args.dry_run:
                raise InstallError('faltan herramientas (arriba); no se toca nada')
            log('  (--dry-run: se ensenan los pasos igualmente)')
        head(2, total, 'archivos del juego')
        step_verify(args, juego)
        head(3, total, 'arbol de trabajo')
        step_stage(args, juego, None)
        head(4, total, 'iconos de botones')
        step_icons(args, juego, args.work)
        head(5, total, 'menus en Lua')
        step_lua(args, juego, args.work)
        head(6, total, 'shaders')
        step_shaders(args, juego, args.work)
        head(7, total, 'paquete de datos')
        step_pack(args, juego, args.work)
        head(8, total, 'codigo generado (ReXGlue)')
        step_codegen(args, juego, args.work)
        head(9, total, 'NRO')
        step_build(args, juego, args.work)
        head(10, total, 'carpeta final')
        final = step_package(args, juego, args.work)
    except InstallError as e:
        log('')
        log('ERROR: %s' % e)
        return 1
    except KeyboardInterrupt:
        log('')
        log('interrumpido')
        return 130
    log('')
    log('listo en %d s (%s)' % (time.time() - t0, final))
    return 0


if __name__ == '__main__':
    sys.exit(main())
