# ProSE paper

Material for the publication on ProSE, the database search engine of [OpenMS](https://github.com/OpenMS/OpenMS).

## Contents

| Path | What |
|---|---|
| [`datasets/DATASETS.md`](datasets/DATASETS.md) | The benchmark datasets. Main benchmark: 20 DDA runs, seven acquisition groups, full runs, 1,509,392 MS2. Further candidates: ETD, Astral, low resolution, immunopeptidomics. Also databases, entrapment and open decisions. All with download links. |
| [`datasets/prepare_inputs.sh`](datasets/prepare_inputs.sh) | Downloads and checks the input FASTAs of the main benchmark (`hy`, `hye`, `human`; *Arabidopsis*). |
| [`datasets/build_entrapment_dbs.sh`](datasets/build_entrapment_dbs.sh) | Builds the target/entrapment/decoy databases with OpenMS `DecoyDatabase` (develop ≥ `916a7d5`). |
| [`datasets/build_section2_dbs.sh`](datasets/build_section2_dbs.sh) | Builds the databases of the further datasets from the FASTAs the original authors deposited. They are checked by SHA256, and immunopeptidomics gets target-decoy only. |
| [`datasets/entrapment_dbs.sha256`](datasets/entrapment_dbs.sha256), [`datasets/section2_dbs.sha256`](datasets/section2_dbs.sha256) | SHA256 of the uncompressed databases. |
| [`datasets/databases/`](datasets/databases/) | All 31 built databases (`.fasta.gz`): 12 for the main benchmark, 19 for the further datasets. [`SHA256SUMS.gz.txt`](datasets/databases/SHA256SUMS.gz.txt) has the SHA256 of the `.gz` files. |

## Rebuilding the databases

The build is deterministic: the same OpenMS commit gives byte-identical files.

```bash
./datasets/prepare_inputs.sh work
export OPENMS_DATA_PATH=<OpenMS source>/share/OpenMS
./datasets/build_entrapment_dbs.sh <OpenMS build>/bin work   # -> work/db
./datasets/build_section2_dbs.sh <OpenMS build>/bin work     # -> work/db2
(cd work/db && sha256sum -c ../../datasets/entrapment_dbs.sha256)
(cd work/db2 && sha256sum -c ../../datasets/section2_dbs.sha256)
```
