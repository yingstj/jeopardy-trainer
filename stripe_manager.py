import os
import stripe
import requests


def _get_stripe_credentials():
    hostname = os.environ.get("REPLIT_CONNECTORS_HOSTNAME", "connectors.replit.com")
    repl_identity = os.environ.get("REPL_IDENTITY")
    web_repl_renewal = os.environ.get("WEB_REPL_RENEWAL")

    if repl_identity:
        token = f"repl {repl_identity}"
    elif web_repl_renewal:
        token = f"depl {web_repl_renewal}"
    else:
        raise RuntimeError("No Replit identity token found")

    is_production = os.environ.get("REPLIT_DEPLOYMENT") == "1"
    env = "production" if is_production else "development"

    url = (
        f"https://{hostname}/api/v2/connection"
        f"?include_secrets=true&connector_names=stripe&environment={env}"
    )
    resp = requests.get(url, headers={
        "Accept": "application/json",
        "X-Replit-Token": token,
    }, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    item = (data.get("items") or [None])[0]
    if not item or not item.get("settings"):
        raise RuntimeError(f"Stripe {env} connection not found")

    settings = item["settings"]
    return settings.get("publishable", ""), settings.get("secret", "")


_cached_keys = None


def get_stripe_keys():
    global _cached_keys
    if _cached_keys is None:
        _cached_keys = _get_stripe_credentials()
    return _cached_keys


def get_stripe_client():
    _, secret = get_stripe_keys()
    stripe.api_key = secret
    return stripe


MONTHLY_PRICE_AMOUNT = 400
ANNUAL_PRICE_AMOUNT = 2500
MONTHLY_LABEL = "$4 / month"
ANNUAL_LABEL = "$25 / year (save 48%)"


def _ensure_product_and_prices():
    s = get_stripe_client()

    products = s.Product.search(query="metadata['app']:'jayopardy'", limit=1)
    if products.data:
        product = products.data[0]
    else:
        product = s.Product.create(
            name="Jayopardy! Premium",
            description="Saved progress, adaptive training, challenge mode, bookmarks, and detailed analytics.",
            metadata={"app": "jayopardy"},
        )

    prices = s.Price.list(product=product.id, active=True, limit=10)
    monthly_price = None
    annual_price = None
    for p in prices.data:
        if p.recurring and p.recurring.interval == "month" and p.unit_amount == MONTHLY_PRICE_AMOUNT:
            monthly_price = p
        if p.recurring and p.recurring.interval == "year" and p.unit_amount == ANNUAL_PRICE_AMOUNT:
            annual_price = p

    if not monthly_price:
        monthly_price = s.Price.create(
            product=product.id,
            unit_amount=MONTHLY_PRICE_AMOUNT,
            currency="usd",
            recurring={"interval": "month"},
        )
    if not annual_price:
        annual_price = s.Price.create(
            product=product.id,
            unit_amount=ANNUAL_PRICE_AMOUNT,
            currency="usd",
            recurring={"interval": "year"},
        )

    return product.id, monthly_price.id, annual_price.id


_product_cache = None


def get_product_and_prices():
    global _product_cache
    if _product_cache is None:
        _product_cache = _ensure_product_and_prices()
    return _product_cache


def create_checkout_session(email: str, price_id: str, success_url: str, cancel_url: str):
    s = get_stripe_client()

    customers = s.Customer.list(email=email, limit=1)
    if customers.data:
        customer = customers.data[0]
    else:
        customer = s.Customer.create(email=email)

    session = s.checkout.Session.create(
        customer=customer.id,
        payment_method_types=["card"],
        line_items=[{"price": price_id, "quantity": 1}],
        mode="subscription",
        success_url=success_url + "?checkout=success&session_id={CHECKOUT_SESSION_ID}",
        cancel_url=cancel_url + "?checkout=cancelled",
        metadata={"app": "jayopardy", "user_email": email},
    )
    return session.url


def check_subscription_status(email: str):
    s = get_stripe_client()

    customers = s.Customer.list(email=email, limit=1)
    if not customers.data:
        return False, None

    customer = customers.data[0]
    subs = s.Subscription.list(customer=customer.id, status="active", limit=1)
    if subs.data:
        sub = subs.data[0]
        return True, {
            "id": sub.id,
            "status": sub.status,
            "current_period_end": sub.current_period_end,
            "plan_interval": sub.items.data[0].price.recurring.interval if sub.items.data else None,
        }

    return False, None


def create_customer_portal_session(email: str, return_url: str):
    s = get_stripe_client()
    customers = s.Customer.list(email=email, limit=1)
    if not customers.data:
        return None
    session = s.billing_portal.Session.create(
        customer=customers.data[0].id,
        return_url=return_url,
    )
    return session.url
