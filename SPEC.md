# SPEC – ĪresPalīgs (working name)

A simple web app for Latvian private landlords who rent out 1–10 flats.
It keeps leases, rent, utility meter readings and monthly statements in one place,
and reminds the landlord about the dates that matter.

> Items marked **TODO: verify** concern law, taxes or government rules.
> They are collected in [VERIFY.md](VERIFY.md) and must be checked before launch.

---

## 1. Target user persona

**Ilze, 46, Riga.** Works full-time (office job). Inherited her parents' 2-room flat in
Imanta and bought a small studio in Āgenskalns as an investment. Both are rented out
on 12-month leases.

- **Today:** a Google Sheet for rent, photos of meter readings on WhatsApp, a calculator
  for the monthly utility bill, sticky notes for lease end dates.
- **Pains:**
  - Every month she spends ~1 hour per flat collecting readings, calculating utilities and
    writing the tenant a message with the total.
  - She once noticed a missed rent payment 3 weeks late.
  - In spring she has to dig through her bank statement to add up the year's rental income
    for the tax declaration.
  - She worries about missing legal deadlines (VID notification, lease renewal,
    land register) but doesn't know them by heart.
- **Tech level:** comfortable with internet banking and latvija.gov.lv; not technical.
- **Language:** Latvian first. (Secondary persona: Russian-speaking landlord, same pains →
  Russian UI is a v1.1 candidate.)
- **Will pay:** a few euros a month if it clearly saves her time every month.

**Not our user (for now):** property management companies, landlords with 20+ units,
short-term (Airbnb) rentals, commercial premises.

---

## 2. Top 5 user stories

1. **Set up a property and lease**
   As a landlord, I add a flat, my tenant (name, email, phone) and the lease
   (start/end date, monthly rent, deposit, rent due day) so everything is in one place.
   *Done when:* the dashboard shows the flat, tenant, rent and days until the lease ends.

2. **Monthly utility statement from meter readings**
   As a landlord, I enter this month's meter readings (cold/hot water, electricity, heat,
   or a fixed amount) and my tariffs, and the app calculates the consumption and the
   total due, then produces a statement (PDF + email to the tenant) in Latvian.
   *Done when:* the statement shows previous/current reading, consumption, tariff, amount,
   rent and the grand total, in `1 234,56 €` format and dates as `dd.mm.yyyy`.

3. **Track payments and spot late rent**
   As a landlord, I mark a statement as paid (full or partial), and I can see at a glance
   who is late and by how much.
   *Done when:* overdue statements are highlighted on the dashboard and in a reminder email.

4. **Reminders for important dates**
   As a landlord, I get email reminders: meter reading day, rent overdue, lease ending in
   60/30 days, and legal deadlines tied to my lease (e.g. VID notification after signing
   a new lease – **TODO: verify** rule and deadline).
   *Done when:* reminders arrive on the right day and can be turned off per type.

5. **Year-end income summary**
   As a landlord, I download a summary of rent and other income received per property for
   a calendar year (CSV + PDF), so I can fill in my tax declaration (EDS) quickly.
   *Done when:* the totals match the payments recorded. The app **does not calculate tax**;
   it only shows a clear note about the regimes with a link to VID (**TODO: verify** text).

---

## 3. MVP scope

### IN
- Sign-up / login with email + password, plus magic-link login (Smart-ID-ready design).
- Properties, tenants, leases (one active lease per property).
- Meters per property, tariffs, monthly readings, utility calculation.
- Monthly statements: generate, PDF, email to tenant, mark paid / partly paid.
- Dashboard: properties, outstanding amounts, overdue, leases ending soon.
- Email reminders (daily scheduled job).
- Year-end income summary export (CSV, PDF).
- Subscription billing with Stripe (free tier + paid plan), prices shown incl. 21% PVN.
- UI in Latvian (primary) and English; all text through i18n.
- GDPR: privacy policy, cookie consent (only essential cookies at launch), export all my
  data (JSON/CSV), delete my account and all data.
- Simple admin (Django admin) for support.
- Landing page with pricing.

### Explicitly OUT (for MVP)
- **Personas kods** – we never store it (not for landlord, not for tenant).
- Uploading lease contracts or other documents (they usually contain personas kods and
  other sensitive data → storage/security burden).
- Tenant accounts / tenant portal. *(v1.1 candidate: tenant submits meter readings via a
  no-login link.)*
- Automatic bank statement import, open banking, or online rent collection.
- Calculating or filing taxes; submitting anything to VID or the land register.
- Lease contract generation / legal templates.
- Smart-ID / eParaksts login (design for it, don't build it).
- Baltic bank-link payments (Montonio, Paysera) – Stripe only for now.
- Russian UI (structure ready, translations later).
- Mobile apps (the web app must work well on a phone).
- Multiple users per account, accountants' access, agencies.
- Short-term rentals, commercial leases.

---

## 4. Pricing model

Simple, two tiers. All prices **include 21% PVN** (**TODO: verify** whether we must charge
PVN from day one – depends on our company's PVN registration status and threshold).

| Plan     | Price (incl. PVN) | Net (excl. PVN) | Limits                          |
|----------|-------------------|-----------------|---------------------------------|
| Bezmaksas (Free) | 0 €        | 0 €             | 1 property, no PDF/email statements, no reminders |
| Standarta | **4,99 €/mēn.**  | 4,12 €          | up to 5 properties, everything included |
| Standarta (gada) | **49,90 €/gadā** | 41,24 € | same, 2 months free             |

- 14-day free trial of Standarta, no card required.
- 6–10 properties: a "Plus" tier (9,99 €/mēn.) only if users ask for it.
- Billing via Stripe Checkout + Stripe Customer Portal (cancel anytime).
- Later: a Baltic bank-link provider (Montonio / Paysera) as an alternative payment method,
  since many Latvians prefer paying by bank link over card.
- **TODO: verify** consumer rules for online subscriptions (14-day right of withdrawal for
  digital services, what must be shown before purchase).

---

## 5. Success metric (first 3 months after launch)

**North-star:** **30 paying landlords** by the end of month 3.

Supporting signals (to understand *why* if we miss it):
- **Activation:** ≥ 50 % of sign-ups create their first monthly statement within 7 days.
- **Retention:** ≥ 60 % of activated users create a statement again the following month.
- **Conversion:** ≥ 15 % of trial users become paying.
- **Qualitative:** 10 user interviews; at least 5 say "I'd be upset if this disappeared".

If activation is fine but retention is low → the monthly statement flow is not saving
enough time; fix that before anything else.

---

## 6. Competitors (checked 31.10.2026, light research)

- **Landlordy** – made in Riga (E-protect SIA); mobile app for tracking leases, rent,
  expenses and invoices. English-first, aimed at a global market. **TODO: verify** current
  pricing, Latvian language support, meter/utility features.
- **Rendin** (Estonia) – rental agreement + rent guarantee platform, not day-to-day
  management. **TODO: verify** whether it operates in Latvia.
- **Bidrento** (Estonia) – property management software, aimed more at professional
  managers. **TODO: verify.**
- **Excel / Google Sheets** – the real main competitor.

**Our angle:** Latvian-first, built around the Latvian monthly routine (meter readings →
utilities → statement), Latvian legal-date reminders, and a cheap monthly price.
