#!/usr/bin/env bash
#
# Keep web/node_modules in step with web/package-lock.json.
#
# node_modules is untracked, so after a pull that adds a dependency (e.g.
# @tiptap/*) it silently goes stale and svelte-check / vitest fail with
# "Cannot find module" errors that look like code bugs. This compares a hash of
# the lockfile against a stamp written after the last successful `npm ci` and
# reinstalls only when they differ. Called from the pre-push and post-merge /
# post-checkout hooks and by `make install`.

set -euo pipefail

root="$(git rev-parse --show-toplevel)"
lock="$root/web/package-lock.json"
stamp="$root/web/node_modules/.lock.sha256"

[ -f "$lock" ] || exit 0

want="$(sha256sum "$lock" | cut -d' ' -f1)"
have="$(cat "$stamp" 2>/dev/null || true)"

if [ "$want" != "$have" ] || [ ! -d "$root/web/node_modules/.bin" ]; then
	echo "==> web deps out of date with package-lock.json: running npm ci"
	npm --prefix "$root/web" ci
	echo "$want" >"$stamp"
fi
