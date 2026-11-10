#!/usr/bin/env python3
"""Driver of the ProSE publication benchmark (datasets/DATASETS.md, sections 4.2 to 4.5). Linux, Python 3 only.

Every stage reads the run table (runs.tsv, one row per run) and the ProSE parameter files datasets/params/*.ini.
The Sage and MSFragger configurations are translated from the values in those files (ProSE defaults included),
so no file is selected and no setting is typed by hand. README.md next to this file has the order of the commands.

  bench.py --work W versions                   version output of every tool -> W/versions.txt
  bench.py --work W databases                  the databases of the run table -> W/db, checked by SHA256
  bench.py --work W fetch                      download the vendor files
  bench.py --work W convert                    vendor files -> mzML with FileConverter, SHA256 of every mzML
  bench.py --work W search  --engine E --db D  one invocation per run (immunopeptidomics: per sample);
                                               D = td (counts, timings), entrap (FDP), ref (Arabidopsis)
                                               --timed: one discarded run, then three under /usr/bin/time -v
  bench.py --work W count   --engine E --db D  results -> idXML -> EntrapmentEvaluator: accepted PSMs and peptides
                                               at q <= 0.01 (td) and the entrapment FDP (entrap, ref)
  bench.py --work W collect                    all count.tsv -> W/counts.tsv
  bench.py --work W batch   --engine E         all files of a group in one invocation (timed)
  bench.py --work W scaling --engine E         thread grid on the scaling files (timed, pinned, 24 h limit)

Common options: --only ID[,ID...] restricts to some runs, --dry-run prints the commands and runs nothing,
--runs FILE takes another run table (smoke/runs.tsv is a three-file test that runs in minutes).
Tools come from --openms-bin, --sage, --msfragger-jar, --percolator (or the environment variables OPENMS_BIN,
SAGE, MSFRAGGER_JAR, PERCOLATOR).

Work directory: vendor/ mzml/ db/ out/<engine>/<benchmark>/<run>/<database>/ commands.log timings.tsv counts.tsv
mzml.sha256 versions.txt

Checked against the sources (2026-11-10): the ProSE and EntrapmentEvaluator options (OpenMS develop), the Sage
configuration (v0.14.7), the MSFragger parameter names and the non-specific enzyme (FragPipe workflows).
Sage has no z+1 ions in any release, so it is not run on the electron-based runs (column `ions` = bycz).
Differences that remain: Sage does not clip the protein N-terminal methionine (ProSE and MSFragger do); the fragment
m/z range, fragment charges, minimum matched ions and deisotoping stay at each engine's default.

STATUS (2026-11-10): the Sage path (configuration, search, timing, pinning, time limit, result reader, idXML) was run
on the smoke test with Sage 0.14.7. The ProSE and MSFragger paths, FileConverter and EntrapmentEvaluator were only
dry-run: run the smoke test with them first (README.md).
"""
import argparse, csv, glob, gzip, hashlib, json, os, re, shlex, shutil, signal, subprocess, sys, tarfile, urllib.request
from xml.sax.saxutils import quoteattr

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
PARAMS = os.path.join(REPO, "datasets", "params")
sys.dont_write_bytecode = True
sys.path.insert(0, PARAMS)
import xml.etree.ElementTree as ET  # noqa: E402
from make_inis import items, value  # noqa: E402  (the readers of the ProSE parameter files)

GRID = [1, 2, 4, 8, 16, 32, 48, 64, 96, 128, 192]
MASS = {"Carbamidomethyl": 57.021464, "Oxidation": 15.994915, "TMT6plex": 229.162932, "TMTpro": 304.207146}
# ProSE enzyme -> (cleave after, not before, MSFragger's name of the enzyme)
ENZYME = {"Trypsin/P": ("KR", "", "stricttrypsin"), "Chymotrypsin": ("FYWL", "P", "chymotrypsin"),
          "unspecific cleavage": (None, "", "nonspecific")}
# ProSE scores electron-activated spectra with b, y, c and z+1 ions (Search:ions:by_activation)
IONS = {"by": ["b", "y"], "bycz": ["b", "y", "c", "z"]}


# ---------------------------------------------------------------- run table and helpers
def settings(name):
    """The Search:* values of a ProSE parameter file, e.g. {'enzyme': 'Trypsin/P', 'peptide:min_size': '7', ...}"""
    it = items(ET.parse(os.path.join(PARAMS, name + ".ini")).getroot())
    return {k[len("Search:"):]: value(v) for k, v in it.items() if k.startswith("Search:")}


def runs(args):
    rows = list(csv.DictReader(open(args.runs, encoding="utf-8"), delimiter="\t"))
    ids = [r["id"] for r in rows]
    assert len(ids) == len(set(ids)), "run table: duplicate id"
    for r in rows:
        assert os.path.exists(os.path.join(PARAMS, r["params"] + ".ini")), f"{r['id']}: no parameter file {r['params']}"
        assert r["ions"] in IONS, f"{r['id']}: unknown ion series {r['ions']}"
    if args.only:
        want = set(args.only.split(","))
        assert want <= set(ids), f"unknown run id: {sorted(want - set(ids))}"
        rows = [r for r in rows if r["id"] in want]
    if getattr(args, "engine", None) == "sage":  # no z+1 ions in any Sage release
        for r in rows:
            if r["ions"] != "by":
                log(args, f"# sage: {r['id']} skipped (electron-based run)")
        rows = [r for r in rows if r["ions"] == "by"]
    if getattr(args, "engine", None) == "prose":
        # Sage and MSFragger search every spectrum at its recorded charge; ProSE does so only with this setting
        # (DATASETS.md, section 4.4). Parameter files written before the option existed do not hold it.
        old = sorted({r["params"] for r in rows
                      if settings(r["params"]).get("precursor:recorded_charge_outside_range") != "search"})
        if old:
            text = (f"parameter files without precursor:recorded_charge_outside_range = search: {', '.join(old)}. "
                    "Write them again with datasets/params/make_inis.py and the frozen ProSE build.")
            if not args.dry_run:
                sys.exit(text)
            log(args, "# WARNING: " + text)
    return rows


def databases(r, kind):
    if kind == "td":
        return [r["db"] + "_td.fasta"]
    return [x for x in r["entrap" if kind == "entrap" else "ref"].split(";") if x != "-"]


def mzml(args, r):
    return os.path.join(args.work, "mzml", r["id"] + ".mzML")


def bench_name(args, bench):
    tag = getattr(args, "tag", None)
    return bench + ("_" + tag if tag else "")


def outdir(args, engine, bench, name, db, threads=None):
    return os.path.join(args.work, "out", engine, bench, name, db[:-len(".fasta")] + (f"_t{threads}" if threads else ""))


def log(args, text):
    print(text, flush=True)
    if not args.dry_run:
        with open(os.path.join(args.work, "commands.log"), "a", encoding="utf-8") as f:
            f.write(text + "\n")


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 24), b""):
            h.update(block)
    return h.hexdigest()


def call(args, cmd, env=None, timing=None, pin=None, limit=None, output=None):
    """Runs cmd. timing = dict of labels: runs under /usr/bin/time -v and appends a line to timings.tsv.
    limit = seconds: the command and everything it started is killed after that time (exit 'over_limit').
    output = file that receives stdout and stderr."""
    if pin:
        cmd = ["taskset", "-c", pin] + cmd
    tfile = os.path.join(args.work, "time.txt")
    if timing is not None:
        cmd = ["/usr/bin/time", "-v", "-o", tfile] + cmd
    show = " ".join(f"{k}={v}" for k, v in (env or {}).items())
    log(args, (show + " " if show else "") + " ".join(shlex.quote(c) for c in cmd) + (f" > {shlex.quote(output)} 2>&1" if output else ""))
    if args.dry_run:
        return 0
    e = dict(os.environ, **(env or {}))
    e.pop("OPENMS_BRUKER_SDK_PATH", None)  # section 4.0: never the Bruker SDK
    if os.path.exists(tfile):
        os.remove(tfile)
    out = open(output, "wb") if output else None
    # a session of its own, so that a run over the limit is killed with all its child processes
    proc = subprocess.Popen(cmd, env=e, stdout=out, stderr=subprocess.STDOUT if out else None, start_new_session=True)
    try:
        code = proc.wait(timeout=limit)
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGKILL)
        proc.wait()
        code = "over_limit"
    if out:
        out.close()
    if timing is not None:
        t = {}
        if os.path.exists(tfile):
            for line in open(tfile):
                k, _, v = line.strip().rpartition(": ")
                t[k] = v
            os.remove(tfile)
        wall = 0.0
        for part in t.get("Elapsed (wall clock) time (h:mm:ss or m:ss)", "0").split(":"):
            wall = wall * 60 + float(part)
        if code == "over_limit":
            wall = float(limit)
        cpu = float(t.get("User time (seconds)", "nan")) + float(t.get("System time (seconds)", "nan"))
        record(args, timing, wall, cpu, t.get("Maximum resident set size (kbytes)", "NA"), code)
    return code


def record(args, timing, wall, cpu, rss, code):
    """One line of timings.tsv. Repetition 0 is the discarded run that fills the page cache."""
    table = os.path.join(args.work, "timings.tsv")
    new = not os.path.exists(table)
    cols = ["engine", "benchmark", "run", "database", "stage", "threads", "repetition"]
    with open(table, "a", encoding="utf-8") as f:
        if new:
            f.write("\t".join(cols + ["wall_s", "cpu_s", "max_rss_kb", "exit"]) + "\n")
        f.write("\t".join([str(timing[c]) for c in cols] + [f"{wall:.2f}", f"{cpu:.2f}", str(rss), str(code)]) + "\n")


# ---------------------------------------------------------------- versions, databases, fetch, convert
def versions(args):
    tools = [[os.path.join(args.openms_bin, t), "--help"] for t in ("ProSE", "FileConverter", "EntrapmentEvaluator", "FalseDiscoveryRate")]
    tools += [[args.sage, "--version"], ["java", "-jar", args.msfragger_jar, "--version"], [args.percolator, "--version"]]
    lines = []
    for cmd in tools:
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, errors="replace", timeout=120)
            found = [x.strip() for x in (r.stdout + r.stderr).splitlines() if re.search(r"version|\d+\.\d+", x, re.I)]
            lines.append(" ".join(cmd) + "\t" + (" | ".join(found[:3]) or "no version line"))
        except (OSError, subprocess.TimeoutExpired) as err:
            lines.append(" ".join(cmd) + f"\tNOT FOUND ({err.__class__.__name__})")
    print("\n".join(lines))
    if not args.dry_run:
        open(os.path.join(args.work, "versions.txt"), "w", encoding="utf-8").write("\n".join(lines) + "\n")


def dbs(args):
    """Every database of the run table -> W/db: a .fasta next to the run table, or datasets/databases/<name>.gz.
    The SHA256 of the uncompressed file is checked against the lists in datasets/."""
    sums = {}
    for lst in ("entrapment_dbs.sha256", "section2_dbs.sha256", "plain_td_dbs.sha256"):
        for line in open(os.path.join(REPO, "datasets", lst)):
            if line.strip():
                h, n = line.split()
                sums[os.path.basename(n.lstrip("*"))] = h
    d, missing = os.path.join(args.work, "db"), []
    need = sorted({db for r in runs(args) for kind in ("td", "entrap", "ref") for db in databases(r, kind)})
    for name in need:
        dest = os.path.join(d, name)
        local, packed = os.path.join(os.path.dirname(args.runs), name), os.path.join(REPO, "datasets", "databases", name + ".gz")
        if not os.path.exists(local) and not os.path.exists(packed):
            missing.append(name)
            continue
        log(args, f"database {name} <- {local if os.path.exists(local) else packed}")
        if args.dry_run:
            continue
        os.makedirs(d, exist_ok=True)
        if not os.path.exists(dest):
            with (open(local, "rb") if os.path.exists(local) else gzip.open(packed)) as a, open(dest + ".part", "wb") as b:
                shutil.copyfileobj(a, b)
            os.replace(dest + ".part", dest)
        if name in sums and sha256(dest) != sums[name]:
            sys.exit(f"{name}: SHA256 differs from the list in datasets/")
    if missing:
        sys.exit("databases not in the repository: " + ", ".join(missing))


def fetch(args):
    d = os.path.join(args.work, "vendor")
    for r in runs(args):
        dest = os.path.join(d, os.path.basename(r["url"]))
        if os.path.exists(dest):
            continue
        log(args, f"fetch {r['url']}")
        if not args.dry_run:
            os.makedirs(d, exist_ok=True)
            urllib.request.urlretrieve(r["url"], dest + ".part")
            os.replace(dest + ".part", dest)


def convert(args):
    fc = os.path.join(args.openms_bin, "FileConverter")
    v, m = os.path.join(args.work, "vendor"), os.path.join(args.work, "mzml")
    for r in runs(args):
        out = mzml(args, r)
        if os.path.exists(out):
            continue
        src = os.path.join(v, os.path.basename(r["url"]))
        extra = []
        if not args.dry_run:
            os.makedirs(m, exist_ok=True)
        if r["format"] == "mzML":  # the smoke test: already mzML, taken as it is
            log(args, f"copy {src} -> {out}")
            if not args.dry_run:
                shutil.copyfile(src, out)
            continue
        if r["format"] == "raw":
            extra = ["-RawToMzML:reader", "inprocess"]
        elif r["format"] == "d.tar.gz":  # unpack to <id>.d first; a .d.zip is read directly
            unpacked = os.path.join(v, r["id"] + ".d")
            if not args.dry_run and not os.path.exists(unpacked):
                with tarfile.open(src) as t:
                    t.extractall(os.path.join(v, r["id"] + ".unpack"))
                found = [os.path.join(p, x) for p, ds, _ in os.walk(os.path.join(v, r["id"] + ".unpack"))
                         for x in ds if x.endswith(".d")]
                assert len(found) == 1, f"{r['id']}: expected one .d folder, found {found}"
                os.replace(found[0], unpacked)
            src = unpacked
        elif r["format"] in ("ms2.gz", "ms2.tar.gz"):
            plain = os.path.join(v, r["id"] + ".ms2")
            if not args.dry_run and not os.path.exists(plain):
                if r["format"] == "ms2.gz":
                    with gzip.open(src) as a, open(plain, "wb") as b:
                        shutil.copyfileobj(a, b)
                else:  # the worm archive holds worm-01 ... worm-12
                    with tarfile.open(src) as t:
                        member = [x for x in t.getmembers() if os.path.basename(x.name) == r["id"] + ".ms2"]
                        assert len(member) == 1, f"{r['id']}.ms2 not found in {src}"
                        with t.extractfile(member[0]) as a, open(plain, "wb") as b:
                            shutil.copyfileobj(a, b)
            src = plain
        logf = out + ".log"  # everything FileConverter prints, kept as the record of the conversion
        code = call(args, [fc, "-in", src, "-out", out + ".part.mzML"] + extra, output=logf)
        if args.dry_run:
            continue
        assert code == 0, f"{r['id']}: FileConverter failed, see {logf}"
        if "TIMS calibration: Bruker SDK" in open(logf, errors="replace").read():
            sys.exit(f"{r['id']}: converted with the Bruker SDK (section 4.0 forbids it)")
        os.replace(out + ".part.mzML", out)
        with open(os.path.join(args.work, "mzml.sha256"), "a") as f:
            f.write(f"{sha256(out)}  {os.path.basename(out)}\n")


# ---------------------------------------------------------------- the engines
def mod_masses(names):
    """['Carbamidomethyl (C)', 'TMT6plex (N-term)'] -> {'C': 57.02, '^': 229.16}"""
    out = {}
    for n in names:
        name, site = n.rstrip(")").split(" (")
        out["^" if site == "N-term" else site] = MASS[name]
    return out


def sage_config(c, ions, db):
    """Sage v0.14.7. An empty cleave_at is the non-specific digestion."""
    cut, nocut, _ = ENZYME[c["enzyme"]]
    da = c["precursor:mass_tolerance_unit"] == "Da"
    lo, hi = float(c["precursor:mass_tolerance_lower"]), float(c["precursor:mass_tolerance_upper"])
    ft = float(c["fragment:mass_tolerance"])
    database = {
        "enzyme": {"missed_cleavages": int(c["peptide:missed_cleavages"]), "min_len": int(c["peptide:min_size"]),
                   "max_len": int(c["peptide:max_size"]), "cleave_at": "" if cut is None else cut,
                   "restrict": nocut or None, "c_terminal": True},
        "static_mods": mod_masses(c["modifications:fixed"]),
        "variable_mods": {k: [v] for k, v in mod_masses(c["modifications:variable"]).items()},
        "max_variable_mods": int(c["modifications:variable_max_per_peptide"]),
        "peptide_min_mass": float(c["peptide:min_mass"]), "peptide_max_mass": float(c["peptide:max_mass"]),
        "ion_kinds": IONS[ions], "decoy_tag": c["decoy_prefix"], "generate_decoys": False, "fasta": db,
    }
    return {
        "database": database,
        "precursor_tol": {"da" if da else "ppm": [-lo, hi]},
        "fragment_tol": {"da" if c["fragment:mass_tolerance_unit"] == "Da" else "ppm": [-ft, ft]},
        # the charges tried for a spectrum without a recorded charge; other spectra are searched at their charge
        "precursor_charge": [int(c["precursor:min_charge"]), int(c["precursor:max_charge"])],
        "isotope_errors": [int(c["precursor:isotope_error_min"]), int(c["precursor:isotope_error_max"])],
    }


def msfragger_params(c, ions, db, threads):
    """The settings written over MSFragger's own closed-search defaults (`--config closed`)."""
    cut, nocut, name = ENZYME[c["enzyme"]]
    ppm = c["precursor:mass_tolerance_unit"] == "ppm"
    lo, hi = float(c["precursor:mass_tolerance_lower"]), float(c["precursor:mass_tolerance_upper"])
    fixed, var = mod_masses(c["modifications:fixed"]), mod_masses(c["modifications:variable"])
    maxmods = c["modifications:variable_max_per_peptide"]
    iso = range(int(c["precursor:isotope_error_min"]), int(c["precursor:isotope_error_max"]) + 1)
    p = {
        "database_name": db, "num_threads": threads, "decoy_prefix": c["decoy_prefix"],
        "precursor_mass_lower": -lo, "precursor_mass_upper": hi, "precursor_mass_units": int(ppm),
        "precursor_true_tolerance": hi, "precursor_true_units": int(ppm),
        "fragment_mass_tolerance": c["fragment:mass_tolerance"],
        "fragment_mass_units": int(c["fragment:mass_tolerance_unit"] == "ppm"),
        "isotope_error": "/".join(str(i) for i in iso),
        "search_enzyme_name_1": name, "search_enzyme_cut_1": "@" if cut is None else cut,
        "search_enzyme_nocut_1": nocut, "search_enzyme_sense_1": "C",
        "allowed_missed_cleavage_1": c["peptide:missed_cleavages"], "num_enzyme_termini": 0 if cut is None else 2,
        "digest_min_length": c["peptide:min_size"], "digest_max_length": c["peptide:max_size"],
        "digest_mass_range": f"{c['peptide:min_mass']} {c['peptide:max_mass']}",
        "clip_nTerm_M": int(c["peptide:clip_nterm_methionine"] == "true"),
        "max_variable_mods_per_peptide": maxmods,
        # the charges tried for a spectrum without a recorded charge; the recorded charge is not overridden
        "precursor_charge": f"{c['precursor:min_charge']} {c['precursor:max_charge']}", "override_charge": 0,
        "fragment_ion_series": ",".join(IONS[ions]),
        "add_C_cysteine": fixed.get("C", 0), "add_K_lysine": fixed.get("K", 0), "add_Nterm_peptide": fixed.get("^", 0),
        "output_format": "pin", "output_report_topN": 1,
    }
    for i, (site, mass) in enumerate(sorted(var.items()), 1):
        p[f"variable_mod_{i:02d}"] = f"{mass} {site} {maxmods}"
    return p


def write_fragger(defaults, path, params):
    """Default lines kept, our keys replaced, every default variable modification beyond ours removed."""
    lines, seen = [], set()
    for line in open(defaults, encoding="utf-8", errors="replace"):
        key = line.split("=")[0].strip().lstrip("# ").strip() if "=" in line else ""
        if key.startswith("variable_mod_") and key not in params:
            continue
        if key in params and not line.lstrip().startswith("#"):
            line = f"{key} = {params[key]}\n"
            seen.add(key)
        lines.append(line)
    lines += [f"{k} = {v}\n" for k, v in params.items() if k not in seen]
    open(path, "w", encoding="utf-8").writelines(lines)


def stem(f):
    return os.path.basename(f)[:-len(".mzML")]


def pooled_pin(out):
    return os.path.join(out, "pooled")


def invocations(args, engine, r, files, db, out, threads, pooled=False):
    """The command lines of one search: a list of (stage, command, environment).
    pooled: the files are the technical replicates of one sample and get one common FDR (immunopeptidomics)."""
    c, dbpath = settings(r["params"]), os.path.join(args.work, "db", db)
    extra = shlex.split(getattr(args, "extra", None) or "")
    assert not extra or engine == "prose", "--extra is for ProSE only"
    if not args.dry_run:
        os.makedirs(out, exist_ok=True)
    if engine == "prose":  # several inputs: the index is built once; one output per input
        ini = os.path.join(PARAMS, r["params"] + ".ini")
        cmd = [os.path.join(args.openms_bin, "ProSE"), "-ini", ini, "-in", *files, "-database", dbpath,
               "-out", *[os.path.join(out, stem(f) + ".idXML") for f in files],
               "-summary_out", os.path.join(out, "summary.yaml"), "-threads", str(threads)]
        if pooled:
            cmd += ["-out_merged", os.path.join(out, "merged.idXML")]
        return [("all", cmd + extra, {})]
    if engine == "sage":
        cfg = os.path.join(out, "sage.json")
        if not args.dry_run:
            json.dump(sage_config(c, r["ions"], dbpath), open(cfg, "w"), indent=1)
        return [("all", [args.sage, cfg, "-o", out, *files], {"RAYON_NUM_THREADS": str(threads)})]
    if engine == "msfragger":
        par = os.path.join(out, "fragger.params")
        local = [os.path.join(out, os.path.basename(f)) for f in files]
        if not args.dry_run:
            defaults = os.path.join(args.work, "closed_fragger.params")
            if not os.path.exists(defaults):
                subprocess.run(["java", "-jar", args.msfragger_jar, "--config", "closed"], cwd=args.work, check=True)
            write_fragger(defaults, par, msfragger_params(c, r["ions"], dbpath, threads))
            for f, link in zip(files, local):  # MSFragger writes its .pin next to the input
                if not os.path.exists(link):
                    os.symlink(os.path.abspath(f), link)
        cmds = [("search", ["java", f"-Xmx{args.java_gb}g", "-jar", args.msfragger_jar, par, *local], {})]
        pins = [f[:-len(".mzML")] for f in local]
        if pooled:  # one Percolator run over the replicates: the .pin files are joined first
            cmds.append(("join", [sys.executable, os.path.abspath(__file__), "--work", args.work, "joinpins",
                                  pooled_pin(out) + ".pin", *[p + ".pin" for p in pins]], {}))
            pins = [pooled_pin(out)]
        for p in pins:  # FragPipe's Percolator options, without --only-psms (the peptide level is needed)
            cmds.append(("rescoring", [args.percolator, "--num-threads", str(threads), "--no-terminate",
                                       "--post-processing-tdc", "--protein-decoy-pattern", c["decoy_prefix"],
                                       "--results-psms", p + ".psms.tsv", "--decoy-results-psms", p + ".decoy_psms.tsv",
                                       "--results-peptides", p + ".peptides.tsv",
                                       "--decoy-results-peptides", p + ".decoy_peptides.tsv", p + ".pin"], {}))
        return cmds
    sys.exit(f"unknown engine {engine}")


def joinpins(args):
    """Joins Percolator input files under one header. The scan numbers of file i get i * 10 million added, so that
    spectra of different files never share a scan number (Percolator pairs targets and decoys by scan)."""
    with open(args.out, "w", encoding="utf-8") as o:
        for i, p in enumerate(args.pins):
            with open(p, encoding="utf-8") as f:
                head = f.readline()
                scan = head.rstrip("\n").split("\t").index("ScanNr")
                if i == 0:
                    o.write(head)
                for line in f:
                    x = line.split("\t")
                    x[scan] = str(int(x[scan]) + i * 10_000_000)
                    o.write("\t".join(x))


def measure(args, engine, bench, name, r, files, db, threads, timed, pin=None, limit=None, pooled=False, warm=True):
    bench = bench_name(args, bench)
    out = outdir(args, engine, bench, name, db, threads if bench.startswith("scaling") else None)
    # repetition 0 fills the page cache; it is recorded as repetition 0 and not used
    for rep in (([0] if warm else []) + [1, 2, 3] if timed else [1]):
        for stage, cmd, env in invocations(args, engine, r, files, db, out, threads, pooled):
            timing = None
            if timed:
                timing = dict(engine=engine, benchmark=bench, run=name, database=db, stage=stage, threads=threads, repetition=rep)
            if call(args, cmd, env, timing, pin, limit) == "over_limit":
                return True  # recorded as over the limit; no further repetitions
    return False


def units(rows, key):
    """Rows grouped by a column, in table order; '-' means no group."""
    out = {}
    for r in rows:
        if r[key] != "-":
            out.setdefault(r[key], []).append(r)
    return out


def searches(args):
    """(name, first row, rows): one per run; immunopeptidomics: one per sample over its technical replicates."""
    rows = runs(args)
    return [(n, rs[0], rs) for n, rs in units(rows, "sample").items()] + [(r["id"], r, [r]) for r in rows if r["sample"] == "-"]


# ---------------------------------------------------------------- the benchmarks
def search(args):
    for name, r, rs in searches(args):
        for db in databases(r, args.db):
            measure(args, args.engine, "per_file", name, r, [mzml(args, x) for x in rs], db, args.threads, args.timed,
                    pooled=len(rs) > 1)


def batch(args):
    for name, rs in units([r for r in runs(args) if r["sample"] == "-"], "group").items():
        if len(rs) < 2:
            continue  # a group of one file has no batch
        assert len({(r["params"], r["db"], r["ions"]) for r in rs}) == 1, f"{name}: mixed settings in one batch"
        measure(args, args.engine, "batch", name, rs[0], [mzml(args, r) for r in rs], databases(rs[0], "td")[0],
                args.threads, True)


def scaling(args):
    grid = sorted((int(x) for x in args.grid.split(",")), reverse=True) if args.grid else GRID[::-1]
    for r in runs(args):
        if r["scaling"] != "1":
            continue
        for i, n in enumerate(grid):  # from the highest thread count down; the page cache is filled once per file
            # whole cores: logical CPUs 0..n-1 must be n different physical cores (check with lscpu -e).
            # Sage 0.14.7 aborts on a single core ("chunk size must be non-zero": it reads num_cpus / 2 files at a
            # time), so its one-thread point runs one search thread on two cores.
            cores = 2 if args.engine == "sage" and n == 1 else n
            db, limit = databases(r, "td")[0], args.limit_hours * 3600
            if measure(args, args.engine, "scaling", r["id"], r, [mzml(args, r)], db, n, True,
                       pin=f"0-{cores - 1}", limit=limit, warm=(i == 0)):
                # over the limit at n threads: fewer threads take longer still, so they are recorded and not run
                for m in grid[i + 1:]:
                    log(args, f"# {args.engine} {r['id']}: {m} threads not run (over the limit at {n} threads)")
                    record(args, dict(engine=args.engine, benchmark="scaling", run=r["id"], database=db, stage="all",
                                      threads=m, repetition=1), limit, float("nan"), "NA", "not_run_over_limit")
                break


# ---------------------------------------------------------------- counting: every engine through EntrapmentEvaluator
def bare(peptide):
    """'K.PEPTM[15.9949]IDEK.R' or 'PEPTM[+15.9949]IDEK' -> 'PEPTMIDEK'"""
    p = re.sub(r"\[[^\]]*\]|\([^)]*\)", "", peptide)
    if len(p) > 4 and p[1] == "." and p[-2] == ".":
        p = p[2:-2]
    return re.sub(r"[^A-Z]", "", p)


def write_idxml(path, engine, psms):
    """psms: (spectrum, unmodified sequence, [accessions], PSM q-value, peptide q-value), target top hits only.
    A minimal idXML for EntrapmentEvaluator: q-value as main score, 'peptide q-value' as meta value."""
    acc = {}
    for _, _, proteins, _, _ in psms:
        for a in proteins:
            acc.setdefault(a, f"PH_{len(acc)}")
    with open(path, "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n<IdXML version="1.5">\n'
                '\t<SearchParameters id="SP_0" db="" db_version="" taxonomy="" mass_type="monoisotopic" charges="" '
                'enzyme="unknown_enzyme" missed_cleavages="0" precursor_peak_tolerance="0" '
                'precursor_peak_tolerance_ppm="false" peak_mass_tolerance="0" peak_mass_tolerance_ppm="false"/>\n'
                f'\t<IdentificationRun date="2026-01-01T00:00:00" search_engine={quoteattr(engine)} '
                'search_engine_version="" search_parameters_ref="SP_0">\n'
                '\t\t<ProteinIdentification score_type="" higher_score_better="true" significance_threshold="0">\n')
        for a, i in acc.items():
            f.write(f'\t\t\t<ProteinHit id="{i}" accession={quoteattr(a)} score="0" sequence=""/>\n')
        f.write('\t\t</ProteinIdentification>\n')
        for spectrum, seq, proteins, q, pq in psms:
            f.write('\t\t<PeptideIdentification score_type="q-value" higher_score_better="false" '
                    f'significance_threshold="0" MZ="0" RT="0" spectrum_reference={quoteattr(spectrum)}>\n'
                    f'\t\t\t<PeptideHit sequence="{seq}" charge="0" score="{q}" '
                    f'protein_refs="{" ".join(acc[a] for a in proteins)}">\n'
                    '\t\t\t\t<UserParam type="string" name="target_decoy" value="target"/>\n'
                    f'\t\t\t\t<UserParam type="float" name="peptide q-value" value="{pq}"/>\n'
                    '\t\t\t</PeptideHit>\n\t\t</PeptideIdentification>\n')
        f.write('\t</IdentificationRun>\n</IdXML>\n')


def sage_psms(out):
    """results.sage.tsv -> {file stem: psms}; target top hits; spectrum_q and peptide_q are Sage's own q-values."""
    res = {}
    for row in csv.DictReader(open(os.path.join(out, "results.sage.tsv"), encoding="utf-8"), delimiter="\t"):
        if row["label"] != "1" or row["rank"] != "1":
            continue
        res.setdefault(stem(row["filename"]), []).append(
            (row["scannr"], bare(row["peptide"]), row["proteins"].split(";"), row["spectrum_q"], row["peptide_q"]))
    return res


def percolator_psms(prefix):
    """Percolator target tables -> psms. The protein columns are the tab-separated tail of each line."""
    def table(path):
        with open(path, encoding="utf-8") as f:
            head = f.readline().rstrip("\n").split("\t")
            for line in f:
                x = line.rstrip("\n").split("\t")
                yield dict(zip(head[:-1], x)), x[len(head) - 1:]
    pq = {row["peptide"]: row["q-value"] for row, _ in table(prefix + ".peptides.tsv")}
    return [(row["PSMId"], bare(row["peptide"]), proteins, row["q-value"], pq.get(row["peptide"], "1"))
            for row, proteins in table(prefix + ".psms.tsv")]


def count(args):
    """Writes <run>.count.idXML per result and runs EntrapmentEvaluator on it: with the plain target-decoy database
    the accepted PSMs and peptides are the identification counts, with an entrapment database the FDP follows."""
    ee = os.path.join(args.openms_bin, "EntrapmentEvaluator")
    for name, r, rs in searches(args):
        pooled = len(rs) > 1
        for db in databases(r, args.db):
            out = outdir(args, args.engine, bench_name(args, "per_file"), name, db)
            ids = [os.path.join(out, (x["id"] if not pooled else "pooled") + ".count.idXML") for x in (rs[:1] if pooled else rs)]
            if not args.dry_run:
                if args.engine == "prose" and not pooled:
                    # ProSE names its peptide-level q-value 'percolator_peptide_q_value'; EntrapmentEvaluator reads
                    # 'peptide q-value'. The copy differs from the result only in this name.
                    for x, dest in zip(rs, ids):
                        text = open(os.path.join(out, x["id"] + ".idXML"), encoding="utf-8").read()
                        open(dest, "w", encoding="utf-8").write(text.replace('name="percolator_peptide_q_value"', 'name="peptide q-value"'))
                elif args.engine == "sage":
                    res = sage_psms(out)
                    psms = [p for x in rs for p in res.get(x["id"], [])] if pooled else res.get(rs[0]["id"], [])
                    write_idxml(ids[0], "Sage", psms)
                elif args.engine == "msfragger":
                    write_idxml(ids[0], "MSFragger", percolator_psms(pooled_pin(out) if pooled else os.path.join(out, rs[0]["id"])))
            if args.engine == "prose" and pooled:
                # section 4.2: peptide-level FDR on the pooled replicates with FalseDiscoveryRate
                call(args, [os.path.join(args.openms_bin, "FalseDiscoveryRate"), "-in", os.path.join(out, "merged.idXML"),
                            "-out", ids[0], "-PSM", "false", "-peptide", "true", "-protein", "false"])
            call(args, [ee, "-in", *ids, "-database", os.path.join(args.work, "db", db), "-q_value", "0.01",
                        "-out", os.path.join(out, "count.tsv")])


def collect(args):
    """Every count.tsv of W/out -> W/counts.tsv, with the engine, benchmark, run and database in front."""
    paths = sorted(glob.glob(os.path.join(args.work, "out", "*", "*", "*", "*", "count.tsv")))
    lines, head = [], None
    for p in paths:
        engine, bench, run, db = os.path.normpath(p).split(os.sep)[-5:-1]
        with open(p, encoding="utf-8") as f:
            h = f.readline().rstrip("\n")
            assert head in (None, h), f"{p}: another header"
            head = h
            lines += [f"{engine}\t{bench}\t{run}\t{db}\t{x}" for x in f.read().splitlines() if x]
    print(f"{len(paths)} count.tsv, {len(lines)} rows")
    if paths and not args.dry_run:
        open(os.path.join(args.work, "counts.tsv"), "w", encoding="utf-8").write(
            "engine\tbenchmark\trun\tdatabase\t" + head + "\n" + "\n".join(lines) + "\n")


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--work", required=True)
    p.add_argument("--runs", default=os.path.join(HERE, "runs.tsv"), help="run table (default: runs.tsv next to this file)")
    p.add_argument("--only", help="comma-separated run ids")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--openms-bin", default=os.environ.get("OPENMS_BIN", ""))
    p.add_argument("--sage", default=os.environ.get("SAGE", "sage"))
    p.add_argument("--msfragger-jar", default=os.environ.get("MSFRAGGER_JAR", "MSFragger.jar"))
    p.add_argument("--percolator", default=os.environ.get("PERCOLATOR", "percolator"))
    p.add_argument("--java-gb", type=int, default=200, help="Java heap of MSFragger in GB")
    sub = p.add_subparsers(dest="stage", required=True)
    for name, f in (("versions", versions), ("databases", dbs), ("fetch", fetch), ("convert", convert), ("collect", collect)):
        sub.add_parser(name).set_defaults(f=f)
    for name, f in (("search", search), ("count", count), ("batch", batch), ("scaling", scaling)):
        s = sub.add_parser(name)
        s.set_defaults(f=f)
        s.add_argument("--engine", required=True, choices=["prose", "sage", "msfragger"])
        if name in ("search", "batch"):
            s.add_argument("--threads", type=int, default=64)
        if name in ("search", "count"):
            s.add_argument("--db", required=True, choices=["td", "entrap", "ref"])
            s.add_argument("--tag", help="name of an extra arm, e.g. standard_mode; its results go to per_file_<tag>")
        if name == "search":
            s.add_argument("--timed", action="store_true")
            s.add_argument("--extra", help="further ProSE options of an extra arm, e.g. '-Search:low_memory false'")
        if name == "scaling":
            s.add_argument("--grid", help="comma-separated thread counts (default: the grid of section 4.3)")
            s.add_argument("--limit-hours", type=float, default=24.0, help="wall-time limit per run (default 24)")
    j = sub.add_parser("joinpins")  # internal: joins Percolator input files, keeping one header
    j.set_defaults(f=joinpins)
    j.add_argument("out")
    j.add_argument("pins", nargs="+")
    args = p.parse_args()
    args.runs = os.path.abspath(args.runs)
    if not args.dry_run:
        os.makedirs(args.work, exist_ok=True)
    args.f(args)


if __name__ == "__main__":
    main()
