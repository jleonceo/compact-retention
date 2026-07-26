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
aparecen por pantalla, así que conviene saberlo antes de la primera ejecución curiosa. El programa
lo avisa.

### Lo que puede romper esto

La documentación de Claude Code dice, sobre los ficheros que esta herramienta lee, que **el formato
de cada entrada es interno y cambia entre versiones, de modo que un programa que los lea
directamente puede dejar de funcionar en cualquier actualización**. Lo dice en
[code.claude.com/docs/en/sessions](https://code.claude.com/docs/en/sessions). Ahí recomienda usar
`/export` o las interfaces de script en su lugar.

Esta herramienta hace justo lo que ahí se desaconseja, y conviene saberlo antes de apoyarse en sus
números:

- **Probada contra Claude Code 2.x**, en julio de 2026. Si el formato cambia, lo que verás es un
  recuento que baja sin motivo, no un error: por eso el banco fabrica sus propias trazas y no
  depende de tu historial.
- **Tus transcripts se borran a los 30 días** por defecto (`cleanupPeriodDays`). Cualquier medición
  «desde siempre» tiene ese suelo, y una regla dada de alta hace tres meses no se puede medir desde
  su alta.
- `CLAUDE_CONFIG_DIR` mueve la carpeta entera fuera de `~/.claude`, y
  `CLAUDE_CODE_SKIP_PROMPT_HISTORY` deja de escribirlos.
- El transcript se escribe de forma asíncrona, así que los últimos segundos de una sesión viva
  pueden no estar todavía en disco.

### Los límites que hay que decir

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
python test_medir_compacts_generico.py    # 50 casos
python mutar.py                           # 24 sabotajes contra esos 50 casos
```


El segundo comando es el que da derecho a fiarse del primero. Sabotea el codigo a proposito,
una linea cada vez, y exige que la suite se ponga roja. Un sabotaje que nadie caza no es un
fallo del codigo: es una linea que ningun caso vigila. Hoy son veinticuatro de veinticuatro, cero huecos.
La primera vez que se paso, doce de dieciocho sobrevivian: se podia dejar la cobertura media
clavada en 99 % con los veinte casos de entonces en verde.

## Requisitos / Requirements
Python 3.9+. Solo biblioteca estandar: ni pytest ni nada que instalar.
Python 3.9+, standard library only: no pytest, nothing to install.

## Licencia / License
MIT. Ver [LICENSE](LICENSE).
