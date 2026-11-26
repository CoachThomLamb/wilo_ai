#!/usr/bin/env bash
# A local copy of WILO's Postgres (#241): pg_dump of $DATABASE_URL into ~/Documents/wilo-backups/ (outside the
# repo: it holds every user's data, which never goes in git). Keeps the newest 30 dumps.
#
#   DATABASE_URL='postgresql://...' scripts/pg_backup.sh
#
# Use Render's *external* connection string (Render dashboard -> the database -> Connections), and a pg_dump
# at least as new as the server (`pg_dump --version`; Arch: pacman -S postgresql-libs).
#
# Nightly, with a systemd user timer (runs when the machine wakes if it was asleep at 3am):
#   ~/.config/wilo-backup.env           DATABASE_URL=postgresql://...   (chmod 600)
#   ~/.config/systemd/user/wilo-backup.service
#       [Service]
#       Type=oneshot
#       EnvironmentFile=%h/.config/wilo-backup.env
#       ExecStart=%h/wilo/scripts/pg_backup.sh
#   ~/.config/systemd/user/wilo-backup.timer
#       [Timer]
#       OnCalendar=*-*-* 03:00
#       Persistent=true
#       [Install]
#       WantedBy=timers.target
#   systemctl --user enable --now wilo-backup.timer
#
# Restore into an empty database:  pg_restore --no-owner -d "$TARGET_URL" ~/Documents/wilo-backups/wilo-<stamp>.dump
set -euo pipefail

: "${DATABASE_URL:?set DATABASE_URL to the Render Postgres external connection string}"
dir="${WILO_BACKUP_DIR:-$HOME/Documents/wilo-backups}"
keep="${WILO_BACKUP_KEEP:-30}"
mkdir -p "$dir"
chmod 700 "$dir"

out="$dir/wilo-$(date +%Y-%m-%dT%H-%M-%S).dump"
pg_dump --format=custom --no-owner --file="$out.part" "$DATABASE_URL"
mv "$out.part" "$out"
chmod 600 "$out"
echo "saved $out ($(du -h "$out" | cut -f1))"

# Keep the newest $keep dumps.
ls -1t "$dir"/wilo-*.dump | tail -n +"$((keep + 1))" | xargs -r rm --
