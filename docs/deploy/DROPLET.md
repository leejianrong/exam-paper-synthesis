# Droplet runbook

How to set up the production server once, deploy the app on it, and keep it running. The stack
itself is `deploy/compose.yaml` (Caddy → app → Postgres 17); backups and the restore drill are in
[BACKUPS.md](BACKUPS.md); the launch checklist is [../LAUNCH.md](../LAUNCH.md). Decisions:
[ADR-0024](../adr/0024-droplet-compose-hosting.md).

Every step ends with a **Check**. Commands run on the droplet as the `deploy` user unless the
step says otherwise. `HOST` below is the hostname users reach: `examsmith.app`
(on a droplet without a domain, `<droplet-ip>.sslip.io`).

## 1. Create the droplet (doctl)

From your laptop, with [doctl](https://docs.digitalocean.com/reference/doctl/how-to/install/)
installed. Sign it in once with an API token (**API → Tokens → Generate New Token**, with an
expiry): full access is simplest; a custom-scoped token needs *account* (read) and create, read,
update and delete on *droplet*, *firewall*, *ssh_key*, *tag*, *monitoring* and *uptime* (the
console adds the read scopes these depend on):

```bash
doctl auth init          # paste the token at the prompt; it is stored in doctl's own config
deploy/provision.sh      # or SSH_FROM=<your-ip>/32 deploy/provision.sh
```

`deploy/provision.sh` imports your SSH key (`~/.ssh/id_ed25519.pub`), creates the cloud firewall
(step 2) and a **Basic 1 GB / 1 vCPU** droplet (`s-1vcpu-1gb`, US$6/month) in **Singapore (SGP1)**
on **Ubuntu 24.04**, named `exam-prod`, with **Monitoring** on (the free metrics agent, used for
alerts in step 9) and **Droplet backups** off: DigitalOcean keeps those snapshots for about four
weeks, but the privacy notice promises every copy of the data is gone within 14 days. The
database has its own nightly dump ([BACKUPS.md](BACKUPS.md)), and the droplet itself can be
rebuilt from this runbook. It refuses to run if a droplet with that name already exists.

On its first boot the droplet runs `deploy/cloud-init.yaml`, which does steps 3–6 below and
clones the repo into `/opt/exam`, in a few minutes. The steps say what it did, so the droplet can
also be set up by hand (create it in the console, then run each block as root), and each has a
**Check** to run once it has finished:

```bash
ssh deploy@<droplet-ip> 'test -f /var/lib/exam-setup-done && echo ready || sudo tail -3 /var/log/cloud-init-output.log'
```

The set-up script (`/usr/local/sbin/exam-setup`) stops at the first failure. If the check prints
log lines instead of `ready`, `sudo less /var/log/cloud-init-output.log` shows which command
failed; fix the cause and run `sudo /usr/local/sbin/exam-setup` again (every step is safe to
repeat), or do the remaining steps by hand.

## 2. Cloud firewall

Created by `provision.sh` as `exam-prod-firewall`, applied by the droplet's tag (`exam-prod`), so
a rebuilt droplet with the same tag is covered too. Inbound rules:

| Type | Protocol | Port | Sources |
|------|----------|------|---------|
| SSH | TCP | 22 | `SSH_FROM`: your own IP address if it is stable, else all (the default) |
| HTTP | TCP | 80 | all (Let's Encrypt and the http → https redirect) |
| HTTPS | TCP | 443 | all |
| Custom | UDP | 443 | all (HTTP/3) |

Outbound: everything. Use this cloud firewall rather than `ufw`: Docker writes its own iptables
rules for published ports and goes around `ufw`, but it cannot go around a firewall outside the
droplet. To change the SSH source later: **Networking → Firewalls → exam-prod-firewall**.

**Check:** `doctl compute firewall list` shows `exam-prod-firewall` with tag `exam-prod`. Then on
the droplet run `sudo python3 -m http.server 8000` and, from your laptop,
`nc -zv -w5 <droplet-ip> 8000` times out (Ctrl-C the server afterwards).

## 3. A deploy user and SSH hardening

What cloud-init ran, as `root`:

```bash
adduser --disabled-password --comment "" deploy
usermod -aG sudo deploy
mkdir -p /home/deploy/.ssh && cp /root/.ssh/authorized_keys /home/deploy/.ssh/
chown -R deploy:deploy /home/deploy/.ssh && chmod 700 /home/deploy/.ssh
echo 'deploy ALL=(ALL) NOPASSWD:ALL' > /etc/sudoers.d/deploy && chmod 440 /etc/sudoers.d/deploy
# 00-: sshd keeps the first value it reads, and DigitalOcean's 50-cloud-init.conf comes later.
cat > /etc/ssh/sshd_config.d/00-hardening.conf <<'EOF'
PermitRootLogin no
PasswordAuthentication no
KbdInteractiveAuthentication no
EOF
sshd -t && systemctl reload ssh
```

**Check:** `ssh deploy@<droplet-ip>` logs in and `sudo true` succeeds; `ssh root@<droplet-ip>` is
refused; and `sudo sshd -T | grep -E 'permitrootlogin|passwordauthentication|kbdinteractive'`
prints `no` for all three.

## 4. Swap

A 1 GB droplet relies on swap for Chromium's peaks; cloud-init adds 2 GB of it:

```bash
fallocate -l 2G /swapfile && chmod 600 /swapfile
mkswap /swapfile && swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab
echo 'vm.swappiness=10' > /etc/sysctl.d/99-swap.conf && sysctl --system
```

**Check:** `free -h` shows `Swap: 2.0Gi`.

## 5. Automatic security updates

Ubuntu installs security updates daily by default (`unattended-upgrades`). cloud-init lets it
reboot when an update needs one, at 03:30 Singapore time (19:30 UTC; the droplet's clock is UTC):

```bash
tee /etc/apt/apt.conf.d/52unattended-upgrades-local <<'EOF'
Unattended-Upgrade::Automatic-Reboot "true";
Unattended-Upgrade::Automatic-Reboot-Time "19:30";
EOF
```

The containers come back by themselves after a reboot (`restart: unless-stopped`). Docker's own
packages are not in the automatic set: run `sudo apt update && sudo apt upgrade` monthly.

**Check:** `apt-config dump | grep Automatic-Reboot` shows `"true"` and `"19:30"`.

## 6. Docker, with log rotation

Docker's apt repository (not Ubuntu's older `docker.io`), with container logs rotated (the
`daemon.json` is written before Docker starts, so it applies to every container):

```bash
mkdir -p /etc/docker
echo '{"log-driver": "local", "log-opts": {"max-size": "10m", "max-file": "5"}}' > /etc/docker/daemon.json
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
  > /etc/apt/sources.list.d/docker.list
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
usermod -aG docker deploy
```

(Done by hand on a running Docker, `sudo systemctl restart docker` afterwards, then log out and
back in for the `docker` group.)

**Check:** `docker compose version` prints v2 or later; `docker info --format '{{.LoggingDriver}}'`
prints `local`.

## 7. Sign-in apps

The full walk-through, with every console click and the fixes for common errors, is
[SIGN-IN.md](SIGN-IN.md). In short:

Both callback URLs are `https://HOST/auth/<provider>/callback`.

- **GitHub**: Settings → Developer settings → OAuth Apps → New OAuth App. Homepage
  `https://HOST`, callback `https://HOST/auth/github/callback`. Generate a client secret.
- **Google**: Google Cloud console → a new project → Google Auth Platform. Branding: app name,
  support email, home page `https://HOST`, privacy policy `https://HOST/privacy`, terms
  `https://HOST/terms` (EXA-185), and the domain under authorised domains (on sslip.io Google
  takes only `sslip.io` itself there, since it is not on the Public Suffix List). Audience: External.
  Clients → Create client → Web application → authorised redirect URI
  `https://HOST/auth/google/callback`. The app asks only for `openid email profile`, which
  needs no security review, but Google lets only listed test users sign in until the app is
  published (Audience → Publish app). Google expects the authorised domain to be one you own, so
  this step is where `sslip.io` is most likely to fall short; a bought domain avoids it.

When the hostname changes (a domain is bought), update both apps' URLs.

## 8. First deploy

The app image on GHCR is public, so no registry login is needed. If `docker compose pull` is
ever denied, check GitHub → Packages → exam-paper-synthesis → Package settings → visibility.
The backup job's small image is built on the droplet from `deploy/backup/` (hence `--build`).

cloud-init has already cloned the repo into `/opt/exam` (by hand:
`sudo mkdir -p /opt/exam && sudo chown deploy:deploy /opt/exam && git clone --depth 1
https://github.com/leejianrong/exam-paper-synthesis.git /opt/exam`).

```bash
cd /opt/exam/deploy
cp .env.example .env && chmod 600 .env
nano .env    # HOST in SITE_ADDRESS and both URLs, POSTGRES_PASSWORD (openssl rand -hex 24),
             # the OAuth ids and secrets, the Spaces values (BACKUPS.md)
docker compose pull --ignore-buildable
docker compose up -d --build
```

Only an IPv4 address (an A record) should point at the droplet. Docker hands IPv6 visitors to
Caddy from its bridge gateway, so they would all share one sign-in rate limit; add an AAAA record
only together with IPv6 on the stack's network.

**Check:**
- `docker compose ps` shows `db`, `app`, `caddy` (and `backup`) running, `db` and `app` healthy.
- `docker compose logs caddy | grep -i "certificate obtained"` shows the certificate for HOST.
  On sslip.io, Let's Encrypt's weekly limit per registered domain is shared by every sslip.io
  user; if it refuses, Caddy retries with ZeroSSL by itself (look for `zerossl` in the log).
  Another reason to buy a domain.
- From your laptop: `curl -fsS https://HOST/ready` prints `{"status":"ready"}`, and
  `curl -sI http://HOST/` answers `308` to `https://`.
- If the app keeps restarting, `docker compose logs app` names each unsafe setting.

Then run the smoke test in [LAUNCH.md](../LAUNCH.md).

## 9. Monitoring (EXA-183)

From your laptop, with `HOST` and your email address filled in:

```bash
HOST=examsmith.app; EMAIL=you@example.com
# Uptime check on /ready from all four locations, with downtime and certificate alerts.
check=$(doctl monitoring uptime create exam-ready --target "https://$HOST/ready" --type https \
  --regions us_east,us_west,eu_west,se_asia --format ID --no-header)
doctl monitoring uptime alert create "$check" --name "exam down" --type down \
  --comparison less_than --threshold 1 --period 2m --emails "$EMAIL"
doctl monitoring uptime alert create "$check" --name "exam certificate" --type ssl_expiry \
  --threshold 14 --period 2m --emails "$EMAIL"
# Resource alerts for every droplet tagged exam-prod.
alert() {  # metric, percent, window (5m, 10m, 30m or 1h)
  doctl monitoring alert create --type "v1/insights/droplet/$1" --compare GreaterThan \
    --value "$2" --window "$3" --tags exam-prod --emails "$EMAIL" --description "exam-prod $1"
}
alert memory_utilization_percent 90 5m
alert disk_utilization_percent 80 5m
alert cpu 90 10m
```

`/ready` answers 503 when the database is unreachable, so the uptime check catches a broken
database as well as a stopped app. On a 1 GB droplet the memory alert at 90% may fire during an
export now and then; one that lasts the full 5 minutes means it is time to scale up (below).
(The same checks can be made in the console: **Monitoring → Uptime** and **Resource Alerts**.)

**Check:** `docker compose stop app`; the downtime email arrives within a few minutes;
`docker compose start app`; the recovery email follows.

## Scaling up

The droplet starts at 1 GB with one PDF render at a time (`EXAM_EXPORT_CONCURRENCY=1`), which is
enough for a few teachers: a second export waits for the first, which takes under a second. Move
to 2 GB when the memory alert keeps firing, `free -h` shows swap in steady use, or teachers see
"The server is busy". From your laptop (about a minute of downtime; the disk is kept as it is,
so the move can be undone):

```bash
id=$(doctl compute droplet list --format ID,Name --no-header | awk '$2 == "exam-prod" {print $1}')
doctl compute droplet-action power-off "$id" --wait
doctl compute droplet-action resize "$id" --size s-1vcpu-2gb --wait
doctl compute droplet-action power-on "$id" --wait
```

Then on the droplet, in `/opt/exam/deploy/.env`, uncomment the 2 GB memory limits at the end and
set `EXAM_EXPORT_CONCURRENCY=2`, and run `docker compose up -d`.

## Day to day

| Task | Command (in `/opt/exam/deploy`) |
|------|------|
| Deploy the latest main | `git pull && docker compose pull --ignore-buildable && docker compose up -d --build` |
| Roll back | set `APP_TAG=sha-<commit>` in `.env`, then `docker compose up -d app` |
| Status | `docker compose ps` |
| Logs | `docker compose logs -f --tail 100 app` (or `caddy`, `db`) |
| Restart the app | `docker compose restart app` |
| Change the hostname | edit `SITE_ADDRESS`, `EXAM_PUBLIC_URL`, `EXAM_WEB_URL` in `.env`, `docker compose up -d`, then update the OAuth apps (step 7) and the uptime check |
| Disk use | `df -h /` and `docker system df`; `docker image prune -a` removes old images |

Every merge to main publishes `:latest` and `:sha-<commit>`; nothing deploys by itself.
