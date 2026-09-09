[English](../README.md) · [العربية](README.ar.md) · [Español](README.es.md) · [Français](README.fr.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Tiếng Việt](README.vi.md) · [中文 (简体)](README.zh-Hans.md) · [中文（繁體）](README.zh-Hant.md) · [Deutsch](README.de.md) · [Русский](README.ru.md)

[![LazyingArt banner](https://github.com/lachlanchen/lachlanchen/raw/main/figs/banner.png)](https://github.com/lachlanchen/lachlanchen/blob/main/figs/banner.png)

# LazyTunnel

*独立于桌面控制的私有电脑双向 SSH。*

[Website](https://remote.lazying.art) · [GitHub Sponsors](https://github.com/sponsors/lachlanchen)

LazyTunnel 是一个基于 OpenSSH 和 systemd 的小型工具集，通过云服务器中转连接私有电脑。每台电脑独立发起自己的出站隧道，因此 UU、RDP 或 VNC 的桌面接管不再拥有这条连接。终端和文件传输仍使用原生 SSH 认证。

| Donate | PayPal | Stripe |
| --- | --- | --- |
| [![Donate](https://img.shields.io/badge/Donate-LazyingArt-0EA5E9?style=for-the-badge&logo=kofi&logoColor=white)](https://chat.lazying.art/donate) | [![PayPal](https://img.shields.io/badge/PayPal-RongzhouChen-00457C?style=for-the-badge&logo=paypal&logoColor=white)](https://paypal.me/RongzhouChen) | [![Stripe](https://img.shields.io/badge/Stripe-Donate-635BFF?style=for-the-badge&logo=stripe&logoColor=white)](https://buy.stripe.com/aFadR8gIaflgfQV6T4fw400) |

## 原生应用，独立核心

**LazyRemote** 是基于这一独立核心打造的产品体验。[产品网站](https://remote.lazying.art) · [下载与发行说明](https://github.com/lachlanchen/LazyTunnel/releases/tag/v0.2.0)。当前原生预览版仍名为 LazyTunnel，既有命令和应用标识保持不变。

可选的原生应用支持 Ubuntu、macOS、Windows、iOS 和 Android，提供真正的 Flutter 管理界面、安全保存的连接、验证主机身份的 SSH 终端，以及私有 noVNC 和网页查看器。独立 Python 代理与纯 Dart 通信库均不依赖原生 GUI 或网页 GUI；关闭界面不会停止现有的持久隧道。

[安装、连接、构建和签名指南](../docs/native-apps.md).


## 设计

反向转发仅监听云端 loopback。隧道、跳板、终端登录分别使用独立密钥，并固定验证主机公钥。无需 VPN、容器、默认路由变更，也不公开桌面端口。它补充 LazyEdge 的使用场景，不绕过其 HTTP 安全防护。

```text
alpha ── outbound SSH ── cloud loopback ── outbound SSH ── beta
```

## 快速开始

示例使用合成测试公钥和无效域名，仅用于检查生成结果，无法建立真实连接。请在每台真实端点上分别注册，并在使用安装器之前完整阅读部署手册。

```bash
python3 lazytunnel.py validate --config examples/two-peers.json
python3 lazytunnel.py plan --config examples/two-peers.json
python3 -m unittest discover -s tests -v
```

## 文件与部署

请阅读架构说明和运维手册。注册工具只在生成密钥的端点保存私钥。云端和端点安装器默认仅打印计划，必须明确传入 --apply 才会实施变更。已有 UU 别名和桌面服务保持不变。

[docs/design.md](../docs/design.md) · [docs/operations.md](../docs/operations.md) · [scripts/](../scripts/) · [tests/](../tests/)

## 私有网页访问

在 beta 上，通过已有 SSH 连接访问 alpha 的本地服务。运行以下命令，然后在 beta 的浏览器打开 `http://127.0.0.1:6144/wechat`。监听端口仅绑定本机回环地址，不更改远程桌面服务。

```bash
install -D -m 0755 scripts/lazy-web "$HOME/.local/bin/lazy-web"
lazy-web run alpha 6144
```

[常驻转发、对端局域网、SOCKS 与故障排查](../docs/private-web.md).


## 验证与状态

当前是需要运维人员审查的早期版本。配置生成测试和云端管理员接入初始化已经检查；每次实际部署仍需验证双向终端、文件传输、故障恢复及越权拒绝。配置开机启用不等于通过重启测试。systemd 能恢复连接，但不能恢复已断开的 shell；长任务请使用远程 tmux。

## 跨设备统一 SSH 名称

经过审阅的端点配置工具保留现有 SSH 设置，在 Linux、macOS 和 Windows 上安装相同的私有设备名称。每台设备独立保管自己的私钥。

[设备注册、连接路径与回滚](../docs/device-ssh.md).


## 独立的服务端与客户端

设备群扩展支持 Linux、macOS 和 Windows，服务端与客户端可分别更新。设备密钥和私有配置保存在 Git 之外；客户端通过固定主机密钥的 SSH 配置目录刷新设备列表，无需持有云端管理员凭据。实际七台设备已通过全部 49 个方向的 SSH 检查；已检查开机设置，但未重启测试。

在已注册的 Linux/macOS 客户端运行：

```bash
lazytunnel status
lazytunnel devices
ssh-lazy-alpha
lazytunnel sync
lazytunnel web alpha 6144 --local-port 16144 --path /wecom
```

[安装、设备注册与登录、更新、Windows 修复及私有 noVNC 访问](../docs/fleet.md).


## 可选的私有图形界面

轻量的浏览器控制台集中显示已注册的电脑、按需 SSH 检查和保存的 noVNC 查看器。支持搜索、网格和列表、浅色与深色主题，以及手机布局。在 Linux 上，查看器转发由独立的 systemd 服务管理，重启 GUI 不会中断转发。密钥和访问码保存在私有位置，已有桌面和 SSH 隧道保持不变。

```bash
cd /path/to/LazyTunnel
python3 scripts/lazytunnel-client.py update --source .
lazytunnel gui install
lazytunnel gui code
lazytunnel gui
```

[安装、访问码解锁、远程浏览器和安全边界](../docs/gui.md).


## 引用

使用 LazyTunnel 时可引用本仓库。GitHub 读取 CITATION.cff，显示仓库引用信息。 [CITATION.cff](../CITATION.cff)

```bibtex
@software{chen_lazytunnel_2026,
  author = {Chen, Lachlan},
  title = {LazyTunnel: independent private SSH relays},
  year = {2026},
  url = {https://github.com/lachlanchen/LazyTunnel}
}
```
