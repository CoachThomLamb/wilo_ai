// Human coaches (#242): fe/coaching.js plannedDoc against the shared cases in tests/fixtures/coach_plan_cases.json
// (tests/test_wilo_data.py holds wilo/data.py planned_doc to the same), plus the coach's exercise lines.
// Run with: node tests/fe/coach_test.mjs
import { readFileSync } from 'node:fs'
import assert from 'node:assert/strict'

const src = readFileSync(new URL('../../fe/coaching.js', import.meta.url), 'utf8')
function extract(name) {
  const start = src.indexOf(`function ${name}(`)
  assert.notEqual(start, -1, `${name} not found`)
  let depth = 0
  for (let j = src.indexOf('{', start); j < src.length; j++) {
    if (src[j] === '{') depth++
    else if (src[j] === '}' && --depth === 0) return src.slice(start, j + 1)
  }
  throw new Error(`${name} not closed`)
}
const names = ['iso', 'plannedDoc', 'docIdFor', 'parseLines', 'exerciseLine']
const fns = new Function(`${names.map(extract).join('\n')}\nreturn { ${names.join(', ')} }`)()

// Same doc as Python's planned_doc.
const { cases } = JSON.parse(readFileSync(new URL('../fixtures/coach_plan_cases.json', import.meta.url), 'utf8'))
for (const c of cases)
  assert.deepEqual(fns.plannedDoc(c.workout, new Date(c.now), c.plannedBy), c.doc, c.name)
assert.equal('plannedBy' in fns.plannedDoc(cases[0].workout, new Date(cases[0].now)), false, 'no coach, no plannedBy')

// Tracker-style id.
assert.match(fns.docIdFor('Legs Day', new Date(2026, 10, 26, 9, 5)), /^26-nov-09:05-legs--[a-z0-9]{1,4}$/)

// Lines the coach types.
let r = fns.parseLines('Squat 3x5 @135 - sit deep\n\nPlank 2x30s\nPull-up 4 x 8\nRDL 3×10 at 95 lbs')
assert.deepEqual(r.errors, [])
assert.deepEqual(r.exercises.map(x => [x.name, x.sets.length, x.sets[0].reps, x.sets[0].lbs, !!x.timed, x.cue]), [
  ['Squat', 3, 5, 135, false, 'sit deep'],
  ['Plank', 2, 30, '', true, undefined],
  ['Pull-up', 4, 8, '', false, undefined],
  ['RDL', 3, 10, 95, false, undefined],
])
assert.equal(r.exercises[0].sets.every(s => s.done === false), true)
r = fns.parseLines('Squat heavy\nBench 3x5')
assert.equal(r.errors.length, 1)
assert.match(r.errors[0], /^Line 1/)
assert.deepEqual(fns.parseLines('  \n').errors, ['Add at least one exercise.'])
assert.equal(fns.parseLines('Squat 50x5').errors.length, 1)

// What the coach reads back.
const sq = { name: 'Squat', sets: [{ lbs: 135, reps: 5, done: true }, { lbs: 145, reps: 5, done: true }, { lbs: 155, reps: 5, done: false }] }
assert.equal(fns.exerciseLine(sq, true), 'Squat: 135×5, 145×5')
assert.equal(fns.exerciseLine(sq, false), 'Squat: 3×5 @135')
assert.equal(fns.exerciseLine({ name: 'Plank', timed: true, sets: [{ lbs: '', reps: 30, done: true }] }, true), 'Plank: 30s')
assert.equal(fns.exerciseLine({ name: 'X', sets: [{ reps: 5, done: false }] }, true), '')

console.log(`coach: ${cases.length} cases ok`)
