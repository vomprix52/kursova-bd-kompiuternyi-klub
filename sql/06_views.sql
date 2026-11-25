-- =====================================================================
-- Скрипт 06. Представлення (VIEW)
-- =====================================================================
USE cyberclub;

-- ---------------------------------------------------------------------
-- Представлення 1. Поточна завантаженість залу (карта місць)
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW v_hall_status AS
SELECT c.computer_id,
       c.seat_label,
       z.name                                         AS zone_name,
       c.status,
       s.session_id,
       CONCAT(cl.last_name, ' ', cl.first_name)       AS client_name,
       s.started_at,
       s.planned_end,
       GREATEST(TIMESTAMPDIFF(MINUTE, NOW(), s.planned_end), 0) AS minutes_left,
       (SELECT MIN(b.starts_at) FROM booking b
         WHERE b.computer_id = c.computer_id AND b.status = 'pending'
           AND b.ends_at > NOW())                     AS next_booking
FROM computer c
JOIN zone z              ON z.zone_id = c.zone_id
LEFT JOIN game_session s ON s.computer_id = c.computer_id AND s.status = 'active'
LEFT JOIN client cl      ON cl.client_id = s.client_id;

-- ---------------------------------------------------------------------
-- Представлення 2. Денна виручка від ігрового часу по зонах
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW v_zone_daily_revenue AS
SELECT DATE(s.started_at)               AS work_date,
       z.name                           AS zone_name,
       COUNT(*)                         AS sessions,
       ROUND(SUM(s.minutes_used) / 60, 1) AS hours_played,
       SUM(s.cost)                      AS revenue
FROM game_session s
JOIN computer c ON c.computer_id = s.computer_id
JOIN zone z     ON z.zone_id = c.zone_id
WHERE s.status = 'finished'
GROUP BY DATE(s.started_at), z.zone_id, z.name;

-- ---------------------------------------------------------------------
-- Представлення 3. Статистика клієнта
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW v_client_stats AS
SELECT cl.client_id,
       cl.login,
       CONCAT(cl.last_name, ' ', cl.first_name) AS client_name,
       l.name                                   AS level_name,
       l.discount_pct,
       cl.balance,
       cl.total_spent,
       COALESCE(gs.sessions, 0)                 AS sessions,
       COALESCE(gs.hours, 0)                    AS hours_played,
       COALESCE(gs.game_spent, 0)               AS game_spent,
       COALESCE(br.bar_spent, 0)                AS bar_spent,
       gs.last_visit
FROM client cl
JOIN loyalty_level l ON l.level_id = cl.level_id
LEFT JOIN (SELECT client_id, COUNT(*) AS sessions,
                  ROUND(SUM(minutes_used) / 60, 1) AS hours,
                  SUM(cost) AS game_spent, MAX(started_at) AS last_visit
             FROM game_session WHERE status = 'finished'
            GROUP BY client_id) gs ON gs.client_id = cl.client_id
LEFT JOIN (SELECT client_id, SUM(total) AS bar_spent
             FROM sale WHERE client_id IS NOT NULL AND sale_type = 'bar'
            GROUP BY client_id) br ON br.client_id = cl.client_id;

-- ---------------------------------------------------------------------
-- Представлення 4. Популярність товарів бару
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW v_bar_popularity AS
SELECT p.product_id,
       p.name                                   AS product_name,
       pc.name                                  AS category,
       COALESCE(SUM(si.quantity), 0)            AS qty_sold,
       COALESCE(SUM(si.quantity * si.unit_price), 0) AS revenue,
       p.stock_qty,
       RANK() OVER (ORDER BY COALESCE(SUM(si.quantity), 0) DESC) AS popularity_rank
FROM product p
JOIN product_category pc ON pc.category_id = p.category_id
LEFT JOIN sale_item si   ON si.product_id = p.product_id
GROUP BY p.product_id, p.name, pc.name, p.stock_qty;

-- ---------------------------------------------------------------------
-- Представлення 5. Черга заявок для техніка
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW v_open_requests AS
SELECT r.request_id,
       c.seat_label,
       r.problem,
       r.priority,
       r.status,
       r.created_at,
       CONCAT(e.last_name, ' ', e.first_name)  AS reported_by,
       CONCAT(t.last_name, ' ', t.first_name)  AS assigned_to,
       TIMESTAMPDIFF(HOUR, r.created_at, NOW()) AS hours_open
FROM maintenance_request r
JOIN computer c      ON c.computer_id = r.computer_id
JOIN employee e      ON e.employee_id = r.reported_by
LEFT JOIN employee t ON t.employee_id = r.assigned_to
WHERE r.status <> 'resolved';

-- Привілеї на представлення
GRANT SELECT ON cyberclub.v_hall_status    TO r_operator, r_technician;
GRANT SELECT ON cyberclub.v_client_stats   TO r_operator, r_client_app;
GRANT SELECT ON cyberclub.v_bar_popularity TO r_operator;
GRANT SELECT ON cyberclub.v_open_requests  TO r_operator, r_technician;
