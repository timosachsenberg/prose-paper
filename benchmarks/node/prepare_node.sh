#!/usr/bin/env bash
# Sets up and checks a benchmark node after the copy: the checks after copying and the set-up of each node
# (datasets/DATASETS.md section 5, tasks 2, 3, 4 and 7; benchmarks/node/README.md). Run it on the node as the user who
# runs the benchmark, in a login shell (systemd-run --user needs the user's session bus), and never in a shell in which
# P's env_native.sh was sourced.
#
# usage: prepare_node.sh --copy <copy> --mem-gb <N> --role engine|scaling
#                        (--openms-bin <node build>/bin [--hand-build] | --native-only)
#                        [--w-node <folder>] [--dotnet-root <folder>] [--from <step> | --only <step>[,<step>...]]
#
#   --copy         the copied folder: prose-paper/, work/ (mzml/, db/), smoke_work/, tools/
#   --mem-gb       the memory cap N of this node (bench.py --mem-gb; at least 7, which the smoke test's MSFragger needs)
#   --role         engine (the engine comparison) or scaling (the scaling node: CPUs 0-191 must be 192 cores)
#   --openms-bin   bin/ of P built on this node (build_P.sh --prefix <prefix>: <prefix>/bin)
#   --hand-build   the node build was not made by build_P.sh (no BUILD_P.txt): its generic flags, its configure output
#                  and WITH_* cannot be checked; this is recorded
#   --native-only  no node build yet: the untimed checks run with P's native copy, the steps build and env are left
#                  out. Run the script again with --openms-bin once P is built (--from build), with the same --copy,
#                  --mem-gb, --role and --w-node: a run without the step machine stops if these differ from machine.txt
#   --w-node       the work folder of the checks of step 5 (default <copy>/W_node)
#   --dotnet-root  the .NET 8 runtime of the node build (default /usr/share/dotnet, where build_P.sh puts it)
#   --from, --only start at a step, or run only these steps (after a failure, for example)
# The paths of --copy, --openms-bin, --w-node and --dotnet-root may hold only letters, digits and . _ / + - (node_env.sh
# embeds them). After a new N: the step machine, then --only smoke,env, with the same --role and --w-node; after a new
# --w-node: the step machine, then --only copy,env (the step copy takes the two vendor files from the earlier W_node, by
# a hard link or a move); or --from machine. The step machine notes a role, N or W_node other than the one before.
#
# The steps, in this order (the quick ones first). Each stops the script at its first failure; the record is in
# <copy>/node_prep/.
#   machine   RAM, CPUs, OS, storage, the role, the memory cap and W_node into node_prep/machine.txt (task 7); the cap
#             must be in force, also in the cgroups above the user's; on the scaling node (pinned runs) CPUs 0-191 must
#             be 192 different cores, all of them got by taskset in a scope of the user (cpusets) and not held lower by
#             a CPU quota; on the engine node (runs not pinned) fewer than 16 CPUs without taskset get a note; the copy
#             must not be on a noexec mount; a network file system (by its type in the mount table, of the mount in
#             effect) gets a warning
#   tools     the executable bits; the Percolator build that runs here (3.09.0), Sage (0.14.7, which prints 0.14.6),
#             Java, MSFragger 4.4.1, /usr/bin/time and taskset
#   copy      prose-paper at PAPER_MIN or later with no changed file; the 92 mzML against datasets/mzml.sha256 (116 GB to
#             read); P's tarballs against tools/openms.sha256; the two vendor files of W_node against
#             benchmarks/vendor.sha256 (moved from work/vendor/, or taken from the vendor/ of an earlier W_node, to
#             W_node/vendor/)
#   native    unpacks P's native copy into tools/ (through a temporary folder) and checks it: every file of the tarball,
#             and the tools in a subshell with its env_native.sh
#   build     the node build: made by build_P.sh on this node, every library found, libOpenMS from the build, version
#             3.7.0 and Revision: eaf9175, the PeptDeep models, the Thermo bridge, the .NET 8 runtime, and no trace of
#             the native copy or of another OpenMS in its environment; its storage (as in machine), noted in machine.txt
#   params    the 12 ProSE parameter files written again with P: compare_inis.py must print result: PASS (task 11a;
#             the order of a string parameter's allowed values, which differs between two builds of P, is not compared)
#   versions  bench.py versions and databases in work/ (the 34 databases by SHA256)
#   smoke     the smoke test with all three engines, in a new folder node_prep/smoke_<build|native> (about 15 minutes)
#   env       writes <copy>/node_env.sh: OPENMS_BIN, PERCOLATOR, DOTNET_ROOT, B and BW for the benchmark on this node
#             (the two vendor files must be in W_node/vendor/; node_env.sh sets no BW while they are missing there)
#
# Left to you: that MSFragger's licence covers the person who runs it (open point 2). The engine node is the VM of the
# trial (16 vCPUs; the owner runs the thread scaling later), and N is 200 on both nodes (decided 2026-11-23, DATASETS.md
# section 5).
set -Eeuo pipefail

P_COMMIT=eaf9175bc745f92af82b2384fba23a412d72f665
P_SHORT=eaf9175bc7
P_REV=eaf9175
# the commit of prose-paper (1327715, 2026-11-26) with datasets/mzml.sha256 (the five PXD065289 lines of eaf9175)
# and P = eaf9175 (build_P.sh, image_configure.txt, image_packages.txt, systemd_container/Dockerfile); P's tarballs
# are checked against <copy>/tools/openms.sha256, which is not in prose-paper
PAPER_MIN=1327715c0690dce0e13a0b2db4e26b9bcfacc205
NATIVE_NAME=openms-$P_SHORT
NODE_VENDOR=(LFQ_Astral_DDA_15min_250pg_Condition_A_REP2.raw LFQ_Ultra2_PASEF_15min_50ng_Condition_A_REP2.d.zip)
TOOL_NAMES=(ProSE FileConverter EntrapmentEvaluator)
ENGINES=(prose sage msfragger)
MODELS=(peptdeep_ms2_dynamic.onnx peptdeep_rt_dynamic.onnx peptdeep_ccs_dynamic.onnx)
ALL_STEPS=(machine tools copy native build params versions smoke env)
# network file systems by their type in the mount table (findmnt); other FUSE types get a note
NETWORK_FS='nfs|nfs4|cifs|smb2|smb3|smbfs|lustre|gpfs|beegfs|fhgfs|ceph|afs|orangefs|wekafs|panfs|davfs|fuse\.(sshfs|ceph-fuse|ceph|glusterfs|s3fs|rclone|gcsfuse|juicefs|davfs2|cvmfs2)'
HERE=$(dirname "$(realpath "${BASH_SOURCE[0]}")")

usage() {
  echo "usage: prepare_node.sh --copy <copy> --mem-gb <N> --role engine|scaling"
  echo "                       (--openms-bin <node build>/bin [--hand-build] | --native-only)"
  echo "                       [--w-node <folder>] [--dotnet-root <folder>] [--from <step> | --only <step>[,<step>...]]"
  echo "steps: ${ALL_STEPS[*]} (the comment at the top of $0 says what each does)"
  exit "$1"
}
STEP=start
die() {
  printf 'prepare_node.sh: FAILED in step %s: %s\n' "$STEP" "$*" >&2
  [ "$STEP" = start ] || printf 'prepare_node.sh: once that is fixed, run it again from this step: ... --from %s\n' "$STEP" >&2
  exit 3   # 3: the ERR trap below stays silent when a subshell ends so (die has said why)
}
ok() { echo "  ok: $*"; }
note() { echo "  note: $*"; }

COPY="" MEM_GB="" ROLE="" BUILD_BIN="" NATIVE_ONLY=0 HAND_BUILD=0 W_NODE="" DOTNET=/usr/share/dotnet FROM="" ONLY=""
while [ $# -gt 0 ]; do
  case $1 in
    --copy|--mem-gb|--role|--openms-bin|--w-node|--dotnet-root|--from|--only) [ $# -ge 2 ] || usage 1 ;;&
    --copy) COPY=$2; shift 2 ;;
    --mem-gb) MEM_GB=$2; shift 2 ;;
    --role) ROLE=$2; shift 2 ;;
    --openms-bin) BUILD_BIN=$2; shift 2 ;;
    --hand-build) HAND_BUILD=1; shift ;;
    --native-only) NATIVE_ONLY=1; shift ;;
    --w-node) W_NODE=$2; shift 2 ;;
    --dotnet-root) DOTNET=$2; shift 2 ;;
    --from) FROM=$2; shift 2 ;;
    --only) ONLY=$2; shift 2 ;;
    -h|--help) usage 0 ;;
    *) echo "prepare_node.sh: unknown argument $1" >&2; usage 1 ;;
  esac
done
[ -n "$COPY" ] && [ -n "$MEM_GB" ] && [ -n "$ROLE" ] || usage 1
if [ "$(id -u)" -eq 0 ] && [ -n "${SUDO_USER:-}" ]; then
  die "run prepare_node.sh as the user who runs the benchmark, not with sudo (its files would belong to root, and" \
    "systemd-run --user needs that user's session)"
fi
[ -d "$COPY" ] || die "--copy $COPY is no folder"
COPY=$(realpath "$COPY")
[[ $MEM_GB =~ ^[0-9]+$ ]] && [ "$MEM_GB" -ge 7 ] || die "--mem-gb needs a whole number of GB, at least 7"
[[ $ROLE == engine || $ROLE == scaling ]] || die "--role is engine or scaling"
REPO=$COPY/prose-paper WORK=$COPY/work SMOKE=$COPY/smoke_work TOOLS=$COPY/tools STATE=$COPY/node_prep
NATIVE=$TOOLS/$NATIVE_NAME
if [ $NATIVE_ONLY = 1 ]; then
  [ -z "$BUILD_BIN" ] && [ $HAND_BUILD = 0 ] || die "--native-only goes without --openms-bin and --hand-build"
else
  [ -n "$BUILD_BIN" ] || die "give --openms-bin <node build>/bin, or --native-only while there is no node build"
  [ -d "$BUILD_BIN" ] || die "--openms-bin $BUILD_BIN is no folder"
  BUILD_BIN=$(realpath "$BUILD_BIN")
  # the native copy (env_native.sh and syslib/ next to its OpenMS/) is not the node build
  case "$BUILD_BIN/" in "$NATIVE"/*) die "--openms-bin $BUILD_BIN is in P's native copy; give the node build (build_P.sh)" ;; esac
  d=$(dirname "$(dirname "$BUILD_BIN")")
  [ ! -e "$d/env_native.sh" ] && [ ! -d "$d/syslib" ] \
    || die "--openms-bin $BUILD_BIN is a native copy (env_native.sh or syslib/ in $d); give the node build (build_P.sh)"
fi
[ -n "$FROM" ] && [ -n "$ONLY" ] && die "give --from or --only, not both"
W_NODE=$(realpath -m "${W_NODE:-$COPY/W_node}")
DOTNET=$(realpath -m "$DOTNET")
# node_env.sh embeds these paths in shell code, so only plain characters (a $, a backtick or a quote would change it)
for p in "$COPY" "$BUILD_BIN" "$W_NODE" "$DOTNET"; do
  [[ $p =~ ^[A-Za-z0-9._/+-]*$ ]] \
    || die "--copy, --openms-bin, --w-node and --dotnet-root may hold only letters, digits and . _ / + - (node_env.sh embeds them): $p"
done
MODE=$([ $NATIVE_ONLY = 1 ] && echo native || echo build)
P_BIN=$([ $NATIVE_ONLY = 1 ] && echo "$NATIVE/OpenMS/bin" || echo "$BUILD_BIN")   # P of the untimed checks
B=(python3 "$REPO/benchmarks/bench.py" --work "$WORK" --mem-gb "$MEM_GB")
# the parameter-file comparison, next to this script (checks/freeze_P/compare_inis.py of the freeze of b2d252b442 compares the order of
# the allowed values too, which differs between two builds of P: README)
CMP=$HERE/compare_inis.py

# the steps to run
RUN=()
if [ -n "$ONLY" ]; then
  IFS=, read -r -a want <<<"$ONLY"
  for s in "${want[@]}"; do [[ " ${ALL_STEPS[*]} " == *" $s "* ]] || die "unknown step $s (steps: ${ALL_STEPS[*]})"; done
  for s in "${ALL_STEPS[@]}"; do [[ ",$ONLY," == *",$s,"* ]] && RUN+=("$s"); done
else
  started=$([ -z "$FROM" ] && echo 1 || echo 0)
  for s in "${ALL_STEPS[@]}"; do [ "$s" = "$FROM" ] && started=1; [ "$started" = 1 ] && RUN+=("$s"); done
  [ ${#RUN[@]} -gt 0 ] || die "unknown step $FROM (steps: ${ALL_STEPS[*]})"
fi
if [[ " ${RUN[*]} " == *" params "* ]] && [ ! -f "$CMP" ]; then
  die "compare_inis.py is not next to $0 (a set-up error, not task 11a): use prepare_node.sh of a prose-paper clone" \
    "that has benchmarks/node/"
fi

mkdir -p "$STATE"
exec > >(tee -a "$STATE/prepare.log") 2>&1
trap '[ $? = 3 ] || echo "prepare_node.sh: FAILED in step $STEP (line $LINENO: $BASH_COMMAND)" >&2' ERR
echo
echo "=== prepare_node.sh on $(hostname), $(date -Is)"
echo "copy $COPY; role $ROLE; --mem-gb $MEM_GB; W_node $W_NODE; P: $([ $NATIVE_ONLY = 1 ] && echo "native copy only" || echo "node build $BUILD_BIN")"
echo "steps: ${RUN[*]}"
# A pass without the step machine (--from build after --native-only, or --only) must follow a step machine that passed
# (its last line, "machine: passed"), with the same arguments: the cap, the CPUs of the role and the storage of W_node
# were checked for those only.
if [[ " ${RUN[*]} " != *" machine "* ]]; then
  [ -f "$STATE/machine.txt" ] || die "$STATE/machine.txt is missing: run the step machine first (the whole script, or --from machine)"
  grep -q '^machine: passed' "$STATE/machine.txt" \
    || die "$STATE/machine.txt is of a step machine that did not pass (or of an earlier version of this script): run --from machine"
  for x in "role: $ROLE" "memory cap: --mem-gb $MEM_GB" "W_node: $W_NODE"; do
    grep -qxF "$x" "$STATE/machine.txt" \
      || die "$STATE/machine.txt has '$(grep -m1 "^${x%%: *}:" "$STATE/machine.txt" || echo "no ${x%%: *} line")', not '$x':" \
        "give the --role, --mem-gb and --w-node of the run that passed the step machine, or run the step machine again" \
        "with the values you want (--only machine,<the steps>, or --from machine)"
  done
fi

# This shell must not carry the native copy's environment: its LD_LIBRARY_PATH would make even the node build load the
# copy's libOpenMS.so. The native copy runs only in subshells below.
for v in LD_LIBRARY_PATH OPENMS_DATA_PATH OPENMS_BIN DOTNET_ROOT PATH; do
  case "${!v:-}" in
    *"$NATIVE_NAME"*) die "\$$v names $NATIVE_NAME: env_native.sh was sourced in this shell. Run the script from a new shell." ;;
  esac
done
[ -z "${LD_PRELOAD:-}" ] || die "LD_PRELOAD is set ($LD_PRELOAD): every timed run would load it; run from a shell without it"
[ -z "${LD_LIBRARY_PATH:-}" ] || note "LD_LIBRARY_PATH is set ($LD_LIBRARY_PATH); the timed runs should load the node's own libraries"
[ -z "${OPENMS_DATA_PATH:-}" ] || note "OPENMS_DATA_PATH is set ($OPENMS_DATA_PATH); it is cleared for the node build"

PERC=""
pick_percolator() {  # the Percolator build that runs here (open point 3)
  [ -z "$PERC" ] || return 0
  local c out nf why=""
  for c in "$TOOLS/percolator-3.09/deb/usr/bin/percolator" "$TOOLS/percolator-3.09-rpm/usr/bin/percolator"; do
    if [ ! -e "$c" ]; then why+="; ${c#"$TOOLS"/}: missing"; continue; fi
    if [ ! -x "$c" ]; then why+="; ${c#"$TOOLS"/}: not executable (the step tools sets the bits; a noexec mount?)"; continue; fi
    out=$("$c" --help 2>&1 || true)
    if grep -q "Percolator version 3.09.0" <<<"$out"; then PERC=$c; return 0; fi
    nf=$(ldd "$c" 2>/dev/null | awk '/not found/ {print $1}' | tr '\n' ' ' || true)
    why+="; ${c#"$TOOLS"/}: ${nf:+libraries not found: $nf}${nf:-$(sed -n 1p <<<"$out")}"
  done
  die "neither Percolator build in tools/ prints 'Percolator version 3.09.0' here${why}. The .deb build needs" \
    "libboost-filesystem1.83.0 (sudo apt-get install libboost-filesystem1.83.0, or bash build_P.sh --deps-only);" \
    "the .rpm build Boost 1.66 (open point 3)"
}
# environments, set only in subshells
env_tools() {
  # shellcheck source=/dev/null
  source "$TOOLS/env.sh"
  export PERCOLATOR=$PERC
}
env_native() {
  [ -f "$NATIVE/env_native.sh" ] || die "the native copy is not unpacked: run the step native first"
  env_tools
  # shellcheck source=/dev/null
  source "$NATIVE/env_native.sh"
}
env_build() {  # the node build: nothing of another OpenMS
  local d dirs
  env_tools
  unset OPENMS_DATA_PATH
  IFS=: read -r -a dirs <<<"${LD_LIBRARY_PATH:-}"
  for d in "${dirs[@]}"; do
    [ ! -e "$d/libOpenMS.so" ] || die "LD_LIBRARY_PATH holds $d, which has a libOpenMS.so: run from a shell without it"
  done
  export OPENMS_BIN=$BUILD_BIN DOTNET_ROOT=$DOTNET
  export PATH="$DOTNET:$PATH"
}
env_p() { if [ $NATIVE_ONLY = 1 ]; then env_native; else env_build; fi; }  # P for the untimed checks

check_p() {  # check_p <install folder> <label>, in the environment of that P
  local dir=$1 label=$2 t out lib v m re="Revision: $P_REV([^0-9a-f]|\$)"
  [ "$(realpath "$OPENMS_BIN")" = "$(realpath "$dir/bin")" ] || die "$label: OPENMS_BIN is $OPENMS_BIN, not $dir/bin"
  for t in "${TOOL_NAMES[@]}"; do
    [ -x "$OPENMS_BIN/$t" ] || die "$label: $OPENMS_BIN/$t is missing"
    out=$(ldd "$OPENMS_BIN/$t")
    if grep -q "not found" <<<"$out"; then
      die "$label: $t: libraries not found: $(grep 'not found' <<<"$out" | tr -s ' \t\n' ' ')"
    fi
    lib=$(awk '$1 == "libOpenMS.so" {print $3}' <<<"$out")
    { [ -n "$lib" ] && [ "$(realpath "$lib")" = "$(realpath "$dir/lib/libOpenMS.so")" ]; } \
      || die "$label: $t loads libOpenMS.so from ${lib:-nowhere}, not from $dir/lib"
    out=$("$OPENMS_BIN/$t" --help < /dev/null 2>&1 || true)
    v=$(grep -m1 '^Version:' <<<"$out" || true)
    [[ $v == "Version: 3.7.0"* && $v =~ $re ]] || die "$label: $t prints '${v:-no version line}', not version 3.7.0 with Revision: $P_REV"
    ok "$label: $t, libOpenMS.so from $dir/lib, $v"
  done
  for m in "${MODELS[@]}"; do
    [ -s "$dir/share/OpenMS/models/$m" ] || die "$label: PeptDeep model $m is not in $dir/share/OpenMS/models"
  done
  [ -d "$dir/lib/openms_thermo_bridge" ] || die "$label: no Thermo bridge in $dir/lib (WITH_THERMO_RAW)"
  out=$("$DOTNET_ROOT/dotnet" --list-runtimes 2>&1 || true)
  grep -q "^Microsoft.NETCore.App 8\.0\." <<<"$out" || die "$label: no .NET 8 runtime in DOTNET_ROOT=$DOTNET_ROOT"
  ok "$label: the three PeptDeep models, the Thermo bridge; .NET runtime $(grep -m1 '^Microsoft.NETCore.App 8\.0\.' <<<"$out" | cut -d' ' -f2) in $DOTNET_ROOT"
}

version_line() {  # version_line <versions.txt> <awk test of the command, $1> <awk test of the output, $2>
  # bench.py versions writes "<command>\t<what it printed>": the output column alone is tested
  awk -F'\t' "($2) && ($3) {f = 1} END {exit !f}" "$1"
}
check_versions() {  # check_versions <versions.txt of bench.py> <bin/ of P>
  local f=$1 bin=$2 t
  [ -s "$f" ] || die "$f is missing"
  if grep -q "NOT FOUND" "$f"; then die "$f: $(grep 'NOT FOUND' "$f" | tr '\n' ' ')"; fi
  for t in "${TOOL_NAMES[@]}"; do
    version_line "$f" "\$1 == \"$bin/$t --help\"" "\$2 ~ /^Version: 3\\.7\\.0.*Revision: $P_REV([^0-9a-f]|\$)/" \
      || die "$f: no line of $bin/$t with version 3.7.0 and Revision: $P_REV"
  done
  version_line "$f" '$1 ~ /\/sage --version$/' '$2 ~ /^sage 0\.14\.6$/' || die "$f: Sage is not 0.14.7 (sage 0.14.6)"
  version_line "$f" '$1 ~ /^java -jar .* --version$/' '$2 ~ /^MSFragger version MSFragger-4\.4\.1( |$)/' \
    || die "$f: MSFragger does not print 'MSFragger version MSFragger-4.4.1'"
  version_line "$f" '$1 ~ /\/percolator --help$/' '$2 ~ /^Percolator version 3\.09\.0,/' || die "$f: Percolator is not 3.09.0"
  ok "$f: P from $bin (Revision: $P_REV), Sage 0.14.7, MSFragger 4.4.1, Percolator 3.09.0"
}

# the type in the mount table (nfs4, fuse.sshfs, beegfs, ...); stat -f, the fallback, names all FUSE types "fuseblk".
# findmnt -T lists every mount stacked on the target, the one in effect last (an NFS share under an automount: autofs,
# then nfs4)
fs_type() { local t; t=$(findmnt -no FSTYPE -T "$1" 2> /dev/null | tail -n 1 || true); echo "${t:-$(stat -f -c %T "$1")}"; }
check_storage() {  # check_storage <folder> <what it holds> [exec]: a line in machine.txt, a warning on a network file
  # system, and with exec: not on a noexec mount
  local f=$1 what=$2 t
  t=$(fs_type "$f")
  [ ! -f "$STATE/machine.txt" ] || echo "storage: $what $f on $t ($(df -P -h "$f" | awk 'NR == 2 {print $1}'))" >> "$STATE/machine.txt"
  if [[ $t =~ ^($NETWORK_FS)$ ]]; then
    echo "  WARNING: $f ($what) is on a network file system ($t): the timed runs should read from a local disk (DATASETS.md section 4.3)"
  fi
  case "$t" in
    v9fs|9p|fuseblk|ntfs|ntfs3|vfat|msdos|exfat) note "$f is on a $t file system, not a Linux one (the archives hold symlinks)" ;;
    fuse|fuse.*) [[ $t =~ ^($NETWORK_FS)$ ]] || note "$f is on the FUSE file system $t: if that is a network one, the timed runs should read from a local disk" ;;
  esac
  if [ "${3:-}" = exec ]; then
    [[ ,$(findmnt -no OPTIONS -T "$f" 2> /dev/null | tail -n 1 || true), != *,noexec,* ]] \
      || die "$f is on a noexec mount: $what cannot run from there"
  fi
}
cpus_cover() {  # cpus_cover <cpu list, e.g. 0-95,192-287> <n>: are CPUs 0..n-1 all in the list?
  awk -v list="$1" -v n="$2" 'BEGIN {
    k = split(list, parts, ",")
    for (i = 1; i <= k; i++) { m = split(parts[i], r, "-"); hi = (m > 1) ? r[2] : r[1]; for (c = r[1] + 0; c <= hi + 0; c++) have[c] = 1 }
    for (c = 0; c < n; c++) if (!(c in have)) exit 1
    exit 0 }'
}
cpus_count() { awk -v list="$1" 'BEGIN { k = split(list, parts, ","); n = 0
  for (i = 1; i <= k; i++) { m = split(parts[i], r, "-"); n += (m > 1) ? r[2] - r[1] + 1 : 1 }; print n }'; }
cap_probe() {  # cap_probe <GB>: inside a scope with that cap: its memory.max and memory.swap.max; "cpus <list>", the
  # CPUs a process there gets from taskset -c 0-<last CPU> (bench.py pins the scaling runs so; the kernel keeps only the
  # CPUs of the cpuset in force, which on Ubuntu 24.04 is that of a cgroup above the user's, as the user's have no cpuset
  # controller); "unpinned <list>", the CPUs of a process there without taskset (the other timed runs: the affinity of
  # this shell, which the scope keeps); and every cgroup above it: "above <path> <memory.max> <memory.high> <cpu.max>"
  local last; last=$(( $(getconf _NPROCESSORS_CONF) - 1 ))
  # shellcheck disable=SC2016
  timeout 120 systemd-run --user --scope --quiet -p "MemoryMax=${1}G" -p MemorySwapMax=0 -- sh -c '
    p=$(cut -d: -f3 /proc/self/cgroup); c=/sys/fs/cgroup$p
    cat "$c/memory.max" "$c/memory.swap.max"
    echo "cpus $(taskset -c "0-$1" sh -c "sed -n \"s/^Cpus_allowed_list:[[:space:]]*//p\" /proc/self/status" 2>/dev/null || echo -)"
    echo "unpinned $(sed -n "s/^Cpus_allowed_list:[[:space:]]*//p" /proc/self/status)"
    while [ -n "$p" ] && [ "$p" != / ]; do
      p=$(dirname "$p"); d=/sys/fs/cgroup${p%/}
      echo "above $p $(cat "$d/memory.max" 2>/dev/null || echo -) $(cat "$d/memory.high" 2>/dev/null || echo -) $({ cat "$d/cpu.max" 2>/dev/null || echo -; } | tr " " /)"
    done' probe "$last"
}

step_machine() {
  local m=$STATE/machine.txt out kb ncpu cores cap path mmax mhigh cmax x y cpus unpinned quota="" f t malloc_env old=""
  # glibc's malloc settings change the memory and time of every timed run, and the order of ProSE's enzyme list
  malloc_env=$(env | grep -E '^(MALLOC_[A-Z_]*|GLIBC_TUNABLES)=' | paste -sd ' ' - || true)
  # the role, N and W_node of the step machine before, to note a change (a new N given without the --w-node of before
  # would switch to the default W_node)
  [ ! -f "$m" ] || old=$(grep -E '^(role|memory cap|W_node): ' "$m" || true)
  {
    echo "# prepare_node.sh, $(date -Is)"
    echo "host: $(hostname -f 2> /dev/null || hostname)"
    echo "role: $ROLE"
    echo "memory cap: --mem-gb $MEM_GB"
    echo "W_node: $W_NODE"
    echo "P of the untimed checks: $([ $NATIVE_ONLY = 1 ] && echo "native copy $NATIVE" || echo "node build $BUILD_BIN")$([ $HAND_BUILD = 1 ] && echo " (--hand-build: not made by build_P.sh)")"
    echo "malloc settings of this shell: ${malloc_env:-none, the defaults of glibc}"
    echo; echo "## RAM"; grep -E '^(MemTotal|SwapTotal):' /proc/meminfo
    echo; echo "## CPU"; lscpu
    echo "SMT control: $(cat /sys/devices/system/cpu/smt/control 2> /dev/null || echo unknown)"
    echo; echo "## OS"; grep '^PRETTY_NAME=' /etc/os-release || true; uname -srvm; ldd --version 2>&1 | sed -n 1p
    echo; echo "## storage of $COPY"; df -hT "$COPY"; findmnt -T "$COPY" || true
    echo; lsblk -o NAME,MODEL,SIZE,ROTA,TYPE,FSTYPE,MOUNTPOINTS 2> /dev/null || lsblk 2> /dev/null || true
    echo; echo "## software"; python3 --version; { java -version 2>&1 || echo "java: not found"; } | sed -n 1p; git --version
    echo; echo "## cgroup"; stat -f -c %T /sys/fs/cgroup; cat /sys/fs/cgroup/cgroup.controllers 2> /dev/null || true
  } > "$m"
  ok "machine record: $m"
  for x in "role: $ROLE" "memory cap: --mem-gb $MEM_GB" "W_node: $W_NODE"; do
    y=$(grep -m1 "^${x%%: *}: " <<<"$old" || true)
    [ -z "$y" ] || [ "$y" = "$x" ] || note "${x%%: *} is now '${x#*: }'; the step machine before had '${y#*: }'$([ "${x%%: *}" != W_node ] \
      || echo " (to keep that W_node, run the step machine again with --w-node ${y#*: }; a new W_node needs the step copy, which takes the two vendor files from an earlier one)")"
  done
  [ -z "$malloc_env" ] || note "glibc's malloc is tuned in this shell ($malloc_env): it changes the memory and time of the timed runs; record it with the results, or run from a shell without it"

  # storage: the copy and W_node on a local disk (DATASETS.md section 4.3), the copy executable (the node build is
  # checked in the step build, which every run with it passes)
  mkdir -p "$W_NODE"
  check_storage "$COPY" "the copy (Sage, Percolator, P's native copy)" exec
  check_storage "$W_NODE" "W_node"

  # the memory cap: in force in a scope of systemd-run --user, and not undercut by a cgroup above it
  out=$(cap_probe 1 2>&1) \
    || die "systemd-run --user failed ($(tr '\n' ' ' <<<"$out")): it needs a login session with the user's bus (XDG_RUNTIME_DIR, DBUS_SESSION_BUS_ADDRESS) and cgroup v2 with the memory controller delegated to the user"
  [ "$(sed -n 1p <<<"$out")" = 1073741824 ] || die "a cap of 1G is not in force: memory.max is '$(sed -n 1p <<<"$out")', not 1073741824"
  out=$(cap_probe "$MEM_GB" 2>&1) || die "systemd-run --user with MemoryMax=${MEM_GB}G failed ($out)"
  { echo; echo "## memory cap check (systemd-run --user --scope, MemoryMax=${MEM_GB}G, MemorySwapMax=0)"; echo "$out"; } >> "$m"
  cap=$(sed -n '1p;2p' <<<"$out" | xargs)
  [ "$cap" = "$((MEM_GB * 1073741824)) 0" ] || die "a cap of ${MEM_GB}G without swap is not in force: memory.max and memory.swap.max are '$cap'"
  while read -r _ path mmax mhigh cmax; do
    for x in "$mmax" "$mhigh"; do
      if [[ $x =~ ^[0-9]+$ ]] && [ "$x" -lt $((MEM_GB * 1073741824)) ]; then
        die "the cgroup $path above the scope limits memory to $((x / 1048576)) MB (memory.max/memory.high $mmax/$mhigh):" \
          "below --mem-gb $MEM_GB, so the engines would be held at that limit instead"
      fi
    done
    if [[ $cmax =~ ^([0-9]+)/([0-9]+)$ ]]; then
      x=$((BASH_REMATCH[1] / BASH_REMATCH[2]))
      if [ -z "$quota" ] || [ "$x" -lt "$quota" ]; then quota=$x; fi
    fi
  done < <(grep '^above ' <<<"$out" || true)   # none when the scope's cgroup sits right below the root (a container)
  ok "the memory cap is in force (1G and ${MEM_GB}G, no swap; no cgroup above it has a lower limit)"
  kb=$(awk '/^MemTotal:/ {print $2}' /proc/meminfo)
  [ $((MEM_GB * 1048576)) -le "$kb" ] || note "--mem-gb $MEM_GB is more than the RAM ($((kb / 1048576)) GB in MemTotal)"

  # the CPUs a process pinned with taskset gets in a scope of this user (what the cpusets in force leave; the scaling
  # runs), those of one without taskset (the other timed runs), and the CPU quota of the cgroups above it
  cpus=$(sed -n 's/^cpus //p' <<<"$out"); unpinned=$(sed -n 's/^unpinned //p' <<<"$out")
  [[ $cpus =~ ^[0-9][0-9,-]*$ ]] || die "the CPUs that taskset gets in a scope of this user cannot be read ('$cpus'; taskset of util-linux?)"
  [[ $unpinned =~ ^[0-9][0-9,-]*$ ]] || die "the CPUs of a process in a scope of this user cannot be read ('$unpinned')"
  ncpu=$(lscpu -p=CPU | grep -vc '^#')
  if [ "$ROLE" = scaling ]; then
    [ "$ncpu" -ge 192 ] || die "the scaling node needs CPUs 0-191; this one has $ncpu"
    cores=$(lscpu -p=CPU,CORE,SOCKET | grep -v '^#' | awk -F, '$1 <= 191 {print $3 "," $2}' | sort -u | wc -l)
    [ "$cores" -eq 192 ] || die "CPUs 0-191 are $cores different cores, not 192 (SMT siblings among them?)"
    cpus_cover "$cpus" 192 || die "in a scope of this user, taskset gets only CPUs $cpus, not all of 0-191 (a cpuset, e.g. AllowedCPUs of user.slice)"
    [ -z "$quota" ] || [ "$quota" -ge 192 ] || die "a cgroup above the user's scopes allows only $quota CPUs (cpu.max), not 192"
    echo "scaling node: CPUs 0-191 are 192 different cores; taskset gets CPUs $cpus in a scope, a run without taskset CPUs $unpinned; CPU quota above it: ${quota:-none}" >> "$m"
    ok "CPUs 0-191 are 192 different cores, and a process in a scope of this user may run on all of them"
  else
    # the engine comparison's runs are not pinned: they get the CPUs of the shell that starts bench.py
    x=$(cpus_count "$unpinned")
    if [ -n "$quota" ] && [ "$quota" -lt "$x" ]; then x=$quota; fi
    echo "engine node: $ncpu CPUs; a run without taskset gets CPUs $unpinned in a scope (from this shell), taskset CPUs $cpus; CPU quota above it: ${quota:-none}" >> "$m"
    if [ "$x" -ge 16 ]; then ok "a process in a scope of this user may run on $x CPUs (CPUs $unpinned, not pinned)"
    else note "the engine comparison runs 16 threads; a process in a scope of this user may run on $x CPUs (CPUs $unpinned, not pinned$([ "$unpinned" = "$cpus" ] || echo "; with taskset: $cpus, so this shell's affinity is narrower: start the benchmark from a shell without it"))"; fi
  fi
  # the mark that every check of this step passed (a later pass without the step machine, and node_env.sh, need it; a
  # new run of the step rewrites machine.txt from its first line, so one that fails drops the mark)
  echo "machine: passed $(date -Is)" >> "$m"
}

step_tools() {
  local out
  chmod +x "$TOOLS"/sage-v0.14.7/*/sage "$TOOLS"/percolator-3.09/deb/usr/bin/* "$TOOLS"/percolator-3.09-rpm/usr/bin/*
  ok "executable bits of Sage and Percolator set"
  [ -x /usr/bin/time ] && /usr/bin/time -v true 2> /dev/null \
    || die "/usr/bin/time is missing (bench.py measures every timed run with /usr/bin/time -v): sudo apt-get install time, or bash build_P.sh --deps-only"
  command -v taskset > /dev/null || die "taskset is missing (util-linux)"
  ok "/usr/bin/time -v and taskset ($(command -v taskset))"
  pick_percolator
  (
    env_tools
    out=$("$PERCOLATOR" --help 2>&1 || true)
    ok "Percolator: $PERCOLATOR ($(grep -m1 -o 'Percolator version [^,]*' <<<"$out"))"
    [ -x "$SAGE" ] || die "Sage is not at $SAGE (tools/env.sh), or not executable"
    out=$("$SAGE" --version 2>&1 || true)
    [[ $out == *"sage 0.14.6"* ]] || die "$SAGE prints '$out', not 'sage 0.14.6' (the 0.14.7 release)"
    ok "Sage: $SAGE ($out)"
    command -v java > /dev/null || die "no java on the PATH (MSFragger needs it): sudo apt-get install openjdk-21-jre-headless, or bash build_P.sh --deps-only"
    [ -f "$MSFRAGGER_JAR" ] || die "MSFragger is not at $MSFRAGGER_JAR (tools/env.sh)"
    out=$(java -jar "$MSFRAGGER_JAR" --version 2>&1 || true)
    # what MSFragger prints, not its path (a jar that Java cannot open makes Java print the path)
    grep -Eq '^MSFragger version MSFragger-4\.4\.1( |$)' <<<"$out" \
      || die "$MSFRAGGER_JAR does not print 'MSFragger version MSFragger-4.4.1': $(sed -n 1p <<<"$out")"
    ok "MSFragger 4.4.1 with $(java -version 2>&1 | sed -n 1p)"
  )
  [ ! -f "$STATE/machine.txt" ] || echo "tools: /usr/bin/time, $(command -v taskset), Percolator $PERC" >> "$STATE/machine.txt"
  note "MSFragger's licence (academic, non-transferable: tools/msfragger/README.txt) must cover the person who runs it (open point 2)"
}

step_copy() {
  local -a g=(git -c "safe.directory=$REPO" -C "$REPO")
  local changed n f d want got
  [ -e "$REPO/.git" ] || die "$REPO is no Git clone of prose-paper (git clone https://github.com/timosachsenberg/prose-paper)"
  "${g[@]}" merge-base --is-ancestor "$PAPER_MIN" HEAD 2>/dev/null \
    || die "prose-paper is at $("${g[@]}" rev-parse --short HEAD), not at ${PAPER_MIN:0:7} or later (git pull; a shallow clone cannot tell)"
  changed=$("${g[@]}" status --porcelain --untracked-files=no)
  [ -z "$changed" ] || die "prose-paper has changed files (a copy from Windows has CRLF line ends: clone it afresh): $(tr '\n' ' ' <<<"$changed")"
  ok "prose-paper at $("${g[@]}" log -1 --format='%h (%cs) %s')"
  for f in "$TOOLS/env.sh" "$TOOLS/openms.sha256" "$WORK/db" "$SMOKE/vendor/BSA1.mzML" "$SMOKE/vendor/BSA2.mzML" "$SMOKE/vendor/BSA3.mzML"; do
    [ -e "$f" ] || die "$f is missing (HANDOFF, Copy to the nodes)"
  done

  (cd "$TOOLS" && grep -F " $NATIVE_NAME-native.tar.gz" openms.sha256 | sha256sum -c --strict -) \
    || die "tools/$NATIVE_NAME-native.tar.gz is missing or differs from tools/openms.sha256"
  f=openms-docker/prose-bench_openms-tools_3.7.0-$P_SHORT.tar.gz
  if [ -e "$TOOLS/$f" ]; then
    (cd "$TOOLS" && grep -F " $f" openms.sha256 | sha256sum -c --strict -) || die "tools/$f differs from tools/openms.sha256"
  else
    note "tools/$f is not here (needed only to run P in Docker)"
  fi

  # the two vendor files into W_node: from work/vendor/ (the copy, moved), else from an earlier W_node: the default one,
  # or one in which an earlier step copy found or put them (its ok and note lines in prepare.log), so that a new
  # --w-node gets them too. From an earlier W_node by a hard link where it can (that W_node keeps them, and the
  # node_env.sh written for it stays good), else moved. A symlink is never linked or moved as it is (a relative one would
  # point to nothing from another folder): W_node gets a symlink to its file
  local -a from=("$WORK/vendor" "$COPY/W_node/vendor")
  [ ! -f "$STATE/prepare.log" ] \
    || mapfile -t -O 2 from < <(sed -n -e 's|^  note: moved .* to \(/.*\)/$|\1|p' \
      -e 's|^  ok: the two vendor files of W_node in \(/[^,]*\), as in benchmarks/vendor\.sha256$|\1|p' \
      "$STATE/prepare.log" | sort -u || true)
  mkdir -p "$W_NODE/vendor"
  for f in "${NODE_VENDOR[@]}"; do
    if [ -L "$W_NODE/vendor/$f" ] && [ ! -e "$W_NODE/vendor/$f" ]; then
      note "removed $W_NODE/vendor/$f, a symlink to nothing ($(readlink "$W_NODE/vendor/$f"))"
      rm -f "$W_NODE/vendor/$f"
    fi
    if [ ! -e "$W_NODE/vendor/$f" ]; then
      for d in "${from[@]}"; do
        if [ "$d" != "$W_NODE/vendor" ] && [ -e "$d/$f" ]; then
          if [ -L "$d/$f" ]; then
            ln -s "$(realpath -e "$d/$f")" "$W_NODE/vendor/$f"
            note "linked $W_NODE/vendor/$f to $(realpath -e "$d/$f") (a symlink, as $d/$f is one)"
          elif [ "$d" != "$WORK/vendor" ] && ln "$d/$f" "$W_NODE/vendor/$f" 2> /dev/null; then
            note "linked $d/$f into $W_NODE/vendor/ (a hard link: $d keeps it)"
          else
            mv "$d/$f" "$W_NODE/vendor/$f"
            note "moved $d/$f to $W_NODE/vendor/"
          fi
          break
        fi
      done
    fi
    [ -e "$W_NODE/vendor/$f" ] || die "$f is in none of $W_NODE/vendor/ and $(printf '%s/\n' "${from[@]}" | awk -v w="$W_NODE/vendor/" '$0 != w && !s[$0]++' | paste -sd ' ' -)" \
      "(work/vendor/, the default W_node and each W_node of an earlier step copy in prepare.log): put it into $W_NODE/vendor/ (HANDOFF, Copy to the nodes)"
    want=$(awk -v f="$f" '$2 == f {print $1}' "$REPO/benchmarks/vendor.sha256")
    [ -n "$want" ] || die "$f is not in benchmarks/vendor.sha256"
    got=$(sha256sum "$W_NODE/vendor/$f" | cut -d' ' -f1)
    [ "$got" = "$want" ] || die "$W_NODE/vendor/$f: SHA256 $got, benchmarks/vendor.sha256 has $want"
  done
  rmdir "$WORK/vendor" 2> /dev/null || true
  ok "the two vendor files of W_node in $W_NODE/vendor, as in benchmarks/vendor.sha256"

  n=$(grep -c . "$REPO/datasets/mzml.sha256")
  [ "$n" -eq 92 ] || die "datasets/mzml.sha256 has $n lines, not 92"
  [ -d "$WORK/mzml" ] || die "$WORK/mzml is missing"
  echo "  checking the 92 mzML against datasets/mzml.sha256 (116 GB to read), $(date +%T) ..."
  (cd "$WORK/mzml" && sha256sum -c --quiet --strict "$REPO/datasets/mzml.sha256") \
    || die "mzML in $WORK/mzml differ from datasets/mzml.sha256 or are missing (lines above)"
  ok "92 mzML as in datasets/mzml.sha256 ($(date +%T))"
  n=$(find "$WORK/mzml/" -maxdepth 1 -name '*.mzML' | wc -l)
  [ "$n" -eq 92 ] || note "$WORK/mzml holds $n mzML, 92 of them listed"
}

step_native() {
  local tgz=$TOOLS/$NATIVE_NAME-native.tar.gz tmp missing
  rm -rf "$TOOLS"/.native_unpack.*   # what an unpack that stopped left
  if [ ! -e "$NATIVE" ]; then
    # into a temporary folder first: an unpack that stops (disk full, Ctrl-C) leaves no $NATIVE behind
    tmp=$(mktemp -d "$TOOLS/.native_unpack.XXXXXX")
    tar -C "$tmp" -xzf "$tgz" || die "could not unpack $tgz (disk full?)"
    [ -f "$tmp/$NATIVE_NAME/env_native.sh" ] || die "$tgz holds no $NATIVE_NAME/env_native.sh"
    mv "$tmp/$NATIVE_NAME" "$NATIVE"
    rmdir "$tmp"
    ok "unpacked tools/$NATIVE_NAME-native.tar.gz into $NATIVE"
  fi
  # every file of the tarball there (an unpack by hand may have stopped half-way)
  missing=$( { tar -tzf "$tgz" || echo "(tar -tzf failed)"; } \
    | while read -r f; do [ -e "$TOOLS/$f" ] || [ -L "$TOOLS/$f" ] || echo "$f"; done | head -5 || true)
  [ -z "$missing" ] || die "$NATIVE lacks files of $tgz (an unpack that stopped?), e.g. $(tr '\n' ' ' <<<"$missing"): remove $NATIVE and run again"
  ok "$NATIVE holds every file of the tarball"
  ( env_native; check_p "$NATIVE/OpenMS" "native copy" )
}

step_build() {
  local dir r; dir=$(dirname "$BUILD_BIN"); r=$dir/BUILD_P.txt
  # the node build's storage, and into machine.txt which P the untimed checks use from here on (a run --from build
  # after --native-only does not pass the step machine)
  check_storage "$dir" "the node build" exec
  [ ! -f "$STATE/machine.txt" ] || echo "P of the untimed checks from $(date -Is): node build $BUILD_BIN$([ $HAND_BUILD = 1 ] && echo " (--hand-build: not made by build_P.sh)")" >> "$STATE/machine.txt"
  (
    env_build
    case "${LD_LIBRARY_PATH:-} ${OPENMS_DATA_PATH:-}" in
      *"$NATIVE_NAME"*) die "LD_LIBRARY_PATH or OPENMS_DATA_PATH names the native copy" ;;
    esac
    check_p "$dir" "node build"
  )
  if [ $HAND_BUILD = 1 ]; then
    note "--hand-build: $dir was not checked for -march=native, its configure output or its WITH_* options (no BUILD_P.txt)"
    return 0
  fi
  [ -f "$r" ] || die "$r is missing: build P with build_P.sh (or give --hand-build for a build of your own)"
  grep -Fq "P = OpenMS $P_COMMIT " "$r" || die "$r is not of P ($P_COMMIT)"
  grep -Fq "built by build_P.sh on $(hostname)," "$r" \
    || die "$r: P was built on another node ($(sed -n 's/.*built by build_P.sh on \([^,]*\),.*/\1/p' "$r")); build it on this one"
  for v in WITH_ONNX WITH_THERMO_RAW WITH_OPENTIMS; do
    grep -Eq "^  $v:BOOL=(ON|TRUE|1)\$" "$r" || die "$r: $v is not ON"
  done
  if grep -q '^configure output: DIFFERS' "$r"; then
    echo "  WARNING: $r: the configure output differed from the image's and was accepted (--accept-configure-diff):"
    sed -n '/^configure output: DIFFERS/,/^[^ ]/p' "$r" | sed '1d;$d'
  else
    grep -q '^configure output: as in the image' "$r" || die "$r says nothing about the configure output"
  fi
  ok "built by build_P.sh on this node: $(sed -n 1p "$r")"
  if grep -q 'packages of the image.s base stage .* with another version here: [1-9]' "$r"; then
    note "$(grep -o 'packages of the image.s base stage .* with another version here: [0-9]*' "$r") (listed in $r)"
  fi
}

# The subshells below stand left of || (their output goes to a log): set -e does not work in them, so each command
# that must not fail ends in || exit.
step_params() {
  local out=$STATE/inis
  rm -rf "$out"; mkdir -p "$out"
  ( env_p || exit 1
    python3 "$REPO/datasets/params/make_inis.py" "$OPENMS_BIN/ProSE" "$out" || exit 1
  ) > "$STATE/make_inis.log" 2>&1 || die "make_inis.py failed: $STATE/make_inis.log"
  python3 -I -B "$CMP" "$out" "$REPO/datasets/params" > "$STATE/compare_inis.txt" 2>&1 || true
  cat "$STATE/compare_inis.txt"
  grep -q '^result: PASS' "$STATE/compare_inis.txt" \
    || die "the parameter files written with P differ from datasets/params ($STATE/compare_inis.txt): the run order stops here (task 11a)"
  ok "the 12 parameter files written with P: PASS (P from the $MODE; $CMP)"
}

step_versions() {
  pick_percolator
  rm -f "$WORK/versions.txt"
  ( env_p || exit 1
    cd "$REPO/benchmarks" || exit 1
    "${B[@]}" versions || exit 1
    "${B[@]}" databases || exit 1
  ) 2>&1 | tee "$STATE/versions.log" || die "bench.py versions or databases failed ($STATE/versions.log)"
  check_versions "$WORK/versions.txt" "$P_BIN"
  ok "bench.py databases: the databases in $WORK/db checked (P from the $MODE)"
}

step_smoke() {
  pick_percolator
  local s=$STATE/smoke_$MODE n bad f e
  rm -rf "$s"; mkdir -p "$s"
  cp -r "$SMOKE/vendor" "$s/vendor"
  local bs=(python3 "$REPO/benchmarks/bench.py" --work "$s" --runs "$REPO/benchmarks/smoke/runs.tsv" --mem-gb "$MEM_GB")
  echo "  smoke test in $s, $(date +%T) (about 15 minutes; log $s/smoke.log)"
  (
    # the commands of the README's smoke test, one by one; the first that fails ends the subshell. set -e does not
    # work here (the subshell stands left of ||), hence the explicit exit.
    run() { "${bs[@]}" "$@" || { echo "prepare_node.sh: bench.py $* failed (exit $?)"; exit 1; }; }
    env_p || exit 1
    cd "$REPO/benchmarks" || exit 1
    run versions
    run databases
    run fetch
    run convert
    for e in "${ENGINES[@]}"; do
      run search --engine "$e" --db td --threads 8 --timed
      run search --engine "$e" --db entrap --threads 8
      run count --engine "$e" --db td
      run count --engine "$e" --db entrap
      run batch --engine "$e" --threads 8
      run scaling --engine "$e" --grid 1,2,4,8
    done
    run collect
  ) > "$s/smoke.log" 2>&1 || die "the smoke test failed ($(date +%T)): $(grep -m1 'prepare_node.sh: bench.py' "$s/smoke.log" || echo 'see the log'); $s/smoke.log, $s/commands.log"
  check_versions "$s/versions.txt" "$P_BIN"
  for f in timings.tsv counts.tsv coverage.tsv commands.log; do [ -s "$s/$f" ] || die "the smoke test wrote no $s/$f"; done
  if grep -Eq '^# (FAILED|NOT COUNTED|NO TIMING)' "$s/commands.log"; then
    die "$s/commands.log: $(grep -E '^# (FAILED|NOT COUNTED|NO TIMING)' "$s/commands.log" | tr '\n' ' ')"
  fi
  for e in "${ENGINES[@]}"; do
    [ -d "$s/out/$e" ] || die "the smoke test has no search of $e ($s/out/$e)"
    awk -F'\t' -v e="$e" 'NR > 1 && $1 == e {f = 1} END {exit !f}' "$s/timings.tsv" || die "$s/timings.tsv has no row of $e"
  done
  n=$(find "$s/out" -name status | wc -l)
  bad=$(find "$s/out" -name status -exec grep -L '^ok$' {} + || true)
  [ "$n" -gt 0 ] && [ -z "$bad" ] || die "smoke searches not ok: ${bad:-no search folder}"
  bad=$(awk -F'\t' 'NR > 1 && $NF != "0"' "$s/timings.tsv")
  [ -z "$bad" ] || die "$s/timings.tsv: runs that did not exit 0: $(tr '\n' ' ' <<<"$bad")"
  # coverage.tsv: every search of the run table ok and counted (Sage's not_run_by_design aside), every other one ok
  bad=$(awk -F'\t' 'NR > 1 && $5 !~ /^not_run_by_design/ && !($5 == "ok" && ($2 != "per_file" || $6 == "yes"))' "$s/coverage.tsv")
  [ -z "$bad" ] || die "$s/coverage.tsv: searches not ok or not counted: $(tr '\n' ' ' <<<"$bad")"
  ok "smoke test ($(date +%T)): every command exit 0, $n searches ok, every timed run exit 0, every search of the" \
    "run table counted; timings.tsv, counts.tsv and coverage.tsv written (P from the $MODE)"
}

step_env() {
  pick_percolator
  local f=$COPY/node_env.sh h lib v; h=$(hostname); lib=$(realpath "$(dirname "$BUILD_BIN")/lib")/libOpenMS.so
  # BW is the driver with W_node: the checks of step 5 need its two vendor files (the step copy puts them there)
  for v in "${NODE_VENDOR[@]}"; do
    [ -e "$W_NODE/vendor/$v" ] || die "$W_NODE/vendor/$v is missing: run --only copy,env with this --w-node (the step copy" \
      "takes the file from work/vendor/ or an earlier W_node, as prepare.log records; it reads the 116 GB of mzML again)," \
      "or, to use the W_node that has the two files, the steps machine and env with that --w-node (--only machine,env;" \
      "after a new --mem-gb, --only machine,smoke,env)"
  done
  {
    echo "# Written by prepare_node.sh on $h, $(date -Is): the environment of the benchmark on this node."
    echo "# In a new shell in which env_native.sh was never sourced:  source $f"
    echo "unset B BW   # a refused source leaves no driver of an earlier one"
    echo "if [ \"\$(hostname)\" != \"$h\" ]; then echo \"node_env.sh: written on $h, not on \$(hostname)\" >&2; return 1; fi"
    echo "case \"\${LD_LIBRARY_PATH:-}:\${OPENMS_DATA_PATH:-}\" in"
    echo "  *$NATIVE_NAME*) echo 'node_env.sh: env_native.sh was sourced in this shell; open a new one' >&2; return 1 ;;"
    echo "esac"
    echo "if [ -n \"\${LD_PRELOAD:-}\" ]; then echo \"node_env.sh: LD_PRELOAD is set (\$LD_PRELOAD); every timed run would load it\" >&2; return 1; fi"
    echo "# the cap and W_node of B and BW must be those of the last step machine, and that step must have passed"
    echo "_m=$STATE/machine.txt"
    echo "if ! grep -q '^machine: passed' \"\$_m\" 2>/dev/null || ! grep -qxF $(printf %q "memory cap: --mem-gb $MEM_GB") \"\$_m\" || ! grep -qxF $(printf %q "W_node: $W_NODE") \"\$_m\"; then"
    echo "  echo \"node_env.sh: written for --mem-gb $MEM_GB and W_node $W_NODE, but the last step machine (\$_m) had other ones or did not pass: run prepare_node.sh --from machine with the arguments you want (or, after a passed step machine, --only smoke,env for a new --mem-gb with the same --role and --w-node, --only copy,env for a new --w-node)\" >&2; unset _m; return 1"
    echo "fi"
    echo "unset _m"
    echo "source $TOOLS/env.sh"
    echo "unset OPENMS_DATA_PATH   # the node build reads its own share/"
    echo "export OPENMS_BIN=$BUILD_BIN PERCOLATOR=$PERC DOTNET_ROOT=$DOTNET"
    echo "export PATH=\"\$DOTNET_ROOT:\$PATH\""
    echo "_l=\$(ldd \"\$OPENMS_BIN/ProSE\" | awk '\$1 == \"libOpenMS.so\" {print \$3}')"
    echo "if [ \"\$(realpath \"\${_l:-/nonexistent}\" 2>/dev/null)\" != \"$lib\" ]; then"
    echo "  echo \"node_env.sh: ProSE loads libOpenMS.so from \${_l:-nowhere}, not $lib (LD_LIBRARY_PATH?)\" >&2; unset _l; return 1"
    echo "fi"
    echo "unset _l"
    echo "# the driver with the main work folder, and with W_node (step 5), which needs the two vendor files there"
    echo "B=\"python3 $REPO/benchmarks/bench.py --work $WORK --mem-gb $MEM_GB\""
    echo "if [ -e $W_NODE/vendor/${NODE_VENDOR[0]} ] && [ -e $W_NODE/vendor/${NODE_VENDOR[1]} ]; then"
    echo "  BW=\"python3 $REPO/benchmarks/bench.py --work $W_NODE --mem-gb $MEM_GB\""
    echo "else"
    echo "  echo \"node_env.sh: BW is not set: $W_NODE/vendor/ lacks the two vendor files of step 5 (a step copy with another --w-node moved them?): run prepare_node.sh --only copy,env with --w-node $W_NODE. B is set.\" >&2"
    echo "fi"
  } > "$f"
  ok "$f written:"
  sed 's/^/    /' "$f"
  # shellcheck source=/dev/null
  ( source "$f" > /dev/null && [ "$OPENMS_BIN" = "$BUILD_BIN" ] && [ -n "${BW:-}" ] ) || die "$f does not work in this shell"
  ok "$f sourced in a subshell: OPENMS_BIN, BW, and ProSE loads $lib"
}

t0=$(date +%s)
for STEP in "${RUN[@]}"; do
  if [ $NATIVE_ONLY = 1 ] && { [ "$STEP" = build ] || [ "$STEP" = env ]; }; then
    echo; echo "--- $STEP: left out (--native-only)"
    continue
  fi
  echo; echo "--- $STEP ($(date +%T))"
  "step_$STEP"
done
STEP=end
echo
echo "=== prepare_node.sh: done ($(( ($(date +%s) - t0) / 60 )) min): ${RUN[*]}"
if [ $NATIVE_ONLY = 1 ]; then
  echo "The timed runs need P built on this node: build_P.sh, then prepare_node.sh with the same --copy, --mem-gb, --role and --w-node, and --openms-bin <prefix>/bin --from build"
elif [[ " ${RUN[*]} " == *" env "* ]]; then
  echo "Next (DATASETS.md section 5): source $COPY/node_env.sh; the checks of step 5 in $W_NODE with \$BW; then the main searches with \$B"
else
  echo "node_env.sh was not written in this run. After a new --mem-gb, run --only smoke,env with it (and the same --role" \
    "and --w-node); after a new --w-node, --only copy,env (the step copy takes the two vendor files from the earlier" \
    "W_node). node_env.sh refuses to load while the last step machine had other values, and sets no BW while W_node" \
    "lacks the two files."
fi
echo "Left to you: MSFragger's licence must cover the person who runs it (open point 2)."
