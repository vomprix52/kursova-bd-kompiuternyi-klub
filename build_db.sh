#!/bin/sh
# Повне перестворення БД cyberclub: структура, ролі, дані, процедури, тригери, представлення
set -e
cd "$(dirname "$0")"
for f in sql/01_schema.sql sql/02_roles.sql sql/03_data.sql sql/04_procedures.sql \
         sql/05_triggers.sql sql/06_views.sql; do
  echo ">> $f"
  ./run_sql.sh < "$f"
done
