-- ============================================================================
-- AURUM PostgreSQL / Supabase Initial Schema Migration
-- 7 Core Tables with Row-Level Security (RLS) & Foreign Key Constraints
-- ============================================================================

-- Enable UUID extension if not enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ----------------------------------------------------------------------------
-- 1. users
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('customer', 'jeweller', 'admin')),
    phone TEXT,
    hashed_password TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);

-- ----------------------------------------------------------------------------
-- 2. jewellery
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS jewellery (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    owner_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type TEXT NOT NULL,
    gross_weight NUMERIC(10, 4) NOT NULL CHECK (gross_weight > 0),
    purity INT NOT NULL CHECK (purity IN (999, 916, 750, 585)),
    hallmark TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_jewellery_owner ON jewellery(owner_id);

-- ----------------------------------------------------------------------------
-- 3. verifications
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS verifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    jewellery_id UUID NOT NULL REFERENCES jewellery(id) ON DELETE CASCADE,
    huid VARCHAR(6),
    xrf_result NUMERIC(6, 2),
    net_weight NUMERIC(10, 4),
    stone_weight NUMERIC(10, 4) DEFAULT 0,
    verified_by UUID REFERENCES users(id),
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'verified', 'disputed')),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_verifications_jewellery ON verifications(jewellery_id);
CREATE INDEX IF NOT EXISTS idx_verifications_huid ON verifications(huid);

-- ----------------------------------------------------------------------------
-- 4. gold_rates
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS gold_rates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    date DATE NOT NULL,
    purity_label TEXT NOT NULL,
    fineness INT NOT NULL CHECK (fineness IN (999, 916, 750, 585)),
    rate_per_gram NUMERIC(10, 2) NOT NULL CHECK (rate_per_gram > 0),
    source TEXT NOT NULL DEFAULT 'IBJA',
    session TEXT NOT NULL CHECK (session IN ('AM', 'PM')),
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT uq_rate_date_fineness_session UNIQUE (date, fineness, session)
);

CREATE INDEX IF NOT EXISTS idx_gold_rates_date ON gold_rates(date);
CREATE INDEX IF NOT EXISTS idx_gold_rates_fineness ON gold_rates(fineness);

-- ----------------------------------------------------------------------------
-- 5. transactions
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS transactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id UUID NOT NULL REFERENCES users(id),
    jeweller_id UUID NOT NULL REFERENCES users(id),
    jewellery_id UUID REFERENCES jewellery(id),
    snapshot JSONB NOT NULL,
    status TEXT NOT NULL DEFAULT 'confirmed' CHECK (status IN ('draft', 'confirmed', 'completed', 'cancelled')),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_transactions_customer ON transactions(customer_id);
CREATE INDEX IF NOT EXISTS idx_transactions_jeweller ON transactions(jeweller_id);
CREATE INDEX IF NOT EXISTS idx_transactions_created_at ON transactions(created_at DESC);

-- ----------------------------------------------------------------------------
-- 6. evidence
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS evidence (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    transaction_id UUID NOT NULL REFERENCES transactions(id) ON DELETE CASCADE,
    file_url TEXT NOT NULL,
    evidence_type TEXT NOT NULL CHECK (evidence_type IN ('photo', 'xrf_cert', 'bill', 'scale_receipt')),
    uploaded_by UUID NOT NULL REFERENCES users(id),
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_evidence_transaction ON evidence(transaction_id);

-- ----------------------------------------------------------------------------
-- 7. anomaly_flags
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS anomaly_flags (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    transaction_id UUID NOT NULL REFERENCES transactions(id) ON DELETE CASCADE,
    flag_type TEXT NOT NULL CHECK (flag_type IN (
        'purity_mismatch',
        'weight_variance',
        'hallmark_mismatch',
        'incomplete_evidence',
        'stale_rate',
        'disproportionate_deduction'
    )),
    severity TEXT NOT NULL CHECK (severity IN ('low', 'medium', 'high')),
    explanation TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_anomaly_flags_transaction ON anomaly_flags(transaction_id);

-- ============================================================================
-- ROW LEVEL SECURITY (RLS) POLICIES
-- ============================================================================

-- Enable RLS on all sensitive tables
ALTER TABLE jewellery ENABLE ROW LEVEL SECURITY;
ALTER TABLE verifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE evidence ENABLE ROW LEVEL SECURITY;
ALTER TABLE anomaly_flags ENABLE ROW LEVEL SECURITY;
ALTER TABLE gold_rates ENABLE ROW LEVEL SECURITY;

-- 1. Gold rates are publicly viewable by any authenticated user
CREATE POLICY "Gold rates are viewable by everyone" 
    ON gold_rates FOR SELECT 
    USING (true);

-- 2. Jewellery RLS: Customers can view/manage their own jewellery; Jewellers can view
CREATE POLICY "Customers manage own jewellery" 
    ON jewellery FOR ALL 
    USING (auth.uid() = owner_id);

CREATE POLICY "Jewellers can view jewellery for verification" 
    ON jewellery FOR SELECT 
    USING (
        EXISTS (
            SELECT 1 FROM users 
            WHERE users.id = auth.uid() AND users.role IN ('jeweller', 'admin')
        )
    );

-- 3. Transactions RLS: Customers view their own; Jewellers view/manage theirs
CREATE POLICY "Customers view own transactions" 
    ON transactions FOR SELECT 
    USING (auth.uid() = customer_id);

CREATE POLICY "Jewellers manage their store transactions" 
    ON transactions FOR ALL 
    USING (auth.uid() = jeweller_id);

CREATE POLICY "Admins full access to transactions" 
    ON transactions FOR ALL 
    USING (
        EXISTS (
            SELECT 1 FROM users 
            WHERE users.id = auth.uid() AND users.role = 'admin'
        )
    );

-- 4. Evidence RLS: Visible to transaction participants
CREATE POLICY "Transaction participants view evidence" 
    ON evidence FOR SELECT 
    USING (
        EXISTS (
            SELECT 1 FROM transactions 
            WHERE transactions.id = evidence.transaction_id 
              AND (transactions.customer_id = auth.uid() OR transactions.jeweller_id = auth.uid())
        )
    );

-- 5. Anomaly Flags RLS: Visible to transaction participants
CREATE POLICY "Transaction participants view anomaly flags" 
    ON anomaly_flags FOR SELECT 
    USING (
        EXISTS (
            SELECT 1 FROM transactions 
            WHERE transactions.id = anomaly_flags.transaction_id 
              AND (transactions.customer_id = auth.uid() OR transactions.jeweller_id = auth.uid())
        )
    );

