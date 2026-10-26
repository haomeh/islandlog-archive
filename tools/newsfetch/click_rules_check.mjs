// Test helper for test_click_routes.py: stop rules, date labels and the per-request robots guard. No network.
import { labelDate, isoDate, stopReason, looksBlocked } from './click_rules.mjs'
import { parseRobots, isAllowed, createRobotsGuard } from './robots_rules.mjs'

const base = { freshDates: ['2026-09-20'], freshCount: 5, empty: 0, emptyLimit: 3, stopBefore: '2026-04-24', blocked: false, capped: false, robotsAborted: false, hasNext: true, step: 3, maxSteps: 50 }
const stops = {
  go: stopReason(base),
  date: stopReason({ ...base, freshDates: ['2026-04-23', '2026-04-20'] }),
  dateMixed: stopReason({ ...base, freshDates: ['2026-04-23', '2026-05-01'] }),
  noRows: stopReason({ ...base, freshCount: 0, freshDates: [], empty: 3 }),
  noRowsLimit6: stopReason({ ...base, freshCount: 0, freshDates: [], empty: 3, emptyLimit: 6 }),
  noNext: stopReason({ ...base, hasNext: false }),
  maxSteps: stopReason({ ...base, step: 50 }),
  disallowed: stopReason({ ...base, freshCount: 0, freshDates: [], empty: 1, robotsAborted: true }),
  disallowedButRows: stopReason({ ...base, robotsAborted: true }),
  captcha: stopReason({ ...base, blocked: true }),
  cap: stopReason({ ...base, capped: true }),
}
const now = new Date('2026-10-26T06:00:00Z')
const dates = {
  iso: isoDate('2026/9/5 10:00'),
  isoT: labelDate('2026-09-20T09:58:00Z', now),
  hours: labelDate('5小時前', now),
  days: labelDate('2天前', now),
  yesterday: labelDate('昨天 10:00', now),
  none: labelDate('熱門', now),
}
const blocked = {
  captchaTitle: looksBlocked('Please complete the CAPTCHA', ''),
  cloudflare: looksBlocked('Just a moment...', 'Verify you are human by completing the action below.'),
  status403: looksBlocked('x', '', 403),
  normal: looksBlocked('政治 - 測試新聞', '今日新聞 快訊'),
}

const robotsText = ['User-agent: *', 'Disallow: /api/', 'Disallow: /search*', 'Allow: /api/open', '', 'User-agent: islandlog-newsfetch', 'Disallow: /private/', 'Disallow: /*.json$'].join('\n')
const named = parseRobots(robotsText, 'islandlog-newsfetch')
const star = parseRobots(robotsText, 'other-bot')
const rules = {
  namedBlocks: isAllowed(named, '/private/a'),
  namedAllowsApi: isAllowed(named, '/api/more'),
  namedBlocksJsonEnd: isAllowed(named, '/x/list.json'),
  namedAllowsJsonQuery: isAllowed(named, '/x/list.json?a=1'),
  starBlocksApi: isAllowed(star, '/api/more'),
  starLongestAllow: isAllowed(star, '/api/open/list'),
  starBlocksSearch: isAllowed(star, '/search?q=a'),
  starAllowsList: isAllowed(star, '/list?page=2'),
}

const reads = []
const answers = {
  'a.test': { status: 200, body: 'User-agent: *\nDisallow: /api/\n' },
  'b.test': { status: 404, body: '' },
  'c.test': { status: 503, body: '' },
  'd.test': 'throw',
  'e.test': { status: 301, body: '' },
}
const guard = createRobotsGuard({
  token: 'islandlog-newsfetch',
  readRobots: async (protocol, host) => {
    reads.push(host)
    if (answers[host] === 'throw') throw new Error('network down')
    return answers[host]
  },
})
const checks = {}
for (const [key, url] of Object.entries({
  aList: 'https://a.test/list?page=2', aApi: 'https://a.test/api/more?page=2', aApi2: 'https://a.test/api/more?page=3',
  bAny: 'https://b.test/api/x', cAny: 'https://c.test/list', dAny: 'https://d.test/list', eAny: 'https://e.test/list',
})) checks[key] = await guard.check(url)

process.stdout.write(JSON.stringify({ stops, dates, blocked, rules, checks, reads, aborts: guard.aborts() }) + '\n')
