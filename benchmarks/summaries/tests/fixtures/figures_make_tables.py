"""Synthetic tables for test_figures.py: made-up values in exactly the SPEC section 3 columns, over the real unit
layout of benchmarks/runs.tsv (design information only). Missing cases are included on purpose:
Sage zero on pxd011695_HCD, Sage failed_memory on the six class II samples, Sage not_run_by_design on bycz, decision
runs, a failed MSFragger electron run, a missing Sage velos realisation, a scaling over_limit/not_run_over_limit,
an incomplete low_memory timing, a failed calibration arm, the ProSE other arrangement not run.

usage: python3 -B figures_make_tables.py [<out_dir>]   (default: fixtures/figures_tables next to this file)
The tables are committed; rerun only when a table module changes its columns (deterministic seed).
"""
import csv
import math
import os
import random
import sys

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
BENCH = os.path.abspath(os.path.join(HERE, "..", "..", ".."))  # benchmarks/
sys.path.insert(0, BENCH)
from summaries import design as D  # noqa: E402

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "figures_tables")
os.makedirs(OUT, exist_ok=True)
rng = random.Random(20261124)


def fmt(v, spec=".6f"):
    if v is None:
        return "NA"
    if isinstance(v, bool):
        return "yes" if v else "no"
    if isinstance(v, int):
        return str(v)
    if isinstance(v, float):
        return format(v, spec)
    return str(v)


FMTS = {}


def write(name, cols, rows, note=None, formats=None):
    formats = formats or {}
    with open(os.path.join(OUT, name + ".tsv"), "w", encoding="utf-8", newline="") as f:
        if note:
            f.write("# " + note + "\n")
        f.write("\t".join(cols) + "\n")
        for r in rows:
            assert set(r) == set(cols), (name, sorted(set(r) ^ set(cols)))
            f.write("\t".join(fmt(r[c], formats.get(c, ".6f")) for c in cols) + "\n")
    print(name, len(rows))


def gmean(xs):
    return math.exp(math.fsum(math.log(x) for x in xs) / len(xs))


# ---------------------------------------------------------------- units from runs.tsv
with open(os.path.join(BENCH, "runs.tsv"), encoding="utf-8", newline="") as f:
    runs = list(csv.DictReader(f, delimiter="\t"))
units, by_name = [], {}
for r in runs:
    name = r["sample"] if r["sample"] != "-" else r["id"]
    if name not in by_name:
        u = {"name": name, "group": r["group"], "role": r["role"], "runs": [], "ions": r["ions"],
             "entrap": [e[:-6] for e in r["entrap"].split(";") if e not in ("-", "")],
             "ref": [e[:-6] for e in r["ref"].split(";") if e not in ("-", "")]}
        by_name[name] = u
        units.append(u)
    by_name[name]["runs"].append(r["id"])
for u in units:
    u["kind"], u["cls"], u["grade"] = D.kind(u["group"]), D.cls(u["group"]), D.grade(u["group"])
    u["expected"] = ("prose", "sage", "msfragger") if u["ions"] == "by" else ("prose", "msfragger")
    u["n_files"] = len(u["runs"])
    u["shuffled"] = [s for s in u["entrap"] if "_entrap_s" in s]
    u["natural"] = [s for s in u["entrap"] if s.endswith("_natural_td")]

FACTOR = {"prose": 1.0, "msfragger": 0.91, "sage": 0.86}
BASE = {}
for g in D.ALL_GROUPS:
    BASE[g] = rng.choice((8000, 14000, 22000, 35000, 52000))
BASE["astral"] = 60000
counts = {}  # (engine, unit, level) -> accepted
for u in units:
    for e in D.ENGINES:
        for level in D.LEVELS:
            base = BASE[u["group"]] * (0.55 if level == "peptide" else 1.0)
            f = FACTOR[e]
            if u["group"] == "astral" and e != "prose":
                f *= 0.72  # astral: a large lead (version b in the sentence)
            counts[(e, u["name"], level)] = int(base * f * rng.uniform(0.92, 1.08))


def accepted(e, u, level):
    """None when not counted (Sage on bycz, Sage failed_memory on class II), 0 for the zero case."""
    if e not in u["expected"]:
        return None
    if e == "sage" and u["group"].endswith("classII"):
        return None
    if e == "sage" and u["group"] == "pxd011695_HCD":
        return 0
    if e == "msfragger" and u["name"] == "pxd065289_frac15":
        return None
    return counts[(e, u["name"], level)]


def status(e, u):
    if e not in u["expected"]:
        return "not_run_by_design Sage has no c/z ion types"
    if e == "sage" and u["group"].endswith("classII"):
        return "failed_memory stage all repetition 0 exit 137"
    if e == "msfragger" and u["name"] == "pxd065289_frac15":
        return "failed stage search repetition 1 exit 1"
    return "ok"


tryptic = [u for u in units if u["kind"] in ("tuning", "heldout")]

# ---------------------------------------------------------------- O02_pairs_runs, O04 datasets/sides
cols = "pair level kind class grade group unit role prose comparator ratio used reason".split()
rows = []
ds = {}
for comp in ("msfragger", "sage"):
    pair = f"prose_{comp}"
    for level in D.LEVELS:
        for u in units:
            p, c = accepted("prose", u, level), accepted(comp, u, level)
            used = u["role"] != "decision" and bool(p) and bool(c)
            reason = "" if used else ("decision" if u["role"] == "decision" else
                                      f"{comp}:{'zero' if c == 0 else (status(comp, u).split()[0])}")
            ratio = p / c if (p and c) else None
            rows.append({"pair": pair, "level": level, "kind": u["kind"], "class": u["cls"], "grade": u["grade"],
                         "group": u["group"], "unit": u["name"], "role": u["role"], "prose": p, "comparator": c,
                         "ratio": ratio, "used": used, "reason": reason})
            if used and u["kind"] in ("tuning", "heldout"):
                ds.setdefault((comp, level), {}).setdefault(u["group"], []).append(ratio)
write("O02_pairs_runs", cols, rows)
for level in D.LEVELS:
    drows, srows = [], []
    for g in D.TUNING + D.HELDOUT:
        r = {"dataset": g, "side": "tuning" if g in D.TUNING else "heldout", "class": D.cls(g), "grade": D.grade(g)}
        for comp in ("msfragger", "sage"):
            xs = ds.get((comp, level), {}).get(g)
            r[f"n_runs_{comp}"] = len(xs) if xs else 0
            r[f"value_{comp}"] = gmean(xs) if xs else None
            r[f"lead_{comp}"] = 100 * (gmean(xs) - 1) if xs else None
        drows.append(r)
    for comp in ("msfragger", "sage"):
        t = [gmean(xs) for g, xs in ds[(comp, level)].items() if g in D.TUNING]
        h = [gmean(xs) for g, xs in ds[(comp, level)].items() if g in D.HELDOUT]
        lt, lh = 100 * (gmean(t) - 1), 100 * (gmean(h) - 1)
        srows.append({"comparator": comp, "n_tuning": len(t), "L_T": lt, "n_heldout": len(h), "L_H": lh,
                      "gap": lt - lh, "within_margin": (lt - lh) <= 3.0})
    write(f"O04_overtuning_{level}_datasets",
          "dataset side class grade n_runs_msfragger value_msfragger lead_msfragger n_runs_sage value_sage "
          "lead_sage".split(), drows, formats={"lead_msfragger": ".1f", "lead_sage": ".1f"})
    write(f"O04_overtuning_{level}_sides", "comparator n_tuning L_T n_heldout L_H gap within_margin".split(), srows)
    orows = []
    for comp in ("msfragger", "sage"):
        for r in rows:
            if (r["pair"] == f"prose_{comp}" and r["level"] == level and r["used"]
                    and r["kind"] in ("tuning", "heldout")):
                orows.append({"engine": D.ENGINE_NAME[comp], "side": r["kind"], "dataset": r["group"],
                              "run": r["unit"], "ratio": r["ratio"],
                              "dataset_value": gmean(ds[(comp, level)][r["group"]])})
    write(f"O04_overtuning_{level}_runs", "engine side dataset run ratio dataset_value".split(), orows)

# ---------------------------------------------------------------- O03_three_runs (R3)
rows = []
for level in D.LEVELS:
    for u in units:
        if u["role"] == "decision" or u["kind"] not in ("tuning", "heldout", "immuno"):
            continue
        vals = {e: accepted(e, u, level) for e in D.ENGINES}
        if all(vals.values()):
            rows.append({"kind": u["kind"], "class": u["cls"], "grade": u["grade"], "group": u["group"],
                         "unit": u["name"], "level": level, **vals})
write("O03_three_runs", "kind class grade group unit level prose sage msfragger".split(), rows)

# ---------------------------------------------------------------- O11_fdp_runs, O12_fdp_arath
fdp_value = {}  # (engine, unit, level, stem) -> fdp fraction (None: not counted)
for u in units:
    for e in u["expected"]:
        for level in D.LEVELS:
            for stem in u["entrap"] + u["ref"]:
                if accepted(e, u, level) is None:
                    continue
                if e == "sage" and u["name"] == "velos_125_R1" and stem.endswith("_s3_td"):
                    continue  # one failed entrapment search (as in one trial)
                if accepted(e, u, level) == 0:
                    fdp_value[(e, u["name"], level, stem)] = None  # none accepted
                    continue
                base = {"prose": 0.0085, "sage": 0.0075, "msfragger": 0.0095}[e]
                if stem.endswith("_arath_td"):
                    base *= 0.8
                if stem.endswith("_natural_td"):
                    base *= 1.15
                if u["group"] == "astral_250pg":
                    base *= 1.35
                fdp_value[(e, u["name"], level, stem)] = base * rng.uniform(0.7, 1.3) * (1.1 if level == "peptide"
                                                                                         else 1.0)
cols = ("engine kind class grade group unit role level design n_own mean_own sd_own min_own max_own n_shared "
        "mean_shared sd_shared natural arath note").split()
rows, o12 = [], []
for u in units:
    if not u["entrap"] and not u["ref"]:
        continue
    for level in D.LEVELS:
        shared = [s for s in u["shuffled"]
                  if all(fdp_value.get((e, u["name"], level, s)) is not None for e in u["expected"])]
        for e in u["expected"]:
            if accepted(e, u, level) is None:
                continue
            own = [fdp_value[(e, u["name"], level, s)] for s in u["shuffled"]
                   if fdp_value.get((e, u["name"], level, s)) is not None]
            nat = fdp_value.get((e, u["name"], level, u["natural"][0])) if u["natural"] else None
            ara = fdp_value.get((e, u["name"], level, u["ref"][0])) if u["ref"] else None
            decision = u["role"] == "decision"
            sh = [fdp_value[(e, u["name"], level, s)] for s in shared] if not decision else []

            def msd(xs):
                if not xs:
                    return None, None
                m = math.fsum(xs) / len(xs)
                return m, (math.sqrt(math.fsum((x - m) ** 2 for x in xs) / (len(xs) - 1)) if len(xs) > 1 else None)
            base = {"engine": e, "kind": u["kind"], "class": u["cls"], "grade": u["grade"], "group": u["group"],
                    "unit": u["name"], "role": u["role"], "level": level, "natural": nat, "arath": ara}
            if u["shuffled"]:
                mo, so = msd(own)
                ms, ss = msd(sh)
                note = "decision" if decision else ("none_accepted" if accepted(e, u, level) == 0 else
                                                    ("incomplete" if len(own) < 3 else ""))
                rows.append({**base, "design": "shuffled", "n_own": len(own), "mean_own": mo, "sd_own": so,
                             "min_own": min(own) if own else None, "max_own": max(own) if own else None,
                             "n_shared": len(sh), "mean_shared": ms, "sd_shared": ss, "note": note})
            for design, v in (("natural", nat), ("arath", ara)):
                if (design == "natural" and u["natural"]) or (design == "arath" and u["ref"]):
                    rows.append({**base, "design": design, "n_own": 1 if v is not None else 0, "mean_own": v,
                                 "sd_own": None, "min_own": v, "max_own": v, "n_shared": None, "mean_shared": None,
                                 "sd_shared": None, "note": "decision" if decision else ""})
            if u["ref"]:
                ms, ss = msd(sh)
                o12.append({"engine": e, "class": u["cls"], "grade": u["grade"], "group": u["group"],
                            "unit": u["name"], "level": level, "arath": ara, "shuffled_mean_shared": ms,
                            "shuffled_sd_shared": ss, "shuffled_n_shared": len(sh),
                            "difference_pp": None if ara is None or ms is None else 100 * (ara - ms),
                            "in_shared_set": True})
write("O11_fdp_runs", cols, rows)
write("O12_fdp_arath", ("engine class grade group unit level arath shuffled_mean_shared shuffled_sd_shared "
                        "shuffled_n_shared difference_pp in_shared_set").split(), o12)

# ---------------------------------------------------------------- O08_electron_runs
cols = ("group class grade unit role level prose msfragger sage_status ratio fdp_prose_mean fdp_prose_sd fdp_prose_n "
        "fdp_msfragger_mean fdp_msfragger_sd fdp_msfragger_n fdp_shared_n note").split()
rows = []
for level in D.LEVELS:
    for u in units:
        if u["kind"] != "electron":
            continue
        p, m = accepted("prose", u, level), accepted("msfragger", u, level)
        r = {"group": u["group"], "class": u["cls"], "grade": u["grade"], "unit": u["name"], "role": u["role"],
             "level": level, "prose": p, "msfragger": m, "sage_status": status("sage", u),
             "ratio": p / m if p and m else None,
             "note": "decision" if u["role"] == "decision" else ("" if m else "msfragger:failed")}
        for e in ("prose", "msfragger"):
            own = [fdp_value[(e, u["name"], level, s)] for s in u["shuffled"]
                   if fdp_value.get((e, u["name"], level, s)) is not None]
            mo = math.fsum(own) / len(own) if own else None
            so = math.sqrt(math.fsum((x - mo) ** 2 for x in own) / (len(own) - 1)) if len(own) > 1 else None
            r[f"fdp_{e}_mean"], r[f"fdp_{e}_sd"], r[f"fdp_{e}_n"] = mo, so, len(own)
        r["fdp_shared_n"] = 3 if (p and m and u["role"] != "decision") else 0
        rows.append(r)
write("O08_electron_runs", cols, rows)

# ---------------------------------------------------------------- O09_immuno_samples
cols = ("group class grade sample donor_tissue role level main_arrangement prose_main prose_other sage sage_status "
        "msfragger mhcquant fragpipe peaks fdr_note comparability ratio_prose_msfragger ratio_prose_sage "
        "ratio_other_main note").split()
rows = []
for level in D.LEVELS:
    for u in units:
        if u["kind"] != "immuno":
            continue
        p, s, m = (accepted(e, u, level) for e in ("prose", "sage", "msfragger"))
        donor = u["name"].split("_")[1] + "_" + u["name"].split("_")[2]
        p058 = u["group"].startswith("pxd058436")
        ref = (lambda f: int(p * f) if level == "peptide" else None)
        rows.append({"group": u["group"], "class": u["cls"], "grade": u["grade"], "sample": u["name"],
                     "donor_tissue": donor, "role": u["role"], "level": level, "main_arrangement": "per_file",
                     "prose_main": p, "prose_other": None, "sage": s, "sage_status": status("sage", u),
                     "msfragger": m, "mhcquant": ref(0.82), "fragpipe": ref(0.95) if p058 else None,
                     "peaks": ref(1.04) if p058 else None, "fdr_note": "" if p058 else "local",
                     "comparability": "same FDR level" if p058 else "local FDR, not the same level",
                     "ratio_prose_msfragger": p / m if p and m else None,
                     "ratio_prose_sage": p / s if p and s else None, "ratio_other_main": None,
                     "note": "; ".join(x for x in ("decision" if u["role"] == "decision" else "",
                                                   "sage:failed_memory" if s is None else "",
                                                   "prose_other:not_run") if x)})
write("O09_immuno_samples", cols, rows)

# ---------------------------------------------------------------- O13_matched_fdp (fdp.O13_COLUMNS)
cols = ("pair level kind class grade group unit role design n_realisations n_entrap_prose_matched "
        "n_entrap_comparator_matched ratio_matched n_entrap_prose_q01 n_entrap_comparator_q01 ratio_q01 "
        "ratio_plain monotone_ok note").split()
rows = []
for comp in ("msfragger", "sage"):
    for level in D.LEVELS:
        for u in tryptic:
            if comp not in u["expected"]:
                continue
            p, c = accepted("prose", u, level), accepted(comp, u, level)
            if not p or not c:
                continue
            designs = ((["shuffled"] if u["shuffled"] else []) + (["natural"] if u["natural"] else [])
                       + (["arath"] if u["ref"] else []))
            for d in designs:
                q01 = p / c * rng.uniform(0.98, 1.02)
                pe, ce = p * 0.004, c * 0.004 / q01 * (p / c)
                rows.append({"pair": f"prose_{comp}", "level": level, "kind": u["kind"], "class": u["cls"],
                             "grade": u["grade"], "group": u["group"], "unit": u["name"], "role": u["role"],
                             "design": d, "n_realisations": 3 if d == "shuffled" else 1,
                             "n_entrap_prose_matched": pe * 0.97, "n_entrap_comparator_matched": ce,
                             "ratio_matched": q01 * rng.uniform(0.94, 1.0), "n_entrap_prose_q01": pe,
                             "n_entrap_comparator_q01": ce, "ratio_q01": q01, "ratio_plain": p / c,
                             "monotone_ok": True, "note": "decision" if u["role"] == "decision" else ""})
write("O13_matched_fdp", cols, rows)

# ---------------------------------------------------------------- O15_time_runs
cols = ("engine kind class grade group unit role n_files threads state n_reps wall_med_s cpu_med_s rss_med_gib wall_r1 "
        "wall_r2 wall_r3 cpu_r1 cpu_r2 cpu_r3 rss_r1_gib rss_r2_gib rss_r3_gib search_wall_med_s join_wall_med_s "
        "rescoring_wall_med_s gc_heap_gib note").split()
rows = []
WALL = {"prose": 0.45, "sage": 0.7, "msfragger": 1.0}
RSS = {"prose": 0.35, "sage": 0.5, "msfragger": 1.0}
per_file_wall = {}
for u in units:
    base_wall = {"immuno": 2400, "electron": 900}.get(u["kind"], 600) * rng.uniform(0.6, 1.6)
    base_rss = {"immuno": 90, "electron": 30}.get(u["kind"], 40) * rng.uniform(0.6, 1.4)
    for e in D.ENGINES:
        st = status(e, u)
        state = st.split()[0]
        r = {c: None for c in cols}
        r.update({"engine": e, "kind": u["kind"], "class": u["cls"], "grade": u["grade"], "group": u["group"],
                  "unit": u["name"], "role": u["role"], "n_files": u["n_files"], "threads": 16, "state": state,
                  "note": "" if state == "ok" else state})
        if state == "ok":
            if u["name"] == "UPS1_2500amol_R3" and e == "sage":
                r.update({"state": "incomplete", "n_reps": 2, "note": "no_timing (r2)"})
            else:
                w = [base_wall * WALL[e] * u["n_files"] * rng.uniform(0.97, 1.03) for _ in range(3)]
                rs = [base_rss * RSS[e] * rng.uniform(0.98, 1.02) for _ in range(3)]
                cp = [x * 12 for x in w]
                r.update({"n_reps": 3, "wall_med_s": sorted(w)[1], "cpu_med_s": sorted(cp)[1],
                          "rss_med_gib": sorted(rs)[1], "wall_r1": w[0], "wall_r2": w[1], "wall_r3": w[2],
                          "cpu_r1": cp[0], "cpu_r2": cp[1], "cpu_r3": cp[2], "rss_r1_gib": rs[0], "rss_r2_gib": rs[1],
                          "rss_r3_gib": rs[2]})
                if e == "msfragger":
                    r["search_wall_med_s"] = r["wall_med_s"] * 0.7
                    r["rescoring_wall_med_s"] = r["wall_med_s"] * 0.25
                    r["join_wall_med_s"] = r["wall_med_s"] * 0.05 if u["n_files"] > 1 else None
                per_file_wall[(e, u["name"])] = r["wall_med_s"]
        rows.append(r)
write("O15_time_runs", cols, rows,
      note="MSFragger's RSS includes its JVM heap of up to 196 GiB (DS:651, 653)",
      formats={c: ".2f" for c in cols if c.endswith("_s") or c.startswith(("wall_r", "cpu_r"))}
      | {c: ".3f" for c in cols if c.endswith("_gib")})

# ---------------------------------------------------------------- O16_batch
cols = ("engine kind class grade group n_files threads batch_wall_med_s batch_wall_per_file_s sum_per_file_wall_s "
        "ratio_wall batch_cpu_med_s sum_per_file_cpu_s ratio_cpu batch_rss_med_gib max_per_file_rss_gib in_B3 "
        "note").split()
rows = []
for g in D.BATCH_ORDER:
    members = [u for u in units if u["group"] == g and len(u["runs"]) == 1]
    ions = members[0]["ions"]
    for e in D.ENGINES:
        r = {c: None for c in cols}
        r.update({"engine": e, "kind": D.kind(g), "class": D.cls(g), "grade": D.grade(g), "group": g,
                  "n_files": len(members), "threads": 16, "in_B3": g != "ultra2_hye", "note": ""})
        if e == "sage" and ions != "by":
            r.update({"note": "not_run_by_design", "in_B3": True})
        elif e == "msfragger" and g == "ultra2_hye":
            r.update({"note": "incomplete (batch timing)"})
        else:
            s = math.fsum(per_file_wall.get((e, u["name"]), 600.0) for u in members)
            ratio = rng.uniform(0.45, 1.15) if e != "sage" else rng.uniform(0.7, 1.3)
            r.update({"batch_wall_med_s": s * ratio, "batch_wall_per_file_s": s * ratio / len(members),
                      "sum_per_file_wall_s": s, "ratio_wall": ratio, "batch_cpu_med_s": s * ratio * 10,
                      "sum_per_file_cpu_s": s * 11, "ratio_cpu": ratio * 10 / 11, "batch_rss_med_gib": 60.0,
                      "max_per_file_rss_gib": 40.0})
        rows.append(r)
write("O16_batch", cols, rows)

# ---------------------------------------------------------------- O17_scaling
cols = ("engine machine threads state n_reps wall_med_s wall_lower_bound_s cpu_med_s rss_med_gib speedup efficiency "
        "speedup_rel efficiency_rel cores_used search_wall_med_s rescoring_wall_med_s note").split()
rows = []
grid = (64, 48, 32, 16, 8, 4, 2, 1)
L = 7200.0
for e, t1, alpha in (("prose", 3600.0, 0.93), ("sage", 5400.0, 0.9), ("msfragger", 21000.0, 0.85)):
    t = {n: t1 / (n ** alpha) for n in grid}
    for n in grid:
        r = {c: None for c in cols}
        r.update({"engine": e, "machine": "scaling node", "threads": n, "note": ""})
        if e == "msfragger" and n == 2:
            r.update({"state": "over_limit", "n_reps": 0, "wall_lower_bound_s": L, "note": "over_limit at r1"})
        elif e == "msfragger" and n == 1:
            r.update({"state": "not_run_over_limit", "n_reps": 0, "note": "not_run_over_limit"})
        else:
            r.update({"state": "ok", "n_reps": 3, "wall_med_s": t[n], "cpu_med_s": t[n] * n * 0.8,
                      "rss_med_gib": {"prose": 18, "sage": 25, "msfragger": 70}[e] * (1 + 0.004 * n),
                      "cores_used": n * 0.8})
            if e == "msfragger":
                r["search_wall_med_s"] = t[n] * 0.75
                r["rescoring_wall_med_s"] = t[n] * 0.25
                n0 = 4
                r["speedup_rel"] = t[n0] / t[n]
                r["efficiency_rel"] = r["speedup_rel"] / (n / n0)
            else:
                r["speedup"] = t1 / t[n]
                r["efficiency"] = r["speedup"] / n
        rows.append(r)
    ref = {c: None for c in cols}
    ref.update({"engine": e, "machine": "engine node", "threads": 64, "state": "ok", "n_reps": 3,
                "wall_med_s": t[16] * 0.92, "cpu_med_s": t[16] * 13, "rss_med_gib": {"prose": 18, "sage": 25,
                                                                                    "msfragger": 70}[e] * 1.05,
                "note": "workstation comparison (DS:671): per_file hfx_A2 on the engine node; per_file ran "
                        "at 64 threads"})
    rows.append(ref)
write("O17_scaling", cols, rows)

# ---------------------------------------------------------------- O10_low_memory
cols = ("group class grade sample role psm_std psm_lm pep_std pep_lm identical wall_std wall_lm wall_ratio cpu_std "
        "cpu_lm cpu_ratio rss_std_gib rss_lm_gib rss_ratio note").split()
rows = []
ratios = {"wall": [], "cpu": [], "rss": []}
for u in units:
    if u["kind"] != "immuno":
        continue
    ps, pp = accepted("prose", u, "psm"), accepted("prose", u, "peptide")
    ws = 3 * 2400 * 0.45 * rng.uniform(0.7, 1.3)
    rs = 120 * rng.uniform(0.6, 1.4)
    wl = None if u["name"] == "pxd019643_DN14_Bladder_classII" else ws * rng.uniform(1.2, 1.5)
    rl = rs * rng.uniform(0.3, 0.45)
    r = {"group": u["group"], "class": u["cls"], "grade": u["grade"], "sample": u["name"], "role": u["role"],
         "psm_std": ps, "psm_lm": ps, "pep_std": pp, "pep_lm": pp, "identical": True, "wall_std": ws, "wall_lm": wl,
         "wall_ratio": wl / ws if wl else None, "cpu_std": ws * 14, "cpu_lm": wl * 14 if wl else None,
         "cpu_ratio": wl / ws if wl else None, "rss_std_gib": rs, "rss_lm_gib": rl, "rss_ratio": rl / rs,
         "note": "" if wl else "incomplete (low_memory r3)"}
    rows.append(r)
    if u["role"] != "decision":
        for k in ratios:
            if r[f"{k}_ratio"] is not None:
                ratios[k].append(r[f"{k}_ratio"])
summary = {c: None for c in cols}
summary.update({"group": "-", "class": "-", "grade": "-", "sample": "median over non-decision samples", "role": "-",
                "identical": True, "wall_ratio": sorted(ratios["wall"])[len(ratios["wall"]) // 2],
                "cpu_ratio": sorted(ratios["cpu"])[len(ratios["cpu"]) // 2],
                "rss_ratio": sorted(ratios["rss"])[len(ratios["rss"]) // 2], "note": "summary"})
rows.append(summary)
write("O10_low_memory", cols, rows)

# ---------------------------------------------------------------- O19_calibration_counts
cols = ("unit class grade group engine arm level accepted_td ratio_to_main fdp_shuffled_mean fdp_shuffled_sd "
        "fdp_shuffled_n fdp_natural status").split()
rows = []
for name in D.CAL_RUNS:
    u = by_name[name]
    for e, arms in (("prose", ("main", "cal_off")), ("sage", ("main",)), ("msfragger", ("main", "cal1", "cal0"))):
        for arm in arms:
            for level in D.LEVELS:
                main = accepted(e, u, level)
                failed = (e == "msfragger" and arm == "cal0" and name == "tims_plasma_30min")
                f = {"main": 1.0, "cal_off": rng.uniform(0.9, 0.99), "cal1": rng.uniform(0.96, 1.01),
                     "cal0": rng.uniform(0.85, 0.97)}[arm]
                acc = None if failed or main is None else int(main * f)
                fd = [0.008 * rng.uniform(0.7, 1.3) for _ in range(3)] if u["shuffled"] and acc else []
                m = math.fsum(fd) / len(fd) if fd else None
                rows.append({"unit": name, "class": u["cls"], "grade": u["grade"], "group": u["group"], "engine": e,
                             "arm": arm, "level": level, "accepted_td": acc,
                             "ratio_to_main": (acc / main if acc and main else None),
                             "fdp_shuffled_mean": m,
                             "fdp_shuffled_sd": (math.sqrt(math.fsum((x - m) ** 2 for x in fd) / 2) if fd else None),
                             "fdp_shuffled_n": len(fd),
                             "fdp_natural": 0.009 * rng.uniform(0.8, 1.2) if u["natural"] and acc else None,
                             "status": "failed stage search repetition 1 exit 1" if failed else
                             ("zero" if main == 0 else "ok")})
write("O19_calibration_counts", cols, rows)

# ---------------------------------------------------------------- O20 and O21 (calib.py columns) with _datasets
def dataset_rows(key, name, level, results, extra):
    out = []
    for g in sorted({u["group"] for u, _, _ in results}, key=D.order_key):
        xs = [ratio for u, ratio, used in results if u["group"] == g and used]
        gm = gmean(xs) if xs else None
        r = {key: name, "level": level, "kind": D.kind(g), "side": D.side(g) or "-", "class": D.cls(g),
             "grade": D.grade(g), "group": g, "n_units": sum(1 for u, _, _ in results if u["group"] == g),
             "n_used": len(xs), "gmean": gm, "lead_pct": None if gm is None else 100 * (gm - 1),
             "note": "" if xs else "no used run"}
        r.update(extra)
        out.append(r)
    return out


cols = ("pair level kind class grade group unit role prose_n_seeds prose comparator_n_seeds comparator ratio used "
        "reason fdp_prose fdp_comparator fdp_n_shared").split()
dcols = ("pair level kind side class grade group n_units n_used gmean lead_pct sum_ratio sum_lead_pct "
         "fdp_prose_mean fdp_comparator_mean fdp_n_runs note").split()
rows, drows = [], []
for comp in ("msfragger", "sage"):
    for level in D.LEVELS:
        results = []
        for u in tryptic:
            p, c = accepted("prose", u, level), accepted(comp, u, level)
            used = u["role"] != "decision" and bool(p) and bool(c)
            ratio = p / c * rng.uniform(0.95, 1.0) if p and c else None
            results.append((u, ratio, used))
            rows.append({"pair": f"prose/{comp}", "level": level, "kind": u["kind"], "class": u["cls"],
                         "grade": u["grade"], "group": u["group"], "unit": u["name"], "role": u["role"],
                         "prose_n_seeds": 3, "prose": p, "comparator_n_seeds": 3 if c is not None else 0,
                         "comparator": c, "ratio": ratio, "used": used,
                         "reason": "" if used else ("decision" if u["role"] == "decision" else f"{comp}:zero"),
                         "fdp_prose": 0.0095, "fdp_comparator": 0.0098, "fdp_n_shared": 3})
        drows += dataset_rows("pair", f"prose/{comp}", level, results,
                              {"sum_ratio": None, "sum_lead_pct": None, "fdp_prose_mean": 0.0095,
                               "fdp_comparator_mean": 0.0098, "fdp_n_runs": 3})
write("O20_external_percolator", cols, rows)
write("O20_external_percolator_datasets", dcols, drows)


def summary_rows(key, drows, scopes, extra):
    """calib.py's _summary rows: per comparison, level and scope the equal-weight gmean of the dataset gmeans with
    a used run (no random numbers: the other tables stay as they are)."""
    out = []
    for name in dict.fromkeys(r[key] for r in drows):
        for level in D.LEVELS:
            for scope in scopes:
                ds = [r for r in drows if r[key] == name and r["level"] == level and r["n_used"]
                      and (scope == "pred_groups" or r["kind"] == scope)]
                e = gmean([r["gmean"] for r in ds]) if ds else None
                r = {key: name, "level": level, "scope": scope, "n_datasets": len(ds),
                     "n_runs": sum(r["n_used"] for r in ds), "equal_weight": e,
                     "lead_pct": None if e is None else 100 * (e - 1), "dropped_datasets": "-"}
                r.update(extra(e))
                out.append(r)
    return out


write("O20_external_percolator_summary",
      "pair level scope n_datasets n_runs equal_weight lead_pct run_weighted rw_lead_pct sum_ratio sum_lead_pct "
      "dropped_datasets".split(),
      summary_rows("pair", drows, ("heldout", "tuning"),
                   lambda e: {"run_weighted": e, "rw_lead_pct": None if e is None else 100 * (e - 1),
                              "sum_ratio": None, "sum_lead_pct": None}))

cols = ("comparison level kind class grade group unit role instrument numerator denominator ratio used reason "
        "fdp_numerator fdp_denominator fdp_n_shared").split()
dcols = ("comparison level kind side class grade group instrument n_units n_used gmean lead_pct fdp_numerator_mean "
         "fdp_denominator_mean fdp_n_runs note").split()
rows, drows = [], []
for name, lead in (("peptdeep_vs_msbooster", 1.06), ("peptdeep_vs_main", 1.04), ("msbooster_vs_main", 1.09)):
    for level in D.LEVELS:
        results = []
        for g in D.PRED_GROUPS:
            for u in (u for u in units if u["group"] == g):
                den = accepted("prose", u, level)
                ratio = lead * rng.uniform(0.96, 1.04)
                used = u["role"] != "decision"
                results.append((u, ratio, used))
                rows.append({"comparison": name, "level": level, "kind": u["kind"], "class": u["cls"],
                             "grade": u["grade"], "group": g, "unit": u["name"], "role": u["role"],
                             "instrument": "Lumos", "numerator": int(den * ratio), "denominator": den,
                             "ratio": ratio, "used": used, "reason": "" if used else "decision",
                             "fdp_numerator": None, "fdp_denominator": None, "fdp_n_shared": 0})
        drows += dataset_rows("comparison", name, level, results,
                              {"instrument": "Lumos", "fdp_numerator_mean": None, "fdp_denominator_mean": None,
                               "fdp_n_runs": 0})
write("O21_prediction", cols, rows)
write("O21_prediction_datasets", dcols, drows)
write("O21_prediction_summary",
      "comparison level scope n_datasets n_runs equal_weight lead_pct dropped_datasets msbooster_version".split(),
      summary_rows("comparison", drows, ("pred_groups",), lambda e: {"msbooster_version": "4.0.0"}))

# ---------------------------------------------------------------- O14_coverage (ids.py columns): per_file td only
cols = "engine benchmark unit database db_design kind class grade group role state status counted".split()
rows = []
for u in units:
    for e in D.ENGINES:
        st = status(e, u)
        if st.startswith("not_run_by_design"):
            st = "not_run_by_design (no z+1 ions in Sage 0.14.7)"  # the status text of the trial tables
        rows.append({"engine": e, "benchmark": "per_file", "unit": u["name"], "database": u["name"] + "_td",
                     "db_design": "td", "kind": u["kind"], "class": u["cls"], "grade": u["grade"], "group": u["group"],
                     "role": u["role"], "state": st.split()[0], "status": st, "counted": st == "ok"})
write("O14_coverage", cols, rows)
