#!/usr/bin/env node
// Optional headless acceptance checks; Playwright is not a build dependency.
// node scripts/test_browser.cjs URL [BASELINE_URL] [SCREENSHOT_DIRECTORY]
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {chromium} = require('playwright');
const locales = require('../site/locales.json');
const base = (process.argv[2] || 'http://127.0.0.1:8769').replace(/\/$/, '');
const baseline = process.argv[3]?.replace(/\/$/, '');
const shots = process.argv[4];

async function main() {
  const browser = await chromium.launch({headless: true});
  const downloads = new Set();
  let comparisons = 0;
  try {
    const context = await browser.newContext();
    const page = await context.newPage();
    const errors = [];
    page.on('pageerror', error => errors.push(String(error)));
    for (const theme of ['light', 'dark']) {
      await page.emulateMedia({colorScheme: theme, reducedMotion: 'reduce'});
      for (const width of [1440, 390]) {
        await page.setViewportSize({width, height: 1000});
        for (const locale of locales) {
          const label = `${locale}-${width}-${theme}`;
          assert.equal((await page.goto(`${base}/${locale}/`)).status(), 200, label);
          assert.equal(await page.locator('html').getAttribute('lang'), locale);
          assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), label);
          assert.equal(await page.locator('.languages a').count(), 31);
          assert.equal(await page.locator('.languages [aria-current="page"]').getAttribute('lang'), locale);
          const links = await page.locator('.release-download').evaluateAll(els => els.map(el => el.href));
          assert.equal(links.length, 3);
          assert(links[0].endsWith('/DolUnzip-0.1.0.dmg'));
          assert.equal(links[0], links[1]);
          assert(links[2].endsWith('/dz-0.1.0.pkg'));
          links.forEach(link => downloads.add(link));
          assert.equal(await page.locator('#download button:disabled').count(), 1);
          if (baseline && ['ko', 'en'].includes(locale)) {
            const current = await page.screenshot({fullPage: true, animations: 'disabled'});
            assert.equal((await page.goto(`${baseline}/${locale}/`)).status(), 200);
            const previous = await page.screenshot({fullPage: true, animations: 'disabled'});
            if (shots) {
              fs.mkdirSync(shots, {recursive: true});
              fs.writeFileSync(path.join(shots, `${label}-before.png`), previous);
              fs.writeFileSync(path.join(shots, `${label}-after.png`), current);
            }
            assert(current.equals(previous), `Screenshot differs: ${label}`);
            comparisons++;
            await page.goto(`${base}/${locale}/`);
          }
          const menu = page.locator('.languages');
          await menu.locator('summary').click();
          assert(await menu.evaluate(el => el.open));
          const box = await menu.locator('div').boundingBox();
          assert(box.x >= 0 && box.x + box.width <= width + 1, label);
          await page.keyboard.press('Escape');
          assert.equal(await menu.evaluate(el => el.open), false);
          assert(await menu.locator('summary').evaluate(el => el === document.activeElement));
          if (width === 390) {
            const nav = page.locator('.navigation');
            assert.equal(await nav.evaluate(el => el.open), false);
            await nav.locator('summary').click();
            assert(await nav.evaluate(el => el.open));
            await page.keyboard.press('Escape');
            assert.equal(await nav.evaluate(el => el.open), false);
          }
        }
        console.log(`PASS: 31 locale URLs, downloads and navigation, ${width}px ${theme}`);
      }
    }
    await page.goto(`${base}/ko/`);
    await page.locator('.languages summary').click();
    await page.locator('.languages a[lang="en"]').click();
    await page.waitForURL(`${base}/en/`);
    assert.equal(await page.locator('html').getAttribute('lang'), 'en');
    for (const [locale, expected] of [['en-US', 'en'], ['ko-KR', 'ko'], ['zh-TW', 'zh-Hant'], ['pt-BR', 'pt-BR'], ['nb-NO', 'nb']]) {
      const routing = await browser.newContext({locale});
      const tab = await routing.newPage();
      await tab.goto(`${base}/`);
      await tab.waitForURL(`${base}/${expected}/`);
      await routing.close();
    }
    const noJS = await browser.newContext({javaScriptEnabled: false});
    const fallback = await noJS.newPage();
    assert.equal((await fallback.goto(`${base}/`)).status(), 200);
    assert.equal(await fallback.locator('.language-grid a').count(), 31);
    await fallback.locator('.language-grid a[lang="ko"]').click();
    assert.equal(await fallback.locator('html').getAttribute('lang'), 'ko');
    await noJS.close();
    for (const url of downloads) {
      const response = await context.request.head(url);
      assert.equal(response.status(), 200, url);
      assert(Number(response.headers()['content-length']) > 0, url);
      console.log(`PASS: download HTTP 200: ${url.split('/').pop()}`);
    }
    assert.deepEqual(errors, []);
    console.log(`PASS: language routing and no-JS fallback; ${comparisons} identical before/after screenshots`);
  } finally {
    await browser.close();
  }
}
main().catch(error => { console.error(error); process.exitCode = 1; });
