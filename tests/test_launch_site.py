from pathlib import Path
import unittest
from urllib.parse import parse_qs, unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]


class LaunchSiteTests(unittest.TestCase):
    def test_localized_routes_are_reciprocal_and_reuse_launch_assets(self):
        english = (ROOT / "website" / "index.html").read_text(encoding="utf-8")
        chinese = (ROOT / "website" / "zh-Hans" / "index.html").read_text(
            encoding="utf-8"
        )

        self.assertIn('hreflang="zh-Hans" href="https://remote.lazying.art/zh-Hans/"', english)
        self.assertIn('href="zh-Hans/" hreflang="zh-Hans"', english)
        self.assertIn('<html lang="zh-Hans">', chinese)
        self.assertIn('<link rel="canonical" href="https://remote.lazying.art/zh-Hans/">', chinese)
        self.assertIn('hreflang="en" href="https://remote.lazying.art/"', chinese)
        self.assertIn('href="../" hreflang="en"', chinese)
        self.assertIn('href="../style.css"', chinese)
        self.assertIn('src="../app.js"', chinese)
        self.assertIn('src="../assets/native-desktop.png"', chinese)

    def test_simplified_chinese_page_preserves_product_and_offer_boundaries(self):
        page = (ROOT / "website" / "zh-Hans" / "index.html").read_text(
            encoding="utf-8"
        )

        for platform in ("Ubuntu", "macOS", "Windows", "iOS", "Android"):
            self.assertIn(platform, page)
        self.assertIn("开源、自托管，无需注册托管账户", page)
        self.assertIn("由开源、自托管、与供应商无关的", page)
        self.assertIn("不会替换或接管现有的 UU、RDP、VNC 服务", page)
        self.assertIn("一台可连接的中继服务器和最多三台现有电脑", page)
        self.assertIn("USD 250 · 固定范围", page)
        self.assertIn("可选软件评估服务", page)
        self.assertIn("第一封邮件只写环境元数据", page)
        self.assertIn("书面确认范围并付款后十个工作日内交付", page)
        self.assertIn("最多十项事实性更正", page)
        self.assertIn("路由器或防火墙改动", page)
        self.assertIn("工作开始前取消可全额退款", page)
        self.assertIn("十四个自然日内删除", page)
        self.assertIn("不保证未实地检查的网络", page)
        self.assertIn('href="../sample-report.html" hreflang="en"', page)
        self.assertIn("https://github.com/lachlanchen/LazyTunnel/releases/tag/v0.2.0", page)
        self.assertNotIn("buy.stripe.com", page)

    def test_simplified_chinese_fit_check_opens_a_chinese_template(self):
        page = (ROOT / "website" / "zh-Hans" / "index.html").read_text(
            encoding="utf-8"
        )
        prefix = 'href="mailto:contact@lazying.art?'
        encoded = page.split(prefix, 1)[1].split('"', 1)[0].replace("&amp;", "&")
        query = parse_qs(urlsplit(f"mailto:contact@lazying.art?{encoded}").query)

        self.assertEqual(unquote(query["subject"][0]), "LazyRemote 网络适配确认")
        body = unquote(query["body"][0])
        self.assertIn("需要访问的设备或服务", body)
        self.assertIn("终端操作系统（最多三台）", body)
        self.assertIn("NAT、CGNAT 或端口限制", body)
        self.assertIn("我不会在第一封邮件中附上密码、私钥", body)

    def test_simplified_chinese_readme_promotes_localized_route(self):
        readme = (ROOT / "i18n" / "README.zh-Hans.md").read_text(encoding="utf-8")
        localized_url = (
            "https://remote.lazying.art/zh-Hans/?utm_source=github"
            "&utm_medium=readme&utm_campaign=lazytunnel_readme"
        )

        self.assertGreaterEqual(readme.count(localized_url), 2)

    def test_network_fit_review_is_bounded_and_fit_first(self):
        page = (ROOT / "website" / "index.html").read_text(encoding="utf-8")

        self.assertIn("LazyRemote Network Fit Review", page)
        self.assertIn("fixed USD 250 review", page)
        self.assertIn("one reachable relay and up to three computers", page)
        self.assertIn("Topology and listener-exposure map", page)
        self.assertIn("Recovery, rollback, and acceptance checklist", page)
        self.assertIn("Start with metadata only", page)
        self.assertIn("written scope and payment", page)
        self.assertIn("Cancel before work begins for a full refund", page)
        self.assertIn("Deployment, hardware, relay hosting", page)
        self.assertIn("does not guarantee", page)
        self.assertIn("mailto:contact@lazying.art?subject=LazyRemote%20network%20fit%20check", page)
        self.assertIn('href="sample-report.html"', page)
        self.assertNotIn("stripe-buy-button", page)
        self.assertNotIn("buy.stripe.com", page)

    def test_network_fit_sample_is_complete_and_truthful(self):
        page = (ROOT / "website" / "sample-report.html").read_text(encoding="utf-8")
        markdown = (ROOT / "website" / "sample-report.md").read_text(encoding="utf-8")

        for text in (page, markdown):
            self.assertIn("Conditional go", text)
            self.assertIn("Listener exposure map", text)
            self.assertIn("Identity and trust map", text)
            self.assertIn("Acceptance checklist", text)
            self.assertIn("Rollback", text)
            self.assertIn("not a customer result", text)
            self.assertIn("no private fleet data", text)
            self.assertIn("127.0.0.1", text)
        self.assertIn("sample-report.md", page)
        self.assertIn("utm_source=sample_report", page)
        self.assertNotIn("0.0.0.0:</code>", page)
        self.assertNotIn("buy.stripe.com", page)


if __name__ == "__main__":
    unittest.main()
