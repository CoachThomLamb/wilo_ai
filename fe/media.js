/*
  Exercise videos and photos (#152), for the tracker (index.html).

  - A client attaches a form video (30 s max) or photo to an exercise. The file goes straight from the phone to
    Backblaze B2 with a signed link from the connector (wilo/media.py); the tracker keeps the key on the exercise
    in the workout's log (media: [{key, type, at}]).
  - The coach uploads one demo per exercise name (10 s max), which every client sees on that exercise.
  - Watching: the connector signs a 1-hour link; the file opens in a full-screen viewer.

  Exposes window.__media = { upload(file, {kind, docId, exId, exercise}), urls({keys, demos}), show(url, type) }.
  Needs window.__auth from auth.js.
*/

const LOCAL = /^(localhost|127\.0\.0\.1)$/.test(location.hostname);
const SERVER = LOCAL ? "http://localhost:8000" : "https://wilo-connector.onrender.com";
const SECONDS = { form: 30, demo: 10 };   // same as SECONDS in wilo/media.py

async function call(path, body) {
  const user = window.__auth && window.__auth.currentUser();
  if (!user) throw new Error("sign in first");
  const res = await fetch(SERVER + path, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: "Bearer " + await user.getIdToken() },
    body: JSON.stringify(body),
  });
  const out = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(out.error || "HTTP " + res.status);
  return out;
}

// A video's length in seconds, read in the browser before uploading.
function duration(file) {
  return new Promise((resolve, reject) => {
    const v = document.createElement("video");
    v.preload = "metadata";
    v.onloadedmetadata = () => { URL.revokeObjectURL(v.src); resolve(v.duration); };
    v.onerror = () => { URL.revokeObjectURL(v.src); reject(new Error("couldn't read that video")); };
    v.src = URL.createObjectURL(file);
  });
}

// iPhones sometimes hand over a video with no type; guess from the name.
function typeOf(file) {
  if (file.type) return file.type;
  const ext = (file.name.split(".").pop() || "").toLowerCase();
  return { mov: "video/quicktime", mp4: "video/mp4", webm: "video/webm", jpg: "image/jpeg", jpeg: "image/jpeg",
           png: "image/png", heic: "image/heic", webp: "image/webp" }[ext] || "";
}

async function upload(file, { kind, docId, exId, exercise }) {
  const contentType = typeOf(file);
  if (contentType.startsWith("video/")) {
    const secs = await duration(file);
    if (secs > SECONDS[kind] + 0.5)
      throw new Error(`That video is ${Math.round(secs)} s. Keep it under ${SECONDS[kind]} s.`);
  }
  const { key, url, headers } = await call("/media/upload", { kind, docId, exId, exercise, contentType });
  const put = await fetch(url, { method: "PUT", headers, body: file });
  if (!put.ok) throw new Error("upload failed (" + put.status + ")");
  return call("/media/done", { key, exercise });   // {key, type, size}
}

const urls = body => call("/media/urls", body);

// Full-screen viewer: tap outside or × to close.
function show(url, type) {
  const box = document.createElement("div");
  box.className = "media-view";
  box.innerHTML = `<button class="media-close" aria-label="Close">&times;</button>` +
    (type === "video" ? `<video src="${url}" controls autoplay playsinline loop></video>` : `<img src="${url}" alt="">`);
  box.addEventListener("click", e => { if (e.target === box || e.target.closest(".media-close")) box.remove(); });
  document.body.appendChild(box);
}

window.__media = { upload, urls, show };
