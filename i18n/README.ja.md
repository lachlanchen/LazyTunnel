[English](../README.md) · [العربية](README.ar.md) · [Español](README.es.md) · [Français](README.fr.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Tiếng Việt](README.vi.md) · [中文 (简体)](README.zh-Hans.md) · [中文（繁體）](README.zh-Hant.md) · [Deutsch](README.de.md) · [Русский](README.ru.md)

[![LazyingArt banner](https://github.com/lachlanchen/lachlanchen/raw/main/figs/banner.png)](https://github.com/lachlanchen/lachlanchen/blob/main/figs/banner.png)

# LazyTunnel

*デスクトップ操作から独立した、プライベート端末間の SSH 接続。*

[Website](https://lazying.art) · [GitHub Sponsors](https://github.com/sponsors/lachlanchen)

LazyTunnel は、クラウド中継サーバー経由でプライベートな端末同士を接続する、小さな OpenSSH・systemd ツール集です。各端末が独自の外向きトンネルを開始するため、UU・RDP・VNC の操作先切り替えに接続の所有権が左右されません。シェル操作とファイル転送には通常の SSH 認証を使います。

| Donate | PayPal | Stripe |
| --- | --- | --- |
| [![Donate](https://img.shields.io/badge/Donate-LazyingArt-0EA5E9?style=for-the-badge&logo=kofi&logoColor=white)](https://chat.lazying.art/donate) | [![PayPal](https://img.shields.io/badge/PayPal-RongzhouChen-00457C?style=for-the-badge&logo=paypal&logoColor=white)](https://paypal.me/RongzhouChen) | [![Stripe](https://img.shields.io/badge/Stripe-Donate-635BFF?style=for-the-badge&logo=stripe&logoColor=white)](https://buy.stripe.com/aFadR8gIaflgfQV6T4fw400) |

## 設計

逆向き転送の待受先はクラウドのループバックだけです。トンネル用・踏み台用・ログイン用の鍵を分離し、ホスト鍵を固定します。VPN、コンテナ、デフォルト経路変更、デスクトップ用ポートの公開は不要です。LazyEdge を補完する仕組みであり、その HTTP 保護を迂回しません。

```text
alpha ── outbound SSH ── cloud loopback ── outbound SSH ── beta
```

## クイックスタート

サンプルには合成したテスト鍵と無効なホスト名が含まれます。接続せず、生成内容の確認に使ってください。実際の端末はそれぞれ個別に登録し、インストーラーを使う前に導入手順全体を確認します。

```bash
python3 lazytunnel.py validate --config examples/two-peers.json
python3 lazytunnel.py plan --config examples/two-peers.json
python3 -m unittest discover -s tests -v
```

## ファイルと導入

構成説明と運用手順を参照してください。登録ヘルパーは秘密鍵を生成元の端末に保持します。クラウド側・端末側のインストーラーは、--apply を明示しない限り計画の表示だけを行います。既存の UU エイリアスとデスクトップサービスは変更しません。

[docs/design.md](../docs/design.md) · [docs/operations.md](../docs/operations.md) · [scripts/](../scripts/) · [tests/](../tests/)

## プライベートな Web アクセス

beta から、既存の SSH 接続で alpha のローカルサービスを開けます。以下を実行し、beta のブラウザーで `http://127.0.0.1:6144/wechat` を開いてください。待受先はループバックのみで、デスクトップサービスは変更しません。

```bash
install -D -m 0755 scripts/lazy-web "$HOME/.local/bin/lazy-web"
lazy-web run alpha 6144
```

[常駐転送・相手側 LAN・SOCKS・トラブルシューティング](../docs/private-web.md).


## 検証と状態

運用者のレビューを前提とした初期版です。生成器のテストとクラウド管理アクセスの初期設定は確認済みですが、実際の導入ごとに双方向シェル、ファイル転送、障害復旧、権限制限の拒否テストが必要です。起動時の有効化は再起動試験の証拠ではありません。systemd が復旧するのは接続であり失われたシェルではないため、長い作業にはリモート tmux を使います。

## デバイス間で共通のSSH名

確認済みの設定を適用する補助ツールは、既存のSSH設定を維持し、Linux・macOS・Windowsで共通のプライベート接続名を使えるようにします。秘密鍵は各デバイスに保持します。

[デバイス登録・経路・ロールバック](../docs/device-ssh.md).


## 独立したサーバーとクライアント

端末群の拡張機能は Linux、macOS、Windows に対応し、サーバーとクライアントを個別に更新できます。端末の鍵と非公開設定は Git の外に保存し、ホスト鍵を固定した SSH レジストリから管理者認証情報なしで端末一覧を更新します。実際の7台構成では全49方向の SSH 検査に成功しました。起動設定は確認済みですが、再起動試験は行っていません。

登録済みの Linux/macOS クライアントで実行します。

```bash
lazytunnel status
lazytunnel devices
ssh-lazy-alpha
lazytunnel sync
lazytunnel web alpha 6144 --local-port 16144 --path /wecom
```

[インストール、端末登録とログイン、更新、Windows 対策、非公開 noVNC 接続](../docs/fleet.md).


## 任意のプライベートGUI

軽量なブラウザーコンソールで、登録済みコンピューター、手動のSSH接続確認、保存したnoVNCビューアーをまとめて管理できます。検索、グリッドとリスト、ライトとダークのテーマ、スマートフォン向け表示に対応しています。Linuxでは転送が独立したsystemdサービスとして動作し、GUIを再起動しても継続します。鍵とアクセスコードは非公開のまま、既存のデスクトップとSSHトンネルも維持されます。

```bash
cd /path/to/LazyTunnel
python3 scripts/lazytunnel-client.py update --source .
lazytunnel gui install
lazytunnel gui code
lazytunnel gui
```

[インストール、コードによるロック解除、リモートブラウザーとセキュリティ境界](../docs/gui.md).


## 引用

LazyTunnel を利用する場合は、このリポジトリを引用してください。GitHub は CITATION.cff から引用情報を表示します。 [CITATION.cff](../CITATION.cff)

```bibtex
@software{chen_lazytunnel_2026,
  author = {Chen, Lachlan},
  title = {LazyTunnel: independent private SSH relays},
  year = {2026},
  url = {https://github.com/lachlanchen/LazyTunnel}
}
```
