# -*- coding: utf-8 -*-
"""
medir_compacts_generico.py - mide que sobrevive al resumen de un auto-compact, leyendo SOLO del
JSONL de sesion, sin depender de ningun hook de sellado propio.

POR QUE GENERICO (24/07/2026)
-----------------------------
su version interna compara la ventana previa al corte contra el resumen, pero saca la ventana de un
transcript SELLADO por nuestro hook de PreCompact. Un tercero no tiene ese hook, asi que no puede
reproducir la medida. Este lee las dos cosas del MISMO fichero: el JSONL de sesion ya contiene, en
orden, los turnos previos al corte Y el mensaje marcado `isCompactSummary`. Sin instalar nada.

METODO
------
1. Una sesion puede tener varios cortes: cada `isCompactSummary` cierra una ventana. La ventana del
   corte k son los registros entre el resumen k-1 (excluido) y el resumen k. Se derivan solas del
   fichero; no hay lista escrita a mano de ventanas (esa es la diferencia con la version interna).
2. Las ENTIDADES de la ventana: rutas de fichero escritas (tool_use Write/Edit/MultiEdit/NotebookEdit),
   y como clases secundarias los hashes de commit y los identificadores tipo ABC-001 que aparezcan en
   el texto de la ventana.
3. El RESUMEN es el texto del mensaje `isCompactSummary`.
4. COBERTURA = que fraccion de las entidades de la ventana aparece literalmente en el resumen, y el
   RECUENTO ABSOLUTO de nombres conservados, que es donde vive la tesis del techo.

LIMITE QUE HAY QUE DECIR (heredado de la version interna): el emparejamiento de rutas es por BASENAME. Dos
rutas distintas con el mismo nombre (`SKILL.md`) se unen y el porcentaje sale OPTIMISTA. Se informa
aparte el recuento por ruta completa, que es el PESIMISTA. La verdad esta entre los dos.
"""

from __future__ import annotations

import argparse
import io
import json
import os
import re
import sys

ESCRIBEN = ("Write", "Edit", "MultiEdit", "NotebookEdit")

# Hash de commit: 7 a 40 hex. Identificador de dominio: DOS+ mayusculas, guion, 2 a 4 digitos.
#
# LAS DOS RESTRICCIONES DE ABAJO SON DEL 26/07/2026, y salen de una medicion sobre datos
# reales, no de leer el patron. Era `\b[0-9a-f]{7,40}\b`, y `\b` trata el guion como
# frontera: cada tramo de un UUID pasaba por hash de commit. Sondeando cinco ventanas
# reales salieron 23 "hashes", de los que cuatro eran tramos de UUID de nombres de sesion
# (`c1ecef4f`, `099c1bca`, `cf21d492`, `8df4798a3d57`). Como un tramo de UUID no aparece
# jamas en un resumen, esa clase venia SESGADA HACIA ABAJO por construccion: la linea
# "commits: 2 de 22" contaba veintidos cosas que no eran commits.
#
#   - Los lookarounds excluyen lo pegado a un guion o a otro caracter de palabra, que es
#     como viene un tramo de UUID.
#   - La longitud pasa a 7-12 o 40 exactos, que es lo que git produce de verdad (corto o
#     completo). El rango abierto colaba cosas como `a74dd00b0653d7683`, 17 caracteres,
#     que no es una longitud que git emita.
RE_COMMIT = re.compile(r"(?<![0-9A-Za-z-])(?:[0-9a-f]{40}|[0-9a-f]{7,12})(?![0-9A-Za-z-])")
RE_ID = re.compile(r"\b[A-Z]{2,}-\d{2,4}\b")


def aplanar_texto(content) -> str:
    """El content de un mensaje a texto plano (str, o lista de bloques con .text)."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(b.get("text", "") for b in content if isinstance(b, dict))
    return ""


def leer_jsonl(path):
    """(lineno, obj) por cada linea parseable; las rotas se saltan sin tumbar la lectura."""
    with io.open(path, encoding="utf-8", errors="replace") as fh:
        for i, ln in enumerate(fh, 1):
            ln = ln.strip()
            if not ln:
                continue
            try:
                yield i, json.loads(ln)
            except Exception:
                continue


def es_resumen(obj) -> bool:
    """Un JSONL de verdad trae lineas que no son objetos: `null`, un array suelto, un numero.

    Son JSON perfectamente valido, asi que `json.loads` las acepta y `obj.get` reventaba con un
    AttributeError delante del usuario. Comprobar el tipo cuesta una linea; el traceback lo paga
    quien acaba de descargarse esto.
    """
    return bool(obj.get("isCompactSummary")) if isinstance(obj, dict) else False


def nombre_de(ruta):
    """El basename de una ruta, venga con barras de Windows o de POSIX.

    `os.path.basename` PARTE SEGUN EL SISTEMA donde se ejecuta, no segun la ruta. En Linux y en
    Mac no considera `\\` un separador, asi que `C:\\proy\\doc.md` es un solo nombre entero de
    veinte caracteres y no casa con nada del resumen. Medido el 25/07 sustituyendo la funcion por
    su version POSIX: la cobertura de una ventana pasaba de 100 % a 0 % con el mismo resumen
    nombrando los dos ficheros, y seis de los veinte casos del banco se ponian rojos.

    Lo peor es que no da error. Da un cero, y el README dice que un recuento que baja sin motivo
    significa que cambio el formato de los transcripts. El usuario de Mac habria ido a buscar el
    fallo al sitio equivocado.
    """
    partes = [p for p in re.split(r"[\\/]", str(ruta)) if p]
    # Una ruta acabada en separador daba nombre VACIO, y la cadena vacia esta contenida en
    # cualquier resumen: esa entidad puntuaba siempre y la pantalla lo presentaba como 100 %.
    # No se ha visto en datos reales (0 de 10.523 rutas), pero una entidad que siempre acierta
    # no es una medida, es un adorno con aspecto de cifra.
    return partes[-1] if partes else ""


def ventanas_de_sesion(path):
    """Lista de (registros_ventana, texto_resumen) por cada CORTE de la sesion.

    La ventana del corte k son los registros acumulados desde el resumen anterior hasta este. Los
    registros posteriores al ultimo resumen NO forman ventana: no hubo corte que los resumiera.

    UN CORTE NO ES UNA APARICION. El JSONL reescribe el mismo mensaje `isCompactSummary` una vez
    por cada prompt posterior: entre dos copias solo cambia `promptId`, y `uuid`, `parentUuid`,
    `timestamp` y el mensaje son identicos. Sobre un historial real medido el 27/07 hay **234
    apariciones para 153 cortes**, un 53 % de inflado en 22 ficheros, con una sesion que sola tenia
    22 apariciones de 7 resumenes. Contarlas todas abre ventanas que nunca existieron, reparte las
    escrituras de un corte entre varias y saca el MISMO resumen con seis porcentajes distintos.
    """
    ventanas = []
    acum = []
    vistos = set()
    for _, obj in leer_jsonl(path):
        if es_resumen(obj):
            texto = aplanar_texto((obj.get("message") or {}).get("content"))
            # EL TEXTO ENTERO, no sus primeros caracteres. Con `texto[:200]` dos cortes
            # distintos se fundian, porque los resumenes reales arrancan con una cabecera de
            # plantilla de 238 caracteres: sobre un corpus real, 148 cortes colapsaban a 86 y el
            # segundo de cada par desaparecia con sus escrituras dentro. Un prefijo se eligio
            # "por eficiencia" sobre cadenas de 16.000 caracteres; comparar enteras cuesta lo
            # mismo en la practica y no inventa colisiones.
            clave = obj.get("uuid") or texto
            if clave in vistos:
                continue          # copia del mismo corte: ni abre ventana ni corta la que hay
            vistos.add(clave)
            ventanas.append((acum, texto))
            acum = []
        elif isinstance(obj, dict):
            acum.append(obj)
    return ventanas


def rutas_escritas(registros):
    """Rutas de fichero escritas en la ventana (Write/Edit/...), normalizadas a backslash."""
    rutas = []
    for obj in registros:
        if not isinstance(obj, dict):
            continue
        msg = obj.get("message") or {}
        for b in (msg.get("content") or []):
            if not isinstance(b, dict) or b.get("type") != "tool_use":
                continue
            if b.get("name") not in ESCRIBEN:
                continue
            fp = (b.get("input") or {}).get("file_path")
            if fp:
                # Se guarda TAL CUAL. Antes se normalizaba a contrabarra, que es lo comodo en
                # Windows y lo que rompia el basename en Linux y Mac. Quien parte la ruta es
                # `nombre_de`, que entiende las dos barras vengan de donde vengan.
                rutas.append(str(fp))
    return rutas


def texto_de_ventana(registros) -> str:
    """Texto plano de todos los mensajes de la ventana, para pescar commits e IDs."""
    trozos = []
    for obj in registros:
        if not isinstance(obj, dict):
            continue
        trozos.append(aplanar_texto((obj.get("message") or {}).get("content")))
    return "\n".join(trozos)


def cobertura(entidades, resumen):
    """(aciertos, total): cuantas entidades distintas aparecen literalmente en el resumen."""
    unicas = sorted(set(entidades))
    hit = [e for e in unicas if e in resumen]
    return len(hit), len(unicas)


def recuperable(base, resumen, indice):
    """El prefijo del nombre que el resumen conserva y que AUN lleva al fichero, o None.

    Un resumen no siempre escribe el nombre entero: abrevia `00_INFORME_ANUAL_conclusiones.md`
    como `00_INFORME_ANUAL`. Contar eso como nombre PERDIDO hunde la cifra sin motivo, porque con
    ese prefijo se vuelve al fichero con un glob. Medido el 25/07 sobre una ventana real: 50 %
    exigiendo el nombre entero, 91 % contando lo que de verdad sigue siendo localizable.

    Dos condiciones, y la segunda hizo falta porque la primera sola colaba basura:
      (1) UNICIDAD: un glob `prefijo*` sobre `indice` devuelve ese fichero y ningun otro. Se
          cuentan las coincidencias en vez de agruparlas, porque dos ficheros con el mismo
          nombre en dos carpetas distintas son dos y un `set` los daria por uno.
      (2) LIMITE DE TOKEN: el prefijo acaba donde acaba un trozo del nombre (antes de `_`, `-`
          o `.`), nunca a mitad de palabra. Sin esto, `.gitignore` colaba como `.git` y
          `escanear_ficheros.py` como `esca`: presentes en el resumen por ser palabras
          corrientes, no porque el resumen recuerde el fichero.

    `indice` es la lista de nombres de fichero contra la que se comprueba la unicidad. Se pasa
    desde fuera a proposito: esta funcion no sabe donde vive el proyecto de quien la use.
    """
    sin_ext = os.path.splitext(base)[0]
    for k in range(len(sin_ext), 3, -1):
        p = sin_ext[:k]
        if p not in resumen:
            continue
        if k < len(sin_ext) and sin_ext[k] not in "_-.":
            continue
        casan = [n for n in indice if n.startswith(p)]
        return p if casan == [base] else None
    return None


def medir_ventana(registros, resumen, con_secundarias=True, indice=None, nombres=False):
    """Diccionario con las cifras de una ventana.

    `indice`: nombres de fichero del proyecto, para la vara de recuperables. Sin el, esa vara
    no se calcula y `cob_localizable` sale igual que `cob_base`, que es el comportamiento
    anterior y no miente: solo mide menos.
    """
    rutas = rutas_escritas(registros)
    u_rutas = sorted(set(rutas))
    u_base = sorted(set(nombre_de(r) for r in u_rutas))

    hit_base = [b for b in u_base if b in resumen]
    rec = {}
    if indice:
        rec = {b: recuperable(b, resumen, indice) for b in u_base if b not in resumen}
    hit_prefijo = [b for b, v in rec.items() if v]
    # Ruta completa: se prueba en backslash y en barra, como la version interna.
    hit_ruta = [x for x in u_rutas
                if x in resumen or x.replace("\\", "/") in resumen
                or x.replace("/", "\\") in resumen]

    d = {
        "escrituras": len(rutas),
        "rutas_distintas": len(u_rutas),
        "nombres_distintos": len(u_base),
        "resumen_chars": len(resumen),
        "resumen_palabras": len(resumen.split()),
        "hit_base": len(hit_base),
        "hit_ruta": len(hit_ruta),
        "hit_prefijo": len(hit_prefijo),
        "cob_base": (100.0 * len(hit_base) / len(u_base)) if u_base else None,
        "cob_ruta": (100.0 * len(hit_ruta) / len(u_rutas)) if u_rutas else None,
        "cob_localizable": (100.0 * (len(hit_base) + len(hit_prefijo)) / len(u_base))
                           if u_base else None,
        # LOS PERDIDOS DEL TODO: ni el nombre entero ni un prefijo que lleve a el.
        #
        # SALE EL CONTEO, NO LA LISTA, y esa es la diferencia entre una metrica y una filtracion.
        # Un auditor midio el 25/07 que `--json` sobre un historial real volcaba 1.025 nombres de
        # fichero: titulos de documentos privados, `.env.example`, nombres de persona dentro del
        # titulo. El aviso decia "conversaciones privadas y sus nombres", que cualquiera entiende
        # como identificadores de sesion, porque es lo unico que saca el modo texto. Quien pegara
        # esa salida en un issue publicaba su arbol de trabajo entero.
        #
        # Con `--con-nombres` vuelve la lista, y entonces el usuario ha dicho que si.
        "faltan_n": len([b for b in u_base if b not in resumen and not rec.get(b)]),
    }
    if nombres:
        d["faltan"] = [b for b in u_base if b not in resumen and not rec.get(b)]
    if con_secundarias:
        txt = texto_de_ventana(registros)
        commits = set(RE_COMMIT.findall(txt))
        ids = set(RE_ID.findall(txt))
        d["commit_hit"], d["commit_total"] = cobertura(commits, resumen)
        d["id_hit"], d["id_total"] = cobertura(ids, resumen)
    return d


def sesiones_en(projects_dir):
    """Todos los *.jsonl bajo projects_dir (recursivo). Vale un dir de proyecto o uno de juguete.

    Si se le pasa un FICHERO en vez de una carpeta, devuelve ese fichero y ya esta. Lo pedia el
    README, que enseñaba en portada `--sesion <ruta-al-jsonl>` cuando el programa solo aceptaba
    carpetas: el comando de la primera pantalla fallaba el 100 % de las veces, en los dos idiomas.
    """
    if os.path.isfile(projects_dir):
        return [projects_dir] if projects_dir.lower().endswith(".jsonl") else []
    encontrados = []
    for raiz, _, ficheros in os.walk(projects_dir):
        for f in ficheros:
            # `.lower()` EN LAS CUATRO COMPROBACIONES (27/07/2026). Aqui iba sin el y en las
            # puertas de validacion con el, asi que un `S.JSONL` copiado en Windows o en Mac
            # pasaba la puerta y luego no lo recogia nadie: cero silencioso por las DOS banderas,
            # sobre un fichero de contenido perfectamente valido. Dos funciones del mismo fichero
            # discrepando sobre el mismo predicado. Lo cazo una auditoria ciega.
            if f.lower().endswith(".jsonl"):
                encontrados.append(os.path.join(raiz, f))
    return sorted(encontrados)


def _tiene_json(ruta):
    """Al menos una linea del fichero parsea como JSON. La comprobacion que ya existia para
    `--sesion`, sacada a funcion para que las DOS banderas usen el mismo predicado en vez de
    cada una el suyo."""
    try:
        with io.open(ruta, encoding="utf-8", errors="replace") as fh:
            for linea in fh:
                if not linea.strip():
                    continue
                try:
                    json.loads(linea)
                    return True
                except Exception:
                    continue
    except Exception:
        return False
    return False


def autodetectar_projects_dir():
    """~/.claude/projects si existe. El lector puede pasar el suyo con --projects-dir."""
    cand = os.path.expanduser(os.path.join("~", ".claude", "projects"))
    return cand if os.path.isdir(cand) else None


def medir_todo(projects_dir, con_nombres=False):
    """Recorre las sesiones y devuelve (por_ventana, agregado).

    DOS PASADAS, y la primera existe por una razon concreta. `recuperable()` necesita saber que
    otros nombres hay para decidir si un prefijo lleva a UN fichero o a doce, y el CLI no le pasaba
    nada: la cifra doble que el codigo anunciaba (50 % exigiendo el nombre entero, 91 % contando lo
    localizable) NO se podia reproducir ejecutando esto, porque `hit_prefijo` salia 0 siempre. Un
    auditor lo encontro el 25/07. Una cifra que el lector no puede recalcular es una cifra que
    tiene que creerse.

    El indice se arma con los nombres del PROPIO historial que se esta midiendo, no del disco: asi
    la medida es autocontenida y sale igual en cualquier maquina con los mismos ficheros.
    """
    ventanas = []
    for ps in sesiones_en(projects_dir):
        for registros, resumen in ventanas_de_sesion(ps):
            ventanas.append((os.path.basename(ps), registros, resumen))

    # LISTA, no conjunto, y `recuperable` documenta por que: un nombre que aparece en dos
    # carpetas son DOS ficheros, y un prefijo que lleva a los dos no localiza ninguno. El
    # conjunto le quitaba esa multiplicidad y le hacia conceder creditos que su propia regla
    # niega: 10 de 177 sobre un historial real, con `DECISIONES.md` presente en cinco rutas.
    indice = sorted(nombre_de(r) for _, regs, _ in ventanas for r in rutas_escritas(regs))

    por_ventana = []
    for sesion, registros, resumen in ventanas:
        d = medir_ventana(registros, resumen, indice=indice, nombres=con_nombres)
        d["sesion"] = sesion
        por_ventana.append(d)

    con_datos = [d for d in por_ventana if d["nombres_distintos"] > 0]
    nombres = [d["hit_base"] for d in con_datos]
    agregado = {
        "sesiones": len(set(d["sesion"] for d in por_ventana)),
        "ventanas": len(por_ventana),
        "ventanas_con_escrituras": len(con_datos),
        "nombres_conservados_min": min(nombres) if nombres else None,
        "nombres_conservados_max": max(nombres) if nombres else None,
        "cobertura_media_base": (sum(d["cob_base"] for d in con_datos) / len(con_datos))
        if con_datos else None,
    }
    return por_ventana, agregado


def imprimir(por_ventana, agregado, projects_dir):
    print("=" * 78)
    print("COBERTURA DEL RESUMEN DE COMPACT  (leída del JSONL de sesión, reproducible)")
    print("fuente: %s" % projects_dir)
    print("=" * 78)
    for d in por_ventana:
        if d["nombres_distintos"] == 0:
            continue
        print("\n%s" % d["sesion"])
        print("  resumen: %d chars, %d palabras" % (d["resumen_chars"], d["resumen_palabras"]))
        print("  escrituras: %d llamadas sobre %d rutas (%d nombres distintos)"
              % (d["escrituras"], d["rutas_distintas"], d["nombres_distintos"]))
        print("  NOMBRADOS por el resumen:")
        print("    por nombre  : %d de %d  (%.0f%%)  <- optimista"
              % (d["hit_base"], d["nombres_distintos"], d["cob_base"]))
        print("    por ruta    : %d de %d  (%.0f%%)  <- pesimista"
              % (d["hit_ruta"], d["rutas_distintas"], d["cob_ruta"]))
        if d.get("commit_total"):
            print("    commits     : %d de %d" % (d["commit_hit"], d["commit_total"]))
        if d.get("id_total"):
            print("    ids ABC-001 : %d de %d" % (d["id_hit"], d["id_total"]))
    print()
    print("-" * 78)
    a = agregado
    print("AGREGADO: %d sesiones, %d ventanas (%d con escrituras)."
          % (a["sesiones"], a["ventanas"], a["ventanas_con_escrituras"]))
    if a["nombres_conservados_min"] is not None:
        print("Nombres de fichero conservados por el resumen: banda de %d a %d."
              % (a["nombres_conservados_min"], a["nombres_conservados_max"]))
        print("Cobertura media (por nombre): %.0f%%." % a["cobertura_media_base"])
        print("Ahí vive la tesis del TECHO: el resumen conserva un número acotado de nombres,")
        print("no un porcentaje fijo; cuanto más grande la ventana, menor la fracción.")
        print()
        # ESTO NO ES DECORACION Y VA AQUI A PROPOSITO (26/07/2026). El aviso existia, pero
        # vivia en un cursor privado y en un informe, o sea en ningun sitio para quien se
        # descarga la herramienta. Un desconocido lee "cobertura 67 %" y entiende que pierde
        # un tercio de su trabajo en cada corte, que es exactamente lo contrario de lo medido:
        # de veintisiete cortes seguidos, veintitres no perdieron NADA irrecuperable. Una cifra que
        # se puede leer como dano tiene que decir que no lo es en el mismo sitio donde se
        # imprime, no en la documentacion de al lado.
        print("QUÉ NO ES ESTE NÚMERO: no es cuánto trabajo se pierde. Mide en cuántas cosas")
        print("te repartías, no cuánto daño hizo el corte. Lo que protege lo que importa es")
        print("haberlo commiteado, no que el resumen acierte a nombrarlo.")
        print()
        # PARA QUE SIRVE LA CIFRA. Sin esta linea el lector se queda con un numero suelto y sin
        # nada que hacer con el. La decision que habilita es donde poner el umbral del corte, y
        # el README trae los dos regimenes medidos aqui (292k y 585k) con sus cuatro ventanas.
        print("PARA QUÉ SIRVE: es un termómetro comparativo, no una nota absoluta. Mide el mismo")
        print("historial antes y después de mover el umbral del auto-compact, o un día contra")
        print("otro. El README explica las dos variables que mueven ese umbral y qué salió al")
        print("medirlas.")
    else:
        print("Ninguna ventana con escrituras: nada que medir en esta fuente.")
    print("-" * 78)


def main(argv=None):
    p = argparse.ArgumentParser(description="Mide qué sobrevive al resumen de un auto-compact.")
    p.add_argument("--sesion", default=None,
                   help="UN fichero .jsonl de sesión. Es por donde se empieza: mide solo esa.")
    p.add_argument("--projects-dir", default=None,
                   help="Carpeta con los JSONL de sesión (recursivo). Por defecto, ~/.claude/projects.")
    p.add_argument("--demo", action="store_true",
                   help="Fabrica una sesion de juguete en un temporal y la mide. Sirve para ver "
                        "el programa funcionar sin tener historial propio.")
    p.add_argument("--json", action="store_true", help="Salida en JSON en vez de texto.")
    p.add_argument("--con-nombres", action="store_true",
                   help="Incluye en el JSON los NOMBRES de fichero que el resumen perdió. Son "
                        "nombres de TUS documentos: no pegues esa salida en un issue sin mirarla.")
    args = p.parse_args(argv)

    if args.sesion and args.projects_dir:
        print("--sesion y --projects-dir piden cosas distintas: un fichero o una carpeta. Elige.")
        return 2

    # `--demo` EXISTE PORQUE QUIEN NO USA CLAUDE CODE NO TENIA NADA QUE MIRAR (27/07/2026). Sin
    # historial propio, la primera ejecucion de un desconocido era un bloque de ceros: no podia
    # distinguir "esta herramienta no me sirve" de "no tengo cortes todavia". Lo señalaron por
    # separado un lector externo y una prueba de clon frio. Fabrica la traza en un temporal y la
    # borra: no escribe en el arbol ni toca tu historial.
    if args.demo:
        import shutil
        import tempfile
        carpeta = tempfile.mkdtemp(prefix="compact_demo_")
        try:
            ruta = os.path.join(carpeta, "sesion_de_juguete.jsonl")
            escritura = lambda f: {"message": {"content": [
                {"type": "tool_use", "name": "Write", "input": {"file_path": f}}]}}
            filas = [escritura("/proyecto/informe.md"),
                     escritura("/proyecto/analisis.py"),
                     escritura("/proyecto/notas_sueltas.txt"),
                     {"message": {"content": [
                         {"type": "text",
                          "text": "Commit a1b2c3d sobre ABC-001, ya cerrado."}]}},
                     {"isCompactSummary": True, "message": {"content":
                      "Resumen: se trabajo en informe.md y en analisis.py, con el commit "
                      "a1b2c3d y la incidencia ABC-001. Queda pendiente revisar el resto."}}]
            with io.open(ruta, "w", encoding="utf-8", newline="\n") as fh:
                for fila in filas:
                    fh.write(json.dumps(fila, ensure_ascii=False) + "\n")
            # `--demo --json` SE ACEPTABA Y SE TIRABA (27/07/2026). Esta rama retornaba antes de
            # llegar a la de JSON, asi que quien pidiera las dos recibia la tabla de pantalla y un
            # codigo 0: una bandera admitida que no hacia nada, que es peor que rechazarla. Lo cazo
            # una revision ciega. La narracion se va a stderr por el mismo motivo que el aviso de
            # privacidad de mas abajo: en modo maquina, stdout tiene que ser JSON y nada mas.
            salida = sys.stderr if args.json else sys.stdout
            print("DEMO: sesion de juguete con 3 ficheros escritos, 1 commit y 1 identificador.",
                  file=salida)
            print("      El resumen nombra dos de los tres ficheros, asi que la cobertura por",
                  file=salida)
            print("      nombre tiene que salir 2 de 3. Lo que falta, `notas_sueltas.txt`.",
                  file=salida)
            print(file=salida)
            por_ventana, agregado = medir_todo(ruta, con_nombres=False)
            if args.json:
                # La clave es `ventanas`, la MISMA que la salida real de mas abajo. Un demo que
                # devuelve otro esquema entrena al lector contra su propia herramienta.
                print(json.dumps({"ventanas": por_ventana, "agregado": agregado},
                                 ensure_ascii=False, indent=2))
            else:
                imprimir(por_ventana, agregado, ruta)
            return 0
        finally:
            shutil.rmtree(carpeta, ignore_errors=True)

    # SIN ARGUMENTOS SE LEE TODO EL HISTORIAL, Y ESO HAY QUE DECIRLO. El valor por defecto es la
    # carpeta de todos los proyectos, o sea que la primera ejecucion curiosa abre conversaciones
    # privadas y saca sus nombres por pantalla. No sale nada del ordenador, pero conviene saberlo
    # antes y no despues.
    origen = args.sesion or args.projects_dir or autodetectar_projects_dir()
    if not origen or not os.path.exists(origen):
        print("No hay sesiones que medir. Pasa --sesion con un .jsonl o --projects-dir con una "
              "carpeta que los contenga.")
        return 2
    if args.sesion and not os.path.isfile(origen):
        print("--sesion espera un fichero .jsonl. Para una carpeta entera usa --projects-dir.")
        return 2
    # LA SIMETRIA QUE FALTABA. `--sesion` lleva desde el 27/07 rechazando una carpeta, y
    # `--projects-dir` seguia tragando un fichero suelto: apuntarlo a `notas.txt` daba la tabla de
    # ceros con codigo 0. O sea que EL MISMO error del lector recibia diagnostico o silencio segun
    # cual de las dos banderas hubiera acertado. Las dos comprobaciones se escribieron con dias de
    # diferencia y ninguna miro a su hermana.
    if args.projects_dir and not os.path.isdir(origen):
        print("--projects-dir espera una carpeta. Para un fichero suelto usa --sesion.")
        return 2

    # EL FICHERO EQUIVOCADO TIENE QUE DECIRLO (27/07/2026). Antes, apuntar `--sesion` a un
    # `notas.txt` daba el mismo texto y el mismo codigo 0 que "aqui no hay cortes", asi que quien
    # se equivocaba de argumento concluia que no tenia compacts. Tres estados distintos con una
    # sola respuesta. Lo destapo una prueba de clon frio.
    #
    # Un fichero VACIO sigue saliendo con codigo 0 a proposito: eso no es un error, es una sesion
    # sin nada dentro, y hay dos casos del banco que lo fijan.
    if args.sesion:
        if not origen.lower().endswith(".jsonl"):
            print("%s no es un .jsonl. Las sesiones de Claude Code terminan en .jsonl; esto "
                  "parece otra cosa." % os.path.basename(origen))
            return 2
        legibles = 0
        with io.open(origen, encoding="utf-8", errors="replace") as fh:
            for linea in fh:
                if not linea.strip():
                    continue
                try:
                    json.loads(linea)
                    legibles += 1
                    break
                except Exception:
                    continue
        if os.path.getsize(origen) > 0 and legibles == 0:
            print("%s tiene contenido pero ninguna línea es JSON válido: no parece un JSONL de "
                  "sesión." % os.path.basename(origen))
            return 2
    # Y LA MITAD QUE FALTABA (27/07/2026). El arreglo de arriba se hizo solo para `--sesion` y una
    # segunda revision ciega lo cazo: apuntar `--projects-dir` a una carpeta llena de ficheros que
    # no son sesiones seguia diciendo "aqui no hay cortes", con codigo 0. El mismo fichero era "no
    # es un JSONL de sesion" por una via e invisible por la otra.
    #
    # Una carpeta vacia SI sale con 0 a proposito: eso es ausencia de dato legitima. Lo que se
    # separa es "no hay nada" de "hay cosas y ninguna es lo que buscas".
    # Y EL TERCER PISO DEL MISMO DEFECTO (27/07/2026). Primero se arreglo la EXTENSION en las dos
    # banderas, luego las MAYUSCULAS en las cuatro comprobaciones, y quedaba el CONTENIDO: un
    # `sesion_falsa.jsonl` lleno de basura era "ninguna linea es JSON valido" por `--sesion` y una
    # tabla de ceros con codigo 0 por `--projects-dir`. Tres rondas para el mismo predicado en dos
    # sitios. La leccion no es el arreglo: es que un defecto se cierra en la SUPERFICIE donde vive,
    # no en el camino donde se noto, y esta es la cuarta vez que este repositorio lo paga.
    if args.projects_dir and os.path.isdir(origen):
        hay = falsos = vacios = 0
        for raiz, _, ficheros in os.walk(origen):
            for f in ficheros:
                hay += 1
                ruta = os.path.join(raiz, f)
                if not f.lower().endswith(".jsonl"):
                    falsos += 1
                elif os.path.getsize(ruta) > 0 and not _tiene_json(ruta):
                    falsos += 1          # se llama .jsonl y por dentro no lo es
                elif os.path.getsize(ruta) == 0:
                    vacios += 1          # un fichero vacio no acusa a nadie
        if hay and falsos == hay:
            print("En %s hay %d fichero(s) y ninguno es un .jsonl. Las sesiones de Claude Code "
                  "terminan en .jsonl: esto no es una carpeta de sesiones, o esta es la carpeta "
                  "equivocada. No es un cero, es que no se pudo mirar." % (origen, hay))
            return 2

    if not args.sesion and not args.projects_dir:
        # A stderr, y no es cosmetico: iba a stdout por delante del JSON y la salida en modo
        # maquina dejaba de ser JSON. Quien encadenara esto con otra cosa recibia un aviso
        # pegado delante del objeto. Ademas este aviso lleva la ruta del home dentro.
        print("Sin --sesion ni --projects-dir se lee TODO tu historial de Claude Code "
              "(%s), de todos los proyectos a la vez. Son conversaciones PRIVADAS: no sale nada "
              "de tu ordenador, pero conviene saberlo antes y no después." % origen,
              file=sys.stderr)
    if args.con_nombres:
        # El aviso va donde esta el riesgo. `--con-nombres` mete en el JSON los nombres de los
        # ficheros que el resumen perdio, que son titulos de documentos de quien lo ejecuta: sobre
        # un historial real se midieron 1.025, con `.env.example` entre ellos. Quien pegue esa
        # salida en un issue publica su arbol de trabajo, y tiene que saberlo en ese momento.
        print("AVISO de PRIVACIDAD: --con-nombres incluye los nombres de TUS ficheros en la "
              "salida. Míralos antes de pegarla en ningún sitio.", file=sys.stderr)
    projects_dir = origen

    por_ventana, agregado = medir_todo(projects_dir, con_nombres=args.con_nombres)
    if args.json:
        print(json.dumps({"ventanas": por_ventana, "agregado": agregado},
                         ensure_ascii=False, indent=2))
    else:
        imprimir(por_ventana, agregado, projects_dir)
    return 0


if __name__ == "__main__":
    # La salida lleva tildes y la consola de Windows no siempre viene en UTF-8. Sin esto, un
    # `print` con una tilde tumba el programa entero con UnicodeEncodeError en vez de imprimir.
    # Con `errors="replace"` una consola antigua enseña un signo raro, que es un mal menor
    # comparado con una traza. Va dentro de `try` porque `reconfigure` no existe antes de 3.7.
    for flujo in (sys.stdout, sys.stderr):
        try:
            flujo.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    sys.exit(main())
