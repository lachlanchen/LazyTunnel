[English](../README.md) · [العربية](README.ar.md) · [Español](README.es.md) · [Français](README.fr.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Tiếng Việt](README.vi.md) · [中文 (简体)](README.zh-Hans.md) · [中文（繁體）](README.zh-Hant.md) · [Deutsch](README.de.md) · [Русский](README.ru.md)

[![LazyingArt banner](https://github.com/lachlanchen/lachlanchen/raw/main/figs/banner.png)](https://github.com/lachlanchen/lachlanchen/blob/main/figs/banner.png)

# LazyTunnel

*独立于桌面控制的私有电脑双向 SSH。*

[Website](https://lazying.art) · [GitHub Sponsors](https://github.com/sponsors/lachlanchen)

LazyTunnel 是一个基于 OpenSSH 和 systemd 的小型工具集，通过云服务器中转连接私有电脑。每台电脑独立发起自己的出站隧道，因此 UU、RDP 或 VNC 的桌面接管不再拥有这条连接。终端和文件传输仍使用原生 SSH 认证。

| Donate | PayPal | Stripe |
| --- | --- | --- |
| [![Donate](https://img.shields.io/badge/Donate-LazyingArt-0EA5E9?style=for-the-badge&logo=kofi&logoColor=white)](https://chat.lazying.art/donate) | [![PayPal](https://img.shields.io/badge/PayPal-RongzhouChen-00457C?style=for-the-badge&logo=paypal&logoColor=white)](https://paypal.me/RongzhouChen) | [![Stripe](https://img.shields.io/badge/Stripe-Donate-635BFF?style=for-the-badge&logo=stripe&logoColor=white)](https://buy.stripe.com/aFadR8gIaflgfQV6T4fw400) |

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

## 验证与状态

当前是需要运维人员审查的早期版本。配置生成测试和云端管理员接入初始化已经检查；每次实际部署仍需验证双向终端、文件传输、故障恢复及越权拒绝。配置开机启用不等于通过重启测试。systemd 能恢复连接，但不能恢复已断开的 shell；长任务请使用远程 tmux。

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
