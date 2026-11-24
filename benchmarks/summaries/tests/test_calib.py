"""Tests of the calib module (SPEC 6): T23 (the MSFragger, ProSE and Sage log parsers), O19 counts on the base
fixtures, the O19 settings tables on a temporary W/out tree (with what C23 reads), O20 and O21 on made-up arm rows,
and the empty cases (no logs, no arm rows, W_node, smoke). Fixtures: the base fixtures of the loader tests and fixtures/calib_*
(calib_logs/ log shapes as in the local driver logs; calib_counts_arms_fx.tsv and calib_coverage_arms_fx.tsv: rows
of the future per_file_percolator_s{1,42,137}, per_file_peptdeep and per_file_msbooster arms, added to the base
fixtures by the tests; calib_commands_fx.log, calib_versions_fx.txt, calib_iprg2015_qe_fx.ini for O21)."""
import math
import os
import shutil
import statistics
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True

from summaries import calib, design, tables as T  # noqa: E402

FX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")
LOGS = os.path.join(FX, "calib_logs")


def fx(name):
    return os.path.join(FX, name)


def lx(name):
    return os.path.join(LOGS, name)


def fx_fdp(engine, bench, run, db, level="psm"):
    """combined_fdp of one row of counts_fx.tsv as printed there: the expected FDP values follow the fixture, so a
    regenerated fixture (tests/fixtures/make_fixtures.py) keeps these tests valid."""
    found = []
    with open(fx("counts_fx.tsv"), encoding="utf-8") as f:
        header = f.readline().rstrip("\r\n").split("\t")
        for line in f:
            r = dict(zip(header, line.rstrip("\r\n").split("\t")))
            if (r["engine"], r["benchmark"], r["run"], r["database"], r["level"]) == (engine, bench, run, db, level):
                found.append(float(r["combined_fdp"]))
    if len(found) != 1:
        raise AssertionError(f"counts_fx.tsv {engine} {bench} {run} {db} {level}: {len(found)} rows")
    return found[0]


def options(**kw):
    """Options of the base fixture W (runs_fx + counts/coverage/timings_fx), nothing written."""
    o = dict(runs=fx("runs_fx.tsv"), counts=fx("counts_fx.tsv"), coverage=fx("coverage_fx.tsv"),
             timings=fx("timings_fx.tsv"), versions=None, params_dir=fx("params_fx"), references=None,
             mzml_counts=None)
    o.update(kw)
    return T.Options(**o)


def concat(base, extra, dst):
    """base TSV plus the data lines of extra (same header)."""
    with open(base, encoding="utf-8") as f:
        a = f.read().splitlines()
    with open(extra, encoding="utf-8") as f:
        b = f.read().splitlines()
    if a[0] != b[0]:
        raise AssertionError(f"{extra}: header differs from {base}")
    with open(dst, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(a + b[1:]) + "\n")
    return dst


def keep_rows(src, dst, keep):
    with open(src, encoding="utf-8") as f:
        lines = f.read().splitlines()
    out = [lines[0]] + [x for x in lines[1:] if keep(x.split("\t"))]
    with open(dst, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(out) + "\n")
    return dst


def lines_of(ctx, level=None, cid=None):
    return [(lv, c, m) for lv, c, m in ctx.report.lines if (level is None or lv == level) and (cid is None or
                                                                                              c == cid)]


def number(ctx, key):
    found = [n for n in ctx.numbers if n.key == key]
    if len(found) != 1:
        raise AssertionError(f"number {key}: {len(found)} rows")
    return found[0]


def pick(rows, **match):
    out = [r for r in rows if all(r[k] == v for k, v in match.items())]
    if len(out) != 1:
        raise AssertionError(f"{match}: {len(out)} rows")
    return out[0]


def missing(x, reason=None):
    return isinstance(x, T.Missing) and (reason is None or x.reason == reason)


class TempDir(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="summaries_calib_test_")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def path(self, *parts):
        return os.path.join(self.tmp, *parts)

    def text(self, path, text):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        return path


# ---------------------------------------------------------------- T23 log parsers (SPEC O19, 6)
class TestT23Parsers(TempDir):
    def test_msfragger_chosen(self):
        """'New fragment_mass_tolerance = 10 PPM' -> (10, ppm, chosen); a New line after '... DONE IN' is ignored."""
        chosen = calib.parse_msfragger_log(lx("msfragger_search_fx.log"))
        self.assertEqual(chosen["fragment_mass_tolerance"], "10 PPM")
        self.assertEqual(chosen["use_topN_peaks"], "150")  # not the 999 after the block
        values, source, notes = calib.msfragger_settings(chosen, calib.read_fragger_params(lx("fragger_fx.params")))
        self.assertEqual((values["fragment_tol"], values["fragment_tol_unit"], source), (10.0, "ppm", "chosen"))
        self.assertEqual((values["use_topN_peaks"], values["minimum_ratio"], values["intensity_transform"],
                          values["remove_precursor_peak"], values["max_fragment_charge"]), (150, 0.01, 1, 1, 2))
        self.assertEqual(notes, [])

    def test_msfragger_configured_da(self):
        """No New lines + fragger.params with fragment_mass_units 0 -> the configured values, unit Da."""
        params = calib.read_fragger_params(lx("fragger_fx.params"))
        self.assertEqual(params["fragment_mass_units"], "0")  # the comment after '#' is removed
        self.assertEqual(params["remainder_fragment_masses"], "")
        for log in ("msfragger_search_nonew_fx.log", "msfragger_search_cal1_fx.log"):
            chosen = calib.parse_msfragger_log(lx(log))
            self.assertEqual(dict(chosen), {}, log)  # calibrate_mass 0: no banner; 1: 'MASS CALIBRATION' only
            values, source, notes = calib.msfragger_settings(chosen, params)
            self.assertEqual((values["fragment_tol"], values["fragment_tol_unit"], source), (0.02, "Da", "configured"))
            self.assertEqual((values["use_topN_peaks"], values["minimum_ratio"], values["intensity_transform"],
                              values["remove_precursor_peak"], values["max_fragment_charge"]), (300, 0.0, 0, 1, 2))

    def test_msfragger_mixed_and_missing(self):
        chosen = calib.parse_msfragger_log(lx("msfragger_search_mixed_fx.log"))
        self.assertNotIn("max_fragment_charge", chosen)  # as in 17 of the 274 local logs
        values, source, notes = calib.msfragger_settings(chosen, calib.read_fragger_params(lx("fragger_fx.params")))
        self.assertEqual((source, values["fragment_tol"], values["fragment_tol_unit"], values["max_fragment_charge"]),
                         ("mixed", 7.0, "ppm", 2))
        self.assertEqual(notes, ["configured: max_fragment_charge"])
        values, source, notes = calib.msfragger_settings(chosen, None)  # no fragger.params
        self.assertEqual(source, "mixed")
        self.assertTrue(missing(values["max_fragment_charge"], "missing"))
        self.assertEqual(notes, ["missing: max_fragment_charge"])
        values, source, notes = calib.msfragger_settings({}, None)
        self.assertTrue(missing(source, "no_settings"))
        self.assertTrue(missing(values["fragment_tol"], "missing"))
        values, source, notes = calib.msfragger_settings({"fragment_mass_tolerance": "ten"}, None)
        self.assertTrue(missing(values["fragment_tol"], "unparsed"))
        params = {"fragment_mass_tolerance": "20", "fragment_mass_units": "2"}
        values, source, notes = calib.msfragger_settings({}, params)
        self.assertTrue(missing(values["fragment_tol_unit"], "fragment_mass_units"))

    def test_prose_ppm_line(self):
        sections, ordered = calib.parse_prose_log(lx("prose_all_fx.log"))
        self.assertEqual(list(sections), ["hfx_r1"])
        self.assertEqual(sections["hfx_r1"]["fragment"], (0.0, 1.56, "ppm", 20.0, 6.26, "ppm", 95.0))
        self.assertEqual(len(ordered), 1)  # the Precursor and 'Fragment idx' lines do not match

    def test_prose_da_three_inputs(self):
        """ProSE Da log with 3 inputs and the deisotoping-limit line -> 3 rows in input order, unit Da."""
        deiso = ("[ProSE] Fragment tolerance 0.5 Da exceeds the deisotoping limit (100 ppm / 0.1 Da); skipping MS2 "
                 "deisotoping (expected for low-resolution data).")
        self.assertIsNone(calib.PROSE_FRAGMENT.match(deiso))
        sections, ordered = calib.parse_prose_log(lx("prose_all_da_fx.log"))
        self.assertEqual(len(ordered), 3)  # the deisotoping line is not matched
        inputs = ["run_c", "run_a", "run_b"]
        by_input, extra = calib.prose_by_input(lx("prose_all_da_fx.log"), inputs)
        self.assertEqual((list(by_input), extra), (inputs, 0))
        self.assertEqual([by_input[i]["fragment"][4] for i in inputs], [0.33, 0.50, 0.30])
        self.assertEqual({by_input[i]["fragment"][5] for i in inputs}, {"Da"})
        self.assertEqual({by_input[i]["fragment"][2] for i in inputs}, {"Da"})
        self.assertEqual(by_input["run_b"]["fragment"][6], 95.5)
        self.assertEqual([by_input[i]["kept"] for i in inputs], [False, True, False])
        # assigned by name, not by position, when the inputs file has another order
        by_name, _ = calib.prose_by_input(lx("prose_all_da_fx.log"), ["run_a", "run_b", "run_c"])
        self.assertEqual(by_name["run_a"]["fragment"][4], 0.50)

    def test_prose_without_searching_lines(self):
        """Without Searching lines the i-th Fragment line goes to input i (SPEC O19); surplus lines are counted."""
        with open(lx("prose_all_da_fx.log"), encoding="utf-8") as f:
            text = "".join(x for x in f.read().splitlines(True) if "Searching" not in x)
        p = self.text(self.path("all.log"), text)
        by_input, extra = calib.prose_by_input(p, ["x", "y"])
        self.assertEqual([by_input[i]["fragment"][4] for i in ("x", "y")], [0.33, 0.50])
        self.assertEqual(extra, 1)
        by_input, extra = calib.prose_by_input(p, ["x", "y", "z", "w"])
        self.assertIsNone(by_input["w"]["fragment"])

    def test_prose_insufficient(self):
        sections, ordered = calib.parse_prose_log(lx("prose_all_insufficient_fx.log"))
        self.assertEqual((sections["hfx_r1"]["fragment"], sections["hfx_r1"]["insufficient"], ordered),
                         (None, True, []))

    def test_prose_configured(self):
        shutil.copy(lx("summary_fx.yaml"), self.path("summary.yaml"))
        self.assertEqual(calib.prose_configured(self.tmp), (20.0, "ppm", True, ""))
        os.remove(self.path("summary.yaml"))
        tol, unit, enabled, note = calib.prose_configured(self.tmp)
        self.assertTrue(missing(tol, "no_summary"))
        self.assertEqual(note, "no summary.yaml")

    def test_sage_json(self):
        self.assertEqual(calib.read_sage_json(lx("sage_fx.json")), (20.0, "ppm", 2, []))
        p = self.text(self.path("sage.json"), '{"fragment_tol": {"da": [-0.5, 0.4]}}')
        tol, unit, mfc, notes = calib.read_sage_json(p)
        self.assertEqual((tol, unit), (0.4, "Da"))
        self.assertTrue(missing(mfc, "sage_default"))
        self.assertEqual(notes, ["asymmetric window [-0.5, 0.4]"])

    def test_pick_logs(self):
        """Timed search: the last of r1-r3 is used, r1-r3 compared; untimed: <stage>.log (SPEC O19 "Which log")."""
        self.assertEqual(calib.pick_logs(self.tmp, "search"), (None, []))
        self.text(self.path("search.log"), "")
        self.assertEqual(calib.pick_logs(self.tmp, "search"), ("search.log", ["search.log"]))
        for r in (1, 2, 3):
            self.text(self.path(f"all.r{r}.log"), "")
        self.assertEqual(calib.pick_logs(self.tmp, "all"), ("all.r3.log", ["all.r1.log", "all.r2.log", "all.r3.log"]))


# ---------------------------------------------------------------- O19 counts (SPEC O19 "Counts file")
class TestO19Counts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ctx = T.load(options())
        calib.build_counts(cls.ctx, ("hfx_r1", "velos_r1", "no_such_run"))
        cls.rows = cls.ctx.results["O19_calibration_counts"]

    def row(self, unit, engine, arm, level="psm"):
        return pick(self.rows, unit=unit, engine=engine, arm=arm, level=level)

    def test_rows(self):
        # 2 units x (prose main, cal_off; msfragger main, cal1, cal0; sage main) x 2 levels
        self.assertEqual(len(self.rows), 24)
        self.assertEqual([(r["engine"], r["arm"]) for r in self.rows if r["unit"] == "hfx_r1" and r["level"] == "psm"],
                         [("prose", "main"), ("prose", "cal_off"), ("msfragger", "main"), ("msfragger", "cal1"),
                          ("msfragger", "cal0"), ("sage", "main")])

    def test_hfx_counts_and_fdp(self):
        """FDP over the realisations with N > 0 in the main arm and every arm of the engine (arms: s1 only)."""
        r = self.row("hfx_r1", "prose", "main")
        self.assertEqual(r["accepted_td"], 12100)
        self.assertTrue(missing(r["ratio_to_main"], "main"))
        self.assertAlmostEqual(r["fdp_shuffled_mean"], fx_fdp("prose", "per_file", "hfx_r1", "hye_entrap_s1_td"),
                               places=12)
        self.assertTrue(missing(r["fdp_shuffled_sd"], "n<2"))
        self.assertEqual(r["fdp_shuffled_n"], 1)
        self.assertTrue(missing(r["fdp_natural"], "no_natural"))
        self.assertEqual(r["status"], "ok")
        r = self.row("hfx_r1", "prose", "cal_off")
        self.assertEqual(r["accepted_td"], 11737)
        self.assertAlmostEqual(r["ratio_to_main"], 0.97, places=12)
        self.assertAlmostEqual(r["fdp_shuffled_mean"], fx_fdp("prose", "per_file_cal_off", "hfx_r1",
                                                              "hye_entrap_s1_td"), places=12)
        for arm, bench in (("main", "per_file"), ("cal1", "per_file_cal1"), ("cal0", "per_file_cal0")):
            r = self.row("hfx_r1", "msfragger", arm)
            self.assertAlmostEqual(r["fdp_shuffled_mean"], fx_fdp("msfragger", bench, "hfx_r1", "hye_entrap_s1_td"),
                                   places=12)
            self.assertEqual(r["fdp_shuffled_n"], 1)
        self.assertAlmostEqual(self.row("hfx_r1", "msfragger", "cal1")["ratio_to_main"], 10670 / 11000, places=12)
        r = self.row("hfx_r1", "sage", "main")  # Sage has no arm: its own three realisations
        self.assertEqual((r["accepted_td"], r["fdp_shuffled_n"]), (10450, 3))
        sage = [fx_fdp("sage", "per_file", "hfx_r1", f"hye_entrap_s{i}_td") for i in (1, 2, 3)]
        self.assertAlmostEqual(r["fdp_shuffled_mean"], math.fsum(sage) / 3, places=12)
        self.assertAlmostEqual(r["fdp_shuffled_sd"], statistics.stdev(sage), places=12)
        r = self.row("hfx_r1", "prose", "cal_off", level="peptide")
        self.assertAlmostEqual(r["ratio_to_main"], 3912 / 4033, places=12)

    def test_velos_natural_and_arm_not_run(self):
        r = self.row("velos_r1", "prose", "main")
        self.assertEqual((r["accepted_td"], r["fdp_shuffled_n"]), (11000, 3))
        self.assertAlmostEqual(r["fdp_shuffled_mean"], 0.012, places=12)
        self.assertAlmostEqual(r["fdp_shuffled_sd"], 0.002, places=12)
        self.assertAlmostEqual(r["fdp_natural"], fx_fdp("prose", "per_file", "velos_r1", "hy_velos_natural_td"),
                               places=12)
        r = self.row("velos_r1", "prose", "cal_off")  # no arm search on velos_r1 in the fixtures
        self.assertTrue(missing(r["accepted_td"], "no_coverage"))
        self.assertTrue(missing(r["ratio_to_main"], "no_coverage"))
        self.assertEqual((r["fdp_shuffled_n"], r["status"]), (0, "no_coverage"))
        self.assertTrue(missing(r["fdp_shuffled_mean"], "no_coverage"))
        self.assertTrue(missing(r["fdp_natural"], "no_coverage"))
        r = self.row("velos_r1", "sage", "main")  # s3 failed: s1 and s2
        self.assertEqual(r["fdp_shuffled_n"], 2)
        self.assertAlmostEqual(r["fdp_shuffled_mean"], (fx_fdp("sage", "per_file", "velos_r1", "hy_entrap_s1_td")
                                                        + fx_fdp("sage", "per_file", "velos_r1", "hy_entrap_s2_td"))
                               / 2, places=12)
        self.assertAlmostEqual(r["fdp_natural"], fx_fdp("sage", "per_file", "velos_r1", "hy_velos_natural_td"),
                               places=12)

    def test_numbers(self):
        n = number(self.ctx, "cal.cal_off.psm.lead")
        self.assertAlmostEqual(n.value, -3.0, places=9)
        self.assertEqual((n.text, n.unit, n.output, n.source_side, n.main_text_allowed), ("-3.0", "%", "O19",
                                                                                          "tuning", "no"))
        self.assertEqual(number(self.ctx, "cal.cal_off.psm.n_runs").value, 1)
        self.assertAlmostEqual(number(self.ctx, "cal.cal0.peptide.lead").value, 100 * (3556 / 3666 - 1), places=9)
        self.assertEqual(len([n for n in self.ctx.numbers if n.key.startswith("cal.")]), 12)

    def test_checks(self):
        info = [m for _, _, m in lines_of(self.ctx, "INFO", "O19")]
        self.assertIn("1 of 3 CAL_RUNS not in the run table: no_such_run", info)
        self.assertTrue(any("expected 9" in m and "prose cal_off 2, msfragger cal1 2, msfragger cal0 2" in m
                            for m in info), info)
        self.assertTrue(lines_of(self.ctx, "WARN", "O19"))  # 2 of 9 searches per arm

    def test_arm_outside_cal_runs(self):
        ctx = T.load(options())
        calib.build_counts(ctx, ("velos_r1",))
        warn = [m for _, _, m in lines_of(ctx, "WARN", "O19")]
        self.assertTrue(any("outside CAL_RUNS" in m and "hfx_r1" in m for m in warn), warn)
        self.assertTrue(missing(number(ctx, "cal.cal_off.psm.lead").value, "empty"))
        self.assertEqual(number(ctx, "cal.cal_off.psm.lead").source_side, "none")


class TestO19FdpSets(TempDir):
    def test_arm_rows_use_their_own_pair_with_main(self):
        """SPEC O19: an arm row's FDP is over the realisations counted in both that arm and the main arm. MSFragger
        cal1 counted s1-s3 on hfx_r1, cal0 only s1: cal1 averages 3, cal0 1, the main row (main and every arm) 1."""
        with open(fx("counts_fx.tsv"), encoding="utf-8") as f:
            counts_text = f.read()
        with open(fx("coverage_fx.tsv"), encoding="utf-8") as f:
            coverage_text = f.read()
        extra_counts, extra_cov = [], []
        for line in counts_text.splitlines()[1:]:
            c = line.split("\t")
            if c[:3] == ["msfragger", "per_file", "hfx_r1"] and c[3] in ("hye_entrap_s2_td", "hye_entrap_s3_td"):
                c[1] = "per_file_cal1"
                extra_counts.append("\t".join(c))
                if c[5] == "psm":
                    extra_cov.append(f"msfragger\tper_file_cal1\thfx_r1\t{c[3]}\tok\tyes")
        counts = self.text(self.path("counts.tsv"), counts_text + "\n".join(extra_counts) + "\n")
        coverage = self.text(self.path("coverage.tsv"), coverage_text + "\n".join(extra_cov) + "\n")
        ctx = T.load(options(counts=counts, coverage=coverage))
        calib.build_counts(ctx, ("hfx_r1",))
        rows = ctx.results["O19_calibration_counts"]
        cal1 = pick(rows, unit="hfx_r1", engine="msfragger", arm="cal1", level="psm")
        values = [ctx.fdp("msfragger", "hfx_r1", f"hye_entrap_s{i}_td", "psm", benchmark="per_file_cal1")
                  for i in (1, 2, 3)]
        self.assertEqual(cal1["fdp_shuffled_n"], 3)
        self.assertAlmostEqual(cal1["fdp_shuffled_mean"], math.fsum(values) / 3, places=12)
        self.assertAlmostEqual(cal1["fdp_shuffled_sd"], statistics.stdev(values), places=12)
        cal0 = pick(rows, unit="hfx_r1", engine="msfragger", arm="cal0", level="psm")
        self.assertEqual(cal0["fdp_shuffled_n"], 1)
        main = pick(rows, unit="hfx_r1", engine="msfragger", arm="main", level="psm")
        self.assertEqual(main["fdp_shuffled_n"], 1)
        self.assertAlmostEqual(main["fdp_shuffled_mean"], fx_fdp("msfragger", "per_file", "hfx_r1",
                                                                 "hye_entrap_s1_td"), places=12)


# ---------------------------------------------------------------- O19 settings tables and C23 on a W/out tree
class TestO19Settings(TempDir):
    """A W/out tree for hfx_r1 and the pooled pxd058436_DN05 (log shapes of calib_logs/)."""

    def folder(self, engine, bench, run, db, inputs=None):
        p = self.path("W", "out", engine, bench, run, db)
        os.makedirs(p, exist_ok=True)
        self.text(os.path.join(p, "inputs"), "\n".join(inputs or [run]) + "\n")
        return p

    def put(self, folder, name, src=None, text=None):
        if src is not None:
            shutil.copy(lx(src), os.path.join(folder, name))
        else:
            self.text(os.path.join(folder, name), text)

    def make_tree(self):
        run = "hfx_r1"
        for db in ("hye_td", "hye_entrap_s1_td", "hye_entrap_s2_td", "hye_entrap_s3_td", "hye_arath_td"):
            f = self.folder("msfragger", "per_file", run, db)
            if db != "hye_entrap_s2_td":
                self.put(f, "fragger.params", "fragger_fx.params")
            if db == "hye_td":
                for r in (1, 2, 3):
                    self.put(f, f"search.r{r}.log", "msfragger_search_fx.log")
            elif db in ("hye_entrap_s1_td", "hye_entrap_s2_td"):
                self.put(f, "search.log", "msfragger_search_mixed_fx.log")
            elif db == "hye_arath_td":  # r1 differs from r2, r3
                self.put(f, "search.r1.log", "msfragger_search_mixed_fx.log")
                self.put(f, "search.r2.log", "msfragger_search_fx.log")
                self.put(f, "search.r3.log", "msfragger_search_fx.log")
            else:
                self.put(f, "search.log", "msfragger_search_fx.log")
            f = self.folder("prose", "per_file", run, db)
            self.put(f, "summary.yaml", "summary_fx.yaml")
            if db == "hye_td":  # r2 differs: note varies, values of r3
                with open(lx("prose_all_fx.log"), encoding="utf-8") as fh:
                    log = fh.read()
                self.put(f, "all.r1.log", "prose_all_fx.log")
                self.put(f, "all.r2.log", text=log.replace("-> 6.26 ppm", "-> 6.50 ppm"))
                self.put(f, "all.r3.log", "prose_all_fx.log")
            elif db == "hye_entrap_s3_td":
                self.put(f, "all.log", "prose_all_insufficient_fx.log")
            else:
                self.put(f, "all.log", "prose_all_fx.log")
            f = self.folder("sage", "per_file", run, db)
            self.put(f, "sage.json", "sage_fx.json")
            self.put(f, "all.log", text="")
        for bench, log in (("per_file_cal1", "msfragger_search_cal1_fx.log"),
                           ("per_file_cal0", "msfragger_search_nonew_fx.log")):
            for db in ("hye_td", "hye_entrap_s1_td"):
                f = self.folder("msfragger", bench, run, db)
                self.put(f, "fragger.params", "fragger_fx.params")
                self.put(f, "search.log", log)
        with open(lx("summary_fx.yaml"), encoding="utf-8") as fh:
            off = fh.read().replace("calibration_enabled: true", "calibration_enabled: false")
        for db in ("hye_td", "hye_entrap_s1_td"):
            f = self.folder("prose", "per_file_cal_off", run, db)
            self.put(f, "summary.yaml", text=off)
            self.put(f, "all.log", text="[ProSE] [1/1] Searching /W/mzml/hfx_r1.mzML\n[ProSE] Total time: 5.0 s\n")
        f = self.folder("msfragger", "per_file", "pxd058436_DN05", "pxd058436_td", ["DN05_r1", "DN05_r2"])
        self.put(f, "fragger.params", "fragger_fx.params")
        self.put(f, "search.log", "msfragger_search_fx.log")
        for bench in ("per_file", "per_file_low_memory"):
            f = self.folder("prose", bench, "pxd058436_DN05", "pxd058436_td", ["DN05_r1", "DN05_r2"])
            self.put(f, "summary.yaml", "summary_fx.yaml")
            self.put(f, "all.log", "prose_all_pooled_fx.log")
        return self.path("W")

    def only_tree_units(self):
        return keep_rows(fx("coverage_fx.tsv"), self.path("coverage.tsv"),
                         lambda c: c[2] in ("hfx_r1", "pxd058436_DN05"))

    def test_rows_and_values(self):
        w = self.make_tree()
        ctx = T.load(options(work=w, coverage=self.only_tree_units(), only=("calibration",)))
        self.assertTrue(ctx.logs_available)
        calib.build(ctx)
        msf = ctx.results["O19_settings_msfragger"]
        self.assertEqual(len(msf), 10)  # hfx_r1: 5 per_file, 2 cal1, 2 cal0; the pooled sample: 1
        r = pick(msf, benchmark="per_file", unit="hfx_r1", database="hye_td")
        self.assertEqual((r["log"], r["source"], r["fragment_tol"], r["fragment_tol_unit"], r["use_topN_peaks"],
                          r["max_fragment_charge"], r["note"]), ("search.r3.log", "chosen", 10.0, "ppm", 150, 2, ""))
        r = pick(msf, benchmark="per_file", unit="hfx_r1", database="hye_entrap_s1_td")
        self.assertEqual((r["source"], r["fragment_tol"], r["max_fragment_charge"], r["note"]),
                         ("mixed", 7.0, 2, "configured: max_fragment_charge"))
        r = pick(msf, benchmark="per_file", unit="hfx_r1", database="hye_entrap_s2_td")
        self.assertEqual((r["source"], r["note"]), ("mixed", "no fragger.params; missing: max_fragment_charge"))
        self.assertEqual(pick(msf, benchmark="per_file", unit="hfx_r1", database="hye_arath_td")["note"], "varies")
        for bench in ("per_file_cal1", "per_file_cal0"):
            r = pick(msf, benchmark=bench, unit="hfx_r1", database="hye_td")
            self.assertEqual((r["source"], r["fragment_tol"], r["fragment_tol_unit"], r["log"]),
                             ("configured", 0.02, "Da", "search.log"))
        prose = ctx.results["O19_settings_prose"]
        self.assertEqual(len(prose), 11)  # hfx_r1: 5 per_file, 2 cal_off; the pooled sample: 2 inputs x 2
        r = pick(prose, benchmark="per_file", unit="hfx_r1", database="hye_td")
        self.assertEqual((r["input"], r["log"], r["source"], r["prose_fragment_offset"], r["prose_fragment_sigma"],
                          r["prose_fragment_tol"], r["prose_fragment_tol_unit"], r["prose_covered_pct"], r["note"]),
                         ("hfx_r1", "all.r3.log", "chosen", 0.0, 1.56, 6.26, "ppm", 95.0, "varies"))
        r = pick(prose, benchmark="per_file", unit="hfx_r1", database="hye_entrap_s3_td")
        self.assertEqual((r["source"], r["prose_fragment_tol"], r["prose_fragment_tol_unit"], r["note"]),
                         ("configured", 20.0, "ppm", "calibration: insufficient PSMs"))
        self.assertTrue(missing(r["prose_fragment_sigma"], "configured"))
        r = pick(prose, benchmark="per_file_cal_off", unit="hfx_r1", database="hye_td")
        self.assertEqual((r["source"], r["prose_fragment_tol"], r["note"]), ("configured", 20.0, "calibration off"))
        pooled = [r for r in prose if r["benchmark"] == "per_file" and r["unit"] == "pxd058436_DN05"]
        self.assertEqual([(r["input"], r["prose_fragment_tol"]) for r in pooled],
                         [("DN05_r1", 6.2), ("DN05_r2", 8.1)])  # input order, assigned by the Searching lines
        sage = ctx.results["O19_settings_sage"]
        self.assertEqual(len(sage), 5)  # the pooled Sage search failed (not counted)
        self.assertEqual({(r["log"], r["source"], r["fragment_tol"], r["fragment_tol_unit"], r["max_fragment_charge"])
                          for r in sage}, {("sage.json", "configured", 20.0, "ppm", 2)})
        # what checks.py's C23 reads: a row with a source for every counted search, one per input file for ProSE
        for name, engine in (("O19_settings_msfragger", "msfragger"), ("O19_settings_prose", "prose")):
            have = {}
            for r in ctx.results[name]:
                if not T.is_missing(r["source"]):
                    key = (r["benchmark"], r["unit"], r["database"])
                    have[key] = have.get(key, 0) + 1
            for c in ctx.coverage:
                if c.engine == engine and c.scope == "unit" and c.counted:
                    need = c.unit.n_files if engine == "prose" else 1
                    self.assertGreaterEqual(have.get((c.benchmark, c.run, c.database), 0), need, (name, c.run))
        info = [m for _, _, m in lines_of(ctx, "INFO", "O19") if m.startswith("settings rows")]
        self.assertEqual(len(info), 1)
        self.assertIn("10 MSFragger (10 searches, 0 without a value)", info[0])
        self.assertIn("11 ProSE inputs (9 searches, 0 without a value)", info[0])
        self.assertIn("r1-r3 differ: 1 MSFragger, 1 ProSE", info[0])
        self.assertEqual(lines_of(ctx, cid="C23"), [])  # C23 is checks.py's

    def test_searches_without_folder(self):
        """Counted searches without a folder get a row with every value NA (source NA: no settings row for C23)."""
        w = self.make_tree()
        ctx = T.load(options(work=w, only=("calibration",)))
        calib.build(ctx)
        r = pick(ctx.results["O19_settings_msfragger"], benchmark="per_file", unit="velos_r1", database="hy_td")
        self.assertEqual(r["note"], "no search folder")
        self.assertTrue(missing(r["source"], "no_folder"))
        self.assertTrue(missing(r["fragment_tol"], "no_folder"))
        r = pick(ctx.results["O19_settings_prose"], benchmark="per_file", unit="velos_r1", database="hy_td")
        self.assertEqual((r["input"], r["note"]), ("velos_r1", "no search folder"))
        info = [m for _, _, m in lines_of(ctx, "INFO", "O19") if m.startswith("settings rows")][0]
        self.assertNotIn(" 0 without a value", info.split("ProSE inputs")[0])
        ctx = T.load(options(work=w, only=("percolator",)))
        calib.build(ctx)  # --only without calibration: no O19 table
        self.assertFalse([n for n in ctx.results if n.startswith("O19_")])

    def test_no_logs_header_only(self):
        """Without W/out the settings tables have their header and a note (SPEC 4)."""
        out = self.path("out")
        ctx = T.load(options(out=out))
        self.assertFalse(ctx.logs_available)
        calib.build(ctx)
        for name, cols in (("O19_settings_msfragger", calib.MSF_COLUMNS), ("O19_settings_prose", calib.PROSE_COLUMNS),
                           ("O19_settings_sage", calib.SAGE_COLUMNS)):
            with open(os.path.join(out, "tables", name + ".tsv"), encoding="utf-8") as f:
                lines = f.read().splitlines()
            self.assertTrue(lines[0].startswith("# not built: no W/out logs"), name)
            self.assertEqual(lines[1:], ["\t".join(cols)], name)
        info =[m for _, _, m in lines_of(ctx, "INFO", "O19")]
        self.assertTrue(any(m.startswith("settings tables empty") for m in info), info)
        self.assertIn("9 of 9 CAL_RUNS not in the run table", " ".join(info))
        self.assertEqual(ctx.results["O19_calibration_counts"], [])


# ---------------------------------------------------------------- O20 external Percolator (SPEC O20)
class TestO20Percolator(TempDir):
    def setUp(self):
        super().setUp()
        cnt = concat(fx("counts_fx.tsv"), fx("calib_counts_arms_fx.tsv"), self.path("counts.tsv"))
        cov = concat(fx("coverage_fx.tsv"), fx("calib_coverage_arms_fx.tsv"), self.path("coverage.tsv"))
        self.ctx = T.load(options(counts=cnt, coverage=cov))
        calib.build_percolator(self.ctx)
        self.runs = self.ctx.results["O20_external_percolator"]
        self.summary = self.ctx.results["O20_external_percolator_summary"]
        self.datasets = self.ctx.results["O20_external_percolator_datasets"]

    def run_row(self, pair, unit, level="psm"):
        return pick(self.runs, pair=pair, unit=unit, level=level)

    def test_run_rows(self):
        r = self.run_row("prose/msfragger", "hfx_r1")
        self.assertEqual((r["prose_n_seeds"], r["comparator_n_seeds"], r["used"], r["reason"], r["fdp_n_shared"]),
                         (3, 3, True, "", 1))
        self.assertAlmostEqual(r["prose"], 1100.0, places=9)  # mean of 1090, 1100, 1110
        self.assertAlmostEqual(r["comparator"], 1000.0, places=9)
        self.assertAlmostEqual(r["ratio"], 1.1, places=12)
        self.assertAlmostEqual(r["fdp_prose"], 0.012, places=12)  # s1 only: MSFragger has no s2 search
        self.assertAlmostEqual(r["fdp_comparator"], 0.008, places=12)
        r = self.run_row("prose/sage", "hfx_r1")
        self.assertEqual(r["fdp_n_shared"], 2)
        self.assertAlmostEqual(r["fdp_prose"], 0.011, places=12)
        self.assertAlmostEqual(r["fdp_comparator"], 0.011, places=12)
        r = self.run_row("prose/sage", "lumos_lfq_r1")  # Sage s42 accepted 0
        self.assertEqual((r["comparator_n_seeds"], r["used"], r["reason"]), (3, False, "sage:zero"))
        self.assertTrue(missing(r["ratio"], "sage:zero"))
        r = self.run_row("prose/sage", "hela_qe_hf_r1")  # Sage s137 failed
        self.assertEqual((r["comparator_n_seeds"], r["used"]), (2, False))
        self.assertTrue(r["reason"].startswith("sage:") and r["reason"].endswith("(per_file_percolator_s137)"),
                        r["reason"])
        r = self.run_row("prose/msfragger", "astral250pg_A2")  # decision run: ratio shown, not used
        self.assertAlmostEqual(r["ratio"], 1.5, places=12)
        self.assertEqual((r["used"], r["reason"]), (False, "decision"))
        r = self.run_row("prose/msfragger", "velos_r1")  # a tryptic unit without seed rows
        self.assertEqual((r["used"], r["prose_n_seeds"]), (False, 0))
        self.assertEqual(r["reason"], "prose:no_coverage (per_file_percolator_s1)")

    def test_summary_and_numbers(self):
        s = pick(self.summary, pair="prose/msfragger", level="psm", scope="tuning")
        self.assertEqual((s["n_datasets"], s["n_runs"]), (2, 2))
        self.assertAlmostEqual(s["equal_weight"], math.sqrt(1.1 * 1.21), places=12)
        self.assertAlmostEqual(s["run_weighted"], math.sqrt(1.1 * 1.21), places=12)
        self.assertAlmostEqual(s["sum_ratio"], 2310 / 2000, places=12)
        self.assertIn("velos", s["dropped_datasets"].split(", "))
        s = pick(self.summary, pair="prose/msfragger", level="psm", scope="heldout")
        self.assertEqual((s["n_datasets"], s["n_runs"]), (2, 2))
        self.assertAlmostEqual(s["equal_weight"], math.sqrt(0.99), places=12)
        self.assertAlmostEqual(s["sum_ratio"], 1990 / 2000, places=12)
        self.assertIn("astral_250pg", s["dropped_datasets"].split(", "))  # decision run only
        s = pick(self.summary, pair="prose/sage", level="psm", scope="tuning")
        self.assertEqual(s["n_datasets"], 1)
        self.assertAlmostEqual(s["equal_weight"], 1.1, places=12)
        self.assertIn("lumos_lfq", s["dropped_datasets"].split(", "))
        s = pick(self.summary, pair="prose/sage", level="psm", scope="heldout")
        self.assertAlmostEqual(s["equal_weight"], 0.9, places=12)
        self.assertIn("hela_qe_hf", s["dropped_datasets"].split(", "))
        n = number(self.ctx, "percolator.tuning.psm.msfragger.lead")
        self.assertAlmostEqual(n.value, 100 * (math.sqrt(1.331) - 1), places=9)
        self.assertEqual((n.text, n.source_side, n.main_text_allowed), ("15.4", "tuning", "no"))
        n = number(self.ctx, "percolator.heldout.psm.sage.lead")
        self.assertAlmostEqual(n.value, -10.0, places=9)
        self.assertEqual(n.main_text_allowed, "yes")
        self.assertAlmostEqual(number(self.ctx, "percolator.heldout.psm.msfragger.sum_lead").value, -0.5, places=9)
        self.assertEqual(number(self.ctx, "percolator.heldout.psm.msfragger.n_runs").value, 2)
        self.assertEqual(len([n for n in self.ctx.numbers if n.key.startswith("percolator.")]),
                         2 * 2 * 2 * 5)  # pairs x levels x scopes x keys

    def test_datasets(self):
        d = pick(self.datasets, pair="prose/sage", level="psm", group="lumos_lfq")
        self.assertEqual((d["n_units"], d["n_used"], d["note"]), (1, 0, "dropped: no run in the set"))
        d = pick(self.datasets, pair="prose/msfragger", level="psm", group="hfx")
        self.assertEqual((d["kind"], d["side"], d["fdp_n_runs"]), ("tuning", "tuning", 1))
        self.assertAlmostEqual(d["fdp_prose_mean"], 0.012, places=12)
        self.assertAlmostEqual(d["sum_ratio"], 1.1, places=12)
        d = pick(self.datasets, pair="prose/msfragger", level="psm", group="astral_250pg")
        self.assertEqual((d["n_units"], d["n_used"]), (2, 0))
        info = [m for _, _, m in lines_of(self.ctx, "INFO", "O20")]
        self.assertEqual(len(info), 1)
        self.assertTrue(info[0].startswith("built:"), info)


# ---------------------------------------------------------------- O21 prediction supplement (SPEC O21)
class TestO21Prediction(TempDir):
    def load(self, with_logs=True):
        cnt = concat(fx("counts_fx.tsv"), fx("calib_counts_arms_fx.tsv"), self.path("counts.tsv"))
        cov = concat(fx("coverage_fx.tsv"), fx("calib_coverage_arms_fx.tsv"), self.path("coverage.tsv"))
        params = self.path("params")
        shutil.copytree(fx("params_fx"), params, dirs_exist_ok=True)
        shutil.copy(fx("calib_iprg2015_qe_fx.ini"), os.path.join(params, "iprg2015_qe.ini"))
        kw = dict(counts=cnt, coverage=cov, params_dir=params)
        if with_logs:
            w = self.path("W")
            os.makedirs(w, exist_ok=True)
            shutil.copy(fx("calib_commands_fx.log"), os.path.join(w, "commands.log"))
            kw.update(work=w, versions=fx("calib_versions_fx.txt"))
        ctx = T.load(options(**kw))
        calib.build_prediction(ctx, design.PRED_GROUPS)
        return ctx

    def test_runs_summary_numbers(self):
        ctx = self.load()
        runs = ctx.results["O21_prediction"]
        r = pick(runs, comparison="peptdeep_vs_msbooster", level="psm", unit="hfx_r1")
        self.assertEqual((r["numerator"], r["denominator"], r["used"], r["instrument"], r["fdp_n_shared"]),
                         (13310, 12100, True, "Lumos", 1))  # the last command line of a search wins
        self.assertAlmostEqual(r["ratio"], 1.1, places=12)
        self.assertAlmostEqual(r["fdp_numerator"], 0.007, places=12)
        self.assertAlmostEqual(r["fdp_denominator"], 0.009, places=12)
        r = pick(runs, comparison="peptdeep_vs_msbooster", level="psm", unit="iprg2015_r1")
        self.assertAlmostEqual(r["ratio"], 20460 / 15500, places=12)
        self.assertEqual(r["instrument"], "QE")  # from <params_dir>/iprg2015_qe.ini
        r = pick(runs, comparison="peptdeep_vs_msbooster", level="psm", unit="astral250pg_B1")
        self.assertTrue(missing(r["instrument"], "no_command_line"))
        r = pick(runs, comparison="peptdeep_vs_msbooster", level="psm", unit="astral250pg_A2")
        self.assertEqual((r["used"], r["reason"]), (False, "decision"))
        r = pick(runs, comparison="peptdeep_vs_msbooster", level="psm", unit="astral250pg_B3")
        self.assertEqual((r["used"], r["reason"]), (False, "prose_peptdeep:no_coverage"))
        r = pick(runs, comparison="peptdeep_vs_main", level="psm", unit="hfx_r1")
        self.assertAlmostEqual(r["ratio"], 13310 / 12100, places=12)
        self.assertAlmostEqual(r["fdp_denominator"], fx_fdp("prose", "per_file", "hfx_r1", "hye_entrap_s1_td"),
                               places=12)
        r = pick(runs, comparison="msbooster_vs_main", level="psm", unit="hfx_r1")
        self.assertAlmostEqual(r["ratio"], 12100 / 11000, places=12)
        self.assertAlmostEqual(r["fdp_denominator"], fx_fdp("msfragger", "per_file", "hfx_r1", "hye_entrap_s1_td"),
                               places=12)
        s = pick(ctx.results["O21_prediction_summary"], comparison="peptdeep_vs_msbooster", level="psm")
        e = (1.1 * 1.32 * 1.0) ** (1 / 3)
        self.assertEqual((s["scope"], s["n_datasets"], s["n_runs"], s["msbooster_version"]),
                         ("pred_groups", 3, 3, "MSBooster v1.3.9"))
        self.assertAlmostEqual(s["equal_weight"], e, places=12)
        self.assertIn("lumos_lfq", s["dropped_datasets"].split(", "))
        n = number(ctx, "prediction.psm.peptdeep_vs_msbooster.lead")
        self.assertAlmostEqual(n.value, 100 * (e - 1), places=9)
        self.assertEqual((n.source_side, n.main_text_allowed), ("mixed", "no"))
        self.assertAlmostEqual(number(ctx, "prediction.psm.msbooster_vs_main.lead").value,
                               100 * ((1.1 * 1.0 * 1.1) ** (1 / 3) - 1), places=9)
        self.assertEqual(number(ctx, "prediction.psm.peptdeep_vs_main.n_datasets").value, 3)
        d = pick(ctx.results["O21_prediction_datasets"], comparison="peptdeep_vs_msbooster", level="psm",
                 group="iprg2015")
        self.assertEqual((d["instrument"], d["note"]), ("QE", "instrument from the parameter file"))
        d = pick(ctx.results["O21_prediction_datasets"], comparison="peptdeep_vs_msbooster", level="psm",
                 group="astral_250pg")
        self.assertEqual((d["n_units"], d["n_used"]), (2, 1))
        self.assertTrue(d["note"].startswith("runs out of the set: astral250pg_B3"), d["note"])
        self.assertEqual(lines_of(ctx, "WARN", "O21"), [])

    def test_without_commands_and_versions(self):
        ctx = self.load(with_logs=False)
        warn = [m for _, _, m in lines_of(ctx, "WARN", "O21")]
        self.assertEqual(len(warn), 2, warn)
        r = pick(ctx.results["O21_prediction"], comparison="peptdeep_vs_msbooster", level="psm", unit="hfx_r1")
        self.assertTrue(missing(r["instrument"], "no_command_line"))
        s = pick(ctx.results["O21_prediction_summary"], comparison="peptdeep_vs_msbooster", level="psm")
        self.assertTrue(missing(s["msbooster_version"], "not_recorded"))


# ---------------------------------------------------------------- empty cases (SPEC 4, T27, T28)
class TestEmpty(TempDir):
    def check_not_built(self, ctx):
        info = {c: m for lv, c, m in ctx.report.lines if lv == "INFO" and c in ("O20", "O21")}
        self.assertTrue(info["O20"].startswith("not built"), info)
        self.assertTrue(info["O21"].startswith("not built"), info)
        self.assertNotIn("O20_external_percolator", ctx.results)
        self.assertNotIn("O21_prediction", ctx.results)

    def test_base_without_arm_rows(self):
        ctx = T.load(options())
        calib.build(ctx)
        self.check_not_built(ctx)
        self.assertEqual(len([n for n in ctx.numbers if n.key.startswith("cal.")]), 12)

    def test_wnode(self):
        ctx = T.load(options(counts=fx("counts_wnode_fx.tsv"), coverage=fx("coverage_wnode_fx.tsv"),
                             timings=fx("timings_wnode_fx.tsv")))
        calib.build(ctx)
        self.check_not_built(ctx)

    def test_smoke(self):
        ctx = T.load(T.Options(runs=fx("runs_smoke_fx.tsv"), design="none", counts=fx("counts_smoke_fx.tsv"),
                               coverage=fx("coverage_smoke_fx.tsv"), timings=fx("timings_smoke_fx.tsv"),
                               references=None, mzml_counts=None, params_dir=fx("params_fx")))
        calib.build(ctx)
        self.check_not_built(ctx)
        self.assertEqual(ctx.results["O19_calibration_counts"], [])


if __name__ == "__main__":
    unittest.main()
