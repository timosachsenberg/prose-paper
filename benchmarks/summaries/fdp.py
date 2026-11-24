"""Entrapment FDP: outputs O11, O12, O13 and O26 (SPEC v2 section 3.2), and "FDP as O11" for the other modules.

Citation keys as in the SPEC: DS = datasets/DATASETS.md, B = benchmarks/bench.py, EE-lib = EntrapmentEvaluation.cpp
and EE-tool = EntrapmentEvaluator.cpp at P.

Estimator (SPEC O11; DS:616-620; EE-lib:30-34, 90-93)
  The combined entrapment FDP N_E / N * (1 + T/E) of one entrapment search at q <= 0.01 (B:1311), i.e. the
  combined_fdp column of counts.tsv. EE prints 0 when nothing is accepted (EE-lib:32); the package carries that as
  Missing('none_accepted') in every mean, SD and maximum, and the raw 0 only in O11_fdp_results (SPEC 2.6, T10).
  Shuffled designs have three realisations s1-s3, each searched separately; reported is the mean +- sample SD (n-1)
  over them (DS:620, 931; OPEN Q14). Natural and Arabidopsis designs have one database: the single value, no SD
  (DS:620; OPEN Q15-Q17).

Shared-run rule (SPEC 2.7 F; DS:621-623): the shared realisations of a unit are those that every engine of E(u)
  counted with accepted > 0. The run's shared value is the mean over them; a unit is in F (the set of every summary)
  when it is not a decision unit and has at least one. Own values (over the engine's own counted realisations) appear
  only in the per-run tables, in the columns labelled _own, never in numbers.tsv (OPEN Q62). Decision runs get their
  per-run values with note 'decision' and are in no summary (DS:96, 858, 998; OPEN Q9).

Outputs
  O11  tables/O11_fdp_results.tsv, O11_fdp_runs.tsv, O11_fdp_datasets.tsv; keys fdp.<level>.<engine>.*   --only fdp
  O12  tables/O12_fdp_arath.tsv                                                                         --only fdp
  O13  tables/O13_matched_fdp.tsv and O13_matched_fdp_searches.tsv, only if W/counts_qgrid.tsv exists
       (qgrid.py, the raw stage, is not written yet); keys fdp.matched.*                                --only matched
  O26  tables/O26_pairings.tsv                                                                          --only pairing

Formats (SPEC 3 "Formatting"): FDP values are fractions as in counts.tsv. The columns copied from counts.tsv
  (lower_bound_fdp, combined_fdp, paired_fdp, te_ratio) are written with '.10g', i.e. exactly as EE printed them
  (4 significant digits, EE-tool:188-194); computed FDP values (means, SDs, minima, maxima, combined_recomputed) with
  6 decimals like ratios; difference_pp (O12) in percentage points with 2 decimals; numbers.tsv FDP keys in % (value
  full precision, text 2 decimals).

Reusable API for the other modules (from summaries import fdp)
  fdp.fdp_as_o11(ctx, engine, benchmark, unit, level, design_name=None, shared_with=None, stems=None) -> FdpRun
      FDP as O11 of one (engine, benchmark, unit, level) and one design ('shuffled' | 'natural' | 'arath'; default the
      unit's main design, main_design()). shared_with: the (engine, benchmark) pairs whose counted searches (accepted
      > 0) define the shared realisations; default every engine of E(u) on the same benchmark (the F rule). stems:
      restrict the designed databases (e.g. O19: the realisations counted in both an arm and the main arm).
  fdp.search_fdp(ctx, engine, benchmark, unit, db, level) -> float | Missing      combined FDP of one search
  fdp.main_design(unit), fdp.designs_of(unit), fdp.shared_stems(ctx, unit, level, design_name, shared_with, ...)
  fdp.c8_tolerance(combined, te_ratio, ne_over_n), fdp.c8_combined_ok(row), fdp.c8_lower_ok(row)   (C8, T29)
  fdp.match_grid(points, target=0.01) -> Match                                                          (O13, T32)
  ctx.shared['fdp_runs'] {(engine, benchmark, unit name, level, design): FdpRun} caches the runs of this build.
"""
import math
import os
from collections import OrderedDict, namedtuple
from dataclasses import dataclass

from . import design
from . import tables as T

ENGINES = design.ENGINES
LEVELS = design.LEVELS
DESIGNS = ("shuffled", "natural", "arath")  # SPEC 2.1 "Database design" (td is not an entrapment search)
TARGET = 0.01  # q <= 0.01 (B:1311); the 1% line of fig_fdp; O13 matches the combined FDP to 1.0% (OPEN Q19)
MATCH_EPS = 1e-12  # float noise of N_E/N*(1+T/E) at exactly 1% (O13)
NOT_RAN = ("not_run", "not_run_by_design")  # "an engine that did not run the search gets no row" (SPEC O11)
FMT_RAW = ".10g"  # the counts.tsv FDP columns exactly as EE printed them (4 significant digits, EE-tool:188-194)
RAW_FORMATS = {"te_ratio": FMT_RAW, "lower_bound_fdp": FMT_RAW, "combined_fdp": FMT_RAW, "paired_fdp": FMT_RAW}

# O26 pairings (DS:159, 271, 312; OPEN Q58): (name, test group, its design, counterpart group, its design)
PAIRINGS = (
    ("set_S1", "astral_s1", "natural", "astral", "shuffled"),  # natural entrapment on Astral, DS:159
    ("set_S2", "ultra2_s2", "natural", "ultra2_hye", "shuffled"),  # natural entrapment on timsTOF, DS:312
    ("astral_250pg", "astral_250pg", "shuffled", "astral", "shuffled"),  # 250 pg next to 50 ng, DS:271
)
# DS:271: the 250 pg files are "the three counterparts of astral_A2, astral_B1 and astral_B3":
# (pairing, group of the run) -> (prefix of the run, prefix of its counterpart, group of the counterpart)
COUNTERPART = {("astral_250pg", "astral_250pg"): ("astral250pg_", "astral_", "astral"),
               ("astral_250pg", "astral"): ("astral_", "astral250pg_", "astral_250pg")}

O11_RESULTS_COLUMNS = ("engine kind class grade group unit role database design realisation level "
                       "n_accepted_entrap_search n_entrapment_hits te_ratio lower_bound_fdp combined_fdp "
                       "combined_recomputed paired_fdp status note").split()
O11_RUNS_COLUMNS = ("engine kind class grade group unit role level design n_own mean_own sd_own min_own max_own "
                    "n_shared mean_shared sd_shared natural arath note").split()
O11_DATASETS_COLUMNS = ("engine kind class grade group level design n_units n_runs mean_of_run_means max_run_mean "
                        "n_runs_mean_above_1pct note").split()
O12_COLUMNS = ("engine class grade group unit level arath shuffled_mean_shared shuffled_sd_shared shuffled_n_shared "
               "difference_pp in_shared_set").split()
O13_COLUMNS = ("pair level kind class grade group unit role design n_realisations n_entrap_prose_matched "
               "n_entrap_comparator_matched ratio_matched n_entrap_prose_q01 n_entrap_comparator_q01 ratio_q01 "
               "ratio_plain monotone_ok note").split()
O13_SEARCH_COLUMNS = ("engine kind class grade group unit role database design realisation level n_grid q_match "
                      "fdp_at_match n_entrap_at_match monotone_ok n_entrap_q01 fdp_q01 status note").split()
O26_COLUMNS = ("pairing engine level kind class grade group unit role counterpart design accepted_td n_own mean_own "
               "sd_own n_shared mean_shared sd_shared note").split()


# ---------------------------------------------------------------- the per-run FDP of O11 (reusable)
@dataclass
class FdpRun:
    """FDP as O11 of one (engine, benchmark, unit, level, design) (SPEC O11 "Per run").

    values: {stem: combined FDP (float) or Missing(reason)} for every designed database of the design, in unit order;
    statuses: {stem: coverage status text}; own: the stems with a value; shared: the stems every (engine, benchmark)
    of shared_with counted with accepted > 0. For the single-database designs (natural, arath) value is the engine's
    own value (DS:620); for shuffled it is Missing('not_single'). ran: the engine ran a search of the design.
    run_mean is the run's value in every summary: mean_shared, Missing('decision') for a decision unit."""
    engine: str
    benchmark: str
    unit: object
    level: str
    design: str
    stems: tuple
    values: dict
    statuses: dict
    own: tuple
    n_own: int
    mean_own: object
    sd_own: object
    min_own: object
    max_own: object
    shared: tuple
    n_shared: int
    mean_shared: object
    sd_shared: object
    value: object
    ran: bool
    note: str

    @property
    def in_f(self):
        """In F for this design: not a decision unit and at least one shared realisation (SPEC 2.7)."""
        return not self.unit.is_decision and self.n_shared > 0

    @property
    def run_mean(self):
        if self.unit.is_decision:
            return T.Missing("decision")
        return self.mean_shared


def designs_of(unit):
    """The entrapment designs of a unit, in the order shuffled, natural, arath (SPEC 2.1)."""
    return tuple(d for d in DESIGNS if unit.stems_of(d))


def main_design(unit):
    """The design of a unit's main FDP value: natural where the unit has a natural database (velos: natural is the
    main value and s1-s3 the check, DS:393-394; ups1_control DS:288; astral_s1 and ultra2_s2 DS:160, 313), else
    shuffled; None for a unit without entrapment (immunopeptidomics, DS:631)."""
    if unit.stems_of("natural"):
        return "natural"
    if unit.stems_of("shuffled"):
        return "shuffled"
    return None


def label(unit, stem):
    """Short name of a database in notes: 's1'-'s3' for a shuffled realisation, else the design name."""
    d = unit.design_of(stem)
    if d is None:
        return stem
    if d[0] == "shuffled" and d[1] is not None:
        return f"s{d[1]}"
    return d[0]


def search_fdp(ctx, engine, benchmark, unit, db, level):
    """combined_fdp of one entrapment search (EE-lib:30-34), Missing('none_accepted') when N = 0 (EE prints 0,
    EE-lib:32; SPEC 2.6), or Missing(<coverage reason>) when the search was not counted."""
    return ctx.fdp(engine, unit, db, level, benchmark=benchmark)


def search_status(ctx, engine, benchmark, unit, db):
    c = ctx.coverage_row(engine, benchmark, ctx.unit(unit).name, db)
    return c.status if c is not None else "no_coverage"


def search_ran(ctx, engine, benchmark, unit, db, level=None):
    """The engine ran the search: a coverage row with another state than not_run / not_run_by_design, or a count
    row (SPEC O11: "An engine that did not run the search gets no row; its status is in O14")."""
    u = ctx.unit(unit)
    c = ctx.coverage_row(engine, benchmark, u.name, db)
    if c is not None and c.state not in NOT_RAN:
        return True
    levels = (level,) if level else LEVELS
    return any(ctx.count_row(engine, u, lv, db=db, benchmark=benchmark) is not None for lv in levels)


def _counted_positive(v):
    return isinstance(v, int) and not isinstance(v, bool) and v > 0


def shared_stems(ctx, unit, level, design_name, shared_with=None, benchmark="per_file", stems=None):
    """The stems of a design that every (engine, benchmark) of shared_with counted with accepted > 0 (SPEC 2.7 F;
    DS:623: "completed for an engine and database"). Default shared_with: every engine of E(u) on benchmark.
    The decision rule is not applied here (FdpRun.in_f applies it)."""
    u = ctx.unit(unit)
    pairs = list(shared_with) if shared_with is not None else [(e, benchmark) for e in u.expected]
    out = []
    for s in (stems if stems is not None else u.stems_of(design_name)):
        if all(_counted_positive(ctx.accepted(e, u, level, db=s, benchmark=b)) for e, b in pairs):
            out.append(s)
    return tuple(out)


def fdp_as_o11(ctx, engine, benchmark, unit, level, design_name=None, shared_with=None, stems=None):
    """FDP as O11 for one (engine, benchmark, unit, level) and one design (SPEC O11 "Per run"; DS:616-620).

    shuffled: own n, mean, sample SD (n-1), min, max over the engine's counted realisations with accepted > 0; shared
    n, mean, SD over the realisations every engine of E(u) counted with accepted > 0 (SPEC 2.7 F; OPEN Q13-Q15).
    natural / arath: the single value (DS:620; OPEN Q16) in value, with n_own and n_shared 0 or 1 (several databases
    of one design would give the own mean). A realisation an engine did not count is left out of its own values with
    note 'incomplete' and dropped from the shared values of every engine (OPEN Q15).
    Missing values: Missing(<coverage reason>) per database (failed, failed_memory, not_run, ...), none_accepted
    when N = 0, 'empty' for a statistic over no value, SD 'n<2' for one value (tables.mean_sd)."""
    u = ctx.unit(unit)
    design_name = design_name or main_design(u)
    designed = tuple(u.stems_of(design_name)) if design_name else ()
    if stems is not None:
        keep = set(stems)
        designed = tuple(s for s in designed if s in keep)
    values, statuses = OrderedDict(), OrderedDict()
    for s in designed:
        values[s] = search_fdp(ctx, engine, benchmark, u, s, level)
        statuses[s] = search_status(ctx, engine, benchmark, u, s)
    own = tuple(s for s, v in values.items() if not isinstance(v, T.Missing))
    own_values = [values[s] for s in own]
    # no own value: the statistics carry the reason of the first database (e.g. none_accepted, T10; failed_memory)
    first = next((v for v in values.values() if isinstance(v, T.Missing)), T.Missing("empty"))
    if own_values:
        mean_own, sd_own = T.mean_sd(own_values)
        min_own, max_own = min(own_values), max(own_values)
    else:
        mean_own = sd_own = min_own = max_own = first
    shared = shared_stems(ctx, u, level, design_name, shared_with, benchmark, stems=designed)
    shared = tuple(s for s in shared if s in own)  # an engine outside shared_with may still lack the database
    if shared:
        mean_shared, sd_shared = T.mean_sd([values[s] for s in shared])
    else:
        mean_shared = sd_shared = first if not own_values else T.Missing("not_shared")
    if design_name in ("natural", "arath"):
        value = values[designed[0]] if len(designed) == 1 else mean_own
    else:
        value = T.Missing("not_single")
    ran = any(search_ran(ctx, engine, benchmark, u, s, level) for s in designed)
    notes = []
    if u.is_decision:
        notes.append("decision")
    if design_name == "shuffled" and designed and len(own) < len(designed):
        notes.append("incomplete")
    for s, v in values.items():
        if isinstance(v, T.Missing):
            notes.append(f"{label(u, s)} {v.reason}")
    dropped = [label(u, s) for s in own if s not in shared]
    if dropped:
        notes.append("not shared: " + ", ".join(dropped))
    return FdpRun(engine=engine, benchmark=benchmark, unit=u, level=level, design=design_name, stems=designed,
                  values=values, statuses=statuses, own=own, n_own=len(own), mean_own=mean_own, sd_own=sd_own,
                  min_own=min_own, max_own=max_own, shared=shared, n_shared=len(shared), mean_shared=mean_shared,
                  sd_shared=sd_shared, value=value, ran=ran, note="; ".join(notes))


def run_of(ctx, engine, unit, level, design_name, benchmark="per_file"):
    """fdp_as_o11 with the default shared rule, cached in ctx.shared['fdp_runs'] for this build."""
    u = ctx.unit(unit)
    cache = ctx.shared.setdefault("fdp_runs", OrderedDict())
    key = (engine, benchmark, u.name, level, design_name)
    if key not in cache:
        cache[key] = fdp_as_o11(ctx, engine, benchmark, u, level, design_name)
    return cache[key]


def not_shared_reason(ctx, unit, level, design_name, benchmark="per_file"):
    """Why a non-decision unit has no shared realisation of a design: the first engine and database of E(u) that was
    not counted with accepted > 0 (notes of the per-dataset table)."""
    u = ctx.unit(unit)
    for s in u.stems_of(design_name):
        for e in u.expected:
            v = ctx.accepted(e, u, level, db=s, benchmark=benchmark)
            if isinstance(v, T.Missing):
                return f"{e} {label(u, s)} {v.reason}"
            if v == 0:
                return f"{e} {label(u, s)} zero"
    return "no database"


# ---------------------------------------------------------------- C8 tolerance (for checks.py; SPEC C8, T29)
def h(v):
    """Half a unit in the 4th significant digit of a printed value, 0.5 * 10^(floor(log10|v|) - 3); h(0) = 0
    (EE prints with std::setprecision(4), EE-tool:188-194; SPEC C8)."""
    if v == 0:
        return 0.0
    return 0.5 * 10 ** (math.floor(math.log10(abs(v))) - 3)


def c8_tolerance(combined, te_ratio, ne_over_n):
    """SPEC C8: the allowed |combined - recomputed| = h(combined) + (N_E/N) * h(te_ratio) + 1e-12.
    T29: combined 0.01, te 1, N_E/N 0.005 -> 5e-6 + 2.5e-6 + 1e-12."""
    return h(combined) + ne_over_n * h(te_ratio) + 1e-12


def recomputed_combined(accepted, entrapment, te_ratio):
    """entrapment / accepted * (1 + te_ratio) from the printed columns (SPEC O11, C8); Missing('none_accepted') at
    N = 0 (EE-lib:32)."""
    if accepted == 0:
        return T.Missing("none_accepted")
    return entrapment / accepted * (1 + te_ratio)


def c8_combined_ok(row):
    """C8 for one counts row: the printed combined_fdp agrees with entrapment/accepted*(1+te_ratio) within
    c8_tolerance; an N = 0 row must print 0 (EE-lib:32)."""
    if row.accepted == 0:
        return row.combined_fdp == 0
    ne_n = row.entrapment / row.accepted
    return abs(row.combined_fdp - ne_n * (1 + row.te_ratio)) <= c8_tolerance(row.combined_fdp, row.te_ratio, ne_n)


def c8_lower_ok(row):
    """C8: |lower_bound - N_E/N| <= h(lower_bound) + 1e-12 (EE-lib:84-88); an N = 0 row must print 0."""
    if row.accepted == 0:
        return row.lower_bound_fdp == 0
    return abs(row.lower_bound_fdp - row.entrapment / row.accepted) <= h(row.lower_bound_fdp) + 1e-12


# ---------------------------------------------------------------- helpers of the tables
def _unit_sort(ctx):
    index = {u.name: i for i, u in enumerate(ctx.units)}
    return lambda u: (design.order_key(u.group), index[u.name])


def _entrap_units(ctx):
    """Units with at least one entrapment database, in design order (FIGURE_ORDER, electron, immuno, other) and
    run-table order within a group (the fig_fdp x axis, SPEC O11 "Figure")."""
    return sorted((u for u in ctx.units if designs_of(u)), key=_unit_sort(ctx))


def _ident(u):
    """The leading columns every per-run table carries (SPEC 3 "Grade everywhere")."""
    return OrderedDict([("kind", u.kind), ("class", u.cls), ("grade", u.grade), ("group", u.group)])


def _source_side(units):
    sides = {u.side or u.kind for u in units}
    if not sides:
        return "none"
    if len(sides) == 1 and next(iter(sides)) in ("heldout", "tuning"):
        return next(iter(sides))
    return "mixed"


def _pct(v):
    """A fraction as % (numbers.tsv value, full precision), Missing passed through."""
    return v if isinstance(v, T.Missing) else 100 * v


def _pct_text(v):
    return "NA" if T.is_missing(v) else f"{100 * v:.2f}"  # FDP in %: 2 decimals (SPEC 3 "Formatting")


def _runs(ctx):
    """Every (engine of E(u), unit with entrapment, level, design) FdpRun of the build, in table order."""
    out = []
    for u in _entrap_units(ctx):
        for e in ENGINES:
            if e not in u.expected:
                continue
            for level in ctx.levels:
                for d in designs_of(u):
                    out.append(run_of(ctx, e, u, level, d))
    return out


# ---------------------------------------------------------------- O11
def o11_results(ctx):
    """tables/O11_fdp_results.tsv (SPEC O11 "Selection", "Files"): one row per entrapment search (per_file, database
    in the unit's entrap or ref list) and level that the engine ran, counted or not (an engine that did not run the
    search gets no row). The FDP columns are copied from counts.tsv; an N = 0 search keeps EE's raw 0 with note
    none_accepted (T10); combined_recomputed = entrapment/accepted*(1+te_ratio) (checked by C8). The two counts are
    entrapment-search counts, not identification numbers (DS:610). Returns (rows, n searches, n rows with N = 0)."""
    searches = OrderedDict()
    for c in ctx.coverage:
        if c.benchmark == "per_file" and c.scope == "unit" and c.design in DESIGNS and c.state not in NOT_RAN:
            searches[(c.engine, c.unit.name, c.db)] = c
    for r in ctx.counts:
        if r.benchmark == "per_file" and r.design in DESIGNS:
            searches.setdefault((r.engine, r.unit.name, r.database), None)
    usort = _unit_sort(ctx)

    def key(k):
        u = ctx.unit_by_name[k[1]]
        return (ENGINES.index(k[0]), usort(u), u.stems.index(k[2]))

    rows, n_zero = [], 0
    for k in sorted(searches, key=key):
        engine, name, db = k
        u = ctx.unit_by_name[name]
        d, realisation = u.design_of(db)
        cov = searches[k]
        for level in ctx.levels:
            r = ctx.count_row(engine, u, level, db=db)
            why = ctx.search_reason(engine, "per_file", name, db)
            if r is None or why:
                m = T.Missing(why or "missing_count")
                vals = OrderedDict.fromkeys(("n_accepted_entrap_search", "n_entrapment_hits", "te_ratio",
                                             "lower_bound_fdp", "combined_fdp", "combined_recomputed", "paired_fdp"),
                                            m)
                note = m.reason
            else:
                vals = OrderedDict(n_accepted_entrap_search=r.accepted, n_entrapment_hits=r.entrapment,
                                   te_ratio=r.te_ratio, lower_bound_fdp=r.lower_bound_fdp, combined_fdp=r.combined_fdp,
                                   combined_recomputed=recomputed_combined(r.accepted, r.entrapment, r.te_ratio),
                                   paired_fdp=r.paired_fdp)
                note = ""
                if r.accepted == 0:
                    note = "none_accepted"  # EE's raw 0 is kept here only (SPEC 2.6, T10)
                    n_zero += 1
            row = OrderedDict(engine=engine)
            row.update(_ident(u))
            row.update(unit=name, role=u.role, database=db, design=d,
                       realisation=realisation if realisation is not None else "-", level=level)
            row.update(vals)
            row.update(status=cov.status if cov is not None else "no_coverage", note=note)
            rows.append(row)
    ctx.write_table("O11_fdp_results", O11_RESULTS_COLUMNS, rows, formats=RAW_FORMATS,
                    header_note="FDP columns are fractions; lower_bound_fdp, combined_fdp, paired_fdp and te_ratio as "
                                "printed by EntrapmentEvaluator (4 significant digits); combined_recomputed = "
                                "entrapment/accepted*(1+te_ratio). n_accepted_entrap_search and n_entrapment_hits are "
                                "entrapment-search counts, not identification numbers (DS:610).")
    return rows, len(searches), n_zero


def o11_run_row(run):
    """One row of O11_fdp_runs (SPEC O11): shuffled rows fill the own and shared statistics; natural and arath rows
    the single value in their column (no SD, OPEN Q16), with n_own and n_shared 0 or 1."""
    u = run.unit
    single = run.design in ("natural", "arath")
    row = OrderedDict(engine=run.engine)
    row.update(_ident(u))
    row.update(unit=u.name, role=u.role, level=run.level, design=run.design, n_own=run.n_own,
               mean_own=None if single else run.mean_own, sd_own=None if single else run.sd_own,
               min_own=None if single else run.min_own, max_own=None if single else run.max_own,
               n_shared=run.n_shared, mean_shared=None if single else run.mean_shared,
               sd_shared=None if single else run.sd_shared,
               natural=run.value if run.design == "natural" else None,
               arath=run.value if run.design == "arath" else None, note=run.note)
    return row


def o11_runs(ctx):
    """tables/O11_fdp_runs.tsv: one row per (engine, unit, level, design) that the engine ran (SPEC O11 "Per run");
    rows in design order (the fig_fdp x axis), engines in ENGINES order within a unit, then level, then design."""
    runs = [r for r in _runs(ctx) if r.ran]
    ctx.write_table("O11_fdp_runs", O11_RUNS_COLUMNS, [o11_run_row(r) for r in runs])
    return runs


def dataset_summary(ctx, engine, group, level, design_name, benchmark="per_file"):
    """Per dataset (SPEC O11 "Per dataset"; OPEN Q13, Q53), over the units of F (non-decision, at least one shared
    realisation): n_runs, the mean of the run means, the maximum run mean and the number of run means above 1%.
    n_units: the non-decision units of the group with the design and the engine expected."""
    units = [ctx.unit(n) for n in ctx.groups[group].units]
    units = [u for u in units if design_name in designs_of(u) and engine in u.expected]
    eligible = [u for u in units if not u.is_decision]
    means, missing = [], []
    for u in eligible:
        run = run_of(ctx, engine, u, level, design_name, benchmark)
        if run.in_f:
            means.append(run.run_mean)
        else:
            missing.append(f"{u.name} ({not_shared_reason(ctx, u, level, design_name, benchmark)})")
    if units and not eligible:
        note = "decision only"
    elif missing:
        note = "not in F: " + ", ".join(missing)
    else:
        note = ""
    return OrderedDict(n_units=len(eligible), n_runs=len(means), mean_of_run_means=T.fmean(means),
                       max_run_mean=max(means) if means else T.Missing("empty"),
                       n_runs_mean_above_1pct=sum(1 for m in means if m > TARGET) if means else T.Missing("empty"),
                       note=note)


def o11_datasets(ctx):
    """tables/O11_fdp_datasets.tsv: per engine, group, level and design, for every group of the run table that has
    the design with the engine expected (groups in design order)."""
    rows = []
    groups = sorted(ctx.groups.values(), key=lambda g: design.order_key(g.name))
    for e in ENGINES:
        for g in groups:
            us = [ctx.unit(n) for n in g.units]
            for level in ctx.levels:
                for d in DESIGNS:
                    if not any(d in designs_of(u) and e in u.expected for u in us):
                        continue
                    row = OrderedDict([("engine", e), ("kind", g.kind), ("class", g.cls), ("grade", g.grade),
                                       ("group", g.name), ("level", level), ("design", d)])
                    row.update(dataset_summary(ctx, e, g.name, level, d))
                    rows.append(row)
    ctx.write_table("O11_fdp_datasets", O11_DATASETS_COLUMNS, rows)
    return rows


def o11_numbers(ctx):
    """numbers.tsv keys over F (SPEC O11 "Text"; OPEN Q13, Q53), per level and engine; FDP in % (value full precision,
    text 2 decimals):
      fdp.<level>.<engine>.{max_run_mean, n_runs_mean_above_1pct, n_runs}            each unit at its main design
                                                                                      (natural if it has one, else
                                                                                      shuffled; main_design())
      fdp.<level>.<engine>.<design>.{max_run_mean, n_runs_mean_above_1pct, n_runs}   per design
    A run mean is the shared mean of a unit of F (decision units out, DS:998); an empty set gives NA. Not an
    identification ratio, so main_text_allowed is yes (OPEN Q59); source_side from the units used."""
    ref = "DS:616-620; SPEC O11; OPEN Q13, Q53"
    for level in ctx.levels:
        for e in ENGINES:
            sets = OrderedDict([(None, [])] + [(d, []) for d in DESIGNS])
            for u in _entrap_units(ctx):
                if e not in u.expected or u.is_decision:
                    continue
                for d in designs_of(u):
                    run = run_of(ctx, e, u, level, d)
                    if run.in_f:
                        sets[d].append((u, run.run_mean))
                        if d == main_design(u):
                            sets[None].append((u, run.run_mean))
            for d, items in sets.items():
                prefix = f"fdp.{level}.{e}" + (f".{d}" if d else "")
                means = [m for _, m in items]
                side = _source_side([u for u, _ in items])
                mx = max(means) if means else T.Missing("empty")
                ctx.number(prefix + ".max_run_mean", _pct(mx), _pct_text(mx), unit="%", output="O11",
                           protocol_ref=ref, source_side=side)
                above = sum(1 for m in means if m > TARGET) if means else T.Missing("empty")
                ctx.number(prefix + ".n_runs_mean_above_1pct", above, unit="runs", output="O11", protocol_ref=ref,
                           source_side=side)
                ctx.number(prefix + ".n_runs", len(means), unit="runs", output="O11", protocol_ref=ref,
                           source_side=side)


# ---------------------------------------------------------------- O12
def o12(ctx):
    """tables/O12_fdp_arath.tsv (SPEC O12; DS:370, 619, 935): the units with an Arabidopsis reference database (the 9
    runs of hfx, astral, eclipse_tmtpro), per engine of E(u) and level: the arath value next to the shuffled shared
    mean +- SD of the same run (OPEN Q18); difference_pp = 100 * (arath - shuffled shared mean), table only (OPEN
    Q52); in_shared_set: every engine of E(u) counted the arath search with accepted > 0 and the unit is not a
    decision unit. As in O11, an engine that ran neither the arath nor a shuffled search of the unit gets no row
    (its status is in O14)."""
    rows = []
    for u in _entrap_units(ctx):
        if not u.ref:
            continue
        for e in ENGINES:
            if e not in u.expected:
                continue
            if not any(search_ran(ctx, e, "per_file", u, s) for s in u.ref + tuple(u.stems_of("shuffled"))):
                continue
            for level in ctx.levels:
                ar = run_of(ctx, e, u, level, "arath")
                sh = run_of(ctx, e, u, level, "shuffled")
                a, m = ar.value, sh.mean_shared
                if isinstance(a, T.Missing):
                    diff = a
                elif isinstance(m, T.Missing):
                    diff = m
                else:
                    diff = 100 * (a - m)
                rows.append(OrderedDict([
                    ("engine", e), ("class", u.cls), ("grade", u.grade), ("group", u.group), ("unit", u.name),
                    ("level", level), ("arath", a), ("shuffled_mean_shared", m), ("shuffled_sd_shared", sh.sd_shared),
                    ("shuffled_n_shared", sh.n_shared), ("difference_pp", diff), ("in_shared_set", ar.in_f)]))
    ctx.write_table("O12_fdp_arath", O12_COLUMNS, rows, formats={"difference_pp": T.FMT_PCT})
    return rows


# ---------------------------------------------------------------- O26
def counterpart(ctx, pairing, unit):
    """The run of the other group of a pairing with run-level counterparts (DS:271: astral250pg_X <-> astral_X),
    '-' if none."""
    rule = COUNTERPART.get((pairing, unit.group))
    if rule is None or not unit.name.startswith(rule[0]):
        return "-"
    other = rule[1] + unit.name[len(rule[0]):]
    v = ctx.unit_by_name.get(other)
    return other if v is not None and v.group == rule[2] else "-"


def o26(ctx):
    """tables/O26_pairings.tsv (SPEC O26; DS:159, 271, 312; OPEN Q58), per pairing, engine and level, one row per run
    of both groups: set S1 (astral_s1 natural next to astral shuffled), set S2 (ultra2_s2 natural next to ultra2_hye
    shuffled), and the 250 pg runs next to astral (td counts and FDP per run; counterpart astral250pg_X <->
    astral_X). FDP as O11 at the given design (natural: the single value in mean_own / mean_shared, SD NA).
    accepted_td is the identification count on td; no ratio of identifications from this table enters numbers.tsv
    (astral is a tuning dataset, DS:894). An engine that ran neither the td nor an entrapment search of the run gets
    no row (as O11; its status is in O14)."""
    rows = []
    usort = _unit_sort(ctx)
    for name, g_test, d_test, g_ref, d_ref in PAIRINGS:
        for e in ENGINES:
            for level in ctx.levels:
                for g, d in ((g_test, d_test), (g_ref, d_ref)):
                    if g not in ctx.groups:
                        continue
                    for u in sorted((ctx.unit(n) for n in ctx.groups[g].units), key=usort):
                        if e not in u.expected or d not in designs_of(u):
                            continue
                        run = run_of(ctx, e, u, level, d)
                        if not (run.ran or search_ran(ctx, e, "per_file", u, u.td, level)):
                            continue
                        row = OrderedDict([("pairing", name), ("engine", e), ("level", level)])
                        row.update(_ident(u))
                        row.update(unit=u.name, role=u.role, counterpart=counterpart(ctx, name, u), design=d,
                                   accepted_td=ctx.accepted(e, u, level), n_own=run.n_own, mean_own=run.mean_own,
                                   sd_own=run.sd_own, n_shared=run.n_shared, mean_shared=run.mean_shared,
                                   sd_shared=run.sd_shared, note=run.note)
                        rows.append(row)
    ctx.write_table("O26_pairings", O26_COLUMNS, rows,
                    header_note="FDP columns are fractions (natural: the single value, no SD); accepted_td is the "
                                "td identification count; no ratio from this table enters numbers.tsv (DS:894).")
    return rows


# ---------------------------------------------------------------- O13 matched FDP (fixtures only now)
GridPoint = namedtuple("GridPoint", "q accepted entrapment te_ratio line")
Match = namedtuple("Match", "q_match n_match ne_match fdp_match monotone_ok n_grid")


def grid_fdp(p):
    """The combined FDP of one grid point recomputed from the integer columns and te_ratio, N_E/N * (1 + T/E), as the
    printed combined_fdp is rounded to 4 significant digits (SPEC O13; EE-tool:188-194). N = 0 gives 0 as EE prints
    (EE-lib:32): an empty result qualifies, with count 0."""
    if p.accepted == 0:
        return 0.0
    return p.entrapment / p.accepted * (1 + p.te_ratio)


def match_grid(points, target=TARGET):
    """q_match = the largest grid q whose recomputed FDP is <= target (1.0%, OPEN Q19, Q56); monotone_ok: every grid
    q' <= q_match qualifies as well (the FDP is not monotone in q). T32: FDP 0.008, 0.011, 0.009, 0.012 -> q_match =
    the third grid q, monotone_ok False. No qualifying q: every field Missing('no_match')."""
    pts = sorted(points, key=lambda p: p.q)
    fdps = [grid_fdp(p) for p in pts]
    ok = [f <= target + MATCH_EPS for f in fdps]
    hits = [i for i, o in enumerate(ok) if o]
    if not hits:
        m = T.Missing("no_match")
        return Match(m, m, m, m, m, len(pts))
    i = hits[-1]
    return Match(pts[i].q, pts[i].accepted, pts[i].entrapment, fdps[i], all(ok[:i + 1]), len(pts))


def _qnum(path, line, col, text, kind):
    """int (>= 0) or finite float of one counts_qgrid.tsv cell; stop (exit 2) otherwise."""
    try:
        v = int(text) if kind == "int" else float(text)
    except ValueError:
        T.stop(path, line, col, text, "an integer" if kind == "int" else "a number")
    if kind == "int" and v < 0:
        T.stop(path, line, col, text, "an integer >= 0")
    if kind == "float" and (math.isnan(v) or math.isinf(v)):
        T.stop(path, line, col, text, "a number")
    return v


def read_qgrid(ctx, path):
    """W/counts_qgrid.tsv (SPEC O13: counts.tsv's columns, many q_value; written by qgrid.py, not yet scripted).
    Validated like counts.tsv (SPEC 2.3; stop, exit 2): engine, benchmark name, level, class all, numbers, q in
    (0, 1], file == the unit's count file, one row per (engine, benchmark, run, database, level, q). Kept: per_file
    rows of the units' entrapment databases (O13 is the main arm); arm, td and outside-design rows are counted.
    Returns ({(engine, benchmark, unit, db, level): [GridPoint]}, {reason: n excluded rows})."""
    _, rows = T.read_tsv(path, exact_header=T.COUNTS_HEADER)
    grid, excluded, seen = OrderedDict(), OrderedDict(), set()
    for line, r in rows:
        engine, bench, run, db, level = r["engine"], r["benchmark"], r["run"], r["database"], r["level"]
        if engine not in ENGINES:
            T.stop(path, line, "engine", engine, ", ".join(ENGINES))
        if design.arm_of(bench) is None:
            T.stop(path, line, "benchmark", bench, "per_file or per_file_<tag>")
        if level not in LEVELS:
            T.stop(path, line, "level", level, ", ".join(LEVELS))
        if r["class"] != "all":
            T.stop(path, line, "class", r["class"], "all")
        q = _qnum(path, line, "q_value", r["q_value"], "float")
        if not 0 < q <= 1:
            T.stop(path, line, "q_value", r["q_value"], "a q value in (0, 1]")
        accepted = _qnum(path, line, "accepted", r["accepted"], "int")
        entrapment = _qnum(path, line, "entrapment", r["entrapment"], "int")
        te = _qnum(path, line, "te_ratio", r["te_ratio"], "float")
        u = ctx.unit_by_name.get(run)
        if u is not None and r["file"] != u.count_file:
            T.stop(path, line, "file", r["file"], u.count_file + " (B:1292)")
        qkey = (engine, bench, run, db, level, round(q, 9))
        if qkey in seen:
            T.stop(path, line, "q_value", r["q_value"], "one row per (engine, benchmark, run, database, level, q)")
        seen.add(qkey)
        d = u.design_of(db) if u is not None else None
        if bench != "per_file":
            why = "arm"
        elif d is None:
            why = "outside_design"
        elif d[0] not in DESIGNS:
            why = "td"
        else:
            why = None
        if why:
            excluded[why] = excluded.get(why, 0) + 1
            continue
        grid.setdefault((engine, bench, u.name, db, level), []).append(GridPoint(q, accepted, entrapment, te, line))
    return grid, excluded


def qgrid_state(ctx, engine, unit, db):
    """'ok', 'stale_qgrid' or 'unverified' for the qgrid of one search (SPEC O13, C2). With W/out/ present, the
    SHA256 in <search folder>/count_qgrid.sha256 (first word) must equal that of the current <count file> there, since
    count rewrites it (B:1296-1303); without out/ (the trial copies) or without the two files: 'unverified'."""
    if not ctx.logs_available:
        return "unverified"
    folder = ctx.search_dir(engine, "per_file", unit.name, db)
    sha_file = os.path.join(folder, "count_qgrid.sha256")
    idxml = os.path.join(folder, unit.count_file)
    if not (os.path.exists(sha_file) and os.path.exists(idxml)):
        return "unverified"
    with open(sha_file, encoding="utf-8") as f:
        words = f.read().split()
    return "ok" if words and words[0].lower() == T.sha256_file(idxml) else "stale_qgrid"


def o13(ctx, path=None):
    """O13, counts at a matched combined entrapment FDP (task 9; DS:1052, 742; SPEC O13; OPEN Q19, Q55, Q56), from
    W/counts_qgrid.tsv when it exists (else skipped with INFO). Returns the run rows or None.

    tables/O13_matched_fdp_searches.tsv, per search and level: q_match, the FDP and N there, monotone_ok, next to N
    and the combined FDP at q <= 0.01 from counts.tsv. The count is N, EE's accepted of the entrapment search (DS:742),
    an entrapment-search count (DS:610). A stale qgrid (C2) gives NA.
    tables/O13_matched_fdp.tsv, per run, pair and design: the realisations that every engine of E(u) counted with
    accepted > 0 (F) and matched (a valid qgrid with a q_match); per engine the mean N over them at the matched FDP
    and at q <= 0.01; ratio_matched and ratio_q01 = ProSE / comparator of these means; ratio_plain = O2's run ratio on
    td. Shuffled: the mean over the shared realisations; natural and arath: the single value (OPEN Q55).
    Keys: o13_numbers."""
    path = path or (os.path.join(ctx.work, "counts_qgrid.tsv") if ctx.work else None)
    if not path or not os.path.exists(path):
        ctx.check("INFO", "O13", "no W/counts_qgrid.tsv (qgrid.py not run): O13 matched FDP skipped")
        return None
    ctx.record_input(path, "counts_qgrid")
    grid, excluded = read_qgrid(ctx, path)
    usort = _unit_sort(ctx)
    matches, states, search_rows = {}, {}, []
    n_q01_diff = 0

    def skey(k):
        u = ctx.unit_by_name[k[2]]
        return (ENGINES.index(k[0]), usort(u), u.stems.index(k[3]), LEVELS.index(k[4]))

    for k in sorted(grid, key=skey):
        engine, _, name, db, level = k
        u = ctx.unit_by_name[name]
        d, realisation = u.design_of(db)
        if (engine, name, db) not in states:
            states[(engine, name, db)] = qgrid_state(ctx, engine, u, db)
        m = match_grid(grid[k])
        notes = []
        if states[(engine, name, db)] == "stale_qgrid":
            s = T.Missing("stale_qgrid")
            m = Match(s, s, s, s, s, m.n_grid)
            notes.append("stale_qgrid")
        elif isinstance(m.q_match, T.Missing):
            notes.append("no_match")
        matches[k] = m
        row01 = ctx.count_row(engine, u, level, db=db)
        g01 = [p for p in grid[k] if abs(p.q - TARGET) < 1e-9]
        if g01 and row01 is not None and (g01[0].accepted, g01[0].entrapment) != (row01.accepted, row01.entrapment):
            notes.append("q01_differs")  # the qgrid run saw another result than counts.tsv
            n_q01_diff += 1
        row = OrderedDict(engine=engine)
        row.update(_ident(u))
        row.update(unit=name, role=u.role, database=db, design=d,
                   realisation=realisation if realisation is not None else "-", level=level, n_grid=m.n_grid,
                   q_match=m.q_match, fdp_at_match=m.fdp_match, n_entrap_at_match=m.n_match,
                   monotone_ok=m.monotone_ok, n_entrap_q01=ctx.accepted(engine, u, level, db=db),
                   fdp_q01=ctx.fdp(engine, u, db, level), status=search_status(ctx, engine, "per_file", u, db),
                   note="; ".join(notes))
        search_rows.append(row)
    ctx.write_table("O13_matched_fdp_searches", O13_SEARCH_COLUMNS, search_rows, formats={"q_match": ".6g"},
                    header_note="n_entrap_* are entrapment-search counts (EE's accepted N), not identification "
                                "numbers (DS:610); FDP columns are fractions.")

    def valid(engine, u, db, level):
        m = matches.get((engine, "per_file", u.name, db, level))
        return m is not None and not isinstance(m.q_match, T.Missing)

    rows, per_run = [], []
    units_with_grid = {k[2] for k in grid}
    for u in _entrap_units(ctx):
        if u.name not in units_with_grid:
            continue
        for prose, comp in design.PAIRS:
            if comp not in u.expected:
                continue
            for level in ctx.levels:
                for d in designs_of(u):
                    if not any((e, "per_file", u.name, s, level) in grid for e in (prose, comp)
                               for s in u.stems_of(d)):
                        continue
                    shared = [s for s in shared_stems(ctx, u, level, d)
                              if all(valid(e, u, s, level) for e in u.expected)]
                    notes = ["decision"] if u.is_decision else []
                    if not shared:
                        notes.append("no shared matched realisation")
                    pm = T.fmean([matches[(prose, "per_file", u.name, s, level)].n_match for s in shared])
                    cm = T.fmean([matches[(comp, "per_file", u.name, s, level)].n_match for s in shared])
                    p01 = T.fmean([ctx.accepted(prose, u, level, db=s) for s in shared])
                    c01 = T.fmean([ctx.accepted(comp, u, level, db=s) for s in shared])
                    mono = (all(matches[(e, "per_file", u.name, s, level)].monotone_ok for e in (prose, comp)
                                for s in shared) if shared else T.Missing("empty"))
                    row = OrderedDict([("pair", f"{prose}_{comp}"), ("level", level)])
                    row.update(_ident(u))
                    row.update(unit=u.name, role=u.role, design=d, n_realisations=len(shared),
                               n_entrap_prose_matched=pm, n_entrap_comparator_matched=cm,
                               ratio_matched=T.ratio(pm, cm), n_entrap_prose_q01=p01, n_entrap_comparator_q01=c01,
                               ratio_q01=T.ratio(p01, c01),
                               ratio_plain=T.ratio(ctx.accepted(prose, u, level), ctx.accepted(comp, u, level)),
                               monotone_ok=mono, note="; ".join(notes))
                    rows.append(row)
                    per_run.append((u, comp, level, d, row))
    ctx.write_table("O13_matched_fdp", O13_COLUMNS, rows,
                    header_note="n_entrap_* are mean entrapment-search counts over the shared realisations, not "
                                "identification numbers (DS:610).")
    o13_numbers(ctx, per_run)
    n_stale = sum(1 for s in states.values() if s == "stale_qgrid")
    ctx.check("INFO", "O13", f"counts_qgrid.tsv: {len(search_rows)} search rows, {len(rows)} run rows; excluded rows: "
                             + (", ".join(f"{k} {v}" for k, v in excluded.items()) or "none"))
    if excluded.get("outside_design"):
        ctx.check("WARN", "O13", f"{excluded['outside_design']} counts_qgrid.tsv rows outside the design excluded",
                  strict=True)
    if n_stale:
        ctx.check("WARN", "O13", f"{n_stale} searches with a stale qgrid (count_qgrid.sha256 differs from the current "
                                 "count file): NA", strict=True)
    if n_q01_diff:
        ctx.check("WARN", "O13", f"{n_q01_diff} qgrid search rows whose q = 0.01 point differs from counts.tsv",
                  strict=True)
    return rows


def o13_numbers(ctx, per_run):
    """Keys of O13 (OPEN Q19: ratios in the text, counts only in the supplement table):
    fdp.matched.<scope>.<level>.<comparator>.{lead_matched, lead_q01, lead_plain, n_runs, n_datasets}, over the
    non-decision runs of scope heldout / tuning at their main design with all three ratios, aggregated as O2
    (geometric mean per dataset, then equal weight over datasets, SPEC O2 step 2-3); leads 100(x-1) with 1 decimal.
    main_text_allowed only for heldout (DS:894)."""
    ref = "DS:1052, 742; SPEC O13; OPEN Q19, Q55, Q56"
    for scope in ("heldout", "tuning"):
        allowed = "yes" if scope == "heldout" else "no"
        for level in ctx.levels:
            for _, comp in design.PAIRS:
                by_group = OrderedDict()
                for u, c, lv, d, row in per_run:
                    if c != comp or lv != level or u.kind != scope or u.is_decision or d != main_design(u):
                        continue
                    if any(isinstance(row[x], T.Missing) for x in ("ratio_matched", "ratio_q01", "ratio_plain")):
                        continue
                    by_group.setdefault(u.group, []).append(row)
                prefix = f"fdp.matched.{scope}.{level}.{comp}"
                for col, name in (("ratio_matched", "lead_matched"), ("ratio_q01", "lead_q01"),
                                  ("ratio_plain", "lead_plain")):
                    v = T.lead(T.gmean([T.gmean([r[col] for r in rs]) for rs in by_group.values()]))
                    ctx.number(f"{prefix}.{name}", v, "NA" if T.is_missing(v) else f"{v:.1f}", unit="%",
                               output="O13", protocol_ref=ref, source_side=scope, main_text_allowed=allowed)
                ctx.number(f"{prefix}.n_runs", sum(len(v) for v in by_group.values()), unit="runs", output="O13",
                           protocol_ref=ref, source_side=scope, main_text_allowed=allowed)
                ctx.number(f"{prefix}.n_datasets", len(by_group), unit="datasets", output="O13", protocol_ref=ref,
                           source_side=scope, main_text_allowed=allowed)


# ---------------------------------------------------------------- build
def build(ctx):
    """Writes O11 and O12 (--only fdp), O13 (--only matched; only with W/counts_qgrid.tsv) and O26 (--only pairing),
    with their numbers and INFO/WARN lines (names and counts only, SPEC 5)."""
    if ctx.want("fdp"):
        results, n_searches, n_zero = o11_results(ctx)
        runs = o11_runs(ctx)
        datasets = o11_datasets(ctx)
        o11_numbers(ctx)
        short = sorted({f"{r.engine}:{r.unit.name}" for r in runs
                        if r.design == "shuffled" and len(r.stems) > 1 and r.n_own < len(r.stems)})
        ctx.check("INFO", "O11", f"{len(results)} result rows ({n_searches} entrapment searches), {len(runs)} run "
                                 f"rows, {len(datasets)} dataset rows; {len(short)} engine-runs with own shuffled "
                                 "n < 3" + (f": {', '.join(short)}" if short else ""))
        if n_zero:
            ctx.check("INFO", "O11", f"{n_zero} entrapment-search rows with accepted 0: EE's FDP 0 kept in "
                                     "O11_fdp_results only, none_accepted in every mean (SPEC 2.6)")
        arath = o12(ctx)
        ctx.check("INFO", "O12", f"{len(arath)} rows, {len({r['unit'] for r in arath})} units with a reference "
                                 "database")
    if ctx.want("matched"):
        o13(ctx)
    if ctx.want("pairing"):
        pairs = o26(ctx)
        ctx.check("INFO", "O26", f"{len(pairs)} rows, {len({r['pairing'] for r in pairs})} pairings with runs")
