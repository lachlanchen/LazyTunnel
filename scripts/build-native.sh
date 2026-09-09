#!/usr/bin/env bash
# Reuse a pinned SDK; build only the selected platform on its supported host.
set -euo pipefail
native_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
native_flutter="${FLUTTER_BIN:-flutter}"
native_target="${1:-}"
case "$native_target" in
  linux|android|macos|ios|ios-simulator) ;;
  *) echo 'Usage: FLUTTER_BIN=/path/to/flutter scripts/build-native.sh linux|android|macos|ios|ios-simulator' >&2; exit 2 ;;
esac
native_version="$("$native_flutter" --version)"
if [[ "$native_version" != "Flutter 3.47.2 "* ]]; then
  echo 'Use the pinned Flutter 3.47.2 SDK (see docs/native-apps.md).' >&2
  exit 2
fi
case "$native_target:$(uname -s)" in
  linux:Linux|android:Linux|android:Darwin|macos:Darwin|ios:Darwin|ios-simulator:Darwin) ;;
  *) echo 'This target requires a different build host.' >&2; exit 2 ;;
esac
cd "$native_root/apps/lazytunnel"
"$native_flutter" pub get --enforce-lockfile
"$native_flutter" analyze
"$native_flutter" test
case "$native_target" in
  linux|macos) "$native_flutter" build "$native_target" --release ;;
  android)
    : "${LAZYTUNNEL_ANDROID_SIGNING_PROPERTIES:?Set the path to your private signing properties}"
    "$native_flutter" build apk --release --split-per-abi ;;
  ios) "$native_flutter" build ios --release --no-codesign ;;
  ios-simulator) "$native_flutter" build ios --simulator --debug ;;
esac
