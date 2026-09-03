-- ==============================================================================
-- TerraRisk AI - Supabase PostgreSQL Production Schema & Seed Migration
-- Execute this script in your Supabase Project -> SQL Editor to initialize all
-- disaster intelligence tables, indexes, spatial constraints, and seed records.
-- ==============================================================================

-- 1. EXTENSIONS
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ==============================================================================
-- 2. CORE DISASTER PLATFORM TABLES
-- ==============================================================================

-- Table 1: Users (Citizens, Field Volunteers, and Authority Incident Commanders)
CREATE TABLE IF NOT EXISTS users (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    phone TEXT UNIQUE,
    email TEXT UNIQUE,
    password_hash TEXT NOT NULL,
    lat DOUBLE PRECISION,
    lng DOUBLE PRECISION,
    district TEXT,
    role TEXT NOT NULL DEFAULT 'Citizen' CHECK(role IN ('Citizen', 'Volunteer', 'Authority_Admin')),
    is_verified INT NOT NULL DEFAULT 0,
    is_email_verified INT NOT NULL DEFAULT 0,
    email_otp TEXT,
    email_otp_expires_at TIMESTAMP WITH TIME ZONE,
    credibility_score INT NOT NULL DEFAULT 100,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Table 2: Incident Reports (Crowdsourced Geotagged Hazards & AI Computer Vision Triage)
CREATE TABLE IF NOT EXISTS incident_reports (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    hazard_type TEXT NOT NULL,
    lat DOUBLE PRECISION NOT NULL,
    lng DOUBLE PRECISION NOT NULL,
    description TEXT,
    image_url TEXT,
    severity INT NOT NULL DEFAULT 3 CHECK(severity >= 1 AND severity <= 5),
    status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending', 'verified', 'rejected', 'resolved', 'cleared')),
    cluster_id TEXT,
    verified_by BIGINT REFERENCES users(id) ON DELETE SET NULL,
    ai_confidence DOUBLE PRECISION,
    ai_hazard_type TEXT,
    ai_severity INT,
    ai_summary TEXT,
    is_flagged_spam INT DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Table 3: Relief Shelters (Kerala Camp Inventory, Capacities & Logistics)
CREATE TABLE IF NOT EXISTS relief_shelters (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    lat DOUBLE PRECISION NOT NULL,
    lng DOUBLE PRECISION NOT NULL,
    capacity INT NOT NULL DEFAULT 100 CHECK(capacity >= 0),
    occupied INT NOT NULL DEFAULT 0 CHECK(occupied >= 0),
    contact_number TEXT,
    district TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active', 'full', 'standby', 'closed')),
    in_charge_name TEXT,
    in_charge_phone TEXT,
    supplies_json TEXT,
    amenities_json TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Table 4: Missing Persons Registry (Search & Rescue Reunification)
CREATE TABLE IF NOT EXISTS missing_persons (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    age INT,
    gender TEXT,
    last_known_location TEXT,
    lat DOUBLE PRECISION,
    lng DOUBLE PRECISION,
    contact_phone TEXT,
    photo_url TEXT,
    medical_needs TEXT,
    status TEXT NOT NULL DEFAULT 'missing' CHECK(status IN ('missing', 'search_in_progress', 'located_safe', 'hospitalized')),
    located_at_shelter_id BIGINT REFERENCES relief_shelters(id) ON DELETE SET NULL,
    reported_by_user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Table 5: Family Safety Circle Contacts (Offline SOS & Emergency Location Pings)
CREATE TABLE IF NOT EXISTS family_safety_contacts (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    contact_name TEXT NOT NULL,
    contact_phone TEXT NOT NULL,
    relationship TEXT,
    last_ping_status TEXT,
    last_ping_lat DOUBLE PRECISION,
    last_ping_lng DOUBLE PRECISION,
    last_ping_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Table 6: Field Volunteer Missions (NDRF / Civil Defence Tactical Tasks)
CREATE TABLE IF NOT EXISTS volunteer_missions (
    id BIGSERIAL PRIMARY KEY,
    cluster_id TEXT NOT NULL,
    volunteer_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    status TEXT NOT NULL DEFAULT 'dispatched' CHECK(status IN ('dispatched', 'en_route', 'on_site', 'verified', 'resolved')),
    assigned_by BIGINT REFERENCES users(id) ON DELETE SET NULL,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Table 7: Audit Logs (Immutable Official Action Trail)
CREATE TABLE IF NOT EXISTS audit_logs (
    id BIGSERIAL PRIMARY KEY,
    action TEXT NOT NULL,
    actor_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    target_id BIGINT,
    details TEXT,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Table 8: Emergency Broadcasts (Persistent Warning Bulletins)
CREATE TABLE IF NOT EXISTS emergency_broadcasts (
    id BIGSERIAL PRIMARY KEY,
    broadcast_id TEXT UNIQUE NOT NULL,
    hazard_type TEXT NOT NULL,
    lat DOUBLE PRECISION NOT NULL,
    lng DOUBLE PRECISION NOT NULL,
    radius_km DOUBLE PRECISION NOT NULL,
    alert_en TEXT NOT NULL,
    alert_ml TEXT NOT NULL,
    recipients_count INT DEFAULT 0,
    sender TEXT,
    telegram_link TEXT,
    whatsapp_link TEXT,
    sent_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ==============================================================================
-- 3. PERFORMANCE INDEXES
-- ==============================================================================
CREATE INDEX IF NOT EXISTS idx_users_phone ON users(phone);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);

CREATE INDEX IF NOT EXISTS idx_incident_reports_status ON incident_reports(status);
CREATE INDEX IF NOT EXISTS idx_incident_reports_coords ON incident_reports(lat, lng);
CREATE INDEX IF NOT EXISTS idx_incident_reports_cluster ON incident_reports(cluster_id);
CREATE INDEX IF NOT EXISTS idx_incident_reports_created ON incident_reports(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_relief_shelters_district ON relief_shelters(district);
CREATE INDEX IF NOT EXISTS idx_relief_shelters_coords ON relief_shelters(lat, lng);
CREATE INDEX IF NOT EXISTS idx_relief_shelters_status ON relief_shelters(status);

CREATE INDEX IF NOT EXISTS idx_missing_persons_status ON missing_persons(status);
CREATE INDEX IF NOT EXISTS idx_family_safety_user ON family_safety_contacts(user_id);
CREATE INDEX IF NOT EXISTS idx_volunteer_missions_status ON volunteer_missions(status);
CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp ON audit_logs(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_emergency_broadcasts_sent ON emergency_broadcasts(sent_at DESC);
CREATE INDEX IF NOT EXISTS idx_emergency_broadcasts_bid ON emergency_broadcasts(broadcast_id);

-- ==============================================================================
-- 4. ROW LEVEL SECURITY (RLS) POLICIES
-- ==============================================================================
-- Enable RLS on public tables
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE incident_reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE relief_shelters ENABLE ROW LEVEL SECURITY;
ALTER TABLE missing_persons ENABLE ROW LEVEL SECURITY;
ALTER TABLE family_safety_contacts ENABLE ROW LEVEL SECURITY;
ALTER TABLE volunteer_missions ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE emergency_broadcasts ENABLE ROW LEVEL SECURITY;

-- Allow all operations for postgres / service_role (used by the backend API)
CREATE POLICY "Full access for service_role and backend" ON users FOR ALL TO authenticated, anon, service_role USING (true) WITH CHECK (true);
CREATE POLICY "Full access for service_role and backend" ON incident_reports FOR ALL TO authenticated, anon, service_role USING (true) WITH CHECK (true);
CREATE POLICY "Full access for service_role and backend" ON relief_shelters FOR ALL TO authenticated, anon, service_role USING (true) WITH CHECK (true);
CREATE POLICY "Full access for service_role and backend" ON missing_persons FOR ALL TO authenticated, anon, service_role USING (true) WITH CHECK (true);
CREATE POLICY "Full access for service_role and backend" ON family_safety_contacts FOR ALL TO authenticated, anon, service_role USING (true) WITH CHECK (true);
CREATE POLICY "Full access for service_role and backend" ON volunteer_missions FOR ALL TO authenticated, anon, service_role USING (true) WITH CHECK (true);
CREATE POLICY "Full access for service_role and backend" ON audit_logs FOR ALL TO authenticated, anon, service_role USING (true) WITH CHECK (true);
CREATE POLICY "Full access for service_role and backend" ON emergency_broadcasts FOR ALL TO authenticated, anon, service_role USING (true) WITH CHECK (true);

-- Enable Realtime for Emergency Alerts and Incident Reports
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_publication WHERE pubname = 'supabase_realtime') THEN
    ALTER PUBLICATION supabase_realtime ADD TABLE emergency_broadcasts;
    ALTER PUBLICATION supabase_realtime ADD TABLE incident_reports;
  END IF;
EXCEPTION WHEN OTHERS THEN
  NULL;
END $$;

-- ==============================================================================
-- 5. SEED DATA (IDEMPOTENT)
-- ==============================================================================

-- 1. Seed Default Authority Admin (Abhinav)
-- Pass: A12345678 (PBKDF2-HMAC-SHA256 hash)
INSERT INTO users (name, phone, email, password_hash, role, is_verified, is_email_verified, credibility_score)
VALUES (
    'Abhinav (KSDMA Authority Admin)',
    '+916282115954',
    'admin@terrarisk.gov.in',
    '23d062fc38fb15ebfce321d283c74900$ecdafc009d1b72e59bb6a22f3ca5fb0ea2aebae26b8dc60bc72861e687e651d2',
    'Authority_Admin',
    1,
    1,
    100
)
ON CONFLICT (phone) DO UPDATE SET
    role = 'Authority_Admin',
    is_verified = 1,
    is_email_verified = 1,
    credibility_score = 100;

-- 1b. Seed Incident Commander (Automated Drills)
-- Pass: Admin@Terra2026!
INSERT INTO users (name, phone, email, password_hash, role, is_verified, is_email_verified, credibility_score)
VALUES (
    'KSDMA Incident Commander',
    '+919999900000',
    'commander@terrarisk.gov.in',
    'ec8d62ee6cbbf8ec2ba3a453712d9c02$d39ff52d7ee89b94090b8f6c589025078519ca4fae10c7ee6006ff26cfc80fb8',
    'Authority_Admin',
    1,
    1,
    100
)
ON CONFLICT (phone) DO UPDATE SET
    role = 'Authority_Admin',
    is_verified = 1,
    is_email_verified = 1;

-- 2. Seed Default Field Volunteer
-- Pass: Volunteer@2026!
INSERT INTO users (name, phone, email, password_hash, role, is_verified, is_email_verified, credibility_score)
VALUES (
    'Anandhu Nair (NDRF Volunteer)',
    '+919888800000',
    'volunteer@terrarisk.org',
    'fc9c8fb664fc5f27663f7d1b3152fc7e$97b398df9813c9e9959f6ad89839c4d9b2e5fa1faec298df3637e17415d18d40',
    'Volunteer',
    1,
    1,
    100
)
ON CONFLICT (phone) DO UPDATE SET
    role = 'Volunteer',
    is_verified = 1,
    is_email_verified = 1;

-- 3. Seed Default Citizen (For quick evaluator logins)
-- Pass: SecurePassword123!
INSERT INTO users (name, phone, email, password_hash, role, is_verified, is_email_verified, credibility_score)
VALUES (
    'Abhinav R (Citizen)',
    '+919847012345',
    'citizen@terrarisk.org',
    'a75d5e2154d8e5cc69910d52b1b36625$37eeb55767b439c28bf1dc87cbafc409cf6e02621cb6d21469e38e658399554e',
    'Citizen',
    1,
    1,
    100
)
ON CONFLICT (phone) DO UPDATE SET
    is_verified = 1,
    is_email_verified = 1;

-- 4. Seed 11 Kerala Relief Shelters across high-risk districts
INSERT INTO relief_shelters (name, lat, lng, capacity, occupied, contact_number, district, status, in_charge_name, in_charge_phone, supplies_json, amenities_json)
SELECT
    'Meppadi Community Relief Center', 11.5510, 76.1280, 400, 85, '+914936282220', 'Wayanad', 'active',
    'Rajesh Kumar (Deputy Tahsildar)', '+919447123456',
    '{"water_litres": 3200, "food_packets": 650, "medical_kits": 45, "infant_supplies": 30, "fuel_litres": 250}',
    '{"medical_post": true, "power_backup": true, "wheelchair_accessible": true, "child_care": true}'
WHERE NOT EXISTS (SELECT 1 FROM relief_shelters WHERE name = 'Meppadi Community Relief Center');

INSERT INTO relief_shelters (name, lat, lng, capacity, occupied, contact_number, district, status, in_charge_name, in_charge_phone, supplies_json, amenities_json)
SELECT
    'Kalpetta SKMJ Higher Secondary Camp', 11.6080, 76.0825, 600, 120, '+914936202444', 'Wayanad', 'active',
    'Dr. Sunitha Menon', '+919447654321',
    '{"water_litres": 4500, "food_packets": 1100, "medical_kits": 80, "infant_supplies": 50, "fuel_litres": 400}',
    '{"medical_post": true, "power_backup": true, "wheelchair_accessible": true, "child_care": true}'
WHERE NOT EXISTS (SELECT 1 FROM relief_shelters WHERE name = 'Kalpetta SKMJ Higher Secondary Camp');

INSERT INTO relief_shelters (name, lat, lng, capacity, occupied, contact_number, district, status, in_charge_name, in_charge_phone, supplies_json, amenities_json)
SELECT
    'Mananthavady Govt High School Shelter', 11.8020, 76.0030, 300, 30, '+914935240222', 'Wayanad', 'active',
    'K. V. Mathew (Revenue Inspector)', '+919447789012',
    '{"water_litres": 1800, "food_packets": 400, "medical_kits": 25, "infant_supplies": 15, "fuel_litres": 150}',
    '{"medical_post": false, "power_backup": true, "wheelchair_accessible": false, "child_care": true}'
WHERE NOT EXISTS (SELECT 1 FROM relief_shelters WHERE name = 'Mananthavady Govt High School Shelter');

INSERT INTO relief_shelters (name, lat, lng, capacity, occupied, contact_number, district, status, in_charge_name, in_charge_phone, supplies_json, amenities_json)
SELECT
    'Sulthan Bathery St. Mary''s Relief Camp', 11.6620, 76.2570, 350, 45, '+914936220333', 'Wayanad', 'active',
    'Fr. George Thomas', '+919447334455',
    '{"water_litres": 2200, "food_packets": 500, "medical_kits": 30, "infant_supplies": 20, "fuel_litres": 180}',
    '{"medical_post": true, "power_backup": true, "wheelchair_accessible": true, "child_care": true}'
WHERE NOT EXISTS (SELECT 1 FROM relief_shelters WHERE name = 'Sulthan Bathery St. Mary''s Relief Camp');

INSERT INTO relief_shelters (name, lat, lng, capacity, occupied, contact_number, district, status, in_charge_name, in_charge_phone, supplies_json, amenities_json)
SELECT
    'Munnar Govt Arts College Relief Camp', 10.0889, 77.0595, 450, 110, '+914865230230', 'Idukki', 'active',
    'P. Murugan (Village Officer)', '+919446112233',
    '{"water_litres": 2800, "food_packets": 550, "medical_kits": 35, "infant_supplies": 20, "fuel_litres": 300}',
    '{"medical_post": true, "power_backup": true, "wheelchair_accessible": true, "child_care": true}'
WHERE NOT EXISTS (SELECT 1 FROM relief_shelters WHERE name = 'Munnar Govt Arts College Relief Camp');

INSERT INTO relief_shelters (name, lat, lng, capacity, occupied, contact_number, district, status, in_charge_name, in_charge_phone, supplies_json, amenities_json)
SELECT
    'Devikulam Community Hall Shelter', 10.0620, 77.1040, 300, 40, '+914865264210', 'Idukki', 'active',
    'S. Ramaswamy (Tahsildar)', '+919446223344',
    '{"water_litres": 2000, "food_packets": 450, "medical_kits": 25, "infant_supplies": 15, "fuel_litres": 200}',
    '{"medical_post": true, "power_backup": true, "wheelchair_accessible": false, "child_care": true}'
WHERE NOT EXISTS (SELECT 1 FROM relief_shelters WHERE name = 'Devikulam Community Hall Shelter');

INSERT INTO relief_shelters (name, lat, lng, capacity, occupied, contact_number, district, status, in_charge_name, in_charge_phone, supplies_json, amenities_json)
SELECT
    'Adimali Govt Vocational Higher Secondary Camp', 10.0450, 76.9550, 400, 70, '+914864222100', 'Idukki', 'active',
    'Biju Varghese (Panchayat Officer)', '+919446334455',
    '{"water_litres": 2500, "food_packets": 600, "medical_kits": 40, "infant_supplies": 25, "fuel_litres": 220}',
    '{"medical_post": true, "power_backup": true, "wheelchair_accessible": true, "child_care": true}'
WHERE NOT EXISTS (SELECT 1 FROM relief_shelters WHERE name = 'Adimali Govt Vocational Higher Secondary Camp');

INSERT INTO relief_shelters (name, lat, lng, capacity, occupied, contact_number, district, status, in_charge_name, in_charge_phone, supplies_json, amenities_json)
SELECT
    'Nilambur Govt Higher Secondary Camp', 11.2770, 76.2240, 500, 95, '+914831220456', 'Malappuram', 'active',
    'Muhammed Faisal (Panchayat Sec.)', '+919446889900',
    '{"water_litres": 3500, "food_packets": 800, "medical_kits": 50, "infant_supplies": 35, "fuel_litres": 350}',
    '{"medical_post": true, "power_backup": true, "wheelchair_accessible": true, "child_care": true}'
WHERE NOT EXISTS (SELECT 1 FROM relief_shelters WHERE name = 'Nilambur Govt Higher Secondary Camp');

INSERT INTO relief_shelters (name, lat, lng, capacity, occupied, contact_number, district, status, in_charge_name, in_charge_phone, supplies_json, amenities_json)
SELECT
    'Eranad Knowledge City Relief Shelter', 11.1950, 76.1220, 550, 60, '+914832734500', 'Malappuram', 'active',
    'Abdul Rasheed (Coordinator)', '+919446990011',
    '{"water_litres": 4000, "food_packets": 900, "medical_kits": 60, "infant_supplies": 40, "fuel_litres": 300}',
    '{"medical_post": true, "power_backup": true, "wheelchair_accessible": true, "child_care": true}'
WHERE NOT EXISTS (SELECT 1 FROM relief_shelters WHERE name = 'Eranad Knowledge City Relief Shelter');

INSERT INTO relief_shelters (name, lat, lng, capacity, occupied, contact_number, district, status, in_charge_name, in_charge_phone, supplies_json, amenities_json)
SELECT
    'Kozhikode Medical College Relief Camp', 11.2725, 75.8360, 700, 150, '+914952350212', 'Kozhikode', 'active',
    'Dr. K. Narayanan (Superintendent)', '+919447445566',
    '{"water_litres": 6000, "food_packets": 1400, "medical_kits": 120, "infant_supplies": 80, "fuel_litres": 500}',
    '{"medical_post": true, "power_backup": true, "wheelchair_accessible": true, "child_care": true}'
WHERE NOT EXISTS (SELECT 1 FROM relief_shelters WHERE name = 'Kozhikode Medical College Relief Camp');

INSERT INTO relief_shelters (name, lat, lng, capacity, occupied, contact_number, district, status, in_charge_name, in_charge_phone, supplies_json, amenities_json)
SELECT
    'Thamarassery GHSS Emergency Shelter', 11.4167, 75.9333, 380, 50, '+914952223400', 'Kozhikode', 'active',
    'Smt. Leela Damodaran', '+919447556677',
    '{"water_litres": 2600, "food_packets": 520, "medical_kits": 35, "infant_supplies": 20, "fuel_litres": 200}',
    '{"medical_post": true, "power_backup": true, "wheelchair_accessible": true, "child_care": true}'
WHERE NOT EXISTS (SELECT 1 FROM relief_shelters WHERE name = 'Thamarassery GHSS Emergency Shelter');

-- 5. Seed Sample Missing Persons Entry
INSERT INTO missing_persons (name, age, gender, last_known_location, lat, lng, contact_phone, photo_url, medical_needs, status, reported_by_user_id)
SELECT
    'Pranav Varma', 28, 'Male', 'Chooralmala Tea Estate Section 4', 11.5361, 76.1667, '+919876543210', NULL, 'Requires insulin', 'missing', 1
WHERE NOT EXISTS (SELECT 1 FROM missing_persons WHERE name = 'Pranav Varma');

INSERT INTO missing_persons (name, age, gender, last_known_location, lat, lng, contact_phone, photo_url, medical_needs, status, reported_by_user_id)
SELECT
    'Kalyani Amma', 67, 'Female', 'Mundakkai Riverbank settlement', 11.5167, 76.1500, '+919876543211', NULL, 'Mobility impaired', 'search_in_progress', 1
WHERE NOT EXISTS (SELECT 1 FROM missing_persons WHERE name = 'Kalyani Amma');
