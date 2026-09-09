import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("apple_release_status", ROOT / "scripts/apple_release_status.py")
apple = importlib.util.module_from_spec(spec)
spec.loader.exec_module(apple)


class AppleReadinessTests(unittest.TestCase):
    def setUp(self):
        self.plan = apple.load_plan(ROOT / "store/apple/release-plan.json")
        self.build = {
            "attributes": {"version": self.plan["build_number"], "expired": False,
                           "processingState": "VALID", "buildAudienceType": "APP_STORE_ELIGIBLE",
                           "usesNonExemptEncryption": True},
            "relationships": {"app": {"data": {"id": "123"}}},
        }
        self.pre = {"attributes": {"version": self.plan["version"], "platform": "IOS"}}

    def test_standard_build_can_be_tested_internally_and_remain_eligible(self):
        self.assertEqual(apple.assess_build(self.build, self.pre, self.plan, "123"), [])

    def test_internal_only_is_not_promotable(self):
        self.build["attributes"]["buildAudienceType"] = "INTERNAL_ONLY"
        self.assertTrue(any("new standard-distribution upload" in x for x in apple.assess_build(self.build, self.pre, self.plan, "123")))

    def test_unknown_audience_is_not_assumed_eligible(self):
        del self.build["attributes"]["buildAudienceType"]
        self.assertTrue(apple.assess_build(self.build, self.pre, self.plan, "123"))

    def test_rejects_other_app_or_marketing_version(self):
        with self.assertRaises(ValueError):
            apple.assess_build(self.build, self.pre, self.plan, "999")
        self.pre["attributes"]["version"] = "99.0"
        with self.assertRaises(ValueError):
            apple.assess_build(self.build, self.pre, self.plan, "123")

    def test_beta_expiration_is_not_used_as_store_eligibility(self):
        self.build["attributes"].update(expired=True)
        self.assertEqual(apple.assess_build(self.build, self.pre, self.plan, "123"), [])
        self.build["attributes"].update(processingState="PROCESSING", usesNonExemptEncryption=None)
        self.assertEqual(len(apple.assess_build(self.build, self.pre, self.plan, "123")), 2)

    def test_status_missing_record_performs_only_one_get(self):
        class Fake:
            calls = []
            def get(self, path, query):
                self.calls.append((path, query))
                return {"data": []}
        client = Fake()
        result = apple.live_report(client, self.plan)
        self.assertFalse(result["provider_changes"])
        self.assertEqual(len(client.calls), 1)
        self.assertIn("Create the LazyRemote App Store Connect app record", result["missing"][-1])

    def test_rejects_partial_and_duplicate_inventories(self):
        for payload in [{"data": [], "links": {"next": "https://example.invalid"}},
                        {"data": [{"id": "123"}, {"id": "123"}]}, {"data": [None]}, []]:
            with self.assertRaises(ValueError):
                apple.collection(payload)

    def test_build_must_actually_be_attached_to_store_version(self):
        build = copy.deepcopy(self.build)
        build.update(id="build-1", type="builds")
        build["relationships"]["preReleaseVersion"] = {"data": {"id": "pre-1"}}
        pre = dict(self.pre, id="pre-1", type="preReleaseVersions")
        version = {"id": "version-1", "attributes": {"versionString": self.plan["version"],
                   "releaseType": "MANUAL", "copyright": "2026 Example", "appStoreState": "PREPARE_FOR_SUBMISSION"}}
        responses = {
            "/v1/apps": {"data": [{"id": "123", "attributes": {"bundleId": self.plan["bundle_id"]}}]},
            "/v1/apps/123/appStoreVersions": {"data": [version]},
            "/v1/appStoreVersions/version-1/appStoreVersionLocalizations": {"data": []},
            "/v1/builds": {"data": [{"id": "build-1"}]},
            "/v1/builds/build-1": {"data": build},
            "/v1/preReleaseVersions/pre-1": {"data": pre},
        }
        class Fake:
            def get(self, path, query=None):
                return responses[path]
        for selected, message in [(None, "Attach the exact"),
                                  ({"type": "builds", "id": "other"}, "different or unknown"),
                                  ({"type": "builds", "id": "build-1"}, None)]:
            responses["/v1/appStoreVersions/version-1/relationships/build"] = {"data": selected}
            report = apple.live_report(Fake(), self.plan)
            attachment = [x for x in report["missing"] if "Attach the exact" in x or "different or unknown" in x]
            if message:
                self.assertIn(message, attachment[0])
            else:
                self.assertEqual(attachment, [])

    def test_der_ecdsa_integer_padding(self):
        r = b"\x00\x80" + b"\x12" * 31
        s = b"\x03"
        body = b"\x02" + bytes([len(r)]) + r + b"\x02\x01" + s
        self.assertEqual(apple.raw_es256(b"\x30" + bytes([len(body)]) + body), r[1:] + s.rjust(32, b"\0"))

    def test_rejects_invalid_signatures(self):
        for value in (b"", b"\x30\x06\x02\x01\xff\x02\x01\x01", b"\x30\x00garbage"):
            with self.assertRaises(ValueError):
                apple.raw_es256(value)

    def test_rejects_api_path_injection_before_network(self):
        client = apple.Apple("fixture")
        for value in ("https://other.invalid", "//other.invalid/v1/apps", "/v1/apps?token=x", "/v1/apps\n"):
            with self.assertRaises(ValueError):
                client.get(value)

    def test_redirect_never_forwards_token(self):
        with self.assertRaises(ValueError):
            apple.NoRedirect().redirect_request(None, None, 302, "", {}, "https://other.invalid")

    def test_private_file_permissions_and_foreign_bundle(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "plan.json"
            p.write_text("fixture"); p.chmod(0o644)
            with self.assertRaises(ValueError):
                apple.private_file(p)
            p.chmod(0o600); apple.private_file(p)
            plan = copy.deepcopy(self.plan); plan["bundle_id"] = "art.lazying.echomind"
            p.write_text(json.dumps(plan))
            with self.assertRaises(ValueError):
                apple.load_plan(p)


if __name__ == "__main__":
    unittest.main()
