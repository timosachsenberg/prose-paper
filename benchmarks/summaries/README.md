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
  writes (INFO STALE; kept under `--only`), and `fig_*` files of figures that are now skipped.
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

**Other modes**
- **Figures only:** `--figures-only --out OUT` redraws the figures from `OUT/tables/*.tsv`, for example in WSL on a
  copied output folder that has matplotlib. `--no-figures` skips the figures.
- **Smoke build:** `--work smoke_build --runs benchmarks/smoke/runs.tsv --design none`. Groups that `design.py`
  does not know become kind `other`. The side/class summaries, O4-O7, C14 and C15 are skipped.
- **Tests:** `--test` runs the unittest suite in `summaries/tests`. Without matplotlib the drawing tests are skipped.

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

| Figure | From | Panels |
|---|---|---|
| `fig_overtuning_psm`, `fig_overtuning_peptide` | O4/O7 (O5, the over-tuning figure) | 2 |
| `fig_ids_counts_psm`, `fig_ids_counts_peptide` | O3 | 2 (tryptic, immuno) |
| `fig_electron` | O8 | 2×2 |
| `fig_immuno` | O9, O24 | 2×2 |
| `fig_fdp` | O11, O12 | 2 (PSM, peptide) |
| `fig_matched_fdp` | O13 | 1-2 |
| `fig_time_per_file` | O15 | 2 (wall, RSS) |
| `fig_batch` | O16 | 1 |
| `fig_scaling` | O17 | 2×2 |
| `fig_low_memory` | O10 | 2 |
| `fig_calibration` | O19 | 2 |
| `fig_ext_percolator`, `fig_prediction` | O20, O21 | as O5 |

A figure whose table is absent or empty is skipped with an INFO line, and its stale file is removed. A table that
lacks a column the figure needs fails that figure only (FAIL FIGURES, traceback in `errors.txt`).

How the figures show special cases:
- Missing values are an x at the axis base with a short reason. They are never drawn as 0.
- `failed_memory` is drawn on the 200 GiB cap line.
- Decision runs are open grey markers or hatched bars.
- Every held-out category carries its grade letter.

## The check report

`check_report.txt` has one line per finding:

```
PASS|WARN|FAIL|INFO <id> <message>
```

- Messages give keys and counts, never outcome values.
- The report starts with `INFO LOAD` lines (rows read, tags, design) and the INFO lines of the modules (what was built
  or skipped, and why).
- It ends with `INFO FIGURES` per figure and `INFO SUMMARY n PASS, n WARN, n FAIL, n INFO`.
- A module that raised gives `FAIL MODULE <name>`.
- (s) marks a WARN that `--strict` turns into a FAIL.

| Id | Check |
|---|---|
| C1 | `counts.tsv` keys equal the coverage keys with counted = yes, in both directions |
| C2 | every counted search has exactly one psm and one peptide row: class all, q 0.01, the unit's count file. When `out/` is present, `count_qgrid.sha256` must match the current `.count.idXML`; a missing hash or idXML counts as unverified |
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
| C23 | with logs: a settings row for every counted MSFragger (WARN(s)) and ProSE (WARN) per_file* search |
| C24 | with logs: timed folders hold `<stage>.r<rep>.log` and no stale `<stage>.log`. Scaling folders are read from `S/out`, the others from `W/out`; a missing tree gives an INFO SKIP for its searches |
| C25 | O4-O7 are skipped when a side has no dataset for a comparator: WARN(s) |

Other report ids:
- `O18`: a node without `--machine` gives a WARN(s).
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
9. Decision runs appear in per-run tables and figures as open grey markers. They are absent from the over-tuning figure and excluded from every summary (FDP, timing and low_memory included), but kept inside batch groups.
10. In the supplements, decision runs are listed per run and excluded from the summaries.
11. Failures are never drawn as 0 or as "slow". Electron and immuno datasets get their own panels.
12. Published references are read from `datasets/reference_ids.tsv` through `design.REFERENCE_MAP`: immuno and iPRG2015.
13. FDP beyond a single run is the per-dataset mean of run means, plus the maximum, over the shared set F (runs and realisations completed by every expected engine). Own-set values are per run only.
14. The SD is the sample SD (n−1) over s1-s3.
15. A missing realisation gives the own mean ± SD of those present, with n and a flag. Comparisons use the shared realisations.
16. Single-database sets (ups1_control, astral_s1, ultra2_s2) are reported like velos natural, without an SD.
17. For velos, natural entrapment is the main value and s1-s3 the check. Both are shown.
18. The Arabidopsis FDP is shown next to the shuffled mean ± SD of the same run, as △ in `fig_fdp`.
19. Matched FDP targets 1.0% combined, recomputed from the integer columns and te_ratio, per realisation, then averaged over the shared realisations, at both levels. It is built only when `W/counts_qgrid.tsv` exists; the q-grid stage (`qgrid.py`) is not written. Its counts go to the supplement table only, labelled; the text uses ratios.
20. lower_bound and paired FDP appear only in the per-result table.
21. Timing medians are taken per metric independently.
22. Stage times:
    - ProSE: index/search/output/total from `all.r<rep>.log`, median over r1-r3, plus the finer split from `summary.yaml` of r3, labelled;
    - Sage: from `all.r<rep>.log`;
    - MSFragger: from the timings and its search log.
23. Cross-run timing: per-dataset sums and the geometric mean of per-unit time ratios over the shared ok units T(pair), equal weight per kind, tryptic also over T3. Memory maxima are taken over the same sets. `failed_memory` is excluded.
24. Batch time per file is the batch median / n_files, compared with the Σ per-file medians of the same files. Cross-engine keys use B3.
25. Scaling: S = T1/Tn and E = S/n, with relative columns when T1 is missing. MSFragger time includes Percolator, with search-only alongside. over_limit gives a lower bound. The 16-thread point is ringed as the workstation comparison. The engine node's per_file `hfx_A2` row is drawn as a square just right of its own thread count, which the table note and legend state: at 16 threads (the paper's per_file setting) it stands beside the ring; at another count (64 in both trials) it stands at that count.
26. Memory is in GiB (2^30 bytes).
27. low_memory: medians plus the identity check. The summary is the median ratio over non-decision samples.
28. Calibration:
    - chosen settings for every MSFragger search and every ProSE per_file search;
    - a supplement table for the 9 calibration files;
    - velos with natural and s1-s3.
29. Settings are reported from repetition 3, and differences between repetitions are flagged.
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
