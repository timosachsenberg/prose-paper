# ProSE paper

Material for the publication on ProSE, the database search engine of [OpenMS](https://github.com/OpenMS/OpenMS).

## Contents

| Path | What |
|---|---|
| [`datasets/DATASETS.md`](datasets/DATASETS.md) | The benchmark datasets. Main benchmark: 20 DDA runs, seven acquisition groups, full runs, 1,509,392 MS2. Further candidates: ETD, Astral, low resolution, immunopeptidomics. Also databases, entrapment and open decisions. All with download links. |
| [`datasets/prepare_inputs.sh`](datasets/prepare_inputs.sh) | Downloads and checks the input FASTAs of the main benchmark (`hy`, `hye`, `human`; *Arabidopsis*). |
| [`datasets/build_entrapment_dbs.sh`](datasets/build_entrapment_dbs.sh) | Builds the target/entrapment/decoy databases with OpenMS `DecoyDatabase` (develop ≥ `916a7d5`). |
| [`datasets/entrapment_dbs.sha256`](datasets/entrapment_dbs.sha256) | SHA256 of the uncompressed databases. |
| [`datasets/databases/`](datasets/databases/) | The twelve built databases (`.fasta.gz`). |

## Rebuilding the databases

The build is deterministic: the same OpenMS commit gives byte-identical files.

```bash
./datasets/prepare_inputs.sh work
OPENMS_DATA_PATH=<OpenMS source>/share/OpenMS ./datasets/build_entrapment_dbs.sh <OpenMS build>/bin work
sha256sum -c datasets/entrapment_dbs.sha256   # run inside work/db
```
