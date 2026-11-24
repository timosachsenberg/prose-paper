"""Fixed design constants of the benchmark (SPEC section 2.2), checked against runs.tsv, the parameter files and
overtuning.py on every run (checks C15, C22).

Citation keys as in the SPEC: DS = datasets/DATASETS.md, B = benchmarks/bench.py, OT = benchmarks/overtuning.py,
RM = benchmarks/README.md, REF = datasets/reference_ids.tsv, PI = datasets/params/<name>.ini.

What is here
- Kinds: TUNING and HELDOUT (imported from OT:26-28, not copied), ELECTRON, IMMUNO; TRYPTIC = TUNING + HELDOUT.
- CLASS, GRADE, INSTRUMENT, DISPLAY_NAME per group; the lookups kind(), cls(), grade(), side(), instrument(),
  display() also answer for groups outside the design ('other', '-') as --design none needs (SPEC section 1, CLI).
- Orders: CLASS_BLOCKS, FIGURE_ORDER (17 tryptic datasets), ELECTRON_ORDER, IMMUNO_ORDER, BATCH_ORDER.
- DECISION (11 run ids, DS:998), ENGINES, ENGINE_NAME, COLOUR, PAIRS, LEVELS.
- ARMS (benchmark -> Arm) and arm_of(benchmark); other_arrangement_tag(); read_pooled_arrangement() (the reader of
  POOLED_ARRANGEMENT, Search:rescore_reuse:mode of the immunopeptidomics parameter files, PI pxd019643_classI.ini:154).
- CAL_RUNS (RM:160-161, DS:775), PRED_GROUPS (OPEN Q38 default), REFERENCE_MAP and EXPECTED_TOOLS (OPEN Q12, Q46,
  Q47), CAP_GIB (DS:653).
"""
import importlib.util
import os
import sys
from collections import namedtuple

sys.dont_write_bytecode = True  # before overtuning and make_inis are imported (SPEC section 1, B:102-105)

HERE = os.path.dirname(os.path.abspath(__file__))  # benchmarks/summaries
BENCH = os.path.dirname(HERE)  # benchmarks
REPO = os.path.dirname(BENCH)
PARAMS = os.path.join(REPO, "datasets", "params")

if BENCH not in sys.path:
    sys.path.insert(0, BENCH)
import overtuning as OT  # noqa: E402  (import-safe: main is guarded at OT:189-190)

# ---------------------------------------------------------------- kinds (SPEC 2.2 "Kind")
TUNING = OT.TUNING  # the 7 tuning datasets, DS:862-868, in OT's order (OT:26)
HELDOUT = OT.HELDOUT  # the 10 held-out tryptic datasets, DS:869-878, in OT's order (OT:27-28)
TRYPTIC = TUNING + HELDOUT  # used by O15, O16
ELECTRON = ("pxd011695_EThcD", "pxd011695_ETciD", "pxd011695_ETD", "pxd011695_AI-ETD", "pxd065289_etcid")  # DS:881
IMMUNO = ("pxd058436_classI", "pxd058436_classII", "pxd019643_classI", "pxd019643_classII")  # DS:881; runs.tsv 40-75
ALL_GROUPS = TRYPTIC + ELECTRON + IMMUNO
KINDS = ("tuning", "heldout", "electron", "immuno", "other")

# ---------------------------------------------------------------- class (SPEC 2.2 "Class"; DS:860-878, 120, 134-135, 201, 210)
CLASS = {
    "velos": "IT", "lumos_tmt": "IT", "hfx": "OT", "lumos_lfq": "OT", "eclipse_tmtpro": "OT", "astral": "Astral",
    "tims_plasma": "timsTOF",
    "ups1_control": "IT", "pxd042233_lumos_cid": "IT", "pxd011695_HCD": "IT", "iprg2015": "OT", "hela_qe_hf": "OT",
    "hela_exploris480": "OT", "astral_s1": "Astral", "astral_250pg": "Astral", "ultra2_s2": "timsTOF",
    "ultra2_hye": "timsTOF",
    # electron: pxd011695_* ion-trap MS2 (DS:120), pxd065289_etcid Orbitrap MS2 (DS:134-135)
    "pxd011695_EThcD": "IT", "pxd011695_ETciD": "IT", "pxd011695_ETD": "IT", "pxd011695_AI-ETD": "IT",
    "pxd065289_etcid": "OT",
    # immuno: timsTOF Pro 2 (DS:201); Fusion Lumos with Orbitrap MS2 at 20 ppm fragments (DS:210, 577)
    "pxd058436_classI": "timsTOF", "pxd058436_classII": "timsTOF", "pxd019643_classI": "OT", "pxd019643_classII": "OT",
}
CLASS_BLOCKS = ("IT", "OT", "Astral", "timsTOF")

# ---------------------------------------------------------------- grade (SPEC 2.2 "Grade"; DS:110-112; tuning '-')
GRADE = {g: "-" for g in TUNING}
GRADE.update({g: "A" for g in ("pxd011695_HCD", "pxd011695_EThcD", "pxd011695_ETciD", "pxd011695_ETD",
                               "pxd011695_AI-ETD", "pxd065289_etcid")})
GRADE.update({g: "B" for g in ("pxd042233_lumos_cid", "hela_qe_hf", "hela_exploris480", "iprg2015") + IMMUNO})
GRADE.update({g: "C" for g in ("astral_s1", "astral_250pg", "ups1_control", "ultra2_s2", "ultra2_hye")})

# ---------------------------------------------------------------- orders (SPEC 2.2 "Figure order"; OPEN Q32)
# class blocks IT, OT, Astral, timsTOF; within a block tuning first, then held-out, each in DS 4.6 table order
FIGURE_ORDER = (
    "velos", "lumos_tmt", "ups1_control", "pxd042233_lumos_cid", "pxd011695_HCD",  # IT
    "hfx", "lumos_lfq", "eclipse_tmtpro", "iprg2015", "hela_qe_hf", "hela_exploris480",  # OT
    "astral", "astral_s1", "astral_250pg",  # Astral
    "tims_plasma", "ultra2_s2", "ultra2_hye",  # timsTOF
)
ELECTRON_ORDER = ELECTRON  # runs.tsv lines 23-31
IMMUNO_ORDER = IMMUNO  # run-table order, runs.tsv lines 40-75
# the 16 tryptic batch groups in figure order (pxd011695_HCD has one file and no batch, B:976), then the electron
# block with pxd065289_etcid; 17 groups, 16 for Sage (pxd065289_etcid is bycz) (SPEC 2.1 "Batch groups", 2.2)
BATCH_ORDER = tuple(g for g in FIGURE_ORDER if g != "pxd011695_HCD") + ("pxd065289_etcid",)

# ---------------------------------------------------------------- decision runs (DS:998; runs.tsv 23, 25, 37, 46-48, 64-66, 76, 82)
DECISION = (
    "pxd011695_EThcD", "pxd011695_ETD", "iprg2015_1A",
    "DN13_Tongue_classI_techRep1", "DN13_Tongue_classI_techRep2", "DN13_Tongue_classI_techRep3",
    "170218_AM_AUT01-DN13_Tongue_W6-32_10_DDA_1_400-650mz_msms15_standard",
    "170218_AM_AUT01-DN13_Tongue_W6-32_10_DDA_2_400-650mz_msms16_standard",
    "170218_AM_AUT01-DN13_Tongue_W6-32_10_DDA_3_400-650mz_msms17_standard",
    "astral250pg_A2", "ultra2_A2",
)

# ---------------------------------------------------------------- engines (SPEC 2.2 "Other constants")
ENGINES = ("prose", "sage", "msfragger")
ENGINE_NAME = {"prose": "ProSE", "sage": "Sage", "msfragger": "MSFragger"}
COLOUR = {"prose": "#0072B2", "sage": "#009E73", "msfragger": "#D55E00"}  # Okabe-Ito
PAIRS = (("prose", "msfragger"), ("prose", "sage"))  # the main comparison (SPEC O2)
LEVELS = ("psm", "peptide")
CAP_GIB = 200  # memory cap N = 200 GiB (DS:653, 1009)

# ---------------------------------------------------------------- arms (SPEC 2.2 ARMS; OPEN Q36-Q38, Q49, Q57)
Arm = namedtuple("Arm", "benchmark tag engines label known")
_ALL = ENGINES
ARMS = {
    "per_file": Arm("per_file", None, _ALL, "main", True),
    "per_file_low_memory": Arm("per_file_low_memory", "low_memory", ("prose",), "low_memory", True),  # RA:121-123
    "per_file_cal_off": Arm("per_file_cal_off", "cal_off", ("prose",), "calibration off", True),  # RM:163
    "per_file_cal1": Arm("per_file_cal1", "cal1", ("msfragger",), "calibrate_mass 1", True),  # RM:164
    "per_file_cal0": Arm("per_file_cal0", "cal0", ("msfragger",), "calibrate_mass 0", True),  # RM:165
    # the other pooled arrangement of ProSE (proposed, OPEN Q36): which of the two is "other" depends on
    # POOLED_ARRANGEMENT, see other_arrangement_tag()
    "per_file_mode_joint": Arm("per_file_mode_joint", "mode_joint", ("prose",), "other pooled arrangement", True),
    "per_file_mode_per_file": Arm("per_file_mode_per_file", "mode_per_file", ("prose",), "other pooled arrangement",
                                  True),
    "per_file_peptdeep": Arm("per_file_peptdeep", "peptdeep", ("prose",), "ProSE + PeptDeep", True),  # OPEN Q38, Q57
    "per_file_msbooster": Arm("per_file_msbooster", "msbooster", ("msfragger",), "MSFragger + MSBooster", True),
    "per_file_percolator_s1": Arm("per_file_percolator_s1", "percolator_s1", _ALL, "external Percolator, seed 1",
                                  True),  # OPEN Q37
    "per_file_percolator_s42": Arm("per_file_percolator_s42", "percolator_s42", _ALL, "external Percolator, seed 42",
                                   True),
    "per_file_percolator_s137": Arm("per_file_percolator_s137", "percolator_s137", _ALL,
                                    "external Percolator, seed 137", True),
}
PERCOLATOR_SEEDS = (1, 42, 137)  # DS:613


def arm_of(benchmark):
    """The Arm of a per_file benchmark name ('per_file' or 'per_file_<tag>'), or None for another name.
    A tag outside ARMS gives a generic arm (known False, every engine allowed): further arms are allowed (DS:652, 811;
    OPEN Q49) and go to O25 with a WARN."""
    if benchmark in ARMS:
        return ARMS[benchmark]
    if benchmark.startswith("per_file_") and len(benchmark) > len("per_file_"):
        tag = benchmark[len("per_file_"):]
        return Arm(benchmark, tag, ENGINES, "further arm " + tag, False)
    return None


def other_arrangement_tag(mode):
    """The tag of ProSE's other pooled arrangement (DS:629; OPEN Q36): 'mode_joint' when the main arrangement is
    per_file, 'mode_per_file' when it is joint, None otherwise."""
    return {"per_file": "mode_joint", "joint": "mode_per_file"}.get(mode)


# ---------------------------------------------------------------- calibration runs, prediction groups
CAL_RUNS = ("hfx_A2", "astral_A2", "velos_125_R1", "lumos_lfq_5192", "lumos_tmt_5058", "eclipse_tmtpro_10855",
            "tims_plasma_30min", "2015_12_21_12_42_Orbitrap-Fusion-Lumos_FSN20115", "pxd011695_HCD")  # RM:160-161
PRED_GROUPS = ("hfx", "astral", "lumos_lfq", "eclipse_tmtpro", "tims_plasma", "iprg2015", "astral_s1",
               "astral_250pg")  # OPEN Q38 default (DS:749, 942)

# ---------------------------------------------------------------- instruments (DS sections 1 and 2; OPEN Q42, Q43)
INSTRUMENT = {
    "velos": "LTQ Orbitrap Velos", "lumos_tmt": "Orbitrap Fusion Lumos", "hfx": "Q Exactive HF-X",
    "lumos_lfq": "Orbitrap Fusion Lumos", "eclipse_tmtpro": "Orbitrap Exploris 480", "astral": "Orbitrap Astral",
    "tims_plasma": "timsTOF HT",
    "ups1_control": "LTQ Orbitrap Velos", "pxd042233_lumos_cid": "Orbitrap Fusion Lumos",
    "pxd011695_HCD": "Orbitrap Elite",  # DS:120 (reference_ids.md says Fusion Lumos: OPEN Q43)
    "iprg2015": "Q Exactive", "hela_qe_hf": "Q Exactive HF", "hela_exploris480": "Orbitrap Exploris 480",
    "astral_s1": "Orbitrap Astral", "astral_250pg": "Orbitrap Astral", "ultra2_s2": "timsTOF Ultra 2",
    "ultra2_hye": "timsTOF Ultra 2",
    "pxd011695_EThcD": "Orbitrap Elite", "pxd011695_ETciD": "Orbitrap Elite", "pxd011695_ETD": "Orbitrap Elite",
    "pxd011695_AI-ETD": "Orbitrap Elite", "pxd065289_etcid": "Orbitrap Ascend",  # DS:135
    "pxd058436_classI": "timsTOF Pro 2", "pxd058436_classII": "timsTOF Pro 2",  # DS:201
    "pxd019643_classI": "Orbitrap Fusion Lumos", "pxd019643_classII": "Orbitrap Fusion Lumos",  # DS:210
}

# ---------------------------------------------------------------- display names (OPEN Q30): short dataset names of
# the DS section 1 group column and the section 2 headings
DISPLAY_NAME = {
    "velos": "Velos CID", "lumos_tmt": "Lumos CID TMT6", "hfx": "HF-X HCD", "lumos_lfq": "Lumos HCD LFQ",
    "eclipse_tmtpro": "Exploris 480 TMTpro", "astral": "Astral", "tims_plasma": "timsTOF HT plasma",
    "ups1_control": "UPS1 control", "pxd042233_lumos_cid": "PXD042233 Lumos CID", "pxd011695_HCD": "PXD011695 HCD",
    "iprg2015": "iPRG2015", "hela_qe_hf": "HeLa Q Exactive HF", "hela_exploris480": "HeLa Exploris 480",
    "astral_s1": "Astral set S1", "astral_250pg": "Astral 250 pg", "ultra2_s2": "timsTOF Ultra 2 set S2",
    "ultra2_hye": "timsTOF Ultra 2 HYE",
    "pxd011695_EThcD": "PXD011695 EThcD", "pxd011695_ETciD": "PXD011695 ETciD", "pxd011695_ETD": "PXD011695 ETD",
    "pxd011695_AI-ETD": "PXD011695 AI-ETD", "pxd065289_etcid": "PXD065289 ETciD",
    "pxd058436_classI": "PXD058436 class I", "pxd058436_classII": "PXD058436 class II",
    "pxd019643_classI": "PXD019643 class I", "pxd019643_classII": "PXD019643 class II",
}


# ---------------------------------------------------------------- lookups
def kind(group):
    """'tuning' | 'heldout' | 'electron' | 'immuno' | 'other' (a group outside design.py, --design none)."""
    if group in TUNING:
        return "tuning"
    if group in HELDOUT:
        return "heldout"
    if group in ELECTRON:
        return "electron"
    if group in IMMUNO:
        return "immuno"
    return "other"


def cls(group):
    """'IT' | 'OT' | 'Astral' | 'timsTOF'; '-' outside the design."""
    return CLASS.get(group, "-")


def grade(group):
    """'A' | 'B' | 'C'; '-' for tuning datasets (DS:862-868 have no grade) and outside the design."""
    return GRADE.get(group, "-")


def side(group):
    """'tuning' or 'heldout' for the 17 tryptic datasets (DS 4.6), else None."""
    return {"tuning": "tuning", "heldout": "heldout"}.get(kind(group))


def instrument(group):
    return INSTRUMENT.get(group, "-")


def display(group):
    """DISPLAY_NAME, or the run-table key for a group outside the design."""
    return DISPLAY_NAME.get(group, group)


def order_key(group):
    """Sort key of the design order: FIGURE_ORDER, then ELECTRON_ORDER, then IMMUNO_ORDER, then other groups."""
    for i, block in enumerate((FIGURE_ORDER, ELECTRON_ORDER, IMMUNO_ORDER)):
        if group in block:
            return (i, block.index(group), group)
    return (3, 0, group)


# ---------------------------------------------------------------- published references (SPEC 2.2 REFERENCE_MAP)
# strings are matched as prefixes; any other string in a row of these groups and scope stops (ids.py, O9/O24, C21).
# Each entry: groups, the REF lines it covers, the scope prefix ('<sample>' = the unit name), (engine prefix, tool)
# pairs (tool None: the row is ignored), the level and fdr prefixes (None: taken per row) and a flag.
REFERENCE_MAP = (
    {"groups": ("pxd058436_classI", "pxd058436_classII"), "ref_lines": (264, 281),
     "scope": "per sample <sample>:",
     "engines": (("MHCquant2", "mhcquant"), ("FragPipe", "fragpipe"), ("PEAKS", "peaks")),
     "level": "peptides: unique unmodified sequences, I=L",
     "fdr": "1% peptide-level FDR among the technical replicates of the sample", "flag": ""},
    {"groups": ("pxd019643_classI", "pxd019643_classII"), "ref_lines": (282, 287),
     "scope": "per sample <sample>:",
     "engines": (("MHCquant 1.5.1", "mhcquant"),),
     "level": "peptides: unique sequences (I=L gives the same count)",
     "fdr": "1% local peptide-level FDR among the technical replicates of the sample", "flag": "local"},  # OPEN Q46
    {"groups": ("iprg2015",), "ref_lines": (251, 263),
     "scope": "per run",
     "engines": (("MS-GF+ v2018.01.30 via OpenMS", "msgf_openms"), ("MS-GF+ v10089 with DeMix", "msgf_demix"),
                 ("ProSE + Percolator", None)),
     "level": None, "fdr": None, "flag": "O24"},  # OPEN Q47
)
# every immuno sample must get these tools, else FAIL (C21)
EXPECTED_TOOLS = {"pxd058436_classI": ("mhcquant", "fragpipe", "peaks"),
                  "pxd058436_classII": ("mhcquant", "fragpipe", "peaks"),
                  "pxd019643_classI": ("mhcquant",), "pxd019643_classII": ("mhcquant",)}


# ---------------------------------------------------------------- POOLED_ARRANGEMENT (SPEC 2.2)
_MAKE_INIS = None


def make_inis():
    """datasets/params/make_inis.py, loaded from its path (its readers items() and value(), as B:103-105), without
    putting datasets/params on sys.path and without writing bytecode."""
    global _MAKE_INIS
    if _MAKE_INIS is None:
        path = os.path.join(PARAMS, "make_inis.py")
        spec = importlib.util.spec_from_file_location("make_inis", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _MAKE_INIS = module
    return _MAKE_INIS


def ini_value(path, key):
    """The value of one parameter (e.g. 'Search:rescore_reuse:mode') of a ProSE parameter file, read with
    make_inis.items() and value() as bench.settings() does (B:136-139); None if the file lacks the key."""
    import xml.etree.ElementTree as ET
    m = make_inis()
    it = m.items(ET.parse(path).getroot())
    return m.value(it[key]) if key in it else None


POOLED_KEY = "Search:rescore_reuse:mode"


def read_pooled_arrangement(paths):
    """POOLED_ARRANGEMENT: ProSE's main arrangement of the immunopeptidomics replicates, Search:rescore_reuse:mode
    of the parameter files of the immuno groups (PI pxd019643_classI.ini:154). The main searches run untagged with
    these files (DS:1088; --extra needs --tag, DS:811), so this is the arrangement of the per_file rows whatever task
    11b decides (DS:629). The files must agree, else the run stops (exit 2).
    paths: the parameter files (in run-table order). Returns (mode, [(path, mode), ...]); (None, []) without files."""
    from .tables import ValidationStop  # late import: tables imports this module
    found = []
    for p in paths:
        if not os.path.exists(p):
            raise ValidationStop(f"{p}: parameter file not found (needed for POOLED_ARRANGEMENT, SPEC 2.2)")
        found.append((p, ini_value(p, POOLED_KEY)))
    modes = sorted({str(m) for _, m in found})
    if len(modes) > 1:
        detail = ", ".join(f"{os.path.basename(p)}: {m}" for p, m in found)
        raise ValidationStop(f"POOLED_ARRANGEMENT: the immunopeptidomics parameter files disagree on {POOLED_KEY} "
                             f"({detail}); allowed: one value for all (SPEC 2.2)")
    if found and found[0][1] is None:
        raise ValidationStop(f"{found[0][0]}: no {POOLED_KEY} (SPEC 2.2)")
    return (found[0][1] if found else None), found
