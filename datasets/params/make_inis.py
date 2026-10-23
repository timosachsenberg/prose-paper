"""Writes the ProSE parameter files (.ini) of the benchmark, one per acquisition setting.

usage: make_inis.py <ProSE binary> <out dir>

Starts from `ProSE -write_ini` of the given build (its defaults), sets the values below, and checks every file by
reading it back with that ProSE (`-ini <file> -write_ini`): an invalid value or name aborts, and the values must come
back unchanged. Everything not set here stays at the default of the ProSE version used for the paper.

The tryptic search space is the one frozen in OpenMS/OpenMS#10364 (Trypsin/P, 2 missed cleavages, 7-40 aa,
Carbamidomethyl (C) fixed, at most one Oxidation (M), isotope errors -2..1, charge 2-5); the datasets differ only in
tolerances, labels and charges. The immunopeptidomics settings are those of the original publications."""
import os, subprocess, sys, xml.etree.ElementTree as ET

TRYPTIC = {
    "enzyme": "Trypsin/P",
    "peptide:missed_cleavages": "2",
    "peptide:min_size": "7",
    "peptide:max_size": "40",
    "modifications:fixed": ["Carbamidomethyl (C)"],
    "modifications:variable": ["Oxidation (M)"],
    "modifications:variable_max_per_peptide": "1",
    "precursor:mass_tolerance_lower": "20.0",
    "precursor:mass_tolerance_upper": "20.0",
    "precursor:mass_tolerance_unit": "ppm",
    "precursor:min_charge": "2",
    "precursor:max_charge": "5",
    "precursor:isotope_error_min": "-2",
    "precursor:isotope_error_max": "1",
    "fragment:mass_tolerance": "20.0",
    "fragment:mass_tolerance_unit": "ppm",
}
LOWRES = {"fragment:mass_tolerance": "0.5", "fragment:mass_tolerance_unit": "Da"}
LTQ = {**LOWRES,  # Percolator paper sets: precursor charge unknown, +-3 Da average-mass window (yeast.params)
       "precursor:mass_tolerance_lower": "3.0", "precursor:mass_tolerance_upper": "3.0",
       "precursor:mass_tolerance_unit": "Da", "precursor:min_charge": "1", "precursor:max_charge": "4",
       "precursor:isotope_error_min": "0", "precursor:isotope_error_max": "0"}

def immuno(min_size, max_size, max_mass, min_charge, max_charge, max_mods, precursor_ppm):
    return {"enzyme": "unspecific cleavage", "low_memory": "true",
            "peptide:min_size": str(min_size), "peptide:max_size": str(max_size),
            "peptide:min_mass": "800", "peptide:max_mass": str(max_mass),
            "modifications:fixed": [], "modifications:variable": ["Oxidation (M)"],
            "modifications:variable_max_per_peptide": str(max_mods),
            "precursor:mass_tolerance_lower": str(precursor_ppm), "precursor:mass_tolerance_upper": str(precursor_ppm),
            "precursor:mass_tolerance_unit": "ppm",
            "precursor:min_charge": str(min_charge), "precursor:max_charge": str(max_charge),
            "fragment:mass_tolerance": "0.02", "fragment:mass_tolerance_unit": "Da"}

CONFIGS = {
    # section 1, main benchmark
    "main_highres": TRYPTIC,  # HF-X, Astral, Lumos LFQ, timsTOF
    "main_velos_cid": {**TRYPTIC, **LOWRES},
    "main_lumos_tmt6_cid": {**TRYPTIC, **LOWRES,
                            "modifications:fixed": ["Carbamidomethyl (C)", "TMT6plex (K)", "TMT6plex (N-term)"]},
    "main_exploris_tmtpro": {**TRYPTIC, "precursor:mass_tolerance_lower": "50.0", "precursor:mass_tolerance_upper": "50.0",
                             "modifications:fixed": ["Carbamidomethyl (C)", "TMTpro (K)", "TMTpro (N-term)"]},
    # section 2, held-out datasets
    "pxd011695_elite_itms": {**TRYPTIC, **LOWRES},  # ETD-type spectra get c/z+1 ions by activation (default)
    "pxd065289_etcid_ot": TRYPTIC,
    "pxd042233_lumos_cid": {**TRYPTIC, **LOWRES},
    "iprg2015_qe": TRYPTIC,
    "percolator_ltq": {**TRYPTIC, **LTQ},
    "percolator_ltq_chymotrypsin": {**TRYPTIC, **LTQ, "enzyme": "Chymotrypsin"},
    # MHCquant2 (PXD058436): 20 ppm / 0.02 Da; class I 8-14 aa, 800-2500 Da, z 1-4, <= 3 mods; class II 12-30 aa, 800-5000 Da, z 1-5, <= 5 mods
    "pxd058436_classI": immuno(8, 14, 2500, 1, 4, 3, 20.0),
    "pxd058436_classII": immuno(12, 30, 5000, 1, 5, 5, 20.0),
    # MHCquant 1.5.1 (PXD019643): 5 ppm / 0.02 Da; class I 8-12 aa, 800-2500 Da, z 2-3; class II 8-25 aa, 800-5000 Da, z 2-5
    "pxd019643_classI": immuno(8, 12, 2500, 2, 3, 3, 5.0),
    "pxd019643_classII": immuno(8, 25, 5000, 2, 5, 5, 5.0),
}

def items(root):
    out = {}
    def walk(n, path):
        for c in n:
            if c.tag == "NODE": walk(c, path + [c.get("name")])
            elif c.tag in ("ITEM", "ITEMLIST"): out[":".join(path[2:] + [c.get("name")])] = c
    walk(root, [])
    return out

def value(e):
    return e.get("value") if e.tag == "ITEM" else [x.get("value") for x in e]

prose, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
default = os.path.join(out, "default.ini")
subprocess.run([prose, "-write_ini", default], check=True, capture_output=True)
for name, settings in CONFIGS.items():
    tree = ET.parse(default)
    it = items(tree.getroot())
    for key, val in settings.items():
        e = it["Search:" + key]
        if isinstance(val, list):
            for x in list(e): e.remove(x)
            for v in val: ET.SubElement(e, "LISTITEM", value=v)
        else:
            e.set("value", val)
    path = os.path.join(out, name + ".ini")
    tree.write(path, encoding="ISO-8859-1", xml_declaration=True)
    check = path + ".check"
    r = subprocess.run([prose, "-ini", path, "-write_ini", check], capture_output=True, text=True)
    back = items(ET.parse(check).getroot())
    os.remove(check)
    bad = [k for k in settings if value(back["Search:" + k]) != settings[k]]
    if r.returncode != 0 or "Invalid" in r.stdout + r.stderr or bad:
        sys.exit(f"{name}: not accepted by ProSE ({bad}): {r.stdout[-500:]} {r.stderr[-500:]}")
    print(f"{name}.ini: {len(settings)} settings, read back unchanged")
os.remove(default)
