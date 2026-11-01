# Contributing – project conventions

Read [SPEC.md](SPEC.md) (what we build), [ARCHITECTURE.md](ARCHITECTURE.md) (how) and
[VERIFY.md](VERIFY.md) (open legal and tax items) first. Work in small vertical slices.

## Commands (everything runs through Docker)

| What | Command |
|---|---|
| Start | `docker compose up` → http://localhost:8000 |
| Tests | `docker compose run --rm web pytest` |
| Migrations | `docker compose run --rm web python manage.py makemigrations` / `migrate` |
| Translations | `docker compose run --rm web python manage.py makemessages -l lv -l en -l ru --ignore=staticfiles`, then `compilemessages --ignore=staticfiles` |
| Admin user | `docker compose run --rm web python manage.py createsuperuser` |
| Demo data | `docker compose run --rm web python manage.py seed_demo` |

## Definition of done for every change

1. The app runs (`docker compose up`, no errors).
2. `pytest` passes; new flows have tests.
3. New strings are translated in `locale/lv`, `locale/en` and `locale/ru`.
4. One commit with a clear message (`feat: ...`, `fix: ...`, `test: ...`, `docs: ...`).

## Code rules

- **Django 5.2 LTS, Python 3.12, PostgreSQL.** Server-rendered templates; no JavaScript framework, no npm.
- Business logic in `apps/<app>/services.py` as plain functions; views stay thin.
- **Money is `Decimal`, never float.** Database: `DecimalField(max_digits=12, decimal_places=2)`.
  Round with `ROUND_HALF_UP` per line.
- **Owner scoping:** every query for user data uses `Model.objects.for_owner(request.user)` or the
  owner mixin. Never `Model.objects.get(pk=...)` on user data in a view.
- **i18n:** no hard-coded user-facing text in Python or templates. Use `gettext_lazy as _` and
  `{% translate %}` / `{% blocktranslate %}`. Latvian is the default language.
- **Formats:** dates `dd.mm.yyyy`, decimal comma, money via the `|eur` filter (`1 234,56 €`).
- Short comments only where the logic isn't obvious. Readable names over clever code.
- Pin dependency versions in `requirements.txt` / `requirements-dev.txt`.

## Hard rules

- **Never store personal identity codes** (personas kods) or ID document numbers.
- **Never commit secrets.** Configuration comes from environment variables; keep `.env.example` current.
- **Law, tax and government data:** don't rely on memory. Mark code with `TODO: verify` and add an entry
  to VERIFY.md with its ID (e.g. V2), source and date.
- The app **does not calculate taxes** and submits nothing to VID or the Land Register.
- Hosting, databases, email and backups stay in the **EU**.
- No new third-party service without updating the sub-processor list on the privacy page.
- Tests never call Stripe or send real emails.

## Practical notes

- After `docker compose build`, run `docker compose up -d` – a plain restart keeps the old image.
- Long legal texts (privacy policy, terms) are per-language templates in
  `templates/pages/legal/<name>_<lang>.html`, not .po strings. Keep lv, en and ru in sync (Latvian prevails).
- After `makemessages`, check each .po header still says `Language: lv/en/ru`.
- In .po files a `%` needs care (`10 percent` in msgids, `%%` in `blocktranslate`). Latvian has 3 plural
  forms, Russian 4. Entries marked `#, fuzzy` are ignored by gettext – review them and remove the flag.
- Windows: keep migration names short (path length limit); line endings are LF (`.gitattributes`).
- Russian translations should be reviewed by a native speaker before launch.

## Extension points

- Smart-ID / eParaksts login → an allauth OpenID Connect provider (ARCHITECTURE §5). Such logins
  usually return the personal identity code – store only the provider's user ID.
- Baltic bank-link payments (Montonio, Paysera) → `apps/subscriptions/providers/` (ARCHITECTURE §6).
