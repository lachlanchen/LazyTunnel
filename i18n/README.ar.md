[English](../README.md) · [العربية](README.ar.md) · [Español](README.es.md) · [Français](README.fr.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Tiếng Việt](README.vi.md) · [中文 (简体)](README.zh-Hans.md) · [中文（繁體）](README.zh-Hant.md) · [Deutsch](README.de.md) · [Русский](README.ru.md)

[![LazyingArt banner](https://github.com/lachlanchen/lachlanchen/raw/main/figs/banner.png)](https://github.com/lachlanchen/lachlanchen/blob/main/figs/banner.png)

# LazyTunnel

*اتصال SSH بين الحواسيب الخاصة، مستقل عن التحكم بسطح المكتب.*

[Website](https://lazying.art) · [GitHub Sponsors](https://github.com/sponsors/lachlanchen)

LazyTunnel مجموعة أدوات صغيرة تعتمد على OpenSSH وsystemd لربط الحواسيب الخاصة عبر خادم سحابي وسيط. يبدأ كل جهاز نفقه الصادر بنفسه، فلا يرتبط هذا الاتصال بتبديل التحكم عبر UU أو RDP أو VNC. تبقى جلسات الطرفية ونقل الملفات محمية بمصادقة SSH الأصلية.

| Donate | PayPal | Stripe |
| --- | --- | --- |
| [![Donate](https://img.shields.io/badge/Donate-LazyingArt-0EA5E9?style=for-the-badge&logo=kofi&logoColor=white)](https://chat.lazying.art/donate) | [![PayPal](https://img.shields.io/badge/PayPal-RongzhouChen-00457C?style=for-the-badge&logo=paypal&logoColor=white)](https://paypal.me/RongzhouChen) | [![Stripe](https://img.shields.io/badge/Stripe-Donate-635BFF?style=for-the-badge&logo=stripe&logoColor=white)](https://buy.stripe.com/aFadR8gIaflgfQV6T4fw400) |

## التصميم

تستمع المنافذ العكسية على واجهة loopback السحابية فقط. توجد مفاتيح منفصلة للنفق والقفزة وتسجيل الدخول، مع تثبيت مفاتيح هوية الأجهزة. لا حاجة إلى VPN أو حاوية أو تغيير المسار الافتراضي أو نشر منفذ لسطح المكتب. يكمل المشروع LazyEdge ولا يتجاوز حمايات HTTP الخاصة به.

```text
alpha ── outbound SSH ── cloud loopback ── outbound SSH ── beta
```

## البدء السريع

يحتوي المثال على مفاتيح اصطناعية واسم مضيف غير صالح؛ استخدمه لفحص المخرجات وليس للاتصال. سجّل كل جهاز فعلي بصورة مستقلة وراجع دليل النشر كاملاً قبل تشغيل أدوات التثبيت.

```bash
python3 lazytunnel.py validate --config examples/two-peers.json
python3 lazytunnel.py plan --config examples/two-peers.json
python3 -m unittest discover -s tests -v
```

## الملفات والنشر

اقرأ شرح البنية ودليل التشغيل. يحتفظ مساعد التسجيل بالمفاتيح الخاصة على الجهاز الذي أنشأها. تعرض أدوات تثبيت الخادم والأجهزة خطة فقط ما لم تمرر --apply صراحةً. تظل اختصارات UU وخدمات سطح المكتب الموجودة دون تغيير.

[docs/design.md](../docs/design.md) · [docs/operations.md](../docs/operations.md) · [scripts/](../scripts/) · [tests/](../tests/)

## الوصول الخاص إلى خدمات الويب

على الجهاز beta، افتح خدمة محلية تعمل على alpha عبر مسار SSH الحالي. نفّذ الأوامر التالية ثم افتح `http://127.0.0.1:6144/wechat` على beta. يبقى منفذ الاستماع محليًا ولا تتغير خدمات سطح المكتب.

```bash
install -D -m 0755 scripts/lazy-web "$HOME/.local/bin/lazy-web"
lazy-web run alpha 6144
```

[التحويل الدائم وأجهزة الشبكة المحلية البعيدة وSOCKS واستكشاف الأخطاء](../docs/private-web.md).


## التحقق والحالة

إصدار مبكر يتطلب مراجعة المشغّل. جرى التحقق من اختبارات التوليد وتهيئة إدارة الخادم السحابي، لكن كل نشر فعلي يحتاج إلى اختبار الطرفية ونقل الملفات بالاتجاهين والتعافي ورفض الصلاحيات غير المسموحة. تمكين الخدمة لا يثبت نجاح إعادة التشغيل. يعيد systemd الاتصال، لا الجلسة المفقودة؛ استخدم tmux عن بُعد.

## الاستشهاد

إذا استخدمت LazyTunnel فاستشهد بهذا المستودع. يقرأ GitHub ملف CITATION.cff لعرض معلومات الاستشهاد. [CITATION.cff](../CITATION.cff)

```bibtex
@software{chen_lazytunnel_2026,
  author = {Chen, Lachlan},
  title = {LazyTunnel: independent private SSH relays},
  year = {2026},
  url = {https://github.com/lachlanchen/LazyTunnel}
}
```
