-- Migration: release/2.1
-- Remove redundant Season.event_url column (superseded by season_events table)

ALTER TABLE FantasyValDev.seasons DROP COLUMN event_url;
ALTER TABLE FantasyValProd.seasons DROP COLUMN event_url;
