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
| Run tests | `docker compose run --rm web pytest` |
| Create an admin user (for /admin/) | `docker compose run --rm web python manage.py createsuperuser` |
| After changing a model | `docker compose run --rm web python manage.py makemigrations` |
| After adding/changing text | `docker compose run --rm web python manage.py makemessages -l lv -l en --ignore=staticfiles`, translate in `locale/lv/LC_MESSAGES/django.po`, then `docker compose run --rm web python manage.py compilemessages --ignore=staticfiles` |
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
