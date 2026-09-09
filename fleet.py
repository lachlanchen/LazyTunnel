#!/usr/bin/env python3
"""Fleet renderer. Extends a relay without rewriting existing two-peer carriers."""
import json
import plistlib
import re
import shlex
from lazytunnel import public_key, require, port


def validate(c):
    require(set(c)=={'version','edge','peers'},'Unexpected fleet fields')
    require(c.get('version') == 1, 'Unsupported fleet version')
    e = c['edge']
    require(set(e)=={'host','port','host_key'},'Only public edge identity belongs in a fleet manifest')
    require(re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9.-]+', e['host']), 'Invalid relay host')
    port(e['port']); public_key(e['host_key'])
    require(1 <= len(c['peers']) <= 32, 'Configure 1–32 enrolled peers')
    names, ports, keys, hosts, aliases = set(), set(), set(), {e['host_key']}, set()
    for p in c['peers']:
        required={'name','user','home','platform','ssh_port','relay_port','host_key','tunnel_key','jump_key','login_key'}
        require(required.issubset(p) and set(p).issubset(required|{'hostname','aliases','external_carrier'}),
                'Unexpected peer fields: keep passwords and private keys outside enrollment packets')
        require(re.fullmatch(r'[a-z0-9][a-z0-9-]{0,19}', p['name']), 'Invalid peer name')
        require(p['name'] not in names, 'Duplicate peer name'); names.add(p['name'])
        require(p['platform'] in ('linux','darwin','windows'), 'Unsupported platform')
        require(re.fullmatch(r'[A-Za-z_][A-Za-z0-9_-]{0,30}', p['user']), 'Invalid user')
        require(p['user'] != 'root', 'Use a non-root endpoint user')
        require(re.fullmatch(r'(?:/|[A-Z]:/)[A-Za-z0-9_/.-]+', p['home']) and
                '..' not in p['home'].split('/'), 'Unsupported home path')
        port(p['relay_port'])
        require(p['relay_port'] not in ports and p['relay_port'] != e['port'], 'Duplicate port')
        ports.add(p['relay_port'])
        require(type(p['ssh_port']) is int and 1 <= p['ssh_port'] <= 65535, 'Invalid SSH port')
        public_key(p['host_key']); require(p['host_key'] not in hosts, 'Duplicate host key')
        hosts.add(p['host_key'])
        require(type(p.get('external_carrier',False)) is bool, 'Invalid carrier ownership')
        for alias in [p['name']] + p.get('aliases',[]):
            require(re.fullmatch(r'[a-z0-9][a-z0-9-]{0,30}', alias), 'Invalid alias')
            require(alias not in aliases, 'Duplicate alias'); aliases.add(alias)
        for role in ('tunnel','jump','login'):
            key = public_key(p[role+'_key'])
            require(key not in keys, 'Identities must be unique across hosts and roles'); keys.add(key)
    require(not keys.intersection(hosts), 'Host and client keys must be separate')
    return c


def edge_files(c):
    """Own a separate account namespace; never change legacy lt-* identities."""
    result, lines = {}, ['# LazyTunnel fleet. Does not replace legacy carrier policy.']
    for p in c['peers']:
        roles = ['hop','info'] if p.get('external_carrier') else ['tun','hop','info']
        for role in roles:
            account = 'lf-'+role+'-'+p['name']
            lines += ['Match User '+account,
                ' AuthenticationMethods publickey', ' PasswordAuthentication no',
                ' KbdInteractiveAuthentication no', ' PermitTTY no', ' X11Forwarding no',
                ' AllowAgentForwarding no', ' AllowStreamLocalForwarding no',
                ' PermitTunnel no', ' GatewayPorts no', ' MaxSessions 0',
                ' ForceCommand /usr/sbin/nologin', ' ClientAliveInterval 20',
                ' ClientAliveCountMax 3', ' AuthorizedKeysFile /etc/lazytunnel-fleet/keys/%u']
            if role == 'info':
                # A pinned SSH registry, readable only with this device's
                # enrollment key. No shell, arbitrary files or forwarding.
                # Override within this block by replacing its initial values;
                # sshd uses the first applicable value, not the last one.
                start=lines.index('Match User '+account)
                for i in range(start,len(lines)):
                    if lines[i]==' MaxSessions 0':lines[i]=' MaxSessions 1'
                    if lines[i]==' ForceCommand /usr/sbin/nologin':
                        lines[i]=' ForceCommand /bin/cat /etc/lazytunnel-fleet/bundles/'+p['name']+'.json'
                lines += [' AllowTcpForwarding no',' PermitListen none',' PermitOpen none']
                opts='restrict';key=p['jump_key']
            elif role == 'tun':
                dst = '127.0.0.1:'+str(p['relay_port'])
                lines += [' AllowTcpForwarding remote', ' PermitListen '+dst, ' PermitOpen none']
                opts='restrict,port-forwarding,permitlisten="'+dst+'"'
                key=p['tunnel_key']
            else:
                dsts=['127.0.0.1:'+str(q['relay_port']) for q in c['peers']]
                lines += [' AllowTcpForwarding local',' PermitListen none',' PermitOpen '+' '.join(dsts)]
                opts='restrict,port-forwarding,'+','.join('permitopen="'+d+'"' for d in dsts)
                key=p['jump_key']
            result['keys/'+account]=opts+' '+key+'\n'
            lines.append('')
    result['70-lazytunnel-fleet.conf']='\n'.join(lines+['Match all',''])
    for p in c['peers']:
        result['bundles/'+p['name']+'.json']=json.dumps(bundle(c,p['name']),indent=2)+'\n'
    return result


def worker_files(c, name):
    p=next(q for q in c['peers'] if q['name']==name)
    root=p['home']+'/.config/lazytunnel-fleet'
    windows=p['platform']=='windows'
    exe='C:/Windows/System32/OpenSSH/ssh.exe' if windows else '/usr/bin/ssh'
    # Keep the carrier on native OpenSSH. Windows interactive wrappers may use
    # Git OpenSSH for its reliable nested ProxyCommand under an SSH login.
    common=[' IdentitiesOnly yes',' BatchMode yes',' StrictHostKeyChecking yes',
            ' UserKnownHostsFile '+root+'/known_hosts',' GlobalKnownHostsFile none',
            ' PasswordAuthentication no',' KbdInteractiveAuthentication no',
            ' ForwardAgent no',' ForwardX11 no',' ControlMaster no',' ControlPath none',
            ' ConnectTimeout 10',' ConnectionAttempts 1',' ServerAliveInterval 20',
            ' ServerAliveCountMax 3',' UpdateHostKeys no']
    hop=['Host lazy-fleet-hop',' HostName '+c['edge']['host'],' Port '+str(c['edge']['port']),
         ' User lf-hop-'+name,' HostKeyAlias lazy-fleet-edge',
         ' IdentityFile '+root+'/jump_ed25519']+common+['']
    registry=['Host lazy-fleet-registry',' HostName '+c['edge']['host'],
         ' Port '+str(c['edge']['port']),' User lf-info-'+name,
         ' HostKeyAlias lazy-fleet-edge',' IdentityFile '+root+'/jump_ed25519',' RequestTTY no']+common+['']
    config=hop+registry
    for q in c['peers']:
        aliases=['lazy-'+s for s in [q['name']]+q.get('aliases',[])]
        config += ['Host '+' '.join(aliases),' HostName 127.0.0.1',' Port '+str(q['relay_port']),
                   ' User '+q['user'],' HostKeyAlias lazy-fleet-'+q['name'],
                   ' IdentityFile '+root+'/login_ed25519',
                   ' ProxyCommand "'+exe+'" -F "'+root+'/ssh_config" -W %h:%p lazy-fleet-hop']+common+['']
    config+=['Host *','']
    carrier=['Host lazy-fleet-carrier',' HostName '+c['edge']['host'],
             ' Port '+str(c['edge']['port']),' User lf-tun-'+name,
             ' HostKeyAlias lazy-fleet-edge',' IdentityFile '+root+'/tunnel_ed25519',
             ' ExitOnForwardFailure yes',' RequestTTY no',
             ' RemoteForward 127.0.0.1:'+str(p['relay_port'])+' 127.0.0.1:'+str(p['ssh_port'])]+common+['']
    result={'ssh_config':'\n'.join(config), 'carrier.conf':'\n'.join(carrier),
            'known_hosts':'\n'.join(['lazy-fleet-edge '+c['edge']['host_key']]+
              ['lazy-fleet-'+q['name']+' '+q['host_key'] for q in c['peers']])+'\n',
            'authorized_keys.append':'\n'.join(q['login_key']+' lazy-fleet-'+q['name'] for q in c['peers'])+'\n'}
    if not windows:
        result['scp-lazy']='#!/bin/sh\nexec /usr/bin/scp -F "'+root+'/ssh_config" "$@"\n'
        result['ssh-lazy']='''#!/bin/sh
# LazyTunnel fleet command; no shell reload required.
name=${0##*/}
if [ "$name" = ssh-lazy ]; then
  if [ "$#" -eq 0 ]; then echo 'Usage: ssh-lazy DEVICE [SSH arguments...]' >&2; exit 2; fi
  name=$1; shift
else
  name=${name#ssh-lazy-}
fi
case "$name" in *[!a-z0-9-]*|'') echo 'Invalid device name' >&2; exit 2;; esac
exec /usr/bin/ssh -F "'''+root+'''/ssh_config" "lazy-$name" "$@"
'''
    if not p.get('external_carrier'):
        if p['platform']=='linux':
            result['lazytunnel-fleet.service']='''[Unit]
Description=LazyTunnel fleet carrier
StartLimitIntervalSec=0
[Service]
ExecStart=/usr/bin/ssh -F '''+root+'''/carrier.conf -NT lazy-fleet-carrier
Restart=always
RestartSec=20
TimeoutStopSec=10
UMask=0077
NoNewPrivileges=yes
[Install]
WantedBy=default.target
'''
        elif p['platform']=='darwin':
            result['art.lazying.lazytunnel-fleet.plist']=plistlib.dumps({
                'Label':'art.lazying.lazytunnel-fleet','UserName':p['user'],
                'ProgramArguments':['/usr/bin/ssh','-F',root+'/carrier.conf','-NT','lazy-fleet-carrier'],
                'RunAtLoad':True,'KeepAlive':True,'ThrottleInterval':20,
                'StandardOutPath':root+'/carrier.log','StandardErrorPath':root+'/carrier.log',
                'ProcessType':'Background'}).decode()
        else:
            result['carrier.ps1']="& \"$env:WINDIR\\System32\\OpenSSH\\ssh.exe\" -F '"+root+"/carrier.conf' -NT lazy-fleet-carrier\nexit 1\n"
    return result


def bundle(c,name):
    validate(c)
    return {'peer':next(p for p in c['peers'] if p['name']==name),
            'aliases':[a for p in c['peers'] for a in [p['name']]+p.get('aliases',[])],
            'files':worker_files(c,name)}
