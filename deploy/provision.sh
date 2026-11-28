#!/usr/bin/env bash
# Create the production droplet and its cloud firewall with doctl (docs/deploy/DROPLET.md,
# steps 1-2); deploy/cloud-init.yaml then does steps 3-6 on first boot. Run from your laptop
# after `doctl auth init`. It refuses to touch a droplet that already exists.
#
#   deploy/provision.sh                      # 1 GB droplet in Singapore, SSH from anywhere
#   SSH_FROM=203.0.113.7/32 deploy/provision.sh
#
# Settings (environment): NAME (exam-prod), SIZE (s-1vcpu-1gb; s-1vcpu-2gb for 2 GB),
# REGION (sgp1), SSH_PUBKEY (~/.ssh/id_ed25519.pub), SSH_FROM (addresses allowed to SSH).
set -euo pipefail

NAME=${NAME:-exam-prod}
SIZE=${SIZE:-s-1vcpu-1gb}
REGION=${REGION:-sgp1}
IMAGE=ubuntu-24-04-x64
SSH_PUBKEY=${SSH_PUBKEY:-$HOME/.ssh/id_ed25519.pub}
SSH_FROM=${SSH_FROM:-0.0.0.0/0,::/0}
TAG=$NAME                       # the firewall and the alerts follow the tag, not a droplet id
here=$(cd "$(dirname "$0")" && pwd)

doctl account get >/dev/null || { echo "doctl isn't signed in: run doctl auth init" >&2; exit 1; }
[ -f "$SSH_PUBKEY" ] || { echo "No SSH public key at $SSH_PUBKEY (set SSH_PUBKEY)" >&2; exit 1; }

if doctl compute droplet list --format Name --no-header | grep -qx "$NAME"; then
  echo "A droplet called $NAME already exists; nothing was changed:" >&2
  doctl compute droplet list --format Name,PublicIPv4,Memory,Status | grep -E "^(Name|$NAME) " >&2
  exit 1
fi

# The SSH key, imported once (DigitalOcean names keys by their MD5 fingerprint).
fp=$(ssh-keygen -E md5 -lf "$SSH_PUBKEY" | awk '{print $2}'); fp=${fp#MD5:}
if ! doctl compute ssh-key get "$fp" >/dev/null 2>&1; then
  doctl compute ssh-key import "$NAME-$(hostname -s)" --public-key-file "$SSH_PUBKEY" >/dev/null
  echo "Imported the SSH key $SSH_PUBKEY"
fi

# The firewall first, by tag, so the droplet is covered from its first boot. A firewall can
# only name a tag that exists; creating one that does is harmless.
doctl compute tag create "$TAG" >/dev/null
all='address:0.0.0.0/0,address:::/0'
if ! doctl compute firewall list --format Name --no-header | grep -qx "$NAME-firewall"; then
  ssh_addresses=address:${SSH_FROM//,/,address:}
  doctl compute firewall create --name "$NAME-firewall" --tag-names "$TAG" \
    --inbound-rules "protocol:tcp,ports:22,$ssh_addresses protocol:tcp,ports:80,$all protocol:tcp,ports:443,$all protocol:udp,ports:443,$all" \
    --outbound-rules "protocol:tcp,ports:all,$all protocol:udp,ports:all,$all protocol:icmp,$all" \
    >/dev/null
  echo "Created the firewall $NAME-firewall (SSH from $SSH_FROM; 80, 443 and UDP 443 from all)"
fi

# Monitoring on (the free metrics agent, for the resource alerts); Droplet backups off: DigitalOcean
# keeps those for about four weeks, past the privacy notice's 14 days.
echo "Creating $NAME ($SIZE, $REGION)…"
ip=$(doctl compute droplet create "$NAME" --region "$REGION" --size "$SIZE" --image "$IMAGE" \
  --ssh-keys "$fp" --tag-name "$TAG" --enable-monitoring \
  --user-data-file "$here/cloud-init.yaml" --wait --format PublicIPv4 --no-header)

cat <<EOF

Droplet $NAME is up at $ip. First-boot set-up (deploy user, swap, Docker) takes a few minutes;
it has finished when this prints "ready" (until the deploy user exists, the login is refused):

  ssh deploy@$ip 'test -f /var/lib/exam-setup-done && echo ready || sudo tail -3 /var/log/cloud-init-output.log'

HOST is $ip.sslip.io until a domain is bought. Next: docs/deploy/DROPLET.md step 7.
EOF
