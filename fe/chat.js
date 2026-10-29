/*
  WILO coach chat — a full-screen sheet in the tracker that talks to the
  connector server's POST /chat (wilo/chat.py). The server runs the coach
  over the same tools Claude uses through the connector, so a plan made
  here lands in users/{uid}/workouts like one made in the Claude app, and
  the tracker shows it as soon as it's saved (#126).

  - Auth: the signed-in user's Firebase ID token, sent as a Bearer token.
    The server checks it and decides whose data the coach touches.
  - One chat per local day: the server freezes the coach's context (date,
    profile) when a chat starts, so a new day starts a new chat. "New"
    starts one sooner. The chat id and the transcript we show are kept in
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

function load() {
  try {
    const saved = JSON.parse(localStorage.getItem(KEY) || "null");
    if (saved && saved.day === today()) return saved;
  } catch {}
  return { day: today(), chatId: null, messages: [] };
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
    bubble("hint", "Ask your coach: plan this week, swap an exercise, how did bench go?\nHold a message to copy it.");
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
      body: JSON.stringify({ message: text, chatId: chat.chatId }),
    });
    const body = await res.json().catch(() => ({}));
    if (res.status === 404) chat.chatId = null;   // chat gone: the next message starts a new one
    if (!res.ok) throw new Error(body.error || "HTTP " + res.status);
    chat.chatId = body.chatId;
    const reply = body.reply || "(no reply)";
    chat.messages.push({ role: "coach", text: reply });
    wait.className = "msg coach";
    wait.textContent = reply;
  } catch (err) {
    wait.className = "msg err";
    wait.textContent = "Couldn't reach the coach: " + (err.message || err);
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
  if (chat.day !== today()) chat = load();
  draw();
  sheet.classList.add("open");
  wake();
});
$("chatClose").addEventListener("click", () => sheet.classList.remove("open"));
$("chatNew").addEventListener("click", () => {
  chat = { day: today(), chatId: null, messages: [] };
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
