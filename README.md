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

## Claude Skills

This project uses Claude Code skills tracked in `skills-lock.json`. The skill files
themselves are gitignored (`.agents/`), so after a fresh clone you need to reinstall them:

```bash
claude /install-skills
```

This reads `skills-lock.json` and pulls down the correct versions of each skill.
