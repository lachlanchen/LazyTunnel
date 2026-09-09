#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('../', import.meta.url));
const pkg = JSON.parse(fs.readFileSync(path.join(root, 'package.json')));
const npm = process.env.npm_execpath;
const got = spawnSync(npm ? process.execPath : 'npm', [...(npm ? [npm] : []), 'pack', '--dry-run', '--json', '--ignore-scripts'],
  { cwd: root, encoding: 'utf8', timeout: 60000 });
if (got.status !== 0) throw new Error('npm pack inspection failed: ' + got.stderr);
const pack = JSON.parse(got.stdout)[0];
const allowed = [...pkg.files, 'package.json'].map(pattern => new RegExp('^' + pattern.split('*')
  .map(part => part.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('[^/]*') + '$'));
const required = [
  ...Object.values(pkg.bin), 'lib/cli.mjs', 'lib/accounts.mjs', 'accounts.py', 'scripts/account-admin.py', 'scripts/account-command.py', 'docs/accounts.md', 'lazytunnel.py', 'fleet.py', 'LICENSE',
  'scripts/lazytunnel-client.py', 'scripts/lazytunnel-server.py', 'scripts/lazytunnel.ps1',
  'scripts/fleet-install-posix.py', 'scripts/fleet-install-windows.ps1', 'scripts/fleet-install-edge.py',
  'scripts/fleet-prepare.py', 'scripts/fleet-prepare.ps1', 'scripts/lazy-web',
  'lazytunnel_core/agent.py', 'lazytunnel_core/http_api.py', 'lazytunnel_core/controller.py', 'lazytunnel_core/__init__.py',
  'gui/server.py', 'gui/index.html', 'gui/app.js', 'gui/style.css', 'gui/icon.svg', 'docs/npm.md',
];
const names = new Set(pack.files.map(file => file.path));
for (const file of pack.files) {
  if (!allowed.some(re => re.test(file.path)) || /(?:^|\/)(?:\.env|\.npmrc|private|runtime|node_modules|__pycache__)(?:\/|$)/.test(file.path)) {
    throw new Error('Unexpected package file: ' + file.path);
  }
  const text = fs.readFileSync(path.join(root, file.path), 'utf8');
  if (/-----BEGIN (?:OPENSSH |RSA |EC )?PRIVATE KEY-----|\bnpm_[A-Za-z0-9]{30,}\b/.test(text)) {
    throw new Error('Credential-like material in ' + file.path);
  }
}
for (const file of required) if (!names.has(file)) throw new Error('Missing runtime file: ' + file);
if (pack.unpackedSize > 2 * 1024 * 1024) throw new Error('Package grew beyond the 2 MiB review limit');
if (['preinstall', 'install', 'postinstall'].some(name => pkg.scripts?.[name])) throw new Error('Install lifecycle hooks are forbidden');
console.log(JSON.stringify({ name: pack.name, version: pack.version, files: pack.files.length,
  compressed_bytes: pack.size, unpacked_bytes: pack.unpackedSize, install_hooks: false }, null, 2));
