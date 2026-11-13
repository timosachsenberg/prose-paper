#!/usr/bin/env python3
"""Driver of the ProSE publication benchmark (datasets/DATASETS.md, sections 4.2 to 4.5). Linux, Python 3 only.

Every stage reads the run table (runs.tsv, one row per run) and the ProSE parameter files datasets/params/*.ini.
The Sage and MSFragger configurations are translated from the values in those files (ProSE defaults included),
so no file is selected and no setting is typed by hand. README.md next to this file has the order of the commands.

  bench.py --work W versions                   version output of every tool -> W/versions.txt
  bench.py --work W databases                  the databases of the run table -> W/db, checked by SHA256
                                               and for one usable accession per header (check_fasta)
  bench.py --work W fetch                      download the vendor files, checked by SHA256 (vendor.sha256 next to
                                               the run table; files already there are checked too)
  bench.py --work W convert                    vendor files -> mzML with FileConverter, SHA256 of every mzML
  bench.py --work W search  --engine E --db D  one invocation per run (immunopeptidomics: per sample);
                                               D = td (counts, timings), entrap (FDP), ref (Arabidopsis)
                                               --timed: one discarded run, then three under /usr/bin/time -v
  bench.py --work W count   --engine E --db D  results -> idXML -> EntrapmentEvaluator: accepted PSMs and peptides
                                               at q <= 0.01 (td) and the entrapment FDP (entrap, ref)
  bench.py --work W collect                    all count.tsv -> W/counts.tsv; the status of every search of the run
                                               table and of every search folder -> W/coverage.tsv
  bench.py --work W batch   --engine E         all files of a group in one invocation (timed)
  bench.py --work W scaling --engine E         thread grid on the scaling files (timed, pinned, 24 h limit)

Common options, before the stage name: --only ID[,ID...] restricts to some runs (a sample name selects all its
replicates; a part of a sample is refused, as a sample is searched and counted as a whole), --dry-run prints the
commands and runs nothing, --runs FILE takes another run table (smoke/runs.tsv is a three-file test that runs in
minutes). Tools come from --openms-bin, --sage, --msfragger-jar, --percolator (or the environment variables OPENMS_BIN,
SAGE, MSFRAGGER_JAR, PERCOLATOR).

Work directory: vendor/ mzml/ db/ out/<engine>/<benchmark>/<run>/<database>/ commands.log timings.tsv counts.tsv
coverage.tsv mzml.sha256 versions.txt. A search empties its folder first. The folder holds `inputs` (the run ids) and
`status`: 'running ...' (with the process ids of the driver and of the engine) from before the engine starts, then ok,
failed ..., failed_memory ..., over_limit ... or interrupted ... (the driver was stopped; it stops the engine with it
on SIGINT, SIGTERM, SIGHUP and SIGQUIT, also when the signal comes while the engine starts: it then takes effect once
the engine's process group is known). count counts only a search whose status is ok; collect copies the status into
coverage.tsv. A search is refused while the folder's status says 'running' and that driver or engine is still alive
(e.g. an engine left behind by a driver killed with SIGKILL). Several drivers may share a work directory only if they
never run the same search folder, and never two MSFragger searches against the same database at once (its digest
cache next to the database, drop_pepindex).

Memory (DATASETS.md section 4.3): --mem-gb N runs every engine invocation in a cgroup with N GB of memory and no swap
(systemd-run --user --scope; needs a user session bus and cgroup v2 with the memory controller delegated to the user;
checked once before the stage, check_cap). A run killed at the cap, or stopped by its engine's own out-of-memory error
(out_of_memory), is recorded as failed_memory; without --mem-gb every failure is 'failed', as a kill by the kernel's
out-of-memory killer cannot be told from other kills. The engines run as one process each (MSFragger briefly starts
ldconfig), so a kill at the cap is a SIGKILL of the engine; with systemd's default OOMPolicy=stop a command of several
processes would get SIGTERM and be recorded as failed. MSFragger's Java heap is N - 4 GB (--java-gb overrides it;
without --mem-gb 80% of the memory the driver may use: the RAM, capped by its cgroup's memory.max) and at least 1 GB;
its JVM runs with -XX:+ExitOnOutOfMemoryError. Network calls of the engines are switched off: Sage's telemetry and the
OpenMS update check.

Checked against the sources (2026-11-10): the ProSE and EntrapmentEvaluator options (OpenMS develop), the Sage
configuration (v0.14.7), the MSFragger parameter names and the non-specific enzyme (FragPipe workflows).
Sage has no z+1 ions in any release, so it is not run on the electron-based runs (column `ions` = bycz).
Differences that remain: Sage does not clip the protein N-terminal methionine (ProSE and MSFragger do); OpenMS
Trypsin/P also cleaves after X, in ProSE's digestion and in its protein mapping (Sage and MSFragger cleave only after K
and R); ProSE's protein mapping also accepts a peptide that starts after the first two residues ('MX') of a protein
beginning with M (OpenMS's 'M or MX' rule; the digestion clips only the M) and matches B, J, Z and X in a protein as
wildcards; the fragment m/z range, deisotoping and mass calibration stay at each engine's default. The fragment charges
stay at each engine's default except where ProSE scores several fragment charges (not deisotoped, e.g. ion-trap CID):
there Sage gets ProSE's fragment:max_charge (sage_config). The minimum number of matched fragment ions comes from the
parameter file. MSFragger bounds the peptide mass of the unmodified sequence, ProSE and Sage that of each modified form
(neutral_mass_range). The peaks per spectrum stay at each engine's default (DATASETS.md section 4.4): Sage uses the 150
most intense deisotoped peaks (max_peaks) for candidates, scoring and its rescoring features; MSFragger uses
use_topN_peaks peaks, chosen by calibrate_mass 2 from a grid up to 300; ProSE looks up candidates with all raw peaks,
scores at most 20 peaks per 100 Th (capped by peaks:keep_n, 400 at high resolution) and computes its ion-prior and
local fragment evidence features on all deisotoped peaks. On dense spectra (astral_A2, a median of 978 raw peaks) this
costs Sage and MSFragger identifications.
The count takes the target and decoy labels from one search space for every engine, the parameter file's digestion of
the target proteins (relabel, il_twins; DATASETS.md section 4.2): a decoy PSM whose sequence equals a target peptide
of that space with I = L counts as a target, and a target PSM that also maps to a decoy protein (ProSE's
'target+decoy') counts as a target only if it is a target peptide of that space.

Extra arms (e.g. the calibration ablation, DATASETS.md section 4.4): search --extra '<settings>' --tag NAME writes to
per_file_NAME; the settings are ProSE options, Sage configuration keys or MSFragger parameters (extra_settings).
Sage's write_pin and annotate_matches become its flags --write-pin and --annotate-matches (SAGE_FLAGS), as Sage takes
them from its command line only. Sage searches with the fragment tolerance of the parameter file in every arm: it does
not calibrate, and no arm gives it a tolerance from another engine's calibration (decided 2026-11-13, DATASETS.md
section 4.4; the arm --prose-fragment-tol of 2026-11-12 was removed).

STATUS (2026-11-12): every stage was run with all three engines, the frozen OpenMS build, Sage 0.14.7, MSFragger 4.4.1
and Percolator 3.09 on the smoke test and on astral250pg_A2 and ultra2_A2 (2026-11-11); after the changes of that day
both files were searched and counted again with all three engines, and astral250pg_A2 again after those of 2026-11-12,
with the arms of the calibration supplement (README.md, DATASETS.md section 4.5).
After the changes of 2026-11-13 (memory cap, MSFragger's digest cache and uncalibrated spectra, status and coverage,
I = L twins and target+decoy labels, protein lists and accession checks, MSFragger's mass bounds, Sage's fragment
charges, telemetry, Sage's one-thread point, interrupted and concurrent runs; DATASETS.md section 5): the smoke test
with all three engines (23 of 23 steps exit 0, coverage.tsv agrees with counts.tsv), one test per failure case,
tims_plasma_30min and astral_A2 with all three engines, MSFragger on velos_5000_R2, and a count again of all pilot
results (only ProSE on pxd011695_EThcD changes, by the target+decoy rule); README.md 'Tested on 2026-11-13',
DATASETS.md section 4.5. After the astral_A2 analysis of that day (SAGE_FLAGS, and --prose-fragment-tol removed): the
64 dry runs and one Sage search of the smoke test with write_pin.
"""
import argparse, csv, fcntl, glob, gzip, hashlib, json, os, re, shlex, shutil, signal, subprocess, sys, tarfile
import tempfile
import urllib.request
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
PROTON = 1.007276
WATER = 18.010565
# the keys of a Sage 0.14.7 configuration (sage-cli/src/input.rs, Input; crates/sage/src/database.rs, Builder): Sage
# ignores keys it does not know, so --extra accepts only these
SAGE_KEYS = {"database", "precursor_tol", "fragment_tol", "report_psms", "chimera", "wide_window", "min_peaks",
             "max_peaks", "max_fragment_charge", "min_matched_peaks", "precursor_charge", "isotope_errors", "deisotope",
             "quant", "predict_rt"}
# two further keys of the configuration that Sage 0.14.7 overwrites with its command-line flags (input.rs, the flags
# read false when absent), so a key alone has no effect: --extra write_pin=true becomes the flag --write-pin
SAGE_FLAGS = {"write_pin": "--write-pin", "annotate_matches": "--annotate-matches"}
SAGE_DB_KEYS = {"bucket_size", "enzyme", "fragment_min_mz", "fragment_max_mz", "peptide_min_mass", "peptide_max_mass",
                "ion_kinds", "min_ion_index", "static_mods", "variable_mods", "max_variable_mods", "decoy_tag",
                "generate_decoys"}
# ProSE enzyme -> (cleave after, not before, MSFragger's name of the enzyme)
ENZYME = {"Trypsin/P": ("KR", "", "stricttrypsin"), "unspecific cleavage": (None, "", "nonspecific")}
# ProSE scores electron-activated spectra with b, y, c and z+1 ions (Search:ions:by_activation)
IONS = {"by": ["b", "y"], "bycz": ["b", "y", "c", "z"]}
# the engines' own out-of-memory errors in the log of a failed step (out_of_memory): MSFragger's Java heap (with
# -XX:+ExitOnOutOfMemoryError 'Terminating due to java.lang.OutOfMemoryError: Java heap space', without it 'Not enough
# memory allocated to MSFragger.', and its check before the search 'Insufficient memory!'); std::bad_alloc of ProSE
# and Percolator; Rust's 'memory allocation of N bytes failed' (Sage). Exit 3 of the JVM alone is not enough: other
# OutOfMemoryErrors ('Requested array size exceeds VM limit') give it too
OOM = re.compile(r"java\.lang\.OutOfMemoryError: (Java heap space|GC overhead limit exceeded)|Not enough memory "
                 r"allocated to MSFragger|Insufficient memory!|std::bad_alloc|memory allocation of \d+ bytes failed")


# ---------------------------------------------------------------- run table and helpers
def settings(name):
    """The Search:* values of a ProSE parameter file, e.g. {'enzyme': 'Trypsin/P', 'peptide:min_size': '7', ...}"""
    it = items(ET.parse(os.path.join(PARAMS, name + ".ini")).getroot())
    return {k[len("Search:"):]: value(v) for k, v in it.items() if k.startswith("Search:")}


def run_table(args):
    """All rows of the run table, checked."""
    rows = list(csv.DictReader(open(args.runs, encoding="utf-8"), delimiter="\t"))
    ids = [r["id"] for r in rows]
    assert len(ids) == len(set(ids)), "run table: duplicate id"
    for r in rows:
        assert os.path.exists(os.path.join(PARAMS, r["params"] + ".ini")), f"{r['id']}: no parameter file {r['params']}"
        assert r["ions"] in IONS, f"{r['id']}: unknown ion series {r['ions']}"
    return rows


def runs(args):
    """The rows of the run table that --only selects (run ids or sample names)."""
    rows = run_table(args)
    if args.only:
        want = set(args.only.split(","))
        known = {r["id"] for r in rows} | {r["sample"] for r in rows if r["sample"] != "-"}
        assert want <= known, f"unknown run id or sample: {sorted(want - known)}"
        rows = [r for r in rows if r["id"] in want or r["sample"] in want]
    if getattr(args, "engine", None) == "sage":  # no z+1 ions in any Sage release
        for r in rows:
            if r["ions"] != "by":
                log(args, f"# sage: {r['id']} skipped (electron-based run)")
        rows = [r for r in rows if r["ions"] == "by"]
    if getattr(args, "engine", None) == "prose":
        # Sage and MSFragger search every spectrum at its recorded charge; ProSE does so only with this setting
        # (DATASETS.md, section 4.1). Parameter files written before the option existed do not hold it.
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


def scope(args):
    """The prefix of the memory cap: the same hard cap, without swap, for every engine (section 4.3)."""
    if not getattr(args, "mem_gb", None):
        return []
    return ["systemd-run", "--user", "--scope", "--quiet", "-p", f"MemoryMax={args.mem_gb}G", "-p", "MemorySwapMax=0",
            "--"]


def check_cap(args):
    """--mem-gb: one call under the cap before the stage. systemd-run fails without a user session bus (cron, sudo,
    many batch systems), which would turn every search into 'failed', and it accepts a property it cannot enforce (a
    controller not delegated to the user). So the cap is read back from the cgroup of that call: memory.max must be
    N GB and memory.swap.max 0."""
    sh = 'c=/sys/fs/cgroup$(cut -d: -f3 /proc/self/cgroup); cat "$c/memory.max" "$c/memory.swap.max"'
    try:
        r = subprocess.run(scope(args) + ["sh", "-c", sh], capture_output=True, text=True, timeout=120)
        ok, got = r.returncode == 0 and r.stdout.split() == [str(args.mem_gb * 2 ** 30), "0"], r.stdout + r.stderr
    except (OSError, subprocess.TimeoutExpired) as err:
        ok, got = False, str(err)
    if not ok:
        sys.exit(f"--mem-gb {args.mem_gb}: the memory cap does not work here ({' '.join(got.split())!r}, expected "
                 f"memory.max {args.mem_gb * 2 ** 30} and memory.swap.max 0). It needs systemd-run --user, i.e. a user "
                 "session bus (XDG_RUNTIME_DIR, DBUS_SESSION_BUS_ADDRESS), and cgroup v2 with the memory controller "
                 "delegated to the user (DATASETS.md section 4.3)")


def call(args, cmd, env=None, timing=None, pin=None, limit=None, output=None, started=None):
    """Runs cmd. timing = dict of labels: runs under /usr/bin/time -v and appends a line to timings.tsv.
    limit = seconds: the command and everything it started is killed after that time (exit 'over_limit').
    output = file that receives stdout and stderr. started(process group id) is called once the command runs."""
    if pin:
        cmd = ["taskset", "-c", pin] + cmd
    cmd = scope(args) + cmd
    # one time file per invocation, next to its log: drivers that share the work directory never touch each other's
    tfile = (output or os.path.join(args.work, f"call{os.getpid()}")) + ".time"
    if timing is not None:
        cmd = ["/usr/bin/time", "-v", "-o", tfile] + cmd
    show = " ".join(f"{k}={v}" for k, v in (env or {}).items())
    log(args, (show + " " if show else "") + " ".join(shlex.quote(c) for c in cmd) + (f" > {shlex.quote(output)} 2>&1" if output else ""))
    if args.dry_run:
        return 0
    e = dict(os.environ, **(env or {}))
    e.pop("OPENMS_BRUKER_SDK_PATH", None)  # section 4.0: never the Bruker SDK
    e["OPENMS_DISABLE_UPDATE_CHECK"] = "ON"  # no network call of the OpenMS tools inside a timed run
    if timing is not None and os.path.exists(tfile):
        os.remove(tfile)
    out = open(output, "wb") if output else None
    proc = None
    try:
        # a stop signal that comes while Popen starts the command waits until its process group is known (stop):
        # raised inside Popen, it would leave the started engine running without the driver
        STARTING[0] = True
        try:
            # a session of its own, so that a run over the limit is killed with all its child processes
            proc = subprocess.Popen(cmd, env=e, stdout=out, stderr=subprocess.STDOUT if out else None,
                                    start_new_session=True)
        finally:
            STARTING[0] = False
            if PENDING:
                signum = PENDING[0]
                PENDING.clear()
                stop(signum, None)
        if started:
            started(proc.pid)
        code = proc.wait(timeout=limit)
    except subprocess.TimeoutExpired:
        killpg(proc)
        code = "over_limit"
    except BaseException:
        # interrupted (Ctrl-C, SIGTERM, SIGHUP, an error of the driver): in its own session the engine would go on
        # without the driver and write into a folder whose search is recorded as unfinished
        if proc is not None:
            killpg(proc)
        raise
    finally:
        if out:
            out.close()
    if timing is not None:
        t = {}
        if os.path.exists(tfile):
            for line in open(tfile):
                k, _, v = line.strip().rpartition(": ")
                t[k] = v
            os.remove(tfile)
        wall, cpu, rss, state = None, None, "NA", code
        if code == "over_limit":  # /usr/bin/time was killed with the command: no time file, the limit is the time
            wall, cpu = float(limit), float("nan")
        elif "Elapsed (wall clock) time (h:mm:ss or m:ss)" in t:
            wall = 0.0
            for part in t["Elapsed (wall clock) time (h:mm:ss or m:ss)"].split(":"):
                wall = wall * 60 + float(part)
            cpu = float(t.get("User time (seconds)", "nan")) + float(t.get("System time (seconds)", "nan"))
            rss = t.get("Maximum resident set size (kbytes)", "NA")
        elif code == 0:  # the command ran, but its time is lost: recorded and reported, never as 0 s
            state = "no_timing"
            text = (f"{timing['engine']} {timing['benchmark']} {timing['run']} {timing['database']} stage "
                    f"{timing['stage']} repetition {timing['repetition']}: no timing (no output of /usr/bin/time)")
            log(args, f"# NO TIMING: {text}")
            args.failed.append(text)
        record(args, timing, wall, cpu, rss, state)
    return code


def killpg(proc):
    """Kills the command's process group (the engine and everything it started) and waits for it."""
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except OSError:  # already gone
        pass
    proc.wait()


def record(args, timing, wall, cpu, rss, code):
    """One line of timings.tsv (NA: not measured). Repetition 0 is the discarded run that fills the page cache."""
    table = os.path.join(args.work, "timings.tsv")
    cols = ["engine", "benchmark", "run", "database", "stage", "threads", "repetition"]
    line = "\t".join([str(timing[c]) for c in cols] + ["NA" if x is None else f"{x:.2f}" for x in (wall, cpu)]
                     + [str(rss), str(code)]) + "\n"
    # drivers may share the table: under an exclusive lock the header goes only into an empty table, so it stays the
    # first line; each row is one appended write. A file system without locks: written as before, without the lock
    with open(table, "a", encoding="utf-8") as f:
        try:
            fcntl.flock(f, fcntl.LOCK_EX)
        except OSError:
            pass
        if os.fstat(f.fileno()).st_size == 0:
            line = "\t".join(cols + ["wall_s", "cpu_s", "max_rss_kb", "exit"]) + "\n" + line
        f.write(line)
        f.flush()


# ---------------------------------------------------------------- versions, databases, fetch, convert
def versions(args):
    tools = [[os.path.join(args.openms_bin, t), "--help"] for t in ("ProSE", "FileConverter", "EntrapmentEvaluator")]
    # Percolator 3.09 has no --version; the first line of its --help is "Percolator version 3.09.0, Build Date ..."
    tools += [[args.sage, "--version"], ["java", "-jar", args.msfragger_jar, "--version"], [args.percolator, "--help"]]
    lines = []
    for cmd in tools:
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, errors="replace", timeout=120)
            out = [x.strip() for x in (r.stdout + r.stderr).splitlines()]
            # lines that name a version; else lines with a version-like number (Sage: "sage 0.14.6")
            found = [x for x in out if re.search(r"version", x, re.I)] or [x for x in out if re.search(r"\d+\.\d+", x)]
            lines.append(" ".join(cmd) + "\t" + (" | ".join(found[:3]) or "no version line"))
        except (OSError, subprocess.TimeoutExpired) as err:
            lines.append(" ".join(cmd) + f"\tNOT FOUND ({err.__class__.__name__})")
    print("\n".join(lines))
    if not args.dry_run:
        open(os.path.join(args.work, "versions.txt"), "w", encoding="utf-8").write("\n".join(lines) + "\n")


def dbs(args):
    """Every database of the run table -> W/db: a .fasta next to the run table, or datasets/databases/<name>.gz.
    The SHA256 of the uncompressed file is checked against the lists in datasets/ (a .fasta next to the run table: against
    that file). A copy in W/db with another SHA256, e.g. from before the rebuild of 2026-11-11, is replaced. Every
    database must have accessions that all engines read alike (check_fasta)."""
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
        want = sums.get(name) or (sha256(local) if os.path.exists(local) else None)
        if os.path.exists(dest) and want and sha256(dest) != want:
            log(args, f"database {name}: the copy in {d} has another SHA256, replaced")
            os.remove(dest)
        if not os.path.exists(dest):
            with (open(local, "rb") if os.path.exists(local) else gzip.open(packed)) as a, open(dest + ".part", "wb") as b:
                shutil.copyfileobj(a, b)
            os.replace(dest + ".part", dest)
        if want and sha256(dest) != want:
            sys.exit(f"{name}: SHA256 differs from the list in datasets/")
        check_fasta(dest)
    if missing:
        sys.exit("databases not in the repository: " + ", ".join(missing))


def check_fasta(path):
    """Every engine reports the first word of a header as the accession, but they cut it differently: OpenMS (ProSE,
    EntrapmentEvaluator) at a space or tab, Sage at ASCII white space, read_fasta at any white space; and the count
    splits the protein lists of Sage and MSFragger at ';' (sage_psms, percolator_psms). So the first word (up to the
    first space or tab) must be non-empty and unique, and hold no ';' and no other white space (also none before it):
    otherwise the engines could report different accessions for one protein, and the count would classify them
    wrongly. Run in the databases stage, before any search."""
    seen, bad = set(), []
    with open(path, encoding="utf-8", errors="replace", newline="") as f:  # newline="": a '\r' stays visible
        for n, line in enumerate(f, 1):
            if not line.startswith(">"):
                continue
            head = line.rstrip("\n")
            word = re.split("[ \t]", head[1:], maxsplit=1)[0]
            why = ("empty" if not word else "';' in it" if ";" in word
                   else "white space other than space or tab" if any(ch.isspace() for ch in word)
                   else "repeated" if word in seen else None)
            if why:
                bad.append(f"line {n}, first word {why}: {head[:80]!r}")
            seen.add(word)
    if bad:
        sys.exit(f"{path}: {len(bad)} header(s) without a usable accession: " + "; ".join(bad[:5]))


def vendor_sums(args):
    """SHA256 of the vendor files: vendor.sha256 next to the run table (sha256sum format, file names only)."""
    path, sums = os.path.join(os.path.dirname(args.runs), "vendor.sha256"), {}
    if os.path.exists(path):
        for line in open(path):
            if line.strip():
                h, n = line.split(maxsplit=1)
                sums[n.strip().lstrip("*")] = h
    return sums


def fetch(args):
    """Downloads the vendor files of the run table to W/vendor. Every file, also one that is already there, is checked
    against vendor.sha256 next to the run table: a right size alone does not prove a good download (DATASETS.md,
    section 4.5). A download with another SHA256 is kept as <file>.bad, and the stage fails at the end."""
    d, sums, bad, unlisted = os.path.join(args.work, "vendor"), vendor_sums(args), [], []
    for url in dict.fromkeys(r["url"] for r in runs(args)):  # a file shared by several runs is fetched once
        name = os.path.basename(url)
        dest = os.path.join(d, name)
        if name not in sums:
            unlisted.append(name)
        if not os.path.exists(dest):
            log(args, f"fetch {url}")
            if args.dry_run:
                continue
            os.makedirs(d, exist_ok=True)
            urllib.request.urlretrieve(url, dest + ".part")
            if name in sums and sha256(dest + ".part") != sums[name]:
                os.replace(dest + ".part", dest + ".bad")
                bad.append(f"{name} (the download is kept as {name}.bad)")
                continue
            os.replace(dest + ".part", dest)
        elif name in sums and not args.dry_run:
            print(f"check {name}", flush=True)
            if sha256(dest) != sums[name]:
                bad.append(f"{name} (already in {d}: delete it and run fetch again)")
    if unlisted:
        print("not in vendor.sha256, so not checked: " + ", ".join(unlisted), file=sys.stderr)
    if bad:
        sys.exit("SHA256 differs from vendor.sha256: " + "; ".join(bad))


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
        elif r["format"] in ("d.zip", "d.tar.gz"):
            # MS2 only: the MS1 frames as recorded are 81-96% of the mzML, and no search uses them (DATASETS.md, 4.0)
            extra = ["-bruker:load_ms1", "false"]
            if r["format"] == "d.tar.gz":  # unpack to <id>.d first; a .d.zip is read directly
                unpacked = os.path.join(v, r["id"] + ".d")
                if not args.dry_run and not os.path.exists(unpacked):
                    with tarfile.open(src) as t:
                        t.extractall(os.path.join(v, r["id"] + ".unpack"))
                    found = [os.path.join(p, x) for p, ds, _ in os.walk(os.path.join(v, r["id"] + ".unpack"))
                             for x in ds if x.endswith(".d")]
                    assert len(found) == 1, f"{r['id']}: expected one .d folder, found {found}"
                    os.replace(found[0], unpacked)
                src = unpacked
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


def isotope_errors(c):
    """The searched isotope errors in the convention of Sage and MSFragger, observed minus theoretical mass in 13C
    spacings. ProSE's precursor:isotope_error_min/max are added to the observed mass (-1 finds a peptide whose first
    13C peak was selected, i.e. observed - theoretical = +1), so the range is negated: ProSE -2..1 is -1..+2 there."""
    return -int(c["precursor:isotope_error_max"]), -int(c["precursor:isotope_error_min"])


def neutral_mass_range(c):
    """ProSE's peptide:min_mass and max_mass bound the singly protonated mass [M+H]+ of each peptidoform, with its fixed
    and variable modifications (its fragment index adds water and a proton to the residues); Sage bounds the neutral
    mass of each modified peptide (its peptide mass starts at H2O). The bounds less one proton. MSFragger bounds the
    residue sum of the unmodified sequence, without water and without fixed or variable modifications
    (msfragger_params)."""
    return round(float(c["peptide:min_mass"]) - PROTON, 6), round(float(c["peptide:max_mass"]) - PROTON, 6)


def prose_max_fragment_charge(c):
    """ProSE's fragment:max_charge where ProSE scores several fragment charges, else None. scoring:fragment_charges
    'auto' scores several charges (1 .. max(1, min(z - 1, fragment:max_charge))) when the MS2 spectra are not
    deisotoped: fragment:deisotope false, or 'auto' with a fragment tolerance above the deisotoper's limit (0.1 Da /
    100 ppm), as for ion-trap CID. Deisotoped spectra are scored with charge 1 only."""
    mode = c.get("scoring:fragment_charges", "auto")
    tol, unit = float(c["fragment:mass_tolerance"]), c["fragment:mass_tolerance_unit"]
    deiso = c.get("fragment:deisotope", "auto")
    deisotoped = deiso == "true" or (deiso == "auto" and tol <= (0.1 if unit == "Da" else 100.0))
    if mode == "multiple" or (mode == "auto" and not deisotoped):
        return int(c["fragment:max_charge"])
    return None


def sage_config(c, ions, db):
    """Sage v0.14.7. An empty cleave_at is the non-specific digestion.
    precursor_tol [a, b]: Sage searches theoretical masses from observed + a to observed + b, so ProSE's window
    (theoretical within observed - lower ... observed + upper) is [-lower, upper]."""
    cut, nocut, _ = ENZYME[c["enzyme"]]
    da = c["precursor:mass_tolerance_unit"] == "Da"
    lo, hi = float(c["precursor:mass_tolerance_lower"]), float(c["precursor:mass_tolerance_upper"])
    ft = float(c["fragment:mass_tolerance"])
    min_mass, max_mass = neutral_mass_range(c)
    database = {
        "enzyme": {"missed_cleavages": int(c["peptide:missed_cleavages"]), "min_len": int(c["peptide:min_size"]),
                   "max_len": int(c["peptide:max_size"]), "cleave_at": "" if cut is None else cut,
                   "restrict": nocut or None, "c_terminal": True},
        "static_mods": mod_masses(c["modifications:fixed"]),
        "variable_mods": {k: [v] for k, v in mod_masses(c["modifications:variable"]).items()},
        "max_variable_mods": int(c["modifications:variable_max_per_peptide"]),
        "peptide_min_mass": min_mass, "peptide_max_mass": max_mass,
        "ion_kinds": IONS[ions], "decoy_tag": c["decoy_prefix"], "generate_decoys": False, "fasta": db,
    }
    config = {
        "database": database,
        "precursor_tol": {"da" if da else "ppm": [-lo, hi]},
        "fragment_tol": {"da" if c["fragment:mass_tolerance_unit"] == "Da" else "ppm": [-ft, ft]},
        # the charges tried for a spectrum without a recorded charge; other spectra are searched at their charge
        "precursor_charge": [int(c["precursor:min_charge"]), int(c["precursor:max_charge"])],
        "isotope_errors": list(isotope_errors(c)),
        # Sage's own default is 4 as well; set from the parameter file so all engines use the same value
        "min_matched_peaks": int(c["fragment:min_matched_ions"]),
    }
    # Sage scores fragment charges 1 .. z - 1 without a cap by default. Where ProSE scores several fragment charges
    # (0.5 Da ion-trap MS2: CID, and the HCD run of PXD011695), Sage gets the same cap, so that both score the same
    # fragment charges, 1 .. max(1, min(z - 1, fragment:max_charge)) (decided 2026-11-13, DATASETS.md 4.4); elsewhere
    # both stay at their defaults. ProSE's candidate retrieval (fragment index) uses 1 .. min(z, fragment:max_charge)
    # on every file, so at z = 2 it also matches charge-2 fragments; in both engines one setting sets both ranges, so
    # this difference cannot be aligned without changing the scored charges
    cap = prose_max_fragment_charge(c)
    if cap is not None:
        config["max_fragment_charge"] = cap
    return config


def msfragger_params(c, ions, db, threads):
    """The settings written over MSFragger's own closed-search defaults (`--config closed`).
    precursor_mass_lower/upper bound observed - theoretical mass, the mirror of ProSE's window (theoretical within
    observed - lower ... observed + upper): lower = -upper, upper = lower. All parameter files are symmetric."""
    cut, nocut, name = ENZYME[c["enzyme"]]
    ppm = c["precursor:mass_tolerance_unit"] == "ppm"
    lo, hi = float(c["precursor:mass_tolerance_lower"]), float(c["precursor:mass_tolerance_upper"])
    fixed, var = mod_masses(c["modifications:fixed"]), mod_masses(c["modifications:variable"])
    maxmods = c["modifications:variable_max_per_peptide"]
    lo_iso, hi_iso = isotope_errors(c)
    iso = range(lo_iso, hi_iso + 1)
    # MSFragger 4.4.1 applies digest_mass_range to the residue sum of the unmodified sequence: no water, no fixed and
    # no variable modifications. So the neutral bounds less water (corrected 2026-11-13; before, it searched 18.01 Da
    # heavier peptides). This matches ProSE and Sage only for peptides without modifications, as they bound each
    # modified form: the tryptic bounds cut nothing, but at the immunopeptidomics bounds the oxidised forms within
    # k x 15.995 Da differ: MSFragger lacks them at the lower bound, and would search more at the upper one, where the
    # length limits leave no peptide (pilot: 4 accepted ProSE PSMs of one peptide in the lower band on pxd058436 class
    # I, 0 on pxd019643 class I, 0 MSFragger PSMs in the upper band; DATASETS.md 4.4). MSFragger has no setting that
    # bounds each modified form
    min_mass, max_mass = (round(m - WATER, 6) for m in neutral_mass_range(c))
    p = {
        "database_name": db, "num_threads": threads, "decoy_prefix": c["decoy_prefix"],
        "precursor_mass_lower": -hi, "precursor_mass_upper": lo, "precursor_mass_units": int(ppm),
        "precursor_true_tolerance": max(lo, hi), "precursor_true_units": int(ppm),
        "fragment_mass_tolerance": c["fragment:mass_tolerance"],
        "fragment_mass_units": int(c["fragment:mass_tolerance_unit"] == "ppm"),
        "isotope_error": "/".join(str(i) for i in iso),
        # MSFragger's own default is 4 as well; set from the parameter file so all engines use the same value
        "min_matched_fragments": c["fragment:min_matched_ions"],
        "search_enzyme_name_1": name, "search_enzyme_cut_1": "@" if cut is None else cut,
        "search_enzyme_nocut_1": nocut, "search_enzyme_sense_1": "C",
        "allowed_missed_cleavage_1": c["peptide:missed_cleavages"], "num_enzyme_termini": 0 if cut is None else 2,
        "digest_min_length": c["peptide:min_size"], "digest_max_length": c["peptide:max_size"],
        "digest_mass_range": f"{min_mass} {max_mass}",
        "clip_nTerm_M": int(c["peptide:clip_nterm_methionine"] == "true"),
        "max_variable_mods_per_peptide": maxmods,
        # the charges tried for a spectrum without a recorded charge; the recorded charge is not overridden
        "precursor_charge": f"{c['precursor:min_charge']} {c['precursor:max_charge']}", "override_charge": 0,
        "fragment_ion_series": ",".join(IONS[ions]),
        # used only by labile/glycan searches (labile_search_mode stays off), but MSFragger 4.4.1 rejects the blank value
        # its own --config closed writes ("labile ion type must be one of ..."); b,y as in FragPipe's closed workflows
        "labile_fragment_ion_series": "b,y",
        "add_C_cysteine": fixed.get("C", 0), "add_K_lysine": fixed.get("K", 0), "add_Nterm_peptide": fixed.get("^", 0),
        "output_format": "pin", "output_report_topN": 1,
        # --config closed writes the uncalibrated spectra (<run>_uncalibrated.mzBIN, up to 1 GB) inside the timed
        # search, and nothing reads them; the .pin is byte-identical without (velos_5000_R2, checked 2026-11-13)
        "write_uncalibrated_mzml": 0,
    }
    for i, (site, mass) in enumerate(sorted(var.items()), 1):
        p[f"variable_mod_{i:02d}"] = f"{mass} {site} {maxmods}"
    return p


def fragger_key(line):
    return line.split("=")[0].strip().lstrip("# ").strip() if "=" in line else ""


def extra_settings(args, engine):
    """The settings of an extra arm (search --extra). ProSE: further options of its command line. Sage: key=JSON
    pairs set in its configuration, database.<key> for the database part (e.g. deisotope=false,
    fragment_tol={"ppm":[-10,10]}); write_pin and annotate_matches take true or false and become Sage's flags
    (SAGE_FLAGS). MSFragger: key=value pairs written into fragger.params (e.g. calibrate_mass=0; a value with spaces
    in shell quotes, e.g. clear_mz_range='125.5 134.5'). The pairs are separated by white space."""
    text = getattr(args, "extra", None) or ""
    if engine == "prose":
        return shlex.split(text)
    pairs = {}
    # Sage's JSON values keep their double quotes (plain split); MSFragger's values may hold spaces (shell quoting)
    for x in (shlex.split(text) if engine == "msfragger" else text.split()):
        k, sep, v = x.partition("=")
        if not (sep and k and v):
            sys.exit(f"--extra for {engine}: key=value expected, got {x!r}")
        if engine == "sage" and not (k in SAGE_KEYS or k in SAGE_FLAGS
                                     or k.startswith("database.") and k[len("database."):] in SAGE_DB_KEYS):
            sys.exit(f"--extra for sage: {k} is no key of the Sage 0.14.7 configuration (Sage would ignore it)")
        if engine == "sage" and k in SAGE_FLAGS and v not in ("true", "false"):
            sys.exit(f"--extra for sage: {k}={v}: true or false expected (Sage's flag {SAGE_FLAGS[k]})")
        pairs[k] = v
    if engine == "msfragger" and pairs:
        known = fragger_keys(args)
        if known is None:
            print("# WARNING: --extra for msfragger: the keys were not checked (no MSFragger to write its defaults)",
                  file=sys.stderr)
        elif sorted(set(pairs) - known):
            sys.exit(f"--extra for msfragger: {', '.join(sorted(set(pairs) - known))} not in MSFragger's closed-search "
                     "parameter file (--config closed)")
    return pairs


def fragger_defaults(args):
    """MSFragger's own closed-search parameter file, W/closed_fragger.params (written by `--config closed`): the
    defaults that msfragger_params overrides."""
    path = os.path.join(args.work, "closed_fragger.params")
    if not os.path.exists(path):
        subprocess.run(["java", "-jar", args.msfragger_jar, "--config", "closed"], cwd=args.work, check=True)
    return path


def fragger_keys(args):
    """The keys of MSFragger's closed-search parameter file, which --extra may set. A dry run that finds no file in the
    work directory writes one to a temporary folder (None if that fails)."""
    if not hasattr(args, "fragger_keys"):
        path = os.path.join(args.work, "closed_fragger.params")
        if os.path.exists(path) or not args.dry_run:
            lines = open(fragger_defaults(args), encoding="utf-8", errors="replace").readlines()
        else:
            with tempfile.TemporaryDirectory() as d:
                try:
                    subprocess.run(["java", "-jar", args.msfragger_jar, "--config", "closed"], cwd=d, check=True,
                                   capture_output=True)
                    with open(os.path.join(d, "closed_fragger.params"), encoding="utf-8", errors="replace") as f:
                        lines = f.readlines()
                except (OSError, subprocess.CalledProcessError):
                    lines = None
        args.fragger_keys = None if lines is None else {fragger_key(line) for line in lines}
    return args.fragger_keys


def set_sage(cfg, pairs):
    """The --extra pairs into a Sage configuration; a value that is no JSON is taken as a string."""
    for k, v in pairs.items():
        try:
            v = json.loads(v)
        except ValueError:
            pass
        if k.startswith("database."):
            cfg["database"][k[len("database."):]] = v
        else:
            cfg[k] = v
    return cfg


def write_fragger(defaults, path, params):
    """Default lines kept, our keys replaced, every default variable modification beyond ours removed."""
    lines, seen = [], set()
    for line in open(defaults, encoding="utf-8", errors="replace"):
        key = fragger_key(line)
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
    extra = extra_settings(args, engine)
    if extra and engine != "prose":  # not on the command line, so recorded here
        log(args, f"# {engine} {r['id']} {db}: extra settings {' '.join(f'{k}={v}' for k, v in extra.items())}")
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
            keys = {k: v for k, v in extra.items() if k not in SAGE_FLAGS}  # the flags go on the command line
            config = set_sage(sage_config(c, r["ions"], dbpath), keys)
            json.dump(config, open(cfg, "w"), indent=1)
        # no telemetry: Sage would send it synchronously before it exits, inside the timed run. On one thread the
        # default batch size (number of CPUs / 2) is 0, which Sage rejects; one file at a time gives the same results
        cmd = [args.sage, cfg, "-o", out, "--disable-telemetry-i-dont-want-to-improve-sage"]
        cmd += [flag for k, flag in SAGE_FLAGS.items() if extra.get(k) == "true"]
        if threads == 1:
            cmd += ["--batch-size", "1"]
        return [("all", cmd + files, {"RAYON_NUM_THREADS": str(threads)})]
    if engine == "msfragger":
        par = os.path.join(out, "fragger.params")
        local = [os.path.join(out, os.path.basename(f)) for f in files]
        if not args.dry_run:  # the --extra keys were checked by search() (extra_settings)
            write_fragger(fragger_defaults(args), par, {**msfragger_params(c, r["ions"], dbpath, threads), **extra})
            for f, link in zip(files, local):  # MSFragger writes its .pin next to the input
                # a link into another work directory (this one moved or copied) would be dangling or read old spectra
                if os.path.islink(link) and os.path.realpath(link) != os.path.realpath(f):
                    os.remove(link)
                if not os.path.exists(link):
                    os.symlink(os.path.abspath(f), link)
        # -XX:+ExitOnOutOfMemoryError: a full Java heap ends the run at once (exit 3, 'Terminating due to
        # java.lang.OutOfMemoryError'), which out_of_memory records under --mem-gb as failed_memory, like a kill at
        # the cap of the other engines (without --mem-gb every failure is 'failed'). MSFragger 4.4.1 has no recovery
        # from that error (its only handler exits 1)
        cmds = [("search", ["java", "-XX:+ExitOnOutOfMemoryError", f"-Xmx{args.java_gb}g", "-jar", args.msfragger_jar,
                            par, *local], {})]
        pins = [f[:-len(".mzML")] for f in local]
        if pooled:  # one Percolator run over the replicates: the .pin files are joined first
            cmds.append(("join", [sys.executable, os.path.abspath(__file__), "--work", args.work, "joinpins",
                                  pooled_pin(out) + ".pin", *[p + ".pin" for p in pins]], {}))
            pins = [pooled_pin(out)]
        # FragPipe's Percolator options, without --only-psms: Percolator's own peptide tables are kept for comparison;
        # the count computes both levels from the scores of the PSM tables (q_values)
        for p in pins:
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


def set_status(args, out, text):
    """The outcome of a search, kept in its folder for count and collect (other processes)."""
    if not args.dry_run:
        with open(os.path.join(out, "status"), "w", encoding="utf-8") as f:
            f.write(text + "\n")


def drop_pepindex(args, db):
    """MSFragger writes its digested peptides next to the database (<fasta>.<n>.pepindex) and reads them in every later
    search with the same digestion settings, so it would skip the digestion that ProSE and Sage do in every run. The
    files are removed before each MSFragger search, outside the timed command (DATASETS.md section 4.3)."""
    for f in sorted(glob.glob(os.path.join(args.work, "db", glob.escape(db) + ".*.pepindex"))):
        log(args, f"rm {shlex.quote(f)}")
        if not args.dry_run:
            os.remove(f)


def still_running(out):
    """What may still run the search of this folder: the driver named in a 'running' status (a live process of this
    script) or the engine's process group. An engine is left behind when its driver was killed with SIGKILL, which
    the driver cannot catch."""
    try:
        text = open(os.path.join(out, "status"), encoding="utf-8").read()
    except OSError:
        return None
    if not text.startswith("running"):
        return None
    driver, group = re.search(r"\bdriver (\d+)", text), re.search(r"\bpgid (\d+)", text)
    if driver and int(driver[1]) != os.getpid():
        try:
            if os.path.basename(__file__).encode() in open(f"/proc/{driver[1]}/cmdline", "rb").read():
                return f"driver process {driver[1]}"
        except OSError:
            pass
    if group:
        try:
            os.killpg(int(group[1]), 0)
            return f"engine process group {group[1]}"
        except OSError:
            pass
    return None


def out_of_memory(args, code, log_path):
    """A failed step that ran out of memory under --mem-gb: killed at the cap (SIGKILL: -9 from Popen, 137 through
    /usr/bin/time or systemd-run), or stopped by its engine's own out-of-memory error (OOM, read from the end of the
    step's log). Without --mem-gb every failure is 'failed': a kill by the kernel's out-of-memory killer (ProSE, Sage)
    cannot be told from other kills, so no engine's memory failure is labelled differently from another's."""
    if not getattr(args, "mem_gb", None):
        return False
    if code in (-9, 137):
        return True
    try:
        with open(log_path, "rb") as f:
            f.seek(0, 2)
            f.seek(max(0, f.tell() - (1 << 20)))
            return bool(OOM.search(f.read().decode("utf-8", "replace")))
    except OSError:
        return False


def measure(args, engine, bench, name, r, files, db, threads, timed, pin=None, limit=None, pooled=False, warm=True):
    bench = bench_name(args, bench)
    out = outdir(args, engine, bench, name, db, threads if bench.startswith("scaling") else None)
    if not args.dry_run:
        busy = still_running(out)
        if busy:
            sys.exit(f"{out}: a search may still run there ({busy}); let it finish or stop it, then run again")
        # a rerun starts from an empty folder: no result, count or status of an earlier run may be read as its own
        if os.path.isdir(out):
            for x in os.listdir(out):
                p = os.path.join(out, x)
                if os.path.isdir(p) and not os.path.islink(p):
                    shutil.rmtree(p)
                else:
                    os.remove(p)
        os.makedirs(out, exist_ok=True)
        set_status(args, out, f"running driver {os.getpid()}")  # count refuses the folder until the search ends ok
        with open(os.path.join(out, "inputs"), "w", encoding="utf-8") as f:  # count checks them against the table
            f.write("".join(stem(x) + "\n" for x in files))
    stage = rep = None
    try:
        # repetition 0 fills the page cache; it is recorded as repetition 0 and not used
        for rep in (([0] if warm else []) + [1, 2, 3] if timed else [1]):
            for stage, cmd, env in invocations(args, engine, r, files, db, out, threads, pooled):
                timing = None
                if timed:
                    timing = dict(engine=engine, benchmark=bench, run=name, database=db, stage=stage, threads=threads,
                                  repetition=rep)
                if engine == "msfragger" and stage == "search":
                    drop_pepindex(args, db)
                # the engine's own output is kept next to its results (e.g. the tolerances its calibration chose)
                output = os.path.join(out, f"{stage}.r{rep}.log" if timed else f"{stage}.log")
                code = call(args, cmd, env, timing, pin, limit, output=output, started=lambda pgid: set_status(
                    args, out, f"running stage {stage} repetition {rep} driver {os.getpid()} pgid {pgid}"))
                if code == "over_limit":
                    set_status(args, out, f"over_limit stage {stage} repetition {rep}")
                    return True  # recorded as over the limit; no further repetitions
                if code != 0:  # a failed engine: no later step on its missing output, no further repetitions
                    kind = "failed_memory" if out_of_memory(args, code, output) else "failed"
                    text = f"{engine} {bench} {name} {db} stage {stage} repetition {rep}: exit {code}"
                    log(args, f"# FAILED: {text}{' (out of memory)' if kind == 'failed_memory' else ''}; the "
                              "remaining steps of this search are not run")
                    args.failed.append(text)
                    set_status(args, out, f"{kind} stage {stage} repetition {rep} exit {code}")
                    return False
    except BaseException as err:  # Ctrl-C, a signal, an error of the driver: call() has stopped the engine
        set_status(args, out, f"interrupted stage {stage} repetition {rep} ({err.__class__.__name__})")
        raise
    set_status(args, out, "ok")
    return False


def units(rows, key):
    """Rows grouped by a column, in table order; '-' means no group."""
    out = {}
    for r in rows:
        if r[key] != "-":
            out.setdefault(r[key], []).append(r)
    return out


def searches(args):
    """(name, first row, rows): one per run; immunopeptidomics: one per sample over its technical replicates.
    A sample is searched and counted as a whole: --only with a part of it is refused (else its pooled folder would get
    the search or count of some replicates)."""
    rows = runs(args)
    every = units(run_table(args), "sample")
    for n, rs in units(rows, "sample").items():
        missing = [x["id"] for x in every[n] if x not in rs]
        if missing:
            sys.exit(f"--only selects a part of the sample {n}; missing: {', '.join(missing)}. Give the sample name or "
                     "all its replicates")
    return [(n, rs[0], rs) for n, rs in units(rows, "sample").items()] + [(r["id"], r, [r]) for r in rows if r["sample"] == "-"]


# ---------------------------------------------------------------- the benchmarks
def search(args):
    extra_settings(args, args.engine)  # a wrong --extra key stops the stage before any search folder is touched
    plan = searches(args)
    for name, r, rs in plan:
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
            # whole cores: logical CPUs 0..n-1 must be n different physical cores (check with lscpu -e). Every engine
            # runs n threads on n cores; Sage's one-thread point gets --batch-size 1 (invocations), as it would
            # abort on one core with its default batch size (number of CPUs / 2 = 0)
            db, limit = databases(r, "td")[0], args.limit_hours * 3600
            if measure(args, args.engine, "scaling", r["id"], r, [mzml(args, r)], db, n, True,
                       pin=f"0-{n - 1}", limit=limit, warm=(i == 0)):
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


def il_key(peptide):
    """The peptide of the count: the unmodified sequence with I = L (DATASETS.md section 4.2)."""
    return bare(peptide).replace("I", "L")


def write_idxml(path, engine, psms):
    """psms: (spectrum, unmodified sequence, [accessions], PSM q-value, peptide q-value), target top hits only.
    A minimal idXML for EntrapmentEvaluator: q-value as main score, 'peptide q-value' as meta value."""
    acc = {}
    for _, _, proteins, _, _ in psms:
        for a in proteins:
            # one accession per protein: a joined list would be classified by its first protein only
            assert a and not re.search(r"[;\s]", a), f"{path}: protein accession {a!r} is not one accession"
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


def tdc_q(items):
    """items: (key, score, decoy), higher score = better -> {key: q} for the target keys. Sorted by score,
    q = (D + 1) / T (at most 1) at each score, where equal scores enter together, then the minimum over all lower
    scores."""
    ranked = sorted(items, key=lambda x: -x[1])
    groups, t, d, i = [], 0, 0, 0
    while i < len(ranked):
        j = i
        while j < len(ranked) and ranked[j][1] == ranked[i][1]:
            d += ranked[j][2]
            t += not ranked[j][2]
            j += 1
        groups.append((ranked[i:j], min(1.0, (d + 1) / t) if t else 1.0))
        i = j
    q, low = {}, 1.0
    for group, fdr in reversed(groups):
        low = min(low, fdr)
        for k, _, decoy in group:
            if not decoy:
                q[k] = low
    return q


def q_values(psms):
    """The PSM- and peptide-level q-values of section 4.2, computed the same way for every engine.
    psms: (spectrum, sequence, [accessions], final score, decoy) for the top hit of each spectrum, targets and decoys;
    the final score is the engine's own score after its rescoring, higher = better.
    PSM level: every PSM competes with its score (tdc_q).
    Peptide level: a peptide is an unmodified sequence with I = L; each peptide competes with its best PSM by that
    score, separately per label (tdc_q).
    Returns the target PSMs as write_idxml takes them, each with its PSM q-value and the q-value of its peptide."""
    psm_q = tdc_q([(i, score, decoy) for i, (_, _, _, score, decoy) in enumerate(psms)])
    best = {}
    for _, seq, _, score, decoy in psms:
        k = (il_key(seq), decoy)
        best[k] = max(best.get(k, score), score)
    pep_q = tdc_q([(k, score, k[1]) for k, score in best.items()])
    return [(s, bare(seq), proteins, repr(psm_q[i]), repr(pep_q[(il_key(seq), False)]))
            for i, (s, seq, proteins, _, decoy) in enumerate(psms) if not decoy]


def prose_psms(path, pooled):
    """A ProSE idXML (one input, or -out_merged) -> psms: the top hit of each spectrum, targets and decoys, with its
    final score. For one input that is the Percolator score of the rescoring (meta value 'percolator_score'). In
    -out_merged each input keeps its own Percolator model, so the scores of the inputs are not on one scale; there the
    PSMs are ranked by Percolator's PEP ('percolator_pep'; final score = -PEP), which is on one scale for all inputs
    (DATASETS.md section 4.2).
    A hit of a target and a decoy protein ('target+decoy') is read as a target, as in OpenMS; count() then decides its
    label with the search space of all engines (relabel)."""
    acc, psms = {}, []
    for _, e in ET.iterparse(path):
        if e.tag == "ProteinHit":
            acc[e.get("id")] = e.get("accession")
            e.clear()
        elif e.tag == "PeptideIdentification":
            meta = {u.get("name"): u.get("value") for u in e.findall("UserParam")}
            hits = [(h, {u.get("name"): u.get("value") for u in h.findall("UserParam")}) for h in e.findall("PeptideHit")]
            if hits:
                if any("percolator_score" not in m or "percolator_pep" not in m for _, m in hits):
                    raise ValueError(f"{path}: a PSM without percolator_score or percolator_pep (was every input "
                                     "rescored?)")
                h, m = max(hits, key=lambda x: float(x[1]["percolator_score"]))
                # in merged.idXML the spectra of the inputs are told apart by their input
                spectrum = e.get("spectrum_reference")
                if "id_merge_index" in meta:
                    spectrum = meta["id_merge_index"] + ":" + spectrum
                score = -float(m["percolator_pep"]) if pooled else float(m["percolator_score"])
                psms.append((spectrum, h.get("sequence"), [acc[p] for p in h.get("protein_refs", "").split()],
                             score, m["target_decoy"] == "decoy"))
            e.clear()
    return psms


def complete(path):
    """A table that does not end with a line end was cut while it was written (or copied)."""
    with open(path, "rb") as f:
        f.seek(0, 2)
        if f.tell() == 0:
            return False
        f.seek(-1, 2)
        return f.read(1) == b"\n"


def sage_psms(out):
    """results.sage.tsv -> {file stem: psms}: the top hit of each spectrum, targets and decoys, with Sage's final score
    (sage_discriminant_score, of its LDA rescoring). The proteins of a PSM are split at ';', as Sage joins them; a
    ';' inside an accession is refused by check_fasta. A cut table is refused (ValueError)."""
    path, res = os.path.join(out, "results.sage.tsv"), {}
    with open(path, encoding="utf-8") as f:
        for n, row in enumerate(csv.DictReader(f, delimiter="\t"), 2):
            if None in row or None in row.values():
                raise ValueError(f"{path}: line {n} has another number of fields than the header (a cut file?)")
            if row["rank"] != "1":
                continue
            res.setdefault(stem(row["filename"]), []).append(
                (row["scannr"], row["peptide"], row["proteins"].split(";"), float(row["sage_discriminant_score"]),
                 row["label"] != "1"))
    if res and not complete(path):
        raise ValueError(f"{path}: no line end at the end (a cut file?)")
    return res


def percolator_psms(prefix):
    """Percolator's PSM tables of targets and decoys -> psms, with Percolator's score. The proteins are the tail of
    each line: MSFragger 4.4.1 writes all proteins of a PSM into one ';'-separated field with a trailing ';', which
    Percolator copies (proteinIds); further tab-separated fields are read the same way (fixed 2026-11-13: before, the
    joined field was one accession, so EntrapmentEvaluator classified the PSM by its first protein). A ';' inside an
    accession is refused by check_fasta. An empty or cut table is refused (ValueError)."""
    def table(path):
        with open(path, encoding="utf-8") as f:
            head = f.readline().rstrip("\n").split("\t")
            if head[0] != "PSMId" or not {"score", "peptide"} <= set(head):
                raise ValueError(f"{path}: no Percolator header (an empty or cut file?)")
            for n, line in enumerate(f, 2):
                x = line.rstrip("\n").split("\t")
                if len(x) < len(head) or not line.endswith("\n"):
                    raise ValueError(f"{path}: line {n} is cut")
                yield dict(zip(head[:-1], x)), [a for field in x[len(head) - 1:] for a in field.split(";") if a]
    return [(row["PSMId"], row["peptide"], proteins, float(row["score"]), decoy)
            for decoy, path in ((False, prefix + ".psms.tsv"), (True, prefix + ".decoy_psms.tsv"))
            for row, proteins in table(path)]


def read_fasta(path):
    """(accession, sequence) of each entry; the accession is the first word of the header, as every engine reports it."""
    acc, seq = None, []
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            if line.startswith(">"):
                if acc is not None:
                    yield acc, "".join(seq)
                words = line[1:].split()
                acc, seq = (words[0] if words else ""), []
            else:
                seq.append(line.strip())
    if acc is not None:
        yield acc, "".join(seq)


def il_twins(keys, c, dbpath):
    """Which of the keys (unmodified sequences with I = L, il_key) are target peptides of the search space: {key:
    [target accessions]}; and the accessions (first words) of all entries of the database. The search space is the
    parameter file's digestion of the target proteins of the database: the enzyme (cleavage sites after K and R;
    unspecific: every position) and the protein N-terminal Met clipping. Length, mass and missed cleavages need no
    check: a key has the length and mass of its PSM, and its cleavage sites inside the peptide.
    For a decoy PSM such a key is an I = L twin of a target peptide. MSFragger maps a peptide to its I = L target
    proteins in its search space and so labels such a PSM a target; ProSE (its protein mapping is exact in I and L, but
    goes beyond the search space in other ways, see relabel) and Sage (exact duplicates only) label it a decoy. The
    count applies MSFragger's rule to every engine, matching the peptide definition (unmodified, I = L; decided
    2026-11-13, DATASETS.md 4.2). The space is the same for every engine, so for Sage it also holds the Met-clipped
    peptides, which Sage does not search (DATASETS.md 4.2)."""
    lengths = sorted({len(k) for k in keys})
    m = lengths[0] if keys else 0
    prefixes = {k[:m] for k in keys}
    cut, nocut, _ = ENZYME[c["enzyme"]]
    clip = c.get("peptide:clip_nterm_methionine") == "true"
    prefix = c["decoy_prefix"]
    found, accessions = {}, set()
    for acc, seq in read_fasta(dbpath):
        accessions.add(acc)
        if not keys or acc.startswith(prefix):
            continue
        s = seq.replace("I", "L")
        if cut is None:
            starts, ends = range(len(s)), None
        else:
            sites = [i + 1 for i, a in enumerate(s[:-1]) if a in cut and not (nocut and s[i + 1] in nocut)]
            starts = {0, *sites} | ({1} if clip and s.startswith("M") else set())
            ends = set(sites) | {len(s)}
        for st in starts:
            if s[st:st + m] not in prefixes:
                continue
            for n in lengths:
                e = st + n
                if e > len(s):
                    break
                if (ends is None or e in ends) and s[st:e] in keys:
                    hits = found.setdefault(s[st:e], [])
                    if acc not in hits:
                        hits.append(acc)
    return found, accessions


def relabel(psms, c, dbpath):
    """The target and decoy labels of the count, from one search space for every engine (il_twins; DATASETS.md 4.2):
    - A decoy PSM whose key is a target peptide of the space becomes a target, with the target proteins of that peptide
      (an I = L twin).
    - A target PSM that also maps to a decoy protein stays a target only if its key is a target peptide of the space,
      and then gets the target proteins of that peptide in the space, so that EntrapmentEvaluator classifies it by them;
      otherwise it becomes a decoy. Such PSMs come from ProSE ('target+decoy'), whose protein mapping goes beyond the
      space: OpenMS Trypsin/P also cleaves after X, a peptide may start right after the initial M of a protein or one
      residue later (OpenMS's 'M or MX' rule; the digestion clips only the M), and B, J, Z and X in a protein match any
      residue. Sage lists no decoy protein for a target; MSFragger's such PSMs lie inside the space.
    - Other target PSMs stay as they are: ProSE's targets after an X lie outside the space, as do its decoys there.
    Every accession must be a first word of the database: a protein list split wrongly (e.g. at a ';' inside an
    accession; sage_psms and percolator_psms split at ';') would be classified by its prefix only (ValueError).
    Returns the PSMs and lines for the log."""
    prefix = c["decoy_prefix"]

    def mixed(p):
        return not p[4] and any(a.startswith(prefix) for a in p[2])
    space, accessions = il_twins({il_key(p[1]) for p in psms if p[4] or mixed(p)}, c, dbpath)
    unknown = sorted({a for p in psms for a in p[2]} - accessions)
    if unknown:
        raise ValueError(f"{len(unknown)} protein accession(s) not in {os.path.basename(dbpath)}, e.g. "
                         f"{', '.join(map(repr, unknown[:3]))} (a protein list split wrongly?)")
    new, twins, kept, flipped = [], set(), [], []
    for p in psms:
        s, seq, proteins, score, decoy = p
        k = il_key(seq)
        if decoy and k in space:
            twins.add(k)
            p = (s, seq, space[k], score, False)
        elif mixed(p):
            (kept if k in space else flipped).append(k)
            p = (s, seq, space[k], score, False) if k in space else (s, seq, proteins, score, True)
        new.append(p)
    notes = []
    if twins:
        notes.append(f"{sum(1 for p in psms if p[4] and il_key(p[1]) in twins)} decoy PSMs are I = L twins of a target "
                     f"peptide, counted as targets ({len(twins)} peptides)")
    if kept or flipped:
        notes.append(f"{len(kept) + len(flipped)} target PSMs also map to a decoy protein: {len(flipped)} outside the "
                     f"search space, counted as decoys ({len(set(flipped))} peptides); {len(kept)} inside, counted "
                     "with their target proteins of the space")
    return new, notes


def count(args):
    """Runs EntrapmentEvaluator on each result: with the plain target-decoy database the accepted PSMs and peptides are
    the identification counts, with an entrapment database the FDP follows. For every engine the driver first writes
    <run>.count.idXML (pooled runs: pooled.count.idXML): the target top hits with the PSM- and peptide-level q-values of
    q_values(), computed the same way for all engines from each engine's final score (DATASETS.md section 4.2).
    Before that, the labels come from one search space for every engine (relabel).
    Only a search whose status is ok, and whose inputs (if the folder records them) are the run table's, is counted.
    A search that failed, did not finish or has no usable result is skipped: its status reaches coverage.tsv through
    the status file (counted = no), the reason goes to commands.log ('# NOT COUNTED') and the closing error message;
    the stage then ends with an error after counting all others. An earlier count of the search is removed first, so
    none survives a failure."""
    ee = os.path.join(args.openms_bin, "EntrapmentEvaluator")
    for name, r, rs in searches(args):
        pooled = len(rs) > 1
        for db in databases(r, args.db):
            out = outdir(args, args.engine, bench_name(args, "per_file"), name, db)
            idxml = os.path.join(out, (rs[0]["id"] if not pooled else "pooled") + ".count.idXML")
            tsv, part = os.path.join(out, "count.tsv"), os.path.join(out, "count.part.tsv")
            dbpath = os.path.join(args.work, "db", db)
            if not args.dry_run:
                for f in (tsv, part, idxml):
                    if os.path.lexists(f):
                        os.remove(f)
                try:
                    psms = read_results(args, out, rs, pooled)
                    psms, notes = relabel(psms, settings(r["params"]), dbpath)
                    write_idxml(idxml, {"prose": "ProSE", "sage": "Sage", "msfragger": "MSFragger"}[args.engine],
                                q_values(psms))
                except Exception as err:  # a missing, cut or unreadable result: this search only
                    text = f"{args.engine} {name} {db}: not counted ({err.__class__.__name__}: {err})"
                    log(args, f"# NOT COUNTED: {text}")
                    args.failed.append(text)
                    continue
                for note in notes:
                    log(args, f"# {args.engine} {name} {db}: {note}")
            code = call(args, [ee, "-in", idxml, "-database", dbpath, "-q_value", "0.01", "-out", part])
            if args.dry_run:
                continue
            if code == 0 and os.path.exists(part):  # count.tsv only from a complete run of EntrapmentEvaluator
                os.replace(part, tsv)
            else:
                text = f"{args.engine} {name} {db}: not counted (EntrapmentEvaluator exit {code})"
                log(args, f"# NOT COUNTED: {text}")
                args.failed.append(text)


def read_results(args, out, rs, pooled):
    """The PSMs of one search folder, if its search ended ok with the inputs that the run table names (ValueError or
    OSError otherwise)."""
    status = os.path.join(out, "status")
    if not os.path.exists(status):
        raise ValueError("no status file: the search did not finish under this driver")
    state = open(status, encoding="utf-8").read().strip()
    if state != "ok":
        raise ValueError(f"search status: {state}")
    inputs, want = os.path.join(out, "inputs"), [x["id"] for x in rs]
    if os.path.exists(inputs) and open(inputs, encoding="utf-8").read().split() != want:
        raise ValueError(f"searched with {' '.join(open(inputs, encoding='utf-8').read().split())}, the run table has "
                         f"{' '.join(want)}")
    if args.engine == "prose":
        return prose_psms(os.path.join(out, "merged.idXML" if pooled else rs[0]["id"] + ".idXML"), pooled)
    if args.engine == "sage":
        res = sage_psms(out)
        missing = [x["id"] for x in rs if x["id"] not in res]
        if missing:
            raise ValueError(f"{out}/results.sage.tsv: no PSMs of {', '.join(missing)}")
        return [p for x in rs for p in res[x["id"]]]
    return percolator_psms(pooled_pin(out) if pooled else os.path.join(out, rs[0]["id"]))


def collect(args):
    """Every count.tsv of W/out -> W/counts.tsv, with the engine, benchmark, run and database in front.
    W/coverage.tsv: every search of the run table (per_file: each engine, run or sample, and database of the table) and
    every further search folder, with its status and whether it was counted. A search of the table without a folder is
    'not_run', Sage on the electron-based runs 'not_run_by_design'. Comparisons across runs use only the runs all
    compared engines completed (DATASETS.md section 4.2)."""
    cover = {}
    for name, r, _ in searches(args):  # what the run table asks for
        for engine in ("prose", "sage", "msfragger"):
            for kind in ("td", "entrap", "ref"):
                for db in databases(r, kind):
                    state = ("not_run_by_design (no z+1 ions in Sage 0.14.7)" if engine == "sage" and r["ions"] != "by"
                             else "not_run")
                    cover[(engine, "per_file", name, db[:-len(".fasta")])] = state
    for d in sorted(glob.glob(os.path.join(args.work, "out", "*", "*", "*", "*", ""))):  # what was run
        key = tuple(os.path.normpath(d).split(os.sep)[-4:])
        status = os.path.join(d, "status")
        cover[key] = open(status, encoding="utf-8").read().strip() if os.path.exists(status) else "unknown"
    cover = [f"{e}\t{b}\t{n}\t{db}\t{state}\t"
             f"{'yes' if os.path.exists(os.path.join(args.work, 'out', e, b, n, db, 'count.tsv')) else 'no'}"
             for (e, b, n, db), state in sorted(cover.items())]
    if cover and not args.dry_run:
        open(os.path.join(args.work, "coverage.tsv"), "w", encoding="utf-8").write(
            "engine\tbenchmark\trun\tdatabase\tstatus\tcounted\n" + "\n".join(cover) + "\n")
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
    table = os.path.join(args.work, "counts.tsv")
    if paths and not args.dry_run:
        open(table, "w", encoding="utf-8").write(
            "engine\tbenchmark\trun\tdatabase\t" + head + "\n" + "\n".join(lines) + "\n")
    elif not args.dry_run and os.path.exists(table):  # no count left: an old table must not stand next to coverage.tsv
        os.remove(table)
        print(f"no count.tsv: the old {table} was removed")


def default_java_gb():
    """80% of the memory the driver may use (section 4.3): the RAM (sysconf, else /proc/meminfo), capped by the
    memory.max of its cgroup and of the cgroups above it (e.g. a batch job's allocation). None if the RAM cannot be
    read."""
    try:
        total = os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")
    except (ValueError, OSError, AttributeError):
        total = 0
    if total <= 0 and os.path.exists("/proc/meminfo"):
        total = 1024 * next((int(x.split()[1]) for x in open("/proc/meminfo") if x.startswith("MemTotal:")), 0)
    if total <= 0:
        return None
    try:
        path = next(x.rstrip("\n").split(":", 2)[2] for x in open("/proc/self/cgroup") if x.startswith("0::"))
        while True:
            limit = os.path.join("/sys/fs/cgroup" + path.rstrip("/"), "memory.max")
            if os.path.exists(limit) and open(limit).read().strip() != "max":
                total = min(total, int(open(limit).read()))
            if path in ("", "/"):
                break
            path = os.path.dirname(path)
    except (OSError, StopIteration, ValueError):
        pass
    return int(0.8 * total / 2 ** 30)


STARTING, PENDING = [False], []  # call() is inside subprocess.Popen; the stop signals that came meanwhile


def stop(signum, frame):
    """Signal handler: ends the driver through an exception, as Ctrl-C does (SIGINT: KeyboardInterrupt, the others:
    SystemExit 128 + signal). While call() starts a command, the signal waits in PENDING until the command's process
    group is known, so that call() can stop it."""
    if STARTING[0]:
        PENDING.append(signum)
        return
    try:
        print(f"stopped by signal {signum}", file=sys.stderr, flush=True)
    except (OSError, ValueError):  # a closed terminal or pipe must not turn the stop into an ordinary error
        pass
    if signum == signal.SIGINT:
        raise KeyboardInterrupt
    raise SystemExit(128 + signum)


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--work", required=True)
    p.add_argument("--runs", default=os.path.join(HERE, "runs.tsv"), help="run table (default: runs.tsv next to this file)")
    p.add_argument("--only", help="comma-separated run ids or sample names (a sample only as a whole)")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--openms-bin", default=os.environ.get("OPENMS_BIN", ""))
    p.add_argument("--sage", default=os.environ.get("SAGE", "sage"))
    p.add_argument("--msfragger-jar", default=os.environ.get("MSFRAGGER_JAR", "MSFragger.jar"))
    p.add_argument("--percolator", default=os.environ.get("PERCOLATOR", "percolator"))
    p.add_argument("--mem-gb", type=int, help="hard memory cap per engine invocation in GB (at least 1), without swap "
                   "(cgroup via systemd-run --user --scope, checked before the stage); a run killed at the cap, or "
                   "stopped by its engine's own out-of-memory error, is recorded as failed_memory")
    p.add_argument("--java-gb", type=int, help="Java heap of MSFragger in GB, at least 1 (default: --mem-gb less 4, else "
                   "80%% of the memory the driver may use)")
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
            s.add_argument("--tag", help="name of an extra arm, e.g. low_memory; its results go to per_file_<tag>")
        if name == "search":
            s.add_argument("--timed", action="store_true")
            s.add_argument("--extra", help="settings of an extra arm (needs --tag). ProSE: further options, e.g. "
                           "'-Search:low_memory true'; Sage: key=JSON pairs of its configuration, e.g. "
                           "'deisotope=false'; MSFragger: key=value pairs of fragger.params, e.g. 'calibrate_mass=0'")
        if name == "scaling":
            s.add_argument("--grid", help="comma-separated thread counts (default: the grid of section 4.3)")
            s.add_argument("--limit-hours", type=float, default=24.0, help="wall-time limit per run (default 24)")
    j = sub.add_parser("joinpins")  # internal: joins Percolator input files, keeping one header
    j.set_defaults(f=joinpins)
    j.add_argument("out")
    j.add_argument("pins", nargs="+")
    args = p.parse_args()
    if getattr(args, "extra", None) and not args.tag:
        p.error("--extra needs --tag: an extra arm goes to per_file_<tag>, not over the main results")
    args.runs = os.path.abspath(args.runs)
    if args.mem_gb is not None and args.mem_gb < 1:  # 0 would mean no cap, a negative value fails every engine
        p.error(f"--mem-gb {args.mem_gb}: at least 1 GB")
    source = "--java-gb"
    if args.java_gb is None:  # MSFragger's heap from the same budget as the other engines (section 4.3)
        if args.mem_gb:
            args.java_gb, source = args.mem_gb - 4, f"--mem-gb {args.mem_gb} less 4"
        else:
            args.java_gb, source = default_java_gb(), "80% of the memory the driver may use"
    heap = getattr(args, "engine", None) == "msfragger" and args.stage in ("search", "batch", "scaling")
    if heap:  # checked only where MSFragger runs: other stages do not need its heap
        if args.java_gb is None:
            p.error("the size of the RAM cannot be read: give --mem-gb or --java-gb")
        if args.java_gb < 1:  # the JVM would not start ('Invalid maximum heap size'), recorded as failed
            p.error(f"MSFragger's Java heap would be {args.java_gb} GB ({source}): give --mem-gb 5 or more, or "
                    "--java-gb 1 or more")
        if args.mem_gb and args.java_gb > args.mem_gb - 2:
            p.error(f"--java-gb {args.java_gb} leaves MSFragger's JVM no room under --mem-gb {args.mem_gb}")
    if not args.dry_run:
        os.makedirs(args.work, exist_ok=True)
        if args.mem_gb and args.stage in ("convert", "search", "count", "batch", "scaling"):
            check_cap(args)
    if heap:
        log(args, f"# MSFragger Java heap {args.java_gb} GB ({source})")
    # SIGTERM (kill, a batch system), SIGHUP (a closed terminal) and SIGQUIT end the driver like Ctrl-C, so that
    # call() stops the engine and measure() records the search as interrupted; Ctrl-C goes through the same handler,
    # so that a signal while an engine starts waits for its process group; a signal ignored at the start (nohup, a
    # background job) stays ignored
    for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP, signal.SIGQUIT):
        if signal.getsignal(sig) in (signal.SIG_DFL, signal.default_int_handler):
            signal.signal(sig, stop)
    args.failed = []  # searches whose engine exited with an error (measure)
    args.f(args)
    if args.failed:
        sys.exit(f"{len(args.failed)} failed command(s), the other searches ran:\n  " + "\n  ".join(args.failed))


if __name__ == "__main__":
    main()
