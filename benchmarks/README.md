# Running the benchmark

`bench.py` runs every stage of the benchmark from the run table [`runs.tsv`](runs.tsv) and the ProSE parameter files in
[`../datasets/params/`](../datasets/params/). The protocol is [`../datasets/DATASETS.md`](../datasets/DATASETS.md),
sections 4.2 to 4.5. Status: 2026-11-13.

## What you need

- Linux with Python 3 (standard library only), `/usr/bin/time` and `taskset`.
- For the memory cap (`--mem-gb`, DATASETS.md section 4.3): systemd with a user session bus (`systemd-run --user`) and
  cgroup v2 with the memory controller delegated to the user. `systemd-run` also accepts a limit it cannot enforce, so
  the driver reads the cap back before each stage that runs tools under it (`convert`, `search`, `count`, `batch`,
  `scaling`) and stops if it is not in force. By hand:
  `systemd-run --user --scope -p MemoryMax=1G -p MemorySwapMax=0 -- sh -c 'cat /sys/fs/cgroup$(cut -d: -f3 /proc/self/cgroup)/memory.max'`
  must print 1073741824.
- An OpenMS build of the frozen commit, OpenMS develop `2287ee5532` (re-frozen 2026-11-12; DATASETS.md, section 4.1),
  tagged `prose-benchmark-2026-11-12`
  (`git clone --branch prose-benchmark-2026-11-12 https://github.com/OpenMS/OpenMS`), with
  `WITH_THERMO_RAW` (and a .NET 8 runtime) and `WITH_OPENTIMS`: `ProSE`, `FileConverter`, `EntrapmentEvaluator`.
  The `count` stage computes the PSM- and peptide-level q-values itself, the same way for all three engines, from
  each engine's final score (DATASETS.md, section 4.2), so it needs no q-values from the engines. ProSE's own
  peptide-level values (`peptide q-value`) agree with it on single files within 0.02%; ProSE's own PSM-level values
  use Percolator's π0 and accept about 1% more PSMs.
- Sage 0.14.7 (its binary reports `sage 0.14.6`: the release did not raise the version in its `Cargo.toml`).
- MSFragger (the `.jar`) with Java, and Percolator 3.09 (the release of the external control; DATASETS.md, section 4.4).

```bash
export OPENMS_BIN=<OpenMS build>/bin SAGE=<path>/sage MSFRAGGER_JAR=<path>/MSFragger.jar PERCOLATOR=<path>/percolator
```

## Before the first run

1. **Check the parameter files** against your build: the files in the repository were written with the first frozen
   ProSE build (2026-11-11; the four immunopeptidomics files changed in three values on 2026-11-13). Writing them again
   with your build must give the same values:
   `python3 ../datasets/params/make_inis.py $OPENMS_BIN/ProSE <empty folder>`, then compare the values with
   `../datasets/params` (the version string and some descriptions differ between builds).
   The driver refuses to run ProSE with parameter files that lack `precursor:recorded_charge_outside_range`.
2. **Run the smoke test** (below) with all three engines.
3. **Run one real file** through every stage: `--only astral250pg_A2` (a 159 MB raw file).

## The smoke test

Three small BSA runs from the OpenMS examples against 680 proteins. The spectra are fetched from a fixed OpenMS commit
and checked against [`smoke/vendor.sha256`](smoke/vendor.sha256). It takes minutes and exercises every stage.
The two smoke databases have the decoys of the main databases since 2026-11-11 (`datasets/DATASETS.md` section 3.2;
only the decoys were replaced, the targets and the entrapment proteins are unchanged).
The sample is one protein, so the identification numbers mean nothing: check that every command finishes and that
`timings.tsv`, `counts.tsv` and `coverage.tsv` are written. With `--mem-gb`, MSFragger needs more than a 2 GB heap
even here: at 2 threads `--mem-gb 6` (2 GB) failed with `Insufficient memory!`, `--mem-gb 7` (3 GB) and `--mem-gb 8`
(4 GB) worked.

```bash
B="python3 bench.py --work /scratch/smoke --runs smoke/runs.tsv"
$B versions
$B databases && $B fetch && $B convert
for e in prose sage msfragger; do
  $B search --engine $e --db td --threads 8 --timed
  $B search --engine $e --db entrap --threads 8
  $B count --engine $e --db td && $B count --engine $e --db entrap
  $B batch --engine $e --threads 8
  $B scaling --engine $e --grid 1,2,4,8
done
$B collect
```

## The benchmark

Every command takes `--only <id>[,<id>...]` to restrict the runs and `--dry-run` to print the commands without running
anything, both before the stage name (`$B --only <id> search ...`). `--only` also takes sample names; an
immunopeptidomics sample is searched and counted as a whole, so a part of its replicates is refused. A search empties
its result folder first, so a repeated search replaces the earlier one completely.

Every engine invocation runs under the same memory cap, without swap: `--mem-gb N` (DATASETS.md section 4.3; N is
recorded with the RAM of the node). MSFragger's Java heap is N − 4 GB and at least 1 GB, so MSFragger needs `--mem-gb 5`
or more; its JVM runs with `-XX:+ExitOnOutOfMemoryError`. Without `--mem-gb` the heap is 80% of the memory the driver
may use (the RAM, capped by its cgroup); `commands.log` names the heap and its source. A run killed at the cap, or
stopped by its engine's own out-of-memory error (MSFragger's full heap or `Insufficient memory!`, `std::bad_alloc`,
Rust's `memory allocation of … bytes failed`), is recorded as `failed_memory` and the stage goes on with the other runs.
Without `--mem-gb` every failure is recorded as `failed`, as a kill by the kernel's out-of-memory killer cannot be told
from other kills.

Each search folder holds `status`, written as `running …` before the engine starts; `count` counts only a search with
status `ok`. Ctrl-C, SIGTERM, SIGHUP and SIGQUIT stop the driver together with its engine and leave `interrupted …`,
also when the signal comes while the engine starts.
After a SIGKILL of the driver its engine may still run: the folder then stays `running`, and a new search there is
refused until that engine has ended (`kill -- -<pgid>`, with the process group named in `status`). Several drivers may
share a work directory only if they never run the same search folder, and never two MSFragger searches against the same
database at once (its digest cache lies next to the database). The folders of the pilot of 2026-11-12 have no `status`
and are not counted until `ok` is written into them after a check.

```bash
B="python3 bench.py --work /scratch/prose-bench --mem-gb <N>"
$B versions                      # versions.txt
$B databases                     # db/, 34 databases, checked by SHA256 and for usable accessions
$B fetch                         # vendor/, every file checked against vendor.sha256
$B convert                       # mzml/, mzml.sha256, one conversion log per file
```

`fetch` also checks the files that are already there, so running it again checks a copied work directory (138 GB to
read). A file with another SHA256 stops the stage: a new download is kept as `<file>.bad`, an old file is named for you
to delete and fetch again. `databases` replaces a database in `db/` whose SHA256 differs from the list, e.g. one from
before the rebuild of 2026-11-11 (new decoys, `datasets/DATASETS.md` section 3.2), and logs it.

On the node of the engine comparison (64 threads), for each engine `prose`, `sage`, `msfragger`:

```bash
$B search --engine $e --db td --timed       # counts and per-file timings
$B search --engine $e --db entrap           # entrapment searches (three realisations, or the natural entrapment)
$B search --engine $e --db ref              # Arabidopsis reference (HF-X, Astral, TMTpro)
$B count  --engine $e --db td               # PSMs and peptides at q <= 0.01
$B count  --engine $e --db entrap           # entrapment FDP
$B count  --engine $e --db ref
$B batch  --engine $e                       # batch arm
```

On the node of the thread scaling:

```bash
$B scaling --engine $e                      # 9 files, 192 threads down to 1, pinned, 24 h limit per run
```

At the end:

```bash
$B collect                                  # counts.tsv, coverage.tsv
```

Further arms get their own result folder with `--tag` (`per_file_<tag>`; `--extra` needs it). `--extra` takes ProSE
options, Sage configuration keys (`key=JSON`, e.g. `deisotope=false`) or MSFragger parameters (`key=value`, e.g.
`calibrate_mass=0`); the driver refuses Sage and MSFragger keys the engine does not know, before any search folder is
touched and also with `--dry-run`; ProSE options are passed on unchecked, so ProSE itself checks them when the search
runs. Sage's `write_pin` and `annotate_matches` take `true` or `false` and become its flags `--write-pin` and
`--annotate-matches`, as Sage 0.14.7 overwrites these two keys of its configuration with its command-line flags. For
example the `low_memory` arm of the immunopeptidomics searches (the main arm runs ProSE's standard mode):

```bash
$B --only <immunopeptidomics samples> search --engine prose --db td --timed --extra '-Search:low_memory true' --tag low_memory
```

The calibration supplement (DATASETS.md, section 4.4): ProSE without its calibration and MSFragger with calibration
only and without it, next to their main arms. Sage has no arm: it does not calibrate, so its main arm is its search
without calibration, and it keeps the fragment tolerance of the parameter file (decided 2026-11-13; the Sage arm
`--prose-fragment-tol`, which took its tolerance from ProSE's calibration, was removed).

```bash
A=hfx_A2,astral_A2,velos_125_R1,lumos_lfq_5192,lumos_tmt_5058,eclipse_tmtpro_10855,tims_plasma_30min
A=$A,2015_12_21_12_42_Orbitrap-Fusion-Lumos_FSN20115,pxd011695_HCD   # ion-trap runs, since 2026-11-13
for db in td entrap; do
  $B --only $A search --engine prose --db $db --extra '-Search:calibration:enabled false' --tag cal_off
  $B --only $A search --engine msfragger --db $db --extra calibrate_mass=1 --tag cal1
  $B --only $A search --engine msfragger --db $db --extra calibrate_mass=0 --tag cal0
  for arm in "prose cal_off" "msfragger cal1" "msfragger cal0"; do
    set -- $arm
    $B --only $A count --engine $1 --db $db --tag $2
  done
done
```

## What is written

| File | Content |
|---|---|
| `commands.log` | every command line that was run; `# FAILED:` marks an engine step that exited with an error, with `(out of memory)` for `failed_memory` (the remaining steps of that search, e.g. Percolator on MSFragger's `.pin`, and its further repetitions are not run; the other searches run, and the stage ends with a non-zero exit and the list of failures); `# NOT COUNTED:` marks a search that `count` skipped, with the reason (status not `ok`, inputs other than the run table's, a missing, cut or unreadable result, an accession not in the database, `EntrapmentEvaluator` failed), after which it counts the others; `# NO TIMING:` a timed run without output of `/usr/bin/time`; `# MSFragger Java heap …` the heap and where it came from; `rm …pepindex` the removal of MSFragger's digest cache before each of its searches |
| `timings.tsv` | one line per timed invocation: engine, benchmark, run, database, stage, threads, repetition, wall time, CPU time, peak memory, exit status (`NA` and `no_timing` when `/usr/bin/time` gave no output). Repetition 0 is the discarded run that fills the page cache. MSFragger's search, join and Percolator are rows of their own; the analysis sums them per repetition (DATASETS.md section 4.3); in its batch arm every file's Percolator is a `rescoring` row with the same keys. |
| `out/<engine>/<benchmark>/<run>/<database>/` | the results of one search; `inputs` the run ids it searched; `status` its outcome (`running …` while it runs, then `ok`, `failed …`, `failed_memory …`, `over_limit …` or `interrupted …`); `<stage>.log` (timed: `<stage>.r<repetition>.log`) the output of each engine step, e.g. the tolerances its calibration chose (in MSFragger's batch arm the `rescoring` log keeps only the last file's Percolator); `<run>.count.idXML` (pooled samples: `pooled.count.idXML`) holds what is counted, the target top hits with the PSM- and peptide-level q-values of the driver (decoys equal to a target peptide with I = L counted as targets, and target PSMs that also map to a decoy protein labelled by the same search space, DATASETS.md section 4.2); `count.tsv` is the output of `EntrapmentEvaluator` on it, written only when it ends without error |
| `counts.tsv` | all `count.tsv` in one table (removed by `collect` when there is none) |
| `coverage.tsv` | every search the run table asks for and every further search folder, with its status (`not_run` without a folder, `not_run_by_design` for Sage on the electron-based runs, `unknown` for a folder without `status`) and whether it was counted: the basis of the comparisons over shared runs (DATASETS.md section 4.2); why a search was not counted is in `commands.log` |
| `mzml.sha256`, `mzml/<id>.mzML.log` | the record of the conversion |
| `versions.txt` | the version output of every tool |

## What was tested, and what was not

Tested on 2026-11-10 with Sage 0.14.7 on the smoke test, on a 20-core Linux machine:

- `databases`, `fetch`, `search` (timed and untimed, plain and entrapment databases), `batch`, `scaling` with pinning,
  `count` up to the idXML file, `collect`.
- The time limit: a run over the limit is stopped together with its child processes and recorded.
- Sage accepted the configurations made from the parameter files of then, the unspecific ones included.

Tested on 2026-11-11 (WSL2, Ubuntu 24.04, 20 cores):

- `fetch` with its SHA256 checks on the smoke test (download, files already there, a damaged file, a wrong download, a
  run table without `vendor.sha256`) and on one file of the main table, and `versions` with Sage 0.14.7, MSFragger
  4.4.1 and Percolator 3.09.
- With the frozen OpenMS build (a native copy of the Docker image), Sage 0.14.7, MSFragger 4.4.1 and Percolator 3.09:
  the smoke test, every command above in its order, with all three engines (every step exit 0); and every stage with
  all three engines on `astral250pg_A2` and on `ultra2_A2` (timsTOF, MS2-only mzML). `EntrapmentEvaluator` reads the
  idXML files the driver writes and accepts a database without entrapment proteins (the plain target-decoy counts).
- After the changes of that day (isotope-error sign, minimum matched ions, peptide-level q-values in the driver;
  DATASETS.md, section 5): `search` and `count` of both files again, with all three engines. On 2026-11-12 `count`
  again on `astral250pg_A2` after the PSM-level q-values moved into the driver (plain and entrapment database).

Tested on 2026-11-12 after the changes of that day (peptide mass bounds as neutral masses, MSFragger's window
translation, `--extra` for Sage and MSFragger, `--prose-fragment-tol`, engine logs): `search` and `count` of
`astral250pg_A2` with the plain and the s1 entrapment database, all three engines and the four arms the calibration
supplement had then (the Sage arm was removed on 2026-11-13); every step exit 0, the main counts unchanged
(DATASETS.md, section 4.5).

Tested on 2026-11-13 after the changes of that day (memory cap, MSFragger's digest cache and uncalibrated spectra,
status and coverage, I = L twins and target+decoy labels, protein lists and accession checks, MSFragger's mass bounds,
Sage's fragment charges, telemetry, Sage's one-thread point, interrupted and concurrent runs), with the frozen build,
Sage 0.14.7, MSFragger 4.4.1 and Percolator 3.09 (WSL2, 20 cores; counts in DATASETS.md, section 4.5):

- MSFragger on `velos_5000_R2` under the memory cap: the digest cache is removed before the search, `status` is
  written, and without the uncalibrated spectra the `.pin` and Percolator's results are byte-identical.
- `tims_plasma_30min` and `astral_A2`, all three engines, plain and s1 entrapment database: every step exit 0.
- The smoke test above with the final driver of that day, all three engines (`--mem-gb 16`, `--threads 4`,
  `scaling --grid 1,2`): 23 of 23 steps exit 0; `coverage.tsv` lists 27 search folders, all `ok`, and its 18 counted
  ones are those of `counts.tsv`; `timings.tsv` has 100 rows, all exit 0 and with times. 64 dry runs of every stage
  with both run tables exit 0 and create no work directory.
- One test per failure case: two timed drivers in one work directory (all timings complete); SIGINT, SIGTERM and
  SIGHUP (the engine is stopped, `status` says `interrupted`, `count` does not count the folder); a SIGKILL of the
  driver (a new search of the folder is refused while the orphaned engine runs); out of memory (`failed_memory` for
  MSFragger's full heap, exit 3, for its `Insufficient memory!`, exit 1, and for ProSE and Sage killed at a 1 GB cap,
  exit 137); a part of a pooled sample in `--only` (refused); a failing `EntrapmentEvaluator`, a cut idXML, a cut Sage
  table and an empty Percolator table (that search not counted, the others counted); a stale `counts.tsv` (removed); a
  moved work directory (MSFragger's input links re-pointed); unknown `--extra` keys (refused before any folder is
  touched, also in a dry run); no user session bus with `--mem-gb` (stops before any search); a database header with
  `;`, a repeated or a vertical-tab first word (refused by `databases`), and an accession not in the database (refused
  by `count`). As tests of the driver's functions: a stop signal while a command starts (600 calls, no command left
  running), a stop while stderr is a broken pipe or a closed file (the driver still ends as for the signal), four
  processes writing the first row of a new `timings.tsv` at once (500 times, the header always on line 1), and an
  out-of-memory exit without `--mem-gb` (recorded as `failed`).
- `count` again on all pilot searches of 2026-11-12 (no new searches; status `ok` written into copies of the pilot
  folders): only ProSE on `pxd011695_EThcD` changes, by the target+decoy rule (DATASETS.md section 4.2); every Sage,
  MSFragger and pooled count is unchanged.
- Not seen in a test: Sage's own out-of-memory message, `std::bad_alloc` and SIGQUIT (handled like SIGTERM).
- After the `astral_A2` analysis of that day (Sage's `write_pin` and `annotate_matches` as flags; the Sage arm
  `--prose-fragment-tol` removed): the 64 dry runs exit 0 with the same command lines as before; a Sage search of one
  smoke file with `--extra 'write_pin=true annotate_matches=true'` wrote `results.sage.pin` and
  `matched_fragments.sage.tsv`.

Checked in the pilot of 2026-11-12 (DATASETS.md, section 5, task 6):

- MSFragger searches the timsTOF precursors without a charge at the charges of the parameter file, as ProSE and Sage
  do.
- Sage's default deisotoping costs it no identifications on the 0.5 Da ion-trap spectra.

To check on the first runs:

- Sage's pooled count on an immunopeptidomics sample. Its unspecific searches need the memory of the benchmark nodes.
- On the scaling node, `lscpu -e` shows that CPUs 0 to 191 are 192 different cores.
- On one class II sample, the oxidised forms at MSFragger's lower peptide mass bound (DATASETS.md section 4.4).

Not scripted: the external Percolator 3.09 control (one hit per spectrum; the same call on the Percolator input of all
three engines is proposed, DATASETS.md section 4.2), the supplement with MSFragger + MSBooster (DATASETS.md, sections 4.2 and 4.4), and the summaries over
`counts.tsv`, `coverage.tsv` and `timings.tsv`: the comparisons over shared runs with the geometric mean of the per-run
ratios, the mean ± SD of the FDP over the realisations, the medians of the repetitions, speed-up, efficiency and stage
times, and the table of the settings each calibration chose (DATASETS.md, section 4.5). ProSE + PeptDeep can be run as an extra arm with `--extra` and `--tag`.
