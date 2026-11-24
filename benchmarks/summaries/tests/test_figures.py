"""Tests of the figures module (SPEC 3.7): every figure drawn from the synthetic tables of fixtures/figures_tables
(made-up values in exactly the columns the table modules write), as one-page PDF and 300 dpi PNG of the stated size;
skips for absent and header-only tables; a contract mismatch as FAIL plus FigureError while the other figures are still
drawn; missing values never drawn as 0; the small helpers. The fixture tables are written by
fixtures/figures_make_tables.py (deterministic) over the unit layout of benchmarks/runs.tsv. matplotlib is optional
(SPEC 1): without it the drawing tests are skipped, and the build's WARN FIGURES path is tested instead."""
import importlib.util
import os
import re
import shutil
import struct
import sys
import tempfile
import unittest
from unittest import mock

sys.dont_write_bytecode = True
os.environ.setdefault("MPLBACKEND", "Agg")

from summaries import figures, tables as T  # noqa: E402

FX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "figures_tables")
HAVE_MATPLOTLIB = importlib.util.find_spec("matplotlib") is not None
needs_matplotlib = unittest.skipUnless(HAVE_MATPLOTLIB, "matplotlib not installed (optional, SPEC 1)")

# figure height in inches (width 7.0 in); PNG pixels at 300 dpi
HEIGHT_IN = {
    "fig_overtuning_psm": 4.5, "fig_overtuning_peptide": 4.5, "fig_ids_counts_psm": 3.3,
    "fig_ids_counts_peptide": 3.3, "fig_electron": 5.0, "fig_immuno": 5.0, "fig_fdp": 5.0, "fig_matched_fdp": 3.4,
    "fig_time_per_file": 5.0, "fig_batch": 3.0, "fig_scaling": 5.5, "fig_low_memory": 3.0, "fig_calibration": 4.0,
    "fig_ext_percolator": 0.9 + 2.0 * 2, "fig_prediction": 0.9 + 2.0 * 3,
}


def png_size(path):
    with open(path, "rb") as f:
        head = f.read(24)
    assert head[:8] == b"\x89PNG\r\n\x1a\n", path
    return struct.unpack(">II", head[16:24])


def pdf_pages(path):
    with open(path, "rb") as f:
        data = f.read()
    return len(re.findall(rb"/Type\s*/Page(?![a-zA-Z])", data))


def copy_tables(dst, drop=(), edit=None):
    """A copy of the fixture tables without the names in drop; edit(name, text) -> text rewrites a table."""
    os.makedirs(dst, exist_ok=True)
    for fn in os.listdir(FX):
        name = fn[:-4]
        if not fn.endswith(".tsv") or name in drop:
            continue
        with open(os.path.join(FX, fn), encoding="utf-8", newline="") as f:
            text = f.read()
        if edit:
            text = edit(name, text)
        with open(os.path.join(dst, fn), "w", encoding="utf-8", newline="") as f:
            f.write(text)


def header_only(text):
    lines = text.splitlines(keepends=True)
    return "".join(line for line in lines if line.startswith("#")) + next(x for x in lines if not x.startswith("#"))


def drop_column(text, column):
    out = []
    idx = None
    for line in text.splitlines(keepends=True):
        if line.startswith("#"):
            out.append(line)
            continue
        cells = line.rstrip("\r\n").split("\t")
        if idx is None:
            idx = cells.index(column)
        out.append("\t".join(c for i, c in enumerate(cells) if i != idx) + "\n")
    return "".join(out)


class FiguresTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="test_figures_")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def lines(self, report, level=None):
        return [(lv, cid, msg) for lv, cid, msg in report.lines if level is None or lv == level]

    @needs_matplotlib
    def test_all_figures_from_the_fixture_tables(self):
        out = os.path.join(self.tmp, "figures")
        report = T.Report()
        figures.draw(FX, out, report)
        self.assertEqual(self.lines(report, "FAIL"), [])
        drawn = {msg.split(":")[0] for lv, cid, msg in report.lines if lv == "INFO" and ": drawn (" in msg}
        self.assertEqual(drawn, set(figures.FIGURE_NAMES))
        self.assertEqual(set(HEIGHT_IN), set(figures.FIGURE_NAMES))
        for name in figures.FIGURE_NAMES:
            pdf, png = os.path.join(out, name + ".pdf"), os.path.join(out, name + ".png")
            self.assertTrue(os.path.isfile(pdf), pdf)
            self.assertTrue(os.path.isfile(png), png)
            self.assertEqual(pdf_pages(pdf), 1, pdf)
            width, height = png_size(png)
            self.assertEqual(width, round(figures.WIDTH * figures.DPI), png)
            self.assertEqual(height, round(HEIGHT_IN[name] * figures.DPI), png)
        self.assertEqual(sorted(f for f in os.listdir(out) if f.endswith(".tmp")), [])
        with open(os.path.join(out, "fig_batch.pdf"), "rb") as f:
            pdf = f.read()
        self.assertIn(b"/FontFile2", pdf)  # TrueType embedded (pdf.fonttype 42), no Type 3 font
        self.assertNotIn(b"/Subtype /Type3", pdf)

    @needs_matplotlib
    def test_absent_tables_skip_every_figure(self):
        tables_dir, out = os.path.join(self.tmp, "tables"), os.path.join(self.tmp, "figures")
        os.makedirs(tables_dir)
        report = T.Report()
        figures.draw(tables_dir, out, report)
        self.assertEqual(self.lines(report, "FAIL"), [])
        infos = [msg for lv, cid, msg in report.lines if lv == "INFO"]
        self.assertEqual(len(infos), len(figures.FIGURE_NAMES))
        self.assertTrue(all(" skipped: table " in m and m.endswith(" absent") for m in infos), infos)
        self.assertEqual(os.listdir(out), [])

    @needs_matplotlib
    def test_header_only_table_skips_and_removes_a_stale_figure(self):
        tables_dir, out = os.path.join(self.tmp, "tables"), os.path.join(self.tmp, "figures")
        copy_tables(tables_dir, edit=lambda name, text: header_only(text) if name == "O16_batch" else text)
        os.makedirs(out)
        for ext in ("pdf", "png"):
            with open(os.path.join(out, f"fig_batch.{ext}"), "wb") as f:
                f.write(b"stale")
        report = T.Report()
        figures.draw(tables_dir, out, report)
        self.assertEqual(self.lines(report, "FAIL"), [])
        msgs = [msg for lv, cid, msg in report.lines if msg.startswith("fig_batch")]
        self.assertEqual(len(msgs), 1)
        self.assertIn("skipped: table O16_batch empty", msgs[0])
        self.assertIn("stale fig_batch.pdf, fig_batch.png removed", msgs[0])
        self.assertFalse(os.path.exists(os.path.join(out, "fig_batch.png")))
        self.assertTrue(os.path.isfile(os.path.join(out, "fig_scaling.png")))

    @needs_matplotlib
    def test_contract_mismatch_fails_one_figure_and_draws_the_others(self):
        tables_dir, out = os.path.join(self.tmp, "tables"), os.path.join(self.tmp, "figures")
        copy_tables(tables_dir, edit=lambda name, text: drop_column(text, "ratio_wall") if name == "O16_batch"
                    else text)
        report = T.Report()
        with self.assertRaises(figures.FigureError) as cm:
            figures.draw(tables_dir, out, report)
        self.assertIsInstance(cm.exception.__cause__, ValueError)
        fails = self.lines(report, "FAIL")
        self.assertEqual(len(fails), 1)
        self.assertEqual(fails[0][1], "FIGURES")
        self.assertIn("fig_batch: ValueError: table O16_batch lacks the columns ratio_wall", fails[0][2])
        self.assertFalse(os.path.exists(os.path.join(out, "fig_batch.png")))
        for name in figures.FIGURE_NAMES:
            if name != "fig_batch":
                self.assertTrue(os.path.isfile(os.path.join(out, name + ".png")), name)

    @needs_matplotlib
    def test_pair_leads_without_the_datasets_table(self):
        """O20 without O20_external_percolator_datasets: the bars are the gmean of the used runs, said in INFO."""
        tables_dir, out = os.path.join(self.tmp, "tables"), os.path.join(self.tmp, "figures")
        copy_tables(tables_dir, drop=("O20_external_percolator_datasets",))
        report = T.Report()
        figures.draw(tables_dir, out, report)
        msg = next(m for lv, cid, m in report.lines if m.startswith("fig_ext_percolator"))
        self.assertIn("bars from run rows for prose/msfragger, prose/sage", msg)

    @needs_matplotlib
    def test_overtuning_points_fall_back_to_o02(self):
        tables_dir, out = os.path.join(self.tmp, "tables"), os.path.join(self.tmp, "figures")
        copy_tables(tables_dir, drop=("O04_overtuning_psm_runs",))
        report = T.Report()
        figures.draw(tables_dir, out, report)
        msg = next(m for lv, cid, m in report.lines if m.startswith("fig_overtuning_psm"))
        self.assertIn("run points from O02_pairs_runs", msg)

    @needs_matplotlib
    def test_missing_values_are_never_drawn_as_zero(self):
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.patches import Rectangle
        tabs = figures.Tables(FX)
        with plt.rc_context(figures.rc_params()):
            # O9: Sage failed (memory) on every class II sample, the other arrangement not run: no bar of height 0
            fig, _ = figures.fig_immuno(plt, tabs)
            try:
                for ax in fig.axes:
                    heights = [p.get_height() for p in ax.patches if isinstance(p, Rectangle)]
                    self.assertTrue(heights)
                    self.assertTrue(all(h > 0 for h in heights), (ax.get_title(loc="left"), heights))
                class_ii = [ax for ax in fig.axes if "class II" in ax.get_title(loc="left")]
                self.assertEqual(len(class_ii), 2)
                for ax in class_ii:  # 3 samples x (ProSE main, MSFragger); Sage and the other arrangement: x marks
                    self.assertEqual(len([p for p in ax.patches if isinstance(p, Rectangle)]), 6)
                    marks = [ln for ln in ax.lines if ln.get_marker() == "x"]
                    self.assertEqual(len(marks), 6)
                    texts = [t.get_text() for t in ax.texts]
                    self.assertEqual(texts.count("failed (memory)"), 3)
            finally:
                plt.close(fig)
            # O15: failed_memory as x on the 200 GiB cap of the RSS panel, never a point at the top of the time panel
            fig, _ = figures.fig_time_per_file(plt, tabs)
            try:
                time_ax, rss_ax = fig.axes[0], fig.axes[1]
                caps = [ln for ln in rss_ax.lines if ln.get_marker() == "x"
                        and list(ln.get_ydata()) == [figures.D.CAP_GIB]]
                self.assertEqual(len(caps), 6)
                for ln in time_ax.lines:
                    if ln.get_marker() == "o":
                        self.assertTrue(all(y > 0 for y in ln.get_ydata()))
                self.assertIn("failed (memory)", [t.get_text() for t in time_ax.texts])
            finally:
                plt.close(fig)

    def test_build_without_matplotlib_warns_and_skips(self):
        """SPEC 1: without matplotlib the build gives WARN FIGURES and draws nothing; the tables are unaffected."""
        import summarize  # benchmarks/summarize.py (top_level_dir = benchmarks)
        report, errors = T.Report(), []
        out = os.path.join(self.tmp, "figures")
        with mock.patch("importlib.util.find_spec", return_value=None):
            summarize.draw_figures(FX, out, report, errors)
        self.assertEqual(self.lines(report), [("WARN", "FIGURES", "matplotlib not found: figures skipped, tables "
                                                                  "are built (SPEC 1)")])
        self.assertEqual(errors, [])
        self.assertFalse(os.path.exists(out))

    def test_helpers(self):
        self.assertIsNone(figures.num("NA"))
        self.assertIsNone(figures.num("nan"))
        self.assertIsNone(figures.num("-"))
        self.assertEqual(figures.num("0"), 0.0)
        self.assertEqual(figures.first(None, 0.0, 1.0), 0.0)
        self.assertEqual(figures.reason_label("failed_memory stage all repetition 0 exit 137"), "failed (memory)")
        self.assertEqual(figures.reason_label("msfragger:failed; sage:zero", engine="sage"), "zero count")
        self.assertEqual(figures.reason_label("msfragger:failed", engine="prose"), "n/a")
        self.assertEqual(figures.reason_label("", "incomplete r3"), "incomplete")
        self.assertEqual(figures.comparator_of("prose/msfragger"), "msfragger")
        self.assertEqual(figures.comparator_of("prose_sage"), "sage")
        self.assertEqual(figures.comparator_of("peptdeep_vs_main"), "prose")
        self.assertEqual(figures.comparator_of("peptdeep_vs_msbooster"), "msfragger")
        self.assertEqual(figures.comparator_of("msbooster_vs_main"), "msfragger")
        self.assertEqual(figures.pair_title("prose/msfragger"), "ProSE / MSFragger")
        self.assertEqual(figures.pair_title("peptdeep_vs_msbooster"), "ProSE+PeptDeep / MSFragger+MSBooster")
        self.assertEqual(figures.pair_title("msbooster_vs_main"), "MSFragger+MSBooster / MSFragger")


if __name__ == "__main__":
    unittest.main()
