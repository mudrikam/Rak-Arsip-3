-- Migration: 001_20251204_migration_init.sql
-- Date: 2025-12-04
-- Purpose: Move hardcoded database creation into a migration-driven
--          initialization process. This migration creates the initial
--          schema that was previously implemented directly in code
--          (table creation moved from db helper/connection logic to
--          SQL migration files). Keeping DDL in migrations ensures a
--          reproducible, versioned database schema and enables future
--          schema evolution using additional migration files.
-- Notes:
--  - This file must be applied first on a fresh installation.
--  - Do NOT remove this file after applying; it serves as a historical
--    record of the initial schema. If removed, the system will still
--    consider it applied when present in `schema_migrations` table.
--  - For changes, add new migration files (e.g. 002_..., 003_..., etc.)
--  - Migration process will create backups before applying each file
--    and restore on failure.
--
-- Critical files touched / changed when migrating to migration-driven init:
--  - `configs/db_config.json`
--      * Now contains only runtime settings (type/path/create_if_not_exists)
--      * New key: `migration_backup_retention_days` (integer, days)
--      * Table definitions were removed from this config and moved to migrations.
--  - `database/db_manager.py`
--      * Initializes `DatabaseMigrationHelper` and delegates schema creation to migrations.
--      * Holds references to helper classes and coordinates backup/migration flow.
--  - `database/db_helper/db_helper_connection.py`
--      * `ensure_database_exists()` updated: calls migration initializer instead of creating tables.
--      * `create_tables()` logic removed (moved to SQL migrations).
--  - `database/db_helper/db_helper_migration.py`
--      * New helper responsible for: finding migration files, applying them,
--        recording applied migrations (`schema_migrations`), backup before apply,
--        restoring on failure, and cleaning old migration backups.
--  - `database/db_helper/db_helper_backup.py`
--      * Added `create_migration_backup()` and `restore_backup()` used by migration helper.
--      * Export/import CSV logic refactored to be dynamic (reads actual DB schema via PRAGMA).
--      * Existing `.db` backup cleanup logic retained and adjusted to coexist with migration backups.
--  - `gui/windows/preferences_helper/preferences_helper_backup.py`
--      * UI relayout so CSV Export and Import are side-by-side.
--      * Uses the dynamic export/import (no hardcoded table lists).
--  - Other `database/db_helper/*.py` helpers
--      * May need to be reviewed if they assumed table existence at import time.
--      * Helper functions that access tables should acquire a DB connection at runtime
--        (the migration system ensures schema is present before normal operations).
--
-- Guidance / Risk notes:
--  - Keep migration files as the single source of truth for DDL; do not duplicate DDL in code.
--  - Do not delete migration files after applying; they are the audit/history of schema evolution.
--  - When adding migrations that alter existing tables, consider data migration steps and
--    include backups/verification in the SQL or as separate steps.
--  - Review any startup code that assumed a table existed at import time; move such checks
--    to runtime after migrations have run.

-- Suggested SQL Migration Header Documentation (fill when creating a new migration)
--  - Migration ID:       <numeric_prefix>_<YYYYMMDDHHMMSS>_<short_name>.sql
--  - Date:               YYYY-MM-DD
--  - Author:             Full Name <email@example.com>
--  - Purpose:            One-line summary of the change
--  - Description:        Short paragraph describing schema and/or data changes
--  - Affected Files:     Code/config files that need updates or attention
--  - DDL Summary:        List of tables/columns/indexes created, altered, or dropped
--  - Data Migration:     Any data transform/cleanup steps (if applicable)
--  - Rollback Steps:     How to undo this migration (if reversible) or notes about restore
--  - Backups:            Which backup(s) are created before applying (migration backup file name)
--  - Prerequisites:      Other migrations or environment conditions required
--  - Testing:            Minimal verification steps to confirm success after apply
--  - Notes:              Performance, locking, or compatibility considerations
--
-- Example (fill and keep with migration file):
-- Migration ID: 002_20251205_add_index_to_files.sql
-- Date: 2025-12-05
-- Author: Jane Developer <jane@example.com>
-- Purpose: Add index to speed up recent-file queries.
-- Description: Adds an index on `files(date)` to improve query performance for
--              recent-file lookups used by the UI list view. No schema changes
--              to columns; safe to apply online.
-- Affected Files: gui/widgets/main_list.py, database/db_helper/db_helper_connection.py
-- DDL Summary: CREATE INDEX IF NOT EXISTS idx_files_date ON files(date);
-- Data Migration: None.
-- Rollback Steps: DROP INDEX IF EXISTS idx_files_date;
-- Backups: migration_backup_<timestamp>_002_20251205_add_index_to_files.db created automatically.
-- Prerequisites: Migration 001_* must be applied first.
-- Testing: 1) Run `SELECT name FROM sqlite_master WHERE type='index' AND name='idx_files_date';`
--          2) Measure query time for recent-file query before/after on a test dataset.
-- Notes: Index creation can take time on large tables; consider creating during low-traffic window.

CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS subcategories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    FOREIGN KEY (category_id) REFERENCES categories(id)
);

CREATE TABLE IF NOT EXISTS statuses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    color TEXT,
    font_weight TEXT
);

CREATE TABLE IF NOT EXISTS templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    content TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    name TEXT NOT NULL,
    root TEXT NOT NULL,
    path TEXT NOT NULL,
    status_id INTEGER NOT NULL,
    category_id INTEGER,
    subcategory_id INTEGER,
    template_id INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (status_id) REFERENCES statuses(id),
    FOREIGN KEY (category_id) REFERENCES categories(id),
    FOREIGN KEY (subcategory_id) REFERENCES subcategories(id),
    FOREIGN KEY (template_id) REFERENCES templates(id)
);

CREATE TABLE IF NOT EXISTS teams (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    full_name TEXT NOT NULL,
    contact TEXT,
    address TEXT,
    email TEXT,
    phone TEXT,
    attendance_pin TEXT,
    profile_image TEXT,
    bank TEXT,
    account_number TEXT,
    account_holder TEXT,
    started_at DATETIME,
    added_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS attendance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    team_id INTEGER NOT NULL,
    date DATE NOT NULL,
    check_in DATETIME,
    check_out DATETIME,
    note TEXT,
    FOREIGN KEY (team_id) REFERENCES teams(id)
);

CREATE TABLE IF NOT EXISTS item_price (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id INTEGER NOT NULL UNIQUE,
    price REAL NOT NULL,
    currency TEXT NOT NULL,
    note TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (file_id) REFERENCES files(id)
);

CREATE TABLE IF NOT EXISTS earnings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    team_id INTEGER NOT NULL,
    item_price_id INTEGER NOT NULL,
    amount REAL NOT NULL,
    note TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (team_id) REFERENCES teams(id),
    FOREIGN KEY (item_price_id) REFERENCES item_price(id)
);

CREATE TABLE IF NOT EXISTS client (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_name TEXT NOT NULL,
    contact TEXT,
    links TEXT,
    status TEXT,
    note TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS file_client_price (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id INTEGER NOT NULL,
    item_price_id INTEGER NOT NULL,
    client_id INTEGER NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (file_id) REFERENCES files(id),
    FOREIGN KEY (item_price_id) REFERENCES item_price(id),
    FOREIGN KEY (client_id) REFERENCES client(id)
);

CREATE TABLE IF NOT EXISTS batch_list (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_number TEXT NOT NULL UNIQUE,
    client_id INTEGER NOT NULL,
    note TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (client_id) REFERENCES client(id)
);

CREATE TABLE IF NOT EXISTS file_client_batch (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_number TEXT NOT NULL,
    client_id INTEGER NOT NULL,
    file_id INTEGER NOT NULL,
    note TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (batch_number) REFERENCES batch_list(batch_number),
    FOREIGN KEY (client_id) REFERENCES client(id),
    FOREIGN KEY (file_id) REFERENCES files(id)
);

CREATE TABLE IF NOT EXISTS url_provider (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    status TEXT,
    email TEXT,
    password TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS file_url (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id INTEGER NOT NULL,
    provider_id INTEGER NOT NULL,
    url_value TEXT NOT NULL,
    note TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (file_id) REFERENCES files(id),
    FOREIGN KEY (provider_id) REFERENCES url_provider(id)
);

CREATE TABLE IF NOT EXISTS wallet_pockets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    pocket_type TEXT,
    icon TEXT,
    color TEXT,
    image TEXT,
    settings TEXT,
    note TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS wallet_cards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pocket_id INTEGER NOT NULL,
    card_name TEXT NOT NULL,
    card_number TEXT NOT NULL,
    card_type TEXT,
    vendor TEXT,
    issuer TEXT,
    status TEXT,
    virtual BOOLEAN DEFAULT 0,
    issue_date DATETIME,
    expiry_date DATETIME,
    holder_name TEXT,
    cvv TEXT,
    billing_address TEXT,
    phone TEXT,
    email TEXT,
    country TEXT,
    card_limit REAL,
    image TEXT,
    color TEXT,
    note TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (pocket_id) REFERENCES wallet_pockets(id)
);

CREATE TABLE IF NOT EXISTS wallet_categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    note TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS wallet_currency (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    symbol TEXT,
    note TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS wallet_transaction_statuses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    note TEXT,
    color TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS wallet_transaction_locations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    location_type TEXT,
    address TEXT,
    city TEXT,
    country TEXT,
    postal_code TEXT,
    online_url TEXT,
    contact TEXT,
    phone TEXT,
    email TEXT,
    status TEXT,
    image TEXT,
    description TEXT,
    rating REAL,
    note TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS wallet_transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pocket_id INTEGER NOT NULL,
    card_id INTEGER,
    destination_pocket_id INTEGER,
    category_id INTEGER,
    status_id INTEGER,
    currency_id INTEGER NOT NULL,
    location_id INTEGER,
    transaction_name TEXT NOT NULL,
    transaction_date DATETIME NOT NULL,
    transaction_type TEXT NOT NULL,
    tags TEXT,
    note TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (pocket_id) REFERENCES wallet_pockets(id),
    FOREIGN KEY (card_id) REFERENCES wallet_cards(id),
    FOREIGN KEY (destination_pocket_id) REFERENCES wallet_pockets(id),
    FOREIGN KEY (category_id) REFERENCES wallet_categories(id),
    FOREIGN KEY (status_id) REFERENCES wallet_transaction_statuses(id),
    FOREIGN KEY (currency_id) REFERENCES wallet_currency(id),
    FOREIGN KEY (location_id) REFERENCES wallet_transaction_locations(id)
);

CREATE TABLE IF NOT EXISTS wallet_transaction_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    wallet_transaction_id INTEGER NOT NULL,
    item_type TEXT NOT NULL,
    sku TEXT,
    item_name TEXT NOT NULL,
    item_description TEXT,
    quantity INTEGER DEFAULT 1,
    unit TEXT,
    amount REAL NOT NULL,
    width REAL,
    height REAL,
    depth REAL,
    weight REAL,
    material TEXT,
    color TEXT,
    file_url TEXT,
    license_key TEXT,
    expiry_date DATETIME,
    digital_type TEXT,
    note TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (wallet_transaction_id) REFERENCES wallet_transactions(id)
);

CREATE TABLE IF NOT EXISTS wallet_transactions_invoice_prove (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    wallet_transaction_id INTEGER NOT NULL,
    image_path TEXT NOT NULL,
    image_name TEXT,
    image_size INTEGER,
    image_type TEXT,
    description TEXT,
    uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (wallet_transaction_id) REFERENCES wallet_transactions(id)
);
