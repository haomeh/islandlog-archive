// Browser helper for list pages (R93). Usage: node list_browser.mjs <url> <user-agent> <config-json>
// It opens one list page, scrolls it slowly (or clicks a load-more button) and prints one JSON object.
// It prints {items, denied}. Each item has href, title, row (the short text of the list row) and hint (a date in the row markup). No article body leaves the page.
// config: { link: "regex for article hrefs", more: "css selector of a load-more button" | "",
//           max_steps: 60, delay_ms: 1200, stop_before: "YYYY-MM-DD" | "",
//           page_template: "URL with {page}" | "", last_page: 9000, light: true,  (page mode: one page load per step)
//           stop_probe: "regex on href with groups y, m, d" (page mode: stop when a page is older than stop_before)
//           row_selector: "css selector of one list row" | "",
//           deny: ["regex of URL paths that robots.txt disallows"] }
// The page may load only its own site. A request to another site or to a denied path is aborted and counted.
// Each scroll or click that loads data waits delay_ms: 1 request per second per host or less.
import { createRequire } from 'node:module'
import { writeFileSync } from 'node:fs'

const require = createRequire(import.meta.url)
const { chromium } = require('playwright')
const [url, userAgent, configText] = process.argv.slice(2)
if (!url || !userAgent) {
  console.error('usage: node list_browser.mjs <url> <user-agent> <config-json>')
  process.exit(2)
}
const config = Object.assign({ link: '', more: '', max_steps: 60, delay_ms: 1200, stop_before: '', deny: [], row_selector: '', partial: '', page_template: '', last_page: 9000, light: false, stop_probe: '' }, JSON.parse(configText || '{}'))
const delay = Math.max(1000, config.delay_ms)

const browser = await chromium.launch()
try {
  const context = await browser.newContext({ userAgent, javaScriptEnabled: true })
  const page = await context.newPage()
  const site = new URL(url).hostname.split('.').slice(-2).join('.')
  const denyRes = config.deny.map((d) => new RegExp(d))
  const denied = new Set()
  await page.route('**/*', (route) => {
    const req = route.request()
    const u = new URL(req.url())
    if (['image', 'media', 'font'].includes(req.resourceType())) return route.abort()
    // Page mode reads server-rendered lists: skip scripts and styles, so one page costs one request.
    if (config.light && ['stylesheet', 'script'].includes(req.resourceType())) return route.abort()
    if (!u.hostname.endsWith(site)) return route.abort()
    if (denyRes.some((re) => re.test(u.pathname + u.search))) {
      denied.add(u.pathname)
      return route.abort()
    }
    return route.continue()
  })
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 30000 })
  await page.waitForTimeout(delay)

  const collect = () => page.evaluate(([linkSource, rowSelector]) => {
    const re = new RegExp(linkSource)
    const out = []
    const seen = new Set()
    for (const a of document.querySelectorAll('a[href]')) {
      const href = a.href
      if (!re.test(href) || seen.has(href)) continue
      const title = (a.getAttribute('title') || a.textContent || '').replace(/\s+/g, ' ').trim()
      if (!title) continue
      seen.add(href)
      // The row is the closest list item or block. Keep 200 characters at most: it carries the time label.
      const rowEl = a.closest(rowSelector || 'li, article, tr, .item, .news-item, div') || a.parentElement
      const row = ((rowEl && rowEl.innerText) || '').replace(/\s+/g, ' ').trim().slice(0, 200)
      // hint: a date written inside the row markup, for example in a picture path. Only the date leaves the page.
      const hint = ((rowEl && rowEl.outerHTML.match(/20\d\d[\/-]\d\d[\/-]\d\d/)) || [''])[0]
      out.push({ href, title: title.slice(0, 200), row, hint })
    }
    return out
  }, [config.link, config.row_selector])

  if (config.page_template) {
    const all = new Map()
    const probe = config.stop_probe ? new RegExp(config.stop_probe) : null
    const letters = { A: 10, B: 11, C: 12 }
    for (let pageNo = 1; pageNo <= Math.min(config.last_page, config.max_steps); pageNo++) {
      // Page 1 is already open (the start url).
      if (pageNo > 1) {
        await page.goto(config.page_template.replace('{page}', String(pageNo)), { waitUntil: 'domcontentloaded', timeout: 30000 })
      }
      const items = await collect()
      let added = 0
      for (const it of items) {
        if (!all.has(it.href)) { all.set(it.href, it); added += 1 }
      }
      if (!added) break
      if (probe && config.stop_before) {
        const dates = items.map((i) => {
          const m = i.href.match(probe)
          if (!m) return ''
          const mo = letters[m.groups.m] || Number(m.groups.m)
          return `${m.groups.y}-${String(mo).padStart(2, '0')}-${m.groups.d}`
        }).filter(Boolean)
        if (dates.length && dates.every((d) => d < config.stop_before)) break
      }
      if (config.partial && pageNo % 50 === 0) {
        writeFileSync(config.partial, JSON.stringify({ items: [...all.values()], denied: [...denied] }))
      }
      await page.waitForTimeout(delay)
    }
    process.stdout.write(JSON.stringify({ items: [...all.values()], denied: [...denied] }) + '\n')
    await browser.close()
    process.exit(0)
  }

  let lastCount = -1
  let stale = 0
  for (let step = 0; step < config.max_steps; step++) {
    const items = await collect()
    if (config.stop_before && items.length) {
      const dates = items.map((i) => ((i.row + ' ' + i.hint).match(/20\d\d[-/.]\d\d[-/.]\d\d/) || [''])[0].replace(/[/.]/g, '-')).filter(Boolean)
      if (dates.length && dates.every((d) => d < config.stop_before)) break
    }
    if (items.length === lastCount) {
      stale += 1
      if (stale >= 8) break
    } else {
      stale = 0
    }
    lastCount = items.length
    if (config.more) {
      const button = await page.$(config.more)
      if (!button) break
      await button.click().catch(() => {})
    } else {
      await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight))
    }
    await page.waitForTimeout(delay)
    if (config.partial && step % 50 === 49) {
      // A long run saves its rows now and then, so a crash loses little.
      writeFileSync(config.partial, JSON.stringify({ items: await collect(), denied: [...denied] }))
    }
  }
  process.stdout.write(JSON.stringify({ items: await collect(), denied: [...denied] }) + '\n')
} finally {
  await browser.close()
}
