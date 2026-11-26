/*
  Firebase setup shared by the signed-in pages (index, day, week): one copy of
  the config (#189). A page imports it first, then the Firestore functions it
  uses:

    import "./firebase.js";
    import { setDoc } from "https://www.gstatic.com/firebasejs/11.0.0/firebase-firestore.js";

  It starts the app, opens the `wilo` database and loads auth.js, which
  reports sign-in as a "wilo-user" event on window (detail: the user or null),
  or "wilo-auth-error" if auth.js can't load.

  authDomain = this page's own host on Firebase Hosting (wilo2-1ee44.web.app,
  the hiwilo.com custom domain and PR previews all serve /__/auth/handler).
  Otherwise redirect sign-in breaks in Safari's in-app browsers (Camera,
  Claude app, Instagram): the handler on another domain loses its state
  ("missing initial state"). Each host must be an Authorized redirect URI
  (https://<host>/__/auth/handler) on the OAuth web client in Google Cloud.
  Elsewhere (localhost) use the default.

  Data access: per-user paths, through auth.js's userCol / userDoc
  (users/{uid}/...). The one other top-level collection is coaches/ (human
  coaches, #242, through coaching.js).
*/
import { initializeApp } from "https://www.gstatic.com/firebasejs/11.0.0/firebase-app.js";
import { getFirestore } from "https://www.gstatic.com/firebasejs/11.0.0/firebase-firestore.js";

const onHosting = /\.web\.app$|\.firebaseapp\.com$|^hiwilo\.com$/.test(location.hostname);
const app = initializeApp({
  apiKey: "AIzaSyDQ-MDgxaD6vab2awYKuez3vLB-Tmj6oLM",
  authDomain: onHosting ? location.host : "wilo2-1ee44.firebaseapp.com",
  projectId: "wilo2-1ee44",
  storageBucket: "wilo2-1ee44.firebasestorage.app",
  messagingSenderId: "103580826325",
  appId: "1:103580826325:web:0e5cc800c5cbb29691c05c"
});
getFirestore(app, "wilo");

// auth.js calls getApp() at load, so it's imported after initializeApp.
import("./auth.js")
  .then(a => a.onUser(user =>
    window.dispatchEvent(new CustomEvent("wilo-user", { detail: user }))))
  .catch(err => window.dispatchEvent(new CustomEvent("wilo-auth-error", { detail: err })));
