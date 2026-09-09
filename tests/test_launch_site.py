from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class LaunchSiteTests(unittest.TestCase):
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
