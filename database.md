# Database info

## Databases

### FantasyValDev

Development database.

### FantasyValProd

Production database.

## MySQL Database creation statements

### Stats tables

```sql
CREATE TABLE teams 
(
	id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
	name VARCHAR(50) NOT NULL UNIQUE,
	abbrev VARCHAR(10) NOT NULL UNIQUE,
	region VARCHAR(10)
);

CREATE TABLE players
(
	id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
	name VARCHAR(20) NOT NULL UNIQUE,
	team_id INT,
	CONSTRAINT fk_team FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE SET NULL ON UPDATE CASCADE
);

CREATE TABLE events
(
	id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
	name VARCHAR(80) NOT NULL
);

CREATE TABLE results
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
	FOREIGN KEY (event_id) REFERENCES events(id) ON UPDATE CASCADE ON DELETE CASCADE,
	FOREIGN KEY (player_id) REFERENCES players(id) ON UPDATE CASCADE ON DELETE CASCADE
);

### Fantasy teams tables

CREATE TABLE positions
(
	id INT NOT NULL PRIMARY KEY,
	position VARCHAR(20) NOT NULL UNIQUE
);

INSERT INTO positions (id, position)
VALUES
	(0, "captain"),
	(1, "player1"),
	(2, "player2"),
	(3, "player3"),
	(4, "player4"),
	(5, "player5"),
	(6, "sub1"),
	(7, "sub2"),
	(8, "sub3"),
	(9, "sub4");

CREATE TABLE fantasy_teams
(
	id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
	name VARCHAR(50) NOT NULL UNIQUE,
	abbrev VARCHAR(10) NOT NULL UNIQUE
);

CREATE TABLE users
(
	discord_id VARCHAR(18) NOT NULL PRIMARY KEY,
	fantasy_team_id INT UNIQUE,
	CONSTRAINT fk_team_id FOREIGN KEY (fantasy_team_id) REFERENCES fantasy_teams(id) ON DELETE SET NULL ON UPDATE CASCADE
);

CREATE TABLE fantasy_players
(
	id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
	player_id INT NOT NULL UNIQUE,
	fantasy_team_id INT,
	position INT,
	FOREIGN KEY (player_id) REFERENCES players(id) ON DELETE CASCADE ON UPDATE CASCADE,
	FOREIGN KEY (fantasy_team_id) REFERENCES fantasy_teams(id) ON DELETE SET NULL ON UPDATE CASCADE,
	FOREIGN KEY (position) REFERENCES positions(id) ON DELETE SET NULL ON UPDATE CASCADE
);
```

