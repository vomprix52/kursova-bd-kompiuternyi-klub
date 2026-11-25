-- =====================================================================
-- Скрипт 05. Тригери та подія планувальника
-- =====================================================================
USE cyberclub;

DROP TRIGGER IF EXISTS trg_booking_bi;
DROP TRIGGER IF EXISTS trg_booking_bu;
DROP TRIGGER IF EXISTS trg_session_bi;
DROP TRIGGER IF EXISTS trg_session_ai;
DROP TRIGGER IF EXISTS trg_session_au;
DROP TRIGGER IF EXISTS trg_client_bu;
DROP TRIGGER IF EXISTS trg_client_au;
DROP TRIGGER IF EXISTS trg_tariff_au;
DROP TRIGGER IF EXISTS trg_product_au;
DROP TRIGGER IF EXISTS trg_sale_item_bi;
DROP TRIGGER IF EXISTS trg_sale_item_ai;
DROP TRIGGER IF EXISTS trg_request_ai;
DROP TRIGGER IF EXISTS trg_request_au;
DROP EVENT   IF EXISTS ev_booking_housekeeping;

DELIMITER $$

-- ---------------------------------------------------------------------
-- Тригер 1. БП-03: бронювання одного місця не перетинаються в часі
-- ---------------------------------------------------------------------
CREATE TRIGGER trg_booking_bi BEFORE INSERT ON booking
FOR EACH ROW
BEGIN
  IF NEW.status = 'pending' AND EXISTS (
       SELECT 1 FROM booking b
        WHERE b.computer_id = NEW.computer_id AND b.status = 'pending'
          AND b.starts_at < NEW.ends_at AND b.ends_at > NEW.starts_at) THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'БП-03: місце вже заброньоване на частину цього інтервалу';
  END IF;
END$$

CREATE TRIGGER trg_booking_bu BEFORE UPDATE ON booking
FOR EACH ROW
BEGIN
  IF NEW.status = 'pending'
     AND (NEW.starts_at <> OLD.starts_at OR NEW.ends_at <> OLD.ends_at
          OR NEW.computer_id <> OLD.computer_id OR OLD.status <> 'pending')
     AND EXISTS (
       SELECT 1 FROM booking b
        WHERE b.computer_id = NEW.computer_id AND b.status = 'pending'
          AND b.booking_id <> NEW.booking_id
          AND b.starts_at < NEW.ends_at AND b.ends_at > NEW.starts_at) THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'БП-03: місце вже заброньоване на частину цього інтервалу';
  END IF;
END$$

-- ---------------------------------------------------------------------
-- Тригер 2. Не можна почати сесію на місці, що перебуває на ремонті
-- ---------------------------------------------------------------------
CREATE TRIGGER trg_session_bi BEFORE INSERT ON game_session
FOR EACH ROW
BEGIN
  IF (SELECT status FROM computer WHERE computer_id = NEW.computer_id) = 'maintenance' THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Місце перебуває на обслуговуванні';
  END IF;
END$$

-- ---------------------------------------------------------------------
-- Тригер 3. Автоматична зміна статусу ПК під час старту / завершення сесії
-- ---------------------------------------------------------------------
CREATE TRIGGER trg_session_ai AFTER INSERT ON game_session
FOR EACH ROW
BEGIN
  IF NEW.status = 'active' THEN
    UPDATE computer SET status = 'busy' WHERE computer_id = NEW.computer_id;
  END IF;
END$$

CREATE TRIGGER trg_session_au AFTER UPDATE ON game_session
FOR EACH ROW
BEGIN
  IF OLD.status = 'active' AND NEW.status <> 'active' THEN
    -- якщо під час гри подано термінову заявку — місце йде на ремонт
    UPDATE computer
       SET status = IF(EXISTS (SELECT 1 FROM maintenance_request r
                                WHERE r.computer_id = NEW.computer_id
                                  AND r.priority = 'high' AND r.status <> 'resolved'),
                       'maintenance', 'free')
     WHERE computer_id = NEW.computer_id;
  END IF;
END$$

-- ---------------------------------------------------------------------
-- Тригер 4. Контроль балансу клієнта та автоматичне підвищення рівня
-- ---------------------------------------------------------------------
CREATE TRIGGER trg_client_bu BEFORE UPDATE ON client
FOR EACH ROW
BEGIN
  DECLARE v_level TINYINT UNSIGNED;
  IF NEW.balance < 0 THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'БП-08: операція призведе до від''ємного балансу клієнта';
  END IF;
  IF NEW.total_spent > OLD.total_spent THEN
    SELECT level_id INTO v_level FROM loyalty_level
     WHERE min_spent <= NEW.total_spent ORDER BY min_spent DESC LIMIT 1;
    -- рівень лише підвищується; ручне призначення вищого рівня зберігається
    IF (SELECT min_spent FROM loyalty_level WHERE level_id = v_level) >
       (SELECT min_spent FROM loyalty_level WHERE level_id = NEW.level_id) THEN
      SET NEW.level_id = v_level;
    END IF;
  END IF;
END$$

-- ---------------------------------------------------------------------
-- Тригер 5. Аудит змін балансу та рівня клієнта.
-- employee_id береться із сеансової змінної @app_employee_id, яку встановлює
-- застосунок (id працівника, що увійшов) або процедура (параметр p_employee_id)
-- ---------------------------------------------------------------------
CREATE TRIGGER trg_client_au AFTER UPDATE ON client
FOR EACH ROW
BEGIN
  IF NEW.balance <> OLD.balance THEN
    INSERT INTO audit_log (table_name, record_id, action, field_name, old_value, new_value,
                           employee_id, changed_by)
    VALUES ('client', NEW.client_id, 'UPDATE', 'balance', OLD.balance, NEW.balance,
            @app_employee_id, USER());
  END IF;
  IF NEW.level_id <> OLD.level_id THEN
    INSERT INTO audit_log (table_name, record_id, action, field_name, old_value, new_value,
                           employee_id, changed_by)
    VALUES ('client', NEW.client_id, 'UPDATE', 'level_id', OLD.level_id, NEW.level_id,
            @app_employee_id, USER());
  END IF;
END$$

-- ---------------------------------------------------------------------
-- Тригер 6. Аудит змін цін тарифів і товарів
-- ---------------------------------------------------------------------
CREATE TRIGGER trg_tariff_au AFTER UPDATE ON tariff
FOR EACH ROW
BEGIN
  IF NEW.price <> OLD.price THEN
    INSERT INTO audit_log (table_name, record_id, action, field_name, old_value, new_value,
                           employee_id, changed_by)
    VALUES ('tariff', NEW.tariff_id, 'UPDATE', 'price', OLD.price, NEW.price,
            @app_employee_id, USER());
  END IF;
END$$

CREATE TRIGGER trg_product_au AFTER UPDATE ON product
FOR EACH ROW
BEGIN
  IF NEW.price <> OLD.price THEN
    INSERT INTO audit_log (table_name, record_id, action, field_name, old_value, new_value,
                           employee_id, changed_by)
    VALUES ('product', NEW.product_id, 'UPDATE', 'price', OLD.price, NEW.price,
            @app_employee_id, USER());
  END IF;
END$$

-- ---------------------------------------------------------------------
-- Тригер 7. Позиція чека: перевірка залишку та списання товару
-- ---------------------------------------------------------------------
CREATE TRIGGER trg_sale_item_bi BEFORE INSERT ON sale_item
FOR EACH ROW
BEGIN
  DECLARE v_stock  INT;
  DECLARE v_active BOOLEAN;
  SELECT stock_qty, is_active INTO v_stock, v_active
    FROM product WHERE product_id = NEW.product_id FOR UPDATE;
  IF NOT v_active THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Товар виведено з продажу';
  END IF;
  IF v_stock < NEW.quantity THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Недостатньо товару на складі';
  END IF;
  UPDATE product SET stock_qty = stock_qty - NEW.quantity WHERE product_id = NEW.product_id;
END$$

CREATE TRIGGER trg_sale_item_ai AFTER INSERT ON sale_item
FOR EACH ROW
BEGIN
  UPDATE sale SET total = total + NEW.quantity * NEW.unit_price WHERE sale_id = NEW.sale_id;
END$$

-- ---------------------------------------------------------------------
-- Тригер 8. Заявки з високим пріоритетом виводять місце з експлуатації
-- ---------------------------------------------------------------------
CREATE TRIGGER trg_request_ai AFTER INSERT ON maintenance_request
FOR EACH ROW
BEGIN
  IF NEW.priority = 'high' THEN
    -- зайняте місце перейде в ремонт після завершення сесії (trg_session_au)
    UPDATE computer SET status = 'maintenance'
     WHERE computer_id = NEW.computer_id AND status <> 'busy';
  END IF;
END$$

CREATE TRIGGER trg_request_au AFTER UPDATE ON maintenance_request
FOR EACH ROW
BEGIN
  IF NEW.status = 'resolved' AND OLD.status <> 'resolved' AND NOT EXISTS (
       SELECT 1 FROM maintenance_request r
        WHERE r.computer_id = NEW.computer_id AND r.priority = 'high'
          AND r.status <> 'resolved' AND r.request_id <> NEW.request_id) THEN
    UPDATE computer SET status = 'free'
     WHERE computer_id = NEW.computer_id AND status = 'maintenance';
  END IF;
END$$

-- ---------------------------------------------------------------------
-- Подія: щохвилини резервує місця за 15 хв до бронювання
-- і фіксує неявки (клієнт не прийшов протягом 15 хв)
-- ---------------------------------------------------------------------
CREATE EVENT ev_booking_housekeeping
ON SCHEDULE EVERY 1 MINUTE
DO
BEGIN
  UPDATE booking SET status = 'no_show'
   WHERE status = 'pending' AND NOW() > starts_at + INTERVAL 15 MINUTE;

  UPDATE computer c
     SET c.status = 'free'
   WHERE c.status = 'reserved'
     AND NOT EXISTS (SELECT 1 FROM booking b
                      WHERE b.computer_id = c.computer_id AND b.status = 'pending'
                        AND NOW() >= b.starts_at - INTERVAL 15 MINUTE);

  UPDATE computer c
     SET c.status = 'reserved'
   WHERE c.status = 'free'
     AND EXISTS (SELECT 1 FROM booking b
                  WHERE b.computer_id = c.computer_id AND b.status = 'pending'
                    AND NOW() BETWEEN b.starts_at - INTERVAL 15 MINUTE AND b.ends_at);
END$$

DELIMITER ;
