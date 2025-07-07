-- Initialize Clerk database with dev data

-- Create law_firms table
CREATE TABLE IF NOT EXISTS law_firms (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    domain VARCHAR(255),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create users table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),
    law_firm_id UUID REFERENCES law_firms(id),
    is_admin BOOLEAN DEFAULT false,
    last_login TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create cases table
CREATE TABLE IF NOT EXISTS cases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    law_firm_id UUID REFERENCES law_firms(id),
    collection_name VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    status VARCHAR(50) DEFAULT 'active',
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Create case_permissions table
CREATE TABLE IF NOT EXISTS case_permissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id UUID REFERENCES cases(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    permission_level VARCHAR(50) NOT NULL,
    granted_by UUID REFERENCES users(id),
    granted_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    UNIQUE(case_id, user_id)
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_users_law_firm ON users(law_firm_id);
CREATE INDEX IF NOT EXISTS idx_cases_law_firm ON cases(law_firm_id);
CREATE INDEX IF NOT EXISTS idx_cases_collection ON cases(collection_name);
CREATE INDEX IF NOT EXISTS idx_case_permissions_user ON case_permissions(user_id);
CREATE INDEX IF NOT EXISTS idx_case_permissions_case ON case_permissions(case_id);

-- Insert dev data
-- Dev law firm
INSERT INTO law_firms (id, name, domain, is_active)
VALUES ('dev-firm-123', 'Development Law Firm', 'dev.clerk.ai', true)
ON CONFLICT DO NOTHING;

-- Dev user
INSERT INTO users (id, email, name, law_firm_id, is_admin)
VALUES ('dev-user-123', 'dev@clerk.ai', 'Dev User', 'dev-firm-123', true)
ON CONFLICT DO NOTHING;

-- Create trigger to update updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply trigger to all tables
CREATE TRIGGER update_law_firms_updated_at BEFORE UPDATE ON law_firms
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_cases_updated_at BEFORE UPDATE ON cases
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Ensure updated_at is never NULL for cases
CREATE OR REPLACE FUNCTION ensure_updated_at_not_null()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.updated_at IS NULL THEN
        NEW.updated_at = COALESCE(OLD.updated_at, NEW.created_at, NOW());
    END IF;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER ensure_cases_updated_at_not_null BEFORE INSERT OR UPDATE ON cases
    FOR EACH ROW EXECUTE FUNCTION ensure_updated_at_not_null();