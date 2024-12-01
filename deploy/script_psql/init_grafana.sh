#!/bin/bash

echo "Start created database $GRAFANA_PSQL_DB with user"

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE ROLE $GRAFANA_PSQL_USER WITH LOGIN PASSWORD '$GRAFANA_PSQL_PASSWORD'
    NOSUPERUSER INHERIT NOCREATEDB NOCREATEROLE NOREPLICATION VALID UNTIL 'infinity';
    CREATE DATABASE $GRAFANA_PSQL_DB OWNER $GRAFANA_PSQL_USER;
EOSQL

echo "Created database $GRAFANA_PSQL_DB with user"
