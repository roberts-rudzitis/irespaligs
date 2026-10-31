# VERIFY – assumptions about law, tax and government rules

Rules change. Nothing here is legal or tax advice. Items are checked against official sources
(likumi.lv, vid.gov.lv, dvi.gov.lv, ptac.gov.lv) where possible; anything that needs a judgement
call stays open for a Latvian lawyer / tax adviser. Re-check verified items at least once a year.

Status legend: ☐ open · ◐ partly checked (needs an expert) · ☑ verified · ✎ verified and it changed our design

Main sources (checked 31.10.2026):
- **[VID-M]** VID methodology "Nodokļi no dzīvokļa izīrēšanas vai iznomāšanas ienākumiem", updated
  27.10.2026 – https://www.vid.gov.lv/lv/media/32522/download
- **[DTIL]** Dzīvojamo telpu īres likums, version in force from 01.07.2026 – https://likumi.lv/ta/id/322216
- **[MK255]** MK noteikumi Nr. 255 "Noteikumi par distances līgumu" – https://likumi.lv/ta/id/266462
- **[ISPL]** Informācijas sabiedrības pakalpojumu likums, Art. 7.1 – https://likumi.lv/ta/id/96619

## Taxes (VID)

- ☑ **V1 – 10 % IIN on rental income.** A private person may choose not to register a business and pay
  10 % IIN on rental income; no expenses can be deducted except real estate tax on that property.
  *Source:* [VID-M] §3 "Paziņotā saimnieciskā darbība". *Used in:* year summary note.
- ✎ **V2 – VID notification within 5 working days of *signing* the lease**, via EDS (registration form +
  copy of the lease). *Source:* [VID-M] §1 and §3. *Changed:* added `Lease.signed_on`; the reminder now
  counts from the signing date and states the rule (only for landlords on this regime).
- ☑ **V3 – Payment and declaration.** Under the 10 % regime the landlord pays the tax with the annual
  income declaration, appendix D11, from 1 March to 1 June (or 1 July) of the following year. If the
  tenant is a company/registered business, it withholds the tax instead. *Source:* [VID-M] p. 18–19.
  *Used in:* year summary note.
- ◐ **V4 – Non-residents** renting out a Latvian flat: [VID-M] mentions non-residents only in the PVN
  context. Not covered by the app; ask a tax adviser if non-resident landlords become a target group.
- ☑ **V5 – Payment notices from a private landlord:** no mandatory form found. [DTIL] sets no invoice
  rules (the lease must list services, costs and payment terms, Art. 8(1)(4)). [VID-M] §3: if rent is
  received in cash, the landlord keeps an income register (entry no., date, document no./date, payer,
  description, amount); not needed if all income is cashless. *Changed:* the year summary CSV now has
  these columns, so it can serve as that register.
- ✎ **V6 – What counts as income (10 % regime).** Utility and management payments the tenant pays
  **through the landlord** are taxable income; payments the tenant makes **directly** to providers are
  not. A received **deposit** is also income. *Source:* [VID-M] §3. *Changed:* year summary note now
  says this. Idea for later: record deposit receipts in the app.

## Rental law (Dzīvojamo telpu īres likums)

- ☑ **L1 – Land register:** leases may be registered (Art. 35); an unregistered lease does not bind a
  new owner (Art. 28). *Source:* [DTIL].
- ✎ **L2 – Leases signed before 01.05.2021:** bind a new owner only until **31.12.2026** (or the lease
  end, if earlier); if the parties can't agree on registration, a court claim is possible until
  31.12.2026 (transitional provisions 2–3). *Source:* [DTIL]. *Changed:* `Lease.registered_in_land_register`;
  dashboard warning + one-time reminder for unregistered leases signed before 01.05.2021 (`apps/rentals/rules.py`).
- ☑ **L3 – Leases are fixed-term** (Art. 9). *Source:* [DTIL]. *Used in:* end date is required.
- ✎ **L4 – Deposit max. two months' rent** (Art. 12(1)); unused part returned by the day the dwelling is
  vacated unless the lease says otherwise (Art. 12(4)). *Changed:* lease form rejects a larger deposit.
- ☑ **L5 – Utilities:** may be included in rent only if agreed in writing (Art. 10(2)); the lease sets
  how they are paid (Art. 11); landlord may terminate if they are >2 months overdue (Art. 24(1)(2)).
  The app only does arithmetic with the landlord's own tariffs – consistent with this.

## Our own company / billing

- ◐ **B1 – PVN registration.** Threshold is **50 000 EUR per calendar year** (since 2025; above 55 000 EUR
  register within 1 working day). Below it, registration is voluntary. *Sources:* VID / lvportals.lv
  articles (2025). *Open (adviser):* whether to register voluntarily from day one. If **not** registered,
  we must not charge PVN – then prices should say "PVN nav piemērots" instead of "incl. 21 % PVN".
  Prices in `apps/subscriptions/plans.py` and the landing/billing pages must match the decision.
- ◐ **B2 – Customers in other EU countries.** Up to 10 000 EUR/year EU-wide B2C sales of electronic
  services → Latvian VAT rules; above → customer's country rate via OSS (requires Latvian VAT
  registration). *Sources:* EU OSS rules (secondary sources). Not relevant while customers are in Latvia.
- ◐ **B3 – Right of withdrawal (14 days) for subscriptions.** [MK255] allows starting the service during
  the withdrawal period only with the consumer's **express request on a durable medium** and
  confirmation about losing the right once the service is fully performed (point 14, amended 2022).
  *Open (lawyer):* exact checkout wording and a pro-rata refund rule; then add a consent checkbox before
  Stripe Checkout and fill the [PLACEHOLDER] in the terms.
- ☐ **B4 – Price display rules** for consumers (total price incl. taxes) – depends on B1.

## GDPR / data protection

- ☐ **G1 – Roles:** landlord = controller of tenant data, we = processor → DPA in our terms (draft section
  exists). Needs a lawyer.
- ☐ **G2 – Retention** of our own billing records (accounting law) and of tenants' data after a lease ends.
- ◐ **G3 – Cookies:** [ISPL] Art. 7.1 – consent is not required for storage strictly necessary to provide
  the service the user requested. We only use session, CSRF, language and notice cookies → an
  information notice should suffice. *Open:* confirm with DVI cookie guidance before adding any
  analytics (then real opt-in consent is needed).
- ☐ **G4 – Emailing tenants on the landlord's behalf** – information duty towards the tenant (Art. 14 GDPR)?
- ☐ **G5 – US-owned providers in EU regions** (Render, Stripe, Sentry): SCCs / EU–US Data Privacy
  Framework vs an EU-owned host (Scaleway, Hetzner).
- ☐ **G6 – Legal texts**: privacy policy and terms in `templates/pages/legal/` are drafts with
  `[PLACEHOLDERS]`. Have a lawyer review, then set `LEGAL_TEXTS_REVIEWED=1`.

## Authentication (later)

- ☐ **A1 – Smart-ID / eParaksts login providers** (OpenID Connect brokers), prices, and what personal
  data (personas kods) they return. *Used in:* ARCHITECTURE §5.

## Market (not legal, but unverified)

- ☐ **M1 – Landlordy** (Riga, E-protect SIA): current pricing, Latvian UI, utility features.
- ☐ **M2 – Rendin** (EE): active in Latvia?
- ☐ **M3 – Bidrento** (EE): target segment and price.
