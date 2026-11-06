// The tracker's merge of a new coach plan into the log (#126, #145): logged sets, renames,
// deletions and added exercises survive. Run with: node tests/fe/merge_test.mjs
// Extracts makeExercise and mergePlan from fe/index.html verbatim.
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
let n = 0
const uid = () => 'ex' + (n++)
const userExId = () => 'u-' + (n++)
const makeExercise = eval(`(${extract('makeExercise')})`)
const mergePlan = eval(`(${extract('mergePlan')})`)

const def = (exId, name, sets = 3, extra = {}) => ({ exId, name, sets, ...extra })
const view = ex => ex.map(x => `${x.exId}:${x.name}:${x.sets.filter(s => s.done).length}/${x.sets.length}${x.removed ? ':removed' : ''}`)
const tick = (ex, i) => { ex.sets[i].done = true; return ex }

// Plan x1 bench, x2 row. Log: 2 bench sets done.
const plan1 = [def('x1', 'Bench'), def('x2', 'Row')]
const log = plan1.map(makeExercise)
tick(log[0], 0); tick(log[0], 1)

// The coach adds a set to bench: logged sets stay, the rest comes from the plan (#145).
let m = mergePlan(log, [def('x1', 'Bench', 4), def('x2', 'Row')], plan1)
assert.deepEqual(view(m), ['x1:Bench:2/4', 'x2:Row:0/3'])
assert.equal(m[0].instanceId, log[0].instanceId, 'same exercise keeps its instanceId')

// Plan done flags are ignored: a set is never counted twice.
m = mergePlan(log, [def('x1', 'Bench', 3), def('x2', 'Row')].map(d => ({ ...d, sets: [{ done: true }, { done: true }, { done: true }] })), plan1)
assert.equal(m[0].sets.filter(s => s.done).length, 2)

// You renamed it: your name stays when the coach's change didn't touch the name...
log[1].name = 'Barbell row'
m = mergePlan(log, [def('x1', 'Bench'), def('x2', 'Row', 4)], plan1)
assert.equal(m[1].name, 'Barbell row')
assert.equal(m[1].sets.length, 4)
// ...but the coach's rename wins when it changes the name.
m = mergePlan(log, [def('x1', 'Bench'), def('x2', 'Seated row')], plan1)
assert.equal(m[1].name, 'Seated row')

// You deleted a plan exercise: it stays deleted. One you added stays, at the end.
log[1].removed = true
const mine = makeExercise({ exId: 'u-mine', name: 'Curls', sets: 2 })
const withMine = [...log, mine]
m = mergePlan(withMine, [def('x1', 'Bench'), def('x2', 'Row'), def('x3', 'Squat')], plan1)
assert.deepEqual(view(m), ['x1:Bench:2/3', 'x2:Barbell row:0/3:removed', 'x3:Squat:0/3', 'u-mine:Curls:0/2'])

// The coach drops one: gone if nothing was logged on it, kept with its logged sets (first) if started.
const log2 = [def('x1', 'Bench'), def('x2', 'Row')].map(makeExercise)
tick(log2[1], 0)
m = mergePlan(log2, [def('x3', 'Squat')], plan1)
assert.deepEqual(view(m), ['x2:Row:1/1', 'x3:Squat:0/3'])
m = mergePlan([def('x1', 'Bench'), def('x2', 'Row')].map(makeExercise), [def('x3', 'Squat')], plan1)
assert.deepEqual(view(m), ['x3:Squat:0/3'])

// Merging the same plan twice changes nothing.
const once = mergePlan(log2, [def('x2', 'Row'), def('x3', 'Squat')], plan1)
assert.deepEqual(view(mergePlan(once, [def('x2', 'Row'), def('x3', 'Squat')], plan1)), view(once))

console.log('merge_test: all assertions passed')

// Form videos (#152) stay on the exercise when the coach changes the plan.
const withVideo = plan1.map(makeExercise)
withVideo[0].media = [{ key: 'users/u/d/x1/a.mp4', type: 'video', at: 't' }]
m = mergePlan(withVideo, [def('x1', 'Bench', 4), def('x2', 'Row')], plan1)
assert.deepEqual(m[0].media, withVideo[0].media)
assert.deepEqual(m[1].media, [])
console.log('media ok')
