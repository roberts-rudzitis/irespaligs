# ĪresPalīgs

A simple web app for Latvian landlords: leases, rent, utility meter readings and monthly
statements in one place. Latvian first, English second.

- What we build: [SPEC.md](SPEC.md)
- How it's built: [ARCHITECTURE.md](ARCHITECTURE.md)
- Legal/tax assumptions still to check: [VERIFY.md](VERIFY.md)
- Conventions for working on the code: [CLAUDE.md](CLAUDE.md)

## Run it locally (one command)

You need [Docker Desktop](https://www.docker.com/products/docker-desktop/) running.

```bash
docker compose up --build
```

Open http://localhost:8000. The first start takes a few minutes (it downloads Python and
PostgreSQL images). Stop with `Ctrl+C`.

No `.env` file is needed for local development. To override settings, copy `.env.example`
to `.env`.

**Emails in development** (sign-up confirmation, login codes) are not sent. They are printed
in the terminal where `docker compose up` runs. Look for the confirmation link or the code there.

## Common tasks

| What | Command |
|---|---|
| Create demo data (login `demo@example.lv` / `demo-parole-2026`) | `docker compose run --rm web python manage.py seed_demo` |
| Send today's reminder emails (runs daily in production) | `docker compose run --rm web python manage.py send_reminders` (add `--date 01.12.2026` to test another day) |
| Run tests | `docker compose run --rm web pytest` |
| Create an admin user (for /admin/) | `docker compose run --rm web python manage.py createsuperuser` |
| After changing a model | `docker compose run --rm web python manage.py makemigrations` |
| After adding/changing text | `docker compose run --rm web python manage.py makemessages -l lv -l en --ignore=staticfiles`, translate in `locale/lv/LC_MESSAGES/django.po`, then `docker compose run --rm web python manage.py compilemessages --ignore=staticfiles` |
| Admin panel / metrics | http://localhost:8000/admin/ and http://localhost:8000/admin/metrics/ (staff user needed) |
| Open a database shell (SQL) | `docker compose exec db psql -U irespaligs` |
| Start from an empty database | `docker compose down -v` (⚠️ deletes all local data) |

## Project layout

```
irespaligs/     settings, URLs, Latvian date/number formats
apps/core/      language selection, money formatting (|eur filter)
apps/accounts/  User model (email login, no username, no personas kods)
apps/pages/     home page, dashboard
templates/      HTML templates (base layout, allauth overrides)
locale/         translations (lv, en)
tests/          pytest tests
```

## Payments (Stripe)

Without Stripe keys the app works normally; the "Subscription" page just says payments are
not configured. New accounts get a 14-day trial of the paid plan without a card.

To try real checkout in **test mode** (no real money):

1. Create a free Stripe account and stay in **Test mode**.
2. Create a product "ĪresPalīgs Standarta" with two recurring prices: **4,99 EUR / month** and
   **49,90 EUR / year**, both with tax behaviour **"inclusive"** (price includes PVN).
3. Put the keys in `.env`: `STRIPE_SECRET_KEY` (sk_test_…), `STRIPE_PRICE_MONTHLY` and
   `STRIPE_PRICE_YEARLY` (price_…).
4. Forward webhooks to your computer with the [Stripe CLI](https://docs.stripe.com/stripe-cli):
   `stripe listen --forward-to localhost:8000/stripe/webhook/` and put the `whsec_…` it prints
   into `STRIPE_WEBHOOK_SECRET`.
5. Restart (`docker compose up`), open "Abonements", pay with test card `4242 4242 4242 4242`.

In production, add the webhook endpoint `https://<your-domain>/stripe/webhook/` in the Stripe
dashboard with the events `checkout.session.completed` and `customer.subscription.*`.
Plan limits live in `apps/subscriptions/plans.py`.

## Deploying (Render, Frankfurt)

`render.yaml` describes the web app, a PostgreSQL 17 database and the daily reminder job, all in
the Frankfurt region (EU). Field names were checked against Render's Blueprint docs (31.10.2026).

1. **Put the code on GitHub (private).** Create an empty *private* repository on github.com
   (e.g. `irespaligs`, no README), then in this folder:
   `git remote add origin https://github.com/<your-user>/irespaligs.git` and `git push -u origin main`.
2. **Render:** New → Blueprint → pick the repository. Render asks for every value marked
   `sync: false` (allowed hosts, admin path, email and Stripe keys).
3. **Email:** create a Brevo account, add your sending domain with SPF/DKIM records (otherwise
   notices land in spam), and put the SMTP login into `EMAIL_HOST_USER` / `EMAIL_HOST_PASSWORD`.
4. **Domain:** point your domain to the Render web service; set `DJANGO_ALLOWED_HOSTS` and
   `DJANGO_CSRF_TRUSTED_ORIGINS` accordingly.
5. **Stripe:** create the webhook endpoint `https://<your-domain>/stripe/webhook/` (see "Payments").
6. **Admin user:** Render dashboard → web service → Shell → `python manage.py createsuperuser`.
7. **Check the cron job's first run time** (the timezone is assumed to be UTC).

Before real users: see the open items in [VERIFY.md](VERIFY.md) and replace the `[PLACEHOLDERS]`
in `templates/pages/legal/`.
