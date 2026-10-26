// Test helper for test_click_routes.py: reads each fixture page with the row reader of the click route. No network.
// It sets the page content from a local file, so the browser sends no request. Prints {outlet: rows}.
import { createRequire } from 'node:module'
import { readFileSync } from 'node:fs'
import { readRowsOnPage } from './click_rules.mjs'

const require = createRequire(import.meta.url)
const { chromium } = require('playwright')
const feeds = JSON.parse(readFileSync(new URL('./feeds.json', import.meta.url), 'utf-8'))
const browser = await chromium.launch()
const out = {}
try {
  const page = await browser.newPage()
  for (const feed of feeds) {
    if (!feed.click_route) continue
    const html = readFileSync(new URL(`./fixtures/click/${feed.id}.html`, import.meta.url), 'utf-8')
    await page.route('**/*', (route) => route.abort())
    await page.setContent(html, { waitUntil: 'domcontentloaded' })
    out[feed.id] = await readRowsOnPage(page, feed.click_route)
  }
} finally {
  await browser.close()
}
process.stdout.write(JSON.stringify(out) + '\n')
