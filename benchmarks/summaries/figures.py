"""Figures of the paper (SPEC v2 section 3.7), drawn from the written tables only.

This is the only module of the package that imports matplotlib, and it does so lazily inside draw(), with the Agg
backend (SPEC section 1, "matplotlib only in figures.py, imported lazily"). It reads only <out>/tables/*.tsv through
tables.read_table, never the raw inputs, so `summarize.py --figures-only` can run in WSL on a copied output folder.

Figure index (SPEC 3.7) and the tables each figure reads
  fig_overtuning_psm / _peptide  O5 / O7  O04_overtuning_<level>_datasets and _sides; run points from
                                          O04_overtuning_<level>_runs (OT's rows: engine side dataset run ratio
                                          dataset_value) when written, else the used runs of O02_pairs_runs (C6b checks
                                          that these equal OT's rows)
  fig_ids_counts_psm / _peptide  O3       O03_three_runs (R3 units)
  fig_electron                   O8       O08_electron_runs; FDP of the shared realisations from O11_fdp_runs (the own
                                          values of O08 only when O11_fdp_runs is absent, labelled)
  fig_immuno                     O9       O09_immuno_samples (level peptide, DS:625)
  fig_fdp                        O11+O12  O11_fdp_runs; arath from O12_fdp_arath where O11_fdp_runs has none
  fig_matched_fdp                O13      O13_matched_fdp (pair level role design ratio_q01 ratio_matched)
  fig_time_per_file              O15      O15_time_runs
  fig_batch                      O16      O16_batch
  fig_scaling                    O17      O17_scaling
  fig_low_memory                 O10      O10_low_memory
  fig_calibration                O19      O19_calibration_counts
  fig_ext_percolator             O20      O20_external_percolator (runs) and _datasets (bars), "as O5"
  fig_prediction                 O21      O21_prediction (runs) and _datasets (bars), the same layout

Common rules (SPEC 3 "Figures", "Grade everywhere")
- Width 7.0 in (double column), every text 7 pt; PDF with pdf.fonttype 42 (TrueType embedded) and PNG at 300 dpi.
- Engine colours fixed: Okabe-Ito, design.COLOUR (ProSE #0072B2, Sage #009E73, MSFragger #D55E00).
- A missing value is never drawn as 0 or as an extreme value. It is drawn as an x at the axis base with a short label
  taken from the row's status/state/note ("failed (memory)", "not run by design"); neighbouring marks with the same
  label share one label. Exceptions given by the outputs: O5 labels a dropped dataset "n/a" (SPEC O5); O15 draws a
  failed_memory search as an x on the 200 GiB cap line of the RSS panel and labels it below the time axis (SPEC O15).
- Every held-out category label carries its grade letter: a row of grade letters directly under the axis (SPEC O5:
  "the grade letter under each held-out label"); tuning datasets have none (grade '-').
- Decision runs: grey open markers in per-run figures (OPEN Q9), hatched bars where the output says so (O8, O9), and
  not shown in O5 (DS:858).
- FDP columns are fractions (combined_fdp of counts.tsv, EE-lib:30-34; O12's difference_pp = 100 x (arath - shuffled
  mean)); the figures show them in percent with a dashed 1% line.

Skips and failures
- A figure whose table is absent or has no data row is skipped with an INFO line; a file of that figure left by an
  earlier build is removed, so no stale figure stays next to fresh ones (the package's own output names, as
  summarize.py does for stale tables).
- A figure that raises gives 'FAIL FIGURES <figure>: <exception>'; the other figures are still drawn, and draw()
  raises FigureError at the end, chained to the first exception, so that summarize.py writes its traceback to
  errors.txt (module contract).
"""
import math
import os
import re

from . import design as D
from . import tables as T

WIDTH = 7.0  # in; double column (SPEC 3 "Figures")
FONT_PT = 7
DPI = 300
FONTS = ("Arial", "Helvetica", "Arimo", "Liberation Sans", "Nimbus Sans", "DejaVu Sans")  # first one installed
GREY = "0.55"  # decision runs (OPEN Q9)
MISSING_COLOUR = "0.25"
HATCH = "//////"
ROLES = ("tuned", "heldout", "decision")
NA_TEXT = ("", "NA", "nan", "NaN", "None", "-")
LEVEL_NAME = {"psm": "PSM", "peptide": "peptide"}
LEVEL_UNIT = {"psm": "PSMs", "peptide": "peptides"}
BLOCK_NAME = {"IT": "IT", "OT": "OT", "Astral": "Astral", "timsTOF": "timsTOF", "electron": "electron-based",
              "immuno": "immunopeptidomics", "other": "other"}
# short labels of the missing-value reasons (SPEC 2.6), found as words of a status, state or note cell
REASON_LABEL = {
    "failed_memory": "failed (memory)", "failed": "failed", "not_run_by_design": "not run by design",
    "not_run": "not run", "running": "running", "interrupted": "interrupted", "unknown": "unknown",
    "over_limit": "over limit", "not_run_over_limit": "not run (over limit)", "incomplete": "incomplete",
    "no_timing": "no timing", "no_timing_rows": "no timing", "stale_timing": "stale timing", "zero": "zero count",
    "none_accepted": "none accepted", "not_counted": "not counted", "empty": "n/a", "outside_design": "outside design",
    "no_coverage": "no coverage", "missing_count": "no count",
}
CAL_SLOTS = (("prose", "main"), ("prose", "cal_off"), ("sage", "main"), ("msfragger", "main"),
             ("msfragger", "cal1"), ("msfragger", "cal0"))  # O19 arms (SPEC 2.2 ARMS; RM:163-165)
CAL_MARKER = {"main": "o", "cal_off": "v", "cal1": "s", "cal0": "D"}
CAL_LABEL = {"main": "main", "cal_off": "calibration off", "cal1": "calibrate_mass 1", "cal0": "calibrate_mass 0"}


class Skip(Exception):
    """The figure is not drawn: its table is absent or holds nothing for it (INFO)."""


class FigureError(Exception):
    """One or more figures raised; draw() raises this at the end, chained to the first error."""


# ---------------------------------------------------------------- entry point
def draw(tables_dir, figures_dir, report):
    """Draws every figure of SPEC 3.7 from tables_dir into figures_dir as fig_<name>.pdf and .png; one INFO line per
    figure drawn or skipped, one FAIL line per figure that raised (then FigureError at the end)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    os.makedirs(figures_dir, exist_ok=True)
    tabs = Tables(tables_dir)
    failed = []
    with plt.rc_context(rc_params()):
        for name, func, args in FIGURES:
            try:
                fig, info = func(plt, tabs, *args)
            except Skip as why:
                plt.close("all")
                removed = remove_stale(figures_dir, name)
                report.check("INFO", "FIGURES", f"{name} skipped: {why}" + (f"; stale {removed} removed" if removed
                                                                               else ""))
                continue
            except Exception as err:  # one broken figure must not stop the others (module contract)
                plt.close("all")
                report.check("FAIL", "FIGURES", f"{name}: {err.__class__.__name__}: {err}")
                failed.append((name, err))
                continue
            try:
                save(fig, figures_dir, name)
            except Exception as err:  # e.g. a full disk: reported like a drawing error
                report.check("FAIL", "FIGURES", f"{name}: not saved: {err.__class__.__name__}: {err}")
                failed.append((name, err))
                continue
            finally:
                plt.close(fig)
            report.check("INFO", "FIGURES", f"{name}: drawn ({info})")
    if failed:
        raise FigureError(f"{len(failed)} figure(s) failed: {', '.join(n for n, _ in failed)}") from failed[0][1]


def rc_params():
    """7 pt everywhere, TrueType fonts in the PDF (pdf.fonttype 42), 300 dpi PNG (SPEC 1 "Output folder", 3)."""
    return {
        "pdf.fonttype": 42, "ps.fonttype": 42, "savefig.dpi": DPI, "figure.dpi": 100,
        "font.family": "sans-serif", "font.sans-serif": [font_name()], "mathtext.default": "regular",
        "font.size": FONT_PT, "axes.titlesize": FONT_PT, "axes.labelsize": FONT_PT, "xtick.labelsize": FONT_PT,
        "ytick.labelsize": FONT_PT, "legend.fontsize": FONT_PT, "figure.titlesize": FONT_PT,
        "legend.title_fontsize": FONT_PT, "axes.linewidth": 0.6, "xtick.major.width": 0.6, "ytick.major.width": 0.6,
        "xtick.minor.width": 0.4, "ytick.minor.width": 0.4, "xtick.major.size": 2.5, "ytick.major.size": 2.5,
        "xtick.minor.size": 1.5, "ytick.minor.size": 1.5, "lines.linewidth": 0.8, "lines.markersize": 3,
        "hatch.linewidth": 0.5, "patch.linewidth": 0.6, "legend.frameon": False, "legend.handlelength": 1.6,
        "legend.columnspacing": 1.2, "legend.borderaxespad": 0.2, "axes.spines.top": False,
        "axes.spines.right": False, "axes.titlelocation": "left", "axes.unicode_minus": True,
        "errorbar.capsize": 0,
    }


def font_name():
    """The first installed font of FONTS (Arial where present; Arimo has its metrics), so matplotlib never warns."""
    from matplotlib import font_manager
    names = {f.name for f in font_manager.fontManager.ttflist}
    for name in FONTS:
        if name in names:
            return name
    return "DejaVu Sans"


def save(fig, figures_dir, name):
    """fig_<name>.pdf and .png, each written to a temporary file and moved into place (atomic, as the tables). The
    y labels of panels stacked in one column are aligned first."""
    fig.align_ylabels()
    for ext in ("pdf", "png"):
        path = os.path.join(figures_dir, f"{name}.{ext}")
        tmp = path + ".tmp"
        meta = {"CreationDate": None} if ext == "pdf" else {"Software": None}
        fig.savefig(tmp, format=ext, dpi=DPI, metadata=meta)
        os.replace(tmp, path)


def remove_stale(figures_dir, name):
    """Removes fig_<name>.pdf/.png of an earlier build when this build skips the figure; returns what it removed."""
    removed = []
    for ext in ("pdf", "png"):
        path = os.path.join(figures_dir, f"{name}.{ext}")
        if os.path.exists(path):
            os.remove(path)
            removed.append(os.path.basename(path))
    return ", ".join(removed)


# ---------------------------------------------------------------- reading the written tables
class Tables:
    """The written tables/*.tsv, each read once with tables.read_table ('#' note lines skipped)."""

    def __init__(self, folder):
        self.folder = folder
        self.cache = {}

    def read(self, name):
        """(columns, rows) of tables/<name>.tsv, or None when the file is absent."""
        if name not in self.cache:
            path = os.path.join(self.folder, name + ".tsv")
            self.cache[name] = T.read_table(path) if os.path.exists(path) else None
        return self.cache[name]

    def columns(self, name):
        got = self.read(name)
        return got[0] if got else []

    def need(self, name, columns):
        """The rows of a table the figure is drawn from: Skip when absent or empty; ValueError when a column the
        figure needs is not in the header (a contract mismatch, reported as FAIL)."""
        got = self.read(name)
        if got is None:
            raise Skip(f"table {name} absent")
        cols, rows = got
        if not rows:
            raise Skip(f"table {name} empty")
        lacking = [c for c in columns if c not in cols]
        if lacking:
            raise ValueError(f"table {name} lacks the columns {', '.join(lacking)} (SPEC 3)")
        return rows

    def optional(self, name, columns):
        """The rows of a table that adds to a figure; [] when absent or empty; ValueError on a lacking column."""
        got = self.read(name)
        if got is None or not got[1]:
            return []
        lacking = [c for c in columns if c not in got[0]]
        if lacking:
            raise ValueError(f"table {name} lacks the columns {', '.join(lacking)} (SPEC 3)")
        return got[1]


def num(text):
    """A number cell -> float; None for NA (and nan, inf, '-', empty). Missing values stay None: never 0."""
    if text is None:
        return None
    s = text.strip()
    if s in NA_TEXT:
        return None
    try:
        v = float(s)
    except ValueError:
        return None
    if math.isnan(v) or math.isinf(v):
        return None
    return v


def first(*values):
    """The first value that is not None (a 0.0 is a value: FDP 0 with no entrapment hit, so no 'or' here)."""
    for v in values:
        if v is not None:
            return v
    return None


def yes(text):
    return (text or "").strip().lower() in ("yes", "true", "1")


def state_word(text):
    """The first word of a status/state cell ('failed_memory stage all ...' -> 'failed_memory')."""
    words = (text or "").split()
    return words[0] if words else ""


def reason_label(*texts, engine=None):
    """The short label of a missing value: a known reason word (SPEC 2.6) in the given status, state or note cells
    ('failed_memory stage all repetition 0 exit 137' -> 'failed (memory)', 'sage:zero' -> 'zero count'). With engine,
    a reason prefixed by that engine ('<engine>:<reason>') comes first and one prefixed by another engine is skipped;
    otherwise the first unprefixed reason; 'n/a' when none is found."""
    generic = None
    for text in texts:
        for m in re.finditer(r"(?:([A-Za-z]+):)?([a-z_]+)", text or ""):
            who, word = m.group(1), m.group(2)
            if word not in REASON_LABEL:
                continue
            if who and engine:
                if who.lower() == engine:
                    return REASON_LABEL[word]
                continue
            if generic is None:
                generic = REASON_LABEL[word]
    return generic or "n/a"


# the sides of an O21 comparison name (calib.PRED_COMPARISONS): '<numerator>_vs_<denominator>'; 'main' is the main
# arm of the other side's engine
PRED_SIDES = {"peptdeep": ("ProSE+PeptDeep", "prose"), "msbooster": ("MSFragger+MSBooster", "msfragger"),
              "prose": ("ProSE", "prose"), "sage": ("Sage", "sage"), "msfragger": ("MSFragger", "msfragger")}


def comparison_sides(text):
    """'peptdeep_vs_main' -> (('ProSE+PeptDeep', 'prose'), ('ProSE', 'prose')); None for any other text."""
    if "_vs_" not in (text or ""):
        return None
    a, b = text.lower().split("_vs_", 1)
    num_side = PRED_SIDES.get(a, (a, None))
    if b == "main":
        engine = num_side[1]
        den_side = (D.ENGINE_NAME.get(engine, b), engine)
    else:
        den_side = PRED_SIDES.get(b, (b, None))
    return num_side, den_side


def comparator_of(text):
    """The engine whose colour a pair or comparison takes, the comparator (denominator): 'prose/msfragger',
    'prose_msfragger', 'MSFragger' -> 'msfragger'; ... 'sage'; 'peptdeep_vs_main' -> 'prose',
    'peptdeep_vs_msbooster' -> 'msfragger'; 'prose' when it names ProSE only; None otherwise."""
    sides = comparison_sides(text)
    if sides:
        return sides[1][1]
    s = (text or "").lower()
    if "fragger" in s:
        return "msfragger"
    if "sage" in s:
        return "sage"
    if "prose" in s:
        return "prose"
    return None


def pair_title(text):
    """A pair or comparison cell for a panel title: 'prose/msfragger' or 'prose_msfragger' -> 'ProSE / MSFragger';
    'peptdeep_vs_msbooster' -> 'ProSE+PeptDeep / MSFragger+MSBooster'."""
    sides = comparison_sides(text)
    if sides:
        return f"{sides[0][0]} / {sides[1][0]}"
    names = {"prose": "ProSE", "sage": "Sage", "msfragger": "MSFragger", "peptdeep": "PeptDeep",
             "msbooster": "MSBooster"}

    def side(s):
        return "+".join(names.get(w.lower(), w) for w in s.split("_") if w)
    if "/" in text:
        return " / ".join(side(s) for s in text.split("/"))
    return " / ".join(names.get(w.lower(), w) for w in text.split("_") if w)


def ordered_groups(groups):
    """Design order (design.order_key): the 17 tryptic datasets in class blocks, then electron, immuno, others."""
    return sorted(set(groups), key=D.order_key)


def block_of(group):
    """The x block of a group: its class for the tryptic datasets, else its kind (SPEC 2.2 "Figure order")."""
    k = D.kind(group)
    if k in ("tuning", "heldout"):
        return D.cls(group)
    return k if k in ("electron", "immuno") else "other"


def spread(n, half):
    """Deterministic offsets of n points within +-half (SPEC O5: "deterministic jitter +-0.15")."""
    if n <= 1:
        return [0.0] * n
    return [-half + 2 * half * i / (n - 1) for i in range(n)]


def dodge(keys, width):
    """{key: x offset} for engines (or engine-arm slots) side by side within one category."""
    k = len(keys)
    return {e: (i - (k - 1) / 2) * width for i, e in enumerate(keys)}


def engines_in(rows, column="engine"):
    present = {r.get(column) for r in rows}
    return [e for e in D.ENGINES if e in present]


def unit_suffix(unit, group):
    """The part of a unit name that tells it apart within its group ('pxd065289_frac1' in pxd065289_etcid ->
    'frac1'); long run ids are shortened for a tick label."""
    prefix = os.path.commonprefix([unit, group])
    prefix = prefix[:prefix.rfind("_") + 1] if "_" in prefix else ""
    s = unit[len(prefix):] or unit
    return s if len(s) <= 16 else s[:7] + "…" + s[-7:]


def donor_of(sample, donor_tissue=""):
    """'pxd058436_DN05_Thyroid_classI' -> ('DN05', 'Thyroid') (x of fig_immuno and fig_low_memory, SPEC O9)."""
    for text in (donor_tissue, sample):
        m = re.search(r"(DN\d+)(?:[_ -]([A-Za-z]+))?", text or "")
        if m:
            tissue = m.group(2) or ""
            return m.group(1), ("" if tissue.lower().startswith("class") else tissue)
    return sample, ""


def donor_number(sample):
    m = re.search(r"DN(\d+)", sample or "")
    return int(m.group(1)) if m else 10 ** 6


# ---------------------------------------------------------------- drawing helpers
def new_figure(plt, height, nrows=1, ncols=1, categorical=True, **kw):
    """A 7.0 in wide figure with constrained layout (labels, legends and annotations stay inside the page); on a
    categorical x axis no tick marks (also on the upper panels of a shared axis)."""
    fig = plt.figure(figsize=(WIDTH, height), layout="constrained")
    axs = fig.subplots(nrows, ncols, squeeze=False, **kw)
    if categorical:
        for row in axs:
            for a in row:
                a.tick_params(axis="x", length=0)
    return fig, axs


def log_ticks(ax, axis="y"):
    """A log10 axis with plain numbers: ticks at 1, 2, 5 x 10^k over up to three decades, else at 10^k."""
    from matplotlib import ticker
    lo, hi = ax.get_ylim() if axis == "y" else ax.get_xlim()
    decades = math.log10(hi / lo) if lo > 0 and hi > lo else 1.0
    target = ax.yaxis if axis == "y" else ax.xaxis
    target.set_major_locator(ticker.LogLocator(base=10, subs=(1.0, 2.0, 5.0) if decades <= 3 else (1.0,)))
    target.set_minor_locator(ticker.LogLocator(base=10, subs=tuple(float(s) for s in range(2, 10))))
    target.set_major_formatter(ticker.FuncFormatter(lambda v, _: f"{v:,g}"))
    target.set_minor_formatter(ticker.NullFormatter())


def category_axis(ax, positions, labels, groups=None, rotation=40):
    """Category ticks with rotated labels and, for held-out groups, the grade letter directly under the axis (SPEC 3
    "Grade everywhere"; O5 "the grade letter under each held-out label")."""
    positions = list(positions)
    ax.set_xticks(positions)
    ax.set_xticklabels(labels, rotation=rotation, ha="right" if rotation else "center", rotation_mode="anchor")
    ax.tick_params(axis="x", length=0, pad=10 if groups else 3)
    for x, g in zip(positions, groups or ()):
        grade = D.grade(g)
        if grade in ("A", "B", "C"):
            ax.annotate(grade, xy=(x, 0), xycoords=("data", "axes fraction"), xytext=(0, -2),
                        textcoords="offset points", ha="center", va="top")


def dataset_axis(ax, groups, positions=None):
    positions = list(range(len(groups))) if positions is None else positions
    category_axis(ax, positions, [D.display(g) for g in groups], groups)
    ax.set_xlim(min(positions) - 0.6, max(positions) + 0.6)


def draw_blocks(ax, groups, positions=None, label=True):
    """Thin separators between the class blocks (IT, OT, Astral, timsTOF, then electron, immuno) and, on the top panel,
    the block names above the axes (SPEC O5: "class names above the blocks"). True when names were drawn."""
    positions = list(range(len(groups))) if positions is None else positions
    spans = []
    for g, x in zip(groups, positions):
        b = block_of(g)
        if spans and spans[-1][0] == b:
            spans[-1][2] = x
        else:
            spans.append([b, x, x])
    for i in range(1, len(spans)):
        ax.axvline((spans[i - 1][2] + spans[i][1]) / 2, color="0.82", lw=0.5, zorder=0)
    if label:
        for b, x0, x1 in spans:
            ax.annotate(BLOCK_NAME.get(b, b), xy=((x0 + x1) / 2, 1), xycoords=("data", "axes fraction"),
                        xytext=(0, 2), textcoords="offset points", ha="center", va="bottom", color="0.3")
    return label and bool(spans)


def title(ax, text, above_blocks=False):
    ax.set_title(text, loc="left", pad=12 if above_blocks else 4)


def legend_top(fig, handles, ncol):
    if handles:
        fig.legend(handles=handles, loc="outside upper center", ncol=ncol)


class Marks:
    """The missing values of one axes: an x per value at the axis base and one short label per run of neighbouring
    marks with the same label (SPEC 3 "Figures": a missing value is never drawn as 0 or as an extreme value)."""

    def __init__(self, ax):
        self.ax = ax
        self.items = []

    def add(self, x, label, colour=MISSING_COLOUR):
        self.items.append((x, label, colour))

    def draw(self, mode="above", gap=1.7):
        """mode 'above': one horizontal label per cluster just above the base; 'below': under the axis, outside the
        data range (SPEC O15); 'slot': one vertical label per mark, in the empty bar slot above it."""
        if not self.items:
            return
        from matplotlib.transforms import blended_transform_factory
        ax = self.ax
        trans = blended_transform_factory(ax.transData, ax.transAxes)
        for x, _, colour in self.items:
            ax.plot([x], [0.0], ls="none", marker="x", ms=4, mew=0.9, color=colour, transform=trans, clip_on=False,
                    zorder=6)
        if mode == "slot":
            for x, label, _ in self.items:
                if label:
                    ax.annotate(label, xy=(x, 0), xycoords=("data", "axes fraction"), xytext=(0, 5),
                                textcoords="offset points", rotation=90, ha="center", va="bottom", color="0.25",
                                zorder=7)
            return
        below = mode == "below"
        clusters = []  # [label, x0, x1]
        for label in sorted({lab for _, lab, _ in self.items if lab}):
            for x in sorted(x for x, lab, _ in self.items if lab == label):
                if clusters and clusters[-1][0] == label and x - clusters[-1][2] <= gap:
                    clusters[-1][2] = x
                else:
                    clusters.append([label, x, x])
        clusters.sort(key=lambda c: c[1])
        rows = []
        for i, (label, x0, x1) in enumerate(clusters):
            # a cluster close to the previous one goes one line further from the axis, so labels do not overlap
            near = i > 0 and x0 - clusters[i - 1][2] <= gap * 1.5
            rows.append((rows[-1] + 1) % 3 if near else 0)
            dy = -(5 + 8 * rows[-1]) if below else 4 + 8 * rows[-1]
            ax.annotate(label, xy=((x0 + x1) / 2, 0), xycoords=("data", "axes fraction"), xytext=(0, dy),
                        textcoords="offset points", ha="center", va="top" if below else "bottom", color="0.25",
                        bbox=None if below else dict(boxstyle="square,pad=0.1", fc="white", ec="none", alpha=0.75),
                        zorder=7)


def cap_line(ax, label=True):
    """The 200 GiB memory cap (DS:653, 1009) as a dashed line, labelled at the left end."""
    ax.axhline(D.CAP_GIB, color="0.35", ls="--", lw=0.7, zorder=1)
    if label:
        from matplotlib.transforms import blended_transform_factory
        ax.annotate(f"{D.CAP_GIB} GiB cap", xy=(0.005, D.CAP_GIB),
                    xycoords=blended_transform_factory(ax.transAxes, ax.transData), xytext=(0, 2),
                    textcoords="offset points", ha="left", va="bottom", color="0.35")  # clear of the dashes


def one_percent_line(ax):
    ax.axhline(1.0, color="0.35", ls="--", lw=0.7, zorder=1)


LOG2_TICKS = (1 / 64, 1 / 32, 1 / 16, 0.125, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0, 8.0, 16.0, 32.0, 64.0)


def log2_ticks(ax, values):
    """Limits and ticks of a log2 ratio axis around 1: plain numbers (0.5, 0.75, 1, 1.5, 2, ...), thinned on a wide
    range."""
    from matplotlib import ticker
    vals = [v for v in values if v is not None and v > 0] + [1.0]
    lo, hi = min(vals) / 1.25, max(vals) * 1.25
    ticks = [t for t in LOG2_TICKS if lo <= t <= hi]
    if len(ticks) > 9:
        ticks = [t for t in ticks if math.log2(t) == int(math.log2(t))]
    ax.yaxis.set_major_locator(ticker.FixedLocator(ticks))
    ax.yaxis.set_minor_locator(ticker.NullLocator())
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda v, _: f"{v:g}"))
    ax.set_ylim(lo, hi)


def engine_handles(engines, marker="o", line=False):
    from matplotlib.lines import Line2D
    return [Line2D([], [], color=D.COLOUR[e], marker=marker, ls="-" if line else "none", ms=4,
                   label=D.ENGINE_NAME[e]) for e in engines]


def marker_handle(label, marker="o", colour="0.2", face=None, ms=4, ls="none", mew=0.8):
    from matplotlib.lines import Line2D
    return Line2D([], [], color=colour, marker=marker, ls=ls, ms=ms, mfc=colour if face is None else face,
                  mec=colour, mew=mew, label=label)


def patch_handle(label, face, edge=None, hatch=None, alpha=None):
    from matplotlib.patches import Patch
    return Patch(facecolor=face, edgecolor=edge or face, hatch=hatch, lw=0.6, alpha=alpha, label=label)


def text_handle(label):
    from matplotlib.patches import Patch
    return Patch(facecolor="none", edgecolor="none", label=label)


# ---------------------------------------------------------------- O5 / O7, O20, O21: leads per dataset
def lead_panel(ax, groups, bars, points, colour, na_label="n/a"):
    """SPEC O5 layout: bar = dataset lead in % (tuning filled in the comparator colour, held-out white with hatch);
    points = run leads with deterministic jitter +-0.15; a dataset without a value is labelled n/a; zero line."""
    for x, g in enumerate(groups):
        v = bars.get(g)
        tuning = D.kind(g) == "tuning"
        if v is None:
            ax.annotate(na_label, xy=(x, 0), xytext=(0, 2), textcoords="offset points", ha="center", va="bottom",
                        color="0.25")
        else:
            ax.bar(x, v, width=0.7, color=colour if tuning else "white", edgecolor=colour,
                   hatch=None if tuning else HATCH, lw=0.6, zorder=2)
        pts = points.get(g, [])
        if pts:
            offs = spread(len(pts), 0.15)
            ax.plot([x + o for o in offs], pts, ls="none", marker="o", ms=2.4, mfc="0.1", mec="white", mew=0.3,
                    zorder=3)
    ax.axhline(0, color="black", lw=0.6, zorder=2.5)
    ax.set_xlim(-0.6, len(groups) - 0.4)


def side_lines(ax, lt, lh):
    """L_T as a solid and L_H as a dashed line across the panel, each labelled right of the panel (SPEC O5): the label
    of the upper line above it, of the lower line below it, so the two never overlap."""
    from matplotlib.transforms import blended_transform_factory
    trans = blended_transform_factory(ax.transAxes, ax.transData)
    lines = [(v, name, ls) for v, name, ls in ((lt, "$L_T$", "-"), (lh, "$L_H$", (0, (4, 2)))) if v is not None]
    top = max(v for v, _, _ in lines) if lines else None
    for v, name, ls in lines:
        ax.axhline(v, color="0.15", ls=ls, lw=0.8, zorder=4)
        upper = v == top and (len(lines) == 1 or lines[0][0] != lines[1][0] or name == "$L_T$")
        ax.annotate(f"{name} {v:+.1f}%", xy=(1.0, v), xycoords=trans, xytext=(2, 1 if upper else -1),
                    textcoords="offset points", ha="left", va="bottom" if upper else "top", annotation_clip=False)


def lead_handles(with_sides):
    hs = [patch_handle("tuning dataset (filled)", "0.55"),
          patch_handle("held-out dataset (hatched)", "white", "0.4", HATCH),
          marker_handle("run", "o", "0.1", ms=3)]
    if with_sides:
        from matplotlib.lines import Line2D
        hs += [Line2D([], [], color="0.15", ls="-", lw=0.8, label="$L_T$ tuning lead"),
               Line2D([], [], color="0.15", ls=(0, (4, 2)), lw=0.8, label="$L_H$ held-out lead")]
    return hs


def overtuning_points(tabs, level):
    """{comparator: {dataset: [run leads in %]}}: OT's rows if a table of them is written, else the used runs of
    O02_pairs_runs (decision runs are not shown, DS:858; C6b checks these ratios equal OT's strings)."""
    out = {}
    rows = tabs.optional(f"O04_overtuning_{level}_runs", ("engine", "dataset", "ratio"))
    if rows:
        for r in rows:
            comp, v = comparator_of(r["engine"]), num(r["ratio"])
            if comp and v is not None:
                out.setdefault(comp, {}).setdefault(r["dataset"], []).append(100 * (v - 1))
        return out, f"O04_overtuning_{level}_runs"
    rows = tabs.optional("O02_pairs_runs", ("pair", "level", "group", "role", "ratio", "used"))
    if rows:
        for r in rows:
            v = num(r["ratio"])
            if (r["level"] == level and yes(r["used"]) and r["role"] != "decision" and v is not None
                    and D.kind(r["group"]) in ("tuning", "heldout")):
                out.setdefault(comparator_of(r["pair"]), {}).setdefault(r["group"], []).append(100 * (v - 1))
        return out, "O02_pairs_runs"
    return out, "no run table"


def fig_overtuning(plt, tabs, level):
    """O5 (psm) / O7 (peptide), SPEC 3.5: two stacked panels, MSFragger then Sage, over the 17 datasets in design order;
    bar = dataset lead, points = run leads, L_T solid and L_H dashed; 7.0 x 4.5 in."""
    name = f"O04_overtuning_{level}_datasets"
    ds_rows = tabs.need(name, ("dataset", "side", "value_msfragger", "lead_msfragger", "value_sage", "lead_sage"))
    sides = {}
    for r in tabs.optional(f"O04_overtuning_{level}_sides", ("comparator", "L_T", "L_H")):
        sides[comparator_of(r["comparator"])] = (num(r["L_T"]), num(r["L_H"]))
    points, source = overtuning_points(tabs, level)
    groups = ordered_groups(r["dataset"] for r in ds_rows)
    fig, axs = new_figure(plt, 4.5, 2, 1, sharex=True)
    for i, comp in enumerate(("msfragger", "sage")):
        ax = axs[i][0]
        bars = {}
        for r in ds_rows:
            value = num(r[f"value_{comp}"])
            bars[r["dataset"]] = first(num(r[f"lead_{comp}"]), None if value is None else 100 * (value - 1))
        lead_panel(ax, groups, bars, points.get(comp, {}), D.COLOUR[comp])
        lt, lh = sides.get(comp, (None, None))
        side_lines(ax, lt, lh)
        ax.set_ylabel(f"lead over {D.ENGINE_NAME[comp]} (%)")
        blocks = draw_blocks(ax, groups, label=(i == 0))
        title(ax, f"({'ab'[i]}) ProSE vs {D.ENGINE_NAME[comp]}, {LEVEL_NAME[level]} level", above_blocks=blocks)
    dataset_axis(axs[1][0], groups)
    legend_top(fig, lead_handles(True), 5)
    return fig, f"2 panels, {len(groups)} x categories, run points from {source}"


def fig_pair_leads(plt, tabs, table, what):
    """O20 / O21 "as O5" (SPEC 3.4): one panel per pair (O20, column pair) or comparison (O21, column comparison) over
    the datasets in design order, PSM level (as O5), without the side lines. Points: the used, non-decision run
    ratios of <table>; bars: lead_pct (or gmean) of <table>_datasets (calib.py). Without that table, rows of <table>
    without a unit (unit NA or '-') are read as dataset rows, and failing those the bar is the gmean of the used run
    ratios (display only, said in the INFO line)."""
    rows = tabs.need(table, ("level", "group"))
    cols = tabs.columns(table)
    key = next((c for c in ("pair", "comparison") if c in cols), None)
    if key is None:
        raise ValueError(f"{table} has neither a pair nor a comparison column")
    level = "psm" if any(r["level"] == "psm" for r in rows) else rows[0]["level"]
    rows = [r for r in rows if r["level"] == level]
    pairs, runs, bars = [], {}, {}
    ds_rows = [r for r in tabs.optional(f"{table}_datasets", (key, "level", "group")) if r["level"] == level]
    separate = bool(ds_rows)
    for r in rows:
        if r[key] not in pairs:
            pairs.append(r[key])
        unit = r.get("unit", "-") if "unit" in cols else "-"
        if unit.strip() not in NA_TEXT:
            v = num(r.get("ratio"))
            if v is not None and v > 0 and r.get("role") != "decision" and ("used" not in cols or yes(r["used"])):
                runs.setdefault(r[key], {}).setdefault(r["group"], []).append(v)
        elif not separate:
            ds_rows.append(r)
    for r in ds_rows:
        g = num(r.get("gmean"))
        bars.setdefault(r[key], {})[r["group"]] = first(num(r.get("lead_pct")), None if g is None else 100 * (g - 1))
    computed = []
    for pair in pairs:
        if pair not in bars:
            computed.append(pair)
            bars[pair] = {g: 100 * (math.exp(math.fsum(math.log(v) for v in vs) / len(vs)) - 1)
                          for g, vs in runs.get(pair, {}).items()}
    groups = ordered_groups(r["group"] for r in rows)
    fig, axs = new_figure(plt, 0.9 + 2.0 * len(pairs), len(pairs), 1, sharex=True)
    for i, pair in enumerate(pairs):
        ax = axs[i][0]
        comp = comparator_of(pair) or "prose"
        points = {g: [100 * (v - 1) for v in vs] for g, vs in runs.get(pair, {}).items()}
        lead_panel(ax, groups, bars[pair], points, D.COLOUR[comp])
        ax.set_ylabel("lead (%)")
        blocks = draw_blocks(ax, groups, label=(i == 0))
        title(ax, f"({chr(97 + i)}) {what}: {pair_title(pair)}, {LEVEL_NAME.get(level, level)} level",
              above_blocks=blocks)
    dataset_axis(axs[-1][0], groups)
    legend_top(fig, lead_handles(False), 3)
    source = f"bars from {table}_datasets" if not computed else f"bars from run rows for {', '.join(computed)}"
    return fig, f"{len(pairs)} panels, {len(groups)} x categories; {source}"


# ---------------------------------------------------------------- O3: counts of the three engines
def fig_ids_counts(plt, tabs, level):
    """O3 figure (SPEC 3.1; OPEN Q6, Q54): per dataset the geometric mean of the accepted counts over its R3 units
    (log scale), grouped bars per engine, the R3 units as dots; tryptic datasets (left) and immunopeptidomics class I
    (right). gmean(P)/gmean(C) = gmean(P/C) over the same units."""
    rows = tabs.need("O03_three_runs", ("group", "unit", "level") + D.ENGINES)
    rows = [r for r in rows if r["level"] == level]
    if not rows:
        raise Skip(f"O03_three_runs has no {level} row")
    units = {}
    for r in rows:
        vals = [num(r[e]) for e in D.ENGINES]
        if all(v is not None and v > 0 for v in vals):  # R3: all three counted with accepted > 0
            units.setdefault(r["group"], []).append(vals)
    present = {r["group"] for r in rows}
    paper = any(D.kind(g) in ("tuning", "heldout", "immuno") for g in present)
    left = list(D.FIGURE_ORDER) if paper else []
    left += ordered_groups(g for g in present if D.kind(g) == "other")
    right = [g for g in D.IMMUNO_ORDER if g.endswith("classI") or g in present] if paper else []
    panels = [(left, "tryptic datasets")] + ([(right, "immuno")] if right else [])
    fig, axs = new_figure(plt, 3.3, 1, len(panels),
                          gridspec_kw={"width_ratios": [max(len(p[0]), 1) + 1.5 for p in panels]})
    axs = axs[0]
    off = dodge(D.ENGINES, 0.27)
    every = [v for vals in units.values() for row in vals for v in row]
    for i, (groups, label) in enumerate(panels):
        ax = axs[i]
        marks = Marks(ax)
        for x, g in enumerate(groups):
            vals = units.get(g)
            if not vals:
                marks.add(x, "no R3 run")
                continue
            for j, e in enumerate(D.ENGINES):
                col = [v[j] for v in vals]
                gm = math.exp(math.fsum(math.log(v) for v in col) / len(col))
                ax.bar(x + off[e], gm, width=0.26, color=D.COLOUR[e], lw=0, zorder=2)
                ax.plot([x + off[e] + o for o in spread(len(col), 0.07)], col, ls="none", marker="o", ms=1.8,
                        mfc="0.1", mec="none", zorder=3)
        ax.set_yscale("log")
        if every:  # bars start at the power of ten below the smallest count
            ax.set_ylim(10 ** math.floor(math.log10(min(every))), max(every) * 1.5)
        log_ticks(ax)
        marks.draw()
        draw_blocks(ax, groups, label=(i == 0))
        dataset_axis(ax, groups)
        title(ax, f"({'ab'[i]}) {label}", above_blocks=True)  # both titles on one line
        if i == 0:
            ax.set_ylabel(f"{LEVEL_UNIT[level]} at 1% FDR")
    legend_top(fig, [patch_handle(f"{D.ENGINE_NAME[e]}: gmean over the R3 runs", D.COLOUR[e]) for e in D.ENGINES]
               + [marker_handle("run of R3", "o", "0.1", ms=2.5)], 4)
    return fig, f"{len(panels)} panels, {sum(len(p[0]) for p in panels)} x categories"


# ---------------------------------------------------------------- O8: electron-based datasets
def fdp_index(rows):
    """{(engine, unit, level): {'role', 'group', 'shuffled': (mean_shared, sd_shared), 'own', 'natural', 'arath',
    'notes'}} from O11_fdp_runs (one row per engine, unit, level and design)."""
    out = {}
    for r in rows:
        rec = out.setdefault((r["engine"], r["unit"], r["level"]),
                             {"role": r.get("role", ""), "group": r.get("group", ""), "shuffled": (None, None),
                              "own": None, "natural": None, "arath": None, "notes": []})
        design = r.get("design", "")
        if design == "shuffled":
            rec["shuffled"] = (num(r.get("mean_shared")), num(r.get("sd_shared")))
            rec["own"] = num(r.get("mean_own"))
        rec["natural"] = first(rec["natural"], num(r.get("natural")),
                               num(r.get("mean_own")) if design == "natural" else None)
        rec["arath"] = first(rec["arath"], num(r.get("arath")), num(r.get("mean_own")) if design == "arath" else None)
        if r.get("note"):
            rec["notes"].append(r["note"])
    return out


def unit_positions(items, gap=0.5):
    """x positions of units grouped by dataset: 1 apart, plus a gap between datasets."""
    xs, x, prev = [], 0.0, None
    for g, _ in items:
        if prev is not None:
            x += 1.0 + (gap if g != prev else 0.0)
        xs.append(x)
        prev = g
    return xs


def unit_labels(items):
    count = {}
    for g, _ in items:
        count[g] = count.get(g, 0) + 1
    return [D.display(g) if count[g] == 1 else f"{D.display(g)} {unit_suffix(u, g)}" for g, u in items]


def fig_electron(plt, tabs):
    """O8 figure (SPEC 3.1): 2 x 2, rows PSM and peptide; left ProSE/MSFragger per run grouped by dataset (decision
    runs hatched and labelled), right combined FDP mean +- SD per run and engine over the shared realisations with a
    1% line; "Sage not run by design". 7.0 x 5 in."""
    rows = tabs.need("O08_electron_runs", ("group", "unit", "role", "level", "ratio", "sage_status", "note",
                                           "fdp_prose_mean", "fdp_prose_sd", "fdp_msfragger_mean",
                                           "fdp_msfragger_sd"))
    o11 = tabs.optional("O11_fdp_runs", ("engine", "unit", "role", "level", "design", "mean_own", "mean_shared",
                                         "sd_shared"))
    fdp = fdp_index(o11)
    items = []
    for r in rows:
        if (r["group"], r["unit"]) not in items:
            items.append((r["group"], r["unit"]))
    items.sort(key=lambda it: D.order_key(it[0]))  # stable: table order within a dataset
    xs = unit_positions(items)
    labels = unit_labels(items)
    levels = [lv for lv in D.LEVELS if any(r["level"] == lv for r in rows)]
    fig, axs = new_figure(plt, 5.0, len(levels), 2, sharex=True)
    engines = ("prose", "msfragger")
    off = dodge(engines, 0.32)
    for i, level in enumerate(levels):
        by_unit = {r["unit"]: r for r in rows if r["level"] == level}
        ax, bx = axs[i][0], axs[i][1]
        marks, fmarks = Marks(ax), Marks(bx)
        top = 1.0
        for x, (g, u) in zip(xs, items):
            r = by_unit.get(u)
            ratio = num(r["ratio"]) if r else None
            decision = r is not None and r["role"] == "decision"
            if ratio is None:
                marks.add(x, reason_label(r["note"] if r else "", "empty"))
            else:
                ax.bar(x, ratio - 1, bottom=1, width=0.7, color=D.COLOUR["msfragger"],
                       edgecolor="white" if decision else D.COLOUR["msfragger"], hatch=HATCH if decision else None,
                       lw=0.6, zorder=2)
                top = max(top, ratio)
                if decision:
                    ax.annotate("decision", xy=(x, max(ratio, 1)), xytext=(0, 2), textcoords="offset points",
                                rotation=90, ha="center", va="bottom", color="0.3")
            for e in engines:
                rec = fdp.get((e, u, level))
                if o11:
                    mean, sd = rec["shuffled"] if rec else (None, None)
                    own = rec["own"] if rec else None
                    notes = rec["notes"] if rec else []
                else:  # O11_fdp_runs absent: O08's own values (labelled in the title)
                    mean, sd = (num(r[f"fdp_{e}_mean"]), num(r[f"fdp_{e}_sd"])) if r else (None, None)
                    own, notes = mean, ([r["note"]] if r else [])
                xe = x + off[e]
                if decision:
                    if first(own, mean) is not None:
                        bx.plot([xe], [100 * first(own, mean)], ls="none", marker="o", ms=3.5, mfc="none", mec=GREY,
                                mew=0.8, zorder=3)
                elif mean is not None:
                    bx.errorbar([xe], [100 * mean], yerr=None if sd is None else [100 * sd], fmt="o", ms=3.2,
                                color=D.COLOUR[e], elinewidth=0.7, zorder=3)
                elif own is not None:  # counted, but the run is not in F (no realisation shared by both engines)
                    fmarks.add(xe, "not shared", D.COLOUR[e])
                elif r is not None:
                    fmarks.add(xe, reason_label(*notes, r["note"], engine=e), D.COLOUR[e])
        ax.axhline(1, color="black", lw=0.6, zorder=2.5)
        bottom = min(ax.get_ylim()[0], 0.9)
        ax.set_ylim(bottom, top + 0.18 * (top - bottom) + 0.05)
        one_percent_line(bx)
        bx.set_ylim(bottom=0)
        marks.draw()
        fmarks.draw()
        ax.set_ylabel("ProSE / MSFragger")
        bx.set_ylabel("combined entrapment FDP (%)")
        title(ax, f"({chr(97 + 2 * i)}) {LEVEL_NAME[level]}: identifications, ProSE / MSFragger")
        title(bx, f"({chr(98 + 2 * i)}) {LEVEL_NAME[level]}: entrapment FDP, mean ± SD"
                  + (" of the shared realisations" if o11 else " (own realisations)"))
        for a in (ax, bx):
            for k in range(1, len(items)):
                if items[k][0] != items[k - 1][0]:
                    a.axvline((xs[k - 1] + xs[k]) / 2, color="0.85", lw=0.5, zorder=0)
    for a in axs[-1]:
        category_axis(a, xs, labels, [g for g, _ in items])
        a.set_xlim(xs[0] - 0.7, xs[-1] + 0.7)
    legend_top(fig, [patch_handle("ProSE / MSFragger", D.COLOUR["msfragger"]),
                     patch_handle("decision run (in no summary)", D.COLOUR["msfragger"], "white", HATCH)]
               + engine_handles(engines) + [marker_handle("decision run", "o", GREY, face="none"),
                                            text_handle("Sage: not run by design")], 6)
    return fig, f"{2 * len(levels)} panels, {len(items)} x categories"


# ---------------------------------------------------------------- O9: immunopeptidomics
def fig_immuno(plt, tabs):
    """O9 figure (SPEC 3.1): 2 x 2, rows pxd019643 and pxd058436, columns class I and class II; x DN05, DN13, DN14;
    bars ProSE main arrangement, ProSE other arrangement ("not run" until it exists), Sage, MSFragger; published values
    as markers (MHCquant diamond, FragPipe triangle, PEAKS square; "local FDR" for pxd019643); Sage failed as x
    "failed (memory)"; decision samples hatched; peptides at 1% peptide-level FDR. 7.0 x 5 in."""
    from matplotlib import ticker
    rows = tabs.need("O09_immuno_samples", ("group", "grade", "sample", "donor_tissue", "role", "level",
                                            "main_arrangement", "prose_main", "prose_other", "sage", "sage_status",
                                            "msfragger", "mhcquant", "fragpipe", "peaks", "fdr_note", "note"))
    rows = [r for r in rows if r["level"] == "peptide"]  # peptide level is primary (DS:625)
    if not rows:
        raise Skip("O09_immuno_samples has no peptide row")
    main = next((r["main_arrangement"] for r in rows if r["main_arrangement"] not in NA_TEXT), "main")
    other = {"per_file": "joint", "joint": "per_file"}.get(main, "other")
    bars = (("prose_main", D.COLOUR["prose"], "white", None, f"ProSE {main} (main)"),
            ("prose_other", "white", D.COLOUR["prose"], "....", f"ProSE {other} (other arrangement)"),
            ("sage", D.COLOUR["sage"], "white", None, "Sage"),
            ("msfragger", D.COLOUR["msfragger"], "white", None, "MSFragger"))
    published = (("mhcquant", "D", "MHCquant2"), ("fragpipe", "^", "FragPipe"), ("peaks", "s", "PEAKS"))
    width = 0.16
    offs = [-2 * width, -width, 0.0, width]
    pub_x = 2 * width + 0.02
    fig, axs = new_figure(plt, 5.0, 2, 2)
    local_used = False
    n_x = 0
    for i, project in enumerate(("pxd019643", "pxd058436")):
        for j, cls_name in enumerate(("classI", "classII")):
            ax = axs[i][j]
            group = f"{project}_{cls_name}"
            sub = sorted((r for r in rows if r["group"] == group), key=lambda r: donor_number(r["sample"]))
            grade = D.grade(group) if D.grade(group) != "-" else (sub[0]["grade"] if sub else "-")
            title(ax, f"({chr(97 + 2 * i + j)}) {D.display(group)}" + (f" ({grade})" if grade != "-" else ""))
            if not sub:
                ax.text(0.5, 0.5, "no sample in the table", transform=ax.transAxes, ha="center", va="center",
                        color="0.3")
                ax.set_xticks([])
                continue
            marks = Marks(ax)
            ticks = []
            for x, r in enumerate(sub):
                decision = r["role"] == "decision"
                donor, tissue = donor_of(r["sample"], r["donor_tissue"])
                ticks.append(donor + (f"\n{tissue}" if tissue else "") + ("\ndecision" if decision else ""))
                for (col, face, edge, hatch, _), o in zip(bars, offs):
                    v = num(r[col])
                    if v is None:
                        if col == "prose_other":
                            why = "not run"
                        elif col == "sage":
                            why = reason_label(r["sage_status"], r["note"])
                        else:
                            why = reason_label(r["note"])
                        marks.add(x + o, why, face if face != "white" else edge)
                        continue
                    if decision:
                        hatch = HATCH if hatch is None else hatch + "//"
                        edge = "white" if face != "white" else edge
                    ax.bar(x + o, v, width=width, color=face, edgecolor=edge, hatch=hatch, lw=0.5, zorder=2)
                local = r["fdr_note"].strip().lower() == "local"
                for k, (col, marker, _) in enumerate(published):
                    v = num(r[col])
                    if v is not None:
                        local_used = local_used or local
                        ax.plot([x + pub_x + (k - 1) * 0.045], [v], ls="none", marker=marker, ms=3.8,
                                mfc="0.6" if local else "white", mec="black", mew=0.7, zorder=4)
            n_x += len(sub)
            ax.set_xticks(range(len(sub)))
            ax.set_xticklabels(ticks)
            ax.tick_params(axis="x", length=0)
            ax.set_xlim(-0.6, len(sub) - 0.4)
            ax.set_ylim(bottom=0)
            ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda v, _: f"{v:,.0f}"))  # as fig_ids_counts
            marks.draw(mode="slot")
            if j == 0:
                ax.set_ylabel("unique peptides at 1%\npeptide-level FDR")
    hs = [patch_handle(label, face, edge, hatch) for _, face, edge, hatch, label in bars]
    hs += [marker_handle(label, marker, "black", face="white") for _, marker, label in published]
    if local_used:
        hs.append(marker_handle("MHCquant 1.5.1, local FDR", "D", "black", face="0.6"))
    hs.append(patch_handle("decision sample (hatched)", "0.6", "white", HATCH))
    legend_top(fig, hs, min(5, (len(hs) + 1) // 2))  # two legend rows, never one entry alone in a third
    return fig, f"4 panels, {n_x} x categories"


# ---------------------------------------------------------------- O11 + O12: entrapment FDP
def fig_fdp(plt, tabs):
    """O11 figure with O12's arath values (SPEC 3.2): rows PSM and peptide; x the tryptic datasets then the electron
    datasets in design order, engines dodged; per run the shared shuffled mean as a filled dot with an SD bar, natural
    as a diamond, arath as a triangle, decision runs as grey open circles; dashed 1% line; y in %. 7.0 x 5 in."""
    rows = tabs.need("O11_fdp_runs", ("engine", "group", "unit", "role", "level", "design", "mean_own", "mean_shared",
                                      "sd_shared", "natural", "arath", "note"))
    fdp = fdp_index(rows)
    for r in tabs.optional("O12_fdp_arath", ("engine", "unit", "level", "arath")):
        rec = fdp.get((r["engine"], r["unit"], r["level"]))
        if rec is not None and rec["arath"] is None:
            rec["arath"] = num(r["arath"])
    groups = ordered_groups(rec["group"] for rec in fdp.values() if D.kind(rec["group"]) != "immuno")
    engines = engines_in(rows)
    off = dodge(engines, 0.27)
    levels = [lv for lv in D.LEVELS if any(k[2] == lv for k in fdp)]
    fig, axs = new_figure(plt, 5.0, len(levels), 1, sharex=True)
    for i, level in enumerate(levels):
        ax = axs[i][0]
        marks = Marks(ax)
        for x, g in enumerate(groups):
            for e in engines:
                recs = [rec for (en, _, lv), rec in fdp.items() if en == e and lv == level and rec["group"] == g]
                for rec, o in zip(recs, spread(len(recs), 0.08)):
                    xe = x + off[e] + o
                    mean, sd = rec["shuffled"]
                    if rec["role"] == "decision":
                        v = first(rec["own"], rec["natural"], rec["arath"])
                        if v is not None:
                            ax.plot([xe], [100 * v], ls="none", marker="o", ms=3.4, mfc="none", mec=GREY, mew=0.8,
                                    zorder=3)
                        continue
                    if mean is not None:
                        ax.errorbar([xe], [100 * mean], yerr=None if sd is None else [100 * sd], fmt="o", ms=3,
                                    color=D.COLOUR[e], elinewidth=0.7, zorder=4)
                    if rec["natural"] is not None:
                        ax.plot([xe], [100 * rec["natural"]], ls="none", marker="D", ms=3, mfc="white",
                                mec=D.COLOUR[e], mew=0.8, zorder=5)
                    if rec["arath"] is not None:
                        ax.plot([xe], [100 * rec["arath"]], ls="none", marker="^", ms=3.4, mfc="white",
                                mec=D.COLOUR[e], mew=0.8, zorder=5)
                    if mean is None and rec["natural"] is None and rec["arath"] is None:
                        # counted, but no realisation shared by every expected engine (not in F); else the reason
                        why = "not shared" if rec["own"] is not None else reason_label(*rec["notes"], engine=e)
                        marks.add(xe, why, D.COLOUR[e])
        one_percent_line(ax)
        ax.set_ylim(bottom=0)
        marks.draw()
        ax.set_ylabel("combined entrapment FDP (%)")
        blocks = draw_blocks(ax, groups, label=(i == 0))
        title(ax, f"({'ab'[i]}) {LEVEL_NAME[level]} level, q ≤ 0.01", above_blocks=blocks)
    dataset_axis(axs[-1][0], groups)
    legend_top(fig, engine_handles(engines) + [
        marker_handle("shuffled s1–s3: mean ± SD (shared realisations)", "o", "0.2"),
        marker_handle("natural entrapment", "D", "0.2", face="white"),
        marker_handle("Arabidopsis reference", "^", "0.2", face="white"),
        marker_handle("decision run", "o", GREY, face="none")], 4)
    return fig, f"{len(levels)} panels, {len(groups)} x categories"


# ---------------------------------------------------------------- O13: matched FDP
def fig_matched_fdp(plt, tabs):
    """O13 figure (SPEC 3.2): per run, ProSE's lead at q <= 0.01 against its lead at the matched combined FDP of 1%, on
    the same entrapment searches; one panel per level, one colour per comparator, marker by design (shuffled mean
    dot, natural diamond, arath triangle), decision runs grey open; identity line."""
    rows = tabs.need("O13_matched_fdp", ("pair", "level", "role", "design", "ratio_q01", "ratio_matched"))
    levels = [lv for lv in D.LEVELS if any(r["level"] == lv for r in rows)]
    if not levels:
        raise Skip("O13_matched_fdp has no psm or peptide row")
    shapes = {"shuffled": "o", "natural": "D", "arath": "^"}
    fig, axs = new_figure(plt, 3.4, 1, len(levels), categorical=False)
    comps = []
    n_points = 0
    for i, level in enumerate(levels):
        ax = axs[0][i]
        lo, hi = 0.0, 0.0
        for r in rows:
            if r["level"] != level:
                continue
            a, b = num(r["ratio_q01"]), num(r["ratio_matched"])
            if a is None or b is None or a <= 0 or b <= 0:
                continue
            comp = comparator_of(r["pair"]) or "prose"
            if comp not in comps:
                comps.append(comp)
            la, lb = 100 * (a - 1), 100 * (b - 1)
            lo, hi = min(lo, la, lb), max(hi, la, lb)
            marker = shapes.get(r["design"], "o")
            if r["role"] == "decision":
                ax.plot([la], [lb], ls="none", marker=marker, ms=3.4, mfc="none", mec=GREY, mew=0.8, zorder=3)
            else:
                ax.plot([la], [lb], ls="none", marker=marker, ms=3.2, mfc=D.COLOUR[comp] if marker == "o" else "white",
                        mec=D.COLOUR[comp], mew=0.8, zorder=4)
            n_points += 1
        pad = 0.08 * (hi - lo or 1.0)
        ax.plot([lo - pad, hi + pad], [lo - pad, hi + pad], color="0.4", ls="--", lw=0.7, zorder=1)
        ax.axhline(0, color="0.7", lw=0.5, zorder=0)
        ax.axvline(0, color="0.7", lw=0.5, zorder=0)
        ax.set_xlim(lo - pad, hi + pad)
        ax.set_ylim(lo - pad, hi + pad)
        ax.set_aspect("equal", adjustable="box")
        ax.set_xlabel("ProSE lead at q ≤ 0.01 (%)")
        ax.set_ylabel("ProSE lead at matched 1% FDP (%)")
        title(ax, f"({'ab'[i]}) {LEVEL_NAME[level]} level, entrapment searches")
    hs = [marker_handle(f"ProSE vs {D.ENGINE_NAME[c]}", "o", D.COLOUR[c]) for c in comps if c != "prose"]
    hs += [marker_handle("shuffled (mean of shared)", "o", "0.2"), marker_handle("natural", "D", "0.2", face="white"),
           marker_handle("Arabidopsis", "^", "0.2", face="white"),
           marker_handle("decision run", "o", GREY, face="none")]
    legend_top(fig, hs, 4)
    return fig, f"{len(levels)} panels, {n_points} points"


# ---------------------------------------------------------------- O15: per-file timing
def fig_time_per_file(plt, tabs):
    """O15 figure (SPEC 3.3): rows wall time per file (min, log) and peak RSS (GiB, log); x the tryptic datasets then
    electron then immuno; one dot per unit per engine, dodged; failed_memory as x on the 200 GiB cap line of the RSS
    panel and a "failed (memory)" label below the time axis, never at the top (DS:649); 200 GiB cap line. The reason
    of every missing value is written once, below the time axis; the RSS panel repeats only the x marks.
    A pooled sample's wall time is divided by its n_files (time per file). 7.0 x 5 in."""
    rows = tabs.need("O15_time_runs", ("engine", "group", "unit", "role", "n_files", "state", "wall_med_s",
                                       "rss_med_gib", "note"))
    groups = ordered_groups(r["group"] for r in rows)
    engines = engines_in(rows)
    off = dodge(engines, 0.27)
    fig, axs = new_figure(plt, 5.0, 2, 1, sharex=True)
    ta, ra = axs[0][0], axs[1][0]
    # the reasons are written once, below the time axis (outside the data); the RSS panel repeats only the marks
    tmarks, rmarks = Marks(ta), Marks(ra)
    seen = set()  # legend keys only for what is drawn: an x without a cap is a labelled missing value, not a failure
    for x, g in enumerate(groups):
        for e in engines:
            sub = [r for r in rows if r["group"] == g and r["engine"] == e]
            for r, o in zip(sub, spread(len(sub), 0.08)):
                xe = x + off[e] + o
                n_files = num(r["n_files"]) or 1.0
                wall, rss = num(r["wall_med_s"]), num(r["rss_med_gib"])
                if r["role"] == "decision":
                    style = dict(ls="none", marker="o", ms=3.4, mfc="none", mec=GREY, mew=0.8)
                    seen.add("decision")
                else:
                    style = dict(ls="none", marker="o", ms=3, mfc=D.COLOUR[e], mec=D.COLOUR[e], mew=0.5)
                if state_word(r["state"]) == "failed_memory":  # on the cap line, never "slow" (DS:649, 653)
                    ra.plot([xe], [D.CAP_GIB], ls="none", marker="x", ms=4, mew=0.9, color=D.COLOUR[e], zorder=6)
                    tmarks.add(xe, "failed (memory)", D.COLOUR[e])
                    seen.add("failed_memory")
                    continue
                label = reason_label(r["state"], r["note"])
                if wall is not None and wall > 0:
                    ta.plot([xe], [wall / n_files / 60.0], zorder=4, **style)
                else:
                    tmarks.add(xe, label, D.COLOUR[e])
                if rss is not None and rss > 0:
                    ra.plot([xe], [rss], zorder=4, **style)
                else:
                    rmarks.add(xe, None, D.COLOUR[e])
    for a in (ta, ra):
        a.set_yscale("log")
    cap_line(ra)
    lo, hi = ra.get_ylim()
    ra.set_ylim(lo, max(hi, D.CAP_GIB * 1.8))
    for a in (ta, ra):
        log_ticks(a)
    tmarks.draw(mode="below", gap=2.5)
    rmarks.draw()
    ta.set_ylabel("wall time per file (min)")
    ra.set_ylabel("peak RSS (GiB)")
    blocks = draw_blocks(ta, groups, label=True)
    draw_blocks(ra, groups, label=False)
    title(ta, "(a) wall time per file, median of 3 repetitions", above_blocks=blocks)
    title(ra, "(b) peak memory (RSS), median of 3 repetitions")
    dataset_axis(ra, groups)
    handles = engine_handles(engines)
    if "decision" in seen:
        handles.append(marker_handle("decision run", "o", GREY, face="none"))
    if "failed_memory" in seen:
        handles.append(marker_handle("failed (memory): drawn at the cap", "x", "0.2"))
    legend_top(fig, handles, 5)
    return fig, f"2 panels, {len(groups)} x categories"


# ---------------------------------------------------------------- O16: batch arm
def fig_batch(plt, tabs):
    """O16 figure (SPEC 3.3): x the batch groups in batch order (16 tryptic, then pxd065289_etcid in an electron block),
    labels with grade; y batch / sum of the per-file wall times on a log2 axis, one marker per engine, reference line
    at 1; open markers: group not in B3. 7.0 x 3 in."""
    rows = tabs.need("O16_batch", ("engine", "group", "ratio_wall", "in_B3", "note"))
    groups = ordered_groups(r["group"] for r in rows)
    engines = engines_in(rows)
    off = dodge(engines, 0.22)
    fig, axs = new_figure(plt, 3.0)
    ax = axs[0][0]
    marks = Marks(ax)
    values = [1.0]
    open_used = False
    for x, g in enumerate(groups):
        for e in engines:
            for r in (r for r in rows if r["group"] == g and r["engine"] == e):
                v = num(r["ratio_wall"])
                if v is None or v <= 0:
                    marks.add(x + off[e], reason_label(r["note"]), D.COLOUR[e])
                    continue
                in_b3 = yes(r["in_B3"])
                open_used = open_used or not in_b3
                ax.plot([x + off[e]], [v], ls="none", marker="o", ms=3.6, mfc=D.COLOUR[e] if in_b3 else "white",
                        mec=D.COLOUR[e], mew=0.8, zorder=4)
                values.append(v)
    ax.set_yscale("log", base=2)
    log2_ticks(ax, values)
    ax.axhline(1, color="0.3", lw=0.7, zorder=1)
    marks.draw()
    ax.set_ylabel("batch / Σ per-file wall time")
    blocks = draw_blocks(ax, groups, label=True)
    title(ax, "batch arm: wall time of the batch search over the sum of the per-file medians", above_blocks=blocks)
    dataset_axis(ax, groups)
    hs = engine_handles(engines)
    if open_used:
        hs.append(marker_handle("open: group not in B3", "o", "0.3", face="white"))
    legend_top(fig, hs, 4)
    return fig, f"1 panel, {len(groups)} x categories"


# ---------------------------------------------------------------- O17: thread scaling
def fig_scaling(plt, tabs):
    """O17 figure (SPEC 3.3): 2 x 2, (a) wall time against threads n, log-log, ideal T_1/n dashed; (b) speed-up, ideal
    y = n; (c) efficiency; (d) peak RSS. x ticks at the grid points; the 16-thread point in an open ring ("workstation
    comparison", DS:671); the engine node's per_file point (the rows of the other machine) as an open square just
    right of its own thread count, which the legend states: at 16 threads, as per_file runs in the paper (DS:657), it
    stands beside the ringed 16-thread point (SPEC O17); a per_file run at another count (both trials: 64) is drawn at
    that count, with a tick of its own when the grid lacks it, never beside n = 16 (a row without a thread count:
    beside 16, or beside the largest grid point below 16); over_limit points
    as triangles at their lower bound, points without a value as x at the axis base. Without T_1 the relative columns
    (speedup_rel, efficiency_rel) are drawn and the ideal is relative to the smallest completed n. 7.0 x 5.5 in."""
    from matplotlib import ticker
    from matplotlib.lines import Line2D
    rows = tabs.need("O17_scaling", ("engine", "machine", "threads", "state", "wall_med_s", "wall_lower_bound_s",
                                     "rss_med_gib", "speedup", "efficiency", "speedup_rel", "efficiency_rel"))
    machines = {}
    for r in rows:
        machines[r["machine"]] = machines.get(r["machine"], 0) + 1
    scaling_machine = max(machines, key=lambda m: (machines[m], "engine" not in m.lower()))
    engines = engines_in(rows)
    grid = sorted({int(num(r["threads"])) for r in rows if num(r["threads"]) is not None
                   and r["machine"] == scaling_machine})
    def reference_n(r):
        """The thread count at which an engine-node per_file point is drawn (just right of it, x 1.12): its own."""
        n = num(r["threads"])
        if n is not None and n > 0:
            return n
        return 16 if 16 in grid or not grid else max([g for g in grid if g <= 16] or grid[:1])
    reference_ns = set()
    fig, axs = new_figure(plt, 5.5, 2, 2, categorical=False, sharex=True)
    wa, sa, ea, ma = axs[0][0], axs[0][1], axs[1][0], axs[1][1]
    panels = (("wall", wa), ("speedup", sa), ("efficiency", ea), ("rss", ma))
    marks = {key: Marks(a) for key, a in panels}
    relative_used = over_used = missing_used = ring_used = False
    reference_threads = set()
    for e in engines:
        pts = sorted((r for r in rows if r["engine"] == e and r["machine"] == scaling_machine
                      and num(r["threads"]) is not None), key=lambda r: num(r["threads"]))
        col = D.COLOUR[e]
        absolute = any(num(r["speedup"]) is not None for r in pts)
        sp_col, ef_col = ("speedup", "efficiency") if absolute else ("speedup_rel", "efficiency_rel")
        relative_used = relative_used or (not absolute and any(num(r["speedup_rel"]) is not None for r in pts))
        series = {key: [] for key, _ in panels}
        for r in pts:
            n = num(r["threads"])
            wall = num(r["wall_med_s"])
            values = {"wall": None if wall is None else wall / 60.0, "speedup": num(r[sp_col]),
                      "efficiency": num(r[ef_col]), "rss": num(r["rss_med_gib"])}
            lower = num(r["wall_lower_bound_s"])
            for key, a in panels:
                v = values[key]
                if v is not None and v > 0:
                    series[key].append((n, v))
                elif key == "wall" and state_word(r["state"]) == "over_limit" and lower is not None:
                    a.plot([n], [lower / 60.0], ls="none", marker="^", ms=4.5, mfc=col, mec=col, zorder=5)
                    over_used = True
                else:
                    marks[key].add(n, None, col)
                    missing_used = True
        for key, a in panels:
            if series[key]:
                a.plot([n for n, _ in series[key]], [v for _, v in series[key]], color=col, marker="o", ms=3.2,
                       zorder=4)
            ring = [v for n, v in series[key] if n == 16]
            if ring:
                a.plot([16], ring, ls="none", marker="o", ms=8, mfc="none", mec="black", mew=0.7, zorder=6)
                ring_used = True
        if series["wall"]:  # ideal T_1/n, or T_n0 * n0 / n without T_1
            n0, t0 = series["wall"][0]
            wa.plot(grid, [t0 * n0 / n for n in grid], color=col, ls=(0, (4, 2)) if n0 == 1 else ":", lw=0.7,
                    zorder=2)
            if not absolute and series["speedup"]:
                sa.plot(grid, [n / n0 for n in grid], color=col, ls=":", lw=0.7, zorder=2)
        for r in rows:  # the engine node's per_file point at its own thread count (O17 reference row, DS:671; Q25)
            if r["engine"] == e and r["machine"] != scaling_machine:
                n_ref = reference_n(r)
                for key, a in (("wall_med_s", wa), ("rss_med_gib", ma)):
                    v = num(r[key])
                    if v is not None and v > 0:
                        a.plot([1.12 * n_ref], [v / 60.0 if key == "wall_med_s" else v], ls="none", marker="s",
                               ms=3.6, mfc="white", mec=col, mew=0.9, zorder=6)
                        threads = num(r["threads"])
                        reference_threads.add(f"{threads:g} threads" if threads is not None else "threads not given")
                        reference_ns.add(n_ref)
    if grid:
        sa.plot(grid, grid, color="black", ls=(0, (4, 2)), lw=0.7, zorder=1)
    ea.axhline(1, color="black", ls=(0, (4, 2)), lw=0.7, zorder=1)
    ticks = sorted(set(grid) | reference_ns) or [1]
    for _, a in panels:
        a.set_xscale("log", base=2)
        a.xaxis.set_major_locator(ticker.FixedLocator(ticks))
        a.xaxis.set_minor_locator(ticker.NullLocator())
        a.xaxis.set_major_formatter(ticker.FuncFormatter(lambda v, _: f"{v:g}"))
        if grid:
            a.set_xlim(grid[0] / 1.35, max([grid[-1]] + [1.12 * n for n in reference_ns]) * 1.35)
    wa.set_yscale("log")
    log_ticks(wa)
    sa.set_yscale("log", base=2)
    sa.yaxis.set_major_formatter(ticker.FuncFormatter(lambda v, _: f"{v:g}"))
    ea.set_ylim(bottom=0)
    ma.set_ylim(bottom=0)
    for key, _ in panels:
        marks[key].draw()
    wa.set_ylabel("wall time (min)")
    sa.set_ylabel("speed-up")
    ea.set_ylabel("efficiency")
    ma.set_ylabel("peak RSS (GiB)")
    for a in (ea, ma):
        a.set_xlabel("threads n")
    title(wa, "(a) wall time, median of 3 repetitions")
    title(sa, "(b) speed-up $T_1/T_n$" + (" (dotted: relative to the smallest completed n)" if relative_used else ""))
    title(ea, "(c) efficiency: speed-up / n")
    title(ma, "(d) peak memory (RSS)")
    hs = engine_handles(engines, line=True) + [Line2D([], [], color="black", ls=(0, (4, 2)), lw=0.7, label="ideal")]
    if relative_used:
        hs.append(Line2D([], [], color="0.3", ls=":", lw=0.7, label="ideal from the smallest completed n (no $T_1$)"))
    if over_used:
        hs.append(marker_handle("over limit: lower bound", "^", "0.3", ms=4.5))
    if missing_used:
        hs.append(marker_handle("no value (not run, over limit, failed)", "x", MISSING_COLOUR))
    if ring_used:
        hs.append(marker_handle("16 threads: workstation comparison", "o", "black", face="none", ms=7, mew=0.7))
    if reference_threads:
        hs.append(marker_handle(f"engine node, per_file ({', '.join(sorted(reference_threads))})", "s", "0.3",
                                face="white"))
    legend_top(fig, hs, 4)
    return fig, f"4 panels, {len(grid)} grid points"


# ---------------------------------------------------------------- O10: low_memory
def fig_low_memory(plt, tabs):
    """O10 figure (SPEC 3.3): 2 panels, peak RSS (GiB, with the 200 GiB line) and wall time; x the samples; paired bars
    standard against low_memory. The summary row (role not tuned/heldout/decision) is not a sample. 7.0 x 3 in."""
    rows = tabs.need("O10_low_memory", ("group", "sample", "role", "wall_std", "wall_lm", "rss_std_gib", "rss_lm_gib",
                                        "note"))
    rows = [r for r in rows if r["role"] in ROLES]
    if not rows:
        raise Skip("O10_low_memory has no sample row")
    rows.sort(key=lambda r: (D.order_key(r["group"]), donor_number(r["sample"])))
    items = [(r["group"], r["sample"]) for r in rows]
    xs = unit_positions(items, gap=0.6)
    fig, axs = new_figure(plt, 3.0, 1, 2)
    width = 0.38
    colour = D.COLOUR["prose"]
    for k, (a, std, lm, scale, ylabel, head) in enumerate((
            (axs[0][0], "rss_std_gib", "rss_lm_gib", 1.0, "peak RSS (GiB)", "(a) peak memory (RSS)"),
            (axs[0][1], "wall_std", "wall_lm", 1 / 60.0, "wall time (min)", "(b) wall time"))):
        marks = Marks(a)
        for x, r in zip(xs, rows):
            alpha = 0.45 if r["role"] == "decision" else 1.0
            for col, o, face, hatch in ((std, -width / 2, colour, None), (lm, width / 2, "white", HATCH)):
                v = num(r[col])
                if v is None or v <= 0:
                    marks.add(x + o, reason_label(r["note"]), colour)
                    continue
                a.bar(x + o, v * scale, width=width, color=face, edgecolor=colour, hatch=hatch, lw=0.6, alpha=alpha,
                      zorder=2)
        if k == 0:
            cap_line(a)
            a.set_ylim(0, max(a.get_ylim()[1], D.CAP_GIB * 1.12))  # room for the cap label inside the axes
        else:
            a.set_ylim(bottom=0)
        marks.draw(mode="slot")
        a.set_ylabel(ylabel)
        title(a, head)
        a.set_xticks(xs)
        a.set_xticklabels([donor_of(s)[0] for _, s in items], rotation=90)
        a.tick_params(axis="x", length=0)
        a.set_xlim(xs[0] - 0.7, xs[-1] + 0.7)
        start = 0
        for i in range(1, len(items) + 1):  # dataset labels under the donors, with grade
            if i == len(items) or items[i][0] != items[start][0]:
                g = items[start][0]
                grade = D.grade(g)
                label = D.display(g).replace(" class", "\nclass") + (f" ({grade})" if grade != "-" else "")
                a.annotate(label, xy=((xs[start] + xs[i - 1]) / 2, 0), xycoords=("data", "axes fraction"),
                           xytext=(0, -24), textcoords="offset points", ha="center", va="top")
                if i < len(items):
                    a.axvline((xs[i - 1] + xs[i]) / 2, color="0.85", lw=0.5, zorder=0)
                start = i
    legend_top(fig, [patch_handle("standard (per_file)", colour), patch_handle("low_memory", "white", colour, HATCH),
                     patch_handle("decision sample (faded)", colour, colour, alpha=0.45)], 3)
    return fig, f"2 panels, {len(items)} x categories"


# ---------------------------------------------------------------- O19: calibration
def arm_name(text):
    """'per_file' / 'main' -> 'main'; 'per_file_cal_off' / 'cal_off' -> 'cal_off'."""
    s = (text or "").strip()
    if s in ("per_file", "main", ""):
        return "main"
    return s[len("per_file_"):] if s.startswith("per_file_") else s


def fig_calibration(plt, tabs):
    """O19 figure (SPEC 3.4, optional): per run the arm/main ratio of the td counts (left) and the shuffled FDP mean
    +- SD (right), one marker per engine-arm; PSM filled, peptide open; natural entrapment as a bar marker. 7.0 x 4."""
    rows = tabs.need("O19_calibration_counts", ("unit", "group", "engine", "arm", "level", "ratio_to_main",
                                                "fdp_shuffled_mean", "fdp_shuffled_sd", "fdp_natural", "status"))
    units = []
    for r in rows:
        if (r["group"], r["unit"]) not in units:
            units.append((r["group"], r["unit"]))
    order = {u: i for i, u in enumerate(D.CAL_RUNS)}
    units.sort(key=lambda gu: (order.get(gu[1], len(order)), D.order_key(gu[0])))
    slots = list(CAL_SLOTS) + sorted({(r["engine"], arm_name(r["arm"])) for r in rows} - set(CAL_SLOTS))
    left_slots = [s for s in slots if s[1] != "main"]
    fig, axs = new_figure(plt, 4.0, 1, 2)
    level_off = {"psm": -0.025, "peptide": 0.025}
    for k, (ax, use) in enumerate(((axs[0][0], left_slots), (axs[0][1], slots))):
        off = dodge(use, 0.8 / max(len(use), 1))
        marks = Marks(ax)
        for x, (g, u) in enumerate(units):
            for slot in use:
                e, arm = slot
                for r in rows:
                    if r["unit"] != u or r["engine"] != e or arm_name(r["arm"]) != arm:
                        continue
                    xe = x + off[slot] + level_off.get(r["level"], 0.0)
                    face = D.COLOUR[e] if r["level"] == "psm" else "white"
                    marker = CAL_MARKER.get(arm, "P")
                    if k == 0:
                        v = num(r["ratio_to_main"])
                        if v is None:
                            marks.add(xe, reason_label(r["status"]), D.COLOUR[e])
                        else:
                            ax.plot([xe], [v], ls="none", marker=marker, ms=3.2, mfc=face, mec=D.COLOUR[e], mew=0.7,
                                    zorder=4)
                        continue
                    mean, sd, nat = num(r["fdp_shuffled_mean"]), num(r["fdp_shuffled_sd"]), num(r["fdp_natural"])
                    if mean is not None:
                        ax.errorbar([xe], [100 * mean], yerr=None if sd is None else [100 * sd], fmt=marker, ms=3.2,
                                    mfc=face, mec=D.COLOUR[e], mew=0.7, ecolor=D.COLOUR[e], elinewidth=0.6, zorder=4)
                    if nat is not None:
                        ax.plot([xe], [100 * nat], ls="none", marker="_", ms=5, mew=1.0, color=D.COLOUR[e], zorder=5)
                    if mean is None and nat is None:
                        marks.add(xe, reason_label(r["status"]), D.COLOUR[e])
        if k == 0:
            ax.axhline(1, color="0.3", lw=0.7, zorder=1)
            ax.set_ylabel("arm / main, td accepted")
            title(ax, "(a) identifications of the arm over the main arm")
        else:
            one_percent_line(ax)
            ax.set_ylim(bottom=0)
            ax.set_ylabel("combined entrapment FDP (%)")
            title(ax, "(b) entrapment FDP, shuffled mean ± SD")
        marks.draw()
        for i in range(1, len(units)):
            ax.axvline(i - 0.5, color="0.88", lw=0.5, zorder=0)
        category_axis(ax, range(len(units)), unit_labels(units), [g for g, _ in units])
        ax.set_xlim(-0.6, len(units) - 0.4)
    hs = [marker_handle(f"{D.ENGINE_NAME[e]} {CAL_LABEL.get(arm, arm)}", CAL_MARKER.get(arm, "P"), D.COLOUR[e])
          for e, arm in slots]
    hs += [marker_handle("PSM (filled)", "o", "0.3"), marker_handle("peptide (open)", "o", "0.3", face="white"),
           marker_handle("natural entrapment", "_", "0.3", ms=5, mew=1.0)]
    legend_top(fig, hs, 5)
    return fig, f"2 panels, {len(units)} x categories"


# ---------------------------------------------------------------- the figure index (SPEC 3.7)
FIGURES = (
    ("fig_overtuning_psm", fig_overtuning, ("psm",)),
    ("fig_overtuning_peptide", fig_overtuning, ("peptide",)),
    ("fig_ids_counts_psm", fig_ids_counts, ("psm",)),
    ("fig_ids_counts_peptide", fig_ids_counts, ("peptide",)),
    ("fig_electron", fig_electron, ()),
    ("fig_immuno", fig_immuno, ()),
    ("fig_fdp", fig_fdp, ()),
    ("fig_matched_fdp", fig_matched_fdp, ()),
    ("fig_time_per_file", fig_time_per_file, ()),
    ("fig_batch", fig_batch, ()),
    ("fig_scaling", fig_scaling, ()),
    ("fig_low_memory", fig_low_memory, ()),
    ("fig_calibration", fig_calibration, ()),
    ("fig_ext_percolator", fig_pair_leads, ("O20_external_percolator", "external Percolator")),
    ("fig_prediction", fig_pair_leads, ("O21_prediction", "prediction")),
)
FIGURE_NAMES = tuple(name for name, _, _ in FIGURES)
