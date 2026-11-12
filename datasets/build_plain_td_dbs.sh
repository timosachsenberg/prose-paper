#!/usr/bin/env bash
# Writes the plain target-decoy databases (targets and their decoys, no entrapment): the databases of the
# identification counts and timings (DATASETS.md, sections 3.2 and 3.3).
#
# usage: build_plain_td_dbs.sh <out dir> <dir with entrapment databases>...
#        e.g. build_plain_td_dbs.sh work/plain work/db work/db2     (after the two build scripts)
#          or build_plain_td_dbs.sh work/plain datasets/databases   (from the files of this repository)
#        The databases may be .fasta or .fasta.gz.
#
# Each <name>_td.fasta is <name>_entrap_s1_td.fasta without its ENTRAP_ and DECOY_ENTRAP_ entries, so it holds exactly
# the targets and decoys of the entrapment databases. The three realisations must give the same file (checked).
# This is what DecoyDatabase writes without -entrapment_ratio: for iPRG2015, built directly from the same targets with
# the options of build_section2_dbs.sh, the two files are byte-identical (checked on 2026-11-12, DATASETS.md section 3).
# No OpenMS is needed.
set -euo pipefail
O=$1
shift
mkdir -p "$O"

src() { # <name>: prints the uncompressed database
  for d in "${DIRS[@]}"; do
    if [ -f "$d/$1.fasta" ]; then cat "$d/$1.fasta"; return; fi
    if [ -f "$d/$1.fasta.gz" ]; then zcat "$d/$1.fasta.gz"; return; fi
  done
  echo "$1: not found in ${DIRS[*]}" >&2
  return 1
}
DIRS=("$@")
plain() { # <entrapment database name>: prints it without the entrapment entries
  src "$1" | awk '/^>/ { keep = (index($0, ">ENTRAP_") != 1 && index($0, ">DECOY_ENTRAP_") != 1) } keep'
}
sum() { sha256sum | cut -c1-64; }

for db in hy hye human pxd011695_mouse pxd065289_human pxd042233_human iprg2015; do
  plain "${db}_entrap_s1_td" > "$O/${db}_td.fasta"
  a=$(sum < "$O/${db}_td.fasta")
  for seed in 2 3; do
    [ "$(plain "${db}_entrap_s${seed}_td" | sum)" = "$a" ] || { echo "$db: realisation $seed gives another file" >&2; exit 1; }
  done
  echo "${db}_td.fasta: $(grep -c '^>' "$O/${db}_td.fasta") entries, $(grep -c '^>DECOY_' "$O/${db}_td.fasta") decoys"
done

(cd "$O" && sha256sum ./hy_td.fasta ./hye_td.fasta ./human_td.fasta ./pxd011695_mouse_td.fasta ./pxd065289_human_td.fasta \
  ./pxd042233_human_td.fasta ./iprg2015_td.fasta > SHA256SUMS.plain)
cat "$O/SHA256SUMS.plain"
