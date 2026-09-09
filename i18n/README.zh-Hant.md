[English](../README.md) · [العربية](README.ar.md) · [Español](README.es.md) · [Français](README.fr.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Tiếng Việt](README.vi.md) · [中文 (简体)](README.zh-Hans.md) · [中文（繁體）](README.zh-Hant.md) · [Deutsch](README.de.md) · [Русский](README.ru.md)

[![LazyingArt banner](https://github.com/lachlanchen/lachlanchen/raw/main/figs/banner.png)](https://github.com/lachlanchen/lachlanchen/blob/main/figs/banner.png)

# LazyTunnel

*獨立於桌面控制的私有電腦雙向 SSH。*

[Website](https://remote.lazying.art) · [GitHub Sponsors](https://github.com/sponsors/lachlanchen)

LazyTunnel 是基於 OpenSSH 和 systemd 的小型工具集，透過雲端伺服器中繼連接私有電腦。每台電腦獨立發起自己的對外隧道，因此 UU、RDP 或 VNC 的桌面接管不再擁有這條連線。終端操作與檔案傳輸仍使用原生 SSH 驗證。

| Donate | PayPal | Stripe |
| --- | --- | --- |
| [![Donate](https://img.shields.io/badge/Donate-LazyingArt-0EA5E9?style=for-the-badge&logo=kofi&logoColor=white)](https://chat.lazying.art/donate) | [![PayPal](https://img.shields.io/badge/PayPal-RongzhouChen-00457C?style=for-the-badge&logo=paypal&logoColor=white)](https://paypal.me/RongzhouChen) | [![Stripe](https://img.shields.io/badge/Stripe-Donate-635BFF?style=for-the-badge&logo=stripe&logoColor=white)](https://buy.stripe.com/aFadR8gIaflgfQV6T4fw400) |

## 原生應用，獨立核心

**LazyRemote** 是以這個獨立核心打造的產品體驗。[產品網站](https://remote.lazying.art) · [下載與發行說明](https://github.com/lachlanchen/LazyTunnel/releases/tag/v0.2.0)。目前原生預覽版仍名為 LazyTunnel，既有指令與應用程式識別碼保持不變。

可選的原生應用支援 Ubuntu、macOS、Windows、iOS 和 Android，提供真正的 Flutter 管理介面、安全儲存的連線、驗證主機身分的 SSH 終端，以及私有 noVNC 和網頁檢視器。獨立 Python 代理與純 Dart 通訊程式庫均不依賴原生 GUI 或網頁 GUI；關閉介面不會停止既有的持久隧道。

[安裝、連線、建置和簽章指南](../docs/native-apps.md).

[Apple 發布指南](../docs/apple-publication.md)：整理了從 EchoMind 學到的流程、明確的發布計畫和唯讀就緒檢查命令。iOS 預覽版尚未上傳至 TestFlight，也未提交 App Review。


## 透過 npm 安裝命令列工具

一個小型套件提供用戶端與 Linux 中繼管理命令。npm 安裝不會啟動服務，也不會變更裝置註冊、憑證或遠端桌面。原生圖形應用仍需另外下載。

```bash
npm install -g @lazyingart/lazytunnel
lazytunnel-client install
lazytunnel-client doctor
```

在 Linux 中繼伺服器上：

```bash
lazytunnel-server install
sudo lazytunnel-server install --apply
```

[完整的 npm 安裝、註冊與更新指南](../docs/npm.md)。

## 設計

反向轉送只監聽雲端 loopback。隧道、跳板與終端登入分別使用獨立金鑰，並固定驗證主機公鑰。不需要 VPN、容器、預設路由變更，也不公開桌面連接埠。它補充 LazyEdge 的使用情境，不繞過其 HTTP 安全防護。

```text
alpha ── outbound SSH ── cloud loopback ── outbound SSH ── beta
```

## 快速開始

範例使用合成測試公鑰與無效網域，只供檢查生成結果，無法建立真實連線。請在每台真實端點分別註冊，並在使用安裝程式之前完整閱讀部署手冊。

```bash
python3 lazytunnel.py validate --config examples/two-peers.json
python3 lazytunnel.py plan --config examples/two-peers.json
python3 -m unittest discover -s tests -v
```

## 檔案與部署

請閱讀架構說明與維運手冊。註冊工具只在產生金鑰的端點保存私鑰。雲端與端點安裝程式預設只列印計畫，必須明確傳入 --apply 才會實施變更。既有 UU 別名與桌面服務維持不變。

[docs/design.md](../docs/design.md) · [docs/operations.md](../docs/operations.md) · [scripts/](../scripts/) · [tests/](../tests/)

## 私有網頁存取

在 beta 上，透過既有 SSH 連線存取 alpha 的本機服務。執行以下指令，然後在 beta 的瀏覽器開啟 `http://127.0.0.1:6144/wechat`。監聽連接埠僅綁定本機回環位址，不更改遠端桌面服務。

```bash
install -D -m 0755 scripts/lazy-web "$HOME/.local/bin/lazy-web"
lazy-web run alpha 6144
```

[常駐轉送、對端區域網路、SOCKS 與疑難排解](../docs/private-web.md).


## 驗證與狀態

目前是需要維運人員審查的早期版本。組態生成測試與雲端管理員接入初始化已經檢查；每次實際部署仍須驗證雙向終端、檔案傳輸、故障復原及越權拒絕。設定開機啟用不等於通過重新啟動測試。systemd 能恢復連線，但不能恢復中斷的 shell；長任務請使用遠端 tmux。

## 跨裝置統一 SSH 名稱

經過審閱的端點設定工具保留現有 SSH 設定，在 Linux、macOS 和 Windows 上安裝相同的私有裝置名稱。每台裝置獨立保管自己的私鑰。

[裝置註冊、連線路徑與回復](../docs/device-ssh.md).


## 獨立的伺服器與用戶端

裝置群擴充功能支援 Linux、macOS 和 Windows，伺服器與用戶端可分別更新。裝置金鑰和私人設定保存在 Git 之外；用戶端透過固定主機金鑰的 SSH 設定目錄更新裝置清單，不必持有雲端管理員憑證。實際七台裝置已通過全部 49 個方向的 SSH 檢查；已檢查開機設定，但未重新啟動測試。

在已註冊的 Linux/macOS 用戶端執行：

```bash
lazytunnel status
lazytunnel devices
ssh-lazy-alpha
lazytunnel sync
lazytunnel web alpha 6144 --local-port 16144 --path /wecom
```

[安裝、裝置註冊與登入、更新、Windows 修復及私人 noVNC 存取](../docs/fleet.md).


## 可選的私有圖形介面

輕量的瀏覽器控制台集中顯示已註冊的電腦、按需 SSH 檢查與儲存的 noVNC 檢視器。支援搜尋、網格與清單、淺色與深色主題，以及手機版面。在 Linux 上，檢視器轉發由獨立的 systemd 服務管理，重新啟動 GUI 不會中斷轉發。金鑰與存取碼保存在私有位置，既有桌面和 SSH 通道保持不變。

```bash
cd /path/to/LazyTunnel
python3 scripts/lazytunnel-client.py update --source .
lazytunnel gui install
lazytunnel gui code
lazytunnel gui
```

[安裝、存取碼解鎖、遠端瀏覽器與安全邊界](../docs/gui.md).


## 引用

使用 LazyTunnel 時可引用本儲存庫。GitHub 讀取 CITATION.cff，顯示儲存庫引用資訊。 [CITATION.cff](../CITATION.cff)

```bibtex
@software{chen_lazytunnel_2026,
  author = {Chen, Lachlan},
  title = {LazyTunnel: independent private SSH relays},
  year = {2026},
  url = {https://github.com/lachlanchen/LazyTunnel}
}
```
