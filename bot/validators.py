"""
Валидация того, что вводит клиент на каждом шаге анкеты.
Каждая функция возвращает (ok: bool, error_text: str | None, normalized_value: str | None)
"""
import re
from datetime import datetime, date

PHONE_RE = re.compile(r"^\+?\d[\d\s\-\(\)]{9,14}\d$")
DATE_RE = re.compile(r"^(\d{2})\.(\d{2})\.(\d{4})$")
TIME_RE = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")


def validate_full_name(text: str):
    text = text.strip()
    parts = [p for p in text.split() if p]
    if len(parts) < 2:
        return False, "Пожалуйста, введите ФИО полностью — фамилию и имя (можно и отчество), например: Иванова Мария Сергеевна.", None
    if not all(re.fullmatch(r"[А-Яа-яЁёA-Za-z\-]+", p) for p in parts):
        return False, "ФИО должно состоять только из букв. Попробуйте ещё раз.", None
    normalized = " ".join(p.capitalize() for p in parts)
    return True, None, normalized


def validate_birth_date(text: str):
    text = text.strip()
    m = DATE_RE.match(text)
    if not m:
        return False, "Введите дату рождения в формате ДД.ММ.ГГГГ, например: 05.03.1990.", None
    day, month, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
    try:
        d = date(year, month, day)
    except ValueError:
        return False, "Такой даты не существует. Проверьте число, месяц и год.", None
    today = date.today()
    age = today.year - d.year - ((today.month, today.day) < (d.month, d.day))
    if d > today:
        return False, "Дата рождения не может быть в будущем. Проверьте, пожалуйста.", None
    if age > 120:
        return False, "Проверьте год рождения — получилось больше 120 лет.", None
    return True, None, d.strftime("%d.%m.%Y")


def validate_phone(text: str):
    text = text.strip()
    digits = re.sub(r"\D", "", text)
    if not PHONE_RE.match(text) or len(digits) < 10:
        return False, "Введите номер телефона в формате +7XXXXXXXXXX или воспользуйтесь кнопкой «Отправить номер» ниже.", None
    if not digits.startswith("7") and not digits.startswith("8") and len(digits) == 10:
        digits = "7" + digits
    if digits.startswith("8") and len(digits) == 11:
        digits = "7" + digits[1:]
    normalized = "+" + digits
    return True, None, normalized


def validate_appointment_dt(text: str):
    text = text.strip()
    m = re.match(r"^(\d{2})\.(\d{2})\.(\d{4})\s+([01]\d|2[0-3]):([0-5]\d)$", text)
    if not m:
        return False, "Введите желаемую дату и время в формате ДД.ММ.ГГГГ ЧЧ:ММ, например: 20.08.2026 14:30.", None
    day, month, year, hour, minute = map(int, m.groups())
    try:
        dt = datetime(year, month, day, hour, minute)
    except ValueError:
        return False, "Такой даты/времени не существует. Проверьте значения.", None
    if dt < datetime.now():
        return False, "Эта дата и время уже прошли. Укажите, пожалуйста, будущую дату.", None
    return True, None, dt.strftime("%d.%m.%Y %H:%M")
