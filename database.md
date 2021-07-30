# Database info

## Databases

### FantasyValDev

### FantasyValProd

## MySQL Database creation statements

CREATE TABLE teams 
(
	id INT NOT NULL AUTO_INCREMENT,
	name VARCHAR(20) NOT NULL,
	abbrev VARCHAR(10) NOT NULL,
	region VARCHAR(10) NOT NULL,
	PRIMARY KEY (id)
);

CREATE TABLE players
(
	id INT NOT NULL AUTO_INCREMENT,
	name VARCHAR(20) NOT NULL,
	team_id INT,
	INDEX team_ind (team_id),
	CONSTRAINT fk_team FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE SET NULL ON UPDATE CASCADE,
	PRIMARY KEY (id)
);

CREATE TABLE events
(
	id INT NOT NULL AUTO_INCREMENT,
	name VARCHAR(50) NOT NULL,
	start_date DATE NOT NULL,
	PRIMARY KEY (id)
);

CREATE TABLE results
(
	id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
	map VARCHAR(10) NOT NULL,
	game_id INT NOT NULL,
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
	INDEX event_ind (event_id),
	INDEX player_ind (player_id),
	FOREIGN KEY (event_id) REFERENCES events(id) ON UPDATE CASCADE ON DELETE CASCADE,
	FOREIGN KEY (player_id) REFERENCES players(id) ON UPDATE CASCADE ON DELETE CASCADE
);
