CREATE DATABASE FantasyValDev;
CREATE DATABASE FantasyValProd;

CREATE TABLE IF NOT EXISTS FantasyValDev.teams
(
	id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
	name VARCHAR(50) NOT NULL UNIQUE,
	abbrev VARCHAR(10) NOT NULL UNIQUE,
	region VARCHAR(10)
);

CREATE TABLE IF NOT EXISTS FantasyValProd.teams
(
	id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
	name VARCHAR(50) NOT NULL UNIQUE,
	abbrev VARCHAR(10) NOT NULL UNIQUE,
	region VARCHAR(10)
);

CREATE TABLE IF NOT EXISTS FantasyValDev.players
(
	id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
	name VARCHAR(20) NOT NULL UNIQUE,
	team_id INT,
	CONSTRAINT fk_team FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE SET NULL ON UPDATE CASCADE
);

CREATE TABLE IF NOT EXISTS FantasyValProd.players
(
	id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
	name VARCHAR(20) NOT NULL UNIQUE,
	team_id INT,
	CONSTRAINT fk_team FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE SET NULL ON UPDATE CASCADE
);

CREATE TABLE IF NOT EXISTS FantasyValDev.events
(
	id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
	name VARCHAR(80) NOT NULL
);

CREATE TABLE IF NOT EXISTS FantasyValProd.events
(
	id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
	name VARCHAR(80) NOT NULL
);

CREATE TABLE IF NOT EXISTS FantasyValDev.results
(
	id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
	map VARCHAR(20) NOT NULL,
	game_id INT NOT NULL,
	match_id INT NOT NULL,
	event_id INT,
	player_id INT NOT NULL,
	player_acs FLOAT,
	player_kills INT,
	player_deaths INT,
	player_assists INT,
	player_2k INT,
	player_3k INT,
	player_4k INT,
	player_5k INT,
	player_clutch_v2 INT,
	player_clutch_v3 INT,
	player_clutch_v4 INT,
	player_clutch_v5 INT,
	agent VARCHAR(20),
	FOREIGN KEY (event_id) REFERENCES events(id) ON UPDATE CASCADE ON DELETE CASCADE,
	FOREIGN KEY (player_id) REFERENCES players(id) ON UPDATE CASCADE ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS FantasyValProd.results
(
	id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
	map VARCHAR(20) NOT NULL,
	game_id INT NOT NULL,
	match_id INT NOT NULL,
	event_id INT,
	player_id INT NOT NULL,
	player_acs FLOAT,
	player_kills INT,
	player_deaths INT,
	player_assists INT,
	player_2k INT,
	player_3k INT,
	player_4k INT,
	player_5k INT,
	player_clutch_v2 INT,
	player_clutch_v3 INT,
	player_clutch_v4 INT,
	player_clutch_v5 INT,
	agent VARCHAR(20),
	FOREIGN KEY (event_id) REFERENCES events(id) ON UPDATE CASCADE ON DELETE CASCADE,
	FOREIGN KEY (player_id) REFERENCES players(id) ON UPDATE CASCADE ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS FantasyValDev.positions
(
	id INT NOT NULL PRIMARY KEY,
	position VARCHAR(20) NOT NULL UNIQUE
);

INSERT IGNORE INTO FantasyValDev.positions (id, position)
VALUES
	(0, "igl"),
	(1, "duelist"),
	(2, "initiator"),
	(3, "controller"),
	(4, "sentinel"),
	(5, "flex"),
	(6, "sub1"),
	(7, "sub2"),
	(8, "sub3"),
	(9, "sub4");

CREATE TABLE IF NOT EXISTS FantasyValProd.positions
(
	id INT NOT NULL PRIMARY KEY,
	position VARCHAR(20) NOT NULL UNIQUE
);

INSERT IGNORE INTO FantasyValProd.positions (id, position)
VALUES
	(0, "igl"),
	(1, "duelist"),
	(2, "initiator"),
	(3, "controller"),
	(4, "sentinel"),
	(5, "flex"),
	(6, "sub1"),
	(7, "sub2"),
	(8, "sub3"),
	(9, "sub4");

CREATE TABLE IF NOT EXISTS FantasyValDev.fantasy_teams
(
	id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
	name VARCHAR(50) NOT NULL UNIQUE,
	abbrev VARCHAR(10) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS FantasyValProd.fantasy_teams
(
	id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
	name VARCHAR(50) NOT NULL UNIQUE,
	abbrev VARCHAR(10) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS FantasyValDev.users
(
	discord_id VARCHAR(18) NOT NULL PRIMARY KEY,
	fantasy_team_id INT UNIQUE,
	CONSTRAINT fk_team_id FOREIGN KEY (fantasy_team_id) REFERENCES fantasy_teams(id) ON DELETE SET NULL ON UPDATE CASCADE
);

CREATE TABLE IF NOT EXISTS FantasyValProd.users
(
	discord_id VARCHAR(18) NOT NULL PRIMARY KEY,
	fantasy_team_id INT UNIQUE,
	CONSTRAINT fk_team_id FOREIGN KEY (fantasy_team_id) REFERENCES fantasy_teams(id) ON DELETE SET NULL ON UPDATE CASCADE
);

CREATE TABLE IF NOT EXISTS FantasyValDev.fantasy_players
(
	id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
	player_id INT NOT NULL UNIQUE,
	fantasy_team_id INT,
	position INT,
	FOREIGN KEY (player_id) REFERENCES players(id) ON DELETE CASCADE ON UPDATE CASCADE,
	FOREIGN KEY (fantasy_team_id) REFERENCES fantasy_teams(id) ON DELETE SET NULL ON UPDATE CASCADE,
	FOREIGN KEY (position) REFERENCES positions(id) ON DELETE SET NULL ON UPDATE CASCADE
);

CREATE TABLE IF NOT EXISTS FantasyValProd.fantasy_players
(
	id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
	player_id INT NOT NULL UNIQUE,
	fantasy_team_id INT,
	position INT,
	FOREIGN KEY (player_id) REFERENCES players(id) ON DELETE CASCADE ON UPDATE CASCADE,
	FOREIGN KEY (fantasy_team_id) REFERENCES fantasy_teams(id) ON DELETE SET NULL ON UPDATE CASCADE,
	FOREIGN KEY (position) REFERENCES positions(id) ON DELETE SET NULL ON UPDATE CASCADE
);

-- H2H: seasons, weeks, matchups; week_id on results

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
	FOREIGN KEY (season_id) REFERENCES seasons(id) ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE TABLE IF NOT EXISTS FantasyValProd.weeks
(
	id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
	season_id INT NOT NULL,
	week_number INT NOT NULL,
	FOREIGN KEY (season_id) REFERENCES seasons(id) ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE TABLE IF NOT EXISTS FantasyValDev.matchups
(
	id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
	week_id INT NOT NULL,
	home_team_id INT NOT NULL,
	away_team_id INT NULL,
	ghost_team_id INT NULL,
	home_score FLOAT NOT NULL DEFAULT 0.0,
	away_score FLOAT NOT NULL DEFAULT 0.0,
	FOREIGN KEY (week_id) REFERENCES weeks(id) ON DELETE CASCADE ON UPDATE CASCADE,
	FOREIGN KEY (home_team_id) REFERENCES fantasy_teams(id) ON DELETE CASCADE ON UPDATE CASCADE,
	FOREIGN KEY (away_team_id) REFERENCES fantasy_teams(id) ON DELETE SET NULL ON UPDATE CASCADE,
	FOREIGN KEY (ghost_team_id) REFERENCES fantasy_teams(id) ON DELETE SET NULL ON UPDATE CASCADE
);

CREATE TABLE IF NOT EXISTS FantasyValProd.matchups
(
	id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
	week_id INT NOT NULL,
	home_team_id INT NOT NULL,
	away_team_id INT NULL,
	ghost_team_id INT NULL,
	home_score FLOAT NOT NULL DEFAULT 0.0,
	away_score FLOAT NOT NULL DEFAULT 0.0,
	FOREIGN KEY (week_id) REFERENCES weeks(id) ON DELETE CASCADE ON UPDATE CASCADE,
	FOREIGN KEY (home_team_id) REFERENCES fantasy_teams(id) ON DELETE CASCADE ON UPDATE CASCADE,
	FOREIGN KEY (away_team_id) REFERENCES fantasy_teams(id) ON DELETE SET NULL ON UPDATE CASCADE,
	FOREIGN KEY (ghost_team_id) REFERENCES fantasy_teams(id) ON DELETE SET NULL ON UPDATE CASCADE
);

ALTER TABLE FantasyValDev.results ADD COLUMN IF NOT EXISTS week_id INT NULL,
	ADD CONSTRAINT fk_results_week FOREIGN KEY (week_id) REFERENCES weeks(id) ON DELETE SET NULL ON UPDATE CASCADE;

ALTER TABLE FantasyValProd.results ADD COLUMN IF NOT EXISTS week_id INT NULL,
	ADD CONSTRAINT fk_results_week FOREIGN KEY (week_id) REFERENCES weeks(id) ON DELETE SET NULL ON UPDATE CASCADE;

ALTER TABLE FantasyValDev.results ADD COLUMN IF NOT EXISTS player_fk INT NULL;
ALTER TABLE FantasyValProd.results ADD COLUMN IF NOT EXISTS player_fk INT NULL;

ALTER TABLE FantasyValDev.results ADD COLUMN IF NOT EXISTS rounds_played INT NULL;
ALTER TABLE FantasyValDev.results ADD COLUMN IF NOT EXISTS rounds_won INT NULL;
ALTER TABLE FantasyValDev.results ADD COLUMN IF NOT EXISTS team_won BOOLEAN NULL;

ALTER TABLE FantasyValProd.results ADD COLUMN IF NOT EXISTS rounds_played INT NULL;
ALTER TABLE FantasyValProd.results ADD COLUMN IF NOT EXISTS rounds_won INT NULL;
ALTER TABLE FantasyValProd.results ADD COLUMN IF NOT EXISTS team_won BOOLEAN NULL;

-- Multi-stage: link Stage 2 back to Stage 1
ALTER TABLE FantasyValDev.seasons
	ADD COLUMN IF NOT EXISTS previous_season_id INT NULL,
	ADD CONSTRAINT fk_prev_season_dev FOREIGN KEY (previous_season_id) REFERENCES seasons(id);

ALTER TABLE FantasyValProd.seasons
	ADD COLUMN IF NOT EXISTS previous_season_id INT NULL,
	ADD CONSTRAINT fk_prev_season_prod FOREIGN KEY (previous_season_id) REFERENCES seasons(id);

-- Multi-region: map a season to one or more VCT event URLs
CREATE TABLE IF NOT EXISTS FantasyValDev.season_events (
	id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
	season_id INT NOT NULL,
	event_url VARCHAR(255) NOT NULL,
	FOREIGN KEY (season_id) REFERENCES seasons(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS FantasyValProd.season_events (
	id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
	season_id INT NOT NULL,
	event_url VARCHAR(255) NOT NULL,
	FOREIGN KEY (season_id) REFERENCES seasons(id) ON DELETE CASCADE
);

