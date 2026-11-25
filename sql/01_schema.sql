-- =====================================================================
-- Курсова робота «Проєктування та реалізація бази даних
-- для автоматизації діяльності комп'ютерного клубу»
-- Скрипт 01. Створення структури бази даних (DDL)
-- СКБД: MySQL 8.0+ (перевірено на MySQL Community Server 9.6)
-- =====================================================================

DROP DATABASE IF EXISTS cyberclub;
CREATE DATABASE cyberclub
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_0900_ai_ci;
USE cyberclub;

-- ---------------------------------------------------------------------
-- Довідники
-- ---------------------------------------------------------------------

-- Рівні програми лояльності
CREATE TABLE loyalty_level (
  level_id      TINYINT UNSIGNED NOT NULL AUTO_INCREMENT,
  name          VARCHAR(30)      NOT NULL,
  min_spent     DECIMAL(10,2)    NOT NULL,
  discount_pct  DECIMAL(4,2)     NOT NULL DEFAULT 0,
  PRIMARY KEY (level_id),
  UNIQUE KEY uq_level_name (name),
  UNIQUE KEY uq_level_min_spent (min_spent),
  CONSTRAINT chk_level_min_spent CHECK (min_spent >= 0),
  CONSTRAINT chk_level_discount  CHECK (discount_pct BETWEEN 0 AND 30)
) ENGINE=InnoDB COMMENT='Рівні програми лояльності';

-- Ігрові зони клубу
CREATE TABLE zone (
  zone_id      TINYINT UNSIGNED NOT NULL AUTO_INCREMENT,
  code         CHAR(3)          NOT NULL,
  name         VARCHAR(40)      NOT NULL,
  description  VARCHAR(255)     NULL,
  PRIMARY KEY (zone_id),
  UNIQUE KEY uq_zone_code (code),
  UNIQUE KEY uq_zone_name (name)
) ENGINE=InnoDB COMMENT='Ігрові зони';

-- Типові конфігурації обладнання
CREATE TABLE pc_config (
  config_id    SMALLINT UNSIGNED NOT NULL AUTO_INCREMENT,
  name         VARCHAR(40)       NOT NULL,
  cpu          VARCHAR(60)       NOT NULL,
  gpu          VARCHAR(60)       NOT NULL,
  ram_gb       SMALLINT UNSIGNED NOT NULL,
  storage      VARCHAR(60)       NOT NULL,
  monitor      VARCHAR(80)       NOT NULL,
  refresh_hz   SMALLINT UNSIGNED NOT NULL DEFAULT 60,
  PRIMARY KEY (config_id),
  UNIQUE KEY uq_config_name (name),
  CONSTRAINT chk_config_ram     CHECK (ram_gb BETWEEN 4 AND 256),
  CONSTRAINT chk_config_refresh CHECK (refresh_hz BETWEEN 50 AND 540)
) ENGINE=InnoDB COMMENT='Конфігурації ПК та ігрових консолей';

-- Ігрові місця (ПК / консолі)
CREATE TABLE computer (
  computer_id  SMALLINT UNSIGNED NOT NULL AUTO_INCREMENT,
  seat_label   VARCHAR(6)        NOT NULL,
  zone_id      TINYINT UNSIGNED  NOT NULL,
  config_id    SMALLINT UNSIGNED NOT NULL,
  ip_address   VARCHAR(15)       NOT NULL,
  status       ENUM('free','busy','reserved','maintenance') NOT NULL DEFAULT 'free',
  installed_at DATE              NOT NULL,
  PRIMARY KEY (computer_id),
  UNIQUE KEY uq_computer_seat (seat_label),
  UNIQUE KEY uq_computer_ip (ip_address),
  KEY ix_computer_zone_status (zone_id, status),
  CONSTRAINT fk_computer_zone   FOREIGN KEY (zone_id)
    REFERENCES zone (zone_id) ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT fk_computer_config FOREIGN KEY (config_id)
    REFERENCES pc_config (config_id) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB COMMENT='Ігрові місця';

-- Тарифи (погодинні та пакетні) у розрізі зон
CREATE TABLE tariff (
  tariff_id      SMALLINT UNSIGNED NOT NULL AUTO_INCREMENT,
  zone_id        TINYINT UNSIGNED  NOT NULL,
  name           VARCHAR(40)       NOT NULL,
  tariff_type    ENUM('hourly','package') NOT NULL,
  price          DECIMAL(8,2)      NOT NULL COMMENT 'грн/год для hourly, вартість пакета для package',
  duration_min   SMALLINT UNSIGNED NULL     COMMENT 'тривалість пакета, хв',
  start_from_h   TINYINT UNSIGNED  NULL     COMMENT 'з якої години можна активувати пакет',
  start_to_h     TINYINT UNSIGNED  NULL     COMMENT 'до якої години (не включно) можна активувати пакет',
  is_active      BOOLEAN           NOT NULL DEFAULT TRUE,
  PRIMARY KEY (tariff_id),
  UNIQUE KEY uq_tariff_zone_name (zone_id, name),
  CONSTRAINT fk_tariff_zone FOREIGN KEY (zone_id)
    REFERENCES zone (zone_id) ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT chk_tariff_price CHECK (price > 0),
  CONSTRAINT chk_tariff_type_duration CHECK (
       (tariff_type = 'hourly'  AND duration_min IS NULL)
    OR (tariff_type = 'package' AND duration_min BETWEEN 30 AND 720)),
  CONSTRAINT chk_tariff_hours CHECK (
       (start_from_h IS NULL AND start_to_h IS NULL)
    OR (start_from_h BETWEEN 0 AND 23 AND start_to_h BETWEEN 0 AND 23))
) ENGINE=InnoDB COMMENT='Тарифи';

-- Посади персоналу
CREATE TABLE position (
  position_id  TINYINT UNSIGNED NOT NULL AUTO_INCREMENT,
  title        VARCHAR(40)      NOT NULL,
  hourly_rate  DECIMAL(7,2)     NOT NULL COMMENT 'ставка оплати праці, грн/год',
  PRIMARY KEY (position_id),
  UNIQUE KEY uq_position_title (title),
  CONSTRAINT chk_position_rate CHECK (hourly_rate > 0)
) ENGINE=InnoDB COMMENT='Посади';

-- ---------------------------------------------------------------------
-- Люди
-- ---------------------------------------------------------------------

CREATE TABLE employee (
  employee_id    SMALLINT UNSIGNED NOT NULL AUTO_INCREMENT,
  last_name      VARCHAR(50)       NOT NULL,
  first_name     VARCHAR(50)       NOT NULL,
  phone          VARCHAR(13)       NOT NULL,
  login          VARCHAR(30)       NOT NULL,
  password_hash  VARCHAR(255)      NOT NULL,
  position_id    TINYINT UNSIGNED  NOT NULL,
  hired_at       DATE              NOT NULL,
  is_active      BOOLEAN           NOT NULL DEFAULT TRUE,
  PRIMARY KEY (employee_id),
  UNIQUE KEY uq_employee_login (login),
  UNIQUE KEY uq_employee_phone (phone),
  CONSTRAINT fk_employee_position FOREIGN KEY (position_id)
    REFERENCES position (position_id) ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT chk_employee_phone CHECK (phone REGEXP '^\\+380[0-9]{9}$')
) ENGINE=InnoDB COMMENT='Працівники';

CREATE TABLE client (
  client_id      INT UNSIGNED     NOT NULL AUTO_INCREMENT,
  login          VARCHAR(30)      NOT NULL,
  password_hash  VARCHAR(255)     NOT NULL,
  last_name      VARCHAR(50)      NOT NULL,
  first_name     VARCHAR(50)      NOT NULL,
  phone          VARCHAR(13)      NOT NULL,
  email          VARCHAR(100)     NULL,
  birth_date     DATE             NOT NULL,
  balance        DECIMAL(10,2)    NOT NULL DEFAULT 0,
  total_spent    DECIMAL(12,2)    NOT NULL DEFAULT 0,
  level_id       TINYINT UNSIGNED NOT NULL DEFAULT 1,
  status         ENUM('active','blocked') NOT NULL DEFAULT 'active',
  registered_at  DATETIME         NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (client_id),
  UNIQUE KEY uq_client_login (login),
  UNIQUE KEY uq_client_phone (phone),
  UNIQUE KEY uq_client_email (email),
  KEY ix_client_name (last_name, first_name),
  CONSTRAINT fk_client_level FOREIGN KEY (level_id)
    REFERENCES loyalty_level (level_id) ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT chk_client_balance CHECK (balance >= 0),
  CONSTRAINT chk_client_spent   CHECK (total_spent >= 0),
  CONSTRAINT chk_client_phone   CHECK (phone REGEXP '^\\+380[0-9]{9}$'),
  CONSTRAINT chk_client_email   CHECK (email IS NULL OR email LIKE '%_@_%._%')
) ENGINE=InnoDB COMMENT='Клієнти клубу';

-- ---------------------------------------------------------------------
-- Робота персоналу
-- ---------------------------------------------------------------------

CREATE TABLE shift (
  shift_id     INT UNSIGNED      NOT NULL AUTO_INCREMENT,
  employee_id  SMALLINT UNSIGNED NOT NULL,
  started_at   DATETIME          NOT NULL,
  ended_at     DATETIME          NULL,
  cash_start   DECIMAL(10,2)     NOT NULL DEFAULT 0,
  cash_end     DECIMAL(10,2)     NULL,
  PRIMARY KEY (shift_id),
  KEY ix_shift_started (started_at),
  CONSTRAINT fk_shift_employee FOREIGN KEY (employee_id)
    REFERENCES employee (employee_id) ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT chk_shift_period CHECK (ended_at IS NULL OR ended_at > started_at),
  CONSTRAINT chk_shift_cash   CHECK (cash_start >= 0 AND (cash_end IS NULL OR cash_end >= 0))
) ENGINE=InnoDB COMMENT='Робочі зміни адміністраторів';

-- ---------------------------------------------------------------------
-- Бронювання та ігрові сесії
-- ---------------------------------------------------------------------

CREATE TABLE booking (
  booking_id   INT UNSIGNED      NOT NULL AUTO_INCREMENT,
  client_id    INT UNSIGNED      NOT NULL,
  computer_id  SMALLINT UNSIGNED NOT NULL,
  starts_at    DATETIME          NOT NULL,
  ends_at      DATETIME          NOT NULL,
  status       ENUM('pending','fulfilled','cancelled','no_show') NOT NULL DEFAULT 'pending',
  created_at   DATETIME          NOT NULL DEFAULT CURRENT_TIMESTAMP,
  created_by   SMALLINT UNSIGNED NULL COMMENT 'NULL — бронювання створив сам клієнт',
  PRIMARY KEY (booking_id),
  KEY ix_booking_pc_time (computer_id, starts_at, ends_at),
  KEY ix_booking_client (client_id, starts_at),
  CONSTRAINT fk_booking_client FOREIGN KEY (client_id)
    REFERENCES client (client_id) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT fk_booking_computer FOREIGN KEY (computer_id)
    REFERENCES computer (computer_id) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT fk_booking_employee FOREIGN KEY (created_by)
    REFERENCES employee (employee_id) ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT chk_booking_period CHECK (ends_at > starts_at
    AND TIMESTAMPDIFF(MINUTE, starts_at, ends_at) BETWEEN 30 AND 720)
) ENGINE=InnoDB COMMENT='Бронювання місць';

CREATE TABLE game_session (
  session_id    INT UNSIGNED      NOT NULL AUTO_INCREMENT,
  client_id     INT UNSIGNED      NOT NULL,
  computer_id   SMALLINT UNSIGNED NOT NULL,
  tariff_id     SMALLINT UNSIGNED NOT NULL,
  shift_id      INT UNSIGNED      NULL,
  booking_id    INT UNSIGNED      NULL,
  started_at    DATETIME          NOT NULL,
  planned_end   DATETIME          NOT NULL COMMENT 'час, до якого вистачає балансу або діє пакет',
  ended_at      DATETIME          NULL,
  minutes_used  SMALLINT UNSIGNED NULL,
  discount_pct  DECIMAL(4,2)      NOT NULL DEFAULT 0,
  cost          DECIMAL(10,2)     NULL,
  status        ENUM('active','finished','cancelled') NOT NULL DEFAULT 'active',
  -- технічні стовпці для БП-01 та БП-02: не більше однієї активної сесії
  -- на одному ПК і в одного клієнта (NULL не порушує UNIQUE)
  active_pc     SMALLINT UNSIGNED AS (IF(status = 'active', computer_id, NULL)) STORED,
  active_client INT UNSIGNED      AS (IF(status = 'active', client_id,   NULL)) STORED,
  PRIMARY KEY (session_id),
  UNIQUE KEY uq_session_active_pc (active_pc),
  UNIQUE KEY uq_session_active_client (active_client),
  UNIQUE KEY uq_session_booking (booking_id),
  KEY ix_session_started (started_at),
  KEY ix_session_client_started (client_id, started_at),
  CONSTRAINT fk_session_client FOREIGN KEY (client_id)
    REFERENCES client (client_id) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT fk_session_computer FOREIGN KEY (computer_id)
    REFERENCES computer (computer_id) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT fk_session_tariff FOREIGN KEY (tariff_id)
    REFERENCES tariff (tariff_id) ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT fk_session_shift FOREIGN KEY (shift_id)
    REFERENCES shift (shift_id) ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT fk_session_booking FOREIGN KEY (booking_id)
    REFERENCES booking (booking_id) ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT chk_session_period CHECK (planned_end > started_at
    AND (ended_at IS NULL OR ended_at >= started_at)),
  CONSTRAINT chk_session_cost CHECK (cost IS NULL OR cost >= 0),
  CONSTRAINT chk_session_discount CHECK (discount_pct BETWEEN 0 AND 30),
  CONSTRAINT chk_session_finished CHECK (status <> 'finished'
    OR (ended_at IS NOT NULL AND cost IS NOT NULL AND minutes_used IS NOT NULL))
) ENGINE=InnoDB COMMENT='Ігрові сесії';

-- ---------------------------------------------------------------------
-- Бар
-- ---------------------------------------------------------------------

CREATE TABLE product_category (
  category_id  TINYINT UNSIGNED NOT NULL AUTO_INCREMENT,
  name         VARCHAR(40)      NOT NULL,
  PRIMARY KEY (category_id),
  UNIQUE KEY uq_category_name (name)
) ENGINE=InnoDB COMMENT='Категорії товарів бару';

CREATE TABLE product (
  product_id   SMALLINT UNSIGNED NOT NULL AUTO_INCREMENT,
  category_id  TINYINT UNSIGNED  NOT NULL,
  name         VARCHAR(60)       NOT NULL,
  price        DECIMAL(8,2)      NOT NULL,
  stock_qty    INT               NOT NULL DEFAULT 0,
  is_active    BOOLEAN           NOT NULL DEFAULT TRUE,
  PRIMARY KEY (product_id),
  UNIQUE KEY uq_product_name (name),
  CONSTRAINT fk_product_category FOREIGN KEY (category_id)
    REFERENCES product_category (category_id) ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT chk_product_price CHECK (price > 0),
  CONSTRAINT chk_product_stock CHECK (stock_qty >= 0)
) ENGINE=InnoDB COMMENT='Товари бару';

-- Чек: або покупка в барі (позиції в sale_item), або оплата ігрової сесії
CREATE TABLE sale (
  sale_id         INT UNSIGNED      NOT NULL AUTO_INCREMENT,
  sale_type       ENUM('bar','game') NOT NULL DEFAULT 'bar',
  session_id      INT UNSIGNED      NULL COMMENT 'оплачена сесія (лише для чека за гру)',
  client_id       INT UNSIGNED      NULL COMMENT 'NULL — анонімний покупець',
  employee_id     SMALLINT UNSIGNED NULL COMMENT 'касир; NULL — чек сформовано автоматично',
  shift_id        INT UNSIGNED      NULL,
  created_at      DATETIME          NOT NULL DEFAULT CURRENT_TIMESTAMP,
  payment_method  ENUM('cash','card','balance') NOT NULL,
  total           DECIMAL(10,2)     NOT NULL DEFAULT 0,
  PRIMARY KEY (sale_id),
  UNIQUE KEY uq_sale_session (session_id),
  KEY ix_sale_created (created_at),
  CONSTRAINT fk_sale_session FOREIGN KEY (session_id)
    REFERENCES game_session (session_id) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT fk_sale_client FOREIGN KEY (client_id)
    REFERENCES client (client_id) ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT fk_sale_employee FOREIGN KEY (employee_id)
    REFERENCES employee (employee_id) ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT fk_sale_shift FOREIGN KEY (shift_id)
    REFERENCES shift (shift_id) ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT chk_sale_total CHECK (total >= 0),
  -- чек за гру завжди прив'язаний до сесії й оплачується з балансу
  CONSTRAINT chk_sale_type CHECK (
       (sale_type = 'game' AND session_id IS NOT NULL AND payment_method = 'balance')
    OR (sale_type = 'bar'  AND session_id IS NULL))
) ENGINE=InnoDB COMMENT='Чеки: бар та оплата ігрових сесій';

-- Асоціативна таблиця: розв'язує зв'язок M:N між sale та product
CREATE TABLE sale_item (
  sale_id     INT UNSIGNED      NOT NULL,
  product_id  SMALLINT UNSIGNED NOT NULL,
  quantity    SMALLINT UNSIGNED NOT NULL,
  unit_price  DECIMAL(8,2)      NOT NULL COMMENT 'ціна на момент продажу',
  PRIMARY KEY (sale_id, product_id),
  KEY ix_sale_item_product (product_id),
  CONSTRAINT fk_item_sale FOREIGN KEY (sale_id)
    REFERENCES sale (sale_id) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT fk_item_product FOREIGN KEY (product_id)
    REFERENCES product (product_id) ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT chk_item_qty   CHECK (quantity BETWEEN 1 AND 50),
  CONSTRAINT chk_item_price CHECK (unit_price > 0)
) ENGINE=InnoDB COMMENT='Позиції чека';

-- ---------------------------------------------------------------------
-- Фінанси, обслуговування, аудит
-- ---------------------------------------------------------------------

CREATE TABLE balance_transaction (
  tx_id           INT UNSIGNED      NOT NULL AUTO_INCREMENT,
  client_id       INT UNSIGNED      NOT NULL,
  tx_type         ENUM('topup','bonus','refund','session','bar') NOT NULL,
  amount          DECIMAL(10,2)     NOT NULL COMMENT '+ зарахування, − списання',
  balance_after   DECIMAL(10,2)     NOT NULL,
  payment_method  ENUM('cash','card','none') NOT NULL DEFAULT 'none',
  sale_id         INT UNSIGNED      NULL COMMENT 'чек, яким оплачено гру або бар',
  employee_id     SMALLINT UNSIGNED NULL,
  created_at      DATETIME          NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (tx_id),
  KEY ix_tx_client_created (client_id, created_at),
  KEY ix_tx_created (created_at),
  CONSTRAINT fk_tx_client FOREIGN KEY (client_id)
    REFERENCES client (client_id) ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT fk_tx_sale FOREIGN KEY (sale_id)
    REFERENCES sale (sale_id) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT fk_tx_employee FOREIGN KEY (employee_id)
    REFERENCES employee (employee_id) ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT chk_tx_sign CHECK (
       (tx_type IN ('topup','bonus','refund') AND amount > 0)
    OR (tx_type IN ('session','bar')          AND amount < 0)),
  CONSTRAINT chk_tx_balance_after CHECK (balance_after >= 0),
  -- списання завжди має чек, зарахування – ніколи
  CONSTRAINT chk_tx_sale CHECK ((tx_type IN ('session','bar')) = (sale_id IS NOT NULL))
) ENGINE=InnoDB COMMENT='Рух коштів на балансі клієнта';

CREATE TABLE maintenance_request (
  request_id   INT UNSIGNED      NOT NULL AUTO_INCREMENT,
  computer_id  SMALLINT UNSIGNED NOT NULL,
  reported_by  SMALLINT UNSIGNED NOT NULL,
  assigned_to  SMALLINT UNSIGNED NULL,
  problem      VARCHAR(255)      NOT NULL,
  priority     ENUM('low','medium','high') NOT NULL DEFAULT 'medium',
  status       ENUM('open','in_progress','resolved') NOT NULL DEFAULT 'open',
  created_at   DATETIME          NOT NULL DEFAULT CURRENT_TIMESTAMP,
  resolved_at  DATETIME          NULL,
  resolution   VARCHAR(255)      NULL,
  PRIMARY KEY (request_id),
  KEY ix_request_status (status, priority),
  CONSTRAINT fk_request_computer FOREIGN KEY (computer_id)
    REFERENCES computer (computer_id) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT fk_request_reporter FOREIGN KEY (reported_by)
    REFERENCES employee (employee_id) ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT fk_request_assignee FOREIGN KEY (assigned_to)
    REFERENCES employee (employee_id) ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT chk_request_resolved CHECK (
       (status =  'resolved' AND resolved_at IS NOT NULL AND resolved_at >= created_at)
    OR (status <> 'resolved' AND resolved_at IS NULL))
) ENGINE=InnoDB COMMENT='Заявки на обслуговування обладнання';

CREATE TABLE audit_log (
  audit_id    BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  table_name  VARCHAR(40)     NOT NULL,
  record_id   INT UNSIGNED    NOT NULL,
  action      ENUM('INSERT','UPDATE','DELETE') NOT NULL,
  field_name  VARCHAR(40)     NULL,
  old_value   VARCHAR(255)    NULL,
  new_value   VARCHAR(255)    NULL,
  employee_id SMALLINT UNSIGNED NULL COMMENT 'працівник, від імені якого виконано зміну',
  changed_by  VARCHAR(80)     NOT NULL COMMENT 'обліковий запис СКБД',
  changed_at  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (audit_id),
  KEY ix_audit_table_record (table_name, record_id),
  KEY ix_audit_changed (changed_at),
  CONSTRAINT fk_audit_employee FOREIGN KEY (employee_id)
    REFERENCES employee (employee_id) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB COMMENT='Журнал аудиту змін цін і балансів';
