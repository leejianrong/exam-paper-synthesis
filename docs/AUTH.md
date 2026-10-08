# Accounts and sign-in (W3a)

Social sign-in only (ADR-0022): **Google, Microsoft, GitHub**. No passwords are stored.

## Configure (environment)

| Variable | Meaning |
|---|---|
| `EXAM_OAUTH_{GOOGLE,MICROSOFT,GITHUB}_CLIENT_ID` / `_CLIENT_SECRET` | Both set ⇒ that provider is offered on the login page. |
| `EXAM_PUBLIC_URL` | The API's external base URL (default `http://localhost:8000`). Redirect URIs are built from it; `https://…` also turns on `Secure` cookies. |
| `EXAM_WEB_URL` | The web app's URL (default `http://localhost:5173`). The only place the API ever redirects to, and the default CORS origin. |
| `EXAM_CORS_ORIGINS` | Optional comma-separated override of the allowed web origins. |
| `EXAM_AUTH_PATH` | SQLite accounts DB (default `~/.exam_engine/accounts.sqlite3`; Postgres arrives in W3b). |
| `EXAM_DEV_AUTH=1` | Local development stub: no sign-in, owner = `X-Dev-Owner` (default `local`). A valid session still wins. **Never set in production** — without it, anonymous requests are 401. |

## Register with each provider

Redirect (callback) URI: `{EXAM_PUBLIC_URL}/auth/{google|microsoft|github}/callback`.

- **Google**: OAuth client (Web application); scopes `openid email profile`.
- **Microsoft**: Entra app registration, accounts in any org directory and personal accounts ("common"); a client secret.
- **GitHub**: OAuth App (not a GitHub App); scopes `read:user user:email`.

## Behaviour worth knowing

- Flow: `/auth/{provider}/login` → provider → `/auth/{provider}/callback` → session cookie → web app. `state` is bound to the browser by an HttpOnly cookie (login CSRF) and PKCE S256 is used. The profile is read from the provider's userinfo endpoint with the access token just obtained from its token endpoint.
- Session: random token, stored hashed, 30 days; cookie `exam_session` is HttpOnly, SameSite=Lax. `POST /auth/logout` deletes it. `GET /auth/me` says who you are.
- Linking: a second provider reaches the same account **only** when both sides have a *verified* email (Google's `email_verified`; GitHub's primary verified address). Microsoft does not assert verification, so its email never links. An unverified email never links or claims an address.
- Documents, bank rows and assets are owned by the user id; a foreign id is always 404.
