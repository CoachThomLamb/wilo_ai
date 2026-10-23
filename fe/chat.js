/*
  WILO coach chat — a full-screen sheet in the tracker that talks to the
  connector server's POST /chat (wilo/chat.py). The server runs the coach
  over the same tools Claude uses through the connector, so a plan made
  here lands in users/{uid}/assigned like one made in the Claude app.

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
  if (!chat.messages.length) bubble("hint", "Ask your coach: plan this week, swap an exercise, how did bench go?");
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
    let reply = body.reply || "(no reply)";
    if ((body.tools || []).some(t => t === "assign_workout" || t === "update_workout"))
      reply += "\n\nIf the coach saved a workout, tap Load to get it.";
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
