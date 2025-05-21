import matplotlib.pyplot as plt
from matplotlib.patches import Wedge
from datetime import datetime
import pytz

# Конфигурация торговых сессий
sessions = [
    {"name": "Сидней", "start": 22, "end": 7, "color": "#3498db"},
    {"name": "Токио", "start": 0, "end": 9, "color": "#2ecc71"},
    {"name": "Лондон", "start": 7, "end": 16, "color": "#e74c3c"},
    {"name": "Нью-Йорк", "start": 13, "end": 22, "color": "#f1c40f"},
]

# Определяем текущую сессию
utc_now = datetime.now(pytz.utc)
current_hour = utc_now.hour


# Функция для проверки активности сессии
def is_active(start, end, current):
    if start < end:
        return start <= current < end
    else:
        return current >= start or current < end


# Создание круговой диаграммы
fig, ax = plt.subplots(figsize=(8, 8), subplot_kw={"aspect": "equal"})
ax.set_title("Торговые сессии Форекс", fontsize=16, weight="bold")

# Рисуем круговые сектора
start_angle = 90  # Начало с верхней точки круга
for session in sessions:
    # Вычисляем углы для сектора
    end_angle = start_angle - (session["end"] - session["start"]) * 15
    if session["end"] < session["start"]:
        end_angle = start_angle - (24 - session["start"] + session["end"]) * 15

    # Выделение активной сессии
    active = is_active(session["start"], session["end"], current_hour)
    alpha = 1 if active else 0.5

    # Добавляем сектор
    wedge = Wedge(
        center=(0, 0),
        r=1,
        theta1=start_angle,
        theta2=end_angle,
        facecolor=session["color"],
        alpha=alpha,
        label=f"{session['name']} ({session['start']:02d}:00 - {session['end']:02d}:00)",
    )
    ax.add_patch(wedge)
    start_angle = end_angle

# Добавляем текущий час как стрелку
angle = 90 - current_hour * 15
ax.plot(
    [0, 0.7 * plt.cos(angle * 3.14159 / 180)],
    [0, 0.7 * plt.sin(angle * 3.14159 / 180)],
    color="black",
    lw=2,
    label=f"Сейчас: {current_hour:02d}:00 UTC",
)

# Настройка
ax.set_xlim(-1.2, 1.2)
ax.set_ylim(-1.2, 1.2)
ax.axis("off")
ax.legend(loc="center left", bbox_to_anchor=(1, 0.5), fontsize=10)

# Отображение
plt.show()
