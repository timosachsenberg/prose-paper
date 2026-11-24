"""Tests of the loader layer (SPEC 6): T1-T3 (helpers), T12-T16, T19 (attempt/state level), T20, T21, T28, T30, T33,
plus the units, comparison sets, Missing reasons and output writers on the base fixtures."""
import hashlib
import math
import os
import shutil
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True

from summaries import design, tables as T  # noqa: E402

FX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")
L = 86400.0  # the time limit of timings_overlimit_fx.tsv


def fx(name):
    return os.path.join(FX, name)


def options(**kw):
    """Options of the base fixture W (runs_fx + counts/coverage/timings_fx), nothing written."""
    o = dict(runs=fx("runs_fx.tsv"), counts=fx("counts_fx.tsv"), coverage=fx("coverage_fx.tsv"),
             timings=fx("timings_fx.tsv"), versions=None, params_dir=fx("params_fx"), references=None,
             mzml_counts=None)
    o.update(kw)
    return T.Options(**o)


_CTX = None


def base_ctx():
    global _CTX
    if _CTX is None:
        _CTX = T.load(options())
    return _CTX


def copy_with(src, dst, edit=None, keep=None):
    """A copy of a fixture TSV: keep(line) filters data lines, edit(line_no, line) -> line rewrites them."""
    with open(src, encoding="utf-8", newline="") as f:
        lines = f.read().splitlines(True)
    out = [lines[0]]
    for i, line in enumerate(lines[1:], start=2):
        if keep and not keep(line):
            continue
        out.append(edit(i, line) if edit else line)
    with open(dst, "w", encoding="utf-8", newline="") as f:
        f.write("".join(out))
    return dst


def set_field(line, col, value, header):
    nl = "\r\n" if line.endswith("\r\n") else "\n"
    cells = line.rstrip("\r\n").split("\t")
    cells[header.index(col)] = value
    return "\t".join(cells) + nl


class TempDir(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="summaries_test_")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def path(self, name):
        return os.path.join(self.tmp, name)


# ---------------------------------------------------------------- T1-T3 and the stats helpers (SPEC 2.7)
class TestHelpers(unittest.TestCase):
    def test_t1_gmean(self):
        self.assertAlmostEqual(T.gmean([1.0, 1.21]), 1.1, places=12)

    def test_t2_one_run_dataset(self):
        self.assertAlmostEqual(T.gmean([1.05]), 1.05, places=12)

    def test_t3_equal_weight_run_weighted_sums(self):
        ga = T.gmean([1210 / 1000, 2000 / 2000])
        gb = T.gmean([900 / 1000])
        self.assertAlmostEqual(ga, 1.1, places=12)
        self.assertAlmostEqual(gb, 0.9, places=12)
        self.assertAlmostEqual(T.gmean([ga, gb]), math.sqrt(0.99), places=12)  # equal weight E
        self.assertEqual(f"{T.gmean([ga, gb]):.6f}", "0.994987")
        w = T.gmean([1.21, 1.0, 0.9])  # run-weighted W
        self.assertAlmostEqual(w, 1.089 ** (1 / 3), places=12)
        self.assertEqual(f"{w:.6f}", "1.028828")
        self.assertAlmostEqual(T.sum_ratio([1210, 2000, 900], [1000, 2000, 1000]), 1.0275, places=12)

    def test_median_and_mean_sd(self):
        self.assertEqual(T.median([100, 100, 120]), 100)  # T13 at helper level
        m, sd = T.mean_sd([0.010, 0.012, 0.014])  # T10 numbers
        self.assertAlmostEqual(m, 0.012, places=12)
        self.assertAlmostEqual(sd, 0.002, places=12)
        m, sd = T.mean_sd([0.010, 0.012])
        self.assertAlmostEqual(m, 0.011, places=12)
        self.assertAlmostEqual(sd, 0.0014142, places=7)
        m, sd = T.mean_sd([0.01])
        self.assertEqual(m, 0.01)
        self.assertIsInstance(sd, T.Missing)

    def test_empty_and_missing(self):
        for f in (T.gmean, T.median, T.fmean):
            self.assertEqual(f([]), T.Missing("empty"))
        self.assertEqual(T.mean_sd([]), (T.Missing("empty"), T.Missing("empty")))
        self.assertEqual(T.sum_ratio([], []), T.Missing("empty"))
        self.assertEqual(T.gmean([1.0, T.Missing("failed")]), T.Missing("failed"))
        self.assertEqual(T.ratio(5, 0), T.Missing("zero"))
        self.assertEqual(T.sum_ratio([1], [0]), T.Missing("zero"))
        self.assertFalse(T.Missing("x"))
        self.assertTrue(T.is_missing(float("nan")) and T.is_missing(None) and T.is_missing(T.Missing("x")))
        self.assertAlmostEqual(T.lead(1.1), 10.0, places=9)

    def test_gib(self):
        self.assertEqual(f"{T.gib(2000000):.6f}", "1.907349")  # T14 in GiB
        self.assertEqual(T.gib(2 ** 20), 1.0)

    def test_fmt(self):
        self.assertEqual(T.fmt(T.Missing("zero")), "NA")
        self.assertEqual(T.fmt(None), "NA")
        self.assertEqual(T.fmt(float("nan")), "NA")
        self.assertEqual(T.fmt(True), "yes")
        self.assertEqual(T.fmt(12), "12")
        self.assertEqual(T.fmt(1.1), "1.100000")
        self.assertEqual(T.fmt(1.907349, T.FMT_GIB), "1.907")


# ---------------------------------------------------------------- T20 key normalisation
class TestKeys(unittest.TestCase):
    def test_t20(self):
        self.assertEqual(T.normalise_db("hye_td.fasta"), "hye_td")
        self.assertEqual(T.split_scaling_db("hye_td_t16"), ("hye_td", 16))
        self.assertIsNone(T.split_scaling_db("hye_td"))
        self.assertEqual(T.split_scaling_db("pxd042233_human_td_t1"), ("pxd042233_human_td", 1))


# ---------------------------------------------------------------- units, groups, design (SPEC 2.1)
class TestUnits(unittest.TestCase):
    def setUp(self):
        self.ctx = base_ctx()

    def test_units(self):
        c = self.ctx
        self.assertEqual(len(c.runs), 25)
        self.assertEqual(len(c.units), 23)
        dn05 = c.unit("pxd058436_DN05")
        self.assertTrue(dn05.pooled)
        self.assertEqual(dn05.runs, ("DN05_r1", "DN05_r2"))
        self.assertEqual(dn05.count_file, "pooled.count.idXML")
        single = c.unit("pxd019643_DN05")  # a sample with one replicate: <run id>.count.idXML (B:1292)
        self.assertFalse(single.pooled)
        self.assertEqual(single.count_file, "p19_DN05_r1.count.idXML")
        self.assertTrue(c.unit("pxd058436_DN13").is_decision)
        self.assertEqual(c.unit_of_run["DN13_r2"].name, "pxd058436_DN13")
        self.assertEqual(c.unit("pxd011695_ETciD_r1").expected, ("prose", "msfragger"))
        self.assertEqual(c.unit("velos_r1").expected, ("prose", "sage", "msfragger"))

    def test_database_design(self):
        v = self.ctx.unit("velos_r1")
        self.assertEqual(v.td, "hy_td")
        self.assertEqual(v.design_of("hy_velos_natural_td"), ("natural", None))
        self.assertEqual(v.design_of("hy_entrap_s2_td"), ("shuffled", 2))
        self.assertIsNone(v.design_of("hye_td"))
        s1 = self.ctx.unit("astral_s1_r1")  # 'hye_s1_natural_td' contains s1 but is natural
        self.assertEqual(s1.design_of("hye_s1_natural_td"), ("natural", None))
        h = self.ctx.unit("hfx_r1")
        self.assertEqual(h.design_of("hye_arath_td"), ("arath", None))
        self.assertEqual(h.stems_of("shuffled"), ["hye_entrap_s1_td", "hye_entrap_s2_td", "hye_entrap_s3_td"])

    def test_groups_batch_scaling(self):
        c = self.ctx
        self.assertEqual(list(c.batch_groups), ["astral_250pg"])
        b = c.batch_groups["astral_250pg"]
        self.assertEqual(b.n_files, 3)  # decision runs included (OPEN Q24)
        self.assertEqual(b.n_decision, 1)
        self.assertEqual(c.scaling_runs, ("hfx_r1",))
        g = c.groups["pxd058436_classI"]
        self.assertEqual((g.kind, g.cls, g.grade, g.n_runs, g.n_decision), ("immuno", "timsTOF", "B", 4, 2))
        self.assertEqual(c.groups["velos"].grade, "-")
        self.assertEqual(c.groups["astral_250pg"].side, "heldout")
        self.assertEqual(c.pooled_arrangement, "per_file")
        self.assertEqual(c.other_arrangement_tag, "mode_joint")


# ---------------------------------------------------------------- counts, coverage, Missing, sets (SPEC 2.3-2.7)
class TestSets(unittest.TestCase):
    def setUp(self):
        self.ctx = base_ctx()

    def test_counts_and_missing(self):
        c = self.ctx
        self.assertEqual(c.accepted("prose", "velos_r1", "psm"), 11000)
        self.assertEqual(c.accepted("sage", "pxd011695_HCD_r1", "psm"), 0)  # zero is a value in O1
        self.assertEqual(c.accepted("sage", "pxd011695_ETciD_r1", "psm"), T.Missing("not_run_by_design"))
        self.assertEqual(c.accepted("sage", "pxd058436_DN05", "psm"), T.Missing("failed_memory"))
        self.assertEqual(c.accepted("sage", "velos_r1", "psm", db="hy_entrap_s3_td"), T.Missing("failed"))
        self.assertEqual(c.fdp("prose", "velos_r1", "hy_entrap_s1_td", "psm"), 0.01)  # T10: 5 * (1 + 1) / 1000
        self.assertEqual(c.fdp("sage", "pxd011695_HCD_r1", "pxd011695_mouse_entrap_s1_td", "psm"),
                         T.Missing("none_accepted"))
        row = c.count_row("prose", "velos_r1", "psm")
        self.assertIsNone(row.paired_fdp)
        self.assertIsInstance(row.lower_bound_fdp, float)
        self.assertEqual(c.accepted("prose", "pxd058436_DN05", "psm", benchmark="per_file_low_memory"),
                         c.accepted("prose", "pxd058436_DN05", "psm"))
        self.assertEqual(c.tags, ["cal0", "cal1", "cal_off", "low_memory"])
        self.assertEqual(c.unknown_tags, [])

    def test_r_r3_c_f(self):
        c = self.ctx
        r_ps = {u.name for u in c.R(("prose", "sage"), "psm")}
        r_pm = {u.name for u in c.R(("prose", "msfragger"), "psm")}
        r3 = {u.name for u in c.R3("psm")}
        self.assertNotIn("pxd011695_HCD_r1", r_ps)  # Sage zero: out of every ratio
        self.assertIn("pxd011695_HCD_r1", r_pm)
        self.assertNotIn("pxd058436_DN05", r_ps)  # Sage failed_memory
        self.assertIn("pxd058436_DN05", r_pm)
        self.assertNotIn("pxd011695_ETciD_r1", r3)  # bycz: no Sage
        self.assertIn("pxd011695_ETciD_r1", r_pm)
        for s in (r_ps, r_pm, r3):
            self.assertFalse(s & {"astral250pg_A2", "pxd058436_DN13"})  # decision units
        self.assertTrue(r3 <= r_ps and r3 <= r_pm)
        self.assertEqual(c.reason("pxd011695_HCD_r1", ("prose", "sage"), "psm"), "sage:zero")
        self.assertEqual(c.reason("astral250pg_A2", ("prose", "sage"), "psm"), "decision")
        self.assertEqual([u.name for u in c.C("pxd011695_HCD", "psm")], ["pxd011695_HCD_r1"])  # zero allowed
        self.assertEqual([u.name for u in c.C("astral_250pg", "psm")], ["astral250pg_B1", "astral250pg_B3"])
        f = c.F("psm", "shuffled")
        self.assertEqual(f["velos_r1"], ["hy_entrap_s1_td", "hy_entrap_s2_td"])  # Sage failed on s3
        self.assertIn("pxd011695_ETciD_r1", f)  # E(u) = prose, msfragger
        self.assertNotIn("pxd011695_HCD_r1", f)  # Sage accepted nothing
        self.assertNotIn("astral250pg_A2", f)
        self.assertEqual(c.F("psm", "natural")["velos_r1"], ["hy_velos_natural_td"])
        self.assertEqual(list(c.F("psm", "arath")), ["hfx_r1", "eclipse_tmtpro_r1", "astral_r1"])

    def test_t_b3(self):
        c = self.ctx
        t_ps = {u.name for u in c.T(("prose", "sage"))}
        t_pm = {u.name for u in c.T(("prose", "msfragger"))}
        t3 = {u.name for u in c.T3()}
        self.assertNotIn("pxd058436_DN05", t_ps)  # Sage failed_memory
        self.assertNotIn("iprg2015_r1", t_pm)  # MSFragger no_timing in r2
        self.assertIn("iprg2015_r1", t_ps)
        self.assertNotIn("astral250pg_A2", t3)
        self.assertTrue(t3 <= t_ps and t3 <= t_pm)
        self.assertEqual(c.B3(), ["astral_250pg"])

    def test_coverage_rows(self):
        c = self.ctx
        row = c.coverage_row("prose", "scaling", "hfx_r1", "hye_td_t16")
        self.assertEqual((row.db, row.threads, row.scope, row.counted), ("hye_td", 16, "scaling", False))
        row = c.coverage_row("sage", "per_file", "pxd058436_DN05", "pxd058436_td")
        self.assertEqual(row.state, "failed_memory")
        self.assertEqual(row.status, "failed_memory stage all repetition 0 exit 137")
        self.assertEqual(c.coverage_row("msfragger", "batch", "astral_250pg", "hye_td").group.n_files, 3)
        self.assertEqual(c.unflagged_scaling, [])
        self.assertEqual(c.coverage_outside, [])


# ---------------------------------------------------------------- timings (SPEC 2.5): T12-T16, T30
class TestTimings(unittest.TestCase):
    def setUp(self):
        self.ctx = base_ctx()

    def test_t12_median_of_totals(self):
        t = self.ctx.timing("msfragger", "per_file", "hfx_r1")
        self.assertEqual(t.state, "complete")
        self.assertEqual(t.wall_r, {1: 120.0, 2: 100.0, 3: 115.0})
        self.assertEqual(t.wall_med, 115.0)  # not 90 + 15 = 105
        self.assertEqual(t.stage_wall_med, {"search": 90.0, "rescoring": 15.0})
        self.assertEqual(t.expected, {"search": 1, "rescoring": 1})

    def test_t13_median_tie(self):
        self.assertEqual(self.ctx.timing("prose", "per_file", "ups1_r1").wall_med, 100.0)

    def test_t14_rss_max(self):
        t = self.ctx.timing("msfragger", "per_file", "hfx_r1")
        self.assertEqual(t.rss_r_kb, {1: 2000000, 2: 2000000, 3: 2000000})
        self.assertEqual(t.rss_med_kb, 2000000)
        self.assertEqual(f"{T.gib(t.rss_med_kb):.6f}", "1.907349")

    def test_t15_attempts(self):
        c = self.ctx
        key = ("sage", "per_file", "lumos_lfq_r1", "hy_td", None)
        t = c.timings[key]
        self.assertEqual(t.n_attempts, 2)
        self.assertEqual(t.attempts[0].state, "incomplete")
        self.assertIs(t.attempt, t.attempts[-1])
        self.assertEqual((t.state, t.wall_med), ("complete", 69.0))
        self.assertIn((key, 1), c.earlier_attempts)
        self.assertIsInstance(c.timing_value("sage", "per_file", "lumos_lfq_r1"), T.Timing)

    def test_t16_no_timing(self):
        c = self.ctx
        t = c.timing("msfragger", "per_file", "iprg2015_r1")
        self.assertEqual(t.state, "no_timing")
        self.assertIn("no_timing", t.note)
        for v in (t.wall_med, t.cpu_med, t.rss_med_kb):
            self.assertEqual(v, T.Missing("no_timing"))
        self.assertEqual(c.timing_value("msfragger", "per_file", "iprg2015_r1"), T.Missing("no_timing"))

    def test_t30_attempts_across_threads(self):
        t = self.ctx.timing("prose", "per_file", "lumos_tmt_r1")
        self.assertEqual(t.n_attempts, 2)
        self.assertEqual([a.threads for a in t.attempts], [16, 8])
        self.assertEqual((t.threads, t.state, t.wall_med), (8, "complete", 101.0))

    def test_failed_memory_and_shapes(self):
        c = self.ctx
        self.assertEqual(c.timing_value("sage", "per_file", "pxd058436_DN05"), T.Missing("failed_memory"))
        pooled = c.timing("msfragger", "per_file", "pxd058436_DN05")
        self.assertEqual((pooled.state, pooled.expected), ("complete", {"search": 1, "join": 1, "rescoring": 1}))
        batch = c.timing("msfragger", "batch", "astral_250pg")
        self.assertEqual((batch.state, batch.expected), ("complete", {"search": 1, "rescoring": 3}))
        self.assertEqual(c.timing("prose", "batch", "astral_250pg").wall_med, 285.0)  # T17 batch median
        s = c.timing("prose", "scaling", "hfx_r1", threads=16)
        self.assertEqual((s.state, s.wall_med), ("complete", 125.0))  # repetition 0 only at the top point
        s1 = c.timing("prose", "scaling", "hfx_r1", threads=1)
        self.assertEqual((s1.state, s1.wall_med, 0 in s1.reps), ("complete", 1600.0, False))
        low = c.timing("prose", "per_file_low_memory", "pxd058436_DN13")
        self.assertEqual(low.state, "complete")
        self.assertEqual(c.search_dir("prose", "scaling", "hfx_r1", "hye_td", 8), None)  # no W given


# ---------------------------------------------------------------- T19: scaling over the limit, driver format
class TestOverLimit(TempDir):
    def overlimit_ctx(self):
        w = self.path("W")
        os.makedirs(w)
        not_scaling = lambda line: line.split("\t")[1] != "scaling"
        copy_with(fx("coverage_fx.tsv"), os.path.join(w, "coverage.tsv"), keep=not_scaling)
        copy_with(fx("timings_fx.tsv"), os.path.join(w, "timings.tsv"), keep=not_scaling)
        shutil.copy(fx("counts_fx.tsv"), os.path.join(w, "counts.tsv"))
        return T.load(T.Options(runs=fx("runs_fx.tsv"), work=w, scaling_coverage=fx("coverage_overlimit_fx.tsv"),
                                scaling_timings=fx("timings_overlimit_fx.tsv"), params_dir=fx("params_fx"),
                                references=None, mzml_counts=None))

    def test_t19(self):
        c = self.overlimit_ctx()
        for e in ("prose", "msfragger"):
            for n in (16, 8, 4):
                self.assertIsInstance(c.timing_value(e, "scaling", "hfx_r1", threads=n), T.Timing)
            t2 = c.timing(e, "scaling", "hfx_r1", threads=2)
            self.assertEqual(t2.state, "over_limit")
            self.assertEqual(t2.lower_bound, L)  # min({} u {L})
            self.assertEqual(t2.limit, L)
            self.assertEqual(t2.wall_med, T.Missing("over_limit"))  # L is never read as a wall time
            self.assertEqual(c.timing_value(e, "scaling", "hfx_r1", threads=2), T.Missing("over_limit"))
            self.assertEqual(c.coverage_row(e, "scaling", "hfx_r1", "hye_td_t2").state, "over_limit")
            t1 = c.timing(e, "scaling", "hfx_r1", threads=1)
            self.assertEqual(t1.state, "not_run_over_limit")
            self.assertIsNone(t1.attempt)
            self.assertEqual(t1.n_attempts, 0)
            self.assertEqual(t1.limit, L)
            self.assertEqual(t1.wall_med, T.Missing("not_run_over_limit"))
            self.assertIsNone(c.coverage_row(e, "scaling", "hfx_r1", "hye_td_t1"))  # no folder, no coverage row
            self.assertEqual(c.timing_value(e, "scaling", "hfx_r1", threads=1), T.Missing("not_run_over_limit"))
        self.assertEqual(c.timing("prose", "scaling", "hfx_r1", threads=4).wall_med, 412.0)
        self.assertEqual(c.timing("prose", "scaling", "hfx_r1", threads=16).wall_med, 127.0)

    def test_lower_bound_with_completed_repetitions(self):
        p = self.path("timings.tsv")
        with open(p, "w", encoding="utf-8") as f:
            f.write("\t".join(T.TIMINGS_HEADER) + "\n")
            for rep, wall, code in ((1, "500.00", "0"), (2, "450.00", "0"), (3, "86400.00", "over_limit")):
                cpu, rss = ("nan", "NA") if code == "over_limit" else ("4000.00", "100")
                f.write(f"prose\tscaling\thfx_r1\thye_td.fasta\tall\t2\t{rep}\t{wall}\t{cpu}\t{rss}\t{code}\n")
        w = self.path("W")
        os.makedirs(w)
        copy_with(fx("coverage_fx.tsv"), os.path.join(w, "coverage.tsv"))
        shutil.copy(fx("counts_fx.tsv"), os.path.join(w, "counts.tsv"))
        c = T.load(T.Options(runs=fx("runs_fx.tsv"), work=w, timings=p, params_dir=fx("params_fx"),
                             references=None, mzml_counts=None))
        t = c.timing("prose", "scaling", "hfx_r1", threads=2)
        self.assertEqual((t.state, t.lower_bound), ("over_limit", 450.0))

    def test_scaling_rows_in_both_folders_stop(self):
        w = self.path("W")
        os.makedirs(w)
        for name in ("coverage", "timings", "counts"):
            shutil.copy(fx(f"{name}_fx.tsv"), os.path.join(w, f"{name}.tsv"))
        with self.assertRaises(T.ValidationStop) as cm:
            T.load(T.Options(runs=fx("runs_fx.tsv"), work=w, scaling_coverage=fx("coverage_overlimit_fx.tsv"),
                             scaling_timings=fx("timings_overlimit_fx.tsv"), params_dir=fx("params_fx"),
                             references=None, mzml_counts=None))
        self.assertIn("scaling", cm.exception.message)


# ---------------------------------------------------------------- T21 validation stops
class TestStops(TempDir):
    CH = T.COUNTS_HEADER
    VH = T.COVERAGE_HEADER

    def assert_stop(self, opts, *fragments):
        with self.assertRaises(SystemExit) as cm:
            T.load(opts)
        err = cm.exception
        self.assertIsInstance(err, T.ValidationStop)
        self.assertEqual(err.code, 2)
        self.assertIn("line ", err.message)
        self.assertIn("column ", err.message)
        for x in fragments:
            self.assertIn(x, err.message)
        return err.message

    def counts_edit(self, col, value, line_no=2):
        return copy_with(fx("counts_fx.tsv"), self.path("counts.tsv"),
                         edit=lambda i, x: set_field(x, col, value, self.CH) if i == line_no else x)

    def test_level_protein(self):
        p = self.counts_edit("level", "protein")
        self.assert_stop(options(counts=p), "line 2", "column level", "'protein'", "psm, peptide")

    def test_class_i(self):
        p = self.counts_edit("class", "I")
        self.assert_stop(options(counts=p), "line 2", "column class", "'I'")

    def test_known_arm_wrong_engine(self):
        p = self.counts_edit("benchmark", "per_file_low_memory")  # line 2 is a MSFragger row
        self.assertTrue(open(p, encoding="utf-8").read().splitlines()[1].startswith("msfragger"))
        self.assert_stop(options(counts=p), "line 2", "column engine", "per_file_low_memory")
        done = []

        def first_msfragger_per_file(i, x):
            if not done and x.startswith("msfragger\tper_file\t"):
                done.append(i)
                return set_field(x, "benchmark", "per_file_cal_off", self.VH)
            return x
        q = copy_with(fx("coverage_fx.tsv"), self.path("coverage.tsv"), edit=first_msfragger_per_file)
        self.assert_stop(options(coverage=q), f"line {done[0]}", "column engine", "per_file_cal_off")

    def test_unknown_group(self):
        h = list(T.RUNS_COLUMNS)
        p = copy_with(fx("runs_fx.tsv"), self.path("runs.tsv"),
                      edit=lambda i, x: set_field(x, "group", "velos_new", h) if i == 2 else x)
        self.assert_stop(options(runs=p), "line 2", "column group", "'velos_new'")

    def test_other_stops(self):
        p = self.counts_edit("q_value", "0.05")
        self.assert_stop(options(counts=p), "column q_value")
        p = self.counts_edit("file", "other.count.idXML")
        self.assert_stop(options(counts=p), "column file", "count.idXML")
        p = self.counts_edit("accepted", "NA")
        self.assert_stop(options(counts=p), "column accepted")
        p = copy_with(fx("counts_fx.tsv"), self.path("counts2.tsv"), keep=lambda x: not (
            x.startswith("prose\tper_file\tvelos_r1\thy_td\t") and "\tpeptide\t" in x))
        self.assert_stop(options(counts=p), "column level")  # a search without its peptide row
        q = copy_with(fx("coverage_fx.tsv"), self.path("coverage.tsv"),
                      edit=lambda i, x: set_field(x, "status", "done", self.VH) if i == 3 else x)
        self.assert_stop(options(coverage=q), "column status", "'done'")
        t = copy_with(fx("timings_fx.tsv"), self.path("timings.tsv"),
                      edit=lambda i, x: set_field(x, "stage", "search", T.TIMINGS_HEADER)
                      if x.startswith("prose\tper_file\t") else x)
        self.assert_stop(options(timings=t), "column stage")
        h = list(T.RUNS_COLUMNS)
        r = copy_with(fx("runs_fx.tsv"), self.path("runs.tsv"),
                      edit=lambda i, x: set_field(x, "role", "tuned", h) if i == 16 else x)
        self.assert_stop(options(runs=r), "column role")  # a replicate of a decision sample with another role

    def test_outside_design_is_excluded(self):
        p = copy_with(fx("counts_fx.tsv"), self.path("counts.tsv"))
        with open(p, "a", encoding="utf-8") as f:
            for level in ("psm", "peptide"):
                f.write(f"prose\tper_file\tvelos_r1\thy_other_td\tvelos_r1.count.idXML\t{level}\tall\t0.01\t10\t0\t0\t0"
                        "\tNA\tNA\tNA\t1\n")
                f.write(f"prose\tper_file_newarm\tvelos_r1\thy_td\tvelos_r1.count.idXML\t{level}\tall\t0.01\t10\t0\t0"
                        "\t0\tNA\tNA\tNA\t1\n")
        c = T.load(options(counts=p))
        self.assertEqual([(r.database, r.design) for r in c.counts_outside],
                         [("hy_other_td", "outside_design")] * 2)
        self.assertEqual(c.unknown_tags, ["newarm"])  # a generic arm (O25), not a stop
        self.assertEqual(c.accepted("prose", "velos_r1", "psm", benchmark="per_file_newarm"),
                         T.Missing("no_coverage"))


# ---------------------------------------------------------------- T28 smoke layout, W_node, T33
class TestLayouts(TempDir):
    def test_t28_smoke(self):
        o = T.Options(runs=fx("runs_smoke_fx.tsv"), design="none", counts=fx("counts_smoke_fx.tsv"),
                      coverage=fx("coverage_smoke_fx.tsv"), timings=fx("timings_smoke_fx.tsv"), references=None,
                      mzml_counts=None)
        c = T.load(o)
        self.assertEqual([u.name for u in c.units], ["bsa1", "bsa2", "bsa3"])
        u = c.unit("bsa1")
        self.assertEqual((u.kind, u.role, u.cls, u.grade, u.side), ("other", "heldout", "-", "-", None))
        self.assertEqual(u.entrap, (("smoke_entrap_td", "shuffled", None),))
        self.assertEqual(list(c.batch_groups), ["smoke"])
        self.assertEqual(c.scaling_runs, ("bsa1",))
        self.assertEqual(c.timing("msfragger", "batch", "smoke").state, "complete")
        self.assertEqual(c.timing("prose", "scaling", "bsa1", threads=8).state, "complete")
        self.assertEqual(c.timing("prose", "scaling", "bsa1", threads=1).state, "complete")
        self.assertIsInstance(c.count_row("prose", "bsa1", "psm").lower_bound_fdp, float)  # printed as int 0
        self.assertIsNone(c.pooled_arrangement)
        self.assertEqual(len(c.R3("psm")), 3)
        with self.assertRaises(T.ValidationStop):  # the smoke table has no role column
            T.load(T.Options(runs=fx("runs_smoke_fx.tsv"), counts=fx("counts_smoke_fx.tsv"),
                             coverage=fx("coverage_smoke_fx.tsv"), timings=fx("timings_smoke_fx.tsv"),
                             references=None, mzml_counts=None))

    def test_wnode_decision_only(self):
        c = T.load(options(counts=fx("counts_wnode_fx.tsv"), coverage=fx("coverage_wnode_fx.tsv"),
                           timings=fx("timings_wnode_fx.tsv")))
        self.assertEqual(c.R(("prose", "msfragger"), "psm"), [])
        self.assertEqual(c.R3("peptide"), [])
        self.assertEqual(c.F("psm", "shuffled"), {})
        self.assertEqual(c.T3(), [])
        self.assertEqual(c.B3(), [])
        self.assertEqual(T.gmean([]), T.Missing("empty"))
        self.assertEqual(c.accepted("prose", "velos_r1", "psm"), T.Missing("not_run"))
        self.assertIsInstance(c.accepted("prose", "astral250pg_A2", "psm"), int)

    def test_t33_pooled_arrangement(self):
        per_file, joint = fx("params_fx/immuno_per_file.ini"), fx("params_fx/immuno_joint.ini")
        mode, found = design.read_pooled_arrangement([per_file])
        self.assertEqual((mode, design.other_arrangement_tag(mode)), ("per_file", "mode_joint"))
        mode, _ = design.read_pooled_arrangement([joint])
        self.assertEqual((mode, design.other_arrangement_tag(mode)), ("joint", "mode_per_file"))
        with self.assertRaises(T.ValidationStop):
            design.read_pooled_arrangement([per_file, joint])
        h = list(T.RUNS_COLUMNS)
        p = copy_with(fx("runs_fx.tsv"), self.path("runs.tsv"),
                      edit=lambda i, x: set_field(x, "params", "immuno_joint", h) if "\tp19_DN05_r1" in "\t" + x
                      else x)
        with self.assertRaises(T.ValidationStop) as cm:  # a mismatch across the immuno groups stops
            T.load(options(runs=p))
        self.assertIn("disagree", cm.exception.message)


# ---------------------------------------------------------------- Ctx outputs
class TestOutputs(TempDir):
    def test_write_table_and_number(self):
        c = T.load(options(out=self.tmp))
        path = c.write_table("O99_test_runs", ["unit", "grade", "ratio", "gib", "ok", "note"],
                             [{"unit": "velos_r1", "grade": "-", "ratio": 1.1, "gib": 1.9073486, "ok": True,
                               "note": ""},
                              ["hfx_r1", "-", T.Missing("zero"), None, False, ""]],
                             formats={"gib": T.FMT_GIB}, auto_note=True)
        with open(path, encoding="utf-8") as f:
            text = f.read()
        self.assertEqual(text, "unit\tgrade\tratio\tgib\tok\tnote\nvelos_r1\t-\t1.100000\t1.907\tyes\t\n"
                               "hfx_r1\t-\tNA\tNA\tno\tzero (ratio)\n")
        self.assertEqual(c.results["O99_test_runs"][1]["ratio"], T.Missing("zero"))
        cols, rows = T.read_table(path)
        self.assertEqual((cols[0], rows[1]["ratio"]), ("unit", "NA"))
        with self.assertRaises(ValueError):
            c.write_table("O99_test_runs", ["a"], [])
        with self.assertRaises(ValueError):
            c.write_table("O98_bad", ["a"], [{"b": 1}])
        c.number("ids.heldout.psm.msfragger.lead", 12.345, "12.3%", "%", "O2", "DS:624", "heldout")
        c.number("ids.tuning.psm.msfragger.lead", 1.0, "1.0%", source_side="tuning")
        c.number("scaling.prose.speedup_t16", 12.8)
        self.assertEqual([n.main_text_allowed for n in c.numbers], ["yes", "no", "yes"])
        with self.assertRaises(ValueError):
            c.number("Bad Key", 1)
        with self.assertRaises(ValueError):
            c.number("scaling.prose.speedup_t16", 1)
        self.assertTrue(c.want("ids"))
        with self.assertRaises(ValueError):
            c.want("nonsense")

    def test_numbers_tex(self):
        import summarize  # benchmarks/summarize.py (top_level_dir = benchmarks)
        c = T.load(options(out=self.tmp))
        c.number("scaling.prose.speedup_t16", 12.8, "12.8")
        c.number("ids.heldout_grade_a.psm.sage.lead", 0.05, "5.0%", source_side="heldout")
        summarize.write_numbers(c, self.tmp)
        with open(os.path.join(self.tmp, "numbers.tex"), encoding="utf-8") as f:
            tex = f.read()
        self.assertIn(summarize.NUM_MACRO, tex)
        self.assertIn("\\expandafter\\def\\csname num@scaling.prose.speedup_t16\\endcsname{12.8}", tex)
        self.assertIn("\\csname num@ids.heldout_grade_a.psm.sage.lead\\endcsname{5.0\\%}", tex)
        with open(os.path.join(self.tmp, "numbers.tsv"), encoding="utf-8") as f:
            lines = f.read().splitlines()
        self.assertEqual(lines[0].split("\t"), list(summarize.NUMBERS_COLUMNS))
        self.assertEqual(lines[1].split("\t")[:3], ["scaling.prose.speedup_t16", "12.8", "12.8"])

    def test_yaml_subset(self):
        text = ('shared:\n  fragment_tol: 0.5\n  fragment_tol_unit: "Da"\n  files:\n    - "a.mzML"\n    - "b.mzML"\n'
                '  seconds_total: 12.5\nper_file:\n  - file: "a.mzML"\n    rescored: true\n    timing_seconds:\n'
                '      calibration: 1.5\n      search: 3\n  - file: "b.mzML"\n    rescored: false\n')
        y = T.parse_yaml(text)
        self.assertEqual(y["shared"], {"fragment_tol": 0.5, "fragment_tol_unit": "Da", "files": ["a.mzML", "b.mzML"],
                                       "seconds_total": 12.5})
        self.assertEqual(y["per_file"][0], {"file": "a.mzML", "rescored": True,
                                            "timing_seconds": {"calibration": 1.5, "search": 3}})
        self.assertEqual(y["per_file"][1], {"file": "b.mzML", "rescored": False})

    def test_read_machine(self):
        """key: value lines split at a ':' followed by whitespace; the kernel line (with a time stamp) and other
        lines are kept whole (machine.txt of PN:30)."""
        rows = T.read_machine(fx("timing_machine_fx.txt"))
        self.assertEqual(rows[0], ("", "header", "prepare_node.sh, 2026-01-01T00:00:00+00:00"))
        self.assertIn(("", "memory cap", "--mem-gb 200"), rows)
        self.assertIn(("RAM", "MemTotal", "2097152 kB"), rows)
        self.assertIn(("CPU", "CPU(s)", "16"), rows)
        self.assertIn(("CPU", "Vulnerability Meltdown", "Not affected"), rows)
        self.assertIn(("OS", "", "Linux 6.8.0-1-generic #1 SMP Mon Jan 1 12:34:56 UTC 2026 x86_64"), rows)
        self.assertIn(("memory cap check (systemd-run --user --scope, MemoryMax=200G, MemorySwapMax=0)", "machine",
                       "passed 2026-01-01T00:00:00+00:00"), rows)

    def test_sha256_file(self):
        with open(fx("runs_smoke_fx.tsv"), "rb") as f:
            expected = hashlib.sha256(f.read()).hexdigest()
        self.assertEqual(T.sha256_file(fx("runs_smoke_fx.tsv")), expected)


if __name__ == "__main__":
    unittest.main()
