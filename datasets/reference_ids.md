# Reference identification numbers per run (`reference_ids.tsv`)

Compiled 2026-11-11 and rechecked independently on 2026-11-12 (see the last section), for the runs of [`../benchmarks/runs.tsv`](../benchmarks/runs.tsv) (92 runs, 26 groups).

**Purpose:** a plausibility check of our search parameters. Our counts should land roughly in the published range. A large gap points to a parameter error.

**Rules followed:**
- Every number is recorded as published, or counted exactly from a deposited result file. Nothing is estimated or read off a plot.
- Where no number exists, the row has an empty value and the reason.
- Where a source reports several engines on the same files, all of them are in the table.
- Earlier ProSE numbers of [DATASETS.md](DATASETS.md) are included only as context. Their `origin` is "earlier ProSE, context only".

## How to read the table

One row per run (or per sample, or per union of runs), source, engine and level. The value is always a count of targets.

| Column | Content |
|---|---|
| `run_ids` | run id(s) of `runs.tsv`; several ids separated by `;` |
| `group` | group of `runs.tsv` |
| `dataset` | project and publication |
| `scope` | per run, per sample (immunopeptidomics: replicates pooled), union or mean over more runs than ours, or summed |
| `value` | the number; empty if none was found |
| `level` | what is counted: PSMs, peptides (unmodified? I=L?), precursors, spectral-count sums |
| `fdr` | FDR level and method of the source |
| `engine` | engine, version, rescoring |
| `database` | the source's database, and ours |
| `settings` | notable search settings |
| `source` | DOI or URL, table or file, column |
| `origin` | see below |
| `comparability` | same files? same database? same level and FDR? what pushes the value up or down against ours |
| `notes` | further values (peptides, proteins, spectra) and how the value was obtained |

**`origin`:**
- **published:** the number is printed in a paper, on a project page or in a public results table (HLA Ligand Atlas), or is in a per-run report the authors deposited.
- **published (ProteoBench results):** ProteoBench's public metric, a union over 6 runs.
- **counted from deposited results:** counted here from result files the authors deposited (PRIDE, Zenodo).
- **counted from a ProteoBench submission:** counted here from the tool output a submitter uploaded to ProteoBench.
- **counted from a published supplementary table:** sums over a supplementary table.
- **published third-party reanalysis:** quantms reanalysis reports (PXD007683).
- **earlier ProSE, context only:** ProSE numbers listed in DATASETS.md, from older builds and partly other databases.
- **no reference found:** empty value, with the reason.

**Our counting** (DATASETS.md 4.2):
- PSMs: top hit per spectrum at PSM q ≤ 0.01.
- Peptides: unique unmodified sequences, I = L, at peptide-level q ≤ 0.01.
- Plain target-decoy database, per file, no protein filter.
- PSM q-values: computed by the driver for all engines, (D + 1) / T on each engine's final score (DATASETS.md 4.2, decided 2026-11-12). ProSE's own, (D + π0) / T, would give about 1% more PSMs.
- Immunopeptidomics: unique peptides per sample, with the replicates searched together.

**Main differences to watch** when comparing:
- **Chimeric searches** (FragPipe DDA+, DeMix, Sage with `chimera`, MaxQuant second peptides) give more than one PSM per spectrum.
- **Protein-level filters** (FragPipe, quantms, Gygi LDA) remove PSMs.
- **Rescoring** with external predictors of spectra or retention times (MSBooster, MS2Rescore, PEAKS, MHCquant2) raises counts. Our arms rescore without them: Sage with its built-in LDA (plus its own RT model, `predict_rt`, fitted on the search's own PSMs), MSFragger and ProSE with Percolator. Results without any rescoring are therefore below our arms, not like them.
- **FDR over several runs** differs from our per-file FDR: PXD065289 (20 fractions), PXD053748 (6 runs), the deposited Mascot results of PXD070049 (one merged search of 9 runs), and the ProteoBench submissions, which analyse their module's 6 runs in one project (MaxQuant, for example, controls the FDR over all of them).

## Overview per group

"Best reference" is the closest to our counting. Values are listed in the run order of `runs.tsv`.

| Group (runs) | Best reference | How comparable | Gaps |
|---|---|---|---|
| `velos` (3) | Ramus 2016 Data in Brief, Suppl. Table 1. Sums of protein spectral counts for 5000_R2 / 25000_R3 by four workflows: MaxQuant 1.3.0.5 14,736 / 14,728; Mascot + MFPaQ 12,855 / 12,559; IRMa 9,812 / 9,627; Scaffold 6,779 / 7,016 | weak: protein-level spectral-count sums, not PSMs; FDR differs per workflow; run mapping assumed; our database (`hy_td`, 27,488 targets) is about 3.5 times theirs | `velos_125_R1`: nothing. No PSM count for any run (Ramus 2016 full text not reachable) |
| `hfx` (3) | ProteoBench submissions counted per run. FragPipe 22.0 at 20 ppm / 20 ppm: 68,294 / 67,225 / 72,281 PSMs. MaxQuant 2.5.1.0: 41,061 / 40,442 / 43,161. Sage 0.15 via i2MassChroQ: 46,620 / 45,988 / 49,407 precursors | same files; each submission's FASTA is named in `database`. FragPipe with MSBooster and a protein filter, so above an MSFragger arm without them | no paper; no per-run Sage PSM count (only precursors) |
| `astral` (3) | Synergy paper (JPR 2026), per file, without rescoring: Sage 0.14.6 30,977 / 32,352 / 32,527; MS-GF+ 23,560 / 24,915 / 24,632; X!Tandem 19,530 / 19,717 / 19,980 PSMs. ProteoBench FragPipe 23: 48,883 / 50,983 / 50,700 | same files, per-file FDR; Swiss-Prot HYE instead of the ProteoBench FASTA; without rescoring, so below our arms, which rescore (the mokapot condition is the closer analogue) | none |
| `lumos_lfq` (3) | quantms reanalysis: 49,573 / 49,928 / 49,130 PSMs of quantified peptides | MS-GF+ and Comet combined, with MS2Rescore; final FDR levels not shown | no per-run value from the original authors |
| `lumos_tmt` (3) | quantms reanalysis: 13,935 / 14,683 / 15,630 | as above | as above |
| `eclipse_tmtpro` (3) | Zuniga 2024, Comet + LDA (deposited mzIdentML): 9,905 / 9,244 / 9,440 PSMs | much larger database (isoforms + TrEMBL); PSM and protein filter | one engine only |
| `tims_plasma` (2) | TIMS²Rescore deposit, Sage 0.14.3: 13,278 / 14,547 PSMs; rescored: 14,593 / 16,236 | q-values over 6 runs together; chimera on | none |
| `pxd011695_*` (5 groups, 1 run each) | Deposited COMPASS/OMSSA tables, HCD / EThcD / ETciD / ETD / AI-ETD: 63,686 / 12,292 / 10,436 / 6,873 / 12,921 PSMs | E-value + ppm filter at 1%; 3 missed cleavages; the searched database was probably smaller than the deposited one | one engine only; the paper's Table S1 not retrieved |
| `pxd065289_etcid` (5) | Deposited FragPipe 22 / MSFragger 4.1 (`ETciD.zip`), c, z ions: 10,780 / 11,560 / 10,142 / 8,239 / 9,023 PSMs (also a, b, c, x, y, z and b, y) | FDR over all 20 fractions, plus a protein filter | the paper gives figures only |
| `astral_s1` (3) | Deposited Mascot 3.1.0 + Percolator: 16,978 / 16,872 / 16,932 PSMs | cut at 1% peptide FDR, which is about 0.5% PSM FDR; one merged search of 9 runs; 1 missed cleavage | only Mascot |
| `pxd042233_lumos_cid` (2) | MaxQuant 1.6.12.0 summary: 27,476 / 27,666 MS/MS identified; 20,599 / 20,628 peptide sequences | second peptides on; canonical + isoforms database | one engine only |
| `iprg2015` (3) | DeMix + MS-GF+ (deposited mzid): 29,033 / 27,122 / 26,074 PSMs on 25,477 / 23,775 / 23,063 spectrum IDs. OpenMS + MS-GF+: at least 18,940 / 17,924 / 17,423 spectra | DeMix is chimeric, and 2,428 / 2,314 / 2,117 of its PSMs repeat another PSM of the same spectrum; the mzTab counts are lower bounds | the study's own IDs are not public |
| `pxd058436_classI` / `classII` (3 + 3 samples) | Deposited per-sample tables of MHCquant2, FragPipe and PEAKS (unique peptides, replicates pooled) | same files, same level; other Swiss-Prot release; all three use predicted features | none |
| `pxd019643_classI` / `classII` (3 + 3 samples) | HLA Ligand Atlas 2020.12 (MHCquant 1.5.1): 3,828 / 1,815 / 850 (I) and 1,199 / 2,577 / 2,492 (II) peptides | same files, same targets, same level; each published count includes 0–4 decoy-only sequences | one engine only |
| `astral_250pg` (3) | Synergy paper, without rescoring, for B1 / B3: Sage 1,609 / 1,575; X!Tandem 1,045 / 840; MS-GF+ 786 / 866 PSMs | per-file FDR; at 250 pg Sage's rescoring had no effect | `astral250pg_A2`: no published value (its results exist only as a pickle file, not opened) |
| `ups1_control` (3) | As `velos`, for 500amol_R2 / 12500amol_R2: MaxQuant 14,621 / 14,993; MFPaQ 13,028 / 12,823; IRMa 9,735 / 9,835; Scaffold 6,971 / 7,026 | weak, as for `velos` | `UPS1_2500amol_R3`: nothing |
| `ultra2_hye` (3) | Synergy paper, without rescoring: Sage 25,386 / 26,115 / 26,183; X!Tandem 23,234 / 23,909 / 24,111; MS-GF+ 15,870 / 16,334 / 16,828 PSMs | per-file FDR; Swiss-Prot HYE | none |
| `ultra2_s2` (3) | Deposited Mascot 3.1.0 + Percolator: 21,909 / 21,893 / 22,071 PSMs | as `astral_s1` | only Mascot |
| `hela_exploris480` (3) | MaxQuant 1.6.12.0: 54,780 / 55,295 / 55,213 MS/MS identified; 39,719 / 38,195 / 41,537 peptide sequences | as `pxd042233_lumos_cid` | one engine only |
| `hela_qe_hf` (3) | MaxQuant 1.6.12.0: 43,409 / 43,372 / 43,296; 32,457 / 31,068 / 34,085 | as above | one engine only |

## Notes per dataset

### PXD001819 (`velos`, `ups1_control`; Ramus et al., J Proteomics 2016)

- **Paper:** the full text is not open access and was not read (the HAL copy is behind bot protection).
- **Data in Brief companion (PMC4706616):** its Supplementary Table 1 holds per-protein spectral counts per run for three pairwise comparisons, by four workflows: Mascot + MFPaQ, MaxQuant 1.3.0.5, Mascot + IRMa-hEIDI, Mascot + Scaffold.
- **Values in the table:** the per-run sum of spectral counts, counted by a helper agent and re-counted independently on 2026-11-12, with the same result. The number of proteins is in the notes.
  - This is not a PSM count: a spectrum shared between protein groups can count more than once.
  - The FDR differs per workflow: MFPaQ uses 5% peptide FDR plus 1% protein FDR, Scaffold < 5% protein FDR.
- **Our database:** `hy_td.fasta` (27,488 human + yeast targets), about 3.5 times the 7,846 entries searched here. `hy_velos_natural_td.fasta` splits the same proteins into 7,152 targets and 20,336 entrapment entries and gives only the FDP.
- **Run mapping:** assumed, not documented. Replicate *n* = R*n*; the spike level comes from the comparison block on each workflow's sheet. In every block the lower-spike column has the lower UPS1 spectral counts.
- **Mascot version:** the headers of the deposited WF1-4-5 Mascot `.dat` files say Mascot 2.3.01.01 and `S_cerevisiae_20121108.fasta` with 7,848 sequences (yeast + UPS). The Data in Brief methods say Mascot 2.4.
- **Gaps:**
  - `velos_125_R1` and `UPS1_2500amol_R3` are not in the table.
  - The deposited WF3-8 Mascot `.dat` files for these two runs hold unfiltered results only (Mascot 2.4.1; 28,137 and 28,562 queries; a 15,695-sequence target-decoy database), no FDR-filtered count.

### HF-X (`hfx`, ProteoBench Module 2, PXD028735)

- **No paper with per-run counts:** Van Puyvelde 2022 gives only "approximately 40,000" peptide sequences over nine runs, which is not usable.
- **ProteoBench's published metric:** per submission, only the number of precursor ions quantified in ≥ 1 of the module's 6 runs (`results.1.nr_feature`). All 46 public submissions are in the table as union rows: MaxQuant 15, FragPipe 7, i2MassChroQ with X!Tandem 6 or Sage 4, AlphaPept 4, WOMBAT 5, Mascot 2, Sage 1, PEAKS 1, Comet 1.
- **Per-run values counted here** from the tool output that the submitters uploaded (`<hash>_data.zip`):
  - **FragPipe/MSFragger, 6 searches:**
    - PSMs = sum of the per-run `Spectral Count` in `combined_ion.tsv`.
    - Peptides = unmodified sequences (I=L) of ions with MS/MS in the run.
    - Closest to our settings: FragPipe 22.0 at 20 ppm / 20 ppm (`3bd27fcfd7…`).
  - **MaxQuant:** 2.5.1.0 (MBR off) and 1.5.3.30 (MBR on, matches excluded), from `evidence.txt`.
  - **AlphaPept 0.5.0:** distinct precursors with q ≤ 0.01. Its table can hold more than one row per precursor and run.
  - **Sage:** only through i2MassChroQ (Sage 0.15.0-alpha, MBR off, `min_matched_peaks` 6), as precursors per run. Its `sequence` column carries the modifications (it equals `ProForma`); the notes give unmodified sequences, re-counted on 2026-11-12. Sage's own submission has no per-run identification column (its `lfq.tsv` gives quantities per run, with MBR on), so per-run identifications cannot be derived from it.
- **Caveats:**
  - All FragPipe submissions use MSBooster and a 1% protein filter. Our MSFragger arm has neither, so expect it lower.
  - The DDA+ submission (`c8041832…`) is a chimeric search with 162,863 PSMs for 111,413 MS2 in `hfx_A2`. It is comparable only with a chimeric ProSE search.
  - **Search settings:** most submissions use protein N-terminal acetylation and up to 3 modifications. `main_highres.ini` has Oxidation (M) only, at most 1.
  - **MaxQuant:** its values include second peptides.
  - **Database:** each row names the FASTA the submission searched, from its uploaded parameter files, with each engine's own decoys.
    - Six submissions searched `ProteoBenchFASTA_MixedSpecies_HYE.fasta`, the file our `hye_td.fasta` is built from.
    - Most others searched `ProteoBenchFASTA_DDAQuantification.fasta` or `BenchmarkFASTAModule2_DDA.fasta`. Whether their targets equal ours was not checked; neither file is public. The parent session's second check (2026-11-12) found every protein accession reported in the 13 counted outputs among our `hye_td` targets, which fits but does not prove equality.
    - Three FragPipe searches appended contaminants. None of their outputs contain a contaminant hit.
    - For union rows without an uploaded zip, the searched file is unknown.
  - **FragPipe 22.0 with MBR off (`45486140…`)** used a precursor window of ±10 ppm, not 20 ppm.

### Astral 50 ng (`astral`) and the other PXD070049 runs (`astral_s1`, `astral_250pg`, `ultra2_hye`, `ultra2_s2`)

- **Synergy paper** (Heyndrickx et al., JPR 2026, doi:10.1021/acs.jproteome.6c00295):
  - **Search:** X!Tandem, MS-GF+ and Sage 0.14.6, each without rescoring, with mokapot, and with MS2Rescore. Every raw file separately, 1% FDR at PSM, peptide and protein level.
  - **Where the numbers are:** the paper shows only means (Fig. 2). The per-run values come from the deposited HTML reports (Zenodo 18743931), plot "Identifications at 1.0% FDR", embedded data. A helper agent extracted them; a second one re-extracted them independently on 2026-11-12, with the same result.
  - **In the table:** the PSM value in each row; peptides and proteins are in the notes.
  - **Closest to our arms:** the mokapot condition, which rescores on the engine's own features without predicted ones, as our arms do (Sage's LDA, Percolator for MSFragger and ProSE). Same files, per-file FDR. The values without rescoring are lower bounds for our arms.
  - **Database:** Swiss-Prot human/yeast/E. coli + cRAP, not the ProteoBench FASTA.
  - **Tolerances:** Astral 5 / 15 ppm, Ultra2 20 / 25 ppm.
  - **IM2Deep** (ion mobility) is used only for the timsTOF (Ultra2) data, per the paper and the deposited code.
  - **Coverage:** no Human_01–03 runs, and no report for 250 pg A_REP2.
    - That run's results are in the same Zenodo record's `pkl.zip`, as a pickle file, and the paper's 250 pg means include it.
    - The pickle was not opened, because loading a pickle runs code from the file.
  - **At 250 pg:** Sage has the same values under all three rescoring conditions, so its rescoring did not take effect there.
- **Deposited Mascot results** (`F013347_Astral.mzid`, `F013348_Ultra2.mzid`):
  - **Runs:** only the single-species runs, which are sets S1 and S2.
  - **Search:** Mascot 3.1.0 + Percolator, cut at 1% peptide-sequence FDR. The PSM FDR in the file is 0.50% / 0.56%. 1 missed cleavage, variable peptide N-terminal acetylation.
  - **One search for 9 runs:** Mascot Daemon merged the runs into one MGF (`mascot_daemon_merge.mgf`), so the FDR is over the 9 runs.
  - **Counts:** a helper agent counted the per-run values; all were re-counted independently on 2026-11-12. The 9-run totals are 106,754 (Astral file) and 134,270 (Ultra2 file).
- **ProteoBench Astral module:**
  - **Union rows:** all 9 public submissions.
  - **Per-run values counted here:** FragPipe 23.0 and 22.1, MaxQuant 2.6.7.0, i2MassChroQ + Sage 0.15.0-beta.1 (MBR off, precursors), and DIA-NN 2.6.0 run on the DDA files (precursors).
  - **Left out:** the second DIA-NN submission (`b6b29b75…`) is the same search without the MS1 filters of the first. Its parameter files are identical, and applying those filters to its report gives exactly the precursors of `300beac4…` in all 6 runs. Unfiltered it gives 96,744 / 99,977 / 98,975 precursors per run, so it has no per-run rows. Its union row is in the table.
  - **DIA-NN filters:** the uploaded report was already filtered on run and global precursor q-value, MS1 q-values and MS1 quality. It has no protein filter.
  - **DIA-NN settings:** DIA-NN searched a pre-built predicted library. Its command line (charge 2–3, 1 missed cleavage, 1 variable modification) did not limit that library: the report holds charge 1 and 4 precursors, sequences with 2 missed cleavages and peptidoforms with 2 modifications. So ProteoBench's corrected metadata (charge 1–4, 2 missed cleavages, max 2 modifications) describe the search. The `settings` cells say this.
  - **Sage:** its own submission (0.14.6) combines charge states and has no per-run identifications.
- **Gaps:**
  - `astral250pg_A2` has no published value (see Coverage).
  - Sets S1 and S2 have only Mascot.
- **Context, not a reference:** the current setup of this benchmark (after the isotope-sign fix and `min_matched_ions` 4, searched on 2026-11-11; PSM q-values computed by the driver, 2026-11-12) gives on `astral250pg_A2` ProSE 916, Sage 1,002 and MSFragger 1,326 PSMs. The first pilot run had given 668, 1,340 and 1,369. The synergy paper's Sage values for B1 and B3 without rescoring are 1,609 and 1,575 (other runs).

### PXD007683 (`lumos_lfq`, `lumos_tmt`; O'Connell et al., JPR 2018)

- **The paper:**
  - Aggregates only. LFQ: 454,545 matched peptides over 11 runs (MaxQuant 1.5.8.3, 1% protein FDR), 627,579 with MBR. TMT: an average of 27,500 MS2/MS3 paired scans collected per run (scans, not identifications).
  - Table S3 (totals per pipeline) is not open access.
  - The deposited SEQUEST `.out` files carry no FDR.
- **Per-run values:** only from the quantms reanalysis reports linked in the pmultiqc paper (MCP 2026).
  - **Pipeline:** MS-GF+ (v2023.01.12 in the search step) and Comet, each with MS2Rescore + Percolator, combined by ConsensusID; Swiss-Prot human + yeast.
  - **In the table:** "#PSMs from quant. peptides" and "#Peptides quantified". Checked in the report data.
  - **Caveats:**
    - The final FDR levels are not displayed. The per-engine columns (MSGF, Comet, about 82% of MS2 for LFQ) are not at 1% FDR and are not used.
    - The TMT report's software and workflow section repeats the LFQ report, so engine, database and settings are documented only for the LFQ run.

### PXD054559 (`eclipse_tmtpro`; Zuniga et al., JPR 2024)

- **Per-fraction counts:** from the deposited Comet mzIdentML, as PSMs with passThreshold (decoys removed). Counted here.
- **What passThreshold means:** not documented in the file. Only 0.04–0.12% of the passing PSMs are decoys, so it most likely reflects the LDA 1% PSM filter plus the 1% protein filter.
- **Database:** UniProt human with isoforms and TrEMBL, much larger than our `human_td.fasta`. The mzid names a 2021-11-24 release; the paper says it was downloaded in April 2024.
- **Paper:** 64,410 quantified peptides over all 12 fractions.
- **Other source:** the TMT-Integrator deposit (Zenodo 17353442) has no per-fraction counts.

### PXD053748 (`tims_plasma`; TIMS²Rescore, Declercq et al., JPR 2025, doi:10.1021/acs.jproteome.4c00609)

- **Deposited Sage 0.14.3 output:** counted here per run.
  - PSMs: label 1, `spectrum_q` ≤ 0.01.
  - Peptides: unmodified, I=L, also `peptide_q` ≤ 0.01.
  - The 6-run total, 83,413, reproduces the paper's 83,412.
- **Rescored PSMs** (mokapot): counted by a helper agent and again on 2026-11-12. The totals reproduce Table S2 (92,337); Table S2 gives its totals only as sums of its lost, shared and gained columns.
- **Source files:** the deposit holds them only inside `identifications_results.zip`.
- **Database:** the paper names Swiss-Prot canonical human (UP000005640, 20,597 entries). The searched `UP000005640_9606.fasta` is not deposited, and the target hits include 65 TrEMBL accessions (22 among the PSMs at 1%), so the file held more than Swiss-Prot.
- **Caveats:**
  - All 6 plasma runs were searched and rescored together, so the q-values are over 6 runs.
  - Sage ran with `chimera` on, but the deposited file has one PSM per spectrum.
  - Variable protein N-terminal acetylation was searched.
  - Peptide length: 7–50 in the search config; the paper says 8–50.

### PXD011695 (`pxd011695_*`, five runs)

- **Source of the "Authors" numbers in DATASETS.md 2.1:** they are the row counts of the deposited COMPASS/OMSSA PSM tables `nriley_Mouse_<run>_peptides.csv`, one row per spectrum, targets only. No paper prints them.
  - The method paper is Riley et al., Anal Chem 2017 (doi:10.1021/acs.analchem.7b00213). It gives counts only in figures and in Table S1 (triplicate means; the supplement could not be retrieved).
  - The PRIDE reference (IPSA, MCP 2019) has no counts.
- **Filter:** 1% FDR per run on OMSSA E-value and precursor mass error together.
- **Search:**
  - Trypsin, 3 missed cleavages.
  - c, z• and y ions for ETD, ETciD ("ETcaD") and AI-ETD; b in addition for EThcD.
  - Unreacted and charge-reduced precursor peaks are removed before the ETD-family searches (not described for HCD).
- **File identity:** the acquisition names stored inside three deposited raw files differ from the run names in the CSVs.
  - ETD: `CalRxn_5` against `CalRxn_3`; ETciD: `ETciD35_4` against `ETciD35_2`; AI-ETD: `Laser30_2` against `Laser30_1`.
  - Scan number, retention time and isolation m/z of every CSV row agree with our mzML of the deposited raw file, for all four ETD-family runs. So the CSVs belong to these files; only the names differ.
  - HCD and EThcD carry matching names.
- **Instrument:** an Orbitrap Fusion Lumos (method summary in the raw files, and the paper), not an Orbitrap Elite as PRIDE says. MS2 is in the ion trap, as assumed.
- **Database:**
  - The deposited 88,618-entry FASTA (ours) is probably not the one that was searched.
  - The paper names a download of 2016-05-12; the deposited file is dated 2016-11-09.
  - All OMSSA protein indices in the tables are even, with a maximum of 117,522, which fits an interleaved database of about 58,800 targets.
  - 8–38 accessions per file are not in the deposited FASTA.
- **Not in the table:** the extra deposited file AI-ETD+ (14,021 PSMs) is not one of our runs.

### PXD065289 (`pxd065289_etcid`, five fractions; Nature Methods 2026)

- **Paper:** no per-fraction numbers. ETciD appears only in Supplementary Figs. S18 and S20.
- **Where the ETciD results are:** `fragpipe_msbooster.zip`, the reference named in DATASETS.md 2.1, contains no ETciD (only ECD, EID, HCD and UVPD). The ETciD results are in `ETciD.zip`.
- **Counted here:** rows per fraction of its combined `psm.tsv`, in three ion-type configurations (a, b, c, x, y, z; c, z; b, y). All three are in the table.
- **Search:** FragPipe 22.0 / MSFragger 4.1, MSBooster off, ±20 ppm / ±20 ppm with mass calibration and parameter optimisation. Same database targets as ours.
- **Caveats:**
  - The 1% PSM FDR was applied jointly over all 20 fractions, then a 1% picked protein filter.
  - Variable protein N-terminal acetylation was searched; ours is not.
  - The paper does not say which configuration its ETciD figures use.

### PXD042233 (`pxd042233_lumos_cid`, `hela_exploris480`, `hela_qe_hf`; Webel et al., Sci Data 2024)

- **Source:** the per-run MaxQuant `summary.txt` values: the project's `pride_metadata.csv` has the same numbers as the deposited `summary.txt` files.
- **Search:** MaxQuant 1.6.12.0, one search per raw file, MBR off, 1% PSM and protein FDR, second peptides on.
  - Database: UniProt 2019_05 canonical + 75,468 additional sequences.
  - Ours is the deposited canonical FASTA plus its 246 contaminants (21,196 targets).
  - Where the settings come from: enzyme and modifications from `pride_metadata.csv`; length, mass, MS/MS tolerances, second peptides and MBR from `parameters.txt`; the first and main search tolerances (20 and 4.5 ppm) from the `mqpar.xml` of one Exploris run only (2020_06_10), not checked for the others.
- **What the values are:**
  - "MS/MS Identified" counts SIL and PEAK submissions; the split is in the notes. With second peptides on, one spectrum can count more than once.
  - "Peptide Sequences Identified" has no separate peptide-level FDR.

### iPRG2015 (`iprg2015`)

- **Published:** only a mean per file over all 12 runs: around 28,300 ± 2,200 PSMs and 21,100 ± 1,800 peptides with modifications (Weisser & Choudhary 2017).
  - These are DeMix IDs: MS-GF+ v10089, chimeric spectra deconvoluted, IDPicker 1% PSM FDR.
- **Counted here:**
  - From the deposited DeMix mzIdentML (PXD006336): PSMs, distinct spectrum IDs and unmodified peptides (I=L).
    - The spectrum IDs mix scan numbers and m/z@RT identifiers; there are slightly fewer distinct retention times (25,374 / 23,695 / 22,992).
    - 2,428 / 2,314 / 2,117 PSMs repeat another PSM of the same spectrum ID with the same peptide, charge and precursor m/z. Only 776 / 651 / 604 more unmodified sequences than spectrum IDs come from chimeric co-identification.
    - The mzid names no search engine (only OpenMS TOPP 2.1.0 as the exporter), so engine and settings come from the papers.
  - From the OpenMS / MS-GF+ mzTab in PXD010981: distinct spectra with a target PSM at q ≤ 0.01. This is a lower bound, because the file keeps only PSMs attached to quantified features.
    - 17, 16 and 7 more spectra have a peptide that maps to both a target and a decoy protein; they are not counted.
    - The mzTab was written by an OpenMS feature-branch build (2.4.0-feature-proteomic-lfq-2018-08-31).
- **Database:** our `iprg2015_td.fasta` has the same 6,628 target sequences as `iPRG2015.fasta` deposited with PXD006336.
- **Gap:** the study's own reference IDs (OMSSA + MS-GF+ + Comet through iProphet, semi-tryptic) are only on a password-protected PeptideAtlas FTP and were not fetched.
- **Context, not in the table:** OpenMS/OpenMS#10707 and #10714 give ProSE development numbers on `sample1_A`: 20,418 PSMs with Percolator, 19,792 without.

### PXD058436 (`pxd058436_classI`, `pxd058436_classII`; MHCquant2, Scheid et al., Genome Biol 2025)

- **Source:** the deposited per-sample result tables of MHCquant2, FragPipe and PEAKS: three engines on the same three replicates.
  - Counted here as unique unmodified sequences with I=L. This reproduces `pxd058436_db_check.tsv` and DATASETS.md 2.4.
  - The MHCquant2 tables hold peptides at ≤ 1% peptide-level q. Its mzTab holds one row per peptidoform, with one spectrum each.
  - Engine versions (MHCquant2 v2.6.0, FragPipe v21.1, PEAKS 11.5) are from the PRIDE project description; the tables do not record them.
- **Comparability:**
  - Same files and the same level.
  - Another Swiss-Prot release (2020-10-14). In each result table, at most 0.14% of the peptides are not in our targets (checked 2026-11-12). DATASETS.md 3.3 says fewer than 0.1%.
  - All three use predicted spectra or retention times, so expect our counts at or below these.
  - PEAKS keeps I and L apart; its I=L count is a little lower.

### PXD019643 (`pxd019643_classI`, `pxd019643_classII`; HLA Ligand Atlas, Marcu et al. 2021)

- **Published:** HLA Ligand Atlas release 2020.12, unique peptides per donor, tissue and class at 1% local peptide-level FDR (MHCquant 1.5.1).
- **Cross-check:** the values equal the counts at Percolator peptide-level q ≤ 0.01 in the deposited merged mzIdentML files, decoys included. Those files cover exactly our 3 replicates per sample.
  - The files themselves are cut at q ≤ 0.05; the 5% counts are in the notes.
- **Decoys in the published counts:** 4, 3 and 1 of the class I counts (Thyroid, Tongue, Bladder) and 0, 0 and 4 of the class II counts are decoy-only sequences. The notes give the target-only counts.
- **Comparability:**
  - Same files, same level.
  - Same targets: `sp_21_04_2020`, 20,365 human sequences without contaminants.
  - Percolator's peptide is the modified sequence, ours the unmodified one.
- **Recorded settings:** the mzid records a precursor tolerance of 6.0 ppm and Percolator 3.02; the paper says 5 ppm and Percolator 3.4. The table gives both.
- **One engine only.**

## Points for DATASETS.md (not changed here)

- **2.1, PXD011695:**
  - The "Authors" column holds the row counts of the deposited COMPASS tables, not published numbers.
  - The instrument is an Orbitrap Fusion Lumos, not an Elite (the parameter file name says `elite`).
  - The deposited FASTA is probably not the searched database.
- **2.1, PXD065289:** the ETciD results are in `ETciD.zip`, not in `fragpipe_msbooster.zip`.
- **2.3, PXD042233:** MaxQuant 1.6.12.0, canonical + isoform database (2019_05).
- **1, PXD053748:** the TIMS²Rescore paper is J Proteome Res 2025 (doi:10.1021/acs.jproteome.4c00609). DATASETS.md writes 2024.
- **2.1, PXD011695, file names:** the acquisition names stored inside the deposited ETD, ETciD and AI-ETD raw files differ from the run names in the CSVs. The scan check shows that the CSVs belong to these files.
- **3.3, PXD058436:** in each result table, at most 0.14% of the peptides are not in our targets; 3.3 says fewer than 0.1%.

## How the counts were made

- **Scripts:** `build_ref.py` writes the table. It, the check scripts and both checks' results are in `checks/reference_ids/` of the benchmark_prose folder, outside the repository; its README lists the files.
- **Inputs:** every count uses the deposited or uploaded file named in `source`, with the filter in `level` and `fdr`.
  - **Peptides:** unique unmodified sequences with I=L unless the level says otherwise.
  - **PSMs:** rows or spectra, as stated.
- **Collection (2026-11-11):** helper agents of the same session collected the values for PXD011695, PXD065289, iPRG2015, PXD001819, PXD007683, PXD054559, PXD053748, PXD042233 (settings) and PXD070049 (synergy, Mascot). I re-counted part of them.
- **Independent recheck (2026-11-12):** four fresh agents re-derived every value from the sources with their own code. They did not see the generator or these notes. Only the 8 earlier ProSE context rows, copied from DATASETS.md, were not part of it.
  - **Values:** all reproduced, except the three iPRG2015 mzTab counts. Those had included spectra whose peptide maps to both a target and a decoy protein. They are now target-only: 18,940 / 17,924 / 17,423, before 18,957 / 17,940 / 17,430.
  - **Text cells:** corrected where the recheck found them wrong or imprecise. Examples: the FASTA each ProteoBench submission searched; tool versions and tolerances as recorded in the deposited files; the decoy-only sequences in the HLA Ligand Atlas counts; where settings come from.
  - **One checker claim was wrong:** that three PXD011695 CSVs come from other replicates. A scan-level comparison with our mzML refuted it (see PXD011695).
- **Second check (2026-11-12, by the parent session):** four more checkers, again from the original sources only. Values: no mismatch (ProteoBench 133/133, published 124/124, deposited results 91/91, structure 92/92 runs).
  - **Corrected after it**, each re-derived here first: the i2MassChroQ notes (they had counted modified sequences); the DIA-NN cells (pre-filtered report, library search space, the twin submission); protein instead of peptide N-terminal acetylation where the parameter files say so; the repeated DeMix PSMs; the TIMS²Rescore database (with TrEMBL entries); our database for PXD001819 (`hy_td`); the MaxQuant aggregate of PXD007683 (without MBR); and the wording about our arms (they rescore, without external predictors; ProSE and MSFragger calibrate too).
  - **Left as they are:** omissions it listed that I could not confirm from a cached source: peptide length and charge of the synergy searches, the MaxQuant tolerances of PXD001819 workflow 2, and Comet's isotope error for PXD054559.
