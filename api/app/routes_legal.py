"""EXA-185: the privacy notice and terms, as plain server-rendered pages anyone can read.

``GET /privacy`` and ``GET /terms`` need no sign-in: Google's consent screen links to them and a
teacher reads them before signing in. They are static text with no script; the contact address
is ``EXAM_CONTACT_EMAIL`` (set on the server, shown escaped). The wording is the owner's to
approve; change ``UPDATED`` whenever it changes.
"""

import base64
import os
from functools import lru_cache
from html import escape
from importlib.resources import files

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

APP_NAME = "Examsmith"
UPDATED = "21 November 2026"


def contact_html() -> str:
    """The contact sentence: a mailto link, or a plain note while no address is configured."""
    email = os.environ.get("EXAM_CONTACT_EMAIL", "").strip()
    if not email:
        return "A contact address will be published here before the service opens to the public."
    e = escape(email, quote=True)
    return f'Write to <a href="mailto:{e}">{e}</a>.'


@lru_cache(maxsize=1)
def _font_css() -> str:
    """Inter (the one typeface, EXA-94), regular and semibold latin, inlined like the papers."""
    fonts = files("exam_engine") / "assets" / "fonts"
    rules = []
    for weight in (400, 600):
        raw = (fonts / f"inter-latin-{weight}-normal.woff2").read_bytes()
        rules.append(
            '@font-face{font-family:"Inter";font-style:normal;'
            f"font-weight:{weight};font-display:swap;"
            f"src:url(data:font/woff2;base64,{base64.b64encode(raw).decode('ascii')}) "
            'format("woff2")}'
        )
    return "\n".join(rules)


_STYLE = """
:root{--ink:#1d1d1f;--muted:#5b5b60;--line:#dcdce0;--bg:#fff;--link:#1f4fbf}
@media (prefers-color-scheme:dark){:root{--ink:#ececf0;--muted:#a4a4ab;--line:#3a3a40;
--bg:#16161a;--link:#8fb0ff}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.6 Inter,sans-serif}
main{max-width:44rem;margin:0 auto;padding:2.5rem 1rem 4rem}
h1{font-size:1.75rem;line-height:1.25;margin:0 0 .25rem}
h2{font-size:1.125rem;margin:2rem 0 .5rem}
p,li{margin:.5rem 0}
ul{padding-left:1.25rem}
a{color:var(--link)}
.meta{color:var(--muted);margin:0 0 2rem}
nav{display:flex;gap:1.25rem;border-bottom:1px solid var(--line);padding-bottom:.75rem;
margin-bottom:2rem}
"""


def _page(title: str, body: str) -> HTMLResponse:
    html = f"""<!doctype html>
<html lang="en-SG">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)} · {APP_NAME}</title>
<style>{_font_css()}{_STYLE}</style>
</head>
<body>
<main>
<nav><a href="/">{APP_NAME}</a><a href="/privacy">Privacy</a><a href="/terms">Terms</a></nav>
<h1>{escape(title)}</h1>
<p class="meta">Last updated {UPDATED}</p>
{body}
</main>
</body>
</html>"""
    return HTMLResponse(html)


PRIVACY = """
<p>{app} is a free tool for teachers to make maths exam papers. It is meant for teachers, not
for students or children. It is run by an independent developer in Singapore, who is also its
data protection officer (contact below). This notice says what it keeps about you, why, for how
long, and how to get it back or delete it. We handle personal data in line with Singapore's
Personal Data Protection Act.</p>

<h2>What we keep</h2>
<ul>
<li><strong>Your account</strong>: from your sign-in provider (Google or GitHub), your name,
your email address, whether the provider has verified that address, and the provider's id for
you; and when your account was made. We never see or store a password.</li>
<li><strong>Your work</strong>: the papers you make and their folders, the questions in your
question bank, the images you upload and your settings.</li>
<li><strong>Your export allowance</strong>: the time of each PDF or Word export, to apply the
daily limit. Each record is removed after 24 hours.</li>
<li><strong>Sign-in records and cookies</strong>: one first-party cookie keeps you signed in for
up to 30 days; the server keeps a record of that session (a scrambled copy of the cookie and its
expiry date). Two more first-party cookies live for at most 10 minutes while you sign in, to
protect the sign-in step. There are no advertising or tracking cookies and no third-party
analytics.</li>
<li><strong>Error logs</strong>: when something goes wrong, the server notes the error. It does
not keep a log of each visit or of visitors' addresses.</li>
</ul>

<h2>Information from Google</h2>
<p>When you sign in with Google we ask only for your basic profile: your name, your email
address and your Google account id (the <code>openid email profile</code> scopes). We use it
only to sign you in and to show you who is signed in. We do not share it with anyone except the
hosting company that stores it for us, and deleting your account deletes it. Our use of
information received from Google APIs adheres to the
<a href="https://developers.google.com/terms/api-services-user-data-policy">Google API Services
User Data Policy</a>, including its Limited Use requirements.</p>

<h2>How it is used</h2>
<p>Only to run the service for you: to show you your papers, make your PDFs and Word files, and
keep accounts apart. Your papers, questions and images are private to your account. We do not
sell your data, show adverts, or use your work to train any model.</p>

<h2>Where it is kept, and for how long</h2>
<p>On a server in Singapore rented from DigitalOcean, a US company that stores the data for us
and does not use it. The database is backed up every night to DigitalOcean storage in
Singapore, and each backup is deleted after 14 days. Signing in goes through Google or GitHub,
which handle that step on their own systems, largely in the United States, under their own
privacy policies.</p>
<p>We keep your account and your work for as long as you have an account. When you delete it,
everything is removed from the live database at once, and from the backups as they expire,
within 14 days.</p>

<h2>Your choices</h2>
<ul>
<li><strong>Download your data</strong>: in the app, open the account menu (your initials, top
right) and choose <em>Download my data</em> for a zip of your papers, bank questions and
images.</li>
<li><strong>Correct your details</strong>: your name and email come from Google or GitHub;
change them there and they update the next time you sign in, or write to us.</li>
<li><strong>Delete your account</strong>: choose <em>Delete my account…</em> in the same menu.
It removes your account, papers, folders, bank, images, settings, export records and sign-in
links at once. This is also how you withdraw your consent to us keeping your data.</li>
</ul>

<h2>Contact</h2>
<p>Questions or requests about your data, for the data protection officer: {contact}</p>

<h2>Changes</h2>
<p>If this notice changes, the date at the top changes too. A change that affects what we keep
or how it is used will also be announced in the app.</p>
"""

TERMS = """
<p>These terms apply when you use {app}. By signing in you agree to them.</p>

<h2>The service</h2>
<p>{app} is free. It generates maths questions with worked answers, lets you write your own,
and exports papers as PDF and Word files. Each account may make 30 exports in any 24 hours
and 5 a minute (the limits may change), so that one account cannot slow the service for
everyone.</p>

<h2>Your content</h2>
<ul>
<li>What you write and upload stays yours, and private to your account.</li>
<li>Only upload material you have the right to use. Past-paper questions you add are for your
own internal practice use; do not use the service to publish or share them.</li>
<li>Check a paper before you hand it out. Generated answers are worked by the program and
tested, but you are responsible for the papers you use with students.</li>
</ul>

<h2>Fair use</h2>
<p>Do not try to break, overload or get around the limits of the service, or reach other
people's accounts. We may suspend an account that does.</p>

<h2>No warranty</h2>
<p>The service is provided as it is, without any warranty. It may be unavailable at times, and
it may change. We may stop it, and will give notice in the app first, with time to download
your data. To the extent the law allows, we are not liable for any loss from using it.</p>

<h2>Law</h2>
<p>These terms are governed by the laws of Singapore.</p>

<h2>Contact</h2>
<p>{contact}</p>
"""


@router.get("/privacy", response_class=HTMLResponse)
def privacy() -> HTMLResponse:
    return _page("Privacy notice", PRIVACY.format(app=APP_NAME, contact=contact_html()))


@router.get("/terms", response_class=HTMLResponse)
def terms() -> HTMLResponse:
    return _page("Terms of use", TERMS.format(app=APP_NAME, contact=contact_html()))
