[English](../README.md) · [العربية](README.ar.md) · [Español](README.es.md) · [Français](README.fr.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Tiếng Việt](README.vi.md) · [中文 (简体)](README.zh-Hans.md) · [中文（繁體）](README.zh-Hant.md) · [Deutsch](README.de.md) · [Русский](README.ru.md)

[![LazyingArt banner](https://github.com/lachlanchen/lachlanchen/raw/main/figs/banner.png)](https://github.com/lachlanchen/lachlanchen/blob/main/figs/banner.png)

# LazyTunnel

*SSH zwischen privaten Rechnern, unabhängig von der Desktop-Steuerung.*

[Website](https://lazying.art) · [GitHub Sponsors](https://github.com/sponsors/lachlanchen)

LazyTunnel ist ein kleines OpenSSH- und systemd-Werkzeugpaket, das private Rechner über einen Cloud-Relay verbindet. Jeder Rechner startet seinen eigenen ausgehenden Tunnel. Ein Wechsel der Steuerung über UU, RDP oder VNC besitzt diese Verbindung nicht. Shell und Dateiübertragung behalten die native SSH-Authentifizierung.

| Donate | PayPal | Stripe |
| --- | --- | --- |
| [![Donate](https://img.shields.io/badge/Donate-LazyingArt-0EA5E9?style=for-the-badge&logo=kofi&logoColor=white)](https://chat.lazying.art/donate) | [![PayPal](https://img.shields.io/badge/PayPal-RongzhouChen-00457C?style=for-the-badge&logo=paypal&logoColor=white)](https://paypal.me/RongzhouChen) | [![Stripe](https://img.shields.io/badge/Stripe-Donate-635BFF?style=for-the-badge&logo=stripe&logoColor=white)](https://buy.stripe.com/aFadR8gIaflgfQV6T4fw400) |

## Entwurf

Rückwärtige Listener binden ausschließlich an Cloud-Loopback. Tunnel-, Sprung- und Anmeldeschlüssel sind getrennt; Hostschlüssel werden fest hinterlegt. VPN, Container, Änderungen der Standardroute oder öffentliche Desktop-Ports sind nicht nötig. Das Projekt ergänzt LazyEdge, ohne dessen HTTP-Schutz zu umgehen.

```text
alpha ── outbound SSH ── cloud loopback ── outbound SSH ── beta
```

## Schnellstart

Das Beispiel enthält synthetische Testschlüssel und einen ungültigen Hostnamen: Es dient zum Prüfen der Ausgabe, nicht zum Verbinden. Registrieren Sie echte Rechner getrennt und lesen Sie die vollständige Anleitung vor dem Einsatz eines Installers.

```bash
python3 lazytunnel.py validate --config examples/two-peers.json
python3 lazytunnel.py plan --config examples/two-peers.json
python3 -m unittest discover -s tests -v
```

## Dateien und Bereitstellung

Lesen Sie Architektur und Betriebshandbuch. Die Registrierung behält private Schlüssel auf ihrem Ursprungsrechner. Cloud- und Rechner-Installer zeigen ohne ausdrückliches --apply nur einen Plan. Bestehende UU-Aliase und Desktop-Dienste bleiben unverändert.

[docs/design.md](../docs/design.md) · [docs/operations.md](../docs/operations.md) · [scripts/](../scripts/) · [tests/](../tests/)

## Privater Webzugriff

Öffne auf beta einen lokalen Dienst von alpha über die vorhandene SSH-Verbindung. Führe die folgenden Befehle aus und öffne auf beta `http://127.0.0.1:6144/wechat`. Der Port bleibt auf die lokale Loopback-Adresse beschränkt; Desktop-Dienste werden nicht verändert.

```bash
install -D -m 0755 scripts/lazy-web "$HOME/.local/bin/lazy-web"
lazy-web run alpha 6144
```

[Dauerhafte Weiterleitungen, entferntes LAN, SOCKS und Fehlersuche](../docs/private-web.md).


## Prüfung und Status

Frühe Version mit Prüfung durch den Betreiber. Generatortests und die anfängliche Cloud-Administration wurden geprüft; jede reale Installation braucht weiterhin beidseitige Shell-, Datei-, Wiederherstellungs- und Negativtests der Berechtigungen. Startaktivierung ist kein Neustarttest. Systemd stellt Verbindungen wieder her, nicht verlorene Shells; nutzen Sie entferntes tmux.

## Zitieren

Wenn Sie LazyTunnel verwenden, zitieren Sie dieses Repository. GitHub liest CITATION.cff für sein Zitationsfeld. [CITATION.cff](../CITATION.cff)

```bibtex
@software{chen_lazytunnel_2026,
  author = {Chen, Lachlan},
  title = {LazyTunnel: independent private SSH relays},
  year = {2026},
  url = {https://github.com/lachlanchen/LazyTunnel}
}
```
