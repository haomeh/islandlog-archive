// Browser helper for list pages (R93). Usage: node list_browser.mjs <url> <user-agent> <config-json>
// It opens one list page, scrolls it slowly (or clicks a load-more button) and prints one JSON object.
// It prints {items, denied}. Each item has href, title, row (the short text of the list row) and hint (a date in the row markup). No article body leaves the page.
// config: { link: "regex for article hrefs", more: "css selector of a load-more button" | "",
//           max_steps: 60, delay_ms: 1200, stop_before: "YYYY-MM-DD" | "",
//           page_template: "URL with {page}" | "", last_page: 9000, light: true,  (page mode: one page load per step)
//           stop_probe: "regex on href with groups y, m, d" (page mode: stop when a page is older than stop_before)
//           row_selector: "css selector of one list row" | "",
//           title_selector: "css selector of the headline inside the link" | "" (R60: the link text may carry the lead paragraph),
//           request_cap: 20000 (requests per host per run), request_log: "path of the request log" | "",
//           deny: ["regex of URL paths that robots.txt disallows"],
//           mode: "click" (R179: act like a reader; the keys below apply to it only)
//           rows: "css selector of one list row", link_selector: "css selector of the link inside the row" | "",
//           date_selector: "css selector of the date element inside the row" (datetime or title attribute first, then text),
//           next: "css selector of the next-page or load-more control" | "", scroll_to: "css selector to scroll into view" | "",
//           next_text: "regex on the text of the control; picks one of several matches of next" | "",
//           scroll: true (scroll to the page bottom each step), wait_ms: 6000 (longest wait for new rows after one step), settle_ms: 5000 (wait after the first load),
//           allow_hosts: ["api host of another site that the list needs; its robots.txt decides"],
//           empty_limit: 3 (stop after this many steps in a row without a new row),
//           add_query: "name of a query key that the site script adds to its own links, for example chdtv" | "" (used with no_script),
//           no_script: true (a server-rendered list with a pager link: skip scripts, one request per page) }
// Every request that the browser sends passes the robots.txt of its host (fail closed) and then the R175 gate.
// The page may load only its own site. A request to another site or to a denied path is aborted and counted.
// Each scroll or click that loads data waits delay_ms: 1 request per second per host or less.
import { createRequire } from 'node:module'
import { writeFileSync, appendFileSync } from 'node:fs'
import { decide, createGate } from './browser_gate.mjs'
import { createRobotsGuard } from './robots_rules.mjs'
import { labelDate, stopReason, looksBlocked, readRowsOnPage } from './click_rules.mjs'

const require = createRequire(import.meta.url)
const { chromium } = require('playwright')
const [url, userAgent, configText] = process.argv.slice(2)
if (!url || !userAgent) {
  console.error('usage: node list_browser.mjs <url> <user-agent> <config-json>')
  process.exit(2)
}
const config = Object.assign({ link: '', more: '', max_steps: 60, delay_ms: 1200, stop_before: '', deny: [], row_selector: '', title_selector: '', request_cap: 20000, request_log: '', partial: '', page_template: '', last_page: 9000, light: false, stop_probe: '', mode: '', rows: '', link_selector: '', date_selector: '', next: '', next_text: '', scroll_to: '', scroll: false, wait_ms: 6000, settle_ms: 5000, no_script: false, add_query: '', empty_limit: 3, allow_hosts: [] }, JSON.parse(configText || '{}'))
const delay = Math.max(1000, config.delay_ms)

const browser = await chromium.launch()
try {
  const context = await browser.newContext({ userAgent, javaScriptEnabled: true })
  const page = await context.newPage()
  const site = new URL(url).hostname.split('.').slice(-2).join('.')
  const denyRes = config.deny.map((d) => new RegExp(d))
  const denied = new Set()
  // R175: only document, script, xhr and fetch pass; no Next.js data or prefetch; 1 request per 1.1 s per host on every request; a cap per host.
  const gate = createGate({ cap: config.request_cap, logFile: config.request_log, tag: 'list' })
  let capped = false
  // R61: the robots.txt of every host that the page talks to. The read counts against the gate of that host. Any failure gives disallow all.
  const guard = createRobotsGuard({
    token: userAgent.split('/')[0].toLowerCase(),
    readRobots: async (protocol, host) => {
      if (!(await gate.admit(host, '/robots.txt'))) return { status: null, body: '' }
      const response = await context.request.get(`${protocol}//${host}/robots.txt`, { timeout: 30000, maxRedirects: 0 })
      return { status: response.status(), body: response.status() === 200 ? await response.text() : '' }
    },
  })
  let robotsAborts = 0
  let offsite = 0
  await page.route('**/*', async (route) => {
    const req = route.request()
    const u = new URL(req.url())
    if (decide(req.resourceType(), req.url(), req.headers())) return route.abort()
    // Page mode reads server-rendered lists: skip scripts, so one page costs one request.
    if ((config.light || config.no_script) && req.resourceType() === 'script') return route.abort()
    // Another site is blocked, unless the route names it in allow_hosts (an API that the list needs). Then robots.txt of that host decides.
    if (!u.hostname.endsWith(site) && !config.allow_hosts.some((h) => u.hostname === h || u.hostname.endsWith('.' + h))) {
      offsite += 1
      return route.abort()
    }
    if (denyRes.some((re) => re.test(u.pathname + u.search))) {
      denied.add(u.pathname)
      return route.abort()
    }
    // The site script would add this key to the pager link. Without scripts the page would come back in the mobile layout.
    let target = req.url()
    if (config.add_query && req.resourceType() === 'document' && u.hostname === new URL(url).hostname && !u.searchParams.has(config.add_query)) {
      u.searchParams.set(config.add_query, '')
      target = u.href.replace(new RegExp(`([?&]${config.add_query})=(&|$)`), '$1$2')
    }
    if (!(await guard.check(target))) {
      robotsAborts += 1
      denied.add(u.hostname + u.pathname)
      if (config.request_log) appendFileSync(config.request_log, `${new Date().toISOString()} list ${u.hostname} ROBOTS-ABORT ${u.pathname.slice(0, 120)}\n`)
      return route.abort()
    }
    if (!(await gate.admit(u.hostname, u.pathname + u.search))) {
      capped = true
      return route.abort()
    }
    return route.continue({ url: target })
  })
  let first = null
  try {
    first = await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 30000 })
  } catch (err) {
    // The start page itself is disallowed by robots.txt: report it and stop. Any other failure is an error.
    if (config.mode !== 'click' || !robotsAborts) throw err
    process.stdout.write(JSON.stringify({ items: [], stop: 'disallowed', steps: 0, oldest: '', newest: '', denied: [...denied], capped, min_gap_ms: gate.minGap(), robots_aborts: guard.aborts(), offsite_aborts: offsite }) + '\n')
    await browser.close()
    process.exit(0)
  }
  await page.waitForTimeout(delay)

  if (config.mode === 'click') {
    // A script-rendered list needs time to hydrate: a click before that does nothing.
    await page.waitForTimeout(config.settle_ms)
    const result = await runClick(first ? first.status() : 200)
    process.stdout.write(JSON.stringify(Object.assign(result, { denied: [...denied], capped, min_gap_ms: gate.minGap(), robots_aborts: guard.aborts(), offsite_aborts: offsite })) + '\n')
    await browser.close()
    process.exit(0)
  }

  // R179: act like a reader. Read the rows, stop by the rules, then scroll or click, then wait for new rows.
  async function runClick(status) {
    const readRowsOnce = () => readRowsOnPage(page, config)
    // A new document can replace the page while we read: wait and read again.
    const readRows = async () => {
      for (let attempt = 0; attempt < 4; attempt++) {
        try {
          return await readRowsOnce()
        } catch {
          await page.waitForTimeout(1000)
        }
      }
      return []
    }
    // A list can fill in slowly: read until the row count stays the same for two reads.
    const stableRows = async () => {
      let rows = await readRows()
      for (let i = 0; i < 12; i++) {
        await page.waitForTimeout(700)
        const next = await readRows()
        if (next.length === rows.length && next.length) return next
        rows = next
      }
      return rows
    }
    const act = async () => {
      if (config.next) {
        let control = null
        if (config.next_text) {
          // Several controls match: take the one whose text matches (for example the 下一頁 link of a pager).
          const re = new RegExp(config.next_text)
          for (const candidate of await page.$$(config.next)) {
            if (re.test(((await candidate.textContent()) || '') + ' ' + ((await candidate.getAttribute('aria-label')) || ''))) { control = candidate; break }
          }
        } else {
          control = await page.$(config.next)
        }
        if (!control) return false
        const off = await control.evaluate((e) => e.disabled || e.getAttribute('aria-disabled') === 'true' || /(^|\s)disabled(\s|$)/.test(e.className || ''))
        if (off) return false
        await control.scrollIntoViewIfNeeded({ timeout: 10000 }).catch(() => {})
        await control.click({ timeout: 10000 }).catch(() => {})
        return true
      }
      if (config.scroll_to) {
        return page.evaluate((sel) => {
          const e = document.querySelector(sel)
          if (!e) return false
          e.scrollIntoView({ block: 'center' })
          return true
        }, config.scroll_to)
      }
      // Scroll like a reader: up a little, then down to the bottom. A list that loads by scroll watches the viewport and needs a scroll event.
      await page.evaluate(() => window.scrollTo(0, Math.max(0, document.body.scrollHeight - 1500)))
      await page.waitForTimeout(800)
      await page.mouse.wheel(0, 700)
      await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight))
      return true
    }
    const seen = new Map()
    let empty = 0
    let step = 0
    let stop = ''
    let abortsBefore = robotsAborts
    let hasNext = true
    for (;;) {
      const rows = await stableRows()
      const fresh = rows.filter((r) => !seen.has(r.href))
      for (const r of fresh) seen.set(r.href, r)
      empty = fresh.length ? 0 : empty + 1
      const head = await page.evaluate(() => (document.body ? document.body.innerText : '').slice(0, 400))
      const blocked = looksBlocked(await page.title(), head, step === 0 ? status : 200) && !seen.size
      stop = stopReason({
        freshDates: fresh.map((r) => labelDate(r.date)), freshCount: fresh.length, empty, emptyLimit: config.empty_limit, stopBefore: config.stop_before,
        blocked, capped, robotsAborted: robotsAborts > abortsBefore, hasNext, step, maxSteps: config.max_steps,
      })
      if (process.env.LB_DEBUG) console.error(`step ${step} rows ${rows.length} fresh ${fresh.length} empty ${empty} stop=${stop} url=${page.url()}`)
      if (stop) break
      abortsBefore = robotsAborts
      const before = (await readRows()).length
      hasNext = await act()
      if (!hasNext) {
        stop = 'no_next'
        break
      }
      step += 1
      // Wait for new rows: the gate spaces the requests, so the wait can be long. Poll until the row count or the first row changes.
      const startWait = Date.now()
      const firstBefore = rows.length ? rows[0].href : ''
      await page.waitForLoadState('domcontentloaded').catch(() => {})
      await page.waitForTimeout(delay)
      while (Date.now() - startWait < config.wait_ms) {
        const now = await readRows()
        // A pager link may load a new document: rows are empty until it renders, so wait for rows.
        if (now.length && (now.length !== before || now[0].href !== firstBefore)) break
        if (robotsAborts > abortsBefore) break
        await page.waitForTimeout(500)
      }
      if (config.partial && step % 50 === 0) writeFileSync(config.partial, JSON.stringify({ items: [...seen.values()], denied: [...denied] }))
    }
    const dates = [...seen.values()].map((r) => labelDate(r.date)).filter(Boolean).sort()
    return { items: [...seen.values()], stop, steps: step, oldest: dates[0] || '', newest: dates[dates.length - 1] || '' }
  }

  const collect = () => page.evaluate(([linkSource, rowSelector, titleSelector]) => {
    const re = new RegExp(linkSource)
    const out = []
    const seen = new Set()
    for (const a of document.querySelectorAll('a[href]')) {
      const href = a.href
      if (!re.test(href) || seen.has(href)) continue
      const headline = titleSelector ? a.querySelector(titleSelector) : null
      if (titleSelector && !headline) continue
      const title = (headline ? headline.textContent : (a.getAttribute('title') || a.textContent || '')).replace(/\s+/g, ' ').trim()
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
  }, [config.link, config.row_selector, config.title_selector])

  if (config.page_template) {
    const all = new Map()
    // feeds.json uses Python group names: (?P<y>) becomes (?<y>).
    const probe = config.stop_probe ? new RegExp(config.stop_probe.replace(/\(\?P</g, '(?<')) : null
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
    process.stdout.write(JSON.stringify({ items: [...all.values()], denied: [...denied], capped, min_gap_ms: gate.minGap() }) + '\n')
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
  process.stdout.write(JSON.stringify({ items: await collect(), denied: [...denied], capped, min_gap_ms: gate.minGap() }) + '\n')
} finally {
  await browser.close()
}
