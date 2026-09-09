#!/usr/bin/env node
// Adapted from LazyNPM's exact-artifact release pattern. No credential storage.
import { createHash } from 'node:crypto';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';

const args = process.argv.slice(2);
if (args.some(arg => !['--publish', '--provenance'].includes(arg))) throw new Error('Use --publish and optionally --provenance; default is preparation only.');
const pkg = JSON.parse(fs.readFileSync('package.json', 'utf8'));
const cli = process.env.npm_execpath;
const npmCommand = cli ? process.execPath : 'npm';
const npmPrefix = cli ? [cli] : [];
function run(command, argv, options = {}) {
  const result = spawnSync(command, argv, { encoding: 'utf8', ...options });
  if (result.status !== 0) throw new Error(`${path.basename(command)} ${argv[0] ?? ''} failed (${result.status ?? result.error?.code}); nothing will be retried automatically.`);
  return result;
}
function npm(argv, options) { return run(npmCommand, [...npmPrefix, ...argv], options); }
async function registry() {
  const response = await fetch(`https://registry.npmjs.org/${encodeURIComponent(pkg.name)}/${encodeURIComponent(pkg.version)}`,
    { redirect: 'error', signal: AbortSignal.timeout(15000) });
  if (response.status === 404) return null;
  if (!response.ok) throw new Error(`Registry HTTP ${response.status}`);
  return response.json();
}
function exact(doc, integrity) {
  if (doc.name !== pkg.name || doc.version !== pkg.version || doc.dist?.integrity !== integrity) {
    throw new Error('Existing registry version has different bytes or identity. Refusing to overwrite or claim success.');
  }
}
if (pkg.private || pkg.name !== '@lazyingart/lazytunnel' || !/^\d+\.\d+\.\d+(?:-[a-zA-Z0-9.-]+)?$/.test(pkg.version)) throw new Error('Unexpected package identity');
if (run('git', ['status', '--porcelain']).stdout.trim()) throw new Error('Commit the intended changes before preparing a release.');
npm(['test'], { stdio: 'inherit' });
npm(['run', 'test:core'], { stdio: 'inherit' });
npm(['run', 'verify:package'], { stdio: 'inherit' });
const temporary = fs.mkdtempSync(path.join(os.tmpdir(), 'lazytunnel-release-'));
try {
  const packed = JSON.parse(npm(['pack', '--json', '--ignore-scripts', '--pack-destination', temporary]).stdout);
  if (packed.length !== 1) throw new Error('Expected exactly one package');
  const tarball = path.join(temporary, path.basename(packed[0].filename));
  const integrity = 'sha512-' + createHash('sha512').update(fs.readFileSync(tarball)).digest('base64');
  const existing = await registry();
  if (existing) {
    exact(existing, integrity);
    console.log(`Verified identical existing ${pkg.name}@${pkg.version}; no publish performed.`);
  } else if (!args.includes('--publish')) {
    console.log(`Prepared ${pkg.name}@${pkg.version}; use --publish for publication.\n${integrity}`);
  } else {
    const publish = ['publish', tarball, '--access', 'public', '--tag', pkg.version.includes('-') ? 'next' : 'latest'];
    if (args.includes('--provenance')) publish.push('--provenance');
    npm(publish, { stdio: 'inherit' });
    let document;
    for (let attempt = 0; attempt < 10; attempt++) {
      document = await registry();
      if (document) break;
      await new Promise(resolve => setTimeout(resolve, 3000));
    }
    if (!document) throw new Error('Upload returned success but registry version is not visible; inspect before retrying.');
    exact(document, integrity);
    console.log(`Published and byte-verified ${pkg.name}@${pkg.version}.`);
  }
} finally {
  fs.rmSync(temporary, { recursive: true, force: true });
}
