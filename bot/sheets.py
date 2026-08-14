"""
Запись заявок в Google Sheets через сервисный аккаунт (gspread).

Как подключить (см. подробнее в README.md):
1. Создать сервисный аккаунт в Google Cloud, включить Google Sheets API.
2. Скачать json-ключ, положить рядом с ботом, путь указать в .env как GOOGLE_CREDENTIALS_FILE.
3. Создать Google-таблицу, дать сервисному аккаунту доступ "Редактор" по его email
   (он указан в json-файле в поле client_email).
4. ID таблицы (из URL) указать в .env как GOOGLE_SHEET_ID.

Если Google Sheets не настроен (нет credentials.json), бот продолжает работать
и просто пропускает запись в таблицу — заявки всё равно уходят администраторам.
"""
import json
import logging
from datetime import datetime

import gspread
from google.oauth2.service_account import Credentials

from bot import config

logger = logging.getLogger(__name__)

_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

_HEADER = ["Дата и время заявки", "ФИО", "Дата рождения", "Телефон", "Врач/специализация", "Желаемая дата и время приёма", "Telegram username", "Telegram ID"]

_worksheet = None
_enabled = False


def init_sheets() -> None:
    """Пытается подключиться к Google Sheets. Если не получилось — просто отключает эту функцию."""
    global _worksheet, _enabled
    if not config.GOOGLE_SHEET_ID:
        logger.warning("GOOGLE_SHEET_ID не задан — запись в Google Sheets отключена.")
        return
    try:
        if config.GOOGLE_CREDENTIALS_JSON:
            # Удобно для хостингов вроде Railway: весь json-ключ вставляется
            # одной переменной окружения, без загрузки отдельного файла.
            info = json.loads(config.GOOGLE_CREDENTIALS_JSON)
            creds = Credentials.from_service_account_info(info, scopes=_SCOPES)
        else:
            creds = Credentials.from_service_account_file(config.GOOGLE_CREDENTIALS_FILE, scopes=_SCOPES)
        client = gspread.authorize(creds)
        sheet = client.open_by_key(config.GOOGLE_SHEET_ID)
        try:
            ws = sheet.worksheet(config.GOOGLE_SHEET_WORKSHEET)
        except gspread.WorksheetNotFound:
            ws = sheet.add_worksheet(title=config.GOOGLE_SHEET_WORKSHEET, rows=1000, cols=len(_HEADER))
        if ws.row_count == 0 or not ws.row_values(1):
            ws.append_row(_HEADER)
        _worksheet = ws
        _enabled = True
        logger.info("Google Sheets подключены успешно.")
    except Exception:
        logger.exception("Не удалось подключиться к Google Sheets. Запись в таблицу будет пропущена.")
        _enabled = False


def append_booking(data: dict, username: str, user_id: int) -> None:
    if not _enabled or _worksheet is None:
        return
    try:
        _worksheet.append_row(
            [
                datetime.now().strftime("%d.%m.%Y %H:%M:%S"),
                data["full_name"],
                data["birth_date"],
                data["phone"],
                data["doctor_label"],
                data["appointment_dt"],
                f"@{username}" if username else "-",
                str(user_id),
            ]
        )
    except Exception:
        logger.exception("Не удалось записать заявку в Google Sheets.")
