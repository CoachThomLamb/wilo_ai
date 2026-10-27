// #100: the coach's cue and the user's note are separate fields. Run with: node tests/fe/cue_note_test.mjs
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
const deriveExId = name => (name || '').toLowerCase().replace(/\s+/g, '-').replace(/[^a-z0-9-]/g, '')
const makeExercise = eval(`(${extract('makeExercise')})`)
const mergePlan = eval(`(${extract('mergePlan')})`)

// Loading a plan: the cue is the coach's, the note starts empty.
const ex = makeExercise({ instanceId: 'ex-1', name: 'Dumbbell RDL', cue: 'slow on the way down', sets: 3, target: { reps: 8 } })
assert.equal(ex.cue, 'slow on the way down')
assert.equal(ex.note, '')

// Mid-workout: the user typed a note, then the coach swaps the exercise with a new cue.
const current = [{ ...ex, note: 'left hamstring tight' }]
const [merged] = mergePlan(current, [{ instanceId: 'ex-1', name: 'Back Squat', cue: 'brace first', sets: 3, target: { reps: 5 } }])
assert.equal(merged.name, 'Back Squat', "the coach's swap wins")
assert.equal(merged.cue, 'brace first', "the coach's new cue")
assert.equal(merged.note, 'left hamstring tight', "the user's note stays")

console.log('cue_note_test: all assertions passed')
