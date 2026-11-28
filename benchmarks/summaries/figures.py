"""Figures of the paper (SPEC v2 section 3.7), drawn from the written tables only.

This is the only module of the package that imports matplotlib, and it does so lazily inside draw(), with the Agg
backend (SPEC section 1, "matplotlib only in figures.py, imported lazily"). It reads only <out>/tables/*.tsv through
tables.read_table, never the raw inputs, so `summarize.py --figures-only` can run in WSL on a copied output folder.

Figure index (SPEC 3.7) and the tables each figure reads
  fig_ids_panels_psm / _peptide  O3       O03_three_runs (R3 units), O03_three_datasets (optional: the excluded
                                          units and the reasons), O14_coverage (optional): Fig 1 / FigS1, one small
                                          panel per dataset (owner, 2026-11-28)
  fig_overtuning_psm / _peptide  O5 / O7  O04_overtuning_<level>_datasets and _sides; run points from
                                          O04_overtuning_<level>_runs (OT's rows: engine side dataset run ratio
                                          dataset_value) when written, else the used runs of O02_pairs_runs (C6b checks
                                          that these equal OT's rows)
  fig_ids_counts_psm / _peptide  O3       O03_three_runs (R3 units); drawn, but no paper number since 2026-11-28
  fig_electron                   O8       O08_electron_runs; FDP of the shared realizations from O11_fdp_runs (the own
                                          values of O08 only when O11_fdp_runs is absent, labelled)
  fig_immuno                     O9       O09_immuno_samples (level peptide, DS:625)
  fig_fdp                        O11+O12  O11_fdp_runs; arath from O12_fdp_arath where O11_fdp_runs has none
  fig_fdp_main                   O11      O11_fdp_runs: the slim main-text version of fig_fdp (tryptic datasets,
                                          shuffled mean +- SD per run, natural values as open diamonds)
  fig_matched_fdp                O13      O13_matched_fdp (pair level role design ratio_q01 ratio_matched)
  fig_time_per_file              O15      O15_time_runs
  fig_batch                      O16      O16_batch (batch time per file and the batch / separate-file ratio)
  fig_scaling                    O17      O17_scaling
  fig_low_memory                 O10      O10_low_memory
  fig_calibration                O19      O19_calibration_counts
  fig_ext_percolator             O20      O20_external_percolator (runs), _datasets (bars) and _summary (the mean
                                          leads over the tuning and the held-out datasets), "as O5"
  fig_prediction                 O21      O21_prediction (runs) and _datasets (bars), the same layout
  fig_fdp, fig_time_per_file and fig_batch also read O14_coverage (optional) for their "Sage: not run" label;
  fig_fdp_main and fig_fdp read it for the reason of an immunopeptidomics group without an O11 row (index.tsv).

Common rules (SPEC 3 "Figures", "Grade everywhere"; the camera-ready rules G1-G17 of FIGURES_CAMERA_READY.md)
- Width 7.0 in (double column), height at most 9 in, every text 7 pt; PDF with pdf.fonttype 42 (TrueType embedded)
  and PNG at 300 dpi. No mathtext (text.parse_math off: a '$' prints as it is), so no subscript prints below 6 pt.
- No printed stroke below 0.5 pt and no transparency (no alpha below 1 anywhere).
- Font: the first installed of FONTS (Arial, Helvetica, then fonts with Arial's metrics). When the environment variable
  SUMMARIZE_FONT_DIR names a folder, its files arial.ttf, arialbd.ttf, ariali.ttf and arialbi.ttf (any case, no other
  file) are added to matplotlib's font list at run time; nothing is installed. draw() writes the font in use.
- Engine colours fixed: Okabe-Ito, design.COLOUR (ProSE #0072B2, Sage #009E73, MSFragger #D55E00).
- Words, not code names: every legend entry, axis label and heading takes its words from VOCAB, REASON_LABEL,
  CAL_LABEL or design.py's display names; BANNED lists the code names that must not be visible.
- Panel letters: every figure with more than one panel has bold letters (PANEL_LETTERS) at the left edge of the
  panel's column, on the baseline of the heading; headings are a few words without method details. Exception:
  fig_ids_panels (Fig 1, FigS1), one like panel per dataset whose title names it, has no letters and its legend
  right of row 2 (owner, 2026-11-28; README).
- A missing value is never drawn as 0 or as an extreme value. It is drawn as an x at the axis base with a short label
  taken from the row's status/state/note ("out of memory", "not run"); neighbouring marks with the same label share
  one label. Where an x would mislead (at the base of a log time axis it reads as the fastest value), the label is
  drawn without the x (Marks.add(..., mark=False)): every missing value of a log time axis (fig_time_per_file A,
  fig_batch A) is a label below that axis, and one of the log count axis of fig_ids_counts a label at its base. A
  lead axis (O5, fig_electron, fig_calibration) labels a missing value at its zero line, without an x ("n/a" for a
  dropped dataset, SPEC O5). O15 draws a failed_memory search as an x on the 200 GiB cap line of the RSS panel and
  labels it below the time axis (SPEC O15). Where the runs of an engine are spread in a column, their missing values
  share one x at the engine's place (Marks). Where Sage was never run (O14 state not_run_by_design, and no Sage
  value in the figure's own table), one label "Sage: not run" without an x stands under the run of such categories
  (G15), on two lines when one line is wider than the run.
- Dodge: in Fig 3, FigS4 and FigS6 the engines side by side in a category are the engines with a row there (no empty
  slot where Sage has no run); the FDP columns of Fig 2 and FigS4 dodge less when an engine has fewer than 3 runs
  (fdp_dodge); FigS9 puts each arm at one x in all four rows.
- Every held-out category label carries its grade letter: a row of grade letters directly under the axis, labelled
  "grade" at its left (SPEC O5: "the grade letter under each held-out label"); tuning datasets have none (grade '-').
  Exception: fig_ids_panels (Fig 1, FigS1) has no grade, development or held-out word at all (owner, 2026-11-28).
- Decision runs have no mark of their own (owner, 2026-11-28; DS 4.6 "Datasets."): the figures of single runs
  (fig_time_per_file, fig_immuno, fig_fdp, fig_electron, fig_low_memory, fig_matched_fdp) draw them as any other run;
  fig_ids_panels_*, fig_overtuning_*, fig_fdp_main, fig_ids_counts_* and fig_pair_leads leave them out. index.tsv has
  no fact about them.
- Hatching means held-out (the lead figures) only. ProSE in a non-default mode (low-memory, joint rescoring) is an open
  bar: white with a ProSE-blue edge. The bars of fig_overtuning (FigS2, FigS3) are neutral grey (LEAD_GREY, D2
  alternative); those of fig_pair_leads keep the comparator colour.
- FDP columns are fractions (combined_fdp of counts.tsv, EE-lib:30-34; O12's difference_pp = 100 x (arath - shuffled
  mean)); the figures show them in percent on one axis format (fdp_axis) with a dashed 1% line.

Paper copies: PAPER_FIGURES maps the code names to the paper's numbers. draw() also writes figures/main/Fig<n>_<name>
and figures/supplement/FigS<n>_<name> (PDF and PNG) and figures/index.tsv (one row per drawn figure: number, file,
size, tables read, the caption items of the camera-ready spec and facts from the tables for the caption writer).

Skips and failures
- A figure whose table is absent or has no data row is skipped with an INFO line; a file of that figure left by an
  earlier build is removed, so no stale figure stays next to fresh ones (the package's own output names, as
  summarize.py does for stale tables). The same holds for the paper copies in figures/main and figures/supplement:
  a copy that this build did not write is removed, and index.tsv lists the drawn figures only.
- A figure that raises gives 'FAIL FIGURES <figure>: <exception>'; the other figures are still drawn, and draw()
  raises FigureError at the end, chained to the first exception, so that summarize.py writes its traceback to
  errors.txt (module contract).
"""
import math
import os
import re

from . import design as D
from . import tables as T

WIDTH = 7.0  # in; double column (SPEC 3 "Figures"; ACS 178 mm)
MAX_HEIGHT = 9.0  # in; the journal's page height for a figure with its caption room
FONT_PT = 7
DPI = 300
HANDLE_LENGTH = 1.6  # legend handles, in font sizes: 11.2 pt
FONTS = ("Arial", "Helvetica", "Arimo", "Liberation Sans", "Nimbus Sans", "DejaVu Sans")  # first one installed
PREFERRED_FONTS = ("Arial", "Helvetica")  # any other font gives a WARN (not strict)
FONT_DIR_ENV = "SUMMARIZE_FONT_DIR"  # a folder whose FONT_FILES are added at run time (nothing is installed)
FONT_FILES = ("arial.ttf", "arialbd.ttf", "ariali.ttf", "arialbi.ttf")  # compared case-insensitively
GREY = "0.55"  # neutral legend handles only
LEAD_GREY = "0.35"  # the bars of fig_overtuning (FigS2, FigS3): D2 alternative, filled (development) or hatched edge
MISSING_COLOUR = "0.25"
HATCH = "//////"  # held-out bars of the lead figures only
ROLES = ("tuned", "heldout", "decision")
NA_TEXT = ("", "NA", "nan", "NaN", "None", "-")
LEVEL_NAME = {"psm": "PSM", "peptide": "peptide"}
LEVEL_UNIT = {"psm": "PSMs", "peptide": "peptides"}
# block = the MS2 analyzer class (the caption says so); a name wider than its block takes its short form
BLOCK_NAME = {"IT": "ion trap", "OT": "Orbitrap", "Astral": "Astral", "timsTOF": "timsTOF",
              "electron": "electron-based", "immuno": "immunopeptidomics", "other": "other"}
BLOCK_SHORT = {"IT": "IT", "OT": "OT", "electron": "electron", "immuno": "immuno-\npeptidomics"}
# short labels of the missing-value reasons (SPEC 2.6), found as words of a status, state or note cell
REASON_LABEL = {
    "failed_memory": "out of memory", "failed": "failed", "not_run_by_design": "not run",
    "not_run": "not run", "running": "running", "interrupted": "interrupted", "unknown": "unknown",
    "over_limit": "over limit", "not_run_over_limit": "not run (over limit)", "incomplete": "incomplete",
    "no_timing": "no timing", "no_timing_rows": "no timing", "stale_timing": "stale timing", "zero": "zero count",
    "none_accepted": "none accepted", "not_counted": "not counted", "empty": "n/a", "outside_design": "outside design",
    "no_coverage": "no coverage", "missing_count": "no count",
}
CAL_SLOTS = (("prose", "main"), ("prose", "cal_off"), ("sage", "main"), ("msfragger", "main"),
             ("msfragger", "cal1"), ("msfragger", "cal0"))  # O19 arms (SPEC 2.2 ARMS; RM:163-165)
# a triangle is "no mass calibration" (down ProSE, up MSFragger); "D" means natural entrapment elsewhere (S8b)
CAL_MARKER = {"main": "o", "cal_off": "v", "cal1": "s", "cal0": "^"}
CAL_LABEL = {"main": "default settings", "cal_off": "ProSE, no mass calibration",
             "cal1": "MSFragger, mass calibration only", "cal0": "MSFragger, no mass calibration"}
CAL_LEGEND = ("main", "cal_off", "cal0", "cal1")  # legend order of the arms
CAL_MARK = dict(ms=3.4, mew=0.5)  # the arm markers of the change rows (3.9 pt across) and their legend handles

# marks and lines (G2, G6, G7): no printed stroke below 0.5 pt, no alpha
SEPARATOR = dict(color="0.7", lw=0.5)  # between class blocks
ZERO_LINE = dict(color="black", lw=0.5)  # lead panels; thinner than the mean-lead lines
MEAN_LINE_LW = 0.9  # tuning (solid) and held-out (dashed HELDOUT_DASHES) mean-lead lines
HELDOUT_DASHES = (4, 2)  # in line widths, as matplotlib scales a dash pattern: 3.6 pt dashes, 1.8 pt gaps
ONE_PERCENT = dict(color="0.35", lw=0.7)  # the 1% line of the FDP figures, dashed ONE_PERCENT_DASHES
ONE_PERCENT_DASHES = (3.7, 1.6)  # matplotlib's '--' pattern (lines.dashed_pattern), in line widths
RUN_DOT = dict(marker="o", ms=2.6, mfc="0.1", mec="none")  # runs in the lead figures, no halo
DOT_MS = 3.0  # engine data dots
OPEN_BAR = dict(color="white", lw=0.8)  # ProSE in a non-default mode (low-memory, joint); edge ProSE blue
PANEL_LETTERS = "ABCDEFGH"  # bold; "abcdefgh" for journals that want lower case (one place)
PANEL_LETTER_WEIGHT = "bold"
LETTER_GAP_PT = 10  # a panel letter ends at least this far left of its axes, where its heading starts
SIDE_LABEL_X_PT, LABEL_GAP_PT = 12, 8.5  # right-hand labels of the mean-lead lines
GRADE_DY_PT, GRADE_PAD_PT = -5, 13  # grade letters 5 pt under the axis; x tick-label pad below them
TICK_STEPS, MAX_TICKS = (1, 2, 5, 10, 20, 50), 9  # linear lead axes: one step per figure
EDGE_CLEAR_PT = 1.0  # log time axes: a marker keeps at least this much white to the top and the bottom (clear_decades)
FDP_STEP, FDP_MIN_TOP = 0.5, 2.0  # fdp_axis
# shuffled mean +- SD per run (Fig 2, FigS4, FigS5): no marker edge, so that the dot prints 2.6 pt wide (matplotlib's
# default 1 pt edge made it 3.6 pt)
FDP_DOT = dict(fmt="o", ms=2.6, mew=0, elinewidth=0.6, capsize=0)
# legend dots without an edge: the engines (engine_handles) and the mean +- SD (errorbar_handle), 3.4 pt across. With
# matplotlib's default 1 pt edge an engine dot was 5.0 pt, larger than any dot it stands for (1.8 to 4.2 pt)
HANDLE_DOT_MS = 3.4
# engines; runs (+-0.10 for 3 runs, one step of 0.10 for 2, see fdp_half); runs of a group with > 3 runs per engine.
# Dodge 0.32, not 0.28: the gap between the runs of two engines (dodge - 2 x spread, 0.12 category) is wider than the
# step between the runs of one engine (0.10)
FDP_DODGE, FDP_SPREAD, FDP_SPREAD_WIDE = 0.32, 0.10, 0.12
# a group with an empty engine slot (FigS4: the electron-based groups, no Sage): the engines present are dodged
# FDP_DODGE (2 engines +-0.16, as FigS5), so that the two dots of one column stand closer to each other than to the
# next column; with > 3 runs per engine (PXD065289 ETciD) they take the whole category, their runs spread wider
FDP_SPARSE_DODGE, FDP_SPARSE_SPREAD = 0.54, 0.20
# a column with fewer than 3 runs per engine dodges its engines less (fdp_dodge): the same gap between the runs of two
# engines as with 3 runs (0.22 for 2 runs), and FDP_ONE_RUN_DODGE for one run each, so that the dots of one column
# stand closer to each other than to the next column
FDP_ONE_RUN_DODGE = 0.16
# FigS4 has 22 categories of about 21 pt, so its run step (FDP_SPREAD) is 2.1 pt: a 1.8 pt dot keeps the runs of one
# engine apart, with Fig 2's step, engine gap and column gap (0.10 < 0.12 < 0.16 category); a 2.6 pt dot touches
FDP_FULL_DOT = dict(FDP_DOT, ms=1.8)
# FigS4's legend dots (engines, mean +- SD): 2.6 pt, not HANDLE_DOT_MS, so that no handle is about twice its 1.8 pt dot
FDP_FULL_HANDLE_MS = 2.6
# FigS4's layers (and Fig 2's, for a run with a shuffled mean and a natural value): the SD bar under the open marks of
# its run, whose white fill breaks the bar (else a triangle on the bar forms a solid arrow; one exactly at a bar end can
# still look like an open arrowhead: index.tsv arath_marks), and the dot on top
FDP_FULL_BAR_Z, FDP_FULL_OPEN_Z, FDP_FULL_DOT_Z = 3, 3.5, 4
# Fig 2's dot (FDP_DOT, 1.3 pt radius) is wider than the diamond across its flats ((ms + mew) / 2 = 1.05 pt), unlike
# FigS4's 1.8 pt dot: a diamond less than FDP_ON_DOT_PT from its dot (measured once the layout is final) is drawn
# above the dot (FDP_ON_DOT_Z, above the dot's 4.1), so that it can still be read, and index.tsv names it (natural_on_dot)
FDP_ON_DOT_PT, FDP_ON_DOT_Z = 1.0, 4.5
# natural entrapment, an open diamond, mec = the engine colour: about 3.0 pt from tip to tip (sqrt 2 x (ms + mew)),
# so that the three runs of an engine (2.7 pt apart in Fig 2) do not cover each other
NATURAL = dict(marker="D", ms=1.6, mfc="white", mew=0.5)
# Arabidopsis entrapment (FigS4), an open triangle with the diamond's footprint (about 3 pt wide and tall)
ARATH = dict(marker="^", ms=2.2, mfc="white", mew=0.5)
# FigS9: the natural diamond stands this far right of its arm marker (slots 6.7 pt apart), not on the arm's SD bar
NATURAL_BESIDE_PT = 2.8
# the narrow (stacked) form of a missing-value label: lines closer than matplotlib's 1.2 (Fig 3 "Sage:\nout of\nmemory")
NARROW_LINESPACING = 1.0
IDEAL = dict(color="0.4", lw=0.7)  # fig_scaling: every ideal line, dashed (4, 2); the relative ideal dotted
BAND_16 = dict(color="0.92", lw=0)  # fig_scaling: the main benchmark's 16 threads, 16 / 1.12 to 16 x 1.12
MAIN_RUN_OFFSET_PT = 7  # fig_scaling: the main benchmark's run, right of its own thread count
# fig_scaling: the engine dots on their lines, 4.2 pt across (ms + mew, the edge in the line color); the legend dot
# is as wide, without an edge, so that it does not look smaller than the dots it stands for
SCALING_DOT_MS, SCALING_DOT_MEW = 3.2, 1.0
# fig_immuno: bar width (category); the published markers' centers right of the last bar and apart, in points (the
# 3.8 pt diamond is 5.4 pt wide: about 1.5 pt clear of the bar and 0.7 pt of the triangle)
IMMUNO_BAR, PUBLISHED_FIRST_PT, PUBLISHED_STEP_PT = 0.16, 4.5, 6.0
# fig_fdp_main: the datasets with natural entrapment only (no shuffled design) as open diamonds; False leaves them out
# (then index.tsv names them: natural_only_left_out, and left_out with the reason 'natural entrapment only')
FDP_MAIN_NATURAL_ONLY = True

# every visible word of a legend, axis label or heading that is not a name of design.py (G3); American English
VOCAB = {
    "run": "run",
    "shuffled": "shuffled entrapment, mean ± SD", "natural": "natural entrapment", "arath": "Arabidopsis entrapment",
    "one_percent": "1% FDR threshold", "sage_not_run": "Sage: not run", "sage_not_run_narrow": "Sage:\nnot run",
    "ids": "{} at 1% FDR",  # PSMs, peptides
    "ids_thousands": "{} at 1% FDR (thousands)",  # fig_ids_panels: PSMs, peptides
    "run_pooled": "run (class I: pooled sample)",  # fig_ids_panels: a class I dot is one sample of pooled runs
    "lead_over": "{} lead over\n{} (%)",  # 100 x (ratio - 1); always a lead, never a raw ratio
    "lead_over_long": "{}\nlead over\n{} (%)",  # the same where two lines are taller than the panel (fit_ylabel)
    "lead_level_over": "{} lead in {} over\n{} (%)",  # fig_overtuning: ProSE, PSMs or peptides, comparator
    "lead_level_over_long": "{} lead\nin {} over\n{} (%)",  # the same on three lines (fit_ylabel)
    "level": "{} level",  # PSM, peptide
    # the figures call the tuning datasets development datasets: ProSE was developed using them (owner, 2026-11-28)
    "tuning_dataset": "development dataset", "heldout_dataset": "held-out dataset",
    "mean_tuning": "mean lead, development", "mean_heldout": "mean lead, held-out",
    "side_tuning": "development", "side_heldout": "held-out", "grade": "grade",
    "arrangement": {"per_file": "per-file rescoring", "joint": "joint rescoring"},
    "low_memory_std": "ProSE, standard mode", "low_memory_lm": "ProSE, low-memory mode",
    "ideal": "ideal scaling", "ideal_relative": "ideal from the smallest completed thread count",
    "main_threads": "16 threads (main benchmark setting)", "main_run": "same run in the main benchmark",
    "lower_bound": "time limit reached: lower bound", "threads": "threads",
    "batch_ratio": "batch time /\nseparate-file time", "batch_time": "batch time per file (min)",
    "memory": "peak memory (GiB)", "missing_scaling": "no value (not run, over limit, failed)",
    "time_per_file": "time per file (min)", "time_per_sample": "time per sample (min)", "time": "time (min)",
    "speedup": "speedup", "efficiency": "efficiency", "fdp": "entrapment FDP (%)",
    "fdp_level": "{} entrapment\nFDP (%)",  # PSM, peptide
    "out_of_memory_cap": "out of memory ({} GiB cap)", "published": "{} (published)",
    "change_level": "change in {} (%)",  # PSMs, peptides: 100 x (arm / default - 1) of the same engine (G17)
    "gmean_runs": "geometric mean over runs", "shuffled_mean": "shuffled entrapment (mean)",
    "not_shared": "not shared", "not_counted_all": "not counted by all three engines",
    "not_counted_all_narrow": "not counted by\nall three engines", "no_sample": "no sample in the table",
    "not_counted_all_panel": "not counted\nby all three\nengines",  # the empty panel of fig_ids_panels
    "engine_out_of_memory": "{}: out of memory", "engine_out_of_memory_narrow": "{}:\nout of\nmemory",
    "matched_x": "ProSE lead at q ≤ 0.01 (%), entrapment search",
    "matched_y": "ProSE lead at matched 1% FDP (%),\nentrapment search",
}
# code names that must not be visible (G3; test C4 runs it over the drawn texts). "main" is banned as an arm name only
BANNED = re.compile(r"_|\$|per_file|low_memory|calibrate_mass|gmean|\bR3\b|\bB3\b|\btd\b|\barm\b"
                    r"|(?<!\()\bmain\b(?!\)| benchmark)|\bs[1-3]\b|\bfrac\d+|reali[sz]|colour|speed-up|engine node"
                    r"|scaling node|workstation|\bRSS\b")


class Skip(Exception):
    """The figure is not drawn: its table is absent or holds nothing for it (INFO)."""


class FigureError(Exception):
    """One or more figures raised; draw() raises this at the end, chained to the first error."""


# ---------------------------------------------------------------- entry point
def draw(tables_dir, figures_dir, report):
    """Draws every figure of SPEC 3.7 from tables_dir into figures_dir as fig_<name>.pdf and .png, with the paper
    copies of PAPER_FIGURES and figures/index.tsv; one INFO line per figure drawn or skipped, one FAIL line per figure
    that raised (then FigureError at the end); when a figure was drawn, the font line (INFO, and a WARN when the font
    is neither Arial nor Helvetica) and the index line."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    os.makedirs(figures_dir, exist_ok=True)
    font_files, font_problem = add_fonts()  # before rc_params, which chooses the font
    tabs = Tables(tables_dir)
    failed, index = [], []
    with plt.rc_context(rc_params()):
        font, font_file = font_in_use()
        for name, func, args in FIGURES:
            tabs.used = []
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
                index.append(index_row(fig, name, tabs.used, copy_paper(figures_dir, name)))
            except Exception as err:  # e.g. a full disk: reported like a drawing error
                report.check("FAIL", "FIGURES", f"{name}: not saved: {err.__class__.__name__}: {err}")
                failed.append((name, err))
                continue
            finally:
                plt.close(fig)
            report.check("INFO", "FIGURES", f"{name}: drawn ({info})")
    removed = remove_stale_copies(figures_dir, {row[1] for row in index})
    write_index(figures_dir, index, font_files)
    if index:
        kind = "TrueType" if font_file.lower().endswith((".ttf", ".ttc")) else "not TrueType"
        report.check("INFO", "FIGURES", f"font: {font} ({font_file}, {kind}, embedded)")
        if font not in PREFERRED_FONTS:
            report.check("WARN", "FIGURES", f"font: {font}, not Arial or Helvetica; set {FONT_DIR_ENV} to a folder "
                                            f"with {', '.join(FONT_FILES[:2])}")
        report.check("INFO", "FIGURES", f"index.tsv: {len(index)} figure(s), "
                                        + ", ".join(f"{n} {f}" for n, f in sorted(index_counts(index).items()))
                                        + (f"; stale copies removed: {T.list_text(removed)}" if removed else ""))
    if font_problem:
        report.check("WARN", "FIGURES", font_problem)
    if failed:
        raise FigureError(f"{len(failed)} figure(s) failed: {T.list_text(n for n, _ in failed)}") from failed[0][1]


def rc_params():
    """7 pt everywhere, TrueType fonts in the PDF (pdf.fonttype 42), 300 dpi PNG (SPEC 1 "Output folder", 3); no
    mathtext ("$" prints as it is), no stroke below 0.5 pt, plain headings (panel letters are bold)."""
    return {
        "pdf.fonttype": 42, "ps.fonttype": 42, "savefig.dpi": DPI, "figure.dpi": 100,
        "font.family": "sans-serif", "font.sans-serif": [font_name()], "mathtext.default": "regular",
        "text.parse_math": False,
        "font.size": FONT_PT, "axes.titlesize": FONT_PT, "axes.labelsize": FONT_PT, "xtick.labelsize": FONT_PT,
        "ytick.labelsize": FONT_PT, "legend.fontsize": FONT_PT, "figure.titlesize": FONT_PT,
        "legend.title_fontsize": FONT_PT, "axes.titleweight": "normal", "axes.linewidth": 0.6,
        "xtick.major.width": 0.6, "ytick.major.width": 0.6,
        "xtick.minor.width": 0.5, "ytick.minor.width": 0.5, "xtick.major.size": 2.5, "ytick.major.size": 2.5,
        "xtick.minor.size": 1.5, "ytick.minor.size": 1.5, "lines.linewidth": 0.8, "lines.markersize": 3,
        "hatch.linewidth": 0.5, "patch.linewidth": 0.6, "legend.frameon": False, "legend.handlelength": HANDLE_LENGTH,
        "legend.columnspacing": 1.2, "legend.borderaxespad": 0.2, "axes.spines.top": False,
        "axes.spines.right": False, "axes.titlelocation": "left", "axes.unicode_minus": True,
        "errorbar.capsize": 0,
    }


def add_fonts():
    """Adds the FONT_FILES found in the folder $SUMMARIZE_FONT_DIR (names compared case-insensitively, no other
    file) to matplotlib's font list for this process; nothing is installed and no cache is touched. Returns (the
    paths added or already added, a WARN text or None): a variable that names no folder gives the WARN."""
    folder = os.environ.get(FONT_DIR_ENV, "").strip()
    if not folder:
        return [], None
    if not os.path.isdir(folder):
        return [], f"{FONT_DIR_ENV} is not a folder: {folder}"
    from matplotlib import font_manager
    known = {os.path.normcase(f.fname) for f in font_manager.fontManager.ttflist}
    paths = []
    for fn in sorted(os.listdir(folder)):
        if fn.lower() not in FONT_FILES:
            continue
        path = os.path.join(folder, fn)
        if os.path.normcase(path) not in known:
            font_manager.fontManager.addfont(path)
        paths.append(path)
    return paths, None if paths else f"{FONT_DIR_ENV}: no {', '.join(FONT_FILES)} in {folder}"


def font_name():
    """The first installed font of FONTS (Arial where present; Arimo has its metrics), so matplotlib never warns."""
    from matplotlib import font_manager
    names = {f.name for f in font_manager.fontManager.ttflist}
    for name in FONTS:
        if name in names:
            return name
    return "DejaVu Sans"


def font_in_use():
    """(family name, file) of the regular text font of the current rcParams."""
    import matplotlib
    from matplotlib import font_manager
    name = matplotlib.rcParams["font.sans-serif"][0]
    path = font_manager.findfont(font_manager.FontProperties(family=name), fallback_to_default=True)
    return font_manager.get_font(path).family_name, path


def settle(fig, tol_pt=0.25, most=8):
    """Draws the figure once, or, when an axes has a fixed aspect, until no axes moves by more than tol_pt between
    two draws (at most `most` draws). Constrained layout shrinks such an axes after it has placed the labels, so each
    draw moves the axes and their labels a little; a letter placed after one draw would not sit at the column edge
    of the saved figure."""
    fig.canvas.draw()
    if all(ax.get_aspect() == "auto" and ax.get_box_aspect() is None for ax in fig.axes):
        return
    tol = tol_pt * fig.dpi / 72.0
    last = [ax.bbox.extents.copy() for ax in fig.axes]
    for _ in range(most - 1):
        fig.canvas.draw()
        now = [ax.bbox.extents.copy() for ax in fig.axes]
        if max(abs(a - b).max() for a, b in zip(now, last)) <= tol:
            return
        last = now


def finish(fig):
    """The steps that need the final layout, before a figure is saved (save() calls it; a test calls it before it
    measures the drawn texts): the y labels of stacked panels aligned; one draw, or more until the layout has
    settled (settle()); the steps registered with later(fig, step) (block names fitted to their blocks, right-hand
    labels pushed apart); one more draw; the panel letters placed at the left edge of their column."""
    fig.align_ylabels()
    settle(fig)
    steps = getattr(fig, "finish_steps", [])
    for step in steps:
        step()
    if steps:
        fig.canvas.draw()
    place_letters(fig)


def later(fig, step):
    """Registers step() to run in finish(), once the layout is known."""
    if not hasattr(fig, "finish_steps"):
        fig.finish_steps = []
    fig.finish_steps.append(step)


def save(fig, figures_dir, name):
    """fig_<name>.pdf and .png, each written to a temporary file and moved into place (atomic, as the tables), after
    finish()."""
    finish(fig)
    for ext in ("pdf", "png"):
        path = os.path.join(figures_dir, f"{name}.{ext}")
        tmp = path + ".tmp"
        meta = {"CreationDate": None} if ext == "pdf" else {"Software": None}
        fig.savefig(tmp, format=ext, dpi=DPI, metadata=meta)
        os.replace(tmp, path)


def remove_stale(figures_dir, name):
    """Removes fig_<name>.pdf/.png of an earlier build when this build skips the figure; returns what it removed. Its
    paper copy is removed by remove_stale_copies."""
    removed = []
    for ext in ("pdf", "png"):
        path = os.path.join(figures_dir, f"{name}.{ext}")
        if os.path.exists(path):
            os.remove(path)
            removed.append(os.path.basename(path))
    return ", ".join(removed)


# ---------------------------------------------------------------- paper copies and index.tsv (O1)
PAPER_COPY = re.compile(r"^Fig(S?)\d+_[A-Za-z0-9_]+\.(pdf|png)(\.tmp)?$")  # the names copy_paper writes
INDEX_COLUMNS = ("number", "file", "code_name", "width_in", "height_in", "tables", "caption_keys", "facts")


def paper_name(name):
    """(folder, number, file stem) of a code name in PAPER_FIGURES, or None."""
    entry = PAPER_FIGURES.get(name)
    if entry is None:
        return None
    folder, stem = entry
    return folder, stem.split("_", 1)[0], stem


def copy_paper(figures_dir, name):
    """Copies fig_<name>.pdf/.png to figures/<folder>/<FigN_name>.pdf/.png (tmp + os.replace); returns the relative
    path of the copy without extension, or '' for a figure outside PAPER_FIGURES."""
    import shutil
    entry = paper_name(name)
    if entry is None:
        return ""
    folder, _, stem = entry
    os.makedirs(os.path.join(figures_dir, folder), exist_ok=True)
    for ext in ("pdf", "png"):
        dst = os.path.join(figures_dir, folder, f"{stem}.{ext}")
        shutil.copyfile(os.path.join(figures_dir, f"{name}.{ext}"), dst + ".tmp")
        os.replace(dst + ".tmp", dst)
    return f"{folder}/{stem}"


def remove_stale_copies(figures_dir, written):
    """Removes every paper copy in figures/main and figures/supplement that this build did not write (a skipped or
    failed figure, or a number changed in PAPER_FIGURES), and an emptied folder; returns the names removed."""
    removed = []
    for folder in sorted({f for f, _ in PAPER_FIGURES.values()}):
        path = os.path.join(figures_dir, folder)
        if not os.path.isdir(path):
            continue
        for fn in sorted(os.listdir(path)):
            stem = f"{folder}/{fn.split('.', 1)[0]}"
            if PAPER_COPY.match(fn) and (fn.endswith(".tmp") or stem not in written):
                os.remove(os.path.join(path, fn))
                removed.append(f"{folder}/{fn}")
        if not os.listdir(path):
            os.rmdir(path)
    return removed


def index_row(fig, name, used, copy):
    """One row of index.tsv: number, file, code name, size, the tables read, the caption items and the facts."""
    entry = paper_name(name)
    w, h = fig.get_size_inches()
    facts = getattr(fig, "facts", {})
    return (entry[1] if entry else "-", copy or name, name, f"{w:.2f}", f"{h:.2f}",
            ",".join(dict.fromkeys(used)) or "-", CAPTION_KEYS.get(name, "-"),
            "; ".join(f"{k}={v}" for k, v in facts.items()) or "-")


def index_counts(index):
    out = {}
    for row in index:
        folder = row[1].split("/", 1)[0] if "/" in row[1] else "other"
        out[folder] = out.get(folder, 0) + 1
    return out


def write_index(figures_dir, index, font_files):
    """figures/index.tsv (tmp + os.replace), the drawn figures in PAPER_FIGURES order, with a '#' note naming the
    font files added from $SUMMARIZE_FONT_DIR; removed when no figure was drawn."""
    path = os.path.join(figures_dir, "index.tsv")
    if not index:
        if os.path.exists(path):
            os.remove(path)
        return
    order = {n: i for i, n in enumerate(PAPER_FIGURES)}
    rows = sorted(index, key=lambda r: order.get(r[2], len(order)))
    note = ("# one row per drawn figure; caption_keys are the must-say items of FIGURES_CAMERA_READY.md; facts come "
            "from the tables the figure read; font files: " + (", ".join(font_files) or "none added") + "\n")
    text = note + "\t".join(INDEX_COLUMNS) + "\n" + "".join("\t".join(r) + "\n" for r in rows)
    with open(path + ".tmp", "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    os.replace(path + ".tmp", path)


# ---------------------------------------------------------------- reading the written tables
class Tables:
    """The written tables/*.tsv, each read once with tables.read_table ('#' note lines skipped)."""

    def __init__(self, folder):
        self.folder = folder
        self.cache = {}
        self.used = []  # the tables present that the current figure read (index.tsv); draw() resets it

    def read(self, name):
        """(columns, rows) of tables/<name>.tsv, or None when the file is absent."""
        if name not in self.cache:
            path = os.path.join(self.folder, name + ".tsv")
            self.cache[name] = T.read_table(path) if os.path.exists(path) else None
        if self.cache[name] is not None:
            self.used.append(name)
        return self.cache[name]

    def columns(self, name):
        got = self.read(name)
        return got[0] if got else []

    def notes(self, name):
        """The '#' header note lines of tables/<name>.tsv (without the '#'), [] when the file is absent."""
        path = os.path.join(self.folder, name + ".tsv")
        if not os.path.exists(path):
            return []
        with open(path, encoding="utf-8", newline="") as f:
            return [x[1:].strip() for x in f.read().split("\n") if x.startswith("#")]

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


def machine_facts(tabs, role="engine"):
    """index.tsv facts of the machine with the given role in O18_machines (else its first machine): label, cpus,
    cpu_model and ram_gib, for the caption (threads and CPUs are never printed in a figure); NA without the table."""
    nodes = {}
    for r in tabs.optional("O18_machines", ("node", "section", "item", "value")):
        if r["section"] == "summary":
            nodes.setdefault(r["node"], {})[r["item"]] = r["value"]
    pick = [n for n, s in nodes.items() if s.get("role") == role] or list(nodes)[:1]
    s = nodes[pick[0]] if pick else {}
    return {"machine": pick[0] if pick else "NA", "cpus": s.get("cpus", "NA"), "cpu_model": s.get("cpu_model", "NA"),
            "ram_gib": s.get("ram_gib", "NA"), "hypervisor": s.get("hypervisor", "NA")}


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
    ('failed_memory stage all repetition 0 exit 137' -> 'out of memory', 'sage:zero' -> 'zero count'). With engine,
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


def fdp_half(n):
    """The half spread of n runs of one engine in an FDP figure: +-FDP_SPREAD for 3 or more runs, one step of
    FDP_SPREAD for 2 (so that the gap to the next engine stays wider than the step between runs)."""
    return FDP_SPREAD * (n - 1) / 2 if n < 3 else FDP_SPREAD


def fdp_dodge(most):
    """The engine dodge of an FDP column (Fig 2, FigS4) whose engines have at most `most` runs: FDP_DODGE for 3 runs
    or more; with fewer runs the gap between the runs of two engines of a 3-run column (FDP_DODGE - 2 x FDP_SPREAD),
    so 0.22 for 2 runs, but at least FDP_ONE_RUN_DODGE (one run per engine)."""
    if most >= 3:
        return FDP_DODGE
    return max(FDP_ONE_RUN_DODGE, FDP_DODGE - 2 * (FDP_SPREAD - fdp_half(most)))


def dodge(keys, width):
    """{key: x offset} for engines (or engine-arm slots) side by side within one category."""
    k = len(keys)
    return {e: (i - (k - 1) / 2) * width for i, e in enumerate(keys)}


def engines_in(rows, column="engine"):
    present = {r.get(column) for r in rows}
    return [e for e in D.ENGINES if e in present]


def unit_suffix(unit, group):
    """The part of a unit name that tells it apart within its group, in words ('pxd065289_frac1' in pxd065289_etcid
    -> 'fraction 1', G3); long run ids are shortened for a tick label."""
    prefix = os.path.commonprefix([unit, group])
    prefix = prefix[:prefix.rfind("_") + 1] if "_" in prefix else ""
    s = unit[len(prefix):] or unit
    m = re.fullmatch(r"frac(?:tion)?_?(\d+)", s)
    if m:
        return f"fraction {int(m.group(1))}"
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


def minus(text):
    """A number string with a true minus sign (U+2212) for each hyphen-minus (G10): every FuncFormatter and every
    number formatted into a label goes through it; the default formatter already does this."""
    return str(text).replace("-", "−")


def log_ticks(ax, axis="y"):
    """A log10 axis with plain numbers: ticks at 1, 2, 5 x 10^k over up to three decades, else at 10^k."""
    from matplotlib import ticker
    lo, hi = ax.get_ylim() if axis == "y" else ax.get_xlim()
    decades = math.log10(hi / lo) if lo > 0 and hi > lo else 1.0
    target = ax.yaxis if axis == "y" else ax.xaxis
    target.set_major_locator(ticker.LogLocator(base=10, subs=(1.0, 2.0, 5.0) if decades <= 3.01 else (1.0,)))
    target.set_minor_locator(ticker.LogLocator(base=10, subs=tuple(float(s) for s in range(2, 10))))
    target.set_major_formatter(ticker.FuncFormatter(lambda v, _: minus(f"{v:,g}")))
    target.set_minor_formatter(ticker.NullFormatter())


def decade_limits(ax, values=None):
    """A log y axis rounded out to whole decades (G10): the limits of values (else of the axes' data) -> 10^floor,
    10^ceil; once the layout is known, one decade more at an end that a marker would touch (clear_decades)."""
    vals = [v for v in (values if values is not None else ax.dataLim.intervaly) if v is not None and v > 0
            and math.isfinite(v)]
    if not vals:
        return
    lo, hi = math.floor(math.log10(min(vals))), math.ceil(math.log10(max(vals)))
    ax.set_ylim(10.0 ** lo, 10.0 ** max(hi, lo + 1))
    later(ax.figure, lambda: clear_decades(ax))


def clear_decades(ax, clear_pt=EDGE_CLEAR_PT):
    """A step of finish(): one decade more below (above) when a marker of the axes keeps less than clear_pt points of
    white to the bottom (top) of the axes, so that no dot rests on an axis (FigS6 A: a 0.0125 min dot over a 0.01
    limit). The marks of a missing value (Marks: y = 0, in axes units) do not count. The ticks follow (log_ticks), and
    the figure is drawn again for the steps after this one. True when a limit moved."""
    import numpy as np
    k = 72.0 / ax.figure.dpi  # points per pixel
    lo, hi = ax.get_ylim()
    low = high = False
    for ln in ax.lines:
        if not ln.get_visible() or ln.get_marker() in (None, "", " ", "None", "none"):
            continue
        x, y = np.asarray(ln.get_xdata(), float), np.asarray(ln.get_ydata(), float)
        inside = np.isfinite(x) & np.isfinite(y) & (y > lo) & (y < hi)
        if not inside.any():
            continue
        xy = ln.get_transform().transform(np.column_stack([x[inside], y[inside]]))
        ys = xy[(xy[:, 0] >= ax.bbox.x0) & (xy[:, 0] <= ax.bbox.x1), 1]  # a marker outside the x range is not drawn
        if not ys.size:
            continue
        radius = (ln.get_markersize() + ln.get_markeredgewidth()) / 2
        low = low or float(((ys - ax.bbox.y0) * k).min()) - radius < clear_pt
        high = high or float(((ax.bbox.y1 - ys) * k).min()) - radius < clear_pt
    if not (low or high):
        return False
    ax.set_ylim(lo / 10.0 if low else lo, hi * 10.0 if high else hi)
    log_ticks(ax)
    ax.figure.canvas.draw()
    return True


def tick_step(axes, lo_hi):
    """Linear lead axes of one figure (G10): each axes gets its data range lo_hi[i] (bars, run points, mean lines and
    0) padded 5% on each side, and all get the same step, the smallest of TICK_STEPS that gives at most MAX_TICKS
    major ticks on every panel. Returns the step."""
    from matplotlib import ticker
    limits = []
    for lo, hi in lo_hi:
        lo, hi = min(lo, 0.0), max(hi, 0.0)
        pad = 0.05 * ((hi - lo) or 1.0)
        limits.append((lo - pad, hi + pad))
    step = TICK_STEPS[-1]
    for s in TICK_STEPS:
        if all(math.floor(hi / s) - math.ceil(lo / s) + 1 <= MAX_TICKS for lo, hi in limits):
            step = s
            break
    for ax, (lo, hi) in zip(axes, limits):
        ax.set_ylim(lo, hi)
        ax.yaxis.set_major_locator(ticker.MultipleLocator(step))
    return step


def fdp_axis(ax, values):
    """One FDP axis (G11): 0 to the next multiple of FDP_STEP above the highest whisker or value (at least
    FDP_MIN_TOP), ticks every FDP_STEP printed with '{:g}' (0, 0.5, 1, ...), the y label "entrapment FDP (%)"."""
    from matplotlib import ticker
    vals = [v for v in values if v is not None and math.isfinite(v)]
    top = max(vals) if vals else 0.0
    ax.set_ylim(0.0, max(FDP_MIN_TOP, (math.floor(top / FDP_STEP + 1e-9) + 1) * FDP_STEP))
    ax.yaxis.set_major_locator(ticker.MultipleLocator(FDP_STEP))
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda v, _: minus(f"{v:g}")))
    ax.set_ylabel(VOCAB["fdp"])


def category_axis(ax, positions, labels, groups=None, rotation=40):
    """Category ticks with rotated labels and, for held-out groups, the grade letter directly under the axis (SPEC 3
    "Grade everywhere"; O5 "the grade letter under each held-out label"), with the row label "grade" at its left when
    a letter is shown (G8: the letters are no compact letter display). A panel that shares y with a panel left of it
    in the same row whose grade row is labelled (FigS2 B) has no label of its own: there it would stand in the gap
    between the panels and seem to continue the row of the left panel."""
    positions = list(positions)
    ax.set_xticks(positions)
    ax.set_xticklabels(labels, rotation=rotation, ha="right" if rotation else "center", rotation_mode="anchor")
    ax.tick_params(axis="x", length=0, pad=GRADE_PAD_PT if groups else 3)
    shown = False
    for x, g in zip(positions, groups or ()):
        grade = D.grade(g)
        if grade in ("A", "B", "C"):
            shown = True
            ax.annotate(grade, xy=(x, 0), xycoords=("data", "axes fraction"), xytext=(0, GRADE_DY_PT),
                        textcoords="offset points", ha="center", va="top")
    if shown and not labelled_left(ax):
        ax.annotate(VOCAB["grade"], xy=(0, 0), xycoords="axes fraction", xytext=(-2, GRADE_DY_PT),
                    textcoords="offset points", ha="right", va="top", color="0.35")
        ax.grade_labelled = True


def labelled_left(ax):
    """True when an axes left of ax in the same grid row shares its y axis and has a labelled grade row."""
    spec = ax.get_subplotspec()
    if spec is None:
        return False
    spec = spec.get_topmost_subplotspec()
    for other in ax.get_shared_y_axes().get_siblings(ax):
        o = other.get_subplotspec() if other is not ax and getattr(other, "grade_labelled", False) else None
        if o is None:
            continue
        o = o.get_topmost_subplotspec()
        if (o.get_gridspec() is spec.get_gridspec() and o.rowspan.start == spec.rowspan.start
                and o.colspan.start < spec.colspan.start):
            return True
    return False


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
        ax.axvline((spans[i - 1][2] + spans[i][1]) / 2, zorder=0, **SEPARATOR)
    if label:
        names = []
        for b, x0, x1 in spans:
            t = ax.annotate(BLOCK_NAME.get(b, b), xy=((x0 + x1) / 2, 1), xycoords=("data", "axes fraction"),
                            xytext=(0, 2), textcoords="offset points", ha="center", va="bottom", color="0.3")
            names.append((t, BLOCK_SHORT.get(b), x0 - 0.5, x1 + 0.5))
        later(ax.figure, lambda: fit_block_names(ax, names))
    return label and bool(spans)


def fit_block_names(ax, names):
    """G12, once the layout is known: a block name wider than its block (from half a category before its first to
    half a category after its last category, within the axes) takes its short form (names: (text, short form or
    None, x0, x1); BLOCK_SHORT); a name that would cross an end of the axes is aligned to that end."""
    renderer = ax.figure.canvas.get_renderer()
    lo, hi = ax.get_xlim()
    for t, short, x0, x1 in names:
        left = ax.transData.transform((max(x0, lo), 0))[0]
        right = ax.transData.transform((min(x1, hi), 0))[0]
        if t.get_window_extent(renderer).width > right - left and short:
            t.set_text(short)
        box = t.get_window_extent(renderer)
        if box.x1 > ax.bbox.x1:
            t.xy = (hi, 1)
            t.set_horizontalalignment("right")
        elif box.x0 < ax.bbox.x0:
            t.xy = (lo, 1)
            t.set_horizontalalignment("left")


def title(ax, text, above_blocks=False, letter=None, pad=None):
    """The heading of a panel (a few words, left; never a letter) and, with letter i, the panel letter
    PANEL_LETTERS[i] on its baseline (G4). A panel with a letter and no heading gets a blank heading, which keeps the
    room for the letter in the layout. pad: points above the axes (default 12 above block names, else 4)."""
    pad = pad if pad is not None else (12 if above_blocks else 4)
    ax.set_title(text or (" " if letter is not None else ""), loc="left", pad=pad)
    if letter is not None:
        panel_letter(ax, letter, pad)


def panel_letter(ax, i, pad=4):
    """PANEL_LETTERS[i] in bold 7 pt on the heading's baseline (pad points above the axes), out of the layout; its x is
    set by place_letters() in finish()."""
    t = ax.annotate(PANEL_LETTERS[i], xy=(0, 1), xycoords="axes fraction", xytext=(0, pad), textcoords="offset points",
                    ha="left", va="baseline", fontweight=PANEL_LETTER_WEIGHT, annotation_clip=False)
    t.set_in_layout(False)
    ax.panel_letter = t
    return t


def place_letters(fig):
    """Moves each panel letter to the left edge of its panel's column: the leftmost y label or y tick label of the
    axes in that column (G4), with its right edge at least LETTER_GAP_PT left of its own axes, where the heading
    starts (a column without y tick labels, as FigS2 B with its shared y, would else put the letter against the
    heading), and not left of the page."""
    letters = [ax for ax in fig.axes if getattr(ax, "panel_letter", None) is not None]
    if not letters:
        return
    renderer = fig.canvas.get_renderer()

    def column(ax):
        spec = ax.get_subplotspec()
        return spec.get_topmost_subplotspec().colspan.start if spec is not None else id(ax)
    left = {}
    for ax in fig.axes:
        x0 = ax.bbox.x0
        bb = ax.yaxis.get_tightbbox(renderer)
        if bb is not None and bb.width > 0:
            x0 = min(x0, bb.x0)
        left[column(ax)] = min(left.get(column(ax), x0), x0)
    gap = LETTER_GAP_PT * fig.dpi / 72.0
    for ax in letters:
        t = ax.panel_letter
        x = min(left[column(ax)], ax.bbox.x0 - t.get_window_extent(renderer).width - gap)
        t.xycoords = ("figure fraction", "axes fraction")
        t.xy = (max(x, 0.0) / fig.bbox.width, 1)


def below_ticks(ax, labels, gap_pt=3.0):
    """Moves annotations placed under the x axis (offset points, va top) to gap_pt below the lowest x tick label."""
    renderer = ax.figure.canvas.get_renderer()
    boxes = [t.get_window_extent(renderer) for t in ax.get_xticklabels() if t.get_visible() and t.get_text()]
    if not boxes:
        return
    depth = (ax.bbox.y0 - min(b.y0 for b in boxes)) * 72.0 / ax.figure.dpi
    for t in labels:
        t.xyann = (t.xyann[0], -(depth + gap_pt))


def legend_rows(fig, row1, row2=()):
    """G9: one legend row when every entry fits within the page width, else two rows: row 1 the engines (row1),
    row 2 the encodings (row2), the shorter row padded with empty entries (column-major fill); encodings that do not
    fit in one row continue in a third row (and so on), never narrower than the engines row."""
    row1, row2 = list(row1), list(row2)
    if not row1 + row2:
        return None
    renderer = fig.canvas.get_renderer()
    limit = fig.bbox.width - 2 * fig.dpi * 0.04
    leg = fig.legend(handles=row1 + row2, loc="outside upper center", ncol=len(row1 + row2))
    if leg.get_window_extent(renderer).width <= limit or not row2 or not row1:
        return leg
    tried = set()
    for k in range(1, len(row2) + 1):
        n = max(len(row1), math.ceil(len(row2) / k))
        if n in tried:
            continue
        tried.add(n)
        grid = [row1] + [row2[i:i + n] for i in range(0, len(row2), n)]
        grid = [r + [text_handle("")] * (n - len(r)) for r in grid]
        leg.remove()
        leg = fig.legend(handles=[r[c] for c in range(n) for r in grid], loc="outside upper center", ncol=n)
        if leg.get_window_extent(renderer).width <= limit:
            break
    return leg


class Marks:
    """The missing values of one axes: an x per value at the axis base and one short label per run of neighbouring
    marks with the same label (SPEC 3 "Figures": a missing value is never drawn as 0 or as an extreme value). With
    mark=False the label is drawn without the x, where an x would mislead (G15). A label may have a narrow form (the
    same words on more lines), used when the label is wider than its categories. Values added at the same x in the
    same colour share one x: a figure that spreads the runs of an engine adds their missing values at the engine's
    place in the column, so that the x marks do not merge into one blob."""

    def __init__(self, ax):
        self.ax = ax
        self.items = []
        self.narrow = {}  # label -> its narrow form
        self.spans = {}  # (label, x) -> (first, last category) that one label at x stands for

    def add(self, x, label, colour=MISSING_COLOUR, mark=True, narrow=None, span=None):
        self.items.append((x, label, colour, mark))
        if label and narrow:
            self.narrow[label] = narrow
        if label and span:
            self.spans[(label, x)] = span

    def draw(self, mode="above", gap=1.7):
        """mode 'above': one horizontal label per cluster just above the base, on an opaque white box; 'below': under
        the axis, outside the data range (SPEC O15); 'slot': one vertical label per mark, in the empty bar slot above
        it. In modes 'above' and 'below' a label wider than its categories (half a category beyond the first and the
        last one) takes its narrow form, a label that would touch a label left of it goes one line further from the
        axis (at most three lines), and a label that would cross an end of the axes is moved inside it (place_labels,
        once the layout is known)."""
        if not self.items:
            return
        from matplotlib.transforms import blended_transform_factory
        ax = self.ax
        trans = blended_transform_factory(ax.transData, ax.transAxes)
        # one x per place and colour: the runs of one engine in a column give their marks at the engine's place
        for x, colour in dict.fromkeys((round(x, 9), colour) for x, _, colour, mark in self.items if mark):
            ax.plot([x], [0.0], ls="none", marker="x", ms=4, mew=0.9, color=colour, transform=trans,
                    clip_on=False, zorder=6)
        if mode == "slot":
            for x, label, _, _ in self.items:
                if label:
                    ax.annotate(label, xy=(x, 0), xycoords=("data", "axes fraction"), xytext=(0, 5),
                                textcoords="offset points", rotation=90, ha="center", va="bottom", color="0.25",
                                zorder=7)
            return
        below = mode == "below"
        clusters = []  # [label, x0, x1, first category, last category]
        for label in sorted({it[1] for it in self.items if it[1]}):
            for x in sorted(it[0] for it in self.items if it[1] == label):
                lo, hi = self.spans.get((label, x), (x, x))
                if clusters and clusters[-1][0] == label and x - clusters[-1][2] <= gap:
                    clusters[-1][2:] = [x, min(clusters[-1][3], lo), max(clusters[-1][4], hi)]
                else:
                    clusters.append([label, x, x, lo, hi])
        clusters.sort(key=lambda c: c[1])
        labels = [ax.annotate(c[0], xy=((c[1] + c[2]) / 2, 0), xycoords=("data", "axes fraction"),
                              xytext=(0, -5 if below else 4), textcoords="offset points", ha="center",
                              va="top" if below else "bottom", color="0.25", zorder=7,
                              bbox=None if below else dict(boxstyle="square,pad=0.1", fc="white", ec="none"))
                  for c in clusters]
        spans = [(c[3] - 0.5, c[4] + 0.5) for c in clusters]
        later(ax.figure, lambda: self.place_labels(labels, below, spans))

    def place_labels(self, labels, below, spans=None, pad_pt=2.0, line_pt=8):
        """Rows and ends of the cluster labels, in reading order: a label with a narrow form that is wider than its
        span (data x, within the axes) takes that form, its lines NARROW_LINESPACING apart; each label takes the
        first line (0, 1 or 2 lines of line_pt points further from the axis) on which it keeps pad_pt points from
        every label already placed, and a label wider than the room left between the end of the axes and its center
        is shifted inside the axes."""
        renderer = self.ax.figure.canvas.get_renderer()
        pt = 72.0 / self.ax.figure.dpi  # points per pixel
        lo, hi = self.ax.bbox.x0, self.ax.bbox.x1
        xlo, xhi = sorted(self.ax.get_xlim())
        for t, (a, b) in zip(labels, spans or ()):
            short = self.narrow.get(t.get_text())
            if short:
                left, right = (self.ax.transData.transform((v, 0))[0] for v in (max(a, xlo), min(b, xhi)))
                if t.get_window_extent(renderer).width > right - left:
                    t.set_text(short)
                    t.set_linespacing(NARROW_LINESPACING)
        placed = []  # (x0, x1, line) in pixels
        for t in sorted(labels, key=lambda t: t.get_window_extent(renderer).x0):
            box = t.get_window_extent(renderer)
            dx = hi - box.x1 if box.x1 > hi else (lo - box.x0 if box.x0 < lo else 0.0)
            x0, x1 = box.x0 + dx, box.x1 + dx
            line = 0
            while line < 2 and any(n == line and a < x1 + pad_pt / pt and x0 < b + pad_pt / pt for a, b, n in placed):
                line += 1
            placed.append((x0, x1, line))
            t.xyann = (dx * pt, -(5 + line_pt * line) if below else 4 + line_pt * line)


def cap_line(ax, label=True):
    """The 200 GiB memory cap (DS:653, 1009) as a dashed line, labelled at the left end: 3 pt right of the y axis
    and 2 pt above the dashes in every panel (an offset in points, not a fraction of the panel width)."""
    ax.axhline(D.CAP_GIB, color="0.35", ls="--", lw=0.7, zorder=1)
    if label:
        from matplotlib.transforms import blended_transform_factory
        ax.annotate(f"{D.CAP_GIB} GiB cap", xy=(0, D.CAP_GIB),
                    xycoords=blended_transform_factory(ax.transAxes, ax.transData), xytext=(3, 2),
                    textcoords="offset points", ha="left", va="bottom", color="0.35")


def one_percent_line(ax):
    ax.axhline(1.0, ls=(0, ONE_PERCENT_DASHES), zorder=1, **ONE_PERCENT)


def not_run_reason(status):
    """The reason part of a not_run_by_design status cell ('not_run_by_design (no z+1 ions in Sage 0.14.7)' -> 'no
    z+1 ions in Sage 0.14.7'), for index.tsv: the caption gives it, the figure says "Sage: not run"."""
    words = (status or "").split(None, 1)
    rest = words[1].strip() if len(words) > 1 else ""
    return rest[1:-1].strip() if rest.startswith("(") and rest.endswith(")") else rest


def sage_not_run(tabs, groups, own_sage, own_not_run=()):
    """G15: the groups of a figure in which Sage was never run: O14_coverage (optional) has a Sage row of the group
    in state not_run_by_design, or the figure's own table marks the group's Sage rows so (own_not_run), and the
    figure's own table has no other Sage row of it (own_sage). Returns (the groups, index.tsv facts: the groups and
    O14's reason)."""
    o14 = {}
    for r in tabs.optional("O14_coverage", ("engine", "group", "state", "status")):
        if r["engine"] == "sage" and state_word(r["state"]) == "not_run_by_design":
            o14.setdefault(r["group"], not_run_reason(r["status"]))
    out = [g for g in groups if (g in o14 or g in own_not_run) and g not in own_sage]
    facts = {"sage_not_run": ",".join(out) or "none"}
    reasons = sorted({o14[g] for g in out if o14.get(g)})
    if reasons:
        facts["sage_not_run_reason"] = "; ".join(reasons)
    return out, facts


def engine_reasons(text):
    """The engine-prefixed reasons of a note, each once and joined by ' and ' ('dropped: ... DN05_Thyroid_classII
    sage:failed_memory; ...' -> 'Sage out of memory'); '' when there is none."""
    found = []
    for m in re.finditer(r"\b([A-Za-z]+):([a-z_]+)", text or ""):
        engine, word = m.group(1).lower(), m.group(2)
        if engine in D.ENGINE_NAME and word in REASON_LABEL:
            found.append(f"{D.ENGINE_NAME[engine]} {REASON_LABEL[word]}")
    return " and ".join(dict.fromkeys(found))


def left_out_fact(reasons):
    """The index.tsv fact of the design groups a figure leaves out, for its caption: 'group (reason), ...' in design
    order, 'none' without one. No ',' or ';' inside a reason."""
    return ", ".join(f"{g} ({why})" for g, why in sorted(reasons, key=lambda gw: D.order_key(gw[0]))) or "none"


def not_run_labels(marks, groups, positions, wanted):
    """One label "Sage: not run" without an x per run of neighbouring categories whose group is in wanted, centered
    under that run (G15); Marks.draw places it, on two lines ("Sage:", "not run") when one line is wider than the
    run (fig_batch: one electron-based category)."""
    run = []
    for g, x in list(zip(groups, positions)) + [(None, None)]:
        if g is not None and g in wanted:
            run.append(x)
            continue
        if run:
            marks.add((run[0] + run[-1]) / 2, VOCAB["sage_not_run"], mark=False, narrow=VOCAB["sage_not_run_narrow"],
                      span=(run[0], run[-1]))
            run = []


def unit_blocks(ax, items, xs, label=True):
    """x blocks of a figure with one category per unit (fig_electron, S4): a separator between the class blocks only,
    as draw_blocks (the datasets of a block are set apart by the gap of unit_positions) and, with label, the class
    block names over their units. A dataset with several units (fractions; their ticks say "fraction N") is named
    once: after its block name ("Orbitrap · PXD065289 ETciD") when it fills its block, else in a second row 9 pt
    higher. The block names fit their blocks (G12). Returns the heading pad in points: 4 without names, 12 with one
    row of names, 21 with two."""
    spans = []  # [block, first index, last index]
    for i, (g, _) in enumerate(items):
        b = D.cls(g) if D.cls(g) != "-" else block_of(g)
        if spans and spans[-1][0] == b:
            spans[-1][2] = i
        else:
            spans.append([b, i, i])
    for k in range(1, len(spans)):
        ax.axvline((xs[spans[k - 1][2]] + xs[spans[k][1]]) / 2, zorder=0, **SEPARATOR)
    if not label or not items:
        return 4
    count = {}
    for g, _ in items:
        count[g] = count.get(g, 0) + 1
    names, second = [], False
    for b, i0, i1 in spans:
        inside = list(dict.fromkeys(g for g, _ in items[i0:i1 + 1]))
        multi = [g for g in inside if count[g] > 1]
        text, short = BLOCK_NAME.get(b, b), BLOCK_SHORT.get(b)
        if len(inside) == 1 and multi:
            text, short = f"{text} · {D.display(multi[0])}", f"{short or text} · {D.display(multi[0])}"
        else:
            for g in multi:
                at = [x for (gg, _), x in zip(items, xs) if gg == g]
                ax.annotate(D.display(g), xy=((at[0] + at[-1]) / 2, 1), xycoords=("data", "axes fraction"),
                            xytext=(0, 11), textcoords="offset points", ha="center", va="bottom", color="0.3")
                second = True
        t = ax.annotate(text, xy=((xs[i0] + xs[i1]) / 2, 1), xycoords=("data", "axes fraction"), xytext=(0, 2),
                        textcoords="offset points", ha="center", va="bottom", color="0.3")
        names.append((t, short, xs[i0] - 0.5, xs[i1] + 0.5))
    later(ax.figure, lambda: fit_block_names(ax, names))
    return 21 if second else 12


def fit_ylabel(ax, alternative, pad_pt=2.0):
    """C5, once the layout is known: a y label taller than its axes plus pad_pt points takes its alternative wording
    (the same words on more, shorter lines)."""
    renderer = ax.figure.canvas.get_renderer()
    if ax.yaxis.label.get_window_extent(renderer).height > ax.bbox.height + pad_pt * ax.figure.dpi / 72.0:
        ax.set_ylabel(alternative)


def pair_names(text):
    """(numerator, denominator) of a pair or comparison cell: 'prose/msfragger' -> ('ProSE', 'MSFragger');
    'peptdeep_vs_msbooster' -> ('ProSE+PeptDeep', 'MSFragger+MSBooster')."""
    sides = comparison_sides(text)
    if sides:
        return sides[0][0], sides[1][0]
    parts = pair_title(text).split(" / ")
    return (parts[0], parts[1]) if len(parts) == 2 else (pair_title(text), "")


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
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda v, _: minus(f"{v:g}")))
    ax.set_ylim(lo, hi)


def engine_handles(engines, marker="o", line=False, ms=HANDLE_DOT_MS):
    """The engine entries of a legend (row 1 of G9): a dot in the engine color, ms points across and without an
    edge (HANDLE_DOT_MS: the size of errorbar_handle's dot), on a short line with line."""
    from matplotlib.lines import Line2D
    return [Line2D([], [], color=D.COLOUR[e], marker=marker, ls="-" if line else "none", ms=ms, mew=0,
                   label=D.ENGINE_NAME[e]) for e in engines]


def marker_handle(label, marker="o", colour="0.2", face=None, ms=4, ls="none", mew=0.8):
    from matplotlib.lines import Line2D
    return Line2D([], [], color=colour, marker=marker, ls=ls, ms=ms, mfc=colour if face is None else face,
                  mec=colour, mew=mew, label=label)


def errorbar_handle(label, colour="0.2", ms=HANDLE_DOT_MS, mew=0):
    """The legend entry of a mean +- SD mark: a dot with a short vertical bar of the SD bars' width (G9: the handle
    shows what its words name)."""
    from matplotlib.collections import LineCollection
    from matplotlib.container import ErrorbarContainer
    from matplotlib.lines import Line2D
    dot = Line2D([], [], ls="none", marker="o", ms=ms, color=colour, mfc=colour, mec=colour, mew=mew)
    bar = LineCollection([], colors=colour, linewidths=FDP_DOT["elinewidth"])
    return ErrorbarContainer((dot, (), (bar,)), has_xerr=False, has_yerr=True, label=label)


def natural_handle():
    """The legend entry of natural entrapment: the open diamond, a little larger than the drawn one (3.5 against
    3.0 pt from tip to tip, as the shuffled dot's handle against its dot)."""
    return marker_handle(VOCAB["natural"], "D", "0.2", face="white", ms=2.0, mew=NATURAL["mew"])


def arath_handle():
    """The legend entry of Arabidopsis entrapment: the open triangle, a little larger than the drawn one."""
    return marker_handle(VOCAB["arath"], "^", "0.2", face="white", ms=2.6, mew=ARATH["mew"])


def line_handle(label, ls="-", lw=MEAN_LINE_LW, colour="0.15"):
    from matplotlib.lines import Line2D
    return Line2D([], [], color=colour, ls=ls, lw=lw, label=label)


def whole_dashes(dashes, lw, length_pt=HANDLE_LENGTH * FONT_PT):
    """The line style (offset, dashes) of a legend handle length_pt points long that draws the pattern dashes (on, off,
    in line widths) of a line lw points wide as whole dashes, centered: as many dashes as fit, the rest split between
    the two ends, in a gap (whole dashes when that rest is at most one gap). With offset 0 the held-out handle (4, 2)
    at 0.9 pt would end in a 0.4 pt stub that reads as a dot (F1.2); the plotted line keeps offset 0."""
    on, off = dashes[0] * lw, dashes[1] * lw
    n = max(1, int((length_pt + off) // (on + off)))
    margin = (length_pt - n * on - (n - 1) * off) / 2
    return (((on + off - margin) % (on + off)) / lw, tuple(dashes))


def patch_handle(label, face, edge=None, hatch=None, lw=0.6):
    from matplotlib.patches import Patch
    return Patch(facecolor=face, edgecolor=edge or face, hatch=hatch, lw=lw, label=label)


def text_handle(label):
    from matplotlib.patches import Patch
    return Patch(facecolor="none", edgecolor="none", label=label)


# ---------------------------------------------------------------- O5 / O7, O20, O21: leads per dataset
def lead_panel(ax, groups, bars, points, colour, na_label="n/a"):
    """SPEC O5 layout: bar = dataset lead in % (tuning filled in colour, held-out white with an edge and hatch in
    colour; colour is the comparator colour in fig_pair_leads and LEAD_GREY in fig_overtuning, D2;
    width 0.7, edge 0.6 pt); points = run leads (RUN_DOT) with deterministic jitter +-0.15; a dataset without a value
    is labelled n/a; zero line (ZERO_LINE). Returns the values drawn, for tick_step."""
    values = [0.0]
    for x, g in enumerate(groups):
        v = bars.get(g)
        tuning = D.kind(g) == "tuning"
        if v is None:
            ax.annotate(na_label, xy=(x, 0), xytext=(0, 2), textcoords="offset points", ha="center", va="bottom",
                        color="0.25")
        else:
            ax.bar(x, v, width=0.7, color=colour if tuning else "white", edgecolor=colour,
                   hatch=None if tuning else HATCH, lw=0.6, zorder=2)
            values.append(v)
        pts = points.get(g, [])
        if pts:
            offs = spread(len(pts), 0.15)
            ax.plot([x + o for o in offs], pts, ls="none", zorder=3, **RUN_DOT)
            values += pts
    ax.axhline(0, zorder=2.5, **ZERO_LINE)
    ax.set_xlim(-0.6, len(groups) - 0.4)
    return values


def side_lines(ax, lt, lh):
    """The mean leads over the tuning (solid) and the held-out datasets (dashed HELDOUT_DASHES, (4, 2)) as lines across
    the panel (MEAN_LINE_LW), each labelled in words right of the panel (F1.1: "development +5.6%", "held-out +2.0%"),
    centered on its own line with a short leader; in finish(), two labels closer than LABEL_GAP_PT are pushed apart
    symmetrically. Returns the values drawn."""
    from matplotlib.transforms import blended_transform_factory
    trans = blended_transform_factory(ax.transAxes, ax.transData)
    labels = []
    for v, word, ls in ((lt, VOCAB["side_tuning"], "-"), (lh, VOCAB["side_heldout"], (0, HELDOUT_DASHES))):
        if v is None:
            continue
        ax.axhline(v, color="0.15", ls=ls, lw=MEAN_LINE_LW, zorder=4)
        t = ax.annotate(f"{word} {minus(format(v, '+.1f'))}%", xy=(1.0, v), xycoords=trans,
                        xytext=(SIDE_LABEL_X_PT, 0), textcoords="offset points", ha="left", va="center",
                        annotation_clip=False,
                        arrowprops=dict(arrowstyle="-", lw=0.5, color="0.15", shrinkA=0, shrinkB=1.5))
        labels.append((v, t))
    if len(labels) == 2:
        later(ax.figure, lambda: spread_side_labels(ax, labels))
    return [v for v, _ in labels]


def spread_side_labels(ax, labels):
    """Two right-hand labels whose lines are closer than LABEL_GAP_PT (in points, at the final layout) are moved
    apart symmetrically about the mean of their lines; on a tie the tuning label goes up."""
    k = 72.0 / ax.figure.dpi
    ys = [ax.transData.transform((0, v))[1] * k for v, _ in labels]
    if abs(ys[0] - ys[1]) >= LABEL_GAP_PT:
        return
    mid = (ys[0] + ys[1]) / 2
    up = 0 if ys[0] >= ys[1] else 1
    want = [0.0, 0.0]
    want[up], want[1 - up] = mid + LABEL_GAP_PT / 2, mid - LABEL_GAP_PT / 2
    for (_, t), y, w in zip(labels, ys, want):
        t.xyann = (SIDE_LABEL_X_PT, w - y)


def lead_handles(with_sides, fill=GREY, edge="0.4"):
    """F1.2: development dataset, held-out dataset, run and, with the side lines, the two mean-lead lines (no
    counts); the held-out handle shows the line's dash pattern as whole dashes (whole_dashes). fill and edge: the
    development fill and the held-out edge and hatch (the neutral GREY and 0.4 where the bars take the comparator
    colour, fig_pair_leads; LEAD_GREY for the grey bars of fig_overtuning, so the handles are the bars)."""
    hs = [patch_handle(VOCAB["tuning_dataset"], fill),
          patch_handle(VOCAB["heldout_dataset"], "white", edge, HATCH),
          marker_handle(VOCAB["run"], "o", "0.1", ms=3, mew=0)]
    if with_sides:
        hs += [line_handle(VOCAB["mean_tuning"]),
               line_handle(VOCAB["mean_heldout"], ls=whole_dashes(HELDOUT_DASHES, MEAN_LINE_LW))]
    return hs


def overtuning_points(tabs, level):
    """{comparator: {dataset: [run leads in %]}}: OT's rows if a table of them is written, else the used runs of
    O02_pairs_runs (decision runs are not shown, DS 4.6 "Datasets."; C6b checks these ratios equal OT's strings)."""
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
    """O5 (psm) / O7 (peptide), SPEC 3.5; FigS2 / FigS3 since the new Fig 1 (owner, 2026-11-28): two stacked panels,
    MSFragger then Sage, over the 17 datasets in design order; bar = dataset lead, points = run leads, the mean leads
    over the tuning (solid) and the held-out datasets (dashed) labelled in words; 7.0 x 4.5 in. The bars are neutral
    grey, not the comparator colour (D2 alternative, owner 2026-11-28: next to Fig 1, where orange is MSFragger's own
    count, an orange bar here would read as a count): LEAD_GREY filled for the development datasets, white with a
    LEAD_GREY edge and hatch for the held-out ones; the legend handles are these two bars. Independent y with one tick
    step (G10); letters A, B; headings "ProSE vs <engine>"; the level in the y label ("ProSE lead in PSMs over
    MSFragger (%)"; this revises F1.6, which left it to the caption), on three lines where two are taller than the
    panel; one legend row without counts (F1.2). index.tsv facts: n_tuning, n_heldout, L_T and L_H per comparator
    (OT's 1-decimal format, as the labels)."""
    name = f"O04_overtuning_{level}_datasets"
    ds_rows = tabs.need(name, ("dataset", "side", "value_msfragger", "lead_msfragger", "value_sage", "lead_sage"))
    sides, facts = {}, {}
    side_rows = tabs.optional(f"O04_overtuning_{level}_sides", ("comparator", "L_T", "L_H"))
    for r in side_rows:
        comp = comparator_of(r["comparator"])
        sides[comp] = (num(r["L_T"]), num(r["L_H"]))
        for key, col in (("n_tuning", "n_tuning"), ("n_heldout", "n_heldout")):
            if col in r:
                facts[f"{key}_{comp}"] = r[col]
        for key, v in (("L_T", sides[comp][0]), ("L_H", sides[comp][1])):
            facts[f"{key}_{comp}"] = "NA" if v is None else format(v, "+.1f")
    points, source = overtuning_points(tabs, level)
    groups = ordered_groups(r["dataset"] for r in ds_rows)
    fig, axs = new_figure(plt, 4.5, 2, 1, sharex=True)
    ranges = []
    for i, comp in enumerate(("msfragger", "sage")):
        ax = axs[i][0]
        bars = {}
        for r in ds_rows:
            value = num(r[f"value_{comp}"])
            bars[r["dataset"]] = first(num(r[f"lead_{comp}"]), None if value is None else 100 * (value - 1))
        values = lead_panel(ax, groups, bars, points.get(comp, {}), LEAD_GREY)
        lt, lh = sides.get(comp, (None, None))
        values += side_lines(ax, lt, lh)
        ranges.append((min(values), max(values)))
        words = ("ProSE", LEVEL_UNIT[level], D.ENGINE_NAME[comp])
        ax.set_ylabel(VOCAB["lead_level_over"].format(*words))
        later(fig, lambda ax=ax, w=words: fit_ylabel(ax, VOCAB["lead_level_over_long"].format(*w)))
        blocks = draw_blocks(ax, groups, label=(i == 0))
        title(ax, f"ProSE vs {D.ENGINE_NAME[comp]}", above_blocks=blocks, letter=i)
    step = tick_step([axs[0][0], axs[1][0]], ranges)
    dataset_axis(axs[1][0], groups)
    legend_rows(fig, lead_handles(True, fill=LEAD_GREY, edge=LEAD_GREY))
    facts.update(level=level, tick_step=f"{step:g}", run_points=source)
    fig.facts = facts
    return fig, f"2 panels, {len(groups)} x categories, run points from {source}"


def fig_pair_leads(plt, tabs, table, what):
    """O20 / O21 "as O5" (SPEC 3.4; S10): one panel per pair (O20, column pair) or comparison (O21, column comparison)
    over the datasets in design order, PSM level (as O5). Points: the used, non-decision run ratios of <table>; bars:
    lead_pct (or gmean) of <table>_datasets (calib.py). Without that table, rows of <table> without a unit (unit NA
    or '-') are read as dataset rows, and failing those the bar is the gmean of the used run ratios (display only,
    said in the INFO line). The mean leads over the tuning and the held-out datasets (lead_pct of <table>_summary,
    scopes tuning and heldout; O20 has them, O21's single scope has not) are drawn as FigS2's side lines with words.
    The bars keep the comparator colour (D2; only fig_overtuning switched to grey).
    Per panel the y label "<numerator> lead over <denominator> (%)" and the heading "<numerator> vs <denominator>";
    independent y with one tick step (G10); 7.0 x (0.9 + 1.6 n) in."""
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
    sides = {}
    for r in tabs.optional(f"{table}_summary", (key, "level", "scope", "lead_pct")):
        if r["level"] == level and r["scope"] in ("tuning", "heldout"):
            sides.setdefault(r[key], {})[r["scope"]] = num(r["lead_pct"])
    groups = ordered_groups(r["group"] for r in rows)
    fig, axs = new_figure(plt, 0.9 + 1.6 * len(pairs), len(pairs), 1, sharex=True)
    ranges, facts, with_sides = [], {"what": what, "level": level}, False
    for i, pair in enumerate(pairs):
        ax = axs[i][0]
        comp = comparator_of(pair) or "prose"
        points = {g: [100 * (v - 1) for v in vs] for g, vs in runs.get(pair, {}).items()}
        values = lead_panel(ax, groups, bars[pair], points, D.COLOUR[comp])
        lt, lh = sides.get(pair, {}).get("tuning"), sides.get(pair, {}).get("heldout")
        drawn = side_lines(ax, lt, lh)
        with_sides = with_sides or bool(drawn)
        values += drawn
        for k, v in (("L_T", lt), ("L_H", lh)):
            if pair in sides:
                facts[f"{k}_{pair}"] = "NA" if v is None else format(v, "+.1f")
        ranges.append((min(values), max(values)))
        numerator, denominator = pair_names(pair)
        ax.set_ylabel(VOCAB["lead_over"].format(numerator, denominator))
        later(fig, lambda ax=ax, n=numerator, d=denominator: fit_ylabel(ax, VOCAB["lead_over_long"].format(n, d)))
        blocks = draw_blocks(ax, groups, label=(i == 0))
        title(ax, f"{numerator} vs {denominator}", above_blocks=blocks, letter=i if len(pairs) > 1 else None)
    facts["tick_step"] = f"{tick_step([a[0] for a in axs], ranges):g}"
    dataset_axis(axs[-1][0], groups)
    legend_rows(fig, lead_handles(with_sides))
    fig.facts = facts
    source = f"bars from {table}_datasets" if not computed else f"bars from run rows for {', '.join(computed)}"
    return fig, (f"{len(pairs)} panels, {len(groups)} x categories; {source}"
                 + ("; mean leads from " + f"{table}_summary" if with_sides else ""))


# ---------------------------------------------------------------- O3: counts of the three engines
IDS_RIGHT_IN, IDS_AXES_IN = 1.5, 6.2  # fig_ids_counts: width of the class I panel (its one-line heading); both panels


def fig_ids_counts(plt, tabs, level):
    """O3 figure (SPEC 3.1; OPEN Q6, Q54; S2, D9): per dataset the geometric mean of the accepted counts over its R3
    units as a short line (0.22 category, 1.2 pt) in the engine colour, engines dodged, the R3 units as grey dots
    (2.2 pt); no bars, because a bar on a log axis has no meaningful length. A: the tryptic datasets, B:
    immunopeptidomics class I, with one shared log y axis (B's tick labels hidden). gmean(P)/gmean(C) = gmean(P/C)
    over the same units. A dataset without an R3 unit is a label at the axis base without an x (G15). index.tsv
    names the design groups without a category and why (left_out: the engine reasons of O03_three_datasets' note,
    else "Sage not run" from O14, else "not counted by all three engines"). 7.0 x 3.3 in."""
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
    panels = [(left, "tryptic datasets")] + ([(right, f"{BLOCK_NAME['immuno']}, class I")] if right else [])
    ratios = [max(len(p[0]), 1) + 1.5 for p in panels]
    if len(ratios) > 1:  # the class I panel at least IDS_RIGHT_IN wide, so that its heading fits on one line
        ratios[1] = max(ratios[1], ratios[0] * IDS_RIGHT_IN / (IDS_AXES_IN - IDS_RIGHT_IN))
    fig, axs = new_figure(plt, 3.3, 1, len(panels), sharey=True, gridspec_kw={"width_ratios": ratios})
    axs = axs[0]
    off = dodge(D.ENGINES, 0.27)
    every = [v for vals in units.values() for row in vals for v in row]
    for i, (groups, label) in enumerate(panels):
        ax = axs[i]
        marks = Marks(ax)
        for x, g in enumerate(groups):
            vals = units.get(g)
            if not vals:  # a label at the base, without an x: on a log axis an x would read as the lowest count
                marks.add(x, VOCAB["not_counted_all"], mark=False, narrow=VOCAB["not_counted_all_narrow"])
                continue
            for j, e in enumerate(D.ENGINES):
                col = [v[j] for v in vals]
                gm = math.exp(math.fsum(math.log(v) for v in col) / len(col))
                xe = x + off[e]
                ax.plot([xe + o for o in spread(len(col), 0.07)], col, ls="none", marker="o", ms=2.2, mfc="0.35",
                        mec="none", zorder=3)
                ax.plot([xe - 0.11, xe + 0.11], [gm, gm], color=D.COLOUR[e], lw=1.2, solid_capstyle="butt", zorder=4)
        ax.set_yscale("log")
        marks.draw()
        draw_blocks(ax, groups, label=(i == 0))
        dataset_axis(ax, groups)
        title(ax, label, above_blocks=True, letter=i if len(panels) > 1 else None)  # both headings on one line
        if i == 0:
            ax.set_ylabel(VOCAB["ids"].format(LEVEL_UNIT[level]))
    if every:  # the data range, a little padded (no bar needs a base)
        axs[0].set_ylim(min(every) / 1.3, max(every) * 1.3)
    log_ticks(axs[0])
    legend_rows(fig, [line_handle(D.ENGINE_NAME[e], lw=1.2, colour=D.COLOUR[e]) for e in D.ENGINES],
                [line_handle(VOCAB["gmean_runs"], lw=1.2, colour="0.2"),
                 marker_handle(VOCAB["run"], "o", "0.35", ms=2.2, mew=0)])
    fig.facts = {"level": level, "datasets": sum(1 for p, _ in panels for g in p if g in units),
                 "units": sum(len(units.get(g, [])) for p, _ in panels for g in p)}
    if right:  # the caption says that the points of B are samples, not runs
        fig.facts["points_B"] = "samples (pooled files of one sample), not runs"
    if paper:  # S2c: the design groups without a category (class II, the electron-based datasets) and why
        shown = set(left) | set(right)
        gone = [g for g in D.ALL_GROUPS if g not in shown]
        notes = {r["group"]: r["note"] for r in tabs.optional("O03_three_datasets", ("level", "group", "note"))
                 if r["level"] == level}
        not_run, _ = sage_not_run(tabs, gone, set())
        sage = f"{D.ENGINE_NAME['sage']} {REASON_LABEL['not_run_by_design']}"
        fig.facts["left_out"] = left_out_fact(
            (g, engine_reasons(notes.get(g)) or (sage if g in not_run else VOCAB["not_counted_all"])) for g in gone)
    return fig, f"{len(panels)} panels, {sum(len(p[0]) for p in panels)} x categories"


# ---------------------------------------------------------------- O3: Fig 1 and FigS1, one small panel per dataset
# fig_ids_panels, in inches: page margins (left: room for the y label), room for a panel's tick labels left of its axes,
# the space between one panel's axes and the next panel's tick labels, the extra space between blocks; from the top of
# a row: the block name, its rule (rule_in from the row top), the panel titles (up to three lines), the axes, the room
# under them; the space between the rows and under row 2. Row 1 (IDS_ROW1_BLOCKS) sets the panel width.
PANELS = dict(left=0.30, right=0.08, ticks=0.18, pad=0.04, gap=0.13, top=0.04, block=0.14, rule=0.12, title=0.34,
              axes=0.80, below=0.05, row_gap=0.10, bottom=0.02, ylabel_x=0.03)
PANELS_HEIGHT = round(PANELS["top"] + 2 * (PANELS["block"] + PANELS["title"] + PANELS["axes"] + PANELS["below"])
                      + PANELS["row_gap"] + PANELS["bottom"], 6)  # 2.82 in
IDS_ROW1_BLOCKS = ("IT", "OT")  # row 1: ion trap and Orbitrap; row 2: Astral, timsTOF, immunopeptidomics, the legend
# bar width (category), half spread of the run dots (category; 2.3 pt apart at 3 runs, as the 2.6 pt RUN_DOT nearly
# touch), headroom over the highest bar or dot, legend handle length (font sizes: 8.4 pt, so the side legend fits)
PANELS_BAR, PANELS_SPREAD, PANELS_HEADROOM, PANELS_HANDLE_LENGTH = 0.72, 0.27, 1.12, 1.2
PANELS_TICK_CLEAR_PT = 5.0  # the highest y tick at least this far under the top of its axes (ids_panel)
# panel titles: the display name (design.DISPLAY_NAME) broken into lines of at most about 12 characters, so that the
# titles of neighbouring panels do not touch; the class I panels name the HLA class (a test checks that the words are
# the display name's)
PANEL_TITLES = {
    "lumos_tmt": "Lumos CID\nTMT6", "ups1_control": "UPS1\ncontrol", "pxd042233_lumos_cid": "PXD042233\nLumos CID",
    "pxd011695_HCD": "PXD011695\nHCD", "lumos_lfq": "Lumos\nHCD LFQ", "eclipse_tmtpro": "Exploris 480\nTMTpro",
    "hela_qe_hf": "HeLa Q\nExactive HF", "hela_exploris480": "HeLa\nExploris 480", "astral_s1": "Astral\nset S1",
    "astral_250pg": "Astral\n250 pg", "tims_plasma": "timsTOF HT\nplasma", "ultra2_s2": "timsTOF\nUltra 2\nset S2",
    "ultra2_hye": "timsTOF\nUltra 2\nHYE", "pxd058436_classI": "PXD058436\nHLA class I",
    "pxd019643_classI": "PXD019643\nHLA class I",
}


def panel_title(group):
    """The title of a dataset's panel in fig_ids_panels: PANEL_TITLES, else the display name."""
    return PANEL_TITLES.get(group, D.display(group))


def note_units(note):
    """[(unit, reason)] of the units an O03_three_datasets note excludes ('dropped: no run in the set (DS:897); u1
    sage:failed_memory; u2 ...' -> [('u1', 'Sage out of memory'), ...]); the reason in words, without ',' or ';'."""
    out = []
    for part in (note or "").split(";"):
        part = part.strip()
        if not part or part.startswith("dropped:") or part in ("decision only", "no unit"):
            continue
        unit, _, why = part.partition(" ")
        label = engine_reasons(why) or reason_label(why)
        out.append((unit, label if label != "n/a" else (why.replace("_", " ").replace(",", " ") or "not counted")))
    return out


def ids_panel(ax, vals):
    """One dataset's panel of fig_ids_panels: per engine a bar (geometric mean over the units, in thousands) in the
    engine colour and the units as RUN_DOT dots spread +-PANELS_SPREAD; its own linear y from 0 (G10: about 4 ticks of
    1, 2, 2.5 or 5 x 10^k)."""
    from matplotlib import ticker
    top = 0.0
    for j, e in enumerate(D.ENGINES):
        col = [v[j] / 1000.0 for v in vals]
        gm = math.exp(math.fsum(math.log(v) for v in col) / len(col))
        ax.bar(j, gm, width=PANELS_BAR, color=D.COLOUR[e], lw=0, zorder=2)
        ax.plot([j + o for o in spread(len(col), PANELS_SPREAD)], col, ls="none", zorder=3, **RUN_DOT)
        top = max([top, gm] + col)
    hi = top * PANELS_HEADROOM
    ticks = [v for v in ticker.MaxNLocator(nbins=4, steps=[1, 2, 2.5, 5, 10], min_n_ticks=3).tick_values(0.0, hi)
             if 0.0 <= v <= hi * (1 + 1e-9)]
    # the highest tick at least PANELS_TICK_CLEAR_PT under the top of the axes, so that its label (3.5 pt above the
    # tick) stays under a title wider than the axes
    clear = PANELS_TICK_CLEAR_PT / (PANELS["axes"] * 72.0)
    hi = max(hi, ticks[-1] / (1.0 - clear))
    ax.set_ylim(0.0, hi)
    ax.yaxis.set_major_locator(ticker.FixedLocator(ticks))
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda v, _: minus(f"{v:,g}")))


def fig_ids_panels(plt, tabs, level):
    """Fig 1 (psm) and FigS1 (peptide), owner 2026-11-28: the accepted identifications of the three engines as grouped
    bars, one small panel per dataset. Panels: the 17 tryptic datasets of design.FIGURE_ORDER and the class I groups
    of design.IMMUNO_ORDER, in analyzer blocks (ion trap and Orbitrap in row 1; Astral, timsTOF and
    immunopeptidomics in row 2), each block named over a thin rule. A bar is the geometric mean over the dataset's R3
    units (O03_three_runs: the runs all three engines counted, decision runs not among them), in thousands, in the
    engine colour; the dots are the units (runs; class I: samples of pooled replicate runs). Each panel has its own
    linear y from 0. The figure names no role: no development, held-out, grade or decision word anywhere.
    A dataset without an R3 unit is an empty panel with "not counted by all three engines" (G15, no x) and is named in
    left_out; nothing drops out silently. Exceptions, recorded in README: no panel letters (G4: a faceted figure of
    19 like panels; the titles name them), and the legend stands in the free room right of row 2, not on top (G9).
    7.0 x PANELS_HEIGHT in. index.tsv facts: level, datasets (with bars), units, units_per_dataset, points_class_I,
    empty_panels, dropped_runs (units of a drawn dataset outside R3, with the reason) and left_out (the design groups
    without bars: the electron-based groups, class II, an empty panel; the reason as fig_ids_counts)."""
    from matplotlib.lines import Line2D
    rows = tabs.need("O03_three_runs", ("group", "unit", "level") + D.ENGINES)
    rows = [r for r in rows if r["level"] == level]
    if not rows:
        raise Skip(f"O03_three_runs has no {level} row")
    if not any(D.kind(r["group"]) in ("tuning", "heldout", "immuno") for r in rows):
        raise Skip("O03_three_runs has no design group (fig_ids_counts draws the groups of --design none)")
    units, dropped = {}, {}
    for r in rows:
        vals = [num(r[e]) for e in D.ENGINES]
        if all(v is not None and v > 0 for v in vals):  # R3: all three counted with accepted > 0
            units.setdefault(r["group"], []).append(vals)
        else:
            lacking = " and ".join(D.ENGINE_NAME[e] for e, v in zip(D.ENGINES, vals) if v is None or v <= 0)
            dropped[r["unit"]] = (r["group"], f"no count of {lacking}")
    shown = list(D.FIGURE_ORDER) + [g for g in D.IMMUNO_ORDER if g.endswith("classI")]
    notes = {r["group"]: r["note"] for r in tabs.optional("O03_three_datasets", ("level", "group", "note"))
             if r["level"] == level}
    for g in shown:
        for unit, why in note_units(notes.get(g)):
            dropped.setdefault(unit, (g, why))
    blocks = []  # [block, [groups]] in design order
    for g in shown:
        b = block_of(g)
        if blocks and blocks[-1][0] == b:
            blocks[-1][1].append(g)
        else:
            blocks.append([b, [g]])
    row1 = [b for b in blocks if b[0] in IDS_ROW1_BLOCKS]
    row2 = [b for b in blocks if b[0] not in IDS_ROW1_BLOCKS]
    P, height = PANELS, PANELS_HEIGHT
    slot = (WIDTH - P["left"] - P["right"] - P["gap"] * (len(row1) - 1)) / sum(len(gs) for _, gs in row1)
    aw = slot - P["ticks"] - P["pad"]
    row_h = P["block"] + P["title"] + P["axes"] + P["below"]
    fig = plt.figure(figsize=(WIDTH, height))  # fixed axes: every panel the same size (no constrained layout)

    def fx(inch):
        return inch / WIDTH

    def fy(inch_from_top):
        return 1.0 - inch_from_top / height
    empty, x, ax_top = [], 0.0, 0.0
    for r, row in enumerate((row1, row2)):
        y_top = P["top"] + r * (row_h + P["row_gap"])
        ax_top = y_top + P["block"] + P["title"]
        x = P["left"]
        for b, groups in row:
            x_first = x + P["ticks"]
            for g in groups:
                ax = fig.add_axes([fx(x + P["ticks"]), fy(ax_top + P["axes"]), fx(aw), P["axes"] / height])
                ax.set_title(panel_title(g), loc="center", pad=2, linespacing=NARROW_LINESPACING)
                ax.set_xlim(-0.6, len(D.ENGINES) - 0.4)
                ax.set_xticks([])
                if units.get(g):
                    ids_panel(ax, units[g])
                else:  # no scale without counts; the label stands at the base, without an x (G15)
                    empty.append(g)
                    ax.set_yticks([])
                    ax.spines["left"].set_visible(False)  # the label is wider than the axes: no line through it
                    ax.annotate(VOCAB["not_counted_all_panel"], xy=(0.5, 0), xycoords="axes fraction", xytext=(0, 4),
                                textcoords="offset points", ha="center", va="bottom", color="0.25",
                                linespacing=NARROW_LINESPACING)
                x += slot
            x_last = x - P["pad"]  # the right edge of the block's last axes
            fig.text(fx((x_first + x_last) / 2), fy(y_top), BLOCK_NAME.get(b, b), ha="center", va="top", color="0.3")
            fig.add_artist(Line2D([fx(x_first), fx(x_last)], [fy(y_top + P["rule"])] * 2, **SEPARATOR))
            x += P["gap"]
    handles = [patch_handle(D.ENGINE_NAME[e], D.COLOUR[e], lw=0) for e in D.ENGINES]
    handles += [patch_handle(VOCAB["gmean_runs"], "white", "0.2"),
                marker_handle(VOCAB["run_pooled"], "o", RUN_DOT["mfc"], ms=RUN_DOT["ms"], mew=0)]
    fig.legend(handles=handles, loc="center left", bbox_to_anchor=(fx(x), fy(ax_top + P["axes"] / 2)),
               handlelength=PANELS_HANDLE_LENGTH, borderaxespad=0)
    fig.text(fx(P["ylabel_x"]), 0.5, VOCAB["ids_thousands"].format(LEVEL_UNIT[level]), rotation=90, ha="left",
             va="center")
    drawn = [g for g in shown if units.get(g)]
    per = [len(units[g]) for g in drawn]
    gone = [g for g in D.ALL_GROUPS if g not in shown] + empty
    not_run, _ = sage_not_run(tabs, gone, set(units))
    sage = f"{D.ENGINE_NAME['sage']} {REASON_LABEL['not_run_by_design']}"
    others = ordered_groups(g for g in units if g not in shown)  # groups outside the design: not drawn
    fig.facts = {
        "level": level, "datasets": len(drawn), "units": sum(per),
        "units_per_dataset": "NA" if not per else (f"{min(per)}" if min(per) == max(per) else
                                                     f"{min(per)} to {max(per)}"),
        "points_class_I": "samples (pooled files of one sample), not runs",
        "empty_panels": ",".join(empty) or "none",
        "dropped_runs": ", ".join(f"{u} ({why})" for u, (g, why) in sorted(
            dropped.items(), key=lambda kv: (D.order_key(kv[1][0]), kv[0])) if g in shown) or "none",
        "left_out": left_out_fact(
            [(g, engine_reasons(notes.get(g)) or (sage if g in not_run else VOCAB["not_counted_all"])) for g in gone]
            + [(g, REASON_LABEL["outside_design"]) for g in others]),
    }
    return fig, f"{len(shown)} panels, {len(empty)} empty"


# ---------------------------------------------------------------- O8: electron-based datasets
def fdp_index(rows):
    """{(engine, unit, level): {'role', 'group', 'shuffled': (mean_shared, sd_shared), 'n_shared', 'own', 'natural',
    'arath', 'notes', 'designs'}} from O11_fdp_runs (one row per engine, unit, level and design; 'designs' the designs
    of its rows, with or without a value)."""
    out = {}
    for r in rows:
        rec = out.setdefault((r["engine"], r["unit"], r["level"]),
                             {"role": r.get("role", ""), "group": r.get("group", ""), "shuffled": (None, None),
                              "n_shared": None, "own": None, "natural": None, "arath": None, "notes": [],
                              "designs": set()})
        design = r.get("design", "")
        rec["designs"].add(design)
        if design == "shuffled":
            rec["shuffled"] = (num(r.get("mean_shared")), num(r.get("sd_shared")))
            rec["n_shared"] = num(r.get("n_shared"))
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
    """O8 figure (SPEC 3.1; S4): 2 x 2, rows PSM and peptide level, y shared per column, letters A-D. Left the lead of
    ProSE over MSFragger per run in %, 100 x (ratio - 1) (G17), as bars from 0 in the comparator colour (as FigS11), on
    a lead axis symmetric about 0 with the tick rule of G10; a missing ratio is labelled at the zero line, without an
    x. Right the combined FDP mean +- SD per run and engine over the shared realizations on fdp_axis with a 1% line.
    A decision run is drawn as any other run (no mark of its own). x: one category per unit, grouped by dataset; the
    class blocks are named above the top row, and a dataset with several units is named once there while its ticks say
    "fraction N" (unit_blocks). Legend: the engines, then the mean +- SD mark (as Fig 2 and FigS4) and "Sage: not run";
    O08's reason goes to index.tsv. 7.0 x 4.6 in."""
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
    count = {}
    for g, _ in items:
        count[g] = count.get(g, 0) + 1
    labels = [D.display(g) if count[g] == 1 else unit_suffix(u, g) for g, u in items]
    levels = [lv for lv in D.LEVELS if any(r["level"] == lv for r in rows)]
    fig, axs = new_figure(plt, 4.6, len(levels), 2, sharex=True, sharey="col")
    engines = ("prose", "msfragger")
    off = dodge(engines, FDP_DODGE)
    leads, fdp_values = [0.0], []
    for i, level in enumerate(levels):
        by_unit = {r["unit"]: r for r in rows if r["level"] == level}
        ax, bx = axs[i][0], axs[i][1]
        fmarks = Marks(bx)
        for x, (g, u) in zip(xs, items):
            r = by_unit.get(u)
            ratio = num(r["ratio"]) if r else None
            if ratio is None:  # a lead axis: the reason at the zero line, no x (as O5's n/a)
                ax.annotate(reason_label(r["note"] if r else "", "empty"), xy=(x, 0), xytext=(0, 2),
                            textcoords="offset points", ha="center", va="bottom", color="0.25")
            else:
                colour = D.COLOUR["msfragger"]
                ax.bar(x, 100 * (ratio - 1), width=0.7, color=colour, edgecolor=colour, lw=0.6, zorder=2)
                leads.append(100 * (ratio - 1))
            for e in engines:
                rec = fdp.get((e, u, level))
                if o11:
                    mean, sd = rec["shuffled"] if rec else (None, None)
                    own = rec["own"] if rec else None
                    notes = rec["notes"] if rec else []
                else:  # O11_fdp_runs absent: O08's own values (index.tsv says so)
                    mean, sd = (num(r[f"fdp_{e}_mean"]), num(r[f"fdp_{e}_sd"])) if r else (None, None)
                    own, notes = mean, ([r["note"]] if r else [])
                xe = x + off[e]
                if mean is not None:
                    bx.errorbar([xe], [100 * mean], yerr=None if sd is None else [100 * sd], color=D.COLOUR[e],
                                zorder=3, **FDP_DOT)
                    fdp_values.append(100 * (mean + (sd or 0.0)))
                elif own is not None:  # counted, but the run is not in F (no realization shared by both engines)
                    fmarks.add(xe, VOCAB["not_shared"], D.COLOUR[e])
                elif r is not None:
                    fmarks.add(xe, reason_label(*notes, r["note"], engine=e), D.COLOUR[e])
        ax.axhline(0, zorder=2.5, **ZERO_LINE)
        one_percent_line(bx)
        fmarks.draw()
        ax.set_ylabel(VOCAB["lead_over"].format("ProSE", D.ENGINE_NAME["msfragger"]))
        for a, k, what in ((ax, 2 * i, "identifications"), (bx, 2 * i + 1, "entrapment FDP")):
            pad = unit_blocks(a, items, xs, label=(i == 0))
            title(a, f"{LEVEL_NAME[level]} level, {what}", letter=k, pad=pad)
    top = max(abs(v) for v in leads)
    step = tick_step([axs[i][0] for i in range(len(levels))], [(-top, top)] * len(levels))  # symmetric about 0
    for i in range(len(levels)):
        fdp_axis(axs[i][1], fdp_values)
    for a in axs[-1]:
        category_axis(a, xs, labels, [g for g, _ in items])
        a.set_xlim(xs[0] - 0.7, xs[-1] + 0.7)
    reasons = sorted({not_run_reason(r["sage_status"]) for r in rows
                      if state_word(r["sage_status"]) == "not_run_by_design"} - {""})
    not_run = any(state_word(r["sage_status"]) == "not_run_by_design" for r in rows)
    legend_rows(fig, engine_handles(engines), [errorbar_handle(VOCAB["shuffled"])]
                + ([text_handle(VOCAB["sage_not_run"])] if not_run else []))
    fig.facts = {"tick_step": f"{step:g}",
                 "fdp": "shared realizations" if o11 else "own realizations (no O11_fdp_runs)",
                 "sage_not_run_reason": "; ".join(reasons) or "NA"}
    return fig, f"{2 * len(levels)} panels, {len(items)} x categories"


# ---------------------------------------------------------------- O9: immunopeptidomics
def fig_immuno(plt, tabs):
    """O9 figure (SPEC 3.1; F4.1-F4.5): 2 x 2, rows in design.IMMUNO_ORDER (PXD058436, then PXD019643; G13), columns
    class I and class II, letters A-D row by row; x the samples (donor and tissue); peptides at 1% peptide-level FDR
    (DS:625). Bars ProSE, Sage, MSFragger (width IMMUNO_BAR, edge 0.5 pt). ProSE's other arrangement is a fourth,
    open bar (G7) only when the table has a value for it: with prose_other NA in every row its slot and legend entry
    are dropped (D7), else the bars say "ProSE, <arrangement> (main)" and "ProSE, <other arrangement>". A missing
    value is an x with a vertical label in its slot ("out of memory" for Sage on class II). Published values are
    markers right of the bars (MHCquant2 diamond, FragPipe triangle, PEAKS square, each "(published)"; filled grey for
    a local FDR), PUBLISHED_FIRST_PT points right of the last bar, then PUBLISHED_STEP_PT apart (points, so that they
    touch neither the bar nor each other at any panel width). A decision sample is drawn as any other sample (no mark
    of its own). Headings "<dataset>, <instrument>, grade <g>". Legend: the bars, then the published markers.
    index.tsv facts for the caption (F4.5): the samples drawn as "out of memory" per engine and group (the 200 GiB
    cap), and that each panel has its own y scale. 7.0 x 4.4 in."""
    from matplotlib import ticker
    from matplotlib.transforms import offset_copy
    rows = tabs.need("O09_immuno_samples", ("group", "grade", "sample", "donor_tissue", "role", "level",
                                            "main_arrangement", "prose_main", "prose_other", "sage", "sage_status",
                                            "msfragger", "mhcquant", "fragpipe", "peaks", "fdr_note", "note"))
    rows = [r for r in rows if r["level"] == "peptide"]  # peptide level is primary (DS:625)
    if not rows:
        raise Skip("O09_immuno_samples has no peptide row")
    main = next((r["main_arrangement"] for r in rows if r["main_arrangement"] not in NA_TEXT), "main")
    other = {"per_file": "joint", "joint": "per_file"}.get(main, "other")
    words = VOCAB["arrangement"]
    other_drawn = any(num(r["prose_other"]) is not None for r in rows)  # D7: no slot for an arrangement without data
    # (column, fill, edge, line width, label): ProSE's other arrangement is an open bar (G7)
    bars = [("prose_main", D.COLOUR["prose"], "white", 0.5,
             f"ProSE, {words.get(main, 'main arrangement')} (main)" if other_drawn else D.ENGINE_NAME["prose"])]
    if other_drawn:
        bars.append(("prose_other", OPEN_BAR["color"], D.COLOUR["prose"], OPEN_BAR["lw"],
                     f"ProSE, {words.get(other, 'other arrangement')}"))
    bars += [("sage", D.COLOUR["sage"], "white", 0.5, D.ENGINE_NAME["sage"]),
             ("msfragger", D.COLOUR["msfragger"], "white", 0.5, D.ENGINE_NAME["msfragger"])]
    published = (("mhcquant", "D", "MHCquant2"), ("fragpipe", "^", "FragPipe"), ("peaks", "s", "PEAKS"))
    width = IMMUNO_BAR
    offs = [(k - (len(bars) - 1) / 2) * width for k in range(len(bars))]
    pub_x = offs[-1] + width / 2  # the right edge of the last bar
    fig, axs = new_figure(plt, 4.4, 2, 2)
    local_used = False
    n_x = 0
    oom = {}  # (engine name, group) -> samples drawn as "out of memory"
    # rows in the design order (G13: as fig_time_per_file and fig_low_memory), columns class I and class II
    projects = list(dict.fromkeys(g.split("_", 1)[0] for g in D.IMMUNO_ORDER))[:2]
    for i, project in enumerate(projects):
        for j, cls_name in enumerate(("classI", "classII")):
            ax = axs[i][j]
            group = f"{project}_{cls_name}"
            sub = sorted((r for r in rows if r["group"] == group), key=lambda r: donor_number(r["sample"]))
            grade = D.grade(group) if D.grade(group) != "-" else (sub[0]["grade"] if sub else "-")
            title(ax, f"{D.display(group)}, {D.instrument(group)}" + (f", grade {grade}" if grade != "-" else ""),
                  letter=2 * i + j)
            if not sub:
                ax.text(0.5, 0.5, VOCAB["no_sample"], transform=ax.transAxes, ha="center", va="center", color="0.3")
                ax.set_xticks([])
                continue
            marks = Marks(ax)
            ticks = []
            for x, r in enumerate(sub):
                donor, tissue = donor_of(r["sample"], r["donor_tissue"])
                ticks.append(donor + (f"\n{tissue}" if tissue else ""))
                for (col, face, edge, lw, _), o in zip(bars, offs):
                    v = num(r[col])
                    if v is None:
                        if col == "prose_other":
                            why = "not run"
                        elif col == "sage":
                            why = reason_label(r["sage_status"], r["note"])
                        else:
                            why = reason_label(r["note"])
                        marks.add(x + o, why, face if face != "white" else edge)
                        if why == REASON_LABEL["failed_memory"]:  # the caption says the memory cap stopped it (F4.5)
                            name = D.ENGINE_NAME["prose" if col.startswith("prose") else col]
                            oom[(name, group)] = oom.get((name, group), 0) + 1
                        continue
                    ax.bar(x + o, v, width=width, color=face, edgecolor=edge, lw=lw, zorder=2)
                local = r["fdr_note"].strip().lower() == "local"
                for k, (col, marker, _) in enumerate(published):
                    v = num(r[col])
                    if v is not None:
                        local_used = local_used or local
                        shift = offset_copy(ax.transData, fig=fig, x=PUBLISHED_FIRST_PT + k * PUBLISHED_STEP_PT,
                                            units="points")
                        ax.plot([x + pub_x], [v], ls="none", marker=marker, ms=3.8, mfc="0.6" if local else "white",
                                mec="black", mew=0.7, zorder=4, transform=shift)
                        ax.update_datalim([(x + pub_x, v)])  # the y limits include it (shifted lines are not)
            n_x += len(sub)
            ax.set_xticks(range(len(sub)))
            ax.set_xticklabels(ticks)
            ax.tick_params(axis="x", length=0)
            ax.set_xlim(-0.6, len(sub) - 0.4)
            ax.set_ylim(bottom=0)
            ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda v, _: minus(f"{v:,.0f}")))  # as fig_ids_counts
            marks.draw(mode="slot")
            if j == 0:
                ax.set_ylabel(VOCAB["ids"].format("peptides"))
    hs = [marker_handle(VOCAB["published"].format(label), marker, "black", face="white")
          for _, marker, label in published]
    if local_used:
        hs.append(marker_handle("MHCquant 1.5.1 (published, local FDR)", "D", "black", face="0.6"))
    legend_rows(fig, [patch_handle(label, face, edge, lw=lw) for _, face, edge, lw, label in bars], hs)
    fig.facts = {"main_arrangement": main,
                 "other_arrangement": "drawn" if other_drawn else "slot dropped (NA in every row)",
                 "published_local_fdr": "yes" if local_used else "no",
                 "out_of_memory": ", ".join(f"{e} {g} ({n} samples)" for (e, g), n in oom.items()) or "none",
                 "y_scales": "independent per panel"}
    return fig, f"4 panels, {n_x} x categories" + ("" if other_drawn else ", other arrangement all NA: slot dropped")


# ---------------------------------------------------------------- O11 + O12: entrapment FDP
def fig_fdp(plt, tabs):
    """O11 figure with O12's arath values (SPEC 3.2; FigS4, S3): rows PSM and peptide level with one y axis
    (fdp_axis); x the tryptic datasets then the electron datasets in design order; engines dodged fdp_dodge (FDP_DODGE
    for 3 runs per engine, less for fewer) and runs spread fdp_half (FDP_SPREAD_WIDE for a group with more than 3 runs
    per engine). A group with an empty engine slot (no Sage on electron-based data) dodges only the engines present,
    with more than 3 runs per engine FDP_SPARSE_DODGE with the runs spread FDP_SPARSE_SPREAD. Per run the shared
    shuffled mean as a 1.8 pt dot (FDP_FULL_DOT: the 22 categories are narrower than Fig 2's) with its SD bar; natural
    as an open diamond and arath as an open triangle of the same footprint, at the run's x above its SD bar and under
    its dot (FDP_FULL_*_Z); a decision run is drawn as any other run (its shared mean +- SD; no mark of its own);
    dashed 1% line; "Sage: not run" (from O14) under the electron block in A, inside the panel at its base. index.tsv
    facts for the caption (S3): the natural values of the datasets that also have a shuffled design
    (O11_fdp_datasets, the mean of the run means; velos, and since 2026-11-26 ups1_control, astral_s1 and ultra2_s2),
    the range of the Arabidopsis values drawn and of O12's difference_pp, and when it draws a design group the design
    groups it does not draw, with the reason (left_out, fdp_left_out: immunopeptidomics, groups without an O11 row).
    It writes no count of the runs above 1%: Fig 2's counts leave out the decision runs that FigS4 draws. Legend dots
    of FDP_FULL_HANDLE_MS. 7.0 x 5.0 in."""
    rows = tabs.need("O11_fdp_runs", ("engine", "group", "unit", "role", "level", "design", "mean_own", "mean_shared",
                                      "sd_shared", "natural", "arath", "note"))
    fdp = fdp_index(rows)
    o12 = tabs.optional("O12_fdp_arath", ("engine", "unit", "level", "arath"))
    for r in o12:
        rec = fdp.get((r["engine"], r["unit"], r["level"]))
        if rec is not None and rec["arath"] is None:
            rec["arath"] = num(r["arath"])
    groups = ordered_groups(rec["group"] for rec in fdp.values() if D.kind(rec["group"]) != "immuno")
    engines = engines_in(rows)
    levels = [lv for lv in D.LEVELS if any(k[2] == lv for k in fdp)]
    not_run, facts = sage_not_run(tabs, groups, {rec["group"] for (e, _, _), rec in fdp.items() if e == "sage"})
    fig, axs = new_figure(plt, 5.0, len(levels), 1, sharex=True, sharey=True)
    # per group over both levels (so that A and B put an engine at the same x): the engines with a run, and the most
    # runs of one engine
    runs_of = {}
    for (e, u, lv), rec in fdp.items():
        runs_of.setdefault(rec["group"], {}).setdefault((e, lv), []).append(u)
    present_in = {g: [e for e in engines if any(k[0] == e for k in runs_of.get(g, {}))] for g in groups}
    most_in = {g: max((len(v) for v in runs_of.get(g, {}).values()), default=0) for g in groups}
    values, arath, arath_units, both = [], {}, set(), []
    for i, level in enumerate(levels):
        ax = axs[i][0]
        marks = Marks(ax)
        for x, g in enumerate(groups):
            by_engine = {e: [(u, rec) for (en, u, lv), rec in fdp.items() if en == e and lv == level
                             and rec["group"] == g] for e in engines}
            present = present_in[g]
            # an empty engine slot: the engines present close up; with more than 3 runs per engine they spread wider
            wide = len(present) < len(engines) and most_in[g] > 3
            offs = dodge(present, FDP_SPARSE_DODGE if wide else fdp_dodge(most_in[g]))
            for e in present:
                recs = by_engine[e]
                if not recs:
                    continue
                half = FDP_SPARSE_SPREAD if wide else FDP_SPREAD_WIDE if len(recs) > 3 else fdp_half(len(recs))
                for (unit, rec), o in zip(recs, spread(len(recs), half)):
                    xe = x + offs[e] + o
                    mean, sd = rec["shuffled"]
                    if mean is not None and rec["natural"] is not None and g not in both:
                        both.append(g)
                    if rec["arath"] is not None:
                        arath.setdefault((level, e), []).append(100 * rec["arath"])
                        arath_units.add(unit)
                    if mean is not None:
                        bar = ax.errorbar([xe], [100 * mean], yerr=None if sd is None else [100 * sd],
                                          color=D.COLOUR[e], zorder=FDP_FULL_DOT_Z, **FDP_FULL_DOT)
                        for lines in bar.lines[2]:  # the bar under the open marks, the dot (bar.lines[0]) above
                            lines.set_zorder(FDP_FULL_BAR_Z)
                        values.append(100 * (mean + (sd or 0.0)))
                    # the open marks of the same run at its x (2.1 pt steps leave no room beside it), between its SD
                    # bar and its dot: the white fill breaks the bar, the dot stays whole
                    if rec["natural"] is not None:
                        ax.plot([xe], [100 * rec["natural"]], ls="none", mec=D.COLOUR[e], zorder=FDP_FULL_OPEN_Z,
                                **NATURAL)
                        values.append(100 * rec["natural"])
                    if rec["arath"] is not None:
                        ax.plot([xe], [100 * rec["arath"]], ls="none", mec=D.COLOUR[e], zorder=FDP_FULL_OPEN_Z,
                                **ARATH)
                        values.append(100 * rec["arath"])
                    if mean is None and rec["natural"] is None and rec["arath"] is None:
                        # counted, but no realization shared by every expected engine (not in F); else the reason.
                        # One x per engine and column, at the engine's place
                        why = VOCAB["not_shared"] if rec["own"] is not None else reason_label(*rec["notes"], engine=e)
                        marks.add(x + offs[e], why, D.COLOUR[e])
        if i == 0:
            not_run_labels(marks, groups, range(len(groups)), not_run)
        one_percent_line(ax)
        marks.draw()
        blocks = draw_blocks(ax, groups, label=(i == 0))
        title(ax, VOCAB["level"].format(LEVEL_NAME[level]), above_blocks=blocks,
              letter=i if len(levels) > 1 else None)
    for i in range(len(levels)):
        fdp_axis(axs[i][0], values)
    dataset_axis(axs[-1][0], groups)
    legend_rows(fig, engine_handles(engines, ms=FDP_FULL_HANDLE_MS), [
        errorbar_handle(VOCAB["shuffled"], ms=FDP_FULL_HANDLE_MS), natural_handle(), arath_handle()])
    facts.update(fdp_caption_facts(tabs, both, levels, engines, arath, arath_units, o12))
    if arath:  # one at a bar end can look like an open arrowhead: the caption says what the triangles are
        facts["arath_marks"] = "open triangles: the run's Arabidopsis entrapment FDP, a value (not an arrow or a bound)"
    if any(g in D.ALL_GROUPS for g in groups):  # the caption says which design groups have no column, and why
        facts["left_out"] = fdp_left_out(tabs, fdp, groups)
    fig.facts = facts
    return fig, f"{len(levels)} panels, {len(groups)} x categories"


def fdp_caption_facts(tabs, both, levels, engines, arath, arath_units, o12):
    """index.tsv facts of FigS4 (S3) beyond Fig 2's: per dataset drawn with both a shuffled and a natural design
    (found in the data: velos, and since 2026-11-26 ups1_control, astral_s1 and ultra2_s2) and level, the natural
    value of each engine, the mean of its run means in % (O11_fdp_datasets, read here; NA without it); the
    Arabidopsis units, per level the range of the values drawn in % and of O12's difference_pp (arath - shuffled
    mean) per engine."""
    def pct(v):
        return "NA" if v is None else f"{100 * v:.2f}"
    facts = {}
    datasets = tabs.optional("O11_fdp_datasets", ("engine", "group", "level", "design", "mean_of_run_means")) \
        if both else []
    for g in both:
        for level in levels:
            got = {r["engine"]: num(r["mean_of_run_means"]) for r in datasets
                   if r["group"] == g and r["level"] == level and r["design"] == "natural"}
            facts[f"natural_{g}_{level}_pct"] = ", ".join(f"{D.ENGINE_NAME[e]} {pct(got.get(e))}" for e in engines)
    facts["arath_units"] = str(len(arath_units))
    for level in levels:
        drawn = [(e, arath[(level, e)]) for e in engines if (level, e) in arath]
        if drawn:
            facts[f"arath_{level}_pct"] = ", ".join(f"{D.ENGINE_NAME[e]} {min(v):.2f} to {max(v):.2f}"
                                                    for e, v in drawn)
        diffs = {}
        for r in o12:
            d = num(r.get("difference_pp"))
            if r["level"] == level and d is not None:
                diffs.setdefault(r["engine"], []).append(d)
        if diffs:
            facts[f"arath_{level}_difference_pp"] = ", ".join(
                f"{D.ENGINE_NAME[e]} {min(diffs[e]):+.2f} to {max(diffs[e]):+.2f}" for e in engines if e in diffs)
    return facts


def natural_only_groups(fdp, groups, levels):
    """The groups whose non-decision runs have no shuffled design in any level (no O11 row of that design, whatever
    its value) but a natural value (found in the data, never a fixed list): the natural-only datasets of
    fig_fdp_main. A group with a shuffled design whose shuffled means are all missing (e.g. not shared by every
    engine) is not one: its runs get the missing marks."""
    out = []
    for g in groups:
        recs = [rec for (_, _, lv), rec in fdp.items() if rec["group"] == g and lv in levels
                and rec["role"] != "decision"]
        if recs and all("shuffled" not in rec["designs"] for rec in recs) and any(rec["natural"] is not None
                                                                                 for rec in recs):
            out.append(g)
    return out


ENTRAPMENT_DESIGNS = ("shuffled", "natural", "arath")  # O14_coverage db_design of an entrapment search


def fdp_left_out(tabs, fdp, drawn, natural_only=()):
    """index.tsv's left_out of Fig 2 and FigS4 (left_out_fact): every design group (D.ALL_GROUPS) not in drawn, with
    the reason. First 'natural entrapment only' for a group of natural_only (Fig 2 with FDP_MAIN_NATURAL_ONLY =
    False). Else a group with an O11 row is left out when it is electron-based (Fig 2: 'electron-based: in FigS4',
    the number of fig_fdp in PAPER_FIGURES; 'in the full FDP figure' when fig_fdp has none) or immunopeptidomics
    ('immunopeptidomics: not drawn'). An immunopeptidomics group without an O11 row: 'no entrapment search' when
    O14_coverage (optional, read only then) has no entrapment search of it, 'no row in O11' when O14 has one or is
    absent or empty. Any other group without an O11 row: 'no row in O11'."""
    in_o11 = {rec["group"] for rec in fdp.values()}
    gone = [g for g in D.ALL_GROUPS if g not in drawn]
    o14 = []
    if any(D.kind(g) == "immuno" and g not in in_o11 for g in gone):
        o14 = tabs.optional("O14_coverage", ("group", "db_design"))
    entrapment = {r["group"] for r in o14 if r["db_design"] in ENTRAPMENT_DESIGNS}
    full = paper_name("fig_fdp")  # where the electron-based groups are drawn; no code name in a caption fact
    electron = f"electron-based: in {full[1]}" if full else "electron-based: in the full FDP figure"

    def why(g):
        if g in natural_only:
            return "natural entrapment only"
        if g in in_o11:
            return electron if D.kind(g) == "electron" else "immunopeptidomics: not drawn"
        if D.kind(g) == "immuno" and o14 and g not in entrapment:
            return "no entrapment search"
        return "no row in O11"
    return left_out_fact((g, why(g)) for g in gone)


def fig_fdp_main(plt, tabs):
    """Fig 2 of the paper (F2.1), the slim fig_fdp: O11_fdp_runs over the tryptic datasets only (design.FIGURE_ORDER
    present in the data); rows PSM and peptide level with one y axis (fdp_axis); per non-decision run the shuffled
    shared mean as a filled 2.6 pt dot (FDP_DOT, no edge) with its SD bar (0.6 pt), engines dodged fdp_dodge (FDP_DODGE
    for 3 runs per engine, less for fewer) and runs spread fdp_half. Every natural value of a run is an open diamond
    (NATURAL) without SD: a dataset without a shuffled design but with natural values (natural-only,
    natural_only_groups, found in the data) shows only diamonds (D3; with FDP_MAIN_NATURAL_ONLY = False these datasets
    are left out and index.tsv names them, natural_only_left_out); a dataset with both designs shows both, as FigS4,
    the diamond at the run's x between its SD bar and its dot (FDP_FULL_*_Z; decided 2026-11-26, when ups1_control,
    astral_s1 and ultra2_s2 got the shuffled design; for velos too, the owner's choice), or above the dot when it is
    less than FDP_ON_DOT_PT from it (natural_on_dot). Not drawn: decision runs, Arabidopsis. Missing shuffled values
    (also in a dataset with a shuffled design whose means are all missing) as x plus label (one x per engine and
    column; an engine without a shuffled row of a run in a dataset with a shuffled design gets 'not run', as O11
    leaves out a design only when its searches did not run: has_shuffled). index.tsv facts: the natural-only datasets and the datasets drawn with both designs
    (natural_with_shuffled); the diamonds drawn above their dot, with run, engine and level (natural_on_dot, set when
    the figure is finished); the design groups not drawn, with the reason (left_out, fdp_left_out: an
    electron-based group with an O11 row is in fig_fdp's figure, by its PAPER_FIGURES number); per level and engine
    the runs drawn above 1%, apart for the shuffled means (dots, shuffled_runs_above_1pct_*), the natural values of
    the natural-only datasets (diamonds, natural_only_runs_above_1pct_*) and those of the datasets with both designs
    (diamonds, natural_with_shuffled_runs_above_1pct_*); the n of the SD bars (sd_n_shared). 7.0 x 4.0 in."""
    rows = tabs.need("O11_fdp_runs", ("engine", "group", "unit", "role", "level", "design", "mean_own", "mean_shared",
                                      "sd_shared", "natural", "arath", "note"))
    fdp = fdp_index(rows)
    present = {rec["group"] for rec in fdp.values()}
    groups = [g for g in D.FIGURE_ORDER if g in present]
    if not groups:
        raise Skip("O11_fdp_runs has no tryptic dataset")
    levels = [lv for lv in D.LEVELS if any(k[2] == lv and fdp[k]["group"] in groups for k in fdp)]
    natural_only = natural_only_groups(fdp, groups, levels)
    left_out = [] if FDP_MAIN_NATURAL_ONLY else natural_only
    groups = [g for g in groups if g not in left_out]
    engines = engines_in(rows)
    # per group over both levels (A and B put an engine at the same x): the most non-decision runs of one engine
    runs_of = {}
    for (e, _, lv), rec in fdp.items():
        if rec["role"] != "decision" and lv in levels:
            runs_of[(rec["group"], e, lv)] = runs_of.get((rec["group"], e, lv), 0) + 1
    offs_of = {g: dodge(engines, fdp_dodge(max((n for (gg, _, _), n in runs_of.items() if gg == g), default=0)))
               for g in groups}
    # the datasets with a shuffled design: an O11 shuffled row of one of their runs, with or without a value (the
    # negation of natural_only_groups' first test). There a run of an engine without a shuffled row did not run its
    # shuffled searches: O11 leaves out a design only when its searches are not_run or not_run_by_design
    # (fdp.search_ran), so its label is 'not run'
    has_shuffled = {g: any("shuffled" in rec["designs"] for (_, _, lv), rec in fdp.items()
                           if rec["group"] == g and lv in levels and rec["role"] != "decision") for g in groups}
    fig, axs = new_figure(plt, 4.0, len(levels), 1, sharex=True, sharey=True)
    values, facts, n_shared, both, near = [], {}, [], [], []
    for i, level in enumerate(levels):
        ax = axs[i][0]
        marks = Marks(ax)
        for x, g in enumerate(groups):
            off = offs_of[g]
            for e in engines:
                recs = [(u, rec) for (en, u, lv), rec in fdp.items() if en == e and lv == level and rec["group"] == g
                        and rec["role"] != "decision"]
                # natural-only (natural_only_groups): no shuffled design and a natural value, not just no shuffled
                # mean; a dataset with neither design's value is not natural-only and has no shuffled design either
                diamonds = g in natural_only
                # [above 1%, drawn]; the natural values apart for the natural-only datasets and the datasets that also
                # have a shuffled design
                shown = {"shuffled": [0, 0], "natural_only": [0, 0], "natural_with_shuffled": [0, 0]}
                for (unit, rec), o in zip(recs, spread(len(recs), fdp_half(len(recs)))):
                    xe = x + off[e] + o
                    mean, sd = rec["shuffled"]
                    nat = rec["natural"]
                    if mean is not None:
                        bar = ax.errorbar([xe], [100 * mean], yerr=None if sd is None else [100 * sd],
                                          color=D.COLOUR[e], zorder=FDP_FULL_DOT_Z, **FDP_DOT)
                        values.append(100 * (mean + (sd or 0.0)))
                        shown["shuffled"] = [shown["shuffled"][0] + (mean > 0.01), shown["shuffled"][1] + 1]
                        if sd is not None:
                            n_shared.append(rec["n_shared"])
                    if nat is not None:
                        # with a dot, as FigS4: the diamond at the run's x (the runs' 2.7 pt steps leave no room
                        # beside it), between its SD bar and its dot: the white fill breaks the bar, the dot stays whole
                        if mean is not None:
                            for lines in bar.lines[2]:
                                lines.set_zorder(FDP_FULL_BAR_Z)
                        ln, = ax.plot([xe], [100 * nat], ls="none", mec=D.COLOUR[e],
                                      zorder=FDP_FULL_OPEN_Z if mean is not None else 5, **NATURAL)
                        if mean is not None:
                            near.append((ax, ln, xe, mean, nat, unit, e, level))
                        values.append(100 * nat)
                        what = "natural_only" if diamonds else "natural_with_shuffled"
                        shown[what] = [shown[what][0] + (nat > 0.01), shown[what][1] + 1]
                        if not diamonds and g not in both:
                            both.append(g)
                    if mean is None and (nat is None or not diamonds):
                        # no shuffled mean where the dataset has a shuffled design (or nothing at all): no shuffled
                        # row of the run where the dataset has that design (its searches did not run: has_shuffled),
                        # counted but not in F (no realization shared by every engine), else the reason; one x per
                        # engine and column, at the engine's place
                        if has_shuffled[g] and "shuffled" not in rec["designs"]:
                            why = REASON_LABEL["not_run"]
                        elif rec["own"] is not None:
                            why = VOCAB["not_shared"]
                        else:
                            why = reason_label(*rec["notes"], engine=e)
                        marks.add(x + off[e], why, D.COLOUR[e])
                # the runs drawn (tryptic; O11's own keys also count the electron runs), apart by mark: the shuffled
                # means (dots), the natural values of the natural-only datasets and those of the datasets that also
                # have a shuffled design (diamonds)
                for what, (above, n) in shown.items():
                    if n:
                        key = f"{what}_runs_above_1pct_{level}_{e}"
                        a, m = (int(v) for v in facts.get(key, "0/0").split("/"))
                        facts[key] = f"{a + above}/{m + n}"
        one_percent_line(ax)
        marks.draw()
        blocks = draw_blocks(ax, groups, label=(i == 0))
        title(ax, VOCAB["level"].format(LEVEL_NAME[level]), above_blocks=blocks,
              letter=i if len(levels) > 1 else None)
    for i in range(len(levels)):
        fdp_axis(axs[i][0], values)
    dataset_axis(axs[-1][0], groups)
    legend_rows(fig, engine_handles(engines), [
        errorbar_handle(VOCAB["shuffled"]), natural_handle(),
        line_handle(VOCAB["one_percent"], ls=whole_dashes(ONE_PERCENT_DASHES, ONE_PERCENT["lw"]),
                    lw=ONE_PERCENT["lw"], colour=ONE_PERCENT["color"])])  # whole dashes, no end stub
    # the n of the SD bars drawn (F2.2 item 3 says n = 3): their range and the runs with fewer shared realizations
    known = [int(n) for n in n_shared if n is not None]
    counts = {k: facts[k] for what in ("shuffled", "natural_only", "natural_with_shuffled") for level in levels
              for e in engines for k in [f"{what}_runs_above_1pct_{level}_{e}"] if k in facts}
    fig.facts = {"natural_only": ",".join(natural_only) or "none",
                 "natural_only_drawn": "yes" if FDP_MAIN_NATURAL_ONLY else "no (left out)",
                 "natural_only_left_out": ",".join(left_out) or "none",
                 "natural_with_shuffled": ",".join(both) or "none",
                 "natural_on_dot": "not measured (the figure was not finished)",
                 "left_out": fdp_left_out(tabs, fdp, groups, left_out), **counts,
                 "sd_n_shared": "NA" if not known else (f"{min(known)}" if min(known) == max(known)
                                                        else f"{min(known)} to {max(known)}"),
                 "sd_runs_n_shared_below_3": str(sum(n < 3 for n in known))}

    def raise_on_dot():
        """Once the layout is final: a diamond less than FDP_ON_DOT_PT from its run's dot above the dot; the runs."""
        on = []
        for ax, ln, xe, mean, nat, unit, e, level in near:
            y_mean, y_nat = (ax.transData.transform((xe, 100 * v))[1] for v in (mean, nat))
            if abs(y_nat - y_mean) * 72.0 / fig.dpi < FDP_ON_DOT_PT:
                ln.set_zorder(FDP_ON_DOT_Z)
                on.append(f"{unit} ({D.ENGINE_NAME[e]}, {LEVEL_NAME[level]})")
        fig.facts["natural_on_dot"] = str(len(on)) + (f": {', '.join(on)}" if on else "")
    later(fig, raise_on_dot)
    return fig, (f"{len(levels)} panels, {len(groups)} x categories, "
                 f"{len(natural_only) if FDP_MAIN_NATURAL_ONLY else 0} natural-only"
                 + (f"; left out: {', '.join(left_out)}" if left_out else ""))


# ---------------------------------------------------------------- O13: matched FDP
def fig_matched_fdp(plt, tabs):
    """O13 figure (SPEC 3.2; S9, D16): per run, ProSE's lead at q <= 0.01 against its lead at the matched combined FDP
    of 1%, on the same entrapment searches; one panel per level (letters A, B; headings "PSM level", "peptide level")
    on one common range with an identity line; one colour per comparator, marker by design (shuffled mean dot, natural
    diamond, arath triangle); a decision run is drawn as any other run (no mark of its own). A row without both ratios
    is not drawn and is counted (info string and index.tsv). 7.0 x 3.6 in."""
    rows = tabs.need("O13_matched_fdp", ("pair", "level", "role", "design", "ratio_q01", "ratio_matched"))
    levels = [lv for lv in D.LEVELS if any(r["level"] == lv for r in rows)]
    if not levels:
        raise Skip("O13_matched_fdp has no psm or peptide row")
    shapes = {"shuffled": "o", "natural": "D", "arath": "^"}
    points, skipped = [], 0
    for r in rows:
        if r["level"] not in levels:
            continue
        a, b = num(r["ratio_q01"]), num(r["ratio_matched"])
        if a is None or b is None or a <= 0 or b <= 0:
            skipped += 1
            continue
        points.append((r["level"], comparator_of(r["pair"]) or "prose", shapes.get(r["design"], "o"),
                       100 * (a - 1), 100 * (b - 1)))
    lo = min([0.0] + [min(p[3], p[4]) for p in points])
    hi = max([0.0] + [max(p[3], p[4]) for p in points])
    pad = 0.08 * (hi - lo or 1.0)
    fig, axs = new_figure(plt, 3.6, 1, len(levels), categorical=False)
    comps = set()
    for i, level in enumerate(levels):
        ax = axs[0][i]
        for lv, comp, marker, la, lb in points:
            if lv != level:
                continue
            comps.add(comp)
            ax.plot([la], [lb], ls="none", marker=marker, ms=3.2, mfc=D.COLOUR[comp] if marker == "o" else "white",
                    mec=D.COLOUR[comp], mew=0.8, zorder=4)
        ax.plot([lo - pad, hi + pad], [lo - pad, hi + pad], color="0.4", ls="--", lw=0.7, zorder=1)
        ax.axhline(0, color="0.7", lw=0.5, zorder=0)
        ax.axvline(0, color="0.7", lw=0.5, zorder=0)
        ax.set_xlim(lo - pad, hi + pad)
        ax.set_ylim(lo - pad, hi + pad)
        ax.set_aspect("equal", adjustable="box")
        ax.set_xlabel(VOCAB["matched_x"])
        ax.set_ylabel(VOCAB["matched_y"])
        title(ax, VOCAB["level"].format(LEVEL_NAME[level]), letter=i if len(levels) > 1 else None)
    legend_rows(fig, [marker_handle(f"ProSE vs {D.ENGINE_NAME[c]}", "o", D.COLOUR[c]) for c in D.ENGINES
                      if c in comps and c != "prose"],
                [marker_handle(VOCAB["shuffled_mean"], "o", "0.2"),
                 marker_handle(VOCAB["natural"], "D", "0.2", face="white"),
                 marker_handle(VOCAB["arath"], "^", "0.2", face="white")])
    fig.facts = {"points": len(points), "skipped_rows": skipped}
    return fig, f"{len(levels)} panels, {len(points)} points, {skipped} row(s) without both ratios skipped"


# ---------------------------------------------------------------- O15: per-file timing
def fig_time_per_file(plt, tabs):
    """O15 figure (SPEC 3.3; F3.1-F3.5): A wall time per file (min, log, whole decades), B peak RSS (GiB, log); x the
    tryptic datasets then electron then immuno; one dot per unit per engine, the engines present in a category dodged
    0.27 (no empty slot where Sage has no run, as FigS4) and their runs spread +-0.08; a decision run is a dot as any
    other run (no mark of its own). A pooled sample's wall time is divided by its n_files (time per file). A missing
    value is never drawn as slow or fast: on the time axis every missing value is a label below the
    axis without an x (G15; "<engine>: out of memory" under each category where the engine ran out of memory, on
    three lines when one line is wider than the category); the RSS panel draws failed_memory as one x per engine and
    category on the 200 GiB cap line (DS:649, 653), a missing RSS of a timed search as an x with its label at the
    base, and nothing for an untimed search (its label stands between the panels). "Sage: not run" (from O14) under
    the electron block, below the time axis. Letters A, B without headings. Threads and machine (with its hypervisor)
    go to index.tsv, never into the figure, with the out-of-memory searches and, when an immunopeptidomics point is
    drawn, the note that B is the peak memory of a pooled sample's whole search (F3.4). 7.0 x 4.6 in."""
    rows = tabs.need("O15_time_runs", ("engine", "group", "unit", "role", "n_files", "state", "wall_med_s",
                                       "rss_med_gib", "note"))
    groups = ordered_groups(r["group"] for r in rows)
    engines = engines_in(rows)
    sage = [r for r in rows if r["engine"] == "sage"]
    not_run, nr_facts = sage_not_run(
        tabs, groups, {r["group"] for r in sage if state_word(r["state"]) != "not_run_by_design"},
        {r["group"] for r in sage if state_word(r["state"]) == "not_run_by_design"})
    fig, axs = new_figure(plt, 4.6, 2, 1, sharex=True)
    ta, ra = axs[0][0], axs[1][0]
    times = []
    # the reasons are written once, below the time axis (outside the data); the RSS panel repeats only the marks
    tmarks, rmarks = Marks(ta), Marks(ra)
    seen = set()  # legend keys only for what is drawn
    pooled = set()  # n_files of the immunopeptidomics points drawn
    for x, g in enumerate(groups):
        by_engine = {e: [r for r in rows if r["group"] == g and r["engine"] == e]
                     for e in engines if not (e == "sage" and g in not_run)}  # one label for the block (G15)
        off = dodge([e for e in engines if by_engine.get(e)], 0.27)
        for e, sub in by_engine.items():
            capped = False
            style = dict(ls="none", marker="o", ms=DOT_MS, mfc=D.COLOUR[e], mec=D.COLOUR[e], mew=0.5, zorder=4)
            for r, o in zip(sub, spread(len(sub), 0.08)):
                xe = x + off[e] + o
                n_files = num(r["n_files"]) or 1.0
                wall, rss = num(r["wall_med_s"]), num(r["rss_med_gib"])
                if state_word(r["state"]) == "failed_memory":  # on the cap line, never "slow" (DS:649, 653)
                    if not capped:  # one x per engine and category (index.tsv counts the searches)
                        capped = True
                        ra.plot([x + off[e]], [D.CAP_GIB], ls="none", marker="x", ms=4, mew=0.9, color=D.COLOUR[e],
                                zorder=6)
                        # below the time axis, under its own category, naming the engine ("Sage: out of memory")
                        name = D.ENGINE_NAME[e]
                        tmarks.add(x + off[e], VOCAB["engine_out_of_memory"].format(name), D.COLOUR[e], mark=False,
                                   narrow=VOCAB["engine_out_of_memory_narrow"].format(name), span=(x, x))
                    seen.add("failed_memory")
                    continue
                label = reason_label(r["state"], r["note"])
                timed = wall is not None and wall > 0
                if timed:
                    ta.plot([xe], [wall / n_files / 60.0], **style)
                    times.append(wall / n_files / 60.0)
                else:
                    tmarks.add(x + off[e], label, D.COLOUR[e], mark=False)
                if rss is not None and rss > 0:
                    ra.plot([xe], [rss], **style)
                elif timed:  # an untimed search already has its label between the panels: no x as "least memory"
                    rmarks.add(x + off[e], label, D.COLOUR[e])
                if timed or (rss is not None and rss > 0):  # a point is drawn
                    if D.kind(g) == "immuno" and num(r["n_files"]) is not None:
                        pooled.add(f"{num(r['n_files']):g}")
    not_run_labels(tmarks, groups, range(len(groups)), not_run)
    for a in (ta, ra):
        a.set_yscale("log")
    cap_line(ra)
    lo, hi = ra.get_ylim()
    ra.set_ylim(lo, max(hi, D.CAP_GIB * 1.8))
    decade_limits(ta, times)
    for a in (ta, ra):
        log_ticks(a)
    tmarks.draw(mode="below", gap=1.5)  # neighbouring categories share a label; one category apart they do not
    rmarks.draw()
    ta.set_ylabel(VOCAB["time_per_file"])
    ra.set_ylabel(VOCAB["memory"])
    blocks = draw_blocks(ta, groups, label=True)
    draw_blocks(ra, groups, label=False)
    title(ta, "", above_blocks=blocks, letter=0)
    title(ra, "", letter=1)
    dataset_axis(ra, groups)
    extra = []
    if "failed_memory" in seen:
        extra.append(marker_handle(VOCAB["out_of_memory_cap"].format(D.CAP_GIB), "x", "0.2"))
    legend_rows(fig, engine_handles(engines), extra)
    threads = sorted({r["threads"] for r in rows if "threads" in r and r["threads"] not in NA_TEXT})
    # the caption (F3.4 items 1, 3, 6): the searches stopped by the memory cap, per engine and group; that B is the
    # peak memory of the whole search of a pooled sample (A is divided by n_files).
    # No ";" inside a value: index.tsv separates the facts with "; ".
    oom = [(e, g, sum(r["engine"] == e and r["group"] == g and state_word(r["state"]) == "failed_memory"
                      for r in rows)) for g in groups for e in engines]
    oom_text = ", ".join(f"{D.ENGINE_NAME[e]} {g} ({n} {'samples' if D.kind(g) == 'immuno' else 'runs'})"
                         for e, g, n in oom if n)
    fig.facts = {"threads": ",".join(threads) or "NA", **machine_facts(tabs), **nr_facts,
                 "out_of_memory": oom_text or "none"}
    if pooled:  # an immunopeptidomics point is drawn
        fig.facts["immuno_memory"] = (f"B: peak memory of the search of a whole pooled sample "
                                      f"({'/'.join(sorted(pooled))} files), not divided, while A is the sample's time "
                                      "divided by its n_files")
    return fig, f"2 panels, {len(groups)} x categories"


# ---------------------------------------------------------------- O16: batch arm
def fig_batch(plt, tabs):
    """O16 figure (SPEC 3.3; S5, D12): two rows over the batch groups in design order (16 tryptic, then
    pxd065289_etcid in its block), shared x, letters A and B without headings. A: the batch time per file
    (batch_wall_per_file_s / 60, min) on a log axis of whole decades, in the unit of Fig 3 A; B: the batch /
    separate-file ratio (ratio_wall) on a log2 axis with a line at 1. One filled dot per engine, the engines present
    in a category dodged 0.22 (no empty slot where Sage has no batch, as FigS4): the ratio alone hides that a ProSE
    batch is still the fastest. A missing time is a label below A without an x (an x on the log time axis would read
    as fastest) and nothing in B; a missing ratio of a timed batch is an x with its label at B's base. "Sage: not
    run" (from O14) under the electron block, below A. Groups outside B3 are not marked (every dot is filled, as in
    Fig 3; the caption names them); index.tsv names them, and the design groups without a batch (left_out: one file,
    or pooled samples, SPEC 2.1 "Batch groups"). 7.0 x 4.4 in."""
    rows = tabs.need("O16_batch", ("engine", "group", "batch_wall_per_file_s", "ratio_wall", "note"))
    groups = ordered_groups(r["group"] for r in rows)
    engines = engines_in(rows)
    sage = [r for r in rows if r["engine"] == "sage"]
    own_not_run = {r["group"] for r in sage if "not_run_by_design" in (r["note"] or "")}
    not_run, nr_facts = sage_not_run(tabs, groups, {r["group"] for r in sage} - own_not_run, own_not_run)
    fig, axs = new_figure(plt, 4.4, 2, 1, sharex=True)
    ta, ra = axs[0][0], axs[1][0]
    tmarks, rmarks = Marks(ta), Marks(ra)
    times, ratios = [], [1.0]
    for x, g in enumerate(groups):
        by_engine = {e: [r for r in rows if r["group"] == g and r["engine"] == e]
                     for e in engines if not (e == "sage" and g in not_run)}  # one label for the block (G15)
        off = dodge([e for e in engines if by_engine.get(e)], 0.22)
        for e, sub in by_engine.items():
            style = dict(ls="none", marker="o", ms=DOT_MS, mfc=D.COLOUR[e], mec=D.COLOUR[e], mew=0.5, zorder=4)
            for r in sub:
                xe = x + off[e]
                t, v = num(r["batch_wall_per_file_s"]), num(r["ratio_wall"])
                label = reason_label(r["note"])
                timed = t is not None and t > 0
                if timed:
                    ta.plot([xe], [t / 60.0], **style)
                    times.append(t / 60.0)
                else:
                    tmarks.add(xe, label, D.COLOUR[e], mark=False)
                if v is not None and v > 0:
                    ra.plot([xe], [v], **style)
                    ratios.append(v)
                elif timed:  # an untimed batch already has its label between the panels: no x as "best ratio"
                    rmarks.add(xe, label, D.COLOUR[e])
    not_run_labels(tmarks, groups, range(len(groups)), not_run)
    ta.set_yscale("log")
    decade_limits(ta, times)
    log_ticks(ta)
    ra.set_yscale("log", base=2)
    log2_ticks(ra, ratios)
    ra.axhline(1, color="0.3", lw=0.7, zorder=1)
    tmarks.draw(mode="below", gap=2.5)
    rmarks.draw()
    ta.set_ylabel(VOCAB["batch_time"])
    ra.set_ylabel(VOCAB["batch_ratio"])
    blocks = draw_blocks(ta, groups, label=True)
    draw_blocks(ra, groups, label=False)
    title(ta, "", above_blocks=blocks, letter=0)
    title(ra, "", letter=1)
    dataset_axis(ra, groups)
    legend_rows(fig, engine_handles(engines))
    threads = sorted({r["threads"] for r in rows if "threads" in r and r["threads"] not in NA_TEXT})
    outside = sorted({r["group"] for r in rows if "in_B3" in r and not yes(r["in_B3"])}, key=D.order_key)
    fig.facts = {"threads": ",".join(threads) or "NA", **machine_facts(tabs),
                 "not_in_B3": ",".join(outside) or "none", **nr_facts}
    if any(g in D.ALL_GROUPS for g in groups):  # the caption says which design groups have no batch, and why
        fig.facts["left_out"] = left_out_fact(
            (g, "pooled samples: not in the batch arm" if D.kind(g) == "immuno" else
             "one file: no batch" if g not in D.BATCH_ORDER else "no row in O16")
            for g in D.ALL_GROUPS if g not in groups)
    return fig, f"2 panels, {len(groups)} x categories"


# ---------------------------------------------------------------- O17: thread scaling
def fig_scaling(plt, tabs):
    """O17 figure (SPEC 3.3; S6, D11): 2 x 2 over the thread count n (log2), letters A-D without headings: A wall
    time (min, log, whole decades), B speedup, C efficiency, D peak RSS. Every ideal line is grey (IDEAL) and dashed
    (4, 2): T_1 / n per engine in A, y = n in B, 1 in C; without T_1 the relative columns (speedup_rel,
    efficiency_rel) are drawn and the ideal from the smallest completed n is dotted. A grey band marks 16 threads, the
    main benchmark setting, in every panel. The engine node's per_file run of the same unit (the rows of the other
    machine, DS:671) is a white square at its own thread count, MAIN_RUN_OFFSET_PT points right of it; a count
    outside the grid gets a tick of its own (a row without a count: 16, or the largest grid point below 16). x ticks
    at every grid point, labelled at the powers of 2 and the largest grid point (minor ticks elsewhere). over_limit
    points are triangles at their lower bound, points without a value an x at the axis base. 7.0 x 4.6 in."""
    from matplotlib import ticker
    from matplotlib.lines import Line2D
    from matplotlib.transforms import offset_copy
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
        """The thread count at which an engine-node per_file point is drawn: its own."""
        n = num(r["threads"])
        if n is not None and n > 0:
            return n
        return 16 if 16 in grid or not grid else max([g for g in grid if g <= 16] or grid[:1])
    dashed, dotted = (0, (4, 2)), (0, (1, 1.5))
    fig, axs = new_figure(plt, 4.6, 2, 2, categorical=False, sharex=True)
    wa, sa, ea, ma = axs[0][0], axs[0][1], axs[1][0], axs[1][1]
    panels = (("wall", wa), ("speedup", sa), ("efficiency", ea), ("rss", ma))
    marks = {key: Marks(a) for key, a in panels}
    relative_used = over_used = missing_used = False
    reference_threads, reference_ns = set(), set()
    times = []  # the drawn times (points, lower bounds, squares, the ends of the ideal lines): whole decades around
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
                    times.append(lower / 60.0)
                    over_used = True
                else:
                    marks[key].add(n, None, col)
                    missing_used = True
        for key, a in panels:
            if series[key]:
                a.plot([n for n, _ in series[key]], [v for _, v in series[key]], color=col, marker="o",
                       ms=SCALING_DOT_MS, mew=SCALING_DOT_MEW, zorder=4)
        if series["wall"]:  # ideal T_1 / n, or T_n0 x n0 / n from n0 on without T_1 (dotted)
            n0, t0 = series["wall"][0]
            ns = [n for n in grid if n >= n0]
            wa.plot(ns, [t0 * n0 / n for n in ns], ls=dashed if n0 == 1 else dotted, zorder=2, **IDEAL)
            times.append(t0 * n0 / ns[-1])  # the ideal line ends inside the axes
            if not absolute and series["speedup"]:
                sa.plot(ns, [n / n0 for n in ns], ls=dotted, zorder=2, **IDEAL)
        times += [v for _, v in series["wall"]]
        for r in rows:  # the engine node's per_file run at its own thread count (O17 reference row, DS:671; Q25)
            if r["engine"] == e and r["machine"] != scaling_machine:
                n_ref = reference_n(r)
                for key, a in (("wall_med_s", wa), ("rss_med_gib", ma)):
                    v = num(r[key])
                    if v is not None and v > 0:
                        a.plot([n_ref], [v / 60.0 if key == "wall_med_s" else v], ls="none", marker="s", ms=3.6,
                               mfc="white", mec=col, mew=0.9, zorder=6,
                               transform=offset_copy(a.transData, fig=fig, x=MAIN_RUN_OFFSET_PT, units="points"))
                        a.update_datalim([(n_ref, v / 60.0 if key == "wall_med_s" else v)])  # in the y limits
                        if key == "wall_med_s":
                            times.append(v / 60.0)
                        threads = num(r["threads"])
                        reference_threads.add(f"{threads:g}" if threads is not None else "NA")
                        reference_ns.add(n_ref)
    if grid:
        sa.plot(grid, grid, ls=dashed, zorder=1, **IDEAL)
    ea.axhline(1, ls=dashed, zorder=1, **IDEAL)
    counts = sorted(set(grid) | reference_ns) or [1]
    largest = grid[-1] if grid else counts[-1]
    majors = [n for n in counts if n > 0 and (math.log2(n).is_integer() or n == largest)]
    minors = [n for n in counts if n not in majors]
    band = bool(grid) and grid[0] <= 16 <= counts[-1]
    for _, a in panels:
        a.set_xscale("log", base=2)
        a.xaxis.set_major_locator(ticker.FixedLocator(majors))
        a.xaxis.set_minor_locator(ticker.FixedLocator(minors))
        a.xaxis.set_major_formatter(ticker.FuncFormatter(lambda v, _: minus(f"{v:g}")))
        a.xaxis.set_minor_formatter(ticker.NullFormatter())
        if grid:
            a.set_xlim(grid[0] / 1.35, counts[-1] * 1.35)
        if band:  # the main benchmark's setting (D11: a band, no ring)
            a.axvspan(16 / 1.12, 16 * 1.12, zorder=0, **BAND_16)
    wa.set_yscale("log")
    decade_limits(wa, times)
    log_ticks(wa)
    sa.set_yscale("log", base=2)
    sa.yaxis.set_major_formatter(ticker.FuncFormatter(lambda v, _: minus(f"{v:g}")))
    ea.set_ylim(bottom=0)
    ma.set_ylim(bottom=0)
    for key, _ in panels:
        marks[key].draw()
    wa.set_ylabel(VOCAB["time"])
    sa.set_ylabel(VOCAB["speedup"])
    ea.set_ylabel(VOCAB["efficiency"])
    ma.set_ylabel(VOCAB["memory"])
    for a in (ea, ma):
        a.set_xlabel(VOCAB["threads"])
    for k, a in enumerate((wa, sa, ea, ma)):
        title(a, "", letter=k)
    hs = [Line2D([], [], ls=dashed, label=VOCAB["ideal"], **IDEAL)]
    if relative_used:
        hs.append(Line2D([], [], ls=dotted, label=VOCAB["ideal_relative"], **IDEAL))
    if over_used:
        hs.append(marker_handle(VOCAB["lower_bound"], "^", "0.3", ms=4.5))
    if missing_used:
        hs.append(marker_handle(VOCAB["missing_scaling"], "x", MISSING_COLOUR))
    if band:
        hs.append(patch_handle(VOCAB["main_threads"], BAND_16["color"]))
    if reference_threads:
        hs.append(marker_handle(VOCAB["main_run"], "s", "0.3", face="white"))
    legend_rows(fig, engine_handles(engines, line=True, ms=SCALING_DOT_MS + SCALING_DOT_MEW), hs)
    # the caption names the scaling run (S6c), from the table's header note ("scaling run(s): hfx_A2")
    runs = [m.group(1).strip() for note in tabs.notes("O17_scaling")
            for m in [re.search(r"scaling run\(s\): ([^;]+)", note)] if m]
    fig.facts = {"scaling_run": ",".join(runs) or "NA", "main_run_threads": ",".join(sorted(reference_threads)) or "NA",
                 **machine_facts(tabs)}
    return fig, f"4 panels, {len(grid)} grid points"


# ---------------------------------------------------------------- O10: low_memory
def fig_low_memory(plt, tabs):
    """O10 figure (SPEC 3.3; S7): A peak memory (GiB, with the 200 GiB line), B time per sample (min; O10's wall
    time is per sample, D17); letters A, B without headings; x the samples (donor and tissue, as Fig 4) in
    design.IMMUNO_ORDER; paired bars, standard mode filled against low-memory mode open (G7); a decision sample is
    drawn as any other sample (no mark of its own). The summary row (role not tuned/heldout/decision) is not a sample.
    index.tsv facts: the samples with identical counts and the peak memory maxima, over the samples that are not
    decision samples, as lowmem.identical_all (decision samples enter no summary). 7.0 x 3.0 in."""
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
    ticks = []
    for (_, s), r in zip(items, rows):
        donor, tissue = donor_of(s)
        ticks.append(f"{donor} {tissue}".strip())
    for k, (a, std, lm, scale, ylabel) in enumerate((
            (axs[0][0], "rss_std_gib", "rss_lm_gib", 1.0, VOCAB["memory"]),
            (axs[0][1], "wall_std", "wall_lm", 1 / 60.0, VOCAB["time_per_sample"]))):
        marks = Marks(a)
        for x, r in zip(xs, rows):
            # standard mode filled, low-memory mode an open bar (G7)
            for col, o, face, lw in ((std, -width / 2, colour, 0.6),
                                     (lm, width / 2, OPEN_BAR["color"], OPEN_BAR["lw"])):
                v = num(r[col])
                if v is None or v <= 0:
                    marks.add(x + o, reason_label(r["note"]), colour)
                    continue
                a.bar(x + o, v * scale, width=width, color=face, edgecolor=colour, lw=lw, zorder=2)
        if k == 0:
            cap_line(a)
            a.set_ylim(0, max(a.get_ylim()[1], D.CAP_GIB * 1.12))  # room for the cap label inside the axes
        else:
            a.set_ylim(bottom=0)
        marks.draw(mode="slot")
        a.set_ylabel(ylabel)
        title(a, "", letter=k)
        a.set_xticks(xs)
        a.set_xticklabels(ticks, rotation=90)
        a.tick_params(axis="x", length=0)
        a.set_xlim(xs[0] - 0.7, xs[-1] + 0.7)
        start = 0
        dataset_labels = []
        for i in range(1, len(items) + 1):  # dataset labels under the donors, with grade
            if i == len(items) or items[i][0] != items[start][0]:
                g = items[start][0]
                grade = D.grade(g)
                label = D.display(g).replace(" class", "\nclass") + (f", grade {grade}" if grade != "-" else "")
                dataset_labels.append(a.annotate(label, xy=((xs[start] + xs[i - 1]) / 2, 0),
                                                 xycoords=("data", "axes fraction"), xytext=(0, -24),
                                                 textcoords="offset points", ha="center", va="top"))
                if i < len(items):
                    a.axvline((xs[i - 1] + xs[i]) / 2, zorder=0, **SEPARATOR)
                start = i
        later(fig, lambda a=a, labels=dataset_labels: below_ticks(a, labels))
    legend_rows(fig, [patch_handle(VOCAB["low_memory_std"], colour),
                      patch_handle(VOCAB["low_memory_lm"], OPEN_BAR["color"], colour, lw=OPEN_BAR["lw"])])
    # the caption's facts over the samples that are not decision samples, as the key lowmem.identical_all: decision
    # samples are drawn, but enter no summary
    use = [r for r in rows if r["role"] != "decision"]
    identical = [r for r in use if "identical" in r]
    std_max = max((num(r["rss_std_gib"]) for r in use if num(r["rss_std_gib"]) is not None), default=None)
    lm_max = max((num(r["rss_lm_gib"]) for r in use if num(r["rss_lm_gib"]) is not None), default=None)
    fig.facts = {"identical": f"{sum(yes(r['identical']) for r in identical)}/{len(identical)}" if identical else "NA",
                 "rss_std_max_gib": "NA" if std_max is None else f"{std_max:.1f}",
                 "rss_lm_max_gib": "NA" if lm_max is None else f"{lm_max:.1f}"}
    return fig, f"2 panels, {len(items)} x categories"


# ---------------------------------------------------------------- O19: calibration
def arm_name(text):
    """'per_file' / 'main' -> 'main'; 'per_file_cal_off' / 'cal_off' -> 'cal_off'."""
    s = (text or "").strip()
    if s in ("per_file", "main", ""):
        return "main"
    return s[len("per_file_"):] if s.startswith("per_file_") else s


def fig_calibration(plt, tabs):
    """O19 figure (SPEC 3.4, optional; S8): four full-width rows over the calibration runs in design order (class
    blocks named above A, the grade row under D), shared x, letters A-D: A and B the change of the target-decoy PSMs and
    peptides against the same engine's default settings, 100 x (ratio_to_main - 1) in % (G17), on one y range with one
    tick step (G10; a change that looks equal in A and B is equal), a missing value labelled at the zero line; C and D
    the shuffled entrapment FDP mean +- SD of every engine
    and arm at PSM and peptide level on one fdp_axis, natural entrapment (velos) as an open diamond. Colour by engine,
    marker by arm (CAL_MARKER: a triangle is "no mass calibration", down for ProSE, up for MSFragger), each arm at the
    same x in all four rows (A and B leave the default slots empty); the natural diamond stands NATURAL_BESIDE_PT
    points right of its arm marker. Legend: the engines, then the arms, the mean +- SD mark and the diamond. index.tsv
    facts: the run of each column (O19's units, in x order) and the runs per dataset. 7.0 x 6.4 in."""
    from matplotlib.transforms import offset_copy
    rows = tabs.need("O19_calibration_counts", ("unit", "group", "engine", "arm", "level", "ratio_to_main",
                                                "fdp_shuffled_mean", "fdp_shuffled_sd", "fdp_natural", "status"))
    units = []
    for r in rows:
        if (r["group"], r["unit"]) not in units:
            units.append((r["group"], r["unit"]))
    order = {u: i for i, u in enumerate(D.CAL_RUNS)}
    units.sort(key=lambda gu: (D.order_key(gu[0]), order.get(gu[1], len(order)), gu[1]))
    groups = [g for g, _ in units]
    levels = [lv for lv in D.LEVELS if any(r["level"] == lv for r in rows)]
    slots = list(CAL_SLOTS) + sorted({(r["engine"], arm_name(r["arm"])) for r in rows} - set(CAL_SLOTS))
    slots = [s for s in slots if any(r["engine"] == s[0] and arm_name(r["arm"]) == s[1] for r in rows)]
    index = {(r["unit"], r["engine"], arm_name(r["arm"]), r["level"]): r for r in rows}
    panels = [("change", lv) for lv in levels] + [("fdp", lv) for lv in levels]
    fig, axs = new_figure(plt, 6.4, len(panels), 1, sharex=True)
    ranges, fdp_values, natural_used, shuffled_used, zero_labels = [], [], False, False, []
    off = dodge(slots, 0.8 / max(len(slots), 1))  # one x per arm in all four rows: a reader reads down a column
    for k, (what, level) in enumerate(panels):
        ax = axs[k][0]
        use = [s for s in slots if s[1] != "main"] if what == "change" else slots
        marks = Marks(ax)
        values = [0.0]
        for x, (g, u) in enumerate(units):
            for slot in use:
                e, arm = slot
                r = index.get((u, e, arm, level))
                if r is None:
                    continue
                xe, col, marker = x + off[slot], D.COLOUR.get(e, "0.3"), CAL_MARKER.get(arm, "P")
                if what == "change":
                    v = num(r["ratio_to_main"])
                    if v is None:  # a lead axis: the reason at the zero line, no x (placed once the limits are set)
                        zero_labels.append((ax, xe, reason_label(r["status"])))
                    else:
                        ax.plot([xe], [100 * (v - 1)], ls="none", marker=marker, mfc=col, mec=col, zorder=4,
                                **CAL_MARK)
                        values.append(100 * (v - 1))
                    continue
                mean, sd, nat = num(r["fdp_shuffled_mean"]), num(r["fdp_shuffled_sd"]), num(r["fdp_natural"])
                if mean is not None:
                    ax.errorbar([xe], [100 * mean], yerr=None if sd is None else [100 * sd], fmt=marker, ms=3.2,
                                mfc=col, mec=col, mew=0.5, ecolor=col, elinewidth=0.6, capsize=0, zorder=4)
                    fdp_values.append(100 * (mean + (sd or 0.0)))
                    shuffled_used = True
                if nat is not None:  # beside its arm marker, not on the SD bar (under the marker if they meet)
                    ax.plot([xe], [100 * nat], ls="none", mec=col, zorder=3,
                            transform=offset_copy(ax.transData, fig=fig, x=NATURAL_BESIDE_PT, units="points"),
                            **NATURAL)
                    fdp_values.append(100 * nat)
                    natural_used = True
                if mean is None and nat is None:
                    marks.add(xe, reason_label(r["status"]), col)
        if what == "change":
            ax.axhline(0, zorder=2.5, **ZERO_LINE)
            ranges.append((min(values), max(values)))
        else:
            one_percent_line(ax)
        marks.draw()
        blocks = draw_blocks(ax, groups, label=(k == 0))
        title(ax, "", above_blocks=blocks, letter=k)
    change_axes = [axs[k][0] for k, (what, _) in enumerate(panels) if what == "change"]
    if ranges:  # one range for A and B: the rows share x and invite a look from A to B
        ranges = [(min(lo for lo, _ in ranges), max(hi for _, hi in ranges))] * len(ranges)
    step = tick_step(change_axes, ranges) if change_axes else None
    for ax, xe, text in zero_labels:  # vertical, on the side of the zero line with more room (inside the axes)
        lo, hi = ax.get_ylim()
        down = hi < -lo
        ax.annotate(text, xy=(xe, 0), xytext=(0, -3 if down else 3), textcoords="offset points", rotation=90,
                    ha="center", va="top" if down else "bottom", color="0.25")
    for k, (what, level) in enumerate(panels):
        if what == "change":
            axs[k][0].set_ylabel(VOCAB["change_level"].format(LEVEL_UNIT[level]))
        else:
            fdp_axis(axs[k][0], fdp_values)
            axs[k][0].set_ylabel(VOCAB["fdp_level"].format(LEVEL_NAME[level]))
    category_axis(axs[-1][0], range(len(units)), unit_labels(units), groups)
    axs[-1][0].set_xlim(-0.6, len(units) - 0.4)
    # legend order CAL_LEGEND: the two "no mass calibration" triangles side by side when the encodings wrap
    arms = sorted(dict.fromkeys(arm for _, arm in slots),
                  key=lambda a: CAL_LEGEND.index(a) if a in CAL_LEGEND else len(CAL_LEGEND))
    # the arm shapes at the size of the change rows' markers, as the engine dots near their size
    row2 = [marker_handle(CAL_LABEL.get(arm, arm), CAL_MARKER.get(arm, "P"), "0.3", **CAL_MARK) for arm in arms]
    if shuffled_used:  # the SD bars of C and D, as in Fig 2, FigS4 and FigS5
        row2.append(errorbar_handle(VOCAB["shuffled"]))
    if natural_used:
        row2.append(natural_handle())
    legend_rows(fig, engine_handles([e for e in D.ENGINES if any(s[0] == e for s in slots)]), row2)
    # the caption says that each column is one run of its dataset (the tick labels name the dataset)
    per = [groups.count(g) for g in dict.fromkeys(groups)]
    fig.facts = {"units": len(units), "runs": ",".join(u for _, u in units),
                 "runs_per_dataset": f"{min(per)}" if min(per) == max(per) else f"{min(per)} to {max(per)}",
                 "arms": ",".join(f"{e}:{arm}" for e, arm in slots),
                 "tick_step": "NA" if step is None else f"{step:g}"}
    return fig, f"{len(panels)} panels, {len(units)} x categories"


# ---------------------------------------------------------------- the figure index (SPEC 3.7)
FIGURES = (
    ("fig_ids_panels_psm", fig_ids_panels, ("psm",)),
    ("fig_ids_panels_peptide", fig_ids_panels, ("peptide",)),
    ("fig_overtuning_psm", fig_overtuning, ("psm",)),
    ("fig_overtuning_peptide", fig_overtuning, ("peptide",)),
    ("fig_ids_counts_psm", fig_ids_counts, ("psm",)),
    ("fig_ids_counts_peptide", fig_ids_counts, ("peptide",)),
    ("fig_electron", fig_electron, ()),
    ("fig_immuno", fig_immuno, ()),
    ("fig_fdp", fig_fdp, ()),
    ("fig_fdp_main", fig_fdp_main, ()),
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

# the paper's numbers (O1): code name -> (folder under figures/, file stem). A skipped figure leaves a gap; nothing is
# renumbered. Moving a figure between main and supplement is one line here. Since 2026-11-28 (owner) Fig 1 is the
# panel figure of the identifications (fig_ids_panels_psm, its peptide version FigS1); the lead figures moved to FigS2
# and FigS3. fig_ids_counts_psm and _peptide (the log count figures, FigS2 and FigS3 before) are still drawn as
# fig_ids_counts_*.pdf/.png but have no paper number (index.tsv: number '-').
PAPER_FIGURES = {
    "fig_ids_panels_psm": ("main", "Fig1_identifications"),
    "fig_fdp_main": ("main", "Fig2_entrapment_fdp"),
    "fig_time_per_file": ("main", "Fig3_time_memory"),
    "fig_immuno": ("main", "Fig4_immunopeptidomics"),
    "fig_ids_panels_peptide": ("supplement", "FigS1_identifications_peptide"),
    "fig_overtuning_psm": ("supplement", "FigS2_overtuning_psm"),
    "fig_overtuning_peptide": ("supplement", "FigS3_overtuning_peptide"),
    "fig_fdp": ("supplement", "FigS4_entrapment_fdp_full"),
    "fig_electron": ("supplement", "FigS5_electron"),
    "fig_batch": ("supplement", "FigS6_batch"),
    "fig_scaling": ("supplement", "FigS7_scaling"),
    "fig_low_memory": ("supplement", "FigS8_low_memory"),
    "fig_calibration": ("supplement", "FigS9_calibration"),
    "fig_matched_fdp": ("supplement", "FigS10_matched_fdp"),
    "fig_ext_percolator": ("supplement", "FigS11_external_percolator"),
    "fig_prediction": ("supplement", "FigS12_prediction"),
}
# the must-say caption items of FIGURES_CAMERA_READY.md section 2 and 3, for the caption writer (index.tsv). F1.3
# and "S1,F1.3" moved with the lead figures to FigS2 and FigS3; F1new and S1new are the new Fig 1 and FigS1 (README
# "Figures" lists what they must say; the spec has no section for them yet)
CAPTION_KEYS = {
    "fig_ids_panels_psm": "F1new", "fig_ids_panels_peptide": "S1new",
    "fig_overtuning_psm": "F1.3", "fig_fdp_main": "F2.2", "fig_time_per_file": "F3.4", "fig_immuno": "F4.3,F4.5",
    "fig_overtuning_peptide": "S1,F1.3", "fig_ids_counts_psm": "S2c", "fig_ids_counts_peptide": "S2c",
    "fig_fdp": "S3,F2.2", "fig_electron": "S4", "fig_batch": "S5", "fig_scaling": "S6c", "fig_low_memory": "S7b",
    "fig_calibration": "S8b", "fig_matched_fdp": "S9", "fig_ext_percolator": "S10", "fig_prediction": "S10",
}
