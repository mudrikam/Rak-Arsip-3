-- Migration: 002_20260310_add_microstock_tables.sql
-- Date: 2026-03-10
-- Purpose: Add microstock platform management and upload status tracking per file.
-- Description: Adds microstock_platforms table to store platforms (Freepik, Shutterstock, etc.)
--              and file_microstock_status table to track the upload status of each file
--              on each platform. Status references the shared statuses table (Draft, Active, etc.).
-- DDL Summary:
--   CREATE TABLE microstock_platforms (id, name, url, description, note, created_at, updated_at)
--   CREATE TABLE file_microstock_status (id, file_id, platform_id, status_id, note, created_at, updated_at)
--   UNIQUE constraint on (file_id, platform_id) to prevent duplicate assignments.
-- Prerequisites: Migration 001_* must be applied first.

CREATE TABLE IF NOT EXISTS microstock_platforms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    platform_name TEXT NOT NULL UNIQUE,
    platform_url TEXT,
    platform_description TEXT,
    platform_note TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS file_microstock_status (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id INTEGER NOT NULL,
    platform_id INTEGER NOT NULL,
    status_id INTEGER NOT NULL,
    note TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(file_id, platform_id),
    FOREIGN KEY (file_id) REFERENCES files(id),
    FOREIGN KEY (platform_id) REFERENCES microstock_platforms(id),
    FOREIGN KEY (status_id) REFERENCES statuses(id)
);
