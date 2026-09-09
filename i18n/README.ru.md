[English](../README.md) · [العربية](README.ar.md) · [Español](README.es.md) · [Français](README.fr.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Tiếng Việt](README.vi.md) · [中文 (简体)](README.zh-Hans.md) · [中文（繁體）](README.zh-Hant.md) · [Deutsch](README.de.md) · [Русский](README.ru.md)

[![LazyingArt banner](https://github.com/lachlanchen/lachlanchen/raw/main/figs/banner.png)](https://github.com/lachlanchen/lachlanchen/blob/main/figs/banner.png)

# LazyTunnel

*SSH между частными компьютерами независимо от управления рабочим столом.*

[Website](https://remote.lazying.art) · [GitHub Sponsors](https://github.com/sponsors/lachlanchen)

LazyTunnel — небольшой набор инструментов OpenSSH и systemd для связи частных компьютеров через облачный ретранслятор. Каждый узел сам открывает исходящий туннель. Переключение управления через UU, RDP или VNC не владеет этим соединением. Терминал и передача файлов сохраняют обычную аутентификацию SSH.

| Donate | PayPal | Stripe |
| --- | --- | --- |
| [![Donate](https://img.shields.io/badge/Donate-LazyingArt-0EA5E9?style=for-the-badge&logo=kofi&logoColor=white)](https://chat.lazying.art/donate) | [![PayPal](https://img.shields.io/badge/PayPal-RongzhouChen-00457C?style=for-the-badge&logo=paypal&logoColor=white)](https://paypal.me/RongzhouChen) | [![Stripe](https://img.shields.io/badge/Stripe-Donate-635BFF?style=for-the-badge&logo=stripe&logoColor=white)](https://buy.stripe.com/aFadR8gIaflgfQV6T4fw400) |

## Нативные приложения и независимое ядро

**LazyRemote** — продукт на основе этого независимого ядра. [Сайт продукта](https://remote.lazying.art) · [Загрузки и примечания к выпуску](https://github.com/lachlanchen/LazyTunnel/releases/tag/v0.2.0). Текущая нативная предварительная версия называется LazyTunnel; существующие команды и идентификаторы приложений не меняются.

Необязательное приложение поддерживает Ubuntu, macOS, Windows, iOS и Android: нативные экраны Flutter, безопасное хранение подключений, SSH-терминалы с проверкой ключа сервера и приватный просмотр noVNC и веб-приложений. Агент Python и транспортная библиотека Dart не зависят ни от нативного, ни от браузерного интерфейса.

[Установка, подключения, сборка и подпись](../docs/native-apps.md).


## Устройство

Обратные порты слушают только loopback облачного сервера. Ключи туннеля, промежуточного подключения и входа разделены; ключи хостов закреплены. Не нужны VPN, контейнер, изменение маршрута по умолчанию или публичный порт рабочего стола. Проект дополняет LazyEdge, не обходя его HTTP-защиту.

```text
alpha ── outbound SSH ── cloud loopback ── outbound SSH ── beta
```

## Быстрый старт

Пример содержит синтетические тестовые ключи и недействительное имя хоста: он предназначен для проверки результата, а не для подключения. Регистрируйте реальные узлы отдельно и прочитайте полное руководство до запуска установщика.

```bash
python3 lazytunnel.py validate --config examples/two-peers.json
python3 lazytunnel.py plan --config examples/two-peers.json
python3 -m unittest discover -s tests -v
```

## Файлы и развёртывание

Прочитайте описание архитектуры и руководство оператора. Регистрация сохраняет закрытые ключи на исходном узле. Установщики сервера и узлов выводят только план, если явно не указан --apply. Существующие псевдонимы UU и службы рабочего стола остаются без изменений.

[docs/design.md](../docs/design.md) · [docs/operations.md](../docs/operations.md) · [scripts/](../scripts/) · [tests/](../tests/)

## Приватный доступ к веб-сервисам

На beta можно открыть локальный сервис alpha через существующее SSH-соединение. Выполните команды ниже и откройте `http://127.0.0.1:6144/wechat` в браузере beta. Порт доступен только через loopback; службы рабочего стола не изменяются.

```bash
install -D -m 0755 scripts/lazy-web "$HOME/.local/bin/lazy-web"
lazy-web run alpha 6144
```

[Постоянные туннели, удалённая локальная сеть, SOCKS и диагностика](../docs/private-web.md).


## Проверка и состояние

Ранний выпуск, требующий проверки оператором. Проверены тесты генератора и начальный административный доступ к облаку; каждое реальное развёртывание всё ещё требует двусторонних тестов оболочки, файлов, восстановления и отказа запрещённым действиям. Включение автозапуска не является проверкой перезагрузки. Systemd восстанавливает соединение, но не потерянную оболочку; используйте удалённый tmux.

## Единые SSH-имена устройств

Инструменты установки проверенных конфигураций сохраняют существующие настройки SSH и добавляют одинаковые частные имена устройств в Linux, macOS и Windows. Закрытые ключи остаются на своих устройствах.

[Регистрация устройств, маршруты и откат](../docs/device-ssh.md).


## Независимые сервер и клиенты

Расширение для группы устройств поддерживает Linux, macOS и Windows с отдельным обновлением сервера и клиентов. Ключи устройств и закрытые настройки хранятся вне Git. Реестр SSH с закреплённым ключом сервера позволяет обновлять список устройств без учётных данных администратора. В реальном развёртывании на семи устройствах успешно выполнены все 49 направленных проверок SSH; настройки запуска проверены без перезагрузки.

На зарегистрированном клиенте Linux/macOS:

```bash
lazytunnel status
lazytunnel devices
ssh-lazy-alpha
lazytunnel sync
lazytunnel web alpha 6144 --local-port 16144 --path /wecom
```

[Установка, регистрация и вход, обновления, исправления Windows и закрытый доступ noVNC](../docs/fleet.md).


## Необязательный приватный интерфейс

Лёгкая браузерная консоль объединяет зарегистрированные компьютеры, проверки SSH по запросу и сохранённые подключения noVNC. Есть поиск, сетка и список, светлая и тёмная темы, а также мобильная компоновка. В Linux перенаправления работают как отдельные службы systemd и сохраняются при перезапуске интерфейса. Ключи и коды доступа остаются приватными; существующие рабочие столы и SSH-туннели не изменяются.

```bash
cd /path/to/LazyTunnel
python3 scripts/lazytunnel-client.py update --source .
lazytunnel gui install
lazytunnel gui code
lazytunnel gui
```

[Установка, разблокировка кодом, удалённые браузеры и границы безопасности](../docs/gui.md).


## Цитирование

При использовании LazyTunnel ссылайтесь на этот репозиторий. GitHub читает CITATION.cff для отображения сведений о цитировании. [CITATION.cff](../CITATION.cff)

```bibtex
@software{chen_lazytunnel_2026,
  author = {Chen, Lachlan},
  title = {LazyTunnel: independent private SSH relays},
  year = {2026},
  url = {https://github.com/lachlanchen/LazyTunnel}
}
```
