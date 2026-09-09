[English](README.md) · [العربية](i18n/README.ar.md) · [Español](i18n/README.es.md) · [Français](i18n/README.fr.md) · [日本語](i18n/README.ja.md) · [한국어](i18n/README.ko.md) · [Tiếng Việt](i18n/README.vi.md) · [中文 (简体)](i18n/README.zh-Hans.md) · [中文（繁體）](i18n/README.zh-Hant.md) · [Deutsch](i18n/README.de.md) · [Русский](i18n/README.ru.md)

[![LazyingArt banner](https://github.com/lachlanchen/lachlanchen/raw/main/figs/banner.png)](https://github.com/lachlanchen/lachlanchen/blob/main/figs/banner.png)

# LazyTunnel

*SSH between private computers, independent of desktop control.*

[Website](https://remote.lazying.art) · [GitHub Sponsors](https://github.com/sponsors/lachlanchen)

LazyTunnel is a small OpenSSH and systemd toolkit for connecting private computers through a cloud relay. Each endpoint initiates its own tunnel. Switching UU, RDP or VNC control does not own that connection. Shell access and file transfers keep their native SSH authentication.

| Donate | PayPal | Stripe |
| --- | --- | --- |
| [![Donate](https://img.shields.io/badge/Donate-LazyingArt-0EA5E9?style=for-the-badge&logo=kofi&logoColor=white)](https://chat.lazying.art/donate) | [![PayPal](https://img.shields.io/badge/PayPal-RongzhouChen-00457C?style=for-the-badge&logo=paypal&logoColor=white)](https://paypal.me/RongzhouChen) | [![Stripe](https://img.shields.io/badge/Stripe-Donate-635BFF?style=for-the-badge&logo=stripe&logoColor=white)](https://buy.stripe.com/aFadR8gIaflgfQV6T4fw400) |

## Native apps, independent core

Meet **LazyRemote**, the product experience powered by this independent core. [Launch website](https://remote.lazying.art) · [Downloads and release notes](https://github.com/lachlanchen/LazyTunnel/releases/tag/v0.2.0). The current native preview is named LazyTunnel; existing commands and application identifiers stay unchanged.

The optional native app supports Ubuntu, macOS, Windows, iOS and Android with real Flutter management screens, secure saved connections, verified SSH terminals and private noVNC/web viewers. A standalone Python agent and a pure-Dart transport library remain independent of both native and browser GUIs.

[Native installation, connection setup, builds and signing](docs/native-apps.md).

[Apple release guide](docs/apple-publication.md): the workflow learned from EchoMind, an explicit release plan and a read-only readiness command. The iOS preview has not yet been uploaded to TestFlight or submitted to App Review.


[![Native LazyTunnel app with a sample fleet](website/assets/native-desktop.png)](https://remote.lazying.art)

## Install the CLI with npm

One small package provides the client and Linux relay administration commands. npm installation starts no services and keeps enrollment, credentials and remote desktops unchanged. The native graphical app remains a separate download.

```bash
npm install -g @lazyingart/lazytunnel
lazytunnel-client install
lazytunnel-client doctor
```

On the Linux relay:

```bash
lazytunnel-server install
sudo lazytunnel-server install --apply
```

[Complete npm installation, enrollment and update guide](docs/npm.md).

## Design

Reverse listeners stay on cloud loopback. Separate keys identify tunnel, jump and endpoint roles; host keys are pinned. No VPN, container, default-route change or public desktop port is required. This complements LazyEdge; it does not bypass its HTTP guards.

```text
alpha ── outbound SSH ── cloud loopback ── outbound SSH ── beta
```

## Quick start

The example contains synthetic keys and an invalid hostname: use it to inspect output, not to connect. Enroll real peers independently and review the complete deployment guide before using an installer.

```bash
python3 lazytunnel.py validate --config examples/two-peers.json
python3 lazytunnel.py plan --config examples/two-peers.json
python3 -m unittest discover -s tests -v
```

## Files and deployment

Read the architecture and operator runbook. The enrollment helper keeps private keys on their originating endpoint. Edge and worker installers print a plan unless explicitly given --apply. Existing UU aliases and desktop services stay unchanged.

[docs/design.md](docs/design.md) · [docs/operations.md](docs/operations.md) · [scripts/](scripts/) · [tests/](tests/)

## Private web access

On beta, open a local service hosted on alpha through the existing SSH route. Run the commands below, then browse `http://127.0.0.1:6144/wechat` on beta. The listener stays private and does not change desktop services.

```bash
install -D -m 0755 scripts/lazy-web "$HOME/.local/bin/lazy-web"
lazy-web run alpha 6144
```

[Persistent forwards, remote LAN targets, SOCKS and troubleshooting](docs/private-web.md).


## Validation and status

Early operator-reviewed release. Renderer tests and cloud administration bootstrap have been checked; every actual deployment still needs bidirectional shell, file-transfer, failure-recovery and negative-permission tests. Boot enablement is not a reboot test. Systemd can restore a connection, not a lost shell; use remote tmux.

## SSH names across devices

Reviewed endpoint helpers preserve existing SSH settings and install the same private device names on Linux, macOS and Windows. Each device keeps its own private keys.

[Device enrollment, routes and rollback](docs/device-ssh.md).


## Independent server and clients

The fleet extension supports Linux, macOS and Windows with separate server and client updates. Device keys and private configuration stay outside Git; a pinned SSH registry lets an enrolled client refresh its device list without administrator credentials. The live seven-device deployment passed all 49 directed SSH checks; boot settings were inspected without rebooting.

On an enrolled Linux/macOS client:

```bash
lazytunnel status
lazytunnel devices
ssh-lazy-alpha
lazytunnel sync
lazytunnel web alpha 6144 --local-port 16144 --path /wecom
```

[Installation, enrollment/login, updates, Windows fixes and private noVNC access](docs/fleet.md).


## Optional private GUI

A lightweight browser console brings enrolled computers, on-demand SSH checks and saved noVNC viewers together. It includes search, grid/list layouts, light/dark themes and a phone-sized layout. On Linux, viewer forwards have their own systemd services and survive a GUI restart. Keys and access codes remain private; existing desktops and SSH carriers are preserved.

```bash
cd /path/to/LazyTunnel
python3 scripts/lazytunnel-client.py update --source .
lazytunnel gui install
lazytunnel gui code
lazytunnel gui
```

[Installation, access-code unlock, remote browsers and security boundaries](docs/gui.md).


## Citation

If you use LazyTunnel, cite this repository. GitHub reads CITATION.cff for its citation panel. [CITATION.cff](CITATION.cff)

```bibtex
@software{chen_lazytunnel_2026,
  author = {Chen, Lachlan},
  title = {LazyTunnel: independent private SSH relays},
  year = {2026},
  url = {https://github.com/lachlanchen/LazyTunnel}
}
```
