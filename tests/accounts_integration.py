"""Run ONLY in the disposable accounts test container; exercises real sshd/sudo."""
import json
import os
from pathlib import Path
import select
import socket
import subprocess
import tempfile
import threading
import time

assert os.getuid()==0 and Path('/.dockerenv').exists(), 'Disposable container required'
ROOT=Path('/src');STATE=Path('/var/lib/lazytunnel-fleet')
TEMP=Path(tempfile.mkdtemp(prefix='account-fixture-'))


def run(*args,ok=True,**kw):
    result=subprocess.run(args,capture_output=True,text=True,timeout=60,**kw)
    if ok and result.returncode:raise AssertionError(result.stderr+result.stdout)
    return result


def key(name):
    p=TEMP/name;run('ssh-keygen','-q','-t','ed25519','-N','','-f',str(p));return p


def pub(p):return ' '.join(Path(str(p)+'.pub').read_text().split()[:2])
def admin(*args,**kw):return run('python3',str(ROOT/'scripts/account-admin.py'),*args,**kw)
def ssh(user,identity=None,tail=(),password=None):
    args=['ssh','-T','-F','/dev/null','-o','StrictHostKeyChecking=yes','-o','GlobalKnownHostsFile=none',
          '-o','UserKnownHostsFile='+str(TEMP/'known_hosts'),'-o','ConnectTimeout=5','-o','IdentitiesOnly=yes']
    if password:args=['sshpass','-f',str(password)]+args
    else:args+=['-o','BatchMode=yes']
    if identity:args+=['-i',str(identity)]
    return args+list(tail)+['-l',user,'127.0.0.1']


def rpc(account,identity,message,ok=True,password=None):
    r=run(*ssh('lf-acct-'+account,identity,password=password),input=json.dumps(message)+'\n',ok=ok)
    if ok:
        value=json.loads(r.stdout);assert value['ok'],value;return value
    assert r.returncode!=0 or json.loads(r.stdout).get('ok') is False
    return r


class Echo:
    def __init__(self,port,label):
        self.socket=socket.socket();self.socket.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
        self.socket.bind(('127.0.0.1',port));self.socket.listen();self.label=label.encode()
        threading.Thread(target=self.accept,daemon=True).start()
    def accept(self):
        while True:
            c,_=self.socket.accept();threading.Thread(target=self.echo,args=(c,),daemon=True).start()
    def echo(self,c):
        with c:
            c.sendall(self.label+b'\n')
            while True:
                value=c.recv(1024)
                if not value:return
                c.sendall(value)


def peer(label):
    keys={role:key(label+'-'+role) for role in ('host','tunnel','jump','login')}
    packet={role+'_key':pub(value) for role,value in keys.items()}
    packet.update(name=label,user='demo',home='/home/demo',platform='linux',ssh_port=22)
    return packet,keys


def line(process):
    assert select.select([process.stdout],[],[],5)[0], 'Timed out waiting for SSH data'
    return process.stdout.readline().strip()


run('python3',str(ROOT/'scripts/lazytunnel-server.py'),'install','--apply')
host=' '.join(Path('/etc/ssh/ssh_host_ed25519_key.pub').read_text().split()[:2])
(TEMP/'known_hosts').write_text('127.0.0.1 '+host+'\n')
admin('init','--host','127.0.0.1','--port','22','--host-key-file','/etc/ssh/ssh_host_ed25519_key.pub','--apply')
alice=key('account-alice');bob=key('account-bob')
for name,identity in [('alice',alice),('bob',bob)]:admin('add',name,'--key-file',str(identity)+'.pub','--apply')
invitation=TEMP/'alice.json';admin('invite','alice','--output',str(invitation))
def cli(*args):
    return run('node',str(ROOT/'bin/lazytunnel-client.mjs'),'account',*args,'--invite',str(invitation),'--identity',str(alice))
assert json.loads(cli('devices').stdout)['devices']==[]
a,ak=peer('laptop');b,bk=peer('laptop-b');a2,a2k=peer('phone')
b['name']='laptop' # Same friendly label in different accounts is supported.
ar=rpc('alice',alice,{'version':1,'op':'enroll','peer':a})
br=rpc('bob',bob,{'version':1,'op':'enroll','peer':b})
a2r=rpc('alice',alice,{'version':1,'op':'enroll','peer':a2})
again=rpc('alice',alice,{'version':1,'op':'enroll','peer':a})
assert ar['bundle']['peer']['name']==again['bundle']['peer']['name']
assert b['host_key'] not in json.dumps(again)
assert len(rpc('alice',alice,{'version':1,'op':'devices'})['devices'])==2
assert len(rpc('bob',bob,{'version':1,'op':'devices'})['devices'])==1
rpc('alice',alice,{'version':1,'op':'devices','account':'bob'},ok=False)
rpc('alice',alice,{'version':1,'op':'enroll','peer':b},ok=False)
rpc('alice',alice,{'version':1,'op':'revoke','device':br['bundle']['peer']['name']},ok=False)
rpc('bob',alice,{'version':1,'op':'devices'},ok=False)

ap=ar['bundle']['peer'];bp=br['bundle']['peer'];a2p=a2r['bundle']['peer']
services=[Echo(p['relay_port'],label) for p,label in [(ap,'alice'),(bp,'bob'),(a2p,'phone')]]
denied=run(*ssh('lf-hop-'+ap['name'],ak['jump'],tail=['-W','127.0.0.1:'+str(bp['relay_port'])]),ok=False)
assert denied.returncode and 'administratively prohibited' in denied.stderr
denied=run(*ssh('lf-acct-alice',alice,tail=['-W','127.0.0.1:'+str(ap['relay_port'])]),ok=False)
assert denied.returncode
owned=run(*ssh('lf-info-'+ap['name'],ak['jump']))
assert b['host_key'] not in owned.stdout
rpc('alice',alice,{'version':1,'op':'shell','command':'cat /etc/shadow'},ok=False)

# A conflicting earlier Match must cause a complete rollback, including bundle
# ownership/modes and the manifest. Newly created inert users remain retryable.
before=(STATE/'manifest.json').read_bytes()
owned_path=Path('/etc/lazytunnel-fleet/bundles')/(ap['name']+'.json')
original=owned_path.stat();original_bytes=owned_path.read_bytes()
conflict=Path('/etc/ssh/sshd_config.d/01-test-conflict.conf')
conflict.write_text('Match User lf-acct-conflict\n ForceCommand /bin/sh\nMatch all\n')
conflict_key=key('account-conflict')
result=admin('add','conflict','--key-file',str(conflict_key)+'.pub','--apply',ok=False)
assert result.returncode and (STATE/'manifest.json').read_bytes()==before
assert owned_path.read_bytes()==original_bytes
assert (owned_path.stat().st_uid,owned_path.stat().st_mode)==(original.st_uid,original.st_mode)
conflict.unlink()
admin('add','conflict','--key-file',str(conflict_key)+'.pub','--apply')
assert rpc('conflict',conflict_key,{'version':1,'op':'devices'})['devices']==[]

connections=[]
try:
    for p,k,label in [(ap,ak,'alice'),(bp,bk,'bob')]:
        process=subprocess.Popen(ssh('lf-hop-'+p['name'],k['jump'],tail=['-W','127.0.0.1:'+str(p['relay_port'])]),
                                 stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,bufsize=1)
        connections.append(process);assert line(process)==label
    assert json.loads(cli('revoke','phone').stdout)['revoked']==a2p['name']
    connections[0].wait(timeout=5) # Old Alice hop permissions must not survive.
    connections[1].stdin.write('still-bob\n');connections[1].stdin.flush();assert line(connections[1])=='still-bob'
    denied=run(*ssh('lf-hop-'+a2p['name'],a2k['jump'],tail=['-W','127.0.0.1:'+str(a2p['relay_port'])]),ok=False)
    assert denied.returncode
    admin('disable','alice','--apply')
    rpc('alice',alice,{'version':1,'op':'devices'},ok=False)
    connections[1].stdin.write('bob-after-disable\n');connections[1].stdin.flush();assert line(connections[1])=='bob-after-disable'
finally:
    for p in connections:
        if p.poll() is None:p.terminate()
        p.wait(timeout=5)

password=TEMP/'password';password.write_text('fixture-'+os.urandom(16).hex());password.chmod(0o600)
admin('add','charlie','--password-file',str(password),'--apply')
assert rpc('charlie',None,{'version':1,'op':'devices'},password=password)['devices']==[]
admin('disable','charlie','--apply')
rpc('charlie',None,{'version':1,'op':'devices'},password=password,ok=False)
assert len(json.loads((STATE/'manifest.json').read_text())['peers'])==3
print('PASS: real Node CLI/OpenSSH key/password login, sudo UID ownership, idempotent enrollment, isolated lists/keys/SSH, denied spoofing, policy rollback, revocation and unaffected Bob connection')
