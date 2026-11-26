"""Tests of the FDP module (SPEC 6): T10, T11, T29, T32, plus O11 tables and keys, O12, O13 (table, keys, stale and
excluded qgrid rows), O26, --only, and the W_node and smoke layouts. Fixtures: the base fixtures of the loader tests
and fixtures/fdp_counts_qgrid_fx.tsv (made-up grid for O13)."""
import hashlib
import math
import os
import shutil
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock

sys.dont_write_bytecode = True

from summaries import fdp, tables as T  # noqa: E402

FX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")


def fx(name):
    return os.path.join(FX, name)


def options(**kw):
    """Options of the base fixture W (runs_fx + counts/coverage/timings_fx), nothing written."""
    o = dict(runs=fx("runs_fx.tsv"), counts=fx("counts_fx.tsv"), coverage=fx("coverage_fx.tsv"),
             timings=fx("timings_fx.tsv"), versions=None, params_dir=fx("params_fx"), references=None,
             mzml_counts=None)
    o.update(kw)
    return T.Options(**o)


def load(**kw):
    return T.load(options(**kw))


def rewrite(src, dst, edit=None, keep=None, extra=()):
    """A copy of a fixture TSV: keep(cells) filters data rows, edit(cells) -> cells rewrites them, extra rows added."""
    with open(src, encoding="utf-8", newline="") as f:
        lines = f.read().splitlines()
    out = [lines[0]]
    for line in lines[1:]:
        cells = line.split("\t")
        if keep and not keep(cells):
            continue
        out.append("\t".join(edit(cells) if edit else cells))
    out += ["\t".join(x) for x in extra]
    with open(dst, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(out) + "\n")
    return dst


def rows_of(ctx, table, **match):
    return [r for r in ctx.results[table] if all(r[k] == v for k, v in match.items())]


def one(ctx, table, **match):
    rs = rows_of(ctx, table, **match)
    if len(rs) != 1:
        raise AssertionError(f"{table} {match}: {len(rs)} rows")
    return rs[0]


class TempDir(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="summaries_fdp_test_")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def path(self, name):
        return os.path.join(self.tmp, name)

    def without_prose_velos_s3(self):
        """Base fixtures with ProSE's velos_r1 s3 search failed (coverage failed, no counts rows)."""
        cov = rewrite(fx("coverage_fx.tsv"), self.path("coverage.tsv"),
                      edit=lambda c: c[:4] + ["failed stage all repetition 1 exit 1", "no"]
                      if c[:4] == ["prose", "per_file", "velos_r1", "hy_entrap_s3_td"] else c)
        cnt = rewrite(fx("counts_fx.tsv"), self.path("counts.tsv"),
                      keep=lambda c: c[:4] != ["prose", "per_file", "velos_r1", "hy_entrap_s3_td"])
        return load(coverage=cov, counts=cnt)


_BASE = None


def base():
    """The base fixture context with fdp.build run once (no output folder)."""
    global _BASE
    if _BASE is None:
        _BASE = load()
        fdp.build(_BASE)
    return _BASE


# ---------------------------------------------------------------- T10 FDP mean, SD, missing realisation, N = 0
class TestT10(TempDir):
    def test_own_and_shared(self):
        r = fdp.fdp_as_o11(base(), "prose", "per_file", "velos_r1", "psm", "shuffled")
        self.assertEqual(r.n_own, 3)
        self.assertAlmostEqual(r.mean_own, 0.012, places=12)  # 0.010/0.012/0.014
        self.assertAlmostEqual(r.sd_own, 0.002, places=12)  # n - 1
        self.assertAlmostEqual(r.min_own, 0.010, places=12)
        self.assertAlmostEqual(r.max_own, 0.014, places=12)
        # Sage's s3 search failed: the shared values drop s3 for every engine (OPEN Q15)
        self.assertEqual(r.shared, ("hy_entrap_s1_td", "hy_entrap_s2_td"))
        self.assertAlmostEqual(r.mean_shared, 0.011, places=12)
        self.assertAlmostEqual(r.sd_shared, 0.0014142, places=7)
        self.assertIn("not shared: s3", r.note)
        s = fdp.fdp_as_o11(base(), "sage", "per_file", "velos_r1", "psm", "shuffled")
        self.assertEqual(s.n_own, 2)
        self.assertEqual(s.values["hy_entrap_s3_td"], T.Missing("failed"))
        self.assertTrue(s.note.startswith("incomplete"))
        self.assertIn("s3 failed", s.note)

    def test_without_s3(self):
        c = self.without_prose_velos_s3()
        r = fdp.fdp_as_o11(c, "prose", "per_file", "velos_r1", "psm", "shuffled")
        self.assertEqual(r.n_own, 2)
        self.assertAlmostEqual(r.mean_own, 0.011, places=12)
        self.assertAlmostEqual(r.sd_own, 0.0014142, places=7)
        self.assertTrue(r.note.startswith("incomplete"))
        fdp.build(c)
        row = one(c, "O11_fdp_runs", engine="prose", unit="velos_r1", level="psm", design="shuffled")
        self.assertEqual((row["n_own"], row["n_shared"]), (2, 2))
        self.assertIn("incomplete", row["note"])
        # the failed search keeps a results row with NA values and its status
        res = one(c, "O11_fdp_results", engine="prose", unit="velos_r1", database="hy_entrap_s3_td", level="psm")
        self.assertEqual(res["combined_fdp"], T.Missing("failed"))
        self.assertTrue(res["status"].startswith("failed"))
        self.assertEqual(res["note"], "failed")
        # INFO O11 names the engine-runs with own shuffled n < 3
        info = [m for lv, cid, m in c.report.lines if lv == "INFO" and cid == "O11" and "own shuffled" in m]
        self.assertEqual(len(info), 1)
        self.assertIn("engine-runs with own shuffled n < 3: ", info[0])
        self.assertIn("prose:velos_r1", info[0])

    def test_short_runs_list_stops_after_ten(self):
        """The INFO O11 list of engine-runs with own shuffled n < 3 stops after 10 items and says how many it leaves
        out, as the check report's lists do (tables.list_text)."""
        runs = [SimpleNamespace(engine="sage", unit=SimpleNamespace(name=f"u{i:02d}"), design="shuffled",
                                stems=("s1", "s2", "s3"), n_own=2) for i in range(12)]
        c = load()
        with mock.patch.object(fdp, "o11_runs", return_value=runs):
            fdp.build(c)
        info = [m for lv, cid, m in c.report.lines if lv == "INFO" and cid == "O11" and "own shuffled" in m]
        self.assertEqual(len(info), 1)
        self.assertTrue(info[0].endswith("; 12 engine-runs with own shuffled n < 3: sage:u00, sage:u01, sage:u02, "
                                         "sage:u03, sage:u04, sage:u05, sage:u06, sage:u07, sage:u08, sage:u09, ... "
                                         "(+2 more)"), info[0])

    def test_none_accepted(self):
        c = base()
        # Sage accepts 0 on pxd011695_HCD_r1 (T4): EE's raw 0 only in O11_fdp_results
        res = one(c, "O11_fdp_results", engine="sage", unit="pxd011695_HCD_r1",
                  database="pxd011695_mouse_entrap_s1_td", level="psm")
        self.assertEqual(res["combined_fdp"], 0.0)
        self.assertEqual(res["n_accepted_entrap_search"], 0)
        self.assertEqual(res["combined_recomputed"], T.Missing("none_accepted"))
        self.assertEqual(res["note"], "none_accepted")
        r = fdp.fdp_as_o11(c, "sage", "per_file", "pxd011695_HCD_r1", "psm", "shuffled")
        self.assertEqual(r.n_own, 0)
        self.assertEqual(r.mean_own, T.Missing("none_accepted"))
        self.assertEqual(r.max_own, T.Missing("none_accepted"))
        # the unit leaves F for every engine: ProSE's run has no shared value
        p = fdp.fdp_as_o11(c, "prose", "per_file", "pxd011695_HCD_r1", "psm", "shuffled")
        self.assertEqual(p.n_own, 3)
        self.assertEqual((p.n_shared, p.mean_shared), (0, T.Missing("not_shared")))
        self.assertFalse(p.in_f)
        ds = one(c, "O11_fdp_datasets", engine="prose", group="pxd011695_HCD", level="psm", design="shuffled")
        self.assertEqual((ds["n_units"], ds["n_runs"]), (1, 0))
        self.assertEqual(ds["max_run_mean"], T.Missing("empty"))
        self.assertIn("sage s1 zero", ds["note"])

    def test_dataset_and_keys(self):
        c = base()
        ds = one(c, "O11_fdp_datasets", engine="prose", group="velos", level="psm", design="shuffled")
        self.assertEqual((ds["n_units"], ds["n_runs"]), (1, 1))
        self.assertAlmostEqual(ds["mean_of_run_means"], 0.011, places=12)
        self.assertAlmostEqual(ds["max_run_mean"], 0.011, places=12)
        self.assertEqual(ds["n_runs_mean_above_1pct"], 1)
        keys = {n.key: n for n in c.numbers}
        self.assertIn("fdp.psm.prose.max_run_mean", keys)
        self.assertEqual(keys["fdp.psm.prose.max_run_mean"].unit, "%")
        self.assertEqual(keys["fdp.peptide.msfragger.shuffled.n_runs_mean_above_1pct"].output, "O11")
        self.assertEqual(keys["fdp.psm.prose.arath.n_runs"].value, 3)  # hfx, eclipse_tmtpro, astral
        self.assertEqual(keys["fdp.psm.prose.arath.n_runs"].source_side, "tuning")
        # decision units are in no summary: astral250pg_A2 (decision) is not counted in the astral_250pg dataset
        ds = one(c, "O11_fdp_datasets", engine="prose", group="astral_250pg", level="psm", design="shuffled")
        self.assertEqual((ds["n_units"], ds["n_runs"]), (2, 2))
        # ... but keeps its per-run row with note decision
        row = one(c, "O11_fdp_runs", engine="prose", unit="astral250pg_A2", level="psm", design="shuffled")
        self.assertTrue(row["note"].startswith("decision"))
        self.assertIsInstance(row["mean_shared"], float)
        self.assertFalse(fdp.run_of(c, "prose", "astral250pg_A2", "psm", "shuffled").in_f)
        self.assertEqual(fdp.run_of(c, "prose", "astral250pg_A2", "psm", "shuffled").run_mean,
                         T.Missing("decision"))
        # main design: velos natural, ups1 natural, hfx shuffled
        self.assertEqual(fdp.main_design(c.unit("velos_r1")), "natural")
        self.assertEqual(fdp.main_design(c.unit("hfx_r1")), "shuffled")
        self.assertIsNone(fdp.main_design(c.unit("pxd058436_DN05")))

    def test_results_rows(self):
        c = base()
        rows = c.results["O11_fdp_results"]
        # 58 entrapment databases x 3 engines - Sage on the 3 of the bycz ETciD unit = 171 searches, 2 levels
        self.assertEqual(len(rows), 342)
        self.assertFalse(rows_of(c, "O11_fdp_results", engine="sage", unit="pxd011695_ETciD_r1"))
        r = one(c, "O11_fdp_results", engine="prose", unit="velos_r1", database="hy_entrap_s1_td", level="peptide")
        self.assertEqual((r["design"], r["realisation"], r["n_accepted_entrap_search"], r["n_entrapment_hits"]),
                         ("shuffled", 1, 500, 2))
        self.assertAlmostEqual(r["combined_recomputed"], 0.008, places=12)
        self.assertEqual(r["paired_fdp"], 0.00784)
        self.assertEqual(one(c, "O11_fdp_results", engine="prose", unit="velos_r1", database="hy_velos_natural_td",
                             level="psm")["realisation"], "-")
        # run rows: (engine, unit, level, design) that the engine ran
        runs = c.results["O11_fdp_runs"]
        self.assertFalse([r for r in runs if r["engine"] == "sage" and r["group"] == "pxd011695_ETciD"])
        self.assertFalse([r for r in runs if r["kind"] == "immuno"])

    def test_reuse_for_arms(self):
        """The API for O19 (calib.py): FDP of an arm over the realisations counted in both the arm and the main arm
        of the same engine (the fixture's calibration arms were searched on td and s1 of hfx_r1)."""
        c = base()
        both = [("msfragger", "per_file"), ("msfragger", "per_file_cal1")]
        arm = fdp.fdp_as_o11(c, "msfragger", "per_file_cal1", "hfx_r1", "psm", "shuffled", shared_with=both)
        main = fdp.fdp_as_o11(c, "msfragger", "per_file", "hfx_r1", "psm", "shuffled", shared_with=both)
        self.assertEqual(arm.shared, ("hye_entrap_s1_td",))
        self.assertEqual(main.shared, ("hye_entrap_s1_td",))
        self.assertEqual(main.mean_shared, c.count_row("msfragger", "hfx_r1", "psm", db="hye_entrap_s1_td")
                         .combined_fdp)  # MSFragger's per_file s1 value
        self.assertEqual(arm.n_own, 1)
        self.assertIn("s2 no_coverage", arm.note)  # s2 and s3 were not searched in the arm
        # restricting the databases instead
        r = fdp.fdp_as_o11(c, "prose", "per_file", "hfx_r1", "psm", "shuffled", stems=["hye_entrap_s1_td"])
        self.assertEqual((r.stems, r.n_own), (("hye_entrap_s1_td",), 1))


# ---------------------------------------------------------------- T11 single database
class TestT11(unittest.TestCase):
    def test_single_database(self):
        c = base()
        value = c.count_row("prose", "ups1_r1", "psm", db="hy_velos_natural_td").combined_fdp
        row = one(c, "O11_fdp_runs", engine="prose", unit="ups1_r1", level="psm", design="natural")
        self.assertEqual(row["natural"], value)
        self.assertIsNone(row["sd_own"])  # no SD (OPEN Q16)
        self.assertIsNone(row["mean_own"])
        self.assertEqual((row["n_own"], row["n_shared"]), (1, 1))
        r = fdp.fdp_as_o11(c, "prose", "per_file", "ups1_r1", "psm")  # main design: natural
        self.assertEqual(r.design, "natural")
        self.assertEqual(r.value, value)
        self.assertEqual(r.sd_own, T.Missing("n<2"))
        self.assertFalse(rows_of(c, "O11_fdp_runs", unit="ups1_r1", design="shuffled"))
        # velos has both: natural (main) and s1-s3 (check), DS:393-394
        self.assertEqual({r["design"] for r in rows_of(c, "O11_fdp_runs", unit="velos_r1", engine="prose")},
                         {"shuffled", "natural"})


# ---------------------------------------------------------------- T29 C8 tolerance
class TestT29(unittest.TestCase):
    def test_tolerance(self):
        self.assertEqual(fdp.h(0), 0.0)
        self.assertAlmostEqual(fdp.h(0.01), 5e-6, places=18)
        self.assertAlmostEqual(fdp.h(1.0), 5e-4, places=15)
        self.assertAlmostEqual(fdp.h(0.008472), 5e-7, places=18)
        tol = fdp.c8_tolerance(0.01, 1.0, 0.005)
        self.assertAlmostEqual(tol, 7.5e-6 + 1e-12, places=18)
        self.assertLessEqual(abs(0.01 - 0.0099926), tol)  # PASS
        self.assertGreater(abs(0.01 - 0.0099926), 6e-6)  # v1's 6e-6 would FAIL

    def test_rows(self):
        row = SimpleNamespace(accepted=8206, entrapment=41, te_ratio=1.0, combined_fdp=0.01, lower_bound_fdp=0.004996)
        self.assertAlmostEqual(row.entrapment / row.accepted * 2, 0.0099926, places=6)
        self.assertTrue(fdp.c8_combined_ok(row))
        self.assertTrue(fdp.c8_lower_ok(row))
        self.assertFalse(fdp.c8_combined_ok(SimpleNamespace(accepted=8206, entrapment=41, te_ratio=1.0,
                                                            combined_fdp=0.01001)))
        zero = SimpleNamespace(accepted=0, entrapment=0, te_ratio=1.0, combined_fdp=0.0, lower_bound_fdp=0.0)
        self.assertTrue(fdp.c8_combined_ok(zero) and fdp.c8_lower_ok(zero))
        self.assertEqual(fdp.recomputed_combined(0, 0, 1.0), T.Missing("none_accepted"))
        # the T10 rows of the fixture agree
        for db in ("hy_entrap_s1_td", "hy_entrap_s2_td", "hy_entrap_s3_td"):
            self.assertTrue(fdp.c8_combined_ok(base().count_row("prose", "velos_r1", "psm", db=db)))


# ---------------------------------------------------------------- T32 and O13 matched FDP
def gp(q, n, ne, te=1.0):
    return fdp.GridPoint(q, n, ne, te, 0)


class TestT32(TempDir):
    def test_match_grid(self):
        # FDP 0.008, 0.011, 0.009, 0.012
        pts = [gp(0.002, 500, 2), gp(0.004, 2000, 11), gp(0.006, 4000, 18), gp(0.008, 5000, 30)]
        self.assertEqual([round(fdp.grid_fdp(p), 12) for p in pts], [0.008, 0.011, 0.009, 0.012])
        m = fdp.match_grid(list(reversed(pts)))  # file order does not matter
        self.assertEqual((m.q_match, m.n_match, m.monotone_ok, m.n_grid), (0.006, 4000, False, 4))
        self.assertAlmostEqual(m.fdp_match, 0.009, places=12)
        m = fdp.match_grid([gp(0.005, 1000, 5), gp(0.01, 1000, 5)])  # exactly 1.0% qualifies
        self.assertEqual((m.q_match, m.monotone_ok), (0.01, True))
        m = fdp.match_grid([gp(0.005, 1000, 6)])
        self.assertEqual(m.q_match, T.Missing("no_match"))
        m = fdp.match_grid([gp(0.0005, 0, 0), gp(0.001, 100, 1)])  # N = 0: EE's 0 qualifies with count 0
        self.assertEqual((m.q_match, m.n_match), (0.0005, 0))

    def ctx_with_grid(self, grid=None, **kw):
        c = load(**kw)
        fdp.o13(c, path=grid or fx("fdp_counts_qgrid_fx.tsv"))
        return c

    def test_o13_tables(self):
        c = self.ctx_with_grid()
        s = one(c, "O13_matched_fdp_searches", engine="prose", unit="lumos_tmt_r1", level="psm")
        self.assertEqual((s["q_match"], s["n_entrap_at_match"], s["monotone_ok"], s["n_grid"]), (0.006, 4000, False, 4))
        self.assertEqual(s["n_entrap_q01"], c.accepted("prose", "lumos_tmt_r1", "psm", db="hy_entrap_s1_td"))
        self.assertEqual(s["note"], "")
        s = one(c, "O13_matched_fdp_searches", engine="msfragger", unit="velos_r1", database="hy_entrap_s1_td")
        self.assertEqual((s["q_match"], s["n_entrap_at_match"], s["monotone_ok"]), (0.015, 10500, True))
        r = one(c, "O13_matched_fdp", pair="prose_msfragger", unit="velos_r1", level="psm", design="shuffled")
        self.assertEqual(r["n_realisations"], 2)  # Sage's s3 failed
        self.assertEqual((r["n_entrap_prose_matched"], r["n_entrap_comparator_matched"]), (850, 10200))
        self.assertAlmostEqual(r["ratio_matched"], 850 / 10200, places=12)
        self.assertAlmostEqual(r["ratio_q01"], 1000 / 9900, places=12)
        self.assertAlmostEqual(r["ratio_plain"], 1.1, places=12)
        self.assertIs(r["monotone_ok"], True)
        r = one(c, "O13_matched_fdp", pair="prose_sage", unit="velos_r1", level="psm", design="shuffled")
        self.assertEqual(r["n_entrap_comparator_matched"], 9602.5)
        r = one(c, "O13_matched_fdp", pair="prose_msfragger", unit="velos_r1", level="psm", design="natural")
        self.assertEqual(r["n_realisations"], 1)
        self.assertAlmostEqual(r["ratio_matched"], 10890 / 10400, places=12)
        # lumos_tmt_r1 has a grid for ProSE only: no shared matched realisation
        r = one(c, "O13_matched_fdp", pair="prose_msfragger", unit="lumos_tmt_r1", level="psm", design="shuffled")
        self.assertEqual(r["n_realisations"], 0)
        self.assertEqual(r["ratio_matched"], T.Missing("empty"))
        self.assertIn("no shared matched realisation", r["note"])
        keys = {n.key: n for n in c.numbers}
        k = keys["fdp.matched.tuning.psm.msfragger.lead_matched"]  # velos at its main design (natural)
        self.assertAlmostEqual(k.value, 100 * (10890 / 10400 - 1), places=9)
        self.assertEqual((k.text, k.main_text_allowed, k.source_side), ("4.7", "no", "tuning"))
        self.assertEqual(keys["fdp.matched.tuning.psm.msfragger.n_runs"].value, 1)
        self.assertEqual(keys["fdp.matched.heldout.psm.sage.lead_q01"].value, T.Missing("empty"))
        self.assertEqual(keys["fdp.matched.heldout.psm.sage.lead_q01"].main_text_allowed, "yes")

    def test_o13_skipped_without_grid(self):
        c = load()
        self.assertIsNone(fdp.o13(c, path=self.path("counts_qgrid.tsv")))
        self.assertNotIn("O13_matched_fdp", c.results)
        self.assertTrue(any(cid == "O13" and lv == "INFO" for lv, cid, _ in c.report.lines))

    def test_o13_stale_and_excluded(self):
        w = self.path("W")
        os.makedirs(w)
        extra = [["prose", "per_file_cal_off", "hfx_r1", "hye_entrap_s1_td", "hfx_r1.count.idXML", "psm", "all",
                  "0.01", "10", "0", "0", "0", "NA", "NA", "NA", "1"],
                 ["prose", "per_file", "velos_r1", "hy_td", "velos_r1.count.idXML", "psm", "all", "0.01", "10", "0",
                  "0", "0", "NA", "NA", "NA", "1"],
                 ["prose", "per_file", "velos_r1", "hye_entrap_s1_td", "velos_r1.count.idXML", "psm", "all", "0.01",
                  "10", "0", "0", "0", "NA", "NA", "NA", "1"]]
        rewrite(fx("fdp_counts_qgrid_fx.tsv"), os.path.join(w, "counts_qgrid.tsv"), extra=extra)
        # W/out with the count file of prose velos_r1 s1 and a count_qgrid.sha256 of another file: stale
        folder = os.path.join(w, "out", "prose", "per_file", "velos_r1", "hy_entrap_s1_td")
        os.makedirs(folder)
        with open(os.path.join(folder, "velos_r1.count.idXML"), "w") as f:
            f.write("<idXML/>\n")
        with open(os.path.join(folder, "count_qgrid.sha256"), "w") as f:
            f.write(hashlib.sha256(b"an older count file").hexdigest() + "  velos_r1.count.idXML\n")
        # s2: matching SHA256: ok
        folder2 = os.path.join(w, "out", "prose", "per_file", "velos_r1", "hy_entrap_s2_td")
        os.makedirs(folder2)
        with open(os.path.join(folder2, "velos_r1.count.idXML"), "wb") as f:
            f.write(b"<idXML s2/>\n")
        with open(os.path.join(folder2, "count_qgrid.sha256"), "w") as f:
            f.write(hashlib.sha256(b"<idXML s2/>\n").hexdigest() + "  velos_r1.count.idXML\n")
        c = load(work=w)
        self.assertTrue(c.logs_available)
        fdp.o13(c)
        s1 = one(c, "O13_matched_fdp_searches", engine="prose", unit="velos_r1", database="hy_entrap_s1_td")
        self.assertEqual((s1["q_match"], s1["note"]), (T.Missing("stale_qgrid"), "stale_qgrid"))
        s2 = one(c, "O13_matched_fdp_searches", engine="prose", unit="velos_r1", database="hy_entrap_s2_td")
        self.assertEqual(s2["q_match"], 0.005)
        r = one(c, "O13_matched_fdp", pair="prose_msfragger", unit="velos_r1", level="psm", design="shuffled")
        self.assertEqual(r["n_realisations"], 1)  # s1 dropped for every engine
        lines = [(lv, msg) for lv, cid, msg in c.report.lines if cid == "O13"]
        self.assertTrue(any(lv == "WARN" and "stale" in msg for lv, msg in lines))
        self.assertTrue(any(lv == "WARN" and "outside the design" in msg for lv, msg in lines))
        self.assertTrue(any(lv == "INFO" and "arm 1" in msg and "td 1" in msg and "outside_design 1" in msg
                            for lv, msg in lines))

    def test_o13_qgrid_file_not_read(self):
        """A count_qgrid.sha256 or a count file that cannot be read (a folder of that name stands in for an unreadable
        file): fdp does not raise; the search is unverified (its q_match is kept, as without the files), its rows
        note '<file> not read: <error>', and a WARN O13 (not strict) names the file."""
        w = self.path("W")
        os.makedirs(w)
        shutil.copy(fx("fdp_counts_qgrid_fx.tsv"), os.path.join(w, "counts_qgrid.tsv"))
        out = os.path.join(w, "out", "prose", "per_file", "velos_r1")
        os.makedirs(os.path.join(out, "hy_entrap_s1_td", "count_qgrid.sha256"))
        with open(os.path.join(out, "hy_entrap_s1_td", "velos_r1.count.idXML"), "w") as f:
            f.write("<idXML/>\n")
        os.makedirs(os.path.join(out, "hy_entrap_s2_td", "velos_r1.count.idXML"))
        with open(os.path.join(out, "hy_entrap_s2_td", "count_qgrid.sha256"), "w") as f:
            f.write(hashlib.sha256(b"<idXML s2/>\n").hexdigest() + "  velos_r1.count.idXML\n")
        c = load(work=w, strict=True)
        u = c.unit_by_name["velos_r1"]
        lost = []
        self.assertEqual(fdp.qgrid_state(c, "prose", u, "hy_entrap_s1_td", lost), "unverified")
        self.assertEqual(lost, [("prose/per_file/velos_r1/hy_entrap_s1_td/count_qgrid.sha256",
                                 "count_qgrid.sha256 not read: IsADirectoryError: Is a directory")])
        fdp.o13(c)
        s1 = one(c, "O13_matched_fdp_searches", engine="prose", unit="velos_r1", database="hy_entrap_s1_td")
        self.assertEqual(s1["note"], "count_qgrid.sha256 not read: IsADirectoryError: Is a directory")
        self.assertFalse(isinstance(s1["q_match"], T.Missing))
        s2 = one(c, "O13_matched_fdp_searches", engine="prose", unit="velos_r1", database="hy_entrap_s2_td")
        self.assertEqual((s2["q_match"], s2["note"]),
                         (0.005, "velos_r1.count.idXML not read: IsADirectoryError: Is a directory"))
        warn = [(lv, msg) for lv, cid, msg in c.report.lines if cid == "O13" and "not read" in msg]
        self.assertEqual(warn, [("WARN", "2 qgrid file(s) not read (the search counts as unverified, and its rows "
                                         "note '<file> not read: <error>'): prose/per_file/velos_r1/hy_entrap_s1_td/"
                                         "count_qgrid.sha256, prose/per_file/velos_r1/hy_entrap_s2_td/"
                                         "velos_r1.count.idXML")])

    def test_o13_stops(self):
        dup = [["prose", "per_file", "lumos_tmt_r1", "hy_entrap_s1_td", "lumos_tmt_r1.count.idXML", "psm", "all",
                "0.002", "500", "2", "0.004", "0.008", "NA", "NA", "NA", "1"]]
        p = rewrite(fx("fdp_counts_qgrid_fx.tsv"), self.path("dup.tsv"), extra=dup)
        with self.assertRaises(T.ValidationStop) as cm:
            fdp.o13(load(), path=p)
        self.assertIn("q_value", str(cm.exception))
        p = rewrite(fx("fdp_counts_qgrid_fx.tsv"), self.path("level.tsv"),
                    edit=lambda c: c[:5] + ["protein"] + c[6:] if c[2] == "lumos_tmt_r1" else c)
        with self.assertRaises(T.ValidationStop) as cm:
            fdp.o13(load(), path=p)
        self.assertIn("column level", str(cm.exception))


# ---------------------------------------------------------------- O12 Arabidopsis reference
class TestO12(TempDir):
    def test_arath(self):
        c = base()
        rows = c.results["O12_fdp_arath"]
        self.assertEqual(len(rows), 3 * 3 * 2)  # hfx_r1, eclipse_tmtpro_r1, astral_r1; 3 engines; 2 levels
        r = one(c, "O12_fdp_arath", engine="sage", unit="hfx_r1", level="psm")
        arath = c.count_row("sage", "hfx_r1", "psm", db="hye_arath_td").combined_fdp
        self.assertEqual(r["arath"], arath)
        shuffled = [c.count_row("sage", "hfx_r1", "psm", db=f"hye_entrap_s{i}_td").combined_fdp for i in (1, 2, 3)]
        mean = math.fsum(shuffled) / 3
        self.assertAlmostEqual(r["shuffled_mean_shared"], mean, places=12)
        self.assertEqual(r["shuffled_n_shared"], 3)
        self.assertAlmostEqual(r["difference_pp"], 100 * (arath - mean), places=9)
        self.assertIs(r["in_shared_set"], True)
        self.assertEqual((r["class"], r["grade"], r["group"]), ("OT", "-", "hfx"))

    def test_arath_not_shared(self):
        cov = rewrite(fx("coverage_fx.tsv"), self.path("coverage.tsv"),
                      edit=lambda c: c[:4] + ["failed stage all repetition 1 exit 1", "no"]
                      if c[:4] == ["sage", "per_file", "hfx_r1", "hye_arath_td"] else c)
        cnt = rewrite(fx("counts_fx.tsv"), self.path("counts.tsv"),
                      keep=lambda c: c[:4] != ["sage", "per_file", "hfx_r1", "hye_arath_td"])
        c = load(coverage=cov, counts=cnt)
        fdp.o12(c)
        for e in ("prose", "sage", "msfragger"):
            self.assertIs(one(c, "O12_fdp_arath", engine=e, unit="hfx_r1", level="psm")["in_shared_set"], False)
        r = one(c, "O12_fdp_arath", engine="sage", unit="hfx_r1", level="psm")
        self.assertEqual((r["arath"], r["difference_pp"]), (T.Missing("failed"), T.Missing("failed")))
        self.assertIs(one(c, "O12_fdp_arath", engine="sage", unit="astral_r1", level="psm")["in_shared_set"], True)


# ---------------------------------------------------------------- O26 pairings
class TestO26(unittest.TestCase):
    def test_pairings(self):
        c = base()
        rows = c.results["O26_pairings"]
        # per engine and level: S1 astral_s1_r1 + astral_r1, S2 ultra2_s2_r1 + ultra2_hye_r1, 250 pg A2/B1/B3 +
        # astral_r1
        self.assertEqual(len(rows), 8 * 3 * 2)
        r = one(c, "O26_pairings", pairing="set_S1", engine="prose", level="psm", unit="astral_s1_r1")
        self.assertEqual((r["design"], r["n_own"], r["counterpart"], r["grade"]), ("natural", 1, "-", "C"))
        self.assertEqual(r["sd_own"], T.Missing("n<2"))
        self.assertIsInstance(r["accepted_td"], int)
        r = one(c, "O26_pairings", pairing="set_S1", engine="prose", level="psm", unit="astral_r1")
        self.assertEqual((r["design"], r["kind"], r["n_shared"]), ("shuffled", "tuning", 3))
        r = one(c, "O26_pairings", pairing="astral_250pg", engine="sage", level="peptide", unit="astral250pg_A2")
        self.assertEqual(r["role"], "decision")
        self.assertTrue(r["note"].startswith("decision"))
        self.assertEqual([x["unit"] for x in rows_of(c, "O26_pairings", pairing="set_S2", engine="msfragger",
                                                      level="psm")], ["ultra2_s2_r1", "ultra2_hye_r1"])

    def test_counterpart(self):
        units = {n: SimpleNamespace(name=n, group=g) for n, g in
                 (("astral250pg_A2", "astral_250pg"), ("astral_A2", "astral"), ("astral_B1", "astral"))}
        ctx = SimpleNamespace(unit_by_name=units)
        self.assertEqual(fdp.counterpart(ctx, "astral_250pg", units["astral250pg_A2"]), "astral_A2")
        self.assertEqual(fdp.counterpart(ctx, "astral_250pg", units["astral_A2"]), "astral250pg_A2")
        self.assertEqual(fdp.counterpart(ctx, "astral_250pg", units["astral_B1"]), "-")  # no astral250pg_B1
        self.assertEqual(fdp.counterpart(ctx, "set_S1", units["astral_A2"]), "-")


# ---------------------------------------------------------------- build, --only, W_node and smoke layouts
class TestBuild(TempDir):
    def test_written_files(self):
        c = load(out=self.path("out"))
        fdp.build(c)
        names = sorted(os.listdir(self.path("out/tables")))
        self.assertEqual(names, ["O11_fdp_datasets.tsv", "O11_fdp_results.tsv", "O11_fdp_runs.tsv",
                                 "O12_fdp_arath.tsv", "O26_pairings.tsv"])
        cols, rows = T.read_table(self.path("out/tables/O11_fdp_results.tsv"))  # skips the '#' note line
        self.assertEqual(cols, fdp.O11_RESULTS_COLUMNS)
        r = [x for x in rows if x["engine"] == "msfragger" and x["unit"] == "velos_r1"
             and x["database"] == "hy_entrap_s1_td" and x["level"] == "psm"][0]
        _, raw = T.read_table(fx("counts_fx.tsv"))
        src = [x for x in raw if x["engine"] == "msfragger" and x["benchmark"] == "per_file" and x["run"] == "velos_r1"
               and x["database"] == "hy_entrap_s1_td" and x["level"] == "psm"][0]
        # copied columns exactly as EE printed them; the recomputed value with 6 decimals
        self.assertEqual((r["combined_fdp"], r["te_ratio"], r["lower_bound_fdp"]),
                         (src["combined_fdp"], src["te_ratio"], src["lower_bound_fdp"]))
        rec = int(src["entrapment"]) / int(src["accepted"]) * (1 + float(src["te_ratio"]))
        self.assertEqual(r["combined_recomputed"], f"{rec:.6f}")
        cols, rows = T.read_table(self.path("out/tables/O11_fdp_runs.tsv"))
        r = [x for x in rows if x["engine"] == "prose" and x["unit"] == "velos_r1" and x["level"] == "psm"
             and x["design"] == "shuffled"][0]
        self.assertEqual((r["mean_own"], r["sd_own"], r["mean_shared"], r["natural"]),
                         ("0.012000", "0.002000", "0.011000", "NA"))

    def test_only(self):
        c = load(only=("pairing",))
        fdp.build(c)
        self.assertEqual(list(c.results), ["O26_pairings"])
        self.assertEqual(c.numbers, [])
        c = load(only=("fdp",), levels=("psm",))
        fdp.build(c)
        self.assertEqual(list(c.results), ["O11_fdp_results", "O11_fdp_runs", "O11_fdp_datasets", "O12_fdp_arath"])
        self.assertEqual({r["level"] for r in c.results["O11_fdp_runs"]}, {"psm"})
        self.assertFalse([n for n in c.numbers if ".peptide." in n.key])

    def test_wnode(self):
        c = load(counts=fx("counts_wnode_fx.tsv"), coverage=fx("coverage_wnode_fx.tsv"),
                 timings=fx("timings_wnode_fx.tsv"))
        fdp.build(c)
        self.assertEqual({r["unit"] for r in c.results["O11_fdp_runs"]}, {"astral250pg_A2"})
        self.assertTrue(all(r["n_runs"] == 0 for r in c.results["O11_fdp_datasets"]))
        keys = {n.key: n for n in c.numbers}
        self.assertEqual(keys["fdp.psm.prose.max_run_mean"].value, T.Missing("empty"))
        self.assertEqual(keys["fdp.psm.prose.max_run_mean"].text, "NA")
        self.assertEqual(keys["fdp.psm.prose.n_runs"].value, 0)
        self.assertEqual(keys["fdp.psm.prose.n_runs_mean_above_1pct"].value, T.Missing("empty"))
        self.assertEqual(c.results["O12_fdp_arath"], [])
        self.assertEqual({r["unit"] for r in c.results["O26_pairings"]}, {"astral250pg_A2"})

    def test_smoke(self):
        c = T.load(T.Options(runs=fx("runs_smoke_fx.tsv"), design="none", counts=fx("counts_smoke_fx.tsv"),
                             coverage=fx("coverage_smoke_fx.tsv"), timings=fx("timings_smoke_fx.tsv"),
                             references=None, mzml_counts=None))
        fdp.build(c)
        runs = c.results["O11_fdp_runs"]
        self.assertEqual(len(runs), 3 * 3 * 2)
        self.assertEqual({r["kind"] for r in runs}, {"other"})
        res = c.results["O11_fdp_results"]
        self.assertEqual({r["realisation"] for r in res}, {"-"})  # smoke_entrap_td: shuffled without realisation
        self.assertEqual(c.results["O12_fdp_arath"], [])
        self.assertEqual(c.results["O26_pairings"], [])
        keys = {n.key: n for n in c.numbers}
        self.assertEqual(keys["fdp.psm.prose.n_runs"].source_side, "mixed")


if __name__ == "__main__":
    unittest.main()
