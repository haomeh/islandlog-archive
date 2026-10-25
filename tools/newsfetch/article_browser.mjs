// Browser helper for article.py (R60). Usage: node article_browser.mjs <url> <user-agent>
// The page is parsed inside the browser. Only byline, section, published_at and a short
// quote leave the page. The body is never printed, written or cached (the context is ephemeral).
import { createRequire } from 'node:module'

const require = createRequire(import.meta.url)
const { chromium } = require('playwright')
const [url, userAgent] = process.argv.slice(2)
if (!url || !userAgent) {
  console.error('usage: node article_browser.mjs <url> <user-agent>')
  process.exit(2)
}

const browser = await chromium.launch()
try {
  const context = await browser.newContext({ userAgent, javaScriptEnabled: true })
  const page = await context.newPage()
  // Do not load images, media or fonts: they are never stored and they add requests.
  await page.route('**/*', (route) => {
    const type = route.request().resourceType()
    return ['image', 'media', 'font'].includes(type) ? route.abort() : route.continue()
  })
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 30000 })
  const fields = await page.evaluate(() => {
    const meta = (sel) => document.querySelector(sel)?.getAttribute('content')?.trim() || ''
    let byline = ''
    let section = meta('meta[property="article:section"]')
    let published = meta('meta[property="article:published_time"]') || meta('meta[name="pubdate"]')
    for (const node of document.querySelectorAll('script[type="application/ld+json"]')) {
      try {
        const data = [].concat(JSON.parse(node.textContent || 'null'))
        for (const d of data) {
          if (!d || typeof d !== 'object') continue
          const author = [].concat(d.author || [])[0]
          if (!byline && author) byline = typeof author === 'string' ? author : author.name || ''
          if (!section && d.articleSection) section = [].concat(d.articleSection)[0]
          if (!published && d.datePublished) published = d.datePublished
        }
      } catch (e) { /* ignore broken JSON-LD */ }
    }
    // A JSON-LD or meta author that is an organization (自由時報電子報) is not a byline.
    if (/(報|新聞|電子報|媒體|網)$/.test(byline)) byline = ''
    const root = document.querySelector('.whitecon, article, .article-content, .story') || document.body
    const text = root.innerText || ''
    // Byline forms: 記者王小明／台北報導, 〔即時新聞／綜合報導〕
    const m = text.match(/([^\s〔\[／/]{2,30})[／/]([^\s〕\]／/]{0,10}報導)/)
    if (m) byline = m[1].startsWith('記者') ? m[1] : `${m[1]}／${m[2]}`
    const isCaption = (t) => /圖擷自|擷取自|（圖|\(圖|圖／|翻攝|資料照|提供）|攝）|攝影）/.test(t)
    const paras = [...root.querySelectorAll('p')]
      .map((p) => p.textContent.replace(/\s+/g, ' ').trim())
      .filter((t) => t.length >= 20 && !isCaption(t) && !(m && t.includes(m[0])))
    const first = paras[0] || ''
    return { byline, section, published_at: published, quote: first.slice(0, 150) }
  })
  process.stdout.write(JSON.stringify(fields) + '\n')
} finally {
  await browser.close()
}
