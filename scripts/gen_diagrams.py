"""Діаграми процесів і архітектури (Mermaid -> PNG) для пояснювальної записки."""
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IMG = ROOT / "img"
MMDC = ROOT / "node_modules" / ".bin" / "mmdc.cmd"

USE_CASE = """flowchart LR
  classDef actor fill:#ffffff,stroke:#333,stroke-width:1.5px,font-weight:bold
  classDef uc fill:#f2f2f2,stroke:#555
  CL[/"Клієнт"\\]:::actor
  OP[/"Адміністратор зали"\\]:::actor
  TE[/"Технік"\\]:::actor
  OW[/"Керуючий клубом"\\]:::actor
  DBA[/"Адміністратор БД"\\]:::actor
  subgraph S["Система обліку комп'ютерного клубу"]
    direction TB
    U1(["Переглянути тарифи та свій баланс"]):::uc
    U2(["Забронювати місце"]):::uc
    U3(["Зареєструвати клієнта"]):::uc
    U4(["Поповнити баланс"]):::uc
    U5(["Почати / завершити ігрову сесію"]):::uc
    U6(["Продати товари бару"]):::uc
    U7(["Відкрити / закрити зміну"]):::uc
    U8(["Подати / закрити заявку на ремонт"]):::uc
    U9(["Змінити тарифи та ціни"]):::uc
    U10(["Переглянути звіти"]):::uc
    U11(["Керувати ролями, резервні копії"]):::uc
  end
  CL --- U1
  CL --- U2
  OP --- U2
  OP --- U3
  OP --- U4
  OP --- U5
  OP --- U6
  OP --- U7
  OP --- U8
  TE --- U8
  OW --- U9
  OW --- U10
  DBA --- U11
"""

PROCESS = """flowchart LR
  A([Відвідувач прийшов до клубу]) --> B{Є обліковий запис?}
  B -- ні --> C[Реєстрація клієнта] --> D
  B -- так --> D{Є бронювання?}
  D -- так --> E[Пошук бронювання,<br/>звільнення місця]
  D -- ні --> F[Вибір зони і вільного місця]
  E --> G
  F --> G[Вибір тарифу: погодинний<br/>або пакет]
  G --> H{Коштів досить?}
  H -- ні --> I[Поповнення балансу<br/>готівкою або карткою] --> H
  H -- так --> J[Старт сесії, ПК стає «зайнятим»]
  J --> K[Гра; покупки в барі]
  K --> L{Клієнт завершує<br/>або час вичерпано}
  L --> M[Завершення сесії:<br/>розрахунок і списання]
  M --> N[Нарахування рівня лояльності,<br/>ПК стає «вільним»]
"""

ARCH = """flowchart LR
  B["Браузер<br/>(HTML/CSS)"] -- HTTP --> F["Flask-застосунок<br/>app.py, шаблони Jinja2"]
  F -- "PyMySQL<br/>CALL / SELECT" --> M[("MySQL<br/>БД cyberclub")]
  subgraph M2 [" "]
    direction TB
    R["Ролі: r_owner, r_operator,<br/>r_technician, r_client_app"]
    P["Процедури та функції"]
    T["Тригери та подія"]
    V["Представлення"]
  end
  M --- M2
"""


def render(src, name):
    mmd = IMG / f"{name}.mmd"
    mmd.write_text(src, encoding="utf-8")
    cfg = IMG / "mermaid_flow.json"
    cfg.write_text('{"theme":"neutral","flowchart":{"htmlLabels":true,"curve":"basis"},'
                   '"themeVariables":{"fontFamily":"Times New Roman","fontSize":"18px"}}',
                   encoding="utf-8")
    subprocess.run([str(MMDC), "-i", str(mmd), "-o", str(IMG / f"{name}.png"), "-c", str(cfg),
                    "-s", "3", "-b", "white"], check=True, shell=True)


if __name__ == "__main__":
    # use_case і process малюються вручну: scripts/gen_svg_diagrams.py
    render(ARCH, "architecture")
    print("ok")
