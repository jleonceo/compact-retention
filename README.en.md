Versión en español: [README.md](README.md)

# compact-retention

[![ci](https://github.com/jleonceo/compact-retention/actions/workflows/ci.yml/badge.svg)](https://github.com/jleonceo/compact-retention/actions/workflows/ci.yml)

Measures what survives the automatic summary of a long context in Claude Code, reading only the session
JSONL. No install, no custom hooks. **You run the measurer on your own sessions; the twenty-seven-cut
series below comes from a private install and that part you cannot replay.**

## The problem
When a Claude Code session fills its context window, an auto-compact fires: the history is replaced by a
summary and work continues. The practical question is how much actually survives. A summary that forgets
the files you touched, or the step you were on, forces you to reconstruct it.

## What it measures
For each cut, it compares the pre-cut window against the summary that replaced it:
- coverage: what fraction of the window's entities appears verbatim in the summary;
- absolute count of preserved names, which is where the summary's ceiling shows.

Entities are the file paths written in the window (`Write`/`Edit`/`MultiEdit`/`NotebookEdit`), plus commit
hashes and domain identifiers (`ABC-001`) found in the text as secondary classes.

## Why it reads only the JSONL
The session JSONL already contains, in order, the turns before the cut and the message flagged
`isCompactSummary`. Both halves of the measurement come from one file, so no sealing hook is needed. A
session with several cuts splits itself: each `isCompactSummary` closes a window.

## Usage

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

## The lever: where to cut and why this setup cuts at 60 %

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

## How this was measured

The six steps live in **[METODO.md](METODO.md)**, each with the failure that taught it. They start
with the most expensive one: the first automatic cut interrupted the installation of the very
instrument meant to measure it, and its empty log read as «it did not happen».

## What can break this

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

## The limits worth stating

**A cut is not an appearance.** The JSONL rewrites the same summary message once per later turn:
between two copies only an internal identifier changes. On one real history, measured on 27 July 2026, that meant **234
appearances for 153 cuts**, a 53 % inflation spread over 22 files. This tool deduplicates them. If
you write your own, that is the first place the number goes wrong.

**Subagent writes inflate the denominator.** An agent launched in parallel writes files the main
thread's summary was never going to name, because they are not its own. They are not told apart
here, so coverage comes out slightly lower than it should.

## The matching limit
Path matching is by file basename. Two different paths sharing a name (`SKILL.md`) merge, and the
percentage comes out **optimistic**. The count by full path is reported separately as the **pessimistic**
figure. The truth sits between them, which is why both numbers ship.

## Tests

```bash
python test_medir_compacts_generico.py    # 62 cases
python mutar.py                           # 28 sabotages against those 62 cases
```

The second command is what entitles you to trust the first. It sabotages the code on purpose, one line at a
time, and demands that the suite turns red. Today all twenty-eight are caught, zero gaps; a twenty-ninth, which
changes no decision, has to come out uncaught, as the harness's own negative control.

## Requirements

Python 3.9+, standard library only: no pytest, nothing to install. That 3.9 is **certified** as of
27/07/2026: nine green jobs across 3.9, 3.11 and 3.13 on Windows, Linux and Mac. Until that morning
this line read «declared, not certified», which was true. It was true when written and stopped being true on the
first push, yet it stayed up for hours. A note of humility goes stale like any other figure. This
one went stale towards the side that makes the repository look worse than it is.

## Licence

MIT. See [LICENSE](LICENSE).
