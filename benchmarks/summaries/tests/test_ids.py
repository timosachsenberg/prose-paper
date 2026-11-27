"""Tests of ids.py (SPEC 6): T3 (summary level), T4, T5, T6, T7, T8, T9, T25, T27, T35, and the O8 FDP columns, O9,
O10 (counts part), O14 and O24 on the base fixtures (runs_fx, counts_fx, coverage_fx) and ids_reference_fx.tsv."""
import math
import os
import shutil
import sys
import tempfile
import unittest
import warnings

sys.dont_write_bytecode = True

from summaries import design, fdp, ids, tables as T  # noqa: E402

OT = design.OT
FX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")
REF_FX = os.path.join(FX, "ids_reference_fx.tsv")


def fx(name):
    return os.path.join(FX, name)


def make_ctx(**kw):
    """T.load of the base fixture W (as test_tables.options), with the given Options fields replaced."""
    o = dict(runs=fx("runs_fx.tsv"), counts=fx("counts_fx.tsv"), coverage=fx("coverage_fx.tsv"),
             timings=fx("timings_fx.tsv"), versions=None, params_dir=fx("params_fx"), references=None,
             mzml_counts=None)
    o.update(kw)
    return T.load(T.Options(**o))


def built(**kw):
    ctx = make_ctx(**kw)
    ids.build(ctx)
    return ctx


def rows(ctx, table, **where):
    return [r for r in ctx.results[table] if all(r.get(k) == v for k, v in where.items())]


def one(ctx, table, **where):
    found = rows(ctx, table, **where)
    if len(found) != 1:
        raise AssertionError(f"{table} {where}: {len(found)} rows")
    return found[0]


def checks(ctx, cid, level=None):
    return [(lv, msg) for lv, c, msg in ctx.report.lines if c == cid and (level is None or lv == level)]


def number(ctx, key):
    found = [n for n in ctx.numbers if n.key == key]
    if len(found) != 1:
        raise AssertionError(f"number {key}: {len(found)} rows")
    return found[0]


def write_tsv(path, header, dict_rows):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\t".join(header) + "\n" + "".join("\t".join(str(r[c]) for c in header) + "\n" for r in dict_rows))
    return path


def read_tsv_rows(path):
    with open(path, encoding="utf-8") as f:
        lines = [x for x in f.read().split("\n") if x]
    header = lines[0].split("\t")
    return header, [dict(zip(header, x.split("\t"))) for x in lines[1:]]


def edit_counts(dst, fn, src=None, extra=()):
    """A copy of counts_fx.tsv: fn(row dict) -> row dict or None (drop); extra rows appended."""
    header, data = read_tsv_rows(src or fx("counts_fx.tsv"))
    out = [x for x in (fn(dict(r)) for r in data) if x is not None]
    return write_tsv(dst, header, out + list(extra))


def count_row(engine, bench, run, db, file, level, accepted, entrapment=0, combined=0.0, te=1.0):
    return {"engine": engine, "benchmark": bench, "run": run, "database": db, "file": file, "level": level,
            "class": "all", "q_value": "0.01", "accepted": accepted, "entrapment": entrapment,
            "lower_bound_fdp": combined, "combined_fdp": combined, "paired_fdp": "NA",
            "entrapment_target_not_accepted": "NA", "entrapment_above_target": "NA", "te_ratio": te}


class Quiet(unittest.TestCase):
    """overtuning.py leaves its input files to the garbage collector (OT:92, 102): no ResourceWarning noise."""
    def setUp(self):
        warnings.simplefilter("ignore", ResourceWarning)


class TempDir(Quiet):
    def setUp(self):
        super().setUp()
        self.tmp = tempfile.mkdtemp(prefix="ids_test_")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def path(self, name):
        return os.path.join(self.tmp, name)


class FakeUnit:
    def __init__(self, name):
        self.name, self.is_decision = name, False


_BASE = None


def base():
    """ids.build on the base fixture, built once (no output folder)."""
    global _BASE
    if _BASE is None:
        _BASE = built()
    return _BASE


# ---------------------------------------------------------------- T3 summary level
class TestT3Summary(Quiet):
    def test_t3_equal_weight_run_weighted_sums(self):
        def entry(name, p, c):
            return {"unit": FakeUnit(name), "p": p, "c": c, "ratio": p / c, "used": True, "reason": None}
        a = ids._dataset([entry("a1", 1210, 1000), entry("a2", 2000, 2000)])
        b = ids._dataset([entry("b1", 900, 1000)])
        self.assertAlmostEqual(a["gmean"], 1.1, places=12)
        self.assertAlmostEqual(b["gmean"], 0.9, places=12)
        s = ids._scope([("A", a), ("B", b)])
        self.assertAlmostEqual(s["equal_weight"], math.sqrt(0.99), places=12)
        self.assertAlmostEqual(s["equal_weight"], 0.994987, places=6)
        self.assertAlmostEqual(s["run_weighted"], 1.089 ** (1 / 3), places=12)
        self.assertAlmostEqual(s["run_weighted"], 1.028828, places=6)
        self.assertAlmostEqual(s["sum_ratio"], 4110 / 4000, places=12)
        self.assertEqual((s["n_datasets"], s["n_runs"], s["dropped"]), (2, 3, []))

    def test_t3_dropped_dataset_and_empty_scope(self):
        d = ids._dataset([{"unit": FakeUnit("x"), "p": 5, "c": 0, "ratio": T.Missing("zero"), "used": False,
                           "reason": "sage:zero"}])
        self.assertTrue(d["note"].startswith("dropped"))
        s = ids._scope([("X", d)])
        self.assertEqual((s["n_datasets"], s["dropped"]), (0, ["X"]))
        self.assertEqual(s["equal_weight"], T.Missing("empty"))

    def test_base_fixture_leads(self):
        ctx = base()
        r = one(ctx, "O02_pairs_summary", pair="prose_msfragger", level="psm", scope="heldout")
        self.assertAlmostEqual(r["lead_pct"], 10.0, places=9)
        self.assertEqual((r["n_datasets"], r["n_runs"]), (10, 11))  # astral_250pg: 2 runs plus the decision run
        self.assertEqual(number(ctx, "ids.heldout.psm.msfragger.lead").main_text_allowed, "yes")
        self.assertEqual(number(ctx, "ids.tuning.psm.msfragger.lead").main_text_allowed, "no")
        self.assertEqual(number(ctx, "ids.heldout_grade_a.psm.msfragger.lead").main_text_allowed, "no")
        self.assertEqual(number(ctx, "three.heldout.psm.prose_sage.lead").main_text_allowed, "yes")


# ---------------------------------------------------------------- T4 zero count
class TestT4Zero(TempDir):
    def test_t4_sage_zero_on_pxd011695_hcd(self):
        ctx = built(out=self.tmp)
        r = one(ctx, "O02_pairs_runs", pair="prose_sage", level="psm", unit="pxd011695_HCD_r1")
        self.assertEqual((r["used"], r["reason"], r["ratio"]), (False, "sage:zero", T.Missing("zero")))
        d = one(ctx, "O02_pairs_datasets", pair="prose_sage", level="psm", group="pxd011695_HCD")
        self.assertEqual(d["n_used"], 0)
        self.assertTrue(d["note"].startswith("dropped"))
        self.assertTrue(T.is_missing(d["gmean"]))
        s = one(ctx, "O02_pairs_summary", pair="prose_sage", level="psm", scope="heldout")
        self.assertEqual((s["n_datasets"], s["dropped_datasets"]), (9, "pxd011695_HCD"))
        m = one(ctx, "O02_pairs_summary", pair="prose_msfragger", level="psm", scope="heldout")
        self.assertEqual(m["n_datasets"], 10)
        self.assertEqual(one(ctx, "O01_ids_runs", unit="pxd011695_HCD_r1", engine="sage", level="psm")["note"], "zero")
        entry = ctx.shared["overtuning"]["psm"]
        self.assertEqual(entry["n_h"], {"msfragger": 10, "sage": 9})
        with open(self.path("sentence_overtuning_psm.txt"), encoding="utf-8") as f:
            text = f.read()
        self.assertIn("On the 10 (for Sage 9) held-out tryptic datasets", text)
        self.assertEqual(number(ctx, "overtuning.psm.n_h_sage").value, 9)


# ---------------------------------------------------------------- T5 failed search
class TestT5Failed(Quiet):
    def test_t5_sage_failed_memory(self):
        ctx = base()
        for level in ("psm", "peptide"):
            r = one(ctx, "O02_pairs_runs", pair="prose_sage", level=level, unit="pxd058436_DN05")
            self.assertEqual((r["used"], r["reason"]), (False, "sage:failed_memory"))
            r = one(ctx, "O02_pairs_runs", pair="prose_msfragger", level=level, unit="pxd058436_DN05")
            self.assertEqual((r["used"], r["reason"]), (True, ""))
            self.assertEqual(rows(ctx, "O03_three_runs", unit="pxd058436_DN05", level=level), [])
            s = one(ctx, "O09_immuno_samples", sample="pxd058436_DN05", level=level)
            self.assertEqual(s["sage"], T.Missing("failed_memory"))
            self.assertTrue(s["sage_status"].startswith("failed_memory"))
            self.assertEqual(s["ratio_prose_sage"], T.Missing("failed_memory"))
            d = one(ctx, "O09_immuno_datasets", group="pxd058436_classI", level=level, pair="prose_sage")
            self.assertEqual(d["n_used"], 0)
            d = one(ctx, "O09_immuno_datasets", group="pxd058436_classI", level=level, pair="prose_msfragger")
            self.assertEqual(d["n_used"], 1)  # DN13 is the decision sample


# ---------------------------------------------------------------- T6 engine missing a run (bycz)
class TestT6NotRunByDesign(Quiet):
    def test_t6_sage_bycz(self):
        ctx = base()
        g = one(ctx, "O01_ids_groups", group="pxd011695_ETciD", level="psm", set="expected")
        self.assertEqual(g["sum_sage"], T.Missing("not_in_set"))
        self.assertEqual((g["sum_prose"], g["sum_msfragger"]), (15400, 14000))
        self.assertIn("sage not expected", g["note"])
        self.assertNotIn("not expected", one(ctx, "O01_ids_groups", group="velos", level="psm", set="expected")["note"])
        r = one(ctx, "O08_electron_runs", unit="pxd011695_ETciD_r1", level="psm")
        self.assertTrue(r["sage_status"].startswith("not_run_by_design"))
        self.assertAlmostEqual(r["ratio"], 1.1, places=12)
        self.assertEqual(rows(ctx, "O03_three_runs", unit="pxd011695_ETciD_r1"), [])
        p = one(ctx, "O14_coverage_paper", engine="sage", kind="electron")
        self.assertEqual((p["expected"], p["counted"], p["not_run_by_design"]), (0, 0, 1))


# ---------------------------------------------------------------- T7 decision run
SUMMARY_TABLES = ("O01_ids_groups", "O02_pairs_datasets", "O02_pairs_summary", "O03_three_datasets",
                  "O03_three_summary", "O04_overtuning_psm_datasets", "O04_overtuning_psm_sides",
                  "O06_overtuning_psm_loo", "O04_overtuning_peptide_sides")


class TestT7Decision(TempDir):
    def _summaries(self, ctx):
        nums = {n.key: (n.text, n.value) for n in ctx.numbers
                if n.key.startswith(("ids.", "three.", "overtuning.", "lowmem."))}
        return {t: ctx.results[t] for t in SUMMARY_TABLES}, nums

    def test_t7_decision_row_changes_nothing(self):
        ref = self._summaries(base())

        def triple(r):
            if r["run"] == "astral250pg_A2" and r["benchmark"] == "per_file":
                r["accepted"] = str(int(r["accepted"]) * 3 + 7)
            return r
        changed = built(counts=edit_counts(self.path("counts.tsv"), triple))
        self.assertEqual(self._summaries(changed), ref)
        where = dict(unit="astral250pg_A2", engine="prose", level="psm")
        self.assertNotEqual(one(changed, "O01_ids_runs", **where)["accepted"],
                            one(base(), "O01_ids_runs", **where)["accepted"])

    def test_t7_without_the_decision_row(self):
        ref = self._summaries(base())
        counts = edit_counts(self.path("counts.tsv"),
                             lambda r: None if r["run"] == "astral250pg_A2" else r)
        header, cov = read_tsv_rows(fx("coverage_fx.tsv"))
        coverage = write_tsv(self.path("coverage.tsv"), header, [r for r in cov if r["run"] != "astral250pg_A2"])
        without = built(counts=counts, coverage=coverage)
        self.assertEqual(self._summaries(without), ref)


# ---------------------------------------------------------------- T8, T9 over-tuning
def overtuning_counts(dst, prose_of):
    """counts_fx with every tryptic per_file td count set to 10000 for MSFragger and Sage and prose_of(group) * 10000
    for ProSE (both levels)."""
    ctx = base()

    def edit(r):
        u = ctx.unit_by_name.get(r["run"])
        if u is None or r["benchmark"] != "per_file" or r["database"] != u.td or u.kind not in ("tuning", "heldout"):
            return r
        r["accepted"] = str(round(prose_of(u.group) * 10000)) if r["engine"] == "prose" else "10000"
        return r
    return edit_counts(dst, edit)


class TestT8Overtuning(TempDir):
    def test_t8_version_b_astral(self):
        counts = overtuning_counts(self.path("counts.tsv"), lambda g: 1.4 if g == "astral" else 1.1)
        ds, ot_rows, notes = OT.load(fx("runs_fx.tsv"), counts, "psm")
        out = os.path.join(self.tmp, "summary")
        ctx = built(counts=counts, out=out)
        e = ctx.shared["overtuning"]["psm"]
        lt = 100 * (math.exp((6 * math.log(1.1) + math.log(1.4)) / 7) - 1)
        self.assertAlmostEqual(lt, 13.856, places=3)
        for eng in OT.ENGINES:
            self.assertAlmostEqual(e["full"][eng][0], lt, places=9)
            self.assertAlmostEqual(e["full"][eng][1], 10.0, places=9)
            self.assertAlmostEqual(e["full"][eng][2], lt - 10.0, places=9)
        self.assertEqual((e["version"], e["best"]), ("b", "astral"))
        # the independent path (O2, package code) against OT.load: dataset values within 1e-12, the run ratio
        # strings equal, the side leads within 1e-9 points (the comparisons of C6 a, b, d)
        self.assertEqual(e["ds"], ds)
        for eng in OT.ENGINES:
            self.assertEqual(sorted(ds[eng]), sorted(design.TUNING + design.HELDOUT))
            for g, v in ds[eng].items():
                mine = one(ctx, "O02_pairs_datasets", pair="prose_" + eng, level="psm", group=g)["gmean"]
                self.assertLessEqual(abs(mine - v) / v, 1e-12)
            for scope, i in (("tuning", 0), ("heldout", 1)):
                lead = one(ctx, "O02_pairs_summary", pair="prose_" + eng, level="psm", scope=scope)["lead_pct"]
                self.assertLessEqual(abs(lead - e["full"][eng][i]), 1e-9)
                self.assertEqual(number(ctx, f"ids.{scope}.psm.{eng}.lead").value, lead)
        mine = {(OT.NAMES[r["pair"].split("_")[1]], "tuning" if r["kind"] == "tuning" else "heldout", r["group"],
                 r["unit"]): f"{r['prose'] / r['comparator']:.6f}"
                for r in ctx.results["O02_pairs_runs"] if r["level"] == "psm" and r["used"]
                and r["kind"] in ("tuning", "heldout")}
        self.assertEqual(mine, {r[:4]: r[4] for r in ot_rows})
        self.assertEqual([tuple(r.values()) for r in ctx.results["O04_overtuning_psm_runs"]], ot_rows)
        with open(os.path.join(out, "sentence_overtuning_psm.txt"), encoding="utf-8") as f:
            text = f.read().rstrip("\n")
        self.assertEqual(text, OT.sentence(e["version"], e["best"], e["full"], e["loo"], e["n_t"], e["n_h"], "PSMs"))
        self.assertIn("one dataset, astral (without it", text)
        with open(os.path.join(out, "sentence_overtuning_psm_display.txt"), encoding="utf-8") as f:
            display = f.read()
        self.assertIn(f"one dataset, {design.display('astral')} (without it", display)
        self.assertEqual(number(ctx, "overtuning.psm.version").value, "b")
        self.assertEqual(number(ctx, "overtuning.psm.dataset_b").value, "astral")
        self.assertEqual(number(ctx, "overtuning.psm.dataset_b_display").value, "Astral")
        self.assertEqual(number(ctx, "overtuning.psm.lt_msfragger").text, "+13.9")
        self.assertEqual(number(ctx, "overtuning.psm.lh_sage").text, "10.0")
        self.assertEqual(number(ctx, "overtuning.psm.gap_sage").text, "+3.9")
        sides = one(ctx, "O04_overtuning_psm_sides", comparator="msfragger")
        self.assertIs(sides["within_margin"], False)
        loo = one(ctx, "O06_overtuning_psm_loo", left_out="astral")
        self.assertIs(loo["named_in_b"], True)
        self.assertIs(loo["both_within_margin"], True)
        self.assertEqual(len(ctx.results["O04_overtuning_psm_runs"]), len(ot_rows))
        with open(os.path.join(out, "tables", "O04_overtuning_psm.stdout.txt"), encoding="utf-8") as f:
            self.assertIn("version b (astral)", f.read())


class TestT9LooTie(Quiet):
    def test_t9_first_in_table_order(self):
        tmp = tempfile.mkdtemp(prefix="ids_test_")
        try:
            counts = overtuning_counts(os.path.join(tmp, "counts.tsv"),
                                       lambda g: 1.25 if g in ("velos", "lumos_tmt") else 1.1)
            ctx = built(counts=counts)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        e = ctx.shared["overtuning"]["psm"]
        self.assertEqual((e["version"], e["best"]), ("b", "velos"))
        self.assertEqual(e["loo"]["velos"], e["loo"]["lumos_tmt"])  # an exact tie
        self.assertIs(one(ctx, "O06_overtuning_psm_loo", left_out="velos")["named_in_b"], True)
        tie = one(ctx, "O06_overtuning_psm_loo", left_out="lumos_tmt")
        self.assertEqual((tie["named_in_b"], tie["both_within_margin"]), (False, True))
        self.assertEqual(OT.rule(e["ds"])[:2], ("b", "velos"))


# ---------------------------------------------------------------- T25 references, O9, O24
class TestT25References(TempDir):
    def ref_copy(self, edit=None, drop=None, dup=None):
        header, data = read_tsv_rows(REF_FX)
        out = []
        for i, r in enumerate(data):
            if drop is not None and drop(r):
                continue
            if edit is not None:
                r = edit(dict(r))
            out.append(r)
            if dup is not None and dup(r):
                out.append(dict(r))
        return write_tsv(self.path("reference.tsv"), header, out)

    def test_t25_mapping_and_local_flag(self):
        ctx = built(references=REF_FX)
        refs = ctx.shared["references"]
        self.assertEqual(list(refs["immuno"]["pxd058436_DN05"]), ["mhcquant", "fragpipe", "peaks"])
        self.assertEqual(refs["immuno"]["pxd058436_DN13"]["peaks"]["value"], 10900)
        p19 = refs["immuno"]["pxd019643_DN05"]
        self.assertEqual(list(p19), ["mhcquant"])
        self.assertEqual((p19["mhcquant"]["value"], p19["mhcquant"]["flag"]), (3800, "local"))
        self.assertEqual(ids.lacking_tools(ctx, refs), [])
        s = one(ctx, "O09_immuno_samples", sample="pxd019643_DN05", level="peptide")
        self.assertEqual((s["mhcquant"], s["fdr_note"]), (3800, "local"))
        self.assertEqual(s["fragpipe"], T.Missing("not_published"))
        s = one(ctx, "O09_immuno_samples", sample="pxd058436_DN05", level="peptide")
        self.assertEqual((s["mhcquant"], s["fragpipe"], s["peaks"], s["fdr_note"]), (5100, 4600, 5000, ""))
        self.assertIn("mhcquant: same FDR level", s["comparability"])
        s = one(ctx, "O09_immuno_samples", sample="pxd058436_DN05", level="psm")
        self.assertEqual(s["mhcquant"], T.Missing("peptide_level_only"))

    def test_t25_unknown_level_stops(self):
        path = self.ref_copy(edit=lambda r: dict(r, level="PSMs: unique sequences")
                             if r["engine"].startswith("FragPipe") and "DN13" in r["scope"] else r)
        ctx = make_ctx(references=path)
        with self.assertRaises(T.ValidationStop) as cm:
            ids.build(ctx)
        self.assertIn("column level", str(cm.exception))
        self.assertIn("line 6", str(cm.exception))

    def test_t25_unknown_engine_stops(self):
        path = self.ref_copy(edit=lambda r: dict(r, engine="Comet 2024") if r["engine"].startswith("PEAKS") else r)
        with self.assertRaises(T.ValidationStop) as cm:
            ids.build(make_ctx(references=path))
        self.assertIn("column engine", str(cm.exception))

    def test_t25_duplicate_stops(self):
        path = self.ref_copy(dup=lambda r: r["engine"].startswith("MHCquant 1.5.1"))
        with self.assertRaises(T.ValidationStop) as cm:
            ids.build(make_ctx(references=path))
        self.assertIn("one row per (sample, tool)", str(cm.exception))
        path = self.ref_copy(dup=lambda r: r["engine"].startswith("MS-GF+ v2018"))
        with self.assertRaises(T.ValidationStop):
            ids.build(make_ctx(references=path))

    def test_t25_sample_without_its_tools_fails(self):
        path = self.ref_copy(drop=lambda r: r["engine"].startswith("PEAKS") and "DN05" in r["scope"])
        ctx = built(references=path, out=self.tmp)
        self.assertEqual(ids.lacking_tools(ctx, ctx.shared["references"]), ["pxd058436_DN05:peaks"])
        with open(os.path.join(self.tmp, "tables", "O09_immuno_samples.tsv"), encoding="utf-8") as f:
            self.assertIn("published values missing (1, C21): pxd058436_DN05:peaks", f.readline())
        self.assertEqual(one(ctx, "O09_immuno_samples", sample="pxd058436_DN05", level="peptide")["peaks"],
                         T.Missing("not_published"))

    def test_c21_data_without_reference_file(self):
        self.assertEqual(base().shared["references"], None)
        self.assertEqual(len(ids.lacking_tools(base(), None)), 7)  # 2 samples x 3 tools + 1 x 1

    def test_o24_iprg2015(self):
        ctx = built(references=REF_FX)
        rs = rows(ctx, "O24_external_references", unit="iprg2015_r1")
        self.assertEqual(len(rs), 3)  # PSMs: DeMix and OpenMS; peptides: DeMix; mean and ProSE rows ignored
        psm = rows(ctx, "O24_external_references", unit="iprg2015_r1", level="psm")
        self.assertEqual([(r["tool"], r["ref_value"]) for r in psm], [("msgf_demix", 29000), ("msgf_openms", 18900)])
        self.assertEqual((psm[0]["prose"], psm[0]["sage"], psm[0]["msfragger"]), (17050, 14725, 15500))
        pep = one(ctx, "O24_external_references", unit="iprg2015_r1", level="peptide")
        self.assertEqual((pep["tool"], pep["ref_value"], pep["ref_level"]),
                         ("msgf_demix", 20000, "peptides: unique unmodified sequences, I=L"))
        self.assertFalse(any(n.key.startswith("ref") for n in ctx.numbers))
        none = rows(base(), "O24_external_references")
        self.assertEqual(len(none), 2)
        self.assertEqual(none[0]["ref_value"], T.Missing("no_reference_file"))


# ---------------------------------------------------------------- O9 and O10 counts part
class TestO9Immuno(Quiet):
    def test_o9_samples(self):
        ctx = base()
        self.assertEqual(len(ctx.results["O09_immuno_samples"]), 6)  # 3 samples x 2 levels
        s = one(ctx, "O09_immuno_samples", sample="pxd058436_DN05", level="peptide")
        self.assertEqual((s["prose_main"], s["msfragger"], s["main_arrangement"]), (5866, 5333, "per_file"))
        self.assertEqual(s["donor_tissue"], "DN05")
        self.assertEqual(s["prose_other"], T.Missing("no_coverage"))  # per_file_mode_joint not run in the fixture
        self.assertAlmostEqual(s["ratio_prose_msfragger"], 5866 / 5333, places=12)
        d = one(ctx, "O09_immuno_samples", sample="pxd058436_DN13", level="psm")
        self.assertEqual(d["role"], "decision")
        self.assertIn("decision sample", d["note"])
        g = one(ctx, "O09_immuno_datasets", group="pxd058436_classI", level="peptide", pair="prose_other_main")
        self.assertEqual(g["n_used"], 0)
        self.assertAlmostEqual(number(ctx, "ids.immuno.pxd058436_classi.peptide.msfragger.lead").value,
                               100 * (5866 / 5333 - 1), places=9)
        self.assertEqual(number(ctx, "ids.immuno.pxd058436_classi.peptide.sage.n_samples").value, 0)
        # SPEC O9: "PSM goes into the table only": no PSM-level immuno key, the PSM rows stay in the tables
        self.assertEqual([n.key for n in ctx.numbers if n.key.startswith("ids.immuno.") and ".psm." in n.key], [])
        self.assertTrue(rows(ctx, "O09_immuno_datasets", level="psm"))
        self.assertTrue(all(n.main_text_allowed == "yes" and n.source_side == "heldout"
                            for n in ctx.numbers if n.key.startswith("ids.immuno.")))

    def test_o10_counts_part(self):
        ctx = base()
        o10 = ctx.shared["O10_counts"]
        self.assertEqual([r["sample"] for r in o10], ["pxd058436_DN05", "pxd058436_DN13", "pxd019643_DN05"])
        self.assertTrue(all(r["identical"] is True for r in o10))
        self.assertIs(number(ctx, "lowmem.identical_all").value, True)

    def test_o10_different_counts(self):
        tmp = tempfile.mkdtemp(prefix="ids_test_")
        try:
            def edit(r):
                if r["benchmark"] == "per_file_low_memory" and r["run"] == "pxd019643_DN05" and r["level"] == "psm":
                    r["accepted"] = "18699"
                return r
            ctx = built(counts=edit_counts(os.path.join(tmp, "counts.tsv"), edit))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        r = [x for x in ctx.shared["O10_counts"] if x["sample"] == "pxd019643_DN05"][0]
        self.assertIs(r["identical"], False)
        self.assertIs(number(ctx, "lowmem.identical_all").value, False)


# ---------------------------------------------------------------- O8 FDP columns: FDP as O11 (fdp.run_of)
class TestO8Electron(Quiet):
    def test_o8_fdp_without_fdp_build(self):
        """The O8 FDP columns are FDP as O11 (fdp.run_of), also when fdp.build did not run (--only electron): the
        mean over the three shuffled realisations of counts_fx.tsv, all shared."""
        ctx = base()
        self.assertNotIn("O11_fdp_runs", ctx.results)
        r = one(ctx, "O08_electron_runs", unit="pxd011695_ETciD_r1", level="psm")
        for e in ("prose", "msfragger"):
            vals = [ctx.fdp(e, "pxd011695_ETciD_r1", f"pxd011695_mouse_entrap_s{i}_td", "psm") for i in (1, 2, 3)]
            self.assertAlmostEqual(r[f"fdp_{e}_mean"], math.fsum(vals) / 3, places=12)
            self.assertEqual(r[f"fdp_{e}_n"], 3)
        self.assertEqual(r["fdp_shared_n"], 3)
        self.assertAlmostEqual(number(ctx, "ids.electron.pxd011695_etcid.psm.msfragger.lead").value, 10.0, places=9)

    def test_o8_equals_o11_rows(self):
        """With fdp.build first (the order of summarize.py), O8 equals the O11_fdp_runs rows of the same runs."""
        ctx = make_ctx()
        fdp.build(ctx)
        ids.build(ctx)
        o11 = {(x["engine"], x["unit"], x["level"]): x for x in ctx.results["O11_fdp_runs"]
               if x["design"] == "shuffled"}
        for r in ctx.results["O08_electron_runs"]:
            for e in ("prose", "msfragger"):
                x = o11[(e, r["unit"], r["level"])]
                self.assertEqual((r[f"fdp_{e}_mean"], r[f"fdp_{e}_sd"], r[f"fdp_{e}_n"]),
                                 (x["mean_own"], x["sd_own"], x["n_own"]))
                self.assertEqual(r["fdp_shared_n"], x["n_shared"])
        d = one(ctx, "O08_electron_datasets", group="pxd011695_ETciD", level="psm")
        x = o11[("prose", "pxd011695_ETciD_r1", "psm")]
        self.assertEqual((d["fdp_prose_mean_of_shared"], d["fdp_n_runs"]), (x["mean_shared"], 1))


# ---------------------------------------------------------------- O14 coverage
class TestO14Coverage(Quiet):
    def test_o14_rows_and_paper_table(self):
        ctx = base()
        self.assertEqual(len(ctx.results["O14_coverage"]), len(ctx.coverage) + len(ctx.coverage_outside))
        first, last = ctx.results["O14_coverage"][0], ctx.results["O14_coverage"][-1]
        self.assertEqual((first["benchmark"], first["kind"], first["unit"], first["db_design"]),
                         ("per_file", "tuning", "velos_r1", "td"))
        self.assertEqual(last["benchmark"], "scaling")
        n_kind = {}
        for u in ctx.units:
            n_kind[u.kind] = n_kind.get(u.kind, 0) + 1
        for r in ctx.results["O14_coverage_paper"]:
            total = sum(r[c] for c in ("counted", "failed_memory", "failed", "not_run_by_design", "not_run", "other"))
            self.assertEqual(total, n_kind[r["kind"]], r)
        sage = one(ctx, "O14_coverage_paper", engine="sage", kind="immuno")
        self.assertEqual((sage["expected"], sage["counted"], sage["failed_memory"]), (3, 2, 1))
        self.assertEqual(number(ctx, "coverage.sage.failed_memory").value, 1)
        self.assertEqual(number(ctx, "coverage.sage.not_run_by_design").value, 1)
        self.assertEqual(number(ctx, "coverage.prose.counted").value, len(ctx.units))
        summary = ctx.results["O14_coverage_summary"]
        self.assertEqual(sum(r["n_searches"] for r in summary), len(ctx.results["O14_coverage"]))


# ---------------------------------------------------------------- T27 empty sets (W_node)
class TestT27Empty(Quiet):
    def test_t27_wnode(self):
        ctx = built(counts=fx("counts_wnode_fx.tsv"), coverage=fx("coverage_wnode_fx.tsv"),
                    timings=fx("timings_wnode_fx.tsv"))
        for table in ("O02_pairs_summary", "O03_three_summary"):
            self.assertTrue(ctx.results[table])
            for r in ctx.results[table]:
                self.assertEqual((r["equal_weight"], r["run_weighted"], r["sum_ratio"], r["n_datasets"]),
                                 (T.Missing("empty"), T.Missing("empty"), T.Missing("empty"), 0), r)
        self.assertEqual(len([m for lv, m in checks(ctx, "O04", "INFO") if "O4-O7 skipped" in m]), 2)
        self.assertFalse(any(t.startswith(("O04", "O06")) for t in ctx.results))
        self.assertEqual(number(ctx, "overtuning.psm.version").value, T.Missing("skipped"))
        self.assertEqual(number(ctx, "ids.heldout.psm.msfragger.lead").value, T.Missing("empty"))
        self.assertTrue(ctx.shared["overtuning"]["psm"]["skipped"])
        self.assertEqual([lv for lv, _, _ in ctx.report.lines if lv != "INFO"], [])  # the verdicts are checks.py's


# ---------------------------------------------------------------- smoke layout, --design none
class TestSmoke(Quiet):
    def test_design_none(self):
        ctx = built(runs=fx("runs_smoke_fx.tsv"), counts=fx("counts_smoke_fx.tsv"),
                    coverage=fx("coverage_smoke_fx.tsv"), timings=fx("timings_smoke_fx.tsv"), design="none")
        self.assertEqual(ctx.results["O02_pairs_summary"], [])
        self.assertTrue(ctx.results["O01_ids_runs"])
        self.assertFalse(any(n.key.startswith(("ids.", "three.", "overtuning.")) for n in ctx.numbers))
        self.assertEqual([lv for lv, _ in checks(ctx, "O04")], ["INFO"])
        self.assertNotIn("overtuning", ctx.shared)


# ---------------------------------------------------------------- T35 outside the design, rule11b
class TestT35Outside(TempDir):
    def test_t35_outside_design_row(self):
        extra = [count_row("prose", "per_file", "hfx_r1", "hye_other_td", "hfx_r1.count.idXML", lv, 99999)
                 for lv in ("psm", "peptide")]
        counts = edit_counts(self.path("counts.tsv"), lambda r: r, extra=extra)
        header, cov = read_tsv_rows(fx("coverage_fx.tsv"))
        cov.append({"engine": "prose", "benchmark": "per_file", "run": "hfx_r1", "database": "hye_other_td",
                    "status": "ok", "counted": "yes"})
        ctx = built(counts=counts, coverage=write_tsv(self.path("coverage.tsv"), header, cov))
        self.assertEqual(ctx.results["O01_ids_runs"], base().results["O01_ids_runs"])
        self.assertEqual(ctx.results["O02_pairs_summary"], base().results["O02_pairs_summary"])
        r = one(ctx, "O14_coverage", unit="hfx_r1", database="hye_other_td")
        self.assertEqual((r["db_design"], r["engine"], r["group"]), ("outside_design", "prose", "hfx"))
        self.assertEqual(len(ctx.results["O14_coverage"]), len(base().results["O14_coverage"]) + 1)

    def test_t35_rule11b_pair_goes_to_o9b(self):
        runs11b = write_tsv(self.path("runs_11b.tsv"), ["id", "db", "entrap", "ref", "sample"],
                            [{"id": "DN13_r1", "db": "pxd058436", "entrap": "pxd058436_classI_entrap_td.fasta",
                              "ref": "-", "sample": "pxd058436_DN13"}])
        ent = "pxd058436_classI_entrap_td"
        f = "pooled.count.idXML"
        extra = []
        for lv in ("psm", "peptide"):
            extra.append(count_row("prose", "per_file", "pxd058436_DN13", ent, f, lv, 6000, 30, 0.01, 1.0))
            extra.append(count_row("prose", "per_file_mode_joint", "pxd058436_DN13", "pxd058436_td", f, lv, 6500))
            extra.append(count_row("prose", "per_file_mode_joint", "pxd058436_DN13", ent, f, lv, 6500, 33, 0.0102, 1.0))
        counts = edit_counts(self.path("counts.tsv"), lambda r: r, extra=extra)
        header, cov = read_tsv_rows(fx("coverage_fx.tsv"))
        for bench, db in (("per_file", ent), ("per_file_mode_joint", "pxd058436_td"), ("per_file_mode_joint", ent)):
            cov.append({"engine": "prose", "benchmark": bench, "run": "pxd058436_DN13", "database": db,
                        "status": "ok", "counted": "yes"})
        ctx = built(counts=counts, coverage=write_tsv(self.path("coverage.tsv"), header, cov), runs_11b=runs11b)
        self.assertEqual(len(ctx.counts_rule11b), 4)
        self.assertEqual(ctx.results["O02_pairs_summary"], base().results["O02_pairs_summary"])
        pf = one(ctx, "O09b_rule11b", pool="pxd058436_DN13", arrangement="per_file")
        jt = one(ctx, "O09b_rule11b", pool="pxd058436_DN13", arrangement="joint")
        self.assertEqual((pf["benchmark"], jt["benchmark"]), ("per_file", "per_file_mode_joint"))
        self.assertEqual((pf["peptides_td"], jt["peptides_td"]), (6050, 6500))
        se = math.sqrt(30) * 2 / 6000
        self.assertAlmostEqual(pf["fdp_poisson_se"], se, places=12)
        self.assertAlmostEqual(pf["fdp_limit"], 0.01 + se, places=12)
        self.assertEqual((jt["more_peptides"], jt["fdp_ok"], jt["chosen"]), (True, True, "joint"))
        self.assertIs(jt["equals_pooled_arrangement"], False)  # the fixture's arrangement is per_file
        self.assertEqual(ctx.shared["rule11b_chosen"], "joint")
        # one condition fails -> per_file stays
        bad = [dict(r, combined_fdp=0.02, lower_bound_fdp=0.02) if r["benchmark"] == "per_file_mode_joint"
               and r["database"] == ent else r for r in extra]
        counts2 = edit_counts(self.path("counts2.tsv"), lambda r: r, extra=bad)
        ctx2 = built(counts=counts2, coverage=self.path("coverage.tsv"), runs_11b=runs11b)
        jt = one(ctx2, "O09b_rule11b", pool="pxd058436_DN13", arrangement="joint")
        self.assertEqual((jt["fdp_ok"], jt["chosen"]), (False, "per_file"))


# ---------------------------------------------------------------- O23 and the written files
class TestFiles(TempDir):
    def test_tables_written_and_keys_unique(self):
        ctx = built(out=self.tmp, references=REF_FX)
        for name in ctx.results:
            self.assertTrue(os.path.exists(os.path.join(self.tmp, "tables", name + ".tsv")), name)
        keys = [n.key for n in ctx.numbers]
        self.assertEqual(len(keys), len(set(keys)))
        g = one(ctx, "O23_datasets", group="velos")
        self.assertEqual((g["n_runs"], g["entrap_design"], g["ms2_total"]),
                         (1, "natural + shuffled s1-s3", T.Missing("no_mzml_counts")))
        self.assertEqual(len(ctx.results["O23_runs"]), len(ctx.runs))
        self.assertEqual([lv for lv, _, _ in ctx.report.lines if lv != "INFO"], [])


# ---------------------------------------------------------------- O25 a further arm
class TestO25FurtherArm(TempDir):
    def test_o25_arm_outside_arms(self):
        f = "hfx_r1.count.idXML"
        extra = []
        for lv, n_td, n_s1 in (("psm", 12342, 12000), ("peptide", 4100, 4000)):
            extra.append(count_row("prose", "per_file_foo", "hfx_r1", "hye_td", f, lv, n_td))
            extra.append(count_row("prose", "per_file_foo", "hfx_r1", "hye_entrap_s1_td", f, lv, n_s1, 60, 0.0105, 1.0))
            extra.append(count_row("msfragger", "per_file_foo", "hfx_r1", "hye_td", f, lv, 11000))
        counts = edit_counts(self.path("counts.tsv"), lambda r: r, extra=extra)
        header, cov = read_tsv_rows(fx("coverage_fx.tsv"))
        for e, db in (("prose", "hye_td"), ("prose", "hye_entrap_s1_td"), ("msfragger", "hye_td")):
            cov.append({"engine": e, "benchmark": "per_file_foo", "run": "hfx_r1", "database": db, "status": "ok",
                        "counted": "yes"})
        coverage = write_tsv(self.path("coverage.tsv"), header, cov)
        main = "/w/bin/ProSE -ini /w/p.ini -in /w/mzml/hfx_r1.mzML -database /w/db/hye_td.fasta -out " \
               "/w/out/prose/{b}/hfx_r1/hye_td/hfx_r1.idXML -threads 16"
        with open(self.path("commands.log"), "w", encoding="utf-8") as fh:
            fh.write(main.format(b="per_file") + " > /w/out/prose/per_file/hfx_r1/hye_td/all.r1.log 2>&1\n")
            fh.write("# msfragger hfx_r1 hye_td.fasta: extra settings calibrate_mass=2\n")
            fh.write("/w/bin/fragger.sh /w/out/msfragger/per_file_foo/hfx_r1/hye_td/fragger.params > "
                     "/w/out/msfragger/per_file_foo/hfx_r1/hye_td/search.r1.log 2>&1\n")
            fh.write(main.format(b="per_file_foo") + " -Search:foo 1 > /w/out/prose/per_file_foo/hfx_r1/hye_td/"
                     "all.r1.log 2>&1\n")
        ctx = built(work=self.tmp, counts=counts, coverage=coverage, timings=fx("timings_fx.tsv"))
        self.assertEqual(ctx.unknown_tags, ["foo"])
        rs = ctx.results["O25_arm_foo"]
        self.assertEqual([(r["engine"], r["level"]) for r in rs],
                         [("prose", "psm"), ("prose", "peptide"), ("msfragger", "psm"), ("msfragger", "peptide")])
        p = one(ctx, "O25_arm_foo", engine="prose", level="psm")
        self.assertEqual((p["arm_accepted"], p["main_accepted"], p["fdp_n"], p["extra_settings"]),
                         (12342, 12100, 1, "-Search:foo 1"))
        self.assertAlmostEqual(p["ratio"], 12342 / 12100, places=12)
        self.assertEqual(p["fdp_arm_mean"], 0.0105)
        self.assertEqual(p["wall_arm_med_s"], T.Missing("no_timing_rows"))
        m = one(ctx, "O25_arm_foo", engine="msfragger", level="psm")
        self.assertEqual((m["extra_settings"], m["fdp_n"], m["fdp_arm_mean"]),
                         ("calibrate_mass=2", 0, T.Missing("empty")))
        d = one(ctx, "O25_arm_foo_datasets", engine="prose", group="hfx", level="psm")
        self.assertEqual((d["n_units"], d["n_used"], d["fdp_n_runs"]), (1, 1, 1))
        self.assertAlmostEqual(d["gmean_ratio"], 12342 / 12100, places=12)


class TestO25DeclaredArm(TempDir):
    def arm_inputs(self, with_arm=True):
        """counts and coverage: the fixtures plus, with_arm, the declared arm ion_index0 on the three Astral 250 pg
        runs (A2: td + s1; B1: td + s1-s3; B3: td + s1) and one search on an immunopeptidomics sample (outside the
        arm's kinds)."""
        header, cov = read_tsv_rows(fx("coverage_fx.tsv"))
        extra = []
        arm = {"astral250pg_A2": (20000, 6600, {"s1": 0.0090}),
               "astral250pg_B1": (21780, 7260, {"s1": 0.0100, "s2": 0.0100, "s3": 0.0100}),
               "astral250pg_B3": (24420, 8140, {"s1": 0.0200})}
        if with_arm:
            for run, (n_psm, n_pep, fdps) in arm.items():
                f = run + ".count.idXML"
                for lv, n in (("psm", n_psm), ("peptide", n_pep)):
                    extra.append(count_row("prose", "per_file_ion_index0", run, "hye_td", f, lv, n))
                    for s, fdp in fdps.items():
                        extra.append(count_row("prose", "per_file_ion_index0", run, f"hye_entrap_{s}_td", f, lv,
                                               n - 200, 80, fdp, 1.003))
                for db in ["hye_td"] + [f"hye_entrap_{s}_td" for s in fdps]:
                    cov.append({"engine": "prose", "benchmark": "per_file_ion_index0", "run": run, "database": db,
                                "status": "ok", "counted": "yes"})
            cov.append({"engine": "prose", "benchmark": "per_file_ion_index0", "run": "pxd058436_DN05",
                        "database": "pxd058436_td", "status": "ok", "counted": "no"})
        counts = edit_counts(self.path(f"counts{int(with_arm)}.tsv"), lambda r: r, extra=extra)
        coverage = write_tsv(self.path(f"coverage{int(with_arm)}.tsv"), header, cov)
        return counts, coverage

    def test_o25_declared_arm(self):
        # ion_index0 is in ARMS and TABLE_ARMS: O25 tables as for a further arm, but no unknown tag (no C3 WARN); a
        # row for every planned unit (kinds tuning, heldout, electron), searched or not; per dataset the decision run
        # astral250pg_A2 is shown per run but kept out of the geometric mean and of the FDP
        counts, coverage = self.arm_inputs()
        ctx = built(work=self.tmp, counts=counts, coverage=coverage, timings=fx("timings_fx.tsv"))
        self.assertIn("ion_index0", ctx.tags)
        self.assertNotIn("ion_index0", ctx.unknown_tags)
        planned = [u for u in ctx.units if u.kind in ("tuning", "heldout", "electron")]
        rs = ctx.results["O25_arm_ion_index0"]
        self.assertEqual({(r["engine"], r["unit"]) for r in rs},
                         {("prose", u.name) for u in planned} | {("prose", "pxd058436_DN05")})
        a2 = one(ctx, "O25_arm_ion_index0", unit="astral250pg_A2", level="psm")
        self.assertEqual((a2["role"], a2["arm_accepted"], a2["main_accepted"]), ("decision", 20000, 19250))
        h = one(ctx, "O25_arm_ion_index0", unit="hfx_r1", level="psm")
        self.assertEqual((h["arm_status"], h["fdp_n"]), (T.Missing("no_coverage"), 0))
        self.assertTrue(T.is_missing(h["arm_accepted"]))
        d = one(ctx, "O25_arm_ion_index0_datasets", engine="prose", group="astral_250pg", level="psm")
        self.assertEqual((d["n_units"], d["n_used"], d["fdp_n_runs"]), (2, 2, 2))
        self.assertAlmostEqual(d["gmean_ratio"], (1.1 * 1.2) ** 0.5, places=12)
        self.assertAlmostEqual(d["lead_pct"], 100 * ((1.1 * 1.2) ** 0.5 - 1), places=9)
        self.assertAlmostEqual(d["sum_ratio"], (21780 + 24420) / (19800 + 20350), places=12)
        # the mean of the run means (B1: 3 realisations at 0.010, B3: 1 at 0.020), not of the 4 (run, realisation)
        # pairs (0.0125)
        self.assertAlmostEqual(d["fdp_arm_mean"], 0.015, places=12)
        self.assertAlmostEqual(d["fdp_main_mean"], ((0.008175 + 0.008277 + 0.008379) / 3 + 0.008152) / 2, places=12)
        p = one(ctx, "O25_arm_ion_index0_datasets", engine="prose", group="astral_250pg", level="peptide")
        self.assertAlmostEqual(p["gmean_ratio"], (7260 / 6600 * 8140 / 6783) ** 0.5, places=12)
        hd = one(ctx, "O25_arm_ion_index0_datasets", engine="prose", group="hfx", level="psm")
        self.assertEqual((hd["n_units"], hd["n_used"], hd["fdp_n_runs"]), (1, 0, 0))
        self.assertIn("hfx_r1 arm:", hd["note"])
        groups = {r["group"] for r in ctx.results["O25_arm_ion_index0_datasets"]}
        self.assertEqual(groups, {u.group for u in planned} | {"pxd058436_classI"})
        # coverage check: 8 counted searches (A2 2, B1 4, B3 2) of the expected td + entrap of the planned units
        expected = sum(1 + len(u.entrap) for u in planned)
        info = [m for lv, m in checks(ctx, "O25", "INFO") if "per_file_ion_index0" in m]
        self.assertEqual(len(info), 1)
        self.assertIn(f"prose: 8 of {expected} td + entrapment searches counted over the {len(planned)} units", info[0])
        warns = [m for lv, m in checks(ctx, "O25", "WARN")]
        self.assertTrue(any(f"{expected - 8} of {expected}" in m and "velos_r1 hy_td" in m for m in warns), warns)
        self.assertTrue(any("outside its kinds" in m and "pxd058436_DN05" in m for m in warns), warns)
        # across datasets: astral_250pg is the only held-out tryptic dataset with runs of the arm
        s = one(ctx, "O25_arm_ion_index0_summary", pair="prose", level="psm", scope="heldout")
        self.assertEqual((s["tag"], s["n_datasets"], s["n_runs"]), ("ion_index0", 1, 2))
        self.assertAlmostEqual(s["equal_weight"], (1.1 * 1.2) ** 0.5, places=12)
        t = one(ctx, "O25_arm_ion_index0_summary", pair="prose", level="psm", scope="tuning")
        self.assertEqual(t["n_datasets"], 0)
        self.assertTrue(T.is_missing(t["equal_weight"]))
        k = number(ctx, "arm.ion_index0.prose.heldout.psm.lead")
        self.assertEqual((k.main_text_allowed, k.source_side, k.output), ("no", "heldout", "O25"))
        self.assertAlmostEqual(k.value, 100 * ((1.1 * 1.2) ** 0.5 - 1), places=9)
        self.assertEqual(number(ctx, "arm.ion_index0.prose.heldout_grade_c.psm.n_runs").value, 2)
        self.assertEqual(len(ctx.results["O25_arm_ion_index0_summary"]), 2 * (2 + len(ids.GRADE_SCOPES)))

    def test_declared_arm_enters_no_main_summary(self):
        # DATASETS 4.4: the arm enters no main summary. With and without its rows, every table but the coverage
        # listing (O14) and the arm's own (O25) and every numbers.tsv key outside arm.* are the same
        out = []
        for with_arm in (False, True):
            counts, coverage = self.arm_inputs(with_arm)
            ctx = make_ctx(work=self.tmp, counts=counts, coverage=coverage, timings=fx("timings_fx.tsv"))
            ids.build(ctx)
            fdp.build(ctx)
            out.append(ctx)
        ctx0, ctx1 = out
        main = [k for k in ctx0.results if not k.startswith(("O14_", "O25_"))]
        self.assertTrue(main)
        self.assertEqual({k: ctx0.results[k] for k in main}, {k: ctx1.results[k] for k in main})
        self.assertEqual(sorted(k for k in ctx1.results if k not in ctx0.results),
                         ["O25_arm_ion_index0", "O25_arm_ion_index0_datasets", "O25_arm_ion_index0_summary"])
        self.assertEqual(sorted((n.key, repr(n.value)) for n in ctx0.numbers),
                         sorted((n.key, repr(n.value)) for n in ctx1.numbers if not n.key.startswith("arm.")))


class TestO25Tags(TempDir):
    def test_tables_of_two_tags_clash(self):
        # 'x' and 'x_datasets' would both write O25_arm_x_datasets: stop before any table
        extra = [count_row("prose", f"per_file_{t}", "hfx_r1", "hye_td", "hfx_r1.count.idXML", lv, 12000)
                 for t in ("x", "x_datasets") for lv in ("psm", "peptide")]
        counts = edit_counts(self.path("counts.tsv"), lambda r: r, extra=extra)
        with self.assertRaises(T.ValidationStop) as cm:
            built(work=self.tmp, counts=counts)
        self.assertIn("x, x_datasets", cm.exception.message)

    def test_arm_settings_after_a_timed_main_search(self):
        # the main td search is timed (B:249-250), the arm is not; an arm line without a main line does not end the
        # search for one that has
        main = ("/w/bin/ProSE -ini /w/p.ini -in /w/mzml/hfx_r1.mzML -database /w/db/{db}.fasta -out "
                "/w/out/prose/{b}/hfx_r1/{db}/hfx_r1.idXML -threads 16")

        def log(b, db):
            return f" > /w/out/prose/{b}/hfx_r1/{db}/all.r1.log 2>&1\n"

        with open(self.path("commands.log"), "w", encoding="utf-8") as fh:
            fh.write("/usr/bin/time -v -o /w/out/prose/per_file/hfx_r1/hye_td/all.r1.log.time "
                     + main.format(b="per_file", db="hye_td") + log("per_file", "hye_td"))
            fh.write(main.format(b="per_file", db="hye_entrap_s1_td") + log("per_file", "hye_entrap_s1_td"))
            # an arm line whose main line is not in the log
            fh.write(main.format(b="per_file_foo", db="hye_entrap_s2_td") + " -Search:foo 1"
                     + log("per_file_foo", "hye_entrap_s2_td"))
            fh.write(main.format(b="per_file_foo", db="hye_td") + " -Search:foo 1" + log("per_file_foo", "hye_td"))
        ctx = make_ctx(work=self.tmp)
        self.assertEqual(ids._arm_settings(ctx, "foo"), {"prose": "-Search:foo 1"})
        # an env prefix before the time prefix (B:251)
        with open(self.path("commands.log"), "w", encoding="utf-8") as fh:
            fh.write("OMP_NUM_THREADS=16 /usr/bin/time -v -o /w/t.time " + main.format(b="per_file", db="hye_td")
                     + "\n")
            fh.write("OMP_NUM_THREADS=16 " + main.format(b="per_file_foo", db="hye_td") + " -Search:foo 2\n")
        self.assertEqual(ids._arm_settings(ctx, "foo"), {"prose": "-Search:foo 2"})


if __name__ == "__main__":
    unittest.main()
