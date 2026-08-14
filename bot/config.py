"""
Загрузка настроек бота из переменных окружения (.env).
"""
import os
from dotenv import load_dotenv

load_dotenv()


def _parse_admin_ids(raw: str) -> list[int]:
    ids = []
    for part in raw.split(","):
        part = part.strip()
        if part:
            ids.append(int(part))
    return ids


BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")

# Telegram numeric ID двух администраторов, через запятую в .env:
# ADMIN_IDS=111111111,222222222
ADMIN_IDS: list[int] = _parse_admin_ids(os.getenv("ADMIN_IDS", ""))

# Данные клиники для приветственного сообщения (можно менять под себя)
CLINIC_NAME: str = os.getenv("CLINIC_NAME", "CMD Технопарк (ООО «МедСистема»)")
CLINIC_ADDRESS: str = os.getenv("CLINIC_ADDRESS", "г. Москва, пр-т Лихачёва, д. 22 (10 мин от м. Технопарк, выход №3)")
CLINIC_PHONE: str = os.getenv("CLINIC_PHONE", "+7 (495) 788-00-01, +7 (495) 120-13-12")
CLINIC_HOURS: str = os.getenv("CLINIC_HOURS", "Пн–Пт 07:30–19:00, Сб–Вс 08:00–17:00")

# --- Google Sheets ---
# Путь к json-файлу сервисного аккаунта Google (вариант для запуска на своём компьютере/VPS)
GOOGLE_CREDENTIALS_FILE: str = os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json")

# Альтернатива файлу: весь json-ключ одной строкой в переменной окружения
# (удобно для облачных хостингов типа Railway, где нет своего файла на диске).
# Если задано — имеет приоритет над GOOGLE_CREDENTIALS_FILE.
GOOGLE_CREDENTIALS_JSON: str = os.getenv("GOOGLE_CREDENTIALS_JSON", "")

# ID Google-таблицы (берётся из её URL:
# https://docs.google.com/spreadsheets/d/ЭТОТ_ID/edit)
GOOGLE_SHEET_ID: str = os.getenv("GOOGLE_SHEET_ID", "")

# Название листа внутри таблицы, куда будут дописываться заявки
GOOGLE_SHEET_WORKSHEET: str = os.getenv("GOOGLE_SHEET_WORKSHEET", "Заявки")

if not BOT_TOKEN:
    raise RuntimeError(
        "Не задан BOT_TOKEN. Укажите его в файле .env (см. .env.example)."
    )

if len(ADMIN_IDS) < 1:
    raise RuntimeError(
        "Не задан ни один администратор. Укажите ADMIN_IDS в .env (см. .env.example)."
    )
