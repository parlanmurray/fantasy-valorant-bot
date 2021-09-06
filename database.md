# Database info

## Databases

### FantasyValDev

### FantasyValProd

## MySQL Database creation statements

### Fantasy teams tables

CREATE TABLE users
{
	discord_id VARCHAR(18) NOT NULL,
	fantasy_team_id INT UNIQUE,
	INDEX fantasy_team_id_ind (fantasy_team_id),
	CONSTRAINT fk_team_id FOREIGN KEY (fantasy_team_id) REFERENCES fantasy_teams(id) ON DELETE SET NULL ON UPDATE CASCADE,
	PRIMARY KEY (discord_id)
};

CREATE TABLE fantasy_teams
{
	id INT NOT NULL AUTO_INCREMENT,
	name VARCHAR(50) NOT NULL UNIQUE,
	abbrev VARCHAR(10) NOT NULL UNIQUE,
	player1 INT,
	player2 INT,
	player3 INT,
	player4 INT,
	player5 INT,
	flex INT,
	sub1 INT,
	sub2 INT,
	sub3 INT,
	sub4 INT,
	INDEX player1_ind (player1),
	CONSTRAINT fk_player1 FOREIGN KEY (player1) REFERENCES players(id) ON DELETE SET NULL ON UPDATE CASCADE,
	INDEX player2_ind (player2),
	CONSTRAINT fk_player2 FOREIGN KEY (player2) REFERENCES players(id) ON DELETE SET NULL ON UPDATE CASCADE,
	INDEX player3_ind (player3),
	CONSTRAINT fk_player3 FOREIGN KEY (player3) REFERENCES players(id) ON DELETE SET NULL ON UPDATE CASCADE,
	INDEX player4_ind (player4),
	CONSTRAINT fk_player4 FOREIGN KEY (player4) REFERENCES players(id) ON DELETE SET NULL ON UPDATE CASCADE,
	INDEX player5_ind (player5),
	CONSTRAINT fk_player5 FOREIGN KEY (player5) REFERENCES players(id) ON DELETE SET NULL ON UPDATE CASCADE,
	INDEX flex_ind (flex),
	CONSTRAINT fk_flex FOREIGN KEY (flex) REFERENCES players(id) ON DELETE SET NULL ON UPDATE CASCADE,
	INDEX sub1 (sub1),
	CONSTRAINT fk_sub1 FOREIGN KEY (sub1) REFERENCES players(id) ON DELETE SET NULL ON UPDATE CASCADE,
	INDEX sub2 (sub2),
	CONSTRAINT fk_sub2 FOREIGN KEY (sub2) REFERENCES players(id) ON DELETE SET NULL ON UPDATE CASCADE,
	INDEX sub3 (sub3),
	CONSTRAINT fk_sub3 FOREIGN KEY (sub3) REFERENCES players(id) ON DELETE SET NULL ON UPDATE CASCADE,
	INDEX sub4 (sub4),
	CONSTRAINT fk_sub4 FOREIGN KEY (sub4) REFERENCES players(id) ON DELETE SET NULL ON UPDATE CASCADE,
	PRIMARY KEY (id)
};

### Stats tables

CREATE TABLE teams 
(
	id INT NOT NULL AUTO_INCREMENT,
	name VARCHAR(20) NOT NULL UNIQUE,
	abbrev VARCHAR(10) NOT NULL UNIQUE,
	region VARCHAR(10) NOT NULL,
	PRIMARY KEY (id)
);

CREATE TABLE players
(
	id INT NOT NULL AUTO_INCREMENT,
	name VARCHAR(20) NOT NULL UNIQUE,
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
