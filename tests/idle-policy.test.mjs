import {test} from 'node:test';
import assert from 'node:assert/strict';
import {IdlePolicy} from '../viewer/idle-policy.mjs';

test('visible idle pauses; real activity resets the deadline', () => {
    const p = new IdlePolicy({now:0});
    assert.equal(p.reason(119999),null);
    assert.equal(p.reason(120000),'idle');
    p.activity(119000);
    assert.equal(p.reason(120000),null);
    assert.equal(p.reason(239000),'idle');
});
test('hidden deadline also applies in keep-live mode', () => {
    const p = new IdlePolicy({now:0});
    p.keepLive = true;
    assert.equal(p.reason(1000000),null);
    p.visibility(true,1000000);
    assert.equal(p.reason(1009999),null);
    assert.equal(p.reason(1010000),'hidden');
    p.visibility(false,1010001);
    assert.equal(p.reason(1010001),null);
});
test('repeated hidden events cannot postpone disconnect', () => {
    const p = new IdlePolicy({now:0});
    p.visibility(true,1);
    p.visibility(true,9999);
    assert.equal(p.reason(10001),'hidden');
});
