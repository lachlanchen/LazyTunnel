import copy
import importlib.util
import unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from fleet import validate,edge_files,worker_files
import json


class FleetTests(unittest.TestCase):
    def setUp(self):
        self.c=json.loads((Path(__file__).resolve().parents[1]/'examples/two-peers.json').read_text())
        for p in self.c['peers']:p['platform']='linux'
    def test_legacy_owner_not_replaced(self):
        self.c['peers'][0]['external_carrier']=True
        files=edge_files(validate(self.c))
        name=self.c['peers'][0]['name']
        self.assertNotIn('keys/lf-tun-'+name,files)
        self.assertIn('keys/lf-hop-'+name,files)
        self.assertNotIn('lazytunnel-fleet.service',worker_files(self.c,name))
    def test_cloud_restricts_each_tunnel_to_one_loopback_port(self):
        files=edge_files(validate(self.c))
        for p in self.c['peers']:
            key=files['keys/lf-tun-'+p['name']]
            self.assertIn('permitlisten="127.0.0.1:'+str(p['relay_port'])+'"',key)
            self.assertNotIn('permitopen=',key)
        self.assertIn('MaxSessions 0',files['70-lazytunnel-fleet.conf'])
        self.assertNotIn('0.0.0.0',files['70-lazytunnel-fleet.conf'])
    def test_duplicate_ports_aliases_and_identity_rejected(self):
        for field in ('relay_port','login_key','host_key'):
            c=copy.deepcopy(self.c);c['peers'][1][field]=c['peers'][0][field]
            with self.assertRaises(ValueError):validate(c)
        self.c['peers'][1]['aliases']=[self.c['peers'][0]['name']]
        with self.assertRaises(ValueError):validate(self.c)
    def test_native_platform_supervision(self):
        p=self.c['peers'][0]
        p['platform']='darwin';p['home']='/Users/demo'
        f=worker_files(validate(self.c),p['name'])
        import plistlib
        plist=plistlib.loads(f['art.lazying.lazytunnel-fleet.plist'].encode())
        self.assertEqual(plist['UserName'],p['user'])
        self.assertTrue(plist['KeepAlive'])
        p['platform']='windows';p['home']='C:/Users/demo'
        f=worker_files(validate(self.c),p['name'])
        self.assertIn('exit 1',f['carrier.ps1'])
        self.assertIn('C:/Windows/System32/OpenSSH/ssh.exe',f['ssh_config'])

    def test_registry_has_no_shell_or_forwarding(self):
        c=validate(self.c);files=edge_files(c)
        name=c['peers'][0]['name']
        block=files['70-lazytunnel-fleet.conf'].split('Match User lf-info-'+name+'\n')[1].split('Match User ')[0]
        self.assertIn('MaxSessions 1',block)
        self.assertNotIn('MaxSessions 0',block)
        self.assertIn('ForceCommand /bin/cat /etc/lazytunnel-fleet/bundles/'+name+'.json',block)
        self.assertIn('AllowTcpForwarding no',block)
        self.assertTrue(files['keys/lf-info-'+name].startswith('restrict ssh-ed25519 '))
        b=json.loads(files['bundles/'+name+'.json'])
        self.assertEqual(b['peer']['name'],name)
        self.assertIn('Host lazy-fleet-registry',b['files']['ssh_config'])

    def test_secret_fields_are_rejected(self):
        for target in ('edge','peer'):
            c=copy.deepcopy(self.c)
            obj=c['edge'] if target=='edge' else c['peers'][0]
            obj['password']='not-a-real-secret'
            with self.assertRaises(ValueError):validate(c)


if __name__=='__main__':unittest.main()
