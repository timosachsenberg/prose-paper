"""Speed and memory (SPEC 3.3): O15 per-file timing, O15b stage times, O16 batch arm, O17 thread scaling, the joint
low_memory table O10 (its timing part next to the counts read from ctx) and O18 machines, versions and memory cap.

Citation keys as in the SPEC: DS = datasets/DATASETS.md, B = benchmarks/bench.py, RM = benchmarks/README.md,
PN = benchmarks/node/prepare_node.sh, RA = checks/node_trial/full/run_all.sh. The timing values themselves (attempts,
per-repetition totals, medians, states) come from the loader (tables.py, SPEC 2.5); this module selects, combines and
writes them.

Outputs (file stems as in SPEC 3.3; the --only keyword in brackets)
  O15  [time]     tables/O15_time_runs.tsv, O15_time_datasets.tsv, O15_time_summary.tsv; keys time.*, mem.*
  O15b [stages]   tables/O15b_stage_times.tsv; needs W/out/ logs and is skipped without them (the loader reports it)
  O16  [batch]    tables/O16_batch.tsv; keys batch.<engine>.median_ratio
  O17  [scaling]  tables/O17_scaling.tsv: the scaling rows (from --scaling-work S, else W) plus one workstation
                  comparison row per engine; keys scaling.<engine>.*
  O10  [lowmem]   tables/O10_low_memory.tsv (counts part: ids.py's ctx.shared['O10_counts'] when it ran); keys
                  lowmem.median_rss_ratio, lowmem.median_wall_ratio (lowmem.identical_all is ids.py's; written here
                  only when ids.py did not run)
  O18  [any of time, stages, batch, scaling, lowmem]  tables/O18_versions.tsv, O18_machines.tsv; keys cap.gib and
                  versions.<tool>

Each output is built on its own: an exception in one is collected, the others are still written, and build() then
raises one RuntimeError naming them (summarize.py turns it into 'FAIL MODULE timing: ...', with the traceback of the
first one as the cause). A ValidationStop propagates at once (exit 2).
"""
import math
import os
import re

from . import design
from . import tables as T

ENGINES = design.ENGINES
# the timing pairs of O15 ("sage/prose, msfragger/prose"): (comparator, base); every ratio is comparator / ProSE
TIME_PAIRS = (("msfragger", "prose"), ("sage", "prose"))
SUMMARY_KINDS = ("tryptic", "electron", "immuno", "other")  # tryptic = tuning + heldout (SPEC 2.2); other: --design none
SHOW_REPS = ("ok", "incomplete", "no_timing")  # states whose complete repetitions are shown as measured
ENGINE_NODE = "engine node"
SCALING_NODE = "scaling node"
LOW_MEMORY = "per_file_low_memory"
JVM_NOTE = ("MSFragger's RSS includes its JVM heap of up to 196 GiB (DS:651, 653); gc_heap_gib is filled only once "
            "task 12 defines the GC-log measurement (OPEN Q48)")

# ---------------------------------------------------------------- columns (SPEC 3.3)
O15_RUNS = ("engine kind class grade group unit role n_files threads state n_reps wall_med_s cpu_med_s rss_med_gib "
            "wall_r1 wall_r2 wall_r3 cpu_r1 cpu_r2 cpu_r3 rss_r1_gib rss_r2_gib rss_r3_gib search_wall_med_s "
            "join_wall_med_s rescoring_wall_med_s gc_heap_gib note").split()
O15_DATASETS = ("pair kind class grade group n_units_group n_units sum_wall_med_s_prose sum_wall_med_s_comparator "
                "sum_cpu_med_s_prose sum_cpu_med_s_comparator max_rss_med_gib_prose max_rss_med_gib_comparator "
                "wall_ratio_gmean n_units_own_prose n_units_own_comparator sum_wall_med_s_own_prose "
                "sum_wall_med_s_own_comparator max_rss_med_gib_own_prose max_rss_med_gib_own_comparator note").split()
O15_SUMMARY = ("kind set pair n_datasets n_units equal_weight run_weighted total_wall_h_prose total_wall_h_comparator "
               "max_rss_gib_prose max_rss_gib_comparator dropped_datasets note").split()
O15B = "engine class grade group unit stage seconds source reps_used note".split()
O16 = ("engine kind class grade group n_files threads batch_wall_med_s batch_wall_per_file_s sum_per_file_wall_s "
       "ratio_wall batch_cpu_med_s sum_per_file_cpu_s ratio_cpu batch_rss_med_gib max_per_file_rss_gib in_B3 "
       "note").split()
O17 = ("engine machine threads state n_reps wall_med_s wall_lower_bound_s cpu_med_s rss_med_gib speedup efficiency "
       "speedup_rel efficiency_rel cores_used search_wall_med_s rescoring_wall_med_s note").split()
O10 = ("group class grade sample role psm_std psm_lm pep_std pep_lm identical wall_std wall_lm wall_ratio cpu_std "
       "cpu_lm cpu_ratio rss_std_gib rss_lm_gib rss_ratio note").split()
O18_VERSIONS = "node tool version command text".split()
O18_MACHINES = "node section item value".split()

# ---------------------------------------------------------------- log line shapes (SPEC O15b; to be confirmed on P logs)
# ProSE's end-of-search report in all.r<rep>.log
PROSE_INDEX = re.compile(r"^\s*\[ProSE\]\s+Fragment idx\s*:\s*\S+\s+peptides\s*/\s*\S+\s+fragments\s+"
                         r"\(build\s+([0-9.]+)\s*s\)")
PROSE_TOTAL = re.compile(r"^\s*\[ProSE\]\s+Total time\s*:\s*total\s+([0-9.]+)\s*s\s*\|\s*search of the file\(s\)\s+"
                         r"([0-9.]+)\s*s\s*\|\s*outputs\s+([0-9.]+)\s*s")
# Sage 0.14.7: lines carry a timestamp prefix and padding, so the patterns are unanchored with \s+
SAGE_INDEX = re.compile(r"generated\s+(\S+)\s+fragments,\s+(\S+)\s+peptides\s+in\s+(\d+)ms")
SAGE_IO = re.compile(r"-\s+file IO:\s+(\d+)\s+ms")
SAGE_SEARCH = re.compile(r"-\s+search:\s+(\d+)\s+ms")
SAGE_TOTAL = re.compile(r"finished in\s+([\d.]+)s")
# MSFragger search.r<rep>.log
FRAGGER_SLICE = re.compile(r"Fragment index slice generated in\s+([\d.]+)\s*s")
FRAGGER_CAL = re.compile(r"MASS CALIBRATION AND PARAMETER OPTIMIZATION DONE IN\s+([\d.]+)\s*MIN")

LOG_STAGES = {"prose": ("index", "search", "output", "total"), "sage": ("index", "io", "search", "total"),
              "msfragger": ("index", "calibration")}
YAML_STAGES = ("calibration", "search", "fdr", "index", "output", "total")
LOG_NAME = {"prose": "all", "sage": "all", "msfragger": "search"}  # <stage>.r<rep>.log of timed runs (B:911-922)

# ---------------------------------------------------------------- machine.txt (O18; PN:30)
CPU_KEYS = ("Architecture", "CPU(s)", "Model name", "Thread(s) per core", "Core(s) per socket", "Socket(s)",
            "NUMA node(s)", "Hypervisor vendor", "Virtualization type")
RAM_KEYS = ("MemTotal", "SwapTotal")
CPU_SUMMARY = {"CPU(s)": "cpus", "Model name": "cpu_model", "Socket(s)": "sockets",
               "Thread(s) per core": "threads_per_core", "Hypervisor vendor": "hypervisor"}
VERSION_TOOLS = ("prose", "fileconverter", "entrapmentevaluator", "sage", "msfragger", "percolator")


# ================================================================ entry point
def build(ctx):
    """Writes O15, O15b, O16, O17, O10 and O18 as --only selects them (SPEC 1; module contract)."""
    steps = []
    if ctx.want("time"):
        steps.append(("O15", build_o15))
    if ctx.want("stages"):
        steps.append(("O15b", build_o15b))
    if ctx.want("batch"):
        steps.append(("O16", build_o16))
    if ctx.want("scaling"):
        steps.append(("O17", build_o17))
    if ctx.want("lowmem"):
        steps.append(("O10", build_o10))
    if any(ctx.want(k) for k in ("time", "stages", "batch", "scaling", "lowmem")):
        steps.append(("O18", build_o18))
    failed = []
    for name, step in steps:
        try:
            step(ctx)
        except T.ValidationStop:
            raise
        except Exception as err:  # the other outputs are still built
            failed.append((name, err))
    if failed:
        text = "; ".join(f"{n}: {e.__class__.__name__}: {e}" for n, e in failed)
        raise RuntimeError(f"timing outputs failed ({text})") from failed[0][1]


# ================================================================ small helpers
def _fsum(xs):
    xs = list(xs)
    return math.fsum(xs) if xs else T.Missing("empty")


def _max(xs):
    xs = list(xs)
    return max(xs) if xs else T.Missing("empty")


def _div(a, b):
    """a / b; a Missing operand passes through; Missing('zero') for b == 0."""
    for x in (a, b):
        if T.is_missing(x):
            return x if isinstance(x, T.Missing) else T.Missing("NA")
    if b == 0:
        return T.Missing("zero")
    return a / b


def _kind4(kind):
    """'tryptic' for tuning and heldout (SPEC 2.2 "tryptic = tuning u heldout", used by O15), else the kind."""
    return "tryptic" if kind in ("tuning", "heldout") else kind


def _side_of_kind(kind):
    """source_side of a unit kind (SPEC 3.8): electron and immuno runs are held-out runs (runs.tsv set heldout)."""
    return {"tuning": "tuning", "heldout": "heldout", "electron": "heldout", "immuno": "heldout"}.get(kind, "none")


def _source_side(kinds):
    sides = {_side_of_kind(k) for k in kinds}
    if not sides:
        return "none"
    return sides.pop() if len(sides) == 1 else "mixed"


def _formats(columns):
    """SPEC 3 "Formatting": times in s (2 decimals, as timings.tsv, B:330), memory in GiB (3), hours (4), ratios (6)."""
    out = {}
    for c in columns:
        words = c.split("_")
        if "gib" in words:
            out[c] = T.FMT_GIB
        elif c.startswith("total_wall_h"):
            out[c] = ".4f"
        elif "s" in words or re.fullmatch(r"(wall|cpu)_r\d", c) or c in ("seconds", "wall_std", "wall_lm", "cpu_std",
                                                                          "cpu_lm"):
            out[c] = T.FMT_S
        else:
            out[c] = T.FMT_RATIO
    return out


def _write(ctx, name, columns, rows, header_note=None):
    """ctx.write_table with the formats of _formats. A table another module already wrote is not written again
    (WARN), so one clash does not stop the other timing outputs."""
    if name in ctx.results:
        ctx.check("WARN", "TIMING", f"table {name} was already written by another module; timing.py did not write it")
        return None
    return ctx.write_table(name, columns, rows, formats=_formats(columns), header_note=header_note)


def _number(ctx, key, value, text=None, **kw):
    """ctx.number, unless another module already wrote the key (WARN instead of a ValueError)."""
    if any(n.key == key for n in ctx.numbers):
        ctx.check("WARN", "TIMING", f"number key {key} was already written by another module; timing.py kept it")
        return
    ctx.number(key, value, text=text, **kw)


def _sig3(value):
    """Paper text of a time, ratio, speed-up or efficiency: 3 significant digits in fixed notation (0.0226, 2.61,
    23.5, 1132); 'NA' for Missing (SPEC 3.8: the value column keeps full precision)."""
    if T.is_missing(value):
        return "NA"
    if value == 0:
        return "0"
    decimals = max(0, 2 - math.floor(math.log10(abs(value))))
    return format(value, f".{decimals}f")


def _unit_order(ctx):
    """Sort key of the design order (SPEC 2.2: FIGURE_ORDER, ELECTRON_ORDER, IMMUNO_ORDER), run-table order within."""
    index = {u.name: i for i, u in enumerate(ctx.units)}
    return lambda u: (design.order_key(u.group), index[u.name])


def _groups_in_order(ctx):
    names = list(ctx.groups)
    return sorted(ctx.groups.values(), key=lambda g: (design.order_key(g.name), names.index(g.name)))


def _timed(ctx, engine, benchmark, run, db=None, threads=None):
    """(state, timing) of one search: ('ok', Timing) when ctx.timing_value gives a value (coverage ok and the last
    attempt complete; SPEC 2.5, 2.6), else (the Missing reason, the Timing or None)."""
    v = ctx.timing_value(engine, benchmark, run, db, threads)
    if isinstance(v, T.Timing):
        return "ok", v
    return v.reason, ctx.timing(engine, benchmark, run, db, threads)


def _n_reps(state, t):
    """The number of complete repetitions r in 1..3 of the attempt used, where its values are reported: the states
    whose repetitions are shown (SHOW_REPS: ok, incomplete, no_timing) and over_limit (they give its lower bound,
    SPEC 2.5). 0 for every other state, whose values are all NA: stale_timing (the attempt belongs to an older search,
    SPEC 2.5), failed, failed_memory, not_run, ... (SPEC O15)."""
    if t is None or t.attempt is None or state not in SHOW_REPS + ("over_limit",):
        return 0
    return sum(1 for r in (1, 2, 3) if r in t.reps and t.reps[r].complete)


def _metrics(state, t):
    """The metric columns of one timed search (SPEC O15): the medians over r = 1..3 per metric independently (OPEN
    Q21; computed by the loader), the per-repetition totals (wall_r = fsum wall, cpu_r = fsum cpu, rss_r = max rss over
    the invocations of r; SPEC 2.5) and the MSFragger stage medians. Medians exist only for state 'ok'. The complete
    repetitions of an incomplete or no_timing attempt are shown as measured; failed searches get NA (SPEC O15)."""
    miss = T.Missing(state)
    out = {"threads": t.threads if t is not None else miss, "n_reps": _n_reps(state, t)}
    if state == "ok":
        out.update(wall=t.wall_med, cpu=t.cpu_med, rss_gib=T.gib(t.rss_med_kb))
    else:
        out.update(wall=miss, cpu=miss, rss_gib=miss)
    for r in (1, 2, 3):
        rep = t.reps.get(r) if t is not None else None
        if state in SHOW_REPS and rep is not None and rep.complete:
            out[f"wall_r{r}"], out[f"cpu_r{r}"], out[f"rss_r{r}"] = rep.wall, rep.cpu, T.gib(rep.rss_kb)
        else:
            out[f"wall_r{r}"] = out[f"cpu_r{r}"] = out[f"rss_r{r}"] = miss
    out["stages"] = {}
    if t is not None:
        for s in t.expected:
            out["stages"][s] = t.stage_wall_med[s] if state == "ok" else miss
    return out


def _note(state, t, coverage):
    """Why a value is NA (the coverage status, or the attempt's note), plus the earlier attempts (SPEC 2.5, C5)."""
    parts = []
    if state != "ok":
        if coverage is not None and coverage.state != "ok":
            parts.append(coverage.status)
        elif t is not None and t.note:
            parts.append(f"{state}: {t.note}")
        else:
            parts.append(state)
    if t is not None and t.n_attempts > 1:
        parts.append(f"{t.n_attempts - 1} earlier attempt(s) not used (SPEC 2.5)")
    return "; ".join(parts)


# ================================================================ O15 per-file timing
def per_file_timings(ctx):
    """{(engine, unit name): (state, Timing or None)} of the per_file td search of every expected engine (SPEC O15
    "Selection": the last attempt, coverage ok). Kept in ctx.shared['timing_per_file'] for O16, O17 and O10."""
    if "timing_per_file" not in ctx.shared:
        out = {}
        for u in ctx.units:
            for e in u.expected:
                out[(e, u.name)] = _timed(ctx, e, "per_file", u.name)
        ctx.shared["timing_per_file"] = out
    return ctx.shared["timing_per_file"]


def build_o15(ctx):
    """O15 (DS:643-648, 657-659, 941): O15_time_runs (one row per unit and expected engine), O15_time_datasets,
    O15_time_summary and the keys time.<kind>.<pair>.ratio, time.<kind>.<pair>.<engine>.total_h,
    mem.<kind>.<pair>.<engine>.max_gib and mem.tryptic.three.<engine>.max_gib (OPEN Q23, Q62)."""
    timed = per_file_timings(ctx)
    units = sorted(ctx.units, key=_unit_order(ctx))
    if ctx.gc_logs:
        ctx.check("WARN", "O15", "--gc-logs given, but the GC-log format is not defined yet (task 12, OPEN Q48): "
                                 "gc_heap_gib stays NA")
    rows = []
    for e in ENGINES:
        frag = e == "msfragger"
        for u in units:
            if e not in u.expected:
                continue  # Sage on bycz units: not run by design, no expected value (B:1357)
            state, t = timed[(e, u.name)]
            m = _metrics(state, t)
            rows.append({
                "engine": e, "kind": u.kind, "class": u.cls, "grade": u.grade, "group": u.group, "unit": u.name,
                "role": u.role, "n_files": u.n_files, "threads": m["threads"], "state": state, "n_reps": m["n_reps"],
                "wall_med_s": m["wall"], "cpu_med_s": m["cpu"], "rss_med_gib": m["rss_gib"],
                "wall_r1": m["wall_r1"], "wall_r2": m["wall_r2"], "wall_r3": m["wall_r3"],
                "cpu_r1": m["cpu_r1"], "cpu_r2": m["cpu_r2"], "cpu_r3": m["cpu_r3"],
                "rss_r1_gib": m["rss_r1"], "rss_r2_gib": m["rss_r2"], "rss_r3_gib": m["rss_r3"],
                "search_wall_med_s": m["stages"].get("search") if frag else None,
                "join_wall_med_s": m["stages"].get("join") if frag else None,
                "rescoring_wall_med_s": m["stages"].get("rescoring") if frag else None,
                "gc_heap_gib": T.Missing("no_gc_logs") if frag else None,
                "note": _note(state, t, ctx.coverage_row(e, "per_file", u.name, u.td)),
            })
    _write(ctx, "O15_time_runs", O15_RUNS, rows,
           header_note=JVM_NOTE + "; medians over repetitions 1-3 per metric (OPEN Q21), repetition 0 never used "
                                  "(DS:642, 804); failed searches NA, never slow (DS:649)")
    states = {}
    for r in rows:
        by = states.setdefault(r["state"], {})
        by[r["engine"]] = by.get(r["engine"], 0) + 1
    ctx.check("INFO", "O15", f"O15_time_runs: {len(rows)} rows; " + "; ".join(
        f"{s} " + "/".join(f"{e} {n}" for e, n in by.items()) for s, by in states.items()))
    _o15_datasets(ctx, timed)
    _o15_summary(ctx, timed)


def _values(timed, engine, units):
    """Wall and CPU medians (s) and RSS medians (GiB) of one engine over units whose timing is ok."""
    ts = [timed[(engine, u.name)][1] for u in units]
    return [t.wall_med for t in ts], [t.cpu_med for t in ts], [T.gib(t.rss_med_kb) for t in ts]


def _ratios(timed, comp, base, units):
    """Per-unit wall-time ratios comparator / base (OPEN Q23); a zero wall gives no ratio (T.ratio)."""
    out = []
    for u in units:
        r = T.ratio(timed[(comp, u.name)][1].wall_med, timed[(base, u.name)][1].wall_med)
        if not isinstance(r, T.Missing):
            out.append(r)
    return out


def _own(timed, engine, units):
    """An engine's own set: the units whose per_file td timing is ok for it (columns _own only, OPEN Q62)."""
    return [u for u in units if timed[(engine, u.name)][0] == "ok"]


def _out_of_set_note(ctx, units, used, engines):
    """Counts of why units are out of the set, e.g. 'sage:failed_memory 3' (names and counts only)."""
    reasons = {}
    used_names = {u.name for u in used}
    for u in units:
        if u.name in used_names:
            continue
        for e in engines:
            v = ctx.timing_value(e, "per_file", u.name)
            if isinstance(v, T.Missing):
                key = f"{e}:{v.reason}"
                reasons[key] = reasons.get(key, 0) + 1
                break
    return ", ".join(f"{k} {n}" for k, n in reasons.items())


def _o15_datasets(ctx, timed):
    """O15_time_datasets (OPEN Q23): per pair and group, over T(pair) of the group's non-decision units: n_units, per
    engine the sums of the wall and CPU medians and the maximum RSS median, the gmean of the per-unit wall ratios
    comparator / ProSE; and each engine's own-set columns (labelled _own). Groups on which the comparator is not run
    by design (Sage on bycz) have no row."""
    rows = []
    for comp, base in TIME_PAIRS:
        for g in _groups_in_order(ctx):
            expecting = [ctx.unit(n) for n in g.units]
            expecting = [u for u in expecting if comp in u.expected and base in u.expected]
            if not expecting:
                continue
            cand = [u for u in expecting if not u.is_decision]
            used = ctx.T((base, comp), units=cand)
            bw, bc, br = _values(timed, base, used)
            cw, cc, cr = _values(timed, comp, used)
            own_b, own_c = _own(timed, base, cand), _own(timed, comp, cand)
            note = ""
            if not cand:
                note = "decision only"
            elif len(used) < len(cand):
                note = "out of T(pair): " + _out_of_set_note(ctx, cand, used, (base, comp))
            rows.append({
                "pair": f"{comp}/{base}", "kind": g.kind, "class": g.cls, "grade": g.grade, "group": g.name,
                "n_units_group": len(cand), "n_units": len(used),
                "sum_wall_med_s_prose": _fsum(bw), "sum_wall_med_s_comparator": _fsum(cw),
                "sum_cpu_med_s_prose": _fsum(bc), "sum_cpu_med_s_comparator": _fsum(cc),
                "max_rss_med_gib_prose": _max(br), "max_rss_med_gib_comparator": _max(cr),
                "wall_ratio_gmean": T.gmean(_ratios(timed, comp, base, used)),
                "n_units_own_prose": len(own_b), "n_units_own_comparator": len(own_c),
                "sum_wall_med_s_own_prose": _fsum(_values(timed, base, own_b)[0]),
                "sum_wall_med_s_own_comparator": _fsum(_values(timed, comp, own_c)[0]),
                "max_rss_med_gib_own_prose": _max(_values(timed, base, own_b)[2]),
                "max_rss_med_gib_own_comparator": _max(_values(timed, comp, own_c)[2]),
                "note": note,
            })
    _write(ctx, "O15_time_datasets", O15_DATASETS, rows,
           header_note="pair = comparator/prose; wall_ratio_gmean = gmean over T(pair) of comparator wall / ProSE "
                       "wall (OPEN Q23); the _own columns are each engine's own complete units (OPEN Q62)")


def _o15_summary(ctx, timed):
    """O15_time_summary (OPEN Q23): per kind (tryptic, electron, immuno) and pair over T(pair): the equal-weight
    gmean over datasets of the per-dataset gmeans (only datasets with at least one unit), the run-weighted gmean, n,
    the total wall hours and the maximum RSS per engine; for tryptic also over T3 (set 'three'). The keys of
    numbers.tsv come from these rows; a kind on which no unit expects the comparator (Sage on the electron runs) gets
    neither a row nor a key."""
    rows = []
    groups = _groups_in_order(ctx)
    for kind in SUMMARY_KINDS:
        groups_k = [g for g in groups if _kind4(g.kind) == kind]
        for set_name in (("pair", "three") if kind == "tryptic" else ("pair",)):
            for comp, base in TIME_PAIRS:
                engines = ENGINES if set_name == "three" else (base, comp)
                per_group = []
                for g in groups_k:
                    expecting = [ctx.unit(n) for n in g.units]
                    expecting = [u for u in expecting if all(e in u.expected for e in engines)]
                    if not expecting:
                        continue
                    cand = [u for u in expecting if not u.is_decision]
                    used = ctx.T3(units=cand) if set_name == "three" else ctx.T((base, comp), units=cand)
                    per_group.append((g, cand, used))
                if not per_group:
                    continue
                used_all = [u for _, _, used in per_group for u in used]
                g_means = [T.gmean(_ratios(timed, comp, base, used)) for _, _, used in per_group if used]
                g_means = [x for x in g_means if not isinstance(x, T.Missing)]
                bw, _, br = _values(timed, base, used_all)
                cw, _, cr = _values(timed, comp, used_all)
                hours_b, hours_c = _div(_fsum(bw), 3600.0), _div(_fsum(cw), 3600.0)
                row = {
                    "kind": kind, "set": set_name, "pair": f"{comp}/{base}", "n_datasets": len(g_means),
                    "n_units": len(used_all), "equal_weight": T.gmean(g_means),
                    "run_weighted": T.gmean(_ratios(timed, comp, base, used_all)),
                    "total_wall_h_prose": hours_b, "total_wall_h_comparator": hours_c,
                    "max_rss_gib_prose": _max(br), "max_rss_gib_comparator": _max(cr),
                    "dropped_datasets": ",".join(g.name for g, _, used in per_group if not used),
                    "note": "T3: units with complete timings for all three engines" if set_name == "three" else "",
                }
                rows.append(row)
                if set_name != "pair":
                    continue
                side = _source_side(u.kind for _, cand, _ in per_group for u in cand)
                key = f"{kind}.{comp}_{base}"
                _number(ctx, f"time.{key}.ratio", row["equal_weight"], _sig3(row["equal_weight"]),
                        unit="ratio", output="O15", protocol_ref="DS:621, 643-648", source_side=side)
                for e, hours, mx in ((base, hours_b, row["max_rss_gib_prose"]),
                                     (comp, hours_c, row["max_rss_gib_comparator"])):
                    _number(ctx, f"time.{key}.{e}.total_h", hours, _sig3(hours), unit="h", output="O15",
                            protocol_ref="DS:643-648", source_side=side)
                    _number(ctx, f"mem.{key}.{e}.max_gib", mx, T.fmt(mx, T.FMT_GIB), unit="GiB", output="O15",
                            protocol_ref="DS:647, 653", source_side=side)
    three = [r for r in rows if r["kind"] == "tryptic" and r["set"] == "three"]
    if three:  # mem.tryptic.three.<engine>.max_gib over T3 (OPEN Q23)
        maxima = {"prose": three[0]["max_rss_gib_prose"]}
        for r in three:
            maxima[r["pair"].split("/")[0]] = r["max_rss_gib_comparator"]
        for e in ENGINES:
            v = maxima.get(e, T.Missing("empty"))
            _number(ctx, f"mem.tryptic.three.{e}.max_gib", v, T.fmt(v, T.FMT_GIB), unit="GiB", output="O15",
                    protocol_ref="DS:623, 647, 653", source_side="mixed")
    _write(ctx, "O15_time_summary", O15_SUMMARY, rows,
           header_note="equal_weight = gmean over datasets of the per-dataset gmeans of comparator/ProSE wall over "
                       "T(pair) (or T3); run_weighted = gmean over all units of the set (OPEN Q23)")


# ================================================================ O15b stage times
def _float(text):
    try:
        return float(text)
    except ValueError:
        return None


def parse_prose_log(text):
    """ProSE all.r<rep>.log (SPEC O15b): 'Fragment idx : N peptides / N fragments (build <x> s)' -> index;
    'Total time : total <x>s | search of the file(s) <x>s | outputs <x>s' -> total, search, output (seconds). The
    report is printed once at the end; the last occurrence counts. A missing line gives None."""
    out = dict.fromkeys(LOG_STAGES["prose"])
    for line in text.splitlines():
        m = PROSE_INDEX.match(line)
        if m:
            out["index"] = _float(m.group(1))
        m = PROSE_TOTAL.match(line)
        if m:
            out["total"], out["search"], out["output"] = (_float(x) for x in m.groups())
    return out


def parse_sage_log(text):
    """Sage all.r<rep>.log (SPEC O15b; lines with a timestamp prefix and padding): 'generated N fragments, N peptides
    in <x>ms' -> index; '- file IO: <x> ms' -> io; '- search: <x> ms' -> search (each summed over the chunks of files
    Sage processes); 'finished in <x>s' -> total (the last one). In seconds; a missing line gives None."""
    sums = {"index": [], "io": [], "search": []}
    total = None
    for line in text.splitlines():
        m = SAGE_INDEX.search(line)
        if m:
            sums["index"].append(int(m.group(3)) / 1000.0)
        m = SAGE_IO.search(line)
        if m:
            sums["io"].append(int(m.group(1)) / 1000.0)
        m = SAGE_SEARCH.search(line)
        if m:
            sums["search"].append(int(m.group(1)) / 1000.0)
        m = SAGE_TOTAL.search(line)
        if m:
            total = _float(m.group(1))
    out = {k: (math.fsum(v) if v else None) for k, v in sums.items()}
    out["total"] = total
    return out


def parse_fragger_log(text):
    """MSFragger search.r<rep>.log (SPEC O15b): the sum of 'Fragment index slice generated in <x> s' -> index;
    'MASS CALIBRATION AND PARAMETER OPTIMIZATION DONE IN <x> MIN' -> calibration (converted to s). None if absent."""
    slices, cal = [], []
    for line in text.splitlines():
        m = FRAGGER_SLICE.search(line)
        if m:
            slices.append(float(m.group(1)))
        m = FRAGGER_CAL.search(line)
        if m:
            cal.append(60.0 * float(m.group(1)))
    return {"index": math.fsum(slices) if slices else None, "calibration": math.fsum(cal) if cal else None}


def parse_prose_yaml(data):
    """ProSE summary.yaml (SPEC O15b): the sums over per_file[].timing_seconds of calibration, search and fdr;
    shared.seconds_index_build -> index, shared.seconds_output -> output, shared.seconds_total -> total."""
    out = dict.fromkeys(YAML_STAGES)
    per_file = data.get("per_file") if isinstance(data, dict) else None
    if isinstance(per_file, list) and per_file:
        for stage in ("calibration", "search", "fdr"):
            vals = []
            for entry in per_file:
                ts = entry.get("timing_seconds") if isinstance(entry, dict) else None
                v = ts.get(stage) if isinstance(ts, dict) else None
                if not isinstance(v, (int, float)) or isinstance(v, bool):
                    vals = None
                    break
                vals.append(float(v))
            out[stage] = math.fsum(vals) if vals else None
    shared = data.get("shared") if isinstance(data, dict) else None
    if isinstance(shared, dict):
        for stage, key in (("index", "seconds_index_build"), ("output", "seconds_output"), ("total", "seconds_total")):
            v = shared.get(key)
            out[stage] = float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None
    return out


def _read_text(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()


def build_o15b(ctx):
    """O15b (DS:647-648, 809-810; OPEN Q22): stage times of every per_file td search whose coverage is ok: from the
    engine logs under W/out (median over r1-r3 per stage; DS:648), ProSE's summary.yaml (r3 only, as it is
    overwritten every repetition, B:761) and, for MSFragger, the stage medians of timings.tsv (search, join,
    rescoring). Needs W/out: skipped without it (the loader writes the INFO LOGS line)."""
    if not ctx.logs_available:
        return
    parsers = {"prose": parse_prose_log, "sage": parse_sage_log, "msfragger": parse_fragger_log}
    timed = per_file_timings(ctx)
    units = sorted(ctx.units, key=_unit_order(ctx))
    rows, n_logs = [], 0
    for e in ENGINES:
        for u in units:
            if e not in u.expected:
                continue
            cov = ctx.coverage_row(e, "per_file", u.name, u.td)
            if cov is None or cov.state != "ok":
                continue  # failed and not-run searches: their state is in O15
            state, t = timed[(e, u.name)]
            base = {"engine": e, "class": u.cls, "grade": u.grade, "group": u.group, "unit": u.name}
            timing_note = "" if state == "ok" else f"timing {state}"
            if e == "msfragger" and t is not None:
                for stage in ("search", "join", "rescoring"):
                    if stage in t.expected:
                        v = t.stage_wall_med[stage] if state == "ok" else T.Missing(state)
                        rows.append(dict(base, stage=stage, seconds=v, source="timings.tsv", reps_used="r1-r3",
                                         note=timing_note))
            folder = ctx.search_dir(e, "per_file", u.name, u.td)
            parsed, absent = {}, []
            for r in (1, 2, 3):
                path = os.path.join(folder, f"{LOG_NAME[e]}.r{r}.log")
                if os.path.exists(path):
                    parsed[r] = parsers[e](_read_text(path))
                    ctx.record_input(path, f"log {e} {u.name} r{r}")
                    n_logs += 1
                else:
                    absent.append(f"no {LOG_NAME[e]}.r{r}.log")
            for stage in LOG_STAGES[e]:
                vals = [parsed[r][stage] if r in parsed else None for r in (1, 2, 3)]
                lacking = [f"r{r}" for r in (1, 2, 3) if r in parsed and parsed[r][stage] is None]
                note = absent + ([f"line not found in {','.join(lacking)}"] if lacking else [])
                note += [timing_note] if timing_note else []
                v = T.median(vals) if all(x is not None for x in vals) else T.Missing("no_log" if absent
                                                                                       else "not_found")
                rows.append(dict(base, stage=stage, seconds=v, source=f"{LOG_NAME[e]}.r<rep>.log", reps_used="r1-r3",
                                 note="; ".join(note)))
            if e == "prose":
                path = os.path.join(folder, "summary.yaml")
                ynote, yvals = "", dict.fromkeys(YAML_STAGES)
                if not os.path.exists(path):
                    ynote = "no summary.yaml"
                else:
                    ctx.record_input(path, f"summary.yaml {u.name}")
                    try:
                        yvals = parse_prose_yaml(T.read_yaml(path))
                    except ValueError as err:
                        ynote = f"summary.yaml not read: {err}"
                for stage in YAML_STAGES:
                    v = yvals[stage]
                    note = [ynote or ("" if v is not None else "key not found"), timing_note]
                    rows.append(dict(base, stage=stage, seconds=v if v is not None else T.Missing("no_yaml"),
                                     source="summary.yaml", reps_used="r3", note="; ".join(x for x in note if x)))
    _write(ctx, "O15b_stage_times", O15B, rows,
           header_note="line shapes of builds before P, to be confirmed on P logs (SPEC 7); logs: median over r1-r3 "
                       "per stage (DS:648); summary.yaml: r3 only (B:761); MSFragger search/join/rescoring: stage "
                       "medians of timings.tsv")
    ctx.check("INFO", "O15b", f"O15b_stage_times: {len(rows)} rows from {n_logs} logs")


# ================================================================ O16 batch arm
def _batch_groups_in_order(ctx):
    """BATCH_ORDER (SPEC 2.2: the 16 tryptic batch groups in figure order, then pxd065289_etcid); others after."""
    names = list(ctx.batch_groups)
    idx = {g: i for i, g in enumerate(design.BATCH_ORDER)}
    return sorted(ctx.batch_groups.values(),
                  key=lambda g: (0, idx[g.name]) if g.name in idx else (1, names.index(g.name)))


def build_o16(ctx):
    """O16 (DS:661-663, 797; B:974-980): per engine and batch group the batch medians (wall and CPU: median over r of
    the summed invocations; RSS: median over r of the maximum; MSFragger 1 search + n_files rescoring, RM:178), the
    batch time per file = batch_wall / n_files (n_files = the group's rows with sample == '-', decision runs included;
    OPEN Q24), the sum of the files' per_file medians (O15; NA if a file lacks one), ratio = batch / sum for wall and
    CPU, and the batch RSS next to the maximum per-file RSS median. Keys batch.<engine>.median_ratio over B3."""
    b3 = set(ctx.B3())
    rows = []
    groups = _batch_groups_in_order(ctx)
    for e in ENGINES:
        ratios = []
        for g in groups:
            if e not in g.expected:
                continue  # Sage on pxd065289_etcid (bycz)
            state, t = _timed(ctx, e, "batch", g.name)
            m = _metrics(state, t)
            singles = [(r, ctx.timing_value(e, "per_file", r)) for r in g.runs]
            lacking = [(r, v.reason) for r, v in singles if isinstance(v, T.Missing)]
            if lacking:
                sum_wall = sum_cpu = max_rss = T.Missing("per_file_missing")
            else:
                sum_wall = math.fsum(v.wall_med for _, v in singles)
                sum_cpu = math.fsum(v.cpu_med for _, v in singles)
                max_rss = max(T.gib(v.rss_med_kb) for _, v in singles)
            ratio_wall = _div(m["wall"], sum_wall)
            note = [_note(state, t, ctx.coverage_row(e, "batch", g.name, g.td))]
            if lacking:
                note.append("per_file medians missing: " + ", ".join(f"{r} {why}" for r, why in lacking))
            rows.append({
                "engine": e, "kind": g.kind, "class": g.cls, "grade": g.grade, "group": g.name, "n_files": g.n_files,
                "threads": m["threads"], "batch_wall_med_s": m["wall"],
                "batch_wall_per_file_s": _div(m["wall"], g.n_files), "sum_per_file_wall_s": sum_wall,
                "ratio_wall": ratio_wall, "batch_cpu_med_s": m["cpu"], "sum_per_file_cpu_s": sum_cpu,
                "ratio_cpu": _div(m["cpu"], sum_cpu), "batch_rss_med_gib": m["rss_gib"],
                "max_per_file_rss_gib": max_rss, "in_B3": g.name in b3,
                "note": "; ".join(x for x in note if x),
            })
            if g.name in b3 and not isinstance(ratio_wall, T.Missing):
                ratios.append(ratio_wall)
        v = T.median(ratios)
        side = _source_side(g.kind for g in groups if g.name in b3 and e in g.expected)
        _number(ctx, f"batch.{e}.median_ratio", v, _sig3(v), unit="ratio", output="O16",
                protocol_ref="DS:661-663", source_side=side)
    _write(ctx, "O16_batch", O16, rows,
           header_note="ratio = batch median / sum of the files' per_file medians (O15); n_files includes decision "
                       "runs, which the batch contains (OPEN Q24); in_B3: the batch ratio exists for every engine of "
                       "the group (SPEC 2.7)")
    n_ok = {e: sum(1 for r in rows if r["engine"] == e and not isinstance(r["batch_wall_med_s"], T.Missing))
            for e in ENGINES}
    ctx.check("INFO", "O16", f"O16_batch: {len(rows)} rows; batch timing ok " +
              "/".join(f"{e} {n}" for e, n in n_ok.items()) + f"; B3 {len(b3)} groups")


# ================================================================ O17 thread scaling
def _separate_scaling(ctx):
    """True when the scaling rows come from another folder S (--scaling-work; OPEN Q35)."""
    o = ctx.options
    if not o.scaling_timings:
        return False
    return not (o.timings and os.path.realpath(o.timings) == os.path.realpath(o.scaling_timings))


def scaling_points(ctx):
    """[((engine, run), sorted thread counts)] from the scaling coverage rows and the scaling timing keys (the
    not_run_over_limit points have timing rows only, B:996-999). The grid is read from the data (SPEC O17)."""
    points = {}
    for c in ctx.coverage:
        if c.benchmark == "scaling":
            points.setdefault((c.engine, c.run), set()).add(c.threads)
    for key in ctx.timings:
        if key[1] == "scaling":
            points.setdefault((key[0], key[2]), set()).add(key[4])
    runs = list(ctx.scaling_runs) + sorted({r for _, r in points if r not in ctx.scaling_runs})
    return [((e, r), sorted(points[(e, r)])) for r in runs for e in ENGINES if (e, r) in points]


def build_o17(ctx):
    """O17 (DS:640, 665-671, 1006, 1016; B:983-1001). Per (engine, n): T_n = median over r of the summed wall
    (MSFragger search + rescoring, OPEN Q25; search alongside), C_n, M_n; S_n = T_1/T_n and E_n = S_n/n when T_1
    exists, else the relative S_rel_n = T_n0/T_n and E_rel_n = S_rel_n/(n/n0) with n0 the smallest completed n;
    cores_used = C_n/T_n (table only, OPEN Q51). over_limit points carry only the lower bound min(completed
    repetitions, L) (SPEC 2.5); not_run_over_limit points are NA. Per engine one workstation comparison row: the
    engine node's per_file timing of the scaling run's unit (O15), next to the scaling node's 16-thread point (DS:671;
    OPEN Q25)."""
    timed = per_file_timings(ctx)
    grid = scaling_points(ctx)
    runs = []
    for (_, run), _ in grid:
        if run not in runs:
            runs.append(run)
    if len(runs) > 1:
        ctx.check("WARN", "O17", f"{len(runs)} scaling runs: the rows carry the run in the note; the keys use the "
                                 "first run of each engine")
    rows, first = [], {}
    for (e, run), threads in grid:
        rr = ctx.run_by_id.get(run)
        if rr is None:
            continue
        db = rr.db + "_td"
        points = {n: _timed(ctx, e, "scaling", run, db, n) for n in threads}
        walls = {n: t.wall_med for n, (state, t) in points.items() if state == "ok"}
        t1 = walls.get(1)
        n0 = min(walls) if walls else None
        for n in threads:
            state, t = points[n]
            m = _metrics(state, t)
            wall = m["wall"]
            if state != "ok":
                speed = eff = speed_rel = eff_rel = T.Missing(state)
            elif t1 is not None:
                speed = _div(t1, wall)
                eff = _div(speed, n)
                speed_rel = eff_rel = T.Missing("t1_exists")
            else:
                speed = eff = T.Missing("no_t1")
                speed_rel = _div(walls[n0], wall)
                eff_rel = _div(speed_rel, n / n0)
            if t is not None and t.state == "over_limit":
                lower = t.lower_bound
            else:
                lower = T.Missing("no_over_limit_row" if state == "over_limit" else "not_over_limit")
            note = [f"run {run}"] if len(runs) > 1 else []
            if state == "over_limit" and t is not None and t.limit is not None:
                note.append(f"over the limit L = {t.limit:.0f} s ({t.note}); wall_lower_bound_s = min(completed "
                            "repetitions, L)")
            elif state == "not_run_over_limit":
                note.append("not run: over the limit at a higher thread count (B:996-999); no coverage row")
            else:
                note.append(_note(state, t, ctx.coverage_row(e, "scaling", run, f"{db}_t{n}")))
            if state == "ok" and t1 is None:
                note.append(f"no T_1: speedup_rel and efficiency_rel against n0 = {n0}")
            if run not in ctx.scaling_runs:
                note.append("run not flagged scaling in the run table (B:986)")
            frag = e == "msfragger"
            rows.append({
                "engine": e, "machine": SCALING_NODE, "threads": n, "state": state, "n_reps": m["n_reps"],
                "wall_med_s": wall, "wall_lower_bound_s": lower, "cpu_med_s": m["cpu"], "rss_med_gib": m["rss_gib"],
                "speedup": speed, "efficiency": eff, "speedup_rel": speed_rel, "efficiency_rel": eff_rel,
                "cores_used": _div(m["cpu"], wall),
                "search_wall_med_s": m["stages"].get("search", T.Missing(state)) if frag else None,
                "rescoring_wall_med_s": m["stages"].get("rescoring", T.Missing(state)) if frag else None,
                "note": "; ".join(x for x in note if x),
            })
            if e not in first or first[e][0] == run:
                first.setdefault(e, (run, {}))[1][n] = rows[-1]
        rows.append(_workstation_row(ctx, timed, e, run))
    if _separate_scaling(ctx):
        source = f"S = {ctx.options.scaling_work or os.path.dirname(ctx.options.scaling_timings)} (--scaling-work)"
    else:
        source = "W (no --scaling-work: the scaling rows were read from W)"
    _write(ctx, "O17_scaling", O17, rows,
           header_note=f"scaling rows from {source}; scaling run(s): {', '.join(runs) or 'none'}; machine "
                       f"'{ENGINE_NODE}' = the workstation comparison row (per_file, O15; DS:671); MSFragger wall = "
                       "search + rescoring (OPEN Q25)")
    _scaling_numbers(ctx, first)
    ctx.check("INFO", "O17", f"O17_scaling: {len(rows)} rows; grid points per engine " + "/".join(
        f"{e} {sum(1 for r in rows if r['engine'] == e and r['machine'] == SCALING_NODE)}" for e in ENGINES))


def _workstation_row(ctx, timed, engine, run):
    """The engine node's per_file timing of the scaling run's unit (O15), as the workstation comparison (DS:671)."""
    u = ctx.unit_of_run.get(run)
    if u is None or engine not in u.expected:
        state, t = "no_unit", None
    else:
        state, t = timed[(engine, u.name)]
    m = _metrics(state, t)
    note = [f"workstation comparison (DS:671): per_file {u.name if u else run} on the engine node (O15), next to "
            "the scaling node's 16-thread point"]
    if state == "ok" and m["threads"] != 16:
        note.append(f"per_file ran at {m['threads']} threads, not 16")
    if u is not None and u.pooled:
        note.append("the per_file unit is a pooled sample, not the single scaling run")
    if state != "ok":
        note.append(_note(state, t, ctx.coverage_row(engine, "per_file", u.name, u.td) if u else None))
    frag = engine == "msfragger"
    na = T.Missing("workstation_row")
    return {
        "engine": engine, "machine": ENGINE_NODE, "threads": m["threads"], "state": state, "n_reps": m["n_reps"],
        "wall_med_s": m["wall"], "wall_lower_bound_s": na, "cpu_med_s": m["cpu"], "rss_med_gib": m["rss_gib"],
        "speedup": na, "efficiency": na, "speedup_rel": na, "efficiency_rel": na,
        "cores_used": _div(m["cpu"], m["wall"]),
        "search_wall_med_s": m["stages"].get("search", T.Missing(state)) if frag else None,
        "rescoring_wall_med_s": m["stages"].get("rescoring", T.Missing(state)) if frag else None,
        "note": "; ".join(x for x in note if x),
    }


def _scaling_numbers(ctx, first):
    """Keys scaling.<engine>.{wall_t1_h, wall_t16_min, speedup_t16, speedup_tmax, efficiency_t16, efficiency_tmax}
    (SPEC O17 "Text") from the first scaling run of each engine; NA where the point is missing or not complete."""
    for e in ENGINES:
        run, by_n = first.get(e, (None, {}))
        u = ctx.unit_of_run.get(run) if run else None
        side = _side_of_kind(u.kind) if u is not None else "none"
        missing = T.Missing("not_in_grid" if by_n else "no_scaling_rows")
        tmax = max(by_n) if by_n else None

        def col(n, name):
            return by_n[n][name] if n in by_n else missing

        values = (
            ("wall_t1_h", _div(col(1, "wall_med_s"), 3600.0), "h"),
            ("wall_t16_min", _div(col(16, "wall_med_s"), 60.0), "min"),
            ("speedup_t16", col(16, "speedup"), ""),
            ("speedup_tmax", col(tmax, "speedup"), ""),
            ("efficiency_t16", col(16, "efficiency"), ""),
            ("efficiency_tmax", col(tmax, "efficiency"), ""),
        )
        for name, v, unit in values:
            _number(ctx, f"scaling.{e}.{name}", v, _sig3(v), unit=unit, output="O17",
                    protocol_ref="DS:665-671", source_side=side)


# ================================================================ O10 low_memory arm, joint table
COUNT_COLUMNS = ("psm_std", "psm_lm", "pep_std", "pep_lm")


def _identical_all(flags):
    """lowmem.identical_all over the non-decision samples, as ids.py computes it (it owns the key, SPEC 1 module
    map: ids.py the O10 counts part): Missing('empty') without samples, Missing('incomplete') if a sample is not
    counted, else whether all are identical (DS:988; OPEN Q27)."""
    if not flags:
        return T.Missing("empty")
    if any(T.is_missing(x) for x in flags):
        return T.Missing("incomplete")
    return all(flags)


def build_o10(ctx):
    """O10 (DS:579-582, 652, 988; RA:121-123): per sample with a per_file_low_memory td search, ProSE's td counts of
    both arms (identical expected, DS:988; the verdict is C10's), the wall, CPU and RSS medians of both arms (timing
    as O15; a ratio lm/std only when both are complete), and a summary row (group 'summary') with the median of each
    ratio over the non-decision samples (OPEN Q27). The counts part is ids.py's ctx.shared['O10_counts'] when ids.py
    ran (it also writes lowmem.identical_all); else it is read from ctx here and the key is written here. Keys
    lowmem.median_rss_ratio, lowmem.median_wall_ratio (and lowmem.identical_all without ids.py)."""
    samples = [u for u in ctx.units if ctx.coverage_row("prose", LOW_MEMORY, u.name, u.td) is not None]
    from_ids = ctx.shared.get("O10_counts")
    by_sample = {r["sample"]: r for r in from_ids} if from_ids is not None else None
    if by_sample is not None and set(by_sample) != {u.name for u in samples}:
        ctx.check("WARN", "O10", f"the counts part of ids.py has {len(by_sample)} samples, the low_memory coverage "
                                 f"rows {len(samples)}; samples without ids.py's row are counted here")
    rows = []
    for u in samples:
        if by_sample is not None and u.name in by_sample:
            counts = {c: by_sample[u.name][c] for c in COUNT_COLUMNS}
            identical = by_sample[u.name]["identical"]
        else:
            counts = {}
            for level, std_col, lm_col in (("psm", "psm_std", "psm_lm"), ("peptide", "pep_std", "pep_lm")):
                counts[std_col] = ctx.accepted("prose", u, level)
                counts[lm_col] = ctx.accepted("prose", u, level, benchmark=LOW_MEMORY)
            if any(isinstance(v, T.Missing) for v in counts.values()):
                identical = T.Missing("not_counted")
            else:
                identical = counts["psm_std"] == counts["psm_lm"] and counts["pep_std"] == counts["pep_lm"]
        lacking = [c for c, v in counts.items() if isinstance(v, T.Missing)]
        s_state, s_t = _timed(ctx, "prose", "per_file", u.name)
        l_state, l_t = _timed(ctx, "prose", LOW_MEMORY, u.name)
        s, lm = _metrics(s_state, s_t), _metrics(l_state, l_t)
        note = []
        if lacking:
            note.append("not counted: " + ", ".join(f"{c} {counts[c].reason}" for c in lacking))
        if s_state != "ok":
            note.append("standard: " + _note(s_state, s_t, ctx.coverage_row("prose", "per_file", u.name, u.td)))
        if l_state != "ok":
            note.append("low_memory: " + _note(l_state, l_t, ctx.coverage_row("prose", LOW_MEMORY, u.name, u.td)))
        row = {"group": u.group, "class": u.cls, "grade": u.grade, "sample": u.name, "role": u.role}
        row.update(counts)
        row.update({
            "identical": identical, "wall_std": s["wall"], "wall_lm": lm["wall"],
            "wall_ratio": _div(lm["wall"], s["wall"]), "cpu_std": s["cpu"], "cpu_lm": lm["cpu"],
            "cpu_ratio": _div(lm["cpu"], s["cpu"]), "rss_std_gib": s["rss_gib"], "rss_lm_gib": lm["rss_gib"],
            "rss_ratio": _div(lm["rss_gib"], s["rss_gib"]), "note": "; ".join(note),
        })
        rows.append(row)
    used = [r for r in rows if r["role"] != "decision"]
    medians = {c: T.median([r[c] for r in used if not isinstance(r[c], T.Missing)])
               for c in ("wall_ratio", "cpu_ratio", "rss_ratio")}
    identical_all = _identical_all([r["identical"] for r in used])
    if rows:
        n_ratio = sum(1 for r in used if not isinstance(r["wall_ratio"], T.Missing))
        summary = dict.fromkeys(O10)
        summary.update({
            "group": "summary", "class": "-", "grade": "-", "sample": f"median over {n_ratio} non-decision samples",
            "role": "-", "identical": identical_all,
            "note": "median of each ratio over the non-decision samples with both arms complete (OPEN Q27); "
                    "identical over the non-decision samples (DS:988)"})
        summary.update(medians)
        rows.append(summary)
    _write(ctx, "O10_low_memory", O10, rows,
           header_note="ProSE td: per_file (standard) vs per_file_low_memory; ratios lm/std; the last row (group "
                       "summary) holds the medians over the non-decision samples")
    side = "heldout" if used else "none"
    _number(ctx, "lowmem.median_rss_ratio", medians["rss_ratio"], _sig3(medians["rss_ratio"]), unit="ratio",
            output="O10", protocol_ref="DS:582, 652", source_side=side)
    _number(ctx, "lowmem.median_wall_ratio", medians["wall_ratio"], _sig3(medians["wall_ratio"]),
            unit="ratio", output="O10", protocol_ref="DS:582, 652", source_side=side)
    written = [n for n in ctx.numbers if n.key == "lowmem.identical_all"]
    if not written:  # ids.py did not run: the key is written here
        ctx.number("lowmem.identical_all", identical_all, output="O10", protocol_ref="DS:988", source_side=side)
    elif written[0].value != identical_all:
        ctx.check("WARN", "O10", f"lowmem.identical_all of ids.py is {T.fmt(written[0].value)}, the joint table's "
                                 f"summary row {T.fmt(identical_all)}")
    ctx.check("INFO", "O10", f"O10_low_memory: {len(samples)} samples, {len(used)} non-decision" +
              ("; counts part from ids.py" if by_sample is not None else "; counts read here (ids.py did not run)"))


# ================================================================ O18 machines, versions, memory cap
def version_tool(command):
    """The tool of a versions.txt line (B:357): the base name of the executable (or of the jar), lower case."""
    words = command.split()
    exe = words[0] if words else ""
    if os.path.basename(exe) == "java" and "-jar" in words and words.index("-jar") + 1 < len(words):
        exe = words[words.index("-jar") + 1]
    name = os.path.basename(exe).lower()
    if name.startswith("msfragger"):
        return "msfragger"
    name = re.sub(r"\.(jar|exe)$", "", name)
    return re.sub(r"[^a-z0-9_]", "_", name) or "unknown"


def version_text(tool, text):
    """The version in one versions.txt line: OpenMS tools '<version>, revision <rev>'; Sage, MSFragger and
    Percolator their version number; any other tool the first ' | ' part of its text."""
    m = re.search(r"Version:\s*(\S+).*?Revision:\s*(\w+)", text)
    if m:
        return f"{m.group(1)}, revision {m.group(2)}"
    patterns = {"sage": r"^sage\s+(\S+)", "msfragger": r"MSFragger-([0-9][0-9.]*)",
                "percolator": r"Percolator version\s+([0-9][0-9.]*)"}
    if tool in patterns:
        m = re.search(patterns[tool], text)
        if m:
            return m.group(1).rstrip(".")
    return text.split(" | ")[0].strip()


def machine_rows(label, path):
    """node_prep/machine.txt (PN:30; DS:641, 1049) -> ([(node, section, item, value)], summary dict). First a
    'summary' block (host, role, memory cap, RAM in GiB, CPUs, CPU model, sockets, OS, kernel, memory.max of the cap
    check), then the record: the key/value lines of the head, RAM and the CPU keys of CPU_KEYS, and every other
    section line by line (loop devices left out). Read line by line here rather than with T.read_machine, as a value
    may itself hold ':' (the kernel's build time in the OS section)."""
    with open(path, encoding="utf-8", errors="replace") as f:
        lines = f.read().splitlines()
    record, summary, section = [], {}, ""
    for line in lines:
        if not line.strip():
            continue
        if line.startswith("## "):
            section = line[3:].strip()
            continue
        if line.startswith("# "):
            record.append(("header", "header", line[2:].strip()))
            continue
        key, sep, val = line.partition(":")
        key, val = key.strip(), val.strip()
        if section == "":
            record.append(("head", key, val) if sep else ("head", "line", line.strip()))
            if sep and key in ("host", "role", "memory cap"):
                summary[key.replace(" ", "_")] = val
        elif section == "RAM":
            if sep and key in RAM_KEYS:
                record.append((section, key, val))
                m = re.match(r"^(\d+)\s*kB$", val)
                if key == "MemTotal" and m:
                    summary["ram_gib"] = format(int(m.group(1)) / 2 ** 20, T.FMT_GIB)
        elif section == "CPU":
            if sep and key in CPU_KEYS:
                record.append((section, key, val))
                if key in CPU_SUMMARY:
                    summary[CPU_SUMMARY[key]] = val
        else:
            if section.startswith("storage") and re.match(r"^(loop\d+|sr\d+)\s", line):
                continue
            record.append((section, "line", line.strip()))
            if section == "OS" and line.startswith("PRETTY_NAME="):
                summary["os"] = line.split("=", 1)[1].strip().strip('"')
            elif section == "OS" and line.startswith("Linux ") and len(line.split()) > 1:
                summary["kernel"] = line.split()[1]
            elif section.startswith("memory cap check") and re.fullmatch(r"\d+", line.strip()) \
                    and "memory_max_bytes" not in summary:
                summary["memory_max_bytes"] = line.strip()
    out = [(label, "summary", k, v) for k, v in summary.items()]
    out += [(label, s, k, v) for s, k, v in record]
    return out, summary


def build_o18(ctx):
    """O18 (DS:638-641, 649-653, 1009-1017, task 7): W/versions.txt and S/versions.txt into O18_versions (B:357, with
    a node column; the strings are checked by C13 in checks.py); every --machine LABEL=PATH (PN:30) into O18_machines;
    WARN(s) if no machine file is given for W, or for a separate scaling folder S (DS:641: "Recorded for both"); a
    WARN if a machine's cap is not 200 GiB; the keys cap.gib = 200 (DS:653) and versions.<tool> of W."""
    separate = _separate_scaling(ctx)
    sources = [(ENGINE_NODE, ctx.versions, ctx.options.versions)]
    if separate:
        o = ctx.options
        same = o.scaling_versions and o.versions and os.path.realpath(o.scaling_versions) == os.path.realpath(
            o.versions)
        sources.append((SCALING_NODE, None if same or not o.scaling_versions else ctx.scaling_versions,
                        o.scaling_versions))
    rows = []
    for node, versions, path in sources:
        if versions is None:
            ctx.check("WARN", "O18", f"no versions.txt for the {node} ({path})", strict=True)
            continue
        for command, text in versions:
            tool = version_tool(command)
            rows.append({"node": node, "tool": tool, "version": version_text(tool, text), "command": command,
                         "text": text})
    _write(ctx, "O18_versions", O18_VERSIONS, rows,
           header_note="versions.txt (B:357) of W" + (" and S" if separate else "") + "; the strings are checked by "
                                                                                      "C13")
    for r in rows:
        if r["node"] == ENGINE_NODE and r["tool"] in VERSION_TOOLS:
            _number(ctx, f"versions.{r['tool']}", r["version"], r["version"], output="O18",
                    protocol_ref="DS:729; B:347-357", source_side="none")
    mrows = []
    for label, path in ctx.machines:
        out, summary = machine_rows(label, path)
        mrows += out
        cap = summary.get("memory_cap", "")
        m = re.search(r"--mem-gb\s+(\d+)", cap)
        if m and int(m.group(1)) != design.CAP_GIB:
            ctx.check("WARN", "O18", f"machine {label}: memory cap --mem-gb {m.group(1)}, not {design.CAP_GIB} "
                                     "(DS:653)")
        mx = summary.get("memory_max_bytes")
        if mx and int(mx) != design.CAP_GIB * 2 ** 30:
            ctx.check("WARN", "O18", f"machine {label}: memory.max {mx} bytes, not {design.CAP_GIB} GiB (DS:653)")
    _write(ctx, "O18_machines", O18_MACHINES, mrows,
           header_note="node_prep/machine.txt per --machine LABEL=PATH (PN:30); what backs the virtual disks is "
                       "recorded by hand (task 7, DS:1049)")
    if not ctx.machines:
        ctx.check("WARN", "O18", "no machine file (--machine LABEL=PATH) for the engine node W (DS:641)", strict=True)
    elif separate and len(ctx.machines) < 2:
        ctx.check("WARN", "O18", "one machine file for W and a separate scaling folder S: no machine file for the "
                                 "scaling node (DS:641)", strict=True)
    else:
        ctx.check("INFO", "O18", f"O18: {len(ctx.machines)} machine file(s), {len(sources)} versions file(s)")
    _number(ctx, "cap.gib", design.CAP_GIB, str(design.CAP_GIB), unit="GiB", output="O18", protocol_ref="DS:653",
            source_side="none")
