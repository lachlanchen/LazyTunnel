import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawn, spawnSync } from 'node:child_process';

export const root = fileURLToPath(new URL('../', import.meta.url));
const metadata = JSON.parse(fs.readFileSync(new URL('../package.json', import.meta.url), 'utf8'));
const pythonProbe = 'import sys; print(sys.executable); sys.exit(0 if sys.version_info >= (3,9) else 1)';

export function pythonExecutable(env = process.env) {
  const candidates = env.LAZYTUNNEL_PYTHON ? [env.LAZYTUNNEL_PYTHON] : ['/usr/bin/python3', 'python3'];
  for (const candidate of candidates) {
    const result = spawnSync(candidate, ['-c', pythonProbe], { env, encoding: 'utf8', timeout: 5000 });
    if (!result.error && result.status === 0) return result.stdout.trim();
  }
  throw new Error('Python 3.9+ is required. Install it normally, or set LAZYTUNNEL_PYTHON to its executable path.');
}

const help = `LazyTunnel ${metadata.version} — private SSH fleet and optional LazyRemote interfaces

  lazytunnel [client] <command> [options]
  lazytunnel server <command> [options]
  lazytunnel-client <command> [options]
  lazytunnel-server <command> [options]

Client: install, update, prepare, login, sync, status, devices, boot, ssh, web
Accounts: login --invite ACCOUNT.json --name DEVICE; account devices; account revoke DEVICE
Linux controller: agent, gui
Server (Linux): install, update, apply, enroll, export, status, devices, account

  lazytunnel install                      Install persistent client code only
  lazytunnel prepare --name alpha         Prepare public enrollment packet
  lazytunnel login --bundle /private/alpha-bundle.json
  lazytunnel ssh beta hostname
  lazytunnel server install               Preview server code installation
  sudo lazytunnel server install --apply  Install persistent server code only
  lazytunnel doctor                       Inspect local prerequisites
  lazytunnel client --help                Detailed platform client options
  lazytunnel server --help                Detailed server options

npm install/update does not enroll devices, change SSH policy or start services.
Persistent code is independent of the npm directory; credentials remain private.
Documentation: https://github.com/lachlanchen/LazyTunnel/blob/main/docs/npm.md`;

export function invocation(role, args, options = {}) {
  const platform = options.platform ?? process.platform;
  const packageRoot = options.root ?? root;
  const env = options.env ?? process.env;
  if (!['client', 'server'].includes(role)) throw new Error('Unknown command role');
  if (role === 'server' && platform !== 'linux') throw new Error('The relay server requires Linux and OpenSSH. Run this command on your cloud server.');
  if (!['linux', 'darwin', 'win32'].includes(platform)) throw new Error('Supported clients: Linux, macOS and Windows.');
  const installing = ['install', 'update'].includes(args[0]);
  if (platform === 'win32') {
    if (['agent', 'gui'].includes(args[0])) throw new Error('The controller service currently runs on Linux. Use the native Windows app to connect to it.');
    const mapped = args.map(arg => ({ '--name': '-Name', '--bundle': '-Bundle', '--source': '-Source',
      '--device': '-Device', '--output': '-Output', '--port': '-Port', '--local-port': '-LocalPort', '--path': '-Path' }[arg] ?? arg));
    if (['ssh', 'web'].includes(mapped[0]) && mapped[1] && !mapped[1].startsWith('-')) mapped.splice(1, 0, '-Device');
    if (mapped[0] === 'web' && /^\d+$/.test(mapped[3] ?? '')) mapped.splice(3, 0, '-Port');
    if (installing) {
      if (!mapped.some(arg => arg.toLowerCase() === '-source')) mapped.push('-Source', path.win32.join(packageRoot, 'scripts'));
      mapped.push('-NoLauncher');
    }
    const windows = env.SystemRoot || env.WINDIR || 'C:\\Windows';
    return { command: path.win32.join(windows, 'System32/WindowsPowerShell/v1.0/powershell.exe'),
      args: ['-NoLogo', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', path.win32.join(packageRoot, 'scripts/lazytunnel.ps1'), ...mapped] };
  }
  const command = options.python ?? pythonExecutable(env);
  const extra = [...args];
  if (installing) extra.push('--no-launcher');
  return { command, args: [path.join(packageRoot, 'scripts', `lazytunnel-${role}.py`), ...extra] };
}

export function run(inv, options = {}) {
  return new Promise(resolve => {
    const child = spawn(inv.command, inv.args, { stdio: 'inherit', shell: false, ...options });
    const handlers = new Map();
    for (const signal of ['SIGINT', 'SIGTERM', 'SIGHUP']) {
      const handler = () => child.kill(signal);
      handlers.set(signal, handler);
      process.on(signal, handler);
    }
    child.once('error', error => console.error(`LazyTunnel: cannot start ${path.basename(inv.command)} (${error.code ?? 'error'}).`));
    child.once('close', (code, signal) => {
      for (const [name, handler] of handlers) process.off(name, handler);
      resolve(code ?? (signal ? 128 + (os.constants.signals[signal] ?? 1) : 1));
    });
  });
}

function doctor() {
  const checks = { package: metadata.name, version: metadata.version, platform: process.platform, node: process.version };
  if (process.platform === 'win32') {
    const inv = invocation('client', []);
    checks.powershell = fs.existsSync(inv.command);
    checks.ssh = fs.existsSync(path.win32.join(process.env.SystemRoot || 'C:\\Windows', 'System32/OpenSSH/ssh.exe'));
    process.exitCode = checks.powershell && checks.ssh ? 0 : 1;
  } else {
    try { checks.python = pythonExecutable(); } catch { checks.python = 'missing Python 3.9+'; process.exitCode = 1; }
    checks.ssh = fs.existsSync('/usr/bin/ssh');
    checks.ssh_keygen = fs.existsSync('/usr/bin/ssh-keygen');
    if (!checks.ssh || !checks.ssh_keygen) process.exitCode = 1;
    checks.controller_service_supported = process.platform === 'linux';
  }
  console.log(JSON.stringify(checks, null, 2));
}

export async function main(fixedRole) {
  try {
    const args = process.argv.slice(2);
    let role = fixedRole ?? 'client';
    if (!fixedRole && ['client', 'server'].includes(args[0])) role = args.shift();
    if (['--version', '-v', 'version'].includes(args[0])) { console.log(metadata.version); return; }
    if (args[0] === 'doctor') { doctor(); return; }
    if (role==='client' && (args[0]==='account' || (args[0]==='login' && args.includes('--invite')))) {
      const {accountCommand}=await import('./accounts.mjs');
      accountCommand(args[0]==='account'?args.slice(1):args,invocation);return;
    }
    if (!args.length || (!fixedRole && process.argv[2] === '--help')) { console.log(help); return; }
    if (process.platform === 'win32' && ['--help', '-h'].includes(args[0])) { console.log(help); return; }
    process.exitCode = await run(invocation(role, args));
  } catch (error) {
    console.error('LazyTunnel: ' + error.message);
    process.exitCode = 1;
  }
}
