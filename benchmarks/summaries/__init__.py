"""Summaries of the ProSE benchmark tables (SPEC v2 = checks/analysis_validation/design/SPEC.md).

benchmarks/summarize.py is the entry point. The package turns W/counts.tsv, W/coverage.tsv and W/timings.tsv (and,
where present, the engine logs under W/out/) into every number, table and figure of the paper (DATASETS.md section
4.5, "Summaries"):

  design.py   fixed design constants (SPEC section 2.2)
  tables.py   loaders, validation, timing attempts, comparison sets, stats helpers and the Ctx object (sections 2.1-2.7)
  fdp.py      O11, O12, O13, O26           ids.py     O1-O3, O4-O7 glue, O8, O9, O9b, O10 counts, O23-O25
  timing.py   O10 time part, O15-O17       calib.py   O19-O21
  checks.py   the consistency layer        figures.py the only module that imports matplotlib

No bytecode is written into the repository (SPEC section 1): summarize.py sets sys.dont_write_bytecode before it
imports this package, and the flag is set here again for any other importer.
"""
import sys

sys.dont_write_bytecode = True
