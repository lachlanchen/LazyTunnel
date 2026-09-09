FROM ubuntu:24.04
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends python3 openssh-server openssh-client sudo iproute2 sshpass \
    && rm -rf /var/lib/apt/lists/* && mkdir -p /run/sshd
# This fixture reloads its own PID-1 sshd. It never controls host systemd.
RUN printf '#!/bin/sh\n[ "$*" = "reload ssh.service" ] || exit 1\nkill -HUP 1\n' > /usr/bin/systemctl && chmod 755 /usr/bin/systemctl
CMD ["/usr/sbin/sshd", "-D", "-e"]
