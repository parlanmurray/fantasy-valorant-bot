-- Migration: 2.0
-- Adds H2H tables (seasons, weeks, matchups), week_id on results,
-- multi-stage (previous_season_id), multi-region (season_events).
-- player_fk already applied; idempotent via IF NOT EXISTS.

CREATE TABLE IF NOT EXISTS FantasyValDev.seasons
(
	id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
	name VARCHAR(100) NOT NULL,
	event_url VARCHAR(255) NOT NULL,
	num_weeks INT NOT NULL,
	is_active BOOLEAN NOT NULL DEFAULT FALSE,
	roster_locked BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS FantasyValProd.seasons
(
	id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
	name VARCHAR(100) NOT NULL,
	event_url VARCHAR(255) NOT NULL,
	num_weeks INT NOT NULL,
	is_active BOOLEAN NOT NULL DEFAULT FALSE,
	roster_locked BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS FantasyValDev.weeks
(
	id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
	season_id INT NOT NULL,
	week_number INT NOT NULL,
	FOREIGN KEY (season_id) REFERENCES FantasyValDev.seasons(id) ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE TABLE IF NOT EXISTS FantasyValProd.weeks
(
	id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
	season_id INT NOT NULL,
	week_number INT NOT NULL,
	FOREIGN KEY (season_id) REFERENCES FantasyValProd.seasons(id) ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE TABLE IF NOT EXISTS FantasyValDev.matchups
(
	id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
	week_id INT NOT NULL,
	home_team_id INT NOT NULL,
	away_team_id INT NULL,
	home_score FLOAT NOT NULL DEFAULT 0.0,
	away_score FLOAT NOT NULL DEFAULT 0.0,
	FOREIGN KEY (week_id) REFERENCES FantasyValDev.weeks(id) ON DELETE CASCADE ON UPDATE CASCADE,
	FOREIGN KEY (home_team_id) REFERENCES FantasyValDev.fantasy_teams(id) ON DELETE CASCADE ON UPDATE CASCADE,
	FOREIGN KEY (away_team_id) REFERENCES FantasyValDev.fantasy_teams(id) ON DELETE SET NULL ON UPDATE CASCADE
);

CREATE TABLE IF NOT EXISTS FantasyValProd.matchups
(
	id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
	week_id INT NOT NULL,
	home_team_id INT NOT NULL,
	away_team_id INT NULL,
	home_score FLOAT NOT NULL DEFAULT 0.0,
	away_score FLOAT NOT NULL DEFAULT 0.0,
	FOREIGN KEY (week_id) REFERENCES FantasyValProd.weeks(id) ON DELETE CASCADE ON UPDATE CASCADE,
	FOREIGN KEY (home_team_id) REFERENCES FantasyValProd.fantasy_teams(id) ON DELETE CASCADE ON UPDATE CASCADE,
	FOREIGN KEY (away_team_id) REFERENCES FantasyValProd.fantasy_teams(id) ON DELETE SET NULL ON UPDATE CASCADE
);

-- week_id on results (FK to weeks, nullable so existing rows are unaffected)
ALTER TABLE FantasyValDev.results
	ADD COLUMN IF NOT EXISTS week_id INT NULL,
	ADD CONSTRAINT fk_results_week_dev FOREIGN KEY (week_id) REFERENCES FantasyValDev.weeks(id) ON DELETE SET NULL ON UPDATE CASCADE;

ALTER TABLE FantasyValProd.results
	ADD COLUMN IF NOT EXISTS week_id INT NULL,
	ADD CONSTRAINT fk_results_week_prod FOREIGN KEY (week_id) REFERENCES FantasyValProd.weeks(id) ON DELETE SET NULL ON UPDATE CASCADE;

-- player_fk (already exists on live DBs; IF NOT EXISTS is a no-op)
ALTER TABLE FantasyValDev.results ADD COLUMN IF NOT EXISTS player_fk INT NULL;
ALTER TABLE FantasyValProd.results ADD COLUMN IF NOT EXISTS player_fk INT NULL;

-- rounds data (Ph3)
ALTER TABLE FantasyValDev.results ADD COLUMN IF NOT EXISTS rounds_played INT NULL;
ALTER TABLE FantasyValDev.results ADD COLUMN IF NOT EXISTS rounds_won INT NULL;
ALTER TABLE FantasyValDev.results ADD COLUMN IF NOT EXISTS team_won BOOLEAN NULL;

ALTER TABLE FantasyValProd.results ADD COLUMN IF NOT EXISTS rounds_played INT NULL;
ALTER TABLE FantasyValProd.results ADD COLUMN IF NOT EXISTS rounds_won INT NULL;
ALTER TABLE FantasyValProd.results ADD COLUMN IF NOT EXISTS team_won BOOLEAN NULL;

-- Multi-stage: previous_season_id on seasons
ALTER TABLE FantasyValDev.seasons
	ADD COLUMN IF NOT EXISTS previous_season_id INT NULL,
	ADD CONSTRAINT fk_prev_season_dev FOREIGN KEY (previous_season_id) REFERENCES FantasyValDev.seasons(id);

ALTER TABLE FantasyValProd.seasons
	ADD COLUMN IF NOT EXISTS previous_season_id INT NULL,
	ADD CONSTRAINT fk_prev_season_prod FOREIGN KEY (previous_season_id) REFERENCES FantasyValProd.seasons(id);

-- Multi-region: season_events
CREATE TABLE IF NOT EXISTS FantasyValDev.season_events (
	id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
	season_id INT NOT NULL,
	event_url VARCHAR(255) NOT NULL,
	FOREIGN KEY (season_id) REFERENCES FantasyValDev.seasons(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS FantasyValProd.season_events (
	id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
	season_id INT NOT NULL,
	event_url VARCHAR(255) NOT NULL,
	FOREIGN KEY (season_id) REFERENCES FantasyValProd.seasons(id) ON DELETE CASCADE
);

-- Role-based positions: rename captain/player1-5 → igl/duelist/initiator/controller/sentinel/flex
UPDATE FantasyValDev.positions SET position = 'igl'        WHERE id = 0;
UPDATE FantasyValDev.positions SET position = 'duelist'    WHERE id = 1;
UPDATE FantasyValDev.positions SET position = 'initiator'  WHERE id = 2;
UPDATE FantasyValDev.positions SET position = 'controller' WHERE id = 3;
UPDATE FantasyValDev.positions SET position = 'sentinel'   WHERE id = 4;
UPDATE FantasyValDev.positions SET position = 'flex'       WHERE id = 5;

UPDATE FantasyValProd.positions SET position = 'igl'        WHERE id = 0;
UPDATE FantasyValProd.positions SET position = 'duelist'    WHERE id = 1;
UPDATE FantasyValProd.positions SET position = 'initiator'  WHERE id = 2;
UPDATE FantasyValProd.positions SET position = 'controller' WHERE id = 3;
UPDATE FantasyValProd.positions SET position = 'sentinel'   WHERE id = 4;
UPDATE FantasyValProd.positions SET position = 'flex'       WHERE id = 5;
