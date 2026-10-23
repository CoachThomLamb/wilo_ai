# ngrok status

**Not needed yet.** Parked until we need to serve the app outside the home network (e.g. gym on cellular).

## What works
- ngrok installed via yay
- Local server: `python3 -m http.server 8080` from `~/wilo/fe/`
- Tunnel starts: `ngrok http 8080`
- UFW needs port 8080 open: `sudo ufw allow 8080`

## What doesn't work yet
- TLS error hitting the ngrok HTTPS URL from phone — not debugged, suspected VPN interference (HackTheBox tun0 was active)

## Current solution
- App is deployed on Firebase — use that URL for now
- On home WiFi: `http://10.0.0.46:8080/tracker.html`

## Resume here
When we need ngrok: disconnect HackTheBox VPN first (`sudo killall openvpn`), restart ngrok, and retest the HTTPS URL from phone.
