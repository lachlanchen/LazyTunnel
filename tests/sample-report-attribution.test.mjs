import assert from 'node:assert/strict';
import test from 'node:test';
import fs from 'node:fs';

import { fitCheckHref } from '../website/sample-report.js';

const fallback =
  'https://lazying.art/lazyremote/fit-check/?utm_source=sample_report' +
  '&utm_medium=owned_proof&utm_campaign=lazyremote_network_review' +
  '&utm_content=complete_sample';

test('Chinese landing and sample keep the Chinese intake destination', () => {
  for (const name of ['index.html', 'sample-report.html']) {
    const html = fs.readFileSync(new URL(`../website/zh-Hans/${name}`, import.meta.url), 'utf8');
    const link = html.match(/href="(https:\/\/lazying\.art\/lazyremote\/fit-check\/[^\"]+)"/)[1].replaceAll('&amp;', '&');
    const result = new URL(fitCheckHref('?utm_source=github&utm_campaign=uu_remote_bridge&token=private', link));
    assert.equal(result.pathname, '/lazyremote/fit-check/zh-Hans/');
    assert.equal(result.searchParams.get('utm_source'), 'github');
    assert.equal(result.searchParams.get('utm_campaign'), 'uu_remote_bridge');
    assert.equal(result.searchParams.has('token'), false);
  }
});

test('landing pages load the shared bridge for both the sample and fit action', () => {
  for (const locale of ['', 'zh-Hans/']) {
    const html = fs.readFileSync(new URL(`../website/${locale}index.html`, import.meta.url), 'utf8');
    assert.match(html, /<script type="module" src="(?:\.\.\/)?sample-report\.js"><\/script>/);
    assert.match(html, /data-fit-check-link href="https:\/\/lazying\.art\/lazyremote\/fit-check\//);
    assert.match(html, /data-attribution-link href="sample-report\.html"/);
    const sample = fitCheckHref('?utm_source=github&utm_campaign=uu_remote_bridge&token=private', `https://remote.lazying.art/${locale}sample-report.html`);
    const fit = new URL(fitCheckHref(new URL(sample).search, `https://lazying.art/lazyremote/fit-check/${locale}`));
    assert.equal(fit.searchParams.get('utm_source'), 'github');
    assert.equal(fit.searchParams.get('utm_campaign'), 'uu_remote_bridge');
    assert.equal(fit.searchParams.has('token'), false);
  }
});

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
