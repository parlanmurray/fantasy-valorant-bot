-- Migration: release/2.1
-- Remove redundant Season.event_url column (superseded by season_events table)

ALTER TABLE FantasyValDev.seasons DROP COLUMN event_url;
ALTER TABLE FantasyValProd.seasons DROP COLUMN event_url;

-- Roster snapshots: capture slot assignments at lockout time for historical !matchup accuracy
CREATE TABLE IF NOT EXISTS FantasyValDev.roster_snapshots
(
	id         INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
	week_id    INT NOT NULL,
	fteam_id   INT NOT NULL,
	player_id  INT NOT NULL,
	position   INT NOT NULL,
	FOREIGN KEY (week_id)   REFERENCES weeks(id) ON DELETE CASCADE ON UPDATE CASCADE,
	FOREIGN KEY (fteam_id)  REFERENCES fantasy_teams(id) ON DELETE CASCADE ON UPDATE CASCADE,
	FOREIGN KEY (player_id) REFERENCES players(id) ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE TABLE IF NOT EXISTS FantasyValProd.roster_snapshots
(
	id         INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
	week_id    INT NOT NULL,
	fteam_id   INT NOT NULL,
	player_id  INT NOT NULL,
	position   INT NOT NULL,
	FOREIGN KEY (week_id)   REFERENCES weeks(id) ON DELETE CASCADE ON UPDATE CASCADE,
	FOREIGN KEY (fteam_id)  REFERENCES fantasy_teams(id) ON DELETE CASCADE ON UPDATE CASCADE,
	FOREIGN KEY (player_id) REFERENCES players(id) ON DELETE CASCADE ON UPDATE CASCADE
);
