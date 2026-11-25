-- =====================================================================
-- Скрипт 02. Ролі та облікові записи користувачів СКБД
-- Привілеї на процедури (04) та представлення (06) видаються наприкінці цих скриптів,
-- бо MySQL дозволяє GRANT лише на вже створені процедури та представлення.
-- Паролі нижче — тестові, лише для локального демонстраційного стенда.
-- =====================================================================
USE cyberclub;

DROP ROLE IF EXISTS r_owner, r_operator, r_technician, r_client_app, r_dba;
CREATE ROLE r_owner, r_operator, r_technician, r_client_app, r_dba;

-- ---------------- Власник / керуючий клубом ------------------------------
-- Бачить усе, керує довідниками (ціни, тарифи, товари, персонал),
-- але не змінює баланси та сесії напряму — лише через процедури.
GRANT SELECT ON cyberclub.* TO r_owner;
GRANT INSERT, UPDATE ON cyberclub.tariff           TO r_owner;
GRANT INSERT, UPDATE ON cyberclub.product          TO r_owner;
GRANT INSERT, UPDATE ON cyberclub.product_category TO r_owner;
GRANT INSERT, UPDATE ON cyberclub.loyalty_level    TO r_owner;
GRANT INSERT, UPDATE ON cyberclub.zone             TO r_owner;
GRANT INSERT, UPDATE ON cyberclub.computer         TO r_owner;
GRANT INSERT, UPDATE ON cyberclub.pc_config        TO r_owner;
GRANT INSERT, UPDATE ON cyberclub.position         TO r_owner;
GRANT INSERT, UPDATE ON cyberclub.employee         TO r_owner;
GRANT UPDATE (status, level_id) ON cyberclub.client TO r_owner;

-- ---------------- Адміністратор зали (оператор зміни) --------------------
GRANT SELECT ON cyberclub.client           TO r_operator;
GRANT SELECT ON cyberclub.loyalty_level    TO r_operator;
GRANT SELECT ON cyberclub.zone             TO r_operator;
GRANT SELECT ON cyberclub.computer         TO r_operator;
GRANT SELECT ON cyberclub.tariff           TO r_operator;
GRANT SELECT ON cyberclub.booking          TO r_operator;
GRANT SELECT ON cyberclub.game_session     TO r_operator;
GRANT SELECT ON cyberclub.balance_transaction TO r_operator;
GRANT SELECT ON cyberclub.product          TO r_operator;
GRANT SELECT ON cyberclub.product_category TO r_operator;
GRANT SELECT ON cyberclub.sale             TO r_operator;
GRANT SELECT ON cyberclub.sale_item        TO r_operator;
GRANT SELECT ON cyberclub.employee         TO r_operator;
GRANT SELECT, INSERT, UPDATE ON cyberclub.shift TO r_operator;
GRANT SELECT, INSERT ON cyberclub.maintenance_request TO r_operator;
-- реєстрація клієнта та редагування контактів; баланс змінювати не можна
GRANT INSERT ON cyberclub.client TO r_operator;
GRANT UPDATE (last_name, first_name, phone, email, status) ON cyberclub.client TO r_operator;
GRANT UPDATE (status) ON cyberclub.booking TO r_operator;

-- ---------------- Технік ---------------------------------------------------
GRANT SELECT ON cyberclub.zone      TO r_technician;
GRANT SELECT ON cyberclub.employee  TO r_technician;
GRANT SELECT, INSERT, UPDATE ON cyberclub.pc_config TO r_technician;
GRANT SELECT ON cyberclub.computer  TO r_technician;
GRANT UPDATE (config_id, ip_address) ON cyberclub.computer TO r_technician;
GRANT SELECT, INSERT ON cyberclub.maintenance_request TO r_technician;
GRANT UPDATE (assigned_to, status, resolved_at, resolution)
  ON cyberclub.maintenance_request TO r_technician;

-- ---------------- Клієнтський застосунок ------------------------------------
-- Клієнт не має власного облікового запису СКБД: застосунок працює від
-- імені kc_client_app і бачить лише довідкову інформацію та представлення.
GRANT SELECT ON cyberclub.zone          TO r_client_app;
GRANT SELECT ON cyberclub.tariff        TO r_client_app;
GRANT SELECT ON cyberclub.loyalty_level TO r_client_app;
GRANT SELECT (computer_id, seat_label, zone_id, status) ON cyberclub.computer TO r_client_app;
GRANT SELECT (client_id, login, password_hash, first_name, last_name, balance, level_id, status)
  ON cyberclub.client TO r_client_app;
GRANT SELECT (booking_id, client_id, computer_id, starts_at, ends_at, status)
  ON cyberclub.booking TO r_client_app;

-- ---------------- Адміністратор БД -----------------------------------------
GRANT ALL PRIVILEGES ON cyberclub.* TO r_dba WITH GRANT OPTION;

-- ---------------- Облікові записи ------------------------------------------
DROP USER IF EXISTS 'kc_owner'@'localhost', 'kc_operator'@'localhost',
  'kc_tech'@'localhost', 'kc_client_app'@'localhost', 'kc_dba'@'localhost';

CREATE USER 'kc_owner'@'localhost'      IDENTIFIED BY 'Owner#2026'    DEFAULT ROLE r_owner;
CREATE USER 'kc_operator'@'localhost'   IDENTIFIED BY 'Operator#2026' DEFAULT ROLE r_operator;
CREATE USER 'kc_tech'@'localhost'       IDENTIFIED BY 'Tech#2026'     DEFAULT ROLE r_technician;
CREATE USER 'kc_client_app'@'localhost' IDENTIFIED BY 'Client#2026'   DEFAULT ROLE r_client_app;
CREATE USER 'kc_dba'@'localhost'        IDENTIFIED BY 'Dba#2026'      DEFAULT ROLE r_dba;

GRANT r_owner      TO 'kc_owner'@'localhost';
GRANT r_operator   TO 'kc_operator'@'localhost';
GRANT r_technician TO 'kc_tech'@'localhost';
GRANT r_client_app TO 'kc_client_app'@'localhost';
GRANT r_dba        TO 'kc_dba'@'localhost';
