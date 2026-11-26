/*
  WILO coach chat — a full-screen sheet in the tracker that talks to the
  connector server's POST /chat (wilo/chat.py). The server runs the coach
  over the same tools Claude uses through the connector, so a plan made
  here lands in users/{uid}/workouts like one made in the Claude app, and
  the tracker's listener shows it as soon as it's saved (#126).

  - Auth: the signed-in user's Firebase ID token, sent as a Bearer token.
    The server checks it and decides whose data the coach touches.
  - One chat per local day: the server freezes the coach's context (date,
    profile) when a chat starts, so a new day starts a new chat. An hour
    with no message starts one too (#143: the server's cache has expired by
    then, and the server starts a fresh chat itself). "New" starts one
    sooner. The chat id and the transcript we show are kept in
    localStorage (this phone only; the server keeps the real history).
  - Wake-up: Render's free tier sleeps after 15 min, so opening the sheet
    pings /chat first and the first reply isn't stuck behind a cold start.

  - Chat-first (tracker, #222): the page sends "wilo-empty-day" when today
    has no workout. The sheet opens full with Wilo speaking first (a local
    greeting with two chips; the server never sees it). "wilo-workout-in"
    (a workout for today just landed) drops it to half, so you see the
    workout under it; touching the workout ("wilo-workout-touched") folds it
    to the bar. Tapping the title flips full / half.

  - Tap-to-answer (#246): a reply with choices (the coach called
    offer_choices) shows them as buttons under Wilo's message; a tap sends
    the option as your message.

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
const IDLE_MS = 60 * 60 * 1000;   // same as IDLE in wilo/chat.py
const current = c => !!c && c.day === today() && (!c.lastAt || Date.now() - c.lastAt < IDLE_MS);

function load() {
  try {
    const saved = JSON.parse(localStorage.getItem(KEY) || "null");
    if (current(saved)) return saved;
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

// Accounts not yet on the invite list (the server decides): Wilo's waitlist words, else null.
let waitlist = null;

// Chat-first greeting on an empty day: Wilo speaks first, with chips that send the line for you.
let greet = false;
const GREETING = "Nothing on for today. What are you training? Or tell me what you already did and I'll log it.";
const CHIPS = ["Plan today's workout", "Log a workout I did"];

function chips() {
  const row = document.createElement("div");
  row.className = "rate chips";
  const inner = document.createElement("div");
  inner.className = "row";
  for (const c of CHIPS) {
    const b = document.createElement("button");
    b.type = "button";
    b.textContent = c;
    b.addEventListener("click", () => { input.value = c; form.requestSubmit(); });
    inner.append(b);
  }
  row.append(inner);
  log.append(row);
}

function draw() {
  log.replaceChildren();
  if (waitlist) bubble("coach", waitlist);
  else if (!chat.messages.length && greet) { bubble("coach", GREETING); chips(); }
  else if (!chat.messages.length)
    bubble("hint", "Ask your coach: plan this week, swap an exercise, how did bench go?\nHold a message to copy it.");
  chat.messages.forEach((m, i) => { bubble(m.role, m.text); choiceRow(chat.messages, i); });
  askRating();
}

// ---- tap-to-answer (#246) ---------------------------------------------
// When the coach calls offer_choices, the server's reply carries choices: they're kept on Wilo's message and shown
// as buttons under it. A tap sends that option as your message; typing still works. Once answered (or passed by),
// the buttons stay greyed out, the pick highlighted, so a reload shows what was chosen.
function choiceState(messages, i) {
  const m = messages[i];
  if (!m || m.role !== "coach" || !Array.isArray(m.choices) || !m.choices.length) return "none";
  if (m.picked != null) return "answered";
  return i === messages.length - 1 ? "open" : "passed";
}

function choiceRow(messages, i) {
  const state = choiceState(messages, i);
  if (state === "none") return null;
  const m = messages[i];
  const row = document.createElement("div");
  row.className = "choices " + state;
  for (const c of m.choices) {
    const b = document.createElement("button");
    b.type = "button";
    b.textContent = c;   // text only, like the bubbles
    b.disabled = state !== "open";
    if (c === m.picked) b.classList.add("picked");
    b.addEventListener("click", () => pick(m, c));
    row.append(b);
  }
  log.append(row);
  log.scrollTop = log.scrollHeight;
  return row;
}

function pick(m, c) {
  if (busy || m.picked != null) return;
  m.picked = c;
  save();
  closeChoices(c);
  input.value = c;
  form.requestSubmit();
}

// Grey out the open buttons: answered (picked is the label tapped) or passed by (the user typed instead).
function closeChoices(picked) {
  log.querySelectorAll(".choices.open").forEach(row => {
    row.className = "choices " + (picked == null ? "passed" : "answered");
    row.querySelectorAll("button").forEach(b => {
      b.disabled = true;
      if (picked != null && b.textContent === picked) b.classList.add("picked");
    });
  });
}

// ---- "How's Wilo doing?" ---------------------------------------------
// After Wilo's second reply in a chat, ask once: Bad / Good / Great. Bad asks what Wilo should do better, Great
// asks what made it great (both optional); Good just says thanks. Saved per chat on the server (chat_feedback/{chatId}); chat.rated stops it asking again.
const ASK_AFTER = 2;   // Wilo replies in a chat before asking
const style = document.createElement("style");
style.textContent = `
  .rate { align-self: stretch; display: flex; flex-direction: column; align-items: center; gap: 8px;
          padding: 10px 0 4px; color: var(--dim); font-size: 14px; text-align: center; }
  .rate .row { display: flex; gap: 8px; }
  .rate button { background: var(--field); color: var(--text); border: 0; border-radius: 999px;
                 padding: 8px 16px; font: inherit; font-size: 15px; }
  .rate form { display: flex; gap: 8px; width: 100%; }
  .choices { align-self: flex-start; display: flex; flex-wrap: wrap; gap: 8px; max-width: 100%;
             margin: -2px 0 6px; }
  .choices button { min-height: 44px; padding: 10px 18px; border-radius: 999px; font: inherit; font-size: 16px;
                    background: var(--field); color: var(--text); border: 1px solid var(--dim);
                    max-width: 100%; overflow-wrap: anywhere; text-align: left; touch-action: manipulation; }
  .choices button:disabled { opacity: .45; }
  .choices button.picked { opacity: 1; border-color: var(--text); font-weight: 600; }
  .rate input { flex: 1; min-width: 0; background: var(--field); color: var(--text); border: 0;
                border-radius: 999px; padding: 8px 14px; font: inherit; font-size: 16px; }`;
document.head.appendChild(style);

async function postRating(rating, note) {
  const user = window.__auth && window.__auth.currentUser();
  if (!user || !chat.chatId) return;
  try {
    await fetch(SERVER + "/chat/feedback", {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: "Bearer " + await user.getIdToken() },
      body: JSON.stringify({ chatId: chat.chatId, rating, note }),
    });
  } catch {}   // feedback is best effort; never get in the way of the chat
}

function askRating() {
  log.querySelectorAll(".rate").forEach(el => el.remove());
  const replies = chat.messages.filter(m => m.role === "coach").length;
  if (waitlist || !chat.chatId || chat.rated || replies < ASK_AFTER) return;
  const box = document.createElement("div");
  box.className = "rate";
  const row = document.createElement("div");
  row.className = "row";
  for (const [rating, label] of [["bad", "Bad"], ["good", "Good"], ["great", "Great"]]) {
    const b = document.createElement("button");
    b.type = "button";
    b.textContent = label;
    b.addEventListener("click", () => rated(rating, box));
    row.append(b);
  }
  box.append("How's Wilo doing?", row);
  log.append(box);
  log.scrollTop = log.scrollHeight;
}

function rated(rating, box) {
  chat.rated = rating;
  save();
  postRating(rating);
  if (rating === "good") { box.replaceChildren("Thanks!"); return; }
  const f = document.createElement("form");
  const note = document.createElement("input");
  note.placeholder = "Optional";
  note.enterKeyHint = "send";
  const send = document.createElement("button");
  send.textContent = "Send";
  f.append(note, send);
  f.addEventListener("submit", ev => {
    ev.preventDefault();
    if (note.value.trim()) postRating(rating, note.value.trim());
    box.replaceChildren("Thanks, that helps.");
  });
  box.replaceChildren(rating === "great" ? "Nice! What made it great?" : "Thanks. What should Wilo do better?", f);
  note.focus();
}

function wake() {
  fetch(SERVER + "/chat", { method: "OPTIONS" }).catch(() => {});
}

// The tracker's workout on screen (index.html window.__screen); null on pages without one (day.html).
function screen() {
  try { return window.__screen ? window.__screen() : null; } catch { return null; }
}

async function send(text) {
  const user = window.__auth && window.__auth.currentUser();
  if (!user) { bubble("err", "Sign in first."); return; }
  if (greet && !chat.messages.length) chat.messages.push({ role: "coach", text: GREETING });   // keep what Wilo opened with
  chat.messages.push({ role: "me", text });
  chat.lastAt = Date.now();
  log.querySelectorAll(".hint, .chips").forEach(el => el.remove());
  closeChoices(null);   // typed instead of tapping (after a tap they're already closed)
  bubble("me", text);
  save();
  const wait = bubble("coach pending", "Thinking…");
  const slow = setTimeout(() => { wait.textContent = "Still thinking (the server may be waking up)…"; }, 12000);
  try {
    const res = await fetch(SERVER + "/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: "Bearer " + await user.getIdToken() },
      body: JSON.stringify({ message: text, chatId: chat.chatId, screen: screen() }),
    });
    const body = await res.json().catch(() => ({}));
    if (res.status === 404) chat.chatId = null;   // chat gone: the next message starts a new one
    // 402: the user's spend cap; 403: not on the invite list. Show the server's words as they are, not as a
    // connection error.
    if ((res.status === 402 || res.status === 403) && body.error) throw Object.assign(new Error(body.error), { plain: true });
    if (!res.ok) throw new Error(body.error || "HTTP " + res.status);
    chat.chatId = body.chatId;
    const reply = body.reply || "(no reply)";
    const said = { role: "coach", text: reply };
    if (Array.isArray(body.choices) && body.choices.length) said.choices = body.choices.map(String);
    chat.messages.push(said);
    wait.className = "msg coach";
    wait.textContent = reply;
    choiceRow(chat.messages, chat.messages.length - 1);
    askRating();
    // The page can refresh what the coach wrote (day.html reloads the day after update_day).
    window.dispatchEvent(new CustomEvent("wilo-chat-reply", { detail: { tools: body.tools || [] } }));
  } catch (err) {
    wait.className = "msg err";
    wait.textContent = err.plain ? err.message : "Couldn't reach the coach: " + (err.message || err);
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

// ---- invite list ----------------------------------------------------
// Right after sign-in, ask the server whether the chat is open for this account. If not, open the sheet once
// (per account, per phone) with Wilo's waitlist message, so a new person hears it before typing anything.
let checkedFor = null;
async function checkAccess(user) {
  if (!user || checkedFor === user.uid) return;
  checkedFor = user.uid;
  try {
    const res = await fetch(SERVER + "/chat/access", { headers: { Authorization: "Bearer " + await user.getIdToken() } });
    const body = await res.json();
    if (!res.ok) return;
    waitlist = body.open ? null : body.message;
  } catch { return; }   // server asleep or offline: the 403 on the first message says the same
  if (!waitlist) return;
  const seen = "wilo-waitlist-seen-" + user.uid;
  let shown = false;
  try { shown = !!localStorage.getItem(seen); localStorage.setItem(seen, "1"); } catch {}
  draw();
  if (!shown) sheet.classList.add("open");
}
window.addEventListener("wilo-user", ev => ev.detail ? checkAccess(ev.detail) : (waitlist = null, checkedFor = null));
if (window.__auth && window.__auth.currentUser()) checkAccess(window.__auth.currentUser());

// Open the sheet full or half; close folds it back to the page's button (the tracker's bar).
function open(half) {
  if (!current(chat)) chat = load();
  draw();
  sheet.classList.toggle("half", !!half);
  sheet.classList.add("open");
  wake();
}
const close = () => sheet.classList.remove("open", "half");
// With a workout on screen the chat opens half, so you still see it; otherwise (empty day, the Day page) full.
$("chatBtn").addEventListener("click", () => { const w = screen(); open(!!(w && w.exercises)); });
$("chatClose").addEventListener("click", close);
sheet.querySelector(".sheet-head strong").addEventListener("click", () => {
  if (sheet.classList.contains("open")) sheet.classList.toggle("half");
});
window.addEventListener("wilo-empty-day", () => {
  if (waitlist || sheet.classList.contains("open")) return;
  greet = true;
  open(false);
});
window.addEventListener("wilo-workout-in", () => {
  if (sheet.classList.contains("open")) { sheet.classList.add("half"); log.scrollTop = log.scrollHeight; }
});
window.addEventListener("wilo-workout-touched", () => {
  if (sheet.classList.contains("half")) close();
});
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
  if (!current(chat)) { chat = load(); draw(); }   // idle: the server starts a fresh chat too
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
