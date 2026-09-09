"""Account-scoped enrollment. Authentication belongs to OpenSSH, not JSON input."""
import copy
import hashlib
import json
import re
from fleet import validate, bundle, account_of, active, visible_peers
from lazytunnel import require


def upgrade(config):
    c = copy.deepcopy(validate(config))
    if c['version'] == 1:
        c.update(version=2, accounts={'default': dict(enabled=True, login_keys=[], password_auth=False)})
        for p in c['peers']: p['account'] = 'default'
    return validate(c)


def inventory(config, account):
    require(account in config.get('accounts', {}) and config['accounts'][account]['enabled'], 'Account unavailable')
    return [dict(name=p['name'], aliases=p.get('aliases', []), platform=p['platform'],
                 revoked=p.get('revoked', False)) for p in config['peers'] if account_of(p) == account]


def request(config, account, message, occupied=()):
    """Return (candidate, reply); caller derives account from authenticated Unix UID."""
    c = upgrade(config)
    inventory(c, account)
    require(type(message) is dict and message.get('version') == 1, 'Invalid request version')
    op = message.get('op')
    if op == 'devices':
        require(set(message) == {'version', 'op'}, 'Unexpected request fields')
        return c, {'account': account, 'devices': inventory(c, account)}
    if op == 'revoke':
        require(set(message) == {'version', 'op', 'device'} and type(message['device']) is str, 'Invalid revocation request')
        p = next((p for p in c['peers'] if account_of(p) == account
                  and message['device'] in [p['name']] + p.get('aliases', [])), None)
        require(p is not None, 'Device unavailable')
        require(not p.get('external_carrier'), 'Legacy carrier revocation requires its administrator')
        p['revoked'] = True
        return validate(c), {'account': account, 'revoked': p['name']}
    require(op == 'enroll' and set(message) == {'version', 'op', 'peer'}, 'Unsupported account operation')
    packet = message['peer']
    fields = {'name','user','home','platform','ssh_port','host_key','tunnel_key','jump_key','login_key'}
    require(type(packet) is dict and fields <= set(packet) <= fields | {'hostname'}, 'Invalid public enrollment packet')
    require(type(packet['name']) is str and re.fullmatch(r'[a-z0-9][a-z0-9-]{0,19}', packet['name']), 'Invalid device label')
    # IDs are globally unique while friendly aliases are private to an account.
    require(type(packet['login_key']) is str, 'Invalid login key')
    name = 'd' + hashlib.sha256((account+'\0'+packet['login_key']).encode()).hexdigest()[:19]
    existing = next((p for p in c['peers'] if p['login_key'] == packet['login_key']), None)
    if existing:
        require(account_of(existing) == account and active(c, existing), 'Identity unavailable; administrator review required')
        for field in fields - {'name'}:
            require(existing[field] == packet[field], 'Existing identity differs; administrator review required')
        require(packet['name'] in [existing['name']] + existing.get('aliases', []), 'Existing device label differs')
        return c, {'account': account, 'bundle': bundle(c, existing['name'])}
    require(sum(account_of(p) == account for p in c['peers']) < 32, 'Account device limit reached')
    used = {p['relay_port'] for p in c['peers']} | set(occupied) | {c['edge']['port']}
    available = next((n for n in range(23000, 24000) if n not in used), None)
    require(available is not None, 'Relay port pool exhausted')
    peer = dict(packet, name=name, aliases=[packet['name']], account=account,
                relay_port=available, external_carrier=False, revoked=False)
    c['peers'].append(peer)
    validate(c)
    return c, {'account': account, 'bundle': bundle(c, name)}


def transition(previous, candidate):
    """Disallow implicit identity moves; return only identities whose sessions must end."""
    validate(candidate)
    if previous is None: return []
    validate(previous)
    require(previous['edge'] == candidate['edge'], 'Relay identity migration requires administrator review')
    if previous['version'] == 2:
        require(candidate['version'] == 2, 'Account isolation cannot be downgraded')
        require(set(previous['accounts']) <= set(candidate['accounts']), 'Disable accounts instead of removing their ownership history')
    new = {p['name']: p for p in candidate['peers']}
    disconnect = set()
    for p in previous['peers']:
        require(p['name'] in new, 'Revoke devices instead of removing their ownership history')
        q = new[p['name']]
        require(account_of(p) == account_of(q), 'Device account transfer requires explicit migration')
        for field in ('relay_port','host_key','tunnel_key','jump_key','login_key','external_carrier','user','home','platform','ssh_port'):
            require(p.get(field) == q.get(field), 'Identity or port migration requires review')
        if active(previous, p) and not active(candidate, q):
            require(not p.get('external_carrier'), 'Legacy carrier revocation requires its administrator')
            disconnect.update('lf-'+role+'-'+p['name'] for role in ('tun','hop','info'))
        if {x['name'] for x in visible_peers(previous,p)} - {x['name'] for x in visible_peers(candidate,q)}:
            disconnect.add('lf-hop-'+p['name'])
    for name, a in previous.get('accounts', {}).items():
        if a != candidate['accounts'][name]:
            disconnect.add('lf-acct-'+name)
    return sorted(disconnect)
