#!/usr/bin/env python3
"""Summaries of the benchmark tables: every number, table and figure of the paper (DATASETS.md section 4.5).

The specification is checks/analysis_validation/design/SPEC.md (v2) outside the repository; section numbers below
refer to it. Citation keys: DS = datasets/DATASETS.md, B = benchmarks/bench.py, OT = benchmarks/overtuning.py.

  python3 -B summarize.py --work W [--out O]          tables, numbers.tsv/.tex, provenance, check report, figures
  python3 -B summarize.py --work W --no-figures       the same without figures (no matplotlib needed)
  python3 -B summarize.py --figures-only --out O      figures from O/tables/*.tsv only (e.g. in WSL on a copy)
  python3 -B summarize.py --test                      the unit tests (benchmarks/summaries/tests)
  python3 -B summarize.py --print-light-copy-filter   rsync filter rules for a light copy of W

Order of a build (SPEC 1, module contract): tables.load() builds the context (exit 2 on a validation stop); then
fdp.build, ids.build, timing.build and calib.build; then checks.run; then numbers.tsv, numbers.tex and
provenance.tsv; then, unless --no-figures, figures.draw, which reads only the written tables. Each module is imported
lazily: an import error or an exception becomes the report line 'FAIL MODULE <name>: <exception>' with the traceback
in <out>/errors.txt, and the build goes on.

Exit codes (SPEC 1): 2 an input validation stop; 1 any FAIL in the check report; 0 otherwise.
"""
import argparse
import datetime
import importlib
import importlib.util
import os
import platform
import re
import subprocess
import sys
import traceback
import unittest

sys.dont_write_bytecode = True  # SPEC 1: no bytecode in the repository (as B:102-105); run with python3 -B as well

HERE = os.path.dirname(os.path.abspath(__file__))  # benchmarks
REPO = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from summaries import tables  # noqa: E402  (after sys.dont_write_bytecode, SPEC 1)

MODULES = ("fdp", "ids", "timing", "calib")  # the order of the module contract
STALE_TABLE = re.compile(r"^O\d\d[a-z]?_.+\.(tsv|txt)$")
NUMBERS_COLUMNS = ("key", "value", "text", "unit", "output", "protocol_ref", "source_side", "main_text_allowed")
NUM_MACRO = (r"\newcommand{\Num}[1]{\ifcsname num@#1\endcsname\csname num@#1\endcsname\else"
             r"\PackageError{numbers}{unknown key #1}{}\fi}")
TEX_SPECIAL = {"\\": r"\textbackslash{}", "{": r"\{", "}": r"\}", "%": r"\%", "#": r"\#", "&": r"\&", "_": r"\_",
               "$": r"\$", "^": r"\textasciicircum{}", "~": r"\textasciitilde{}"}

# SPEC 1 "Where it runs": the tables, versions.txt, commands.log and, per search folder, status, inputs, *.log,
# summary.yaml, sage.json, fragger.params. Use as: rsync -am --filter='merge FILTER' W/ COPY/
LIGHT_COPY_FILTER = """\
# light copy of a work folder W for summarize.py (SPEC 1): rsync -am --filter='merge <this file>' W/ COPY/
+ /counts.tsv
+ /coverage.tsv
+ /timings.tsv
+ /versions.txt
+ /commands.log
+ /overtuning_*.tsv
+ /counts_qgrid.tsv
+ /out/
+ /out/**/
+ /out/**/status
+ /out/**/count_qgrid.sha256
+ /out/**/inputs
+ /out/**/*.log
+ /out/**/summary.yaml
+ /out/**/sage.json
+ /out/**/fragger.params
- *
"""


def parse_args(argv):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--work", help="work folder W: counts.tsv, coverage.tsv, timings.tsv, versions.txt, optional out/, "
                                  "commands.log, overtuning_<level>.tsv, counts_qgrid.tsv")
    p.add_argument("--runs", default=os.path.join(HERE, "runs.tsv"), help="run table (default benchmarks/runs.tsv); "
                   "benchmarks/smoke/runs.tsv needs --design none")
    p.add_argument("--runs-11b", help="the task-11b run table (DS:1056); default benchmarks/pooled_rule_runs.tsv if it "
                                      "exists")
    p.add_argument("--rule11b-work", help="work folder of task 11b, for O9b (OPEN Q45)")
    p.add_argument("--out", help="output folder (default W/summary)")
    p.add_argument("--scaling-work", help="folder with the scaling node's timings.tsv, coverage.tsv, versions.txt; only "
                                          "benchmark == scaling rows are read from it (default W; OPEN Q35)")
    p.add_argument("--machine", action="append", default=[], metavar="LABEL=PATH",
                   help="node_prep/machine.txt of a node (PN:30), for O18; repeatable (OPEN Q64)")
    p.add_argument("--gc-logs", help="MSFragger GC logs, for O15 (OPEN Q48)")
    p.add_argument("--level", default="both", choices=("psm", "peptide", "both"))
    p.add_argument("--only", help="comma list of " + ", ".join(tables.ONLY_KEYWORDS) + "; checks always run")
    p.add_argument("--logs", default="auto", choices=("yes", "no", "auto"),
                   help="read W/out/** logs, summary.yaml, sage.json, fragger.params when present")
    p.add_argument("--references", default=tables.DEFAULT_REFERENCES, help="published values (OPEN Q12, Q47)")
    p.add_argument("--mzml-counts", default=tables.DEFAULT_MZML_COUNTS, help="for O23")
    p.add_argument("--design", default="paper", choices=("paper", "none"),
                   help="none: groups unknown to design.py become kind other, role optional (smoke test)")
    p.add_argument("--strict", action="store_true", help="final-run mode: the WARNs marked (s) become FAILs")
    p.add_argument("--expect-threads", type=int, help="thread count of per_file, its arms and batch (strict: 16)")
    p.add_argument("--listing", help="an 'ls -l' listing of W (e.g. work.ls), for C18 on copies")
    p.add_argument("--figures-only", action="store_true", help="draw the figures from <out>/tables/*.tsv only")
    p.add_argument("--no-figures", action="store_true")
    p.add_argument("--print-light-copy-filter", action="store_true",
                   help="print the rsync filter rules of the light copy and exit")
    p.add_argument("--test", action="store_true", help="run the unit tests and exit")
    a = p.parse_args(argv)
    if a.only:
        a.only = tuple(x.strip() for x in a.only.split(",") if x.strip())
        bad = [x for x in a.only if x not in tables.ONLY_KEYWORDS]
        if bad:
            p.error(f"--only: unknown {', '.join(bad)}; allowed: {', '.join(tables.ONLY_KEYWORDS)}")
    machines = []
    for m in a.machine:
        label, sep, path = m.partition("=")
        if not sep or not label or not path:
            p.error(f"--machine {m!r}: expected LABEL=PATH")
        machines.append((label, path))
    a.machine = machines
    if not (a.test or a.print_light_copy_filter):
        if a.figures_only:
            if not a.out and not a.work:
                p.error("--figures-only needs --out (or --work for W/summary)")
        elif not a.work:
            p.error("--work is required (except with --figures-only, --test, --print-light-copy-filter)")
    if a.figures_only and a.no_figures:
        p.error("--figures-only and --no-figures exclude each other")
    return a


# ---------------------------------------------------------------- --test
def run_tests():
    """unittest discovery on benchmarks/summaries/tests with top_level_dir=benchmarks (SPEC 1, 6)."""
    loader = unittest.TestLoader()
    suite = loader.discover(os.path.join(HERE, "summaries", "tests"), pattern="test*.py", top_level_dir=HERE)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


# ---------------------------------------------------------------- output writers
def tex_escape(text):
    return "".join(TEX_SPECIAL.get(ch, ch) for ch in str(text))


def value_text(v):
    """numbers.tsv value column: full precision (repr) for floats (SPEC 3.8)."""
    if v is None or isinstance(v, tables.Missing):
        return "NA"
    if isinstance(v, bool):
        return "yes" if v else "no"
    if isinstance(v, float):
        return "NA" if v != v else repr(v)
    return str(v)


def write_numbers(ctx, out):
    """numbers.tsv and numbers.tex (SPEC 3.8). Two keys equal after normalisation stop the run (exit 2)."""
    seen = {}
    for n in ctx.numbers:
        norm = n.key.strip().lower()
        if norm in seen:
            raise tables.ValidationStop(f"numbers: keys {seen[norm]!r} and {n.key!r} are equal after normalisation "
                                        "(SPEC 3.8)")
        seen[norm] = n.key
    lines = ["\t".join(NUMBERS_COLUMNS)]
    for n in ctx.numbers:
        lines.append("\t".join([n.key, value_text(n.value), n.text, n.unit, n.output, n.protocol_ref, n.source_side,
                                n.main_text_allowed]))
    tables.write_atomic(os.path.join(out, "numbers.tsv"), "\n".join(lines) + "\n")
    tex = ["% numbers.tex written by benchmarks/summarize.py (SPEC 3.8); use \\Num{<key>} in the text",
           NUM_MACRO]
    tex += [f"\\expandafter\\def\\csname num@{n.key}\\endcsname{{{tex_escape(n.text)}}}" for n in ctx.numbers]
    tables.write_atomic(os.path.join(out, "numbers.tex"), "\n".join(tex) + "\n")


def repo_head():
    """git -C <repo> rev-parse HEAD, or 'NA (<first line of git's message>)' (SPEC 1: provenance without git)."""
    try:
        r = subprocess.run(["git", "-C", REPO, "rev-parse", "HEAD"], capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError) as err:
        return f"NA ({str(err).splitlines()[0] if str(err) else err.__class__.__name__})"
    if r.returncode == 0 and r.stdout.strip():
        return r.stdout.strip()
    msg = (r.stderr or r.stdout or f"exit {r.returncode}").strip().splitlines()
    return f"NA ({msg[0] if msg else 'exit ' + str(r.returncode)})"


def clean(text):
    return " ".join(str(text).split())


def write_provenance(ctx, out, command_line):
    """provenance.tsv (SPEC 1): every input path, size, SHA256, mtime; the repository HEAD; the command line;
    POOLED_ARRANGEMENT and its parameter files."""
    rows = [("item", "path", "size", "sha256", "mtime", "value")]
    rows.append(("command_line", "", "", "", "", clean(command_line)))
    rows.append(("repo_head", REPO, "", "", "", clean(repo_head())))
    rows.append(("python", sys.executable, "", "", "", clean(platform.python_version())))
    rows.append(("design", "", "", "", "", ctx.design_mode))
    rows.append(("levels", "", "", "", "", ",".join(ctx.levels)))
    rows.append(("only", "", "", "", "", ",".join(ctx.only) if ctx.only else "all"))
    rows.append(("logs_available", ctx.out_dir or "", "", "", "", "yes" if ctx.logs_available else "no"))
    rows.append(("pooled_arrangement", "", "", "", "", str(ctx.pooled_arrangement)))
    for p, mode in ctx.pooled_arrangement_files:
        rows.append(("pooled_arrangement_file", p, "", "", "", str(mode)))
    for path, item in ctx.inputs.items():
        st = os.stat(path)
        mtime = datetime.datetime.fromtimestamp(st.st_mtime, datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        rows.append(("input " + item, path, str(st.st_size), tables.sha256_file(path), mtime, ""))
    tables.write_atomic(os.path.join(out, "provenance.tsv"), "".join("\t".join(map(clean, r)) + "\n" for r in rows))


def write_report(report, path):
    lv = {x: report.count(x) for x in tables.Report.LEVELS}
    report.check("INFO", "SUMMARY", f"{lv['PASS']} PASS, {lv['WARN']} WARN, {lv['FAIL']} FAIL, {lv['INFO']} INFO"
                                    f"{' (strict)' if report.strict else ''}")
    tables.write_atomic(path, report.text())


# ---------------------------------------------------------------- module calls
def call_module(name, func, args, report, errors):
    """Imports summaries.<name> lazily and calls func(*args). A ValidationStop propagates (exit 2); any other error
    becomes 'FAIL MODULE <name>: <exception>' with the traceback in errors.txt (module contract)."""
    try:
        mod = importlib.import_module("summaries." + name)
        getattr(mod, func)(*args)
        return True
    except tables.ValidationStop:
        raise
    except BaseException as err:  # ImportError, SyntaxError, any exception of the module
        if isinstance(err, (KeyboardInterrupt, SystemExit)) and not isinstance(err, tables.ValidationStop):
            raise
        report.check("FAIL", "MODULE", f"{name}: {err.__class__.__name__}: {err}")
        errors.append(f"== module {name} ({func})\n{traceback.format_exc()}")
        return False


def draw_figures(tables_dir, figures_dir, report, errors):
    if importlib.util.find_spec("matplotlib") is None:
        report.check("WARN", "FIGURES", "matplotlib not found: figures skipped, tables are built (SPEC 1)")
        return
    os.environ.setdefault("MPLBACKEND", "Agg")
    os.makedirs(figures_dir, exist_ok=True)
    call_module("figures", "draw", (tables_dir, figures_dir, report), report, errors)


def write_errors(out, errors):
    tables.write_atomic(os.path.join(out, "errors.txt"), "\n".join(errors) + ("\n" if errors else ""))


def figures_only(a, command_line):
    out = a.out or os.path.join(a.work, "summary")
    tables_dir = os.path.join(out, "tables")
    report = tables.Report(strict=a.strict)
    errors = []
    if not os.path.isdir(tables_dir):
        report.check("FAIL", "FIGURES", f"no tables folder {tables_dir}")
    else:
        report.check("INFO", "FIGURES", f"--figures-only from {tables_dir}")
        draw_figures(tables_dir, os.path.join(out, "figures"), report, errors)
    # its own report file, so the build's check_report.txt is kept
    write_report(report, os.path.join(out, "check_report_figures.txt"))
    if errors:
        tables.write_atomic(os.path.join(out, "errors_figures.txt"), "\n".join(errors) + "\n")
    sys.stdout.write(report.text())
    return 1 if report.n_fail else 0


def build(a, command_line):
    out = a.out or os.path.join(a.work, "summary")
    runs_11b = a.runs_11b
    if runs_11b is None and os.path.exists(tables.DEFAULT_RUNS_11B):
        runs_11b = tables.DEFAULT_RUNS_11B
    options = tables.Options(
        runs=a.runs, work=a.work, scaling_work=a.scaling_work, runs_11b=runs_11b, rule11b_work=a.rule11b_work,
        out=out, design=a.design, levels=tables.LEVELS if a.level == "both" else (a.level,), only=a.only,
        logs=a.logs, strict=a.strict, expect_threads=a.expect_threads, references=a.references,
        mzml_counts=a.mzml_counts, listing=a.listing, machines=tuple(a.machine), gc_logs=a.gc_logs,
        command_line=command_line)
    os.makedirs(out, exist_ok=True)
    try:
        ctx = tables.load(options)
    except tables.ValidationStop as err:
        report = tables.Report(strict=a.strict)
        report.check("FAIL", "STOP", err.message)
        write_report(report, os.path.join(out, "check_report.txt"))
        sys.stderr.write(f"validation stop: {err.message}\n")
        return 2
    report, errors = ctx.report, []
    tables_dir = ctx.tables_dir
    os.makedirs(tables_dir, exist_ok=True)  # figures.draw always gets an existing (possibly empty) tables folder
    before = set(x for x in os.listdir(tables_dir) if STALE_TABLE.match(x))
    try:
        for name in MODULES:
            call_module(name, "build", (ctx,), report, errors)
        call_module("checks", "run", (ctx,), report, errors)
        written = set(x for x in os.listdir(tables_dir) if STALE_TABLE.match(x)) if os.path.isdir(tables_dir) \
            else set()
        rewritten = {n + ".tsv" for n in ctx.results}
        stale = sorted(x for x in before if x not in rewritten and x in written and not _written_now(ctx, x))
        if stale and ctx.only is None:
            for x in stale:  # tables of an earlier build that this full build did not write: figures must not read them
                os.remove(os.path.join(tables_dir, x))
            report.check("INFO", "STALE", f"{len(stale)} table(s) of an earlier build removed: {', '.join(stale)}")
        elif stale:
            report.check("INFO", "STALE", f"{len(stale)} table(s) of an earlier build kept (--only): "
                                          f"{', '.join(stale)}")
        write_numbers(ctx, out)
        write_provenance(ctx, out, command_line)
    except tables.ValidationStop as err:
        report.check("FAIL", "STOP", err.message)
        write_report(report, os.path.join(out, "check_report.txt"))
        write_errors(out, errors)
        sys.stderr.write(f"validation stop: {err.message}\n")
        return 2
    if not a.no_figures:
        try:
            draw_figures(tables_dir, ctx.figures_dir, report, errors)
        except tables.ValidationStop as err:
            report.check("FAIL", "STOP", err.message)
            write_report(report, os.path.join(out, "check_report.txt"))
            write_errors(out, errors)
            return 2
    write_errors(out, errors)
    write_report(report, os.path.join(out, "check_report.txt"))
    sys.stdout.write(report.text())
    return 1 if report.n_fail else 0


def _written_now(ctx, filename):
    """A non-TSV output written by a module in this build (e.g. tables/O04_overtuning_psm.stdout.txt) is recorded in
    ctx.shared['written'] by Ctx.write_file."""
    return os.path.join("tables", filename) in ctx.shared.get("written", ())


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    a = parse_args(argv)
    if a.print_light_copy_filter:
        sys.stdout.write(LIGHT_COPY_FILTER)
        return 0
    if a.test:
        return run_tests()
    command_line = " ".join(["python3", "-B", os.path.abspath(__file__)] + list(argv))
    if a.figures_only:
        return figures_only(a, command_line)
    return build(a, command_line)


if __name__ == "__main__":
    sys.exit(main())
