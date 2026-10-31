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
