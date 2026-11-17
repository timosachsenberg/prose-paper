"""Compare the ProSE parameter files written with P against datasets/params (task 11a, DATASETS.md section 5).

usage: compare_inis.py <new dir> <old dir>

Per file and parameter (full name with its nodes): value, type, restrictions and list entries. Only the version string
may differ in value; the descriptions are reported separately and may differ. Exit code 1 if anything else differs.

The order of a string parameter's allowed values (its restrictions, e.g. the 33 enzymes of Search:enzyme) is not
compared, only the values themselves, each as often: OpenMS lists the enzymes in the order of their addresses in memory
(the std::set<const DigestionEnzymeType*> of DigestionEnzymeDB), which depends on the binary and on the heap at start.
With glibc's default malloc settings the image's ProSE writes the order of datasets/params and a node build another one
with the same 33 values; with tcache off or MALLOC_ARENA_MAX 1 or 2 even the image's ProSE writes others, under the
latter from run to run (2026-11-17, checks/node_scripts/enzyme_order/). Such parameters are listed as "order of the
allowed values" and do not count as differences. This is the one change from checks/freeze_P/compare_inis.py of the
freeze.
"""
import os
import sys
import xml.etree.ElementTree as ET


def params(path):
    out, desc = {}, {}

    def walk(el, prefix):
        for c in el:
            if c.tag == "NODE":
                walk(c, prefix + c.get("name") + ":")
            elif c.tag == "ITEM":
                n = prefix + c.get("name")
                out[n] = ("item", c.get("value"), c.get("type"), c.get("restrictions"))
                desc[n] = c.get("description")
            elif c.tag == "ITEMLIST":
                n = prefix + c.get("name")
                out[n] = ("list", tuple(li.get("value") for li in c.findall("LISTITEM")), c.get("type"),
                          c.get("restrictions"))
                desc[n] = c.get("description")
    walk(ET.parse(path).getroot(), "")
    return out, desc


def same_but_order(x, y):
    """The same parameter but for the order of the allowed values of a string parameter (each value as often)."""
    if x[:3] != y[:3] or x[2] not in ("string", "string-list") or x[3] is None or y[3] is None:
        return False
    return x[3] != y[3] and sorted(x[3].split(",")) == sorted(y[3].split(","))


def main():
    new, old = sys.argv[1], sys.argv[2]
    names = sorted(f for f in os.listdir(old) if f.endswith(".ini"))
    assert sorted(f for f in os.listdir(new) if f.endswith(".ini")) == names, "different sets of files"
    bad = order = 0
    for f in names:
        a, da = params(os.path.join(old, f))
        b, db = params(os.path.join(new, f))
        lines, n_order = [], 0
        for n in sorted(set(a) | set(b)):
            if n not in a:
                lines.append(f"  NEW parameter {n} = {b[n][1]}")
                bad += 1
            elif n not in b:
                lines.append(f"  MISSING parameter {n} (was {a[n][1]})")
                bad += 1
            elif same_but_order(a[n], b[n]):
                lines.append(f"  order of the allowed values {n} ({len(a[n][3].split(','))} values, the same ones)")
                n_order += 1
            elif a[n] != b[n]:
                ok = n.endswith(":version") or n == "version"
                lines.append(f"  {'version' if ok else 'CHANGED'} {n}: {a[n]} -> {b[n]}")
                bad += 0 if ok else 1
        order += n_order
        changed_desc = [n for n in sorted(set(a) & set(b)) if da[n] != db[n]]
        print(f"{f}: {len(a)} parameters; value changes: {len(lines) - n_order}; description changes: {len(changed_desc)}"
              + (f" ({', '.join(changed_desc)})" if changed_desc else "")
              + (f"; order of the allowed values: {n_order}" if n_order else ""))
        for line in lines:
            print(line)
    if bad:
        print(f"result: FAIL ({bad} differences)")
    else:
        print("result: PASS (only the version string and descriptions differ"
              + (f"; the order of the allowed values in {order} parameters" if order else "") + ")")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
