-- HomeDesk Facility Management Portal - Production PostgreSQL Schema
-- Phase 2 Architecture: Normal User, Category-bound Organization, and Admin roles.
-- Requirements belong to a Category and a User, NOT directly to an Organization.

-- 1. Service Categories Table
CREATE TABLE IF NOT EXISTS categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    display_name VARCHAR(100),
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (NOW() AT TIME ZONE 'UTC') NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_categories_name ON categories(name);

-- 2. Organizations Table (Categorized Service Providers)
CREATE TABLE IF NOT EXISTS organizations (
    id SERIAL PRIMARY KEY,
    organization_name VARCHAR(100) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(120) UNIQUE,
    phone VARCHAR(20),
    password_hash VARCHAR(255),
    category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE RESTRICT,
    status VARCHAR(30) DEFAULT 'active' NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (NOW() AT TIME ZONE 'UTC') NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_organizations_slug ON organizations(slug);
CREATE INDEX IF NOT EXISTS idx_organizations_cat_id ON organizations(category_id);

-- 3. Users Table (Normal users, Org members, and Admins)
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    organization_id INTEGER REFERENCES organizations(id) ON DELETE SET NULL,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(120) UNIQUE,
    phone VARCHAR(20) NOT NULL,
    password_hash VARCHAR(255),
    role VARCHAR(30) DEFAULT 'user' NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (NOW() AT TIME ZONE 'UTC') NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_users_phone ON users(phone);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
CREATE INDEX IF NOT EXISTS idx_users_org_id ON users(organization_id);

-- 4. Customer Requirements Table
CREATE TABLE IF NOT EXISTS requirements (
    id SERIAL PRIMARY KEY,
    lead_id VARCHAR(30) UNIQUE NOT NULL,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE RESTRICT,
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
CREATE UNIQUE INDEX IF NOT EXISTS idx_requirements_lead_id ON requirements(lead_id);
CREATE INDEX IF NOT EXISTS idx_requirements_user_id ON requirements(user_id);
CREATE INDEX IF NOT EXISTS idx_requirements_cat_id ON requirements(category_id);
CREATE INDEX IF NOT EXISTS idx_requirements_mobile ON requirements(mobile);
CREATE INDEX IF NOT EXISTS idx_requirements_status ON requirements(status);

-- 5. Cook Service Specific Requirements
CREATE TABLE IF NOT EXISTS cook_requirements (
    id SERIAL PRIMARY KEY,
    requirement_id INTEGER UNIQUE NOT NULL REFERENCES requirements(id) ON DELETE CASCADE,
    cuisine_type VARCHAR(100),
    meals_per_day INTEGER
);
CREATE INDEX IF NOT EXISTS idx_cook_req_req_id ON cook_requirements(requirement_id);

-- 6. Driver Service Specific Requirements
CREATE TABLE IF NOT EXISTS driver_requirements (
    id SERIAL PRIMARY KEY,
    requirement_id INTEGER UNIQUE NOT NULL REFERENCES requirements(id) ON DELETE CASCADE,
    vehicle_type VARCHAR(100),
    license_required VARCHAR(20)
);
CREATE INDEX IF NOT EXISTS idx_driver_req_req_id ON driver_requirements(requirement_id);

-- 7. Security Guard Service Specific Requirements
CREATE TABLE IF NOT EXISTS security_guard_requirements (
    id SERIAL PRIMARY KEY,
    requirement_id INTEGER UNIQUE NOT NULL REFERENCES requirements(id) ON DELETE CASCADE,
    shift VARCHAR(50),
    site_type VARCHAR(50)
);
CREATE INDEX IF NOT EXISTS idx_guard_req_req_id ON security_guard_requirements(requirement_id);

-- Seed Categories
INSERT INTO categories (name, display_name)
VALUES
    ('COOK', 'Cook'),
    ('DRIVER', 'Driver'),
    ('SECURITY_GUARD', 'Security Guard')
ON CONFLICT (name) DO NOTHING;

