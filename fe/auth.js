/*
  WILO auth — Google sign-in via Firebase Auth, per-user Firestore paths.

  - Reuses the app the page already initialized (index.html / builder.html
    call initializeApp in their head <script type="module">). Same CDN
    version, so it's the same module instance.
  - Sign-in: Google popup, falling back to redirect if the popup is blocked.
    The Firebase SDK persists the session itself (IndexedDB); nothing here
    touches localStorage.
  - Provision: on every sign-in, merge-writes users/{uid} with profile
    fields. createdAt is only set the first time.
  - Data: userCol('completed') -> users/{uid}/completed, etc. Pages swap
    collection(db, 'completed') for userCol('completed'); the security rule
    on users/{uid}/** does the per-user filtering server-side.

  Usage:
    import { onUser, signIn, signOut, userCol, userDoc } from './auth.js';
    onUser(user => user ? boot() : showSignInButton());
*/

import { getApp } from "https://www.gstatic.com/firebasejs/11.0.0/firebase-app.js";
import {
  getAuth, GoogleAuthProvider, onAuthStateChanged,
  signInWithPopup, signInWithRedirect, getRedirectResult,
  signOut as fbSignOut,
} from "https://www.gstatic.com/firebasejs/11.0.0/firebase-auth.js";
import {
  getFirestore, doc, getDoc, setDoc, collection, serverTimestamp,
} from "https://www.gstatic.com/firebasejs/11.0.0/firebase-firestore.js";

const app = getApp();
const auth = getAuth(app);
const db = getFirestore(app, "wilo");
const provider = new GoogleAuthProvider();
provider.setCustomParameters({ prompt: "select_account" });

// Creates or refreshes users/{uid}. Safe to call on every sign-in.
async function provision(user) {
  const ref = doc(db, "users", user.uid);
  const profile = {
    email: user.email,
    name: user.displayName,
    photo: user.photoURL,
    lastSignIn: serverTimestamp(),
  };
  const snap = await getDoc(ref);
  if (!snap.exists()) profile.createdAt = serverTimestamp();
  await setDoc(ref, profile, { merge: true });
}

export async function signIn() {
  try {
    const { user } = await signInWithPopup(auth, provider);
    await provision(user);
    return user;
  } catch (e) {
    if (e.code === "auth/popup-blocked" || e.code === "auth/operation-not-supported-in-this-environment") {
      await signInWithRedirect(auth, provider);  // page navigates away; finished below on return
      return null;
    }
    throw e;
  }
}

// Completes a redirect sign-in when the page loads back.
getRedirectResult(auth)
  .then(res => res && provision(res.user))
  .catch(e => console.error("redirect sign-in failed", e));

export const signOut = () => fbSignOut(auth);

// cb(user | null). Fires once on load with the persisted session, then on changes.
export const onUser = cb => onAuthStateChanged(auth, cb);

export const currentUser = () => auth.currentUser;

function uid() {
  const u = auth.currentUser;
  if (!u) throw new Error("not signed in");
  return u.uid;
}

// users/{uid}/{name}
export const userCol = name => collection(db, "users", uid(), name);

// users/{uid}/{name}/{id}
export const userDoc = (name, id) => doc(db, "users", uid(), name, id);

window.__auth = { signIn, signOut, onUser, currentUser, userCol, userDoc };
