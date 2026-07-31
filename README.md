# compact-retention

Mide qué sobrevive al resumen automático de un contexto largo en Claude Code, leyendo solo el JSONL de
sesión. Sin instalar nada y sin hooks propios. **El medidor lo ejecutas tú sobre tus sesiones; la serie
de veintisiete cortes que hay más abajo salió de una instalación privada y esa no la puedes repetir.**

*Measures what survives the automatic summary of a long context in Claude Code, reading only the session
JSONL. No install, no custom hooks. **You run the measurer on your own sessions; the twenty-seven-cut
series below comes from a private install and that part you cannot replay.***

---

## Español

### El problema
Cuando una sesión de Claude Code llena su ventana de contexto, se dispara un auto-compact: el historial se
sustituye por un resumen y el trabajo continúa. La pregunta práctica es cuánto se conserva de verdad. Un
resumen que olvida los ficheros que tocaste, o el paso en el que ibas, te obliga a re-derivarlo.

### Qué mide
Por cada corte, compara la ventana previa contra el resumen que la reemplazó:
- cobertura: qué fracción de las entidades de la ventana aparece literal en el resumen;
- recuento absoluto de nombres conservados, que es donde se ve el techo del resumen.

Las entidades son las rutas de fichero escritas en la ventana (`Write`/`Edit`/`MultiEdit`/`NotebookEdit`).
Como clases secundarias, los hashes de commit y los identificadores de dominio (`ABC-001`) del texto.

### Por qué lee solo el JSONL
El JSONL de sesión ya contiene, en orden, los turnos previos al corte y el mensaje marcado
`isCompactSummary`. Las dos mitades de la medición salen del mismo fichero, así que no hace falta ningún
hook de sellado. Una sesión con varios cortes se trocea sola: cada `isCompactSummary` cierra una ventana.

### Uso

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

### La palanca: dónde cortar y por qué aquí el corte está al 60 %

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

Leído de corrido parece que doblar el umbral cuesta veintisiete puntos de conservación. No es eso lo
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

### Cómo se midió

Los seis pasos del método están en **[METODO.md](METODO.md)**, con el fallo que enseñó cada uno.
Empiezan por el que más caro salió: el primer corte automático interrumpió la instalación del
instrumento que debía medirlo, y su bitácora vacía se leyó como «no ha ocurrido».

### Lo que puede romper esto

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

### Los límites que debes conocer

**Un corte no es una aparición.** El JSONL reescribe el mismo mensaje de resumen una vez por cada
turno posterior: entre dos copias solo cambia un identificador interno. Sobre un historial real, medido el
27/07/2026, hay **234 apariciones para 153 cortes**, un 53 % de inflado repartido en 22 ficheros. Esta
herramienta las deduplica; si escribes la tuya, ese es el primer sitio donde se tuerce la cifra.

**Las escrituras de subagente engordan el denominador.** Un agente lanzado en paralelo escribe
ficheros que el resumen del hilo principal nunca iba a nombrar, porque no son suyos. Aquí no se
distinguen, así que la cobertura sale algo más baja de lo que corresponde.

### El límite del emparejamiento
El emparejamiento de rutas es por nombre de fichero. Dos rutas distintas con el mismo nombre
(`SKILL.md`) se unen y el porcentaje sale **optimista**. Se informa aparte el recuento por ruta
completa, que es el **pesimista**. La verdad está entre los dos y por eso se publican los dos
números.

---

## English

### The problem
When a Claude Code session fills its context window, an auto-compact fires: the history is replaced by a
summary and work continues. The practical question is how much actually survives. A summary that forgets
the files you touched, or the step you were on, forces you to reconstruct it.

### What it measures
For each cut, it compares the pre-cut window against the summary that replaced it:
- coverage: what fraction of the window's entities appears verbatim in the summary;
- absolute count of preserved names, which is where the summary's ceiling shows.

Entities are the file paths written in the window (`Write`/`Edit`/`MultiEdit`/`NotebookEdit`), plus commit
hashes and domain identifiers (`ABC-001`) found in the text as secondary classes.

### Why it reads only the JSONL
The session JSONL already contains, in order, the turns before the cut and the message flagged
`isCompactSummary`. Both halves of the measurement come from one file, so no sealing hook is needed. A
session with several cuts splits itself: each `isCompactSummary` closes a window.

### Usage

If you do not use Claude Code, or want to see the program work before pointing it at
anything of your own:

```bash
python medir_compacts_generico.py --demo
```

It builds a toy session in a temp folder, measures it and deletes it. It announces what the
result will be before printing it, so you can check: three files written, the summary names two.

On your own sessions:

```bash
python medir_compacts_generico.py --sesion "path/to/session-file.jsonl"
```
Claude Code sessions live under `~/.claude/projects/<encoded-cwd>/<uuid>.jsonl`, so to see which
ones you have, run `ls ~/.claude/projects`. Keep the quotes around the path: Claude Code builds that
folder name from your working directory and it can contain spaces. To measure a whole folder at
once, use `--projects-dir`.

What it prints is shown in the Spanish half above, dated **27 July 2026** on one real history: the
program prints in Spanish, so the block is not duplicated here. Yours will differ, and so will mine
next week, because the history grows with every session. Two lines to read it: `Cobertura media` is
the mean coverage by name, and `banda de 1 a 29` is the range of names any one summary kept.

The last two paragraphs are always printed. On its own the number reads as loss. It is not: of the
twenty-seven cuts this author has measured one by one, **twenty-three** lost nothing that could not
be recovered from git or from disk. In the other four something was really lost, six files in
total. This used to say "of the twenty-six, twenty-five". That "all but one" shape had been dragged along
for three versions without being measured again. A skeptic caught it by running the measurer
instead of reading the text. Four out of twenty-seven is still few, but it is four times more than
what was being published.

**With no arguments it reads your ENTIRE history**, every project at once, because that is the
default. Nothing leaves your machine, but these are private conversations and their names are
printed, so it is worth knowing before the first curious run. The program says so.

### The lever: where to cut and why this setup cuts at 60 %

Claude Code compacts only when the window is nearly full. The factory threshold is the window minus
a margin, which on this install is 987,000 tokens out of a million, 98.7 %. The four peaks measured
before changing anything were 997,956 · 997,369 · 994,163 · 970,036, between 97.0 % and 99.8 %
occupancy. The problem is not that it summarises. It is that by the time it does, you have been
working with a saturated context for a long while. The cut is moved earlier with two environment
variables, both documented at
[code.claude.com/docs/en/env-vars](https://code.claude.com/docs/en/env-vars):

```json
{
  "env": {
    "CLAUDE_CODE_AUTO_COMPACT_WINDOW": "1000000",
    "CLAUDE_AUTOCOMPACT_PCT_OVERRIDE": "60"
  }
}
```

The percentage only applies when the window is declared. It never raises the threshold: it lowers it
or does nothing. It takes effect on restart, so the running session keeps cutting where it did. None of this is a discovery, it is in the official docs. What this repository adds is the
measurement behind the choice of percentage.

**Why 60 and not 30.** At `30` the cuts landed between 292,755 and 294,027 tokens; at `60`, between
580,370 and 588,381. The reason to raise it was not summary quality but reasoning quality: the model
works worse with a very full context, and 600k was the estimated edge of the good zone on this
install. Cutting at 300k left half of the usable bandwidth unused.

**And this is where the measurement earns its keep**, because the result is not the intuitive one.
Twenty-one automatic cuts, same yardstick, across the three regimes:

```
default    ~987k   n=4    preserved 46 %   names per window 29.0
override 30 ~292k  n=5    preserved 88 %   names per window 10.2
override 60 ~585k  n=12   preserved 61 %   names per window 27.5
```

The override-60 row went from n=11 to n=12 on the afternoon of 27/07, with a cut that landed after
this was written and preserved little. It is said here because the series grows on its own, and a
published table ages every time the author works.

Read straight, doubling the threshold looks like it costs twenty-seven points. That is not what the
data says. Those windows carried nearly three times as many names. That is the variable that rules:

```
correlation between window density (distinct names) and % preserved, n=27
   Pearson  -0.77
   Spearman -0.75
```

The twenty-one in the table are the **automatic** cuts, the only ones that say anything about the
threshold. The correlation uses all twenty-seven measured windows, those twenty-one plus six manual cuts:
manual cuts tell you nothing about the threshold, but they do inform the density relationship. Two
yardsticks that do not assume the same shape of relationship point the same way. And in the only
density band where both regimes overlap, 19 to 25 names per window, there is **a single window from
the low cut, at 65 %, against three from the high one, between 50 % and 96 %**. That sample cannot
separate the threshold effect from the density effect.

Saying so matters. An earlier version of this paragraph called those "means", with one window on
one side and three on the other.

**One figure in this table was published wrong, and the reason is worth knowing.** The window of 24
July at 10:52 was counted under the default regime, and its real cut was 292,789 tokens, that is
override 30. The cause: every other row carries its cut in the label and that one did not, so
grouping by label sent it to the wrong bucket. With it in place, the default regime goes from 56 %
to 46 % and the low one from 85 % to 88 %. **The thesis does not fall, it gets stronger**, and a
reviewer found it by cross-checking the label against the logbook, not the instrument.

So the advice the data supports is not the one it started from. Moving the cut earlier works
indirectly, by letting fewer files fit in a window. Attacking density is cheaper and costs no
context: a committed file stops depending on the summary, because `git log` brings it back.

You do not choose how dense the work is. You do choose when to commit.

**What cutting earlier costs.** Every cycle pays a fixed toll before writing a line (system prompt,
tools, skill descriptions, context files): 69,213 tokens measured on 23 July 2026, and between
70,000 and 71,000 across the last ten sessions. Against the default cut that is 7.0 %; against a cut
at 292k it becomes 23.6 %, because the same toll is paid 3.4 times as often. That is the reason not
to lower the percentage further than your case needs.

The figures in this section come from one install, July 2026, one-million window. Yours will differ.

**And it must be said which of this you can reproduce.** The script shipped in this repository
measures summary coverage and nothing else. The regime table, the density correlation and the
startup toll come from two other measurers that live on the author's install and **are not published
here**: they are reproducible in method, not in a command. What you do run as-is is
`medir_compacts_generico.py` over your own history, which tells you whether your install behaves
like this one.

### How this was measured

The six steps live in **[METODO.md](METODO.md)**, each with the failure that taught it. They start
with the most expensive one: the first automatic cut interrupted the installation of the very
instrument meant to measure it, and its empty log read as «it did not happen».

### What can break this

The Claude Code documentation states, about the files this tool reads, that **the entry format is
internal and changes between versions, so scripts that parse them directly can break on any
release**. The page is
[code.claude.com/docs/en/sessions](https://code.claude.com/docs/en/sessions). It recommends `/export`
or the script interfaces instead.

This tool does exactly what that paragraph advises against, and you should know before leaning on
its numbers:

- Tested against Claude Code 2.x, July 2026. If the format changes, what you see is a count
  dropping for no reason, not an error. That is why the test suite builds its own traces and never
  reads your real history.
- Your transcripts are deleted after 30 days by default (`cleanupPeriodDays`). Any "since the
  beginning" measurement has that floor, and a compact from three months ago can no longer be
  measured: its transcript is gone. **This applies to the figures above:** the install they come from has
  that value set to 3650, which disables the deletion. With the factory thirty days there would not
  be enough history to reach fifty-one sessions.
- `CLAUDE_CONFIG_DIR` moves the whole folder out of `~/.claude`, and
  `CLAUDE_CODE_SKIP_PROMPT_HISTORY` stops them from being written at all.
- The transcript is written asynchronously, so the last seconds of a live session may not be on
  disk yet.

### The limits worth stating

**A cut is not an appearance.** The JSONL rewrites the same summary message once per later turn:
between two copies only an internal identifier changes. On one real history, measured on 27 July 2026, that meant **234
appearances for 153 cuts**, a 53 % inflation spread over 22 files. This tool deduplicates them. If
you write your own, that is the first place the number goes wrong.

**Subagent writes inflate the denominator.** An agent launched in parallel writes files the main
thread's summary was never going to name, because they are not its own. They are not told apart
here, so coverage comes out slightly lower than it should.

### The matching limit
Path matching is by file basename. Two different paths sharing a name (`SKILL.md`) merge, and the
percentage comes out **optimistic**. The count by full path is reported separately as the **pessimistic**
figure. The truth sits between them, which is why both numbers ship.

---

## Tests
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

## Requisitos / Requirements
Python 3.9+. Solo biblioteca estándar: ni pytest ni nada que instalar. Ese 3.9 está **certificado**
desde el 27/07/2026: nueve trabajos en verde, con 3.9, 3.11 y 3.13 sobre Windows, Linux y Mac.
Hasta esa mañana aquí ponía «declarado, no certificado», y era cierto. Dejó de serlo con el primer
push y siguió publicado unas horas: una nota de humildad caduca igual que una cifra. Esta caducó
en la dirección que hace parecer el repositorio peor de lo que es.

Python 3.9+, standard library only: no pytest, nothing to install. That 3.9 is **certified** as of
27/07/2026: nine green jobs across 3.9, 3.11 and 3.13 on Windows, Linux and Mac. Until that morning
this line read «declared, not certified», which was true. It was true when written and stopped being true on the
first push, yet it stayed up for hours. A note of humility goes stale like any other figure. This
one went stale towards the side that makes the repository look worse than it is.

## Licencia / License
MIT. Ver [LICENSE](LICENSE).
