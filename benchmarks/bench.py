#!/usr/bin/env python3
"""Driver of the ProSE publication benchmark (datasets/DATASETS.md, sections 4.2 to 4.5).

Every stage reads the run table runs.tsv (one row per run) and the ProSE parameter files datasets/params/*.ini.
The Sage and MSFragger configurations are translated from the values in those files (ProSE defaults included),
so no file is selected and no setting is typed by hand.

  bench.py --work W fetch                      download the vendor files
  bench.py --work W convert                    vendor files -> mzML with FileConverter, SHA256 of every mzML
  bench.py --work W search  --engine E --db D  one invocation per run (immunopeptidomics: per sample);
                                               D = td (counts, timings), entrap (FDP), ref (Arabidopsis)
                                               --timed: one discarded run, then three under /usr/bin/time -v
  bench.py --work W count   --engine E --db D  results -> idXML -> EntrapmentEvaluator: accepted PSMs and peptides
                                               at q <= 0.01 (td) and the entrapment FDP (entrap, ref)
  bench.py --work W batch   --engine E         all files of a group in one invocation (timed)
  bench.py --work W scaling --engine E         thread grid on the scaling files (timed, pinned, 24 h limit)

Common options: --only ID[,ID...] restricts to some runs, --dry-run prints the commands and runs nothing.
Tools come from --openms-bin, --sage, --msfragger-jar, --percolator (or the environment variables OPENMS_BIN,
SAGE, MSFRAGGER_JAR, PERCOLATOR). Databases are expected in W/db, uncompressed, under the names of DATASETS.md.

Work directory: vendor/ mzml/ db/ out/<engine>/<benchmark>/<run>/<database>/ commands.log timings.tsv mzml.sha256

Checked against the sources (2026-11-10): the ProSE and EntrapmentEvaluator options (OpenMS develop), the Sage
configuration (v0.14.7), the MSFragger parameter names and the non-specific enzyme (FragPipe workflows).
Sage has no z+1 ions in any release, so it is not run on the electron-based runs (column `ions` = bycz).
Differences that remain: Sage does not clip the protein N-terminal methionine (ProSE and MSFragger do); the fragment
m/z range, fragment charges, minimum matched ions and deisotoping stay at each engine's default.

STATUS: draft, checked in --dry-run mode. The result parsers and the idXML writer were checked on made-up tables
(the idXML is read by OpenMS 3.1 TextExporter). No search was run. Still to check on the first real run:
EntrapmentEvaluator on a database without entrapment proteins (the plain target-decoy counts), and the
FalseDiscoveryRate options of the pooled immunopeptidomics results.
"""
import argparse, csv, gzip, hashlib, json, os, re, shlex, shutil, subprocess, sys, tarfile, urllib.request
from xml.sax.saxutils import quoteattr

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
PARAMS = os.path.join(REPO, "datasets", "params")
sys.dont_write_bytecode = True
sys.path.insert(0, PARAMS)
import xml.etree.ElementTree as ET  # noqa: E402
from make_inis import items, value  # noqa: E402  (the readers of the ProSE parameter files)

GRID = [1, 2, 4, 8, 16, 32, 48, 64, 96, 128, 192]
LIMIT_S = 24 * 3600
MASS = {"Carbamidomethyl": 57.021464, "Oxidation": 15.994915, "TMT6plex": 229.162932, "TMTpro": 304.207146}
# enzyme -> (cleave after, not before)
ENZYME = {"Trypsin/P": ("KR", ""), "Chymotrypsin": ("FYWL", "P"), "unspecific cleavage": (None, "")}
# ProSE scores electron-activated spectra with b, y, c and z+1 ions (Search:ions:by_activation)
IONS = {"by": ["b", "y"], "bycz": ["b", "y", "c", "z"]}


# ---------------------------------------------------------------- run table and helpers
def settings(name):
    """The Search:* values of a ProSE parameter file, e.g. {'enzyme': 'Trypsin/P', 'peptide:min_size': '7', ...}"""
    it = items(ET.parse(os.path.join(PARAMS, name + ".ini")).getroot())
    return {k[len("Search:"):]: value(v) for k, v in it.items() if k.startswith("Search:")}


def runs(args):
    rows = list(csv.DictReader(open(os.path.join(HERE, "runs.tsv"), encoding="utf-8"), delimiter="\t"))
    ids = [r["id"] for r in rows]
    assert len(ids) == len(set(ids)), "runs.tsv: duplicate id"
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
    return rows


def databases(r, kind):
    if kind == "td":
        return [r["db"] + "_td.fasta"]
    return [x for x in r["entrap" if kind == "entrap" else "ref"].split(";") if x != "-"]


def mzml(args, r):
    return os.path.join(args.work, "mzml", r["id"] + ".mzML")


def outdir(args, engine, bench, name, db, threads=None):
    return os.path.join(args.work, "out", engine, bench, name, db[:-len(".fasta")] + (f"_t{threads}" if threads else ""))


def log(args, text):
    print(text, flush=True)
    if not args.dry_run:
        with open(os.path.join(args.work, "commands.log"), "a", encoding="utf-8") as f:
            f.write(text + "\n")


def call(args, cmd, env=None, timing=None, pin=None, limit=None):
    """Runs cmd. timing = dict of labels: runs under /usr/bin/time -v and appends a line to timings.tsv."""
    if pin:
        cmd = ["taskset", "-c", pin] + cmd
    tfile = os.path.join(args.work, "time.txt")
    if timing is not None:
        cmd = ["/usr/bin/time", "-v", "-o", tfile] + cmd
    show = " ".join(f"{k}={v}" for k, v in (env or {}).items())
    log(args, (show + " " if show else "") + " ".join(shlex.quote(c) for c in cmd))
    if args.dry_run:
        return 0
    e = dict(os.environ, **(env or {}))
    e.pop("OPENMS_BRUKER_SDK_PATH", None)  # section 4.0: never the Bruker SDK
    try:
        code = subprocess.run(cmd, env=e, timeout=limit).returncode
    except subprocess.TimeoutExpired:
        code = "over_limit"
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
        cpu = float(t.get("User time (seconds)", 0)) + float(t.get("System time (seconds)", 0))
        out = os.path.join(args.work, "timings.tsv")
        new = not os.path.exists(out)
        cols = ["engine", "benchmark", "run", "database", "stage", "threads", "repetition"]
        with open(out, "a", encoding="utf-8") as f:
            if new:
                f.write("\t".join(cols + ["wall_s", "cpu_s", "max_rss_kb", "exit"]) + "\n")
            f.write("\t".join([str(timing[c]) for c in cols] + [f"{wall:.2f}", f"{cpu:.2f}",
                    t.get("Maximum resident set size (kbytes)", "NA"), str(code)]) + "\n")
    return code


# ---------------------------------------------------------------- fetch and convert
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
        logf = out + ".log"
        code = call(args, [fc, "-in", src, "-out", out] + extra + ["-log", logf])
        if args.dry_run:
            continue
        assert code == 0, f"{r['id']}: FileConverter failed"
        if "TIMS calibration: Bruker SDK" in open(logf, errors="replace").read():
            sys.exit(f"{r['id']}: converted with the Bruker SDK (section 4.0 forbids it)")
        h = hashlib.sha256()
        with open(out, "rb") as f:
            for block in iter(lambda: f.read(1 << 24), b""):
                h.update(block)
        with open(os.path.join(args.work, "mzml.sha256"), "a") as f:
            f.write(f"{h.hexdigest()}  {os.path.basename(out)}\n")


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
    cut, nocut = ENZYME[c["enzyme"]]
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
        "precursor_charge": [int(c["precursor:min_charge"]), int(c["precursor:max_charge"])],
        "isotope_errors": [int(c["precursor:isotope_error_min"]), int(c["precursor:isotope_error_max"])],
    }


def msfragger_params(c, ions, db, threads):
    """The settings written over MSFragger's own closed-search defaults (`--config closed`)."""
    cut, nocut = ENZYME[c["enzyme"]]
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
        "search_enzyme_name_1": "nonspecific" if cut is None else c["enzyme"],
        "search_enzyme_cut_1": "@" if cut is None else cut, "search_enzyme_nocut_1": nocut,
        "search_enzyme_sense_1": "C", "allowed_missed_cleavage_1": c["peptide:missed_cleavages"],
        "num_enzyme_termini": 0 if cut is None else 2,
        "digest_min_length": c["peptide:min_size"], "digest_max_length": c["peptide:max_size"],
        "digest_mass_range": f"{c['peptide:min_mass']} {c['peptide:max_mass']}",
        "clip_nTerm_M": int(c["peptide:clip_nterm_methionine"] == "true"),
        "max_variable_mods_per_peptide": maxmods,
        "precursor_charge": f"{c['precursor:min_charge']} {c['precursor:max_charge']}",
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
    if not args.dry_run:
        os.makedirs(out, exist_ok=True)
    if engine == "prose":  # several inputs: the index is built once; one output per input
        ini = os.path.join(PARAMS, r["params"] + ".ini")
        cmd = [os.path.join(args.openms_bin, "ProSE"), "-ini", ini, "-in", *files, "-database", dbpath,
               "-out", *[os.path.join(out, stem(f) + ".idXML") for f in files],
               "-summary_out", os.path.join(out, "summary.yaml"), "-threads", str(threads)]
        if pooled:
            cmd += ["-out_merged", os.path.join(out, "merged.idXML")]
        return [("all", cmd, {})]
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
    with open(args.out, "w", encoding="utf-8") as o:
        for i, p in enumerate(args.pins):
            with open(p, encoding="utf-8") as f:
                head = f.readline()
                if i == 0:
                    o.write(head)
                shutil.copyfileobj(f, o)


def measure(args, engine, bench, name, r, files, db, threads, timed, pin=None, limit=None, pooled=False):
    out = outdir(args, engine, bench, name, db, threads if bench == "scaling" else None)
    for rep in ([0, 1, 2, 3] if timed else [1]):  # repetition 0 fills the page cache and is not recorded
        for stage, cmd, env in invocations(args, engine, r, files, db, out, threads, pooled):
            timing = None
            if timed and rep > 0:
                timing = dict(engine=engine, benchmark=bench, run=name, database=db, stage=stage, threads=threads, repetition=rep)
            if call(args, cmd, env, timing, pin, limit) == "over_limit":
                return  # reported as over the limit; no further repetitions


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
    for r in runs(args):
        if r["scaling"] != "1":
            continue
        for n in GRID:
            # whole cores: logical CPUs 0..n-1 must be n different physical cores (check with lscpu -e)
            measure(args, args.engine, "scaling", r["id"], r, [mzml(args, r)], databases(r, "td")[0], n, True,
                    pin=f"0-{n - 1}", limit=LIMIT_S)


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
            out = outdir(args, args.engine, "per_file", name, db)
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


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--work", required=True)
    p.add_argument("--only", help="comma-separated run ids")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--openms-bin", default=os.environ.get("OPENMS_BIN", ""))
    p.add_argument("--sage", default=os.environ.get("SAGE", "sage"))
    p.add_argument("--msfragger-jar", default=os.environ.get("MSFRAGGER_JAR", "MSFragger.jar"))
    p.add_argument("--percolator", default=os.environ.get("PERCOLATOR", "percolator"))
    p.add_argument("--java-gb", type=int, default=200, help="Java heap of MSFragger in GB")
    sub = p.add_subparsers(dest="stage", required=True)
    sub.add_parser("fetch").set_defaults(f=fetch)
    sub.add_parser("convert").set_defaults(f=convert)
    for name, f in (("search", search), ("count", count), ("batch", batch), ("scaling", scaling)):
        s = sub.add_parser(name)
        s.set_defaults(f=f)
        s.add_argument("--engine", required=True, choices=["prose", "sage", "msfragger"])
        if name in ("search", "batch"):
            s.add_argument("--threads", type=int, default=64)
        if name in ("search", "count"):
            s.add_argument("--db", required=True, choices=["td", "entrap", "ref"])
        if name == "search":
            s.add_argument("--timed", action="store_true")
    j = sub.add_parser("joinpins")  # internal: joins Percolator input files, keeping one header
    j.set_defaults(f=joinpins)
    j.add_argument("out")
    j.add_argument("pins", nargs="+")
    args = p.parse_args()
    if not args.dry_run:
        os.makedirs(args.work, exist_ok=True)
    args.f(args)


if __name__ == "__main__":
    main()
