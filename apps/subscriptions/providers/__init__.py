"""Payment providers.

Each provider module offers the same three functions:

    start_checkout(user, interval, success_url, cancel_url) -> URL to send the user to
    manage_url(user, return_url) -> URL where the user can change card / cancel
    handle_webhook(payload: bytes, headers) -> None   (updates Subscription rows)

Today only Stripe (card subscriptions). A Baltic bank-link provider (Montonio, Paysera) would be a
new module here. Bank links are usually one-off payments, so the likely model is "pay 12 months
upfront": its handle_webhook would set status=active and current_period_end one year ahead.
"""
