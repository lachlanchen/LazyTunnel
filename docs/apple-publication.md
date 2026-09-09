# LazyRemote: internal TestFlight to the App Store

This is the Apple release workflow adapted from EchoMind's **standard
publication path of 2026-09-05**, checked against its actual account state on
2026-09-09. The native app is in `apps/lazytunnel`; its current display name is
LazyTunnel, while the product website is LazyRemote.

## Current state: preparation, not a submitted release

| Item | Verified result on 2026-09-09 |
| --- | --- |
| EchoMind iOS 1.0 | `WAITING_FOR_REVIEW`, with `MANUAL` release selected; not evidence of public release |
| LazyRemote / LazyTunnel | No App Store Connect app record found for `art.lazying.lazytunnel` or `art.lazying.lazyremote` |
| Developer identifiers | Neither of those bundle identifiers was registered in the queried team |
| Native source | Bundle `art.lazying.lazytunnel`, version/build `0.2.0+2` |
| iOS artifacts | Simulator build and unsigned device build; no distribution-signed IPA or uploaded TestFlight build |
| iOS visual QA | Incomplete: debugger reported a rendered frame, but captures of both the app and Safari were black on the review host |
| Changes made during this investigation | Local plan, export template, GET-only status tool, tests and documentation; no Apple registration, upload, submission or release |

There is therefore no LazyRemote TestFlight build to promote yet. Register the
app and prepare its first signed candidate before following the promotion
steps below. Keep the current bundle identifier stable unless deliberately
choosing a new app identity; changing the public display name does not require
changing that identifier.

## The important TestFlight distinction

| Existing build | Can it be selected for App Review? |
| --- | --- |
| A normal App Store Connect upload, tested by an internal group | Yes, if otherwise eligible; reuse the exact tested build |
| An upload made with **TestFlight Internal Only** distribution | No; upload a new build using normal App Store Connect distribution |
| A development/ad-hoc IPA or unsigned device build | No; archive and export with App Store distribution signing |

Apple exposes the distinction as `buildAudienceType`: `APP_STORE_ELIGIBLE` or
`INTERNAL_ONLY`. Adding an internal tester does not by itself make a normal
build Internal Only. An external TestFlight beta review is a separate optional
path; it is not a prerequisite for submitting an eligible build to App Review.
See [Apple's internal testing instructions](https://developer.apple.com/help/app-store-connect/test-a-beta-version/add-internal-testers)
and [BuildAudienceType](https://developer.apple.com/documentation/appstoreconnectapi/buildaudiencetype).

## Run the readiness inventory

From the repository root:

```bash
python3 scripts/apple_release_status.py
python3 scripts/apple_release_status.py --live
```

The first command reads the checked-in release plan and the Flutter version.
The second also queries Apple using authenticated **GET requests only**. It
reports the app/version, processed build, audience, selected build, manual
release setting and several missing fields. It cannot create an app, upload,
submit or release. It rejects a different bundle identity, ambiguous builds,
partial inventories and redirects rather than silently using them.

Files:

- [`store/apple/release-plan.json`](../store/apple/release-plan.json): candidate identity and explicit pending items. Unknown app/build IDs and artifact hashes remain `null`.
- [`store/apple/api-config.example.json`](../store/apple/api-config.example.json): structure for an owner-private API configuration.
- [`store/apple/ExportOptions.example.plist`](../store/apple/ExportOptions.example.plist): normal App Store Connect export template; replace the profile placeholder before use.
- [`scripts/apple_release_status.py`](../scripts/apple_release_status.py): Python standard library plus the installed `openssl` command; no SDK/package installation needed for status.

Store the real API configuration at `$HOME/.config/lazytunnel/apple-api.json`
(mode `0600`, parent directory `0700`). Its `private_key` field points to an
existing authorized `.p8` file, also owner-private. Use `--config /private/path`
for another account configuration. Neither file nor the generated short-lived
token belongs in Git, a screenshot or a shared log. A shared team key can be
referenced without copying it; use an appropriately authorized key for the team.

The inventory exits successfully when it can produce a report, even when
`missing` is nonempty. A zero exit status is **not submission approval**. It is
not a full App Store validator: it does not inspect signed IPA bytes, all
Console-only declarations, screenshots or reviewer connectivity. The plan's
`complete` values are operator records, not proof inferred by the tool.

`testflight_expired` is reported separately from App Store audience eligibility.
Do not turn the beta's testing lifetime into a guessed App Store rejection;
check Apple's actual version/build selection. See
[Apple's TestFlight overview](https://developer.apple.com/help/app-store-connect/test-a-beta-version/testflight-overview).

## 1. Register the app and finish its identity

Use the intended Apple developer team to register the exact explicit bundle ID
and create an iOS App Store Connect app record. Choose the final display name,
primary language and SKU; record Apple's app ID in the plan. Resolve required
agreements through the account's normal Apple interface. The first candidate
can retain version `0.2.0`; an App Store launch does not require a `1.0` label.
See [Apple: add a new app](https://developer.apple.com/help/app-store-connect/create-an-app-record/add-a-new-app/).

Create an App Store distribution provisioning profile for this bundle using a
valid Apple Distribution certificate. EchoMind's certificate may serve another
app in the same team, but **EchoMind's app-specific profile cannot**. Validate
the profile's team, bundle ID, expiration, certificate and entitlements. A
development profile with device registrations and debugging entitlement is not
an App Store profile.

Before freezing a candidate, finish the app icon/display name and inspect the
actual iOS screens, permissions and privacy manifests. A generated marketing
logo or Android screenshot is not a substitute for an iOS app screenshot.

## 2. Archive once and export a normal distribution IPA

Use a compatible macOS/Xcode host and the existing verified Flutter SDK. Keep
the application's exact source commit, lockfiles, version/build and toolchain
versions in the private build record. Store archives, signing material and IPA
output outside Git; do not duplicate whole SDKs or start overlapping archives.

The normal Flutter/Xcode path is sufficient. After installing the correct
profile and configuring signing on the build Mac, copy the export template to
a private file and replace its team/profile values. Then, in `apps/lazytunnel`:

```bash
/path/to/flutter/bin/flutter build ipa --release \
  --export-options-plist=/absolute/private/ExportOptions.plist
```

This template selects `app-store-connect`, keeps the intended build number and
sets `testFlightInternalTestingOnly` to `false`. Xcode Organizer's normal
App Store Connect distribution is also suitable. Do not use the development
IPA helper from the native setup guide for App Store publication.

EchoMind's useful signing repair was a **separate release keychain** containing
the existing distribution identity and the required Apple certificate chain.
Its builder unlocks that keychain, grants codesign access there, verifies a
signing probe, archives/exports, restores the prior search list and locks the
release keychain on exit. Reuse that scoped pattern if remote signing fails;
do not weaken the user's login keychain or replace all signing certificates.
This investigation located that working setup but did not import or unlock keys.

An existing verified `.xcarchive` can be exported again without rebuilding:

```bash
xcodebuild -exportArchive \
  -archivePath /absolute/private/LazyRemote.xcarchive \
  -exportPath /absolute/private/LazyRemote-export \
  -exportOptionsPlist /absolute/private/ExportOptions.plist
```

Verify the resulting IPA's actual signature, embedded profile, entitlements,
bundle/version/team, SDK and privacy manifests. Calculate its SHA-256, record
the application source commit, and perform relevant runtime QA. Distinguish
simulator tests, internal TestFlight installation and any physical-device
testing that actually happened. A signed device IPA does not run in a simulator.

Record publication-tool source separately from application source. Editing
release documentation does not change already signed app bytes and does not
require a new app build. Changed application inputs do require a new candidate.

## 3. Upload, wait for processing and test

Validate and upload the exact IPA using Xcode Organizer, Transporter or the
current Xcode command-line uploader. EchoMind's standard uploader validates
before upload and snapshots/checks the planned artifact hash. Its bundle and
Watch checks are EchoMind-specific: do not run that script unchanged on this app.

After upload, query the exact app, marketing version and build number. Wait for
`VALID` processing and record the Apple build ID. Check `APP_STORE_ELIGIBLE` and
complete the encryption questions. If an upload times out, inspect Apple before
retrying: an unknown client result does not mean the upload failed. See
[Apple's upload workflow](https://developer.apple.com/help/app-store-connect/manage-builds/upload-builds/).

Attach that build to an internal TestFlight group for normal testing. Once it
is satisfactory, reuse it for the formal version. A different binary or an
Internal Only upload needs a new build number and new upload.

## 4. Prepare accurate store information and reviewer access

Complete the listing, support/privacy URLs, copyright, content rights, age
questionnaire, price/availability, and any account/region requirements Apple
shows. Utilities is a plausible category for this app, but choose it based on
the shipped features. Do not copy EchoMind's social-app age rating, categories,
payments or privacy answers.

Inspect dependencies and real behavior for the privacy declaration. Locally
stored SSH credentials, data sent to an operator's own server and any data
collected by the publisher must be described according to what actually occurs.
Keep reviewer contact information and credentials in App Store Connect/private
records, not public JSON.

**SSH encryption needs its own assessment.** The native transport uses
`dartssh2` and Dart cryptography; it is not just HTTPS implemented by Apple's
operating system. Do not copy an HTTPS-only exemption or blindly set
`ITSAppUsesNonExemptEncryption=false`. Answer Apple's encryption questionnaire
for the actual implementation and distribution territories. Apple identifies
additional documentation conditions for standard encryption outside its OS,
including France. See [Apple's encryption documentation table](https://developer.apple.com/help/app-store-connect/reference/app-information/export-compliance-documentation-for-encryption).

Provide actual iPhone/iPad screenshots in the sets App Store Connect requires
for the supported devices. Website and desktop screenshots remain marketing
assets. The earlier black simulator captures are a host limitation to resolve,
not images to submit or evidence of an iOS visual pass.

Give App Review a reliable way to exercise the app: an isolated demonstration
controller with test-only identities and sample devices, or suitable built-in
demo functionality with clear review instructions. A static screenshot alone
does not test connection/terminal/viewer behavior. Never provide a production
workstation password, cloud administrator key or real fleet access. Test the
review instructions from a fresh installation outside the local LAN.

## 5. Submit the exact version, then release after approval

In App Store Connect, open the planned iOS version, select the exact eligible
build, choose **manual release**, finish the required fields, then add it to
review and submit the completed submission. Read back the resulting state.
[Apple explains the submission steps here](https://developer.apple.com/help/app-store-connect/manage-submissions-to-app-review/submit-an-app).

For later automation, follow EchoMind's simple standard publisher: scoped
identity checks; reuse the existing review submission/item when appropriate;
submit once; reconcile server state before retrying. The modern API uses
[`reviewSubmissions`](https://developer.apple.com/documentation/appstoreconnectapi/review-submissions).
Keep status, upload, review submission and public release separate operations.
The included LazyRemote status helper implements only the read-only part.

`WAITING_FOR_REVIEW` means submitted, not approved. With manual release selected,
approval can lead to `PENDING_DEVELOPER_RELEASE`; then the owner releases the
approved version. Verify actual availability before claiming the app is live.
See [manual versus automatic release](https://developer.apple.com/help/app-store-connect/manage-your-apps-availability/select-an-app-store-version-release-option).
Phased release is for version updates, not the first App Store launch:
[Apple's phased-update guide](https://developer.apple.com/help/app-store-connect/update-your-app/release-a-version-update-in-phases).

## What was learned from EchoMind

The current reference was its `docs/echomind_standard_publication.md` and
`build_echomind_apple_standard.py`, `upload_echomind_apple_standard.py`,
`publish_echomind_apple.py` and `publish_echomind_testflight_standard.py`.
The inspected protected publication-tool snapshot was
`0aed3d16abb140758d63a1a01cce3999a519cfee`; that is not a claim that its commit
is the app binary's source commit.

Earlier worktrees contain a much more complicated cross-platform approval
system. EchoMind's current owner-operated workflow explicitly supersedes it as
the default. An Android phone, Google production status, matching Android
commit, external beta approval or a new physical-device receipt is not an
Apple submission prerequisite. Keep meaningful artifact QA and accurate
evidence; do not import unrelated platform gates or invent successful tests.

All Apple investigation here was read-only. Existing SSH, UU, RDP and VNC
services were unaffected. The release readiness checks have offline tests:

```bash
python3 -m unittest discover -s tests -p 'test_apple_release_status.py' -v
```
