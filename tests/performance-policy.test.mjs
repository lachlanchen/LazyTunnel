import { test } from 'node:test';
import assert from 'node:assert/strict';
import { performanceChoice, applyPerformance } from '../viewer/performance-policy.mjs';

test('explicit encoding parameters and per-viewer preferences are respected', () => {
    assert.equal(performanceChoice('', null), 'balanced');
    assert.equal(performanceChoice('', 'economy'), 'economy');
    assert.equal(performanceChoice('?quality=9', 'economy'), 'custom');
    assert.equal(performanceChoice('?compression=2', null), 'custom');
    assert.equal(performanceChoice('?performance=sharp', 'economy'), 'sharp');
    assert.equal(performanceChoice('?performance=unknown', 'unknown'), 'balanced');
    assert.equal(performanceChoice('?performance=constructor', '__proto__'), 'balanced');
});

test('only supported encoding preferences change, never input or resolution', () => {
    const rfb = {qualityLevel: 9, compressionLevel: 2, resizeSession: false,
                 scaleViewport: true, viewOnly: false};
    const original = {...rfb};
    applyPerformance(rfb, 'custom');
    applyPerformance(rfb, '__proto__');
    assert.deepEqual(rfb, original);
    applyPerformance(rfb, 'economy');
    assert.deepEqual(rfb, {...original, qualityLevel: 2, compressionLevel: 7});
    applyPerformance(rfb, 'balanced');
    assert.deepEqual(rfb, {...original, qualityLevel: 5, compressionLevel: 6});
    applyPerformance(rfb, 'sharp');
    assert.deepEqual(rfb, {...original, qualityLevel: 8, compressionLevel: 2});
    assert.doesNotThrow(() => applyPerformance(null, 'balanced'));
});
