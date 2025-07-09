-- Initialize Clerk database with correct schema matching SQLAlchemy models

-- Create ENUMs first (using SQLAlchemy naming convention)
-- Note: Application sends uppercase enum values
CREATE TYPE permissionlevel AS ENUM ('READ', 'WRITE', 'ADMIN');
CREATE TYPE casestatus AS ENUM ('ACTIVE', 'ARCHIVED', 'CLOSED', 'DELETED');

-- Create law_firms table
CREATE TABLE IF NOT EXISTS law_firms (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    domain VARCHAR(255),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for law_firms
CREATE INDEX IF NOT EXISTS idx_law_firms_name ON law_firms(name);
CREATE INDEX IF NOT EXISTS idx_law_firms_domain ON law_firms(domain);

-- Create users table
CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(36) PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    law_firm_id VARCHAR(36) NOT NULL REFERENCES law_firms(id) ON DELETE CASCADE,
    is_active BOOLEAN DEFAULT true,
    is_admin BOOLEAN DEFAULT false,
    last_login TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for users
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_law_firm_id ON users(law_firm_id);

-- Create cases table
CREATE TABLE IF NOT EXISTS cases (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    collection_name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    law_firm_id VARCHAR(36) NOT NULL REFERENCES law_firms(id) ON DELETE CASCADE,
    status casestatus DEFAULT 'ACTIVE' NOT NULL,
    created_by VARCHAR(36) NOT NULL REFERENCES users(id),
    case_metadata TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for cases
CREATE INDEX IF NOT EXISTS idx_cases_name ON cases(name);
CREATE INDEX IF NOT EXISTS idx_cases_collection_name ON cases(collection_name);
CREATE INDEX IF NOT EXISTS idx_cases_law_firm_id ON cases(law_firm_id);
CREATE INDEX IF NOT EXISTS idx_cases_status ON cases(status);
CREATE INDEX IF NOT EXISTS idx_cases_created_by ON cases(created_by);

-- Create user_case_permissions association table
CREATE TABLE IF NOT EXISTS user_case_permissions (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    case_id VARCHAR(36) NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    permission_level permissionlevel NOT NULL,
    granted_at TIMESTAMPTZ DEFAULT NOW(),
    granted_by VARCHAR(36) REFERENCES users(id),
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for user_case_permissions
CREATE INDEX IF NOT EXISTS idx_user_case_permissions_user_id ON user_case_permissions(user_id);
CREATE INDEX IF NOT EXISTS idx_user_case_permissions_case_id ON user_case_permissions(case_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_user_case_permissions_user_case ON user_case_permissions(user_id, case_id);

-- Create user_case_permissions_orm table (ORM model)
CREATE TABLE IF NOT EXISTS user_case_permissions_orm (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    case_id VARCHAR(36) NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    permission_level permissionlevel NOT NULL,
    granted_at TIMESTAMPTZ DEFAULT NOW(),
    granted_by VARCHAR(36) REFERENCES users(id),
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for user_case_permissions_orm
CREATE INDEX IF NOT EXISTS idx_user_case_perm_user_id ON user_case_permissions_orm(user_id);
CREATE INDEX IF NOT EXISTS idx_user_case_perm_case_id ON user_case_permissions_orm(case_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_user_case_perm_user_case ON user_case_permissions_orm(user_id, case_id);

-- Create refresh_tokens table
CREATE TABLE IF NOT EXISTS refresh_tokens (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token VARCHAR(500) NOT NULL UNIQUE,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    revoked_at TIMESTAMPTZ
);

-- Create indexes for refresh_tokens
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_token ON refresh_tokens(token);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user_id ON refresh_tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_expires_at ON refresh_tokens(expires_at);

-- Create alembic_version table for migrations tracking
CREATE TABLE IF NOT EXISTS alembic_version (
    version_num VARCHAR(32) NOT NULL,
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

-- Insert dev data only if not exists
DO $$
BEGIN
    -- Dev law firm
    IF NOT EXISTS (SELECT 1 FROM law_firms WHERE id = '123e4567-e89b-12d3-a456-426614174000') THEN
        INSERT INTO law_firms (id, name, domain, is_active)
        VALUES ('123e4567-e89b-12d3-a456-426614174000', 'Development Law Firm', 'dev.clerk.ai', true);
    END IF;
    
    -- Dev user with bcrypt hash for password 'password'
    -- Note: This is a default dev password, change in production!
    IF NOT EXISTS (SELECT 1 FROM users WHERE id = '123e4567-e89b-12d3-a456-426614174001') THEN
        INSERT INTO users (id, email, password_hash, name, law_firm_id, is_admin)
        VALUES (
            '123e4567-e89b-12d3-a456-426614174001', 
            'dev@clerk.ai', 
            '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewKyNiGHTGpFyNBC',  -- bcrypt hash of 'password'
            'Dev User', 
            '123e4567-e89b-12d3-a456-426614174000', 
            true
        );
    END IF;
    
    -- Mark database as initialized with latest migration
    IF NOT EXISTS (SELECT 1 FROM alembic_version WHERE version_num = '002_add_password_hash') THEN
        INSERT INTO alembic_version (version_num) VALUES ('002_add_password_hash');
    END IF;
END $$;

-- Create trigger to update updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply trigger to all tables with updated_at
CREATE TRIGGER update_law_firms_updated_at BEFORE UPDATE ON law_firms
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_cases_updated_at BEFORE UPDATE ON cases
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_case_permissions_updated_at BEFORE UPDATE ON user_case_permissions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_case_permissions_orm_updated_at BEFORE UPDATE ON user_case_permissions_orm
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();