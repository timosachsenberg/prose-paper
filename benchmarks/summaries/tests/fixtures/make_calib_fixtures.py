"""Writes the calib test fixtures (calib_* names) next to this file, or into the folder given as argument. The files are
static; rerun only to change them. Run: python3 -B make_calib_fixtures.py [<out dir>]"""
import os
import sys

FX = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
LOGS = os.path.join(FX, "calib_logs")
os.makedirs(LOGS, exist_ok=True)


def write(path, text):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


# ---------------------------------------------------------------- MSFragger logs (shapes of MSFragger 4.4.1)
HEAD = ("MSFragger version MSFragger-4.4.1\nBatmass-IO version 1.36.6\n(c) University of Michigan\n"
        "Parameters:\nnum_threads = 16\nfragment_mass_tolerance = 20.0\n")
TABLE = ("-----|---------------|---------------|---------------|---------------\n"
         " Run |  Median  MAD  |  Median  MAD  |  Median  MAD  |  Median  MAD  \n"
         " 001 |   1.63   0.62 |   0.04   0.61 |  -2.66   1.44 |  -0.12   1.41  \n"
         "Finding the optimal parameters:\n")
TAIL = ("Number of unique peptides\n\tof length 7: 1000\n"
        "New use_topN_peaks = 999\n"  # after the block: must be ignored
        "Total time: 1.000 min\n")
write(os.path.join(LOGS, "msfragger_search_fx.log"),
      HEAD + "*********************MASS CALIBRATION AND PARAMETER OPTIMIZATION*******************\n" + TABLE +
      "New fragment_mass_tolerance = 10 PPM\nNew use_topN_peaks = 150\nNew minimum_ratio = 0.010000\n"
      "New intensity_transform = 1\nNew remove_precursor_peak = 1\nNew max_fragment_charge = 2\n"
      "************MASS CALIBRATION AND PARAMETER OPTIMIZATION DONE IN 4.463 MIN*********\n" + TAIL)
write(os.path.join(LOGS, "msfragger_search_mixed_fx.log"),
      HEAD + "*********************MASS CALIBRATION AND PARAMETER OPTIMIZATION*******************\n" + TABLE +
      "New fragment_mass_tolerance = 7.000000 PPM\nNew use_topN_peaks = 300\nNew minimum_ratio = 0.000000\n"
      "New intensity_transform = 1\nNew remove_precursor_peak = 1\n"
      "************MASS CALIBRATION AND PARAMETER OPTIMIZATION DONE IN 4.463 MIN*********\n" + TAIL)
write(os.path.join(LOGS, "msfragger_search_cal1_fx.log"),
      HEAD + "*********************MASS CALIBRATION*******************\n" + TABLE +
      "************MASS CALIBRATION DONE IN 0.512 MIN*********\n" + TAIL)
write(os.path.join(LOGS, "msfragger_search_nonew_fx.log"), HEAD + TAIL)
write(os.path.join(LOGS, "fragger_fx.params"),
      "database_name = /W/db/hye_td.fasta\t\t\t# Path to the protein database file in FASTA format.\n"
      "num_threads = 16\t\t\t# 0=poll CPU to set num threads; else specify num threads directly (max 64).\n"
      "fragment_mass_tolerance = 0.02\t\t\t# Fragment mass tolerance (window is +/- this value).\n"
      "fragment_mass_units = 0\t\t\t# Fragment mass tolerance units (0 for Da, 1 for ppm).\n"
      "calibrate_mass = 0\t\t\t# Perform mass calibration (0 for OFF, 1 for ON, 2 for ON and find optimal "
      "parameters).\n"
      "use_topN_peaks = 300\t\t\t# Pre-process experimental spectrum to only use top N peaks.\n"
      "minimum_ratio = 0.00\t\t\t# Filters out all peaks in experimental spectrum less intense than this "
      "multiple of the base peak intensity.\n"
      "intensity_transform = 0\t\t\t# Transform peak intensities with sqrt root. 0 = none; 1 = sqrt root.\n"
      "remove_precursor_peak = 1\t\t\t# Remove precursor peaks from tandem mass spectra. 0 = not remove.\n"
      "max_fragment_charge = 2\t\t\t# Maximum charge state for theoretical fragments to match.\n"
      "remainder_fragment_masses = \t\t\t# [labile search_mode only] List of possible remainder fragment ions.\n")

# ---------------------------------------------------------------- ProSE logs (shapes of the local driver logs)
FRAG_PPM = ("[ProSE]   Fragment:  offset 0.00, sigma 1.56 ppm (|offset| + 4 sigma 6.26; 38546 peaks) -> tolerance "
            "20.00 -> 6.26 ppm (covers 95 % of the peaks)\n")
write(os.path.join(LOGS, "prose_all_fx.log"),
      "[ProSE] Loading parameters\n[ProSE] [1/1] Searching /W/mzml/hfx_r1.mzML\n"
      "[ProSE] Calibration: 5123 PSMs at 1 % FDR\n"
      "[ProSE]   Precursor: offset 1.20, sigma 0.80 ppm -> tolerance 10.00 -> 4.40 ppm\n" + FRAG_PPM +
      "[ProSE] Fragment idx : 123456 entries\nSearching with up to 3 ambiguous amino acid(s) and 0 mismatch(es)!\n"
      "[ProSE] Total time: 12.3 s\n")
write(os.path.join(LOGS, "prose_all_da_fx.log"),
      "[ProSE] Loading parameters\n"
      "[ProSE] Fragment tolerance 0.5 Da exceeds the deisotoping limit (100 ppm / 0.1 Da); skipping MS2 "
      "deisotoping (expected for low-resolution data).\n"
      "[ProSE] [1/3] Searching /W/mzml/run_c.mzML\n"
      "[ProSE]   Fragment:  offset 0.01, sigma 0.08 Da (|offset| + 4 sigma 0.33; 27652 peaks) -> tolerance 0.50 -> "
      "0.33 Da (covers 96 % of the peaks)\n"
      "[ProSE] [2/3] Searching /W/mzml/run_a.mzML\n"
      "[ProSE] Calibration: the fragment tolerance |median| + 4 sigma covers only 94 % of the matched fragment "
      "peaks of the calibration PSMs: the configured fragment tolerance is kept.\n"
      "[ProSE]   Fragment:  offset 0.00, sigma 0.08 Da (|offset| + 4 sigma 0.33; 25000 peaks) -> tolerance 0.50 -> "
      "0.50 Da (covers 94 % of the peaks)\n"
      "[ProSE] [3/3] Searching /W/mzml/run_b.mzML\n"
      "[ProSE]   Fragment:  offset -0.02, sigma 0.07 Da (|offset| + 4 sigma 0.30; 26000 peaks) -> tolerance 0.50 "
      "-> 0.30 Da (covers 95.5 % of the peaks)\n"
      "[ProSE] Fragment idx : 654321 entries\n[ProSE] Total time: 30.0 s\n")
write(os.path.join(LOGS, "prose_all_insufficient_fx.log"),
      "[ProSE] [1/1] Searching /W/mzml/hfx_r1.mzML\n"
      "[ProSE] Calibration: insufficient PSMs (12 < 100), using configured tolerances.\n"
      "[ProSE] Total time: 5.0 s\n")
write(os.path.join(LOGS, "prose_all_pooled_fx.log"),  # two inputs, logged in the reverse order of 'inputs'
      "[ProSE] [1/2] Searching /W/mzml/DN05_r2.mzML\n"
      "[ProSE]   Fragment:  offset 0.10, sigma 2.00 ppm (|offset| + 4 sigma 8.10; 9000 peaks) -> tolerance "
      "20.00 -> 8.10 ppm (covers 95 % of the peaks)\n"
      "[ProSE] [2/2] Searching /W/mzml/DN05_r1.mzML\n"
      "[ProSE]   Fragment:  offset -0.20, sigma 1.50 ppm (|offset| + 4 sigma 6.20; 8000 peaks) -> tolerance "
      "20.00 -> 6.20 ppm (covers 96 % of the peaks)\n")
write(os.path.join(LOGS, "summary_fx.yaml"),
      "tool: ProSE\nversion: fixture\nshared:\n  fragment_tol: 20\n  fragment_tol_unit: ppm\n"
      "  calibration_enabled: true\n  precursor_tol: 10\nfiles:\n  - name: hfx_r1\n")
write(os.path.join(LOGS, "sage_fx.json"),
      '{\n  "database": {"fasta": "/W/db/hye_td.fasta"},\n  "precursor_tol": {"ppm": [-10, 10]},\n'
      '  "fragment_tol": {"ppm": [-20, 20]},\n  "max_fragment_charge": 2\n}\n')

# ---------------------------------------------------------------- counts / coverage rows of the future arms
COUNTS_HEADER = ["engine", "benchmark", "run", "database", "file", "level", "class", "q_value", "accepted",
                 "entrapment", "lower_bound_fdp", "combined_fdp", "paired_fdp", "entrapment_target_not_accepted",
                 "entrapment_above_target", "te_ratio"]
counts, coverage = [], []


def g(x):
    return f"{x:.6g}"


def search(engine, bench, run, db, psm, entrap=None, status="ok", counted="yes"):
    """Coverage row plus psm and peptide counts rows; entrap = entrapment count E on N = psm (te_ratio 1:
    combined = 2 E / N, lower = E / N)."""
    coverage.append([engine, bench, run, db, status, counted])
    if counted != "yes":
        return
    for level, n in (("psm", psm), ("peptide", psm // 2)):
        e = 0 if entrap is None else (entrap if level == "psm" else entrap // 2)
        lower, comb = (e / n, 2 * e / n) if n else (0, 0)
        paired = ["NA", "NA", "NA"] if level == "psm" else ([g(comb), str(e), "0"] if entrap is not None
                                                             else ["NA", "NA", "NA"])
        counts.append([engine, bench, run, db, run + ".count.idXML", level, "all", "0.01", str(n), str(e),
                       g(lower), g(comb)] + paired + ["1"])


SEEDS = ("per_file_percolator_s1", "per_file_percolator_s42", "per_file_percolator_s137")
TD = {"hfx_r1": "hye_td", "lumos_lfq_r1": "hy_td", "iprg2015_r1": "iprg2015_td",
      "hela_qe_hf_r1": "pxd042233_human_td", "astral250pg_A2": "hye_td", "astral250pg_B1": "hye_td"}
PERC = {  # run -> engine -> psm per seed (s1, s42, s137); None = failed search
    "hfx_r1": {"prose": (1090, 1100, 1110), "msfragger": (990, 1000, 1010), "sage": (1000, 1000, 1000)},
    "lumos_lfq_r1": {"prose": (1210,) * 3, "msfragger": (1000,) * 3, "sage": (1000, 0, 1000)},
    "iprg2015_r1": {"prose": (990,) * 3, "msfragger": (1000,) * 3, "sage": (1100,) * 3},
    "hela_qe_hf_r1": {"prose": (1000,) * 3, "msfragger": (1000,) * 3, "sage": (1000, 1000, None)},
    "astral250pg_A2": {"prose": (1500,) * 3, "msfragger": (1000,) * 3, "sage": (1000,) * 3},
}
for run, engines in PERC.items():
    for engine, vals in engines.items():
        for bench, v in zip(SEEDS, vals):
            if v is None:
                search(engine, bench, run, TD[run], 0, status="failed stage all repetition 1 exit 1", counted="no")
            else:
                search(engine, bench, run, TD[run], v)
# hfx_r1 entrapment searches of the seeds (N = 2000): combined 0.011/0.012/0.013 (prose s1), 0.010 (prose s2),
# 0.008 (msfragger s1 only), 0.011 (sage s1 and s2)
for bench, e in zip(SEEDS, (11, 12, 13)):
    search("prose", bench, "hfx_r1", "hye_entrap_s1_td", 2000, entrap=e)
    search("prose", bench, "hfx_r1", "hye_entrap_s2_td", 2000, entrap=10)
    search("msfragger", bench, "hfx_r1", "hye_entrap_s1_td", 2000, entrap=8)
    search("sage", bench, "hfx_r1", "hye_entrap_s1_td", 2000, entrap=11)
    search("sage", bench, "hfx_r1", "hye_entrap_s2_td", 2000, entrap=11)
PRED = {"hfx_r1": (13310, 12100), "iprg2015_r1": (20460, 15500), "astral250pg_B1": (19800, 19800),
        "astral250pg_A2": (20000, 17500)}
for run, (pd, mb) in PRED.items():
    search("prose", "per_file_peptdeep", run, TD[run], pd)
    search("msfragger", "per_file_msbooster", run, TD[run], mb)
search("prose", "per_file_peptdeep", "hfx_r1", "hye_entrap_s1_td", 2000, entrap=7)  # combined 0.007
search("msfragger", "per_file_msbooster", "hfx_r1", "hye_entrap_s1_td", 2000, entrap=9)  # combined 0.009

write(os.path.join(FX, "calib_counts_arms_fx.tsv"),
      "\n".join("\t".join(r) for r in [COUNTS_HEADER] + counts) + "\n")
write(os.path.join(FX, "calib_coverage_arms_fx.tsv"),
      "\n".join("\t".join(r) for r in [["engine", "benchmark", "run", "database", "status", "counted"]] + coverage)
      + "\n")

# ---------------------------------------------------------------- commands.log and versions.txt (O21)
P = "/W/out/prose/per_file_peptdeep"
write(os.path.join(FX, "calib_commands_fx.log"),
      f"/opt/openms/bin/ProSE -ini /W/params/main_highres.ini -in /W/mzml/hfx_r1.mzML -database /W/db/hye_td.fasta "
      f"-out /W/out/prose/per_file/hfx_r1/hye_td/hfx_r1.idXML -summary_out /W/out/prose/per_file/hfx_r1/hye_td/"
      f"summary.yaml -threads 16 > /W/out/prose/per_file/hfx_r1/hye_td/all.log 2>&1\n"
      f"systemd-run --user --scope --quiet -p MemoryMax=24G -- /opt/openms/bin/ProSE -ini /W/params/main_highres.ini "
      f"-in /W/mzml/hfx_r1.mzML -database /W/db/hye_td.fasta -out {P}/hfx_r1/hye_td/hfx_r1.idXML -summary_out "
      f"{P}/hfx_r1/hye_td/summary.yaml -Search:peptdeep:instrument QE -threads 16 > {P}/hfx_r1/hye_td/all.log 2>&1\n"
      f"# NOT COUNTED {P}/hfx_r1/hye_td: fixture comment line\n"
      f"systemd-run --user --scope --quiet -p MemoryMax=24G -- /opt/openms/bin/ProSE -ini /W/params/main_highres.ini "
      f"-in /W/mzml/hfx_r1.mzML -database /W/db/hye_td.fasta -out {P}/hfx_r1/hye_td/hfx_r1.idXML -summary_out "
      f"{P}/hfx_r1/hye_td/summary.yaml -Search:peptdeep:instrument Lumos -threads 16 > {P}/hfx_r1/hye_td/all.log "
      f"2>&1\n"
      f"/opt/openms/bin/ProSE -ini /W/params/main_highres.ini -in /W/mzml/hfx_r1.mzML -database "
      f"/W/db/hye_entrap_s1_td.fasta -out {P}/hfx_r1/hye_entrap_s1_td/hfx_r1.idXML -summary_out "
      f"{P}/hfx_r1/hye_entrap_s1_td/summary.yaml -Search:peptdeep:instrument Lumos -threads 16\n"
      f"/opt/openms/bin/ProSE -ini /W/params/iprg2015_qe.ini -in /W/mzml/iprg2015_r1.mzML -database "
      f"/W/db/iprg2015_td.fasta -out {P}/iprg2015_r1/iprg2015_td/iprg2015_r1.idXML -summary_out "
      f"{P}/iprg2015_r1/iprg2015_td/summary.yaml -threads 16\n"
      f"java -jar /opt/msfragger/MSFragger-4.4.1.jar /W/out/msfragger/per_file_msbooster/hfx_r1/hye_td/"
      f"fragger.params /W/mzml/hfx_r1.mzML\n")
write(os.path.join(FX, "calib_versions_fx.txt"),
      "/opt/bench/openms/bin/ProSE --help\tVersion: 3.7.0-pre-HEAD-2026-01-01 Jan 01 2026, 00:00:00, Revision: "
      "abc1234\n"
      "java -jar /opt/bench/tools/msbooster/MSBooster-1.3.9.jar --version\tMSBooster v1.3.9\n")
write(os.path.join(FX, "calib_iprg2015_qe_fx.ini"),
      "<?xml version='1.0' encoding='ISO-8859-1'?>\n<PARAMETERS version=\"1.8.0\">\n"
      "  <NODE name=\"ProSE\" description=\"fixture\">\n"
      "    <ITEM name=\"version\" value=\"fixture\" type=\"string\" description=\"\" />\n"
      "    <NODE name=\"1\" description=\"Instance '1' section for 'ProSE'\">\n"
      "      <NODE name=\"Search\" description=\"\">\n"
      "        <NODE name=\"peptdeep\" description=\"fixture\">\n"
      "          <ITEM name=\"instrument\" value=\"QE\" type=\"string\" description=\"fixture\" />\n"
      "        </NODE>\n      </NODE>\n    </NODE>\n  </NODE>\n</PARAMETERS>\n")
print(len(counts), "counts rows,", len(coverage), "coverage rows")
