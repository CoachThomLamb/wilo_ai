const express = require('express');
const db = require('./db');

const app = express();
app.use(express.urlencoded({ extended: true }));

function weekOf(date) {
  const d = new Date(date);
  d.setDate(d.getDate() - d.getDay());
  return d.toISOString().slice(0, 10);
}

function renderWorkout(program) {
  const blocks = program.blocks.map(block => {
    const exercises = block.exercises.map((ex, ei) => `
      <div class="exercise">
        <div class="ex-name">${ex.name}</div>
        ${ex.cue ? `<div class="cue">${ex.cue}</div>` : ''}
        <div class="sets">
          ${Array.from({ length: ex.sets }, (_, si) => `
            <div class="set">
              <span class="set-num">Set ${si + 1}</span>
              <input type="number" name="ex_${ei}_set_${si}_lbs" value="${ex.start_weight_lbs || ''}" placeholder="lbs" step="5">
              <input type="number" name="ex_${ei}_set_${si}_reps" placeholder="reps">
              <label class="done-wrap">
                <input type="checkbox" name="ex_${ei}_set_${si}_done"> Done
              </label>
            </div>
          `).join('')}
        </div>
        <input type="hidden" name="ex_${ei}_id" value="${ex.id}">
        <input type="hidden" name="ex_${ei}_name" value="${ex.name}">
        <input type="hidden" name="ex_${ei}_block" value="${block.id}">
        <input type="hidden" name="ex_${ei}_sets_count" value="${ex.sets}">
      </div>
    `).join('');

    return `
      <div class="block">
        <div class="block-head">
          <h2>${block.name}</h2>
          ${block.notes ? `<p>${block.notes}</p>` : ''}
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
<title>WILO — ${program.name}</title>
<style>
  :root { --bg:#000; --panel:#0e0e0f; --field:#1c1c1e; --line:#262628; --text:#f2f2f7; --dim:#7c7c82; --accent:#0a84ff; --done:#1f4a2c; --done-line:#34c759; }
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
  .ex-name { font-size: 16px; font-weight: 600; margin-bottom: 4px; }
  .cue { font-size: 13px; color: var(--dim); margin-bottom: 12px; }
  .sets { display: flex; flex-direction: column; gap: 8px; }
  .set { display: flex; align-items: center; gap: 8px; }
  .set-num { font-size: 13px; color: var(--dim); width: 42px; flex: none; }
  input[type=number] { background: var(--field); border: 1px solid var(--line); color: var(--text); border-radius: 8px; padding: 8px 10px; font-size: 16px; width: 72px; }
  .done-wrap { display: flex; align-items: center; gap: 6px; font-size: 14px; color: var(--dim); margin-left: 4px; }
  input[type=checkbox] { width: 20px; height: 20px; accent-color: var(--accent); }
  .finish-wrap { position: fixed; bottom: 0; left: 0; right: 0; padding: 16px; background: var(--bg); border-top: 1px solid var(--line); }
  button[type=submit] { width: 100%; background: var(--accent); color: #fff; border: 0; border-radius: 999px; padding: 14px; font-size: 17px; font-weight: 600; }
</style>
</head>
<body>
<header>
  <h1>${program.name}</h1>
  <span style="color:var(--dim);font-size:14px">${new Date().toLocaleDateString([], { weekday: 'short', month: 'short', day: 'numeric' })}</span>
</header>
<form method="POST" action="/finish">
  <input type="hidden" name="session_id" value="${program.id}">
  <input type="hidden" name="session_name" value="${program.name}">
  <input type="hidden" name="ex_count" value="${program.blocks.reduce((n, b) => n + b.exercises.length, 0)}">
  ${blocks}
  <div class="finish-wrap">
    <button type="submit">Finish</button>
  </div>
</form>
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
  const { session_id, session_name, ex_count, ...fields } = req.body;
  const count = parseInt(ex_count, 10);

  const exercises = [];
  for (let ei = 0; ei < count; ei++) {
    const setCount = parseInt(fields[`ex_${ei}_sets_count`], 10);
    const sets = [];
    for (let si = 0; si < setCount; si++) {
      sets.push({
        lbs: parseFloat(fields[`ex_${ei}_set_${si}_lbs`]) || 0,
        reps: parseInt(fields[`ex_${ei}_set_${si}_reps`], 10) || 0,
        done: !!fields[`ex_${ei}_set_${si}_done`]
      });
    }
    exercises.push({ id: fields[`ex_${ei}_id`], name: fields[`ex_${ei}_name`], blockId: fields[`ex_${ei}_block`], sets });
  }

  const doneSets = exercises.flatMap(e => e.sets).filter(s => s.done).length;
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
