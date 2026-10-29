"""Review real messages and label what the tool caller should do: Thom's labels become the training/test targets.

    python ml/review.py            # → http://localhost:8765

For each real message (ml/toolcall_eval.jsonl) you see the conversation before it, what Wilo (Claude) called in the
real chat, and what each scored model called (latest file per model in ml/results/). Pick one of those or write your
own call, add a note, save. Labels go to ml/labels.jsonl (one line per item, rewritten on every save). Local only:
nothing runs against WILO data.
"""
import json
import re
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
LABELS = HERE / 'labels.jsonl'
PORT = 8765


def load():
    items = [json.loads(l) for l in open(HERE / 'toolcall_eval.jsonl')]
    test = {json.loads(l)['id'] for l in open(HERE / 'test.jsonl')}
    # Every results file (<model>-<YYYYMMDD-HHMM>.jsonl), oldest first, so each item shows its newest output per model.
    outputs, models = {}, set()
    for f in sorted((HERE / 'results').glob('*.jsonl'), key=lambda f: f.stem[-13:]):
        model = re.sub(r'-\d{8}-\d{4}$', '', f.stem)
        models.add(model)
        for l in open(f):
            r = json.loads(l)
            outputs.setdefault(r['id'], {})[model] = r['got']
    labels = {}
    if LABELS.exists():
        for l in open(LABELS):
            r = json.loads(l)
            labels[r['id']] = r
    tools = [t['function']['name'] for t in json.loads((HERE / 'wilo_tools.json').read_text())]
    return {'items': [dict(i, split='test' if i['id'] in test else 'seed', outputs=outputs.get(i['id'], {}))
                      for i in items],
            'labels': labels, 'tools': tools, 'models': sorted(models)}


def save_label(rec):
    labels = load()['labels']
    labels[rec['id']] = rec
    LABELS.write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in labels.values()))


class Handler(BaseHTTPRequestHandler):
    def send(self, body, ctype):
        data = body.encode()
        self.send_response(200)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == '/api/data':
            self.send(json.dumps(load(), ensure_ascii=False), 'application/json')
        else:
            self.send(PAGE, 'text/html; charset=utf-8')

    def do_POST(self):
        rec = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        save_label(rec)
        self.send('{"ok": true}', 'application/json')

    def log_message(self, *a):
        pass


PAGE = r"""<!doctype html><html><head><meta charset="utf-8"><title>WILO label review</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
:root{--bg:#fafaf8;--fg:#1d1d1b;--mut:#6b6b66;--line:#e2e1dc;--card:#fff;--acc:#2f6fdf;--ok:#1f8a4c;--bad:#c2410c}
@media (prefers-color-scheme:dark){:root{--bg:#161615;--fg:#e8e7e3;--mut:#9a9a94;--line:#2c2c2a;--card:#1e1e1c;--acc:#6b9cf0;--ok:#4cc27f;--bad:#f08a5d}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:14px/1.45 system-ui,sans-serif;display:flex;height:100vh}
#list{width:260px;border-right:1px solid var(--line);overflow:auto;flex-shrink:0}
#list .f{padding:8px;border-bottom:1px solid var(--line);display:flex;gap:6px;flex-wrap:wrap}
#list button.it{display:block;width:100%;text-align:left;border:0;border-bottom:1px solid var(--line);background:none;color:inherit;padding:6px 10px;cursor:pointer;font:inherit}
#list button.it.cur{background:var(--card);box-shadow:inset 3px 0 var(--acc)}
.done{color:var(--ok)}.mut{color:var(--mut)}.small{font-size:12px}
#main{flex:1;overflow:auto;padding:16px 20px;max-width:1300px}
.msg{padding:6px 10px;border-radius:8px;margin:4px 0;max-width:80%;white-space:pre-wrap;word-break:break-word}
.u{background:var(--card);border:1px solid var(--line);margin-left:auto}.a{background:transparent;border:1px dashed var(--line)}
.now{border:2px solid var(--acc);font-weight:600}
.tools{font-size:12px;color:var(--mut)}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:10px;margin:14px 0}
.card{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:10px;font-size:13px}
.card h4{margin:0 0 6px;font-size:13px}.card pre{white-space:pre-wrap;word-break:break-word;margin:6px 0;font-size:12px;max-height:260px;overflow:auto}
button{font:inherit;cursor:pointer;border:1px solid var(--line);background:var(--card);color:var(--fg);border-radius:6px;padding:4px 10px}
button.pri{background:var(--acc);color:#fff;border-color:var(--acc)}
textarea,select,input{font:12px ui-monospace,monospace;width:100%;background:var(--card);color:var(--fg);border:1px solid var(--line);border-radius:6px;padding:6px}
.row{display:flex;gap:10px;align-items:center;margin:6px 0}
.tag{font-size:11px;padding:1px 6px;border-radius:10px;border:1px solid var(--line)}
</style></head><body>
<div id="list"><div class="f"><label class="small"><input type="checkbox" id="onlyOpen" style="width:auto"> unlabeled only</label>
<select id="split" style="width:auto"><option value="">all</option><option value="test">test</option><option value="seed">seed</option></select>
<span id="count" class="small mut"></span></div><div id="items"></div></div>
<div id="main"></div>
<script>
let D, cur = 0;
const $ = s => document.querySelector(s);
const esc = s => String(s ?? '').replace(/[&<>]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
function wsum(w){ if(!w||!Array.isArray(w.exercises)) return ''; return (w.name||'')+(w.assignedFor?' · for '+w.assignedFor:'')+'\n'+
  w.exercises.map((e,i)=>`${i+1}. ${e.name} ${(e.sets||[]).length}x${(e.sets||[])[0]?.reps??''}${(e.sets||[])[0]?.lbs?' @ '+e.sets[0].lbs:''}`).join('\n'); }
function show(call){
  if(!call) return '<span class="mut">not scored</span>';
  if(call.tool===null||call.tool===undefined) return '<b>no tool</b>'+(call.text?`<pre>${esc(call.text.slice(0,300))}</pre>`:'');
  const a = {...(call.args||{})}; const w = a.workout; delete a.workout;
  return `<b>${esc(call.tool)}</b><pre>${esc(JSON.stringify(a,null,1))}</pre>`+(w?`<pre>${esc(wsum(w))}</pre>`:'');
}
function visible(){ return D.items.map((it,i)=>[it,i]).filter(([it])=>(!$('#split').value||it.split===$('#split').value)&&(!$('#onlyOpen').checked||!D.labels[it.id])); }
function renderList(){
  const v = visible(); $('#count').textContent = `${Object.keys(D.labels).length}/${D.items.length} labeled`;
  $('#items').innerHTML = v.map(([it,i])=>`<button class="it ${i===cur?'cur':''}" data-i="${i}">
    <span class="${D.labels[it.id]?'done':''}">${D.labels[it.id]?'✓':'·'}</span> <span class="small mut">${it.split} ${it.date}</span><br>
    ${esc(it.message.slice(0,60))}</button>`).join('');
  document.querySelectorAll('button.it').forEach(b=>b.onclick=()=>{cur=+b.dataset.i;render();});
}
function render(){
  renderList(); const it = D.items[cur], lab = D.labels[it.id];
  const ctx = it.context.map(c=>`<div class="msg ${c.role==='user'?'u':'a'}">${esc(c.text||'(no text)')}${c.tools?`<div class="tools">called: ${esc(c.tools.join(', '))}</div>`:''}</div>`).join('');
  const scr = it.screen?`Tracker: "${esc(it.screen.name||'workout')}" on screen (${esc(it.screen.assignedDocId)})`:'Tracker: no workout loaded';
  const cards = [['Wilo (real chat)', it.expected, 'wilo']].concat(D.models.map(m=>[m, it.outputs[m], m]));
  const init = lab ? lab.expected : it.expected;
  $('#main').innerHTML = `
   <div class="row"><b>${esc(it.id)}</b><span class="tag">${it.split}</span><span class="mut small">${it.date} · ${esc(it.source)}</span>
     <span style="flex:1"></span><button id="prev">← prev</button><button id="next">next →</button></div>
   ${it.review?`<div class="small">earlier review note: ${esc(it.review)}</div>`:''}
   ${ctx}<div class="small mut" style="text-align:right">${scr}</div><div class="msg u now">${esc(it.message)}</div>
   <div class="cards">${cards.map(([n,c,k])=>`<div class="card"><h4>${esc(n)}</h4>${show(c)}
     ${c&&c.tool!=='_error'?`<button data-pick="${k}">use this</button>`:''}</div>`).join('')}</div>
   <div class="card"><h4>Your label ${lab?`<span class="done small">saved (${esc(lab.picked)})</span>`:''}</h4>
     <div class="row"><select id="tool" style="width:220px"><option value="">no tool</option>${D.tools.map(t=>`<option>${t}</option>`).join('')}</select>
       <span class="small mut">args as JSON</span></div>
     <textarea id="args" rows="8"></textarea>
     <input id="note" placeholder="note: why (what you'd do as the coach)" value="${esc(lab?.note||'')}">
     <div class="row"><button class="pri" id="save">save + next</button><span id="msg" class="small"></span></div></div>`;
  let picked = lab?.picked || 'custom';
  const fill = (c,k) => { $('#tool').value = c?.tool||''; $('#args').value = c?.tool?JSON.stringify(c.args||{},null,1):''; picked = k; };
  fill(init, picked);
  document.querySelectorAll('[data-pick]').forEach(b=>b.onclick=()=>{const k=b.dataset.pick; fill(k==='wilo'?it.expected:it.outputs[k], k);});
  $('#tool').onchange = $('#args').oninput = () => picked = 'custom';
  $('#prev').onclick = () => go(-1); $('#next').onclick = () => go(1);
  $('#save').onclick = async () => {
    let args = null;
    if($('#tool').value){ try{ args = JSON.parse($('#args').value||'{}'); }catch(e){ $('#msg').textContent='args are not valid JSON'; $('#msg').className='small bad'; return; } }
    const rec = {id: it.id, expected: {tool: $('#tool').value||null, args}, picked, note: $('#note').value, wilo: it.expected.tool, saved: new Date().toISOString()};
    await fetch('/api/label', {method:'POST', body: JSON.stringify(rec)}); D.labels[it.id] = rec; go(1);
  };
}
function go(d){ const v = visible().map(([,i])=>i); const p = v.indexOf(cur); cur = v[Math.max(0, Math.min(v.length-1, (p<0?0:p+d)))] ?? cur; render(); }
document.addEventListener('keydown', e => { if(['TEXTAREA','INPUT','SELECT'].includes(e.target.tagName)) return;
  if(e.key==='j'||e.key==='ArrowRight') go(1); if(e.key==='k'||e.key==='ArrowLeft') go(-1); });
$('#onlyOpen').onchange = $('#split').onchange = () => { renderList(); };
fetch('/api/data').then(r=>r.json()).then(d=>{ D = d; render(); });
</script></body></html>"""


def main():
    srv = ThreadingHTTPServer(('127.0.0.1', PORT), Handler)
    print(f'review at http://localhost:{PORT}  (labels → {LABELS})')
    webbrowser.open(f'http://localhost:{PORT}')
    srv.serve_forever()


if __name__ == '__main__':
    main()
