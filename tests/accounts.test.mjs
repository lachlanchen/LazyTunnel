import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {spawnSync} from 'node:child_process';
import {validateInvite,sshAccountArgs} from '../lib/accounts.mjs';

const fixture=JSON.parse(fs.readFileSync(new URL('../examples/two-peers.json',import.meta.url)));
const invite={version:1,account:'alice',edge:{...fixture.edge,port:22}};
test('account invitations pin identity and reject shell/SSH option injection',()=>{
  assert.equal(validateInvite(invite),invite);
  for(const change of [
    {...invite,account:'alice;id'}, {...invite,account:'-root'}, {...invite,password:'secret'},
    {...invite,edge:{...invite.edge,host:'-oProxyCommand=sh'}},
    {...invite,edge:{...invite.edge,host:'relay\nHost *'}},
    {...invite,edge:{...invite.edge,port:'22'}},
    {...invite,edge:{...invite.edge,port:65536}},
    {...invite,edge:{...invite.edge,host_key:invite.edge.host_key+'\n'}},
    {...invite,edge:{...invite.edge,host_key:'ssh-ed25519 '+'A'.repeat(68)}}
  ])assert.throws(()=>validateInvite(change));
});
test('account SSH has pinned keys, no forwarding or TTY, and literal arguments',()=>{
  for(const platform of ['linux','win32']){
    const args=sshAccountArgs(invite,'/private path/known_hosts',undefined,platform);
    assert.equal(args[1],platform==='win32'?'NUL':'/dev/null');
    for(const value of ['StrictHostKeyChecking=yes','ForwardAgent=no','ForwardX11=no','ClearAllForwardings=yes','GlobalKnownHostsFile=none'])assert.ok(args.includes(value));
    assert.ok(args.includes('UserKnownHostsFile=/private path/known_hosts'));
    assert.deepEqual(args.slice(-4),['-l','lf-acct-alice',invite.edge.host,'lazytunnel-account']);
  }
  const args=sshAccountArgs(invite,'/tmp/known','/private key/$(id)');
  assert.equal(args[args.indexOf('-i')+1],'/private key/$(id)');
});
test('account help works before enrollment, without Python or a network connection',()=>{
  for(const args of [['account','--help'],['login','--invite','unused.json','--help']]){
    const r=spawnSync(process.execPath,[new URL('../bin/lazytunnel-client.mjs',import.meta.url).pathname,...args],
      {encoding:'utf8',env:{...process.env,LAZYTUNNEL_PYTHON:'/nonexistent'}});
    assert.equal(r.status,0,r.stderr);assert.match(r.stdout,/pinned invitation/);
  }
});
