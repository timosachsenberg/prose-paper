# Running the benchmark

`bench.py` runs every stage of the benchmark from the run table [`runs.tsv`](runs.tsv) and the ProSE parameter files in
[`../datasets/params/`](../datasets/params/). The protocol is [`../datasets/DATASETS.md`](../datasets/DATASETS.md),
sections 4.2 to 4.5. Status: 2026-11-10.

## What you need

- Linux with Python 3 (standard library only), `/usr/bin/time` and `taskset`.
- An OpenMS build of the frozen commit, with `WITH_THERMO_RAW` (and a .NET 8 runtime) and `WITH_OPENTIMS`:
  `ProSE`, `FileConverter`, `EntrapmentEvaluator`, `FalseDiscoveryRate`.
- Sage 0.14.7 (its binary reports `sage 0.14.6`).
- MSFragger (the `.jar`) with Java, and Percolator.

```bash
export OPENMS_BIN=<OpenMS build>/bin SAGE=<path>/sage MSFRAGGER_JAR=<path>/MSFragger.jar PERCOLATOR=<path>/percolator
```

## Before the first run

1. **Write the parameter files again** with the frozen ProSE build:
   `python3 ../datasets/params/make_inis.py $OPENMS_BIN/ProSE ../datasets/params`.
   The files in the repository were written with an older build and lack `precursor:recorded_charge_outside_range`.
   Until they are rewritten, the driver refuses to run ProSE.
2. **Run the smoke test** (below) with all three engines.
3. **Run one real file** through every stage: `--only astral250pg_A2` (a 159 MB raw file).

## The smoke test

Three small BSA runs from the OpenMS examples against 680 proteins. It takes minutes and exercises every stage.
The sample is one protein, so the identification numbers mean nothing: check that every command finishes and that
`timings.tsv` and `counts.tsv` are written.

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
anything. Results of finished searches are overwritten when a search is repeated.

```bash
B="python3 bench.py --work /scratch/prose-bench"
$B versions                      # versions.txt
$B databases                     # db/, 42 databases, checked by SHA256
$B fetch                         # vendor/
$B convert                       # mzml/, mzml.sha256, one conversion log per file
```

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
$B collect                                  # counts.tsv
```

Further ProSE arms get their own result folder with `--tag`, for example the standard-mode arm of the
immunopeptidomics searches:

```bash
$B search --engine prose --db td --timed --extra '-Search:low_memory false' --tag standard_mode --only <immunopeptidomics ids>
```

## What is written

| File | Content |
|---|---|
| `commands.log` | every command line that was run |
| `timings.tsv` | one line per timed invocation: engine, benchmark, run, database, stage, threads, repetition, wall time, CPU time, peak memory, exit status. Repetition 0 is the discarded run that fills the page cache. |
| `out/<engine>/<benchmark>/<run>/<database>/` | the results of one search; `count.tsv` is the output of `EntrapmentEvaluator` |
| `counts.tsv` | all `count.tsv` in one table |
| `mzml.sha256`, `mzml/<id>.mzML.log` | the record of the conversion |
| `versions.txt` | the version output of every tool |

## What was tested, and what was not

Tested on 2026-11-10 with Sage 0.14.7 on the smoke test, on a 20-core Linux machine:

- `databases`, `fetch`, `search` (timed and untimed, plain and entrapment databases), `batch`, `scaling` with pinning,
  `count` up to the idXML file, `collect`.
- The time limit: a run over the limit is stopped together with its child processes and recorded.
- Sage accepts the configurations made from all 14 parameter files, the unspecific ones included.

Not run, because the test machine had no build of the frozen OpenMS and no MSFragger:

- ProSE, MSFragger with Percolator, `FileConverter`, `EntrapmentEvaluator`, `FalseDiscoveryRate`. Their command lines
  were checked against the sources and in `--dry-run` mode. A stand-in took the place of `EntrapmentEvaluator`.

To check on the first runs:

- `EntrapmentEvaluator` reads the idXML files the driver writes for Sage and MSFragger (OpenMS 3.1 reads them), and
  accepts a database without entrapment proteins (the plain target-decoy counts).
- MSFragger searches the spectra of the Percolator sets, which have no recorded charge, at charges 1 to 4.
- All engines treat the spectra converted from `.ms2` as centroided (DATASETS.md, section 4.0).
- On the scaling node, `lscpu -e` shows that CPUs 0 to 191 are 192 different cores.

Not scripted: the external Percolator 3.09 control and the supplement with MSFragger + MSBooster
(DATASETS.md, sections 4.2 and 4.4). ProSE + PeptDeep can be run as an extra arm with `--extra` and `--tag`.
