/*
  WILO coach chat — a full-screen sheet in the tracker that talks to the
  connector server's POST /chat (wilo/chat.py). The server runs the coach
  over the same tools Claude uses through the connector, so a plan made
  here lands in users/{uid}/assigned like one made in the Claude app.

  - Auth: the signed-in user's Firebase ID token, sent as a Bearer token.
    The server checks it and decides whose data the coach touches.
  - One chat per workout (and per day): loading a different workout starts
    a new chat, so a chat stays short and each call resends less
    (wilo-ops#13). Finish keeps it, so the user can talk the workout over. The server freezes the coach's context (date, profile)
    when a chat starts. "New" starts one sooner. The chat id and the transcript we show are kept in
    localStorage (this phone only; the server keeps the real history).
  - Wake-up: Render's free tier sleeps after 15 min, so opening the sheet
    pings /chat first and the first reply isn't stuck behind a cold start.

  Needs the page's #chatBtn, #chatSheet, #chatLog, #chatForm, #chatInput,
  #chatNew, #chatClose, and window.__auth from auth.js.
*/

const LOCAL = /^(localhost|127\.0\.0\.1)$/.test(location.hostname);
const SERVER = LOCAL ? "http://localhost:8000" : "https://wilo-connector.onrender.com";
const KEY = "wilo-chat";
const KEEP = 60;   // messages kept for display

const $ = id => document.getElementById(id);
const sheet = $("chatSheet"), log = $("chatLog"), form = $("chatForm"), input = $("chatInput");
const today = () => new Date().toLocaleDateString("en-CA");   // YYYY-MM-DD, local
// Which conversation this is: today + the workout on screen, from index.html.
const scope = () => today() + "|" + ((window.__workoutScope && window.__workoutScope()) || "");

function load() {
  try {
    const saved = JSON.parse(localStorage.getItem(KEY) || "null");
    if (saved && saved.scope === scope()) return saved;
  } catch {}
  return { scope: scope(), chatId: null, messages: [] };
}
let chat = load();

function save() {
  chat.messages = chat.messages.slice(-KEEP);
  try { localStorage.setItem(KEY, JSON.stringify(chat)); } catch {}
}

function bubble(role, text) {
  const el = document.createElement("div");
  el.className = "msg " + role;
  el.textContent = text;   // text only: never render the reply as HTML
  log.appendChild(el);
  log.scrollTop = log.scrollHeight;
  return el;
}

function draw() {
  log.replaceChildren();
  if (!chat.messages.length)
    bubble("hint", "Ask Wilo: plan this week, swap an exercise, how did bench go?\nHold a message to copy it.");
  for (const m of chat.messages) bubble(m.role, m.text);
}

function wake() {
  fetch(SERVER + "/chat", { method: "OPTIONS" }).catch(() => {});
}

async function send(text) {
  const user = window.__auth && window.__auth.currentUser();
  if (!user) { bubble("err", "Sign in first."); return; }
  chat.messages.push({ role: "me", text });
  log.querySelectorAll(".hint").forEach(el => el.remove());
  bubble("me", text);
  save();
  const wait = bubble("coach pending", "Thinking…");
  const slow = setTimeout(() => { wait.textContent = "Still thinking (the server may be waking up)…"; }, 12000);
  try {
    const res = await fetch(SERVER + "/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: "Bearer " + await user.getIdToken() },
      // The workout on screen (index.html), so Wilo knows what "this workout" is.
      body: JSON.stringify({ message: text, chatId: chat.chatId, workout: (window.__workoutInfo && window.__workoutInfo()) || null }),
    });
    const body = await res.json().catch(() => ({}));
    if (res.status === 404) chat.chatId = null;   // chat gone: the next message starts a new one
    if (!res.ok) throw new Error(body.error || "HTTP " + res.status);
    chat.chatId = body.chatId;
    const reply = body.reply || "(no reply)";
    chat.messages.push({ role: "coach", text: reply });
    wait.className = "msg coach";
    wait.textContent = reply;
    // Its own bubble, so copying the coach's reply copies only the reply.
    if ((body.tools || []).some(t => t === "assign_workout" || t === "update_workout")) {
      const tip = "If Wilo saved a workout, tap Load to get it.";
      chat.messages.push({ role: "note", text: tip });
      bubble("note", tip);
    }
  } catch (err) {
    wait.className = "msg err";
    wait.textContent = "Couldn't reach Wilo: " + (err.message || err);
  } finally {
    clearTimeout(slow);
    save();
    log.scrollTop = log.scrollHeight;
  }
}

// ---- hold to copy ---------------------------------------------------
// On a phone, a long press selects one word and the handles rarely grab a
// whole reply. Holding a bubble copies all of it instead. The copy runs on
// release (pointerup), because iOS only lets a user gesture write to the
// clipboard; the timer just marks the bubble as held. Moving or scrolling
// cancels. Touch screens get no text selection on bubbles (CSS), so the
// system callout doesn't fight this; with a mouse, selection still works.
const HOLD = 450;   // ms
let press = null;

async function copy(text) {
  try { await navigator.clipboard.writeText(text); return true; } catch {}
  const ta = document.createElement("textarea");   // older iOS: execCommand on a hidden field
  ta.value = text;
  ta.setAttribute("readonly", "");
  ta.style.cssText = "position:fixed;top:0;opacity:0";
  document.body.appendChild(ta);
  ta.select();
  ta.setSelectionRange(0, text.length);
  let ok = false;
  try { ok = document.execCommand("copy"); } catch {}
  ta.remove();
  return ok;
}

function release() {
  if (!press) return;
  clearTimeout(press.timer);
  press.el.classList.remove("held");
  press = null;
}

log.addEventListener("pointerdown", ev => {
  const el = ev.target.closest(".msg.me, .msg.coach");
  if (!el || el.classList.contains("pending")) return;
  release();
  press = { el, x: ev.clientX, y: ev.clientY, timer: setTimeout(() => el.classList.add("held"), HOLD) };
});
log.addEventListener("pointermove", ev => {
  if (press && Math.hypot(ev.clientX - press.x, ev.clientY - press.y) > 10) release();
});
log.addEventListener("pointercancel", release);   // the browser took over to scroll
log.addEventListener("pointerup", async () => {
  if (!press) return;
  const el = press.el, held = el.classList.contains("held");
  release();
  if (!held) return;
  const ok = await copy(el.textContent);
  el.dataset.flash = ok ? "Copied" : "Couldn't copy";
  el.classList.add("flash");
  setTimeout(() => el.classList.remove("flash"), 1200);
});
// Android opens a context menu on long press; the hold already copies.
log.addEventListener("contextmenu", ev => { if (ev.target.closest(".msg")) ev.preventDefault(); });

$("chatBtn").addEventListener("click", () => {
  if (chat.scope !== scope()) chat = load();
  draw();
  sheet.classList.add("open");
  wake();
});
$("chatClose").addEventListener("click", () => sheet.classList.remove("open"));
$("chatNew").addEventListener("click", () => {
  chat = { scope: scope(), chatId: null, messages: [] };
  save();
  draw();
  input.focus();
});

let busy = false;
form.addEventListener("submit", async ev => {
  ev.preventDefault();
  const text = input.value.trim();
  if (!text || busy) return;
  busy = true;
  input.value = "";
  form.querySelector("button").disabled = true;
  try { await send(text); }
  finally { busy = false; form.querySelector("button").disabled = false; }
});
// Enter sends; Shift+Enter is a new line.
input.addEventListener("keydown", ev => {
  if (ev.key === "Enter" && !ev.shiftKey && !ev.isComposing) { ev.preventDefault(); form.requestSubmit(); }
});
