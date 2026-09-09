import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { invocation, root, pythonExecutable } from '../lib/cli.mjs';

test('client and server select their own backend without a shell', () => {
  for (const role of ['client', 'server']) {
    const got = invocation(role, ['install'], { platform: 'linux', python: '/usr/bin/python3' });
    assert.equal(got.command, '/usr/bin/python3');
    assert.deepEqual(got.args, [path.join(root, 'scripts', `lazytunnel-${role}.py`), 'install', '--no-launcher']);
  }
});
test('paths and remote command arguments remain individual literal arguments', () => {
  const args = ['ssh', 'alpha', 'printf', '%s', 'space ; $HOME $(not-a-command)'];
  const got = invocation('client', args, { platform: 'darwin', python: '/opt/Python With Space/python3' });
  assert.equal(got.command, '/opt/Python With Space/python3');
  assert.deepEqual(got.args.slice(1), args);
});
test('Windows uses installed PowerShell, ships its backend and preserves paths', () => {
  const got = invocation('client', ['login', '--bundle', 'C:\\Users\\Demo User\\private\\bundle.json'],
    { platform: 'win32', root: 'C:\\Program Files\\LazyTunnel', env: { SystemRoot: 'C:\\Windows' } });
  assert.equal(got.command, 'C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe');
  assert.equal(got.args[5], 'C:\\Program Files\\LazyTunnel\\scripts\\lazytunnel.ps1');
  assert.deepEqual(got.args.slice(6), ['login', '-Bundle', 'C:\\Users\\Demo User\\private\\bundle.json']);
});
test('Windows npm installation does not overwrite launchers and web arguments map', () => {
  const opts = { platform: 'win32', root: 'C:\\npm\\package', env: {} };
  const install = invocation('client', ['update'], opts);
  assert.deepEqual(install.args.slice(-3), ['-Source', 'C:\\npm\\package\\scripts', '-NoLauncher']);
  const web = invocation('client', ['web', 'alpha', '6080', '--local-port', '16080'], opts);
  assert.deepEqual(web.args.slice(6), ['web', '-Device', 'alpha', '-Port', '6080', '-LocalPort', '16080']);
});
test('unsupported server and controller platforms fail clearly', () => {
  assert.throws(() => invocation('server', ['install'], { platform: 'win32' }), /requires Linux/);
  assert.throws(() => invocation('client', ['gui'], { platform: 'win32' }), /controller service/);
});
test('--version works without Python and every public bin agrees', () => {
  const expected = JSON.parse(fs.readFileSync(path.join(root, 'package.json'))).version;
  for (const bin of ['lazytunnel', 'lazytunnel-client', 'lazytunnel-server']) {
    const got = spawnSync(process.execPath, [path.join(root, 'bin', bin + '.mjs'), '--version'],
      { encoding: 'utf8', env: { ...process.env, LAZYTUNNEL_PYTHON: '/does/not/exist' } });
    assert.equal(got.status, 0, got.stderr);
    assert.equal(got.stdout.trim(), expected);
  }
});
test('missing Python and failed backend preserve failure exit codes', { skip: process.platform === 'win32' }, () => {
  const bin = path.join(root, 'bin/lazytunnel.mjs');
  const missing = spawnSync(process.execPath, [bin, 'status'], { encoding: 'utf8',
    env: { ...process.env, LAZYTUNNEL_PYTHON: '/does/not/exist' } });
  assert.equal(missing.status, 1);
  assert.match(missing.stderr, /Python 3.9/);
  const bad = spawnSync(process.execPath, [bin, 'unknown-command'], { encoding: 'utf8' });
  assert.equal(bad.status, 2);
});
test('install twice into an isolated home preserves credentials and launcher bytes', { skip: process.platform === 'win32' }, () => {
  const home = fs.mkdtempSync(path.join(os.tmpdir(), 'lazytunnel npm home '));
  try {
    fs.mkdirSync(path.join(home, '.config/lazytunnel-fleet'), { recursive: true });
    fs.writeFileSync(path.join(home, '.config/lazytunnel-fleet/fixture'), 'private existing state');
    fs.mkdirSync(path.join(home, '.local/bin'), { recursive: true });
    fs.writeFileSync(path.join(home, '.local/bin/lazytunnel'), 'existing launcher\n');
    fs.writeFileSync(path.join(home, '.bashrc'), 'existing profile\n');
    const command = [path.join(root, 'bin/lazytunnel.mjs'), 'install'];
    for (let i = 0; i < 2; i++) {
      const got = spawnSync(process.execPath, command, { encoding: 'utf8', env: { ...process.env, HOME: home } });
      assert.equal(got.status, 0, got.stderr);
    }
    assert.equal(fs.readFileSync(path.join(home, '.local/bin/lazytunnel'), 'utf8'), 'existing launcher\n');
    assert.equal(fs.readFileSync(path.join(home, '.bashrc'), 'utf8'), 'existing profile\n');
    assert.equal(fs.readFileSync(path.join(home, '.config/lazytunnel-fleet/fixture'), 'utf8'), 'private existing state');
    assert.equal(fs.existsSync(path.join(home, '.profile')), false);
    const code = path.join(home, '.local/share/lazytunnel/client/current');
    assert.ok(fs.existsSync(path.join(code, 'lazytunnel_core/agent.py')));
    assert.ok(fs.existsSync(path.join(code, 'gui/index.html')));
    assert.equal(fs.readdirSync(path.join(home, '.local/share/lazytunnel/client/releases')).length, 1);
    const got = spawnSync(pythonExecutable(), [path.join(code, 'scripts/lazytunnel-client.py'), '--help'], { encoding: 'utf8' });
    assert.equal(got.status, 0, got.stderr);
  } finally { fs.rmSync(home, { recursive: true, force: true }); }
});
test('server install preview requires no root and does not activate policy', { skip: process.platform !== 'linux' }, () => {
  const got = spawnSync(process.execPath, [path.join(root, 'bin/lazytunnel-server.mjs'), 'install'], { encoding: 'utf8' });
  assert.equal(got.status, 0, got.stderr);
  assert.match(got.stdout, /Server code release:/);
  assert.doesNotMatch(got.stdout, /Code updated/);
});
