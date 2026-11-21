# Database backups

The production database is Postgres 17 in the `db` service of `deploy/compose.yaml`, on the
droplet's `pgdata` volume. If the droplet is lost, the volume goes with it, so the stack's
`backup` service copies the database to a DigitalOcean Spaces bucket every night. This page
covers how that works, how to run a backup by hand, and how to restore one, including the drill
to rehearse before launch and every few months after.

Point-in-time recovery is out of scope: a restore brings back the database as it was at the
last dump, so up to a day of changes can be lost.

**Backups last 14 days.** The privacy notice tells users that each backup is deleted after 14
days, so an account they delete is gone from the backups within 14 days. Everything below keeps
that promise; don't lengthen it without changing the notice first.

## How it works

- **Where it runs.** The `backup` service (`deploy/backup/`) is a small Alpine image with
  Postgres 17's client tools (`pg_dump`, `pg_restore`, `psql`) and [rclone](https://rclone.org/)
  1.71 copied from the official `rclone/rclone` image. Compose builds it on the droplet; nothing
  is pulled from a private registry. Its memory limit is 128 MB.
- **When.** Every day at `BACKUP_TIME` (default `03:00`), Singapore time. The service's shell
  loop sleeps until then; there is no cron. If the droplet is off at that moment, that night is
  skipped. On start it logs when the next one is due.
- **What.** `pg_dump -Fc` (Postgres's compressed custom format) of the `exam` database, named
  `exam-<UTC timestamp>.dump`, e.g. `exam-20261121T190000Z.dump` (19:00 UTC is 03:00 in
  Singapore). It goes to `<SPACES_BUCKET>/<BACKUP_PATH>/` (default folder `db`).
- **Checks before upload.** The job refuses to back up a database with no tables (say, one
  left empty by a failed restore), so an empty dump never becomes the newest. The dump is
  written to the container's `/tmp` first and uploaded only if `pg_dump` succeeded, the file is
  not empty and `pg_restore -f /dev/null` reads every byte of it back (a cut-off or corrupt
  archive fails that). The upload is a single S3 object write, so a half-sent dump never
  appears in the bucket.
- **Retention: 14 days, by age.** After each nightly run, *whether or not the dump worked*,
  the job deletes every object in the backup folder that was uploaded more than 14 days ago:
  nightly dumps, `pre-restore-…` safety dumps and anything else put there. Run it by hand with
  `exam-backup prune`. As a backstop, the bucket has a lifecycle rule that expires objects
  after 14 days (set up below), and **bucket versioning stays off**: with versioning on, a
  deleted dump would live on as an old version.
- **The catch: after a long outage the last good copy expires too.** If backups fail for more
  than 14 days in a row, every dump is gone. That is the price of the promise, which is why a
  failed night must be noticed within days: check the log (below) and keep the uptime alert
  (EXA-183) working.
- **Failures.** Any failed step exits non-zero with an `ERROR:` line and
  `backup FAILED (exit 1)`, in `docker compose logs backup`. The nightly loop logs it and tries
  again the next night. If the `SPACES_*` values are empty, the service logs which one and
  keeps restarting; the rest of the stack runs regardless.
- **Secrets.** The bucket keys and the database password reach the container as environment
  variables from `deploy/.env` (rclone reads `RCLONE_CONFIG_SPACES_*`, the Postgres tools read
  `PGPASSWORD`). They are not baked into the image, passed on a command line or logged. Anyone
  who can run `docker inspect` on the droplet can read them, as with the app's own settings.

## Set up (once)

1. In the DigitalOcean control panel, create a Spaces bucket in **SGP1**, private (file listing
   restricted), CDN off, versioning off (the default). A name like `exam-backups-<something>`;
   bucket names are global.
2. Create a Spaces access key **limited to that bucket**, with read, write and delete
   permission (the job deletes old dumps). Copy the secret now: it is shown once.
3. Fill in `deploy/.env` (see `deploy/.env.example`):

   ```sh
   SPACES_BUCKET=exam-backups-something
   SPACES_ENDPOINT=https://sgp1.digitaloceanspaces.com
   SPACES_ACCESS_KEY_ID=DO00...
   SPACES_SECRET_ACCESS_KEY=...
   # optional: BACKUP_PATH=db  BACKUP_TIME=03:00
   ```

4. Start or update the stack, which builds the backup image: `docker compose up -d --build`.
   After a change to `deploy/backup/`, run that again so the service is rebuilt.
5. Add the 14-day lifecycle rule and check versioning is off. The control panel has no screen
   for lifecycle rules, so use the AWS CLI's official image against the Spaces endpoint. In
   `deploy/`, with the keys passed by name only (never typed on the command line):

   ```sh
   set -a; . ./.env; set +a
   export AWS_ACCESS_KEY_ID="$SPACES_ACCESS_KEY_ID" AWS_SECRET_ACCESS_KEY="$SPACES_SECRET_ACCESS_KEY"
   aws() { docker run --rm -i -e AWS_ACCESS_KEY_ID -e AWS_SECRET_ACCESS_KEY \
     -e AWS_DEFAULT_REGION=sgp1 amazon/aws-cli:2.31.39 --endpoint-url "$SPACES_ENDPOINT" "$@"; }

   aws s3api put-bucket-lifecycle-configuration --bucket "$SPACES_BUCKET" \
     --lifecycle-configuration '{"Rules":[{"ID":"expire-backups-14d","Status":"Enabled",
       "Filter":{"Prefix":""},"Expiration":{"Days":14},
       "AbortIncompleteMultipartUpload":{"DaysAfterInitiation":1}}]}'
   aws s3api get-bucket-lifecycle-configuration --bucket "$SPACES_BUCKET"  # shows the rule
   aws s3api get-bucket-versioning --bucket "$SPACES_BUCKET"  # prints nothing: never enabled
   ```

   The rule covers the whole bucket, so keep nothing else in it. If versioning ever shows
   `"Status": "Enabled"`, suspend it and delete the old versions.
6. Run one backup now (next section) and check it is listed.

## Day to day

All commands run in `deploy/` on the droplet.

```sh
# back up now (prints the object name and size; exit status 0 on success)
docker compose exec backup exam-backup now

# list the dumps in the bucket, oldest first: size, date, time (UTC), name
docker compose exec backup exam-backup list

# the newest nightly dump's name
docker compose exec backup exam-backup latest

# rows per table in the live database
docker compose exec backup exam-backup counts

# delete everything older than 14 days now (the nightly run does this anyway)
docker compose exec backup exam-backup prune

# did last night's backup work?
docker compose logs --since 24h backup | grep -E 'uploaded|deleted|FAILED|ERROR'
```

A good night logs lines like these (the `deleted` ones from the 15th night on):

```
2026-11-21T19:00:00Z backup: dumping database exam to exam-20261121T190000Z.dump
2026-11-21T19:00:01Z backup: uploaded spaces:exam-backups-something/db/exam-20261121T190000Z.dump (13817 bytes)
2026-11-21T19:00:02Z prune: deleted exam-20261107T190000Z.dump (older than 14d)
2026-11-21T19:00:02Z prune: done; nothing in spaces:exam-backups-something/db is older than 14d
```

To keep a copy off DigitalOcean, download a dump from the bucket in the control panel. A dump
is restored with `pg_restore` from Postgres 17 or newer.

## Restore

`deploy/restore.sh` replaces the whole database with one dump:

```sh
cd deploy
./restore.sh                               # the newest nightly dump
./restore.sh exam-20261121T190000Z.dump    # a named one (from `exam-backup list`)
```

It:

1. starts the database if it is not running and waits for it;
2. prints the dump it will restore and the row counts now;
3. asks you to type `restore` (anything else stops it, with nothing changed);
4. stops the app and the backup job (so no nightly run happens mid-restore);
5. uploads a safety dump of the current database as `pre-restore-<timestamp>.dump`, unless the
   database has no tables (if the dump fails it asks whether to go on);
6. downloads the chosen dump and loads it into a scratch database, `exam_restore`, with
   `pg_restore --single-transaction --exit-on-error`;
7. only once that has loaded, renames the live `exam` aside, renames `exam_restore` to `exam`
   and drops the old one;
8. prints the row counts after the restore;
9. starts the app and the backup job and waits until `/ready` answers.

If the restore fails at step 6, the live database is untouched; the app and the backup job are
started again whatever happens. To undo a restore, restore the `pre-restore-…` dump it made
(within 14 days: it expires like any other).

## The restore drill

Rehearse the worst case, a lost droplet, before launch and then every three months. Do it on a
**throwaway droplet** (any size with 2 GB, created for the drill and destroyed after), so the
live site is never touched. Write the date and the result at the end of this page.

On the live droplet, note what the restore should bring back:

```sh
cd deploy
docker compose exec backup exam-backup now        # a fresh dump to restore
docker compose exec backup exam-backup counts     # write these numbers down
docker compose exec db psql -U exam -d exam -c \
  "SELECT owner_id, count(*) FROM documents GROUP BY 1 ORDER BY 2 DESC LIMIT 1"
```

On the throwaway droplet (Docker Engine and the compose plugin installed):

1. Get the deploy files: a checkout of the repository, or copy the live `deploy/` folder over
   with `scp -r`. Then `cd deploy`.
2. Copy the live `deploy/.env` there too (`chmod 600 .env`). Change `SITE_ADDRESS`,
   `EXAM_PUBLIC_URL` and `EXAM_WEB_URL` to the throwaway droplet's `<ip>.sslip.io`. Keep the
   same `POSTGRES_PASSWORD` and Spaces values.
3. Start only the database and the backup job, which builds its image:
   `docker compose up -d --build db backup`
4. Check the bucket is reachable: `docker compose exec backup exam-backup list` shows the dump
   you just made.
5. Restore: `./restore.sh`, type `restore`. It ends with
   `restore.sh: done: the app is up and reads the restored database`.
6. Check:
   - the "rows after the restore" match the counts you wrote down;
   - the app reads the papers (use the owner id you noted):

     ```sh
     docker compose exec app uv run --no-sync python -c \
       "from app.docstore import get_store; print(len(get_store().list('OWNER_ID')))"
     ```

     prints that owner's paper count;
   - `docker compose up -d` starts Caddy too; `https://<ip>.sslip.io/ready` answers
     `{"status":"ready"}`.
7. Destroy the throwaway droplet. Its own backup job would upload to the same bucket at 03:00,
   so don't leave it running overnight.

If any step fails, fix the cause (and this page) before relying on the backups.

The same steps are the real recovery after losing the droplet: on the new droplet, use the real
domain in `.env`, restore, then run `docker compose up -d` and point DNS at the new address.

### Drill log

| Date | Dump | Result |
|------|------|--------|
| 2026-11-21 | local rehearsal with an S3 stand-in (EXA-180) | dump uploaded; restored into a new volume; app read the rows; old objects pruned by age |
