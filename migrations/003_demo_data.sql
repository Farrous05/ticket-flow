-- Migration: 003_demo_data.sql
-- Description: Add tables for demo data (customers, products, orders, help articles)
-- Purpose: Enable real database queries instead of mocked responses

-- ============================================================================
-- HELP ARTICLES (for FAQ queries)
-- ============================================================================

CREATE TABLE IF NOT EXISTS help_articles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    category TEXT NOT NULL,  -- 'account', 'orders', 'technical', 'billing', 'shipping'
    keywords TEXT[] DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_help_articles_category ON help_articles(category);
CREATE INDEX IF NOT EXISTS idx_help_articles_keywords ON help_articles USING GIN(keywords);

-- ============================================================================
-- CUSTOMERS
-- ============================================================================

CREATE TABLE IF NOT EXISTS customers (
    id TEXT PRIMARY KEY,  -- e.g., 'cust_john_doe' or email
    email TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    phone TEXT,
    tier TEXT DEFAULT 'standard',  -- 'standard', 'premium', 'vip'
    lifetime_value DECIMAL(10, 2) DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_customers_email ON customers(email);
CREATE INDEX IF NOT EXISTS idx_customers_tier ON customers(tier);

-- ============================================================================
-- PRODUCTS
-- ============================================================================

CREATE TABLE IF NOT EXISTS products (
    id TEXT PRIMARY KEY,  -- e.g., 'prod_wh1000'
    name TEXT NOT NULL,
    description TEXT,
    price DECIMAL(10, 2) NOT NULL,
    category TEXT,
    in_stock BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_products_category ON products(category);
CREATE INDEX IF NOT EXISTS idx_products_name ON products(name);

-- ============================================================================
-- ORDERS
-- ============================================================================

CREATE TABLE IF NOT EXISTS orders (
    id TEXT PRIMARY KEY,  -- e.g., 'ord_12345'
    customer_id TEXT REFERENCES customers(id),
    status TEXT NOT NULL DEFAULT 'pending',
    -- Status values: 'pending', 'confirmed', 'processing', 'shipped', 'delivered', 'cancelled', 'refunded'
    total DECIMAL(10, 2) NOT NULL,
    shipping_address JSONB,
    tracking_number TEXT,
    carrier TEXT,  -- 'UPS', 'FedEx', 'USPS'
    estimated_delivery DATE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    shipped_at TIMESTAMPTZ,
    delivered_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_orders_customer_id ON orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders(created_at DESC);

-- ============================================================================
-- ORDER ITEMS
-- ============================================================================

CREATE TABLE IF NOT EXISTS order_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    order_id TEXT NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    product_id TEXT REFERENCES products(id),
    product_name TEXT NOT NULL,  -- Denormalized for convenience
    quantity INTEGER NOT NULL DEFAULT 1,
    unit_price DECIMAL(10, 2) NOT NULL,
    subtotal DECIMAL(10, 2) NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_order_items_order_id ON order_items(order_id);

-- ============================================================================
-- ROW LEVEL SECURITY
-- ============================================================================

ALTER TABLE help_articles ENABLE ROW LEVEL SECURITY;
ALTER TABLE customers ENABLE ROW LEVEL SECURITY;
ALTER TABLE products ENABLE ROW LEVEL SECURITY;
ALTER TABLE orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE order_items ENABLE ROW LEVEL SECURITY;

-- Service role policies (full access for backend)
CREATE POLICY "Service role full access on help_articles"
    ON help_articles FOR ALL
    USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access on customers"
    ON customers FOR ALL
    USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access on products"
    ON products FOR ALL
    USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access on orders"
    ON orders FOR ALL
    USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access on order_items"
    ON order_items FOR ALL
    USING (auth.role() = 'service_role');
