#!/bin/sh
# Restore the stack's database from a dump in Spaces (EXA-180; docs/deploy/BACKUPS.md).
#
#   ./restore.sh                  the newest nightly dump
#   ./restore.sh exam-20261121T190000Z.dump
#
# Run it in deploy/ next to .env. It overwrites every row in the database, so it asks first.
# Steps: stop the app, take a safety dump ("pre-restore-…", kept until you delete it), drop and
# recreate the database from the chosen dump, start the app and wait until /ready answers.
# COMPOSE overrides the compose command (default "docker compose").
set -eu
cd "$(dirname "$0")"
compose=${COMPOSE:-docker compose}

say() { echo "restore.sh: $*"; }
# Compose commands get no stdin: they would swallow the typed (or piped) confirmation.
dc() { $compose "$@" </dev/null; }
run() { dc run --rm --no-deps -T backup exam-backup "$@"; }

say "starting the database"
dc up -d db
i=0
until dc exec -T db pg_isready -q -h 127.0.0.1 -U exam -d exam; do
	i=$((i + 1))
	[ "$i" -lt 30 ] || { say "the database did not come up"; exit 1; }
	sleep 2
done

name=${1:-}
[ -n "$name" ] || name=$(run latest)
say "dump to restore: $name"
say "rows now:"
run counts || true

printf '\nThis REPLACES the whole database with %s.\nType "restore" to go on: ' "$name"
read -r answer || answer=
[ "$answer" = restore ] || { say "not confirmed; nothing changed"; exit 1; }

say "stopping the app"
dc stop app

if ! run now pre-restore; then
	printf 'The safety dump failed (see above). Restore anyway? Type "yes": '
	read -r answer || answer=
	[ "$answer" = yes ] || { say "stopped; the app is down, start it with: $compose up -d app"; exit 1; }
fi

run restore "$name"
say "rows after the restore:"
run counts

say "starting the app"
dc up -d app
i=0
until dc exec -T app python -c \
	"import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/ready')" 2>/dev/null; do
	i=$((i + 1))
	[ "$i" -lt 45 ] || { say "the app has not answered /ready; check: $compose logs app"; exit 1; }
	sleep 2
done
say "done: the app is up and reads the restored database"
