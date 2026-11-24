"""Tests of timing.py (SPEC 6) at output level: T12-T16 and T30 in O15, T17 (O16), T18 and T19 (O17), T22 (the
data part of O10), T24 (the O15b parsers and rows), T31 (stale timing in O15), plus O15 sets and keys, O18, the
smoke and W_node layouts and --only. Fixtures: the base fixtures of test_tables.py and fixtures/timing_* (made-up
numbers in the line shapes of the engine logs, versions.txt and node_prep/machine.txt)."""
import math
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

sys.dont_write_bytecode = True

from summaries import tables as T, timing  # noqa: E402

FX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")
L = 86400.0  # the time limit of timings_overlimit_fx.tsv


def fx(name):
    return os.path.join(FX, name)


def options(**kw):
    """Options of the base fixture W (runs_fx + counts/coverage/timings_fx) with the timing_* versions and machine
    files."""
    o = dict(runs=fx("runs_fx.tsv"), counts=fx("counts_fx.tsv"), coverage=fx("coverage_fx.tsv"),
             timings=fx("timings_fx.tsv"), versions=fx("timing_versions_fx.txt"), params_dir=fx("params_fx"),
             references=None, mzml_counts=None, machines=(("fx", fx("timing_machine_fx.txt")),))
    o.update(kw)
    return T.Options(**o)


def build(opts):
    ctx = T.load(opts)
    timing.build(ctx)
    return ctx


def rows(ctx, table, **kw):
    return [r for r in ctx.results[table] if all(r[k] == v for k, v in kw.items())]


def row(ctx, table, **kw):
    found = rows(ctx, table, **kw)
    if len(found) != 1:
        raise AssertionError(f"{table} {kw}: {len(found)} rows")
    return found[0]


def number(ctx, key):
    found = [n for n in ctx.numbers if n.key == key]
    return found[0] if found else None


def checks(ctx, cid):
    return [(lv, msg) for lv, c, msg in ctx.report.lines if c == cid]


def read_tsv(path):
    """(header note, column names, [dict]) of a written table."""
    with open(path, encoding="utf-8") as f:
        lines = f.read().splitlines()
    note = lines[0][2:] if lines and lines[0].startswith("# ") else ""
    lines = [x for x in lines if not x.startswith("#")]
    cols = lines[0].split("\t")
    return note, cols, [dict(zip(cols, x.split("\t"))) for x in lines[1:]]


def copy_with(src, dst, edit=None):
    """A copy of a fixture TSV; edit(line) -> line rewrites the data lines."""
    with open(src, encoding="utf-8", newline="") as f:
        lines = f.read().splitlines(True)
    with open(dst, "w", encoding="utf-8", newline="") as f:
        f.write("".join([lines[0]] + [edit(x) if edit else x for x in lines[1:]]))
    return dst


def make_w(root, keep=None):
    """A work folder W with the base counts, coverage and timings (keep(line) filters coverage and timings)."""
    w = os.path.join(root, "W")
    os.makedirs(w)
    for name in ("counts", "coverage", "timings"):
        src = fx(f"{name}_fx.tsv")
        if keep and name != "counts":
            with open(src, encoding="utf-8", newline="") as f:
                lines = f.read().splitlines(True)
            with open(os.path.join(w, f"{name}.tsv"), "w", encoding="utf-8", newline="") as f:
                f.write("".join([lines[0]] + [x for x in lines[1:] if keep(x)]))
        else:
            shutil.copy(src, os.path.join(w, f"{name}.tsv"))
    return w


def w_options(w, **kw):
    o = dict(runs=fx("runs_fx.tsv"), work=w, params_dir=fx("params_fx"), references=None, mzml_counts=None,
             versions=fx("timing_versions_fx.txt"), machines=(("fx", fx("timing_machine_fx.txt")),))
    o.update(kw)
    return T.Options(**o)


class TempDir(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="timing_test_")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)


class BaseBuild(unittest.TestCase):
    """One build of the base fixtures into a temporary output folder, shared by the tests of a class."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="timing_test_")
        cls.ctx = build(options(out=os.path.join(cls.tmp, "out")))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def table(self, name):
        return read_tsv(os.path.join(self.tmp, "out", "tables", name + ".tsv"))


# ---------------------------------------------------------------- helpers
class TestHelpers(unittest.TestCase):
    def test_formats(self):
        f = timing._formats(timing.O15_RUNS + timing.O16 + timing.O17 + timing.O15_SUMMARY + ["seconds"])
        for c in ("wall_med_s", "wall_r1", "cpu_r3", "batch_wall_per_file_s", "seconds", "wall_lower_bound_s"):
            self.assertEqual(f[c], T.FMT_S, c)
        for c in ("rss_med_gib", "rss_r2_gib", "max_per_file_rss_gib", "gc_heap_gib"):
            self.assertEqual(f[c], T.FMT_GIB, c)
        for c in ("ratio_wall", "speedup", "efficiency_rel", "cores_used", "equal_weight"):
            self.assertEqual(f[c], T.FMT_RATIO, c)
        self.assertEqual(f["total_wall_h_prose"], ".4f")
        g = timing._formats(timing.O10)
        self.assertEqual((g["wall_std"], g["wall_lm"], g["wall_ratio"], g["rss_ratio"]),
                         (T.FMT_S, T.FMT_S, T.FMT_RATIO, T.FMT_RATIO))

    def test_sig3(self):
        self.assertEqual(timing._sig3(0.022649), "0.0226")
        self.assertEqual(timing._sig3(2.6123), "2.61")
        self.assertEqual(timing._sig3(23.456), "23.5")
        self.assertEqual(timing._sig3(1132.4), "1132")
        self.assertEqual(timing._sig3(12.8), "12.8")
        self.assertEqual(timing._sig3(T.Missing("empty")), "NA")

    def test_version_tool_and_text(self):
        self.assertEqual(timing.version_tool("java -jar /x/MSFragger-4.4.1/MSFragger-4.4.1.jar --version"),
                         "msfragger")
        self.assertEqual(timing.version_tool("/opt/bench/tools/sage-v0.14.7/sage --version"), "sage")
        self.assertEqual(timing.version_tool("/opt/bench/openms/bin/EntrapmentEvaluator --help"),
                         "entrapmentevaluator")
        self.assertEqual(timing.version_text("prose", "Version: 3.7.0-pre-HEAD-x Jan 01 2026, Revision: abc1234"),
                         "3.7.0-pre-HEAD-x, revision abc1234")
        self.assertEqual(timing.version_text("percolator", "Percolator version 3.09.0, Build Date x"), "3.09.0")
        self.assertEqual(timing.version_text("other", "tool 1.0 | more"), "tool 1.0")

    def test_failures_are_collected(self):
        with mock.patch.object(timing, "build_o16", side_effect=KeyError("boom")):
            ctx = T.load(options())
            with self.assertRaises(RuntimeError) as cm:
                timing.build(ctx)
        self.assertIn("O16: KeyError", str(cm.exception))
        self.assertIsInstance(cm.exception.__cause__, KeyError)
        self.assertIn("O15_time_runs", ctx.results)  # the other outputs are still written
        self.assertIn("O17_scaling", ctx.results)
        self.assertNotIn("O16_batch", ctx.results)


# ---------------------------------------------------------------- O15: T12-T16, T30
class TestO15(BaseBuild):
    def run_row(self, engine, unit):
        return row(self.ctx, "O15_time_runs", engine=engine, unit=unit)

    def test_t12_median_of_totals(self):
        r = self.run_row("msfragger", "hfx_r1")
        self.assertEqual(r["state"], "ok")
        self.assertEqual((r["wall_r1"], r["wall_r2"], r["wall_r3"]), (120.0, 100.0, 115.0))
        self.assertEqual(r["wall_med_s"], 115.0)  # not 90 + 15 = 105
        self.assertEqual((r["search_wall_med_s"], r["rescoring_wall_med_s"]), (90.0, 15.0))
        self.assertIsNone(r["join_wall_med_s"])  # not a pooled sample
        self.assertEqual(r["n_reps"], 3)
        self.assertEqual(self.run_row("msfragger", "pxd058436_DN05")["join_wall_med_s"], 2.0)
        self.assertIsNone(self.run_row("prose", "hfx_r1")["search_wall_med_s"])  # stage columns: MSFragger only

    def test_t13_median_tie(self):
        self.assertEqual(self.run_row("prose", "ups1_r1")["wall_med_s"], 100.0)

    def test_t14_rss(self):
        r = self.run_row("msfragger", "hfx_r1")
        self.assertEqual(f"{r['rss_med_gib']:.6f}", "1.907349")
        self.assertEqual(f"{r['rss_r1_gib']:.6f}", "1.907349")
        _, _, tsv = self.table("O15_time_runs")
        line = [x for x in tsv if x["engine"] == "msfragger" and x["unit"] == "hfx_r1"][0]
        self.assertEqual((line["rss_med_gib"], line["wall_med_s"], line["wall_r2"]), ("1.907", "115.00", "100.00"))

    def test_t15_attempts(self):
        r = self.run_row("sage", "lumos_lfq_r1")
        self.assertEqual((r["state"], r["wall_med_s"]), ("ok", 69.0))
        self.assertIn("1 earlier attempt(s) not used", r["note"])

    def test_t16_no_timing(self):
        r = self.run_row("msfragger", "iprg2015_r1")
        self.assertEqual(r["state"], "no_timing")
        for c in ("wall_med_s", "cpu_med_s", "rss_med_gib", "search_wall_med_s", "rescoring_wall_med_s", "wall_r2"):
            self.assertIsInstance(r[c], T.Missing, c)
        self.assertEqual((r["wall_r1"], r["wall_r3"], r["n_reps"]), (97.0, 101.0, 2))  # complete reps as measured
        self.assertIn("no_timing", r["note"])
        _, _, tsv = self.table("O15_time_runs")
        line = [x for x in tsv if x["engine"] == "msfragger" and x["unit"] == "iprg2015_r1"][0]
        self.assertEqual((line["wall_med_s"], line["wall_r2"], line["wall_r1"]), ("NA", "NA", "97.00"))

    def test_t30_attempts_across_threads(self):
        r = self.run_row("prose", "lumos_tmt_r1")
        self.assertEqual((r["threads"], r["wall_med_s"]), (8, 101.0))
        self.assertIn("1 earlier attempt(s) not used", r["note"])

    def test_failed_memory_is_na(self):
        r = self.run_row("sage", "pxd058436_DN05")
        self.assertEqual(r["state"], "failed_memory")
        for c in ("wall_med_s", "wall_r1", "rss_med_gib"):
            self.assertIsInstance(r[c], T.Missing, c)
        self.assertEqual(r["note"], "failed_memory stage all repetition 0 exit 137")

    def test_rows_and_gc_column(self):
        runs = self.ctx.results["O15_time_runs"]
        self.assertEqual(len(runs), 68)  # 23 units x 3 engines, no Sage on the bycz unit
        self.assertEqual(rows(self.ctx, "O15_time_runs", engine="sage", unit="pxd011695_ETciD_r1"), [])
        self.assertEqual(self.run_row("msfragger", "velos_r1")["gc_heap_gib"], T.Missing("no_gc_logs"))
        self.assertIsNone(self.run_row("prose", "velos_r1")["gc_heap_gib"])
        note, cols, _ = self.table("O15_time_runs")
        self.assertEqual(cols, timing.O15_RUNS)
        self.assertIn("JVM heap", note)

    def test_datasets(self):
        c = self.ctx
        r = row(c, "O15_time_datasets", pair="sage/prose", group="pxd058436_classI")
        self.assertEqual((r["n_units_group"], r["n_units"]), (1, 0))  # DN13 is a decision sample
        self.assertEqual(r["note"], "out of T(pair): sage:failed_memory 1")
        self.assertEqual(r["wall_ratio_gmean"], T.Missing("empty"))
        self.assertEqual((r["n_units_own_prose"], r["n_units_own_comparator"]), (1, 0))
        r = row(c, "O15_time_datasets", pair="msfragger/prose", group="iprg2015")
        self.assertEqual(r["note"], "out of T(pair): msfragger:no_timing 1")
        r = row(c, "O15_time_datasets", pair="msfragger/prose", group="astral_250pg")
        self.assertEqual((r["n_units_group"], r["n_units"]), (2, 2))
        self.assertEqual(r["sum_wall_med_s_prose"], 230.0)  # B1 110 + B3 120; A2 is a decision run
        self.assertAlmostEqual(r["wall_ratio_gmean"], math.sqrt((137 / 110) * (142 / 120)), places=12)
        self.assertEqual(rows(c, "O15_time_datasets", pair="sage/prose", group="pxd011695_ETciD"), [])

    def test_summary_and_keys(self):
        c = self.ctx
        e = row(c, "O15_time_summary", kind="electron", set="pair", pair="msfragger/prose")
        self.assertEqual((e["n_datasets"], e["n_units"]), (1, 1))
        self.assertAlmostEqual(e["equal_weight"], 97 / 91, places=12)  # the single electron unit's ratio
        self.assertAlmostEqual(e["run_weighted"], 97 / 91, places=12)
        self.assertEqual(rows(c, "O15_time_summary", kind="electron", pair="sage/prose"), [])
        self.assertIsNone(number(c, "time.electron.sage_prose.ratio"))
        n = number(c, "time.electron.msfragger_prose.ratio")
        self.assertAlmostEqual(n.value, 97 / 91, places=12)
        self.assertEqual((n.text, n.source_side, n.output), ("1.07", "heldout", "O15"))
        self.assertAlmostEqual(number(c, "time.electron.msfragger_prose.prose.total_h").value, 91 / 3600, places=12)
        i = row(c, "O15_time_summary", kind="immuno", set="pair", pair="sage/prose")
        self.assertEqual((i["n_datasets"], i["dropped_datasets"]), (1, "pxd058436_classI"))
        # equal weight = gmean over the tryptic datasets of the per-dataset gmeans of O15_time_datasets
        tryptic = [r for r in c.results["O15_time_datasets"] if r["pair"] == "sage/prose"
                   and r["kind"] in ("tuning", "heldout") and r["n_units"] > 0]
        t = row(c, "O15_time_summary", kind="tryptic", set="pair", pair="sage/prose")
        self.assertAlmostEqual(t["equal_weight"], T.gmean([r["wall_ratio_gmean"] for r in tryptic]), places=12)
        self.assertEqual(t["n_datasets"], len(tryptic))
        self.assertEqual(t["n_units"], sum(r["n_units"] for r in tryptic))
        three = row(c, "O15_time_summary", kind="tryptic", set="three", pair="sage/prose")
        self.assertLessEqual(three["n_units"], t["n_units"])
        names3 = {u.name for u in c.T3()}
        self.assertNotIn("iprg2015_r1", names3)
        self.assertEqual(number(c, "mem.tryptic.three.prose.max_gib").value, three["max_rss_gib_prose"])
        self.assertEqual(number(c, "mem.tryptic.three.sage.max_gib").value, three["max_rss_gib_comparator"])
        for key in ("time.tryptic.msfragger_prose.sage.total_h", "mem.electron.sage_prose.sage.max_gib",
                    "time.tryptic.three.ratio"):
            self.assertIsNone(number(c, key), key)  # per pair only its two engines; no ratio key over T3
        for key in ("time.tryptic.sage_prose.ratio", "time.tryptic.msfragger_prose.msfragger.total_h",
                    "mem.immuno.sage_prose.sage.max_gib", "time.immuno.msfragger_prose.ratio"):
            self.assertIsNotNone(number(c, key), key)
        self.assertEqual([lv for lv, _ in checks(c, "O15")], ["INFO"])


# ---------------------------------------------------------------- O16: T17
class TestO16(BaseBuild):
    def test_t17(self):
        r = row(self.ctx, "O16_batch", engine="prose", group="astral_250pg")
        self.assertEqual((r["batch_wall_med_s"], r["batch_wall_per_file_s"], r["sum_per_file_wall_s"]),
                         (285.0, 95.0, 330.0))
        self.assertAlmostEqual(r["ratio_wall"], 285 / 330, places=12)
        self.assertEqual((r["n_files"], r["in_B3"]), (3, True))
        _, _, tsv = self.table("O16_batch")
        line = [x for x in tsv if x["engine"] == "prose"][0]
        self.assertEqual((line["ratio_wall"], line["batch_wall_per_file_s"], line["in_B3"]),
                         ("0.863636", "95.00", "yes"))
        f = row(self.ctx, "O16_batch", engine="msfragger", group="astral_250pg")
        self.assertEqual(f["batch_wall_med_s"], 264.0)  # 1 search + 3 rescoring per repetition
        n = number(self.ctx, "batch.prose.median_ratio")
        self.assertAlmostEqual(n.value, 285 / 330, places=12)
        self.assertEqual(n.text, "0.864")
        self.assertEqual(len(self.ctx.results["O16_batch"]), 3)


# ---------------------------------------------------------------- O17: T18
class TestO17(BaseBuild):
    def test_t18(self):
        c = self.ctx
        for e in ("prose", "sage", "msfragger"):
            r = row(c, "O17_scaling", engine=e, machine=timing.SCALING_NODE, threads=16)
            self.assertAlmostEqual(r["speedup"], 12.8, places=9, msg=e)
            self.assertAlmostEqual(r["efficiency"], 0.8, places=9, msg=e)
            self.assertEqual(r["speedup_rel"], T.Missing("t1_exists"))
            r1 = row(c, "O17_scaling", engine=e, machine=timing.SCALING_NODE, threads=1)
            self.assertEqual((r1["speedup"], r1["efficiency"]), (1.0, 1.0))
        p = row(c, "O17_scaling", engine="prose", machine=timing.SCALING_NODE, threads=16)
        self.assertEqual(p["wall_med_s"], 125.0)  # repetition 0 of the top point is not used
        self.assertAlmostEqual(p["cores_used"], 2000 / 125, places=12)
        self.assertEqual(p["wall_lower_bound_s"], T.Missing("not_over_limit"))
        m = row(c, "O17_scaling", engine="msfragger", machine=timing.SCALING_NODE, threads=16)
        self.assertEqual((m["wall_med_s"], m["search_wall_med_s"], m["rescoring_wall_med_s"]), (200.0, 180.0, 20.0))
        self.assertEqual(len(c.results["O17_scaling"]), 18)  # 3 engines x (5 points + 1 workstation row)

    def test_workstation_row(self):
        w = row(self.ctx, "O17_scaling", engine="prose", machine=timing.ENGINE_NODE)
        self.assertEqual((w["threads"], w["state"], w["wall_med_s"]), (16, "ok", 61.0))  # per_file hfx_r1 (O15)
        self.assertEqual(w["speedup"], T.Missing("workstation_row"))
        self.assertNotIn("not 16", w["note"])
        self.assertIn("workstation comparison", w["note"])

    def test_keys(self):
        c = self.ctx
        self.assertAlmostEqual(number(c, "scaling.prose.speedup_t16").value, 12.8, places=9)
        self.assertEqual(number(c, "scaling.prose.speedup_t16").text, "12.8")
        self.assertAlmostEqual(number(c, "scaling.prose.efficiency_t16").value, 0.8, places=9)
        self.assertAlmostEqual(number(c, "scaling.prose.speedup_tmax").value, 12.8, places=9)
        self.assertAlmostEqual(number(c, "scaling.prose.wall_t1_h").value, 1600 / 3600, places=12)
        self.assertEqual(number(c, "scaling.prose.wall_t1_h").text, "0.444")
        self.assertAlmostEqual(number(c, "scaling.sage.wall_t16_min").value, 162.5 / 60, places=12)
        self.assertEqual(number(c, "scaling.msfragger.wall_t16_min").unit, "min")
        self.assertEqual(number(c, "scaling.prose.speedup_t16").source_side, "tuning")


# ---------------------------------------------------------------- O17: T19 (scaling over the limit, from S)
class TestO17OverLimit(TempDir):
    def build_overlimit(self):
        w = make_w(self.tmp, keep=lambda line: line.split("\t")[1] != "scaling")
        return build(w_options(w, out=os.path.join(self.tmp, "out"),
                               scaling_coverage=fx("coverage_overlimit_fx.tsv"),
                               scaling_timings=fx("timings_overlimit_fx.tsv")))

    def test_t19(self):
        c = self.build_overlimit()
        for e in ("prose", "msfragger"):
            def pt(n):
                return row(c, "O17_scaling", engine=e, machine=timing.SCALING_NODE, threads=n)
            self.assertEqual([r["threads"] for r in c.results["O17_scaling"]
                              if r["engine"] == e and r["machine"] == timing.SCALING_NODE], [1, 2, 4, 8, 16])
            t1 = pt(1)
            self.assertEqual(t1["state"], "not_run_over_limit")
            for col in ("wall_med_s", "wall_lower_bound_s", "speedup", "speedup_rel", "cpu_med_s"):
                self.assertIsInstance(t1[col], T.Missing, col)
            self.assertIn("not run", t1["note"])
            t2 = pt(2)
            self.assertEqual((t2["state"], t2["wall_lower_bound_s"]), ("over_limit", L))
            for col in ("wall_med_s", "speedup", "efficiency", "speedup_rel", "efficiency_rel", "cores_used"):
                self.assertIsInstance(t2[col], T.Missing, col)  # L is never read as a wall time
            self.assertIn("over the limit L = 86400 s", t2["note"])
            t4 = pt(4)
            self.assertEqual((t4["wall_med_s"], t4["speedup_rel"], t4["efficiency_rel"]), (412.0, 1.0, 1.0))
            self.assertEqual(t4["speedup"], T.Missing("no_t1"))
            self.assertIn("n0 = 4", t4["note"])
            t16 = pt(16)
            self.assertEqual(t16["wall_med_s"], 127.0)
            self.assertAlmostEqual(t16["speedup_rel"], 412 / 127, places=12)
            self.assertAlmostEqual(t16["efficiency_rel"], (412 / 127) / (16 / 4), places=12)
            self.assertIsInstance(number(c, f"scaling.{e}.speedup_t16").value, T.Missing)
            self.assertIsInstance(number(c, f"scaling.{e}.wall_t1_h").value, T.Missing)
            self.assertEqual(number(c, f"scaling.{e}.wall_t1_h").text, "NA")
            self.assertAlmostEqual(number(c, f"scaling.{e}.wall_t16_min").value, 127 / 60, places=12)
        self.assertEqual(rows(c, "O17_scaling", engine="sage", machine=timing.SCALING_NODE), [])
        note, _, _ = read_tsv(os.path.join(self.tmp, "out", "tables", "O17_scaling.tsv"))
        self.assertIn("scaling rows from S = ", note)
        self.assertIn("(--scaling-work)", note)
        o18 = [msg for lv, msg in checks(c, "O18") if lv == "WARN"]
        self.assertTrue(any("no versions.txt for the scaling node" in m for m in o18), o18)
        self.assertTrue(any("no machine file for the scaling node" in m for m in o18), o18)


# ---------------------------------------------------------------- O10: T22 (data part)
class TestO10(BaseBuild):
    def test_identical_and_ratios(self):
        c = self.ctx
        table = c.results["O10_low_memory"]
        self.assertEqual([r["sample"] for r in table[:3]], ["pxd058436_DN05", "pxd058436_DN13", "pxd019643_DN05"])
        for r in table[:3]:
            self.assertIs(r["identical"], True)
            self.assertEqual((r["psm_std"], r["pep_std"]), (r["psm_lm"], r["pep_lm"]))
        dn05 = table[0]
        self.assertEqual((dn05["psm_std"], dn05["wall_std"], dn05["wall_lm"]), (17600, 111.0, 82.0))
        self.assertAlmostEqual(dn05["wall_ratio"], 82 / 111, places=12)
        self.assertAlmostEqual(dn05["rss_ratio"], 1500000 / 3120000, places=12)
        s = table[3]
        self.assertEqual((s["group"], s["identical"]), ("summary", True))
        self.assertEqual(s["sample"], "median over 2 non-decision samples")
        self.assertAlmostEqual(s["wall_ratio"], (82 / 111 + 82 / 121) / 2, places=12)
        self.assertAlmostEqual(s["rss_ratio"], (1500000 / 3120000 + 1500000 / 3140000) / 2, places=12)
        n = number(c, "lowmem.identical_all")
        self.assertEqual((n.value, n.text), (True, "yes"))
        self.assertAlmostEqual(number(c, "lowmem.median_wall_ratio").value, s["wall_ratio"], places=12)
        self.assertEqual(number(c, "lowmem.median_rss_ratio").text, "0.479")
        _, cols, tsv = self.table("O10_low_memory")
        self.assertEqual(cols, timing.O10)
        self.assertEqual((tsv[0]["identical"], tsv[0]["wall_std"], tsv[3]["identical"]), ("yes", "111.00", "yes"))


class TestO10Different(TempDir):
    def test_different_counts(self):
        h = T.COUNTS_HEADER

        def edit(line):
            cells = line.rstrip("\r\n").split("\t")
            if cells[:4] == ["prose", "per_file_low_memory", "pxd019643_DN05", "pxd019643_td"] and cells[5] == "psm":
                cells[h.index("accepted")] = "18000"
                return "\t".join(cells) + "\n"
            return line
        counts = copy_with(fx("counts_fx.tsv"), os.path.join(self.tmp, "counts.tsv"), edit)
        c = build(options(counts=counts))
        r = row(c, "O10_low_memory", sample="pxd019643_DN05")
        self.assertEqual((r["psm_std"], r["psm_lm"], r["identical"]), (18700, 18000, False))
        self.assertIs(row(c, "O10_low_memory", sample="pxd058436_DN05")["identical"], True)
        self.assertIs(row(c, "O10_low_memory", group="summary")["identical"], False)
        n = number(c, "lowmem.identical_all")
        self.assertEqual((n.value, n.text), (False, "no"))

    def counts_part(self, ctx, flip):
        """ids.py's counts part (ctx.shared['O10_counts'] rows) of the base fixtures; flip: a sample marked not
        identical."""
        out = []
        for name in ("pxd058436_DN05", "pxd058436_DN13", "pxd019643_DN05"):
            u = ctx.unit(name)
            r = {"group": u.group, "class": u.cls, "grade": u.grade, "sample": name, "role": u.role, "note": ""}
            for level, short in (("psm", "psm"), ("peptide", "pep")):
                r[f"{short}_std"] = ctx.accepted("prose", u, level)
                r[f"{short}_lm"] = ctx.accepted("prose", u, level, benchmark="per_file_low_memory")
            r["identical"] = name != flip
            out.append(r)
        return out

    def test_counts_part_of_ids(self):
        c = T.load(options())
        c.shared["O10_counts"] = self.counts_part(c, flip="pxd019643_DN05")
        c.number("lowmem.identical_all", False, output="O10", protocol_ref="ids", source_side="heldout")
        timing.build(c)
        self.assertIs(row(c, "O10_low_memory", sample="pxd019643_DN05")["identical"], False)  # taken from ids.py
        self.assertIs(row(c, "O10_low_memory", group="summary")["identical"], False)
        self.assertEqual(number(c, "lowmem.identical_all").protocol_ref, "ids")  # the key stays ids.py's
        self.assertEqual([lv for lv, _ in checks(c, "O10")], ["INFO"])
        self.assertEqual(checks(c, "TIMING"), [])
        self.assertIn("counts part from ids.py", checks(c, "O10")[0][1])

    def test_counts_part_disagrees(self):
        c = T.load(options())
        c.shared["O10_counts"] = self.counts_part(c, flip="pxd058436_DN05")
        c.number("lowmem.identical_all", True, output="O10", protocol_ref="ids", source_side="heldout")
        timing.build(c)
        warns = [msg for lv, msg in checks(c, "O10") if lv == "WARN"]
        self.assertEqual(len(warns), 1)
        self.assertIn("lowmem.identical_all of ids.py is yes", warns[0])


# ---------------------------------------------------------------- O15b: T24
class TestO15b(TempDir):
    def setUp(self):
        super().setUp()
        self.w = make_w(self.tmp)
        out = os.path.join(self.w, "out")
        logs = (("prose", "pxd058436_DN05", "pxd058436_td", "timing_prose_all", "all"),
                ("sage", "hfx_r1", "hye_td", "timing_sage_all", "all"),
                ("msfragger", "hfx_r1", "hye_td", "timing_fragger_search", "search"))
        for engine, unit, db, src, name in logs:
            folder = os.path.join(out, engine, "per_file", unit, db)
            os.makedirs(folder)
            for r in (1, 2, 3):
                shutil.copy(fx(f"{src}.r{r}.log"), os.path.join(folder, f"{name}.r{r}.log"))
        shutil.copy(fx("timing_summary.yaml"),
                    os.path.join(out, "prose", "per_file", "pxd058436_DN05", "pxd058436_td", "summary.yaml"))
        # ups1_r1: the report of r2 lacks its 'Total time' line
        folder = os.path.join(out, "prose", "per_file", "ups1_r1", "hy_td")
        os.makedirs(folder)
        for r in (1, 2, 3):
            with open(fx(f"timing_prose_all.r{r}.log"), encoding="utf-8") as f:
                text = f.read()
            if r == 2:
                text = "".join(x for x in text.splitlines(True) if "Total time" not in x)
            with open(os.path.join(folder, f"all.r{r}.log"), "w", encoding="utf-8") as f:
                f.write(text)

    def read(self, name):
        with open(fx(name), encoding="utf-8") as f:
            return f.read()

    def test_parsers(self):
        p = [timing.parse_prose_log(self.read(f"timing_prose_all.r{r}.log")) for r in (1, 2, 3)]
        self.assertEqual(p[0], {"index": 4.5, "search": 50.0, "output": 5.0, "total": 60.0})
        self.assertEqual(p[1], {"index": 4.7, "search": 51.0, "output": 5.5, "total": 62.0})
        s = timing.parse_sage_log(self.read("timing_sage_all.r1.log"))  # timestamp prefix, padding, two chunks
        self.assertAlmostEqual(s["io"], 1.5, places=12)
        self.assertEqual((s["index"], s["search"], s["total"]), (2.1, 30.0, 36.0))
        f = timing.parse_fragger_log(self.read("timing_fragger_search.r1.log"))
        self.assertAlmostEqual(f["index"], 2.5, places=12)  # both slices
        self.assertAlmostEqual(f["calibration"], 30.0, places=12)  # 0.500 MIN
        y = timing.parse_prose_yaml(T.read_yaml(fx("timing_summary.yaml")))
        self.assertEqual(y, {"calibration": 7.5, "search": 42.0, "fdr": 5.0, "index": 4.6, "output": 5.2,
                             "total": 61.0})
        self.assertEqual(timing.parse_prose_log("[ProSE] Fragment:  offset 0.1\n"),
                         dict.fromkeys(("index", "search", "output", "total")))
        self.assertEqual(timing.parse_sage_log("nothing\n"), dict.fromkeys(("index", "io", "search", "total")))

    def test_rows(self):
        c = build(w_options(self.w))
        self.assertTrue(c.logs_available)

        def sec(engine, unit, stage, source):
            return row(c, "O15b_stage_times", engine=engine, unit=unit, stage=stage, source=source)

        log = "all.r<rep>.log"
        for stage, v in (("index", 4.6), ("search", 51.0), ("output", 5.2), ("total", 61.0)):
            r = sec("prose", "pxd058436_DN05", stage, log)
            self.assertAlmostEqual(r["seconds"], v, places=12, msg=stage)
            self.assertEqual((r["reps_used"], r["note"]), ("r1-r3", ""))
        for stage, v in (("calibration", 7.5), ("search", 42.0), ("fdr", 5.0), ("index", 4.6), ("output", 5.2),
                         ("total", 61.0)):
            r = sec("prose", "pxd058436_DN05", stage, "summary.yaml")
            self.assertAlmostEqual(r["seconds"], v, places=12, msg=stage)
            self.assertEqual(r["reps_used"], "r3")
        for stage, v in (("index", 2.2), ("io", 1.6), ("search", 31.0), ("total", 37.0)):
            self.assertAlmostEqual(sec("sage", "hfx_r1", stage, log)["seconds"], v, places=12, msg=stage)
        self.assertAlmostEqual(sec("msfragger", "hfx_r1", "index", "search.r<rep>.log")["seconds"], 2.5, places=12)
        self.assertAlmostEqual(sec("msfragger", "hfx_r1", "calibration", "search.r<rep>.log")["seconds"], 30.0,
                               places=9)
        self.assertEqual(sec("msfragger", "hfx_r1", "search", "timings.tsv")["seconds"], 90.0)
        self.assertEqual(sec("msfragger", "hfx_r1", "rescoring", "timings.tsv")["seconds"], 15.0)
        r = sec("prose", "velos_r1", "index", log)  # no logs in the folder
        self.assertEqual(r["seconds"], T.Missing("no_log"))
        self.assertIn("no all.r1.log", r["note"])
        self.assertEqual(sec("prose", "velos_r1", "total", "summary.yaml")["note"], "no summary.yaml")
        r = sec("prose", "ups1_r1", "total", log)
        self.assertEqual(r["seconds"], T.Missing("not_found"))
        self.assertEqual(r["note"], "line not found in r2")
        self.assertAlmostEqual(sec("prose", "ups1_r1", "index", log)["seconds"], 4.6, places=12)
        self.assertEqual(rows(c, "O15b_stage_times", engine="sage", unit="pxd058436_DN05"), [])  # failed_memory
        self.assertEqual(len(rows(c, "O15b_stage_times", engine="msfragger", unit="iprg2015_r1",
                                  source="timings.tsv")), 2)
        self.assertIn("timing no_timing", row(c, "O15b_stage_times", engine="msfragger", unit="iprg2015_r1",
                                              stage="search", source="timings.tsv")["note"])

    def test_skipped_without_logs(self):
        c = build(options())
        self.assertFalse(c.logs_available)
        self.assertNotIn("O15b_stage_times", c.results)


# ---------------------------------------------------------------- T31 stale timing
class TestStale(TempDir):
    def test_t31(self):
        w = make_w(self.tmp)
        folder = os.path.join(w, "out", "prose", "per_file", "velos_r1", "hy_td")
        os.makedirs(folder)
        with open(os.path.join(folder, "all.log"), "w", encoding="utf-8") as f:
            f.write("[ProSE] an untimed rerun\n")
        c = build(w_options(w))
        r = row(c, "O15_time_runs", engine="prose", unit="velos_r1")
        self.assertEqual(r["state"], "stale_timing")
        self.assertIsInstance(r["wall_med_s"], T.Missing)
        self.assertIsInstance(r["wall_r1"], T.Missing)  # a stale timing is not shown as measured
        self.assertEqual(r["n_reps"], 0)  # nor counted: its attempt belongs to an older search (SPEC 2.5)
        self.assertIn("all.log", r["note"])
        self.assertEqual(row(c, "O15_time_runs", engine="sage", unit="velos_r1")["state"], "ok")
        names = {u.name for u in c.T(("prose", "sage"))}
        self.assertNotIn("velos_r1", names)
        self.assertEqual(row(c, "O15_time_datasets", pair="sage/prose", group="velos")["n_units"], 0)


# ---------------------------------------------------------------- O18
class TestO18(BaseBuild):
    def test_versions(self):
        c = self.ctx
        v = c.results["O18_versions"]
        self.assertEqual([r["tool"] for r in v], ["prose", "fileconverter", "entrapmentevaluator", "sage",
                                                  "msfragger", "percolator"])
        self.assertEqual(row(c, "O18_versions", tool="prose")["version"], "3.7.0-pre-HEAD-2026-01-01, revision abc1234")
        self.assertEqual(row(c, "O18_versions", tool="msfragger")["version"], "4.4.1")
        self.assertEqual(number(c, "versions.sage").text, "0.14.6")
        self.assertEqual(number(c, "versions.percolator").value, "3.09.0")
        self.assertEqual({r["node"] for r in v}, {timing.ENGINE_NODE})

    def test_machines_and_cap(self):
        c = self.ctx
        summary = {r["item"]: r["value"] for r in rows(c, "O18_machines", node="fx", section="summary")}
        self.assertEqual(summary, {"host": "fixture-node", "role": "engine", "memory_cap": "--mem-gb 200",
                                   "ram_gib": "2.000", "cpus": "16", "cpu_model": "Fixture CPU 16-Core Processor",
                                   "threads_per_core": "1", "sockets": "16", "os": "Ubuntu 24.04.5 LTS",
                                   "kernel": "6.8.0-1-generic", "memory_max_bytes": "214748364800"})
        lines = [r["value"] for r in c.results["O18_machines"]]
        self.assertFalse(any(x.startswith("loop0") for x in lines))
        self.assertIn("Linux 6.8.0-1-generic #1 SMP Mon Jan 1 12:34:56 UTC 2026 x86_64", lines)  # ':' in a value
        self.assertEqual(rows(c, "O18_machines", section="CPU", item="Flags"), [])
        n = number(c, "cap.gib")
        self.assertEqual((n.value, n.text, n.unit), (200, "200", "GiB"))
        self.assertEqual([lv for lv, _ in checks(c, "O18")], ["INFO"])

    def test_missing_files_and_cap_mismatch(self):
        tmp = tempfile.mkdtemp(prefix="timing_test_")
        try:
            c = build(options(machines=(), versions=None))
            warns = [msg for lv, msg in checks(c, "O18") if lv == "WARN"]
            self.assertTrue(any("no machine file" in m for m in warns), warns)
            self.assertTrue(any("no versions.txt for the engine node" in m for m in warns), warns)
            self.assertEqual(c.results["O18_versions"], [])
            self.assertIsNone(number(c, "versions.prose"))
            self.assertEqual(number(c, "cap.gib").value, 200)
            p = os.path.join(tmp, "machine.txt")
            with open(fx("timing_machine_fx.txt"), encoding="utf-8") as f:
                text = f.read()
            with open(p, "w", encoding="utf-8") as f:
                f.write(text.replace("--mem-gb 200", "--mem-gb 100").replace("214748364800", "107374182400"))
            c = build(options(machines=(("small", p),)))
            warns = [msg for lv, msg in checks(c, "O18") if lv == "WARN"]
            self.assertTrue(any("--mem-gb 100" in m for m in warns), warns)
            self.assertTrue(any("memory.max 107374182400" in m for m in warns), warns)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------- layouts and --only
class TestLayouts(unittest.TestCase):
    def test_smoke(self):
        c = build(T.Options(runs=fx("runs_smoke_fx.tsv"), design="none", counts=fx("counts_smoke_fx.tsv"),
                            coverage=fx("coverage_smoke_fx.tsv"), timings=fx("timings_smoke_fx.tsv"),
                            references=None, mzml_counts=None))
        self.assertEqual(len(c.results["O15_time_runs"]), 9)
        self.assertEqual({r["kind"] for r in c.results["O15_time_summary"]}, {"other"})
        self.assertIsNotNone(number(c, "time.other.sage_prose.ratio"))
        self.assertEqual(len(c.results["O16_batch"]), 3)
        self.assertEqual(sum(1 for r in c.results["O17_scaling"] if r["machine"] == timing.ENGINE_NODE), 3)
        self.assertEqual(number(c, "scaling.prose.speedup_t16").value, T.Missing("not_in_grid"))
        self.assertEqual(c.results["O10_low_memory"], [])
        self.assertEqual(number(c, "lowmem.identical_all").value, T.Missing("empty"))

    def test_wnode_decision_only(self):
        c = build(options(counts=fx("counts_wnode_fx.tsv"), coverage=fx("coverage_wnode_fx.tsv"),
                          timings=fx("timings_wnode_fx.tsv")))
        self.assertEqual(len(c.results["O15_time_runs"]), 68)
        self.assertEqual(c.B3(), [])
        self.assertIsInstance(number(c, "batch.prose.median_ratio").value, T.Missing)
        for r in c.results["O15_time_datasets"]:
            self.assertEqual(r["n_units"], 0)
        self.assertIsInstance(number(c, "time.tryptic.sage_prose.ratio").value, T.Missing)

    def test_only_scaling(self):
        c = build(options(only=("scaling",)))
        self.assertEqual(set(c.results), {"O17_scaling", "O18_versions", "O18_machines"})
        self.assertFalse(any(n.key.startswith(("time.", "mem.", "batch.", "lowmem.")) for n in c.numbers))

    def test_only_other_module(self):
        c = build(options(only=("ids",)))
        self.assertEqual(c.results, {})
        self.assertEqual(c.numbers, [])


if __name__ == "__main__":
    unittest.main()
