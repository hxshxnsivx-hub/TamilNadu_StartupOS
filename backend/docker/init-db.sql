-- Runs once on first container init (mounted into /docker-entrypoint-initdb.d).
-- Enables the extensions the schema depends on.
CREATE EXTENSION IF NOT EXISTS vector;    -- pgvector: embedding similarity
CREATE EXTENSION IF NOT EXISTS postgis;   -- geo blocking for B2B matching
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pgcrypto;  -- gen_random_uuid(), hashing
