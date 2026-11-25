#!/bin/sh
# Виконує SQL-скрипт на локальному екземплярі MySQL (порт 3307)
"/c/Program Files/MySQL/MySQL Server 9.6/bin/mysql.exe" --defaults-file="C:/Users/kracu/Desktop/kursova/mysql.ini" -uroot -h127.0.0.1 --default-character-set=utf8mb4 "$@"
