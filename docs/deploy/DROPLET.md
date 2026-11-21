# Droplet runbook

How to set up the production server once, deploy the app on it, and keep it running. The stack
itself is `deploy/compose.yaml` (Caddy → app → Postgres 17); backups and the restore drill are in
[BACKUPS.md](BACKUPS.md); the launch checklist is [../LAUNCH.md](../LAUNCH.md). Decisions:
[ADR-0024](../adr/0024-droplet-compose-hosting.md).

Every step ends with a **Check**. Commands run on the droplet as the `deploy` user unless the
step says otherwise. `HOST` below is the hostname users reach: `<droplet-ip>.sslip.io` until a
domain is bought, then the domain.

## 1. Create the droplet

In the DigitalOcean console: **Create → Droplets**.

- Region **Singapore (SGP1)**; image **Ubuntu 24.04 LTS x64**; size **Basic, Regular, 2 GB /
  1 vCPU** (US$12/month).
- Authentication: **SSH key** (add your public key; never a password).
- Turn on **Monitoring** (the free metrics agent, used for alerts in step 9). Droplet backups
  (weekly snapshots, +20%) are optional: the database has its own nightly dump.
- Hostname: `exam-prod`.

**Check:** `ssh root@<droplet-ip>` logs in without a password prompt.

## 2. Cloud firewall

**Networking → Firewalls → Create Firewall**, applied to the droplet. Inbound rules:

| Type | Protocol | Port | Sources |
|------|----------|------|---------|
| SSH | TCP | 22 | your own IP address if it is stable, else all |
| HTTP | TCP | 80 | all IPv4 (Let's Encrypt and the http → https redirect) |
| HTTPS | TCP | 443 | all IPv4 |
| Custom | UDP | 443 | all IPv4 (HTTP/3) |

Outbound: leave the defaults (all). Use this cloud firewall rather than `ufw`: Docker writes its
own iptables rules for published ports and goes around `ufw`, but it cannot go around a firewall
outside the droplet.

**Check:** from your laptop, `nc -zv <droplet-ip> 5432` and `nc -zv <droplet-ip> 8080` fail.

## 3. A deploy user and SSH hardening

As `root`:

```bash
adduser --disabled-password --gecos "" deploy
usermod -aG sudo deploy
mkdir -p /home/deploy/.ssh && cp /root/.ssh/authorized_keys /home/deploy/.ssh/
chown -R deploy:deploy /home/deploy/.ssh && chmod 700 /home/deploy/.ssh
echo 'deploy ALL=(ALL) NOPASSWD:ALL' > /etc/sudoers.d/deploy && chmod 440 /etc/sudoers.d/deploy
cat > /etc/ssh/sshd_config.d/99-hardening.conf <<'EOF'
PermitRootLogin no
PasswordAuthentication no
KbdInteractiveAuthentication no
EOF
sshd -t && systemctl reload ssh
```

**Check:** in a *new* terminal (keep the root one open until this works), `ssh deploy@<droplet-ip>`
logs in and `sudo true` succeeds; `ssh root@<droplet-ip>` is refused.

## 4. Swap

The droplet has no swap; Chromium's peaks are safer with 2 GB of it.

```bash
sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile
sudo mkswap /swapfile && sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
echo 'vm.swappiness=10' | sudo tee /etc/sysctl.d/99-swap.conf && sudo sysctl --system
```

**Check:** `free -h` shows `Swap: 2.0Gi`.

## 5. Automatic security updates

Ubuntu installs security updates daily by default (`unattended-upgrades`). Let it reboot when an
update needs one, at 03:30 Singapore time (19:30 UTC; the droplet's clock is UTC):

```bash
sudo tee /etc/apt/apt.conf.d/52unattended-upgrades-local <<'EOF'
Unattended-Upgrade::Automatic-Reboot "true";
Unattended-Upgrade::Automatic-Reboot-Time "19:30";
EOF
```

The containers come back by themselves after a reboot (`restart: unless-stopped`). Docker's own
packages are not in the automatic set: run `sudo apt update && sudo apt upgrade` monthly.

**Check:** `sudo unattended-upgrade --dry-run --debug 2>&1 | tail -3` ends without errors.

## 6. Docker, with log rotation

Docker's apt repository (not Ubuntu's older `docker.io`):

```bash
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
  | sudo tee /etc/apt/sources.list.d/docker.list
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker deploy
```

Rotate container logs (before the first `up`: it applies to containers created afterwards):

```bash
echo '{"log-driver": "local", "log-opts": {"max-size": "10m", "max-file": "5"}}' \
  | sudo tee /etc/docker/daemon.json
sudo systemctl restart docker
```

Log out and back in (for the `docker` group).

**Check:** `docker compose version` prints v2.x; `docker info --format '{{.LoggingDriver}}'`
prints `local`.

## 7. Sign-in apps

Both callback URLs are `https://HOST/auth/<provider>/callback`.

- **GitHub**: Settings → Developer settings → OAuth Apps → New OAuth App. Homepage
  `https://HOST`, callback `https://HOST/auth/github/callback`. Generate a client secret.
- **Google**: Google Cloud console → a new project → Google Auth Platform. Branding: app name,
  support email, home page `https://HOST`, privacy policy `https://HOST/privacy`, terms
  `https://HOST/terms` (EXA-185), and the domain under authorised domains. Audience: External.
  Clients → Create client → Web application → authorised redirect URI
  `https://HOST/auth/google/callback`. The app asks only for `openid email profile`, which
  needs no security review, but Google lets only listed test users sign in until the app is
  published (Audience → Publish app). Google expects the authorised domain to be one you own, so
  this step is where `sslip.io` is most likely to fall short; a bought domain avoids it.

When the hostname changes (a domain is bought), update both apps' URLs.

## 8. First deploy

```bash
sudo mkdir -p /opt/exam && sudo chown deploy:deploy /opt/exam
git clone --depth 1 https://github.com/leejianrong/exam-paper-synthesis.git /opt/exam
cd /opt/exam/deploy
cp .env.example .env && chmod 600 .env
nano .env    # HOST in SITE_ADDRESS and both URLs, POSTGRES_PASSWORD (openssl rand -hex 24),
             # the OAuth ids and secrets, the Spaces values (BACKUPS.md)
docker compose pull
docker compose up -d
```

The image must be public on GHCR first (GitHub → Packages → exam-paper-synthesis → Package
settings → Change visibility), or log in with `docker login ghcr.io` and a `read:packages` token.

Only an IPv4 address (an A record) should point at the droplet. Docker hands IPv6 visitors to
Caddy from its bridge gateway, so they would all share one sign-in rate limit; add an AAAA record
only together with IPv6 on the stack's network.

**Check:**
- `docker compose ps` shows `db`, `app`, `caddy` (and `backup`) running, `db` and `app` healthy.
- `docker compose logs caddy | grep -i "certificate obtained"` shows the certificate for HOST.
- From your laptop: `curl -fsS https://HOST/ready` prints `{"status":"ready"}`, and
  `curl -sI http://HOST/` answers `308` to `https://`.
- If the app keeps restarting, `docker compose logs app` names each unsafe setting.

Then run the smoke test in [LAUNCH.md](../LAUNCH.md).

## 9. Monitoring (EXA-183)

In the DigitalOcean console:

- **Monitoring → Uptime → Create Uptime check**: type HTTPS, URL `https://HOST/ready`, regions
  including Southeast Asia. Alerts: *Downtime* (down for 2 minutes) and *SSL certificate
  expiry* (within 14 days), to your email. `/ready` answers 503 when the database is
  unreachable, so it catches a broken database as well as a stopped app.
- **Monitoring → Create alert policy** on the droplet: memory above 90% for 5 minutes; disk
  above 80% for 5 minutes; CPU above 90% for 15 minutes.

**Check:** `docker compose stop app`; the downtime email arrives within a few minutes;
`docker compose start app`; the recovery email follows.

## Day to day

| Task | Command (in `/opt/exam/deploy`) |
|------|------|
| Deploy the latest main | `git pull && docker compose pull && docker compose up -d` |
| Roll back | set `APP_TAG=sha-<commit>` in `.env`, then `docker compose up -d app` |
| Status | `docker compose ps` |
| Logs | `docker compose logs -f --tail 100 app` (or `caddy`, `db`) |
| Restart the app | `docker compose restart app` |
| Change the hostname | edit `SITE_ADDRESS`, `EXAM_PUBLIC_URL`, `EXAM_WEB_URL` in `.env`, `docker compose up -d`, then update the OAuth apps (step 7) and the uptime check |
| Disk use | `df -h /` and `docker system df`; `docker image prune -a` removes old images |

Every merge to main publishes `:latest` and `:sha-<commit>`; nothing deploys by itself.
