// Regression test for #109, run with: node tests/fe/merge_plan_test.mjs
// Extracts the plan-merge functions from fe/index.html verbatim and checks
// that a user's rename survives a mid-workout merge.
import { readFileSync } from 'node:fs'
import assert from 'node:assert/strict'

const html = readFileSync(new URL('../../fe/index.html', import.meta.url), 'utf8')

function extract(name) {
  const start = html.indexOf(`function ${name}(`)
  assert.notEqual(start, -1, `${name} not found`)
  let depth = 0, i = html.indexOf('{', start)
  for (let j = i; j < html.length; j++) {
    if (html[j] === '{') depth++
    else if (html[j] === '}') { depth--; if (depth === 0) return html.slice(start, j + 1) }
  }
  throw new Error(`${name} not closed`)
}

let nextId = 0
const uid = () => 'ex' + (nextId++) + '-t'
const deriveExId = name => (name || '').toLowerCase().replace(/\s+/g, '-').replace(/[^a-z0-9-]/g, '')

const makeExercise = eval(`(${extract('makeExercise')})`)
const mergePlan = eval(`(${extract('mergePlan')})`)

// The trainer renamed the exercise but logged no sets; the coach's plan still
// carries the old name.
const current = [{
  instanceId: 'ex-1', exId: 'hip-thrust-v2', name: 'Hip Thrust v2', note: 'pause at top',
  custom_name: null, userEdited: true, timed: false, fallback: null, swapped: false, original: null,
  sets: [{ lbs: 0, reps: 10, done: false, custom: null }],
}]
const planDefs = [{ instanceId: 'ex-1', name: 'Hip Thrust', sets: 1, target: { reps: 10 } }]

const merged = mergePlan(current, planDefs)
assert.equal(merged.length, 1)
assert.equal(merged[0].name, 'Hip Thrust v2', 'the rename snapped back to the plan (#109)')
assert.equal(merged[0].exId, 'hip-thrust-v2')
assert.equal(merged[0].note, 'pause at top')
assert.equal(merged[0].sets.length, 1)

// Untouched exercises still take the plan's version.
const untouched = mergePlan([makeExercise({ instanceId: 'ex-2', name: 'Squat', sets: 1, target: { reps: 5 } })],
  [{ instanceId: 'ex-2', name: 'Squat', sets: 1, target: { reps: 5 } }])
assert.equal(untouched[0].name, 'Squat')
assert.ok(!('userEdited' in untouched[0]))

console.log('merge_plan_test: all assertions passed')
