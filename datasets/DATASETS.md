# ProSE publication: benchmark datasets

Status: draft, 2026-10-23. Every download link below was checked (HTTP 200, size as listed).

## 1. Main benchmark: 20 DDA runs, seven acquisition groups, full runs

This is the suite of issue [OpenMS/OpenMS#10364](https://github.com/OpenMS/OpenMS/issues/10364), with one change: every run is
searched **in full** instead of the 8,000 MS2 spectra sampled per file there. All numbers published in OpenMS/OpenMS#10364 and
the PRs that cite it are on the 8,000-spectrum subsets and have to be re-measured on the full runs.

The mzML files are the exact inputs frozen on 2026-09-30 (size and SHA256 from the reproduction package's
`inputs.json`, [README](https://github.com/OpenMS/OpenMS/blob/a5705ec8e1cb19d40ebfa7bb16f6b5651aa1dc65/benchmark-reproduction/prose-andes/README.md)).
Spectrum counts are from the package's per-file provenance (`broad_benchmark/provenance/<id>.json`).

**Totals:** 1,509,392 MS2 spectra; 1,497,401 of them with a recorded precursor charge of 2–5.

| Group | ID | Run | MS2 | Charge 2–5 | MS1 | mzML (as frozen) | Vendor raw (timsTOF: the input) |
|---|---|---|---:|---:|---:|---|---|
| LTQ Orbitrap Velos, ion-trap CID | `velos_125_R1` | PXD001819 UPS1_125amol_R1 | 36,802 | 36,768 | 7,277 | [mzML.gz](https://archive.openms.de/openms/benchmarks/pride-benchmarks/lfq/LTQOrbitrapVelos/PXD001819/UPS1_125amol_R1.mzML.gz) (398 MB) | [raw](https://ftp.pride.ebi.ac.uk/pride/data/archive/2015/12/PXD001819/UPS1_125amol_R1.raw) (1.7 GB) |
| | `velos_5000_R2` | PXD001819 UPS1_5000amol_R2 | 38,046 | 38,005 | 7,195 | [mzML.gz](https://archive.openms.de/openms/benchmarks/pride-benchmarks/lfq/LTQOrbitrapVelos/PXD001819/UPS1_5000amol_R2.mzML.gz) (405 MB) | [raw](https://ftp.pride.ebi.ac.uk/pride/data/archive/2015/12/PXD001819/UPS1_5000amol_R2.raw) (1.7 GB) |
| | `velos_25000_R3` | PXD001819 UPS1_25000amol_R3 | 40,439 | 40,398 | 6,973 | [mzML.gz](https://archive.openms.de/openms/benchmarks/pride-benchmarks/lfq/LTQOrbitrapVelos/PXD001819/UPS1_25000amol_R3.mzML.gz) (418 MB) | [raw](https://ftp.pride.ebi.ac.uk/pride/data/archive/2015/12/PXD001819/UPS1_25000amol_R3.raw) (1.7 GB) |
| Q Exactive HF-X, HCD | `hfx_A2` | ProteoBench Module 2, Condition_A_Sample_Alpha_02 | 111,413 | 111,413 | 26,090 | [mzML.gz](https://archive.openms.de/openms/benchmarks/pride-benchmarks/lfq/QExactiveHF/ProteoBench_Module_2/LFQ_Orbitrap_DDA_Condition_A_Sample_Alpha_02.mzML.gz) (501 MB) | [raw](https://archive.openms.de/openms/benchmarks/pride-benchmarks/lfq/QExactiveHF/ProteoBench_Module_2/LFQ_Orbitrap_DDA_Condition_A_Sample_Alpha_02.raw) (3.6 GB) |
| | `hfx_B1` | ProteoBench Module 2, Condition_B_Sample_Alpha_01 | 111,088 | 111,088 | 25,931 | [mzML.gz](https://archive.openms.de/openms/benchmarks/pride-benchmarks/lfq/QExactiveHF/ProteoBench_Module_2/LFQ_Orbitrap_DDA_Condition_B_Sample_Alpha_01.mzML.gz) (485 MB) | [raw](https://archive.openms.de/openms/benchmarks/pride-benchmarks/lfq/QExactiveHF/ProteoBench_Module_2/LFQ_Orbitrap_DDA_Condition_B_Sample_Alpha_01.raw) (3.5 GB) |
| | `hfx_B3` | ProteoBench Module 2, Condition_B_Sample_Alpha_03 | 118,174 | 118,174 | 24,689 | [mzML.gz](https://archive.openms.de/openms/benchmarks/pride-benchmarks/lfq/QExactiveHF/ProteoBench_Module_2/LFQ_Orbitrap_DDA_Condition_B_Sample_Alpha_03.mzML.gz) (514 MB) | [raw](https://archive.openms.de/openms/benchmarks/pride-benchmarks/lfq/QExactiveHF/ProteoBench_Module_2/LFQ_Orbitrap_DDA_Condition_B_Sample_Alpha_03.raw) (3.7 GB) |
| Orbitrap Astral, HCD | `astral_A2` | ProteoBench Module 8, 15min_50ng_Condition_A_REP2 | 123,621 | 123,607 | 3,680 | [mzML.gz](https://archive.openms.de/openms/benchmarks/pride-benchmarks/lfq/OrbitrapAstral/ProteoBench_Module_8/LFQ_Astral_DDA_15min_50ng_Condition_A_REP2.mzML.gz) (1.0 GB) | [raw](https://archive.openms.de/openms/benchmarks/pride-benchmarks/lfq/OrbitrapAstral/ProteoBench_Module_8/LFQ_Astral_DDA_15min_50ng_Condition_A_REP2.raw) (2.6 GB) |
| | `astral_B1` | ProteoBench Module 8, 15min_50ng_Condition_B_REP1 | 122,686 | 122,659 | 3,702 | [mzML.gz](https://archive.openms.de/openms/benchmarks/pride-benchmarks/lfq/OrbitrapAstral/ProteoBench_Module_8/LFQ_Astral_DDA_15min_50ng_Condition_B_REP1.mzML.gz) (1.0 GB) | [raw](https://archive.openms.de/openms/benchmarks/pride-benchmarks/lfq/OrbitrapAstral/ProteoBench_Module_8/LFQ_Astral_DDA_15min_50ng_Condition_B_REP1.raw) (2.6 GB) |
| | `astral_B3` | ProteoBench Module 8, 15min_50ng_Condition_B_REP3 | 122,647 | 122,625 | 3,697 | [mzML.gz](https://archive.openms.de/openms/benchmarks/pride-benchmarks/lfq/OrbitrapAstral/ProteoBench_Module_8/LFQ_Astral_DDA_15min_50ng_Condition_B_REP3.mzML.gz) (1.0 GB) | [raw](https://archive.openms.de/openms/benchmarks/pride-benchmarks/lfq/OrbitrapAstral/ProteoBench_Module_8/LFQ_Astral_DDA_15min_50ng_Condition_B_REP3.raw) (2.6 GB) |
| Orbitrap Fusion Lumos, HCD, LFQ | `lumos_lfq_5192` | PXD007683 a05192 | 73,549 | 73,549 | 13,613 | [mzML.gz](https://archive.openms.de/openms/benchmarks/pride-benchmarks/lfq/OrbitrapFusionLumos/PXD007683/a05192.mzML.gz) (294 MB) | [raw](https://ftp.pride.ebi.ac.uk/pride/data/archive/2018/04/PXD007683/a05192.raw) (663 MB) |
| | `lumos_lfq_5194` | PXD007683 a05194 | 74,198 | 74,198 | 13,450 | [mzML.gz](https://archive.openms.de/openms/benchmarks/pride-benchmarks/lfq/OrbitrapFusionLumos/PXD007683/a05194.mzML.gz) (295 MB) | [raw](https://ftp.pride.ebi.ac.uk/pride/data/archive/2018/04/PXD007683/a05194.raw) (666 MB) |
| | `lumos_lfq_5199` | PXD007683 a05199 | 73,666 | 73,666 | 13,443 | [mzML.gz](https://archive.openms.de/openms/benchmarks/pride-benchmarks/lfq/OrbitrapFusionLumos/PXD007683/a05199.mzML.gz) (292 MB) | [raw](https://ftp.pride.ebi.ac.uk/pride/data/archive/2018/04/PXD007683/a05199.raw) (660 MB) |
| Orbitrap Fusion Lumos, ion-trap CID, TMT6plex | `lumos_tmt_5058` | PXD007683 a05058 | 37,330 | 37,330 | 6,870 | [mzML.gz](https://archive.openms.de/openms/benchmarks/pride-benchmarks/tmt/OrbitrapFusionLumos/PXD007683/a05058.mzML.gz) (376 MB) | [raw](https://ftp.pride.ebi.ac.uk/pride/data/archive/2018/04/PXD007683/a05058.raw) (537 MB) |
| | `lumos_tmt_5059` | PXD007683 a05059 | 37,536 | 37,536 | 6,471 | [mzML.gz](https://archive.openms.de/openms/benchmarks/pride-benchmarks/tmt/OrbitrapFusionLumos/PXD007683/a05059.mzML.gz) (380 MB) | [raw](https://ftp.pride.ebi.ac.uk/pride/data/archive/2018/04/PXD007683/a05059.raw) (534 MB) |
| | `lumos_tmt_5066` | PXD007683 a05066 | 41,078 | 41,078 | 6,051 | [mzML.gz](https://archive.openms.de/openms/benchmarks/pride-benchmarks/tmt/OrbitrapFusionLumos/PXD007683/a05066.mzML.gz) (425 MB) | [raw](https://ftp.pride.ebi.ac.uk/pride/data/archive/2018/04/PXD007683/a05066.raw) (593 MB) |
| Orbitrap Exploris 480, HCD, TMTpro | `eclipse_tmtpro_10855` | PXD054559 xb10855 | 33,013 | 33,013 | 8,764 | [mzML.gz](https://archive.openms.de/openms/benchmarks/pride-benchmarks/tmt/OrbitrapEclipse/PXD054559/xb10855.mzML.gz) (128 MB) | [raw](https://ftp.pride.ebi.ac.uk/pride/data/archive/2024/10/PXD054559/xb10855.raw) (361 MB) |
| | `eclipse_tmtpro_10858` | PXD054559 xb10858 | 32,637 | 32,637 | 8,689 | [mzML.gz](https://archive.openms.de/openms/benchmarks/pride-benchmarks/tmt/OrbitrapEclipse/PXD054559/xb10858.mzML.gz) (117 MB) | [raw](https://ftp.pride.ebi.ac.uk/pride/data/archive/2024/10/PXD054559/xb10858.raw) (333 MB) |
| | `eclipse_tmtpro_10863` | PXD054559 xb10863 | 33,517 | 33,517 | 8,667 | [mzML.gz](https://archive.openms.de/openms/benchmarks/pride-benchmarks/tmt/OrbitrapEclipse/PXD054559/xb10863.mzML.gz) (121 MB) | [raw](https://ftp.pride.ebi.ac.uk/pride/data/archive/2024/10/PXD054559/xb10863.raw) (344 MB) |
| timsTOF HT, DDA-PASEF, plasma | `tims_plasma_30min` | PXD053748 DDA_30min_200ng_QCPlasma_Slot1-36_1_4363 | 115,047 | 109,511 | 2,533 | [mzml](https://ftp.pride.ebi.ac.uk/pride/data/archive/2025/02/PXD053748/DDA_30min_200ng_QCPlasma_Slot1-36_1_4363.mzml) (2.2 GB) | [d.zip](https://ftp.pride.ebi.ac.uk/pride/data/archive/2025/02/PXD053748/DDA_30min_200ng_QCPlasma_Slot1-36_1_4363.d.zip) (1.6 GB) |
| | `tims_plasma_50min` | PXD053748 DDA_50min_200ng_QCPlasma_Slot1-36_1_4367 | 132,905 | 126,629 | 3,440 | [mzml](https://ftp.pride.ebi.ac.uk/pride/data/archive/2025/02/PXD053748/DDA_50min_200ng_QCPlasma_Slot1-36_1_4367.mzml) (2.7 GB) | [d.zip](https://ftp.pride.ebi.ac.uk/pride/data/archive/2025/02/PXD053748/DDA_50min_200ng_QCPlasma_Slot1-36_1_4367.d.zip) (2.0 GB) |

Notes on the files:

- **Project pages:**
  - [PXD001819](https://www.ebi.ac.uk/pride/archive/projects/PXD001819): UPS1 spiked into yeast.
  - [PXD007683](https://www.ebi.ac.uk/pride/archive/projects/PXD007683)
  - [PXD054559](https://www.ebi.ac.uk/pride/archive/projects/PXD054559)
  - [PXD053748](https://www.ebi.ac.uk/pride/archive/projects/PXD053748)
  - [PXD028735](https://www.ebi.ac.uk/pride/archive/projects/PXD028735) (Van Puyvelde et al., Sci Data 2022): source of ProteoBench Module 2, HF-X, HYE mix, "Alpha" series.
  - [PXD070049](https://www.ebi.ac.uk/pride/archive/projects/PXD070049) ("LFQ Benchmark Dataset – Generation Beta", public since 2026-02-03): source of the ProteoBench Astral DDA module (Module 8 here). Mix A = H65/Y30/E5, B = H65/Y15/E20.
  - [ProteoBench](https://proteobench.readthedocs.io) documents both modules.
- **ProteoBench:** the HF-X and Astral files are the ProteoBench copies on archive.openms.de. Each of the six raw files there has the same byte size as the file of the same name on PRIDE (PXD028735, PXD070049); the hashes were not compared. For the paper, cite the PRIDE accessions.
- **Folder names:** the archive folder `OrbitrapEclipse` holds Exploris 480 data. The suite IDs keep the `eclipse_` prefix.
- **TMT6plex runs:** each file also holds one MS3 scan per MS2 scan (37–41k). Only the CID MS2 spectra are searched.
- **timsTOF files:** the paper reads the Bruker `.d.zip` directly with ProSE's native reader (OpenMS/OpenMS#10680), not the mzML. The spectrum counts in the table come from the PRIDE mzML (exporter output, with 5,536 and 6,276 precursors of charge 1, which the 8,000-spectrum selection excluded); counts from the `.d.zip` may differ.
- **Checksums:** the SHA256 of each frozen mzML is in `inputs.json` of the reproduction package (`prose-andes-reproduction.zip` at the README's commit).

### Database and search settings (as frozen in OpenMS/OpenMS#10364)

- **FASTA:** [ProteoBenchFASTA_MixedSpecies_HYE.fasta](https://archive.openms.de/openms/benchmarks/pride-benchmarks/lfq/QExactiveHF/ProteoBench_Module_2/ProteoBenchFASTA_MixedSpecies_HYE.fasta)
  (16,670,994 bytes, 31,889 targets, SHA256 `d9ac434d88492c10c8e9a587ee7dbc9480fa0995fa07a6ba35a7da8abf39aa25`).
  It is split by accession suffix (contaminants `Cont_` kept in all three), with one full-sequence reversed `DECOY_` per protein:

  | Database | Used for | Targets |
  |---|---|---:|
  | `hy` (human + yeast) | Velos, Lumos LFQ, Lumos TMT | 27,488 |
  | `hye` (human + yeast + E. coli) | HF-X, Astral | 31,889 |
  | `human` | TMTpro, timsTOF | 20,767 |

- **Digestion and modifications:** Trypsin/P, 2 missed cleavages, peptide length 7–40, fixed Carbamidomethyl (C), at most one Oxidation (M); TMT6plex or TMTpro fixed on the labelled groups.
- **Tolerances:** precursor 20 ppm (TMTpro 50 ppm); fragment 20 ppm, or 0.5 Da for the ion-trap CID groups (Velos, Lumos TMT).
- **Counting:** target PSMs at q ≤ 0.01 after **ProSE's in-process Percolator** (the default since OpenMS/OpenMS#10578), as users run ProSE.
  - Control, for the supplement: Percolator 3.09 as an external step (`-Y -U`, seeds 1/42/137), as in OpenMS/OpenMS#10364.
- **Entrapment, the only estimate of the true error rate here:**
  - **Velos:** natural entrapment, UPS1/yeast against all human proteins, r = 3.376.
  - **HF-X, Astral, TMTpro:** one shuffled, mass-matched entrapment protein per target, r = 1.
  - **timsTOF:** added later with the same `human` database (OpenMS/OpenMS#10639).
  - **Lumos:** only a whole-protein shuffle so far (OpenMS/OpenMS#10639).
  - For the paper all entrapment databases were rebuilt with DecoyDatabase, Lumos included; see section 3.2.
- **Comparison engines for the paper:** **Sage** and **MSFragger** on every dataset, **ANDES** on the Astral data.
  - Versions are fixed: Sage 0.14.7 and ANDES b7eaece (auto models), as in OpenMS/OpenMS#10364.
  - The MSFragger version is fixed at its first run and recorded here.
  - So far: Sage and ANDES on the 8,000-spectrum suite, MSFragger only in OpenMS/OpenMS#10403.

### Caveat for the paper

ProSE's defaults were tuned on these 20 files (the PRs listed in OpenMS/OpenMS#10364). ANDES was developed on the same Velos, Lumos and Astral studies.
A held-out set is therefore needed. The datasets in section 2 were not used for tuning the defaults and are that set.

## 2. Held-out datasets

These datasets were not used to tune ProSE's defaults; they are the held-out set of the paper (see "Caveat" in section 1). Every file is named below, so that everyone who uses this document tests the same files. The databases for each dataset are in section 3.3.

Numbers measured so far (in September 2026, PR [OpenMS/OpenMS#10261](https://github.com/OpenMS/OpenMS/pull/10261) and [OpenMS/OpenMS#10268](https://github.com/OpenMS/OpenMS/pull/10268), full runs) come from develop before the scoring changes OpenMS/OpenMS#10391, OpenMS/OpenMS#10397, OpenMS/OpenMS#10399 and the in-process Percolator (OpenMS/OpenMS#10578), and partly from other databases. They are context only and have to be re-measured.

### 2.1 Electron-based fragmentation (ETD, AI-ETD, EThcD, ETciD)

**[PXD011695](https://www.ebi.ac.uk/pride/archive/projects/PXD011695):** one mouse brain digest on an Orbitrap Elite with ion-trap MS2, one run per activation method (five runs). Search: 0.5 Da fragments, 20 ppm precursor.
The reference is the authors' OMSSA/COMPASS search (context only).

| Run | Raw | PSMs at 1% FDR so far, ProSE + Percolator (Swiss-Prot mouse, 17,277) | Authors |
|---|---|---:|---:|
| HCD | [nriley_Mouse_HCD.raw](https://ftp.pride.ebi.ac.uk/pride/data/archive/2019/05/PXD011695/nriley_Mouse_HCD.raw) (1.6 GB) | 65,519 | 63,686 |
| EThcD | [nriley_Mouse_EThcD.raw](https://ftp.pride.ebi.ac.uk/pride/data/archive/2019/05/PXD011695/nriley_Mouse_EThcD.raw) (618 MB) | 12,445 | 12,292 |
| ETciD | [nriley_Mouse_ETciD.raw](https://ftp.pride.ebi.ac.uk/pride/data/archive/2019/05/PXD011695/nriley_Mouse_ETciD.raw) (628 MB) | 11,373 | 10,436 |
| ETD (22,056 MS2) | [nriley_Mouse_ETD.raw](https://ftp.pride.ebi.ac.uk/pride/data/archive/2019/05/PXD011695/nriley_Mouse_ETD.raw) (614 MB) | 7,819 (OpenMS/OpenMS#10268 defaults) | 6,873 |
| AI-ETD | [nriley_Mouse_AI-ETD.raw](https://ftp.pride.ebi.ac.uk/pride/data/archive/2019/05/PXD011695/nriley_Mouse_AI-ETD.raw) (651 MB) | 10,890 (before OpenMS/OpenMS#10268) | 12,921 |

- **Database for the paper:** the authors' FASTA (UniProt mouse with TrEMBL and isoforms, 88,618 entries, section 3.3), so the new counts will differ from the Swiss-Prot ones above.
- **Native FDR on ETD 2+ precursors is weak:** ProSE's top hit is the authors' peptide for 2,427 of their 3,482 2+ PSMs. The native FDR keeps 159 of them, Percolator 2,740.

**[PXD065289](https://www.ebi.ac.uk/pride/archive/projects/PXD065289):** HEK293 (Expi293), trypsin, ETciD with Orbitrap MS2, high-pH fractions.
- **Instrument:** the file names (`ASND01_…`) suggest an Orbitrap Ascend; PRIDE lists an Exploris 480.
- **Selected files:** five of the 20 trypsin ETciD fractions, spread over the fractionation.
- **Reference:** the authors' FragPipe/MSBooster results, deposited as [fragpipe_msbooster.zip](https://ftp.pride.ebi.ac.uk/pride/data/archive/2026/03/PXD065289/fragpipe_msbooster.zip) (9.4 GB).
- **Earlier measurement:** OpenMS/OpenMS#10261 measured one ETciD run (file not recorded): 9,667 PSMs with z+1 ions against 6,154 with z ions (Percolator).

| Run | Raw |
|---|---|
| fraction 1 | [ASND01_NGL_YD1_241129_Expi_trypsin_ETciD_frac1_08.raw](https://ftp.pride.ebi.ac.uk/pride/data/archive/2026/03/PXD065289/ASND01_NGL_YD1_241129_Expi_trypsin_ETciD_frac1_08.raw) (930 MB) |
| fraction 5 | [ASND01_NGL_YD1_241129_Expi_trypsin_ETciD_frac5_14.raw](https://ftp.pride.ebi.ac.uk/pride/data/archive/2026/03/PXD065289/ASND01_NGL_YD1_241129_Expi_trypsin_ETciD_frac5_14.raw) (928 MB) |
| fraction 10 | [ASND01_NGL_YD1_241129_Expi_trypsin_ETciD_frac10_21.raw](https://ftp.pride.ebi.ac.uk/pride/data/archive/2026/03/PXD065289/ASND01_NGL_YD1_241129_Expi_trypsin_ETciD_frac10_21.raw) (927 MB) |
| fraction 15 | [ASND01_NGL_YD1_241129_Expi_trypsin_ETciD_frac15_28.raw](https://ftp.pride.ebi.ac.uk/pride/data/archive/2026/03/PXD065289/ASND01_NGL_YD1_241129_Expi_trypsin_ETciD_frac15_28.raw) (942 MB) |
| fraction 20 | [ASND01_NGL_YD1_241129_Expi_trypsin_ETciD_frac20_35.raw](https://ftp.pride.ebi.ac.uk/pride/data/archive/2026/03/PXD065289/ASND01_NGL_YD1_241129_Expi_trypsin_ETciD_frac20_35.raw) (976 MB) |

### 2.2 Orbitrap Astral

The Astral dataset of the paper is the ProteoBench Astral DDA module from [PXD070049](https://www.ebi.ac.uk/pride/archive/projects/PXD070049), already in section 1 (`astral_A2`, `astral_B1`, `astral_B3`).
- **Ground truth:** the HYE mix gives a known species composition and known fold changes.
- **Comparable:** the public ProteoBench submissions of other engines use the same files, and so does ANDES (`Condition_A_REP1`).
- **Results so far:**
  - OpenMS/OpenMS#10364 (8,000 MS2 per file): ProSE +20.5% PSMs over Sage, −13.6% against ANDES, which uses an Astral-specific model.
  - OpenMS/OpenMS#10638 (chimeric search, whole `Condition_A_REP1` run): 42,469 → 91,875 PSMs at q ≤ 1%. The rank-2 FDP alone is 2.23%.

**Optional supplementary set S1: natural entrapment from single-species runs.** The nine single-species runs of the same project and conditions (15 min, 50 ng), searched against the `hye` database:
- **Human runs:** every yeast or E. coli PSM is false.
- **Yeast and E. coli runs:** every PSM to another species is false.

| Run | Raw |
|---|---|
| Human 1–3 | [LFQ_Astral_DDA_15min_50ng_Human_01.raw](https://ftp.pride.ebi.ac.uk/pride/data/archive/2026/02/PXD070049/LFQ_Astral_DDA_15min_50ng_Human_01.raw) (2.3 GB), [_02.raw](https://ftp.pride.ebi.ac.uk/pride/data/archive/2026/02/PXD070049/LFQ_Astral_DDA_15min_50ng_Human_02.raw) (2.3 GB), [_03.raw](https://ftp.pride.ebi.ac.uk/pride/data/archive/2026/02/PXD070049/LFQ_Astral_DDA_15min_50ng_Human_03.raw) (2.3 GB) |
| Yeast 1–3 | [LFQ_Astral_DDA_15min_50ng_Yeast_01.raw](https://ftp.pride.ebi.ac.uk/pride/data/archive/2026/02/PXD070049/LFQ_Astral_DDA_15min_50ng_Yeast_01.raw) (2.1 GB), [_02.raw](https://ftp.pride.ebi.ac.uk/pride/data/archive/2026/02/PXD070049/LFQ_Astral_DDA_15min_50ng_Yeast_02.raw) (2.1 GB), [_03.raw](https://ftp.pride.ebi.ac.uk/pride/data/archive/2026/02/PXD070049/LFQ_Astral_DDA_15min_50ng_Yeast_03.raw) (2.1 GB) |
| E. coli 1–3 | [LFQ_Astral_DDA_15min_50ng_Ecoli_01.raw](https://ftp.pride.ebi.ac.uk/pride/data/archive/2026/02/PXD070049/LFQ_Astral_DDA_15min_50ng_Ecoli_01.raw) (971 MB), [_02.raw](https://ftp.pride.ebi.ac.uk/pride/data/archive/2026/02/PXD070049/LFQ_Astral_DDA_15min_50ng_Ecoli_02.raw) (966 MB), [_03.raw](https://ftp.pride.ebi.ac.uk/pride/data/archive/2026/02/PXD070049/LFQ_Astral_DDA_15min_50ng_Ecoli_03.raw) (966 MB) |

The short names `_02.raw` and `_03.raw` stand for the full file names `LFQ_Astral_DDA_15min_50ng_<Species>_02.raw` etc.

### 2.3 Low resolution (ion-trap MS2) and a high-resolution reference

In section 1: PXD001819 (Velos, ion-trap CID) and the Lumos ion-trap CID TMT runs. In addition:

**Percolator paper sets** (Käll et al., Nat Methods 2007; [data page](https://noble.gs.washington.edu/proj/percolator/data/)): LTQ, ion-trap CID, precursor charge unknown (±3 Da), MS2 format only (no raw files), no ground truth. The classic benchmark of Percolator, Crux/Tide and Comet.

| Set | File | ProSE so far (native / Percolator) |
|---|---|---|
| yeast-01 | [yeast-01.ms2.gz](https://noble.gs.washington.edu/proj/percolator/data/yeast-01.ms2.gz) (113 MB) | 7,388 / 9,954 |
| yeast-02 | [yeast-02.ms2.gz](https://noble.gs.washington.edu/proj/percolator/data/yeast-02.ms2.gz) (120 MB) | 8,146 / 10,652 |
| yeast-03 | [yeast-03.ms2.gz](https://noble.gs.washington.edu/proj/percolator/data/yeast-03.ms2.gz) (115 MB) | 7,232 / 9,906 |
| yeast-04 | [yeast-04.ms2.gz](https://noble.gs.washington.edu/proj/percolator/data/yeast-04.ms2.gz) (116 MB) | 7,249 / 9,617 |
| yeast, chymotrypsin | [chymotrypsin.ms2.gz](https://noble.gs.washington.edu/proj/percolator/data/chymotrypsin.ms2.gz) (186 MB) | 1,254 / 2,036 |
| worm-01, worm-02 | `worm-01.ms2` and `worm-02.ms2` from [worm.ms2.tar.gz](https://noble.gs.washington.edu/proj/percolator/data/worm.ms2.tar.gz) (1.5 GB, SHA256 `b8366aad…`; it holds worm-01 to worm-12, only the first two are used) | 8,604 / 9,903 and 5,655 / 6,769 |

**[PXD042233](https://www.ebi.ac.uk/pride/archive/projects/PXD042233)** (Webel et al., Sci Data 2024, HeLa QC runs of many instruments): the only two Orbitrap Fusion Lumos runs of the project with ion-trap CID.
- **How they were found:** the instrument method in the raw-file headers of all 226 Lumos runs was checked. Both runs have CID 35% with ion-trap detection, a 144-minute method and a 1.3 Th isolation window.
- **Other runs:** all other Lumos runs are HCD (detected in the ion trap or the Orbitrap), and 9 have no readable method.
- **Earlier measurement:** OpenMS/OpenMS#10261 measured one Lumos CID HeLa run (21,501 / 28,173 PSMs; file not recorded).

| Run | Raw |
|---|---|
| Lumos CID 1 | [2015_12_21_12_42_Orbitrap-Fusion-Lumos_FSN20115.raw](https://ftp.pride.ebi.ac.uk/pride/data/archive/2023/12/PXD042233/2015_12_21_12_42_Orbitrap-Fusion-Lumos_FSN20115.raw) (2.1 GB) |
| Lumos CID 2 | [2015_12_22_00_06_Orbitrap-Fusion-Lumos_FSN20115.raw](https://ftp.pride.ebi.ac.uk/pride/data/archive/2023/12/PXD042233/2015_12_22_00_06_Orbitrap-Fusion-Lumos_FSN20115.raw) (2.1 GB) |

**ProteomeTools** ([PXD004732](https://www.ebi.ac.uk/pride/archive/projects/PXD004732), Zolg et al., Nat Methods 2017): synthetic tryptic human peptides, pools of about 1,000, on an Orbitrap Fusion Lumos.
- **Method:** the `2xIT_2xHCD` method fragments the same precursors four times, as the raw-file header shows: CID 35% with ion-trap readout, HCD 28% in the ion trap, and HCD 20% and 23% in the Orbitrap.
- **Why it is useful:** low- and high-resolution spectra of the same peptides, with the peptide sequence as ground truth.
- **Selected files:** three tryptic pools from the first set.
- **MaxQuant results:** each pool has the authors' MaxQuant results (zip next to the raw file).

| Pool | Raw | MaxQuant results |
|---|---|---|
| TUM_first_pool_1 | [01625b_GA1-TUM_first_pool_1_01_01-2xIT_2xHCD-1h-R1.raw](https://ftp.pride.ebi.ac.uk/pride/data/archive/2017/02/PXD004732/01625b_GA1-TUM_first_pool_1_01_01-2xIT_2xHCD-1h-R1.raw) (835 MB) | [TUM_first_pool_1_01_01_2xIT_2xHCD-1h-R1-tryptic.zip](https://ftp.pride.ebi.ac.uk/pride/data/archive/2017/02/PXD004732/TUM_first_pool_1_01_01_2xIT_2xHCD-1h-R1-tryptic.zip) |
| TUM_first_pool_30 | [01625b_GF4-TUM_first_pool_30_01_01-2xIT_2xHCD-1h-R1.raw](https://ftp.pride.ebi.ac.uk/pride/data/archive/2017/02/PXD004732/01625b_GF4-TUM_first_pool_30_01_01-2xIT_2xHCD-1h-R1.raw) (892 MB) | [TUM_first_pool_30_01_01_2xIT_2xHCD-1h-R1-tryptic.zip](https://ftp.pride.ebi.ac.uk/pride/data/archive/2017/02/PXD004732/TUM_first_pool_30_01_01_2xIT_2xHCD-1h-R1-tryptic.zip) |
| TUM_first_pool_61 | [01650b_BC3-TUM_first_pool_61_01_01-2xIT_2xHCD-1h-R2.raw](https://ftp.pride.ebi.ac.uk/pride/data/archive/2017/02/PXD004732/01650b_BC3-TUM_first_pool_61_01_01-2xIT_2xHCD-1h-R2.raw) (925 MB) | [TUM_first_pool_61_01_01_2xIT_2xHCD-1h-R2-tryptic.zip](https://ftp.pride.ebi.ac.uk/pride/data/archive/2017/02/PXD004732/TUM_first_pool_61_01_01_2xIT_2xHCD-1h-R2-tryptic.zip) |

- **Database:** the Swiss-Prot human target-decoy database of section 3.3 (`pxd058436_td.fasta`, UniProt 2026_01).
- **Ground truth, still to obtain:** a PSM is correct if its peptide was synthesized in the pool. The pool peptide lists are not on PRIDE; the MaxQuant zips only hold what MaxQuant identified.

**iPRG2015** ([PXD010981](https://www.ebi.ac.uk/pride/archive/projects/PXD010981), MassIVE MSV000079843) is not low-resolution: Q Exactive HCD, MS2 at 17,500.
- **Role in the paper:** a high-resolution reference with an external comparison (MS-GF+ on the same three runs in the OpenMS archive).
- **Sample:** 200 ng yeast with spiked proteins.
- **Raw file names:** they spell two of the runs with a hyphen (`sample1-A`, `sample4-A`).

| Run | mzML | raw | ProSE so far (native / Percolator) |
|---|---|---|---|
| 1A | [JD_06232014_sample1_A.mzML](https://ftp.pride.ebi.ac.uk/pride/data/archive/2018/09/PXD010981/JD_06232014_sample1_A.mzML) (1.4 GB) | [JD_06232014_sample1-A.raw](https://ftp.pride.ebi.ac.uk/pride/data/archive/2018/09/PXD010981/JD_06232014_sample1-A.raw) (1.1 GB) | 20,046 / 20,201 |
| 2A | [JD_06232014_sample2_A.mzML](https://ftp.pride.ebi.ac.uk/pride/data/archive/2018/09/PXD010981/JD_06232014_sample2_A.mzML) (1.4 GB) | [JD_06232014_sample2_A.raw](https://ftp.pride.ebi.ac.uk/pride/data/archive/2018/09/PXD010981/JD_06232014_sample2_A.raw) (1.1 GB) | 18,476 / 18,688 |
| 4A | [JD_06232014_sample4_A.mzML](https://ftp.pride.ebi.ac.uk/pride/data/archive/2018/09/PXD010981/JD_06232014_sample4_A.mzML) (1.4 GB) | [JD_06232014_sample4-A.raw](https://ftp.pride.ebi.ac.uk/pride/data/archive/2018/09/PXD010981/JD_06232014_sample4-A.raw) (1.1 GB) | 17,887 / 18,085 |

### 2.4 Immunopeptidomics (HLA class I and II, unspecific cleavage)

The two datasets come from the same donors (IDs `DN02`…`DN17`; inferred from the IDs, not confirmed) and the same tissues on two instruments. All technical replicates of each sample are searched, because the published references count unique peptides per sample with the replicates pooled.

**[PXD058436](https://www.ebi.ac.uk/pride/archive/projects/PXD058436): MHCquant2 benign tissues** (Scheid et al., Genome Biol 2025)
- **Data:** timsTOF Pro 2, DDA-PASEF, all 633 runs of the project, 12 donors.
- **Reference results on PRIDE:** MHCquant2, FragPipe and PEAKS, per sample.
- **Input:** the Bruker `.d` (unpack the `.d.tar.gz`), as for timsTOF in section 1. The mzML is listed as well.
- **ProSE so far** (single replicates, no comparison with another engine):
  - DN08_Brain_classI_techRep1: 2,011 PSMs at 1% FDR (67,944 MS2).
  - DN09_Pancreas_classII_techRep1: 8,399 PSMs (120,442 MS2) (OpenMS/OpenMS#10639).
- **Memory:** an unspecific human index does not fit into 12.5 GiB. The search needs `low_memory` or `database:mass_slices` (OpenMS/OpenMS#10639).

**[PXD019643](https://www.ebi.ac.uk/pride/archive/projects/PXD019643): HLA Ligand Atlas** (Marcu et al., J Immunother Cancer 2021)
- **Data:** Orbitrap Fusion Lumos, CID. Class I W6/32, 400–650 m/z; class II Tü39 + L243, 400–1000 m/z.
- **Reference results on PRIDE:** MHCquant v1 (Comet + Percolator).
- **ProSE so far:** OpenMS/OpenMS#9975 (PeptDeep rescoring), six class I files that are not recorded. 9,764 → 10,893 PSMs (+11.6%).

PXD058436, all technical replicates of nine samples (30 runs). mzML from archive.openms.de (same files as on PRIDE); Bruker `.d.tar.gz` from PRIDE:

| Sample | Class, yield | Run | mzML | Bruker .d |
|---|---|---|---|---|
| DN12_Liver_classI | I, high | `DN12_Liver_classI_techRep1` | [mzML](https://archive.openms.de/openms/testfiles/id_bruker/classI/high/DN12_Liver_classI_techRep1.mzML) (2.2 GB) | [d.tar.gz](https://ftp.pride.ebi.ac.uk/pride/data/archive/2025/08/PXD058436/DN12_Liver_classI_techRep1.d.tar.gz) (3.1 GB) |
| DN12_Liver_classI | I, high | `DN12_Liver_classI_techRep2` | [mzML](https://archive.openms.de/openms/testfiles/id_bruker/classI/high/DN12_Liver_classI_techRep2.mzML) (2.1 GB) | [d.tar.gz](https://ftp.pride.ebi.ac.uk/pride/data/archive/2025/08/PXD058436/DN12_Liver_classI_techRep2.d.tar.gz) (3.1 GB) |
| DN12_Liver_classI | I, high | `DN12_Liver_classI_techRep3` | [mzML](https://archive.openms.de/openms/testfiles/id_bruker/classI/high/DN12_Liver_classI_techRep3.mzML) (2.1 GB) | [d.tar.gz](https://ftp.pride.ebi.ac.uk/pride/data/archive/2025/08/PXD058436/DN12_Liver_classI_techRep3.d.tar.gz) (3.1 GB) |
| DN02_Spleen_classI | I, high | `DN02_Spleen_classI_techRep1` | [mzML](https://archive.openms.de/openms/testfiles/id_bruker/classI/high/DN02_Spleen_classI_techRep1.mzML) (2.0 GB) | [d.tar.gz](https://ftp.pride.ebi.ac.uk/pride/data/archive/2025/08/PXD058436/DN02_Spleen_classI_techRep1.d.tar.gz) (2.7 GB) |
| DN02_Spleen_classI | I, high | `DN02_Spleen_classI_techRep2` | [mzML](https://archive.openms.de/openms/testfiles/id_bruker/classI/high/DN02_Spleen_classI_techRep2.mzML) (2.1 GB) | [d.tar.gz](https://ftp.pride.ebi.ac.uk/pride/data/archive/2025/08/PXD058436/DN02_Spleen_classI_techRep2.d.tar.gz) (2.8 GB) |
| DN02_Spleen_classI | I, high | `DN02_Spleen_classI_techRep3` | [mzML](https://archive.openms.de/openms/testfiles/id_bruker/classI/high/DN02_Spleen_classI_techRep3.mzML) (2.0 GB) | [d.tar.gz](https://ftp.pride.ebi.ac.uk/pride/data/archive/2025/08/PXD058436/DN02_Spleen_classI_techRep3.d.tar.gz) (2.7 GB) |
| DN13_Corpus_classI | I, high | `DN13_Corpus_classI_techRep1` | [mzML](https://archive.openms.de/openms/testfiles/id_bruker/classI/high/DN13_Corpus_classI_techRep1.mzML) (2.1 GB) | [d.tar.gz](https://ftp.pride.ebi.ac.uk/pride/data/archive/2025/08/PXD058436/DN13_Corpus_classI_techRep1.d.tar.gz) (2.6 GB) |
| DN13_Corpus_classI | I, high | `DN13_Corpus_classI_techRep2` | [mzML](https://archive.openms.de/openms/testfiles/id_bruker/classI/high/DN13_Corpus_classI_techRep2.mzML) (2.1 GB) | [d.tar.gz](https://ftp.pride.ebi.ac.uk/pride/data/archive/2025/08/PXD058436/DN13_Corpus_classI_techRep2.d.tar.gz) (2.6 GB) |
| DN13_Corpus_classI | I, high | `DN13_Corpus_classI_techRep3` | [mzML](https://archive.openms.de/openms/testfiles/id_bruker/classI/high/DN13_Corpus_classI_techRep3.mzML) (2.1 GB) | [d.tar.gz](https://ftp.pride.ebi.ac.uk/pride/data/archive/2025/08/PXD058436/DN13_Corpus_classI_techRep3.d.tar.gz) (2.6 GB) |
| DN09_Pancreas_classI | I, middle | `DN09_Pancreas_classI_techRep1` | [mzML](https://archive.openms.de/openms/testfiles/id_bruker/classI/middle/DN09_Pancreas_classI_techRep1.mzML) (1.6 GB) | [d.tar.gz](https://ftp.pride.ebi.ac.uk/pride/data/archive/2025/08/PXD058436/DN09_Pancreas_classI_techRep1.d.tar.gz) (1.8 GB) |
| DN09_Pancreas_classI | I, middle | `DN09_Pancreas_classI_techRep2` | [mzML](https://archive.openms.de/openms/testfiles/id_bruker/classI/middle/DN09_Pancreas_classI_techRep2.mzML) (1.6 GB) | [d.tar.gz](https://ftp.pride.ebi.ac.uk/pride/data/archive/2025/08/PXD058436/DN09_Pancreas_classI_techRep2.d.tar.gz) (1.9 GB) |
| DN09_Pancreas_classI | I, middle | `DN09_Pancreas_classI_techRep3` | [mzML](https://archive.openms.de/openms/testfiles/id_bruker/classI/middle/DN09_Pancreas_classI_techRep3.mzML) (1.6 GB) | [d.tar.gz](https://ftp.pride.ebi.ac.uk/pride/data/archive/2025/08/PXD058436/DN09_Pancreas_classI_techRep3.d.tar.gz) (2.0 GB) |
| DN08_Brain_classI | I, middle | `DN08_Brain_classI_techRep1` | [mzML](https://archive.openms.de/openms/testfiles/id_bruker/classI/middle/DN08_Brain_classI_techRep1.mzML) (1.3 GB) | [d.tar.gz](https://ftp.pride.ebi.ac.uk/pride/data/archive/2025/08/PXD058436/DN08_Brain_classI_techRep1.d.tar.gz) (1.4 GB) |
| DN08_Brain_classI | I, middle | `DN08_Brain_classI_techRep2` | [mzML](https://archive.openms.de/openms/testfiles/id_bruker/classI/middle/DN08_Brain_classI_techRep2.mzML) (1.4 GB) | [d.tar.gz](https://ftp.pride.ebi.ac.uk/pride/data/archive/2025/08/PXD058436/DN08_Brain_classI_techRep2.d.tar.gz) (1.4 GB) |
| DN08_Brain_classI | I, middle | `DN08_Brain_classI_techRep3` | [mzML](https://archive.openms.de/openms/testfiles/id_bruker/classI/middle/DN08_Brain_classI_techRep3.mzML) (1.4 GB) | [d.tar.gz](https://ftp.pride.ebi.ac.uk/pride/data/archive/2025/08/PXD058436/DN08_Brain_classI_techRep3.d.tar.gz) (1.4 GB) |
| DN08_Brain_classI | I, middle | `DN08_Brain_classI_techRep4` | [mzML](https://archive.openms.de/openms/testfiles/id_bruker/classI/middle/DN08_Brain_classI_techRep4.mzML) (1.7 GB) | [d.tar.gz](https://ftp.pride.ebi.ac.uk/pride/data/archive/2025/08/PXD058436/DN08_Brain_classI_techRep4.d.tar.gz) (2.4 GB) |
| DN08_Brain_classI | I, middle | `DN08_Brain_classI_techRep5` | [mzML](https://archive.openms.de/openms/testfiles/id_bruker/classI/middle/DN08_Brain_classI_techRep5.mzML) (1.4 GB) | [d.tar.gz](https://ftp.pride.ebi.ac.uk/pride/data/archive/2025/08/PXD058436/DN08_Brain_classI_techRep5.d.tar.gz) (1.5 GB) |
| DN08_Brain_classI | I, middle | `DN08_Brain_classI_techRep6` | [mzML](https://archive.openms.de/openms/testfiles/id_bruker/classI/middle/DN08_Brain_classI_techRep6.mzML) (1.2 GB) | [d.tar.gz](https://ftp.pride.ebi.ac.uk/pride/data/archive/2025/08/PXD058436/DN08_Brain_classI_techRep6.d.tar.gz) (1.1 GB) |
| DN12_Liver_classII | II, middle | `DN12_Liver_classII_techRep1` | [mzML](https://archive.openms.de/openms/testfiles/id_bruker/classII/middle/DN12_Liver_classII_techRep1.mzML) (2.1 GB) | [d.tar.gz](https://ftp.pride.ebi.ac.uk/pride/data/archive/2025/08/PXD058436/DN12_Liver_classII_techRep1.d.tar.gz) (2.7 GB) |
| DN12_Liver_classII | II, middle | `DN12_Liver_classII_techRep2` | [mzML](https://archive.openms.de/openms/testfiles/id_bruker/classII/middle/DN12_Liver_classII_techRep2.mzML) (2.1 GB) | [d.tar.gz](https://ftp.pride.ebi.ac.uk/pride/data/archive/2025/08/PXD058436/DN12_Liver_classII_techRep2.d.tar.gz) (2.7 GB) |
| DN12_Liver_classII | II, middle | `DN12_Liver_classII_techRep3` | [mzML](https://archive.openms.de/openms/testfiles/id_bruker/classII/middle/DN12_Liver_classII_techRep3.mzML) (2.1 GB) | [d.tar.gz](https://ftp.pride.ebi.ac.uk/pride/data/archive/2025/08/PXD058436/DN12_Liver_classII_techRep3.d.tar.gz) (2.7 GB) |
| DN09_Pancreas_classII | II, middle | `DN09_Pancreas_classII_techRep1` | [mzML](https://archive.openms.de/openms/testfiles/id_bruker/classII/middle/DN09_Pancreas_classII_techRep1.mzML) (2.0 GB) | [d.tar.gz](https://ftp.pride.ebi.ac.uk/pride/data/archive/2025/08/PXD058436/DN09_Pancreas_classII_techRep1.d.tar.gz) (2.4 GB) |
| DN09_Pancreas_classII | II, middle | `DN09_Pancreas_classII_techRep2` | [mzML](https://archive.openms.de/openms/testfiles/id_bruker/classII/middle/DN09_Pancreas_classII_techRep2.mzML) (2.0 GB) | [d.tar.gz](https://ftp.pride.ebi.ac.uk/pride/data/archive/2025/08/PXD058436/DN09_Pancreas_classII_techRep2.d.tar.gz) (2.4 GB) |
| DN09_Pancreas_classII | II, middle | `DN09_Pancreas_classII_techRep3` | [mzML](https://archive.openms.de/openms/testfiles/id_bruker/classII/middle/DN09_Pancreas_classII_techRep3.mzML) (2.0 GB) | [d.tar.gz](https://ftp.pride.ebi.ac.uk/pride/data/archive/2025/08/PXD058436/DN09_Pancreas_classII_techRep3.d.tar.gz) (2.4 GB) |
| DN08_Spleen_classII | II, high | `DN08_Spleen_classII_techRep1` | [mzML](https://archive.openms.de/openms/testfiles/id_bruker/classII/high/DN08_Spleen_classII_techRep1.mzML) (1.9 GB) | [d.tar.gz](https://ftp.pride.ebi.ac.uk/pride/data/archive/2025/08/PXD058436/DN08_Spleen_classII_techRep1.d.tar.gz) (2.3 GB) |
| DN08_Spleen_classII | II, high | `DN08_Spleen_classII_techRep2` | [mzML](https://archive.openms.de/openms/testfiles/id_bruker/classII/high/DN08_Spleen_classII_techRep2.mzML) (2.0 GB) | [d.tar.gz](https://ftp.pride.ebi.ac.uk/pride/data/archive/2025/08/PXD058436/DN08_Spleen_classII_techRep2.d.tar.gz) (2.3 GB) |
| DN08_Spleen_classII | II, high | `DN08_Spleen_classII_techRep3` | [mzML](https://archive.openms.de/openms/testfiles/id_bruker/classII/high/DN08_Spleen_classII_techRep3.mzML) (2.0 GB) | [d.tar.gz](https://ftp.pride.ebi.ac.uk/pride/data/archive/2025/08/PXD058436/DN08_Spleen_classII_techRep3.d.tar.gz) (2.3 GB) |
| DN13_Corpus_classII | II, high | `DN13_Corpus_classII_techRep1` | [mzML](https://archive.openms.de/openms/testfiles/id_bruker/classII/high/DN13_Corpus_classII_techRep1.mzML) (2.1 GB) | [d.tar.gz](https://ftp.pride.ebi.ac.uk/pride/data/archive/2025/08/PXD058436/DN13_Corpus_classII_techRep1.d.tar.gz) (2.6 GB) |
| DN13_Corpus_classII | II, high | `DN13_Corpus_classII_techRep2` | [mzML](https://archive.openms.de/openms/testfiles/id_bruker/classII/high/DN13_Corpus_classII_techRep2.mzML) (2.1 GB) | [d.tar.gz](https://ftp.pride.ebi.ac.uk/pride/data/archive/2025/08/PXD058436/DN13_Corpus_classII_techRep2.d.tar.gz) (2.6 GB) |
| DN13_Corpus_classII | II, high | `DN13_Corpus_classII_techRep3` | [mzML](https://archive.openms.de/openms/testfiles/id_bruker/classII/high/DN13_Corpus_classII_techRep3.mzML) (2.1 GB) | [d.tar.gz](https://ftp.pride.ebi.ac.uk/pride/data/archive/2025/08/PXD058436/DN13_Corpus_classII_techRep3.d.tar.gz) (2.6 GB) |

PXD019643, all three DDA replicates of six samples (18 runs), from PRIDE:

| Sample | Class | Run | mzML | raw |
|---|---|---|---|---|
| DN12_Liver_W6-32 | I | `170413_AM_AUT01-DN12_Liver_W6-32_10_DDA_1_400-650mz_msms17_standard` | [mzML](https://ftp.pride.ebi.ac.uk/pride/data/archive/2021/04/PXD019643/170413_AM_AUT01-DN12_Liver_W6-32_10_DDA_1_400-650mz_msms17_standard.mzML) (248 MB) | [raw](https://ftp.pride.ebi.ac.uk/pride/data/archive/2021/04/PXD019643/170413_AM_AUT01-DN12_Liver_W6-32_10_DDA_1_400-650mz_msms17_standard.raw) (478 MB) |
| DN12_Liver_W6-32 | I | `170413_AM_AUT01-DN12_Liver_W6-32_10_DDA_2_400-650mz_msms18_standard` | [mzML](https://ftp.pride.ebi.ac.uk/pride/data/archive/2021/04/PXD019643/170413_AM_AUT01-DN12_Liver_W6-32_10_DDA_2_400-650mz_msms18_standard.mzML) (250 MB) | [raw](https://ftp.pride.ebi.ac.uk/pride/data/archive/2021/04/PXD019643/170413_AM_AUT01-DN12_Liver_W6-32_10_DDA_2_400-650mz_msms18_standard.raw) (481 MB) |
| DN12_Liver_W6-32 | I | `170413_AM_AUT01-DN12_Liver_W6-32_10_DDA_3_400-650mz_msms19_standard` | [mzML](https://ftp.pride.ebi.ac.uk/pride/data/archive/2021/04/PXD019643/170413_AM_AUT01-DN12_Liver_W6-32_10_DDA_3_400-650mz_msms19_standard.mzML) (250 MB) | [raw](https://ftp.pride.ebi.ac.uk/pride/data/archive/2021/04/PXD019643/170413_AM_AUT01-DN12_Liver_W6-32_10_DDA_3_400-650mz_msms19_standard.raw) (480 MB) |
| DN12_Liver_Tue39L243 | II | `170413_AM_AUT01-DN12_Liver_Tue39L243_10_DDA_1_400-1000mz_msms24_standard` | [mzML](https://ftp.pride.ebi.ac.uk/pride/data/archive/2021/04/PXD019643/170413_AM_AUT01-DN12_Liver_Tue39L243_10_DDA_1_400-1000mz_msms24_standard.mzML) (436 MB) | [raw](https://ftp.pride.ebi.ac.uk/pride/data/archive/2021/04/PXD019643/170413_AM_AUT01-DN12_Liver_Tue39L243_10_DDA_1_400-1000mz_msms24_standard.raw) (765 MB) |
| DN12_Liver_Tue39L243 | II | `170413_AM_AUT01-DN12_Liver_Tue39L243_10_DDA_2_400-1000mz_msms25_standard` | [mzML](https://ftp.pride.ebi.ac.uk/pride/data/archive/2021/04/PXD019643/170413_AM_AUT01-DN12_Liver_Tue39L243_10_DDA_2_400-1000mz_msms25_standard.mzML) (429 MB) | [raw](https://ftp.pride.ebi.ac.uk/pride/data/archive/2021/04/PXD019643/170413_AM_AUT01-DN12_Liver_Tue39L243_10_DDA_2_400-1000mz_msms25_standard.raw) (748 MB) |
| DN12_Liver_Tue39L243 | II | `170413_AM_AUT01-DN12_Liver_Tue39L243_10_DDA_3_400-1000mz_msms26_standard` | [mzML](https://ftp.pride.ebi.ac.uk/pride/data/archive/2021/04/PXD019643/170413_AM_AUT01-DN12_Liver_Tue39L243_10_DDA_3_400-1000mz_msms26_standard.mzML) (429 MB) | [raw](https://ftp.pride.ebi.ac.uk/pride/data/archive/2021/04/PXD019643/170413_AM_AUT01-DN12_Liver_Tue39L243_10_DDA_3_400-1000mz_msms26_standard.raw) (749 MB) |
| DN09_Pancreas_W6-32 | I | `180921_AM_AUT01-DN09_Pancreas_W6-32_10_DDA_1_400-650mz_msms10_standard` | [mzML](https://ftp.pride.ebi.ac.uk/pride/data/archive/2021/04/PXD019643/180921_AM_AUT01-DN09_Pancreas_W6-32_10_DDA_1_400-650mz_msms10_standard.mzML) (217 MB) | [raw](https://ftp.pride.ebi.ac.uk/pride/data/archive/2021/04/PXD019643/180921_AM_AUT01-DN09_Pancreas_W6-32_10_DDA_1_400-650mz_msms10_standard.raw) (493 MB) |
| DN09_Pancreas_W6-32 | I | `180921_AM_AUT01-DN09_Pancreas_W6-32_10_DDA_2_400-650mz_msms11_standard` | [mzML](https://ftp.pride.ebi.ac.uk/pride/data/archive/2021/04/PXD019643/180921_AM_AUT01-DN09_Pancreas_W6-32_10_DDA_2_400-650mz_msms11_standard.mzML) (219 MB) | [raw](https://ftp.pride.ebi.ac.uk/pride/data/archive/2021/04/PXD019643/180921_AM_AUT01-DN09_Pancreas_W6-32_10_DDA_2_400-650mz_msms11_standard.raw) (500 MB) |
| DN09_Pancreas_W6-32 | I | `180921_AM_AUT01-DN09_Pancreas_W6-32_10_DDA_3_400-650mz_msms12_standard` | [mzML](https://ftp.pride.ebi.ac.uk/pride/data/archive/2021/04/PXD019643/180921_AM_AUT01-DN09_Pancreas_W6-32_10_DDA_3_400-650mz_msms12_standard.mzML) (218 MB) | [raw](https://ftp.pride.ebi.ac.uk/pride/data/archive/2021/04/PXD019643/180921_AM_AUT01-DN09_Pancreas_W6-32_10_DDA_3_400-650mz_msms12_standard.raw) (500 MB) |
| DN09_Pancreas_Tue39L243 | II | `180921_AM_AUT01-DN09_Pancreas_Tue39L243_10_DDA_1_400-1000mz_msms17_standard` | [mzML](https://ftp.pride.ebi.ac.uk/pride/data/archive/2021/04/PXD019643/180921_AM_AUT01-DN09_Pancreas_Tue39L243_10_DDA_1_400-1000mz_msms17_standard.mzML) (296 MB) | [raw](https://ftp.pride.ebi.ac.uk/pride/data/archive/2021/04/PXD019643/180921_AM_AUT01-DN09_Pancreas_Tue39L243_10_DDA_1_400-1000mz_msms17_standard.raw) (592 MB) |
| DN09_Pancreas_Tue39L243 | II | `180921_AM_AUT01-DN09_Pancreas_Tue39L243_10_DDA_2_400-1000mz_msms18_standard` | [mzML](https://ftp.pride.ebi.ac.uk/pride/data/archive/2021/04/PXD019643/180921_AM_AUT01-DN09_Pancreas_Tue39L243_10_DDA_2_400-1000mz_msms18_standard.mzML) (300 MB) | [raw](https://ftp.pride.ebi.ac.uk/pride/data/archive/2021/04/PXD019643/180921_AM_AUT01-DN09_Pancreas_Tue39L243_10_DDA_2_400-1000mz_msms18_standard.raw) (596 MB) |
| DN09_Pancreas_Tue39L243 | II | `180921_AM_AUT01-DN09_Pancreas_Tue39L243_10_DDA_3_400-1000mz_msms19_standard` | [mzML](https://ftp.pride.ebi.ac.uk/pride/data/archive/2021/04/PXD019643/180921_AM_AUT01-DN09_Pancreas_Tue39L243_10_DDA_3_400-1000mz_msms19_standard.mzML) (297 MB) | [raw](https://ftp.pride.ebi.ac.uk/pride/data/archive/2021/04/PXD019643/180921_AM_AUT01-DN09_Pancreas_Tue39L243_10_DDA_3_400-1000mz_msms19_standard.raw) (590 MB) |
| DN08_Spleen_W6-32 | I | `160325_DK_AUT01-DN08_Spleen_W6-32_20_DDA_1_400-650mz_msms1_SpeedVac` | [mzML](https://ftp.pride.ebi.ac.uk/pride/data/archive/2021/04/PXD019643/160325_DK_AUT01-DN08_Spleen_W6-32_20_DDA_1_400-650mz_msms1_SpeedVac.mzML) (320 MB) | [raw](https://ftp.pride.ebi.ac.uk/pride/data/archive/2021/04/PXD019643/160325_DK_AUT01-DN08_Spleen_W6-32_20_DDA_1_400-650mz_msms1_SpeedVac.raw) (603 MB) |
| DN08_Spleen_W6-32 | I | `160325_DK_AUT01-DN08_Spleen_W6-32_20_DDA_2_400-650mz_msms3_SpeedVac` | [mzML](https://ftp.pride.ebi.ac.uk/pride/data/archive/2021/04/PXD019643/160325_DK_AUT01-DN08_Spleen_W6-32_20_DDA_2_400-650mz_msms3_SpeedVac.mzML) (323 MB) | [raw](https://ftp.pride.ebi.ac.uk/pride/data/archive/2021/04/PXD019643/160325_DK_AUT01-DN08_Spleen_W6-32_20_DDA_2_400-650mz_msms3_SpeedVac.raw) (603 MB) |
| DN08_Spleen_W6-32 | I | `160325_DK_AUT01-DN08_Spleen_W6-32_20_DDA_3_400-650mz_msms5_SpeedVac` | [mzML](https://ftp.pride.ebi.ac.uk/pride/data/archive/2021/04/PXD019643/160325_DK_AUT01-DN08_Spleen_W6-32_20_DDA_3_400-650mz_msms5_SpeedVac.mzML) (320 MB) | [raw](https://ftp.pride.ebi.ac.uk/pride/data/archive/2021/04/PXD019643/160325_DK_AUT01-DN08_Spleen_W6-32_20_DDA_3_400-650mz_msms5_SpeedVac.raw) (603 MB) |
| DN08_Spleen_Tue39L243 | II | `160325_DK_AUT01-DN08_Spleen_Tue39L243_20_DDA_1_400-1000mz_msms11_SpeedVac` | [mzML](https://ftp.pride.ebi.ac.uk/pride/data/archive/2021/04/PXD019643/160325_DK_AUT01-DN08_Spleen_Tue39L243_20_DDA_1_400-1000mz_msms11_SpeedVac.mzML) (479 MB) | [raw](https://ftp.pride.ebi.ac.uk/pride/data/archive/2021/04/PXD019643/160325_DK_AUT01-DN08_Spleen_Tue39L243_20_DDA_1_400-1000mz_msms11_SpeedVac.raw) (826 MB) |
| DN08_Spleen_Tue39L243 | II | `160325_DK_AUT01-DN08_Spleen_Tue39L243_20_DDA_2_400-1000mz_msms13_SpeedVac` | [mzML](https://ftp.pride.ebi.ac.uk/pride/data/archive/2021/04/PXD019643/160325_DK_AUT01-DN08_Spleen_Tue39L243_20_DDA_2_400-1000mz_msms13_SpeedVac.mzML) (479 MB) | [raw](https://ftp.pride.ebi.ac.uk/pride/data/archive/2021/04/PXD019643/160325_DK_AUT01-DN08_Spleen_Tue39L243_20_DDA_2_400-1000mz_msms13_SpeedVac.raw) (828 MB) |
| DN08_Spleen_Tue39L243 | II | `160325_DK_AUT01-DN08_Spleen_Tue39L243_20_DDA_3_400-1000mz_msms15_SpeedVac` | [mzML](https://ftp.pride.ebi.ac.uk/pride/data/archive/2021/04/PXD019643/160325_DK_AUT01-DN08_Spleen_Tue39L243_20_DDA_3_400-1000mz_msms15_SpeedVac.mzML) (474 MB) | [raw](https://ftp.pride.ebi.ac.uk/pride/data/archive/2021/04/PXD019643/160325_DK_AUT01-DN08_Spleen_Tue39L243_20_DDA_3_400-1000mz_msms15_SpeedVac.raw) (819 MB) |

**Comparison with the published references:**
- **Counting:** unique peptides at 1% peptide-level FDR per sample, over all technical replicates. MHCquant2 settings: 20 ppm; z 1–4; 8–14 aa for class I.
  - PXD058436: MHCquant2 reports, for example, 18,472 peptides for DN12_Liver_classI.
  - PXD019643: MHCquant v1 reports, for example, 4,418 sequences for DN12 Liver HLA-I.
- **Database:** MHCquant2's Swiss-Prot of 2020-10-14 is not available. ProSE uses `human_sp.fasta` from archive.openms.de, which is Swiss-Prot human of UniProt release 2026_01 (section 3.3). Only 0.03% of the published peptides are missing from it (measured in section 3.3), so the difference hardly matters, but the comparison has to state it.
- **FDR control:** target-decoy only, no entrapment (section 3.3).
- **Possible ground truth:** PXD058436 also has six synthetic peptide mix runs (`*_Synpepmix*_classI_*.raw`, Thermo), which have not been examined yet.

## 3. Databases and entrapment

Status 2026-10-23: **all databases are built with DecoyDatabase**.
- **Main benchmark:** twelve databases (section 3.2).
- **Held-out datasets:** twenty-one databases (section 3.3). Twenty come from the FASTAs the original authors deposited. PXD058436 and ProteomeTools use `human_sp.fasta` from archive.openms.de.

### 3.1 Tools

Since 2026-10-23, PR [OpenMS/OpenMS#10629](https://github.com/OpenMS/OpenMS/pull/10629) is merged into develop. It adds two tools:

- **`DecoyDatabase -entrapment_ratio N`:** writes N shuffled entrapment copies of each target protein (prefix `ENTRAP_`), each with its own decoys.
  - Each copy is shuffled peptide by peptide. The C-terminal residue and K, R and P stay in place, and residues are permuted, never replaced, so entrapment peptides are mass-matched.
  - Shuffles that equal a target peptide or exceed the identity threshold are rejected.
  - The output is deterministic for a given `-seed`.
- **`EntrapmentEvaluator`:** estimates the FDP at each q-value threshold. It uses the combined estimator `N_E / N · (1 + T/E)`, with T/E measured from the database (`-database`, I = L).

**How the design was validated (OpenMS/OpenMS#10629):** on HF-X, Astral and TMTpro it was compared with a foreign-proteome entrapment (reviewed *Arabidopsis*, UP000006548).
- The estimates were within 0.15–0.45 pp of the foreign reference.
- They were close to the OpenMS/OpenMS#10364 `make_entrapment.py` design.
- The ANDES whole-protein shuffle underestimated the FDP by 20–33%. ANDES has since switched to the same design (bigbio/andes#237).

**For the paper** all shuffled entrapment databases are built with `DecoyDatabase -entrapment_ratio 1` from develop, instead of the per-PR scripts.
- **Several realisations:** **3 realisations** (`-seed 1/2/3`) per database, because a single realisation scatters by 0.1–0.27 pp (SD) on 3 files × 8,000 spectra.
- **Reference:** the *Arabidopsis* foreign entrapment for `hye` and `human`.
- **Archive:** all built databases are in this repository, under [`databases/`](databases/) (gzip). The authors' FASTAs are pinned by SHA256 in the build scripts.

### 3.2 Main benchmark: built databases

Built on 2026-10-23 with [`prepare_inputs.sh`](prepare_inputs.sh) and [`build_entrapment_dbs.sh`](build_entrapment_dbs.sh). The build used OpenMS develop `916a7d5` (the OpenMS/OpenMS#10629 merge), Release, system libraries on Ubuntu 24.04. It takes about 1 minute for all twelve. The databases are in [`databases/`](databases/) as `.fasta.gz`. SHA256 of the uncompressed files: [`entrapment_dbs.sha256`](entrapment_dbs.sha256). SHA256 of the `.gz` files (`gzip -9 -n`): [`databases/SHA256SUMS.gz.txt`](databases/SHA256SUMS.gz.txt).

**Inputs:**
- `hy`, `hye` and `human` targets: cut from the HYE FASTA (`d9ac434d…`) exactly as the frozen `prepare_databases.py` does. The script checks the resulting target-decoy files against the frozen `databases.json`, and all three match.
- *Arabidopsis*: reviewed UP000006548, UniProt 2026_03 (16,345 proteins), SHA256 `e20271b5…`, the same file as in OpenMS/OpenMS#10629.

**DecoyDatabase settings** (all databases):
- `-enzyme Trypsin/P` (the search enzyme).
- `-Decoy:keepPeptideNTerm false -Decoy:keepPeptideCTerm false`. This makes the decoys full-protein reversals with the `DECOY_` prefix, as in the OpenMS/OpenMS#10364 suite and in the OpenMS/OpenMS#10629 validation. With the peptide-termini options on, DecoyDatabase reverses peptide by peptide instead.
- Shuffled entrapment: `-entrapment_ratio 1 -seed 1|2|3`.
- Decoys are made for targets and entrapment proteins alike (`DECOY_ENTRAP_…`).

| Group | Database | Targets | Entrapment | Decoys | Size |
|---|---|---:|---:|---:|---:|
| Velos (main) | `hy_velos_natural_td.fasta`: natural, all human proteins except UPS1 and contaminants | 7,152 | 20,336 | 27,488 | 31 MB |
| Velos (check), Lumos LFQ, Lumos TMT | `hy_entrap_s{1,2,3}_td.fasta`: shuffled, r = 1 | 27,488 | 27,488 | 54,976 | 65 MB each |
| HF-X, Astral | `hye_entrap_s{1,2,3}_td.fasta`: shuffled, r = 1 | 31,889 | 31,889 | 63,778 | 71 MB each |
| TMTpro, timsTOF | `human_entrap_s{1,2,3}_td.fasta`: shuffled, r = 1 | 20,767 | 20,767 | 41,534 | 51 MB each |
| HF-X, Astral (reference) | `hye_arath_td.fasta`: *Arabidopsis* as foreign entrapment | 31,889 | 16,345 | 48,234 | 53 MB |
| TMTpro, timsTOF (reference) | `human_arath_td.fasta`: *Arabidopsis* as foreign entrapment | 20,767 | 16,345 | 37,112 | 43 MB |

**Checks** (on all twelve databases):
- **Decoys:** every decoy is the exact reversal of its target or entrapment protein.
- **Composition:** every shuffled entrapment protein has the amino acid composition of its target.
- **Mass-matched peptides** (`db_stats.py` of OpenMS/OpenMS#10629; Trypsin/P, ≤ 2 missed cleavages, 7–40 aa): no protein has moved cleavage sites, and every entrapment peptide has a target peptide of the same composition, hence the same mass.
  - 0.3% of the entrapment peptides equal a target peptide (e.g. `hye` s1: 10,292 of 3.33 million). DecoyDatabase keeps them when no shuffle within the identity threshold remains; OpenMS/OpenMS#10629 reports the same 0.3%.
  - T/E = 1.003 (`hy`, `hye`, `human`, seed 1).
- **Velos natural:** same entrapment accessions and sequences as the frozen `make_velos_natural.py` applied to `hy_td.fasta`. Only the decoy names differ (`DECOY_ENTRAP_…` instead of `DECOY_<accession>`), which does not matter to EntrapmentEvaluator. Its target and entrapment sequences are the ones on which OpenMS/OpenMS#10629 measured T/E = 0.2962, the frozen 1/r (r = 3.376).
- **Determinism:** a rerun of `hye` seed 2 gives a byte-identical file.

**Not changed from OpenMS/OpenMS#10364:** the contaminants (`Cont_`) get entrapment copies like every other target.

**What the PRs used before:** `make_entrapment.py` of the OpenMS/OpenMS#10364 supplement `sage-comparison-20261002`, SHA256 `fb77e3df…` (`hye`) and `76d25071…` (`human`). For Lumos (`hy`) only a whole-protein shuffle existed (OpenMS/OpenMS#10639, `1462fb72…`), the design that underestimates. These scripts are on branch `claude/andes-benchmarks` of OpenMS/OpenMS (`benchmark-reproduction/andes-ports/pr10629/scripts/`). Numbers measured with them are not directly comparable with the new databases, which are different realisations.

### 3.3 Held-out datasets: built databases

**FASTA:** for every dataset of section 2, the FASTA the original authors deposited. The exceptions are PXD058436, which deposits none, and ProteomeTools, whose search database is a human proteome. Both get `human_sp.fasta` from archive.openms.de (see the table).
- **Build script:** [`build_section2_dbs.sh`](build_section2_dbs.sh), same OpenMS build and DecoyDatabase settings as in section 3.2.
- **Pinned and checked:** the script downloads the authors' FASTAs and checks each against its SHA256.
- **Authors' decoys removed:** the script drops the authors' own decoys and builds new ones. Those decoys were full reversals only for PXD011695 (iPRG2015, PXD019643 and PXD065289 use other decoy designs), so the decoys would otherwise differ between datasets.
- **Run time:** about 5 minutes.
- **Files:** in [`databases/`](databases/). SHA256 of the uncompressed files: [`section2_dbs.sha256`](section2_dbs.sha256); of the `.gz` files: [`databases/SHA256SUMS.gz.txt`](databases/SHA256SUMS.gz.txt).

| Dataset | FASTA of the authors | Targets | Database (for the paper) |
|---|---|---:|---|
| PXD011695 (ETD, mouse) | [010090_MusMusculus_Uniprot_ISOFORMS_CONCAT_20161109.fasta](https://ftp.pride.ebi.ac.uk/pride/data/archive/2019/05/PXD011695/010090_MusMusculus_Uniprot_ISOFORMS_CONCAT_20161109.fasta): UniProt mouse with TrEMBL and isoforms, 2016-11-09 | 88,618 | `pxd011695_mouse_entrap_s{1,2,3}_td.fasta`, shuffled r = 1 (186 MB each, 85 MB gzip) |
| PXD065289 (ETciD, HEK293) | `2024-10-29-decoys-contam-UP000005640_9606.fasta.fas` from [fasta.zip](https://ftp.pride.ebi.ac.uk/pride/data/archive/2026/03/PXD065289/fasta.zip): human reference proteome with contaminants, 2024-10-29 | 20,702 | `pxd065289_human_entrap_s{1,2,3}_td.fasta`, shuffled r = 1 |
| PXD042233 (Lumos CID HeLa) | [UP000005640_9606.fasta](https://ftp.pride.ebi.ac.uk/pride/data/archive/2023/12/PXD042233/UP000005640_9606.fasta) + [contaminants.fasta](https://ftp.pride.ebi.ac.uk/pride/data/archive/2023/12/PXD042233/contaminants.fasta) (246) | 21,196 | `pxd042233_human_entrap_s{1,2,3}_td.fasta`, shuffled r = 1 |
| iPRG2015 (PXD010981) | [iPRG2015_decoy.fasta](https://ftp.pride.ebi.ac.uk/pride/data/archive/2018/09/PXD010981/iPRG2015_decoy.fasta), targets only | 6,628 | `iprg2015_entrap_s{1,2,3}_td.fasta`, shuffled r = 1 |
| Percolator LTQ yeast sets (yeast-01…04) | [yeast.fasta.gz](https://noble.gs.washington.edu/proj/percolator/data/yeast.fasta.gz) | 6,734 | `percolator_yeast_entrap_s{1,2,3}_td.fasta`, shuffled r = 1 |
| Percolator yeast chymotrypsin set | [yeast.fasta.gz](https://noble.gs.washington.edu/proj/percolator/data/yeast.fasta.gz) | 6,734 | `percolator_yeast_td.fasta`, **target-decoy only** (the shuffle is not mass-matched for chymotrypsin) |
| Percolator LTQ worm sets (worm-01/02) | [worm.fasta.gz](https://noble.gs.washington.edu/proj/percolator/data/worm.fasta.gz) | 27,499 | `percolator_worm_entrap_s{1,2,3}_td.fasta`, shuffled r = 1 |
| PXD019643 (immuno, Lumos) | [sp_21_04_2020_decoy.fasta](https://ftp.pride.ebi.ac.uk/pride/data/archive/2021/04/PXD019643/sp_21_04_2020_decoy.fasta), targets only: Swiss-Prot human, downloaded 2020-04-21, i.e. release 2020_01 by date | 20,365 | `pxd019643_td.fasta`, **target-decoy only** |
| PXD058436 (immuno, timsTOF) | not deposited; instead [human_sp.fasta](https://archive.openms.de/openms/testfiles/human_sp.fasta) from archive.openms.de: Swiss-Prot human, UniProt 2026_01 (see below) | 20,431 | `pxd058436_td.fasta`, **target-decoy only** |
| ProteomeTools (PXD004732) | none (the pools are synthetic); `human_sp.fasta` as for PXD058436 | 20,431 | `pxd058436_td.fasta`, target-decoy only; correctness from the pool peptide lists, not from entrapment |

**Checks** (as in section 3.2, on all twenty-one databases):
- **Decoys:** every decoy is the exact reversal of its protein. No accession occurs twice.
- **Composition:** every entrapment protein has the composition of its target.
- **Peptides** (`db_stats.py`, Trypsin/P): no protein has moved cleavage sites, every entrapment peptide has a target peptide of the same composition, and T/E = 1.002–1.003.
- **Determinism:** a second run of the script gives the same SHA256.

**Data notes:**
- **Percolator yeast FASTA:**
  - 6,698 sequences end with the stop codon `*`, and 6 pseudogenes or ORFs (YDR134C, YER109C, YER186W-A, YIL080W, YOL153C, YOR031W) have `*` inside.
  - DecoyDatabase turns `*` into `X` in the entrapment copies, which broke the composition check in a first build.
  - The script therefore drops the final `*` and writes the inner ones as `X`.
- **PXD011695:** the authors' database has 88,618 entries (TrEMBL and isoforms). The numbers in section 2.1 are from Swiss-Prot mouse (17,277 entries), so the new searches will differ from them. The project also deposits a yeast FASTA (`559292_SaccharomycesCerevisiae_Uniprot_ISOFORMS_CONCAT_20180626.fasta`) for its yeast runs, which are not selected.
- **PXD065289:** the shuffle is mass-matched only for Trypsin, Lys-C and Arg-C. The entrapment databases therefore apply to the trypsin runs (`…_trypsin_ETciD_…`). The project's Lys-N runs would need another design.
- **Percolator chymotrypsin set:** for the same reason it gets no entrapment database, only the target-decoy `percolator_yeast_td.fasta`.

**PXD058436: FASTA not from the authors.**
- **What the authors used:** MHCquant2, FragPipe and PEAKS searched "UniProtKB (Swiss-Prot, downloaded on 14.10.20) of Homo sapiens" (PRIDE data processing protocol). That file is not deposited. The matching UniProt release, 2020_05 (released 7 October 2020; the next, 2020_06, came on 2 December 2020), is not in the EBI mirror of previous releases, and ftp.uniprot.org was not reachable.
  - Release dates from UniSave, `https://rest.uniprot.org/unisave/P04637?format=json` (`firstReleaseDate`), checked 2026-10-23. The 2020 releases are 2020_01 (26 Feb), 2020_02 (22 Apr), 2020_03 (17 Jun), 2020_04 (12 Aug), 2020_05 (7 Oct) and 2020_06 (2 Dec).
- **What the paper uses instead:** [`human_sp.fasta`](https://archive.openms.de/openms/testfiles/human_sp.fasta) from archive.openms.de.
  - 20,431 Swiss-Prot human entries, no decoys, 36 selenocysteines (U).
  - SHA256 `b205ed9970fee62413e2f192c6fb82daab86e4a5897ef521f907ecbfcd7b3e63`, last modified on the archive 2026-06-09.
  - **Version: UniProt release 2026_01** (28 January 2026), all reviewed human entries (Swiss-Prot, `OX=9606`, no isoforms).
    - Checked on 2026-10-23 against `uniprot_sprot.fasta.gz` of the archived releases ([2026_01](https://ftp.ebi.ac.uk/pub/databases/uniprot/previous_releases/release-2026_01/knowledgebase/), [2026_02](https://ftp.ebi.ac.uk/pub/databases/uniprot/previous_releases/release-2026_02/knowledgebase/)) and the current 2026_03.
    - Release 2026_01 has the same 20,431 entries with identical headers and sequences. The file differs from it only in entry order and line wrapping.
    - Releases 2026_02 and 2026_03 also have 20,431 human entries, but differ in 19 and 39 accessions and in 9 and 12 sequences.
  - It is the database of the earlier ProSE runs on PXD058436 (OpenMS/OpenMS#10634, OpenMS/OpenMS#10639).
- **Consequence:** ProSE searches a newer Swiss-Prot (2026_01) than the published MHCquant2, FragPipe and PEAKS results (2020_05, downloaded 2020-10-14). The comparison in section 2.4 has to state this.
- **Measured difference** (2026-10-23, [`pxd058436_db_check.py`](pxd058436_db_check.py), per-sample results in [`pxd058436_db_check.tsv`](pxd058436_db_check.tsv)):
  - **Data:** the published peptide tables of MHCquant2, FragPipe and PEAKS for the nine samples of section 2.4 (5 class I, 4 class II). Each peptide was looked up, without modifications and with I = L, in the target sequences of two databases:

    | Database | Entries | Residues | Class I peptides missing | Class II peptides missing | Protein accessions missing |
    |---|---:|---:|---:|---:|---:|
    | `human_sp.fasta` (used; UniProt 2026_01) | 20,431 | 11,415,371 | 19 of 68,472 (0.028%) | 18 of 51,428 (0.035%) | 19 of 12,573 |
    | `sp_21_04_2020` of PXD019643 (same lab; release 2020_01 by date, four releases before the authors') | 20,365 | 11,357,832 | 7 (0.010%) | 4 (0.008%) | 12 |

  - **Where the missing peptides come from:**
    - `human_sp.fasta`: proteins removed, merged or changed since 2020 (e.g. P04745, P35544, P0DN76, Q5SRD0).
    - `sp_21_04_2020`: proteins added between releases 2020_01 and 2020_05 (e.g. P0DTE1–P0DTE8, P0DTU3/4).
  - **What the authors' database must hold:** it found all of these peptides, so it holds both sets of proteins. Neither available file reproduces it exactly.
  - **Size of the effect:**
    - At most 0.035% of the published peptides cannot be found in `human_sp.fasta`.
    - Its search space is 0.5% larger than that of April 2020 (in residues); the authors' October 2020 file lies in between.
    - The effect on identification counts is therefore far below the scatter between technical replicates.
  - **Recommendation:** keep `human_sp.fasta` and state the difference. Getting the authors' file would not change the comparison noticeably.

**Immunopeptidomics without entrapment:** two reasons.
- With unspecific cleavage, entrapment counts per run are too small to estimate an FDP (2–7 hits per run so far).
- DecoyDatabase's peptide-wise shuffle is designed for enzymatic peptides and has not been checked on unspecific searches.

There, FDR control rests on target-decoy only. The comparison is with the published MHCquant2, FragPipe and PEAKS results at the same FDR level.

## 4. Decisions and remaining tasks

**Decisions** (2026-10-23):
- **Rescoring:** ProSE's in-process Percolator is counted. Percolator 3.09 as an external step is the control in the supplement.
- **timsTOF input:** the Bruker `.d.zip` (section 1) and `.d` (PXD058436), read directly by ProSE.
- **PXD065289:** the five trypsin ETciD fractions of section 2.1.
- **ProteomeTools:** in the paper, with the three pools of section 2.3.
- **Immunopeptidomics:** all technical replicates of the nine PXD058436 samples (30 runs) and the six PXD019643 samples (18 runs).
- **Comparison engines:** Sage and MSFragger on every dataset, ANDES on Astral. Versions are fixed in section 1.
- **Held-out set:** all datasets of section 2.
- **PXD070049 extensions:** only the single-species runs, as the optional supplementary set S1 (section 2.2).
- **PXD058436 database:** `human_sp.fasta` (UniProt 2026_01).

**Remaining tasks:**
- **ProteomeTools ground truth:** obtain the synthetic peptide lists of `TUM_first_pool_1`, `_30` and `_61`, and add them with their source to this file. ProteomeTools publishes them, but they are not on PRIDE.
- **MSFragger:** fix its version at the first run and record it in section 1.
