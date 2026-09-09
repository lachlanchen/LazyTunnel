import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';

export function validateInvite(value) {
  const exact = (o, keys) => o && typeof o === 'object' && !Array.isArray(o)
    && Object.keys(o).sort().join(',') === [...keys].sort().join(',');
  if (!exact(value, ['version','account','edge']) || value.version !== 1
      || !/^[a-z][a-z0-9-]{0,19}$/.test(value.account)
      || !exact(value.edge, ['host','port','host_key'])
      || !/^[A-Za-z0-9][A-Za-z0-9.-]{0,252}$/.test(value.edge.host)
      || !Number.isInteger(value.edge.port) || value.edge.port < 1 || value.edge.port > 65535) {
    throw new Error('Invalid pinned account invitation');
  }
  const key=value.edge.host_key;
  if(typeof key !== 'string' || !/^ssh-ed25519 [A-Za-z0-9+/]{68}$/.test(key)) throw new Error('Invalid pinned server key');
  const bytes=Buffer.from(key.split(' ')[1],'base64');
  if(bytes.length!==51 || bytes.subarray(0,19).toString('hex')!=='0000000b7373682d6564323535313900000020') throw new Error('Invalid pinned server key');
  return value;
}

export function sshAccountArgs(invite, knownHosts, identity, platform=process.platform) {
  validateInvite(invite);
  return ['-F',platform==='win32'?'NUL':'/dev/null','-T','-p',String(invite.edge.port),
    '-o','HostKeyAlias=lazytunnel-account-edge','-o','UserKnownHostsFile='+knownHosts,
    '-o','GlobalKnownHostsFile=none','-o','StrictHostKeyChecking=yes','-o','IdentitiesOnly=yes',
    '-o','ForwardAgent=no','-o','ForwardX11=no','-o','ClearAllForwardings=yes',
    '-o','ConnectTimeout=10','-o','ConnectionAttempts=1','-o','NumberOfPasswordPrompts=2',
    ...(identity?['-i',path.resolve(identity)]:[]),
    '-l','lf-acct-'+invite.account,invite.edge.host,'lazytunnel-account'];
}

const help=`Account enrollment on your own relay (no public signup service)

  lazytunnel-client login --invite alice.json --name laptop [--identity account-key]
  lazytunnel-client account devices [--invite alice.json] [--identity account-key]
  lazytunnel-client account revoke laptop [--invite alice.json] [--identity account-key]

Obtain the pinned invitation from your relay administrator. OpenSSH asks for
your account password or uses the specified private account key. Passwords are
never saved. Account login enrolls this device, installs its scoped bundle and
starts its normal carrier. Other enrolled devices use sync to refresh the list.
One endpoint OS user has one active fleet identity; account transfers require
administrator review. A revocation ends affected SSH connections immediately.
`;

export function accountCommand(args, invocation) {
  const action=args[0];
  if(!action || args.some(a=>['--help','-h'].includes(a))){console.log(help);return;}
  if(!['login','devices','revoke'].includes(action)) throw new Error(help);
  const opts={};let device;
  for(let i=1;i<args.length;i++){
    const arg=args[i];
    if(['--invite','--name','--identity'].includes(arg)){
      if(!args[i+1] || args[i+1].startsWith('--') || opts[arg])throw new Error('Missing or duplicate option: '+arg);
      opts[arg]=args[++i];
    }else if(action==='revoke' && !device && !arg.startsWith('-'))device=arg;
    else throw new Error('Unexpected account argument: '+arg);
  }
  if(action==='revoke' && !device)throw new Error('Specify the device to revoke');
  const state=path.join(os.homedir(),'.config/lazytunnel-fleet');
  const invite=validateInvite(JSON.parse(fs.readFileSync(opts['--invite'] ?? path.join(state,'account.json'),'utf8')));
  const temp=fs.mkdtempSync(path.join(os.tmpdir(),'lazytunnel-account-'));fs.chmodSync(temp,0o700);
  const execute=(roleArgs, capture=true)=>{
    const cmd=invocation('client',roleArgs);
    const r=spawnSync(cmd.command,cmd.args,{stdio:['inherit',capture?'pipe':'inherit','inherit'],encoding:'utf8',maxBuffer:2*1024*1024});
    if(r.error || r.status!==0)throw new Error('Local client operation failed; current enrollment retained');
    return r.stdout;
  };
  try{
    let message={version:1,op:action==='login'?'enroll':action};
    if(action==='login'){
      const existing=path.join(state,'bundle.json');
      let old;
      if(fs.existsSync(existing)){
        old=JSON.parse(fs.readFileSync(existing,'utf8'));
        if((old.peer.account??'default')!==invite.account)throw new Error('This OS user is enrolled in another account; refusing an implicit transfer');
        if(!old.files.known_hosts.split('\n').includes('lazy-fleet-edge '+invite.edge.host_key)) throw new Error('Existing relay identity differs');
      }
      const name=opts['--name']??old?.peer.aliases?.[0]??old?.peer.name??os.hostname().toLowerCase().replace(/[^a-z0-9-]/g,'-').slice(0,20);
      message.peer=JSON.parse(execute(['prepare','--name',name]));
    }
    if(action==='revoke')message.device=device;
    const known=path.join(temp,'known_hosts');fs.writeFileSync(known,'lazytunnel-account-edge '+invite.edge.host_key+'\n',{mode:0o600});
    const ssh=process.platform==='win32'?path.join(process.env.SystemRoot??'C:\\Windows','System32/OpenSSH/ssh.exe'):'/usr/bin/ssh';
    const result=spawnSync(ssh,sshAccountArgs(invite,known,opts['--identity']),
      {input:JSON.stringify(message)+'\n',stdio:['pipe','pipe','inherit'],encoding:'utf8',timeout:120000,maxBuffer:2*1024*1024});
    let reply;
    try{reply=JSON.parse(result.stdout);}catch{throw new Error('Account connection failed; check credentials, server key and relay account support');}
    if(result.error || result.status!==0 || reply.ok!==true || reply.account!==invite.account) throw new Error('Account operation denied or failed');
    if(action==='login'){
      if(reply.bundle?.peer.account!==invite.account)throw new Error('Server returned another account’s bundle');
      const candidate=path.join(temp,'bundle.json');fs.writeFileSync(candidate,JSON.stringify(reply.bundle),{mode:0o600});
      execute(['login','--bundle',candidate],false);
      const saved=path.join(state,'account.json');
      if(fs.existsSync(saved) && fs.lstatSync(saved).isSymbolicLink())throw new Error('Refusing linked account invitation');
      const pending=path.join(state,'.account-'+process.pid+'.json');
      fs.writeFileSync(pending,JSON.stringify(invite,null,2)+'\n',{mode:0o600,flag:'wx'});fs.renameSync(pending,saved);
      console.log('Enrolled account: '+invite.account+'. Existing devices: run lazytunnel-client sync.');
    }else console.log(JSON.stringify(reply,null,2));
  }finally{fs.rmSync(temp,{recursive:true,force:true});}
}
