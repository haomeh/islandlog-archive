// R61 and R175 gate for every Playwright request. No network code here, so a test can run it with a fake clock.
// decide(): which requests may leave the browser. Only document, script, xhr and fetch pass.
// createGate(): 1 request per 1.1 s per host on every request, a cap per host per run, and a log line per request.
import { appendFileSync } from 'node:fs'

export const ALLOWED_TYPES = ['document', 'script', 'xhr', 'fetch']
export const MIN_GAP_MS = 1100

export function decide(resourceType, url, headers = {}) {
  if (!ALLOWED_TYPES.includes(resourceType)) return 'type'
  const u = new URL(url)
  if (u.pathname.includes('/_next/data/')) return 'next-data'
  const purpose = `${headers['purpose'] || ''} ${headers['sec-purpose'] || ''} ${headers['next-router-prefetch'] || ''}`.toLowerCase()
  if (purpose.includes('prefetch') || purpose.trim() === '1') return 'prefetch'
  return ''
}

export function createGate({ cap = 20000, logFile = '', now = () => Date.now(), sleep = (ms) => new Promise((r) => setTimeout(r, ms)), tag = '' } = {}) {
  const last = new Map()
  const counts = new Map()
  let chain = Promise.resolve()
  const gate = {
    gaps: [],
    // Returns true when the request may go. Calls run one after the other, so the gap holds under parallel requests.
    admit(host, path = '') {
      const run = chain.then(async () => {
        const n = (counts.get(host) || 0) + 1
        if (n > cap) return false
        counts.set(host, n)
        const prev = last.get(host)
        if (prev !== undefined) {
          const wait = prev + MIN_GAP_MS - now()
          if (wait > 0) await sleep(wait)
        }
        const t = now()
        if (prev !== undefined) gate.gaps.push(t - prev)
        last.set(host, t)
        if (logFile) appendFileSync(logFile, `${new Date(t).toISOString()} ${tag} ${host} ${n} ${path.slice(0, 120)}\n`)
        return true
      })
      chain = run.catch(() => {})
      return run
    },
    count(host) { return counts.get(host) || 0 },
    minGap() { return gate.gaps.length ? Math.min(...gate.gaps) : null },
  }
  return gate
}
