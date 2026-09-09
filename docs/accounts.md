# One relay, separate accounts

Available in **`@lazyingart/lazytunnel@0.3.0`**. Run one private account for
yourself, or host several independent accounts on one Linux relay. The
MIT-licensed core can be reused in your own remote-access service. Each account
has separate device lists and SSH permissions. Both GUIs remain optional.

Authentication uses OpenSSH account keys or passwords. The operator creates
accounts and issues invitations. This release does not include public signup,
billing, email recovery or a cloud account-login screen in the native app.

```text
Alice: laptop ↔ phone       Bob: laptop ↔ workstation
          \                         /
           one cloud OpenSSH relay
           separate account permissions
```

Users can list, enroll and revoke their own devices. They cannot list another
account's devices, forward to them, retrieve their bundles, authorize their
keys, transfer ownership or choose arbitrary relay ports. Friendly names are
private to an account: Alice and Bob can both name a device `laptop`. The server
assigns a stable internal ID and an unused loopback port.

Within an account, devices trust each other's endpoint-login keys. Use separate
accounts for people who should not have that mutual access. Per-device guest
sharing is not implemented. Destination OS and application permissions apply.

## 1. Install your relay

Use Linux with systemd, Python 3.9+, OpenSSH Server, sudo, iproute2, `useradd`,
`chpasswd` and `visudo`. The tested target is Ubuntu 24.04/OpenSSH 9.6. Node 22+
and npm provide the CLI. Keep an independent administrator SSH connection while
applying policy. Your chosen SSH port must already work through the firewall.

```bash
npm install -g @lazyingart/lazytunnel
lazytunnel-server install
sudo lazytunnel-server install --apply

# NEW relay only: use your real hostname and EXISTING public SSH port.
sudo lazytunnel-server account init \
  --host relay.example.com --port 22 \
  --host-key-file /etc/ssh/ssh_host_ed25519_key.pub --apply
```

Code installation creates no accounts and starts no tunnels. `account init`
creates the private version-2 registry and restricted account policy. It does
not change public SSH ports, firewalls, default routes or desktop services.
Omit `--apply` to preview mutating account commands.

If Node/npm is outside sudo's PATH, install from the verified npm package:

```bash
sudo /usr/bin/python3 "$(npm root -g)/@lazyingart/lazytunnel/scripts/lazytunnel-server.py" install --apply --no-launcher
relay() {
  sudo /usr/bin/python3 /usr/local/lib/lazytunnel/server/current/scripts/lazytunnel-server.py "$@"
}
relay account --help
```

This root-owned runtime works without Node in sudo's PATH; substitute
`relay account ...` for the administrative commands below.

For an **existing fleet**, skip `init`. Update the server code and add an
account. Its version-1 fleet becomes account `default`, preserving names, keys,
ports, legacy carriers and routes. No existing devices move to the new account.
Installing/updating npm alone does not activate that migration.

## 2. Create accounts and invitations

The user generates a private account key and gives the operator only its public
`.pub` file. It must be separate from the device's generated role keys.

```bash
# User's computer; choose a passphrase when prompted.
ssh-keygen -t ed25519 -f "$HOME/.ssh/lazytunnel-account"
```

On the relay, use the received public key:

```bash
sudo lazytunnel-server account add alice --key-file /private/alice.pub --apply
sudo lazytunnel-server account invite alice --output /private/alice.json
sudo lazytunnel-server account list

# Bob supplies a DIFFERENT account public key.
sudo lazytunnel-server account add bob --key-file /private/bob.pub --apply
sudo lazytunnel-server account invite bob --output /private/bob.json
```

Invitations contain the account name, address, port and pinned server host key;
no password or private key. Deliver them through a trusted channel to prevent
server-key substitution. `invite` refuses to overwrite an existing output file.

### Password login

Alternatively, enable an OpenSSH account password. Use a unique password of at
least 12 characters, in a root-owned regular file with mode 0600 and one line.
Symlinks/hard links are rejected. This Bash prompt keeps it out of argv/history:

```bash
sudo bash -c 'umask 077; read -r -s -p "New account password: " pw; echo; printf "%s\n" "$pw" > /root/alice-password'
sudo lazytunnel-server account add alice --password-file /root/alice-password --apply
sudo lazytunnel-server account invite alice --output /root/alice.json
sudo unlink /root/alice-password
```

`add` accepts both key and password options. Passwords reach `chpasswd` through
a pipe; only the OS password hash is retained. LazyTunnel does not store them
in manifests or on clients. A failed initial password setup leaves the account
unusable until corrected. Repeated `add` does not reset a password; use
`account password`. Do not put credentials in Git or public notes.

## 3. Log in from a device

Each endpoint needs a working SSH server and readable Ed25519 host public key.
Enable that through normal OS administration first. Root is refused as an
endpoint user. Windows users should follow the [fleet prerequisites](fleet.md),
including authorized-key ACLs and their actual Windows account name.

```bash
npm install -g @lazyingart/lazytunnel
lazytunnel-client install
lazytunnel-client login --invite alice.json --name laptop \
  --identity "$HOME/.ssh/lazytunnel-account"
lazytunnel-client boot
lazytunnel-client account devices --identity "$HOME/.ssh/lazytunnel-account"
```

For password login, omit `--identity`; OpenSSH prompts securely. PowerShell uses
the same npm commands, with `"$env:USERPROFILE\.ssh\lazytunnel-account"` as the
identity path. The shared Node CLI handles account enrollment; existing OS
backends handle device installation.

Login generates missing device keys locally, submits the public packet, receives
its account-scoped bundle and verifies local identities before installation.
Repeating it with identical keys/name is idempotent. Conflicts do not silently
transfer ownership. The public invitation is saved as
`~/.config/lazytunnel-fleet/account.json`; account passwords/keys are not copied.
Pass `--identity` again for later account administration. Device SSH and `sync`
use their own keys and need no account password.

Enroll another computer with the same invitation and a different friendly name,
such as `workstation`. On previously enrolled devices:

```bash
lazytunnel-client sync
lazytunnel-client devices
lazytunnel-client ssh workstation hostname
ssh-lazy-workstation
scp-lazy ./example.txt lazy-workstation:Downloads/
lazytunnel-client web workstation 6080 --local-port 16080
```

Open `http://127.0.0.1:16080` on the client running the forward. The destination
must already serve noVNC/the app. This creates no desktop and preserves the
viewer authentication. See [fleet boot and Windows usage](fleet.md).

`account devices` queries the registry live, including revoked entries.
`devices` and the GUI use the installed bundle. **Run `sync` on remaining
endpoints after membership changes.** No automatic policy-polling daemon is
added. One endpoint OS user has one active enrollment. Do not share one host
identity or Windows administrator key file between unrelated account owners.

## 4. Revoke a device or disable an account

The owner can revoke by friendly name or internal ID:

```bash
lazytunnel-client account revoke phone --identity "$HOME/.ssh/lazytunnel-account"
# On each remaining endpoint:
lazytunnel-client sync
```

The relay immediately removes device authorization and ends its managed
carrier/info/jump sessions plus affected same-account jump sessions. Existing
connections cannot retain stale relay permissions. Active shells/forwards in
that account may close; other accounts and administrators stay connected.
Remaining carriers stay running. Use tmux for shell work across disconnects.

Endpoint `sync` removes only exact key rows recorded in its previous managed
bundle, preserving unrelated manual keys. Cloud revocation does **not** instantly
revoke direct LAN access: synchronize the endpoints and review any separately
granted manual keys. Hiding an alias alone is not revocation.

Relay administration:

```bash
sudo lazytunnel-server account disable alice --apply
sudo lazytunnel-server account enable alice --apply
sudo lazytunnel-server account key alice --key-file /private/alice-new.pub --apply
sudo lazytunnel-server account password alice --password-file /root/alice-password --apply
```

Disable blocks the account and its devices. Enable restores non-revoked devices.
`key` replaces account login keys; password rotation leaves endpoint identities
unchanged. Revoked records/ports remain reserved as ownership history. Deletion,
unrevocation, identity replacement and transfer require a reviewed migration.
Revoking legacy `external_carrier` devices is refused until their administrator
handles the independently owned carrier. This can also prevent disabling a
legacy account; the command fails before changing its policy.

## Security and limits

- `lf-acct-ACCOUNT` SSH identities have no PTY, shell, arbitrary command or
  forwarding. A forced command uses sudo to invoke one exact root-owned helper
  with no arguments. Ownership comes from the authenticated sudo UID, never a
  JSON field. The account cannot submit a different owner or executable path.
- Requests are single JSON lines up to 64 KiB with a 60-second deadline. Only
  list/enroll/revoke operations exist. Locking and manifest revision checks
  reject concurrent overwrites; retry an explicit conflict.
- `PermitOpen`, role keys, pinned host keys, bundles and aliases are scoped to
  accounts on the server. UI filtering alone is not an authorization boundary.
  Relay listeners stay on loopback.
- Limits: 64 accounts, 256 total device records, 32 self-enrolled records per
  account; revoked records count. Allocation uses 23000–23999, skipping occupied
  and reserved ports. No public signup/rate-billing infrastructure is included.
- The server operator is trusted. Root can administer all accounts; shared-host
  resource isolation is not equivalent to separate VMs. Apply suitable SSH
  ingress/rate controls. This is not a claim of an audited hosted SaaS service.
- Review any existing address-specific SSH policy. The installer validates
  syntax and effective generated settings for a loopback connection, rejecting
  earlier conflicting Match blocks rather than rewriting them.

The local browser/agent access code remains distinct from cloud authentication.
The console displays the account label; both GUIs use the endpoint's scoped
bundle. They do not need a public management port or public signup backend.

## State, rollback and verification

Private root state: `/var/lib/lazytunnel-fleet/`. Generated keys/bundles:
`/etc/lazytunnel-fleet/`. Account access has a dedicated sudoers file. Revisions
save previous target bytes, manifest, modes and owners. Failed policy applies
restore them and reload validated prior SSH settings. Inert newly created users
can remain recorded for a safe retry. Do not restore an old policy over later
changes without review, or downgrade a version-2 manifest to bypass isolation.

```bash
npm test
npm run test:core
npm run test:accounts:integration
npm run verify:package
```

The integration test uses disposable Docker with no host networking/published
ports. It checks real OpenSSH/sudo key/password login, isolation of lists,
bundles and forwarding, rejected spoofing, idempotent enrollment, policy rollback,
and revocation while another account keeps an established connection. Docker
is a development test dependency, not a production requirement.

New Windows/macOS account login has shared CLI/argument tests but has not been
accepted end-to-end on those OSes in this release; real account SSH integration
targets Linux. Development did not change the existing production relay or
UU/RDP/VNC sessions. No reboot test is claimed.

See [npm installation](npm.md), [fleet startup](fleet.md) and [local GUI](gui.md).
