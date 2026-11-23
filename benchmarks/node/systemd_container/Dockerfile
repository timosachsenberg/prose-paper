# Ubuntu 24.04 with systemd 255 as PID 1, so that `systemd-run --user --scope` gives each engine invocation a real
# memory cap on a host whose own OS cannot (benchmarks/node/README.md, "In a systemd container"). BASE is an image in
# which build_P.sh ran; on the engine node, a commit of the trial's container, which keeps the dependencies of P's
# node build (the build itself is in the bind-mounted copy). Run it with the hostname that BUILD_P.txt records.
ARG BASE
FROM ${BASE}
ENV container=docker
# The trial's test double of systemd-run, and its password-free sudo: the container runs privileged, so root in it is
# root on the host, and nothing of the benchmark needs sudo once P is built.
RUN rm -f /usr/local/bin/systemd-run /etc/sudoers.d/ubuntu \
 && test -x /usr/bin/systemd-run && test -x /lib/systemd/systemd
# Units that would touch the host's kernel, clock, devices, consoles or network, or start jobs during the timed runs.
# A masked unit is a link to /dev/null (what `systemctl mask` writes). Every timer is masked, of the system manager
# and of the user managers (the lingering one runs the benchmark). logind gets no virtual terminals: privileged, the
# container sees the host's /dev/tty*, and logind would hold one and start gettys on the host's consoles.
RUN set -e; cd /etc/systemd/system; \
    for u in systemd-sysctl.service systemd-modules-load.service systemd-binfmt.service \
             proc-sys-fs-binfmt_misc.automount proc-sys-fs-binfmt_misc.mount \
             systemd-timesyncd.service systemd-resolved.service systemd-networkd.service systemd-networkd.socket \
             systemd-networkd-wait-online.service networkd-dispatcher.service systemd-udevd.service systemd-udevd-control.socket \
             systemd-udevd-kernel.socket systemd-udev-trigger.service systemd-udev-settle.service \
             systemd-hwdb-update.service systemd-random-seed.service systemd-pstore.service systemd-remount-fs.service \
             systemd-firstboot.service systemd-machine-id-commit.service systemd-journald-audit.socket \
             sys-kernel-debug.mount sys-kernel-tracing.mount sys-kernel-config.mount sys-fs-fuse-connections.mount \
             dev-hugepages.mount dev-mqueue.mount tmp.mount \
             getty.target getty@.service autovt@.service console-getty.service getty@tty1.service serial-getty@ttyS0.service \
             e2scrub_reap.service apt-daily.service apt-daily-upgrade.service unattended-upgrades.service \
             cron.service anacron.service atd.service ssh.service ssh.socket; do \
      ln -sf /dev/null "$u"; done; \
    for t in $(find /lib/systemd/system /usr/lib/systemd/system /etc/systemd/system -name '*.timer' -printf '%f\n' 2>/dev/null | sort -u); do \
      ln -sf /dev/null "$t"; done; \
    mkdir -p /etc/systemd/user; \
    for t in $(find /usr/lib/systemd/user /etc/systemd/user -name '*.timer' -printf '%f\n' 2>/dev/null | sort -u); do \
      ln -sf /dev/null "/etc/systemd/user/$t"; done; \
    mkdir -p /etc/systemd/logind.conf.d; printf '[Login]\nNAutoVTs=0\nReserveVT=0\n' > /etc/systemd/logind.conf.d/no-vt.conf; \
    ln -sf /lib/systemd/system/multi-user.target default.target; \
    mkdir -p /var/lib/systemd/linger && touch /var/lib/systemd/linger/ubuntu; \
    systemctl list-unit-files --state=enabled --no-pager | sed 's/^/enabled: /'; \
    systemctl --global list-unit-files --type=timer --no-pager | sed 's/^/user timer: /'
STOPSIGNAL SIGRTMIN+3
CMD ["/sbin/init"]
