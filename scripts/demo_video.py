"""Записує демонстраційне відео вебзастосунку -> docs/Demo_CyberClub.mp4.

Готує «живий» стан залу (як для скриншотів), запускає Flask і проходить
сценарій через Playwright з видимим курсором і субтитрами. Потрібен
запущений MySQL на 3307 і ffmpeg у PATH."""
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

from db import connect
from screenshots import BASE, live_state

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "Demo_CyberClub.mp4"
TMP = ROOT / "docs" / "tmp" / "video"
W, H = 1366, 800
SUBTITLES = False   # True – показувати пояснення внизу кадру

# курсор і субтитри; субтитр зберігається в sessionStorage і переживає переходи між сторінками
INIT_JS = """
(() => {
  const arrow = '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="30" viewBox="0 0 20 30">'
    + '<path d="M1 1 L1 23 L6.5 17.8 L10.3 27 L14 25.4 L10.3 16.5 L17.5 16.5 Z" fill="#fff" '
    + 'stroke="#000" stroke-width="1.4" stroke-linejoin="round"/></svg>';
  const css = `#__cur{position:fixed;z-index:99999;width:20px;height:30px;pointer-events:none;
    filter:drop-shadow(1px 2px 1.5px rgba(0,0,0,.35))}
    #__cap{position:fixed;z-index:99998;left:50%;bottom:22px;transform:translateX(-50%);
    max-width:1100px;background:rgba(20,24,33,.88);color:#fff;font:500 21px/1.35 'Segoe UI',sans-serif;
    padding:12px 24px;border-radius:10px;text-align:center;pointer-events:none;
    box-shadow:0 6px 24px rgba(0,0,0,.25)} #__cap:empty{display:none}`;
  const boot = () => {
    if (document.getElementById('__cur')) return;
    const st = document.createElement('style'); st.textContent = css; document.head.appendChild(st);
    const c = document.createElement('div'); c.id = '__cur'; c.innerHTML = arrow; document.body.appendChild(c);
    const p = JSON.parse(sessionStorage.getItem('__pos') || '[683,400]');
    c.style.left = p[0] + 'px'; c.style.top = p[1] + 'px';
    const cap = document.createElement('div'); cap.id = '__cap';
    cap.textContent = sessionStorage.getItem('__cap') || ''; document.body.appendChild(cap);
    addEventListener('mousemove', e => { c.style.left = e.clientX + 'px'; c.style.top = e.clientY + 'px';
      sessionStorage.setItem('__pos', JSON.stringify([e.clientX, e.clientY])); }, true);
  };
  window.__setCap = t => { sessionStorage.setItem('__cap', t);
    const el = document.getElementById('__cap'); if (el) el.textContent = t; };
  document.readyState === 'loading' ? addEventListener('DOMContentLoaded', boot) : boot();
})();
"""


class Demo:
    def __init__(self, page):
        self.p = page
        self.pos = (W / 2, H / 2)

    def cap(self, text, wait=0.0):
        if SUBTITLES:
            self.js("t => window.__setCap(t)", text)
        self.pause(wait)

    def pause(self, s):
        if s:
            self.p.wait_for_timeout(int(s * 1000))

    def move(self, sel):
        loc = self.p.locator(sel).first
        loc.scroll_into_view_if_needed()
        self.pause(0.25)
        b = loc.bounding_box()
        x, y = b["x"] + b["width"] / 2, b["y"] + b["height"] / 2
        self.p.mouse.move(x, y, steps=22)
        self.pos = (x, y)
        self.pause(0.3)
        return loc

    def click(self, sel, after=1.0):
        self.move(sel)
        self.p.mouse.down()
        self.pause(0.08)
        self.p.mouse.up()
        self.p.wait_for_load_state("networkidle")
        self.pause(after)

    def type(self, sel, text):
        loc = self.move(sel)
        loc.click()
        loc.fill("")
        loc.press_sequentially(text, delay=85)
        self.pause(0.4)

    def select(self, sel, value):
        self.move(sel)
        self.p.locator(sel).first.select_option(value)
        self.pause(0.7)

    def set_value(self, sel, value):
        self.move(sel)
        self.p.locator(sel).first.fill(value)
        self.pause(0.6)

    def scroll(self, dy, steps=10, wait=0.6):
        for _ in range(steps):
            self.p.mouse.wheel(0, dy / steps)
            self.pause(0.06)
        self.pause(wait)

    def js(self, code, arg=None):
        # після кліку сторінка може ще перезавантажуватись – чекаємо і пробуємо знову
        for _ in range(5):
            try:
                self.p.wait_for_load_state("networkidle")
                return self.p.evaluate(code, arg)
            except Exception as e:
                if "context was destroyed" not in str(e):
                    raise
                self.pause(0.3)

    def top(self):
        self.js("window.scrollTo({top:0, behavior:'smooth'})")
        self.pause(0.6)

    def login(self, user, pwd, client=False):
        self.p.goto(BASE + "/logout")
        self.p.goto(BASE + "/login")
        self.p.wait_for_load_state("networkidle")
        self.pause(0.6)
        if client:
            self.click("text=Клієнт", after=0.3)
        self.type("input[name=login]", user)
        self.type("input[name=password]", pwd)
        self.click("button.btn", after=1.2)


def scenario(d, tomorrow, client_login):
    p = d.p
    # ---------- вступ
    p.goto(BASE + "/login")
    p.wait_for_load_state("networkidle")
    d.cap("CyberClub – демонстраційний вебзастосунок до бази даних комп'ютерного клубу", 3.5)
    d.cap("Уся логіка (ціни, списання, перевірки) працює в самій базі MySQL, сайт лише показує результат", 4)

    # ---------- керуючий
    d.cap("Спершу входимо як керуючий (власник клубу)", 0.5)
    d.login("owner", "owner123")
    d.cap("Звіти: виторг по днях і зонах, найактивніші клієнти – дані беруться з представлень у базі", 4)
    d.scroll(450, wait=2.5)
    d.cap("Журнал змін цін: тригер сам записує, хто і коли змінив ціну", 3)
    d.scroll(600, wait=3)
    d.top()

    # ---------- адміністратор зали
    d.cap("Тепер входимо як адміністратор зали", 0.5)
    d.login("admin3", "admin123")
    d.cap("Карта залу: зелене – вільне місце, червоне – зайняте, жовте – заброньоване", 4)
    d.scroll(380, wait=1.5)
    d.cap("Для кожного зайнятого місця видно клієнта і скільки часу ще оплачено", 3)
    d.top()

    d.cap("Поповнюємо баланс клієнта на 300 грн карткою", 0.8)
    topup = "form[action='/topup']"
    d.select(f"{topup} select[name=client_id]", "19")
    d.type(f"{topup} input[name=amount]", "300")
    d.select(f"{topup} select[name=method]", "card")
    d.click(f"{topup} button", after=0.5)
    d.top()
    d.cap("Баланс змінила процедура в базі, а операція записалась у журнал транзакцій", 3.5)

    d.cap("Запускаємо ігрову сесію: клієнт, вільне місце, тариф", 0.8)
    start = "form[action='/session/start']"
    d.select(f"{start} select[name=client_id]", "19")
    d.select(f"{start} select[name=computer_id]", "18")
    d.select(f"{start} select[name=tariff_id]", "4")
    d.click(f"{start} button", after=0.5)
    d.top()
    d.cap("Сесію розпочато – база сама порахувала, на скільки хвилин вистачає грошей", 4)

    d.cap("Завершуємо одну з сесій – база рахує хвилини і вартість", 0.8)
    d.click(".seat.busy form button", after=0.5)
    d.top()
    d.pause(3.5)

    # ---------- бронювання з помилкою
    d.cap("Бронювання: спробуємо зайняти місце S-02 на час, коли воно вже заброньоване", 1)
    d.click("nav >> text=Бронювання", after=1)
    dt = tomorrow.strftime("%Y-%m-%d")
    d.select("select[name=client_id]", "10")
    d.select("select[name=computer_id]", "2")
    d.set_value("input[name=starts_at]", f"{dt}T19:00")
    d.set_value("input[name=ends_at]", f"{dt}T21:00")
    d.click("form button.btn >> text=Забронювати", after=0.5)
    d.top()
    d.cap("Відмова! Перетин бронювань не пропустив тригер у базі, а не перевірка на сайті", 5)

    # ---------- бар
    d.cap("Бар: продаємо напій і снек з оплатою з балансу клієнта", 1)
    d.click("nav >> text=Бар", after=1)
    d.type("input[name=qty_5]", "1")
    d.type("input[name=qty_16]", "2")
    d.select("select[name=client_id]", "27")
    d.select("select[name=method]", "balance")
    d.click("text=Пробити чек", after=0.5)
    d.top()
    d.cap("Чек пробито: база списала товар зі складу і гроші з балансу одночасно", 4.5)

    # ---------- технік
    d.cap("Входимо як технік", 0.5)
    d.login("tech1", "tech123")
    d.cap("Створюємо заявку з високим пріоритетом – місце автоматично виводиться з роботи", 1)
    d.select("select[name=computer_id]", "5")
    d.type("input[name=problem]", "Не працює мишка")
    d.select("select[name=priority]", "high")
    d.click("form button.btn >> text=Створити", after=1)
    d.cap("Заявку створено, а тригер у базі сам перевів місце S-05 у статус «ремонт» – сесію на ньому не почати", 4.5)
    d.cap("Закриваємо заявку – тригер повертає місце у статус «вільне»", 0.8)
    d.click("tr:has-text('Не працює мишка') form button", after=0.5)
    d.pause(3)

    # ---------- клієнт
    d.cap("І нарешті – кабінет клієнта", 0.5)
    d.login(client_login, "client123", client=True)
    d.cap("Клієнт бачить свій баланс, рівень знижки, історію та може забронювати місце", 4)
    d.scroll(500, wait=3)
    d.top()
    d.cap("Кожна роль працює під своїм обліковим записом MySQL – права перевіряє сама база", 4.5)
    d.cap("", 0.5)


def main():
    if not shutil.which("ffmpeg"):
        sys.exit("ffmpeg не знайдено")
    tomorrow = live_state()
    con = connect()
    cur = con.cursor()
    cur.execute("SELECT login FROM client WHERE client_id = 3")
    client_login = cur.fetchone()[0]
    con.close()

    srv = subprocess.Popen([sys.executable, str(ROOT / "app" / "app.py")], cwd=ROOT / "app")
    for _ in range(40):
        try:
            urllib.request.urlopen(BASE + "/login")
            break
        except OSError:
            time.sleep(0.5)
    shutil.rmtree(TMP, ignore_errors=True)
    TMP.mkdir(parents=True)
    try:
        with sync_playwright() as pw:
            b = pw.chromium.launch()
            ctx = b.new_context(viewport={"width": W, "height": H},
                                record_video_dir=str(TMP), record_video_size={"width": W, "height": H})
            ctx.add_init_script(INIT_JS)
            page = ctx.new_page()
            scenario(Demo(page), tomorrow, client_login)
            video = page.video.path()
            ctx.close()
            b.close()
    finally:
        srv.terminate()
    # webm -> mp4 (H.264), перша секунда (порожня сторінка) обрізається
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", "1", "-i", video,
                    "-c:v", "libx264", "-preset", "slow", "-crf", "20", "-pix_fmt", "yuv420p",
                    "-r", "30", "-movflags", "+faststart", str(OUT)], check=True)
    print("ok", OUT)


if __name__ == "__main__":
    main()
