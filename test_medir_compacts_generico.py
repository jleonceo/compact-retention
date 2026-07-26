# -*- coding: utf-8 -*-
"""Suite de aceptacion de medir_compacts_generico.py. Sin dependencias externas (unittest).

Cubre:
  CA1  se ejecuta sobre un --projects-dir arbitrario con dos JSONL de juguete (uno con resumen, otro sin).
  W    la ventana se deriva sola: multi-resumen no recuenta lo de la ventana anterior.
  ENT  entidades: rutas (basename/completa), commits e IDs.
  COB  la aritmetica de cobertura.
  CA5  corner: fichero vacio, lineas rotas, resumen sin escrituras, dir sin JSONL.
"""

import io
import json
import os
import tempfile
import unittest

import medir_compacts_generico as m


def rec_write(*rutas):
    """Un registro de asistente con tool_use Write por cada ruta."""
    content = [{"type": "tool_use", "name": "Write", "input": {"file_path": r}} for r in rutas]
    return {"type": "assistant", "message": {"content": content}}


def rec_texto(txt):
    """Un registro con texto plano (para colar commits/IDs en la ventana)."""
    return {"type": "assistant", "message": {"content": [{"type": "text", "text": txt}]}}


def rec_resumen(txt, como_lista=False):
    """El mensaje isCompactSummary. content puede ser str o lista de bloques."""
    content = [{"type": "text", "text": txt}] if como_lista else txt
    return {"isCompactSummary": True, "message": {"content": content}}


def escribir_jsonl(path, registros):
    with io.open(path, "w", encoding="utf-8") as fh:
        for r in registros:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")


class BaseDir(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="medcompact_")

    def tearDown(self):
        for raiz, _, fs in os.walk(self.tmp, topdown=False):
            for f in fs:
                os.remove(os.path.join(raiz, f))
            os.rmdir(raiz)

    def jsonl(self, nombre, registros):
        escribir_jsonl(os.path.join(self.tmp, nombre), registros)


class TestCA1DirArbitrario(BaseDir):
    def test_dos_juguete_uno_con_resumen_otro_sin(self):
        # Sesion CON resumen: escribe A.md y B.py; el resumen solo nombra A.md.
        self.jsonl("con_resumen.jsonl", [
            rec_write("C:/x/A.md"),
            rec_write("C:/y/B.py"),
            rec_resumen("Resumen: se toco A.md y otras cosas."),
        ])
        # Sesion SIN resumen: escribe algo pero nunca compacta.
        self.jsonl("sin_resumen.jsonl", [
            rec_write("C:/z/C.txt"),
        ])
        por_ventana, agg = m.medir_todo(self.tmp, con_nombres=True)

        self.assertEqual(agg["ventanas"], 1, "solo la sesion con resumen aporta ventana")
        self.assertEqual(agg["ventanas_con_escrituras"], 1)
        d = por_ventana[0]
        self.assertEqual(d["nombres_distintos"], 2)          # A.md, B.py
        self.assertEqual(d["hit_base"], 1)                    # solo A.md nombrado
        self.assertEqual(d["faltan"], ["B.py"])
        self.assertEqual(agg["nombres_conservados_min"], 1)
        self.assertEqual(agg["nombres_conservados_max"], 1)


class TestVentanaSeDeriva(BaseDir):
    def test_multiresumen_no_recuenta_la_ventana_anterior(self):
        # Corte 1: escribe A.md, resumen nombra A.md -> 1/1.
        # Corte 2: escribe B.py DESPUES del primer resumen, resumen 2 no nombra nada -> 0/1.
        self.jsonl("s.jsonl", [
            rec_write("C:/x/A.md"),
            rec_resumen("nombra A.md"),
            rec_write("C:/y/B.py"),
            rec_resumen("no nombra el fichero nuevo"),
        ])
        por_ventana, agg = m.medir_todo(self.tmp, con_nombres=True)
        self.assertEqual(agg["ventanas"], 2)
        v1, v2 = por_ventana
        self.assertEqual((v1["nombres_distintos"], v1["hit_base"]), (1, 1))
        self.assertEqual((v2["nombres_distintos"], v2["hit_base"]), (1, 0))
        self.assertEqual(v2["faltan"], ["B.py"])

    def test_registros_tras_el_ultimo_resumen_no_forman_ventana(self):
        self.jsonl("s.jsonl", [
            rec_write("C:/x/A.md"),
            rec_resumen("nombra A.md"),
            rec_write("C:/y/B.py"),   # sin resumen posterior: no es ventana
        ])
        por_ventana, agg = m.medir_todo(self.tmp)
        self.assertEqual(agg["ventanas"], 1)


class TestEntidades(BaseDir):
    def test_basename_optimista_vs_ruta_pesimista(self):
        # Mismo basename en dos rutas: por nombre cuenta 1, por ruta cuenta 2.
        self.jsonl("s.jsonl", [
            rec_write("C:/a/SKILL.md"),
            rec_write("C:/b/SKILL.md"),
            rec_resumen("el resumen dice SKILL.md una vez"),
        ])
        d = m.medir_todo(self.tmp)[0][0]
        self.assertEqual(d["nombres_distintos"], 1)          # un basename
        self.assertEqual(d["rutas_distintas"], 2)            # dos rutas
        self.assertEqual(d["hit_base"], 1)                   # optimista: 1/1
        self.assertEqual(d["hit_ruta"], 0)                   # pesimista: ninguna ruta completa aparece

    def test_commits_e_ids_secundarios(self):
        self.jsonl("s.jsonl", [
            rec_texto("commit 1a2b3c4 cierra ABC-001 y toca XYZ-042"),
            rec_write("C:/a/X.md"),
            rec_resumen("el resumen menciona 1a2b3c4 y ABC-001 y nada mas"),
        ])
        d = m.medir_todo(self.tmp)[0][0]
        self.assertEqual(d["commit_hit"], 1)                 # 1a2b3c4 sobrevive
        self.assertGreaterEqual(d["commit_total"], 1)
        self.assertEqual(d["id_total"], 2)                   # ABC-001, XYZ-042
        self.assertEqual(d["id_hit"], 1)                     # solo ABC-001 nombrado

    def test_resumen_como_lista_de_bloques(self):
        # El isCompactSummary a veces trae content como lista, no como str.
        self.jsonl("s.jsonl", [
            rec_write("C:/a/A.md"),
            rec_resumen("nombra A.md", como_lista=True),
        ])
        d = m.medir_todo(self.tmp)[0][0]
        self.assertEqual(d["hit_base"], 1)


class TestCornerCA5(BaseDir):
    def test_fichero_vacio(self):
        self.jsonl("vacio.jsonl", [])
        por_ventana, agg = m.medir_todo(self.tmp)
        self.assertEqual(agg["ventanas"], 0)

    def test_lineas_rotas_no_tumban(self):
        path = os.path.join(self.tmp, "roto.jsonl")
        with io.open(path, "w", encoding="utf-8") as fh:
            fh.write("{no es json\n")
            fh.write(json.dumps(rec_write("C:/a/A.md")) + "\n")
            fh.write("otra basura }{\n")
            fh.write(json.dumps(rec_resumen("nombra A.md")) + "\n")
        d = m.medir_todo(self.tmp)[0][0]
        self.assertEqual(d["hit_base"], 1)                   # midio pese a las lineas rotas

    def test_resumen_sin_escrituras(self):
        self.jsonl("s.jsonl", [
            rec_texto("solo hable, no escribi ficheros"),
            rec_resumen("un resumen cualquiera"),
        ])
        por_ventana, agg = m.medir_todo(self.tmp)
        self.assertEqual(agg["ventanas"], 1)
        self.assertEqual(agg["ventanas_con_escrituras"], 0)  # ventana sin escrituras
        self.assertIsNone(agg["nombres_conservados_min"])    # nada que promediar

    def test_dir_sin_jsonl(self):
        por_ventana, agg = m.medir_todo(self.tmp)
        self.assertEqual(por_ventana, [])
        self.assertEqual(agg["ventanas"], 0)


class TestRecuperablePorPrefijo(unittest.TestCase):
    """La vara que distingue un nombre PERDIDO de uno abreviado.

    Los cuatro casos de abajo son cuatro defectos reales que tuvo esta funcion el 25/07: un
    falso negativo (el que la motiva), dos falsos positivos por prefijo corto, y el `set` que
    daba por unico un nombre repetido en dos carpetas.
    """

    def test_abreviado_en_token_sigue_siendo_localizable(self):
        r = m.recuperable("00_INFORME_ANUAL_conclusiones.md",
                          "se escribio 00_INFORME_ANUAL con las abstracciones",
                          ["00_INFORME_ANUAL_conclusiones.md"])
        self.assertEqual(r, "00_INFORME_ANUAL")

    def test_palabra_corriente_no_cuenta_como_nombre(self):
        r = m.recuperable("escanear_ficheros.py", "hay que escalar el metodo por peldaños",
                          ["escanear_ficheros.py"])
        self.assertIsNone(r, "'esca' corta a mitad de palabra")

    def test_prefijo_ambiguo_no_lleva_a_ningun_fichero(self):
        r = m.recuperable("informe_julio.md", "se actualizo el informe_ del dia",
                          ["informe_julio.md", "informe_agosto.md"])
        self.assertIsNone(r)

    def test_mismo_nombre_en_dos_carpetas_no_es_unico(self):
        r = m.recuperable("README.md", "se escribio el README bilingue",
                          ["README.md", "README.md"])
        self.assertIsNone(r, "dos README: el prefijo no dice cual")

    def test_sin_indice_la_vara_no_se_aplica_y_no_rompe(self):
        # Contrato del parametro opcional: sin indice, `cob_localizable` == `cob_base`.
        regs = [rec_write("proyecto/00_PLANTEAMIENTO_largo.md")]
        d = m.medir_ventana(regs, "toque 00_PLANTEAMIENTO", con_secundarias=False)
        self.assertEqual(d["cob_localizable"], d["cob_base"])
        self.assertEqual(d["hit_prefijo"], 0)

    def test_con_indice_la_misma_ventana_sube(self):
        regs = [rec_write("proyecto/00_PLANTEAMIENTO_largo.md")]
        d = m.medir_ventana(regs, "toque 00_PLANTEAMIENTO", con_secundarias=False,
                            indice=["00_PLANTEAMIENTO_largo.md"], nombres=True)
        self.assertEqual(d["cob_base"], 0.0)          # el nombre entero NO esta
        self.assertEqual(d["cob_localizable"], 100.0)  # pero se vuelve a el
        self.assertEqual(d["faltan"], [])


class TestLoQueEncontroUnUsuarioNuevo(BaseDir):
    """Tres defectos que salieron cuando alguien se descargo esto y siguio el README literalmente.

    Ninguno lo habrian encontrado los casos de arriba, porque los de arriba prueban el interior y
    estos viven en la frontera: el comando de la portada, una linea de JSONL que nadie fabrica a
    mano, y el aviso que no se daba.
    """

    def test_el_comando_de_la_portada_acepta_un_fichero(self):
        """El README enseñaba `--sesion <ruta-al-jsonl>` y el programa solo aceptaba carpetas: el
        primer comando que ejecuta cualquiera fallaba el 100 % de las veces, en los dos idiomas."""
        self.jsonl("s.jsonl", [rec_write("C:/a/X.md"), rec_resumen("nombra X.md")])
        ruta = os.path.join(self.tmp, "s.jsonl")
        self.assertEqual(m.sesiones_en(ruta), [ruta])
        self.assertEqual(len(m.medir_todo(ruta)[0]), 1,
                         "medir un fichero suelto tiene que dar su ventana, igual que la carpeta")

    def test_un_fichero_que_no_es_jsonl_no_se_cuela(self):
        p = os.path.join(self.tmp, "notas.txt")
        io.open(p, "w", encoding="utf-8").write("esto no es una sesion")
        self.assertEqual(m.sesiones_en(p), [])

    def test_json_valido_que_no_es_objeto_no_tumba_la_lectura(self):
        """Una linea `[1,2,3]`, `null` o un numero suelto es JSON perfectamente valido, asi que
        pasa el json.loads y reventaba en `obj.get` con un AttributeError delante del usuario."""
        p = os.path.join(self.tmp, "raro.jsonl")
        with io.open(p, "w", encoding="utf-8") as fh:
            fh.write("[1, 2, 3]\n")
            fh.write("null\n")
            fh.write("42\n")
        self.assertEqual(m.ventanas_de_sesion(p), [],
                         "sin resumen no hay ventana, pero tampoco puede haber traceback")

    def test_una_linea_rara_no_esconde_las_buenas(self):
        """Control positivo del caso anterior: saltarse la basura no puede saltarse lo demas."""
        p = os.path.join(self.tmp, "mixta.jsonl")
        with io.open(p, "w", encoding="utf-8") as fh:
            fh.write("[1, 2, 3]\n")
            for r in (rec_write("C:/a/X.md"), rec_resumen("nombra X.md")):
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
        self.assertEqual(len(m.ventanas_de_sesion(p)), 1)




class TestUnCorteNoEsUnaAparicion(BaseDir):
    """El JSONL reescribe el mismo resumen una vez por cada prompt posterior.

    Medido el 25/07 sobre un historial real: 229 apariciones de `isCompactSummary` para 148 cortes,
    un 55 % de inflado en 22 ficheros. Entre dos copias solo cambia `promptId`. Contarlas todas abre
    ventanas que nunca existieron y saca el mismo resumen con seis porcentajes distintos.
    """

    def _res(self, uuid, txt):
        return {"isCompactSummary": True, "uuid": uuid, "message": {"content": txt}}

    def test_el_mismo_resumen_repetido_no_abre_ventana_nueva(self):
        self.jsonl("s.jsonl", [
            rec_write("C:/x/A.md"),
            self._res("u1", "nombra A.md"),
            rec_write("C:/y/B.py"),
            self._res("u1", "nombra A.md"),      # la copia: misma uuid, mismo texto
            self._res("u2", "segundo corte"),
        ])
        por_ventana, agg = m.medir_todo(self.tmp)
        self.assertEqual(agg["ventanas"], 2, "conto la copia como un corte mas")
        self.assertEqual(por_ventana[1]["nombres_distintos"], 1,
                         "la copia partio en dos la ventana del segundo corte")

    def test_dos_cortes_distintos_siguen_siendo_dos(self):
        """Control al reves: pasarse deduplicando borra cortes de verdad."""
        self.jsonl("s.jsonl", [rec_write("C:/x/A.md"), self._res("u1", "uno"),
                               rec_write("C:/y/B.py"), self._res("u2", "dos")])
        self.assertEqual(m.medir_todo(self.tmp)[1]["ventanas"], 2)


class TestFueraDeWindows(BaseDir):
    """La cifra de portada se hundia a 0 en Linux y Mac, sin dar error.

    `os.path.basename` parte segun el SISTEMA, no segun la ruta: en POSIX la contrabarra no es separador, asi
    que una ruta de Windows entera contaba como un nombre de veinte caracteres que no casa con
    nada. Un auditor lo midio el 25/07 y la cobertura de una ventana pasaba de 100 % a 0 % con el
    resumen nombrando los dos ficheros.
    """

    def test_nombre_de_parte_por_las_dos_barras(self):
        self.assertEqual(m.nombre_de(r"C:\proy\doc.md"), "doc.md")
        self.assertEqual(m.nombre_de("/home/ana/doc.md"), "doc.md")
        self.assertEqual(m.nombre_de(r"C:\proy/mezcladas\doc.md"), "doc.md")
        self.assertEqual(m.nombre_de("doc.md"), "doc.md")

    def test_rutas_de_windows_medidas_con_el_basename_POSIX(self):
        """Reproduce el fallo: se sustituye la funcion del sistema por la de POSIX, que es la que
        se ejecutaria en Mac. Si el codigo volviera a apoyarse en ella, este caso se pone rojo."""
        import posixpath
        real = os.path.basename
        try:
            os.path.basename = posixpath.basename
            self.jsonl("s.jsonl", [
                rec_write(r"C:\home\ana\proy\A.md"),
                rec_write(r"C:\home\ana\otro\B.py"),
                rec_resumen("el resumen nombra A.md y B.py"),
            ])
            d = m.medir_todo(self.tmp)[0][0]
            self.assertEqual(d["cob_base"], 100.0,
                             "en Linux o Mac esta medida se hunde: el basename no parte por \\")
        finally:
            os.path.basename = real


class TestNoVuelcaNombresSinPedirlo(BaseDir):
    """`--json` volcaba 1.025 nombres de ficheros privados sobre un historial real.

    Titulos de documentos, `.env.example`, nombres de persona dentro del titulo. El aviso hablaba
    de "conversaciones privadas y sus nombres", que se entiende como identificadores de sesion,
    porque es lo unico que saca el modo texto. Quien pegara esa salida en un issue publicaba su
    arbol de trabajo entero.
    """

    def test_por_defecto_sale_el_conteo_y_no_la_lista(self):
        self.jsonl("s.jsonl", [rec_write("C:/x/SECRETO_nomina.md"), rec_resumen("no lo nombra")])
        d = m.medir_todo(self.tmp)[0][0]
        self.assertEqual(d["faltan_n"], 1, "tiene que decir CUANTOS se perdieron")
        self.assertNotIn("faltan", d, "la lista de nombres no sale si nadie la pide")
        self.assertNotIn("SECRETO_nomina.md", json.dumps(d),
                         "el nombre del fichero privado se ha colado en la salida")

    def test_con_nombres_vuelve_la_lista(self):
        self.jsonl("s.jsonl", [rec_write("C:/x/SECRETO_nomina.md"), rec_resumen("no lo nombra")])
        d = m.medir_todo(self.tmp, con_nombres=True)[0][0]
        self.assertEqual(d["faltan"], ["SECRETO_nomina.md"])


class TestLaCapaQueElUsuarioEjECUTA(BaseDir):
    """`main()` no tenia un solo caso, y es lo unico que ejecuta quien se descarga esto.

    Un auditor lo midio con `sys.settrace` el 25/07: `main`, `imprimir` y `autodetectar_projects_dir`
    con CERO lineas ejecutadas por los veinte casos. Se podia dejar la cobertura media fija en 99 %
    o borrar el aviso de privacidad que el README promete, con la suite entera en verde.
    """

    def _correr(self, *args):
        """Devuelve (codigo, stdout, stderr) SEPARADOS, y esa separacion es la que se prueba.

        Los avisos van a stderr desde la ronda 10. Iban a stdout y por delante del JSON, asi que
        la salida en modo maquina no era JSON: `json.loads` daba "Expecting value: line 1". El
        caso que lo comprobaba pasaba `--projects-dir`, que esquiva justo ese aviso.
        """
        import contextlib
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                cod = m.main(list(args))
            except SystemExit as e:
                cod = e.code
        return cod, out.getvalue(), err.getvalue()

    def test_el_aviso_de_privacidad_sale_de_verdad(self):
        """El aviso va donde esta el riesgo, y por eso se comprueba en `--con-nombres`: es el
        modo que mete nombres de ficheros propios en la salida."""
        self.jsonl("s.jsonl", [rec_write("C:/x/A.md"), rec_resumen("no lo nombra")])
        _, salida, avisos = self._correr("--projects-dir", self.tmp, "--con-nombres", "--json")
        self.assertRegex(avisos.lower(), r"privacidad",
                         "el README promete que avisa, y esto es quien lo comprueba")
        json.loads(salida)   # y el aviso NO puede haber ensuciado la salida de maquina

    def test_la_cobertura_impresa_es_la_medida(self):
        """Que el numero de la pantalla salga del calculo y no de una constante."""
        self.jsonl("s.jsonl", [rec_write("C:/x/A.md"), rec_write("C:/y/B.py"),
                               rec_resumen("solo nombra A.md")])
        _, salida, _ = self._correr("--projects-dir", self.tmp)
        self.assertIn("50", salida, "1 de 2 nombres conservados son el 50 %, y no aparece")

    def test_json_es_json(self):
        self.jsonl("s.jsonl", [rec_write("C:/x/A.md"), rec_resumen("nombra A.md")])
        _, salida, _ = self._correr("--projects-dir", self.tmp, "--json")
        datos = json.loads(salida)
        self.assertIn("ventanas", datos)
        self.assertEqual(datos["agregado"]["ventanas"], 1)

    def test_los_dos_flags_de_origen_a_la_vez_se_rechazan(self):
        """Con un fichero que EXISTE, o el rechazo llega por el camino equivocado y el caso
        aprueba sin probar lo suyo: la mutacion que quita esa guarda sobrevivia."""
        self.jsonl("s.jsonl", [rec_write("C:/x/A.md"), rec_resumen("nombra A.md")])
        cod, salida, _ = self._correr("--sesion", os.path.join(self.tmp, "s.jsonl"),
                                      "--projects-dir", self.tmp)
        self.assertEqual(cod, 2)
        self.assertIn("Elige", salida, "rechazo, pero por otro motivo")

    def test_sesion_apuntando_a_una_carpeta_se_rechaza(self):
        cod, _, _ = self._correr("--sesion", self.tmp)
        self.assertEqual(cod, 2)

class TestHuecosQueDestapoLaMutacion(BaseDir):
    """Siete lineas que el banco no vigilaba, cada una con su caso.

    Salieron de ejecutar `mutar.py`: se sabotea una linea y se mira si algun caso se pone rojo. Las
    siete de aqui pasaban en verde con el codigo mintiendo, que es la definicion de hueco. Ninguna
    era un fallo: eran lineas sin nadie mirandolas.
    """

    def test_las_funciones_de_entidades_aguantan_registros_CRUDOS(self):
        """`rutas_escritas` y `texto_de_ventana` son API publica: un tercero las llama con lo que
        acaba de leer del JSONL, sin filtrar. Ahi llegan listas sueltas, `null` y numeros, que son
        JSON valido, y reventaban con AttributeError."""
        crudos = [[1, 2, 3], None, 42, "texto suelto",
                  rec_write("C:/x/A.md"), rec_texto("commit 1a2b3c4d")]
        self.assertEqual(m.rutas_escritas(crudos), ["C:/x/A.md"])
        self.assertIn("1a2b3c4d", m.texto_de_ventana(crudos))

    def test_la_ruta_completa_se_busca_tambien_en_barras_POSIX(self):
        """Un resumen escrito en Mac nombra `/home/ana/A.md`; el historial puede traer la ruta con
        contrabarras. Si solo se prueba una forma, la vara pesimista da cero y parece un dato."""
        self.jsonl("s.jsonl", [rec_write("/home/ana/A.md"),
                               rec_resumen("el resumen la escribe como " +
                                           chr(92) + "home" + chr(92) + "ana" +
                                           chr(92) + "A.md")])
        d = m.medir_todo(self.tmp)[0][0]
        self.assertEqual(d["hit_ruta"], 1, "no probo la ruta en la otra barra")

    def test_una_linea_que_no_es_objeto_no_entra_en_la_ventana(self):
        path = os.path.join(self.tmp, "s.jsonl")
        nl = chr(10)
        with io.open(path, "w", encoding="utf-8") as fh:
            fh.write("[1, 2, 3]" + nl)
            fh.write(json.dumps(rec_write("C:/x/A.md")) + nl)
            fh.write("null" + nl)
            fh.write(json.dumps(rec_resumen("nombra A.md")) + nl)
        d = m.medir_todo(self.tmp)[0][0]
        self.assertEqual(d["hit_base"], 1, "una linea rara tumbo la medida")

    def test_el_indice_llega_desde_el_CLI_y_la_vara_del_prefijo_se_aplica(self):
        """La cifra doble que el codigo anuncia (nombre entero contra localizable) no se podia
        reproducir: el llamador no pasaba indice, asi que `hit_prefijo` era 0 siempre."""
        self.jsonl("s.jsonl", [rec_write("proy/00_PLANTEAMIENTO_largo.md"),
                               rec_resumen("toque 00_PLANTEAMIENTO")])
        d = m.medir_todo(self.tmp)[0][0]
        self.assertEqual(d["cob_base"], 0.0)
        self.assertEqual(d["hit_prefijo"], 1, "el indice no llego: la vara buena no se aplico")
        self.assertEqual(d["cob_localizable"], 100.0)

    def test_un_hash_de_seis_hex_no_es_un_commit(self):
        """Seis digitos hex es cualquier cosa: un color CSS, un trozo de id. Con el limite en seis,
        el denominador se llena de basura y la cobertura de commits baja sola."""
        self.jsonl("s.jsonl", [rec_texto("el color 1a2b3c y el commit 1a2b3c4d"),
                               rec_write("C:/x/A.md"),
                               rec_resumen("menciona 1a2b3c4d")])
        d = m.medir_todo(self.tmp)[0][0]
        self.assertEqual(d["commit_total"], 1, "conto un hex de seis como commit")
        self.assertEqual(d["commit_hit"], 1)

    def test_un_identificador_necesita_DOS_mayusculas(self):
        """`A-001` es una viñeta o una talla. `ABC-001` es un identificador de dominio."""
        self.jsonl("s.jsonl", [rec_texto("mira A-001 y tambien ABC-001"),
                               rec_write("C:/x/A.md"),
                               rec_resumen("nada de eso")])
        d = m.medir_todo(self.tmp)[0][0]
        self.assertEqual(d["id_total"], 1, "conto A-001 como identificador")

    def test_la_cobertura_por_nombre_se_divide_entre_NOMBRES(self):
        """Dos rutas con el mismo basename: por nombre es 1 de 1, no 1 de 2. Dividir entre rutas
        mezcla la vara optimista con la pesimista y da un numero que no es ninguna de las dos."""
        self.jsonl("s.jsonl", [rec_write("C:/a/SKILL.md"), rec_write("C:/b/SKILL.md"),
                               rec_resumen("el resumen dice SKILL.md")])
        d = m.medir_todo(self.tmp)[0][0]
        self.assertEqual(d["cob_base"], 100.0)
        self.assertEqual(d["cob_ruta"], 0.0)



class TestLasNueveQueSobrevivieron(BaseDir):
    """Nueve mutaciones que un esceptico externo escribio y el banco no cazo.

    LA LECCION, antes que los casos: el mutador lo habia escrito yo, y probaba lo que yo ya sabia
    que habia que probar. Catorce sabotajes propios, catorce cazados, cero huecos, y otro venia con
    doce distintos de los que sobrevivieron nueve. Un mutador escrito por el autor hereda el punto
    ciego del autor; el numero que da no mide la calidad del banco, mide el acuerdo entre dos
    cosas que salieron de la misma cabeza.
    """

    def _edit(self, ruta, viejo="a", nuevo="b"):
        return {"message": {"content": [{"type": "tool_use", "name": "Edit",
                                         "input": {"file_path": ruta, "old_string": viejo,
                                                   "new_string": nuevo}}]}}

    def _notebook(self, ruta):
        return {"message": {"content": [{"type": "tool_use", "name": "NotebookEdit",
                                         "input": {"file_path": ruta, "new_source": "x"}}]}}

    def test_Edit_y_NotebookEdit_cuentan_como_escritura(self):
        """La mas cara de las nueve. Los 38 casos fabricaban sus trazas SOLO con `Write`, asi que
        dejar el codigo contando unicamente `Write` no ponia rojo nada. En el historial real hay
        11.777 llamadas a `Edit` frente a 4.186 de `Write`: la cifra de portada se movia un 38 %
        con la suite entera en verde."""
        self.jsonl("s.jsonl", [self._edit("C:/x/A.md"), self._notebook("C:/y/B.ipynb"),
                               rec_resumen("nombra A.md y B.ipynb")])
        d = m.medir_todo(self.tmp)[0][0]
        self.assertEqual(d["nombres_distintos"], 2, "una edicion no cuenta como escritura")

    def test_la_dedup_va_por_uuid_y_no_por_texto(self):
        """Dos cortes DISTINTOS con el mismo texto son dos cortes: pasa cuando una sesion repite
        el mismo trabajo. Deduplicar por texto los funde y se pierde el segundo con lo suyo."""
        a = {"isCompactSummary": True, "uuid": "u1", "message": {"content": "mismo texto"}}
        b = {"isCompactSummary": True, "uuid": "u2", "message": {"content": "mismo texto"}}
        self.jsonl("s.jsonl", [rec_write("C:/x/A.md"), a, rec_write("C:/y/B.py"), b])
        por_ventana, agg = m.medir_todo(self.tmp)
        self.assertEqual(agg["ventanas"], 2, "fundio dos cortes distintos por parecerse el texto")

    def test_el_emparejamiento_distingue_mayusculas(self):
        """`README.md` y `readme.md` son ficheros distintos en Linux. Emparejar sin distinguir
        infla la cobertura con aciertos que no lo son."""
        self.jsonl("s.jsonl", [rec_write("C:/x/DECISIONES.md"),
                               rec_resumen("el resumen escribe decisiones.md en minuscula")])
        d = m.medir_todo(self.tmp)[0][0]
        self.assertEqual(d["hit_base"], 0, "conto un acierto cambiando mayusculas por minusculas")

    def test_un_resumen_multibloque_se_lee_ENTERO(self):
        """El resumen puede venir en varios bloques de texto. Quedarse con el primero pierde la
        mitad y baja la cobertura sin motivo, que es el sintoma que el README atribuye a un
        cambio de formato."""
        res = {"isCompactSummary": True, "uuid": "u1", "message": {"content": [
            {"type": "text", "text": "primera parte, nombra A.md"},
            {"type": "text", "text": "segunda parte, nombra B.py"}]}}
        self.jsonl("s.jsonl", [rec_write("C:/x/A.md"), rec_write("C:/y/B.py"), res])
        d = m.medir_todo(self.tmp)[0][0]
        self.assertEqual(d["hit_base"], 2, "se quedo con el primer bloque del resumen")

    def test_un_isCompactSummary_falso_no_abre_ventana(self):
        """El campo puede venir `false` o `null` en registros corrientes. Tratarlo como resumen
        parte la sesion en ventanas inventadas."""
        self.jsonl("s.jsonl", [{"isCompactSummary": False, "message": {"content": "no soy resumen"}},
                               rec_write("C:/x/A.md"),
                               rec_resumen("nombra A.md")])
        por_ventana, agg = m.medir_todo(self.tmp)
        self.assertEqual(agg["ventanas"], 1, "un falso abrio ventana")
        self.assertEqual(por_ventana[0]["hit_base"], 1)

    def test_con_nombres_llega_de_verdad_hasta_el_dato(self):
        """El flag existia y se podia volver inerte sin que nada se quejara."""
        self.jsonl("s.jsonl", [rec_write("C:/x/SOLO_MIO.md"), rec_resumen("no lo nombra")])
        _, salida, _ = self._correr_json("--projects-dir", self.tmp, "--json", "--con-nombres")
        self.assertIn("SOLO_MIO.md", salida, "el flag no llego al dato")

    def test_la_pantalla_no_intercambia_las_dos_varas(self):
        """La optimista va por nombre y la pesimista por ruta. Intercambiarlas en pantalla
        sobrevivia porque el unico caso que miraba lo impreso buscaba un numero suelto."""
        self.jsonl("s.jsonl", [rec_write("C:/a/SKILL.md"), rec_write("C:/b/SKILL.md"),
                               rec_resumen("el resumen dice SKILL.md")])
        _, salida, _ = self._correr_json("--projects-dir", self.tmp)
        # La linea del agregado tambien dice "por nombre": se filtra por la sangria de la ficha.
        lineas = [l for l in salida.splitlines()
                  if l.startswith("    por nombre") or l.startswith("    por ruta")]
        self.assertEqual(len(lineas), 2, "no se ven las dos varas")
        self.assertIn("100%", [l for l in lineas if "por nombre" in l][0],
                      "la vara optimista no es la de nombre")
        self.assertIn("0%", [l for l in lineas if "por ruta" in l][0],
                      "la vara pesimista no es la de ruta")

    def test_el_agregado_cuenta_las_sesiones_que_hay(self):
        """UNA sesion con DOS cortes, y no dos sesiones con uno: con un corte por fichero, contar
        ventanas y contar sesiones da el mismo numero y la mutacion pasa por el medio."""
        self.jsonl("a.jsonl", [rec_write("C:/x/A.md"),
                               {"isCompactSummary": True, "uuid": "u1",
                                "message": {"content": "nombra A.md"}},
                               rec_write("C:/y/B.py"),
                               {"isCompactSummary": True, "uuid": "u2",
                                "message": {"content": "nombra B.py"}}])
        agg = m.medir_todo(self.tmp)[1]
        self.assertEqual(agg["ventanas"], 2)
        self.assertEqual(agg["sesiones"], 1, "conto una sesion por ventana")

    def test_una_ruta_acabada_en_separador_no_da_nombre_vacio(self):
        """La cadena vacia esta contenida en cualquier resumen, asi que esa entidad puntuaria
        siempre y la pantalla lo presentaria como un 100 % medido."""
        self.assertEqual(m.nombre_de("C:/x/carpeta/"), "carpeta")
        self.jsonl("s.jsonl", [rec_write("C:/x/carpeta/"),
                               rec_resumen("el resumen no nombra nada de eso")])
        d = m.medir_todo(self.tmp)[0][0]
        self.assertEqual(d["hit_base"], 0, "una entidad vacia puntuo contra cualquier texto")

    def test_el_indice_lleva_TODOS_los_nombres(self):
        """Si el indice se queda con uno, la vara del prefijo deja de distinguir un prefijo util
        de uno ambiguo, que es justo lo que esa funcion documenta."""
        self.jsonl("s.jsonl", [rec_write("proy/00_INFORME_ANUAL_conclusiones.md"),
                               rec_write("otro/00_INFORME_ANUAL_anexos.md"),
                               rec_resumen("toque 00_INFORME_ANUAL")])
        d = m.medir_todo(self.tmp)[0][0]
        self.assertEqual(d["hit_prefijo"], 0,
                         "un prefijo que lleva a DOS ficheros no localiza ninguno")

    def _correr_json(self, *args):
        import contextlib
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                cod = m.main(list(args))
            except SystemExit as e:
                cod = e.code
        return cod, out.getvalue(), err.getvalue()


class TestLoQueDestapoLaAuditoriaExterna(unittest.TestCase):
    """Dos defectos que 48 casos y 23 sabotajes no vieron, porque no miraban ahi.

    Los 48 casos son de fonteria: parseo, deduplicacion, partir rutas, banderas, privacidad,
    portabilidad. Ninguno preguntaba si lo que se cuenta es lo que se dice contar. Un auditor
    externo hizo esa pregunta el 26/07/2026 y salieron estas dos.
    """

    def test_un_tramo_de_UUID_no_es_un_hash_de_commit(self):
        """La clase de commits venia sesgada hacia abajo por construccion.

        `\\b` trata el guion como frontera, asi que cada tramo de un UUID de nombre de sesion
        pasaba por hash. Y un tramo de UUID no aparece nunca en un resumen, luego entraba en
        el denominador y jamas en el numerador. Sobre cinco ventanas reales, cuatro de los
        veintitres "hashes" contados eran esto.
        """
        uuid = "6424de57-b64d-4b55-aa59-43a9aa7625cb"
        self.assertEqual(m.RE_COMMIT.findall(uuid), [],
                         "un UUID sigue aportando hashes falsos al denominador")
        # Control positivo: si el patron se rompe del todo, el caso de arriba pasa igual.
        self.assertEqual(m.RE_COMMIT.findall("el commit 1d36d8e lo arregla"), ["1d36d8e"],
                         "el patron ha dejado de ver un hash corto de verdad")
        largo = "429fc19a1b2c3d4e5f60718293a4b5c6d7e8f901"
        self.assertEqual(m.RE_COMMIT.findall(largo), [largo],
                         "el patron ha dejado de ver un hash completo de 40")
        self.assertEqual(m.RE_COMMIT.findall("a74dd00b0653d7683 no es un hash"), [],
                         "17 caracteres no es una longitud que git emita")

    def test_la_salida_dice_que_la_cobertura_no_es_dano(self):
        """El aviso vivia en un cursor privado, o sea en ningun sitio para quien la instala.

        La herramienta imprime un porcentaje que se lee solo como perdida. Lo medido es lo
        contrario: de veintiun cortes, veinte sin perdida real. Si el numero sale por consola,
        su limite tiene que salir por consola.
        """
        import io as _io
        import contextlib
        agregado = {"sesiones": 1, "ventanas": 1, "ventanas_con_escrituras": 1,
                    "nombres_conservados_min": 3, "nombres_conservados_max": 9,
                    "cobertura_media_base": 67.0}
        buf = _io.StringIO()
        with contextlib.redirect_stdout(buf):
            m.imprimir([], agregado, "C:/no/importa")
        salida = buf.getvalue().lower()
        self.assertIn("no es cuanto trabajo se pierde", salida,
                      "la salida publica una cobertura sin decir que no es dano")
        self.assertIn("commiteado", salida,
                      "la salida no dice que lo que protege es commitear")


if __name__ == "__main__":
    unittest.main(verbosity=2)
