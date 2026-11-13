English version: [README.en.md](README.en.md)

# compact-retention

Mide qué sobrevive al resumen automático de un contexto largo en Claude Code, leyendo solo el JSONL de
sesión. Sin instalar nada y sin hooks propios. **El medidor lo ejecutas tú sobre tus sesiones; la serie
de veintisiete cortes que hay más abajo salió de una instalación privada y esa no la puedes repetir.**

## El problema
Cuando una sesión de Claude Code llena su ventana de contexto, se dispara un auto-compact: el historial se
sustituye por un resumen y el trabajo continúa. La pregunta práctica es cuánto se conserva de verdad. Un
resumen que olvida los ficheros que tocaste, o el paso en el que ibas, te obliga a re-derivarlo.

## Qué mide
Por cada corte, compara la ventana previa contra el resumen que la reemplazó:
- cobertura: qué fracción de las entidades de la ventana aparece literal en el resumen;
- recuento absoluto de nombres conservados, que es donde se ve el techo del resumen.

Las entidades son las rutas de fichero escritas en la ventana (`Write`/`Edit`/`MultiEdit`/`NotebookEdit`).
Como clases secundarias, los hashes de commit y los identificadores de dominio (`ABC-001`) del texto.

## Por qué lee solo el JSONL
El JSONL de sesión ya contiene, en orden, los turnos previos al corte y el mensaje marcado
`isCompactSummary`. Las dos mitades de la medición salen del mismo fichero, así que no hace falta ningún
hook de sellado. Una sesión con varios cortes se trocea sola: cada `isCompactSummary` cierra una ventana.

## Uso

Si no usas Claude Code, o quieres ver el programa funcionar antes de apuntarlo a nada tuyo:

```bash
python medir_compacts_generico.py --demo
```

Fabrica una sesión de juguete en un temporal, la mide y la borra. Anuncia lo que va a salir antes
de salir, para que se pueda comprobar: tres ficheros escritos, el resumen nombra dos.

Sobre tus propias sesiones:

```bash
python medir_compacts_generico.py --sesion "ruta/al/fichero-de-sesion.jsonl"
```
Las sesiones de Claude Code viven en `~/.claude/projects/<cwd-codificado>/<uuid>.jsonl`, así que
para ver cuáles tienes:

```bash
ls ~/.claude/projects
```

Deja las comillas de la ruta: el nombre de la carpeta lo genera Claude Code a partir de tu
directorio de trabajo y puede traer espacios. Para medir una carpeta entera de golpe,
`--projects-dir`.

Lo que devuelve. Esta salida es la del **27/07/2026** sobre un historial real; el tuyo dará otros
números, y el mío también dentro de una semana, porque el historial crece con cada sesión:

```
------------------------------------------------------------------------------
AGREGADO: 51 sesiones, 153 ventanas (149 con escrituras).
Nombres de fichero conservados por el resumen: banda de 1 a 29.
Cobertura media (por nombre): 67%.
Ahí vive la tesis del TECHO: el resumen conserva un número acotado de nombres,
no un porcentaje fijo; cuanto más grande la ventana, menor la fracción.

QUÉ NO ES ESTE NÚMERO: no es cuánto trabajo se pierde. Mide en cuántas cosas
te repartías, no cuánto daño hizo el corte. Lo que protege lo que importa es
haberlo commiteado, no que el resumen acierte a nombrarlo.

PARA QUÉ SIRVE: es un termómetro comparativo, no una nota absoluta. Mide el mismo
historial antes y después de mover el umbral del auto-compact, o un día contra
otro. El README explica las dos variables que mueven ese umbral y qué salió al
medirlas.
------------------------------------------------------------------------------
```

Los dos últimos párrafos salen siempre. Están ahí porque la cifra se lee sola como pérdida. No lo
es: de los veintisiete cortes que este autor lleva medidos uno por uno, **veintitrés** no perdieron
nada que no se pudiera recuperar de git o del disco. En los otros cuatro se perdió algo de verdad,
seis ficheros en total. Cuatro sobre veintisiete sigue siendo poco, pero es cuatro veces más de lo que se publicaba.

**Sin ningún argumento lee TODO tu historial**, de todos los proyectos a la vez, porque ese es el
valor por defecto. No sale nada de tu ordenador, pero son conversaciones privadas y sus nombres
aparecen por pantalla, así que más vale que lo sepas antes de tu primera ejecución por curiosidad. El programa
lo avisa.

## La palanca: dónde cortar y por qué aquí el corte está al 60 %

Claude Code compacta solo cuando la ventana está casi llena. El umbral de fábrica es la ventana
menos un margen, que en esta instalación son 987.000 tokens sobre un millón, el 98,7 %. Los cuatro
picos medidos antes de tocar nada fueron 997.956, 997.369, 994.163 y 970.036, entre el 97,0 % y el
99,8 % de ocupación.

El problema no es que resuma. Es que para cuando resume llevas mucho rato trabajando con el
contexto saturado. El corte se adelanta con dos variables de entorno, ambas documentadas en
[code.claude.com/docs/en/env-vars](https://code.claude.com/docs/en/env-vars):

```json
{
  "env": {
    "CLAUDE_CODE_AUTO_COMPACT_WINDOW": "1000000",
    "CLAUDE_AUTOCOMPACT_PCT_OVERRIDE": "60"
  }
}
```

El porcentaje solo actúa cuando la ventana va declarada y solo puede bajar el umbral, nunca
subirlo. Entra al reiniciar Claude Code: la sesión en curso sigue cortando donde cortaba. Esto no es
un hallazgo de nadie, está en la documentación oficial. Lo que aporta este repositorio es el número
medido detrás de la elección del porcentaje.

**Por qué 60 y no 30.** Con `30` los cortes cayeron entre 292.755 y 294.027 tokens; con `60`, entre
580.370 y 588.381. La razón de subirlo no fue la calidad del resumen sino la del razonamiento: el
modelo trabaja peor con el contexto muy lleno, y 600k era la estimación del borde de la zona buena
en esta instalación. Cortar a 300k dejaba sin usar la mitad del ancho de banda aprovechable.

**Y aquí es donde hace falta el medidor**, porque lo que sale no es lo que uno diría. Veintiún cortes
automáticos medidos con la misma vara, repartidos en los tres regímenes:

```
por defecto ~987k   n=4    conservado 46 %   nombres por ventana 29,0
override 30 ~292k   n=5    conservado 88 %   nombres por ventana 10,2
override 60 ~585k   n=12   conservado 61 %   nombres por ventana 27,5
```

Leído seguido parece que doblar el umbral cuesta veintisiete puntos de conservación. No es eso lo
que dice el dato. Esas ventanas llevaban casi el triple de nombres dentro. La variable que manda
es esa:

```
correlación densidad (nombres distintos en la ventana) contra % conservado, n=27
   Pearson  −0,77
   Spearman −0,75
```

Los veintiuno de la tabla son los cortes **automáticos**, que son los únicos que dicen algo sobre el
umbral. La correlación usa las veintisiete ventanas medidas, o sea esos veintiuno más seis cortes
manuales: al umbral no lo tocan, y a la relación entre densidad y conservación sí la informan. Dos
varas que no dependen de la misma forma de la relación apuntan al mismo sitio. Y en la única
banda de densidad donde los dos regímenes se solapan, de 19 a 25 nombres por ventana, hay **una
sola ventana del corte bajo, al 65 %, contra tres del alto, entre el 50 % y el 96 %**. Con esa
muestra no se puede separar el efecto del umbral del efecto de la densidad.

**Una cifra de esta tabla estuvo mal publicada y conviene saber por qué.** La ventana del 24/07 a
las 10:52 estaba contada en el régimen por defecto. Su corte real fue de 292.789 tokens, o sea
override 30. La causa: las etiquetas de las demás filas llevan su corte escrito y esa no, así que
al agrupar por etiqueta se fue al grupo equivocado. Con ella en su sitio, el régimen por defecto
pasa de 56 % a 46 % y el bajo de 85 % a 88 %. **La tesis no se cae, se refuerza**. El fallo lo
encontró un revisor cruzando la etiqueta contra la bitácora. El instrumento no lo vio.

Así que el consejo que sale del dato no es el que parecía al empezar. Adelantar el corte funciona de
forma indirecta, porque hace que quepan menos ficheros en cada ventana. Atacar la densidad sale más
barato y no cuesta contexto: un fichero commiteado deja de depender del resumen porque lo repone
`git log`.

La densidad del trabajo no se elige. El momento del commit sí.

**Lo que cuesta adelantar el corte.** Cada ciclo paga un peaje fijo antes de escribir una línea
(prompt de sistema, herramientas, descripciones de skills y ficheros de contexto): 69.213 tokens
medidos el 23/07/2026 y entre 70.000 y 71.000 en las últimas diez sesiones. Sobre el corte por
defecto eso es el 7,0 %; sobre un corte en 292k pasa a ser el 23,6 %, porque el mismo peaje se paga
3,4 veces más a menudo. Es la razón para no bajar el porcentaje más de lo que pide tu caso.

Las cifras de este apartado son de una instalación concreta, julio de 2026 y ventana de un millón.
La tuya dará otras.

**Y hay que decir qué de esto puedes reproducir tú.** El script que viaja en este repositorio mide
la cobertura del resumen y nada más. La tabla de regímenes, la correlación con la densidad y el
peaje de arranque salen de otros dos medidores que viven en la instalación del autor y **no se
publican aquí**: son reproducibles en método, aunque no en un comando. Lo que sí ejecutas tal cual es
`medir_compacts_generico.py` sobre tu propio historial, que es lo que te dice si tu instalación se
comporta como esta.

## Cómo se midió

Los seis pasos del método están en **[METODO.md](METODO.md)**, con el fallo que enseñó cada uno.
Empiezan por el que más caro salió: el primer corte automático interrumpió la instalación del
instrumento que debía medirlo, y su bitácora vacía se leyó como «no ha ocurrido».

## Lo que puede romper esto

La documentación de Claude Code dice, sobre los ficheros que esta herramienta lee, que **el formato
de cada entrada es interno y cambia entre versiones, de modo que un programa que los lea
directamente puede dejar de funcionar en cualquier actualización**. Lo dice en
[code.claude.com/docs/en/sessions](https://code.claude.com/docs/en/sessions). Ahí recomienda usar
`/export` o las interfaces de script en su lugar.

Esta herramienta hace justo lo que ahí se desaconseja y lo sabes antes de apoyarte en sus
números:

- Probada contra Claude Code 2.x, en julio de 2026. Si el formato cambia, lo que verás es un
  recuento que baja sin motivo en vez de un error: por eso el banco fabrica sus propias trazas y no
  depende de tu historial.
- Tus transcripts se borran a los 30 días por defecto (`cleanupPeriodDays`). Cualquier medición
  «desde siempre» tiene ese suelo, y un corte de hace tres meses ya no se puede medir: su transcript
  no está. **Y esto vale para las cifras de aquí arriba:** la instalación de la que salen tiene ese
  valor puesto en 3650, o sea el borrado desactivado. Con los treinta días de fábrica no habría
  historial suficiente para llegar a cincuenta y una sesiones.
- `CLAUDE_CONFIG_DIR` mueve la carpeta entera fuera de `~/.claude`, y
  `CLAUDE_CODE_SKIP_PROMPT_HISTORY` deja de escribirlos.
- El transcript se escribe de forma asíncrona, así que los últimos segundos de una sesión viva
  pueden no estar todavía en disco.

## Los límites que debes conocer

**Un corte no es una aparición.** El JSONL reescribe el mismo mensaje de resumen una vez por cada
turno posterior: entre dos copias solo cambia un identificador interno. Sobre un historial real, medido el
27/07/2026, hay **234 apariciones para 153 cortes**, un 53 % de inflado repartido en 22 ficheros. Esta
herramienta las deduplica; si escribes la tuya, ese es el primer sitio donde se tuerce la cifra.

**Las escrituras de subagente engordan el denominador.** Un agente lanzado en paralelo escribe
ficheros que el resumen del hilo principal nunca iba a nombrar, porque no son suyos. Aquí no se
distinguen, así que la cobertura sale algo más baja de lo que corresponde.

## El límite del emparejamiento
El emparejamiento de rutas es por nombre de fichero. Dos rutas distintas con el mismo nombre
(`SKILL.md`) se unen y el porcentaje sale **optimista**. Se informa aparte el recuento por ruta
completa, que es el **pesimista**. La verdad está entre los dos y por eso se publican los dos
números.

## Pruebas

```bash
python test_medir_compacts_generico.py    # 62 casos
python mutar.py                           # 28 sabotajes contra esos 62 casos
```



El segundo comando es el que da derecho a fiarse del primero. Sabotea el código a propósito, una
línea cada vez, para exigir que la suite se ponga roja. Un sabotaje que nadie caza no es un fallo del
código: es una línea que ningún caso vigila. Hoy son veintiocho de veintiocho, cero huecos.

Y hay un sabotaje número veintinueve que **tiene que salir hueco**: alarga un comentario y no cambia
ni una decisión del programa. Es el control negativo del propio arnés, y va dentro del bucle, con la
copia de seguridad puesta, para que sufra exactamente lo mismo que los otros veintiocho. Sin él, un
arnés que solo sabe decir «cazada» no demuestra que ve: puede estar poniendo la suite en rojo por un
motivo suyo y firmar un pleno. Le pasó al repositorio hermano, y lo encontró una auditoría de fuera
porque aquí todos los verificadores son el objeto verificado.

*El origen de este banco está escrito en la cabecera de `mutar.py`: el 25/07/2026 un escéptico pasó
dieciocho mutaciones a mano contra una suite de veinte casos y **sobrevivieron doce**. Se podía dejar
la cobertura clavada en el 99 %, o borrar el aviso de privacidad que este README promete, con los
veinte casos en verde. De ahí salen los veintiocho sabotajes de hoy.*

## Requisitos

Python 3.9+. Solo biblioteca estándar: ni pytest ni nada que instalar. Ese 3.9 está **certificado**
desde el 27/07/2026: nueve trabajos en verde, con 3.9, 3.11 y 3.13 sobre Windows, Linux y Mac.
Hasta esa mañana aquí ponía «declarado, no certificado», y era cierto. Dejó de serlo con el primer
push y siguió publicado unas horas: una nota de humildad caduca igual que una cifra. Esta caducó
en la dirección que hace parecer el repositorio peor de lo que es.

## Licencia

MIT. Ver [LICENSE](LICENSE).
