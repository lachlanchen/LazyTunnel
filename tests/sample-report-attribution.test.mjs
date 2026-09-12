import assert from 'node:assert/strict';
import test from 'node:test';

import { fitCheckHref } from '../website/sample-report.js';

const fallback =
  'https://lazying.art/lazyremote/fit-check/?utm_source=sample_report' +
  '&utm_medium=owned_proof&utm_campaign=lazyremote_network_review' +
  '&utm_content=complete_sample';

test('preserves the four reviewed inbound attribution fields', () => {
  const result = new URL(fitCheckHref(
    '?utm_source=github&utm_medium=readme&utm_campaign=uu_remote_bridge' +
      '&utm_content=network_review_sample_zh_hans&ignored=secret',
    fallback,
  ));

  assert.equal(result.origin + result.pathname, 'https://lazying.art/lazyremote/fit-check/');
  assert.equal(result.searchParams.get('utm_source'), 'github');
  assert.equal(result.searchParams.get('utm_medium'), 'readme');
  assert.equal(result.searchParams.get('utm_campaign'), 'uu_remote_bridge');
  assert.equal(result.searchParams.get('utm_content'), 'network_review_sample_zh_hans');
  assert.equal(result.searchParams.has('ignored'), false);
});

test('keeps the sample default when no valid attribution is supplied', () => {
  assert.equal(fitCheckHref('?email=private%40example.com', fallback), fallback);
  assert.equal(fitCheckHref('?utm_source=%3Cscript%3E', fallback), fallback);
});

test('forwards only valid fields and never copies unrelated query data', () => {
  const result = new URL(fitCheckHref(
    '?utm_source=github&utm_medium=%3Cbad%3E&utm_campaign=uu_remote_bridge' +
      '&token=do-not-forward',
    fallback,
  ));

  assert.equal(result.searchParams.get('utm_source'), 'github');
  assert.equal(result.searchParams.get('utm_campaign'), 'uu_remote_bridge');
  assert.equal(result.searchParams.has('utm_medium'), false);
  assert.equal(result.searchParams.has('utm_content'), false);
  assert.equal(result.searchParams.has('token'), false);
});
