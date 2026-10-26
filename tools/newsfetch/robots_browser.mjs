// Browser helper that reads one robots.txt (R108). Usage: node robots_browser.mjs <robots-url> <user-agent>
// It prints one JSON object: {status, body}. status is null when the browser cannot load the page (for example a TLS error).
// TLS checks stay on. The caller fails closed on any status other than 200, 404 and 410.
import { createRequire } from 'node:module'

const require = createRequire(import.meta.url)
const { chromium } = require('playwright')
const [url, userAgent] = process.argv.slice(2)
if (!url || !userAgent) {
  console.error('usage: node robots_browser.mjs <robots-url> <user-agent>')
  process.exit(2)
}

const browser = await chromium.launch()
let result = { status: null, body: '' }
try {
  const context = await browser.newContext({ userAgent })
  const response = await context.request.get(url, { timeout: 30000, maxRedirects: 0 })
  result = { status: response.status(), body: response.status() === 200 ? await response.text() : '' }
} catch (err) {
  result = { status: null, body: '', error: String(err.message || err).slice(0, 200) }
} finally {
  await browser.close()
}
process.stdout.write(JSON.stringify(result) + '\n')
