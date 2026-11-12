# ProSE publication: benchmark datasets

Status: draft, 2026-11-10. Every download link below was checked (HTTP 200, size as listed). The scope decisions of 2026-11-10 are listed in section 5; the benchmark is run by scripts from one run table (section 4.5).

## 1. Main benchmark: 20 DDA runs, seven acquisition groups, full runs

This is the suite of issue [OpenMS/OpenMS#10364](https://github.com/OpenMS/OpenMS/issues/10364), with one change: every run is
searched **in full** instead of the 8,000 MS2 spectra sampled per file there. All numbers published in OpenMS/OpenMS#10364 and
the PRs that cite it are on the 8,000-spectrum subsets and have to be re-measured on the full runs.

**Input:** the vendor raw files, converted to mzML by us like every other dataset (section 4.0).
- **Frozen mzML files:** the mzML files in the table are the inputs frozen for OpenMS/OpenMS#10364 on 2026-09-30 (size and SHA256 from the reproduction package's `inputs.json`, [README](https://github.com/OpenMS/OpenMS/blob/a5705ec8e1cb19d40ebfa7bb16f6b5651aa1dc65/benchmark-reproduction/prose-andes/README.md)).
- **What they are used for:** they stay listed as the reference of the earlier numbers, not as inputs.
- **Spectrum counts:** from those frozen files (the package's `broad_benchmark/provenance/<id>.json`); they are counted again on the converted files.

**Totals:** 1,509,392 MS2 spectra; 1,497,401 of them with a recorded precursor charge of 2–5.

| Group | ID | Run | MS2 | Charge 2–5 | MS1 | mzML frozen in #10364 (reference only) | Vendor raw (the input) |
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
- **ProteoBench:** the HF-X and Astral files are the ProteoBench copies on archive.openms.de. Each of the six raw files there has the same byte size as the file of the same name on PRIDE (PXD028735, PXD070049). The three Astral files are byte-identical to PXD070049 (SHA-1 of its `checksum.txt`, compared 2026-11-11); the three HF-X files cannot be compared, as PXD028735 publishes no checksum. For the paper, cite the PRIDE accessions.
- **Folder names:** the archive folder `OrbitrapEclipse` holds Exploris 480 data. The suite IDs keep the `eclipse_` prefix.
- **TMT6plex runs:** each file also holds one MS3 scan per MS2 scan (37–41k). Only the CID MS2 spectra are searched.
- **timsTOF files:** all inputs are mzML (section 4.0). The spectrum counts in the table come from the PRIDE mzML (exporter output, with 5,536 and 6,276 precursors of charge 1, which the 8,000-spectrum selection excluded).
- **timsTOF plasma runs, sample and digestion** (PXD053748, PRIDE protocol; TIMS²Rescore, J Proteome Res 2024, doi:10.1021/acs.jproteome.4c00609):
  - **Sample:** EDTA plasma of one healthy donor, prepared with the PreOmics iST-BCT kit from 2 µl plasma; 200 ng peptides per injection on a timsTOF HT.
  - **Digestion:** tryptic. PRIDE names the kit but not the enzyme; the iST kits digest with a trypsin/Lys-C mix, and Lys-C only cleaves after K, so the peptides stay tryptic.
  - **Authors' search:** Sage 0.14.3, trypsin without cleavage before P, 8–50 aa, fixed Carbamidomethyl (C), variable acetylation and Oxidation (M), 10 ppm precursor and fragment. The benchmark uses the shared tryptic search space instead (below).
- **Checksums:** the SHA256 of each frozen mzML is in `inputs.json` of the reproduction package (`prose-andes-reproduction.zip` at the README's commit).

### Database and search settings (as frozen in OpenMS/OpenMS#10364)

The ProSE parameter files that implement these settings are in [`params/`](params/) (section 4.1).

- **FASTA:** [ProteoBenchFASTA_MixedSpecies_HYE.fasta](https://archive.openms.de/openms/benchmarks/pride-benchmarks/lfq/QExactiveHF/ProteoBench_Module_2/ProteoBenchFASTA_MixedSpecies_HYE.fasta)
  (16,670,994 bytes, 31,889 targets, SHA256 `d9ac434d88492c10c8e9a587ee7dbc9480fa0995fa07a6ba35a7da8abf39aa25`).
  It is split by accession suffix (contaminants `Cont_` kept in all three), with one full-sequence reversed `DECOY_` per protein (the databases of the paper have other decoys, section 3.2):

  | Database | Used for | Targets |
  |---|---|---:|
  | `hy` (human + yeast) | Velos, Lumos LFQ, Lumos TMT | 27,488 |
  | `hye` (human + yeast + E. coli) | HF-X, Astral | 31,889 |
  | `human` | TMTpro, timsTOF | 20,767 |

- **Digestion and modifications:** Trypsin/P, 2 missed cleavages, peptide length 7–40, fixed Carbamidomethyl (C), at most one Oxidation (M); TMT6plex or TMTpro fixed on the labelled groups.
- **Tolerances:** precursor 20 ppm (TMTpro 50 ppm); fragment 20 ppm, or 0.5 Da for the ion-trap CID groups (Velos, Lumos TMT).
- **Counting:** target PSMs at q ≤ 0.01 after **ProSE's in-process Percolator** (the default since OpenMS/OpenMS#10578), as users run ProSE.
  - **Database for counts and timings:** the plain target-decoy database (`hy_td.fasta`, `hye_td.fasta`, `human_td.fasta`), as users search. The entrapment databases are searched separately and give only the FDP (sections 3.2 and 4.2).
  - Control, for the supplement: Percolator 3.09 as an external step (`-Y -U`, seeds 1/42/137), as in OpenMS/OpenMS#10364.
- **Entrapment, the only estimate of the true error rate here:**
  - **Velos:** natural entrapment, UPS1/yeast against all human proteins, r = 3.376.
  - **HF-X, Astral, TMTpro:** one shuffled, mass-matched entrapment protein per target, r = 1.
  - **timsTOF:** added later with the same `human` database (OpenMS/OpenMS#10639).
  - **Lumos:** only a whole-protein shuffle so far (OpenMS/OpenMS#10639).
  - For the paper all entrapment databases were rebuilt with DecoyDatabase, Lumos included; see section 3.2.
- **Comparison engines for the paper:** **MSFragger** on every dataset, **Sage** on every dataset except the electron-based runs (below).
  - Sage version: 0.14.7, the last stable release (decided 2026-11-10; also the version of OpenMS/OpenMS#10364). Version 0.15 exists only as prereleases (v0.15.0-beta.2 of 2026-03-31).
  - Sage is not run on the electron-based runs (PXD011695 except its HCD run, and PXD065289). No Sage release has z+1 ions: only the master branch has them (`z_radical`), and the `z` ions of the releases are y − NH3, 1.008 Da lighter (section 4.4).
  - MSFragger version: 4.4.1 (`MSFragger-4.4.1`, the version of its first runs on 2026-11-11: the smoke test and the first real files, section 4.5).
  - So far: Sage on the 8,000-spectrum suite, MSFragger only in OpenMS/OpenMS#10403.
  - How they are run: section 4.4.

### Caveat for the paper

ProSE's defaults were tuned on these 20 files (the PRs listed in OpenMS/OpenMS#10364).
A held-out set is therefore needed. The datasets in section 2 were not used for tuning the defaults and are that set.

## 2. Held-out datasets

These datasets were not used to tune ProSE's defaults; they are the held-out set of the paper (see "Caveat" in section 1). Every file is named below, so that everyone who uses this document tests the same files. The databases for each dataset are in section 3.3.

**How independent each set is.** "Held-out" means that the files were not used for tuning. It does not always mean another laboratory or instrument:

| Independence | Datasets |
|---|---|
| Other project, laboratory and instrument | PXD011695, PXD065289, PXD042233 (Lumos CID, section 2.3; HeLa HCD, section 2.8), iPRG2015, PXD019643, PXD058436 |
| Other files of a project that also has tuned files | set S1 and the 250 pg runs (same Astral and method as `astral_*`), the independent UPS1 control (same Velos series), the timsTOF HYE runs (section 2.7: other instrument, but the HYE mixtures of `astral_*`) |

The paper has to state this difference when it reports the held-out results.

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
- **Instrument:** the file names (`ASND01_…`) suggest an Orbitrap Ascend; PRIDE lists an Exploris 480. An Exploris 480 has no ETD. **Checked 2026-11-10:** the header of the fraction 1 file holds an "Orbitrap Ascend Method Summary" with Orbitrap detection (resolutions 60K and 7.5K), so the instrument is an Orbitrap Ascend and the PRIDE entry is wrong.
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
- **Comparable:** the public ProteoBench submissions of other engines use the same files.
- **Results so far:**
  - OpenMS/OpenMS#10364 (8,000 MS2 per file): ProSE +20.5% PSMs over Sage.
  - OpenMS/OpenMS#10638 (chimeric search, whole `Condition_A_REP1` run): 42,469 → 91,875 PSMs at q ≤ 1%. The rank-2 FDP alone is 2.23%.

**Supplementary set S1: natural entrapment on Astral.** The three human-only runs of the same project and conditions (15 min, 50 ng), searched against `hye` with `main_highres.ini`.
- **What makes a PSM false:** the sample holds no yeast or E. coli, so every PSM that maps only to yeast or E. coli proteins is false.
- **Why:** it is the only natural entrapment on high-resolution data, next to Velos (ion trap). It checks the shuffled entrapment on Astral without any assumption about how the entrapment was made.
- **FDP:** EntrapmentEvaluator, with the yeast and E. coli proteins marked as entrapment (prefix `ENTRAP_`) and T/E from the database.

| Run | Raw |
|---|---|
| Human 1 | [LFQ_Astral_DDA_15min_50ng_Human_01.raw](https://ftp.pride.ebi.ac.uk/pride/data/archive/2026/02/PXD070049/LFQ_Astral_DDA_15min_50ng_Human_01.raw) (2.3 GB) |
| Human 2 | [LFQ_Astral_DDA_15min_50ng_Human_02.raw](https://ftp.pride.ebi.ac.uk/pride/data/archive/2026/02/PXD070049/LFQ_Astral_DDA_15min_50ng_Human_02.raw) (2.3 GB) |
| Human 3 | [LFQ_Astral_DDA_15min_50ng_Human_03.raw](https://ftp.pride.ebi.ac.uk/pride/data/archive/2026/02/PXD070049/LFQ_Astral_DDA_15min_50ng_Human_03.raw) (2.3 GB) |

### 2.3 Low resolution (ion-trap MS2) and a high-resolution reference

In section 1: PXD001819 (Velos, ion-trap CID) and the Lumos ion-trap CID TMT runs. In addition:

**[PXD042233](https://www.ebi.ac.uk/pride/archive/projects/PXD042233)** (Webel et al., Sci Data 2024, HeLa QC runs of many instruments): the only two Orbitrap Fusion Lumos runs of the project with ion-trap CID.
- **How they were found:** the instrument method in the raw-file headers of all 226 Lumos runs was checked. Both runs have CID 35% with ion-trap detection, a 144-minute method and a 1.3 Th isolation window.
- **Other runs:** all other Lumos runs are HCD (detected in the ion trap or the Orbitrap), and 9 have no readable method.
- **Earlier measurement:** OpenMS/OpenMS#10261 measured one Lumos CID HeLa run (21,501 / 28,173 PSMs; file not recorded).

| Run | Raw |
|---|---|
| Lumos CID 1 | [2015_12_21_12_42_Orbitrap-Fusion-Lumos_FSN20115.raw](https://ftp.pride.ebi.ac.uk/pride/data/archive/2023/12/PXD042233/2015_12_21_12_42_Orbitrap-Fusion-Lumos_FSN20115.raw) (2.1 GB) |
| Lumos CID 2 | [2015_12_22_00_06_Orbitrap-Fusion-Lumos_FSN20115.raw](https://ftp.pride.ebi.ac.uk/pride/data/archive/2023/12/PXD042233/2015_12_22_00_06_Orbitrap-Fusion-Lumos_FSN20115.raw) (2.1 GB) |

**iPRG2015** ([PXD010981](https://www.ebi.ac.uk/pride/archive/projects/PXD010981), MassIVE MSV000079843) is not low-resolution: Q Exactive HCD, MS2 at 17,500.
- **Role in the paper:** a high-resolution reference with an external comparison (MS-GF+ on the same three runs in the OpenMS archive).
- **Sample:** 200 ng yeast with spiked proteins.
- **Raw file names:** they spell two of the runs with a hyphen (`sample1-A`, `sample4-A`).

| Run | mzML (deposited, reference only) | raw (the input) | ProSE so far (native / Percolator) |
|---|---|---|---|
| 1A | [JD_06232014_sample1_A.mzML](https://ftp.pride.ebi.ac.uk/pride/data/archive/2018/09/PXD010981/JD_06232014_sample1_A.mzML) (1.4 GB) | [JD_06232014_sample1-A.raw](https://ftp.pride.ebi.ac.uk/pride/data/archive/2018/09/PXD010981/JD_06232014_sample1-A.raw) (1.1 GB) | 20,046 / 20,201 |
| 2A | [JD_06232014_sample2_A.mzML](https://ftp.pride.ebi.ac.uk/pride/data/archive/2018/09/PXD010981/JD_06232014_sample2_A.mzML) (1.4 GB) | [JD_06232014_sample2_A.raw](https://ftp.pride.ebi.ac.uk/pride/data/archive/2018/09/PXD010981/JD_06232014_sample2_A.raw) (1.1 GB) | 18,476 / 18,688 |
| 4A | [JD_06232014_sample4_A.mzML](https://ftp.pride.ebi.ac.uk/pride/data/archive/2018/09/PXD010981/JD_06232014_sample4_A.mzML) (1.4 GB) | [JD_06232014_sample4-A.raw](https://ftp.pride.ebi.ac.uk/pride/data/archive/2018/09/PXD010981/JD_06232014_sample4-A.raw) (1.1 GB) | 17,887 / 18,085 |

### 2.4 Immunopeptidomics (HLA class I and II, unspecific cleavage)

**Samples:** three donor–tissue pairs, each measured on both instruments: DN05 thyroid, DN13 tongue and DN14 bladder.
- Both HLA classes, three technical replicates each: 3 pairs × 2 classes × 3 replicates × 2 instruments = 36 runs, as in the manuscript.
- The two datasets share the donors (IDs `DN05`, `DN13`, `DN14`; that they are the same people is inferred from the IDs, not confirmed).
- All technical replicates of each sample are searched, because the published references count unique peptides per sample with the replicates pooled.

**[PXD058436](https://www.ebi.ac.uk/pride/archive/projects/PXD058436): MHCquant2 benign tissues** (Scheid et al., Genome Biol 2025)
- **Data:** timsTOF Pro 2, DDA-PASEF, all 633 runs of the project, 12 donors.
- **Reference results on PRIDE:** MHCquant2, FragPipe and PEAKS, per sample.
- **Input:** mzML (section 4.0).
- **ProSE so far** (single replicates, no comparison with another engine):
  - DN08_Brain_classI_techRep1: 2,011 PSMs at 1% FDR (67,944 MS2).
  - DN09_Pancreas_classII_techRep1: 8,399 PSMs (120,442 MS2) (OpenMS/OpenMS#10639).
- **Memory:** an unspecific human index does not fit into 12.5 GiB. The search needs `low_memory` or `database:mass_slices` (OpenMS/OpenMS#10639).

**[PXD019643](https://www.ebi.ac.uk/pride/archive/projects/PXD019643): HLA Ligand Atlas** (Marcu et al., J Immunother Cancer 2021)
- **Data:** Orbitrap Fusion Lumos, CID. Class I W6/32, 400–650 m/z; class II Tü39 + L243, 400–1000 m/z.
- **Reference results on PRIDE:** MHCquant v1 (Comet + Percolator).
- **ProSE so far:** OpenMS/OpenMS#9975 (PeptDeep rescoring), six class I files that are not recorded. 9,764 → 10,893 PSMs (+11.6%).

PXD058436, 18 runs. The input is the Bruker `.d.tar.gz`, converted by us (section 4.0); the deposited mzML is listed for reference. Both from PRIDE:

| Donor, tissue | Class | Run | Bruker .d (the input) | mzML (deposited, reference only) |
|---|---|---|---|---|
| DN05 Thyroid | I | `DN05_Thyroid_classI_techRep1` | [d.tar.gz](https://ftp.pride.ebi.ac.uk/pride/data/archive/2025/08/PXD058436/DN05_Thyroid_classI_techRep1.d.tar.gz) (2.2 GB) | [mzML](https://ftp.pride.ebi.ac.uk/pride/data/archive/2025/08/PXD058436/DN05_Thyroid_classI_techRep1.mzML) (1.6 GB) |
| DN05 Thyroid | I | `DN05_Thyroid_classI_techRep2` | [d.tar.gz](https://ftp.pride.ebi.ac.uk/pride/data/archive/2025/08/PXD058436/DN05_Thyroid_classI_techRep2.d.tar.gz) (2.2 GB) | [mzML](https://ftp.pride.ebi.ac.uk/pride/data/archive/2025/08/PXD058436/DN05_Thyroid_classI_techRep2.mzML) (1.6 GB) |
| DN05 Thyroid | I | `DN05_Thyroid_classI_techRep3` | [d.tar.gz](https://ftp.pride.ebi.ac.uk/pride/data/archive/2025/08/PXD058436/DN05_Thyroid_classI_techRep3.d.tar.gz) (2.3 GB) | [mzML](https://ftp.pride.ebi.ac.uk/pride/data/archive/2025/08/PXD058436/DN05_Thyroid_classI_techRep3.mzML) (1.6 GB) |
| DN05 Thyroid | II | `DN05_Thyroid_classII_techRep1` | [d.tar.gz](https://ftp.pride.ebi.ac.uk/pride/data/archive/2025/08/PXD058436/DN05_Thyroid_classII_techRep1.d.tar.gz) (2.5 GB) | [mzML](https://ftp.pride.ebi.ac.uk/pride/data/archive/2025/08/PXD058436/DN05_Thyroid_classII_techRep1.mzML) (1.7 GB) |
| DN05 Thyroid | II | `DN05_Thyroid_classII_techRep2` | [d.tar.gz](https://ftp.pride.ebi.ac.uk/pride/data/archive/2025/08/PXD058436/DN05_Thyroid_classII_techRep2.d.tar.gz) (2.5 GB) | [mzML](https://ftp.pride.ebi.ac.uk/pride/data/archive/2025/08/PXD058436/DN05_Thyroid_classII_techRep2.mzML) (1.8 GB) |
| DN05 Thyroid | II | `DN05_Thyroid_classII_techRep3` | [d.tar.gz](https://ftp.pride.ebi.ac.uk/pride/data/archive/2025/08/PXD058436/DN05_Thyroid_classII_techRep3.d.tar.gz) (2.5 GB) | [mzML](https://ftp.pride.ebi.ac.uk/pride/data/archive/2025/08/PXD058436/DN05_Thyroid_classII_techRep3.mzML) (1.7 GB) |
| DN13 Tongue | I | `DN13_Tongue_classI_techRep1` | [d.tar.gz](https://ftp.pride.ebi.ac.uk/pride/data/archive/2025/08/PXD058436/DN13_Tongue_classI_techRep1.d.tar.gz) (2.1 GB) | [mzML](https://ftp.pride.ebi.ac.uk/pride/data/archive/2025/08/PXD058436/DN13_Tongue_classI_techRep1.mzML) (1.8 GB) |
| DN13 Tongue | I | `DN13_Tongue_classI_techRep2` | [d.tar.gz](https://ftp.pride.ebi.ac.uk/pride/data/archive/2025/08/PXD058436/DN13_Tongue_classI_techRep2.d.tar.gz) (2.2 GB) | [mzML](https://ftp.pride.ebi.ac.uk/pride/data/archive/2025/08/PXD058436/DN13_Tongue_classI_techRep2.mzML) (1.8 GB) |
| DN13 Tongue | I | `DN13_Tongue_classI_techRep3` | [d.tar.gz](https://ftp.pride.ebi.ac.uk/pride/data/archive/2025/08/PXD058436/DN13_Tongue_classI_techRep3.d.tar.gz) (2.2 GB) | [mzML](https://ftp.pride.ebi.ac.uk/pride/data/archive/2025/08/PXD058436/DN13_Tongue_classI_techRep3.mzML) (1.7 GB) |
| DN13 Tongue | II | `DN13_Tongue_classII_techRep1` | [d.tar.gz](https://ftp.pride.ebi.ac.uk/pride/data/archive/2025/08/PXD058436/DN13_Tongue_classII_techRep1.d.tar.gz) (2.4 GB) | [mzML](https://ftp.pride.ebi.ac.uk/pride/data/archive/2025/08/PXD058436/DN13_Tongue_classII_techRep1.mzML) (1.9 GB) |
| DN13 Tongue | II | `DN13_Tongue_classII_techRep2` | [d.tar.gz](https://ftp.pride.ebi.ac.uk/pride/data/archive/2025/08/PXD058436/DN13_Tongue_classII_techRep2.d.tar.gz) (2.4 GB) | [mzML](https://ftp.pride.ebi.ac.uk/pride/data/archive/2025/08/PXD058436/DN13_Tongue_classII_techRep2.mzML) (1.9 GB) |
| DN13 Tongue | II | `DN13_Tongue_classII_techRep3` | [d.tar.gz](https://ftp.pride.ebi.ac.uk/pride/data/archive/2025/08/PXD058436/DN13_Tongue_classII_techRep3.d.tar.gz) (2.4 GB) | [mzML](https://ftp.pride.ebi.ac.uk/pride/data/archive/2025/08/PXD058436/DN13_Tongue_classII_techRep3.mzML) (1.9 GB) |
| DN14 Bladder | I | `DN14_Bladder_classI_techRep1` | [d.tar.gz](https://ftp.pride.ebi.ac.uk/pride/data/archive/2025/08/PXD058436/DN14_Bladder_classI_techRep1.d.tar.gz) (2.2 GB) | [mzML](https://ftp.pride.ebi.ac.uk/pride/data/archive/2025/08/PXD058436/DN14_Bladder_classI_techRep1.mzML) (2.1 GB) |
| DN14 Bladder | I | `DN14_Bladder_classI_techRep2` | [d.tar.gz](https://ftp.pride.ebi.ac.uk/pride/data/archive/2025/08/PXD058436/DN14_Bladder_classI_techRep2.d.tar.gz) (2.2 GB) | [mzML](https://ftp.pride.ebi.ac.uk/pride/data/archive/2025/08/PXD058436/DN14_Bladder_classI_techRep2.mzML) (2.1 GB) |
| DN14 Bladder | I | `DN14_Bladder_classI_techRep3` | [d.tar.gz](https://ftp.pride.ebi.ac.uk/pride/data/archive/2025/08/PXD058436/DN14_Bladder_classI_techRep3.d.tar.gz) (2.3 GB) | [mzML](https://ftp.pride.ebi.ac.uk/pride/data/archive/2025/08/PXD058436/DN14_Bladder_classI_techRep3.mzML) (2.1 GB) |
| DN14 Bladder | II | `DN14_Bladder_classII_techRep1` | [d.tar.gz](https://ftp.pride.ebi.ac.uk/pride/data/archive/2025/08/PXD058436/DN14_Bladder_classII_techRep1.d.tar.gz) (2.5 GB) | [mzML](https://ftp.pride.ebi.ac.uk/pride/data/archive/2025/08/PXD058436/DN14_Bladder_classII_techRep1.mzML) (2.3 GB) |
| DN14 Bladder | II | `DN14_Bladder_classII_techRep2` | [d.tar.gz](https://ftp.pride.ebi.ac.uk/pride/data/archive/2025/08/PXD058436/DN14_Bladder_classII_techRep2.d.tar.gz) (2.6 GB) | [mzML](https://ftp.pride.ebi.ac.uk/pride/data/archive/2025/08/PXD058436/DN14_Bladder_classII_techRep2.mzML) (2.3 GB) |
| DN14 Bladder | II | `DN14_Bladder_classII_techRep3` | [d.tar.gz](https://ftp.pride.ebi.ac.uk/pride/data/archive/2025/08/PXD058436/DN14_Bladder_classII_techRep3.d.tar.gz) (2.5 GB) | [mzML](https://ftp.pride.ebi.ac.uk/pride/data/archive/2025/08/PXD058436/DN14_Bladder_classII_techRep3.mzML) (2.2 GB) |

PXD019643, 18 runs. The input is the `.raw`, converted by us (section 4.0); the deposited mzML is listed for reference. Both from PRIDE:

| Donor, tissue | Class | Run | raw (the input) | mzML (deposited, reference only) |
|---|---|---|---|---|
| DN05 Thyroid | I | `160625_DK_AUT01-DN05_Thyroid_W6-32_20_DDA_1_400-650mz_msms8_standard` | [raw](https://ftp.pride.ebi.ac.uk/pride/data/archive/2021/04/PXD019643/160625_DK_AUT01-DN05_Thyroid_W6-32_20_DDA_1_400-650mz_msms8_standard.raw) (507 MB) | [mzML](https://ftp.pride.ebi.ac.uk/pride/data/archive/2021/04/PXD019643/160625_DK_AUT01-DN05_Thyroid_W6-32_20_DDA_1_400-650mz_msms8_standard.mzML) (256 MB) |
| DN05 Thyroid | I | `160625_DK_AUT01-DN05_Thyroid_W6-32_20_DDA_2_400-650mz_msms9_standard` | [raw](https://ftp.pride.ebi.ac.uk/pride/data/archive/2021/04/PXD019643/160625_DK_AUT01-DN05_Thyroid_W6-32_20_DDA_2_400-650mz_msms9_standard.raw) (508 MB) | [mzML](https://ftp.pride.ebi.ac.uk/pride/data/archive/2021/04/PXD019643/160625_DK_AUT01-DN05_Thyroid_W6-32_20_DDA_2_400-650mz_msms9_standard.mzML) (258 MB) |
| DN05 Thyroid | I | `160625_DK_AUT01-DN05_Thyroid_W6-32_20_DDA_3_400-650mz_msms10_standard` | [raw](https://ftp.pride.ebi.ac.uk/pride/data/archive/2021/04/PXD019643/160625_DK_AUT01-DN05_Thyroid_W6-32_20_DDA_3_400-650mz_msms10_standard.raw) (506 MB) | [mzML](https://ftp.pride.ebi.ac.uk/pride/data/archive/2021/04/PXD019643/160625_DK_AUT01-DN05_Thyroid_W6-32_20_DDA_3_400-650mz_msms10_standard.mzML) (257 MB) |
| DN05 Thyroid | II | `160625_DK_AUT01-DN05_Thyroid_Tue39L243_20_DDA_1_400-1000mz_msms32_standard` | [raw](https://ftp.pride.ebi.ac.uk/pride/data/archive/2021/04/PXD019643/160625_DK_AUT01-DN05_Thyroid_Tue39L243_20_DDA_1_400-1000mz_msms32_standard.raw) (790 MB) | [mzML](https://ftp.pride.ebi.ac.uk/pride/data/archive/2021/04/PXD019643/160625_DK_AUT01-DN05_Thyroid_Tue39L243_20_DDA_1_400-1000mz_msms32_standard.mzML) (436 MB) |
| DN05 Thyroid | II | `160625_DK_AUT01-DN05_Thyroid_Tue39L243_20_DDA_2_400-1000mz_msms33_standard` | [raw](https://ftp.pride.ebi.ac.uk/pride/data/archive/2021/04/PXD019643/160625_DK_AUT01-DN05_Thyroid_Tue39L243_20_DDA_2_400-1000mz_msms33_standard.raw) (760 MB) | [mzML](https://ftp.pride.ebi.ac.uk/pride/data/archive/2021/04/PXD019643/160625_DK_AUT01-DN05_Thyroid_Tue39L243_20_DDA_2_400-1000mz_msms33_standard.mzML) (426 MB) |
| DN05 Thyroid | II | `160625_DK_AUT01-DN05_Thyroid_Tue39L243_20_DDA_3_400-1000mz_msms34_standard` | [raw](https://ftp.pride.ebi.ac.uk/pride/data/archive/2021/04/PXD019643/160625_DK_AUT01-DN05_Thyroid_Tue39L243_20_DDA_3_400-1000mz_msms34_standard.raw) (768 MB) | [mzML](https://ftp.pride.ebi.ac.uk/pride/data/archive/2021/04/PXD019643/160625_DK_AUT01-DN05_Thyroid_Tue39L243_20_DDA_3_400-1000mz_msms34_standard.mzML) (429 MB) |
| DN13 Tongue | I | `170218_AM_AUT01-DN13_Tongue_W6-32_10_DDA_1_400-650mz_msms15_standard` | [raw](https://ftp.pride.ebi.ac.uk/pride/data/archive/2021/04/PXD019643/170218_AM_AUT01-DN13_Tongue_W6-32_10_DDA_1_400-650mz_msms15_standard.raw) (471 MB) | [mzML](https://ftp.pride.ebi.ac.uk/pride/data/archive/2021/04/PXD019643/170218_AM_AUT01-DN13_Tongue_W6-32_10_DDA_1_400-650mz_msms15_standard.mzML) (235 MB) |
| DN13 Tongue | I | `170218_AM_AUT01-DN13_Tongue_W6-32_10_DDA_2_400-650mz_msms16_standard` | [raw](https://ftp.pride.ebi.ac.uk/pride/data/archive/2021/04/PXD019643/170218_AM_AUT01-DN13_Tongue_W6-32_10_DDA_2_400-650mz_msms16_standard.raw) (470 MB) | [mzML](https://ftp.pride.ebi.ac.uk/pride/data/archive/2021/04/PXD019643/170218_AM_AUT01-DN13_Tongue_W6-32_10_DDA_2_400-650mz_msms16_standard.mzML) (234 MB) |
| DN13 Tongue | I | `170218_AM_AUT01-DN13_Tongue_W6-32_10_DDA_3_400-650mz_msms17_standard` | [raw](https://ftp.pride.ebi.ac.uk/pride/data/archive/2021/04/PXD019643/170218_AM_AUT01-DN13_Tongue_W6-32_10_DDA_3_400-650mz_msms17_standard.raw) (470 MB) | [mzML](https://ftp.pride.ebi.ac.uk/pride/data/archive/2021/04/PXD019643/170218_AM_AUT01-DN13_Tongue_W6-32_10_DDA_3_400-650mz_msms17_standard.mzML) (234 MB) |
| DN13 Tongue | II | `170407_AM_AUT01-DN13_Tongue_Tue39L243_10_DDA_1_400-1000mz_msms6_standard` | [raw](https://ftp.pride.ebi.ac.uk/pride/data/archive/2021/04/PXD019643/170407_AM_AUT01-DN13_Tongue_Tue39L243_10_DDA_1_400-1000mz_msms6_standard.raw) (634 MB) | [mzML](https://ftp.pride.ebi.ac.uk/pride/data/archive/2021/04/PXD019643/170407_AM_AUT01-DN13_Tongue_Tue39L243_10_DDA_1_400-1000mz_msms6_standard.mzML) (328 MB) |
| DN13 Tongue | II | `170407_AM_AUT01-DN13_Tongue_Tue39L243_10_DDA_2_400-1000mz_msm7_standard` | [raw](https://ftp.pride.ebi.ac.uk/pride/data/archive/2021/04/PXD019643/170407_AM_AUT01-DN13_Tongue_Tue39L243_10_DDA_2_400-1000mz_msm7_standard.raw) (657 MB) | [mzML](https://ftp.pride.ebi.ac.uk/pride/data/archive/2021/04/PXD019643/170407_AM_AUT01-DN13_Tongue_Tue39L243_10_DDA_2_400-1000mz_msm7_standard.mzML) (350 MB) |
| DN13 Tongue | II | `170407_AM_AUT01-DN13_Tongue_Tue39L243_10_DDA_3_400-1000mz_msms8_standard` | [raw](https://ftp.pride.ebi.ac.uk/pride/data/archive/2021/04/PXD019643/170407_AM_AUT01-DN13_Tongue_Tue39L243_10_DDA_3_400-1000mz_msms8_standard.raw) (660 MB) | [mzML](https://ftp.pride.ebi.ac.uk/pride/data/archive/2021/04/PXD019643/170407_AM_AUT01-DN13_Tongue_Tue39L243_10_DDA_3_400-1000mz_msms8_standard.mzML) (349 MB) |
| DN14 Bladder | I | `170527_AM_AUT01-DN14_Bladder_W6-32_10_DDA_1_400-650mz_msms30_standard` | [raw](https://ftp.pride.ebi.ac.uk/pride/data/archive/2021/04/PXD019643/170527_AM_AUT01-DN14_Bladder_W6-32_10_DDA_1_400-650mz_msms30_standard.raw) (471 MB) | [mzML](https://ftp.pride.ebi.ac.uk/pride/data/archive/2021/04/PXD019643/170527_AM_AUT01-DN14_Bladder_W6-32_10_DDA_1_400-650mz_msms30_standard.mzML) (233 MB) |
| DN14 Bladder | I | `170527_AM_AUT01-DN14_Bladder_W6-32_10_DDA_2_400-650mz_msms31_standard` | [raw](https://ftp.pride.ebi.ac.uk/pride/data/archive/2021/04/PXD019643/170527_AM_AUT01-DN14_Bladder_W6-32_10_DDA_2_400-650mz_msms31_standard.raw) (473 MB) | [mzML](https://ftp.pride.ebi.ac.uk/pride/data/archive/2021/04/PXD019643/170527_AM_AUT01-DN14_Bladder_W6-32_10_DDA_2_400-650mz_msms31_standard.mzML) (239 MB) |
| DN14 Bladder | I | `170527_AM_AUT01-DN14_Bladder_W6-32_10_DDA_3_400-650mz_msms32_standard` | [raw](https://ftp.pride.ebi.ac.uk/pride/data/archive/2021/04/PXD019643/170527_AM_AUT01-DN14_Bladder_W6-32_10_DDA_3_400-650mz_msms32_standard.raw) (471 MB) | [mzML](https://ftp.pride.ebi.ac.uk/pride/data/archive/2021/04/PXD019643/170527_AM_AUT01-DN14_Bladder_W6-32_10_DDA_3_400-650mz_msms32_standard.mzML) (236 MB) |
| DN14 Bladder | II | `170530_AM_AUT01-DN14_Bladder_Tue39L243_10_DDA_1_400-1000mz_msms4_standard` | [raw](https://ftp.pride.ebi.ac.uk/pride/data/archive/2021/04/PXD019643/170530_AM_AUT01-DN14_Bladder_Tue39L243_10_DDA_1_400-1000mz_msms4_standard.raw) (765 MB) | [mzML](https://ftp.pride.ebi.ac.uk/pride/data/archive/2021/04/PXD019643/170530_AM_AUT01-DN14_Bladder_Tue39L243_10_DDA_1_400-1000mz_msms4_standard.mzML) (406 MB) |
| DN14 Bladder | II | `170530_AM_AUT01-DN14_Bladder_Tue39L243_10_DDA_2_400-1000mz_msms5_standard` | [raw](https://ftp.pride.ebi.ac.uk/pride/data/archive/2021/04/PXD019643/170530_AM_AUT01-DN14_Bladder_Tue39L243_10_DDA_2_400-1000mz_msms5_standard.raw) (765 MB) | [mzML](https://ftp.pride.ebi.ac.uk/pride/data/archive/2021/04/PXD019643/170530_AM_AUT01-DN14_Bladder_Tue39L243_10_DDA_2_400-1000mz_msms5_standard.mzML) (419 MB) |
| DN14 Bladder | II | `170530_AM_AUT01-DN14_Bladder_Tue39L243_10_DDA_3_400-1000mz_msms6_standard` | [raw](https://ftp.pride.ebi.ac.uk/pride/data/archive/2021/04/PXD019643/170530_AM_AUT01-DN14_Bladder_Tue39L243_10_DDA_3_400-1000mz_msms6_standard.raw) (776 MB) | [mzML](https://ftp.pride.ebi.ac.uk/pride/data/archive/2021/04/PXD019643/170530_AM_AUT01-DN14_Bladder_Tue39L243_10_DDA_3_400-1000mz_msms6_standard.mzML) (423 MB) |

**Comparison with the published references:**
- **Counting:** unique peptides at 1% peptide-level FDR per sample, over all technical replicates. MHCquant2 settings: 20 ppm; z 1–4; 8–14 aa for class I.
  - PXD058436: for example, DN13_Tongue_classI has 11,220 peptides with MHCquant2, 9,507 with FragPipe and 11,027 with PEAKS (counted from the deposited result tables).
- **Database:** MHCquant2's Swiss-Prot of 2020-10-14 is not available. ProSE uses `human_sp.fasta` from archive.openms.de, which is Swiss-Prot human of UniProt release 2026_01 (section 3.3). Under 0.1% of the published peptides are missing from it (measured in section 3.3), so the difference hardly matters, but the comparison has to state it.
- **FDR control:** target-decoy only, no entrapment (section 3.3).
- **Possible ground truth:** PXD058436 also has six synthetic peptide mix runs (`*_Synpepmix*_classI_*.raw`, Thermo), which have not been examined yet.

### 2.5 Low input (250 pg)

**[PXD070049](https://www.ebi.ac.uk/pride/archive/projects/PXD070049), Astral DDA at 250 pg:** the same HYE mixtures as the Astral files of section 1, measured with 200 times less material, on the same Orbitrap Astral with the same 15-minute method.
- **Selected files:** the three counterparts of `astral_A2`, `astral_B1` and `astral_B3`, so only the load differs between the two sets.
- **What it tests:** whether identification numbers and FDR control hold on sparse low-input spectra.
- **How:** the same parameter file (`main_highres.ini`), databases (`hye_entrap_s{1,2,3}_td.fasta`, section 3.2) and counting as the 50 ng files.

| ID | Run | Counterpart at 50 ng | Raw |
|---|---|---|---|
| `astral250pg_A2` | LFQ_Astral_DDA_15min_250pg_Condition_A_REP2 | `astral_A2` | [LFQ_Astral_DDA_15min_250pg_Condition_A_REP2.raw](https://ftp.pride.ebi.ac.uk/pride/data/archive/2026/02/PXD070049/LFQ_Astral_DDA_15min_250pg_Condition_A_REP2.raw) (159 MB) |
| `astral250pg_B1` | LFQ_Astral_DDA_15min_250pg_Condition_B_REP1 | `astral_B1` | [LFQ_Astral_DDA_15min_250pg_Condition_B_REP1.raw](https://ftp.pride.ebi.ac.uk/pride/data/archive/2026/02/PXD070049/LFQ_Astral_DDA_15min_250pg_Condition_B_REP1.raw) (185 MB) |
| `astral250pg_B3` | LFQ_Astral_DDA_15min_250pg_Condition_B_REP3 | `astral_B3` | [LFQ_Astral_DDA_15min_250pg_Condition_B_REP3.raw](https://ftp.pride.ebi.ac.uk/pride/data/archive/2026/02/PXD070049/LFQ_Astral_DDA_15min_250pg_Condition_B_REP3.raw) (182 MB) |

- **Not used:** the timsTOF runs of the same project at 250 pg. They were measured on a timsTOF Ultra, the 50 ng runs on an Ultra 2, so load and instrument would be confounded.

### 2.6 Independent UPS1 control

The three Velos UPS1 files of section 1 were used to tune ProSE's defaults, so their natural-entrapment FDP is not an independent check. [PXD001819](https://www.ebi.ac.uk/pride/archive/projects/PXD001819) holds 27 UPS1 runs: 9 spike levels (50–50,000 amol) × 3 replicates.

**Selected files:** three runs that were never used for tuning or for earlier ProSE measurements, at other spike levels and replicates.
- **Not used:** the files of section 1, and `UPS1_2500amol_R1` and `UPS1_50000amol_R1` from OpenMS/OpenMS#10261.
- **How they are searched:** with `main_velos_cid.ini` against `hy_velos_natural_td.fasta`. The sample is yeast + the 48 UPS1 proteins, so every PSM that maps only to other human proteins is false.

| Run | Raw (the input) |
|---|---|
| UPS1_500amol_R2 | [UPS1_500amol_R2.raw](https://ftp.pride.ebi.ac.uk/pride/data/archive/2015/12/PXD001819/UPS1_500amol_R2.raw) (1.8 GB) |
| UPS1_2500amol_R3 | [UPS1_2500amol_R3.raw](https://ftp.pride.ebi.ac.uk/pride/data/archive/2015/12/PXD001819/UPS1_2500amol_R3.raw) (1.7 GB) |
| UPS1_12500amol_R2 | [UPS1_12500amol_R2.raw](https://ftp.pride.ebi.ac.uk/pride/data/archive/2015/12/PXD001819/UPS1_12500amol_R2.raw) (1.7 GB) |

### 2.7 timsTOF, cell lysate (HYE)

The only timsTOF data of section 1 are two plasma runs, and they were used for tuning. [PXD070049](https://www.ebi.ac.uk/pride/archive/projects/PXD070049) also holds DDA-PASEF runs of the HYE mixtures on a timsTOF Ultra 2 (file names `LFQ_Ultra2_PASEF_…`; 5-minute and 15-minute methods, 50 ng).
- **Selected files:** the 15-minute, 50 ng counterparts of `astral_A2`, `astral_B1` and `astral_B3`, so the same three mixtures are measured on both instruments.
- **What it tests:** a complex lysate on a timsTOF, on files and an instrument that were not used for tuning. The species composition is known.
- **How:** `main_highres.ini`; counts and timings against `hye_td.fasta`, FDP against `hye_entrap_s{1,2,3}_td.fasta` (section 3.2).
- **Input:** the Bruker `.d.zip`, converted by us (section 4.0).
- **Checked 2026-11-10** (the `analysis.tdf` of each `.d.zip`, read with range requests): all runs are DDA-PASEF on a timsTOF Ultra 2, method `ddaPASEF_1.1sec.m`, with MS1 and DDA-PASEF frames only and 27 minutes of acquisition. The precursor counts are in the tables. The MS2 counts are counted on the converted files.

| ID | Run | Counterpart on Astral | Precursors | Charge 2–5 | Bruker .d (the input) |
|---|---|---|---:|---:|---|
| `ultra2_A2` | LFQ_Ultra2_PASEF_15min_50ng_Condition_A_REP2 | `astral_A2` | 94,794 | 87,338 | [d.zip](https://ftp.pride.ebi.ac.uk/pride/data/archive/2026/02/PXD070049/LFQ_Ultra2_PASEF_15min_50ng_Condition_A_REP2.d.zip) (1.6 GB) |
| `ultra2_B1` | LFQ_Ultra2_PASEF_15min_50ng_Condition_B_REP1 | `astral_B1` | 94,911 | 87,585 | [d.zip](https://ftp.pride.ebi.ac.uk/pride/data/archive/2026/02/PXD070049/LFQ_Ultra2_PASEF_15min_50ng_Condition_B_REP1.d.zip) (1.7 GB) |
| `ultra2_B3` | LFQ_Ultra2_PASEF_15min_50ng_Condition_B_REP3 | `astral_B3` | 94,281 | 86,776 | [d.zip](https://ftp.pride.ebi.ac.uk/pride/data/archive/2026/02/PXD070049/LFQ_Ultra2_PASEF_15min_50ng_Condition_B_REP3.d.zip) (1.6 GB) |

**Supplementary set S2: natural entrapment on timsTOF** (decided 2026-11-10). The three human-only runs of the same method, searched against `hye` like set S1 on Astral (section 2.2): the sample holds no yeast or E. coli, so every PSM that maps only to yeast or E. coli proteins is false.
- **Why:** the only natural entrapment on timsTOF data. It checks the shuffled entrapment there without any assumption about how the entrapment was made.
- **How:** `main_highres.ini`; FDP against `hye_s1_natural_td.fasta` (section 3.2), counts against `hye_td.fasta`.

| ID | Run | Precursors | Charge 2–5 | Bruker .d (the input) |
|---|---|---:|---:|---|
| `ultra2_human_01` | LFQ_Ultra2_PASEF_15min_50ng_Human_01 | 95,843 | 88,561 | [d.zip](https://ftp.pride.ebi.ac.uk/pride/data/archive/2026/02/PXD070049/LFQ_Ultra2_PASEF_15min_50ng_Human_01.d.zip) (1.6 GB) |
| `ultra2_human_02` | LFQ_Ultra2_PASEF_15min_50ng_Human_02 | 94,682 | 87,662 | [d.zip](https://ftp.pride.ebi.ac.uk/pride/data/archive/2026/02/PXD070049/LFQ_Ultra2_PASEF_15min_50ng_Human_02.d.zip) (1.6 GB) |
| `ultra2_human_03` | LFQ_Ultra2_PASEF_15min_50ng_Human_03 | 95,184 | 87,672 | [d.zip](https://ftp.pride.ebi.ac.uk/pride/data/archive/2026/02/PXD070049/LFQ_Ultra2_PASEF_15min_50ng_Human_03.d.zip) (1.6 GB) |

### 2.8 HeLa, HCD with Orbitrap MS2 (two instruments of another laboratory)

Standard tryptic HCD data from a project, a laboratory and instruments that were not used for tuning: HeLa QC runs of [PXD042233](https://www.ebi.ac.uk/pride/archive/projects/PXD042233) (the project of the Lumos CID runs in section 2.3), three runs each on an Orbitrap Exploris 480 and a Q Exactive HF.

**How the runs were selected** (2026-11-10, from the project's [`pride_metadata.csv`](https://ftp.pride.ebi.ac.uk/pride/data/archive/2023/12/PXD042233/pride_metadata.csv), 7,444 runs):
1. **Instrument:** per model, the instrument with the most runs: Exploris 480 `MA10132C` (105 runs) and Q Exactive HF `207` (412 runs). All their runs are HCD without MS3.
2. **Method:** the most frequent run length of that instrument: 145 minutes (67 runs) and 144 minutes (350 runs).
3. **Typical runs, spread over time:** these runs, ordered by date, are cut into three equal parts. From each part comes the run whose number of identified MS2 spectra (MaxQuant, column `MS/MS Identified`) is closest to the instrument's median (55,295 and 43,366).

- **How:** `main_highres.ini`; counts and timings against `pxd042233_human_td.fasta`, FDP against `pxd042233_human_entrap_s{1,2,3}_td.fasta` (section 3.3).
- **MS2 analyzer:** both instruments have an Orbitrap as their only analyzer. **Checked 2026-11-10** in the header of the first Exploris 480 run: resolutions 60,000 and 15,000. The header of the Q Exactive HF runs was not read (the download broke off).
- **MS2 counts:** from the metadata table; they are counted again on the converted files.

| Run | Instrument | MS2 (metadata) | MS2 identified by MaxQuant (context) | Raw (the input) |
|---|---|---:|---:|---|
| `2020_06_10_07_00_Orbitrap-Exploris-480_MA10132C` | Exploris 480 | 149,897 | 54,780 | [raw](https://ftp.pride.ebi.ac.uk/pride/data/archive/2023/12/PXD042233/2020_06_10_07_00_Orbitrap-Exploris-480_MA10132C.raw) (2.4 GB) |
| `2020_06_26_18_23_Orbitrap-Exploris-480_MA10132C` | Exploris 480 | 151,697 | 55,295 | [raw](https://ftp.pride.ebi.ac.uk/pride/data/archive/2023/12/PXD042233/2020_06_26_18_23_Orbitrap-Exploris-480_MA10132C.raw) (3.1 GB) |
| `2020_10_16_17_37_Orbitrap-Exploris-480_MA10132C` | Exploris 480 | 149,318 | 55,213 | [raw](https://ftp.pride.ebi.ac.uk/pride/data/archive/2023/12/PXD042233/2020_10_16_17_37_Orbitrap-Exploris-480_MA10132C.raw) (2.7 GB) |
| `2015_03_02_16_45_Q-Exactive-HF-Orbitrap_207` | Q Exactive HF | 85,097 | 43,409 | [raw](https://ftp.pride.ebi.ac.uk/pride/data/archive/2023/12/PXD042233/2015_03_02_16_45_Q-Exactive-HF-Orbitrap_207.raw) (1.9 GB) |
| `2015_12_04_18_57_Q-Exactive-HF-Orbitrap_207` | Q Exactive HF | 74,110 | 43,372 | [raw](https://ftp.pride.ebi.ac.uk/pride/data/archive/2023/12/PXD042233/2015_12_04_18_57_Q-Exactive-HF-Orbitrap_207.raw) (2.1 GB) |
| `2017_03_15_19_58_Q-Exactive-HF-Orbitrap_207` | Q Exactive HF | 79,363 | 43,296 | [raw](https://ftp.pride.ebi.ac.uk/pride/data/archive/2023/12/PXD042233/2017_03_15_19_58_Q-Exactive-HF-Orbitrap_207.raw) (2.1 GB) |

## 3. Databases and entrapment

Status 2026-10-23: **all entrapment databases are built with DecoyDatabase**. Rebuilt on 2026-11-11 with other decoys (decided 2026-11-11): every database holds the decoys ProSE generates by default, and all three engines search these decoys; ProSE reads them from the database (`decoys auto`, sections 3.2 and 4.1). Targets and entrapment are unchanged.
- **Plain target-decoy databases** (decided and built 2026-11-10): counts and timings come from searches without entrapment. [`build_plain_td_dbs.sh`](build_plain_td_dbs.sh) writes `<name>_td.fasta` for every tryptic dataset (seven files, sections 3.2 and 3.3): the first entrapment realisation without its entrapment entries, so each file holds exactly the targets and decoys of the entrapment databases. No OpenMS is needed. SHA256: [`plain_td_dbs.sha256`](plain_td_dbs.sha256).
  - **Same file from every realisation:** the three realisations of each database give the same plain file (the script checks it).
  - **Same as DecoyDatabase:** for iPRG2015, DecoyDatabase run directly on the same targets with the options of `build_section2_dbs.sh` (without `-entrapment_ratio`) writes a byte-identical file (checked on 2026-11-12 with the frozen build; SHA256 `fe3fa31f…`).
  - **Same targets as the frozen databases:** `hy_td`, `hye_td` and `human_td` have the accessions and target sequences of the frozen OpenMS/OpenMS#10364 target-decoy databases. Their decoys differ: OpenMS/OpenMS#10364 reversed whole proteins (section 3.2).
- **Main benchmark:** sixteen databases (section 3.2): thirteen with entrapment, including the natural entrapment of set S1, and three plain target-decoy.
- **Held-out datasets:** eighteen databases (section 3.3): fourteen of 2026-10-23 (twelve with entrapment, two target-decoy only) and four plain target-decoy. All come from the FASTAs the original authors deposited, except those of PXD058436, which uses `human_sp.fasta` from archive.openms.de.

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
- **Reference:** the *Arabidopsis* foreign entrapment for HF-X and Astral (`hye`) and TMTpro (`human`), the groups on which OpenMS/OpenMS#10629 checked the shuffled design against it.
- **Archive:** all built databases are in this repository, under [`databases/`](databases/) (gzip). The authors' FASTAs are pinned by SHA256 in the build scripts.

### 3.2 Main benchmark: built databases

Built on 2026-10-23 with [`prepare_inputs.sh`](prepare_inputs.sh) and [`build_entrapment_dbs.sh`](build_entrapment_dbs.sh). The build used OpenMS develop `916a7d5` (the OpenMS/OpenMS#10629 merge), Release, system libraries on Ubuntu 24.04. It takes about 1 minute for all thirteen. **Rebuilt on 2026-11-11** with the decoys below, with DecoyDatabase of the frozen OpenMS `fbb25191d7` (Docker image `prose-bench/openms-tools:3.7.0-fbb25191d7`, section 4.1), about 30 seconds per database. The databases are in [`databases/`](databases/) as `.fasta.gz`. SHA256 of the uncompressed files: [`entrapment_dbs.sha256`](entrapment_dbs.sha256). SHA256 of the `.gz` files (`gzip -9 -n`): [`databases/SHA256SUMS.gz.txt`](databases/SHA256SUMS.gz.txt).

**Inputs:**
- `hy`, `hye` and `human` targets: cut from the HYE FASTA (`d9ac434d…`) exactly as the frozen `prepare_databases.py` does. The script checks the resulting target-decoy files against the frozen `databases.json`, and all three match.
- *Arabidopsis*: reviewed UP000006548, UniProt 2026_03 (16,345 proteins), SHA256 `e20271b5…`, the same file as in OpenMS/OpenMS#10629.
  - UniProt serves only its current release, and on 2026-11-11 the download no longer matched. `prepare_inputs.sh` then takes the *Arabidopsis* proteins from the entrapment entries of `databases/hye_arath_td.fasta.gz`. The rebuilt reference databases show that these are the same proteins (checks below).

**DecoyDatabase settings** (all databases):
- `-enzyme Trypsin/P` (the search enzyme).
- **Decoys** (since 2026-11-11): `-Decoy:keepPeptideNTerm true -Decoy:keepPeptideCTerm true -Decoy:non_shuffle_pattern K,P,R`, prefix `DECOY_`. Each protein is cut at every Trypsin/P site (no missed cleavages); in each segment the first and the last residue and every K, R and P stay in place, and the rest is reversed.
  - **The decoys ProSE generates by default** (`decoys generate`, `decoy_method keep_termini`, defaults of the ProSE tool since OpenMS/OpenMS#10740). ProSE of the frozen build regenerates exactly these decoys from every database (checks below). ProSE reads them from the database (`decoys auto`, section 4.1), as Sage and MSFragger do; the checksum shows it would generate the same ones.
  - **Every target peptide has a decoy of the same length, mass and cleavage sites,** also every protein N-terminal and Met-clipped one: the decoys start with M as often as the targets (`hye_td`: 99.7% of both). Whole-protein reversals start with M in 2.1% of the cases, so the Met-clipped target peptides had (almost) no decoys, about 1% of the target candidates. A rescoring feature that marks these peptides then lets Percolator accept them with no decoys to pay for it: in OpenMS/OpenMS#10726 the entrapment FDP rose from about 1% to 13–24%.
  - **Cost:** 1.8% of the decoy peptides equal a target peptide (`hye_td` 1.76%, `human_td` 1.83%; whole-protein reversals 0.12% and 0.09%; Trypsin/P, ≤ 2 missed cleavages, 7–40 aa, I = L), mostly peptides made of short segments.
  - **Before 2026-11-11:** `-Decoy:keepPeptideNTerm false -Decoy:keepPeptideCTerm false`, full-protein reversals, as in the OpenMS/OpenMS#10364 suite and in the OpenMS/OpenMS#10629 validation.
- Shuffled entrapment: `-entrapment_ratio 1 -seed 1|2|3`. The decoy settings do not change it.
- Decoys are made for targets and entrapment proteins alike (`DECOY_ENTRAP_…`).

| Group | Database | Targets | Entrapment | Decoys | Size |
|---|---|---:|---:|---:|---:|
| Velos (main) | `hy_velos_natural_td.fasta`: natural, all human proteins except UPS1 and contaminants | 7,152 | 20,336 | 27,488 | 31 MB |
| Velos (check), Lumos LFQ, Lumos TMT | `hy_entrap_s{1,2,3}_td.fasta`: shuffled, r = 1 | 27,488 | 27,488 | 54,976 | 65 MB each |
| HF-X, Astral | `hye_entrap_s{1,2,3}_td.fasta`: shuffled, r = 1 | 31,889 | 31,889 | 63,778 | 71 MB each |
| TMTpro, timsTOF | `human_entrap_s{1,2,3}_td.fasta`: shuffled, r = 1 | 20,767 | 20,767 | 41,534 | 51 MB each |
| Set S1 (Astral human-only runs) | `hye_s1_natural_td.fasta`: natural, every yeast and E. coli protein of `hye` (contaminants `Cont_` excluded) | 20,768 | 11,121 | 31,889 | 34 MB |
| HF-X, Astral (reference) | `hye_arath_td.fasta`: *Arabidopsis* as foreign entrapment | 31,889 | 16,345 | 48,234 | 53 MB |
| TMTpro, timsTOF (reference) | `human_arath_td.fasta`: *Arabidopsis* as foreign entrapment | 20,767 | 16,345 | 37,112 | 43 MB |
| All groups: counts and timings | `hy_td.fasta`, `hye_td.fasta`, `human_td.fasta`: targets and their decoys, no entrapment | 27,488 / 31,889 / 20,767 | 0 | 27,488 / 31,889 / 20,767 | 31 / 34 / 25 MB |

The timsTOF HYE runs of section 2.7 use the `hye` databases of this table, and set S2 uses `hye_s1_natural_td.fasta` like set S1.

**Checks** (on all thirteen databases):
- **Decoys (2026-11-11):** ProSE of the frozen build regenerates the decoys of every database (`-Search:decoys generate`) and logs a checksum of them (`-Search:decoy_parity_report true`: FNV-1a 64 of the decoy sequences in target order). For every database it equals the checksum of the database's own decoys, with no cleavage-site mismatch. Every decoy is a permutation of its protein.
- **Unchanged by the rebuild:** the targets and entrapment proteins (headers, sequences and order) and the decoy accessions are those of the 2026-10-23 build.
- **Composition:** every shuffled entrapment protein has the amino acid composition of its target.
- **Mass-matched peptides** (`db_stats.py` of OpenMS/OpenMS#10629; Trypsin/P, ≤ 2 missed cleavages, 7–40 aa): no protein has moved cleavage sites, and every entrapment peptide has a target peptide of the same composition, hence the same mass.
  - 0.3% of the entrapment peptides equal a target peptide (e.g. `hye` s1: 10,292 of 3.33 million). DecoyDatabase keeps them when no shuffle within the identity threshold remains; OpenMS/OpenMS#10629 reports the same 0.3%.
  - T/E = 1.003 (`hy`, `hye`, `human`, seed 1).
- **Velos natural:** same entrapment accessions and sequences as the frozen `make_velos_natural.py` applied to `hy_td.fasta`. Only the decoy names differ (`DECOY_ENTRAP_…` instead of `DECOY_<accession>`), which does not matter to EntrapmentEvaluator. Its target and entrapment sequences are the ones on which OpenMS/OpenMS#10629 measured T/E = 0.2962, the frozen 1/r (r = 3.376).
- **Determinism:** a rerun of `hye` seed 2 gives a byte-identical file.

**Not changed from OpenMS/OpenMS#10364:** the contaminants (`Cont_`) get entrapment copies like every other target.

**What the PRs used before:** `make_entrapment.py` of the OpenMS/OpenMS#10364 supplement `sage-comparison-20261002`, SHA256 `fb77e3df…` (`hye`) and `76d25071…` (`human`). For Lumos (`hy`) only a whole-protein shuffle existed (OpenMS/OpenMS#10639, `1462fb72…`), the design that underestimates. These scripts are on branch `claude/andes-benchmarks` of OpenMS/OpenMS (`benchmark-reproduction/andes-ports/pr10629/scripts/`). Numbers measured with them are not directly comparable with the new databases, which are different realisations.

### 3.3 Held-out datasets: built databases

**FASTA:** for every dataset of section 2, the FASTA the original authors deposited, with one exception. PXD058436 deposits none, so it gets `human_sp.fasta` from archive.openms.de (see the table).
- **Build script:** [`build_section2_dbs.sh`](build_section2_dbs.sh), same OpenMS build and DecoyDatabase settings as in section 3.2, rebuilt on 2026-11-11 like them. The decoys are those ProSE generates for the search of each database, with one case of its own:
  - **Immunopeptidomics** (unspecific search): ProSE then reverses the whole protein and keeps an initial Met in front (`peptide:clip_nterm_methionine`, on in the parameter files). The script reverses whole proteins (DecoyDatabase `-enzyme "no cleavage"`) and moves a trailing M back to the front.
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
| PXD019643 (immuno, Lumos) | [sp_21_04_2020_decoy.fasta](https://ftp.pride.ebi.ac.uk/pride/data/archive/2021/04/PXD019643/sp_21_04_2020_decoy.fasta), targets only: Swiss-Prot human, downloaded 2020-04-21, i.e. release 2020_01 by date | 20,365 | `pxd019643_td.fasta`, **target-decoy only** |
| PXD058436 (immuno, timsTOF) | not deposited; instead [human_sp.fasta](https://archive.openms.de/openms/testfiles/human_sp.fasta) from archive.openms.de: Swiss-Prot human, UniProt 2026_01 (see below) | 20,431 | `pxd058436_td.fasta`, **target-decoy only** |

**Plain target-decoy databases** (built 2026-11-10 with [`build_plain_td_dbs.sh`](build_plain_td_dbs.sh), section 3, again on 2026-11-11 from the rebuilt databases): `pxd011695_mouse_td.fasta`, `pxd065289_human_td.fasta`, `pxd042233_human_td.fasta` and `iprg2015_td.fasta`, for counts and timings. The immunopeptidomics databases are target-decoy only anyway. The HeLa HCD runs of section 2.8 use the PXD042233 databases.

**Checks** (as in section 3.2, on all fourteen databases):
- **Decoys (2026-11-11):** ProSE's regenerated decoys have the checksum of the database's decoys for every database, also for the immunopeptidomics databases (ProSE with their parameter files). No cleavage-site mismatch. Targets, decoy accessions and the entrapment are those of the 2026-10-23 build. No accession occurs twice.
- **Composition:** every entrapment protein has the composition of its target.
- **Peptides** (`db_stats.py`, Trypsin/P): no protein has moved cleavage sites, every entrapment peptide has a target peptide of the same composition, and T/E = 1.002–1.003.
- **Determinism:** a second run of the script gives the same SHA256.

**Data notes:**
- **PXD011695:** the authors' database has 88,618 entries (TrEMBL and isoforms). The numbers in section 2.1 are from Swiss-Prot mouse (17,277 entries), so the new searches will differ from them. The project also deposits a yeast FASTA (`559292_SaccharomycesCerevisiae_Uniprot_ISOFORMS_CONCAT_20180626.fasta`) for its yeast runs, which are not selected.
- **PXD065289:** the shuffle is mass-matched only for Trypsin, Lys-C and Arg-C. The entrapment databases therefore apply to the trypsin runs (`…_trypsin_ETciD_…`). The project's Lys-N runs would need another design.

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
  - **Data:** the published peptide tables of MHCquant2, FragPipe and PEAKS for the six PXD058436 samples of section 2.4 (3 class I, 3 class II). Each peptide was looked up, without modifications and with I = L, in the target sequences of two databases:

    | Database | Entries | Residues | Class I peptides missing | Class II peptides missing | Protein accessions missing |
    |---|---:|---:|---:|---:|---:|
    | `human_sp.fasta` (used; UniProt 2026_01) | 20,431 | 11,415,371 | 15 of 24,292 (0.062%) | 19 of 20,723 (0.092%) | 16 of 9,285 |
    | `sp_21_04_2020` of PXD019643 (same lab; release 2020_01 by date, four releases before the authors') | 20,365 | 11,357,832 | 3 (0.012%) | 0 (0%) | 3 |

  - **Where the missing peptides come from:**
    - `human_sp.fasta`: proteins removed, merged or changed since 2020 (e.g. P04745, P35544, P0DN76, Q5SRD0).
    - `sp_21_04_2020`: proteins added between releases 2020_01 and 2020_05 (e.g. P0DTE7, P0DTE8, A0A2R8Y619).
  - **What the authors' database must hold:** it found all of these peptides, so it holds both sets of proteins. Neither available file reproduces it exactly.
  - **Size of the effect:**
    - At most 0.092% of the published peptides cannot be found in `human_sp.fasta`.
    - Its search space is 0.5% larger than that of April 2020 (in residues); the authors' October 2020 file lies in between.
    - The effect on identification counts is therefore far below the scatter between technical replicates.
  - **Recommendation:** keep `human_sp.fasta` and state the difference. Getting the authors' file would not change the comparison noticeably.

**Immunopeptidomics without entrapment:** two reasons.
- With unspecific cleavage, entrapment counts per run are too small to estimate an FDP (2–7 hits per run so far).
- DecoyDatabase's peptide-wise shuffle is designed for enzymatic peptides and has not been checked on unspecific searches.

There, FDR control rests on target-decoy only. The comparison is with the published MHCquant2, FragPipe and PEAKS results at the same FDR level.

## 4. Search parameters and measurement protocol

### 4.0 Input format

Every search, by every engine, reads mzML that we converted ourselves, all with the same converter and settings. No deposited mzML is used as input, so no dataset depends on how others converted it.

| Source format | Datasets |
|---|---|
| Thermo `.raw` | section 1 except timsTOF; PXD011695, PXD065289, PXD042233, iPRG2015, PXD019643; set S1, the 250 pg runs; the independent UPS1 control (section 2.6); the HeLa HCD runs (section 2.8) |
| Bruker `.d` (`.d.zip`, `.d.tar.gz`) | timsTOF plasma (section 1), PXD058436, the timsTOF HYE runs (section 2.7) |

- **Records:** the converter, its version and settings are recorded here, together with the SHA256 of every converted mzML.
- **Spectrum counts:** the MS2 counts of all runs are counted on the converted files and replace the counts of section 1.
- **Converter:** OpenMS `FileConverter` from the frozen OpenMS build, for every format. The build needs `WITH_THERMO_RAW` (and a .NET 8 runtime) and `WITH_OPENTIMS`. Output is uncompressed, lossless mzML: no zlib, no numpress, no zstd (`FileConverter` has no option for zlib alone; it writes zlib only together with numpress, and `-zstd_compression` gives zstd). Sage, MSFragger and ProSE all read it; the files are larger than with zlib. The first converted file is checked for `MS:1000576` (no compression). Large files may use `-process_lowmemory`, which does not change the output.

**Thermo `.raw`: vendor peak picking.**
- **Command:** `FileConverter -in <run>.raw -out <run>.mzML -RawToMzML:reader inprocess`.
- **Reader:** the in-process reader (default on Linux and macOS): the `openms-thermo-bridge` 1.0.0 (pinned in OpenMS' vcpkg port, commit `75849ecf`) with Thermo RawFileReader 8.0.37.
- **Peak picking:** on, as by default; `-RawToMzML:no_peak_picking` is not set. "Vendor peak picking" then means, for each scan (bridge, `ThermoScanReader.cs`, `ReadPeaks`):
  1. **Centroid stream present:** a scan with a centroid stream (the label data of Orbitrap and Astral scans, computed by the instrument software) is written as these centroids. With them come the vendor's peak charges, if requested.
  2. **Profile without centroid stream:** a profile scan without a centroid stream (typically ion-trap scans acquired in profile) is centroided by RawFileReader (`Scan.ToCentroid`), Thermo's own centroiding in the library.
  3. **Acquired as centroid:** a scan acquired in centroid mode (typically ion-trap MS2) is written as stored.
  - In every case OpenMS itself does no peak picking. The mzML records `peak picking` as data processing, together with the RawFileReader version.
- **Precursor m/z:** the trailer value "Monoisotopic M/Z" if it is plausible, i.e. within the isolation window, or within −3/+2.5 Th for narrow windows. Otherwise the isolation target (`ThermoRawFileMetadata::selectedIon`). Both values are stored on the precursor. The charge comes from the trailer.

**Bruker `.d`: no vendor peak picking available.**
- **Why none:** Bruker's own centroiding of PASEF MS/MS spectra exists only in its closed TDF SDK, and OpenMS does not use it for spectra. OpenMS reads the TDF data with OpenTIMS and processes it itself.
- **Command:** `FileConverter -in <run>.d -out <run>.mzML -bruker:load_ms1 false` (a `.d.zip` is read directly; a `.d.tar.gz` is unpacked first).
- **Defaults otherwise:** the conversion uses the defaults (`bruker:ms2_centroid_algo off`), which means:
  - **DDA-PASEF MS2:** per precursor, the raw TOF events of all PASEF frames of that precursor are summed per TOF index, smoothed (±1 TOF index) and reduced to local maxima (±1 TOF index), and these are the centroids. This is the processing of timsrust, which Sage uses.
  - **MS1: not written** (`-bruker:load_ms1 false`, decided 2026-11-11). By default the MS1 frames are written as the detector records them (TOF events per mobility scan, not centroided). That is 81–96% of each mzML (12–18 GB per run, 7–8 times the `.d`), and Sage then takes 5–6 times as long as on the `.d`: the timed timsTOF searches would mostly measure mzML parsing. No search of the benchmark uses MS1 (ProSE's parameter files have no MS1 option; Sage uses MS1 only for quantification, which is off). Whether ProSE and MSFragger run as expected on the MS2-only mzML is checked on the first timsTOF run. The MS1 counts of the timsTOF runs in section 1 are the MS1 frames of the `analysis.tdf`.
  - **Calibration: without the Bruker SDK** (decided 2026-10-23), so that everyone gets the same mzML with open software only.
    - **m/z:** OpenMS' implementation of the TDF `MzCalibration` table, with per-frame temperature correction.
    - **Ion mobility (1/K0):** the rational model of the `TimsCalibration` table, or the linear model of `GlobalMetadata` if that table is missing.
    - **How the SDK is excluded:** OpenMS uses the SDK only when `OPENMS_BRUKER_SDK_PATH` names it (`FileConverter` sets no SDK path). The variable must therefore be unset during the conversion.
    - **Check:** the conversion log must not contain the line `TIMS calibration: Bruker SDK`.
  - **Precursor:** m/z is Bruker's `MonoisotopicMz` from the `Precursors` table, or `LargestPeakMz` if the acquisition software determined none. The charge also comes from `Precursors`, the ion mobility from `Precursors.ScanNumber`.
- **Checked 2026-11-11** with OpenMS develop `db4bd541`, on one run of each timsTOF dataset (`tims_plasma_30min`, timsTOF HT; `ultra2_A2`, timsTOF Ultra 2; `DN13_Tongue_classI_techRep1`, timsTOF Pro), against each run's `analysis.tdf`:
  - Every precursor with PASEF MS/MS gives one MS2 spectrum (115,047, 94,794 and 97,503), none empty; precursor m/z and charge are the TDF values; 1/K0 lies within the acquisition range; the calibration is the TDF tables', without the Bruker SDK.
  - Sage 0.14.7 on the mzML against Sage on the `.d` (read by timsrust), with the benchmark's configuration: of the PSMs at 1% FDR found in both, 99.7% (plasma) and 99.3% (`ultra2_A2`) have the same peptide, with the same scores. The mzML gives 6.6% and 3.0% more PSMs, mainly from precursors without monoisotopic m/z and charge, which timsrust drops and `FileConverter` keeps. 1/K0 differs by 0.01–0.02 (OpenMS applies the `TimsCalibration` model) and the RT by under a second.
  - Without MS1 (`ultra2_A2`): the same MS2 spectra, 2.3 GB instead of 12.3 GB, and identical Sage results.

The conversion settings (the versions of OpenMS, the bridge and RawFileReader) are recorded together with the SHA256 of every mzML.


### 4.1 ProSE parameter files

Every search uses one of the parameter files in [`params/`](params/). They are written by [`params/make_inis.py`](params/make_inis.py) from the defaults of the ProSE build, and the script checks each file by reading it back with that ProSE (invalid names or values abort).
- **Settings in the files:** the search space, tolerances, labels and charges, `decoys auto` and `fragment:min_matched_ions 4` (below).
- **Everything else:** the defaults of the ProSE version used for the paper. This includes in-process Percolator rescoring (`Search:rescore true`), the mass calibration with m/z recalibration (`Search:calibration:enabled true`, `recalibrate offset`), and the terminal rescoring features and stratum q-values (`Search:rescoring:terminal_features`, `stratum_q_values`).
- **Deviation from the ProSE defaults, `decoys auto`** (decided 2026-11-11): ProSE reads the `DECOY_` entries of the database, the same file Sage and MSFragger search, instead of generating its own decoys (`decoys generate`, the default). They are the decoys ProSE would generate (keep_termini, section 3.2). The reason: all engines search one file, even if ProSE's decoy generation changes later.
  - ProSE logs `decoys=auto: reusing existing decoys detected in the database (marker 'DECOY_', prefix)` and a note that `decoy_method keep_termini` has no effect.
  - Checked 2026-11-11: ProSE switches the terminal features and stratum q-values off when fewer than half as many decoys as targets (by share) start with M. None of the 36 databases (34 of the benchmark, 2 of the smoke test) meets that condition; their decoys start with M exactly as often as their targets. One search each against `smoke_td.fasta` and `human_td.fasta` logged no Met warning and recorded both options as `true`.
- **Deviation from the ProSE defaults, `fragment:min_matched_ions 4`** (decided 2026-11-11): a PSM needs at least 4 matched fragment ions, not 5 (the ProSE default). 4 is the default of Sage (`min_matched_peaks`) and MSFragger (`min_matched_fragments`), and the driver passes the value of the parameter file to both (section 4.4). The reason: the same value for all engines.
- **Current build:** the files were written on 2026-11-11 with the frozen commit (below), built from OpenMS's `dockerfiles/Dockerfile` (target `tools`); version string `3.7.0-pre-HEAD-2026-11-11`, revision `fbb2519`. Written again on the same day with the same build for `fragment:min_matched_ions 4`: only that value changed.
- **Frozen commit:** OpenMS develop `fbb25191d7` (`fbb25191d7659e9aa0326456cc187b7f9119409e`, 2026-11-11, version 3.7.0), frozen on 2026-11-11 and tagged in OpenMS/OpenMS as `prose-benchmark-2026-11` (annotated tag, `git checkout prose-benchmark-2026-11`; not a release). It contains OpenMS/OpenMS#10713 (charge range), #10874 (q-values (D + 1) / T), #10877 (`peptide q-value`, section 4.2), #10878 and #10879 (`-out_merged` with inputs that the calibration gave different tolerances). Its code is the code that the CI of #10879 built and tested on all platforms; develop after #10879 adds only documentation (#10872). The parameter files are written with it (above).
- **Run command:** `ProSE -ini <file> -in <spectra> -database <database> -out <out> -threads <n>` (`-out_idxml` is a deprecated alias of `-out`). The spectra are always mzML (section 4.0).

| Parameter file | Used for | Precursor | Fragment | Enzyme, length | Modifications | Charge |
|---|---|---|---|---|---|---|
| `main_highres.ini` | HF-X, Astral, Lumos LFQ, timsTOF (section 1); also set S1 and the 250 pg runs (section 2.5) | ±20 ppm, isotope errors −2…1 | 20 ppm | Trypsin/P, ≤ 2 missed cleavages, 7–40 aa | fixed Carbamidomethyl (C); variable Oxidation (M), ≤ 1 | 2–5 |
| `main_velos_cid.ini` | Velos (section 1) and the independent UPS1 control (section 2.6) | as above | 0.5 Da | as above | as above | 2–5 |
| `main_lumos_tmt6_cid.ini` | Lumos TMT | as above | 0.5 Da | as above | + fixed TMT6plex (K), (N-term) | 2–5 |
| `main_exploris_tmtpro.ini` | Exploris TMTpro | ±50 ppm | 20 ppm | as above | + fixed TMTpro (K), (N-term) | 2–5 |
| `pxd011695_elite_itms.ini` | PXD011695 (all five runs; ETD-type spectra get c and z+1 ions by activation) | ±20 ppm | 0.5 Da | as above | as main | 2–5 |
| `pxd065289_etcid_ot.ini` | PXD065289 | ±20 ppm | 20 ppm | as above | as main | 2–5 |
| `pxd042233_lumos_cid.ini` | PXD042233 | ±20 ppm | 0.5 Da | as above | as main | 2–5 |
| `iprg2015_qe.ini` | iPRG2015 (mzML; centroided) | ±20 ppm | 20 ppm | as above | as main | 2–5 |
| `pxd058436_classI.ini` | PXD058436 class I | ±20 ppm | 0.02 Da | unspecific, 8–14 aa, 800–2,500 Da | none fixed; Oxidation (M), ≤ 3 | 1–4 |
| `pxd058436_classII.ini` | PXD058436 class II | ±20 ppm | 0.02 Da | unspecific, 12–30 aa, 800–5,000 Da | none fixed; Oxidation (M), ≤ 5 | 1–5 |
| `pxd019643_classI.ini` | PXD019643 class I | ±5 ppm | 0.02 Da | unspecific, 8–12 aa, 800–2,500 Da | none fixed; Oxidation (M), ≤ 3 | 2–3 |
| `pxd019643_classII.ini` | PXD019643 class II | ±5 ppm | 0.02 Da | unspecific, 8–25 aa, 800–5,000 Da | none fixed; Oxidation (M), ≤ 5 | 2–5 |

**Charge range** (decided 2026-11-10): every engine searches a spectrum with a recorded precursor charge at that charge, also when the charge lies outside the range of the table. The range only gives the charges tried for spectra without a recorded charge (timsTOF precursors for which the acquisition software determined no charge, section 4.0).
- **Why:** Sage and MSFragger always search a spectrum at its recorded charge. ProSE skips spectra outside the range by default since OpenMS/OpenMS#10713 (on timsTOF, 5–6% of the precursors have charge 1). All parameter files therefore set `precursor:recorded_charge_outside_range` to `search`, the behaviour before that change.
- **Consequences:** this is the third setting, after `decoys auto` and `fragment:min_matched_ions 4` (above), in which ProSE does not run at its default. The published charge ranges of the immunopeptidomics sets (for example 2–3 for PXD019643 class I) do not restrict any engine.

**Sources of the settings:**
- **Tryptic search space:** frozen in OpenMS/OpenMS#10364 (`jobs.json`, arm `native_dedup:default`). All tryptic datasets share it and differ only in tolerances, labels and charges.
- **Immunopeptidomics:** the settings of the original publications (PRIDE data processing protocols).
  - **PXD058436 (MHCquant2):** 20 ppm, 0.02 Da, lengths, masses, charges, and at most 3 or 5 modifications.
  - **PXD019643 (MHCquant 1.5.1):** 5 ppm, 0.02 Da, lengths, masses and charges. The protocol does not state the modification limit, so the PXD058436 values are used.
  - **Both:** `low_memory` is on, because an unspecific human index does not fit into 12.5 GiB otherwise.
  - **Standard-mode arm:** the manuscript compares standard and low-memory mode. The standard-mode arm uses the same file with `-Search:low_memory false` on the command line (driver: `search --extra '-Search:low_memory false' --tag standard_mode`, section 4.5).
- **Smoke test:** `main_highres.ini` and `pxd058436_classI.ini` ran on the ProSE test data (`SimpleSearchEngine_1.mzML`) without errors.

### 4.2 What is counted

- **Levels:** per file; for groups, summed over the files of the group.
  - **PSMs** at 1% PSM-level FDR (PSM q ≤ 0.01).
  - **Peptides** at 1% peptide-level FDR (peptide q ≤ 0.01): unique unmodified sequences (I = L), each with its best PSM. Not the unique sequences among the PSMs that pass the PSM-level threshold.
  - No protein level: protein inference differs too much between the engines.
  - **PSM-level q-values** (decided 2026-11-12): computed by the driver, the same way for all engines, from each engine's PSMs (the top hit of each spectrum, targets and decoys) and its final PSM score after rescoring: ProSE's Percolator score (`percolator_score`), Sage's `sage_discriminant_score`, Percolator's score for MSFragger.
    - Sorted by score, q = (D + 1) / T (at most 1), equal scores entering together, then the minimum over all lower scores.
    - The reason: ProSE's own PSM q-values are (D + π0) / T, with Percolator's π0 estimate (`Search:rescoring:use_pi0 true`, the ProSE default; π0 0.08–0.32 on three results), while Sage's `spectrum_q` and Percolator's (with `-Y`) are (D + 1) / T. On `astral250pg_A2` ProSE's own accept 926 PSMs and (D + 1) / T on the same score 916 (−1.1%); on `ultra2_A2` 40,583 and 40,576. For Sage and MSFragger the driver's values give exactly the engines' own counts (both files, checked 2026-11-12). Computed in the driver, ProSE stays at its default.
  - **Peptide-level q-values** (decided 2026-11-11): computed by the driver in the same way, from the same PSMs and scores.
    - A peptide is an unmodified sequence with I = L. Each peptide competes with its best PSM by that score, separately per label (target, decoy).
    - The q-values are computed as at the PSM level.
    - The reason: the engines' own peptide-level q-values are defined differently, so the same results would be counted differently. Sage's `peptide_q` is (1 + Σ PEP) / T on modified sequences, with PEPs from a kernel density estimate. Percolator's peptide table uses modified sequences. ProSE's `peptide q-value` (OpenMS's `FalseDiscoveryRate::applyBasicPeptideLevel`) uses unmodified sequences without I = L and ranks by Percolator PEP. The common definition changes every engine's count, in both directions. Searches of 2026-11-11 with prose-paper `5c5dd5f`, before the other changes of that day, counted both ways: on `astral250pg_A2` Sage's own `peptide_q` accepts 1,240 peptides and the common definition 1,303 (+5%), ProSE (647) and MSFragger (1,325) are unchanged; on `ultra2_A2` the common definition lowers MSFragger from 26,105 to 25,956 (−0.6%), Sage from 25,894 to 25,855 (−0.15%) and ProSE from 26,491 to 26,486 (−0.02%).
    - ProSE's own `peptide q-value` is not used, but nearly agrees on single files: the same peptides on `astral250pg_A2` (647 with the plain database, 631 with entrapment s1), 5 fewer of 26,491 on `ultra2_A2` (0.02%; ProSE keeps I and L apart in the competition).
  - **One counting tool for all engines:** `EntrapmentEvaluator`. It counts the top hit of each spectrum (PSM level) and distinct unmodified sequences with I = L (peptide level). With the plain target-decoy database its accepted PSMs and peptides are the identification counts.
    - The results of all three engines are first written as a minimal idXML by the driver (section 4.5): the target top hits with spectrum, unmodified sequence, proteins, the driver's PSM q-value (main score) and its peptide q-value (meta value `peptide q-value`, which `EntrapmentEvaluator` reads).
- **Database:** counts come from the search against the plain target-decoy database (section 3). The searches against the entrapment databases give the FDP only; their counts are not reported as identification numbers.
- **Rescoring:** ProSE's in-process Percolator (default).
  - Its random seed is fixed in ProSE (Percolator default 1) and cannot be set from outside, so the main numbers come from one run per file.
  - Control, for the supplement: Percolator 3.09 as an external step on the `-out_pin` of a second run with `-Search:rescore false -Search:report:top_hits 10`, with seeds 1, 42 and 137 (`-Y -U`). The mean over the seeds is reported, as in OpenMS/OpenMS#10364.
- **Entrapment FDP:** `EntrapmentEvaluator -database <entrapment database>` on each result, combined estimator, at both levels (PSM and peptide).
  - Each shuffled design has three database realisations (`_s1`, `_s2`, `_s3`), each searched separately.
  - *Arabidopsis* reference: HF-X and Astral (`hye_arath_td.fasta`) and TMTpro (`human_arath_td.fasta`), one search per file. Not on timsTOF.
  - Reported is the mean ± SD of the FDP over the three realisations. Velos (natural) and the *Arabidopsis* reference have one database each.
- **Immunopeptidomics:** unique peptides at 1% peptide-level FDR per sample, as the published references count them.
  - All technical replicates of a sample are searched together (`-in` with all replicates, `-out_merged`).
  - The driver computes the q-values of a sample across its replicates: the same computation as per file (above), on the pooled PSMs of all replicates (ProSE's `-out_merged` result, Sage's one search of all replicates, Percolator on MSFragger's pooled `.pin`). A union of the per-replicate peptide lists would not be FDR-controlled, as true peptides recur across replicates and false ones rarely do.
  - **ProSE's pooled PSMs are ranked by Percolator's PEP** (`percolator_pep`; decided 2026-11-12), not by its score: in `-out_merged` each input keeps its own Percolator model, so the scores of the inputs are not on one scale, while the PEPs are. Sage and MSFragger train one model on the pooled PSMs. In a test with two runs (`astral250pg_A2` and `ultra2_A2`), ranking by score accepted 26,562 peptides and 41,444 PSMs, ranking by PEP 26,606 and 41,529 (ProSE's own `peptide q-value` also gives 26,606). With one model both rankings give the same peptides (all 12 single-file results of the three engines, checked 2026-11-12).
  - No entrapment so far. How the true error rate is checked there is open: Jonas Scheid provides the design (section 5).

### 4.3 Speed and memory

Speed and memory are part of the paper, for ProSE and the comparison engines alike. There are three timing benchmarks. All of them search the plain target-decoy databases (section 3).

**Common protocol:**
- **Machines** (as in the manuscript):
  - **Engine comparison and batch arm:** a 64-core AMD EPYC 7763 node, reserved exclusively.
  - **Thread scaling:** a two-socket AMD EPYC 9654 node, threads pinned to whole cores, for all three engines.
  - Recorded for both: RAM, OS and storage.
- **Input:** local SSD. One discarded run first fills the page cache (in the thread scaling: once per file and engine).
- **What is measured:** with `/usr/bin/time -v`, per invocation, end to end, including the database index and the rescoring, without file conversion:
  - wall time
  - CPU time (user + system)
  - peak resident memory (maximum RSS)
- **Stages:** where an engine logs them, the times of index building, search and rescoring are reported separately. For MSFragger, the search and the Percolator step are two timed invocations, and their sum is the end-to-end time.
- **Repetitions:** each measurement three times; the median is reported.
- **Memory caps:** a run that needs more memory than the machine has counts as failed, not as slow. ProSE's memory options (`low_memory`, `database:mass_slices` once merged) are reported with the setting used.

**1. Engine comparison, per file:** every file of sections 1 and 2, one invocation per file, at 64 threads. Every engine builds its index anew for every file.

**2. Batch arm:** per group, all files of the group in one invocation at 64 threads, as users run a study. It shows how much of the per-file time is the index, which a batch builds once.
- **Groups:** the seven groups of section 1 and each held-out dataset. For immunopeptidomics, the per-sample search over the three technical replicates (section 4.2) already is a batch.
- **Reported:** time per batch and per file, next to the sum of the per-file times of benchmark 1.

**3. Thread scaling:** ProSE, Sage and MSFragger, each at 1, 2, 4, 8, 16, 32, 48, 64, 96, 128 and 192 threads.
- **Files:** one per group: `hfx_A2`, `astral_A2`, `velos_125_R1`, `lumos_lfq_5192`, `lumos_tmt_5058`, `eclipse_tmtpro_10855`, `tims_plasma_30min`, `DN13_Tongue_classI_techRep1`, `DN13_Tongue_classII_techRep1`.
- **Order:** from 192 threads down. The discarded run that fills the page cache is done once per file and engine, at 192 threads.
- **Size:** 9 files × 11 thread counts × 3 engines × 3 repetitions = 891 timed runs.
- **Time limit:** 24 hours of wall time per run. A run that hits it is stopped and recorded as over the limit, and the lower thread counts of that file and engine are recorded as not run, because they would take longer still. The unspecific searches at 1 and 2 threads are the likely cases.
- **Sage at one thread:** Sage 0.14.7 aborts when it sees a single core (it reads half as many files at a time as there are cores). Its one-thread point therefore runs one search thread pinned to two cores.
- **Reported:** wall time, speed-up over one thread, parallel efficiency, CPU time and peak memory per thread count. The 16-thread point serves as the workstation comparison.

### 4.4 Comparison engines

**Principle:** same search space, each engine's own algorithm.
- **Same as ProSE:** every engine searches exactly the same database files as ProSE (the plain target-decoy FASTA for counts and timings, the entrapment FASTAs for the FDP; section 3), with the settings of the ProSE parameter file of the dataset (section 4.1) translated to the engine. These settings are:
  - enzyme, missed cleavages, peptide length and mass. ProSE bounds the singly protonated mass [M+H]+ (`peptide:min_mass`, `max_mass`), Sage and MSFragger the neutral mass, so the driver passes ProSE's bounds less one proton (1.007276 Da; since 2026-11-12). Before, Sage and MSFragger searched up to 1 Da heavier peptides at both bounds: 0.01–0.05% of the peptides of the immunopeptidomics search spaces; the tryptic bounds (100 and 9,000 Da) cut no peptide of 7–40 residues.
  - fixed and variable modifications, and their maximum
  - the configured precursor and fragment tolerances, as ± half-widths in all three engines (observed minus theoretical mass within ± the tolerance) (checked against the sources and on the mass errors of the decoy PSMs, 2026-11-12); all parameter files are symmetric. The calibrations of ProSE and MSFragger then change the fragment tolerance per search, MSFragger's also beyond the configured value (below).
  - charges and isotope errors
  - the minimum number of matched fragment ions, 4 (Sage `min_matched_peaks`, MSFragger `min_matched_fragments`; both have 4 as default, and the driver passes the value of the parameter file; section 4.1). The value is the same, the criterion not quite: Sage and MSFragger require it of the scored PSM, ProSE of the candidates of its fragment index, which holds no b1, b2, y1 and y2 ions. So ProSE PSMs can end with fewer matched ions: on `astral250pg_A2` 155 of 1,297 top hits, 21 of them accepted (checked 2026-11-12).
- **Translated, not copied:** the values of the parameter file are written in each engine's convention. Example: the isotope errors (below).
- **Engine defaults:** the scoring, peak processing and rescoring of each engine stay at its defaults. The engines are compared, not search spaces.
  - **Mass calibration:** each engine runs its own default calibration (decided 2026-11-12, section 5). The three do different things, and the supplement measures what each one changes (below).
    - **ProSE** measures the mass errors in a calibration pass over the 10% most intense spectra, corrects the m/z per tenth of the run (`recalibrate offset`) and searches with the fragment tolerance |offset| + 4σ of the remaining errors, between 5 ppm (0.01 Da) and the configured tolerance. A tolerance that covers less than 95% of the matched fragment peaks is not used, and the configured one is kept (`Search:calibration`, section 4.1). The precursor window stays as configured. ProSE calibrates every search anew: on `astral250pg_A2` 11.38 ppm instead of 20 ppm with the plain database, 11.48 ppm with entrapment s1.
    - **MSFragger** runs `calibrate_mass 2`: mass calibration, then a search over its own settings on the run: the fragment tolerance from a grid (5–50 ppm; for a tolerance in Da, 150–500 ppm) and the peak processing (number of peaks, minimum intensity ratio, intensity transformation). The chosen tolerance can exceed the configured one, and a tolerance in Da is replaced by one in ppm. On `astral250pg_A2` it chose 10 ppm with the plain database and 7, 10 and 20 ppm with entrapment s1–s3. In the pilot of 2026-11-12: 10–20 ppm on the 20 ppm files, 150–500 ppm on the 0.5 Da ion-trap files (500 ppm is ±1.0 Da at m/z 2,000), 20–25 ppm on the 0.02 Da immunopeptidomics files. As it chooses per search, its counts (plain database) and its FDP (entrapment databases) can come from different settings.
    - **Sage** does not calibrate and searches with the configured tolerances; its LDA rescoring has the precursor mass error as a feature.
    - Corrected on 2026-11-12: this section said before that every engine calibrates "within the same configured tolerances", which does not hold for MSFragger.
  - **ProSE defaults without a counterpart in the other engines** (checked 2026-11-12; documented, not changed):
    - Percolator rescores the two best hits of each spectrum (`Search:rescoring:top_hits 2`), so the rescoring can replace a top hit by the runner-up. Sage's LDA and MSFragger's Percolator see one hit per spectrum (`report_psms 1`, `output_report_topN 1`).
    - No minimum number of peaks per spectrum. Sage and MSFragger skip spectra with fewer than 15 peaks (`min_peaks`, `minimum_peaks`). On `astral250pg_A2` such spectra gave 12 of ProSE's 926 accepted PSMs (21 when only the peaks in Sage's fragment range of 150–2,000 m/z are counted; ProSE's own q-values, before the PSM level of 2026-11-12).
    - Self-trained fragment-ion priors (`Search:annotate:self_trained_ion_priors true`): fragment-ion likelihoods learned from the confident PSMs of the run itself, cross-validated over two halves of the spectra, as Percolator features. Like Sage's retention-time model (below), they are trained on the search itself, not an external predictor, so they stay on.
  - **Retention time in Sage's rescoring:** Sage's `predict_rt` (default true) fits a retention-time model on the confident PSMs (1% FDR) of the search itself and uses the deviation as a rescoring feature: per run in the per-file searches; in a search of several files (the replicates of an immunopeptidomics sample, section 4.2) one model on the retention times of all files after aligning them (Sage 0.14.7, `sage-cli/src/main.rs`, `ml/retention_model.rs`). It is not an external predictor like MSBooster or PeptDeep (below), so it stays on.
- **Counting:** the same for all engines (section 4.2), including the entrapment FDP with `EntrapmentEvaluator`.

| Engine | Datasets | Rescoring and q-values |
|---|---|---|
| ProSE | all | in-process Percolator (default) |
| Sage 0.14.7 | all except the electron-based runs (PXD011695 ETD, EThcD, ETciD, AI-ETD; PXD065289) | its built-in rescoring (LDA) |
| MSFragger 4.4.1 | all | Percolator 3.09 (the release of the external control, section 4.2) with the options of the FragPipe default workflow (`--no-terminate --post-processing-tdc`), but without `--only-psms`, so that Percolator's own peptide-level q-values are kept for comparison (the count computes its own, section 4.2); **without MSBooster** |

**Differences in the search space that remain** (checked against the sources on 2026-11-10):
- **Electron-based runs:** ProSE scores spectra recorded as electron-activated with b, y, c and z+1 ions (`Search:ions:by_activation`). MSFragger gets `fragment_ion_series = b,y,c,z`, as in FragPipe's hybrid workflows. Sage is not run there (section 1).
- **N-terminal methionine:** ProSE and MSFragger also search protein N-terminal peptides without the initial methionine (`peptide:clip_nterm_methionine`, `clip_nTerm_M`). Sage 0.14.7 has no such option, so it lacks these peptides.
- **Isotope errors:** −2…1 in all parameter files. The tryptic files set them; the immunopeptidomics files keep the ProSE default, which is −2…1 in the frozen build (−1…1 before 2026-11-02).
  - **Conventions:** ProSE adds the isotope error to the observed mass (−1 finds a peptide whose first 13C peak was selected as the precursor). Sage and MSFragger count observed minus theoretical mass, so the driver negates the range: ProSE −2…1 is `isotope_errors [-1, 2]` for Sage and `isotope_error -1/0/1/2` for MSFragger. All three search the same precursors: up to two 13C spacings above the monoisotopic mass and one below.
  - **Fixed on 2026-11-11:** before, the driver passed −2…1 unchanged, so Sage and MSFragger searched observed − theoretical −2…+1 while ProSE searched −1…+2 (section 5).
- **Charge range:** every engine searches every spectrum at its recorded charge (section 4.1).
- **Sage version string:** the binary of release v0.14.7 reports `sage 0.14.6`.
- **MSFragger parameter file:** the driver writes the settings over the defaults of `MSFragger --config closed`, and removes its default variable modifications (N-terminal acetylation among them).

**Without predictions in the main comparison:** MSBooster adds features from predicted spectra and retention times. ProSE does not use predictions by default (`Search:peptdeep:enable false`), so the main comparison runs both without.

**Supplement: comparison with predictions.**
- **MSFragger + MSBooster** against **ProSE + PeptDeep**, with the same counting.
- **Datasets:** the HCD datasets: HF-X, Astral, Lumos LFQ, TMTpro, timsTOF, iPRG2015, set S1 and the 250 pg runs. The prediction models of both are trained on HCD-type spectra, so the ion-trap CID, ETD and immunopeptidomics data are left out.
- **ProSE + PeptDeep:** `-Search:peptdeep:enable true`, with the models shipped with ProSE. This needs an OpenMS build with ONNX Runtime (`WITH_ONNX=ON`).
- **Instrument setting:** `Search:peptdeep:instrument` is set to match the data: `QE` for Q Exactive, HF-X and Exploris, `Lumos` for Lumos, `ThermoTOF` (AlphaPeptDeep's instrument class of the Astral) for Astral, `timsTOF` for timsTOF. The setting used is recorded per dataset.

**Supplement: mass calibration** (decided 2026-11-12). The main comparison runs each engine's default calibration (above), and no setting is neutral: calibration off for all would cost MSFragger about as much as the defaults cost Sage, which does not calibrate.
- **Why:** a check on `astral250pg_A2` (2026-11-12, 4 threads; PSMs and peptides at 1% with the plain database, PSMs in the entrapment searches as the mean over s1–s3):

  | Arm | PSMs | Peptides | PSMs, entrapment |
  |---|---|---|---|
  | ProSE, default (11.38 ppm) | 916 | 779 | 701 |
  | ProSE, calibration off (20 ppm) | 809 | 778 | 802 |
  | MSFragger, `calibrate_mass 2` (default) | 1,326 | 1,276 | 1,023 |
  | MSFragger, `calibrate_mass 1` | 1,171 | 1,139 | 1,003 |
  | MSFragger, `calibrate_mass 0` | 1,077 | 1,046 | 784 |
  | Sage, default (20 ppm) | 1,002 | 1,015 | 1,079 |
  | Sage, 11.4 ppm (ProSE's tolerance) | 1,271 | 1,245 | 1,195 |

  - The file is small (6,024 MS2 spectra), so differences below about 15% are not interpretable there: ProSE with only the m/z correction (934 PSMs) and with only the narrowing (990) both lie above the default with both (916).
  - Sage at 10 ppm gave 1,125 PSMs, at 14 ppm 1,326.
- **Arms**, each next to the main arm of its engine (driver: `search --extra ... --tag ...`, section 4.5):
  - ProSE with calibration off: `-Search:calibration:enabled false` (tag `cal_off`).
  - MSFragger with calibration only, without the search over its settings (`calibrate_mass 1`, tag `cal1`), and without calibration (`calibrate_mass 0`, tag `cal0`).
  - Sage with the fragment tolerance that ProSE's calibration applied to the same file in its search against the plain database (`--prose-fragment-tol`, tag `prose_tol`), one value per file for all its databases. Where ProSE kept the configured tolerance, this arm repeats Sage's main search.
- **Files:** one per group of section 1, the files of the thread scaling: `hfx_A2`, `astral_A2`, `velos_125_R1`, `lumos_lfq_5192`, `lumos_tmt_5058`, `eclipse_tmtpro_10855`, `tims_plasma_30min`. Each against the plain database (counts) and its entrapment databases (FDP), counted as in section 4.2.
- **Reported:** the counts and the FDP of every arm next to the main arms, and the fragment tolerance each calibration chose per search (from the engine logs that the driver keeps).

### 4.5 Scripts: every number comes from a script

The benchmark is driven by scripts, so that it can be repeated with one command per stage and nobody selects files or types settings by hand.

- **Run table:** [`../benchmarks/runs.tsv`](../benchmarks/runs.tsv) has one row per run of sections 1 and 2 (92 runs): ID, set, group, download link, parameter file, databases, and the flags for the scaling files and the immunopeptidomics samples. The tables of this document and the run table must agree; the run table is what the scripts read.
- **Search settings:** the ProSE parameter files in [`params/`](params/) are the single source. The driver translates the Sage and MSFragger configurations from the values in these files, including the ProSE defaults that [`params/make_inis.py`](params/make_inis.py) does not set (for example the isotope errors −2…1 of the immunopeptidomics files and the clipping of the protein N-terminal methionine). So the three engines cannot drift apart.
  - **Translated in each engine's convention,** not copied: for example the isotope errors (section 4.4).
  - **Not translated**, each engine keeps its default: fragment m/z range, fragment charges, deisotoping (Sage's on the ion-trap data is checked on the first runs, section 5, task 6), mass calibration (its effect is the supplement of section 4.4). The minimum number of matched fragment ions is translated since 2026-11-11 (4 for all, section 4.1), the peptide mass bounds as neutral masses since 2026-11-12 (section 4.4).
- **Driver:** [`../benchmarks/bench.py`](../benchmarks/bench.py) (Linux, Python 3 standard library only), with one subcommand per stage. [`../benchmarks/README.md`](../benchmarks/README.md) has the commands in their order.

  | Stage | What it does |
  |---|---|
  | `versions` | records the version output of every tool |
  | `databases` | unpacks the databases of the run table from [`databases/`](databases/) and checks their SHA256 |
  | `fetch` | downloads the vendor files of the run table and checks every file, also one already there, against the SHA256 in `vendor.sha256` next to the run table |
  | `convert` | converts them to mzML with `FileConverter` (section 4.0), keeps its output as the record of the conversion, and records the SHA256 of every mzML |
  | `search` | runs one engine on every run against the plain target-decoy, the entrapment or the reference databases; with `--timed`, one discarded run and three repetitions under `/usr/bin/time -v` |
  | `count` | computes the PSM- and peptide-level q-values the same way for every engine, writes each result as idXML and runs `EntrapmentEvaluator` on it: counts with the plain target-decoy database, FDP with the entrapment databases (section 4.2) |
  | `collect` | joins all counts into one table |
  | `batch` | the batch arm of section 4.3 (groups of at least two files) |
  | `scaling` | the thread-scaling grid of section 4.3, pinned, with the time limit |

- **Vendor checksums:** [`../benchmarks/vendor.sha256`](../benchmarks/vendor.sha256) holds the SHA256 of all 92 vendor files of the 92 runs, computed on 2026-11-11 from copies that were checked against the sources:
  - 80 files match the SHA-1 that PRIDE publishes: in the project's `checksum.txt` (PXD053748, PXD058436, PXD065289, PXD070049; 37 files) or through the PRIDE Archive API (PXD007683, PXD010981, PXD011695, PXD019643, PXD042233; 40 files), and the 3 ProteoBench Astral copies against PXD070049.
  - The 12 raw files without a published checksum (PXD001819: 6, PXD054559: 3, ProteoBench HF-X copies: 3) were downloaded twice, with the same SHA256.
  - A right size alone does not prove a good download: one file of PXD058436 had the right size, but 196 wrong bytes and a failing gzip test. `urllib` only notices a download that ends short.
- **Records:** every timed invocation appends one line to `timings.tsv` (engine, benchmark, run, database, stage, threads, repetition, wall time, CPU time, peak memory, exit status); repetition 0 is the discarded run. Every stage writes its exact command lines to `commands.log`, and `--dry-run` prints them without running anything.
- **Stages of ProSE:** every ProSE search also writes its end-of-search report (`-summary_out`), which holds the times of its stages.
- **Engine logs:** since 2026-11-12 the output of every engine step is kept next to its results (`<stage>.log`, timed runs `<stage>.r<repetition>.log`), for example the tolerances the calibrations chose.
- **Further arms:** `search --extra '<settings>' --tag <name>` runs a further arm into its own result folder (`per_file_<name>`; `--extra` without `--tag` is refused). The settings are ProSE options (for example the standard-mode arm of section 4.1, or ProSE + PeptDeep per instrument, section 4.4), Sage configuration keys as `key=JSON` (`deisotope=false`; the driver refuses a key that Sage 0.14.7 does not know, as Sage would ignore it) or MSFragger parameters as `key=value` (`calibrate_mass=0`; only keys of its parameter file). The Sage and MSFragger settings are logged in `commands.log`. `--prose-fragment-tol` gives Sage the fragment tolerance of ProSE's calibration (the calibration supplement, section 4.4).
- **Not scripted:** the external Percolator 3.09 control (section 4.2) and MSFragger + MSBooster (section 4.4).
- **Smoke test:** [`../benchmarks/smoke/`](../benchmarks/smoke/) has its own run table: three small BSA runs from the OpenMS examples (LTQ Orbitrap XL, ion-trap CID, 10–14 MB each; fetched from OpenMS commit `4e7455e4`, the last that changed them, and checked against `smoke/vendor.sha256`) against 680 proteins of `hye` (the contaminants and 300 yeast proteins), with a plain and an entrapment database. It exercises every stage in minutes. The sample is one protein, so its identification numbers mean nothing.
- **Checked against the sources (2026-11-10):** the options of ProSE and `EntrapmentEvaluator` (OpenMS develop), the configuration of Sage 0.14.7, and the MSFragger parameter names and non-specific enzyme (FragPipe workflows).
- **Tested (2026-11-10)** on the smoke test with Sage 0.14.7, on a 20-core Linux machine:
  - **Run:** `databases`, `fetch`, `search` (timed and untimed, plain and entrapment databases), `batch`, `scaling` with pinning, `count` up to the idXML file, and `collect`. Sage accepted the configurations made from the parameter files of then, the unspecific ones included.
  - **Time limit:** a run over the limit is stopped together with its child processes and recorded.
  - **Found and fixed by the test:** Sage aborts on a single core (section 4.3), and a run over the limit in the discarded repetition left no record.
- **Tested (2026-11-11)** with the frozen OpenMS build (a native copy of the Docker image), Sage 0.14.7, MSFragger 4.4.1 and Percolator 3.09 (WSL2, Ubuntu 24.04, 20 cores; prose-paper `5c5dd5f`):
  - **Smoke test:** every command of the README in its order, with all three engines; every step exit 0. Its BSA files reach no q ≤ 0.01 with (D + 1) / T, so it runs `count` and `EntrapmentEvaluator` end to end with zero counts.
  - **Two real files through every stage, all three engines:** `astral250pg_A2` and `ultra2_A2` (timsTOF Ultra 2, MS2-only mzML); every step exit 0. `EntrapmentEvaluator` reads the idXML that the driver writes and accepts a database without entrapment proteins.
  - **After the changes of 2026-11-11** (section 5): both files searched and counted again with all three engines (section 4.2 has the counts).
- **Tested (2026-11-12)** after the changes of that day (peptide mass bounds, MSFragger's window translation, `--extra` for all engines, `--prose-fragment-tol`, engine logs; section 5): `search` and `count` of `astral250pg_A2` with the plain and the s1 entrapment database, with all three engines and the four arms of the calibration supplement (section 4.4); every step exit 0.
  - The main arms give the same counts as before (ProSE 916 PSMs and 779 peptides, Sage 1,002 and 1,015, MSFragger 1,326 and 1,276): the tryptic mass bounds cut no peptide.
  - The arms give the numbers of the table in section 4.4 (Sage's arm: 11.38 ppm read from ProSE's log, 1,270 PSMs and 1,246 peptides).
  - Each search folder holds its engine logs, for example MSFragger's choice of 10 ppm (plain database) and 7 ppm (s1).

## 5. Decisions and remaining tasks

**Decisions** (2026-10-23):
- **Rescoring:** ProSE's in-process Percolator is counted. Percolator 3.09 as an external step is the control in the supplement.
- **Input format:** mzML for every dataset and every engine. Every vendor file is converted by us with OpenMS `FileConverter`, with vendor peak picking for Thermo and without the Bruker SDK for timsTOF (section 4.0). The deposited mzML files are reference only.
- **PXD065289:** the five trypsin ETciD fractions of section 2.1.
- **Immunopeptidomics:** three donor–tissue pairs on both instruments (DN05 thyroid, DN13 tongue, DN14 bladder), both classes, all three technical replicates: 36 runs (section 2.4).
- **Comparison engines:** Sage and MSFragger on every dataset. Versions in section 1. (Changed for Sage on 2026-11-10, below.)
- **Held-out set:** all datasets of section 2, including the independent UPS1 control (section 2.6).
- **PXD070049 extensions:** the three human-only runs, as supplementary set S1 (natural entrapment, section 2.2). The three 250 pg counterparts of the Astral files, as the low-input set (section 2.5).
- **PXD058436 database:** `human_sp.fasta` (UniProt 2026_01).
- **Parameters:** one ProSE parameter file per acquisition setting (section 4.1).
- **ProSE version:** OpenMS develop `fbb25191d7`, frozen on 2026-11-11, tag `prose-benchmark-2026-11` (section 4.1).
- **Counting:** PSMs and peptides at q ≤ 0.01.
  - In-process Percolator: one run (fixed seed).
  - External control: mean over three seeds.
  - Entrapment FDP: mean ± SD over the three database realisations (section 4.2).
- **Speed and memory:** measured, with the protocol of section 4.3.
- **Comparison engines:** same search space and database as ProSE, each engine's own algorithm. MSFragger with Percolator, without MSBooster (section 4.4).
- **Supplement with predictions:** MSFragger + MSBooster against ProSE + PeptDeep (section 4.4).
- ***Arabidopsis* reference:** HF-X, Astral and TMTpro, not timsTOF (section 4.2).

**Decisions** (2026-11-10):
- **Database for counts and timings:** the plain target-decoy database. Entrapment searches are a separate arm and give only the FDP (sections 3 and 4.2).
- **Counting:** PSMs at 1% PSM-level FDR and unique peptides at 1% peptide-level FDR; the entrapment FDP at both levels; no protein level (section 4.2).
- **Thread scaling:** all three engines on the full grid of 11 thread counts and 9 files (section 4.3).
- **Timing:** per file, plus one batch run per group, with the stages reported separately where the engines log them (section 4.3).
- **Held-out additions:** the timsTOF Ultra 2 HYE runs of PXD070049 (section 2.7) and HeLa HCD runs of PXD042233 on an Exploris 480 and a Q Exactive HF (section 2.8).
- **Large search spaces:** immunopeptidomics only. No phospho, metaproteomics, semi-tryptic or open search.
- **Scripts:** the benchmark is run by scripts from one run table (section 4.5).
- **Sage:** version 0.14.7, the last stable release; not run on the electron-based runs (sections 1 and 4.4).
- **Counting tool:** `EntrapmentEvaluator` for all three engines; Sage and MSFragger results are converted to idXML (section 4.2). Since 2026-11-11 the results of all three engines (below).
- **Peptide level:** each engine's own peptide-level q-values (section 4.2). Replaced on 2026-11-11 (below).
- **Set S2:** the three human-only timsTOF Ultra 2 runs, as natural entrapment on timsTOF (section 2.7).
- **Selected files of sections 2.7 and 2.8:** adopted; acquisition mode and instruments checked (sections 2.7 and 2.8).
- **Thread scaling, time limit:** 24 hours of wall time per run (section 4.3).
- **Immunopeptidomics isotope errors:** stay at the ProSE default, for all engines (section 4.4). Then −1…1; with the frozen build −2…1 (2026-11-11, below).
- **Charge range:** every engine searches every spectrum at its recorded charge; the ProSE parameter files set `precursor:recorded_charge_outside_range` to `search` (section 4.1).
- **Plain target-decoy databases:** derived from the entrapment databases, built and checked (section 3).
- **Thread scaling:** from 192 threads down; lower thread counts are not run after a run over the limit; Sage's one-thread point on two cores (section 4.3).

**Decisions** (2026-11-11):
- **Decoys:** all three engines search the same decoys, the ones ProSE generates by default; every database was rebuilt with them, targets and entrapment unchanged (section 3). ProSE reads them from the database with `decoys auto`, so all engines search one file (section 4.1).
- **Immunopeptidomics isotope errors:** −2…1, the default of the frozen ProSE, for all engines (section 4.4).
- **Settings audit before the real benchmark** (no engine may be disadvantaged): each equal setting is checked in the driver's output for all parameter files. Decided from it:
  - **Isotope errors, sign:** the driver translates ProSE's convention into that of Sage and MSFragger (−2…1 becomes −1…+2 there). Before, they searched the mirrored range (section 4.4).
  - **Minimum matched fragment ions:** 4 for all engines, the default of Sage and MSFragger; set in the ProSE parameter files and passed to both (sections 4.1 and 4.4).
  - **Peptide level:** the driver computes the peptide-level q-values the same way for all engines, from each engine's PSMs and final score (section 4.2). It replaces the engines' own peptide-level q-values, which are defined differently.
  - **Mass calibration:** each engine's own default, within the same tolerances; documented, not changed (section 4.4). Corrected on 2026-11-12: MSFragger's calibration leaves the configured tolerances (below).
  - **Sage's retention-time model:** stays on (default); it is fitted on the PSMs of the search itself, not an external predictor (section 4.4).

**Decisions** (2026-11-12), from a second check of the counting (no engine may be disadvantaged):
- **PSM level:** the driver computes the PSM-level q-values the same way for all engines, (D + 1) / T on each engine's final score (section 4.2). ProSE's own, (D + π0) / T, accepted about 1% more PSMs.
- **ProSE's pooled samples:** ranked by Percolator's PEP, because its inputs keep separate Percolator models; ranking by score cost it 0.17% of the peptides (section 4.2).

**Decisions** (2026-11-12), from a check of the search settings (tolerances, calibration, other settings; no engine may be disadvantaged):
- **Tolerances:** the configured windows are equivalent in all three engines (± half-widths; section 4.4). The driver's translation for MSFragger was mirrored for asymmetric windows; no parameter file has one, so no search was affected. Fixed.
- **Mass calibration:** each engine keeps its default calibration in the main comparison. They differ (MSFragger chooses its fragment tolerance per search, also beyond the configured one and in ppm for a tolerance in Da; Sage does not calibrate), so a supplement measures each engine with and without it, on one file per group (section 4.4).
- **Peptide mass bounds:** ProSE's bound the [M+H]+ mass, Sage's and MSFragger's the neutral mass; the driver passes the bounds less one proton (section 4.4).
- **ProSE defaults without a counterpart** (two hits per spectrum in the rescoring, no minimum number of peaks, self-trained fragment-ion priors): documented, not changed (section 4.4).

**Open decisions:**
- **Immunopeptidomics, true error rate:** how FDR control is checked on the unspecific searches (section 3.3 has no entrapment there). Owner: Jonas Scheid, who provides the design.

**Remaining tasks, in this order** (hand-off of 2026-11-10; the commands are in [`../benchmarks/README.md`](../benchmarks/README.md)):
1. **Peptide-level q-value in OpenMS:** done. [OpenMS/OpenMS#10877](https://github.com/OpenMS/OpenMS/pull/10877) is merged (2026-11-11, `1a3c037a`; it replaced OpenMS/OpenMS#10871): ProSE writes `peptide q-value` with one peptide definition, per file and in `-out_merged` across all inputs (section 4.2). The formula (D + 1) / T came with [OpenMS/OpenMS#10874](https://github.com/OpenMS/OpenMS/pull/10874) (`db4bd541`). Since 2026-11-11 the driver computes the peptide level itself for all engines and does not count on the value; on single files the two nearly agree (section 4.2).
2. **ProSE version:** frozen at OpenMS develop `fbb25191d7` (2026-11-11; it contains OpenMS/OpenMS#10713 and task 1; section 4.1). Built on 2026-11-11 (Docker image of OpenMS's `dockerfiles/Dockerfile`); the parameter files are written with it, and its version string is in section 4.1. Still to do: the same commit built on the benchmark nodes, for the timed runs.
3. **Other tools:** Sage 0.14.7, MSFragger 4.4.1 and Percolator 3.09, installed and run on 2026-11-11 (sections 1 and 4.5). Still to do: on the benchmark nodes, with the output of the `versions` stage there.
4. **Smoke test:** run with all three engines on 2026-11-11 (section 4.5). Still to do: again on the benchmark nodes, as a check of their tools and paths.
5. **One real file through every stage:** `astral250pg_A2` (159 MB), and `ultra2_A2` (timsTOF): done on 2026-11-11 (section 4.5). Still to do: again on the benchmark nodes.
6. **Checks on the first runs:**
   - Sage deisotopes every MS2 spectrum by default (`deisotope` true in the code of 0.14.7), with a fixed 10 ppm window, also the 0.5 Da ion-trap spectra: check that this does not cost it identifications there.
   - MSFragger searches the timsTOF precursors without a charge (section 4.0) at the charges of the parameter file, as ProSE and Sage do.
   - The driver's pooled peptide count across the replicates runs on the immunopeptidomics results of all three engines (section 4.2; so far tested on a two-run ProSE `-out_merged` result only).
   - How each engine labels a peptide that is both a target and a decoy peptide (1.8% of the decoy peptides, section 3.2).
   - MSFragger's `z` ions on the electron-based runs: z• (z+1, as ProSE scores them) or y−NH3. Test: `ion_series_definitions` with z• on `pxd011695_EThcD`.
   - ProSE's precursor recalibration on PXD019643 class I (found 2026-11-12, OpenMS/OpenMS#10885): late in the run most calibration PSMs are matches to a PEG contaminant, at +10 to +13 ppm for targets and decoys alike. The per-chunk model followed them to about +10 ppm, and the correct PSMs (about 0.2 ppm) fell out of the ±5 ppm window. Fix: OpenMS/OpenMS#10886, open. A chunk where more than a quarter of the calibration PSMs are decoy hits takes the offset of its neighbours. On the 11 pilot runs it gives +22% PSMs and +23% peptides on this run, −1.2% PSMs and +0.5% peptides on PXD058436 class I, and bit-identical results on the other nine. The frozen OpenMS commit needs the fix before the immunopeptidomics numbers are used.
7. **Machines:** record RAM, OS and storage of the two nodes of section 4.3, and check on the scaling node that CPUs 0–191 are 192 different cores.
8. **Conversion:** convert all inputs (section 4.0), record converter, settings and SHA256, recount the MS2 spectra, and update the tables of sections 1 and 2.
9. **Not scripted yet:** the external Percolator control and MSFragger + MSBooster (section 4.5).
10. **Calibration supplement:** the arms of section 4.4 on its seven files, after the main searches of these files (the Sage arm reads ProSE's log of its main search).
