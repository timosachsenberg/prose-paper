"""Consistency layer of the summaries: the checks C1-C25 of SPEC section 5 -> check_report.txt.

Every invocation runs them (--only included, SPEC 1). Each check writes one or more lines
'PASS|WARN|FAIL|INFO <id> <message>' through ctx.check. Messages name keys and counts only, never values (SPEC 5).
A WARN marked (s) in SPEC 5 is written with strict=True, so --strict turns it into a FAIL.

There is no blind mode (the lead's decision of 2026-11-24): every verdict, C10 and the zero-count INFO included, goes
to check_report.txt.

Inputs: the loaded inputs on ctx (tables.py), the tables the modules wrote before (ctx.results, by the SPEC's file
stems and columns) and the numbers (ctx.numbers). A check that needs a table which this build did not write (e.g.
under --only) says 'INFO <id> SKIP ...: table <name> absent'. A check that raises an exception gives
'FAIL <id> check raised ...'; the other checks go on, and the tracebacks go to <out>/errors_checks.txt (written on
every build, empty without an error, so no stale file stays).

C6 is reported under the ids C6a-C6d (its parts (a)-(d) in SPEC 5): it compares the tables and numbers the modules
wrote (O02_pairs_*, O04_overtuning_<level>_sides, ids.* and overtuning.* keys) and W/overtuning_<level>.tsv with
overtuning.py's own OT.load, so it is independent of the module that made them.

Expected values of the paper design (C4, C11, C13, C14, C15) are in PAPER; run(ctx, expected) replaces them with a
fixture's values in the tests (SPEC 6: "The checks run with a fixture design").

Citation keys as in the SPEC: DS = datasets/DATASETS.md, B = benchmarks/bench.py, OT = benchmarks/overtuning.py,
RM = benchmarks/README.md, RA = the engine-node trial runner, REF = datasets/reference_ids.tsv, EE-tool / EE-lib =
EntrapmentEvaluator at P.
"""
import math
import os
import re
import traceback
from collections import Counter, OrderedDict

from . import design
from . import tables as T

OT = design.OT  # benchmarks/overtuning.py, imported by design.py (import-safe: main is guarded, OT:189-190)

TRYPTIC = OT.TUNING + OT.HELDOUT  # the 17 datasets of the over-tuning check, in OT's order (OT:26-28)
REL_TOL = 1e-12  # C6a, C6b: the package's fsum against OT's plain sum (OT:34-35; SPEC 2.7)
PP_TOL = 1e-9  # C6d: leads in percentage points
LIST = 10  # keys named per message
TIMED_PER_FILE = ("per_file", "per_file_low_memory")  # C5: per_file td of every unit and the low_memory arm (RA:121-123)
OT_HEADER = "engine\tside\tdataset\trun\tratio\tdataset_value"  # OT:147

# the expected values of the paper design; the tests pass the fixture's (SPEC 6)
PAPER = {
    # SPEC 2.1 "Batch groups": the 16 tryptic groups with >= 2 files plus pxd065289_etcid; 16 for Sage (bycz)
    "batch_groups": design.BATCH_ORDER,
    # DS:998 (runs.tsv lines 23, 25, 37, 46-48, 64-66, 76, 82)
    "decision": design.DECISION,
    # DS:860-878 "Runs used": non-decision runs per tryptic dataset, in OT's order
    "runs_used": OrderedDict(zip(TRYPTIC, (3, 3, 3, 3, 3, 3, 2, 3, 2, 1, 2, 3, 3, 3, 2, 3, 2))),
    # DS:16: MS2 spectra of the 20 tuning runs
    "ms2_tuned": 1509392,
    # DS:1011 (decision of 2026-11-23): Sage is expected to fail for memory on the class II samples
    "failed_memory_expected": (("sage", "pxd058436_classII"), ("sage", "pxd019643_classII")),
    # C13: (tool, regular expression on the command of versions.txt, required text) (DS:729, 1001; B:346-357)
    "versions": (
        ("ProSE", r"(^|/)ProSE(\s|$)", "Revision: b2d252b"),
        ("FileConverter", r"(^|/)FileConverter(\s|$)", "Revision: b2d252b"),
        ("EntrapmentEvaluator", r"(^|/)EntrapmentEvaluator(\s|$)", "Revision: b2d252b"),
        ("Sage", r"(^|/)sage(\s|$)", "sage 0.14.6"),  # the v0.14.7 binary reports 0.14.6 (DS:729)
        ("MSFragger", r"MSFragger[^/\s]*\.jar", "MSFragger-4.4.1"),
        ("Percolator", r"(^|/)percolator(\s|$)", "Percolator version 3.09"),
    ),
}


# ---------------------------------------------------------------- small helpers
def _list(items, limit=LIST):
    """At most `limit` items, comma-separated, then '... (+n more)'."""
    items = [str(x) for x in items]
    if len(items) <= limit:
        return ", ".join(items)
    return ", ".join(items[:limit]) + f", ... (+{len(items) - limit} more)"


def _key(parts):
    """A search key as text: engine/benchmark/run/database[/t<threads>]."""
    out = []
    for i, p in enumerate(parts):
        if p is None:
            continue
        out.append(f"t{p}" if i == 4 else str(p))
    return "/".join(out)


def _by(keys, index=0):
    """'prose 12, sage 12': the counts of element `index` of the keys, in first-seen order."""
    c = Counter(k[index] for k in keys)
    return ", ".join(f"{k} {n}" for k, n in c.items())


def _num(v):
    """A typed table cell as a float, or None for Missing/None/NaN/bool/text that is not a number."""
    if v is None or isinstance(v, (bool, T.Missing)):
        return None
    if isinstance(v, (int, float)):
        return None if isinstance(v, float) and math.isnan(v) else float(v)
    try:
        x = float(str(v))
    except ValueError:
        return None
    return None if math.isnan(x) else x


def _int(v):
    """A typed cell as a non-bool int, else None."""
    if isinstance(v, bool):
        return None
    if isinstance(v, int):
        return v
    if isinstance(v, str) and re.fullmatch(r"\d+", v.strip()):
        return int(v)
    return None


def _yes(v):
    """A yes/no cell (bool, or text 'yes'/'true')."""
    if isinstance(v, bool):
        return v
    return isinstance(v, str) and v.strip().lower() in ("yes", "true", "1")


def _comparator(pair):
    """The comparator engine named in a pair or comparator cell ('prose_msfragger', 'ProSE/Sage', 'MSFragger')."""
    s = str(pair).lower()
    if "msfragger" in s:
        return "msfragger"
    if "sage" in s:
        return "sage"
    return None


def _table(ctx, cid, name, columns, purpose):
    """The typed rows of a table another module wrote (ctx.results), or None: 'INFO <cid> SKIP' when the table is
    absent, FAIL when it lacks a column the SPEC names (SPEC 3)."""
    if name not in ctx.results:
        ctx.check("INFO", cid, f"SKIP {purpose}: table {name} absent (not written by this build)")
        return None
    have = ctx.result_columns.get(name, [])
    lacking = [c for c in columns if c not in have]
    if lacking:
        ctx.check("FAIL", cid, f"{purpose}: table {name} lacks the column(s) {', '.join(lacking)} (SPEC 3)")
        return None
    return ctx.results[name]


def _age(ctx, name):
    """(sort key, source) of a file of W: from --listing when it names the file (copies carry the copy time, SPEC
    C18), else the file's mtime; None if neither knows the file."""
    if ctx.listing is not None and name in ctx.listing:
        return ctx.listing[name]["key"], "listing"
    if ctx.work:
        p = os.path.join(ctx.work, name)
        if os.path.exists(p):
            return os.path.getmtime(p), "mtime"
    return None


def _older(ctx, name, than):
    """True/False whether W/<name> is older than W/<than>; None when the two ages cannot be compared."""
    a, b = _age(ctx, name), _age(ctx, than)
    if a is None or b is None or a[1] != b[1]:
        return None
    return a[0] < b[0]


def _ot_leads(ds, e):
    """(L_T, L_H) of one comparator from OT's dataset values with OT's own gmean (OT:41-47); None for a side without
    a dataset (OT.side_leads then returns None for the whole dict, OT:44-45)."""
    t = [v for d, v in ds[e].items() if d in OT.TUNING]
    h = [v for d, v in ds[e].items() if d in OT.HELDOUT]
    return (100 * (OT.gmean(t) - 1) if t else None, 100 * (OT.gmean(h) - 1) if h else None)


def _ot(ctx, state):
    """OT.load(runs, W/counts.tsv, level) per level, once per build (C6, C25): (ds, rows, notes) or the exception."""
    if "ot" not in state:
        out = OrderedDict()
        for level in ctx.levels:
            try:
                out[level] = OT.load(ctx.options.runs, ctx.options.counts, level)
            except Exception as err:  # OT asserts its inputs (OT:93-107)
                out[level] = err
        state["ot"] = out
    return state["ot"]


def _ot_skip(ctx, cid):
    """C6 and C25 need --design paper and W/counts.tsv; True (with an INFO SKIP line) when they cannot run."""
    if ctx.design_mode != "paper":
        ctx.check("INFO", cid, "SKIP: --design none (OT.load needs the role column and the 17 datasets, OT:93, 95)")
        return True
    if not ctx.options.counts or not os.path.exists(ctx.options.counts):
        ctx.check("INFO", cid, "SKIP: no counts.tsv")
        return True
    return False


def _clean_rep(rep):
    """A repetition whose rows all exited 0 (a failed or over-limit repetition stops early, B:298-313)."""
    return all(x.exit == 0 for x in rep.rows)


# ---------------------------------------------------------------- C1-C5: inputs
def c01_key_sets(ctx, exp, state):
    """C1: the key set of counts.tsv equals the coverage keys with counted = yes, both directions (B:1365: counted is
    yes exactly when the folder has a count.tsv; B:1370-1378: counts.tsv is collected from the same files)."""
    counts = {(r.engine, r.benchmark, r.run, r.database)
              for r in ctx.counts + ctx.counts_outside + ctx.counts_rule11b}
    counted = {(c.engine, c.benchmark, c.run, c.database) for c in ctx.coverage + ctx.coverage_outside if c.counted}
    only_counts, only_cov = sorted(counts - counted), sorted(counted - counts)
    if not only_counts and not only_cov:
        ctx.check("PASS", "C1", f"counts.tsv and coverage.tsv (counted yes): the same {len(counts)} search keys")
        return
    ctx.check("FAIL", "C1", f"{len(only_counts)} counts.tsv key(s) without coverage counted=yes"
                            f"{': ' + _list(map(_key, only_counts)) if only_counts else ''}; {len(only_cov)} "
                            f"coverage counted=yes key(s) without counts rows"
                            f"{': ' + _list(map(_key, only_cov)) if only_cov else ''}")


def c02_count_rows(ctx, exp, state):
    """C2: each counted search has exactly one psm and one peptide row, class all, q 0.01 and file == the unit's count
    file (SPEC 2.1, 2.3; EE-tool:198-204; B:1292; the loader stops on each, so this restates it per key). With
    W/counts_qgrid.tsv and W/out, the SHA256 recorded next to the count file (count_qgrid.sha256, first word) matches
    the current .count.idXML (SPEC O13), else stale_qgrid WARN(s). qgrid.py is not written yet (lead's decision)."""
    by_key = OrderedDict()
    for r in ctx.counts + ctx.counts_rule11b + ctx.counts_outside:
        by_key.setdefault((r.engine, r.benchmark, r.run, r.database), []).append(r)
    bad_levels = [k for k, rs in by_key.items() if sorted(r.level for r in rs) != ["peptide", "psm"]]
    bad_q = [k for k, rs in by_key.items() if any(abs(r.q_value - 0.01) >= 1e-9 for r in rs)]
    bad_file = [k for k, rs in by_key.items() if any(r.unit is not None and r.file != r.unit.count_file for r in rs)]
    if bad_levels or bad_q or bad_file:
        ctx.check("FAIL", "C2", f"{len(bad_levels)} search(es) without exactly one psm and one peptide row"
                                f"{': ' + _list(map(_key, bad_levels)) if bad_levels else ''}; {len(bad_q)} with q != "
                                f"0.01{': ' + _list(map(_key, bad_q)) if bad_q else ''}; {len(bad_file)} with another "
                                f"count file{': ' + _list(map(_key, bad_file)) if bad_file else ''}")
    else:
        ctx.check("PASS", "C2", f"{len(by_key)} counted searches: one psm and one peptide row each, class all, q 0.01, "
                                "file = the unit's count file")
    qgrid = os.path.join(ctx.work, "counts_qgrid.tsv") if ctx.work else None
    if not qgrid or not os.path.exists(qgrid):
        return
    if not ctx.out_dir or not os.path.isdir(ctx.out_dir):
        ctx.check("INFO", "C2", "SKIP qgrid SHA256: W/counts_qgrid.tsv present, but no W/out")
        return
    stale, compared, without = [], 0, 0
    for k, rs in by_key.items():
        unit = rs[0].unit
        if unit is None:
            continue
        folder = ctx.search_dir(*k)
        rec = os.path.join(folder, "count_qgrid.sha256")
        idxml = os.path.join(folder, unit.count_file)
        if not (os.path.exists(rec) and os.path.exists(idxml)):
            without += 1  # unverified, as fdp.qgrid_state says (e.g. a light copy has no .count.idXML)
            continue
        with open(rec, encoding="utf-8") as f:
            words = f.read().split()
        compared += 1
        if not words or words[0].lower() != T.sha256_file(idxml):
            stale.append(k)
    if stale:
        ctx.check("WARN", "C2", f"stale_qgrid: {len(stale)} of {compared} count_qgrid.sha256 differ from the current "
                                f".count.idXML: {_list(map(_key, stale))}", strict=True)
    else:
        ctx.check("PASS", "C2", f"qgrid SHA256 equal in {compared} search folders ({without} without "
                                "count_qgrid.sha256 or .count.idXML: unverified)")


def c03_coverage(ctx, exp, state):
    """C3: coverage holds every per_file (engine x unit x database) the run table implies (B:1353-1359; 690 for the
    full table); tags outside ARMS are generic arms (O25, WARN, SPEC 2.2); rows outside the design are excluded and
    listed in O14 (WARN(s), SPEC 2.3; T35); rule11b rows go to O9b (INFO)."""
    implied = [(e, "per_file", u.name, s) for u in ctx.units for e in design.ENGINES for s in u.stems]
    missing = [k for k in implied if k not in ctx.coverage_index]
    if missing:
        ctx.check("FAIL", "C3", f"coverage lacks {len(missing)} of the {len(implied)} per_file searches the run table "
                                f"implies (B:1353-1359): {_list(map(_key, missing))}")
    else:
        ctx.check("PASS", "C3", f"coverage holds all {len(implied)} per_file searches the run table implies")
    for tag in ctx.unknown_tags:
        n_counts = len({(r.engine, r.run, r.database) for r in ctx.counts if r.tag == tag})
        n_cov = sum(1 for c in ctx.coverage if c.tag == tag)
        n_tim = sum(1 for r in ctx.timing_rows if r.tag == tag)
        ctx.check("WARN", "C3", f"generic arm per_file_{tag} (tag not in ARMS, O25): {n_cov} coverage rows, "
                                f"{n_counts} counted searches, {n_tim} timing rows")
    outside_counts = sorted({(r.engine, r.benchmark, r.run, r.database) for r in ctx.counts_outside})
    outside_cov = [(c.engine, c.benchmark, c.run, c.database) for c in ctx.coverage_outside]
    outside_tim = sorted({(r.engine, r.benchmark, r.run, r.db) for r in ctx.timing_outside})
    if outside_counts or outside_cov or outside_tim:
        keys = list(OrderedDict.fromkeys(outside_counts + outside_cov + outside_tim))
        ctx.check("WARN", "C3", f"rows outside the design, excluded and listed in O14 (outside_design): "
                                f"{len(outside_counts)} counted searches, {len(outside_cov)} coverage rows, "
                                f"{len(outside_tim)} timing keys: {_list(map(_key, keys))}", strict=True)
    elif not ctx.unknown_tags:
        ctx.check("PASS", "C3", "no row outside the design; no generic arm")
    if ctx.counts_rule11b:
        keys = sorted({(r.engine, r.benchmark, r.run, r.database) for r in ctx.counts_rule11b})
        ctx.check("INFO", "C3", f"{len(keys)} rule11b searches (task 11b, to O9b): {_list(map(_key, keys))}")


def c04_states(ctx, exp, state):
    """C4: states (SPEC 2.4, 2.6). not_run_by_design <=> Sage on a bycz unit (B:1357), both directions; Sage
    failed_memory on the class II samples is expected (PASS with a note, DS:1011); any other failed / failed_memory,
    and not_run, running, interrupted, unknown, over_limit on per_file* -> WARN(s); ok with counted = no on per_file*
    -> WARN(s) (not_counted). Batch and scaling are counted = no by construction (B:1365) and not checked for it; their
    other states WARN(s), except scaling over_limit (an INFO of C12). accepted == 0 on a per_file td result: INFO (kept
    in O1, out of every ratio, OT:113-116)."""
    expected_fm = {tuple(x) for x in exp["failed_memory_expected"]}
    nrbd_ok, nrbd_bad, fm_ok, problems = [], [], [], OrderedDict()
    n_ok = 0
    for c in ctx.coverage:
        key = (c.engine, c.benchmark, c.run, c.database)
        u = c.unit
        if c.scope == "unit":
            if c.state == "not_run_by_design":
                (nrbd_ok if c.engine == "sage" and u is not None and u.ions == "bycz" else nrbd_bad).append(key)
            elif c.state == "failed_memory" and u is not None and (c.engine, u.group) in expected_fm:
                fm_ok.append(key)
            elif c.state == "ok":
                if c.counted:
                    n_ok += 1
                else:
                    problems.setdefault("ok but not counted (not_counted)", []).append(key)
            else:
                problems.setdefault(c.state, []).append(key)
        elif c.state != "ok" and not (c.scope == "scaling" and c.state == "over_limit"):
            problems.setdefault(f"{c.state} ({c.scope})", []).append(key)
    for u in ctx.units:  # the converse: every Sage per_file search of a bycz unit is not_run_by_design
        if u.ions != "bycz":
            continue
        for s in u.stems:
            c = ctx.coverage_index.get(("sage", "per_file", u.name, s))
            if c is not None and c.state != "not_run_by_design":
                nrbd_bad.append(("sage", "per_file", u.name, s))
    if nrbd_bad:
        ctx.check("FAIL", "C4", f"not_run_by_design <=> Sage on a bycz unit violated by {len(nrbd_bad)} search(es) "
                                f"(B:1357): {_list(map(_key, nrbd_bad))}")
    else:
        ctx.check("PASS", "C4", f"not_run_by_design exactly on the {len(nrbd_ok)} Sage searches of bycz units "
                                "(B:1357)")
    for label, keys in problems.items():
        ctx.check("WARN", "C4", f"{len(keys)} search(es) {label} ({_by(keys)}): {_list(map(_key, keys))}",
                  strict=True)
    note = (f"{len(fm_ok)} expected failed_memory (Sage on the class II samples, DS:1011): "
            f"{_list(sorted({k[2] for k in fm_ok}))}" if fm_ok else "")
    if not problems:
        ctx.check("PASS", "C4", f"every other per_file* search ok and counted ({n_ok}); batch and scaling ok"
                                f"{'; ' + note if note else ''}")
    elif fm_ok:
        ctx.check("PASS", "C4", note)
    zero = [(r.engine, r.run, r.level) for r in ctx.counts if r.design == "td" and r.benchmark == "per_file"
            and r.accepted == 0]
    if zero:
        ctx.check("INFO", "C4", f"accepted == 0 in {len(zero)} per_file td result(s) (kept in O1, out of every ratio, "
                                f"OT:113-116): {_list('/'.join(k) for k in zero)}")


def _timed(c):
    """Whether a coverage row is a timed search (SPEC C5): per_file td of every unit, the low_memory arm, batch,
    scaling."""
    if c.benchmark in ("batch", "scaling"):
        return True
    return c.benchmark in TIMED_PER_FILE and c.design == "td"


def c05_timings(ctx, exp, state):
    """C5: timings (SPEC 2.5). Every timing key maps to a coverage key, except the not_run_over_limit points (no folder,
    B:996-999, 1360-1363); every coverage-ok timed search (per_file td of all units, low_memory, batch, scaling) has a
    complete last attempt (over_limit exempt; stale_timing is C24's); earlier attempts are counted and listed;
    no_timing -> WARN; the stage multiset per repetition as SPEC 2.5 (repetitions that exited 0); MSFragger batch:
    rescoring rows per repetition == n_files (RM:178)."""
    no_cov, n_nrol = [], 0
    for key, t in ctx.timings.items():
        if t.state == "not_run_over_limit":
            n_nrol += 1
            continue
        e, b, run, db, thr = key
        if (e, b, run, f"{db}_t{thr}" if b == "scaling" else db) not in ctx.coverage_index:
            no_cov.append(key)
    if no_cov:
        ctx.check("WARN", "C5", f"{len(no_cov)} timing key(s) without a coverage row: {_list(map(_key, no_cov))}",
                  strict=True)
    else:
        ctx.check("PASS", "C5", f"every timing key ({len(ctx.timings) - n_nrol}) has a coverage row"
                                f"{f' ({n_nrol} not_run_over_limit points have none, B:996-999)' if n_nrol else ''}")
    n_complete, missing, incomplete, stale, over = 0, [], [], [], []
    for c in ctx.coverage:
        if c.state != "ok" or not _timed(c):
            continue
        key = (c.engine, c.benchmark, c.run, c.db, c.threads if c.benchmark == "scaling" else None)
        t = ctx.timings.get(key)
        if t is None:
            missing.append(key)
        elif t.state == "complete":
            n_complete += 1
        elif t.state == "stale_timing":
            stale.append(key)
        elif t.state == "over_limit":
            over.append(key)
        elif t.state != "no_timing":  # no_timing: its own line below
            incomplete.append((key, t.state, t.note))
    if missing or incomplete:
        parts = [f"{_key(k)} ({s}: {n})" for k, s, n in incomplete]
        ctx.check("WARN", "C5", f"{len(missing) + len(incomplete)} coverage-ok timed search(es) without a complete "
                                f"last attempt: {len(missing)} without timing rows"
                                f"{': ' + _list(map(_key, missing)) if missing else ''}; {len(incomplete)} incomplete"
                                f"{': ' + _list(parts, 5) if parts else ''}")
    else:
        extra = [f"{len(over)} over_limit (exempt)" if over else "", f"{len(stale)} stale_timing (C24)" if stale else ""]
        extra = "; ".join(x for x in extra if x)
        ctx.check("PASS", "C5", f"{n_complete} coverage-ok timed searches (per_file td, low_memory, batch, scaling) "
                                f"have a complete last attempt{'; ' + extra if extra else ''}")
    no_timing = [(k, t.note) for k, t in ctx.timings.items() if t.state == "no_timing"]
    if no_timing:
        ctx.check("WARN", "C5", f"no_timing in {len(no_timing)} key(s) (B:305-312; values NA): "
                                f"{_list(f'{_key(k)} ({n})' for k, n in no_timing)}")
    if ctx.earlier_attempts:
        ctx.check("INFO", "C5", f"{len(ctx.earlier_attempts)} key(s) with earlier attempts, only the last is used "
                                f"(SPEC 2.5): {_list(f'{_key(k)} ({n} earlier)' for k, n in ctx.earlier_attempts)}")
    bad_stages, n_reps = [], 0
    for key, t in ctx.timings.items():
        if t.attempt is None or t.attempt.state in ("over_limit", "no_timing"):
            continue
        for r, rep in t.attempt.reps.items():
            if not _clean_rep(rep):
                continue
            n_reps += 1
            if rep.stages != t.expected:
                bad_stages.append(f"{_key(key)} r{r}")
    if bad_stages:
        ctx.check("WARN", "C5", f"{len(bad_stages)} repetition(s) with another stage set than SPEC 2.5: "
                                f"{_list(bad_stages)}")
    else:
        ctx.check("PASS", "C5", f"stage sets as SPEC 2.5 in all {n_reps} clean repetitions of the used attempts")
    batch = [(k, t) for k, t in ctx.timings.items() if k[0] == "msfragger" and k[1] == "batch"
             and t.attempt is not None and t.attempt.state not in ("over_limit", "no_timing")]
    bad_batch = [f"{_key(k)} r{r}" for k, t in batch for r, rep in t.attempt.reps.items()
                 if _clean_rep(rep) and rep.stages.get("rescoring", 0) != t.group.n_files]
    if bad_batch:
        ctx.check("WARN", "C5", f"MSFragger batch: rescoring rows != n_files in {len(bad_batch)} repetition(s) "
                                f"(RM:178): {_list(bad_batch)}")
    elif batch:
        ctx.check("PASS", "C5", f"MSFragger batch: rescoring rows per repetition == n_files in {len(batch)} group(s)")


# ---------------------------------------------------------------- C6: over-tuning against OT
def c06_overtuning(ctx, exp, state):
    """C6 (lines C6a-C6d): the over-tuning numbers against overtuning.py (SPEC 3.5; OT:90-124).
    (a) the package's dataset values (O02_pairs_datasets gmean) vs OT.load's ds: relative difference <= 1e-12 (fsum vs
        OT's plain sum, OT:34-35), both comparators and levels;
    (b) run ratios: f"{p/q:.6f}" == OT's strings, keyed by (NAMES[e], side, dataset, run) (OT:30, 117, 123);
        dataset_value strings equal, or floats within 1e-12 relative (INFO "rounding boundary");
    (c) W/overtuning_<level>.tsv rows == OT's rows as strings (OT:147): missing or different -> WARN(s); older than
        counts.tsv -> WARN only, not strict (SPEC 3.5, C6c; the default of OPEN Q61; SPEC 9 R1-19). C18 records the
        ages as INFO. SPEC 7 V3 expects "no WARN" on the engine-node trial, which contradicts Q61; the Q61 default is followed;
    (d) the O2 equal-weight leads on scopes heldout and tuning (O02_pairs_summary lead_pct, the numbers
        ids.<scope>.<level>.<comparator>.lead) and the O4 values (O04_overtuning_<level>_sides L_T, L_H; the numbers
        overtuning.<level>.lt_/lh_<comparator>) == OT's L_T / L_H within 1e-9 percentage points."""
    if _ot_skip(ctx, "C6"):
        return
    loaded = OrderedDict()
    for level, res in _ot(ctx, state).items():
        if isinstance(res, Exception):
            ctx.check("FAIL", "C6", f"{level}: OT.load raised {res.__class__.__name__}: {res}")
        else:
            loaded[level] = res
    if not loaded:
        return
    ds_rows = _table(ctx, "C6a", "O02_pairs_datasets", ("pair", "level", "group", "gmean"),
                     "C6a/C6b dataset values")
    pkg_ds = None
    if ds_rows is not None:
        pkg_ds = {}
        for row in ds_rows:
            e = _comparator(row["pair"])
            if e in OT.ENGINES and row["group"] in TRYPTIC:
                pkg_ds[(e, row["level"], row["group"])] = row["gmean"]
        _c06a(ctx, loaded, pkg_ds)
    run_rows = _table(ctx, "C6b", "O02_pairs_runs", ("pair", "level", "group", "unit", "role", "prose", "comparator",
                                                     "ratio", "used"), "C6b run ratios")
    if run_rows is not None:
        _c06b(ctx, loaded, run_rows, pkg_ds)
    _c06c(ctx, loaded)
    _c06d(ctx, loaded)


def _c06a(ctx, loaded, pkg_ds):
    for level, (ds, _, _) in loaded.items():
        bad, n, dropped = [], 0, 0
        for e in OT.ENGINES:
            for d in TRYPTIC:
                if (e, level, d) not in pkg_ds:
                    bad.append(f"{OT.NAMES[e]} {d} (no package row)")
                    continue
                p, o = _num(pkg_ds[(e, level, d)]), ds[e].get(d)
                if p is None and o is None:
                    dropped += 1
                elif p is None or o is None:
                    bad.append(f"{OT.NAMES[e]} {d} ({'package' if p is None else 'OT'} NA)")
                elif abs(p - o) > REL_TOL * abs(o):
                    bad.append(f"{OT.NAMES[e]} {d}")
                else:
                    n += 1
        if bad:
            ctx.check("FAIL", "C6a", f"{level}: {len(bad)} dataset value(s) differ from OT.load beyond 1e-12 "
                                     f"(relative): {_list(bad)}")
        elif n:
            ctx.check("PASS", "C6a", f"{level}: {n} dataset values equal OT.load within 1e-12 (relative); {dropped} "
                                     "dropped in both")
        else:
            ctx.check("INFO", "C6a", f"{level}: no dataset value to compare; all {dropped} dropped in both (OT:118-120)")


def _c06b(ctx, loaded, run_rows, pkg_ds):
    for level, (ds, rows, _) in loaded.items():
        ot_runs = {(r[0], r[1], r[2], r[3]): r[4] for r in rows}
        ot_dsv = OrderedDict(((r[0], r[2]), r[5]) for r in rows)
        pkg = {}
        for row in run_rows:
            e = _comparator(row["pair"])
            g = row["group"]
            if row["level"] != level or e not in OT.ENGINES or g not in TRYPTIC or row["role"] == "decision":
                continue
            if not _yes(row["used"]):
                continue
            p, q = _int(row["prose"]), _int(row["comparator"])
            value = p / q if p is not None and q else _num(row["ratio"])  # ints divided as OT:117
            pkg[(OT.NAMES[e], design.side(g), g, row["unit"])] = "NA" if value is None else f"{value:.6f}"
        only_ot = sorted(set(ot_runs) - set(pkg))
        only_pkg = sorted(set(pkg) - set(ot_runs))
        differ = sorted(k for k in set(ot_runs) & set(pkg) if ot_runs[k] != pkg[k])
        if only_ot or only_pkg or differ:
            ctx.check("FAIL", "C6b", f"{level}: run ratios against OT's rows: {len(only_ot)} only in OT"
                                     f"{': ' + _list(' '.join(k) for k in only_ot) if only_ot else ''}; "
                                     f"{len(only_pkg)} only in O02_pairs_runs"
                                     f"{': ' + _list(' '.join(k) for k in only_pkg) if only_pkg else ''}; "
                                     f"{len(differ)} strings differ"
                                     f"{': ' + _list(' '.join(k) for k in differ) if differ else ''}")
        elif ot_runs:
            ctx.check("PASS", "C6b", f"{level}: {len(ot_runs)} run ratios equal OT's strings (6 decimals)")
        else:
            ctx.check("INFO", "C6b", f"{level}: no run ratio in OT's rows nor in O02_pairs_runs (used)")
        if pkg_ds is None or not ot_dsv:
            continue
        rounding, bad = [], []
        for (name, d), text in ot_dsv.items():
            e = next(x for x in OT.ENGINES if OT.NAMES[x] == name)
            p = _num(pkg_ds.get((e, level, d)))
            if p is not None and f"{p:.6f}" == text:
                continue
            o = ds[e].get(d)
            if p is not None and o is not None and abs(p - o) <= REL_TOL * abs(o):
                rounding.append(f"{name} {d}")
            else:
                bad.append(f"{name} {d}")
        if bad:
            ctx.check("FAIL", "C6b", f"{level}: {len(bad)} dataset_value string(s) differ from OT's: {_list(bad)}")
        else:
            ctx.check("PASS", "C6b", f"{level}: {len(ot_dsv) - len(rounding)} dataset_value strings equal OT's")
        if rounding:
            ctx.check("INFO", "C6b", f"{level}: rounding boundary in {len(rounding)} dataset_value string(s) (floats "
                                     f"within 1e-12): {_list(rounding)}")


def _c06c(ctx, loaded):
    if not ctx.work:
        ctx.check("INFO", "C6c", "SKIP: no work folder (--work), no W/overtuning_<level>.tsv to compare")
        return
    for level, (ds, rows, _) in loaded.items():
        name = f"overtuning_{level}.tsv"
        path = os.path.join(ctx.work, name)
        if not os.path.exists(path):
            if OT.side_leads(ds) is None:  # overtuning.py cannot run on this input (OT:53-54): no file expected
                ctx.check("INFO", "C6c", f"SKIP {level}: no W/{name}; OT.rule cannot run on this input (C25)")
            else:
                ctx.check("WARN", "C6c", f"{level}: W/{name} missing (the kept output of overtuning.py, "
                                         "DS:1072-1074)", strict=True)
            continue
        with open(path, encoding="utf-8") as f:
            lines = f.read().splitlines()
        want = ["\t".join(r) for r in rows]
        older = _older(ctx, name, "counts.tsv")
        age = "; also older than counts.tsv (C18)" if older else ""
        if lines[:1] == [OT_HEADER] and lines[1:] == want:
            ctx.check("PASS", "C6c", f"{level}: W/{name} == OT's {len(want)} rows as strings")
            if older:  # OPEN Q61 / SPEC 3.5: older than counts.tsv -> WARN only (not strict); the content decides
                ctx.check("WARN", "C6c", f"{level}: W/{name} older than counts.tsv (C18); its rows equal OT's, so WARN "
                                         "only, not strict (OPEN Q61)")
            continue
        got = lines[1:]
        only_file = [x for x in got if x not in set(want)]
        only_ot = [x for x in want if x not in set(got)]
        what = ("header differs; " if lines[:1] != [OT_HEADER] else "") + \
               f"{len(only_file)} row(s) only in the file, {len(only_ot)} only in OT's rows" + \
               ("; the same rows in another order or repeated" if not only_file and not only_ot else "")
        ctx.check("WARN", "C6c", f"{level}: W/{name} differs from OT's rows: {what}{age}", strict=True)


def _c06d(ctx, loaded):
    numbers = {n.key.lower(): n.value for n in ctx.numbers}
    summary = ctx.results.get("O02_pairs_summary")
    if summary is None:
        ctx.check("INFO", "C6d", "SKIP O2 leads: table O02_pairs_summary absent (not written by this build)")
    elif any(c not in ctx.result_columns["O02_pairs_summary"] for c in ("pair", "level", "scope", "lead_pct")):
        ctx.check("FAIL", "C6d", "table O02_pairs_summary lacks a column of pair, level, scope, lead_pct (SPEC 3)")
        summary = None
    for level, (ds, _, _) in loaded.items():
        guard = OT.side_leads(ds) is None
        sides = ctx.results.get(f"O04_overtuning_{level}_sides")
        bad, n, n_na, absent = [], 0, 0, []
        for e in OT.ENGINES:
            lt, lh = _ot_leads(ds, e)
            for scope, ot_value in (("tuning", lt), ("heldout", lh)):
                cands = []
                if summary is not None:
                    vals = [r["lead_pct"] for r in summary
                            if r["level"] == level and r["scope"] == scope and _comparator(r["pair"]) == e]
                    if vals:
                        cands += [("O02_pairs_summary", v) for v in vals]
                    else:
                        absent.append(f"O02_pairs_summary {scope} {e}")
                key = f"ids.{scope}.{level}.{e}.lead"
                if key in numbers:
                    cands.append((key, numbers[key]))
                else:
                    absent.append(key)
                if sides is not None:
                    col = "L_T" if scope == "tuning" else "L_H"
                    cands += [(f"O04_overtuning_{level}_sides {col}", r.get(col)) for r in sides
                              if _comparator(r.get("comparator")) == e]
                key = f"overtuning.{level}.{'lt' if scope == 'tuning' else 'lh'}_{e}"
                if key in numbers:
                    cands.append((key, numbers[key]))
                for src, v in cands:
                    p = _num(v)
                    if p is None and ot_value is None:
                        n_na += 1
                        continue
                    n += 1
                    if p is None or ot_value is None or abs(p - ot_value) > PP_TOL:
                        bad.append(f"{src} {scope} {e}")
        if sides is None and not guard:
            ctx.check("INFO", "C6d", f"SKIP {level} O4 values: table O04_overtuning_{level}_sides absent (not written "
                                     "by this build)")
        if bad:
            ctx.check("FAIL", "C6d", f"{level}: {len(bad)} lead(s) differ from OT's L_T/L_H beyond 1e-9 points: "
                                     f"{_list(bad)}")
        elif n:
            ctx.check("PASS", "C6d", f"{level}: {n} leads (O2 equal weight, O4, numbers) equal OT's L_T/L_H within "
                                     f"1e-9 points{f'; {n_na} NA in both' if n_na else ''}"
                                     f"{f'; absent: {_list(absent, 4)}' if absent else ''}")
        elif n_na:
            ctx.check("INFO", "C6d", f"{level}: no lead to compare: {n_na} NA in the package and in OT (a side "
                                     "without datasets, C25)")
        else:
            ctx.check("INFO", "C6d", f"SKIP {level}: no O2/O4 lead to compare (absent: {_list(absent, 4)})")


# ---------------------------------------------------------------- C7-C10: counts
def c07_td_rows(ctx, exp, state):
    """C7: td rows have entrapment == 0 and te_ratio == 1 (no ENTRAP_ protein in a td database; EE-lib:135 returns 1
    without entrapment peptides)."""
    td = [r for r in ctx.counts if r.design == "td"]
    bad = [f"{_key((r.engine, r.benchmark, r.run, r.database))}/{r.level}" for r in td
           if r.entrapment != 0 or r.te_ratio != 1.0]
    if bad:
        ctx.check("FAIL", "C7", f"{len(bad)} td row(s) with entrapment != 0 or te_ratio != 1: {_list(bad)}")
    else:
        ctx.check("PASS", "C7", f"{len(td)} td rows: entrapment 0, te_ratio 1")


def c08_fdp_columns(ctx, exp, state):
    """C8: the FDP columns as EntrapmentEvaluator computes them (EE-lib:30-34, 85-99) and prints them with 4
    significant digits (EE-tool:188-194):
      |combined - N_E/N (1 + T/E)| <= h(combined) + (N_E/N) h(te_ratio) + 1e-12,
      |lower_bound - N_E/N| <= h(lower_bound) + 1e-12,
    with h(v) = 0.5 10^(floor(log10|v|) - 3), h(0) = 0, both 0 when N = 0 (EE-lib:32, 86); paired_fdp NA exactly on
    psm rows and on td/natural/arath peptide rows (SPEC C8; T29). The tolerance is defined once, in fdp.py
    (fdp.c8_combined_ok, fdp.c8_lower_ok), and used here."""
    from . import fdp  # imported here, so that an error in fdp.py fails C8 only (module contract)
    bad_comb, bad_lower, bad_paired = [], [], []
    for r in ctx.counts + ctx.counts_rule11b:
        name = f"{_key((r.engine, r.benchmark, r.run, r.database))}/{r.level}"
        if not fdp.c8_combined_ok(r):
            bad_comb.append(name)
        if not fdp.c8_lower_ok(r):
            bad_lower.append(name)
        if r.design != "rule11b":
            na_expected = r.level == "psm" or r.design in ("td", "natural", "arath")
            if na_expected != (r.paired_fdp is None):
                bad_paired.append(name)
    if bad_comb or bad_lower or bad_paired:
        ctx.check("FAIL", "C8", f"{len(bad_comb)} row(s) with combined_fdp != N_E/N(1+T/E) beyond the printing "
                                f"tolerance{': ' + _list(bad_comb) if bad_comb else ''}; {len(bad_lower)} with "
                                f"lower_bound_fdp != N_E/N{': ' + _list(bad_lower) if bad_lower else ''}; "
                                f"{len(bad_paired)} with paired_fdp NA where a value is expected or the reverse"
                                f"{': ' + _list(bad_paired) if bad_paired else ''}")
    else:
        ctx.check("PASS", "C8", f"{len(ctx.counts) + len(ctx.counts_rule11b)} rows: combined_fdp and lower_bound_fdp "
                                "recompute within half a unit of the 4th significant digit; paired_fdp NA exactly on "
                                "psm rows and td/natural/arath peptide rows")


def c09_realisations(ctx, exp, state):
    """C9: per (engine, unit) with the engine expected (SPEC 2.1: Sage only on by units), the shuffled realisations
    s1-s3 are counted, else WARN(s) listing the missing ones (SPEC 3.2 O11 "Missing realisation")."""
    missing, n_pairs = [], 0
    for u in ctx.units:
        stems = u.stems_of("shuffled")
        if not stems:
            continue
        for e in u.expected:
            n_pairs += 1
            lacking = []
            for s in stems:
                why = ctx.search_reason(e, "per_file", u.name, s)
                if why is not None:
                    r = u.design_of(s)[1]
                    lacking.append(f"{'s' + str(r) if r else s} {why}")
            if lacking:
                missing.append(f"{e} {u.name} ({', '.join(lacking)})")
    if missing:
        ctx.check("WARN", "C9", f"{len(missing)} of {n_pairs} (engine, unit) pairs lack shuffled realisations: "
                                f"{_list(missing)}", strict=True)
    else:
        ctx.check("PASS", "C9", f"all {n_pairs} (engine, unit) pairs with an expected engine counted every shuffled "
                                "realisation (Sage on bycz units not expected)")


def c10_low_memory(ctx, exp, state):
    """C10: per sample, the low_memory arm gives the standard counts at every level (prose, td; DS:988), else WARN.
    No blind sealing (lead's decision of 2026-11-24)."""
    units = list(OrderedDict.fromkeys(
        c.unit.name for c in ctx.coverage if c.engine == "prose" and c.benchmark == "per_file_low_memory"
        and c.design == "td" and c.unit is not None))
    if not units:
        ctx.check("INFO", "C10", "no per_file_low_memory search in coverage")
        return
    same, differ, missing = 0, [], []
    for name in units:
        for level in ctx.levels:
            std = ctx.accepted("prose", name, level)
            low = ctx.accepted("prose", name, level, benchmark="per_file_low_memory")
            if isinstance(std, T.Missing) or isinstance(low, T.Missing):
                which = "standard" if isinstance(std, T.Missing) else "low_memory"
                why = std.reason if isinstance(std, T.Missing) else low.reason
                missing.append(f"{name} {level} ({which} {why})")
            elif std == low:
                same += 1
            else:
                differ.append(f"{name} {level}")
    if differ:
        ctx.check("WARN", "C10", f"low_memory counts differ from the standard counts in {len(differ)} of "
                                 f"{len(units) * len(ctx.levels)} sample-levels (DS:988): {_list(differ)}")
    if missing:
        ctx.check("WARN", "C10", f"{len(missing)} sample-level(s) not comparable: {_list(missing)}")
    if not differ and not missing:
        ctx.check("PASS", "C10", f"low_memory counts == standard counts on {len(units)} samples x "
                                 f"{len(ctx.levels)} level(s) (DS:988)")


# ---------------------------------------------------------------- C11-C13: arms, threads, scaling, versions
def c11_batch_threads(ctx, exp, state):
    """C11: batch groups == the SPEC 2.1 list (17; 16 for Sage, B:974-977); a batch search per expected engine and
    group in coverage, WARN(s); one thread count across per_file, the per_file arms and batch (the used attempts;
    DS:657, 1015), equal to --expect-threads when given (strict default 16), WARN(s) (T30)."""
    groups = list(ctx.batch_groups)
    if ctx.design_mode == "paper":
        want = list(exp["batch_groups"])
        if set(groups) != set(want):
            ctx.check("FAIL", "C11", f"batch groups of the run table differ from SPEC 2.1: only in the run table "
                                     f"{_list(sorted(set(groups) - set(want))) or 'none'}; missing "
                                     f"{_list(sorted(set(want) - set(groups))) or 'none'}")
        else:
            n_sage = sum(1 for g in ctx.batch_groups.values() if "sage" in g.expected)
            ctx.check("PASS", "C11", f"{len(groups)} batch groups as SPEC 2.1 ({n_sage} for Sage)")
    else:
        ctx.check("INFO", "C11", f"--design none: {len(groups)} batch group(s) from the run table, list not compared")
    lacking = []
    for e in design.ENGINES:
        have = {c.run for c in ctx.coverage if c.engine == e and c.benchmark == "batch"}
        lacking += [(e, "batch", g.name) for g in ctx.batch_groups.values() if e in g.expected and g.name not in have]
    extra = [(c.engine, "batch", c.run) for c in ctx.coverage
             if c.benchmark == "batch" and c.engine not in ctx.batch_groups[c.run].expected]
    if lacking or extra:
        ctx.check("WARN", "C11", f"batch searches: {len(lacking)} expected but absent from coverage"
                                 f"{' (' + _by(lacking) + '): ' + _list(map(_key, lacking)) if lacking else ''}; "
                                 f"{len(extra)} for an engine not expected"
                                 f"{': ' + _list(map(_key, extra)) if extra else ''}", strict=True)
    else:
        per = Counter(c.engine for c in ctx.coverage if c.benchmark == "batch")
        ctx.check("PASS", "C11", "a batch search per expected engine and group (" +
                  ", ".join(f"{e} {per.get(e, 0)}" for e in design.ENGINES) + ")")
    timings = [(k, t) for k, t in ctx.timings.items()
               if (k[1] == "batch" or k[1].startswith("per_file")) and t.attempt is not None]
    if not timings:
        ctx.check("INFO", "C11", "no per_file, arm or batch timing")
        return
    threads = Counter(t.threads for _, t in timings)
    expect = ctx.expect_threads
    if len(threads) > 1 or (expect is not None and set(threads) != {expect}):
        main = expect if expect is not None else threads.most_common(1)[0][0]
        others = [f"{_key(k)} ({t.threads})" for k, t in timings if t.threads != main]
        ctx.check("WARN", "C11", "threads of per_file, arms and batch: " +
                  ", ".join(f"{n} keys at {th}" for th, n in sorted(threads.items())) +
                  (f"; expected {expect} (--expect-threads)" if expect is not None else "") +
                  f": {_list(others)}", strict=True)
    else:
        th = next(iter(threads))
        ctx.check("PASS", "C11", f"all {len(timings)} per_file, arm and batch timings at {th} threads"
                                 f"{' (--expect-threads)' if expect is not None else ''}")


def c12_scaling(ctx, exp, state):
    """C12: thread scaling (SPEC 2.4, 2.5, O17; B:983-1001). Repetition 0 only at the top grid point (B:994,
    warm=(i==0)); after over_limit at n every lower point is not_run_over_limit, stage all, repetition 1, without a
    coverage row (B:996-999, 1360-1363), and no not_run_over_limit point stands without an over_limit point above it
    (FAIL otherwise); per run the grid sets of the engines with scaling rows are identical (WARN(s)). over_limit and
    not_run_over_limit points, and an expected engine without scaling rows: INFO; scaling rows of a run not flagged
    in the run table: WARN (B:986)."""
    rows_by_key = OrderedDict()
    for r in ctx.timing_rows:
        if r.benchmark == "scaling":
            rows_by_key.setdefault((r.engine, r.run, r.threads), []).append(r)
    points = OrderedDict()  # (engine, run) -> {threads: [Timing or None, CoverageRow or None]}
    for k, t in ctx.timings.items():
        if k[1] == "scaling":
            points.setdefault((k[0], k[2]), {}).setdefault(k[4], [None, None])[0] = t
    for c in ctx.coverage:
        if c.benchmark == "scaling":
            points.setdefault((c.engine, c.run), {}).setdefault(c.threads, [None, None])[1] = c
    if not points:
        ctx.check("INFO", "C12", "no scaling rows")
    bad, over, not_run = [], [], []
    for (e, run), pts in points.items():
        top = max(pts)
        seen_over = None
        for n in sorted(pts, reverse=True):
            t, c = pts[n]
            name = f"{e}/{run}/t{n}"
            if n != top and t is not None and t.attempt is not None \
                    and any(r.repetition == 0 for r in t.attempt.rows):
                bad.append(f"{name}: repetition 0 below the top point t{top}")
            is_over = (t is not None and t.state == "over_limit") or (c is not None and c.state == "over_limit")
            if t is not None and t.state == "not_run_over_limit":
                not_run.append(name)
                if seen_over is None:
                    bad.append(f"{name}: not_run_over_limit without an over_limit point above")
                if c is not None:
                    bad.append(f"{name}: not_run_over_limit with a coverage row")
                marks = [r for r in rows_by_key.get((e, run, n), []) if r.exit == "not_run_over_limit"]
                if any(r.stage != "all" or r.repetition != 1 for r in marks):
                    bad.append(f"{name}: not_run_over_limit row not stage all, repetition 1")
            elif seen_over is not None:
                bad.append(f"{name}: run below the over_limit point t{seen_over}")
            if is_over:
                over.append(name)
                if seen_over is None:
                    seen_over = n
    if bad:
        ctx.check("FAIL", "C12", f"{len(bad)} scaling point(s) break the driver's rules: {_list(bad)}")
    elif points:
        tops = sorted({f"t{max(p)}" for p in points.values()})
        ctx.check("PASS", "C12", f"{len(points)} (engine, run) grids: repetition 0 only at the top point "
                                 f"({', '.join(tops)}); not_run_over_limit only below an over_limit point")
    runs = OrderedDict()
    for (e, run), pts in points.items():
        runs.setdefault(run, OrderedDict())[e] = tuple(sorted(pts, reverse=True))
    for run, grids in runs.items():
        u = ctx.unit_of_run.get(run)
        expected = u.expected if u is not None else design.ENGINES
        without = [e for e in expected if e not in grids]
        if len(set(grids.values())) > 1:
            ctx.check("WARN", "C12", f"{run}: the grids differ between engines: " +
                      "; ".join(f"{e} {','.join(map(str, g))}" for e, g in grids.items()), strict=True)
        else:
            grid = next(iter(grids.values()))
            ctx.check("PASS", "C12", f"{run}: the same grid for {', '.join(grids)}: {','.join(map(str, grid))} "
                                     "threads")
        if without:
            ctx.check("INFO", "C12", f"{run}: no scaling rows for {', '.join(without)}")
    if over or not_run:
        ctx.check("INFO", "C12", f"over_limit (lower bound only, SPEC 2.5): {_list(over) or 'none'}; "
                                 f"not_run_over_limit (NA, DS:669): {_list(not_run) or 'none'}")
    if ctx.unflagged_scaling:
        keys = sorted({(c.engine, c.run) for c in ctx.unflagged_scaling})
        ctx.check("WARN", "C12", f"scaling rows of {len(keys)} (engine, run) not flagged scaling == 1 in the run table "
                                 f"(B:986): {_list('/'.join(k) for k in keys)}")


def _versions(ctx, label, entries, rules, need_msbooster):
    """C13 on one versions.txt: every tool of the rules has exactly one line, and its text holds the required string."""
    if entries is None:
        ctx.check("WARN", "C13", f"no {label}/versions.txt (B:346-357)", strict=True)
        return
    bad, ok = [], []
    for tool, pattern, required in rules:
        lines = [text for cmd, text in entries if re.search(pattern, cmd)]
        if len(lines) != 1:
            bad.append(f"{tool}: {len(lines)} lines")
        elif required not in lines[0]:
            bad.append(f"{tool}: '{required}' not found")
        else:
            ok.append(tool)
    if need_msbooster and not any("msbooster" in (cmd + " " + text).lower() for cmd, text in entries):
        ctx.check("WARN", "C13", f"{label}/versions.txt: no MSBooster line although the msbooster arm ran (O21; "
                                 "B:347-349)")
    if bad:
        ctx.check("FAIL", "C13", f"{label}/versions.txt: {_list(bad)}")
    else:
        ctx.check("PASS", "C13", f"{label}/versions.txt: {', '.join(ok)} as required "
                                 f"({'; '.join(r for _, _, r in rules)})")


def c13_versions(ctx, exp, state):
    """C13: W/versions.txt and S/versions.txt (B:357): ProSE, FileConverter and EntrapmentEvaluator 'Revision: b2d252b'
    (the paper build P), 'sage 0.14.6' (DS:729), 'MSFragger-4.4.1', 'Percolator version 3.09'; MSBooster when the
    msbooster arm ran (O21). A missing file: WARN(s); a missing or other version: FAIL."""
    need = "msbooster" in ctx.tags
    separate = ctx.scaling_versions is not ctx.versions
    _versions(ctx, "W" if separate else "W (= S)", ctx.versions, exp["versions"], need)
    if separate:
        _versions(ctx, "S", ctx.scaling_versions, exp["versions"], False)


# ---------------------------------------------------------------- C14-C16: design
def c14_mzml_counts(ctx, exp, state):
    """C14: mzml_counts.tsv holds every run id of the run table; the MS2 spectra of the tuned runs sum to 1,509,392
    (DS:16). Skipped with --design none."""
    if ctx.design_mode != "paper":
        ctx.check("INFO", "C14", "SKIP: --design none")
        return
    if ctx.mzml_counts is None:
        ctx.check("WARN", "C14", "no mzml_counts.tsv (--mzml-counts)")
        return
    missing = [r.id for r in ctx.runs if r.id not in ctx.mzml_counts]
    tuned = [r.id for r in ctx.runs if r.role == "tuned" and r.id in ctx.mzml_counts]
    total = sum(ctx.mzml_counts[i]["ms2"] for i in tuned)
    if missing:
        ctx.check("FAIL", "C14", f"{len(missing)} run id(s) missing in mzml_counts.tsv: {_list(missing)}")
    if total != exp["ms2_tuned"]:
        ctx.check("FAIL", "C14", f"the MS2 spectra of the {len(tuned)} tuned runs do not sum to {exp['ms2_tuned']} "
                                 "(DS:16)")
    if not missing and total == exp["ms2_tuned"]:
        ctx.check("PASS", "C14", f"mzml_counts.tsv holds all {len(ctx.runs)} run ids; the MS2 spectra of the "
                                 f"{len(tuned)} tuned runs sum to {exp['ms2_tuned']} (DS:16)")


def c15_design(ctx, exp, state):
    """C15: the design (SPEC 2.2): groups of the run table within design.py; TUNING/HELDOUT equal OT's (OT:26-28); the
    role=decision runs equal the DS:998 list; the non-decision runs per tryptic dataset equal DS:860-878 "Runs used".
    Skipped with --design none; the tests pass the fixture's expected values."""
    if ctx.design_mode != "paper":
        ctx.check("INFO", "C15", "SKIP: --design none")
        return
    problems = []
    unknown = sorted({r.group for r in ctx.runs} - set(design.ALL_GROUPS))
    if unknown:
        problems.append(f"groups outside design.py: {_list(unknown)}")
    if tuple(design.TUNING) != tuple(OT.TUNING) or tuple(design.HELDOUT) != tuple(OT.HELDOUT):
        problems.append("design.TUNING/HELDOUT differ from overtuning.py")
    decision = {r.id for r in ctx.runs if r.role == "decision"}
    want = set(exp["decision"])
    if decision != want:
        problems.append(f"role=decision differs from DS:998: only in the run table "
                        f"{_list(sorted(decision - want)) or 'none'}; missing {_list(sorted(want - decision)) or 'none'}")
    used = Counter(r.group for r in ctx.runs if r.role != "decision")
    wrong = [f"{g} {used.get(g, 0)} (DS {n})" for g, n in exp["runs_used"].items() if used.get(g, 0) != n]
    if wrong:
        problems.append(f"non-decision runs per dataset differ from DS:860-878: {_list(wrong)}")
    if problems:
        ctx.check("FAIL", "C15", "; ".join(problems))
    else:
        ctx.check("PASS", "C15", f"{len({r.group for r in ctx.runs})} groups within design.py; TUNING/HELDOUT == OT; "
                                 f"{len(decision)} decision runs as DS:998; runs used per dataset as DS:860-878 "
                                 f"({sum(exp['runs_used'].values())} runs)")


def c16_sets(ctx, exp, state):
    """C16: the comparison sets (SPEC 2.7): R3 within R(pair) for each pair and level; no decision unit in R, R3, F,
    T, T3; B3 holds batch groups only (a decision run stays inside its batch, OPEN Q24). With O02_pairs_runs: on the
    tryptic groups its rows marked used are exactly R(pair, level) among the units it lists, and no decision unit is
    used."""
    bad, n = [], 0
    for level in ctx.levels:
        r3 = {u.name for u in ctx.R3(level)}
        if any(ctx.unit(x).is_decision for x in r3):
            bad.append(f"R3 {level} holds a decision unit")
        for pair in design.PAIRS:
            rp = {u.name for u in ctx.R(pair, level)}
            n += 1
            if not r3 <= rp:
                bad.append(f"R3 {level} not within R({'/'.join(pair)}): {_list(sorted(r3 - rp), 3)}")
            if any(ctx.unit(x).is_decision for x in rp):
                bad.append(f"R({'/'.join(pair)}) {level} holds a decision unit")
        for d in ("shuffled", "natural", "arath"):
            if any(ctx.unit(x).is_decision for x in ctx.F(level, d)):
                bad.append(f"F {level} {d} holds a decision unit")
    for name, units in [(f"T({'/'.join(p)})", ctx.T(p)) for p in design.PAIRS] + [("T3", ctx.T3())]:
        if any(u.is_decision for u in units):
            bad.append(f"{name} holds a decision unit")
    b3 = ctx.B3()
    if any(g not in ctx.batch_groups for g in b3):
        bad.append("B3 names a group that is no batch group")
    rows = ctx.results.get("O02_pairs_runs")
    note = ""
    if rows is None:
        ctx.check("INFO", "C16", "SKIP O2 cross-check: table O02_pairs_runs absent (not written by this build)")
    elif any(c not in ctx.result_columns["O02_pairs_runs"] for c in ("pair", "level", "group", "unit", "used")):
        bad.append("O02_pairs_runs lacks a column of pair, level, group, unit, used")
    else:
        checked = 0
        for level in ctx.levels:
            for pair in design.PAIRS:
                sel = [r for r in rows if r["level"] == level and _comparator(r["pair"]) == pair[1]
                       and r["group"] in TRYPTIC]
                listed = {r["unit"] for r in sel}
                used = {r["unit"] for r in sel if _yes(r["used"])}
                want = {u.name for u in ctx.R(pair, level)} & listed
                checked += len(sel)
                if used != want:
                    bad.append(f"O02_pairs_runs {level} {'/'.join(pair)}: used {len(used)} != R {len(want)} "
                               f"({_list(sorted(used ^ want), 3)})")
                if any(x in ctx.unit_by_name and ctx.unit(x).is_decision for x in used):
                    bad.append(f"O02_pairs_runs {level} {'/'.join(pair)} uses a decision unit")
        note = f"; O02_pairs_runs: {checked} tryptic rows, used == R"
    if bad:
        ctx.check("FAIL", "C16", f"{len(bad)} comparison-set violation(s): {_list(bad)}")
    else:
        ctx.check("PASS", "C16", f"R3 within R for {n} (pair, level); no decision unit in R, R3, F, T, T3; B3 "
                                 f"{len(b3)} batch group(s){note}")


# ---------------------------------------------------------------- C17-C20: databases, inputs, numbers, grades
def c17_databases(ctx, exp, state):
    """C17: the timing database is the unit's/group's/run's td (SPEC 2.5; the loader stops otherwise, so this counts
    them); the coverage database of batch is the group's td and of scaling the run's td + _t<n> (SPEC 2.4): the
    loader puts other batch/scaling rows outside the design, FAIL here."""
    bad = [(c.engine, c.benchmark, c.run, c.database) for c in ctx.coverage_outside if c.scope in ("batch", "scaling")]
    if bad:
        ctx.check("FAIL", "C17", f"{len(bad)} batch/scaling coverage row(s) whose database is not the td: "
                                 f"{_list(map(_key, bad))}")
    else:
        n_cov = sum(1 for c in ctx.coverage if c.scope in ("batch", "scaling"))
        ctx.check("PASS", "C17", f"{len(ctx.timing_rows)} timing rows and {n_cov} batch/scaling coverage rows on the "
                                 "unit's/group's/run's td")


def c18_inputs(ctx, exp, state):
    """C18: W/overtuning_<level>.tsv older than counts.tsv -> INFO (collect rewrites counts.tsv after later stages,
    SPEC 9 R1-19); the non-strict WARN of OPEN Q61 for such a file is C6c's. On copies the mtimes are the copy time, so
    --listing (e.g. work.ls) is read instead."""
    if not ctx.work:
        ctx.check("INFO", "C18", "SKIP: no work folder")
        return
    source = "--listing" if ctx.listing is not None else "mtimes"
    for level in design.LEVELS:
        name = f"overtuning_{level}.tsv"
        if _age(ctx, name) is None:
            ctx.check("INFO", "C18", f"no W/{name}")
            continue
        older = _older(ctx, name, "counts.tsv")
        if older is None:
            ctx.check("INFO", "C18", f"W/{name}: age not comparable with counts.tsv ({source})")
        elif older:
            text = ""
            if ctx.listing is not None and name in ctx.listing and "counts.tsv" in ctx.listing:
                text = f": {ctx.listing[name]['text']} < {ctx.listing['counts.tsv']['text']}"
            ctx.check("INFO", "C18", f"W/{name} older than counts.tsv ({source}{text}); its content is compared by "
                                     "C6c (WARN there, OPEN Q61)")
        else:
            ctx.check("INFO", "C18", f"W/{name} not older than counts.tsv ({source})")


def c19_numbers(ctx, exp, state):
    """C19: numbers.tsv (SPEC 3.8; OPEN Q59, Q62): every identification-ratio key (ids., three., cal., percolator.,
    prediction., and the O13 leads fdp.matched., tables.ID_RATIO_FAMILIES) with main_text_allowed = yes has
    source_side = heldout (overtuning.* is another family, exempt, DS:894, 903); no own-set value is a key."""
    if not ctx.numbers:
        ctx.check("INFO", "C19", "no numbers.tsv key")
        return
    idr = [x for x in ctx.numbers if x.key.startswith(T.ID_RATIO_FAMILIES)]
    bad = [x.key for x in idr if x.main_text_allowed == "yes" and x.source_side != "heldout"]
    own = [x.key for x in ctx.numbers if re.search(r"(^|[._])own([._]|$)", x.key)]
    if bad or own:
        ctx.check("FAIL", "C19", f"{len(bad)} identification-ratio key(s) allowed in the main text without "
                                 f"source_side heldout{': ' + _list(bad) if bad else ''}; {len(own)} own-set key(s)"
                                 f"{': ' + _list(own) if own else ''}")
    else:
        n_main = sum(1 for x in idr if x.main_text_allowed == "yes")
        ctx.check("PASS", "C19", f"{len(ctx.numbers)} keys; {len(idr)} identification-ratio keys, {n_main} allowed in "
                                 "the main text, all from held-out data; no own-set key")


def _row_group(ctx, row):
    """The group a table row belongs to: its group/dataset/left_out column, else the group of its unit/sample/run."""
    for col in ("group", "dataset", "left_out"):
        g = row.get(col)
        if isinstance(g, str) and g in ctx.groups:
            return g
    for col in ("unit", "sample", "run"):
        v = row.get(col)
        if isinstance(v, str):
            u = ctx.unit_by_name.get(v) or ctx.unit_of_run.get(v)
            if u is not None:
                return u.group
    return None


def c20_grades(ctx, exp, state):
    """C20: every row of every table with a grade column carries its dataset's grade (DS:114; SPEC 3 "Grade
    everywhere"): A/B/C on held-out rows, '-' on tuning rows, as design.GRADE; rows without a group are checked by
    their side/kind column (heldout -> A/B/C, tuning -> '-')."""
    tables = [name for name, cols in ctx.result_columns.items() if "grade" in cols]
    if not tables:
        ctx.check("INFO", "C20", "SKIP: no table with a grade column written by this build")
        return
    bad, n, unchecked = [], 0, 0
    for name in tables:
        for row in ctx.results[name]:
            g = _row_group(ctx, row)
            grade = row.get("grade")
            if g is not None:
                want = design.grade(g)
                n += 1
                if grade != want:
                    bad.append(f"{name} {g} ({grade}, expected {want})")
                continue
            side = row.get("side") if row.get("side") in ("tuning", "heldout") else row.get("kind")
            if side == "heldout":
                n += 1
                if grade not in ("A", "B", "C"):
                    bad.append(f"{name} held-out row without a grade ({grade})")
            elif side == "tuning":
                n += 1
                if grade != "-":
                    bad.append(f"{name} tuning row with grade {grade}")
            else:
                unchecked += 1
    if bad:
        ctx.check("FAIL", "C20", f"{len(bad)} row(s) with a wrong grade (DS:114): {_list(bad)}")
    else:
        ctx.check("PASS", "C20", f"{n} rows of {len(tables)} tables carry their dataset's grade ({unchecked} rows "
                                 "without a group or side, e.g. summary rows)")


# ---------------------------------------------------------------- C21-C25: references, arrangement, logs, guard
def c21_references(ctx, exp, state):
    """C21: published references (SPEC 2.2 REFERENCE_MAP; OPEN Q12, Q46, Q47). In the REF rows of the mapped groups
    and scopes every engine, level and fdr string is in the map (prefixes), every value an integer; one row per
    (sample, tool); every immuno sample of the run table gets its expected tools (design.EXPECTED_TOOLS), else FAIL.
    pxd019643's rows carry the 'local' FDR flag (OPEN Q46). Skipped with --design none; without a reference file a
    run table with immuno samples FAILs (their tools are missing), one without is skipped."""
    if ctx.design_mode != "paper":
        ctx.check("INFO", "C21", "SKIP: --design none")
        return
    path = ctx.references_path
    if not path or not os.path.exists(path):
        samples = [u.name for u in ctx.units if u.group in design.EXPECTED_TOOLS]
        if samples:
            ctx.check("FAIL", "C21", f"no reference file ({path}): {len(samples)} immuno samples without their "
                                     f"expected tools: {_list(samples)}")
        else:
            ctx.check("INFO", "C21", f"SKIP: no reference file ({path}) and no immuno sample")
        return
    try:
        _, rows = T.read_tsv(path, required=("group", "scope", "value", "level", "fdr", "engine"))
    except T.ValidationStop as err:
        ctx.check("FAIL", "C21", f"reference file unreadable: {err.message}")
        return
    bad, tools_of, n_rows, n_ignored, flagged = [], OrderedDict(), 0, 0, 0
    for entry in design.REFERENCE_MAP:
        prefix = entry["scope"].split("<sample>")[0]
        per_sample = "<sample>" in entry["scope"]
        for line, r in rows:
            if r["group"] not in entry["groups"] or not r["scope"].startswith(prefix):
                continue
            n_rows += 1
            tool = next((t for p, t in entry["engines"] if r["engine"].startswith(p)), False)
            if tool is False:
                bad.append(f"line {line}: engine string not in REFERENCE_MAP")
                continue
            if tool is None:
                n_ignored += 1
                continue
            for col in ("level", "fdr"):
                if entry[col] is not None and not r[col].startswith(entry[col]):
                    bad.append(f"line {line}: {col} string not in REFERENCE_MAP")
            if not re.fullmatch(r"\d+", r["value"].strip()):
                bad.append(f"line {line}: value not an integer")
            if entry["flag"] == "local":
                flagged += 1
            if per_sample:
                sample = r["scope"][len(prefix):].split(":")[0].strip()
                u = ctx.unit_by_name.get(sample)
                if u is None or u.group != r["group"]:
                    bad.append(f"line {line}: sample {sample} not a unit of {r['group']} in the run table")
                    continue
                if (sample, tool) in tools_of:
                    bad.append(f"line {line}: second row for {sample} {tool}")
                tools_of[(sample, tool)] = line
    lacking = [f"{u.name} {tool}" for u in ctx.units for tool in design.EXPECTED_TOOLS.get(u.group, ())
               if (u.name, tool) not in tools_of]
    if lacking:
        bad.append(f"{len(lacking)} expected reference(s) missing: {_list(lacking)}")
    if bad:
        ctx.check("FAIL", "C21", f"references ({os.path.basename(path)}): {_list(bad)}")
    else:
        n_samples = sum(1 for u in ctx.units if u.group in design.EXPECTED_TOOLS)
        ctx.check("PASS", "C21", f"{n_rows} reference rows of the mapped groups ({n_ignored} ignored by the map, "
                                 f"{flagged} flagged local FDR, OPEN Q46); all {n_samples} immuno samples have their "
                                 "expected tools")


def c22_arrangement(ctx, exp, state):
    """C22: POOLED_ARRANGEMENT is the same in the immuno parameter files (SPEC 2.2; the loader stops otherwise); with
    O9b (task 11b), it equals the arrangement the rule chose (O09b_rule11b column chosen; DS:629, 1056)."""
    if ctx.pooled_arrangement is None:
        ctx.check("INFO", "C22", "no immunopeptidomics group in the run table: no POOLED_ARRANGEMENT")
        return
    modes = {str(m) for _, m in ctx.pooled_arrangement_files}
    if len(modes) != 1 or str(ctx.pooled_arrangement) not in modes:
        ctx.check("FAIL", "C22", f"POOLED_ARRANGEMENT differs between the parameter files: {_list(sorted(modes))}")
    else:
        ctx.check("PASS", "C22", f"POOLED_ARRANGEMENT {ctx.pooled_arrangement} in all "
                                 f"{len(ctx.pooled_arrangement_files)} immuno parameter files ({design.POOLED_KEY})")
    rows = ctx.results.get("O09b_rule11b")
    if rows is None:
        if ctx.counts_rule11b or ctx.rule11b_work:
            ctx.check("INFO", "C22", "SKIP O9b: table O09b_rule11b absent (not written by this build)")
        else:
            ctx.check("INFO", "C22", "no task 11b result (O9b not built)")
        return
    cols = [c for c in ("chosen", "chosen_arrangement") if c in ctx.result_columns["O09b_rule11b"]]
    if not cols:
        ctx.check("FAIL", "C22", "table O09b_rule11b has no column chosen (SPEC 3.1 O9b)")
        return
    chosen = {str(r[cols[0]]) for r in rows if not T.is_missing(r[cols[0]]) and str(r[cols[0]]) not in ("", "-")}
    if not chosen:
        ctx.check("INFO", "C22", "O9b: no arrangement chosen")
    elif chosen != {str(ctx.pooled_arrangement)}:
        ctx.check("FAIL", "C22", f"O9b chose {_list(sorted(chosen))}, POOLED_ARRANGEMENT is "
                                 f"{ctx.pooled_arrangement} (DS:629)")
    else:
        ctx.check("PASS", "C22", f"O9b chose {ctx.pooled_arrangement} = POOLED_ARRANGEMENT")


def c23_settings(ctx, exp, state):
    """C23 (with logs): every counted MSFragger per_file* search has a row in O19_settings_msfragger with a source
    (parsed or configured, DS:691, 983), WARN(s); every counted ProSE per_file* search has one row per input file in
    O19_settings_prose (OPEN Q28), WARN."""
    if not ctx.logs_available:
        ctx.check("INFO", "C23", "SKIP: no W/out logs (the O19 settings need them)")
        return
    for engine, name, strict in (("msfragger", "O19_settings_msfragger", True), ("prose", "O19_settings_prose", False)):
        rows = _table(ctx, "C23", name, ("benchmark", "unit", "database", "source"), f"{engine} settings")
        if rows is None:
            continue
        have = Counter((r["benchmark"], r["unit"], r["database"]) for r in rows
                       if not T.is_missing(r["source"]) and str(r["source"]) not in ("", "-"))
        searches = [c for c in ctx.coverage if c.engine == engine and c.scope == "unit" and c.counted]
        lacking = []
        for c in searches:
            need = c.unit.n_files if (engine == "prose" and c.unit is not None) else 1
            if have.get((c.benchmark, c.run, c.database), 0) < need:
                lacking.append((c.engine, c.benchmark, c.run, c.database))
        if lacking:
            ctx.check("WARN", "C23", f"{len(lacking)} of {len(searches)} counted {engine} per_file* searches without "
                                     f"settings rows in {name}: {_list(map(_key, lacking))}", strict=strict)
        else:
            ctx.check("PASS", "C23", f"all {len(searches)} counted {engine} per_file* searches have settings rows in "
                                     f"{name}")


def c24_logs(ctx, exp, state):
    """C24 (with logs): each timed td folder (coverage ok) holds <stage>.r<rep>.log for every stage and repetition of
    its used attempt and no <stage>.log; a <stage>.log means the search was rerun untimed after the timed run (B:920),
    so its timing is stale_timing (NA), WARN(s) (T31). The scaling folders are read from S/out and the others from
    W/out, each only when that out/ tree exists (ctx.logs_for): a separate S without out/ gives an INFO SKIP for its
    scaling searches, not a WARN per folder."""
    if not ctx.logs_available and not ctx.scaling_logs_available:
        ctx.check("INFO", "C24", "SKIP: no W/out logs")
        return
    stale, lacking, n = [], [], 0
    skipped = {}  # base -> number of timed folders not looked at, because that base has no out/ tree
    for key, t in ctx.timings.items():
        e, b, run, db, thr = key
        if t.attempt is None or t.state not in ("complete", "stale_timing"):
            continue
        c = ctx.coverage_index.get((e, b, run, f"{db}_t{thr}" if b == "scaling" else db))
        if c is None or c.state != "ok":
            continue
        if not ctx.logs_for(b):
            base = "S/out (scaling)" if b == "scaling" else "W/out"
            skipped[base] = skipped.get(base, 0) + 1
            continue
        folder = ctx.search_dir(e, b, run, db, thr)
        n += 1
        if not folder or not os.path.isdir(folder):
            lacking.append(f"{_key(key)} (no folder)")
            continue
        names = set(os.listdir(folder))
        plain = sorted(s + ".log" for s in t.expected if s + ".log" in names)
        if plain:
            stale.append(f"{_key(key)} ({', '.join(plain)})")
        missing = sorted({f"{s}.r{r}.log" for r, rep in t.attempt.reps.items() for s in rep.stages} - names)
        if missing:
            lacking.append(f"{_key(key)} ({', '.join(missing[:3])}{' ...' if len(missing) > 3 else ''})")
    if stale or lacking:
        ctx.check("WARN", "C24", f"{len(stale)} timed folder(s) with an untimed <stage>.log (stale_timing, B:920)"
                                 f"{': ' + _list(stale) if stale else ''}; {len(lacking)} without all their "
                                 f"<stage>.r<rep>.log{': ' + _list(lacking) if lacking else ''}", strict=True)
    else:
        ctx.check("PASS", "C24", f"{n} timed folders hold <stage>.r<rep>.log for every repetition and no <stage>.log")
    for base, count in skipped.items():
        ctx.check("INFO", "C24", f"SKIP {count} timed folder(s) of {base}: no such out/ tree")


def c25_overtuning_guard(ctx, exp, state):
    """C25: O4-O7 are skipped when a side has no dataset for a comparator (OT.side_leads is None, OT:44-45; OT.rule
    would raise, OT:53-54) -> WARN(s) (SPEC 3.5 "Guard"; T27, the W_node case)."""
    if _ot_skip(ctx, "C25"):
        return
    for level, res in _ot(ctx, state).items():
        if isinstance(res, Exception):
            ctx.check("INFO", "C25", f"SKIP {level}: OT.load failed (C6)")
            continue
        ds = res[0]
        if OT.side_leads(ds) is not None:
            ctx.check("PASS", "C25", f"{level}: every side has a dataset for both comparators; O4-O7 computable")
            continue
        empty = [f"{OT.NAMES[e]} {side}" for e in OT.ENGINES
                 for side, names in (("tuning", OT.TUNING), ("held-out", OT.HELDOUT))
                 if not any(d in names for d in ds[e])]
        ctx.check("WARN", "C25", f"{level}: O4-O7 skipped: no dataset for {', '.join(empty)} (OT:44-45, 53-54)",
                  strict=True)


CHECKS = (
    ("C1", c01_key_sets), ("C2", c02_count_rows), ("C3", c03_coverage), ("C4", c04_states), ("C5", c05_timings),
    ("C6", c06_overtuning), ("C7", c07_td_rows), ("C8", c08_fdp_columns), ("C9", c09_realisations),
    ("C10", c10_low_memory), ("C11", c11_batch_threads), ("C12", c12_scaling), ("C13", c13_versions),
    ("C14", c14_mzml_counts), ("C15", c15_design), ("C16", c16_sets), ("C17", c17_databases), ("C18", c18_inputs),
    ("C19", c19_numbers), ("C20", c20_grades), ("C21", c21_references), ("C22", c22_arrangement),
    ("C23", c23_settings), ("C24", c24_logs), ("C25", c25_overtuning_guard),
)


def run(ctx, expected=None):
    """Runs C1-C25 on ctx in order. expected: values replacing PAPER (the tests' fixture design, SPEC 6).
    A check that raises gives 'FAIL <id> check raised ...' and the others go on; the tracebacks are written to
    <out>/errors_checks.txt (empty without an error). A ValidationStop propagates (exit 2, module contract).
    Returns the list of tracebacks."""
    exp = dict(PAPER)
    exp.update(expected or {})
    state, errors = {}, []
    for cid, func in CHECKS:
        try:
            func(ctx, exp, state)
        except T.ValidationStop:
            raise
        except Exception as err:
            ctx.check("FAIL", cid, f"check raised {err.__class__.__name__}: {err} (traceback in errors_checks.txt)")
            errors.append(f"== check {cid} ({func.__name__})\n{traceback.format_exc()}")
    ctx.write_file("errors_checks.txt", "\n".join(errors) + ("\n" if errors else ""))
    return errors
