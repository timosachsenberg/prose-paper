#!/usr/bin/env bash
# Builds the databases of the further datasets (DATASETS.md, section 2) from the FASTAs the original authors deposited,
# with DecoyDatabase from OpenMS develop (>= 916a7d5, PR OpenMS/OpenMS#10629; the files in the repository: the frozen
# fbb25191d7).
#
# usage: build_section2_dbs.sh <OpenMS bin dir> <work dir>
#
# Downloads and checks the authors' FASTAs into <work dir>/authors, removes their decoys, and writes to <work dir>/db2:
#   shuffled entrapment, r = 1, seeds 1/2/3: PXD011695 (mouse), PXD065289 (human), PXD042233 (human + contaminants),
#   iPRG2015 (PXD010981);
#   target-decoy only, no entrapment: PXD019643 and PXD058436 (immunopeptidomics). PXD058436 deposits no FASTA; it gets human_sp.fasta from archive.openms.de (Swiss-Prot human of UniProt release 2026_01, 20,431 entries, the database of OpenMS/OpenMS#10634 and #10639).
# Decoys and entrapment are made as in build_entrapment_dbs.sh: the decoys ProSE generates by default (peptide-wise
# reversal with the first and last residue of each segment and K, R and P in place; Trypsin/P), the
# entrapment a peptide-wise shuffle with C-terminus, K, R and P fixed (Trypsin/P). For the unspecific immunopeptidomics
# searches ProSE reverses the whole protein and keeps an initial Met in front, and so do their databases (below).
# The authors' own decoys are not used (they differ between datasets).
set -euo pipefail
BIN=$1
W=$2
A=$W/authors
O=$W/db2
mkdir -p "$A" "$O"
PRIDE=https://ftp.pride.ebi.ac.uk/pride/data/archive

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

decoy() {
  "$BIN/DecoyDatabase" -in "$1" -out "$2" -enzyme Trypsin/P \
    -Decoy:keepPeptideNTerm true -Decoy:keepPeptideCTerm true -Decoy:non_shuffle_pattern K,P,R "${@:3}" -no_progress
}
# unspecific <targets> <out>: the decoys of ProSE for a non-specific search with peptide:clip_nterm_methionine (on in
# the parameter files): the whole protein reversed, an initial Met kept in front. DecoyDatabase reverses whole proteins
# for 'no cleavage'; the trailing M of a reversed Met-initial protein is then moved back to the front.
unspecific() {
  "$BIN/DecoyDatabase" -in "$1" -out "$2.tmp" -enzyme "no cleavage" -no_progress
  python3 -I - "$2.tmp" "$2" <<'EOF'
import sys
entries, h, s = [], None, []
for line in open(sys.argv[1]):
    line = line.rstrip("\n")
    if line.startswith(">"):
        if h is not None: entries.append((h, "".join(s)))
        h, s = line, []
    else: s.append(line)
entries.append((h, "".join(s)))
n, target = 0, None
with open(sys.argv[2], "w") as out:
    for h, seq in entries:
        if not h.startswith(">DECOY_"):
            target = seq
        else:
            assert seq == target[::-1], h
            if len(target) > 1 and target[0] == "M":
                seq, n = "M" + seq[:-1], n + 1
        out.write(h + "\n" + "".join(seq[i:i + 80] + "\n" for i in range(0, len(seq), 80)))
print(sys.argv[2], "decoys with the initial Met in front:", n)
EOF
  rm "$2.tmp"
}
for db in pxd011695_mouse pxd065289_human pxd042233_human iprg2015; do
  for seed in 1 2 3; do
    decoy "$A/${db}_targets.fasta" "$O/${db}_entrap_s${seed}_td.fasta" -entrapment_ratio 1 -seed "$seed"
  done
done
# The plain target-decoy databases of the tryptic sets (the databases of the identification counts and timings) are
# written afterwards by build_plain_td_dbs.sh, from the databases built here.
unspecific "$A/pxd019643_targets.fasta" "$O/pxd019643_td.fasta"
unspecific "$A/pxd058436_targets.fasta" "$O/pxd058436_td.fasta"

(cd "$O" && sha256sum ./*_td.fasta > SHA256SUMS)
cat "$O/SHA256SUMS"
