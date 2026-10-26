// Stop rules and date reading for the browser click route (R179). No browser code here, so a test can run it.
// A click route opens a list page, scrolls or clicks like a reader, and reads the rows from the DOM.

const DATE_RE = /(20\d\d)[-/.](\d{1,2})[-/.](\d{1,2})/

// Returns YYYY-MM-DD from the first date in a text, or '' when the text has none.
export function isoDate(raw) {
  const m = String(raw || '').match(DATE_RE)
  if (!m) return ''
  return `${m[1]}-${m[2].padStart(2, '0')}-${m[3].padStart(2, '0')}`
}

// Like isoDate, but also reads a relative label (3小時前, 2天前, 昨天) as a Taipei date. Returns '' when the text has no date.
export function labelDate(raw, now = new Date()) {
  const iso = isoDate(raw)
  if (iso) return iso
  const text = String(raw || '')
  const taipei = (offsetDays) => new Date(now.getTime() + 8 * 3600 * 1000 - offsetDays * 86400 * 1000).toISOString().slice(0, 10)
  const days = text.match(/(\d+)\s*天前/)
  if (days) return taipei(Number(days[1]))
  if (/昨天/.test(text)) return taipei(1)
  if (/\d+\s*(分鐘|小時)前|剛剛/.test(text) || /^\s*\d{1,2}:\d{2}\s*$/.test(text)) return taipei(0)
  return ''
}

// Returns the reason to stop, or '' to go on. The order is the order of the rules.
//   captcha: the page shows a block or CAPTCHA page.
//   cap: the request cap of a host is used up.
//   disallowed: the last click sent a request that robots.txt disallows, and no new row came.
//   no_rows: emptyLimit steps in a row (default 3) gave no new row.
//   date: every new row is older than stopBefore.
//   no_next: the next control is missing or disabled.
//   max_steps: the step limit is reached.
export function stopReason({ freshDates, freshCount, empty, emptyLimit = 3, stopBefore, blocked, capped, robotsAborted, hasNext, step, maxSteps }) {
  if (blocked) return 'captcha'
  if (capped) return 'cap'
  if (freshCount === 0 && robotsAborted) return 'disallowed'
  if (empty >= emptyLimit) return 'no_rows'
  const dates = freshDates.filter(Boolean)
  if (stopBefore && dates.length && dates.every((d) => d < stopBefore)) return 'date'
  if (!hasNext) return 'no_next'
  if (step >= maxSteps) return 'max_steps'
  return ''
}

const BLOCK_RE = /captcha|are you a (human|robot)|access denied|verify you are human|unusual traffic|請完成.{0,6}驗證|人機驗證|機器人驗證/i

// True when the page title or the first part of the text looks like a block page or a CAPTCHA.
export function looksBlocked(title, textHead, status = 200) {
  if ([403, 429].includes(status)) return true
  return BLOCK_RE.test(`${title || ''} ${String(textHead || '').slice(0, 400)}`)
}

// Reads the rows of a list page in the browser. Only href, title and the date text leave the page (R60): no lead paragraph, no body.
// config: link (regex source on the absolute href), rows, link_selector, title_selector, date_selector.
export function readRowsOnPage(page, config) {
  return page.evaluate(([rowSel, linkSource, linkSel, titleSel, dateSel]) => {
    const re = new RegExp(linkSource)
    const out = []
    for (const row of document.querySelectorAll(rowSel)) {
      const a = row.matches('a[href]') ? row : row.querySelector(linkSel || 'a[href]')
      if (!a || !re.test(a.href)) continue
      const head = titleSel ? row.querySelector(titleSel) : null
      const title = ((head ? head.textContent : (a.getAttribute('title') || a.textContent || '')) || '').replace(/\s+/g, ' ').trim()
      if (!title) continue
      const d = dateSel ? row.querySelector(dateSel) : null
      const date = d ? (d.getAttribute('datetime') || d.getAttribute('title') || d.textContent || '') : ''
      out.push({ href: a.href, title: title.slice(0, 200), row: '', hint: '', date: date.replace(/\s+/g, ' ').trim().slice(0, 40) })
    }
    return out
  }, [config.rows, config.link, config.link_selector, config.title_selector, config.date_selector])
}
