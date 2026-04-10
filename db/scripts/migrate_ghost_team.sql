-- Migration: add ghost_team_id to matchups table
-- Tracks which real team the ghost matchup mirrors (odd-team-out leagues)

ALTER TABLE FantasyValDev.matchups
    ADD COLUMN IF NOT EXISTS ghost_team_id INT NULL,
    ADD CONSTRAINT fk_matchups_ghost_dev
        FOREIGN KEY (ghost_team_id) REFERENCES fantasy_teams(id) ON DELETE SET NULL ON UPDATE CASCADE;

ALTER TABLE FantasyValProd.matchups
    ADD COLUMN IF NOT EXISTS ghost_team_id INT NULL,
    ADD CONSTRAINT fk_matchups_ghost_prod
        FOREIGN KEY (ghost_team_id) REFERENCES fantasy_teams(id) ON DELETE SET NULL ON UPDATE CASCADE;
