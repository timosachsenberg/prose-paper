# benchmarks/summaries: tables, numbers and figures of the benchmark

`benchmarks/summarize.py` and this package turn the raw tables of a benchmark work folder into every summary
number, table and figure of the paper. This is the "summaries" step that `datasets/DATASETS.md` §4.5 listed as not
scripted (DS:812). Citation keys used here and in the docstrings:
- DS = `datasets/DATASETS.md`
- B = `benchmarks/bench.py`
- OT = `benchmarks/overtuning.py`
- SPEC = the design document of this package (section numbers, outputs O1-O26, checks C1-C25, OPEN questions Qn).
  It is kept with the validation records outside the repository; the rules it fixed are in the code, the tests and
  the defaults listed at the end of this README.

What it does:
- Reads the work folder W written by `bench.py`:
  - `counts.tsv`, `coverage.tsv`, `timings.tsv`, `versions.txt` and `commands.log`;
  - `overtuning_<level>.tsv` and, when present, `counts_qgrid.tsv`;
  - the logs under `W/out/`;
  - the run table `benchmarks/runs.tsv` and the parameter files.
- Checks those inputs against the fixed design in `design.py`. An input that breaks the design stops the run with
  exit 2, and the message names the file, line, column, value and allowed set.
- Builds the outputs O1-O26 in four modules:
  - `ids.py`: identifications;
  - `fdp.py`: entrapment FDP;
  - `timing.py`: speed and memory;
  - `calib.py`: supplements.
  The over-tuning outputs reuse `overtuning.py` as it is.
- Writes the outputs as TSV tables, `numbers.tsv`/`numbers.tex` and the over-tuning sentences.
- Runs about 25 consistency checks into `check_report.txt`.
- Draws the figures from the written tables only.

The arithmetic uses the standard library only (`math.fsum`, `statistics`) on Python 3.10+. Only `figures.py`
imports matplotlib, and it does so lazily. Without matplotlib the tables are still built and the report gets a WARN.

## Layout

| File | Role |
|---|---|
| `../summarize.py` | entry point: CLI, build order, `numbers.tsv/.tex`, `provenance.tsv`, `--test` |
| `design.py` | fixed design: groups → kind/class/grade/instrument/order, arms and engines, batch order, reference map, display names |
| `tables.py` | loaders and validation, the shared context `Ctx`, comparison sets, timing attempts, statistics helpers, atomic writes, SHA256 |
| `ids.py` | O1, O2, O3, O4-O7 glue, O8, O9, O9b, O10 counts part, O14, O23, O24, O25 |
| `fdp.py` | O11, O12, O13, O26, and the FDP of any search as O11 computes it (`fdp_as_o11`, `run_of`, `search_fdp`) |
| `timing.py` | O10 time part, O15, O15b, O16, O17, O18 |
| `calib.py` | O19 (with the MSFragger/ProSE/Sage log parsers), O20, O21 |
| `checks.py` | the consistency layer → `check_report.txt` |
| `figures.py` | the only module that imports matplotlib; reads only `<out>/tables/*.tsv` |
| `tests/` | unittest suite and `fixtures/` (the fixture generators are `fixtures/make_*.py`) |

Module contract:
1. `tables.load` builds the context `Ctx`.
2. `fdp.build`, `ids.build`, `timing.build` and `calib.build` run in that order. Each module is imported lazily, and
   an exception in one module becomes `FAIL MODULE <name>` with the traceback in `<out>/errors.txt`. The other
   modules still run.
3. `checks.run` runs, then `numbers.tsv/.tex` and `provenance.tsv` are written.
4. `figures.draw` runs last, unless `--no-figures` is given.

Modules share data only through `ctx.shared` and the functions of `fdp.py`.

## How to run it

Always run it with `python3 -B`, so that no bytecode lands in the repository (`summarize.py` also sets
`sys.dont_write_bytecode`).

**Main work folder W** (the engine node, or a copy of W):

```sh
python3 -B benchmarks/summarize.py --work W --out OUT \
    --machine W=W/../node_prep/machine.txt --expect-threads 64 [--listing W.ls] [--strict]
```

- `--out` defaults to `W/summary`. Files are written atomically (tmp + `os.replace`).
- The run removes only files under its own names: `O??_*` tables of an earlier build that a full build no longer
  writes (INFO STALE; kept under `--only`), and `fig_*` files of figures that are now skipped, with their paper copies.
- `--expect-threads N`: the thread count of `per_file`, its arms and `batch`. Under `--strict` the default is 16.
  Both trials ran at 64.
- `--machine LABEL=PATH` (repeatable): the `node_prep/machine.txt` of each node, for O18. A path that does not exist
  stops the run (exit 2). No machine file for W, or for a separate S, gives a WARN(s) O18.
- `--listing F`: an `ls -l` listing of W, for check C18 on copies, whose mtimes are the copy time.
- `--strict`: final-run mode, which turns the WARNs marked (s) below into FAILs.
- `--level psm|peptide|both`: which levels to build.
- `--only a,b,...`: restricts the build to some outputs. The keywords are `coverage, ids, overtuning, electron,
  immuno, rule11b, lowmem, fdp, matched, time, stages, batch, scaling, calibration, percolator, prediction,
  references, arms, pairing, datasets`. The checks always run.
- `--logs yes|no|auto`: whether to read the `W/out/**` logs, `summary.yaml`, `sage.json` and `fragger.params`.
  `auto` reads them when they exist.
- `--runs`, `--references`, `--mzml-counts`: other run, reference or MS2-count tables. The defaults are
  `benchmarks/runs.tsv`, `datasets/reference_ids.tsv` and `datasets/mzml_counts.tsv`.
- `--runs-11b T`, `--rule11b-work R`: the task-11b run table and work folder, for O9b.
- `--gc-logs DIR`: MSFragger GC logs, for `gc_heap_gib` in O15. No log format is defined yet.

**Scaling folder S.** When the thread-scaling runs come from another node:

```sh
python3 -B benchmarks/summarize.py --work W --scaling-work S --out OUT \
    --machine W=.../W_node/machine.txt --machine S=.../S_node/machine.txt
```

- Only the `benchmark == scaling` rows are read from S, from its `timings.tsv`, `coverage.tsv` and `versions.txt`.
- Scaling rows present in both W and S stop the run.
- C13 also checks `S/versions.txt`.
- `S/out` is optional. When it exists (copy S with the light-copy filter below), C24 and the stale-timing test read
  the scaling folders from it. Without it they skip the scaling searches with an INFO (`LOGS`, `C24`), not a WARN.
  The logs of the other searches are read from `W/out` independently.

**Light copy.** The numbers can be computed in WSL on a copy of W that has no mzML or idXML files:

```sh
python3 -B benchmarks/summarize.py --print-light-copy-filter > light.filter
rsync -am --filter='merge light.filter' W/ COPY/
python3 -B benchmarks/summarize.py --work COPY --listing W.ls ...
```

The filter keeps:
- the tables, `versions.txt`, `commands.log`, `overtuning_*.tsv` and `counts_qgrid.tsv`;
- per search folder: `status`, `count_qgrid.sha256`, `inputs`, `*.log`, `summary.yaml`, `sage.json` and `fragger.params`.

When `W/out` is not a plain folder of W, `rsync -am` with this filter copies no `out/` and reports no error (`+ /out/`
matches directories only), so the copy has no logs and `--logs auto` only writes an INFO:
- `W/out` is a symbolic link (e.g. to another disk): add `-k` (`--copy-dirlinks`), i.e. `rsync -amk ...`.
- `out/` is copied on its own from its root: drop the `/out` prefix from the filter first,
  `sed -e '/^+ \/out\/$/d' -e 's#^+ /out/\*\*/#+ /**/#' light.filter > out.filter`. After the first rsync of W, run
  `rsync -am --filter='merge out.filter' OUT_ROOT/ COPY/out/`. rsync creates `COPY/out/` only when `COPY` exists.
  Otherwise add `--mkpath` (rsync 3.2.3 or later).
- Folder links inside `out/` (e.g. a search folder that is a link) are like a linked `W/out`: `rsync -am` drops them
  without a message, `rsync -amk` copies them as real folders.
- A `W/out` link whose target is missing: `rsync -am` and `rsync -amk` drop it, without an error. Another tool (e.g.
  `cp -a`) copies it as a link, and the build gives a WARN LOGS.
- A dangling link inside `out/` that is named like a log is copied as a link by `rsync -am` and `rsync -amk`. The
  build gives a WARN C24 for it.
Build with `--logs yes` when the copy should have logs: a missing `W/out` then gives a WARN, not only an INFO.

**Other modes**
- **Figures only:** `--figures-only --out OUT` redraws the figures from `OUT/tables/*.tsv`, for example in WSL on a
  copied output folder that has matplotlib. `--no-figures` skips the figures.
- **Smoke build:** `--work smoke_build --runs benchmarks/smoke/runs.tsv --design none`. Groups that `design.py`
  does not know become kind `other`. The side/class summaries, O4-O7, C14 and C15 are skipped.
- **Tests:** `--test` runs the unittest suite in `summaries/tests`. Without matplotlib the drawing tests are skipped.

**Font of the figures.** The figures use Arial, else Helvetica, else the first installed of Arimo, Liberation Sans,
Nimbus Sans and DejaVu Sans. Where Arial is not installed (as in a plain WSL), set the variable `SUMMARIZE_FONT_DIR`
to a folder that holds the Arial files, for example the Windows font folder as WSL sees it. The run then adds
`arial.ttf`, `arialbd.ttf`, `ariali.ttf` and `arialbi.ttf` of that folder (any case, no other file) to matplotlib for
this process only. Nothing is installed, copied or cached. The report says `INFO FIGURES font: <name> (<file>,
TrueType, embedded)`, plus a WARN (not strict) when the font is neither Arial nor Helvetica or when the variable names
no usable folder. `figures/index.tsv` names the font files that were added.

Exit codes:
- 2: an input validation stop;
- 1: any FAIL in the check report;
- 0: otherwise.

## Output folder

| File | Content |
|---|---|
| `check_report.txt` | the consistency report (below) |
| `errors.txt` | tracebacks of failed modules or figures (empty when none failed) |
| `provenance.tsv` | every input: path, size, SHA256 and mtime. Also the repository HEAD (or `NA (<git message>)` when git refuses, e.g. "dubious ownership" on Windows), the command line, the Python version, and `POOLED_ARRANGEMENT` with the parameter files it was read from |
| `numbers.tsv` | one row per placeholder key, with columns `key value text unit output protocol_ref source_side main_text_allowed`. `value` is full precision, `text` is formatted for the paper |
| `numbers.tex` | `\expandafter\def\csname num@<key>\endcsname{<text>}` per key, plus `\Num{<key>}`, which stops LaTeX on an unknown key |
| `sentence_overtuning_<level>.txt` | OT's over-tuning sentence, verbatim |
| `sentence_overtuning_<level>_display.txt` | the same sentence with display names for the dataset keys |
| `tables/O??_*.tsv` | the tables below. The first line of each is a `#` header note: definitions, sets, open-question defaults |
| `tables/O04_overtuning_<level>.stdout.txt` | OT's own printed output |
| `figures/fig_*.pdf`, `fig_*.png` | PDF with Type 42 fonts, PNG at 300 dpi |
| `figures/main/Fig<N>_*`, `figures/supplement/FigS<N>_*` | copies of the drawn figures under their paper numbers (`PAPER_FIGURES` in `figures.py`). A copy that this build did not write is removed |
| `figures/index.tsv` | one row per drawn figure: number, file, code name, size, the tables it read, the caption items and its facts (counts the caption needs) |

`numbers.tsv` key families: `ids.*`, `three.*`, `overtuning.*`, `fdp.*`, `coverage.*`, `time.*`, `mem.*`,
`batch.*`, `scaling.*`, `lowmem.*`, `cal.*`, `versions.*`, `cap.*`.
- Keys match `^[a-z0-9_.]+$`, so OT's L_T/L_H are `lt_<comparator>`/`lh_<comparator>`.
- FDPs are fractions in the tables and percentages in the keys.
- Own-set values and entrapment-search counts are never keys.

### Tables, by protocol section

Section 4.2, what is counted: identifications (DS §4.2, DS:585-632; held-out datasets DS §2)

| Table | Output |
|---|---|
| `O01_ids_runs`, `O01_ids_runs_wide`, `O01_ids_groups` | O1 identification counts per run and per group (DS:587-590, 608-610) |
| `O02_pairs_runs`, `O02_pairs_datasets`, `O02_pairs_summary` | O2 ProSE/comparator ratios: per run, per dataset, and the summaries per side/class/grade (DS:621-624) |
| `O03_three_runs`, `O03_three_datasets`, `O03_three_summary` | O3 the three-engine comparison over R3 (DS:623) |
| `O08_electron_runs`, `O08_electron_datasets` | O8 electron-based datasets: ProSE/MSFragger and FDP (DS §2.1, DS:881) |
| `O09_immuno_samples`, `O09_immuno_datasets` | O9 immunopeptidomics: both ProSE arrangements, published tools (DS §2.4, DS:625-631) |
| `O09b_rule11b` | O9b the pooled-arrangement rule of task 11b (DS:629, 1056); only with `--rule11b-work` |
| `O10_low_memory` | O10 the low_memory arm: counts identity, time and memory (DS:579-582, 652, 988) |
| `O14_coverage`, `O14_coverage_paper`, `O14_coverage_summary` | O14 coverage: every search and its state (DS:622, 807) |
| `O23_datasets`, `O23_runs` | O23 the dataset table: instrument, MS2 spectra, database and design (DS §1-2, DS:498-499) |
| `O24_external_references` | O24 published identification counts next to ours (DS:183, 485) |
| `O25_arm_<tag>` | O25 a generic table for an arm tag that `design.py` does not know (DS:652, 811) |

Section 4.2, entrapment FDP (DS:616-620, 931-939)

| Table | Output |
|---|---|
| `O11_fdp_results`, `O11_fdp_runs`, `O11_fdp_datasets` | O11 combined entrapment FDP per search, per run (mean ± SD over s1-s3, own and shared) and per dataset |
| `O12_fdp_arath` | O12 the Arabidopsis-reference FDP next to the shuffled mean (DS:370, 619) |
| `O13_matched_fdp`, `O13_matched_fdp_searches` | O13 counts at a matched combined FDP of 1% (DS:742, 1052). Built only when `W/counts_qgrid.tsv` exists |
| `O26_pairings` | O26 the natural-entrapment and low-input pairings: set S1, set S2, 250 pg (DS:159, 271, 312) |

Section 4.3, speed and memory (DS:633-672)

| Table | Output |
|---|---|
| `O15_time_runs`, `O15_time_datasets`, `O15_time_summary` | O15 per-file wall, CPU and peak RSS, median of 3 repetitions (DS:643-659) |
| `O15b_stage_times` | O15b stage times from the engine logs (DS:647-648, 809-810); only with `W/out/` logs |
| `O16_batch` | O16 the batch arm against the sum of the per-file medians (DS:661-663) |
| `O17_scaling` | O17 thread scaling: speed-up, efficiency, and the workstation comparison row (DS:665-671) |
| `O18_machines`, `O18_versions` | O18 machines, versions and the 200 GiB memory cap (DS:638-641, 649-653) |

Section 4.4, comparison engines: supplements (DS:673-777)

| Table | Output |
|---|---|
| `O19_calibration_counts` | O19 the calibration arms: ProSE calibration off, MSFragger calibrate_mass 0/1 (DS:756-776) |
| `O19_settings_msfragger`, `O19_settings_prose`, `O19_settings_sage` | O19 the chosen settings per search (DS:691, 983); filled only from `W/out/` logs |
| `O20_external_percolator*` | O20 the external Percolator control (DS:613-615, 991); only with `per_file_percolator_s<seed>` rows |
| `O21_prediction*` | O21 the prediction supplement, PeptDeep/MSBooster (DS:747-754); only with `per_file_peptdeep`/`_msbooster` rows |

Section 4.6, over-tuning check (DS:854-913)

| Table | Output |
|---|---|
| `O04_overtuning_<level>_runs`, `_datasets`, `_sides` | O4 OT's run ratios, dataset values and L_T/L_H, through `overtuning.py`; O7 is the peptide level |
| `O06_overtuning_<level>_loo` | O6 the leave-one-out table |
| `sentence_overtuning_*.txt` | the over-tuning sentence (version a/b/c of OT) |

O22, the required statements, is text only. The package supplies the inputs for it:
- dataset counts per side;
- grades in every held-out row;
- version strings;
- arrangement names.

### Figures

| Figure | Paper | From | Panels |
|---|---|---|---|
| `fig_overtuning_psm`, `fig_overtuning_peptide` | Fig 1, FigS1 | O4/O7 (O5, the over-tuning figure) | 2 |
| `fig_fdp_main` | Fig 2 | O11 (tryptic datasets only), O14 (optional) | 2 (PSM, peptide) |
| `fig_time_per_file` | Fig 3 | O15, O14 (optional) | 2 (time, peak memory) |
| `fig_immuno` | Fig 4 | O9, O24 | 2×2 |
| `fig_ids_counts_psm`, `fig_ids_counts_peptide` | FigS2, FigS3 | O3, O14 (optional) | 2 (tryptic, immuno) |
| `fig_fdp` | FigS4 | O11, O12, O14 (optional) | 2 (PSM, peptide) |
| `fig_electron` | FigS5 | O8, O11 | 2×2 |
| `fig_batch` | FigS6 | O16, O14 (optional) | 2 (batch time per file, ratio) |
| `fig_scaling` | FigS7 | O17 | 2×2 |
| `fig_low_memory` | FigS8 | O10 | 2 |
| `fig_calibration` | FigS9 | O19 | 4 (change in PSMs, peptides; PSM, peptide FDP) |
| `fig_matched_fdp` | FigS10 | O13 | 1-2 |
| `fig_ext_percolator`, `fig_prediction` | FigS11, FigS12 | O20, O21 | as O5 |

Each drawn figure is also copied under its paper number: Fig 1-4 to `figures/main`, FigS1-S12 to
`figures/supplement`. `figures/index.tsv` has one row per drawn figure, with the facts its caption needs: for
example the machine and threads (Fig 3), the out-of-memory searches, the decision runs and samples (DN13 class I is a
decision sample, DN13 class II is held-out), the runs above 1% FDP (Fig 2: shuffled dots, natural-only diamonds and
the diamonds of the datasets with both designs apart; the diamonds drawn above their dot), the run of each FigS9 column, that the Fig 4 panels have independent y scales, and the design groups that
Fig 2, FigS2, FigS3, FigS4 and FigS6 leave out, with the reason (`left_out`). In Fig 2 an electron-based group with
an O11 row has "electron-based: in FigS4" (the number of `fig_fdp` in `PAPER_FIGURES`; "in the full FDP figure"
when it has none). In Fig 2 and FigS4 an immunopeptidomics group with an O11 row has "immunopeptidomics: not
drawn". One without an O11 row has "no entrapment search" when `O14_coverage` lists no entrapment search of it. Any
other group without an O11 row has "no row in O11", also an immunopeptidomics group when `O14_coverage` lists one or
is absent or empty. The facts describe what the
figure draws: Fig 3
names a decision sample, and gives the memory note of the pooled samples, only when an immunopeptidomics point is
drawn.

A figure whose table is absent or empty is skipped with an INFO line, and its stale files and paper copies are
removed. A table that lacks a column the figure needs fails that figure only (FAIL FIGURES, traceback in
`errors.txt`). The report then gives the font line (above) and `INFO FIGURES index.tsv: n figure(s), main n,
supplement n`.

Common rules: 7.0 in wide and at most 9 in tall; 7 pt text with the font embedded as TrueType; no mathtext (a `$`
prints as it is); no stroke below 0.5 pt; no transparency; a true minus sign and thousands commas; bold panel
letters A, B, ... at the left edge of their column and at least 10 pt left of their axes on figures with more than
one panel; visible words from `VOCAB` in `figures.py`, never code names (`BANNED`). Two things in every PDF are
expected and print nothing: one graphics state with stroke alpha 0 (`/CA 0`, matplotlib's stroke of a marker edge
set to "none"), and one subset tag shared by the regular and the bold Arial (matplotlib derives it from the
character map). A production preflight may flag them.

How the figures show special cases:
- Missing values are an x at the axis base with a short reason. They are never drawn as 0. The spread runs of one
  engine in a column share one x, at the engine's place. Where an x would mislead, the reason stands alone: below the
  log time axes of Fig 3 and FigS6 (with no x in the panel under them), at the base of the log count axes of FigS2
  and FigS3 ("not counted by all three engines", on two lines when one line is wider than the category), and at the
  zero line of the change rows of FigS9.
- "Sage: not run" is one label under the electron block of Fig 3, FigS4 and FigS6, without an x, for the groups in
  which `O14_coverage` (or the figure's own table) has Sage as `not_run_by_design` and the figure's table has no other
  Sage row. It takes two lines when one line is wider than the block (FigS6). FigS5 has it as a legend entry. The
  reason ("no z+1 ions in Sage 0.14.7") goes to `index.tsv`.
- `failed_memory` is one x per engine and category on the 200 GiB cap line of the memory panel (`index.tsv` counts
  the searches). In Fig 3 A it is a label without an x that names the engine ("Sage: out of memory"), under each
  category with such a run, on three lines when one line is wider than the category. A label in such a stacked form
  has its lines closer (line spacing 1.0) than one-line text.
- Decision runs are open circles in the engine color, drawn above the other marks so that the whole ring shows, or
  bars in a tint of the engine color with a second tick-label line "decision". In FigS4 and FigS5 a decision run is
  the mean of its own realizations, without an SD bar (`index.tsv` says so).
- Engines side by side: a category dodges only the engines that have a row in it. So in an electron-based column
  (no Sage) ProSE and MSFragger stand at minus and plus half the dodge, not in the outer two of three slots. This
  holds in Fig 3 (dodge 0.27, as FIGURES_CAMERA_READY.md F3.5 says for the full columns), FigS4 (below) and FigS6
  (dodge 0.22). FigS5 has no Sage slot at all.
- The FDP figures (Fig 2, FigS4, FigS5) draw the shuffled mean as a 2.6 pt dot without an edge, with a 0.6 pt SD
  bar; the legend entry is a dot with a short bar. The engines are dodged 0.32 of a category, not 0.28 as
  FIGURES_CAMERA_READY.md F2.1 says: with 0.28 the gap between the runs of two engines (0.08) is narrower than the
  step between the runs of one engine (0.10), and the engine order cannot be read in grayscale. In Fig 2 and FigS4 a
  column with fewer runs per engine is dodged less: 0.22 with 2 runs, which keeps the gap between engines of a 3-run
  column (0.12), and 0.16 with one run. So the dots of one column stand closer to each other than to the next
  column. The natural diamond is about 3 pt from tip to tip (ms 1.6, edge 0.5), not 4.8 pt (ms 2.8, edge 0.8), so
  that the diamonds of one engine do not overlap; it has this size in every figure (Fig 2, FigS4 and FigS9). FigS4
  has 22 categories of about 21 pt, not 27 pt as Fig 2, so its dot is 1.8 pt, not 2.6 pt: with Fig 2's spacing the
  runs of one engine stay apart, and the gap between engines (2.6 pt) and between columns (3.4 pt) stays wider than
  the step between runs (2.1 pt). For the same reason the FigS4 decision ring is 2.3 pt across (ms 1.8, edge 0.5),
  not 4.2 pt, so that it does not cover the dot of the next run; its legend entry matches it. With more than 3 runs
  per engine and no Sage (PXD065289) FigS4 dodges the two engines 0.54 and spreads their runs ±0.20, not ±0.12. The
  FigS4 natural diamonds and Arabidopsis triangles (about 3 pt, the same footprint) stand at the x of their run,
  above its SD bar and under its dot: their white fill breaks the bar, so no solid arrow forms. A triangle exactly at
  a bar end can still look like an open arrowhead, so `index.tsv` (`arath_marks`) asks the caption to say that the
  triangles are Arabidopsis values. The 2.1 pt run step leaves no
  room beside the bar, so two such marks of one engine with nearly the same value still touch. In FigS9 the natural
  diamond stands 2.8 pt right of its arm marker, off the arm's SD bar, and each arm has one x in all four rows. The
  values are constants at the top of `figures.py` (`FDP_*`, `NATURAL`, `ARATH`, `NATURAL_BESIDE_PT`). Fig 2 draws
  the natural diamond of a run with a shuffled mean in the same way, at the run's x between its SD bar and its dot:
  its 2.7 pt run step leaves no room beside the dot either. Its dot (2.6 pt) is wider than the diamond across its
  flats, so a diamond less than 1 pt from its dot (`FDP_ON_DOT_PT`, measured once the layout is final) is drawn
  above the dot, and `index.tsv` lists these runs (`natural_on_dot`); a diamond under such a dot would show only its
  tips.
- FigS9 A and B (change in PSMs, in peptides) share one y range and tick step, so that a change that looks equal in
  both rows is equal.
- A log time axis (Fig 3 A, FigS6 A, FigS7 A) spans whole decades. It takes one decade more at an end where a
  marker would keep less than 1 pt of white to the axis (`EDGE_CLEAR_PT`).
- The held-out handle of the Fig 1 and FigS1 legend shows the line's (4, 2) dashes as two whole dashes, centered
  (`whole_dashes`): without the offset it ends in a 0.4 pt stub that reads as a dot. The "1% FDR threshold" handle
  of Fig 2 shows the 1% line's dashes (`ONE_PERCENT_DASHES`, matplotlib's `--` at 0.7 pt) as three whole dashes.
- A legend handle is about as large as the mark it stands for, and at least 2.4 pt across (the FigS2 and FigS3 run
  dot is 2.2 pt, as its dots). The engine dots have no edge and are 3.4 pt across, as the dot of the mean ± SD entry
  (`HANDLE_DOT_MS`). They are 2.6 pt in FigS4, whose dots are 1.8 pt, and 4.2 pt in FigS7, as its dots. The FigS9
  arm shapes have the size of the markers of A and B (`CAL_MARK`).
- A thin gray line separates the class blocks, with the block names above them. FigS5 has one category per run;
  there the datasets of a block are set apart by a gap, not by a line.
- Hatching marks the held-out datasets of the lead figures only.
- Open bars (white, ProSE-blue edge) mark ProSE in a non-default mode: joint rescoring, low-memory mode.
- Every held-out category carries its grade letter, in a row labelled "grade". A panel that shares y with a labelled
  panel left of it (FigS2 B, FigS3 B) has no label of its own, although G8 gives every grade row one: in the gap
  between the panels it would seem to continue the row of A.
- Fig 2 draws every natural value of a run as an open diamond without SD. A dataset with natural entrapment only
  (found in the data: no shuffled row in O11 for any of its runs, and a natural value) has only diamonds. With
  `FDP_MAIN_NATURAL_ONLY = False` in `figures.py` these natural-only datasets are left out. Then `index.tsv` names
  them in `natural_only_left_out`, and in `left_out` with the reason "natural entrapment only". A dataset with a
  shuffled design is never natural-only, even when its shuffled means are all missing (e.g. no realization shared by
  every engine): a run without a shuffled mean gets the missing mark next to its diamonds. Where an engine has no
  shuffled row of a run in a dataset with a shuffled design, its shuffled searches did not run (O11 leaves out a
  design only then), and the label is "not run". A dataset with both designs shows both, the dot with its SD bar and the diamond at the same x (above), and
  `index.tsv` names these datasets in `natural_with_shuffled`. Until 2026-11-26 UPS1 control, set S1 and set S2 had
  natural entrapment only, and Fig 2 showed velos's shuffled values only (FIGURES_CAMERA_READY.md D3). Since
  ups1_control, astral_s1 and ultra2_s2 have the shuffled design too (DATASETS.md, decisions of 2026-11-26), the
  owner decided that Fig 2 shows both values for them, and for velos too.

Figure rules that differ from SPEC (FIGURES_CAMERA_READY.md section 8):
- SPEC 3 "Figures": no mathtext; text at least 6 pt and lines at least 0.5 pt; no transparency; panel letters;
  `VOCAB`; a missing value may be a word without an x.
- SPEC O8, O9 (and OPEN Q9): decision runs as open circles in the engine color and tinted bars, not gray open
  markers and hatching.
- SPEC 3.7: the new `fig_fdp_main`, the `main`/`supplement` folders and `index.tsv`.
- SPEC O11: defaults 16-18 hold for the full `fig_fdp` (FigS4) only. Fig 2 shows the shuffled mean ± SD plus the
  natural values, with no decision run and no Arabidopsis value.
- SPEC O3: a geometric-mean line plus dots instead of grouped bars; the two panels share y.
- SPEC O5: the labels are words ("tuning +5.6%"), not L_T and L_H. The content is unchanged.
- SPEC O8: the lead in % on an axis centered on 0, not the ratio; a two-level x (the class block, a dataset with
  several units named once, its ticks "fraction N"); the decision tint.
- SPEC O9: rows in the order of `IMMUNO_ORDER` (PXD058436 on top); "(published)" labels; the slot of ProSE's other
  arrangement dropped when it is NA in every row (instead of "not run until it exists").
- SPEC O10: labels, open bars, no alpha; the time is per sample.
- SPEC O15: 7.0 x 4.6 in; every missing value of the time axis a label without an x (also "Sage: out of memory");
  "Sage: not run".
- SPEC O16: two panels (the batch time per file, then the ratio), 7.0 x 4.4 in, all markers filled: no open markers
  for "not in B3" (`index.tsv` names those groups).
- SPEC O17: a band instead of the ring, the square 7 pt right of its own thread count (not at 1.12 x n), x tick labels
  only at the powers of 2 and the largest grid point; one gray dashed ideal line per engine.
- SPEC O19: the change from the engine's default settings in %, 100 x (ratio_to_main - 1), not the ratio; four
  rows in design order, new arm markers (a triangle is "no mass calibration"), the natural diamond beside its arm
  marker.

## The check report

`check_report.txt` has one line per finding:

```
PASS|WARN|FAIL|INFO <id> <message>
```

- Messages give keys and counts, never outcome values.
- Lists of keys and files stop after 10 items and then say `... (+n more)`. Some stop earlier: after 5 (C5
  incomplete timings), 4 (C6d absent leads) or 3 (C16, and the missing r-logs of one C24 folder). Lists with a small
  fixed bound are given whole: the files of one search or of one skipped figure, the stale logs of one C24 folder,
  the CAL_RUNS and calibration arms of O19, the sides of C25, and the columns a table lacks. The tables of an
  earlier build that `INFO STALE` names are also given whole.
- The report starts with `INFO LOAD` lines (rows read, tags, design) and the INFO lines of the modules (what was built
  or skipped, and why).
- It ends with `INFO FIGURES` per figure and `INFO SUMMARY n PASS, n WARN, n FAIL, n INFO`.
- A module that raised gives `FAIL MODULE <name>`.
- (s) marks a WARN that `--strict` turns into a FAIL.

| Id | Check |
|---|---|
| C1 | `counts.tsv` keys equal the coverage keys with counted = yes, in both directions |
| C2 | every counted search has exactly one psm and one peptide row: class all, q 0.01, the unit's count file. When `out/` is present, `count_qgrid.sha256` must match the current `.count.idXML`. A missing hash or idXML counts as unverified. So does one that cannot be read, and a WARN (not strict) names it |
| C3 | coverage holds every per_file search the run table implies. Arm folders unknown to `design.py`: WARN. Rows outside the design: WARN(s) |
| C4 | search states. Only Sage on bycz units is `not_run_by_design`. Sage `failed_memory` on class II is expected (PASS with a note). Any other failed, not_run or running state: WARN(s) |
| C5 | timings: every timing key has a coverage row; every timed ok search has a complete last attempt; stage sets per engine; MSFragger batch rescoring rows = n_files |
| C6a-d | over-tuning against OT. (a) dataset values within 1e-12 relative; (b) run ratios as OT's 6-decimal strings; (c) the kept `W/overtuning_<level>.tsv` equals OT's rows, else WARN(s); a kept file older than counts.tsv gives a WARN that `--strict` leaves a WARN; (d) the leads within 1e-9 points |
| C7 | td rows: entrapment 0, te_ratio 1 |
| C8 | `combined_fdp` and `lower_bound_fdp` recompute from the integer columns within half a unit of the 4th significant digit; `paired_fdp` is NA exactly where expected |
| C9 | every (engine, unit) has all shuffled realisations s1-s3, else WARN(s) |
| C10 | low_memory counts equal the standard counts per sample |
| C11 | the batch groups (17; 16 for Sage); one thread count across per_file, arms and batch; `--expect-threads` |
| C12 | scaling grids: repetition 0 only at the top point; `not_run_over_limit` only below an over_limit point; the same grid per engine |
| C13 | `versions.txt` of W (and S): ProSE/EE/FileConverter revision, Sage, MSFragger and Percolator versions |
| C14 | `mzml_counts.tsv` has every run; the MS2 spectra of the tuned runs sum to 1,509,392 (DS:16) |
| C15 | groups, the tuning/held-out lists, decision runs and runs per dataset agree with `design.py`, OT and DS |
| C16 | comparison sets: R3 ⊆ R(pair); no decision unit in R, R3, F, T, T3 or B3 |
| C17 | timing and batch/scaling coverage rows use the unit's or group's td database |
| C18 | input ages: whether each kept over-tuning file is older than counts.tsv, as INFO (the WARN is C6c's); `--listing` is used on copies |
| C19 | every identification-ratio key allowed in the main text comes from held-out data: `ids.*`, `three.*`, `cal.*`, `percolator.*`, `prediction.*` and the O13 leads `fdp.matched.*` |
| C20 | every held-out row carries a grade, every tuning row `-` |
| C21 | the reference map: every immuno sample has its expected published tools |
| C22 | `POOLED_ARRANGEMENT` is equal in the four immuno parameter files (and, with O9b, equals 11b's choice) |
| C23 | with logs: a settings row for every counted MSFragger (WARN(s)) and ProSE (WARN: one for each file of the run table, under its name, and no row without a value) per_file* search. A row counts only with a source and a value (not NA, empty or `-`) in every setting (MSFragger: fragment_tol and unit, use_topN_peaks, minimum_ratio, intensity_transform, remove_precursor_peak, max_fragment_charge; ProSE: the tolerance and its unit). The WARN names the NA columns and, for ProSE, the run table's files without a row (`no row: <files>`). An MSFragger search without a row is `no row`. INFO O19's "without a value" counts by the same rule |
| C24 | with logs: timed folders hold `<stage>.r<rep>.log` for every stage and repetition of the used attempt (r0 included) and no stale `<stage>.log` of any stage, named by their folder under `out/` (`.../hye_td_t4` for scaling). Scaling folders are read from `S/out`, the others from `W/out`. A missing `W/out` or `S/out` gives an INFO SKIP for its searches; a missing engine subtree or search folder inside an existing tree gives WARN(s) `(no folder)`. A dangling symbolic link named like a file the package reads in a search folder gives a WARN (not strict), when the build listed that folder. The names are a log, `inputs`, `summary.yaml`, `sage.json`, `fragger.params`, `count_qgrid.sha256` and the `.count.idXML` |
| C25 | O4-O7 are skipped when a side has no dataset for a comparator: WARN(s) |

C11 and C12 also compare the thread count of every used timing with the CPUs of its `--machine` file (role engine;
for a separate S role scaling): more threads than CPUs gives WARN(s), and C11 gives a WARN when no machine file is
given.

Other report ids:
- `O13`: a qgrid file that cannot be read gives a WARN. The search counts as unverified, and its rows note the error.
- `O18`: a node without `--machine` gives a WARN(s).
- `O19`: WARNs for calibration arms with fewer counted searches than expected, for calibration-arm searches on units
  outside CAL_RUNS (not in O19), for ProSE input problems (inputs file, run table and Searching lines disagree), and
  for files of counted searches that could not be read.
- `FIGURES`: one line per figure, as above.

## Defaults taken for the open design questions

Each line is the rule the code applies.

1. Group counts are sums of per-file counts over the units that every compared engine counted, decision runs excluded. Peptides are never unioned, and immuno gets no group sums.
2. "The sums" are ΣProSE/Σcomparator over the same run set as the geometric mean, per dataset and scope.
3. The run-weighted value is the geometric mean of the per-run ratios over all runs of the scope.
4. Zero counts are dropped from every ratio, as OT does, and still shown in O1. The FDP of an empty result is missing, never 0.
5. The headline leads are OT's held-out leads L_H at PSM level. The peptide-level leads go to the supplement.
6. The three-engine comparison gets a supplementary table plus `fig_ids_counts`, and no text number.
7. Per-run and per-group tables are supplementary TSVs.
8. Electron and immuno datasets get per-dataset values only, also listed in O3. A dataset with only decision runs gets no value.
9. Decision runs appear in per-run tables and figures as open circles in the engine color, or as bars in a tint of the engine color with the tick-label line "decision". They are absent from the over-tuning figure and excluded from every summary (FDP, timing and low_memory included), but kept inside batch groups.
10. In the supplements, decision runs are listed per run and excluded from the summaries.
11. Failures are never drawn as 0 or as "slow". Electron and immuno datasets get their own panels.
12. Published references are read from `datasets/reference_ids.tsv` through `design.REFERENCE_MAP`: immuno and iPRG2015.
13. FDP beyond a single run is the per-dataset mean of run means, plus the maximum, over the shared set F (runs and realisations completed by every expected engine). Own-set values are per run only.
14. The SD is the sample SD (n−1) over s1-s3.
15. A missing realisation gives the own mean ± SD of those present, with n and a flag. Comparisons use the shared realisations.
16. A dataset with a natural database only is reported like velos natural, without an SD. Until 2026-11-26 these were ups1_control, astral_s1 and ultra2_s2; since then they have s1-s3 too (DATASETS.md, decisions of 2026-11-26) and follow 17.
17. Where a dataset has a natural database (velos; since 2026-11-26 also ups1_control, astral_s1 and ultra2_s2), natural entrapment is the main value and s1-s3 the check. Both are shown.
18. The Arabidopsis FDP is shown next to the shuffled mean ± SD of the same run, as △ in `fig_fdp`. Defaults 16-18 hold for the full `fig_fdp` (FigS4); Fig 2 (`fig_fdp_main`) shows no Arabidopsis value and no decision run.
19. Matched FDP targets 1.0% combined, recomputed from the integer columns and te_ratio, per realisation, then averaged over the shared realisations, at both levels. It is built only when `W/counts_qgrid.tsv` exists; the q-grid stage (`qgrid.py`) is not written. Its counts go to the supplement table only, labelled; the text uses ratios.
20. lower_bound and paired FDP appear only in the per-result table.
21. Timing medians are taken per metric independently.
22. Stage times (O15b), for every per_file td search whose coverage is ok (failed searches, e.g. Sage's 6
    `failed_memory` class II samples, have their state in O15 and no O15b rows; the arms, batch and scaling have no
    stage rows):
    - ProSE: index/search/output/total from `all.r<rep>.log`, median over r1-r3, plus the finer split from `summary.yaml` of r3 (calibration, scoring, fdr, index, output, total), labelled by `source`;
    - Sage: from `all.r<rep>.log`;
    - MSFragger: search/join/rescoring from the timings, index and calibration from its search log.
23. Cross-run timing: per-dataset sums and the geometric mean of per-unit time ratios over the shared ok units T(pair), equal weight per kind, tryptic also over T3. Memory maxima are taken over the same sets. `failed_memory` is excluded.
24. Batch time per file is the batch median / n_files, compared with the Σ per-file medians of the same files. Cross-engine keys use B3.
25. Scaling: S = T1/Tn and E = S/n, with relative columns when T1 is missing. MSFragger time includes Percolator, with search-only alongside. over_limit gives a lower bound. A gray band marks 16 threads, the main benchmark setting. The engine node's per_file `hfx_A2` row is drawn as a white square 7 pt right of its own thread count, which the table note and legend state: at 16 threads (the paper's per_file setting) it stands next to the band; at another count (64 in both trials) it stands next to that count.
26. Memory is in GiB (2^30 bytes).
27. low_memory: medians plus the identity check. The summary is the median ratio over non-decision samples.
28. Calibration:
    - chosen settings for every MSFragger search and every ProSE per_file search;
    - a supplement table for the 9 calibration files;
    - velos with natural and s1-s3.
29. Settings are reported from repetition 3 (when r3 is missing, from the last r-log present), and differences
    between repetitions are flagged (`note=varies`): per MSFragger search, and per input row of a ProSE search (a
    pooled search can vary on one input only). Repetition 0 is not compared.
30. Over-tuning numbers use OT's format (1 decimal, signed L_T), and the 3-point test runs on unrounded values. OT's sentence is kept verbatim, with a display-name version next to it.
31. When the dataset numbers differ between comparators, the text reads "N (for Sage M)".
32. The over-tuning figure uses class blocks with tuning then held-out inside each, the lead in % on a linear axis, and no decision runs. The peptide version goes to the supplement.
33. The leave-one-out table has one row per left-out dataset (side, class, grade). Each row gives L_T, L_H and the gap per comparator, whether both stay within the margin, and whether the dataset is the one named in version (b).
34. The package lives in `benchmarks/summarize.py` + `benchmarks/summaries/`. Numbers use the standard library, figures use matplotlib.
35. `--scaling-work S` reads scaling rows only from S. Scaling rows in both folders stop the run. C13 also checks `S/versions.txt`, and S's machine file comes via `--machine`.
36. The ProSE other-arrangement arm is tag `mode_joint` when the main arrangement is per_file (`mode_per_file` otherwise): 12 samples, td, untimed. The main arrangement is read from the immuno parameter files.
37. External Percolator covers all tryptic per_file units, td + s1-s3, with tags `percolator_s<seed>`.
38. The prediction list is hfx, astral, lumos_lfq, eclipse_tmtpro, tims_plasma, iprg2015, astral_s1 and astral_250pg.
39. Pre-P observations are not produced by the package.
40. Immuno FDP gives no output until its design exists.
41. Strict mode expects 16 threads for per_file, its arms and batch.
42. In O23, instrument names come from `design.py` and MS2 counts from `datasets/mzml_counts.tsv`.
43. PXD011695's instrument follows DATASETS.md (Orbitrap Elite).
44. Sage's class II wall time before the memory kill is not reported.
45. Task 11b runs in its own work folder with its own run table and is reported as O9b, a decision-sample supplement table. Its "1 Poisson SE" is `sqrt(N_E)·(1+T/E)/N` of per_file's estimate.
46. PXD019643's MHCquant 1.5.1 values (1% *local* peptide-level FDR) are shown with a "local FDR" flag, without claiming the same FDR level.
47. Other references:
    - iPRG2015 uses the MS-GF+ rows that match DS:183, with the DeMix rows as context;
    - PXD065289, ProteoBench and PXD011695 OMSSA/COMPASS get none in the package;
    - the remaining reference rows are not used.
48. Peak RSS is the reported memory for all engines, with a note that MSFragger's includes its JVM heap. `gc_heap_gib` stays NA until a GC-log format is defined.
49. An unknown arm tag gives a WARN and a generic O25 table. The planned arms are `design.ARMS`.
50. The held-out grade scopes A/B/C are computed, for the supplement only.
51. `cores_used` appears in O17 only, with no key.
52. O12 `difference_pp` is Arabidopsis minus the shuffled mean, in percentage points, table only.
53. `n_runs_mean_above_1pct` (runs in F whose shared mean exceeds 1%) is a key next to the mean and maximum.
54. `fig_ids_counts` shows the per-dataset geometric mean of the counts over R3.
55. O13 gives natural-only units their single natural value, puts Arabidopsis in its own column, and lists the plain-database ratio at q ≤ 0.01 alongside.
56. The O13 count is N, EE's `accepted` of the entrapment search. q_match is the largest grid q with FDP ≤ 1.0%, and `monotone_ok` is reported.
57. Prediction arms are also run on s1-s3, with FDP as O11. The instrument comes from `commands.log`, and the MSBooster version from `versions.txt`.
58. O26 pairings (set S1, set S2, 250 pg) are an optional supplement table, with no identification ratio in the text.
59. `main_text_allowed = yes` goes only to identification-ratio keys from held-out data, the over-tuning keys, and keys that are not identification ratios.
60. Numbers and logs run in the engine-node container (Python 3.12) or in WSL on a light copy, and figures in WSL from the written tables. Python 3.10 is the floor.
61. A kept over-tuning file that is missing or differs from OT's rows gives a WARN(s). One older than counts.tsv gives a WARN only, which `--strict` does not turn into a FAIL (C6c); C18 records the ages as INFO. Both trials therefore get two such WARNs (psm, peptide), although SPEC 7 V3 expected no WARN on the engine-node trial.
62. Own-set values appear only in per-run tables and in labelled `_own` columns, never in `numbers.tsv`.
63. There is no blind mode (no `--blind`, no `sealed/`), so nothing is sealed.
64. `--machine` reads `node_prep/machine.txt` of each node. A missing one gives a WARN(s).
65. Rows in W outside the design (other than 11b pairs and further arms) are excluded and listed, with a WARN(s).

Decisions made while building the package:
- SPEC.md contradicts itself on the age of the kept over-tuning file: §3.5, C6c, Q61 and §9 say WARN, while C18 and
  V3 say INFO. The default of Q61 is followed: a non-strict WARN under C6c, with the ages as INFO under C18.
- `ids.immuno.*` keys exist at the peptide level only; the PSM values stay in the O9 tables (SPEC O9).
- O19 FDP: an arm row averages the realisations with N > 0 in both that arm and the engine's main arm (SPEC O19). The
  SPEC gives no set for the main row, which averages the realisations with N > 0 in the main arm and every arm of the
  engine that ran on the unit. `fdp_shuffled_n` shows each row's set.
- `n_reps` (O15, O17) counts the complete repetitions whose values are reported (states ok, incomplete, no_timing,
  and over_limit for its lower bound). It is 0 for every other state, e.g. stale_timing, failed or not_run.
- Two tables beyond the planned list:
  - `O04_overtuning_<level>_runs`: OT's run ratios, used by the figure;
  - `O13_matched_fdp_searches`: per search, before the realisation mean.
- O9's header note states, for each published value, its reference FDR level and kind.
- A missing reference file is a FAIL in C21 when immuno samples exist, and INFO SKIP otherwise.

Where the logs of `b2d252b442` differ from what SPEC.md assumed (SPEC took its log shapes from builds before `b2d252b442`; checked on the
engine-node trial, which ran at 64 threads with ProSE `b2d252b442`, Sage 0.14.7 and MSFragger 4.4.1). The code follows the logs:
- **ProSE timing line, two shapes.** SPEC O15b names only `[ProSE] Total time   : total <x>s | search of the file(s)
  <x>s | outputs <x>s`, which is what the multi-input report of a pooled sample prints. A single-input report prints
  `[ProSE] total <x>s | search of the file(s) <x>s | outputs <x>s` without the label, under a `--- Timing ---` header
  next to `[ProSE] calib <x>s | scoring <x>s | index(shared) <x>s` (56 single-input units in the trial). Both shapes
  are read. The index line `Fragment idx : ... (build <x> s)` has one or two blanks before `(build`; both are read.
- **What the ProSE stages mean.** The log's `search` ("search of the file(s)") is the whole per-file phase, total
  minus outputs: index build, calibration, scoring and Percolator. `summary.yaml`'s `timing_seconds.search` is the
  scoring step only (it equals the log's `scoring`), so its O15b stage is called `scoring`, not `search` as in SPEC
  O15b. `fdr` is `timing_seconds.fdr`, ProSE's own FDR step, so its stage is called `fdr`, not `rescoring/fdr` as in
  SPEC O15b. It is 0 with `fdr_applied: false` (the whole trial), and the row's note says so: Percolator's rescoring
  has no time of its own in the log or in `summary.yaml`.
- **Resolution.** ProSE log times have 0.1 s, `summary.yaml` 6 significant digits; Sage's `finished in` total is
  whole seconds, its ms lines 1 ms; MSFragger's phase times 0.001 min. MSFragger's index time is the sum of the
  `Fragment index slice generated` lines of its first and main search; its calibration time (`... DONE IN <x> MIN`)
  excludes the first search.
- **Stale timing of any stage.** A timed folder with the untimed `<stage>.log` of any stage of the search (`all`,
  `search`, `join`, `rescoring`) is `stale_timing`, as SPEC 2.5 and C24 name any `<stage>.log`; O15/O16/O17, C5 and
  C24 agree. `measure()` empties the folder before every search (B:896-904), so a stale folder holds only
  `<stage>.log` files, unless a copy merged two states of it. In a stale folder O15b gives NA in every row (SPEC
  2.6), since its r-logs belong to the older timed search and its `summary.yaml` to the untimed rerun. A dangling
  `<stage>.log` link counts as absent, so it does not make the folder `stale_timing`; it gives a WARN C24, not
  strict. A literal reading of SPEC 2.5 and C24 ("holds `<stage>.log`") would make the folder stale, with a FAIL
  under `--strict` (open SPEC question).
- **O19 in a stale folder (a deviation from SPEC O19 "Which log", which names r3 for every timed search).** O19
  reads the rerun's `<stage>.log` when the folder holds it, since the rerun's output is the counted one. Every
  MSFragger and ProSE row of a stale search says which log it read (Sage reads `sage.json`, no log):
  `stale_timing: <stage>.log of the untimed rerun used`, plus `, <stage>.r<rep>.log ignored` when the r-logs are
  there too; or `stale_timing (<logs> in the folder): <log> used` when another stage's log makes the folder stale
  (e.g. MSFragger's `join.log`, with the values from `search.r3.log`). A folder with r-logs and `<stage>.log` whose
  search is not `stale_timing` (an untimed search, or another timing state) gets `<stage>.r<rep>.log and
  <stage>.log in the folder: <stage>.log used`. Whether SPEC should read r3 here instead is open.
- **A missing r-log** of a complete timing (e.g. `all.r2.log`) leaves the O15 state as timings.tsv gives it; O15b's
  log rows become NA (`no all.r2.log`), not a median of the others, and C24 gives a WARN(s). SPEC C24 ("else
  `stale_timing` WARN(s)") could be read as `stale_timing` here; this package keeps the O15 state (open SPEC
  question). When `r3` is the missing one, O19 reads the last r-log present, e.g. `all.r2.log`. The `log` column
  names it; the header says r3. This package's C24 also requires the warm-up `r0` logs (every repetition of the used
  attempt), although r0 is never used for a value. SPEC C24 and 2.5 do not say which repetitions need a log (open
  SPEC question).
- **MSFragger `New` lines.** Every calibrated search has one block with `New fragment_mass_tolerance`,
  `use_topN_peaks`, `minimum_ratio`, `intensity_transform` and `remove_precursor_peak`; `New max_fragment_charge`
  appears only on the ion-trap searches (61 of the 230 per_file searches of the trial, not "missing in 17 of 338" as
  in SPEC O19). The other rows take it from `fragger.params`: `source=mixed`, note `configured: max_fragment_charge`.
  SPEC O19 says `source=configured` for a key from fragger.params. Here `configured` is kept for rows without any
  `New` line: calibrate_mass 0 or 1, or a calibrated log without any `New` line (e.g. a cut log), which gets the note
  `no New lines`. The tolerance is always printed in PPM: the 0.5 Da searches get a ppm
  tolerance, with the note `configured tolerance 0.5 Da`. A `New` key outside the six is named in the note (`other
  New keys`).
- **ProSE Fragment lines.** One per input, inside the `[i/n] Searching <file>` block; block i names line i of `inputs`
  in every search of the trial (SPEC's "to be confirmed on P logs"). The blocks are matched to the inputs by name
  only. The name is the file name without its folder and a final `.mzML`, compared exactly, so `<id>.mzML.gz`,
  `<id>.mzml` or another case of the run id does not match. This deviates from SPEC O19 "ProSE parser", which
  assigns line i to input i: a name that differs means that ProSE searched another file. A log without Searching
  lines is still matched by order (SPEC's rule). An input that no Searching line names gets no value (source NA,
  note `not searched in <log> (no Searching line names it)`). This holds also when the Searching lines name none of
  the inputs. The blocks need not follow `inputs`: the pooled test fixture, in the log shape of builds before `b2d252b442`,
  searches `DN05_r2` before `DN05_r1`, so a match by position could swap values. Two cases give a WARN O19: an
  inputs file that differs from the run table (the WARN names the files only in one of them), and a log that
  searched other files (the WARN names them). Not matched besides SPEC's two lines: the tolerance estimate `[ProSE]
  Fragment     : median N ppm, MAD N -> recommend N ppm`. When `|offset| + 4 sigma` covers too few peaks, ProSE logs
  `covers only N % ... the configured fragment tolerance is kept` before the Fragment line; the row gets the note
  `configured tolerance kept`, and its `prose_covered_pct` is that of the rejected candidate, not of the reported
  tolerance. The Fragment line prints offset, sigma and tolerances with 2 decimals and covers as an integer, and so
  does the table (a logged `-0.00` stays `-0.00`); a configured tolerance from `summary.yaml` is printed with 2
  decimals, or exactly when it has more (`0.025`).
- **Settings tables, the columns SPEC leaves open.** `source` is one of:
  - `chosen`: from the log;
  - `configured`: fragger.params, summary.yaml or sage.json only;
  - `mixed`: MSFragger, not every key from a `New` line. The keys taken from fragger.params are named in
    `configured: <keys>`, the keys in neither in `missing: <keys>`;
  - NA: no settings, no folder, an input not searched, a log that could not be read, or a calibrated search without
    a log.

  The rule is "no readable log, no value", unless the configuration fixes the value:
  - A search without a log keeps its configured values only when the engine does not choose them at run time:
    MSFragger with `calibrate_mass` 0 or 1 in fragger.params, ProSE with calibration off (`calibration_enabled:
    false` in summary.yaml; without that key, the cal_off arm). A calibrated search without a log (MSFragger
    `calibrate_mass` 2, ProSE with calibration on) gets NA with the note `no search log` or `no all log`, and a C23
    WARN. For MSFragger that WARN is strict (WARN(s), a FAIL under `--strict`). Its configured value need not be the
    value the engine used.
  - When the log of the `log` column cannot be read, the row is NA in every arm. So a cal_off ProSE search or a cal0
    MSFragger search whose log cannot be read loses its configured value, although its summary.yaml or
    fragger.params is readable. An unreadable r1 or r2 log only gets the note.

  Sage rows exist for counted searches only (not for the 6 `failed_memory` folders). Sage's `max_fragment_charge` NA
  means sage.json does not set it, i.e. Sage's default. The header line of each table names its log and its sources,
  and for MSFragger and ProSE its main notes. Every note the tables can hold (a row's notes are joined by `; `):
  - O19_settings_msfragger: `no search folder`, `stale_timing ...` and `... in the folder: search.log used` (above),
    `no search log`, `no New lines`, `varies`, `<file> not read: <error>` (a log or fragger.params), `no
    fragger.params`, `unparsed fragment_mass_tolerance line (<line>)`, `configured tolerance <x> <unit>`,
    `fragment_mass_units <x> (0 or 1, B:618)`, `configured: <keys>`, `missing: <keys>`, `other New keys: <keys>`.
  - O19_settings_prose: `no search folder`, `no all log`, `stale_timing ...` and `... in the folder: all.log used`
    (above), `not searched in <log> (no Searching line names it)`, `sigma in <unit>`, `configured tolerance kept`,
    `calibration off`, `calibration: insufficient PSMs`, `no fragment calibration line`, `no summary.yaml`,
    `summary.yaml without shared`, `<file> not read: <error>` (inputs, a log or summary.yaml), `varies`, `<n>
    searched file(s) not in inputs`, `<n> more Fragment lines than inputs`.
  - O19_settings_sage: `no search folder`, `no sage.json`, `sage.json not read: <error>`, `no fragment_tol object`,
    `asymmetric window [<lo>, <hi>]`.
  - O15b_stage_times: `no <log>.r<n>.log`, `<log>.r<n>.log not read: <error>`, `line not found in r<n>[,r<m>]`,
    `timing <state>` (the O15 state when it is not ok), `no summary.yaml`, `summary.yaml not read: <error>`,
    `summary.yaml of the untimed rerun, not of r3` (stale_timing), `key not found`, and on the fdr row `fdr_applied
    false: ProSE's FDR step did not run, and Percolator's rescoring has no time of its own (in the log's search of
    the file(s))`.
- **C23** counts a settings row only when its source and every setting have a value (not NA, empty or `-`); a ProSE
  search needs one such row for each file of the run table, under that file's name (`input`), and no row without a
  value (e.g. an input of its inputs file that the log did not search). INFO O19's "without a value" uses the same
  rule (`calib.search_lacks_value`), so both count the same searches. An MSFragger row of source `mixed` whose
  fragment tolerance is NA (a `New` block without `fragment_mass_tolerance` and no fragger.params) is such a row.
  C23 is a WARN for ProSE (SPEC C23), so `--strict` does not fail on it. A calibrated search without a log has
  source NA (above), so C23 gives a WARN for it: for MSFragger a WARN(s), which fails under `--strict`. This
  deviates from SPEC C23, whose "(parsed or configured)" would
  count its configured value, which need not be the value the engine used (open SPEC question).
- **Reading W/out.** Each search folder is listed once and each file read once per build (`ctx.files`), shared by
  O15b, O19, C24 and the stale test. This matters on a slow disk (a Windows disk read from WSL, where each stat or
  open costs milliseconds).
  - A dangling symbolic link counts as absent, as for `os.path.exists`. One named like a file the package reads in a
    search folder gives a WARN C24 that names it, not strict. These names are a log, `inputs`, `summary.yaml`,
    `sage.json`, `fragger.params`, and `count_qgrid.sha256` and the `.count.idXML` of the qgrid check (C2, O13). The
    real W also holds MSFragger's links to the mzML files, which dangle when W moves; those are not named.
  - A listed file that cannot be read (no permission, or a folder of that name) gives the note `<file> not read:
    <error>`. In O15b the note is on the file's rows, which are NA. In O19 it is on every row of the search, and a
    value that needs the file is NA: an unreadable log read gives no value, and an unreadable `inputs` falls back to
    the run table's files. A WARN O15b (for the files O15b reads) and a WARN O19 name each such file by its path
    under `out/`, the same path in both.
  - With `W/counts_qgrid.tsv`, a qgrid file (`count_qgrid.sha256` or the count file) that cannot be read leaves its
    search unverified. A WARN C2 names the file. With logs, a WARN O13 names it too, for the searches in
    `counts_qgrid.tsv`, and the O13 rows of the search note the error.
  - provenance.tsv lists every file the O15b and O19 tables read, but not one that could not be read. Its sha256 is
    that of the bytes the build read, without a second read. Its size and mtime come from summarize.py's stat when
    provenance.tsv is written. So a file that changed during the build (a live W) keeps the hash of the bytes the
    build used next to its new size and mtime. The row then no longer matches the file, which shows the change.
- **summary.yaml subset.** A line the subset cannot place (a block scalar, a nested sequence, a line indented under a
  scalar) raises an error naming it. O15b writes it in the note of the summary.yaml rows, O19 in the note of every
  row of the search (`summary.yaml not read: <error>`, for an unreadable file `<class>: <reason>`), and the WARNs
  above name the file. A quoted value followed by a comment loses the comment, and `-nan` is a float NaN.
