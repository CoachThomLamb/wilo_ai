/*
  Voice coach, option 2 (#78 spike): Claude, one turn at a time.

  Tap the mic once to start a conversation. Each turn: the browser's speech
  recognition (Web Speech API) hears one sentence, /coach/turn on the
  connector sends it to Claude with the workout on screen and the recent
  conversation, the tracker runs Claude's tool calls (window.wiloTracker.apply),
  and the browser speaks the reply. Then it listens again. Tap to stop.
*/

const API = /^(localhost|127\.0\.0\.1)$/.test(location.hostname)
  ? 'http://localhost:8000' : 'https://wilo-connector.onrender.com';

const btn = document.getElementById('micBtn');
const tracker = () => window.wiloTracker;
const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
let on = false, rec = null;
const history = [];   // text-only turns, sent with each request

function setMode(mode) { btn.className = 'mic' + (mode ? ' ' + mode : ''); }

function listen() {
  if (!on) return;
  rec = new Recognition();
  rec.lang = 'en-US';
  rec.interimResults = false;
  let heard = '';
  rec.onresult = e => { heard = e.results[0][0].transcript; };
  rec.onerror = e => { if (e.error !== 'no-speech' && e.error !== 'aborted') stop('Mic: ' + e.error); };
  rec.onend = () => { rec = null; heard ? turn(heard) : listen(); };
  setMode('live');
  rec.start();
}

async function turn(text) {
  setMode('connecting');
  tracker().note('You: ' + text);
  try {
    const user = window.__auth.currentUser();
    const r = await fetch(API + '/coach/turn', {
      method: 'POST',
      headers: { Authorization: 'Bearer ' + await user.getIdToken(), 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, workout: tracker().summary(), history }),
    });
    const body = await r.json();
    if (!r.ok) throw new Error(body.error || 'HTTP ' + r.status);
    const results = body.ops.map(op => tracker().apply(op.name, op.args));
    const failed = results.filter(x => !x.ok).map(x => x.error);
    history.push({ role: 'user', content: text },
      { role: 'assistant', content: body.say + (failed.length ? ' [failed: ' + failed.join('; ') + ']' : '') });
    if (failed.length) tracker().note("Coach couldn't: " + failed.join('; '), 'err');
    await speak(body.say);
    listen();
  } catch (err) {
    stop('Coach failed: ' + (err.message || err));
  }
}

function speak(text) {
  return new Promise(resolve => {
    if (!text || !on) return resolve();
    const u = new SpeechSynthesisUtterance(text);
    u.onend = u.onerror = resolve;
    speechSynthesis.speak(u);
  });
}

function start() {
  if (!Recognition) return tracker().note("This browser can't do speech recognition", 'err');
  if (!window.__auth || !window.__auth.currentUser()) return tracker().note('Sign in to talk to your coach', 'err');
  on = true;
  // iOS only speaks after a tap has spoken once: prime it inside this tap.
  speechSynthesis.speak(new SpeechSynthesisUtterance(''));
  tracker().note('Coach is listening', 'ok');
  listen();
}

function stop(msg) {
  on = false;
  if (rec) rec.abort();
  speechSynthesis.cancel();
  setMode('');
  if (msg) tracker().note(msg, /failed|Mic:/.test(msg) ? 'err' : undefined);
}

btn.addEventListener('click', () => on ? stop('Coach stopped') : start());
