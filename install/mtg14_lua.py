#!/usr/bin/env python3
"""Los menus de Magic 2014, preparados EN LA INSTALACION a partir de los .LOB de TU copia del juego.

Magic 2014 guarda sus menus como bytecode Lua compilado (.LOB) dentro de sus WAD. Ese bytecode es del juego y NO
viaja en este repositorio: lo que viaja son las operaciones que hay que aplicarle (este archivo) y el Lua propio del
port que se anade encima. El resultado son los ficheros de `out/lua/`, que el cargador del port usa en lugar de los
del juego.

    py -3 -I install/mtg14_lua.py --data <carpeta del juego> --out <carpeta de salida> [--only <salida>]

Lo llama `install/install.py` (paso 5); cada entrada de `lua` en `install/games/mtg14.toml` dice su WAD, su ruta
dentro del WAD, que operacion se aplica y como se llama el fichero de salida.

Cuatro clases de fichero:

  menu / menu_layout / extras   bytecode del juego, con unas pocas instrucciones nuestras delante (ocultar filas) o
                                tres constantes cambiadas (colocar el menu).
  envoltorio                    texto Lua: el bytecode ORIGINAL como cadena, `loadstring`, quedarse en el entorno del
                                modulo, y encima el parche propio (idioma, iconos, DLC, una sola pulsacion, el anillo
                                de carga).
  layout_helper                 el mismo envoltorio, pero el bytecode que se mete como cadena es el del layout ya
                                retocado (los constructores del menu, para anadir filas).

Nada de esto se distribuye con el repositorio; se genera aqui, en tu equipo, a partir de tu copia comprada.
"""
import argparse
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.join(os.path.dirname(HERE), 'tools')
for _ruta in (HERE, TOOLS):
    if _ruta not in sys.path:
        sys.path.insert(0, _ruta)

import luadis  # noqa: E402  (tools/luadis.py)

# ----------------------------------------------------------------------------- nuestro Lua (lo unico que viaja)

# Idioma, iconos de botones y estado del DLC: lo comparten el script del menu de Configuracion y su layout.
COMMON = """
local languages={{code='en',name='English'},{code='es',name='Espa\\241ol'},
 {code='fr',name='Fran\\231ais'},{code='de',name='Deutsch'},{code='it',name='Italiano'},
 {code='ja',name='Nihongo'},{code='pt',name='Portugu\\234s'},{code='ko',name='Hangugeo'},{code='ru',name='Russkiy'}}
local styles={{code='xbox',name='Xbox'},{code='ps',name='PlayStation'},{code='switch',name='Nintendo Switch'}}
local function names(t) local n={} for i,v in ipairs(t) do n[i]=v.name end return n end
local function index(t,c) for i,v in ipairs(t) do if v.code==c then return i end end return 1 end
"""

# El script de Configuracion: se guarda su `reset` y se envuelve. No se toca lo que el juego ya hacia.
SETTINGS_TAIL = """
local original=assert(loadstring(%s))
original(...)
setfenv(1,getfenv(original))

local old_reset=reset
reset=function(menu)
 old_reset(menu)
 for _,key in ipairs({'metrics_opt_out','dynamic_loading_screens','dynamic_loading_screens_label','dynamic_loading_screens_frame'}) do
  if id[key] then
   local item=menu:get_item_by_id(id[key])
   if item then item:hide() end
  end
 end
 menu:send_item_message(14221,message.set_values,{value=index(languages,MTG14.idioma)})
 menu:send_item_message(14222,message.set_values,{value=index(styles,MTG14.estilo)})
 frontend:playMovie('mtg14:idioma='..MTG14.idioma,true)
 frontend:playMovie('mtg14:estilo='..MTG14.estilo,true)
end
on_event[14221]=function(menu,item,evt)
 if evt==event.value_change then
  local v=languages[tonumber(item.selected_option)]
  if v then MTG14.idioma=v.code; frontend:playMovie('mtg14:idioma='..v.code,true) end
 end
end
on_event[14222]=function(menu,item,evt)
 if evt==event.value_change then
  local v=styles[tonumber(item.selected_option)]
  if v then MTG14.estilo=v.code; frontend:playMovie('mtg14:estilo='..v.code,true) end
 end
end
local old_pop=on_pop
on_pop=function(menu)
 for _,setting in ipairs({{14221,languages,'idioma'},{14222,styles,'estilo'}}) do
  local item=menu:get_item_by_id(setting[1])
  local v=item and setting[2][tonumber(item.selected_option)]
  if v then frontend:playMovie('mtg14:'..setting[3]..'='..v.code,true) end
 end
 if old_pop then old_pop(menu) end
end
"""

# El layout de Configuracion: los constructores del juego se envuelven para anadir las filas propias y colocar las
# que ya tenia (la dificultad, las pistas y los consejos) sin que se solapen.
LAYOUT_HEAD = """
local saved={}
local function adjust(t,e)
 local tip=t.tool_tip or ''
 if t.y==-330 then t.y=-340 elseif t.y==-240 then t.y=-275 elseif t.y==-150 then t.y=-210
 elseif t.y==-60 or t.y==30 then t.y=-3000 end
 if string.find(tip,'METRICS') or string.find(tip,'DYNAMIC_LOADING') or t.id==107 then t.y=-3000 end
 if tip=='TT_SETTINGS_BASIC_DIFFICULTY' then t.y=-340 end
 if tip=='TT_SETTINGS_BASIC_HINTS' then t.y=-275 end
 if tip=='TT_SETTINGS_BASIC_TIPS' then t.y=-210 end
 if t.id==106 then t.y=240 end
 if t.id==212 then t.y=305 end
 if t.id==e.id.display_sealed_tutorial then t.y=370 end
 return t
end
local constructors={'content','options_frm','options_lbl','text','options_checkbox','button','dropdown'}
for _,n in ipairs(constructors) do
 local name=n
 saved[name]=_G['MTG14_'..name]
 _G['MTG14_'..name]=function(t)
  local e=getfenv(2)
  setfenv(1,e)
  if name=='content' then
   local insertion=11 -- after the original difficulty, hints and tips controls
   local function add(v) table.insert(t.items,insertion,v); insertion=insertion+1 end
   add(e.options_lbl{id=14211,x=-50,y=-145,w=500,text=MTG14.txt_idioma})
   add(e.dropdown{id=14221,group=1001,x=250,y=-145,w=300,h=70,options=names(languages),fixed_order=true})
   add(e.options_lbl{id=14212,x=-50,y=-80,w=500,text=MTG14.txt_botones})
   add(e.dropdown{id=14222,group=1001,x=250,y=-80,w=300,h=70,options=names(styles),fixed_order=true})
   add(e.options_lbl{id=14213,x=-50,y=-15,w=1000,text=MTG14.txt_dlc})
   for i,v in ipairs(MTG14.packs) do
    add(e.text{id=14230+i,x=-50,y=30+(i-1)*35,w=1050,h=35,font='general',text=v,alignment=e.text_alignment.left})
   end
   add(e.text{id=14214,x=-50,y=190,w=1050,h=40,font='general',text=MTG14.txt_reinicio,alignment=e.text_alignment.left})
  else adjust(t,e) end
  return e[name](t)
 end
end
"""
LAYOUT_TAIL = """
for _,n in ipairs(constructors) do _G['MTG14_'..n]=saved[n] end
if not ok then error(err) end
"""

# "Enciende tu chispa" pedia DOS pulsaciones: la primera asigna el mando y carga la partida, asi que cuando se
# comprueba el jugador todavia no es valido y la pulsacion se pierde. Se recuerda y se completa en cuanto lo es.
PRESS_START = '''
-- Port (2026-11-11): sin servidor no hay promociones: el menu principal (proto 0.19) ponia el rastro dorado
-- (show_golden_trail_id) en ADICIONALES cuando frontend:GetDoWeHaveALovelyAdvertToSee() decia que si.
pcall(function()
 if type(frontend) == 'table' then
  frontend.GetDoWeHaveALovelyAdvertToSee = function() return false end
 end
end)
-- Port (2026-11-11): una sola pulsacion basta en la pantalla de titulo.
-- OJO: player:IsPlayerValid() tiene efecto (con la pulsacion asigna el mando y carga la partida): se llama
-- solo despues de una pulsacion aceptada, como el original; llamarlo en cada evento dejaba el titulo sordo.
local original_on_input = on_input
local original_on_update = on_update
local original_run_game = run_game
local lanzado = false
local pendiente = false
local cuadros = 0
run_game = function(...)
 lanzado = true
 pendiente = false
 return original_run_game(...)
end
on_input = function(menu, ...)
 local r = original_on_input(menu, ...)
 if r and not lanzado and not pendiente then
  pendiente = true             -- pulsacion aceptada sin jugador todavia: se completa en on_update
  cuadros = 0
 end
 return r
end
on_update = function(menu, ...)
 if original_on_update then original_on_update(menu, ...) end
 if not pendiente then return end
 cuadros = cuadros + 1
 if cuadros % 15 ~= 0 then return end   -- cada ~0.25 s, como una pulsacion nueva
 local ok, valido = pcall(function() return player:IsPlayerValid() end)
 if ok and valido then
  run_game(menu)
 elseif cuadros > 600 then
  pendiente = false            -- ~10 s sin jugador: queda como el original (otra pulsacion)
 end
end
'''

# Al cargar el contenido descargable, el dialogo tapaba el menu y parecia congelado. Ahora se ve solo el anillo que
# gira (items 103 y 105), sin la caja ni el texto, y se cierra en cuanto termina (sin los cinco segundos minimos).
CONTENT_ENUMERATION = '''
-- Port (2026-11-11): mientras carga el contenido descargable se ve solo el anillo de carga.
local original_on_push = on_push
on_push = function(menu, ...)
 local r = original_on_push(menu, ...)
 for _, n in ipairs({ 101, 102 }) do
  pcall(function()
   local it = menu:get_item_by_id(n)
   if it then it:set_alpha(0) end
  end)
 end
 return r
end
local function solo_anillo(menu)
 menu.poll_for_enumeration = true
 menu:set_alpha(0)
 wait(0.5)
 if menu.allow_refresh then return end   -- ya termino: no se muestra nada
 menu.poll_for_enumeration = false
 menu:set_alpha(255)
 menu.allow_refresh = true                -- se cierra en cuanto termina la carga (on_refresh / on_update)
 menu:refresh()
end
show_for_atleast_five_seconds = solo_anillo
pcall(function()
 local items = _LUBEMENU and _LUBEMENU.items
 if type(items) ~= 'table' then return end
 for i = 1, #items do
  local it = items[i]
  if type(it) == 'table' and it.id == 602 then it.timeline = solo_anillo end
 end
end)
'''

HEAD = '-- Generado por install/mtg14_lua.py a partir de %s. No editar a mano.\n'

# Filas del menu principal que no llevan a nada sin Xbox Live, logros ni tienda.
OCULTAS = ('MULTIPLAYER', 'LEADERBOARDS', 'ACHIEVEMENTS', 'DOWNLOADABLE_CONTENT', 'STORE')
# Botones de la barra que se ocultan en Adicionales (promociones y desbloqueos que no existen aqui).
OCULTAS_EXTRAS = ('PROMO_UNLOCK', 'PROMOTIONS')


class ErrorLua(Exception):
    pass


# ----------------------------------------------------------------------------- bytecode

def encode(f, e):
    """El cuerpo de una funcion Lua 5.1, tal como lo guarda el juego (sin los 12 bytes de cabecera)."""
    def numero(n):
        return struct.pack(e + 'i', n)

    def cadena(s):
        if s is None:
            return numero(0)
        b = s.encode('latin1') + b'\0'
        return numero(len(b)) + b

    b = cadena(f.source) + numero(f.linedefined) + numero(f.lastlinedefined)
    b += bytes([f.nups, f.numparams, f.is_vararg, f.maxstacksize])
    b += numero(len(f.code)) + b''.join(struct.pack(e + 'I', x) for x in f.code)
    b += numero(len(f.constants))
    for c in f.constants:
        if c is None:
            b += b'\0'
        elif isinstance(c, bool):
            b += bytes([1, int(c)])
        elif isinstance(c, (int, float)):
            b += b'\3' + struct.pack(e + 'd', c)
        else:
            b += b'\4' + cadena(c)
    b += numero(len(f.protos)) + b''.join(encode(p, e) for p in f.protos)
    b += numero(len(f.lineinfo)) + b''.join(numero(x) for x in f.lineinfo)
    b += numero(len(f.locvars)) + b''.join(cadena(n) + numero(a) + numero(z) for n, a, z in f.locvars)
    b += numero(len(f.upvalues)) + b''.join(cadena(s) for s in f.upvalues)
    return b


def endian(datos):
    return '<' if len(datos) > 6 and datos[6] else '>'


def literal(datos):
    """El bytecode como cadena Lua: cada byte, en decimal con tres cifras (nunca un salto de linea)."""
    return '"' + ''.join('\\%03d' % v for v in datos) + '"'


def cargar(datos, que):
    try:
        f = luadis.load(datos)
    except Exception as exc:
        raise ErrorLua('%s: no es bytecode Lua 5.1 (%s)' % (que, exc))
    if f.end != len(datos):
        raise ErrorLua('%s: el bytecode ocupa %d de %d bytes' % (que, f.end, len(datos)))
    return f


def instruccion(nombre, a, b=0, c=0):
    return luadis.OPNAMES.index(nombre) | (a << 6) | (c << 14) | (b << 23)


def instruccion_bx(nombre, a, bx):
    return luadis.OPNAMES.index(nombre) | (a << 6) | (bx << 14)


def constante(f, valor):
    if valor not in f.constants:
        f.constants.append(valor)
    return f.constants.index(valor)


def ocultar(f, items):
    """Las instrucciones que ya usa el juego para ocultar una fila, una vez por cada nombre."""
    palabras = []
    for item in items:
        palabras += [
            instruccion('SELF', 1, 0, 256 + constante(f, 'send_item_message')),
            instruccion_bx('GETGLOBAL', 3, constante(f, 'id')),
            instruccion('GETTABLE', 3, 3, 256 + constante(f, 'magno_list')),
            instruccion_bx('GETGLOBAL', 4, constante(f, 'message')),
            instruccion('GETTABLE', 4, 4, 256 + constante(f, 'set_values')),
            instruccion('NEWTABLE', 5, 0, 1),
            instruccion_bx('GETGLOBAL', 6, constante(f, 'id')),
            instruccion('GETTABLE', 6, 6, 256 + constante(f, item)),
            instruccion('SETTABLE', 5, 256 + constante(f, 'hide_item_id'), 6),
            instruccion('CALL', 1, 5, 1),
        ]
    if len(f.constants) >= 256:
        raise ErrorLua('demasiadas constantes para las filas que se ocultan')
    f.code = palabras + f.code
    f.maxstacksize = max(f.maxstacksize, 7)


# ----------------------------------------------------------------------------- cada clase de fichero

def menu_principal(datos):
    """El menu principal sin las filas que necesitan red, sin el cartel de promo y sin las filas de abajo."""
    f = cargar(datos, 'MAIN_MENU.LOB')
    if len(f.protos) < 19:
        raise ErrorLua('MAIN_MENU.LOB: se esperaban al menos 19 prototipos, hay %d' % len(f.protos))
    push = f.protos[16]
    for clave in ('hide_item_id', 'magno_list'):
        if clave not in push.constants:
            raise ErrorLua('MAIN_MENU.LOB: el prototipo 16 no tiene "%s"' % clave)
    ocultar(push, OCULTAS)
    banner = f.protos[18]
    if 'GetRandomAdvertBanner' not in banner.constants:
        raise ErrorLua('MAIN_MENU.LOB: el prototipo 18 no es el cartel de promociones')
    # Se queda la funcion y sus tablas de depuracion, pero salta directa al `return`.
    banner.code[0] = 22 | ((len(banner.code) - 2 + 131071) << 14)
    # Y las cuatro filas de la parte de abajo, ocultas igual que las de arriba.
    palabras = []
    for fila in (996, 997, 999, 1000):
        palabras += [
            instruccion('SELF', 1, 0, 256 + constante(push, 'send_item_message')),
            instruccion_bx('LOADK', 3, constante(push, fila)),
            instruccion_bx('GETGLOBAL', 4, constante(push, 'message')),
            instruccion('GETTABLE', 4, 4, 256 + constante(push, 'hide')),
            instruccion('CALL', 1, 4, 1),
        ]
    push.code = palabras + push.code
    push.maxstacksize = max(push.maxstacksize, 5)
    return datos[:12] + encode(f, endian(datos))


def menu_layout(datos):
    """El layout del menu principal: los tres textos que quedan fuera de pantalla se van del todo."""
    f = cargar(datos, 'MAIN_MENU_LAYOUT.LOB')
    for valor in (365.0, 446.0, 447.0):
        if valor not in f.constants:
            raise ErrorLua('MAIN_MENU_LAYOUT.LOB: no esta la constante %s' % valor)
        f.constants[f.constants.index(valor)] = -3000.0
    return datos[:12] + encode(f, endian(datos))


def extras(datos):
    """El menu de Adicionales sin las promociones ni los desbloqueos que no existen en este port."""
    f = cargar(datos, 'EXTRAS_MENU.LOB')
    if len(f.protos) < 7:
        raise ErrorLua('EXTRAS_MENU.LOB: se esperaban al menos 7 prototipos, hay %d' % len(f.protos))
    focus = f.protos[6]
    for clave in ('magno_list', 'PROMOTIONS'):
        if clave not in focus.constants:
            raise ErrorLua('EXTRAS_MENU.LOB: el prototipo 6 no tiene "%s"' % clave)
    palabras = []
    for item in OCULTAS_EXTRAS:
        palabras += [
            instruccion('SELF', 1, 0, 256 + constante(focus, 'send_item_message')),
            instruccion_bx('GETGLOBAL', 3, constante(focus, 'id')),
            instruccion('GETTABLE', 3, 3, 256 + constante(focus, 'magno_list')),
            instruccion_bx('GETGLOBAL', 4, constante(focus, 'message')),
            instruccion('GETTABLE', 4, 4, 256 + constante(focus, 'set_values')),
            instruccion('NEWTABLE', 5, 0, 1),
            instruccion_bx('GETGLOBAL', 6, constante(focus, 'id')),
            instruccion('GETTABLE', 6, 6, 256 + constante(focus, item)),
            instruccion('SETTABLE', 5, 256 + constante(focus, 'hide_item_id'), 6),
            instruccion('CALL', 1, 5, 1),
        ]
    if len(focus.constants) >= 256:
        raise ErrorLua('EXTRAS_MENU.LOB: demasiadas constantes en el prototipo 6')
    focus.code = palabras + focus.code
    focus.maxstacksize = max(focus.maxstacksize, 7)
    return datos[:12] + encode(f, endian(datos))


def envoltorio(datos, parche, nombre):
    return (HEAD % nombre) + '\nlocal original = assert(loadstring(' + literal(datos) + '))\n' \
        + 'original(...)\nsetfenv(1, getfenv(original))\n' + parche


def layout_helper(datos):
    """El layout de Configuracion: los constructores del juego se cambian por los nuestros dentro del bytecode."""
    f = cargar(datos, 'HELP_OPTIONS_BASIC_SETTINGS_LAYOUT.LOB')
    for nombre in ('content', 'options_frm', 'options_lbl', 'text', 'options_checkbox', 'button', 'dropdown'):
        if nombre not in f.constants:
            raise ErrorLua('HELP_OPTIONS_BASIC_SETTINGS_LAYOUT.LOB: no esta el constructor "%s"' % nombre)
        viejo = f.constants.index(nombre)
        nuevo = len(f.constants)
        f.constants.append('MTG14_' + nombre)
        # 'text' es a la vez un constructor y una propiedad de tabla: solo se cambia GETGLOBAL, nunca la clave.
        for pc, palabra in enumerate(f.code):
            if (palabra & 63) == 5 and (palabra >> 14) == viejo:
                f.code[pc] = (palabra & 0x3fff) | (nuevo << 14)
    retocado = datos[:12] + encode(f, endian(datos))
    return COMMON + LAYOUT_HEAD + '\nlocal original=assert(loadstring(' + literal(retocado) + '))\n' \
        + 'local ok,err=pcall(original,...)\n' + LAYOUT_TAIL


def configuracion(datos):
    return COMMON + SETTINGS_TAIL % literal(datos)


OPERACIONES = {
    'main_menu': menu_principal,
    'main_menu_layout': menu_layout,
    'extras_menu': extras,
    'layout_helper': layout_helper,
    'settings': configuracion,
    'press_start': lambda datos: envoltorio(datos, PRESS_START, 'PRESS_START.LOB'),
    'content_enumeration': lambda datos: envoltorio(datos, CONTENT_ENUMERATION, 'CONTENT_ENUMERATION.LOB'),
}


# ----------------------------------------------------------------------------- leer el WAD y generar

def leer_wad(ruta):
    """{ruta dentro del WAD en mayusculas: (indice, posicion)} de un WAD, con su lector de tools/wad.py."""
    import wad
    posiciones = None
    with open(ruta, 'rb') as f:
        posiciones = wad.posiciones(f)
    return {nombre.upper(): (i, posiciones[i]) for i, (nombre, _) in wad.rutas(ruta).items()}


def leer_entrada(carpeta, entrada, wads):
    ruta_wad = os.path.join(carpeta, entrada['wad'])
    if not os.path.isfile(ruta_wad):
        raise ErrorLua('falta %s en %s' % (entrada['wad'], carpeta))
    if ruta_wad not in wads:
        wads[ruta_wad] = leer_wad(ruta_wad)
    clave = entrada['entry'].upper()
    if clave not in wads[ruta_wad]:
        raise ErrorLua('%s no contiene %s' % (entrada['wad'], entrada['entry']))
    import wad
    return wad.contenido(ruta_wad, wads[ruta_wad][clave][1])


def generar(carpeta, entradas, destino, solo=None):
    """Escribe en `destino` los ficheros de `entradas`. Devuelve [(nombre, bytes)]."""
    os.makedirs(destino, exist_ok=True)
    wads = {}
    hechos = []
    for entrada in entradas:
        if solo and entrada['out'] != solo:
            continue
        clase = entrada.get('clase', entrada['out'].rsplit('.', 1)[1])
        if clase not in OPERACIONES:
            raise ErrorLua('%s: clase desconocida "%s"' % (entrada['out'], clase))
        datos = leer_entrada(carpeta, entrada, wads)
        try:
            salida = OPERACIONES[clase](datos)
        except ErrorLua as exc:
            raise ErrorLua('%s: %s' % (entrada['out'], exc))
        if isinstance(salida, str):
            # Los .lua del port se escriben con CRLF, igual que los que se probaron en consola.
            crudo = salida.replace('\n', '\r\n').encode('latin1')
        else:
            crudo = salida
        with open(os.path.join(destino, entrada['out']), 'wb') as f:
            f.write(crudo)
        hechos.append((entrada['out'], len(crudo)))
    return hechos


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--data', required=True, help='carpeta del juego (con los .WAD)')
    ap.add_argument('--out', required=True, help='carpeta donde dejar los ficheros generados')
    ap.add_argument('--game', default='mtg14', help='juego de install/games/ (por defecto mtg14)')
    ap.add_argument('--only', help='generar solo este fichero de salida')
    a = ap.parse_args()
    sys.path.insert(0, HERE)
    import importlib.util  # noqa: E402
    spec = importlib.util.spec_from_file_location('mtg14_install', os.path.join(HERE, 'install.py'))
    instalador = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(instalador)   # install/install.py, el mismo lector de TOML
    juego = instalador.cargar_juego(a.game)
    try:
        hechos = generar(a.data, juego.get('lua', []), a.out, a.only)
    except ErrorLua as exc:
        print('ERROR: %s' % exc)
        return 1
    for nombre, tam in hechos:
        print('  %-52s %8d bytes' % (nombre, tam))
    return 0


if __name__ == '__main__':
    sys.exit(main())
