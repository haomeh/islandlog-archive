// Test helper for test_browser_gate.py: runs the gate with a fake clock and prints one JSON object. No network.
import { decide, createGate } from './browser_gate.mjs'

let clock = 1000000
const slept = []
const gate = createGate({ cap: 4, now: () => clock, sleep: async (ms) => { slept.push(ms); clock += ms } })
const out = { decisions: {}, admitted: [], slept }
const h = 'https://example.test'
out.decisions.image = decide('image', `${h}/a.png`)
out.decisions.stylesheet = decide('stylesheet', `${h}/a.css`)
out.decisions.font = decide('font', `${h}/a.woff`)
out.decisions.media = decide('media', `${h}/a.mp4`)
out.decisions.document = decide('document', `${h}/news`)
out.decisions.script = decide('script', `${h}/a.js`)
out.decisions.xhr = decide('xhr', `${h}/api`)
out.decisions.fetch = decide('fetch', `${h}/api`)
out.decisions.nextData = decide('fetch', `${h}/_next/data/abc/story/x.json`)
out.decisions.prefetch = decide('fetch', `${h}/api`, { purpose: 'prefetch' })
out.decisions.nextPrefetch = decide('fetch', `${h}/api`, { 'next-router-prefetch': '1' })
// Ten requests at once to one host, and two to another host.
const jobs = []
for (let i = 0; i < 10; i++) jobs.push(gate.admit('a.test', `/p${i}`).then((ok) => out.admitted.push(['a', ok])))
for (let i = 0; i < 2; i++) jobs.push(gate.admit('b.test', `/p${i}`).then((ok) => out.admitted.push(['b', ok])))
await Promise.all(jobs)
out.countA = gate.count('a.test')
out.minGap = gate.minGap()
process.stdout.write(JSON.stringify(out) + '\n')
