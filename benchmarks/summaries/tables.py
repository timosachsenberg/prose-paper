"""Shared loader layer of the summaries (SPEC sections 2.1-2.7): loaders with every validation stop, units, the
database design, batch groups, scaling runs, counts/coverage/timings normalisation, timing attempts with
per-repetition totals, Missing values, comparison sets, stats helpers, and the Ctx object that the modules build on.

Citation keys as in the SPEC: DS = datasets/DATASETS.md, B = benchmarks/bench.py, OT = benchmarks/overtuning.py,
RM = benchmarks/README.md, EE-tool / EE-lib = EntrapmentEvaluator sources at P.

========================================================================================================================
Ctx API (the contract of the module authors)
========================================================================================================================
summarize.py builds one Ctx with load(Options(...)) and calls fdp.build(ctx), ids.build(ctx), timing.build(ctx),
calib.build(ctx), then checks.run(ctx); then it writes numbers.tsv/.tex, provenance.tsv and check_report.txt; then
figures.draw(tables_dir, figures_dir, report) reads only the written tables (read_table below).

Module-level names (from summaries import tables as T)
  T.Missing(reason)            frozen dataclass; bool(Missing) is False; formats as 'NA'. T.is_missing(x) is True for
                               Missing, None and float NaN. Reasons are those of SPEC 2.6: not_counted, failed_memory,
                               failed, not_run_by_design, not_run, running, interrupted, unknown, over_limit, zero,
                               none_accepted, decision, incomplete, no_timing, stale_timing, not_run_over_limit,
                               outside_design, empty; plus no_coverage (no coverage row), missing_count (coverage says
                               counted but counts.tsv has no row) and no_timing_rows (no timings row of the key).
  T.ValidationStop(message)    SystemExit subclass with code 2 (SPEC 1 "Exit codes"); T.stop(path, line, column,
                               value, allowed) raises it with a message naming file, line, column, value, allowed set.
  Stats helpers (SPEC 2.7; every one returns Missing('empty') on empty input; a Missing element is returned as is,
  i.e. it propagates; numbers are summed with math.fsum):
    T.gmean(xs) -> float         exp(fsum(log x)/n); x <= 0 raises ValueError (zeros are dropped before ratios)
    T.median(xs) -> float        statistics.median
    T.fmean(xs) -> float         fsum(xs)/n
    T.mean_sd(xs) -> (mean, sd)  sample SD (n-1); sd = Missing('n<2') for one value; (Missing, Missing) when empty
    T.gib(kb) -> float           kb / 2**20 (GiB, OPEN Q26); Missing passes through
    T.sum_ratio(ps, cs) -> float fsum(ps)/fsum(cs); Missing('zero') if fsum(cs) == 0
    T.ratio(p, c) -> float       p/c; Missing('zero') if p or c is 0; Missing operands pass through
    T.lead(x) -> float           100*(x-1); Missing passes through
  Formats (SPEC 3 "Formatting"): T.fmt(value, spec) -> str ('NA' for Missing/None/NaN, 'yes'/'no' for bool, str(int),
    format(float, spec)); T.FMT_RATIO '.6f' (default of every float column), T.FMT_LEAD '.1f', T.FMT_PCT '.2f',
    T.FMT_GIB '.3f', T.FMT_S '.2f'.
  Keys: T.normalise_db('hye_td.fasta') -> 'hye_td'; T.split_scaling_db('hye_td_t16') -> ('hye_td', 16) (B:196, 891).
  Readers: T.read_tsv(path, exact_header=None, required=None) -> (header, [(line, {col: str})]);
    T.read_table(path) -> (columns, [{col: str}]) for figures (skips '#' lines);
    T.parse_yaml(text) / T.read_yaml(path) -> dict (the summary.yaml subset; SPEC 1 "No PyYAML");
    T.read_versions(path) -> [(command, text)] (B:357); T.read_machine(path) -> [(section, key, value)];
    T.read_listing(path) -> {name: {'size', 'month', 'day', 'time', 'year', 'text', 'key'}} ('ls -l' of W; 'key' sorts
    by date when the listing shows times, i.e. within one year).
  Files: T.write_atomic(path, text) (tmp + os.replace); T.sha256_file(path) -> hex digest (provenance, O13, C2).
  Constants: T.COUNTS_HEADER, T.COVERAGE_HEADER, T.TIMINGS_HEADER, T.STATES, T.ONLY_KEYWORDS, T.SOURCE_SIDES.

Data classes (all fields plain Python values; '-' as in the run table)
  Run         id set group format params db entrap ref ions sample scaling role line; entrap/ref are tuples of file
              names as in runs.tsv ('-' dropped).
  Unit        (SPEC 2.1) name runs pooled group role set kind cls grade td entrap ref ions scaling_runs expected
              count_file, plus sample params db side instrument display n_files.
              runs: tuple of run ids in table order; entrap: ((stem, design, realisation), ...) with design 'shuffled'
              (realisation 1..3; None for the smoke database under --design none) or 'natural' (None);
              ref: (stem, ...) of design 'arath'; expected: the engines expected on the unit, in ENGINES order (prose,
              sage only if ions == 'by', msfragger; B:161-165, 1357); kind 'tuning'|'heldout'|'electron'|'immuno'|
              'other'; side 'tuning'|'heldout'|None; is_decision property (role == 'decision').
              u.stems -> (td, entrap stems..., ref stems...); u.design_of(stem) -> (design, realisation) with design
              'td'|'shuffled'|'natural'|'arath', or None for a stem outside the unit; u.stems_of(design) -> [stems].
  Group       name kind cls grade side instrument display units (tuple of unit names) runs (tuple of run ids)
              n_runs n_decision.
  BatchGroup  (SPEC 2.1) name runs n_files td kind cls grade side ions expected n_decision (rows with sample == '-',
              grouped by group, at least 2 files, decision runs included; B:974-977).
  CountRow    line engine benchmark tag run database file level q_value accepted entrapment lower_bound_fdp
              combined_fdp paired_fdp entrapment_target_not_accepted entrapment_above_target te_ratio design
              realisation unit. The three NA-able columns are None when NA; lower_bound/combined are floats (the
              smoke prints ints). design: 'td'|'shuffled'|'natural'|'arath'|'rule11b'|'outside_design'; tag: None
              for per_file, else the text after 'per_file_'; unit: the Unit or None.
  CoverageRow line engine benchmark tag run database (as in the file) db (stem; for scaling the td without _t<n>)
              threads (scaling only, else None) status state counted (bool) design realisation scope
              ('unit'|'batch'|'scaling') unit (Unit or None) group (BatchGroup or None). state = first word of
              status (one of STATES).
  TimingRow   line engine benchmark tag run database db stage threads repetition wall cpu rss_kb exit; wall/cpu
              None for NA/nan, rss_kb None for NA; exit an int or 'over_limit'|'not_run_over_limit'|'no_timing'.
  Rep         repetition rows stages ({stage: n}) wall cpu (fsum, or Missing) rss_kb (max, or Missing) stage_wall
              ({stage: fsum}) complete (bool) problem (str).
  Attempt     index threads rows reps ({r: Rep}) state ('complete'|'incomplete'|'no_timing'|'over_limit') note
              limit lower_bound.
  Timing      key = (engine, benchmark, run, db, threads) with threads None except for scaling (SPEC 2.5 "Attempt
              key"); engine benchmark run db threads (of the attempt used); state 'complete'|'incomplete'|
              'no_timing'|'over_limit'|'not_run_over_limit'|'stale_timing'; note; attempts (all, file order);
              attempt (the last one, used; None if only not_run_over_limit rows); n_attempts; reps ({r: Rep} of the
              used attempt, repetition 0 included but never used for a value); wall_r / cpu_r / rss_r_kb
              ({1: v, 2: v, 3: v}); wall_med cpu_med rss_med_kb (median over r = 1..3 per metric independently,
              OPEN Q21; Missing(state) unless complete); stage_wall_med ({stage: median over r of the stage's sum});
              limit (L of an over_limit / not_run_over_limit row, else None; never a wall time); lower_bound
              (over_limit: min of the completed repetition totals and L, SPEC 2.5; else Missing); expected (stage
              multiset); unit (Unit, per_file and scaling) group (BatchGroup, batch) n_files.

load(options) -> Ctx; Options(...) fields: runs work counts coverage timings versions scaling_work scaling_coverage
  scaling_timings scaling_versions runs_11b rule11b_work out (None: nothing is written) design ('paper'|'none')
  params_dir levels only logs ('yes'|'no'|'auto') strict expect_threads references mzml_counts listing machines
  ([(label, path)]) gc_logs command_line. Paths left None default to <work>/<file> (scaling ones to <scaling_work>/...,
  scaling_work defaulting to work).

Ctx attributes
  options strict design_mode levels only expect_threads (strict default 16)
  work out tables_dir figures_dir (None when options.out is None)
  out_dir (W/out) scaling_out_dir (S/out) logs_available (bool: --logs yes or auto, and W/out exists)
  scaling_logs_available (the same for S/out; equal to logs_available without a separate --scaling-work)
  runs [Run] run_by_id {id: Run}
  units [Unit] in run-table order of first appearance; unit_by_name {name: Unit}; unit_of_run {run id: Unit}
  groups {group: Group} in run-table order; batch_groups {group: BatchGroup} in table order
  scaling_runs (run ids with scaling == '1', B:985-993)
  pooled_arrangement ('per_file'|'joint'|... or None without immuno groups); pooled_arrangement_files [(path, mode)]
  other_arrangement_tag ('mode_joint'|'mode_per_file'|None)
  rule11b_pairs {(unit name, stem)} from --runs-11b (DS:1056); rule11b_work
  counts [CountRow] inside the design (per_file and every arm); counts_outside [CountRow] (excluded, listed in O14);
  counts_rule11b [CountRow] (for O9b); count_index {(engine, benchmark, unit, db, level): CountRow}
  tags (sorted tags seen in counts/coverage/timings); unknown_tags (tags not in design.ARMS: generic arms, O25)
  coverage [CoverageRow] inside the design; coverage_outside [CoverageRow]; coverage_index {(engine, benchmark, run,
  database as in the file): CoverageRow}
  timing_rows [TimingRow] inside the design; timing_outside [TimingRow]; timings {key: Timing} in file order of
  their first row; earlier_attempts [(key, n_earlier)] (C5)
  unflagged_scaling [CoverageRow] (scaling run not flagged in runs.tsv: WARN, B:986)
  versions / scaling_versions [(command, text)] or None; mzml_counts {run id: {col: int|str}} or None
  listing {name: {...}} or None; references_path; machines [(label, path)]; gc_logs
  inputs {path: item} (every input file, for provenance.tsv; record more with ctx.record_input(path, item))
  results {table name: [row dict with typed values]}; result_columns {table name: [columns]}
  numbers [Number]; report (Report); shared {} (free dict for values passed between modules, e.g. O15 to O16)

Ctx methods (unit arguments take a Unit or a unit name)
  want(keyword) -> bool                  --only selection (keywords: ONLY_KEYWORDS); True without --only
  unit(name_or_unit) -> Unit             KeyError for an unknown name
  select_units(kinds=None, groups=None, decision=True) -> [Unit]   in table order; decision=False drops decision units
  search_reason(engine, benchmark, run, db) -> str | None   SPEC 2.6 reason of a per_file* search, None if counted
  coverage_row(engine, benchmark, run, database) -> CoverageRow | None   database as in the file ('hye_td_t16' scaling)
  count_row(engine, unit, level, db=None, benchmark='per_file') -> CountRow | None   db defaults to unit.td
  accepted(engine, unit, level, db=None, benchmark='per_file') -> int | Missing      zero is returned as 0
  fdp(engine, unit, db, level, benchmark='per_file') -> float | Missing   combined_fdp; Missing('none_accepted') if N=0
  reason(unit, engines, level, db=None, benchmark='per_file', positive=True) -> str | None
                                         why a unit is out of a set: 'decision', or '<engine>:<reason>' ('zero' when
                                         positive and accepted == 0); None when in
  E(unit) -> tuple                       expected engines (SPEC 2.7)
  R(pair, level, units=None, benchmark='per_file') -> [Unit]   non-decision, both counted on td, both accepted > 0
  R3(level, units=None, benchmark='per_file') -> [Unit]        the same with all three engines
  C(group, level, engines=None) -> [Unit]   non-decision units of the group whose td search every engine of E(u)
                                         (or of engines) counted, zero allowed (O1)
  F(level, design_name, engines=None, units=None, benchmark='per_file') -> {unit name: [stems]}   per non-decision
                                         unit, the stems of design_name ('shuffled'|'natural'|'arath') that every
                                         engine of E(u) (or engines) counted with accepted > 0; units without one
                                         are absent
  timing(engine, benchmark, run, db=None, threads=None) -> Timing | None   db defaults to the unit's/group's td
  timing_value(engine, benchmark, run, db=None, threads=None) -> Timing | Missing   the Timing only if its coverage
                                         state is ok and the last attempt is complete; else Missing(reason)
  T(pair, units=None, benchmark='per_file') -> [Unit]   non-decision units whose per_file td timing_value exists for
                                         both engines;  T3(units=None, benchmark='per_file') -> [Unit] all three
  B3() -> [group name]                   batch groups (table order) whose batch ratio (O16) exists for every engine
                                         of E: batch timing_value and the per_file td timing_value of every file
  search_dir(engine, benchmark, run, db, threads=None) -> path of W/out/<engine>/<benchmark>/<run>/<db>[_t<n>] (B:195)
                                         (S/out/... for scaling)
  logs_for(benchmark) -> bool            scaling_logs_available for scaling, logs_available otherwise
  write_table(name, columns, rows, formats=None, header_note=None, auto_note=False) -> path | None
                                         name = the SPEC file stem ('O02_pairs_runs'); rows: dicts (every column
                                         present, no other key) or sequences in column order; atomic write of
                                         <out>/tables/<name>.tsv (tmp + os.replace); floats as formats.get(col,
                                         FMT_RATIO), Missing/None as NA, bool as yes/no; header_note: a first line
                                         '# <text>' (read_table skips it); auto_note: fill an empty 'note' column
                                         with the Missing reasons of the row; stores the typed rows in
                                         ctx.results[name]; a name written twice raises ValueError
  write_file(relpath, text) -> path | None   atomic text file under <out> (e.g. 'sentence_overtuning_psm.txt',
                                         'tables/O04_overtuning_psm.stdout.txt')
  number(key, value, text=None, unit='', output='', protocol_ref='', source_side='none', main_text_allowed=None)
                                         one numbers.tsv row (SPEC 3.8): key ^[a-z0-9_.]+$ and unique (else
                                         ValueError); value int/float/str/bool/Missing (written with repr for
                                         floats); text for the paper (default: str(value), 'NA' for Missing; pass it
                                         formatted); source_side in SOURCE_SIDES; main_text_allowed 'yes'|'no'|bool,
                                         default 'no' for identification-ratio keys (ids., three., cal., percolator.,
                                         prediction.) unless source_side == 'heldout', else 'yes' (C19)
  check(level, cid, message, strict=False)  one check_report line 'LEVEL CID message'; level PASS|WARN|FAIL|INFO;
                                         strict=True marks a WARN(s) of SPEC 5, which --strict turns into FAIL
  record_input(path, item)               adds a file to provenance.tsv
  gmean median fmean mean_sd gib sum_ratio ratio lead Missing is_missing   the module-level helpers, as attributes

Report (ctx.report; the third argument of figures.draw)
  report.check(level, cid, message, strict=False); report.lines [(level, cid, message)]; report.count(level) -> int;
  report.n_fail -> int; report.text() -> str. Whitespace in cid and message is collapsed to single blanks.

Conventions of the contract
  - Modules only read ctx and write through write_table / write_file / number / check; they never write elsewhere.
  - A ValidationStop raised by a module (e.g. an unexpected string in reference_ids.tsv, SPEC O24) ends the build
    with exit 2; any other exception becomes 'FAIL MODULE <name>: <exception>' (traceback in <out>/errors.txt).
  - The loader records but does not report its findings: counts_outside, coverage_outside, timing_outside,
    counts_rule11b, unknown_tags, unflagged_scaling and earlier_attempts are reported by checks.py (C3, C5, C11, C12).
    The loader itself writes only INFO LOAD / LOGS lines (and a WARN(s) LOAD when counts.tsv is absent).
  - write_file records its relpath in ctx.shared['written'] (summarize.py then keeps those files; it removes tables of
    an earlier build that a full build did not write, so figures never read a stale table).
"""
import csv
import hashlib
import math
import os
import re
import statistics
from collections import OrderedDict
from dataclasses import dataclass

from . import design

ENGINES = design.ENGINES
LEVELS = design.LEVELS
HERE = os.path.dirname(os.path.abspath(__file__))
BENCH = os.path.dirname(HERE)
REPO = os.path.dirname(BENCH)

# ---------------------------------------------------------------- formats (SPEC 3 "Formatting")
FMT_RATIO = ".6f"  # ratios: 6 decimals in TSVs (as OT:122-123); the default of every float column
FMT_LEAD = ".1f"  # leads 100(x-1) in text (OT:68, 75)
FMT_PCT = ".2f"  # FDP in %
FMT_GIB = ".3f"  # memory in GiB
FMT_S = ".2f"  # times in s (timings.tsv has 2 decimals, B:330)

# ---------------------------------------------------------------- headers and value sets
RUNS_COLUMNS = ("id", "set", "group", "format", "url", "params", "db", "entrap", "ref", "ions", "sample", "scaling",
                "role")  # runs.tsv:1
COUNTS_HEADER = ["engine", "benchmark", "run", "database", "file", "level", "class", "q_value", "accepted",
                 "entrapment", "lower_bound_fdp", "combined_fdp", "paired_fdp", "entrapment_target_not_accepted",
                 "entrapment_above_target", "te_ratio"]  # B:1380-1383 + EE-tool:196
COVERAGE_HEADER = ["engine", "benchmark", "run", "database", "status", "counted"]  # B:1368-1369
TIMINGS_HEADER = ["engine", "benchmark", "run", "database", "stage", "threads", "repetition", "wall_s", "cpu_s",
                  "max_rss_kb", "exit"]  # B:329, 340
STATES = ("ok", "failed", "failed_memory", "interrupted", "running", "not_run", "not_run_by_design", "unknown",
          "over_limit")  # B:905-937, 1357-1363; DS:622
TIMING_EXITS = ("over_limit", "not_run_over_limit", "no_timing")  # B:298-313, 996-999
ROLES = ("tuned", "heldout", "decision")
SETS = ("tuned", "heldout")
ONLY_KEYWORDS = ("coverage", "ids", "overtuning", "electron", "immuno", "rule11b", "lowmem", "fdp", "matched", "time",
                 "stages", "batch", "scaling", "calibration", "percolator", "prediction", "references", "arms",
                 "pairing", "datasets")  # SPEC 1, --only
SOURCE_SIDES = ("heldout", "tuning", "decision", "mixed", "none")  # SPEC 3.8
# C19 (SPEC 5); fdp.matched.* (O13: ProSE/comparator leads at a matched FDP) are identification ratios as well,
# beyond the SPEC's list, so that C19 guards their main_text_allowed too
ID_RATIO_FAMILIES = ("ids.", "three.", "cal.", "percolator.", "prediction.", "fdp.matched.")
KEY_PATTERN = re.compile(r"^[a-z0-9_.]+$")  # SPEC 3.8
TABLE_NAME = re.compile(r"^O\d\d[a-z]?_[A-Za-z0-9_.+-]+$")
TAG_PATTERN = re.compile(r"^[A-Za-z0-9_.+-]+$")
SHUFFLED = re.compile(r"^(.+)_entrap_s([123])_td$")  # SPEC 2.1 "Database design"
NATURAL = re.compile(r"^.+_natural_td$")
ARATH = re.compile(r"^.+_arath_td$")
SCALING_DB = re.compile(r"^(.+_td)_t(\d+)$")  # B:196, 891
DEFAULT_RUNS = os.path.join(BENCH, "runs.tsv")
DEFAULT_RUNS_11B = os.path.join(BENCH, "pooled_rule_runs.tsv")
DEFAULT_REFERENCES = os.path.join(REPO, "datasets", "reference_ids.tsv")
DEFAULT_MZML_COUNTS = os.path.join(REPO, "datasets", "mzml_counts.tsv")
DEFAULT_PARAMS = design.PARAMS


# ---------------------------------------------------------------- validation stops (SPEC 1 "Exit codes")
class ValidationStop(SystemExit):
    """An input validation stop: exit code 2, the message names the file, line, column, value and allowed set."""

    def __init__(self, message):
        super().__init__(message)
        self.message = message
        self.code = 2

    def __str__(self):
        return self.message


def stop(path, line, column, value, allowed):
    raise ValidationStop(f"{path}: line {line}, column {column}: value {value!r} not allowed; allowed: {allowed}")


# ---------------------------------------------------------------- Missing (SPEC 2.6)
@dataclass(frozen=True)
class Missing:
    """A value that does not exist, with its reason (SPEC 2.6). Written as NA (plus a note) in every TSV."""
    reason: str

    def __bool__(self):
        return False

    def __str__(self):
        return "NA"


def is_missing(x):
    return x is None or isinstance(x, Missing) or (isinstance(x, float) and math.isnan(x))


def _first_missing(xs):
    for x in xs:
        if isinstance(x, Missing):
            return x
        if x is None or (isinstance(x, float) and math.isnan(x)):
            return Missing("NA")
    return None


# ---------------------------------------------------------------- stats helpers (SPEC 2.7)
def gmean(xs):
    """Geometric mean exp(fsum(log x)/n) (SPEC 2.7; OT:34-35 uses plain sum, so values agree with OT to rounding)."""
    xs = list(xs)
    if not xs:
        return Missing("empty")
    m = _first_missing(xs)
    if m is not None:
        return m
    if any(x <= 0 for x in xs):
        raise ValueError("gmean of a non-positive value (zero counts are dropped before any ratio, OT:113-116)")
    return math.exp(math.fsum(math.log(x) for x in xs) / len(xs))


def median(xs):
    """statistics.median (SPEC 2.7); the median of 100, 100, 120 is 100 (SPEC T13)."""
    xs = list(xs)
    if not xs:
        return Missing("empty")
    m = _first_missing(xs)
    if m is not None:
        return m
    return statistics.median(xs)


def fmean(xs):
    xs = list(xs)
    if not xs:
        return Missing("empty")
    m = _first_missing(xs)
    if m is not None:
        return m
    return math.fsum(xs) / len(xs)


def mean_sd(xs):
    """(mean, sample SD with n-1) (SPEC 2.7; OPEN Q14); SD is Missing('n<2') for a single value."""
    xs = list(xs)
    if not xs:
        return Missing("empty"), Missing("empty")
    m = _first_missing(xs)
    if m is not None:
        return m, m
    mean = math.fsum(xs) / len(xs)
    if len(xs) < 2:
        return mean, Missing("n<2")
    return mean, math.sqrt(math.fsum((x - mean) ** 2 for x in xs) / (len(xs) - 1))


def gib(kb):
    """kB -> GiB, kb / 2**20 (SPEC 2.7; OPEN Q26: the cap is in GiB, DS:653)."""
    if is_missing(kb):
        return kb if isinstance(kb, Missing) else Missing("NA")
    return kb / 2 ** 20


def sum_ratio(ps, cs):
    """Ratio of sums fsum(P)/fsum(C) over the same run set (SPEC O2 step 2-3; OPEN Q2)."""
    ps, cs = list(ps), list(cs)
    if not ps or not cs:
        return Missing("empty")
    m = _first_missing(ps + cs)
    if m is not None:
        return m
    c = math.fsum(cs)
    if c == 0:
        return Missing("zero")
    return math.fsum(ps) / c


def ratio(p, c):
    """p / c; Missing('zero') when either count is 0 (zero counts are out of every ratio, OT:113-116)."""
    m = _first_missing([p, c])
    if m is not None:
        return m
    if p == 0 or c == 0:
        return Missing("zero")
    return p / c


def lead(x):
    """100(x - 1), a lead in percent (OT:46, 68)."""
    if is_missing(x):
        return x if isinstance(x, Missing) else Missing("NA")
    return 100 * (x - 1)


def fmt(value, spec=FMT_RATIO):
    """One TSV cell: NA for Missing/None/NaN, yes/no for bool, str(int), format(float, spec)."""
    if value is None or isinstance(value, Missing):
        return "NA"
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return "NA"
        return format(value, spec)
    text = str(value)
    if "\t" in text or "\n" in text or "\r" in text:
        raise ValueError(f"a table cell holds a tab or newline: {text!r}")
    return text


# ---------------------------------------------------------------- key normalisation (SPEC 2.4, 2.5; T20)
def normalise_db(name):
    """A database name as timings.tsv writes it ('hye_td.fasta') -> its stem 'hye_td' (B:196, 915)."""
    return name[:-len(".fasta")] if name.endswith(".fasta") else name


def split_scaling_db(name):
    """A scaling folder name 'hye_td_t16' -> ('hye_td', 16) (B:196, 891); None if it does not match."""
    m = SCALING_DB.match(name)
    return (m.group(1), int(m.group(2))) if m else None


# ---------------------------------------------------------------- readers
def read_tsv(path, exact_header=None, required=None):
    """(header, [(line, {column: text})]); blank lines skipped. Stops (exit 2) on a missing file, another header or a
    row with another number of fields. quoting is off: the driver writes plain tab-joined lines."""
    if not os.path.exists(path):
        raise ValidationStop(f"{path}: file not found")
    rows = []
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f, delimiter="\t", quoting=csv.QUOTE_NONE)
        header = next(reader, None)
        if header is None:
            stop(path, 1, "header", "", "a header line")
        if exact_header is not None and header != list(exact_header):
            stop(path, 1, "header", "\t".join(header), "\t".join(exact_header))
        for col in required or ():
            if col not in header:
                stop(path, 1, col, "\t".join(header), "a header with the column " + col)
        for cells in reader:
            if not cells or cells == [""]:
                continue
            line = reader.line_num
            if len(cells) != len(header):
                stop(path, line, "(row)", f"{len(cells)} fields", f"{len(header)} fields as in the header")
            rows.append((line, dict(zip(header, cells))))
    return header, rows


def read_table(path):
    """A written tables/*.tsv for figures.py: (columns, [{column: text}]); lines starting with '#' are skipped."""
    with open(path, encoding="utf-8", newline="") as f:
        lines = [x for x in f.read().split("\n") if x and not x.startswith("#")]
    if not lines:
        return [], []
    cols = lines[0].split("\t")
    return cols, [dict(zip(cols, x.split("\t"))) for x in lines[1:]]


def _yaml_scalar(text):
    text = text.strip()
    if text.startswith('"') and text.endswith('"') and len(text) >= 2:
        escapes = {"\\": "\\", '"': '"', "n": "\n", "t": "\t", "/": "/"}  # the escapes of a double-quoted scalar
        return re.sub(r"\\(.)", lambda m: escapes.get(m.group(1), "\\" + m.group(1)), text[1:-1])
    if text.startswith("'") and text.endswith("'") and len(text) >= 2:
        return text[1:-1].replace("''", "'")
    if " #" in text:
        text = text.split(" #", 1)[0].rstrip()
    if text in ("true", "True"):
        return True
    if text in ("false", "False"):
        return False
    if text in ("null", "~", ""):
        return None
    if text == "[]":
        return []
    if text == "{}":
        return {}
    if text.startswith("[") and text.endswith("]"):
        return [_yaml_scalar(x) for x in text[1:-1].split(",") if x.strip()]
    if re.fullmatch(r"[-+]?\d+", text):
        return int(text)
    if re.fullmatch(r"[-+]?(\d+\.?\d*|\.\d+)([eE][-+]?\d+)?", text):
        return float(text)
    if text in (".nan", ".NaN", "nan"):
        return float("nan")
    if text in (".inf", "inf"):
        return float("inf")
    if text in ("-.inf", "-inf"):
        return float("-inf")
    return text


def _yaml_key(content):
    """(key, rest) of 'key: rest' or 'key:' (key possibly quoted), or None if the line is not a mapping entry."""
    if content[:1] in ('"', "'"):
        q = content[0]
        end = content.find(q, 1)
        if end > 0 and content[end + 1:end + 2] == ":" and content[end + 2:end + 3] in ("", " "):
            return content[1:end], content[end + 2:].strip()
        return None
    m = re.match(r"^([^:#]+?):(\s+(.*))?$", content)
    if not m:
        return None
    return m.group(1).strip(), (m.group(3) or "").strip()


def parse_yaml(text):
    """The YAML subset of ProSE's summary.yaml (SPEC 1 "No PyYAML"; SPEC O15b): block mappings ('key: value',
    'key:' with a nested block), block sequences ('- scalar', '- key: value' items continuing at the indentation of
    their first key), scalars (quoted strings, true/false, null, int, float, [] and simple flow lists)."""
    lines = []
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        lines.append([len(raw) - len(raw.lstrip(" ")), raw.strip()])

    def block(i, indent):
        if lines[i][1] == "-" or lines[i][1].startswith("- "):
            return sequence(i, indent)
        return mapping(i, indent)

    def value_after(i, indent, rest):
        """the value of an entry at line i whose text after the colon is rest"""
        if rest:
            return _yaml_scalar(rest), i + 1
        j = i + 1
        if j < len(lines) and (lines[j][0] > indent or (lines[j][0] == indent and lines[j][1].startswith("-"))):
            return block(j, lines[j][0])
        return None, j

    def mapping(i, indent):
        out = OrderedDict()
        while i < len(lines) and lines[i][0] == indent and not (lines[i][1] == "-" or lines[i][1].startswith("- ")):
            kv = _yaml_key(lines[i][1])
            if kv is None:
                raise ValueError(f"summary.yaml: not a mapping line: {lines[i][1]!r}")
            out[kv[0]], i = value_after(i, indent, kv[1])
        return dict(out), i

    def sequence(i, indent):
        out = []
        while i < len(lines) and lines[i][0] == indent and (lines[i][1] == "-" or lines[i][1].startswith("- ")):
            rest = lines[i][1][1:].strip()
            if not rest:
                v, i = (block(i + 1, lines[i + 1][0]) if i + 1 < len(lines) and lines[i + 1][0] > indent
                        else (None, i + 1))
                out.append(v)
                continue
            kv = _yaml_key(rest)
            if kv is None:
                out.append(_yaml_scalar(rest))
                i += 1
                continue
            item_indent = indent + (len(lines[i][1]) - len(rest))
            lines[i] = [item_indent, rest]  # the item is a mapping whose first key sits at item_indent
            v, i = mapping(i, item_indent)
            out.append(v)
        return out, i

    if not lines:
        return {}
    value, _ = block(0, lines[0][0])
    return value


def read_yaml(path):
    with open(path, encoding="utf-8") as f:
        return parse_yaml(f.read())


def read_versions(path):
    """W/versions.txt: one line per tool, '<command>\\t<version lines joined by ' | '>' (B:357). None if absent."""
    if not path or not os.path.exists(path):
        return None
    out = []
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f.read().splitlines():
            if line.strip():
                cmd, _, text = line.partition("\t")
                out.append((cmd, text))
    return out


MACHINE_ITEM = re.compile(r"^([^:#]*[^:#\s])\s*:(?:\s+(.*))?$")  # 'key: value'; the key holds no '#' and no ':'


def read_machine(path):
    """node_prep/machine.txt (PN:30): [(section, key, value)]; section from '## ' headers; a 'key: value' line is
    split at the first ':' that is followed by whitespace or the line end, with a key free of '#' (so 'MemTotal:  N kB',
    'CPU(s):  16' and 'memory cap: --mem-gb 200' split, while the kernel line 'Linux 5.4.0 #236-Ubuntu SMP ...
    19:53:21 UTC' and time stamps do not); other lines as (section, '', line); a '# ' line as (section, 'header',
    text). timing.py (O18) reads the file with its own section rules (timing.machine_rows)."""
    out, section = [], ""
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f.read().splitlines():
            if not line.strip():
                continue
            if line.startswith("## "):
                section = line[3:].strip()
                continue
            if line.startswith("# "):
                out.append((section, "header", line[2:].strip()))
                continue
            m = MACHINE_ITEM.match(line)
            out.append((section, m.group(1).strip(), (m.group(2) or "").strip()) if m else (section, "", line.strip()))
    return out


MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
LS_LINE = re.compile(r"^[-dlcbps][-rwxsStT@+.]{9}\S*\s+\d+\s+\S+\s+\S+\s+(\d+)\s+(\w{3})\s+(\d{1,2})\s+"
                     r"(\d{1,2}:\d{2}|\d{4})\s+(.+)$")


def read_listing(path):
    """An 'ls -l' listing of W (e.g. work.ls; SPEC C18): {name: {size, month, day, time, year, text, key}}. key sorts
    by (year or 0, month, day, hh, mm); 'ls -l' shows a time instead of the year for files of the last 6 months."""
    out = {}
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f.read().splitlines():
            m = LS_LINE.match(line.strip())
            if not m or m.group(2) not in MONTHS:
                continue
            size, mon, day, tm, name = m.groups()
            year, hh, mm = (int(tm), 0, 0) if ":" not in tm else (None, *map(int, tm.split(":")))
            out[name] = {"size": int(size), "month": mon, "day": int(day), "time": tm if ":" in tm else "",
                         "year": year, "text": f"{mon} {day} {tm}",
                         "key": (year or 0, MONTHS.index(mon) + 1, int(day), hh, mm)}
    return out


# ---------------------------------------------------------------- data classes
@dataclass(frozen=True)
class Run:
    """One row of runs.tsv (columns read by name, B:144)."""
    id: str
    set: str
    group: str
    format: str
    params: str
    db: str
    entrap: tuple
    ref: tuple
    ions: str
    sample: str
    scaling: str
    role: str
    line: int


@dataclass(frozen=True)
class Unit:
    """What bench.py searches and counts (SPEC 2.1; B:950-961): one per sample name (sample != '-'), with its
    replicates in table order, else one per run id. pooled = len(runs) > 1 (B:971, 1289)."""
    name: str
    runs: tuple
    pooled: bool
    group: str
    role: str
    set: str
    kind: str
    cls: str
    grade: str
    td: str
    entrap: tuple
    ref: tuple
    ions: str
    scaling_runs: tuple
    expected: tuple
    count_file: str
    sample: str
    params: str
    db: str
    side: object
    instrument: str
    display: str

    @property
    def n_files(self):
        return len(self.runs)

    @property
    def is_decision(self):
        return self.role == "decision"

    @property
    def stems(self):
        return (self.td,) + tuple(s for s, _, _ in self.entrap) + tuple(self.ref)

    def design_of(self, stem):
        """(design, realisation) of one of the unit's databases, None for another stem (SPEC 2.1)."""
        if stem == self.td:
            return ("td", None)
        for s, d, r in self.entrap:
            if s == stem:
                return (d, r)
        if stem in self.ref:
            return ("arath", None)
        return None

    def stems_of(self, design_name):
        if design_name == "td":
            return [self.td]
        if design_name == "arath":
            return list(self.ref)
        return [s for s, d, _ in self.entrap if d == design_name]


@dataclass(frozen=True)
class Group:
    name: str
    kind: str
    cls: str
    grade: str
    side: object
    instrument: str
    display: str
    units: tuple
    runs: tuple
    n_runs: int
    n_decision: int


@dataclass(frozen=True)
class BatchGroup:
    """A batch group (SPEC 2.1; B:974-977): the rows with sample == '-' of one group, kept with >= 2 files;
    n_files counts every one of them, decision runs included (OPEN Q24)."""
    name: str
    runs: tuple
    n_files: int
    td: str
    kind: str
    cls: str
    grade: str
    side: object
    ions: str
    expected: tuple
    n_decision: int


@dataclass(frozen=True)
class CountRow:
    line: int
    engine: str
    benchmark: str
    tag: object
    run: str
    database: str
    file: str
    level: str
    q_value: float
    accepted: int
    entrapment: int
    lower_bound_fdp: float
    combined_fdp: float
    paired_fdp: object
    entrapment_target_not_accepted: object
    entrapment_above_target: object
    te_ratio: float
    design: str
    realisation: object
    unit: object


@dataclass(frozen=True)
class CoverageRow:
    line: int
    engine: str
    benchmark: str
    tag: object
    run: str
    database: str
    db: str
    threads: object
    status: str
    state: str
    counted: bool
    design: str
    realisation: object
    scope: str
    unit: object
    group: object


@dataclass(frozen=True)
class TimingRow:
    line: int
    engine: str
    benchmark: str
    tag: object
    run: str
    database: str
    db: str
    stage: str
    threads: int
    repetition: int
    wall: object
    cpu: object
    rss_kb: object
    exit: object


@dataclass
class Rep:
    """One repetition of an attempt: wall_r = fsum(wall), cpu_r = fsum(cpu), rss_r = max(rss) over its rows
    (SPEC 2.5 "Per repetition r")."""
    repetition: int
    rows: list
    stages: dict
    wall: object
    cpu: object
    rss_kb: object
    stage_wall: dict
    complete: bool
    problem: str


@dataclass
class Attempt:
    index: int
    threads: int
    rows: list
    reps: dict
    state: str
    note: str
    limit: object = None
    lower_bound: object = None


@dataclass
class Timing:
    key: tuple
    engine: str
    benchmark: str
    run: str
    db: str
    threads: object
    state: str
    note: str
    attempts: list
    attempt: object
    reps: dict
    wall_med: object
    cpu_med: object
    rss_med_kb: object
    stage_wall_med: dict
    limit: object
    lower_bound: object
    expected: dict
    unit: object
    group: object
    n_files: int

    @property
    def n_attempts(self):
        return len(self.attempts)

    @property
    def wall_r(self):
        return {r: self.reps[r].wall for r in (1, 2, 3) if r in self.reps}

    @property
    def cpu_r(self):
        return {r: self.reps[r].cpu for r in (1, 2, 3) if r in self.reps}

    @property
    def rss_r_kb(self):
        return {r: self.reps[r].rss_kb for r in (1, 2, 3) if r in self.reps}


@dataclass
class Number:
    key: str
    value: object
    text: str
    unit: str
    output: str
    protocol_ref: str
    source_side: str
    main_text_allowed: str


class Report:
    """The check report (SPEC 5): lines 'PASS|WARN|FAIL|INFO <id> <message>'. A WARN marked strict (the (s) of
    SPEC 5) becomes FAIL under --strict."""
    LEVELS = ("PASS", "WARN", "FAIL", "INFO")

    def __init__(self, strict=False):
        self.strict = strict
        self.lines = []

    def check(self, level, cid, message, strict=False):
        if level not in self.LEVELS:
            raise ValueError(f"check level {level!r}; allowed {self.LEVELS}")
        if strict and self.strict and level == "WARN":
            level = "FAIL"
        cid = "_".join(str(cid).split()) or "-"
        self.lines.append((level, cid, " ".join(str(message).split())))

    @property
    def n_fail(self):
        return sum(1 for x in self.lines if x[0] == "FAIL")

    def count(self, level):
        return sum(1 for x in self.lines if x[0] == level)

    def text(self):
        return "".join(f"{lv} {cid} {msg}\n" for lv, cid, msg in self.lines)


# ---------------------------------------------------------------- options
@dataclass
class Options:
    """The inputs of one build (summarize.py fills it from its command line; tests give fixture paths)."""
    runs: str = DEFAULT_RUNS
    work: object = None
    counts: object = None
    coverage: object = None
    timings: object = None
    versions: object = None
    scaling_work: object = None
    scaling_coverage: object = None
    scaling_timings: object = None
    scaling_versions: object = None
    runs_11b: object = None
    rule11b_work: object = None
    out: object = None
    design: str = "paper"
    params_dir: str = DEFAULT_PARAMS
    levels: tuple = LEVELS
    only: object = None
    logs: str = "auto"
    strict: bool = False
    expect_threads: object = None
    references: object = DEFAULT_REFERENCES
    mzml_counts: object = DEFAULT_MZML_COUNTS
    listing: object = None
    machines: tuple = ()
    gc_logs: object = None
    command_line: str = ""

    def resolve(self):
        """Fills the paths left None from work and scaling_work (default: work), SPEC 1 CLI."""
        w = self.work
        for name, fname in (("counts", "counts.tsv"), ("coverage", "coverage.tsv"), ("timings", "timings.tsv"),
                            ("versions", "versions.txt")):
            if getattr(self, name) is None and w:
                setattr(self, name, os.path.join(w, fname))
        s = self.scaling_work
        if s:
            for name, fname in (("scaling_coverage", "coverage.tsv"), ("scaling_timings", "timings.tsv"),
                                ("scaling_versions", "versions.txt")):
                if getattr(self, name) is None:
                    setattr(self, name, os.path.join(s, fname))
        return self


def _same_file(a, b):
    return bool(a) and bool(b) and os.path.realpath(a) == os.path.realpath(b)


# ---------------------------------------------------------------- value parsers (stop on violation)
def _int(path, line, col, text, minimum=None):
    try:
        v = int(text)
    except ValueError:
        stop(path, line, col, text, "an integer")
    if minimum is not None and v < minimum:
        stop(path, line, col, text, f"an integer >= {minimum}")
    return v


def _float(path, line, col, text, na_ok=False):
    if text in ("NA", "nan", "NaN"):
        if na_ok:
            return None
        stop(path, line, col, text, "a number (NA is allowed only in paired_fdp, entrapment_target_not_accepted, "
                                    "entrapment_above_target)" if col in COUNTS_HEADER else "a number")
    try:
        v = float(text)
    except ValueError:
        stop(path, line, col, text, "a number" + (" or NA" if na_ok else ""))
    if math.isnan(v):
        if na_ok:
            return None
        stop(path, line, col, text, "a number")
    return v


def _int_or_na(path, line, col, text):
    if text == "NA":
        return None
    return _int(path, line, col, text, minimum=0)


# ---------------------------------------------------------------- the context
class Ctx:
    """The loaded inputs and the output channels of one build; see the module docstring for the API."""

    gmean = staticmethod(gmean)
    median = staticmethod(median)
    fmean = staticmethod(fmean)
    mean_sd = staticmethod(mean_sd)
    gib = staticmethod(gib)
    sum_ratio = staticmethod(sum_ratio)
    ratio = staticmethod(ratio)
    lead = staticmethod(lead)
    Missing = Missing
    is_missing = staticmethod(is_missing)

    def __init__(self, options):
        o = options
        self.options = o
        self.strict = bool(o.strict)
        self.design_mode = o.design
        self.levels = tuple(o.levels)
        self.only = None if o.only is None else tuple(o.only)
        self.expect_threads = o.expect_threads if o.expect_threads is not None else (16 if o.strict else None)
        self.work = o.work
        self.out = o.out
        self.tables_dir = os.path.join(o.out, "tables") if o.out else None
        self.figures_dir = os.path.join(o.out, "figures") if o.out else None
        self.out_dir = os.path.join(o.work, "out") if o.work else None
        self.scaling_out_dir = os.path.join(o.scaling_work, "out") if o.scaling_work else self.out_dir
        # the logs of W (per_file, arms, batch) and of S (scaling) are available separately: a scaling folder S may
        # come without its out/ tree (only timings.tsv, coverage.tsv and versions.txt are needed from it)
        if o.logs in ("yes", "auto"):  # --logs yes only adds a WARN when they are missing (_loader_info)
            self.logs_available = bool(self.out_dir) and os.path.isdir(self.out_dir)
            self.scaling_logs_available = bool(self.scaling_out_dir) and os.path.isdir(self.scaling_out_dir)
        else:
            self.logs_available = self.scaling_logs_available = False
        self.report = Report(strict=self.strict)
        self.inputs = OrderedDict()
        self.results = OrderedDict()
        self.result_columns = OrderedDict()
        self.numbers = []
        self._number_keys = set()
        self.shared = {}
        self.runs, self.run_by_id = [], {}
        self.units, self.unit_by_name, self.unit_of_run = [], {}, {}
        self.groups, self.batch_groups = OrderedDict(), OrderedDict()
        self.scaling_runs = ()
        self.pooled_arrangement, self.pooled_arrangement_files, self.other_arrangement_tag = None, [], None
        self.rule11b_pairs, self.rule11b_work = set(), o.rule11b_work
        self.counts, self.counts_outside, self.counts_rule11b, self.count_index = [], [], [], {}
        self.coverage, self.coverage_outside, self.coverage_index = [], [], {}
        self.timing_rows, self.timing_outside, self.timings, self.earlier_attempts = [], [], OrderedDict(), []
        self.unflagged_scaling = []
        self._tags = set()
        self.versions = self.scaling_versions = None
        self.mzml_counts = None
        self.listing = None
        self.references_path = o.references
        self.machines = list(o.machines or ())
        self.gc_logs = o.gc_logs

    # ------------------------------------------------------------ small API
    def want(self, keyword):
        """--only selection (SPEC 1): True if no --only was given or keyword is in it."""
        if keyword not in ONLY_KEYWORDS:
            raise ValueError(f"want({keyword!r}): not an --only keyword {ONLY_KEYWORDS}")
        return self.only is None or keyword in self.only

    def check(self, level, cid, message, strict=False):
        self.report.check(level, cid, message, strict)

    def record_input(self, path, item):
        if path and os.path.exists(path) and path not in self.inputs:
            self.inputs[path] = item

    @property
    def tags(self):
        return sorted(self._tags)

    @property
    def unknown_tags(self):
        return sorted(t for t in self._tags if f"per_file_{t}" not in design.ARMS)

    def unit(self, u):
        return u if isinstance(u, Unit) else self.unit_by_name[u]

    def select_units(self, kinds=None, groups=None, decision=True):
        out = []
        for u in self.units:
            if kinds is not None and u.kind not in kinds:
                continue
            if groups is not None and u.group not in groups:
                continue
            if not decision and u.is_decision:
                continue
            out.append(u)
        return out

    def E(self, u):
        return self.unit(u).expected

    def search_dir(self, engine, benchmark, run, db, threads=None):
        """W/out/<engine>/<benchmark>/<run>/<db>[_t<n>] (B:195-196); S/out for scaling."""
        base = self.scaling_out_dir if benchmark == "scaling" else self.out_dir
        if base is None:
            return None
        return os.path.join(base, engine, benchmark, run, db + (f"_t{threads}" if threads else ""))

    def logs_for(self, benchmark):
        """Whether the search folders of a benchmark can be read: S/out for scaling (scaling_logs_available), W/out
        for every other benchmark (logs_available)."""
        return self.scaling_logs_available if benchmark == "scaling" else self.logs_available

    # ------------------------------------------------------------ lookups (SPEC 2.6)
    def coverage_row(self, engine, benchmark, run, database):
        return self.coverage_index.get((engine, benchmark, run, database))

    def search_reason(self, engine, benchmark, run, db):
        """None if the per_file* search is ok and counted; else its SPEC 2.6 reason."""
        c = self.coverage_index.get((engine, benchmark, run, db))
        if c is None:
            return "no_coverage"
        if c.state != "ok":
            return c.state
        if not c.counted:
            return "not_counted"
        return None

    def count_row(self, engine, unit, level, db=None, benchmark="per_file"):
        u = self.unit(unit)
        return self.count_index.get((engine, benchmark, u.name, db or u.td, level))

    def accepted(self, engine, unit, level, db=None, benchmark="per_file"):
        """The accepted count of a search (td by default), or Missing(reason) (SPEC 2.6). Zero is returned as 0."""
        u = self.unit(unit)
        db = db or u.td
        why = self.search_reason(engine, benchmark, u.name, db)
        if why:
            return Missing(why)
        row = self.count_index.get((engine, benchmark, u.name, db, level))
        if row is None:
            return Missing("missing_count")
        return row.accepted

    def fdp(self, engine, unit, db, level, benchmark="per_file"):
        """combined_fdp of an entrapment search (EE-lib:30-34), Missing('none_accepted') when N = 0 (EE prints 0,
        EE-lib:32; SPEC 2.6), or Missing(reason)."""
        u = self.unit(unit)
        n = self.accepted(engine, u, level, db=db, benchmark=benchmark)
        if isinstance(n, Missing):
            return n
        if n == 0:
            return Missing("none_accepted")
        return self.count_index[(engine, benchmark, u.name, db, level)].combined_fdp

    # ------------------------------------------------------------ comparison sets (SPEC 2.7)
    def reason(self, unit, engines, level, db=None, benchmark="per_file", positive=True):
        u = self.unit(unit)
        if u.is_decision:
            return "decision"
        for e in engines:
            v = self.accepted(e, u, level, db=db, benchmark=benchmark)
            if isinstance(v, Missing):
                return f"{e}:{v.reason}"
            if positive and v == 0:
                return f"{e}:zero"
        return None

    def _units_arg(self, units):
        return self.units if units is None else [self.unit(u) for u in units]

    def R(self, pair, level, units=None, benchmark="per_file"):
        """Units with role != decision, both engines counted on td, both accepted > 0 (DS:621-623, 986; OT:113-116)."""
        return [u for u in self._units_arg(units) if self.reason(u, pair, level, benchmark=benchmark) is None]

    def R3(self, level, units=None, benchmark="per_file"):
        """R with all three engines (DS:623)."""
        return self.R(ENGINES, level, units, benchmark)

    def C(self, group, level, engines=None):
        """Non-decision units of group g whose td search every engine of E(u) (or of engines) counted, zero allowed
        (count sums of O1; OPEN Q1)."""
        return [u for u in self.units if u.group == group
                and self.reason(u, engines or u.expected, level, positive=False) is None]

    def F(self, level, design_name, engines=None, units=None, benchmark="per_file"):
        """For FDP: per non-decision unit, the stems of the design that every engine of E(u) (or of engines) counted
        with accepted > 0; a unit is in F with at least one (SPEC 2.7; OPEN Q13, Q15)."""
        out = OrderedDict()
        for u in self._units_arg(units):
            if u.is_decision:
                continue
            shared = []
            for s in u.stems_of(design_name):
                vals = [self.accepted(e, u, level, db=s, benchmark=benchmark) for e in (engines or u.expected)]
                if all(isinstance(v, int) and not isinstance(v, bool) and v > 0 for v in vals):
                    shared.append(s)
            if shared:
                out[u.name] = shared
        return out

    def timing(self, engine, benchmark, run, db=None, threads=None):
        if db is None:
            db = self._td_of(benchmark, run)
        return self.timings.get((engine, benchmark, run, db, threads if benchmark == "scaling" else None))

    def _td_of(self, benchmark, run):
        if benchmark == "batch":
            g = self.batch_groups.get(run)
            return g.td if g else None
        if benchmark == "scaling":
            r = self.run_by_id.get(run)
            return r.db + "_td" if r else None
        u = self.unit_by_name.get(run)
        return u.td if u else None

    def timing_value(self, engine, benchmark, run, db=None, threads=None):
        """The Timing if its search is ok in coverage and its last attempt is complete; else Missing(reason)."""
        if db is None:
            db = self._td_of(benchmark, run)
        t = self.timing(engine, benchmark, run, db, threads)
        if t is not None and t.state == "not_run_over_limit":
            return Missing("not_run_over_limit")
        database = f"{db}_t{threads}" if benchmark == "scaling" else db
        c = self.coverage_index.get((engine, benchmark, run, database))
        if c is None:
            return Missing("no_coverage")
        if c.state != "ok":
            return Missing(c.state)
        if t is None:
            return Missing("no_timing_rows")
        if t.state != "complete":
            return Missing(t.state)
        return t

    def T(self, pair, units=None, benchmark="per_file"):
        """Non-decision units whose per_file td timing is complete for both engines (SPEC 2.7; C16)."""
        out = []
        for u in self._units_arg(units):
            if u.is_decision:
                continue
            if all(isinstance(self.timing_value(e, benchmark, u.name), Timing) for e in pair):
                out.append(u)
        return out

    def T3(self, units=None, benchmark="per_file"):
        return self.T(ENGINES, units, benchmark)

    def B3(self):
        """Batch groups whose batch ratio (O16: batch wall / sum of the per-file medians of its files) exists for
        every engine of E: the batch timing and the per_file td timing of every file complete (SPEC 2.7)."""
        out = []
        for g in self.batch_groups.values():
            ok = True
            for e in g.expected:
                if not isinstance(self.timing_value(e, "batch", g.name), Timing):
                    ok = False
                for r in g.runs:
                    if not isinstance(self.timing_value(e, "per_file", r), Timing):
                        ok = False
            if ok:
                out.append(g.name)
        return out

    # ------------------------------------------------------------ outputs
    def write_table(self, name, columns, rows, formats=None, header_note=None, auto_note=False):
        """One tables/<name>.tsv (SPEC 3), atomically; the typed rows go to self.results[name]."""
        if not TABLE_NAME.match(name):
            raise ValueError(f"table name {name!r}: expected the SPEC file stem, e.g. 'O02_pairs_runs'")
        if name in self.results:
            raise ValueError(f"table {name} written twice")
        columns = list(columns)
        if len(set(columns)) != len(columns):
            raise ValueError(f"{name}: duplicate column names")
        formats = formats or {}
        typed, lines = [], ["\t".join(columns)]
        for row in rows:
            if isinstance(row, dict):
                extra = set(row) - set(columns)
                lacking = [c for c in columns if c not in row]
                if extra or lacking:
                    raise ValueError(f"{name}: row keys differ from the columns (extra {sorted(extra)}, "
                                     f"lacking {lacking})")
                d = OrderedDict((c, row[c]) for c in columns)
            else:
                row = list(row)
                if len(row) != len(columns):
                    raise ValueError(f"{name}: a row has {len(row)} values for {len(columns)} columns")
                d = OrderedDict(zip(columns, row))
            if auto_note and "note" in d and not d["note"]:
                reasons = OrderedDict()
                for c, v in d.items():
                    if isinstance(v, Missing):
                        reasons.setdefault(v.reason, []).append(c)
                d["note"] = "; ".join(f"{r} ({', '.join(cs)})" for r, cs in reasons.items())
            typed.append(dict(d))
            lines.append("\t".join(fmt(v, formats.get(c, FMT_RATIO)) for c, v in d.items()))
        self.results[name] = typed
        self.result_columns[name] = columns
        if not self.tables_dir:
            return None
        text = ("# " + " ".join(header_note.split()) + "\n" if header_note else "") + "\n".join(lines) + "\n"
        return write_atomic(os.path.join(self.tables_dir, name + ".tsv"), text)

    def write_file(self, relpath, text):
        if not self.out:
            return None
        if os.path.isabs(relpath) or ".." in relpath.replace("\\", "/").split("/"):
            raise ValueError(f"write_file: {relpath!r} must be a path inside the output folder")
        self.shared.setdefault("written", set()).add(os.path.normpath(relpath))
        return write_atomic(os.path.join(self.out, relpath), text)

    def number(self, key, value, text=None, unit="", output="", protocol_ref="", source_side="none",
               main_text_allowed=None):
        """One row of numbers.tsv (SPEC 3.8)."""
        if not isinstance(key, str) or not KEY_PATTERN.match(key):
            raise ValueError(f"number key {key!r} does not match {KEY_PATTERN.pattern}")
        if key in self._number_keys:
            raise ValueError(f"number key {key} given twice")
        if source_side not in SOURCE_SIDES:
            raise ValueError(f"{key}: source_side {source_side!r} not in {SOURCE_SIDES}")
        if isinstance(main_text_allowed, bool):
            main_text_allowed = "yes" if main_text_allowed else "no"
        if main_text_allowed is None:
            idr = key.startswith(ID_RATIO_FAMILIES)
            main_text_allowed = "no" if idr and source_side != "heldout" else "yes"
        if main_text_allowed not in ("yes", "no"):
            raise ValueError(f"{key}: main_text_allowed {main_text_allowed!r}")
        if isinstance(value, float) and math.isnan(value):
            value = Missing("NA")
        if text is None:
            text = "NA" if is_missing(value) else (("yes" if value else "no") if isinstance(value, bool)
                                                   else str(value))
        for s in (str(text), str(unit), str(output), str(protocol_ref)):
            if "\t" in s or "\n" in s:
                raise ValueError(f"{key}: a field holds a tab or newline")
        self._number_keys.add(key)
        self.numbers.append(Number(key, value, str(text), str(unit), str(output), str(protocol_ref), source_side,
                                   main_text_allowed))

    # ------------------------------------------------------------ loading
    def _load_runs(self):
        """runs.tsv -> runs, units, groups, batch groups, scaling runs (SPEC 2.1)."""
        path = self.options.runs
        paper = self.design_mode == "paper"
        required = RUNS_COLUMNS if paper else tuple(c for c in RUNS_COLUMNS if c != "role")
        header, rows = read_tsv(path, required=required)
        self.record_input(path, "runs")
        seen = set()
        for line, r in rows:
            rid = r["id"]
            if rid in seen:
                stop(path, line, "id", rid, "a run id not used before (B:146)")
            seen.add(rid)
            if r["ions"] not in ("by", "bycz"):
                stop(path, line, "ions", r["ions"], "by, bycz (B:149)")
            role = r["role"] if "role" in header else "heldout"
            if paper:
                if role not in ROLES:
                    stop(path, line, "role", role, ", ".join(ROLES))
                if r["set"] not in SETS:
                    stop(path, line, "set", r["set"], ", ".join(SETS))
                if r["set"] == "tuned" and role != "tuned":
                    stop(path, line, "role", role, "tuned (set == tuned)")
                if r["group"] not in design.ALL_GROUPS:
                    stop(path, line, "group", r["group"], "a group of design.py (SPEC 2.2)")
            files = {}
            for col in ("entrap", "ref"):
                names = tuple(x.strip() for x in r[col].split(";") if x.strip() and x.strip() != "-")
                for x in names:
                    if not x.endswith(".fasta"):
                        stop(path, line, col, x, "file names ending in .fasta (B:180-183)")
                files[col] = names
            run = Run(rid, r["set"], r["group"], r["format"], r["params"], r["db"], files["entrap"], files["ref"],
                      r["ions"], r["sample"], r["scaling"], role, line)
            self.runs.append(run)
            self.run_by_id[rid] = run
        self.scaling_runs = tuple(r.id for r in self.runs if r.scaling == "1")
        # units: samples (with their replicates in table order) and single runs, in order of first appearance
        order, by_sample = [], OrderedDict()
        for r in self.runs:
            if r.sample != "-":
                if r.sample not in by_sample:
                    by_sample[r.sample] = []
                    order.append(r.sample)
                by_sample[r.sample].append(r)
            else:
                order.append(r)
        for item in order:
            rs = by_sample[item] if isinstance(item, str) else [item]
            first = rs[0]
            for r in rs[1:]:  # bench.py uses the first row (B:961) and does not assert this; the loader stops
                for col in ("group", "role", "set", "params", "db", "entrap", "ref", "ions"):
                    if getattr(r, col) != getattr(first, col):
                        stop(path, r.line, col, getattr(r, col),
                             f"{getattr(first, col)!r} as in the first replicate of sample {first.sample}")
            name = first.sample if first.sample != "-" else first.id
            if name in self.unit_by_name:
                stop(path, first.line, "sample" if first.sample != "-" else "id", name, "a unit name used once")
            entrap = tuple(self._entrap_design(path, first.line, normalise_db(x)) for x in first.entrap)
            ref = []
            for x in first.ref:
                stem = normalise_db(x)
                if not ARATH.match(stem):
                    stop(path, first.line, "ref", x, "<db>_arath_td.fasta (SPEC 2.1)")
                ref.append(stem)
            pooled = len(rs) > 1
            g = first.group
            unit = Unit(
                name=name, runs=tuple(r.id for r in rs), pooled=pooled, group=g, role=first.role, set=first.set,
                kind=design.kind(g), cls=design.cls(g), grade=design.grade(g), td=first.db + "_td", entrap=entrap,
                ref=tuple(ref), ions=first.ions, scaling_runs=tuple(r.id for r in rs if r.scaling == "1"),
                expected=tuple(e for e in ENGINES if e != "sage" or first.ions == "by"),
                count_file=(first.id if not pooled else "pooled") + ".count.idXML",  # B:1292
                sample=first.sample, params=first.params, db=first.db, side=design.side(g),
                instrument=design.instrument(g), display=design.display(g))
            self.units.append(unit)
            self.unit_by_name[name] = unit
            for r in rs:
                self.unit_of_run[r.id] = unit
        for u in self.units:
            if u.group not in self.groups:
                self.groups[u.group] = []
            self.groups[u.group].append(u)
        self.groups = OrderedDict(
            (g, Group(name=g, kind=design.kind(g), cls=design.cls(g), grade=design.grade(g), side=design.side(g),
                      instrument=design.instrument(g), display=design.display(g), units=tuple(u.name for u in us),
                      runs=tuple(r for u in us for r in u.runs), n_runs=sum(u.n_files for u in us),
                      n_decision=sum(u.n_files for u in us if u.is_decision)))
            for g, us in self.groups.items())
        # batch groups: rows with sample == '-', grouped by group, at least 2 files (B:974-977)
        singles = OrderedDict()
        for r in self.runs:
            if r.sample == "-":
                singles.setdefault(r.group, []).append(r)
        for g, rs in singles.items():
            if len(rs) < 2:
                continue
            self.batch_groups[g] = BatchGroup(
                name=g, runs=tuple(r.id for r in rs), n_files=len(rs), td=rs[0].db + "_td", kind=design.kind(g),
                cls=design.cls(g), grade=design.grade(g), side=design.side(g), ions=rs[0].ions,
                expected=tuple(e for e in ENGINES if e != "sage" or rs[0].ions == "by"),
                n_decision=sum(1 for r in rs if r.role == "decision"))

    def _entrap_design(self, path, line, stem):
        """(stem, design, realisation) of an entrap entry (SPEC 2.1): shuffled s1-s3, natural, or (only with
        --design none) the smoke database as shuffled without realisation. 'hye_s1_natural_td' is natural."""
        m = SHUFFLED.match(stem)
        if m is not None:
            return (stem, "shuffled", int(m.group(2)))
        if NATURAL.match(stem):
            return (stem, "natural", None)
        if self.design_mode == "none" and stem.endswith("_td"):
            return (stem, "shuffled", None)
        stop(path, line, "entrap", stem + ".fasta", "<db>_entrap_s{1,2,3}_td.fasta or <name>_natural_td.fasta")

    def _load_rule11b(self):
        """--runs-11b (DS:1056): its (sample, database) pairs are accepted as design rule11b. The file is a run
        table like runs.tsv (the six DN13 class I rows with the class I entrapment databases); its database names
        are not pattern-checked."""
        path = self.options.runs_11b
        if not path:
            return
        _, rows = read_tsv(path, required=("id", "db", "entrap", "ref", "sample"))
        self.record_input(path, "runs_11b")
        for _, r in rows:
            name = r["sample"] if r["sample"] != "-" else r["id"]
            stems = [r["db"] + "_td"] + [normalise_db(x.strip()) for c in ("entrap", "ref")
                                         for x in r[c].split(";") if x.strip() and x.strip() != "-"]
            for s in stems:
                u = self.unit_by_name.get(name)
                if u is None or u.design_of(s) is None:
                    self.rule11b_pairs.add((name, s))

    def _load_pooled_arrangement(self):
        """POOLED_ARRANGEMENT from the parameter files of the immuno groups of the run table (SPEC 2.2)."""
        names = []
        for r in self.runs:
            if r.group in design.IMMUNO and r.params not in names:
                names.append(r.params)
        if not names:
            return
        paths = [os.path.join(self.options.params_dir, n + ".ini") for n in names]
        mode, found = design.read_pooled_arrangement(paths)
        self.pooled_arrangement, self.pooled_arrangement_files = mode, found
        self.other_arrangement_tag = design.other_arrangement_tag(mode)
        for p in paths:
            self.record_input(p, "params (POOLED_ARRANGEMENT)")

    def _benchmark(self, path, line, engine, benchmark, extra=()):
        """(tag) of a benchmark name; stops on an unknown name and on a known arm with an engine outside its set."""
        if benchmark in extra:
            return None
        arm = design.arm_of(benchmark)
        if arm is None or (arm.tag is not None and not TAG_PATTERN.match(arm.tag)):
            stop(path, line, "benchmark", benchmark, "per_file or per_file_<tag>" + (
                ", " + ", ".join(extra) if extra else ""))
        if engine not in arm.engines:
            stop(path, line, "engine", engine, f"{', '.join(arm.engines)} (the engines of the arm {benchmark}, "
                                               "SPEC 2.2 ARMS)")
        if arm.tag:
            self._tags.add(arm.tag)
        return arm.tag

    def _classify(self, run, stem):
        """(design, realisation, unit) of a per_file* search: the unit's design, rule11b, or outside_design."""
        u = self.unit_by_name.get(run)
        if u is not None:
            d = u.design_of(stem)
            if d:
                return d[0], d[1], u
        if (run, stem) in self.rule11b_pairs:
            return "rule11b", None, u
        return "outside_design", None, u

    def _coverage_rows(self, path, keep):
        _, rows = read_tsv(path, exact_header=COVERAGE_HEADER)
        return [(path, line, r) for line, r in rows if keep(r)]

    def _load_coverage(self):
        """coverage.tsv (SPEC 2.4); scaling rows from S when --scaling-work names another folder (OPEN Q35)."""
        o = self.options
        if not o.coverage:
            raise ValidationStop("no coverage.tsv given (--work W)")
        separate = bool(o.scaling_coverage) and not _same_file(o.coverage, o.scaling_coverage)
        rows = self._coverage_rows(o.coverage, lambda r: True)
        self.record_input(o.coverage, "coverage")
        if separate:
            for p, line, r in rows:
                if r["benchmark"] == "scaling":
                    stop(p, line, "benchmark", "scaling", "no scaling rows in W when --scaling-work names another "
                                                          "folder (OPEN Q35)")
            rows += self._coverage_rows(o.scaling_coverage, lambda r: r["benchmark"] == "scaling")
            self.record_input(o.scaling_coverage, "scaling coverage")
        for path, line, r in rows:
            engine, bench, run, database = r["engine"], r["benchmark"], r["run"], r["database"]
            if engine not in ENGINES:
                stop(path, line, "engine", engine, ", ".join(ENGINES))
            words = r["status"].split()
            state = words[0] if words else ""
            if state not in STATES:
                stop(path, line, "status", r["status"], "a status starting with " + ", ".join(STATES))
            if r["counted"] not in ("yes", "no"):
                stop(path, line, "counted", r["counted"], "yes, no")
            counted = r["counted"] == "yes"
            tag = self._benchmark(path, line, engine, bench, extra=("batch", "scaling"))
            key = (engine, bench, run, database)
            if key in self.coverage_index or any(key == (c.engine, c.benchmark, c.run, c.database)
                                                 for c in self.coverage_outside):
                stop(path, line, "database", database, "one row per (engine, benchmark, run, database)")
            threads, scope, unit, group, realisation = None, "unit", None, None, None
            if bench == "scaling":
                sp = split_scaling_db(database)
                if sp is None:
                    stop(path, line, "database", database, "<db>_td_t<threads> (B:196, 891)")
                db, threads = sp
                scope = "scaling"
                run_row = self.run_by_id.get(run)
                unit = self.unit_of_run.get(run)
                if run_row is None:
                    des = "outside_design"
                else:
                    des = "td" if db == run_row.db + "_td" else "outside_design"
            elif bench == "batch":
                db = database
                scope = "batch"
                group = self.batch_groups.get(run)
                if group is None:
                    stop(path, line, "run", run, "a batch group of the run table (B:974-977)")
                des = "td" if db == group.td else "outside_design"
            else:
                db = database
                des, realisation, unit = self._classify(run, db)
            row = CoverageRow(line, engine, bench, tag, run, database, db, threads, r["status"], state, counted, des,
                              realisation, scope, unit, group)
            if des == "outside_design":
                self.coverage_outside.append(row)
                continue
            self.coverage.append(row)
            self.coverage_index[key] = row
            if bench == "scaling" and run not in self.scaling_runs:
                self.unflagged_scaling.append(row)  # WARN (B:986), reported by checks.py

    def _load_counts(self):
        """counts.tsv (SPEC 2.3) with every validation stop; rows outside the design are excluded, not stopped."""
        path = self.options.counts
        if not path or not os.path.exists(path):
            # collect removes counts.tsv when nothing is counted (B:1384-1386)
            self.check("WARN", "LOAD", f"no counts.tsv ({path}): every count is missing", strict=True)
            return
        _, rows = read_tsv(path, exact_header=COUNTS_HEADER)
        self.record_input(path, "counts")
        levels_of = OrderedDict()
        for line, r in rows:
            engine, bench, run, db, level = r["engine"], r["benchmark"], r["run"], r["database"], r["level"]
            if engine not in ENGINES:
                stop(path, line, "engine", engine, ", ".join(ENGINES))
            tag = self._benchmark(path, line, engine, bench)
            if level not in LEVELS:
                stop(path, line, "level", level, ", ".join(LEVELS))
            if r["class"] != "all":
                stop(path, line, "class", r["class"], "all")
            q = _float(path, line, "q_value", r["q_value"])
            if abs(q - 0.01) >= 1e-9:  # as OT:104
                stop(path, line, "q_value", r["q_value"], "0.01 (B:1311)")
            accepted = _int(path, line, "accepted", r["accepted"], minimum=0)
            entrapment = _int(path, line, "entrapment", r["entrapment"], minimum=0)
            lower = _float(path, line, "lower_bound_fdp", r["lower_bound_fdp"])  # cast: ints in the smoke
            combined = _float(path, line, "combined_fdp", r["combined_fdp"])
            paired = _float(path, line, "paired_fdp", r["paired_fdp"], na_ok=True)
            etna = _int_or_na(path, line, "entrapment_target_not_accepted", r["entrapment_target_not_accepted"])
            eat = _int_or_na(path, line, "entrapment_above_target", r["entrapment_above_target"])
            te = _float(path, line, "te_ratio", r["te_ratio"])
            des, realisation, unit = self._classify(run, db)
            if unit is not None and r["file"] != unit.count_file:
                stop(path, line, "file", r["file"], unit.count_file + " (B:1292)")
            key = (engine, bench, run, db)
            seen = levels_of.setdefault(key, [line])
            if level in seen[1:]:
                stop(path, line, "level", level, "one psm and one peptide row per search (EE-tool:198-204)")
            seen.append(level)
            row = CountRow(line, engine, bench, tag, run, db, r["file"], level, q, accepted, entrapment, lower,
                           combined, paired, etna, eat, te, des, realisation, unit)
            if des == "outside_design":
                self.counts_outside.append(row)
            elif des == "rule11b":
                self.counts_rule11b.append(row)
            else:
                self.counts.append(row)
                self.count_index[key + (level,)] = row
        for key, seen in levels_of.items():
            if sorted(seen[1:]) != ["peptide", "psm"]:
                stop(path, seen[0], "level", ",".join(seen[1:]), "exactly one psm and one peptide row per search "
                                                                 f"{key} (EE-tool:198-204)")

    def _timing_rows(self, path, keep):
        _, rows = read_tsv(path, exact_header=TIMINGS_HEADER)
        return [(path, line, r) for line, r in rows if keep(r)]

    def _load_timings(self):
        """timings.tsv (SPEC 2.5): normalisation, attempts, per-repetition totals, states."""
        o = self.options
        if not o.timings or not os.path.exists(o.timings):
            self.check("INFO", "LOAD", f"no timings.tsv ({o.timings}): no timing")
            rows = []
        else:
            rows = self._timing_rows(o.timings, lambda r: True)
            self.record_input(o.timings, "timings")
        separate = bool(o.scaling_timings) and not _same_file(o.timings, o.scaling_timings)
        if separate:
            for p, line, r in rows:
                if r["benchmark"] == "scaling":
                    stop(p, line, "benchmark", "scaling", "no scaling rows in W when --scaling-work names another "
                                                          "folder (OPEN Q35)")
            rows += self._timing_rows(o.scaling_timings, lambda r: r["benchmark"] == "scaling")
            self.record_input(o.scaling_timings, "scaling timings")
        by_key = OrderedDict()
        for path, line, r in rows:
            engine, bench, run = r["engine"], r["benchmark"], r["run"]
            if engine not in ENGINES:
                stop(path, line, "engine", engine, ", ".join(ENGINES))
            tag = self._benchmark(path, line, engine, bench, extra=("batch", "scaling"))
            threads = _int(path, line, "threads", r["threads"], minimum=1)
            rep = _int(path, line, "repetition", r["repetition"], minimum=0)
            if rep > 3:
                stop(path, line, "repetition", r["repetition"], "0, 1, 2, 3 (B:911)")
            ex = r["exit"]
            if ex not in TIMING_EXITS:
                ex = _int(path, line, "exit", ex)
            stage = r["stage"]
            if ex == "not_run_over_limit":
                if stage != "all":
                    stop(path, line, "stage", stage, "all (a not_run_over_limit row, B:998)")
            elif engine == "msfragger":
                if stage not in ("search", "join", "rescoring"):
                    stop(path, line, "stage", stage, "search, join, rescoring (B:764, 777, 793-807)")
            elif stage != "all":
                stop(path, line, "stage", stage, "all (B:764, 777)")
            wall = _float(path, line, "wall_s", r["wall_s"], na_ok=True)
            cpu = _float(path, line, "cpu_s", r["cpu_s"], na_ok=True)
            rss = None if r["max_rss_kb"] == "NA" else _int(path, line, "max_rss_kb", r["max_rss_kb"], minimum=0)
            db = normalise_db(r["database"])
            if bench == "batch":
                g = self.batch_groups.get(run)
                if g is None:
                    stop(path, line, "run", run, "a batch group of the run table (B:974-977)")
                if db != g.td:
                    stop(path, line, "database", r["database"], g.td + ".fasta (the group's td, SPEC 2.5)")
                known = True
            elif bench == "scaling":
                rr = self.run_by_id.get(run)
                known = rr is not None
                if known and db != rr.db + "_td":
                    stop(path, line, "database", r["database"], rr.db + "_td.fasta (the run's td, SPEC 2.5)")
            else:
                u = self.unit_by_name.get(run)
                known = u is not None
                if known and db != u.td:
                    stop(path, line, "database", r["database"], u.td + ".fasta (the unit's td, SPEC 2.5)")
            row = TimingRow(line, engine, bench, tag, run, r["database"], db, stage, threads, rep, wall, cpu, rss,
                            ex)
            if not known:
                self.timing_outside.append(row)
                continue
            self.timing_rows.append(row)
            key = (engine, bench, run, db, threads if bench == "scaling" else None)
            by_key.setdefault(key, []).append(row)
        for key, krows in by_key.items():
            self.timings[key] = self._timing(key, krows)
            if self.timings[key].n_attempts > 1:
                self.earlier_attempts.append((key, self.timings[key].n_attempts - 1))

    def _expected_stages(self, engine, bench, run):
        """The stage multiset of one repetition (SPEC 2.5 "Complete"): {all} for ProSE and Sage; MSFragger
        {search, rescoring} for single files and scaling, {search, join, rescoring} for pooled samples,
        {search} + n_files x {rescoring} for the batch arm (RM:178)."""
        if engine != "msfragger":
            return {"all": 1}, 1
        if bench == "batch":
            n = self.batch_groups[run].n_files
            return {"search": 1, "rescoring": n}, n
        if bench == "scaling":
            return {"search": 1, "rescoring": 1}, 1
        u = self.unit_by_name[run]
        if u.pooled:
            return {"search": 1, "join": 1, "rescoring": 1}, u.n_files
        return {"search": 1, "rescoring": 1}, 1

    def _timing(self, key, rows):
        """Attempts of one key and the state of the last one (SPEC 2.5 "Attempts")."""
        engine, bench, run, db, kthreads = key
        expected, n_files = self._expected_stages(engine, bench, run)
        first_stage = "search" if engine == "msfragger" else "all"
        attempts, cur, prev = [], None, None
        for r in rows:
            if r.exit == "not_run_over_limit":  # not an attempt (B:996-999)
                prev = r
                continue
            new = (cur is None or prev is None or prev.exit == "not_run_over_limit" or r.threads != prev.threads
                   or (r.stage == first_stage and r.repetition <= prev.repetition))
            if new:
                cur = []
                attempts.append(cur)
            cur.append(r)
            prev = r
        warm_required = bench != "scaling"  # per_file and batch always run repetition 0 (B:911); scaling only on top
        evaluated = [self._attempt(i, a, expected, warm_required) for i, a in enumerate(attempts)]
        unit = self.unit_of_run.get(run) if bench == "scaling" else self.unit_by_name.get(run)
        group = self.batch_groups.get(run) if bench == "batch" else None
        last = rows[-1]
        if last.exit == "not_run_over_limit":
            state, note, used = "not_run_over_limit", "not run: over the limit at a higher thread count (B:996-999)", \
                None
            limit = last.wall
        else:
            used = evaluated[-1]
            state, note, limit = used.state, used.note, used.limit
        if state == "complete" and self.logs_for(bench):  # C24: an untimed rerun after the timed run (B:920)
            folder = self.search_dir(engine, bench, run, db, kthreads)
            if folder and os.path.exists(os.path.join(folder, first_stage + ".log")):
                state, note = "stale_timing", f"{first_stage}.log in the folder: rerun untimed after the timed run"
        missing = Missing(state)
        if state == "complete":
            reps = used.reps
            wall_med = median([reps[r].wall for r in (1, 2, 3)])
            cpu_med = median([reps[r].cpu for r in (1, 2, 3)])
            rss_med = median([reps[r].rss_kb for r in (1, 2, 3)])
            stage_med = {s: median([reps[r].stage_wall[s] for r in (1, 2, 3)]) for s in expected}
        else:
            wall_med = cpu_med = rss_med = missing
            stage_med = {s: missing for s in expected}
        lower = used.lower_bound if used is not None and used.state == "over_limit" else Missing("not_over_limit")
        return Timing(key=key, engine=engine, benchmark=bench, run=run, db=db,
                      threads=(used.threads if used is not None else last.threads), state=state, note=note,
                      attempts=evaluated, attempt=used, reps=(used.reps if used is not None else {}),
                      wall_med=wall_med, cpu_med=cpu_med, rss_med_kb=rss_med, stage_wall_med=stage_med,
                      limit=limit, lower_bound=lower, expected=expected,
                      unit=unit if bench != "batch" else None, group=group, n_files=n_files)

    @staticmethod
    def _rep(r, rows, expected):
        stages = {}
        for x in rows:
            stages[x.stage] = stages.get(x.stage, 0) + 1
        numeric = all(x.wall is not None and x.cpu is not None and x.rss_kb is not None for x in rows)
        if numeric:
            wall = math.fsum(x.wall for x in rows)
            cpu = math.fsum(x.cpu for x in rows)
            rss = max(x.rss_kb for x in rows)
            stage_wall = {s: math.fsum(x.wall for x in rows if x.stage == s) for s in stages}
        else:
            wall = cpu = rss = Missing("NA")
            stage_wall = {s: Missing("NA") for s in stages}
        problems = []
        if stages != expected:
            problems.append(f"stages {_ms(stages)} instead of {_ms(expected)}")
        bad = [x for x in rows if x.exit != 0]
        if bad:
            problems.append(f"exit {bad[0].exit} at stage {bad[0].stage}")
        if not numeric and not bad:
            problems.append("a wall, cpu or rss value is NA")
        return Rep(r, rows, stages, wall, cpu, rss, stage_wall, not problems, "; ".join(problems))

    def _attempt(self, index, rows, expected, warm_required):
        reps = OrderedDict()
        for x in rows:
            reps.setdefault(x.repetition, []).append(x)
        reps = OrderedDict((r, self._rep(r, rs, expected)) for r, rs in sorted(reps.items()))
        threads = rows[0].threads
        over = [x for x in rows if x.exit == "over_limit"]
        if over:
            # over_limit at any repetition (also 0 at the top grid point): no median; lower bound
            # min({completed repetition totals r in 1..3} u {L}) (SPEC 2.5; B:911, 923-925)
            limit = over[0].wall
            done = [reps[r].wall for r in (1, 2, 3) if r in reps and reps[r].complete]
            lower = min(done + [limit]) if limit is not None else (min(done) if done else Missing("NA"))
            return Attempt(index, threads, rows, reps, "over_limit",
                           f"over the limit at stage {over[0].stage} repetition {over[0].repetition}", limit, lower)
        nt = [x for x in rows if x.exit == "no_timing"]
        if nt:
            return Attempt(index, threads, rows, reps, "no_timing",
                           f"no_timing at stage {nt[0].stage} repetition {nt[0].repetition} (B:305-312)")
        problems = [f"repetition {r} missing" for r in (1, 2, 3) if r not in reps]
        if warm_required and 0 not in reps:
            problems.append("repetition 0 missing")
        problems += [f"repetition {r}: {rep.problem}" for r, rep in reps.items() if not rep.complete]
        return Attempt(index, threads, rows, reps, "incomplete" if problems else "complete", "; ".join(problems))

    def _load_side_inputs(self):
        o = self.options
        self.versions = read_versions(o.versions)
        self.record_input(o.versions, "versions")
        if o.scaling_versions and not _same_file(o.versions, o.scaling_versions):
            self.scaling_versions = read_versions(o.scaling_versions)
            self.record_input(o.scaling_versions, "scaling versions")
        else:
            self.scaling_versions = self.versions
        if o.mzml_counts and os.path.exists(o.mzml_counts):
            _, rows = read_tsv(o.mzml_counts, required=("id", "ms2"))
            self.mzml_counts = {}
            for line, r in rows:
                d = dict(r)
                for c in ("bytes", "spectra", "ms1", "ms2", "ms3"):
                    if c in d:
                        d[c] = _int(o.mzml_counts, line, c, d[c], minimum=0)
                self.mzml_counts[r["id"]] = d
            self.record_input(o.mzml_counts, "mzml_counts")
        if o.listing:
            if not os.path.exists(o.listing):
                raise ValidationStop(f"{o.listing}: listing not found (--listing)")
            self.listing = read_listing(o.listing)
            self.record_input(o.listing, "listing")
        if o.references and os.path.exists(o.references):
            self.record_input(o.references, "references")
        for label, p in self.machines:
            if not os.path.exists(p):
                raise ValidationStop(f"{p}: machine file not found (--machine {label}=...)")
            self.record_input(p, f"machine {label}")
        if o.work:
            for level in LEVELS:
                self.record_input(os.path.join(o.work, f"overtuning_{level}.tsv"), f"overtuning_{level}")
            self.record_input(os.path.join(o.work, "commands.log"), "commands.log")
            self.record_input(os.path.join(o.work, "counts_qgrid.tsv"), "counts_qgrid")
        if o.rule11b_work:
            self.record_input(os.path.join(o.rule11b_work, "counts.tsv"), "rule11b counts")

    def _loader_info(self):
        """INFO lines on what was loaded (names and counts only)."""
        self.check("INFO", "LOAD", f"runs: {len(self.runs)} runs, {len(self.units)} units, {len(self.groups)} groups, "
                                   f"{len(self.batch_groups)} batch groups, {len(self.scaling_runs)} scaling runs; "
                                   f"design {self.design_mode}; POOLED_ARRANGEMENT {self.pooled_arrangement}")
        self.check("INFO", "LOAD", f"counts: {len(self.counts)} rows in the design, {len(self.counts_outside)} outside, "
                                   f"{len(self.counts_rule11b)} rule11b; tags: {', '.join(self.tags) or 'none'}")
        self.check("INFO", "LOAD", f"coverage: {len(self.coverage)} rows in the design, "
                                   f"{len(self.coverage_outside)} outside")
        self.check("INFO", "LOAD", f"timings: {len(self.timing_rows)} rows, {len(self.timings)} keys, "
                                   f"{len(self.earlier_attempts)} keys with earlier attempts, "
                                   f"{len(self.timing_outside)} rows outside the design")
        separate_s = self.scaling_out_dir != self.out_dir
        if self.options.logs == "yes" and not self.logs_available:
            self.check("WARN", "LOGS", "--logs yes, but W/out is missing: log-based outputs are skipped")
        elif not self.logs_available:
            self.check("INFO", "LOGS", "no W/out logs read: log-based outputs (O15b, O19 settings, C23, C24) skipped"
                       + ("; S/out logs read for the scaling searches (C24)" if separate_s and
                          self.scaling_logs_available else ""))
        if separate_s and self.options.logs != "no" and not self.scaling_logs_available:
            text = ("no S/out logs (--scaling-work S): C24 and the stale_timing test (SPEC 2.5) skip the scaling "
                    "searches; only S's timings.tsv, coverage.tsv and versions.txt are read")
            if self.options.logs == "yes":
                self.check("WARN", "LOGS", "--logs yes, but " + text)
            else:
                self.check("INFO", "LOGS", text)


def _ms(stages):
    return "{" + ", ".join(f"{s}x{n}" if n > 1 else s for s, n in sorted(stages.items())) + "}"


def write_atomic(path, text):
    """Writes text to path through a temporary file and os.replace (SPEC 1 "Output folder")."""
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    tmp = f"{path}.tmp.{os.getpid()}"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    os.replace(tmp, path)
    return path


def sha256_file(path):
    """The SHA256 hex digest of a file, read in 1 MiB blocks (provenance.tsv, SPEC 1; the qgrid check of O13 and C2)."""
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def load(options):
    """Reads and validates every input of one build (SPEC 2.1-2.6) -> Ctx. Raises ValidationStop (exit 2)."""
    options.resolve()
    ctx = Ctx(options)
    ctx._load_runs()
    ctx._load_rule11b()
    ctx._load_pooled_arrangement()
    ctx._load_coverage()
    ctx._load_counts()
    ctx._load_timings()
    ctx._load_side_inputs()
    ctx._loader_info()
    return ctx
