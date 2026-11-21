#!/bin/sh
# Restore the stack's database from a dump in Spaces (EXA-180; docs/deploy/BACKUPS.md).
#
#   ./restore.sh                  the newest nightly dump
#   ./restore.sh exam-20261121T190000Z.dump
#
# Run it in deploy/ next to .env. It replaces every row in the database, so it asks first.
# Steps: stop the app and the backup job, take a safety dump ("pre-restore-…") unless the
# database is empty, load the chosen dump into a scratch database and swap it in only once it
# has loaded, then start the app and the backup job again and wait until /ready answers.
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
	[ "$i" -lt 30 ] || {
		say "the database did not come up"
		exit 1
	}
	sleep 2
done

name=${1:-}
[ -n "$name" ] || name=$(run latest)
say "dump to restore: $name"
before=$(run counts)
say "rows now:"
echo "${before:-  (no tables)}"

printf '\nThis REPLACES the whole database with %s.\nType "restore" to go on: ' "$name"
read -r answer || answer=
[ "$answer" = restore ] || {
	say "not confirmed; nothing changed"
	exit 1
}

# The backup job stays stopped for the whole restore, so a nightly run cannot dump a database
# half way through. Both come back however this script ends; the live database is only replaced
# once the dump has loaded, so a failed restore leaves the old data in place.
say "stopping the app and the backup job"
dc stop app backup
trap 'say "starting the app and the backup job"; dc up -d app backup' EXIT

if [ -z "$before" ]; then
	say "the database has no tables: no safety dump needed"
elif ! run now pre-restore; then
	printf 'The safety dump failed (see above). Restore anyway? Type "yes": '
	read -r answer || answer=
	[ "$answer" = yes ] || {
		say "stopped; nothing changed"
		exit 1
	}
fi

run restore "$name"
say "rows after the restore:"
run counts

trap - EXIT
say "starting the app and the backup job"
dc up -d app backup
i=0
until dc exec -T app python -c \
	"import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/ready')" 2>/dev/null; do
	i=$((i + 1))
	[ "$i" -lt 45 ] || {
		say "the app has not answered /ready; check: $compose logs app"
		exit 1
	}
	sleep 2
done
say "done: the app is up and reads the restored database"
