# fantasy-valorant-bot

## Setup

### Dependencies

Docker

### secrets

Put discord token in `backend/discord-token.txt` and database password in `db/password.txt`.

### Database

This project uses a mysql database for storing information. the `db` service has a databse you will need to configure. Database table creation statements can be found in `database.md`. It is recommended to create a user for the app to use.

## Startup

From the project root, run:

```sh
docker compose up -d
```
