#!/usr/bin/env bash
# Builds P, the frozen OpenMS of the ProSE benchmark, on a benchmark node, the way OpenMS's dockerfiles/Dockerfile
# builds it (its stages base and build; the image prose-bench/openms-tools:3.7.0-b2d252b442 of 2026-11-16).
# datasets/DATASETS.md section 4.1 and section 5, task 2; benchmarks/node/README.md.
#
#   P = OpenMS develop b2d252b4426f74a1d45b199e3d1f8bbcb9c87253, tag prose-benchmark-2026-11-16, version 3.7.0.
#
# usage: build_P.sh --prefix <install folder> [--work <folder>] [--jobs <N>] [--skip-deps | --deps-only]
#                   [--accept-configure-diff]
#
#   --prefix     where P is installed (bin/, lib/, share/): a new or empty folder of this node, or an earlier install of
#                this script on this node (it is emptied before each build)
#   --work       source, build tree and the logs build_P.log and configure.log (default: ./build_P_b2d252b442; about
#                4 GB; best on a local disk of the node)
#   --jobs       parallel build jobs (default: the CPUs, at most one per 2 GB of available memory)
#   --skip-deps  install no dependency: they must be there already (they are checked all the same)
#   --deps-only  install the dependencies and stop (its log too goes to --work, by default under the current folder)
#   --accept-configure-diff
#                go on although CMake's configure output differs from the image's (see below); the differences go into
#                <prefix>/BUILD_P.txt. Only after reading <work>/configure.diff.
#
# Needs Ubuntu 24.04 on x86_64, like the image. Run it as yourself, not with sudo: it calls sudo itself to install the
# dependencies (or runs them directly as root, e.g. in a container); the build does not need it.
#
# The dependencies of the Dockerfile's base stage:
#   - its apt packages (the compilers, libsvm-dev, libzip-dev, ..., libboost-dev, libicu74), with Ubuntu's universe
#     component enabled. apt installs Ubuntu 24.04's current versions; GCC must be 13.3.0 as in the image. The
#     versions the image got (image_packages.txt, from the log of its base stage) are compared, and every difference
#     goes into BUILD_P.txt;
#   - Arrow and Parquet 24.0.0-1 (libparquet-dev) from Apache's apt repository, pinned to 24.* as in the image;
#   - CMake 3.28.1, Kitware's installer, in /opt/cmake;
#   - libxml2 2.15.4, built from source into /opt/libxml2 (Ubuntu 24.04 has 2.9.14; OpenMS needs 2.13 or later);
#   - ONNX Runtime 1.30.0, Microsoft's release, in /opt/onnxruntime (WITH_ONNX: the PeptDeep models);
#   - the .NET SDK 8.0.428 (runtime and host pack 8.0.34) in /usr/share/dotnet, by Microsoft's dotnet-install.sh
#     (WITH_THERMO_RAW; Ubuntu's dotnet-sdk-8.0 lacks the host pack the Thermo bridge needs).
# Not in the image, but needed by the other tools of the benchmark on the node: python3, time (/usr/bin/time),
# util-linux (taskset), openjdk-21-jre-headless (MSFragger; OpenJDK 21 as on the preparation PC) and
# libboost-filesystem1.83.0 (Percolator's .deb build).
# The downloads of CMake, libxml2 and ONNX Runtime are checked by their SHA256. Three files are not, as their
# makers change them in place, so they cannot be pinned: Microsoft's dotnet-install.sh, Apache's
# apache-arrow-apt-source-latest-noble.deb and KEYS (the image took the same files); their SHA256 go into the log, and
# BUILD_P.txt records the Arrow apt source and keyring that are installed. Downloads go to a temporary folder in
# /var/tmp. apt never removes a package here (--no-remove): if it would have to, the script stops. A folder in /opt
# that holds another version, or Arrow packages the image did not have, stop the script instead of being changed.
# Unlike the image, nothing is linked into /usr/local/bin. The Dockerfile also puts the search engines of OpenMS's
# THIRDPARTY repository on the PATH; OpenMS's CMake uses them only to add tests (src/tests/topp/THIRDPARTY,
# src/tests/class_tests), so they change no binary and are left out here.
#
# Then the build stage, in a clean environment (no variable of your shell but HOME, USER and the proxy settings; PATH
# /opt/cmake/bin, /usr/share/dotnet and the system folders, without /usr/local, so that ld and as are Ubuntu's): the
# CMake call of the Dockerfile (checks/freeze_P/build.log, line 178) with --prefix as the install folder, plus what the
# image's call found or chose on its own, pinned: /usr/bin/gcc and /usr/bin/c++, the toolchain's default linker, ONNX
# Runtime and dotnet from /opt/onnxruntime and /usr/share/dotnet, and none of the optional packages the image did not
# have (Arrow Dataset and S3, a system opentims, Thermo bridge or HiGHS, Doxygen, anything in the install folder).
# CMake's configure output must then be the image's (image_configure.txt): compiler GNU 13.3.0, the linker, every
# package found and its version, the Thermo bridge's .NET host pack 8.0.34, ...; only the THIRDPARTY tests and download
# progress may differ. Then make all, make install/strip and the checks of the Dockerfile's last step. The build is
# generic: no -march=native may reach the compiler flags. GCC searches /usr/local/include before /usr/include (the image
# had nothing there): every header a source file used must come from the source and build trees or the folders the
# image's build used (/usr/include, /usr/lib/gcc, /opt/libxml2, /opt/onnxruntime, .NET's nethost; the compiler's
# dependency files are read after make all), so none from /usr/local, and no library of P may be loaded from
# /usr/local. Hence --work and --prefix may not be under /usr/local.
# At the end ProSE, FileConverter and EntrapmentEvaluator must find every library, load libOpenMS.so from
# <prefix>/lib, print version 3.7.0 and Revision: b2d252b, and have the image's RUNPATH; <prefix>/BUILD_P.txt records
# the build.
#
# Running P on Thermo .raw files needs the .NET 8 runtime: DOTNET_ROOT=/usr/share/dotnet (prepare_node.sh sets it).
#
# image_configure.txt was made from the image's log with this script:
#   awk '/^#18 [0-9.]+ \+ cmake / {on = 1; next} on && sub(/^#18 [0-9.]+ /, "") {print} on && /Build files have been written/ {exit}' \
#     checks/freeze_P/build.log | bash build_P.sh --normalize-configure /tmp/OpenMS/bld /tmp/OpenMS /opt/OpenMS
# and image_packages.txt from the log of the image's base stage (Docker step #8, base 2/7, the only step of that stage
# that installs packages; BuildKit prints its output in parts, between those of step #9):
#   awk '/^#8 [0-9.]+ Setting up /' conversion_test/build_openms.log \
#     | sed -E 's/^#8 [0-9.]+ Setting up ([^ ]+) \(([^)]+)\).*/\1 \2/; s/:amd64 / /' | sort -u
set -Eeuo pipefail

COMMIT=b2d252b4426f74a1d45b199e3d1f8bbcb9c87253
REVISION=b2d252b
TAG=prose-benchmark-2026-11-16
TAG_OBJECT=2c725c75f667fcbec279f2c89daf078fa61badbd
REPO_URL=https://github.com/OpenMS/OpenMS
CMAKE_VERSION=3.28.1
CMAKE_SHA256=ada6a46be9da5f8cbeb00b9523ffe45ee6b36172eb81aaa5bdc6a2a8231b677c   # Kitware's cmake-3.28.1-SHA-256.txt
LIBXML2_VERSION=2.15.4
LIBXML2_SHA256=98087fd181d9070724f3fbc65c7377db03038eb92bd882374daff44940138821  # the Dockerfile's LIBXML2_SHA256
ONNXRUNTIME_VERSION=1.30.0
ONNXRUNTIME_SHA256=a5ed5a3cac51fbb2e90da632ae43d19212faaa20e76484e62bcb7c23ddb3b3fd  # ONNXRUNTIME_SHA256_AMD64
ARROW_VERSION=24.0.0-1
ARROW_PACKAGES=(libparquet-dev libarrow-dev libparquet2400 libarrow2400)   # the Arrow packages of the image
DOTNET_SDK_VERSION=8.0.428
DOTNET_HOST_VERSION=8.0.34   # runtime and host pack of SDK 8.0.428, as in the image
DOTNET_DIR=/usr/share/dotnet
CMAKE=/opt/cmake/bin/cmake
GCC_VERSION=13.3.0
APT_PACKAGES=(g++ make git ca-certificates build-essential libsvm-dev libzip-dev zlib1g-dev libzstd-dev libzip4 zlib1g
  libicu74 libbz2-dev libcurl4-openssl-dev libomp-dev libhdf5-dev libeigen3-dev libboost-dev)
# what g++ resolves to on Ubuntu 24.04, named so that apt brings them up to date
GCC_PACKAGES=(gcc-13 g++-13 cpp-13 libstdc++-13-dev)
# not in the image: what the other tools of the benchmark need on the node (bench.py, /usr/bin/time, taskset,
# MSFragger's Java as on the preparation PC, the libraries of Percolator's .deb build)
BENCH_PACKAGES=(python3 time util-linux openjdk-21-jre-headless libboost-filesystem1.83.0)
MODELS=(peptdeep_ms2_dynamic.onnx peptdeep_rt_dynamic.onnx peptdeep_ccs_dynamic.onnx)
TOOLS=(ProSE FileConverter EntrapmentEvaluator)
HERE=$(dirname "$(realpath "${BASH_SOURCE[0]}")")
IMAGE_CONFIGURE=$HERE/image_configure.txt
IMAGE_PACKAGES=$HERE/image_packages.txt

usage() {
  echo "usage: build_P.sh --prefix <install folder> [--work <folder>] [--jobs <N>] [--skip-deps | --deps-only]"
  echo "                  [--accept-configure-diff]"
  echo "(the comment at the top of $0 says what it does)"
  exit "$1"
}
die() { echo "build_P.sh: FAILED: $*" >&2; exit 1; }
step() { echo; echo "=== $* ($(date -Is))"; }

re_escape() { printf '%s' "$1" | sed 's/[][\\.*^$#|+?(){}]/\\&/g'; }
# CMake's configure output, made comparable with the image's: the build tree, source and install folder as <BLD>,
# <SRC> and <PREFIX>, no times; left out: download progress, and what depends on THIRDPARTY (tests only). The image's
# linker lines (lld and mold tested, neither found) become the line of OPENMS_LINKER=default, the same choice. Its
# "Could NOT find Doxygen" is left out: the node's call does not look for Doxygen (CMAKE_DISABLE_FIND_PACKAGE_Doxygen),
# the same outcome ("Doxygen not found. Disabling all documentation targets!" stays in both).
normalize_configure() {  # normalize_configure <build tree> <source> <install folder>, stdin -> stdout
  local bld src prefix
  bld=$(re_escape "$1"); src=$(re_escape "$2"); prefix=$(re_escape "$3")
  sed -E -e 's/[[:space:]]+$//' -e "s#$bld#<BLD>#g; s#$src#<SRC>#g; s#$prefix#<PREFIX>#g" \
      -e 's/^-- (Configuring|Generating) done \([0-9.]+s\)$/-- \1 done (<t>)/' \
      -e 's/^-- Linker: toolchain default \(no lld\/mold found.*$/-- Linker: toolchain default (OPENMS_LINKER=default)/' \
    | { grep -Ev -e '^-- \[download [0-9]+% complete\]$' -e '^-- Performing Test OPENMS_LINKER_SUPPORTS_' \
          -e '^-- (Percolator_subprocess|PercolatorAdapter)_parity_test: ' \
          -e '^--   [-+] .*( binary found at .* -> Enabling corresponding tests\.| not found)$' \
          -e '^-- Could NOT find Doxygen \(missing: DOXYGEN_EXECUTABLE\)$' || true; }
}
if [ "${1:-}" = --normalize-configure ]; then
  [ $# -eq 4 ] || die "usage: build_P.sh --normalize-configure <build tree> <source> <install folder> < output"
  normalize_configure "$2" "$3" "$4"
  exit 0
fi

PREFIX="" WORK="$PWD/build_P_${COMMIT:0:10}" WORK_GIVEN=0 JOBS="" DEPS=install ACCEPT_DIFF=0
while [ $# -gt 0 ]; do
  case $1 in
    --prefix|--work|--jobs) [ $# -ge 2 ] || usage 1 ;;&
    --prefix) PREFIX=$2; shift 2 ;;
    --work) WORK=$2; WORK_GIVEN=1; shift 2 ;;
    --jobs) JOBS=$2; shift 2 ;;
    --skip-deps) DEPS=check; shift ;;
    --deps-only) DEPS=only; shift ;;
    --accept-configure-diff) ACCEPT_DIFF=1; shift ;;
    -h|--help) usage 0 ;;
    *) echo "build_P.sh: unknown argument $1" >&2; usage 1 ;;
  esac
done
[ "$DEPS" = only ] || [ -n "$PREFIX" ] || usage 1
if [ "$(id -u)" -eq 0 ] && [ -n "${SUDO_USER:-}" ]; then
  die "run build_P.sh as yourself, not with sudo: it calls sudo for the dependencies, and the build and install" \
    "folders must belong to you"
fi
if [ -z "$JOBS" ]; then  # one job per CPU, at most one per 2 GB of available memory (a C++ -O3 job can take that much)
  JOBS=$(nproc)
  mem_jobs=$(awk '/^MemAvailable:/ {print int($2 / 2097152)}' /proc/meminfo)
  [ "$mem_jobs" -ge "$JOBS" ] || JOBS=$mem_jobs
  [ "$JOBS" -ge 1 ] || JOBS=1
fi
[[ $JOBS =~ ^[1-9][0-9]*$ ]] || die "--jobs needs a positive number"
WORK=$(realpath -m "$WORK")
[ -z "$PREFIX" ] || PREFIX=$(realpath -m "$PREFIX")
WORK_IS=$([ $WORK_GIVEN = 1 ] && echo "--work '$WORK'" || echo "the default --work '$WORK' (./build_P_${COMMIT:0:10} in the current folder)")
if [ "$DEPS" != only ]; then   # the folders of the build (--deps-only writes only its log to --work)
  why="must not hold white space, '#', '\$' or '\\' (GCC escapes them in its dependency files; CMake refuses '#')"
  [[ $WORK != *[[:space:]\#\$\\]* ]] || die "$WORK_IS $why: give --work <folder> elsewhere"
  [[ $PREFIX != *[[:space:]\#\$\\]* ]] || die "--prefix '$PREFIX' $why: give --prefix <folder> elsewhere"
  # the build stops on any file from /usr/local (the checks after make all and in verify), so its own trees may not be there
  for d in "$WORK" "$PREFIX"; do
    case "$d/" in /usr/local/*|"$(realpath -m /usr/local)"/*) die "$d is under /usr/local: give --work and --prefix outside it" ;; esac
  done
fi
if [ -n "$PREFIX" ]; then
  case "$WORK/" in "$PREFIX/"*) die "--work $WORK is inside --prefix $PREFIX, which is emptied before each build" ;; esac
  case "$PREFIX/" in "$WORK/"*) die "--prefix $PREFIX is inside --work $WORK: give two separate folders" ;; esac
fi
HOST=$(hostname)
mkdir -p "$WORK" 2> /dev/null || die "cannot make $WORK_IS: its log goes there, also with --deps-only; give --work <a folder of yours>"
[ -w "$WORK" ] || die "cannot write to $WORK (made by another user, or by an earlier run with sudo?)"
if [ -f "$WORK/.build_P_host" ] && [ "$(cat "$WORK/.build_P_host")" != "$HOST" ]; then
  die "$WORK was used by build_P.sh on $(cat "$WORK/.build_P_host"): each node needs a --work of its own"
fi
echo "$HOST" > "$WORK/.build_P_host"
exec > >(tee -a "$WORK/build_P.log") 2>&1
trap 'echo "build_P.sh: FAILED at line $LINENO: $BASH_COMMAND" >&2' ERR
TMPD=$(mktemp -d /var/tmp/build_P.XXXXXX)   # downloads and the libxml2 build: local, readable by root (sudo)
chmod 755 "$TMPD"
trap 'rm -rf "$TMPD"' EXIT
echo "build_P.sh on $HOST, $(date -Is): P = OpenMS $COMMIT ($TAG); prefix ${PREFIX:-none}, work $WORK, jobs $JOBS, dependencies: $DEPS"

# The build runs in this environment only, like the image's in Docker: no compiler, flags, search paths, CMake or
# pkg-config settings, LD_LIBRARY_PATH or OPENMS_DATA_PATH of the user's shell. No /usr/local in the PATH: GCC takes
# ld and as from the PATH, and the image's /usr/local/bin held only links to cmake and dotnet.
CLEAN=(env -i HOME="$HOME" USER="${USER:-$(id -un)}"
  PATH="/opt/cmake/bin:$DOTNET_DIR:/usr/sbin:/usr/bin:/sbin:/bin"
  DOTNET_ROOT="$DOTNET_DIR" DOTNET_CLI_TELEMETRY_OPTOUT=1 DOTNET_NOLOGO=1)
for v in http_proxy https_proxy no_proxy HTTP_PROXY HTTPS_PROXY NO_PROXY SSL_CERT_FILE SSL_CERT_DIR GIT_SSL_CAINFO TMPDIR; do
  [ -z "${!v:-}" ] || CLEAN+=("$v=${!v}")
done

[ "$(uname -s)" = Linux ] && [ "$(uname -m)" = x86_64 ] || die "needs Linux on x86_64"
# shellcheck source=/dev/null
. /etc/os-release
if [ "${ID:-}" != ubuntu ] || [ "${VERSION_ID:-}" != 24.04 ]; then
  die "only Ubuntu 24.04 is supported (P must be built with the image's compiler and package versions), and this is" \
    "${PRETTY_NAME:-unknown}. On another system, the untimed checks can use P's native copy" \
    "(prepare_node.sh --native-only); how to build P there is open."
fi
[ -f "$IMAGE_CONFIGURE" ] && [ -f "$IMAGE_PACKAGES" ] || die "image_configure.txt or image_packages.txt is not next to $0"
if [ -n "$PREFIX" ]; then
  # .build_P marks an install folder of this script on this node; it is emptied before each build (see build)
  if [ -f "$PREFIX/.build_P" ]; then
    h=$(sed -n 's/^host //p' "$PREFIX/.build_P")
    [ -z "$h" ] || [ "$h" = "$HOST" ] || die "$PREFIX is the install folder of build_P.sh on $h: each node needs one of its own"
  elif [ -d "$PREFIX" ] && [ -n "$(ls -A "$PREFIX")" ]; then
    die "$PREFIX holds files that this script did not install (no .build_P): choose a new or empty folder"
  fi
  { mkdir -p "$PREFIX" && [ -w "$PREFIX" ]; } || die "cannot write to $PREFIX: choose a folder of yours"
  [ "$DEPS" = only ] || printf 'install folder of build_P.sh (emptied before each build)\nhost %s\n' "$HOST" > "$PREFIX/.build_P"
fi
free_gb=$(df -P -BG "$WORK" | awk 'NR==2 {sub("G", "", $4); print $4}')
[ "$free_gb" -ge 10 ] || echo "WARNING: only ${free_gb} GB free in $WORK; source and build tree take about 4 GB"
# the type in the mount table (nfs4, fuse.sshfs, beegfs, ...; stat -f names FUSE file systems all "fuseblk"); findmnt -T
# lists every mount stacked on the target, the one in effect last (an NFS share under an automount: autofs, then nfs4)
fs_type=$(findmnt -no FSTYPE -T "$WORK" 2>/dev/null | tail -n 1 || true)
case "${fs_type:=$(stat -f -c %T "$WORK")}" in
  nfs*|cifs|smb*|fuse|fuse.*|lustre|gpfs|beegfs|fhgfs|ceph|v9fs|9p|afs|orangefs|wekafs|panfs|davfs)
    echo "WARNING: $WORK is on a $fs_type file system: the build is much faster on a local disk" ;;
esac

if [ "$(id -u)" -eq 0 ]; then SUDO=(); else SUDO=(sudo); fi
as_root() { "${SUDO[@]}" env DEBIAN_FRONTEND=noninteractive "$@"; }
ARCH=$(dpkg --print-architecture)
version_of() {  # the version of an installed package (of this node's architecture, or "all"), else nothing; the
  # first letter of the status is the selection (i, or h for a package held with apt-mark hold), the second the state
  dpkg-query -W -f='${db:Status-Abbrev}|${Architecture}|${Version}\n' "$1" 2>/dev/null \
    | awk -F'|' -v a="$ARCH" '$1 ~ /^.i/ && ($2 == a || $2 == "all") {print $3; exit}' || true
}
need() {  # need <what>: stops with --skip-deps, else says what is installed
  [ "$DEPS" != check ] || die "$1 is missing; install it, or run without --skip-deps"
  step "installing $1"
}

apt_plan() {  # what apt would do for these packages, a simulation (it also resolves virtual packages like libzip4):
  # "new <pkg>...", "upgrade <pkg>..." and "remove <pkg>..." lines
  local sim
  sim=$(apt-get -s install --no-install-recommends --no-install-suggests "$@" 2>&1 || true)
  if grep -q '^E: ' <<<"$sim"; then echo "new $*"; return; fi
  echo "new $(awk '$1 == "Inst" && $3 !~ /^\[/ {print $2}' <<<"$sim" | tr '\n' ' ')"
  echo "upgrade $(awk '$1 == "Inst" && $3 ~ /^\[/ {print $2}' <<<"$sim" | tr '\n' ' ')"
  echo "remove $(awk '$1 == "Remv" {print $2}' <<<"$sim" | tr '\n' ' ')"
}
# apt-get install -y would remove, without asking, every package that conflicts with one to install: --no-remove
# makes apt stop instead
apt_install() { as_root apt-get install -y --no-remove "$@"; }
deps_apt() {
  local plan new upgrade remove v
  plan=$(apt_plan "${APT_PACKAGES[@]}" "${GCC_PACKAGES[@]}" "${BENCH_PACKAGES[@]}" wget xz-utils)
  new=$(sed -n 's/^new //p' <<<"$plan" | xargs); upgrade=$(sed -n 's/^upgrade //p' <<<"$plan" | xargs)
  remove=$(sed -n 's/^remove //p' <<<"$plan" | xargs)
  [ -z "$remove" ] || die "apt would have to remove $remove to install the packages of the base stage (a conflict" \
    "with a package of this node); this script removes nothing: resolve it first"
  if [ -z "$new" ] && [ -z "$upgrade" ]; then
    echo "apt packages of the base stage and of the other tools: there"
  elif [ "$DEPS" = check ] && [ -z "$new" ]; then
    echo "apt packages of the base stage and of the other tools: there (apt has newer versions of: $upgrade)"
  else
    need "the apt packages of the base stage and of the other tools (apt would install: ${new:-none}; upgrade: ${upgrade:-none})"
    as_root apt-get update
    apt_install software-properties-common
    as_root add-apt-repository -y universe
    as_root apt-get update
    apt_install --no-install-recommends --no-install-suggests "${APT_PACKAGES[@]}" "${GCC_PACKAGES[@]}" wget xz-utils \
      || die "apt-get could not install the packages of the base stage (it stops rather than remove a package)"
    as_root update-ca-certificates
    apt_install --no-install-recommends --no-install-suggests "${BENCH_PACKAGES[@]}" \
      || die "apt-get could not install ${BENCH_PACKAGES[*]} (it stops rather than remove a package)"
  fi
  for v in gcc-13 g++-13; do
    [[ $(version_of "$v") == "$GCC_VERSION"-* ]] || die "$v is '$(version_of "$v")', not GCC $GCC_VERSION as in the image"
  done
}

deps_arrow() {
  local p ok=1 others pin
  # Arrow and Parquet packages this node has: only the image's four at 24.0.0-1 may be there
  others=$(dpkg-query -W -f='${db:Status-Abbrev}|${Package}|${Version}\n' 'libarrow*' 'libparquet*' 2>/dev/null \
    | awk -F'|' -v v="$ARROW_VERSION" -v ok=" ${ARROW_PACKAGES[*]} " \
        '$1 ~ /^.i/ && !(index(ok, " " $2 " ") && $3 == v) {printf "%s %s; ", $2, $3}' || true)
  [ -z "$others" ] || die "Arrow/Parquet packages that are not the image's ($ARROW_VERSION of ${ARROW_PACKAGES[*]})" \
    "are installed: $others remove them first (OpenMS would build against them)"
  for p in "${ARROW_PACKAGES[@]}"; do
    [ "$(version_of "$p")" = "$ARROW_VERSION" ] || ok=0
  done
  if [ $ok = 1 ]; then echo "Arrow and Parquet $ARROW_VERSION: there"; return; fi
  pin=$'Package: libarrow* libparquet*\nPin: version 24.*\nPin-Priority: 999'
  if [ -e /etc/apt/preferences.d/arrow ] && [ "$(cat /etc/apt/preferences.d/arrow)" != "$pin" ]; then
    die "/etc/apt/preferences.d/arrow holds another pin than the image's (Pin: version 24.*); it is not changed"
  fi
  need "Arrow and Parquet $ARROW_VERSION (Apache's apt repository, pinned to 24.* as in the image)"
  # The two files of Apache's repository are not pinned: Apache changes both in place, and the image took the current
  # ones too. Their SHA256 go into the log; apt then checks the Arrow packages against the keyring.
  local deb=$TMPD/apache-arrow-apt-source-latest-noble.deb
  wget -q -O "$deb" https://packages.apache.org/artifactory/arrow/ubuntu/apache-arrow-apt-source-latest-noble.deb
  echo "apache-arrow-apt-source-latest-noble.deb: SHA256 $(sha256sum "$deb" | cut -d' ' -f1)," \
    "$(dpkg-deb -f "$deb" Package Version | tr '\n' ' ')(not pinned: Apache updates it in place)"
  apt_install --no-install-recommends "$deb"
  # as in the image: the current KEYS appended to the keyring the .deb names (OpenMS issue #9729)
  wget -q -O "$TMPD/arrow_KEYS" https://downloads.apache.org/arrow/KEYS
  echo "Apache Arrow KEYS: SHA256 $(sha256sum "$TMPD/arrow_KEYS" | cut -d' ' -f1) (not pinned: Apache adds keys to it)"
  as_root tee -a /usr/share/keyrings/apache-arrow-apt-source.asc < "$TMPD/arrow_KEYS" > /dev/null
  [ -e /etc/apt/preferences.d/arrow ] || printf '%s\n' "$pin" | as_root tee /etc/apt/preferences.d/arrow > /dev/null
  as_root apt-get update
  apt_install --no-install-recommends --no-install-suggests "libparquet-dev=$ARROW_VERSION" \
    "libarrow-dev=$ARROW_VERSION" "libparquet2400=$ARROW_VERSION" "libarrow2400=$ARROW_VERSION" \
    || die "Arrow/Parquet $ARROW_VERSION could not be installed (no longer in Apache's repository, or apt would" \
      "have to remove a package?)"
  echo "left in apt's configuration: the package apache-arrow-apt-source (Apache's repository)," \
    "/usr/share/keyrings/apache-arrow-apt-source.asc and the pin /etc/apt/preferences.d/arrow"
}

deps_cmake() {
  if [ -x "$CMAKE" ] && "$CMAKE" --version | grep -q "^cmake version $CMAKE_VERSION\$"; then
    echo "CMake $CMAKE_VERSION in /opt/cmake: there"; return
  fi
  [ ! -e /opt/cmake ] || die "/opt/cmake holds another CMake than $CMAKE_VERSION; move it away first"
  need "CMake $CMAKE_VERSION into /opt/cmake"
  local f=$TMPD/cmake-$CMAKE_VERSION-linux-x86_64.sh
  wget -q -O "$f" "https://github.com/Kitware/CMake/releases/download/v$CMAKE_VERSION/cmake-$CMAKE_VERSION-linux-x86_64.sh"
  echo "$CMAKE_SHA256  $f" | sha256sum -c -
  as_root mkdir -p /opt/cmake
  as_root sh "$f" --skip-license --prefix=/opt/cmake
}

libxml2_version() { sed -n 's/^#define LIBXML_DOTTED_VERSION "\(.*\)"/\1/p' /opt/libxml2/include/libxml2/libxml/xmlversion.h 2>/dev/null || true; }
deps_libxml2() {
  if [ "$(libxml2_version)" = "$LIBXML2_VERSION" ] && [ -e /opt/libxml2/lib/libxml2.so ]; then
    echo "libxml2 $LIBXML2_VERSION in /opt/libxml2: there"; return
  fi
  [ ! -e /opt/libxml2 ] || die "/opt/libxml2 holds another libxml2 than $LIBXML2_VERSION ($(libxml2_version)); move it away first"
  need "libxml2 $LIBXML2_VERSION into /opt/libxml2 (built from source, as in the base stage)"
  local t=$TMPD/libxml2-$LIBXML2_VERSION.tar.xz s=$TMPD/libxml2-src b=$TMPD/libxml2-build
  wget -q -O "$t" "https://download.gnome.org/sources/libxml2/2.15/libxml2-$LIBXML2_VERSION.tar.xz"
  echo "$LIBXML2_SHA256  $t" | sha256sum -c -
  mkdir -p "$s"
  tar xf "$t" --strip-components=1 -C "$s"
  "${CLEAN[@]}" "$CMAKE" -S "$s" -B "$b" -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_INSTALL_PREFIX=/opt/libxml2 -DBUILD_SHARED_LIBS=ON \
    -DLIBXML2_WITH_PYTHON=OFF -DLIBXML2_WITH_PROGRAMS=OFF -DLIBXML2_WITH_TESTS=OFF \
    -DLIBXML2_WITH_LEGACY=OFF -DLIBXML2_WITH_ZLIB=ON \
    -DLIBXML2_WITH_SAX1=ON -DLIBXML2_WITH_PUSH=ON -DLIBXML2_WITH_SCHEMAS=ON \
    -DLIBXML2_WITH_THREADS=ON -DLIBXML2_WITH_ICONV=ON
  "${CLEAN[@]}" "$CMAKE" --build "$b" --parallel 8
  as_root "$CMAKE" --install "$b"
  as_root mkdir -p /opt/libxml2/share/licenses/libxml2
  as_root cp "$s/Copyright" /opt/libxml2/share/licenses/libxml2/
}

deps_onnxruntime() {
  if [ "$(cat /opt/onnxruntime/VERSION_NUMBER 2>/dev/null)" = "$ONNXRUNTIME_VERSION" ] \
     && [ -f /opt/onnxruntime/include/onnxruntime_cxx_api.h ] && [ -e /opt/onnxruntime/lib/libonnxruntime.so ]; then
    echo "ONNX Runtime $ONNXRUNTIME_VERSION in /opt/onnxruntime: there"; return
  fi
  [ ! -e /opt/onnxruntime ] || die "/opt/onnxruntime holds another ONNX Runtime than $ONNXRUNTIME_VERSION; move it away first"
  need "ONNX Runtime $ONNXRUNTIME_VERSION into /opt/onnxruntime"
  local t=$TMPD/onnxruntime-linux-x64-$ONNXRUNTIME_VERSION.tgz
  wget -q -O "$t" "https://github.com/microsoft/onnxruntime/releases/download/v$ONNXRUNTIME_VERSION/onnxruntime-linux-x64-$ONNXRUNTIME_VERSION.tgz"
  echo "$ONNXRUNTIME_SHA256  $t" | sha256sum -c -
  as_root mkdir -p /opt/onnxruntime
  as_root tar xzf "$t" --no-same-owner --strip-components=1 -C /opt/onnxruntime
  test -f /opt/onnxruntime/include/onnxruntime_cxx_api.h
  test -e /opt/onnxruntime/lib/libonnxruntime.so
}

dotnet_sdks() { "$DOTNET_DIR/dotnet" --list-sdks 2>/dev/null || true; }
dotnet_others() {  # SDKs, runtimes and host packs in DOTNET_DIR besides those of SDK 8.0.428
  { dotnet_sdks | awk -v v="$DOTNET_SDK_VERSION" '$1 != v {print "SDK " $1}'
    "$DOTNET_DIR/dotnet" --list-runtimes 2>/dev/null | awk -v v="$DOTNET_HOST_VERSION" '$2 != v {print $1 " " $2}' || true
    find "$DOTNET_DIR/packs/Microsoft.NETCore.App.Host.linux-x64" -mindepth 1 -maxdepth 1 ! -name "$DOTNET_HOST_VERSION" \
      -printf 'host pack %f\n' 2>/dev/null || true; } | tr '\n' ';'
}
deps_dotnet() {
  if [ -x "$DOTNET_DIR/dotnet" ] && grep -q "^$DOTNET_SDK_VERSION " <<<"$(dotnet_sdks)"; then
    echo ".NET SDK $DOTNET_SDK_VERSION in $DOTNET_DIR: there"
  else
    need ".NET SDK $DOTNET_SDK_VERSION into $DOTNET_DIR (dotnet-install.sh)"
    local f=$TMPD/dotnet-install.sh
    wget -q -O "$f" https://dot.net/v1/dotnet-install.sh
    echo "dotnet-install.sh: SHA256 $(sha256sum "$f" | cut -d' ' -f1) (not pinned: Microsoft updates it in place)"
    as_root bash "$f" --version "$DOTNET_SDK_VERSION" --install-dir "$DOTNET_DIR"
  fi
  [ -d "$DOTNET_DIR/packs/Microsoft.NETCore.App.Host.linux-x64/$DOTNET_HOST_VERSION" ] \
    || die "$DOTNET_DIR has no host pack $DOTNET_HOST_VERSION (the image's; SDK $DOTNET_SDK_VERSION brings it)"
  local others; others=$(dotnet_others)
  [ -z "$others" ] || echo "WARNING: $DOTNET_DIR also holds $others the Thermo bridge must link host pack" \
    "$DOTNET_HOST_VERSION (checked after CMake), and at run time .NET rolls forward to the newest 8.0 runtime there"
}

local_headers() {  # headers in /usr/local/include that GCC would take before Ubuntu's (the image had none)
  local f
  for f in boost eigen3 Eigen arrow parquet libxml2 libxml nlohmann zlib.h zip.h zstd.h bzlib.h svm.h curl omp.h H5Cpp.h hdf5.h; do
    [ ! -e "/usr/local/include/$f" ] || printf '%s ' "/usr/local/include/$f"
  done
}

deps() {
  step "dependencies of the Dockerfile's base stage"
  deps_apt
  deps_arrow
  deps_cmake
  deps_libxml2
  deps_onnxruntime
  deps_dotnet
  local h; h=$(local_headers)
  [ -z "$h" ] || echo "WARNING: headers in /usr/local/include come before Ubuntu's in GCC's search: $h(the image had" \
    "none). If the build uses any header from /usr/local, it stops after make all."
}

source_tree() {
  local src=$WORK/OpenMS
  step "OpenMS source: tag $TAG"
  if [ ! -d "$src/.git" ]; then
    "${CLEAN[@]}" git clone --branch "$TAG" --depth 1 "$REPO_URL" "$src"
  fi
  git -C "$src" rev-parse -q --verify "refs/tags/$TAG" > /dev/null \
    || "${CLEAN[@]}" git -C "$src" fetch --depth 1 origin "refs/tags/$TAG:refs/tags/$TAG"
  [ "$(git -C "$src" rev-parse HEAD)" = "$COMMIT" ] || die "$src is at $(git -C "$src" rev-parse HEAD), not at $COMMIT"
  [ "$(git -C "$src" rev-parse "refs/tags/$TAG")" = "$TAG_OBJECT" ] \
    || die "the tag $TAG is $(git -C "$src" rev-parse "refs/tags/$TAG"), not the tag object $TAG_OBJECT"
  [ -z "$(git -C "$src" status --porcelain --untracked-files=no)" ] || die "$src has changed files"
  echo "OpenMS $(git -C "$src" log -1 --format='%H %cI %s')"
}

build() {
  local src=$WORK/OpenMS bld=$WORK/OpenMS/bld v
  # the SDK of the image for the Thermo bridge's `dotnet publish`, also if the node has others
  printf '{ "sdk": { "version": "%s", "rollForward": "disable" } }\n' "$DOTNET_SDK_VERSION" > "$WORK/global.json"
  # Like the image, every build starts with an empty install folder and a new build tree: CMake searches the install
  # prefix, and would otherwise link libraries of an earlier install (e.g. libopenms_thermo_bridge.so) and write
  # <prefix>/lib into the RUNPATH. This also removes the BUILD_P.txt of an earlier build.
  if [ -n "$(find "$PREFIX" -mindepth 1 -maxdepth 1 ! -name .build_P -print -quit)" ] || [ -e "$bld" ]; then
    step "removing the earlier install in $PREFIX and the build tree $bld"
    find "$PREFIX" -mindepth 1 -maxdepth 1 ! -name .build_P -exec rm -rf {} +
    rm -rf "$bld"
  fi
  step "CMake: the call of the Dockerfile's build stage, install folder $PREFIX (output: $WORK/configure.log)"
  # The Dockerfile's call (its first nine arguments), then what that call found or chose in the image, pinned
  CMAKE_ARGS=(
    -DOPENMS_USE_VCPKG=OFF
    -DCMAKE_BUILD_TYPE='Release'
    -DCMAKE_PREFIX_PATH="/opt/libxml2;/usr/;/usr/local;/opt/onnxruntime"
    -DLIBXML2_INCLUDE_DIR=/opt/libxml2/include/libxml2
    -DLIBXML2_LIBRARY=/opt/libxml2/lib/libxml2.so
    -DWITH_ONNX=ON
    -DCMAKE_INSTALL_PREFIX="$PREFIX"
    -S "$src"
    -B "$bld"
    -G "Unix Makefiles"
    -DCMAKE_C_COMPILER=/usr/bin/gcc
    -DCMAKE_CXX_COMPILER=/usr/bin/c++
    -DOPENMS_LINKER=default
    -DONNXRuntime_LIBRARY=/opt/onnxruntime/lib/libonnxruntime.so
    -DONNXRuntime_INCLUDE_DIR=/opt/onnxruntime/include
    -DDOTNET_EXECUTABLE="$DOTNET_DIR/dotnet"
    -DCMAKE_FIND_NO_INSTALL_PREFIX=ON
    -DCMAKE_DISABLE_FIND_PACKAGE_ArrowDataset=ON
    -DCMAKE_DISABLE_FIND_PACKAGE_ArrowS3=ON
    -DCMAKE_DISABLE_FIND_PACKAGE_Opentims=ON
    -DCMAKE_DISABLE_FIND_PACKAGE_OpenMSThermoBridge=ON
    -DCMAKE_DISABLE_FIND_PACKAGE_highs=ON
    -DCMAKE_DISABLE_FIND_PACKAGE_Doxygen=ON
  )
  # the assembler and linker GCC runs (it takes them from the PATH): Ubuntu's binutils, as in the image
  for v in ld as; do
    [ "$("${CLEAN[@]}" sh -c "command -v $v")" = "/usr/bin/$v" ] \
      || die "in the clean environment, $v is $("${CLEAN[@]}" sh -c "command -v $v" || echo missing), not /usr/bin/$v (binutils)"
  done
  echo "$CMAKE ${CMAKE_ARGS[*]}"
  "${CLEAN[@]}" "$CMAKE" "${CMAKE_ARGS[@]}" 2>&1 | tee "$WORK/configure.log"
  for v in WITH_ONNX WITH_THERMO_RAW WITH_OPENTIMS; do
    grep -Eq "^$v:BOOL=(ON|TRUE|1)\$" "$bld/CMakeCache.txt" || die "$v is not ON in $bld/CMakeCache.txt"
  done
  for v in "CMAKE_C_COMPILER=/usr/bin/gcc" "CMAKE_CXX_COMPILER=/usr/bin/c++" "DOTNET_EXECUTABLE=$DOTNET_DIR/dotnet" \
           "ONNXRuntime_LIBRARY=/opt/onnxruntime/lib/libonnxruntime.so" "ONNXRuntime_INCLUDE_DIR=/opt/onnxruntime/include" \
           "OPENMS_LINKER=default"; do
    # the cache line is <name>:<type>=<value>
    grep -Eq "^${v%%=*}:[A-Z]+=$(re_escape "${v#*=}")\$" "$bld/CMakeCache.txt" \
      || die "$bld/CMakeCache.txt does not have ${v%%=*} = ${v#*=}"
  done
  if grep -rqs --include=flags.make -- "-march=native" "$bld" \
     || grep -Eq -- '^CMAKE_[A-Z_]*FLAGS[A-Z_]*:STRING=.*-march=native' "$bld/CMakeCache.txt"; then
    die "-march=native in the compiler flags ($bld)"
  fi
  normalize_configure "$bld" "$src" "$PREFIX" < "$WORK/configure.log" > "$WORK/configure.normalized"
  if diff -u "$IMAGE_CONFIGURE" "$WORK/configure.normalized" > "$WORK/configure.diff"; then
    echo "configure output: as in the image (image_configure.txt)"
  else
    echo "configure output differs from the image's ('-' image, '+' here; $WORK/configure.diff):"
    sed -n '3,$p' "$WORK/configure.diff"
    [ "$ACCEPT_DIFF" = 1 ] || die "CMake's configure output differs from the image's (above, $WORK/configure.diff):" \
      "this build would not be the image's. Make the node match it, or, only if every difference is harmless," \
      "run again with --accept-configure-diff (the differences then go into BUILD_P.txt)"
    echo "WARNING: --accept-configure-diff: building with these differences"
  fi
  step "make all ($JOBS jobs)"
  "${CLEAN[@]}" MAKEFLAGS="-j$JOBS" make -C "$bld" all
  # every file a source file read, from the compiler's dependency files (<object>.o.d): only from the source and build
  # trees and the folders the image's build read (Ubuntu's /usr/include, GCC's own headers, /opt/libxml2,
  # /opt/onnxruntime, the nethost headers of .NET). So none from /usr/local, which GCC searches before /usr/include, and
  # none through a link from there to another folder either (GCC writes the shorter real path of a system header).
  local n_dep used roots=() r
  n_dep=$(find "$bld" -name '*.o.d' | wc -l)
  [ "$n_dep" -ge 1000 ] || die "only $n_dep dependency files (*.o.d) in $bld: the headers used cannot be checked"
  for r in "$WORK" /usr/include /usr/lib/gcc /opt/libxml2 /opt/onnxruntime "$DOTNET_DIR"; do roots+=("$r/" "$(realpath -m "$r")/"); done
  used=$(find "$bld" -name '*.o.d' -exec cat {} + | tr -s '[:space:]\\' '\n' | sed -n 's/:$//; /^\//p' | sort -u \
    | ROOTS=$(printf '%s\n' "${roots[@]}") awk 'BEGIN {n = split(ENVIRON["ROOTS"], r, "\n")}
        {for (i = 1; i <= n; i++) if (r[i] != "" && index($0, r[i]) == 1) next; print}' | head -20 || true)
  [ -z "$used" ] || die "the build read files from outside its source and build trees and the image's folders" \
    "(/usr/include, /usr/lib/gcc, /opt/libxml2, /opt/onnxruntime, $DOTNET_DIR)$(grep -q '^/usr/local/' <<<"$used" \
    && echo ', from /usr/local among them, which GCC searches before /usr/include'): $(tr '\n' ' ' <<<"$used")"
  echo "headers: all from the source and build trees, /usr/include, /usr/lib/gcc, /opt/libxml2, /opt/onnxruntime and" \
    "$DOTNET_DIR; none from /usr/local ($n_dep dependency files of the compiler)"
  step "make install/strip"
  "${CLEAN[@]}" MAKEFLAGS="-j$JOBS" make -C "$bld" install/strip
}

finish() {
  step "the last step of the Dockerfile's build stage: licences, PeptDeep models, ONNX Runtime from $PREFIX/lib"
  mkdir -p "$PREFIX/share/OpenMS/LICENSES/onnxruntime"
  cp /opt/onnxruntime/LICENSE /opt/onnxruntime/ThirdPartyNotices.txt /opt/onnxruntime/VERSION_NUMBER \
    "$PREFIX/share/OpenMS/LICENSES/onnxruntime/"
  local m
  for m in "${MODELS[@]}"; do
    [ -s "$PREFIX/share/OpenMS/models/$m" ] || die "PeptDeep model $m is not in $PREFIX/share/OpenMS/models"
  done
  mkdir -p "$PREFIX/share/OpenMS/LICENSES/peptdeep_models"
  printf '%s\n' \
    "share/OpenMS/models/peptdeep_*_dynamic.onnx are ONNX exports of the pretrained" \
    "AlphaPeptDeep models (https://github.com/MannLabs/alphapeptdeep)," \
    "Copyright (c) Mann Labs, licensed under the Apache License 2.0" \
    "(https://www.apache.org/licenses/LICENSE-2.0)." \
    > "$PREFIX/share/OpenMS/LICENSES/peptdeep_models/NOTICE.txt"
  local out; out=$("${CLEAN[@]}" ldd "$PREFIX/lib/libOpenMS.so")
  grep onnxruntime <<<"$out" || true
  grep -qF "libonnxruntime.so.1 => $PREFIX/lib/" <<<"$out" || die "libOpenMS does not load ONNX Runtime from $PREFIX/lib"
  cmp -s "$PREFIX/lib/libonnxruntime.so.1" "/opt/onnxruntime/lib/libonnxruntime.so.$ONNXRUNTIME_VERSION" \
    || die "$PREFIX/lib/libonnxruntime.so.1 is not ONNX Runtime $ONNXRUNTIME_VERSION of /opt/onnxruntime"
}

verify() {
  step "checks of the installed P"
  local t out lib v re="Revision: $REVISION([^0-9a-f]|\$)"
  for t in "${TOOLS[@]}"; do
    [ -x "$PREFIX/bin/$t" ] || die "$PREFIX/bin/$t is missing"
    out=$("${CLEAN[@]}" ldd "$PREFIX/bin/$t")
    if grep -q "not found" <<<"$out"; then die "$t: libraries not found: $(grep 'not found' <<<"$out" | tr -s ' \t\n' ' ')"; fi
    if grep -q "=> /usr/local/" <<<"$out"; then
      die "$t loads libraries from /usr/local, unlike the image: $(grep '=> /usr/local/' <<<"$out" | tr -s ' \t\n' ' ')"
    fi
    lib=$(awk '$1 == "libOpenMS.so" {print $3}' <<<"$out")
    [ -n "$lib" ] && [ "$(realpath "$lib")" = "$(realpath "$PREFIX/lib/libOpenMS.so")" ] \
      || die "$t loads libOpenMS.so from ${lib:-nowhere}, not from $PREFIX/lib"
    out=$("${CLEAN[@]}" "$PREFIX/bin/$t" --help < /dev/null 2>&1 || true)
    v=$(grep -m1 '^Version:' <<<"$out" || true)
    [[ $v == "Version: 3.7.0"* && $v =~ $re ]] || die "$t prints '${v:-no version line}', not version 3.7.0 with Revision: $REVISION"
    echo "$t: $v"
  done
  [ -d "$PREFIX/lib/openms_thermo_bridge" ] || die "no Thermo bridge in $PREFIX/lib (WITH_THERMO_RAW)"
  # the RUNPATH of the image's binaries and libraries (its /opt/OpenMS)
  local f want got
  while read -r f want; do
    got=$(readelf -d "$PREFIX/$f" | sed -n 's/.*Library runpath: \[\(.*\)\]/\1/p')
    [ "$got" = "$want" ] || die "$f has the RUNPATH '$got', the image's has '$want'"
  done <<'EOF'
bin/ProSE $ORIGIN/../lib/:/opt/libxml2/lib:/opt/onnxruntime/lib
bin/FileConverter $ORIGIN/../lib/:/opt/libxml2/lib:/opt/onnxruntime/lib
bin/EntrapmentEvaluator $ORIGIN/../lib/:/opt/libxml2/lib:/opt/onnxruntime/lib
lib/libOpenMS.so $ORIGIN/../lib/:/opt/onnxruntime/lib:/opt/libxml2/lib
lib/libOpenMS_CLI.so $ORIGIN/../lib/:/opt/libxml2/lib:/opt/onnxruntime/lib
lib/libOpenSwathAlgo.so $ORIGIN/../lib/
lib/libopenms_thermo_bridge.so $ORIGIN/../lib/
EOF
  echo "RUNPATH of the three tools and the four libraries: as in the image"
}

package_diff() {  # the packages of the image's base stage whose version here is another
  local p want got
  while read -r p want; do
    got=$(version_of "$p")
    [ "$got" = "$want" ] || echo "$p: image $want, here ${got:-not installed}"
  done < "$IMAGE_PACKAGES"
}

record() {
  local bld=$WORK/OpenMS/bld t d n
  d=$(package_diff)
  n=$(grep -c . <<<"$d" || true)
  {
    echo "P = OpenMS $COMMIT (tag $TAG, tag object $TAG_OBJECT), built by build_P.sh on $HOST, $(date -Is)"
    echo "prefix $PREFIX; work $WORK; jobs $JOBS"
    echo "CMake call: $CMAKE ${CMAKE_ARGS[*]}"
    echo "OS: ${PRETTY_NAME:-unknown}; kernel $(uname -r); $(ldd --version 2>&1 | sed -n 1p)"
    echo "compiler (CMake's): $(sed -n 's/^set(CMAKE_CXX_COMPILER_ID "\(.*\)")/\1/p' "$bld"/CMakeFiles/"$CMAKE_VERSION"/CMakeCXXCompiler.cmake)" \
      "$(sed -n 's/^set(CMAKE_CXX_COMPILER_VERSION "\(.*\)")/\1/p' "$bld"/CMakeFiles/"$CMAKE_VERSION"/CMakeCXXCompiler.cmake)" \
      "$(grep '^CMAKE_CXX_COMPILER:' "$bld/CMakeCache.txt"); g++-13 $(version_of g++-13); $("$CMAKE" --version | sed -n 1p)"
    if [ -s "$WORK/configure.diff" ]; then
      echo "configure output: DIFFERS from the image's (--accept-configure-diff):"; sed -n '3,$p' "$WORK/configure.diff" | sed 's/^/  /'
    else
      echo "configure output: as in the image (image_configure.txt)"
    fi
    echo "libxml2 $(libxml2_version) (/opt/libxml2); ONNX Runtime $(cat /opt/onnxruntime/VERSION_NUMBER) (/opt/onnxruntime)"
    echo "Arrow/Parquet: libparquet-dev $(version_of libparquet-dev), libarrow-dev $(version_of libarrow-dev);" \
      "apt source apache-arrow-apt-source $(version_of apache-arrow-apt-source), keyring" \
      "/usr/share/keyrings/apache-arrow-apt-source.asc $(sha256sum /usr/share/keyrings/apache-arrow-apt-source.asc 2>/dev/null | awk '{print "SHA256", $1}' || echo "not there")"
    echo ".NET in $DOTNET_DIR:"; dotnet_sdks; "$DOTNET_DIR/dotnet" --list-runtimes 2>/dev/null || true
    echo "packages of the image's base stage (image_packages.txt) with another version here: $n"
    [ -z "$d" ] || sed 's/^/  /' <<<"$d"
    echo "/usr/local/include: $(ls /usr/local/include 2>/dev/null | tr '\n' ' ')(no header from there was used)"
    echo "/usr/local/lib: $(ls /usr/local/lib 2>/dev/null | tr '\n' ' ')(no library of P is loaded from there)"
    echo "/usr/local/bin: $(ls /usr/local/bin 2>/dev/null | tr '\n' ' ')(not in the PATH of the build)"
    echo "CMakeCache.txt:"
    grep -E '^(CMAKE_BUILD_TYPE|CMAKE_C_COMPILER|CMAKE_CXX_COMPILER|CMAKE_CXX_FLAGS|CMAKE_CXX_FLAGS_RELEASE|CMAKE_C_FLAGS_RELEASE|OPENMS_USE_VCPKG|OPENMS_LINKER|DOTNET_EXECUTABLE|ONNXRuntime_LIBRARY|WITH_[A-Z_]+):' \
      "$bld/CMakeCache.txt" | sed 's/^/  /'
    for t in "${TOOLS[@]}"; do
      echo "$t: $("${CLEAN[@]}" "$PREFIX/bin/$t" --help < /dev/null 2>&1 | grep -m1 '^Version:' || true)"
    done
  } > "$PREFIX/BUILD_P.txt"
  cat "$PREFIX/BUILD_P.txt"
  [ "$n" = 0 ] || echo "WARNING: $n packages of the image's base stage have another version here (BUILD_P.txt)"
}

deps
if [ "$DEPS" = only ]; then step "dependencies done"; exit 0; fi
source_tree
build
finish
verify
record
step "done: P is in $PREFIX. Next: prepare_node.sh ... --openms-bin $PREFIX/bin"
