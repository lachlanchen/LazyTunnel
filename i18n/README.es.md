[English](../README.md) · [العربية](README.ar.md) · [Español](README.es.md) · [Français](README.fr.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Tiếng Việt](README.vi.md) · [中文 (简体)](README.zh-Hans.md) · [中文（繁體）](README.zh-Hant.md) · [Deutsch](README.de.md) · [Русский](README.ru.md)

[![LazyingArt banner](https://github.com/lachlanchen/lachlanchen/raw/main/figs/banner.png)](https://github.com/lachlanchen/lachlanchen/blob/main/figs/banner.png)

# LazyTunnel

*SSH entre equipos privados, independiente del control del escritorio.*

[Website](https://remote.lazying.art) · [GitHub Sponsors](https://github.com/sponsors/lachlanchen)

LazyTunnel es un conjunto pequeño de herramientas OpenSSH y systemd para conectar equipos privados mediante un servidor en la nube. Cada equipo inicia su propio túnel. Cambiar el control mediante UU, RDP o VNC no controla esa conexión. La terminal y las transferencias mantienen la autenticación SSH nativa.

| Donate | PayPal | Stripe |
| --- | --- | --- |
| [![Donate](https://img.shields.io/badge/Donate-LazyingArt-0EA5E9?style=for-the-badge&logo=kofi&logoColor=white)](https://chat.lazying.art/donate) | [![PayPal](https://img.shields.io/badge/PayPal-RongzhouChen-00457C?style=for-the-badge&logo=paypal&logoColor=white)](https://paypal.me/RongzhouChen) | [![Stripe](https://img.shields.io/badge/Stripe-Donate-635BFF?style=for-the-badge&logo=stripe&logoColor=white)](https://buy.stripe.com/aFadR8gIaflgfQV6T4fw400) |

## Aplicaciones nativas, núcleo independiente

**LazyRemote** es la experiencia de producto sobre este núcleo independiente. [Sitio del producto](https://remote.lazying.art) · [Descargas y notas de versión](https://github.com/lachlanchen/LazyTunnel/releases/tag/v0.2.0). La vista previa nativa actual se llama LazyTunnel; los comandos e identificadores existentes no cambian.

La aplicación opcional funciona en Ubuntu, macOS, Windows, iOS y Android, con pantallas Flutter nativas, conexiones guardadas de forma segura, terminales SSH con identidad verificada y visores privados de noVNC y aplicaciones web. El agente Python y la biblioteca de transporte Dart son independientes de las interfaces nativa y web.

[Instalación, conexiones, compilación y firma](../docs/native-apps.md).

[Guía de publicación en Apple](../docs/apple-publication.md): el proceso aprendido de EchoMind, un plan de lanzamiento explícito y un comando de comprobación de solo lectura. La versión preliminar de iOS todavía no se ha subido a TestFlight ni enviado a App Review.


## Diseño

Los puertos inversos escuchan únicamente en loopback del servidor. Las claves de túnel, salto e inicio de sesión están separadas y se fijan las claves de los hosts. No requiere VPN, contenedores, cambios de ruta predeterminada ni puertos de escritorio públicos. Complementa LazyEdge sin eludir sus protecciones HTTP.

```text
alpha ── outbound SSH ── cloud loopback ── outbound SSH ── beta
```

## Inicio rápido

El ejemplo contiene claves sintéticas y un hostname inválido: sirve para inspeccionar resultados, no para conectarse. Registra cada equipo real de forma independiente y revisa la guía completa antes de ejecutar un instalador.

```bash
python3 lazytunnel.py validate --config examples/two-peers.json
python3 lazytunnel.py plan --config examples/two-peers.json
python3 -m unittest discover -s tests -v
```

## Archivos y despliegue

Consulta la arquitectura y el manual operativo. El registro conserva las claves privadas en el equipo que las genera. Los instaladores del servidor y los clientes muestran un plan salvo que se indique --apply explícitamente. Los alias UU y los servicios de escritorio existentes no cambian.

[docs/design.md](../docs/design.md) · [docs/operations.md](../docs/operations.md) · [scripts/](../scripts/) · [tests/](../tests/)

## Acceso web privado

En beta, abre un servicio local alojado en alpha mediante la conexión SSH existente. Ejecuta estos comandos y abre `http://127.0.0.1:6144/wechat` en beta. El puerto de escucha sigue siendo privado y no se modifican los servicios de escritorio.

```bash
install -D -m 0755 scripts/lazy-web "$HOME/.local/bin/lazy-web"
lazy-web run alpha 6144
```

[Túneles persistentes, destinos de la LAN remota, SOCKS y diagnóstico](../docs/private-web.md).


## Validación y estado

Versión temprana con revisión del operador. Se comprobaron las pruebas del generador y el acceso administrativo inicial al servidor; cada despliegue requiere verificar terminal, archivos, recuperación y denegación de permisos en ambas direcciones. Habilitar el arranque no equivale a probar un reinicio. Systemd recupera conexiones, no terminales perdidas; usa tmux remoto.

## Nombres SSH entre dispositivos

Las herramientas de configuración conservan los ajustes SSH existentes e instalan los mismos nombres privados en Linux, macOS y Windows. Cada dispositivo conserva sus propias claves privadas.

[Registro, rutas y reversión](../docs/device-ssh.md).


## Servidor y clientes independientes

La extensión de dispositivos admite Linux, macOS y Windows, con actualizaciones independientes del servidor y los clientes. Las claves y la configuración privada quedan fuera de Git; un registro SSH con identidad fijada permite actualizar la lista de dispositivos sin credenciales de administrador. El despliegue real de siete dispositivos superó las 49 pruebas SSH dirigidas; se inspeccionó el arranque sin reiniciar.

En un cliente Linux/macOS registrado:

```bash
lazytunnel status
lazytunnel devices
ssh-lazy-alpha
lazytunnel sync
lazytunnel web alpha 6144 --local-port 16144 --path /wecom
```

[Instalación, registro e inicio de sesión, actualizaciones, soluciones para Windows y acceso privado con noVNC](../docs/fleet.md).


## Interfaz privada opcional

Una consola ligera en el navegador reúne equipos registrados, comprobaciones SSH bajo demanda y visores noVNC guardados. Incluye búsqueda, vistas de cuadrícula y lista, temas claro y oscuro y diseño para móviles. En Linux, las conexiones de los visores tienen servicios systemd independientes y sobreviven al reinicio de la interfaz. Las claves y los códigos de acceso siguen siendo privados; se conservan los escritorios y túneles SSH existentes.

```bash
cd /path/to/LazyTunnel
python3 scripts/lazytunnel-client.py update --source .
lazytunnel gui install
lazytunnel gui code
lazytunnel gui
```

[Instalación, desbloqueo con código, navegadores remotos y límites de seguridad](../docs/gui.md).


## Cita

Si utilizas LazyTunnel, cita este repositorio. GitHub lee CITATION.cff para mostrar su panel de citas. [CITATION.cff](../CITATION.cff)

```bibtex
@software{chen_lazytunnel_2026,
  author = {Chen, Lachlan},
  title = {LazyTunnel: independent private SSH relays},
  year = {2026},
  url = {https://github.com/lachlanchen/LazyTunnel}
}
```
