// Host rules shared by the browser helpers (T64: F-01 own-site check, F-04 address check).
// No dependency on playwright, so node can test it alone.

// Two-label public suffixes that the crawler meets. A host under one of them needs three labels.
const SECOND_LEVEL = new Set(['com.tw', 'org.tw', 'gov.tw', 'edu.tw', 'net.tw', 'idv.tw', 'mil.tw', 'ebiz.tw', 'club.tw', 'game.tw',
  'com.cn', 'org.cn', 'gov.cn', 'edu.cn', 'net.cn', 'com.hk', 'org.hk', 'gov.hk', 'edu.hk', 'net.hk', 'co.jp', 'or.jp', 'go.jp', 'ne.jp', 'ac.jp', 'co.uk', 'org.uk', 'gov.uk', 'ac.uk'])

export function registrableDomain(hostname) {
  const labels = String(hostname).toLowerCase().replace(/\.$/, '').split('.')
  if (labels.length <= 2) return labels.join('.')
  const last2 = labels.slice(-2).join('.')
  return SECOND_LEVEL.has(last2) ? labels.slice(-3).join('.') : last2
}

// True when hostname is base or a subdomain of base (dot boundary).
export function sameSite(hostname, base) {
  const h = String(hostname).toLowerCase()
  const b = String(base).toLowerCase()
  return h === b || h.endsWith('.' + b)
}

// A host written as an address or as a local name that points to this machine or a private net.
export function isPrivateHostLiteral(hostname) {
  const h = String(hostname).toLowerCase().replace(/^\[|\]$/g, '')
  if (h === 'localhost' || h.endsWith('.localhost') || h.endsWith('.local') || h.endsWith('.internal')) return true
  const v4 = h.match(/^(\d+)\.(\d+)\.(\d+)\.(\d+)$/)
  if (v4) {
    const [a, b] = [Number(v4[1]), Number(v4[2])]
    return a === 0 || a === 10 || a === 127 || (a === 169 && b === 254) || (a === 172 && b >= 16 && b <= 31) || (a === 192 && b === 168) || (a === 100 && b >= 64 && b <= 127) || a >= 224
  }
  if (h.includes(':')) {
    const mapped = h.match(/^::ffff:(\d+\.\d+\.\d+\.\d+)$/)
    if (mapped) return isPrivateHostLiteral(mapped[1])
    return h === '::' || h === '::1' || /^f[cd]/.test(h) || /^fe[89ab]/.test(h)
  }
  return false
}

export function isHttpUrl(text) {
  try {
    const u = new URL(text)
    return u.protocol === 'http:' || u.protocol === 'https:'
  } catch {
    return false
  }
}
