-- HomeDesk Facility Management Portal - Multi-Tenant PostgreSQL Schema
-- Enforces tenant isolation at the database layer with foreign keys and tenant-scoped indexes.

-- 1. Organizations / Tenants Table
CREATE TABLE IF NOT EXISTS organizations (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (NOW() AT TIME ZONE 'UTC') NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_organizations_slug ON organizations(slug);

-- 2. Users Table (Tenant-scoped)
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    organization_id INTEGER NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    mobile VARCHAR(20) NOT NULL,
    email VARCHAR(120) UNIQUE NOT NULL,
    password_hash VARCHAR(255),
    role VARCHAR(30) DEFAULT 'customer' NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (NOW() AT TIME ZONE 'UTC') NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_users_org_id ON users(organization_id);
CREATE INDEX IF NOT EXISTS idx_users_org_mobile ON users(organization_id, mobile);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);


-- 3. Core Leads Table (Tenant-scoped)
CREATE TABLE IF NOT EXISTS leads (
    id SERIAL PRIMARY KEY,
    lead_id VARCHAR(30) NOT NULL,
    organization_id INTEGER NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    service_type VARCHAR(50) NOT NULL,
    name VARCHAR(100) NOT NULL,
    mobile VARCHAR(20) NOT NULL,
    email VARCHAR(120),
    address TEXT,
    city VARCHAR(100) NOT NULL,
    state VARCHAR(100),
    pincode VARCHAR(10),
    start_date DATE,
    preferred_timing VARCHAR(50),
    budget NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    additional_notes TEXT,
    status VARCHAR(30) DEFAULT 'New' NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (NOW() AT TIME ZONE 'UTC') NOT NULL,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (NOW() AT TIME ZONE 'UTC') NOT NULL
);
-- Tenant isolation indexes
CREATE UNIQUE INDEX IF NOT EXISTS idx_leads_org_lead_id ON leads(organization_id, lead_id);
CREATE INDEX IF NOT EXISTS idx_leads_org_mobile ON leads(organization_id, mobile);
CREATE INDEX IF NOT EXISTS idx_leads_org_service ON leads(organization_id, service_type);

-- 4. Cook Service Requirements
CREATE TABLE IF NOT EXISTS cook_requirements (
    id SERIAL PRIMARY KEY,
    lead_id INTEGER UNIQUE NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
    cuisine_type VARCHAR(100),
    meals_per_day INTEGER
);
CREATE INDEX IF NOT EXISTS idx_cook_req_lead_id ON cook_requirements(lead_id);

-- 5. Driver Service Requirements
CREATE TABLE IF NOT EXISTS driver_requirements (
    id SERIAL PRIMARY KEY,
    lead_id INTEGER UNIQUE NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
    vehicle_type VARCHAR(100),
    license_required VARCHAR(20)
);
CREATE INDEX IF NOT EXISTS idx_driver_req_lead_id ON driver_requirements(lead_id);

-- 6. Security Guard Service Requirements
CREATE TABLE IF NOT EXISTS security_guard_requirements (
    id SERIAL PRIMARY KEY,
    lead_id INTEGER UNIQUE NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
    shift VARCHAR(50),
    site_type VARCHAR(50)
);
CREATE INDEX IF NOT EXISTS idx_guard_req_lead_id ON security_guard_requirements(lead_id);

-- Seed Initial Tenants for Multi-Tenancy
INSERT INTO organizations (name, slug)
VALUES
    ('HomeDesk Primary', 'homedesk'),
    ('Acme Facilities Group', 'acme')
ON CONFLICT (slug) DO NOTHING;
