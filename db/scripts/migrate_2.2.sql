-- Migration 2.2
-- Adds players.status, bot_config table, and weeks.is_closed
--
-- players.status and bot_config were applied directly to hestia during 2.2 dev;
-- included here for completeness. weeks.is_closed is new.

-- players.status
ALTER TABLE FantasyValDev.players
    ADD COLUMN IF NOT EXISTS status VARCHAR(20) NOT NULL DEFAULT 'active';

ALTER TABLE FantasyValProd.players
    ADD COLUMN IF NOT EXISTS status VARCHAR(20) NOT NULL DEFAULT 'active';

-- bot_config key/value store
CREATE TABLE IF NOT EXISTS FantasyValDev.bot_config (
    `key`   VARCHAR(64)  NOT NULL PRIMARY KEY,
    `value` VARCHAR(255) NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS FantasyValProd.bot_config (
    `key`   VARCHAR(64)  NOT NULL PRIMARY KEY,
    `value` VARCHAR(255) NOT NULL DEFAULT ''
);

-- weeks.is_closed: set by !closeweek; controls !matchup default week
ALTER TABLE FantasyValDev.weeks
    ADD COLUMN IF NOT EXISTS is_closed TINYINT(1) NOT NULL DEFAULT 0;

ALTER TABLE FantasyValProd.weeks
    ADD COLUMN IF NOT EXISTS is_closed TINYINT(1) NOT NULL DEFAULT 0;
