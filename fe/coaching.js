/*
  Human coaches (#242): a coach signs up (coaches.html), shares an invite link
  (join.html?coach=<uid>), and plans and watches their clients' workouts (coach.html).

  Data (rules in firestore.rules):
    coaches/{coach}                  the coach's card: { name, createdAt }. Written by the coach.
    coaches/{coach}/clients/{client} { name, email, joinedAt }. Written only by the client, by
                                     opening the invite link and tapping Join. It's what lets the
                                     coach read users/{client}/workouts and coach/*, and plan workouts.
    users/{client}/workouts/{id}     a coach's plan is the same doc wilo/data.py assign writes, plus
                                     plannedBy = the coach (plannedDoc below; the shared cases in
                                     tests/fixtures/coach_plan_cases.json hold both to it).

  Reads are capped (#225): a client's view is at most PLANNED_MAX + LOGGED_MAX workout docs.

  A page imports "./firebase.js" first (the app, the database, sign-in), then this file.
*/
import { getApp } from "https://www.gstatic.com/firebasejs/11.0.0/firebase-app.js";
import {
  getFirestore, doc, getDoc, setDoc, deleteDoc, collection, getDocs, query, where, orderBy, limit,
} from "https://www.gstatic.com/firebasejs/11.0.0/firebase-firestore.js";

export const PLANNED_MAX = 10;
export const LOGGED_MAX = 10;

const db = () => getFirestore(getApp(), "wilo");
const coachRef = uid => doc(db(), "coaches", uid);
const clientRef = (coach, client) => doc(db(), "coaches", coach, "clients", client);
const workoutsOf = client => collection(db(), "users", client, "workouts");

// ---- pure: the planned workout doc (same as wilo/data.py planned_doc) ----

export function iso(d) {
  return d.toISOString();   // 2026-11-26T15:04:05.123Z, like wilo/data.py _iso
}

export function plannedDoc(workout, now, plannedBy) {
  let next = 1;
  const plan = workout.exercises.map(x => ({
    ...x, sets: (x.sets || []).map(s => ({ ...s, done: false })), exId: 'x' + next++,
  }));
  const doc = {
    id: 'prog_' + now.getTime(), name: workout.name,
    assignedFor: workout.assignedFor || iso(now), status: 'planned', createdAt: iso(now),
    plan, diffs: [], exercises: plan, nextExId: next, log: [], logBase: 0,
  };
  if (plannedBy) doc.plannedBy = plannedBy;
  return doc;
}

// Tracker-style id (wilo/data.py doc_id), e.g. 26-nov-15:04-legs-, plus 4 random characters so two plans
// in the same minute don't collide (the tracker's makeDocId does the same).
export function docIdFor(name, now) {
  const pad = n => String(n).padStart(2, '0');
  const month = now.toLocaleString('en-US', { month: 'short' }).toLowerCase();
  const slug = (name || 'workout').slice(0, 5).toLowerCase().replace(/\s+/g, '-');
  const rand = Math.random().toString(36).slice(2, 6);
  return `${pad(now.getDate())}-${month}-${pad(now.getHours())}:${pad(now.getMinutes())}-${slug}-${rand}`;
}

// What the coach types, one exercise per line:  Squat 3x5 @135 - sit deep
//   <name> <sets>x<reps>[s]  [@ <lbs>]  [- <cue>]      "s" after reps: timed (seconds), e.g. Plank 3x30s
// Returns { exercises, errors }: errors name the lines that don't fit.
export function parseLines(text) {
  const exercises = [], errors = [];
  String(text || '').split('\n').forEach((raw, i) => {
    const line = raw.trim();
    if (!line) return;
    const [main, ...cue] = line.split(/\s+[-–—]\s+/);
    const m = main.match(/^(.+?)\s+(\d+)\s*[x×]\s*(\d+)\s*(s|sec|secs)?(?:\s*(?:@|at)\s*(\d+(?:\.\d+)?)\s*(?:lbs?)?)?$/i);
    if (!m) { errors.push(`Line ${i + 1}: "${line}" (try: Squat 3x5 @135)`); return; }
    const [, name, sets, reps, timed, lbs] = m;
    if (+sets < 1 || +sets > 20) { errors.push(`Line ${i + 1}: ${sets} sets?`); return; }
    const x = { name: name.trim(), sets: Array.from({ length: +sets }, () => ({ lbs: lbs ? +lbs : '', reps: +reps, done: false })) };
    if (timed) x.timed = true;
    if (cue.length) x.cue = cue.join(' - ').trim();
    exercises.push(x);
  });
  if (!exercises.length && !errors.length) errors.push('Add at least one exercise.');
  return { exercises, errors };
}

// One line per exercise for the coach: "Squat: 135×5, 135×5" (done sets only), or the plan's "3×5 @135".
export function exerciseLine(x, doneOnly) {
  const sets = (x.sets || []).filter(s => !doneOnly || s.done);
  const unit = x.timed ? 's' : '';
  const one = s => (s.lbs !== '' && s.lbs != null && +s.lbs > 0 ? s.lbs + '×' : '') + s.reps + unit;
  if (doneOnly) return sets.length ? `${x.name}: ${sets.map(one).join(', ')}` : '';
  const first = sets[0];
  return `${x.name}: ${sets.length}×${first ? first.reps + unit : '?'}${first && +first.lbs > 0 ? ' @' + first.lbs : ''}`;
}

// ---- Firestore ----

export async function coachCard(uid) {
  const snap = await getDoc(coachRef(uid));
  return snap.exists() ? snap.data() : null;
}

// Makes the user a coach. Returns true the first time (the sign-up), false if they already were.
export async function becomeCoach(user) {
  if (await coachCard(user.uid)) return false;
  await setDoc(coachRef(user.uid), { name: (user.displayName || user.email || 'Coach').slice(0, 100), createdAt: iso(new Date()) });
  return true;
}

export async function joined(coach, user) {
  return (await getDoc(clientRef(coach, user.uid))).exists();
}

export async function joinCoach(coach, user) {
  await setDoc(clientRef(coach, user.uid), { name: user.displayName || '', email: user.email || '', joinedAt: iso(new Date()) });
}

export const leaveCoach = (coach, user) => deleteDoc(clientRef(coach, user.uid));
export const removeClient = (coach, client) => deleteDoc(clientRef(coach, client));

export async function myClients(coach) {
  const snap = await getDocs(collection(db(), "coaches", coach, "clients"));
  return snap.docs.map(d => ({ uid: d.id, ...d.data() }))
    .sort((a, b) => (a.name || a.email || '').toLowerCase().localeCompare((b.name || b.email || '').toLowerCase()));
}

// A client's planned workouts (soonest first) and their last logged ones (newest first). At most
// PLANNED_MAX + LOGGED_MAX reads, never the whole history (#225).
export async function recentWorkouts(client) {
  const [p, l] = await Promise.all([
    getDocs(query(workoutsOf(client), where('status', '==', 'planned'), limit(PLANNED_MAX))),
    getDocs(query(workoutsOf(client), orderBy('updatedAt', 'desc'), limit(LOGGED_MAX))),
  ]);
  const rows = s => s.docs.map(d => ({ docId: d.id, ...d.data() }));
  const planned = rows(p).sort((a, b) => String(a.assignedFor || '').localeCompare(String(b.assignedFor || '')));
  return { planned, logged: rows(l).filter(w => w.status !== 'planned') };
}

export async function assignToClient(coach, client, workout, now = new Date()) {
  const d = plannedDoc(workout, now, coach);
  const id = docIdFor(workout.name, now);
  await setDoc(doc(workoutsOf(client), id), d);
  return id;
}
