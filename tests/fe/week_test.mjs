// The Week page's date maths and ordering (#168).
// Run with: node tests/fe/week_test.mjs. Extracts the functions from fe/week.html verbatim.
import { readFileSync } from 'node:fs'
import assert from 'node:assert/strict'

const html = readFileSync(new URL('../../fe/week.html', import.meta.url), 'utf8')
function extract(name) {
  const start = html.indexOf(`function ${name}(`)
  assert.notEqual(start, -1, `${name} not found`)
  let depth = 0
  for (let j = html.indexOf('{', start); j < html.length; j++) {
    if (html[j] === '{') depth++
    else if (html[j] === '}' && --depth === 0) return html.slice(start, j + 1)
  }
  throw new Error(`${name} not closed`)
}
const pad = n => String(n).padStart(2, '0')
const localDate = d => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
const parse = s => new Date(s + 'T12:00')
const addDays = eval(`(${extract('addDays')})`)
const mondayOf = eval(`(${extract('mondayOf')})`)
const byTime = eval(`(${extract('byTime')})`)

// weeks run Monday to Sunday
assert.equal(mondayOf('2026-11-16'), '2026-11-16')   // a Monday
assert.equal(mondayOf('2026-11-15'), '2026-11-09')   // Sunday belongs to the week before
assert.equal(mondayOf('2026-11-19'), '2026-11-16')
assert.equal(mondayOf('2027-01-01'), '2026-12-28')   // across a year

assert.equal(addDays('2026-11-30', 1), '2026-12-01')
assert.equal(addDays('2026-11-01', -1), '2026-10-31')   // across the clock change
assert.equal(addDays('2026-03-08', 7), '2026-03-15')
assert.equal(addDays('2026-12-28', 6), '2027-01-03')

// all-day first, then by time, then in the order added (same as wilo/data.py events())
const day = [
  { text: 'late', time: '18:00', createdAt: '1' },
  { text: 'second all day', createdAt: '3' },
  { text: 'early', time: '09:00', createdAt: '2' },
  { text: 'first all day', createdAt: '0' },
]
assert.deepEqual(day.sort(byTime).map(e => e.text), ['first all day', 'second all day', 'early', 'late'])

console.log('week_test ok')
