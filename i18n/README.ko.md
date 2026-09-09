[English](../README.md) · [العربية](README.ar.md) · [Español](README.es.md) · [Français](README.fr.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Tiếng Việt](README.vi.md) · [中文 (简体)](README.zh-Hans.md) · [中文（繁體）](README.zh-Hant.md) · [Deutsch](README.de.md) · [Русский](README.ru.md)

[![LazyingArt banner](https://github.com/lachlanchen/lachlanchen/raw/main/figs/banner.png)](https://github.com/lachlanchen/lachlanchen/blob/main/figs/banner.png)

# LazyTunnel

*데스크톱 제어와 독립적인 사설 컴퓨터 간 SSH 연결.*

[Website](https://remote.lazying.art) · [GitHub Sponsors](https://github.com/sponsors/lachlanchen)

LazyTunnel은 클라우드 중계 서버를 통해 사설 컴퓨터를 연결하는 작은 OpenSSH 및 systemd 도구 모음입니다. 각 컴퓨터가 자신의 아웃바운드 터널을 시작하므로 UU, RDP, VNC의 제어권 전환이 이 연결을 소유하지 않습니다. 터미널과 파일 전송은 기본 SSH 인증을 유지합니다.

| Donate | PayPal | Stripe |
| --- | --- | --- |
| [![Donate](https://img.shields.io/badge/Donate-LazyingArt-0EA5E9?style=for-the-badge&logo=kofi&logoColor=white)](https://chat.lazying.art/donate) | [![PayPal](https://img.shields.io/badge/PayPal-RongzhouChen-00457C?style=for-the-badge&logo=paypal&logoColor=white)](https://paypal.me/RongzhouChen) | [![Stripe](https://img.shields.io/badge/Stripe-Donate-635BFF?style=for-the-badge&logo=stripe&logoColor=white)](https://buy.stripe.com/aFadR8gIaflgfQV6T4fw400) |

## 네이티브 앱과 독립적인 코어

**LazyRemote**는 이 독립 코어를 사용하는 제품입니다. [제품 웹사이트](https://remote.lazying.art) · [다운로드 및 릴리스 안내](https://github.com/lachlanchen/LazyTunnel/releases/tag/v0.2.0). 현재 네이티브 미리보기 앱 이름은 LazyTunnel이며 기존 명령과 앱 식별자는 변경되지 않습니다.

선택형 네이티브 앱은 Ubuntu, macOS, Windows, iOS, Android를 지원합니다. Flutter 관리 화면, 안전한 연결 정보 저장, 호스트 신원을 확인하는 SSH 터미널, 비공개 noVNC 및 웹 뷰어를 제공합니다. Python 에이전트와 순수 Dart 전송 라이브러리는 네이티브 GUI 및 웹 GUI와 독립적으로 동작합니다.

[설치, 연결, 빌드 및 서명 안내](../docs/native-apps.md).


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

## 비공개 웹 접속

beta에서 기존 SSH 연결을 통해 alpha의 로컬 서비스에 접속할 수 있습니다. 아래 명령을 실행한 뒤 beta에서 `http://127.0.0.1:6144/wechat`을 여세요. 수신 포트는 로컬에만 열리며 데스크톱 서비스는 변경하지 않습니다.

```bash
install -D -m 0755 scripts/lazy-web "$HOME/.local/bin/lazy-web"
lazy-web run alpha 6144
```

[상시 포워딩, 원격 LAN 대상, SOCKS 및 문제 해결](../docs/private-web.md).


## 검증과 상태

운영자 검토가 필요한 초기 버전입니다. 생성기 테스트와 클라우드 관리 접속 초기 설정을 확인했지만, 실제 배포마다 양방향 터미널, 파일 전송, 장애 복구 및 권한 거부 테스트가 필요합니다. 부팅 시 활성화는 재부팅 검증이 아닙니다. Systemd는 연결을 복구할 뿐 사라진 셸을 되살리지 않으므로 원격 tmux를 사용하세요.

## 기기 간 공통 SSH 이름

검토한 설정을 적용하는 도구는 기존 SSH 설정을 유지하며 Linux, macOS, Windows에서 동일한 비공개 기기 이름을 사용할 수 있게 합니다. 각 기기는 자체 개인 키를 보관합니다.

[기기 등록, 경로 및 롤백](../docs/device-ssh.md).


## 독립적인 서버와 클라이언트

장치 확장은 Linux, macOS, Windows를 지원하며 서버와 클라이언트를 따로 업데이트합니다. 장치 키와 비공개 설정은 Git 외부에 보관합니다. 호스트 키를 고정한 SSH 레지스트리를 통해 관리자 인증 정보 없이 장치 목록을 갱신할 수 있습니다. 실제 장치 7대에서 49개 방향의 SSH 검사를 모두 통과했으며, 재부팅 없이 시작 설정을 확인했습니다.

등록된 Linux/macOS 클라이언트에서 실행합니다.

```bash
lazytunnel status
lazytunnel devices
ssh-lazy-alpha
lazytunnel sync
lazytunnel web alpha 6144 --local-port 16144 --path /wecom
```

[설치, 장치 등록과 로그인, 업데이트, Windows 수정 및 비공개 noVNC 접속](../docs/fleet.md).


## 선택 사항인 비공개 GUI

가벼운 브라우저 콘솔에서 등록된 컴퓨터, 요청 시 수행하는 SSH 연결 확인, 저장된 noVNC 뷰어를 관리합니다. 검색, 그리드와 목록, 밝고 어두운 테마, 휴대전화 화면을 지원합니다. Linux에서는 뷰어 전달이 별도의 systemd 서비스로 실행되므로 GUI를 재시작해도 연결이 유지됩니다. 키와 접근 코드는 비공개로 보관하며 기존 데스크톱과 SSH 터널은 그대로 유지합니다.

```bash
cd /path/to/LazyTunnel
python3 scripts/lazytunnel-client.py update --source .
lazytunnel gui install
lazytunnel gui code
lazytunnel gui
```

[설치, 접근 코드 잠금 해제, 원격 브라우저와 보안 경계](../docs/gui.md).


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
