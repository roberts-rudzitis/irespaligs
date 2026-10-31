"""Dates from Latvian rental law used by the app.

Dzīvojamo telpu īres likums (in force since 01.05.2021), transitional provisions 2–3, checked on likumi.lv
31.10.2026 (VERIFY.md L2): a lease concluded before 01.05.2021 and not registered in the Land Register
binds a new owner of the dwelling only until 31.12.2026 (or until the lease ends, if earlier).
"""

from datetime import date

OLD_LAW_CUTOFF = date(2021, 5, 1)  # leases signed before this date
OLD_LEASE_TRANSITION_END = date(2026, 12, 31)


def needs_land_register_warning(lease, today):
    """True for a running, unregistered lease signed before 01.05.2021, while the transition period lasts."""
    return (
        not lease.registered_in_land_register
        and lease.signing_date() < OLD_LAW_CUTOFF
        and lease.end_date >= today
        and today <= OLD_LEASE_TRANSITION_END
    )
