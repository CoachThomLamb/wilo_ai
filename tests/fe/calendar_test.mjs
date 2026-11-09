// The calendar's day math (fe/calendar.html): weeks start Monday, todos keep their time when moved.
// Run with: node tests/fe/calendar_test.mjs. Extracts the functions from fe/calendar.html verbatim.
import { readFileSync } from 'node:fs'
import assert from 'node:assert/strict'

const html = readFileSync(new URL('../../fe/calendar.html', import.meta.url), 'utf8')
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
const localDay = eval(`(${extract('localDay')})`)
const addDays = eval(`(${extract('addDays')})`)
const weekStart = eval(`(${extract('weekStart')})`)
const dayOf = eval(`(${extract('dayOf')})`)
const todoDay = eval(`(${extract('todoDay')})`)
const movedDue = eval(`(${extract('movedDue')})`)

assert.equal(addDays('2026-11-09', 1), '2026-11-10')
assert.equal(addDays('2026-10-31', 1), '2026-11-01')   // DST weekend
assert.equal(addDays('2026-11-01', -1), '2026-10-31')
assert.equal(addDays('2026-12-28', 7), '2027-01-04')

assert.equal(weekStart('2026-11-09'), '2026-11-09')    // Monday
assert.equal(weekStart('2026-11-15'), '2026-11-09')    // Sunday belongs to the week before it
assert.equal(weekStart('2026-11-11'), '2026-11-09')

assert.equal(dayOf('2026-11-07'), '2026-11-07')
assert.equal(dayOf(''), '')

assert.equal(todoDay('2026-11-09 19:00'), '2026-11-09')
assert.equal(todoDay('2026-11-09'), '2026-11-09')
assert.equal(todoDay('friday'), '')
assert.equal(todoDay(undefined), '')

assert.equal(movedDue('2026-11-09 19:00', '2026-11-12'), '2026-11-12 19:00')   // time stays
assert.equal(movedDue('2026-11-09', '2026-11-12'), '2026-11-12')
assert.equal(movedDue('friday', '2026-11-13'), '2026-11-13')                   // free text gives way to a date
assert.equal(movedDue(undefined, '2026-11-13'), '2026-11-13')
assert.equal(movedDue('2026-11-09 19:00', ''), '')                             // "No date"

console.log('calendar ok')
