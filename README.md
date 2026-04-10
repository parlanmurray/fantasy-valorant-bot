# fantasy-valorant-bot

Discord bot for fantasy league play on VCT (Valorant Champions Tour) esports. Users register fantasy teams, draft pro players via snake draft, and accumulate points based on real match stats scraped from vlr.gg.

## Setup

### Dependencies

Docker and Docker Compose.

### Secrets

Create the following files with their respective values:

| File | Contents |
|------|----------|
| `backend/discord_token.txt` | Discord bot token |
| `db/disc_password.txt` | MariaDB password for the app user (`discord`) |
| `db/root_password.txt` | MariaDB root password |

### Database

Initialize the database by running `db/scripts/init_db.sql` against the MariaDB container:

```sh
ROOT_PASS=$(cat db/root_password.txt)
docker exec -i fantasy-valorant-bot-db-1 mysql -u root -p"$ROOT_PASS" < db/scripts/init_db.sql
```

This creates `FantasyValDev` and `FantasyValProd` databases, all tables, and seeds the positions table.

## Startup

```sh
docker compose up -d
```

By default the bot connects to the dev database. Use `--prod` for production:

```sh
docker compose run backend python3 main.py --prod
```

### CLI Flags

| Flag | Description |
|------|-------------|
| `--prod` | Use production database (`FantasyValProd`) |
| `--skip-draft` | Start bot without initializing draft state |
| `-r / --rounds` | Number of draft rounds (default: 5) |
| `-s / --subs` | Number of sub slots (default: 4) |

## Bot Commands

### Registration & Setup
| Command | Description |
|---------|-------------|
| `!register <abbrev> <name>` | Register a fantasy team |
| `!roles` | Show role descriptions and bonuses |
| `!scoring` | Show scoring weights and role bonuses |
| `!rules` | Show league rules |

### Draft
| Command | Description |
|---------|-------------|
| `!draft <player>` | Draft a player during your turn |
| `!freeagents` | List undrafted players |

### Roster Management
| Command | Description |
|---------|-------------|
| `!roster` | View your roster with Base/Role/Total points |
| `!set <player> <role>` | Assign a player to a role slot |
| `!lockroster` | Lock your roster for the current week |

### Standings & Stats
| Command | Description |
|---------|-------------|
| `!standings` | League standings with role bonuses applied |
| `!matchup` | View current week's head-to-head matchup |
| `!info <player/team>` | Look up a pro player or team's stats |
| `!rankplayers` | Rank all players by fantasy points |

### Roles
Players are assigned to one of six role slots. Role assignment is manager-driven — no agent matching enforced.

| Role | Bonus |
|------|-------|
| IGL | +8.5 pts per map win |
| Duelist | +2.0 per first kill |
| Initiator | +1.0 per assist |
| Controller | +0.65 per assist, +0.35 per round survived |
| Sentinel | +0.40 per death (reduces penalty from -1.0 to -0.60) |
| Flex | No bonus |
