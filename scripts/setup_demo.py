#!/usr/bin/env python
"""
One-command demo setup script.
Run: python -m scripts.setup_demo

This script:
1. Verifies environment configuration
2. Seeds all demo data (help articles, customers, products, orders)
3. Prints demo scenarios to try
"""

import os
import sys


def check_env():
    """Verify required environment variables."""
    print("Checking environment variables...\n")

    required = [
        ("SUPABASE_URL", "Supabase database URL"),
        ("SUPABASE_KEY", "Supabase service role key"),
        ("OPENAI_API_KEY", "OpenAI API key for the agent"),
    ]

    optional = [
        ("GITHUB_TOKEN", "Personal access token for creating issues"),
        ("GITHUB_REPO", "Repository for bug reports (owner/repo)"),
        ("RABBITMQ_URL", "RabbitMQ connection URL"),
    ]

    missing = []
    for var, description in required:
        value = os.getenv(var)
        if value:
            # Mask sensitive values
            masked = value[:8] + "..." if len(value) > 12 else "***"
            print(f"  [OK] {var}: {masked}")
        else:
            print(f"  [MISSING] {var}: {description}")
            missing.append(var)

    print()
    for var, description in optional:
        value = os.getenv(var)
        if value:
            masked = value[:8] + "..." if len(value) > 12 else "***"
            print(f"  [OK] {var}: {masked}")
        else:
            print(f"  [--] {var}: Not configured (optional)")

    if missing:
        print(f"\n[ERROR] Missing required environment variables: {', '.join(missing)}")
        print("\nTo fix:")
        print("  1. Copy .env.example to .env")
        print("  2. Fill in the required values")
        print("  3. Re-run this script")
        return False

    print("\n[OK] Environment configured correctly")
    return True


def seed_data():
    """Run the data seeding script."""
    print("\n" + "=" * 60)
    print("SEEDING DEMO DATA")
    print("=" * 60 + "\n")

    try:
        from scripts.seed_data import main as seed_main
        seed_main()
        return True
    except Exception as e:
        print(f"\n[ERROR] Failed to seed data: {e}")
        print("\nPossible issues:")
        print("  - Database tables not created (run migrations first)")
        print("  - Invalid Supabase credentials")
        print("  - Network connectivity issues")
        return False


def print_demo_guide():
    """Print demo usage instructions."""
    github_configured = bool(os.getenv("GITHUB_TOKEN") and os.getenv("GITHUB_REPO"))

    print("\n" + "=" * 60)
    print("DEMO SETUP COMPLETE!")
    print("=" * 60)
    print("""
STARTING THE SERVICES
=====================

Option 1 - Docker Compose:
  docker compose up -d

Option 2 - Manual:
  # Terminal 1: API
  uvicorn src.api.main:app --reload --port 8000

  # Terminal 2: Worker
  python -m src.worker.main

  # Terminal 3: Dashboard
  cd dashboard && npm run dev

DEMO SCENARIOS TO TRY
=====================

1. ORDER STATUS CHECK
   Subject: "Where is my order?"
   Body: "I placed order ord_12345 and want to know where it is"

   What happens: Agent queries real order data, returns tracking info

2. FAQ / HELP QUERY
   Subject: "How do I reset my password?"
   Body: "I forgot my password and can't log in to my account"

   What happens: Agent queries help_articles table, returns relevant FAQ

3. PRODUCT INQUIRY
   Subject: "Product question"
   Body: "Do you have wireless headphones? What's the price?"

   What happens: Agent searches products table, returns matching items

4. REFUND REQUEST (triggers approval)
   Subject: "I want a refund"
   Body: "Order ord_12345 arrived damaged, please refund $195.98"

   What happens: Agent validates order, creates approval request
   Then: Go to Approvals page to approve/reject
""")

    if github_configured:
        print("""5. BUG REPORT (creates GitHub issue)
   Subject: "App keeps crashing"
   Body: "Every time I try to checkout, the app crashes on iOS"

   What happens: Agent creates real GitHub issue in your repo
""")
    else:
        print("""5. BUG REPORT
   Subject: "App keeps crashing"
   Body: "Every time I try to checkout, the app crashes on iOS"

   Note: GitHub not configured - will create local bug ID
   To enable: Set GITHUB_TOKEN and GITHUB_REPO in .env
""")

    print("""
SAMPLE IDS FOR TESTING
======================

Orders:
  ord_12345 - Shipped (Wireless Headphones + USB Hub)
  ord_22222 - Processing (4K Monitor + Laptop Stand)
  ord_33333 - Pending (Mouse + Pad + Cable)
  ord_44444 - Shipped (Webcam + Backpack)
  ord_99999 - Refunded (Wireless Headphones)

Customers:
  cust_john_doe / john.doe@email.com (premium)
  cust_jane_smith / jane.smith@email.com (vip)
  cust_bob_wilson / bob.wilson@email.com (standard)

URLS
====
  Dashboard: http://localhost:3000
  API Docs:  http://localhost:8000/docs
  API Health: http://localhost:8000/health
""")


def main():
    print("=" * 60)
    print("SUPPORT TICKET AGENT - DEMO SETUP")
    print("=" * 60)
    print()

    # Check environment
    if not check_env():
        sys.exit(1)

    # Seed data
    if not seed_data():
        print("\n[WARNING] Data seeding had issues. Some features may not work.")
        print("Make sure the database migration (003_demo_data.sql) has been applied.")

    # Print guide
    print_demo_guide()


if __name__ == "__main__":
    main()
