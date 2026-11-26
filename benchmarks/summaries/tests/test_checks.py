"""Tests of the consistency layer checks.py (SPEC 5, 6): for every check C1-C25 its PASS path and its WARN/FAIL path
(at least one each; C18 is INFO-only), on the foundation fixtures plus the checks_* fixtures (versions, mzml_counts,
references, listing). Hand-computed cases: T19 (C5, C12 PASS over the limit), T27 (C25 WARN on decision runs only),
T29 (C8 tolerance), T30 (C11 WARN), T31 (C24 stale_timing), T35 (C3 outside the design). T34 (blind sealing) is
dropped: there is no blind mode.

The checks run with the fixture design (SPEC 6): FX_EXPECTED replaces the paper's expected values of C11, C14, C15.
counts_fx.tsv prints combined_fdp as EE does, N_E/N (1 + T/E) (EE-lib:30-34), with 4 significant digits; the C8
tests check it as written and on copies recomputed with fix_fdp (fixed_counts) or edited."""
import dataclasses
import os
import re
import shutil
import sys
import tempfile
import unittest
import warnings

sys.dont_write_bytecode = True

from summaries import checks, design, fdp, tables as T  # noqa: E402

OT = design.OT
FX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")
COUNTS_HEADER = T.COUNTS_HEADER
COVERAGE_HEADER = T.COVERAGE_HEADER
TIMINGS_HEADER = T.TIMINGS_HEADER


def fx(name):
    return os.path.join(FX, name)


def _runs_used():
    """Non-decision runs per tryptic dataset of runs_fx.tsv (the fixture's DS:860-878)."""
    _, rows = T.read_tsv(fx("runs_fx.tsv"))
    out = {}
    for _, r in rows:
        if r["group"] in checks.TRYPTIC and r["role"] != "decision":
            out[r["group"]] = out.get(r["group"], 0) + 1
    return {g: out.get(g, 0) for g in checks.TRYPTIC}


FX_EXPECTED = {
    "batch_groups": ("astral_250pg",),
    "decision": ("DN13_r1", "DN13_r2", "astral250pg_A2"),
    "runs_used": _runs_used(),
    "ms2_tuned": 91000,  # checks_mzml_counts_fx.tsv: 10000 + 11000 + ... + 16000 over the 7 tuned runs
}


def options(**kw):
    """Options of the base fixture (runs_fx + counts/coverage/timings_fx), nothing written."""
    o = dict(runs=fx("runs_fx.tsv"), counts=fx("counts_fx.tsv"), coverage=fx("coverage_fx.tsv"),
             timings=fx("timings_fx.tsv"), versions=None, params_dir=fx("params_fx"), references=None,
             mzml_counts=None)
    o.update(kw)
    return T.Options(**o)


def smoke_options(**kw):
    o = dict(runs=fx("runs_smoke_fx.tsv"), design="none", counts=fx("counts_smoke_fx.tsv"),
             coverage=fx("coverage_smoke_fx.tsv"), timings=fx("timings_smoke_fx.tsv"), versions=None,
             params_dir=fx("params_fx"), references=None, mzml_counts=None)
    o.update(kw)
    return T.Options(**o)


def run_checks(ctx, expected=FX_EXPECTED, prepare=None):
    """checks.run on ctx; returns the lines it added [(level, cid, message)]."""
    if prepare:
        prepare(ctx)
    n0 = len(ctx.report.lines)
    checks.run(ctx, expected)
    return ctx.report.lines[n0:]


def of(lines, cid):
    return [(lv, m) for lv, c, m in lines if c == cid]


def levels(lines, cid):
    return {lv for lv, _ in of(lines, cid)}


def copy_with(src, dst, edit=None, keep=None, add=()):
    """A copy of a fixture TSV: keep(line) filters data lines, edit(line) -> line rewrites them, add appends lines."""
    with open(src, encoding="utf-8", newline="") as f:
        lines = f.read().splitlines()
    out = [lines[0]]
    for line in lines[1:]:
        if keep and not keep(line):
            continue
        out.append(edit(line) if edit else line)
    out += list(add)
    with open(dst, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(out) + "\n")
    return dst


def cells(line, header):
    return dict(zip(header, line.split("\t")))


def join(d, header):
    return "\t".join(d[c] for c in header)


def fix_fdp(line):
    """combined_fdp and lower_bound_fdp as EE prints them (EE-lib:30-34; EE-tool:188-194: 4 significant digits)."""
    d = cells(line, COUNTS_HEADER)
    n, ne, te = int(d["accepted"]), int(d["entrapment"]), float(d["te_ratio"])
    d["combined_fdp"] = f"{ne * (1 + te) / n:.4g}" if n else "0"
    d["lower_bound_fdp"] = f"{ne / n:.4g}" if n else "0"
    return join(d, COUNTS_HEADER)


def match(*values):
    """keep/edit predicate on the first cells of a line (engine, benchmark, run, database, ...)."""
    def f(line):
        c = line.split("\t")
        return all(v is None or c[i] == v for i, v in enumerate(values))
    return f


class Temp(unittest.TestCase):
    def setUp(self):
        warnings.simplefilter("ignore", ResourceWarning)  # OT.load leaves its csv files to the collector (OT:92, 102)
        self.tmp = tempfile.mkdtemp(prefix="checks_test_")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def path(self, *names):
        return os.path.join(self.tmp, *names)

    def work(self, counts=None, coverage=None, timings=None, versions=None, overtuning=False, name="W"):
        """A work folder W with the fixture tables (or the given ones); overtuning: W/overtuning_<level>.tsv written
        from OT.load as overtuning.py writes them (OT:147)."""
        w = self.path(name)
        os.makedirs(w, exist_ok=True)
        for src, fname in ((counts or fx("counts_fx.tsv"), "counts.tsv"),
                           (coverage or fx("coverage_fx.tsv"), "coverage.tsv"),
                           (timings or fx("timings_fx.tsv"), "timings.tsv")):
            if os.path.abspath(src) != os.path.abspath(os.path.join(w, fname)):
                shutil.copy(src, os.path.join(w, fname))
        if versions:
            shutil.copy(versions, os.path.join(w, "versions.txt"))
        if overtuning:
            for level in design.LEVELS:
                _, rows, _ = OT.load(fx("runs_fx.tsv"), os.path.join(w, "counts.tsv"), level)
                with open(os.path.join(w, f"overtuning_{level}.tsv"), "w", encoding="utf-8", newline="\n") as f:
                    f.write(checks.OT_HEADER + "\n" + "".join("\t".join(r) + "\n" for r in rows))
        return w

    def load_work(self, w, **kw):
        o = dict(runs=fx("runs_fx.tsv"), work=w, params_dir=fx("params_fx"), references=None, mzml_counts=None)
        o.update(kw)
        return T.load(T.Options(**o))

    def fixed_counts(self, name="counts_fixed.tsv", edit=None):
        def both(line):
            line = fix_fdp(line)
            return edit(line) if edit else line
        return copy_with(fx("counts_fx.tsv"), self.path(name), edit=both)


# ---------------------------------------------------------------- the ids tables of O2/O4, as SPEC 3.1/3.5 name them
def build_o2(ctx, numbers=True):
    """O02_pairs_runs/datasets/summary and O04_overtuning_<level>_sides with the SPEC columns, made from ctx with the
    package's helpers (T.gmean, fsum), as ids.py would: the C6/C16/C20 inputs."""
    runs, dsets, sums = [], [], []
    for pair in design.PAIRS:
        name = "_".join(pair)
        for level in ctx.levels:
            r_names = {u.name for u in ctx.R(pair, level)}
            g_of = {}
            for u in ctx.units:
                if u.group not in checks.TRYPTIC:
                    continue
                p, q = ctx.accepted(pair[0], u, level), ctx.accepted(pair[1], u, level)
                ratio = p / q if isinstance(p, int) and isinstance(q, int) and q else T.Missing("zero")
                used = u.name in r_names
                runs.append({"pair": name, "level": level, "kind": u.kind, "class": u.cls, "grade": u.grade,
                             "group": u.group, "unit": u.name, "role": u.role, "prose": p, "comparator": q,
                             "ratio": ratio, "used": "yes" if used else "no", "reason": ""})
                if used:
                    g_of.setdefault(u.group, []).append(ratio)
            for g in checks.TRYPTIC:
                gm = T.gmean(g_of.get(g, []))
                dsets.append({"pair": name, "level": level, "kind": design.kind(g), "side": design.side(g),
                              "class": design.cls(g), "grade": design.grade(g), "group": g,
                              "n_units": len(ctx.groups[g].units), "n_used": len(g_of.get(g, [])), "gmean": gm,
                              "lead_pct": T.lead(gm), "sum_ratio": T.Missing("not_computed"),
                              "sum_lead_pct": T.Missing("not_computed"), "note": ""})
            for scope, names in (("heldout", OT.HELDOUT), ("tuning", OT.TUNING)):
                gs = [d["gmean"] for d in dsets if d["pair"] == name and d["level"] == level
                      and d["group"] in names and not T.is_missing(d["gmean"])]
                e = T.gmean(gs)
                sums.append({"pair": name, "level": level, "scope": scope, "n_datasets": len(gs), "n_runs": 0,
                             "equal_weight": e, "lead_pct": T.lead(e), "run_weighted": T.Missing("not_computed"),
                             "rw_lead_pct": T.Missing("not_computed"), "sum_ratio": T.Missing("not_computed"),
                             "sum_lead_pct": T.Missing("not_computed"), "dropped_datasets": ""})
                if numbers:
                    ctx.number(f"ids.{scope}.{level}.{pair[1]}.lead", T.lead(e), source_side=scope)
    ctx.write_table("O02_pairs_runs", ["pair", "level", "kind", "class", "grade", "group", "unit", "role", "prose",
                                       "comparator", "ratio", "used", "reason"], runs)
    ctx.write_table("O02_pairs_datasets", ["pair", "level", "kind", "side", "class", "grade", "group", "n_units",
                                           "n_used", "gmean", "lead_pct", "sum_ratio", "sum_lead_pct", "note"], dsets)
    ctx.write_table("O02_pairs_summary", ["pair", "level", "scope", "n_datasets", "n_runs", "equal_weight",
                                          "lead_pct", "run_weighted", "rw_lead_pct", "sum_ratio", "sum_lead_pct",
                                          "dropped_datasets"], sums)
    for level in ctx.levels:
        srows = []
        for e in OT.ENGINES:
            pick = {s["scope"]: s for s in sums if s["level"] == level and s["pair"] == "prose_" + e}
            lt, lh = pick["tuning"]["lead_pct"], pick["heldout"]["lead_pct"]
            gap = T.Missing("skipped") if T.is_missing(lt) or T.is_missing(lh) else lt - lh
            srows.append({"comparator": e, "n_tuning": pick["tuning"]["n_datasets"], "L_T": lt,
                          "n_heldout": pick["heldout"]["n_datasets"], "L_H": lh, "gap": gap,
                          "within_margin": gap if T.is_missing(gap) else ("yes" if gap <= OT.MARGIN else "no")})
            if numbers:
                ctx.number(f"overtuning.{level}.lt_{e}", lt, source_side="tuning")
                ctx.number(f"overtuning.{level}.lh_{e}", lh, source_side="heldout")
        ctx.write_table(f"O04_overtuning_{level}_sides", ["comparator", "n_tuning", "L_T", "n_heldout", "L_H", "gap",
                                                          "within_margin"], srows)


def edit_table(ctx, name, pred, **changes):
    """Changes the cells of the rows of ctx.results[name] for which pred(row) holds; returns how many changed."""
    n = 0
    for row in ctx.results[name]:
        if pred(row):
            row.update(changes)
            n += 1
    return n


# ================================================================ C1-C5
class TestC1C5(Temp):
    def test_c1_pass_and_fail(self):
        lines = run_checks(T.load(options()))
        self.assertEqual(levels(lines, "C1"), {"PASS"})
        cov = copy_with(fx("coverage_fx.tsv"), self.path("cov.tsv"),
                        edit=lambda l: l[:-3] + "no" if match("prose", "per_file", "velos_r1", "hy_td")(l) else l)
        lines = run_checks(T.load(options(coverage=cov)))
        self.assertEqual(levels(lines, "C1"), {"FAIL"})
        self.assertIn("prose/per_file/velos_r1/hy_td", of(lines, "C1")[0][1])

    def test_c2_pass_fail_and_qgrid(self):
        c = T.load(options())
        self.assertEqual(levels(run_checks(c), "C2"), {"PASS"})
        c = T.load(options())  # the loader stops on these; a row changed after loading reaches the check
        c.counts[0] = dataclasses.replace(c.counts[0], q_value=0.05)
        self.assertEqual(levels(run_checks(c), "C2"), {"FAIL"})
        # qgrid SHA256 (SPEC O13): W/counts_qgrid.tsv and W/out with one recorded hash
        w = self.work()
        shutil.copy(fx("fdp_counts_qgrid_fx.tsv"), os.path.join(w, "counts_qgrid.tsv"))
        folder = os.path.join(w, "out", "prose", "per_file", "velos_r1", "hy_td")
        os.makedirs(folder)
        with open(os.path.join(folder, "velos_r1.count.idXML"), "w", encoding="utf-8") as f:
            f.write("<idXML/>\n")
        digest = T.sha256_file(os.path.join(folder, "velos_r1.count.idXML"))
        with open(os.path.join(folder, "count_qgrid.sha256"), "w", encoding="utf-8") as f:
            f.write(digest + "  velos_r1.count.idXML\n")
        lines = run_checks(self.load_work(w))
        self.assertIn(("PASS", "C2"), [(lv, c) for lv, c, m in lines if "qgrid SHA256" in m])
        with open(os.path.join(folder, "velos_r1.count.idXML"), "a", encoding="utf-8") as f:
            f.write("<!-- recounted -->\n")
        c = self.load_work(w, strict=True)
        lines = run_checks(c)
        self.assertTrue(any(lv == "FAIL" and "stale_qgrid" in m for lv, m in of(lines, "C2")))

    def test_c2_qgrid_file_not_read(self):
        """A count_qgrid.sha256 or a count file that cannot be read (a folder of that name stands in for an unreadable
        file): C2 does not raise; the search counts as unverified, and a WARN (not strict) names the file."""
        w = self.work()
        shutil.copy(fx("fdp_counts_qgrid_fx.tsv"), os.path.join(w, "counts_qgrid.tsv"))
        for db, folder_name, file_name in (("hy_td", "count_qgrid.sha256", "velos_r1.count.idXML"),
                                           ("hy_entrap_s1_td", "velos_r1.count.idXML", "count_qgrid.sha256")):
            folder = os.path.join(w, "out", "prose", "per_file", "velos_r1", db)
            os.makedirs(os.path.join(folder, folder_name))
            with open(os.path.join(folder, file_name), "w", encoding="utf-8") as f:
                f.write(("0" * 64 + "  velos_r1.count.idXML\n") if file_name.endswith("sha256") else "<idXML/>\n")
        c = self.load_work(w, strict=True)
        lines = of(run_checks(c), "C2")
        self.assertFalse([m for lv, m in lines if "raised" in m], lines)
        self.assertTrue(any(lv == "PASS" and m.startswith("qgrid SHA256 equal in 0 search folders") for lv, m in lines),
                        lines)
        self.assertIn(("WARN", "2 qgrid file(s) not read (the search counts as unverified): "
                               "prose/per_file/velos_r1/hy_td/count_qgrid.sha256 (IsADirectoryError: Is a directory), "
                               "prose/per_file/velos_r1/hy_entrap_s1_td/velos_r1.count.idXML (IsADirectoryError: Is a "
                               "directory)"), lines)

    def test_c3_pass_missing_outside_t35_and_generic_arm(self):
        lines = run_checks(T.load(options()))
        self.assertEqual(levels(lines, "C3"), {"PASS"})
        cov = copy_with(fx("coverage_fx.tsv"), self.path("cov.tsv"),
                        keep=lambda l: not match("msfragger", "per_file", "hfx_r1", "hye_arath_td")(l))
        cnt = copy_with(fx("counts_fx.tsv"), self.path("cnt.tsv"),
                        keep=lambda l: not match("msfragger", "per_file", "hfx_r1", "hye_arath_td")(l))
        lines = run_checks(T.load(options(coverage=cov, counts=cnt)))
        self.assertIn("FAIL", levels(lines, "C3"))
        # T35: a counted search on a database outside the unit's stems -> excluded, WARN(s); strict FAIL
        extra = [f"prose\tper_file\tvelos_r1\thy_other_td\tvelos_r1.count.idXML\t{lv}\tall\t0.01\t100\t0\t0\t0\tNA\t"
                 f"NA\tNA\t1" for lv in ("psm", "peptide")]
        cnt = copy_with(fx("counts_fx.tsv"), self.path("cnt2.tsv"), add=extra)
        cov = copy_with(fx("coverage_fx.tsv"), self.path("cov2.tsv"),
                        add=["prose\tper_file\tvelos_r1\thy_other_td\tok\tyes"])
        lines = run_checks(T.load(options(counts=cnt, coverage=cov)))
        self.assertEqual([lv for lv, m in of(lines, "C3") if "outside the design" in m], ["WARN"])
        self.assertEqual(levels(lines, "C1"), {"PASS"})  # C1 counts the excluded rows too
        lines = run_checks(T.load(options(counts=cnt, coverage=cov, strict=True)))
        self.assertEqual([lv for lv, m in of(lines, "C3") if "outside the design" in m], ["FAIL"])
        # a further arm (tag outside ARMS, O25): WARN, also without --strict
        cov = copy_with(fx("coverage_fx.tsv"), self.path("cov3.tsv"),
                        add=["prose\tper_file_newarm\tvelos_r1\thy_td\tok\tno"])
        lines = run_checks(T.load(options(coverage=cov)))
        self.assertTrue(any(lv == "WARN" and "per_file_newarm" in m for lv, m in of(lines, "C3")))

    def test_c4_paths(self):
        # base: Sage failed_memory on a class I sample and a failed entrapment search -> WARN(s)
        lines = run_checks(T.load(options()))
        c4 = of(lines, "C4")
        self.assertIn(("PASS", "not_run_by_design exactly on the 4 Sage searches of bycz units (B:1357)"), c4)
        self.assertEqual(sorted(m.split(" search(es) ")[1].split(" ")[0] for lv, m in c4 if lv == "WARN"),
                         ["failed", "failed_memory"])
        self.assertTrue(any(lv == "INFO" and "accepted == 0" in m for lv, m in c4))
        lines = run_checks(T.load(options(strict=True)))
        self.assertEqual({lv for lv, m in of(lines, "C4") if "failed" in m and "search(es)" in m}, {"FAIL"})
        # class II: Sage failed_memory is expected (DS:1011) -> a PASS with the note, no WARN for it
        runs = copy_with(fx("runs_fx.tsv"), self.path("runs.tsv"),
                         edit=lambda l: l.replace("\tpxd058436_classI\t", "\tpxd058436_classII\t")
                         if l.startswith("DN05_r") else l)
        c = T.load(options(runs=runs))
        lines = run_checks(c)
        c4 = of(lines, "C4")
        self.assertTrue(any(lv == "PASS" and "1 expected failed_memory" in m for lv, m in c4))
        self.assertFalse(any(lv == "WARN" and "failed_memory" in m for lv, m in c4))
        # not_run_by_design on a by unit -> FAIL
        cov = copy_with(fx("coverage_fx.tsv"), self.path("cov.tsv"),
                        edit=lambda l: "sage\tper_file\tvelos_r1\thy_td\tnot_run_by_design\tno"
                        if match("sage", "per_file", "velos_r1", "hy_td")(l) else l)
        cnt = copy_with(fx("counts_fx.tsv"), self.path("cnt.tsv"),
                        keep=lambda l: not match("sage", "per_file", "velos_r1", "hy_td")(l))
        lines = run_checks(T.load(options(coverage=cov, counts=cnt)))
        self.assertIn("FAIL", levels(lines, "C4"))
        # smoke: every search ok -> PASS only
        lines = run_checks(T.load(smoke_options()))
        self.assertEqual(levels(lines, "C4"), {"PASS"})

    def test_c5_paths(self):
        lines = run_checks(T.load(options()))
        c5 = of(lines, "C5")
        self.assertTrue(any(lv == "PASS" and "have a complete last attempt" in m for lv, m in c5))
        self.assertTrue(any(lv == "WARN" and m.startswith("no_timing in 1 key") for lv, m in c5))
        self.assertTrue(any(lv == "INFO" and "2 key(s) with earlier attempts" in m for lv, m in c5))
        self.assertTrue(any(lv == "PASS" and "MSFragger batch" in m for lv, m in c5))
        # a coverage-ok timed search without timing rows -> WARN
        tim = copy_with(fx("timings_fx.tsv"), self.path("tim.tsv"),
                        keep=lambda l: not match("prose", "per_file", "velos_r1")(l))
        lines = run_checks(T.load(options(timings=tim)))
        self.assertTrue(any(lv == "WARN" and "prose/per_file/velos_r1/hy_td" in m for lv, m in of(lines, "C5")))
        # MSFragger batch with one rescoring row less in r2 -> stage-set WARN and batch WARN
        dropped = []

        def keep(line):
            if not dropped and match("msfragger", "batch", "astral_250pg", None, "rescoring", None, "2")(line):
                dropped.append(line)
                return False
            return True
        tim = copy_with(fx("timings_fx.tsv"), self.path("tim2.tsv"), keep=keep)
        lines = run_checks(T.load(options(timings=tim)))
        self.assertTrue(any(lv == "WARN" and "MSFragger batch" in m for lv, m in of(lines, "C5")))

    def test_t19_over_limit_c5_c12_pass(self):
        w = self.path("W")
        os.makedirs(w)
        not_scaling = lambda line: line.split("\t")[1] != "scaling"  # noqa: E731
        copy_with(fx("coverage_fx.tsv"), os.path.join(w, "coverage.tsv"), keep=not_scaling)
        copy_with(fx("timings_fx.tsv"), os.path.join(w, "timings.tsv"), keep=not_scaling)
        shutil.copy(fx("counts_fx.tsv"), os.path.join(w, "counts.tsv"))
        o = dict(scaling_coverage=fx("coverage_overlimit_fx.tsv"), scaling_timings=fx("timings_overlimit_fx.tsv"))
        lines = run_checks(self.load_work(w, **o))
        c5 = of(lines, "C5")
        self.assertTrue(any(lv == "PASS" and "2 not_run_over_limit points have none" in m for lv, m in c5))
        self.assertNotIn("FAIL", levels(lines, "C5"))
        self.assertFalse(any(lv == "WARN" and "complete last attempt" in m for lv, m in c5))
        c12 = of(lines, "C12")
        self.assertTrue(any(lv == "PASS" and "repetition 0 only at the top point" in m for lv, m in c12))
        self.assertTrue(any(lv == "PASS" and "hfx_r1: the same grid for prose, msfragger: 16,8,4,2,1" in m
                            for lv, m in c12))
        self.assertTrue(any(lv == "INFO" and "prose/hfx_r1/t2" in m and "msfragger/hfx_r1/t1" in m for lv, m in c12))
        self.assertNotIn("FAIL", levels(lines, "C12"))
        self.assertNotIn("WARN", levels(lines, "C12"))
        # without the over_limit point at 2 the not_run_over_limit point at 1 has nothing above it -> FAIL
        cov = copy_with(fx("coverage_overlimit_fx.tsv"), self.path("cov_ol.tsv"),
                        keep=lambda l: not match("prose", "scaling", "hfx_r1", "hye_td_t2")(l))
        tim = copy_with(fx("timings_overlimit_fx.tsv"), self.path("tim_ol.tsv"),
                        keep=lambda l: not match("prose", "scaling", "hfx_r1", None, None, "2")(l))
        lines = run_checks(self.load_work(w, scaling_coverage=cov, scaling_timings=tim))
        self.assertTrue(any(lv == "FAIL" and "prose/hfx_r1/t1: not_run_over_limit without an over_limit point"
                            in m for lv, m in of(lines, "C12")))
        self.assertTrue(any(lv == "WARN" and "the grids differ" in m for lv, m in of(lines, "C12")))


# ================================================================ C6
class TestC6(Temp):
    def ctx(self, **kw):
        w = self.work(overtuning=True)
        return self.load_work(w, **kw)

    def test_c6_pass(self):
        lines = run_checks(self.ctx(), prepare=build_o2)
        for cid in ("C6a", "C6b", "C6c", "C6d"):
            self.assertEqual(levels(lines, cid), {"PASS"}, (cid, of(lines, cid)))
        self.assertEqual(levels(lines, "C16"), {"PASS"})
        self.assertEqual(levels(lines, "C20"), {"PASS"})
        self.assertEqual(levels(lines, "C19"), {"PASS"})

    def test_c6_skip_without_tables(self):
        lines = run_checks(self.ctx())
        self.assertIn(("INFO", "SKIP C6a/C6b dataset values: table O02_pairs_datasets absent (not written by this "
                               "build)"), of(lines, "C6a"))
        self.assertTrue(all(lv == "INFO" and "absent" in m for lv, m in of(lines, "C6b")))
        self.assertEqual(levels(lines, "C6c"), {"PASS"})  # the W file needs no table

    def test_c6a_fail(self):
        def prep(c):
            build_o2(c)
            self.assertEqual(edit_table(c, "O02_pairs_datasets", lambda r: r["group"] == "astral"
                                        and r["pair"] == "prose_sage" and r["level"] == "psm",
                                        gmean=None), 1)
            for r in c.results["O02_pairs_datasets"]:
                if r["group"] == "velos" and r["pair"] == "prose_msfragger" and r["level"] == "psm":
                    r["gmean"] = r["gmean"] * (1 + 1e-9)
        lines = run_checks(self.ctx(), prepare=prep)
        c6a = of(lines, "C6a")
        self.assertTrue(any(lv == "FAIL" and m.startswith("psm: 2 dataset value(s)") and "Sage astral (package NA)"
                            in m and "MSFragger velos" in m for lv, m in c6a), c6a)
        self.assertIn("PASS", {lv for lv, m in c6a if m.startswith("peptide")})

    def test_c6a_within_tolerance(self):
        def prep(c):
            build_o2(c)
            for r in c.results["O02_pairs_datasets"]:
                if r["group"] == "velos" and r["level"] == "psm" and not T.is_missing(r["gmean"]):
                    r["gmean"] = r["gmean"] * (1 + 1e-13)  # fsum against OT's plain sum (OT:34-35)
        self.assertEqual(levels(run_checks(self.ctx(), prepare=prep), "C6a"), {"PASS"})

    def test_c6b_fail(self):
        def prep(c):
            build_o2(c)
            edit_table(c, "O02_pairs_runs", lambda r: r["unit"] == "hfx_r1" and r["pair"] == "prose_msfragger"
                       and r["level"] == "peptide", prose=1)
            edit_table(c, "O02_pairs_runs", lambda r: r["unit"] == "astral_r1" and r["pair"] == "prose_sage"
                       and r["level"] == "peptide", used="no")
        lines = run_checks(self.ctx(), prepare=prep)
        bad = [m for lv, m in of(lines, "C6b") if lv == "FAIL"]
        self.assertTrue(any("peptide: run ratios" in m and "1 only in OT: Sage tuning astral astral_r1" in m
                            and "1 strings differ: MSFragger tuning hfx hfx_r1" in m for m in bad), bad)
        self.assertEqual(levels(lines, "C16"), {"FAIL"})  # used != R for the changed row

    def test_c6c_warn(self):
        c = self.ctx()
        path = os.path.join(c.work, "overtuning_psm.tsv")
        with open(path, encoding="utf-8") as f:
            text = f.read().splitlines()
        cells_ = text[1].split("\t")
        cells_[4] = "9.999999"
        text[1] = "\t".join(cells_)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(text) + "\n")
        os.remove(os.path.join(c.work, "overtuning_peptide.tsv"))
        lines = run_checks(self.load_work(c.work))
        c6c = of(lines, "C6c")
        self.assertIn(("WARN", "psm: W/overtuning_psm.tsv differs from OT's rows: 1 row(s) only in the file, 1 only "
                               "in OT's rows"), c6c)
        self.assertTrue(any(lv == "WARN" and "overtuning_peptide.tsv missing" in m for lv, m in c6c))
        lines = run_checks(self.load_work(c.work, strict=True))
        self.assertEqual(levels(lines, "C6c"), {"FAIL"})

    def test_c6c_older_is_a_plain_warn(self):
        """OPEN Q61 (SPEC 3.5, C6c): a kept file older than counts.tsv -> WARN only, also under --strict; C18 INFO."""
        c = self.ctx(listing=fx("checks_listing_fx.ls"))
        lines = run_checks(c, prepare=build_o2)
        c6c = of(lines, "C6c")
        self.assertEqual([lv for lv, _ in c6c], ["PASS", "WARN", "PASS", "WARN"], c6c)
        self.assertIn(("PASS", "psm: W/overtuning_psm.tsv == OT's 35 rows as strings"), c6c)
        self.assertIn(("WARN", "psm: W/overtuning_psm.tsv older than counts.tsv (C18); its rows equal OT's, so WARN "
                               "only, not strict (OPEN Q61)"), c6c)
        c18 = of(lines, "C18")
        self.assertIn(("INFO", "W/overtuning_psm.tsv older than counts.tsv (--listing: Nov 21 13:32 < Nov 21 16:39); "
                               "its content is compared by C6c (WARN there, OPEN Q61)"), c18)
        strict = run_checks(self.load_work(c.work, listing=fx("checks_listing_fx.ls"), strict=True), prepare=build_o2)
        self.assertEqual([lv for lv, _ in of(strict, "C6c")], ["PASS", "WARN", "PASS", "WARN"])
        # not older (mtimes of the temporary W: overtuning written after counts.tsv): no WARN
        self.assertEqual(levels(run_checks(self.load_work(c.work), prepare=build_o2), "C6c"), {"PASS"})

    def test_c6d_fail(self):
        def prep(c):
            build_o2(c)
            edit_table(c, "O02_pairs_summary", lambda r: r["pair"] == "prose_sage" and r["level"] == "psm"
                       and r["scope"] == "heldout", lead_pct=1.0)
            for r in c.results["O04_overtuning_peptide_sides"]:
                if r["comparator"] == "msfragger":
                    r["L_T"] = r["L_T"] + 2e-9
        lines = run_checks(self.ctx(), prepare=prep)
        c6d = of(lines, "C6d")
        self.assertTrue(any(lv == "FAIL" and m.startswith("psm: 1 lead(s)") and "O02_pairs_summary heldout sage" in m
                            for lv, m in c6d), c6d)
        self.assertTrue(any(lv == "FAIL" and m.startswith("peptide: 1 lead(s)")
                            and "O04_overtuning_peptide_sides L_T tuning msfragger" in m for lv, m in c6d), c6d)

    def test_c6_c25_skipped_with_design_none(self):
        lines = run_checks(T.load(smoke_options()))
        self.assertEqual(levels(lines, "C6"), {"INFO"})
        self.assertEqual(levels(lines, "C25"), {"INFO"})


# ================================================================ C7-C10
class TestC7C10(Temp):
    def test_c7(self):
        self.assertEqual(levels(run_checks(T.load(options())), "C7"), {"PASS"})

        def edit(line):
            if match("prose", "per_file", "velos_r1", "hy_td", None, "psm")(line):
                d = cells(line, COUNTS_HEADER)
                d["entrapment"] = "3"
                return join(d, COUNTS_HEADER)
            return line
        cnt = copy_with(fx("counts_fx.tsv"), self.path("cnt.tsv"), edit=edit)
        lines = run_checks(T.load(options(counts=cnt)))
        self.assertEqual(of(lines, "C7"), [("FAIL", "1 td row(s) with entrapment != 0 or te_ratio != 1: "
                                                    "prose/per_file/velos_r1/hy_td/psm")])

    def test_c8_pass_on_ee_formula_and_fail_on_another(self):
        self.assertEqual(levels(run_checks(T.load(options())), "C8"), {"PASS"})  # counts_fx.tsv as written
        lines = run_checks(T.load(options(counts=self.fixed_counts())))
        self.assertEqual(levels(lines, "C8"), {"PASS"})

        def inverse(line):  # N_E/N (1 + E/T): the formula of an earlier fixture generator, which C8 must reject
            d = cells(line, COUNTS_HEADER)
            n, ne, te = int(d["accepted"]), int(d["entrapment"]), float(d["te_ratio"])
            if n and ne and te != 1.0:
                d["combined_fdp"] = f"{ne * (1 + 1 / te) / n:.4g}"
            return join(d, COUNTS_HEADER)
        lines = run_checks(T.load(options(counts=self.fixed_counts(name="inverse.tsv", edit=inverse))))
        self.assertEqual(levels(lines, "C8"), {"FAIL"})
        self.assertIn("with combined_fdp != N_E/N(1+T/E)", of(lines, "C8")[0][1])

    def test_c8_paired_na(self):
        def edit(line):
            d = cells(line, COUNTS_HEADER)
            if match("prose", "per_file", "velos_r1", "hy_entrap_s1_td", None, "peptide")(line):
                d["paired_fdp"] = "NA"
            return join(d, COUNTS_HEADER)
        lines = run_checks(T.load(options(counts=self.fixed_counts(edit=edit))))
        self.assertEqual(levels(lines, "C8"), {"FAIL"})
        self.assertIn("1 with paired_fdp NA where a value is expected or the reverse: "
                      "prose/per_file/velos_r1/hy_entrap_s1_td/peptide", of(lines, "C8")[0][1])

    def test_t29_c8_tolerance(self):
        """T29: N = 10,000,000, N_E = 49,963 (N_E/N = 0.0049963), te printed 1, combined printed 0.01: recomputed
        0.0099926, |diff| = 7.4e-6 <= h(0.01) + 0.0049963 h(1) + 1e-12 = 5e-6 + 2.498e-6: PASS (v1's 6e-6 would
        FAIL); combined 0.01001 FAILs."""
        c = T.load(options(counts=self.fixed_counts()))
        i = next(i for i, r in enumerate(c.counts) if r.design == "shuffled" and r.level == "peptide")
        r = dataclasses.replace(c.counts[i], accepted=10000000, entrapment=49963, te_ratio=1.0, combined_fdp=0.01,
                                lower_bound_fdp=0.004996)
        self.assertAlmostEqual(fdp.h(0.01) + 0.0049963 * fdp.h(1.0), 7.49815e-6, places=10)
        c.counts[i] = r
        self.assertEqual(levels(run_checks(c), "C8"), {"PASS"})
        c.counts[i] = dataclasses.replace(r, combined_fdp=0.01001)
        self.assertEqual(levels(run_checks(c), "C8"), {"FAIL"})
        c.counts[i] = dataclasses.replace(r, lower_bound_fdp=0.004997)
        self.assertEqual(levels(run_checks(c), "C8"), {"FAIL"})

    def test_c9(self):
        lines = run_checks(T.load(options()))
        self.assertEqual(of(lines, "C9"), [("WARN", "1 of 50 (engine, unit) pairs lack shuffled realisations: "
                                                    "sage velos_r1 (s3 failed)")])
        lines = run_checks(T.load(options(strict=True)))
        self.assertEqual(levels(lines, "C9"), {"FAIL"})
        self.assertEqual(levels(run_checks(T.load(smoke_options())), "C9"), {"PASS"})

    def test_c10(self):
        lines = run_checks(T.load(options()))
        self.assertEqual(of(lines, "C10"), [("PASS", "low_memory counts == standard counts on 3 samples x 2 level(s) "
                                                     "(DS:988)")])

        def edit(line):
            if match("prose", "per_file_low_memory", "pxd058436_DN05", None, None, "psm")(line):
                d = cells(line, COUNTS_HEADER)
                d["accepted"] = "17599"
                return join(d, COUNTS_HEADER)
            return line
        cnt = copy_with(fx("counts_fx.tsv"), self.path("cnt.tsv"), edit=edit)
        lines = run_checks(T.load(options(counts=cnt)))
        self.assertEqual(of(lines, "C10"), [("WARN", "low_memory counts differ from the standard counts in 1 of 6 "
                                                     "sample-levels (DS:988): pxd058436_DN05 psm")])
        self.assertEqual(levels(run_checks(T.load(smoke_options())), "C10"), {"INFO"})


# ================================================================ C11-C13
class TestC11C13(Temp):
    def test_c11_t30_and_pass(self):
        lines = run_checks(T.load(options()))
        c11 = of(lines, "C11")
        self.assertIn(("PASS", "1 batch groups as SPEC 2.1 (1 for Sage)"), c11)
        self.assertIn(("WARN", "threads of per_file, arms and batch: 1 keys at 8, 73 keys at 16: "
                               "prose/per_file/lumos_tmt_r1/hy_td (8)"), c11)  # T30
        # without the 8-thread rerun every timing is at 16 = --expect-threads
        tim = copy_with(fx("timings_fx.tsv"), self.path("tim.tsv"),
                        keep=lambda l: not match("prose", "per_file", "lumos_tmt_r1", None, None, "8")(l))
        lines = run_checks(T.load(options(timings=tim, expect_threads=16)))
        self.assertIn(("PASS", "all 74 per_file, arm and batch timings at 16 threads (--expect-threads)"),
                      of(lines, "C11"))
        lines = run_checks(T.load(options(timings=tim, expect_threads=64)))
        self.assertTrue(any(lv == "WARN" and "expected 64" in m for lv, m in of(lines, "C11")))

    def test_c11_batch_list_and_coverage(self):
        exp = dict(FX_EXPECTED, batch_groups=("astral_250pg", "velos"))
        lines = run_checks(T.load(options()), expected=exp)
        self.assertTrue(any(lv == "FAIL" and "missing velos" in m for lv, m in of(lines, "C11")))
        cov = copy_with(fx("coverage_fx.tsv"), self.path("cov.tsv"),
                        keep=lambda l: not match("sage", "batch")(l))
        tim = copy_with(fx("timings_fx.tsv"), self.path("tim.tsv"), keep=lambda l: not match("sage", "batch")(l))
        lines = run_checks(T.load(options(coverage=cov, timings=tim, strict=True)))
        self.assertTrue(any(lv == "FAIL" and "1 expected but absent from coverage (sage 1): sage/batch/astral_250pg"
                            in m for lv, m in of(lines, "C11")))

    def test_c11_c12_threads_against_cpus(self):
        """Camera-ready C1: every used per_file, arm, batch and scaling timing against the CPUs of its machine file
        (timing_machine_fx.txt: role engine, 16 CPUs); WARN above them, FAIL under --strict; a WARN without a
        machine file."""
        machine = (("fx", fx("timing_machine_fx.txt")),)
        lines = run_checks(T.load(options(machines=machine)))
        self.assertIn(("PASS", "threads <= CPUs: 74 timings at up to 16 threads on fx (16 CPUs)"), of(lines, "C11"))
        c12 = [m for lv, m in of(lines, "C12") if "CPUs" in m]
        self.assertEqual(len(c12), 1)
        self.assertRegex(c12[0], r"^threads <= CPUs: \d+ timings at up to 16 threads on fx \(16 CPUs\)$")
        self.assertNotIn("WARN", levels(lines, "C12"))
        # 8 CPUs: 73 timings at 16 threads are above them (the 8-thread rerun is not); every scaling point at 16 too
        eight = copy_with(fx("timing_machine_fx.txt"), self.path("machine8.txt"),
                          edit=lambda l: "CPU(s):                             8" if l.startswith("CPU(s):") else l)
        machine = (("fx", eight),)
        lines = run_checks(T.load(options(machines=machine)))
        self.assertIn(("WARN", "threads > CPUs: 73 timings at 16 threads on fx (8 CPUs)"), of(lines, "C11"))
        self.assertTrue(any(lv == "WARN" and re.match(r"^threads > CPUs: \d+ timings at 16 threads on fx \(8 CPUs\)$",
                                                      m) for lv, m in of(lines, "C12")), of(lines, "C12"))
        lines = run_checks(T.load(options(machines=machine, strict=True)))
        self.assertIn(("FAIL", "threads > CPUs: 73 timings at 16 threads on fx (8 CPUs)"), of(lines, "C11"))
        # no machine file: one WARN in C11 (also under --strict), nothing about CPUs in C12
        lines = run_checks(T.load(options(strict=True)))
        self.assertIn(("WARN", "cannot compare threads with CPUs: no --machine file"), of(lines, "C11"))
        self.assertFalse(any("CPUs" in m for _, m in of(lines, "C12")))
        # a separate scaling folder S needs a machine file with role scaling
        w = self.path("W")
        os.makedirs(w)
        not_scaling = lambda line: line.split("\t")[1] != "scaling"  # noqa: E731
        copy_with(fx("coverage_fx.tsv"), os.path.join(w, "coverage.tsv"), keep=not_scaling)
        copy_with(fx("timings_fx.tsv"), os.path.join(w, "timings.tsv"), keep=not_scaling)
        shutil.copy(fx("counts_fx.tsv"), os.path.join(w, "counts.tsv"))
        lines = run_checks(self.load_work(w, scaling_coverage=fx("coverage_overlimit_fx.tsv"),
                                          scaling_timings=fx("timings_overlimit_fx.tsv"),
                                          machines=(("fx", fx("timing_machine_fx.txt")),)))
        self.assertIn(("WARN", "cannot compare threads with CPUs: no --machine file with role scaling"),
                      of(lines, "C12"))
        scaling = copy_with(fx("timing_machine_fx.txt"), self.path("machine_s.txt"),
                            edit=lambda l: "role: scaling" if l.startswith("role:") else l)
        lines = run_checks(self.load_work(w, scaling_coverage=fx("coverage_overlimit_fx.tsv"),
                                          scaling_timings=fx("timings_overlimit_fx.tsv"),
                                          machines=(("fx", fx("timing_machine_fx.txt")), ("fs", scaling))))
        self.assertTrue(any(lv == "PASS" and m.startswith("threads <= CPUs: ") and m.endswith(" on fs (16 CPUs)")
                            for lv, m in of(lines, "C12")), of(lines, "C12"))

    def test_c12_paths(self):
        lines = run_checks(T.load(options()))
        self.assertEqual(levels(lines, "C12"), {"PASS"})
        # repetition 0 below the top point -> FAIL
        tim = copy_with(fx("timings_fx.tsv"), self.path("tim.tsv"),
                        add=["prose\tscaling\thfx_r1\thye_td.fasta\tall\t8\t0\t100.00\t800.00\t3000000\t0"])
        lines = run_checks(T.load(options(timings=tim)))
        self.assertTrue(any(lv == "FAIL" and "prose/hfx_r1/t8: repetition 0 below the top point t16" in m
                            for lv, m in of(lines, "C12")))
        # one engine without the point 1 -> the grids differ, WARN(s)
        cov = copy_with(fx("coverage_fx.tsv"), self.path("cov.tsv"),
                        keep=lambda l: not match("sage", "scaling", "hfx_r1", "hye_td_t1")(l))
        tim = copy_with(fx("timings_fx.tsv"), self.path("tim2.tsv"),
                        keep=lambda l: not match("sage", "scaling", "hfx_r1", None, None, "1")(l))
        lines = run_checks(T.load(options(coverage=cov, timings=tim, strict=True)))
        self.assertIn(("FAIL", "hfx_r1: the grids differ between engines: prose 16,8,4,2,1; sage 16,8,4,2; "
                               "msfragger 16,8,4,2,1"), of(lines, "C12"))
        # scaling rows of a run not flagged scaling == 1 -> WARN (B:986)
        runs = copy_with(fx("runs_fx.tsv"), self.path("runs.tsv"),
                         edit=lambda l: l.replace("\tby\t-\t1\t", "\tby\t-\t0\t") if l.startswith("hfx_r1") else l)
        lines = run_checks(T.load(options(runs=runs)))
        self.assertTrue(any(lv == "WARN" and "not flagged scaling == 1" in m for lv, m in of(lines, "C12")))

    def test_c13(self):
        lines = run_checks(T.load(options(versions=fx("checks_versions_fx.txt"))))
        self.assertEqual(levels(lines, "C13"), {"PASS"})
        lines = run_checks(T.load(options()))
        self.assertEqual(of(lines, "C13"), [("WARN", "no W (= S)/versions.txt (B:346-357)")])
        ver = copy_with(fx("checks_versions_fx.txt"), self.path("versions.txt"),
                        edit=lambda l: l.replace("sage 0.14.6", "sage 0.14.7"))
        lines = run_checks(T.load(options(versions=ver)))
        self.assertEqual(of(lines, "C13"), [("FAIL", "W (= S)/versions.txt: Sage: 'sage 0.14.6' not found")])
        # a separate S/versions.txt is checked on its own
        s = self.path("S")
        os.makedirs(s)
        shutil.copy(ver, os.path.join(s, "versions.txt"))
        lines = run_checks(T.load(options(versions=fx("checks_versions_fx.txt"),
                                          scaling_versions=os.path.join(s, "versions.txt"))))
        self.assertEqual([lv for lv, _ in of(lines, "C13")], ["PASS", "FAIL"])


# ================================================================ C14-C17
class TestC14C17(Temp):
    def test_c14(self):
        lines = run_checks(T.load(options(mzml_counts=fx("checks_mzml_counts_fx.tsv"))))
        self.assertEqual(levels(lines, "C14"), {"PASS"})
        lines = run_checks(T.load(options(mzml_counts=fx("checks_mzml_counts_fx.tsv"))),
                           expected=dict(FX_EXPECTED, ms2_tuned=1509392))
        self.assertEqual(levels(lines, "C14"), {"FAIL"})
        mz = copy_with(fx("checks_mzml_counts_fx.tsv"), self.path("mz.tsv"), keep=lambda l: not l.startswith("ups1"))
        lines = run_checks(T.load(options(mzml_counts=mz)))
        self.assertIn(("FAIL", "1 run id(s) missing in mzml_counts.tsv: ups1_r1"), of(lines, "C14"))
        self.assertEqual(levels(run_checks(T.load(options())), "C14"), {"WARN"})
        self.assertEqual(levels(run_checks(T.load(smoke_options())), "C14"), {"INFO"})

    def test_c15(self):
        lines = run_checks(T.load(options()))
        self.assertEqual(levels(lines, "C15"), {"PASS"})
        lines = run_checks(T.load(options()), expected={})  # the paper's DS:860-878 and DS:998 values
        c15 = of(lines, "C15")
        self.assertEqual([lv for lv, _ in c15], ["FAIL"])
        self.assertIn("role=decision differs from DS:998", c15[0][1])
        self.assertIn("velos 1 (DS 3)", c15[0][1])
        self.assertEqual(levels(run_checks(T.load(smoke_options())), "C15"), {"INFO"})

    def test_c16(self):
        lines = run_checks(T.load(options()))
        self.assertIn(("PASS", "R3 within R for 4 (pair, level); no decision unit in R, R3, F, T, T3; B3 1 batch "
                               "group(s)"), of(lines, "C16"))

        def prep(c):
            build_o2(c, numbers=False)
            edit_table(c, "O02_pairs_runs", lambda r: r["unit"] == "astral250pg_A2", used="yes")
        lines = run_checks(T.load(options()), prepare=prep)
        bad = [m for lv, m in of(lines, "C16") if lv == "FAIL"]
        self.assertEqual(len(bad), 1)
        self.assertIn("uses a decision unit", bad[0])

    def test_c17(self):
        self.assertEqual(levels(run_checks(T.load(options())), "C17"), {"PASS"})
        cov = copy_with(fx("coverage_fx.tsv"), self.path("cov.tsv"),
                        add=["prose\tbatch\tastral_250pg\thye_other_td\tok\tno"])
        lines = run_checks(T.load(options(coverage=cov)))
        self.assertEqual(of(lines, "C17"), [("FAIL", "1 batch/scaling coverage row(s) whose database is not the td: "
                                                     "prose/batch/astral_250pg/hye_other_td")])


# ================================================================ C18-C22
class TestC18C22(Temp):
    def test_c18_listing_and_mtimes(self):
        w = self.work(overtuning=True)
        lines = run_checks(self.load_work(w, listing=fx("checks_listing_fx.ls")))
        self.assertEqual([lv for lv, _ in of(lines, "C18")], ["INFO", "INFO"])
        self.assertTrue(all("older than counts.tsv (--listing" in m for _, m in of(lines, "C18")))
        # without --listing the mtimes are read: overtuning written after counts.tsv here
        lines = run_checks(self.load_work(w))
        self.assertTrue(all(m.endswith("not older than counts.tsv (mtimes)") for _, m in of(lines, "C18")))
        lines = run_checks(T.load(options()))
        self.assertEqual(of(lines, "C18"), [("INFO", "SKIP: no work folder")])

    def test_c19(self):
        def good(c):
            c.number("ids.heldout.psm.msfragger.lead", 12.5, source_side="heldout")
            c.number("ids.tuning.psm.msfragger.lead", 15.0, source_side="tuning")  # main_text_allowed no
            c.number("overtuning.psm.lt_msfragger", 15.0, source_side="tuning")  # exempt (DS:903)
        self.assertEqual(of(run_checks(T.load(options()), prepare=good), "C19"),
                         [("PASS", "3 keys; 2 identification-ratio keys, 1 allowed in the main text, all from held-out "
                                   "data; no own-set key")])

        def bad(c):
            c.number("ids.tuning.psm.sage.lead", 15.0, source_side="tuning", main_text_allowed=True)
            c.number("fdp.own_mean.prose", 0.01)
        lines = run_checks(T.load(options()), prepare=bad)
        self.assertEqual(of(lines, "C19"), [("FAIL", "1 identification-ratio key(s) allowed in the main text without "
                                                     "source_side heldout: ids.tuning.psm.sage.lead; 1 own-set key(s): "
                                                     "fdp.own_mean.prose")])

        def matched(c):  # the O13 leads are identification ratios too (tables.ID_RATIO_FAMILIES)
            c.number("fdp.matched.heldout.psm.sage.lead_matched", 3.0, source_side="heldout")
            c.number("fdp.matched.tuning.psm.sage.lead_matched", 4.0, source_side="tuning", main_text_allowed="yes")
            c.number("fdp.psm.sage.max_run_mean", 0.9, source_side="mixed")  # not an identification ratio
        lines = run_checks(T.load(options()), prepare=matched)
        self.assertEqual(of(lines, "C19"), [("FAIL", "1 identification-ratio key(s) allowed in the main text without "
                                                     "source_side heldout: fdp.matched.tuning.psm.sage.lead_matched; "
                                                     "0 own-set key(s)")])

    def test_c20(self):
        def prep(c, wrong=False):
            rows = [{"group": "velos", "grade": "-", "value": 1},
                    {"group": "iprg2015", "grade": design.grade("iprg2015"), "value": 1},
                    {"unit": "pxd058436_DN05", "grade": design.grade("pxd058436_classI"), "value": 1},
                    {"side": "heldout", "grade": "B", "value": 1}, {"scope": "all", "grade": "-", "value": 1}]
            if wrong:
                rows[0]["grade"] = "A"
                rows[3]["grade"] = "-"
            c.write_table("O99_fixture_grades", ["group", "unit", "side", "scope", "grade", "value"],
                          [{k: r.get(k, "") for k in ("group", "unit", "side", "scope", "grade", "value")}
                           for r in rows])
        self.assertIn(design.grade("iprg2015"), ("A", "B", "C"))
        lines = run_checks(T.load(options()), prepare=prep)
        self.assertEqual(of(lines, "C20"), [("PASS", "4 rows of 1 tables carry their dataset's grade (1 rows without "
                                                     "a group or side, e.g. summary rows)")])
        lines = run_checks(T.load(options()), prepare=lambda c: prep(c, wrong=True))
        self.assertEqual(of(lines, "C20"), [("FAIL", "2 row(s) with a wrong grade (DS:114): O99_fixture_grades velos "
                                                     "(A, expected -), O99_fixture_grades held-out row without a grade "
                                                     "(-)")])
        self.assertEqual(levels(run_checks(T.load(options())), "C20"), {"INFO"})

    def test_c21(self):
        lines = run_checks(T.load(options(references=fx("checks_reference_fx.tsv"))))
        self.assertEqual(of(lines, "C21"), [("PASS", "10 reference rows of the mapped groups (1 ignored by the map, 1 "
                                                     "flagged local FDR, OPEN Q46); all 3 immuno samples have their "
                                                     "expected tools")])
        ref = copy_with(fx("checks_reference_fx.tsv"), self.path("ref.tsv"), keep=lambda l: "PEAKS" not in l
                        or "DN13" not in l)
        lines = run_checks(T.load(options(references=ref)))
        self.assertEqual(levels(lines, "C21"), {"FAIL"})
        self.assertIn("1 expected reference(s) missing: pxd058436_DN13 peaks", of(lines, "C21")[0][1])
        with open(fx("checks_reference_fx.tsv"), encoding="utf-8") as f:
            again = [line for line in f.read().splitlines() if "MHCquant 1.5.1" in line]
        ref = copy_with(fx("checks_reference_fx.tsv"), self.path("ref2.tsv"),
                        edit=lambda l: l.replace("FragPipe v21.1", "Unknown tool") if "DN05" in l else l, add=again)
        lines = run_checks(T.load(options(references=ref)))
        msg = of(lines, "C21")[0][1]
        self.assertIn("engine string not in REFERENCE_MAP", msg)
        self.assertIn("second row for pxd019643_DN05 mhcquant", msg)
        self.assertIn("pxd058436_DN05 fragpipe", msg)
        self.assertEqual(of(run_checks(T.load(options())), "C21"),
                         [("FAIL", "no reference file (None): 3 immuno samples without their expected tools: "
                                   "pxd058436_DN05, pxd058436_DN13, pxd019643_DN05")])
        self.assertEqual(levels(run_checks(T.load(smoke_options())), "C21"), {"INFO"})

    def test_c22(self):
        lines = run_checks(T.load(options()))
        self.assertIn(("PASS", "POOLED_ARRANGEMENT per_file in all 1 immuno parameter files "
                               "(Search:rescore_reuse:mode)"), of(lines, "C22"))

        def o9b(choice):
            def prep(c):
                c.write_table("O09b_rule11b", ["pool", "chosen", "note"], [{"pool": "DN13", "chosen": choice,
                                                                            "note": ""}])
            return prep
        self.assertIn(("PASS", "O9b chose per_file = POOLED_ARRANGEMENT"),
                      of(run_checks(T.load(options()), prepare=o9b("per_file")), "C22"))
        self.assertIn(("FAIL", "O9b chose joint, POOLED_ARRANGEMENT is per_file (DS:629)"),
                      of(run_checks(T.load(options()), prepare=o9b("joint")), "C22"))
        self.assertEqual(levels(run_checks(T.load(smoke_options())), "C22"), {"INFO"})


# ================================================================ C23-C25 and run()
class TestC23C25(Temp):
    def logs_ctx(self, stale=None, skip=None, links=()):
        """W with W/out holding <stage>.r<rep>.log for every repetition of every complete timing (B:911-922);
        stale: a key whose folder also gets its untimed <stage>.log (B:920); skip: a key without its r3 logs; links:
        (key, name) of dangling symbolic links to put in a key's folder."""
        base = T.load(options())
        self.n_work = getattr(self, "n_work", 0) + 1
        w = self.work(name=f"W{self.n_work}")
        for key, t in base.timings.items():
            if t.state != "complete":
                continue
            e, b, run, db, thr = key
            folder = os.path.join(w, "out", e, b, run, db + (f"_t{thr}" if thr else ""))
            os.makedirs(folder, exist_ok=True)
            for r, rep in t.attempt.reps.items():
                if key == skip and r == 3:
                    continue
                for s in rep.stages:
                    open(os.path.join(folder, f"{s}.r{r}.log"), "w").close()
            if key == stale:
                open(os.path.join(folder, next(iter(t.expected)) + ".log"), "w").close()
            for k, name in links:
                if k == key:
                    os.symlink(os.path.join(w, "gone", name), os.path.join(folder, name))
        return self.load_work(w)

    def test_c24_dangling_links(self):
        """A dangling symbolic link named like a file the package reads (here a <stage>.log next to complete r-logs,
        which would make the search stale_timing if it resolved, and the files of the qgrid check of C2 and O13)
        counts as absent, and a WARN C24 names it; not strict. A dangling link of another name (MSFragger's mzML
        links when W moved, B:783-788) is not named."""
        prose = ("prose", "per_file", "velos_r1", "hy_td", None)
        msf = ("msfragger", "per_file", "hfx_r1", "hye_td", None)
        try:
            c = self.logs_ctx(links=((prose, "all.log"), (prose, "count_qgrid.sha256"), (msf, "hfx_r1.mzML"),
                                     (msf, "hfx_r1.count.idXML")))
        except (OSError, NotImplementedError):
            self.skipTest("no symbolic links here")
        self.assertEqual(c.timings[prose].state, "complete")  # the link counts as absent
        c.report.strict = True
        lines = run_checks(c)
        self.assertIn("PASS", levels(lines, "C24"))
        warn = [m for lv, m in of(lines, "C24") if lv == "WARN"]
        self.assertEqual(len(warn), 1)
        self.assertTrue(warn[0].startswith("3 symbolic link(s) in the search folders read do not resolve (each counts "
                                           "as absent, so it could hide a stale or missing file): "), warn[0])
        for rel in ("prose/per_file/velos_r1/hy_td/all.log", "prose/per_file/velos_r1/hy_td/count_qgrid.sha256",
                    "msfragger/per_file/hfx_r1/hye_td/hfx_r1.count.idXML"):
            self.assertIn(rel, warn[0])
        self.assertNotIn("mzML", warn[0])
        self.assertNotIn("FAIL", levels(lines, "C24"))

    def test_c24_pass_and_t31(self):
        lines = run_checks(self.logs_ctx())
        self.assertEqual(levels(lines, "C24"), {"PASS"})
        key = ("prose", "per_file", "velos_r1", "hy_td", None)
        c = self.logs_ctx(stale=key)
        self.assertEqual(c.timings[key].state, "stale_timing")
        lines = run_checks(c)
        self.assertEqual(of(lines, "C24"), [("WARN", "1 timed folder(s) with an untimed <stage>.log (stale_timing, "
                                                     "B:920): prose/per_file/velos_r1/hy_td (all.log); 0 without all "
                                                     "their <stage>.r<rep>.log")])
        self.assertTrue(any("1 stale_timing (C24)" in m for _, m in of(lines, "C5")))
        skip = ("msfragger", "batch", "astral_250pg", "hye_td", None)
        lines = run_checks(self.logs_ctx(skip=skip))
        self.assertTrue(any(lv == "WARN" and "msfragger/batch/astral_250pg/hye_td (rescoring.r3.log, search.r3.log)"
                            in m for lv, m in of(lines, "C24")))
        self.assertEqual(levels(run_checks(T.load(options())), "C24"), {"INFO"})

    def test_c24_separate_scaling_folder(self):
        """A separate S (--scaling-work) without S/out: C24 checks W's folders and skips the scaling ones with one
        INFO, also under --strict (only S's timings, coverage and versions are needed); with S/out the scaling
        folders are checked too, and a stale <stage>.log there gives stale_timing (SPEC 2.5, T31)."""
        base = T.load(options())
        w, s = self.path("Wsep"), self.path("Ssep")
        os.makedirs(w)
        os.makedirs(s)
        for src, name in ((fx("coverage_fx.tsv"), "coverage.tsv"), (fx("timings_fx.tsv"), "timings.tsv")):
            with open(src, encoding="utf-8") as f:
                lines = f.read().splitlines()
            for folder, scaling in ((w, False), (s, True)):
                kept = [lines[0]] + [x for x in lines[1:] if (x.split("\t")[1] == "scaling") == scaling]
                with open(os.path.join(folder, name), "w", encoding="utf-8", newline="\n") as f:
                    f.write("\n".join(kept) + "\n")
        shutil.copy(fx("counts_fx.tsv"), os.path.join(w, "counts.tsv"))

        def timed(scaling):  # the keys C24 looks at: complete timings whose coverage is ok
            out = []
            for key, t in base.timings.items():
                e, b, run, db, thr = key
                c = base.coverage_index.get((e, b, run, f"{db}_t{thr}" if b == "scaling" else db))
                if t.state == "complete" and (b == "scaling") == scaling and c is not None and c.state == "ok":
                    out.append(key)
            return out

        def logs(root, keys):
            for key in keys:
                e, b, run, db, thr = key
                folder = os.path.join(root, "out", e, b, run, db + (f"_t{thr}" if thr else ""))
                os.makedirs(folder, exist_ok=True)
                for r, rep in base.timings[key].attempt.reps.items():
                    for st in rep.stages:
                        open(os.path.join(folder, f"{st}.r{r}.log"), "w").close()
        n_w, n_s = len(timed(False)), len(timed(True))
        self.assertTrue(n_w > 0 and n_s > 0)
        logs(w, timed(False))
        for strict in (False, True):
            c = self.load_work(w, scaling_work=s, strict=strict)
            self.assertTrue(c.logs_available)
            self.assertFalse(c.scaling_logs_available)
            lines = run_checks(c)
            self.assertEqual(of(lines, "C24"), [
                ("PASS", f"{n_w} timed folders hold <stage>.r<rep>.log for every repetition and no <stage>.log"),
                ("INFO", f"SKIP {n_s} timed folder(s) of S/out (scaling): no such out/ tree")])
            self.assertIn(("INFO", "no S/out logs (--scaling-work S): C24 and the stale_timing test (SPEC 2.5) skip "
                                   "the scaling searches; only S's timings.tsv, coverage.tsv and versions.txt are read"),
                          of(c.report.lines, "LOGS"))  # a loader line (T.load), before the checks
        logs(s, timed(True))
        c = self.load_work(w, scaling_work=s)
        self.assertTrue(c.scaling_logs_available)
        self.assertEqual(of(run_checks(c), "C24"), [
            ("PASS", f"{n_w + n_s} timed folders hold <stage>.r<rep>.log for every repetition and no <stage>.log")])
        key = next(k for k, t in c.timings.items() if k[1] == "scaling" and k[0] == "prose" and t.state == "complete")
        folder = c.search_dir(*key)
        open(os.path.join(folder, "all.log"), "w").close()
        c = self.load_work(w, scaling_work=s)
        self.assertEqual(c.timings[key].state, "stale_timing")
        warn = [m for lv, m in of(run_checks(c), "C24") if lv == "WARN"]
        self.assertEqual(len(warn), 1)  # named by its folder under out/ (B:196), not by its key
        self.assertIn(f"prose/scaling/{key[2]}/{key[3]}_t{key[4]} (all.log)", warn[0])

    def test_c23(self):
        msf_values = {"fragment_tol": 10.0, "fragment_tol_unit": "ppm", "use_topN_peaks": 150, "minimum_ratio": 0.01,
                      "intensity_transform": 0, "remove_precursor_peak": 1, "max_fragment_charge": 2}

        def prep(c, drop=None, blank=None, strip=False, value=T.Missing("missing"), na_row=None, rename=None):
            """blank: (engine, run, database, column) whose value is `value`; strip: tables without the value
            columns; na_row: (run, database) of a ProSE search with one more row, without a value (an input of its
            inputs file that the log did not search); rename: (run, database, input) of a ProSE search whose last row
            names another input than the run table's file"""
            msf, prose = [], []
            for cv in c.coverage:
                if cv.scope != "unit" or not cv.counted or (cv.engine, cv.run, cv.database) == drop:
                    continue
                row = {"engine": cv.engine, "benchmark": cv.benchmark, "unit": cv.run, "database": cv.database,
                       "source": "parsed"}
                if cv.engine == "msfragger":
                    msf.append(dict(row, **msf_values))
                elif cv.engine == "prose":
                    prose += [dict(row, input=x, prose_fragment_tol=8.1, prose_fragment_tol_unit="ppm")
                              for x in cv.unit.runs]
                    if na_row == (cv.run, cv.database) and cv.benchmark == "per_file":
                        none = T.Missing("not_searched")
                        prose.append(dict(row, input="other_run", source=none, prose_fragment_tol=none,
                                          prose_fragment_tol_unit=none))
                    if rename and rename[:2] == (cv.run, cv.database) and cv.benchmark == "per_file":
                        prose[-1]["input"] = rename[2]
                if blank and (cv.engine, cv.run, cv.database) == blank[:3]:
                    (msf if cv.engine == "msfragger" else prose)[-1][blank[3]] = value
            cols = ["engine", "benchmark", "unit", "database", "source"]
            c.write_table("O19_settings_msfragger", cols + ([] if strip else list(msf_values)),
                          [{k: r[k] for k in cols} for r in msf] if strip else msf)
            c.write_table("O19_settings_prose", cols + ["input", "prose_fragment_tol", "prose_fragment_tol_unit"],
                          prose)
        lines = run_checks(self.logs_ctx(), prepare=prep)
        self.assertEqual(levels(lines, "C23"), {"PASS"})
        lines = run_checks(self.logs_ctx(), prepare=lambda c: prep(c, drop=("msfragger", "hfx_r1", "hye_td")))
        self.assertIn("WARN", levels(lines, "C23"))
        self.assertTrue(any("msfragger/per_file/hfx_r1/hye_td" in m for _, m in of(lines, "C23")))
        # a row whose fragment tolerance is NA is no settings row (it passed silently before: case e of the C23
        # verification, fragger.params and the New line both missing); WARN(s), FAIL under --strict
        blank = ("msfragger", "hfx_r1", "hye_entrap_s2_td", "fragment_tol")
        lines = run_checks(self.logs_ctx(), prepare=lambda c: prep(c, blank=blank))
        warn = [m for lv, m in of(lines, "C23") if lv == "WARN"]
        self.assertEqual(len(warn), 1)
        self.assertIn("1 of", warn[0])
        self.assertIn("msfragger/per_file/hfx_r1/hye_entrap_s2_td (NA: fragment_tol)", warn[0])
        c = self.logs_ctx()
        c.report.strict = True
        self.assertIn("FAIL", levels(run_checks(c, prepare=lambda c: prep(c, blank=blank)), "C23"))
        blank = ("prose", "hfx_r1", "hye_td", "prose_fragment_tol")
        lines = run_checks(self.logs_ctx(), prepare=lambda c: prep(c, blank=blank))
        self.assertTrue(any(lv == "WARN" and "prose/per_file/hfx_r1/hye_td (NA: prose_fragment_tol)" in m
                            for lv, m in of(lines, "C23")))
        # an empty value counts as NA, by the same rule as INFO O19 (calib.lacks_value)
        blank = ("msfragger", "hfx_r1", "hye_entrap_s2_td", "use_topN_peaks")
        lines = run_checks(self.logs_ctx(), prepare=lambda c: prep(c, blank=blank, value=""))
        self.assertTrue(any(lv == "WARN" and "msfragger/per_file/hfx_r1/hye_entrap_s2_td (NA: use_topN_peaks)" in m
                            for lv, m in of(lines, "C23")))
        # a ProSE search with a value row for every file of the run table and one more row without a value: no
        # settings for C23 (INFO O19 counts it the same way)
        lines = run_checks(self.logs_ctx(), prepare=lambda c: prep(c, na_row=("hfx_r1", "hye_td")))
        warn = [m for lv, m in of(lines, "C23") if lv == "WARN"]
        self.assertEqual(len(warn), 1)
        self.assertIn("prose/per_file/hfx_r1/hye_td (NA: source)", warn[0])
        # as many value rows as the run table has files, but under another name: the run table's file has no row
        lines = run_checks(self.logs_ctx(), prepare=lambda c: prep(c, rename=("hfx_r1", "hye_td", "other_run")))
        warn = [m for lv, m in of(lines, "C23") if lv == "WARN"]
        self.assertEqual(len(warn), 1)
        self.assertIn("prose/per_file/hfx_r1/hye_td (no row: hfx_r1)", warn[0])
        lines = run_checks(self.logs_ctx(), prepare=lambda c: prep(c, strip=True))  # a SPEC column is lacking
        self.assertIn(("FAIL", "msfragger settings: table O19_settings_msfragger lacks the column(s) fragment_tol, "
                               "fragment_tol_unit, use_topN_peaks, minimum_ratio, intensity_transform, "
                               "remove_precursor_peak, max_fragment_charge (SPEC 3)"), of(lines, "C23"))
        lines = run_checks(self.logs_ctx())
        self.assertTrue(all(lv == "INFO" and "absent" in m for lv, m in of(lines, "C23")))
        self.assertEqual(levels(run_checks(T.load(options())), "C23"), {"INFO"})

    def test_c25_pass_and_t27(self):
        self.assertEqual(levels(run_checks(T.load(options())), "C25"), {"PASS"})
        c = T.load(options(counts=fx("counts_wnode_fx.tsv"), coverage=fx("coverage_wnode_fx.tsv"),
                           timings=fx("timings_wnode_fx.tsv"), strict=True))
        lines = run_checks(c, prepare=build_o2)  # T27: decision runs only, no exception
        self.assertEqual(levels(lines, "C6a"), {"INFO"})  # nothing to compare: every dataset dropped in both
        self.assertEqual(levels(lines, "C6d"), {"INFO"})  # every lead NA in both
        self.assertEqual(levels(lines, "C6c"), {"INFO"})  # no W file and OT.rule cannot run
        self.assertEqual(of(lines, "C25"),
                         [("FAIL", "psm: O4-O7 skipped: no dataset for MSFragger tuning, MSFragger held-out, Sage "
                                   "tuning, Sage held-out (OT:44-45, 53-54)"),
                          ("FAIL", "peptide: O4-O7 skipped: no dataset for MSFragger tuning, MSFragger held-out, Sage "
                                   "tuning, Sage held-out (OT:44-45, 53-54)")])
        self.assertFalse(any("check raised" in m for _, _, m in lines))

    def test_run_survives_a_failing_check(self):
        def boom(ctx, exp, state):
            raise RuntimeError("made up")
        saved = checks.CHECKS
        checks.CHECKS = (("C1", boom),) + saved[1:]
        try:
            c = T.load(options())
            n0 = len(c.report.lines)
            errors = checks.run(c, FX_EXPECTED)
        finally:
            checks.CHECKS = saved
        lines = c.report.lines[n0:]
        self.assertEqual(of(lines, "C1"), [("FAIL", "check raised RuntimeError: made up (traceback in "
                                                    "errors_checks.txt)")])
        self.assertEqual(len(errors), 1)
        self.assertIn("RuntimeError", errors[0])
        self.assertEqual(levels(lines, "C2"), {"PASS"})  # the others go on

    def test_errors_file_written(self):
        out = self.path("out")
        c = T.load(options(out=out))
        checks.run(c, FX_EXPECTED)
        with open(os.path.join(out, "errors_checks.txt"), encoding="utf-8") as f:
            self.assertEqual(f.read(), "")

    def test_every_check_writes_a_line(self):
        for o in (options(), smoke_options(), options(counts=fx("counts_wnode_fx.tsv"),
                                                      coverage=fx("coverage_wnode_fx.tsv"),
                                                      timings=fx("timings_wnode_fx.tsv"))):
            lines = run_checks(T.load(o))
            ids = {c.rstrip("abcd") for _, c, _ in lines}
            self.assertEqual(ids, {f"C{i}" for i in range(1, 26)})
            self.assertFalse(any("check raised" in m for _, _, m in lines))


if __name__ == "__main__":
    unittest.main()
