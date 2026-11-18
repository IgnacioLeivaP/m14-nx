# La licencia de este repositorio está PENDIENTE de decisión

No elijas una licencia por inercia: la decisión es del autor del port, y tiene consecuencias en las dos direcciones.

## Situación

- El código nuevo del port (la aplicación en `app/`, las herramientas de `tools/` y el instalador de `install/`) no
  lleva hoy ningún aviso de licencia.
- El port está construido sobre otros proyectos con licencias distintas, y algunas de ellas **son incompatibles entre
  sí** si se quiere una sola licencia para todo el repositorio (ver `THIRD_PARTY.md`).
- `app/src/renut_engine` es código de reNut, cuyo permiso de reutilización está documentado pero cuya licencia no se
  encontró: **es la pieza que puede impedir publicar** hasta que su autor lo confirme.

## Recomendación

**GPL-3.0-or-later para el código propio** (`app/`, `tools/`, `install/`, este documento y el README).

Por qué:

1. Es la licencia que ya usan los ports hermanos de esta saga en los que este se apoya, así que el intercambio de
   herramientas entre ellos sigue siendo legal en ambos sentidos.
2. Encaja con que el proyecto no distribuye el juego: la GPL no obliga a nada sobre tus archivos, solo sobre el código.
3. Deja claro que quien reciba una copia del código puede modificarlo, y que las modificaciones vuelven.

Qué NO haría:

- **MIT o Apache-2.0**: son más cómodas, pero no son compatibles con reutilizar tal cual el código GPL de los ports
  hermanos que hay dentro de `tools/` y de algunas partes de `app/`. Cambiar a MIT exigiría reescribir o eliminar ese
  código.
- **Ninguna licencia (todos los derechos reservados)**: legalmente válido, pero nadie podría publicar una mejora ni
  arreglar un fallo, y muchos usuarios no lo instalarían.

## Antes de publicar, hacer

1. Añadir `LICENSE` con el texto completo de la licencia elegida y el aviso de copyright (año y titular).
2. Poner una cabecera corta en los archivos nuevos, o al menos en el README, indicando la licencia.
3. Confirmar con el autor de reNut (masterspike52) que `app/src/renut_engine` puede redistribuirse, y con qué licencia.
   Si la respuesta es que no, esa carpeta no puede ir en el repositorio y habrá que publicarla aparte.
4. Revisar `THIRD_PARTY.md` y dejar de marcar como DUDOSO lo que se aclare.

Mientras no exista `LICENSE`, este repositorio **no está licenciado**: los archivos son de su autor con todos los
derechos reservados por defecto, lo que basta para uso personal pero no para publicarlo en GitHub como proyecto
abierto.
