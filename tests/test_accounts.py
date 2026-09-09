import copy
import json
from pathlib import Path
import unittest
from accounts import upgrade, request, transition
from fleet import validate, edge_files, bundle
from lazytunnel import public_key


class AccountTests(unittest.TestCase):
    def setUp(self):
        c=json.loads((Path(__file__).resolve().parents[1]/'examples/two-peers.json').read_text())
        for p in c['peers']:p['platform']='linux'
        self.legacy=copy.deepcopy(c)
        self.c=upgrade(c)
        self.c['accounts']['alice']={'enabled':True,'login_keys':[],'password_auth':True}
        self.c['accounts']['bob']={'enabled':True,'login_keys':[],'password_auth':True}
        self.c['peers'][0]['account']='alice';self.c['peers'][1]['account']='bob'
        for p in self.c['peers']:p['aliases']=['laptop']

    def test_legacy_upgrade_retains_identity_and_routes(self):
        old=edge_files(self.legacy);new=edge_files(upgrade(self.legacy))
        for k,v in old.items():
            if k.startswith('keys/'):self.assertEqual(new[k],v)
        self.assertEqual(transition(self.legacy,upgrade(self.legacy)),[])

    def test_device_inventory_bundles_and_keys_are_isolated(self):
        validate(self.c)
        alice,bob=self.c['peers'];b=bundle(self.c,alice['name'])
        self.assertNotIn(bob['name'],b['aliases'])
        text=json.dumps(b)
        for field in ('host_key','login_key','tunnel_key','jump_key'):
            self.assertNotIn(bob[field],text)
        policy=edge_files(self.c)['keys/lf-hop-'+alice['name']]
        self.assertNotIn(str(bob['relay_port']),policy)
        self.assertIn(str(alice['relay_port']),policy)

    def test_account_login_has_no_shell_or_forwarding(self):
        text=edge_files(self.c)['70-lazytunnel-fleet.conf']
        block=text.split('Match User lf-acct-alice\n')[1].split('Match User ')[0]
        self.assertIn('AllowTcpForwarding no',block)
        self.assertIn('PermitTTY no',block)
        self.assertIn('ForceCommand /usr/bin/sudo -n ',block)

    def test_owner_is_derived_from_authentication_not_message(self):
        before=copy.deepcopy(self.c)
        for m in ({'version':1,'op':'devices','account':'bob'}, {'version':1,'op':'shell','command':'id'},
                  {'version':1,'op':'revoke','device':self.c['peers'][1]['name']}):
            with self.assertRaises(ValueError):request(self.c,'alice',m)
        self.assertEqual(before,self.c)

    def test_disable_and_revoke_remove_keys_and_only_end_affected_sessions(self):
        new,reply=request(self.c,'alice',{'version':1,'op':'revoke','device':'laptop'})
        alice,bob=self.c['peers'];files=edge_files(new)
        self.assertEqual(files['keys/lf-hop-'+alice['name']],'')
        self.assertTrue(files['keys/lf-hop-'+bob['name']])
        stops=transition(self.c,new)
        self.assertIn('lf-hop-'+alice['name'],stops)
        self.assertFalse(any(bob['name'] in user for user in stops))
        new['accounts']['bob']['enabled']=False
        with self.assertRaises(ValueError):request(new,'bob',{'version':1,'op':'devices'})
        with self.assertRaises(ValueError):bundle(new,bob['name'])

    def test_account_moves_and_implicit_deletion_are_refused(self):
        for change in ('owner','remove','login_key','downgrade'):
            c=copy.deepcopy(self.c)
            if change=='owner':c['peers'][0]['account']='default'
            if change=='remove':c['peers'].pop()
            if change=='login_key':c['peers'][0]['login_key']=self.legacy['edge']['host_key']
            if change=='downgrade':c=self.legacy
            with self.assertRaises(ValueError):transition(self.c,c)

    def test_repeat_enrollment_is_idempotent_and_cannot_claim_another_owner(self):
        peer=self.c['peers'][0]
        packet={k:v for k,v in peer.items() if k not in ('account','relay_port','aliases','external_carrier')}
        packet['name']='laptop'
        same,response=request(self.c,'alice',{'version':1,'op':'enroll','peer':packet})
        self.assertEqual(same,self.c)
        self.assertEqual(response['bundle']['peer']['name'],peer['name'])
        with self.assertRaises(ValueError):request(self.c,'bob',{'version':1,'op':'enroll','peer':packet})

    def test_canonical_keys_prevent_whitespace_identity_aliases(self):
        key=self.c['peers'][0]['login_key']
        for wrong in (key+'\n',key.replace(' ','\t'),key.replace(' ','  ')):
            with self.assertRaises(ValueError):public_key(wrong)

    def test_metadata_cannot_amplify_unbounded_ssh_configuration(self):
        for field,value in [('home','/home/'+'x'*257),('hostname','x'*254),('aliases',['a']*17)]:
            c=copy.deepcopy(self.c);c['peers'][0][field]=value
            with self.assertRaises(ValueError):validate(c)


if __name__=='__main__':unittest.main()
