# compact-retention

Mide qué sobrevive al resumen automático de un contexto largo en Claude Code, leyendo solo el JSONL de
sesión. Sin instalar nada, sin hooks propios, reproducible por cualquiera.

*Measures what survives the automatic summary of a long context in Claude Code, reading only the session
JSONL. No install, no custom hooks, reproducible by anyone.*

---

## Español

### El problema
Cuando una sesión de Claude Code llena su ventana de contexto, se dispara un auto-compact: el historial se
sustituye por un resumen y el trabajo continúa. La pregunta práctica es cuánto se conserva de verdad. Un
resumen que olvida los ficheros que tocaste, o el paso en el que ibas, te obliga a re-derivarlo.

### Qué mide
Por cada corte, compara la ventana previa contra el resumen que la reemplazó:
- **cobertura**: qué fracción de las entidades de la ventana aparece literal en el resumen;
- **recuento absoluto de nombres conservados**, que es donde se ve el techo del resumen.

Las entidades son las rutas de fichero escritas en la ventana (`Write`/`Edit`/`MultiEdit`/`NotebookEdit`),
y como clases secundarias los hashes de commit y los identificadores de dominio (`ABC-001`) del texto.

### Por qué lee solo el JSONL
El JSONL de sesión ya contiene, en orden, los turnos previos al corte y el mensaje marcado
`isCompactSummary`. Las dos mitades de la medición salen del mismo fichero, así que no hace falta ningún
hook de sellado. Una sesión con varios cortes se trocea sola: cada `isCompactSummary` cierra una ventana.

### Uso
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

Lo que devuelve. Esta salida es la del **26/07/2026** sobre un historial real; el tuyo dará otros
números, y el mío también dentro de una semana, porque el historial crece con cada sesión:

```
------------------------------------------------------------------------------
AGREGADO: 50 sesiones, 149 ventanas (145 con escrituras).
Nombres de fichero conservados por el resumen: banda de 1 a 29.
Cobertura media (por nombre): 67%.
Ahi vive la tesis del TECHO: el resumen conserva un numero acotado de nombres,
no un porcentaje fijo; cuanto mas grande la ventana, menor la fraccion.

QUE NO ES ESTE NUMERO: no es cuanto trabajo se pierde. Mide en cuantas cosas
te repartias, no cuanto dano hizo el corte. Lo que protege lo que importa es
haberlo commiteado, no que el resumen acierte a nombrarlo.
------------------------------------------------------------------------------
```

Ese último párrafo sale siempre, y está ahí porque la cifra se lee sola como pérdida. No lo es. De
veintitrés cortes medidos, veintidós no perdieron nada que no se pudiera recuperar.

**Sin ningún argumento lee TODO tu historial**, de todos los proyectos a la vez, porque ese es el
valor por defecto. No sale nada de tu ordenador, pero son conversaciones privadas y sus nombres
aparecen por pantalla, así que más vale que lo sepas antes de tu primera ejecución por curiosidad. El programa
lo avisa.

### La palanca: dónde cortar y por qué aquí el corte está al 60 %

Claude Code compacta solo cuando la ventana está casi llena. Los cuatro cortes medidos en esta
instalación antes de tocar nada cayeron en 997.956, 997.369, 994.163 y 970.036 tokens sobre una
ventana de un millón, o sea al 98,7 % de ocupación. El problema no es que resuma: es que para cuando
resume llevas mucho rato trabajando con el contexto saturado.

El corte se adelanta con dos variables de entorno, ambas documentadas en
[code.claude.com/docs/en/env-vars](https://code.claude.com/docs/en/env-vars):

```json
{
  "env": {
    "CLAUDE_CODE_AUTO_COMPACT_WINDOW": "1000000",
    "CLAUDE_AUTOCOMPACT_PCT_OVERRIDE": "60"
  }
}
```

El porcentaje solo actúa cuando la ventana va declarada, y solo puede bajar el umbral, nunca
subirlo. Entra al reiniciar Claude Code: la sesión en curso sigue cortando donde cortaba. Esto no es
un hallazgo de nadie, está en la documentación oficial. Lo que aporta este repositorio es el número
medido detrás de la elección del porcentaje.

**Por qué 60 y no 30.** Con `30` el corte real cayó en 292.755 tokens; con `60`, en 585.370. La
razón de subirlo no fue la calidad del resumen sino la del razonamiento: el modelo trabaja peor con
el contexto muy lleno, y 600k era la estimación del borde de la zona buena en esta instalación.
Cortar a 300k dejaba sin usar la mitad del ancho de banda aprovechable.

**Y aquí es donde hace falta el medidor**, porque lo que sale no es lo que uno diría. Diecinueve
cortes automáticos medidos con la misma vara, repartidos en los tres regímenes:

```
por defecto ~987k   n=5    conservado 56 %   nombres por ventana 23,8
override 30 ~292k   n=4    conservado 85 %   nombres por ventana 12,0
override 60 ~585k   n=10   conservado 66 %   nombres por ventana 26,7
```

Leído de corrido parece que doblar el umbral cuesta diecinueve puntos de conservación. No es eso lo
que dice el dato. Esas ventanas llevaban más del doble de nombres dentro, y la variable que manda es
esa:

```
correlación densidad (nombres distintos en la ventana) contra % conservado, n=25
   Pearson  −0,76
   Spearman −0,76
```

Los diecinueve de la tabla son los cortes **automáticos**, que son los únicos que dicen algo sobre
el umbral. La correlación usa las veinticinco ventanas medidas, o sea esos diecinueve más seis
cortes manuales: al umbral no lo tocan, y a la relación entre densidad y conservación sí la
informan.

Dos varas que no dependen de la misma forma de la relación apuntan al mismo sitio. Y en el único
tramo de densidad donde los dos regímenes se solapan, de 19 a 25 nombres por ventana, las medias son
65 % con el corte bajo y 71 % con el alto, o sea indistinguibles con esta muestra. La diferencia
global mide cuánto trabajo cabía en cada ventana. El sitio del corte apenas interviene.

Así que el consejo que sale del dato no es el que parecía al empezar. Adelantar el corte funciona de
forma indirecta, porque hace que quepan menos ficheros en cada ventana. Atacar la densidad sale más
barato y no cuesta contexto: un fichero commiteado deja de depender del resumen porque lo repone
`git log`. La densidad del trabajo no se elige. El momento del commit sí.

**Lo que cuesta adelantar el corte.** Cada sesión paga un peaje fijo antes de escribir una línea
(prompt de sistema, herramientas, descripciones de skills y ficheros de contexto): 69.213 tokens en
esta instalación. Con el corte por defecto eso era el 7,5 % del ciclo; con el corte en 292k pasa a
ser el 23,6 %, porque el mismo peaje se paga 3,4 veces más a menudo. Es la razón para no bajar el
porcentaje más de lo que pide tu caso.

Las cifras de este apartado son de una instalación concreta, julio de 2026 y ventana de un millón.
La tuya dará otras, y el medidor de este repositorio es justamente lo que hace falta para saber
cuáles.

### Cómo se midió: la parte reutilizable

Lo de arriba son los resultados. Esto es cómo se consiguieron. El orden de los pasos importa
más que la herramienta. Se puede copiar en cualquier medición parecida. Fueron tres días, y dos y medio
de ellos se fueron en medir en vez de en configurar.

**1. Instrumentar antes de tocar nada.** Un hook que se dispara en el corte y sella el transcript
entero más el estado de git. Sin eso, cada compact es un suceso del que solo queda una impresión.
La lección vino por las malas: el primer auto-compact **interrumpió literalmente la instalación del
instrumento que debía medirlo**, entró 55,9 segundos antes de que el hook quedara registrado, y su
bitácora vacía se leyó como «no ha ocurrido». De ahí sale una regla que vale para cualquier
instrumento: si nació después de la ventana que dice cubrir, **su silencio no es evidencia**.

**2. Una sola vara para todos los casos.** Las cinco primeras medidas se hicieron cada una a su
manera. Una contaba ficheros escritos que el resumen nombra; otra, ficheros sin commitear que el
resumen nombra. Puestas en fila dibujaban un desplome que no existía. Cifra bien calculada sobre
objeto distinto sigue siendo falsa, y encima con aire de rigor.

**3. Escribir la predicción antes de ver el resultado.** Antes de subir el umbral se dejó escrito
dónde tenía que caer el corte: entre 585.000 y 600.000 tokens. Cayó en 580.370, o sea que **la
predicción falló por un 0,8 %** y quedó escrita en su sitio. Una predicción que se ajusta después de
ver el dato no es una predicción.

**4. Refutar la hipótesis rival antes de celebrar la propia.** Existe un mecanismo documentado que,
de estar actuando aquí, habría invalidado el trabajo entero. Se descartó con dato propio: actúa
sobre el 90 % de ocupación y los cuatro cortes medidos caían en el 98,7 %.

**5. Publicar la corrección encima de la versión anterior, sin borrarla.** Con siete ventanas medidas
la conclusión era que el resumen tiene un techo fijo de nueve a diecisiete nombres, pasara lo que
pasara. Con diecinueve se cayó: dos ventanas conservaron 21 y 28. Con veinticinco, la variable que
manda resultó ser la densidad. La tesis del techo estaba escrita y publicada, y sigue escrita al
lado de lo que la corrige, porque un registro que borra sus versiones anteriores no enseña cómo se
corrige una medición.

**6. Un baseline que se está midiendo no admite dos ejecuciones a la vez.** El error más caro de la
serie casi no se ve: un proceso de fondo que no imprime nada no está parado, así que se relanzó, y
los dos quedaron vivos escribiendo el mismo fichero de referencia. En medio se cambió el código bajo
medición. El segundo habría sobrescrito el «antes» con cifras del «después», el diff habría salido
plano y **nada lo habría delatado**: dos ficheros con el nombre correcto y el contenido
intercambiado no disparan ninguna alarma. Se cazó mirando los procesos por otro motivo.

### Lo que puede romper esto

La documentación de Claude Code dice, sobre los ficheros que esta herramienta lee, que **el formato
de cada entrada es interno y cambia entre versiones, de modo que un programa que los lea
directamente puede dejar de funcionar en cualquier actualización**. Lo dice en
[code.claude.com/docs/en/sessions](https://code.claude.com/docs/en/sessions). Ahí recomienda usar
`/export` o las interfaces de script en su lugar.

Esta herramienta hace justo lo que ahí se desaconseja, y lo sabes antes de apoyarte en sus
números:

- **Probada contra Claude Code 2.x**, en julio de 2026. Si el formato cambia, lo que verás es un
  recuento que baja sin motivo en vez de un error: por eso el banco fabrica sus propias trazas y no
  depende de tu historial.
- **Tus transcripts se borran a los 30 días** por defecto (`cleanupPeriodDays`). Cualquier medición
  «desde siempre» tiene ese suelo, y una regla que diste de alta hace tres meses no la puedes medir desde
  su alta.
- `CLAUDE_CONFIG_DIR` mueve la carpeta entera fuera de `~/.claude`, y
  `CLAUDE_CODE_SKIP_PROMPT_HISTORY` deja de escribirlos.
- El transcript se escribe de forma asíncrona, así que los últimos segundos de una sesión viva
  pueden no estar todavía en disco.

### Los límites que debes conocer

**Un corte no es una aparición.** El JSONL reescribe el mismo mensaje de resumen una vez por cada
turno posterior: entre dos copias solo cambia un identificador interno. Sobre un historial real se
contaron **230 apariciones para 149 cortes**, un 54 % de inflado repartido en 22 ficheros. Esta
herramienta las deduplica; si escribes la tuya, ese es el primer sitio donde se tuerce la cifra.

**Las escrituras de subagente engordan el denominador.** Un agente lanzado en paralelo escribe
ficheros que el resumen del hilo principal nunca iba a nombrar, porque no son suyos. Aquí no se
distinguen, así que la cobertura sale algo más baja de lo que corresponde.

### El límite del emparejamiento
El emparejamiento de rutas es por nombre de fichero. Dos rutas distintas con el mismo nombre
(`SKILL.md`) se unen, y el porcentaje sale **optimista**. Se informa aparte el recuento por ruta
completa, que es el **pesimista**. La verdad está entre los dos, y por eso se publican los dos
números.

---

## English

### The problem
When a Claude Code session fills its context window, an auto-compact fires: the history is replaced by a
summary and work continues. The practical question is how much actually survives. A summary that forgets
the files you touched, or the step you were on, forces you to reconstruct it.

### What it measures
For each cut, it compares the pre-cut window against the summary that replaced it:
- **coverage**: what fraction of the window's entities appears verbatim in the summary;
- **absolute count of preserved names**, which is where the summary's ceiling shows.

Entities are the file paths written in the window (`Write`/`Edit`/`MultiEdit`/`NotebookEdit`), plus commit
hashes and domain identifiers (`ABC-001`) found in the text as secondary classes.

### Why it reads only the JSONL
The session JSONL already contains, in order, the turns before the cut and the message flagged
`isCompactSummary`. Both halves of the measurement come from one file, so no sealing hook is needed. A
session with several cuts splits itself: each `isCompactSummary` closes a window.

### Usage
```bash
python medir_compacts_generico.py --sesion "path/to/session-file.jsonl"
```
Claude Code sessions live under `~/.claude/projects/<encoded-cwd>/<uuid>.jsonl`, so to see which
ones you have, run `ls ~/.claude/projects`. Keep the quotes around the path: Claude Code builds that
folder name from your working directory and it can contain spaces. To measure a whole folder at
once, use `--projects-dir`.

What it prints is the output of **26 July 2026** on one real history. Yours will differ, and so will
mine next week, because the history grows with every session.

That last paragraph is always printed. On its own the number reads as loss. It is not. Of
twenty-three cuts measured, twenty-two lost nothing that could not be recovered.

**With no arguments it reads your ENTIRE history**, every project at once, because that is the
default. Nothing leaves your machine, but these are private conversations and their names are
printed, so it is worth knowing before the first curious run. The program says so.

### The lever: where to cut and why this setup cuts at 60 %

Claude Code compacts only when the window is nearly full. The four cuts measured on this install
before changing anything landed at 997,956 · 997,369 · 994,163 · 970,036 tokens on a one-million
window, that is at 98.7 % occupancy. The problem is not that it summarises. It is that by the time
it does, you have been working with a saturated context for a long while.

The cut is moved earlier with two environment variables, both documented at
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

**Why 60 and not 30.** At `30` the real cut landed at 292,755 tokens; at `60`, at 585,370. The
reason to raise it was not summary quality but reasoning quality: the model works worse with a very
full context, and 600k was the estimated edge of the good zone on this install. Cutting at 300k left
half of the usable bandwidth unused.

**And this is where the measurement earns its keep**, because the result is not the intuitive one.
Nineteen automatic cuts, same yardstick, across the three regimes:

```
default    ~987k   n=5    preserved 56 %   names per window 23.8
override 30 ~292k  n=4    preserved 85 %   names per window 12.0
override 60 ~585k  n=10   preserved 66 %   names per window 26.7
```

Read straight, doubling the threshold looks like it costs nineteen points. That is not what the data
says. Those windows carried more than twice as many names. That is the variable that rules:

```
correlation between window density (distinct names) and % preserved, n=25
   Pearson  -0.76
   Spearman -0.76
```

The nineteen in the table are the **automatic** cuts, the only ones that say anything about the
threshold. The correlation uses all twenty-five measured windows, those nineteen plus six manual
cuts: manual cuts tell you nothing about the threshold, but they do inform the density relationship.

Two yardsticks that do not assume the same shape of relationship point the same way. In the only
density band where both regimes overlap, 19 to 25 names per window, the means are 65 % with the low
cut and 71 % with the high one, indistinguishable at this sample size. The global gap measures how
much work fitted in each window. Where the cut sat barely matters.

So the advice the data supports is not the one it started from. Moving the cut earlier works
indirectly, by letting fewer files fit in a window. Attacking density is cheaper and costs no
context: a committed file stops depending on the summary, because `git log` brings it back. You do
not choose how dense the work is. You do choose when to commit.

**What cutting earlier costs.** Every session pays a fixed toll before writing a line (system
prompt, tools, skill descriptions, context files): 69,213 tokens on this install. Under the default
cut that was 7.5 % of the cycle; with the cut at 292k it becomes 23.6 %, because the same toll is
paid 3.4 times as often. That is the reason not to lower the percentage further than your case
needs.

The figures in this section come from one install, July 2026, one-million window. Yours will differ,
and the measurer in this repository is exactly what tells you by how much.

### How this was measured: the reusable part

Everything above is results. This is how they were reached. The order of the steps matters
more than the tool does. It transfers to any similar measurement. It took three days, two and a
half of them spent measuring rather than configuring.

**1. Instrument before touching anything.** A hook that fires on the cut and seals the whole
transcript plus the git state. Without that, each compact is an event you only have an impression
of. The lesson came the hard way: the first auto-compact **literally interrupted the installation of
the instrument meant to measure it**, landing 55.9 seconds before the hook was registered, and its
empty log was read as "it never happened". Hence a rule that holds for any instrument: if it was
born after the window it claims to cover, **its silence is not evidence**.

**2. One yardstick for every case.** The first five measurements were each done their own way. One
counted written files named by the summary; another, uncommitted files named by the summary. Lined
up, they drew a collapse that did not exist. A figure computed correctly over a different object is
still false, with an air of rigour on top.

**3. Write the prediction before seeing the result.** Before raising the threshold, where the cut
had to land was written down: between 585,000 and 600,000 tokens. It landed at 580,370, so **the
prediction missed by 0.8 %**. It stayed on the record. A prediction adjusted after seeing the
data is not a prediction.

**4. Refute the rival hypothesis before celebrating your own.** A documented mechanism exists that,
had it been active here, would have invalidated the whole effort. It was ruled out with local data:
it acts at 90 % occupancy and the four measured cuts landed at 98.7 %.

**5. Publish the correction on top of the earlier version, without deleting it.** With seven windows
measured, the conclusion was that the summary has a fixed ceiling of nine to seventeen names, no
matter what. With nineteen it fell: two windows kept 21 and 28. With twenty-five, the variable that
rules turned out to be density. The ceiling claim was written and published. It still sits next
to what corrects it, because a record that deletes its earlier versions cannot teach how a
measurement gets corrected.

**6. A baseline being measured does not allow two runs at once.** The costliest mistake in the
series is nearly invisible: a background process printing nothing is not a stalled process, so it
got relaunched, and both stayed alive writing the same reference file. Meanwhile the code under
measurement was changed. The second run would have overwritten the "before" with "after" figures,
the diff would have come out flat, and **nothing would have flagged it**: two files with the right
names and swapped contents raise no alarm. It was caught while looking at processes for an
unrelated reason.

### What can break this

The Claude Code documentation states, about the files this tool reads, that **the entry format is
internal and changes between versions, so scripts that parse them directly can break on any
release**. The page is
[code.claude.com/docs/en/sessions](https://code.claude.com/docs/en/sessions). It recommends `/export`
or the script interfaces instead.

This tool does exactly what that paragraph advises against, and you should know before leaning on
its numbers:

- **Tested against Claude Code 2.x**, July 2026. If the format changes, what you see is a count
  dropping for no reason, not an error. That is why the test suite builds its own traces and never
  reads your real history.
- **Your transcripts are deleted after 30 days** by default (`cleanupPeriodDays`). Any "since the
  beginning" measurement has that floor.
- `CLAUDE_CONFIG_DIR` moves the whole folder out of `~/.claude`, and
  `CLAUDE_CODE_SKIP_PROMPT_HISTORY` stops them from being written at all.
- The transcript is written asynchronously, so the last seconds of a live session may not be on
  disk yet.

### The limits worth stating

**A cut is not an appearance.** The JSONL rewrites the same summary message once per later turn:
between two copies only an internal identifier changes. On one real history that meant **230
appearances for 149 cuts**, a 54 % inflation spread over 22 files. This tool deduplicates them. If
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
python test_medir_compacts_generico.py    # 51 casos
python mutar.py                           # 24 sabotajes contra esos 51 casos
```


El segundo comando es el que da derecho a fiarse del primero. Sabotea el código a propósito, una
línea cada vez, y exige que la suite se ponga roja. Un sabotaje que nadie caza no es un fallo del
código: es una línea que ningún caso vigila. Hoy son veinticuatro de veinticuatro, cero huecos. La
primera vez que se pasó sobrevivían doce de dieciocho, o sea que se podía dejar la cobertura media
clavada en el 99 % con los veinte casos de entonces en verde.

## Requisitos / Requirements
Python 3.9+. Solo biblioteca estándar: ni pytest ni nada que instalar.
Python 3.9+, standard library only: no pytest, nothing to install.

## Licencia / License
MIT. Ver [LICENSE](LICENSE).
