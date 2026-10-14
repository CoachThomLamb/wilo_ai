/*
  Voice coach, option 1 (#78 spike): OpenAI Realtime over WebRTC.

  Tap the mic: the phone's mic streams to the model and its voice plays back,
  live, with interruptions. Our server (/voice/call on the connector) swaps the
  SDP offer for an answer using our key, and sets the coach prompt and the
  tracker tools; the browser never holds a key. Tool calls arrive on the data
  channel and run in the tracker (window.wiloTracker.apply); the result goes
  back to the model. Tap again to hang up.
*/

const API = /^(localhost|127\.0\.0\.1)$/.test(location.hostname)
  ? 'http://localhost:8000' : 'https://wilo-connector.onrender.com';

const btn = document.getElementById('micBtn');
const tracker = () => window.wiloTracker;
let pc = null, dc = null, mic = null, audio = null, answeredCall = false;

function setMode(mode) { btn.className = 'mic' + (mode ? ' ' + mode : ''); }
const send = ev => dc && dc.readyState === 'open' && dc.send(JSON.stringify(ev));

async function start() {
  const user = window.__auth && window.__auth.currentUser();
  if (!user) return tracker().note('Sign in to talk to your coach', 'err');
  setMode('connecting');
  try {
    // Made inside the tap, so iOS lets it play.
    audio = new Audio();
    audio.autoplay = true;
    audio.setAttribute('playsinline', '');
    mic = await navigator.mediaDevices.getUserMedia({ audio: true });
    pc = new RTCPeerConnection();
    pc.ontrack = e => { audio.srcObject = e.streams[0]; };
    pc.addTrack(mic.getTracks()[0], mic);
    pc.onconnectionstatechange = () => {
      if (pc && ['failed', 'closed', 'disconnected'].includes(pc.connectionState)) stop('Voice disconnected');
    };
    dc = pc.createDataChannel('oai-events');
    dc.onopen = () => {
      send({ type: 'conversation.item.create', item: { type: 'message', role: 'system',
        content: [{ type: 'input_text', text: 'Workout on screen now: ' + JSON.stringify(tracker().summary()) }] } });
      setMode('live');
      tracker().note('Coach is listening', 'ok');
    };
    dc.onmessage = e => onEvent(JSON.parse(e.data));

    const offer = await pc.createOffer();
    await pc.setLocalDescription(offer);
    const r = await fetch(API + '/voice/call', {
      method: 'POST', body: offer.sdp,
      headers: { Authorization: 'Bearer ' + await user.getIdToken(), 'Content-Type': 'application/sdp' },
    });
    if (!r.ok) throw new Error((await r.json().catch(() => ({}))).error || 'HTTP ' + r.status);
    await pc.setRemoteDescription({ type: 'answer', sdp: await r.text() });
  } catch (err) {
    stop('Voice failed: ' + (err.message || err));
  }
}

// Tool calls run in the tracker. One response can hold several calls, so the
// next response is requested once, when this one is done.
function onEvent(ev) {
  if (ev.type === 'response.function_call_arguments.done') {
    let args = {};
    try { args = JSON.parse(ev.arguments || '{}'); } catch {}
    const result = tracker().apply(ev.name, args);
    send({ type: 'conversation.item.create',
      item: { type: 'function_call_output', call_id: ev.call_id, output: JSON.stringify(result) } });
    answeredCall = true;
  } else if (ev.type === 'response.done' && answeredCall) {
    answeredCall = false;
    send({ type: 'response.create' });
  } else if (ev.type === 'error') {
    tracker().note('Coach: ' + (ev.error && ev.error.message || 'error'), 'err');
  }
}

function stop(msg) {
  if (dc) dc.close();
  if (pc) pc.close();
  if (mic) mic.getTracks().forEach(t => t.stop());
  if (audio) audio.srcObject = null;
  pc = dc = mic = audio = null;
  answeredCall = false;
  setMode('');
  if (msg) tracker().note(msg, msg.startsWith('Voice failed') ? 'err' : undefined);
}

btn.addEventListener('click', () => pc ? stop('Coach hung up') : start());
