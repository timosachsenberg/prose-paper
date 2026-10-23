#!/usr/bin/env bash
# Builds the databases of the further datasets (DATASETS.md, section 2) from the FASTAs the original authors deposited,
# with DecoyDatabase from OpenMS develop (>= 916a7d5, PR OpenMS/OpenMS#10629).
#
# usage: build_section2_dbs.sh <OpenMS bin dir> <work dir>
#
# Downloads and checks the authors' FASTAs into <work dir>/authors, removes their decoys, and writes to <work dir>/db2:
#   shuffled entrapment, r = 1, seeds 1/2/3: PXD011695 (mouse), PXD065289 (human), PXD042233 (human + contaminants),
#   iPRG2015 (PXD010981), Percolator yeast and worm sets;
#   target-decoy only, no entrapment: PXD019643 and PXD058436 (immunopeptidomics). PXD058436 deposits no FASTA; it gets
#   human_sp.fasta from archive.openms.de (Swiss-Prot human of UniProt release 2026_01, 20,431 entries, the database of OpenMS/OpenMS#10634 and #10639).
# Decoys and entrapment are made as in build_entrapment_dbs.sh: full-protein reversal with DECOY_, peptide-wise shuffle
# with C-terminus, K, R and P fixed, enzyme Trypsin/P. The authors' own decoys are not used (they differ between datasets).
set -euo pipefail
BIN=$1
W=$2
A=$W/authors
O=$W/db2
mkdir -p "$A" "$O"
PRIDE=https://ftp.pride.ebi.ac.uk/pride/data/archive
PERC=https://noble.gs.washington.edu/proj/percolator/data

fetch() { # url sha256
  local f="$A/$(basename "$1")"
  [ -s "$f" ] || curl -fsS -o "$f" "$1"
  echo "$2  $f" | sha256sum -c --quiet -
}
fetch $PRIDE/2019/05/PXD011695/010090_MusMusculus_Uniprot_ISOFORMS_CONCAT_20161109.fasta 0f5564e11bb0dcbfffe8558e0d059b1ff03b5e63f93dc4415cab2541195125bc
fetch $PRIDE/2026/03/PXD065289/fasta.zip 472992dffc1399ecdf0a6510506ab1c39dce89a80d1cddd578798dab0c5309d5
fetch $PRIDE/2023/12/PXD042233/UP000005640_9606.fasta 77bf2be9642c3f3acdd2bebc2c06d38f395f9da78120ce9c3940cbf2797792b7
fetch $PRIDE/2023/12/PXD042233/contaminants.fasta 0f177988937dbd5bbd2c792094d8bb9123212adc7050a5cce7cd20a6b521ed1e
fetch $PRIDE/2018/09/PXD010981/iPRG2015_decoy.fasta 32f8a2777f9122c8224555099ef2ab0f26f3a502c3cd12b5b035739d7d843306
fetch $PRIDE/2021/04/PXD019643/sp_21_04_2020_decoy.fasta d351fdc0add26d0a1eb6c2214ee9bf597096387c866f2d6e6ed4507a7a090dcd
fetch $PERC/yeast.fasta.gz b9e7f719281fac9fda9f1d2f33552d2a7a61136ea909a7c64f9a7c00acacab9d
fetch $PERC/worm.fasta.gz 52f3e478fbef55c853218053a2e85ecaf7b2d7ba367a2f6b0641e8cfcdbdb30a
fetch https://archive.openms.de/openms/testfiles/human_sp.fasta b205ed9970fee62413e2f192c6fb82daab86e4a5897ef521f907ecbfcd7b3e63

# PXD065289: only the human database (HEK293 runs) of the authors' archive
unzip -o -q -j "$A/fasta.zip" fasta/2024-10-29-decoys-contam-UP000005640_9606.fasta.fas -d "$A"
echo "e1258d432063e0aa36b0fd63bd182b5b92c9600c8742d9fed3c59ae2c0b95730  $A/2024-10-29-decoys-contam-UP000005640_9606.fasta.fas" | sha256sum -c --quiet -

# targets <out> <decoy prefix or -> <in>...: the input entries without the authors' decoys
targets() {
  local out=$1 pre=$2; shift 2
  for f in "$@"; do case $f in *.gz) zcat "$f" ;; *) cat "$f" ;; esac; done |
    awk -v pre="$pre" '/^>/ { keep = (pre == "-" || index($0, ">" pre) != 1) } keep' > "$out"
  echo "$(basename "$out"): $(grep -c '^>' "$out") targets"
}
targets "$A/pxd011695_mouse_targets.fasta" DECOY_ "$A/010090_MusMusculus_Uniprot_ISOFORMS_CONCAT_20161109.fasta"
targets "$A/pxd065289_human_targets.fasta" rev_ "$A/2024-10-29-decoys-contam-UP000005640_9606.fasta.fas"
targets "$A/pxd042233_human_targets.fasta" - "$A/UP000005640_9606.fasta" "$A/contaminants.fasta"
targets "$A/iprg2015_targets.fasta" DECOY_ "$A/iPRG2015_decoy.fasta"
targets "$A/pxd019643_targets.fasta" DECOY_ "$A/sp_21_04_2020_decoy.fasta"
targets "$A/pxd058436_targets.fasta" - "$A/human_sp.fasta"
targets "$A/percolator_yeast_targets.fasta" - "$A/yeast.fasta.gz"
# the Percolator yeast FASTA ends 6,698 sequences with a stop codon '*', and 6 pseudogenes/ORFs have '*' inside; DecoyDatabase
# turns '*' into 'X' in the entrapment copies, so: drop the final '*', and write the inner ones as 'X' (unknown residue)
python3 -I - "$A/percolator_yeast_targets.fasta" <<'EOF'
import sys
p = sys.argv[1]
entries, h, s = [], None, []
for line in open(p):
    if line.startswith(">"):
        if h is not None: entries.append((h, "".join(s)))
        h, s = line, []
    else: s.append(line.strip())
entries.append((h, "".join(s)))
with open(p, "w") as out:
    for h, seq in entries:
        out.write(h + seq.rstrip("*").replace("*", "X") + "\n")
EOF
targets "$A/percolator_worm_targets.fasta" - "$A/worm.fasta.gz"

decoy() {
  "$BIN/DecoyDatabase" -in "$1" -out "$2" -enzyme Trypsin/P \
    -Decoy:keepPeptideNTerm false -Decoy:keepPeptideCTerm false "${@:3}" -no_progress
}
for db in pxd011695_mouse pxd065289_human pxd042233_human iprg2015 percolator_yeast percolator_worm; do
  for seed in 1 2 3; do
    decoy "$A/${db}_targets.fasta" "$O/${db}_entrap_s${seed}_td.fasta" -entrapment_ratio 1 -seed "$seed"
  done
done
decoy "$A/pxd019643_targets.fasta" "$O/pxd019643_td.fasta"
decoy "$A/pxd058436_targets.fasta" "$O/pxd058436_td.fasta"

(cd "$O" && sha256sum ./*_td.fasta > SHA256SUMS)
cat "$O/SHA256SUMS"
