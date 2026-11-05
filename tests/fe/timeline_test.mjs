// The tracker's ‹ › timeline: done workouts back in time, planned ones ahead, the draft as "Now".
// Run with: node tests/fe/timeline_test.mjs. Extracts dayOf and buildTimeline from fe/index.html verbatim.
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
const pad = n => String(n).padStart(2, '0')
const dayOf = eval(`(${extract('dayOf')})`)
const buildTimeline = eval(`(${extract('buildTimeline')})`)

const w = (docId, id, status, assignedFor, finishedAt) => ({ docId, doc: { id, name: id, status, assignedFor, finishedAt, exercises: [] } })
const show = t => t.map(s => `${s.kind}:${s.docId}${s.live ? '*' : ''}`)

assert.equal(dayOf('2026-11-02'), '2026-11-02')
assert.equal(dayOf(''), '')
assert.equal(dayOf('nonsense'), '')

const workouts = [
  w('oct20', 'p-oct20', 'planned', '2026-10-20'),   // skipped: never done
  w('oct29', 'p-oct29', 'done', '2026-10-29', '2026-10-30T16:23:19.028Z'),
  // Finished the day after its plan's day: sits on the plan's day.
  w('oct31', 'p-oct31', 'done', '2026-10-31', '2026-11-01T18:42:34.953Z'),
  // Logged with no plan date: sits on the day it was finished.
  w('oct23', 'cardio', 'done', undefined, '2026-10-23T10:53:34.770Z'),
  // Started but not finished: still planned.
  w('nov2', 'p-nov2', 'in progress', '2026-11-02'),
  w('nov3', 'p-nov3', 'planned', '2026-11-03'),
]

// Mid-workout on Nov 2: it is the live stop; everything else is in day order.
let t = buildTimeline(workouts, { docId: 'nov2', workoutId: 'p-nov2', key: '2026-11-02' })
assert.deepEqual(show(t), ['plan:oct20', 'done:oct23', 'done:oct29', 'done:oct31', 'plan:nov2*', 'plan:nov3'])
assert.equal(t.find(s => s.docId === 'oct31').key, '2026-10-31', "a done workout sits on its plan's day")
assert.equal(t.find(s => s.docId === 'oct23').key, '2026-10-23', 'no plan date: the day it was finished')

// The next workout to open is the earliest not done, skipped ones included (#90).
assert.equal(buildTimeline(workouts, {}).find(s => s.kind === 'plan').docId, 'oct20')

// Finished on this phone: the same doc, now done, still live.
const finished = workouts.map(x => x.docId === 'nov2' ? w('nov2', 'p-nov2', 'done', '2026-11-02', '2026-11-02T17:00:00.000Z') : x)
t = buildTimeline(finished, { docId: 'nov2', workoutId: 'p-nov2', key: '2026-11-02' })
assert.deepEqual(show(t).slice(-2), ['done:nov2*', 'plan:nov3'])

// A draft from before #126 has no docId: found by the workout's id.
t = buildTimeline(workouts, { docId: null, workoutId: 'p-nov3', key: '2026-11-03' })
assert.equal(t.find(s => s.live).docId, 'nov3')

// A draft that matches nothing, or has no plan: a 'draft' stop on the draft's day.
t = buildTimeline(workouts, { docId: 'gone', workoutId: 'p-nov2', key: '2026-11-02' })
assert.deepEqual(show(t).slice(-3), ['draft:null*', 'plan:nov2', 'plan:nov3'])
t = buildTimeline([], { docId: null, workoutId: null, key: '2026-11-02' })
assert.deepEqual(show(t), ['draft:null*'])

// Exactly one live stop, even if two workouts share an id.
t = buildTimeline([w('x1', 'same', 'planned', '2026-11-04'), w('x2', 'same', 'planned', '2026-11-05')], { docId: null, workoutId: 'same', key: '2026-11-02' })
assert.equal(t.filter(s => s.live).length, 1)

console.log('timeline_test: all assertions passed')
