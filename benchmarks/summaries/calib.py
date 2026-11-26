"""Supplement outputs O19, O20 and O21 (SPEC 3.4): the calibration supplement with the chosen-settings tables and their
log parsers, the external Percolator control and the prediction supplement.

Citation keys as in the SPEC: DS = datasets/DATASETS.md, B = benchmarks/bench.py, RM = benchmarks/README.md,
OT = benchmarks/overtuning.py, PI = datasets/params/<name>.ini, EE-lib = EntrapmentEvaluation.cpp.

Outputs (--only keywords: calibration -> O19, percolator -> O20, prediction -> O21)
  O19  tables/O19_calibration_counts.tsv   the CAL_RUNS, every engine-arm and level (DS:771-776; RM:154-171)
       tables/O19_settings_msfragger.tsv   the settings MSFragger chose, per counted MSFragger per_file* search (DS:691)
       tables/O19_settings_prose.tsv       ProSE's fragment tolerance per input of every counted ProSE search (OPEN Q28)
       tables/O19_settings_sage.tsv        Sage's configured fragment tolerance per counted Sage search (SPEC O19)
       keys cal.<tag>.<level>.{lead,n_runs} (main_text_allowed no: mostly tuning runs, SPEC O19 "Text")
  O20  tables/O20_external_percolator.tsv, _datasets.tsv, _summary.tsv; keys percolator.<scope>.<level>.<comparator>.*
       only when counts or coverage hold per_file_percolator_s{1,42,137} rows (SPEC 4: not run yet)
  O21  tables/O21_prediction.tsv, _datasets.tsv, _summary.tsv; keys prediction.<level>.<comparison>.*
       only when counts or coverage hold per_file_peptdeep / per_file_msbooster rows (SPEC 4: not run yet)
Check lines written here: INFO/WARN O19, O20, O21 (what was built, the arm coverage of the CAL_RUNS, the settings rows
without a value, ProSE searches whose inputs file, run table and log disagree, files of search folders that could not
be read). C23 is checks.py's (c23_settings): it reads O19_settings_msfragger / _prose by their columns benchmark, unit,
database, source, the value columns (VALUE_COLUMNS) and ProSE's input, with the rule of search_lacks_value that INFO
O19 uses too: a search lacks settings when one of its rows has no source or a value column without a value (NA, '' or
'-'), or when it has no row (MSFragger), or when a file of the run table has no row of its name (ProSE) (SPEC 5).

Decisions taken here where the SPEC leaves a choice
- O19 FDP: an arm row averages "the realisations counted in both the arm and the main arm of that engine" (SPEC O19),
  i.e. those with N > 0 in both. The SPEC gives no set for the main row, which stands next to every arm of its engine:
  it averages the realisations with N > 0 in the main arm and in every arm of that engine that ran on the unit (has a
  coverage row), so the main row has one value. When every arm counted the same realisations (both trials), each arm
  row and the main row average the same set; otherwise the main row's set is the smaller one, and fdp_shuffled_n
  shows it. Sage has no arm (DS:774): its own counted realisations. The natural database (velos, DS:394) follows the
  same rule. FDP values are fractions (EE's combined_fdp, EE-lib:30-34), as in counts.tsv. They are computed with
  fdp.py's "FDP as O11" (fdp.fdp_as_o11 with shared_with = the (engine, benchmark) pairs above; fdp.search_fdp per
  search for O20 and O21), so O11 and the supplements share one definition.
- O19 ratio_to_main is NA on the main rows (a main arm has no ratio to itself).
- Which log (SPEC O19 "Which log"; B:911-922): a folder with <stage>.r<rep>.log is a timed search, the last of r1-r3
  (r3; the last r-log present when r3 is missing, the log column names it) is read and r1-r3 are compared (note
  'varies', OPEN Q29); a folder with <stage>.log is read from it. measure() empties the folder before every search
  (B:896-904), so a timed search rerun untimed (stale_timing, SPEC 2.5) holds only <stage>.log, or both in a copy
  merged from two states of the folder; its counted output is the rerun's, so <stage>.log is read (SPEC O19 "Which
  log" names r3 for every timed search: a deviation, README). Every MSFragger and ProSE row of a stale_timing search
  (ctx.timings, any stage's <stage>.log) has a note 'stale_timing ...' naming the log read (Sage reads sage.json, no
  log); a folder with r-logs and <stage>.log whose search is not stale_timing (untimed, or another timing state) gets
  the note '<stage>.r<rep>.log and <stage>.log in the folder: <stage>.log used'.
- The readers take the build's file cache (ctx.files, tables.Files): one listing per folder and one read per file,
  shared with O15b, C24 and provenance.tsv; every file read is recorded for provenance.tsv (SPEC 1), a file that could
  not be read is not. A listed file that cannot be read (no permission, a folder of that name) gives the note
  '<file> not read: <error>' on every row of its search and a WARN O19; a value that needs the file is NA (an
  unreadable log read gives no value at all, an unreadable inputs file the run table's files).
- No readable log, no value, unless the configuration fixes the value: a search without a log keeps its configured
  values only when the engine does not choose them at run time (MSFragger calibrate_mass 0 or 1; ProSE with
  calibration off: summary.yaml calibration_enabled false, or without that key the cal_off arm). A calibrated search
  without a log gets NA (note 'no search log' or 'no all log') and a C23 WARN (strict for MSFragger), as for an
  unreadable log (SPEC C23 says "parsed or configured": a deviation, README). An unreadable log gives NA in every arm,
  also where the configuration fixes the value. A calibrated MSFragger log without a 'New' line keeps the configured
  values with the note 'no New lines', as ProSE's 'no fragment calibration line'.
- ProSE lines are assigned to inputs by name only, by the '[ProSE] [i/n] Searching <file>' line that precedes them.
  The name is the file name without its folder and a final '.mzML' (B:740-741), compared exactly. Such lines are in
  the pooled logs of builds before P and in the P logs of the engine-node trial, where block i names line i of
  'inputs' in every search. Without such lines the i-th Fragment line goes to input i of the folder's 'inputs' file
  (SPEC O19). An input the Searching lines do not name gets no value, also when they name none of the inputs. A match
  by position could swap values, since the blocks need not follow the inputs file: the pooled test fixture, in the log
  shape of builds before P, searches DN05_r2 before DN05_r1. An inputs file that differs from the run table and a log
  that searched other files give a WARN O19.
- O20 per run: the mean over the counted seeds is shown with n_seeds; a unit enters a pair only with all 3 seeds
  counted and > 0 for both engines (SPEC O20). FDP: per realisation the mean over the 3 seeds of combined_fdp (O11's
  value), then per run the mean over the realisations both engines have (OPEN Q37: s1-s3 only).
- O21: three comparisons in long format (ProSE+PeptDeep / MSFragger+MSBooster, ProSE+PeptDeep / ProSE main,
  MSFragger+MSBooster / MSFragger main), each with its own run set as O2's pairs (SPEC O21 "Per run").
"""
import json
import os
import re
import shlex
from collections import OrderedDict

from . import design
from . import fdp
from . import tables as T

# ---------------------------------------------------------------- O19 constants (SPEC 2.2 ARMS, O19)
CAL_TAGS = ("cal_off", "cal1", "cal0")  # RM:163-165, DS:771-773
# the engines of the counts table in the order of SPEC O19 "Arms": ProSE main, cal_off; MSFragger main, cal1, cal0;
# Sage main only, the "no arm" reference (DS:774)
CAL_ENGINE_ORDER = ("prose", "msfragger", "sage")
COUNTS_COLUMNS = ("unit", "class", "grade", "group", "engine", "arm", "level", "accepted_td", "ratio_to_main",
                  "fdp_shuffled_mean", "fdp_shuffled_sd", "fdp_shuffled_n", "fdp_natural", "status")
MSF_COLUMNS = ("engine", "benchmark", "unit", "database", "log", "source", "fragment_tol", "fragment_tol_unit",
               "use_topN_peaks", "minimum_ratio", "intensity_transform", "remove_precursor_peak",
               "max_fragment_charge", "note")
PROSE_COLUMNS = ("engine", "benchmark", "unit", "input", "database", "log", "source", "prose_fragment_offset",
                 "prose_fragment_sigma", "prose_fragment_tol", "prose_fragment_tol_unit", "prose_covered_pct", "note")
# Sage: the SPEC names the content (the configured tolerance), not the columns; max_fragment_charge is the cap the
# driver sets where ProSE scores several fragment charges (B:581-588), NA = Sage's default
SAGE_COLUMNS = ("engine", "benchmark", "unit", "database", "log", "source", "fragment_tol", "fragment_tol_unit",
                "max_fragment_charge", "note")

# ---------------------------------------------------------------- log parsers (SPEC O19 "MSFragger parser", "ProSE parser")
# MSFragger 4.4.1: 'New <key> = <value>' lines between the banner 'MASS CALIBRATION AND PARAMETER OPTIMIZATION' and
# '... DONE IN <x> MIN' (calibrate_mass 2). calibrate_mass 1 prints only 'MASS CALIBRATION' banners, 0 none; both
# give the configured values (SPEC O19).
MSF_BANNER = "MASS CALIBRATION AND PARAMETER OPTIMIZATION"
MSF_NEW = re.compile(r"^New (\w+) = (.+?)\s*$")
# the keys reported (SPEC O19; DS:776: fragment tolerance, max_fragment_charge, remove_precursor_peak, peak processing)
MSF_KEYS = ("fragment_mass_tolerance", "use_topN_peaks", "minimum_ratio", "intensity_transform",
            "remove_precursor_peak", "max_fragment_charge")
MSF_TOL = re.compile(r"^([-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?)\s*([A-Za-z]+)?$")
# ProSE (SPEC O19 "ProSE parser"): '[ProSE]   Fragment:  offset <o>, sigma <s> ppm|Da (...) -> tolerance <configured>
# -> <chosen> ppm|Da (covers <c> % ...'. Not matched: '[ProSE] Fragment tolerance N Da exceeds the deisotoping limit'
# and '[ProSE] Fragment idx : ...'.
PROSE_FRAGMENT = re.compile(r"^\[ProSE\]\s+Fragment:\s+offset\s+(\S+),\s+sigma\s+(\S+)\s+(ppm|Da)\s+\(.*?\)\s+->\s+"
                            r"tolerance\s+(\S+)\s+->\s+(\S+)\s+(ppm|Da)\s+\(covers\s+(\S+)\s+%")
PROSE_SEARCHING = re.compile(r"^\[ProSE\]\s+\[(\d+)/(\d+)\]\s+Searching\s+(.+?)\s*$")
PROSE_KEPT = "the configured fragment tolerance is kept"
PROSE_INSUFFICIENT = re.compile(r"^\[ProSE\]\s+Calibration:\s+insufficient PSMs")

# ---------------------------------------------------------------- O20 / O21 constants (SPEC O20, O21; OPEN Q37, Q38)
PERCOLATOR_BENCHMARKS = tuple(f"per_file_percolator_s{s}" for s in design.PERCOLATOR_SEEDS)  # DS:613
PRED_BENCHMARKS = ("per_file_peptdeep", "per_file_msbooster")
O20_RUN_COLUMNS = ("pair", "level", "kind", "class", "grade", "group", "unit", "role", "prose_n_seeds", "prose",
                   "comparator_n_seeds", "comparator", "ratio", "used", "reason", "fdp_prose", "fdp_comparator",
                   "fdp_n_shared")
O20_DATASET_COLUMNS = ("pair", "level", "kind", "side", "class", "grade", "group", "n_units", "n_used", "gmean",
                       "lead_pct", "sum_ratio", "sum_lead_pct", "fdp_prose_mean", "fdp_comparator_mean", "fdp_n_runs",
                       "note")
O20_SUMMARY_COLUMNS = ("pair", "level", "scope", "n_datasets", "n_runs", "equal_weight", "lead_pct", "run_weighted",
                       "rw_lead_pct", "sum_ratio", "sum_lead_pct", "dropped_datasets")
O21_RUN_COLUMNS = ("comparison", "level", "kind", "class", "grade", "group", "unit", "role", "instrument",
                   "numerator", "denominator", "ratio", "used", "reason", "fdp_numerator", "fdp_denominator",
                   "fdp_n_shared")
O21_DATASET_COLUMNS = ("comparison", "level", "kind", "side", "class", "grade", "group", "instrument", "n_units",
                       "n_used", "gmean", "lead_pct", "fdp_numerator_mean", "fdp_denominator_mean", "fdp_n_runs",
                       "note")
O21_SUMMARY_COLUMNS = ("comparison", "level", "scope", "n_datasets", "n_runs", "equal_weight", "lead_pct",
                       "dropped_datasets", "msbooster_version")
FMT_COUNT_MEAN = ".3f"  # a mean of integer counts over the seeds


class Side:
    """One side of a comparison: an engine and the benchmark(s) whose td count it takes. With several benchmarks
    (the three Percolator seeds, SPEC O20) the value is their mean."""

    def __init__(self, engine, benchmarks, label):
        self.engine = engine
        self.benchmarks = tuple(benchmarks)
        self.label = label


# the comparisons of O21 (SPEC O21 "Per run": arm/main per engine, ProSE+PeptDeep / MSFragger+MSBooster)
PRED_COMPARISONS = (
    ("peptdeep_vs_msbooster", Side("prose", ("per_file_peptdeep",), "prose_peptdeep"),
     Side("msfragger", ("per_file_msbooster",), "msfragger_msbooster")),
    ("peptdeep_vs_main", Side("prose", ("per_file_peptdeep",), "prose_peptdeep"),
     Side("prose", ("per_file",), "prose_main")),
    ("msbooster_vs_main", Side("msfragger", ("per_file_msbooster",), "msfragger_msbooster"),
     Side("msfragger", ("per_file",), "msfragger_main")),
)


# ================================================================ entry point
def build(ctx):
    """O19, O20 and O21 (SPEC 3.4). Reads ctx only; writes through write_table, number and check."""
    if ctx.want("calibration"):
        build_counts(ctx, design.CAL_RUNS)
        write_settings(ctx, collect_settings(ctx))
    if ctx.want("percolator"):
        build_percolator(ctx)
    if ctx.want("prediction"):
        build_prediction(ctx, design.PRED_GROUPS)


# ================================================================ small helpers
def is_number(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and not T.is_missing(x)


def source_side(units):
    """numbers.tsv source_side of a set of units (SPEC 3.8): their common side, 'mixed', or 'none'."""
    sides = {u.side for u in units if u.side}
    if not sides:
        return "none"
    if len(sides) == 1:
        return sides.pop()
    return "mixed"


def bench_rank(benchmark):
    """Sort key of a per_file* benchmark: per_file, then the arms in ARMS order, then further tags by name."""
    names = list(design.ARMS)
    return (names.index(benchmark), benchmark) if benchmark in names else (len(names), benchmark)


def coverage_runs(ctx):
    """{(engine, benchmark, run)} of every coverage row inside the design (which arms ran on a unit)."""
    return {(c.engine, c.benchmark, c.run) for c in ctx.coverage}


def status_text(ctx, engine, benchmark, unit, db=None):
    """coverage's status text of a search (SPEC 2.4), or 'no_coverage' when the search has no row (an arm that was
    not run has no folder and no row, B:1346-1369)."""
    c = ctx.coverage_row(engine, benchmark, unit.name, db or unit.td)
    return c.status if c is not None else "no_coverage"


def mean_over(values):
    """fsum mean of floats (SPEC 2.7); Missing('empty') for none."""
    return T.fmean(values) if values else T.Missing("empty")


# ================================================================ O19 counts (SPEC O19 "Counts file")
def cal_arms(engine):
    """(benchmark, arm label) of an engine in the calibration supplement: main first, then its arms (SPEC 2.2 ARMS,
    O19 "Arms")."""
    out = [("per_file", "main")]
    for tag in CAL_TAGS:
        arm = design.ARMS["per_file_" + tag]
        if engine in arm.engines:
            out.append((arm.benchmark, tag))
    return out


def build_counts(ctx, cal_runs):
    """tables/O19_calibration_counts.tsv (SPEC O19 "Counts file"): per CAL_RUNS unit (RM:160-161, DS:775), engine-arm
    and level: the td accepted count at q <= 0.01, the ratio arm/main of the same engine (both counted, > 0; zero
    counts are out of every ratio, OT:113-116), the shuffled FDP mean, SD (n - 1, OPEN Q14) and n, and the natural FDP
    (velos_125_R1, DS:394), over the realisations described in the module docstring. Arms are searched on td and
    entrap only (RM:162), so arath is not part of it.
    Keys cal.<tag>.<level>.{lead,n_runs}: lead = 100 (G - 1) with G the geometric mean of the per-run arm/main ratios
    over the non-decision CAL units with both counted (one run per group, so equal weight per dataset, SPEC 3
    "Aggregation"); main_text_allowed no (SPEC O19 "Text"). cal_runs: run ids (design.CAL_RUNS; tests pass their own)."""
    ran = coverage_runs(ctx)
    units, absent = [], []
    for rid in cal_runs:
        u = ctx.unit_by_name.get(rid) or ctx.unit_of_run.get(rid)
        if u is None:
            absent.append(rid)
        elif u not in units:
            units.append(u)
    if absent:
        ctx.check("INFO", "O19", f"{len(absent)} of {len(cal_runs)} CAL_RUNS not in the run table: "
                                 f"{', '.join(absent)}")
    rows = []
    ratios = OrderedDict()  # (tag, level) -> [(unit, ratio)]
    for u in units:
        for engine in CAL_ENGINE_ORDER:
            if engine not in u.expected:
                continue  # Sage on a bycz unit is not run by design (B:1357); no CAL run is bycz
            arms = cal_arms(engine)
            run_arms = [b for b, tag in arms if b == "per_file" or (engine, b, u.name) in ran]
            for b, tag in arms:
                for level in ctx.levels:
                    acc = ctx.accepted(engine, u, level, benchmark=b)
                    if tag == "main":
                        rtm = T.Missing("main")
                    else:
                        rtm = T.ratio(acc, ctx.accepted(engine, u, level, benchmark="per_file"))
                        if is_number(rtm) and not u.is_decision:
                            ratios.setdefault((tag, level), []).append((u, rtm))
                    ran_here = b in run_arms  # an arm without a coverage row on the unit has no FDP set
                    # FDP as O11 (fdp.fdp_as_o11) over the O19 FDP set (module docstring): an arm row over the
                    # realisations counted (N > 0) in both this arm and the main arm of the engine (SPEC O19); the
                    # main row over those counted in the main arm and in every arm of the engine that ran on the unit
                    if tag == "main":
                        shared_with = [(engine, rb) for rb in run_arms]
                    else:
                        shared_with = [(engine, "per_file"), (engine, b)]
                    if ran_here:
                        shuffled = fdp.fdp_as_o11(ctx, engine, b, u, level, "shuffled", shared_with=shared_with)
                        n_shared = shuffled.n_shared
                        mean, sd = T.mean_sd([shuffled.values[s] for s in shuffled.shared])
                    else:
                        n_shared = 0
                        mean, sd = T.Missing("no_coverage"), T.Missing("no_coverage")
                    if not u.stems_of("natural"):
                        natural = T.Missing("no_natural")
                    elif not ran_here:
                        natural = T.Missing("no_coverage")
                    else:
                        nat = fdp.fdp_as_o11(ctx, engine, b, u, level, "natural", shared_with=shared_with)
                        natural = nat.values[nat.shared[0]] if nat.shared else T.Missing("not_shared")
                    rows.append(OrderedDict([
                        ("unit", u.name), ("class", u.cls), ("grade", u.grade), ("group", u.group),
                        ("engine", engine), ("arm", tag), ("level", level), ("accepted_td", acc),
                        ("ratio_to_main", rtm), ("fdp_shuffled_mean", mean), ("fdp_shuffled_sd", sd),
                        ("fdp_shuffled_n", n_shared), ("fdp_natural", natural),
                        ("status", status_text(ctx, engine, b, u))]))
    ctx.write_table("O19_calibration_counts", COUNTS_COLUMNS, rows,
                    header_note="O19 calibration supplement (SPEC 3.4; DS:771-776; RM:154-171): accepted_td at "
                                "q <= 0.01 on the plain database; ratio_to_main = arm/main of the same engine (both "
                                "counted, > 0); FDP = combined entrapment FDP as a fraction; an arm row over the "
                                "realisations with N > 0 in both the arm and the engine's main arm (SPEC O19), the "
                                "main row over those with N > 0 in the main arm and every arm of the engine run on "
                                "the unit")
    for tag in CAL_TAGS:
        for level in ctx.levels:
            pairs = ratios.get((tag, level), [])
            ld = T.lead(T.gmean([r for _, r in pairs]))
            side = source_side([u for u, _ in pairs])
            ctx.number(f"cal.{tag}.{level}.lead", ld, text=T.fmt(ld, T.FMT_LEAD), unit="%", output="O19",
                       protocol_ref="DS:771-776", source_side=side, main_text_allowed="no")
            ctx.number(f"cal.{tag}.{level}.n_runs", len(pairs), unit="runs", output="O19",
                       protocol_ref="DS:775", source_side=side, main_text_allowed="no")
    arm_coverage_check(ctx, units)


def arm_coverage_check(ctx, units):
    """INFO/WARN O19: per calibration arm, the counted td + entrapment searches over the CAL units, against the
    expected td + entrap count (9 + 28 = 37 on the paper's run table, SPEC 7 V3; RM:162: td and entrap only); WARN
    for an arm run on part of them, and for arm searches on other units (outside RM:160-161)."""
    cal_names = {u.name for u in units}
    expected = sum(1 + len(u.entrap) for u in units)
    parts, short = [], []
    for tag in CAL_TAGS:
        arm = design.ARMS["per_file_" + tag]
        for engine in arm.engines:
            n = 0
            for u in units:
                for s in (u.td,) + tuple(x for x, _, _ in u.entrap):
                    c = ctx.coverage_row(engine, arm.benchmark, u.name, s)
                    if c is not None and c.state == "ok" and c.counted:
                        n += 1
            parts.append(f"{engine} {tag} {n}")
            if 0 < n < expected:
                short.append(f"{engine} {tag} {n}")
    if units:
        ctx.check("INFO", "O19", f"counted searches per arm over {len(units)} CAL units (expected {expected}: td + "
                                 f"entrap, RM:162): {', '.join(parts)}")
    if short:
        ctx.check("WARN", "O19", f"calibration arms with fewer counted searches than expected ({expected}): "
                                 f"{', '.join(short)}")
    other = sorted({c.run for c in ctx.coverage if c.tag in CAL_TAGS and c.run not in cal_names})
    if other:
        ctx.check("WARN", "O19", f"calibration-arm searches on {len(other)} unit(s) outside CAL_RUNS (RM:160-161), "
                                 f"not in O19: {T.list_text(other)}")


# ================================================================ O19 settings: log parsers (SPEC O19, T23)
# Every reader takes an optional files (tables.Files, the build's cache: ctx.files); without it the file is read
# directly.
def _files(files):
    return files if files is not None else T.Files()


def read_lines(path, files=None):
    return _files(files).text(path).splitlines()


def parse_msfragger_log(path, files=None):
    """The 'New <key> = <value>' lines of MSFragger's 'MASS CALIBRATION AND PARAMETER OPTIMIZATION' block
    (SPEC O19 "MSFragger parser"): OrderedDict key -> value text (the last line of a key wins; keys outside MSF_KEYS
    are kept and named in the row's note). Empty for calibrate_mass 1 (only 'MASS CALIBRATION' banners) and 0 (no
    banner)."""
    out = OrderedDict()
    inside = False
    for line in read_lines(path, files):
        if MSF_BANNER in line:
            inside = "DONE IN" not in line
            continue
        if inside and "DONE IN" in line:
            inside = False
            continue
        if inside:
            m = MSF_NEW.match(line.strip())
            if m:
                out[m.group(1)] = m.group(2).strip()
    return out


def read_fragger_params(path, files=None):
    """fragger.params of a search folder (written by write_fragger, B:716-727): {key: value text}, comments after
    '#' removed. None when the file is absent."""
    files = _files(files)
    if not path or not files.exists(path):
        return None
    out = OrderedDict()
    for line in read_lines(path, files):
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        key, _, value = s.partition("=")
        out[key.strip()] = value.split("#", 1)[0].strip()
    return out


def unit_name(text):
    """'PPM'/'ppm' -> 'ppm', 'DA'/'Da'/'da' -> 'Da', else None."""
    return {"ppm": "ppm", "da": "Da"}.get(str(text or "").lower())


def to_number(text):
    """An int or float from a log or parameter value, else the text itself."""
    t = str(text).strip()
    if re.fullmatch(r"[-+]?\d+", t):
        return int(t)
    if re.fullmatch(r"[-+]?(\d+\.?\d*|\.\d+)([eE][-+]?\d+)?", t):
        return float(t)
    return t


def to_float(text):
    """A float from a log value, or Missing('unparsed')."""
    v = to_number(text)
    return float(v) if is_number(v) else T.Missing("unparsed")


def msfragger_settings(chosen, configured):
    """The settings of one MSFragger search (SPEC O19): each key from its 'New' line (chosen) or else from
    fragger.params (configured; fragment_mass_units 0 = Da, 1 = ppm, B:618).
    Returns (values {column: value}, source, notes): source 'chosen' (every key from New lines), 'configured' (no New
    line, at least one key from fragger.params), 'mixed' (some keys from New lines, not all: the configured ones named
    in 'configured: <keys>', those in neither in 'missing: <keys>') or Missing('no_settings') (no key at all); Missing
    for a key in neither. Notes also name New keys outside
    MSF_KEYS ('other New keys') and the configured tolerance when the chosen one has another unit (MSFragger chooses
    a ppm tolerance for the 0.5 Da ion-trap searches)."""
    values, notes, from_chosen, from_conf, lacking = OrderedDict(), [], [], [], []
    conf = configured or {}
    conf_unit = {"0": "Da", "1": "ppm"}.get(conf.get("fragment_mass_units", ""))
    for key in MSF_KEYS:
        if key in chosen:
            from_chosen.append(key)
            raw = chosen[key]
            if key == "fragment_mass_tolerance":
                m = MSF_TOL.match(raw)
                unit = unit_name(m.group(2)) if m else None
                if m is None or unit is None:
                    values["fragment_tol"], values["fragment_tol_unit"] = T.Missing("unparsed"), T.Missing("unparsed")
                    notes.append(f"unparsed fragment_mass_tolerance line ({raw})")
                else:
                    values["fragment_tol"], values["fragment_tol_unit"] = float(m.group(1)), unit
                    if conf_unit and unit != conf_unit and key in conf:
                        notes.append(f"configured tolerance {conf[key]} {conf_unit}")
            else:
                values[key] = to_number(raw)
        elif key in conf:
            from_conf.append(key)
            if key == "fragment_mass_tolerance":
                units = conf_unit
                tol = to_number(conf[key])
                values["fragment_tol"] = float(tol) if is_number(tol) else T.Missing("unparsed")
                values["fragment_tol_unit"] = units if units else T.Missing("fragment_mass_units")
                if units is None:
                    notes.append(f"fragment_mass_units {conf.get('fragment_mass_units', 'missing')} (0 or 1, B:618)")
            else:
                values[key] = to_number(conf[key])
        else:
            lacking.append(key)
            if key == "fragment_mass_tolerance":
                values["fragment_tol"], values["fragment_tol_unit"] = T.Missing("missing"), T.Missing("missing")
            else:
                values[key] = T.Missing("missing")
    if from_chosen and not from_conf and not lacking:
        source = "chosen"
    elif from_chosen:
        source = "mixed"
        if from_conf:
            notes.append("configured: " + ",".join(from_conf))
    elif from_conf:
        source = "configured"
    else:
        source = T.Missing("no_settings")
    if lacking:
        notes.append("missing: " + ",".join(lacking))
    other = [k for k in chosen if k not in MSF_KEYS]
    if other:
        notes.append("other New keys: " + ",".join(other))
    return values, source, notes


def parse_prose_log(path, files=None):
    """ProSE's fragment calibration lines (SPEC O19 "ProSE parser").
    Returns (sections, ordered): sections = OrderedDict input stem -> {'fragment': tuple or None, 'kept': bool,
    'insufficient': bool}, one per '[ProSE] [i/n] Searching <file>' line (stem = file name without .mzML, as
    B:740-741); ordered = every matched Fragment tuple in file order (for logs without Searching lines). A Fragment
    tuple is (offset, sigma, sigma_unit, configured_tol, tol, tol_unit, covered_pct). The deisotoping-limit line
    '[ProSE] Fragment tolerance ... exceeds ...', the 'Fragment idx' line and the tolerance estimate '[ProSE]
    Fragment     : median N ppm, MAD N -> recommend N ppm' do not match PROSE_FRAGMENT. 'kept': the section's
    'covers only N % ... the configured fragment tolerance is kept' line (P logs: it precedes the Fragment line, whose
    covered % is then that of the rejected |offset| + 4 sigma candidate)."""
    sections, ordered, current = OrderedDict(), [], None
    for line in read_lines(path, files):
        s = line.rstrip()
        m = PROSE_SEARCHING.match(s)
        if m:
            name = os.path.basename(m.group(3).replace("\\", "/"))
            stem = name[:-len(".mzML")] if name.endswith(".mzML") else name
            current = sections.setdefault(stem, {"fragment": None, "kept": False, "insufficient": False})
            continue
        m = PROSE_FRAGMENT.match(s)
        if m:
            frag = (to_float(m.group(1)), to_float(m.group(2)), m.group(3), to_float(m.group(4)),
                    to_float(m.group(5)), m.group(6), to_float(m.group(7)))
            ordered.append(frag)
            if current is not None:
                current["fragment"] = frag
            continue
        if current is not None:
            if PROSE_KEPT in s:
                current["kept"] = True
            if PROSE_INSUFFICIENT.match(s):
                current["insufficient"] = True
    return sections, ordered


def prose_by_input(path, inputs, files=None):
    """assign_inputs of one ProSE log (parse_prose_log)."""
    return assign_inputs(*parse_prose_log(path, files), inputs)


def assign_inputs(sections, ordered, inputs):
    """({input: section or None}, n extra) from parse_prose_log's (sections, ordered): by the Searching lines, by name
    only, else the i-th Fragment line -> input i (SPEC O19). With Searching lines, an input the log did not search
    maps to None (also when they name none of the inputs: their order need not be that of the inputs file), and n
    extra counts the searched files that are not in inputs; without them, n extra counts the Fragment lines beyond the
    inputs."""
    if sections:
        return {i: sections.get(i) for i in inputs}, sum(1 for s in sections if s not in inputs)
    out = {}
    for k, name in enumerate(inputs):
        frag = ordered[k] if k < len(ordered) else None
        out[name] = {"fragment": frag, "kept": False, "insufficient": False}
    return out, max(0, len(ordered) - len(inputs))


def read_sage_json(path, files=None):
    """sage.json of a search folder (B:572-591, 768-770): (fragment_tol, unit, max_fragment_charge, notes).
    fragment_tol is an object {"ppm"|"da": [-x, x]} (B:574); x is reported, an asymmetric window is named in a note."""
    cfg = json.loads(_files(files).text(path))
    if not isinstance(cfg, dict):
        raise ValueError("sage.json is not an object")
    notes = []
    ft = cfg.get("fragment_tol")
    tol, unit = T.Missing("missing"), T.Missing("missing")
    if isinstance(ft, dict) and len(ft) == 1:
        key, win = next(iter(ft.items()))
        unit = unit_name(key) or T.Missing("unparsed")
        if isinstance(win, list) and len(win) == 2 and all(is_number(x) for x in win):
            lo, hi = float(win[0]), float(win[1])
            tol = hi
            if lo != -hi:
                notes.append(f"asymmetric window [{lo}, {hi}]")
        else:
            tol = T.Missing("unparsed")
    else:
        notes.append("no fragment_tol object")
    mfc = cfg.get("max_fragment_charge")
    mfc = mfc if is_number(mfc) else T.Missing("sage_default")  # set only where ProSE caps the charges (B:581-588)
    return tol, unit, mfc, notes


def timed_logs(folder, stage, files=None):
    """The <stage>.r<rep>.log of r1-r3 present in a search folder, in repetition order."""
    names = _files(files).names(folder) or frozenset()
    return [f"{stage}.r{r}.log" for r in (1, 2, 3) if f"{stage}.r{r}.log" in names]


def pick_logs(folder, stage, files=None):
    """(log used, [logs compared]) of one search folder (SPEC O19 "Which log"; B:920): an untimed search has
    <stage>.log, which is used; a timed search has <stage>.r<rep>.log and the last of r1-r3 is used (r3, the
    repetition whose output is counted, B:911-922), r1-r3 compared. A folder with both is a timed search rerun
    untimed (stale_timing, SPEC 2.5): its counted output, and so the log used, is the untimed rerun's <stage>.log
    (measure() empties the folder before every search, B:896-904, so only a copy merged from two states holds both).
    (None, []) when neither exists."""
    files = _files(files)
    names = files.names(folder) or frozenset()
    if f"{stage}.log" in names:
        return f"{stage}.log", [f"{stage}.log"]
    reps = timed_logs(folder, stage, files)
    if reps:
        return reps[-1], reps
    return None, []


def read_inputs(folder, files=None):
    """The run ids a search read, from its 'inputs' file (B:906-907), or None."""
    files = _files(files)
    p = os.path.join(folder, "inputs")
    if not files.exists(p):
        return None
    return [x.strip() for x in read_lines(p, files) if x.strip()]


def _stale_note(ctx, engine, benchmark, unit, db, folder, stage, used):
    """The note of a search whose timing is stale_timing (SPEC 2.5: an untimed <stage>.log of any stage in the timed
    folder, ctx.timings), or whose untimed <stage>.log is used next to r-logs: which log the values come from.
    'stale_timing: all.log of the untimed rerun used[, all.r<rep>.log ignored]' when the plain log is used;
    'stale_timing (<logs> in the folder): <log> used' when the folder is stale through another stage's log;
    'all.r<rep>.log and all.log in the folder: all.log used' when the search is not stale_timing (no timing key, or
    another state such as incomplete) but its folder holds both."""
    t = ctx.timings.get((engine, benchmark, unit, db, None))
    stale = t is not None and t.state == "stale_timing"
    timed = timed_logs(folder, stage, ctx.files)
    if used == f"{stage}.log" and stale:
        return (f"stale_timing: {used} of the untimed rerun used"
                + (f", {stage}.r<rep>.log ignored" if timed else ""))
    if used == f"{stage}.log" and timed:
        return f"{stage}.r<rep>.log and {used} in the folder: {used} used"
    if not stale:
        return ""
    plain = ", ".join(ctx.untimed_logs(engine, benchmark, unit, db, None, t.expected))
    return f"stale_timing ({plain} in the folder)" + (f": {used} used" if used else "")


def _not_read(name, err, lost):
    """The note '<name> not read: <error>' of a listed file of a search folder that cannot be read (no permission, a
    folder of that name); lost (a list) gets (name, note): every row of the search carries the note, and WARN O19
    counts the file (collect_settings 'unread')."""
    note = f"{name} not read: {T.error_text(err)}"
    lost.append((name, note))
    return note


def _record(ctx, folder, names, item):
    """ctx.record_input for the files of a search folder that a settings row read (provenance.tsv, SPEC 1): only
    those ctx.files read (a file that could not be read is no input)."""
    for name in names:
        path = os.path.join(folder, name) if name else None
        if path and ctx.files.sha256(path) is not None:
            ctx.record_input(path, item)


def counted_searches(ctx, engine):
    """The counted per_file* searches of an engine inside the design, as (benchmark, unit, db), sorted by benchmark
    (per_file, the arms in ARMS order, further tags), unit (table order) and database (the unit's order)."""
    order = {u.name: i for i, u in enumerate(ctx.units)}
    out = []
    for c in ctx.coverage:
        if c.engine != engine or c.scope != "unit" or not c.benchmark.startswith("per_file"):
            continue
        if c.state != "ok" or not c.counted or c.unit is None:
            continue
        stems = c.unit.stems
        out.append((bench_rank(c.benchmark), order.get(c.run, len(order)),
                    stems.index(c.db) if c.db in stems else len(stems), c.db, c.benchmark, c.unit))
    out.sort(key=lambda x: x[:4])
    return [(b, u, db) for _, _, _, db, b, u in out]


def fill_missing(base, columns, note):
    """A settings row of a search whose folder is absent: every value NA."""
    row = OrderedDict(base)
    for c in columns:
        if c not in row:
            row[c] = T.Missing("no_folder")
    row["note"] = note
    return OrderedDict((c, row[c]) for c in columns)


def msf_fixed(configured):
    """True when fragger.params fixes the values (calibrate_mass 0 or 1: no parameter search, the configured values
    are used); False for calibrate_mass 2 (or 4), another value or none, where MSFragger chooses at run time."""
    return to_number((configured or {}).get("calibrate_mass", "")) in (0, 1)


def settings_msfragger_row(ctx, benchmark, unit, db, unread=None):
    """One row of O19_settings_msfragger.tsv (SPEC O19 "MSFragger settings file"). A file of the folder that cannot
    be read gets the note '<file> not read: <error>': the log read gives then no value (source NA), fragger.params no
    configured key. A folder without a search log keeps the configured values only when fragger.params fixes them
    (msf_fixed: calibrate_mass 0 or 1); a calibrated search without a log gets no value (source NA, note 'no search
    log'), as its configured values need not be those MSFragger used. A calibrated search whose log has no 'New' line
    (e.g. a cut log) keeps the configured values with the note 'no New lines'. unread (a list): gets
    '<search>/<file>' for each file that could not be read (WARN O19)."""
    folder = ctx.search_dir("msfragger", benchmark, unit.name, db)
    base = OrderedDict([("engine", "msfragger"), ("benchmark", benchmark), ("unit", unit.name), ("database", db)])
    files = ctx.files
    if not folder or not files.isdir(folder):
        return fill_missing(base, MSF_COLUMNS, "no search folder")
    used, compared = pick_logs(folder, "search", files)
    lost, parsed = [], OrderedDict()  # parsed: the logs of compared that could be read (used = compared[-1])
    for x in compared:
        try:
            parsed[x] = parse_msfragger_log(os.path.join(folder, x), files)
        except OSError as err:
            _not_read(x, err, lost)
    try:
        configured = read_fragger_params(os.path.join(folder, "fragger.params"), files)
    except OSError as err:
        configured = None
        _not_read("fragger.params", err, lost)
    notes = [x for x in [_stale_note(ctx, "msfragger", benchmark, unit.name, db, folder, "search", used)] if x]
    chosen, lack = {}, None  # lack: why the row has no value at all (Missing reason)
    if used is None:
        notes.append("no search log")
        if configured is not None and not msf_fixed(configured):
            lack = "no_log"  # a calibrated search: the configured values need not be those MSFragger used
    elif used in parsed:
        chosen = parsed[used]
        if not chosen and configured is not None and not msf_fixed(configured):
            notes.append("no New lines")  # a calibrated search: the configured values may not be those used
        if any(p != chosen for p in parsed.values()):
            notes.append("varies")
    else:
        lack = "unread"  # the log read could not be read
    notes += [note for _, note in lost]
    if configured is None and "fragger.params" not in [name for name, _ in lost]:
        notes.append("no fragger.params")
    _record(ctx, folder, compared + ["fragger.params"], f"O19 msfragger {benchmark} {unit.name} {db}")
    if lack:
        values = OrderedDict((c, T.Missing(lack)) for c in VALUE_COLUMNS["msfragger"])
        source, more = T.Missing(lack), []
    else:
        values, source, more = msfragger_settings(chosen, configured)
    if unread is not None:
        unread.extend(f"msfragger/{benchmark}/{unit.name}/{db}/{name}" for name, _ in lost)
    row = OrderedDict(base)
    row["log"] = used if used else T.Missing("no_log")
    row["source"] = source
    row.update(values)
    row["note"] = "; ".join(notes + more)
    return OrderedDict((c, row[c]) for c in MSF_COLUMNS)


UNREAD_YAML = "summary.yaml not read"  # the start of prose_configured's note when summary.yaml cannot be read


def prose_configured(folder, files=None):
    """ProSE's configured fragment tolerance from summary.yaml shared.fragment_tol / fragment_tol_unit (SPEC O19, for
    cal_off and inputs without a calibration line): (tol, unit, calibration_enabled, note). summary.yaml holds the
    configured value (logs of builds before P: shared.fragment_tol 20 where the Fragment line reads 'tolerance
    20.00 -> 6.26 ppm')."""
    files = _files(files)
    p = os.path.join(folder, "summary.yaml")
    if not files.exists(p):
        return T.Missing("no_summary"), T.Missing("no_summary"), None, "no summary.yaml"
    try:
        y = T.read_yaml(p, files)
    except (OSError, ValueError, IndexError, KeyError, TypeError) as err:  # the note starts as UNREAD_YAML
        return T.Missing("unparsed"), T.Missing("unparsed"), None, f"{UNREAD_YAML}: {T.error_text(err)}"
    shared = y.get("shared") if isinstance(y, dict) else None
    if not isinstance(shared, dict):
        return T.Missing("missing"), T.Missing("missing"), None, "summary.yaml without shared"
    tol = shared.get("fragment_tol")
    unit = unit_name(shared.get("fragment_tol_unit"))
    return (float(tol) if is_number(tol) else T.Missing("missing"), unit or T.Missing("missing"),
            shared.get("calibration_enabled"), "")


def settings_prose_rows(ctx, benchmark, unit, db, problems=None, unread=None):
    """The rows of O19_settings_prose.tsv of one counted ProSE search, one per input (SPEC O19 "ProSE settings
    file"): the chosen tolerance from the Fragment line, else the configured one (source configured). An input the
    log's Searching lines do not name gets no value (source NA: no settings row for C23), also when they name none of
    the inputs (assign_inputs: by name only). A folder without an all log keeps the configured tolerance only with
    calibration off (summary.yaml calibration_enabled false; without that key, the cal_off arm); with calibration on
    every row gets no value (source NA, note 'no all log'), as ProSE chooses the tolerance at run time. A file of the
    folder that cannot be read gets the note '<file> not read: <error>' on every row: the log read gives then no
    value (source NA), inputs the run table's files, summary.yaml no configured tolerance.
    problems (a list): gets '<key>: <text>' when the inputs file differs from the run table's files (naming the
    files), or the log searched other files than the inputs file names (WARN O19). unread (a list): gets
    '<key>/<file>' for each file that could not be read (WARN O19)."""
    folder = ctx.search_dir("prose", benchmark, unit.name, db)
    files = ctx.files
    exists = bool(folder) and files.isdir(folder)
    key = f"prose/{benchmark}/{unit.name}/{db}"
    lost, listed = [], None
    if exists:
        try:
            listed = read_inputs(folder, files)
        except OSError as err:
            _not_read("inputs", err, lost)
    inputs = listed or list(unit.runs)
    if not exists:
        return [fill_missing(OrderedDict([("engine", "prose"), ("benchmark", benchmark), ("unit", unit.name),
                                          ("input", i), ("database", db)]), PROSE_COLUMNS, "no search folder")
                for i in inputs]
    used, compared = pick_logs(folder, "all", files)
    logs = OrderedDict()  # parse_prose_log of the logs of compared that could be read (used = compared[-1])
    for x in compared:
        try:
            logs[x] = parse_prose_log(os.path.join(folder, x), files)
        except OSError as err:
            _not_read(x, err, lost)
    lost_log = used is not None and used not in logs  # the log read could not be read: no values
    if used in logs:
        searched = logs[used][0]
        by_input, extra = assign_inputs(*logs[used], inputs)
    else:
        by_input, extra, searched = {i: None for i in inputs}, 0, {}
    others = [assign_inputs(*logs[x], inputs)[0] for x in compared[:-1] if x in logs]
    conf_tol, conf_unit, cal_enabled, conf_note = prose_configured(folder, files)
    if conf_note.startswith(UNREAD_YAML):  # a note on every row, not only on those that need the configured value
        lost.append(("summary.yaml", conf_note))
    # ProSE's own record decides; the arm name only when summary.yaml does not say (no file, no such key)
    cal_off = cal_enabled is False if isinstance(cal_enabled, bool) else benchmark == "per_file_cal_off"
    no_log = used is None and not cal_off  # calibration on, no log: the configured tolerance need not be the one used
    _record(ctx, folder, ["inputs"] + compared + ["summary.yaml"], f"O19 prose {benchmark} {unit.name} {db}")
    none_named = bool(searched) and not any(i in searched for i in inputs)
    not_in_inputs = [s for s in searched if s not in inputs]
    if problems is not None:
        if listed is not None and sorted(listed) != sorted(unit.runs):
            only_inputs = [x for x in listed if x not in unit.runs]
            only_table = [x for x in unit.runs if x not in listed]
            problems.append(f"{key}: inputs file {len(listed)} file(s), run table {len(unit.runs)}"
                            + (f" (only in inputs: {', '.join(only_inputs)})" if only_inputs else "")
                            + (f" (only in the run table: {', '.join(only_table)})" if only_table else ""))
        unsearched = [i for i in inputs if searched and by_input.get(i) is None]
        if none_named:
            problems.append(f"{key}: the Searching lines of {used} name none of the {len(inputs)} input(s) "
                            f"(searched: {', '.join(searched)}), no values")
        elif unsearched:
            problems.append(f"{key}: {len(unsearched)} of {len(inputs)} input(s) not searched in {used}")
    if unread is not None:
        unread.extend(f"{key}/{name}" for name, _ in lost)
    stale = _stale_note(ctx, "prose", benchmark, unit.name, db, folder, "all", used)
    rows = []
    for i in inputs:
        sec = by_input.get(i)
        frag = sec["fragment"] if sec else None
        notes = ([] if used else ["no all log"]) + ([stale] if stale else [])
        row = OrderedDict([("engine", "prose"), ("benchmark", benchmark), ("unit", unit.name), ("input", i),
                           ("database", db), ("log", used if used else T.Missing("no_log"))])
        if lost_log or no_log or (searched and sec is None):  # no log text, or no Searching line names this input
            none = T.Missing("unread" if lost_log else "no_log" if no_log else "not_searched")
            row.update([("source", none), ("prose_fragment_offset", none), ("prose_fragment_sigma", none),
                        ("prose_fragment_tol", none), ("prose_fragment_tol_unit", none),
                        ("prose_covered_pct", none)])
            if no_log and conf_note and not conf_note.startswith(UNREAD_YAML):  # e.g. 'no summary.yaml'
                notes.append(conf_note)
            elif not lost_log and not no_log:
                notes.append(f"not searched in {used} (no Searching line names it)")
        elif frag is not None:
            offset, sigma, sigma_unit, _configured, tol, tol_unit, covered = frag
            row.update([("source", "chosen"), ("prose_fragment_offset", offset), ("prose_fragment_sigma", sigma),
                        ("prose_fragment_tol", tol), ("prose_fragment_tol_unit", tol_unit),
                        ("prose_covered_pct", covered)])
            if sigma_unit != tol_unit:
                notes.append(f"sigma in {sigma_unit}")
            if sec.get("kept"):
                notes.append("configured tolerance kept")
        else:
            no_value = T.Missing("configured")
            row.update([("source", "configured" if is_number(conf_tol) else T.Missing("no_settings")),
                        ("prose_fragment_offset", no_value), ("prose_fragment_sigma", no_value),
                        ("prose_fragment_tol", conf_tol), ("prose_fragment_tol_unit", conf_unit),
                        ("prose_covered_pct", no_value)])
            if cal_off:
                notes.append("calibration off")
            elif sec and sec.get("insufficient"):
                notes.append("calibration: insufficient PSMs")
            elif used is not None:
                notes.append("no fragment calibration line")
            if conf_note and not conf_note.startswith(UNREAD_YAML):  # an unread summary.yaml: in lost
                notes.append(conf_note)
        notes += [note for _, note in lost]
        for o in ([] if lost_log else others):
            s2 = o.get(i)
            if (s2["fragment"] if s2 else None) != frag:
                notes.append("varies")
                break
        if extra:
            notes.append(f"{extra} searched file(s) not in inputs" if searched
                         else f"{extra} more Fragment lines than inputs")
        row["note"] = "; ".join(notes)
        rows.append(OrderedDict((c, row[c]) for c in PROSE_COLUMNS))
    if problems is not None and extra and not none_named:
        if searched:
            problems.append(f"{key}: {extra} searched file(s) not in inputs ({', '.join(not_in_inputs)}), not in "
                            f"O19_settings_prose")
        else:
            problems.append(f"{key}: {extra} Fragment line(s) beyond the {len(inputs)} input(s), not in "
                            f"O19_settings_prose")
    return rows


def settings_sage_row(ctx, benchmark, unit, db, unread=None):
    """One row of O19_settings_sage.tsv: the configured fragment tolerance from sage.json (SPEC O19). A sage.json
    that cannot be read or parsed gives NA values and the note 'sage.json not read: <error>'; unread (a list) gets
    '<search>/sage.json' then (WARN O19)."""
    folder = ctx.search_dir("sage", benchmark, unit.name, db)
    base = OrderedDict([("engine", "sage"), ("benchmark", benchmark), ("unit", unit.name), ("database", db)])
    files = ctx.files
    if not folder or not files.isdir(folder):
        return fill_missing(base, SAGE_COLUMNS, "no search folder")
    p = os.path.join(folder, "sage.json")
    row = OrderedDict(base)
    if not files.exists(p):
        row.update([("log", T.Missing("no_log")), ("source", T.Missing("no_settings")),
                    ("fragment_tol", T.Missing("no_log")), ("fragment_tol_unit", T.Missing("no_log")),
                    ("max_fragment_charge", T.Missing("no_log")), ("note", "no sage.json")])
        return row
    try:
        tol, tol_unit, mfc, notes = read_sage_json(p, files)
    except (ValueError, OSError) as err:
        tol = tol_unit = mfc = T.Missing("unparsed")
        notes = [f"sage.json not read: {T.error_text(err)}"]
        if unread is not None:
            unread.append(f"sage/{benchmark}/{unit.name}/{db}/sage.json")
    _record(ctx, folder, ["sage.json"], f"O19 sage {benchmark} {unit.name} {db}")  # read, perhaps not parsed
    row.update([("log", "sage.json"), ("source", "configured" if is_number(tol) else T.Missing("no_settings")),
                ("fragment_tol", tol), ("fragment_tol_unit", tol_unit), ("max_fragment_charge", mfc),
                ("note", "; ".join(notes))])
    return row


def collect_settings(ctx):
    """The O19 settings rows of every counted per_file* search (SPEC O19), parsed from W/out when logs are available
    (ctx.logs_available). Returns {'msfragger': rows, 'prose': rows, 'sage': rows, 'searches': {engine: n counted},
    'missing': {engine: [(benchmark, unit, db)]}, 'prose_inputs': [problem text], 'unread': ['<engine>/<benchmark>/
    <unit>/<db>/<file>' of each file that could not be read]}; a search is missing when its rows do not give it a value
    (search_lacks_value; checks.py's C23 applies the same rule to the tables)."""
    out = {"msfragger": [], "prose": [], "sage": [], "searches": {}, "missing": {}, "prose_inputs": [],
           "unread": []}
    for engine in ("msfragger", "prose", "sage"):
        searches = counted_searches(ctx, engine)
        out["searches"][engine] = len(searches)
        if not ctx.logs_available:
            out["missing"][engine] = [(b, u.name, db) for b, u, db in searches]
            continue
        missing = []
        for b, u, db in searches:
            if engine == "msfragger":
                rows = [settings_msfragger_row(ctx, b, u, db, out["unread"])]
            elif engine == "prose":
                rows = settings_prose_rows(ctx, b, u, db, out["prose_inputs"], out["unread"])
            else:
                rows = [settings_sage_row(ctx, b, u, db, out["unread"])]
            out[engine].extend(rows)
            if search_lacks_value(engine, rows, u.runs if engine == "prose" else 1):
                missing.append((b, u.name, db))
        out["missing"][engine] = missing
    return out


# The rule that INFO O19 and C23 (checks.py) share: the value columns a settings row must fill (parsed or
# configured) to count as a settings row (C23; DS:691): every MSFragger setting; ProSE's tolerance (offset, sigma and
# covered % exist only with a Fragment line); Sage's tolerance (max_fragment_charge NA is Sage's default)
VALUE_COLUMNS = {"msfragger": ("fragment_tol", "fragment_tol_unit", "use_topN_peaks", "minimum_ratio",
                               "intensity_transform", "remove_precursor_peak", "max_fragment_charge"),
                 "prose": ("prose_fragment_tol", "prose_fragment_tol_unit"),
                 "sage": ("fragment_tol", "fragment_tol_unit")}


def no_value(value):
    """A settings cell without a value: NA (Missing, None, NaN), or the empty text or '-' (e.g. the fragger.params
    line 'use_topN_peaks =')."""
    return T.is_missing(value) or str(value).strip() in ("", "-")


def na_columns(engine, row):
    """['source'] when a settings row has no source, else its VALUE_COLUMNS without a value (no_value)."""
    if no_value(row["source"]):
        return ["source"]
    return [c for c in VALUE_COLUMNS[engine] if no_value(row[c])]


def lacks_value(engine, row):
    """True when a settings row has no source or a value column without a value (na_columns)."""
    return bool(na_columns(engine, row))


def inputs_without_value(rows, runs):
    """The files of runs (a ProSE search's run table files, unit.runs) without a settings row of that input that has
    every value."""
    have = {r["input"] for r in rows if not lacks_value("prose", r)}
    return [x for x in runs if x not in have]


def search_lacks_value(engine, rows, need):
    """True when the settings rows of one search do not give it a value (INFO O19 and C23): a row without one, or
    for a number need (1: MSFragger, Sage) fewer rows, or for a sequence need (ProSE: the run table's files of the
    unit, unit.runs; OPEN Q28) a file without a row of its name (input) with every value (inputs_without_value)."""
    if any(lacks_value(engine, r) for r in rows):
        return True
    if isinstance(need, int):
        return len(rows) < need
    return bool(inputs_without_value(rows, need))


MSF_NOTE = ("one row per counted MSFragger per_file* search (DS:691); log: search.r3.log for the timed td search "
            "(B:911-922), else search.log (an untimed rerun's search.log wins in a stale_timing folder, note "
            "'stale_timing: ...'); values from the 'New <key> = <value>' lines of the MASS CALIBRATION AND PARAMETER "
            "OPTIMIZATION block; source chosen = every key from a New line, configured = fragger.params only "
            "(calibrate_mass 0 or 1; a calibrated log without a New line has the note 'no New lines'), mixed = not "
            "every key from a New line: the keys from fragger.params named in the note 'configured: <keys>', those "
            "in neither in 'missing: <keys>' (P logs: max_fragment_charge has a New line only on the ion-trap "
            "searches); source NA with note 'no search log' = a search without a log whose fragger.params does not "
            "fix the values (calibrate_mass not 0 or 1), so MSFragger chooses them at run time; note 'varies' = "
            "r1-r3 differ (r3 shown, OPEN Q29); 'configured tolerance <x> <unit>' = the configured tolerance where "
            "MSFragger chose another unit. The README (Settings tables) lists every note")
PROSE_NOTE = ("one row per input of every counted ProSE per_file* search (OPEN Q28); log: all.r3.log for the timed td "
              "search, else all.log (an untimed rerun's all.log wins in a stale_timing folder, note 'stale_timing: "
              "...'); the line '[ProSE] Fragment: offset o, sigma s (...) -> tolerance <configured> -> <chosen> "
              "(covers c % ...)' of the input's '[i/n] Searching' block, printed with 2 decimals (covered % as an "
              "integer); prose_covered_pct = 'covers c % of the peaks' as printed; note 'configured tolerance kept' = "
              "the |offset| + 4 sigma candidate covered too few peaks ('covers only N %'), so the configured "
              "tolerance is reported while covered % is still the candidate's; source configured = summary.yaml "
              "shared.fragment_tol (calibration off, insufficient PSMs, no Fragment line), printed exactly when it "
              "has more than 2 decimals; source NA with 'not searched in <log>' = no Searching line names the input; "
              "source NA with 'no all log' = a search without a log and with calibration on (summary.yaml "
              "calibration_enabled, else the arm), whose tolerance ProSE chooses at run time, or without a readable "
              "summary.yaml tolerance; 'varies' = r1-r3 differ for this input (OPEN Q29). The README (Settings "
              "tables) lists every note")
SAGE_NOTE = ("one row per counted Sage per_file* search (failed searches have none); the configured fragment_tol "
             "of sage.json, {\"ppm\"|\"da\": [-x, x]} (B:574), as x; max_fragment_charge NA = not set in sage.json, "
             "i.e. Sage's default; the driver sets it where ProSE scores several fragment charges (B:581-588)")


def write_settings(ctx, settings):
    """The three settings tables (SPEC O19). Without W/out logs they are written with their header only and an INFO
    line (SPEC 4: the trial copies have no out/)."""
    note = None if ctx.logs_available else ("not built: no W/out logs (engine logs, fragger.params, summary.yaml, "
                                            "sage.json; SPEC 4)")
    ctx.write_table("O19_settings_msfragger", MSF_COLUMNS, settings["msfragger"], header_note=note or MSF_NOTE)
    # the Fragment line prints offset, sigma and tolerances with 2 decimals and covers as an integer; a configured
    # tolerance from summary.yaml is printed exactly when it has more than 2 decimals (e.g. 0.025 Da)
    two = T.fmt_min_decimals(2)
    ctx.write_table("O19_settings_prose", PROSE_COLUMNS, settings["prose"],
                    formats={"prose_fragment_offset": two, "prose_fragment_sigma": two, "prose_fragment_tol": two,
                             "prose_covered_pct": ".0f"}, header_note=note or PROSE_NOTE)
    ctx.write_table("O19_settings_sage", SAGE_COLUMNS, settings["sage"], header_note=note or SAGE_NOTE)
    n = settings["searches"]
    if not ctx.logs_available:
        ctx.check("INFO", "O19", f"settings tables empty: no W/out logs ({n['msfragger']} MSFragger, {n['prose']} "
                                 f"ProSE, {n['sage']} Sage counted per_file* searches)")
        return
    varies = {e: sum(1 for r in settings[e] if "varies" in str(r["note"])) for e in ("msfragger", "prose")}
    miss = {e: len(settings["missing"][e]) for e in ("msfragger", "prose", "sage")}
    ctx.check("INFO", "O19", f"settings rows: {len(settings['msfragger'])} MSFragger ({n['msfragger']} searches, "
                             f"{miss['msfragger']} without a value), {len(settings['prose'])} ProSE inputs "
                             f"({n['prose']} searches, {miss['prose']} without a value), {len(settings['sage'])} "
                             f"Sage ({miss['sage']} without a value); r1-r3 differ: {varies['msfragger']} MSFragger, "
                             f"{varies['prose']} ProSE (note=varies, OPEN Q29)")
    problems = settings.get("prose_inputs") or []
    if problems:
        ctx.check("WARN", "O19", f"{len(problems)} ProSE input problem(s) (inputs file, run table and the log's "
                                 f"Searching lines disagree): {T.list_text(problems, sep='; ')}")
    unread = settings.get("unread") or []
    if unread:
        ctx.check("WARN", "O19", f"{len(unread)} file(s) of counted searches not read (every row of the search notes "
                                 f"'<file> not read: <error>', and a value that needs the file is NA): "
                                 f"{T.list_text(unread)}")


# ================================================================ comparisons with seed means (O20) and arms (O21)
def side_count(ctx, side, unit, level):
    """The td count of one side (SPEC O20, O21): (value, n counted, problem). value: the count of a single benchmark,
    or the fsum mean over the counted benchmarks (seeds); problem: None when every benchmark is counted with
    accepted > 0, else '<label>:<reason>' (with the benchmark for seeds) or '<label>:zero'."""
    vals = [ctx.accepted(side.engine, unit, level, benchmark=b) for b in side.benchmarks]
    got = [v for v in vals if not isinstance(v, T.Missing)]
    problem = None
    for b, v in zip(side.benchmarks, vals):
        if isinstance(v, T.Missing):
            problem = f"{side.label}:{v.reason}" + (f" ({b})" if len(side.benchmarks) > 1 else "")
            break
    if problem is None and any(v == 0 for v in got):
        problem = f"{side.label}:zero"
    if len(side.benchmarks) == 1:
        value = vals[0]
    elif got:
        value = T.fmean(got)
    else:
        value = vals[0]
    return value, len(got), problem


def side_fdp(ctx, side, unit, level, stem):
    """FDP of one side on one entrapment database: O11's value of each search (fdp.search_fdp: combined_fdp,
    Missing('none_accepted') when N = 0), the mean over the seeds for several benchmarks (SPEC O20 "FDP as in O11 on
    the seed means"); Missing if any is missing."""
    vals = [fdp.search_fdp(ctx, side.engine, b, unit, stem, level) for b in side.benchmarks]
    for v in vals:
        if not is_number(v):
            return v if isinstance(v, T.Missing) else T.Missing("NA")
    return vals[0] if len(vals) == 1 else T.fmean(vals)


def compare_run(ctx, num, den, unit, level):
    """One run of a comparison: both values, the ratio (when both sides are counted with every count > 0; decision
    runs keep it, as in the per-run tables, DS:858), used (in the set: also role != decision), reason, and the FDP of
    both sides as the mean over the shuffled realisations both have (SPEC 2.7 F, O11)."""
    pv, pn, pp = side_count(ctx, num, unit, level)
    cv, cn, cp = side_count(ctx, den, unit, level)
    problem = pp or cp
    ratio = T.Missing(problem) if problem else pv / cv
    reason = "decision" if unit.is_decision else problem
    pf, cf = [], []
    for s in unit.stems_of("shuffled"):
        a = side_fdp(ctx, num, unit, level, s)
        b = side_fdp(ctx, den, unit, level, s)
        if is_number(a) and is_number(b):
            pf.append(a)
            cf.append(b)
    return {"num": pv, "num_n": pn, "den": cv, "den_n": cn, "ratio": ratio, "used": reason is None,
            "reason": reason or "", "fdp_num": mean_over(pf), "fdp_den": mean_over(cf), "fdp_n": len(pf)}


def groups_in_order(units):
    """The groups of the units in design order (design.order_key)."""
    out = []
    for u in units:
        if u.group not in out:
            out.append(u.group)
    return sorted(out, key=design.order_key)


def dataset_values(group, results, with_sums):
    """Per dataset (SPEC O2 step 2): over the non-decision units of the group, n_units, n_used, G_d = gmean of the
    used run ratios, Sigma_d = fsum(P)/fsum(C) over the same runs, and the FDP means of the run means over the
    non-decision runs with a shared realisation (OPEN Q13)."""
    us = [(u, r) for u, r in results if u.group == group]
    nd = [(u, r) for u, r in us if not u.is_decision]
    used = [(u, r) for u, r in nd if r["used"]]
    g = T.gmean([r["ratio"] for _, r in used])
    out = OrderedDict([("n_units", len(nd)), ("n_used", len(used)), ("gmean", g), ("lead_pct", T.lead(g))])
    if with_sums:
        s = T.sum_ratio([r["num"] for _, r in used], [r["den"] for _, r in used])
        out["sum_ratio"] = s
        out["sum_lead_pct"] = T.lead(s)
    fdp_runs = [r for _, r in nd if r["fdp_n"] > 0]
    out["fdp_num_mean"] = mean_over([r["fdp_num"] for r in fdp_runs])
    out["fdp_den_mean"] = mean_over([r["fdp_den"] for r in fdp_runs])
    out["fdp_n_runs"] = len(fdp_runs)
    if us and not nd:
        note = "decision only"
    elif not used:
        note = "dropped: no run in the set"
    elif len(used) < len(nd):
        note = "runs out of the set: " + ", ".join(f"{u.name} ({r['reason']})" for u, r in nd if not r["used"])
    else:
        note = ""
    out["note"] = note
    return out


def scope_values(datasets, results):
    """Per scope (SPEC O2 step 3): E = gmean of G_d over the datasets with n_used >= 1 (equal weight), W = gmean of
    every used run ratio (OPEN Q3), Sigma = fsum(P)/fsum(C) over the used runs (OPEN Q2); Missing('empty') without a
    dataset; the datasets without a used run are listed as dropped (DS:897)."""
    kept = [(g, d) for g, d in datasets if d["n_used"] >= 1]
    used = [r for _, r in results if r["used"]]
    e = T.gmean([d["gmean"] for _, d in kept]) if kept else T.Missing("empty")
    w = T.gmean([r["ratio"] for r in used]) if kept else T.Missing("empty")
    s = T.sum_ratio([r["num"] for r in used], [r["den"] for r in used]) if kept else T.Missing("empty")
    dropped = [g for g, d in datasets if d["n_used"] == 0]
    return OrderedDict([("n_datasets", len(kept)), ("n_runs", len(used)), ("equal_weight", e),
                        ("lead_pct", T.lead(e)), ("run_weighted", w), ("rw_lead_pct", T.lead(w)), ("sum_ratio", s),
                        ("sum_lead_pct", T.lead(s)), ("dropped_datasets", ", ".join(dropped) or "-")])


def rows_of(ctx, benchmarks):
    """The runs (unit names) with coverage or counts rows of the given benchmarks."""
    out = {c.run for c in ctx.coverage if c.benchmark in benchmarks}
    out |= {r.run for r in ctx.counts if r.benchmark in benchmarks}
    return out


# ================================================================ O20 external Percolator (SPEC O20; OPEN Q37)
def build_percolator(ctx):
    """O20 (SPEC O20; DS:79, 613-615, 918, 930, 991): counts of per_file_percolator_s{1,42,137} for all three engines;
    per (engine, unit, td, level) the mean over the 3 seeds with n_seeds; a unit enters a pair only with all 3 seeds
    counted (> 0) for both engines; then O2's formulas and sets per run, dataset and scope (heldout, tuning); FDP as
    O11 on the seed means. Units: the tryptic per_file units (OPEN Q37) and any other unit with seed rows.
    Not built without seed rows (SPEC 4: the runs do not exist yet)."""
    with_rows = rows_of(ctx, PERCOLATOR_BENCHMARKS)
    if not with_rows:
        ctx.check("INFO", "O20", "not built: no per_file_percolator_s{1,42,137} rows in counts.tsv or coverage.tsv "
                                 "(SPEC 4)")
        return
    units = [u for u in ctx.units if u.kind in ("tuning", "heldout") or u.name in with_rows]
    run_rows, ds_rows, sum_rows = [], [], []
    ref = "DS:613-615, 991"
    for p, c in design.PAIRS:
        num, den = Side(p, PERCOLATOR_BENCHMARKS, p), Side(c, PERCOLATOR_BENCHMARKS, c)
        pair, pair_units = f"{p}/{c}", [u for u in units if p in u.expected and c in u.expected]
        for level in ctx.levels:
            results = [(u, compare_run(ctx, num, den, u, level)) for u in pair_units]
            for u, r in results:
                run_rows.append(OrderedDict([
                    ("pair", pair), ("level", level), ("kind", u.kind), ("class", u.cls), ("grade", u.grade),
                    ("group", u.group), ("unit", u.name), ("role", u.role), ("prose_n_seeds", r["num_n"]),
                    ("prose", r["num"]), ("comparator_n_seeds", r["den_n"]), ("comparator", r["den"]),
                    ("ratio", r["ratio"]), ("used", r["used"]), ("reason", r["reason"]),
                    ("fdp_prose", r["fdp_num"]), ("fdp_comparator", r["fdp_den"]), ("fdp_n_shared", r["fdp_n"])]))
            datasets = []
            for g in groups_in_order([u for u, _ in results]):
                d = dataset_values(g, results, with_sums=True)
                datasets.append((g, d))
                ds_rows.append(OrderedDict([
                    ("pair", pair), ("level", level), ("kind", design.kind(g)), ("side", design.side(g) or "-"),
                    ("class", design.cls(g)), ("grade", design.grade(g)), ("group", g), ("n_units", d["n_units"]),
                    ("n_used", d["n_used"]), ("gmean", d["gmean"]), ("lead_pct", d["lead_pct"]),
                    ("sum_ratio", d["sum_ratio"]), ("sum_lead_pct", d["sum_lead_pct"]),
                    ("fdp_prose_mean", d["fdp_num_mean"]), ("fdp_comparator_mean", d["fdp_den_mean"]),
                    ("fdp_n_runs", d["fdp_n_runs"]), ("note", d["note"])]))
            for scope in ("heldout", "tuning"):
                s = scope_values([(g, d) for g, d in datasets if design.kind(g) == scope],
                                 [(u, r) for u, r in results if u.kind == scope])
                sum_rows.append(OrderedDict([("pair", pair), ("level", level), ("scope", scope)] + list(s.items())))
                key = f"percolator.{scope}.{level}.{c}"
                for name, col in (("lead", "lead_pct"), ("rw_lead", "rw_lead_pct"), ("sum_lead", "sum_lead_pct")):
                    ctx.number(f"{key}.{name}", s[col], text=T.fmt(s[col], T.FMT_LEAD), unit="%", output="O20",
                               protocol_ref=ref, source_side=scope)
                ctx.number(f"{key}.n_datasets", s["n_datasets"], unit="datasets", output="O20", protocol_ref=ref,
                           source_side=scope)
                ctx.number(f"{key}.n_runs", s["n_runs"], unit="runs", output="O20", protocol_ref=ref,
                           source_side=scope)
    ctx.write_table("O20_external_percolator", O20_RUN_COLUMNS, run_rows,
                    formats={"prose": FMT_COUNT_MEAN, "comparator": FMT_COUNT_MEAN},
                    header_note="O20 external Percolator (SPEC 3.4): td counts are means over the seeds 1, 42, 137 "
                                "(DS:613); a run is used only with all 3 seeds counted (> 0) for both engines; FDP "
                                "= mean over the shared realisations of the seed-mean combined FDP (fraction)")
    ctx.write_table("O20_external_percolator_datasets", O20_DATASET_COLUMNS, ds_rows)
    ctx.write_table("O20_external_percolator_summary", O20_SUMMARY_COLUMNS, sum_rows)
    ctx.check("INFO", "O20", f"built: {len(units)} units, {len(run_rows)} run rows, {len(ds_rows)} dataset rows")


# ================================================================ O21 prediction supplement (SPEC O21; OPEN Q38, Q57)
def read_instruments(ctx):
    """The PeptDeep instrument setting per unit (DS:751) from the ProSE command lines in W/commands.log (bench.py
    logs every command, B:252): a ProSE line whose -summary_out lies in out/prose/per_file_peptdeep/<unit>/<db>/.
    The value of '-Search:peptdeep:instrument <X>' (DS:750-751), else the parameter file's Search:peptdeep:instrument
    (PI ini:97; the -ini file of the line, or <params_dir>/<unit params>.ini). The last line per (unit, db) is kept (a
    rerun appends, B:199-203). Returns ({unit: [(value or None, source)]}, path); ({}, None) without commands.log."""
    path = os.path.join(ctx.work, "commands.log") if ctx.work else None
    if not path or not os.path.exists(path):
        return {}, None
    opt = "-Search:peptdeep:instrument"
    last = OrderedDict()
    for line in read_lines(path):
        if "ProSE" not in line or "per_file_peptdeep" not in line or line.startswith("#"):
            continue
        try:
            tok = shlex.split(line)
        except ValueError:
            continue
        if "-summary_out" not in tok or tok.index("-summary_out") + 1 >= len(tok):
            continue
        parts = tok[tok.index("-summary_out") + 1].replace("\\", "/").split("/")
        if len(parts) < 6 or parts[-1] != "summary.yaml" or parts[-5] != "prose" or parts[-4] != "per_file_peptdeep":
            continue
        value = tok[tok.index(opt) + 1] if opt in tok and tok.index(opt) + 1 < len(tok) else None
        ini = tok[tok.index("-ini") + 1] if "-ini" in tok and tok.index("-ini") + 1 < len(tok) else None
        last[(parts[-3], parts[-2])] = (value, ini)
    out = OrderedDict()
    for (unit, _db), (value, ini) in last.items():
        if value is not None:
            out.setdefault(unit, []).append((value, "command line"))
            continue
        u = ctx.unit_by_name.get(unit)
        candidates = ([ini] if ini else []) + ([os.path.join(ctx.options.params_dir, u.params + ".ini")] if u else [])
        found = None
        for p in candidates:
            if os.path.exists(p):
                try:
                    found = design.ini_value(p, "Search:peptdeep:instrument")
                except Exception:  # an unreadable parameter file: the instrument stays NA
                    found = None
                if found is not None:
                    break
        out.setdefault(unit, []).append((found, "parameter file"))
    return out, path


def msbooster_version(ctx):
    """MSBooster's version text from versions.txt (DS:752; B:357), or None: the driver's versions stage does not
    cover MSBooster now (B:347-349)."""
    for cmd, text in (ctx.versions or []):
        if "msbooster" in (cmd + " " + text).lower():
            return text or cmd
    return None


def unit_instrument(instruments, unit):
    """(instrument text or Missing, note) of one unit from read_instruments()."""
    vals = instruments.get(unit.name)
    if not vals:
        return T.Missing("no_command_line"), ""
    texts = sorted({v for v, _ in vals if v is not None})
    if not texts:
        return T.Missing("not_found"), "instrument not found in the parameter file"
    sources = sorted({s for v, s in vals if v is not None})
    note = "instrument from the parameter file" if sources == ["parameter file"] else ""
    if len(texts) > 1:
        note = (note + "; " if note else "") + "instrument varies across databases"
    return "|".join(texts), note


def build_prediction(ctx, pred_groups):
    """O21 (SPEC O21; DS:747-754, 934, 1066): per_file_peptdeep (prose) and per_file_msbooster (msfragger) on td and,
    if searched, s1-s3 (OPEN Q57). Per run and comparison: the counts, the ratio (O2's rule: both counted, > 0), FDP
    as O11 over the shuffled realisations both sides have; per dataset the gmean; overall the equal weight over the
    pred_groups datasets with a used run (design.PRED_GROUPS, OPEN Q38), decision runs excluded. The instrument per
    dataset from commands.log (DS:751); the MSBooster version from versions.txt, else NA with a WARN (DS:752).
    Not built without prediction rows (SPEC 4)."""
    with_rows = rows_of(ctx, PRED_BENCHMARKS)
    if not with_rows:
        ctx.check("INFO", "O21", "not built: no per_file_peptdeep / per_file_msbooster rows in counts.tsv or "
                                 "coverage.tsv (SPEC 4)")
        return
    units = [u for u in ctx.units if u.group in pred_groups or u.name in with_rows]
    instruments, log_path = read_instruments(ctx)
    if log_path is None:
        ctx.check("WARN", "O21", "no commands.log in W: the PeptDeep instrument setting per dataset is NA (DS:751)")
    version = msbooster_version(ctx)
    if version is None:
        ctx.check("WARN", "O21", "MSBooster version not in versions.txt (the versions stage does not cover it, "
                                 "B:347-349): NA (DS:752)")
    inst = {u.name: unit_instrument(instruments, u) for u in units}
    run_rows, ds_rows, sum_rows = [], [], []
    ref = "DS:747-754"
    for name, num, den in PRED_COMPARISONS:
        cmp_units = [u for u in units if num.engine in u.expected and den.engine in u.expected]
        for level in ctx.levels:
            results = [(u, compare_run(ctx, num, den, u, level)) for u in cmp_units]
            for u, r in results:
                run_rows.append(OrderedDict([
                    ("comparison", name), ("level", level), ("kind", u.kind), ("class", u.cls), ("grade", u.grade),
                    ("group", u.group), ("unit", u.name), ("role", u.role), ("instrument", inst[u.name][0]),
                    ("numerator", r["num"]), ("denominator", r["den"]), ("ratio", r["ratio"]), ("used", r["used"]),
                    ("reason", r["reason"]), ("fdp_numerator", r["fdp_num"]), ("fdp_denominator", r["fdp_den"]),
                    ("fdp_n_shared", r["fdp_n"])]))
            datasets = []
            for g in groups_in_order([u for u, _ in results]):
                d = dataset_values(g, results, with_sums=False)
                datasets.append((g, d))
                gi = [inst[u.name] for u, _ in results if u.group == g]
                texts = sorted({t for t, _ in gi if not T.is_missing(t)})
                note = "; ".join([x for x in [d["note"]] + sorted({n for _, n in gi if n}) if x])
                ds_rows.append(OrderedDict([
                    ("comparison", name), ("level", level), ("kind", design.kind(g)),
                    ("side", design.side(g) or "-"), ("class", design.cls(g)), ("grade", design.grade(g)),
                    ("group", g), ("instrument", "|".join(texts) if texts else T.Missing("no_command_line")),
                    ("n_units", d["n_units"]), ("n_used", d["n_used"]), ("gmean", d["gmean"]),
                    ("lead_pct", d["lead_pct"]), ("fdp_numerator_mean", d["fdp_num_mean"]),
                    ("fdp_denominator_mean", d["fdp_den_mean"]), ("fdp_n_runs", d["fdp_n_runs"]), ("note", note)]))
            # overall: equal weight over the pred_groups datasets with a used run (OPEN Q38), decision runs excluded
            kept = [(g, d) for g, d in datasets if g in pred_groups and d["n_used"] >= 1]
            kept_groups = {g for g, _ in kept}
            e = T.gmean([d["gmean"] for _, d in kept]) if kept else T.Missing("empty")
            n_runs = sum(d["n_used"] for _, d in kept)
            dropped = [g for g in pred_groups if g not in kept_groups]
            sum_rows.append(OrderedDict([
                ("comparison", name), ("level", level), ("scope", "pred_groups"), ("n_datasets", len(kept)),
                ("n_runs", n_runs), ("equal_weight", e), ("lead_pct", T.lead(e)),
                ("dropped_datasets", ", ".join(dropped) or "-"),
                ("msbooster_version", version if version is not None else T.Missing("not_recorded"))]))
            side = source_side([u for u, r in results if r["used"] and u.group in kept_groups])
            key = f"prediction.{level}.{name}"
            ld = T.lead(e)
            ctx.number(f"{key}.lead", ld, text=T.fmt(ld, T.FMT_LEAD), unit="%", output="O21", protocol_ref=ref,
                       source_side=side)
            ctx.number(f"{key}.n_datasets", len(kept), unit="datasets", output="O21", protocol_ref=ref,
                       source_side=side)
            ctx.number(f"{key}.n_runs", n_runs, unit="runs", output="O21", protocol_ref=ref, source_side=side)
    ctx.write_table("O21_prediction", O21_RUN_COLUMNS, run_rows,
                    header_note="O21 prediction supplement (SPEC 3.4): td counts at q <= 0.01; ratio = numerator/"
                                "denominator when both are counted (> 0); FDP = mean combined entrapment FDP "
                                "(fraction) over the shuffled realisations both sides counted with N > 0")
    ctx.write_table("O21_prediction_datasets", O21_DATASET_COLUMNS, ds_rows)
    ctx.write_table("O21_prediction_summary", O21_SUMMARY_COLUMNS, sum_rows)
    ctx.check("INFO", "O21", f"built: {len(units)} units, {len(run_rows)} run rows, {len(ds_rows)} dataset rows")
