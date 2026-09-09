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
        self.assertNotIn("stripe-buy-button", page)
        self.assertNotIn("buy.stripe.com", page)


if __name__ == "__main__":
    unittest.main()
