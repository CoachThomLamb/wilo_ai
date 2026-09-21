const express = require('express');
const db = require('./db');

const app = express();
app.use(express.urlencoded({ extended: true }));
app.use(express.json());

function weekOf(date) {
  const d = new Date(date);
  d.setDate(d.getDate() - d.getDay());
  return d.toISOString().slice(0, 10);
}

function esc(s) { return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }

function renderWorkout(program) {
  const allExercises = program.blocks.flatMap(b => b.exercises.map(ex => ({ ...ex, blockId: b.id })));

  const blocks = program.blocks.map(block => {
    const exercises = block.exercises.map(ex => `
      <div class="exercise" data-id="${esc(ex.id)}" data-block="${esc(block.id)}" data-lbs="${ex.start_weight_lbs || 0}">
        <div class="ex-head">
          <input class="ex-name-input" type="text" value="${esc(ex.name)}" placeholder="Exercise name">
        </div>
        ${ex.cue ? `<div class="cue">${esc(ex.cue)}</div>` : ''}
        <input class="custom-label-input" type="text" placeholder="+ custom field label (e.g. incline height)">
        <div class="sets"></div>
        <button type="button" class="add-set-btn ghost-sm">+ Add set</button>
      </div>
    `).join('');

    return `
      <div class="block">
        <div class="block-head">
          <h2>${esc(block.name)}</h2>
          ${block.notes ? `<p>${esc(block.notes)}</p>` : ''}
        </div>
        ${exercises}
      </div>
    `;
  }).join('');

  return `
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
<title>WILO — ${esc(program.name)}</title>
<style>
  :root { --bg:#000; --panel:#0e0e0f; --field:#1c1c1e; --line:#262628; --text:#f2f2f7; --dim:#7c7c82; --accent:#0a84ff; }
  * { box-sizing: border-box; -webkit-tap-highlight-color: transparent; }
  html, body { margin: 0; background: var(--bg); color: var(--text); font: 400 17px/1.3 -apple-system, BlinkMacSystemFont, sans-serif; }
  body { padding-bottom: 100px; }
  header { padding: 16px; border-bottom: 1px solid var(--line); display: flex; justify-content: space-between; align-items: center; }
  header h1 { margin: 0; font-size: 18px; }
  .block { margin-top: 1px; }
  .block-head { padding: 14px 16px 8px; background: var(--panel); border-bottom: 1px solid var(--line); }
  .block-head h2 { margin: 0; font-size: 14px; font-weight: 600; color: var(--dim); text-transform: uppercase; }
  .block-head p { margin: 4px 0 0; font-size: 13px; color: #5c5c62; }
  .exercise { padding: 16px; border-bottom: 1px solid var(--line); }
  .ex-head { margin-bottom: 4px; }
  .ex-name-input { background: transparent; border: 0; border-bottom: 1px solid transparent; color: var(--text); font-size: 16px; font-weight: 600; width: 100%; padding: 0 0 2px; font-family: inherit; }
  .ex-name-input:focus { outline: none; border-bottom-color: var(--accent); }
  .cue { font-size: 13px; color: var(--dim); margin-bottom: 10px; }
  .custom-label-input { background: transparent; border: 0; border-bottom: 1px solid var(--line); color: var(--dim); font-size: 13px; width: 100%; padding: 4px 0; margin-bottom: 12px; font-family: inherit; }
  .custom-label-input:focus { outline: none; border-bottom-color: var(--accent); color: var(--text); }
  .sets { display: flex; flex-direction: column; gap: 8px; margin-bottom: 10px; }
  .set { display: flex; align-items: center; gap: 8px; }
  .set-num { font-size: 13px; color: var(--dim); width: 42px; flex: none; }
  input[type=number] { background: var(--field); border: 1px solid var(--line); color: var(--text); border-radius: 8px; padding: 8px 10px; font-size: 16px; width: 72px; }
  input[type=text].custom-val { background: var(--field); border: 1px solid var(--line); color: var(--text); border-radius: 8px; padding: 8px 10px; font-size: 16px; width: 90px; font-family: inherit; }
  .done-wrap { display: flex; align-items: center; gap: 6px; font-size: 14px; color: var(--dim); }
  input[type=checkbox] { width: 20px; height: 20px; accent-color: var(--accent); }
  .ghost-sm { background: var(--field); color: var(--dim); border: 1px solid var(--line); border-radius: 999px; padding: 6px 14px; font-size: 14px; font-family: inherit; margin-top: 4px; }
  .add-ex-wrap { padding: 16px; }
  .add-ex-btn { width: 100%; background: var(--field); color: var(--accent); border: 1px solid var(--line); border-radius: 12px; padding: 14px; font-size: 16px; font-family: inherit; }
  .finish-wrap { position: fixed; bottom: 0; left: 0; right: 0; padding: 16px; background: var(--bg); border-top: 1px solid var(--line); }
  .finish-btn { width: 100%; background: var(--accent); color: #fff; border: 0; border-radius: 999px; padding: 14px; font-size: 17px; font-weight: 600; font-family: inherit; }
</style>
</head>
<body>
<header>
  <h1>${esc(program.name)}</h1>
  <span style="color:var(--dim);font-size:14px">${new Date().toLocaleDateString([], { weekday: 'short', month: 'short', day: 'numeric' })}</span>
</header>
<div id="workout">
  ${blocks}
  <div class="add-ex-wrap">
    <button type="button" class="add-ex-btn" id="addExBtn">+ Add exercise</button>
  </div>
</div>
<div class="finish-wrap">
  <button type="button" class="finish-btn" id="finishBtn">Finish</button>
</div>
<script>
  const SESSION_ID = ${JSON.stringify(program.id)};
  const SESSION_NAME = ${JSON.stringify(program.name)};

  function seedSets(exEl) {
    const lbs = parseFloat(exEl.dataset.lbs) || 0;
    const setsDiv = exEl.querySelector('.sets');
    if (setsDiv.children.length === 0) {
      const count = parseInt(exEl.dataset.sets || '3', 10);
      for (let i = 0; i < count; i++) addSet(exEl, lbs);
    }
  }

  function addSet(exEl, lbs) {
    const setsDiv = exEl.querySelector('.sets');
    const si = setsDiv.children.length;
    const customLabel = exEl.querySelector('.custom-label-input').value.trim();
    const row = document.createElement('div');
    row.className = 'set';
    row.innerHTML =
      '<span class="set-num">Set ' + (si + 1) + '</span>' +
      '<input type="number" class="lbs" value="' + (lbs || '') + '" placeholder="lbs" step="5">' +
      '<input type="number" class="reps" placeholder="reps">' +
      (customLabel ? '<input type="text" class="custom-val" placeholder="' + customLabel + '">' : '') +
      '<label class="done-wrap"><input type="checkbox" class="done"> Done</label>';
    setsDiv.appendChild(row);
    renumberSets(setsDiv);
  }

  function renumberSets(setsDiv) {
    Array.from(setsDiv.children).forEach((row, i) => {
      const num = row.querySelector('.set-num');
      if (num) num.textContent = 'Set ' + (i + 1);
    });
  }

  function initExercise(exEl) {
    const defaultLbs = parseFloat(exEl.dataset.lbs) || 0;
    exEl.querySelector('.add-set-btn').addEventListener('click', () => {
      const lastRow = exEl.querySelector('.sets').lastElementChild;
      const lastLbs = lastRow ? parseFloat(lastRow.querySelector('.lbs')?.value) || defaultLbs : defaultLbs;
      addSet(exEl, lastLbs);
    });
    exEl.querySelector('.custom-label-input').addEventListener('change', () => {
      const label = exEl.querySelector('.custom-label-input').value.trim();
      const setsDiv = exEl.querySelector('.sets');
      Array.from(setsDiv.children).forEach(row => {
        let cv = row.querySelector('.custom-val');
        if (label && !cv) {
          cv = document.createElement('input');
          cv.type = 'text';
          cv.className = 'custom-val';
          cv.placeholder = label;
          row.querySelector('.done-wrap').before(cv);
        } else if (!label && cv) {
          cv.remove();
        } else if (label && cv) {
          cv.placeholder = label;
        }
      });
    });
    seedSets(exEl);
  }

  document.querySelectorAll('.exercise').forEach(ex => {
    ex.dataset.sets = ex.querySelectorAll('.set').length || '3';
    initExercise(ex);
  });

  document.getElementById('addExBtn').addEventListener('click', () => {
    const name = prompt('Exercise name:');
    if (!name) return;
    const exEl = document.createElement('div');
    exEl.className = 'exercise';
    exEl.dataset.id = 'custom_' + Date.now();
    exEl.dataset.block = 'custom';
    exEl.dataset.lbs = '0';
    exEl.dataset.sets = '3';
    exEl.innerHTML =
      '<div class="ex-head"><input class="ex-name-input" type="text" value="' + name.replace(/"/g,'&quot;') + '" placeholder="Exercise name"></div>' +
      '<input class="custom-label-input" type="text" placeholder="+ custom field label">' +
      '<div class="sets"></div>' +
      '<button type="button" class="add-set-btn ghost-sm">+ Add set</button>';
    document.querySelector('.add-ex-wrap').before(exEl);
    initExercise(exEl);
  });

  document.getElementById('finishBtn').addEventListener('click', () => {
    const exercises = Array.from(document.querySelectorAll('.exercise')).map(exEl => ({
      id: exEl.dataset.id,
      name: exEl.querySelector('.ex-name-input').value,
      blockId: exEl.dataset.block,
      customLabel: exEl.querySelector('.custom-label-input').value.trim() || null,
      sets: Array.from(exEl.querySelectorAll('.sets .set')).map(row => ({
        lbs: parseFloat(row.querySelector('.lbs')?.value) || 0,
        reps: parseInt(row.querySelector('.reps')?.value, 10) || 0,
        done: row.querySelector('.done')?.checked || false,
        custom: row.querySelector('.custom-val')?.value || null
      }))
    }));

    fetch('/finish', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: SESSION_ID, session_name: SESSION_NAME, exercises })
    }).then(r => r.text()).then(html => {
      document.open(); document.write(html); document.close();
    });
  });
</script>
</body>
</html>`;
}

function renderDone(sessionName, sets) {
  return `
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
<title>WILO — Done</title>
<style>
  body { margin: 0; background: #000; color: #f2f2f7; font: 400 17px/1.3 -apple-system, sans-serif; display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100vh; gap: 12px; }
  h1 { margin: 0; font-size: 28px; color: #34c759; }
  p { margin: 0; color: #7c7c82; }
  a { color: #0a84ff; text-decoration: none; font-size: 15px; }
</style>
</head>
<body>
  <h1>Done</h1>
  <p>${sessionName} — ${sets} sets logged</p>
  <a href="/">Back to today</a>
</body>
</html>`;
}

app.get('/', (req, res) => {
  const today = new Date();
  const week = weekOf(today);
  const dayOfWeek = today.getDay();

  const row = db.prepare('SELECT data FROM microcycles WHERE week_of = ?').get(week);
  if (!row) {
    res.set('Cache-Control', 'no-store');
    return res.send('<h1 style="color:#fff;background:#000;padding:40px;font-family:sans-serif">No program for this week</h1>');
  }

  const mc = JSON.parse(row.data);
  const program = mc.programs.find(p => p.day === dayOfWeek);
  if (!program) {
    res.set('Cache-Control', 'no-store');
    return res.send('<h1 style="color:#fff;background:#000;padding:40px;font-family:sans-serif">Rest day</h1>');
  }

  res.set('Cache-Control', 'public, max-age=86400');
  res.send(renderWorkout(program));
});

app.get('/week', (req, res) => {
  const today = new Date();
  const week = weekOf(today);

  const row = db.prepare('SELECT data FROM microcycles WHERE week_of = ?').get(week);
  const mc = row ? JSON.parse(row.data) : null;

  const days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
  const scheduleByDay = {};
  (mc?.programs || []).forEach(p => { scheduleByDay[p.day] = p.name; });

  const sessionRows = db.prepare(`
    SELECT session_name, finished_at FROM sessions
    WHERE finished_at >= ? AND finished_at <= ?
    ORDER BY finished_at ASC
  `).all(`${week}T00:00:00`, `${week}T23:59:59`.replace(week, addDays(week, 6)));

  const doneByDay = {};
  sessionRows.forEach(r => {
    const d = new Date(r.finished_at).getDay();
    doneByDay[d] = r.session_name;
  });

  const rows = days.map((name, d) => {
    const plan = scheduleByDay[d] || '—';
    const done = doneByDay[d] || '—';
    const isToday = d === today.getDay();
    return `<tr style="${isToday ? 'background:#0e0e0f' : ''}">
      <td>${name}</td>
      <td>${plan}</td>
      <td style="color:${doneByDay[d] ? '#34c759' : '#3a3a3e'}">${done}</td>
    </tr>`;
  }).join('');

  res.set('Cache-Control', 'no-store');
  res.send(`
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
<title>WILO — Week</title>
<style>
  body { margin: 0; background: #000; color: #f2f2f7; font: 400 15px/1.4 -apple-system, sans-serif; padding: 16px; }
  h1 { font-size: 18px; margin: 0 0 16px; }
  table { width: 100%; border-collapse: collapse; }
  th { text-align: left; color: #7c7c82; font-weight: 500; padding: 8px 0; border-bottom: 1px solid #262628; }
  td { padding: 12px 0; border-bottom: 1px solid #1c1c1e; }
  a { color: #0a84ff; text-decoration: none; display: block; margin-top: 24px; font-size: 15px; }
</style>
</head>
<body>
  <h1>Week of ${week}</h1>
  <table>
    <thead><tr><th>Day</th><th>Plan</th><th>Done</th></tr></thead>
    <tbody>${rows}</tbody>
  </table>
  <a href="/">Today's workout</a>
</body>
</html>`);
});

app.post('/finish', (req, res) => {
  const { session_id, session_name, exercises } = req.body;
  const doneSets = (exercises || []).flatMap(e => e.sets || []).filter(s => s.done).length;
  const finishedAt = new Date().toISOString();

  db.prepare('INSERT INTO sessions (session_id, session_name, finished_at, data) VALUES (?, ?, ?, ?)').run(
    session_id, session_name, finishedAt, JSON.stringify({ session_id, session_name, finishedAt, exercises })
  );

  res.send(renderDone(session_name, doneSets));
});

function addDays(isoDate, n) {
  const d = new Date(isoDate);
  d.setDate(d.getDate() + n);
  return d.toISOString().slice(0, 10);
}

const PORT = process.env.PORT || 3000;
app.listen(PORT, '0.0.0.0', () => {
  console.log(`WILO server running on http://0.0.0.0:${PORT}`);
  console.log(`Local:   http://localhost:${PORT}`);
  const { networkInterfaces } = require('os');
  const nets = networkInterfaces();
  for (const name of Object.keys(nets)) {
    for (const net of nets[name]) {
      if (net.family === 'IPv4' && !net.internal) {
        console.log(`Network: http://${net.address}:${PORT}`);
      }
    }
  }
});
