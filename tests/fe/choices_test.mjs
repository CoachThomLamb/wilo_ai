// #246: tap-to-answer buttons in the coach chat. Run with: node tests/fe/choices_test.mjs
// Extracts choiceState, choiceRow, pick and closeChoices from fe/chat.js verbatim and runs them on a tiny fake DOM.
import { readFileSync } from 'node:fs'
import assert from 'node:assert/strict'

const src = readFileSync(new URL('../../fe/chat.js', import.meta.url), 'utf8')
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

// A fake DOM: just enough for the functions under test.
class El {
  constructor(tag) { this.tag = tag; this.children = []; this.className = ''; this.textContent = ''; this.disabled = false
    this.handlers = {}; const set = new Set(); this.classList = { add: c => set.add(c), contains: c => set.has(c) } }
  append(...els) { this.children.push(...els) }
  addEventListener(ev, fn) { this.handlers[ev] = fn }
  click() { if (!this.disabled) this.handlers.click() }
  // Supports ".a.b" (all classes on a direct child) and a tag name, which is all the code uses.
  querySelectorAll(sel) {
    const match = sel.startsWith('.')
      ? el => sel.slice(1).split('.').every(c => el.className.split(' ').includes(c))
      : el => el.tag === sel
    return this.children.filter(match)
  }
}
const document = { createElement: tag => new El(tag) }
const log = new El('div')
const input = { value: '' }
const sent = []
const form = { requestSubmit: () => sent.push(input.value) }
let saves = 0
const save = () => saves++
let busy = false

const choiceState = eval(`(${extract('choiceState')})`)
const choiceRow = eval(`(${extract('choiceRow')})`)
const closeChoices = eval(`(${extract('closeChoices')})`)
const pick = eval(`(${extract('pick')})`)

// States: only Wilo's latest message with unanswered choices is open.
const ask = { role: 'coach', text: 'Drop to 115?', choices: ['Yes', 'No'] }
assert.equal(choiceState([ask], 0), 'open')
assert.equal(choiceState([ask, { role: 'me', text: 'actually 120' }], 0), 'passed', 'typed instead of tapping')
assert.equal(choiceState([{ ...ask, picked: 'No' }, { role: 'me', text: 'No' }], 0), 'answered')
assert.equal(choiceState([{ role: 'coach', text: 'hi' }], 0), 'none')
assert.equal(choiceState([{ role: 'me', text: 'x', choices: ['a', 'b'] }], 0), 'none', 'only Wilo offers choices')
assert.equal(choiceState([{ role: 'coach', text: 'x', choices: [] }], 0), 'none')
assert.equal(choiceRow([{ role: 'coach', text: 'hi' }], 0), null, 'no row without choices')

// An open row: one enabled button per option, labels as text.
const messages = [ask]
const row = choiceRow(messages, 0)
assert.equal(row.className, 'choices open')
assert.deepEqual(row.children.map(b => b.textContent), ['Yes', 'No'])
assert.ok(row.children.every(b => !b.disabled && b.type === 'button'))

// Busy (a message in flight): a tap does nothing.
busy = true
row.children[0].click()
assert.equal(ask.picked, undefined)
assert.deepEqual(sent, [])
busy = false

// Tap: sends the label as the user's message, saves the pick, greys the row out with the pick highlighted.
row.children[1].click()
assert.equal(ask.picked, 'No')
assert.deepEqual(sent, ['No'])
assert.ok(saves > 0)
assert.equal(row.className, 'choices answered')
assert.ok(row.children.every(b => b.disabled))
assert.ok(row.children[1].classList.contains('picked'))
assert.ok(!row.children[0].classList.contains('picked'))
row.children[0].click()   // disabled: a second tap sends nothing
assert.deepEqual(sent, ['No'])

// Reload: an answered row comes back greyed out, the pick highlighted.
const again = choiceRow(messages, 0)
assert.equal(again.className, 'choices answered')
assert.ok(again.children.every(b => b.disabled))
assert.ok(again.children[1].classList.contains('picked'))

// Typing instead of tapping: the open row is passed by, nothing highlighted.
const other = { role: 'coach', text: 'Which day?', choices: ['Mon', 'Wed', 'Fri'] }
const open = choiceRow([other], 0)
closeChoices(null)
assert.equal(open.className, 'choices passed')
assert.ok(open.children.every(b => b.disabled && !b.classList.contains('picked')))

console.log('choices_test: all assertions passed')
