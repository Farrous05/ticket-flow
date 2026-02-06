#!/usr/bin/env python
"""
Seed script for demo data.
Run: python -m scripts.seed_data

Seeds:
- Help articles (FAQs)
- Customers
- Products
- Orders with items
"""

import random
from datetime import datetime, timedelta

from src.db.client import get_supabase_client


# =============================================================================
# HELP ARTICLES (FAQs)
# =============================================================================

HELP_ARTICLES = [
    {
        "title": "How to Reset Your Password",
        "content": """If you've forgotten your password, follow these steps:

1. Click "Forgot Password" on the login page
2. Enter your email address
3. Check your inbox for a reset link (expires in 24 hours)
4. Click the link and create a new password

Password requirements:
- At least 8 characters
- One uppercase letter
- One number
- One special character

If you don't receive the email within 5 minutes, check your spam folder.""",
        "category": "account",
        "keywords": ["password", "reset", "forgot", "login", "access"]
    },
    {
        "title": "Two-Factor Authentication Setup",
        "content": """To enable 2FA on your account:

1. Go to Settings > Security
2. Click "Enable Two-Factor Authentication"
3. Scan the QR code with Google Authenticator or Authy
4. Enter the 6-digit code to verify
5. Save your backup codes in a safe place

If you lose your phone, use backup codes to regain access.""",
        "category": "account",
        "keywords": ["2fa", "security", "authentication", "google authenticator"]
    },
    {
        "title": "Shipping Times and Tracking",
        "content": """Shipping options and estimated delivery times:

- Standard Shipping: 5-7 business days ($4.99)
- Express Shipping: 2-3 business days ($12.99)
- Overnight Shipping: Next business day ($24.99)

To track your order:
1. Check your confirmation email for tracking number
2. Visit our Track Order page or the carrier's website
3. Enter your order number or tracking number

Tracking updates may take 24-48 hours to appear after shipment.""",
        "category": "shipping",
        "keywords": ["shipping", "delivery", "tracking", "order status"]
    },
    {
        "title": "Return and Refund Policy",
        "content": """Our return policy:

- 30-day money-back guarantee on all products
- Items must be unused and in original packaging
- Refunds processed within 5-7 business days
- Original shipping costs are non-refundable

To request a return:
1. Contact support with your order number
2. Explain the reason for your return
3. We'll provide a prepaid return shipping label
4. Ship the item back within 14 days

Defective items are eligible for full refund including shipping costs.""",
        "category": "orders",
        "keywords": ["refund", "return", "money back", "policy"]
    },
    {
        "title": "Order Cancellation",
        "content": """You can cancel your order within 1 hour of placing it.

To cancel:
1. Go to My Orders in your account
2. Find the order and click "Cancel Order"
3. Confirm cancellation

After 1 hour, orders may have already entered processing. In this case:
- You can refuse delivery when it arrives
- Request a return after receiving the package

Canceled orders are refunded within 3-5 business days to your original payment method.""",
        "category": "orders",
        "keywords": ["cancel", "cancellation", "order"]
    },
    {
        "title": "Payment Methods Accepted",
        "content": """We accept the following payment methods:

Credit/Debit Cards:
- Visa
- Mastercard
- American Express
- Discover

Digital Wallets:
- Apple Pay
- Google Pay
- PayPal

All transactions are secured with 256-bit SSL encryption. We never store your full card number.""",
        "category": "billing",
        "keywords": ["payment", "credit card", "paypal", "billing"]
    },
    {
        "title": "Payment Failed - Troubleshooting",
        "content": """If your payment fails, check these common causes:

1. Insufficient funds - Verify your account balance
2. Card expired - Update your card details
3. Incorrect CVV - Re-enter the 3-digit security code
4. Bank block - Contact your bank to authorize the transaction
5. Address mismatch - Billing address must match card

Solutions to try:
- Use a different payment method
- Clear browser cookies and try again
- Disable VPN if using one
- Contact your bank to whitelist our merchant""",
        "category": "billing",
        "keywords": ["payment failed", "declined", "error", "card"]
    },
    {
        "title": "App Not Loading or Crashing",
        "content": """If the app isn't working properly, try these steps:

1. Force close and reopen the app
2. Check your internet connection
3. Clear the app cache (Settings > Apps > [App Name] > Clear Cache)
4. Update to the latest version from the app store
5. Restart your device
6. Reinstall the app (your data will be preserved if you're logged in)

If problems persist, please note:
- Your device model and OS version
- Any error messages shown
- Steps to reproduce the issue

Then contact support with these details.""",
        "category": "technical",
        "keywords": ["app", "crash", "loading", "bug", "error"]
    },
    {
        "title": "Account Update and Profile Changes",
        "content": """To update your account details:

Email address:
1. Go to Settings > Account
2. Click "Change Email"
3. Verify with your current password
4. Confirm via link sent to new email

Shipping address:
1. Go to Settings > Addresses
2. Edit existing or add new address
3. Set as default if desired

Name change:
Contact support with ID verification for legal name changes.

Phone number:
Update directly in Settings > Account > Phone.""",
        "category": "account",
        "keywords": ["update", "profile", "email", "address", "settings"]
    },
    {
        "title": "Subscription and Billing Management",
        "content": """Manage your subscription at Settings > Subscription.

Plans available:
- Free: Basic features, limited usage
- Pro ($9.99/mo): Full features, priority support
- Enterprise: Custom pricing, dedicated support

Cancel subscription:
1. Go to Settings > Subscription
2. Click "Cancel Subscription"
3. Access continues until billing period ends

Billing:
- Receipts sent to your email after each charge
- Update payment method to avoid service interruption
- Failed payments retried for 3 days before suspension

Pro-rated refunds available for annual plans canceled within 14 days.""",
        "category": "billing",
        "keywords": ["subscription", "billing", "cancel", "plan", "pricing"]
    },
]


# =============================================================================
# CUSTOMERS
# =============================================================================

CUSTOMERS = [
    {
        "id": "cust_john_doe",
        "email": "john.doe@email.com",
        "name": "John Doe",
        "phone": "+1-555-0101",
        "tier": "premium",
        "lifetime_value": 1250.00
    },
    {
        "id": "cust_jane_smith",
        "email": "jane.smith@email.com",
        "name": "Jane Smith",
        "phone": "+1-555-0102",
        "tier": "vip",
        "lifetime_value": 5420.00
    },
    {
        "id": "cust_bob_wilson",
        "email": "bob.wilson@email.com",
        "name": "Bob Wilson",
        "phone": "+1-555-0103",
        "tier": "standard",
        "lifetime_value": 89.99
    },
    {
        "id": "cust_alice_jones",
        "email": "alice.jones@email.com",
        "name": "Alice Jones",
        "phone": "+1-555-0104",
        "tier": "premium",
        "lifetime_value": 890.00
    },
    {
        "id": "cust_charlie_brown",
        "email": "charlie.brown@email.com",
        "name": "Charlie Brown",
        "phone": "+1-555-0105",
        "tier": "standard",
        "lifetime_value": 149.99
    },
]


# =============================================================================
# PRODUCTS
# =============================================================================

PRODUCTS = [
    {"id": "prod_wh1000", "name": "Wireless Headphones Pro", "price": 149.99, "category": "electronics", "description": "Premium noise-canceling wireless headphones with 30-hour battery life"},
    {"id": "prod_kb500", "name": "Mechanical Keyboard RGB", "price": 89.99, "category": "electronics", "description": "Mechanical gaming keyboard with RGB lighting and Cherry MX switches"},
    {"id": "prod_ms300", "name": "Ergonomic Mouse", "price": 49.99, "category": "electronics", "description": "Ergonomic wireless mouse with adjustable DPI"},
    {"id": "prod_mon27", "name": "27-inch 4K Monitor", "price": 399.99, "category": "electronics", "description": "Ultra HD 4K monitor with HDR support"},
    {"id": "prod_cam01", "name": "HD Webcam 1080p", "price": 79.99, "category": "electronics", "description": "Full HD webcam with built-in microphone"},
    {"id": "prod_hub01", "name": "USB-C Hub 7-in-1", "price": 45.99, "category": "accessories", "description": "USB-C hub with HDMI, USB-A, SD card reader"},
    {"id": "prod_stand", "name": "Laptop Stand Aluminum", "price": 35.99, "category": "accessories", "description": "Adjustable aluminum laptop stand for better ergonomics"},
    {"id": "prod_pad01", "name": "Mouse Pad XL", "price": 19.99, "category": "accessories", "description": "Extra-large desk pad with stitched edges"},
    {"id": "prod_cable", "name": "Charging Cable 3-Pack", "price": 24.99, "category": "accessories", "description": "Braided USB-C cables in 3ft, 6ft, and 10ft lengths"},
    {"id": "prod_bag01", "name": "Laptop Backpack", "price": 59.99, "category": "accessories", "description": "Water-resistant backpack with padded laptop compartment"},
]


# =============================================================================
# ORDERS
# =============================================================================

CARRIERS = [
    ("UPS", "1Z999AA1"),
    ("FedEx", "7489"),
    ("USPS", "9400111899"),
]


def generate_tracking_number(carrier: str, prefix: str) -> str:
    return f"{prefix}{random.randint(100000000, 999999999)}"


def create_orders():
    """Generate sample orders with various statuses."""
    now = datetime.now()

    orders = [
        # Recent shipped order for John (good for status check demos)
        {
            "id": "ord_12345",
            "customer_id": "cust_john_doe",
            "status": "shipped",
            "items": [("prod_wh1000", 1), ("prod_hub01", 1)],
            "days_ago": 3,
            "shipped_days_ago": 1,
            "carrier_idx": 0
        },
        # Delivered order for John
        {
            "id": "ord_11111",
            "customer_id": "cust_john_doe",
            "status": "delivered",
            "items": [("prod_kb500", 1)],
            "days_ago": 15,
            "shipped_days_ago": 12,
            "delivered_days_ago": 10,
            "carrier_idx": 1
        },
        # Processing order for Jane
        {
            "id": "ord_22222",
            "customer_id": "cust_jane_smith",
            "status": "processing",
            "items": [("prod_mon27", 1), ("prod_stand", 1)],
            "days_ago": 1,
            "carrier_idx": None
        },
        # Pending order for Bob (good for cancellation demos)
        {
            "id": "ord_33333",
            "customer_id": "cust_bob_wilson",
            "status": "pending",
            "items": [("prod_ms300", 1), ("prod_pad01", 1), ("prod_cable", 1)],
            "days_ago": 0,
            "carrier_idx": None
        },
        # Shipped order for Alice
        {
            "id": "ord_44444",
            "customer_id": "cust_alice_jones",
            "status": "shipped",
            "items": [("prod_cam01", 1), ("prod_bag01", 1)],
            "days_ago": 5,
            "shipped_days_ago": 2,
            "carrier_idx": 2
        },
        # Refunded order for Charlie (good for refund demos)
        {
            "id": "ord_99999",
            "customer_id": "cust_charlie_brown",
            "status": "refunded",
            "items": [("prod_wh1000", 1)],
            "days_ago": 20,
            "shipped_days_ago": 17,
            "delivered_days_ago": 14,
            "carrier_idx": 0
        },
    ]

    # Build product lookup
    products_map = {p["id"]: p for p in PRODUCTS}

    result = []
    for template in orders:
        created_at = now - timedelta(days=template["days_ago"])

        # Calculate total from items
        items = []
        total = 0
        for product_id, quantity in template["items"]:
            product = products_map[product_id]
            subtotal = product["price"] * quantity
            total += subtotal
            items.append({
                "product_id": product_id,
                "product_name": product["name"],
                "quantity": quantity,
                "unit_price": product["price"],
                "subtotal": subtotal
            })

        order_data = {
            "id": template["id"],
            "customer_id": template["customer_id"],
            "status": template["status"],
            "total": total,
            "shipping_address": {
                "street": "123 Main St",
                "city": "San Francisco",
                "state": "CA",
                "zip": "94105",
                "country": "USA"
            },
            "created_at": created_at.isoformat(),
            "updated_at": created_at.isoformat(),
            "items": items
        }

        # Add shipping info if applicable
        if template.get("carrier_idx") is not None:
            carrier, prefix = CARRIERS[template["carrier_idx"]]
            order_data["carrier"] = carrier
            order_data["tracking_number"] = generate_tracking_number(carrier, prefix)
            order_data["estimated_delivery"] = (
                created_at + timedelta(days=7)
            ).strftime("%Y-%m-%d")

        if template.get("shipped_days_ago"):
            order_data["shipped_at"] = (
                now - timedelta(days=template["shipped_days_ago"])
            ).isoformat()

        if template.get("delivered_days_ago"):
            order_data["delivered_at"] = (
                now - timedelta(days=template["delivered_days_ago"])
            ).isoformat()

        result.append(order_data)

    return result


# =============================================================================
# SEEDING FUNCTIONS
# =============================================================================

def seed_help_articles(client):
    """Seed help articles table."""
    print("Seeding help articles...")

    for article in HELP_ARTICLES:
        try:
            client.table("help_articles").upsert({
                "title": article["title"],
                "content": article["content"],
                "category": article["category"],
                "keywords": article["keywords"]
            }, on_conflict="title").execute()
            print(f"  [OK] {article['title'][:40]}...")
        except Exception as e:
            print(f"  [FAIL] {article['title'][:40]}... - {e}")


def seed_customers(client):
    """Seed customers table."""
    print("\nSeeding customers...")

    for customer in CUSTOMERS:
        try:
            client.table("customers").upsert(customer, on_conflict="id").execute()
            print(f"  [OK] {customer['name']} ({customer['tier']})")
        except Exception as e:
            print(f"  [FAIL] {customer['name']} - {e}")


def seed_products(client):
    """Seed products table."""
    print("\nSeeding products...")

    for product in PRODUCTS:
        try:
            client.table("products").upsert({
                "id": product["id"],
                "name": product["name"],
                "price": product["price"],
                "category": product["category"],
                "description": product["description"],
                "in_stock": True
            }, on_conflict="id").execute()
            print(f"  [OK] {product['name']}")
        except Exception as e:
            print(f"  [FAIL] {product['name']} - {e}")


def seed_orders(client):
    """Seed orders and order_items tables."""
    print("\nSeeding orders...")

    orders = create_orders()

    for order in orders:
        try:
            # Extract items before inserting order
            items = order.pop("items")

            # Insert order
            client.table("orders").upsert(order, on_conflict="id").execute()

            # Insert order items
            for item in items:
                client.table("order_items").insert({
                    "order_id": order["id"],
                    "product_id": item["product_id"],
                    "product_name": item["product_name"],
                    "quantity": item["quantity"],
                    "unit_price": item["unit_price"],
                    "subtotal": item["subtotal"]
                }).execute()

            print(f"  [OK] {order['id']} ({order['status']}) - ${order['total']:.2f}")
        except Exception as e:
            print(f"  [FAIL] {order['id']} - {e}")


def main():
    """Run all seed functions."""
    print("=" * 60)
    print("SEEDING DEMO DATA")
    print("=" * 60)

    client = get_supabase_client()

    seed_help_articles(client)
    seed_customers(client)
    seed_products(client)
    seed_orders(client)

    print("\n" + "=" * 60)
    print("SEED COMPLETE")
    print("=" * 60)
    print("""
Sample data for testing:

ORDERS:
  - ord_12345 (shipped) - John Doe
  - ord_22222 (processing) - Jane Smith
  - ord_33333 (pending) - Bob Wilson
  - ord_44444 (shipped) - Alice Jones
  - ord_99999 (refunded) - Charlie Brown

CUSTOMERS:
  - cust_john_doe (premium)
  - cust_jane_smith (vip)
  - cust_bob_wilson (standard)

FAQ CATEGORIES:
  - account (password, 2fa, profile)
  - orders (returns, cancellation)
  - shipping (tracking, delivery)
  - billing (payment, subscription)
  - technical (app issues)
""")


if __name__ == "__main__":
    main()
