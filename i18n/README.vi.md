[English](../README.md) · [العربية](README.ar.md) · [Español](README.es.md) · [Français](README.fr.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Tiếng Việt](README.vi.md) · [中文 (简体)](README.zh-Hans.md) · [中文（繁體）](README.zh-Hant.md) · [Deutsch](README.de.md) · [Русский](README.ru.md)

[![LazyingArt banner](https://github.com/lachlanchen/lachlanchen/raw/main/figs/banner.png)](https://github.com/lachlanchen/lachlanchen/blob/main/figs/banner.png)

# LazyTunnel

*SSH giữa các máy riêng, độc lập với quyền điều khiển màn hình.*

[Website](https://lazying.art) · [GitHub Sponsors](https://github.com/sponsors/lachlanchen)

LazyTunnel là bộ công cụ nhỏ dùng OpenSSH và systemd để nối các máy riêng qua máy chủ chuyển tiếp đám mây. Mỗi máy tự mở đường hầm đi ra. Việc chuyển quyền điều khiển UU, RDP hay VNC không sở hữu kết nối này. Terminal và truyền tệp vẫn dùng xác thực SSH gốc.

| Donate | PayPal | Stripe |
| --- | --- | --- |
| [![Donate](https://img.shields.io/badge/Donate-LazyingArt-0EA5E9?style=for-the-badge&logo=kofi&logoColor=white)](https://chat.lazying.art/donate) | [![PayPal](https://img.shields.io/badge/PayPal-RongzhouChen-00457C?style=for-the-badge&logo=paypal&logoColor=white)](https://paypal.me/RongzhouChen) | [![Stripe](https://img.shields.io/badge/Stripe-Donate-635BFF?style=for-the-badge&logo=stripe&logoColor=white)](https://buy.stripe.com/aFadR8gIaflgfQV6T4fw400) |

## Thiết kế

Các cổng chuyển tiếp ngược chỉ lắng nghe trên loopback của máy chủ. Khóa đường hầm, khóa bước nhảy và khóa đăng nhập được tách riêng; khóa máy chủ được ghim. Không cần VPN, container, đổi tuyến mặc định hay công khai cổng màn hình. Công cụ bổ sung cho LazyEdge chứ không bỏ qua lớp bảo vệ HTTP.

```text
alpha ── outbound SSH ── cloud loopback ── outbound SSH ── beta
```

## Bắt đầu nhanh

Ví dụ dùng khóa thử nghiệm tổng hợp và tên máy không hợp lệ: chỉ dùng để kiểm tra đầu ra, không để kết nối. Đăng ký từng máy thật độc lập và đọc toàn bộ hướng dẫn trước khi dùng trình cài đặt.

```bash
python3 lazytunnel.py validate --config examples/two-peers.json
python3 lazytunnel.py plan --config examples/two-peers.json
python3 -m unittest discover -s tests -v
```

## Tệp và triển khai

Đọc tài liệu kiến trúc và vận hành. Công cụ đăng ký giữ khóa riêng trên máy tạo ra chúng. Trình cài đặt phía đám mây và máy trạm chỉ hiển thị kế hoạch nếu chưa chỉ rõ --apply. Các bí danh UU và dịch vụ màn hình hiện có không thay đổi.

[docs/design.md](../docs/design.md) · [docs/operations.md](../docs/operations.md) · [scripts/](../scripts/) · [tests/](../tests/)

## Kiểm tra và trạng thái

Bản đầu cần người vận hành rà soát. Kiểm thử bộ tạo cấu hình và truy cập quản trị đám mây ban đầu đã được kiểm tra; mỗi lần triển khai vẫn cần thử terminal, truyền tệp hai chiều, phục hồi và từ chối quyền sai. Bật tự khởi động không có nghĩa đã thử khởi động lại. Systemd phục hồi kết nối, không phục hồi phiên shell đã mất; hãy dùng tmux từ xa.

## Trích dẫn

Nếu dùng LazyTunnel, hãy trích dẫn kho này. GitHub đọc CITATION.cff để hiển thị bảng trích dẫn. [CITATION.cff](../CITATION.cff)

```bibtex
@software{chen_lazytunnel_2026,
  author = {Chen, Lachlan},
  title = {LazyTunnel: independent private SSH relays},
  year = {2026},
  url = {https://github.com/lachlanchen/LazyTunnel}
}
```
