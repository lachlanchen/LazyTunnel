[English](../README.md) · [العربية](README.ar.md) · [Español](README.es.md) · [Français](README.fr.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Tiếng Việt](README.vi.md) · [中文 (简体)](README.zh-Hans.md) · [中文（繁體）](README.zh-Hant.md) · [Deutsch](README.de.md) · [Русский](README.ru.md)

[![LazyingArt banner](https://github.com/lachlanchen/lachlanchen/raw/main/figs/banner.png)](https://github.com/lachlanchen/lachlanchen/blob/main/figs/banner.png)

# LazyTunnel

*SSH entre ordinateurs privés, indépendant du contrôle du bureau.*

[Website](https://lazying.art) · [GitHub Sponsors](https://github.com/sponsors/lachlanchen)

LazyTunnel est un petit ensemble d’outils OpenSSH et systemd reliant des ordinateurs privés par un relais cloud. Chaque poste établit son propre tunnel sortant. Un changement de contrôle UU, RDP ou VNC ne possède pas cette connexion. Le terminal et les transferts conservent l’authentification SSH native.

| Donate | PayPal | Stripe |
| --- | --- | --- |
| [![Donate](https://img.shields.io/badge/Donate-LazyingArt-0EA5E9?style=for-the-badge&logo=kofi&logoColor=white)](https://chat.lazying.art/donate) | [![PayPal](https://img.shields.io/badge/PayPal-RongzhouChen-00457C?style=for-the-badge&logo=paypal&logoColor=white)](https://paypal.me/RongzhouChen) | [![Stripe](https://img.shields.io/badge/Stripe-Donate-635BFF?style=for-the-badge&logo=stripe&logoColor=white)](https://buy.stripe.com/aFadR8gIaflgfQV6T4fw400) |

## Conception

Les ports inverses écoutent uniquement sur le loopback du cloud. Les clés du tunnel, du relais et de connexion sont distinctes ; les clés des hôtes sont épinglées. Aucun VPN, conteneur, changement de route par défaut ni port de bureau public n’est nécessaire. Le projet complète LazyEdge sans contourner ses protections HTTP.

```text
alpha ── outbound SSH ── cloud loopback ── outbound SSH ── beta
```

## Démarrage rapide

L’exemple utilise des clés synthétiques et un nom d’hôte invalide : il sert à examiner les fichiers, pas à se connecter. Enrôlez chaque poste réel séparément et lisez entièrement le guide avant d’utiliser un installateur.

```bash
python3 lazytunnel.py validate --config examples/two-peers.json
python3 lazytunnel.py plan --config examples/two-peers.json
python3 -m unittest discover -s tests -v
```

## Fichiers et déploiement

Consultez l’architecture et le guide d’exploitation. L’enrôlement garde les clés privées sur leur machine d’origine. Les installateurs cloud et poste affichent un plan sauf si --apply est explicitement fourni. Les alias UU et les services de bureau existants restent inchangés.

[docs/design.md](../docs/design.md) · [docs/operations.md](../docs/operations.md) · [scripts/](../scripts/) · [tests/](../tests/)

## Accès web privé

Sur beta, accédez à un service local hébergé sur alpha par la connexion SSH existante. Exécutez les commandes suivantes, puis ouvrez `http://127.0.0.1:6144/wechat` sur beta. Le port reste privé et les services de bureau ne sont pas modifiés.

```bash
install -D -m 0755 scripts/lazy-web "$HOME/.local/bin/lazy-web"
lazy-web run alpha 6144
```

[Transferts persistants, réseau local distant, SOCKS et dépannage](../docs/private-web.md).


## Validation et état

Version initiale soumise à la revue de l’opérateur. Les tests de génération et l’accès administratif initial au cloud ont été vérifiés ; chaque déploiement exige encore des tests bidirectionnels du terminal, des fichiers, de reprise et de refus d’autorisations. L’activation au démarrage n’est pas un test de redémarrage. Systemd rétablit une connexion, pas une session perdue ; utilisez tmux distant.

## Citation

Si vous utilisez LazyTunnel, citez ce dépôt. GitHub lit CITATION.cff pour afficher son panneau de citation. [CITATION.cff](../CITATION.cff)

```bibtex
@software{chen_lazytunnel_2026,
  author = {Chen, Lachlan},
  title = {LazyTunnel: independent private SSH relays},
  year = {2026},
  url = {https://github.com/lachlanchen/LazyTunnel}
}
```
