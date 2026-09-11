# LazyRemote launch website

Public product home: **https://remote.lazying.art/**. LazyRemote is the product
identity; LazyTunnel remains the independent core, repository, CLI and current
native preview application name. No installed identifiers or SSH aliases are
renamed by publishing this website.

The Simplified Chinese route is **https://remote.lazying.art/zh-Hans/**. Both
pages expose a visible language switch and reciprocal `hreflang` metadata. The
Chinese route reuses the same local assets, stylesheet and locale-aware download
tab script; keep its Network Fit Review scope and terms aligned with the English
source when editing either page.

The site is plain HTML, CSS and JavaScript. There is no server runtime, package
manager, tracking script, remote font, cookie banner, private API connection or
credential form. All images are local files. Download tabs work with pointer
and keyboard input; screenshot dialogs close with Escape; reduced-motion
preferences are respected. The main information and links remain readable
without JavaScript.

`sample-report.html` and its downloadable Markdown counterpart show the full
shape of the optional Network Fit Review. The Simplified Chinese equivalents
live at `zh-Hans/sample-report.html` and `zh-Hans/sample-report.md`; the HTML
reports expose reciprocal `hreflang` links. Both editions use the same synthetic
project-owned topology, are explicitly not a customer result, and contain no
real endpoint, listener, account, or credential data.

## Run locally

```bash
python3 -m http.server 8080 --bind 127.0.0.1 --directory website
```

Open http://127.0.0.1:8080. Choose another unused port if needed. The public site
is not the private management console on port 17765.

## Publish

`.github/workflows/pages.yml` publishes only `website/` through GitHub Pages.
GitHub Pages must use the GitHub Actions build type, and its custom domain must
be `remote.lazying.art`. DNS points that hostname to `lachlanchen.github.io`.
`CNAME` records the intended domain. Enable HTTPS after GitHub provisions its
certificate. No workstation or cloud management port is exposed.

Update the release tag and artifact names in `app.js` when releasing a new
version. Do not label an unsigned iOS app as an installable public download.
The page explicitly states iOS provisioning and desktop signing limits.

## Brand and real screenshots

- `assets/lazyremote-logo.png`: generated with Codex's built-in image generator,
  copied into this repository. See [brand source](../docs/lazyremote-brand.md).
- `assets/native-desktop.png` and `native-dark.png`: actual release Linux app
  window captures, using a read-only sample fleet.
- `assets/native-android.png`: actual signed Android release APK, running on an
  Android 14 emulator, connected to that same sample fleet.
- `assets/social-card.png`: browser capture of the launch site's hero.

The public images contain no real endpoint names, addresses, private keys,
access codes or account details. The demo data is explicitly labeled on the
website; it is not evidence of a live fleet's latency or availability.

Reproduce the sample data with `python3 scripts/demo-agent.py`. In the native
app choose **This device**, agent port `17769`, and any nonempty sample access
code. The fixture is loopback-only and read-only, and never touches inventory,
SSH or services. For an Android emulator, an ADB reverse can connect its local
test port to this fixture; scope it to that exact emulator and remove it after
the capture. Never redirect a user's live agent to this fixture.

Browser validation covers 390/768/1440-pixel widths, image loading, all five
download tabs, keyboard navigation, the screenshot modal and the FAQ. Keep
browser profiles and transient preview processes outside Git.
