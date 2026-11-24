"""Writes fdp_counts_qgrid_fx.tsv (made-up numbers, EE's format) next to this file, or to the path given as argument.
Run: python3 -B make_qgrid_fixture.py [<out file>]"""
import os
import sys
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                         "fdp_counts_qgrid_fx.tsv")
H = ("engine benchmark run database file level class q_value accepted entrapment lower_bound_fdp combined_fdp "
     "paired_fdp entrapment_target_not_accepted entrapment_above_target te_ratio").split()
# (engine, run, db, te, [(q, N, N_E), ...]) ; psm level only
S = [
    ("prose", "velos_r1", "hy_entrap_s1_td", 1.0, [(0.005, 800, 3), (0.01, 1000, 5), (0.015, 1100, 7)]),
    ("prose", "velos_r1", "hy_entrap_s2_td", 1.0, [(0.005, 700, 2), (0.01, 1000, 6), (0.015, 1100, 8)]),
    ("msfragger", "velos_r1", "hy_entrap_s1_td", 1.003, [(0.005, 9000, 30), (0.01, 9900, 41), (0.015, 10500, 52)]),
    ("msfragger", "velos_r1", "hy_entrap_s2_td", 1.003, [(0.005, 9000, 31), (0.01, 9900, 42), (0.015, 10500, 60)]),
    ("sage", "velos_r1", "hy_entrap_s1_td", 1.003, [(0.005, 9000, 30), (0.01, 9405, 39), (0.015, 9800, 50)]),
    ("sage", "velos_r1", "hy_entrap_s2_td", 1.003, [(0.005, 9000, 30), (0.01, 9405, 40), (0.015, 9800, 45)]),
    ("prose", "velos_r1", "hy_velos_natural_td", 0.2962, [(0.005, 8000, 60), (0.01, 10890, 78), (0.015, 11500, 95)]),
    ("msfragger", "velos_r1", "hy_velos_natural_td", 0.2962, [(0.005, 8000, 50), (0.01, 9900, 71), (0.015, 10400, 80)]),
    ("sage", "velos_r1", "hy_velos_natural_td", 0.2962, [(0.005, 8000, 55), (0.01, 9405, 67), (0.015, 9900, 90)]),
    # T32: FDP 0.008, 0.011, 0.009, 0.012 -> q_match = 0.006 (the third grid q), monotone_ok no
    ("prose", "lumos_tmt_r1", "hy_entrap_s1_td", 1.0, [(0.002, 500, 2), (0.004, 2000, 11), (0.006, 4000, 18),
                                                     (0.008, 5000, 30)]),
]
lines = ["\t".join(H)]
for e, run, db, te, pts in S:
    for q, n, ne in pts:
        lb = ne / n
        cb = lb * (1 + te)
        lines.append("\t".join([e, "per_file", run, db, run + ".count.idXML", "psm", "all", f"{q:g}", str(n), str(ne),
                                f"{lb:.4g}", f"{cb:.4g}", "NA", "NA", "NA", f"{te:.4g}"]))
with open(OUT, "w", newline="\n") as f:
    f.write("\n".join(lines) + "\n")
