# fantasy-valorant-bot

## Setup

### Dependencies

Install dependencies.

```sh
pip install --upgrade setuptools
pip install -e .
```

May require sudo.

### Token

Create a file called `.env` in the root directory of this repository.

```sh
DISCORD_TOKEN="bot_token_here"
DATABASE_USER="database_user_here"
DATABASE_PASSWORD="database_password_here"
DATABASE_DEV='development_database_name_here'
DATABASE_PROD='production_database_name_here'
DATABASE_TYPE='database_type'
```

DATABASE_TYPE field is optional, only tested with mysql.

### Database

This project uses a mysql database for storing information. A configured database is assumed to be running on the same host as the discord app. Database table creation statements can be found in `database.md`. It is recommended to create a user for the app to use.

## Startup

From the project root, run:

```sh
python3 main.py
```
