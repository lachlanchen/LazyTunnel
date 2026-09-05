[English](../README.md) · [العربية](README.ar.md) · [Español](README.es.md) · [Français](README.fr.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Tiếng Việt](README.vi.md) · [中文 (简体)](README.zh-Hans.md) · [中文（繁體）](README.zh-Hant.md) · [Deutsch](README.de.md) · [Русский](README.ru.md)

[![LazyingArt banner](https://github.com/lachlanchen/lachlanchen/raw/main/figs/banner.png)](https://github.com/lachlanchen/lachlanchen/blob/main/figs/banner.png)

# LazyTunnel

*데스크톱 제어와 독립적인 사설 컴퓨터 간 SSH 연결.*

[Website](https://lazying.art) · [GitHub Sponsors](https://github.com/sponsors/lachlanchen)

LazyTunnel은 클라우드 중계 서버를 통해 사설 컴퓨터를 연결하는 작은 OpenSSH 및 systemd 도구 모음입니다. 각 컴퓨터가 자신의 아웃바운드 터널을 시작하므로 UU, RDP, VNC의 제어권 전환이 이 연결을 소유하지 않습니다. 터미널과 파일 전송은 기본 SSH 인증을 유지합니다.

| Donate | PayPal | Stripe |
| --- | --- | --- |
| [![Donate](https://img.shields.io/badge/Donate-LazyingArt-0EA5E9?style=for-the-badge&logo=kofi&logoColor=white)](https://chat.lazying.art/donate) | [![PayPal](https://img.shields.io/badge/PayPal-RongzhouChen-00457C?style=for-the-badge&logo=paypal&logoColor=white)](https://paypal.me/RongzhouChen) | [![Stripe](https://img.shields.io/badge/Stripe-Donate-635BFF?style=for-the-badge&logo=stripe&logoColor=white)](https://buy.stripe.com/aFadR8gIaflgfQV6T4fw400) |

## 설계

역방향 포트는 클라우드의 루프백에서만 수신합니다. 터널, 점프, 로그인 역할의 키를 분리하고 호스트 키를 고정합니다. VPN, 컨테이너, 기본 경로 변경이나 공개 데스크톱 포트가 필요하지 않습니다. LazyEdge를 보완하며 HTTP 보호 계층을 우회하지 않습니다.

```text
alpha ── outbound SSH ── cloud loopback ── outbound SSH ── beta
```

## 빠른 시작

예제는 합성 테스트 키와 유효하지 않은 호스트명을 포함하므로 실제 연결 대신 생성 결과를 검토하는 데 사용하세요. 실제 컴퓨터는 각각 등록하고 설치 도구를 실행하기 전에 전체 배포 지침을 검토하세요.

```bash
python3 lazytunnel.py validate --config examples/two-peers.json
python3 lazytunnel.py plan --config examples/two-peers.json
python3 -m unittest discover -s tests -v
```

## 파일과 배포

구조 설명과 운영 지침을 읽어 주세요. 등록 도구는 개인 키를 생성한 컴퓨터에 보관합니다. 클라우드와 클라이언트 설치 도구는 --apply를 명시하지 않으면 계획만 표시합니다. 기존 UU 별칭과 데스크톱 서비스는 변경하지 않습니다.

[docs/design.md](../docs/design.md) · [docs/operations.md](../docs/operations.md) · [scripts/](../scripts/) · [tests/](../tests/)

## 검증과 상태

운영자 검토가 필요한 초기 버전입니다. 생성기 테스트와 클라우드 관리 접속 초기 설정을 확인했지만, 실제 배포마다 양방향 터미널, 파일 전송, 장애 복구 및 권한 거부 테스트가 필요합니다. 부팅 시 활성화는 재부팅 검증이 아닙니다. Systemd는 연결을 복구할 뿐 사라진 셸을 되살리지 않으므로 원격 tmux를 사용하세요.

## 인용

LazyTunnel을 사용한다면 이 저장소를 인용해 주세요. GitHub는 CITATION.cff를 읽어 인용 정보를 표시합니다. [CITATION.cff](../CITATION.cff)

```bibtex
@software{chen_lazytunnel_2026,
  author = {Chen, Lachlan},
  title = {LazyTunnel: independent private SSH relays},
  year = {2026},
  url = {https://github.com/lachlanchen/LazyTunnel}
}
```
