"""Identification outputs (SPEC v2 sections 3.1, 3.5, 3.6): O1, O2, O3, the over-tuning glue O4, O6, O7 with its
sentences, O8, O9, O9b, the counts part of O10, O14, O23, O24, O25 and O27 (the sensitivity value of the decision
runs, DATASETS.md 4.6, amendment of 2026-11-28; beyond the SPEC's outputs). The checks on these outputs (C6 over-tuning
against overtuning.py, C21 published references, C25 over-tuning skipped, C10, C16, C22) are checks.py's (SPEC 5): this
module writes no PASS or FAIL line of its own, only INFO lines with the ids O04, O09b and O25, and WARN lines
O25 on the coverage of a declared arm (design.TABLE_ARMS; _declared_coverage).

Citation keys as in the SPEC: DS = datasets/DATASETS.md, B = benchmarks/bench.py, OT = benchmarks/overtuning.py,
REF = datasets/reference_ids.tsv, EE-lib = EntrapmentEvaluation.cpp, RA = the engine-node trial runner.

Conventions
- Main selection (SPEC 3 "Common rules"): benchmark per_file, database = the unit's td, the levels of ctx.levels.
- Every value is a number or T.Missing(reason) (SPEC 2.6); the tables write NA and say why in their note columns.
- Comparison sets are those of SPEC 2.7 (ctx.R, ctx.R3, ctx.C, ctx.F). Decision runs are shown in the per-run tables
  and enter no summary (DS:96, 858, 998; DATASETS.md 4.6, amendment of 2026-11-28). The one exception is O27, which
  counts them to show how far they would move the leads (write_o27). No identification lead, mean or median outside
  O27 uses them; the per-run tables, O9b (the DN13 class I pools), O14's search counts and O23 list them.
- Per dataset: geometric mean of the per-run ratios; across datasets: geometric mean with equal weight, the
  run-weighted value and the ratio of sums next to it (DS:624, 997; OPEN Q2, Q3). Floats are summed with math.fsum
  (inside T.gmean / T.sum_ratio / T.fmean); integer counts with sum (exact).
- Per-run tables are in design order (design.order_key of the group, then run-table order); per-dataset tables in
  design order (FIGURE_ORDER, ELECTRON_ORDER, IMMUNO_ORDER, then other groups).
- Floats are written with 6 decimals (T.FMT_RATIO), leads included; numbers.tsv texts give leads with 1 decimal.

Data passed to other modules (ctx.shared)
- 'O10_counts': [row dict] the counts part of O10, the C10 data (timing.py writes the joint O10_low_memory.tsv).
- 'overtuning': {level: {'ds', 'rows', 'notes', 'version', 'best', 'full', 'loo', 'n_t', 'n_h', 'skipped'}}.
- 'references': the parsed REFERENCE_MAP rows, see read_references (None without a reference file).
- 'rule11b_chosen': the arrangement task 11b chose (O9b), for C22.

Data taken from other modules
- O8's FDP columns: fdp.run_of (FDP as O11, the runs cached in ctx.shared['fdp_runs']), whether or not --only fdp.
- O10 low_memory times: timing.py writes the joint table from ctx.shared['O10_counts'].
"""
import contextlib
import io
import math
import os
import re
from collections import OrderedDict

from . import design
from . import fdp
from . import tables as T

OT = design.OT
ENGINES = design.ENGINES
LEVEL_UNIT = {"psm": "PSMs", "peptide": "peptides"}  # OT:186
GRADE_SCOPES = ("heldout_grade_A", "heldout_grade_B", "heldout_grade_C")  # SPEC O2 "Scopes"; OPEN Q50
THREE_PAIRS = (("prose", "msfragger"), ("prose", "sage"), ("sage", "msfragger"))  # SPEC O3
SUMMARY_COLUMNS = ["pair", "level", "scope", "n_datasets", "n_runs", "equal_weight", "lead_pct", "run_weighted",
                   "rw_lead_pct", "sum_ratio", "sum_lead_pct", "dropped_datasets"]  # SPEC O2
FDP_DESIGN = "shuffled"  # O8: per engine its own shuffled realisations, F shared (SPEC O8)
OT_HEADER = ("engine", "side", "dataset", "run", "ratio", "dataset_value")  # OT:147
FDP_MARGIN = 0.001  # O9b: 0.1 percentage points as a fraction (DS:629)


# ================================================================ entry point
def build(ctx):
    """Writes the ids tables, sentences and numbers through ctx (module contract of summarize.py). The --only keywords
    (SPEC 1): ids (O1-O3, and O27 with --design paper), overtuning (O4-O7), electron (O8), immuno (O9), rule11b (O9b),
    lowmem (O10 counts part), coverage (O14), datasets (O23), references (O24), arms (O25). The over-tuning data
    (ctx.shared['overtuning']) are made with --design paper whatever --only says; O4-O7 are written under 'overtuning'
    (SPEC 3.5). The reference file is read (and its strings validated, a stop on violation) whenever it exists."""
    if ctx.want("ids"):
        write_o1(ctx)
        write_o2(ctx)
        write_o3(ctx)
        if ctx.design_mode == "paper":
            write_o27(ctx)
    if ctx.design_mode == "paper":
        overtuning(ctx)
    else:
        ctx.check("INFO", "O04", "over-tuning O4-O7 skipped: --design none (SPEC 1, CLI; OT.load needs the role "
                                 "column, OT:93)")
    refs = read_references(ctx)
    ctx.shared["references"] = refs
    if ctx.want("electron"):
        write_o8(ctx)
    if ctx.want("immuno"):
        write_o9(ctx, refs)
    if ctx.want("rule11b"):
        write_o9b(ctx)
    if ctx.want("lowmem"):
        o10_counts(ctx)
    if ctx.want("coverage"):
        write_o14(ctx)
    if ctx.want("datasets"):
        write_o23(ctx)
    if ctx.want("references"):
        write_o24(ctx, refs)
    if ctx.want("arms"):
        write_o25(ctx)


# ================================================================ small helpers
def _units_in_order(ctx, kinds=None):
    """Units in design order: design.order_key of the group, then run-table order."""
    index = {u.name: i for i, u in enumerate(ctx.units)}
    us = [u for u in ctx.units if kinds is None or u.kind in kinds]
    return sorted(us, key=lambda u: (design.order_key(u.group), index[u.name]))


def _groups_in_order(ctx, kinds=None):
    """Group names of the run table in design order (FIGURE_ORDER, ELECTRON_ORDER, IMMUNO_ORDER, other)."""
    gs = [g for g, grp in ctx.groups.items() if kinds is None or grp.kind in kinds]
    return sorted(gs, key=design.order_key)


def _units_of(ctx, group):
    return [ctx.unit(n) for n in ctx.groups[group].units]


def _side(x):
    return x if x else "-"


def _is_count(v):
    return isinstance(v, int) and not isinstance(v, bool)


def _status(ctx, engine, u, benchmark="per_file", db=None):
    """coverage's status text of (engine, benchmark, unit, db) (B:1368-1369), or Missing('no_coverage')."""
    row = ctx.coverage_row(engine, benchmark, u.name, db or u.td)
    return row.status if row is not None else T.Missing("no_coverage")


def _why(v):
    """The SPEC 2.6 reason of a count: '' for a positive count, 'zero' for 0, else the Missing reason."""
    if isinstance(v, T.Missing):
        return v.reason
    if _is_count(v) and v == 0:
        return "zero"
    return ""


def _join(parts):
    return "; ".join(p for p in parts if p)


def _fmt_lead(x):
    """Leads 100(x-1) with 1 decimal in text (SPEC 3 "Formatting"; OT:68, 75)."""
    return "NA" if T.is_missing(x) else f"{x:.1f}"


def _key_part(name):
    """A group name as a numbers.tsv key part (keys match ^[a-z0-9_.]+$, SPEC 3.8)."""
    return re.sub(r"[^a-z0-9_]", "_", name.lower())


def _reason_terms(u, terms):
    """Why a unit is out of a set whose members are (label, count) terms of different benchmarks, by the rule of
    ctx.reason (SPEC 2.7): 'decision', '<label>:<Missing reason>' or '<label>:zero'; None when in."""
    if u.is_decision:
        return "decision"
    for label, v in terms:
        if isinstance(v, T.Missing):
            return f"{label}:{v.reason}"
        if v == 0:
            return f"{label}:zero"
    return None


# ================================================================ ratio aggregation (SPEC O2 "Formula")
def _entries(ctx, num, den, level, units, set_engines=None, benchmarks=None, labels=None):
    """SPEC O2 step 1: per unit P_u, C_u, r_u = P_u / C_u and whether the unit is in the comparison set.
    set_engines: the engines of the set (default the pair, i.e. R(pair) of SPEC 2.7; ENGINES for R3). benchmarks and
    labels: (numerator, denominator) benchmarks of a cross-arm ratio (O9 other arrangement / main).
    The ratio is shown for decision units too (per-run tables), but they are never used (DS:998)."""
    out = []
    for u in units:
        if benchmarks is None:
            p, c = ctx.accepted(num, u, level), ctx.accepted(den, u, level)
            why = ctx.reason(u, set_engines or (num, den), level)
        else:
            p = ctx.accepted(num, u, level, benchmark=benchmarks[0])
            c = ctx.accepted(den, u, level, benchmark=benchmarks[1])
            why = _reason_terms(u, ((labels[0], p), (labels[1], c)))
        out.append({"unit": u, "p": p, "c": c, "ratio": T.ratio(p, c), "used": why is None, "reason": why})
    return out


def _dataset(entries):
    """SPEC O2 step 2, per dataset d with U_d = R & d: G_d = exp(fsum(log r_u)/|U_d|) and S_d = fsum(P)/fsum(C).
    n_units counts the non-decision units; the note names the excluded ones with their reasons."""
    used = [e for e in entries if e["used"]]
    n_units = sum(1 for e in entries if not e["unit"].is_decision)
    excluded = _join(f"{e['unit'].name} {e['reason']}" for e in entries
                     if not e["used"] and not e["unit"].is_decision)
    if n_units == 0:
        note = "decision only" if entries else "no unit"
    elif not used:
        note = _join(["dropped: no run in the set (DS:897)", excluded])
    else:
        note = excluded
    return {"entries": entries, "used": used, "n_units": n_units, "n_used": len(used),
            "gmean": T.gmean([e["ratio"] for e in used]),
            "sum_ratio": T.sum_ratio([e["p"] for e in used], [e["c"] for e in used]), "note": note}


def _scope(datasets):
    """SPEC O2 step 3 over the datasets of a scope [(group, _dataset)]: D_s = the datasets with |U_d| >= 1;
    E_s = gmean of the G_d (equal weight), W_s = gmean of the r_u over R & s (run-weighted, OPEN Q3),
    S_s = fsum(P)/fsum(C) over R & s (OPEN Q2). An empty D_s gives Missing('empty') for every value."""
    kept = [(g, d) for g, d in datasets if d["used"]]
    runs = [e for _, d in kept for e in d["used"]]
    return {"n_datasets": len(kept), "n_runs": len(runs),
            "equal_weight": T.gmean([d["gmean"] for _, d in kept]),
            "run_weighted": T.gmean([e["ratio"] for e in runs]),
            "sum_ratio": T.sum_ratio([e["p"] for e in runs], [e["c"] for e in runs]),
            "dropped": [g for g, d in datasets if not d["used"]]}


def _scope_groups(ctx, scope):
    """The datasets of a scope (SPEC O2 "Scopes"): heldout = the 10 held-out tryptic datasets (the headline,
    DS:624, 894), tuning = the 7, heldout_grade_X = the held-out tryptic datasets of grade X (DS:114; OPEN Q50).
    Only groups of the run table, in design order."""
    if scope == "tuning":
        gs = design.TUNING
    elif scope == "heldout":
        gs = design.HELDOUT
    else:
        gs = tuple(g for g in design.HELDOUT if design.grade(g) == scope[-1])
    return [g for g in design.FIGURE_ORDER if g in gs and g in ctx.groups]


def _pair_data(ctx, pair, level):
    """O2 for one pair and level over R(pair): {'groups': {group: _dataset}, 'scopes': {scope: _scope}}. With
    --design none the side and class summaries are skipped (SPEC 1, CLI), so 'scopes' is empty."""
    num, den = pair
    groups = OrderedDict((g, _dataset(_entries(ctx, num, den, level, _units_of(ctx, g))))
                         for g in _groups_in_order(ctx))
    scopes = OrderedDict()
    if ctx.design_mode == "paper":
        for scope in ("heldout", "tuning") + GRADE_SCOPES:
            scopes[scope] = _scope([(g, groups[g]) for g in _scope_groups(ctx, scope)])
    return {"groups": groups, "scopes": scopes}


def _summary_row(name, level, scope, s):
    return {"pair": name, "level": level, "scope": scope, "n_datasets": s["n_datasets"], "n_runs": s["n_runs"],
            "equal_weight": s["equal_weight"], "lead_pct": T.lead(s["equal_weight"]),
            "run_weighted": s["run_weighted"], "rw_lead_pct": T.lead(s["run_weighted"]),
            "sum_ratio": s["sum_ratio"], "sum_lead_pct": T.lead(s["sum_ratio"]),
            "dropped_datasets": ",".join(s["dropped"]) or "-"}


def _scope_numbers(ctx, prefix, s, output, ref, side, allowed=None):
    """The keys <prefix>.{lead, rw_lead, sum_lead, n_datasets, n_runs} of one scope value (SPEC O2, O3 "Text")."""
    for name, value in (("lead", T.lead(s["equal_weight"])), ("rw_lead", T.lead(s["run_weighted"])),
                        ("sum_lead", T.lead(s["sum_ratio"]))):
        ctx.number(f"{prefix}.{name}", value, _fmt_lead(value), unit="%", output=output, protocol_ref=ref,
                   source_side=side, main_text_allowed=allowed)
    ctx.number(f"{prefix}.n_datasets", s["n_datasets"], unit="datasets", output=output, protocol_ref=ref,
               source_side=side, main_text_allowed=allowed)
    ctx.number(f"{prefix}.n_runs", s["n_runs"], unit="runs", output=output, protocol_ref=ref, source_side=side,
               main_text_allowed=allowed)


# ================================================================ O1 identification counts
def write_o1(ctx):
    """O1 (SPEC 3.1; DS:587-590, 608-610, 928, 939): td accepted counts per unit x engine x level (long and wide),
    and the group sums over C(g) and the pair sets (OPEN Q1: the sum of per-file counts over the units every
    compared engine counted, zero allowed, decision runs excluded; no group sums for immuno, DS:625)."""
    cols = ["kind", "class", "grade", "group", "unit", "pooled", "n_files", "role", "engine", "level", "accepted",
            "status", "counted", "note"]
    wide_cols = ["kind", "class", "grade", "group", "unit", "pooled", "n_files", "role", "level"] + list(ENGINES) + \
        [e + "_status" for e in ENGINES] + ["note"]
    rows, wide = [], []
    for u in _units_in_order(ctx):
        head = {"kind": u.kind, "class": u.cls, "grade": u.grade, "group": u.group, "unit": u.name,
                "pooled": u.pooled, "n_files": u.n_files, "role": u.role}
        for level in ctx.levels:
            w = dict(head, level=level)
            notes = []
            for e in ENGINES:
                acc = ctx.accepted(e, u, level)
                cov = ctx.coverage_row(e, "per_file", u.name, u.td)
                missing = T.Missing("no_coverage")
                rows.append(dict(head, engine=e, level=level, accepted=acc, status=cov.status if cov else missing,
                                 counted=cov.counted if cov else missing, note=_why(acc)))
                w[e] = acc
                if _why(acc):
                    notes.append(f"{e}:{_why(acc)}")
            for e in ENGINES:
                w[e + "_status"] = _status(ctx, e, u)
            w["note"] = _join(notes)
            wide.append(w)
    ctx.write_table("O01_ids_runs", cols, rows)
    ctx.write_table("O01_ids_runs_wide", wide_cols, wide)

    gcols = ["kind", "class", "grade", "group", "level", "set", "n_units", "n_in_set", "sum_prose", "sum_sage",
             "sum_msfragger", "note"]
    grows = []
    for g in _groups_in_order(ctx):
        grp = ctx.groups[g]
        if grp.kind == "immuno":
            continue  # per-sample counts are the unit (DS:625)
        units = _units_of(ctx, g)
        nondec = [u for u in units if not u.is_decision]
        expected = tuple(e for e in ENGINES if any(e in u.expected for u in units))
        for level in ctx.levels:
            for set_name, engines in (("expected", None), ("prose_msfragger", ("prose", "msfragger")),
                                      ("prose_sage", ("prose", "sage"))):
                in_set = ctx.C(g, level, engines)
                set_engines = expected if engines is None else engines
                row = {"kind": grp.kind, "class": grp.cls, "grade": grp.grade, "group": g, "level": level,
                       "set": set_name, "n_units": len(nondec), "n_in_set": len(in_set)}
                for e in ENGINES:
                    if e not in set_engines:
                        row["sum_" + e] = T.Missing("not_in_set")
                    elif not in_set:
                        row["sum_" + e] = T.Missing("empty")
                    else:
                        row["sum_" + e] = sum(ctx.accepted(e, u, level) for u in in_set)  # integer counts: exact
                names = {u.name for u in in_set}
                out = [f"{u.name} {ctx.reason(u, engines or u.expected, level, positive=False)}"
                       for u in nondec if u.name not in names]
                # an engine outside E(u) of the group, e.g. Sage on bycz (B:1357), named in the note
                absent = [f"{e} not expected (E(u), B:1357)" for e in ENGINES
                          if e not in expected and (engines is None or e in engines)]
                row["note"] = "decision only" if not nondec else _join(absent + out)
                grows.append(row)
    ctx.write_table("O01_ids_groups", gcols, grows)


# ================================================================ O2 pairwise ratios and the headline
def write_o2(ctx):
    """O2 (SPEC 3.1; DS:621-624, 986, 997): per-run ratios over R(pair), per-dataset gmeans and sums, scope values
    (heldout = the headline, tuning, heldout_grade_A/B/C) and the keys ids.<scope>.<level>.<comparator>.*
    (main_text_allowed yes only for heldout; the grade scopes are supplement only, OPEN Q50)."""
    run_cols = ["pair", "level", "kind", "class", "grade", "group", "unit", "role", "prose", "comparator", "ratio",
                "used", "reason"]
    ds_cols = ["pair", "level", "kind", "side", "class", "grade", "group", "n_units", "n_used", "gmean", "lead_pct",
               "sum_ratio", "sum_lead_pct", "note"]
    pair_data = {(pair, level): _pair_data(ctx, pair, level) for pair in design.PAIRS for level in ctx.levels}
    runs, dsets, sums = [], [], []
    order = {u.name: i for i, u in enumerate(_units_in_order(ctx))}
    for pair in design.PAIRS:
        name = "_".join(pair)
        for level in ctx.levels:
            data = pair_data[(pair, level)]
            entries = [e for d in data["groups"].values() for e in d["entries"]]
            for e in sorted(entries, key=lambda x: order[x["unit"].name]):
                u = e["unit"]
                runs.append({"pair": name, "level": level, "kind": u.kind, "class": u.cls, "grade": u.grade,
                             "group": u.group, "unit": u.name, "role": u.role, "prose": e["p"], "comparator": e["c"],
                             "ratio": e["ratio"], "used": e["used"], "reason": e["reason"] or ""})
            for g, d in data["groups"].items():
                grp = ctx.groups[g]
                dsets.append({"pair": name, "level": level, "kind": grp.kind, "side": _side(grp.side),
                              "class": grp.cls, "grade": grp.grade, "group": g, "n_units": d["n_units"],
                              "n_used": d["n_used"], "gmean": d["gmean"], "lead_pct": T.lead(d["gmean"]),
                              "sum_ratio": d["sum_ratio"], "sum_lead_pct": T.lead(d["sum_ratio"]),
                              "note": d["note"]})
            for scope, s in data["scopes"].items():
                sums.append(_summary_row(name, level, scope, s))
    note = None if ctx.design_mode == "paper" else "scope summaries skipped: --design none (SPEC 1, CLI)"
    ctx.write_table("O02_pairs_runs", run_cols, runs)
    ctx.write_table("O02_pairs_datasets", ds_cols, dsets)
    ctx.write_table("O02_pairs_summary", SUMMARY_COLUMNS, sums, header_note=note)
    for pair in design.PAIRS:
        for level in ctx.levels:
            for scope, s in pair_data[(pair, level)]["scopes"].items():
                _scope_numbers(ctx, f"ids.{scope.lower()}.{level}.{pair[1]}", s, "O2", "DS:624, 894, 997; SPEC O2",
                               "tuning" if scope == "tuning" else "heldout", "yes" if scope == "heldout" else "no")


# ================================================================ O3 three engines
def write_o3(ctx):
    """O3 (SPEC 3.1; DS:623, 986): the three-engine set R3 (it excludes every electron run, Sage
    not_run_by_design, and Sage's failed searches), per-run counts, per-dataset gmeans of the three ratios (tryptic
    and immuno; immuno per dataset only, DS:881) with the per-dataset gmean of the counts for fig_ids_counts (OPEN
    Q54: gmean(P)/gmean(C) = gmean(P/C) over the same units), and the scope values (heldout, tuning). Keys three.*,
    main_text_allowed yes only for heldout (C19)."""
    run_cols = ["kind", "class", "grade", "group", "unit", "level", "prose", "sage", "msfragger"]
    ds_cols = ["level", "kind", "side", "class", "grade", "group", "n_units", "n_used"] + \
        ["_".join(p) for p in THREE_PAIRS] + ["gmean_count_" + e for e in ENGINES] + ["note"]
    runs, dsets, sums = [], [], []
    groups = _groups_in_order(ctx, kinds=("tuning", "heldout", "immuno", "other"))
    for level in ctx.levels:
        r3 = {u.name for u in ctx.R3(level)}
        for u in _units_in_order(ctx):
            if u.name in r3:
                row = {"kind": u.kind, "class": u.cls, "grade": u.grade, "group": u.group, "unit": u.name,
                       "level": level}
                row.update({e: ctx.accepted(e, u, level) for e in ENGINES})
                runs.append(row)
        per_pair = OrderedDict()
        for pair in THREE_PAIRS:
            per_pair[pair] = OrderedDict(
                (g, _dataset(_entries(ctx, pair[0], pair[1], level, _units_of(ctx, g), set_engines=ENGINES)))
                for g in groups)
        for g in groups:
            grp = ctx.groups[g]
            first = per_pair[THREE_PAIRS[0]][g]
            row = {"level": level, "kind": grp.kind, "side": _side(grp.side), "class": grp.cls, "grade": grp.grade,
                   "group": g, "n_units": first["n_units"], "n_used": first["n_used"]}
            for pair in THREE_PAIRS:
                row["_".join(pair)] = per_pair[pair][g]["gmean"]
            used = [e["unit"] for e in first["used"]]
            for e in ENGINES:
                row["gmean_count_" + e] = T.gmean([ctx.accepted(e, u, level) for u in used])
            row["note"] = first["note"]
            dsets.append(row)
        if ctx.design_mode != "paper":
            continue
        for pair in THREE_PAIRS:
            for scope in ("heldout", "tuning"):
                s = _scope([(g, per_pair[pair][g]) for g in _scope_groups(ctx, scope)])
                sums.append(_summary_row("_".join(pair), level, scope, s))
                _scope_numbers(ctx, f"three.{scope}.{level}.{'_'.join(pair)}", s, "O3", "DS:623, 986; SPEC O3",
                               "tuning" if scope == "tuning" else "heldout")
    note = None if ctx.design_mode == "paper" else "scope summaries skipped: --design none (SPEC 1, CLI)"
    ctx.write_table("O03_three_runs", run_cols, runs)
    ctx.write_table("O03_three_datasets", ds_cols, dsets)
    ctx.write_table("O03_three_summary", SUMMARY_COLUMNS, sums, header_note=note)


# ================================================================ O4, O6, O7 over-tuning (reuse OT)
def overtuning(ctx):
    """O4-O7 (SPEC 3.5), with OT = benchmarks/overtuning.py, not a reimplementation of the rule. Per level:
    ds, rows, notes = OT.load(runs, W/counts.tsv, level) (OT:90-124). If a side has no dataset for a comparator
    (OT.side_leads(ds) is None, OT:44-45), O4-O7 are skipped with NA keys, since OT.rule would raise (OT:53-54): the
    W_node case (the WARN is C25 in checks.py). Else version, best, full, loo = OT.rule(ds) (OT:51-62), n_t and n_h
    as OT:129-130, text = OT.sentence(...) (OT:65-87), and OT.report(ds, rows, notes, None, unit) under
    redirect_stdout into tables/O04_overtuning_<level>.stdout.txt (with out=None OT writes nothing, OT:145). The
    independent path of SPEC 3.5 is O2 (package code, fsum): C6 in checks.py compares the two."""
    counts = ctx.options.counts
    store = ctx.shared.setdefault("overtuning", {})
    for level in ctx.levels:
        unit = LEVEL_UNIT[level]
        if not counts or not os.path.exists(counts):
            ctx.check("INFO", "O04", f"overtuning {level}: no counts.tsv; O4-O7 skipped, keys NA")
            _overtuning_na_keys(ctx, level)
            continue
        try:
            ds, rows, notes = OT.load(ctx.options.runs, counts, level)
        except AssertionError as err:  # OT's own input assertions (OT:93, 95, 99, 106)
            ctx.check("INFO", "O04", f"overtuning {level}: OT.load stopped ({err}); O4-O7 skipped, keys NA (C6)")
            _overtuning_na_keys(ctx, level)
            continue
        entry = {"ds": ds, "rows": rows, "notes": notes, "version": None, "best": None, "full": None, "loo": None,
                 "n_t": None, "n_h": None, "skipped": False}
        store[level] = entry
        if OT.side_leads(ds) is None:
            entry["skipped"] = True
            ctx.check("INFO", "O04", f"overtuning {level}: a side has no dataset completed by ProSE and a comparator "
                                     "(OT:44-45); O4-O7 skipped, keys NA (C25)")
            _overtuning_na_keys(ctx, level)
            continue
        version, best, full, loo = OT.rule(ds)
        n_t = {e: len([d for d in ds[e] if d in OT.TUNING]) for e in OT.ENGINES}  # OT:129
        n_h = {e: len([d for d in ds[e] if d in OT.HELDOUT]) for e in OT.ENGINES}  # OT:130
        text = OT.sentence(version, best, full, loo, n_t, n_h, unit)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            got = OT.report(ds, rows, notes, None, unit)
        if tuple(got) != (version, best):  # cannot happen: report calls rule (OT:128)
            raise AssertionError(f"overtuning {level}: OT.report gives {got}, OT.rule {(version, best)}")
        entry.update(version=version, best=best, full=full, loo=loo, n_t=n_t, n_h=n_h)
        ctx.check("INFO", "O04", f"overtuning {level}: version {version}" + (f" ({best})" if best else "") +
                  f"; datasets tuning {n_t['msfragger']}/{n_t['sage']}, held-out {n_h['msfragger']}/{n_h['sage']} "
                  "(MSFragger/Sage)")
        if ctx.want("overtuning"):
            _write_overtuning(ctx, level, entry, text, buf.getvalue())


def _write_overtuning(ctx, level, entry, text, stdout):
    """The O04/O06 tables (O07 = the same at peptide level), OT's rows for fig_overtuning (O04_..._runs, the data of
    the run points of SPEC O5), the two sentence files and the overtuning.<level>.* keys (SPEC 3.5 "Files", "Text").
    Keys are lower case (SPEC 3.8 key pattern): lt_<e> = L_T, lh_<e> = L_H."""
    ds, rows, full, loo, best, version = (entry["ds"], entry["rows"], entry["full"], entry["loo"], entry["best"],
                                          entry["version"])
    n_rows = {}
    for r in rows:
        n_rows[(r[0], r[2])] = n_rows.get((r[0], r[2]), 0) + 1
    dcols = ["dataset", "side", "class", "grade", "n_runs_msfragger", "value_msfragger", "lead_msfragger",
             "n_runs_sage", "value_sage", "lead_sage"]
    drows = []
    for d in OT.TUNING + OT.HELDOUT:
        row = {"dataset": d, "side": "tuning" if d in OT.TUNING else "heldout", "class": design.cls(d),
               "grade": design.grade(d)}
        for e in OT.ENGINES:
            v = ds[e].get(d)
            row["n_runs_" + e] = n_rows.get((OT.NAMES[e], d), 0)
            row["value_" + e] = v if v is not None else T.Missing("dropped")
            row["lead_" + e] = T.lead(v) if v is not None else T.Missing("dropped")
        drows.append(row)
    ctx.write_table(f"O04_overtuning_{level}_datasets", dcols, drows,
                    header_note="from OT.load (OT:90-124); a dataset dropped for a comparator is NA (DS:897)")
    scols = ["comparator", "n_tuning", "L_T", "n_heldout", "L_H", "gap", "within_margin"]
    srows = [{"comparator": e, "n_tuning": entry["n_t"][e], "L_T": full[e][0], "n_heldout": entry["n_h"][e],
              "L_H": full[e][1], "gap": full[e][2], "within_margin": full[e][2] <= OT.MARGIN} for e in OT.ENGINES]
    ctx.write_table(f"O04_overtuning_{level}_sides", scols, srows,
                    header_note=f"leads in percent; margin OT.MARGIN = {OT.MARGIN:g} points (OT:31)")
    ctx.write_table(f"O04_overtuning_{level}_runs", list(OT_HEADER), [list(r) for r in rows],
                    header_note="OT's figure rows as strings (OT:123), the run points of fig_overtuning (SPEC O5)")
    lcols = ["left_out", "side", "class", "grade", "L_T_msfragger", "L_H_msfragger", "gap_msfragger", "L_T_sage",
             "L_H_sage", "gap_sage", "both_within_margin", "named_in_b"]
    lrows = []
    for d in OT.TUNING + OT.HELDOUT:
        if not any(d in ds[e] for e in OT.ENGINES):  # OT:55
            continue
        g = loo.get(d)  # absent: without d a side has no dataset (OT:56)
        row = {"left_out": d, "side": "tuning" if d in OT.TUNING else "heldout", "class": design.cls(d),
               "grade": design.grade(d)}
        for e in OT.ENGINES:
            for i, name in enumerate(("L_T_", "L_H_", "gap_")):
                row[name + e] = g[e][i] if g else T.Missing("side_empty")
        row["both_within_margin"] = all(g[e][2] <= OT.MARGIN for e in OT.ENGINES) if g else T.Missing("side_empty")
        row["named_in_b"] = version == "b" and d == best
        lrows.append(row)
    ctx.write_table(f"O06_overtuning_{level}_loo", lcols, lrows,
                    header_note="leave-one-out leads in percent (OT:55-61); on a tie the first in table order is "
                                "named (OT:61)")
    display = text
    if version == "b" and best:  # OT inserts the runs.tsv group key (OT:81); the display file uses DISPLAY_NAME
        display = text.replace(f"one dataset, {best} (without it", f"one dataset, {design.display(best)} (without it")
    ctx.write_file(f"sentence_overtuning_{level}.txt", text + "\n")
    ctx.write_file(f"sentence_overtuning_{level}_display.txt", display + "\n")
    ctx.write_file(f"tables/O04_overtuning_{level}.stdout.txt", stdout)
    ref = "DS:893-898; OT:51-87; SPEC 3.5"
    k, out = f"overtuning.{level}", ("O4" if level == "psm" else "O7")
    ctx.number(f"{k}.version", version, output=out, protocol_ref=ref, source_side="mixed")
    ctx.number(f"{k}.dataset_b", best if best else T.Missing("not_version_b"), output=out, protocol_ref=ref,
               source_side="mixed")
    ctx.number(f"{k}.dataset_b_display", design.display(best) if best else T.Missing("not_version_b"), output=out,
               protocol_ref=ref + "; OPEN Q30", source_side="mixed")
    for e in OT.ENGINES:
        lt, lh, gap = full[e]
        # OT's format (OPEN Q30): signed L_T, L_H without its sign ("more"/"fewer", DS:893), 1 decimal
        ctx.number(f"{k}.lt_{e}", lt, f"{lt:+.1f}", unit="%", output=out, protocol_ref=ref + "; DS:903",
                   source_side="tuning")
        ctx.number(f"{k}.lh_{e}", lh, f"{abs(lh):.1f}", unit="%", output=out, protocol_ref=ref,
                   source_side="heldout")
        ctx.number(f"{k}.gap_{e}", gap, f"{gap:+.1f}", unit="points", output=out, protocol_ref=ref,
                   source_side="mixed")
        ctx.number(f"{k}.n_t_{e}", entry["n_t"][e], unit="datasets", output=out, protocol_ref=ref,
                   source_side="tuning")
        ctx.number(f"{k}.n_h_{e}", entry["n_h"][e], unit="datasets", output=out, protocol_ref=ref,
                   source_side="heldout")


def _overtuning_na_keys(ctx, level):
    """The overtuning.<level>.* keys as NA when O4-O7 are skipped (SPEC 3.5 "Guard"; C25)."""
    if not ctx.want("overtuning"):
        return
    k, miss, out = f"overtuning.{level}", T.Missing("skipped"), ("O4" if level == "psm" else "O7")
    for name in ("version", "dataset_b", "dataset_b_display"):
        ctx.number(f"{k}.{name}", miss, output=out, protocol_ref="SPEC 3.5 Guard; C25", source_side="mixed")
    for e in OT.ENGINES:
        for name, side in (("lt", "tuning"), ("lh", "heldout"), ("gap", "mixed"), ("n_t", "tuning"),
                           ("n_h", "heldout")):
            ctx.number(f"{k}.{name}_{e}", miss, output=out, protocol_ref="SPEC 3.5 Guard; C25", source_side=side)


# ================================================================ O8 electron-based datasets
def write_o8(ctx):
    """O8 (SPEC 3.1; DS:881, 900, 718, 511): the kind electron units with ProSE and MSFragger (Sage is
    not_run_by_design, C4). The FDP columns are FDP as O11 (fdp.run_of, design shuffled; the same cached runs that
    O11_fdp_runs is written from, so they agree with it and exist without --only fdp): per engine its own
    realisations (_own), fdp_shared_n = the realisations both engines counted with accepted > 0 (F). Per group: gmean
    and sums over the non-decision runs, and per engine the mean of the shared run means over F (OPEN Q13); a group with
    only decision runs (pxd011695_EThcD, _ETD) is 'decision only', NA. Keys ids.electron.<group>.<level>.msfragger.*."""
    run_cols = ["group", "class", "grade", "unit", "role", "level", "prose", "msfragger", "sage_status", "ratio",
                "fdp_prose_mean", "fdp_prose_sd", "fdp_prose_n", "fdp_msfragger_mean", "fdp_msfragger_sd",
                "fdp_msfragger_n", "fdp_shared_n", "note"]
    ds_cols = ["group", "class", "grade", "level", "n_units", "n_used", "gmean", "lead", "sum_ratio",
               "fdp_prose_mean_of_shared", "fdp_msfragger_mean_of_shared", "fdp_n_runs", "note"]
    pair = ("prose", "msfragger")
    runs, dsets = [], []

    for level in ctx.levels:
        for u in _units_in_order(ctx, kinds=("electron",)):
            p, m = ctx.accepted("prose", u, level), ctx.accepted("msfragger", u, level)
            row = {"group": u.group, "class": u.cls, "grade": u.grade, "unit": u.name, "role": u.role,
                   "level": level, "prose": p, "msfragger": m, "sage_status": _status(ctx, "sage", u),
                   "ratio": T.ratio(p, m)}
            notes = [ctx.reason(u, pair, level) or ""]
            fruns = [fdp.run_of(ctx, e, u, level, FDP_DESIGN) for e in pair]
            for e, fr in zip(pair, fruns):
                row[f"fdp_{e}_mean"] = fr.mean_own
                row[f"fdp_{e}_sd"] = fr.sd_own
                row[f"fdp_{e}_n"] = fr.n_own
            row["fdp_shared_n"] = fruns[0].n_shared  # the same for both engines: the default shared rule over E(u)
            row["note"] = _join(notes)
            runs.append(row)
        for g in _groups_in_order(ctx, kinds=("electron",)):
            grp = ctx.groups[g]
            d = _dataset(_entries(ctx, "prose", "msfragger", level, _units_of(ctx, g)))
            row = {"group": g, "class": grp.cls, "grade": grp.grade, "level": level, "n_units": d["n_units"],
                   "n_used": d["n_used"], "gmean": d["gmean"], "lead": T.lead(d["gmean"]),
                   "sum_ratio": d["sum_ratio"]}
            # non-decision units with a shared mean for both engines (the set F, SPEC 2.7; OPEN Q13)
            in_f = [[fdp.run_of(ctx, e, u, level, FDP_DESIGN) for e in pair] for u in _units_of(ctx, g)]
            in_f = [frs for frs in in_f if all(fr.in_f and not T.is_missing(fr.mean_shared) for fr in frs)]
            for i, e in enumerate(pair):
                row[f"fdp_{e}_mean_of_shared"] = T.fmean([frs[i].mean_shared for frs in in_f])
            row["fdp_n_runs"] = len(in_f)
            row["note"] = d["note"]
            dsets.append(row)
            if ctx.design_mode == "paper":
                ref = "DS:881, 900; SPEC O8"
                key = f"ids.electron.{_key_part(g)}.{level}.msfragger"
                ctx.number(f"{key}.lead", T.lead(d["gmean"]), _fmt_lead(T.lead(d["gmean"])), unit="%", output="O8",
                           protocol_ref=ref, source_side="heldout")
                ctx.number(f"{key}.n_runs", d["n_used"], unit="runs", output="O8", protocol_ref=ref,
                           source_side="heldout")
    note = "FDP columns as in O11_fdp_runs (design shuffled); _own over each engine's counted realisations"
    ctx.write_table("O08_electron_runs", run_cols, runs, header_note=note + "; Sage not run by design (B:1357)")
    ctx.write_table("O08_electron_datasets", ds_cols, dsets, header_note=note + "; *_mean_of_shared over F")


# ================================================================ published references (REFERENCE_MAP)
def read_references(ctx):
    """REF rows of the groups of design.REFERENCE_MAP that are in the run table (SPEC 2.2; OPEN Q12, Q46, Q47).
    - Immuno: scope 'per sample <sample>:' with <sample> a unit of the group; tool from the engine prefix; level and
      fdr must start with the map's prefixes.
    - iprg2015: scope 'per run'; run_ids one unit of the group; tool from the engine prefix ('ProSE + Percolator'
      ignored); level 'PSMs...' -> psm, 'peptides...' -> peptide; level and fdr carried per row (O24).
    Rows of these groups with another scope are not used (e.g. REF:260, a mean over 12 runs). Any other string in a
    used row stops (exit 2), as do a second row per (sample, tool) or (run, tool, level) and a value that is no
    integer. Returns None without a reference file, else {'path', 'immuno': {sample: {tool: ref}}, 'iprg2015':
    {(unit, level): [ref]}} with ref = {'line', 'tool', 'value', 'level', 'fdr', 'comparability', 'flag',
    'engine'}."""
    path = ctx.references_path
    if not path or not os.path.exists(path):
        return None
    _, rows = T.read_tsv(path, required=("run_ids", "group", "scope", "value", "level", "fdr", "engine",
                                         "comparability"))
    out = {"path": path, "immuno": OrderedDict(), "iprg2015": OrderedDict()}
    for line, r in rows:
        g = r["group"]
        entry = next((m for m in design.REFERENCE_MAP if g in m["groups"]), None)
        if entry is None or g not in ctx.groups:
            continue
        scope, units = r["scope"], set(ctx.groups[g].units)

        def ref_row(tool, value):
            return {"line": line, "tool": tool, "value": value, "level": r["level"], "fdr": r["fdr"],
                    "comparability": r["comparability"], "flag": entry["flag"], "engine": r["engine"]}

        if entry["scope"].startswith("per sample"):
            prefix = entry["scope"].split("<sample>")[0]  # 'per sample '
            if not scope.startswith(prefix):
                continue
            rest = scope[len(prefix):]
            sample = rest.split(":", 1)[0]
            if ":" not in rest or sample not in units:
                T.stop(path, line, "scope", scope, f"'{prefix}<sample>:' with a sample of {g} "
                                                   f"({', '.join(sorted(units))})")
            tool = _ref_tool(path, line, r["engine"], entry)
            if tool is None:
                continue
            for col in ("level", "fdr"):
                if not r[col].startswith(entry[col]):
                    T.stop(path, line, col, r[col], f"a {col} starting with {entry[col]!r} (REFERENCE_MAP)")
            by_tool = out["immuno"].setdefault(sample, OrderedDict())
            if tool in by_tool:
                T.stop(path, line, "engine", r["engine"],
                       f"one row per (sample, tool); {sample} {tool} is at line {by_tool[tool]['line']}")
            by_tool[tool] = ref_row(tool, _ref_value(path, line, r["value"]))
        else:  # iprg2015, per run (O24)
            if not scope.startswith(entry["scope"]):
                continue
            tool = _ref_tool(path, line, r["engine"], entry)
            if tool is None:
                continue
            run = r["run_ids"]
            if run not in units:
                T.stop(path, line, "run_ids", run, f"one run of {g} ({', '.join(sorted(units))})")
            if r["level"].startswith("PSMs"):
                level = "psm"
            elif r["level"].startswith("peptides"):
                level = "peptide"
            else:
                T.stop(path, line, "level", r["level"], "a level starting with 'PSMs' or 'peptides'")
            refs = out["iprg2015"].setdefault((run, level), [])
            if any(x["tool"] == tool for x in refs):
                T.stop(path, line, "engine", r["engine"], f"one row per (run, tool, level); {run} {tool} {level} "
                                                          "is there already")
            refs.append(ref_row(tool, _ref_value(path, line, r["value"])))
    return out


def _ref_tool(path, line, engine, entry):
    """The tool of a REF engine string by prefix (REFERENCE_MAP); None for an ignored engine; any other string
    stops."""
    for prefix, tool in entry["engines"]:
        if engine.startswith(prefix):
            return tool
    T.stop(path, line, "engine", engine, "an engine starting with " + ", ".join(repr(p) for p, _ in entry["engines"]))


def _ref_value(path, line, text):
    try:
        return int(text)
    except ValueError:
        T.stop(path, line, "value", text, "an integer")


def lacking_tools(ctx, refs):
    """['<sample>:<tool>'] of the immuno samples of the run table without a published value of an expected tool
    (design.EXPECTED_TOOLS); the C21 verdict on them is checks.py's. Every sample when there is no reference file."""
    have = refs["immuno"] if refs else {}
    return [f"{u.name}:{tool}" for u in _units_in_order(ctx, kinds=("immuno",))
            for tool in design.EXPECTED_TOOLS.get(u.group, ()) if tool not in have.get(u.name, {})]


# ================================================================ O9 immunopeptidomics
def _donor_tissue(u):
    """'pxd058436_DN05_Thyroid_classI' -> 'DN05_Thyroid': the sample name without project prefix and class."""
    name, prefix = u.name, u.group.split("_")[0] + "_"
    if name.startswith(prefix):
        name = name[len(prefix):]
    return re.sub(r"_class(I|II)$", "", name)


def write_o9(ctx, refs):
    """O9 (SPEC 3.1; DS:625-631, 255-265, 485, 881, 1011): the immuno samples, peptide level primary (DS:625), PSM
    in the table only. ProSE main = per_file (its arrangement POOLED_ARRANGEMENT, SPEC 2.2), ProSE other =
    per_file_mode_<other> (DS:629; OPEN Q36; NA until run), Sage and MSFragger per_file. Published values of
    REFERENCE_MAP at the peptide level, fdr_note 'local' for pxd019643 (OPEN Q46), REF's comparability text per tool.
    O09_immuno_datasets: per group and pair the gmean over non-decision samples (DN13 class I are decision samples,
    DS:998). Keys ids.immuno.<group>.peptide.<comparator>.{lead, n_samples}: peptide level only, the PSM values stay
    in the tables (SPEC O9: "PSM goes into the table only")."""
    other = ctx.other_arrangement_tag
    other_bench = f"per_file_{other}" if other else None
    cols = ["group", "class", "grade", "sample", "donor_tissue", "role", "level", "main_arrangement", "prose_main",
            "prose_other", "sage", "sage_status", "msfragger", "mhcquant", "fragpipe", "peaks", "fdr_note",
            "comparability", "ratio_prose_msfragger", "ratio_prose_sage", "ratio_other_main", "note"]
    dcols = ["group", "class", "grade", "level", "pair", "n_units", "n_used", "gmean", "lead_pct", "sum_ratio",
             "sum_lead_pct", "note"]
    rows, dsets = [], []
    immuno_refs = refs["immuno"] if refs else {}
    for level in ctx.levels:
        for u in _units_in_order(ctx, kinds=("immuno",)):
            main = ctx.accepted("prose", u, level)
            alt = ctx.accepted("prose", u, level, benchmark=other_bench) if other_bench else \
                T.Missing("no_arrangement")
            sage, msf = ctx.accepted("sage", u, level), ctx.accepted("msfragger", u, level)
            have = immuno_refs.get(u.name, {})
            row = {"group": u.group, "class": u.cls, "grade": u.grade, "sample": u.name,
                   "donor_tissue": _donor_tissue(u), "role": u.role, "level": level,
                   "main_arrangement": ctx.pooled_arrangement or T.Missing("no_arrangement"), "prose_main": main,
                   "prose_other": alt, "sage": sage, "sage_status": _status(ctx, "sage", u), "msfragger": msf}
            flags = []
            for tool in ("mhcquant", "fragpipe", "peaks"):
                ref = have.get(tool)
                if level != "peptide":
                    row[tool] = T.Missing("peptide_level_only")
                elif ref is None:
                    row[tool] = T.Missing("not_published")
                else:
                    row[tool] = ref["value"]
                    if ref["flag"]:
                        flags.append(ref["flag"])
            row["fdr_note"] = ",".join(sorted(set(flags)))
            row["comparability"] = " | ".join(f"{t}: {r['comparability']}" for t, r in have.items()) or "-"
            row["ratio_prose_msfragger"] = T.ratio(main, msf)
            row["ratio_prose_sage"] = T.ratio(main, sage)
            row["ratio_other_main"] = T.ratio(alt, main)
            row["note"] = _join([f"prose:{_why(main)}" if _why(main) else "",
                                 f"sage:{_why(sage)}" if _why(sage) else "",
                                 f"msfragger:{_why(msf)}" if _why(msf) else "",
                                 f"other arrangement ({other or '?'}): {_why(alt)}" if _why(alt) else "",
                                 "decision sample (DS:998)" if u.is_decision else ""])
            rows.append(row)
        for g in _groups_in_order(ctx, kinds=("immuno",)):
            grp = ctx.groups[g]
            units = _units_of(ctx, g)
            sets = [("prose_msfragger", _entries(ctx, "prose", "msfragger", level, units)),
                    ("prose_sage", _entries(ctx, "prose", "sage", level, units))]
            if other_bench:
                sets.append(("prose_other_main", _entries(ctx, "prose", "prose", level, units,
                                                          benchmarks=(other_bench, "per_file"),
                                                          labels=(other, "main"))))
            for name, entries in sets:
                d = _dataset(entries)
                dsets.append({"group": g, "class": grp.cls, "grade": grp.grade, "level": level, "pair": name,
                              "n_units": d["n_units"], "n_used": d["n_used"], "gmean": d["gmean"],
                              "lead_pct": T.lead(d["gmean"]), "sum_ratio": d["sum_ratio"],
                              "sum_lead_pct": T.lead(d["sum_ratio"]), "note": d["note"]})
                # keys at the peptide level only: "Level peptide is primary (DS:625); PSM goes into the table only"
                # (SPEC O9)
                if ctx.design_mode == "paper" and name != "prose_other_main" and level == "peptide":
                    key = f"ids.immuno.{_key_part(g)}.{level}.{name.split('_')[1]}"
                    ref = "DS:625, 881; SPEC O9"
                    ctx.number(f"{key}.lead", T.lead(d["gmean"]), _fmt_lead(T.lead(d["gmean"])), unit="%",
                               output="O9", protocol_ref=ref, source_side="heldout")
                    ctx.number(f"{key}.n_samples", d["n_used"], unit="samples", output="O9", protocol_ref=ref,
                               source_side="heldout")
    note = [f"main arrangement {ctx.pooled_arrangement} (Search:rescore_reuse:mode of the immuno parameter files, "
            f"SPEC 2.2); other arrangement per_file_{other or '?'}"]
    lacking = lacking_tools(ctx, refs)
    if lacking:
        note.append(f"published values missing ({len(lacking)}, C21): " + ", ".join(lacking[:6]) +
                    (", ..." if len(lacking) > 6 else ""))
    for m in design.REFERENCE_MAP:
        if m["level"]:
            note.append(f"{'/'.join(m['groups'])}: published at '{m['level']}', '{m['fdr']}'"
                        + (f" ({m['flag']} FDR)" if m["flag"] else ""))
    ctx.write_table("O09_immuno_samples", cols, rows, header_note="; ".join(note))
    ctx.write_table("O09_immuno_datasets", dcols, dsets,
                    header_note="gmean over non-decision samples; DN13 class I samples are decision samples (DS:998)")


# ================================================================ O9b task 11b
def _rule11b_rows(ctx, pools):
    """[(benchmark, pool, database, level, accepted, entrapment, combined_fdp, te_ratio)] of ProSE on the pools:
    from --rule11b-work R (R/counts.tsv, counts.tsv format) when given, else from W (the per_file* td rows of the
    pools and the rule11b rows, SPEC 2.3)."""
    out = []
    if ctx.rule11b_work:
        path = os.path.join(ctx.rule11b_work, "counts.tsv")
        _, rows = T.read_tsv(path, exact_header=T.COUNTS_HEADER)
        for line, r in rows:
            if r["run"] not in pools or r["engine"] != "prose":
                continue
            if r["level"] not in design.LEVELS:
                T.stop(path, line, "level", r["level"], ", ".join(design.LEVELS))
            try:
                vals = (int(r["accepted"]), int(r["entrapment"]), float(r["combined_fdp"]), float(r["te_ratio"]))
            except ValueError:
                T.stop(path, line, "accepted, entrapment, combined_fdp, te_ratio",
                       f"{r['accepted']} {r['entrapment']} {r['combined_fdp']} {r['te_ratio']}", "numbers")
            out.append((r["benchmark"], r["run"], r["database"], r["level"]) + vals)
        return out
    for c in list(ctx.counts) + list(ctx.counts_rule11b):
        if c.engine == "prose" and c.run in pools and c.design in ("td", "rule11b"):
            out.append((c.benchmark, c.run, c.database, c.level, c.accepted, c.entrapment, c.combined_fdp,
                        c.te_ratio))
    return out


def write_o9b(ctx):
    """O9b (SPEC 3.1; DS:629, 1056; OPEN Q45): the pooled-arrangement rule on the DN13 class I pools (the decision
    samples of the class I immuno groups). Per pool and arrangement: peptides at 1% on td, and the peptide-level FDP
    on the pool's class I entrapment database. 'joint' is chosen only if on both pools it accepts more peptides than
    'per_file' and its FDP is at most per_file's + max(0.1 percentage points, 1 Poisson SE), SE = sqrt(N_E)(1+T/E)/N
    of per_file's estimate (OPEN Q45); without both databases per_file stays (DS:629). The arrangement of the per_file
    rows is POOLED_ARRANGEMENT; per_file_mode_<x> is the arrangement x (OPEN Q36). Decision samples: reported, in no
    summary (DS:858). Not built without --rule11b-work or rule11b rows (INFO)."""
    pools = OrderedDict((u.name, u) for u in _units_in_order(ctx, kinds=("immuno",))
                        if u.is_decision and u.group.endswith("classI"))
    if not ctx.rule11b_work and not ctx.counts_rule11b:
        ctx.check("INFO", "O09b", "no task-11b counts (--rule11b-work or rule11b rows in W): O09b not built (SPEC 4)")
        return
    if ctx.rule11b_work:
        ctx.record_input(os.path.join(ctx.rule11b_work, "counts.tsv"), "rule11b counts")
    mode = ctx.pooled_arrangement
    bench_of = {"per_file": "per_file" if mode == "per_file" else "per_file_mode_per_file",
                "joint": "per_file" if mode == "joint" else "per_file_mode_joint"}
    found = {}
    for bench, pool, db, level, acc, ent, comb, te in _rule11b_rows(ctx, pools):
        if level == "peptide":
            what = "td" if db == pools[pool].td else "entrap"
            found.setdefault((pool, bench, what), []).append((db, acc, ent, comb, te))
    table, values = [], {}
    for pool, u in pools.items():
        for arr in ("per_file", "joint"):
            bench = bench_of[arr]
            td = found.get((pool, bench, "td"), [])
            ent = sorted(found.get((pool, bench, "entrap"), []))
            notes = []
            peptides = td[0][1] if td else T.Missing("no_td_count")
            if ent:
                db, n, n_e, comb, te = ent[0]
                if len(ent) > 1:
                    notes.append(f"{len(ent)} entrapment databases, the first used")
                fdp = comb if n > 0 else T.Missing("none_accepted")  # EE prints 0 for N = 0 (EE-lib:32)
                se = math.sqrt(n_e) * (1 + te) / n if n > 0 else T.Missing("none_accepted")
            else:
                db = n = n_e = te = fdp = se = T.Missing("no_entrap_search")
            values[(pool, arr)] = {"peptides": peptides, "fdp": fdp, "se": se}
            table.append({"pool": pool, "group": u.group, "class": u.cls, "grade": u.grade, "role": u.role,
                          "arrangement": arr, "benchmark": bench, "peptides_td": peptides, "entrap_database": db,
                          "n_accepted_entrap_search": n, "n_entrapment_hits": n_e, "te_ratio": te, "fdp": fdp,
                          "fdp_poisson_se": se if arr == "per_file" else T.Missing("per_file_only"),
                          "fdp_limit": T.Missing("per_file_only"), "more_peptides": T.Missing("joint_only"),
                          "fdp_ok": T.Missing("joint_only"), "chosen": None, "equals_pooled_arrangement": None,
                          "note": _join(notes)})
    conditions = []
    limits = {}
    for row in table:
        pf = values[(row["pool"], "per_file")]
        if row["arrangement"] == "per_file":
            if not T.is_missing(pf["fdp"]) and not T.is_missing(pf["se"]):
                row["fdp_limit"] = pf["fdp"] + max(FDP_MARGIN, pf["se"])
            limits[row["pool"]] = row["fdp_limit"]
            continue
        jt = values[(row["pool"], "joint")]
        if _is_count(jt["peptides"]) and _is_count(pf["peptides"]):
            row["more_peptides"] = jt["peptides"] > pf["peptides"]
        limit = limits[row["pool"]]
        if not T.is_missing(jt["fdp"]) and not T.is_missing(limit):
            row["fdp_ok"] = jt["fdp"] <= limit
        conditions.append(row["more_peptides"] is True and row["fdp_ok"] is True)
    chosen = "joint" if pools and len(conditions) == len(pools) and all(conditions) else "per_file"
    for row in table:
        row["chosen"] = chosen
        row["equals_pooled_arrangement"] = (chosen == mode) if mode else T.Missing("no_arrangement")
    cols = ["pool", "group", "class", "grade", "role", "arrangement", "benchmark", "peptides_td", "entrap_database",
            "n_accepted_entrap_search", "n_entrapment_hits", "te_ratio", "fdp", "fdp_poisson_se", "fdp_limit",
            "more_peptides", "fdp_ok", "chosen", "equals_pooled_arrangement", "note"]
    ctx.write_table("O09b_rule11b", cols, table,
                    header_note="joint only if on both pools more peptides at 1% and FDP <= per_file's + max(0.1 "
                                "points, 1 Poisson SE) (DS:629); FDP as a fraction; decision samples (DS:858)")
    ctx.shared["rule11b_chosen"] = chosen


# ================================================================ O10 counts part
def o10_counts(ctx):
    """O10 counts part (SPEC 3.1, 3.3; DS:582, 652, 988; RA:121-123): per sample with a per_file_low_memory td search
    (coverage row), the prose td accepted counts of per_file and per_file_low_memory at both levels, and 'identical'
    when all four are counts and pairwise equal (DS:988; the data of C10). Passed in ctx.shared['O10_counts'] to
    timing.py (joint table O10_low_memory.tsv) and checks.py (C10); key lowmem.identical_all over the non-decision
    samples (OPEN Q27; decision samples enter no summary)."""
    out = []
    for u in _units_in_order(ctx):
        if ctx.coverage_row("prose", "per_file_low_memory", u.name, u.td) is None:
            continue
        row = {"group": u.group, "class": u.cls, "grade": u.grade, "sample": u.name, "role": u.role}
        for level, short in (("psm", "psm"), ("peptide", "pep")):
            row[f"{short}_std"] = ctx.accepted("prose", u, level)
            row[f"{short}_lm"] = ctx.accepted("prose", u, level, benchmark="per_file_low_memory")
        names = ("psm_std", "psm_lm", "pep_std", "pep_lm")
        if all(_is_count(row[k]) for k in names):
            row["identical"] = row["psm_std"] == row["psm_lm"] and row["pep_std"] == row["pep_lm"]
            row["note"] = ""
        else:
            row["identical"] = T.Missing("not_counted")
            row["note"] = _join(f"{k}:{row[k].reason}" for k in names if isinstance(row[k], T.Missing))
        out.append(row)
    ctx.shared["O10_counts"] = out
    use = [r for r in out if r["role"] != "decision"]
    if not use:
        value = T.Missing("empty")
    elif any(T.is_missing(r["identical"]) for r in use):
        value = T.Missing("incomplete")
    else:
        value = all(r["identical"] for r in use)
    ctx.number("lowmem.identical_all", value, output="O10", protocol_ref="DS:988; SPEC O10",
               source_side="heldout" if use else "none")


# ================================================================ O14 coverage
def _bench_order(bench):
    """per_file, the arms in ARMS order, further arms, batch, scaling (SPEC O14)."""
    if bench == "per_file":
        return (0, 0, "")
    if bench in design.ARMS:
        return (1, list(design.ARMS).index(bench), "")
    if bench.startswith("per_file_"):
        return (2, 0, bench)
    return (3, {"batch": 0, "scaling": 1}.get(bench, 2), bench)


def write_o14(ctx):
    """O14 (SPEC 3.1; DS:622, 807; B:1346-1369): every coverage row, inside and outside the design, with its database
    design (td, shuffled, natural, arath, rule11b, outside_design), sorted by benchmark (per_file, arms, batch,
    scaling), kind, group, unit, database, engine; the summary per engine x benchmark x state x counted; the paper
    table per engine x kind of the main per_file td searches, each search in exactly one of the columns counted ..
    other; keys coverage.<engine>.<state> (plus .expected and .counted) over the main per_file td searches."""
    cols = ["engine", "benchmark", "unit", "database", "db_design", "kind", "class", "grade", "group", "role", "state",
            "status", "counted"]
    unit_index = {u.name: i for i, u in enumerate(ctx.units)}
    run_index = {r.id: i for i, r in enumerate(ctx.runs)}
    kind_index = {k: i for i, k in enumerate(design.KINDS)}
    keyed = []
    for c in list(ctx.coverage) + list(ctx.coverage_outside):
        kind = cls = grade = group = role = "-"
        stem_pos = 0
        if c.scope == "batch":
            g = c.group or ctx.batch_groups.get(c.run)
            if g is not None:
                kind, cls, grade, group = g.kind, g.cls, g.grade, g.name
        else:
            u = c.unit or (ctx.unit_of_run.get(c.run) if c.scope == "scaling" else ctx.unit_by_name.get(c.run))
            if u is not None:
                kind, cls, grade, group, role = u.kind, u.cls, u.grade, u.group, u.role
                stem_pos = u.stems.index(c.db) if c.db in u.stems else len(u.stems)
        key = (_bench_order(c.benchmark), kind_index.get(kind, len(design.KINDS)), design.order_key(group),
               unit_index.get(c.run, run_index.get(c.run, len(ctx.units))), c.run, stem_pos, c.db, -(c.threads or 0),
               ENGINES.index(c.engine))
        keyed.append((key, {"engine": c.engine, "benchmark": c.benchmark, "unit": c.run, "database": c.database,
                            "db_design": c.design, "kind": kind, "class": cls, "grade": grade, "group": group,
                            "role": role, "state": c.state, "status": c.status, "counted": c.counted}))
    rows = [r for _, r in sorted(keyed, key=lambda x: x[0])]
    ctx.write_table("O14_coverage", cols, rows)

    summary = {}
    for r in rows:
        s = summary.setdefault((r["engine"], r["benchmark"], r["state"], r["counted"]), [0, set()])
        s[0] += 1
        s[1].add(r["unit"])
    order = sorted(summary, key=lambda k: (ENGINES.index(k[0]), _bench_order(k[1]), T.STATES.index(k[2]), not k[3]))
    ctx.write_table("O14_coverage_summary", ["engine", "benchmark", "state", "counted", "n_searches", "n_units"],
                    [{"engine": k[0], "benchmark": k[1], "state": k[2], "counted": k[3], "n_searches": summary[k][0],
                      "n_units": len(summary[k][1])} for k in order])

    pcols = ["engine", "kind", "expected", "counted", "failed_memory", "failed", "not_run_by_design", "not_run",
             "other"]
    prows = []
    states = {e: OrderedDict((s, 0) for s in T.STATES) for e in ENGINES}
    expected_all = {e: 0 for e in ENGINES}
    counted_all = {e: 0 for e in ENGINES}
    kinds = [k for k in design.KINDS if any(u.kind == k for u in ctx.units)]
    for e in ENGINES:
        for k in kinds:
            row = OrderedDict((c, 0) for c in pcols[2:])
            for u in ctx.units:
                if u.kind != k:
                    continue
                c = ctx.coverage_row(e, "per_file", u.name, u.td)
                if e in u.expected:
                    row["expected"] += 1
                    expected_all[e] += 1
                if c is not None:
                    states[e][c.state] += 1
                if c is not None and c.state == "ok" and c.counted:
                    row["counted"] += 1
                    counted_all[e] += 1
                elif c is not None and c.state in ("failed_memory", "failed", "not_run_by_design", "not_run"):
                    row[c.state] += 1
                else:
                    row["other"] += 1  # running, interrupted, unknown, over_limit, ok but not counted, no row
            prows.append(dict(row, engine=e, kind=k))
    ctx.write_table("O14_coverage_paper", pcols, prows,
                    header_note="main per_file td searches of every unit; expected = units with the engine in E(u) "
                                "(B:1357); each search is in exactly one of counted .. other")
    ref = "DS:622; B:1346-1369; SPEC O14"
    for e in ENGINES:
        ctx.number(f"coverage.{e}.expected", expected_all[e], unit="searches", output="O14", protocol_ref=ref,
                   source_side="mixed")
        ctx.number(f"coverage.{e}.counted", counted_all[e], unit="searches", output="O14", protocol_ref=ref,
                   source_side="mixed")
        for s, n in states[e].items():
            ctx.number(f"coverage.{e}.{s}", n, unit="searches", output="O14", protocol_ref=ref, source_side="mixed")


# ================================================================ O23 datasets
def _entrap_design_text(u):
    """'natural', 'shuffled s1-s3', 'natural + shuffled s1-s3' or '-' from the unit's entrapment designs (SPEC 2.1
    "Database design")."""
    parts = []
    if any(d == "natural" for _, d, _ in u.entrap):
        parts.append("natural")
    shuffled = [r for _, d, r in u.entrap if d == "shuffled"]
    if shuffled:
        rs = sorted(r for r in shuffled if r is not None)
        parts.append(f"shuffled s{rs[0]}-s{rs[-1]}" if len(rs) > 1 else (f"shuffled s{rs[0]}" if rs else "shuffled"))
    return " + ".join(parts) or "-"


def _ms2(mz, rid):
    if mz is None:
        return T.Missing("no_mzml_counts")
    if rid not in mz or not _is_count(mz[rid].get("ms2")):
        return T.Missing("run_missing_in_mzml_counts")
    return mz[rid]["ms2"]


def write_o23(ctx):
    """O23 (SPEC 3.6; DS:498-499; OPEN Q42): one row per group (n_runs, n_decision, instrument from design.py,
    params, db, entrapment design, reference databases, ms2_total = the sum of mzml_counts.tsv ms2 over the group's
    runs) and one row per run (O23_runs). The tuned MS2 total (DS:16) is checked by C14 (checks.py)."""
    mz = ctx.mzml_counts
    gcols = ["kind", "class", "grade", "group", "n_runs", "n_decision", "instrument", "params", "db", "entrap_design",
             "ref", "ms2_total"]
    grows = []
    for g in _groups_in_order(ctx):
        grp = ctx.groups[g]
        units = _units_of(ctx, g)
        runs = [ctx.run_by_id[r] for r in grp.runs]
        ms2 = [_ms2(mz, r.id) for r in runs]
        missing = next((x for x in ms2 if isinstance(x, T.Missing)), None)
        designs = []
        for u in units:
            if _entrap_design_text(u) not in designs:
                designs.append(_entrap_design_text(u))
        grows.append({"kind": grp.kind, "class": grp.cls, "grade": grp.grade, "group": g, "n_runs": grp.n_runs,
                      "n_decision": grp.n_decision, "instrument": grp.instrument,
                      "params": ";".join(sorted({r.params for r in runs})),
                      "db": ";".join(sorted({r.db for r in runs})), "entrap_design": ";".join(designs),
                      "ref": ";".join(sorted({s for u in units for s in u.ref})) or "-",
                      "ms2_total": missing if missing is not None else sum(ms2)})
    ctx.write_table("O23_datasets", gcols, grows)
    rcols = ["kind", "class", "grade", "group", "run", "unit", "role", "set", "format", "params", "db", "entrap",
             "ref", "ions", "scaling", "instrument", "ms2"]
    rrows = []
    for u in _units_in_order(ctx):
        for rid in u.runs:
            r = ctx.run_by_id[rid]
            rrows.append({"kind": u.kind, "class": u.cls, "grade": u.grade, "group": u.group, "run": rid,
                          "unit": u.name, "role": r.role, "set": r.set, "format": r.format, "params": r.params,
                          "db": r.db, "entrap": ";".join(r.entrap) or "-", "ref": ";".join(r.ref) or "-",
                          "ions": r.ions, "scaling": r.scaling, "instrument": u.instrument, "ms2": _ms2(mz, rid)})
    ctx.write_table("O23_runs", rcols, rrows)


# ================================================================ O24 external references
def write_o24(ctx, refs):
    """O24 (SPEC 3.1; DS:183, 485; OPEN Q47): per iPRG2015 run and level the three engines' td counts next to each
    REF row of REFERENCE_MAP (REF:251-263), with REF's level, fdr and comparability text; a run and level without a
    REF row gets one row with NA. iprg2015_1A is a decision run: shown (role column), in no summary. No ratio to the
    references enters numbers.tsv (the reference levels differ, e.g. 'lower bound' rows, REF:253)."""
    cols = ["group", "class", "grade", "unit", "role", "level", "prose", "sage", "msfragger", "tool", "ref_value",
            "ref_level", "ref_fdr", "comparability"]
    rows = []
    o24_groups = [g for m in design.REFERENCE_MAP if m["flag"] == "O24" for g in m["groups"]]
    for u in _units_in_order(ctx):
        if u.group not in o24_groups:
            continue
        for level in ctx.levels:
            base = {"group": u.group, "class": u.cls, "grade": u.grade, "unit": u.name, "role": u.role,
                    "level": level}
            base.update({e: ctx.accepted(e, u, level) for e in ENGINES})
            found = refs["iprg2015"].get((u.name, level), []) if refs else []
            if not found:
                miss = T.Missing("no_reference" if refs else "no_reference_file")
                rows.append(dict(base, tool=miss, ref_value=miss, ref_level=miss, ref_fdr=miss, comparability=miss))
            for r in found:
                rows.append(dict(base, tool=r["tool"], ref_value=r["value"], ref_level=r["level"], ref_fdr=r["fdr"],
                                 comparability=r["comparability"]))
    ctx.write_table("O24_external_references", cols, rows,
                    header_note="published values at their own level and FDR (REF:251-263); no ratio enters "
                                "numbers.tsv (REF:253 is a lower bound)")


# ================================================================ O25 further arms
def _arm_settings(ctx, tag):
    """{engine: text} of the --extra settings of the arm per_file_<tag> from W/commands.log (B:199-203, 252, 752-764).
    Sage and MSFragger: the line '# <engine> <run> <db>: extra settings ...' logged before the arm's command. ProSE:
    the options appended to its command (B:764), i.e. what the arm's command line has beyond the main command line
    with the same paths under per_file, both without the redirection (B:252) and without the /usr/bin/time prefix of
    a timed search (B:249-250; the main td search is timed, an arm may not be). The first arm line that has a main
    line gives the settings. {} without commands.log."""
    path = os.path.join(ctx.work, "commands.log") if ctx.work else None
    if not path or not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8", errors="replace") as f:
        lines = f.read().splitlines()
    marker = f"/per_file_{tag}/"
    redirect = re.compile(r" > \S+ 2>&1$")  # B:252
    timed = re.compile(r"(^|(?<= ))/usr/bin/time -v -o \S+ ")  # B:249-250, after an optional env prefix (B:251)

    def clean(x):
        return timed.sub("", redirect.sub("", x), count=1)

    out, pending, mains = {}, {}, None
    for line in lines:
        m = re.match(r"^# (prose|sage|msfragger) \S+ \S+: extra settings (.*)$", line)
        if m:
            pending[m.group(1)] = m.group(2)
            continue
        if marker not in line:
            continue
        for e in ENGINES:
            if e in out or f"/{e}{marker}" not in line:
                continue
            if e != "prose":
                out[e] = pending.get(e, "")
                continue
            if mains is None:
                mains = [clean(x) for x in lines if "/prose/per_file/" in x]
            arm = clean(line).replace(marker, "/per_file/")
            main = next((x for x in mains if arm.startswith(x + " ")), None)
            if main:  # else a later line of the arm may still have its main line
                out[e] = arm[len(main):].strip()
    return out


def _shared_stems(ctx, engine, u, level, bench):
    """The shuffled (else natural) entrapment stems of a unit counted with accepted > 0 by the engine in both the arm
    and the main arm (O25; as O11's shared realisations)."""
    return [s for s in (u.stems_of("shuffled") or u.stems_of("natural")) if all(
        _is_count(v) and v > 0 for v in (ctx.accepted(engine, u, level, db=s, benchmark=bench),
                                         ctx.accepted(engine, u, level, db=s)))]


def _o25_tags(ctx):
    """(tags, declared): the generic tags (ctx.unknown_tags) and the declared arms of design.TABLE_ARMS that have rows,
    in that order. Stops (exit 2) when two tags would write the same O25 table, e.g. 'x' and 'x_datasets'."""
    declared = [t for t in design.TABLE_ARMS if t in ctx.tags]
    tags = ctx.unknown_tags + declared
    names = {}
    for t in tags:
        for n in (f"O25_arm_{t}", f"O25_arm_{t}_datasets") + ((f"O25_arm_{t}_summary",) if t in declared else ()):
            names.setdefault(n, []).append(t)
    clash = sorted({t for ts in names.values() if len(ts) > 1 for t in ts})
    if clash:
        raise T.ValidationStop(f"O25: the arm tags {', '.join(clash)} would write the same table (O25_arm_<tag>, "
                               "O25_arm_<tag>_datasets, O25_arm_<tag>_summary); rename one of them")
    return tags, declared


def _declared_coverage(ctx, tag, bench, planned):
    """INFO/WARN O25 of a declared arm (as calib.arm_coverage_check for the calibration arms): per engine of the arm,
    the counted td + entrapment searches over its planned units (design.TABLE_ARMS kinds) against the expected
    number; WARN for an arm run on part of them, naming what is missing, and for arm searches on other units."""
    kinds = design.TABLE_ARMS[tag].kinds
    expected = sum(1 + len(u.entrap) for u in planned)
    for engine in design.ARMS[bench].engines:
        n, missing = 0, []
        for u in planned:
            for s in (u.td,) + tuple(x for x, _, _ in u.entrap):
                c = ctx.coverage_row(engine, bench, u.name, s)
                if c is not None and c.state == "ok" and c.counted:
                    n += 1
                else:
                    missing.append(f"{u.name} {s}")
        ctx.check("INFO", "O25", f"declared arm {bench}, {engine}: {n} of {expected} td + entrapment searches counted "
                                 f"over the {len(planned)} units of the kinds {', '.join(kinds)}")
        if 0 < n < expected:
            ctx.check("WARN", "O25", f"declared arm {bench}, {engine}: {expected - n} of {expected} td + entrapment "
                                     f"searches not counted: {T.list_text(missing)}")
    names = {u.name for u in planned}
    other = sorted({c.unit.name for c in ctx.coverage
                    if c.benchmark == bench and c.unit is not None and c.unit.name not in names})
    if other:
        ctx.check("WARN", "O25", f"declared arm {bench}: searches on {len(other)} unit(s) outside its kinds "
                                 f"({', '.join(kinds)}), shown per run and per dataset, in no summary: "
                                 f"{T.list_text(other)}")


def write_o25(ctx):
    """O25 (SPEC 3.1; DS:652, 811; OPEN Q49): for every tag outside ARMS (ctx.unknown_tags), and for the declared
    arms of design.TABLE_ARMS that have rows, per (engine, unit, level) with a search of the arm: the arm's td count
    next to the main arm's, ratio arm/main (both counted, > 0), the FDP over the shuffled (else natural) realisations
    counted with accepted > 0 by the engine in both the arm and the main arm (mean of combined_fdp, as O11), the median
    wall time of both arms as O15 when timed, and the --extra settings from commands.log. A declared arm also has a row
    for every planned unit (its engines x the units of its kinds), searched or not, and a coverage check (INFO/WARN
    O25). Tables: tables/O25_arm_<tag>.tsv per run, O25_arm_<tag>_datasets.tsv per dataset (_write_o25_datasets), and
    for a declared arm O25_arm_<tag>_summary.tsv across datasets (_write_o25_summary). The WARN naming a generic tag
    is C3 (checks.py), which reports ctx.unknown_tags; a declared arm gets none."""
    cols = ["tag", "engine", "kind", "class", "grade", "group", "unit", "role", "level", "arm_accepted",
            "main_accepted", "ratio", "arm_status", "fdp_arm_mean", "fdp_main_mean", "fdp_n", "wall_arm_med_s",
            "wall_main_med_s", "wall_ratio", "extra_settings", "note"]
    tags, declared = _o25_tags(ctx)
    for tag in tags:
        bench = f"per_file_{tag}"
        keys = {(c.engine, c.unit.name) for c in ctx.coverage if c.benchmark == bench and c.unit is not None}
        keys |= {(c.engine, c.unit.name) for c in ctx.counts if c.benchmark == bench and c.unit is not None}
        if tag in declared:
            planned = _units_in_order(ctx, design.TABLE_ARMS[tag].kinds)
            keys |= {(e, u.name) for u in planned for e in design.ARMS[bench].engines}
            _declared_coverage(ctx, tag, bench, planned)
            what, src = "declared arm", design.TABLE_ARMS[tag].ref
        else:
            what, src = "further arm", "DS:652, 811; OPEN Q49"
        settings = _arm_settings(ctx, tag)
        rows = []
        for u in _units_in_order(ctx):
            for e in ENGINES:
                if (e, u.name) not in keys:
                    continue
                arm_t, main_t = ctx.timing_value(e, bench, u.name), ctx.timing_value(e, "per_file", u.name)
                wall_arm = arm_t.wall_med if isinstance(arm_t, T.Timing) else arm_t
                wall_main = main_t.wall_med if isinstance(main_t, T.Timing) else main_t
                for level in ctx.levels:
                    arm, main = ctx.accepted(e, u, level, benchmark=bench), ctx.accepted(e, u, level)
                    shared = _shared_stems(ctx, e, u, level, bench)
                    rows.append({"tag": tag, "engine": e, "kind": u.kind, "class": u.cls, "grade": u.grade,
                                 "group": u.group, "unit": u.name, "role": u.role, "level": level,
                                 "arm_accepted": arm, "main_accepted": main, "ratio": T.ratio(arm, main),
                                 "arm_status": _status(ctx, e, u, benchmark=bench),
                                 "fdp_arm_mean": T.fmean([ctx.fdp(e, u, s, level, benchmark=bench) for s in shared]),
                                 "fdp_main_mean": T.fmean([ctx.fdp(e, u, s, level) for s in shared]),
                                 "fdp_n": len(shared), "wall_arm_med_s": wall_arm, "wall_main_med_s": wall_main,
                                 "wall_ratio": T.ratio(wall_arm, wall_main),
                                 "extra_settings": settings.get(e) or T.Missing("not_in_commands_log"),
                                 "note": _join([f"arm:{_why(arm)}" if _why(arm) else "",
                                                f"main:{_why(main)}" if _why(main) else ""])})
        ctx.write_table(f"O25_arm_{tag}", cols, rows, formats={"wall_arm_med_s": T.FMT_S, "wall_main_med_s": T.FMT_S},
                        header_note=f"{what} {bench} ({src}); FDP as a fraction")
        per_group = _write_o25_datasets(ctx, tag, bench, what, src, keys)
        if tag in declared:
            _write_o25_summary(ctx, tag, bench, what, src, per_group)


def _write_o25_datasets(ctx, tag, bench, what, src, keys):
    """The per-dataset part of O25: per (engine, group, level) with a unit of the arm (keys), the geometric mean over
    the group's runs of the ratio arm/main (both counted, > 0; decision runs excluded, SPEC O2 steps 1-2 via _entries
    and _dataset), the ratio of sums, and the FDP of both arms as the mean of the run means (README default 13; as O11
    per dataset): per non-decision unit with at least one shared realisation (_shared_stems), the mean combined_fdp
    over those realisations, then the mean over the units (fdp_n_runs of them). Returns {(engine, group, level):
    _dataset} for _write_o25_summary."""
    cols = ["tag", "engine", "kind", "class", "grade", "group", "side", "level", "n_units", "n_used", "gmean_ratio",
            "lead_pct", "sum_ratio", "fdp_arm_mean", "fdp_main_mean", "fdp_n_runs", "note"]
    rows, per_group = [], {}
    for g in _groups_in_order(ctx):
        grp = ctx.groups[g]
        for e in ENGINES:
            units = [u for u in _units_of(ctx, g) if (e, u.name) in keys]
            if not units:
                continue
            for level in ctx.levels:
                d = _dataset(_entries(ctx, e, e, level, units, benchmarks=(bench, "per_file"), labels=("arm", "main")))
                per_group[(e, g, level)] = d
                run_fdp = []
                for u in units:
                    shared = [] if u.is_decision else _shared_stems(ctx, e, u, level, bench)
                    if shared:
                        run_fdp.append((T.fmean([ctx.fdp(e, u, s, level, benchmark=bench) for s in shared]),
                                        T.fmean([ctx.fdp(e, u, s, level) for s in shared])))
                gm = d["gmean"]
                rows.append({"tag": tag, "engine": e, "kind": grp.kind, "class": grp.cls, "grade": grp.grade,
                             "group": g, "side": _side(grp.side), "level": level, "n_units": d["n_units"],
                             "n_used": d["n_used"], "gmean_ratio": gm, "lead_pct": T.lead(gm),
                             "sum_ratio": d["sum_ratio"], "fdp_arm_mean": T.fmean([a for a, _ in run_fdp]),
                             "fdp_main_mean": T.fmean([m for _, m in run_fdp]), "fdp_n_runs": len(run_fdp),
                             "note": d["note"]})
    ctx.write_table(f"O25_arm_{tag}_datasets", cols, rows,
                    header_note=f"{what} {bench} per dataset ({src}): geometric mean of the per-run ratios arm/main, "
                                "decision runs excluded (DS:998); FDP: mean of the run means over the shared shuffled "
                                "(else natural) realisations of the non-decision runs; FDP as a fraction")
    return per_group


def _write_o25_summary(ctx, tag, bench, what, src, per_group):
    """O25 across datasets for a declared arm (SPEC O2 step 3, as O2 per scope): per engine of the arm, level and
    scope (held-out and tuning tryptic datasets, the held-out ones per grade; _scope_groups), the equal-weight
    geometric mean of the dataset values, the run-weighted value next to it and the sum ratio, and the keys
    arm.<tag>.<engine>.<scope>.<level>.{lead, rw_lead, sum_lead, n_datasets, n_runs} with main_text_allowed no (the
    arm enters no main-text number, DATASETS 4.4). The electron-based and immunopeptidomics datasets are in no scope
    (as O2). With --design none the table is empty (SPEC 1, CLI)."""
    rows = []
    for e in design.ARMS[bench].engines:
        for level in ctx.levels:
            if ctx.design_mode != "paper":
                continue
            for scope in ("heldout", "tuning") + GRADE_SCOPES:
                s = _scope([(g, per_group.get((e, g, level)) or _dataset([])) for g in _scope_groups(ctx, scope)])
                rows.append(dict(_summary_row(e, level, scope, s), tag=tag))
                _scope_numbers(ctx, f"arm.{_key_part(tag)}.{e}.{scope.lower()}.{level}", s, "O25", src,
                               "tuning" if scope == "tuning" else "heldout", allowed="no")
    cols = ["tag"] + SUMMARY_COLUMNS
    note = None if ctx.design_mode == "paper" else "scope summaries skipped: --design none (SPEC 1, CLI)"
    ctx.write_table(f"O25_arm_{tag}_summary", cols, rows,
                    header_note=note or f"{what} {bench} across datasets ({src}): 'pair' is the engine; equal weight "
                                        "over the datasets, run-weighted next to it, decision runs excluded (DS:998); "
                                        "not for the main text")


# ================================================================ O27 the sensitivity value of the decision runs
# The components of decision.lead_change_pp, a fixed list in a fixed order (DATASETS.md 4.6, amendment of
# 2026-11-28): (key, scope or immuno group, comparator, level, value). The value is the field of _scope (the held-out
# scope, as write_o2) or of _dataset (an immuno group, as write_o9) whose lead the key is. On a tie the first counts.
DECISION_COMPONENTS = (
    ("ids.heldout.psm.msfragger.lead", "heldout", "msfragger", "psm", "equal_weight"),
    ("ids.heldout.psm.msfragger.rw_lead", "heldout", "msfragger", "psm", "run_weighted"),
    ("ids.heldout.psm.msfragger.sum_lead", "heldout", "msfragger", "psm", "sum_ratio"),
    ("ids.heldout.psm.sage.lead", "heldout", "sage", "psm", "equal_weight"),
    ("ids.heldout.psm.sage.rw_lead", "heldout", "sage", "psm", "run_weighted"),
    ("ids.heldout.psm.sage.sum_lead", "heldout", "sage", "psm", "sum_ratio"),
    ("ids.immuno.pxd058436_classi.peptide.msfragger.lead", "pxd058436_classI", "msfragger", "peptide", "gmean"),
    ("ids.immuno.pxd058436_classi.peptide.sage.lead", "pxd058436_classI", "sage", "peptide", "gmean"),
    ("ids.immuno.pxd019643_classi.peptide.msfragger.lead", "pxd019643_classI", "msfragger", "peptide", "gmean"),
    ("ids.immuno.pxd019643_classi.peptide.sage.lead", "pxd019643_classI", "sage", "peptide", "gmean"),
)
DECISION_REF = "DATASETS.md 4.6, amendment of 2026-11-28"
O27_COLUMNS = ["component", "pair", "level", "scope", "lead", "lead_with_decision", "change_pp", "units_added",
               "status"]


def _with_decision(entries):
    """The entries of _entries with one difference: a decision unit whose ratio is a number (both counts > 0,
    T.ratio) is used. A pooled sample is one unit. Returns (entries, names of the decision units now used)."""
    out, added = [], []
    for e in entries:
        if e["unit"].is_decision and not T.is_missing(e["ratio"]):
            e = dict(e, used=True, reason=None)
            added.append(e["unit"].name)
        out.append(e)
    return out, added


def _decision_component(ctx, where, comparator, level, field):
    """(L, L', decision units added) of one component. L is computed as write_o2 (the held-out scope) or write_o9 (an
    immuno group) compute its key: _entries, _dataset, then _scope for the scope. L' is the same with the entries of
    _with_decision."""
    if level not in ctx.levels:
        miss = T.Missing("level_not_built")
        return miss, miss, []
    groups = _scope_groups(ctx, where) if where == "heldout" else [g for g in (where,) if g in ctx.groups]
    if not groups:
        miss = T.Missing("no_dataset")
        return miss, miss, []
    base, more, added = [], [], []
    for g in groups:
        entries = _entries(ctx, "prose", comparator, level, _units_of(ctx, g))
        with_decision, names = _with_decision(entries)
        base.append((g, _dataset(entries)))
        more.append((g, _dataset(with_decision)))
        added += names
    if where == "heldout":
        return T.lead(_scope(base)[field]), T.lead(_scope(more)[field]), added
    return T.lead(base[0][1][field]), T.lead(more[0][1][field]), added


def write_o27(ctx):
    """O27 (DATASETS.md 4.6, amendment of 2026-11-28; not in the SPEC): the one sensitivity value of the decision runs.
    - For each component k of DECISION_COMPONENTS: L_k is the value of its key; L'_k is computed by the same code with
      one difference: every decision unit whose ratio is a number counts as used in its dataset (_with_decision).
      change_pp = L'_k - L_k in percentage points, signed. The electron-based decision runs are datasets of their own
      and enter no component.
    - decision.lead_change_pp = Z = max |change_pp|, 1 decimal as the leads. k* is the first component in list order
      with |change_pp| = Z; decision.lead_change_direction is 'higher' or 'lower', the sign of change_pp at k* (ProSE's
      lead with the decision runs counted), 'unchanged' if it is 0.
    - A component without L or L' stays out of the max; its row says why. Without any component, Z and the direction
      are NA and the header note says "could not be computed".
    - Keys decision.<component without 'ids.'>.change_pp, not for the main text. C19 lets exactly
      decision.lead_change_pp and decision.lead_change_direction into the main text.
    Called with --design paper only (build)."""
    rows, best = [], None
    for key, where, comparator, level, field in DECISION_COMPONENTS:
        lead, lead_d, added = _decision_component(ctx, where, comparator, level, field)
        missing = [(name, v) for name, v in (("lead", lead), ("lead_with_decision", lead_d)) if T.is_missing(v)]
        if missing:
            change = T.Missing("no_lead")
            status = "not in the max: " + ", ".join(f"{name} NA ({getattr(v, 'reason', 'NA')})" for name, v in missing)
        else:
            change, status = lead_d - lead, "ok"
            if best is None or abs(change) > abs(best[1]):
                best = (key, change)
        rows.append({"component": key, "pair": f"prose_{comparator}", "level": level, "scope": where, "lead": lead,
                     "lead_with_decision": lead_d, "change_pp": change, "units_added": len(added), "status": status})
        ctx.number(f"decision.{key[len('ids.'):]}.change_pp", change,
                   "NA" if T.is_missing(change) else f"{change:+.1f}", unit="points", output="O27",
                   protocol_ref=DECISION_REF, source_side="mixed", main_text_allowed="no")
    if best is None:
        z = direction = T.Missing("no_component")
        note = "decision.lead_change_pp could not be computed: no component has both leads"
    else:
        z = abs(best[1])
        direction = "higher" if best[1] > 0 else ("lower" if best[1] < 0 else "unchanged")
        note = (f"decision.lead_change_pp = max |change_pp| = {_fmt_lead(z)} points, at {best[0]} (ProSE's lead "
                f"{direction} with the decision runs counted)")
    ctx.number("decision.lead_change_pp", z, _fmt_lead(z), unit="points", output="O27", protocol_ref=DECISION_REF,
               source_side="mixed", main_text_allowed="yes")
    ctx.number("decision.lead_change_direction", direction, output="O27", protocol_ref=DECISION_REF,
               source_side="mixed", main_text_allowed="yes")
    ctx.write_table("O27_decision_sensitivity", O27_COLUMNS, rows,
                    header_note=f"{note}; change_pp = lead_with_decision - lead in percentage points, leads in "
                                "percent; lead_with_decision counts every decision unit whose ratio is a number "
                                f"(units_added); a component with an NA lead is not in the max ({DECISION_REF})")
