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

const plan = (docId, id, assignedFor) => ({ docId, doc: { id, name: id, assignedFor, exercises: [] } })
const done = (docId, id, finishedAt, inProgress = false) => ({ docId, doc: { id, name: id, finishedAt, inProgress, exercises: [] } })
const show = t => t.map(s => `${s.kind}:${s.docId}${s.live ? '*' : ''}`)

assert.equal(dayOf('2026-11-02'), '2026-11-02')
assert.equal(dayOf(''), '')
assert.equal(dayOf('nonsense'), '')

const plans = [
  plan('a-oct20', 'p-oct20', '2026-10-20'),   // skipped: never done
  plan('a-oct29', 'p-oct29', '2026-10-29'),
  plan('a-oct31', 'p-oct31', '2026-10-31'),
  plan('a-nov2', 'p-nov2', '2026-11-02'),
  plan('a-nov3', 'p-nov3', '2026-11-03'),
]
const completed = [
  // Finished the day after its plan's day: sits on the plan's day.
  done('c-oct31', 'p-oct31', '2026-11-01T18:42:34.953Z'),
  done('c-oct29', 'p-oct29', '2026-10-30T16:23:19.028Z'),
  // No plan left: sits on the day it was finished.
  done('c-oct23', 'cardio', '2026-10-23T10:53:34.770Z'),
  // Saved as you go, not finished: doesn't count as done.
  done('c-nov2', 'p-nov2', '2026-11-02T15:00:00.000Z', true),
]

// Mid-workout on Nov 2's plan: it is the live stop; everything else is in day order.
let t = buildTimeline(plans, completed, { workoutId: 'p-nov2', finishDocId: 'c-nov2', key: '2026-11-02' })
assert.deepEqual(show(t), ['plan:a-oct20', 'done:c-oct23', 'done:c-oct29', 'done:c-oct31', 'plan:a-nov2*', 'plan:a-nov3'])
assert.equal(t.find(s => s.docId === 'c-oct31').key, '2026-10-31', "a done workout sits on its plan's day")

// The next workout to open is the earliest unfinished plan, skipped ones included (#90).
assert.equal(buildTimeline(plans, completed, {}).find(s => s.kind === 'plan').docId, 'a-oct20')

// Finished on this phone: the done copy is live and the plan drops off.
const finished = completed.map(c => c.docId === 'c-nov2' ? { ...c, doc: { ...c.doc, inProgress: false } } : c)
t = buildTimeline(plans, finished, { workoutId: 'p-nov2', finishDocId: 'c-nov2', key: '2026-11-02' })
assert.deepEqual(show(t).slice(-2), ['done:c-nov2*', 'plan:a-nov3'])

// Finished elsewhere (another doc), or a draft with no plan: a 'draft' stop on the draft's day.
t = buildTimeline(plans, finished, { workoutId: 'p-nov2', finishDocId: 'c-other', key: '2026-11-02' })
assert.deepEqual(show(t).slice(-3), ['done:c-nov2', 'draft:null*', 'plan:a-nov3'])
t = buildTimeline([], [], { workoutId: null, finishDocId: null, key: '2026-11-02' })
assert.deepEqual(show(t), ['draft:null*'])

// Exactly one live stop, even if two plans share an id.
t = buildTimeline([plan('x1', 'same', '2026-11-04'), plan('x2', 'same', '2026-11-05')], [], { workoutId: 'same', key: '2026-11-02' })
assert.equal(t.filter(s => s.live).length, 1)

console.log('timeline_test: all assertions passed')
