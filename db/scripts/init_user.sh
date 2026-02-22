#!/bin/bash
# Creates the discord DB user with the password from the mounted secret.
# Runs after init_db.sql (alphabetical order) so all tables exist first.
set -e

DISC_PASSWORD=$(cat /run/secrets/db-discord-password)

mysql -uroot -p"${MYSQL_ROOT_PASSWORD}" <<EOF
CREATE USER IF NOT EXISTS 'discord'@'%' IDENTIFIED BY '${DISC_PASSWORD}';
GRANT SELECT, INSERT, UPDATE, DELETE ON FantasyValDev.* TO 'discord'@'%';
GRANT SELECT, INSERT, UPDATE, DELETE ON FantasyValProd.* TO 'discord'@'%';
FLUSH PRIVILEGES;
EOF
