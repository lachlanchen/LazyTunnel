#!/usr/bin/env python3
"""Read-only Apple release readiness, adapted from EchoMind's standard workflow.

No app creation, signing, upload, review submission or public release occurs.
Local checks are the default. --live adds authenticated GET requests only.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
API = "https://api.appstoreconnect.apple.com"
REQUIREMENTS = {
    "distribution_artifact_qa", "native_iphone_ipad_screenshots",
    "privacy_declaration", "encryption_declaration", "age_rating",
    "pricing_and_availability", "reviewer_access",
}


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9-]{1,128}", value):
        raise ValueError("Invalid Apple resource identifier")
    return value


def load_plan(path):
    plan = json.loads(path.read_text())
    if (not isinstance(plan, dict) or not isinstance(plan.get("requirements"), dict)
            or plan.get("schema_version") != 1
            or plan.get("bundle_id") != "art.lazying.lazytunnel"
            or not re.fullmatch(r"\d+\.\d+(?:\.\d+)?", str(plan.get("version", "")))
            or not re.fullmatch(r"[1-9][0-9]*", str(plan.get("build_number", "")))
            or plan.get("release_type") != "MANUAL"
            or not re.fullmatch(r"[A-Z0-9]{10}", str(plan.get("team_id", "")))
            or not isinstance(plan.get("locales"), list) or not plan["locales"]
            or not all(isinstance(x, str) and re.fullmatch(r"[A-Za-z-]{2,20}", x) for x in plan["locales"])
            or set(plan.get("requirements", {})) != REQUIREMENTS
            or any(x not in ("pending", "complete") for x in plan["requirements"].values())):
        raise ValueError("Invalid LazyRemote release plan")
    for key in ("app_id", "build_id"):
        if plan.get(key) is not None:
            identifier(plan[key])
    for key, length in (("source_commit", 40), ("ipa_sha256", 64)):
        if plan.get(key) is not None and (not isinstance(plan[key], str) or not re.fullmatch(r"[0-9a-f]{%d}" % length, plan[key])):
            raise ValueError("Invalid " + key)
    return plan


def private_file(path):
    info = path.lstat()
    if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
            or stat.S_IMODE(info.st_mode) & 0o077):
        raise ValueError("Use an owner-private regular config/key file")


def raw_es256(signature):
    """Convert OpenSSL's small DER SEQUENCE(INTEGER r, INTEGER s) to JOSE."""
    if len(signature) < 8 or signature[0] != 0x30 or signature[1] != len(signature) - 2:
        raise ValueError("Invalid ECDSA signature")
    pos, out = 2, b""
    for _ in range(2):
        if pos + 2 > len(signature) or signature[pos] != 2:
            raise ValueError("Invalid ECDSA integer")
        n = signature[pos + 1]
        value = signature[pos + 2:pos + 2 + n]
        if len(value) != n or not value or value[0] & 0x80:
            raise ValueError("Invalid ECDSA integer length/sign")
        value = value.lstrip(b"\0")
        if not value or len(value) > 32:
            raise ValueError("Expected a P-256 signature")
        out += value.rjust(32, b"\0")
        pos += 2 + n
    if pos != len(signature):
        raise ValueError("Trailing signature bytes")
    return out


def make_token(config_path):
    private_file(config_path)
    config = json.loads(config_path.read_text())
    if (not re.fullmatch(r"[A-Z0-9]{10}", str(config.get("key_id", "")))
            or not re.fullmatch(r"[0-9a-fA-F-]{36}", str(config.get("issuer_id", "")))):
        raise ValueError("Invalid App Store Connect API configuration")
    key = Path(config["private_key"]).expanduser()
    private_file(key)
    encode = lambda raw: base64.urlsafe_b64encode(raw).rstrip(b"=")
    pack = lambda obj: encode(json.dumps(obj, separators=(",", ":")).encode())
    now = int(time.time())
    body = pack({"alg": "ES256", "kid": config["key_id"], "typ": "JWT"}) + b"." + pack({
        "iss": config["issuer_id"], "iat": now, "exp": now + 600, "aud": "appstoreconnect-v1",
    })
    signed = subprocess.run(["openssl", "dgst", "-sha256", "-sign", str(key)],
                            input=body, capture_output=True, timeout=15)
    if signed.returncode:
        raise ValueError("Could not sign App Store Connect token; key contents omitted")
    return (body + b"." + encode(raw_es256(signed.stdout))).decode()


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("Apple API redirect refused before forwarding credentials")


class Apple:
    def __init__(self, token):
        self.token = token
        self.opener = urllib.request.build_opener(NoRedirect())

    def get(self, path, query=None):
        if not re.fullmatch(r"/v[12]/[A-Za-z0-9/_-]+", path):
            raise ValueError("Invalid Apple API path")
        url = API + path + ("?" + urllib.parse.urlencode(query) if query else "")
        request = urllib.request.Request(url, method="GET", headers={
            "Authorization": "Bearer " + self.token, "Accept": "application/json",
        })
        try:
            with self.opener.open(request, timeout=25) as response:
                raw = response.read(4 * 1024 * 1024 + 1)
                if len(raw) > 4 * 1024 * 1024:
                    raise ValueError("Unexpectedly large Apple API response")
                return json.loads(raw)
        except urllib.error.HTTPError as error:
            raise ValueError(f"Apple API GET failed with HTTP {error.code}; no provider change was made") from None


def collection(response):
    if not isinstance(response, dict):
        raise ValueError("Expected an Apple resource response")
    if response.get("links", {}).get("next"):
        raise ValueError("Apple paginated this inventory; do not treat a partial result as complete")
    data = response.get("data")
    if not isinstance(data, list):
        raise ValueError("Expected an Apple resource collection")
    seen = set()
    for item in data:
        if not isinstance(item, dict):
            raise ValueError("Expected an Apple resource object")
        value = identifier(item.get("id"))
        if value in seen:
            raise ValueError("Duplicate Apple resource")
        seen.add(value)
    return data


def related(item, key):
    link = item.get("relationships", {}).get(key, {}).get("data")
    return link.get("id") if isinstance(link, dict) else None


def assess_build(build, prerelease, plan, app_id):
    a, p = build.get("attributes", {}), prerelease.get("attributes", {})
    if (related(build, "app") != app_id or a.get("version") != plan["build_number"]
            or p.get("version") != plan["version"] or p.get("platform") != "IOS"):
        raise ValueError("Apple build belongs to a different app, platform or version")
    missing = []
    if a.get("processingState") != "VALID":
        missing.append("Wait for a VALID processed build")
    if a.get("buildAudienceType") != "APP_STORE_ELIGIBLE":
        missing.append("Require APP_STORE_ELIGIBLE; INTERNAL_ONLY needs a new standard-distribution upload")
    if a.get("usesNonExemptEncryption") is None:
        missing.append("Complete the build's encryption declaration in App Store Connect")
    return missing


def local_report(plan, root=ROOT):
    missing = ["Complete " + k.replace("_", " ") for k, v in plan["requirements"].items() if v != "complete"]
    for key in ("source_commit", "ipa_sha256"):
        if not plan.get(key):
            missing.append("Record exact signed-artifact " + key)
    version = re.search(r"^version:\s*(\S+)", (root / "apps/lazytunnel/pubspec.yaml").read_text(), re.M)
    if not version or version[1] != plan["version"] + "+" + plan["build_number"]:
        missing.append("Align the release plan with pubspec.yaml version/build before archiving")
    return {"bundle_id": plan["bundle_id"], "version": plan["version"],
            "build_number": plan["build_number"], "mode": "local", "missing": missing,
            "provider_changes": False, "note": "Readiness inventory, not signature verification or Apple approval"}


def live_report(client, plan, root=ROOT):
    report = local_report(plan, root)
    report["mode"] = "live-get-only"
    missing = report["missing"]
    apps = collection(client.get("/v1/apps", {"filter[bundleId]": plan["bundle_id"], "limit": "20"}))
    if len(apps) > 1:
        raise ValueError("Ambiguous Apple app identity")
    if not apps:
        missing.append("Create the LazyRemote App Store Connect app record and exact bundle identifier")
        return report
    app = apps[0]
    if app.get("attributes", {}).get("bundleId") != plan["bundle_id"] or plan.get("app_id") not in (None, app["id"]):
        raise ValueError("Apple app identity differs from the plan")
    report["app_id"] = app_id = identifier(app["id"])
    versions = collection(client.get(f"/v1/apps/{app_id}/appStoreVersions", {"filter[platform]": "IOS", "limit": "200"}))
    versions = [v for v in versions if v.get("attributes", {}).get("versionString") == plan["version"]]
    if len(versions) > 1:
        raise ValueError("Ambiguous Apple version")
    if not versions:
        missing.append("Create the planned iOS App Store version")
    else:
        v = versions[0]; va = v.get("attributes", {})
        report.update(version_id=v["id"], state=va.get("appVersionState", va.get("appStoreState")), release_type=va.get("releaseType"))
        if va.get("releaseType") != "MANUAL":
            missing.append("Select manual release before submission")
        if not va.get("copyright"):
            missing.append("Complete version copyright")
        locs = collection(client.get(f"/v1/appStoreVersions/{v['id']}/appStoreVersionLocalizations", {"limit": "200"}))
        for locale in plan["locales"]:
            found = [x for x in locs if x.get("attributes", {}).get("locale") == locale]
            if len(found) != 1:
                missing.append("Complete version localization " + locale)
            else:
                for field in ("description", "keywords", "supportUrl"):
                    if not found[0]["attributes"].get(field):
                        missing.append("Complete " + locale + " " + field)
    builds = collection(client.get("/v1/builds", {"filter[app]": app_id, "filter[version]": plan["build_number"], "limit": "200"}))
    if plan.get("build_id"):
        builds = [b for b in builds if b["id"] == plan["build_id"]]
    if not builds:
        missing.append("Upload the exact distribution-signed IPA and wait for processing")
    elif len(builds) > 1:
        missing.append("Pin the exact build_id; this build number exists in multiple release versions")
    else:
        bid = identifier(builds[0]["id"])
        build = client.get(f"/v1/builds/{bid}", {"include": "app,preReleaseVersion"})["data"]
        if build.get("id") != bid or build.get("type") != "builds":
            raise ValueError("Apple returned a different build resource")
        pre_id = identifier(related(build, "preReleaseVersion"))
        pre = client.get(f"/v1/preReleaseVersions/{pre_id}")["data"]
        if pre.get("id") != pre_id or pre.get("type") != "preReleaseVersions":
            raise ValueError("Apple returned a different pre-release resource")
        missing.extend(assess_build(build, pre, plan, app_id))
        attrs = build.get("attributes", {})
        report.update(build_id=bid, processing_state=attrs.get("processingState"),
                      build_audience=attrs.get("buildAudienceType"), testflight_expired=attrs.get("expired"))
        if versions:
            selected = client.get(f"/v1/appStoreVersions/{versions[0]['id']}/relationships/build").get("data")
            if selected is None:
                missing.append("Attach the exact eligible build to the App Store version")
            elif not isinstance(selected, dict) or selected.get("type") != "builds" or selected.get("id") != bid:
                missing.append("A different or unknown build is attached to the store version; reconcile it")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, default=ROOT / "store/apple/release-plan.json")
    parser.add_argument("--config", type=Path, default=Path.home() / ".config/lazytunnel/apple-api.json")
    parser.add_argument("--live", action="store_true", help="Add authenticated, read-only Apple state")
    args = parser.parse_args()
    plan = load_plan(args.plan)
    report = live_report(Apple(make_token(args.config)), plan) if args.live else local_report(plan)
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        raise SystemExit(str(error)) from None
