# Setting up a benchmark node

Two scripts set up a node of the benchmark after the copy from the preparation PC (DATASETS.md section 5, run order
item 2: tasks 2, 3, 4 and 7). Run both on the node itself, as the user who runs the benchmark (not with `sudo`), in a
login shell:

```bash
cd <copy>/prose-paper/benchmarks/node
bash build_P.sh --prefix <copy>/openms-P --work <copy>/build_P_eaf9175bc7   # P, built on the node (calls sudo for the dependencies)
bash prepare_node.sh --copy <copy> --mem-gb <N> --role engine --openms-bin <copy>/openms-P/bin
source <copy>/node_env.sh                                          # then: $B, the driver with the main work folder
```

`<copy>` is the copied folder on the node's local disk. It holds:
- `prose-paper/`, a fresh `git clone` that has this folder;
- `work/` (`mzml/`, `mzml.sha256`, `db/`). Of the mzML of 2026-11-16, only the five of PXD065289 were converted
  again (2026-11-26, DATASETS.md section 4.0): a node that holds the older copy needs only these five (the step
  `copy` checks all 92 against `datasets/mzml.sha256`);
- `smoke_work/` and `tools/`;
- the two vendor files of `W_node`, in `work/vendor/` or `W_node/vendor/`.

`N` is the memory cap of the node (`bench.py --mem-gb`, DATASETS.md section 4.3), at least 7. The benchmark uses
N = 200 on both nodes (decided 2026-11-23, DATASETS.md section 5). Use `--role scaling` on the scaling node. Each node
builds P into a folder of its own, on its own disk: the prefix and `--work` must not be shared between nodes. A
`--work` that holds the source of another commit stops `build_P.sh` (give a new one); the prefix of an earlier build
of this script is emptied and used again, so a build of P replaces the node build of `b2d252b442`.

## `build_P.sh`: P on the node

P is OpenMS develop `eaf9175bc7`, tag `prose-benchmark-2026-11-26`, version 3.7.0 (DATASETS.md section 4.1; until
2026-11-26 P was `b2d252b442`, tag `prose-benchmark-2026-11-16`). The
timed runs use P built on the node, so that `/usr/bin/time` and `taskset` measure ProSE on the node's own libraries.
`build_P.sh` builds it the way OpenMS's `dockerfiles/Dockerfile` builds the image of P (its stages `base` and
`build`), on Ubuntu 24.04 (x86_64) only.

- **Dependencies** (installed with `sudo`), as in the image:
  - the `base` stage's apt packages (with `curl`, which OpenMS's `tools/ci/fetch_thermo_assets.sh` uses; no
    `libhdf5-dev` since OpenMS #10937), at Ubuntu 24.04's current versions. GCC must be 13.3.0 as in the image. Every
    package that apt set up in the image's `base` stage whose version here differs from the image's
    (`image_packages.txt`, 264 packages) is listed in `BUILD_P.txt`. apt removes nothing (`--no-remove`): if a
    package of the node conflicts with one of the image's, the script stops;
  - Arrow and Parquet 24.0.0-1 from Apache's apt repository, pinned to `24.*` as in the image. Other Arrow packages
    stop the script;
  - CMake 3.28.1 in `/opt/cmake`;
  - libxml2 2.15.4, built into `/opt/libxml2`;
  - ONNX Runtime 1.30.0 in `/opt/onnxruntime`, from Microsoft's release or, failing that, PhotoPrism's mirror of the
    same file, as in the Dockerfile (OpenMS #10951; github.com has answered 404 for it since 2026-11-18);
  - the .NET SDK 8.0.428 (host pack and runtime 8.0.34) in `/usr/share/dotnet`;
  - for the other tools of the benchmark: python3, `time`, `taskset`, OpenJDK 21 and `libboost-filesystem1.83.0`
    (Percolator's `.deb` build).

  The downloads of CMake, libxml2 and ONNX Runtime are checked by their SHA256 (in the build, the Thermo bridge's
  managed zip by OpenMS's `fetch_thermo_assets.sh` and the PeptDeep models by OpenMS's CMake). Three files are not,
  because their makers change them in place (the image took the same files): Microsoft's `dotnet-install.sh`, and Apache's
  `apache-arrow-apt-source-latest-noble.deb` and `KEYS`. Their SHA256 go into `build_P.log`, and `BUILD_P.txt`
  records the Arrow apt source and keyring that are installed; apt checks the Arrow packages against that keyring. A
  folder in `/opt` with another version stops the script. `--skip-deps` installs nothing (and checks that everything
  is there). `--deps-only` stops after the dependencies (its log goes to `--work` too, by default
  `./build_P_eaf9175bc7`: run it from a folder of yours, or give `--work`).
- **Build:**
  - The source is the tag (commit and tag object checked).
  - As in the Dockerfile's configure step (OpenMS #10928), the managed half of the Thermo bridge comes from the zip of
    the bridge's release v1.0.0 (`tools/ci/fetch_thermo_assets.sh --managed-only linux-x64`, SHA-256 pinned there),
    into `<work>/OpenMS/bld/thermo-managed`, and CMake gets it as `OPENMS_THERMO_BRIDGE_PREBUILT_MANAGED_DIR`: no
    `dotnet publish` and no NuGet download. Unlike the Dockerfile, there is no fallback to `dotnet publish`, as that
    build would not be the image's.
  - It is configured with the `build` stage's CMake call, with `--prefix` as the install folder. The script runs it in
    a clean environment: no compiler, flags, search paths or `LD_LIBRARY_PATH` of your shell, and no `/usr/local` in
    the `PATH` (GCC takes `ld` and `as` from there; they must be Ubuntu's `/usr/bin/ld` and `/usr/bin/as`).
  - What the image's call found or chose on its own is pinned:
    - `/usr/bin/gcc` and `/usr/bin/c++`;
    - the toolchain's default linker (`OPENMS_LINKER=default`, not lld or mold);
    - ONNX Runtime and `dotnet` from `/opt/onnxruntime` and `/usr/share/dotnet`;
    - none of the optional packages the image did not have (Arrow Dataset and S3, a system opentims, Thermo bridge or
      HiGHS, Doxygen, an earlier install).
  - **CMake's configure output must then be the image's** (`image_configure.txt`, from
    `checks/freeze_eaf9175bc7/build.log`):
    - compiler GNU 13.3.0, the linker, every package found and its version;
    - the Arrow and Parquet targets, the Thermo bridge's .NET host pack 8.0.34, ONNX Runtime;
    - only download progress and the THIRDPARTY tests may differ, and the image's line "Could NOT find Doxygen" is
      left out (the node's call does not look for Doxygen; both then print "Doxygen not found").

    If anything else differs, the script stops after the configure step and prints the difference. Make the node
    match; only if every difference is harmless, run again with `--accept-configure-diff`, which records them in
    `BUILD_P.txt`.
  - Then `make all` and `make install/strip`, and the checks of the Dockerfile's last step. Every build starts with an
    empty install folder and a new build tree, as in the image.
  - GCC searches `/usr/local/include` before `/usr/include`, and the image had nothing there. After `make all` the
    script reads the compiler's dependency files (`*.o.d`, 2109 of them with P, 2110 with `b2d252b442`): every header a source file used must come
    from the source and build trees or from the folders the image's build used (`/usr/include`, `/usr/lib/gcc`,
    `/opt/libxml2`, `/opt/onnxruntime`, the nethost headers in `/usr/share/dotnet`). So a header from `/usr/local`
    stops the script, and so does one reached through a link in `/usr/local/include` (GCC writes the real path of
    such a header). No library of P may be loaded from `/usr/local` either, so `--work` and `--prefix` must not be
    under `/usr/local`. Nor may they hold white space, `#`, `$` or `\` (GCC escapes these in its dependency files,
    and CMake refuses `#`).
  - The build is generic: no `-march=native`. The search engines of OpenMS's THIRDPARTY repository, which the
    Dockerfile puts on the `PATH`, are left out, as OpenMS's CMake uses them only to add tests.
- **Checks at the end:**
  - `ProSE`, `FileConverter` and `EntrapmentEvaluator` find every library, none from `/usr/local`, and load
    `libOpenMS.so` from `<prefix>/lib`;
  - they print version 3.7.0 and `Revision: eaf9175`, and have the image's RUNPATH;
  - the three PeptDeep models and the Thermo bridge are installed;
  - `<prefix>/BUILD_P.txt` records the node, CMake call, compiler, configure comparison, dependency versions, package
    differences and CMake cache entries.

The source, build tree and the logs (`build_P.log`, `configure.log`, `configure.diff`) go to `--work` (default
`./build_P_eaf9175bc7`, about 4 GB). A build at `-j` the number of CPUs (at most one job per 2 GB of free memory) takes
about 20 minutes on 20 cores. P needs the .NET 8 runtime for Thermo `.raw` files: `DOTNET_ROOT=/usr/share/dotnet`
(set by `node_env.sh`).

## `prepare_node.sh`: the checks after copying and the set-up

Each step stops the script at its first failure and says from which step to run again. `--from <step>` starts at a
step, `--only <step>[,<step>...]` runs only those. The quick steps come first, so a missing tool shows before the
116 GB hash pass. The record goes to `<copy>/node_prep/` (`prepare.log` and the files below).

| Step | What it does |
|---|---|
| `machine` | RAM, CPUs, SMT, OS, storage and N into `machine.txt` (task 7); a role, N or `W_node` other than in the `machine.txt` before gets a note. The memory cap must be in force (`systemd-run --user`, 1G and N GB, no swap), and no cgroup above the user's scopes may hold memory lower (`memory.max`, `memory.high`). The CPUs: what `taskset -c 0-<last>` gets in such a scope, which is what the cpusets in force leave (on Ubuntu 24.04 the user's own cgroups have no cpuset, but `user.slice` may), and what a process there gets without `taskset` (this shell's affinity, which the scope keeps). On the scaling node, whose runs `bench.py` pins, CPUs 0–191 must be 192 different cores, all of them got with `taskset`, and no CPU quota above may be lower. On the engine node, whose runs are not pinned, fewer than 16 CPUs without `taskset` get a note. The copy must not be on a `noexec` mount. The file system of the copy and of `W_node` goes into `machine.txt`; a network file system (by its type in the mount table, of the mount in effect: `nfs4`, `fuse.sshfs`, `beegfs`, ...; under an automount the one above `autofs`) gets a warning, as the timed runs should read from a local disk. `machine.txt` also records the role, N, `W_node` and glibc's malloc settings of the shell (`MALLOC_*`, `GLIBC_TUNABLES`; set ones get a note, as they change the memory and time of the timed runs), and, as its mark, `machine: passed` once every check passed |
| `tools` | the executable bits of Sage and Percolator; `/usr/bin/time -v` and `taskset`; the Percolator build that prints `Percolator version 3.09.0` here (`.deb`, else `.rpm` build; if neither does, why); Sage 0.14.7 (prints `sage 0.14.6`); Java, and MSFragger printing `MSFragger version MSFragger-4.4.1` |
| `copy` | prose-paper at `PAPER_MIN` of `prepare_node.sh` or later (`1327715`, the commit that brought P = `eaf9175bc7`) and without changed files (a copy from Windows has CRLF line ends: clone afresh); P's tarballs against `tools/openms.sha256`; the two vendor files of `W_node` against `benchmarks/vendor.sha256`, moved from `work/vendor/` to `W_node/vendor/` (for a new `--w-node`, taken from an earlier `W_node`: below); the 92 mzML against `datasets/mzml.sha256` (116 GB to read) |
| `native` | unpacks P's native copy (`tools/openms-eaf9175bc7-native.tar.gz`) into `tools/`, through a temporary folder (an unpack that stops leaves nothing half-done); every file of the tarball must be there; then the tools, in a subshell with its `env_native.sh` |
| `build` | the node build, checked in this shell's environment without another OpenMS (`OPENMS_DATA_PATH` cleared, no `libOpenMS.so` on `LD_LIBRARY_PATH`; a set `LD_LIBRARY_PATH` gets a note, as the timed runs keep it too): `BUILD_P.txt` written by `build_P.sh` on this node, with ONNX, Thermo bridge and opentims, and the image's configure output (or the accepted differences, shown); every library found, `libOpenMS.so` from the build, version and revision, PeptDeep models, Thermo bridge, the .NET 8 runtime. Its storage is checked as in `machine` (not `noexec`; a network file system gets a warning), and `machine.txt` gets a line that the untimed checks use it from now on. `--hand-build` accepts a build without `BUILD_P.txt` and records that it was not checked |
| `params` | the 12 ProSE parameter files written again with P (`datasets/params/make_inis.py`, into `inis/`) against `datasets/params`: [`compare_inis.py`](compare_inis.py) must print `result: PASS` (only the version string and descriptions differ; task 11a). Any other difference stops the run order. Not compared: the order of a string parameter's allowed values. OpenMS lists the 33 enzymes of `Search:enzyme` in the order of their addresses in memory, and that order differs between two builds of P (for `b2d252b442`, the node build's was not the image's) and with glibc's malloc settings; the values are the same (below) |
| `versions` | `bench.py versions` and `databases` in `work/` (the 34 databases by SHA256 and accessions); in `versions.txt`, the three tools of P's `bin/` must print 3.7.0 and `Revision: eaf9175`, Sage `sage 0.14.6`, MSFragger `MSFragger version MSFragger-4.4.1` and Percolator `Percolator version 3.09.0` (what each printed, not the command) |
| `smoke` | the smoke test of the README with all three engines, under the memory cap, in a new folder `smoke_build/` (or `smoke_native/`) with the spectra of `smoke_work/vendor/` (about 15 minutes; 9 to 19 here). Each of its 23 commands must exit 0 (the first failure stops it). Then `commands.log` must have no `# FAILED`, `# NOT COUNTED` or `# NO TIMING`. Every search must end `ok`, and every timed run must exit 0, with rows of all three engines in `timings.tsv`. Every search of the run table must be counted in `coverage.tsv` |
| `env` | writes `<copy>/node_env.sh`, then sources it once in a subshell. The file refuses a shell on another host, a shell in which `env_native.sh` was sourced, a set `LD_PRELOAD`, and a `machine.txt` whose last step `machine` had another N or `W_node` or did not pass. It sources `tools/env.sh` and clears `OPENMS_DATA_PATH`. It sets `OPENMS_BIN` (the node build), `PERCOLATOR` (the build chosen above), `DOTNET_ROOT`, and `B` and `BW`, the driver with the main work folder and with `W_node` (`BW` only while `W_node/vendor/` holds the two vendor files, which the step `env` requires; else it says why; a refused source leaves no `B` or `BW` of an earlier one). It checks that `ProSE` loads the node build's `libOpenMS.so` |

Run it in a login shell that opens a session of its own (over `ssh`: a normal login; in the engine node's container:
`su - ubuntu` from root's `docker exec` shell, section "In a systemd container"; not `sudo`, not `docker exec -u`, not
`su` from another user's session): `systemd-run --user` needs the user's session bus. It stops under `sudo`, and
when `LD_PRELOAD` is set (every timed run would load it). Never run it, nor
the benchmark, in a shell in which `env_native.sh` was sourced: its `LD_LIBRARY_PATH` would make even the node build
load the native copy's `libOpenMS.so`. The script stops if it finds such a shell, and runs the native copy only in
subshells. The paths of `--copy`, `--openms-bin`, `--w-node` and `--dotnet-root` may hold only letters, digits and
`. _ / + -`, as `node_env.sh` embeds them.

**Before the node build exists:** `--native-only` runs the untimed checks (`params`, `versions`, `smoke`) with the
native copy and leaves out `build` and `env`. On a fresh node, run `bash build_P.sh --deps-only` first: Percolator's
`.deb` build, `/usr/bin/time` and Java come with it. Once P is built:
`prepare_node.sh ... --openms-bin <prefix>/bin --from build`, with the same `--copy`, `--mem-gb`, `--role` and
`--w-node` as before. A run without the step `machine` (`--from` a later step, or `--only`) stops if the step
`machine` did not pass (no `machine: passed` in `machine.txt`) or if these differ from those in `machine.txt`: the
cap, the CPUs and the storage were checked for those only. After a new N, run `--from machine`, or the step `machine`
and then `--only smoke,env`, with the same `--role` and `--w-node` (without `--w-node` the default `<copy>/W_node` is
taken; the step `machine` notes a role, N or `W_node` other than the one before). After a new `W_node`, run
`--from machine`, or the step `machine` and then `--only copy,env`: the step `copy` moves the two vendor files from
`work/vendor/` into the new `W_node`; once they have left `work/vendor/`, it takes them from the default
`<copy>/W_node` or a `W_node` in which an earlier step `copy` found or put them (as `prepare.log` records), by a hard
link where it can (that `W_node` keeps them), else by a move (a symlink: a new symlink to its file), and checks them
again, with the 116 GB of mzML. `node_env.sh` refuses to load while the last step `machine` had other values than its
own, or did not pass, and sets no `BW` while `W_node` lacks the two files; a refused source leaves no `B` or `BW`.

**Left to you:** that MSFragger's licence (academic, non-transferable: `tools/msfragger/README.txt`) covers the person
who runs it.

**The nodes** (decided 2026-11-23, DATASETS.md sections 4.3 and 5): the engine node (`--role engine`) is an OpenStack
VM with 16 vCPUs of an AMD EPYC 7502 and 251 GiB RAM, and the engine comparison runs at 16 threads, the driver's
default. The owner runs the thread scaling later, on the scaling node (`--role scaling`).

## In a systemd container (the engine node)

The engine node's Ubuntu 20.04 boots with cgroup v1 by default. There `systemd-run --user` cannot give a scope a
memory cap, and `build_P.sh` needs Ubuntu 24.04. So the host boots into the unified cgroup v2 hierarchy, and P, both
scripts and every run of the benchmark run in an Ubuntu 24.04 container with systemd as PID 1 (decided 2026-11-23,
DATASETS.md section 5). Each engine invocation then gets its own scope of the user's systemd manager in the
container, and the memory cap is that of DATASETS.md section 4.3: `bench.py` and `prepare_node.sh` run unchanged.

- **The host** (as root): add `systemd.unified_cgroup_hierarchy=1 swapaccount=1` to the kernel command line, with a
  file in `/etc/default/grub.d/` that holds
  `GRUB_CMDLINE_LINUX="$GRUB_CMDLINE_LINUX systemd.unified_cgroup_hierarchy=1 swapaccount=1"`, then `update-grub` and
  a reboot (deleting the file, `update-grub` and a reboot undo it). Ubuntu's kernel 5.4 has swap accounting off:
  without the second parameter there is no `memory.swap.max`, and the driver stops at its check of the cap. After the
  reboot, `stat -fc %T /sys/fs/cgroup` prints `cgroup2fs`, `/sys/fs/cgroup/system.slice/memory.swap.max` exists, and
  `docker info` shows cgroup version 2.
- **The image:** [`systemd_container/Dockerfile`](systemd_container/Dockerfile), built with
  `--build-arg BASE=<image>` from an Ubuntu 24.04 image in which `build_P.sh` ran. On the engine node that image is a
  commit of the trial's container, which keeps what `build_P.sh` installed for the node build of `b2d252b442`. The build itself is in
  the copy (`<copy>/openms-P`, built in `<copy>/build_P` for `b2d252b442`), which the container gets as a bind mount. A commit does not
  keep the hostname: run the container with the one that `BUILD_P.txt` records (`--hostname` below), or the step
  `build` finds P built on another node. The Dockerfile removes the trial's test double of `systemd-run` and its
  `sudo` without a password. It masks the units that would touch the host's kernel, clock, devices, consoles or
  network or start jobs, and every timer, of the system manager and of the user managers. logind gets no virtual
  terminals (`NAutoVTs=0`, `ReserveVT=0`): privileged, the container sees the host's consoles, and logind would hold
  one and start gettys on them. It starts `/sbin/init`, with lingering for the user `ubuntu`.
- **The container**, and a login shell in it for `build_P.sh`, `prepare_node.sh` and the runs:

  ```bash
  docker run -d --name prose_bench_ct --hostname prose-node-ct --privileged --cgroupns=private -e container=docker \
    --tmpfs /run --tmpfs /run/lock --shm-size 4g --stop-timeout 60 --restart no \
    -v <copy>:<copy> --mount type=bind,source=<results folder>,target=<copy>/work/out <image>
  docker exec -it prose_bench_ct su - ubuntu
  ```

  `su - ubuntu` from root's shell of `docker exec` opens a session with the user's session bus; `docker exec -u
  ubuntu` opens none, and the driver then stops at its check of the cap. The container has no memory limit of its
  own. A limit on it would also be charged the page cache of every finished run, and once it filled up, each run
  would have to reclaim that cache inside its timed command. `--privileged` makes root in the container root on the
  host, hence the masked units and no `sudo`.
- **A dependency that a later P adds** (for `eaf9175bc7`: `curl`, if the container lacks it): `ubuntu` has no `sudo`
  there, so root on the host installs only that package, and `ubuntu` then builds with `--skip-deps`:

  ```bash
  docker exec prose_bench_ct sh -c 'apt-get update && apt-get install -y --no-install-recommends curl'
  docker exec -it prose_bench_ct su - ubuntu    # then: bash build_P.sh --skip-deps --prefix ... --work <a new folder>
  ```

  apt may bring `libcurl4t64` and `libcurl4-openssl-dev` to the version of that `curl`; `BUILD_P.txt` lists every
  version that differs from the image's. Not `build_P.sh --deps-only` as root: it would also bring every other package
  it names to Ubuntu's current version, MSFragger's OpenJDK and python3 among them, under which the trial ran.
- **Long runs**, apart from the terminal (a closed terminal would end a search as `interrupted`): in that login
  shell,

  ```bash
  systemd-run --user --unit=prose-<step> --collect bash -lc \
    'exec > <log> 2>&1; source <copy>/node_env.sh && cd <copy>/prose-paper/benchmarks && $B <stage> ...'
  ```

  `<log>` is an absolute path outside the clone; it also gets a refusal of `node_env.sh`, as the unit is gone once it
  ends (`--collect`). The unit runs in the user's lingering manager, so it outlives the login shell; `systemctl
  --user status prose-<step>` shows it while it runs. A unit started this way had the session bus and read back a
  200G cap after its login shell had ended (engine node, 2026-11-23; the driver itself not yet run so).
- **Checks**, before `prepare_node.sh`. In that login shell:
  - `systemctl is-system-running` prints `running`, and no timer is active (`systemctl list-units --type=timer
    --state=active`, and the same with `--user`);
  - scopes of 1G and 200G read back `memory.max` 1073741824 and 214748364800 and `memory.swap.max` 0, with `max` in
    every cgroup above them that the container sees, up to its own cgroup;
  - 2 GiB written under a 1 GiB cap is killed (exit 137);
  - 512 MiB under the same cap exits 0.

  As root on the host, as the user in the container can list neither the open files of root's processes nor the
  cgroups above the container's own (nor can the step `machine`):
  - `docker exec prose_bench_ct sh -c 'ls -l /proc/$(pidof systemd-logind)/fd'` lists logind's files, and none is a
    `/dev/tty<n>`;
  - `memory.max` and `memory.high` of `/sys/fs/cgroup/system.slice` and of its `docker-<id>.scope` are `max`;
  - the kernel log (`dmesg | grep oom_memcg=`) names the scope of that kill;
  - before the first run that counts, no other container runs (`docker ps`) and no other jobs.

  On the engine node on 2026-11-23, the image before the last rebuild passed systemd's state and the cap items
  (record `checks/node_trial/records/routeB_cap_proof_2026-11-23.console`; the host's cgroups:
  `routeB_review_reads_2026-11-23.console`), but a user timer was active and logind held a host console. The rebuilt
  image passed every check above except the last, which is due only before the first run that counts
  (`routeB_host_step5_2026-11-23.console`; records outside this repository).

## Files

- [`build_P.sh`](build_P.sh), [`prepare_node.sh`](prepare_node.sh).
- [`systemd_container/Dockerfile`](systemd_container/Dockerfile): the image with systemd as PID 1 for the engine node
  (above).
- [`image_configure.txt`](image_configure.txt): the image's configure output, normalized (made from
  `checks/freeze_eaf9175bc7/build.log` with `build_P.sh --normalize-configure`; the command is in the header of
  `build_P.sh`).
- [`image_packages.txt`](image_packages.txt): the 264 packages the image's `base` stage installed, with their versions
  (from the same log, step `[base 2/7]`: the stage was built anew on 2026-11-26, as the Dockerfile's apt list
  changed; its base was the local `ubuntu:24.04` of 2026-02-23,
  `ubuntu@sha256:186072bba1b2f436cbb91ef2567abca677337cfc786c86e107d25b7072feef0c`). Against the list of
  `b2d252b442` (280 packages): HDF5
  and the packages it pulled in are gone (OpenMS #10937), `curl` is new, and 29 packages have newer Ubuntu updates.
- [`compare_inis.py`](compare_inis.py): the parameter-file comparison of the freeze of `b2d252b442` (2026-11-16,
  `checks/freeze_P/compare_inis.py`), with one change (2026-11-17): the order of a string parameter's allowed values
  is not compared, only the values. The ProSE of the `b2d252b442` image writes the 33 enzymes of `Search:enzyme` in the order of
  `datasets/params`, the node build in another one: OpenMS keeps them in a `std::set` of pointers
  (`DigestionEnzymeDB`), ordered by address, so the order depends on the binary and on the heap at start. With
  glibc's default malloc settings it is fixed for a binary (the image's ProSE gives its order also after a move to
  another folder, two node builds give theirs); with tcache off (`GLIBC_TUNABLES=glibc.malloc.tcache_count=0`) the
  image's ProSE gives another fixed order, and with `MALLOC_ARENA_MAX` 1 or 2 a different one from run to run. The
  value of the parameter (`Trypsin/P` or `unspecific cleavage`) and the set of 33 enzymes are the same, and ProSE
  takes the enzyme by its name. Such parameters are listed as "order of the allowed values"; a missing, added or
  repeated value still fails.

## Tested (preparation PC: with P = `eaf9175bc7` on 2026-11-26, with `b2d252b442` on 2026-11-17)

- With P (2026-11-26), `build_P.sh` as a node runs it, in a fresh `ubuntu:24.04` container (the base of the image,
  `ubuntu@sha256:186072bb…`), as a user with `sudo`, with these scripts (a snapshot: `build_P.sh`,
  `compare_inis.py` and the two `image_*.txt` equal to the files here, `prepare_node.sh` but for the comment and
  value of `PAPER_MIN`, changed after the tests):
  - `--deps-only` installed every dependency (34 minutes), ONNX Runtime from the mirror
    (`github.com/microsoft/onnxruntime` did not serve it), checked by its SHA256;
  - then `--skip-deps` built P in 31 minutes (12 jobs), the managed half of the Thermo bridge from the bridge's
    release: the image's configure output and RUNPATH, no package version other than the image's, every header from
    the image's folders (2109 dependency files), and `ProSE`, `FileConverter` and `EntrapmentEvaluator` print
    `Revision: eaf9175`;
  - its install has the image's 1630 files and links (and `BUILD_P.txt` and `.build_P`). 154 differ in content, by
    the build folder or install prefix compiled in: the 147 tools, `libOpenMS.so`, `libOpenMS_CLI.so`, `config.h`,
    `openms_data_path.h`, `libopentims_cpp.a` and the two `.pc` files. The rest are the image's to the byte, the
    Thermo bridge's managed files among them (now both from the bridge's release), and `libOpenSwathAlgo.so`,
    `libopenms_thermo_bridge.so` and `libonnxruntime`; no link differs. Of the 154, nine differ in size too:
    `libOpenMS.so`, `libopentims_cpp.a`, `openms_data_path.h`, the two `.pc` files and four tools by one page each.
- With P (2026-11-26), `prepare_node.sh --native-only` in WSL (Ubuntu 24.04, systemd user session) on a test copy
  with these scripts, the steps `machine`, `tools`, `native`, `params`, `versions` and `smoke` (`copy`, which checks
  `PAPER_MIN`, left out): every step passed in 8 minutes. P's native tarball matched `tools/openms.sha256`; `ProSE`,
  `FileConverter` and `EntrapmentEvaluator` of the unpacked copy print `Revision: eaf9175`; the 12 parameter files
  it wrote equal `datasets/params/` (no value or description differs); the smoke test ran every command with exit 0,
  33 searches, each counted.
- With `b2d252b442` (2026-11-17), `build_P.sh` in a fresh `ubuntu:24.04` container, as a user with `sudo`:
  - the first run installed everything and built `b2d252b442` in about 20 minutes (18 jobs);
  - a re-run over that install, from a shell with `CXX`, `CPATH` and `LD_LIBRARY_PATH` set, gave the image's
    configure output and RUNPATH;
  - its install has the image's 1626 files and links (and `BUILD_P.txt` and the marker `.build_P`). 157 files differ
    in content, by the build folder or install prefix compiled in (`/tmp/OpenMS` in the image; in `libOpenMS.so` also
    the build date): the 147 tools, `libOpenMS.so`, `libOpenMS_CLI.so`, the Thermo bridge's
    `ThermoWrapperManaged.dll` (in `lib/` and `share/`) and its `.pdb`, `config.h`, `openms_data_path.h`,
    `libopentims_cpp.a` and the two `.pc` files of HiGHS and opentims. The other 1469, `libOpenSwathAlgo.so`,
    `libopenms_thermo_bridge.so` and `libonnxruntime` among them, are the image's to the byte (links: the same
    target). Of the 157, ten differ in size too: `libOpenMS.so`, `libopentims_cpp.a`, the DLLs and the `.pdb`,
    `openms_data_path.h`, the `.pc` files, and two tools by one page each (`OpenMSInfo` 4096 bytes smaller,
    `OpenSwathInfer` 4096 larger);
  - four glibc packages were newer than in the image (Ubuntu's updates since), as `BUILD_P.txt` lists them;
  - the last two runs had traps a node may hold: Doxygen installed, a broken `ld` and `as` in `/usr/local/bin`,
    `zlib1g:i386`, and (the last run) `gcc-13` held. Both passed: Doxygen unused, Ubuntu's `ld` and `as` used, no
    header from outside the image's folders. The last run, into another prefix, has every tool and library of the
    run before it to the byte but `libOpenMS.so` (build time and the install prefix compiled in); of the other files
    only `openms_data_path.h`, the two `.pc` files (the install prefix) and `BUILD_P.txt` differ;
  - with a package that conflicts with the image's (`libcurl4-gnutls-dev`), `--deps-only` stopped and removed nothing.
- `prepare_node.sh`:
  - `--native-only` in WSL (Ubuntu 24.04, systemd user session), on a test copy: every step passed, the smoke test
    included;
  - with the node build, in the container (a test double for `systemd-run`): every step but `copy` passed. The
    parameter check passes with the order lines above. The smoke test's `counts.tsv` is the same as with the native
    copy;
  - the guards: a native copy given as the node build, a second pass with other arguments or after a failed step
    `machine`, `node_env.sh` in a shell with `env_native.sh` or `LD_PRELOAD`, on another host, or with another N
    or `W_node` than the last step `machine`, the step `env` without the vendor files, and paths with characters
    outside the allowed ones;
  - on throwaway copies with dummy vendor files: the step `copy` with a new `--w-node` takes the two files from the
    `W_node` before (also from one they were put into by hand), by a hard link that leaves them there; a
    `node_env.sh` whose `W_node` lost them loads without `BW`; a new N without `--w-node` gets a note.
- Seven review rounds; from the second on, each finding was checked by a second reviewer who tried to refute it. The
  records are in `checks/node_scripts/` of the preparation folder (outside this repository); `HANDOFF.md` there has
  the summary.
