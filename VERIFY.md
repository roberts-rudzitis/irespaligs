# VERIFY – assumptions about law, tax and government rules

Rules change. Nothing here is legal or tax advice. Every item must be checked against an
official source (likumi.lv, vid.gov.lv, zemesgramata.lv, dvi.gov.lv) or a Latvian
tax adviser / lawyer before launch. Tick the box and add the source + date when verified.

Status legend: ☐ open · ☑ verified · ✎ verified but changed our design

## Taxes (VID)

- ☐ **V1 – 10 % IIN on rental income.** Individuals renting out property can choose a flat
  10 % personal income tax on rental income instead of progressive rates; with the 10 %
  regime expenses can't be deducted.
  *Seen in:* KPMG tax card, lvportals.lv (2019, 2025). *Used in:* SPEC §2 story 5 (info note only).
- ☐ **V2 – VID notification within 5 working days** of signing a lease, to use the 10 %
  regime. *Seen in:* lvportals.lv e-konsultācija (2025), not yet on vid.gov.lv.
  *Used in:* SPEC §2 story 4 (reminder after a new lease).
- ☐ **V3 – Payment and declaration deadlines** for rental income tax (monthly/quarterly
  payment? annual declaration period in EDS?). *Used in:* reminders, year-end summary.
- ☐ **V4 – Non-residents** renting out a Latvian flat: same rules or different?
- ☐ **V5 – Statements issued by a private landlord**: any mandatory content (e.g. is it a
  "rēķins" with required fields, or just a payment notice)? *Used in:* statement PDF wording.

## Rental law (Dzīvojamo telpu īres likums, in force since 01.05.2021)

- ☐ **L1 – Land register (zemesgrāmata) registration** of a lease makes it binding on a new
  owner; registration is free. *Seen in:* lvportals.lv (2021, 2023).
- ☐ **L2 – Transition deadline 31.12.2026**: unregistered leases signed before 30.04.2021
  stay binding on a new owner only until 31.12.2026 (or the lease end, if earlier).
  *Seen in:* lvportals.lv e-konsultācija (2025). Possible one-time reminder feature.
- ☐ **L3 – Leases must be fixed-term** (no open-ended leases). *Used in:* lease form
  (end date required).
- ☐ **L4 – Deposit (drošības nauda) limits**, if any. *Used in:* lease form validation (no
  validation planned until verified).
- ☐ **L5 – Rules for passing utility costs on to tenants** (meter-based, heating split,
  who pays the building manager). The app only does arithmetic with the landlord's own
  tariffs – confirm this is not misleading.

## Our own company / billing

- ☐ **B1 – PVN registration threshold** for our company and whether we must charge 21 % PVN
  from the first customer. *Used in:* SPEC §4 pricing.
- ☐ **B2 – Selling to consumers in other EU countries** (OSS VAT rules) – relevant only if
  non-Latvian residents sign up. Check whether Stripe Tax is needed.
- ☐ **B3 – Consumer rights for digital subscriptions** (14-day withdrawal, pre-contract
  information, cancellation). *Used in:* checkout page, terms.
- ☐ **B4 – Price display rules**: showing prices incl. PVN to consumers.

## GDPR / data protection

- ☐ **G1 – Roles**: the landlord is the *controller* of tenant data; we are the *processor*
  → we need a Data Processing Agreement (DPA) in our terms. Confirm with a lawyer / DVI guidance.
- ☐ **G2 – Legal basis and retention** for tenant names/emails/phones and payment records
  (how long may we keep them after a lease ends? accounting retention periods?).
- ☐ **G3 – Cookie consent**: if we use only strictly necessary cookies, is a banner still
  needed, or just an information notice?
- ☐ **G4 – Sending statement emails to tenants** on the landlord's behalf – any consent or
  information duty towards the tenant?

- ☐ **G5 – Hosting with a US-owned provider in an EU region** (Render Frankfurt, Stripe,
  Sentry): data stays in the EU, but check whether SCCs / EU-US Data Privacy Framework
  coverage is enough, or whether an EU-owned host (Scaleway, Hetzner) is preferable.
  *Used in:* ARCHITECTURE §1, §9.

## Authentication (later)

- ☐ **A1 – Smart-ID / eParaksts login providers** for Latvia: which brokers offer OpenID
  Connect, their prices, and what personal data (personas kods) they return.
  *Used in:* ARCHITECTURE §5.

## Market (not legal, but unverified)

- ☐ **M1 – Landlordy** (Riga, E-protect SIA): current pricing, Latvian UI, utility features.
- ☐ **M2 – Rendin** (EE): active in Latvia?
- ☐ **M3 – Bidrento** (EE): target segment and price.
