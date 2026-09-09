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

## Truy cập web riêng tư

Trên beta, mở dịch vụ cục bộ chạy trên alpha qua kết nối SSH hiện có. Chạy các lệnh dưới đây rồi mở `http://127.0.0.1:6144/wechat` trên beta. Cổng chỉ lắng nghe trên loopback và không thay đổi dịch vụ màn hình từ xa.

```bash
install -D -m 0755 scripts/lazy-web "$HOME/.local/bin/lazy-web"
lazy-web run alpha 6144
```

[Chuyển tiếp thường trực, thiết bị LAN từ xa, SOCKS và xử lý sự cố](../docs/private-web.md).


## Kiểm tra và trạng thái

Bản đầu cần người vận hành rà soát. Kiểm thử bộ tạo cấu hình và truy cập quản trị đám mây ban đầu đã được kiểm tra; mỗi lần triển khai vẫn cần thử terminal, truyền tệp hai chiều, phục hồi và từ chối quyền sai. Bật tự khởi động không có nghĩa đã thử khởi động lại. Systemd phục hồi kết nối, không phục hồi phiên shell đã mất; hãy dùng tmux từ xa.

## Tên SSH dùng chung giữa các thiết bị

Các công cụ áp dụng cấu hình đã được xem xét giữ nguyên thiết lập SSH hiện có và cài cùng tên thiết bị riêng trên Linux, macOS và Windows. Mỗi thiết bị giữ khóa riêng của mình.

[Đăng ký thiết bị, định tuyến và hoàn tác](../docs/device-ssh.md).


## Máy chủ và máy khách độc lập

Phần mở rộng đội thiết bị hỗ trợ Linux, macOS và Windows, với bản cập nhật máy chủ và máy khách tách biệt. Khóa thiết bị và cấu hình riêng được giữ ngoài Git; danh bạ SSH có khóa máy chủ được ghim cho phép cập nhật danh sách thiết bị mà không cần thông tin xác thực quản trị viên. Triển khai thực tế trên bảy thiết bị đã vượt qua cả 49 phép kiểm tra SSH có hướng; cấu hình khởi động được kiểm tra mà không khởi động lại.

Trên máy khách Linux/macOS đã đăng ký:

```bash
lazytunnel status
lazytunnel devices
ssh-lazy-alpha
lazytunnel sync
lazytunnel web alpha 6144 --local-port 16144 --path /wecom
```

[Cài đặt, đăng ký và đăng nhập, cập nhật, sửa lỗi Windows và truy cập noVNC riêng](../docs/fleet.md).


## GUI riêng tư tùy chọn

Bảng điều khiển trình duyệt gọn nhẹ tập hợp các máy đã đăng ký, kiểm tra SSH theo yêu cầu và trình xem noVNC đã lưu. Giao diện có tìm kiếm, dạng lưới và danh sách, nền sáng và tối, cùng bố cục cho điện thoại. Trên Linux, các kết nối chuyển tiếp chạy bằng dịch vụ systemd riêng và tiếp tục khi GUI khởi động lại. Khóa và mã truy cập vẫn được giữ riêng; máy tính để bàn và đường hầm SSH hiện tại được bảo toàn.

```bash
cd /path/to/LazyTunnel
python3 scripts/lazytunnel-client.py update --source .
lazytunnel gui install
lazytunnel gui code
lazytunnel gui
```

[Cài đặt, mở khóa bằng mã, trình duyệt từ xa và giới hạn bảo mật](../docs/gui.md).


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
