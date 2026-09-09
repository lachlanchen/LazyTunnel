#!/usr/bin/env python3
"""Validate and render private OpenSSH relay artifacts; never deploy implicitly."""
import argparse
import base64
import json
import os
from pathlib import Path
import re
import sys

NAME = re.compile(r"[a-z][a-z0-9-]{0,19}\Z")
USER = re.compile(r"[a-z_][a-z0-9_-]{0,30}\Z")
HOST = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9.-]{0,252}\Z")
PATH = re.compile(r"/[a-zA-Z0-9_./-]+\Z")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def port(value):
    require(type(value) is int and 1024 <= value <= 65535,
            "relay/edge ports must be integers between 1024 and 65535")
    return value


def public_key(value):
    require(isinstance(value, str) and len(value) < 1000, "invalid public key")
    parts = value.split()
    require(len(parts) == 2 and parts[0] == "ssh-ed25519", "use a comment-free Ed25519 public key")
    require(value == ' '.join(parts), 'use canonical single-line public keys')
    try:
        raw = base64.b64decode(parts[1], validate=True)
    except Exception as exc:
        raise ValueError("invalid key encoding") from exc
    # RFC 4253 strings: algorithm name followed by the 32-byte public key.
    require(len(raw) == 51 and raw[:19] == b"\x00\x00\x00\x0bssh-ed25519\x00\x00\x00\x20",
            "invalid Ed25519 public key blob")
    require(base64.b64encode(raw).decode() == parts[1], 'use canonical key encoding')
    return value


def exact_keys(obj, keys, label):
    require(isinstance(obj, dict) and set(obj) == set(keys), f"unexpected or missing {label} fields")


def validate(c):
    exact_keys(c, ["version", "edge", "peers"], "configuration")
    require(c["version"] == 1, "unsupported configuration version")
    e = c["edge"]
    exact_keys(e, ["host", "port", "host_key"], "edge")
    require(isinstance(e["host"], str) and HOST.fullmatch(e["host"]), "invalid edge hostname/IPv4 address")
    port(e["port"])
    public_key(e["host_key"])
    require(isinstance(c["peers"], list) and 2 <= len(c["peers"]) <= 16, "configure 2–16 peers")
    names, ports, identities = set(), set(), set()
    host_keys = {e['host_key']}
    for p in c["peers"]:
        exact_keys(p, ["name", "user", "home", "ssh_port", "relay_port", "host_key",
                       "tunnel_key", "jump_key", "login_key"], "peer")
        require(isinstance(p["name"], str) and NAME.fullmatch(p["name"]), "invalid peer name")
        require(p["name"] not in names, "duplicate peer name")
        names.add(p["name"])
        port(p["relay_port"])
        require(p["relay_port"] not in ports and p["relay_port"] != e["port"], "duplicate/colliding relay port")
        ports.add(p["relay_port"])
        require(isinstance(p["user"], str) and USER.fullmatch(p["user"]) and p["user"] != "root",
                "use an unprivileged endpoint user")
        require(isinstance(p["home"], str) and PATH.fullmatch(p["home"])
                and p["home"] != "/" and ".." not in p["home"].split("/")
                and "//" not in p["home"] and not p["home"].endswith("/"), "invalid absolute endpoint home")
        require(type(p["ssh_port"]) is int and 1 <= p["ssh_port"] <= 65535, "invalid endpoint SSH port")
        public_key(p["host_key"])
        require(p['host_key'] not in host_keys, 'each host needs a unique host key')
        host_keys.add(p['host_key'])
        for field in ["tunnel_key", "jump_key", "login_key"]:
            public_key(p[field])
            require(p[field] not in identities, "keys must be separate across roles and peers")
            require(p[field] not in [e["host_key"], p["host_key"]], "host key cannot be an identity key")
            identities.add(p[field])
    require(not host_keys.intersection(identities), 'host keys and client identities must be distinct')
    return c


def edge_files(c):
    lines = ["# LazyTunnel-owned identity policy. Does not change public SSH ports."]
    result = {}
    for p in c["peers"]:
        destinations = [f'127.0.0.1:{q["relay_port"]}' for q in c["peers"] if q is not p]
        for role in ["tun", "hop"]:
            user = f'lt-{role}-{p["name"]}'
            lines += [f"Match User {user}",
                      "    AuthenticationMethods publickey", "    PubkeyAuthentication yes",
                      "    PasswordAuthentication no", "    KbdInteractiveAuthentication no",
                      "    PermitTTY no", "    X11Forwarding no", "    AllowAgentForwarding no",
                      "    AllowStreamLocalForwarding no",
                      "    PermitTunnel no", "    GatewayPorts no", "    MaxSessions 0",
                      "    ForceCommand /usr/sbin/nologin", "    ClientAliveInterval 15",
                      "    ClientAliveCountMax 3", "    AuthorizedKeysFile /etc/lazytunnel/keys/%u"]
            if role == "tun":
                target = f'127.0.0.1:{p["relay_port"]}'
                lines += ["    AllowTcpForwarding remote", f"    PermitListen {target}", "    PermitOpen none"]
                options = f'restrict,port-forwarding,permitlisten="{target}"'
                key = p["tunnel_key"]
            else:
                lines += ["    AllowTcpForwarding local", "    PermitListen none",
                          "    PermitOpen " + " ".join(destinations)]
                options = "restrict,port-forwarding," + ",".join(f'permitopen="{d}"' for d in destinations)
                key = p["jump_key"]
            result[f"keys/{user}"] = f"{options} {key}\n"
            lines += [""]
    lines += ["Match all", ""]
    result["60-lazytunnel.conf"] = "\n".join(lines)
    result["accounts.txt"] = "".join(f'lt-{r}-{p["name"]}\n' for p in c["peers"] for r in ["tun", "hop"])
    return result


def worker_files(c, name):
    matches = [p for p in c["peers"] if p["name"] == name]
    require(len(matches) == 1, "unknown peer")
    p = matches[0]
    e = c["edge"]
    state = f'{p["home"]}/.config/lazytunnel'
    ssh = []
    common = ["    IdentitiesOnly yes", "    BatchMode yes", "    PasswordAuthentication no",
              "    KbdInteractiveAuthentication no", "    StrictHostKeyChecking yes",
              f"    UserKnownHostsFile {state}/known_hosts", "    GlobalKnownHostsFile /dev/null",
              "    ForwardAgent no", "    ForwardX11 no", "    ControlMaster no", "    ControlPath none",
              "    ConnectionAttempts 1", "    ConnectTimeout 10", "    ServerAliveInterval 15",
              "    ServerAliveCountMax 3", "    UpdateHostKeys no"]
    for role, alias in [("tun", "lazytunnel-carrier"), ("hop", "lazytunnel-hop")]:
        ssh += [f"Host {alias}", f'    HostName {e["host"]}', f'    Port {e["port"]}',
                f'    User lt-{role}-{name}', "    HostKeyAlias lazytunnel-edge",
                f'    IdentityFile {state}/{"tunnel" if role == "tun" else "jump"}_ed25519'] + common
        if role == "tun":
            ssh += ["    RequestTTY no", "    ExitOnForwardFailure yes",
                    f'    RemoteForward 127.0.0.1:{p["relay_port"]} 127.0.0.1:{p["ssh_port"]}']
        ssh += [""]
    for q in c["peers"]:
        if q is p:
            continue
        ssh += [f'Host {q["name"]} lazy-{q["name"]}', "    HostName 127.0.0.1",
                f'    Port {q["relay_port"]}', f'    User {q["user"]}',
                f'    HostKeyAlias lazytunnel-{q["name"]}', f"    IdentityFile {state}/login_ed25519",
                # An explicit ProxyCommand passes this private -F configuration
                # to the child SSH; native ProxyJump may consult another config.
                f'    ProxyCommand /usr/bin/ssh -F {state}/ssh_config -W %h:%p lazytunnel-hop'] + common + [""]
    unit = f'''[Unit]
Description=LazyTunnel outbound SSH carrier ({name})
StartLimitIntervalSec=0

[Service]
Type=simple
ExecStart=/usr/bin/ssh -F {state}/ssh_config -NT lazytunnel-carrier
Restart=always
RestartSec=15
TimeoutStopSec=10
KillMode=control-group
UMask=0077
NoNewPrivileges=yes

[Install]
WantedBy=default.target
'''
    keys = [f'lazytunnel-edge {e["host_key"]}']
    keys += [f'lazytunnel-{q["name"]} {q["host_key"]}' for q in c["peers"] if q is not p]
    access = [q["login_key"] + f' lazytunnel-from-{q["name"]}' for q in c["peers"] if q is not p]
    return {"ssh_config": "\n".join(ssh), "known_hosts": "\n".join(keys) + "\n",
            "lazytunnel.service": unit,
            "authorized_keys.append": "\n".join(access) + "\n"}


def write_bundle(root, files):
    # New empty directory only: never overwrite a live configuration or follow
    # an output symlink. Installation is a separate reviewed operator action.
    root = Path(root).absolute()
    for parent in [root, *root.parents]:
        require(not parent.is_symlink(), "output path must not traverse symlinks")
    require(not root.exists(), "output already exists; choose a new candidate directory")
    root.mkdir(mode=0o700, parents=True)
    for name, content in files.items():
        dest = root / name
        dest.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        fd = os.open(dest, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "w") as f:
            f.write(content)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["validate", "plan", "render"])
    parser.add_argument("--config", required=True)
    parser.add_argument("--role", choices=["edge", "worker"])
    parser.add_argument("--peer")
    parser.add_argument("--output")
    args = parser.parse_args()
    try:
        config = validate(json.loads(Path(args.config).read_text()))
        if args.action == "validate":
            print("Configuration valid; no changes made.")
        elif args.action == "plan":
            print("Independent OpenSSH relay; no changes made.")
            for p in config["peers"]:
                print(f'{p["name"]}: outbound carrier -> cloud 127.0.0.1:{p["relay_port"]} -> endpoint loopback SSH')
            print("No UU takeover, DNS change, firewall replacement or public reverse listeners.")
        else:
            require(args.role and args.output, "render requires --role and --output")
            files = edge_files(config) if args.role == "edge" else worker_files(config, args.peer)
            write_bundle(args.output, files)
            print(f"Rendered {len(files)} candidate files; not installed or started.")
        return 0
    except (ValueError, OSError, KeyError, TypeError) as e:
        # Do not echo full input objects, which may have been private configs.
        print(f"LazyTunnel: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
