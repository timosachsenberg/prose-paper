"""Tests of the figures module (SPEC 3.7): every figure drawn from the synthetic tables of fixtures/figures_tables
(made-up values in exactly the columns the table modules write), as one-page PDF and 300 dpi PNG of the stated size
(at most 9 in tall, C6), with the paper copies in figures/main and figures/supplement and figures/index.tsv; in the
PDFs no transparency, no stroke below 0.5 pt and no text below 6 pt (C2); skips for absent and header-only tables,
stale files and copies removed; a contract mismatch as FAIL plus FigureError while the other figures are still
drawn; missing values never drawn as 0; the camera-ready rules of Fig 1, FigS1 and Fig 2 (panel letters, words, one
tick step, the natural-only diamonds); on every figure the renderer checks of FIGURES_CAMERA_READY.md C3 to C5
(size, words, number format, page, overlaps, rotated spacing, y label height) and the panel letters; Fig 4's dropped
empty slot, "Sage: not run" from O14 and the two fig_batch panels (C7); the spacing and open marks of FigS4, FigS9's
diamond beside its marker and the caption facts in index.tsv; the font variable SUMMARIZE_FONT_DIR; the small
helpers. The fixture tables are written by fixtures/figures_make_tables.py (deterministic) over the unit layout
of benchmarks/runs.tsv.
matplotlib is optional (SPEC 1): without it the drawing tests are skipped, and the build's WARN FIGURES path is tested
instead. The tests pass with and without SUMMARIZE_FONT_DIR set."""
import importlib.util
import math
import os
import re
import shutil
import struct
import sys
import tempfile
import unittest
import zlib
from unittest import mock

sys.dont_write_bytecode = True
os.environ.setdefault("MPLBACKEND", "Agg")

from summaries import figures, tables as T  # noqa: E402

FX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "figures_tables")
HAVE_MATPLOTLIB = importlib.util.find_spec("matplotlib") is not None
needs_matplotlib = unittest.skipUnless(HAVE_MATPLOTLIB, "matplotlib not installed (optional, SPEC 1)")

# figure height in inches (width 7.0 in); PNG pixels at 300 dpi (FIGURES_CAMERA_READY.md section 2, C6)
HEIGHT_IN = {
    "fig_overtuning_psm": 4.5, "fig_overtuning_peptide": 4.5, "fig_ids_counts_psm": 3.3,
    "fig_ids_counts_peptide": 3.3, "fig_electron": 4.6, "fig_immuno": 4.4, "fig_fdp": 5.0, "fig_fdp_main": 4.0,
    "fig_matched_fdp": 3.6, "fig_time_per_file": 4.6, "fig_batch": 4.4, "fig_scaling": 4.6, "fig_low_memory": 3.0,
    "fig_calibration": 6.4, "fig_ext_percolator": 0.9 + 1.6 * 2, "fig_prediction": 0.9 + 1.6 * 3,
}
NATURAL_ONLY = ["ups1_control", "astral_s1", "ultra2_s2"]  # the fixture groups with natural entrapment only
FONT_LINE = re.compile(r"^font: (.+) \((.+), (TrueType|not TrueType), embedded\)$")


def png_size(path):
    with open(path, "rb") as f:
        head = f.read(24)
    assert head[:8] == b"\x89PNG\r\n\x1a\n", path
    return struct.unpack(">II", head[16:24])


def pdf_pages(path):
    with open(path, "rb") as f:
        data = f.read()
    return len(re.findall(rb"/Type\s*/Page(?![a-zA-Z])", data))


def pdf_print_values(path):
    """(alpha values of the whole file, stroke widths, font sizes, page sizes in pt) of a PDF; the content streams
    are inflated (FIGURES_CAMERA_READY.md C2; textcheck_lib.pdf_sizes_and_widths)."""
    with open(path, "rb") as f:
        data = f.read()
    alphas = [float(v) for v in re.findall(rb"/(?:CA|ca)\s+([\d.]+)", data)]
    pages = [tuple(float(v) for v in m.split()) for m in re.findall(rb"/MediaBox\s*\[\s*([-\d.\s]+?)\s*\]", data)]
    widths, sizes = [], []
    for m in re.finditer(rb"stream\r?\n(.*?)\r?\nendstream", data, re.S):
        try:  # a decompressor that tolerates a lost last byte: a stream whose data ends in CR loses it to the regex
            text = zlib.decompressobj().decompress(m.group(1))
        except zlib.error:
            text = m.group(1)
        # any white space between operand and operator: matplotlib wraps long lines ("0.5\nw")
        widths += [float(w) for w in re.findall(rb"(?<![\w.])([\d.]+)\s+w(?![\w])", text)]
        sizes += [float(s) for s in re.findall(rb"/F\d+\s+([\d.]+)\s+Tf", text)]
    return alphas, widths, sizes, pages


def pdf_problems(path):
    """C2 and C6 on one PDF, as text (empty when camera-ready): every text size (Tf) at least 6 pt, no stroke of
    0 < w < 0.5 pt (a zero-width stroke belongs to a filled patch), no alpha (/CA, /ca) of 0 < a < 1 anywhere in the
    file (0 is a stroke or fill of color 'none', which prints nothing), one page 7.0 in wide and at most 9 in tall."""
    alphas, widths, sizes, pages = pdf_print_values(path)
    name = os.path.basename(path)
    problems = [f"{name}: text {s:g} pt" for s in sorted({s for s in sizes if s < 6})]
    problems += [f"{name}: stroke {w:g} pt" for w in sorted({w for w in widths if 0 < w < 0.5})]
    problems += [f"{name}: alpha {a:g}" for a in sorted({a for a in alphas if 0 < a < 1})]
    if not sizes:
        problems.append(f"{name}: no text found")
    if len(pages) != 1:
        problems.append(f"{name}: {len(pages)} pages")
    for box in pages:
        w, h = box[2] - box[0], box[3] - box[1]
        if abs(w - figures.WIDTH * 72) > 0.01 or h > figures.MAX_HEIGHT * 72 + 0.01:
            problems.append(f"{name}: page {w / 72:.2f} x {h / 72:.2f} in")
    return problems


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


def touch(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(b"stale")


def drawn_texts(fig):
    """Every visible, non-empty Text of one draw of a finished figure (FIGURES_CAMERA_READY.md C3)."""
    from matplotlib.text import Text
    got = []
    orig = Text.draw

    def record(self, renderer):
        orig(self, renderer)
        if self.get_visible() and self.get_text().strip():
            got.append(self)
    Text.draw = record
    try:
        fig.canvas.draw()
    finally:
        Text.draw = orig
    return got


def edit_columns(text, change):
    """A table text with change(row) -> {column: new cell} applied to every data row ('#' lines kept)."""
    out, cols = [], None
    for line in text.splitlines(keepends=True):
        if line.startswith("#"):
            out.append(line)
            continue
        cells = line.rstrip("\r\n").split("\t")
        if cols is None:
            cols = cells
        else:
            row = dict(zip(cols, cells))
            row.update(change(row))
            cells = [row[c] for c in cols]
        out.append("\t".join(cells) + "\n")
    return "".join(out)


def drop_rows(text, drop):
    """A table text without the data rows for which drop(row) is true."""
    out, cols = [], None
    for line in text.splitlines(keepends=True):
        cells = line.rstrip("\r\n").split("\t")
        if not line.startswith("#") and cols is not None and drop(dict(zip(cols, cells))):
            continue
        if not line.startswith("#") and cols is None:
            cols = cells
        out.append(line)
    return "".join(out)


HYPHEN_MINUS = re.compile(r"(?<![\w.])-\d")  # G10: a number with a hyphen-minus, not U+2212
NO_THOUSANDS = re.compile(r"(?<![\w.,])\d{4,}(?![\w.,])")  # G10: 10000 instead of 10,000 (not inside a name)


def text_problems(fig):
    """C3, C4 and C5 over one draw of a finished figure, as text (empty when camera-ready): every drawn text at
    least 6 pt, without '$' or a code name (BANNED), with true minus signs and thousands commas (section 6), inside
    the page (0.01 pt); no two 0/90 degree text boxes overlapping by more than 0.3 pt in both directions; rotated
    labels of one axes at least 1.1 x FONT_PT apart perpendicular to their baseline; each y label at most its axes'
    height plus 2 pt (textcheck_lib.drawn_texts and audit)."""
    k = 72.0 / fig.dpi
    width, height = fig.get_size_inches() * 72.0
    renderer = fig.canvas.get_renderer()
    texts = [(t, t.get_window_extent(renderer)) for t in drawn_texts(fig)]
    problems = []
    for t, bb in texts:
        s = t.get_text()
        if t.get_fontsize() < 6:
            problems.append(f"size {t.get_fontsize():.1f} pt: {s!r}")
        if "$" in s or figures.BANNED.search(s):
            problems.append(f"code name or '$': {s!r}")
        if HYPHEN_MINUS.search(s) or NO_THOUSANDS.search(s):
            problems.append(f"number format: {s!r}")
        if bb.x0 * k < -0.01 or bb.y0 * k < -0.01 or bb.x1 * k > width + 0.01 or bb.y1 * k > height + 0.01:
            problems.append(f"outside the page: {s!r}")
    straight = [(t, bb) for t, bb in texts if round(t.get_rotation()) % 90 == 0]
    for i, (a, ba) in enumerate(straight):
        for b, bb in straight[i + 1:]:
            ox = (min(ba.x1, bb.x1) - max(ba.x0, bb.x0)) * k
            oy = (min(ba.y1, bb.y1) - max(ba.y0, bb.y0)) * k
            if ox > 0.3 and oy > 0.3:
                problems.append(f"overlap {ox:.1f} x {oy:.1f} pt: {a.get_text()!r} / {b.get_text()!r}")
    groups = {}
    for t, bb in texts:
        if round(t.get_rotation()) % 90:
            groups.setdefault((id(t.axes), round(t.get_rotation())), []).append(bb.x1 * k)
    for (_, rot), xs in groups.items():
        xs.sort()
        for p, q in zip(xs, xs[1:]):
            if (q - p) * abs(math.sin(math.radians(rot))) < 1.1 * figures.FONT_PT:
                problems.append(f"rotated labels {(q - p):.1f} pt apart (rotation {rot})")
    for ax in fig.axes:
        label = ax.yaxis.label
        if label.get_visible() and label.get_text().strip():
            if label.get_window_extent(renderer).height * k > ax.bbox.height * k + 2.0:
                problems.append(f"y label taller than its axes: {label.get_text()!r}")
    return problems


ENGINE_HANDLE_MS = {"fig_fdp": figures.FDP_FULL_HANDLE_MS,  # FigS4's 1.8 pt dots
                    "fig_scaling": figures.SCALING_DOT_MS + figures.SCALING_DOT_MEW}  # FigS7's 4.2 pt dots


def handle_problems(fig, name):
    """The marker handles of a figure's legends, as text (empty when right): an engine dot is ENGINE_HANDLE_MS or
    HANDLE_DOT_MS points across without an edge (print2-1: with matplotlib's default 1 pt edge it was 5.0 pt), and
    every marker handle is at least 2.4 pt across (ms + mew), except the 2.2 pt run dot of FigS2 and FigS3, which is
    as large as the dots it stands for."""
    from matplotlib.lines import Line2D
    problems = []
    for leg in fig.legends:
        for h, t in zip(leg.legend_handles, leg.get_texts()):
            if not isinstance(h, Line2D) or h.get_marker() in (None, "", " ", "None", "none"):
                continue
            ms, mew, label = h.get_markersize(), h.get_markeredgewidth(), t.get_text()
            if label in figures.D.ENGINE_NAME.values() and (ms, mew) != (ENGINE_HANDLE_MS.get(
                    name, figures.HANDLE_DOT_MS), 0):
                problems.append(f"engine handle {label!r}: ms {ms:g}, mew {mew:g}")
            least = 2.2 if name.startswith("fig_ids_counts") and label == figures.VOCAB["run"] else 2.4
            if ms + mew < least - 1e-9:
                problems.append(f"handle {label!r}: {ms + mew:g} pt across")
    return problems


class FiguresTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="test_figures_")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def lines(self, report, level=None):
        return [(lv, cid, msg) for lv, cid, msg in report.lines if level is None or lv == level]

    def pyplot(self):
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        return plt

    def assert_camera_ready_texts(self, fig):
        """No code name, no '$', at least 6 pt, and no alpha below 1 on any artist (G1, G3, G5)."""
        texts = drawn_texts(fig)
        self.assertTrue(texts)
        for t in texts:
            self.assertIsNone(figures.BANNED.search(t.get_text()), t.get_text())
            self.assertGreaterEqual(t.get_fontsize(), 6, t.get_text())
        legends = list(fig.legends) + [ax.get_legend() for ax in fig.axes if ax.get_legend() is not None]
        unprinted = {id(leg.legendPatch) for leg in legends if not leg.get_frame_on()}  # frame off: never drawn
        for artist in fig.findobj():
            alpha = artist.get_alpha() if hasattr(artist, "get_alpha") else None
            self.assertTrue(alpha is None or alpha >= 1 or id(artist) in unprinted, artist)
        return [t.get_text() for t in texts]

    def assert_letters(self, fig, expected):
        """Bold letters in reading order, left of their axes by at least LETTER_GAP_PT (clear of the heading, also in
        a column without y tick labels), within the page and, measured after one more draw, not right of the
        leftmost y label or y tick label of their column by more than 1 pt (G4; a layout that has not settled moves
        the axes after the letters were placed)."""
        renderer = fig.canvas.get_renderer()
        axes = [ax for ax in fig.axes if getattr(ax, "panel_letter", None) is not None]
        self.assertEqual([ax.panel_letter.get_text() for ax in axes], list(expected))
        def column(ax):
            spec = ax.get_subplotspec()
            return spec.get_topmost_subplotspec().colspan.start if spec is not None else id(ax)
        left = {}
        for ax in fig.axes:
            bb = ax.yaxis.get_tightbbox(renderer)
            x0 = min(ax.bbox.x0, bb.x0) if bb is not None and bb.width > 0 else ax.bbox.x0
            left[column(ax)] = min(left.get(column(ax), x0), x0)
        for ax in axes:
            t = ax.panel_letter
            self.assertEqual(t.get_fontweight(), figures.PANEL_LETTER_WEIGHT)
            box = t.get_window_extent(renderer)
            self.assertLessEqual(box.x1, ax.bbox.x0 - figures.LETTER_GAP_PT * fig.dpi / 72.0 + 0.01, t.get_text())
            self.assertGreaterEqual(box.x0, -0.01)
            self.assertLessEqual(box.x0, max(left[column(ax)], 0.0) + fig.dpi / 72.0, t.get_text())

    @needs_matplotlib
    def test_all_figures_from_the_fixture_tables(self):
        """Every figure drawn by draw() from the fixture tables; C2 on every PDF (text at least 6 pt, no stroke below
        0.5 pt, no transparency); C6 (the heights of section 2, at most 9 in, in HEIGHT_IN, the PDF page and the PNG);
        the paper copies and index.tsv (O1; C7: the rows match the drawn figures); the font line."""
        out = os.path.join(self.tmp, "figures")
        report = T.Report()
        figures.draw(FX, out, report)
        self.assertEqual(self.lines(report, "FAIL"), [])
        drawn = {msg.split(":")[0] for lv, cid, msg in report.lines if lv == "INFO" and ": drawn (" in msg}
        self.assertEqual(drawn, set(figures.FIGURE_NAMES))
        self.assertEqual(set(HEIGHT_IN), set(figures.FIGURE_NAMES))
        problems = []
        for name in figures.FIGURE_NAMES:
            self.assertLessEqual(HEIGHT_IN[name], figures.MAX_HEIGHT, name)  # C6: at most 9 in
            pdf, png = os.path.join(out, name + ".pdf"), os.path.join(out, name + ".png")
            self.assertTrue(os.path.isfile(pdf), pdf)
            self.assertTrue(os.path.isfile(png), png)
            self.assertEqual(pdf_pages(pdf), 1, pdf)
            width, height = png_size(png)
            self.assertEqual(width, round(figures.WIDTH * figures.DPI), png)
            self.assertEqual(height, round(HEIGHT_IN[name] * figures.DPI), png)
            problems += pdf_problems(pdf)  # C2 (G1, G2, G5) and the page size (C6)
            self.assertAlmostEqual(pdf_print_values(pdf)[3][0][3] / 72.0, HEIGHT_IN[name], places=3, msg=pdf)
        self.assertEqual(problems, [])
        self.assertEqual(sorted(f for f in os.listdir(out) if f.endswith(".tmp")), [])
        with open(os.path.join(out, "fig_batch.pdf"), "rb") as f:
            pdf = f.read()
        self.assertIn(b"/FontFile2", pdf)  # TrueType embedded (pdf.fonttype 42), no Type 3 font
        self.assertNotIn(b"/Subtype /Type3", pdf)
        # paper copies (O1): the same bytes under figures/main and figures/supplement
        for name, (folder, stem) in figures.PAPER_FIGURES.items():
            for ext in ("pdf", "png"):
                with open(os.path.join(out, f"{name}.{ext}"), "rb") as a, \
                        open(os.path.join(out, folder, f"{stem}.{ext}"), "rb") as b:
                    self.assertEqual(a.read(), b.read(), (name, ext))
        self.assertEqual(sorted(os.listdir(os.path.join(out, "main"))),
                         sorted(f"{stem}.{ext}" for folder, stem in figures.PAPER_FIGURES.values() if folder == "main"
                                for ext in ("pdf", "png")))
        # index.tsv: one row per drawn figure in PAPER_FIGURES order
        with open(os.path.join(out, "index.tsv"), encoding="utf-8", newline="") as f:
            text = f.read()
        self.assertNotIn("\r", text)
        lines = text.splitlines()
        self.assertTrue(lines[0].startswith("# "))
        self.assertEqual(tuple(lines[1].split("\t")), figures.INDEX_COLUMNS)
        rows = [dict(zip(figures.INDEX_COLUMNS, line.split("\t"))) for line in lines[2:]]
        self.assertEqual([r["code_name"] for r in rows], list(figures.PAPER_FIGURES))
        for r in rows:
            folder, stem = figures.PAPER_FIGURES[r["code_name"]]
            self.assertEqual(r["number"], stem.split("_")[0])
            self.assertEqual(r["file"], f"{folder}/{stem}")
            self.assertEqual((r["width_in"], r["height_in"]), ("7.00", f"{HEIGHT_IN[r['code_name']]:.2f}"))
            self.assertNotEqual(r["tables"], "-", r)
            self.assertEqual(r["caption_keys"], figures.CAPTION_KEYS[r["code_name"]])
        by_name = {r["code_name"]: r for r in rows}
        # O14_coverage: the reason why the immunopeptidomics groups are left out (no entrapment search)
        self.assertEqual(by_name["fig_fdp_main"]["tables"], "O11_fdp_runs,O14_coverage")
        self.assertIn("natural_only=" + ",".join(NATURAL_ONLY), by_name["fig_fdp_main"]["facts"])
        self.assertIn("tick_step=", by_name["fig_overtuning_psm"]["facts"])
        self.assertIn("threads=", by_name["fig_time_per_file"]["facts"])
        # the facts the captions need beyond the counts: the n of Fig 2's SD bars; FigS4's Arabidopsis reference (S3);
        # the samples of FigS2 B; the scaling run of FigS7
        self.assertRegex(by_name["fig_fdp_main"]["facts"], r"sd_n_shared=[\d to]+; sd_runs_n_shared_below_3=\d+")
        self.assertIn("arath_units=", by_name["fig_fdp"]["facts"])
        self.assertIn("arath_psm_difference_pp=ProSE ", by_name["fig_fdp"]["facts"])
        self.assertIn("points_B=samples", by_name["fig_ids_counts_psm"]["facts"])
        # no fact about the decision runs (owner, 2026-11-28): they have no mark of their own, the captions name none
        for r in rows:
            self.assertNotRegex(r["facts"], r"(^|; )(decision\w*|heldout_same_donor)=", r["code_name"])
        self.assertIn("scaling_run=", by_name["fig_scaling"]["facts"])
        # what a figure leaves out or marks missing (its caption says it); index.tsv separates facts with "; "
        self.assertIn("arath_marks=open triangles", by_name["fig_fdp"]["facts"])
        self.assertIn("out_of_memory=Sage pxd058436_classII (3 samples), Sage pxd019643_classII (3 samples); ",
                      by_name["fig_immuno"]["facts"])
        for name in ("fig_ids_counts_psm", "fig_ids_counts_peptide", "fig_batch", "fig_fdp_main", "fig_fdp"):
            facts = dict(f.split("=", 1) for f in by_name[name]["facts"].split("; "))
            self.assertIn("pxd058436_classII (", facts["left_out"], name)
            if name != "fig_fdp":  # FigS4 draws the electron-based groups
                self.assertIn("pxd011695_ETD (", facts["left_out"], name)
        infos = [m for lv, cid, m in report.lines if lv == "INFO" and m.startswith("index.tsv: ")]
        self.assertEqual(infos, [f"index.tsv: {len(rows)} figure(s), main 4, supplement {len(rows) - 4}"])
        # the font line (D18): INFO with the file; a WARN only when the font is neither Arial nor Helvetica
        fonts = [FONT_LINE.match(m) for lv, cid, m in report.lines if lv == "INFO" and m.startswith("font: ")]
        self.assertEqual(len(fonts), 1)
        self.assertIsNotNone(fonts[0])
        warns = [m for lv, cid, m in report.lines if lv == "WARN" and m.startswith("font: ")]
        self.assertEqual(len(warns), 0 if fonts[0].group(1) in figures.PREFERRED_FONTS else 1, warns)

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
        for ext in ("pdf", "png"):
            touch(os.path.join(out, f"fig_batch.{ext}"))
        # stale paper copies: of the skipped figure, and of a number no longer in PAPER_FIGURES; other files stay
        touch(os.path.join(out, "supplement", "FigS6_batch.png"))
        touch(os.path.join(out, "main", "Fig9_old.pdf"))
        touch(os.path.join(out, "supplement", "notes.txt"))
        report = T.Report()
        figures.draw(tables_dir, out, report)
        self.assertEqual(self.lines(report, "FAIL"), [])
        msgs = [msg for lv, cid, msg in report.lines if msg.startswith("fig_batch")]
        self.assertEqual(len(msgs), 1)
        self.assertIn("skipped: table O16_batch empty", msgs[0])
        self.assertIn("stale fig_batch.pdf, fig_batch.png removed", msgs[0])
        self.assertFalse(os.path.exists(os.path.join(out, "fig_batch.png")))
        self.assertTrue(os.path.isfile(os.path.join(out, "fig_scaling.png")))
        self.assertFalse(os.path.exists(os.path.join(out, "supplement", "FigS6_batch.png")))
        self.assertFalse(os.path.exists(os.path.join(out, "main", "Fig9_old.pdf")))
        self.assertTrue(os.path.isfile(os.path.join(out, "supplement", "notes.txt")))
        self.assertTrue(os.path.isfile(os.path.join(out, "supplement", "FigS7_scaling.png")))
        index = [m for lv, cid, m in report.lines if m.startswith("index.tsv: ")]
        self.assertEqual(len(index), 1)
        self.assertIn("stale copies removed: main/Fig9_old.pdf, supplement/FigS6_batch.png", index[0])
        with open(os.path.join(out, "index.tsv"), encoding="utf-8") as f:
            self.assertNotIn("fig_batch", f.read())

    @needs_matplotlib
    def test_stale_copies_list_stops_after_ten(self):
        """The index line names the stale paper copies it removed through tables.list_text: 10, then '... (+n
        more)', as the check report's lists do."""
        tables_dir, out = os.path.join(self.tmp, "tables"), os.path.join(self.tmp, "figures")
        copy_tables(tables_dir, drop=[fn[:-4] for fn in os.listdir(FX) if fn != "O16_batch.tsv"])
        for i in range(12):
            touch(os.path.join(out, "main", f"Fig9_old{i:02d}.pdf"))
        report = T.Report()
        figures.draw(tables_dir, out, report)
        self.assertEqual(self.lines(report, "FAIL"), [])
        index = [m for lv, cid, m in report.lines if m.startswith("index.tsv: ")]
        self.assertEqual(len(index), 1)
        removed = ", ".join(f"main/Fig9_old{i:02d}.pdf" for i in range(10))
        self.assertTrue(index[0].endswith(f"; stale copies removed: {removed}, ... (+2 more)"), index[0])
        self.assertFalse(os.path.exists(os.path.join(out, "main")))

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
        self.assertFalse(os.path.exists(os.path.join(out, "supplement", "FigS6_batch.png")))
        for name in figures.FIGURE_NAMES:
            if name != "fig_batch":
                self.assertTrue(os.path.isfile(os.path.join(out, name + ".png")), name)

    @needs_matplotlib
    def test_failed_figures_list_stops_after_ten(self):
        """The FigureError message names at most 10 failed figures, then how many are left out (README list rule);
        each failed figure has its own FAIL line."""
        def broken(plt, tabs):
            raise ValueError("broken")
        names = [f"fig_x{i:02d}" for i in range(12)]
        report = T.Report()
        with mock.patch.object(figures, "FIGURES", [(n, broken, ()) for n in names]):
            with self.assertRaises(figures.FigureError) as cm:
                figures.draw(FX, os.path.join(self.tmp, "figures"), report)
        self.assertEqual(str(cm.exception), f"12 figure(s) failed: {', '.join(names[:10])}, ... (+2 more)")
        self.assertEqual(len(self.lines(report, "FAIL")), 12)

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
        plt = self.pyplot()
        from matplotlib.patches import Rectangle
        tabs = figures.Tables(FX)
        with plt.rc_context(figures.rc_params()):
            # O9: Sage out of memory on every class II sample, the other arrangement not run: no bar of height 0
            fig, _ = figures.fig_immuno(plt, tabs)
            try:
                # G13: rows in design.IMMUNO_ORDER (PXD058436 on top), columns class I and class II
                heads = [ax.get_title(loc="left") for ax in fig.axes]
                order = [figures.D.display(g) for g in figures.D.IMMUNO_ORDER]
                self.assertEqual([next(d for d in order if h.startswith(d + ",")) for h in heads],
                                 [figures.D.display(g) for g in ("pxd058436_classI", "pxd058436_classII",
                                                                 "pxd019643_classI", "pxd019643_classII")])
                for ax in fig.axes:
                    heights = [p.get_height() for p in ax.patches if isinstance(p, Rectangle)]
                    self.assertTrue(heights)
                    self.assertTrue(all(h > 0 for h in heights), (ax.get_title(loc="left"), heights))
                class_ii = [ax for ax in fig.axes if "class II" in ax.get_title(loc="left")]
                self.assertEqual(len(class_ii), 2)
                for ax in class_ii:  # 3 samples x (ProSE, MSFragger); Sage: x marks (the empty slot is dropped, D7)
                    self.assertEqual(len([p for p in ax.patches if isinstance(p, Rectangle)]), 6)
                    marks = [ln for ln in ax.lines if ln.get_marker() == "x"]
                    self.assertEqual(len(marks), 3)
                    texts = [t.get_text() for t in ax.texts]
                    self.assertEqual(texts.count("out of memory"), 3)
            finally:
                plt.close(fig)
            # O15: failed_memory as x on the 200 GiB cap of the memory panel, never a point at the top of the time
            # panel; on the time axis every missing value is a label without an x (F3.3, G15). The out-of-memory
            # label names the engine and stands under each of its categories (the two class II columns, with class I
            # between them), on three lines once the layout is known
            fig, _ = figures.fig_time_per_file(plt, tabs)
            try:
                time_ax, rss_ax = fig.axes[0], fig.axes[1]
                groups = figures.ordered_groups(r["group"] for r in tabs.read("O15_time_runs")[1])
                caps = [ln for ln in rss_ax.lines if ln.get_marker() == "x"
                        and list(ln.get_ydata()) == [figures.D.CAP_GIB]]
                # one x per engine and column (3 samples each; index.tsv counts them), at Sage's place in the column
                self.assertEqual(sorted(round(ln.get_xdata()[0], 9) for ln in caps),
                                 [groups.index("pxd058436_classII"), groups.index("pxd019643_classII")])
                for ln in time_ax.lines:
                    if ln.get_marker() == "o":
                        self.assertTrue(all(y > 0 for y in ln.get_ydata()))
                self.assertEqual([ln for ln in time_ax.lines if ln.get_marker() == "x"], [])
                texts = [t.get_text() for t in time_ax.texts]
                self.assertNotIn("out of memory", texts)
                self.assertEqual(texts.count(figures.VOCAB["sage_not_run"]), 1)
                wide = figures.VOCAB["engine_out_of_memory"].format("Sage")
                self.assertEqual(sorted(round(t.xy[0], 6) for t in time_ax.texts if t.get_text() == wide),
                                 [groups.index("pxd058436_classII"), groups.index("pxd019643_classII")])
                figures.finish(fig)
                narrow = figures.VOCAB["engine_out_of_memory_narrow"].format("Sage")
                self.assertEqual([t.get_text() for t in time_ax.texts].count(narrow), 2)
            finally:
                plt.close(fig)
            # O3 (G15): a dataset without an R3 unit is a label at the base of the log count axis, without an x
            edited = os.path.join(self.tmp, "o03")
            copy_tables(edited, edit=lambda name, text: edit_columns(
                text, lambda r: {"sage": "NA"} if r["group"] == "velos" else {}) if name == "O03_three_runs" else text)
            fig, _ = figures.fig_ids_counts(plt, figures.Tables(edited), "psm")
            try:
                at = [t.xy[0] for t in fig.axes[0].texts if t.get_text() == figures.VOCAB["not_counted_all"]]
                self.assertIn(figures.D.FIGURE_ORDER.index("velos"), at)
                self.assertEqual([ln for ax in fig.axes for ln in ax.lines if ln.get_marker() == "x"], [])
            finally:
                plt.close(fig)

    @needs_matplotlib
    def test_overtuning_letters_words_and_one_tick_step(self):
        """Fig 1 and FigS1 (F1.1-F1.7): letters A, B; headings "ProSE vs <engine>"; right-hand labels in words with a
        true minus ("development", not "tuning": ProSE was developed using these data, owner 2026-11-28); one tick
        step over both panels; the "grade" row label; no code name."""
        plt = self.pyplot()
        tabs = figures.Tables(FX)
        with plt.rc_context(figures.rc_params()):
            for level in ("psm", "peptide"):
                fig, _ = figures.fig_overtuning(plt, tabs, level)
                try:
                    figures.finish(fig)
                    self.assert_letters(fig, "AB")
                    self.assertEqual([ax.get_title(loc="left") for ax in fig.axes],
                                     ["ProSE vs MSFragger", "ProSE vs Sage"])
                    texts = self.assert_camera_ready_texts(fig)
                    sides = [t for t in texts if re.match(r"^(development|held-out) [+−]\d+\.\d%$", t)]
                    self.assertEqual(len(sides), 4, texts)
                    for word in ("development dataset", "mean lead, development", "held-out dataset"):
                        self.assertIn(word, texts)
                    self.assertFalse([t for t in texts if "tuning" in t.lower()], texts)
                    self.assertIn("grade", texts)
                    steps = set()
                    for ax in fig.axes:
                        lo, hi = ax.get_ylim()
                        self.assertLess(lo, 0)
                        self.assertGreater(hi, 0)
                        ticks = [v for v in ax.get_yticks() if lo <= v <= hi]
                        self.assertLessEqual(len(ticks), figures.MAX_TICKS)
                        steps |= {round(b - a, 9) for a, b in zip(ticks, ticks[1:])}
                    self.assertEqual(len(steps), 1, steps)
                    self.assertEqual(fig.facts["tick_step"], f"{steps.pop():g}")
                finally:
                    plt.close(fig)

    @needs_matplotlib
    def test_fdp_main_tryptic_datasets_and_natural_only_diamonds(self):
        """Fig 2 (F2.1): the tryptic datasets only; natural-only datasets as open diamonds (D3); a dataset with both
        designs (velos in the fixture) shows both, the diamond at the run's x between its SD bar and its dot (as
        FigS4); no decision run, no Arabidopsis value; letters A, B; one FDP axis; dots 2.6 pt without an edge, the
        engines' runs apart; the legend's dot with its SD bar."""
        plt = self.pyplot()
        tabs = figures.Tables(FX)
        with plt.rc_context(figures.rc_params()):
            fig, info = figures.fig_fdp_main(plt, tabs)
            try:
                figures.finish(fig)
                groups = [g for g in figures.D.FIGURE_ORDER]
                self.assertEqual(info, f"2 panels, {len(groups)} x categories, 3 natural-only")
                self.assertEqual(fig.facts["natural_only"], ",".join(NATURAL_ONLY))
                self.assertEqual(fig.facts["natural_only_left_out"], "none")
                self.assertEqual(fig.facts["natural_with_shuffled"], "velos")
                # every design group not drawn, with the reason: the electron-based groups are in FigS4, and the
                # fixture's O14_coverage has only td searches of the immunopeptidomics groups
                full = figures.paper_name("fig_fdp")[1]
                self.assertEqual(fig.facts["left_out"], ", ".join(
                    [f"{g} (electron-based: in {full})" for g in figures.D.ELECTRON]
                    + [f"{g} (no entrapment search)" for g in figures.D.IMMUNO]))
                # the electron reason takes fig_fdp's number from PAPER_FIGURES: a renumbering carries over
                one = {("prose", "u", "psm"): {"group": "pxd011695_ETD"}}
                with mock.patch.dict(figures.PAPER_FIGURES, {"fig_fdp": ("supplement", "FigS7_entrapment_fdp")}):
                    self.assertIn("pxd011695_ETD (electron-based: in FigS7)", figures.fdp_left_out(tabs, one, ()))
                without = {k: v for k, v in figures.PAPER_FIGURES.items() if k != "fig_fdp"}
                with mock.patch.object(figures, "PAPER_FIGURES", without):  # no number: no code name either
                    self.assertIn("pxd011695_ETD (electron-based: in the full FDP figure)",
                                  figures.fdp_left_out(tabs, one, ()))
                # the runs above 1%, apart by mark: shuffled means (dots), natural-only values (3 x 3 diamonds) and
                # the natural values of velos (3 diamonds at its dots)
                self.assertFalse([k for k in fig.facts if k.startswith("drawn_runs")])
                for level in ("psm", "peptide"):
                    for e in figures.D.ENGINES:
                        self.assertRegex(fig.facts[f"shuffled_runs_above_1pct_{level}_{e}"], r"^\d+/\d+$")
                        self.assertRegex(fig.facts[f"natural_only_runs_above_1pct_{level}_{e}"], r"^\d/9$")
                        self.assertRegex(fig.facts[f"natural_with_shuffled_runs_above_1pct_{level}_{e}"], r"^\d/3$")
                self.assert_letters(fig, "AB")
                self.assertEqual([ax.get_title(loc="left") for ax in fig.axes], ["PSM level", "peptide level"])
                texts = self.assert_camera_ready_texts(fig)
                self.assertNotIn(figures.BLOCK_NAME["electron"], texts)
                self.assertFalse([t for t in texts if "decision" in t.lower()])
                self.assertNotIn(figures.VOCAB["arath"], texts)
                self.assertIn(figures.VOCAB["natural"], texts)
                self.assertIn(figures.VOCAB["one_percent"], texts)
                natural_x = {i for i, g in enumerate(groups) if g in NATURAL_ONLY}
                velos_x = groups.index("velos")
                k = 72.0 / fig.dpi
                on_dot = 0
                for ax in fig.axes:
                    self.assertEqual(len(ax.get_xticks()), len(groups))
                    self.assertEqual(ax.get_ylim(), fig.axes[0].get_ylim())
                    self.assertEqual(ax.get_ylim()[0], 0.0)
                    diamonds = [ln for ln in ax.lines if ln.get_marker() == "D"]
                    self.assertEqual(len(diamonds), 27 + 9)  # 3 datasets x 3 engines x 3 runs, velos 3 x 3
                    run_dots = [ln for ln in ax.lines if ln.get_marker() == "o"]
                    from matplotlib.collections import LineCollection
                    bars = [c for c in ax.collections if isinstance(c, LineCollection) and c.get_segments()]
                    for ln in diamonds:
                        self.assertEqual(ln.get_markerfacecolor(), "white")
                        x = ln.get_xdata()[0]
                        at = [d for d in run_dots if d.get_xdata()[0] == x]
                        if round(x) in natural_x:  # natural only: no dot at its x, above everything
                            self.assertEqual(at, [])
                            self.assertEqual(ln.get_zorder(), 5)
                            continue
                        # both designs: at the x of a dot of its engine, under the dot and above that dot's SD bar;
                        # above the dot when less than FDP_ON_DOT_PT from it (the fixture's velos_125_R1, ProSE,
                        # peptide level: about 0.3 pt), as finish() measured it
                        self.assertEqual(round(x), velos_x)
                        self.assertEqual([d.get_color() for d in at], [ln.get_markeredgecolor()])
                        gap = abs(ax.transData.transform((x, ln.get_ydata()[0]))[1]
                                  - ax.transData.transform((x, at[0].get_ydata()[0]))[1]) * k
                        if gap < figures.FDP_ON_DOT_PT:
                            self.assertEqual(ln.get_zorder(), figures.FDP_ON_DOT_Z)
                            self.assertGreater(ln.get_zorder(), at[0].get_zorder())
                            on_dot += 1
                        else:
                            self.assertEqual(ln.get_zorder(), figures.FDP_FULL_OPEN_Z)
                            self.assertLess(ln.get_zorder(), at[0].get_zorder())
                        under = [c for c in bars if any(s[0][0] == x for s in c.get_segments())]
                        self.assertEqual(len(under), 1)
                        self.assertEqual(under[0].get_zorder(), figures.FDP_FULL_BAR_Z)
                    self.assertEqual([ln for ln in ax.lines if ln.get_marker() in ("^", "v")], [])
                    opens = [ln for ln in ax.lines if ln.get_marker() == "o" and ln.get_markerfacecolor() == "white"]
                    self.assertEqual(opens, [])  # no open circle
                    # print size (F2.1): dots 2.6 pt without an edge; the runs of one engine do not touch, and the
                    # gap to the next engine's runs is wider than the step between runs (C-e, D14)
                    dots = [ln for ln in ax.lines if ln.get_marker() == "o"]
                    self.assertTrue(dots)
                    self.assertEqual({(ln.get_markersize(), ln.get_markeredgewidth()) for ln in dots}, {(2.6, 0.0)})
                    category = (ax.transData.transform((1, 0))[0] - ax.transData.transform((0, 0))[0]) * k
                    within, between = [], []
                    for x in range(len(groups)):
                        runs = [sorted(ln.get_xdata()[0] for ln in dots if round(ln.get_xdata()[0]) == x
                                       and ln.get_color() == figures.D.COLOUR[e]) for e in figures.D.ENGINES]
                        runs = [r for r in runs if r]
                        within += [b - a for r in runs for a, b in zip(r, r[1:])]
                        between += [b[0] - a[-1] for a, b in zip(runs, runs[1:])]
                    self.assertGreaterEqual(min(within) * category, 2.6, "runs of one engine touch")
                    self.assertGreater(min(between), max(within), "engine clusters run into each other")
                    # one run per engine (PXD011695 HCD; in the fixture one x per engine, its missing values):
                    # dodged FDP_ONE_RUN_DODGE, so the three marks stand closer to each other than to the next
                    # columns; two runs (PXD042233 Lumos CID): the engine gap of a 3-run column
                    one = figures.FDP_ONE_RUN_DODGE
                    x = groups.index("pxd011695_HCD")
                    xs = sorted(ln.get_xdata()[0] for ln in ax.lines if ln.get_marker() in ("o", "x")
                                and round(ln.get_xdata()[0]) == x)
                    self.assertEqual([round(v - x, 9) for v in xs], [-one, 0.0, one])
                    left = max(ln.get_xdata()[0] for ln in dots if round(ln.get_xdata()[0]) == x - 1)
                    right = min(ln.get_xdata()[0] for ln in dots if round(ln.get_xdata()[0]) == x + 1)
                    self.assertGreater(min(xs[0] - left, right - xs[-1]), one)
                    x = groups.index("pxd042233_lumos_cid")
                    xs = sorted(round(ln.get_xdata()[0] - x, 9) for ln in dots if round(ln.get_xdata()[0]) == x)
                    self.assertEqual(xs, [-0.27, -0.17, -0.05, 0.05, 0.17, 0.27])
                    # an open diamond is no wider than the gap between the engines (sqrt 2 x (ms + mew), miter tips)
                    width = math.sqrt(2) * (figures.NATURAL["ms"] + figures.NATURAL["mew"])
                    self.assertLessEqual(width, min(between) * category)
                self.assertGreaterEqual(on_dot, 1)
                self.assertTrue(fig.facts["natural_on_dot"].startswith(f"{on_dot}: "), fig.facts["natural_on_dot"])
                self.assertIn("velos_125_R1 (ProSE, peptide)", fig.facts["natural_on_dot"])
                # the legend shows the SD bar it names: the shuffled entry is a dot with a vertical bar
                from matplotlib.collections import LineCollection
                self.assertTrue(any(isinstance(h, LineCollection) for h in fig.legends[0].legend_handles))
            finally:
                plt.close(fig)
            with mock.patch.object(figures, "FDP_MAIN_NATURAL_ONLY", False):
                fig, info = figures.fig_fdp_main(plt, tabs)
            try:
                self.assertIn(f"{len(groups) - 3} x categories, 0 natural-only; left out: "
                              + ", ".join(NATURAL_ONLY), info)
                # only velos's diamonds stay (both designs), 3 engines x 3 runs per level
                drawn = [g for g in groups if g not in NATURAL_ONLY]
                for ax in fig.axes:
                    xs = [ln.get_xdata()[0] for ln in ax.lines if ln.get_marker() == "D"]
                    self.assertEqual(len(xs), 9)
                    self.assertEqual({round(x) for x in xs}, {drawn.index("velos")})
                row = figures.index_row(fig, "fig_fdp_main", ["O11_fdp_runs"], "main/Fig2_entrapment_fdp")
                self.assertIn("natural_only_left_out=" + ",".join(NATURAL_ONLY), row[-1])
                self.assertIn("natural_only_drawn=no (left out)", row[-1])
                left = fig.facts["left_out"].split(", ")
                self.assertEqual(left[:3], [f"{g} (natural entrapment only)" for g in NATURAL_ONLY])
                self.assertEqual(len(left), 3 + len(figures.D.ELECTRON) + len(figures.D.IMMUNO))
            finally:
                plt.close(fig)

    @needs_matplotlib
    def test_fdp_main_shuffled_design_without_shared_mean(self):
        """Fig 2: a dataset with a shuffled design whose shuffled means are all missing (here: counted, but no
        realization shared by every engine) is not natural-only. Its diamonds stay, each engine gets the missing mark
        'not shared' in both panels, index.tsv names it among the datasets with both designs, and with
        FDP_MAIN_NATURAL_ONLY = False it is still drawn (review of 2026-11-26)."""
        plt = self.pyplot()
        for name in os.listdir(FX):
            shutil.copy(os.path.join(FX, name), self.tmp)
        path = os.path.join(self.tmp, "O11_fdp_runs.tsv")
        with open(path, newline="") as f:
            lines = [line for line in f.read().split("\n") if line]
        head, out = lines[0].split("\t"), [lines[0]]
        for line in lines[1:]:
            out.append(line)
            r = dict(zip(head, line.split("\t")))
            if r["group"] == "ups1_control" and r["design"] == "natural":
                r.update(design="shuffled", n_own="3", mean_own="0.008", sd_own="0.001", n_shared="0",
                         mean_shared="NA", sd_shared="NA", natural="NA", note="")
                out.append("\t".join(r[c] for c in head))
        with open(path, "w", newline="") as f:
            f.write("\n".join(out) + "\n")
        groups = list(figures.D.FIGURE_ORDER)
        x = groups.index("ups1_control")
        for natural_only in (True, False):
            added = []
            orig = figures.Marks.add

            def record(marks, at, label, *args, **kwargs):
                added.append((round(at, 6), label))
                return orig(marks, at, label, *args, **kwargs)
            with mock.patch.object(figures.Marks, "add", record), \
                    mock.patch.object(figures, "FDP_MAIN_NATURAL_ONLY", natural_only), \
                    plt.rc_context(figures.rc_params()):
                fig, info = figures.fig_fdp_main(plt, figures.Tables(self.tmp))
            try:
                self.assertEqual(fig.facts["natural_only"], "astral_s1,ultra2_s2")
                self.assertEqual(set(fig.facts["natural_with_shuffled"].split(",")), {"velos", "ups1_control"})
                drawn = groups if natural_only else [g for g in groups if g not in ("astral_s1", "ultra2_s2")]
                xu = drawn.index("ups1_control")
                here = {(at, label) for at, label in added if round(at) == xu}
                self.assertEqual({label for _, label in here}, {figures.VOCAB["not_shared"]})
                self.assertEqual(len(here), 3)  # one x per engine
                for ax in fig.axes:
                    ds = [ln for ln in ax.lines if ln.get_marker() == "D" and round(ln.get_xdata()[0]) == xu]
                    self.assertEqual(len(ds), 9)
                    # the x of every engine in each panel (the set above cannot tell 3 + 3 from 3 + 0)
                    xs = [ln for ln in ax.lines if ln.get_marker() == "x" and round(ln.get_xdata()[0]) == xu]
                    self.assertEqual(len(xs), 3)
                    self.assertEqual({ln.get_color() for ln in xs},
                                     {figures.D.COLOUR[e] for e in figures.D.ENGINES})
                    self.assertEqual([ln for ln in ax.lines if ln.get_marker() == "o"
                                      and round(ln.get_xdata()[0]) == xu], [])
                if not natural_only:
                    self.assertIn("left out: astral_s1, ultra2_s2", info)
                    self.assertNotIn("ups1_control (natural entrapment only)", fig.facts["left_out"])
                else:
                    self.assertEqual(x, xu)
                    self.assertIn("2 natural-only", info)
            finally:
                plt.close(fig)

    @needs_matplotlib
    def test_fdp_main_engine_without_shuffled_rows(self):
        """Fig 2: in a dataset with a shuffled design, an engine whose shuffled searches did not run has no shuffled
        row in O11 (O11 leaves out a design only when its searches are not_run or not_run_by_design,
        fdp.search_ran). Its diamonds stay, it gets one x per panel at its place labelled 'not run' (never 'n/a'),
        and its natural values count among the datasets with both designs. A dataset without a shuffled design whose
        natural values are all missing (astral_s1 here, its natural searches out of memory) is not natural-only, has
        no shuffled design either, and keeps the reason of its notes (review of 2026-11-26)."""
        plt = self.pyplot()
        groups = list(figures.D.FIGURE_ORDER)

        def draw(edit):
            """Fig 2 from a copy of FX whose O11 rows went through edit (None drops a row): (fig, the Marks.add
            calls as (x, label), the number of rows dropped)."""
            for name in os.listdir(FX):
                shutil.copy(os.path.join(FX, name), self.tmp)
            path = os.path.join(self.tmp, "O11_fdp_runs.tsv")
            with open(path, newline="") as f:
                lines = [line for line in f.read().split("\n") if line]
            head, out = lines[0].split("\t"), [lines[0]]
            for line in lines[1:]:
                r = edit(dict(zip(head, line.split("\t"))))
                if r is not None:
                    out.append("\t".join(r[c] for c in head))
            with open(path, "w", newline="") as f:
                f.write("\n".join(out) + "\n")
            added = []
            orig = figures.Marks.add

            def record(marks, at, why, *args, **kwargs):
                added.append((round(at, 6), why))
                return orig(marks, at, why, *args, **kwargs)
            with mock.patch.object(figures.Marks, "add", record), \
                    mock.patch.object(figures, "FDP_MAIN_NATURAL_ONLY", True), \
                    plt.rc_context(figures.rc_params()):
                fig, _ = figures.fig_fdp_main(plt, figures.Tables(self.tmp))
            return fig, added, len(lines) - len(out)

        fig, added, dropped = draw(
            lambda r: None if (r["engine"], r["group"], r["design"]) == ("sage", "velos", "shuffled") else r)
        xv = groups.index("velos")
        try:
            self.assertEqual(dropped, 6)  # 3 runs x 2 levels
            self.assertEqual({why for at, why in added if round(at) == xv}, {figures.REASON_LABEL["not_run"]})
            self.assertIn("velos", fig.facts["natural_with_shuffled"].split(","))
            for level in ("psm", "peptide"):
                self.assertTrue(fig.facts[f"natural_with_shuffled_runs_above_1pct_{level}_sage"].endswith("/3"))
            for ax in fig.axes:
                at_v = [ln for ln in ax.lines if round(ln.get_xdata()[0]) == xv]
                self.assertEqual(len([ln for ln in at_v if ln.get_marker() == "D"]), 9)
                dots = [ln for ln in at_v if ln.get_marker() == "o"]
                self.assertEqual(len(dots), 6)  # ProSE and MSFragger only
                self.assertNotIn(figures.D.COLOUR["sage"], {ln.get_color() for ln in dots})
                xs = [ln for ln in at_v if ln.get_marker() == "x"]
                self.assertEqual([ln.get_color() for ln in xs], [figures.D.COLOUR["sage"]])
        finally:
            plt.close(fig)

        def out_of_memory(r):
            if r["group"] == "astral_s1":
                r.update(n_own="0", mean_own="NA", sd_own="NA", min_own="NA", max_own="NA", natural="NA",
                         note="natural failed_memory")
            return r
        fig, added, dropped = draw(out_of_memory)
        xa = groups.index("astral_s1")
        try:
            self.assertEqual(dropped, 0)
            self.assertEqual(set(fig.facts["natural_only"].split(",")), {"ups1_control", "ultra2_s2"})
            self.assertEqual({why for at, why in added if round(at) == xa}, {figures.REASON_LABEL["failed_memory"]})
            for ax in fig.axes:
                at_a = [ln for ln in ax.lines if round(ln.get_xdata()[0]) == xa]
                self.assertEqual([ln for ln in at_a if ln.get_marker() in ("D", "o")], [])
                self.assertEqual(len([ln for ln in at_a if ln.get_marker() == "x"]), 3)
        finally:
            plt.close(fig)

    @needs_matplotlib
    def test_no_open_circles_cap_label_sparse_runs_and_caption_facts(self):
        """No open circle in the figures of single runs that draw runs as markers (Fig 3, FigS4, FigS5, FigS10: a
        decision run is a filled dot as any run, owner 2026-11-28); the cap label 3 pt right of its axis (Fig 3,
        FigS8); FigS4's group with more than 3 runs and an empty engine slot dodges the engines present wider
        (FDP_SPARSE_*); FigS9's two triangles side by side in the legend; the caption facts read from O11_fdp_datasets
        and from O17's header note."""
        from matplotlib.colors import same_color
        plt = self.pyplot()
        tabs = figures.Tables(FX)
        with plt.rc_context(figures.rc_params()):
            for func in (figures.fig_time_per_file, figures.fig_fdp, figures.fig_electron, figures.fig_matched_fdp):
                fig, _ = func(plt, tabs)
                try:
                    lines = [ln for ax in fig.axes for ln in ax.lines]
                    self.assertTrue([ln for ln in lines if ln.get_marker() == "o"], func.__name__)
                    self.assertEqual([ln for ln in lines if ln.get_marker() == "o"
                                      and ln.get_markerfacecolor() == "white"], [], func.__name__)
                finally:
                    plt.close(fig)
            # the cap label: 3 pt right of the y axis and above the dashes, in points (not a share of the width)
            for func in (figures.fig_time_per_file, figures.fig_low_memory):
                fig, _ = func(plt, tabs)
                try:
                    figures.finish(fig)
                    renderer = fig.canvas.get_renderer()
                    k = 72.0 / fig.dpi
                    caps = [(ax, t) for ax in fig.axes for t in ax.texts if t.get_text().endswith("GiB cap")]
                    self.assertTrue(caps, func.__name__)
                    for ax, t in caps:
                        box = t.get_window_extent(renderer)
                        self.assertAlmostEqual((box.x0 - ax.bbox.x0) * k, 3.0, delta=0.5)
                        line = ax.transData.transform((0, figures.D.CAP_GIB))[1]
                        self.assertGreaterEqual((box.y0 - line) * k, 1.5)
                finally:
                    plt.close(fig)
            # FigS4: pxd065289_etcid has 5 ProSE and 4 MSFragger runs and no Sage slot; the two engines present are
            # dodged FDP_SPARSE_DODGE with the runs spread FDP_SPARSE_SPREAD, in the category, clusters apart
            fig, _ = figures.fig_fdp(plt, tabs)
            try:
                rows = tabs.read("O11_fdp_runs")[1]
                groups = figures.ordered_groups(r["group"] for r in rows if figures.D.kind(r["group"]) != "immuno")
                x = groups.index("pxd065289_etcid")
                for ax in fig.axes:
                    xs = {}
                    for ln in ax.lines:
                        if ln.get_marker() in ("o", "D", "^") and round(ln.get_xdata()[0]) == x:
                            e = next(e for e in figures.D.ENGINES
                                     if same_color(ln.get_markeredgecolor(), figures.D.COLOUR[e]))
                            xs.setdefault(e, set()).add(round(ln.get_xdata()[0] - x, 9))
                    self.assertEqual(sorted(xs), ["msfragger", "prose"])
                    half = figures.FDP_SPARSE_DODGE / 2
                    for e, centre in (("prose", -half), ("msfragger", half)):
                        self.assertTrue(all(abs(o - centre) <= figures.FDP_SPARSE_SPREAD + 1e-9 for o in xs[e]), xs)
                        self.assertTrue(all(abs(o) < 0.5 for o in xs[e]), xs)
                    steps = [b - a for e in xs for a, b in zip(sorted(xs[e]), sorted(xs[e])[1:])]
                    self.assertGreaterEqual(min(steps), 0.1 - 1e-9)  # FDP_SPREAD_WIDE would step 0.06 for 5 runs
                    self.assertGreater(min(xs["msfragger"]) - max(xs["prose"]), 0.1)
                facts = fig.facts
                self.assertEqual(facts["natural_velos_psm_pct"], "ProSE NA, Sage NA, MSFragger NA")  # no table
                # no count of the runs above 1%: Fig 2's counts leave out the decision runs that FigS4 draws
                self.assertFalse([k for k in facts if "above_1pct" in k], facts)
            finally:
                plt.close(fig)
            # FigS9: the two "no mass calibration" triangles in one legend row
            fig, _ = figures.fig_calibration(plt, tabs)
            try:
                figures.finish(fig)
                renderer = fig.canvas.get_renderer()
                ys = {t.get_text(): round(t.get_window_extent(renderer).y0, 3) for t in fig.legends[0].get_texts()}
                self.assertEqual(ys[figures.CAL_LABEL["cal_off"]], ys[figures.CAL_LABEL["cal0"]])
            finally:
                plt.close(fig)
            # O11_fdp_datasets (the natural value of velos, as the mean of the run means) and O17's header note
            edited = os.path.join(self.tmp, "facts")
            note = "# scaling rows from W; scaling run(s): hfx_A2; machine 'engine node' = the comparison row\n"
            copy_tables(edited, edit=lambda name, text: note + text if name == "O17_scaling" else text)
            head = ("engine", "kind", "class", "grade", "group", "level", "design", "n_units", "n_runs",
                    "mean_of_run_means", "max_run_mean", "n_runs_mean_above_1pct", "note")
            with open(os.path.join(edited, "O11_fdp_datasets.tsv"), "w", encoding="utf-8", newline="") as f:
                f.write("\t".join(head) + "\n")
                for e, v in (("prose", "0.012811"), ("sage", "0.013627"), ("msfragger", "0.012122")):
                    for design, value in (("shuffled", "0.02"), ("natural", v)):
                        f.write("\t".join((e, "tuning", "IT", "-", "velos", "psm", design, "3", "3", value, value,
                                           "3", "")) + "\n")
            tabs = figures.Tables(edited)
            fig, _ = figures.fig_fdp(plt, tabs)
            try:
                self.assertEqual(fig.facts["natural_velos_psm_pct"], "ProSE 1.28, Sage 1.36, MSFragger 1.21")
                self.assertEqual(fig.facts["natural_velos_peptide_pct"], "ProSE NA, Sage NA, MSFragger NA")
            finally:
                plt.close(fig)
            fig, _ = figures.fig_scaling(plt, tabs)
            try:
                self.assertEqual(fig.facts["scaling_run"], "hfx_A2")
            finally:
                plt.close(fig)
            fig, _ = figures.fig_scaling(plt, figures.Tables(FX))
            try:
                self.assertEqual(fig.facts["scaling_run"], "NA")
            finally:
                plt.close(fig)

    @needs_matplotlib
    def test_fdp_full_spacing_and_open_marks(self):
        """FigS4 (S3) at its narrow categories: the 1.8 pt dot (FDP_FULL_DOT) keeps the runs of one engine apart; the
        gap between two engines' runs is wider than the step between runs, and the gap to the next column wider still
        (D14: the engine order reads in greyscale); a column with one run per engine dodges its engines
        FDP_ONE_RUN_DODGE, also with an empty engine slot (only the engines present are dodged), and one with 2 runs
        keeps the engine gap of a 3-run column, so the dots of one column stand closer to each other than to the next
        column; the natural diamonds and Arabidopsis triangles have the small footprint and lie above the SD bars of
        their runs and under their dots."""
        from matplotlib.colors import same_color
        plt = self.pyplot()
        tabs = figures.Tables(FX)
        with plt.rc_context(figures.rc_params()):
            fig, _ = figures.fig_fdp(plt, tabs)
            try:
                figures.finish(fig)
                rows = tabs.read("O11_fdp_runs")[1]
                groups = figures.ordered_groups(r["group"] for r in rows if figures.D.kind(r["group"]) != "immuno")
                k = 72.0 / fig.dpi
                dot = figures.FDP_FULL_DOT["ms"]
                for ax in fig.axes:
                    category = (ax.transData.transform((1, 0))[0] - ax.transData.transform((0, 0))[0]) * k
                    marked = [ln for ln in ax.lines if ln.get_marker() in ("o", "D", "^")]
                    dots = [ln for ln in marked if ln.get_marker() == "o" and ln.get_markerfacecolor() != "white"]
                    self.assertEqual({(ln.get_markersize(), ln.get_markeredgewidth()) for ln in dots}, {(dot, 0.0)})
                    # the run positions (dots, and the open marks of a run without a dot) per column and engine
                    at = {}
                    for ln in marked:
                        x = ln.get_xdata()[0]
                        e = next(e for e in figures.D.ENGINES
                                 if same_color(ln.get_markeredgecolor(), figures.D.COLOUR[e]))
                        at.setdefault(round(x), {}).setdefault(e, set()).add(round(x, 9))
                    within, steps, between = [], [], {}

                    def full(by):  # every engine with two runs or more, evenly spaced (no run without a mark)
                        gaps = [[b - a for a, b in zip(sorted(v), sorted(v)[1:])] for v in by.values()]
                        return len(by) == 3 and all(g and max(g) - min(g) < 1e-6 for g in gaps)
                    for x, by in sorted(at.items()):
                        runs = [sorted(by[e]) for e in figures.D.ENGINES if e in by]
                        within += [b - a for r in runs for a, b in zip(r, r[1:])]
                        if full(by):
                            steps += [b - a for r in runs for a, b in zip(r, r[1:])]
                            between[x] = [b[0] - a[-1] for a, b in zip(runs, runs[1:])]
                    self.assertGreaterEqual(min(within) * category, dot + 0.2, "runs of one engine touch")
                    self.assertGreater(min(g for v in between.values() for g in v), max(steps),
                                       "engine clusters run into each other")
                    checked = 0
                    for x in between:  # between two columns of 3 runs per engine, the gap to the next column is wider
                        if x + 1 in between and all(len(v) == 3 for c in (x, x + 1) for v in at[c].values()):
                            gap = min(min(v) for v in at[x + 1].values()) - max(max(v) for v in at[x].values())
                            self.assertGreater(gap, max(between[x] + between[x + 1]), "columns run into each other")
                            checked += 1
                    self.assertGreater(checked, 0)
                    # one run per engine: dodged FDP_ONE_RUN_DODGE, with three engines (PXD011695 HCD: in the fixture
                    # one x per engine, its missing values) and with an empty Sage slot (PXD011695 ETciD); the marks
                    # of one column closer than the next column
                    places = {}
                    for ln in ax.lines:
                        if ln.get_marker() in ("o", "D", "^", "x"):
                            x = ln.get_xdata()[0]
                            e = next(e for e in figures.D.ENGINES
                                     if same_color(ln.get_markeredgecolor(), figures.D.COLOUR[e]))
                            places.setdefault(round(x), {}).setdefault(e, set()).add(round(x, 9))
                    one = figures.FDP_ONE_RUN_DODGE
                    for g, want in (("pxd011695_HCD", {"prose": -one, "sage": 0.0, "msfragger": one}),
                                    ("pxd011695_ETciD", {"prose": -one / 2, "msfragger": one / 2})):
                        x = groups.index(g)
                        offs = {e: sorted(v) for e, v in places[x].items()}
                        self.assertEqual(offs, {e: [round(x + o, 9)] for e, o in want.items()}, g)
                        first, last = min(min(v) for v in offs.values()), max(max(v) for v in offs.values())
                        self.assertGreater(min(min(v) for v in at[x + 1].values()) - last, one, g)
                        self.assertGreater(first - max(max(v) for v in at[x - 1].values()), one, g)
                    # two runs per engine (PXD042233 Lumos CID): the engine gap of a 3-run column
                    x = groups.index("pxd042233_lumos_cid")
                    runs = [sorted(at[x][e]) for e in figures.D.ENGINES]
                    self.assertEqual({len(r) for r in runs}, {2})
                    gaps = [b[0] - a[-1] for a, b in zip(runs, runs[1:])]
                    want = figures.FDP_DODGE - 2 * figures.FDP_SPREAD
                    self.assertTrue(all(abs(g - want) < 1e-6 for g in gaps), gaps)
                    # the open marks: one footprint, above the SD bars and under the dots of their runs
                    opens = [ln for ln in marked if ln.get_marker() in ("D", "^")]
                    self.assertEqual({ln.get_marker() for ln in opens}, {"D", "^"})
                    for ln in opens:
                        style = figures.NATURAL if ln.get_marker() == "D" else figures.ARATH
                        self.assertEqual((ln.get_markersize(), ln.get_markeredgewidth()), (style["ms"], style["mew"]))
                        self.assertLess(ln.get_zorder(), min(d.get_zorder() for d in dots))
                        self.assertGreater(ln.get_zorder(), max(c.get_zorder() for c in ax.collections))
            finally:
                plt.close(fig)

    @needs_matplotlib
    def test_marks_beside_bars_legends_and_caption_facts(self):
        """FigS9: the natural diamond NATURAL_BESIDE_PT right of its arm marker (off its SD bar) and under it; the
        legend handles of the diamond and the arm shapes near the drawn size (G9); FigS5's legend names the mean +- SD
        mark; the caption facts of Fig 3, Fig 4 and FigS8: the out-of-memory searches, the immuno memory note (only
        when an immunopeptidomics point is drawn), the y scales of Fig 4, FigS8's identical counts and memory maxima
        over the samples that are not decision samples (as lowmem.identical_all), and no decision fact; the narrow
        out-of-memory label of Fig 3 with lines closer than matplotlib's default."""
        from matplotlib.collections import LineCollection
        plt = self.pyplot()
        tabs = figures.Tables(FX)
        with plt.rc_context(figures.rc_params()):
            fig, _ = figures.fig_calibration(plt, tabs)
            try:
                figures.finish(fig)
                k = 72.0 / fig.dpi
                diamonds = [(ax, ln) for ax in fig.axes for ln in ax.lines if ln.get_marker() == "D"]
                self.assertTrue(diamonds)
                for ax, ln in diamonds:
                    xy = (ln.get_xdata()[0], ln.get_ydata()[0])
                    dx = (ln.get_transform().transform(xy)[0] - ax.transData.transform(xy)[0]) * k
                    self.assertAlmostEqual(dx, figures.NATURAL_BESIDE_PT, places=3)
                    arms = [a for a in ax.lines if a.get_marker() not in ("D", "None", "", None)]
                    self.assertLess(ln.get_zorder(), min(a.get_zorder() for a in arms))
                handle = next(h for h in fig.legends[0].legend_handles
                              if getattr(h, "get_marker", lambda: None)() == "D")
                self.assertLessEqual(handle.get_markersize(), 2.2)
                # the arm shapes in the legend at the size of the change rows' markers (print2-1), next to the
                # 3.4 pt engine dots without an edge
                leg = fig.legends[0]
                shapes = {t.get_text(): h for h, t in zip(leg.legend_handles, leg.get_texts())
                          if t.get_text() in figures.CAL_LABEL.values()}
                self.assertEqual(len(shapes), 4)
                drawn = {(ln.get_markersize(), ln.get_markeredgewidth()) for ln in fig.axes[0].lines
                         if ln.get_marker() in figures.CAL_MARKER.values()}
                self.assertEqual(drawn, {(figures.CAL_MARK["ms"], figures.CAL_MARK["mew"])})
                for label, h in shapes.items():
                    self.assertEqual((h.get_markersize(), h.get_markeredgewidth()), drawn.copy().pop(), label)
                engines = [h for h, t in zip(leg.legend_handles, leg.get_texts())
                           if t.get_text() in figures.D.ENGINE_NAME.values()]
                self.assertEqual({(h.get_markersize(), h.get_markeredgewidth()) for h in engines},
                                 {(figures.HANDLE_DOT_MS, 0)})
                # the SD bars of C and D have their legend entry, as in Fig 2, FigS4 and FigS5
                self.assertTrue(any(isinstance(h, LineCollection) for h in fig.legends[0].legend_handles))
                self.assertIn(figures.VOCAB["shuffled"], [t.get_text() for t in fig.legends[0].get_texts()])
                # each arm at one x in all four rows (a reader reads down a column); A and B have no default slot
                from matplotlib.colors import to_hex
                at = []  # per row: {(engine colour, arm marker): offsets within the category}
                for ax in fig.axes:
                    at.append({})
                    for ln in ax.lines:
                        if ln.get_marker() not in ("D", "x", "None", "", None):
                            x = ln.get_xdata()[0]
                            at[-1].setdefault((to_hex(ln.get_markeredgecolor()), ln.get_marker()), set()).add(
                                round(x - round(x), 9))
                self.assertEqual(len(at), 4)
                self.assertEqual({len(v) for row in at for v in row.values()}, {1})
                for change in at[:2]:
                    for key, offs in change.items():
                        self.assertEqual(offs, at[2][key], key)
                        self.assertEqual(offs, at[3][key], key)
                    self.assertLess(len(change), len(at[2]))
                # the run of each column (the tick labels name its dataset)
                rows = tabs.read("O19_calibration_counts")[1]
                self.assertEqual(sorted(fig.facts["runs"].split(",")), sorted({r["unit"] for r in rows}))
                self.assertEqual(fig.facts["runs_per_dataset"], "1")
            finally:
                plt.close(fig)
            fig, _ = figures.fig_electron(plt, tabs)
            try:
                self.assertTrue(any(isinstance(h, LineCollection) for h in fig.legends[0].legend_handles))
                self.assertIn(figures.VOCAB["shuffled"], [t.get_text() for t in fig.legends[0].get_texts()])
            finally:
                plt.close(fig)
            # the memory note names only what is drawn: no immunopeptidomics point in Fig 3, no note
            untimed = os.path.join(self.tmp, "immuno_untimed")
            copy_tables(untimed, edit=lambda name, text: edit_columns(
                text, lambda r: {"state": "not_run", "wall_med_s": "NA", "rss_med_gib": "NA"}
                if figures.D.kind(r["group"]) == "immuno" else {}) if name == "O15_time_runs" else text)
            fig, _ = figures.fig_time_per_file(plt, figures.Tables(untimed))
            try:
                self.assertNotIn("immuno_memory", fig.facts)
            finally:
                plt.close(fig)
            # FigS8: identical counts and memory maxima over the samples that are not decision samples (the fixture's
            # two DN13 class I samples are drawn); a made-up decision sample with the largest memory changes neither
            rows = [r for r in tabs.read("O10_low_memory")[1] if r["role"] in figures.ROLES]
            use = [r for r in rows if r["role"] != "decision"]
            self.assertTrue(len(use) < len(rows))
            want = {"identical": f"{sum(r['identical'] == 'yes' for r in use)}/{len(use)}",
                    "rss_std_max_gib": f"{max(float(r['rss_std_gib']) for r in use if r['rss_std_gib'] != 'NA'):.1f}",
                    "rss_lm_max_gib": f"{max(float(r['rss_lm_gib']) for r in use if r['rss_lm_gib'] != 'NA'):.1f}"}
            larger = os.path.join(self.tmp, "lowmem_decision")
            copy_tables(larger, edit=lambda name, text: edit_columns(
                text, lambda r: {"identical": "no", "rss_std_gib": "199.0", "rss_lm_gib": "198.0"}
                if r["role"] == "decision" else {}) if name == "O10_low_memory" else text)
            for folder in (FX, larger):
                fig, _ = figures.fig_low_memory(plt, figures.Tables(folder))
                try:
                    self.assertEqual({k: fig.facts[k] for k in want}, want, folder)
                finally:
                    plt.close(fig)
            for func in (figures.fig_immuno, figures.fig_low_memory, figures.fig_time_per_file):
                fig, _ = func(plt, tabs)
                try:
                    self.assertFalse([k for k in fig.facts if "decision" in k or k == "heldout_same_donor"],
                                     func.__name__)
                    if func is figures.fig_immuno:
                        self.assertEqual(fig.facts["y_scales"], "independent per panel")
                    if func is figures.fig_time_per_file:
                        self.assertEqual(fig.facts["out_of_memory"],
                                         "Sage pxd058436_classII (3 samples), Sage pxd019643_classII (3 samples)")
                        self.assertIn("not divided", fig.facts["immuno_memory"])
                        for key in ("out_of_memory", "immuno_memory"):
                            self.assertNotIn(";", fig.facts[key], key)  # index.tsv separates facts with "; "
                        self.assertEqual(fig.facts["hypervisor"], "NA")  # no O18_machines in the fixture
                        figures.finish(fig)
                        narrow = figures.VOCAB["engine_out_of_memory_narrow"].format("Sage")
                        t = next(t for t in fig.axes[0].texts if t.get_text() == narrow)
                        renderer = fig.canvas.get_renderer()
                        tight = t.get_window_extent(renderer).height
                        t.set_linespacing(1.2)
                        self.assertLess(tight, t.get_window_extent(renderer).height)
                finally:
                    plt.close(fig)

    @needs_matplotlib
    def test_decision_runs_have_no_mark(self):
        """Decision runs have no mark of their own (owner, 2026-11-28): Fig 3, Fig 4, FigS4, FigS5, FigS8 and FigS10
        draw the fixture's decision rows exactly as the same rows with role 'heldout' (the same lines and markers,
        bars, error bars, texts, tick labels and legend); FigS4 and FigS5 draw the shared mean +- SD of every run with
        one, decision runs included (O11 has it for them: fdp.shared_stems has no decision rule); the bars of Fig 4
        and FigS8 are in an engine colour or white."""
        from matplotlib.colors import to_hex
        from matplotlib.patches import Rectangle
        plt = self.pyplot()
        tabs = figures.Tables(FX)
        tables = {figures.fig_time_per_file: "O15_time_runs", figures.fig_immuno: "O09_immuno_samples",
                  figures.fig_fdp: "O11_fdp_runs", figures.fig_electron: "O08_electron_runs",
                  figures.fig_low_memory: "O10_low_memory", figures.fig_matched_fdp: "O13_matched_fdp"}
        for name in tables.values():  # not empty: the fixture has decision rows in each of these tables
            self.assertTrue([r for r in tabs.read(name)[1] if r["role"] == "decision"], name)
        heldout = os.path.join(self.tmp, "no_decision")
        copy_tables(heldout, edit=lambda name, text: edit_columns(
            text, lambda r: {"role": "heldout"} if r.get("role") == "decision" else {}))

        def shown(fig):
            """What a finished figure shows, per axes, as values that two draws can compare."""
            figures.finish(fig)
            out = []
            for ax in fig.axes:
                out.append([(ln.get_marker(), ln.get_markersize(), ln.get_markeredgewidth(),
                             repr(ln.get_markerfacecolor()), repr(ln.get_markeredgecolor()), repr(ln.get_color()),
                             ln.get_linestyle(), ln.get_zorder(), tuple(ln.get_xdata()), tuple(ln.get_ydata()))
                            for ln in ax.lines])
                out.append([(p.get_x(), p.get_width(), p.get_height(), to_hex(p.get_facecolor()),
                             to_hex(p.get_edgecolor()), p.get_linewidth(), p.get_zorder())
                            for p in ax.patches if isinstance(p, Rectangle)])
                out.append([(type(c).__name__, c.get_zorder(),
                             tuple(tuple(map(tuple, s)) for s in getattr(c, "get_segments", list)()))
                            for c in ax.collections])
                out.append([t.get_text() for t in ax.texts])
                out.append([t.get_text() for t in ax.get_xticklabels()])
            out.append([t.get_text() for leg in fig.legends for t in leg.get_texts()])
            return out
        allowed = {to_hex(c) for c in figures.D.COLOUR.values()} | {"#ffffff"}
        with plt.rc_context(figures.rc_params()):
            for func in tables:
                figs = [func(plt, tabs)[0], func(plt, figures.Tables(heldout))[0]]
                try:
                    self.assertEqual(shown(figs[0]), shown(figs[1]), func.__name__)
                    if func in (figures.fig_immuno, figures.fig_low_memory):
                        colours = {to_hex(c) for ax in figs[0].axes for p in ax.patches if isinstance(p, Rectangle)
                                   for c in (p.get_facecolor(), p.get_edgecolor())}
                        self.assertTrue(colours)
                        self.assertLessEqual(colours, allowed, func.__name__)
                finally:
                    for fig in figs:
                        plt.close(fig)
            # FigS4 and FigS5: one dot (with its SD bar) per run and engine with a shared mean, decision runs included
            o11 = [r for r in tabs.read("O11_fdp_runs")[1] if r["design"] == "shuffled" and r["mean_shared"] != "NA"]
            o08 = {(r["unit"], r["level"]) for r in tabs.read("O08_electron_runs")[1]}
            for func, want in (
                    (figures.fig_fdp, [r for r in o11 if figures.D.kind(r["group"]) != "immuno"]),
                    (figures.fig_electron, [r for r in o11 if (r["unit"], r["level"]) in o08
                                            and r["engine"] in ("prose", "msfragger")])):
                self.assertTrue([r for r in want if r["role"] == "decision"], func.__name__)
                fig, _ = func(plt, tabs)
                try:
                    dots = [ln for ax in fig.axes for ln in ax.lines if ln.get_marker() == "o"]
                    self.assertEqual(len(dots), len(want), func.__name__)
                    self.assertFalse([ln for ln in dots if ln.get_markerfacecolor() == "white"], func.__name__)
                finally:
                    plt.close(fig)

    @needs_matplotlib
    def test_every_figure_is_camera_ready(self):
        """C3, C4, C5 and the letters of C7 on every figure drawn from the fixture tables: text size, no '$' or code
        name, nothing outside the page, no overlapping texts, rotated labels spaced, y labels not taller than their
        axes, no alpha below 1; every multi-panel figure has bold letters A, B, ... in reading order; legend handles
        near the size of their marks (handle_problems); no text says "decision" (decision runs have no mark of their
        own) or "tuning" (ProSE was developed using those datasets; owner, 2026-11-28)."""
        plt = self.pyplot()
        tabs = figures.Tables(FX)
        problems = []
        with plt.rc_context(figures.rc_params()):
            for name, func, args in figures.FIGURES:
                fig, _ = func(plt, tabs, *args)
                try:
                    figures.finish(fig)
                    problems += [f"{name}: {p}" for p in text_problems(fig)]
                    problems += [f"{name}: {p}" for p in handle_problems(fig, name)]
                    texts = self.assert_camera_ready_texts(fig)
                    problems += [f"{name}: says {t!r}" for t in texts if re.search(r"decision|tuning", t, re.I)]
                    if len(fig.axes) > 1:
                        self.assert_letters(fig, figures.PANEL_LETTERS[:len(fig.axes)])
                finally:
                    plt.close(fig)
        self.assertEqual(problems, [])

    @needs_matplotlib
    def test_the_checks_catch_known_faults(self):
        """pdf_problems (C2, C6) and text_problems (C3-C5) find the faults of the figures before the camera-ready
        work, each on a small figure that has only that fault: a 4.9 pt mathtext subscript, a 0.3 pt stroke, alpha
        0.45, a 9.5 in page; a 5 pt text, '$', a code name, a text off the page, two overlapping texts, crowded
        rotated labels, a hyphen-minus, a number without its thousands comma, a y label taller than its axes; and
        handle_problems an engine dot with matplotlib's default edge and a handle under 2.4 pt."""
        plt = self.pyplot()
        from matplotlib import ticker
        with plt.rc_context(figures.rc_params()):
            fig = plt.figure(figsize=(figures.WIDTH, 9.5))
            fig.text(0.1, 0.1, "x", fontsize=4.9)
            fig.add_artist(plt.Line2D([0.2, 0.8], [0.5, 0.5], lw=0.3))
            fig.add_artist(plt.Rectangle((0.2, 0.6), 0.1, 0.1, alpha=0.45, transform=fig.transFigure))
            pdf = os.path.join(self.tmp, "faults.pdf")
            fig.savefig(pdf)
            plt.close(fig)
            self.assertEqual([p.split(": ", 1)[1] for p in pdf_problems(pdf)],
                             ["text 4.9 pt", "stroke 0.3 pt", "alpha 0.45", "page 7.00 x 9.50 in"])

            def found(build, rows=1):
                fig = plt.figure(figsize=(figures.WIDTH, 3.0), layout="constrained")
                ax = fig.subplots(rows, 1, squeeze=False)[rows // 2][0]  # the middle one: its label stays on the page
                build(fig, ax)
                fig.canvas.draw()
                try:
                    return sorted({p.split(":")[0].split(" ")[0] for p in text_problems(fig)})
                finally:
                    plt.close(fig)

            def crowded(fig, ax):
                ax.set_xticks(range(80))
                ax.set_xticklabels([f"dataset {i}" for i in range(80)], rotation=40, ha="right",
                                   rotation_mode="anchor")
            cases = [
                (lambda fig, ax: ax.set_title("PSM level"), 1, []),
                (lambda fig, ax: ax.text(0.5, 0.5, "small", fontsize=5), 1, ["size"]),
                (lambda fig, ax: ax.text(0.5, 0.5, "$L_T$ +5.6%"), 1, ["code"]),
                (lambda fig, ax: ax.text(0.5, 0.5, "td accepted, per_file"), 1, ["code"]),
                (lambda fig, ax: fig.text(0.99, 0.5, "beyond the edge"), 1, ["outside"]),
                (lambda fig, ax: (ax.text(0.5, 0.5, "grade"), ax.text(0.52, 0.5, "−40")), 1, ["overlap"]),
                (crowded, 1, ["rotated"]),
                (lambda fig, ax: (ax.set_ylim(-10, 10), ax.yaxis.set_major_formatter(
                    ticker.FuncFormatter(lambda v, _: f"{v:g}"))), 1, ["number"]),
                (lambda fig, ax: (ax.set_ylim(0, 20000), ax.yaxis.set_major_formatter(
                    ticker.FuncFormatter(lambda v, _: f"{v:.0f}"))), 1, ["number"]),
                (lambda fig, ax: ax.set_ylabel("a long y label " * 2), 3, ["y"]),
            ]
            for build, rows, expected in cases:
                self.assertEqual(found(build, rows), expected)
            # handle_problems: the engine dot of round 2 (ms 4 with the default 1 pt edge, 5.0 pt), a 2 pt handle
            fig = plt.figure(figsize=(figures.WIDTH, 3.0))
            fig.legend(handles=[plt.Line2D([], [], color="C0", marker="o", ls="none", ms=4, label="ProSE"),
                                plt.Line2D([], [], color="C1", marker="s", ls="none", ms=2, mew=0, label="a mark")])
            try:
                self.assertEqual(handle_problems(fig, "fig_batch"),
                                 ["engine handle 'ProSE': ms 4, mew 1", "handle 'a mark': 2 pt across"])
            finally:
                plt.close(fig)

    @needs_matplotlib
    def test_immuno_drops_the_empty_slot(self):
        """Fig 4 (F4.2, D7): with prose_other NA in every row three bars per sample (offsets -0.16, 0, 0.16) and the
        legend entry "ProSE"; with values four bars, the main arrangement filled and the other one open (G7)."""
        plt = self.pyplot()
        from matplotlib.patches import Rectangle
        tables_dir = os.path.join(self.tmp, "tables")
        copy_tables(tables_dir, edit=lambda name, text: edit_columns(
            text, lambda r: {"prose_other": str(round(float(r["prose_main"]) * 0.97))}) if name == "O09_immuno_samples"
            else text)
        with plt.rc_context(figures.rc_params()):
            for folder, n_bars, words in ((FX, 3, ["ProSE"]),
                                          (tables_dir, 4, ["ProSE, per-file rescoring (main)",
                                                           "ProSE, joint rescoring"])):
                fig, info = figures.fig_immuno(plt, figures.Tables(folder))
                try:
                    legend = [t.get_text() for t in fig.legends[0].get_texts()]
                    for word in words:
                        self.assertIn(word, legend)
                    self.assertFalse([w for w in legend if "per_file" in w or "other arrangement" in w])
                    class_i = fig.axes[0]
                    bars = [p for p in class_i.patches if isinstance(p, Rectangle)]
                    self.assertEqual(len(bars), 3 * n_bars)
                    offsets = sorted({round(p.get_x() + p.get_width() / 2 - round(p.get_x()), 2) for p in bars})
                    width = figures.IMMUNO_BAR
                    self.assertEqual(offsets, [round((k - (n_bars - 1) / 2) * width, 2) for k in range(n_bars)])
                    opens = [p for p in bars if p.get_facecolor()[:3] == (1.0, 1.0, 1.0)]
                    self.assertEqual(len(opens), 0 if n_bars == 3 else 3)
                    self.assertEqual("slot dropped" in info, n_bars == 3)
                finally:
                    plt.close(fig)

    @needs_matplotlib
    def test_sage_not_run_and_batch_panels(self):
        """G15, F3.2, S5: "Sage: not run" once below the time axis of Fig 3 and fig_batch A, centered under the
        electron block, from O14 (also when the figure's own table has no Sage row there) and not without the rows
        of either table; on two lines under fig_batch's single electron-based category, where one line is wider
        than the category; fig_batch has two panels with filled markers only and no x on its time axis."""
        plt = self.pyplot()
        word, narrow = figures.VOCAB["sage_not_run"], figures.VOCAB["sage_not_run_narrow"]
        no_sage = os.path.join(self.tmp, "no_sage")  # O15 without its not_run_by_design Sage rows: O14 alone
        copy_tables(no_sage, edit=lambda name, text: drop_rows(
            text, lambda r: r["engine"] == "sage" and r["state"] == "not_run_by_design") if name == "O15_time_runs"
            else text)
        neither = os.path.join(self.tmp, "neither")
        copy_tables(neither, drop=("O14_coverage",), edit=lambda name, text: drop_rows(
            text, lambda r: r["engine"] == "sage" and r["state"] == "not_run_by_design") if name == "O15_time_runs"
            else text)
        with plt.rc_context(figures.rc_params()):
            for folder, expected in ((FX, 1), (no_sage, 1), (neither, 0)):
                fig, _ = figures.fig_time_per_file(plt, figures.Tables(folder))
                try:
                    labels = [t for t in fig.axes[0].texts if t.get_text() == word]
                    self.assertEqual(len(labels), expected, folder)
                    if labels:
                        electron = [i for i, g in enumerate(figures.ordered_groups(
                            figures.D.ALL_GROUPS)) if figures.D.kind(g) == "electron"]
                        self.assertEqual(labels[0].xy[0], (electron[0] + electron[-1]) / 2)
                        self.assertIn("sage_not_run_reason", fig.facts)
                finally:
                    plt.close(fig)
            fig, _ = figures.fig_time_per_file(plt, figures.Tables(FX))
            try:
                figures.finish(fig)  # five electron-based categories: one line
                self.assertEqual([t.get_text() for t in fig.axes[0].texts].count(word), 1)
            finally:
                plt.close(fig)
            fig, _ = figures.fig_batch(plt, figures.Tables(FX))
            try:
                figures.finish(fig)
                self.assertEqual(len(fig.axes), 2)
                self.assert_letters(fig, "AB")
                texts = [t.get_text() for t in fig.axes[0].texts]
                self.assertEqual((texts.count(word), texts.count(narrow)), (0, 1))
                self.assertEqual([ln for ln in fig.axes[0].lines if ln.get_marker() == "x"], [])
                dots = [ln for ax in fig.axes for ln in ax.lines if ln.get_marker() == "o"]
                self.assertTrue(dots)
                self.assertTrue(all(ln.get_markerfacecolor() == ln.get_markeredgecolor() for ln in dots))
                self.assertEqual(fig.axes[0].get_yscale(), "log")
                self.assertEqual(fig.axes[1].get_ylabel(), figures.VOCAB["batch_ratio"])
            finally:
                plt.close(fig)

    @needs_matplotlib
    def test_dodge_without_empty_slots_and_block_separators(self):
        """Fig 3 and FigS6 dodge only the engines with a row in a category, as FigS4: in an electron-based column
        (no Sage) ProSE and MSFragger stand at -/+ half the dodge, in a tryptic column the three engines at -dodge, 0
        and +dodge; FigS5 draws a separator between its class blocks only, not between the datasets of a block, and
        each block name stands over the middle of its block."""
        from matplotlib.colors import same_color
        plt = self.pyplot()
        tabs = figures.Tables(FX)

        def centres(ax, x):  # {engine: the mean x offset of its marks in category x}
            out = {}
            for ln in ax.lines:
                if ln.get_marker() == "o" and round(ln.get_xdata()[0]) == x:
                    e = next(e for e in figures.D.ENGINES
                             if same_color(ln.get_markeredgecolor(), figures.D.COLOUR[e]))
                    out.setdefault(e, []).append(ln.get_xdata()[0] - x)
            return {e: round(sum(v) / len(v), 6) for e, v in out.items()}
        with plt.rc_context(figures.rc_params()):
            for func, table, width, electron in ((figures.fig_time_per_file, "O15_time_runs", 0.27, "pxd011695_AI-ETD"),
                                                 (figures.fig_batch, "O16_batch", 0.22, "pxd065289_etcid")):
                fig, _ = func(plt, tabs)
                try:
                    groups = figures.ordered_groups(r["group"] for r in tabs.read(table)[1])
                    for ax in fig.axes:
                        self.assertEqual(centres(ax, groups.index(electron)),
                                         {"prose": round(-width / 2, 6), "msfragger": round(width / 2, 6)}, func)
                        self.assertEqual(centres(ax, groups.index("hfx")),
                                         {"prose": round(-width, 6), "sage": 0.0, "msfragger": round(width, 6)}, func)
                finally:
                    plt.close(fig)
            fig, _ = figures.fig_electron(plt, tabs)
            try:
                rows = tabs.read("O08_electron_runs")[1]
                items = sorted(dict.fromkeys((r["group"], r["unit"]) for r in rows),
                               key=lambda it: figures.D.order_key(it[0]))
                xs = figures.unit_positions(items)
                blocks = []  # [class, first x, last x]
                for (g, _), x in zip(items, xs):
                    b = figures.D.cls(g) if figures.D.cls(g) != "-" else figures.block_of(g)
                    if blocks and blocks[-1][0] == b:
                        blocks[-1][2] = x
                    else:
                        blocks.append([b, x, x])
                self.assertGreater(len(set(g for g, _ in items)), len(blocks))  # more datasets than blocks
                want = [(a[2] + b[1]) / 2 for a, b in zip(blocks, blocks[1:])]
                for ax in fig.axes:
                    seps = sorted(ln.get_xdata()[0] for ln in ax.lines if ln.get_color() == figures.SEPARATOR["color"])
                    self.assertEqual(seps, want)
                names = {t.get_text(): t.xy[0] for t in fig.axes[0].texts}
                for b, x0, x1 in blocks:
                    name = figures.BLOCK_NAME.get(b, b)
                    at = next(v for k, v in names.items() if k.startswith(name))
                    self.assertEqual(at, (x0 + x1) / 2, name)
            finally:
                plt.close(fig)

    @needs_matplotlib
    def test_untimed_searches_have_no_x_in_the_second_panel(self):
        """G15: a search without a time is one label between the panels of Fig 3 and fig_batch and no x at the base
        of the second panel (it would read as the least memory or the best ratio); a timed batch without a ratio
        keeps the x with its label."""
        plt = self.pyplot()
        untimed = os.path.join(self.tmp, "untimed")

        def edit(name, text):
            if name == "O15_time_runs":
                return edit_columns(text, lambda r: {"state": "not_run", "wall_med_s": "NA", "rss_med_gib": "NA"}
                                    if (r["engine"], r["unit"]) == ("prose", "velos_125_R1") else {})
            if name == "O16_batch":
                return edit_columns(text, lambda r: {"batch_wall_per_file_s": "NA", "ratio_wall": "NA",
                                                     "note": "not_run"} if (r["engine"], r["group"]) ==
                                    ("prose", "velos") else {"ratio_wall": "NA", "note": "failed"}
                                    if (r["engine"], r["group"]) == ("prose", "lumos_tmt") else {})
            return text
        copy_tables(untimed, edit=edit)
        tabs = figures.Tables(untimed)
        with plt.rc_context(figures.rc_params()):
            for make in (figures.fig_time_per_file, figures.fig_batch):
                fig, _ = make(plt, tabs)
                try:
                    figures.finish(fig)
                    top, second = fig.axes[0], fig.axes[1]
                    self.assertIn("not run", [t.get_text() for t in top.texts], make.__name__)
                    self.assertEqual([ln for ln in top.lines if ln.get_marker() == "x"], [])
                    base = [ln for ln in second.lines if ln.get_marker() == "x"
                            and list(ln.get_ydata()) != [figures.D.CAP_GIB]]
                    if make is figures.fig_batch:  # lumos_tmt: timed, no ratio
                        self.assertEqual(len(base), 1)
                        self.assertIn("failed", [t.get_text() for t in second.texts])
                    else:
                        self.assertEqual(base, [])
                finally:
                    plt.close(fig)

    @needs_matplotlib
    def test_marks_without_x_and_opaque_labels(self):
        """Marks.add(mark=False): the label without the x (G15); the label box is opaque (G5)."""
        plt = self.pyplot()
        with plt.rc_context(figures.rc_params()):
            fig, ax = plt.subplots()
            try:
                marks = figures.Marks(ax)
                marks.add(0, "not run", mark=False)
                marks.add(5, "out of memory")
                marks.draw()
                xs = [ln for ln in ax.lines if ln.get_marker() == "x"]
                self.assertEqual([list(ln.get_xdata()) for ln in xs], [[5]])
                self.assertEqual(sorted(t.get_text() for t in ax.texts), ["not run", "out of memory"])
                for t in ax.texts:
                    box = t.get_bbox_patch()
                    self.assertIsNone(box.get_alpha())
                    self.assertEqual(box.get_facecolor()[3], 1.0)
            finally:
                plt.close(fig)
            # a label wider than its categories takes its narrow form; one that fits keeps its line
            fig, ax = plt.subplots(figsize=(figures.WIDTH, 2.0))
            try:
                ax.set_xlim(-0.6, 16.6)
                marks = figures.Marks(ax)
                for x in (0, 1, 2, 3, 16):
                    marks.add(x, figures.VOCAB["sage_not_run"], mark=False, narrow=figures.VOCAB["sage_not_run_narrow"])
                marks.draw(mode="below")
                figures.finish(fig)
                self.assertEqual([t.get_text() for t in ax.texts],
                                 [figures.VOCAB["sage_not_run"], figures.VOCAB["sage_not_run_narrow"]])
                self.assertEqual([ln for ln in ax.lines if ln.get_marker() == "x"], [])
            finally:
                plt.close(fig)

    @needs_matplotlib
    def test_axis_helpers(self):
        plt = self.pyplot()
        with plt.rc_context(figures.rc_params()):
            fig, axs = plt.subplots(1, 2)
            try:
                figures.fdp_axis(axs[0], [1.2, 2.1, None, float("nan")])
                self.assertEqual(axs[0].get_ylim(), (0.0, 2.5))
                self.assertEqual(axs[0].get_ylabel(), figures.VOCAB["fdp"])
                figures.fdp_axis(axs[0], [0.4])
                self.assertEqual(axs[0].get_ylim(), (0.0, figures.FDP_MIN_TOP))
                figures.fdp_axis(axs[0], [2.5])
                self.assertEqual(axs[0].get_ylim(), (0.0, 3.0))
                formatter = axs[0].yaxis.get_major_formatter()
                self.assertEqual(formatter(-0.5, 0), "−0.5")
                self.assertEqual(formatter(1.0, 0), "1")
                step = figures.tick_step(axs, [(-3.0, 25.0), (2.0, 48.0)])
                self.assertEqual(step, 10)
                for ax in axs:
                    lo, hi = ax.get_ylim()
                    self.assertLess(lo, 0.0)
                    self.assertGreater(hi, 0.0)
                self.assertEqual(figures.tick_step(axs[:1], [(0.0, 3.0)]), 1)
            finally:
                plt.close(fig)

    @needs_matplotlib
    def test_whole_dashes_and_clear_log_ends(self):
        """The held-out legend handle shows the line's (4, 2) dashes as whole dashes, centered (F1.2: without the
        offset it ends in a 0.4 pt stub), and so does Fig 2's 1% handle (three dashes); a log time axis takes one decade more at an end that a marker would come
        within EDGE_CLEAR_PT of, once the layout is known (G10: still whole decades); the x of a missing value at the
        axis base does not count."""
        def dashes(style, lw, length):  # the dashes drawn over [0, length] points: the line starts offset into them
            offset, (on, off) = style
            out, pos = [], -offset * lw
            while pos < length:
                a, b = max(pos, 0.0), min(pos + on * lw, length)
                if b > a:
                    out.append((round(a, 9), round(b, 9)))
                pos += (on + off) * lw
            return out
        length, lw = figures.HANDLE_LENGTH * figures.FONT_PT, figures.MEAN_LINE_LW
        self.assertEqual(dashes((0, figures.HELDOUT_DASHES), lw, length)[-1], (10.8, 11.2))  # the stub
        drawn = dashes(figures.whole_dashes(figures.HELDOUT_DASHES, lw), lw, length)
        self.assertEqual(len(drawn), 2)
        for a, b in drawn:
            self.assertAlmostEqual(b - a, figures.HELDOUT_DASHES[0] * lw)
        self.assertAlmostEqual(drawn[0][0], length - drawn[-1][1])
        self.assertEqual(dashes(figures.whole_dashes((4, 2), 0.7), 0.7, length), [(0.0, 2.8), (4.2, 7.0), (8.4, 11.2)])
        with mock.patch.object(figures, "whole_dashes", wraps=figures.whole_dashes) as whole:
            figures.lead_handles(True)
        whole.assert_called_once_with(figures.HELDOUT_DASHES, lw)
        # Fig 2's 1% handle (0.7 pt, matplotlib's '--' pattern): three whole dashes, centered, no end stub
        one_lw = figures.ONE_PERCENT["lw"]
        a, b = dashes((0, figures.ONE_PERCENT_DASHES), one_lw, length)[-1]
        self.assertLess(b - a, 0.1)  # without the offset: a 0.07 pt stub
        drawn = dashes(figures.whole_dashes(figures.ONE_PERCENT_DASHES, one_lw), one_lw, length)
        self.assertEqual(len(drawn), 3)
        for a, b in drawn:
            self.assertAlmostEqual(b - a, figures.ONE_PERCENT_DASHES[0] * one_lw)
        self.assertAlmostEqual(drawn[0][0], length - drawn[-1][1])
        plt = self.pyplot()
        from matplotlib.transforms import blended_transform_factory
        with plt.rc_context(figures.rc_params()):
            self.assertEqual(tuple(plt.rcParams["lines.dashed_pattern"]), figures.ONE_PERCENT_DASHES)
            with mock.patch.object(figures, "whole_dashes", wraps=figures.whole_dashes) as whole:
                fig, _ = figures.fig_fdp_main(plt, figures.Tables(FX))
                plt.close(fig)
            whole.assert_called_once_with(figures.ONE_PERCENT_DASHES, one_lw)
            for low, high, want in ((0.0105, 5.0, (0.001, 10.0)), (0.03, 5.0, (0.01, 10.0)),
                                    (0.03, 9.8, (0.01, 100.0))):
                fig = plt.figure(figsize=(3.0, 1.5), layout="constrained")
                ax = fig.add_subplot()
                try:
                    ax.set_yscale("log")
                    ax.plot([0, 1], [low, high], ls="none", marker="o", ms=3)
                    ax.plot([0.5], [0.0], ls="none", marker="x", ms=4, clip_on=False,
                            transform=blended_transform_factory(ax.transData, ax.transAxes))
                    figures.decade_limits(ax, [low, high])
                    figures.log_ticks(ax)
                    self.assertEqual(ax.get_ylim(), (0.01, 10.0))
                    figures.finish(fig)
                    got = ax.get_ylim()
                    for g, w in zip(got, want):
                        self.assertAlmostEqual(math.log10(g), math.log10(w), places=9, msg=(low, high, got))
                finally:
                    plt.close(fig)

    @needs_matplotlib
    def test_left_out_groups_shared_rows_and_one_grade_label(self):
        """index.tsv names what Fig 4, FigS2/S3 and FigS6 leave out or mark missing, with the reason (the caption
        must say it): Fig 4's out-of-memory samples, FigS2's class II groups (the engine reason of O03_three_datasets,
        else 'not counted by all three engines') and electron-based datasets ('Sage not run' from O14), FigS6's
        one-file datasets and pooled samples. FigS2 B shares y with A and has no "grade" label of its own. FigS9 A and
        B share one y range. FigS4 asks the caption to say what the triangles are."""
        plt = self.pyplot()
        tabs = figures.Tables(FX)
        o3 = os.path.join(self.tmp, "o3")
        copy_tables(o3)
        with open(os.path.join(o3, "O03_three_datasets.tsv"), "w", encoding="utf-8", newline="") as f:
            f.write("level\tgroup\tn_used\tnote\n"
                    "psm\tpxd058436_classII\t0\tdropped: no run in the set (DS:897); pxd058436_DN05_Thyroid_classII "
                    "sage:failed_memory; pxd058436_DN13_Tongue_classII sage:failed_memory\n"
                    "peptide\tpxd058436_classII\t0\tdropped: no run in the set (DS:897)\n")
        with plt.rc_context(figures.rc_params()):
            fig, _ = figures.fig_immuno(plt, tabs)
            try:
                self.assertEqual(fig.facts["out_of_memory"],
                                 "Sage pxd058436_classII (3 samples), Sage pxd019643_classII (3 samples)")
            finally:
                plt.close(fig)
            fig, _ = figures.fig_batch(plt, tabs)
            try:
                left = fig.facts["left_out"].split(", ")
                self.assertEqual(left[0], "pxd011695_HCD (one file: no batch)")
                self.assertIn("pxd011695_EThcD (one file: no batch)", left)
                self.assertEqual(left[-4:], [f"{g} (pooled samples: not in the batch arm)"
                                             for g in figures.ordered_groups(figures.D.IMMUNO)])
                self.assertEqual(len(left), 9)
            finally:
                plt.close(fig)
            for folder, level, oom in ((FX, "psm", "not counted by all three engines"),
                                       (o3, "psm", "Sage out of memory"),
                                       (o3, "peptide", "not counted by all three engines")):
                fig, _ = figures.fig_ids_counts(plt, figures.Tables(folder), level)
                try:
                    left = fig.facts["left_out"].split(", ")
                    self.assertIn(f"pxd058436_classII ({oom})", left)
                    self.assertIn("pxd019643_classII (not counted by all three engines)", left)
                    for g in figures.D.ELECTRON:
                        self.assertIn(f"{g} (Sage not run)", left)
                    self.assertEqual(len(left), len(figures.D.ELECTRON) + 2)
                    figures.finish(fig)
                    grade = [ax for ax in fig.axes for t in ax.texts if t.get_text() == figures.VOCAB["grade"]]
                    self.assertEqual(grade, [fig.axes[0]])
                    self.assertTrue(any(t.get_text() in ("A", "B", "C") for t in fig.axes[1].texts))
                finally:
                    plt.close(fig)
            fig, _ = figures.fig_calibration(plt, tabs)
            try:
                self.assertEqual(fig.axes[0].get_ylim(), fig.axes[1].get_ylim())
            finally:
                plt.close(fig)
            fig, _ = figures.fig_fdp(plt, tabs)
            try:
                self.assertIn("Arabidopsis", fig.facts["arath_marks"])
            finally:
                plt.close(fig)

    @needs_matplotlib
    def test_fdp_left_out_names_every_group_not_drawn(self):
        """Fig 2 and FigS4 name in left_out every design group they do not draw, with the reason (fdp_left_out):
        the electron-based groups of Fig 2 are in FigS4; an immunopeptidomics group without an O11 row has 'no
        entrapment search' when O14_coverage has no entrapment search of it, else (O14 has one, or is absent) 'no row
        in O11', as any other group without an O11 row; an immunopeptidomics group with an O11 row is 'not drawn'."""
        plt = self.pyplot()
        immuno = list(figures.D.IMMUNO)
        searched, with_row = immuno[0], immuno[2]  # an entrapment search in O14; an O11 row

        def add_row(text, change):
            """The table text plus a copy of its first data row with change applied."""
            lines = text.splitlines()
            head = next(i for i, x in enumerate(lines) if not x.startswith("#"))
            cols = lines[head].split("\t")
            row = dict(zip(cols, lines[head + 1].split("\t")), **change)
            return "\n".join(lines + ["\t".join(row[c] for c in cols)]) + "\n"

        def edit(name, text):
            if name == "O14_coverage":
                return add_row(text, {"group": searched, "kind": "immuno", "db_design": "shuffled"})
            if name == "O11_fdp_runs":
                text = drop_rows(text, lambda r: r["group"] in ("velos", "pxd011695_ETD"))
                return add_row(text, {"group": with_row, "kind": "immuno", "unit": "u_y"})
            return text
        changed, no_o14 = os.path.join(self.tmp, "changed"), os.path.join(self.tmp, "no_o14")
        copy_tables(changed, edit=edit)
        copy_tables(no_o14, drop=("O14_coverage",))
        electron = [f"{g} (electron-based: in {figures.paper_name('fig_fdp')[1]})" for g in figures.D.ELECTRON]
        not_searched = [f"{g} (no entrapment search)" for g in immuno]
        no_row = [f"{g} (no row in O11)" for g in immuno]
        changed_immuno = [f"{searched} (no row in O11)", not_searched[1],
                          f"{with_row} (immunopeptidomics: not drawn)", not_searched[3]]
        changed_electron = ["pxd011695_ETD (no row in O11)" if x.startswith("pxd011695_ETD ") else x
                            for x in electron]
        cases = (  # tables, Fig 2's left_out, FigS4's left_out
            (FX, electron + not_searched, not_searched),
            (no_o14, electron + no_row, no_row),
            (changed, ["velos (no row in O11)"] + changed_electron + changed_immuno,
             ["velos (no row in O11)", "pxd011695_ETD (no row in O11)"] + changed_immuno))
        with plt.rc_context(figures.rc_params()):
            for folder, main, full in cases:
                for func, want in ((figures.fig_fdp_main, main), (figures.fig_fdp, full)):
                    tabs = figures.Tables(folder)
                    fig, _ = func(plt, tabs)
                    try:
                        self.assertEqual(fig.facts["left_out"].split(", "), want, (folder, func.__name__))
                        self.assertEqual("O14_coverage" in tabs.used, folder != no_o14, (folder, func.__name__))
                    finally:
                        plt.close(fig)

    @needs_matplotlib
    def test_font_variable_adds_only_the_arial_files(self):
        """D18: $SUMMARIZE_FONT_DIR adds arial.ttf, arialbd.ttf, ariali.ttf and arialbi.ttf of one folder (any case)
        at run time and nothing else; nothing is installed. A wrong value is a WARN text, an unset one nothing."""
        from matplotlib import font_manager
        folder = os.path.join(self.tmp, "fonts")
        os.makedirs(folder)
        for fn in ("ARIAL.TTF", "arialbd.ttf", "Ariali.ttf", "times.ttf", "arial.ttf.bak", "arialn.ttf"):
            open(os.path.join(folder, fn), "wb").close()
        with mock.patch.dict(os.environ, {figures.FONT_DIR_ENV: folder}), \
                mock.patch.object(font_manager.fontManager, "addfont") as add:
            paths, problem = figures.add_fonts()
        self.assertIsNone(problem)
        self.assertEqual(sorted(os.path.basename(p) for p in paths), ["ARIAL.TTF", "Ariali.ttf", "arialbd.ttf"])
        self.assertEqual(sorted(os.path.basename(c.args[0]) for c in add.call_args_list),
                         ["ARIAL.TTF", "Ariali.ttf", "arialbd.ttf"])
        with mock.patch.dict(os.environ, {figures.FONT_DIR_ENV: ""}):
            self.assertEqual(figures.add_fonts(), ([], None))
        empty = os.path.join(self.tmp, "empty")
        os.makedirs(empty)
        with mock.patch.dict(os.environ, {figures.FONT_DIR_ENV: empty}), \
                mock.patch.object(font_manager.fontManager, "addfont") as add:
            paths, problem = figures.add_fonts()
        self.assertEqual((paths, add.call_count), ([], 0))
        self.assertIn("no arial.ttf", problem)
        # a value that names no folder: WARN FIGURES, also when no figure is drawn
        tables_dir, out = os.path.join(self.tmp, "tables"), os.path.join(self.tmp, "figures")
        os.makedirs(tables_dir)
        report = T.Report()
        with mock.patch.dict(os.environ, {figures.FONT_DIR_ENV: os.path.join(self.tmp, "none")}):
            figures.draw(tables_dir, out, report)
        warns = self.lines(report, "WARN")
        self.assertEqual(len(warns), 1)
        self.assertIn(f"{figures.FONT_DIR_ENV} is not a folder", warns[0][2])
        self.assertEqual(os.listdir(out), [])

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

    def test_words(self):
        """G3: no visible word of VOCAB, BLOCK_NAME, REASON_LABEL or CAL_LABEL is a code name; true minus (G10)."""
        words = []
        for value in list(figures.VOCAB.values()) + list(figures.BLOCK_NAME.values()) \
                + list(figures.REASON_LABEL.values()) + list(figures.CAL_LABEL.values()):
            words += list(value.values()) if isinstance(value, dict) else [value]
        for word in words:
            self.assertIsNone(figures.BANNED.search(word), word)
        for bad in ("per_file", "gmean of R3", "B3", "td accepted", "arm / main", "frac10", "realizations",
                    "colour", "speed-up", "engine node", "RSS", "$L_T$", "set s1"):
            self.assertIsNotNone(figures.BANNED.search(bad), bad)
        for good in ("ProSE, per-file rescoring (main)", "16 threads (main benchmark setting)", "set S1",
                     "Astral set S1", "peak memory (GiB)"):
            self.assertIsNone(figures.BANNED.search(good), good)
        self.assertEqual(figures.minus("-1.5"), "−1.5")
        self.assertEqual(figures.minus(f"{2.0:+.1f}"), "+2.0")

    def test_helpers(self):
        self.assertIsNone(figures.num("NA"))
        self.assertIsNone(figures.num("nan"))
        self.assertIsNone(figures.num("-"))
        self.assertEqual(figures.num("0"), 0.0)
        self.assertEqual(figures.first(None, 0.0, 1.0), 0.0)
        self.assertEqual(figures.reason_label("failed_memory stage all repetition 0 exit 137"), "out of memory")
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
        self.assertEqual(figures.unit_suffix("pxd065289_frac10", "pxd065289_etcid"), "fraction 10")  # G3: no frac10
        self.assertEqual(figures.paper_name("fig_fdp_main"), ("main", "Fig2", "Fig2_entrapment_fdp"))
        self.assertIsNone(figures.paper_name("fig_unknown"))
        self.assertEqual(set(figures.PAPER_FIGURES), set(figures.FIGURE_NAMES))
        self.assertEqual(set(figures.CAPTION_KEYS), set(figures.FIGURE_NAMES))
        for folder, stem in figures.PAPER_FIGURES.values():
            self.assertRegex(f"{stem}.pdf", figures.PAPER_COPY)
        main = sorted(stem for folder, stem in figures.PAPER_FIGURES.values() if folder == "main")
        self.assertEqual([s.split("_")[0] for s in main], ["Fig1", "Fig2", "Fig3", "Fig4"])


if __name__ == "__main__":
    unittest.main()
