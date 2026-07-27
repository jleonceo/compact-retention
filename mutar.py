# -*- coding: utf-8 -*-
"""Sabotea el medidor a proposito y comprueba que el banco se pone rojo.

POR QUE EXISTE (25/07/2026). Un esceptico paso dieciocho mutaciones a mano contra la suite de veinte
casos y **doce sobrevivieron**. Se podia dejar la cobertura media clavada en 99 %, o borrar el aviso
de privacidad que el README promete, con los veinte casos en verde. Un banco que no se pone rojo
cuando el codigo miente no esta protegiendo nada: esta acompañando.

QUE HACE. Rompe una linea, ejecuta el banco y mira si falla. Si no falla, esa linea no la vigila
nadie, y eso NO es un fallo del codigo: es un hueco del banco.

    python mutar.py            las mutaciones de serie
    python mutar.py --lista    solo dice cuales son, sin tocar nada

COMO SE RESTAURA EL FICHERO. La copia intacta se guarda en disco antes de tocar nada
(`medir_compacts_generico.py.original`) y se borra al acabar. Si esa copia sigue ahi al arrancar, la
ejecucion anterior murio a mitad y se restaura antes de hacer nada mas. El `finally` de Python no
cubre que te maten el proceso; el disco si.
"""
from __future__ import print_function

import io
import os
import subprocess
import sys

NL = chr(10)

AQUI = os.path.dirname(os.path.abspath(__file__))
MEDIDO = os.path.join(AQUI, "medir_compacts_generico.py")
RESIDUO = MEDIDO + ".original"
BANCO = "test_medir_compacts_generico.py"

# Cada entrada rompe UNA decision. Se eligen las que, fallando en silencio, darian numeros creibles
# y equivocados. Las doce primeras son las que el esceptico encontro sin cazar.
MUTACIONES = [
    ("el basename deja de entender las barras de Windows",
     'partes = [p for p in re.split(r"[\\\\/]", str(ruta)) if p]',
     'partes = [p for p in str(ruta).split("/") if p]'),
    ("el basename deja de entender las barras de POSIX",
     'partes = [p for p in re.split(r"[\\\\/]", str(ruta)) if p]',
     'partes = [p for p in str(ruta).split(chr(92)) if p]'),
    ("la ruta completa deja de probarse en las dos barras",
     '                or x.replace("/", "\\\\") in resumen]',
     '                ]'),
    ("el mismo resumen repetido vuelve a abrir ventana",
     "            if clave in vistos:",
     "            if False:"),
    # La guarda de `ventanas_de_sesion` NO esta en esta lista, y conviene decir por que: quitarla
    # no cambia nada observable, porque las dos funciones que consumen la ventana filtran tambien.
    # Eso no es un hueco del banco, es defensa repetida a proposito. La que si se mide es la de
    # abajo, que es la que evita el AttributeError cuando a `rutas_escritas` se le pasa el crudo.
    ("las lineas que no son objeto revientan al leer las rutas",
     "        if not isinstance(obj, dict):" + NL + "            continue" + NL +
     "        msg = obj.get",
     "        msg = obj.get"),
    ("los nombres perdidos vuelven a salir en el JSON sin pedirlo",
     "    if nombres:",
     "    if True:"),
    ("el conteo de perdidos pasa a ser siempre cero",
     '        "faltan_n": len([b for b in u_base if b not in resumen and not rec.get(b)]),',
     '        "faltan_n": 0,'),
    ("el indice deja de llegar y la vara del prefijo no se aplica",
     "        d = medir_ventana(registros, resumen, indice=indice, nombres=con_nombres)",
     "        d = medir_ventana(registros, resumen, nombres=con_nombres)"),
    ("desaparece el aviso de privacidad que el README promete",
     "    if args.con_nombres:",
     "    if False:"),
    ("los dos flags de origen a la vez dejan de rechazarse",
     "    if args.sesion and args.projects_dir:",
     "    if False:"),
    ("--sesion apuntando a una carpeta deja de rechazarse",
     "    if args.sesion and not os.path.isfile(origen):",
     "    if False:"),
    ("el hash de commit se reconoce desde 6 hex en vez de 7",
     r'(?:[0-9a-f]{40}|[0-9a-f]{7,12})',
     r'(?:[0-9a-f]{40}|[0-9a-f]{6,12})'),
    ("el hash de commit vuelve a partirse por los guiones y traga tramos de UUID",
     r'(?<![0-9A-Za-z-])(?:[0-9a-f]{40}|[0-9a-f]{7,12})(?![0-9A-Za-z-])',
     r'\b(?:[0-9a-f]{40}|[0-9a-f]{7,12})\b'),
    ("un identificador de dominio basta con UNA mayuscula",
     r'RE_ID = re.compile(r"\b[A-Z]{2,}-\d{2,4}\b")',
     r'RE_ID = re.compile(r"\b[A-Z]{1,}-\d{2,4}\b")'),
    ("la cobertura por nombre se calcula sobre las rutas",
     '"cob_base": (100.0 * len(hit_base) / len(u_base)) if u_base else None,',
     '"cob_base": (100.0 * len(hit_base) / len(u_rutas)) if u_rutas else None,'),
    # LAS NUEVE DE UN TERCERO. Un esceptico externo escribio doce mutaciones que yo no habia
    # pensado y sobrevivieron nueve, con los quince sabotajes de arriba cazados y el banco en
    # verde. Un mutador lo escribe quien conoce el codigo, asi que hereda su punto ciego: el
    # numero que da no mide la calidad del banco, mide el acuerdo entre dos cosas de la misma
    # cabeza. Estas nueve entran aqui para que no vuelvan, y la unica forma de encontrar las
    # siguientes es que las escriba otro.
    ("solo `Write` cuenta como escritura, ni Edit ni NotebookEdit",
     'ESCRIBEN = ("Write", "Edit", "MultiEdit", "NotebookEdit")',
     'ESCRIBEN = ("Write",)'),
    ("la dedup pasa a ir por TEXTO en vez de por uuid",
     '            clave = obj.get("uuid") or texto',
     '            clave = texto'),
    ("el emparejamiento de nombres se vuelve ciego a las mayusculas",
     "    hit_base = [b for b in u_base if b in resumen]",
     "    hit_base = [b for b in u_base if b.lower() in resumen.lower()]"),
    ("un resumen multibloque pierde todo menos el primer bloque",
     '        return "\\n".join(b.get("text", "") for b in content if isinstance(b, dict))',
     '        return next((b.get("text", "") for b in content if isinstance(b, dict)), "")'),
    ("un isCompactSummary falso tambien abre ventana",
     '    return bool(obj.get("isCompactSummary")) if isinstance(obj, dict) else False',
     '    return "isCompactSummary" in obj if isinstance(obj, dict) else False'),
    ("--con-nombres se vuelve inerte en el CLI",
     "    por_ventana, agregado = medir_todo(projects_dir, con_nombres=args.con_nombres)",
     "    por_ventana, agregado = medir_todo(projects_dir, con_nombres=False)"),
    ("el indice se queda con UN solo nombre",
     "    indice = sorted(nombre_de(r) for _, regs, _ in ventanas for r in rutas_escritas(regs))",
     "    indice = sorted(nombre_de(r) for _, regs, _ in ventanas for r in rutas_escritas(regs))[:1]"),
    ("el agregado infla el recuento de sesiones",
     '        "sesiones": len(set(d["sesion"] for d in por_ventana)),',
     '        "sesiones": len(por_ventana),'),
    ("una ruta acabada en separador vuelve a dar nombre vacio",
     "    return partes[-1] if partes else \"\"",
     "    return re.split(r\"[\\\\/]\", str(ruta))[-1]"),
]


def _rescatar_residuo():
    if not os.path.exists(RESIDUO):
        return False
    # El rescate conservaba mal por los dos lados: leia con saltos universales y escribia
    # forzando LF, asi que restaurar tras una muerte convertia el fichero entero.
    io.open(MEDIDO, "w", encoding="utf-8", newline="").write(
        io.open(RESIDUO, encoding="utf-8", newline="").read())
    os.remove(RESIDUO)
    print("  [!] La ejecucion anterior murio con una mutacion puesta. Fichero RESTAURADO.")
    return True


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    _rescatar_residuo()
    if "--lista" in argv:
        for desc, _, _ in MUTACIONES:
            print("  %s" % desc)
        return 0

    # LOS FINALES DE LINEA SE CONSERVAN TAL CUAL (27/07/2026). Antes se leia con saltos
    # universales y se reescribia forzando LF, asi que en un clon de Windows con
    # `core.autocrlf=true` el fichero pasaba de CRLF a LF y `git status` se quedaba diciendo
    # ` M ` para siempre, con `git diff` vacio. Contenido intacto y arbol sucio, justo en el
    # repositorio cuya tesis es que lo que protege es haber commiteado. Lo destapo una prueba
    # de clon frio. `newline=""` desactiva la traduccion en las dos direcciones.
    original = io.open(MEDIDO, encoding="utf-8", newline="").read()
    io.open(RESIDUO, "w", encoding="utf-8", newline="").write(original)

    # EL ARREGLO DE ARRIBA SE HIZO A MEDIAS Y LO DESTAPO EL CI (27/07/2026). Se corrigio la
    # LECTURA y se dejaron las tres escrituras forzando LF, o sea que el fichero se seguia
    # convirtiendo al restaurarlo: el mismo arbol sucio que se decia resuelto. Y encima el ancla
    # multilinea de una mutacion se escribe con `\n` a pelo, asi que en un clon con CRLF no casaba
    # con nada, esa mutacion salia SIN APLICAR y `mutar.py` terminaba con codigo 1. Los tres
    # trabajos de Windows de la matriz salieron rojos por esto; los seis de Linux y Mac, verdes,
    # porque alli el checkout es LF y el defecto es invisible.
    #
    # `SALTO` es el final de linea REAL del fichero medido, y las anclas se traducen a el antes de
    # buscarlas. Asi el mutador funciona igual en un clon LF y en uno CRLF, que es lo unico que
    # puede prometer una herramienta que se descarga.
    SALTO = "\r\n" if "\r\n" in original else "\n"

    def como_el_fichero(txt):
        return txt.replace(NL, SALTO) if SALTO != NL else txt
    cazadas = huecos = sin_aplicar = 0
    print("=" * 78)
    print("VERIFICACION POR MUTACION  --  %d sabotajes contra el banco" % len(MUTACIONES))
    print("=" * 78)
    try:
        for desc, viejo, nuevo in MUTACIONES:
            viejo, nuevo = como_el_fichero(viejo), como_el_fichero(nuevo)
            if viejo not in original:
                print("  %-56s SIN APLICAR (el codigo cambio)" % desc[:56])
                sin_aplicar += 1
                continue
            io.open(MEDIDO, "w", encoding="utf-8", newline="").write(
                original.replace(viejo, nuevo, 1))
            r = subprocess.run([sys.executable, BANCO], capture_output=True, cwd=AQUI)
            if r.returncode != 0:
                cazadas += 1
                print("  %-56s cazada" % desc[:56])
            else:
                huecos += 1
                print("  %-56s *** HUECO ***" % desc[:56])
            io.open(MEDIDO, "w", encoding="utf-8", newline="").write(original)
    finally:
        io.open(MEDIDO, "w", encoding="utf-8", newline="").write(original)
        if os.path.exists(RESIDUO):
            os.remove(RESIDUO)

    print()
    print("  cazadas: %d   huecos: %d   sin aplicar: %d" % (cazadas, huecos, sin_aplicar))
    if huecos:
        print("  Un hueco no es un fallo del codigo: es una linea que el banco no vigila.")
    if sin_aplicar:
        print("  'Sin aplicar' tampoco es aprobado: esas lineas se quedaron sin probar.")
    return 1 if (huecos or sin_aplicar) else 0


if __name__ == "__main__":
    sys.exit(main())
