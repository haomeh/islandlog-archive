// R61 robots check for every Playwright request. No network code here, so a test can run it with a fake fetch.
// parseRobots(): the rules of the group for our token (RFC 9309: a named group wins over the * group).
// isAllowed(): the longest matching rule wins, and Allow wins a tie.
// createRobotsGuard(): one robots.txt per host, read once. Any answer except 200, 404 and 410 gives disallow all (fail closed).

export function parseRobots(text, token) {
  const wanted = token.toLowerCase()
  const groups = []
  let current = null
  let lastWasAgent = false
  for (const raw of text.split(/\r?\n/)) {
    const line = raw.replace(/#.*$/, '').trim()
    const at = line.indexOf(':')
    if (at < 0) continue
    const key = line.slice(0, at).trim().toLowerCase()
    const value = line.slice(at + 1).trim()
    if (key === 'user-agent') {
      if (!current || !lastWasAgent) {
        current = { agents: [], rules: [] }
        groups.push(current)
      }
      current.agents.push(value.toLowerCase())
      lastWasAgent = true
      continue
    }
    lastWasAgent = false
    if (current && (key === 'allow' || key === 'disallow')) current.rules.push({ allow: key === 'allow', path: value })
  }
  const named = groups.filter((g) => g.agents.includes(wanted))
  const chosen = named.length ? named : groups.filter((g) => g.agents.includes('*'))
  return chosen.flatMap((g) => g.rules).filter((r) => r.path)
}

function pathMatches(pattern, target) {
  const anchored = pattern.endsWith('$')
  const body = anchored ? pattern.slice(0, -1) : pattern
  const source = body.split('*').map((part) => part.replace(/[.+?^${}()|[\]\\]/g, '\\$&')).join('.*')
  return new RegExp('^' + source + (anchored ? '$' : '')).test(target)
}

export function isAllowed(rules, pathAndQuery) {
  let best = null
  for (const rule of rules) {
    if (!pathMatches(rule.path, pathAndQuery)) continue
    if (!best || rule.path.length > best.path.length || (rule.path.length === best.path.length && rule.allow)) best = rule
  }
  return !best || best.allow
}

// readRobots(host): async function that returns {status, body}. status is null when the read failed.
export function createRobotsGuard({ readRobots, token }) {
  const hosts = new Map()
  const aborted = new Map()
  const guard = {
    // Returns true when the request may go.
    async check(url) {
      const u = new URL(url)
      if (!hosts.has(u.host)) {
        hosts.set(u.host, (async () => {
          let answer
          try {
            answer = await readRobots(u.protocol, u.host)
          } catch {
            answer = { status: null, body: '' }
          }
          if (answer.status === 200) return { all: false, rules: parseRobots(answer.body || '', token) }
          if (answer.status === 404 || answer.status === 410) return { all: false, rules: [] }
          return { all: true, rules: [] }
        })())
      }
      const entry = await hosts.get(u.host)
      const ok = !entry.all && isAllowed(entry.rules, u.pathname + u.search)
      if (!ok) aborted.set(u.host, (aborted.get(u.host) || 0) + 1)
      return ok
    },
    aborts() { return Object.fromEntries(aborted) },
  }
  return guard
}
