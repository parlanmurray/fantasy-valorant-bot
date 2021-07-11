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
	CONSTRAINT fk_team
		FOREIGN KEY (team_id)
		REFERENCES teams(id)
		ON DELETE SET NULL
		ON UPDATE CASCADE,
	PRIMARY KEY (id)
);

CREATE TABLE players
(
	ID INT NOT NULL AUTO_INCREMENT,
	name VARCHAR(20) NOT NULL,
	team VARCHAR(10) NOT NULL,
	PRIMARY KEY (name)
);

CREATE TABLE events
(
	id INT NOT NULL AUTO_INCREMENT,
	name VARCHAR(50) NOT NULL,
	start_date DATE NOT NULL,
	PRIMARY KEY (id)
);

CREATE TABLE maps
(
	id INT NOT NULL AUTO_INCREMENT,
	map VARCHAR(10) NOT NULL,
	team1_id INT NOT NULL,
	player1_id INT NOT NULL,
	player1_acs FLOAT,
	player1_kills INT,
	player1_deaths INT,
	player1_assists INT,
	player1_2k INT,
	player1_3k INT,
	player1_4k INT,
	player1_5k INT,
	player1_clutch_v2 INT,
	player1_clutch_v3 INT,
	player1_clutch_v4 INT,
	player1_clutch_v5 INT,
	player2_id INT NOT NULL,
	player2_acs FLOAT,
	player2_kills INT,
	player2_deaths INT,
	player2_assists INT,
	player2_2k INT,
	player2_3k INT,
	player2_4k INT,
	player2_5k INT,
	player2_clutch_v2 INT,
	player2_clutch_v3 INT,
	player2_clutch_v4 INT,
	player2_clutch_v5 INT,
	player3_id INT NOT NULL,
	player3_acs FLOAT,
	player3_kills INT,
	player3_deaths INT,
	player3_assists INT,
	player3_2k INT,
	player3_3k INT,
	player3_4k INT,
	player3_5k INT,
	player3_clutch_v2 INT,
	player3_clutch_v3 INT,
	player3_clutch_v4 INT,
	player3_clutch_v5 INT,
	player4_id INT NOT NULL,
	player4_acs FLOAT,
	player4_kills INT,
	player4_deaths INT,
	player4_assists INT,
	player4_2k INT,
	player4_3k INT,
	player4_4k INT,
	player4_5k INT,
	player4_clutch_v2 INT,
	player4_clutch_v3 INT,
	player4_clutch_v4 INT,
	player4_clutch_v5 INT,
	player5_id INT NOT NULL,
	player5_acs FLOAT,
	player5_kills INT,
	player5_deaths INT,
	player5_assists INT,
	player5_2k INT,
	player5_3k INT,
	player5_4k INT,
	player5_5k INT,
	player5_clutch_v2 INT,
	player5_clutch_v3 INT,
	player5_clutch_v4 INT,
	player5_clutch_v5 INT,
	team2_id INT NOT NULL,
	player6_id INT NOT NULL,
	player6_acs FLOAT,
	player6_kills INT,
	player6_deaths INT,
	player6_assists INT,
	player6_2k INT,
	player6_3k INT,
	player6_4k INT,
	player6_5k INT,
	player6_clutch_v2 INT,
	player6_clutch_v3 INT,
	player6_clutch_v4 INT,
	player6_clutch_v5 INT,
	player7_id INT NOT NULL,
	player7_acs FLOAT,
	player7_kills INT,
	player7_deaths INT,
	player7_assists INT,
	player7_2k INT,
	player7_3k INT,
	player7_4k INT,
	player7_5k INT,
	player7_clutch_v2 INT,
	player7_clutch_v3 INT,
	player7_clutch_v4 INT,
	player7_clutch_v5 INT,
	player8_id INT NOT NULL,
	player8_acs FLOAT,
	player8_kills INT,
	player8_deaths INT,
	player8_assists INT,
	player8_2k INT,
	player8_3k INT,
	player8_4k INT,
	player8_5k INT,
	player8_clutch_v2 INT,
	player8_clutch_v3 INT,
	player8_clutch_v4 INT,
	player8_clutch_v5 INT,
	player9_id INT NOT NULL,
	player9_acs FLOAT,
	player9_kills INT,
	player9_deaths INT,
	player9_assists INT,
	player9_2k INT,
	player9_3k INT,
	player9_4k INT,
	player9_5k INT,
	player9_clutch_v2 INT,
	player9_clutch_v3 INT,
	player9_clutch_v4 INT,
	player9_clutch_v5 INT,
	player10_id INT NOT NULL,
	player10_acs FLOAT,
	player10_kills INT,
	player10_deaths INT,
	player10_assists INT,
	player10_2k INT,
	player10_3k INT,
	player10_4k INT,
	player10_5k INT,
	player10_clutch_v2 INT,
	player10_clutch_v3 INT,
	player10_clutch_v4 INT,
	player10_clutch_v5 INT,
	event_id INT,
	PRIMARY KEY (id),
	INDEX event_ind (event_id),
	INDEX team1_ind (team1_id),
	INDEX team2_ind (team2_id),
	INDEX player1_ind (player1_id),
	INDEX player2_ind (player2_id),
	INDEX player3_ind (player3_id),
	INDEX player4_ind (player4_id),
	INDEX player5_ind (player5_id),
	INDEX player6_ind (player6_id),
	INDEX player7_ind (player7_id),
	INDEX player8_ind (player8_id),
	INDEX player9_ind (player9_id),
	INDEX player10_ind (player10_id),
	CONSTRAINT fk_event
		FOREIGN KEY event_id,
		REFERENCES events(id)
		ON DELETE SET NULL,
	CONSTRAINT fk_team1
		FOREIGN KEY team1_id
		REFERENCES teams(id)
		ON DELETE SET NULL,
	CONSTRAINT fk_team2
		FOREIGN KEY team2_id
		REFERENCES teams(id)
		ON DELETE SET NULL,
	CONSTRAINT fk_player1
		FOREIGN KEY player1_id
		REFERENCES players(id)
		ON DELETE SET NULL,
	CONSTRAINT fk_player2
		FOREIGN KEY player2_id
		REFERENCES players(id)
		ON DELETE SET NULL,
	CONSTRAINT fk_player3
		FOREIGN KEY player3_id
		REFERENCES players(id)
		ON DELETE SET NULL,
	CONSTRAINT fk_player4
		FOREIGN KEY player4_id
		REFERENCES players(id)
		ON DELETE SET NULL,
	CONSTRAINT fk_player5
		FOREIGN KEY player5_id
		REFERENCES players(id)
		ON DELETE SET NULL,
	CONSTRAINT fk_player6
		FOREIGN KEY player6_id
		REFERENCES players(id)
		ON DELETE SET NULL,
	CONSTRAINT fk_player7
		FOREIGN KEY player7_id
		REFERENCES players(id)
		ON DELETE SET NULL,
	CONSTRAINT fk_player8
		FOREIGN KEY player8_id
		REFERENCES players(id)
		ON DELETE SET NULL,
	CONSTRAINT fk_player9
		FOREIGN KEY player9_id
		REFERENCES players(id)
		ON DELETE SET NULL,
	CONSTRAINT fk_player10
		FOREIGN KEY player10_id
		REFERENCES players(id)
		ON DELETE SET NULL
);
