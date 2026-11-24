"""Writes the base fixtures of SPEC 6 (made-up numbers in the driver's formats): runs_fx, runs_smoke_fx, params_fx/,
counts/coverage/timings _fx, _wnode_fx, _smoke_fx, _overlimit_fx. The files are committed; rerun only to change them.
Run: python3 -B make_fixtures.py [<out dir>]   (default: the folder of this file)"""
import math
import os
import sys

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
os.makedirs(os.path.join(OUT, "params_fx"), exist_ok=True)
URL = "https://example.org/fixture"
S123 = ";".join(f"{{db}}_entrap_s{i}_td.fasta" for i in (1, 2, 3))

# id set group format params db entrap ref ions sample scaling role
RUNS = [
    ("velos_r1", "tuned", "velos", "raw", "main_velos_cid", "hy", "hy_velos_natural_td.fasta;" + S123, "-", "by", "-", "0", "tuned"),
    ("lumos_tmt_r1", "tuned", "lumos_tmt", "raw", "main_lumos_tmt6_cid", "hy", S123, "-", "by", "-", "0", "tuned"),
    ("hfx_r1", "tuned", "hfx", "raw", "main_highres", "hye", S123, "hye_arath_td.fasta", "by", "-", "1", "tuned"),
    ("lumos_lfq_r1", "tuned", "lumos_lfq", "raw", "main_highres", "hy", S123, "-", "by", "-", "0", "tuned"),
    ("eclipse_tmtpro_r1", "tuned", "eclipse_tmtpro", "raw", "main_exploris_tmtpro", "human", S123, "human_arath_td.fasta", "by", "-", "0", "tuned"),
    ("astral_r1", "tuned", "astral", "raw", "main_highres", "hye", S123, "hye_arath_td.fasta", "by", "-", "0", "tuned"),
    ("tims_plasma_r1", "tuned", "tims_plasma", "d.zip", "main_highres", "human", S123, "-", "by", "-", "0", "tuned"),
    ("pxd011695_HCD_r1", "heldout", "pxd011695_HCD", "raw", "pxd011695_elite_itms", "pxd011695_mouse", S123, "-", "by", "-", "0", "heldout"),
    ("pxd011695_ETciD_r1", "heldout", "pxd011695_ETciD", "raw", "pxd011695_elite_itms", "pxd011695_mouse", S123, "-", "bycz", "-", "0", "heldout"),
    ("astral_s1_r1", "heldout", "astral_s1", "raw", "main_highres", "hye", "hye_s1_natural_td.fasta", "-", "by", "-", "0", "heldout"),
    ("pxd042233_r1", "heldout", "pxd042233_lumos_cid", "raw", "pxd042233_lumos_cid", "pxd042233_human", S123, "-", "by", "-", "0", "heldout"),
    ("iprg2015_r1", "heldout", "iprg2015", "raw", "iprg2015_qe", "iprg2015", S123, "-", "by", "-", "0", "heldout"),
    ("DN05_r1", "heldout", "pxd058436_classI", "d.tar.gz", "immuno_per_file", "pxd058436", "-", "-", "by", "pxd058436_DN05", "0", "heldout"),
    ("DN05_r2", "heldout", "pxd058436_classI", "d.tar.gz", "immuno_per_file", "pxd058436", "-", "-", "by", "pxd058436_DN05", "0", "heldout"),
    ("DN13_r1", "heldout", "pxd058436_classI", "d.tar.gz", "immuno_per_file", "pxd058436", "-", "-", "by", "pxd058436_DN13", "0", "decision"),
    ("DN13_r2", "heldout", "pxd058436_classI", "d.tar.gz", "immuno_per_file", "pxd058436", "-", "-", "by", "pxd058436_DN13", "0", "decision"),
    ("p19_DN05_r1", "heldout", "pxd019643_classI", "raw", "immuno_per_file", "pxd019643", "-", "-", "by", "pxd019643_DN05", "0", "heldout"),
    ("astral250pg_A2", "heldout", "astral_250pg", "raw", "main_highres", "hye", S123, "-", "by", "-", "0", "decision"),
    ("astral250pg_B1", "heldout", "astral_250pg", "raw", "main_highres", "hye", S123, "-", "by", "-", "0", "heldout"),
    ("astral250pg_B3", "heldout", "astral_250pg", "raw", "main_highres", "hye", S123, "-", "by", "-", "0", "heldout"),
    ("ups1_r1", "heldout", "ups1_control", "raw", "main_velos_cid", "hy", "hy_velos_natural_td.fasta", "-", "by", "-", "0", "heldout"),
    ("ultra2_hye_r1", "heldout", "ultra2_hye", "d.zip", "main_highres", "hye", S123, "-", "by", "-", "0", "heldout"),
    ("ultra2_s2_r1", "heldout", "ultra2_s2", "d.zip", "main_highres", "hye", "hye_s1_natural_td.fasta", "-", "by", "-", "0", "heldout"),
    ("hela_exploris480_r1", "heldout", "hela_exploris480", "raw", "main_highres", "pxd042233_human", S123, "-", "by", "-", "0", "heldout"),
    ("hela_qe_hf_r1", "heldout", "hela_qe_hf", "raw", "main_highres", "pxd042233_human", S123, "-", "by", "-", "0", "heldout"),
]
RUNS = [r[:6] + (r[6].format(db=r[5]),) + r[7:] for r in RUNS]
COLS = "id set group format url params db entrap ref ions sample scaling role".split()


def write(name, header, rows, crlf=False):
    nl = "\r\n" if crlf else "\n"
    with open(os.path.join(OUT, name), "w", encoding="utf-8", newline="") as f:
        f.write("\t".join(header) + nl)
        for r in rows:
            f.write("\t".join(str(x) for x in r) + nl)


write("runs_fx.tsv", COLS, [r[:4] + (URL,) + r[4:] for r in RUNS], crlf=True)
SMOKE = [("bsa1", "1"), ("bsa2", "0"), ("bsa3", "0")]
write("runs_smoke_fx.tsv", COLS[:-1], [(i, "smoke", "smoke", "mzML", URL, "main_velos_cid", "smoke", "smoke_entrap_td.fasta",
                                        "-", "by", "-", s) for i, s in SMOKE], crlf=True)

INI = """<?xml version='1.0' encoding='ISO-8859-1'?>
<PARAMETERS version="1.8.0">
  <NODE name="ProSE" description="fixture">
    <ITEM name="version" value="fixture" type="string" description="" />
    <NODE name="1" description="Instance '1' section for 'ProSE'">
      <NODE name="Search" description="">
        <NODE name="rescore_reuse" description="fixture">
          <ITEM name="mode" value="{mode}" type="string" description="fixture" restrictions="per_file,joint,static,own" />
        </NODE>
      </NODE>
    </NODE>
  </NODE>
</PARAMETERS>
"""
for mode in ("per_file", "joint"):
    with open(os.path.join(OUT, "params_fx", f"immuno_{mode}.ini"), "w", encoding="ISO-8859-1", newline="\n") as f:
        f.write(INI.format(mode=mode))

# ---------------------------------------------------------------- units of the fixture
units, order = {}, []
for r in RUNS:
    name = r[9] if r[9] != "-" else r[0]
    if name not in units:
        units[name] = {"runs": [], "db": r[5], "entrap": [x[:-6] for x in r[6].split(";") if x != "-"],
                       "ref": [x[:-6] for x in r[7].split(";") if x != "-"], "ions": r[8], "group": r[2], "role": r[11]}
        order.append(name)
    units[name]["runs"].append(r[0])
for n in order:
    u = units[n]
    u["td"] = u["db"] + "_td"
    u["stems"] = [u["td"]] + u["entrap"] + u["ref"]
    u["file"] = (u["runs"][0] if len(u["runs"]) == 1 else "pooled") + ".count.idXML"
    u["pooled"] = len(u["runs"]) > 1

ENG = ("msfragger", "prose", "sage")
NRBD = "not_run_by_design (no z+1 ions in Sage 0.14.7)"


def sig4(x):
    """EE prints 4 significant digits (EE-tool:188-194)."""
    if x == 0:
        return "0"
    return f"{x:.4g}"


def count_rows(engine, bench, unit, stem, n_psm, special=None):
    """psm and peptide rows of one search (EE columns)."""
    u = units[unit]
    out = []
    for level, n in (("psm", n_psm), ("peptide", n_psm // 3)):
        if stem == u["td"]:
            out.append((engine, bench, unit, stem, u["file"], level, "all", "0.01", n, 0, 0, 0, "NA", "NA", "NA", 1))
            continue
        if stem.endswith("_arath_td"):
            te, ne = 2.056, max(1, n // 300)
        elif stem.endswith("_natural_td"):
            te, ne = 0.2962, max(1, n // 140)
        else:
            te, ne = 1.003, max(1, n // 250 + (int(stem[-4]) if "_entrap_s" in stem else 0))
        n_e = n - n // 100
        if special and level in special:
            n_e, ne, te = special[level]
        if n_e == 0:
            ne = 0
        lower = ne / n_e if n_e else 0
        comb = ne * (1 + te) / n_e if n_e else 0  # EE-lib:30-34: N_E/N (1 + T/E), te_ratio = T/E
        shuffled = "_entrap_s" in stem
        if level == "peptide" and shuffled:
            paired = sig4(comb * 0.98) if n_e else "0"
            etna, eat = (max(0, ne - 2), min(ne, 2)) if n_e else (0, 0)
        else:
            paired, etna, eat = "NA", "NA", "NA"
        out.append((engine, bench, unit, stem, u["file"], level, "all", "0.01", n_e, ne, sig4(lower), sig4(comb), paired,
                    etna, eat, sig4(te) if te != 1 else 1))
    return out


FACT = {"prose": 1.10, "sage": 0.95, "msfragger": 1.00}
base = {n: 10000 + 500 * i for i, n in enumerate(order)}


def cov_state(engine, bench, unit, stem):
    u = units[unit]
    if engine == "sage" and u["ions"] == "bycz":
        return NRBD, "no"
    if bench == "per_file" and engine == "sage" and unit == "pxd058436_DN05" and stem == u["td"]:
        return "failed_memory stage all repetition 0 exit 137", "no"
    if bench == "per_file" and engine == "sage" and unit == "velos_r1" and stem == "hy_entrap_s3_td":
        return "failed stage all repetition 1 exit 1", "no"
    return "ok", "yes"


# per_file searches plus the arms of the fixture
searches = []
for e in ENG:
    for n in order:
        for s in units[n]["stems"]:
            searches.append((e, "per_file", n, s))
for n in ("pxd058436_DN05", "pxd058436_DN13", "pxd019643_DN05"):
    searches.append(("prose", "per_file_low_memory", n, units[n]["td"]))
for e, b in (("prose", "per_file_cal_off"), ("msfragger", "per_file_cal1"), ("msfragger", "per_file_cal0")):
    for s in ("hye_td", "hye_entrap_s1_td"):
        searches.append((e, b, "hfx_r1", s))

coverage, counts = [], []
for e, b, n, s in searches:
    status, counted = cov_state(e, b, n, s)
    coverage.append((e, b, n, s, status, counted))
    if counted == "yes":
        npsm = round(base[n] * FACT[e]) if b in ("per_file", "per_file_low_memory") else round(base[n] * FACT[e] * 0.97)
        special = None
        if e == "sage" and n == "pxd011695_HCD_r1":
            npsm = 0  # T4: zero count
        if e == "prose" and n == "velos_r1" and "_entrap_s" in s:  # T10
            r = int(s[-4])
            special = {"psm": (1000, 4 + r, 1.0), "peptide": (500, 1 + r, 1.0)}
        counts += count_rows(e, b, n, s, npsm, special)
for e in ENG:  # batch: astral_250pg is the only group of >= 2 files with sample '-'
    coverage.append((e, "batch", "astral_250pg", "hye_td", "ok", "no"))
GRID = (16, 8, 4, 2, 1)
for e in ENG:
    for t in GRID:
        coverage.append((e, "scaling", "hfx_r1", f"hye_td_t{t}", "ok", "no"))
coverage.sort(key=lambda r: r[:4])
COV_H = "engine benchmark run database status counted".split()
CNT_H = ("engine benchmark run database file level class q_value accepted entrapment lower_bound_fdp combined_fdp "
         "paired_fdp entrapment_target_not_accepted entrapment_above_target te_ratio").split()
write("coverage_fx.tsv", COV_H, coverage)
write("counts_fx.tsv", CNT_H, counts)

# ---------------------------------------------------------------- timings (driver format, B:326-342)
TIM_H = "engine benchmark run database stage threads repetition wall_s cpu_s max_rss_kb exit".split()
timings = []


def row(e, b, run, db, stage, threads, rep, wall, cpu, rss, code=0):
    f = lambda x: "NA" if x is None else ("nan" if isinstance(x, float) and math.isnan(x) else f"{x:.2f}")
    timings.append((e, b, run, db + ".fasta", stage, threads, rep, f(wall), f(cpu), "NA" if rss is None else rss, code))


def search_rows(e, b, run, db, threads, walls, reps=(0, 1, 2, 3), rss=3000000, stages=None):
    """walls: {rep: wall} for 'all', or {rep: {stage: wall}} for MSFragger."""
    for rep in reps:
        w = walls[rep]
        if isinstance(w, dict):
            for st, x in w:
                row(e, b, run, db, st, threads, rep, x, x * 10, rss if st == "search" else rss // 4)
        else:
            row(e, b, run, db, "all", threads, rep, w, w * 12, rss)


def mf(search, resc, join=None, n_resc=1):
    out = [("search", search)]
    if join is not None:
        out.append(("join", join))
    out += [("rescoring", resc)] * n_resc
    return out


TH = 16
for i, n in enumerate(order):
    u = units[n]
    for e in ("prose", "sage", "msfragger"):
        if e == "sage" and u["ions"] == "bycz":
            continue
        b0 = 50 + 5 * i
        if e == "prose" and n == "ups1_r1":  # T13
            search_rows(e, "per_file", n, u["db"] + "_td", TH, {0: 105, 1: 100, 2: 100, 3: 120})
        elif e == "prose" and n == "lumos_tmt_r1":  # T30: an attempt at 16 threads, then a rerun at 8
            search_rows(e, "per_file", n, u["db"] + "_td", 16, {0: 61, 1: 60, 2: 62, 3: 61})
            search_rows(e, "per_file", n, u["db"] + "_td", 8, {0: 101, 1: 100, 2: 102, 3: 101})
        elif e == "prose" and n.startswith("astral250pg_"):  # T17 per-file medians 100/110/120
            m = {"astral250pg_A2": 100, "astral250pg_B1": 110, "astral250pg_B3": 120}[n]
            search_rows(e, "per_file", n, u["db"] + "_td", TH, {0: m + 3, 1: m - 2, 2: m, 3: m + 4})
        elif e == "sage" and n == "pxd058436_DN05":  # failed_memory: one rep-0 row, exit 137
            row(e, "per_file", n, u["td"], "all", TH, 0, 300.0, 2400.0, 209715200, 137)
        elif e == "sage" and n == "lumos_lfq_r1":  # T15: rep 0 exit 137, then a complete rerun
            row(e, "per_file", n, u["td"], "all", TH, 0, 50.0, 400.0, 150000000, 137)
            search_rows(e, "per_file", n, u["td"], TH, {0: 70, 1: 68, 2: 69, 3: 71})
        elif e == "msfragger" and n == "hfx_r1":  # T12 / T14
            walls = {0: [("search", 85), ("rescoring", 12)], 1: [("search", 80), ("rescoring", 40)],
                     2: [("search", 90), ("rescoring", 10)], 3: [("search", 100), ("rescoring", 15)]}
            for rep in (0, 1, 2, 3):
                for st, x in walls[rep]:
                    row(e, "per_file", n, u["td"], st, TH, rep, x, x * 10, 2000000 if st == "search" else 500000)
        elif e == "msfragger" and n == "iprg2015_r1":  # T16: no_timing in r2
            for rep in (0, 1, 2, 3):
                if rep == 2:
                    row(e, "per_file", n, u["td"], "search", TH, rep, None, None, None, "no_timing")
                else:
                    row(e, "per_file", n, u["td"], "search", TH, rep, 90 + rep, 900.0, 4000000)
                row(e, "per_file", n, u["td"], "rescoring", TH, rep, 5.0 + rep, 50.0, 100000)
        elif e == "msfragger":
            for rep in (0, 1, 2, 3):
                st = mf(b0 + rep, 3 + rep, join=(2.0 if u["pooled"] else None))
                for s_, x in st:
                    row(e, "per_file", n, u["td"], s_, TH, rep, x, x * 10, 5000000 if s_ == "search" else 200000)
        else:
            f = 1.0 if e == "prose" else 1.4
            search_rows(e, "per_file", n, u["td"], TH, {0: b0 * f + 1, 1: b0 * f, 2: b0 * f + 2, 3: b0 * f + 1},
                        rss=3000000 + 10000 * i)
for n in ("pxd058436_DN05", "pxd058436_DN13", "pxd019643_DN05"):  # low_memory arm, timed
    search_rows("prose", "per_file_low_memory", n, units[n]["td"], TH, {0: 81, 1: 80, 2: 82, 3: 83}, rss=1500000)
# batch arm: astral_250pg (3 files); T17 prose walls 270/300/285
search_rows("prose", "batch", "astral_250pg", "hye_td", TH, {0: 280, 1: 270, 2: 300, 3: 285}, rss=6000000)
search_rows("sage", "batch", "astral_250pg", "hye_td", TH, {0: 400, 1: 390, 2: 410, 3: 405}, rss=9000000)
for rep in (0, 1, 2, 3):
    for st, x in mf(250 + rep, 4.0, n_resc=3):
        row("msfragger", "batch", "astral_250pg", "hye_td", st, TH, rep, x, x * 10,
            8000000 if st == "search" else 300000)
# scaling: hfx_r1, grid 16..1, repetition 0 only at the top point; T18 prose T1..T16 = 1600/820/410/220/125
T18 = {16: 125, 8: 220, 4: 410, 2: 820, 1: 1600}
for e in ("prose", "sage", "msfragger"):
    for i, t in enumerate(GRID):
        reps = (0, 1, 2, 3) if i == 0 else (1, 2, 3)
        m = T18[t] * (1.0 if e == "prose" else 1.3 if e == "sage" else 1.6)
        for rep in reps:
            w = m + {0: 2, 1: -1, 2: 0, 3: 1}[rep]
            if e == "msfragger":
                row(e, "scaling", "hfx_r1", "hye_td", "search", t, rep, w * 0.9, w * 0.9 * t, 4000000)
                row(e, "scaling", "hfx_r1", "hye_td", "rescoring", t, rep, w * 0.1, w * 0.1 * t, 300000)
            else:
                row(e, "scaling", "hfx_r1", "hye_td", "all", t, rep, w, w * t, 3500000)
write("timings_fx.tsv", TIM_H, timings)

# ---------------------------------------------------------------- over the limit (T19): scaling rows only
L = 86400.0
timings, cov_ol = [], []
for e in ("prose", "msfragger"):
    first = "search" if e == "msfragger" else "all"
    for i, t in enumerate(GRID):
        if t >= 4:
            m = {16: 125, 8: 220, 4: 410}[t]
            cov_ol.append((e, "scaling", "hfx_r1", f"hye_td_t{t}", "ok", "no"))
            for rep in ((0, 1, 2, 3) if i == 0 else (1, 2, 3)):
                if e == "msfragger":
                    row(e, "scaling", "hfx_r1", "hye_td", "search", t, rep, m * 0.9 + rep, m * t, 4000000)
                    row(e, "scaling", "hfx_r1", "hye_td", "rescoring", t, rep, m * 0.1, m * 0.1 * t, 300000)
                else:
                    row(e, "scaling", "hfx_r1", "hye_td", "all", t, rep, m + rep, m * t, 3500000)
        elif t == 2:  # over the limit at the first repetition: wall = L, cpu nan, rss NA (B:298-300)
            cov_ol.append((e, "scaling", "hfx_r1", "hye_td_t2", f"over_limit stage {first} repetition 1", "no"))
            row(e, "scaling", "hfx_r1", "hye_td", first, t, 1, L, float("nan"), None, "over_limit")
        else:  # not run: recorded with stage all (also for MSFragger), repetition 1, wall = L (B:996-999)
            row(e, "scaling", "hfx_r1", "hye_td", "all", t, 1, L, float("nan"), None, "not_run_over_limit")
write("timings_overlimit_fx.tsv", TIM_H, timings)
write("coverage_overlimit_fx.tsv", COV_H, sorted(cov_ol))

# ---------------------------------------------------------------- W_node (decision runs only)
dec = [n for n in order if units[n]["role"] == "decision"]
cov_w, cnt_w, timings = [], [], []
for e in ENG:
    for n in order:
        for s in units[n]["stems"]:
            if e == "sage" and units[n]["ions"] == "bycz":
                cov_w.append((e, "per_file", n, s, NRBD, "no"))
            elif n in dec:
                cov_w.append((e, "per_file", n, s, "ok", "yes"))
                cnt_w += count_rows(e, "per_file", n, s, round(base[n] * FACT[e]))
            else:
                cov_w.append((e, "per_file", n, s, "not_run", "no"))
for n in dec:
    u = units[n]
    for e in ("prose", "sage", "msfragger"):
        for rep in (0, 1, 2, 3):
            if e == "msfragger":
                for s_, x in mf(60 + rep, 2.0, join=(1.0 if u["pooled"] else None)):
                    row(e, "per_file", n, u["td"], s_, TH, rep, x, x * 10, 5000000)
            else:
                row(e, "per_file", n, u["td"], "all", TH, rep, 40 + rep, 400.0, 3000000)
write("coverage_wnode_fx.tsv", COV_H, sorted(cov_w))
write("counts_wnode_fx.tsv", CNT_H, cnt_w)
write("timings_wnode_fx.tsv", TIM_H, timings)

# ---------------------------------------------------------------- smoke layout (--design none)
units.update({b: {"runs": [b], "db": "smoke", "td": "smoke_td", "entrap": ["smoke_entrap_td"], "ref": [],
                  "file": b + ".count.idXML", "pooled": False, "ions": "by", "group": "smoke", "role": "heldout",
                  "stems": ["smoke_td", "smoke_entrap_td"]} for b, _ in SMOKE})
cov_s, cnt_s, timings = [], [], []
for e in ENG:
    for b, _ in SMOKE:
        for s in ("smoke_td", "smoke_entrap_td"):
            cov_s.append((e, "per_file", b, s, "ok", "yes"))
            rows = count_rows(e, "per_file", b, s, 300 + 10 * len(e))
            cnt_s += rows
    cov_s.append((e, "batch", "smoke", "smoke_td", "ok", "no"))
    for t in (8, 4, 2, 1):
        cov_s.append((e, "scaling", "bsa1", f"smoke_td_t{t}", "ok", "no"))
for e in ("prose", "sage", "msfragger"):
    for b, _ in SMOKE:
        for rep in (0, 1, 2, 3):
            if e == "msfragger":
                row(e, "per_file", b, "smoke_td", "search", 8, rep, 3.0 + rep * 0.1, 20.0, 900000)
                row(e, "per_file", b, "smoke_td", "rescoring", 8, rep, 0.5, 2.0, 50000)
            else:
                row(e, "per_file", b, "smoke_td", "all", 8, rep, 1.0 + rep * 0.1, 6.0, 300000)
    for rep in (0, 1, 2, 3):
        if e == "msfragger":
            row(e, "batch", "smoke", "smoke_td", "search", 8, rep, 5.0, 30.0, 900000)
            for _ in SMOKE:
                row(e, "batch", "smoke", "smoke_td", "rescoring", 8, rep, 0.5, 2.0, 50000)
        else:
            row(e, "batch", "smoke", "smoke_td", "all", 8, rep, 2.5, 15.0, 300000)
    for i, t in enumerate((8, 4, 2, 1)):
        for rep in ((0, 1, 2, 3) if i == 0 else (1, 2, 3)):
            if e == "msfragger":
                row(e, "scaling", "bsa1", "smoke_td", "search", t, rep, 3.0 * 8 / t, 24.0, 900000)
                row(e, "scaling", "bsa1", "smoke_td", "rescoring", t, rep, 0.5, 0.5 * t, 50000)
            else:
                row(e, "scaling", "bsa1", "smoke_td", "all", t, rep, 1.0 * 8 / t, 8.0, 300000)
# the smoke prints lower_bound_fdp / combined_fdp of td rows as ints (SPEC 2.3 "Casting"): count_rows writes 0
write("coverage_smoke_fx.tsv", COV_H, sorted(cov_s))
write("counts_smoke_fx.tsv", CNT_H, cnt_s)
write("timings_smoke_fx.tsv", TIM_H, timings)
print("fixtures written to", OUT)
