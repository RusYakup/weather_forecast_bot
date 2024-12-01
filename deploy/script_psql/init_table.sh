##!/bin/bash
#
#echo "Creating table..."
#
#psql -U ${POSTGRES_USER} -d ${POSTGRES_DB} -c "
#  CREATE TABLE IF NOT EXISTS user_state (
#    chat_id INTEGER PRIMARY KEY,
#    city VARCHAR(50),
#    date_difference VARCHAR(15),
#    qty_days VARCHAR(15),
#    CONSTRAINT unique_chat_id UNIQUE (chat_id)
#  );
#
#  CREATE TABLE IF NOT EXISTS statistic (
#    id SERIAL PRIMARY KEY,
#    ts INTEGER,
#    user_id INTEGER,
#    user_name VARCHAR(50),
#    chat_id INTEGER,
#    action VARCHAR(50)
#  );
#
#  CREATE TABLE IF NOT EXISTS users_online (
#    chat_id INTEGER NOT NULL UNIQUE,
#    timestamp INTEGER NOT NULL
#  );
#"
#
#
#echo "Table created successfully"