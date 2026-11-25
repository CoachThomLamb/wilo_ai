// Personal records (#236): the tracker's mergeRecords against the shared cases in tests/fixtures/records_cases.json
// (tests/test_wilo_data.py runs the same cases on wilo/data.py). Run with: node tests/fe/records_test.mjs
import { readFileSync } from 'node:fs'
import assert from 'node:assert/strict'

const html = readFileSync(new URL('../../fe/index.html', import.meta.url), 'utf8')
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
const recordKey = eval(`(${extract('recordKey')})`)
const mergeRecords = eval(`(${extract('mergeRecords')})`)

const { cases } = JSON.parse(readFileSync(new URL('../fixtures/records_cases.json', import.meta.url), 'utf8'))
for (const c of cases) {
  const { records, prs } = mergeRecords(c.records, c.log)
  assert.deepEqual(prs.map(p => [p.lbs, p.reps]), c.prs, c.name + ': prs')
  for (const [k, pts] of Object.entries(c.front))
    assert.deepEqual(records[k].map(p => [p.lbs, p.reps]), pts, c.name + ': ' + k)
}
console.log(`records: ${cases.length} cases ok`)
