# The stack's backup job (EXA-180): Postgres 17's pg_dump/pg_restore/psql plus rclone for Spaces.
# Keep the client's major in step with the db service: pg_dump must not be older than the server.
# (Not FROM postgres:17-alpine: its VOLUME line would leave an empty anonymous volume behind.)
FROM docker.io/rclone/rclone:1.71 AS rclone

FROM docker.io/library/alpine:3.22
RUN apk add --no-cache postgresql17-client \
    && adduser -D -H backup \
    && touch /etc/rclone.conf
COPY --from=rclone /usr/local/bin/rclone /usr/local/bin/rclone
COPY exam-backup /usr/local/bin/exam-backup
# Singapore time without tzdata (no daylight saving there).
ENV TZ=SGT-8
# rclone's remote comes from RCLONE_CONFIG_SPACES_* (compose); an empty file stops a notice per call.
ENV RCLONE_CONFIG=/etc/rclone.conf
USER backup
WORKDIR /tmp
CMD ["exam-backup", "schedule"]
