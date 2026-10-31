# ARCHITECTURE – ĪresPalīgs

Goal: the simplest setup that one person who knows Python and basic SQL can understand,
run and fix. Boring, well-documented tools only.

---

## 1. Stack (and why)

| Part | Choice | Why (plain language) |
|---|---|---|
| Language | **Python 3.12** | You already know it. |
| Web framework | **Django 5.2 LTS** | "Batteries included": login, admin panel, forms, database migrations, translations and security are built in. LTS = security fixes until April 2028. FastAPI would make us build all of that ourselves. |
| Database | **PostgreSQL 17** | Standard, reliable, you can query it with the SQL you know. |
| Frontend | **Django templates + HTMX + Pico.css** | Pages are rendered on the server (normal HTML). HTMX adds small interactive bits (e.g. "mark as paid" without reloading) with HTML attributes instead of JavaScript code. Pico.css gives a clean look with no build step. No React, no npm. |
| Login | **django-allauth** | The most used Django auth library: email + password, email login codes (our "magic link"), email verification, rate limiting. Can add OpenID Connect providers later → Smart-ID / eParaksts. |
| Payments | **Stripe** (official `stripe` Python library) | Checkout page + Customer Portal hosted by Stripe → we never touch card data. |
| PDF | **WeasyPrint** | Turns an HTML template into a PDF, so the statement PDF is just another template. |
| Email | **Brevo** (EU company, France) via SMTP | EU-based transactional email; plain SMTP means we can switch provider by changing env vars. |
| Background jobs | **None** – one daily `manage.py send_reminders` command run by the host's cron | Avoids Celery/Redis (extra moving parts). Fine for hundreds of users. |
| Static files | **WhiteNoise** | Django serves its own CSS/JS; no separate file server or S3. |
| Tests | **pytest + pytest-django** | You asked for pytest; plain functions and `assert`. |
| Local dev | **Docker Compose** (web + db) | One command: `docker compose up`. Same on Windows/Mac/Linux. |
| Hosting | **Render, Frankfurt region** (web service + managed PostgreSQL + cron job) | Managed: no server to patch, automatic HTTPS, daily DB backups, deploy on `git push`. Data stays in the EU (Germany). |

**Hosting alternative if you want an EU-owned company** (no US parent): **Scaleway** (France)
or **Hetzner** (Germany) – cheaper, but you manage more yourself. Because the app runs in a
standard Docker image, moving later is easy. → see VERIFY.md **G5**.

**What we deliberately don't use:** Celery/Redis, a JavaScript framework, microservices,
Kubernetes, file storage (S3). Each can be added later if a real need appears.

---

## 2. Main modules (Django apps)

```
irespaligs/            project settings, urls
apps/
  accounts/            custom User model, profile, language choice, allauth templates
  rentals/             Property, Tenant, Lease, Meter, Tariff, FixedCharge, MeterReading
  statements/          Statement, StatementLine, Payment, PDF + email, year summary export
  reminders/           reminder rules + ReminderLog, the daily `send_reminders` command
  subscriptions/       Stripe checkout, portal, webhook, plan limits
  privacy/             privacy policy, cookie notice, data export, account deletion
  pages/               landing page, pricing, terms
  core/                shared helpers: money/date formatting, owner-scoping mixin
locale/                lv/ en/ (ru/ later) translation files
templates/             base layout + shared partials
tests/                 pytest tests, one file per flow
```

**Rule:** business logic (calculations) lives in plain functions in `services.py` inside
each app, not in views. They are easy to test and easy to read.
Example: `statements/services.py::build_statement(lease, period)`.

---

## 3. Data model

All tables have `id`, `created_at`, `updated_at`. All money is `NUMERIC(12,2)` (Python
`Decimal`, **never float** – floats give rounding errors like 0.1 + 0.2 = 0.30000000000000004).

```
User ─┬─< Property ─┬─< Meter ───< MeterReading
      │             ├─< FixedCharge
      │             └─< Lease >── Tenant
      │                   └─< Statement ─┬─< StatementLine
      │                                  └─< Payment
      ├─< Tenant
      ├── Subscription (1:1)
      └─< ReminderLog
```

| Table | Key fields | Notes |
|---|---|---|
| **User** | email (login), full_name, language (`lv`/`en`), payment_details (landlord's own IBAN text, printed on notices) | Custom model from day one (Django best practice). **No personas kods.** |
| **Subscription** | user, plan (`free`/`standard`), status, stripe_customer_id, stripe_subscription_id, current_period_end, trial_ends_at | Updated only by Stripe webhooks. |
| **Property** | owner→User, name ("Imantas dzīvoklis"), address (free text), notes | |
| **Tenant** | owner→User, full_name, email, phone | Minimal data. No personas kods, no ID documents. |
| **Lease** | property, tenant (`RESTRICT`: a tenant with leases can't be deleted alone, but deleting the whole account works), start_date, end_date (required – fixed-term, VERIFY **L3**), monthly_rent, deposit, rent_due_day (1–28), vid_notified_on (optional) | One active lease per property (enforced in code). |
| **Meter** | property, kind (`cold_water`, `hot_water`, `electricity`, `heat`, `gas`, `other`), unit (m³, kWh, MWh), label, price_per_unit `NUMERIC(12,5)`, is_active | No separate tariff history table: statement lines copy the price, so old statements stay correct anyway. |
| **FixedCharge** | property, label ("Apsaimniekošana", "Atkritumi"), amount, is_active | Monthly fixed amounts passed on to the tenant. |
| **MeterReading** | meter, period (first day of month), value `NUMERIC(14,3)` | Unique (meter, period). |
| **Statement** | lease, period, issue_date, due_date, status (`draft`/`sent`/`partly_paid`/`paid`), total, sent_at | |
| **StatementLine** | statement, kind (`rent`/`utility`/`fixed`/`other`), description, prev_reading, curr_reading, quantity, unit_price, amount | **Snapshot**: copies numbers at creation time, so later tariff edits don't change old statements. |
| **Payment** | statement, paid_on, amount, note | Several partial payments allowed. Status is derived from the sum. |
| **ReminderLog** | user, kind, object_id, for_date, sent_at | Unique (user, kind, object_id, for_date) → never send the same reminder twice. |

**Multi-tenant safety (each landlord sees only their data):** every query goes through
`OwnerQuerysetMixin` / `for_owner(user)` helpers in `core/`. A test checks that user A gets
404 on user B's property, lease and statement.

**Deleting an account** deletes the user and (via `ON DELETE CASCADE`) all their properties,
tenants, statements, etc. The Stripe customer is deleted too. Retention of billing records
for our own accounting → VERIFY **G2**.

---

## 4. Key flows

**Monthly statement** (`statements/services.py`):
1. Landlord opens the property → "Jauns rēķins / New statement" for month M.
2. Form shows each active meter with last month's reading pre-filled; landlord enters the new ones.
3. `build_statement()` makes lines: rent + for each meter `(curr − prev) × meter price` + fixed charges. Rounds each line to 2 decimals (`ROUND_HALF_UP`), sums.
4. Saved as `draft` → landlord checks it → "Sūtīt" generates the PDF (WeasyPrint) and emails
   it to the tenant (in the landlord's chosen language) → status `sent`.

**Reminders:** cron runs `python manage.py send_reminders` daily at 07:00 Europe/Riga.
For each rule (reading day, rent overdue, lease ends in 60/30 days, VID notification after a
new lease – VERIFY **V2**) it finds due items, skips ones already in `ReminderLog`, sends
one digest email per landlord.

**Year summary:** a query sums `Payment.amount` by property for a calendar year, split by
line kind (rent vs. utilities passed on) → CSV and PDF. Shows a fixed info note about tax
regimes with a link to VID (text in VERIFY **V1**). **No tax calculation.**

---

## 5. Auth

- django-allauth, email as the only identifier, mandatory email verification.
- Login options: **email + password** or **"Send me a login code"** (one-time code / link by
  email – our magic link).
- Password hashing: **Argon2** (current recommendation). Login rate limiting: allauth built-in.
- Sessions: Django's database sessions, secure + HttpOnly cookies, HTTPS only in production.

**Smart-ID / eParaksts later:** allauth supports generic **OpenID Connect** providers. A
Latvian e-ID broker (e.g. a Smart-ID / eParaksts gateway – VERIFY **A1**) can be added as a new
provider in settings, linked to the existing User by verified email. No change to our tables
except allauth's own `SocialAccount`.
⚠️ **Flag:** these logins usually return the **personas kods**. We would store only the
provider's opaque user ID, not the personas kods – to be decided with you before building it.

---

## 6. Payments

- **Stripe Checkout** for subscribing, **Stripe Customer Portal** for card changes / cancel.
  We store only Stripe IDs and the status; Stripe holds card data.
- Stripe Prices are created with **tax behaviour = inclusive** (4,99 € incl. 21 % PVN).
  Whether we use **Stripe Tax** depends on VERIFY **B1/B2**.
- **Webhook** `/stripe/webhook/` (signature verified) handles:
  `checkout.session.completed`, `customer.subscription.updated`,
  `customer.subscription.deleted`, `invoice.payment_failed`. Handlers are idempotent
  (safe if Stripe sends the same event twice).
- **Plan limits** live in one place: `subscriptions/plans.py` (e.g. free = 1 property).
  Views call `can_add_property(user)` etc.
- **Baltic bank link later (Montonio / Paysera):** all payment-provider code sits behind a
  small interface in `subscriptions/providers/` (`start_checkout()`, `handle_webhook()`).
  Bank links are usually one-off payments, not recurring, so the likely model is
  **"pay 12 months upfront by bank link"** → sets `current_period_end` one year ahead.

---

## 7. i18n and Latvian formats

- `LANGUAGE_CODE = "lv"`, `LANGUAGES = [lv, en]` (ru added later by adding a locale folder).
- Every user-facing string uses `{% translate %}` / `gettext_lazy`. **No hardcoded text.**
- Language choice (`core/middleware.py`): logged-in user's saved language → language cookie
  → Latvian. The browser's language is ignored on purpose so Latvian stays the default.
  No language prefix in URLs (simpler; revisit for SEO of the landing page later).
- Formats are forced for **all** languages via our own format module (`irespaligs/formats/`):
  dates `dd.mm.yyyy`, decimal comma, space as thousands separator.
- Money: template filter `{{ amount|eur }}` → `1 234,56 €`. Price labels say
  "ar PVN 21 %" / "incl. 21% VAT" where relevant.
- Time zone `Europe/Riga`, stored in UTC.

---

## 8. GDPR

- **Data minimisation:** landlord = email + name; tenant = name + email + phone (phone
  optional). No personas kods, no documents, no bank account numbers of tenants.
- **Cookies:** only strictly necessary (session, CSRF, language, consent). No analytics at
  launch → a simple notice + "Accept" (VERIFY **G3**). If analytics are added later, use an EU
  cookieless tool or add real opt-in.
- **Privacy policy page** (lv/en), **Terms** with a DPA section (we are the landlord's
  processor for tenant data – VERIFY **G1**).
- **Export my data:** one ZIP with JSON + CSV of everything the user owns.
- **Delete my account:** confirm by password or login code → hard delete + Stripe customer
  delete → confirmation email.
- **Sub-processors list** on the privacy page: Render (hosting, Frankfurt), Stripe
  (payments), Brevo (email).

---

## 9. Deployment

```
GitHub repo ──push to main──> Render (Frankfurt)
                                ├─ Web service: Docker image, gunicorn, runs migrations on deploy
                                ├─ PostgreSQL (managed, daily backups)
                                └─ Cron job: `python manage.py send_reminders` 07:00 Riga
```

- **Config via environment variables only** (12-factor). `.env` locally (never committed),
  Render's dashboard in production. `.env.example` lists every variable.
- `DEBUG=False`, `SECURE_*` settings, HSTS, `ALLOWED_HOSTS` from env.
- **Error tracking:** Sentry with EU data region (optional, free tier).
- **Backups:** Render's daily backups + a monthly manual `pg_dump` you keep yourself.
- **Estimated cost at launch:** roughly €15–30/month (web + DB + cron). TODO: verify current prices.

---

## 10. Testing

- `pytest` in Docker: `docker compose run --rm web pytest`.
- Every core flow has tests: sign-up/login, property/lease CRUD, owner isolation,
  utility calculation (unit tests with tricky decimals), statement PDF renders, payments →
  status, reminders don't duplicate, Stripe webhook (with a fake signed payload),
  data export contains everything, account deletion removes everything, i18n (page renders
  in lv and en, no missing translations in key pages).
- Stripe and email are never called for real in tests (Django's in-memory email backend,
  mocked Stripe client).
