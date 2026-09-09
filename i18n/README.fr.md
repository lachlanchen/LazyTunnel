[English](../README.md) · [العربية](README.ar.md) · [Español](README.es.md) · [Français](README.fr.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Tiếng Việt](README.vi.md) · [中文 (简体)](README.zh-Hans.md) · [中文（繁體）](README.zh-Hant.md) · [Deutsch](README.de.md) · [Русский](README.ru.md)

[![LazyingArt banner](https://github.com/lachlanchen/lachlanchen/raw/main/figs/banner.png)](https://github.com/lachlanchen/lachlanchen/blob/main/figs/banner.png)

# LazyTunnel

*SSH entre ordinateurs privés, indépendant du contrôle du bureau.*

[Website](https://remote.lazying.art) · [GitHub Sponsors](https://github.com/sponsors/lachlanchen)

LazyTunnel est un petit ensemble d’outils OpenSSH et systemd reliant des ordinateurs privés par un relais cloud. Chaque poste établit son propre tunnel sortant. Un changement de contrôle UU, RDP ou VNC ne possède pas cette connexion. Le terminal et les transferts conservent l’authentification SSH native.

| Donate | PayPal | Stripe |
| --- | --- | --- |
| [![Donate](https://img.shields.io/badge/Donate-LazyingArt-0EA5E9?style=for-the-badge&logo=kofi&logoColor=white)](https://chat.lazying.art/donate) | [![PayPal](https://img.shields.io/badge/PayPal-RongzhouChen-00457C?style=for-the-badge&logo=paypal&logoColor=white)](https://paypal.me/RongzhouChen) | [![Stripe](https://img.shields.io/badge/Stripe-Donate-635BFF?style=for-the-badge&logo=stripe&logoColor=white)](https://buy.stripe.com/aFadR8gIaflgfQV6T4fw400) |

## Applications natives, cœur indépendant

**LazyRemote** est le produit construit autour de ce cœur indépendant. [Site du produit](https://remote.lazying.art) · [Téléchargements et notes de version](https://github.com/lachlanchen/LazyTunnel/releases/tag/v0.2.0). La version native de prévisualisation porte encore le nom LazyTunnel ; les commandes et identifiants existants restent inchangés.

L’application facultative prend en charge Ubuntu, macOS, Windows, iOS et Android : écrans Flutter natifs, connexions enregistrées de manière sécurisée, terminaux SSH avec vérification de l’identité et accès privé à noVNC et aux applications web. L’agent Python et la bibliothèque de transport Dart restent indépendants des interfaces native et web.

[Installation, connexions, compilation et signature](../docs/native-apps.md).

[Guide de publication Apple](../docs/apple-publication.md) : le processus appris d’EchoMind, un plan de publication explicite et une commande de vérification en lecture seule. La version préliminaire iOS n’a pas encore été envoyée à TestFlight ni soumise à App Review.


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

## Noms SSH entre appareils

Les outils de configuration préservent les réglages SSH existants et installent les mêmes noms privés sur Linux, macOS et Windows. Chaque appareil conserve ses propres clés privées.

[Inscription, routes et retour arrière](../docs/device-ssh.md).


## Serveur et clients indépendants

L’extension de parc prend en charge Linux, macOS et Windows, avec des mises à jour distinctes du serveur et des clients. Les clés et la configuration privée restent hors de Git ; un registre SSH à identité épinglée permet de rafraîchir la liste des appareils sans identifiants administrateur. Le déploiement réel sur sept appareils a réussi les 49 vérifications SSH dirigées ; le démarrage a été inspecté sans redémarrage.

Sur un client Linux/macOS inscrit :

```bash
lazytunnel status
lazytunnel devices
ssh-lazy-alpha
lazytunnel sync
lazytunnel web alpha 6144 --local-port 16144 --path /wecom
```

[Installation, inscription et connexion, mises à jour, correctifs Windows et accès privé noVNC](../docs/fleet.md).


## Interface privée facultative

Une console légère dans le navigateur rassemble les ordinateurs inscrits, les vérifications SSH à la demande et les visionneuses noVNC enregistrées. Elle propose une recherche, des vues en grille et en liste, deux thèmes et un affichage adapté au téléphone. Sous Linux, les redirections disposent de services systemd indépendants et survivent au redémarrage de la console. Les clés et codes restent privés ; les bureaux et tunnels SSH existants sont préservés.

```bash
cd /path/to/LazyTunnel
python3 scripts/lazytunnel-client.py update --source .
lazytunnel gui install
lazytunnel gui code
lazytunnel gui
```

[Installation, déverrouillage par code, navigateurs distants et limites de sécurité](../docs/gui.md).


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
