# wilo_ai

## Dev Mode

Run a local server from the `fe/` directory:

```bash
cd fe
python3 -m http.server 8080
```

Find your machine's local IP:

```bash
ip addr show | grep 'inet ' | grep -v 127
```

Then open on your phone (on the same WiFi):

```
http://<your-ip>:8080/tracker.html
```

**Firewall:** If your phone can't connect, you may need to allow the port:

```bash
sudo ufw allow 8080
```
