#/bin/bash

export MARIADB_PASSWORD="$(cat /run/secrets/db-disc-password)"
export ROOT_PASSWORD="$(cat /run/secrets/db-root-password)"
mysql -u root --password=${ROOT_PASSWORD} <<-END
    CREATE USER IF NOT EXISTS 'discord'@'172.18.%' IDENTIFIED BY '${MARIADB_PASSWORD}';
END
