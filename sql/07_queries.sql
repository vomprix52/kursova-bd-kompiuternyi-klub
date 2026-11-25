-- =====================================================================
-- Скрипт 07. SQL-запити для основних операцій та демонстрація роботи
-- процедур, функцій, тригерів і представлень.
-- Блоки позначено «-- @@ код | назва»; scripts/run_queries.py виконує їх
-- по черзі та зберігає реальні результати для пояснювальної записки.
-- =====================================================================
USE cyberclub;

-- @@ Q01 | Вільні місця VIP-зони з конфігурацією
SELECT c.seat_label, p.cpu, p.gpu, p.refresh_hz
FROM computer c
JOIN zone z      ON z.zone_id = c.zone_id
JOIN pc_config p ON p.config_id = c.config_id
WHERE z.code = 'VIP' AND c.status = 'free'
ORDER BY c.seat_label;

-- @@ Q02 | Клієнти з балансом понад 400 грн
SELECT login, CONCAT(last_name, ' ', first_name) AS client, phone, balance
FROM client
WHERE balance > 400 AND status = 'active'
ORDER BY balance DESC
LIMIT 6;

-- @@ Q03 | Вечірні сесії суботи 12.09.2026
SELECT s.session_id, c.seat_label, CONCAT(cl.last_name, ' ', cl.first_name) AS client,
       TIME(s.started_at) AS start_t, TIME(s.ended_at) AS end_t, s.cost
FROM game_session s
JOIN computer c ON c.computer_id = s.computer_id
JOIN client cl  ON cl.client_id = s.client_id
WHERE s.started_at BETWEEN '2026-09-12 18:00:00' AND '2026-09-12 23:59:59'
ORDER BY s.started_at;

-- @@ Q04 | Останні чеки бару з позиціями (з'єднання п'яти таблиць)
SELECT sl.sale_id, DATE_FORMAT(sl.created_at, '%d.%m %H:%i') AS sold_at,
       COALESCE(CONCAT(cl.last_name, ' ', LEFT(cl.first_name, 1), '.'), 'анонімний') AS buyer,
       e.last_name AS cashier, p.name AS product, si.quantity AS qty, si.unit_price
FROM sale sl
JOIN sale_item si    ON si.sale_id = sl.sale_id
JOIN product p       ON p.product_id = si.product_id
JOIN employee e      ON e.employee_id = sl.employee_id
LEFT JOIN client cl  ON cl.client_id = sl.client_id
WHERE sl.sale_type = 'bar'
  AND sl.sale_id IN (SELECT sale_id FROM (SELECT sale_id FROM sale
                      WHERE sale_type = 'bar' AND created_at < '2026-10-01'
                      ORDER BY sale_id DESC LIMIT 4) last4)
ORDER BY sl.sale_id, p.name;

-- @@ Q05 | Виручка від ігрового часу за зонами (вересень 2026)
SELECT z.name AS zone, COUNT(*) AS sessions,
       ROUND(SUM(s.minutes_used) / 60, 1) AS hours,
       SUM(s.cost) AS revenue,
       ROUND(AVG(s.cost), 2) AS avg_check
FROM game_session s
JOIN computer c ON c.computer_id = s.computer_id
JOIN zone z     ON z.zone_id = c.zone_id
WHERE s.started_at >= '2026-09-01' AND s.started_at < '2026-10-01'
GROUP BY z.zone_id, z.name
ORDER BY revenue DESC;

-- @@ Q06 | Постійні клієнти: понад 15 сесій (HAVING)
SELECT CONCAT(cl.last_name, ' ', cl.first_name) AS client,
       COUNT(*) AS sessions,
       ROUND(AVG(s.minutes_used)) AS avg_minutes,
       SUM(s.cost) AS spent
FROM game_session s
JOIN client cl ON cl.client_id = s.client_id
GROUP BY cl.client_id, cl.last_name, cl.first_name
HAVING COUNT(*) > 15
ORDER BY sessions DESC;

-- @@ Q07 | Профіль навантаження: старти сесій за годинами доби
SELECT HOUR(started_at) AS hour_of_day, COUNT(*) AS sessions,
       ROUND(AVG(minutes_used)) AS avg_minutes
FROM game_session
GROUP BY HOUR(started_at)
ORDER BY hour_of_day;

-- @@ Q08 | Активні гравці, які жодного разу не купували в барі (NOT EXISTS)
SELECT CONCAT(cl.last_name, ' ', cl.first_name) AS client,
       (SELECT COUNT(*) FROM game_session s WHERE s.client_id = cl.client_id) AS sessions
FROM client cl
WHERE NOT EXISTS (SELECT 1 FROM sale sl
                  WHERE sl.client_id = cl.client_id AND sl.sale_type = 'bar')
  AND (SELECT COUNT(*) FROM game_session s WHERE s.client_id = cl.client_id) >= 5
ORDER BY sessions DESC;

-- @@ Q09 | Найзавантаженіше місце в кожній зоні (корельований підзапит)
SELECT z.name AS zone, c.seat_label,
       ROUND(SUM(s.minutes_used) / 60, 1) AS hours
FROM game_session s
JOIN computer c ON c.computer_id = s.computer_id
JOIN zone z     ON z.zone_id = c.zone_id
GROUP BY z.zone_id, z.name, c.computer_id, c.seat_label
HAVING SUM(s.minutes_used) = (
  SELECT MAX(t.m) FROM (
    SELECT c2.zone_id, SUM(s2.minutes_used) AS m
    FROM game_session s2 JOIN computer c2 ON c2.computer_id = s2.computer_id
    GROUP BY c2.zone_id, c2.computer_id) t
  WHERE t.zone_id = z.zone_id)
ORDER BY z.zone_id;

-- @@ Q10 | Клієнти, які купували «Нічний» пакет (підзапит з IN)
SELECT login, CONCAT(last_name, ' ', first_name) AS client
FROM client
WHERE client_id IN (SELECT s.client_id FROM game_session s
                    JOIN tariff t ON t.tariff_id = s.tariff_id
                    WHERE t.name = 'Нічний')
ORDER BY last_name
LIMIT 8;

-- @@ Q11 | Рейтинг клієнтів за витратами (RANK, частка у виручці)
SELECT RANK() OVER (ORDER BY total_spent DESC) AS place,
       CONCAT(last_name, ' ', first_name) AS client,
       total_spent,
       ROUND(100 * total_spent / SUM(total_spent) OVER (), 1) AS share_pct,
       NTILE(4) OVER (ORDER BY total_spent DESC) AS quartile
FROM client
ORDER BY place
LIMIT 8;

-- @@ Q12 | Наростаючий підсумок виручки за вересень (SUM OVER)
SELECT work_date, day_revenue,
       SUM(day_revenue) OVER (ORDER BY work_date) AS running_total
FROM (SELECT DATE(started_at) AS work_date, SUM(cost) AS day_revenue
        FROM game_session
       WHERE started_at >= '2026-09-01' AND started_at < '2026-10-01'
       GROUP BY DATE(started_at)) d
ORDER BY work_date
LIMIT 10;

-- @@ Q13 | Динаміка виручки за місяцями (CTE + LAG)
WITH games AS (
  SELECT DATE_FORMAT(started_at, '%Y-%m') AS ym, SUM(cost) AS game_rev
  FROM game_session GROUP BY ym),
bar AS (
  SELECT DATE_FORMAT(created_at, '%Y-%m') AS ym, SUM(total) AS bar_rev
  FROM sale WHERE sale_type = 'bar' GROUP BY ym)
SELECT g.ym AS month, g.game_rev, b.bar_rev, g.game_rev + b.bar_rev AS total,
       ROUND(100 * (g.game_rev + b.bar_rev) /
             LAG(g.game_rev + b.bar_rev) OVER (ORDER BY g.ym) - 100, 1) AS growth_pct
FROM games g JOIN bar b ON b.ym = g.ym
ORDER BY g.ym;

-- @@ Q14 | Результати адміністраторів за змінами (CTE)
WITH shift_stats AS (
  SELECT sh.shift_id, sh.employee_id,
         (SELECT COUNT(*) FROM game_session s WHERE s.shift_id = sh.shift_id) AS sessions,
         (SELECT COALESCE(SUM(t.amount), 0) FROM balance_transaction t
           WHERE t.tx_type = 'topup' AND t.created_at >= sh.started_at
             AND t.created_at < sh.ended_at) AS topups,
         sh.cash_end - sh.cash_start AS cash_in
  FROM shift sh)
SELECT CONCAT(e.last_name, ' ', e.first_name) AS admin, COUNT(*) AS shifts,
       SUM(st.sessions) AS sessions, SUM(st.topups) AS topups,
       ROUND(AVG(st.cash_in), 2) AS avg_cash_per_shift
FROM shift_stats st JOIN employee e ON e.employee_id = st.employee_id
GROUP BY e.employee_id, e.last_name, e.first_name
ORDER BY topups DESC;

-- @@ Q15 | Середня зайнятість місць за годинами доби (рекурсивний CTE)
WITH RECURSIVE hours AS (
  SELECT 0 AS h UNION ALL SELECT h + 1 FROM hours WHERE h < 23),
days AS (SELECT COUNT(DISTINCT DATE(started_at)) AS n FROM game_session),
busy AS (
  SELECT hr.h, COUNT(*) AS cnt
  FROM hours hr
  JOIN game_session s
    ON s.started_at < TIMESTAMP(DATE(s.started_at), MAKETIME(hr.h, 59, 59))
   AND s.ended_at  > TIMESTAMP(DATE(s.started_at), MAKETIME(hr.h, 0, 0))
  GROUP BY hr.h)
SELECT hr.h AS hour_of_day,
       ROUND(100 * COALESCE(b.cnt, 0) / (d.n * (SELECT COUNT(*) FROM computer)), 1) AS occupancy_pct
FROM hours hr CROSS JOIN days d LEFT JOIN busy b ON b.h = hr.h
WHERE hr.h IN (0, 10, 12, 14, 16, 18, 19, 20, 21, 22, 23)
ORDER BY hr.h;

-- @@ Q16 | Коефіцієнт використання зон за весь період
SELECT z.name AS zone, COUNT(DISTINCT c.computer_id) AS seats,
       ROUND(SUM(s.minutes_used) / 60) AS hours_sold,
       ROUND(100 * SUM(s.minutes_used) / 60 /
             (COUNT(DISTINCT c.computer_id) * 92 * 24), 1) AS utilization_pct
FROM zone z
JOIN computer c ON c.zone_id = z.zone_id
LEFT JOIN game_session s ON s.computer_id = c.computer_id
GROUP BY z.zone_id, z.name
ORDER BY utilization_pct DESC;

-- @@ Q17 | INSERT: реєстрація нового клієнта
SET TIMESTAMP = UNIX_TIMESTAMP('2026-10-06 17:40:00');
INSERT INTO client (login, password_hash, last_name, first_name, phone, email, birth_date)
VALUES ('taras_hryts7', 'pbkdf2:sha256:600000$demo$0', 'Грицюк', 'Тарас',
        '+380971112233', 'taras.hrytsiuk@gmail.com', '2007-04-18');
SELECT client_id, login, last_name, first_name, balance, level_id, registered_at
FROM client WHERE login = 'taras_hryts7';

-- @@ Q18 | UPDATE: блокування клієнта за порушення правил
UPDATE client SET status = 'blocked' WHERE login = 'taras_hryts7';
SELECT login, status FROM client WHERE login = 'taras_hryts7';
UPDATE client SET status = 'active' WHERE login = 'taras_hryts7';

-- @@ Q19 | DELETE: очищення скасованих бронювань, старших за 30 днів
SELECT COUNT(*) AS to_delete FROM booking
WHERE status = 'cancelled' AND starts_at < NOW() - INTERVAL 30 DAY;
DELETE FROM booking
WHERE status = 'cancelled' AND starts_at < NOW() - INTERVAL 30 DAY;
SELECT status, COUNT(*) AS cnt FROM booking GROUP BY status ORDER BY status;

-- =====================================================================
-- Демонстрація процедур, функцій, тригерів, представлень (підрозділ 3.4)
-- Час «заморожено» через SET TIMESTAMP, щоб результати були відтворюваними.
-- =====================================================================

-- @@ D01 | Функції fn_client_discount та fn_session_cost
SELECT c.client_id, CONCAT(c.last_name, ' ', c.first_name) AS client, l.name AS level_name,
       fn_client_discount(c.client_id) AS discount_pct,
       fn_session_cost(4, 135, fn_client_discount(c.client_id)) AS vip_135_min,
       fn_session_cost(3, 600, fn_client_discount(c.client_id)) AS night_std
FROM client c JOIN loyalty_level l ON l.level_id = c.level_id
WHERE c.client_id IN (SELECT MIN(client_id) FROM client GROUP BY level_id)
ORDER BY l.min_spent;

-- @@ D02 | Відкриття зміни адміністратора
SET TIMESTAMP = UNIX_TIMESTAMP('2026-10-06 09:00:00');
INSERT INTO shift (employee_id, started_at, cash_start) VALUES (2, NOW(), 2000);
SET @shift = LAST_INSERT_ID();
SELECT shift_id, employee_id, started_at, cash_start FROM shift WHERE shift_id = @shift;

-- @@ D03 | sp_top_up: поповнення на 1000 грн з бонусом 5 %
SET TIMESTAMP = UNIX_TIMESTAMP('2026-10-06 17:55:00');
SELECT client_id, balance FROM client WHERE client_id = 17;
CALL sp_top_up(17, 1000, 'card', 2, @bal);
SELECT @bal AS new_balance;
SELECT tx_id, tx_type, amount, balance_after, payment_method, created_at
FROM balance_transaction WHERE client_id = 17 ORDER BY tx_id DESC LIMIT 2;

-- @@ D04 | sp_start_session: старт погодинної сесії на V-01
SET TIMESTAMP = UNIX_TIMESTAMP('2026-10-06 18:00:00');
CALL sp_start_session(17, 15, 4, @shift, @s1);
SELECT session_id, client_id, computer_id, started_at, planned_end, discount_pct, status
FROM game_session WHERE session_id = @s1;
SELECT seat_label, status FROM computer WHERE computer_id = 15;

-- @@ D05 | sp_start_session: пакет «3 години» (списання одразу)
CALL sp_top_up(3, 500, 'cash', 2, @bal3);
CALL sp_start_session(3, 2, 2, @shift, @s2);
SELECT session_id, started_at, planned_end, cost, status FROM game_session WHERE session_id = @s2;
SELECT sl.sale_id, sl.sale_type, sl.session_id, sl.total, t.tx_type, t.amount, t.balance_after
FROM sale sl JOIN balance_transaction t ON t.sale_id = sl.sale_id
WHERE sl.session_id = @s2;

-- @@ D06 | sp_end_session: завершення через 2 год 17 хв
SET TIMESTAMP = UNIX_TIMESTAMP('2026-10-06 20:17:00');
SELECT balance AS balance_before FROM client WHERE client_id = 17;
CALL sp_end_session(@s1);
SELECT balance AS balance_after, total_spent, level_id FROM client WHERE client_id = 17;
SELECT sale_id, sale_type, session_id, employee_id, payment_method, total
FROM sale WHERE session_id = @s1;
SELECT seat_label, status FROM computer WHERE computer_id = 15;

-- @@ D07 | Помилка: старт сесії при нульовому балансі
SELECT client_id, balance FROM client WHERE balance = 0 LIMIT 1 INTO @zero_client, @zb;
-- expect-error
CALL sp_start_session(@zero_client, 3, 1, @shift, @s3);

-- @@ D08 | Тригер trg_session_bi: місце на обслуговуванні
SELECT seat_label, status FROM computer WHERE computer_id = 19;
-- expect-error
INSERT INTO game_session (client_id, computer_id, tariff_id, started_at, planned_end)
VALUES (5, 19, 4, NOW(), NOW() + INTERVAL 1 HOUR);

-- @@ D09 | Тригер trg_booking_bi: перетин бронювань
SELECT client_id, balance FROM client
 WHERE balance >= 200 AND status = 'active' AND client_id NOT IN (3, 17)
 ORDER BY client_id LIMIT 1 INTO @bk_client, @bk_balance;
SELECT @bk_client AS client_id, @bk_balance AS balance;
SELECT booking_id, client_id, computer_id, starts_at, ends_at, status
FROM booking WHERE computer_id = 2 AND status = 'pending';
-- expect-error
CALL sp_create_booking(@bk_client, 2, '2026-10-07 20:00:00', '2026-10-07 22:00:00', 2, @b1);

-- @@ D10 | sp_create_booking: успішне бронювання
CALL sp_create_booking(@bk_client, 2, '2026-10-07 21:00:00', '2026-10-07 23:00:00', 2, @b2);
SELECT booking_id, client_id, computer_id, starts_at, ends_at, status, created_by
FROM booking WHERE booking_id = @b2;

-- @@ D11 | Тригер trg_client_bu: заборона від'ємного балансу
SELECT client_id, balance FROM client WHERE client_id = 1;
-- expect-error
UPDATE client SET balance = balance - 5000 WHERE client_id = 1;

-- @@ D12 | sp_bar_sale: продаж через JSON, списання складу
SELECT product_id, name, stock_qty FROM product WHERE product_id IN (5, 9);
CALL sp_bar_sale(3, 2, @shift, 'balance', '[{"product_id": 5, "qty": 2}, {"product_id": 9, "qty": 1}]', @sale);
SELECT sale_id, client_id, payment_method, total FROM sale WHERE sale_id = @sale;
SELECT product_id, name, stock_qty FROM product WHERE product_id IN (5, 9);

-- @@ D13 | БП-09: оплата бару з балансу під час погодинної сесії
CALL sp_start_session(17, 16, 4, @shift, @s4);
-- expect-error
CALL sp_bar_sale(17, 2, @shift, 'balance', '[{"product_id": 1, "qty": 1}]', @sale2);

-- @@ D14 | Тригери trg_request_ai / trg_request_au: ремонт місця
SET TIMESTAMP = UNIX_TIMESTAMP('2026-10-06 20:30:00');
INSERT INTO maintenance_request (computer_id, reported_by, problem, priority)
VALUES (8, 2, 'Не працює клавіатура', 'high');
SET @req = LAST_INSERT_ID();
SELECT seat_label, status FROM computer WHERE computer_id = 8;
SET TIMESTAMP = UNIX_TIMESTAMP('2026-10-06 20:48:00');
UPDATE maintenance_request
   SET status = 'resolved', assigned_to = 6, resolved_at = NOW(), resolution = 'Замінено клавіатуру'
 WHERE request_id = @req;
SELECT seat_label, status FROM computer WHERE computer_id = 8;

-- @@ D15 | Тригер аудиту: зміна ціни тарифу та товару
-- зміну виконує керуючий (так само id працівника передає застосунок)
SET @app_employee_id = 1;
UPDATE tariff  SET price = 65.00 WHERE tariff_id = 1;
UPDATE product SET price = 69.00 WHERE product_id = 5;
SELECT a.audit_id, a.table_name, a.record_id, a.field_name, a.old_value, a.new_value,
       e.last_name AS employee, a.changed_at
FROM audit_log a LEFT JOIN employee e ON e.employee_id = a.employee_id
ORDER BY a.audit_id DESC LIMIT 4;

-- @@ D16 | Представлення v_hall_status: поточна завантаженість залу
SET TIMESTAMP = UNIX_TIMESTAMP('2026-10-06 20:50:00');
SELECT seat_label, zone_name, status, client_name,
       TIME(started_at) AS started, TIME(planned_end) AS until, minutes_left
FROM v_hall_status
WHERE status <> 'free' OR seat_label IN ('S-01', 'V-02')
ORDER BY computer_id;

-- @@ D17 | Представлення v_zone_daily_revenue
SELECT * FROM v_zone_daily_revenue
WHERE work_date = '2026-09-26'
ORDER BY revenue DESC;

-- @@ D18 | Представлення v_client_stats
SELECT client_name, level_name, sessions, hours_played, game_spent, bar_spent, balance
FROM v_client_stats
ORDER BY game_spent DESC
LIMIT 5;

-- @@ D19 | Представлення v_bar_popularity
SELECT popularity_rank, product_name, category, qty_sold, revenue, stock_qty
FROM v_bar_popularity
ORDER BY popularity_rank
LIMIT 6;

-- @@ D20 | Представлення v_open_requests
SELECT request_id, seat_label, problem, priority, status, assigned_to
FROM v_open_requests ORDER BY request_id;

SET TIMESTAMP = DEFAULT;
