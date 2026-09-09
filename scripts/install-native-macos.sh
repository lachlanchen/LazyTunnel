#!/usr/bin/env bash
set -euo pipefail
native_bundle="${1:?Usage: install-native-macos.sh /path/to/LazyTunnel.app}"
[[ "$(uname -s)" == Darwin ]] || { echo 'Run this installer on macOS.' >&2; exit 2; }
[[ -f "$native_bundle/Contents/Info.plist" ]] || { echo 'Select the complete .app bundle.' >&2; exit 2; }
native_id="$(/usr/libexec/PlistBuddy -c 'Print :CFBundleIdentifier' "$native_bundle/Contents/Info.plist")"
[[ "$native_id" == art.lazying.lazytunnel ]] || { echo 'Unexpected application identifier.' >&2; exit 2; }
native_target="$HOME/Applications/LazyTunnel.app"
mkdir -p "$HOME/Applications"
if [[ -L "$native_target" ]]; then echo 'Refusing an unrelated application symlink.' >&2; exit 2; fi
if [[ -e "$native_target" ]]; then
  native_old_id="$(/usr/libexec/PlistBuddy -c 'Print :CFBundleIdentifier' "$native_target/Contents/Info.plist")"
  [[ "$native_old_id" == "$native_id" ]] || { echo 'An unrelated app already occupies the destination.' >&2; exit 2; }
  # Do not replace or terminate a running application. The user can close it normally.
  if pgrep -f "$native_target/Contents/MacOS/LazyTunnel" >/dev/null; then
    echo 'Close the existing LazyTunnel window normally, then run the installer again.' >&2; exit 2
  fi
  native_backup="$HOME/Library/Application Support/LazyTunnel/previous-$(date +%Y%m%d-%H%M%S).app"
  mkdir -p "$(dirname "$native_backup")"
  mv "$native_target" "$native_backup"
fi
ditto "$native_bundle" "$native_target"
echo "Installed: $native_target"
echo 'Open LazyTunnel from Applications. No background SSH or desktop service was changed.'
