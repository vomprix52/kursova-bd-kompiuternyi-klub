-- =====================================================================
-- Скрипт 04. Функції та збережені процедури
-- =====================================================================
USE cyberclub;

DROP FUNCTION  IF EXISTS fn_client_discount;
DROP FUNCTION  IF EXISTS fn_session_cost;
DROP PROCEDURE IF EXISTS sp_start_session;
DROP PROCEDURE IF EXISTS sp_end_session;
DROP PROCEDURE IF EXISTS sp_top_up;
DROP PROCEDURE IF EXISTS sp_create_booking;
DROP PROCEDURE IF EXISTS sp_bar_sale;

DELIMITER $$

-- ---------------------------------------------------------------------
-- Функція 1. Знижка клієнта згідно з його рівнем лояльності, %
-- ---------------------------------------------------------------------
CREATE FUNCTION fn_client_discount(p_client_id INT UNSIGNED)
RETURNS DECIMAL(4,2)
READS SQL DATA
BEGIN
  DECLARE v_disc DECIMAL(4,2);
  SELECT l.discount_pct INTO v_disc
    FROM client c JOIN loyalty_level l ON l.level_id = c.level_id
   WHERE c.client_id = p_client_id;
  RETURN IFNULL(v_disc, 0);
END$$

-- ---------------------------------------------------------------------
-- Функція 2. Вартість сесії (БП-05):
--   погодинний тариф:  ціна/год × хвилини / 60 × (100 − знижка) / 100
--   пакет:             ціна пакета × (100 − знижка) / 100
-- Множення виконується до ділення, щоб уникнути похибки округлення.
-- ---------------------------------------------------------------------
CREATE FUNCTION fn_session_cost(p_tariff_id SMALLINT UNSIGNED,
                                p_minutes   INT,
                                p_discount  DECIMAL(4,2))
RETURNS DECIMAL(10,2)
READS SQL DATA
BEGIN
  DECLARE v_type  VARCHAR(10);
  DECLARE v_price DECIMAL(8,2);
  SELECT tariff_type, price INTO v_type, v_price
    FROM tariff WHERE tariff_id = p_tariff_id;
  IF v_type = 'hourly' THEN
    RETURN ROUND(v_price * p_minutes * (100 - p_discount) / 6000, 2);
  END IF;
  RETURN ROUND(v_price * (100 - p_discount) / 100, 2);
END$$

-- ---------------------------------------------------------------------
-- Процедура 1. Старт ігрової сесії
-- ---------------------------------------------------------------------
CREATE PROCEDURE sp_start_session(IN  p_client_id   INT UNSIGNED,
                                  IN  p_computer_id SMALLINT UNSIGNED,
                                  IN  p_tariff_id   SMALLINT UNSIGNED,
                                  IN  p_shift_id    INT UNSIGNED,
                                  OUT p_session_id  INT UNSIGNED)
BEGIN
  DECLARE v_now        DATETIME DEFAULT NOW();
  DECLARE v_cl_status  VARCHAR(10);
  DECLARE v_balance    DECIMAL(10,2);
  DECLARE v_pc_status  VARCHAR(12);
  DECLARE v_pc_zone    TINYINT UNSIGNED;
  DECLARE v_t_zone     TINYINT UNSIGNED;
  DECLARE v_type       VARCHAR(10);
  DECLARE v_price      DECIMAL(8,2);
  DECLARE v_duration   SMALLINT UNSIGNED;
  DECLARE v_from_h, v_to_h TINYINT UNSIGNED;
  DECLARE v_active     BOOLEAN;
  DECLARE v_disc       DECIMAL(4,2);
  DECLARE v_minutes    INT;
  DECLARE v_cost       DECIMAL(10,2) DEFAULT NULL;
  DECLARE v_booking_id INT UNSIGNED DEFAULT NULL;
  DECLARE v_emp        SMALLINT UNSIGNED DEFAULT NULL;

  DECLARE EXIT HANDLER FOR SQLEXCEPTION
  BEGIN
    ROLLBACK;
    RESIGNAL;
  END;

  START TRANSACTION;

  SELECT status, balance INTO v_cl_status, v_balance
    FROM client WHERE client_id = p_client_id FOR UPDATE;
  IF v_cl_status IS NULL THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Клієнта не знайдено';
  END IF;
  IF v_cl_status = 'blocked' THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Обліковий запис клієнта заблоковано';
  END IF;

  SELECT status, zone_id INTO v_pc_status, v_pc_zone
    FROM computer WHERE computer_id = p_computer_id FOR UPDATE;
  IF v_pc_status IS NULL THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Ігрове місце не знайдено';
  END IF;
  IF v_pc_status IN ('busy', 'maintenance') THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Місце зайняте або на обслуговуванні';
  END IF;

  -- БП-04: заброньоване місце може зайняти лише власник бронювання
  -- (за 15 хв до початку і до кінця інтервалу бронювання)
  SELECT booking_id INTO v_booking_id
    FROM booking
   WHERE computer_id = p_computer_id AND client_id = p_client_id
     AND status = 'pending'
     AND v_now >= starts_at - INTERVAL 15 MINUTE AND v_now < ends_at
   LIMIT 1;
  IF v_pc_status = 'reserved' AND v_booking_id IS NULL THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Місце заброньоване іншим клієнтом';
  END IF;

  SELECT zone_id, tariff_type, price, duration_min, start_from_h, start_to_h, is_active
    INTO v_t_zone, v_type, v_price, v_duration, v_from_h, v_to_h, v_active
    FROM tariff WHERE tariff_id = p_tariff_id;
  IF v_t_zone IS NULL OR NOT v_active THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Тариф не існує або неактивний';
  END IF;
  IF v_t_zone <> v_pc_zone THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Тариф не діє в зоні обраного місця';
  END IF;
  -- часове вікно активації пакета (з переходом через північ для «Нічного»)
  IF v_from_h IS NOT NULL AND NOT (
       (v_from_h < v_to_h AND HOUR(v_now) >= v_from_h AND HOUR(v_now) < v_to_h)
    OR (v_from_h > v_to_h AND (HOUR(v_now) >= v_from_h OR HOUR(v_now) < v_to_h))) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Пакет зараз недоступний для активації';
  END IF;

  SET v_disc = fn_client_discount(p_client_id);

  IF v_type = 'hourly' THEN
    -- БП-06: скільки хвилин покриває баланс; мінімум — 15 хвилин
    SET v_minutes = FLOOR(v_balance * 6000 / (v_price * (100 - v_disc)));
    IF v_minutes < 15 THEN
      SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Недостатньо коштів: баланс має покривати щонайменше 15 хвилин';
    END IF;
    SET v_minutes = LEAST(v_minutes, 720);
  ELSE
    SET v_cost = fn_session_cost(p_tariff_id, v_duration, v_disc);
    IF v_balance < v_cost THEN
      SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Недостатньо коштів для активації пакета';
    END IF;
    SET v_minutes = v_duration;
  END IF;

  INSERT INTO game_session (client_id, computer_id, tariff_id, shift_id, booking_id,
                            started_at, planned_end, discount_pct, cost, status)
  VALUES (p_client_id, p_computer_id, p_tariff_id, p_shift_id, v_booking_id,
          v_now, v_now + INTERVAL v_minutes MINUTE, v_disc, v_cost, 'active');
  SET p_session_id = LAST_INSERT_ID();

  -- пакет оплачується одразу: формується чек за гру і списання з балансу
  IF v_type = 'package' THEN
    SELECT employee_id INTO v_emp FROM shift WHERE shift_id = p_shift_id;
    SET @app_employee_id = COALESCE(@app_employee_id, v_emp);
    INSERT INTO sale (sale_type, session_id, client_id, employee_id, shift_id, created_at,
                      payment_method, total)
    VALUES ('game', p_session_id, p_client_id, v_emp, p_shift_id, v_now, 'balance', v_cost);
    UPDATE client SET balance = balance - v_cost, total_spent = total_spent + v_cost
     WHERE client_id = p_client_id;
    INSERT INTO balance_transaction (client_id, tx_type, amount, balance_after, sale_id, created_at)
    VALUES (p_client_id, 'session', -v_cost, v_balance - v_cost, LAST_INSERT_ID(), v_now);
  END IF;

  IF v_booking_id IS NOT NULL THEN
    UPDATE booking SET status = 'fulfilled' WHERE booking_id = v_booking_id;
  END IF;

  COMMIT;
END$$

-- ---------------------------------------------------------------------
-- Процедура 2. Завершення сесії з розрахунком вартості та списанням
-- ---------------------------------------------------------------------
CREATE PROCEDURE sp_end_session(IN p_session_id INT UNSIGNED)
BEGIN
  DECLARE v_status     VARCHAR(10);
  DECLARE v_client_id  INT UNSIGNED;
  DECLARE v_tariff_id  SMALLINT UNSIGNED;
  DECLARE v_type       VARCHAR(10);
  DECLARE v_started    DATETIME;
  DECLARE v_planned    DATETIME;
  DECLARE v_end        DATETIME;
  DECLARE v_disc       DECIMAL(4,2);
  DECLARE v_cost       DECIMAL(10,2);
  DECLARE v_minutes    INT;
  DECLARE v_balance    DECIMAL(10,2);
  DECLARE v_shift_id   INT UNSIGNED;
  DECLARE v_emp        SMALLINT UNSIGNED DEFAULT NULL;

  DECLARE EXIT HANDLER FOR SQLEXCEPTION
  BEGIN
    ROLLBACK;
    RESIGNAL;
  END;

  START TRANSACTION;

  SELECT s.status, s.client_id, s.tariff_id, t.tariff_type, s.started_at, s.planned_end,
         s.discount_pct, s.cost, s.shift_id
    INTO v_status, v_client_id, v_tariff_id, v_type, v_started, v_planned, v_disc, v_cost,
         v_shift_id
    FROM game_session s JOIN tariff t ON t.tariff_id = s.tariff_id
   WHERE s.session_id = p_session_id FOR UPDATE;
  IF v_status IS NULL THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Сесію не знайдено';
  END IF;
  IF v_status <> 'active' THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Сесія вже завершена';
  END IF;

  -- час гри не може перевищити оплачений (planned_end)
  SET v_end = LEAST(NOW(), v_planned);
  SET v_minutes = GREATEST(1, CEIL(TIMESTAMPDIFF(SECOND, v_started, v_end) / 60));

  IF v_type = 'hourly' THEN
    SET v_cost = fn_session_cost(v_tariff_id, v_minutes, v_disc);
    SELECT balance INTO v_balance FROM client WHERE client_id = v_client_id FOR UPDATE;
    SET v_cost = LEAST(v_cost, v_balance);
    -- чек за гру: одна сесія – один чек (UNIQUE sale.session_id)
    SELECT employee_id INTO v_emp FROM shift WHERE shift_id = v_shift_id;
    SET @app_employee_id = COALESCE(@app_employee_id, v_emp);
    INSERT INTO sale (sale_type, session_id, client_id, employee_id, shift_id, created_at,
                      payment_method, total)
    VALUES ('game', p_session_id, v_client_id, v_emp, v_shift_id, v_end, 'balance', v_cost);
    UPDATE client SET balance = balance - v_cost, total_spent = total_spent + v_cost
     WHERE client_id = v_client_id;
    INSERT INTO balance_transaction (client_id, tx_type, amount, balance_after, sale_id, created_at)
    VALUES (v_client_id, 'session', -v_cost, v_balance - v_cost, LAST_INSERT_ID(), v_end);
  END IF;

  UPDATE game_session
     SET ended_at = v_end, minutes_used = v_minutes, cost = v_cost, status = 'finished'
   WHERE session_id = p_session_id;

  COMMIT;
  SELECT p_session_id AS session_id, v_minutes AS minutes_used, v_cost AS cost;
END$$

-- ---------------------------------------------------------------------
-- Процедура 3. Поповнення балансу (+5 % бонусу від 1000 грн)
-- ---------------------------------------------------------------------
CREATE PROCEDURE sp_top_up(IN  p_client_id   INT UNSIGNED,
                           IN  p_amount      DECIMAL(10,2),
                           IN  p_method      VARCHAR(4),
                           IN  p_employee_id SMALLINT UNSIGNED,
                           OUT p_balance     DECIMAL(10,2))
BEGIN
  DECLARE v_status  VARCHAR(10);
  DECLARE v_balance DECIMAL(10,2);
  DECLARE v_bonus   DECIMAL(10,2) DEFAULT 0;

  DECLARE EXIT HANDLER FOR SQLEXCEPTION
  BEGIN
    ROLLBACK;
    RESIGNAL;
  END;

  IF p_amount IS NULL OR p_amount < 20 OR p_amount > 20000 THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Сума поповнення має бути від 20 до 20000 грн';
  END IF;
  IF p_method NOT IN ('cash', 'card') THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Спосіб оплати: cash або card';
  END IF;

  START TRANSACTION;
  SELECT status, balance INTO v_status, v_balance
    FROM client WHERE client_id = p_client_id FOR UPDATE;
  IF v_status IS NULL THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Клієнта не знайдено';
  END IF;
  IF v_status = 'blocked' THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Обліковий запис клієнта заблоковано';
  END IF;

  SET @app_employee_id = COALESCE(p_employee_id, @app_employee_id);  -- для журналу аудиту
  SET v_balance = v_balance + p_amount;
  INSERT INTO balance_transaction (client_id, tx_type, amount, balance_after, payment_method, employee_id)
  VALUES (p_client_id, 'topup', p_amount, v_balance, p_method, p_employee_id);

  IF p_amount >= 1000 THEN
    SET v_bonus = ROUND(p_amount * 0.05, 2);
    SET v_balance = v_balance + v_bonus;
    INSERT INTO balance_transaction (client_id, tx_type, amount, balance_after, employee_id)
    VALUES (p_client_id, 'bonus', v_bonus, v_balance, p_employee_id);
  END IF;

  UPDATE client SET balance = v_balance WHERE client_id = p_client_id;
  COMMIT;
  SET p_balance = v_balance;
END$$

-- ---------------------------------------------------------------------
-- Процедура 4. Створення бронювання з перевірками
-- (перетин інтервалів додатково контролює тригер trg_booking_bi)
-- ---------------------------------------------------------------------
CREATE PROCEDURE sp_create_booking(IN  p_client_id   INT UNSIGNED,
                                   IN  p_computer_id SMALLINT UNSIGNED,
                                   IN  p_starts_at   DATETIME,
                                   IN  p_ends_at     DATETIME,
                                   IN  p_employee_id SMALLINT UNSIGNED,
                                   OUT p_booking_id  INT UNSIGNED)
BEGIN
  DECLARE v_status    VARCHAR(10);
  DECLARE v_balance   DECIMAL(10,2);
  DECLARE v_pc_status VARCHAR(12);
  DECLARE v_hour_price DECIMAL(8,2);

  SELECT status, balance INTO v_status, v_balance FROM client WHERE client_id = p_client_id;
  IF v_status IS NULL OR v_status = 'blocked' THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Клієнт не може бронювати місця';
  END IF;
  IF p_starts_at <= NOW() OR p_starts_at > NOW() + INTERVAL 14 DAY THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Бронювання можливе на період до 14 днів наперед';
  END IF;
  IF TIMESTAMPDIFF(MINUTE, p_starts_at, p_ends_at) NOT BETWEEN 60 AND 720 THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Тривалість бронювання — від 1 до 12 годин';
  END IF;

  SELECT c.status, t.price INTO v_pc_status, v_hour_price
    FROM computer c
    JOIN tariff t ON t.zone_id = c.zone_id AND t.tariff_type = 'hourly' AND t.is_active
   WHERE c.computer_id = p_computer_id;
  IF v_pc_status IS NULL THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Ігрове місце не знайдено';
  END IF;
  -- БП-07: на балансі має бути сума щонайменше за першу годину гри
  IF v_balance < v_hour_price THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Для бронювання на балансі має бути вартість 1 години';
  END IF;
  -- клієнт не може мати двох бронювань, що перетинаються в часі
  IF EXISTS (SELECT 1 FROM booking
              WHERE client_id = p_client_id AND status = 'pending'
                AND starts_at < p_ends_at AND ends_at > p_starts_at) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'У клієнта вже є бронювання на цей час';
  END IF;

  INSERT INTO booking (client_id, computer_id, starts_at, ends_at, status, created_by)
  VALUES (p_client_id, p_computer_id, p_starts_at, p_ends_at, 'pending', p_employee_id);
  SET p_booking_id = LAST_INSERT_ID();
END$$

-- ---------------------------------------------------------------------
-- Процедура 5. Продаж у барі. Позиції передаються JSON-масивом:
--   '[{"product_id": 5, "qty": 2}, {"product_id": 9, "qty": 1}]'
-- ---------------------------------------------------------------------
CREATE PROCEDURE sp_bar_sale(IN  p_client_id   INT UNSIGNED,
                             IN  p_employee_id SMALLINT UNSIGNED,
                             IN  p_shift_id    INT UNSIGNED,
                             IN  p_method      VARCHAR(7),
                             IN  p_items       JSON,
                             OUT p_sale_id     INT UNSIGNED)
BEGIN
  DECLARE v_i       INT DEFAULT 0;
  DECLARE v_n       INT;
  DECLARE v_pid     SMALLINT UNSIGNED;
  DECLARE v_qty     SMALLINT UNSIGNED;
  DECLARE v_price   DECIMAL(8,2);
  DECLARE v_total   DECIMAL(10,2);
  DECLARE v_balance DECIMAL(10,2);

  DECLARE EXIT HANDLER FOR SQLEXCEPTION
  BEGIN
    ROLLBACK;
    RESIGNAL;
  END;

  SET v_n = JSON_LENGTH(p_items);
  IF v_n IS NULL OR v_n = 0 THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Чек не містить жодної позиції';
  END IF;
  IF p_method = 'balance' AND p_client_id IS NULL THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Оплата з балансу можлива лише для клієнта клубу';
  END IF;
  -- БП-09: кошти на балансі під час погодинної сесії зарезервовані за ігровим часом
  IF p_method = 'balance' AND EXISTS (
       SELECT 1 FROM game_session s JOIN tariff t ON t.tariff_id = s.tariff_id
        WHERE s.client_id = p_client_id AND s.status = 'active' AND t.tariff_type = 'hourly') THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'Під час погодинної сесії оплата бару з балансу недоступна';
  END IF;

  START TRANSACTION;
  SET @app_employee_id = COALESCE(p_employee_id, @app_employee_id);  -- для журналу аудиту
  INSERT INTO sale (sale_type, client_id, employee_id, shift_id, payment_method)
  VALUES ('bar', p_client_id, p_employee_id, p_shift_id, p_method);
  SET p_sale_id = LAST_INSERT_ID();

  WHILE v_i < v_n DO
    SET v_pid = JSON_EXTRACT(p_items, CONCAT('$[', v_i, '].product_id'));
    SET v_qty = JSON_EXTRACT(p_items, CONCAT('$[', v_i, '].qty'));
    SELECT price INTO v_price FROM product WHERE product_id = v_pid;
    -- наявність і списання залишку перевіряє тригер trg_sale_item_bi
    INSERT INTO sale_item (sale_id, product_id, quantity, unit_price)
    VALUES (p_sale_id, v_pid, v_qty, v_price);
    SET v_i = v_i + 1;
  END WHILE;

  SELECT total INTO v_total FROM sale WHERE sale_id = p_sale_id;

  IF p_method = 'balance' THEN
    SELECT balance INTO v_balance FROM client WHERE client_id = p_client_id FOR UPDATE;
    IF v_balance < v_total THEN
      SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Недостатньо коштів на балансі';
    END IF;
    UPDATE client SET balance = balance - v_total, total_spent = total_spent + v_total
     WHERE client_id = p_client_id;
    INSERT INTO balance_transaction (client_id, tx_type, amount, balance_after, sale_id, employee_id)
    VALUES (p_client_id, 'bar', -v_total, v_balance - v_total, p_sale_id, p_employee_id);
  END IF;
  COMMIT;
END$$

DELIMITER ;

-- Привілеї на виконання підпрограм
GRANT EXECUTE ON FUNCTION  cyberclub.fn_client_discount TO r_operator, r_owner, r_client_app;
GRANT EXECUTE ON FUNCTION  cyberclub.fn_session_cost    TO r_operator, r_owner;
GRANT EXECUTE ON PROCEDURE cyberclub.sp_start_session   TO r_operator;
GRANT EXECUTE ON PROCEDURE cyberclub.sp_end_session     TO r_operator;
GRANT EXECUTE ON PROCEDURE cyberclub.sp_top_up          TO r_operator;
GRANT EXECUTE ON PROCEDURE cyberclub.sp_create_booking  TO r_operator, r_client_app;
GRANT EXECUTE ON PROCEDURE cyberclub.sp_bar_sale        TO r_operator;
