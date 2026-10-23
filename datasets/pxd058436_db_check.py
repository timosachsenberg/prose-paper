"""How many peptides and proteins of the published PXD058436 results (MHCquant2, FragPipe, PEAKS) a FASTA lacks.

usage: pxd058436_db_check.py <dir with the PRIDE result tables> <fasta>[,<label>] ...

Reads the per-sample result tables deposited on PRIDE (`<sample>_prediction_result{,_fragpipe,_peaks}.tsv` for class I,
`<sample>.tsv`, `<sample>_fragpipe.tsv`, `<sample>_peaks.csv` for class II), strips modifications, and looks each
peptide up in the FASTA's target sequences (exact and with I = L). Prints per sample and tool, then the union over
all tables per HLA class, as TSV."""
import csv, glob, os, re, sys, collections, json
csv.field_size_limit(1 << 30)
res = sys.argv[1]
K = 7

def read_fasta(p):
    seqs, accs, h, s = [], set(), None, []
    for l in open(p):
        if l.startswith(">"):
            if h is not None: seqs.append("".join(s))
            h, s = l[1:].split()[0], []
            if h.startswith("DECOY_"): h = None; continue
            parts = h.split("|"); accs.add(parts[1] if len(parts) > 2 else h)
        elif h is not None: s.append(l.strip())
        else: pass
    if h is not None: seqs.append("".join(s))
    return seqs, accs

def clean(p):
    p = re.sub(r"\(.*?\)|\[.*?\]|\{.*?\}", "", p)
    p = p.split(".")[1] if p.count(".") == 2 and len(p.split(".")[1]) > 3 else p
    return re.sub(r"[^A-Z]", "", p)

def accs_of(field):
    out = set()
    for a in re.split(r"[;,:\s]+", field or ""):
        a = a.strip().strip('"')
        if not a: continue
        parts = a.split("|")
        acc = parts[1] if len(parts) >= 3 else parts[0]
        if re.fullmatch(r"[OPQ][0-9][A-Z0-9]{3}[0-9](-\d+)?|[A-NR-Z][0-9]([A-Z][A-Z0-9]{2}[0-9]){1,2}(-\d+)?", acc): out.add(acc)
    return out

def load(path):
    delim = "," if path.endswith(".csv") else "\t"
    peps, accs = set(), set()
    with open(path, newline="") as f:
        r = csv.DictReader(f, delimiter=delim)
        pc = next(c for c in ["sequence", "Peptide", "peptide"] if c in r.fieldnames)
        ac = [c for c in ["proteins", "accessions", "Protein", "Mapped Proteins", "Accession"] if c in r.fieldnames]
        for row in r:
            peps.add(clean(row[pc]))
            for c in ac: accs |= accs_of(row[c])
    peps.discard("")
    return peps, accs

files = sorted(f for f in glob.glob(res + "/DN*_class*") if not f.endswith(".mzTab"))
def tool(f):
    b = os.path.basename(f)
    return "FragPipe" if "fragpipe" in b else "PEAKS" if "peaks" in b else "MHCquant2"
def sample(f):
    return re.match(r"(DN\d+_[A-Za-z]+_class(?:II|I))", os.path.basename(f)).group(1)
data = {(sample(f), tool(f)): load(f) for f in files}

for spec in sys.argv[2:]:
    path, label = (spec.split(",") + [os.path.basename(spec)])[:2]
    seqs, faccs = read_fasta(path)
    big = "#".join(seqs); bigIL = big.replace("I", "L")
    idx = collections.defaultdict(list)
    for i in range(len(bigIL) - K + 1):
        k = bigIL[i:i + K]
        if "#" not in k: idx[k].append(i)
    def present(p, il):
        q = p.replace("I", "L") if il else p
        hay = bigIL if il else big
        if len(q) < K: return q in hay
        return any(hay.startswith(q, i) for i in idx.get(q[:K].replace("I", "L"), ()))
    print(f"# {label}: {path}, {len(seqs)} target entries, {len(big) - len(seqs) + 1} residues")
    print("fasta\tsample\ttool\tpeptides\tmissing_exact\tmissing_IL\tproteins\tproteins_missing")
    union = {"classI": set(), "classII": set()}; uacc = set()
    for (s, t), (peps, accs) in sorted(data.items()):
        miss = [p for p in peps if not present(p, False)]
        missIL = [p for p in miss if not present(p, True)]
        print(f"{label}\t{s}\t{t}\t{len(peps)}\t{len(miss)}\t{len(missIL)}\t{len(accs)}\t{len(accs - faccs)}")
        union["classII" if s.endswith("classII") else "classI"] |= peps; uacc |= accs
    for c, ps in union.items():
        missIL = sorted(p for p in ps if not present(p, True))
        print(f"{label}\tall\tunion {c}\t{len(ps)}\t\t{len(missIL)}\t\t\t{','.join(missIL)}")
    print(f"{label}\tall\tunion proteins\t\t\t\t{len(uacc)}\t{len(uacc - faccs)}\t{','.join(sorted(uacc - faccs))}")
