#!/usr/bin/env python3
"""Over-tuning check of DATASETS.md, section 4.6.

ProSE's lead over MSFragger and over Sage on the 7 tuning datasets against its lead on the 10 held-out tryptic
datasets, from the counts of the main benchmark. No search of its own.

  python3 overtuning.py --work W                 W/counts.tsv and runs.tsv (column role) -> the sentence on stdout,
                                                 the figure data in W/overtuning_<level>.tsv
  python3 overtuning.py --work W --level peptide the same for peptides (supplement)
  python3 overtuning.py --test                   the rule on made-up numbers

Per run: ProSE / engine of the target PSMs at q <= 0.01 on the plain database (per_file). Per dataset (a group of
runs.tsv): the geometric mean over its runs that both engines completed, decision runs left out. Per side: the
geometric mean over its datasets, each with the same weight, as a lead in percent. Gap: tuning lead - held-out lead,
in percentage points, for each engine, and again without each dataset in turn. Version of the sentence: (a) both gaps
at most 3 points; (b) otherwise, both gaps at most 3 points without one dataset (the one with the smallest larger gap);
(c) otherwise. The sentence calls the tuning runs and datasets the runs used to develop ProSE and the development
datasets (DATASETS.md 4.6, amendment of 2026-11-28); the code, the printout and the figure data keep "tuning".
"""
import argparse
import csv
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TUNING = ("velos", "lumos_tmt", "hfx", "lumos_lfq", "eclipse_tmtpro", "astral", "tims_plasma")
HELDOUT = ("ups1_control", "pxd042233_lumos_cid", "pxd011695_HCD", "iprg2015", "hela_qe_hf", "hela_exploris480",
           "astral_s1", "astral_250pg", "ultra2_s2", "ultra2_hye")
ENGINES = ("msfragger", "sage")
NAMES = {"msfragger": "MSFragger", "sage": "Sage"}
MARGIN = 3.0  # percentage points, fixed in section 4.6


def gmean(xs):
    return math.exp(sum(math.log(x) for x in xs) / len(xs))


def side_leads(ds, without=None):
    """ds = {engine: {dataset: value}} -> {engine: (tuning lead, held-out lead, gap)}, leads in percent."""
    out = {}
    for e in ENGINES:
        t = [v for d, v in ds[e].items() if d in TUNING and d != without]
        h = [v for d, v in ds[e].items() if d in HELDOUT and d != without]
        if not t or not h:
            return None  # a side without datasets
        lt, lh = 100 * (gmean(t) - 1), 100 * (gmean(h) - 1)
        out[e] = (lt, lh, lt - lh)
    return out


def rule(ds):
    """The version of the sentence: (version, dataset of version b or None, full leads, leave-one-out leads)."""
    full = side_leads(ds)
    assert full, "a side has no dataset completed by ProSE and both engines"
    loo = {d: side_leads(ds, d) for d in TUNING + HELDOUT if any(d in ds[e] for e in ENGINES)}
    loo = {d: g for d, g in loo.items() if g}
    if all(full[e][2] <= MARGIN for e in ENGINES):
        return "a", None, full, loo
    ok = [d for d, g in loo.items() if all(g[e][2] <= MARGIN for e in ENGINES)]
    if ok:
        return "b", min(ok, key=lambda d: max(loo[d][e][2] for e in ENGINES)), full, loo
    return "c", None, full, loo


def sentence(version, best, full, loo, n_t, n_h, unit):
    """n_t, n_h: {engine: number of datasets used} on each side."""
    def more(x, who):
        return f"{abs(x):.1f}% {'more' if x >= 0 else 'fewer'} {unit + ' ' if who == 'MSFragger' else ''}than {who}"

    def count(n, total):
        a, b = n["msfragger"], n["sage"]
        return f"{a}" if a == b else f"{a} (for Sage {b})"
    m, s = full["msfragger"], full["sage"]
    # the words of 2026-11-28: the tuning runs and datasets are those used to develop ProSE (DATASETS.md 4.6)
    text = (f"On the {count(n_h, 10)} held-out tryptic datasets, which contain none of the 20 runs used to develop "
            f"ProSE, ProSE identified {more(m[1], 'MSFragger')} and {more(s[1], 'Sage')}, against {m[0]:+.1f}% and "
            f"{s[0]:+.1f}% on the {count(n_t, 7)} development datasets")
    if version == "a":
        text += ", so there is no sign that developing ProSE on these data inflated its lead"
    elif version == "b":
        bm, bs = loo[best]["msfragger"], loo[best]["sage"]
        text += (f", a difference that comes from one dataset, {best} (without it {bm[0]:+.1f}% and {bs[0]:+.1f}% "
                 f"against {bm[1]:+.1f}% and {bs[1]:+.1f}%)")
    else:
        who = " and ".join(NAMES[e] for e in ENGINES if full[e][2] > MARGIN)
        text += f", so the lead over {who} is smaller on the held-out datasets"
    return (text + "; all other summary ratios of identifications in the abstract and main text are from held-out "
            "datasets.")


def load(runs_path, counts_path, level):
    """-> ({engine: {dataset: value}}, figure rows, notes)."""
    runs = list(csv.DictReader(open(runs_path, encoding="utf-8"), delimiter="\t"))
    assert runs and "role" in runs[0], f"{runs_path}: no column role (DATASETS.md section 5, task 14)"
    groups = {r["group"] for r in runs}
    assert set(TUNING + HELDOUT) <= groups, f"datasets missing in {runs_path}: {sorted(set(TUNING + HELDOUT) - groups)}"
    use = [r for r in runs if r["group"] in TUNING + HELDOUT and r["role"] != "decision"]
    for r in use:
        want = "tuned" if r["group"] in TUNING else "heldout"
        assert r["role"] == want, f"{r['id']}: role {r['role']}, expected {want} or decision"
    plain = {r["id"]: r["db"] + "_td" for r in use}
    acc = {}
    for c in csv.DictReader(open(counts_path, encoding="utf-8"), delimiter="\t"):
        if (c["benchmark"] == "per_file" and c["level"] == level and c["class"] == "all"
                and abs(float(c["q_value"]) - 0.01) < 1e-9 and plain.get(c["run"]) == c["database"]):
            key = (c["engine"], c["run"])
            assert key not in acc, f"two counts for {key}"
            acc[key] = int(c["accepted"])
    ds, rows, notes = {e: {} for e in ENGINES}, [], []
    for e in ENGINES:
        for d in TUNING + HELDOUT:
            ratios = []
            for r in (x for x in use if x["group"] == d):
                p, q = acc.get(("prose", r["id"])), acc.get((e, r["id"]))
                if not p or not q:  # not completed (or nothing accepted) by one of the two: pairwise rule
                    notes.append(f"{NAMES[e]}: {r['id']} left out (ProSE {p}, {NAMES[e]} {q})")
                    continue
                ratios.append((r["id"], p / q))
            if not ratios:
                notes.append(f"{NAMES[e]}: dataset {d} left out (no run completed by both)")
                continue
            ds[e][d] = gmean([x for _, x in ratios])
            side = "tuning" if d in TUNING else "heldout"
            rows += [(NAMES[e], side, d, i, f"{x:.6f}", f"{ds[e][d]:.6f}") for i, x in ratios]
    return ds, rows, notes


def report(ds, rows, notes, out, unit):
    version, best, full, loo = rule(ds)
    n_t = {e: len([d for d in ds[e] if d in TUNING]) for e in ENGINES}
    n_h = {e: len([d for d in ds[e] if d in HELDOUT]) for e in ENGINES}
    for n in notes:
        print("#", n)
    print("dataset\tside\t" + "\t".join(f"ProSE/{NAMES[e]}" for e in ENGINES))
    for d in TUNING + HELDOUT:
        print(f"{d}\t{'tuning' if d in TUNING else 'heldout'}\t"
              + "\t".join(f"{100 * (ds[e][d] - 1):+.1f}%" if d in ds[e] else "NA" for e in ENGINES))
    for e in ENGINES:
        lt, lh, g = full[e]
        print(f"{NAMES[e]}: tuning lead {lt:+.1f}%, held-out lead {lh:+.1f}%, gap {g:+.1f} points")
    print("left out\t" + "\t".join(f"gap {NAMES[e]}" for e in ENGINES))
    for d, g in loo.items():
        print(f"{d}\t" + "\t".join(f"{g[e][2]:+.1f}" for e in ENGINES))
    print(f"version {version}" + (f" ({best})" if best else ""))
    print(sentence(version, best, full, loo, n_t, n_h, unit))
    if out:
        with open(out, "w", encoding="utf-8") as f:
            f.write("engine\tside\tdataset\trun\tratio\tdataset_value\n" + "".join("\t".join(r) + "\n" for r in rows))
        print(f"figure data: {out}")
    return version, best


def test():
    def ds(t, h):
        v = {d: t.get(d, t["*"]) for d in TUNING}
        v.update({d: h.get(d, h["*"]) for d in HELDOUT})
        return {e: dict(v) for e in ENGINES}
    assert rule(ds({"*": 1.05}, {"*": 1.05}))[0] == "a"
    assert rule(ds({"*": 1.03}, {"*": 1.05}))[0] == "a"  # held-out lead larger: (a)
    assert rule(ds({"*": 1.03, "astral": 1.40}, {"*": 1.03}))[:2] == ("b", "astral")
    assert rule(ds({"*": 1.03}, {"*": 1.03, "astral_250pg": 0.60}))[:2] == ("b", "astral_250pg")
    assert rule(ds({"*": 1.10}, {"*": 1.02}))[0] == "c"
    n_t, n_h = {e: 7 for e in ENGINES}, {e: 10 for e in ENGINES}
    v = rule(ds({"*": 0.97}, {"*": 0.90}))
    text = sentence(*v, n_t, n_h, "PSMs")
    assert v[0] == "c" and "10.0% fewer PSMs than MSFragger" in text and "-3.0%" in text and "over MSFragger and Sage" in text
    v = rule({"msfragger": ds({"*": 1.05}, {"*": 1.05})["msfragger"], "sage": ds({"*": 1.10}, {"*": 1.02})["sage"]})
    assert v[0] == "c" and "lead over Sage is smaller" in sentence(*v, n_t, n_h, "PSMs")
    v = rule(ds({"*": 1.03, "astral": 1.40, "velos": 1.40}, {"*": 1.03}))  # two datasets needed: not (b)
    assert v[0] == "c"
    # the words of 2026-11-28 in every version: "developed", never "tuning" (DATASETS.md 4.6)
    for want, t, h in (("a", {"*": 1.05}, {"*": 1.05}), ("b", {"*": 1.03, "astral": 1.40}, {"*": 1.03}),
                       ("c", {"*": 1.10}, {"*": 1.02})):
        v = rule(ds(t, h))
        text = sentence(*v, n_t, n_h, "PSMs")
        assert v[0] == want and "tuning" not in text, (want, text)
        assert "which contain none of the 20 runs used to develop ProSE, ProSE identified" in text, text
        assert "on the 7 development datasets" in text, text
        assert ("so there is no sign that developing ProSE on these data inflated its lead;" in text) == (want == "a")
    print(sentence(*rule(ds({"*": 1.03, "astral": 1.40}, {"*": 1.03})), n_t, n_h, "PSMs"))
    print("test: ok")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--work", help="work directory with counts.tsv (bench.py collect)")
    p.add_argument("--runs", default=os.path.join(HERE, "runs.tsv"), help="run table (default: runs.tsv next to this file)")
    p.add_argument("--level", default="psm", choices=("psm", "peptide"))
    p.add_argument("--test", action="store_true")
    a = p.parse_args()
    if a.test:
        return test()
    if not a.work:
        p.error("--work or --test")
    ds, rows, notes = load(a.runs, os.path.join(a.work, "counts.tsv"), a.level)
    report(ds, rows, notes, os.path.join(a.work, f"overtuning_{a.level}.tsv"), "PSMs" if a.level == "psm" else "peptides")


if __name__ == "__main__":
    sys.exit(main())
