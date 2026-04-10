-- Allow seasons to be created without an event URL
ALTER TABLE FantasyValDev.seasons MODIFY event_url VARCHAR(255) NULL;
ALTER TABLE FantasyValProd.seasons MODIFY event_url VARCHAR(255) NULL;
