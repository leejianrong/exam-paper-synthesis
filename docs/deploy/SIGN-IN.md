# Setting up Google and GitHub sign-in

The app has no passwords: teachers sign in with Google or GitHub. Each provider needs an
**OAuth app** that you register by hand in its console. It gives you a **client ID** and a
**client secret**, which go into `deploy/.env` on the droplet. This guide walks through both, for
the private trial on `<droplet-ip>.sslip.io` first and for the public launch on a real domain
later.

Steps marked **(you)** happen in a browser console and only you can do them. Everything else
is a command on the droplet.

## Before you start

- **The droplet exists and you know its IPv4 address.** Every URL below depends on it. This
  guide calls the hostname `HOST`: with the address `203.0.113.10`, HOST is
  `203.0.113.10.sslip.io`. Swap in your own address everywhere.
- **The app reads two URLs from `.env`**, and the callback addresses are built from the first:

  ```
  EXAM_PUBLIC_URL=https://HOST
  EXAM_WEB_URL=https://HOST
  ```

- **Each provider sends the teacher back to one fixed address**, which must match character for
  character (https, no trailing slash):

  | Provider | Callback (redirect) URL |
  |----------|-------------------------|
  | Google | `https://HOST/auth/google/callback` |
  | GitHub | `https://HOST/auth/github/callback` |

- **What the app asks for** (nothing else, and never write access):
  - Google: `openid email profile`, which is the teacher's name, email address and Google
    account id.
  - GitHub: `read:user user:email`, which is the profile and email addresses.

## How private is the private trial?

- **Google** stays in *Testing* mode, so only the people you list as test users (up to 100) can
  sign in with Google.
- **GitHub** has no such list of its own, so the app has one: set `EXAM_ALLOWED_EMAILS` in
  `.env` to the invited addresses, and `@domain` entries for whole schools:

  ```
  EXAM_ALLOWED_EMAILS=you@gmail.com, teacher@example.org, @school.edu.sg
  ```

  Then only someone whose Google or GitHub account has a **verified** email on the list can
  sign in or create an account, with either provider. Anyone else goes back to the sign-in
  page with "This server is open to invited teachers only". Taking an address off the list
  (then `docker compose up -d app`) ends that person's sessions at once.
- At the public launch, empty `EXAM_ALLOWED_EMAILS` and run `docker compose up -d app`. Also
  publish the Google app (see the end of this guide).

## GitHub

### 1. Register the OAuth app (you)

1. Sign in to github.com. Click your avatar (top right) → **Settings** → **Developer settings**
   (bottom of the left menu) → **OAuth Apps** → **New OAuth App**. If you see "Register a new
   application" instead, it is the same button.
   - Pick **OAuth Apps**, not **GitHub Apps**: they are different things, and the app supports
     OAuth Apps only.
2. Fill in:
   - **Application name**: `Exam papers` (teachers see it on GitHub's consent page).
   - **Homepage URL**: `https://HOST`
   - **Application description**: optional, e.g. "Make maths exam papers with answer keys".
   - **Authorization callback URL**: `https://HOST/auth/github/callback`
   - **Enable Device Flow**: leave unticked.
3. Click **Register application**.
4. On the app's page, copy the **Client ID**.
5. Click **Generate a new client secret**, confirm with your password or passkey, and **copy the
   secret now**. GitHub shows it only once; if you lose it, generate another and delete the old
   one.
6. Optional: under **Upload new logo**, add an icon. Teachers see it on the consent page.

One GitHub OAuth App allows exactly **one** callback URL. You will need a second app for local
development (see "Local development" below), and you will edit this one when the hostname
changes.

### 2. Put it on the droplet

In `/opt/exam/deploy/.env`:

```
EXAM_OAUTH_GITHUB_CLIENT_ID=<the Client ID>
EXAM_OAUTH_GITHUB_CLIENT_SECRET=<the secret>
```

Then apply it. A plain `restart` would not pick up a changed `.env`; `up -d` recreates the
container:

```bash
cd /opt/exam/deploy && docker compose up -d app
```

### 3. Check it

- `curl -s https://HOST/auth/providers` lists `{"name":"github","label":"GitHub"}`.
- In a private browser window, open `https://HOST`, click **Sign in with GitHub**, approve, and
  you land in the app signed in.
- GitHub → Settings → **Applications** → **Authorized OAuth Apps** now lists Exam papers. That
  is also where a teacher can revoke it.

## Google

Google's console names change often. As of late 2026 the consent-screen pages live under
**Google Auth Platform**; the older **APIs & Services → OAuth consent screen** link takes you
there too.

### 1. Create a project (you)

1. Go to <https://console.cloud.google.com/> and sign in with the Google account that will own
   the app. Use an account you will keep: it owns the sign-in for every teacher.
2. Project picker (top bar) → **New project** → name `Exam papers` → **Create**. No billing
   account is needed for sign-in. Make sure the new project is selected in the top bar.

### 2. Set up the consent screen (you)

1. Menu → **Google Auth Platform** (or search for "Google Auth Platform") → **Get started**.
2. **App information**: app name `Exam papers`; user support email (your address; teachers see
   it).
3. **Audience**: **External** (teachers use their own Google or school accounts, not your
   organisation's).
4. **Contact information**: your email (Google writes to it about the app).
5. Agree to the Google API Services User Data Policy → **Create**.
6. **Branding** (left menu). For the trial, fill in only what is required, but add these now if
   the policy pages are live:
   - The privacy and terms pages arrive with EXA-185 (PR #268); leave those two links empty
     until it is deployed.
   - **Application home page**: `https://HOST`
   - **Application privacy policy link**: `https://HOST/privacy`
   - **Application terms of service link**: `https://HOST/terms`
   - **Authorised domains**: on sslip.io, Google accepts only `sslip.io` itself here, a domain
     you do not own. That is fine while the app is in Testing. If Google refuses to save it,
     leave this list empty for the trial.
   - Save.
7. **Audience** (left menu): check that the publishing status is **Testing**. Under **Test
   users** → **Add users**, enter the Google addresses of everyone in the trial, yourself
   included, and save. Only these people can sign in until the app is published.
8. **Data Access**: nothing to add. `openid`, email and profile are basic scopes, which need no
   review. You may add them under **Add or remove scopes** so the list documents what the app
   asks for.

### 3. Create the client (you)

1. **Clients** (left menu) → **Create client**.
2. **Application type**: **Web application**. Name: `Exam papers (production)`.
3. **Authorised JavaScript origins**: leave empty. The sign-in runs on the server, not in the
   browser.
4. **Authorised redirect URIs** → **Add URI**: `https://HOST/auth/google/callback`. Google
   usually accepts an sslip.io host here (and adds `sslip.io` to the authorised domains by
   itself). If it refuses the URI, the trial needs a real domain for Google; GitHub sign-in
   works either way.
5. **Create**. Copy the **Client ID** and the **Client secret** now, or use **Download JSON** in
   that dialog: once it closes, Google never shows the secret again. If you lose it, add a new
   secret on the client's page and delete the old one.

Google also lets one client hold several redirect URIs, so when you buy a domain you add its
callback next to the sslip.io one and remove the old one later.

### 4. Put it on the droplet

```
EXAM_OAUTH_GOOGLE_CLIENT_ID=<the Client ID, ends in .apps.googleusercontent.com>
EXAM_OAUTH_GOOGLE_CLIENT_SECRET=<the secret, starts with GOCSPX->
```

```bash
cd /opt/exam/deploy && docker compose up -d app
```

### 5. Check it

- `curl -s https://HOST/auth/providers` lists Google too.
- A test user signs in with **Sign in with Google**. In Testing mode Google shows a "Google
  hasn't verified this app" warning: click **Continue**. Your test users will see it too, so
  tell them to expect it.
- Someone who is **not** a test user gets "Access blocked … has not completed the Google
  verification process". That is the Testing-mode limit doing its job.

## When something goes wrong

| What you see | Usually means | Fix |
|--------------|---------------|-----|
| Google: `Error 400: redirect_uri_mismatch` | The callback in the client differs from `EXAM_PUBLIC_URL` + `/auth/google/callback` | Compare character for character: https, the exact host, no trailing slash. Changes can take a few minutes to apply. |
| GitHub: "The redirect_uri is not associated with this application" | Same mismatch, for GitHub | Edit the app's Authorization callback URL. |
| Google: "Access blocked: … has not completed the Google verification process" | The account is not a test user | Add it under Audience → Test users. |
| The app's sign-in page shows no button for a provider | Its ID or secret is missing from `.env`, or the container wasn't recreated | Fill both lines, then `docker compose up -d app`. |
| Back on the sign-in page: "The sign-in service didn't accept the request" | Wrong client secret (or ID) in `.env` | Copy it again, or generate a new secret; `docker compose up -d app`. The app's log does not record the provider's answer, so check the values against the console. |
| Back on the sign-in page: "That sign-in took too long or was started in another tab" | More than 10 minutes on the provider's page, or two sign-ins at once | Sign in again in one tab. |
| The app container keeps restarting | No provider is configured, so the production check refuses to boot | `docker compose logs app` names the problem; add at least one provider. |

## How the two sign-ins relate

- A teacher who signs in with Google and later with GitHub **using the same verified email
  address** reaches the same account.
- If the GitHub account's primary email is not verified, or differs from the Google address,
  the GitHub sign-in becomes a separate, empty account (`docs/AUTH.md`, Linking). A primary
  address that is merely hidden on the GitHub profile still links.
- Revoking the app at Google or GitHub stops future sign-ins. It does not delete anything in
  the app: deleting the account is done from the account menu.

## Local development

You don't need the production apps to work on your own machine. `EXAM_DEV_AUTH=1` skips sign-in
locally. To test real sign-in locally, register **separate** apps:

- **GitHub**: a second OAuth App with callback `http://localhost:8000/auth/github/callback`.
- **Google**: a second client (a separate one, so the production secret never reaches a
  laptop) with `http://localhost:8000/auth/google/callback`. Google allows plain http for
  `localhost` only.

Never put production secrets on a laptop, and never commit any `.env`.

## Going public on a real domain later

When the domain (e.g. `paperbench.dev`) points at the droplet:

1. **Droplet**: set `SITE_ADDRESS`, `EXAM_PUBLIC_URL` and `EXAM_WEB_URL` to the domain in
   `.env`, then `docker compose up -d`. Caddy gets the new certificate by itself.
2. **GitHub (you)**: edit the OAuth App's Homepage URL and callback to the domain. One callback
   only, so the sslip.io address stops working at that moment.
3. **Google (you)**:
   1. Add `https://<domain>/auth/google/callback` to the client's redirect URIs.
   2. Under Branding, set the home page, privacy and terms links to the domain, and put the
      domain under **Authorised domains**.
   3. Verify that you own the domain in **Google Search Console** (a DNS TXT record at your
      registrar), with the same Google account.
   4. Under **Audience**, click **Publish app** so anyone can sign in.
   5. For the app's name and logo to show on the consent screen, Google runs a brand check,
      which usually takes a few days. Basic scopes need no security assessment.
4. **Contact address**: once the privacy pages are deployed (EXA-185, PR #268), set
   `EXAM_CONTACT_EMAIL` (e.g. `hello@<domain>`) so they name it. Then remove the sslip.io
   redirect URI from the Google client.
5. **Check**: sign in with both providers from a private window, using an account that was not
   a test user.

## Keeping the secrets safe

- The secrets live only in `/opt/exam/deploy/.env` (mode 600) and in the provider consoles.
  Don't paste them in chat, email or the repo.
- **If one leaks**:
  1. Generate a new secret in the console.
  2. Put it in `.env` and run `docker compose up -d app`.
  3. Then delete the old secret.

  Teachers stay signed in: their sessions do not depend on the secret.
